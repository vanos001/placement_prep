# Android OS Internals

## Table of Contents

- [Why "Internals" Matter in Interviews](#why-internals-matter-in-interviews)
- [System Stack Overview](#system-stack-overview)
- [The `init` Process and `init.rc`](#the-init-process-and-initrc)
- [The Zygote and Application Forking](#the-zygote-and-application-forking)
- [Android Runtime (ART) vs Dalvik](#android-runtime-art-vs-dalvik)
- [Binder IPC](#binder-ipc)
- [ServiceManager and AIDL](#servicemanager-and-aidl)
- [Activity Manager Service (AMS)](#activity-manager-service-ams)
- [Package Manager Service (PMS)](#package-manager-service-pms)
- [The Framework Layer](#the-framework-layer)
- [Comparison to iOS](#comparison-to-ios)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Why "Internals" Matter in Interviews

Most Android developers never touch the platform layer — they write Kotlin, use
Jetpack libraries, and let the framework do the heavy lifting. But placement
interviewers for system engineering, platform, or framework roles want to know
what happens *below* `Activity.onCreate`. This page covers exactly that layer:
the kernel-to-framework stack that makes Android process isolation, IPC,
component resolution, and lifecycle management possible. If you can explain the
Zygote fork model and Binder transactions clearly, you stand out from
candidates who only know the SDK.

## System Stack Overview

Android is not "a Linux distribution with a UI". It is a Linux kernel plus a
purpose-built user-space that reuses almost none of the GNU userspace you find
on a typical Linux box — no glibc, no systemd, no X11, no GNU coreutils.

```
┌──────────────────────────────────────────────────────────┐
│  Apps (Java/Kotlin compiled to DEX, run in ART)           │
├──────────────────────────────────────────────────────────┤
│  Framework API (android.*) — Activity, View, Window,    │
│  NotificationManager, PackageManager, ContentProvider    │
├──────────────────────────────────────────────────────────┤
│  System Services (in system_server process)             │
│    AMS, PMS, WMS, NMS, InputFlinger, ...                │
├──────────────────────────────────────────────────────────┤
│  Native Daemons & Libraries                              │
│    surfaceflinger, audioserver, mediaserver, netd,       │
│    libc (bionic), libbinder, libutils                    │
├──────────────────────────────────────────────────────────┤
│  Android Runtime (ART) — per-app instance, forked from   │
│  the Zygote process                                      │
├──────────────────────────────────────────────────────────┤
│  Hardware Abstraction Layer (HAL) — HIDL / AIDL          │
├──────────────────────────────────────────────────────────┤
│  Linux Kernel — modified ( Binder, ashmem→memfd, wakelock)│
└──────────────────────────────────────────────────────────┘
```

Two features in the kernel are Android-specific:

- **Binder** — a character device (`/dev/binder`) implementing a capability-based
  IPC mechanism with one-shot copy of payload data and ref-counted object
  passing across processes.
- **ashmem / memfd** — anonymous shared memory regions used for graphics buffers
  and large IPC payloads (avoid a second copy).

Everything else — process scheduling, memory management, file systems (ext4,
f2fs), drivers — is upstream Linux.

## The `init` Process and `init.rc`

PID 1 on Android is `/init`, a custom binary *not* based on systemd or
sysvinit. It parses `.rc` text files written in an Android-specific
declarative language and triggers actions and starts services based on
triggers.

A trimmed example of `init.rc` (from AOSP `system/core/rootdir/init.rc`):

```
on early-init
    write /proc/1/oom_score_adj -1000
    setrlimit 8 -1 -1  # RLIMIT_CORE

on init
    sysclktz 0
    setenv HOSTNAME localhost
    symlink /proc/self/fd/0   /dev/stdin

on zygote-start
    start zygote
    start zygote_secondary

service zygote /system/bin/app_process -Xzygote /system --start-system-server
    class main
    socket zygote stream 660
    onrestart write /sys/android_power/request_state wake
    onrestart restart media
    user root
    group root readproc reserved_disk
    priority -20
    critical
```

Key things `init` does:

1. Mounts `/proc`, `/sys`, `/dev`, `/data`, `/system`, `/vendor`.
2. Sets kernel parameters (`write /proc/...`).
3. Starts critical daemons: `ueventd`, `logd`, `servicemanager`, `hwservicemanager`,
   `vold`, `netd`, `surfaceflinger`, `zygote`.
4. Restarts a `critical` service in a tight loop if it exits — if too many
   restarts occur, the device reboots (panic recovery).

`init` is event-driven: actions fire on triggers like `on boot`,
`on property:sys.boot_completed=1`, `on charger`. Property writes (`setprop`)
go through the property service, a socket served by `init` itself.

## The Zygote and Application Forking

The **Zygote** is the parent process of every Android app. It is started by
`init`, preloads the entire framework class hierarchy and a heapful of common
resources, then opens a socket (`/dev/socket/zygote`) and waits for fork
requests.

The flow when you tap an app icon:

```
Launcher (app) ── AMS.startActivity ──► Zygote socket
                                            │
                                            ▼
                                       fork()
                                            │
                ┌──────────────────────────┴──────────────┐
                │                                           │
        child process (PID = new app)         parent (Zygote stays alive)
                │
                ▼
        App's main(), ActivityThread.attach()
```

Why fork? Because forking a process that has already loaded the
`android.*` classes (~10k+ classes, hundreds of MB of memory) gives the child a
fully initialized heap instantly, *without* re-running class loading or
relinking. The cost is a single `fork()` syscall (~1 ms) plus a CoW page table.

Some classes are *not* preloaded (e.g. app-specific code). App DEX files are
loaded by the child after fork. ART uses `dex2oat` to pre-compile installed APKs
to `.odex`/`.vdex`/`.oat` files, so loading is mostly mmap.

The Zygote also picks up the right UID/GID/seccomp policy from the package's
`AndroidManifest.xml` via `setresuid` after fork — that's how per-app sandboxing
is enforced.

## Android Runtime (ART) vs Dalvik

**Dalvik** was the original interpreter-and-JIT VM, written by Dan Bornstein
and shipped through Android 4.4. Dalvik ran its own bytecode format (Dalvik
Executable, `.dex`), optimized for low-memory devices. Register-based
(vs. JVM stack-based) to keep instruction count low.

**ART** replaced Dalvik fully in Android 5.0 (Lollipop). ART is still a
register-based VM running DEX bytecode, but the compilation strategy changed:

| Aspect | Dalvik | ART (modern) |
|---|---|---|
| Install-time | Copy .apk | `dex2oat` → `.vdex`/`.odex`/`.oat` |
| Runtime | JIT interpreter | AOT + profile-guided JIT (PGO) |
| GC | Concurrent mark-sweep (stop-the-world heavy) | Concurrent copying GC (Region-based, generational) |
| Code cache | none | Per-app `.art` boot image + app image |
| Deoptimization | n/a | On-stack replacement (OSR) supported |

ART's compilation pipeline since Android 7.0:

```
  DEX bytecode
       │
       ▼
  Quick compiler  ──(profiling)──►  AOT (dex2oat)
       │                                  │
       ▼                                  ▼
  JIT (hot methods)              .oat (compiled native)
       │                                  │
       └───── runtime picks best ─────────┘
```

This is called **profile-guided compilation**: the app runs in interpret+JIT
mode for a few runs, ART writes a profile of hot methods, and an idle job runs
`dex2oat --compilation-filter=speed-profile` against that profile to produce a
focused AOT image. Best of both worlds: fast cold start (no huge AOT) and
warm-state native performance (JIT/AOT for hot code).

## Binder IPC

Binder is the only general-purpose IPC mechanism the framework uses.
Sockets, pipes, and shared memory exist but are layered on top or used
in narrow cases (e.g. media buffers).

Binder's design:

- **Single copy**: a `binder_write_read` ioctl on `/dev/binder` does one
  `copy_from_user` of the payload into the target process's address space
  (via `binder_alloc`). A traditional pipe needs two copies (one to kernel,
  one out); Binder needs one.
- **Strong references**: passing a Binder object across processes creates a
  kernel-managed reference count. When the receiving process dies, refs are
  cleaned up. This is what makes `ServiceManager` lookups safe.
- **Thread pool**: the server process spawns a pool of threads (default 15)
  that block in `binder_thread_read`. When a transaction arrives, one thread
  is woken and runs the onTransact handler.

Transaction layout (simplified, from `drivers/android/binder.c`):

```
struct binder_write_read {
    binder_size_t      write_size;
    binder_size_t      read_size;
    binder_uintptr_t  write_buffer;   /* points to BC_* commands */
    binder_uintptr_t  read_buffer;    /* points to BR_* replies */
};

struct binder_transaction_data {
    union { __u32 handle; binder_uintptr_t ptr; } target;
    binder_uintptr_t cookie;     /* server-side pointer to BBinder */
    binder_uintptr_t sender_pid;
    binder_size_t    data_size;
    binder_uintptr_t data.ptr.buffer;
    binder_size_t    offsets_size;     /* offsets of binder objects in payload */
    binder_uintptr_t data.ptr.offsets;
};
```

From the user-space perspective, a Binder transaction is:
`IBinder.transact(code, data, reply, flags)` on the client side, and
`BBinder.onTransact(code, data, reply, flags)` on the server side.

## ServiceManager and AIDL

The **`servicemanager`** is a tiny native binary (`/system/bin/servicemanager`)
running as a special Binder context (`service` context, restricted by SELinux).
It acts as a name service for Binder objects.

Lifecycle of a system service:

```
1. Service starts (e.g. AMS in system_server)
2. Publishes itself:  defaultServiceManager().addService("activity", ams)
3. servicemanager stores mapping: "activity" → ref to AMS Binder
4. App calls:  ServiceManager.getService("activity")
5. servicemanager hands back a BinderProxy (proxy in app, ref in kernel)
6. App invokes: proxy.startActivity(...) → BC_TRANSACTION → kernel → AMS
```

**AIDL** (Android Interface Definition Language) is the IDL used to generate
these proxies automatically. Example AIDL:

```aidl
// IRemoteService.aidl
package com.example;

import com.example.User;

interface IRemoteService {
    int getPid();
    void addUser(in User user);          // "in" = client→server
    User getUser(in long id);           // return value marshalled back
    List<User> allUsers();
}
```

The `aidl` build tool generates a Java (or C++/NDK) class with:

- A `Stub` abstract class to extend (server side, dispatches `onTransact`).
- A `Proxy` inner class (client side, marshals args to Parcel).
- Marshalling via `Parcel.writeInterfaceToken()`, `writeInt()`,
  `writeStrongBinder()`, etc.

A `Proxy` call roughly does:

```java
@Override public int getPid() throws RemoteException {
    Parcel _data = Parcel.obtain();
    Parcel _reply = Parcel.obtain();
    int _result;
    try {
        _data.writeInterfaceToken(DESCRIPTOR);
        _remote.transact(Stub.TRANSACTION_getPid, _data, _reply, 0); // FLAG_ONEWAY off
        _reply.readException();
        _result = _reply.readInt();
    } finally {
        _reply.recycle();
        _data.recycle();
    }
    return _result;
}
```

Every Binder call is synchronous by default. Mark the method `oneway` in AIDL
and the kernel queues the transaction without blocking the caller; reply
Parcel is skipped.

## Activity Manager Service (AMS)

AMS runs inside the `system_server` process (PID ~700, started by Zygote with
the `--start-system-server` flag). It is the central authority for:

- Process lifecycle (asking Zygote to start/kill app processes)
- Activity stack management (back stack, tasks, launch modes)
- Intent resolution and broadcast dispatch
- Permission checks for component access
- Memory trimming decisions when the device is under pressure

A simplified version of "start an activity":

```
app: Context.startActivity(intent)
     │
     ▼
Instrumentation.execStartActivity(...)
     │  (Binder call into AMS via IActivityManager proxy)
     ▼
AMS.startActivity(...)              [in system_server]
     │
     ├─ resolveIntent via PMS
     ├─ check permissions
     ├─ find or create a TaskRecord / ActivityRecord
     ├─ if needed: ask Zygote to fork a process for the target app
     │        via Process.start() → zygote fork
     │
     ▼
ApplicationThread (Binder, in the target app)
     │  (Binder call into the app)
     ▼
ActivityThread.main() → bind Application → call onCreate → ...
```

AMS keeps a `ProcessRecord` per app with OOM adjustment level
(`oom_adj` from -1000 system server down to +999 cached empty processes). The
kernel lowmemorykiller (older Android) or `lmkd` (modern) uses these to pick
victims when memory is short.

## Package Manager Service (PMS)

`PackageManagerService` is also in `system_server`. On boot, PMS scans every
APK in `/system/app`, `/system/priv-app`, `/vendor/app`, `/product/app`, and
`/data/app`, parses `AndroidManifest.xml`, and builds an in-memory database
(`packages.xml` persisted on `/data/system/`) of:

- Packages (package name, version, code path, resource path).
- Components: activities, services, receivers, providers.
- Permissions (declared, requested, granted).
- Signatures and package certificate digests.
- User-id assignments (Android UID for each installed package name).

When `startActivity` needs to know which class to launch, AMS calls
`PMS.resolveActivity(intent, ...)`. PMS consults its intent filters table
and returns the best matching `ActivityInfo`. Without PMS, intent resolution
would have to scan every APK on every call — unworkable.

At install time (`pm install` or via PackageInstaller UI), PMS:
1. Verifies the APK signature.
2. Acquires a UID for the package.
3. Copies the APK to `/data/app/<package>-<random>/base.apk`.
4. Runs `dex2oat` (now `dex2oatd`).
5. Updates `packages.xml` atomically.
6. Broadcasts `ACTION_PACKAGE_ADDED`.

## The Framework Layer

The framework layer (`framework/base/` in AOSP) is the Java code shipped in
`framework.jar`. It is the public API surface developers call —
`android.app.Activity`, `android.view.View`, `android.content.Context`,
`android.media.MediaPlayer`, etc. It also contains the implementations of the
"manager" interfaces (`ActivityManager`, `PackageManager`, `WindowManager`)
which are proxies into `system_server`.

A typical manager call:

```java
// In your app
WindowManager wm = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
wm.addView(view, params);  // actually calls into WindowManagerService via Binder
```

`getSystemService(name)` returns a cached proxy whose backing `IBinder` is
fetched from `ServiceManager` on first use. Hence the framework layer is
"thin": it validates arguments, builds Parcels, and dispatches Binder
transactions into the appropriate system service.

## Comparison to iOS

Android and iOS solve the same problem — a secure, sandboxed, multi-process
mobile OS — but the architecture differs sharply.

| Aspect | Android | iOS |
|---|---|---|
| Kernel | Linux + Binder driver | XNU (Mach + BSD + IOKit) |
| IPC | Binder (one-copy, refcounted) | Mach messages + XPC (since iOS 5) |
| App execution | Each app = separate Linux process, forked from Zygote | Each app = separate Mach task, `posix_spawn` from `launchd` |
| Runtime | ART (AOT+JIT, DEX bytecode) | Compiles to native ARM64; no VM. Swift/Obj-C direct. |
| System services | `system_server` process holds ~70 services | `launchd` spawns daemons; many in `runningboardd`, `SpringBoard` |
| IPC registry | `servicemanager` (single, central) | `launchd` plist files + `xpc_object` discovery |
| Memory reclaim | `lmkd` (lowmemorykiller daemon) by `oom_adj` | `jetsamd` based on memory pressure tiers |
| Background limits | Doze, App Standby, Background limits since 8.0 | Background task limits since iOS 7, tighter by far |
| Code sharing | Preloaded classes in Zygote shared via CoW | Shared dyld cache (read-only, prelinked) |

iOS has no equivalent of the Zygote — there is no pre-warmed, fully loaded
runtime waiting to be forked. App cold-starts on iOS therefore pay the full
cost of loading the system framework (mitigated by the read-only dyld shared
cache, which mmaps the prelinked UIKit/CoreFoundation into every process).
Android amortizes that cost via the Zygote's preloaded heap.

iOS apps run native code, so there is no JIT, no GC, no interpreter — this is
why iOS historically had smoother UI performance. ART's AOT+PGO closed much of
that gap by Android 10.

## Interview Questions

**Q: Why does Android fork apps from Zygote instead of just `fork`-and-exec?**
A: Forking from Zygote gives the child process a fully initialized VM with the
entire `android.*` framework preloaded and pre-linked. `exec` would discard
that address space and force re-loading. Fork + CoW means the child inherits
the preloaded classes cheaply; only app-specific DEX needs to be loaded.

**Q: Why is Binder called a "one-copy" IPC? Regular pipes are "two-copy".**
A: A pipe copies the payload from user-space of the sender into a kernel
buffer, then from the kernel buffer into the receiver's user-space — two
copies. Binder uses `binder_alloc` to reserve address space in every Binder
process; the sender's `copy_from_user` lands directly inside the receiver's
pre-allocated buffer, so there is only one copy. Plus the receiver's thread
is woken only after the data is in place.

**Q: What is the difference between `ActivityManager` and `ActivityManagerService`?**
A: `ActivityManager` is a thin Java class in the framework that holds an
`IActivityManager` Binder proxy. `ActivityManagerService` is the actual
implementation in `system_server`. Every `ActivityManager.getRunningAppProcesses()`
call is a Binder transaction into AMS.

**Q: How does ART decide what to AOT-compile?**
A: Since Nougat, ART uses profile-guided dexlayout. New installs run in
JIT mode while collecting a profile of hot methods. After a defined idle window
(`/data/misc/profiles/cur/<package>/`), `dex2oat --compilation-filter=speed-profile`
runs to produce a focused AOT image. Cold-start methods that aren't in the
profile stay interpreted — keeps `.odex` size small.

**Q: Where does `servicemanager` fit in the boot sequence?**
A: `init` starts `servicemanager` *before* `zygote` and `surfaceflinger`,
because `system_server` (which is forked from Zygote) needs to register itself
with `servicemanager` to be discoverable by apps.

## References

- [Android Platform Architecture — developer.android.com](https://developer.android.com/guide/platform)
- [Binder — Android Open Source Project documentation](https://source.android.com/devices/architecture/hidl/binder-ipc)
- [Android Runtime (ART) — developer.android.com](https://developer.android.com/topic/performance/runtime)
- [Android Init Language — AOSP `system/core/init/README.md`](https://android.googlesource.com/platform/system/core/+/master/init/README.md)
- [AOSP `frameworks/base` source](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/)
- [AOSP `system/server` / `system_server` source](https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/java/com/android/server/)
- [Binder driver source — `drivers/android/binder.c`](https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/android/binder.c)
- [Dalvik bytecode — dalvikvm.com docs archive](https://source.android.com/devices/tech/dalvik)
- [ServiceManager source — `frameworks/native/cmds/servicemanager/`](https://cs.android.com/android/platform/superproject/+/master:frameworks/native/cmds/servicemanager/)
- [iOS Architecture Overview — Apple Developer](https://developer.apple.com/library/archive/documentation/Miscellaneous/Conceptual/iPhoneOSConceptual/iPhoneOSOverview/iPhoneOSOverview.html)
- [XPC — Apple Developer](https://developer.apple.com/documentation/xpc)
- [launchd man page — Apple](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/Introduction.html)
