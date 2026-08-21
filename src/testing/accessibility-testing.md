# Accessibility Testing

Accessibility (a11y) testing verifies that people with disabilities — visual, motor, cognitive, auditory — can perceive, operate, and understand your application. In practice this means testing against the **Web Content Accessibility Guidelines (WCAG)**, the W3C standard cited by legal frameworks like the Americans with Disabilities Act (ADA) and the European Accessibility Act. Automated tools catch roughly 30–50% of WCAG issues; the rest require manual or assistive-technology testing.

## The Accessibility Tree (vs. the DOM)

Every modern browser exposes an **accessibility tree** in parallel to the DOM. The DOM is the structure; the accessibility tree is the *semantic* projection of that structure — what assistive technologies like screen readers actually consume.

```
┌────────────────────────────────────────────────────────────────────┐
│  DOM (HTML)              │  Accessibility tree                     │
│  ─────────────────────────│  ────────────────────────────────────── │
│  <button                 │  button "Save"                          │
│     class="btn-primary"  │   ├─ role: button                        │
│     type="submit"        │   ├─ name: "Save"  (from text content)   │
│     aria-pressed="false" │   ├─ state: not pressed (from aria-pressed)│
│  >Save</button>          │   └─ action: click (default button)     │
│                          │                                          │
│  <div onclick="...">     │  div ""  ← invisible to screen readers!  │
│     Click me             │   ├─ role: generic (useless)              │
│  </div>                  │   └─ name: ""  (no accessible name)       │
└────────────────────────────────────────────────────────────────────┘
```

A screen reader (NVDA, JAWS, VoiceOver, TalkBack) walks the accessibility tree, not the DOM. A `<div>` with an `onclick` handler is in the DOM but has no role and no accessible name in the a11y tree — so the screen reader skips it, and a keyboard user cannot focus it. This is why "it works when I click it with a mouse" is not accessibility.

You can inspect the a11y tree in Chrome DevTools via the "Accessibility" tab in the Elements panel, or programmatically via `node.accessibilityTreeNode()` in Playwright. Lighthouse and axe-core both run by inspecting this tree, not by reading the raw HTML.

## ARIA Roles and Properties

**ARIA** (Accessible Rich Internet Applications) is a W3C spec that augments HTML with semantic attributes the accessibility tree can use. The first rule of ARIA, often quoted but worth repeating: **no ARIA is better than bad ARIA**. A native `<button>` already exposes role `button`, name (from its text content), and click action. Adding `role="button"` to a `<div>` does not make it a button — it just lies to the accessibility tree, and now keyboard users still cannot focus it but screen readers think they can.

```html
<!-- Bad: div with role="button" — looks accessible, isn't -->
<div role="button" tabindex="0" onclick="save()">Save</div>
<!-- Missing: keyboard handler for Enter and Space -->
<!-- Missing: aria-pressed state if it's a toggle -->

<!-- Good: use the native element -->
<button type="submit" onclick="save()">Save</button>
```

ARIA is most valuable when you build custom widgets HTML doesn't have native equivalents for: combo boxes, tab interfaces, tree views, dialog modals. The relevant ARIA attributes fall into three categories:

| Category               | Examples                                 | What they convey |
|------------------------|------------------------------------------|-------------------|
| **Roles**              | `role="tablist"`, `role="dialog"`, `role="alert"` | The semantic type of the element |
| **States**             | `aria-expanded`, `aria-checked`, `aria-busy` | Dynamic state (changes during interaction) |
| **Properties**         | `aria-label`, `aria-labelledby`, `aria-describedby`, `aria-live`, `aria-required` | Static or semi-static metadata |

`aria-live` regions are particularly subtle: they tell the screen reader to announce changes to that region. `aria-live="polite"` waits for the user to pause; `aria-live="assertive"` interrupts immediately. Set this wrong and the screen reader either never announces an "Item added to cart" message, or interrupts the user mid-sentence with a status update.

## WCAG: The Three Levels

WCAG 2.2 (the current recommendation as of October 2023) is organized as four principles — Perceivable, Operable, Understandable, Robust (POUR) — with **78 success criteria** each at conformance level A, AA, or AAA:

| Level | Coverage                                                       | Legal exposure                          |
|-------|----------------------------------------------------------------|-----------------------------------------|
| **A** | Minimum. Mandatory for basic accessibility (alt text, keyboard, no seizure-inducing content) | Always required                          |
| **AA** | Reasonable standard. The level most legislation references (ADA Title II, EAA, Section 508 refresh) | Required for public-sector and most enterprise contracts |
| **AAA** | Highest. Often only achievable for specialized content (sign-language interpretation, no time limits anywhere) | Aspirational; rarely required |

Roughly 50 of the 78 success criteria are **testable by machine**. The remaining 28 require human judgment — for example, "is the alternative text actually meaningful?" and "does the reading order make sense after a layout reflow?" This is why automated tools max out at ~50% of WCAG coverage.

The 12 most common WCAG violations in the wild, all auto-detectable:

1. Missing `alt` text on informative images (1.1.1 Non-text Content, Level A)
2. Form inputs without labels (1.3.1 Info and Relationships, Level A)
3. Missing document language (`<html lang="en">`) (3.1.1 Language of Page, Level A)
4. Insufficient color contrast (< 4.5:1 for normal text) (1.4.3 Contrast Minimum, Level AA)
5. Missing page title and missing skip-to-content link (2.4.2, 2.4.1, Level A)
6. Buttons/links with non-descriptive text ("click here", "read more") (2.4.6 Headings and Labels, Level AA)
7. Tab order that doesn't match visual order (2.4.3 Focus Order, Level A)
8. No visible focus indicator (2.4.7 Focus Visible, Level AA)
9. `tabindex` > 0 used to manipulate tab order (2.4.3, Level A)
10. Auto-playing video with no pause control (1.4.2 Audio Control, Level A)
11. Heading hierarchy skipped (H1 → H3) (1.3.1, Level A)
12. Decorative content not hidden from AT (1.3.1, Level A)

## Automated Tools

### axe-core

Axe (Deque Systems) is the de facto standard. The core engine (`axe-core` on npm) is open source, ~50 KB, and integrates with every popular test runner:

```typescript
// Playwright + axe-core
import { expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('homepage has no a11y violations at level AA', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa'])   // WCAG 2.x A and AA
    .analyze();

  expect(results.violations).toEqual([]);
});
```

Axe runs against the accessibility tree of the rendered page (or component), runs every rule against every node, and returns a `violations` array with severity, rule ID, target selector, and a "fix" suggestion. The 100+ rules in axe-core cover roughly 55% of WCAG success criteria. Axe does **not** check color contrast across dynamic gradients, does not catch focus traps across iframes, and does not test keyboard navigation end-to-end — those require the manual layer.

### Lighthouse Accessibility audit

Lighthouse (Google) bundles axe-core's rules into the Chrome DevTools "Lighthouse" tab and `npx lighthouse` CLI. Its output is a 0–100 score derived from weighted axe violations. Lighthouse is convenient because it is one of the metrics already reported by PageSpeed Insights, but it is a *sample* — it only audits the page you point it at, with the viewport you specify, in the state at the time of the audit. It is not a substitute for an axe-core test suite that hits every page.

```bash
npx lighthouse https://example.com \
  --only-categories=accessibility \
  --output=json \
  --output-path=./a11y-report.json
```

### WAVE

WAVE (WebAIM) is a browser extension and API service that overlays a page with icons indicating violations: missing alt text, contrast failures, structural issues, ARIA misuse. Its strength is the visual overlay — you see exactly which elements are flagged — and its weakness is the lack of a CLI/test-runner integration. Most teams use WAVE as a quick manual spot-check during a review, not as a CI gate.

## Keyboard Navigation Testing

A surprisingly large fraction of WCAG criteria reduce to "can a user operate the page with the keyboard alone." Real users in this category include blind screen-reader users, but also power users who prefer the keyboard, and people with motor impairments who cannot use a mouse.

The keyboard test checklist:

1. **Tab through the page** — does focus move in the same order as the visual layout suggests? Skipped elements = broken.
2. **No keyboard traps** — pressing Tab in a modal dialog must eventually reach a close button, not loop forever inside the modal.
3. **Visible focus indicator** — every focusable element must show a visible ring/outline when focused. Removing `outline: none` without a replacement is the most common Level A violation.
4. **Escape closes modals** — pressing Esc dismisses overlays.
5. **Enter/Space activate buttons** — every "click here" must be reachable via Tab and activatable via Enter/Space.
6. **Arrow keys for composite widgets** — tabs, menus, listboxes, grids follow WAI-ARIA Authoring Practices keyboard patterns.

```typescript
// Playwright keyboard test — verify a combobox opens and is operable
test('search combobox is keyboard-operable', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('combobox').focus();
  await page.keyboard.press('ArrowDown');          // opens popup
  await expect(page.getByRole('option')).toHaveCount(5);
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Enter');              // selects third option
  await expect(page.getByRole('combobox')).toHaveValue('TypeScript');
});
```

Axe cannot catch a missing keyboard handler on a `role="button"` div — it sees the role but not whether `keydown` is wired up. This is one of the classes of bugs that only manual or scripted keyboard tests catch.

## Screen Reader Testing

The four screen readers in production use today:

| Screen reader | Platform                  | Browser                                       | Approximate market share |
|---------------|---------------------------|-----------------------------------------------|--------------------------|
| **NVDA**      | Windows                   | Firefox, Chrome, Edge                          | ~40% of blind users      |
| **JAWS**      | Windows                   | Chrome, Edge (legacy IE too)                  | ~30% — corporate/enterprise |
| **VoiceOver** | macOS, iOS                | Safari                                         | ~25%                     |
| **TalkBack**   | Android                   | Chrome                                         | ~5% — Android phones     |

Screen reader testing is fundamentally manual: you launch the screen reader, navigate the page, and listen. There is no automated "what does this page sound like to a screen reader" tool that catches a meaningful fraction of issues — they all stop short because what matters is whether the *sequence* of spoken output makes sense, which is a context-dependent judgment.

There are practical heuristics for catching common screen reader bugs without firing up NVDA:

1. **Run the axe-core `region` and `landmark` rules** — missing `<main>`, `<nav>`, `<header>` are silent for sighted users but break screen-reader navigation.
2. **Disable CSS** in the browser and read the page top-to-bottom. That is roughly the order a screen reader will read it. If the order is gibberish without styling, the screen reader output is gibberish.
3. **Inspect `aria-label` values** — a button with `aria-label="X"` reads "X" to screen readers. Common bug: the visual label says "Save changes" but `aria-label="disk icon"` overrides it for AT users, breaking parity.
4. **Check `<img alt>` for content vs. decoration.** Decorative images should have `alt=""` (empty); informative images need descriptive alt text. Mislabeling in either direction is a violation.

For a real accessibility audit, the workflow is: (1) axe-core across the whole app, (2) keyboard walkthrough, (3) VoiceOver or NVDA walkthrough of the three highest-traffic flows. Steps 2 and 3 take hours per flow. This is why fully-audited WCAG AA compliance is expensive.

## Manual vs. Automated Testing

| Concern                        | Automated (axe/Lighthouse/WAVE) | Manual              |
|--------------------------------|--------------------------------|---------------------|
| % of WCAG SCs covered          | ~50%                           | ~100%               |
| Time per page                  | Seconds                        | 30–60 minutes        |
| Catches text meaning           | No                             | Yes                 |
| Catches keyboard traps         | No (with rare axe exception)   | Yes                 |
| Catches screen reader quirks   | No                             | Yes                 |
| Catches focus order issues     | Partially (via DOM order)      | Yes                 |
| Runs in CI                     | Yes                            | No (mostly)         |
| Cost per regression            | Cheap                          | Expensive           |

The recommended pattern: automated a11y tests in CI on every PR (catches the cheap stuff before a human sees it), plus a quarterly full audit by a trained accessibility specialist on the top user flows, plus an assistive-tech walkthrough before any major launch. The automated tests do not replace the audit; they make sure the audit time is spent on hard issues, not on re-finding missing `alt` attributes.

```typescript
// Run axe-core in component tests AND in e2e tests, with per-page
// expected-violation lists so regressions are caught but known
// exceptions don't block CI.
test('checkout flow — known issues only', async ({ page }) => {
  await page.goto('/checkout');
  const results = await new AxeBuilder({ page }).analyze();
  const known = new Set(['color-contrast:shipping-label']);
  const newViolations = results.violations.filter(
    (v) => !known.has(`${v.id}:${v.target}`)
  );
  expect(newViolations).toEqual([]);
});
```

The known-issues allow-list is honest: every team has an a11y debt list. Burying those issues in `// TODO` comments in CSS files ensures they never get fixed; surfacing them in code review via a typed allow-list makes the debt visible and tracked.

## References

- [axe-core documentation](https://github.com/dequelabs/axe-core)
- [W3C WAI-ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [WCAG 2.2 recommendation](https://www.w3.org/TR/WCAG22/)
- [MDN: Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility)
- [WebAIM — Web Accessibility Evaluation Tool (WAVE)](https://wave.webaim.org/)
- [Lighthouse Accessibility scoring](https://web.dev/articles/lighthouse-accessibility)
- [Playwright Axe integration](https://playwright.dev/docs/accessibility-testing)
