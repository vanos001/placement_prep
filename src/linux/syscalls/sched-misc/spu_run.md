# spu_run(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC Cell table only) |
| Since (kernel) | 2.6.16 (syscalls(2)) |
| Man page | man2/spu_run.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for spu_run(), necessitating the use of syscall(2)" (spu_run.2, SYNOPSIS) |
| Aliases covered | none; context creation is [spu_create](spu_create.md) |
| Ledger ID | SC-spu_run |

## Purpose

spu_run() executed an SPU context: given the fd from [spu_create](spu_create.md), the context starts at the instruction pointer in `*npc` once scheduled onto a physical SPU, and the syscall blocks synchronously until the SPU stops (spu_run.2, DESCRIPTION). Parallel execution required a separate thread per SPU context (spu_run.2, DESCRIPTION) -- a blocking-run design, in contrast to the async submission of modern compute APIs.

## Synopsis

```c
#include <sys/spu.h>
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_spu_run, int fd, uint32_t *npc, uint32_t *event);
```

## Arguments and behavior

`fd` is the spu_create(2) context descriptor; `npc` points to the entry program counter and is updated on return with the current PC; `event` (optional, requires SPU_CREATE_EVENTS_ENABLED at creation) receives stop reasons (spu_run.2, DESCRIPTION). The return value is the spu_status register bitmask: 0x02 stopped by stop-and-signal, 0x04 by halt, 0x08 waiting for a channel, 0x10 single-step, 0x20 invalid instruction, 0x40 invalid channel, with bits 0x3fff0000 carrying the 14-bit stop-and-signal code when 0x02 is set (spu_run.2, RETURN VALUE). MFC-driven page faults on the DMA path can surface ENOMEM (spu_run.2, ERRORS).

## Return value and errors

The spu_status bitmask on success (one of the low bits always set); -1 with errno on failure (spu_run.2, RETURN VALUE). Errors: EBADF (fd invalid), EFAULT (bad npc/event pointers), EINTR (signal during execution; npc updated), EINVAL (fd not from spu_create), ENOMEM (MFC page-fault resources) (spu_run.2, ERRORS).

## Flags and constants

Status bits 0x02/0x04/0x08/0x10/0x20/0x40 and mask 0x3fff0000 (spu_run.2, RETURN VALUE).

## Security and notes

The whole pair is gated by spufs permissions and the SPU scheduling limits; nothing user-callable exists on non-Cell kernels (ENOSYS). Interview angle: the fd+blocking-run model versus CUDA-style stream submission is a nice architecture comparison, and the event bitmask is a case study in syscall-return-value multiplexing. Cross-reference: [spu_create](spu_create.md), [io_uring_setup](../net-ipc/io_uring_setup.md).

## References

- https://man7.org/linux/man-pages/man2/spu_run.2.html
- man-pages syscalls(2) (2.6.16)
