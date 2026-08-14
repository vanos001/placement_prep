# Flyweight Pattern

## Intent

Use sharing to support large numbers of fine-grained objects efficiently. Minimize memory usage by sharing common state (intrinsic) across objects while keeping unique state (extrinsic) separate.

## Intrinsic vs Extrinsic State

| Aspect | Intrinsic State | Extrinsic State |
|--------|----------------|-----------------|
| Shared? | Yes — stored in the flyweight | No — passed by the client |
| Independent of context? | Yes | No |
| Memory impact | Amortized across all users | Per-object |
| Example | Tree species (name, color, texture) | Position, size of each tree instance |

## Implementation

```python
class TreeStyle:
    """Intrinsic state — shared across all trees of the same species."""
    def __init__(self, name, color, texture):
        self.name = name
        self.color = color
        self.texture = texture

class TreeFactory:
    """Flyweight factory — ensures sharing."""
    _styles = {}

    @classmethod
    def get_style(cls, name, color, texture):
        key = (name, color, texture)
        if key not in cls._styles:
            cls._styles[key] = TreeStyle(name, color, texture)
        return cls._styles[key]

    @classmethod
    def style_count(cls):
        return len(cls._styles)

class Tree:
    """Extrinsic state — unique per tree instance."""
    def __init__(self, x, y, style: TreeStyle):
        self.x = x
        self.y = y
        self.style = style

    def draw(self):
        print(f'{self.style.name} at ({self.x},{self.y})')

# 10,000 trees but only 3 shared styles
styles = [('Oak', 'green', 'rough'), ('Pine', 'dark green', 'smooth'), ('Birch', 'white', 'peeling')]
trees = []
for i in range(10000):
    s = styles[i % 3]
    style = TreeFactory.get_style(*s)
    trees.append(Tree(i % 500, i // 500, style))

print(f'Styles created: {TreeFactory.style_count()}')  # 3, not 10000
```

## String Interning

Python and Java automatically intern short strings — identical string literals share the same object. This is a built-in flyweight optimization.

```python
a = "hello"
b = "hello"
print(a is b)  # True — same object (interned)
```

## When to Use

- A large number of objects consume significant memory.
- Most object state can be made extrinsic.
- The application doesn't depend on object identity (shared references are fine).

## Interview Questions

**Q: What's the difference between intrinsic and extrinsic state?**
A: Intrinsic state is shared and context-independent (stored in the flyweight). Extrinsic state is unique per instance and passed in by the client at use time. Only intrinsic state is stored in the shared pool.

**Q: When is flyweight inappropriate?**
A: When objects have mostly unique state (little to share), when object identity matters (e.g., identity maps), or when the overhead of the factory and extrinsic parameter passing exceeds the memory savings.

**Q: How does string interning relate to the flyweight pattern?**
A: String interning is a specific application of the flyweight pattern. The runtime maintains a pool of unique strings; identical literals map to the same object, saving memory and enabling O(1) equality checks via reference comparison.

## References

- [Design Patterns — GoF](https://www.pearson.com/en-us/subject-catalog/p/design-patterns-elements-of-reusable-object-oriented-software/P200000003270)
- See also: [SOLID Deep Dive](./solid-deep-dive.md), [Creational Patterns](./design-patterns-creational.md), [Structural & Behavioral Patterns](./design-patterns-structural-behavioral.md)
