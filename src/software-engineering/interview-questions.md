# SE Interview Questions — Comprehensive Guide

## Table of Contents

- [Beginner Level](#beginner-level)
- [Intermediate Level](#intermediate-level)
- [Advanced Level](#advanced-level)
- [Scenario-Based Questions](#scenario-based-questions)
- [System Design Tie-Ins](#system-design-tie-ins)

---

## Beginner Level

### SDLC & Process

**Q1: What is the Software Development Life Cycle?**
The SDLC is a structured framework for building software, encompassing phases: requirements analysis, design, implementation, testing, deployment, and maintenance. Different models (Waterfall, Agile, Spiral) organize these phases differently.

**Q2: What is the difference between Waterfall and Agile?**
Waterfall is linear and sequential — each phase completes before the next begins. Agile is iterative — work is done in short cycles (sprints) with continuous feedback. Waterfall requires fixed upfront requirements; Agile embraces change.

**Q3: What are the four Agile Manifesto values?**
(1) Individuals and interactions over processes and tools. (2) Working software over comprehensive documentation. (3) Customer collaboration over contract negotiation. (4) Responding to change over following a plan.

**Q4: What are the three Scrum roles?**
Product Owner (manages backlog, represents customer), Scrum Master (facilitates process, removes impediments), and Development Team (cross-functional, self-organizing team that builds the product).

**Q5: What is a sprint?**
A sprint is a fixed time period (1-4 weeks, typically 2) during which the Scrum team completes a set of backlog items. Each sprint produces a potentially shippable product increment.

**Q6: What are the four Scrum ceremonies?**
Sprint Planning (plan the sprint), Daily Standup (15-min daily sync), Sprint Review (demo to stakeholders), and Sprint Retrospective (team improvement discussion).

### Requirements

**Q7: What is the difference between functional and non-functional requirements?**
Functional requirements describe what the system does (features, behaviors). Non-functional requirements describe how well it does it (performance, security, usability).

**Q8: What is a user story?**
A user story captures a requirement from the user's perspective: "As a [role], I want [feature], so that [benefit]." It's a placeholder for a conversation, not a detailed specification.

**Q9: What is MoSCoW prioritization?**
MoSCoW categorizes requirements as Must Have (critical), Should Have (important), Could Have (nice-to-have), and Won't Have (deferred). It helps teams deliver the most important features first.

### Design

**Q10: What does SOLID stand for?**
Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion. These five principles make object-oriented designs more maintainable.

**Q11: What is the Single Responsibility Principle?**
A class should have one, and only one, reason to change. Each class should have a single, well-defined responsibility.

**Q12: What is DRY?**
"Don't Repeat Yourself" — every piece of knowledge should have a single, authoritative representation. Avoid code duplication, but don't abstract prematurely.

**Q13: What is the difference between coupling and cohesion?**
Coupling measures dependency between modules (low is good). Cohesion measures relatedness within a module (high is good). Good design has high cohesion and low coupling.

### Code Quality

**Q14: What is a code smell?**
A surface-level indicator of a deeper problem. Examples: long methods, duplicated code, large classes, long parameter lists. They don't break functionality but make code harder to maintain.

**Q15: What is technical debt?**
The implied cost of future rework from choosing a quick solution now instead of a better approach. Like financial debt, it accumulates interest over time.

**Q16: What is refactoring?**
Changing the internal structure of code without changing its external behavior. The goal is to improve readability, reduce complexity, and make code easier to maintain.

### Testing & Metrics

**Q17: What is code coverage?**
The percentage of code executed during testing. Types include line coverage, branch coverage, and function coverage. High coverage is necessary but not sufficient for quality.

**Q18: What is cyclomatic complexity?**
A measure of the number of independent paths through a code segment. Higher complexity means more paths to test and higher risk of bugs. Aim for CC < 10 per function.

**Q19: What are the four DORA metrics?**
Deployment Frequency, Lead Time for Changes, Change Failure Rate, and Mean Time to Recovery. These predict software delivery performance.

---

## Intermediate Level

### SDLC & Process

**Q20: When would you choose the Spiral model?**
For large, expensive, high-risk projects with unclear requirements. The Spiral model integrates risk analysis into every iteration, making it ideal for R&D projects or new technology implementations.

**Q21: What is the V-Model and when is it used?**
The V-Model maps each development phase to a testing phase, forming a V shape. Used in safety-critical systems (medical devices, aerospace) where formal verification is required.

**Q22: Explain the difference between Iterative and Incremental development.**
Iterative refines the entire system through repeated cycles. Incremental delivers the system in functional pieces. Many modern approaches combine both (delivering increments iteratively).

### Agile & Scrum

**Q23: What is velocity and how is it used?**
Velocity is the number of story points a team completes per sprint. Used for sprint planning (how much to commit) and release forecasting (when will we finish). It's a planning tool, not a performance metric.

**Q24: What happens if the team can't complete all sprint items?**
Incomplete items return to the Product Backlog. The PO reprioritizes them. The team analyzes why in the retrospective and adjusts their planning process.

**Q25: What is the difference between Scrum and Kanban?**
Scrum uses fixed-length sprints, prescribed roles, and sprint commitments. Kanban uses continuous flow, no prescribed roles, and WIP limits. Scrum is for product development; Kanban is for operations and continuous delivery.

**Q26: How do you handle mid-sprint scope changes?**
The Scrum Master facilitates a conversation. If it's a true emergency, the team can swap items of equal size. Otherwise, the PO adds it to the backlog for the next sprint. Sprint boundaries protect the team's commitment.

### Requirements

**Q27: How do you handle conflicting requirements from different stakeholders?**
Document all perspectives, facilitate discussion to understand underlying needs, use data and prototypes to resolve disagreements, escalate to the PO or sponsor if needed, and prioritize based on business value.

**Q28: What is requirements traceability?**
Tracking each requirement from its origin through design, implementation, and testing. It enables impact analysis, ensures coverage, and supports compliance audits.

**Q29: What are acceptance criteria?**
Conditions that must be met for a user story to be considered complete. Often written in Given/When/Then format. They provide testable conditions and reduce misunderstandings.

### Design

**Q30: Explain the Open/Closed Principle with an example.**
Software should be open for extension but closed for modification. Example: Instead of adding if-else for each payment type, define a PaymentMethod interface. New payment methods are added by creating new classes, not modifying existing code.

**Q31: What is the Liskov Substitution Principle?**
Subtypes must be substitutable for their base types without altering program correctness. If Square extends Rectangle but changes set_width() behavior, it violates LSP.

**Q32: When should you use composition over inheritance?**
Use composition when you need flexible behavior combinations, runtime behavior swapping, or to avoid deep hierarchies. Use inheritance for genuine "is-a" relationships with shallow hierarchies (1-2 levels).

**Q33: What is Dependency Inversion?**
High-level modules should not depend on low-level modules. Both should depend on abstractions. Implemented through Dependency Injection — injecting interfaces rather than creating concrete instances.

### Code Quality

**Q34: How do you manage technical debt strategically?**
(1) Track it in a debt register. (2) Allocate capacity (e.g., 20% per sprint). (3) Prioritize by impact and cost. (4) Apply the boy scout rule. (5) Set quality gates in CI. (6) Regular architecture reviews.

**Q35: What is the "boy scout rule"?**
"Leave the code better than you found it." Fix small issues as you encounter them during regular work. This prevents debt from accumulating without requiring dedicated refactoring sprints.

**Q36: How do you balance clean code with delivery deadlines?**
Apply the 80/20 rule: 80% of clean code benefits come from 20% of effort (good naming, small functions, basic testing). Track deliberate tech debt. For critical paths, invest in quality; for throwaways, accept some debt.

### Metrics

**Q37: What is the difference between lead time and cycle time?**
Lead time: customer request to delivery (includes queue time). Cycle time: work started to work completed (active work only). Long lead time with short cycle time indicates a queue problem.

**Q38: What is a good code coverage target?**
80% for most applications. 90%+ for critical systems. But 100% coverage ≠ bug-free — coverage measures breadth, not depth. Branch coverage is more meaningful than line coverage.

**Q39: How do you measure code quality objectively?**
Combine metrics: cyclomatic complexity, code coverage, duplication percentage, defect density, code review turnaround, and change failure rate. No single metric tells the full story.

### Team Dynamics

**Q40: What makes a good code review?**
Small PRs (< 400 lines), clear descriptions, focus on design first then details, specific and constructive feedback, distinguishing blockers from nits, and timely turnaround (< 4 hours).

**Q41: What is the bus factor?**
The number of team members who would need to leave before the project is critically impacted. A bus factor of 1 means a single point of failure. Improve through pair programming, documentation, and rotation.

**Q42: How do you build psychological safety?**
Leader models vulnerability (admits mistakes), respond to errors with curiosity not blame, actively invite quiet voices, thank people for raising concerns, and celebrate learning from failure.

---

## Advanced Level

### SDLC & Process

**Q43: You're leading a 200-person medical device project with regulatory requirements. 80% of requirements are clear, 20% will evolve. What SDLC approach?**
Hybrid: V-Model for safety-critical components requiring formal verification, combined with Agile sprints for the evolving 20%. Use integration checkpoints to synchronize. The V-Model ensures compliance; Agile allows flexibility.

**Q44: How do modern DevOps practices map to traditional SDLC phases?**
CI/CD automates implementation → testing → deployment. Infrastructure as Code blurs design and implementation. Monitoring extends maintenance into continuous observability. Traditional "phases" become concurrent activities rather than sequential gates.

### Agile & Scrum

**Q45: Your team's velocity has been dropping for 3 sprints. How do you investigate?**
Check for: scope changes (larger stories?), impediment logs (unresolved blockers?), team composition (someone left?), quality metrics (rising defects?), external interruptions (production incidents?), and discuss in retrospective. The solution depends on the root cause.

**Q46: How would you introduce Scrum to a Waterfall team?**
Phase the transition: start with daily standups (easiest), introduce backlog and prioritization, run 1-2 week iterations, add retrospectives, coach on self-organization gradually. Expect resistance and adapt. Don't change everything at once.

### Requirements

**Q47: Users can't articulate what they need. How do you gather requirements?**
Use observation (watch users work), prototyping (low-fidelity mockups), contextual inquiry (ask users to explain while working), analyze existing data (support tickets, analytics), create journey maps, and build what's possible to see reactions.

**Q48: How do you manage 500+ requirements?**
Use a requirements management tool, organize hierarchically (epics → features → stories), assign unique IDs, maintain a traceability matrix, implement formal change control, use baselines at milestones, and regularly prune stale requirements.

### Design

**Q49: You're designing a payment processing system. Apply SOLID.**
SRP: Separate PaymentValidator, PaymentProcessor, PaymentLogger. OCP: Define PaymentMethod interface, add CreditCard/PayPal/Crypto without modifying processor. LSP: All payment methods interchangeable. ISP: Separate Refundable, Recurring, Tokenizable interfaces. DIP: Processor depends on PaymentGateway abstraction, not StripeGateway.

**Q50: When is inheritance actually the right choice?**
When you have a genuine "is-a" relationship, the hierarchy is shallow (1-2 levels), and the base class was designed for extension. Examples: Exception hierarchies, UI framework base classes, template method patterns. Test: Does LSP hold?

**Q51: How do you refactor a 5,000-line God class?**
(1) Identify responsibilities. (2) Group related methods/fields. (3) Extract one class at a time, starting with the most independent. (4) Use delegation. (5) Run tests after each extraction. (6) Apply Extract Class refactoring. (7) Use DI to wire new classes. (8) Repeat until each class has a single responsibility.

### Code Quality

**Q52: You inherit a 500K LOC codebase with no tests and frequent incidents. How do you improve it?**
Phase 1: Stop bleeding — monitoring, fix critical bugs, feature flags. Phase 2: Safety net — characterization tests, integration tests, CI with quality gates. Phase 3: Systematic improvement — refactor hotspots first, strangler fig for architecture. Phase 4: Culture change — code reviews, documentation, tech debt register.

**Q53: How do you measure the ROI of tech debt reduction?**
Measure current cost (developer time working around debt, incident frequency, manual processes). Track before/after (velocity, defect rate, lead time). Calculate payback period. Present in business terms: "This refactoring saves 20 engineering hours/month."

### Metrics

**Q54: How do you set up a metrics dashboard?**
Layer 1 (always visible): DORA metrics. Layer 2 (weekly): velocity trend, cycle time, review turnaround, defect escape rate. Layer 3 (monthly): tech debt ratio, bus factor, coverage trend, satisfaction. Automate data collection. Review in retrospectives as conversation starters.

**Q55: A team's velocity has been steadily increasing for 6 sprints. Is this good?**
Not necessarily. Investigate: Are estimates consistent? Is quality maintained? Has team composition changed? Are stories smaller? Is tech debt accumulating? Best indicator: cycle time and defect rate stable or improving alongside velocity.

### Team Dynamics

**Q56: You're joining a team with low psychological safety. How do you improve it?**
Start with yourself — admit your own mistakes. Ask questions instead of making statements. Thank people for raising concerns. Focus retrospectives on processes, not people. Celebrate learning from failure. Have 1:1s with quiet members. Be patient — takes months to build, seconds to destroy.

**Q57: How do you manage knowledge silos?**
Map who knows what (skills matrix). Start with highest-risk silo. Pair knowledge holder with others. Rotate responsibilities (on-call, features, reviews). Create documentation culture. Establish team norms (no single-person projects). Track bus factor improvement.

---

## Scenario-Based Questions

**Q58: A production database is running out of disk space. What do you do?**
Immediate: Check what's consuming space (logs, temp tables, bloated indexes). Clear non-essential data if safe. Monitor. Short-term: Identify the cause (missing cleanup job? runaway query?). Implement a fix. Long-term: Set up monitoring alerts for disk usage, implement data retention policies, plan capacity upgrades.

**Q59: A critical security vulnerability is found in a dependency. How do you respond?**
Immediate: Assess the vulnerability's impact (is it exploitable in our context?). Check for available patches. Short-term: Apply the patch or upgrade the dependency. If no patch, implement a workaround (WAF rule, input validation). Long-term: Set up automated dependency scanning (Dependabot, Snyk), establish a vulnerability response process.

**Q60: Two team members have a persistent technical disagreement that's affecting the team. How do you handle it?**
(1) Talk to each person privately to understand their perspective. (2) Facilitate a structured discussion focusing on data, not opinions. (3) If no resolution, propose an experiment or prototype. (4) If still stuck, use a decision framework (ADR, team vote). (5) Once decided, enforce "disagree and commit." (6) Address any lingering tension in 1:1s.

**Q61: Your team is consistently missing sprint commitments. What do you investigate?**
(1) Are estimates accurate? Compare estimated vs. actual. (2) Is scope changing mid-sprint? (3) Are there unresolved impediments? (4) Is the team multitasking? (5) Are there external dependencies blocking progress? (6) Is the sprint goal clear? (7) Is the team's capacity calculation correct? (8) Discuss in retrospective — the team knows best.

**Q62: A stakeholder demands a feature that the team thinks is technically inadvisable. How do you handle it?**
(1) Understand the stakeholder's underlying need — what problem are they trying to solve? (2) Present the technical concerns with data — performance impact, maintenance cost, risk. (3) Propose alternative solutions that address the same need. (4) If they insist, document the risks and get explicit sign-off. (5) Implement the best version possible given the constraints. (6) Monitor and raise issues early.

---

## System Design Tie-Ins

**Q63: How do SOLID principles apply to microservices?**
SRP: Each microservice has one bounded context. OCP: New services can be added without modifying existing ones. LSP: Service implementations can be swapped behind the API. ISP: APIs expose only what consumers need. DIP: Services depend on API contracts, not implementations.

**Q64: How do DORA metrics relate to system architecture?**
Microservices enable higher deployment frequency (independent deployments). Good observability reduces MTTR (faster diagnosis). Feature flags reduce change failure rate (safe rollouts). CI/CD automation reduces lead time (faster pipelines). Architecture directly impacts all four metrics.

**Q65: How does technical debt affect system design over time?**
Short-term: Quick fixes that work. Medium-term: Workarounds accumulate, coupling increases. Long-term: System becomes rigid, fragile, and immobile (Robert C. Martin's "design death"). The cost of change increases exponentially. Regular refactoring and architectural governance prevent this decay.
