# Svelte

Svelte is an open-source JavaScript framework for building user interfaces, developed by Rich Harris (New York Times) since 2016. Unlike React or Vue, Svelte is a compiler — it transforms `.svelte` files into vanilla JavaScript that directly manipulates the DOM, with no virtual DOM and no runtime framework overhead. This page covers the compilation model, the reactivity system, the stores abstraction, and the comparison to React.

## The Compilation Model

A `.svelte` file:

```svelte
<script>
  let count = 0;
  
  function increment() {
    count += 1;
  }
</script>

<button on:click={increment}>
  Clicked {count} {count === 1 ? 'time' : 'times'}
</button>
```

Compiles to (simplified):

```js
// Generated JS
function create_fragment(ctx) {
  let button;
  let t0;
  let t1;
  let t2;
  
  return {
    c() {
      button = element('button');
      t0 = text('Clicked ');
      t1 = text(/* count */ ctx[0]);
      t2 = text(/* pluralize */ ctx[0] === 1 ? 'time' : 'times');
    },
    m(target, anchor) {
      insert(target, button, anchor);
      append(button, t0);
      append(button, t1);
      append(button, t2);
    },
    p(ctx, [dirty]) {
      if (dirty & /*count*/) {
        setData(t1, /* count */ ctx[0]);
        setData(t2, /* pluralize */ ctx[0] === 1 ? 'time' : 'times');
      }
    },
    d(detaching) {
      if (detaching) detach(button);
    },
  };
}

function instance($$self, $$props, $$invalidate) {
  let count = 0;
  
  function increment() {
    $$invalidate(0, count += 1);
  }
  
  return [count, increment];
}

class App extends SvelteComponent {
  constructor(options) {
    super();
    init(this, options, instance, create_fragment, safe_not_equal, {});
  }
}

export default App;
```

The compiled output:
- Has no virtual DOM diffing.
- Has direct DOM manipulation (setData, insert, etc.).
- Tracks dependencies statically (the `dirty` bitmask).
- Updates only what changed.

## The Reactivity Model

Svelte's reactivity is based on **assignments**. When a top-level `let` variable is assigned, Svelte schedules a re-render:

```svelte
<script>
  let count = 0;
  
  function increment() {
    count += 1;  // ← assignment triggers re-render
  }
  
  // Reactive declaration: recomputes when count changes
  $: doubled = count * 2;
  
  // Reactive statement: runs when count changes
  $: console.log('count is', count);
</script>
```

The `$:` syntax (a JavaScript label) is Svelte's special syntax for reactive declarations. The compiler analyzes the dependencies and generates the appropriate update logic.

For complex reactive state, use stores (see below).

## Stores

For state that's shared across components, Svelte has "stores":

```js
// stores.js
import { writable } from 'svelte/store';

export const count = writable(0);
```

```svelte
<!-- Component.svelte -->
<script>
  import { count } from './stores.js';
  
  function increment() {
    count.update(n => n + 1);
  }
</script>

<button on:click={increment}>
  Count: {$count}
</button>
```

The `$count` syntax auto-subscribes to the store and unsubscribes on component destroy. Stores can be:
- **writable**: read-write.
- **readable**: read-only (e.g., current time, browser online status).
- **derived**: derived from other stores.

## Components and Props

```svelte
<!-- Child.svelte -->
<script>
  export let name;  // declare a prop
  export let count = 0;  // prop with default
</script>

<h1>Hello, {name}!</h1>
<p>Count: {count}</p>
```

```svelte
<!-- Parent.svelte -->
<script>
  import Child from './Child.svelte';
</script>

<Child name="Alice" count={42} />
```

Props are declared with `export let`. Default values are supported. Svelte's compiler checks prop types statically where possible.

## Lifecycle

```svelte
<script>
  import { onMount, onDestroy, beforeUpdate, afterUpdate, tick } from 'svelte';
  
  onMount(() => {
    console.log('Component mounted');
    return () => console.log('Cleanup on unmount');
  });
  
  onDestroy(() => console.log('Component destroyed'));
  
  beforeUpdate(() => console.log('Before DOM update'));
  afterUpdate(() => console.log('After DOM update'));
</script>
```

`onMount` runs once after the first render; `onDestroy` runs before the component is removed; `beforeUpdate` and `afterUpdate` run on each re-render.

## Transitions and Animations

Svelte has built-in transitions:

```svelte
<script>
  import { fade, fly, slide } from 'svelte/transition';
  
  let visible = true;
</script>

<label>
  <input type="checkbox" bind:checked={visible}>
  Show
</label>

{#if visible}
  <p transition:fade={{ duration: 500 }}>Hello!</p>
{/if}
```

Transitions are CSS-based (fast) and declarative. Svelte also has animations (e.g., `flip` for list reordering) and `tweened`/`spring` stores for value animations.

## Production Performance

Svelte's published performance vs. React:
- Initial render (1000 elements): Svelte ~5 ms; React ~50 ms.
- Re-render: Svelte ~1 ms; React ~5 ms (with memo).
- Bundle size: Svelte ~5 KB (Hello World); React ~40 KB.
- Memory: Svelte ~1 MB; React ~10 MB.

The "no runtime" model gives Svelte much smaller bundles and faster initial loads. For mobile/edge deployments, this is significant.

## Production Use Cases

### Static Site Generation (SvelteKit)

SvelteKit (the official app framework) supports SSR, SSG, and SPA. A typical site generates HTML at build time; the client-side JS hydrates for interactivity.

```svelte
<!-- +page.svelte -->
<script>
  export let data;
</script>

<h1>{data.title}</h1>
<p>{data.content}</p>
```

```js
// +page.js (load function)
export async function load({ fetch }) {
  const res = await fetch('/api/posts/1');
  return { data: await res.json() };
}
```

### Real-Time Dashboards

Svelte's reactivity is ideal for dashboards that update frequently (e.g., stock prices, server metrics).

### Embedded UIs

Svelte's small bundle (5 KB) is ideal for embedded contexts where React's 40 KB is too large.

## Common Pitfalls

1. **Forgetting that reactive assignments must be top-level.** Inside functions or blocks, assignments don't trigger reactivity unless explicitly invalidated.

2. **Forgetting that `$:` syntax requires specific syntax.** A reactive declaration must use `$:` (a label), not a normal variable. The compiler is strict about this.

3. **Forgetting that stores require subscription.** A `$store` syntax auto-subscribes; but outside components, you must `store.subscribe(callback)`.

4. **Forgetting that compiled Svelte has its own conventions.** Tooling (linters, type checkers) may not understand `.svelte` files. Use the official Svelte tooling (svelte-check, svelte-preprocess).

5. **Forgetting that Svelte's compiler version matters.** Different Svelte versions have slightly different syntax (e.g., `slot` vs. `let:` for slots). Pin the version in package.json.

6. **Forgetting that Svelte's stores are global.** A module-level store is shared across all instances. For per-instance state, use `writable` inside the component.

## Comparison to React and Vue

| Aspect | Svelte | React | Vue |
|--------|--------|-------|------|
| Origin | Rich Harris 2016 | Facebook 2013 | Evan You 2014 |
| Model | Compiler | Virtual DOM | Virtual DOM |
| Bundle size | ~5 KB | ~40 KB | ~30 KB |
| Initial render | ~5 ms | ~50 ms | ~20 ms |
| Reactivity | Assignment-based | Hooks (explicit) | Composition API |
| Ecosystem | Growing | Largest | Large |
| Best for | Performance, simplicity | Large apps | Easy migration |

Svelte wins on performance and bundle size; React on ecosystem; Vue on ease of learning.

## References

- [Svelte documentation](https://svelte.dev/docs)
- [Svelte Tutorial](https://svelte.dev/tutorial)
- Rich Harris, "[Rethinking reactivity](https://www.youtube.com/watch?v=AdNJ3lTfpM8)" (YGLF 2019)
- [SvelteKit documentation](https://kit.svelte.dev/docs)
- [Svelte source code](https://github.com/sveltejs/svelte)
- [Svelte vs React (Svelte blog)](https://svelte.dev/blog/virtual-dom-is-pure-overhead)
- [LWN: Svelte overview (2022)](https://lwn.net/Articles/856775/)
