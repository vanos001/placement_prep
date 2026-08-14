# Memento Pattern

## Intent

Capture and externalize an object's internal state so the object can be restored to this state later, without violating encapsulation.

## Structure

| Component | Role |
|-----------|------|
| Originator | Creates and restores mementos |
| Memento | Stores the originator's internal state |
| Caretaker | Safeguards the memento (never peeks inside) |

## Implementation

```python
class EditorMemento:
    """Immutable snapshot of editor state."""
    def __init__(self, content, cursor):
        self._content = content
        self._cursor = cursor

    @property
    def content(self):
        return self._content

    @property
    def cursor(self):
        return self._cursor

class Editor:
    """Originator — creates and restores mementos."""
    def __init__(self):
        self._content = ''
        self._cursor = 0

    def type(self, text):
        self._content += text
        self._cursor += len(text)

    def save(self):
        return EditorMemento(self._content, self._cursor)

    def restore(self, memento: EditorMemento):
        self._content = memento.content
        self._cursor = memento.cursor

    @property
    def content(self):
        return self._content

class History:
    """Caretaker — manages undo/redo stack."""
    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    def push(self, memento):
        self._undo_stack.append(memento)
        self._redo_stack.clear()  # new action invalidates redo

    def undo(self):
        if self._undo_stack:
            m = self._undo_stack.pop()
            self._redo_stack.append(m)
            return m
        return None

    def redo(self):
        if self._redo_stack:
            m = self._redo_stack.pop()
            self._undo_stack.append(m)
            return m
        return None

# Usage
editor = Editor()
history = History()
editor.type('Hello')
history.push(editor.save())
editor.type(' World')
history.push(editor.save())
print(editor.content)  # 'Hello World'
editor.restore(history.undo())
print(editor.content)  # 'Hello'
```

## Command-Query Separation (CQS)

The memento pattern pairs naturally with CQS: commands (mutations) produce a memento before executing, enabling undo. Queries return data without side effects and are not undoable.

| Principle | Example |
|-----------|---------|
| Command | `editor.type(text)` — mutates state, push memento |
| Query | `editor.content` — returns value, no mutation |

## Interview Questions

**Q: How does the memento pattern preserve encapsulation?**
A: The caretaker only holds an opaque memento object. The originator creates and interprets the memento's contents. The caretaker never reads or modifies the internal state stored in the memento.

**Q: What's the memory cost of unlimited undo?**
A: Each memento stores a full state snapshot, so O(n × s) where n is the number of actions and s is the state size. Mitigations: store diffs instead of full snapshots, limit history depth, or use command pattern with inverse operations.

**Q: Memento vs Command pattern for undo?**
A: Memento snapshots state directly — simpler but memory-heavy. Command pattern stores operations and reverses them — more memory-efficient but requires implementing inverse operations for each command.

## References

- [Design Patterns — GoF](https://www.pearson.com/en-us/subject-catalog/p/design-patterns-elements-of-reusable-object-oriented-software/P200000003270)
- See also: [SOLID Deep Dive](./solid-deep-dive.md), [Structural & Behavioral Patterns](./design-patterns-structural-behavioral.md), [Creational Patterns](./design-patterns-creational.md)