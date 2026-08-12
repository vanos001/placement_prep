# TEE — Trusted Execution Environment

## Overview

A **Trusted Execution Environment (TEE)** is a secure area of a processor that
guarantees code and data loaded inside it are protected with respect to
confidentiality and integrity. In the Linux kernel ecosystem, TEE support
enables communication with hardware-based security subsystems — most notably
**ARM TrustZone** with **OP-TEE** as the open-source TEE implementation.

The Linux kernel provides a TEE subsystem (`drivers/tee/`) that offers a
standardized interface for userspace applications to communicate with trusted
applications running in the secure world, regardless of the underlying TEE
hardware implementation.

## Architecture

### Two-World Model

The fundamental architecture of a TEE is the separation of the system into
two worlds:

```
+------------------------------------------+
|              Normal World                |
|  +------------------------------------+  |
|  |         Linux Kernel               |  |
|  |  +------------------------------+  |  |
|  |  |      Userspace (CA)          |  |  |
|  |  |  Client Application          |  |  |
|  |  +------------------------------+  |  |
|  |           | TEE driver              |  |
|  +-----------|--------------------------+  |
+------------------------------------------+
              | SMC (Secure Monitor Call)
+------------------------------------------+
|              Secure World                |
|  +------------------------------------+  |
|  |         TEE OS (OP-TEE)           |  |
|  |  +------------------------------+  |  |
|  |  |   Trusted Application (TA)   |  |  |
|  |  +------------------------------+  |  |
|  +------------------------------------+  |
+------------------------------------------+
```

- **Normal World**: Linux kernel and userspace applications
- **Secure World**: TEE OS and trusted applications
- **Secure Monitor**: firmware layer that mediates world switches (EL3 on ARM)

### TrustZone (ARM)

ARM TrustZone is the hardware foundation for TEE on ARM processors:

- **TrustZone Address Space Controller (TZASC)**: controls memory region
  access per-world
- **TrustZone Protection Controller (TZPC)**: controls peripheral access
- **AXI bus extension**: propagates the "secure" bit on bus transactions
- **Secure interrupts**: FIQ is routed to the secure world by default

TrustZone creates a hardware-enforced boundary — the normal world physically
cannot access secure world memory or peripherals.

### OP-TEE

**OP-TEE** (Open Portable Trusted Execution Environment) is the most widely
used open-source TEE OS for ARM TrustZone:

- **Maintained by**: Linaro / STMicroelectronics / community
- **License**: BSD-2-Clause
- **Platforms**: ARM, ARM64, some RISC-V implementations
- **Compliance**: GlobalPlatform TEE specifications

OP-TEE components:

| Component     | Location              | Description                          |
|---------------|-----------------------|--------------------------------------|
| `optee_os`    | Secure world          | TEE OS kernel                        |
| `optee_client`| Normal world userspace| Client library (libteec)             |
| `optee_linux` | Linux kernel          | Kernel TEE driver (`drivers/tee/`)   |
| `optee_test`  | Both worlds           | Test suite (xtest)                   |

## Linux Kernel TEE Subsystem

### Kernel Interface

The TEE subsystem provides a character device interface:

```bash
/dev/tee0       # First TEE device (OP-TEE)
/dev/teepriv0   # Privileged TEE device (for supplicants)
```

### TEE Driver Architecture

```c
/* include/linux/tee_drv.h */

struct tee_device;
struct tee_driver_ops {
    int (*get_version)(struct tee_device *teedev, struct tee_ioctl_version_data *);
    int (*supp_recv)(struct tee_device *teedev, u32 *func, u32 *num_params,
                     struct tee_param *params);
    int (*supp_send)(struct tee_device *teedev, u32 ret, u32 num_params,
                     struct tee_param *params);
    int (*invoke_func)(struct tee_device *teedev, struct tee_ioctl_invoke_arg *arg,
                       struct tee_param *params);
    int (*cancel_req)(struct tee_device *teedev, u32 cancel_id, u32 session);
    int (*open_session)(struct tee_device *teedev, struct tee_ioctl_open_session_arg *arg,
                        struct tee_param *params);
    int (*close_session)(struct tee_device *teedev, u32 session);
    int (*shm_register)(struct tee_device *teedev, struct page **pages,
                        size_t num_pages, struct tee_shm *shm);
    int (*shm_unregister)(struct tee_device *teedev, struct tee_shm *shm);
};
```

### OP-TEE Kernel Driver

The OP-TEE kernel driver (`drivers/tee/optee/`) handles:

1. **SMC communication**: sends Secure Monitor Calls to the secure world
2. **Shared memory management**: manages memory accessible by both worlds
3. **Session management**: opens/closes sessions with trusted applications
4. **Parameter marshalling**: converts between kernel and TEE parameter formats

```c
/* Simplified SMC call to OP-TEE */
static void optee_smccc_smc(unsigned long func_id, unsigned long a1,
                             unsigned long a2, unsigned long a3,
                             unsigned long a4, unsigned long a5,
                             unsigned long a6, unsigned long a7,
                             struct arm_smccc_res *res)
{
    arm_smccc_smc(func_id, a1, a2, a3, a4, a5, a6, a7, res);
}
```

### OP-TEE SMC Interface

Communication between normal and secure worlds uses ARM SMC (Secure Monitor
Call) convention:

| Function ID     | Description                          |
|-----------------|--------------------------------------|
| `0xBF00FF01`    | OPTEE_SMC_CALLS_UID                  |
| `0xBF00FF03`    | OPTEE_SMC_CALLS_REVISION             |
| `0xB2000000`    | OPTEE_SMC_CALL_GET_OS_UUID           |
| `0xB2000001`    | OPTEE_SMC_CALL_GET_OS_REVISION       |
| `0xFFFF0005`    | OPTEE_SMC_RETURN_RPC_CMD             |
| `0xB2000004`    | OPTEE_SMC_CALL_WITH_ARG              |

## Trusted Applications

### What Is a Trusted Application (TA)?

A Trusted Application runs in the secure world and provides security-sensitive
services:

- **Cryptographic operations**: key generation, encryption, signing
- **Secure storage**: data encrypted with hardware-bound keys
- **Biometric processing**: fingerprint matching in the secure world
- **DRM**: content decryption keys
- **Payment processing**: secure element communication

### TA Lifecycle

```
1. Client Application (CA) opens a session with a TA
2. TEE OS loads the TA if not already running
3. CA invokes commands within the session
4. CA closes the session
5. TEE OS may unload the TA
```

### GlobalPlatform TEE API

Trusted applications use the GlobalPlatform TEE Internal Core API:

```c
/* Trusted Application entry point */
TEE_Result TA_CreateEntryPoint(void) { /* ... */ }
void TA_DestroyEntryPoint(void) { /* ... */ }

TEE_Result TA_OpenSessionEntryPoint(uint32_t param_types,
                                     TEE_Param params[4],
                                     void **sess_ctx) { /* ... */ }
void TA_CloseSessionEntryPoint(void *sess_ctx) { /* ... */ }

TEE_Result TA_InvokeCommandEntryPoint(void *sess_ctx,
                                       uint32_t cmd_id,
                                       uint32_t param_types,
                                       TEE_Param params[4]) {
    switch (cmd_id) {
    case CMD_ENCRYPT:
        return do_encrypt(params);
    case CMD_SIGN:
        return do_sign(params);
    default:
        return TEE_ERROR_NOT_SUPPORTED;
    }
}
```

### TA Types

| Type          | Loading          | Storage              | Use Case           |
|---------------|------------------|----------------------|--------------------|
| Early TA      | Built into TEE OS| Embedded in secure world firmware | Boot-time security |
| Dynamic TA    | Loaded at runtime| Filesystem in secure world | General purpose |
| Pseudo TA     | Part of TEE OS   | Compiled into TEE OS | System services    |

### TA Compilation (OP-TEE)

```bash
# OP-TEE TA development toolchain
# TAs are compiled as ARM/AArch64 shared libraries (.ta files)

# Build a TA
make -C ta/ CROSS_COMPILE=arm-linux-gnueabihf \
    TA_DEV_KIT_DIR=/path/to/optee_os/out/arm/export-ta_arm32

# Output: <uuid>.ta (signed ELF shared library)
```

## Userspace Interface

### libteec (Client Library)

```c
#include <tee_client_api.h>

int main(void) {
    TEEC_Context ctx;
    TEEC_Session sess;
    TEEC_Operation op;
    TEEC_UUID uuid = { /* TA UUID */ };
    TEEC_Result res;

    /* Initialize context */
    res = TEEC_InitializeContext(NULL, &ctx);

    /* Open session with TA */
    res = TEEC_OpenSession(&ctx, &sess, &uuid,
                           TEEC_LOGIN_PUBLIC, NULL, NULL, NULL);

    /* Prepare operation */
    memset(&op, 0, sizeof(op));
    op.paramTypes = TEEC_PARAM_TYPES(
        TEEC_VALUE_INOUT, TEEC_NONE, TEEC_NONE, TEEC_NONE);
    op.params[0].value.a = 42;

    /* Invoke command */
    res = TEEC_InvokeCommand(&sess, CMD_GET_RESULT, &op, NULL);

    printf("Result: %u\n", op.params[0].value.a);

    /* Cleanup */
    TEEC_CloseSession(&sess);
    TEEC_FinalizeContext(&ctx);
    return 0;
}
```

Compile with: `gcc -lteec -o my_ca my_ca.c`

### ioctl Interface

The libteec library uses ioctls on `/dev/tee0`:

```c
/* Open session */
struct tee_ioctl_open_session_arg arg = {
    .uuid = { /* TA UUID */ },
    .clnt_login = TEE_IOCTL_LOGIN_PUBLIC,
};
ioctl(fd, TEE_IOC_OPEN_SESSION, &arg);

/* Invoke command */
struct tee_ioctl_invoke_arg inv_arg = {
    .session = arg.session,
    .func = CMD_ID,
};
ioctl(fd, TEE_IOC_INVOKE, &inv_arg);
```

## Shared Memory

### Why Shared Memory?

Data must be shared between the normal world (CA) and secure world (TA).
This is done through **shared memory** regions that are accessible to both
worlds.

### Shared Memory Management

```c
/* Allocate shared memory */
TEEC_SharedMemory shm;
shm.size = 4096;
shm.flags = TEEC_MEM_INPUT | TEEC_MEM_OUTPUT;
TEEC_AllocateSharedMemory(&ctx, &shm);

/* Use shared memory as a parameter */
op.paramTypes = TEEC_PARAM_TYPES(
    TEEC_MEMREF_WHOLE, TEEC_NONE, TEEC_NONE, TEEC_NONE);
op.params[0].memref.parent = &shm;
op.params[0].memref.size = shm.size;

/* Copy data to shared memory */
memcpy(shm.buffer, data, data_len);

/* Invoke TA with shared memory */
TEEC_InvokeCommand(&sess, CMD_PROCESS, &op, NULL);

/* Read result from shared memory */
memcpy(result, shm.buffer, result_len);

/* Free shared memory */
TEEC_ReleaseSharedMemory(&shm);
```

### Security Considerations for Shared Memory

- Shared memory is **not encrypted** — it's accessible to both worlds
- The kernel driver validates shared memory regions before passing them
  to the secure world
- Shared memory should be **registered** with the TEE (not dynamically
  allocated per-call) for performance
- Shared memory buffers must be **page-aligned** on most implementations

## Security Properties

### What TEE Protects Against

| Threat                    | Protection                          |
|---------------------------|-------------------------------------|
| OS compromise             | TA code/data inaccessible to Linux  |
| Memory dump               | Secure world memory not physical-accessible |
| Debug attacks             | JTAG can be disabled for secure world|
| Software key extraction   | Keys stored in secure world only    |
| Replay attacks            | Secure monotonic counter available  |

### What TEE Does NOT Protect Against

| Threat                    | Limitation                          |
|---------------------------|-------------------------------------|
| Physical attacks (decapping, glitching) | Requires tamper-resistant hardware |
| Side-channel attacks      | Timing, cache, power analysis possible |
| TA bugs                   | TA code must be correct and secure  |
| Secure Monitor bugs       | EL3 firmware vulnerabilities        |
| Supply chain attacks      | Trust in the initial boot chain     |

### Secure Boot Chain

TEE security depends on a trusted boot chain:

```
ROM → Bootloader (verified) → Secure Monitor (EL3) → TEE OS → TAs
                     ↓
              Normal World: Linux Kernel → Userspace
```

Each stage verifies the next. If any stage is compromised, the entire chain
is untrusted.

## OP-TEE Specific Features

### Secure Storage

OP-TEE provides encrypted storage for TAs:

```c
/* In the TA */
TEE_Result write_secure_data(void *data, size_t len) {
    TEE_ObjectHandle handle;
    TEE_Result res;

    res = TEE_CreatePersistentObject(
        TEE_STORAGE_PRIVATE,
        "my_data", 7,
        TEE_DATA_FLAG_ACCESS_WRITE_META | TEE_DATA_FLAG_ACCESS_READ |
        TEE_DATA_FLAG_ACCESS_WRITE,
        TEE_HANDLE_NULL,
        NULL, 0,
        &handle);

    res = TEE_WriteObjectData(handle, data, len);
    TEE_CloseObject(handle);
    return res;
}
```

Secure storage files are encrypted with a hardware-unique key and integrity-
protected.

### Key Derivation

OP-TEE can derive hardware-bound keys:

```c
/* Derive a key unique to this device and TA */
TEE_DeriveKey(&attribute, &salt, derived_key);
```

### Secure Time

OP-TEE provides a trusted time source:

```c
TEE_Time time;
TEE_GetSystemTime(&time);
```

### Attestation

OP-TEE supports device attestation — proving to a remote party that code
is running in a genuine TEE:

```c
/* Generate attestation data */
TEE_GenerateRandom(attestation_nonce, sizeof(attestation_nonce));
```

## Real-World Use Cases

### Android Keystore

Android uses TEE (via Keymaster/KeyMint HAL) to protect cryptographic keys:

```
Android App → Android Keystore → KeyMint HAL → OP-TEE TA
```

Keys generated in the TEE never leave the secure world in plaintext.

### DRM (Digital Rights Management)

Widevine and other DRM systems use TEE for content decryption:

```
Streaming App → DRM Framework → TEE TA → Decrypt content
```

The decryption keys and decrypted content reside in the secure world.

### Secure Biometrics

Fingerprint and face recognition processing in the secure world:

```
Biometric sensor → TEE TA → Match template → Result to normal world
```

### Secure Payments

Mobile payment systems use TEE to protect payment credentials:

```
Payment App → TEE TA → Secure Element communication
```

## Other TEE Implementations

### Qualcomm QTEE

Qualcomm's proprietary TEE for Snapdragon platforms:

- Runs on TrustZone
- Integrated with Qualcomm Secure Processing Unit (SPU)
- Android Keymaster implementation

### Intel SGX (Software Guard Extensions)

Intel's TEE for x86:

- **Enclaves**: isolated memory regions encrypted by hardware
- **Attestation**: remote attestation via Intel Attestation Service
- **Different model**: application-level isolation, not OS-level
- **Linux support**: Intel SGX driver merged in Linux 5.11

### AMD SEV (Secure Encrypted Virtualization)

AMD's TEE for virtual machines:

- **SEV**: encrypted VM memory with per-VM keys
- **SEV-ES**: encrypted register state
- **SEV-SNP**: integrity protection (prevents replay/remap attacks)
- **Use case**: cloud VM isolation

### RISC-V TEE

Emerging TEE standards for RISC-V:

- **Keystone**: open-source TEE framework
- **Penglai**: TEE for RISC-V
- **WorldGuard**: hardware isolation specification

## Development and Testing

### OP-TEE Development Environment

```bash
# Clone OP-TEE repositories
git clone https://github.com/OP-TEE/optee_os.git
git clone https://github.com/OP-TEE/optee_client.git
git clone https://github.com/OP-TEE/optee_examples.git

# Build for QEMU (ARMv7 or ARMv8)
cd optee_os
make -j$(nproc) PLATFORM=vexpress-qemu_virt

# Run in QEMU
cd build
make run
```

### Testing with xtest

```bash
# Run OP-TEE test suite
xtest
# Runs cryptographic tests, storage tests, concurrency tests, etc.
```

### Debugging TAs

```bash
# OP-TEE debug output (requires debug build)
# In secure world console:
D/TA:  my_ta_invoke_command: cmd=1, param_types=0x1
D/TA:  Result: 42
```

### TA Development Workflow

1. Write TA code (C, compiled for ARM/AArch64)
2. Define TA UUID and parameters
3. Build with OP-TEE TA dev kit
4. Copy `.ta` file to target filesystem
5. Write CA (Client Application) using libteec
6. Test with xtest or custom tests

## See Also

- [Kernel Lockdown](../security/lockdown.md) — kernel-level security
  restrictions complementing TEE
- [User Namespace Security](../containers/user-namespace-security.md) —
  container isolation vs. hardware isolation
- [Page Table Isolation](../performance/page-table-isolation.md) — another
  hardware-enforced isolation mechanism

## Further Reading

- **OP-TEE documentation**: https://optee.readthedocs.io/
- **OP-TEE source**: https://github.com/OP-TEE/
- **GlobalPlatform TEE specifications**: https://globalplatform.org/specs-library/tee-specifications/
- **ARM TrustZone**: ARM Security Technology documentation
- **Linux TEE subsystem**: `Documentation/staging/tee.rst`
- **LWN article**: ["An introduction to trusted execution environments"](https://lwn.net/Articles/738425/)
- **Linaro blog**: OP-TEE development guides and tutorials
- **Intel SGX documentation**: https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/overview.html
- **AMD SEV documentation**: AMD Secure Encrypted Virtualization API
- **man page**: `tee(1)` (not related — the TEE subsystem has no dedicated man page)
