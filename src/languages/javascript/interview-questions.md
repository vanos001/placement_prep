# JavaScript Interview Questions

## Fundamentals

### Q1: What is hoisting?

```javascript
// Variable declarations are hoisted
console.log(x); // undefined (not ReferenceError)
var x = 5;

// Function declarations are hoisted
foo(); // Works!
function foo() { console.log('hello'); }

// let/const are hoisted but in "temporal dead zone"
console.log(y); // ReferenceError
let y = 5;
```

### Q2: What is the event loop?

JavaScript is single-threaded. The event loop:
1. Executes synchronous code (call stack)
2. Checks microtask queue (Promises, queueMicrotask)
3. Checks macrotask queue (setTimeout, setInterval, I/O)
4. Renders (browser)
5. Repeat

Microtasks have priority over macrotasks.

### Q3: What are closures?

A function that remembers its lexical scope even when executed outside that scope.

```javascript
function multiplier(factor) {
    return (number) => number * factor;
}
const double = multiplier(2);
double(5); // 10
// `factor` is captured in the closure
```

### Q4: Explain `this` keyword.

| Context | `this` refers to |
|---------|------------------|
| Global | `window` (browser) / `global` (Node.js) |
| Object method | The object |
| Constructor | New instance |
| Arrow function | Enclosing `this` (lexical) |
| `call/apply/bind` | Specified object |

```javascript
const obj = {
    name: 'Alice',
    greet: function() { return this.name; },
    greetArrow: () => this.name // 'this' is outer scope
};
```

### Q5: What is prototypal inheritance?

Every object has a hidden `[[Prototype]]` property linking to another object. Property lookup traverses the chain until found or `null`.

```javascript
const animal = { eats: true };
const dog = Object.create(animal);
dog.barks = true;
dog.eats; // true (inherited)
dog.hasOwnProperty('barks'); // true
dog.hasOwnProperty('eats'); // false
```

## Async

### Q6: Promise states?

- **Pending**: Initial state
- **Fulfilled**: Operation completed successfully
- **Rejected**: Operation failed
- **Settled**: Either fulfilled or rejected (immutable)

```javascript
const p = new Promise((resolve, reject) => {
    // Pending...
    resolve('done'); // Fulfilled
    // or reject('error'); // Rejected
});
```

### Q7: Promise.all vs Promise.allSettled vs Promise.race?

| Method | Resolves when | Rejects when |
|--------|---------------|--------------|
| `all` | All fulfilled | Any rejected |
| `allSettled` | All settled | Never rejects |
| `race` | First settles | First rejects |

```javascript
const results = await Promise.allSettled([
    fetch('/api/1'),
    fetch('/api/2'),
    fetch('/api/3')
]);
// results: [{status: 'fulfilled', value: ...}, ...]
```

### Q8: How to handle errors in async/await?

```javascript
// try/catch
async function fetchData() {
    try {
        const res = await fetch('/api');
        return await res.json();
    } catch (err) {
        console.error('Fetch failed:', err);
        throw err; // Re-throw or handle
    }
}

// Error handling helper
function to(promise) {
    return promise.then(data => [null, data]).catch(err => [err, null]);
}
const [err, data] = await to(fetchData());
```

### Q9: What is the difference between `for...of` and `for...in`?

```javascript
const arr = ['a', 'b', 'c'];

// for...of: values (iterable)
for (const val of arr) console.log(val); // 'a', 'b', 'c'

// for...in: keys (enumerable)
for (const key in arr) console.log(key); // '0', '1', '2'

const obj = { a: 1, b: 2 };
for (const key in obj) console.log(key); // 'a', 'b'
// for...of doesn't work on plain objects
```

## Functions

### Q10: Call, apply, bind?

```javascript
function greet(greeting, punctuation) {
    return `${greeting}, ${this.name}${punctuation}`;
}
const user = { name: 'Alice' };

// call: individual args
greet.call(user, 'Hello', '!'); // 'Hello, Alice!'

// apply: array of args
greet.apply(user, ['Hello', '!']); // 'Hello, Alice!'

// bind: returns new function with bound context
const bound = greet.bind(user, 'Hello');
bound('!'); // 'Hello, Alice!'
```

### Q11: Arrow functions vs regular functions?

| Arrow | Regular |
|-------|---------|
| Lexical `this` | Dynamic `this` |
| No `arguments` object | Has `arguments` |
| Cannot be constructor | Can be constructor |
| No `prototype` | Has `prototype` |
| Cannot be generator | Can be generator |

### Q12: What is currying?

```javascript
// Transform f(a, b, c) into f(a)(b)(c)
function curry(fn) {
    return function curried(...args) {
        if (args.length >= fn.length) {
            return fn.apply(this, args);
        }
        return (...args2) => curried(...args, ...args2);
    };
}

const add = curry((a, b, c) => a + b + c);
add(1)(2)(3); // 6
add(1, 2)(3); // 6
```

## Objects and Arrays

### Q13: Shallow vs deep copy?

```javascript
// Shallow copy
const shallow = { ...obj };
const shallow2 = Object.assign({}, obj);
const shallow3 = arr.slice();

// Deep copy
const deep = JSON.parse(JSON.stringify(obj)); // Loses functions, dates
const deep2 = structuredClone(obj); // Modern browsers

// Nested objects are still references in shallow copy
```

### Q14: Destructuring?

```javascript
// Object destructuring
const { name, age = 25, ...rest } = user;

// Array destructuring
const [first, second, ...others] = arr;

// Function parameter destructuring
function greet({ name, greeting = 'Hello' }) {
    return `${greeting}, ${name}`;
}

// Swap variables
[a, b] = [b, a];
```

### Q15: Map vs Object?

| Map | Object |
|-----|--------|
| Any key type | String/Symbol keys only |
| Size property | Manual count |
| Iterable | Not directly iterable |
| No prototype chain | Prototype chain |
| Better for frequent add/delete | Better for static data |

```javascript
const map = new Map();
map.set(1, 'one');
map.set({}, 'obj');
map.size; // 2
```

## Advanced

### Q16: What is event delegation?

```javascript
// Instead of adding listeners to each element
// Add one listener to parent
document.getElementById('list').addEventListener('click', (e) => {
    if (e.target.tagName === 'LI') {
        handleItemClick(e.target);
    }
});
```

### Q17: What is debouncing vs throttling?

```javascript
// Debounce: execute after delay since last call
function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// Throttle: execute at most once per interval
function throttle(fn, interval) {
    let last = 0;
    return (...args) => {
        const now = Date.now();
        if (now - last >= interval) {
            last = now;
            fn(...args);
        }
    };
}
```

### Q18: What is the module pattern?

```javascript
// IIFE (Immediately Invoked Function Expression)
const Counter = (() => {
    let count = 0;
    return {
        increment: () => ++count,
        getCount: () => count
    };
})();

// ES Modules
// counter.js
let count = 0;
export const increment = () => ++count;
export const getCount = () => count;

// main.js
import { increment, getCount } from './counter.js';
```

### Q19: WeakMap and WeakSet?

```javascript
// WeakMap: keys must be objects, weakly held
const wm = new WeakMap();
let obj = {};
wm.set(obj, 'data');
obj = null; // Entry can be garbage collected

// Use cases:
// - Private data storage
// - Caching without preventing GC
// - DOM element metadata

// WeakSet: similar, but stores objects only
const ws = new WeakSet();
ws.add(obj);
```

### Q20: Proxy and Reflect?

```javascript
const handler = {
    get(target, prop) {
        console.log(`Getting ${prop}`);
        return Reflect.get(target, prop);
    },
    set(target, prop, value) {
        console.log(`Setting ${prop} to ${value}`);
        return Reflect.set(target, prop, value);
    }
};

const proxy = new Proxy({ name: 'Alice' }, handler);
proxy.name; // Logs: Getting name → 'Alice'
proxy.age = 25; // Logs: Setting age to 25
```

## Related Topics

- [Node.js](./nodejs.md) — Server-side JavaScript
- [V8 Engine](./v8.md) — Runtime internals
- [TypeScript](./README.md) — Type system
- [Event Loop](../../os/processes/) — OS-level event handling
