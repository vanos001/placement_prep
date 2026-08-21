# React Native

## Table of Contents

- [The Original Pitch](#the-original-pitch)
- [The Legacy Architecture: The JS Bridge](#the-legacy-architecture-the-js-bridge)
- [Native Modules (Legacy)](#native-modules-legacy)
- [Hermes: A Purpose-Built JS Engine](#hermes-a-purpose-built-js-engine)
- [The New Architecture](#the-new-architecture)
- [JSI: Replacing the Bridge](#jsi-replacing-the-bridge)
- [Fabric: The New Renderer](#fabric-the-new-renderer)
- [TurboModules and Codegen](#turbomodules-and-codegen)
- [Comparison to Flutter](#comparison-to-flutter)
- [Performance Characteristics](#performance-characteristics)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## The Original Pitch

React Native was announced by Facebook in 2015 as "Learn once, write
anywhere" — not write once, run anywhere. The premise: you write UI in React's
declarative model using JavaScript, but the actual rendered components are the
platform's native views (`UIView`, `android.widget.View`). This contrasts with
Flutter, which renders its own pixels. The result is a UI that fits in
visually with the platform, but it is mediated by a JavaScript engine and a
message bridge.

Two pieces define the legacy stack:

1. **The JS thread**, running a JS engine (JSC, then Hermes) that executes your
   bundle and emits view-tree mutations.
2. **The native thread** (main thread on iOS / UI thread on Android), which
   owns the actual view hierarchy and applies those mutations.

Between them, the **bridge**.

## The Legacy Architecture: The JS Bridge

The bridge is an asynchronous, serialized, batched message channel between JS
and Native. Three queues flow over it:

- **Native → JS**: events (touch, layout, lifecycle). Marshalled as JSON.
- **JS → Native**: method calls on imported native modules.
- **JS → Native (view manager)**: `UIManager` setProps / manageChildren calls.

A single bridge transaction is roughly:

```
┌─────────────────────────────────────────────────────────────────┐
│  JS thread                                                      │
│   ┌───────────────────────────┐                                │
│   │ React render → ReactNative │  produces a payload of pending │
│   │   Reconciler               │  view updates:                 │
│   │                            │  ["createView",[4,"RCTView",...]],│
│   │                            │  ["setChildren",[3,[4,5,6]]],  │
│   │                            │  ["setProps",[...]]            │
│   └────────────┬───────────────┘                                │
│                │ batched per frame (16ms)                       │
└────────────────┼────────────────────────────────────────────────┘
                 │  JSON serialize → MessageQueue.processBatch
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│  Native thread                                                  │
│   ┌───────────────────────────┐                                │
│   │ JSThreadExecutor → call    │                                │
│   │ into UIManager.dispatchView│                                │
│   │  ManagerCommands            │                                │
│   └────────────┬───────────────┘                                │
│                ▼                                                │
│   Real UIView / android.view.ViewGroup hierarchy                │
└─────────────────────────────────────────────────────────────────┘
```

Each batch is serialised as JSON. For 60 fps, you have ~16 ms to compute the
React render, serialize, deserialise, apply props, lay out, paint. Anything
slower than that produces a dropped frame. The bridge is:

- **Asynchronous** — you cannot synchronously call back from JS into Native.
  If you tap a button and need to do a heavy native call then update UI, you
  cross the bridge twice.
- **Serialized** — every primitive is converted to JSON and back. Lists of
  large data (e.g. images, geopoints, audio buffers) are expensive.
- **Batched** — the JS thread produces a per-frame batch of commands. This
  means commands are coalesced but also that interactions between JS and
  Native that should be tight take a frame to round-trip.

## Native Modules (Legacy)

A native module is a Java (Android) or Objective-C (iOS) class registered with
the bridge. On the JS side it appears as an object whose method calls are
serialised and dispatched by the bridge.

Android example (Java):

```java
package com.example;

import com.facebook.react.bridge.*;
import com.facebook.react.module.annotations.ReactModule;

@ReactModule(name = "ToastModule")
public class ToastModule extends ReactContextBaseJavaModule {

    public ToastModule(ReactApplicationContext ctx) { super(ctx); }

    @Override public String getName() { return "ToastModule"; }

    @ReactMethod
    public void show(final String message, final int duration) {
        // runs on the native thread
        UiThreadUtil.runOnUiThread(() ->
            Toast.makeText(getReactApplicationContext(), message, duration).show()
        );
    }

    @ReactMethod(isBlockingSynchronousThread = true)
    public String getDeviceNameSync() {
        return android.os.Build.MODEL;
    }
}
```

JS side:

```js
import { NativeModules } from 'react-native';
const { ToastModule } = NativeModules;

// async (legacy bridge is async by default)
ToastModule.show('Hello', ToastModule.SHORT);

// sync (only when isBlockingSynchronousThread=true, and only on Android)
const model = ToastModule.getDeviceNameSync();
```

iOS example (Objective-C):

```objc
@interface ToastModule : RCTEventEmitter
@end

@implementation ToastModule

RCT_EXPORT_MODULE();

RCT_EXPORT_METHOD(show:(NSString *)message duration:(double)duration)
{
  dispatch_async(dispatch_get_main_queue(), ^{
    UIAlertController *alert = [UIAlertController
        alertControllerWithTitle:nil message:message
        preferredStyle:UIAlertControllerStyleAlert];
    // ...
  });
}

@end
```

The macros generate a registration table that the bridge uses to route calls.
The cost is non-trivial — arguments are boxed/unboxed through `RCTBridge`,
and each method call involves JS-to-JSON-to-native conversion.

## Hermes: A Purpose-Built JS Engine

Facebook open-sourced **Hermes** in 2019, an JS engine specifically designed
for React Native on mobile. Hermes replaced JavaScriptCore (JSC) on Android
as the default in React Native 0.70+.

Key features:

- **Bytecode precompilation**: Hermes ships a bytecode format (`.hbc`).
  Tooling compiles JS source to bytecode at build time, eliminating parse
  cost at runtime. App startup time drops significantly.
- **No JIT**: Hermes is purely an interpreter. JITs are memory-hungry and
  cause cold-start regressions; mobile apps prioritize predictable startup.
- **GC tuned for UI**: a generational, concurrent, defragmenting collector
  designed for short pauses (target under 50 ms).
- **`Proxy` and modern ES support**: with Hermes 0.12+, `Proxy`,
  `Reflect`, `Intl`, and ESM `import` are supported.

Build pipeline:

```
  index.js (your JS source)
        │  ▼ metro bundler
  bundle.js (single file, CommonJS or ESM)
        │  ▼ hermesc (build step)
  bundle.hbc (bytecode)
        │
        ▼
  bundled into APK / IPA
        │
        ▼
  Hermes runtime at app start loads bytecode → executes
```

Switching to Hermes typically improves RN app cold-start by 30–60% on Android.
Memory footprint is smaller than JSC. The downside: certain JIT-optimized
workloads (heavy numerical code) run slower; you'd offload those to native
modules anyway.

## The New Architecture

React Native 0.68 introduced opt-in "New Architecture" (0.74 made it default
for new apps). The new architecture is the union of three things:

1. **JSI** (JavaScript Interface) — replaces the bridge.
2. **Fabric** — new renderer for the view tree.
3. **TurboModules** + **Codegen** — replaces legacy native modules with
   typed, statically registered C++ modules.

```
┌────────────────────────────────────────────────────────────────┐
│ JS thread (Hermes)                                              │
│  React render → ReactNativeFabricReconciler                    │
│  NativeModules.TurboModule.method()  ───► JSI direct call       │
└─────────────────┬──────────────────────────────┬──────────────┘
                  │                               │
                  │ direct C++ call               │ direct C++ call
                  ▼                               ▼
┌────────────────────────────────────────────────────────────────┐
│ Fabric: C++ shadow tree → commit → native view tree            │
└────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────┐
│ TurboModules: C++ stubs dispatched synchronously               │
└────────────────────────────────────────────────────────────────┘
```

The key idea: stop serializing everything. JSI lets JS hold references to
C++ "host objects" and call methods on them with native C++ function pointers,
no JSON in the path.

## JSI: Replacing the Bridge

JSI is a thin C++ API that allows the JS engine (Hermes or JSC) to expose
"host objects" — C++ objects whose properties are looked up by
`jsi::HostObject::get(runtime, propId)` — directly to JS. JS code
can read properties, call functions, and pass/receive primitive types and
host objects without serialization.

A minimal TurboModule in C++:

```cpp
// math.h
#pragma once
#include <jsi/jsi.h>
using namespace facebook;

class MathModule : public jsi::HostObject {
public:
  jsi::Value get(jsi::Runtime& rt, const jsi::PropNameID& name) override {
    auto nm = name.utf8(rt);
    if (nm == "add") {
      return jsi::Function::createFromHostFunction(rt,
        jsi::PropNameID::forUtf8(rt, "add"), 2,
        [](jsi::Runtime& rt, const jsi::Value&, const jsi::Value* args, size_t n) {
          double a = n > 0 ? args[0].asNumber() : 0;
          double b = n > 1 ? args[1].asNumber() : 0;
          return jsi::Value(a + b);
        });
    }
    return jsi::Value::undefined();
  }
};

void install(jsi::Runtime& rt) {
  auto math = std::make_shared<MathModule>();
  rt.global().setProperty(rt, "MathNative",
    jsi::Object::createFromHostMemory(rt, math));
}
```

JS now calls:

```js
const sum = MathNative.add(2, 3);   // synchronous, no JSON, no async
```

Performance characteristics:

- No serialization — primitives pass via the engine's typed value API.
- Synchronous — JS can call native code and get a return value immediately,
  which matters for game loops, audio, gesture handling.
- No per-call thread hop — the JS thread executes the C++ function inline.
  Long-running work still needs to be offloaded.

## Fabric: The New Renderer

Legacy React Native maintains a "shadow tree" per platform in Java/ObjC.
Fabric moves the shadow tree into C++ so that layout commits are shared across
platforms. The flow:

```
1. React commits → JS calls Fabric's C++ reconciler directly via JSI
2. C++ shadow tree mutated: setProps, removeChild, appendChild, insertChild
3. Layout (Yoga) computes positions for new shadow nodes
4. Diff commits to a platform-specific "Fabric Container" on the UI thread
5. Native views (UIView/ViewGroup) updated with minimal churn
```

```
              ┌─── commit (one shot) ───►
   JS thread   │                          UI thread
              │                          │
   React render                          Yoga layout
       │                                  │
       ▼                                  ▼
   C++ shadow tree  ──── diff ────► native view tree
```

Why this helps: instead of a JSON batched message describing updates, Fabric
walks an in-memory C++ shadow tree directly, computes layout diff in C++
(shared between iOS and Android), and emits a single commit to the UI thread
with minimal work. Gesture response time falls from "next frame" to
"synchronous"; animations driven by `useAnimatedProps` (Reanimated 3) can
read layout values without crossing the bridge.

## TurboModules and Codegen

TurboModules are JSI-backed native modules. They're declared in a typed IDL
(TypeScript or Flow), and a code generator (`@react-native/codegen`)
produces C++ interfaces, JS spec files, and platform-specific scaffolding.

Spec (TypeScript):

```ts
// specs/NativeMathSpec.ts
import type { TurboModule } from 'react-native';
export interface Spec extends TurboModule {
  add(a: number, b: number): Promise<number>;
  addSync(a: number, b: number): number;
  getVersion(): string;
  readonly constants: {
    PI: number;
  };
}
```

`@react-native/codegen` produces:

- `NativeMathSpecJSI.h` — C++ interface your platform module implements.
- `NativeMathSpec.h` — C++ TurboModule spec.
- JS object: `import NativeMath from 'NativeMath';` with typed signatures.

Platform implementations on Android (Kotlin):

```kotlin
class MathModule(reactContext: ReactApplicationContext)
    : NativeMathSpec(reactContext) {

  override fun getName() = "NativeMath"
  override fun add(a: Double, b: Double, promise: Promise) {
    promise.resolve(a + b)
  }
  override fun addSync(a: Double, b: Double): Double = a + b
  override fun getVersion(): String = "1.0.0"
  override fun getConstants(): Map<String, Any> = mapOf("PI" to Math.PI)
}
```

Benefits: type-safe interface across JS/C++/Java/ObjC; no runtime discovery
(`NativeModules[name]` was untyped lookup); modules lazily loaded on first
use; synchronous calls possible.

## Comparison to Flutter

| Aspect | React Native (new arch) | Flutter |
|---|---|---|
| Language | JS / TS | Dart |
| Compilation | Hermes bytecode (interpreted) | Dart AOT (native) |
| UI primitives | Native views (UIView/ViewGroup) | Self-drawn via Skia/Impeller |
| Cross-thread comms | JSI direct C++ calls | Single isolate, none needed |
| Frame model | React render + Fabric commit + Yoga layout + native inflate | Build → layout → paint on UI thread, raster on GPU thread |
| Bundle size | Small (JS bundle ~1-2 MB) | Larger (Dart AOT runtime + app, ~6-10 MB) |
| Native interop | TurboModules via JSI | Method channels / FFI |
| Hot reload | Yes (Fast Refresh) | Yes |
| Native look-and-feel | Free (uses platform widgets) | Material/Cupertino approximations |
| Animations | Reanimated 3 runs on UI thread via JSI | Native, framework-baked |
| Web target | react-native-web (third party) | Flutter web (CanvasKit Wasm) |

Choose RN when: you need real platform UI parity, your team already writes
React, or you must share code with a React web app.

Choose Flutter when: you need pixel-perfect cross-platform UI, predictable
frame times (Impeller), a single language for mobile + desktop + web, or a
smaller team that wants one stack end-to-end.

## Performance Characteristics

Empirically (as of RN 0.74+ with Hermes + Fabric):

- **Cold start**: ~1-2 s on a mid-range Android device, faster on iOS due to
  smaller bundle parsing cost (Hermes bytecode load is fast).
- **JS execution**: ~2-5x slower than Dart AOT for compute-heavy work because
  Hermes is an interpreter. Reanimated 3 and JSI mitigate this for UI work by
  running animations on the UI thread without crossing back into JS.
- **Scroll perf**: 60 fps achievable on FlatList with proper `getItemLayout`,
  `keyExtractor`, and virtualization. Without those, the bridge can still be
  the bottleneck.
- **Animation perf**: With Reanimated's worklet runtime (a separate JS
  context on the UI thread), 60/120 fps animation is common. Without it,
  JS-driven animations may drop frames.

Flutter generally wins microbenchmarks and first-frame smoothness; RN's new
architecture closes the gap for most user-visible scenarios but the JS engine
remains a real overhead.

## Interview Questions

**Q: What is the React Native bridge, and what were its limitations?**
A: The legacy bridge is an asynchronous, batched, JSON-serialized message
channel between the JS thread and the native UI thread. Three queues flow
over it: native → JS events, JS → native module calls, JS → native view
mutations. Limitations: serialization cost, no synchronous calls back into
native, batch boundary at frame rate, and thread hop latency. The new
architecture (JSI, Fabric, TurboModules) replaces it.

**Q: What is JSI?**
A: The JavaScript Interface is a C++ API in the Hermes/JSC engine that lets
JS hold "host objects" — C++ instances with a `get(runtime, name)` lookup.
Method calls go directly from JS through C++ function pointers with no
serialization, allowing synchronous calls and zero-copy data passing.

**Q: Why did Facebook build Hermes instead of using V8 or JSC?**
A: V8 is too heavy for mobile (JIT, GC, multi-MB heap baseline). JSC works
but has no bytecode precompilation — RN apps were paying parse cost at every
cold start. Hermes ships a small bytecode format precompiled at build time,
eliminating parse cost, with a GC tuned for short pauses. The tradeoff is
no JIT, which is fine for RN's UI workload.

**Q: What is Fabric?**
A: The new React Native renderer. It maintains a C++ shadow tree shared
across iOS and Android, computes layout diff in C++ using Yoga, and commits
to the native view hierarchy in a single synchronous step on the UI thread.
This replaces the legacy "shadow tree per platform" model that communicated
through the bridge as JSON batches.

**Q: How do TurboModules differ from legacy native modules?**
A: Legacy modules are discovered at runtime by name (`NativeModules[name]`),
untyped, and invoked through the asynchronous bridge. TurboModules are
declared in a TypeScript/Flow spec, codegen produces C++/Java/ObjC
interfaces, and the resulting module is invoked synchronously via JSI with
type safety. Modules are also lazily loaded — only initialized on first use.

**Q: How would you choose between React Native and Flutter for a new app?**
A: If platform UI parity is non-negotiable (e.g. an iOS-style settings page
that matches UIKit precisely), or you have an existing React team and a
React web codebase to share with, pick RN. If you need predictable
performance, smaller team scales, one stack across mobile + desktop + web,
or unusual UI (heavy custom animations, charts), Flutter is more predictable.

## References

- [React Native official documentation](https://reactnative.dev/docs/getting-started)
- [The new architecture — reactnative.dev](https://reactnative.dev/docs/the-new-architecture/why)
- [Fabric renderer — reactnative.dev](https://reactnative.dev/architecture/fabric)
- [TurboModules — reactnative.dev](https://reactnative.dev/docs/the-new-architecture/pillars-turbomodules)
- [Codegen — reactnative.dev](https://reactnative.dev/blog/2023/03/09/the-new-architecture-in-react-native-074)
- [Hermes engine — github.com/facebook/hermes](https://github.com/facebook/hermes)
- [Hermes documentation — hermesengine.dev](https://hermesengine.dev/)
- [JavaScript Interface (JSI) — React Native blog](https://reactnative.dev/blog/2023/03/09/the-new-architecture-in-react-native-074)
- [Bridging in React Native — Facebook engineering blog (2017)](https://www.facebook.com/100064905140877/posts/react-native-bridging-in-2022-pf4763yoa5/)
- [Performance overview — reactnative.dev](https://reactnative.dev/docs/performance/overview)
- [Reanimated 3 — docs.swmansion.com/react-native-reanimated](https://docs.swmansion.com/react-native-reanimated/)
- [Comparison of React Native and Flutter — reactnative.dev FAQ](https://reactnative.dev/docs/faq#how-does-react-native-differ-from-flutter)
