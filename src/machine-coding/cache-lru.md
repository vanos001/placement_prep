# LRU Cache — Machine Coding Problem

## Problem Statement

Implement a Least Recently Used (LRU) Cache with O(1) time complexity for both `get` and `put` operations.

## Requirements

### Functional Requirements
1. `get(key)` — Return value if key exists, else -1. Mark as recently used.
2. `put(key, value)` — Insert or update key-value pair. If capacity exceeded, evict LRU item.
3. Configurable capacity
4. O(1) time for both operations

### Why LRU?
- CPU caches, page replacement in OS
- Database query caching
- CDN cache eviction
- Application-level caching (Redis, Memcached)

## Data Structure Design

The key insight: combine **HashMap** (O(1) lookup) with **Doubly Linked List** (O(1) insertion/deletion with order).

```
HashMap:  key → Node reference
Doubly Linked List: ordered by access time (most recent at head)

   head ←→ [A:3] ←→ [B:7] ←→ [C:1] ←→ [D:5] ←→ tail
              ↑most recent               ↑least recent

get(B) → move B to head:
   head ←→ [B:7] ←→ [A:3] ←→ [C:1] ←→ [D:5] ←→ tail

put(E, 9) → capacity exceeded, evict tail (D):
   head ←→ [E:9] ←→ [B:7] ←→ [A:3] ←→ [C:1] ←→ tail
```

## Class Diagram

```
┌──────────────────────────────────────────────┐
│                  LRUCache                     │
├──────────────────────────────────────────────┤
│ - capacity: int                              │
│ - cache: HashMap<K, Node<K,V>>               │
│ - head: Node (sentinel — most recent)        │
│ - tail: Node (sentinel — least recent)       │
├──────────────────────────────────────────────┤
│ + get(key): V or -1                          │
│ + put(key, value)                            │
│ - moveToHead(node)                           │
│ - removeNode(node)                           │
│ - addToHead(node)                            │
│ - removeTail(): Node                         │
│ + size(): int                                │
│ + display()                                  │
└──────────────────────────────────────────────┘
          │
          ▼
┌──────────────────────────────────────┐
│          Node<K, V>                  │
├──────────────────────────────────────┤
│ - key: K                             │
│ - value: V                           │
│ - prev: Node<K, V>                   │
│ - next: Node<K, V>                   │
└──────────────────────────────────────┘
```

## Implementation (Python)

### Using OrderedDict (Simple)

```python
from collections import OrderedDict


class LRUCacheSimple:
    """LRU Cache using Python's OrderedDict."""
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        self.capacity = capacity
        self.cache = OrderedDict()
    
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return self.cache[key]
    
    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            # Remove first item (least recently used)
            self.cache.popitem(last=False)
    
    def size(self) -> int:
        return len(self.cache)
    
    def display(self):
        items = list(self.cache.items())
        print(f"  Cache [{len(self.cache)}/{self.capacity}]: "
              f"{items}")
```

### From Scratch (Interview Version)

```python
class Node:
    """Doubly linked list node."""
    def __init__(self, key: int = 0, value: int = 0):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:
    """LRU Cache with O(1) get/put using HashMap + Doubly Linked List."""
    
    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self.capacity = capacity
        self.cache = {}  # key -> Node
        
        # Sentinel nodes to avoid edge cases
        self.head = Node()  # Most recent side
        self.tail = Node()  # Least recent side
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def _remove_node(self, node: Node):
        """Remove node from linked list."""
        node.prev.next = node.next
        node.next.prev = node.prev
    
    def _add_to_head(self, node: Node):
        """Add node right after head (most recent position)."""
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node
    
    def _move_to_head(self, node: Node):
        """Move existing node to head (mark as recently used)."""
        self._remove_node(node)
        self._add_to_head(node)
    
    def _pop_tail(self) -> Node:
        """Remove and return the least recently used node."""
        node = self.tail.prev
        self._remove_node(node)
        return node
    
    def get(self, key: int) -> int:
        """Get value by key. Returns -1 if not found."""
        if key not in self.cache:
            return -1
        
        node = self.cache[key]
        self._move_to_head(node)
        return node.value
    
    def put(self, key: int, value: int) -> None:
        """Put key-value pair. Evicts LRU if at capacity."""
        if key in self.cache:
            # Update existing
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            # Insert new
            node = Node(key, value)
            self.cache[key] = node
            self._add_to_head(node)
            
            if len(self.cache) > self.capacity:
                # Evict LRU
                lru = self._pop_tail()
                del self.cache[lru.key]
    
    def delete(self, key: int) -> bool:
        """Delete a key. Returns True if existed."""
        if key not in self.cache:
            return False
        node = self.cache.pop(key)
        self._remove_node(node)
        return True
    
    def size(self) -> int:
        return len(self.cache)
    
    def display(self):
        """Display cache contents from most to least recent."""
        current = self.head.next
        items = []
        while current != self.tail:
            items.append(f"{current.key}:{current.value}")
            current = current.next
        print(f"  Cache [{len(self.cache)}/{self.capacity}]: "
              f"{' ↔ '.join(items)}")


# ==================== Demo ====================

def main():
    print("=== LRU Cache Demo (capacity=3) ===\n")
    
    cache = LRUCache(3)
    
    # Insert 3 items
    cache.put(1, 10)
    cache.put(2, 20)
    cache.put(3, 30)
    cache.display()  # 3:30 ↔ 2:20 ↔ 1:10
    
    # Access 1 (moves to front)
    val = cache.get(1)
    print(f"\n  get(1) = {val}")
    cache.display()  # 1:10 ↔ 3:30 ↔ 2:20
    
    # Insert 4 (evicts 2 — LRU)
    cache.put(4, 40)
    print(f"\n  put(4, 40) — evicts LRU")
    cache.display()  # 4:40 ↔ 1:10 ↔ 3:30
    
    # Try to get evicted key
    val = cache.get(2)
    print(f"\n  get(2) = {val} (evicted)")
    
    # Update existing key
    cache.put(3, 300)
    print(f"\n  put(3, 300) — update")
    cache.display()  # 3:300 ↔ 4:40 ↔ 1:10
    
    print("\n=== Thread-Safe LRU Cache ===\n")


if __name__ == "__main__":
    main()
```

### Thread-Safe Version

```python
import threading
from typing import Optional


class ThreadSafeLRUCache:
    """Thread-safe LRU Cache using reentrant lock."""
    
    def __init__(self, capacity: int):
        self._cache = LRUCache(capacity)
        self._lock = threading.RLock()
    
    def get(self, key: int) -> int:
        with self._lock:
            return self._cache.get(key)
    
    def put(self, key: int, value: int) -> None:
        with self._lock:
            self._cache.put(key, value)
    
    def size(self) -> int:
        with self._lock:
            return self._cache.size()
```

### Generic Version (Python)

```python
from typing import TypeVar, Generic

K = TypeVar('K')
V = TypeVar('V')


class GenericNode(Generic[K, V]):
    def __init__(self, key: K = None, value: V = None):
        self.key = key
        self.value = value
        self.prev: Optional[GenericNode] = None
        self.next: Optional[GenericNode] = None


class LRUCacheGeneric(Generic[K, V]):
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.head = GenericNode()
        self.tail = GenericNode()
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def get(self, key: K) -> Optional[V]:
        if key not in self.cache:
            return None
        node = self.cache[key]
        self._move_to_head(node)
        return node.value
    
    def put(self, key: K, value: V) -> None:
        if key in self.cache:
            node = self.cache[key]
            node.value = value
            self._move_to_head(node)
        else:
            node = GenericNode(key, value)
            self.cache[key] = node
            self._add_to_head(node)
            if len(self.cache) > self.capacity:
                lru = self._pop_tail()
                del self.cache[lru.key]
    
    # ... helper methods same as above
```

## Java Implementation (Core)

```java
public class LRUCache<K, V> {
    private final int capacity;
    private final Map<K, Node<K, V>> cache;
    private final Node<K, V> head; // sentinel
    private final Node<K, V> tail; // sentinel
    
    public LRUCache(int capacity) {
        this.capacity = capacity;
        this.cache = new HashMap<>();
        this.head = new Node<>(null, null);
        this.tail = new Node<>(null, null);
        head.next = tail;
        tail.prev = head;
    }
    
    public V get(K key) {
        Node<K, V> node = cache.get(key);
        if (node == null) return null;
        moveToHead(node);
        return node.value;
    }
    
    public void put(K key, V value) {
        Node<K, V> node = cache.get(key);
        if (node != null) {
            node.value = value;
            moveToHead(node);
        } else {
            node = new Node<>(key, value);
            cache.put(key, node);
            addToHead(node);
            if (cache.size() > capacity) {
                Node<K, V> lru = removeTail();
                cache.remove(lru.key);
            }
        }
    }
    
    private void removeNode(Node<K, V> node) {
        node.prev.next = node.next;
        node.next.prev = node.prev;
    }
    
    private void addToHead(Node<K, V> node) {
        node.prev = head;
        node.next = head.next;
        head.next.prev = node;
        head.next = node;
    }
    
    private void moveToHead(Node<K, V> node) {
        removeNode(node);
        addToHead(node);
    }
    
    private Node<K, V> removeTail() {
        Node<K, V> node = tail.prev;
        removeNode(node);
        return node;
    }
    
    static class Node<K, V> {
        K key;
        V value;
        Node<K, V> prev, next;
        Node(K key, V value) {
            this.key = key;
            this.value = value;
        }
    }
}
```

## Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| get | O(1) | O(1) |
| put | O(1) | O(1) |
| Overall Space | — | O(capacity) |

## Variations

### LFU (Least Frequently Used)
- Evict the least frequently accessed item
- Needs frequency counter + min-heap or frequency buckets

### LRU-K
- Track last K accesses, not just the most recent
- More accurate but higher memory cost

### Size-Based LRU
- Items have different sizes
- Evict based on total size, not count

## Interview Follow-ups

1. **"How would you make this thread-safe?"**
   → ReentrantLock or synchronized blocks

2. **"How would you implement a distributed LRU cache?"**
   → Consistent hashing for partitioning, each node manages its own LRU

3. **"How would you handle cache stampede (thundering herd)?"**
   → Lock on miss, or probabilistic early expiration

4. **"How would you add TTL (time-to-live)?"**
   → Store expiration time in node, check on access

5. **"How would you implement LRU for a database buffer pool?"**
   → Clock algorithm (approximation), more efficient for hardware
