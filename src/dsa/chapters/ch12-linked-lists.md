# Chapter 12: Linked Lists

Linked lists are one of the most fundamental data structures and a favorite topic in coding interviews. Unlike arrays, linked lists store elements in non-contiguous memory locations, connected by pointers. This chapter covers singly linked lists, doubly linked lists, circular linked lists, and the essential fast-slow pointer technique, along with common patterns and problems.

---

## 12.1 Singly Linked List

### Node Structure

A singly linked list consists of nodes where each node contains data and a pointer to the next node.

```cpp
struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};
```

### Basic Operations

```cpp
#include <iostream>
#include <vector>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

class SinglyLinkedList {
    ListNode* head;
    int count;

public:
    SinglyLinkedList() : head(nullptr), count(0) {}
    
    ~SinglyLinkedList() {
        while (head) {
            ListNode* temp = head;
            head = head->next;
            delete temp;
        }
    }

    // Insert at the beginning — O(1)
    void insertFront(int val) {
        ListNode* node = new ListNode(val);
        node->next = head;
        head = node;
        ++count;
    }

    // Insert at the end — O(n)
    void insertBack(int val) {
        ListNode* node = new ListNode(val);
        if (!head) {
            head = node;
        } else {
            ListNode* curr = head;
            while (curr->next) {
                curr = curr->next;
            }
            curr->next = node;
        }
        ++count;
    }

    // Insert at index — O(n)
    void insertAt(int index, int val) {
        if (index < 0 || index > count) {
            throw std::out_of_range("Index out of range");
        }
        if (index == 0) {
            insertFront(val);
            return;
        }
        ListNode* curr = head;
        for (int i = 0; i < index - 1; ++i) {
            curr = curr->next;
        }
        ListNode* node = new ListNode(val);
        node->next = curr->next;
        curr->next = node;
        ++count;
    }

    // Delete at index — O(n)
    void deleteAt(int index) {
        if (index < 0 || index >= count) {
            throw std::out_of_range("Index out of range");
        }
        if (index == 0) {
            ListNode* temp = head;
            head = head->next;
            delete temp;
        } else {
            ListNode* curr = head;
            for (int i = 0; i < index - 1; ++i) {
                curr = curr->next;
            }
            ListNode* temp = curr->next;
            curr->next = temp->next;
            delete temp;
        }
        --count;
    }

    // Search — O(n)
    int search(int val) const {
        ListNode* curr = head;
        int index = 0;
        while (curr) {
            if (curr->val == val) return index;
            curr = curr->next;
            ++index;
        }
        return -1;
    }

    // Access by index — O(n)
    int get(int index) const {
        if (index < 0 || index >= count) {
            throw std::out_of_range("Index out of range");
        }
        ListNode* curr = head;
        for (int i = 0; i < index; ++i) {
            curr = curr->next;
        }
        return curr->val;
    }

    // Print the list
    void print() const {
        ListNode* curr = head;
        while (curr) {
            std::cout << curr->val;
            if (curr->next) std::cout << " → ";
            curr = curr->next;
        }
        std::cout << " → NULL\n";
    }

    int size() const { return count; }
    bool empty() const { return count == 0; }
    ListNode* getHead() const { return head; }
};

int main() {
    SinglyLinkedList list;
    list.insertBack(1);
    list.insertBack(2);
    list.insertBack(3);
    list.insertFront(0);
    list.print(); // 0 → 1 → 2 → 3 → NULL
    
    list.insertAt(2, 99);
    list.print(); // 0 → 1 → 99 → 2 → 3 → NULL
    
    list.deleteAt(2);
    list.print(); // 0 → 1 → 2 → 3 → NULL
    
    std::cout << "Search 2: index " << list.search(2) << "\n"; // 2
    std::cout << "Get index 3: " << list.get(3) << "\n";       // 3
    
    return 0;
}
```

### Reverse a Linked List

The most fundamental linked list operation. This is asked in almost every interview.

```cpp
#include <iostream>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// Iterative reverse
// Time: O(n), Space: O(1)
ListNode* reverseList(ListNode* head) {
    ListNode* prev = nullptr;
    ListNode* curr = head;
    
    while (curr) {
        ListNode* next = curr->next; // Save next
        curr->next = prev;           // Reverse pointer
        prev = curr;                 // Move prev forward
        curr = next;                 // Move curr forward
    }
    return prev; // prev is the new head
}

// Recursive reverse
// Time: O(n), Space: O(n) due to call stack
ListNode* reverseListRecursive(ListNode* head) {
    if (!head || !head->next) return head;
    
    ListNode* newHead = reverseListRecursive(head->next);
    head->next->next = head; // Make next node point back to current
    head->next = nullptr;    // Remove current's forward pointer
    return newHead;
}

// Helper: build list from vector
ListNode* buildList(const std::vector<int>& vals) {
    ListNode dummy(0);
    ListNode* curr = &dummy;
    for (int v : vals) {
        curr->next = new ListNode(v);
        curr = curr->next;
    }
    return dummy.next;
}

// Helper: print list
void printList(ListNode* head) {
    while (head) {
        std::cout << head->val;
        if (head->next) std::cout << " → ";
        head = head->next;
    }
    std::cout << " → NULL\n";
}

// Helper: free list
void freeList(ListNode* head) {
    while (head) {
        ListNode* temp = head;
        head = head->next;
        delete temp;
    }
}

int main() {
    ListNode* head = buildList({1, 2, 3, 4, 5});
    std::cout << "Original: ";
    printList(head);
    
    head = reverseList(head);
    std::cout << "Reversed: ";
    printList(head);
    // Output: 5 → 4 → 3 → 2 → 1 → NULL
    
    freeList(head);
    return 0;
}
```

**Dry Run for Iterative Reverse:**

```
Initial: prev=NULL, curr=1→2→3→4→5

Step 1: next=2, 1→NULL,    prev=1, curr=2→3→4→5
Step 2: next=3, 2→1→NULL,  prev=2, curr=3→4→5
Step 3: next=4, 3→2→1→NULL, prev=3, curr=4→5
Step 4: next=5, 4→3→2→1→NULL, prev=4, curr=5
Step 5: next=NULL, 5→4→3→2→1→NULL, prev=5, curr=NULL

Return prev = 5→4→3→2→1→NULL
```

---

## 12.2 Doubly Linked List

### Node Structure

```cpp
struct DoublyListNode {
    int val;
    DoublyListNode* prev;
    DoublyListNode* next;
    DoublyListNode(int x) : val(x), prev(nullptr), next(nullptr) {}
};
```

### Implementation

```cpp
#include <iostream>
#include <stdexcept>

struct DoublyListNode {
    int val;
    DoublyListNode* prev;
    DoublyListNode* next;
    DoublyListNode(int x) : val(x), prev(nullptr), next(nullptr) {}
};

class DoublyLinkedList {
    DoublyListNode* head;
    DoublyListNode* tail;
    int count;

public:
    DoublyLinkedList() : head(nullptr), tail(nullptr), count(0) {}
    
    ~DoublyLinkedList() {
        while (head) {
            DoublyListNode* temp = head;
            head = head->next;
            delete temp;
        }
    }

    // Insert at front — O(1)
    void insertFront(int val) {
        DoublyListNode* node = new DoublyListNode(val);
        node->next = head;
        if (head) head->prev = node;
        head = node;
        if (!tail) tail = node;
        ++count;
    }

    // Insert at back — O(1)
    void insertBack(int val) {
        DoublyListNode* node = new DoublyListNode(val);
        node->prev = tail;
        if (tail) tail->next = node;
        tail = node;
        if (!head) head = node;
        ++count;
    }

    // Delete a given node — O(1)
    void deleteNode(DoublyListNode* node) {
        if (!node) return;
        
        if (node->prev) {
            node->prev->next = node->next;
        } else {
            head = node->next; // Deleting head
        }
        
        if (node->next) {
            node->next->prev = node->prev;
        } else {
            tail = node->prev; // Deleting tail
        }
        
        delete node;
        --count;
    }

    // Delete from front — O(1)
    void deleteFront() {
        if (!head) throw std::underflow_error("List is empty");
        DoublyListNode* temp = head;
        head = head->next;
        if (head) head->prev = nullptr;
        else tail = nullptr;
        delete temp;
        --count;
    }

    // Delete from back — O(1)
    void deleteBack() {
        if (!tail) throw std::underflow_error("List is empty");
        DoublyListNode* temp = tail;
        tail = tail->prev;
        if (tail) tail->next = nullptr;
        else head = nullptr;
        delete temp;
        --count;
    }

    // Print forward
    void printForward() const {
        DoublyListNode* curr = head;
        std::cout << "Forward: ";
        while (curr) {
            std::cout << curr->val;
            if (curr->next) std::cout << " ⇄ ";
            curr = curr->next;
        }
        std::cout << "\n";
    }

    // Print backward
    void printBackward() const {
        DoublyListNode* curr = tail;
        std::cout << "Backward: ";
        while (curr) {
            std::cout << curr->val;
            if (curr->prev) std::cout << " ⇄ ";
            curr = curr->prev;
        }
        std::cout << "\n";
    }

    int size() const { return count; }
    DoublyListNode* getHead() const { return head; }
    DoublyListNode* getTail() const { return tail; }
};

int main() {
    DoublyLinkedList list;
    list.insertBack(1);
    list.insertBack(2);
    list.insertBack(3);
    list.insertFront(0);
    
    list.printForward();  // 0 ⇄ 1 ⇄ 2 ⇄ 3
    list.printBackward(); // 3 ⇄ 2 ⇄ 1 ⇄ 0
    
    list.deleteFront();
    list.deleteBack();
    list.printForward();  // 1 ⇄ 2
    
    return 0;
}
```

### Singly vs. Doubly Linked List

| Feature | Singly Linked | Doubly Linked |
|---------|---------------|---------------|
| Space per node | 1 pointer | 2 pointers |
| Insert after given node | O(1) | O(1) |
| Delete given node | O(n)* | O(1) |
| Traverse backward | No | Yes |
| Memory overhead | Lower | Higher |

*For singly linked list, deleting a given node requires finding its predecessor, unless you copy the next node's data.

---

## 12.3 Circular Linked List

In a circular linked list, the last node's `next` pointer points back to the head instead of `nullptr`.

### Josephus Problem

N people stand in a circle. Starting from person 0, every k-th person is eliminated. Find the last remaining person.

```cpp
#include <iostream>
#include <list>

// Josephus problem using circular linked list concept
// Time: O(n*k), Space: O(n)
int josephus(int n, int k) {
    std::list<int> circle;
    for (int i = 0; i < n; ++i) {
        circle.push_back(i);
    }
    
    auto it = circle.begin();
    
    while (circle.size() > 1) {
        // Move k-1 steps forward
        for (int i = 0; i < k - 1; ++i) {
            ++it;
            if (it == circle.end()) it = circle.begin();
        }
        // Eliminate the k-th person
        it = circle.erase(it);
        if (it == circle.end()) it = circle.begin();
    }
    
    return circle.front();
}

// Mathematical solution: O(n)
int josephusMath(int n, int k) {
    int result = 0;
    for (int i = 2; i <= n; ++i) {
        result = (result + k) % i;
    }
    return result;
}

int main() {
    int n = 7, k = 3;
    std::cout << "Josephus(" << n << "," << k << ") = " 
              << josephus(n, k) << "\n"; // 3
    std::cout << "Josephus(" << n << "," << k << ") = " 
              << josephusMath(n, k) << "\n"; // 3
    return 0;
}
```

---

## 12.4 Fast and Slow Pointers

The **fast and slow pointer** technique (also called **Floyd's algorithm**) is one of the most elegant and frequently tested linked list patterns.

### Cycle Detection (Floyd's Algorithm)

Use two pointers: `slow` moves one step at a time, `fast` moves two steps. If there is a cycle, they will eventually meet.

```cpp
#include <iostream>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// Detect cycle
// Time: O(n), Space: O(1)
bool hasCycle(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    
    while (fast && fast->next) {
        slow = slow->next;
        fast = fast->next->next;
        if (slow == fast) return true;
    }
    return false;
}

// Find the start of the cycle
// After detecting the meeting point, move one pointer to head.
// Move both one step at a time — they meet at the cycle start.
ListNode* detectCycleStart(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    
    // Phase 1: Detect cycle
    while (fast && fast->next) {
        slow = slow->next;
        fast = fast->next->next;
        if (slow == fast) break;
    }
    
    if (!fast || !fast->next) return nullptr; // No cycle
    
    // Phase 2: Find cycle start
    slow = head;
    while (slow != fast) {
        slow = slow->next;
        fast = fast->next;
    }
    return slow;
}

int main() {
    // Create: 1 → 2 → 3 → 4 → 5 → 3 (cycle)
    ListNode* head = new ListNode(1);
    head->next = new ListNode(2);
    head->next->next = new ListNode(3);
    head->next->next->next = new ListNode(4);
    head->next->next->next->next = new ListNode(5);
    head->next->next->next->next->next = head->next->next; // Cycle at node 3
    
    std::cout << "Has cycle: " << (hasCycle(head) ? "yes" : "no") << "\n";
    
    ListNode* cycleStart = detectCycleStart(head);
    if (cycleStart) {
        std::cout << "Cycle starts at node with value: " << cycleStart->val << "\n";
    }
    
    // Cleanup (break cycle first)
    head->next->next->next->next->next = nullptr;
    while (head) {
        ListNode* temp = head;
        head = head->next;
        delete temp;
    }
    return 0;
}
```

**Why does Floyd's cycle detection work?**

```
Let's say:
- Distance from head to cycle start = F
- Cycle length = C
- Distance from cycle start to meeting point = a

When slow and fast meet:
- slow traveled: F + a
- fast traveled: F + a + nC (for some integer n)
- fast traveled 2x slow: 2(F + a) = F + a + nC
- Therefore: F + a = nC → F = nC - a

This means: if we move one pointer from head and one from meeting point,
both moving one step at a time, they meet at the cycle start!
```

### Finding the Middle of a Linked List

```cpp
// Find the middle node
// Time: O(n), Space: O(1)
ListNode* findMiddle(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    
    while (fast->next && fast->next->next) {
        slow = slow->next;
        fast = fast->next->next;
    }
    return slow; // For even length, returns the first middle
}
```

### Finding the Nth Node from the End

```cpp
// Find the nth node from the end
// Time: O(n), Space: O(1)
ListNode* nthFromEnd(ListNode* head, int n) {
    ListNode* fast = head;
    ListNode* slow = head;
    
    // Move fast n steps ahead
    for (int i = 0; i < n; ++i) {
        if (!fast) return nullptr; // List too short
        fast = fast->next;
    }
    
    // Move both until fast reaches the end
    while (fast) {
        slow = slow->next;
        fast = fast->next;
    }
    return slow;
}
```

### Palindrome Check

```cpp
#include <iostream>
#include <stack>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// Check if linked list is a palindrome
// Time: O(n), Space: O(1) using reverse
bool isPalindrome(ListNode* head) {
    if (!head || !head->next) return true;
    
    // Find middle
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast->next && fast->next->next) {
        slow = slow->next;
        fast = fast->next->next;
    }
    
    // Reverse second half
    ListNode* prev = nullptr;
    ListNode* curr = slow->next;
    while (curr) {
        ListNode* next = curr->next;
        curr->next = prev;
        prev = curr;
        curr = next;
    }
    
    // Compare first half and reversed second half
    ListNode* left = head;
    ListNode* right = prev;
    bool result = true;
    while (right) {
        if (left->val != right->val) {
            result = false;
            break;
        }
        left = left->next;
        right = right->next;
    }
    
    // Optional: restore the list
    // (Reverse second half back)
    
    return result;
}
```

---

## 12.5 Linked List Patterns

### Pattern 1: Merge Two Sorted Lists

```cpp
#include <iostream>
#include <vector>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// Merge two sorted linked lists
// Time: O(n + m), Space: O(1)
ListNode* mergeTwoLists(ListNode* l1, ListNode* l2) {
    ListNode dummy(0);
    ListNode* curr = &dummy;
    
    while (l1 && l2) {
        if (l1->val <= l2->val) {
            curr->next = l1;
            l1 = l1->next;
        } else {
            curr->next = l2;
            l2 = l2->next;
        }
        curr = curr->next;
    }
    
    // Attach remaining nodes
    curr->next = l1 ? l1 : l2;
    
    return dummy.next;
}

// Helper functions
ListNode* buildList(const std::vector<int>& vals) {
    ListNode dummy(0);
    ListNode* curr = &dummy;
    for (int v : vals) {
        curr->next = new ListNode(v);
        curr = curr->next;
    }
    return dummy.next;
}

void printList(ListNode* head) {
    while (head) {
        std::cout << head->val;
        if (head->next) std::cout << " → ";
        head = head->next;
    }
    std::cout << "\n";
}

void freeList(ListNode* head) {
    while (head) {
        ListNode* temp = head;
        head = head->next;
        delete temp;
    }
}

int main() {
    ListNode* l1 = buildList({1, 3, 5, 7});
    ListNode* l2 = buildList({2, 4, 6, 8});
    
    std::cout << "List 1: "; printList(l1);
    std::cout << "List 2: "; printList(l2);
    
    ListNode* merged = mergeTwoLists(l1, l2);
    std::cout << "Merged: "; printList(merged);
    // Output: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
    
    freeList(merged);
    return 0;
}
```

### Pattern 2: Reverse in Groups of K

```cpp
#include <iostream>
#include <vector>

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

// Reverse nodes in groups of k
// Time: O(n), Space: O(1)
ListNode* reverseKGroup(ListNode* head, int k) {
    // Check if there are at least k nodes
    ListNode* curr = head;
    for (int i = 0; i < k; ++i) {
        if (!curr) return head; // Fewer than k nodes, don't reverse
        curr = curr->next;
    }
    
    // Reverse k nodes
    ListNode* prev = nullptr;
    curr = head;
    for (int i = 0; i < k; ++i) {
        ListNode* next = curr->next;
        curr->next = prev;
        prev = curr;
        curr = next;
    }
    
    // head is now the last node in this group
    // Recursively reverse the rest and connect
    head->next = reverseKGroup(curr, k);
    
    return prev; // prev is the new head of this group
}

ListNode* buildList(const std::vector<int>& vals) {
    ListNode dummy(0);
    ListNode* curr = &dummy;
    for (int v : vals) {
        curr->next = new ListNode(v);
        curr = curr->next;
    }
    return dummy.next;
}

void printList(ListNode* head) {
    while (head) {
        std::cout << head->val;
        if (head->next) std::cout << " → ";
        head = head->next;
    }
    std::cout << "\n";
}

void freeList(ListNode* head) {
    while (head) {
        ListNode* temp = head;
        head = head->next;
        delete temp;
    }
}

int main() {
    ListNode* head = buildList({1, 2, 3, 4, 5, 6, 7, 8});
    std::cout << "Original: "; printList(head);
    
    head = reverseKGroup(head, 3);
    std::cout << "K=3:      "; printList(head);
    // Output: 3 → 2 → 1 → 6 → 5 → 4 → 7 → 8
    
    freeList(head);
    return 0;
}
```

### Pattern 3: Flatten a Multilevel Linked List

```cpp
#include <iostream>
#include <vector>

// Node with child pointer (multilevel linked list)
struct Node {
    int val;
    Node* next;
    Node* child;
    Node(int x) : val(x), next(nullptr), child(nullptr) {}
};

// Flatten: treat child pointers as part of the main list
// Time: O(n), Space: O(1) using iterative approach
Node* flatten(Node* head) {
    Node* curr = head;
    
    while (curr) {
        if (curr->child) {
            // Find the tail of the child list
            Node* childTail = curr->child;
            while (childTail->next) {
                childTail = childTail->next;
            }
            // Connect child tail to curr's next
            childTail->next = curr->next;
            // Insert child list after curr
            curr->next = curr->child;
            curr->child = nullptr;
        }
        curr = curr->next;
    }
    return head;
}

int main() {
    // 1 → 2 → 3 → 4
    //         |
    //         5 → 6
    Node* head = new Node(1);
    head->next = new Node(2);
    head->next->next = new Node(3);
    head->next->next->next = new Node(4);
    head->next->next->child = new Node(5);
    head->next->next->child->next = new Node(6);
    
    head = flatten(head);
    
    Node* curr = head;
    std::cout << "Flattened: ";
    while (curr) {
        std::cout << curr->val << " ";
        Node* temp = curr;
        curr = curr->next;
        delete temp;
    }
    std::cout << "\n";
    // Output: 1 2 3 5 6 4
    return 0;
}
```

### Pattern 4: Copy List with Random Pointer

```cpp
#include <iostream>
#include <unordered_map>

struct RandomListNode {
    int val;
    RandomListNode* next;
    RandomListNode* random;
    RandomListNode(int x) : val(x), next(nullptr), random(nullptr) {}
};

// Approach 1: Using hash map
// Time: O(n), Space: O(n)
RandomListNode* copyRandomList(RandomListNode* head) {
    if (!head) return nullptr;
    
    std::unordered_map<RandomListNode*, RandomListNode*> map;
    
    // First pass: create all nodes
    RandomListNode* curr = head;
    while (curr) {
        map[curr] = new RandomListNode(curr->val);
        curr = curr->next;
    }
    
    // Second pass: connect pointers
    curr = head;
    while (curr) {
        map[curr]->next = map[curr->next];     // nullptr maps to nullptr
        map[curr]->random = map[curr->random];
        curr = curr->next;
    }
    
    return map[head];
}

// Approach 2: O(1) space — interleave nodes
// Time: O(n), Space: O(1)
RandomListNode* copyRandomListO1(RandomListNode* head) {
    if (!head) return nullptr;
    
    // Step 1: Insert copy nodes after each original node
    // A → A' → B → B' → C → C'
    RandomListNode* curr = head;
    while (curr) {
        RandomListNode* copy = new RandomListNode(curr->val);
        copy->next = curr->next;
        curr->next = copy;
        curr = copy->next;
    }
    
    // Step 2: Connect random pointers
    curr = head;
    while (curr) {
        if (curr->random) {
            curr->next->random = curr->random->next;
        }
        curr = curr->next->next;
    }
    
    // Step 3: Separate the two lists
    curr = head;
    RandomListNode* newHead = head->next;
    while (curr) {
        RandomListNode* copy = curr->next;
        curr->next = copy->next;
        if (copy->next) {
            copy->next = copy->next->next;
        }
        curr = curr->next;
    }
    
    return newHead;
}
```

---

## 12.6 STL and Linked Lists

### `std::list` — Doubly Linked List

```cpp
#include <iostream>
#include <list>
#include <algorithm>

int main() {
    std::list<int> lst = {3, 1, 4, 1, 5, 9};
    
    // Insert at both ends
    lst.push_front(0);
    lst.push_back(10);
    
    // Iterate
    std::cout << "List: ";
    for (int x : lst) std::cout << x << " ";
    std::cout << "\n";
    
    // Remove elements
    lst.remove(1); // Remove all occurrences of 1
    std::cout << "After remove(1): ";
    for (int x : lst) std::cout << x << " ";
    std::cout << "\n";
    
    // Sort
    lst.sort();
    std::cout << "Sorted: ";
    for (int x : lst) std::cout << x << " ";
    std::cout << "\n";
    
    // Unique (must be sorted first)
    lst.unique();
    std::cout << "Unique: ";
    for (int x : lst) std::cout << x << " ";
    std::cout << "\n";
    
    // Splice — move elements from one list to another
    std::list<int> other = {100, 200, 300};
    auto it = lst.begin();
    std::advance(it, 2);
    lst.splice(it, other); // Insert 'other' before position 2
    std::cout << "After splice: ";
    for (int x : lst) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

### `std::forward_list` — Singly Linked List

```cpp
#include <iostream>
#include <forward_list>

int main() {
    std::forward_list<int> flst = {3, 1, 4, 1, 5};
    
    // Insert at front only
    flst.push_front(0);
    
    // Insert after a position
    auto it = flst.begin();
    std::advance(it, 2);
    flst.insert_after(it, 99);
    
    std::cout << "Forward list: ";
    for (int x : flst) std::cout << x << " ";
    std::cout << "\n";
    
    return 0;
}
```

### When to Use Linked List vs. Vector

| Criterion | `std::vector` | `std::list` |
|-----------|---------------|-------------|
| Random access | O(1) | O(n) |
| Insert/delete at front | O(n) | O(1) |
| Insert/delete in middle | O(n) | O(1)* |
| Memory | Contiguous | Scattered |
| Cache performance | Excellent | Poor |
| Iterator invalidation | On resize/insert | Only on delete |
| Use when | Frequent random access | Frequent insert/delete |

*Given an iterator to the position.

**Practical advice:** Almost always prefer `std::vector` unless you have a specific reason to use a linked list. The cache performance advantage of vectors usually outweighs the O(1) insertion advantage of linked lists. In interviews, linked list questions test your pointer manipulation skills, not your choice of STL container.

---

## Interview Tips

1. **Use the dummy node trick.** A dummy head node simplifies edge cases (empty list, insert at head, etc.).
2. **Draw the pointers.** When reversing or rearranging nodes, draw the before and after state.
3. **Master fast-slow pointers.** Cycle detection, finding middle, finding nth from end — all use this pattern.
4. **Be careful with pointer updates.** Always update pointers in the correct order to avoid losing references.
5. **Consider the empty list and single-node list.** These are common edge cases.
6. **Know the time complexities.** Insert at front is O(1), but insert at a given position is O(n) for singly linked lists.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Losing the head pointer | `head = head->next` without saving | Use a dummy node or save head |
| Null pointer dereference | Accessing `curr->next` when `curr` is null | Always check before dereferencing |
| Forgetting to delete nodes | Memory leak in destructor | Delete all nodes in destructor |
| Off-by-one in cycle detection | `fast->next->next` without checking `fast->next` | Check `fast && fast->next` |
| Not handling empty list | Operations on null head | Check `if (!head)` first |
| Wrong order in reversal | Updating `prev` before saving `next` | Save `next` first, then update pointers |

---

## Practice Problems

### Easy

1. **Reverse Linked List** — Reverse a singly linked list iteratively and recursively.
   - *Hint:* Use three pointers: prev, curr, next.

2. **Merge Two Sorted Lists** — Merge two sorted linked lists into one sorted list.
   - *Hint:* Use a dummy head. Compare and attach the smaller node.

3. **Linked List Cycle** — Determine if a linked list has a cycle.
   - *Hint:* Fast and slow pointers.

4. **Remove Duplicates from Sorted List** — Remove duplicates from a sorted linked list.
   - *Hint:* Compare current with next. Skip if equal.

### Medium

5. **Add Two Numbers** — Two numbers represented as linked lists (digits in reverse order), return their sum as a linked list.
   - *Hint:* Simulate addition with carry, digit by digit.

6. **Remove Nth Node From End** — Remove the nth node from the end of the list.
   - *Hint:* Two pointers. Move the first n steps ahead, then move both until the first reaches the end.

7. **Swap Nodes in Pairs** — Swap every two adjacent nodes.
   - *Hint:* Use a dummy head. Adjust pointers for each pair.

8. **Sort List** — Sort a linked list in O(n log n) time using constant space.
   - *Hint:* Merge sort on linked lists. Find middle, sort halves, merge.

### Hard

9. **LRU Cache** — Implement an LRU cache with O(1) get and put.
   - *Hint:* Hash map + doubly linked list. Most recent at tail, least recent at head.

10. **Merge K Sorted Lists** — Merge k sorted linked lists into one sorted list.
    - *Hint:* Use a min-heap. Push the head of each list. Pop the smallest, push its next.

11. **Reverse Nodes in k-Group** — Reverse nodes in groups of k.
    - *Hint:* Check k nodes exist, reverse them, recurse on the rest.

---

## Complexity Summary

| Operation | Singly Linked | Doubly Linked | Array |
|-----------|---------------|---------------|-------|
| Access by index | O(n) | O(n) | O(1) |
| Insert at front | O(1) | O(1) | O(n) |
| Insert at back | O(n)* | O(1) | O(1)** |
| Insert at position | O(n) | O(1)*** | O(n) |
| Delete at front | O(1) | O(1) | O(n) |
| Delete at back | O(n) | O(1) | O(1) |
| Delete at position | O(n) | O(1)*** | O(n) |
| Search | O(n) | O(n) | O(n) |

*O(1) if we maintain a tail pointer. **Amortized. ***Given an iterator to the position.
