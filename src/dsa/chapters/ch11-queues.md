# Chapter 11: Queues

The queue is the natural counterpart to the stack. While a stack follows LIFO (Last In, First Out), a queue follows **FIFO (First In, First Out)** — the first element added is the first to be removed. Queues are fundamental to breadth-first search, scheduling algorithms, and buffering systems. Understanding queues, including their variants like circular queues, deques, and priority queues, is essential for interviews.

---

## 11.1 Queue Fundamentals

### What Is a Queue?

A **queue** is a linear data structure that operates on the **First In, First Out (FIFO)** principle. Think of a line at a grocery store: the first person to join the line is the first to be served.

### Core Operations

| Operation | Description | Time Complexity |
|-----------|-------------|-----------------|
| `enqueue(item)` | Add an element to the back | O(1) |
| `dequeue()` | Remove the front element | O(1) |
| `front()` | View the front element without removing | O(1) |
| `back()` | View the back element without removing | O(1) |
| `empty()` | Check if the queue is empty | O(1) |
| `size()` | Return the number of elements | O(1) |

### Queue vs. Stack

| Feature | Stack | Queue |
|---------|-------|-------|
| Principle | LIFO | FIFO |
| Insert at | Top | Back |
| Remove from | Top | Front |
| Use case | Undo, DFS, parsing | BFS, scheduling, buffering |

---

## 11.2 Circular Queue

### The Problem with Simple Array Implementation

A naive array-based queue has a problem: after several enqueue and dequeue operations, the front of the queue drifts forward, wasting space at the beginning of the array.

```
Initial:  [_, _, _, _, _]
          front=0, back=-1

After enqueue(1), enqueue(2), enqueue(3):
          [1, 2, 3, _, _]
          front=0, back=2

After dequeue() twice:
          [_, _, 3, _, _]
          front=2, back=2

Now enqueue(4), enqueue(5):
          [_, _, 3, 4, 5]
          front=2, back=4

Queue is "full" even though positions 0 and 1 are empty!
```

### Circular Queue Solution

A **circular queue** treats the array as a circle — when the back reaches the end, it wraps around to the beginning.

```cpp
#include <iostream>
#include <stdexcept>

class CircularQueue {
    int* data;
    int capacity;
    int frontIndex;
    int backIndex;
    int count;

public:
    CircularQueue(int cap) : capacity(cap), frontIndex(0), backIndex(-1), count(0) {
        data = new int[capacity];
    }
    
    ~CircularQueue() { delete[] data; }
    
    // Disable copy for simplicity
    CircularQueue(const CircularQueue&) = delete;
    CircularQueue& operator=(const CircularQueue&) = delete;

    void enqueue(int item) {
        if (full()) {
            throw std::overflow_error("Queue is full");
        }
        backIndex = (backIndex + 1) % capacity;
        data[backIndex] = item;
        ++count;
    }

    int dequeue() {
        if (empty()) {
            throw std::underflow_error("Queue is empty");
        }
        int item = data[frontIndex];
        frontIndex = (frontIndex + 1) % capacity;
        --count;
        return item;
    }

    int front() const {
        if (empty()) throw std::underflow_error("Queue is empty");
        return data[frontIndex];
    }

    int back() const {
        if (empty()) throw std::underflow_error("Queue is empty");
        return data[backIndex];
    }

    bool empty() const { return count == 0; }
    bool full() const { return count == capacity; }
    int size() const { return count; }
};

int main() {
    CircularQueue q(5);
    
    q.enqueue(1);
    q.enqueue(2);
    q.enqueue(3);
    std::cout << "Front: " << q.front() << "\n"; // 1
    
    q.dequeue();
    q.dequeue();
    std::cout << "Front: " << q.front() << "\n"; // 3
    
    q.enqueue(4);
    q.enqueue(5);
    q.enqueue(6);
    q.enqueue(7);
    std::cout << "Size: " << q.size() << "\n"; // 5
    
    while (!q.empty()) {
        std::cout << q.dequeue() << " ";
    }
    std::cout << "\n";
    // Output: 3 4 5 6 7
    return 0;
}
```

**Wrap-around visualization:**

```
Capacity = 5

After enqueue(1,2,3), dequeue() x2, enqueue(4,5,6,7):

Index:  0   1   2   3   4
Data:   6   7   3   4   5
                ^front  ^back

frontIndex = 2
backIndex = 1  (wrapped around!)
```

### STL Implementation

```cpp
#include <iostream>
#include <queue>

int main() {
    std::queue<int> q;
    
    q.push(10);
    q.push(20);
    q.push(30);
    
    std::cout << "Front: " << q.front() << "\n"; // 10
    std::cout << "Back: " << q.back() << "\n";   // 30
    
    q.pop();
    std::cout << "Front: " << q.front() << "\n"; // 20
    std::cout << "Size: " << q.size() << "\n";   // 2
    
    return 0;
}
```

---

## 11.3 Deque (Double-Ended Queue)

### What Is a Deque?

A **deque** (pronounced "deck") is a generalized queue that allows insertion and deletion at **both ends** in O(1) time.

### Operations

| Operation | Description | Time |
|-----------|-------------|------|
| `push_front(item)` | Add to front | O(1) |
| `push_back(item)` | Add to back | O(1) |
| `pop_front()` | Remove from front | O(1) |
| `pop_back()` | Remove from back | O(1) |
| `front()` | View front element | O(1) |
| `back()` | View back element | O(1) |

### STL `std::deque`

```cpp
#include <iostream>
#include <deque>
#include <string>

int main() {
    std::deque<int> dq;
    
    // Push at both ends
    dq.push_back(2);    // [2]
    dq.push_back(3);    // [2, 3]
    dq.push_front(1);   // [1, 2, 3]
    dq.push_back(4);    // [1, 2, 3, 4]
    
    std::cout << "Front: " << dq.front() << "\n"; // 1
    std::cout << "Back: " << dq.back() << "\n";   // 4
    
    // Pop from both ends
    dq.pop_front();     // [2, 3, 4]
    dq.pop_back();      // [2, 3]
    
    // Random access (deque supports it!)
    std::cout << "Element at index 0: " << dq[0] << "\n"; // 2
    std::cout << "Element at index 1: " << dq[1] << "\n"; // 3
    
    // Iterate
    std::cout << "Elements: ";
    for (int x : dq) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

### When to Use a Deque

| Use Case | Why Deque |
|----------|-----------|
| Sliding window problems | Need to add at back, remove from front |
| BFS with state | Need to add/remove from both ends |
| Palindrome checking | Compare front and back |
| Undo/Redo | Add at back, remove from front and back |
| Work stealing queues | Threads can steal from either end |

### Implementation Using a Circular Buffer

A deque can be implemented using a circular buffer that grows in both directions:

```cpp
#include <iostream>
#include <stdexcept>
#include <vector>

template <typename T>
class Deque {
    std::vector<T> data;
    int frontIndex;
    int backIndex;
    int count;
    int capacity;

    void resize() {
        int newCap = capacity * 2;
        std::vector<T> newData(newCap);
        for (int i = 0; i < count; ++i) {
            newData[i] = data[(frontIndex + i) % capacity];
        }
        data = std::move(newData);
        frontIndex = 0;
        backIndex = count - 1;
        capacity = newCap;
    }

public:
    Deque(int initCap = 8) 
        : data(initCap), frontIndex(0), backIndex(-1), 
          count(0), capacity(initCap) {}

    void push_back(const T& item) {
        if (count == capacity) resize();
        backIndex = (backIndex + 1) % capacity;
        data[backIndex] = item;
        ++count;
    }

    void push_front(const T& item) {
        if (count == capacity) resize();
        frontIndex = (frontIndex - 1 + capacity) % capacity;
        data[frontIndex] = item;
        ++count;
    }

    T pop_front() {
        if (count == 0) throw std::underflow_error("Deque is empty");
        T item = data[frontIndex];
        frontIndex = (frontIndex + 1) % capacity;
        --count;
        return item;
    }

    T pop_back() {
        if (count == 0) throw std::underflow_error("Deque is empty");
        T item = data[backIndex];
        backIndex = (backIndex - 1 + capacity) % capacity;
        --count;
        return item;
    }

    const T& front() const {
        if (count == 0) throw std::underflow_error("Deque is empty");
        return data[frontIndex];
    }

    const T& back() const {
        if (count == 0) throw std::underflow_error("Deque is empty");
        return data[backIndex];
    }

    bool empty() const { return count == 0; }
    int size() const { return count; }
};

int main() {
    Deque<int> dq;
    dq.push_back(1);
    dq.push_back(2);
    dq.push_front(0);
    
    std::cout << "Front: " << dq.front() << "\n"; // 0
    std::cout << "Back: " << dq.back() << "\n";   // 2
    std::cout << "Size: " << dq.size() << "\n";    // 3
    
    while (!dq.empty()) {
        std::cout << dq.pop_front() << " ";
    }
    std::cout << "\n";
    // Output: 0 1 2
    return 0;
}
```

---

## 11.4 Priority Queue

### Concept

A **priority queue** is a data structure where each element has a **priority**. Elements with higher priority are dequeued before elements with lower priority. Unlike a regular queue, the order of insertion does not matter — only the priority.

A priority queue is typically implemented using a **binary heap** (see the table below for complexity).

### Operations

| Operation | Description | Time (Binary Heap) |
|-----------|-------------|-------------------|
| `push(item)` | Insert an element | O(log n) |
| `pop()` | Remove the highest-priority element | O(log n) |
| `top()` | View the highest-priority element | O(1) |
| `empty()` | Check if empty | O(1) |
| `size()` | Return number of elements | O(1) |

### STL `std::priority_queue`

```cpp
#include <iostream>
#include <queue>
#include <vector>
#include <string>

int main() {
    // Max-heap (default): largest element has highest priority
    std::priority_queue<int> maxHeap;
    maxHeap.push(3);
    maxHeap.push(1);
    maxHeap.push(4);
    maxHeap.push(1);
    maxHeap.push(5);
    
    std::cout << "Max-heap order: ";
    while (!maxHeap.empty()) {
        std::cout << maxHeap.top() << " ";
        maxHeap.pop();
    }
    std::cout << "\n";
    // Output: 5 4 3 1 1
    
    // Min-heap: smallest element has highest priority
    std::priority_queue<int, std::vector<int>, std::greater<int>> minHeap;
    minHeap.push(3);
    minHeap.push(1);
    minHeap.push(4);
    minHeap.push(1);
    minHeap.push(5);
    
    std::cout << "Min-heap order: ";
    while (!minHeap.empty()) {
        std::cout << minHeap.top() << " ";
        minHeap.pop();
    }
    std::cout << "\n";
    // Output: 1 1 3 4 5
    
    return 0;
}
```

### Custom Comparators

```cpp
#include <iostream>
#include <queue>
#include <vector>
#include <string>
#include <functional>

struct Task {
    std::string name;
    int priority;
    
    // For default max-heap comparison
    bool operator<(const Task& other) const {
        return priority < other.priority; // Higher priority = dequeued first
    }
};

// Custom comparator using a functor
struct TaskComparator {
    bool operator()(const Task& a, const Task& b) const {
        return a.priority > b.priority; // Min-heap by priority
    }
};

int main() {
    // Max-heap using operator<
    std::priority_queue<Task> maxPQ;
    maxPQ.push({"Low priority task", 1});
    maxPQ.push({"High priority task", 10});
    maxPQ.push({"Medium priority task", 5});
    
    std::cout << "Max-heap (by priority):\n";
    while (!maxPQ.empty()) {
        std::cout << "  " << maxPQ.top().name 
                  << " (priority " << maxPQ.top().priority << ")\n";
        maxPQ.pop();
    }
    
    // Min-heap using custom comparator
    std::priority_queue<Task, std::vector<Task>, TaskComparator> minPQ;
    minPQ.push({"Low priority task", 1});
    minPQ.push({"High priority task", 10});
    minPQ.push({"Medium priority task", 5});
    
    std::cout << "\nMin-heap (by priority):\n";
    while (!minPQ.empty()) {
        std::cout << "  " << minPQ.top().name 
                  << " (priority " << minPQ.top().priority << ")\n";
        minPQ.pop();
    }
    
    // Lambda comparator
    auto cmp = [](const Task& a, const Task& b) {
        return a.priority < b.priority; // Max-heap
    };
    std::priority_queue<Task, std::vector<Task>, decltype(cmp)> lambdaPQ(cmp);
    
    return 0;
}
```

### Pair Comparison in Priority Queue

When elements are pairs, C++ compares them lexicographically (first element, then second):

```cpp
#include <iostream>
#include <queue>
#include <vector>

int main() {
    // Pairs are compared lexicographically by default
    // For (priority, value), this works naturally for max-heap
    std::priority_queue<std::pair<int, std::string>> pq;
    pq.push({3, "medium"});
    pq.push({1, "low"});
    pq.push({5, "high"});
    
    while (!pq.empty()) {
        std::cout << pq.top().first << ": " << pq.top().second << "\n";
        pq.pop();
    }
    // Output: 5:high, 3:medium, 1:low
    
    return 0;
}
```

---

## 11.5 BFS and Queues

### How BFS Uses a Queue

**Breadth-First Search (BFS)** explores a graph or tree level by level. The queue is the natural data structure for BFS because it processes nodes in the order they were discovered (FIFO).

### BFS Algorithm

```
BFS(graph, source):
    create queue Q
    mark source as visited
    enqueue source into Q
    
    while Q is not empty:
        node = Q.dequeue()
        process(node)
        for each neighbor of node:
            if neighbor not visited:
                mark neighbor as visited
                enqueue neighbor into Q
```

### BFS on a Graph

```cpp
#include <iostream>
#include <vector>
#include <queue>
#include <unordered_set>

class Graph {
    int vertices;
    std::vector<std::vector<int>> adj;

public:
    Graph(int v) : vertices(v), adj(v) {}
    
    void addEdge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u); // Undirected
    }
    
    // BFS from a source vertex
    // Time: O(V + E), Space: O(V)
    std::vector<int> bfs(int source) {
        std::vector<int> result;
        std::vector<bool> visited(vertices, false);
        std::queue<int> q;
        
        visited[source] = true;
        q.push(source);
        
        while (!q.empty()) {
            int node = q.front();
            q.pop();
            result.push_back(node);
            
            for (int neighbor : adj[node]) {
                if (!visited[neighbor]) {
                    visited[neighbor] = true;
                    q.push(neighbor);
                }
            }
        }
        return result;
    }
    
    // BFS to find shortest path (unweighted graph)
    std::vector<int> shortestPath(int source, int target) {
        std::vector<int> parent(vertices, -1);
        std::vector<bool> visited(vertices, false);
        std::queue<int> q;
        
        visited[source] = true;
        q.push(source);
        
        while (!q.empty()) {
            int node = q.front();
            q.pop();
            
            if (node == target) {
                // Reconstruct path
                std::vector<int> path;
                for (int v = target; v != -1; v = parent[v]) {
                    path.push_back(v);
                }
                std::reverse(path.begin(), path.end());
                return path;
            }
            
            for (int neighbor : adj[node]) {
                if (!visited[neighbor]) {
                    visited[neighbor] = true;
                    parent[neighbor] = node;
                    q.push(neighbor);
                }
            }
        }
        return {}; // No path found
    }
};

int main() {
    Graph g(6);
    g.addEdge(0, 1);
    g.addEdge(0, 2);
    g.addEdge(1, 3);
    g.addEdge(2, 4);
    g.addEdge(3, 5);
    g.addEdge(4, 5);
    
    auto order = g.bfs(0);
    std::cout << "BFS order: ";
    for (int v : order) std::cout << v << " ";
    std::cout << "\n";
    // Output: 0 1 2 3 4 5
    
    auto path = g.shortestPath(0, 5);
    std::cout << "Shortest path 0→5: ";
    for (int v : path) std::cout << v << " ";
    std::cout << "\n";
    // Output: 0 1 3 5 or 0 2 4 5
    return 0;
}
```

### Level-Order Traversal of a Binary Tree

BFS naturally gives level-order traversal:

```cpp
#include <iostream>
#include <vector>
#include <queue>

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

// Level-order traversal using BFS
// Time: O(n), Space: O(n)
std::vector<std::vector<int>> levelOrder(TreeNode* root) {
    std::vector<std::vector<int>> result;
    if (!root) return result;
    
    std::queue<TreeNode*> q;
    q.push(root);
    
    while (!q.empty()) {
        int levelSize = q.size();
        std::vector<int> currentLevel;
        
        for (int i = 0; i < levelSize; ++i) {
            TreeNode* node = q.front();
            q.pop();
            currentLevel.push_back(node->val);
            
            if (node->left) q.push(node->left);
            if (node->right) q.push(node->right);
        }
        
        result.push_back(currentLevel);
    }
    return result;
}

int main() {
    //       3
    //      / \
    //     9  20
    //       /  \
    //      15   7
    TreeNode* root = new TreeNode(3);
    root->left = new TreeNode(9);
    root->right = new TreeNode(20);
    root->right->left = new TreeNode(15);
    root->right->right = new TreeNode(7);
    
    auto levels = levelOrder(root);
    std::cout << "Level-order:\n";
    for (int i = 0; i < levels.size(); ++i) {
        std::cout << "Level " << i << ": ";
        for (int v : levels[i]) std::cout << v << " ";
        std::cout << "\n";
    }
    // Output:
    // Level 0: 3
    // Level 1: 9 20
    // Level 2: 15 7
    
    // Cleanup
    delete root->left;
    delete root->right->left;
    delete root->right->right;
    delete root->right;
    delete root;
    return 0;
}
```

---

## Interview Tips

1. **BFS uses a queue, DFS uses a stack.** This is the most fundamental distinction. Memorize it.
2. **Know the circular queue.** It's a common interview question and tests your understanding of modular arithmetic.
3. **Priority queue is a max-heap by default.** Use `std::greater<T>` for a min-heap.
4. **Deque is versatile.** It can act as both a stack and a queue. Use it for sliding window problems.
5. **Two-stack queue:** A common interview question. Use one stack for enqueue and another for dequeue.
6. **Queue of pairs/structs:** When BFS needs to track state (position, distance, etc.), use `std::queue<std::pair<...>>`.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Not checking `empty()` before `front()`/`pop()` | Segfault on empty queue | Always check `empty()` first |
| Forgetting wrap-around in circular queue | `backIndex++` without `% capacity` | Always use `(index + 1) % capacity` |
| Using wrong comparator for min-heap | `std::priority_queue<int>` gives max-heap | Use `std::greater<int>` for min-heap |
| BFS on directed graph with `addEdge(u,v)` only | Missing reverse edge | Add both edges for undirected graphs |
| Not marking nodes as visited when enqueuing | Nodes visited multiple times | Mark as visited *before* enqueueing |
| Comparing pairs incorrectly in priority queue | Wrong field compared | Ensure comparator matches your priority logic |

---

## Practice Problems

### Easy

1. **Implement Queue using Stacks** — Implement a FIFO queue using only two stacks.
   - *Hint:* Push to stack1. For pop, if stack2 is empty, pour all of stack1 into stack2, then pop from stack2. Amortized O(1).

2. **Implement Stack using Queues** — Implement a LIFO stack using only queues.
   - *Hint:* On push, enqueue to q2, then dequeue all from q1 to q2, then swap q1 and q2.

3. **Number of Recent Calls** — Implement `ping(t)` that returns the number of pings in the last 3000ms.
   - *Hint:* Use a queue. Remove old pings, add new one, return size.

### Medium

4. **Sliding Window Maximum** — Given an array and window size k, find the maximum in each sliding window.
   - *Hint:* Use a deque. Maintain elements in decreasing order. Remove elements outside the window.

5. **Moving Average from Data Stream** — Compute the moving average of the last `k` values from a data stream.
   - *Hint:* Use a queue. When size exceeds k, remove the oldest element.

6. **Rotting Oranges** — Given a grid of oranges, find the minimum time for all oranges to rot.
   - *Hint:* Multi-source BFS. Start with all rotten oranges in the queue.

### Hard

7. **Shortest Path in Binary Matrix** — Find the shortest path from top-left to bottom-right in a binary matrix.
   - *Hint:* BFS from (0,0), exploring all 8 directions.

8. **Sliding Window Maximum** — Solve in O(n) using a monotonic deque.
   - *Hint:* Maintain a deque of indices where values are in decreasing order.

9. **Jump Game IV** — Given an array, find the minimum jumps to reach the end.
   - *Hint:* BFS. Group same-valued indices to avoid TLE.

---

## Additional Patterns: Two-Stack Queue

A common interview question: implement a queue using only two stacks.

```cpp
#include <iostream>
#include <stack>

class QueueUsingStacks {
    std::stack<int> stackIn;   // For enqueue
    std::stack<int> stackOut;  // For dequeue

public:
    // Push element to back of queue
    // Time: O(1) amortized
    void push(int x) {
        stackIn.push(x);
    }
    
    // Removes the element from front and returns it
    // Time: O(1) amortized
    int pop() {
        if (stackOut.empty()) {
            // Transfer all elements from stackIn to stackOut
            // This reverses the order, giving us FIFO
            while (!stackIn.empty()) {
                stackOut.push(stackIn.top());
                stackIn.pop();
            }
        }
        if (stackOut.empty()) {
            throw std::runtime_error("Queue is empty");
        }
        int val = stackOut.top();
        stackOut.pop();
        return val;
    }
    
    int peek() {
        if (stackOut.empty()) {
            while (!stackIn.empty()) {
                stackOut.push(stackIn.top());
                stackIn.pop();
            }
        }
        if (stackOut.empty()) {
            throw std::runtime_error("Queue is empty");
        }
        return stackOut.top();
    }
    
    bool empty() {
        return stackIn.empty() && stackOut.empty();
    }
};

int main() {
    QueueUsingStacks q;
    q.push(1);
    q.push(2);
    q.push(3);
    
    std::cout << "Pop: " << q.pop() << "\n"; // 1
    std::cout << "Pop: " << q.pop() << "\n"; // 2
    q.push(4);
    std::cout << "Pop: " << q.pop() << "\n"; // 3
    std::cout << "Pop: " << q.pop() << "\n"; // 4
    
    return 0;
}
```

**Why it works:** When we transfer elements from `stackIn` to `stackOut`, the order is reversed. The oldest element (front of queue) ends up on top of `stackOut`. Each element is moved at most once from `stackIn` to `stackOut`, so the amortized cost per operation is O(1).

### BFS with Distance Tracking

A practical pattern: use a queue to track both nodes and their distances during BFS.

```cpp
#include <iostream>
#include <vector>
#include <queue>

// Find shortest path in an unweighted graph using BFS
std::vector<int> shortestDistances(const std::vector<std::vector<int>>& adj, 
                                    int source) {
    int n = adj.size();
    std::vector<int> dist(n, -1);
    std::queue<int> q;
    
    dist[source] = 0;
    q.push(source);
    
    while (!q.empty()) {
        int node = q.front();
        q.pop();
        
        for (int neighbor : adj[node]) {
            if (dist[neighbor] == -1) {
                dist[neighbor] = dist[node] + 1;
                q.push(neighbor);
            }
        }
    }
    return dist;
}

int main() {
    // Graph: 0-1-2-3-4
    std::vector<std::vector<int>> adj(5);
    adj[0] = {1};
    adj[1] = {0, 2};
    adj[2] = {1, 3};
    adj[3] = {2, 4};
    adj[4] = {3};
    
    auto dist = shortestDistances(adj, 0);
    std::cout << "Distances from 0: ";
    for (int d : dist) std::cout << d << " ";
    std::cout << "\n";
    // Output: 0 1 2 3 4
    return 0;
}
```

## Complexity Summary

| Data Structure | Push/Enqueue | Pop/Dequeue | Peek/Front | Search |
|---------------|-------------|-------------|------------|--------|
| Simple Queue | O(1) | O(n) | O(1) | O(n) |
| Circular Queue | O(1) | O(1) | O(1) | O(n) |
| Linked Queue | O(1) | O(1) | O(1) | O(n) |
| Deque | O(1) | O(1) | O(1) | O(n) |
| Priority Queue | O(log n) | O(log n) | O(1) | O(n) |
| STL queue | O(1)* | O(1)* | O(1) | O(n) |
| STL deque | O(1)* | O(1)* | O(1) | O(n) |

*Amortized for dynamic containers.
