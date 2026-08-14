# Web Accessibility

Accessibility (a11y) ensures that websites are usable by everyone, including people with visual, auditory, motor, or cognitive disabilities. This guide covers WCAG guidelines, ARIA, semantic HTML, and common mistakes — topics critical for interviews and professional development.

## WCAG Guidelines Overview

The Web Content Accessibility Guidelines (WCAG 2.1) are organized around four principles:

| Principle | Description | Example |
|-----------|-------------|---------|
| **Perceivable** | Content must be presentable in ways users can perceive | Alt text for images, captions for video |
| **Operable** | UI components must be operable (keyboard, voice, mouse) | All interactive elements must be keyboard-accessible |
| **Understandable** | Content and UI must be understandable | Clear language, predictable navigation |
| **Robust** | Content must be compatible with assistive technologies | Valid HTML, proper ARIA usage |

### Conformance Levels

- **A** — Minimum (essential for some users)
- **AA** — Standard (recommended; legal requirement in many jurisdictions)
- **AAA** — Enhanced (highest accessibility)

Most organizations target **WCAG 2.1 AA**. WCAG 2.2 (released October 2023) added criteria on focus appearance, dragging, and target size.

## ARIA: Roles, States, and Properties

ARIA (Accessible Rich Internet Applications) supplements HTML when native elements aren't sufficient. It has three categories:

### Roles — What is it?

```html
<div role="navigation" aria-label="Main">
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
<div role="alert" aria-live="assertive">
<div role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100">
```

**First rule of ARIA:** Don't use ARIA if a native HTML element does the job. Prefer `<button>` over `<div role="button">`, `<nav>` over `<div role="navigation">`.

### States — What's happening now?

```html
<button aria-expanded="false">Menu</button>
<button aria-pressed="true">Like</button>
<input aria-invalid="true" aria-describedby="error-msg">
<div aria-hidden="true">Decorative content</div>
```

### Properties — What does it mean?

```html
<img alt="Product photo" aria-label="Close dialog">
<button aria-describedby="hint-text">Submit</button>
<li aria-selected="true">Active tab</li>
<div role="treeitem" aria-level="2" aria-setsize="10" aria-posinset="3">
```

### Common ARIA Attributes

| Attribute | Purpose | Example Value |
|-----------|---------|---------------|
| `aria-label` | Provides accessible name | `"Close dialog"` |
| `aria-labelledby` | Points to element providing the name | `id="title"` |
| `aria-describedby` | Points to element providing description | `id="instructions"` |
| `aria-live` | Announces dynamic content changes | `"polite"`, `"assertive"` |
| `aria-expanded` | Whether element is open/closed | `"true"` / `"false"` |
| `aria-modal` | Whether dialog traps focus | `"true"` |
| `aria-hidden` | Hides element from accessibility tree | `"true"` |

## Semantic HTML for Accessibility

Semantic HTML provides built-in accessibility — use it as your first tool:

```html
<!-- ❌ Non-semantic -->
<div onclick="go()">Click me</div>
<div class="header">
  <div class="nav"><span onclick="home()">Home</span></div>
</div>

<!-- ✅ Semantic -->
<button type="button">Click me</button>
<header>
  <nav>
    <a href="/">Home</a>
  </nav>
</header>
```

**Key semantic elements:**
- `<button>` — native keyboard support, focusable, submit/submit behavior in forms
- `<nav>` — landmark, screen readers can jump to it
- `<main>` — primary content landmark (only one per page)
- `<article>`, `<section>` — content landmarks with `aria-labelledby` implied by heading
- `<label>` — associates text with form controls
- `<fieldset>` + `<legend>` — groups related form controls

```html
<!-- Proper form labeling -->
<label for="email">Email</label>
<input id="email" type="email" required aria-describedby="email-hint">
<span id="email-hint">We'll never share your email</span>
```

## Keyboard Navigation

All interactive elements must be accessible via keyboard. The natural tab order follows the DOM order.

### Focus Management

```javascript
// Focus trap for modals (keeps focus within dialog)
function trapFocus(element) {
  const focusable = element.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  element.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  });
}

// Focus management for modals
const previousFocus = document.activeElement;
dialog.showModal();
dialog.querySelector('button').focus(); // focus first interactive element
// On close:
previousFocus.focus(); // restore focus
```

### Tabindex Values

| Value | Behavior |
|-------|----------|
| `0` | Element is focusable in natural tab order |
| `-1` | Programmatically focusable (via `.focus()`), not in tab order |
| `1+` | **Never use** — breaks natural tab order |

## Screen Reader Testing

### Tools
- **VoiceOver** (macOS: Cmd+F5, iOS: Settings → Accessibility)
- **NVDA** (Windows, free)
- **JAWS** (Windows, commercial)
- **Chrome DevTools** → Accessibility panel → Inspect accessibility tree

### What Screen Readers Announce
- Element roles and names
- State changes (`aria-live` regions)
- Focus movement
- Link destinations (`<a href>` vs `<a href="#">`)

## Color Contrast

WCAG AA requires minimum contrast ratios:

| Element | Normal Text | Large Text (18px+ bold or 24px+) |
|---------|-------------|----------------------------------|
| Minimum ratio | 4.5:1 | 3:1 |

```css
/* Use relative color to ensure contrast */
:root {
  --bg: #ffffff;
  --text: #1a1a1a; /* 12.6:1 contrast against white — passes AAA */
  --text-muted: #6b7280; /* 5.5:1 — passes AA for normal text */
}
```

**Never rely on color alone** to convey information. Use icons, patterns, or text labels alongside color:

```html
<!-- ❌ Bad: color-only status -->
<span style="color: red;">Error</span>

<!-- ✅ Good: color + icon + text -->
<span class="error" role="alert">⚠ Error: Invalid email</span>
```

## Common Accessibility Mistakes

| Mistake | Fix |
|---------|-----|
| Using `<div>` as a button | Use `<button>` — native keyboard support |
| Missing `alt` text on images | Add descriptive `alt` (empty `alt=""` for decorative images) |
| Auto-playing video/audio | Add controls, or allow pause |
| Form inputs without labels | Use `<label for="id">` or `aria-label` |
| Low contrast text | Minimum 4.5:1 for normal text |
| Trapping focus unintentionally | Ensure users can escape modals/overlays |
| Skip navigation missing | Add `<a href="#main" class="skip-link">Skip to main</a>` |
| Dynamic content not announced | Use `aria-live` regions for toasts, notifications |
| Focus not visible | Never use `outline: none` on focusable elements (use custom `:focus-visible`) |
| Click-only interactions | Support keyboard equivalents (Enter, Space) |

## Interview Questions

**Q: What is the first rule of ARIA?**
A: Don't use ARIA if a native HTML element provides the semantics you need. A `<button>` is always better than `<div role="button">` because it provides built-in keyboard support, focus management, and screen reader semantics without extra JavaScript.

**Q: How do you test for accessibility?**
A: Automated tools (axe, Lighthouse) catch ~30% of issues. Manual testing includes: keyboard navigation (Tab, Enter, Escape), screen reader testing (VoiceOver, NVDA), contrast checking, and reviewing the accessibility tree in DevTools. Automated + manual testing is essential.

**Q: What is the difference between `aria-label` and `aria-labelledby`?**
A: `aria-label` provides an accessible name directly as a string attribute. `aria-labelledby` references another element by ID whose visible text becomes the accessible name. Use `aria-labelledby` when the label text is already visible on screen; use `aria-label` for non-visible labels.

**Q: How do you handle dynamic content for screen readers?**
A: Use `aria-live` regions. `aria-live="polite"` announces changes when the user is idle (for non-urgent updates). `aria-live="assertive"` interrupts immediately (for critical alerts). Wrap dynamic content (toast notifications, loading states, error messages) in an `aria-live` container.

## References

- [MDN — Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [WCAG 2.1 Guidelines](https://www.w3.org/TR/WCAG21/)
- [web.dev — Accessibility](https://web.dev/learn/accessibility/)
- [ARIA Practices (W3C)](https://www.w3.org/WAI/ARIA/apg/)
