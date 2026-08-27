# Confidential Computing: TEEs and the Attack on Privileged Software

## The Data-State Gap

Security practice long rested on two pillars: encrypt data **at rest** (disk encryption)
and **in transit** (TLS/IPsec). Both leave a third state wide open: data **in use**,
decrypted in CPU registers and cache, where any code with enough privilege can read it.
On a cloud host that privileged list is long: hypervisor, host kernel, other tenants'
root users, platform firmware, management agents. Confidential computing closes the gap
in hardware: protect data in use by computing inside a hardware-based, attested Trusted
Execution Environment (TEE), per the definition used across vendor docs
([Azure](https://learn.microsoft.com/en-us/azure/confidential-computing/confidential-vm-overview)).
The adversary is not a network attacker -- it is **privileged host software**, the operator
of the machine you rent: insider misuse, compromised infrastructure tooling, co-tenant
kernel access -- threats disk encryption and TLS never touched.

## The Threat-Model Shift

Confidential VMs (CVMs) redraw the trusted computing base (TCB):

| Trust base | Classic VM | Confidential VM |
|---|---|---|
| Hypervisor, host kernel, other tenants | In TCB; reads all guest memory | Untrusted: still schedules and provisions, cannot read private memory |
| Platform firmware (SMM/UEFI) | In TCB | Reduced: measured, or parked behind a security controller |
| Physical DRAM contents | Plaintext | Ciphertext (per-VM or per-enclave key) |
| CPU package + TEE microcode | In TCB | In TCB (the new anchor; guest kernel + apps remain in TCB) |

The provider keeps manageability: the hypervisor still boots the VM, sizes memory,
schedules vCPUs, and emulates devices; confidentiality is enforced by the memory controller
and page tables. The cost: **trust moves from an operator to a manufacturer** -- silicon
plus a small attested firmware blob, verified remotely before key release.

## TEE Hardware Landscape

### Intel SGX: the enclave experiment

SGX (Skylake, 2015) protected at **application** granularity. Code partitioned into
*enclaves* ran on EPC (Enclave Page Cache) pages that the memory encryption engine
encrypted and integrity-protected; OS and hypervisor could evict EPC pages (per-page
MACs make eviction safe) but never read them. EPC was small (BIOS-capped, well under a
gigabyte on client parts) and applications had to be dismembered into trusted/untrusted
halves. The commercial verdict: client SGX retired with 11th Gen Core (2021), gone by
Alder Lake; Ice Lake-SP carried server SGX; Sapphire Rapids (2023) dropped it for TDX.
SGX remains essential history -- Foreshadow and SGX-STEP shaped how the industry reasons
about TEE side channels (see [microarchitectural attacks](microarch-attacks.md) and
[side channels](../../arch/advanced/side-channels.md)). Lesson: VM-granularity won -- unmodified guests -- but the tiny TCB was the adoption tax.

### AMD SEV -> SEV-ES -> SEV-SNP

AMD's ladder added one guarantee per generation, per the
[SEV-SNP whitepaper](https://www.amd.com/system/files/TechDocs/SEV-SNP-strengthening-vm-isolation.pdf):

| Step | Silicon | Guarantee added | Mechanism | Gap closed |
|---|---|---|---|---|
| SEV | EPYC 7001 (2017) | Memory confidentiality | Per-VM AES key selected by ASID; C-bit marks private pages | baseline |
| SEV-ES | EPYC 7002 (2019) | Register-state confidentiality | VMSA (guest register file) encrypted on VMEXIT; GHCB protocol for host communication | interrupt/exit register leaks |
| SEV-SNP | EPYC 7003 (2021) | Memory **integrity** | Reverse Map Table (RMP) records page owner, guest physical address, page size; PVALIDATE lets the guest confirm mappings | replay/relocation/aliasing by the hypervisor |

SEV alone had a famous hole: encryption defeats *reading*, not *relocation*. The
hypervisor cannot decrypt a page, but can hand the guest ciphertext claiming it belongs
at GPA X when it does not. SNP closes this with the RMP: hardware consults it on every
private-page access and raises a #VC fault on mismatch. SNP also adds VMPLs -- in-guest
privilege rings the hypervisor cannot reach.

### Intel TDX: trust domains

TDX is Intel's VM-granularity successor, shipping on 4th-gen Xeon server silicon (2023).
A **trust domain (TD)** is a VM whose private memory is encrypted with a per-TD key by
the MKTME engine and whose control plane is mediated by the **TDX module**, a signed
component running in SEAM (Secure Arbitration Mode) -- a CPU root mode that even SMM and
the VMM cannot inspect. The VMM stays a plain resource manager; hostile mapping changes
are caught by hardware. Intel's
[developer documentation](https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/overview.html)
specs the TDVMCALL interface, TD partitioning, and migration; the Linux side (KVM,
`arch/x86/coco/`, `cc_platform`) lives in
[the kernel CC page](../../linux/security/confidential-computing.md).

### Arm CCA: realms

Armv9-A's Confidential Compute Architecture adds a fourth world alongside
Secure/Normal/Root. *Realms* are dynamic VMs whose memory is protected by Granule
Protection Checks at every stage transition and by the SMMU for DMA, while a small
attested **Realm Management Monitor (RMM)** at EL2 in the Realm world manages realm
lifecycle and the normal-world hypervisor keeps provisioning control. Realms measure
themselves incrementally (RIM), a boot-measurement chain analogous to SNP's launch
digest. TrustZone's Secure world (see [embedded TEEs](../../linux/embedded/tee.md))
still exists; realms target datacenter VMs. Details:
[Arm CCA](https://www.arm.com/architecture/security-features/arm-cca).

### NVIDIA H100 CC mode: the AI twist

Model weights, training corpora, and inference prompts are secrets worth protecting from
the GPU-cloud operator renting you the accelerator. The Hopper H100 (2022) introduced a
confidential computing mode -- the first TEE-class protection on a shipping datacenter
GPU -- extended to Blackwell per [NVIDIA's CC documentation](https://docs.nvidia.com/confidential-computing/).
In CC mode the GPU boots fused and locked: HBM traffic is encrypted, the CPU-GPU path
(PCIe/NVLink) is protected end to end so the host cannot snoop activations, and hardware
firewalls between GPU engines make multi-tenant sharing defensible. Attestation is
CPU-less: the GPU produces a signed report verified via NVIDIA's Remote Attestation
Service, chainable to the host CVM's attestation. Keys live in GPU firmware, not the
host driver.

## Remote Attestation

Attestation answers one question: *why should I release my secrets to this chip?* Every
family implements the same pattern -- measurement, quote, verification:

1. **Measurement.** The platform hashes what it loads: SNP folds the launch image into a
   launch digest; TDX builds TD measurements (MRTD/MRCONFIGID); SGX extends
   MRENCLAVE-style registers; CCA derives the RIM.
2. **Quote generation.** The guest asks the hardware (or attested firmware) for a
   **quote**: measurements, the firmware/CPU security version (TCB version), a caller
   nonce for freshness, and user data -- signed by a device key (SGX EPID/DCAP key;
   SNP's VCEK with its AMD KDS certificate chain; TDX DCAP keys; the H100's device key).
3. **Verification.** The relying party checks the signature chain to the manufacturer
   root, the TCB version against an advisory feed, and measurements against policy for
   the exact expected image, then delivers secrets only over the established session.

```text
Generic attestation handshake (quote + verification + firmware measurement)

  Relying party                 Confidential VM                Platform HW/firmware
  (client / KMS)                (guest kernel + app)           (TEE root of trust)
        | 1. challenge (nonce)      |                                |
        |-------------------------->|                                |
        |                           | 2. request report(nonce)       |
        |                           |------------------------------->|
        |                           |   HW hashes firmware measurement + TCB version |
        |                           | 3. signed quote                |
        |                           |<-------------------------------|
        | 4. quote + nonce          |                                |
        |<--------------------------|                                |
        | 5. verify: chain -> vendor root; TCB vs advisory DB;        |
        |    measurement == expected image digest                     |
        | 6. OK: key exchange, secrets over encrypted session         |
        |<==========================================================>|
        |     (hypervisor sees only ciphertext and timing)            |
```

Two details decide whether attestation is security or theater: the nonce must be bound
into the quote and stale quotes rejected via TCB versions and revocation feeds; and
"signed by AMD" is weak policy -- the useful check is measurement equality with the
exact guest image. Extend order matters too, and the tamper check below is the point:
a hypervisor that swaps one boot stage cannot forge the token. Runnable, Python 3.12:

```python
import hashlib

def extend(prev: bytes, chunk: bytes) -> bytes:
    # TPM/TEE-style extend: new = H(prev || measurement)
    return hashlib.sha256(prev + hashlib.sha256(chunk).digest()).digest()

def boot_chain(stages):
    m = b"\x00" * 32                      # reset register value
    for name, blob in stages:
        m = extend(m, blob)
    return m

stages = [
    ("firmware", b"OVMF/TDVF stage 1 + stage 2"),
    ("kernel",   b"vmlinuz-6.x confidential-guest"),
    ("initrd",   b"initramfs with guest agent"),
    ("config",   b"cmdline: cc_platform=sev-snp"),
]
print("Boot measurement chain (extended register):")
for i, (name, _) in enumerate(stages):
    m = boot_chain(stages[: i + 1])
    print(f"  after {name:<9} {m.hex()[:32]}...")

nonce = b"session-nonce-7f3a"
token = hashlib.sha256(boot_chain(stages) + nonce).hexdigest()
recomputed = hashlib.sha256(boot_chain(stages) + nonce).hexdigest()
print(f"\nnonce: {nonce.decode()}")
print(f"attestation token: {token[:48]}...")
print("verifier recomputation matches:", token == recomputed)

tampered = stages[:-1] + [("config", b"cmdline: cc_platform=none")]
print("tampered image matches:", boot_chain(tampered) == boot_chain(stages))
```

Real output:

```text
Boot measurement chain (extended register):
  after firmware  2e3e7fc84d0e06550f5c0c2d294de66d...
  after kernel    6f2cb6b351cbbe31f9dc59a2ccad9026...
  after initrd    2b9088c44704c0fe1046f421e90d81ad...
  after config    c5d1502c22ef38d320fb957b9785e3bf...

nonce: session-nonce-7f3a
attestation token: 6b9b0abaf210ba03a3c6c08fa5a8c365626f4645a44d74f8...
verifier recomputation matches: True
tampered image matches: False
```

## What Confidential Computing Does NOT Protect

| Out of scope | Why | Partial mitigations |
|---|---|---|
| Microarchitectural side channels | Encryption protects DRAM, not cache/TLB/BTB state; transient-execution attacks repeatedly pierced SGX-class TEEs | Microcode + guest mitigations; [side channels](../../arch/advanced/side-channels.md), [microarch attacks](microarch-attacks.md) |
| Denial of service | The untrusted hypervisor still schedules vCPUs and can simply not run you; migration/HA was immature in early CVM stacks for the same reason (opaque guest state) | Redundancy across providers; SLAs (legal, not technical) |
| Traffic analysis / metadata | Page-fault patterns, message sizes, access timing leak structure | Padding, batching; oblivious RAM (expensive) |
| Invasive physical attacks | Probing the package or defeating key fuses is assumed infeasible, not impossible | Tamper-resistant parts, HSMs at the edges |
| Guest software bugs | SQLi inside an enclave is still SQLi | Standard application security |
| Guest-image supply chain | Attestation proves *what booted*, not that the image is sound | Reproducible builds, signed release pipelines |

## Guest-OS Tradeoffs

- **Private vs shared memory.** Guest pages are private by default; every DMA buffer the
  host must touch lives in shared memory reached via bounce buffers (SWIOTLB), with a
  page-state conversion (`set_memory_decrypted` + hypercall) per transition -- a copy
  plus conversion cost on I/O-heavy paths, and a SWIOTLB region of tens to hundreds of
  MiB (tunable via `swiotlb=`).
- **Device model and visibility.** Para-virtualized virtio with shared-memory rings is
  the norm; host-assisted kdump, hibernation, and host page sharing of private memory
  are unavailable by construction.
- **Performance envelope.** Encryption rides AES-NI-class engines, so steady-state
  overhead is low single digits; tails come from conversions and TLB effects.

Kernel-side mechanics live in [the kernel CC page](../../linux/security/confidential-computing.md).

## Deployment Landscape

| Provider | Offering | Hardware path | Notes |
|---|---|---|---|
| Azure | Confidential VMs (DCasv5 = SEV-SNP, ECasv5 = TDX) | AMD SEV-SNP; Intel TDX | NCC H100 v5 pairs H100 CC with CVMs |
| Google Cloud | [Confidential VMs](https://cloud.google.com/confidential-computing) / Confidential Space | AMD SEV and SNP-era EPYC; TDX rolling out | Confidential Space runs attested containers |
| AWS | [Nitro Enclaves](https://aws.amazon.com/ec2/nitro/nitro-enclaves/) | KVM/Nitro isolation from the parent instance | Not a memory-encryption TEE against the host |
| IBM / Oracle / Alibaba | SEV-SNP or TDX instances | vendor-dependent | Same attestation patterns |

The flagship use case is **key management**: a KMS or managed HSM with a *release
policy* refuses to hand over a key unless the requester presents a valid attestation
quote (right image, right TCB, right customer); the key then lives only inside the guest.
Azure's Always Encrypted with enclaves evaluates queries over encrypted columns inside
the database process this way. The recipe -- attested service + hardware-held key +
provider-blind storage -- composes with
[encrypted databases](../../dbms/advanced/encrypted-databases.md) and the HSM patterns
in [secrets management](../../linux/security/secrets-management.md).

## Failure Modes Checklist

- Attestation pinned only to the vendor root, stale TCB versions accepted without
  advisory checks, or secrets fetched before attestation completes -- all leak.
- SWIOTLB too small (cryptic DMA failures under load) or too large (memory pressure).
- Assuming migration/HA work unchanged -- they often do not yet.
- Expecting protection from billing-plane visibility or DoS: neither is in scope.

## Related

- [Kernel confidential computing](../../linux/security/confidential-computing.md) | [Embedded TEEs](../../linux/embedded/tee.md) | [KVM](../../linux/virtualization/kvm.md)
- [Microarchitectural attacks](microarch-attacks.md) | [Side channels](../../arch/advanced/side-channels.md) | [Secure Boot](../../linux/security/secure-boot.md)

## References

- AMD SEV-SNP whitepaper: https://www.amd.com/system/files/TechDocs/SEV-SNP-strengthening-vm-isolation.pdf
- Intel TDX developer documentation: https://www.intel.com/content/www/us/en/developer/tools/trust-domain-extensions/overview.html
- Arm Confidential Compute Architecture: https://www.arm.com/architecture/security-features/arm-cca
- NVIDIA Confidential Computing documentation: https://docs.nvidia.com/confidential-computing/
- Microsoft Learn, Azure Confidential VMs overview: https://learn.microsoft.com/en-us/azure/confidential-computing/confidential-vm-overview
