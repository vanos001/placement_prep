# HTML & CSS Fundamentals

## Semantic HTML

Use elements that convey meaning, not just appearance:

```html
<!-- ❌ Bad -->
<div class="header">
  <div class="nav">
    <div class="nav-item">Home</div>
  </div>
</div>
<div class="content">
  <div class="article">
    <div class="title">Article Title</div>
  </div>
</div>

<!-- ✅ Good -->
<header>
  <nav>
    <a href="/">Home</a>
  </nav>
</header>
<main>
  <article>
    <h1>Article Title</h1>
  </article>
</main>
```

Key semantic elements:
- `<header>`, `<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<footer>`
- `<h1>`-`<h6>` for headings (hierarchy matters)
- `<button>` for actions, `<a>` for navigation
- `<ul>`, `<ol>`, `<dl>` for lists
- `<table>` for tabular data (not layout)

## Accessibility (a11y)

```html
<!-- ARIA labels -->
<button aria-label="Close dialog">×</button>
<img src="chart.png" alt="Sales increased 40% from Jan to Jun">

<!-- Focus management -->
<div role="dialog" aria-modal="true" aria-labelledby="title">
  <h2 id="title">Confirm Action</h2>
</div>

<!-- Keyboard navigation -->
<nav>
  <a href="/home" tabindex="0">Home</a>
  <a href="/about" tabindex="0">About</a>
</nav>
```

## CSS Box Model

```
┌─────────────────────────────────┐
│           Margin                │
│  ┌───────────────────────────┐  │
│  │        Border             │  │
│  │  ┌─────────────────────┐  │  │
│  │  │     Padding         │  │  │
│  │  │  ┌───────────────┐  │  │  │
│  │  │  │   Content     │  │  │  │
│  │  │  └───────────────┘  │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

```css
/* box-sizing: border-box makes width include padding + border */
* { box-sizing: border-box; }

.box {
  width: 200px;        /* content width (or total width with border-box) */
  padding: 20px;
  border: 2px solid;
  margin: 10px;
}
```

## Flexbox

One-dimensional layout (row or column):

```css
.container {
  display: flex;
  justify-content: space-between; /* main axis */
  align-items: center;            /* cross axis */
  flex-wrap: wrap;
  gap: 16px;
}

.item {
  flex: 1;           /* grow equally */
  flex: 0 0 200px;   /* fixed 200px, no grow/shrink */
}
```

| Property | Values | Purpose |
|---|---|---|
| `justify-content` | flex-start, center, space-between, space-around, space-evenly | Main axis alignment |
| `align-items` | flex-start, center, flex-end, stretch | Cross axis alignment |
| `flex-direction` | row, column, row-reverse, column-reverse | Main axis direction |
| `flex-wrap` | nowrap, wrap | Allow wrapping |
| `gap` | px, em | Space between items |

## CSS Grid

Two-dimensional layout:

```css
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: auto 1fr auto;
  gap: 16px;
}

/* Named areas */
.layout {
  display: grid;
  grid-template-areas:
    "header header header"
    "sidebar main   aside"
    "footer footer footer";
  grid-template-columns: 200px 1fr 200px;
}

.header  { grid-area: header; }
.sidebar { grid-area: sidebar; }
.main    { grid-area: main; }
```

## Responsive Design

```css
/* Mobile-first approach */
.container {
  padding: 16px;
  font-size: 14px;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    padding: 24px;
    font-size: 16px;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    max-width: 1200px;
    margin: 0 auto;
  }
}
```

## CSS Specificity

```
Inline > ID > Class/Pseudo-class > Element/Pseudo-element

#header     → specificity: 0,1,0,0
.nav .item  → specificity: 0,0,2,0
div p       → specificity: 0,0,0,2
*           → specificity: 0,0,0,0
!important  → overrides everything (avoid!)
```

## Interview Questions

**Q: What is the CSS box model?**
A: Every element is a box with content, padding, border, and margin (inside-out). `box-sizing: border-box` makes `width` include padding and border, making layouts more predictable.

**Q: When would you use Flexbox vs Grid?**
A: Flexbox for one-dimensional layouts (row OR column) — navbars, card rows, centering. Grid for two-dimensional layouts (rows AND columns) — page layouts, dashboards, galleries. They complement each other.

**Q: What is specificity in CSS?**
A: The algorithm browsers use to decide which CSS rule wins when multiple rules target the same element. Order: inline styles > IDs > classes/pseudo-classes > elements/pseudo-elements. `!important` overrides everything but should be avoided.

## References

- [MDN Web Docs](https://developer.mozilla.org/)
- [CSS-Tricks Flexbox Guide](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)
- [CSS-Tricks Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
