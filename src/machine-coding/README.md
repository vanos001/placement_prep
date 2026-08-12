# Machine Coding Round Preparation

## What is a Machine Coding Round?

A machine coding round is a **hands-on coding interview** (typically 60–90 minutes) where you design and implement a working system from scratch. Unlike DSA rounds that test algorithmic thinking, machine coding evaluates your ability to **build real software** — clean code, good design, and working functionality.

Companies like **Flipkart, Uber, Walmart, PhonePe, CRED, Ola, Meesho**, and many startups use this round extensively.

## What Interviewers Evaluate

### 1. Requirements Gathering (10–15%)
- Do you ask clarifying questions before coding?
- Do you identify edge cases upfront?
- Do you define scope and prioritize features?

### 2. Class Design & Architecture (25–30%)
- Are your classes cohesive with clear responsibilities?
- Do you use appropriate design patterns?
- Is your design extensible and maintainable?
- Do you follow SOLID principles?

### 3. Code Quality (20–25%)
- Clean, readable, well-structured code
- Proper naming conventions
- Error handling and input validation
- No code duplication (DRY principle)

### 4. Working Solution (25–30%)
- Does the code compile and run?
- Do core features work correctly?
- Can you demo the solution?
- Are edge cases handled?

### 5. Communication & Problem-Solving (10–15%)
- Do you explain your thought process?
- How do you handle feedback and pivots?
- Do you manage time effectively?

## Common Machine Coding Problems

| Problem | Key Concepts | Difficulty |
|---------|-------------|------------|
| Parking Lot | OOP, Strategy Pattern, Enums | Medium |
| Elevator System | State Machine, Scheduling | Medium-Hard |
| Library Management | CRUD, Relationships, Fines | Medium |
| Splitwise | Graph Algorithms, Settlement | Medium |
| Rate Limiter | Algorithms, Concurrency | Medium-Hard |
| LRU Cache | Data Structures, O(1) ops | Medium |
| Task Scheduler | Priority Queues, Dependencies | Medium-Hard |
| URL Shortener | Hashing, Database Design | Easy-Medium |
| Chess/Board Game | State Machine, Rules Engine | Hard |
| Cab Booking | Matching, Geo-spatial | Hard |

## Time Management Strategy

```
Total Time: 75 minutes (typical)

[0-5 min]   → Read requirements, ask questions
[5-15 min]  → Identify entities, relationships, design classes
[15-20 min] → Discuss approach with interviewer
[20-55 min] → Implement core functionality
[55-65 min] → Test, fix bugs, handle edge cases
[65-75 min] → Refactor, discuss improvements
```

## General Approach

1. **Start with requirements** — list functional and non-functional requirements
2. **Identify entities** — what are the core objects?
3. **Define relationships** — how do entities interact?
4. **Choose design patterns** — which patterns fit naturally?
5. **Implement incrementally** — core features first, then enhancements
6. **Test as you go** — don't wait until the end

## Files in This Section

- [approach.md](approach.md) — Detailed approach methodology
- [design-principles.md](design-principles.md) — SOLID and design patterns
- [parking-lot.md](parking-lot.md) — Parking lot system
- [elevator.md](elevator.md) — Elevator system
- [library-management.md](library-management.md) — Library management
- [splitwise.md](splitwise.md) — Expense splitting
- [rate-limiter.md](rate-limiter.md) — Rate limiter
- [cache-lru.md](cache-lru.md) — LRU cache
- [task-scheduler.md](task-scheduler.md) — Task scheduler

## Tips for Success

1. **Practice on paper first** — sketch class diagrams before coding
2. **Use your IDE well** — know shortcuts, auto-complete, debugging
3. **Start simple** — get a working skeleton, then add features
4. **Don't over-engineer** — interviewer wants working code, not a perfect framework
5. **Talk through decisions** — explain WHY you chose a pattern or structure
6. **Handle errors gracefully** — null checks, invalid inputs, edge cases
7. **Write testable code** — even if you don't write tests, make it testable
