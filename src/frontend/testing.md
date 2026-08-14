# Frontend Testing

A well-structured testing strategy is essential for maintainable frontend applications. This guide covers the testing pyramid, tools, and patterns that come up in interviews.

## The Testing Pyramid

```
        ╱  E2E  ╲           ← Few, slow, high confidence
       ╱──────────╲         ← Playwright, Cypress
      ╱  Integration ╲       ← Component testing
     ╱────────────────╲     ← React Testing Library
    ╱    Unit Tests     ╲   ← Many, fast, focused
   ╱──────────────────────╲ ← Vitest, Jest
```

- **Unit tests** — test individual functions, hooks, or utilities in isolation
- **Component tests** — test components with their UI and logic (but mocked dependencies)
- **E2E tests** — test the entire application in a real browser from the user's perspective

## Unit Testing with Vitest / Jest

Vitest is the modern replacement for Jest — faster (native ESM, Vite-powered), and compatible with Jest's API.

```javascript
// utils/format.js
export function formatDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  }).format(new Date(date));
}

export function truncate(str, maxLength = 50) {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

// utils/format.test.js
import { describe, it, expect } from 'vitest';
import { formatDate, truncate } from './format';

describe('formatDate', () => {
  it('formats a date string', () => {
    expect(formatDate('2025-01-15')).toBe('Jan 15, 2025');
  });

  it('returns "Invalid Date" for invalid input', () => {
    expect(formatDate('not-a-date')).toBe('Invalid Date');
  });
});

describe('truncate', () => {
  it('returns the string unchanged if shorter than maxLength', () => {
    expect(truncate('Hello', 10)).toBe('Hello');
  });

  it('truncates long strings and adds ellipsis', () => {
    expect(truncate('A very long string that exceeds the limit', 20))
      .toBe('A very long string ...');
  });

  it('uses default maxLength of 50', () => {
    const short = 'short';
    expect(truncate(short)).toBe(short);
  });
});
```

### Testing Custom Hooks

```javascript
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

it('increments and decrements', () => {
  const { result } = renderHook(() => useCounter());

  expect(result.current.count).toBe(0);

  act(() => result.current.increment());
  expect(result.current.count).toBe(1);

  act(() => result.current.decrement());
  expect(result.current.count).toBe(0);
});
```

## Component Testing with React Testing Library

React Testing Library (RTL) tests components the way users interact with them — by finding elements via accessible roles, labels, and text content, not by CSS selectors or component internals.

```javascript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginForm from './LoginForm';

// ❌ Bad — testing implementation details
test('calls onChange when input changes', () => {
  const onChange = vi.fn();
  render(<LoginForm onChange={onChange} />);
  fireEvent.change(screen.getByTestId('email-input'), {
    target: { value: 'john@example.com' }
  });
  expect(onChange).toHaveBeenCalled();
});

// ✅ Good — testing user behavior
test('submits the form with email and password', async () => {
  const onSubmit = vi.fn();
  render(<LoginForm onSubmit={onSubmit} />);

  // Find by accessible label
  await userEvent.type(screen.getByLabelText('Email'), 'john@example.com');
  await userEvent.type(screen.getByLabelText('Password'), 'secret123');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

  expect(onSubmit).toHaveBeenCalledWith({
    email: 'john@example.com',
    password: 'secret123',
  });
});

// ✅ Good — testing error state
test('shows error message for invalid email', async () => {
  render(<LoginForm />);

  await userEvent.type(screen.getByLabelText('Email'), 'invalid-email');
  await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

  expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
});
```

**Key RTL query methods (ordered by preference):**

| Query | Finds by | Use when... |
|-------|---------|------------|
| `getByRole` | ARIA role | Always prefer — simulates real usage |
| `getByLabelText` | Label text | Form inputs |
| `getByPlaceholderText` | Placeholder | Secondary option for inputs |
| `getByText` | Text content | Headings, paragraphs, buttons |
| `getByTestId` | `data-testid` | Last resort — when no accessible label exists |

## End-to-End Testing with Playwright

Playwright tests run in real browsers, simulating real user interactions:

```javascript
import { test, expect } from '@playwright/test';

test('user can log in and see dashboard', async ({ page }) => {
  await page.goto('/login');

  await page.getByLabel('Email').fill('john@example.com');
  await page.getByLabel('Password').fill('password123');
  await page.getByRole('button', { name: 'Sign In' }).click();

  // Wait for navigation and assertion
  await expect(page).toHaveURL('/dashboard');
  await expect(page.getByText('Welcome, John')).toBeVisible();
});

test('search filters products', async ({ page }) => {
  await page.goto('/products');

  await page.getByPlaceholder('Search products...').fill('laptop');
  await page.getByRole('button', { name: 'Search' }).click();

  const results = page.getByRole('listitem');
  await expect(results).toHaveCount(3);
  await expect(results.first()).toContainText('MacBook');
});
```

**Playwright advantages:** Multi-browser (Chromium, Firefox, WebKit), auto-wait for elements, network interception, visual comparisons, parallel execution.

## Accessibility Testing

```javascript
// Automated a11y testing with axe-core + Vitest
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

test('has no accessibility violations', async () => {
  const { container } = render(<Navigation />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Tools:** axe-core (automated), Lighthouse (CI integration), keyboard testing (manual), screen reader testing (manual).

## Visual Regression Testing

Detect unintended visual changes by comparing screenshots:

```javascript
// Playwright visual comparisons
test('homepage matches snapshot', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png');
});

// Compare specific element
test('card component matches snapshot', async ({ page }) => {
  await page.goto('/products/1');
  await expect(page.getByTestId('product-card')).toHaveScreenshot('card.png');
});
```

**Tools:** Playwright screenshots, Percy (BrowserStack), Chromatic (Storybook), BackstopJS.

## Mocking Strategies

```javascript
import { vi } from 'vitest';

// Mock a module
vi.mock('./api', () => ({
  fetchUsers: vi.fn().mockResolvedValue([{ id: 1, name: 'John' }]),
}));

// Mock a function temporarily
const original = window.fetch;
window.fetch = vi.fn().mockResolvedValue({
  json: () => Promise.resolve({ data: 'mocked' }),
});

// Mock timers
vi.useFakeTimers();
// ... code that uses setTimeout
vi.advanceTimersByTime(1000);
vi.useRealTimers();

// Spy on a method
const spy = vi.fn();
render(<Button onClick={spy} />);
await userEvent.click(screen.getByRole('button'));
expect(spy).toHaveBeenCalledTimes(1);
```

## Test Organization

```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── Button.test.tsx        ← co-located tests
│   └── LoginForm/
│       ├── LoginForm.tsx
│       └── LoginForm.test.tsx
├── hooks/
│   ├── useCounter.ts
│   └── useCounter.test.ts
├── utils/
│   ├── format.ts
│   └── format.test.ts
└── e2e/
    ├── auth.spec.ts                ← end-to-end tests (separate folder)
    └── products.spec.ts
```

**Naming convention:** `describe('ComponentName', () => { it('should do X when Y', ...) })` — describe what it should do, not how.

## Interview Questions

**Q: What's the difference between unit tests, integration tests, and E2E tests?**
A: Unit tests verify individual functions/components in isolation (fast, focused). Integration tests verify that components work together correctly. E2E tests simulate real user flows in a browser (slow, high confidence). Follow the testing pyramid — many unit tests, some integration, few E2E.

**Q: Why does React Testing Library recommend testing by role/label rather than by test ID?**
A: Testing by accessible attributes (role, label, text) ensures components work for all users — including screen reader users. If a button can't be found by its role, a screen reader user can't find it either. `data-testid` is a last resort for elements without accessible identifiers.

**Q: When would you mock an API call vs use the real API in tests?**
A: Mock API calls in unit and component tests for speed, determinism, and isolation. Use real APIs (or a test server) in E2E tests to catch integration issues. Avoid over-mocking — mock at the network level (MSW) rather than internal modules when possible, to test real integration paths.

**Q: What is visual regression testing?**
A: Visual regression testing captures screenshots of UI components and compares them against a baseline. If the rendered output changes unexpectedly (layout shift, color change), the test fails. Tools: Playwright screenshots, Percy, Chromatic. Catches CSS/layout bugs that functional tests miss.

## References

- [Testing Library Documentation](https://testing-library.com/docs/)
- [Vitest Documentation](https://vitest.dev/)
- [Playwright Documentation](https://playwright.dev/)
- [Kent C. Dodds — Testing JavaScript](https://testingjavascript.com/)
