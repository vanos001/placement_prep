# `alloca` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `alloca.h` (line 32); also visible through `stdlib.h`, which includes `<alloca.h>` under `__USE_MISC` (stdlib.h lines 706-709) |
| Standards | BSD extension; "not in POSIX.1" (alloca.3 CONFORMING TO); seen in 32V/PWB/3BSD/4BSD |
| Exported | no `alloca` symbol -- gcc compiles it to the `__builtin_alloca` inline (alloca.h lines 34-36); `nm -D libc.so.6` shows only private `__libc_alloca_cutoff@@GLIBC_PRIVATE` (host glibc 2.41) |
| Thread-safety | MT-Safe (alloca.3 ATTRIBUTES) |
| Ledger ID | GLIBC-alloca |

## Declaration and gates

```c
#include <alloca.h>

extern void *alloca(size_t size);   /* alloca.h:32 */

#ifdef __GNUC__
# define alloca(size) __builtin_alloca (size)   /* alloca.h:34-36 */
#endif
```

No feature-test gate in `alloca.h` itself; `stdlib.h` pulls the prototype
in only under `__USE_MISC`.

## Semantics

`alloca(size)` returns `size` bytes allocated *in the caller's stack
frame*. There is no matching dealloc call: the block vanishes when the
function that called `alloca` returns, exactly like an automatic
variable -- even if the return happens via `longjmp`/`siglongjmp`, which
is the classic trick for temporarily growing scratch space without
cleanup code (alloca.3 NOTES). The manual positions it as
"half-dynamic allocation" (memory.texi, *Variable Size Automatic*).

## Gotchas and portability

- **No error path.** Overflowing the stack is undefined behavior --
  typically SIGSEGV, not NULL (alloca.3 RETURN VALUE). Never use it for
  attacker-controlled sizes; `__libc_alloca_cutoff` is how libc internals
  pick alloca vs malloc.
- **Do not call it inside a function-call argument list** -- the block
  lands in the middle of the argument area: `foo(x, alloca(4), y)` is
  forbidden (manual, *Variable Size Automatic*).
- **Never `free()` an alloca block**; the pointer also stays valid only
  until function exit, not end of scope.
- **VLA contrast** (manual, *GNU C Variable-Size Arrays*): a VLA is freed
  at the end of its *scope*, alloca memory lives to the end of the
  *function*; alloca can be used in a loop, VLAs cannot. Mixing both in
  one function is fragile: leaving a VLA scope frees alloca blocks
  allocated in that scope.
- gcc emits the builtin inline even under `-std=c89` unless `<alloca.h>`
  is not included (alloca.3 "Notes on the GNU version").
- musl 1.2.5: `include/alloca.h` exists and also defines
  `alloca __builtin_alloca` -- same caveats.

## References

- man3: `alloca.3`
- glibc manual: `memory.texi`, nodes *Variable Size Automatic*,
  *Advantages of Alloca*, *Disadvantages of Alloca*,
  *GNU C Variable-Size Arrays*
- headers: `/usr/include/alloca.h` (lines 29-36)
- symbols: `nm -D --with-symbol-versions libc.so.6`
