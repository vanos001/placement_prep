# musl: dynamic loader

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `ldso/dynlink.c`, `ldso/dlstart.c`, `src/ldso/{dlopen.c,dlinfo.c,dladdr.c}`, `crt/{crt1.c,scrt1.c,rcrt1.c}`, `Makefile` |
| glibc counterpart pages | none for the loader itself; see [glibc overview](../glibc/overview.md) |
| Ledger | MUSL-family-dlfcn row; ledger-musl.md header family `dlfcn.h` (6) |

## Implementation notes

musl's `libc.so` *is* the dynamic loader: the Makefile links `LDSO_OBJS`
(`ldso/dynlink.lo`) into `lib/libc.so` and installs the interpreter path
`$(syslibdir)/ld-musl-$(ARCH)$(SUBARCH).so.1` as a symlink to libc.so
(Makefile, LDSO_PATHNAME and install rules). One library, one flat global
symbol namespace. `dynlink.c` reads `LD_LIBRARY_PATH` and `LD_PRELOAD`
(getenv at lines 1824-1825) and binds lazily or now per the
`RTLD_LAZY/RTLD_NOW` flags of `include/dlfcn.h`. The public dlfcn surface is
exactly six functions: `dlopen`, `dlsym`, `dlclose`, `dlerror`, `dladdr`,
`dlinfo` (only `RTLD_DI_LINKMAP` implemented, `src/ldso/dlinfo.c`).
Static PIE is bootstrapped by `crt/rcrt1.c`, which includes `ldso/dlstart.c`
so a statically linked binary self-relocates like the loader and then calls
`__libc_start_main` directly.

## Deltas vs glibc (verified)

- No symbol versioning: `rg dlvsym` over the whole tree returns nothing, while
  glibc 2.41 exports `dlvsym@@GLIBC_2.34` and versioned aliases such as
  `fmemopen@@GLIBC_2.22` (nm -D). dynlink lookup matches names only; musl
  parses `DT_HASH`, `DT_GNU_HASH` and `DT_VERSYM` from loaded objects
  (`ldso/dynlink.c` lines 982-992), and `versym` serves as a visibility
  filter, never for version matching.
- No `RTLD_DEEPBIND` (absent from `include/dlfcn.h`; glibc has it).
- glibc separates `ld-linux-x86-64.so.2` from `libc.so.6` (both present on
  host) and consults `/etc/ld.so.cache`; musl has no cache handling in the
  tree (rg "ld.so.cache" = 0 hits) and reads `/etc/ld-musl-$(ARCH).path`
  plus `LD_LIBRARY_PATH` instead (`ldso/dynlink.c`).
- 1.2.4 added RELR compressed relative relocations; 1.2.5 fixed `dlsym
  RTLD_NEXT` caller-module detection on sh (WHATSNEW).

## Porting notes

Binaries relying on versioned symbol interposition or `dlvsym` need
rework; `dlvsym` has no replacement. `RTLD_DEEPBIND` silently changes
precedence semantics. Invoking libc by its glibc path or expecting
`ld-linux-*` conventions breaks; deployment configs that assume `ldconfig`
caches or glibc path files need the musl `.path` file instead.
