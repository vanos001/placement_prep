# Frontend Interview Questions

## HTML & CSS

**Q: What is the difference between `display: none`, `visibility: hidden`, and `opacity: 0`?**
A: `display: none` removes element from layout (no space). `visibility: hidden` hides element but keeps space. `opacity: 0` makes element invisible but keeps space and is clickable.

**Q: Explain CSS specificity.**
A: Inline (1000) > ID (100) > Class/Pseudo-class (10) > Element/Pseudo-element (1). Equal specificity: last rule wins. `!important` overrides everything (avoid).

**Q: What is the difference between Flexbox and Grid?**
A: Flexbox is 1D (row OR column) — good for component layout. Grid is 2D (rows AND columns) — good for page layout. They complement each other.

**Q: How does CSS `position: sticky` work?**
A: Element scrolls normally until it reaches the threshold (e.g., `top: 0`), then "sticks" like `fixed`. Requires a scrollable parent and `top`/`bottom`/`left`/`right` to be set.

## JavaScript

**Q: Explain closures with an example.**
A: A function that remembers its outer variables even after the outer function returns. `function counter() { let n=0; return () => ++n; }` — the returned function closes over `n`.

**Q: What is the event loop?**
A: JS is single-threaded. The event loop: (1) execute call stack, (2) process microtasks (Promises), (3) process one macrotask (setTimeout), (4) render. This enables non-blocking async I/O.

**Q: What is the difference between `==` and `===`?**
A: `==` performs type coercion (`"1" == 1` is true). `===` checks value AND type without coercion (`"1" === 1` is false). Always use `===`.

**Q: Explain `Promise.all` vs `Promise.allSettled` vs `Promise.race`.**
A: `all` — resolves when all resolve, rejects on first rejection. `allSettled` — resolves when all settle (never rejects). `race` — resolves/rejects with the first settled promise.

## TypeScript

**Q: What is a discriminated union?**
A: A union type where each member has a common literal property for narrowing: `type Shape = {kind:"circle", r:number} | {kind:"rect", w:number}`. Use `switch(shape.kind)` to narrow.

**Q: What does `as const` do?**
A: Makes the value deeply readonly and narrows literal types: `const x = "hello"` is `string`, but `const x = "hello" as const` is `"hello"` (literal type).

## React

**Q: Why do we need keys in lists?**
A: Keys help React identify which items changed, were added, or removed. Without stable keys, React re-renders the entire list on changes. Use unique IDs, not array indices.

**Q: What is the dependency array in `useEffect`?**
A: Controls when the effect re-runs. `[]` = run once on mount. `[a, b]` = run when `a` or `b` changes. Omitted = run on every render. Incorrect deps cause stale closures or infinite loops.

**Q: How do you prevent unnecessary re-renders?**
A: (1) `React.memo` for component memoization, (2) `useMemo` for expensive computations, (3) `useCallback` for function references passed to children, (4) Move state down to where it's needed, (5) Context optimization with separate providers.

## References

- [Frontend Interview Handbook](https://www.frontendinterviewhandbook.com/)
- [JavaScript Interview Questions](https://github.com/sudheerj/javascript-interview-questions)
