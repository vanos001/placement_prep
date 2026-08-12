# Kernel Secrets Management

## Overview

The Linux kernel provides several mechanisms for managing cryptographic secrets: the **kernel keyring** for storing keys in kernel memory, **encrypted keys** that encrypt key material at rest, **dm-crypt** for full-disk encryption key management, and **TPM integration** for hardware-backed key storage.

These subsystems form the foundation of Linux security for encrypted storage, secure boot, and credential management.

> **See also:** [dm-crypt and LUKS](../kernel/drivers/dm-crypt.md), [Secure Boot](./secure-boot.md), [Keyring API](keyring.md)

---

## Kernel Keyring

### Architecture

The kernel keyring subsystem (`security/keys/`) manages cryptographic keys, authentication tokens, and other secrets. Keys are kernel-managed objects with lifecycle, permissions, and type-specific operations.

```
┌──────────────────────────────────────────┐
│              Userspace                    │
│   keyctl / add_key / request_key syscalls│
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│           Keyring Subsystem               │
│  security/keys/                          │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Key Types   │  │ Keyrings         │  │
│  │ - user      │  │ - thread         │  │
│  │ - logon     │  │ - process        │  │
│  │ - encrypted │  │ - session        │  │
│  │ - trusted   │  │ - user           │  │
│  │ - asymmetric│  │ - user_session   │  │
│  └─────────────┘  └──────────────────┘  │
└──────────────────────────────────────────┘
```

### Key Types

| Type          | Description                                     |
|---------------|-------------------------------------------------|
| `user`        | Arbitrary user-defined data (up to 32 KiB)      |
| `logon`       | Like `user` but not readable from userspace     |
| `encrypted`   | Encrypted key material (see below)              |
| `trusted`     | TPM-sealed keys                                 |
| `asymmetric`  | Public/private key pairs (X.509, PKCS#7)        |
| `keyring`     | Container for other keys                        |
| `big_key`     | Large data (>32 KiB), stored in tmpfs or encrypted |

### Keyrings

Every process has access to several keyrings:

| Keyring         | Scope                           | Accessed via              |
|-----------------|---------------------------------|---------------------------|
| Thread          | Current thread only             | `KEY_SPEC_THREAD_KEYRING` |
| Process         | All threads in process          | `KEY_SPEC_PROCESS_KEYRING`|
| Session         | All processes in session        | `KEY_SPEC_SESSION_KEYRING`|
| User            | All processes of the UID        | `KEY_SPEC_USER_KEYRING`   |
| User Session    | All sessions of the UID         | `KEY_SPEC_USER_SESSION_KEYRING` |
| Persistent      | Survives logout (per UID)       | `KEY_SPEC_PERSISTENT_KEYRING` |

### Syscalls

#### add_key()

```c
#include <linux/keyctl.h>
#include <sys/syscall.h>
#include <unistd.h>

key_serial_t add_key(const char *type, const char *description,
                     const void *payload, size_t plen,
                     key_serial_t keyring)
{
    return syscall(__NR_add_key, type, description,
                   payload, plen, keyring);
}

/* Example: add a user key */
key_serial_t key = add_key("user", "my-secret",
                            "password123", 11,
                            KEY_SPEC_SESSION_KEYRING);
```

#### keyctl()

```c
#include <sys/keyctl.h>  /* or linux/keyctl.h */

/* Read a key's payload */
char buf[4096];
long len = keyctl(KEYCTL_READ, key_id, buf, sizeof(buf));

/* Revoke a key */
keyctl(KEYCTL_REVOKE, key_id);

/* Clear a keyring */
keyctl(KEYCTL_CLEAR, keyring_id);

/* Link a key into a keyring */
keyctl(KEYCTL_LINK, key_id, keyring_id);

/* Set key timeout (auto-expire in N seconds) */
keyctl(KEYCTL_SET_TIMEOUT, key_id, 300);

/* Search for a key */
key_serial_t found = keyctl(KEYCTL_SEARCH, keyring_id,
                             "user", "my-secret", 0);

/* Invalidate a key (immediate removal) */
keyctl(KEYCTL_INVALIDATE, key_id);

/* Get keyring ID */
key_serial_t session = keyctl(KEYCTL_GET_KEYRING_ID,
                               KEY_SPEC_SESSION_KEYRING, 0);

/* Join a session keyring */
keyctl(KEYCTL_JOIN_KEYRING, "myring", 0, 0);
```

### keyutils Userspace Tool

```bash
# Add a key
keyctl add user my-key "secret-data" @s

# Read a key
keyctl print $(keyctl search @u user my-key)

# List keys in session keyring
keyctl list @s

# Set timeout (auto-expire in 60 seconds)
keyctl timeout $(keyctl search @u user my-key) 60

# Revoke a key
keyctl revoke $(keyctl search @u user my-key)

# Pipe key to a command
keyctl pipe $(keyctl search @u user my-key) | openssl dgst -sha256

# Create a named keyring
keyctl newring myring @u

# Link key to another keyring
keyctl link <key_id> <keyring_id>

# Show all keyrings
keyctl show
# Session Keyring
#  87654321 --alswrv  1000  1000  keyring: _ses
#  12345678 --alswrv  1000  1000   \_ user: my-key
```

---

## Encrypted Keys

### Concept

**Encrypted keys** are key types where the key material is encrypted at rest using a **master key** derived from either a user passphrase or a TPM. The encrypted blob can safely be stored on disk or in the kernel keyring.

### Format

```
<encrypted-key-blob> = format <type> <master-key-name> <encrypted-data>
```

Example: `encrypted aes128-64-cbc trusted:master-key 0a1b2c3d...`

### Creating Encrypted Keys

```bash
# Load the encrypted key kernel module
modprobe encrypted-keys

# Create a master key (trusted or user)
keyctl add user master-key "$(head -c 32 /dev/urandom | xxd -p)" @s

# Create an encrypted key using the master key
keyctl add encrypted my-enc-key "new trusted:master-key 32" @s

# The key is stored encrypted in the kernel keyring
keyctl pipe $(keyctl search @u encrypted my-enc-key) > /tmp/enc-key.blob
```

### Master Key Types

| Master Key Source | Security Level         | Use Case                |
|-------------------|-----------------------|-------------------------|
| `user:` type key  | Key material in RAM    | Development/testing     |
| `trusted:` type   | TPM-sealed             | Production systems      |

### Load from File

```bash
# Save encrypted key blob to persistent storage
keyctl pipe $(keyctl search @u encrypted my-enc-key) > /etc/keys/enc-key.blob

# Load it back later
keyctl add encrypted my-enc-key "$(cat /etc/keys/enc-key.blob)" @s
```

### Encrypted Key Use Cases

```bash
# Use encrypted key for dm-crypt
# 1. Create encrypted key
keyctl add encrypted disk-key "new 32" @s

# 2. Get key data for cryptsetup
keyctl pipe $(keyctl search @u encrypted disk-key) > /tmp/disk-key

# 3. Open LUKS volume with key
cryptsetup luksOpen /dev/sda1 mydisk --key-file=/tmp/disk-key

# 4. Securely delete temporary key file
shred -u /tmp/disk-key
```

---

## dm-crypt Key Management

### Overview

dm-crypt is the kernel's device-mapper target for **block-level encryption**. It manages encryption keys for LUKS volumes, loop devices, and raw partitions.

### Key Derivation

dm-crypt uses a **key derivation function** (KDF) to transform a passphrase into an encryption key:

| KDF              | Description                           |
|------------------|---------------------------------------|
| PBKDF2           | Traditional (LUKS1)                  |
| Argon2id         | Memory-hard (LUKS2, preferred)       |

### Key Slots (LUKS)

LUKS supports multiple key slots, allowing key rotation and recovery:

```bash
# Add a new key slot
cryptsetup luksAddKey /dev/sda1

# Remove a key slot
cryptsetup luksKillSlot /dev/sda1 0

# Dump LUKS header
cryptsetup luksDump /dev/sda1

# Change passphrase
cryptsetup luksChangeKey /dev/sda1

# Backup LUKS header (CRITICAL - losing this means losing data)
cryptsetup luksHeaderBackup /dev/sda1 --header-backup-file /backup/luks-header.img
```

### dm-crypt Key Types

```bash
# Passphrase-based (default)
cryptsetup luksFormat /dev/sda1

# Key file-based
dd if=/dev/urandom of=/root/keyfile bs=4096 count=1
chmod 600 /root/keyfile
cryptsetup luksAddKey /dev/sda1 /root/keyfile
cryptsetup luksOpen /dev/sda1 encrypted --key-file /root/keyfile

# TPM-bound key (via systemd-cryptenroll)
systemd-cryptenroll --tpm2-device=auto /dev/sda1

# FIDO2 key
systemd-cryptenroll --fido2-device=auto /dev/sda1

# Recovery key
systemd-cryptenroll --recovery-key /dev/sda1
```

### Volatile Keys

For testing or ephemeral volumes, dm-crypt supports volatile keys stored only in kernel memory:

```bash
# Create an encrypted volume with a random in-memory key
dmsetup create mycrypt --table "0 $(blockdev --getsz /dev/loop0) crypt aes-xts-plain64 /dev/urandom 0 /dev/loop0 0"
```

### Key Scrubbing

dm-crypt carefully scrubs key material from memory when not in use:

- Keys are stored in pinned kernel memory (not swappable)
- Key slots are zeroed on `cryptsetup luksClose`
- Emergency wipe: `cryptsetup erase /dev/sda1`

```bash
# Close encrypted volume (scrubs keys from memory)
cryptsetup luksClose mydisk

# Emergency key destruction
cryptsetup erase /dev/sda1
# WARNING: this makes data permanently inaccessible
```

> **See also:** [dm-crypt and LUKS](../kernel/drivers/dm-crypt.md)

---

## TPM Integration

### What is TPM?

A **Trusted Platform Module (TPM)** is a hardware security chip that:

- Generates and stores cryptographic keys
- Performs RSA, SHA, and HMAC operations
- **Seals** data so it can only be decrypted on the same platform state
- Provides a hardware random number generator

### TPM Versions

| Version | Kernel Driver      | Key Algorithm Support |
|---------|--------------------|-----------------------|
| TPM 1.2 | `tpm_tis`, `tpm`  | RSA only              |
| TPM 2.0 | `tpm_tis`, `tpm_crb` | RSA, ECC, HMAC    |

### Trusted Keys (TPM-Sealed)

**Trusted keys** are key types where the key material is sealed inside the TPM chip. The key can only be unsealed when the TPM's Platform Configuration Registers (PCRs) match the expected state.

```bash
# Create a TPM-backed trusted key
keyctl add trusted my-trusted-key "new 32" @s

# The key material never leaves the TPM
# It can only be unsealed on the same machine with the same PCR state
```

### PCR (Platform Configuration Registers)

PCRs store measurements of the boot chain:

| PCR  | Measures                          |
|------|-----------------------------------|
| 0    | BIOS/UEFI firmware                |
| 1    | BIOS/UEFI configuration           |
| 2    | Option ROMs                       |
| 3    | Option ROM configuration          |
| 4    | Boot loader (GRUB, systemd-boot)  |
| 5    | GPT partition table               |
| 7    | Secure Boot state                 |
| 8    | Boot loader commands              |
| 10   | IMA measurement list              |
| 14   | IMA policy                        |

### systemd-cryptenroll with TPM

```bash
# Enroll a LUKS volume with TPM2
systemd-cryptenroll --tpm2-device=auto \
                    --tpm2-pcrs=0+4+7 \
                    /dev/sda1

# The volume can now be unlocked without a passphrase
# when the boot chain matches the enrolled PCR values

# Enroll with PIN (two-factor)
systemd-cryptenroll --tpm2-device=auto \
                    --tpm2-pcrs=0+4+7 \
                    --tpm2-with-pin=true \
                    /dev/sda1

# List enrolled keys
systemd-cryptenroll /dev/sda1

# Wipe TPM enrollment
systemd-cryptenroll --wipe-slot=tpm2 /dev/sda1
```

### Kernel TPM Interface

```bash
# List TPM devices
ls /dev/tpm*

# TPM2 tools
tpm2_createprimary -C o -c primary.ctx
tpm2_create -C primary.ctx -u key.pub -r key.priv
tpm2_load -C primary.ctx -u key.pub -r key.priv -c key.ctx
tpm2_encryptdecrypt -c key.ctx -o encrypted.out plaintext.in

# TPM2 clear (factory reset - WARNING)
tpm2_clear

# TPM2 get random
tpm2_getrandom 32
```

### TPM in the Kernel

```c
#include <linux/tpm.h>

/* Access TPM from kernel module */
struct tpm_chip *chip = tpm_default_chip();
if (chip) {
    /* Use TPM operations */
    tpm_pcr_extend(chip, pcr_idx, hash);
}
```

---

## Integration Example: Full Stack

A complete secrets pipeline combining all mechanisms:

```
┌─────────────────────────────────────────────────────┐
│  TPM Hardware                                        │
│  ┌──────────────────────────────────────────────┐  │
│  │ 2048-bit RSA key (sealed)                    │  │
│  │ PCR measurements                             │  │
│  └──────────────────────────┬───────────────────┘  │
└─────────────────────────────┼───────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────┐
│  Kernel Keyring Subsystem                           │
│  ┌──────────────────────────────────────────────┐  │
│  │ trusted:tpm-master-key (TPM-backed)          │  │
│  │   └─► encrypted:disk-key (AES-256)           │  │
│  │       └─► Used by dm-crypt for LUKS          │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────┐
│  dm-crypt / LUKS                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ /dev/sda1 → AES-256-XTS                      │  │
│  │ Key derived from encrypted:disk-key          │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Key Lifetime

- Keys in RAM are vulnerable to cold-boot attacks
- TPM-sealed keys resist software extraction but not physical attacks on the TPM
- Use `keyctl timeout` for automatic key expiration
- Revoke keys when no longer needed: `keyctl revoke <id>`

### Threat Model

| Attack Vector           | Mitigation                     |
|------------------------|--------------------------------|
| Memory dump            | Key scrubbing, `mlock()`       |
| Passphrase brute-force | Argon2id, TPM sealing          |
| Boot-time tampering    | Secure Boot + TPM PCR binding  |
| Physical disk theft    | LUKS full-disk encryption      |
| Cold-boot attack       | TRESOR (keys in CPU registers) |
| Key in swap            | `mlock()`, encrypted swap      |
| DMA attack             | IOMMU, kernel lockdown         |
| Side-channel           | Constant-time crypto           |

### Best Practices

```bash
# 1. Use LUKS2 with Argon2id
cryptsetup luksFormat --type luks2 --pbkdf argon2id /dev/sda1

# 2. Bind to TPM for unattended boot
systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=0+4+7 /dev/sda1

# 3. Keep backup key in secure location
cryptsetup luksAddKey /dev/sda1
# Store backup passphrase in physical safe

# 4. Backup LUKS header
cryptsetup luksHeaderBackup /dev/sda1 --header-backup-file /secure/backup.img

# 5. Use kernel keyring for runtime secrets
keyctl add encrypted runtime-key "new 32" @s

# 6. Set key timeouts
keyctl timeout $(keyctl search @u user runtime-key) 3600

# 7. Revoke keys on shutdown
# Add to shutdown script:
keyctl clear @s
```

## Appendix: Secrets in Containers

Container runtimes need access to secrets (database passwords, API keys, etc.)
without exposing them in the container image or environment variables.

```bash
# Method 1: Kubernetes Secrets (mounted as files)
# Pod spec mounts secret as volume
# Secret file appears at /var/secrets/db-password

# Method 2: Docker secrets
# Docker swarm mounts secrets at /run/secrets/<name>

# Method 3: Kernel keyring in containers
# Containers can use keyring if CAP_SYS_ADMIN is available
# Or use user keyrings with proper UID mapping

# Method 4: tmpfs mount (RAM-only)
mkdir /mnt/secrets
mount -t tmpfs -o size=1M tmpfs /mnt/secrets
echo "secret" > /mnt/secrets/password
# Data is never written to disk

# Method 5: dm-crypt for container volumes
cryptsetup luksFormat /dev/loop0
cryptsetup luksOpen /dev/loop0 container-secrets
mkfs.ext4 /dev/mapper/container-secrets
mount /dev/mapper/container-secrets /mnt/secrets
```

### Container Security Best Practices

```bash
# 1. Never put secrets in container images
# BAD:
ENV DB_PASSWORD=secret123

# 2. Use mounted secrets
# GOOD:
# Mount secret file at runtime

# 3. Use tmpfs for runtime secrets
mount -t tmpfs tmpfs /run/secrets

# 4. Revoke keys on container stop
# Add to container stop script:
keyctl clear @s

# 5. Use kernel keyring with timeouts
keyctl add user db-pass "secret" @s
keyctl timeout $(keyctl search @s user db-pass) 3600
```

## Appendix: Kernel Configuration

```
CONFIG_KEYS=y                    # Kernel keyring support
CONFIG_ENCRYPTED_KEYS=y          # Encrypted key type
CONFIG_TRUSTED_KEYS=y            # Trusted key type (TPM)
CONFIG_ASYMMETRIC_KEY_TYPE=y     # Asymmetric key support
CONFIG_SYSTEM_TRUSTED_KEYRING=y  # System-wide trusted keyring
CONFIG_DM_CRYPT=y                # dm-crypt support
CONFIG_BLK_DEV_DM=y              # Device mapper
CONFIG_TCG_TPM=y                 # TPM core
CONFIG_TCG_TIS=y                 # TPM Interface Specification
CONFIG_TCG_CRB=y                 # TPM Command Response Buffer (TPM 2.0)
```

## Appendix: Keyring Access Control

```c
/* Key permissions (POSIX-like) */
#define KEY_POS_VIEW    0x01000000  /* Owner: view */
#define KEY_POS_READ    0x02000000  /* Owner: read */
#define KEY_POS_WRITE   0x04000000  /* Owner: write */
#define KEY_POS_SEARCH  0x08000000  /* Owner: search */
#define KEY_POS_LINK    0x10000000  /* Owner: link */
#define KEY_POS_SETATTR 0x20000000  /* Owner: set attributes */

/* Same for group and other */
#define KEY_GRP_READ    0x00020000
#define KEY_OTH_READ    0x00000200

/* Example: owner full access, group read, others none */
keyctl setperm <key_id> 0x3f030000;
```

## Appendix: Troubleshooting

```bash
# Issue: "Key has expired"
# Fix: Check timeout, recreate key without timeout
keyctl timeout <key_id> 0  # Remove timeout

# Issue: "Permission denied"
# Fix: Check key permissions
keyctl list @s
# Verify UID/GID match

# Issue: "Required key not available"
# Fix: Key not in keyring, check request-key
keyctl search @u user my-key
# If not found, add it

# Issue: "Key has been revoked"
# Fix: Cannot unrevoke, must create new key

# Issue: TPM not available
# Fix: Check TPM driver
dmesg | grep tpm
ls /dev/tpm*
modprobe tpm_tis

# Issue: dm-crypt key not in keyring
# Fix: Add key to keyring before opening volume
keyctl add logon "cryptsetup:myvolume" "key_data" @u
cryptsetup luksOpen /dev/sda1 mydisk --keyring-keyring=@u --keyring-key=cryptsetup:myvolume
```

---

## Further Reading

- [Linux kernel source: `security/keys/`](https://elixir.bootlin.com/linux/latest/source/security/keys/)
- [Linux kernel source: `security/keys/encrypted-keys/`](https://elixir.bootlin.com/linux/latest/source/security/keys/encrypted-keys/)
- [kernel.org: Kernel Keyring](https://www.kernel.org/doc/html/latest/security/keys/core.rst)
- [keyctl(1) man page](https://man7.org/linux/man-pages/man1/keyctl.1.html)
- [cryptsetup(8) man page](https://man7.org/linux/man-pages/man8/cryptsetup.8.html)
- [tpm2-tools documentation](https://github.com/tpm2-software/tpm2-tools)
- [LWN: The kernel keyring](https://lwn.net/Articles/636288/)
- [Arch Linux Wiki: dm-crypt](https://wiki.archlinux.org/title/Dm-crypt)
- [systemd-cryptenroll(1)](https://man7.org/linux/man-pages/man1/systemd-cryptenroll.1.html)

> **Related topics:** [dm-crypt](../kernel/drivers/dm-crypt.md), [Secure Boot](./secure-boot.md), [IMA/EVM](ima.md), [Keyring API](keyring.md)
