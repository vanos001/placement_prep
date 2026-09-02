# Visual Regression Testing

Visual regression testing (VRT) catches unintentional changes to a UI by comparing the rendered pixels of a page or component against a previously approved baseline. Where unit and integration tests assert on logic ("does this function return 200?"), VRT asserts on appearance ("does this button still look like a green rounded button at 64 px wide, even after the design-system refactor?"). It is the only automated technique that reliably catches off-by-one CSS regressions, broken responsive breakpoints, and dark-mode bugs that no DOM assertion can see.

## The Baseline / Current / Diff Model

Every VRT run is three images and a comparison:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Visual regression test pipeline                                    │
│                                                                      │
│   ┌────────────┐         ┌────────────┐         ┌──────────────┐     │
│   │  Baseline   │         │  Current   │         │   Diff mask   │     │
│   │  (committed │   xor   │  (freshly  │   ──►   │  (red where    │     │
│   │   snapshot) │         │  rendered) │         │   pixels differ)│   │
│   └────────────┘         └────────────┘         └───────┬───────┘     │
│                                                          │             │
│                                                          ▼             │
│                                       ┌──────────────────────────┐   │
│                                       │  % pixels differing        │   │
│                                       │   > threshold ?            │   │
│                                       │  YES → FAIL (review)       │   │
│                                       │  NO  → PASS                │   │
│                                       └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

On the first run, there is no baseline. The current render becomes the baseline — it is committed to the repo (Playwright) or stored in a service (Percy, Applitools) and the test passes trivially. On every subsequent run, the current render is pixel-diffed against that baseline. If the diff exceeds a configured threshold, the test fails; otherwise it passes.

When a change is **intentional** (you actually want the new look), you approve the new image as the new baseline — Percy has a one-click "Approve" button in its PR review UI; Playwright's `--update-snapshots` regenerates the local baseline file; Applitools has admin roles for baselines.

## Pixel Diffs and Thresholds

The naive diff — count the pixels whose RGB differs by even one channel — is unusable in practice. Anti-aliasing, font hinting differences across OSes, GPU-dithered gradients, and slight viewport size drift all produce enormous diffs for visually identical renders. Real VRT uses one of three threshold schemes:

| Threshold type          | How it works                                                | Typical value      |
|-------------------------|-------------------------------------------------------------|--------------------|
| **Per-pixel RGB delta** | Sum `\|Δr\| + \|Δg\| + \|Δb\|` per pixel, count pixels where this exceeds tolerance | `<= 0.2` channel diff tolerated |
| **Per-pixel ratio**     | `changedPixels / totalPixels` ≤ ratio                       | `maxDiffPixelRatio: 0.01` (1%) |
| **Per-pixel count**     | Hard count of changed pixels                                | `maxDiffPixels: 2500` (50×50 box) |
| **Per-region**          | Divide image into N×M cells; report any cell with diff > cell threshold | e.g. 32×32 grid, 5% per cell |
| **Structural (SSIM / perceptual)** | Compare luminance/contrast/structure windows; report SSIM index | `ssim > 0.95` to pass |

The structural (SSIM) approach is the most resilient to anti-aliasing noise but the hardest to reason about. Most teams ship a hybrid: pixel ratio for the "is there a visible difference at all" gate, plus an SSIM sanity check for the "is it the same layout" question.

```typescript
// Playwright hasScreenshot with per-pixel thresholds
test('pricing page matches baseline', async ({ page }) => {
  await page.goto('/pricing');
  await expect(page).toHaveScreenshot('pricing.png', {
    maxDiffPixelRatio: 0.01,        // up to 1% of pixels may differ
    maxDiffPixels: 5000,            // OR up to 5000 absolute pixels
    threshold: 0.2,                  // per-pixel RGB delta tolerance
    animations: 'disabled',         // freeze CSS animations
    mask: [page.locator('[data-testid="live-clock"]')],  // ignore clock region
    maskColor: '#ff00ff',
  });
});
```

The `mask` parameter is essential for any region that legitimately varies per run — live timestamps, A/B variant badges, randomized placeholder avatars. Without masking, those regions dominate the diff and every test flake-trips on them.

## Tools

### Playwright `toHaveScreenshot`

Bundled with `@playwright/test` since v1.17. Baselines are PNG files committed to the repo under `tests/visual.spec.ts-snapshots/`. No external service needed. Best for teams that want zero vendor lock-in and already use Playwright. Cost: storage of PNGs in the repo (a 1080p screenshot is ~300 KB; a 50-snapshot suite adds ~15 MB to the repo).

### Percy (BrowserStack)

A SaaS visual review platform. The test runner calls `percySnapshot(page, 'name')` which uploads the DOM + assets to Percy's render farm; Percy renders it across browsers/viewports server-side, pixel-diffs, and posts a review comment on your PR with a slider showing baseline vs. current side by side. Percy's killer feature is that it doesn't diff the screenshot you sent — it re-renders the page from the captured DOM, which means flaky client-side animations are eliminated. Baselines live in Percy, not in your repo.

```javascript
import Percy from '@percy/playwright';

test('about page renders correctly', async ({ page }) => {
  await page.goto('/about');
  await Percy.snapshot(page, 'About page desktop', { widths: [1280, 1920] });
});
```

### Applitools Eyes

The market leader in AI-assisted diff. Applitools' "Visual AI" is a learning model trained on millions of real-world diffs that classifies differences as either *visible* (font weight change, layout shift, color change) or *invisible* (anti-aliasing, dithering, sub-pixel rendering). It suppresses the latter so aggressively that an SSIM diff of 0.93 can pass as visually identical. The trade-off: it is a paid commercial product, and review requires going to their dashboard.

```typescript
import { Eyes, Target } from '@applitools/eyes-playwright';

test('login visual regression', async ({ page }) => {
  const eyes = new Eyes();
  await eyes.open(page, 'My App', 'Login visual test');
  await page.goto('/login');
  await eyes.check('Login form', Target.window().fully());
  await eyes.close();
});
```

### BackstopJS

A standalone Node tool that ships with its own Puppeteer engine. You write a JSON config describing URLs to capture and viewports to test, and BackstopJS generates a side-by-side HTML report with slider diffs. It is the most popular open-source-only option for teams that don't want a SaaS dependency. Downside: no AI, so you live with the false-positive problem directly.

```json
{
  "id": "homepage_test",
  "viewports": [
    { "label": "desktop", "width": 1920, "height": 1080 },
    { "label": "mobile",  "width": 375,  "height": 812 }
  ],
  "scenarios": [
    {
      "label": "Homepage hero",
      "url": "http://localhost:3000/",
      "selectors": ["#hero"],
      "misMatchThreshold": 0.01
    }
  ]
}
```

## AI-Assisted Diff: What Applitools Actually Does

Applitools' "Visual AI" is not a generic deep learning model. It is a cascade of specifically-tuned detectors:

1. **Exact pixel match first.** Cheap, fast, and catches trivial changes.
2. **Ignore anti-aliasing** by down-sampling both images with a Gaussian and re-diffing at multiple resolutions.
3. **Layout comparison** — partition the image into regions (DOM elements with bounding boxes, if available) and check whether the *structure* (size, position, color family) of each region matches. A button that moved from `(10, 50)` to `(15, 55)` is flagged as layout shift; a button whose color shifted from `#2d7d2d` to `#2d8d2d` is flagged as color shift.
4. **Ignore** regions explicitly marked as dynamic (timestamps, ads, user content).
5. **Match against a learned model** that has been told "this kind of pixel difference is visually irrelevant" across millions of training cases.

The practical result: Applitools reports a *single* "Login button moved 4 px to the right" issue where naive pixel diff would have flagged 30,000 pixels of difference and made the review screen unusable. The pricing reflects this — Applitools is per-snapshot per-month, an order of magnitude more expensive than Percy.

## Visual Regression vs. Snapshot Testing

These two terms are often conflated. They are not the same thing.

| Concern                | Visual Regression                       | Snapshot Testing (Jest)                   |
|------------------------|-----------------------------------------|--------------------------------------------|
| What is captured       | The rendered pixels (PNG/JPG)            | The serialized output of a function (string, JSON, HTML string) |
| What is diffed         | Pixels                                  | Text                                       |
| Detects                | Layout, color, font, image regressions  | Structural/serial regressions             |
| Misses                 | Anything that renders as identical text but different pixels (e.g. CSS `font-weight: 400` → `300` on the same string) | Anything that renders differently with identical text (e.g. CSS changes the appearance without changing the rendered HTML string) |
| Storage                | Binary, large (KB-MB per snap)          | Text, small (KB per snap)                 |
| Review UX              | Slider image diff in PR comment         | Text diff in PR comment                     |
| False-positive rate    | High without AI/threshold tuning         | Low for stable components, high for churny ones |

The honest takeaway: they are complementary. Use Jest snapshot for "did the props spread on this `<Button>` change?", use VRT for "did the button's appearance change?"

## The False Positive Problem

Visual regression is the only testing technique where the naive failure rate is high enough to destroy team trust in days. A 5% threshold that catches a 3-px text shift also catches:

- Slightly different font rendering on Linux CI vs. dev Mac (font hinting, sub-pixel AA).
- Different default scrollbar width on Chrome 119 vs. 120.
- A 1-pixel viewport drift because the test runner window is `+1px` taller.
- Different antialiasing on screenshots taken with vs. without `deviceScaleFactor: 2`.
- Animations at non-deterministic frames.

Mitigations, in order of effectiveness:

1. **Pin the rendering environment.** Same Docker image in CI as on dev; same `deviceScaleFactor`; same `fontFamily` (use a web font, don't depend on system Helvetica).
2. **Disable animations.** Every VRT tool has a flag for this; Playwright: `animations: 'disabled'`. CSS transitions on `:hover` are the worst offenders.
3. **Mask dynamic regions.** Clocks, dates, ads, A/B variants, placeholder avatars.
4. **Use AI-assisted diff (Applitools) for high-churn UIs** — the model pays for itself in false-positive reduction.
5. **Never use VRT as a gate against main; only on PRs.** A flaky main-branch VRT failure blocks every PR until someone hits `--update-snapshots`.
6. **Treat the baseline file as a code review artifact.** Every `--update-snapshots` change should be in a PR by itself, with a screenshot of the new render in the PR description. The diff in the PNG is binary; reviewers cannot meaningfully review it.

A team that adopts VRT without doing (1)–(5) usually abandons the practice within a quarter. A team that does all five ships with confidence that a CSS change to the design system won't break the checkout page without being noticed.

## References

- [Percy — Visual regression testing](https://docs.percy.io/)
- [Applitools — Visual AI documentation](https://applitools.com/docs/)
- [BackstopJS — GitHub](https://github.com/garris/BackstopJS)
- [Playwright visual comparisons (`toHaveScreenshot`)](https://playwright.dev/docs/test-snapshots)
- [Playwright screenshot options (thresholds, masks)](https://playwright.dev/docs/api/test-locator#locator-screenshot)
- [Structural Similarity Index (SSIM) — Wikipedia](https://en.wikipedia.org/wiki/Structural_similarity)
