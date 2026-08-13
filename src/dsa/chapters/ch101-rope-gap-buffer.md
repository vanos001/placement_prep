# Chapter 101: Rope and Gap Buffer

## Prerequisites
- Binary trees, strings, arrays
- Understanding of text editor internals

## Interview Frequency: ★

Rope and Gap Buffer are data structures designed for efficient text editing. While rarely asked directly in interviews, they demonstrate systems thinking and are common in discussions about text editors, collaborative editing, and string processing at scale.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Rope | ★ | Medium | Tree-based string for large text |
| Gap Buffer | ★ | Medium | Array with movable gap for editors |
| Piece Table | ★ | Medium | Used in VS Code, Word |
| Comparison | ★ | Medium | When to use which |

---

## 101.1 Motivation: Why Not Just Use a String?

Consider a text editor with a million characters. A naive string/array has these problems:

| Operation | String/Array | Why It's Bad |
|---|---|---|
| Insert at position i | O(n) | Shift all characters after i |
| Delete at position i | O(n) | Shift all characters after i |
| Concatenate two files | O(n + m) | Copy entire content |
| Split file at position | O(n) | Copy both halves |

For a user typing at position 1000 in a 1MB file, every keystroke copies ~1MB. At 100 WPM (~8 chars/sec), that's 8MB/sec of copying for typing alone!

**Key insight**: Text editing has a strong **locality pattern** — most operations happen near the cursor. Data structures exploit this.

---

## 101.2 Rope

### Definition

A **rope** is a binary tree where:
- **Leaf nodes** store short string fragments (typically 8-64 characters)
- **Internal nodes** store the **weight** = total length of all text in the left subtree
- The in-order traversal of leaves concatenates to form the full string

### Intuition

Think of a rope as a "divide and conquer" representation of a string. Instead of one long array, we have many small pieces organized in a tree. Operations like split and concatenate just rearrange tree nodes — no copying of actual text.

### Weight Property

For any internal node N with left child L and right child R:
```
N.weight = total characters in L's subtree
```

This allows O(log n) character access: at each node, compare the index with weight to decide whether to go left or right.

---

## 101.3 Rope Operations

### Character Access: O(log n)

To find character at index `i`:
1. Start at root
2. If i < node.weight → go left
3. If i ≥ node.weight → go right with index (i - node.weight)
4. At leaf, return data[i]

**Walkthrough**: Access index 7 in "Hello, World!"

```
        [weight=7]
       /          \
   "Hello, "    "World!"
   
Index 7 ≥ weight 7 → go right with index 7-7=0
At leaf "World!" → return 'W'
```

### Concatenation: O(log n)

To concatenate ropes A and B:
1. Create new root node
2. Set left = A, right = B
3. Weight = size of A's total text

No text is copied — just a new root node.

### Split: O(log n)

To split rope at index `i`:
1. Walk down to find the split point
2. If split point is inside a leaf, split the leaf's string
3. Reconstruct two new ropes from the left and right parts

### Insert: O(log n)

Insert string `s` at position `i`:
1. Split rope at position `i` → left part and right part
2. Create new rope from `s`
3. Concatenate: left + new + right

### Delete: O(log n)

Delete characters from position `i` to `j`:
1. Split at `i` → left and rest
2. Split rest at `j - i` → middle and right
3. Discard middle
4. Concatenate left + right

---

## 101.4 Gap Buffer

### Definition

A **gap buffer** is a single array with a "gap" (empty space) at the cursor position. Text before the gap is at the start; text after the gap is at the end.

```
Array: [H e l l o _ _ _ _ _ W o r l d !]
             ↑         ↑
         gapStart    gapEnd
         
Represents: "Hello World!" with cursor after 'o'
```

### Intuition

Imagine a physical bookshelf with books and an empty space. To insert a book at the gap, just put it there. To move the gap, slide books one by one. The gap acts as an "insertion buffer."

### Key Insight

Most text editing happens at the cursor. If the gap is at the cursor:
- **Insert**: O(1) — write into gap, move gapStart forward
- **Delete**: O(1) — move gapEnd forward (expand gap)
- **Move cursor**: O(n) worst case — shift gap to new position

The amortized cost is excellent for sequential editing (typing, backspacing).

---

## 101.5 Gap Buffer Operations

### Insert Character: O(1) amortized

```
Before: [H e l l o _ _ _ _ _ W o r l d !]
                   ↑
Insert ' ':        [H e l l o ' ' _ _ _ _ W o r l d !]
                         ↑
```

1. Write character at gapStart
2. Increment gapStart

### Delete Character: O(1)

```
Before: [H e l l o ' ' _ _ _ _ W o r l d !]
                          ↑
Delete:  [H e l l o _ _ _ _ _ _ W o r l d !]
                       ↑
```

1. Decrement gapStart (expand gap left)

### Move Gap: O(n) worst, O(1) amortized

To move gap to position `p`:
```
If p < gapStart:  shift characters [p, gapStart) right
If p > gapStart:  shift characters [gapEnd, p+gapSize) left
```

### Gap Resize

When the gap is full and we need to insert:
1. Allocate larger array (typically 2× size)
2. Copy text before gap
3. Copy text after gap (at end of new array)
4. Set new gap boundaries

---

## 101.6 Step-by-Step Walkthrough

### Example: Typing "Hello World" with Gap Buffer

Initial capacity = 20, gap = entire buffer.

```
Step 1: Type 'H'
[_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _]
 ↑
 gap (size 19)
 
Buffer: "H"

Step 2: Type 'e', 'l', 'l', 'o'
[H e l l o _ _ _ _ _ _ _ _ _ _ _ _ _ _ _]
           ↑
           gap (size 15)

Buffer: "Hello"

Step 3: Type ' ' (space)
[H e l l o ' ' _ _ _ _ _ _ _ _ _ _ _ _ _ _]
               ↑
               gap (size 14)

Buffer: "Hello "

Step 4-10: Type 'W', 'o', 'r', 'l', 'd', '!'
[H e l l o ' ' W o r l d ! _ _ _ _ _ _ _ _]
                                ↑
                                gap (size 8)

Buffer: "Hello World!"

Step 11: Move cursor to position 5 (after 'o')
Gap shifts to position 5:
[H e l l o _ _ _ _ _ _ _ _ ' ' W o r l d !]
           ↑                             ↑
         gapStart                      gapEnd
         
Buffer: "Hello World!" (unchanged, just gap moved)

Step 12: Insert '!' at cursor
[H e l l o ! _ _ _ _ _ _ _ _ ' ' W o r l d !]
             ↑
Buffer: "Hello! World!"
```

---

## 101.7 Dry Run: Rope Concatenation

Create ropes for "Hello" and "World" and concatenate:

```
Rope A:          [weight=5]
                /         \
            "Hello"       null

Rope B:          [weight=5]
                /         \
            "World"       null

Concatenate A + B:

Result:          [weight=5]
                /         \
            [weight=5]   [weight=5]
            /      \      /      \
        "Hello"  null  "World"  null

In-order traversal: "Hello" + "World" = "HelloWorld"
```

### Access index 3 in "HelloWorld":

```
Root: weight=5, index=3 < 5 → go left
Left child: weight=5, index=3 < 5 → go left
Leaf "Hello": return "Hello"[3] = 'l'
```

### Access index 7 in "HelloWorld":

```
Root: weight=5, index=7 ≥ 5 → go right, index = 7-5 = 2
Right child: weight=5, index=2 < 5 → go left
Leaf "World": return "World"[2] = 'r'
```

---

## 101.8 Complexity Analysis

### Rope

| Operation | Time | Space | Notes |
|---|---|---|---|
| Access char at index | O(log n) | O(1) | Tree traversal |
| Insert string at index | O(log n) | O(m) | Split + concat |
| Delete range [i, j] | O(log n) | O(1) | Split + discard + concat |
| Concatenate two ropes | O(log n) | O(1) | New root node |
| Split at index | O(log n) | O(log n) | Rebuild path |
| Convert to string | O(n) | O(n) | In-order traversal |
| Substring [i, j] | O(log n + k) | O(k) | Split, extract, rejoin |

where n = total characters, m = inserted string length, k = substring length.

### Gap Buffer

| Operation | Time | Notes |
|---|---|---|
| Insert at cursor | O(1) amortized | Write into gap |
| Delete at cursor | O(1) | Expand gap |
| Move cursor to position | O(n) worst | Shift gap |
| Get text | O(n) | Concatenate parts |
| Resize | O(n) | Allocate + copy |

### Space Comparison

| Structure | Overhead | Fragmentation |
|---|---|---|
| Rope | O(n) for tree nodes | Low (balanced tree) |
| Gap Buffer | O(n) for gap space | Low (single array) |
| Piece Table | O(m) for pieces | Very low |
| String/Array | 0 | None |

---

## 101.9 Code: Complete Implementations

### C++: Rope

```cpp
#include <iostream>
#include <string>
#include <memory>
#include <cassert>

struct RopeNode {
    std::string data;    // Only non-empty for leaves
    int weight;          // Size of left subtree's text
    std::shared_ptr<RopeNode> left, right;

    RopeNode(const std::string& s) : data(s), weight(s.size()), left(nullptr), right(nullptr) {}
    RopeNode(std::shared_ptr<RopeNode> l, std::shared_ptr<RopeNode> r)
        : weight(l ? l->totalSize() : 0), left(l), right(r) {}

    bool isLeaf() const { return !left && !right; }

    int totalSize() const {
        if (isLeaf()) return data.size();
        int rsize = right ? right->totalSize() : 0;
        return weight + rsize;
    }
};

class Rope {
    std::shared_ptr<RopeNode> root;

public:
    Rope() : root(nullptr) {}
    Rope(const std::string& s) : root(std::make_shared<RopeNode>(s)) {}
    Rope(std::shared_ptr<RopeNode> node) : root(node) {}

    int size() const { return root ? root->totalSize() : 0; }
    bool empty() const { return !root || root->totalSize() == 0; }

    // Access character at index
    char charAt(int index) const {
        assert(root && index >= 0 && index < size());
        auto node = root;
        while (!node->isLeaf()) {
            if (index < node->weight) {
                node = node->left;
            } else {
                index -= node->weight;
                node = node->right;
            }
        }
        return node->data[index];
    }

    // Concatenate two ropes
    static Rope concat(const Rope& a, const Rope& b) {
        if (a.empty()) return b;
        if (b.empty()) return a;
        return Rope(std::make_shared<RopeNode>(a.root, b.root));
    }

    // Split rope at index: returns {left, right}
    static std::pair<Rope, Rope> split(const Rope& r, int index) {
        if (!r.root || index <= 0) return {Rope(), r};
        if (index >= r.size()) return {r, Rope()};
        return splitHelper(r.root, index);
    }

    // Insert string at position
    static Rope insert(const Rope& r, int pos, const std::string& s) {
        auto [left, right] = split(r, pos);
        Rope newRope(s);
        return concat(concat(left, newRope), right);
    }

    // Delete range [from, to)
    static Rope remove(const Rope& r, int from, int to) {
        auto [left, rest] = split(r, from);
        auto [_, right] = split(rest, to - from);
        return concat(left, right);
    }

    // Extract substring [from, to)
    std::string substring(int from, int to) const {
        auto [left, rest] = split(*this, from);
        auto [mid, right] = split(rest, to - from);
        return mid.toString();
    }

    // Convert to string
    std::string toString() const {
        if (!root) return "";
        std::string result;
        toStringHelper(root, result);
        return result;
    }

private:
    static std::pair<Rope, Rope> splitHelper(std::shared_ptr<RopeNode> node, int index) {
        if (node->isLeaf()) {
            auto left = std::make_shared<RopeNode>(node->data.substr(0, index));
            auto right = std::make_shared<RopeNode>(node->data.substr(index));
            return {Rope(left), Rope(right)};
        }

        if (index < node->weight) {
            auto [ll, lr] = splitHelper(node->left, index);
            return {ll, concat(lr, Rope(node->right))};
        } else {
            auto [rl, rr] = splitHelper(node->right, index - node->weight);
            return {concat(Rope(node->left), rl), rr};
        }
    }

    static void toStringHelper(std::shared_ptr<RopeNode> node, std::string& result) {
        if (!node) return;
        if (node->isLeaf()) {
            result += node->data;
        } else {
            toStringHelper(node->left, result);
            toStringHelper(node->right, result);
        }
    }
};

int main() {
    // Create ropes
    Rope a("Hello, ");
    Rope b("World!");
    Rope c = Rope::concat(a, b);
    std::cout << "Concatenated: " << c.toString() << "\n";

    // Access characters
    for (int i = 0; i < c.size(); i++)
        std::cout << c.charAt(i);
    std::cout << "\n";

    // Insert
    Rope d = Rope::insert(c, 5, " Beautiful");
    std::cout << "After insert: " << d.toString() << "\n";

    // Delete
    Rope e = Rope::remove(d, 5, 15);
    std::cout << "After delete: " << e.toString() << "\n";

    // Substring
    std::cout << "Substring [0, 5]: " << c.substring(0, 5) << "\n";

    return 0;
}
```

### C++: Gap Buffer

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cassert>

class GapBuffer {
    std::vector<char> buffer;
    int gapStart, gapEnd;

    void resize(int newCapacity) {
        std::vector<char> newBuf(newCapacity, '\0');
        int gapSize = gapEnd - gapStart;
        int rightSize = (int)buffer.size() - gapEnd;

        // Copy left part
        for (int i = 0; i < gapStart; i++)
            newBuf[i] = buffer[i];

        // Copy right part (at end of new buffer)
        int newGapEnd = newCapacity - rightSize;
        for (int i = 0; i < rightSize; i++)
            newBuf[newGapEnd + i] = buffer[gapEnd + i];

        buffer = newBuf;
        gapEnd = newGapEnd;
    }

public:
    GapBuffer(int capacity = 64) : buffer(capacity, '\0'), gapStart(0), gapEnd(capacity) {}

    int totalSize() const { return (int)buffer.size(); }
    int textSize() const { return totalSize() - (gapEnd - gapStart); }
    int gapSize() const { return gapEnd - gapStart; }
    int cursorPos() const { return gapStart; }

    // Move gap to position
    void moveGap(int position) {
        assert(position >= 0 && position <= textSize());

        if (position == gapStart) return;

        if (position < gapStart) {
            // Shift characters right
            int shift = gapStart - position;
            for (int i = 0; i < shift; i++) {
                buffer[gapEnd - shift + i] = buffer[position + i];
            }
            gapStart -= shift;
            gapEnd -= shift;
        } else {
            // Shift characters left
            int shift = position - gapStart;
            for (int i = 0; i < shift; i++) {
                buffer[gapStart + i] = buffer[gapEnd + i];
            }
            gapStart += shift;
            gapEnd += shift;
        }
    }

    // Insert character at cursor
    void insert(char c) {
        if (gapSize() <= 1) {
            resize(totalSize() * 2);
        }
        buffer[gapStart++] = c;
    }

    // Insert string at cursor
    void insertString(const std::string& s) {
        for (char c : s) insert(c);
    }

    // Delete character before cursor (backspace)
    void deleteBefore() {
        if (gapStart > 0) gapStart--;
    }

    // Delete character at cursor
    void deleteAt() {
        if (gapEnd < totalSize()) gapEnd++;
    }

    // Get the full text
    std::string getText() const {
        std::string result;
        result.reserve(textSize());
        for (int i = 0; i < gapStart; i++)
            result += buffer[i];
        for (int i = gapEnd; i < totalSize(); i++)
            result += buffer[i];
        return result;
    }

    // Debug: show internal state
    void debug() const {
        std::cout << "Buffer (size=" << totalSize() << ", gap=["
                  << gapStart << "," << gapEnd << "]): ";
        for (int i = 0; i < totalSize(); i++) {
            if (i == gapStart) std::cout << "[";
            if (i >= gapStart && i < gapEnd) std::cout << "_";
            else std::cout << buffer[i];
            if (i == gapEnd - 1) std::cout << "]";
        }
        std::cout << "\n";
    }
};

int main() {
    GapBuffer gb(20);

    // Type "Hello World"
    gb.insertString("Hello World");
    std::cout << "After typing: " << gb.getText() << "\n";
    gb.debug();

    // Move cursor to position 5
    gb.moveGap(5);
    std::cout << "Cursor at 5: " << gb.getText() << "\n";
    gb.debug();

    // Insert " Beautiful" at cursor
    gb.insertString(" Beautiful");
    std::cout << "After insert: " << gb.getText() << "\n";
    gb.debug();

    // Backspace
    gb.moveGap(gb.textSize());
    gb.deleteBefore();
    gb.deleteBefore();
    std::cout << "After backspace: " << gb.getText() << "\n";

    return 0;
}
```

### Python: Rope

```python
class RopeNode:
    def __init__(self, data=None, left=None, right=None):
        self.data = data or ""
        self.left = left
        self.right = right
        self._update_weight()

    def _update_weight(self):
        if self.left and not self.data:
            self.weight = self.left.total_size()
        else:
            self.weight = len(self.data)

    def is_leaf(self):
        return self.left is None and self.right is None

    def total_size(self):
        if self.is_leaf():
            return len(self.data)
        rsize = self.right.total_size() if self.right else 0
        return self.weight + rsize


class Rope:
    def __init__(self, s=""):
        if isinstance(s, RopeNode):
            self.root = s
        elif s:
            self.root = RopeNode(data=s)
        else:
            self.root = None

    def size(self):
        return self.root.total_size() if self.root else 0

    def __len__(self):
        return self.size()

    def char_at(self, index):
        """Access character at index. O(log n)"""
        assert self.root and 0 <= index < self.size()
        node = self.root
        while not node.is_leaf():
            if index < node.weight:
                node = node.left
            else:
                index -= node.weight
                node = node.right
        return node.data[index]

    def __getitem__(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(self.size())
            return "".join(self.char_at(i) for i in range(start, stop, step))
        return self.char_at(index)

    @staticmethod
    def concat(a, b):
        """Concatenate two ropes. O(log n)"""
        if not a.root:
            return b
        if not b.root:
            return a
        new_node = RopeNode(left=a.root, right=b.root)
        return Rope(new_node)

    def __add__(self, other):
        return Rope.concat(self, other)

    @staticmethod
    def split(r, index):
        """Split rope at index. Returns (left, right). O(log n)"""
        if not r.root or index <= 0:
            return Rope(), r
        if index >= r.size():
            return r, Rope()
        return Rope._split_helper(r.root, index)

    @staticmethod
    def _split_helper(node, index):
        if node.is_leaf():
            left = RopeNode(data=node.data[:index])
            right = RopeNode(data=node.data[index:])
            return Rope(left), Rope(right)

        if index < node.weight:
            ll, lr = Rope._split_helper(node.left, index)
            return ll, Rope.concat(lr, Rope(node.right))
        else:
            rl, rr = Rope._split_helper(node.right, index - node.weight)
            return Rope.concat(Rope(node.left), rl), rr

    def insert(self, pos, s):
        """Insert string at position. O(log n + len(s))"""
        left, right = Rope.split(self, pos)
        new = Rope(s)
        return Rope.concat(Rope.concat(left, new), right)

    def delete(self, fr, to):
        """Delete range [fr, to). O(log n)"""
        left, rest = Rope.split(self, fr)
        _, right = Rope.split(rest, to - fr)
        return Rope.concat(left, right)

    def to_string(self):
        """Convert to string. O(n)"""
        if not self.root:
            return ""
        parts = []
        self._to_string_helper(self.root, parts)
        return "".join(parts)

    def _to_string_helper(self, node, parts):
        if not node:
            return
        if node.is_leaf():
            parts.append(node.data)
        else:
            self._to_string_helper(node.left, parts)
            self._to_string_helper(node.right, parts)

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return f"Rope({self.to_string()!r})"


def demo():
    # Create and concatenate
    a = Rope("Hello, ")
    b = Rope("World!")
    c = a + b
    print(f"Concatenated: {c}")
    print(f"Length: {len(c)}")

    # Character access
    print(f"char_at(0) = '{c.char_at(0)}'")
    print(f"char_at(7) = '{c.char_at(7)}'")
    print(f"c[0:5] = '{c[0:5]}'")

    # Insert
    d = c.insert(7, "Beautiful ")
    print(f"After insert: {d}")

    # Delete
    e = d.delete(7, 17)
    print(f"After delete: {e}")

    # Large rope test
    r = Rope("A" * 100)
    for i in range(10):
        r = r + Rope("B" * 100)
    print(f"Large rope size: {len(r)}")


if __name__ == "__main__":
    demo()
```

### Java: Gap Buffer

```java
public class GapBuffer {
    private char[] buffer;
    private int gapStart, gapEnd;

    public GapBuffer(int capacity) {
        buffer = new char[capacity];
        gapStart = 0;
        gapEnd = capacity;
    }

    public int textSize() {
        return buffer.length - (gapEnd - gapStart);
    }

    public int cursorPos() {
        return gapStart;
    }

    private void resize(int newCapacity) {
        char[] newBuf = new char[newCapacity];
        int rightSize = buffer.length - gapEnd;

        System.arraycopy(buffer, 0, newBuf, 0, gapStart);
        int newGapEnd = newCapacity - rightSize;
        System.arraycopy(buffer, gapEnd, newBuf, newGapEnd, rightSize);

        buffer = newBuf;
        gapEnd = newGapEnd;
    }

    public void moveGap(int position) {
        if (position == gapStart) return;

        if (position < gapStart) {
            int shift = gapStart - position;
            System.arraycopy(buffer, position, buffer, gapEnd - shift, shift);
            gapStart -= shift;
            gapEnd -= shift;
        } else {
            int shift = position - gapStart;
            System.arraycopy(buffer, gapEnd, buffer, gapStart, shift);
            gapStart += shift;
            gapEnd += shift;
        }
    }

    public void insert(char c) {
        if (gapEnd - gapStart <= 1) {
            resize(buffer.length * 2);
        }
        buffer[gapStart++] = c;
    }

    public void insertString(String s) {
        for (char c : s.toCharArray()) insert(c);
    }

    public void deleteBefore() {
        if (gapStart > 0) gapStart--;
    }

    public void deleteAt() {
        if (gapEnd < buffer.length) gapEnd++;
    }

    public String getText() {
        StringBuilder sb = new StringBuilder(textSize());
        for (int i = 0; i < gapStart; i++) sb.append(buffer[i]);
        for (int i = gapEnd; i < buffer.length; i++) sb.append(buffer[i]);
        return sb.toString();
    }

    public void debug() {
        System.out.print("Buffer [");
        for (int i = 0; i < buffer.length; i++) {
            if (i == gapStart) System.out.print("[");
            if (i >= gapStart && i < gapEnd) System.out.print("_");
            else System.out.print(buffer[i]);
            if (i == gapEnd - 1) System.out.print("]");
        }
        System.out.println("]");
    }

    public static void main(String[] args) {
        GapBuffer gb = new GapBuffer(20);

        gb.insertString("Hello World");
        System.out.println("Text: " + gb.getText());
        gb.debug();

        gb.moveGap(5);
        System.out.println("After moveGap(5): " + gb.getText());
        gb.debug();

        gb.insertString(" Beautiful");
        System.out.println("After insert: " + gb.getText());

        gb.moveGap(gb.textSize());
        gb.deleteBefore();
        gb.deleteBefore();
        System.out.println("After backspace: " + gb.getText());
    }
}
```

---

## 101.10 Piece Table (Bonus)

A **piece table** is a third text editing structure used in VS Code and Microsoft Word.

### Concept

- **Original buffer**: immutable, holds the original file content
- **Add buffer**: append-only, holds inserted text
- **Piece table**: list of (buffer, start, length) tuples describing the logical text

```
Original: "Hello World"
Add buffer: "Beautiful " (inserted)

Piece table:
  [(orig, 0, 5),    // "Hello"
   (add, 0, 10),    // "Beautiful "
   (orig, 5, 6)]    // " World"

Result: "Hello Beautiful World"
```

### Advantages
- **Undo**: just remove the last piece entry
- **Memory**: only stores deltas
- **Fast inserts**: append to add buffer + update piece list

---

## 101.11 When to Use Which

| Scenario | Best Choice | Why |
|---|---|---|
| Simple text editor | Gap Buffer | O(1) insert at cursor, simple |
| Large file editing | Rope | O(log n) all operations |
| Collaborative editing | CRDT / Piece Table | Merge-friendly |
| Read-heavy, rare edits | String | Simple, cache-friendly |
| Undo/redo support | Piece Table | Easy history |
| Syntax highlighting | Rope | Efficient substrings |

---

## 101.12 Exercises

### Conceptual Exercises

1. **Explain** why a rope's character access is O(log n) and not O(1). What property of the tree structure enables this?

2. **Compare** the space overhead of rope vs gap buffer for a 1GB text file. Which uses more memory and why?

3. **Prove** that rope concatenation is O(log n) when both ropes are balanced.

4. **Analyze** the amortized cost of typing 1000 characters with a gap buffer starting with gap size 100.

### Coding Exercises

5. **Implement** a rope that supports `find(pattern)` — searching for a substring. What is the time complexity?

6. **Extend** the gap buffer to support undo/redo using a command stack.

7. **Implement** a piece table with `insert`, `delete`, and `getText` operations.

8. **Build** a simple text editor that uses a rope as its backing store and supports basic operations (insert, delete, cursor movement, display).

### Challenge Exercises

9. **Implement** a persistent rope (all versions are preserved) using path copying.

10. **Design** a concurrent rope that supports multiple simultaneous editors (hint: use fine-grained locking or lock-free techniques).

---

## 101.13 Interview Questions

### Conceptual Questions

1. **Q**: Why would you choose a rope over a gap buffer for a collaborative text editor?
   **A**: Ropes support efficient split and merge operations needed for OT/CRDT. Gap buffers require O(n) to merge content from different editors.

2. **Q**: What's the worst case for gap buffer and when does it occur?
   **A**: O(n) per operation when cursor jumps randomly across the file. Amortized O(1) for sequential editing.

3. **Q**: How does a piece table support undo?
   **A**: Each edit adds a piece. Undo removes the last piece. No text is ever modified or deleted from the buffers.

### Implementation Questions

4. **Q**: How would you handle very long lines in a rope-based editor?
   **A**: Break leaf nodes at line boundaries. Each leaf holds one line. This makes line-based operations (syntax highlighting, line numbers) efficient.

5. **Q**: Gap buffer is full and cursor is at position 0. How do you insert a character?
   **A**: Resize the buffer (allocate 2× capacity), copy left part (empty) and right part (all text), then insert at gapStart.

### Systems Questions

6. **Q**: VS Code uses a piece table internally. Why not a rope?
   **A**: Piece tables are simpler to implement, support efficient undo, and have excellent cache locality for sequential access. The append-only buffers are memory-mapped friendly.

---

## 101.14 Cross-References

- **Chapter 13 (Arrays and Strings)**: Basic string operations and their complexities
- **Chapter 15 (Binary Trees)**: Tree structure underlying ropes
- **Chapter 16 (Balanced BSTs)**: AVL/Red-black trees for balanced ropes
- **Chapter 102 (Tries)**: Another tree-based string structure
- **Chapter 104 (Segment Trees)**: Similar augmented tree concept
- **Chapter 105 (Fenwick Trees)**: Prefix sum augmentation

---

## Summary

| Structure | Insert at cursor | Move cursor | Concatenate | Split | Best for |
|---|---|---|---|---|---|
| String/Array | O(n) | O(1) | O(n+m) | O(n) | Small text |
| Gap Buffer | O(1) amortized | O(n) worst | N/A | N/A | Simple editors |
| Rope | O(log n) | O(log n) | O(log n) | O(log n) | Large text |
| Piece Table | O(1) | O(1) | O(1) | O(1) | Undo/redo |

**Key Takeaway**: Text editing data structures exploit locality (gap buffer) or tree decomposition (rope) to achieve efficient editing operations. The choice depends on the use case: gap buffers for simple sequential editing, ropes for complex operations on large texts, and piece tables for undo-heavy applications.
