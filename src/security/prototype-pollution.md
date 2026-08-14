# Prototype Pollution

## Overview

Prototype pollution is a JavaScript vulnerability where an attacker modifies the prototype of `Object`, `Array`, or other built-in types, causing unexpected behavior across the entire application. It targets JavaScript's prototype-based inheritance chain.

## The Mechanism

Every JavaScript object has an internal `[[Prototype]]` link to `Object.prototype`. If an attacker can control the key used in a recursive merge (deep merge), they can write to `Object.prototype` using the `__proto__` property.

```javascript
// Vulnerable deep merge
function merge(target, source) {
    for (let key in source) {
        if (typeof source[key] === 'object' && source[key] !== null) {
            if (!target[key]) target[key] = {};
            merge(target[key], source[key]);
        } else {
            target[key] = source[key];
        }
    }
    return target;
}

// Attack payload
const malicious = JSON.parse('{"__proto__": {"isAdmin": true}}');
merge({}, malicious);

// Every new object now inherits isAdmin
console.log(({}).isAdmin); // true
```

## Attack Vectors

| Vector | Entry Point | Example |
|--------|-------------|---------|
| `Object.assign` | Recursive merge on attacker input | `Object.assign({}, JSON.parse(userInput))` |
| `JSON.parse` + deep merge | API body, URL query params | POST with nested `__proto__` |
| `lodash.merge` (pre-4.17.12) | Any merge of untrusted data | `_.merge(config, req.body)` |
| `_.zipObjectDeep` | Keys with `.prototype` path | `_.zipObjectDeep(['a.__proto__.x'], [1])` |

## Prevention

### Primary: Never merge untrusted input recursively

```javascript
// SAFE: shallow merge — __proto__ becomes a regular key
const result = { ...config, ...userInput };

// SAFE: use Object.create(null) for clean objects
const clean = Object.create(null); // no prototype chain
```

### Secondary defenses

```javascript
// Validate keys before merging
function safeMerge(target, source) {
    for (const key of Object.keys(source)) {
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
            continue; // skip dangerous keys
        }
        target[key] = source[key];
    }
}

// Use Map instead of plain objects for config
const config = new Map();
config.set('key', 'value'); // no prototype chain
```

### Tooling

- **Lodash**: update to >= 4.17.12 (patched `_.merge`)
- **Linter**: eslint-plugin-security detects `__proto__` usage
- **Sandbox**: use `Object.freeze(Object.prototype)` in sensitive contexts

## Interview Questions

**Q: Why does prototype pollution work in JavaScript?**
A: JavaScript uses prototype-based inheritance. The special `__proto__` property provides a writable reference to an object's prototype. If untrusted input reaches a recursive merge, `__proto__` as a key modifies `Object.prototype` instead of creating a regular property, affecting all objects in the runtime.

**Q: How can prototype pollution lead to RCE?**
A: If the application uses template engines (like Pug/EJS) or child process spawning, polluted prototype properties can inject template directives or alter command arguments. For example, polluting `Object.prototype.shell` to `/bin/sh` before a `child_process.exec` call can achieve remote code execution.

## References

- [Prototype Pollution — PortSwigger](https://portswigger.net/web-security/prototype-pollution)
- [CWE-1321: Improperly Controlled Modification of Object Prototype Attributes](https://cwe.mitre.org/data/definitions/1321.html)
- [Snyk — Prototype Pollution Research](https://snyk.io/research/prototype-pollution-in-nodejs/)
- See also: [Web Security](./web-security.md), [Authentication](./authentication.md), [Interview Questions](./interview-questions.md)
