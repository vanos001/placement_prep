# Flutter and Dart

## Table of Contents

- [What Makes Flutter Different](#what-makes-flutter-different)
- [The Rendering Engine: Skia vs Impeller](#the-rendering-engine-skia-vs-impeller)
- [The Three Trees: Widget, Element, RenderObject](#the-three-trees-widget-element-renderobject)
- [StatelessWidget vs StatefulWidget](#statelesswidget-vs-statefulwidget)
- [Dart's Concurrency Model: Single-Threaded Event Loop + Isolates](#darts-concurrency-model-single-threaded-event-loop--isolates)
- [Compilation: AOT vs JIT, and Hot Reload](#compilation-aot-vs-jit-and-hot-reload)
- [Flutter vs React Native](#flutter-vs-react-native)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## What Makes Flutter Different

Flutter is a UI toolkit, not a wrapper around native widgets. When you build a
button in React Native, you get a real `UIButton` on iOS and a real
`android.widget.Button` on Android. When you build a button in Flutter, you get
pixels drawn by Skia/Impeller into a single texture that the platform renders
as if it were a video. The platform contributes nothing to layout, painting,
or hit-testing of your UI.

The Flutter process on Android is essentially a Dart VM running an app's
Dart code that calls into the Skia (or Impeller) graphics library to draw.
Native platform surfaces appear only when you explicitly embed a platform view
(`AndroidView`, `UiKitView`), and even then they're composited via texture or
hybrid composition.

```
┌───────────────────────────────────────────────────────────┐
│              Dart code (your widgets, logic)               │
├───────────────────────────────────────────────────────────┤
│   Flutter Framework (widgets, rendering, gestures, anim)  │
├───────────────────────────────────────────────────────────┤
│   Engine (C++)  ─ Skia or Impeller  ─ Dart VM (also C++)   │
├───────────────────────────────────────────────────────────┤
│   Platform window (Android: SurfaceView / iOS: Metal layer)│
└───────────────────────────────────────────────────────────┘
```

## The Rendering Engine: Skia vs Impeller

Until Flutter 3.7, the engine used **Skia**, Google's mature 2D graphics
library (the same library behind Chrome and Android's hardware-accelerated
canvas). Flutter compiled Skia to native ARM and called its drawing primitives
via a thin C++ layer called **Engine**, exposing the `dart:ui` library to Dart.

The render loop on Android:

```
┌────────────────────────────────────┐
│ Dart: Widgets.bindPipeline         │   ← onDraw → handleBeginFrame
└──────────────┬─────────────────────┘
               │
               ▼
┌────────────────────────────────────┐
│ Renderer: RenderObject tree        │   ← layout → paint → composite
└──────────────┬─────────────────────┘
               │
               ▼
┌────────────────────────────────────┐
│ SceneBuilder → Layer tree          │   ← transfer (no Dart code here)
└──────────────┬─────────────────────┘
               │ (skp)
               ▼
┌────────────────────────────────────┐
│ Engine: raster (GPU) thread        │   ← Skia GPU → GL/Metal/Vulkan
└────────────────────────────────────┘
```

Each frame the UI thread produces a `Scene` containing an SkPicture-like
description of draw commands; a separate raster thread consumes that scene and
issues GPU commands. This is why a slow Dart build method doesn't necessarily
block rasterization — they're on different threads.

**Impeller**, introduced in Flutter 3.10 on iOS and later on Android,
replaces Skia for rendering. Its motivation:

- Skia's pipeline compilation (shader compilation) happened at runtime → first
  frame of a complex animation would stutter ("jank"). Impeller pre-compiles
  shaders offline (`impellerc`) so the GPU pipeline is ready before runtime.
- Impeller uses a modern, explicit, Vulkan-style command buffer API and
  renders via Metal on iOS, Vulkan/OpenGLES on Android. Skia's renderer
  targeted each backend separately.
- Impeller is designed to drop frames cleanly when behind, rather than stutter.

In short: Impeller = precompiled shaders + explicit-API + tessellation-at-build,
designed to eliminate shader-compile jank and produce predictable frame times.

References:

- [Flutter's rendering pipeline — docs.flutter.dev](https://docs.flutter.dev/resources/architectural-overview#rendering-pipeline)
- [Impeller announcement — medium.com/flutter](https://medium.com/flutter/impeller-a-new-rendering-runtime-for-flutter-85f4f4f6c0f6)

## The Three Trees: Widget, Element, RenderObject

This is the single most important Flutter concept, and the one that
distinguishes it from React's two-tree (vDOM + DOM) model. Flutter has three
trees:

```
   Widget tree (immutable descriptions)         ┐
        │                                      │  diff / rebuild
        ▼                                      │  every setState
   Element tree (mutable state + refs)         │
        │                                      │
        ▼                                      │
   RenderObject tree (layout, paint, hit-test) ┘
```

- **Widget**: immutable configuration objects. They are *descriptions* of
  desired UI. Every `build()` call returns brand new `Widget` instances.
- **Element**: the live, mutable instance of a widget. There's an `Element`
  tree in memory that mirrors the current widget tree. When a widget changes,
  the framework updates the corresponding Element if `runtimeType` and `key`
  match — otherwise it tears down and rebuilds the Element subtree.
- **RenderObject**: the actual layout and paint engine. `RenderBox`,
  `RenderFlex`, `RenderParagraph`, etc. implement `layout()`, `paint()`,
  `hitTest()`. They are what produce pixels.

Why three trees? Because the Widget layer must be immutable to enable diffing
cheaply (`canUpdate`); but you need *state* (the current text cursor, the
scroll offset, the open/closed flag) which lives in the Element layer (the
`State` object of a `StatefulWidget` is owned by its `Element`); and the
layout/paint layer needs a separately optimized, dirty-flag-based, retainable
tree that lives below the widget API.

Example diff flow:

```dart
class CounterApp extends StatefulWidget {
  @override State<CounterApp> createState() => _CounterState();
}

class _CounterState extends State<CounterApp> {
  int _count = 0;

  void _inc() => setState(() => _count++);

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text('$_count'),                 // new Text('0') → new Text('1')
        TextButton(onPressed: _inc, child: const Text('+')),
      ],
    );
  }
}
```

On `setState`:

1. `_CounterState` marks its `Element` dirty via `markNeedsBuild()`.
2. Next frame, framework calls `build()` → returns new `Column` widget.
3. Diff against previous `Column`: same `runtimeType`, same `key` (null) →
   reuse the `Element`. Walk children.
4. First child `Text('0')` vs `Text('1')` — same type, so the existing
   `TextElement` is reused; the `RenderParagraph` underneath gets its `text`
   property updated; it marks itself dirty for layout/paint.
5. Second child unchanged — no work.

A change in `runtimeType` (e.g. swap `Text` for `Icon`) causes the framework
to unmount the old `Element`, call its `RenderObject.detach`, and mount a new
one.

## StatelessWidget vs StatefulWidget

```dart
class Greeting extends StatelessWidget {
  const Greeting({super.key, required this.name});
  final String name;

  @override
  Widget build(BuildContext context) {
    return Text('Hello, $name!');
  }
}
```

`StatelessWidget` is a pure function of its constructor args. The framework
rebuilds it whenever its parent rebuilds and passes a `Widget` that isn't
`==` to the old one (the `canUpdate` rule based on `runtimeType` and `key`,
not `operator==`). It owns no mutable state.

```dart
class TimerCard extends StatefulWidget {
  const TimerCard({super.key});
  @override State<TimerCard> createState() => _TimerCardState();
}

class _TimerCardState extends State<TimerCard> {
  Duration _elapsed = Duration.zero;
  late final Ticker _ticker;

  @override
  void initState() {
    super.initState();
    _ticker = Ticker(_onTick)..start();
  }

  void _onTick(Duration elapsed) {
    setState(() => _elapsed = elapsed);
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Text('${_elapsed.inSeconds}s');
}
```

`StatefulWidget`'s `State` object persists across rebuilds — the
`State` instance is held by the `Element`, not the `Widget`. That's why
`initState` runs once even when the widget is rebuilt 100 times: the
`Element` survives; only the widget description rotates. The lifecycle
methods (`initState`, `didChangeDependencies`, `build`, `didUpdateWidget`,
`dispose`) all run on the `State` instance.

Critical interview point: `build()` may be called many times. Don't put
expensive work or side-effects there. `initState` runs once.

## Dart's Concurrency Model: Single-Threaded Event Loop + Isolates

Dart has no threads in the conventional sense. Every Dart program runs inside
an **isolate**: a memory-isolated heap with a single-threaded event loop.
Isolates cannot share mutable state — they communicate only by passing
messages through `SendPort`/`ReceivePort`.

```
┌──────────────────────────────────────────┐
│  Isolate 1 (main)                       │
│  ┌───────────────────────────────────┐  │
│  │ Event Loop  ───► microtask queue  │  │
│  │             ───► event queue      │  │
│  │             ───► timer callbacks │  │
│  └───────────────────────────────────┘  │
└──────────────────────────────────────────┘
       ▼ SendPort.send(msg) (copy)
┌──────────────────────────────────────────┐
│  Isolate 2 (background)                │
│  ┌───────────────────────────────────┐  │
│  │ Event Loop  ───► event queue      │  │
│  └───────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

There are two queues per isolate: the **event queue** (I/O, timers, mouse,
future results) and the **microtask queue** (a higher-priority queue drained
between events for `Future.then` continuations and `scheduleMicrotask`).
Microtasks always run to completion before the next event.

```dart
void main() async {
  print('1');
  Future(() => print('3'));          // event queue
  Future.microtask(() => print('2')); // microtask queue
  print('4');
  await Future.delayed(Duration.zero, () => print('5'));
  print('6');
}
// Output: 1, 4, 2, 3, 5, 6
```

This is why Dart's `async`/`await` is non-preemptive — `await` simply schedules
a continuation; the next iteration of the event loop picks it up. There is no
thread context switch.

For CPU-heavy work, the main isolate would block. The answer is to spawn
another isolate:

```dart
import 'dart:isolate';

Future<int> sumPrimesBelow(int n) async {
  final receive = ReceivePort();
  await Isolate.spawn(_worker, receive.sendPort);
  final sendPort = await receive.first as SendPort;
  final reply = ReceivePort();
  sendPort.send([n, reply.sendPort]);
  return await reply.first as int;
}

void _worker(SendPort toMain) {
  final port = ReceivePort();
  toMain.send(port.sendPort);
  port.listen((msg) {
    final n = msg[0] as int;
    final replyTo = msg[1] as SendPort;
    int sum = 0;
    for (int i = 2; i < n; i++) if (_isPrime(i)) sum += i;
    replyTo.send(sum);
  });
}

bool _isPrime(int n) {
  if (n < 2) return false;
  for (int i = 2; i * i <= n; i++) if (n % i == 0) return false;
  return true;
}
```

Messages crossing isolate boundaries are deep-copied (no shared mutable state).
Flutter's `compute()` helper wraps this pattern with one-off function calls.

## Compilation: AOT vs JIT, and Hot Reload

Dart is one of very few languages with both production JIT and AOT compilers
maintained by the same team. The reason is Flutter's dual use case:

- **During development**: Dart VM with JIT. Hot reload works by the VM
  applying incremental patches to running classes (replacing methods, adding
  fields). The widget tree rebuilds from the new code in ~1 second.
- **In release builds**: Dart AOT-compiled to native ARM64 / x64. There is no
  VM in the usual sense — Dart source is compiled to a tree-shaken, type-
  feedback-optimized native binary that boots in < 100 ms.

| Mode | Used by | Binary form | Hot reload |
|---|---|---|---|
| Kernel + JIT | `flutter run` | `.dill` (kernel bytecode) | Yes |
| AOT (app) | `flutter build apk --release` | Snapshots in `.so` | No |
| AOT + tree-shake | production | Ahead-of-time native code | No |

The `dart compile` family includes `dart compile js` (for web),
`dart compile kernel`, `dart compile exe` (self-contained native binary),
and `dart compile aot-snapshot`. Flutter's release builds use
`dart compile aot-snapshot` plus an embedded Dart VM runtime that loads
precompiled snapshots.

Tree-shaking: Dart's compiler tracks `@pragma('vm:entry-point')` annotations
and only retains symbols reachable from `main()` plus reflected symbols. This
keeps binary size small — small Flutter apps ship under 6 MB on Android.

## Flutter vs React Native

| Aspect | Flutter | React Native (legacy arch) | React Native (new arch) |
|---|---|---|---|
| Language | Dart | JS (Hermes) | JS (Hermes) |
| UI primitives | Own widgets drawn by Skia/Impeller | Native iOS/Android views | Native iOS/Android views |
| Cross-thread comms | none (single isolate for UI) | JSON over JS bridge (async) | JSI direct calls (synchronous) |
| Compilation (prod) | AOT → native code | JS bundle interpreted (Hermes has bytecode) | JS bundle (bytecode) |
| Frame model | Pipeline: build → layout → paint on UI thread, raster on GPU thread | Native view updates from JS thread → shadow tree → native UI | Similar but with synchronous layout |
| First render | Fast (Dart AOT, precompiled shaders with Impeller) | Slower (bridge setup, view inflation) | Faster than legacy but still slower than Flutter |
| Code reuse with web | Same code → CanvasKit (Wasm) | Separate React web project | Separate |
| Ecosystem | Pub.dev | npm | npm |
| Animation perf | Excellent — runs at 60/120 fps with ease | OK but can jank during long JS work | Better with JSI |

Flutter's biggest practical advantage is *predictable* frame times. Because
the rendering pipeline is fully owned by the engine and runs on a UI + raster
thread pair under direct control, with Impeller's precompiled shaders, you
rarely see shader-compile jank. RN's new architecture (Fabric + JSI + Hermes)
closes much of the perf gap but still relies on the platform's view system
which has its own inflation costs.

Flutter's biggest practical disadvantage: every UI element is re-drawn from
scratch — there's no reuse of platform widgets. Things like accessibility
labels map cleanly, but platform-specific behaviors (e.g. iOS specific
transitions, Material You system theming on Android 12+) require glue code.

## Interview Questions

**Q: Why are widgets immutable in Flutter?**
A: Immutability enables cheap diffing — every rebuild produces new
descriptions, and the framework's `canUpdate` (runtimeType + key match)
determines whether to reuse the existing `Element`. State lives in the
`Element`/`State` layer, not the Widget, so immutable widgets don't lose
state across rebuilds.

**Q: What happens when you call `setState`?**
A: The framework calls `State.setState` which internally marks the
`Element` dirty (`markNeedsBuild`). The next frame's `buildOwner.buildScope`
calls `Element.rebuild`, which calls `State.build` and diffs against the
previous widget subtree. RenderObjects are updated for deltas and a new
`Scene` is sent to the raster thread.

**Q: Difference between `StatelessWidget` and `StatefulWidget`?**
A: Both are immutable; the difference is whether the framework attaches a
`State` object to the corresponding Element. `StatelessWidget`'s data lives
only in its final fields; rebuilds require the parent to construct a new
instance. `StatefulWidget`'s `State` persists across rebuilds, supports
`initState`/`dispose` and is where mutable UI state belongs.

**Q: Why is Dart single-threaded and how do you do CPU work?**
A: Dart's main isolate has one event loop with a microtask and event queue.
Without preemption, there's no race risk for shared UI state. For CPU-heavy
work, spawn another isolate via `Isolate.spawn` or `compute()` — these have
their own heap and pass messages by copy through `SendPort`. The result is
parallelism without locks.

**Q: What is Impeller and why did Flutter replace Skia?**
A: Impeller is Flutter's new rendering backend (Flutter 3.10+). It
precompiles shaders offline via `impellerc`, uses a modern explicit GPU API
(Metal on iOS, Vulkan/OpenGLES on Android), and drops frames cleanly when
behind. Skia compiled shaders at runtime, which caused first-frame jank;
Impeller fixes that.

**Q: How does hot reload work?**
A: The Dart VM compiles your Dart to Kernel bytecode. On reload, the VM
loads the new kernel, walks existing instances of changed classes, and
swaps their method pointers. The Flutter framework then triggers a
`reassemble` that calls `build` on the root, producing a new widget tree.
Total time: ~1 s, with state preserved.

## References

- [Flutter architectural overview — docs.flutter.dev](https://docs.flutter.dev/resources/architectural-overview)
- [Inside Flutter — docs.flutter.dev (Bill Simmons)](https://docs.flutter.dev/resources/inside-flutter)
- [Dart language tour — dart.dev](https://dart.dev/language)
- [Dart asynchronous programming — dart.dev](https://dart.dev/codelabs/async-await)
- [Isolates — dart.dev](https://dart.dev/language/concurrency)
- [Flutter rendering pipeline — docs.flutter.dev](https://api.flutter.dev/flutter/rendering/RenderingPipeline-class.html)
- [Impeller architecture — github.com/flutter/engine](https://github.com/flutter/engine/blob/main/impeller/docs/architecture.md)
- [Skia graphics library — skia.org](https://skia.org/)
- [AOT vs JIT in Dart — dart.dev/tools/dart-compile](https://dart.dev/tools/dart-compile)
- [Flutter performance best practices — docs.flutter.dev](https://docs.flutter.dev/perf/best-practices)
- [Material 3 in Flutter — docs.flutter.dev](https://docs.flutter.dev/ui/material)
- [React Native vs Flutter comparison — docs.flutter.dev/architecture](https://docs.flutter.dev/resources/faq#how-is-flutter-different-from-react-native)
