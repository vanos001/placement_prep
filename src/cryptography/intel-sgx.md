# Intel SGX (Software Guard Extensions)

Intel SGX is the most consequential and most painful attempt to bring *enclave computing* to mainstream processors. First shipped in 2015 with Skylake, SGX lets a userspace process create a private memory region — an **enclave** — whose contents are encrypted by the CPU itself and inaccessible to any other code on the system, up to and including the operating system, the hypervisor, the BIOS, and a physical attacker with a logic analyzer on the memory bus. The threat model is unusual for hardware security: SGX assumes the entire host outside the package is hostile. The only thing it trusts is the package.

The intellectual lineage runs through XOM (Liebherr, 2003), AEGIS (Suh et al., 2003), and TrustLite (Costan et al., 2015), but SGX is the first TEE (Trusted Execution Environment) shipped in volume — billions of CPUs include it. The fact that it has since been undermined by side-channel attacks (Foreshadow in 2018, LVI in 2020, SGAxe in 2021) is the most important caveat in this page. SGX is real, deployed, useful, and partially broken — and Intel is still shipping it.

## The Enclave Model

SGX is a *process-context* TEE. The "trusted computing base" (TCB) for an enclave consists of:

- The enclave code itself (signed and measured at load time)
- The silicon implementing the SGX instructions and the Memory Encryption Engine
- The signing key Intel burned into the chip at manufacturing (the *root of trust*)

Notably *not* in the TCB:

- The OS kernel (Linux or Windows)
- The hypervisor (even a malicious VMM cannot read enclave memory, by design)
- The BIOS/UEFI firmware (post-EINIT)
- Other enclaves on the same machine
- The `MMU` page tables (the kernel controls VA->PA mapping but cannot decrypt)

This is structurally different from ARM TrustZone, where the TCB includes a separate OS running in Secure World. SGX is per-enclave; TrustZone is per-SoC.

### Enclave Page Cache (EPC)

SGX allocates a special region of DRAM, the **Enclave Page Cache**, that holds encrypted enclave pages. Each EPC page carries a 64-bit metadata field (in a separate **EPC Memory** structure stored in DRAM alongside) which includes:

- The page's *enclave ID* (the EID — the enclave it belongs to)
- The page type (REG, TCS, etc.)
- The virtual address the page was mapped at in the enclave (so the same ciphertext decrypts to different plaintext on different enclaves)
- A 56-bit integrity MAC over the page contents, plus an 8-bit version for replay protection

When a CPU core accesses an EPC page, the **Memory Encryption Engine (MEE)** transparently decrypts the line as it leaves the package to the L1 cache, and re-encrypts + updates the MAC as it writes back. The key is per-CPU-package and never leaves the package. Physically tapping the DDR bus reveals only AES-encrypted ciphertext — useless without the key.

```
   +---------------------------------------------------------+
   |                 CPU package (trusted)                   |
   |  +------------+   +-----------+   +-------------------+ |
   |  |  Core 0    |   |   Core 1  |   |   ... Core N      | |
   |  | (logical   |   | (logical  |   |                   | |
   |  |  memory    |   |   memory) |   |                   | |
   |  |   view)    |   |           |   |                   | |
   |  +-----+------+   +-----+-----+   +---------+---------+ |
   |        |                |                     |          |
   |        +-----------------+---------------------+          |
   |                          |                                |
   |                  +-------v--------+                       |
   |                  |   L3 / LLC    |                        |
   |                  +-------+-------+                        |
   |                          |                                |
   |                  +-------v--------+                       |
   |                  |  MEE (Memory  |                        |
   |                  |  Encryption   |                        |
   |                  |  Engine)      |                        |
   |                  |  - AES-128 CTR |                       |
   |                  |  - per-page    |                       |
   |                  |    MAC + nonce |                       |
   |                  +-------+-------+                        |
   +--------------------------|-----------------------------+
                              | encrypted on the bus
   +--------------------------v-----------------------------+
   |       DRAM (host — UNTRUSTED)                       |
   |   +-------------+    +-------------+                |
   |   | EPC page    |    | EPC page    |  ...           |
   |   | EID=7 MAC=..|    | EID=7 MAC=..|                |
   |   +-------------+    +-------------+                |
   +-----------------------------------------------------+
```

EPC is *scarce*. Skylake client chips shipped with 128 MiB; Xeon E3-1200 v5 gave 256 MiB and E-2100 doubled that. Server chips with SGX-2 (Ice Lake Xeon-SP and later) push EPC up to 1 TiB per socket, but most cloud instances ship with 64-256 MiB. Paging EPC pages to host RAM (swapping) is supported but slow and complicated — the MEE has to re-encrypt each page on every swap-in.

### Enclave Lifecycle and Instructions

SGX adds a small set of privileged ring-0 instructions (used by the OS driver) and a small set of ring-3 instructions (used by the application). The critical ones:

| Instruction | Mode | Purpose |
|--------------|------|---------|
| `ECREATE` | ring-0 (driver) | Allocate a new enclave in EPC, set initial measurement register |
| `EADD` | ring-0 | Add a page to the enclave, extending the measurement |
| `EINIT` | ring-0 | Finalize enclave, seal measurement to the launch enclave signature |
| `ERESUME` | ring-3 (asynchronous) | Re-enter enclave after an asynchronous exit (interrupt, exception) |
| `EENTER` | ring-3 (SGX-1) | Synchronous entry into the enclave |
| `EEXIT` | ring-3 | Exit the enclave, returning control to the untrusted host |
| `EACCEPT` | ring-3 (SGX-2) | Enclave accepts a page permission change from OS |
| `EMODPE` | ring-3 (SGX-2) | Enclave grows its own page permissions |
| `E TRACK` | ring-0 (SGX-2) | Force IPI to flush other cores' TLBs for a page |

The enclave measurement is a SHA-256 (actually an ERECSHA256, using an extended Merkle-tree form called *ERECSHA-256*) accumulator over every page loaded and every permission bit. `EINIT` finalizes this measurement into a `MRENCLAVE` value — effectively a cryptographic hash of the enclave's code + initial data + page permissions. `MRENCLAVE` is the key identity of the enclave; it is what attestation quotes against.

## Remote Attestation

Attestation is how a remote party verifies that "this enclave is genuinely running on real Intel SGX silicon with these exact bytes, and you can safely send it secrets". SGX has had two attestation architectures.

### EPID (Enhanced Privacy ID) — Legacy Attestation

The original model, used by SGX-1. The CPU contains a per-chip private key sealed inside an Intel-issued provisioning certificate. The flow:

1. The enclave derives an ephemeral *report key* and asks the CPU for a `REPORT` structure (a hash of `MRENCLAVE`, plus some caller data), signed with a report key.
2. A special Launch Enclave (a built-in enclave signed by Intel) co-signs the report, producing a *quote*.
3. The remote verifier sends the quote to Intel's Attestation Service over the network. Intel signs back an attestation that the quote came from genuine SGX silicon.
4. The verifier does a Diffie-Hellman with the enclave using a key derived from the report's `report_data` field — this gives an authenticated shared session key.

The crucial privacy property of EPID is *linkability grouping*. EPID is a group signature scheme: signatures from the same chip can be linked within a "linkage group" (by default, basename = host name), but cannot be linked across groups. Intel deliberately designed EPID so that a site cannot track a chip across services — privacy was treated as a first-class goal.

### DCAP (Data Center Attestation Primitives) — Modern Attestation

EPID has two problems: it requires a network round-trip to Intel, and it leaks (to Intel) that some chip attested. For data centers, neither is acceptable — cloud providers do not want every VM's attestation to ping Intel.

DCAP solves this by introducing a **Provisioning Certification Service (PCS)** running inside the data center. Intel provisions the chip with a per-chip certificate once, at install time. After that, attestation is *local* — the verifier talks to a quoting enclave on the same host, and to a local "cached" Intel certificate. No network call to Intel.

```
   Client (verifier)                  SGX host
   ----------------                  -------------------
   1. Request attestation     ---->  2. App calls sgx_qe_get_quote()
   3. <---- Quote (signed)          3a. Quoting Enclave (QE) signs
                                          the application enclave's
                                          REPORT with the chip's
                                          attestation key.
                                     3b. QE attaches the chip's
                                         provisioning certificate
                                         (cached from PCS).
   4. Verify quote signature          5. (Server fetches Intel CRL
      against cached Intel              and revocation list from
      CA chain + PCS.                   PCS once per ~1 day.)
   5. Verify MRENCLAVE matches
      the expected enclave hash.
   6. Derive shared key from
      REPORT_DATA via KDF.
   7. Send secrets to enclave
      over the established channel.
```

DCAP is what Azure, AWS, and GCP use. It also enables "collateral" — Intel periodically publishes revocation lists for vulnerable SGX versions (e.g., CVE-2018-3615 / L1 Terminal Fault), and the verifier must check those.

## Side-Channel Vulnerabilities

SGX's original security claims assumed the OS and other software were malicious but that the *microarchitecture* was benign. That assumption collapsed in 2018.

### Foreshadow (CVE-2018-3615, L1 Terminal Fault)

Foreshadow (the paper by Bulck et al., USENIX Security 2018) showed that an SGX enclave's data could be read via a speculative-execution attack through the L1 cache. A malicious OS marks an enclave page as not-present, then an attacker process issues a load that speculatively reads the enclave's L1-cached data *before* the page-fault handler fires. The speculatively read value can be exfiltrated via a Flush+Reload side channel. Foreshadow also broke the SGX launch enclave's seal key — meaning every SGX-1 chip on a vulnerable microarchitecture could have its attestation spoofed.

Intel patched with microcode updates that flush L1 on enclave entry and exit, but at a steep performance cost, and the patch was incomplete in some configurations.

### LVI (Load Value Injection, 2020)

LVI is Foreshadow in reverse: instead of reading enclave data out, an attacker can inject *crafted* values into enclave loads, causing the enclave to use attacker-controlled data during speculative execution. This is harder to exploit but broke the assumption that enclave-side code was safe to write without constant-time discipline. The fix was again microcode + compiler mitigations (LLVM and GCC added `-mlvi-cfi` style flags).

### SGAxe (2021)

SGAxe extended Foreshadow's successor (Foreshadow-NG) to read the *attestation keys* out of the Quoting Enclave. Since the QE holds the chip's attestation private key, breaking the QE effectively lets an attacker forge any attestation from that chip. This is what triggered the SGX-1 deprecation for most cloud use cases — Intel added SGX-2 with hardware mitigations, but the Attestation Service now checks microcode revocation for older chips.

### Practical impact

For most developers, the lesson is: SGX is useful but not bulletproof. SGX-2 (Ice Lake Xeon and later) addresses the worst Foreshadow-class bugs at the silicon level, but cache side channels (Prime+Probe, Flush+Reload) and memory-disambiguation attacks (Medusa, SmashEx) still require careful enclave code. SGX is best deployed with:

- The newest available silicon (SGX-2 / TGL+)
- All microcode patches applied
- Constant-time coding discipline inside the enclave
- A formally verified crypto library (MbedTLS, OpenSSL, or libcrux)
- Attestation with revocation checks (DCAP collateral freshness)

## The Confidential Computing Ecosystem

The Linux ecosystem around SGX is a stack of frameworks that try to make "write once, run in a TEE" practical:

```
   Application (unmodified)
        |
        v
   +-------------------------------+
   |  Confidential Containers      |   (Kubernetes operator,
   |  (CoCo, Kata + image          |    uses Kata Containers as the
   |   encryption + attestation)   |    pod runtime, mounts encrypted
   +---------------+---------------+    images, verifies quote
                   |                    before container start)
                   v
   +-------------------------------+
   |  Occlum / Gramine             |   (library-OS layer: re-implements
   |  "library OS" for SGX         |    file system, scheduler, network
   |                               |    stack *inside* the enclave)
   +---------------+---------------+
                   |
                   v
   +-------------------------------+
   |  Intel SGX SDK / Open Enclave |   (enclave loader, sign tool,
   |  SDK                           |    ECalls/OCalls glue)
   +---------------+---------------+
                   |
                   v
   +-------------------------------+
   |  Linux SGX driver             |   (intel_sgx kernel module;
   |  /dev/sgx_enclave              |    ECREATE/EADD/EINIT syscalls)
   +---------------+---------------+
                   |
                   v
                  SGX hardware (EPC + MEE)
```

- **Intel SGX SDK** is the low-level SDK — provides `sgx_create_enclave`, signing tools, ECalls (enclave calls, the trusted→trusted entry points) and OCalls (untrusted calls back to the host). You write the enclave in C/C++ and link against a `sgx_tstdc` libc shim.
- **Open Enclave SDK** (Microsoft, now also a CNCF project) is a portable alternative — same role as Intel SGX SDK but supports SGX and OP-TEE (ARM TrustZone).
- **Occlum** (Ant Group, open source) is a memory-safe library OS written in Rust that runs unmodified Linux binaries inside an SGX enclave — file I/O, syscalls, threads, even malloc all happen entirely inside the protected memory.
- **Gramine** (formerly Graphene, out of Stony Brook and U. of Tennessee) is similar — a library OS that lets you run unmodified Python/Redis/Spark inside SGX.
- **Confidential Containers (CoCo)** is a Kubernetes project that wraps the above into a pod-level abstraction — an operator deploys a pod whose container images are encrypted, the runtime verifies the host's attestation before pulling the image key, and the whole pod runs inside an SGX-protected Kata VM. Confirmed deployments: Azure Confidential VMs, GCP Confidential VMs.

## Comparison to Other TEEs

| Feature | Intel SGX | ARM TrustZone | AMD SEV-SNP | AWS Nitro Enclaves |
|----------|-----------|----------------|---------------|---------------------|
| Granularity | Per-enclave (process) | Per-SoC (whole world) | Per-VM | Per-VM (i.e., one big enclave) |
| Encrypts DRAM | Yes (MEE) | Optional (with TrustZone Address Space Controller) | Yes (SEV) | Yes (Nitro hardware) |
| Threat model | OS + hypervisor + DRAM attacker | Compromised Normal World only | Hypervisor compromised | Nitro hypervisor is trusted TCB |
| Attestation | EPID or DCAP | Platform-specific (often TBB-signed) | AMD SEV attestation report | Attestation Document (Nitro) |
| Side-channel history | Bad (Foreshadow, LVI, SGAxe) | Better (more isolated) | Mixed | Best (minimal surface) |
| Deployment scope | Cloud + on-prem | Mobile + embedded + cloud | Cloud (Epyc only) | AWS only |

## Common Pitfalls

1. **Believing the OS is your enemy but the microarchitecture is your friend.** It isn't. SGX-1 is compromised by Foreshadow-class attacks; you must assume side-channel-competent adversaries and write constant-time enclave code, or run on SGX-2 with all patches.

2. **Forgetting to verify the attestation quote's `MRENCLAVE` against the expected value.** A quote that says "this is a real SGX enclave" tells you *nothing* useful if the enclave code inside is malicious. The verifier must check `MRENCLAVE` against a hash they computed themselves, ideally from a reproducible build.

3. **Trusting the untrusted runtime for randomness.** The OS provides `getrandom()`/`/dev/urandom` to the enclave; the OS is malicious. SGX provides `RDRAND` (after SGX-2 patch), but you should also mix in `RDSEED` and any hardware randomness you can find. Use a vetted RNG.

4. **Side-channeling yourself via shared resources.** Inside the enclave, you share L1/L2/LLC with the OS and other enclaves. Writing a "secret" to a cache line and then measuring how long it takes to read it back is a trivial side channel. Treat cache-timing side channels as live threats.

5. **Forgetting OCall argument validation.** Every OCall (a call from the enclave back to the host) hands control to untrusted code. If your enclave passes a pointer to a buffer to the host, the host can race to modify it during the OCall. Validate every byte returning from an OCall.

6. **Shipping the wrong `MRSIGNER` policy.** Quoting Enclave policies can be `MRENCLAVE`-based (hash of the enclave code) or `MRSIGNER`-based (the signing key). The latter is more flexible (lets you ship new versions) but more brittle (revoking the key invalidates every version). Pick intentionally.

## References

- Costan, Ilia, Lebedev, Suh, "[Intel SGX Explained](https://eprint.iacr.org/2016/086.pdf)" (IACR ePrint 2016/086, 2016-2017) — the canonical academic survey.
- Intel, "[Intel SGX Developer Reference](https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/overview.html)"
- Intel, "[Intel SGX DCAP Architecture](https://download.01.org/intel-sgx/latest/dcap-latest/linux/docs/Intel_SGX_DCAP_Reference_Implementation_for_Linux.pdf)"
- Bulck, Minkin, Weisse, Genkin, et al., "[Foreshadow: Extracting the Keys to the Intel SGX Kingdom with Transient Out-of-Order Execution](https://foreshadowattack.eu/foreshadow.pdf)" (USENIX Security 2018)
- Van Bulck, et al., "[LVI: Hijacking Transient Execution through Microarchitectural Load Value Injection](https://lviattack.eu/lvi.pdf)" (IEEE S&P 2020)
- Van Bulck, Moreira, et al., "[SGAxe: How SGX Fails in Practice](https://www.sgxattack.com/)" (USENIX Security 2021)
- Intel, "[Intel SGX SDK on GitHub](https://github.com/intel/linux-sgx-driver)"
- Occlum project, "[Occlum: A Memory-Safe Library OS for SGX](https://github.com/occlum/occlum)"
- Gramine project, "[Gramine: A Library-OS for SGX and other TEEs](https://gramineproject.io/)"
- Confidential Containers, "[CoCo documentation](https://github.com/confidential-containers/documentation)"
- Linux Foundation, "[Confidential Computing Consortium](https://confidentialcomputing.io/)"
