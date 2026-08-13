# DOM (Document Object Model)

The DOM is a programming interface for web documents. It represents the page as a tree of nodes and objects, providing a structured representation that programs can change to affect the document's structure, style, and content.

## What is the DOM?

The DOM is a language-independent, platform-independent API for HTML and XML documents. When a browser loads an HTML document, it parses the markup and constructs a tree of nodes:

```
Document
└── html
    ├── head
    │   ├── title
    │   │   └── "Page Title"
    │   └── meta
    └── body
        ├── h1
        │   └── "Hello"
        ├── p
        │   └── "World"
        └── div
            └── span
                └── "Nested"
```

Every HTML element becomes an **Element node**, text becomes a **Text node**, comments become **Comment nodes**, and the document itself is the **Document node**.

## DOM API Methods

### Selecting Elements

```javascript
// By ID — returns single element or null
const el = document.getElementById('myId');

// By class name — returns live HTMLCollection
const items = document.getElementsByClassName('item');

// By tag name — returns live HTMLCollection
const paragraphs = document.getElementsByTagName('p');

// CSS selector — returns first match or null
const first = document.querySelector('.container > .item');

// CSS selector — returns all matches (static NodeList)
const all = document.querySelectorAll('.container > .item');

// Closest ancestor matching selector
const ancestor = element.closest('.parent');
```

**Live vs Static Collections:**
- `getElementsByClassName` and `getElementsByTagName` return **live** collections — they update automatically when the DOM changes
- `querySelectorAll` returns a **static** NodeList — a snapshot that doesn't change

### Creating and Modifying Elements

```javascript
// Create elements
const div = document.createElement('div');
const text = document.createTextNode('Hello');

// Append to DOM
parent.appendChild(child);
parent.insertBefore(newChild, referenceChild);
parent.append(child1, child2, 'text'); // multiple args, strings allowed
parent.prepend(child);
parent.after(sibling);
parent.before(sibling);

// Remove from DOM
parent.removeChild(child);
element.remove(); // modern, cleaner

// Replace
parent.replaceChild(newChild, oldChild);
element.replaceWith(newElement);

// Clone
const clone = element.cloneNode(true); // true = deep clone

// Attributes
element.setAttribute('class', 'active');
element.getAttribute('data-id');
element.removeAttribute('disabled');
element.hasAttribute('hidden');
element.dataset.userId; // reads data-user-id

// Classes
element.classList.add('active');
element.classList.remove('hidden');
element.classList.toggle('dark-mode');
element.classList.contains('active');
element.classList.replace('old', 'new');

// Styles
element.style.color = 'red';
element.style.backgroundColor = '#fff';
element.style.cssText = 'color: red; background: blue;';
```

### InnerHTML vs TextContent

```javascript
// innerHTML — parses HTML, triggers reparse
element.innerHTML = '<strong>Bold</strong>';

// textContent — plain text, no parsing, safer (no XSS from user input)
element.textContent = 'Bold text with <tags> as literal';

// outerHTML — the element itself plus its contents
console.log(element.outerHTML); // <div class="x">content</div>
```

**Security Note:** Never use `innerHTML` with user-supplied content — it's a vector for XSS attacks. Use `textContent` or sanitize with DOMPurify.

## DOM Traversal

### Tree Navigation

```javascript
// Parent
node.parentNode;    // parent node (any type)
node.parentElement; // parent element (null if parent is not an element)

// Children
node.childNodes;    // live NodeList of all child nodes (including text, comments)
node.children;      // live HTMLCollection of child elements only
node.firstChild;    // first child node
node.lastChild;     // last child node
node.firstElementChild; // first child element
node.lastElementChild;  // last child element

// Siblings
node.nextSibling;        // next sibling node
node.previousSibling;    // previous sibling node
node.nextElementSibling; // next sibling element
node.previousElementSibling; // previous sibling element
```

### Element Information

```javascript
node.nodeType;   // 1=Element, 3=Text, 8=Comment, 9=Document
node.nodeName;   // tag name (uppercase for elements)
node.nodeValue;  // text content for text/comment nodes
node.textContent; // text content of all descendants

// Element-specific
element.tagName;       // uppercase tag name
element.id;
element.className;     // string of all classes
element.classList;     // DOMTokenList (array-like)
element.innerHTML;
element.textContent;
element.offsetParent;
element.offsetLeft;
element.offsetTop;
element.offsetWidth;
element.offsetHeight;
element.clientWidth;   // width minus scrollbar and border
element.clientHeight;  // height minus scrollbar and border
element.scrollHeight;  // total scrollable height
element.scrollWidth;   // total scrollable width
```

## Events

### Event Listeners

```javascript
// Add listener
element.addEventListener('click', handler, options);

// Remove listener (must reference same function)
element.removeEventListener('click', handler, options);

// Options object
element.addEventListener('click', handler, {
  once: true,         // remove after first invocation
  passive: true,      // handler won't call preventDefault (improves scroll performance)
  capture: true,      // listen during capture phase
  signal: controller.signal // AbortController for removal
});

// Remove with AbortController
const controller = new AbortController();
element.addEventListener('click', handler, { signal: controller.signal });
controller.abort(); // removes the listener
```

### Event Object

```javascript
element.addEventListener('click', (event) => {
  event.type;          // 'click'
  event.target;        // element that triggered the event
  event.currentTarget; // element the listener is attached to
  event.preventDefault();  // prevent default behavior
  event.stopPropagation(); // stop propagation
  event.stopImmediatePropagation(); // stop other listeners on same element
  event.clientX;       // mouse X relative to viewport
  event.clientY;       // mouse Y relative to viewport
  event.pageX;         // mouse X relative to document
  event.pageY;         // mouse Y relative to document
  event.key;           // key pressed (for keyboard events)
  event.code;          // physical key code
  event.timeStamp;     // when the event was created
  event.defaultPrevented; // whether preventDefault was called
});
```

## Event Propagation

Events propagate through the DOM in three phases:

### 1. Capture Phase (Trickling Down)

The event starts at the `window`, then moves down through `document`, `html`, `body`, and through ancestors toward the target element. Listeners registered with `capture: true` fire during this phase.

### 2. Target Phase

The event reaches the target element. All listeners on the target fire (in order of registration, regardless of capture flag).

### 3. Bubbling Phase (Bubbling Up)

The event moves back up from the target to `window`. Listeners registered without `capture` (or with `capture: false`) fire during this phase.

```
Window → Document → html → body → ... → target → ... → body → html → Document → Window
         Capture                               Target        Bubbling
```

```javascript
// Capture phase listener
element.addEventListener('click', handler, true);
element.addEventListener('click', handler, { capture: true });

// Bubbling phase listener (default)
element.addEventListener('click', handler);
element.addEventListener('click', handler, false);
element.addEventListener('click', handler, { capture: false });
```

### Preventing Propagation

```javascript
element.addEventListener('click', (e) => {
  e.stopPropagation(); // stops event from reaching ancestors/descendants
  e.stopImmediatePropagation(); // also stops other listeners on the same element
});
```

## Event Delegation

Instead of attaching listeners to every child element, attach a single listener to a parent and use `event.target` to determine which child was clicked.

### Why Delegate?

- **Performance** — one listener instead of hundreds
- **Memory** — fewer function objects and listener registrations
- **Dynamic elements** — automatically handles elements added after the listener was attached
- **Cleanup** — only one listener to remove

### Implementation

```javascript
// Bad — individual listeners
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('click', handleClick);
});

// Good — delegated listener
document.querySelector('.container').addEventListener('click', (e) => {
  const btn = e.target.closest('.btn');
  if (!btn) return; // not a button click
  if (!e.currentTarget.contains(btn)) return; // not within our container

  // Handle the click
  console.log('Button clicked:', btn.dataset.action);
});
```

The `closest()` method is critical — it handles cases where the click target is a child of the button (like an `<span>` inside a `<button>`).

### Events That Don't Bubble

Some events don't bubble and therefore can't be delegated with bubbling:

- `focus` / `blur` — use `focusin` / `focusout` instead
- `mouseenter` / `mouseleave` — use `mouseover` / `mouseout` instead
- `load`, `unload`, `resize`, `scroll` (on window)
- `DOMContentLoaded`

## Virtual DOM

The Virtual DOM (VDOM) is a programming concept where a virtual representation of the UI is kept in memory and synced with the real DOM. This is the core idea behind React and similar frameworks.

### How It Works

1. **State Change** — when application state changes, a new virtual DOM tree is created
2. **Diffing** — the new VDOM is compared with the previous VDOM to find differences (the "diff" algorithm)
3. **Reconciliation** — only the minimal set of changes needed are applied to the real DOM

### Why Virtual DOM?

- **Batching** — multiple state changes are batched into a single DOM update
- **Minimal DOM operations** — only changed nodes are updated
- **Declarative** — developers describe what the UI should look like, not how to change it
- **Cross-platform** — the same VDOM can render to different targets (DOM, native, canvas)

### Virtual DOM vs Real DOM

| Aspect | Real DOM | Virtual DOM |
|--------|----------|-------------|
| Update speed | Slow for frequent updates | Fast diffing, minimal updates |
| Memory | Browser-managed | Additional memory for VDOM copies |
| Direct manipulation | Yes | No — changes go through framework |
| Debugging | Inspect directly | Framework devtools needed |

### When Virtual DOM Isn't Optimal

- Simple, static pages with minimal interactivity
- Applications with very fine-grained updates (Svelte, SolidJS use different approaches)
- The overhead of diffing can exceed the cost of direct DOM manipulation for very small changes

### The Reconciliation Algorithm (React)

React's reconciliation (called "Fiber" since React 16) uses these heuristics:

1. **Different types produce different trees** — if a `<div>` changes to a `<span>`, the entire subtree is destroyed and rebuilt
2. **Keys identify stable elements** — in lists, `key` props help React match elements between renders

```jsx
// Keys help React identify which items changed
{items.map(item => (
  <ListItem key={item.id} data={item} />
))}
```

### Alternatives to Virtual DOM

- **Svelte** — compiles to direct DOM operations at build time
- **SolidJS** — fine-grained reactivity without VDOM diffing
- **Lit** — uses tagged template literals and efficient updates
- **Signals** — reactive primitives (used by Preact Signals, Qwik, Angular)

## Shadow DOM

The Shadow DOM is a separate DOM tree attached to an element, providing encapsulation:

```javascript
const shadow = element.attachShadow({ mode: 'open' });
shadow.innerHTML = `
  <style>
    /* These styles are scoped to the shadow DOM */
    p { color: red; }
  </style>
  <p>Shadow content</p>
`;
```

- **Encapsulation** — styles inside the shadow DOM don't leak out, external styles don't leak in
- **Composition** — `<slot>` elements allow external content to be projected into the shadow tree
- **Web Components** — custom elements use Shadow DOM for encapsulation by default

## Key Interview Points

- The DOM is a tree-structured API, not the HTML itself
- `querySelectorAll` returns a static NodeList; `getElementsBy*` returns live collections
- Event propagation has three phases: capture, target, and bubbling
- Event delegation uses a single listener on a parent, leveraging bubbling and `closest()`
- `event.stopPropagation()` prevents further propagation; `event.preventDefault()` prevents default behavior
- Virtual DOM is a diffing optimization, not inherently faster than direct DOM manipulation
- Shadow DOM provides style and markup encapsulation for Web Components
- `innerHTML` with user input is an XSS vulnerability
