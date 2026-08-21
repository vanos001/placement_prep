# Mutation Observer

The Mutation Observer API is a browser API for observing changes to the DOM tree. It asynchronously fires a callback when DOM elements are added, removed, or have their attributes/text changed. This page covers the API, the observation options, the use cases, and the production patterns.

## The Problem

Before Mutation Observer, DOM changes were observed via the deprecated `Mutation Events`:

```js
// Old, deprecated API
element.addEventListener('DOMNodeInserted', (event) => {
  // ...
});
```

Mutation Events fired synchronously on every change; for many changes (e.g., a 1000-row table insert), this could block the main thread for seconds.

Mutation Observer fires asynchronously (batched in microtasks), much more performant.

## The API

```js
const observer = new MutationObserver((mutations, observer) => {
  for (const mutation of mutations) {
    if (mutation.type === 'childList') {
      console.log('Children changed:', mutation.target);
      console.log('Added:', mutation.addedNodes);
      console.log('Removed:', mutation.removedNodes);
    } else if (mutation.type === 'attributes') {
      console.log('Attribute changed:', mutation.attributeName, '=', mutation.target.getAttribute(mutation.attributeName));
    } else if (mutation.type === 'characterData') {
      console.log('Text changed:', mutation.target);
    }
  }
});

const target = document.querySelector('#my-element');
observer.observe(target, {
  childList: true,         // observe child addition/removal
  attributes: true,        // observe attribute changes
  characterData: false,    // observe text changes
  subtree: true,          // observe the whole subtree, not just the target
  attributeOldValue: true, // include the old attribute value
  characterDataOldValue: false, // include the old text value
  attributeFilter: ['class', 'data-state'], // only these attributes
});
```

## The Observation Options

- **childList**: fires when child elements are added or removed.
- **attributes**: fires when attributes are added, removed, or changed.
- **characterData**: fires when text content changes.
- **subtree**: if true, observes the entire subtree (descendants), not just the target element.
- **attributeOldValue**: includes the previous attribute value in the mutation record.
- **characterDataOldValue**: includes the previous text value.
- **attributeFilter**: an array of attribute names; only fires for these attributes.

## Production Use Cases

### Content Injection Detection

For third-party content (e.g., ads, analytics scripts) that inject DOM elements:

```js
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'SCRIPT') {
        console.log('Script added:', node.src);
        // Optionally inspect or block
      }
    }
  }
});

observer.observe(document.documentElement, { childList: true, subtree: true });
```

This is used by Content Security Policy (CSP) reporters, ad blockers, and security tools to detect injected content.

### Live Form Generation

For dynamic form builders:

```js
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        // Initialize any newly added form elements
        if (node.tagName === 'INPUT') {
          node.addEventListener('input', validate);
        }
        // Also check child elements
        node.querySelectorAll?.('input').forEach((input) => {
          input.addEventListener('input', validate);
        });
      }
    }
  }
});

observer.observe(document.querySelector('#form'), { childList: true, subtree: true });
```

### Highlighting Search Terms

For search term highlighting (e.g., on a content site):

```js
function highlight(node, searchTerm) {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = node.textContent;
    if (text.includes(searchTerm)) {
      const span = document.createElement('span');
      span.innerHTML = text.replace(new RegExp(searchTerm, 'gi'), '<mark>$&</mark>');
      node.replaceWith(span);
    }
  }
}

const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const node of mutation.addedNodes) {
      highlight(node, 'search-term');
    }
  }
});

observer.observe(document.querySelector('#content'), { childList: true, subtree: true });
```

The observer re-highlights as new content is added (e.g., via infinite scroll).

### Persisting Form State

For auto-saving forms:

```js
const form = document.querySelector('#myform');
const observer = new MutationObserver(() => {
  const data = new FormData(form);
  localStorage.setItem('form-draft', JSON.stringify(Object.fromEntries(data)));
});

observer.observe(form, { attributes: true, attributeFilter: ['value'], subtree: true });
```

When inputs' values change (via attribute mutations), the form auto-saves.

## Production Performance

Mutation Observer's performance characteristics:
- Batching: the browser batches mutations within a single microtask.
- Per-mutation cost: ~1-10 µs (depending on the mutation type).
- Per-callback cost: O(N) where N is the number of mutations.

For high-frequency mutations (e.g., 1000 nodes added at once), the observer fires once with all 1000 mutations. This is much more efficient than Mutation Events (which fired 1000 times synchronously).

## Disconnect and Reconnect

```js
// Stop observing
observer.disconnect();

// Re-observe (after some changes)
observer.observe(target, options);
```

For example, when you're about to do many DOM changes (which you don't want to track), disconnect first; reconnect after.

## Comparison to Other Observation Patterns

| Pattern | When to use |
|---------|--------------|
| Mutation Observer | DOM changes (add/remove elements, attribute changes) |
| Intersection Observer | Element enters/leaves the viewport |
| Resize Observer | Element's size changes |
| Performance Observer | Performance metrics (LCP, FID, etc.) |
| EventTarget (event listeners) | User events (click, key, input) |

## Common Pitfalls

1. **Forgetting that subtree option is needed for descendant changes.** Without `subtree: true`, only direct children's changes are observed.

2. **Forgetting that addedNodes and removedNodes are NodeLists, not arrays.** You must iterate them; you can't `.map()` directly.

3. **Forgetting that the callback fires once per microtask with all mutations.** Don't process one mutation at a time if you can batch; the callback receives an array.

4. **Forgetting that characterData mutations target text nodes, not elements.** The `target` is a Text node, not the parent element.

5. **Forgetting that attribute mutations fire on every attribute change.** Use `attributeFilter` to limit to specific attributes.

6. **Forgetting to disconnect observers.** An observer that observes a removed element keeps the element in memory (the observer holds a reference). Disconnect to release.

## References

- [MDN: Mutation Observer API](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver)
- [MutationObserver: Practical examples (web.dev)](https://web.dev/articles/mutationobserver)
- [Using Mutation Observers in Practice (David Walsh blog)](https://davidwalsh.name/mutationobserver-api)
- [MutationObserver vs MutationEvents (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/MutationObserver#vs_mutation_events)
- [LWN: Mutation Observer overview (2020)](https://lwn.net/Articles/815575/)
