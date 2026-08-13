# End-to-End Testing

End-to-end (E2E) tests verify the entire application stack from the user's perspective. They simulate real user interactions — clicking buttons, filling forms, navigating pages — and verify the system behaves correctly across all layers: UI, API, database, and infrastructure.

## What Is E2E Testing?

```
┌─────────────────────────────────────────────┐
│  E2E Test                                   │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Browser  │─▶│ Frontend │─▶│  Backend  │  │
│  │ (user)   │  │  (React) │  │  (API)    │  │
│  └─────────┘  └──────────┘  └─────┬─────┘  │
│                                    │        │
│                              ┌─────▼─────┐  │
│                              │  Database  │  │
│                              └───────────┘  │
└─────────────────────────────────────────────┘
```

E2E tests are:
- **Slow** (seconds to minutes per test)
- **Brittle** (sensitive to UI changes)
- **Expensive** (require full environment)
- **Valuable** (catch integration issues other tests miss)

## Playwright

Playwright is Microsoft's modern E2E testing framework supporting Chromium, Firefox, and WebKit.

### Setup

```bash
npm init playwright@latest
# Choose: TypeScript, tests folder, install browsers
```

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'] } },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### Basic Tests

```typescript
// tests/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('user can log in with valid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email-input"]', 'alice@test.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="welcome-message"]'))
      .toHaveText('Welcome, Alice');
  });

  test('shows error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email-input"]', 'wrong@test.com');
    await page.fill('[data-testid="password-input"]', 'wrongpassword');
    await page.click('[data-testid="login-button"]');

    await expect(page.locator('[data-testid="error-message"]'))
      .toHaveText('Invalid email or password');
    await expect(page).toHaveURL('/login');
  });

  test('redirects to login when accessing protected page', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
```

### Advanced Playwright Features

```typescript
// Auto-waiting and assertions
test('search functionality', async ({ page }) => {
  await page.goto('/');

  // Playwright auto-waits for elements
  await page.fill('[data-testid="search"]', 'playwright');
  await page.press('[data-testid="search"]', 'Enter');

  // Wait for results to appear
  await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
  const results = page.locator('[data-testid="result-item"]');
  await expect(results).toHaveCount(10);
});

// API testing alongside UI
test('creates order via API and verifies in UI', async ({ page, request }) => {
  // Create order via API
  const response = await request.post('/api/orders', {
    data: { item: 'Widget', quantity: 5 },
  });
  const order = await response.json();

  // Verify it appears in UI
  await page.goto(`/orders/${order.id}`);
  await expect(page.locator('[data-testid="order-status"]'))
    .toHaveText('Pending');
});

// Visual comparison
test('homepage matches screenshot', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png', {
    maxDiffPixelRatio: 0.05,
  });
});

// Network interception
test('handles API failure gracefully', async ({ page }) => {
  await page.route('**/api/products', (route) =>
    route.fulfill({ status: 500, body: 'Server Error' })
  );

  await page.goto('/products');
  await expect(page.locator('[data-testid="error-banner"]'))
    .toHaveText('Failed to load products. Please try again.');
});
```

### Fixtures and Authentication

```typescript
// fixtures.ts
import { test as base } from '@playwright/test';

type Fixtures = {
  authenticatedPage: Page;
};

export const test = base.extend<Fixtures>({
  authenticatedPage: async ({ page, browser }, use) => {
    // Perform login
    await page.goto('/login');
    await page.fill('[data-testid="email"]', 'alice@test.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('/dashboard');

    await use(page);
  },
});

// Usage
test('user can view profile', async ({ authenticatedPage: page }) => {
  await page.goto('/profile');
  await expect(page.locator('h1')).toHaveText('My Profile');
});
```

## Cypress

Cypress is a popular E2E testing framework with a focus on developer experience.

### Setup

```bash
npm install cypress --save-dev
npx cypress open
```

```javascript
// cypress.config.js
const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
    retries: { runMode: 2, openMode: 0 },
  },
});
```

### Basic Tests

```javascript
// cypress/e2e/auth.cy.js
describe('Authentication', () => {
  beforeEach(() => {
    cy.visit('/login');
  });

  it('logs in with valid credentials', () => {
    cy.get('[data-testid="email-input"]')
      .type('alice@test.com');
    cy.get('[data-testid="password-input"]')
      .type('password123');
    cy.get('[data-testid="login-button"]')
      .click();

    cy.url().should('include', '/dashboard');
    cy.get('[data-testid="welcome-message"]')
      .should('contain', 'Welcome, Alice');
  });

  it('shows error for invalid credentials', () => {
    cy.get('[data-testid="email-input"]').type('wrong@test.com');
    cy.get('[data-testid="password-input"]').type('wrong');
    cy.get('[data-testid="login-button"]').click();

    cy.get('[data-testid="error-message"]')
      .should('be.visible')
      .and('contain', 'Invalid email or password');
  });
});
```

### Cypress Commands and Custom Methods

```javascript
// cypress/support/commands.js
Cypress.Commands.add('login', (email = 'alice@test.com', password = 'password123') => {
  cy.session([email, password], () => {
    cy.visit('/login');
    cy.get('[data-testid="email-input"]').type(email);
    cy.get('[data-testid="password-input"]').type(password);
    cy.get('[data-testid="login-button"]').click();
    cy.url().should('include', '/dashboard');
  });
});

Cypress.Commands.add('createOrder', (orderData) => {
  cy.request('POST', '/api/orders', orderData).then((response) => {
    expect(response.status).to.eq(201);
    return response.body;
  });
});

// Usage
describe('Orders', () => {
  beforeEach(() => {
    cy.login();
  });

  it('creates an order', () => {
    cy.visit('/orders/new');
    cy.get('[data-testid="item-input"]').type('Widget');
    cy.get('[data-testid="quantity-input"]').type('5');
    cy.get('[data-testid="submit-button"]').click();

    cy.get('[data-testid="order-confirmation"]')
      .should('be.visible');
  });
});
```

## Playwright vs Cypress

| Feature              | Playwright                    | Cypress                         |
|----------------------|-------------------------------|---------------------------------|
| **Browser support**  | Chromium, Firefox, WebKit     | Chromium, Firefox, WebKit       |
| **Multi-tab**        | ✅ Native                     | ❌ Workarounds needed           |
| **iFrames**          | ✅ Native                     | ⚠️ Limited                     |
| **API testing**      | ✅ Built-in                   | Via `cy.request()`              |
| **Speed**            | Faster (parallel by default)  | Slower (serial in single tab)   |
| **Debugging**        | Trace viewer, screenshots     | Time-travel, excellent UI       |
| **Learning curve**   | Moderate                      | Low                             |
| **Community**        | Growing fast                  | Large, established              |
| **Mobile testing**   | Device emulation              | Viewport only                   |

## Page Object Model (POM)

The Page Object Model encapsulates page interactions in reusable classes:

### Playwright POM

```typescript
// pages/LoginPage.ts
import { Page, Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.locator('[data-testid="email-input"]');
    this.passwordInput = page.locator('[data-testid="password-input"]');
    this.loginButton = page.locator('[data-testid="login-button"]');
    this.errorMessage = page.locator('[data-testid="error-message"]');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  async expectError(message: string) {
    await expect(this.errorMessage).toHaveText(message);
  }
}

// pages/DashboardPage.ts
export class DashboardPage {
  readonly page: Page;
  readonly welcomeMessage: Locator;
  readonly logoutButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.welcomeMessage = page.locator('[data-testid="welcome-message"]');
    this.logoutButton = page.locator('[data-testid="logout-button"]');
  }

  async expectWelcome(name: string) {
    await expect(this.welcomeMessage).toHaveText(`Welcome, ${name}`);
  }

  async logout() {
    await this.logoutButton.click();
  }
}

// tests/auth.spec.ts — clean test using POM
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';

test('successful login', async ({ page }) => {
  const loginPage = new LoginPage(page);
  const dashboardPage = new DashboardPage(page);

  await loginPage.goto();
  await loginPage.login('alice@test.com', 'password123');

  await expect(page).toHaveURL('/dashboard');
  await dashboardPage.expectWelcome('Alice');
});
```

### Cypress POM

```javascript
// cypress/pages/LoginPage.js
class LoginPage {
  visit() {
    cy.visit('/login');
  }

  fillEmail(email) {
    cy.get('[data-testid="email-input"]').clear().type(email);
  }

  fillPassword(password) {
    cy.get('[data-testid="password-input"]').clear().type(password);
  }

  submit() {
    cy.get('[data-testid="login-button"]').click();
  }

  login(email, password) {
    this.fillEmail(email);
    this.fillPassword(password);
    this.submit();
  }

  getError() {
    return cy.get('[data-testid="error-message"]');
  }
}

export default new LoginPage();

// Usage in tests
import loginPage from '../pages/LoginPage';

it('logs in successfully', () => {
  loginPage.visit();
  loginPage.login('alice@test.com', 'password123');
  cy.url().should('include', '/dashboard');
});
```

## Dealing with Flaky Tests

Flaky tests pass sometimes and fail other times — they're the #1 killer of E2E test trust.

### Common Causes

| Cause                    | Symptom                          | Fix                                    |
|--------------------------|----------------------------------|----------------------------------------|
| **Timing issues**        | Element not found intermittently | Use auto-wait, explicit waits          |
| **Race conditions**      | Test order matters               | Make tests independent                 |
| **Shared state**         | Tests interfere with each other  | Clean up data, use isolated accounts   |
| **Network variability**  | Timeouts in CI                   | Mock external services                 |
| **Dynamic content**      | Element text changes             | Use data-testid selectors              |
| **Animations**           | Element not in final position    | Disable animations in test env         |
| **Flaky infrastructure** | Occasional CI runner issues      | Retry on failure, investigate root cause |

### Solutions

```typescript
// 1. Use data-testid instead of CSS classes or XPath
// ❌ Flaky
await page.click('.btn-primary.large');
// ✅ Stable
await page.click('[data-testid="submit-order-button"]');

// 2. Use auto-waiting assertions (Playwright)
// ❌ Manual wait
await page.waitForTimeout(3000);
const text = await page.textContent('.status');
// ✅ Auto-waiting
await expect(page.locator('.status')).toHaveText('Complete');

// 3. Retry with backoff for network requests
test('loads data', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page.locator('[data-testid="data-table"]'))
    .toBeVisible({ timeout: 10000 });
});

// 4. Isolate test data
test.describe('Order tests', () => {
  let testUser;

  test.beforeEach(async ({ request }) => {
    // Create fresh user for each test
    const response = await request.post('/api/test/users', {
      data: { name: `test-user-${Date.now()}`, email: `test-${Date.now()}@test.com` },
    });
    testUser = await response.json();
  });

  test.afterEach(async ({ request }) => {
    await request.delete(`/api/test/users/${testUser.id}`);
  });
});

// 5. Disable animations in test environment
// In your CSS or test config:
// * { animation: none !important; transition: none !important; }
```

### Retry Strategy

```typescript
// playwright.config.ts
export default defineConfig({
  retries: process.env.CI ? 2 : 0,
  // Individual test retry
});

// Or per-test
test('sometimes flaky test', async ({ page }) => {
  test.retry(3); // Retry up to 3 times
  // ...
});
```

```javascript
// cypress.config.js
module.exports = defineConfig({
  e2e: {
    retries: { runMode: 2, openMode: 0 },
  },
});
```

## Testing Strategies for E2E

### Smoke Tests
Quick tests verifying critical paths work:

```typescript
test.describe('Smoke Tests', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
  });

  test('user can log in', async ({ page }) => {
    // Quick login flow
  });

  test('API is responsive', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.ok()).toBeTruthy();
  });
});
```

### Critical Path Tests
Test the most important user journeys:

```typescript
test.describe('Checkout Flow', () => {
  test('complete purchase journey', async ({ page }) => {
    // 1. Browse products
    await page.goto('/products');
    await page.click('[data-testid="product-widget"]');

    // 2. Add to cart
    await page.click('[data-testid="add-to-cart"]');
    await expect(page.locator('[data-testid="cart-count"]')).toHaveText('1');

    // 3. Go to checkout
    await page.click('[data-testid="cart-icon"]');
    await page.click('[data-testid="checkout-button"]');

    // 4. Fill shipping info
    await page.fill('[data-testid="address"]', '123 Main St');
    await page.fill('[data-testid="city"]', 'Springfield');
    await page.click('[data-testid="continue-to-payment"]');

    // 5. Fill payment
    await page.fill('[data-testid="card-number"]', '4242424242424242');
    await page.fill('[data-testid="card-expiry"]', '12/28');
    await page.fill('[data-testid="card-cvc"]', '123');
    await page.click('[data-testid="place-order"]');

    // 6. Verify order confirmation
    await expect(page.locator('[data-testid="order-confirmation"]'))
      .toBeVisible();
    await expect(page.locator('[data-testid="order-number"]'))
      .toMatch(/ORD-\d+/);
  });
});
```

## CI/CD Integration

```yaml
# GitHub Actions
name: E2E Tests
on: [pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run build
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## Best Practices

1. **Use data-testid attributes** — stable selectors that don't break with CSS changes
2. **Test critical paths** — don't try to E2E test everything
3. **Keep tests independent** — no shared state between tests
4. **Use the Page Object Model** — reusable page interactions
5. **Run in CI on every PR** — catch issues before merge
6. **Capture artifacts on failure** — screenshots, videos, traces
7. **Don't use E2E tests for business logic** — that's what unit tests are for
8. **Disable animations** — reduces flakiness
9. **Mock external services** — don't depend on third-party availability
10. **Set reasonable timeouts** — not too short (flaky), not too long (slow feedback)

## Summary

| Concept            | Key Takeaway                                    |
|--------------------|------------------------------------------------|
| **Purpose**        | Verify entire system from user perspective      |
| **Playwright**     | Modern, fast, multi-browser, auto-waiting       |
| **Cypress**        | Great DX, time-travel debugging, easy setup     |
| **Page Object Model** | Encapsulate page interactions for reuse     |
| **Flaky tests**    | Use data-testid, auto-waiting, isolated data    |
| **CI integration** | Run on PRs, capture artifacts on failure        |
