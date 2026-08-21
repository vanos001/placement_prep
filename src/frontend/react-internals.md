# React Internals

React is an open-source JavaScript library for building user interfaces, developed by Facebook (now Meta) since 2013. Its internal architecture has evolved through multiple major versions: the original "stack reconciler" (React 0.x to 15), the "fiber reconciler" (React 16+, 2017), and the concurrent renderer with hooks (React 18, 2022). This page covers the fiber architecture, the reconciliation algorithm, the hooks model, and the concurrent features.

## The Fiber Architecture

React 16 (2017) replaced the original reconciler with "Fiber" — a re-implementation of the rendering pipeline that supports:

- **Time-slicing**: long renders can be paused and resumed.
- **Prioritization**: high-priority updates (e.g., user input) can interrupt low-priority ones (e.g., data fetching).
- **Concurrency**: multiple updates can be in flight simultaneously.

A "fiber" is a JavaScript object representing a unit of work:

```js
{
  type: 'div',           // the element type
  key: null,             // the key (for list reconciliation)
  pendingProps: {...},   // the new props
  memoizedProps: {...},  // the previous props
  memoizedState: {...},  // the previous state (for hooks)
  child: fiber,          // first child
  sibling: fiber,        // next sibling
  return: fiber,         // parent
  alternate: fiber,      // the previous version (for double buffering)
  effectTag: 'UPDATE',   // what to do (PLACEMENT, UPDATE, DELETION)
  updates: [],           // queued state updates
  ...
}
```

The fiber tree mirrors the component tree. React walks the fiber tree, computes the new state, and produces a list of "effects" (DOM mutations to apply).

## The Reconciliation Algorithm

When the user triggers an update (e.g., `setState`), React:

1. **Schedules** the update with a priority.
2. **Renders** the components (calls the function components, gets the new JSX).
3. **Reconciles** the new fiber tree with the old (the "alternate").
4. **Commits** the effects (DOM mutations, lifecycle methods, effects).

### Render Phase (Pure)

```js
function App() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>{count}</button>;
}

// React calls App() to get the JSX.
// React creates a fiber for the <button> with new props {children: count}.
// React diffs the new fiber with the old (memoizedProps).
// React records an effect: "Update button text".
```

The render phase is **pure** — no side effects, can be called multiple times (for time-slicing or re-renders).

### Commit Phase (Side Effects)

```js
// React walks the fiber tree, applies effects:
//   - PLACEMENT: insert DOM node
//   - UPDATE: update DOM node's attributes
//   - DELETION: remove DOM node
// Then runs the useEffect callbacks (deferred to after paint).
```

The commit phase is **synchronous** — DOM mutations must be in order; no interruption. This is why React can't pause during commit.

## The Hooks Model

Hooks (React 16.8, 2019) replaced class components' `this.state` and `this.setState`:

```js
function Counter() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
}
```

Internally, hooks are stored on the fiber's `memoizedState` as a linked list:

```text
fiber.memoizedState:
  useState(0) → hook1 { memoizedState: 0, queue: [], next: hook2 }
  useEffect(...) → hook2 { memoizedState: callback, deps: [], next: hook3 }
  useMemo(...) → hook3 { memoizedState: value, deps: [], next: null }
```

The hooks are called in order on each render; React matches each call to its previous hook (by position). This is why hooks can't be inside conditions — the order would change, mismatching the previous hooks.

### The Rules of Hooks

1. **Only call hooks at the top level** (not in loops, conditions, nested functions).
2. **Only call hooks from React function components** (not regular functions or class components).

These rules exist because of the position-based matching. A conditional hook call would skip a hook in the previous render, mismatching subsequent hooks.

## useEffect vs. useLayoutEffect

```js
useEffect(() => {
  // Runs AFTER paint (async).
  // Good for: data fetching, subscriptions, logging.
  return () => cleanup();
});

useLayoutEffect(() => {
  // Runs BEFORE paint (sync).
  // Good for: DOM measurements (e.g., scroll position), focus management.
  return () => cleanup();
});
```

`useLayoutEffect` blocks the browser paint; use it sparingly. For most cases, `useEffect` is sufficient.

## Concurrent Features (React 18)

React 18 (2022) introduced concurrent rendering:

- **useTransition**: mark a state update as low-priority (non-urgent).
- **useDeferredValue**: defer a value's update.
- **Suspense**: pause rendering while waiting for async data.
- **Automatic batching**: batch updates across async boundaries.

```js
function App() {
  const [isPending, startTransition] = useTransition();
  const [tab, setTab] = useState('home');
  
  const switchTab = (newTab) => {
    startTransition(() => {
      setTab(newTab);  // low-priority; doesn't block input
    });
  };
  
  return (
    <>
      <nav>
        <button onClick={() => switchTab('home')}>Home</button>
        <button onClick={() => switchTab('settings')}>Settings</button>
      </nav>
      {isPending && <p>Loading...</p>}
      <Content tab={tab} />
    </>
  );
}
```

With `useTransition`, switching tabs doesn't block the input — the user can keep clicking while the new tab renders in the background.

## The Virtual DOM

React's "virtual DOM" is a JavaScript object tree representing the desired UI:

```js
const vnode = {
  type: 'div',
  props: {
    children: [
      { type: 'h1', props: { children: 'Hello' } },
      { type: 'p', props: { children: 'World' } },
    ],
  },
};
```

On each render, React creates a new vnode tree, diffs it with the previous, and applies the minimal DOM mutations.

The virtual DOM was innovative in 2013 but is now seen as overhead. Newer frameworks (Solid, Svelte) skip the virtual DOM and compile to direct DOM mutations.

## Production Performance

React's typical performance characteristics:
- Initial render: ~50 ms for a 1000-element tree.
- Re-render (with React.memo): ~5 ms.
- Re-render (without memo): ~20 ms.
- Concurrent rendering: same total work, but no UI blocking.

For high-performance lists (10K+ items), use `react-window` or `react-virtualized` for virtualization.

## Common Pitfalls

1. **Forgetting to memoize expensive computations.** Without `useMemo`, the function runs on every render. Memoize with `useMemo` or extract to `useCallback` for stable references.

2. **Forgetting to use keys in lists.** Without keys, React matches by position; reorders cause unnecessary re-renders. Use stable, unique keys.

3. **Forgetting that `useState` updates are batched.** Multiple `setState` calls in the same event handler are batched into one re-render. But across async boundaries (e.g., `setTimeout`), they're separate (unless React 18's automatic batching).

4. **Forgetting that `useEffect` runs after every render.** Without a dependency array, it runs every render; with an empty array, it runs once.

5. **Forgetting that hook order must be consistent.** A conditional hook call breaks the position-based matching; React throws "Rendered fewer hooks than expected".

6. **Forgetting that refs don't trigger re-renders.** `useRef` is for mutable values that don't need re-rendering; for state that triggers re-renders, use `useState`.

## Comparison to Other Frameworks

| Aspect | React | Vue | Svelte | Solid |
|--------|-------|-----|--------|-------|
| Origin | Facebook 2013 | Evan You 2014 | Rich Harris 2016 | Ryan Carniato 2018 |
| Virtual DOM | Yes | Yes | No (compiled) | No (compiled) |
| Hooks | Yes (16.8) | Composition API | No (different model) | Yes |
| Bundle size | ~40 KB | ~30 KB | ~5 KB (compiled) | ~7 KB |
| Best for | Large teams, ecosystem | Easy learning curve | Performance, small bundle | Performance, signals |

React has the largest ecosystem; Vue is easier to learn; Svelte and Solid compile to direct DOM mutations for smaller bundles and faster runtime.

## References

- [React documentation](https://react.dev/)
- Andrew Clark, "[React Fiber Architecture](https://github.com/acdlite/react-fiber-architecture)" (2016)
- [React 18: Concurrent features](https://react.dev/blog/2022/03/29/react-v18)
- [React internals: Fiber, Reconciler, Scheduler](https://indepth.dev/posts/53/react-internals-fiber)
- Sebastian Markbåge, "[Hooks: The next generation of React](https://www.youtube.com/watch?v=kJVrqO1FmHU)" (React Conf 2018)
- [React source code](https://github.com/facebook/react)
- [LWN: React internals (2020)](https://lwn.net/Articles/815571/)
