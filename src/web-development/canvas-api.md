# Canvas 2D API

The Canvas 2D API is the browser's immediate-mode 2D drawing interface. A `<canvas>` element exposes a `CanvasRenderingContext2D` — a stateful API for paths, fills, strokes, transforms, and pixel manipulation. It is the workhorse for charts, image editing, games, procedural art, and anywhere the DOM's retained-mode boxes won't do. Introduced in Safari 1.1 (2004) and standardized in HTML5; today it's universally supported and forms the basis for `OffscreenCanvas`, `ImageBitmap`, and even the video frame source for `VideoTrackGenerator`.

## The Canvas Element and the Context

```html
<canvas id="c" width="640" height="480"></canvas>
```

```js
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

// Optionally request 'willReadFrequently' if you'll use getImageData often —
// it tells the browser to use a software-backed context (faster pixel reads).
const ctx2 = canvas.getContext('2d', { willReadFrequently: true });
```

The `width` and `height` **attributes** define the canvas's internal resolution (its backing bitmap). They are NOT the same as the CSS `width`/`height` of the element. Setting CSS to make a 1000×1000 canvas display at 500×500 css pixels gives a 2x supersampling for crispness. Setting the attribute to 500×500 and CSS to 1000×1000 gives a blurry result.

```js
function setupHiDPI(canvas, cssWidth, cssHeight) {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = cssWidth * dpr;
  canvas.height = cssHeight * dpr;
  canvas.style.width = cssWidth + 'px';
  canvas.style.height = cssHeight + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);  // all subsequent draws in CSS pixels
  return ctx;
}
```

Forgetting the DPR scale is why so many canvas apps look fuzzy on Retina displays.

## Drawing Primitives

### Rectangles

The two built-in rect ops are `fillRect` and `strokeRect`. Everything else is paths.

```js
ctx.fillStyle = '#4287f5';
ctx.fillRect(10, 10, 100, 80);

ctx.lineWidth = 2;
ctx.strokeStyle = '#333';
ctx.strokeRect(10, 10, 100, 80);
```

### Paths

A path is built by `beginPath()`, then `moveTo`/`lineTo`/`arc`/`bezierCurveTo`, then `fill()` or `stroke()`.

```js
ctx.beginPath();
ctx.moveTo(50, 50);
ctx.lineTo(150, 50);
ctx.lineTo(100, 150);
ctx.closePath();   // line back to (50, 50) — implicit fill boundary
ctx.fillStyle = 'red';
ctx.fill();
```

### Arcs and Circles

```js
ctx.beginPath();
// arc(centerX, centerY, radius, startAngle, endAngle, counterclockwise)
// Angles are in RADIANS — a common bug source.
ctx.arc(100, 100, 40, 0, Math.PI * 2);
ctx.fill();

// Half circle.
ctx.beginPath();
ctx.arc(100, 100, 40, 0, Math.PI);
ctx.fill();

// Use arcTo for rounded rectangles (combined with lineTo).
```

A common idiom: a rounded rect helper since pre-2022 browsers don't have `ctx.roundRect()`:

```js
function roundedRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y,     x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x,     y + h, r);
  ctx.arcTo(x,     y + h, x,     y,     r);
  ctx.arcTo(x,     y,     x + w, y,     r);
  ctx.closePath();
}
```

Modern browsers (Chrome 99+, Firefox 110+, Safari 16+) ship `roundRect` natively:

```js
ctx.beginPath();
ctx.roundRect(10, 10, 100, 80, [10, 5, 10, 5]);  // top, right, bottom, left radii
ctx.fill();
```

### Bezier Curves

Two flavors: cubic (`bezierCurveTo`) and quadratic (`quadraticCurveTo`).

```js
// Cubic: control points c1 and c2, end point at (x, y).
ctx.beginPath();
ctx.moveTo(0, 200);
ctx.bezierCurveTo(150, 0, 350, 400, 500, 200);
ctx.stroke();

// Quadratic: one control point.
ctx.beginPath();
ctx.moveTo(0, 200);
ctx.quadraticCurveTo(250, 0, 500, 200);
ctx.stroke();
```

The math behind `bezierCurveTo(cp1x, cp1y, cp2x, cp2y, x, y)` is the cubic Bezier B(t) = (1-t)³P0 + 3(1-t)²t·P1 + 3(1-t)t²·P2 + t³·P3. The current point is P0; the new point is P3; cp1 and cp2 are P1 and P2.

## State Management: save() and restore()

The 2D context is **stateful**. The state includes: fill/stroke style, line width, line cap/join, shadow settings, transform, clip path, global alpha, global compositing operation, font, text alignment, image smoothing.

`save()` pushes the current state onto a stack; `restore()` pops it.

```js
function drawBadge(ctx, x, y) {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = 'gold';
  ctx.fillRect(0, 0, 60, 30);
  ctx.fillStyle = 'black';
  ctx.font = '14px sans-serif';
  ctx.fillText('★', 24, 20);
  ctx.restore();  // restores translate(0,0), fillStyle, font, etc.
}
```

Nesting is unlimited, but each `save()` allocates a state object — don't accumulate leaks by saving without restoring.

## Transformations

The context maintains a 3×3 affine transformation matrix (only 6 numbers — the bottom row is always `[0, 0, 1]`). Operations:

```js
ctx.translate(50, 50);   // moves origin
ctx.rotate(Math.PI / 4); // rotates by 45 degrees (CCW)
ctx.scale(2, 2);          // doubles subsequent sizes
```

These are applied to subsequent draw calls. They're also cumulative — calling `translate(10, 10); translate(20, 20)` ends at `(30, 30)`.

For setting the matrix directly, use `setTransform(a, b, c, d, e, f)`:

```
| a c e |   | scaleX skewX  translateX |
| b d f | = | skewY  scaleY translateY |
| 0 0 1 |   | 0      0      1          |
```

```js
ctx.setTransform(2, 0, 0, 2, 100, 100);  // 2x scale, origin at (100, 100)
```

`resetTransform()` (or `setTransform(1, 0, 0, 1, 0, 0)`) returns to the identity matrix. After a `save()`/`restore()`, the transform is restored too — that's why save/restore is the safer pattern.

## Image Drawing

`drawImage` accepts an `HTMLImageElement`, `HTMLCanvasElement`, `HTMLVideoElement`, `ImageBitmap`, `OffscreenCanvas`, or `Image`:

```js
// Simple: draw at top-left.
ctx.drawImage(img, 0, 0);

// Scaled to width/height.
ctx.drawImage(img, 0, 0, 320, 240);

// Sub-rectangle of the source, drawn to a destination rect.
ctx.drawImage(img, 100, 100, 50, 50,  10, 10, 200, 200);
//             src x, y, w, h       dst x, y, w, h
```

The 9-argument form is the workhorse for sprite sheets — one image, many sprites, each addressed by source rect.

For best performance, decode once into an `ImageBitmap`:

```js
const bitmap = await createImageBitmap(img);
ctx.drawImage(bitmap, 0, 0);
```

`ImageBitmap` is GPU-friendly and unlocks off-thread decoding. Drawing an `HTMLImageElement` triggers decode-on-draw on first use, which can cause frame drops.

## Pixel Manipulation

`getImageData(sx, sy, sw, sh)` returns an `ImageData` object: a `Uint8ClampedArray` of RGBA bytes (4 per pixel).

```js
const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
const data = imageData.data;  // Uint8ClampedArray, length = w * h * 4

// Invert colors.
for (let i = 0; i < data.length; i += 4) {
  data[i + 0] = 255 - data[i + 0];  // R
  data[i + 1] = 255 - data[i + 1];  // G
  data[i + 2] = 255 - data[i + 2];  // B
  // data[i + 3] = alpha — leave alone
}

ctx.putImageData(imageData, 0, 0);
```

`Uint8ClampedArray` clamps writes to [0, 255] automatically, which is convenient — `data[i] = -10` becomes `0`, not a wrap.

### Direct `ImageData` creation

```js
const img = new ImageData(canvas.width, canvas.height);
// Fill with red.
for (let i = 0; i < img.data.length; i += 4) {
  img.data[i] = 255;
}
ctx.putImageData(img, 0, 0);
```

## OffscreenCanvas

`OffscreenCanvas` decouples canvas from DOM. You can render on a Web Worker, then transfer the result to a visible `<canvas>` via `transferControlToOffscreen()`.

```js
// Main thread.
const canvas = document.querySelector('canvas');
const offscreen = canvas.transferControlToOffscreen();

const worker = new Worker('render-worker.js', { type: 'module' });
worker.postMessage({ canvas: offscreen }, [offscreen]);
```

```js
// render-worker.js
self.onmessage = ({ data: { canvas } }) => {
  const ctx = canvas.getContext('2d');
  let t = 0;
  function frame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = `hsl(${t % 360}, 100%, 50%)`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    t++;
    requestAnimationFrame(frame);
  }
  frame();
};
```

The key win: rendering happens on a worker thread, so the main thread can stay responsive. The visible `<canvas>` is updated automatically — the worker doesn't have to send anything back.

Caveat: the context requested must be `2d` or `webgl`/`webgpu`. You can't do `document`-related things on a worker; for example, drawing an `HTMLImageElement` requires `createImageBitmap` first.

## Performance: Avoiding getImageData in Hot Loops

`getImageData` is slow because:

1. The canvas's backing store is often GPU-side (especially on macOS/iOS). Reading pixels back to the CPU requires a GPU→CPU transfer — possibly a pipeline stall.
2. The browser reads the entire `sw × sh` rectangle into a fresh typed array.
3. `putImageData` does the reverse — CPU→GPU upload.

Doing this in a 60 fps loop on a 4K canvas will cap you at 5-10 fps.

The fix: avoid the round trip.

| Bad pattern | Better pattern |
|-------------|----------------|
| `getImageData` per frame to detect collisions | Use vector math in JS — store your geometry coordinates directly |
| Per-frame color cycling via `getImageData` | Use a pre-rendered sprite, swap the sprite |
| CPU image filters | WebGL/WebGPU fragment shaders — orders of magnitude faster |
| Need pixel-perfect collision detection | Maintain a JS-side model of object positions; only `getImageData` for rare one-shot reads |

When you genuinely need `getImageData` (e.g., an interactive image editor), batch reads: read once per user gesture, not per frame. Use `willReadFrequently: true` when creating the context — this tells the browser to use a CPU-backed context, sidestepping the GPU readback cost. On Chrome this is a measurable speedup; on Safari it's largely a no-op but doesn't hurt.

## Typed Arrays and Performance

Always operate on the underlying `Uint8ClampedArray` directly, not on `ImageData` properties:

```js
const data = imageData.data;  // Uint8ClampedArray
// GOOD: contiguous, type-specialized, no method dispatch per access.
for (let i = 0; i < data.length; i += 4) {
  // ... operate on data[i], data[i+1], data[i+2], data[i+3]
}

// BAD: object property access — 5-10x slower.
const img = ctx.getImageData(0, 0, w, h);
for (let i = 0; i < img.data.length; i += 4) {
  img.data[i] = /* ... */;
}
```

For very large images, consider WebGL or WebGPU fragment shaders — a 4K image filter on CPU might be 200 ms; on GPU, <5 ms.

## Compositing

```js
ctx.globalCompositeOperation = 'source-over';  // default
ctx.globalCompositeOperation = 'multiply';      // for color blending
ctx.globalCompositeOperation = 'lighter';        // additive — used for particle effects
ctx.globalCompositeOperation = 'destination-out'; // erase — like a brush in a paint app
```

For 12+ modes, see https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/globalCompositeOperation. The expensive modes (`multiply`, `screen`) trigger a software fallback — measure before using in hot loops.

## Common Pitfalls

1. **Forgetting `beginPath()` before each shape.** Otherwise every previous sub-path becomes part of the new fill — the screen fills with unintended overlapping shapes.
2. **Mixing radians and degrees.** Canvas uses radians everywhere. `Math.PI / 180` to convert.
3. **Setting canvas `width`/`height` clears the canvas.** Resizing — even to the same value — resets the bitmap, context state, and current path.
4. **Forgetting DPR scaling on Retina.** The result is a blurry canvas. Always multiply by `devicePixelRatio`.
5. **Loading images synchronously.** `drawImage` after `img.src = 'foo.png'` immediately will fail — the image isn't decoded yet. Use `await img.decode()` first, or `createImageBitmap`.
6. **Holding references to ImageData across draws.** The `Uint8ClampedArray` you got is a snapshot; if you `putImageData` after drawing, you overwrite those draws.

## Interview Questions

**Q1: Why does `ctx.save()` exist if all state is mutable directly?**
A: Because transforms and styles compose: setting `fillStyle = 'red'` changes the current state, but later you want to go back to blue. Manually tracking and restoring each property is error-prone. `save()`/`restore()` is a stack of state snapshots — it's especially valuable when functions compose (a function that draws a badge shouldn't leak its font/transform changes to the caller).

**Q2: Why is `getImageData` slow, and what are the alternatives?**
A: `getImageData` reads pixels from the canvas backing store (often GPU-resident) into a fresh typed array on the CPU. For a 4K canvas this can be 30 ms per call due to GPU→CPU transfer and possible pipeline stalls. Alternatives: maintain a JS-side model of object positions and do collision math directly; use WebGL/WebGPU fragment shaders for image processing; use `willReadFrequently: true` when you must read pixels — it forces a CPU-backed context.

**Q3: How do you render a Canvas at HiDPI on a Retina display?**
A: Multiply the canvas's `width`/`height` attributes by `devicePixelRatio`, set CSS `width`/`height` to the logical CSS pixel size, then `ctx.scale(dpr, dpr)` so subsequent draws can be expressed in CSS pixels. Otherwise the browser scales a 1×1 backing store up to 2× CSS pixels — fuzzy output.

**Q4: What does `OffscreenCanvas` give you that a regular canvas doesn't?**
A: Two things. First, rendering on a Web Worker — the main thread stays responsive. Second, `transferControlToOffscreen()` lets a worker draw directly to a visible `<canvas>` without message-passing round trips. The worker's render loop runs entirely off-thread, which is critical for 60 fps rendering with heavy UI on the main thread.

**Q5: What's the difference between `drawImage(img, ...)` and `drawImage(bitmap, ...)` where `bitmap` is an `ImageBitmap`?**
A: `ImageBitmap` is the decoded, GPU-ready form. Drawing an `HTMLImageElement` may trigger decode-on-draw on first use — a one-time cost. `ImageBitmap` can be created off-thread via `createImageBitmap` (in a worker), and is optimized for repeated draws and compositing. For sprite sheets drawn many times per frame, decode once into `ImageBitmap` upfront.

## References

- [HTML Living Standard — The canvas element](https://html.spec.whatwg.org/multipage/canvas.html)
- [MDN: Canvas API](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
- [MDN: CanvasRenderingContext2D](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D)
- [MDN: Optimizing Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)
- [MDN: OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas)
- [MDN: ImageBitmap](https://developer.mozilla.org/en-US/docs/Web/API/ImageBitmap)
- [Chrome DevTools: Canvas inspection](https://developer.chrome.com/docs/devtools/canvas/)
- [W3C Canvas 2D Context (Level 2) Note](https://www.w3.org/TR/2dcontext/)
