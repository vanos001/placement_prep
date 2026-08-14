# Rendering Performance & Core Web Vitals

This guide goes beyond the basic rendering pipeline (covered in [Browser Architecture](browser-architecture.md)) to explore advanced rendering optimizations and the Core Web Vitals that Google uses to evaluate user experience.

## Compositing and Layers

Modern browsers split content into **compositor layers** that are painted independently and then combined by the GPU compositor. Elements are promoted to their own layer when they have properties that the compositor can animate without repainting:

```css
.promoted {
  will-change: transform;
  transform: translateZ(0); /* common trick to force layer promotion */
  opacity: 0.99; /* subtle opacity also creates a layer */
}
```

### The Cost of Layers

Each layer consumes GPU memory. Too many layers cause **layer explosion**, increasing memory usage and hurting performance — especially on mobile. Chrome DevTools → Layers panel shows all compositor layers.

**Rules of thumb:**
- Don't promote more than ~50-100 layers on a page
- Remove `will-change` after animation completes
- `contain: layout style paint` can achieve similar benefits without layer promotion

### Rendering Pipeline Revisited

| Change type | Triggers | Skips |
|------------|----------|-------|
| **JS** | All subsequent steps | None |
| **Style recalc** | Layout, Paint, Composite | JS |
| **Layout (reflow)** | Paint, Composite | JS, Style |
| **Paint** | Composite | JS, Style, Layout |
| **Composite only** | None | JS, Style, Layout, Paint |

Only `transform` and `opacity` changes can skip everything and run directly on the compositor thread.

## requestAnimationFrame (rAF)

`requestAnimationFrame` synchronizes JavaScript work with the browser's repaint cycle:

```javascript
// ❌ BAD — runs independently of frame timing
setInterval(() => {
  element.style.transform = `translateX(${x}px)`;
  x += 10;
}, 16);

// ✅ GOOD — synced with display refresh (usually 60fps)
function animate() {
  element.style.transform = `translateX(${x}px)`;
  x += 10;
  if (x < 500) requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
```

**Why rAF over setInterval?**
- Automatically pauses when tab is hidden (saves battery and CPU)
- Guarantees execution before the next repaint
- Provides a high-resolution timestamp for smooth calculations
- Batches multiple callbacks into a single frame

### rAF for Read-Before-Write

Use rAF to batch reads before writes, avoiding layout thrashing:

```javascript
requestAnimationFrame(() => {
  const box = element.getBoundingClientRect(); // READ in rAF
  requestAnimationFrame(() => {
    element.style.width = box.width + 100 + 'px'; // WRITE in next frame
  });
});
```

## Virtual Scrolling

Rendering 10,000+ DOM nodes causes massive layout and paint costs. Virtual scrolling renders only the items visible in the viewport:

```
Viewport (scrollable)
┌──────────────────────┐
│  ← rendered buffer → │
│  Item 47             │
│  Item 48             │
│  Item 49             │
│  Item 50             │
└──────────────────────┘
   Items 0-46 and 51+ are NOT in the DOM
```

**Libraries:** `react-window`, `react-virtualized`, `@tanstack/virtual`

```jsx
import { FixedSizeList } from 'react-window';

<FixedSizeList height={400} itemCount={10000} itemSize={35}>
  {({ index, style }) => <div style={style}>Row {index}</div>}
</FixedSizeList>
```

**Key technique:** Calculate which items are visible using `scrollTop / itemHeight`, render a buffer above and below, and absolutely position each item using `transform: translateY()`.

## Image Optimization

Images often account for 50%+ of page weight. Optimization strategies:

### Lazy Loading

```html
<!-- Native lazy loading (Chrome, Firefox) -->
<img src="hero.jpg" loading="lazy" alt="Hero image">

<!-- Intersection Observer for full control -->
<img data-src="image.jpg" alt="..." class="lazy">
<script>
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.src = entry.target.dataset.src;
      observer.unobserve(entry.target);
    }
  });
});
document.querySelectorAll('.lazy').forEach(img => observer.observe(img));
</script>
```

### Responsive Images

```html
<!-- Serve different sizes based on viewport -->
<img
  srcset="small.jpg 400w, medium.jpg 800w, large.jpg 1200w"
  sizes="(max-width: 600px) 400px, (max-width: 1000px) 800px, 1200px"
  src="medium.jpg"
  alt="Responsive image"
>

<!-- Art direction: serve different crops -->
<picture>
  <source media="(max-width: 600px)" srcset="crop-square.jpg">
  <source media="(min-width: 601px)" srcset="crop-wide.jpg">
  <img src="crop-wide.jpg" alt="...">
</picture>
```

### Modern Formats

| Format | Compression | Transparency | Animation | Browser Support |
|--------|-----------|-------------|-----------|----------------|
| JPEG | Lossy | No | No | Universal |
| PNG | Lossless | Yes | No | Universal |
| WebP | Both | Yes | Yes | 97%+ |
| AVIF | Both | Yes | Yes | 92%+ |

```html
<picture>
  <source type="image/avif" srcset="photo.avif">
  <source type="image/webp" srcset="photo.webp">
  <img src="photo.jpg" alt="...">
</picture>
```

## Core Web Vitals

Google's Core Web Vitals measure real-world user experience. They affect SEO rankings.

### Largest Contentful Paint (LCP)

Measures perceived load speed — when the largest content element becomes visible.

**Target:** < 2.5 seconds | **Poor:** > 4 seconds

**Common LCP elements:** `<img>`, `<video>`, `<h1>`-`<h6>` text, background images

**How to improve LCP:**
- Preload LCP image: `<link rel="preload" as="image" href="hero.webp">`
- Use responsive images with `srcset`
- Serve images in modern formats (WebP/AVIF)
- Inline critical CSS to unblock first paint
- Use a CDN to reduce server response time (TTFB)

### Interaction to Next Paint (INP)

Replaced FID in March 2024. Measures responsiveness — the latency of all user interactions (clicks, taps, keypresses) throughout the page lifecycle, reporting the worst interaction.

**Target:** < 200ms | **Poor:** > 500ms

**How to improve INP:**
- Break long tasks (>50ms) using `scheduler.yield()` or `setTimeout`
- Reduce main thread work during interactions
- Use `isInputPending()` to defer non-urgent work
- Minimize JavaScript execution time

### Cumulative Layout Shift (CLS)

Measures visual stability — the sum of all unexpected layout shifts that occur during the page's lifespan.

**Target:** < 0.1 | **Poor:** > 0.25

**How to improve CLS:**
- Always set `width` and `height` on images and videos (or use `aspect-ratio`)
- Reserve space for ads and dynamic content
- Avoid inserting content above existing content (e.g., banner notifications)
- Use `contain-intrinsic-size` for lazily loaded content

```
Shift score = impact fraction × distance fraction
```

**Common CLS culprits:** Images without dimensions, late-loading ads, web fonts causing FOIT, dynamically injected content.

## Interview Questions

**Q: What is the difference between layout, paint, and composite?**
A: Layout calculates geometry (positions and sizes). Paint generates draw calls (fill rect, draw text). Composite combines painted layers on the GPU. Only `transform` and `opacity` can skip straight to composite — everything else triggers at least paint.

**Q: Why should you use `requestAnimationFrame` instead of `setTimeout` for animations?**
A: rAF is synced with the browser's refresh cycle (typically 60fps), automatically pauses when the tab is hidden (saving resources), and provides a high-resolution timestamp. `setTimeout` can run at arbitrary intervals and doesn't pause when hidden.

**Q: What is virtual scrolling and why is it needed?**
A: Virtual scrolling renders only the DOM nodes visible in the viewport (plus a small buffer) instead of all items. This prevents performance degradation when rendering large lists (10K+ items), avoiding expensive layout calculations and memory usage from thousands of DOM nodes.

**Q: How would you diagnose and fix a poor LCP score?**
A: Use Chrome DevTools → Performance → identify the LCP element. Common fixes: preload the LCP image, serve it in modern formats (WebP/AVIF), use responsive `srcset`, ensure the server responds quickly (TTFB < 800ms), and inline critical CSS to unblock rendering.

**Q: What causes CLS and how do you fix it?**
A: CLS is caused by elements that shift after initial render. Fix by: setting explicit width/height or aspect-ratio on images/videos, reserving space for dynamic content (ads, banners), avoiding inserting content above the viewport after load, and using CSS `contain` to isolate layout areas.

## References

- [web.dev — Core Web Vitals](https://web.dev/vitals/)
- [web.dev — Rendering Performance](https://web.dev/rendering-performance/)
- [MDN — requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
