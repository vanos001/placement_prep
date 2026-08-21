# Kernel Sanitizers — KASAN, UBSAN, MSAN, KFENCE

## Introduction

User-space programs have enjoyed AddressSanitizer, MemorySanitizer,
and UndefinedBehaviorSanitizer since roughly 2011 — Google published
AddressSanitizer in "AddressSanitizer: A Fast Address Sanity Checker"
(USENIX ATC 2012), reporting 2× slowdown and ~3.3× memory overhead
while catching use-after-free, heap- and stack-buffer overflow, and
stack-use-after-return. The kernel community adopted the same
approach to find bugs that elude conventional testing.

This page covers the four sanitizers in the kernel tree today:

- **KASAN** — memory safety (UAF, OOB, double-free)
- **UBSAN** — undefined behavior
- **KMSAN** — uninitialized memory reads
- **KFENCE** — production-friendly lightweight KASAN, ~0.1% overhead

Plus a brief mention of **KCSAN** (concurrency sanitizer) for context.

The uniting idea: the compiler instruments every memory access, every
arithmetic operation, every branch, or every load — and inserts code
that checks the operation against a *shadow* representation of
program state. In KASAN's case, that shadow is 1 byte per 8 bytes of
memory saying "this byte is allocated/initialized/redzone." In
KMSAN's case, the shadow is 1 bit per byte saying "this byte is
initialized." When a violation is detected, the sanitizer prints a
stack trace and either panics (`panic_on_warn`) or continues.

> **Kernel docs (all in one place):** `Documentation/dev-tools/`
> **Mailing list:** `kasan-dev@googlegroups.com`

## KASAN: Kernel AddressSanitizer

### Modes

KASAN ships in three flavors selected at compile time:

| Mode           | Kconfig                  | Compiler   | Overhead                | Platforms            |
|----------------|--------------------------|------------|-------------------------|----------------------|
| Generic        | `CONFIG_KASAN_GENERIC`   | GCC, Clang | ~2× speed, 1/8 RAM      | all                  |
| SW tags (TBI)  | `CONFIG_KASAN_SW_TAGS`   | Clang only | ~1.5× speed             | arm64 + x86 (TBI)    |
| HW tags (MTE)  | `CONFIG_KASAN_HW_TAGS`   | Clang only | minimal                 | arm64 with MTE only  |

The **generic** mode is the workhorse. Every 8 bytes of memory get 1
byte of shadow. The shadow byte values encode:

```
0x00  : all 8 bytes are addressable
0x01..0x07 : only the low N bytes are addressable
0xF1 : left redzone of a heap object
0xF2 : mid-redzone
0xF3 : right redzone of a heap object
0xF5 : partial redzone (free object)
0xF8 : stack left redzone
0xF9 : stack mid redzone
0xFA : stack right redzone
0xFB : use-after-return (shadow of freed stack frame)
0xFC : freed-by-stack-object
0xFD : shadow-after-scope (out-of-scope stack var)
0xFE : use-after-free shadow (the famous one)
```

Every memory access is instrumented with a sequence like:

```asm
; original:   mov eax, [rdi]
; instrumented:
mov  rax, rdi
shr  rax, 3             ; divide address by 8
add  rax, shadow_base   ; point to shadow byte
movzx ecx, byte [rax]   ; load shadow
test  ecx, ecx
jnz   .report           ; non-zero → slow path
mov   eax, [rdi]        ; original load
```

The slow path checks whether the access is within the redzone. If it
is, KASAN logs and (by default) continues.

### Building and running

```
$ make CC=clang defconfig
$ ./scripts/config \
    --enable CONFIG_KASAN \
    --enable CONFIG_KASAN_INLINE \
    --enable CONFIG_KASAN_VMALLOC \
    --set-val CONFIG_KASAN_STACK 1
$ make CC=clang -j$(nproc)
$ qemu-system-x86_64 -kernel arch/x86/boot/bzImage ...
```

`CONFIG_KASAN_INLINE` (vs. the default outline mode) inlines the
fast-path check. Outline mode emits a function call per check —
smaller code, slower. Inline is what you want for performance.

### Worked example: catching a use-after-free

Consider this trivially broken module:

```c
#include <linux/slab.h>
#include <linux/module.h>

static int __init bug_init(void)
{
    char *p = kmalloc(32, GFP_KERNEL);
    kfree(p);
    pr_info("freed; deref %c\n", p[0]);   /* <-- UAF */
    return 0;
}
module_init(bug_init);
MODULE_LICENSE("GPL");
```

With KASAN enabled, the dmesg on `insmod` reads:

```
==================================================================
BUG: KASAN: slab-use-after-free in bug_init+0x3c/0x1000 [bug]
Read of size 1 at addr ffff8880086f0020 by task insmod/150

CPU: 0 PID: 150 Comm: insmod Not tainted 6.8.0-kasan #1
Call Trace:
 <TASK>
  dump_stack_lvl+0x4f/0x80
  print_report+0xcf/0x650
  kasan_report+0xb1/0x130
  bug_init+0x3c/0x1000 [bug]
  do_one_initcall+0x70/0x2e0
  ...
 </TASK>

Allocated by task 150:
 kasan_save_stack+0x1e/0x40
 kasan_set_track+0x21/0x30
 __kasan_slab_alloc+0x6e/0x80
 kmalloc_trace+0x3a/0xd0
 bug_init+0x18/0x1000 [bug]
 ...

Freed by task 150:
 kasan_save_stack+0x1e/0x40
 kasan_set_track+0x21/0x30
 kasan_save_free_info+0x2b/0x50
 __kasan_slab_free+0x100/0x150
 kfree+0x96/0x2c0
 bug_init+0x24/0x1000 [bug]
 ...

The buggy address belongs to the object at ffff8880086f0020
 which belongs to the cache kmalloc-32 of size 32
The buggy address is located 0 bytes inside of
 32-byte region [ffff8880086f0020, ffff8880086f0040)
==================================================================
```

That single dump — buggy address, *allocated* stack, *freed* stack,
slab of origin — is the killer feature. A bare kernel oops gives
you the faulting instruction pointer; KASAN gives you the full
lifetime.

### Quarantine

When `kfree(p)` runs under KASAN, the slab object is *not* returned
to the freelist immediately. Instead it goes into a per-CPU
**quarantine** of fixed size (default `quarantine_size_mb`). Every
subsequent `kmalloc` consumes from the freelist, not from the
quarantine, so the pointer remains poisoned. The quarantine size
bounds how long an old allocation can survive after `kfree` — long
enough for most UAFs to be spotted, short enough that the memory
overhead stays acceptable.

### Stack instrumentation

KASAN instruments stack objects too. After function entry, it paints
the redzones of every local variable to a unique poison value; on
function exit it verifies they have not been clobbered. This catches
out-of-bounds accesses between two locals on the same frame, which
are otherwise invisible. Enable with `CONFIG_KASAN_STACK=y`.

## KMSAN: Kernel MemorySanitizer

KMSAN, merged in 5.14 (2021) by Alexander Potapenko, catches reads
of uninitialized memory. It only builds with **Clang** (no GCC
support) because it requires the `-fsanitize=memory` LLVM pass and a
small set of compiler-rt helpers that GCC does not have.

The mechanism is straightforward in concept: every byte of memory
has a corresponding **shadow bit** — 0 if the byte has been
initialized, 1 if not. Stores clear the shadow; loads OR the shadow
of the source into a "chain" register tracking which uninitialized
bits flow into the current computation. If a value with a non-zero
shadow ever crosses a "check" boundary (function call whose argument
is not allowed to be uninitialized, conditional branch, syscall
argument), KMSAN reports.

A worked example:

```c
#include <linux/init.h>
#include <linux/module.h>

static int __init kmsan_init(void)
{
    int x;            /* uninitialized */
    int y = x + 1;
    if (y)           /* conditional branch on uninitialized value */
        pr_info("y=%d\n", y);
    return 0;
}
module_init(kmsan_init);
MODULE_LICENSE("GPL");
```

dmesg:

```
=====================================================
BUG: KMSAN: uninit-value in kmsan_init+0x50/0x1000

Local variable x created at:
 kmsan_init+0x10/0x1000

CPU: 0 PID: 200 Comm: insmod Not tainted 5.14.0-kmsan #1
Hardware name: QEMU
Call Trace:
 <TASK>
  dump_stack_lvl+0x4f/0x80
  kmsan_report+0x12a/0x170
  __msan_warning+0x4d/0x90
  kmsan_init+0x50/0x1000 [bug]
 </TASK>
=====================================================
```

KMSAN has overhead — ~3× slowdown and ~2× memory — and so is
primarily run in syzbot CI rather than developer laptops. It is the
only sanitizer that finds the entire class of "we read stack
garbage and used it as a length" bugs.

## UBSAN: Undefined Behavior Sanitizer

UBSAN, originally from the LLVM project, ports to the kernel via
`CONFIG_UBSAN=y`. It instruments operations the C standard leaves
undefined — signed integer overflow, shift past the width, division
of `INT_MIN` by `-1`, misaligned pointer casts, out-of-range enum
conversions, and so on.

Each subcheck is independently toggleable:

| Kconfig                       | Catches                                            |
|-------------------------------|----------------------------------------------------|
| `CONFIG_UBSAN_BOUNDS`        | array index out of bounds (compile-time sizes)     |
| `CONFIG_UBSAN_DIVZERO`       | integer divide-by-zero                             |
| `CONFIG_UBSAN_SHIFT`         | shifts >= width                                    |
| `CONFIG_UBSAN_UNREACHABLE`   | `__builtin_unreachable()` reached                  |
| `CONFIG_UBSAN_SIGNED_OVERFLOW` | signed `+`/`-`/`*` overflow                       |
| `CONFIG_UBSAN_ALIGNMENT`     | pointer dereference of misaligned address          |
| `CONFIG_UBSAN_BOOL`          | true/false values not 0/1                          |
| `CONFIG_UBSAN_ENUM`          | enum value out of declared range                   |

A worked example:

```c
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>

static int __init ub_init(void)
{
    int a = INT_MAX;
    int b = a + 1;       /* signed overflow: UB */
    return b;
}
module_init(ub_init);
MODULE_LICENSE("GPL");
```

`CONFIG_UBSAN_SIGNED_OVERFLOW` will, at runtime, log:

```
UBSAN: signed-integer-overflow in ub_init+0x20/0x1000:
 signed integer overflow: 2147483647 + 1 cannot be represented in
 type 'int'
```

UBSAN is light (low single-digit percent slowdown with the default
subcheck set) and is increasingly enabled in *production* kernels by
distributions like Android and Fedora for the bounds and alignment
subchecks alone. The Linux kernel team keeps it on by default in CI;
syzbot reports hundreds of UBSAN-triggered bugs per year.

## KFENCE: Production KASAN

KASAN's 2× slowdown is too much for a production web server. KFENCE
("Kernel Electric Fence", merged 5.12, 2021) is the answer — a
**sampled** memory error detector designed by Alexander Potapenko and
Marco Elver that catches UAFs and OOBs with **~0.1% overhead**.

The trick: KFENCE does not instrument every access. Instead, it
*occasionally* serves `kmalloc` requests from a dedicated pool of
4 KiB slab pages, where each allocation occupies exactly one page
and is surrounded by guard pages. Any access outside the actual
object hits the guard page → page fault → KFENCE reports.

```
kmalloc(32)
   |
   | (probability 1 / CONFIG_KFENCE_SAMPLE_INTERVAL = 1/100 default)
   v
 KFENCE pool: one 4 KiB page per object
   +------------------------+------------------------+----+
   | obj0 |  guard page    | obj1 |  guard page    | obj2| ...
   | 32B  | (4064 unused)  | 32B  | (4064 unused)  |     |
   +------------------------+------------------------+----+
                           ^
                           `-- any OOB access or UAF hits the
                               guard page fault handler
                                -> kfence_report()
```

Useful sysfs knobs under `/sys/kernel/debug/kfence/` (debugfs):

- `sample_interval` — how often to sample (ms; `0` disables)
- `num_objects` / `num_objects_total` — pool stats
- `bytes_free` / `bytes_total`

A typical report (real, paraphrased from LKML):

```
==================================================================
BUG: KFENCE: use-after-free in nf_hook_slow+0x118/0x1c0

Use-after-free access at 0xffff88812c920020 (5 minutes ago,
12 cpu-clocks)
nf_hook_slow+0x118/0x1c0
ip_local_deliver+0x6d/0xe0

allocated via:
 kmalloc_trace+0x22/0x2c0
 __net_init_hook+0x18/0x40

freed via:
 kfree+0x96/0x2c0
 __net_exit_hook+0x20/0x50
==================================================================
```

The original KFENCE paper ("KFENCE: A Low-Overhead Detection System
for Memory Errors in the Linux Kernel", APSys 2021) reports the
catch rate: at sample interval 100 ms, KFENCE catches roughly 70%
of the UAFs KASAN finds — but at 1000× lower overhead. The Google
KernelSanitizers team has it deployed in production ChromeOS and
Android kernels since 5.13.

## KCSAN (out of scope but worth knowing)

KCSAN (Concurrency Sanitizer) is the odd one out — it does not catch
memory safety bugs, it catches *data races*. The compiler
instruments memory accesses with a check-then-load sequence that
observes whether another CPU touched the same location concurrently.
It is invaluable for RCU and lockless code; see
`Documentation/dev-tools/kcsan.rst`.

## Putting it together: how to enable all of them

```
./scripts/config \
  --enable CONFIG_KASAN \
  --enable CONFIG_KASAN_INLINE \
  --enable CONFIG_KASAN_VMALLOC \
  --enable CONFIG_KASAN_KUNIT_TEST \
  --enable CONFIG_UBSAN \
  --enable CONFIG_UBSAN_BOUNDS \
  --enable CONFIG_UBSAN_SHIFT \
  --enable CONFIG_UBSAN_DIVZERO \
  --enable CONFIG_KFENCE \
  --set-val CONFIG_KFENCE_SAMPLE_INTERVAL 100
# KMSAN is exclusive with KASAN — separate build.
```

KASAN and KMSAN are mutually exclusive (they use conflicting shadow
regions). UBSAN, KFENCE, and KCSAN stack with either.

## References

1. **Kernel KASAN docs** —
   <https://www.kernel.org/doc/html/latest/dev-tools/kasan.html>
2. **Kernel KMSAN docs** —
   <https://www.kernel.org/doc/html/latest/dev-tools/kmsan.html>
3. **Kernel UBSAN docs** —
   <https://www.kernel.org/doc/html/latest/dev-tools/ubsan.html>
4. **Kernel KFENCE docs** —
   <https://www.kernel.org/doc/html/latest/dev-tools/kfence.html>
5. **"AddressSanitizer: A Fast Address Sanity Checker"**
   (Serebryany et al., USENIX ATC 2012) —
   <https://research.google.com/pubs/pub37661.html>
6. **"Kernel Address Sanitizer: a tool for finding memory bugs in
   the Linux kernel"** (Ryabinin et al., ACCESS 2016) —
   <https://doi.org/10.1145/2872362.2872406>
7. **"KFENCE: A Low-Overhead Detection System for Memory Errors in
   the Linux Kernel"** (Elver et al., APSys 2021) —
   <https://doi.org/10.1145/3477132.3483547>
8. **GCC `-fsanitize=address` manual** —
   <https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html>
9. **Clang `-fsanitize=kernel-memory`** —
   <https://clang.llvm.org/docs/MemorySanitizer.html>
10. **KernelSanitizers project (Google)** —
   <https://github.com/google/kmsan>
11. **syzbot continuous sanitizer runs** —
   <https://syzkaller.appspot.com/>
