# React for Interviews

## Component Model

```jsx
// Functional component (modern)
function UserCard({ name, email }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div onClick={() => setExpanded(!expanded)}>
      <h2>{name}</h2>
      {expanded && <p>{email}</p>}
    </div>
  );
}
```

## Essential Hooks

```javascript
// useState — state management
const [count, setCount] = useState(0);

// useEffect — side effects
useEffect(() => {
  fetchData();
  return () => cleanup(); // cleanup on unmount
}, [dependency]); // re-run when dependency changes

// useContext — consume context
const theme = useContext(ThemeContext);

// useReducer — complex state logic
const [state, dispatch] = useReducer(reducer, initialState);

// useMemo — memoize expensive computation
const sorted = useMemo(() => items.sort(), [items]);

// useCallback — memoize function reference
const handleClick = useCallback(() => doSomething(id), [id]);

// useRef — mutable ref, persists across renders
const inputRef = useRef(null);
inputRef.current.focus();
```

## Virtual DOM & Reconciliation

React maintains a virtual DOM (JS object tree). On state change:
1. New virtual DOM created
2. Diffed with previous virtual DOM
3. Only changed parts applied to real DOM

**Keys** help React identify items in lists:
```jsx
// ❌ Bad — using index as key causes re-render issues
{items.map((item, i) => <Item key={i} {...item} />)}

// ✅ Good — stable unique ID
{items.map(item => <Item key={item.id} {...item} />)}
```

## State Management

```javascript
// Context API (built-in, for simple global state)
const ThemeContext = createContext('light');
function App() {
  return (
    <ThemeContext.Provider value="dark">
      <Child />
    </ThemeContext.Provider>
  );
}

// useReducer (for complex local state)
function reducer(state, action) {
  switch (action.type) {
    case 'increment': return { count: state.count + 1 };
    case 'decrement': return { count: state.count - 1 };
    default: throw new Error();
  }
}
```

## Interview Questions

**Q: Explain the React component lifecycle.**
A: Functional components use `useEffect`: (1) Mount — runs after first render, (2) Update — runs when dependencies change, (3) Unmount — cleanup function returned from useEffect. Class components had componentDidMount/DidUpdate/WillUnmount.

**Q: What is the virtual DOM and why is it fast?**
A: An in-memory representation of the real DOM. React diffs the new and old virtual DOMs, then applies only the minimal set of changes to the real DOM. This is faster than direct DOM manipulation because DOM operations are expensive.

**Q: When would you use `useMemo` vs `useCallback`?**
A: `useMemo` memoizes a computed VALUE (expensive calculation). `useCallback` memoizes a FUNCTION reference (prevents child re-renders). Both prevent unnecessary work when dependencies haven't changed.

## References

- [React Documentation](https://react.dev/)
- [React Hooks FAQ](https://react.dev/reference/react/hooks)
