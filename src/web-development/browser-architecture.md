# Browser Architecture

Understanding how browsers work is fundamental to writing performant web applications. This guide covers the major components and processes involved in turning HTML, CSS, and JavaScript into pixels on screen.

## High-Level Architecture

A modern browser consists of several key components:

- **User Interface** — address bar, back/forward buttons, bookmarks bar, everything visible except the page viewport
- **Browser Engine** — bridges the UI and the rendering engine, coordinates actions
- **Rendering Engine** — parses HTML and CSS and renders content to the screen (Blink for Chrome, Gecko for Firefox, WebKit for Safari)
- **JavaScript Engine** — executes JavaScript code (V8 for Chrome, SpiderMonkey for Firefox, JavaScriptCore for Safari)
- **Networking Layer** — handles HTTP requests, DNS resolution, and TLS handshakes
- **Data Storage** — manages cookies, localStorage, IndexedDB, and other persistent storage

### Process Architecture

Modern browsers use a multi-process architecture:

- **Browser Process** — manages the UI, disk, and network access
- **Renderer Process** — one per tab (or site instance with site isolation), handles parsing, layout, and painting
- **GPU Process** — handles GPU-accelerated rendering tasks
- **Plugin Process** — isolates plugins like Flash (legacy) or PDF viewers
- **Utility Processes** — audio, network service, data decoding

This isolation provides security (a crashed tab doesn't crash the browser) and stability.

## The Rendering Engine

The rendering engine is responsible for displaying the requested content. Its workflow follows a well-defined pipeline.

### Parsing HTML to DOM

When the renderer process receives HTML bytes from the network:

1. **Tokenization** — the HTML tokenizer breaks the raw bytes into tokens (start tags, end tags, attributes, text content)
2. **Tree Construction** — tokens are consumed and converted into DOM nodes arranged in a tree structure
3. **Error Recovery** — the HTML parser handles malformed markup gracefully (unclosed tags, misplaced elements) per the HTML specification's parsing rules

The result is the **Document Object Model (DOM)** — a tree-structured representation of the page.

### Parsing CSS to CSSOM

In parallel, CSS is parsed into the **CSS Object Model (CSSOM)**:

1. CSS bytes are converted into tokens
2. Tokens become CSSOM nodes
3. The browser resolves cascading — specificity, inheritance, and the `!important` flag determine final computed styles

The CSSOM is also tree-structured, mirroring the DOM tree but containing style information.

### The Render Tree

The DOM and CSSOM are combined into the **render tree**:

- Only visible elements are included (elements with `display: none` are excluded; `visibility: hidden` elements are included but invisible)
- Each node in the render tree contains the computed styles for its corresponding DOM node
- The render tree represents exactly what will be painted on screen

### Layout (Reflow)

Once the render tree is built, the browser calculates the **geometry and position** of every node:

- Each node's exact coordinates and dimensions are computed
- This is based on the box model — content, padding, border, margin
- Layout calculations traverse the render tree from root to leaves
- Text is broken into lines, and line boxes are created

Layout is also called **reflow** in some engines.

### Painting

After layout, the browser **paints** pixels to the screen:

1. **Paint Records** — the render tree is traversed and drawing instructions (fill rect, draw text, draw image) are generated
2. **Rasterization** — paint records are converted to actual pixels, often in tiles for GPU compositing
3. **Compositing** — layers are combined in the correct order to produce the final image

## The JavaScript Engine

### V8 Architecture (Chrome)

V8 is the most widely used JavaScript engine. Its compilation pipeline has two tiers:

1. **Parser** — JavaScript source is parsed into an Abstract Syntax Tree (AST)
2. **Ignition (Interpreter)** — the AST is compiled into bytecode, which Ignition executes. This is fast to start up
3. **Sparkplug** — a non-optimizing compiler that produces machine code from bytecode without type feedback
4. **TurboFan (Optimizing Compiler)** — hot functions (called frequently) are compiled into highly optimized machine code using type feedback collected during Ignition execution

When TurboFan's assumptions about types become invalid (e.g., a variable that was always a number suddenly becomes a string), the optimized code is **deoptimized** and execution falls back to Ignition.

### Garbage Collection

V8 uses a generational garbage collector:

- **Young Generation** — newly allocated objects. Collected frequently with a **Scavenger** (semi-space collector)
- **Old Generation** — objects that survived multiple young generation collections. Collected with **Mark-Sweep-Compact** or **Incremental Marking**
- **Orinoco** — V8's concurrent and parallel garbage collector, which minimizes pause times

### Memory Management Pitfalls

Common memory leaks in JavaScript:

- **Global variables** — accidentally creating properties on `window`
- **Event listeners** — not removing listeners when elements are destroyed
- **Closures** — closures retaining references to large objects
- **Detached DOM nodes** — removing elements from the DOM but keeping references in JavaScript
- **Timers** — `setInterval` or `setTimeout` callbacks holding references

## The Critical Rendering Path

The **Critical Rendering Path (CRP)** is the sequence of steps the browser goes through from receiving HTML to rendering pixels. Optimizing the CRP is key to fast page loads.

### Steps

1. **Construct DOM** from HTML
2. **Construct CSSOM** from CSS
3. **Combine into Render Tree**
4. **Layout** — compute geometry
5. **Paint** — fill in pixels

### CSS is Render-Blocking

CSS blocks rendering. The browser will not paint until the CSSOM is fully constructed. This is why a `<link rel="stylesheet">` in the `<head>` delays the first paint.

**Optimization:**
- Inline critical CSS
- Use `media` attributes on stylesheets (`media="print"` doesn't block rendering)
- Minimize CSS file size

### JavaScript is Parser-Blocking

JavaScript blocks HTML parsing by default. When the parser encounters a `<script>` tag, it pauses parsing, downloads (if external), and executes the script before continuing.

**Optimization:**
- `async` attribute — downloads in parallel, executes as soon as downloaded (blocks parsing during execution)
- `defer` attribute — downloads in parallel, executes after HTML parsing is complete, in document order
- `type="module"` — deferred by default

### Preload and Prefetch

- `<link rel="preload">` — tells the browser a resource is needed soon, fetches it with high priority
- `<link rel="prefetch">` — tells the browser a resource may be needed for future navigation, fetches with low priority
- `<link rel="preconnect">` — establishes early connection (DNS, TLS, TCP) to a required origin

## Reflow vs Repaint

These are two distinct operations that affect rendering performance:

### Reflow (Layout)

Reflow is the process of recalculating the positions and dimensions of elements. It is triggered when:

- DOM elements are added or removed
- Element dimensions change (width, height, padding, margin, border)
- Content changes (text changes, images with different sizes)
- Browser window is resized
- CSS classes are added or removed
- `offsetWidth`, `offsetHeight`, `getComputedStyle()` are read (forces synchronous layout)

Reflow is **expensive** because it can affect the entire document. A single element's reflow can trigger reflows of its parents and children.

### Repaint

Repaint happens when visual styles change that don't affect layout:

- `color`, `background-color`, `visibility`, `box-shadow`, `border-radius`
- Outline changes
- Text decoration changes

Repaint is cheaper than reflow because layout doesn't need to be recalculated, but it still involves repainting the affected region.

### Optimizing Rendering Performance

**Minimize reflows:**
- Batch DOM changes — use `DocumentFragment` or build strings before inserting
- Avoid reading layout properties in loops (triggers forced synchronous layout, also called layout thrashing)
- Use `transform` and `opacity` for animations — these are handled by the compositor and don't trigger layout or paint
- Take elements out of flow with `position: absolute` or `position: fixed` — their reflows don't affect other elements
- Use `will-change` to hint to the browser that an element will animate

**Minimize repaints:**
- Change classes at the highest level possible
- Avoid frequent changes to properties that trigger repaint
- Use CSS containment (`contain: layout style paint`) to limit the scope of rendering changes

### The Rendering Pipeline

Each frame in the browser follows this pipeline:

1. **JavaScript** — handle events, modify DOM/styles
2. **Style** — recalculate computed styles for affected elements
3. **Layout** — calculate geometry
4. **Paint** — generate paint records
5. **Composite** — combine layers and display

The target is **60 frames per second** — each frame has a budget of ~16.6ms. Exceeding this budget causes jank (dropped frames).

## Layout Thrashing

Layout thrashing occurs when JavaScript repeatedly forces the browser to recalculate layout:

```javascript
// BAD — triggers layout on each iteration
for (let i = 0; i < elements.length; i++) {
  elements[i].style.width = container.offsetWidth + 'px'; // read forces layout
}

// GOOD — read once, then write
const width = container.offsetWidth;
for (let i = 0; i < elements.length; i++) {
  elements[i].style.width = width + 'px';
}
```

Libraries like **FastDOM** batch read and write operations to prevent layout thrashing.

## Key Interview Points

- The CRP is the single most important concept for page load performance
- CSS blocks rendering; JavaScript blocks parsing
- `defer` and `async` change script loading behavior — `defer` maintains order, `async` doesn't
- Reflow is more expensive than repaint
- `transform` and `opacity` animations bypass layout and paint, running on the compositor thread
- The browser targets 60fps — 16.6ms per frame budget
- Multi-process architecture provides isolation and stability
- Understanding the rendering pipeline helps identify performance bottlenecks
