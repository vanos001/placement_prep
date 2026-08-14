# State Management

State management is a core frontend challenge — deciding where data lives, how it flows, and how components communicate. This guide covers the spectrum from local state to global solutions.

## Local State vs Global State

### Local State

State that's only needed within a single component:

```jsx
function SearchInput() {
  const [query, setQuery] = useState('');      // local state
  const [isFocused, setIsFocused] = useState(false);
  // Only this component uses query and isFocused
}
```

**Use for:** form inputs, UI toggles (dropdowns, modals), hover states, loading states scoped to one component.

### Global State

State shared across multiple components at different levels of the tree:

```jsx
// Theme, authentication, user preferences — needed everywhere
const [theme, setTheme] = useState('dark');
const [user, setUser] = useState(null);
```

**Use for:** authentication status, theme/preferences, locale/language, notifications, feature flags.

## The Prop Drilling Problem

Passing props through multiple levels of components that don't need them:

```jsx
// ❌ Prop drilling: App → Page → Layout → Header → UserAvatar
function App() {
  const [user, setUser] = useState(null);
  return <Page user={user} />;
}
function Page({ user }) {
  return <Layout user={user} />;
}
function Layout({ user }) {
  return <Header user={user} />;
}
function Header({ user }) {
  return <UserAvatar user={user} />; // only this needs it!
}
```

**Solutions:** Context API, state management libraries, or component composition.

### Component Composition Alternative

```jsx
// ✅ Avoid prop drilling by composing in the parent
function App() {
  const [user, setUser] = useState(null);
  return (
    <Page>
      <Header>
        <UserAvatar user={user} />
      </Header>
    </Page>
  );
}
```

## Context API

React's built-in solution for sharing state without prop drilling:

```jsx
// 1. Create context
const ThemeContext = createContext('light');

// 2. Provide value
function App() {
  const [theme, setTheme] = useState('dark');
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      <Child />
    </ThemeContext.Provider>
  );
}

// 3. Consume with hook
function Child() {
  const { theme, setTheme } = useContext(ThemeContext);
  return <button onClick={() => setTheme('light')}>{theme}</button>;
}
```

**Limitations of Context:**
- **Re-renders all consumers** — changing context value re-renders every component that uses `useContext`, even if they only use part of the value
- **No selector mechanism** — unlike Redux, you can't subscribe to part of the state
- **No dev tools** for inspecting context changes
- **Not optimized for frequent updates** — great for low-frequency state (theme, auth), not for high-frequency state (typing, dragging)

## Redux

Redux uses a single immutable store with pure reducer functions:

```javascript
// Principles:
// 1. Single source of truth — one store for all state
// 2. State is read-only — only reducers modify state (via actions)
// 3. Changes via pure functions — reducers return new state

const counterSlice = createSlice({
  name: 'counter',
  initialState: { value: 0 },
  reducers: {
    increment: (state) => { state.value += 1; },
    decrement: (state) => { state.value -= 1; },
  }
});

// Components subscribe to specific slices — only re-render when that slice changes
const count = useSelector(state => state.counter.value);
const dispatch = useDispatch();
dispatch(increment());
```

**When to use Redux:** Large applications with complex state logic, state shared between distant components, team projects needing strict state patterns, state that needs time-travel debugging.

**When NOT to use Redux:** Simple apps, apps with mostly local state, when Context API or lighter alternatives suffice.

## Modern Alternatives: Zustand & Jotai

### Zustand

Minimal, unopinionated state management with hooks:

```javascript
import { create } from 'zustand';

const useStore = create((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  theme: 'dark',
  toggleTheme: () => set((state) => ({
    theme: state.theme === 'dark' ? 'light' : 'dark'
  })),
}));

// Use in any component — no Provider needed
function Profile() {
  const user = useStore(state => state.user);
  const toggleTheme = useStore(state => state.toggleTheme);
}
```

**Advantages:** No Provider wrapper, selector-based subscriptions (selective re-renders), minimal boilerplate, works outside React components (middleware, API calls), ~1KB.

### Jotai

Atomic state management — state is split into individual atoms:

```javascript
import { atom, useAtom } from 'jotai';

// Individual atoms
const userAtom = atom(null);
const themeAtom = atom('dark');
const fontSizeAtom = atom(16);

// Derived atoms (computed state)
const doubledFontSizeAtom = atom((get) => get(fontSizeAtom) * 2);

// Components subscribe to specific atoms — no unnecessary re-renders
function ThemeSwitcher() {
  const [theme, setTheme] = useAtom(themeAtom);
  return <button onClick={() => setTheme('light')}>{theme}</button>;
}
```

**Advantages:** Bottom-up approach (atoms compose into derived state), optimal re-rendering (only affected components update), no Provider, TypeScript-friendly.

## Server State vs Client State

A critical distinction often overlooked:

| Type | Examples | Source | Tools |
|------|----------|--------|-------|
| **Server state** | User data, posts, products | API/database | TanStack Query (React Query), SWR |
| **Client state** | Theme, UI toggles, form inputs | Local | useState, Context, Zustand |
| **URL state** | Filters, page, sort, modal open | URL params | useSearchParams, nuqs |

### Server State with TanStack Query

```javascript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['users', page],
  queryFn: () => fetchUsers(page),
  staleTime: 5 * 60 * 1000, // 5 minutes
});

// Mutations
const mutation = useMutation({
  mutationFn: createUser,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
});
```

**Why use TanStack Query instead of putting API data in Redux/Context?**
- Automatic background refetching, caching, deduplication
- Loading and error states built in
- Stale-while-revalidate (SWR) pattern
- Pagination, infinite scrolling support
- Handles cache invalidation

## URL State

Using the URL as a source of truth for state:

```javascript
// Filters, pagination, sorting — all in the URL
const [searchParams, setSearchParams] = useSearchParams();

// Read
const page = searchParams.get('page') || '1';
const sort = searchParams.get('sort') || 'newest';

// Write
setSearchParams({ page: '2', sort: 'popular' });
```

**Benefits:** Shareable URLs, browser back/forward works, bookmarks preserve state, no extra state management needed.

## Interview Questions

**Q: When would you use Context API vs Redux?**
A: Context API for simple, low-frequency global state (theme, auth, locale). Redux for complex state with frequent updates, when you need dev tools (time-travel debugging), middleware (logging, persistence), or strict patterns in large teams. Context re-renders all consumers on every change — Redux allows selector-based subscriptions.

**Q: What is prop drilling and how do you avoid it?**
A: Prop drilling is passing data through multiple component layers that don't need it, just to reach a deeply nested child. Avoid with: Context API, state management libraries (Redux, Zustand), component composition (pass JSX children instead of props), or event emitters.

**Q: What's the difference between client state and server state?**
A: Client state lives in the browser (UI state, form data, theme). Server state is data fetched from an API (users, products, posts). Server state is inherently asynchronous, potentially stale, and shared across users. Use TanStack Query/SWR for server state (handles caching, refetching, deduplication) and local solutions (useState, Zustand) for client state.

**Q: How does Zustand differ from Redux?**
A: Zustand is much simpler — no Provider, no actions/reducers (just `set()`), selector-based subscriptions out of the box, and ~1KB vs Redux's ~5KB+ (with RTK). Zustand is ideal for small-to-medium apps; Redux is better for large apps needing middleware, time-travel debugging, and strict architectural patterns.

## References

- [Redux Documentation](https://redux-toolkit.js.org/)
- [Zustand GitHub](https://github.com/pmndrs/zustand)
- [Jotai GitHub](https://github.com/pmndrs/jotai)
- [TanStack Query Documentation](https://tanstack.com/query)
