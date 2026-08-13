# C Interview Questions

## Overview

This section contains 30+ frequently asked C interview questions with detailed answers. These cover fundamental concepts, memory management, pointers, data structures, and advanced topics commonly tested in technical interviews.

## Fundamentals

### 1. What is the difference between `++i` and `i++`?

**Answer:**

`++i` (pre-increment) increments `i` first, then returns the new value. `i++` (post-increment) returns the current value, then increments `i`.

```c
int i = 5;
int a = ++i;  // i becomes 6, a = 6
int b = i++;  // b = 6, i becomes 7

// In loops, they're usually equivalent:
for (int i = 0; i < 10; ++i) { }  // Same as i++
// But ++i is marginally more efficient with user-defined types (C++ only)
```

**Key insight:** In C with primitive types, there's no performance difference. The distinction matters for side effects in complex expressions.

### 2. What is the difference between `=` and `==`?

**Answer:**

`=` is the assignment operator (stores a value). `==` is the equality comparison operator (returns true/false).

```c
int x = 5;      // Assignment: x now holds 5
if (x == 5) {   // Comparison: is x equal to 5?
    printf("Equal\n");
}

// Common bug:
if (x = 10) {   // Assignment, NOT comparison! Always true (10 is non-zero)
    printf("This always executes!\n");
    // x is now 10
}

// Fix: Put constant on left (Yoda conditions)
if (10 == x) {  // Compiler error if you accidentally write 10 = x
    printf("Equal\n");
}
```

### 3. What are storage classes in C?

**Answer:**

Storage classes define the scope, lifetime, and linkage of variables.

| Storage Class | Scope | Lifetime | Initial Value | Linkage |
|--------------|-------|----------|---------------|---------|
| `auto` | Block | Block execution | Garbage | None |
| `register` | Block | Block execution | Garbage | None |
| `static` (local) | Block | Program lifetime | Zero | None |
| `static` (global) | File | Program lifetime | Zero | Internal |
| `extern` | File | Program lifetime | Zero | External |

```c
// auto (default for local variables)
void func() {
    auto int x = 5;  // 'auto' is implicit
}

// static local — persists between function calls
void counter() {
    static int count = 0;  // Initialized only once
    count++;
    printf("Called %d times\n", count);
}

// extern — declare variable defined elsewhere
extern int global_var;  // Defined in another file

// register — hint to store in CPU register
register int fast_var = 10;  // Cannot take address: &fast_var is error
```

### 4. What is the difference between `struct` and `union`?

**Answer:**

A `struct` allocates memory for all members separately. A `union` shares the same memory for all members.

```c
#include <stdio.h>

struct StructExample {
    int a;      // 4 bytes
    double b;   // 8 bytes
    char c;     // 1 byte + padding
};  // Total: ~24 bytes (with padding)

union UnionExample {
    int a;      // 4 bytes
    double b;   // 8 bytes
    char c;     // 1 byte
};  // Total: 8 bytes (largest member)

int main() {
    printf("Struct size: %zu\n", sizeof(struct StructExample));  // 24
    printf("Union size: %zu\n", sizeof(union UnionExample));     // 8
    
    union UnionExample u;
    u.a = 42;
    printf("a = %d\n", u.a);    // 42
    u.b = 3.14;
    printf("b = %f\n", u.b);    // 3.14
    printf("a = %d\n", u.a);    // Garbage! (overwritten by b)
    
    return 0;
}
```

### 5. What is the `volatile` keyword?

**Answer:**

`volatile` tells the compiler that a variable's value can change at any time (by hardware, interrupt, or another thread), preventing optimizations that assume the value doesn't change.

```c
// Without volatile — compiler might optimize away repeated reads
int *status_reg = (int*)0x40001000;
while (*status_reg == 0) {  // Compiler might read once and loop forever
    wait();
}

// With volatile — compiler reads from memory every time
volatile int *status_reg = (volatile int*)0x40001000;
while (*status_reg == 0) {  // Reads from hardware register each iteration
    wait();
}

// Also useful for variables modified by signal handlers or other threads
volatile int flag = 0;

void signal_handler(int sig) {
    flag = 1;  // Modified by signal
}

int main() {
    signal(SIGINT, signal_handler);
    while (!flag) {  // Without volatile, compiler might optimize this away
        // Wait for signal
    }
    return 0;
}
```

## Pointers and Memory

### 6. What is the difference between `char *s = "hello"` and `char s[] = "hello"`?

**Answer:**

`char *s = "hello"` creates a pointer to a string literal (read-only memory). `char s[] = "hello"` creates a modifiable array initialized with the string.

```c
char *s1 = "hello";    // Pointer to string literal
char s2[] = "hello";   // Modifiable array

// s1[0] = 'H';  // UNDEFINED BEHAVIOR — writing to read-only memory
s2[0] = 'H';        // OK — modifying the array

printf("sizeof(s1) = %zu\n", sizeof(s1));  // 8 (pointer size)
printf("sizeof(s2) = %zu\n", sizeof(s2));  // 6 (5 chars + null terminator)

// s1 can be reassigned to point elsewhere
s1 = "world";       // OK
// s2 = "world";    // ERROR — can't reassign array name
```

### 7. What is a memory leak? How do you prevent it?

**Answer:**

A memory leak occurs when dynamically allocated memory is never freed, causing the program to consume more and more memory over time.

```c
// Leak: forgot to free
void leak() {
    int *p = malloc(100 * sizeof(int));
    // ... use p ...
    // Return without free — memory leaked!
}

// Leak: lost pointer
void leak2() {
    int *p = malloc(100 * sizeof(int));
    p = malloc(200 * sizeof(int));  // First allocation leaked!
    free(p);
}

// Prevention strategies:
// 1. Always free what you allocate
void no_leak() {
    int *p = malloc(100 * sizeof(int));
    // ... use p ...
    free(p);
    p = NULL;
}

// 2. Use cleanup patterns
void cleanup_pattern() {
    int *arr = NULL;
    char *str = NULL;
    int result = -1;
    
    arr = malloc(100 * sizeof(int));
    if (!arr) goto cleanup;
    
    str = malloc(256);
    if (!str) goto cleanup;
    
    // ... do work ...
    result = 0;

cleanup:
    free(arr);
    free(str);
    return result;
}

// 3. Use Valgrind to detect leaks
// valgrind --leak-check=full ./program
```

### 8. Explain pointer arithmetic with an example.

**Answer:**

Pointer arithmetic adjusts the address by `n * sizeof(type)` bytes.

```c
#include <stdio.h>

int main() {
    int arr[] = {10, 20, 30, 40, 50};
    int *p = arr;  // Points to arr[0]
    
    printf("*p = %d\n", *p);         // 10
    printf("*(p+1) = %d\n", *(p+1)); // 20 (p + 1*sizeof(int) bytes)
    printf("*(p+2) = %d\n", *(p+2)); // 30
    
    // Pointer subtraction gives distance in elements
    int *start = &arr[0];
    int *end = &arr[4];
    ptrdiff_t distance = end - start;  // 4 (elements, not bytes)
    printf("Distance: %ld elements\n", distance);
    printf("Bytes apart: %ld\n", (char*)end - (char*)start);  // 16 bytes
    
    // Array indexing is pointer arithmetic: arr[i] == *(arr + i)
    for (int i = 0; i < 5; i++) {
        printf("arr[%d] = %d, *(arr+%d) = %d\n", i, arr[i], i, *(arr+i));
    }
    
    return 0;
}
```

### 9. What is a `void` pointer and when is it used?

**Answer:**

A `void *` is a generic pointer that can point to any data type. It cannot be dereferenced directly.

```c
#include <stdlib.h>
#include <string.h>

// Generic swap function
void swap(void *a, void *b, size_t size) {
    void *temp = malloc(size);
    memcpy(temp, a, size);
    memcpy(a, b, size);
    memcpy(b, temp, size);
    free(temp);
}

// qsort comparison function uses void pointers
int compare_ints(const void *a, const void *b) {
    return *(int*)a - *(int*)b;
}

int main() {
    int x = 5, y = 10;
    swap(&x, &y, sizeof(int));
    printf("x=%d, y=%d\n", x, y);  // x=10, y=5
    
    int arr[] = {5, 2, 8, 1, 9};
    qsort(arr, 5, sizeof(int), compare_ints);
    // arr is now {1, 2, 5, 8, 9}
    
    return 0;
}
```

### 10. What is the output of this code?

```c
#include <stdio.h>
int main() {
    int arr[] = {1, 2, 3, 4, 5};
    int *p = (int*)(&arr + 1);
    printf("%d\n", *(p - 1));
    return 0;
}
```

**Answer:** Output is `5`.

- `&arr` has type `int(*)[5]` — pointer to array of 5 ints
- `&arr + 1` moves past the entire array (to the address after `arr[4]`)
- Cast to `int*`, then `p - 1` moves back one `int` to `arr[4]`
- `*(p - 1)` = `arr[4]` = `5`

## Data Structures

### 11. Implement a linked list in C.

**Answer:**

```c
#include <stdio.h>
#include <stdlib.h>

typedef struct Node {
    int data;
    struct Node *next;
} Node;

Node* create_node(int data) {
    Node *node = malloc(sizeof(Node));
    if (!node) return NULL;
    node->data = data;
    node->next = NULL;
    return node;
}

void push_front(Node **head, int data) {
    Node *node = create_node(data);
    if (!node) return;
    node->next = *head;
    *head = node;
}

void push_back(Node **head, int data) {
    Node *node = create_node(data);
    if (!node) return;
    if (*head == NULL) {
        *head = node;
        return;
    }
    Node *curr = *head;
    while (curr->next) curr = curr->next;
    curr->next = node;
}

void delete_node(Node **head, int data) {
    Node *curr = *head, *prev = NULL;
    while (curr && curr->data != data) {
        prev = curr;
        curr = curr->next;
    }
    if (!curr) return;  // Not found
    if (prev) prev->next = curr->next;
    else *head = curr->next;
    free(curr);
}

void free_list(Node **head) {
    Node *curr = *head;
    while (curr) {
        Node *next = curr->next;
        free(curr);
        curr = next;
    }
    *head = NULL;
}

void print_list(Node *head) {
    while (head) {
        printf("%d -> ", head->data);
        head = head->next;
    }
    printf("NULL\n");
}
```

### 12. Implement a stack using an array.

**Answer:**

```c
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int *data;
    int top;
    int capacity;
} Stack;

Stack* stack_create(int capacity) {
    Stack *s = malloc(sizeof(Stack));
    s->data = malloc(capacity * sizeof(int));
    s->top = -1;
    s->capacity = capacity;
    return s;
}

int stack_push(Stack *s, int value) {
    if (s->top >= s->capacity - 1) return -1;  // Full
    s->data[++s->top] = value;
    return 0;
}

int stack_pop(Stack *s) {
    if (s->top < 0) return -1;  // Empty
    return s->data[s->top--];
}

int stack_peek(Stack *s) {
    if (s->top < 0) return -1;
    return s->data[s->top];
}

int stack_is_empty(Stack *s) {
    return s->top < 0;
}

void stack_destroy(Stack *s) {
    free(s->data);
    free(s);
}
```

### 13. Implement a hash table in C.

**Answer:**

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TABLE_SIZE 101

typedef struct Entry {
    char *key;
    int value;
    struct Entry *next;
} Entry;

typedef struct {
    Entry *buckets[TABLE_SIZE];
} HashTable;

unsigned long hash(const char *key) {
    unsigned long h = 5381;
    int c;
    while ((c = *key++)) {
        h = ((h << 5) + h) + c;  // h * 33 + c (djb2)
    }
    return h % TABLE_SIZE;
}

HashTable* ht_create() {
    HashTable *ht = calloc(1, sizeof(HashTable));
    return ht;
}

void ht_insert(HashTable *ht, const char *key, int value) {
    unsigned long idx = hash(key);
    Entry *entry = ht->buckets[idx];
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            entry->value = value;  // Update existing
            return;
        }
        entry = entry->next;
    }
    // New entry — insert at head
    Entry *new_entry = malloc(sizeof(Entry));
    new_entry->key = strdup(key);
    new_entry->value = value;
    new_entry->next = ht->buckets[idx];
    ht->buckets[idx] = new_entry;
}

int ht_get(HashTable *ht, const char *key, int *value) {
    unsigned long idx = hash(key);
    Entry *entry = ht->buckets[idx];
    while (entry) {
        if (strcmp(entry->key, key) == 0) {
            *value = entry->value;
            return 1;  // Found
        }
        entry = entry->next;
    }
    return 0;  // Not found
}

void ht_destroy(HashTable *ht) {
    for (int i = 0; i < TABLE_SIZE; i++) {
        Entry *entry = ht->buckets[i];
        while (entry) {
            Entry *next = entry->next;
            free(entry->key);
            free(entry);
            entry = next;
        }
    }
    free(ht);
}
```

## Advanced Topics

### 14. What is the difference between `const int *p`, `int * const p`, and `const int * const p`?

**Answer:**

```c
int x = 5, y = 10;

// Pointer to constant int — can't modify the value
const int *p1 = &x;
// *p1 = 20;  // ERROR: can't modify value through p1
p1 = &y;     // OK: can change what p1 points to

// Constant pointer to int — can't change what it points to
int * const p2 = &x;
*p2 = 20;    // OK: can modify the value
// p2 = &y;  // ERROR: can't change p2 itself

// Constant pointer to constant int — can't change anything
const int * const p3 = &x;
// *p3 = 20;  // ERROR
// p3 = &y;   // ERROR

// Read right-to-left:
// const int *p    → "p is a pointer to int that is const"
// int * const p   → "p is a const pointer to int"
// const int * const p → "p is a const pointer to int that is const"
```

### 15. What is a function pointer and how is it used?

**Answer:**

A function pointer stores the address of a function, enabling callbacks and dynamic dispatch.

```c
#include <stdio.h>
#include <stdlib.h>

// Comparison function type
typedef int (*CompareFunc)(const void *, const void *);

int ascending(const void *a, const void *b) {
    return *(int*)a - *(int*)b;
}

int descending(const void *a, const void *b) {
    return *(int*)b - *(int*)a;
}

// Strategy pattern using function pointers
typedef struct {
    int (*add)(int, int);
    int (*subtract)(int, int);
} Calculator;

int add_op(int a, int b) { return a + b; }
int sub_op(int a, int b) { return a - b; }

int main() {
    int arr[] = {5, 2, 8, 1, 9};
    
    // Use function pointer with qsort
    CompareFunc cmp = ascending;
    qsort(arr, 5, sizeof(int), cmp);
    
    // Array of function pointers
    int (*ops[])(int, int) = {add_op, sub_op};
    printf("3 + 4 = %d\n", ops[0](3, 4));  // 7
    printf("3 - 4 = %d\n", ops[1](3, 4));  // -1
    
    return 0;
}
```

### 16. What is the `static` keyword used for?

**Answer:**

`static` has three different uses depending on context:

```c
// 1. Static local variable — persists between function calls
void counter() {
    static int count = 0;  // Initialized only once
    count++;
    printf("Called %d times\n", count);
}

// 2. Static global variable — file-scoped (internal linkage)
static int file_private = 42;  // Only visible in this file

// 3. Static function — file-scoped (internal linkage)
static void helper_function() {  // Only callable from this file
    // ...
}

// Without static: external linkage (visible to other files via extern)
int global_var = 100;  // Any file can access with 'extern int global_var;'
```

### 17. Explain `sizeof` behavior with arrays and pointers.

**Answer:**

```c
#include <stdio.h>
#include <string.h>

void func(int arr[]) {
    // arr decays to pointer here!
    printf("sizeof(arr) in func = %zu\n", sizeof(arr));  // 8 (pointer size)
}

int main() {
    int arr[10] = {0};
    int *p = arr;
    
    printf("sizeof(arr) = %zu\n", sizeof(arr));  // 40 (10 * 4)
    printf("sizeof(p) = %zu\n", sizeof(p));       // 8 (pointer size)
    printf("sizeof(*p) = %zu\n", sizeof(*p));     // 4 (int size)
    
    func(arr);  // Array decays to pointer in function parameter
    
    char str[] = "Hello";
    printf("sizeof(str) = %zu\n", sizeof(str));   // 6 (5 + null)
    printf("strlen(str) = %zu\n", strlen(str));   // 5 (without null)
    
    return 0;
}
```

### 18. What is the difference between `memcpy` and `memmove`?

**Answer:**

```c
#include <string.h>

// memcpy: fast but undefined behavior if source and destination overlap
void *memcpy(void *dest, const void *src, size_t n);

// memmove: safe with overlapping regions (slightly slower)
void *memmove(void *dest, const void *src, size_t n);

// Example of overlap:
char buffer[] = "Hello, World!";
// Move "World" to overlap with "Hello"
memmove(buffer, buffer + 7, 6);  // Safe: "World!" + null
// memcpy(buffer, buffer + 7, 6);  // UNDEFINED BEHAVIOR: regions overlap
```

### 19. What are bit fields in structures?

**Answer:**

Bit fields allow packing data into individual bits within a structure:

```c
#include <stdio.h>

struct Flags {
    unsigned int bold      : 1;  // 1 bit
    unsigned int italic    : 1;  // 1 bit
    unsigned int underline : 1;  // 1 bit
    unsigned int size      : 4;  // 4 bits (0-15)
    unsigned int color     : 3;  // 3 bits (0-7)
};  // Total: 10 bits, but compiler may pad

// Useful for hardware registers, network protocols, compact storage
struct PacketHeader {
    unsigned int version   : 4;
    unsigned int ihl       : 4;
    unsigned int dscp      : 6;
    unsigned int ecn       : 2;
    unsigned int length    : 16;
};

int main() {
    struct Flags f = {0};
    f.bold = 1;
    f.size = 12;
    f.color = 5;
    
    printf("sizeof(Flags) = %zu\n", sizeof(struct Flags));  // 4 bytes
    printf("bold=%u, size=%u, color=%u\n", f.bold, f.size, f.color);
    
    return 0;
}
```

### 20. What is `restrict` keyword?

**Answer:**

`restrict` (C99) is a pointer qualifier that tells the compiler the pointer is the only way to access the memory it points to, enabling aggressive optimizations.

```c
// Without restrict — compiler must assume overlap
void add(int *a, int *b, int *c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
        // Compiler can't assume c doesn't overlap with a or b
    }
}

// With restrict — compiler knows no overlap
void add_restrict(int *restrict a, int *restrict b, 
                  int *restrict c, int n) {
    for (int i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
        // Compiler can optimize more aggressively
    }
}

// Real-world: memcpy uses restrict, memmove doesn't
// void *memcpy(void *restrict dest, const void *restrict src, size_t n);
// void *memmove(void *dest, const void *src, size_t n);
```

## More Questions

### 21-30: Quick-Fire Questions

**21. What is the output of `printf("%d", printf("Hello"));`?**
Output: `Hello5` (prints "Hello" then prints 5, the return value of the inner printf).

**22. Can we use `sizeof` on a function?**
No, `sizeof` cannot be applied to functions. It works on types and expressions.

**23. What is a null pointer vs null character?**
- Null pointer: `NULL` or `(void*)0` — pointer that points to nothing
- Null character: `'\0'` or `0` — character with value zero (string terminator)

**24. What is the difference between `exit()` and `return`?**
- `return` exits the current function
- `exit()` terminates the entire program (calls atexit handlers, flushes buffers)

**25. What are variadic functions?**
Functions that accept a variable number of arguments, like `printf`. Use `<stdarg.h>`:
```c
#include <stdarg.h>
int sum(int count, ...) {
    va_list args;
    va_start(args, count);
    int total = 0;
    for (int i = 0; i < count; i++) {
        total += va_arg(args, int);
    }
    va_end(args);
    return total;
}
```

**26. What is the comma operator?**
Evaluates all expressions left-to-right and returns the value of the last one:
```c
int x = (1, 2, 3);  // x = 3
```

**27. What is the difference between `#include <file>` and `#include "file"`?**
- `<file>`: searches system include paths
- `"file"`: searches current directory first, then system paths

**28. What is a flexible array member (C99)?**
```c
struct FlexArray {
    int size;
    int data[];  // Must be last member
};
struct FlexArray *fa = malloc(sizeof(struct FlexArray) + 10 * sizeof(int));
fa->size = 10;
```

**29. What is `_Generic` (C11)?**
Type-generic selection at compile time:
```c
#define type_name(x) _Generic((x), \
    int: "int", \
    float: "float", \
    char*: "string", \
    default: "unknown")
```

**30. What is `_Atomic` (C11)?**
Provides atomic operations for lock-free programming:
```c
#include <stdatomic.h>
atomic_int counter = 0;
atomic_fetch_add(&counter, 1);  // Thread-safe increment
```

### 31-35: Code Analysis Questions

**31. What's wrong with this code?**
```c
char *get_string() {
    char str[] = "Hello";
    return str;  // Returns address of local variable!
}
```
**Fix:** Use `static char str[]` or `return "Hello"` (string literal) or allocate with `malloc`.

**32. What's the bug here?**
```c
int *arr = malloc(10 * sizeof(int));
for (int i = 0; i <= 10; i++) {
    arr[i] = i;  // Buffer overflow at i=10
}
```
**Fix:** Change `i <= 10` to `i < 10`.

**33. Predict the output:**
```c
int x = 1;
printf("%d %d %d", x++, x++, x++);
```
**Answer:** Undefined behavior. The output is compiler-dependent.

**34. What does this evaluate to?**
```c
int x = 5;
int y = ++x * ++x;
```
**Answer:** Undefined behavior (sequence point violation).

**35. Is this valid C?**
```c
void func(int n, int arr[n]) {
    // Variable-length array parameter (C99)
}
```
**Answer:** Yes, valid C99. The parameter `n` is evaluated before `arr[n]`.

## Related Topics

- [Pointers](./pointers.md) — Deep dive into pointer concepts
- [Memory Management](./memory-management.md) — Dynamic allocation patterns
- [Undefined Behavior](./undefined-behavior.md) — Common pitfalls
- [Compilation](./compilation.md) — Understanding the build process
- [POSIX](./posix.md) — System programming concepts
- [Performance](./performance.md) — Writing efficient C code
