# Code Splitting

Code splitting breaks a large JavaScript bundle into smaller chunks that are loaded on demand. This reduces initial bundle size, improves Time to Interactive (TTI), and ensures users only download the code they actually need.

## Why Code Splitting Matters

Shipping a single large bundle forces users to download and parse all JavaScript upfront, including code for routes and features they may never visit. Code splitting addresses this by creating **lazy-loaded chunks** loaded at runtime.

| Metric | Without Splitting | With Splitting |
|---|---|---|
| Initial JS size | 500 KB (all routes) | 120 KB (entry + current route) |
| TTI | Slow (parse all JS) | Fast (parse only needed code) |
| Cache hit rate | Low (any change invalidates all) | High (unchanged chunks stay cached) |

## Dynamic Import

The `import()` syntax is the foundation of code splitting — it returns a Promise and tells bundlers to create a separate chunk:

```javascript
// Dynamic import — creates a separate chunk
button.addEventListener('click', async () => {
  const { Chart } = await import('./chart-module.js');
  const chart = new Chart(container);
});
```

```javascript
// React lazy loading with Suspense
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./Dashboard'));
const Settings = lazy(() => import('./Settings'));

function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/settings" component={Settings} />
    </Suspense>
  );
}
```

## Splitting Strategies

### Route-Based Splitting

Split at route boundaries — each page becomes a chunk. This is the most common and impactful strategy since users only load the page they visit.

### Component-Based Splitting

Split heavy components within a page (e.g., a rich text editor, a 3D viewer) that are conditionally rendered or below the fold.

### Library Splitting

Separate large third-party libraries (lodash, moment, chart.js) into vendor chunks with longer cache TTLs. Webpack's `SplitChunksPlugin` handles this:

```javascript
// webpack.config.js
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all'
        }
      }
    }
  }
};
```

## Bundle Analysis

Before optimizing, measure. Use these tools to identify large chunks and opportunities:

| Tool | Output | Best For |
|---|---|---|
| `webpack-bundle-analyzer` | Interactive treemap | Identifying large dependencies |
| `source-map-explorer` | Source-level size breakdown | Finding which code contributes most |
| `bundlesize` | CI check for size thresholds | Preventing bundle regression |
| Lighthouse | Performance score with suggestions | Overall load performance |

```javascript
// webpack-bundle-analyzer
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer')
  .BundleAnalyzerPlugin;

module.exports = {
  plugins: [new BundleAnalyzerPlugin()]
};
```

## Prefetching and Preloading

Complement code splitting with resource hints:

```javascript
// Prefetch: low priority, loads for likely next navigation
import(/* webpackPrefetch: true */ './SettingsPage');

// Preload: high priority, loads for current page
import(/* webpackPreload: true */ './HeroChart');
```

## Interview Questions

**Q1: What is code splitting and why is it important?**
A: Code splitting divides a JavaScript bundle into smaller chunks loaded on demand. It reduces the initial payload, improves TTI and FCP, and increases cache efficiency by keeping stable vendor chunks cached while only app code changes.

**Q2: What is the difference between route-based and component-based splitting?**
A: Route-based splitting creates one chunk per route/page — users load only the current page's code. Component-based splitting extracts heavy components (editors, charts) within a page that are conditionally rendered. Route-based is the default starting point; component-based is for further optimization.

**Q3: How does dynamic `import()` differ from static `import`?**
A: Static `import` is resolved at build time and bundles the module eagerly. Dynamic `import()` is resolved at runtime, returns a Promise, and tells the bundler to create a separate chunk. This enables lazy loading — code is only fetched when the import is executed.

**Q4: What is the vendor chunk pattern?**
A: Third-party libraries change less frequently than application code. Extracting them into a separate `vendors` chunk means that when you deploy app changes, users don't re-download the unchanged libraries. Webpack's `SplitChunksPlugin` with a `node_modules` regex test automates this.

## Cross-References

- [Browser Event Loop](browser-event-loop.md) — How async chunk loading fits the event loop
- [Browser Rendering](browser-rendering.md) — Impact of JS parsing on rendering
- [HTTP Fundamentals](http-fundamentals.md) — Caching, ETags, and chunk requests
- [API Communication](api-communication.md) — Lazy-loading API clients

## References

- [Code Splitting — webpack](https://webpack.js.org/guides/code-splitting/)
- [Lazy Loading — React Docs](https://react.dev/reference/react/lazy)
- [webpack-bundle-analyzer](https://github.com/webpack-contrib/webpack-bundle-analyzer)
