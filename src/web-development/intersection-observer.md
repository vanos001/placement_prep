# Intersection Observer

The Intersection Observer API is a browser API for asynchronously observing changes in the intersection of an element with the viewport (or a parent element). Introduced in 2017 (Chrome 51), it replaced the older scroll-event-based pattern for visibility detection, with much better performance. This page covers the API, the use cases, the root margin concept, and the production patterns.

## The Problem

Before Intersection Observer, detecting element visibility required:
1. Listening to scroll events.
2. Calling `getBoundingClientRect()` (forces layout, sync).
3. Computing the intersection manually.

This pattern is slow:
- Scroll events fire many times per second; the computation per event is expensive.
- `getBoundingClientRect()` triggers a synchronous layout recalculation.

For 1000+ elements, this can drop the page to <10 fps.

## The API

```js
const observer = new IntersectionObserver((entries, observer) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      console.log('Element entered the viewport:', entry.target);
      // Optionally stop observing
      observer.unobserve(entry.target);
    }
  }
}, {
  root: null,        // null = viewport; otherwise, a parent element
  rootMargin: '0px', // expand/shrink the root's bounding box
  threshold: 0.5,    // 0.5 = 50% of the element must be visible
});

const target = document.querySelector('#my-element');
observer.observe(target);
```

The observer fires the callback when an observed element's intersection with the root changes:
- `entry.isIntersecting`: true if currently intersecting.
- `entry.intersectionRatio`: the fraction (0-1) currently visible.
- `entry.target`: the observed element.
- `entry.boundingClientRect`: the element's bounding rect.
- `entry.intersectionRect`: the intersection's rect.

## The Threshold

The `threshold` option controls when the callback fires:
- `threshold: 0`: fires as soon as any part is visible.
- `threshold: 0.5`: fires when 50% is visible.
- `threshold: 1.0`: fires when 100% is visible.
- `threshold: [0, 0.25, 0.5, 0.75, 1.0]`: fires at each of these thresholds.

```js
const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    console.log(`${entry.target.id}: ${entry.intersectionRatio * 100}% visible`);
  }
}, { threshold: [0, 0.25, 0.5, 0.75, 1.0] });
```

## The Root Margin

The `rootMargin` option expands or shrinks the root's bounding box:

```js
const observer = new IntersectionObserver((entries) => {
  // Fires when the element is within 100px of the viewport edge
  for (const entry of entries) {
    if (entry.isIntersecting) {
      console.log('About to enter the viewport');
    }
  }
}, { rootMargin: '100px' });
```

A positive root margin means the observer fires when the element is 100px outside the viewport (before it would normally be visible). Useful for pre-loading images before they're scrolled into view.

## The Root Element

The default root is the viewport. You can use a scrollable parent element:

```html
<div id="scroll-container" style="height: 400px; overflow: auto;">
  <div class="item">Item 1</div>
  <div class="item">Item 2</div>
  <!-- ... -->
</div>
```

```js
const container = document.querySelector('#scroll-container');
const observer = new IntersectionObserver((entries) => {
  // ...
}, { root: container });
```

The observer fires when items enter the container's viewport (not the page's viewport).

## Production Use Cases

### Lazy-Loading Images

```html
<img class="lazy" data-src="image1.jpg" alt="...">
<img class="lazy" data-src="image2.jpg" alt="...">
<!-- ... -->
```

```js
const observer = new IntersectionObserver((entries, observer) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;  // set the actual src
      img.classList.remove('lazy');
      observer.unobserve(img);  // stop observing
    }
  }
}, { rootMargin: '200px' });

document.querySelectorAll('img.lazy').forEach((img) => observer.observe(img));
```

Images are loaded only when they're about to enter the viewport (200px before). Saves bandwidth and improves initial load.

### Infinite Scroll

```js
const sentinel = document.querySelector('#sentinel');  // at the bottom of the list
const observer = new IntersectionObserver((entries) => {
  if (entries[0].isIntersecting) {
    loadMoreItems();  // fetch the next page
  }
});
observer.observe(sentinel);
```

When the user scrolls to the bottom, the sentinel enters the viewport; the observer fires; more items are loaded.

### Animated Reveal on Scroll

```js
const observer = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) {
      entry.target.classList.add('revealed');
    } else {
      entry.target.classList.remove('revealed');
    }
  }
}, { threshold: 0.1 });

document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
```

CSS:
```css
.reveal { opacity: 0; transition: opacity 0.5s; }
.reveal.revealed { opacity: 1; }
```

Elements fade in when they enter the viewport.

### Sticky Header Detection

```js
const header = document.querySelector('header');
const sentinel = document.createElement('div');
sentinel.style.height = '1px';
header.parentNode.insertBefore(sentinel, header);

const observer = new IntersectionObserver((entries) => {
  if (!entries[0].isIntersecting) {
    header.classList.add('sticky');
  } else {
    header.classList.remove('sticky');
  }
});
observer.observe(sentinel);
```

When the sentinel (placed above the header) leaves the viewport, the header becomes sticky.

## Production Performance

Intersection Observer's performance characteristics:
- Latency: ~1-5 ms per callback (in the browser's frame).
- Number of observed elements: limited by the browser (typically 1000s before noticeable overhead).
- CPU usage: very low; the browser batches callbacks to the frame rate.

For 10K+ observed elements, the API may struggle. Split into multiple observers or use virtualization.

## Comparison to Older Patterns

| Aspect | Intersection Observer | Scroll Event + getBoundingClientRect |
|--------|------------------------|--------------------------------------|
| Performance | O(1) per element; batched | O(N) per scroll event |
| Layout thrashing | None | getBoundingClientRect forces sync layout |
| API | Async callback | Sync event handler |
| Best for | Lazy load, infinite scroll, animations | Simple cases, older browsers |

For modern browsers, Intersection Observer is the standard. For very old browsers (IE11 and earlier), use a polyfill (WICG's `intersection-observer` polyfill).

## Common Pitfalls

1. **Forgetting that the observer fires on initial observation.** When you observe an element that's already visible, the callback fires immediately. Plan for this.

2. **Forgetting to unobserve elements.** An observer with 10K observed elements consumes memory. Unobserve elements that are no longer needed (e.g., after their image is loaded).

3. **Forgetting that the root element must be a scroll container.** If you pass a non-scrollable root, the observer may not fire as expected.

4. **Forgetting that thresholds can be arrays.** A single threshold fires once; an array fires at multiple visibility percentages.

5. **Forgetting that the callback fires in the browser's frame.** The callback runs during the browser's frame (~16 ms at 60 fps); don't do heavy computation in it.

6. **Forgetting that the observer fires on visibility changes, not on entry only.** It also fires when elements leave the viewport (with `isIntersecting: false`). Handle both cases.

## References

- [MDN: Intersection Observer API](https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API)
- [WICG: Intersection Observer polyfill](https://github.com/WICG/IntersectionObserver)
- [web.dev: Lazy-loading images](https://web.dev/articles/lazy-loading-images)
- [Intersection Observer: Practical examples](https://developers.google.com/web/updates/2016/04/intersectionobserver)
- [CSS-Tricks: Animating on scroll](https://css-tricks.com/scroll-animations-with-intersection-observer/)
- [LWN: Intersection Observer overview (2020)](https://lwn.net/Articles/815575/)
