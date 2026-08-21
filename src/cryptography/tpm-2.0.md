# TPM 2.0 (Trusted Platform Module)

The Trusted Platform Module is the only consumer-facing cryptographic hardware that has truly shipped at scale — every business-class laptop since 2018, every Windows 11 machine by mandate, every Chromebook sold to enterprises, every modern server. Microsoft's TPM 2.0 requirement for Windows 11 put a TPM in roughly a billion devices. And yet the TPM is widely misunderstood. People think it is a smartcard glued to a motherboard, or an HSM, or a Windows feature. None of those is right.

The TPM is a **measured-boot and key-custody coprocessor**. Its job is to record, in a tamper-resistant and unforgeable way, what code ran on the host at boot, and to provide keys whose release is conditioned on those measurements. It is not for high-throughput cryptographic operations — most TPMs do tens of RSA signs per second. It is for *device identity*, *measured boot*, *sealing*, and *remote attestation* — i.e., for asking and answering the question "can we trust this host?". The Trusted Computing Group (TCG) publishes the specification; the latest is TPM 2.0 Rev 01.59 (2020).

## Discrete, Firmware, or Integrated?

A "TPM 2.0" can be one of three physical things, with very different threat profiles:

```
   +---------------------------+   +-------------------------------+
   |   Discrete TPM (dTPM)     |   |   Firmware TPM (fTPM)         |
   |   - separate chip on LPC  |   |   - runs in CPU's microcode   |
   |     or SPI bus            |   |     + isolated DRAM region   |
   |   - Infineon SLB9670,     |   |     (CSME on Intel, PSP on   |
   |     Nuvoton NPCT650,      |   |     AMD, or TrustZone TEE    |
   |     STMicro ST33J         |   |     on ARM)                  |
   |   - FIPS 140-3 L1 cert'd  |   |   - no separate silicon cost |
   |   - tamper-evident        |   |   - protected by CPU's TEE   |
   |   - hard to physically    |   |     (TrustZone or similar)   |
   |     attack                |   |   - vulnerable to attacks on |
   |                           |   |     the CPU/firmware         |
   +---------------------------+   +-------------------------------+

   +---------------------------+
   |   Integrated TPM (iTPM)   |
   |   - same silicon as a     |
   |     secure processor     |
   |     (e.g., Intel PTT     |
   |     integrated in ME)    |
   |   - similar threat model |
   |     to fTPM               |
   +---------------------------+
```

A discrete TPM (dTPM) is a chip from Infineon, Nuvoton, or STMicro plugged into the motherboard's LPC or SPI bus. The cryptographic operations happen *on the chip* and the keys are stored in the chip's internal EEPROM or battery-backed RAM. Physical attacks require either decapping the TPM package or exploiting the SPI/LPC bus — nontrivial but documented in the literature.

A firmware TPM (fTPM) is implemented in CPU microcode running inside an isolated memory region — the Intel Management Engine (ME / CSME) on Intel, the Platform Security Processor (PSP, an ARM core in the SoC) on AMD, or a TrustZone-based TEE on ARM Chromebooks. There is no separate chip. This is the cheapest option and what most consumer laptops actually have. Its trust reduces to "do you trust the Intel ME or AMD PSP not to be compromised?" — a question many security researchers answer with "no".

The two look identical to software: both implement the TPM 2.0 command interface (TSS — TCG Software Stack) over `/dev/tpm0` or `/dev/tpmrm0` (the resource manager device). The Linux `tpm2-tss` userspace library hides the distinction.

## PCRs: Platform Configuration Registers

The core primitive of the TPM is the **PCR** — a 24 (TPM 1.2) or 24+ (TPM 2.0, with bank-level flexibility) "registers" of 256 bits each. PCRs are *append-only*: you cannot write a value into a PCR. You can only *extend* it: `PCR_new = SHA256(PCR_old || data)`. The initial value of every PCR is zero (or `00...01` for the privileged debug PCRs).

```
   Extend operation:
   +---------+      +-----+      +--------+      +---------+
   | PCR_i   |  ++  | data|  ->  | SHA256 |  ->  | PCR_i   |
   | (state) |      |     |      |         |      | (new)   |
   +---------+      +-----+      +--------+      +---------+
```

The PCR is a Merkle-tree-style accumulator: each extension is irreversible (you cannot undo a hash without knowing the prior state and the input data), and the final value uniquely identifies the *sequence* of extensions applied. Crucially, the TPM stores only the *current* PCR value — there is no built-in history. Software outside the TPM maintains a log of what was extended and when; the log itself is untrusted, because it can be verified against the final PCR value (every step in the log can be re-extended to check the final value matches).

Each PCR has a *usage policy* — some are resettable, some are not. The convention (per the TCG PC Client Platform Firmware Profile):

| PCR | Purpose | Resettable at runtime? |
|-----|---------|-------------------------|
| 0 | Firmware (UEFI/BIOS) boot measurements | No |
| 1 | Firmware configuration data | No |
| 2 | Option ROM code | No |
| 3 | Option ROM configuration | No |
| 4 | Boot loader (e.g., GRUB stage 1) code | No |
| 5 | Boot loader config / GPT | No |
| 6 | Host platform-specific (vendor use) | No |
| 7 | Secure Boot policy | No |
| 8-15 | OS measurements (kernel, initramfs, IMA logs) | Yes (only from locality 4 = kernel) |
| 16 | Debug | Yes (with restrictions) |
| 17-22 | DRTM (Dynamic Root of Trust for Measurement — late-launch TPM) | varies |
| 23 | Application-specific (e.g., VM IMC) | Yes |

The non-resettable property is what makes measured boot work: by the time the kernel boots, the firmware measurements (PCRs 0-7) are *frozen* — no software can change them. The OS gets to use PCRs 8-15 for its own measurements and can reset those at boot.

## Measured Boot

Measured boot is the act of extending PCR values with the hash of each piece of code or config *as it is loaded*, before control transfers to it. The sequence is:

```
   Power on
      |
      v
   +-----------------+
   | Boot ROM (on-   | --- extends PCR 0 with hash of itself +
   | chip, in CPU)   |     platform manifest (ACM on Intel)
   +-----------------+
      |
      v
   +-----------------+
   | UEFI firmware   | --- extends PCRs 0, 1 with its code
   | (flash, SPI)    |     and config
   +-----------------+
      |
      v
   +-----------------+
   | Option ROMs     | --- extend PCRs 2, 3 (NIC/GPU option ROMs)
   | (e.g., GPU, NIC) |
   +-----------------+
      |
      v
   +-----------------+
   | Boot loader     | --- extends PCRs 4, 5 with its code and
   | (GRUB, shim)    |     grub.cfg, kernel command line
   +-----------------+
      |
      v
   +-----------------+
   | Linux kernel + | --- extends PCRs 8-15 with kernel image,
   | initramfs       |     initramfs, kernel cmdline
   +-----------------+
      |
      v
   IMA (Integrity Measurement
   Architecture) at runtime
   extends PCRs 9-15 with hashes
   of every executable launched
   post-boot (e.g., systemd, nginx)
```

The result is that, at any time, the TPM's PCR values represent a cumulative hash of everything that has been measured — from CPU boot ROM through to the most recently `execve`'d binary (when IMA is enabled). Different boot = different PCR values. A modified `grub.cfg` or a different kernel image produces a measurably different set of PCR values.

## Sealing and Unsealing

The killer feature of the TPM, the one that makes the PCR concept actually useful, is **sealing**. You can store an arbitrary secret (say, a disk-encryption key) inside the TPM, conditioned on the *current PCR values* matching an expected state. The TPM will refuse to release the secret unless the PCR state at unseal time matches the policy.

```
   Seal (at provisioning time, with a known-good PCR state):
   ----
   TPM2_Create( parentHandle = SRK_handle,
                inSensitive = { dataUser: disk_key },
                inPublic = { type: keyedhash,
                              nameAlg: SHA256,
                              objectAttributes: fixedParent |
                              fixedTPM |
                              adminWithPolicy,
                              authPolicy = PolicyPCR(
                                  PCR_selection = {9, 10, 11},
                                  expected_digest = current_digest) } )
   => returns the sealed "key blob" (public + encrypted private)
       to the host. Store this on disk.

   Unseal (at boot time, with current PCR state):
   ----
   TPM2_Load( parentHandle = SRK_handle, sealed_blob )
       => returns an object handle in the TPM
   TPM2_PolicyPCR( session, PCR_selection={9,10,11},
                   current_digest )
       => asserts in the session that PCRs match
   TPM2_Unseal( session = policy_session, objectHandle )
       => returns disk_key ONLY IF the policy holds
       => returns TPM_RC_POLICY_FAIL if PCRs differ
```

If an attacker boots from a different boot loader, modifies the kernel, or replaces the initramfs, *at least one* PCR will differ from the expected digest. The policy fails, the unseal refuses, and the disk key is not released — full-disk-encryption keys (LUKS, BitLocker) remain sealed.

This is how BitLocker, LUKS with `tpm2` support, and `systemd-cryptenroll --tpm2-device` work. The disk-encryption key is sealed to the TPM, conditioned on the expected boot state, and Windows / Linux unlocks the disk at boot *only if the boot was measured to be unmodified*.

The same primitive is used in confidential VMs (e.g., Azure Confidential VMs, AWS Nitro Enclaves) to bind VM image secrets to the host's attested boot state.

## Key Hierarchy

The TPM has a structured key hierarchy rooted in three permanent keys:

```
                  +-----------------------+
                  | Endorsement Key (EK)  |   <- unique per TPM,
                  | RSA-2048 or ECC-NIST  |      created at manufacture,
                  | persistent at index   |      certified by vendor
                  | 0x81010001            |      (EK certificate in
                  +----------+------------+      NV RAM)
                             |
                             |  restrictively
                             |  "unseals" to EK
                             v
                  +-----------------------+
                  | Storage Root Key (SRK)|  <- created by the
                  | RSA-2048 or ECC       |     "Take Ownership"
                  | persistent at index   |     command, owned by
                  | 0x81000001            |     user/admin
                  +----------+------------+
                             |
                             |  parent for
                             |  all other keys
                             v
                       +------------------+
                       | Sealed blobs,   |  <- arbitrary user keys,
                       | signing keys,   |     loaded into the TPM
                       | storage keys    |     on demand
                       | EK, AIKs        |
                       +------------------+
```

- **EK (Endorsement Key)**: The TPM's identity. Generated at manufacture time, the EK private key never leaves the TPM. The EK public key has a vendor-issued certificate (stored in NV RAM) that says "this EK lives on a genuine TPM from manufacturer X". This is how you prove you're talking to a real TPM, not a software emulator. The EK is the privacy-sensitive key — it is unique per chip and so permits tracking. Privacy-respecting protocols therefore don't *use* the EK for signing; they use an Attestation Key *certified* by the EK.
- **SRK (Storage Root Key)**: Created when the user takes ownership of the TPM (`TPM2_CreatePrimary` with a user-supplied auth value). The SRK is a storage key — it wraps other keys. Setting a new SRK effectively "wipes" the TPM (the old sealed blobs can't be unwrapped without the old SRK), although the EK and TPM state are unchanged.
- **AIK (Attestation Identity Key)**: A signing key used for attestation quotes. It is *certified* by the EK (via a `MakeCredential` / `ActivateCredential` protocol involving a privacy CA — the verifier learns the AIK is bound to a genuine TPM but not which one), so it provides signing without leaking the EK.

## Remote Attestation

A remote party can verify a host's boot state using a **TPM Quote**. The verifier:

1. Sends a random nonce (a challenge).
2. The host asks the TPM: `TPM2_Quote(signingKey = AIK, PCRselect = {0,1,...,15}, nonce)`.
3. The TPM signs `{ PCR_digest, nonce, TPM clock info }` with the AIK.
4. The host sends the signature + the PCR replay log to the verifier.
5. The verifier checks the AIK's certificate chain (back to a TPM vendor CA).
6. Re-computes the expected PCR digest from the replay log and the nonce.
7. Verifies the signature.

```
   Verifier                              Attestee (host)
   --------                              ----------------
   1. nonce = random(128 bit)             |
   2. {nonce, PCRselect}            ->    3. TPM2_Quote(AIK, PCRselect, nonce)
                                          - TPM hashes selected PCRs into
                                            digest = H(PCR0 || PCR1 || ...)
                                          - signs {digest, nonce, clock_info}
                                            with AIK private
                                          - returns signature + PCR_log replay
   7. verify AIK certificate               6. {sig, PCR_log}               ->
      chain back to vendor CA
   8. re-hash PCR_log to check that
      it produces the same digest
      that was signed
   9. check nonce == sent nonce
   10. compare digest to expected
       known-good measurements
```

The nonce prevents replay. The clock info (tick count, reset count) prevents roll-back of TPM state. The AIK cert chain proves the signature came from a real TPM. The PCR_log replay tells the verifier *what* was measured.

Production use cases: Microsoft Azure Attestation, AWS Nitro Attestation, the Linux `keylime` project, and confidential-container policies in Kubernetes.

## Comparison to HSM

| Property | TPM 2.0 | HSM (PKCS#11 Level 3) |
|----------|---------|------------------------|
| Primary use | Device identity, measured boot, sealing | Key operations at scale (RSA sign, TLS termination) |
| Throughput | 10-100 ops/s typical | 1,000-50,000 ops/s |
| Per-device identity | Yes (EK + AIK + cert chain) | Sometimes (vendor-specific) |
| FIPS 140-3 level | Usually L1 (fTPMs), L1-2 (dTPMs) | L3 or L4 |
| Cost | $1-3 (integrated) | $700-$50,000+ |
| Threat model | Software attacker on host; physical attacker is mostly out of scope | Physical attacker explicitly in scope (tamper-responsive L4) |
| TCB | TPM firmware + motherboard wiring | HSM firmware + tamper sensors |
| Tamper resistance | Mostly tamper-evident (dTPM only) | Tamper-responsive — keys zeroized on attack |
| Remote attestation | Built-in (Quote protocol, AIK) | Vendor-specific or absent |

The key insight: **a TPM is for "is this the device I think it is, in the state I expect?" and an HSM is for "perform this cryptographic operation safely."** A TPM might be the root of trust that loads a key *into* an HSM at boot; the HSM then performs the actual signing throughput. They are complementary, not competing.

## Common Pitfalls

1. **Trusting an fTPM as if it were a dTPM.** The fTPM is only as secure as the management engine it runs in. If the Intel ME or AMD PSP is compromised (and there have been ME vulnerabilities — CVE-2017-8694, CVE-2019-0090, etc.), the fTPM's keys are compromised. For high-assurance deployments, use a discrete TPM and disable the fTPM.

2. **Forgetting to clear the TPM after deploying.** A new laptop may have a TPM with EK but no SRK owner — fine, but if a previous owner set a password on the SRK (or on the EK), the new owner cannot use it without a `TPM2_Clear` with the previous password. Windows handles this with "Reset TPM" via MDM, but Linux admins sometimes hit this on repurposed hardware.

3. **Not refreshing PCR policies when the kernel/initramfs is updated.** A common breakage: a kernel update changes PCR 11 (kernel image), the sealed disk-encryption key no longer unseals, and the laptop fails to boot. Solutions: (a) `systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=0+1+2+3+4+5+7+9` after each kernel update, (b) seal to a smaller PCR set (just 7 = Secure Boot policy) so kernel updates don't break the seal but Bootloader tamper does, (c) set up `sbctl`-based recovery keys.

4. **Storing the recovery key on the same disk it unlocks.** BitLocker's "recovery key saved to file" feature has been used to defeat whole-disk encryption on stolen laptops — the recovery key sits in `Documents/BitLocker Recovery Key.txt`. Store it offline (printed) or in a separate TPM-sealed secret.

5. **Trusting PCR replay logs without re-verifying.** The PCR log (TCG Event Log, binary format with `EV_*` event types) is untrusted data. Always re-hash every entry and confirm the final digest equals the PCR value from `TPM2_Quote`. A malicious host could forge a log that "explains" any PCR value — only the signature binds the digest to the actual TPM state.

6. **Forgetting that locality matters.** TPM localities (0-4) are privilege levels — locality 4 is "in-kernel" on Intel. Some operations (resetting PCRs 17-22, certain DRTM commands) require specific localities. Code that tries to reset PCRs from userspace fails because userspace runs at locality 0.

## References

- Trusted Computing Group, "[TCG TPM 2.0 Specification, Revision 01.59](https://trustedcomputinggroup.org/resource/tpm-library-specification/)" (2020)
- Trusted Computing Group, "[PC Client Platform Firmware Profile](https://trustedcomputinggroup.org/resource/pc-client-specific-platform-firmware-profile-specification/)"
- Microsoft, "[TPM Fundamentals](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/tpm-fundamentals)"
- Microsoft, "[TPM 2.0 Provisioning and Windows](https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/tpm-operations-for-it-pros)"
- tpm2-tss project, "[tpm2-tss: TPM 2.0 Software Stack](https://github.com/tpm2-software/tpm2-tss)"
- Linux kernel, "[TPM driver documentation](https://docs.kernel.org/driver-api/tpm/tpm.html)"
- systemd, "[systemd-cryptenroll manual](https://www.freedesktop.org/software/systemd/man/systemd-cryptenroll.html)" — TPM2 integration for LUKS
- Kenneth Goldman et al., "[Practical Guide to TPM 2.0 (book)](https://link.springer.com/book/10.1007/978-1-4302-6584-9)" (Apress, 2016) — written by TPM 2.0 architects
- J. Wertheimer, "[TPM 2.0 Attestation with Azure](https://learn.microsoft.com/en-us/azure/security/fundamentals/attestation)"
- Keylime project, "[Keylime: TPM-based Boot Attestation](https://keylime.dev/)" — Linux Foundation open-source attestation framework
