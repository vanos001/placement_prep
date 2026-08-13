# Vue and Angular

## Overview

React (see [React](../react/README.md)) isn't the only major frontend framework. **Vue** (Evan You, 2014) is the "progressive framework" — gentle learning curve, single-file components, incremental adoption. **Angular** (Google, 2016 rewrite of AngularJS) is the TypeScript-first, opinionated, batteries-included framework for large enterprise apps. Both are mature production choices, and comparing them (with React) is a common frontend interview topic.

## Vue 3

### Core ideas

- **Reactivity**: Vue tracks reactive state and updates the DOM precisely when dependencies change (fine-grained, no manual `setState`).
- **Single-File Components (SFCs)**: template + script + scoped styles in one `.vue` file.
- **Composition API** (Vue 3): logic organized by feature via `ref`, `reactive`, `computed`, `watch` — better than the old Options API for complex components and TypeScript.

```vue
<script setup>
import { ref, computed } from 'vue'

const count = ref(0)
const doubled = computed(() => count.value * 2)
</script>

<template>
  <button @click="count++">count is {{ count }} (doubled: {{ doubled }})</button>
</template>
```

### Ecosystem

- **Nuxt** — the Vue meta-framework (like Next.js for React): SSR/SSG, file-based routing.
- **Pinia** — official state management (replaces Vuex).
- **Vue Router** — routing.
- **Vite** — the default build tool (created by Vue's author, now framework-agnostic).

### Strengths

- Gentle learning curve (HTML/CSS/JS plus a small reactivity model)
- **Progressive adoption** — add Vue to existing pages incrementally
- Small bundle (~35 KB gzipped core)
- Excellent TypeScript with the Composition API

## Angular

### Core ideas

- **TypeScript-first by default** — the entire toolchain assumes typed code.
- **Components + templates** with dependency injection, services, and modules (standalone components since v14+).
- **RxJS** — reactive streams as the async backbone.
- **Signals** (v16+, mature in v17–20): fine-grained reactivity that modernized Angular's change detection (20–30% faster updates in update-heavy scenarios); zoneless operation incoming.

```typescript
import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-counter',
  template: `
    <button (click)="count.set(count() + 1)">
      count is {{ count() }}
    </button>
  `,
  standalone: true,
})
export class CounterComponent {
  count = signal(0);
}
```

### Ecosystem

- **Angular CLI** — scaffolding, build, test, deploy in one tool.
- **Angular Universal** — SSR.
- **RxJS + NgRx** — reactive state management.
- **AOT compilation** — templates compiled at build time for runtime performance.

### Strengths

- **Opinionated structure** — consistency across large, multi-team codebases (enterprise/regulated industries)
- Comprehensive tooling out of the box (CLI, testing, forms, HTTP, routing)
- Strong TypeScript discipline

## Vue vs Angular vs React (quick comparison)

| Dimension | Vue | Angular | React |
|---|---|---|---|
| Creator / backing | Evan You / community | Google | Meta |
| TypeScript | Excellent (Composition API) | **First-class (default)** | Good (community tooling) |
| Learning curve | Gentle | Steep | Moderate |
| Bundle size (gzipped) | ~35 KB | ~62 KB | ~45 KB |
| Reactivity | Fine-grained (ref/computed) | Signals (v16+) | Re-render + reconciliation |
| Structure | Flexible / progressive | Opinionated / full framework | Flexible (library) |
| Meta-framework | **Nuxt** | Angular Universal | **Next.js** |
| Best for | Mid-size teams, gradual adoption, DX | Enterprise, large multi-team apps | Largest ecosystem, flexible projects |

| Framework | Choose when |
|---|---|
| **Vue** | You want React-like flexibility with a gentler curve; incremental adoption; small bundles |
| **Angular** | Enterprise consistency, TypeScript-first discipline, comprehensive built-in tooling |
| **React** | Largest ecosystem/hiring pool, most flexible, RSC/Next.js ecosystem |

**Performance is rarely the deciding factor** — all three are production-grade; team skills, project scale, and hiring pool dominate.

## Interview Questions

### Q: Vue vs Angular — how would you choose?

Vue for gradual adoption, a gentler learning curve, smaller bundles, and teams wanting React-like flexibility with less boilerplate. Angular for large enterprise codebases needing enforced structure, TypeScript-first discipline, and comprehensive out-of-the-box tooling (CLI, DI, RxJS, testing). Neither is objectively better — fit to team and project.

### Q: What is the Composition API in Vue?

The Composition API (Vue 3) organizes component logic by **feature** using `ref`/`reactive`/`computed`/`watch` inside a `setup` block, instead of splitting logic across Options API fields (`data`, `methods`, `computed`). It improves code reuse (composables), type inference with TypeScript, and maintainability of complex components.

### Q: What are Angular Signals and why do they matter?

Signals are Angular's fine-grained reactivity primitives (v16+, mature in v17+): a `signal<T>()` holds state, `computed()` derives values, and change detection updates only what depends on a signal — instead of zone-based checks of the whole tree. This delivers faster updates and enables zoneless operation, closing the performance gap with Vue/React's fine-grained reactivity.

### Q: How does Vue's reactivity differ from React's re-rendering?

Vue tracks reactive dependencies at the fine-grained level: when a `ref` changes, only the components/effects that read it re-run — no full tree re-render. React re-renders the component (and children by default) whenever state changes, then diffs the virtual DOM. Vue's model is more surgical; React's is simpler to reason about but needs memoization (memo/useMemo — now automated by React Compiler).

### Q: When would you pick Vue over React?

When you want progressive adoption (drop Vue into an existing page), a gentler learning curve for mixed-skill teams, smaller bundle size, or you prefer single-file components with scoped styles. React wins on ecosystem size, hiring pool, and framework choices like Next.js. Both are excellent; the tie-breakers are team and project context.

## References

- Vue 3 documentation — https://vuejs.org/
- Nuxt — https://nuxt.com/
- Angular documentation — https://angular.dev/
- Angular Signals guide — https://angular.dev/guide/signals
- State of JS survey (framework usage trends) — https://stateofjs.com/

## Related Topics

- [React](../react/README.md) — the third major framework
- [Next.js](../nextjs/README.md) — React's meta-framework (vs Nuxt)
- [TypeScript](../../languages/typescript/README.md) — the language both use well
- [JavaScript Overview](../../languages/javascript/README.md) — the shared foundation
- [V8 Engine](../../languages/javascript/v8.md) — how the browser runs them
