# CSS Deep Dive

This guide builds on the CSS fundamentals covered in [HTML & CSS Fundamentals](html-css-fundamentals.md) with advanced topics that frequently appear in frontend interviews.

## CSS Specificity and the Cascade

The cascade determines which CSS rule wins when multiple rules target the same element. It considers three factors in order:

1. **Origin and importance** (`!important` > normal; author > user-agent)
2. **Specificity** (inline > ID > class > element)
3. **Source order** (later declarations win when specificity ties)

### Specificity Calculation

Specificity is calculated as four components: `(inline, ID, class/pseudo-class/attribute, element/pseudo-element)`

```css
*                          → (0, 0, 0, 0)
div                        → (0, 0, 0, 1)
div p                      → (0, 0, 0, 2)
.class                     → (0, 0, 1, 0)
.class .other               → (0, 0, 2, 0)
div.class                  → (0, 0, 1, 1)
#id                        → (0, 1, 0, 0)
#id .class div             → (0, 1, 1, 1)
style=""                   → (1, 0, 0, 0)
.class:hover               → (0, 0, 2, 0)  /* pseudo-class counts as class */
div::before                → (0, 0, 0, 2)  /* pseudo-element counts as element */
:not(.class)               → (0, 0, 1, 0)  /* :not() counts its argument */
```

**Interview trap:** `:not(.class)` doesn't add to specificity — the argument inside `:not()` does. `:where(.class)` adds **zero** specificity (useful for base styles). `:is(.class)` takes the **highest** specificity of its arguments.

```css
/* :where() for zero-specificity base styles */
:where(.card) { padding: 1rem; }

/* :is() for simplifying selectors */
:is(.header, .footer) .nav { display: flex; }
/* Equivalent to: .header .nav, .footer .nav */
```

## Flexbox Deep Dive

### Common Patterns

**Holy Grail Layout:**
```css
.container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.main {
  flex: 1; /* fills remaining space */
}
```

**Centering (the classic):**
```css
.center {
  display: flex;
  justify-content: center; /* horizontal */
  align-items: center;     /* vertical */
}
```

**Equal-width columns:**
```css
.columns {
  display: flex;
  gap: 1rem;
}
.columns > * {
  flex: 1;               /* equal share */
  min-width: 0;          /* prevents overflow */
}
```

### Interview Traps

**Q: Why does `flex: 1` sometimes cause overflow?**
Each flex item has a `min-width: auto` by default, which equals the item's content width. Long content (e.g., an unbroken word) prevents the item from shrinking. Fix with `min-width: 0` or `overflow: hidden`.

**Q: What's the difference between `gap` and `margin` on flex items?**
`gap` only adds space between items (no leading/trailing space). `margin` on items adds space on all sides, which can cause extra space at the container edges.

**Q: How does `flex-basis: 0` differ from `flex-basis: auto`?**
With `flex-basis: 0` (or `flex: 1`), all items start at zero and share space equally based on their `flex-grow`. With `flex-basis: auto` (or `flex: auto`), items start at their content size, then remaining space is distributed proportionally.

## Grid Deep Dive

### Common Layouts

**Responsive auto-fill grid:**
```css
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}
/* Automatically creates as many 250px+ columns as fit */
```

**Page layout with named areas:**
```css
.page {
  display: grid;
  grid-template-areas:
    "header  header"
    "sidebar content"
    "footer  footer";
  grid-template-columns: 250px 1fr;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
}
```

**Sticky footer without extra markup:**
```css
body {
  display: grid;
  grid-template-rows: auto 1fr auto;
  min-height: 100vh;
}
```

### Grid vs Flexbox Decision

Use **Grid** when items need to align in both dimensions (rows AND columns). Use **Flexbox** when layout flows in one direction. They compose well — use Grid for the page skeleton and Flexbox for components inside grid cells.

## CSS Methodology: BEM

BEM (Block, Element, Modifier) is a naming convention that prevents specificity issues and makes CSS more maintainable:

```css
/* Block: standalone entity */
.card { }

/* Element: part of a block, delimited by __ */
.card__title { }
.card__body { }
.card__image { }

/* Modifier: variation, delimited by -- */
.card--featured { }
.card__title--large { }
```

```html
<div class="card card--featured">
  <img class="card__image" src="..." alt="...">
  <h2 class="card__title card__title--large">Title</h2>
  <div class="card__body">Content</div>
</div>
```

**Benefits:** Flat specificity (all selectors are single-class), self-documenting HTML, easy to understand component relationships. **Alternatives:** SUIT, ITCSS, CUBE CSS.

## CSS Custom Properties

CSS custom properties (variables) enable dynamic, cascade-aware styling:

```css
:root {
  --color-primary: #3498db;
  --color-text: #2c3e50;
  --spacing-sm: 0.5rem;
  --font-size-base: 16px;
}

/* Runtime theming */
[data-theme="dark"] {
  --color-primary: #5dade2;
  --color-text: #ecf0f1;
  --color-bg: #1a1a2e;
}

.card {
  padding: var(--spacing-sm);
  color: var(--color-text);
  background: var(--color-bg);
  font-size: var(--font-size-base);
}
```

**Key difference from Sass variables:** CSS custom properties are live — they cascade, inherit, and can be changed at runtime with JavaScript:

```javascript
document.documentElement.style.setProperty('--color-primary', '#e74c3c');
```

## CSS-in-JS

### Pros and Cons

| Advantage | Disadvantage |
|-----------|-------------|
| Scoped styles by default | Runtime overhead (styles in JS bundle) |
| Dynamic styling with JS variables | No IDE/CSS tooling support |
| Dead code elimination | Larger bundle size |
| Co-located styles with components | Non-standard syntax (learning curve) |
| Theming via context | SSR hydration mismatches (some libs) |

**Libraries:** Styled Components, Emotion, CSS Modules (zero runtime, compile-time scoping).

**Modern trend:** CSS Modules and Tailwind are preferred over runtime CSS-in-JS for performance reasons.

## Tailwind CSS: Utility-First

Tailwind provides atomic utility classes that compose directly in markup:

```html
<div class="flex items-center justify-between p-4 bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow">
  <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
  <button class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:ring-2 focus:ring-blue-300">
    Submit
  </button>
</div>
```

**Advantages:** No context switching (HTML + CSS in one file), consistent design system enforced by utility classes, small production CSS (PurgeCSS removes unused utilities), rapid prototyping.

**Disadvantages:** Verbose HTML, initial learning curve, some find it harder to read.

## CSS Containment

`contain` tells the browser that an element's internal changes won't affect the rest of the page, allowing rendering optimizations:

```css
.card {
  contain: layout style paint;
  /* layout: internal layout doesn't affect outside */
  /* style: counter values are scoped */
  /* paint: nothing inside paints outside the element bounds */
}

/* Shorthand for all three: */
.card {
  contain: strict;
}
```

Use on repeating UI components (cards, list items) — the browser can skip recalculating styles or layout for the rest of the page when a contained element changes.

## Container Queries

Container queries let components style themselves based on their **parent container's size** rather than the viewport:

```css
.card-wrapper {
  container-type: inline-size;
}

@container (min-width: 400px) {
  .card {
    display: flex;
    gap: 1rem;
  }
}

@container (max-width: 399px) {
  .card {
    display: block;
  }
}
```

**Why it matters:** A card component now adapts whether it's in a wide sidebar or a narrow mobile column — without knowing the viewport. This makes truly reusable, context-aware components.

**Browser support:** Chrome 105+, Safari 16+, Firefox 110+.

## Interview Questions

**Q: How does CSS specificity work?**
A: Specificity is (inline, IDs, classes/attributes/pseudo-classes, elements/pseudo-elements). Higher specificity always wins. When specificity is equal, source order wins (last declaration). `!important` overrides normal specificity but should be avoided.

**Q: What is BEM and why use it?**
A: BEM (Block Element Modifier) is a naming convention: `.block`, `.block__element`, `.block--modifier`. It keeps specificity flat (single-class selectors only), prevents cascading conflicts, and makes styles self-documenting.

**Q: How do container queries differ from media queries?**
A: Media queries respond to the **viewport** size. Container queries respond to the **containing element's** size. This lets components adapt to their available space, making them truly reusable regardless of where they're placed.

**Q: When would you use CSS Modules over CSS-in-JS?**
A: CSS Modules generate unique class names at build time with zero runtime overhead. CSS-in-JS (styled-components, emotion) generates styles at runtime, which adds bundle size and serialization cost. Use CSS Modules for performance-critical apps; CSS-in-JS if you need dynamic styles tightly coupled with JS logic.

## References

- [MDN — CSS Specificity](https://developer.mozilla.org/en-US/docs/Web/CSS/Specificity)
- [CSS-Tricks — A Complete Guide to Grid](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [web.dev — CSS Container Queries](https://web.dev/css-container-queries/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
