# ARM TrustZone — The ARM Security Extension

ARM TrustZone is the security architecture that has shipped in essentially every ARM Cortex-A application processor since the Cortex-A8 in 2005. Where Intel SGX takes a *per-enclave* approach (each process carves out a private encrypted region), TrustZone takes a *per-SoC* approach: every CPU core has a bit that decides whether it is currently executing in the **Normal World** (the untrusted OS) or the **Secure World** (the trusted OS). Memory, peripherals, interrupts, and even external bus transactions are partitioned by that bit. The hardware guarantees that the Normal World cannot read or write Secure World memory, cannot access Secure peripherals, and cannot directly switch into Secure World code — it must go through a tightly controlled gate.

The result is a chip-level TEE (Trusted Execution Environment) that runs an entirely separate operating system — typically **OP-TEE** (the Linaro-led open-source TEE), **Trustonic Kinibi**, **Qualcomm QSEE**, or **Huawei TrustOS** — alongside Android/Linux. The Secure World holds trusted applications (TAs) for fingerprint matching, key storage, DRM key exchange, mobile-payments token signing, secure boot, and (on iPhones) the Secure Enclave. TrustZone is the substrate of mobile device security.

## The Two-World Model

The Secure / Normal world split is enforced throughout the SoC by a single bit: the **NS (Not Secure) bit**. The NS bit lives in the system control coprocessor registers (e.g., `SCR_EL3.NS`), in the MMU translation table descriptors, in the AXI/AHB bus transactions as an AxPROT bit, and in the cache and TLB tags.

```
   +----------------------------------------+
   |  CPU core (Cortex-A78, A710, X-series) |
   |                                        |
   |  Current state: NS bit = 0 or 1        |
   |                                        |
   |  +-----+    +-----+    +-----+         |
   |  | EL0 |    | EL1 |    | EL2 |  EL3   |
   |  |user |    |kern |    |hyp  |  mon    |
   |  +-----+    +-----+    +-----+  +-----+
   |   |          |           |       |
   |   +----------+-----------+-------+
   |                     |
   |              +------v--------+
   |              | Translation   |
   |              | table walk   |
   |              | (uses NS bit) |
   |              +------+--------+
   |                     |
   +---------------------|---------------+
                         |  AXI/AHB bus
                         v
   +------------------------------------------------+
   |  SoC interconnect (NIC-400 / CCI / CMN)         |
   |  - checks AxPROT[1] (NS bit)                   |
   |  - routes to Secure or Normal TZPC ports        |
   +-------------+----------------+-----------------+
                 |                |
   +-------------v----+   +-------v-------------+
   | Secure RAM / ROM |   | Normal RAM (DDR)   |
   | (only NS=0 sees) |   | (both worlds see)  |
   +-------------------+   +---------------------+

   +-------------------------+
   |   TZPC (TrustZone        |   TrustZone Protection
   |   Protection Controller) |   Controller: hardware
   |   - per-region NS policy|   firewall that marks which
   |   - peripheral NS bit    |   peripherals and memory
   |     (e.g., crypto engine|   regions are Secure-only.
   |     is NS=0)             |
   +-------------------------+
```

### Exception levels and the NS bit

ARMv8-A defines four privilege levels — Exception Levels 0, 1, 2, 3 — and a separate dispatch mechanism called **Exception Level 3** (the Secure Monitor). They are not symmetric:

| EL | Typical code | World | Notes |
|----|--------------|-------|-------|
| EL0 | User applications | NS=1 (Normal) or NS=0 (Secure) | Apps in both worlds |
| EL1 | OS kernel (Linux in Normal, TEE OS in Secure) | both | The OS for that world |
| EL2 | Hypervisor (KVM, Xen, pKVM) | Usually NS=1 | Virtualization; can run a "secure hypervisor" in NS=0 |
| EL3 | Secure Monitor | always NS=0 | The *only* code that can switch world |

EL3 is unique: it executes in Secure World with NS=0 always. The Secure Monitor is a tiny firmware stub (part of **TF-A**, Trusted Firmware-A) whose entire job is to be a *dispatcher* between the worlds. When Normal World wants to call into Secure World, it issues an `SMC` (Secure Monitor Call) instruction; this traps to EL3 synchronously; EL3 looks at the call number, decides which Secure World handler to invoke, and switches the NS bit before returning.

### The SMC / HVC dispatch

Two synchronous exception instructions mediate transitions:

- `SMC #imm` (Secure Monitor Call): traps to EL3. Used by both worlds to invoke Secure Monitor services. The `imm` (immediate value) is a function code — convention is SMC calling convention v1.0+ from ARM document "SMC Calling Convention".
- `HVC #imm` (Hypervisor Call): traps to EL2. Used by a guest to call its hypervisor.

`SMC` is the gateway into Secure World. Every TrustZone-mediated service — reading an OTP fuse, calling the hardware crypto engine, provisioning a key into secure storage, asking for a hardware-unique ID — is invoked via an `SMC` with an agreed function ID, argument registers (`x1`-`x7`), and a return code.

## The Secure Monitor and TF-A

The **Trusted Firmware-A** (TF-A, formerly ARM Trusted Firmware) is the open-source reference implementation of the EL3 Secure Monitor. It is the first piece of code that runs after the SoC's boot ROM hands control to EL3, and its responsibilities include:

- Boot-time initialization of the secure state: setting up the TZPC, configuring the GIC (Generic Interrupt Controller) for secure interrupts,programming the SMMU (System MMU) for peripherals that need secure-only access.
- **SCMI / PSCI / SiP SMC handlers**: providing power state management (CPU on/off, hotplug, idle states), and SoC-vendor services (clock setup, fuse reading, secure peripherals).
- **Dispatcher**: routing an SMC to the Secure OS (OP-TEE) or to itself depending on the function ID namespace.
- **Measured Boot / ROTPK verification**: on some SoCs, TF-A verifies the signature of the BL33 (the normal-world bootloader) against a Root-of-Trust Public Key Hash (ROTPK) burned into eFuses.

The boot flow is layered:

```
   Boot ROM (on-chip, NS=0, hardware root)
            |
            v
   BL1  (TF-A's boot ROM stage; minimal, ROM-able)
            | reads ROTPK from eFuses, verifies BL2 signature
            v
   BL2  (TF-A's bootloader stage, in secure RAM)
            | loads and verifies all secure-world images
            | (BL31 monitor, BL32 TEE OS, BL33 normal bootloader)
            v
   BL31 (TF-A's EL3 monitor, lives in secure RAM forever)
            |
            +-----> BL32 (OP-TEE OS or vendor TEE, NS=0, EL1)
            |
            +-----> BL33 (U-Boot or GRUB or systemd-stub, NS=1, EL1)
                            |
                            v
                       Linux kernel (NS=1, EL1)
                            |
                            v
                       Userspace (NS=1, EL0)
```

The split between BL31 (the resident Secure Monitor) and BL32 (the Secure OS) is significant: BL31 is in the TCB forever, runs at EL3, and is small (typically 100-200 KiB of code). The Secure OS at BL32 is much larger — comparable in scope to a microkernel — and runs at EL1 in Secure World.

## OP-TEE: The Open-Source TEE OS

OP-TEE (Linaro, BSD-2-Clause licensed) is the most widely deployed open-source Secure World OS. It is structured as a microkernel:

```
   +---------------------------------------------+
   |        OP-TEE Secure World (EL1, NS=0)       |
   |                                             |
   |  +-----------+ +-----------+ +-----------+ |
   |  | TA: key   | | TA: DRM   | | TA: biomet| |
   |  | storage   | | key       | | matcher   | |
   |  +-----+-----+ +-----+-----+ +-----+-----+ |
   |        |              |              |     |
   |        +------+-------+------+-------+    |
   |               |              |            |
   |        +------v--------------v-------+    |
   |        |  OP-TEE Core (microkernel)  |    |
   |        |  - thread scheduler         |    |
   |        |  - TEE Internal API          |    |
   |        |  - secure storage (RPMB)    |    |
   |        |  - crypto subsystem (HWRNG,  |    |
   |        |    HW AES/RSA, or software)  |    |
   |        +--------------+---------------+    |
   |                       |                    |
   |               +-------v--------+           |
   |               | SMC dispatch   |           |
   |               +----------------+           |
   +-----------------------|---------------------+
                           | SMC (EL3)
   +-----------------------v---------------------+
   |  Linux kernel Normal World (EL1, NS=1)     |
   |  +-------------------------------------------+
   |  | tee.ko driver (drivers/tee/)             |
   |  |  -> /dev/tee[0-1] character devices      |
   |  +-----+-----------------------------------+
   |        |  ioctl / syscall
   |  +-----v---------+
   |  | libteec.so    |  Client Application
   |  | (userspace    |  (CA, NS=1, EL0)
   |  | TEE Client API)|
   |  +---------------+
   +---------------------------------------------+
```

The Linux kernel side is the **TEE subsystem** (`drivers/tee/`), introduced in Linux 4.12. It provides a vendor-neutral interface: userspace applications open `/dev/tee0` (or `/dev/teepriv0` for sessions opened with a `TEE_IOCTL_LOGIN` based on the application's UUID), invoke `TEE_IOC_OPEN_SESSION` / `TEE_IOC_INVOKE` ioctls, and the kernel marshals the arguments across an `SMC` into the Secure World. The TEE Core validates the calling application's identity (kernel-attested via the file's `struct file` and SELinux context, depending on login mode) and dispatches to the requested Trusted Application (TA) by UUID.

OP-TEE exposes two APIs:

- **TEE Client API** (GP-internal) — what a Normal World application (CA) uses, via `libteec`. Sessions are opened to a TA by UUID, parameters are passed as "memrefs" (pointers to shared memory) or "values" (small integers), and invocations are synchronous.
- **TEE Internal API** — what a TA uses internally to call the OP-TEE Core: secure storage, cryptographic primitives, arithmetic.

### Trusted Application lifecycle

TAs are signed ELF binaries loaded by the OP-TEE Core on demand. They have a strict security model:

- **Authentication**: the TA's signature must verify against a key in the OP-TEE root-of-trust (either embedded at build time, or stored in a hash in eFuses). Unsigned TAs can be allowed in debug builds but are disabled in production.
- **Identity**: each TA has a UUID. Sessions opened by a CA must specify the TA's UUID. OP-TEE supports per-TA access control: a TA can ask "what is the calling CA's identity?" via the login mechanism (`TEE_IOCTL_LOGIN_APPLICATION`, `_USER`, `_GROUP`, etc.).
- **Memory isolation**: TAs cannot read each other's memory, even within Secure World. OP-TEE's MMU configuration gives each TA a private address space.

## Secure Storage

OP-TEE provides a "secure storage" API (`TEE_CreatePersistentObject`, `TEE_WriteObjectData`) that persists TAs' secrets across reboots. Two backends are available:

- **RPMB partition**: stores data on the eMMC/ufs device's Replay Protected Memory Block partition. RPMB is a hardware protocol: writes are signed with a per-device HMAC key (provisioned at manufacturing into the SoC) and the eMMC enforces a strict monotonic counter, so an attacker who images the storage chip cannot roll back or forge writes. The actual stored bytes are AES-encrypted by the TEE using a key derived from a Hardware Unique Key (HUK) and a salt, so they are both integrity-protected and confidential.
- **SQL FS over REE (Rich Execution Environment) FS**: a less secure option where data is stored in Normal World files but encrypted + MAC'd by the TEE. Only confidentiality and integrity are guaranteed; rollback is *not* (an attacker who can write to Normal World storage can roll back). Suitable for non-critical data.

```
   TA: TEE_WriteObjectData(secret)
       |
       v
   OP-TEE Core:
       1. Derive key = KDF(HUK, "ss-enc", obj_id)
       2. AES-GCM encrypt the data -> ciphertext + tag
       3. Build RPMB write frame:
          - metadata (counter, write count)
          - HMAC-SHA256(key=RPMB_key, frame)
       4. SMC into RPMB driver (in EL3 or a secure
          MMC driver)
       5. eMMC verifies HMAC, increments counter,
          writes frame to RPMB partition
```

## Secure Key Generation

The HUK (Hardware Unique Key) is the root of all secure storage keys. It is *derived* at boot from per-SoC secrets — typically the SoC's OTP fuses — and never directly used; instead, OP-TEE uses key-derivation functions (`TEE_DeriveKey`) to create per-purpose subkeys. This pattern avoids key reuse across purposes.

For TAs that need asymmetric keys (e.g., a fingerprint matcher that needs to sign a "yes this finger matches" assertion for the Android `Keystore` API), the flow is:

1. The TA calls `TEE_GenerateKeyPair` — the key is generated inside OP-TEE using the SoC's HWRNG (true random number generator, usually a ring-oscillator TRNG on the SoC).
2. The key is persisted as a secure-storage object — encrypted with a key derived from the HUK.
3. Public key can be exported to Normal World; private key never leaves Secure World.
4. Sign operations go via `TEE_AsymmetricSign` — data is signed inside Secure World, signature returned.

Android's `Keystore` (the user-facing API) and Google's `Keymaster` / `KeyMint` HALs are wrappers around a TrustZone TA. The user's fingerprint key, their Face Unlock model, their payment app's HCE (Host Card Emulation) secrets — all live as OP-TEE objects behind SMC.

## Comparison to Intel SGX

The architectural differences are illuminating:

| Aspect | ARM TrustZone | Intel SGX |
|--------|---------------|-----------|
| Granularity | One Secure World per SoC | Per-enclave (process-isolated) |
| TCB size | TEE OS + TF-A + EL3 monitor (~1-2 MB) | The enclave itself (~tens of KiB typically) |
| DRAM encryption | Optional (TrustZone Address Space Controller — TZASC — gates access, does not encrypt) | Mandatory (MEE on every EPC page) |
| Threat model | Assumes Normal World (including kernel) is compromised; assumes physical attacker *cannot* probe DDR (only access-control, not encryption) | Assumes OS, hypervisor, BIOS, and physical DDR probing are all hostile |
| Attestation | Often a TBB (Trusted Board Boot) chain — firmware signatures; remote attestation is vendor-specific | Standardized (EPID / DCAP) |
| Side-channel exposure | Generally better — the Secure World has its own cache state but can share L1/L2; *no* speculative side channels reported at the same scale as SGX | Significant (Foreshadow, LVI, SGAxe) |
| Use case focus | Mobile, embedded, IoT, automotive | Servers (confidential computing), DRM, fintech |

The most important conceptual distinction: **TrustZone encrypts nothing**. It just *gates access*. The hardware root of TrustZone's confidentiality is the bus and memory firewall (TZPC + TZASC). If an attacker can physically probe DDR, on most TrustZone implementations they will see Secure World data in plaintext. SGX, by contrast, encrypts every EPC page in DRAM and is designed to resist a physical attacker with a logic analyzer. TrustZone is for software adversaries; SGX is also for physical adversaries.

This is why you will find SGX in cloud confidential computing (where you rent a server in someone else's rack and don't trust the operator with physical access) but TrustZone in mobile phones (where the device is in your pocket and physical probing is impractical for the threat model).

## Common Pitfalls

1. **Forgetting that DRAM is unencrypted by default.** On most SoCs, if an attacker can dump DRAM (via JTAG, via a glitch, via a cold-boot attack), they get Secure World data. Use a SoC with TZASC + on-die memory encryption (some newer Cortex-X3 designs add "Memory Tagging Extension" and DDR encryption options) if your threat model includes physical access.

2. **Pinning everything to a single TEE OS vendor's API.** The TEE Client API and TEE Internal API are GlobalPlatform standards — code to *those*, not to Qualcomm's or Trustonic's vendor extensions. If you write vendor-specific code, your TA won't run on the next phone with a different TEE.

3. **Storing secrets in REE FS backend by mistake.** The REE FS storage backend has no rollback protection. If you store a "fail-open" flag in REE FS, an attacker can roll it back. Use RPMB for anything where freshness matters.

4. **Forgetting that RPMB has a single global counter.** All OP-TEE secure-storage objects share the same RPMB write counter. A poorly-designed rollback defense can be bypassed if an attacker can replay an older *TA's* frame alongside a newer one — the eMMC will accept any write whose counter is the expected next value. OP-TEE's design guards against this by chaining counters via a per-object "meta" hash, but custom code has to be careful.

5. **Assuming `TEE_IOCTL_LOGIN_APPLICATION` is sufficient authentication.** On Android, it ties the session to the calling app's package name + signing key, but on a regular Linux system the "application" is just the executable path or UID. On an open system, a privilege-escalated process can claim to be anyone. Use SELinux or AppArmor to constrain which SELinux contexts may open the TA's session.

6. **Ignoring the limited secure RAM.** Secure World typically has 1-16 MiB of secure RAM. A TA that allocates megabytes per session will exhaust it; symptoms are cryptic OOMs inside the TEE that look like hangs to a CA. Cap session memory.

## References

- ARM, "[ARM Security Extensions: ARMv8-A Architecture Specification](https://developer.arm.com/documentation/ddi0487/latest)" (DDI0487, the architecture reference manual)
- ARM, "[TrustZone Technology Overview](https://developer.arm.com/ip-products/security-ip/trustzone)" (developer page)
- Linaro / OP-TEE project, "[OP-TEE OS documentation](https://optee.readthedocs.io/)"
- Linaro, "[OP-TEE Linux kernel TEE subsystem documentation](https://www.kernel.org/doc/html/latest/staging/tee.html)"
- Trusted Firmware-A project, "[TF-A Documentation](https://tf-a.readthedocs.io/)"
- GlobalPlatform, "[TEE Client API Specification v1.0](https://globalplatform.org/specs-device/)"
- ARM, "[ARM Trusted Board Boot (TBB) requirements](https://developer.arm.com/documentation/1008328/latest)" — secure boot chain on top of TF-A
- Samsung / Linaro, "[RPMB: Replay Protected Memory Block spec](https://www.jedec.org/standards-documents/docs/jesd-b84-01)" (JEDEC eMMC standard, section on RPMB)
- ARM Community, "[SMC Calling Convention v1.5](https://developer.arm.com/docs/den0028/latest)" (DEN0028)
- Winter, Dietrich, "[TrustZone on ARMv8 — Survey and Side-Channel Analysis](https://www.usenix.org/conference/usenixsecurity18/presentation/winter)" (USENIX Security 2018 — academic survey of TrustZone's security surface)
