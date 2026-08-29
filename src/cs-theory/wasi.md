# WASI -- the WebAssembly System Interface

Core WebAssembly (covered in [webassembly.md](./webassembly.md)) is an instruction set with *no* operating system underneath: a module cannot open a file, read a clock, or touch a socket unless the host explicitly hands it an import that does. WASI (WebAssembly System Interface) is the standardized family of host interfaces that fills that gap: a POSIX-shaped but capability-based system-call surface that lets the same `.wasm` file run under Wasmtime on x86, WAMR on a microcontroller, or a CDN edge node, while never holding more authority than the operator granted. Its stated influences are POSIX and CloudABI, and it is developed by the WASI Subgroup of the WebAssembly Community Group for eventual standardization.

This page is the *system interface* view: naming history, the capability model, the preview1 syscalls, the 0.2/0.3 component-model transition, runtimes, and an honest look at what WASI sandboxing does and does not guarantee. The type system and composition mechanics (WIT, worlds, canonical ABI) live in [wasm-component-model.md](../compilers/advanced/wasm-component-model.md); engine internals are in [wasm-runtimes.md](../compilers/advanced/wasm-runtimes.md).

## Why a sandboxed ISA needs a system interface

The Wasm spec itself is the sandbox: code, stacks, and bounds checks are all specified, and the only doors are imports. The Wasmtime documentation phrases it directly: "All interaction with the outside world is done through imports and exports. There is no raw access to system calls or other forms of I/O; the only thing a WebAssembly instance can do is what is available through interfaces it has been explicitly linked with."

POSIX gives every process *ambient authority*: `open("/etc/passwd")` succeeds whenever the uid allows it, regardless of why the process wants the file. WASI inverts this. Every resource is a handle minted by the host and passed to the module at instantiation; the module can use and narrow handles, but never forge or widen them. A WASI program looks like a Unix process (args, env, fds 0/1/2, filesystem) yet starts with an authority set that is explicitly configured, e.g. `wasmtime run --dir . foo.wasm` grants exactly one preopened directory.

## The naming maze: preview0 / preview1 / 0.2 / 0.3

WASI's version names are genuinely confusing because two schemes (import-module names and release numbers) overlap. The canonical `wasi-0.1` documentation branch of the WASI repo untangles it:

| Era | Import name / packages | IDL | Shape | Status |
|---|---|---|---|---|
| Preview 0 | `wasi_unstable` | witx | 45 flat functions | Short-lived 2019 snapshot ("snapshot_0"); legacy only |
| Preview 1 | `wasi_snapshot_preview1` | witx | 46 flat functions | Frozen legacy; still the most widely deployed |
| WASI 0.2 (Preview 2) | WIT packages `wasi:cli`, `wasi:io`, `wasi:filesystem`, `wasi:clocks`, `wasi:random`, `wasi:sockets`, `wasi:http` | WIT | Typed resources + worlds, component-model based | Shipped (`wasi-cli` v0.2.0 tagged Feb 2024) |
| WASI 0.3 (Preview 3) | WIT packages versioned `0.3.x` | WIT + native async | `stream<T>` / `future<T>` replace explicit streams/polling | Current preview, per the WASI repo README |

Facts worth memorizing about preview1, straight from the canonical witx and branch README:

- The `wasi_snapshot_preview1` module defines **46 functions** (`args_get` through `sock_shutdown`), counted from the witx. Preview0 (`wasi_unstable`) defined 45; the differences are minor.
- The "ephemeral" iteration of preview1 was abandoned and the "preview2" name was recycled for the WIT-based WASI, which is why `wasi_snapshot_preview1` is the only preview1-style name you will ever see in production. Callees were expected to have access to the caller's **entire linear memory** (preview1 has no fine-grained type sharing), and there is an implied global file-descriptor table.
- Several preview1 features were never widely implemented by engines: `proc_raise` (Wasm traps instead), the process/thread CPU-time clock IDs, and the `sock_*` group except `sock_accept`, which was added late for accept-only servers. Full sockets (connect/listen) arrived with preview2's `wasi:sockets`.

## Capability model mechanics (preview1)

Preopened directories are the classic example. The host opens directories *before* the guest starts and exposes them as anonymous fd numbers (typically starting at 3). The guest discovers them by probing:

1. Call `fd_prestat_get(fd)` on successive fds; the call returns a `prestat` record naming the in-sandbox mount point (e.g. `/data`) or `EBADF` when the fd is not a preopen.
2. Call `fd_prestat_dir_name(fd, buf, len)` to learn the directory's guest-visible name.
3. From then on, the *only* way to reach the filesystem is `path_open(dirfd, ...)`, which resolves the path relative to that directory handle and intersects the requested rights with the rights the preopen carries. Handles can only be narrowed (e.g. via `fd_fdstat_set_rights`), never widened.

```text
        grant (operator, at start)      wasmtime run --dir /srv/data::/data app.wasm
        -------------------------------------------------------------
        guest module                          host runtime
  +------------------------+  import   +-------------------------------------+
  | (import "wasi_snapshot_| --------> | fd_prestat_get(3) -> preopen /data  |
  |  preview1" "path_open"))|           | fd 3 == capability to /srv/data     |
  +------------------------+           +-------------------------------------+
        |                                          |
        | path_open(3, "input.csv")                | resolve under /srv/data,
        | ------------------------------------>    | rights include READ
        | <------------------------------------    | -> new fd  -> ALLOW
        |
        | path_open(3, "../etc/shadow")
        | ------------------------------------>    | resolved path escapes
        |                                          | the preopen root
        | <------------------------------------    | -> errno NOTCAPABLE -> DENY
```

The striking property: there is no `open()` in WASI, so "opening a path you were not granted" is not a permission check that can fail at the wrong layer -- it is a type error. `path_open` cannot even *name* an absolute path; it only expresses paths relative to a directory capability the host chose to hand out.

## The preview1 syscall surface

Representative members of the 46-function set (all parameters are i32/i64 integers plus guest-memory pointers):

| Function | Prototype sketch | Purpose | Capability angle |
|---|---|---|---|
| `fd_prestat_get` | `(fd) -> errno, prestat` | Discover a preopen | Enumeration of granted authority |
| `fd_prestat_dir_name` | `(fd, buf, len) -> errno` | Name of preopen dir | Mount-point string, host-set |
| `path_open` | `(dirfd, dirflags, path, oflags, rights_base, rights_inheriting, fdflags) -> errno, fd` | Open under a dir handle | Rights requested <= rights held; no absolute paths |
| `fd_read` / `fd_write` | `(fd, iovs, iovs_len, nwritten) -> errno` | Scatter/gather I/O | Works on any read/write-capable fd incl. stdout/stderr |
| `fd_fdstat_get` / `fd_fdstat_set_rights` | `(fd, ...) -> errno` | Introspect / narrow an fd's rights | Rights only shrink, by construction |
| `clock_time_get` | `(id, precision, result) -> errno` | Wall/monotonic time | Time is a capability, not ambient |
| `random_get` | `(buf, len) -> errno` | Random bytes | Host-controlled entropy source |
| `poll_oneoff` | `(subs, events, n, nevents) -> errno` | Multi-wait on fds/clocks | Preview1's one poll loop; superseded by async in 0.3 |
| `proc_exit` | `(code) ->` | Terminate | No signals in preview1; `sock_accept` is the only socket op most engines shipped |

Every call returns an `errno` using the witx `expected` type rather than trapping: a denied operation is an ordinary return value, which is why capability checks compose with normal control flow. The host functions read and write the guest's linear memory directly (the guest exports its `memory`), so `fd_write` consumes an iovec array laid out in guest memory (see the demo below).

## WASI 0.2 and 0.3: the component-model era

Preview2 rebuilt WASI on the Component Model: interfaces declared in WIT, resources (typed handles like `filesystem.descriptor`) instead of raw i32 fds, and worlds (e.g. `wasi:cli/imports`) bundling what a command-line program may import. Because imports are per-interface, a component's *capability footprint is part of its type signature*: you can read a component's imports and know exactly what it can do before running it. The transition path for the huge preview1 corpus is an adapter module that maps the 46 flat calls onto the typed interfaces. Composition details are in [wasm-component-model.md](../compilers/advanced/wasm-component-model.md).

WASI 0.2 marked the point where the CLI, filesystem, clocks, random, sockets, and HTTP proposals were snapshotted together (`wasi-cli` v0.2.0, tagged 2024-02-07). Sockets grew real connect/listen/UDP under `wasi:sockets`, and `wasi:http` gives components a typed HTTP client/server API.

WASI 0.3 is the **current preview**. Per the WASI README, it "builds on WASI 0.2, replacing the earlier explicit streams and polling interfaces with the component model's native, composable `async` functionality via the `future` and `stream` types", so `poll_oneoff`-style multiplexing and the blocking `wasi:io/streams` shapes give way to asynchronous functions that the host can schedule natively. Do not overstate its status: to be included in 0.3 a proposal must reach phase 3 of the WASI subgroup process, satisfy its portability criteria, and be voted in; and the latest Proposals.md table shows even the 0.2-era core proposals (clocks, filesystem, sockets, cli, http, random) sit at phase 3 (implementation), with nothing yet at phases 4 or 5 (standardization). Treat all of WASI as "standardized API drafts with multiple production implementations," not as a finished W3C standard.

## Runtimes and who implements what

| Runtime | Steward | Preview1 | 0.2 components | Notes |
|---|---|---|---|---|
| Wasmtime | Bytecode Alliance | Yes | Yes (reference implementation) | Cranelift backend; CLI `--dir`/`--env` grants preopens |
| Wasmer | Wasmer, Inc. | Yes | Partial | README advertises WASI "out of the box" plus WASIX, its fork-style superset adding threads/fork |
| WAMR | Bytecode Alliance | Yes (libc-wasi shim) | No | Interpreter/AOT for embedded targets; small footprint |
| WasmEdge | CNCF (sandbox project) | Yes | In progress | Plugin ecosystem (tensor, image, networking) |
| Node.js `node:wasi` | Node core | Yes | No | Marked Stability 1 (experimental); preview1 only |
| Browser engines | W3C implementers | None | None | WASI is deliberately out of scope for the web |

Beyond CLI runtimes, WASI is usually *embedded*: `wasmtime-py` ("Python embedding of Wasmtime") and `wasmtime-dotnet` (".NET embedding of Wasmtime") let a Python or .NET application act as the WASI host for plugin modules. In the container world, containerd's `runwasi` project runs Wasm workloads through shims such as `io.containerd.wasmtime.v1`; Kubelet still schedules a "pod," but the payload is a `.wasm` rather than a rootfs (see [containerd.md](../linux/containers/containerd.md) and [crun.md](../linux/containers/crun.md) for the container side).

## A capability-checking host, modeled in Python

The model below reproduces the two moves that make WASI interesting: a host that only honors syscalls against capabilities it actually granted, and the preview1 `fd_write` iovec encoding where both the iovec array and the byte buffer live in guest linear memory at addresses the syscall names.

```python
# WASI capability model + preview1 fd_write binary encoding (stdlib only).
import posixpath
import struct

# ---- Part 1: a host that enforces preopened-directory capabilities ----
RIGHTS_R, RIGHTS_W = 1, 2          # toy rights bits

def fmt_rights(w):                 # render bits as R-/W- style
    return ("R" if w & RIGHTS_R else "-") + ("W" if w & RIGHTS_W else "-")

class Preopen:                     # a capability minted by the host
    def __init__(self, host_path, guest_name, rights):
        self.host_path, self.guest_name, self.rights = host_path, guest_name, rights

class Host:
    def __init__(self):
        self.preopens = {          # granted before instantiation:
            3: Preopen("/srv/data", "/data", RIGHTS_R | RIGHTS_W),
            4: Preopen("/var/log",  "/logs", RIGHTS_W),          # write-only
        }
        self.next_fd = 5
    def path_open(self, dirfd, path, want):
        po = self.preopens.get(dirfd)
        if po is None:
            return "DENY", f"fd {dirfd} is not a preopen"
        if path.startswith("/"):
            return "DENY", "path_open cannot name absolute paths"
        root = po.guest_name.rstrip("/")
        resolved = posixpath.normpath(root + "/" + path)   # lexical resolve
        if resolved != root and not resolved.startswith(root + "/"):
            return "DENY", f"{path!r} resolves outside preopen {po.guest_name}"
        if want & ~po.rights:
            return "DENY", f"needs {fmt_rights(want)} but preopen grants {fmt_rights(po.rights)}"
        fd = self.next_fd; self.next_fd += 1
        return "ALLOW", f"fd {fd} under {po.host_path}"

host = Host()
cases = [
    (3, "input.csv",       RIGHTS_R),       # under /data, read granted
    (3, "sub/config.yaml", RIGHTS_R),       # subdir of /data
    (3, "/etc/passwd",     RIGHTS_R),       # absolute path: unrepresentable
    (3, "../etc/shadow",   RIGHTS_R),       # traversal out of the preopen
    (4, "app.log",         RIGHTS_W),       # write-only preopen, writing
    (4, "app.log",         RIGHTS_R),       # ... but reading was never granted
    (7, "anything",        RIGHTS_R),       # fd 7 is not a preopen at all
]
print("A. capability enforcement (path_open against preopens)")
for fd, path, want in cases:
    verdict, why = host.path_open(fd, path, want)
    print(f"   {verdict}  path_open({fd}, {path!r}, {fmt_rights(want)})  # {why}")

# ---- Part 2: preview1 fd_write(fd, iovs_ptr, iovs_len, nwritten_ptr) ----
# fd_write takes a pointer to a ciovec array *inside guest linear memory*:
#   ciovec { buf: u32 ptr, buf_len: u32 }   (little-endian, 4-byte fields)
BASE    = 1024                            # guest address where we lay out data
PAYLOAD = b"Hello, WASI\n"
EXTRA   = b"second iovec\n"

buf1, buf2 = BASE + 24, BASE + 24 + len(PAYLOAD)          # buffer addresses
iov_base  = BASE                                          # iovec array address
image  = bytearray(24 + len(PAYLOAD) + len(EXTRA))
struct.pack_into("<II", image, 0, buf1, len(PAYLOAD))     # iovs[0]
struct.pack_into("<II", image, 8, buf2, len(EXTRA))       # iovs[1]
image[24:24+len(PAYLOAD)] = PAYLOAD                       # buffer contents
image[24+len(PAYLOAD):] = EXTRA
nwritten_ptr = BASE + 24 + len(PAYLOAD) + len(EXTRA)      # scratch for result

print("B. fd_write(1, iovs_ptr=%d, iovs_len=2, nwritten_ptr=%d)" %
      (iov_base, nwritten_ptr))
print("   iovs[0] = { ptr=%d, len=%d } -> %r" %
      (buf1, len(PAYLOAD), bytes(image[24:24+len(PAYLOAD)])))
print("   iovs[1] = { ptr=%d, len=%d } -> %r" %
      (buf2, len(EXTRA), bytes(image[24+len(PAYLOAD):])))
total = len(PAYLOAD) + len(EXTRA)
print("   errno=0 (SUCCESS), *nwritten = %d" % total)
print("   first 16 bytes of iovec array: %s" % image[:16].hex(" "))
```

Real output (executed with `python3`, stdlib only):

```text
A. capability enforcement (path_open against preopens)
   ALLOW  path_open(3, 'input.csv', R-)  # fd 5 under /srv/data
   ALLOW  path_open(3, 'sub/config.yaml', R-)  # fd 6 under /srv/data
   DENY  path_open(3, '/etc/passwd', R-)  # path_open cannot name absolute paths
   DENY  path_open(3, '../etc/shadow', R-)  # '../etc/shadow' resolves outside preopen /data
   ALLOW  path_open(4, 'app.log', -W)  # fd 7 under /var/log
   DENY  path_open(4, 'app.log', R-)  # needs R- but preopen grants -W
   DENY  path_open(7, 'anything', R-)  # fd 7 is not a preopen
B. fd_write(1, iovs_ptr=1024, iovs_len=2, nwritten_ptr=1073)
   iovs[0] = { ptr=1048, len=12 } -> b'Hello, WASI\n'
   iovs[1] = { ptr=1060, len=13 } -> b'second iovec\n'
   errno=0 (SUCCESS), *nwritten = 25
   first 16 bytes of iovec array: 18 04 00 00 0c 00 00 00 24 04 00 00 0d 00 00 00
```

## What WASI sandboxing does and does not guarantee

| Property | Guaranteed? | Reality |
|---|---|---|
| No I/O without a granted import | Yes | Enforced by the engine's import linking; unlinked imports fail instantiation |
| Memory isolation between instances | Yes | Wasm spec: checked linear memory, no raw pointers escaping |
| Paths confined to preopens; no rights escalation | Yes, for a correct host | `path_open` resolves under the dirfd (escape -> `NOTCAPABLE`); rights only narrow, never widen |
| CPU / memory / wall-clock limits | No | WASI says nothing about quotas; metering is an engine feature the operator must enable |
| Side channels (Spectre-class) | No | Same story as [sandboxing.md](../security/advanced/sandboxing.md); timing isolation is out of scope |
| Freedom from engine bugs | No | Wasmtime documents defense-in-depth (guard regions, memory zeroing) precisely because residual bugs exist |
| Safe misconfiguration | No | The grant *is* the authority: `--dir /` is a self-inflicted capability leak no runtime will second-guess |

Two nuances matter for interviews. First, the *host runtime is the trusted computing base*: it mediates every syscall and owns the grants, so its bugs subsume WASI's guarantees. Second, preview1's design gives the host (and thus, symmetrically, the guest's full linear memory is exposed to host calls) no fine-grained protection: the witx README is explicit that preview1 callees see the caller's entire linear memory. Fine-grained sharing is one of the problems preview2's component model set out to fix.

## WASI vs containers, honestly

WASI occupies a different layer than containers: an *ABI with explicit capabilities* versus an *OS-level packaging and isolation stack*. Concretely: a container trusts the host kernel and namespaces (ambient authority: root filesystem and network namespace are visible by default and must be *revoked*); a WASI module has no kernel, gets handles only, and its authority must be *granted*. A container image carries a libc, a rootfs, and everything below the app; a WASI component carries only the app and imports the rest, which is why footprints are measured in kilobytes-to-megabytes and startup in milliseconds rather than seconds. The costs are equally real: no process supervision, no volume manager, no ambient network stack, and a syscall surface far smaller than Linux's (see the perf-oriented table in [webassembly.md](./webassembly.md); this page adds only the guarantee angle). The ecosystems converge rather than compete: `runwasi` schedules Wasm through containerd/Kubernetes, while a Wasmtime process itself is routinely packaged *in* a container.

## Where WASI actually runs today

| Deployment | What it does | WASI shape |
|---|---|---|
| Fastly Compute | Customer-compiled Wasm services executed at CDN edge nodes on every request | The `fastly compute serve` local workflow is powered by Viceroy, Fastly's open-source test server whose build embeds `wasmtime` and `wasmtime-wasi` |
| Shopify Functions | Merchant/app logic compiled to Wasm modules ("any language that can compile a WebAssembly module") that extend checkout etc. under platform-enforced limits | Wasm modules behind Shopify's host API surface |
| wasmCloud | Distributed actors/components whose capabilities (keyvalue, http, blob store) are declared as interfaces and injected by hosts | CNCF incubating project built on Wasm components |
| .NET / Python hosts | Applications embedding a WASI host to run plugins: `wasmtime-dotnet`, `wasmtime-py` | Preview1 and preview2 via Wasmtime's C API |

## Interview-style questions

**Q: Why can't a WASI program read `/etc/passwd`?**
A: Because WASI has no `open()` -- only `path_open` on a directory handle the runtime preopened. `/etc/passwd` is outside every preopen root, so no sequence of syscalls can name it. Authority is structural, not policy-checked.

**Q: A plugin asks for `path_open(preopen, "../secrets")`. What happens?**
A: The host resolves the path relative to the preopen root and, since the result leaves the granted subtree, returns `errno::notcapable` (the deny case in the demo above). Runtimes must implement this resolution carefully; the capability model assumes they do.

## Related pages

- [webassembly.md](./webassembly.md) -- core Wasm sandbox, GC, threads; contains the startup/memory container table
- [wasm-component-model.md](../compilers/advanced/wasm-component-model.md) -- WIT, worlds, canonical ABI behind preview2/0.2
- [wasm-runtimes.md](../compilers/advanced/wasm-runtimes.md) -- engine internals: Wasmtime, WAMR, wasmer, V8
- [sandboxing.md](../security/advanced/sandboxing.md) -- WASI as one layer in a defense-in-depth stack
- [containerd.md](../linux/containers/containerd.md) / [crun.md](../linux/containers/crun.md) -- the container-side shims (runwasi)

## References

- WebAssembly/WASI repo (README, 0.2/0.3 status) -- https://github.com/WebAssembly/WASI
- WASI proposals and subgroup phase status -- https://github.com/WebAssembly/WASI/blob/main/docs/Proposals.md
- wasi.dev (official site; preview1/2/3 overview) -- https://wasi.dev/
- Canonical preview1 witx (function definitions) -- https://github.com/WebAssembly/WASI/blob/wasi-0.1/preview1/witx/wasi_snapshot_preview1.witx
- wasi-0.1 docs branch (preview0 `wasi_unstable` / preview1 history) -- https://github.com/WebAssembly/WASI/tree/wasi-0.1
- wasi-cli v0.2.0 release (WASI 0.2 snapshot) -- https://github.com/WebAssembly/wasi-cli/releases/tag/v0.2.0
- Wasmtime book: security and sandbox model -- https://docs.wasmtime.dev/security.html
- Wasmtime book: CLI options (`--dir` preopen grants) -- https://docs.wasmtime.dev/cli-options.html
- Node.js `node:wasi` API (experimental preview1) -- https://nodejs.org/api/wasi.html
- Fastly Compute documentation -- https://developer.fastly.com/learning/compute/
- Viceroy, Fastly's Compute local test server (embeds wasmtime) -- https://github.com/fastly/Viceroy
- Shopify Functions documentation -- https://shopify.dev/docs/apps/build/functions
- wasmCloud (CNCF incubating) -- https://github.com/wasmCloud/wasmCloud
- wasmtime-py / wasmtime-dotnet embeddings -- https://github.com/bytecodealliance/wasmtime-py / https://github.com/bytecodealliance/wasmtime-dotnet
- containerd runwasi (Wasm workloads via containerd) -- https://github.com/containerd/runwasi
- Wasmer (WASI + WASIX) -- https://github.com/wasmerio/wasmer
