# JavaScript Deep Dive

## Closures

A closure is a function that remembers variables from its outer scope, even after the outer function has returned:

```javascript
function createCounter() {
  let count = 0;  // closed-over variable
  return {
    increment: () => ++count,
    getCount: () => count,
  };
}

const counter = createCounter();
counter.increment(); // 1
counter.increment(); // 2
counter.getCount();  // 2
// `count` is not directly accessible — encapsulated via closure
```

**Interview trap**: Closures in loops:
```javascript
// ❌ Classic bug: all callbacks share same `i`
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100); // 3, 3, 3
}

// ✅ Fix 1: `let` creates block scope
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100); // 0, 1, 2
}

// ✅ Fix 2: IIFE creates closure
for (var i = 0; i < 3; i++) {
  ((j) => setTimeout(() => console.log(j), 100))(i);
}
```

## Prototypes

Every object has a prototype chain. Property lookup traverses the chain:

```javascript
const animal = { eats: true };
const rabbit = Object.create(animal);
rabbit.jumps = true;

rabbit.jumps  // true (own property)
rabbit.eats   // true (from prototype)
rabbit.hasOwnProperty('eats') // false
```

**Class syntax is syntactic sugar over prototypes:**
```javascript
class Animal {
  constructor(name) { this.name = name; }
  speak() { return `${this.name} speaks`; }
}

class Dog extends Animal {
  bark() { return `${this.name} barks`; }
}

// Equivalent to prototype chain:
// Dog.prototype → Animal.prototype → Object.prototype
```

## `this` Keyword

Four rules determine `this`:

| Rule | Example | `this` refers to |
|---|---|---|
| **Default** | `fn()` (strict: undefined) | Global object |
| **Implicit** | `obj.fn()` | `obj` |
| **Explicit** | `fn.call(obj)` / `fn.apply(obj)` / `fn.bind(obj)` | First argument |
| **`new`** | `new Constructor()` | New object created |

```javascript
const obj = {
  name: 'Alice',
  greet() { return `Hi, I'm ${this.name}`; },
  greetArrow: () => `Hi, I'm ${this.name}`, // `this` is outer scope!
};

obj.greet();       // "Hi, I'm Alice" (implicit binding)
obj.greetArrow();  // "Hi, I'm undefined" (arrow fn, `this` is global)

const greet = obj.greet;
greet();           // "Hi, I'm undefined" (default binding, lost `this`)
```

**Arrow functions** don't have their own `this` — they inherit from the enclosing scope.

## Promises & async/await

```javascript
// Promise basics
const promise = new Promise((resolve, reject) => {
  if (success) resolve(data);
  else reject(error);
});

promise
  .then(data => transform(data))
  .then(result => use(result))
  .catch(err => handle(err))
  .finally(() => cleanup());

// async/await — syntactic sugar over promises
async function fetchUser(id) {
  try {
    const response = await fetch(`/api/users/${id}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (err) {
    console.error('Failed:', err);
    throw err;
  }
}
```

### Microtask vs Macrotask Queue

```
Call Stack
    ↓
Microtask Queue (Promises, queueMicrotask, MutationObserver)
    ↓
Macrotask Queue (setTimeout, setInterval, I/O, UI rendering)
```

Microtasks are processed before the next macrotask. This is why `Promise.then` runs before `setTimeout(fn, 0)`:

```javascript
console.log('1');                    // synchronous
setTimeout(() => console.log('2'));  // macrotask
Promise.resolve().then(() => console.log('3')); // microtask
console.log('4');                    // synchronous

// Output: 1, 4, 3, 2
```

## Event Loop

```javascript
// Single-threaded, non-blocking
console.log('Start');

setTimeout(() => console.log('Timeout'), 0);

fetch('https://api.example.com/data')
  .then(res => res.json())
  .then(data => console.log('Fetch complete'));

console.log('End');

// Output: Start, End, Fetch complete (async), Timeout
```

## Modules

```javascript
// ES Modules (modern)
// math.js
export const PI = 3.14159;
export function add(a, b) { return a + b; }
export default class Calculator { /* ... */ }

// main.js
import Calculator, { PI, add } from './math.js';
import * as math from './math.js';

// CommonJS (Node.js)
// math.js
module.exports = { add: (a, b) => a + b };
// main.js
const { add } = require('./math.js');
```

## Interview Questions

**Q: What is a closure and how does it work?**
A: A function that retains access to variables from its enclosing scope, even after that scope has finished executing. Closures are created every time a function is created. Used for data privacy, callbacks, and factory functions.

**Q: Explain the event loop.**
A: JavaScript is single-threaded. The event loop continuously checks: (1) execute all synchronous code on the call stack, (2) process all microtasks (Promises), (3) process one macrotask (setTimeout, I/O), (4) render if needed. This enables non-blocking async behavior.

**Q: What is `this` in an arrow function?**
A: Arrow functions don't have their own `this`. They inherit `this` from the enclosing lexical scope. This makes them unsuitable for object methods but perfect for callbacks where you want to preserve the outer `this`.

## References

- [MDN Closures](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Closures)
- [MDN Event Loop](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Event_loop)
- [JavaScript.info](https://javascript.info/)
