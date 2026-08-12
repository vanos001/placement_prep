# Software Engineering Interview Questions

## SDLC & Methodology

### Beginner

**Q: What is the difference between Agile and Waterfall?**
A: Waterfall is sequential (requirements → design → build → test → deploy). Agile is iterative with short sprints, continuous feedback, and working software. Waterfall suits fixed requirements; Agile suits changing requirements.

**Q: What are the Scrum ceremonies?**
A: Sprint Planning (plan work), Daily Standup (15-min sync), Sprint Review (demo to stakeholders), Sprint Retrospective (improve process).

**Q: What is a user story?**
A: "As a [role], I want [feature], so that [benefit]." It captures requirements from the user's perspective with acceptance criteria for when it's "done."

### Intermediate

**Q: How do you estimate work in Agile?**
A: Story points (relative sizing using Fibonacci), planning poker (team consensus), t-shirt sizing (XS-XL). Focus on relative complexity, not absolute hours.

**Q: What is technical debt? How do you manage it?**
A: Intentional or unintentional shortcuts that make future changes harder. Manage by: (1) tracking it explicitly, (2) allocating sprint capacity (e.g., 20%), (3) addressing high-interest debt first, (4) preventing new debt via code review.

### Advanced

**Q: How would you handle a project that's behind schedule?**
A: (1) Identify the critical path, (2) reduce scope (negotiate with stakeholders), (3) add buffer to remaining estimates, (4) address blockers immediately, (5) consider parallel work streams, (6) communicate transparently about realistic timelines.

## Software Design

### Beginner

**Q: What is the Single Responsibility Principle?**
A: A class should have one reason to change. Each class/module/function should do one thing well. Benefits: easier testing, lower coupling, higher cohesion.

**Q: What is the difference between coupling and cohesion?**
A: Coupling = how much modules depend on each other (want LOW). Cohesion = how related a module's responsibilities are (want HIGH). Good design: highly cohesive modules with low coupling.

### Intermediate

**Q: Explain SOLID principles with examples.**
A: **S**RP: User class handles only user data, not email sending. **O**CP: Payment processor is open for extension (new methods) but closed for modification. **L**SP: Subtypes must be substitutable (Square extending Rectangle breaks this). **I**SP: Small, focused interfaces (Printer, Scanner separate, not one Machine). **D**IP: Depend on abstractions (interface), not concretions (MySQLConnection).

**Q: When would you use composition over inheritance?**
A: Prefer composition when: (1) you need "has-a" not "is-a" relationship, (2) behavior needs to change at runtime, (3) you want to avoid fragile base class problem, (4) multiple inheritance-like behavior is needed. Inheritance: when there's a true hierarchical "is-a" relationship.

### Advanced

**Q: How would you design a system that needs to handle 10x current load?**
A: (1) Profile to find bottlenecks (CPU, I/O, memory, network), (2) add caching (Redis/CDN), (3) horizontal scaling (load balancer + stateless services), (4) database optimization (read replicas, sharding), (5) async processing (queues), (6) rate limiting, (7) measure after each change.

## Code Quality & Process

**Q: What is a code smell? Give examples.**
A: Surface indication of deeper design problems. Examples: Long methods (> 30 lines), God classes (do everything), feature envy (uses another class's data excessively), data clumps (same group of parameters everywhere), dead code.

**Q: How do you balance speed and quality?**
A: (1) Define "good enough" — not everything needs perfect design, (2) use the 80/20 rule — 20% of effort gets 80% of quality, (3) time-box perfectionism, (4) track tech debt explicitly, (5) refactor when touching code, not as separate project.

## References

- [Clean Code — Robert C. Martin](https://www.oreilly.com/library/view/clean-code/9780136083238/)
- [Designing Data-Intensive Applications — Martin Kleppmann](https://dataintensive.net/)
- [The Pragmatic Programmer](https://pragprog.com/titles/tpp20/)
- [SWEBOK](https://www.swebok.org/)
