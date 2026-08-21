# Playwright

Playwright is Microsoft's cross-browser end-to-end testing framework, open-sourced in January 2020. It drives Chromium, Firefox, and WebKit from a single Node.js API, ships first-class bindings for TypeScript, JavaScript, Python, Java, and .NET, and treats flaky timing as a framework-level concern rather than something tests should `sleep()` around. This page digs into how Playwright actually talks to browsers, why its locator model is opinionated, and what its fixture and trace tooling buy you over Cypress.

## Browser Automation: CDP and Beyond

The single most important architectural choice in Playwright is that it does not ship a custom browser. It drives the browsers you already have, using the protocols each vendor actually exposes.

```
┌─────────────────────────────────────────────────────────────────┐
│                       Playwright Test Process                    │
│  (Node.js, one per worker)                                       │
│                                                                  │
│   ┌─────────────┐ ┌──────────────┐ ┌──────────────────────┐      │
│   │ Test runner  │ │ Expect API   │ │ Auto-wait scheduler │      │
│   └──────┬──────┘ └──────────────┘ └──────────┬───────────┘      │
│          │                                    │                  │
│          └────────────────┬───────────────────┘                  │
│                           │  Playwright client (per browser)     │
│                           ▼                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │  JSON-RPC over pipe / WebSocket
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌────────────────┐
│  Chromium     │  │   Firefox    │  │   WebKit       │
│  via CDP      │  │ via Juggler  │  │ via IPC patch  │
│  (DevTools    │  │ (Mozilla    │  │ (Apple-patched │
│   Protocol)   │  │  patch)     │  │  WebKit)       │
└──────────────┘  └──────────────┘  └────────────────┘
   one CDP            Juggler          patched build with
   session per        protocol,        bidirectional IPC
   context            CDP-like          on top of the
                       surface           InspectorController
```

For Chromium, Playwright connects over the **Chrome DevTools Protocol (CDP)** — the same WebSocket protocol that `chrome --headless --remote-debugging-port=9222` exposes and that DevTools itself uses. Each `BrowserContext` maps to a CDP `Target`, and `page.goto`, `page.click`, `page.fill` translate to `Page.navigate`, `Input.dispatchMouseEvent`, and `DOM.querySelector` + `Input.insertText` calls. Crucially, Playwright *patches* the browser binaries it downloads (`playwright install`) to add capabilities that vanilla CDP cannot provide: reliable domain isolation between contexts, deterministic input event timing, and access to the `Target.setAutoAttach` edge cases the public protocol leaves buggy.

For Firefox, Playwright ships a Mozilla fork that adds a protocol called **Juggler**. It is intentionally CDP-shaped — methods like `Page.navigate`, `Runtime.evaluate`, `DOM.querySelector` mirror CDP — but it lives inside the Firefox binary rather than over a debugging port. Juggler is what lets the same JavaScript test code run unmodified against Firefox.

For WebKit, Playwright maintains a patched WebKit build that exposes an IPC channel to a custom `InspectorController`. Because Safari's Web Inspector is more locked-down than Chrome's, the patch set is larger. This is why Playwright's WebKit is the most faithful Safari simulation available outside Apple — significantly closer than Cypress's bundled Electron/Chromium.

The user-visible consequence: a single `test('login works', ...)` body runs against three real browser engines in CI without changing a line of code.

```typescript
// playwright.config.ts — one config, three engines, multiple viewports
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',          // capture trace only when a retry fires
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
    { name: 'mobile',   use: { ...devices['iPhone 15'] } },
  ],
});
```

## Auto-Waiting

Auto-waiting is the reason Playwright tests rarely contain `waitForTimeout` calls. Before every action — `click`, `dblclick`, `fill`, `check`, `selectOption` — the engine polls the target element through a fixed actionability checklist and only proceeds once every gate is green:

| Gate                  | Required state                                           |
|-----------------------|----------------------------------------------------------|
| Attached              | Element exists in the DOM tree                           |
| Visible               | Non-empty bounding box, non-zero opacity, no `display:none` |
| Stable                | Bounding box has not moved more than 4 px in the last 1 s |
| Receives events       | Hit-test at the element center hits the element (no overlay) |
| Enabled               | Not `disabled`, not `aria-disabled`, no `readonly`       |
| Editable (for `fill`) | Not `readonly`, not `contenteditable="false"`            |

If the gates don't all open within the per-action timeout (default 30 s), Playwright throws with a *list of the gates that failed and the last 10 inspector snapshots*. The failure message is the killer feature: instead of "element not found", you get "element is attached but covered by `div.modal-overlay` at (540, 320) — see screenshot at frame 4 of the trace."

Assertions auto-wait too. `expect(locator).toBeVisible()` re-evaluates visibility on every animation frame (roughly every 16 ms) until the predicate holds or the assertion timeout (default 5 s) elapses. This is what distinguishes a Playwright assertion from a Cypress `cy.should()` chain — both retry, but Playwright's retries are *predicate-driven on the engine side*, not poll-driven from a Cypress-specific queue.

```typescript
// No sleeps anywhere; the framework waits
test('search returns results', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Search' }).fill('playwright');
  await page.getByRole('button', { name: 'Go' }).click();

  const results = page.getByRole('listitem');
  await expect(results).toHaveCount(10);   // polls until 10 listitems exist
  await expect(page.getByText('Showing 10 of 423')).toBeVisible();
});
```

## The Locator Model

A `Locator` is a *description* of how to find an element, not a handle to an element. This is the conceptual break from Selenium's `WebElement` and Puppeteer's `ElementHandle`. A `Locator` re-resolves on every call — if the React tree re-renders and the `<button>` is now a new DOM node, the locator still works because it is re-queried.

Playwright strongly prefers **semantic locators** over CSS selectors:

| Method                              | Maps to                                | Why preferred                                |
|-------------------------------------|----------------------------------------|-----------------------------------------------|
| `getByRole('button', { name: 'Save' })` | ARIA role + accessible name           | Survives refactors, mirrors how screen readers see it |
| `getByLabel('Email')`               | Form label association                 | Tied to UX semantics, not CSS                 |
| `getByText('Welcome back')`         | Text content                           | Tests intent, not markup                      |
| `getByAltText`, `getByTitle`, `getByPlaceholder`, `getByTestId` | Progressively weaker | Use `data-testid` as escape hatch only       |

```typescript
// The "right" way
const submit = page.getByRole('button', { name: /sign in/i });
await submit.click();

// Chained and filtered
await page
  .getByRole('listitem')                          // a list of results
  .filter({ hasText: 'Playwright' })             // narrow to those mentioning Playwright
  .first()
  .click();

// nth, has, has-not
await page.getByRole('row').nth(2).getByRole('checkbox').check();
```

This isn't aesthetic preference. Tests that use `getByRole` survive a refactor from `<div class="btn-primary">` to `<button class="btn-primary">` without rewriting the test. They also double as a poor-person's accessibility check: if `getByRole('button', { name: 'Save' })` fails to find anything, your button is probably not a real button — it's a `<div>` with an onclick handler, and screen reader users can't see it.

## The Fixture Model: `test.extend`

Playwright's `test` function ships with a built-in dependency injection system based on fixtures. Fixtures are lazy, scoped (test or worker), and composable, and they replace the `beforeEach`/`beforeAll` boilerplate that Cypress needs.

```typescript
import { test as base, expect, type Page } from '@playwright/test';

// A custom fixture: an authenticated browser context
type AuthFixtures = {
  authedPage: Page;
  apiClient: { createOrder: (item: string) => Promise<{ id: string }> };
};

export const test = base.extend<AuthFixtures>({
  authedPage: async ({ browser }, use) => {
    const ctx = await browser.newContext({ storageState: 'state/auth.json' });
    const page = await ctx.newPage();
    await use(page);
    await ctx.close();
  },
  apiClient: async ({ request }, use) => {
    await use({
      createOrder: async (item) => {
        const r = await request.post('/api/orders', { data: { item } });
        return r.json();
      },
    });
  },
});

// Now every test using `test` gets these injected; only tests that
// request `authedPage` pay the storage-state setup cost.
test('order list shows new order', async ({ authedPage: page, apiClient }) => {
  const order = await apiClient.createOrder('Widget');
  await page.goto('/orders');
  await expect(page.getByText(order.id)).toBeVisible();
});
```

Fixture scoping rules:

- **Test-scoped** (default): fresh instance per test, torn down after.
- **Worker-scoped** (`{ scope: 'worker' }`): one instance per worker, reused across tests on that worker. Used for expensive setup like a seeded database or a logged-in `BrowserContext` shared by a smoke suite.
- **Automatic**: declared without `use` callback; the framework treats the value as a constant.

Because fixtures resolve dependencies via parameter names, transitive dependencies just work: a `worker` fixture that depends on `browser` will be created after `browser`, and destroyed before it.

## Trace Viewer

The **Trace Viewer** is a local PWA that replays a recorded test as a timeline. Open `trace.zip` with `npx playwright show-trace trace.zip` and you get:

1. A **frames timeline** — every animation frame the test ever saw, with the live DOM snapshot, console logs, network requests, and source location of the test step at that moment.
2. A **call log** — every Playwright API call (`page.goto`, `locator.click`) with arguments, return value, and duration.
3. A **DOM snapshot per action** — open the inspector on the snapshot from 8 frames ago to see the page as it was when the click was attempted.
4. **Network waterfall** — every fetch, with request/response bodies, headers, and timing.
5. **Console and error streams** interleaved with the timeline.

Trace recording is opt-in because it is expensive (10–30% slowdown, a few MB per test). The idiomatic config is `trace: 'on-first-retry'` — record only when the test already failed once and you're about to retry. The second attempt's trace is then waiting in `test-results/` for inspection. In CI, this is the difference between "flaky test, can't reproduce" and "here is a 4 K-frame movie of the failure."

## Playwright vs. Cypress

| Concern                  | Playwright                                          | Cypress                                              |
|--------------------------|-----------------------------------------------------|------------------------------------------------------|
| Browser coverage         | Chromium, Firefox, WebKit (real patched builds)    | Chromium-family only until 2023; FF/WebKit added later via WebKit/wkhtml — historically single-engine |
| Multi-tab / multi-origin | Native — `context.newPage()`, `popup` events, cross-origin nav works | Single-tab by design; multi-tab is a known limitation (see Cypress issue #3103) |
| Runs in                  | Node.js — talks to the browser over CDP/Juggler/IPC | Runs *inside* the browser — test code is bundled with the app; same-origin sandbox |
| Parallelism              | Worker processes out of the box; `--workers=N`       | Requires Cypress Cloud for parallel runs; local runs are serial |
| Retry semantics          | Per-action and per-assertion auto-waiting; `retries` config | Command queue with retry-ability on `should` assertions; non-assertion commands do not retry |
| Network control          | `page.route()` to mock, modify, continue, abort     | `cy.intercept()` with similar semantics |
| API testing              | First-class `request` fixture, runs in Node         | `cy.request()` runs in browser subject to same-origin |
| Debugging UX             | Trace Viewer (PWA), UI Mode, `--debug`              | Time-travel UI in the Cypress App; very polished for live authoring |
| Test isolation           | One fresh context per test by default               | One browser per spec; tests share state unless `cy.session()` is used |
| Mobile                   | Real device emulation profiles (iPhone 15, Pixel 7) | Viewport-only; no touch event simulation |

The clearest "when to pick which": pick Playwright when you have multi-browser SLAs, multi-tab flows (oauth popups, payment redirects), or need to run thousands of specs in parallel under CI budget. Pick Cypress when developer ergonomics during authoring matters more than the above — Cypress's time-travel UI and "test runs next to your app" model are genuinely faster for greenfield teams iterating on a single browser.

## References

- [Playwright documentation](https://playwright.dev/docs/intro)
- [microsoft/playwright on GitHub](https://github.com/microsoft/playwright)
- [Microsoft announcement: Introducing Playwright](https://blogs.windows.com/windowsexperience/2020/01/23/introducing-playwright-reliable-cross-browser-testing-for-the-modern-web/)
- [Chrome DevTools Protocol viewer](https://chromedevtools.github.io/devtools-protocol/)
- [Trace Viewer documentation](https://playwright.dev/docs/trace-viewer)
- [Playwright test.extend fixtures](https://playwright.dev/docs/test-fixtures)
- [Playwright locators guide](https://playwright.dev/docs/locators)
