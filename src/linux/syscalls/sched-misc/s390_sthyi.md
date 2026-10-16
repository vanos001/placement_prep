# s390_sthyi(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (s390 table only) |
| Since (kernel) | 4.15 (s390_sthyi.2 HISTORY) |
| Man page | man2/s390_sthyi.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for s390_sthyi(), necessitating the use of syscall(2)" (s390_sthyi.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-s390_sthyi |

## Purpose

s390_sthyi() emulates the STHYI (Store Hypervisor Information) instruction: it reports hardware resource information for the machine and its virtualization levels -- CPU type and capacity, machine model, and related metrics (s390_sthyi.2, DESCRIPTION). Guest kernels use it to learn where they sit in the hypervisor stack; the syscall form lets userspace ask the same question without executing the (privileged-emulated) instruction.

## Synopsis

```c
#include <asm/sthyi.h>   /* STHYI_* constants */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_s390_sthyi, unsigned long function_code,
            void *resp_buffer, uint64_t *return_code,
            unsigned long flags);
```

## Arguments and behavior

`function_code` selects the report; STHYI_FC_CP_IFL_CAP returns CP/IFL capacity information into `resp_buffer`, which must be one page (4K) for that code (s390_sthyi.2, DESCRIPTION). `return_code` receives the instruction-level return code; `flags` must be 0 (EINVAL otherwise) (s390_sthyi.2, DESCRIPTION/ERRORS). The kernel caches responses for up to a second (as of 4.16), so repeated calls may observe the same data (s390_sthyi.2, NOTES). Unlike the raw instruction, the syscall path waives the response-buffer alignment requirements (s390_sthyi.2, NOTES).

## Return value and errors

On success the return value mirrors the instruction's condition code, 0..3: 0 = capacity data stored in *resp_buffer; 3 = "unsupported function code" with the buffer unchanged; 1 and 2 reserved (s390_sthyi.2, RETURN VALUE). -1 with errno on error: EFAULT (bad resp_buffer/return_code), EINVAL (nonzero flags), ENOMEM (allocation failed), EOPNOTSUPP (invalid function_code) (s390_sthyi.2, ERRORS).

## Flags and constants

STHYI_FC_CP_IFL_CAP (<asm/sthyi.h>); flags must be 0.

## Security and notes

Machine-capability introspection is exactly the kind of data multi-tenant platforms may not want to expose freely -- visibility follows the instruction's own gating, and the syscall exists so virtualized guests can implement the instruction for their userspace. Interview angle: compare with x86's CPUID in guests (usually paravirt-trapped and synthesized) -- same problem, different mechanism. Cross-reference: [sysinfo](sysinfo.md), [getcpu](getcpu.md), [s390_runtime_instr](s390_runtime_instr.md).

## References

- https://man7.org/linux/man-pages/man2/s390_sthyi.2.html
- man-pages syscalls(2) (4.15, s390 only)
