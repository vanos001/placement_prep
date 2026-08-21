# Mobile Crash Reporting: Crashlytics, Sentry, Bugsnag

## Table of Contents

- [Why Crash Reporting Matters](#why-crash-reporting-matters)
- [The Crash Capture Mechanism](#the-crash-capture-mechanism)
  - [iOS: Mach Exception Handler and Signal Handler](#ios-mach-exception-handler-and-signal-handler)
  - [Android: UncaughtExceptionHandler and Tombstones](#android-uncaughtexceptionhandler-and-tombstones)
- [Symbolication: dSYM and ProGuard Mapping](#symbolication-dsym-and-proguard-mapping)
- [Crash Grouping: Stack Frame Hashing](#crash-grouping-stack-frame-hashing)
- [The Upload Pipeline](#the-upload-pipeline)
- [Crashlytics vs Sentry vs Bugsnag](#crashlytics-vs-sentry-vs-bugsnag)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Why Crash Reporting Matters

A mobile device is the world's most hostile production environment: hundreds of hardware
variants, OS version skew, thermal throttling, network jitter, background kills by the
OS, and user behaviour you can't reproduce locally. If your crash reporting is good, the
first time you learn about a new crash class is when **one** user reports it — not when a
review goes viral.

A crash reporter must solve three hard problems simultaneously:

1. **Capture** the machine state at the moment of the crash — even though the process is
   about to be killed.
2. **Symbolicate** the captured stack trace from raw memory addresses into readable
   function names and line numbers.
3. **Upload** the report without leaking PII, retrying on failure, and not generating
   duplicate reports.

Solving all three is what makes a mobile crash reporter far more complex than a server-side
reporter (where the process lives on, and you can just `try/catch` and email the stack).

---

## The Crash Capture Mechanism

### iOS: Mach Exception Handler and Signal Handler

iOS exposes two distinct ways to be notified of a crash:

**1. Mach exception handler.** Darwin is Mach-based. When the kernel is about to deliver
a hardware exception (EXC_BAD_ACCESS, EXC_BAD_INSTRUCTION, EXC_CRASH, etc.) to a thread,
it consults the task's exception ports. Any process can install a Mach exception handler
that gets the failing thread's register state and the offending instruction address.
Crash reporters prefer this path because:

- It catches **all** Mach-level faults, including native faults that the BSD signal layer
  turns into `SIGSEGV`/`SIGBUS` etc.
- It gives you `EXC_BAD_ACCESS` with the exact faulting address and the type of access
  (read/write/execute).
- It runs *before* the BSD signal layer, so you see the original fault semantics.

```c
// Simplified Mach exception handler install (Crashlytics / PLCrashReporter style).
#include <mach/mach.h>
#include <pthread/excfile.h>

static mach_port_t g_exception_port = MACH_PORT_NULL;

kern_return_t install_exception_handler(void) {
    // Allocate a port we'll receive exception messages on.
    kern_return_t kr = mach_port_allocate(mach_task_self(),
                                          MACH_PORT_RIGHT_RECEIVE,
                                          &g_exception_port);
    if (kr != KERN_SUCCESS) return kr;
    kr = mach_port_insert_right(mach_task_self(), g_exception_port,
                                g_exception_port, MACH_MSG_TYPE_MAKE_SEND);
    if (kr != KERN_SUCCESS) return kr;

    // Request EXC_MASK_BAD_ACCESS | EXC_MASK_BAD_INSTRUCTION | EXC_MASK_CRASH | ...
    exception_mask_t mask = EXC_MASK_BAD_ACCESS | EXC_MASK_BAD_INSTRUCTION
                          | EXC_MASK_ARITHMETIC | EXC_MASK_CRASH;
    kr = task_set_exception_ports(mach_task_self(), mask, g_exception_port,
                                  EXCEPTION_STATE_IDENTITY, MACHINE_THREAD_STATE);
    return kr;
}
```

When an exception arrives on `g_exception_port`, the reporter writes the register state,
the thread's backtrace (via `_Unwind_Backtrace`), the binary image list, and the faulting
address to a `.crash` file on disk — then either re-raises the original signal so the OS
processes the kill normally (the default behaviour apps expect) or marks itself as the
handler.

**2. Signal handler.** Some signals are not Mach faults — `SIGABRT`, `SIGBUS`, `SIGPIPE`,
`SIGSYS`. For these, you need to install handlers via `sigaction`:

```c
#include <signal.h>

static void signal_handler(int signo, siginfo_t *si, void *ctx) {
    void *callstack[128];
    int frames = backtrace(callstack, 128);
    backtrace_symbols_fd(callstack, frames, STDERR_FILENO);
    write_minidump(signo, si, ctx);
    // Re-raise so default disposition still fires (SIG_DFL → terminate).
    struct sigaction sa = { .sa_handler = SIG_DFL };
    sigaction(signo, &sa, NULL);
    raise(signo);
}

void install_signal_handlers(void) {
    struct sigaction sa = {0};
    sa.sa_sigaction = signal_handler;
    sa.sa_flags = SA_SIGINFO | SA_RESTART;
    const int signals[] = { SIGABRT, SIGILL, SIGSEGV, SIGFPE, SIGBUS, SIGPIPE, SIGSYS, SIGTRAP };
    for (size_t i = 0; i < sizeof(signals)/sizeof(signals[0]); ++i) {
        sigaction(signals[i], &sa, NULL);
    }
}
```

Two subtle gotchas:

- You **cannot** use `malloc` in a signal handler (it is not async-signal-safe). Crash
  reporters preallocate a fixed buffer at install time and write into it from the handler.
- Apple's C++ runtime uses `SIGABRT` (from `abort()`) for `std::terminate`, so you must
  *re-raise* the signal after capture; otherwise the abort is silent and the process is
  killed without a Crash Reporter entry.

### Android: UncaughtExceptionHandler and Tombstones

Android has two JVMs in play (the Dalvik/ART VM for Java, and the native layer for JNI).
The two layers report differently:

**Java layer:** any thread's uncaught exception bubbles up to
`Thread.setDefaultUncaughtExceptionHandler`. Crashlytics / Sentry / Bugsnag install their
own handler here, capture the Java stack trace, the device ABI, and metadata, and forward
to the previous handler (or call `System.exit` themselves to prevent looping):

```kotlin
import java.lang.Thread.UncaughtExceptionHandler

class AppCrashHandler(private val previous: UncaughtExceptionHandler?) : UncaughtExceptionHandler {
    override fun uncaughtException(t: Thread, e: Throwable) {
        val stackTrace = Log.getStackTraceString(e)
        val report = buildReportPayload(e, t, stackTrace)
        writeReportToDisk(report)
        previous?.uncaughtException(t, e)
        Process.killProcess(Process.myPid())
    }
}

class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val previous = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler(AppCrashHandler(previous))
    }
}
```

**Native layer:** when C/C++ code crashes (NULL deref, divide-by-zero), the kernel
delivers a signal to the ART process, ART's signal handler runs, dumps a tombstone, and
kills the process. A tombstone is a plain-text file in `/data/tombstones/tombstone_NN`
with:

- The signal number and faulting address.
- The register state for every thread.
- The backtrace of every thread (raw addresses).
- The list of loaded shared libraries and their load addresses.
- The currently running thread's stack memory dump.

```
*** *** *** *** *** *** *** *** *** *** *** *** *** *** *** ***
Build fingerprint: 'google/pixel7/bluefin:TQ3A.230705.001/10216780:user/release-keys'
ABI: 'arm64'
Timestamp: 2023-10-15 14:21:33.040220354+0100
Process uptime: 3d 4h 12m

Cmdline: com.example.app
pid: 8421, tid: 8433, name: RenderThread  >>> com.example.app <<<

signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0000000000000008
    x0  0000000000000000  x1  0000007fff30a000  ...
    ...
backtrace:
  #00 pc 000000000003a8f0  /data/app/.../lib/arm64/librenderkit.so (RenderQueue::flush()+80)
  #01 pc 000000000003b21c  /data/app/.../lib/arm64/librenderkit.so (RenderThread::main+28)
```

Tombstones are not readable by other apps (SELinux policy `tombstone_transfers`). SDKs
like Crashlytics use a *tombstone interception* path: they install a custom
`sigaction` for `SIGSEGV`/`SIGABRT`/`SIGBUS`/`SIGFPE`/`SIGILL`, write their own minidump
alongside the tombstone, and then chain to the original ART handler so the tombstone is
still created.

---

## Symbolication: dSYM and ProGuard Mapping

### dSYM (iOS)

A compiled iOS app is stripped of debug symbols in the final IPA. The function names and
line numbers live in a separate **dSYM** bundle (a Mach-O with `MH_DSYM` file type) that
Xcode produces alongside the build. The dSYM contains:

- A DWARF debug-info section mapping every address → `{symbol, file, line}`.
- A UUID that must match the UUID embedded in the app's Mach-O (Mach-O LC_UUID load
  command).

When a crash report is captured on device, you only have raw addresses:

```
Thread 0 crashed:
0   libsystem_kernel.dylib    	    0x18f8f1234 __pthread_kill + 8
1   libsystem_pthread.dylib   	    0x18fa89000 pthread_kill + 256
2   libsystem_c.dylib        	    0x18f789abc abort + 124
3   MyApp                     	    0x102a04abc 0x1029a0000 + 408252
```

To symbolicate, the crash reporter uploads the raw crash to its server, looks up the
matching dSYM by UUID in its archive, and rewrites:

```
3   MyApp  0x102a04abc  -[LoginViewController viewDidLoad] (LoginViewController.m:42)
```

If the dSYM is missing, you get garbage like `0x102a04abc 0x1029a0000 + 408252`. This is
why CI builds must upload dSYMs to Crashlytics/Sentry/Bugsnag automatically:

```bash
# In a Fastlane lane or Xcode build script.
UPLOAD_SYMBOLS_PATH="$PODS_ROOT/FirebaseCrashlytics/upload-symbols"
BUILD_DIR="$BUILD_DIR"
"$UPLOAD_SYMBOLS_PATH" -gsp "$SRCROOT/MyApp/GoogleService-Info.plist" \
                       -p ios "$DWARF_DSYM_FOLDER_PATH"
```

For bitcode-rebuilt apps (older iOS), Apple re-creates the binary, so you must download
the matching dSYM from App Store Connect before uploading.

### ProGuard / R8 mapping (Android)

Android's R8 (superseding ProGuard) shrinks and obfuscates your release builds.
`MyActivity.fetchUserToken()` becomes `a.b()`. The mapping file looks like:

```
com.example.MyActivity -> com.example.a:
    private java.lang.String fetchUserToken() -> a
    42:42:void onBindViewHolder(androidx.recyclerview.widget.RecyclerView$ViewHolder,int):129
```

When a Java crash arrives, the SDK's server replays the obfuscated stack through the
mapping to produce the original method names and line ranges. Upload the mapping file
in `app/build.gradle`:

```groovy
android {
    buildTypes {
        release {
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'),
                          'proguard-rules.pro'
        }
    }
}

// Firebase Crashlytics mapping upload (Gradle plugin handles automatically).
apply plugin: 'com.google.firebase.crashlytics'
firebaseCrashlytics {
    mappingFileUploadEnabled = true
}
```

For native (C/C++) crashes, you also need to upload Breakpad `.sym` files generated from
the original `.so` binaries via `dump_syms` (Sentry) or upload debug symbols via
Crashlytics' NDK plugin. Without these, the backtrace shows only `librenderkit.so`
addresses, not the function names.

---

## Crash Grouping: Stack Frame Hashing

A single crash class can happen millions of times. To produce a manageable dashboard,
crash reporters group crashes into "issues" — typically using a rolling hash over the
top N stack frames.

The naive approach: hash the entire stack trace. This fails because:

- Pointer addresses vary per build (ASLR, RelRO).
- Pointer addresses vary per device (per-process ASLR on iOS, allocator choice on
  Android).
- Stack frames near the top often include irrelevant dispatcher frames.

The standard algorithm:

1. **Symbolicate** the stack first.
2. Drop frames below a thread boundary (anything past `main` or past `Thread.run`).
3. Take the top **K** frames (commonly K=16) per thread.
4. Hash the normalized representation: `function_name + file_basename` (drop addresses,
   line numbers, and full paths to keep grouping stable across minor edits).
5. Combine thread hashes (XOR or sorted concatenation hash) to form the issue key.

```
Group key = SHA1(
    normalize( crashed_thread_top16_frames ) +
    normalize( other_thread_top8_frames  ) +
    exception_type + exception_message_first_line
)
```

This means a one-line change to a function *can* shift it out of the top-K frames and
fork a new issue — most reporters expose this as a "regressions" feature: a new group key
appearing in a release where it didn't appear before.

Crashlytics uses the top 4 frames of the crashed thread (configurable in dashboard
"stacktrace grouping"). Sentry has a configurable grouping algorithm called
`app:ingest:grouping` that uses a more involved similarity metric and can be tuned per
project.

---

## The Upload Pipeline

You cannot reliably upload a crash report at the moment of the crash, because:

- The process is being killed (network stack may be torn down).
- The crash handler runs in async-signal-safe context (no malloc, no network).
- The user may be on cellular and a 50 KB upload is unwelcome.

So the standard pipeline is:

```
   crash ─▶ handler runs ─▶ serialize to disk ─▶ process killed
                                                  │
                                                  │ next launch
                                                  ▼
   app launch ─▶ Crashlytics/Sentry/Bugsnag init ─▶ read pending crash files
                                                  │
                                                  ▼
                                          upload with retry
                                          (exponential backoff)
```

The serialization format is typically a small binary minidump (Breakpad format,
documented) or a custom plist/protobuf. The retry policy respects:

- Network type (defer on metered Wi-Fi).
- Battery level (defer if < 20%).
- Retry counter with exponential backoff and jitter.

A typical init flow:

```swift
import FirebaseCrashlytics

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        FirebaseApp.configure()
        // Crashlytics init. Pending crashes from previous launches upload here.
        // Custom keys set BEFORE configure() are included in the crash report.
        Crashlytics.crashlytics().setCustomValue("v2.4.1", forKey: "app_version_tag")
        Crashlytics.crashlytics().setUserID("u-918273")  // PII-safe user id
        return true
    }
}
```

```kotlin
class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // The Firebase Crashlytics SDK reads pending reports from
        // /data/data/<pkg>/files/Session.../reports and uploads on init.
        FirebaseApp.initializeApp(this)
        FirebaseCrashlytics.getInstance().setCustomKey("app_version_tag", "v2.4.1")
        FirebaseCrashlytics.getInstance().setUserId("u-918273")
    }
}
```

A subtle correctness issue: custom keys set during the previous session are not in the
next session's report unless persisted. Crashlytics solves this by writing custom keys to
disk synchronously on every `setCustomValue` call, so a crash later in the session has the
most recent values.

---

## Crashlytics vs Sentry vs Bugsnag

| Feature | Firebase Crashlytics | Sentry | Bugsnag |
|---------|---------------------|--------|---------|
| Owner | Google | Functional Software | SmartBear (acquired 2021) |
| iOS capture | PLCrashReporter (Mach + signal) | Own Cocoa SDK (Mach + signal) | Own Cocoa SDK |
| Android capture | Java + NDK (Breakpad-style) | Java + NDK (Breakpad) | Java + NDK |
| Symbol upload | `upload-symbols` (CLI + Gradle plugin) | `sentry-cli` | `bugsnag-android-gradle-plugin` |
| dSYM auto-upload | Gradle + CocoaPods script | Fastlane + Xcode build phase | Fastlane + Xcode build phase |
| Free tier | Unlimited (within Firebase project) | 5k events/mo | 7.5k events/mo |
| Self-hostable | No | Yes (Sentry self-hosted) | No |
| Grouping algorithm | Top-K frames | Stack similarity (customizable) | Top-K + exception type |
| Source maps for JS/React Native | Limited | Native support | Native support |
| Native (C/C++) crash support | Yes (NDK SDK) | Yes (Breakpad symbol upload) | Yes |
| Real-time stream | No (5–15 min delay) | Yes (issue streaming) | Yes (event streaming) |
| Release health | Yes (rolling adoption) | Yes (release sessions) | Yes (release stages) |

A typical decision rubric:

- **Crashlytics** if you're already on Firebase or need free unlimited events and don't
  care about sub-minute latency.
- **Sentry** if you need cross-platform (web + mobile + backend) correlation, custom
  grouping rules, or self-hosting for compliance.
- **Bugsnag** if your team prioritises the out-of-box dashboard UX, release staging (set a
  release as "in production"), and tight Jira/Slack integration.

---

## Interview Questions

1. **Why does iOS need both a Mach exception handler and a BSD signal handler?**
   The BSD signal layer (SIGSEGV, SIGBUS, etc.) is *derived* from Mach exceptions by
   `bsd_init`. Some fault types are caught cleanly by Mach (`EXC_BAD_ACCESS`) and contain
   richer information (faulting address, access type). But `SIGABRT` (from C++ `abort()`
   or `pthread_kill`), `SIGPIPE`, and `SIGSYS` are not Mach-level faults — they have no
   corresponding Mach exception, so they must be caught via `sigaction`. A robust reporter
   installs both because each catches a different set of fault types.

2. **Why can't you call `malloc` in a signal handler?**
   Signal handlers must be async-signal-safe. If a signal fires while another thread is
   inside `malloc`'s critical section (holding its internal lock), the signal handler
   calling `malloc` would deadlock. Crash reporters preallocate a fixed-size buffer at
   install time and use only async-signal-safe calls (`write`, `backtrace`,
   `sigaction`) in the handler itself.

3. **How does the upload pipeline handle the fact that the crashing process dies?**
   The signal/Mach handler writes a minidump file to the app's persistent storage using
   async-signal-safe `write` calls. The process is then killed. On the next app launch,
   the crash SDK initialises, reads pending reports from disk, and uploads them with
   exponential backoff. This is why you often see "a crash from yesterday" arrive in the
   dashboard after the user opens the app again.

4. **What is a dSYM, and what happens if you don't upload one?**
   A dSYM is a Mach-O file with `MH_DSYM` file type containing DWARF debug info. It maps
   addresses in the released binary back to `{symbol, file, line}`. If the matching dSYM
   (matched by UUID) is not uploaded, the crash report shows raw hex addresses instead of
   function names. Most platforms keep dSYMs "forever" (or as long as you support a
   release) so you can retroactively symbolicate crashes.

5. **How does R8/ProGuard obfuscation affect Android crash reports, and how is it
   undone?**
   R8 renames classes and methods to short names, so a crash stack will show `a.b.c()`.
   R8 also writes a `mapping.txt` file mapping obfuscated → original. The crash SDK's
   server replays each obfuscated frame through the mapping to produce the original
   method name, file, and approximate line range. The mapping file must be uploaded at
   build time and versioned per release — without it, the crash dashboard shows
   unreadable obfuscated stacks.

6. **Why is "top-K frames" the standard crash grouping algorithm? What goes wrong if you
   hash the entire stack?**
   Hashing the entire stack is brittle: any caller of a crashed function would shift the
   bottom of the stack and fork a new group. Worse, dispatcher frames at the top of the
   stack (like `Thread.run`) vary across OS versions and device models. Top-K (with K
   around 16) keeps grouping stable across OS updates while still being specific enough
   to distinguish real distinct crashes. Tradeoff: a small change to a function at the
   top of the stack can fork a new issue — most reporters expose this as a "regression
   detection" feature.

---

## References

- [Firebase Crashlytics documentation](https://firebase.google.com/docs/crashlytics)
- [Firebase Crashlytics — Customize crash reports](https://firebase.google.com/docs/crashlytics/customize-crash-reports)
- [Firebase Crashlytics — Deobfuscate reports with R8/ProGuard](https://firebase.google.com/docs/crashlytics/get-deobfuscated-reports)
- [Sentry — Mobile crash reporting](https://docs.sentry.io/platforms/apple/)
- [Sentry — Source maps and debug symbol upload (sentry-cli)](https://docs.sentry.io/product/cli/upload-symbol-sources/)
- [Bugsnag — Mobile error monitoring docs](https://docs.bugsnag.com/platforms/react-native/)
- [Apple — Understanding and analyzing crash reports](https://developer.apple.com/documentation/xcode/analyzing-a-crash-report)
- [Apple — Diagnosing issues using crash reports and device logs](https://developer.apple.com/documentation/xcode/diagnosing-issues-using-crash-reports-and-device-logs)
- [Apple — Mach exception handling (man task_set_exception_ports)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man/task_set_exception_ports.3.html)
- [Android — Inspect app crashes with tombstones](https://source.android.com/docs/core/ota/modular-system/tombstones)
- [Breakpad — Full client design docs (used by Sentry mobile SDK)](https://chromium.googlesource.com/breakpad/breakpad/+/master/docs/getting_started_with_breakpad.md)
- [RFC 8949 — CBOR (used by some minidump formats)](https://www.rfc-editor.org/rfc/rfc8949)
