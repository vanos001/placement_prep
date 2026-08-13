# Chapter 10: Stacks

The stack is one of the most fundamental data structures in computer science. Despite its simplicity — or perhaps because of it — the stack appears everywhere: from managing function calls to evaluating expressions, from parsing syntax to implementing undo mechanisms. Understanding stacks deeply is essential for coding interviews, as stack-based problems test your ability to think about ordering, nesting, and state management.

---

## 10.1 Stack Fundamentals

### What Is a Stack?

A **stack** is a linear data structure that follows the **Last In, First Out (LIFO)** principle. The last element added to the stack is the first one to be removed.

Think of a stack of plates: you add plates to the top and remove plates from the top. You cannot remove a plate from the middle without first removing the plates above it.

### Core Operations

| Operation | Description | Time Complexity |
|-----------|-------------|-----------------|
| `push(item)` | Add an element to the top | O(1) |
| `pop()` | Remove the top element | O(1) |
| `top()` / `peek()` | View the top element without removing | O(1) |
| `empty()` | Check if the stack is empty | O(1) |
| `size()` | Return the number of elements | O(1) |

### Stack Interface

```cpp
template <typename T>
class Stack {
public:
    virtual ~Stack() = default;
    virtual void push(const T& item) = 0;
    virtual void pop() = 0;
    virtual const T& top() const = 0;
    virtual bool empty() const = 0;
    virtual int size() const = 0;
};
```

---

## 10.2 Implementations

### Implementation 1: Array-Based Stack

Using a fixed-size array with a `topIndex` pointer:

```cpp
#include <iostream>
#include <stdexcept>

template <typename T>
class ArrayStack {
    static constexpr int MAX_SIZE = 1000;
    T data[MAX_SIZE];
    int topIndex;

public:
    ArrayStack() : topIndex(-1) {}

    void push(const T& item) {
        if (topIndex >= MAX_SIZE - 1) {
            throw std::overflow_error("Stack overflow");
        }
        data[++topIndex] = item;
    }

    void pop() {
        if (empty()) {
            throw std::underflow_error("Stack underflow");
        }
        --topIndex;
    }

    const T& top() const {
        if (empty()) {
            throw std::underflow_error("Stack is empty");
        }
        return data[topIndex];
    }

    bool empty() const { return topIndex == -1; }
    int size() const { return topIndex + 1; }
};

int main() {
    ArrayStack<int> stk;
    stk.push(10);
    stk.push(20);
    stk.push(30);
    
    std::cout << "Top: " << stk.top() << "\n"; // 30
    stk.pop();
    std::cout << "Top: " << stk.top() << "\n"; // 20
    std::cout << "Size: " << stk.size() << "\n"; // 2
    return 0;
}
```

**Limitations:** Fixed maximum size. Wastes memory if the stack is usually small.

### Implementation 2: Dynamic Array-Based Stack

Using `std::vector` for automatic resizing:

```cpp
#include <iostream>
#include <vector>
#include <stdexcept>

template <typename T>
class DynamicStack {
    std::vector<T> data;

public:
    void push(const T& item) {
        data.push_back(item);
    }

    void pop() {
        if (empty()) {
            throw std::underflow_error("Stack is empty");
        }
        data.pop_back();
    }

    const T& top() const {
        if (empty()) {
            throw std::underflow_error("Stack is empty");
        }
        return data.back();
    }

    bool empty() const { return data.empty(); }
    int size() const { return data.size(); }
};
```

**Advantages:** No fixed size limit, automatic resizing. **Disadvantage:** Occasional O(n) resize on push (amortized O(1)).

### Implementation 3: Linked-List-Based Stack

```cpp
#include <iostream>
#include <stdexcept>

template <typename T>
class LinkedStack {
    struct Node {
        T data;
        Node* next;
        Node(const T& d, Node* n = nullptr) : data(d), next(n) {}
    };

    Node* head;
    int count;

public:
    LinkedStack() : head(nullptr), count(0) {}

    ~LinkedStack() {
        while (!empty()) pop();
    }

    // Disable copy for simplicity
    LinkedStack(const LinkedStack&) = delete;
    LinkedStack& operator=(const LinkedStack&) = delete;

    void push(const T& item) {
        head = new Node(item, head);
        ++count;
    }

    void pop() {
        if (empty()) {
            throw std::underflow_error("Stack is empty");
        }
        Node* old = head;
        head = head->next;
        delete old;
        --count;
    }

    const T& top() const {
        if (empty()) {
            throw std::underflow_error("Stack is empty");
        }
        return head->data;
    }

    bool empty() const { return head == nullptr; }
    int size() const { return count; }
};

int main() {
    LinkedStack<std::string> stk;
    stk.push("hello");
    stk.push("world");
    
    std::cout << "Top: " << stk.top() << "\n"; // world
    stk.pop();
    std::cout << "Top: " << stk.top() << "\n"; // hello
    return 0;
}
```

### Implementation 4: Using STL `std::stack`

```cpp
#include <iostream>
#include <stack>
#include <string>

int main() {
    std::stack<int> stk;
    
    // Push elements
    stk.push(10);
    stk.push(20);
    stk.push(30);
    
    // Access top
    std::cout << "Top: " << stk.top() << "\n"; // 30
    
    // Pop elements
    stk.pop();
    std::cout << "Top after pop: " << stk.top() << "\n"; // 20
    
    // Size and empty
    std::cout << "Size: " << stk.size() << "\n";   // 2
    std::cout << "Empty: " << stk.empty() << "\n"; // 0 (false)
    
    // Stack with different underlying container
    std::stack<std::string, std::vector<std::string>> vecStack;
    vecStack.push("hello");
    vecStack.push("world");
    std::cout << "Top: " << vecStack.top() << "\n"; // world
    
    return 0;
}
```

### Comparison of Implementations

| Feature | Array (Fixed) | Dynamic Array | Linked List | STL `std::stack` |
|---------|---------------|---------------|-------------|------------------|
| Push | O(1) | Amortized O(1) | O(1) | Amortized O(1) |
| Pop | O(1) | O(1) | O(1) | O(1) |
| Top | O(1) | O(1) | O(1) | O(1) |
| Space | O(n) fixed | O(n) | O(n) | O(n) |
| Cache friendly | Yes | Yes | No | Depends |
| Memory overhead | Low | Low | High (pointers) | Low |

**Recommendation:** Use `std::stack` in interviews unless asked to implement from scratch. It's clean, efficient, and idiomatic.

---

## 10.3 Applications

### Application 1: Undo Mechanism

Every action is pushed onto a stack. When the user presses "undo," the most recent action is popped and reversed.

```cpp
#include <iostream>
#include <stack>
#include <string>

class TextEditor {
    std::string text;
    std::stack<std::pair<std::string, std::string>> history; // {action, content}

public:
    void type(const std::string& newText) {
        history.push({"type", newText});
        text += newText;
    }
    
    void deleteLast(int count) {
        if (count > text.size()) count = text.size();
        std::string deleted = text.substr(text.size() - count);
        history.push({"delete", deleted});
        text.erase(text.size() - count);
    }
    
    void undo() {
        if (history.empty()) {
            std::cout << "Nothing to undo.\n";
            return;
        }
        auto [action, content] = history.top();
        history.pop();
        
        if (action == "type") {
            // Undo typing: remove the typed text
            text.erase(text.size() - content.size());
        } else if (action == "delete") {
            // Undo deletion: re-add the deleted text
            text += content;
        }
    }
    
    std::string getText() const { return text; }
};

int main() {
    TextEditor editor;
    editor.type("Hello");
    editor.type(" World");
    std::cout << editor.getText() << "\n"; // Hello World
    
    editor.undo();
    std::cout << editor.getText() << "\n"; // Hello
    
    editor.undo();
    std::cout << editor.getText() << "\n"; // (empty)
    
    return 0;
}
```

### Application 2: Browser Back Button

```cpp
#include <iostream>
#include <stack>
#include <string>

class Browser {
    std::stack<std::string> backStack;
    std::stack<std::string> forwardStack;
    std::string currentPage;

public:
    Browser() : currentPage("about:blank") {}
    
    void visit(const std::string& url) {
        if (!currentPage.empty()) {
            backStack.push(currentPage);
        }
        currentPage = url;
        // Clear forward history when visiting a new page
        while (!forwardStack.empty()) forwardStack.pop();
        std::cout << "Visited: " << currentPage << "\n";
    }
    
    void back() {
        if (backStack.empty()) {
            std::cout << "No page to go back to.\n";
            return;
        }
        forwardStack.push(currentPage);
        currentPage = backStack.top();
        backStack.pop();
        std::cout << "Back to: " << currentPage << "\n";
    }
    
    void forward() {
        if (forwardStack.empty()) {
            std::cout << "No page to go forward to.\n";
            return;
        }
        backStack.push(currentPage);
        currentPage = forwardStack.top();
        forwardStack.pop();
        std::cout << "Forward to: " << currentPage << "\n";
    }
    
    std::string getCurrent() const { return currentPage; }
};

int main() {
    Browser browser;
    browser.visit("google.com");
    browser.visit("stackoverflow.com");
    browser.visit("github.com");
    
    browser.back();    // stackoverflow.com
    browser.back();    // google.com
    browser.forward(); // stackoverflow.com
    
    browser.visit("reddit.com"); // Clears forward history
    browser.forward();           // Nothing to go forward to
    
    return 0;
}
```

### Application 3: Function Calls (The Call Stack)

As discussed in Chapter 8, the call stack is literally a stack. Each function call pushes a stack frame, and each return pops one. This is why deep recursion causes stack overflow.

---

## 10.4 Expression Evaluation

### Balanced Parentheses (Valid Parentheses)

The classic stack problem: determine if a string of brackets is balanced.

```cpp
#include <iostream>
#include <stack>
#include <string>

// Check if parentheses are balanced
// Time: O(n), Space: O(n)
bool isValid(const std::string& s) {
    std::stack<char> stk;
    
    for (char c : s) {
        if (c == '(' || c == '[' || c == '{') {
            stk.push(c);
        } else {
            if (stk.empty()) return false;
            
            char top = stk.top();
            stk.pop();
            
            if ((c == ')' && top != '(') ||
                (c == ']' && top != '[') ||
                (c == '}' && top != '{')) {
                return false;
            }
        }
    }
    return stk.empty(); // Must be empty for valid expression
}

int main() {
    std::cout << "([])  : " << (isValid("([])")  ? "valid" : "invalid") << "\n";
    std::cout << "([)]  : " << (isValid("([)]")  ? "valid" : "invalid") << "\n";
    std::cout << "{[]}  : " << (isValid("{[]}")  ? "valid" : "invalid") << "\n";
    std::cout << "(     : " << (isValid("(")      ? "valid" : "invalid") << "\n";
    return 0;
}
```

### Infix to Postfix Conversion (Shunting-Yard Algorithm)

Converting an infix expression like `3 + 4 * 2` to postfix `3 4 2 * +` is essential for expression evaluation.

**Operator Precedence:**

| Operator | Precedence | Associativity |
|----------|-----------|---------------|
| `+`, `-` | 1 | Left |
| `*`, `/` | 2 | Left |
| `^` | 3 | Right |

```cpp
#include <iostream>
#include <stack>
#include <string>
#include <cctype>

int precedence(char op) {
    if (op == '+' || op == '-') return 1;
    if (op == '*' || op == '/') return 2;
    if (op == '^') return 3;
    return 0;
}

bool isRightAssociative(char op) {
    return op == '^';
}

// Convert infix to postfix using Shunting-Yard algorithm
// Time: O(n), Space: O(n)
std::string infixToPostfix(const std::string& infix) {
    std::string postfix;
    std::stack<char> opStack;
    
    for (int i = 0; i < infix.size(); ++i) {
        char c = infix[i];
        
        if (std::isspace(c)) continue;
        
        if (std::isdigit(c) || std::isalpha(c)) {
            // Operand: add to output
            postfix += c;
            postfix += ' ';
        } else if (c == '(') {
            opStack.push(c);
        } else if (c == ')') {
            // Pop until matching '('
            while (!opStack.empty() && opStack.top() != '(') {
                postfix += opStack.top();
                postfix += ' ';
                opStack.pop();
            }
            if (!opStack.empty()) opStack.pop(); // Remove '('
        } else {
            // Operator
            while (!opStack.empty() && opStack.top() != '(' &&
                   (precedence(opStack.top()) > precedence(c) ||
                    (precedence(opStack.top()) == precedence(c) && !isRightAssociative(c)))) {
                postfix += opStack.top();
                postfix += ' ';
                opStack.pop();
            }
            opStack.push(c);
        }
    }
    
    // Pop remaining operators
    while (!opStack.empty()) {
        postfix += opStack.top();
        postfix += ' ';
        opStack.pop();
    }
    
    return postfix;
}

int main() {
    std::string expr = "3 + 4 * 2 / ( 1 - 5 ) ^ 2 ^ 3";
    std::cout << "Infix:   " << expr << "\n";
    std::cout << "Postfix: " << infixToPostfix(expr) << "\n";
    // Output: 3 4 2 * 1 5 - 2 3 ^ ^ / +
    return 0;
}
```

### Postfix Expression Evaluation

```cpp
#include <iostream>
#include <stack>
#include <string>
#include <sstream>
#include <cctype>
#include <cmath>

// Evaluate a postfix expression
// Time: O(n), Space: O(n)
double evaluatePostfix(const std::string& postfix) {
    std::stack<double> stk;
    std::istringstream iss(postfix);
    std::string token;
    
    while (iss >> token) {
        if (token.size() == 1 && std::ispunct(token[0])) {
            // Operator
            if (stk.size() < 2) {
                throw std::runtime_error("Invalid expression");
            }
            double b = stk.top(); stk.pop();
            double a = stk.top(); stk.pop();
            
            switch (token[0]) {
                case '+': stk.push(a + b); break;
                case '-': stk.push(a - b); break;
                case '*': stk.push(a * b); break;
                case '/': 
                    if (b == 0) throw std::runtime_error("Division by zero");
                    stk.push(a / b); 
                    break;
                case '^': stk.push(std::pow(a, b)); break;
                default:
                    throw std::runtime_error("Unknown operator");
            }
        } else {
            // Operand
            stk.push(std::stod(token));
        }
    }
    
    if (stk.size() != 1) {
        throw std::runtime_error("Invalid expression");
    }
    return stk.top();
}

int main() {
    // "3 4 2 * 1 5 - 2 3 ^ ^ / +"
    // = 3 + 4*2 / (1-5)^(2^3)
    // = 3 + 8 / (-4)^8
    // = 3 + 8 / 65536
    // = 3.000122...
    std::string postfix = "3 4 2 * 1 5 - 2 3 ^ ^ / +";
    std::cout << "Postfix: " << postfix << "\n";
    std::cout << "Result: " << evaluatePostfix(postfix) << "\n";
    
    // Simpler example: "5 1 2 + 4 * + 3 -"
    // = 5 + (1+2)*4 - 3 = 5 + 12 - 3 = 14
    std::string simple = "5 1 2 + 4 * + 3 -";
    std::cout << "Postfix: " << simple << "\n";
    std::cout << "Result: " << evaluatePostfix(simple) << "\n";
    
    return 0;
}
```

---

## 10.5 Next Greater Element

### The Problem

Given an array, for each element, find the **next greater element** — the first element to its right that is larger. If no such element exists, report -1.

**Example:** `[4, 5, 2, 25]` → `[5, 25, 25, -1]`

### Brute Force

```cpp
#include <iostream>
#include <vector>

// Brute force: for each element, scan right
// Time: O(n^2), Space: O(1)
std::vector<int> nextGreaterBruteForce(const std::vector<int>& arr) {
    int n = arr.size();
    std::vector<int> result(n, -1);
    
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (arr[j] > arr[i]) {
                result[i] = arr[j];
                break;
            }
        }
    }
    return result;
}
```

### Monotonic Stack Approach

The key insight: process elements from **right to left**, maintaining a stack of elements in **decreasing order** (a monotonic decreasing stack).

```cpp
#include <iostream>
#include <vector>
#include <stack>

// Monotonic stack: process right to left
// Time: O(n), Space: O(n)
// Each element is pushed and popped at most once
std::vector<int> nextGreater(const std::vector<int>& arr) {
    int n = arr.size();
    std::vector<int> result(n, -1);
    std::stack<int> stk; // Stack stores indices (or values)
    
    for (int i = n - 1; i >= 0; --i) {
        // Pop elements that are not greater than arr[i]
        while (!stk.empty() && stk.top() <= arr[i]) {
            stk.pop();
        }
        // If stack is not empty, top is the next greater element
        if (!stk.empty()) {
            result[i] = stk.top();
        }
        stk.push(arr[i]);
    }
    return result;
}

int main() {
    std::vector<int> arr = {4, 5, 2, 25, 10};
    auto result = nextGreater(arr);
    
    std::cout << "Array:           ";
    for (int v : arr) std::cout << v << " ";
    std::cout << "\nNext Greater:    ";
    for (int v : result) std::cout << v << " ";
    std::cout << "\n";
    // Output: 5 25 25 -1 -1
    return 0;
}
```

**Dry Run for `[4, 5, 2, 25]`:**

```
Processing right to left:

i=3, arr[3]=25:
  Stack is empty → result[3] = -1
  Push 25. Stack: [25]

i=2, arr[2]=2:
  Top=25 > 2 → result[2] = 25
  Push 2. Stack: [25, 2]

i=1, arr[1]=5:
  Top=2 ≤ 5 → pop 2
  Top=25 > 5 → result[1] = 25
  Push 5. Stack: [25, 5]

i=0, arr[0]=4:
  Top=5 > 4 → result[0] = 5
  Push 4. Stack: [25, 5, 4]

Result: [5, 25, 25, -1]
```

### Why Does the Monotonic Stack Work?

The stack maintains elements in decreasing order from top to bottom. When we encounter a new element:
- All smaller elements on the stack cannot be the "next greater" for any element to the left (the new element is closer and smaller). So we pop them.
- The remaining top of the stack is the first element to the right that is greater.

### Variation 1: Next Greater Element II (Circular Array)

```cpp
#include <iostream>
#include <vector>
#include <stack>

// Next greater element in a circular array
// Trick: process the array twice (simulate circular)
std::vector<int> nextGreaterCircular(const std::vector<int>& arr) {
    int n = arr.size();
    std::vector<int> result(n, -1);
    std::stack<int> stk;
    
    for (int i = 2 * n - 1; i >= 0; --i) {
        while (!stk.empty() && stk.top() <= arr[i % n]) {
            stk.pop();
        }
        if (i < n && !stk.empty()) {
            result[i] = stk.top();
        }
        stk.push(arr[i % n]);
    }
    return result;
}

int main() {
    std::vector<int> arr = {1, 2, 1};
    auto result = nextGreaterCircular(arr);
    
    std::cout << "Array:           ";
    for (int v : arr) std::cout << v << " ";
    std::cout << "\nNext Greater (circular): ";
    for (int v : result) std::cout << v << " ";
    std::cout << "\n";
    // Output: 2 -1 2
    return 0;
}
```

### Variation 2: Daily Temperatures

Given an array of temperatures, for each day, find how many days you must wait until a warmer temperature.

```cpp
#include <iostream>
#include <vector>
#include <stack>

// Daily Temperatures
// Time: O(n), Space: O(n)
std::vector<int> dailyTemperatures(const std::vector<int>& temps) {
    int n = temps.size();
    std::vector<int> result(n, 0);
    std::stack<int> stk; // Stack of indices
    
    for (int i = 0; i < n; ++i) {
        // Pop all indices with smaller temperature
        while (!stk.empty() && temps[stk.top()] < temps[i]) {
            int prevDay = stk.top();
            stk.pop();
            result[prevDay] = i - prevDay;
        }
        stk.push(i);
    }
    return result;
}

int main() {
    std::vector<int> temps = {73, 74, 75, 71, 69, 72, 76, 73};
    auto result = dailyTemperatures(temps);
    
    std::cout << "Temperatures: ";
    for (int t : temps) std::cout << t << " ";
    std::cout << "\nDays to wait: ";
    for (int d : result) std::cout << d << " ";
    std::cout << "\n";
    // Output: 1 1 4 2 1 1 0 0
    return 0;
}
```

### Variation 3: Largest Rectangle in Histogram

```cpp
#include <iostream>
#include <vector>
#include <stack>

// Largest rectangle in histogram
// Time: O(n), Space: O(n)
int largestRectangleArea(const std::vector<int>& heights) {
    int n = heights.size();
    std::stack<int> stk;
    int maxArea = 0;
    
    for (int i = 0; i <= n; ++i) {
        int h = (i == n) ? 0 : heights[i];
        while (!stk.empty() && h < heights[stk.top()]) {
            int height = heights[stk.top()];
            stk.pop();
            int width = stk.empty() ? i : i - stk.top() - 1;
            maxArea = std::max(maxArea, height * width);
        }
        stk.push(i);
    }
    return maxArea;
}

int main() {
    std::vector<int> heights = {2, 1, 5, 6, 2, 3};
    std::cout << "Largest rectangle area: " 
              << largestRectangleArea(heights) << "\n";
    // Output: 10 (5*2 = 10, from bars with heights 5 and 6)
    return 0;
}
```

---

## Interview Tips

1. **Recognize stack patterns:** Whenever you need "next greater/smaller," "previous greater/smaller," or "matching/nesting," think stack.
2. **Monotonic stack is your friend:** It solves a whole family of problems in O(n) time.
3. **Know the STL:** `std::stack` wraps `std::deque` by default. Use `std::vector` as the underlying container for better cache performance.
4. **Two-pass technique:** For problems like "next greater element II" (circular), process the array twice.
5. **Stack of indices vs. values:** Storing indices is often more useful because you can compute distances and positions.

## Common Mistakes

| Mistake | Example | Fix |
|---------|---------|-----|
| Not checking `empty()` before `top()`/`pop()` | Accessing top of empty stack | Always check `empty()` first |
| Forgetting to handle remaining elements | In infix-to-postfix, not popping all operators | Pop all remaining operators at the end |
| Wrong precedence in Shunting-Yard | Treating `+` same as `*` | Implement a correct precedence function |
| Confusing left and right associativity | `2^3^4` should be `2^(3^4)`, not `(2^3)^4` | Handle right-associative operators specially |
| Off-by-one in monotonic stack | Processing indices incorrectly | Use `<=` vs `<` consistently |
| Not clearing the stack | Reusing a stack without popping all elements | Call a clear loop or use a fresh stack |

---

## Practice Problems

### Easy

1. **Valid Parentheses** — Given a string containing just `()[]{}{}`, determine if the input is valid.
   - *Hint:* Push opening brackets, pop and match closing brackets.

2. **Implement Stack using Queues** — Implement a stack using only queue operations.
   - *Hint:* Use two queues; on push, enqueue to the second queue, then move all elements from the first queue.

3. **Min Stack** — Design a stack that supports `push`, `pop`, `top`, and `getMin` in O(1).
   - *Hint:* Use a second stack to track the minimum at each level.

### Medium

4. **Evaluate Reverse Polish Notation** — Evaluate the value of an arithmetic expression in Reverse Polish Notation.
   - *Hint:* Push operands; on operator, pop two, compute, push result.

5. **Daily Temperatures** — Given daily temperatures, find how many days until a warmer temperature.
   - *Hint:* Monotonic stack of indices, process left to right.

6. **Decode String** — Given an encoded string like `3[a2[c]]`, decode it.
   - *Hint:* Use two stacks: one for counts, one for strings.

### Hard

7. **Largest Rectangle in Histogram** — Find the area of the largest rectangle in a histogram.
   - *Hint:* Monotonic increasing stack. When a shorter bar is found, compute area for all taller bars.

8. **Trapping Rain Water** — Given an elevation map, compute how much water it can trap.
   - *Hint:* Use a stack of indices; when a taller bar is found, compute trapped water.

9. **Maximal Rectangle** — Given a 2D binary matrix, find the largest rectangle containing only 1s.
   - *Hint:* Convert each row to a histogram and apply the histogram algorithm.

---

## Complexity Summary

| Operation/Algorithm | Time | Space |
|--------------------|------|-------|
| Stack push/pop/top | O(1) | O(n) |
| Valid Parentheses | O(n) | O(n) |
| Infix to Postfix | O(n) | O(n) |
| Postfix Evaluation | O(n) | O(n) |
| Next Greater Element | O(n) | O(n) |
| Daily Temperatures | O(n) | O(n) |
| Largest Rectangle | O(n) | O(n) |
