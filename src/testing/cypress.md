# Cypress

Cypress is a developer-first E2E and component testing framework open-sourced in 2017 by Cypress.io. Its pitch is "tests run in the browser, next to your app" — a deliberately different architectural bet from Selenium and Playwright, where a Node process drives the browser from the outside. That bet makes Cypress uniquely pleasant to author tests in, and uniquely constrained in what kinds of tests it can run.

## Architecture: Tests Run *Inside* the Browser

The single most important thing to understand about Cypress is that the test code is not running in Node. It is running inside the browser, in the same JavaScript realm as the application under test.

```
┌────────────────────────────────────────────────────────────────────┐
│                         Cypress Electron / Browser App             │
│                                                                     │
│   ┌────────────────┐       ┌──────────────────────────────────┐     │
│   │ Node backend   │       │  Browser window                  │     │
│   │ (the "server") │       │  ┌─────────────────────────┐     │     │
│   │                │       │  │  Cypress Runner iframe   │     │     │
│   │  • serves app  │       │  │  ┌───────────────────┐  │     │     │
│   │  • proxy / net  │◄─────┼──┤  │ spec.js iframe    │  │     │     │
│   │  • screenshots │       │  │  │ (test code lives  │  │     │     │
│   │  • videos      │       │  │  │  here, can reach  │  │     │     │
│   │  • reporters   │       │  │  │  into app window) │  │     │     │
│   └────────────────┘       │  │  └───────────────────┘  │     │     │
│                            │  │  ┌───────────────────┐  │     │     │
│                            │  │  │ App under test    │  │     │     │
│                            │  │  │ (your React app)  │  │     │     │
│                            │  │  └───────────────────┘  │     │     │
│                            │  └─────────────────────────┘     │     │
│                            └──────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

Three concrete consequences fall out of this:

1. **Same-origin policy:** Cypress runs in the same origin as the app, which means test code can directly call `window.yourApp.globalMethod()` and read app DOM nodes without serialization. It also means cross-origin navigation (`google.com` → `github.com`) breaks the test runner, because Cypress's runner iframe loses its parent reference. Cypress 12 added partial cross-origin support via `cy.origin()`, but the model is still bolted on, not native.

2. **No multi-tab:** because the runner iframe lives in a single window, Cypress cannot open a second tab. Popups (`window.open`) and OAuth redirects that open a new tab require workarounds like stubbing the popup or pinning to one tab. This is the single most-quoted Cypress limitation; see GitHub issue #3103, open since 2017.

3. **Single browser per spec file:** tests in one `.cy.js` file share a single browser instance, in series. True parallelism requires Cypress Cloud, which shards spec files across CI machines.

The Node "backend" exists mainly to act as a proxy: it intercepts all HTTP traffic from the app, lets you stub responses with `cy.intercept()`, takes screenshots and video on failure, and writes the test report to disk. The actual test logic never runs there.

## The Command Chain: `cy.get`, `cy.click`, `cy.should`

Cypress tests look declarative because every `cy.*` call returns a `Chainable` and pushes the command onto an internal queue. The command does not execute immediately — it executes only when Cypress gets to that step of the queue.

```javascript
describe('Checkout', () => {
  beforeEach(() => cy.visit('/cart'));

  it('applies a discount code', () => {
    cy.get('[data-testid="discount-input"]').as('code');
    cy.get('@code').type('SAVE10');
    cy.get('[data-testid="apply-discount"]').click();
    cy.get('[data-testid="total"]')
      .should('contain', '$90.00')        // assertion command enqueued
      .and('be.visible');                  // chained assertion
  });
});
```

Each line above enqueues a command. The actual execution order is `visit → get(discount-input) → alias → get(alias) → type → get(apply-discount) → click → get(total) → should → should`. Because commands are queued, you cannot reliably do this:

```javascript
// ❌ Will not work as you might expect
const total = cy.get('[data-testid="total"]').invoke('text');
// `total` here is a Chainable, NOT the text. Use cy.wrap/then.
expect(Number(total)).to.be.greaterThan(0); // runs before the get resolves
```

The idiom instead is `.then()`:

```javascript
cy.get('[data-testid="total"]')
  .invoke('text')
  .then((text) => {
    const value = Number(text.replace(/[^0-9.]/g, ''));
    expect(value).to.be.greaterThan(0);
  });
```

This queue-based model is what enables **time-travel debugging**: the Cypress App UI renders every enqueued command as a snapshot, and hovering over one replays the DOM as it was at that moment.

## Retry-Ability

Cypress has two retry mechanisms:

1. **Query retry-ability.** When `cy.get()` is followed by `.should()`, Cypress re-runs *both* commands together until the assertion passes or 4 s (default) elapses. This is why this works:

```javascript
// App will set the badge to '3' 800ms after page load
cy.get('[data-testid="cart-count"]').should('have.text', '3');
// Cypress polls every ~50ms: get → check text → repeat
```

2. **Non-query commands do NOT retry.** `cy.click()` runs once. If the element is detached from the DOM mid-click (common in React 18's concurrent rendering), the click throws `cy.click() failed because the element is detached from the DOM`. The fix is to chain `.should('be.visible').and('not.be.disabled')` *before* the click, so the precondition retries; the click itself runs once on the stable element.

Contrast with Playwright, where *every* action has an implicit actionability wait baked in. Cypress's model is opt-in via `should`, Playwright's is opt-out. Both work — they just shift where the cognitive load sits.

## Component Testing Mode

Cypress Component Testing (stable since v12) runs your components in isolation, mounted in a real browser, with the same Cypress runner you already know. It competes directly with Vitest + Testing Library.

```javascript
// LoginButton.cy.jsx
import { mount } from 'cypress/react18';
import { LoginButton } from './LoginButton';

describe('<LoginButton />', () => {
  it('fires onClick with form payload', () => {
    const spy = cy.spy().as('onClick');
    mount(<LoginButton onClick={spy} loading={false} />);
    cy.get('button').should('contain', 'Sign in').click();
    cy.get('@onClick').should('have.been.calledOnce');
  });

  it('renders spinner while loading', () => {
    mount(<LoginButton loading={true} />);
    cy.get('[data-testid="spinner"]').should('be.visible');
    cy.get('button').should('be.disabled');
  });
});
```

The key distinction vs. E2E mode: there is no `cy.visit()`. The component is mounted in `mount()` directly into a clean slate, no routing, no full app boot. This makes component tests fast (single-digit seconds per file) and isolates failures to a single component's contract.

In modern stack terms, Cypress Component Testing lives in the same tier as React Testing Library — its main value is that one tool can do *both* component and E2E testing, which simplifies the developer mental model.

## Cypress Cloud: Parallelization and Recording

Cypress Cloud is the commercial product layered on top of the open-source runner. It does three things the OSS version cannot:

1. **Parallelization.** On a local run, Cypress is serial: spec by spec, one after the other. In CI, you can run `cypress run --parallel --record --key=...` across N CI containers. The Cloud coordinator hands each container one spec file at a time, balances slow vs. fast specs across runners, and aggregates the results. The result is the only way to run a 200-spec Cypress suite in under 5 minutes — local serial runs of that suite routinely take 40+ minutes.

2. **Recording of runs.** Every run is uploaded: videos, screenshots, console logs, network stubs, DOM snapshots. This means a failed run from last Tuesday's CI is replayable in the cloud dashboard, with the same time-travel UI as a local run. OSS Cypress deletes artifacts after the run finishes.

3. **Flake detection.** Cloud tracks per-test failure rates over time. A test that fails 1-in-20 runs gets flagged as flaky, with a histogram of which CI workers and which app commits triggered it.

The model is pay-per-test-run, which makes it expensive for large teams; many orgs replace it with Playwright + open-source HTML reports once suites exceed a few hundred tests.

```yaml
# Parallelized CI run with Cypress Cloud
- name: Run Cypress
  run: npx cypress run --record --parallel --key ${{ secrets.CYPRESS_KEY }}
  env:
    CYPRESS_PROJECT_ID: ${{ secrets.CYPRESS_PROJECT_ID }}
```

## Cypress vs. Playwright vs. Selenium

| Dimension               | Cypress                                 | Playwright                              | Selenium WebDriver                      |
|-------------------------|-----------------------------------------|-----------------------------------------|-----------------------------------------|
| Where tests run          | Inside browser, same origin as app     | Node.js, drives browser via CDP/Juggler | Node/Java/Python/Ruby, drives via W3C WebDriver HTTP server |
| Browser support          | Chromium; FF/WebKit via Electron       | Chromium, Firefox, WebKit (patched)     | Real Chrome, Firefox, Safari, Edge, IE |
| Multi-tab / cross-origin | No (partial via `cy.origin()`)          | Yes, native                             | Yes, native (WebDriver `switchTo().window()`) |
| Parallelism              | Requires Cypress Cloud                  | Built-in worker pool                    | Requires Selenium Grid or Selenoid       |
| Speed per spec           | Slower (single tab, serial by default)  | Faster (parallel, multi-context)        | Slowest (HTTP hop per command)          |
| Debugging UX             | Excellent time-travel UI                 | Trace Viewer PWA                         | Limited; relies on screenshots/videos  |
| Language bindings        | JS/TS only                              | JS/TS, Python, Java, .NET               | Every major language                     |
| Cloud offering           | Cypress Cloud (paid, recording + parallel) | Microsoft Playwright (free, no native recording cloud) | BrowserStack, Sauce Labs, Selenium Grid |
| Mobile testing           | Viewport only                           | Real device profiles                     | Appium (mobile only)                     |

The quick heuristic: pick Selenium when you need legacy browser coverage (IE, old Safari), native mobile, or a polyglot org that tests in Java. Pick Cypress for greenfield web teams who value authoring speed. Pick Playwright for new projects that need parallel CI, multi-browser, or multi-tab flows.

## When Cypress Shines, When It Hurts

**Shines:** A team writing a new React/Next.js SaaS app, mostly single-origin, mostly single-tab, who want to test drive components in isolation and run a handful of E2E flows in CI. Cypress Cloud's parallel shard makes a 50-spec suite finish in 90 seconds across 4 CI runners, and the time-travel UI is unmatched for diagnosing why a test flaked.

**Hurts:** A fintech app where the OAuth flow opens IDP in a new tab and the test must interact with it. A SaaS that supports IE11 (Cypress dropped IE in 2020). A monorepo where the same suite runs across Chrome, Firefox, and Safari per the support matrix — Cypress's WebKit support is newer and rougher than Playwright's patched WebKit. A team running 1000+ specs who get a $4K/month Cypress Cloud bill.

## References

- [Cypress documentation](https://docs.cypress.io/)
- [cypress-io/cypress on GitHub](https://github.com/cypress-io/cypress)
- [Real World Testing with Cypress (book)](https://www.cypress.io/real-world-testing)
- [Cypress Architecture: How Cypress Works under the Hood](https://docs.cypress.io/app/get-started/why-cypress)
- [Cypress Component Testing](https://docs.cypress.io/app/get-started/component-testing)
- [Cypress Cloud: parallelization](https://docs.cypress.io/app/cloud/introduction)
- [Cypress issue #3103 — multi-tab support](https://github.com/cypress-io/cypress/issues/3103)
