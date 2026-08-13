# IMA — Integrity Measurement Architecture

IMA (Integrity Measurement Architecture) is a Linux kernel security subsystem
that measures and appraises file integrity.  It is part of the Linux Integrity
Measurement Architecture (IMA/EVM) framework and was merged in kernel 2.6.30
(2009).  IMA ensures that files have not been tampered with by comparing their
cryptographic hashes against known-good values.

---

## 1. Overview

IMA operates in two complementary modes:

| Mode | Purpose |
|---|---|
| **Measurement** | Hash every file before execution/access; log hashes to the TPM (Trusted Platform Module) PCR. |
| **Appraisal** | Verify file integrity before allowing access; deny access if hash doesn't match. |

Together, these provide **remote attestation** (measurement) and **local
enforcement** (appraisal).

---

## 2. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   IMA Policy │     │  IMA Hooks   │     │  IMA Lists   │
│  (rules)     │────►│  (bprm_check,│────►│  (measure,   │
│              │     │   file_open, │     │   appraise)  │
│              │     │   mmap, etc.)│     │              │
└──────────────┘     └──────┬───────┘     └──────┬───────┘
                            │                     │
                            ▼                     ▼
                     ┌──────────────┐     ┌──────────────┐
                     │   TPM        │     │  xattr /     │
                     │  (PCR extend)│     │  signatures  │
                     └──────────────┘     └──────────────┘
```

### 2.1 IMA Hooks

IMA hooks are placed at strategic kernel points:

| Hook | Trigger |
|---|---|
| `bprm_check_security` | Before `execve()` |
| `file_open` | On `open()` |
| `file_free` | On file close |
| `mmap_file` | On `mmap()` |
| `kernel_read_file` | Kernel loading firmware/modules |
| `task_alloc` | On `fork()` |

Each hook checks the IMA policy and, if the file matches a rule, invokes
the measurement and/or appraisal actions.

---

## 3. IMA Policy

The IMA policy defines which files to measure/appraise and how.

### 3.1 Loading a Policy

```bash
# Load from userspace (requires ima_policy=appraise_tcb boot param or
# CONFIG_IMA_APPRAISE_BOOTPARAM=y)
echo "measure func=BPRM_CHECK" > /sys/kernel/security/ima/policy

# Or load from a file at boot via initramfs
ima-policy-load /etc/ima/ima-policy
```

### 3.2 Policy Syntax

```
# action condition [condition ...]
measure func=BPRM_CHECK uid=0
appraise func=FILE_CHECK fsmagic=0x9fa0
measure func=MODULE_CHECK uid=0
appraise fsmagic=0x9fa0
dont_appraise fsmagic=0x62656572
```

### 3.3 Policy Actions

| Action | Effect |
|---|---|
| `measure` | Hash the file and extend the TPM PCR |
| `appraise` | Verify the file's hash/signature |
| `dont_appraise` | Skip appraisal for matching files |
| `audit` | Log the access without integrity check |

### 3.4 Policy Conditions

| Condition | Meaning |
|---|---|
| `func=` | Hook function (BPRM_CHECK, FILE_CHECK, etc.) |
| `uid=` | Match user ID |
| `fsmagic=` | Match filesystem magic number |
| `fsuuid=` | Match filesystem UUID |
| `obj_user=` | Match SELinux user |
| `obj_role=` | Match SELinux role |
| `obj_type=` | Match SELinux type |
| `appraise_type=` | `imasig` (require signature) or `imasig\|imasig` (optional) |
| `appraise_flag=` | `appraise_flag=check_exec` (only on exec) |

### 3.5 Example Policies

**Measure all executed binaries:**
```
measure func=BPRM_CHECK
```

**Appraise all files on ext4 (magic 0xef53):**
```
appraise fsmagic=0xef53
```

**Measure and appraise firmware:**
```
measure func=KEXEC_KERNEL_CHECK
appraise func=KEXEC_KERNEL_CHECK
```

**Comprehensive TCB policy:**
```
# Measure and appraise all executed files
measure func=BPRM_CHECK
appraise func=BPRM_CHECK

# Measure all files opened for reading by root
measure func=FILE_MMAP mask=MAY_READ uid=0
measure func=MODULE_CHECK uid=0

# Appraise firmware
appraise func=FIRMWARE_CHECK

# Skip pseudo-filesystems
dont_appraise fsmagic=0x9fa0     # proc
dont_appraise fsmagic=0x62656572 # sysfs
dont_appraise fsmagic=0x64626720 # debugfs
dont_appraise fsmagic=0x01021994 # tmpfs
dont_appraise fsmagic=0x534f434b # sockfs

# Skip files owned by specific UIDs
dont_appraise uid=0
```

**Container-aware policy:**
```
# Measure files in containers
measure func=BPRM_CHECK fsmagic=0xef53
appraise func=BPRM_CHECK fsmagic=0xef53

# Skip tmpfs (container overlay)
dont_appraise fsmagic=0x01021994

# Measure kernel modules
measure func=MODULE_CHECK
appraise func=MODULE_CHECK
```

---

## 4. Measurement

### 4.1 How Measurement Works

```
file accessed → hook fires → IMA policy check
  → calculate hash (SHA-1, SHA-256, etc.)
    → extend hash into TPM PCR (usually PCR-10)
      → add entry to IMA measurement list
```

### 4.2 IMA Measurement List

The measurement list is accessible at:

```
/sys/kernel/security/ima/ascii_runtime_measurements
```

Each line contains:

```
<PCR> <digest> <template> <filename_hash> <filename>
10 6c3a... sha256:ac3b... ima-buf evaled;file_hash;...
```

### 4.3 Templates

| Template | Fields |
|---|---|
| `ima` | pcr, digest, name |
| `ima-ng` | pcr, digest (algo:hash), name |
| `ima-sig` | pcr, digest, name, signature |
| `ima-buf` | pcr, digest (of buffer), name, data |
| `ima-modsig` | pcr, digest, name, modsig |

### 4.4 Runtime Measurement Verification

```bash
# View measurement count
cat /sys/kernel/security/ima/runtime_measurements_count

# Search for specific file in measurement log
grep "/usr/bin/ls" /sys/kernel/security/ima/ascii_runtime_measurements

# Verify measurement against expected hash
EXPECTED_HASH="abc123..."
ACTUAL_HASH=$(grep "/usr/bin/ls" /sys/kernel/security/ima/ascii_runtime_measurements | awk '{print $2}')
if [ "$EXPECTED_HASH" = "$ACTUAL_HASH" ]; then
    echo "Integrity verified"
else
    echo "INTEGRITY VIOLATION"
fi
```

---

## 5. Appraisal

### 5.1 How Appraisal Works

```
file accessed → hook fires → IMA policy check (appraise)
  → read security.ima xattr from file
    → if signature: verify signature against file hash
    → if hash: compare stored hash with calculated hash
      → if match: allow access
      → if mismatch: deny access (EACCES or module load failure)
```

### 5.2 Extended Attribute: `security.ima`

The integrity hash or signature is stored in the `security.ima` extended
attribute:

```bash
# View the IMA xattr
getfattr -n security.ima /usr/bin/ls

# Sign a file
evmctl ima_sign --key /path/to/privkey.pem /usr/bin/ls

# Sign with specific hash algorithm
evmctl ima_sign --hashalgo sha256 --key /path/to/privkey.pem /usr/bin/ls

# Verify signature
evmctl ima_verify --key /path/to/x509_cert.pem /usr/bin/ls
```

### 5.3 Appraisal Types

| Type | Description |
|---|---|
| Hash-based | `security.ima` contains the SHA-256 hash |
| Signature-based | `security.ima` contains a digital signature |
| modsig | Module signature embedded in the file itself |

Signature-based appraisal is preferred because the hash can be forged by an
attacker who can write xattrs.  Signatures require the private key.

### 5.4 Appraisal Modes

```bash
# Check current appraisal mode
cat /sys/kernel/security/ima/policy

# Boot parameters:
# ima_appraise=enforce   - deny access on integrity failure
# ima_appraise=log       - log but allow (for testing)
# ima_appraise=fix       - write new hashes automatically
# ima_appraise=off       - disable appraisal
```

### 5.5 Signing Files for IMA

```bash
#!/bin/bash
# Sign all binaries in /usr/bin for IMA appraisal

KEY="/etc/keys/ima-private.pem"

find /usr/bin -type f -executable | while read file; do
    evmctl ima_sign --hashalgo sha256 --key "$KEY" "$file" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Signed: $file"
    fi
done

# Sign kernel modules
find /lib/modules/$(uname -r) -name "*.ko" -type f | while read mod; do
    evmctl ima_sign --hashalgo sha256 --key "$KEY" "$mod" 2>/dev/null
done
```

---

## 6. EVM — Extended Verification Module

EVM protects the **metadata** (xattrs, UID, GID, mode) of a file, while IMA
protects the **data**.

### 6.1 EVM Signature

EVM computes an HMAC over:

* `security.ima` (IMA hash/signature)
* `security.selinux` (SELinux label)
* File UID, GID, mode
* File size, inode number

The HMAC is stored in `security.evm`.

### 6.2 EVM Modes

| Mode | Boot Param | Behavior |
|---|---|---|
| Fix | `evm=fix` | Write new EVM HMACs automatically |
| HMAC | (default) | Verify EVM HMACs |
| Digital signature | `evm=signing` | Use RSA signature instead of HMAC |

### 6.3 IMA + EVM Together

```
security.ima  → protects file content (data)
security.evm  → protects file metadata (uid, gid, mode, xattrs)
```

Together they form a complete integrity solution: neither the file content
nor its metadata can be tampered with undetected.

### 6.4 EVM Key Management

```bash
# Load EVM trusted key
keyctl add trusted evm-key "new 32" @u

# Or load HMAC key
keyctl add user evm-hmac "$(head -c 64 /dev/urandom | xxd -p)" @u

# Initialize EVM
echo 1 > /sys/kernel/security/evm
```

---

## 7. Keys and Keyrings

### 7.1 IMA Keyrings

| Keyring | Purpose |
|---|---|
| `.ima` | Public keys for IMA signature verification |
| `.evm` | Public keys for EVM signature verification |

### 7.2 Loading Keys

```bash
# Load an IMA public key
keyctl padd asymmetric "" %ima < /path/to/x509.der

# Or via the kernel keyring
evmctl import /path/to/x509.der /etc/keys/x509_ima.der
```

### 7.3 Key Sources

* **Built-in kernel keyring** — compiled into the kernel
* **Machine Owner Key (MOK)** — from UEFI Secure Boot
* **Userspace-loaded** — via `keyctl` or init scripts

---

## 8. Integration with Other Subsystems

### 8.1 IMA + dm-verity

dm-verity protects the root filesystem at the block level.  IMA can then
measure/appraise files on top of the verified base.  dm-verity provides
the trust anchor; IMA provides per-file granularity.

### 8.2 IMA + SELinux

SELinux labels are protected by EVM.  The IMA policy can use SELinux
contexts as conditions:

```
measure func=FILE_CHECK obj_type=untrusted_t
appraise func=FILE_CHECK obj_type=exec_type
```

### 8.3 IMA + UEFI Secure Boot

The IMA policy can be loaded from a signed UEFI variable, ensuring that
the policy itself is trustworthy from boot.

### 8.4 Remote Attestation

The IMA measurement list, combined with TPM quotes, enables **remote
attestation**: a remote verifier checks the TPM's PCR values against the
measurement list to verify the integrity of the booted system.

```bash
# Generate TPM quote for remote attestation
tpm2_quote -c 0x81010001 -l sha256:10,11 -q "challenge" \
    -m quote.msg -s quote.sig -o quote.pcr

# Verify quote on remote system
tpm2_checkquote -u quote.pub -m quote.msg -s quote.sig -f quote.pcr -g sha256
```

### 8.5 IMA + systemd

systemd supports IMA for measuring and appraising service binaries:

```ini
# systemd service unit
[Service]
# systemd will measure binaries before execution
# IMA hooks fire automatically on execve()
ExecStart=/usr/bin/myapp
```

---

## 9. Performance Considerations

### 9.1 Hash Computation Overhead

Hashing every file adds latency.  Typical costs:

| Hash | Throughput | Per-file overhead |
|---|---|---|
| SHA-1 | ~2 GB/s | Minimal for small files |
| SHA-256 | ~1.5 GB/s | Slightly higher |
| SHA-512 | ~1 GB/s | Noticeable for large files |

### 9.2 Mitigation Strategies

* **Policy scoping** — only measure/appraise critical files.
* **`ima_policy=tcb`** — default policy measures executed files only.
* **Cache** — IMA caches the hash of already-measured files.
* **`fsname=` condition** — exclude fast filesystems (tmpfs).
* **`fsmagic=` condition** — skip pseudo-filesystems (proc, sysfs).

### 9.3 IMA Cache

IMA maintains an integrity cache of already-verified files:

```bash
# View IMA cache statistics
cat /sys/kernel/security/ima/stat
# lookups: 12345
# hits: 10000
# misses: 2345
```

---

## 10. Boot Parameters

| Parameter | Effect |
|---|---|
| `ima_appraise=` | `enforce`, `fix`, `log`, `off` |
| `ima_appraise_tcb` | Use the default "tcb" appraisal policy |
| `ima_policy=` | `tcb`, `appraise_tcb`, custom policy path |
| `ima_hash=` | Default hash algorithm (`sha256`, `sha1`) |
| `ima_template=` | Template name (`ima-ng`, `ima-sig`, etc.) |
| `evm=` | EVM mode (`fix`, `hmac`, `signing`) |
| `ima_tcb` | Enable the "tcb" measurement policy |
| `ima_policy=` | Path to custom policy file |

---

## 11. Debugging

```bash
# Check if IMA is enabled
cat /sys/kernel/security/ima/runtime_measurements_count

# View policy
cat /sys/kernel/security/ima/policy

# View measurement log
cat /sys/kernel/security/ima/ascii_runtime_measurements

# Check IMA xattr on a file
getfattr -n security.ima /path/to/file

# Check EVM xattr
getfattr -n security.evm /path/to/file

# Sign a file
evmctl ima_sign --hashalgo sha256 --key /etc/keys/privkey.pem /path/to/file

# Verify signature
evmctl ima_verify --key /etc/keys/x509_cert.pem /path/to/file

# Check IMA hash algorithm
cat /sys/kernel/security/ima/hash

# View IMA statistics
cat /sys/kernel/security/ima/stat

# Debug IMA with dynamic debug
echo "file security/integrity/ima/*.c +p" > /sys/kernel/debug/dynamic_debug/control
dmesg | grep ima
```

### Common Issues

```bash
# Issue: Appraisal denies access
# Check: Is file signed?
getfattr -n security.ima /usr/bin/app

# Issue: Signature verification fails
# Check: Is the signing key loaded?
keyctl list %ima

# Issue: EVM prevents metadata changes
# Check: Is EVM in fix mode?
cat /sys/kernel/security/evm
# Fix: boot with evm=fix to regenerate HMACs

# Issue: Policy not loaded
# Check: Is ima_policy= set in boot params?
cat /proc/cmdline | grep ima
```

---

## 12. Threat Model

| Attack Vector | IMA/EVM Defense | Limitation |
|---|---|---|
| Binary modification | IMA hash/signature check | Only checked on access |
| Metadata tampering | EVM HMAC/signature | Requires EVM keys loaded |
| Rootkit via module | MODULE_CHECK appraisal | Unsigned modules blocked |
| Firmware backdoor | FIRMWARE_CHECK | Must be in policy |
| Runtime memory patch | Not covered | Need lockdown mode |
| Boot-time tampering | TPM PCR + measurement list | Requires TPM |

---

## 13. Further Reading

* **Documentation: `Documentation/security/IMA/`**
* **LWN: [IMA and EVM](https://lwn.net/Articles/461237/)**
* **LWN: [Integrity management with IMA](https://lwn.net/Articles/311689/)**
* **Source: `security/integrity/ima/`**
* **Source: `security/integrity/evm/`**
* **tpm2-tools project for TPM interaction**
* **evmctl tool for signing files**
* **IBM: IMA/EVM walkthrough** — comprehensive setup guide

---

## 14. IMA Policy Examples for Production

### Server Hardening Policy

```
# /etc/ima/ima-policy
# Measure and appraise all executed binaries
measure func=BPRM_CHECK
appraise func=BPRM_CHECK

# Measure kernel modules
measure func=MODULE_CHECK
appraise func=MODULE_CHECK

# Measure firmware
measure func=FIRMWARE_CHECK
appraise func=FIRMWARE_CHECK

# Measure files opened for execution
measure func=FILE_MMAP mask=MAY_EXEC
appraise func=FILE_MMAP mask=MAY_EXEC

# Skip pseudo-filesystems
dont_appraise fsmagic=0x9fa0
dont_appraise fsmagic=0x62656572
dont_appraise fsmagic=0x64626720
dont_appraise fsmagic=0x01021994
dont_appraise fsmagic=0x534f434b
dont_appraise fsmagic=0x73636673
```

### Container Host Policy

```
# Measure and appraise container images
measure func=BPRM_CHECK fsmagic=0xef53
appraise func=BPRM_CHECK fsmagic=0xef53

# Skip tmpfs (container writable layers)
dont_appraise fsmagic=0x01021994

# Measure and appraise kernel modules
measure func=MODULE_CHECK
appraise func=MODULE_CHECK

# Appraise firmware
appraise func=FIRMWARE_CHECK
```

### Development/Testing Policy

```
# Log-only mode for testing
audit func=BPRM_CHECK
audit func=FILE_MMAP mask=MAY_EXEC

# Don't enforce appraisal
dont_appraise fsmagic=0xef53
```

## 15. IMA and Container Security

IMA can measure and appraise files inside containers:

```bash
# Mount container filesystem
mount -t overlay overlay -o lowerdir=/var/lib/docker/overlay2/lower,
  upperdir=/var/lib/docker/overlay2/upper,
  workdir=/var/lib/docker/overlay2/work /mnt/container

# Sign container binaries
find /mnt/container/usr/bin -type f -executable | while read f; do
    evmctl ima_sign --hashalgo sha256 --key /etc/keys/ima.pem "$f"
done

# IMA will measure/appraise when container executes these files
```

### Container Runtime Integration

```bash
# Docker with IMA
# Ensure container runtime passes files through IMA hooks
# Docker's default overlay2 driver triggers IMA hooks

# Podman with IMA
# Podman uses the same kernel interfaces
# IMA policy applies to containerized processes
```

## Cross-References

* [SELinux](./selinux.md) — MAC policy integration
* [dm-verity](../kernel/drivers/dm-verity.md) — block-level integrity
* [Secure Boot](./secure-boot.md) — UEFI trust chain
* LSM Framework — Linux Security Modules
* Keyrings — kernel key management
* [TPM](../kernel/security/tpm.md) — Trusted Platform Module
* [Kernel Lockdown](./lockdown.md) — kernel integrity enforcement
