# Arm CCA and Realms: Confidential Compute on Armv9-A

Arm's answer to Intel TDX and AMD SEV-SNP is the **Confidential Compute Architecture
(CCA)**, built on the Realm Management Extension (RME) that arrived with the
Armv9.2-A architecture: two *additional* security states beyond TrustZone's
Normal/Secure pair, run by a new **Realm Management Monitor (RMM)**. RMM guests --
confidential VMs called **realms** -- are protected not by encryption alone but by
a privilege-independent table classifying every physical address. TDX, SEV-SNP, and
SGX deep dives: [confidential computing](../../security/advanced/confidential-computing.md),
[Intel SGX](../../cryptography/intel-sgx.md); this page covers the Arm mechanisms.

## From Two Worlds to Four

TrustZone gave Arm two worlds: Secure (TEE, see [embedded TEEs](../../linux/embedded/tee.md))
and Normal (rich OS). RME adds **Root** and **Realm** -- four physical address
spaces (PAS) coexisting on one machine:

```text
  World       EL      Resident software                May access PAS
  ----------- ------- -------------------------------- ------------------
  Root        EL3     Monitor firmware (TF-A), GPT     ALL four
                      owner, PAS-transition arbiter
  Realm       EL2     RMM: realm stage-2, lifecycle    Realm + Non-secure
              EL1/0   Realm VM: kernel + apps          Realm (own memory)
  Secure      EL1/0   TEE (OP-TEE etc.)                Secure + Non-secure
  Non-secure  EL2/1/0 Host hypervisor, Linux, VMs      Non-secure
```

The hypervisor keeps *control* (scheduling, memory sizing, device emulation) but
loses *visibility*; the RMM holds realm stage-2 translation and validates every
memory operation; EL3 firmware owns the GPT. A normal VM image can even run *as a
realm* unchanged -- Linux documents its own realm-guest requirements
([kernel arm-cca doc](https://docs.kernel.org/arch/arm64/arm-cca.html)).

## The GPT: One Table Checked on Every Physical Access

Every MMU, SMMU, and TLB walk ends in a physical address, and RME checks it against
a single system-wide **Granule Protection Table** -- a Granule Protection Check (GPC)
invisible to all software below EL3. The GPT is a two-level radix tree whose
parameters live in `GPCCR_EL3`:

| Register field | Values | Meaning |
|---|---|---|
| `GPCCR_EL3.GPC` | enable bit | Turns on granule protection checks |
| `GPCCR_EL3.PPS` | up to 2^52 | Size of the protected physical address space |
| `GPCCR_EL3.PGS` | 4K, 16K, 64K | Granule size; smallest unit one GPTE classifies |
| `GPCCR_EL3.L0GPTSZ` | 1G, 16G, 64G, 512G | PA span governed by one L0 entry |

An L0 entry is either a *block descriptor* (its whole span in one PAS) or a *table
descriptor* pointing into an L1 table of granule entries. Each entry carries a 4-bit
GPI (Granule Protection Info) field; the encodings below match TF-A's GPT library
([TF-A GPT design](https://trustedfirmware-a.readthedocs.io/en/latest/components/granule-protection-tables-design.html)):

| GPI | PAS it selects | Who may access |
|---|---|---|
| `0x0` NO_ACCESS | none | nobody; fault on any access |
| `0x8` SECURE | Secure world | Secure or Root |
| `0x9` NS | Non-secure | Non-secure or Root |
| `0xA` ROOT | Root world | Root only |
| `0xB` REALM | Realm world | Realm or Root |
| `0xF` ANY | shared | all worlds (boot, bounce buffers) |

Realm translation runs in two passes on every access: the realm VM walks stage-1
(VA to IPA), the RMM owns stage-2 (IPA to PA) in Realm-world translation tables,
then the GPC consults the GPT *by physical address* -- `VA --stage1--> IPA
--stage2 (RMM RTT)--> PA --GPT lookup--> PAS match?` -- a check the hypervisor can
neither skip nor spoof. A failure is a **Granule Protection Fault**: a synchronous
external abort routed to EL3 (asynchronous for some write cases). No world can map
a realm-private granule into its own page tables and read it -- the GPT votes
independently of every stage-1/stage-2 mapping. The simulator below enforces the
rules (pure Python; run it):

```python
# GPT walk + GPC simulator. Values per Arm RME / TF-A GPT library:
#   GPCCR_EL3.L0GPTSZ = 30 bits -> one L0 entry governs 1 GiB (1/16/64/512 GiB)
#   GPCCR_EL3.PGS = 4 KiB; the GPTE GPI field is 4 bits, encodings per TF-A gpt_rme.h.
GPI_NAME = {0x0: "NO_ACCESS", 0x8: "SECURE", 0x9: "NS",
            0xA: "ROOT", 0xB: "REALM", 0xF: "ANY"}
L0GPTSZ = 1 << 30                # bytes per L0 entry
PGS = 1 << 12                    # granule size

class GPT:
    def __init__(self, pps_bits):
        self.pps = 1 << pps_bits
        # default like TF-A boot init: every L0 entry is an ANY block
        self.l0 = [("block", 0xF)] * (self.pps // L0GPTSZ)
        self.l1 = {}             # l0 index -> {granule index: gpi}

    def l0_table(self, idx):
        self.l0[idx] = ("table", None)
        self.l1[idx] = {i: 0xF for i in range(self.pps // PGS)}

    def set_gpte(self, pa, gpi):  # GTSI / RMM rewrite entries on transitions
        i0 = pa // L0GPTSZ
        assert self.l0[i0][0] == "table", "shatter the L0 block first"
        self.l1[i0][(pa % L0GPTSZ) // PGS] = gpi

    def lookup(self, pa):
        i0 = pa // L0GPTSZ
        kind, gpi = self.l0[i0]
        if kind == "block":
            return [("L0", i0, "block descriptor")], gpi
        i1 = (pa % L0GPTSZ) // PGS
        return [("L0", i0, "table descriptor"), ("L1", i1, "GPTE")], self.l1[i0][i1]

def gpc(world, gpi):
    if world == "ROOT":          # EL3 firmware sees all four PAS
        return True
    return gpi == 0xF or GPI_NAME[gpi] == world

def access(gpt, world, pa):
    walk, gpi = gpt.lookup(pa)
    path = " -> ".join(f"{lvl}[{i}]" for lvl, i, _ in walk)
    verdict = "allowed" if gpc(world, gpi) else "GPF (abort to EL3)"
    print(f"  {world:<6} PA 0x{pa:08X}  {path:<24} {walk[-1][2]:<17} "
          f"GPI={GPI_NAME[gpi]:<9} -> {verdict}")

gpt = GPT(pps_bits=31)           # 2 GiB protected physical space
gpt.l0_table(0)                  # 0x00000000-0x3FFFFFFF: mixed worlds, L1 granules
gpt.l0[1] = ("block", 0x9)       # 0x40000000-0x7FFFFFFF: host DRAM as one NS block
gpt.set_gpte(0x10000000, 0xB)    # realm region granule 1 (delegated + DATA_CREATE)
gpt.set_gpte(0x10001000, 0xB)    # realm region granule 2
gpt.set_gpte(0x20000000, 0xF)    # shared bounce buffer (host writable)
gpt.set_gpte(0x30000000, 0x9)    # normal world kernel page
print("Walks and granule protection checks:")
access(gpt, "REALM", 0x10001200)     # guest inside realm touches its own RAM
access(gpt, "NS", 0x10001200)        # hostile hypervisor peeks at realm RAM
access(gpt, "NS", 0x20000000)        # host reads the shared bounce buffer
access(gpt, "SECURE", 0x30000000)    # TrustZone TA fetches an NS-marked page
print("Granule Transition Service: bounce buffer handed to the realm")
gpt.set_gpte(0x20000000, 0xB)
access(gpt, "NS", 0x20000000)        # same host read, after the transition
access(gpt, "REALM", 0x20000000)     # realm may now use it
```

Real output:

```text
Walks and granule protection checks:
  REALM  PA 0x10001200  L0[0] -> L1[65537]       GPTE              GPI=REALM     -> allowed
  NS     PA 0x10001200  L0[0] -> L1[65537]       GPTE              GPI=REALM     -> GPF (abort to EL3)
  NS     PA 0x20000000  L0[0] -> L1[131072]      GPTE              GPI=ANY       -> allowed
  SECURE PA 0x30000000  L0[0] -> L1[196608]      GPTE              GPI=NS        -> GPF (abort to EL3)
Granule Transition Service: bounce buffer handed to the realm
  NS     PA 0x20000000  L0[0] -> L1[131072]      GPTE              GPI=REALM     -> GPF (abort to EL3)
  REALM  PA 0x20000000  L0[0] -> L1[131072]      GPTE              GPI=REALM     -> allowed
```

Ownership changes between worlds are explicit. The **Granule Transition Service**
(GTSI, an SMC interface on EL3) moves granules between PAS states: the host
delegates a Non-secure granule to the Realm PAS (`RMI_GRANULE_DELEGATE`) before
the RMM will use it for realm data, and a guest hands pages back via
`RSI_IPA_STATE_SET`, which propagates down to a GPT rewrite. TF-A transitions
only L1 entries, fusing or shattering contiguous GPTE runs.

## RMM and Its Two SMC Interfaces

The RMM is ordinary EL2 software in the Realm world -- an open-source reference
implementation exists ([TF-RMM](https://www.trustedfirmware.org/projects/tf-rmm/))
-- but it is part of the realm TCB, measured and updated as a unit. It speaks SMC
to both sides:

| Interface | Caller -> callee | Direction of trust | Representative calls |
|---|---|---|---|
| **RMI** (Realm Management Interface) | Host hypervisor (NS EL2) -> RMM | Host requests; RMM validates and executes | `RMI_REALM_CREATE`, `RMI_REC_CREATE`, `RMI_REC_ENTER`, `RMI_DATA_CREATE`, `RMI_RTT_MAP_UNPROTECTED`, `RMI_GRANULE_DELEGATE` |
| **RSI** (Realm Services Interface) | Realm guest (EL1/EL0) -> RMM | Guest requests about its own IPA space | `RSI_IPA_STATE_SET`, `RSI_MEASUREMENT_EXTEND`, `RSI_ATTESTATION_TOKEN_INIT`, `RSI_HOST_CALL` |

The host's RMI vocabulary is deliberately narrow: create/destroy realm descriptors
(RD), create and enter Realm Execution Contexts (RECs -- vCPUs), create data pages,
and map *unprotected* IPA ranges for emulated MMIO. The Linux RSI side (verified in
`arch/arm64/include/asm/rsi_smc.h`) is exactly ten calls: `RSI_ABI_VERSION`,
`RSI_FEATURES`, `RSI_REALM_CONFIG`, `RSI_IPA_STATE_SET/GET`,
`RSI_MEASUREMENT_READ/EXTEND`, `RSI_ATTESTATION_TOKEN_INIT/CONTINUE`, `RSI_HOST_CALL`.
The guest's IPA space splits in half: the lower (protected) half carries the
guest-controlled RIPAS attribute; the upper (shared) half holds emulated MMIO,
virtio rings, and bounce buffers -- earlycon must live there.

RIPAS (Realm IPA State) has four values in the kernel's `enum ripas`: `EMPTY` (0),
`RAM` (1), `DESTROYED` (2), `DEV` (3). A guest converts `EMPTY -> RAM` to adopt
memory the host provisioned, or `RAM -> EMPTY` to return it -- without such a
request the RMM refuses host attempts to swap protected pages. That hand-shake is
a first-class architectural loop through the RMM.

## Realm Lifecycle, Measurement, and the Attestation Token

```text
  Host (NS EL2)                  RMM                          Realm guest
  --------------                 ---                          -----------
  RMI_GRANULE_DELEGATE g  -----> GTSI: NS -> Realm PAS
  RMI_REALM_CREATE(rd, params) -> RD built; RIM seeded from params
  RMI_DATA_CREATE, RMI_REC_CREATE, RMI_REALM_ACTIVATE
  RMI_REC_ENTER(rec) -----------> runs guest ---------> RSI_MEASUREMENT_EXTEND(i,..)
                                                        RSI_MEASUREMENT_READ(i)
                                                        RSI_IPA_STATE_SET(..)
                                                        RSI_ATTESTATION_TOKEN_INIT/_CONTINUE
  RMI_REALM_DESTROY -----------> undelegate granules, wipe RD/RECs
```

Two measurement structures drive attestation. The **Realm Initial Measurement
(RIM)** is, per the RMM specification, "a measurement of the configuration and
contents of a Realm at the time of activation" -- the analog of SNP's launch
digest; the RMM also maintains four **Realm Extensible Measurements (REMs 0-3)**
the running guest extends with `RSI_MEASUREMENT_EXTEND`. Token flow (kernel
guest driver `drivers/virt/coco/arm-cca-guest.c`): call `RSI_ATTESTATION_TOKEN_INIT`
with a 32-64 byte challenge, then loop `RSI_ATTESTATION_TOKEN_CONTINUE` pulling
up to 4 KiB per SMC while it returns `RSI_INCOMPLETE`. The signed token carries
the RIM, all four REMs, realm and RMM parameters, and platform identity; a relying
party checks it against expected measurements via a verifier such as Veraison
([project](https://github.com/veraison/veraison)); the generic challenge-quote-verify
pattern is covered in [confidential computing](../../security/advanced/confidential-computing.md#remote-attestation).

## CCA vs TDX and SEV-SNP

Same threat model -- untrusted hypervisor and host kernel -- three enforcement
points (TDX/SEV-SNP details: [confidential computing](../../security/advanced/confidential-computing.md)).
CCA is the only one of the three whose protection decision is made by a separate
architectural table below even the mediating firmware, and the only one designed
for realms and a TrustZone Secure world to coexist on one SoC; the flip side: CCA
shipped last, and its host-side kernel support is the least mature:

| Dimension | Arm CCA | Intel TDX | AMD SEV-SNP |
|---|---|---|---|
| Isolation anchor | GPC: GPT consult on every PA | TDX module in SEAM (alt VMX root) | RMP hardware page table |
| Memory integrity | GPT PAS tagging + RMM-owned RTT | Per-TD MKTME keys + module checks | RMP owner/GPA checks, PVALIDATE |
| Guest mapping control | Guest sets RIPAS via RSI | Guest accepts pages via TDG.* | Guest validates via PVALIDATE |
| Mediating firmware | RMM (EL2, Realm world), measured | TDX module (SEAMRR), signed | PSP firmware (AMD-rooted) |
| Attestation artifact | RSI token: RIM + REMs, RMM-signed | TD quote (MRTD etc.) via DCAP | VCEK-signed report from PSP |
| Hypervisor keeps | Scheduling, provisioning, destroy | Scheduling, provisioning | Scheduling, provisioning |
| Distinctive edge | Granule transitions; coexists with TrustZone TAs | Mature migration story | VMPLs; shipped first, at scale |

## Status on Armv9-A

- **Architecture.** RME (`FEAT_RME`) is part of the Armv9.2-A architecture extension
  (Arm ARM, DDI 0487, section A2.3.3); implementations may still omit it. The RMM
  spec **DEN 0137** reached its ratified **1.0-rel0** release in September 2024;
  2.0 drafts (2.0-bet3) decouple RMI and RSI versions.
- **Silicon.** As of mid-2026 no shipping server CPU implements RME: Arm's Neoverse
  S3 system IP is the first announced to support RME (enabling Neoverse V3-class
  cores), while NVIDIA's Grace, locked before CCA ratification, does not.
- **Software.** Guest-side realm support is mainline (arm-cca-guest driver,
  [kernel arm-cca page](https://docs.kernel.org/arch/arm64/arm-cca.html));
  host-side KVM realm support (Steven Price's series) reached v14 in May 2026 and
  is still landing. TF-RMM implements RMM 1.0; EDK2, TF-A, kvmtool, Veraison
  complete the stack.

## Gotchas

- Encryption is the *least* interesting part of CCA: realms without memory
  integrity are SNP-without-RMP all over again. The GPT answers "what if the host
  remaps a page?"
- A GPF is an abort *to EL3*, not to the faulting world's handler. Device access
  rides SMMU GPC configuration, and shared I/O pays the bounce-buffer tax --
  protected memory is not DMA-safe by magic.
- Attestation freshness comes from the 32-64 byte challenge plus verifier-side TCB
  checks; token retrieval is chunked at 4 KiB per SMC. The RMM is inside the TCB:
  pin its version -- RMM 1.0 vs 2.0 drafts change the RMI surface.

## Related

- [Confidential computing: TEEs overview](../../security/advanced/confidential-computing.md) | [Intel SGX](../../cryptography/intel-sgx.md) | [Kernel CC plumbing](../../linux/security/confidential-computing.md)
- [Arm architecture survey](../modern/arm.md) | [Embedded TEEs / TrustZone](../../linux/embedded/tee.md) | [KVM](../../linux/virtualization/kvm.md)

## References

- Arm, Realm Management Monitor specification (DEN 0137): https://developer.arm.com/documentation/den0137/
- Arm, Realm creation and attestation (CCA security plans, DEN 0127): https://developer.arm.com/documentation/den0127/300/Realm-management/Realm-creation-and-attestation
- Arm, Confidential Compute Architecture overview: https://www.arm.com/architecture/security-features/arm-confidential-compute-architecture
- Linux kernel documentation, Arm Confidential Compute Architecture: https://docs.kernel.org/arch/arm64/arm-cca.html
- TrustedFirmware-A, Granule Protection Tables Library design: https://trustedfirmware-a.readthedocs.io/en/latest/components/granule-protection-tables-design.html
