# Agile & Scrum Deep Dive

## Table of Contents

- [Agile Philosophy](#agile-philosophy)
- [Scrum Framework](#scrum-framework)
- [Scrum Roles](#scrum-roles)
- [Scrum Ceremonies](#scrum-ceremonies)
- [Scrum Artifacts](#scrum-artifacts)
- [User Stories](#user-stories)
- [Story Points & Velocity](#story-points--velocity)
- [Kanban](#kanban)
- [Scrum vs Kanban](#scrum-vs-kanban)
- [Extreme Programming (XP)](#extreme-programming-xp)
- [SAFe — Scaling Agile](#safe--scaling-agile)
- [Interview Questions](#interview-questions)

---

## Agile Philosophy

Agile is not a methodology — it's a **mindset** defined by the Agile Manifesto (2001), authored by 17 software practitioners including Kent Beck, Martin Fowler, and Robert C. Martin.

### The Four Values

```
We value:

  Individuals and interactions  ──over──  Processes and tools
  Working software              ──over──  Comprehensive documentation
  Customer collaboration        ──over──  Contract negotiation
  Responding to change          ──over──  Following a plan

  That is, while the items on the right have value,
  we value the items on the left more.
```

### The Twelve Principles

1. Our highest priority is to satisfy the customer through early and continuous delivery of valuable software.
2. Welcome changing requirements, even late in development.
3. Deliver working software frequently (weeks rather than months).
4. Business people and developers must work together daily.
5. Build projects around motivated individuals. Give them the environment and support they need.
6. The most efficient and effective method of conveying information is face-to-face conversation.
7. Working software is the primary measure of progress.
8. Agile processes promote sustainable development — sponsors, developers, and users should maintain a constant pace indefinitely.
9. Continuous attention to technical excellence and good design enhances agility.
10. Simplicity — maximizing the amount of work not done — is essential.
11. The best architectures, requirements, and designs emerge from self-organizing teams.
12. At regular intervals, the team reflects on how to become more effective and adjusts accordingly.

---

## Scrum Framework

**Scrum** is the most widely used Agile framework. It provides a lightweight structure for managing complex product development through iterative progress.

### Scrum at a Glance

```
Product Backlog
      │
      ▼
┌─────────────────────────────────────────────────────┐
│                  Sprint (1-4 weeks)                  │
│                                                      │
│  Sprint Planning ──▶ Daily Standups ──▶ Sprint Review│
│        │                                      │      │
│        ▼                                      ▼      │
│   Sprint Backlog ◀─────────────── Product Increment   │
│        │                                             │
│        ▼                                             │
│   Development Work ──▶ Sprint Retrospective          │
└─────────────────────────────────────────────────────┘
```

### The Scrum Flow

1. **Product Owner** creates and prioritizes the Product Backlog
2. Team selects items for the Sprint during **Sprint Planning**
3. Team works during the Sprint, meeting daily for **Daily Standups**
4. At Sprint end, team demonstrates work in the **Sprint Review**
5. Team reflects and improves in the **Sprint Retrospective**
6. Repeat

---

## Scrum Roles

### Product Owner (PO)

The voice of the customer and business. Responsible for **maximizing the value** of the product.

| Responsibility | Details |
|---|---|
| Manage Product Backlog | Create, prioritize, and maintain backlog items |
| Define vision | Communicate the product vision to the team |
| Stakeholder management | Gather input from stakeholders and translate to requirements |
| Accept/reject work | Review completed work and accept or request changes |
| ROI focus | Ensure the team delivers maximum business value |

**The PO does NOT:**
- Tell the team *how* to implement features
- Assign tasks to individuals
- Change requirements mid-sprint (protect the sprint goal)

### Scrum Master (SM)

A **servant-leader** who ensures the team follows Scrum practices and removes impediments.

| Responsibility | Details |
|---|---|
| Facilitate ceremonies | Sprint planning, standup, review, retrospective |
| Remove impediments | Clear blockers that slow the team down |
| Coach the team | Guide the team toward self-organization and continuous improvement |
| Shield the team | Protect the team from external interruptions during a sprint |
| Enforce Scrum | Ensure Scrum rules and values are followed |

**The SM is NOT:**
- A project manager who assigns tasks
- A boss or authority figure
- Responsible for the product backlog (that's the PO)

### Development Team

A **cross-functional, self-organizing** team of 3–9 members who build the product.

| Characteristic | Details |
|---|---|
| Cross-functional | Has all skills needed to deliver a product increment |
| Self-organizing | Decides internally how to accomplish work |
| No sub-teams | No titles like "tester" or "developer" — everyone is a "developer" |
| Accountable | Collectively responsible for delivering the sprint goal |

---

## Scrum Ceremonies

### Sprint Planning

**When:** Beginning of each sprint
**Duration:** 2 hours per week of sprint (e.g., 4 hours for a 2-week sprint)
**Attendees:** Entire Scrum team

**Purpose:** Define *what* will be delivered in the sprint and *how* it will be achieved.

```
Sprint Planning Agenda:
├── Part 1: What? (1-2 hours)
│   ├── PO presents prioritized backlog items
│   ├── Team discusses and asks questions
│   └── Team commits to sprint goal and selected items
│
└── Part 2: How? (1-2 hours)
    ├── Team breaks items into tasks
    ├── Estimates effort for each task
    └── Creates the Sprint Backlog
```

**Output:** Sprint Goal + Sprint Backlog

### Daily Standup (Daily Scrum)

**When:** Every day during the sprint, same time and place
**Duration:** 15 minutes (timeboxed)
**Attendees:** Development team (PO and SM optional)

**Three Questions:**

```
1. What did I accomplish yesterday?
2. What will I work on today?
3. What blockers am I facing?
```

**Rules:**
- Stand up (keep it short)
- Not a status report to the SM — it's for the team
- Detailed discussions happen *after* the standup ("parking lot")
- Same time, same place, every day

### Sprint Review

**When:** Last day of the sprint
**Duration:** 1 hour per week of sprint
**Attendees:** Scrum team + stakeholders

**Purpose:** Demonstrate the completed work and gather feedback.

```
Sprint Review Agenda:
├── Demo completed features to stakeholders
├── Product Owner explains what was done vs. not done
├── Stakeholders provide feedback
├── Team discusses what went well and challenges
└── Product Owner updates the backlog based on feedback
```

**Key distinction:** Sprint Review is about the *product*. Sprint Retrospective is about the *process*.

### Sprint Retrospective

**When:** After the Sprint Review, before the next Sprint Planning
**Duration:** 1–1.5 hours for a 2-week sprint
**Attendees:** Scrum team only (no stakeholders)

**Purpose:** Inspect the process and create an improvement plan.

**Common Formats:**

```
Format 1: Start / Stop / Continue
├── What should we START doing?
├── What should we STOP doing?
└── What should we CONTINUE doing?

Format 2: 4 L's
├── What did we LOVE?
├── What did we LEARN?
├── What did we LACK?
└── What do we LONG for?

Format 3: Sailboat
├── Wind (what propels us forward)
├── Anchor (what holds us back)
├── Rocks (risks ahead)
└── Island (our goal)
```

**Output:** 1–3 actionable improvement items for the next sprint

---

## Scrum Artifacts

### Product Backlog

An **ordered list** of everything needed in the product. It is the single source of requirements.

```
Product Backlog (example):
┌────┬──────────────────────────────────┬────────┬──────────┐
│ ID │ Item                             │ Priority│ Estimate │
├────┼──────────────────────────────────┼────────┼──────────┤
│ 1  │ User registration with email     │ High   │ 8 pts    │
│ 2  │ Password reset flow              │ High   │ 5 pts    │
│ 3  │ User profile editing             │ Medium │ 5 pts    │
│ 4  │ Search functionality             │ High   │ 13 pts   │
│ 5  │ Dark mode support                │ Low    │ 3 pts    │
│ 6  │ Export data to CSV               │ Medium │ 3 pts    │
│ 7  │ Two-factor authentication        │ Medium │ 8 pts    │
└────┴──────────────────────────────────┴────────┴──────────┘
```

**Characteristics:**
- Dynamic — constantly evolving
- Ordered by value, risk, and priority
- Estimated by the development team
- Never complete — it's a living document

### Sprint Backlog

The set of Product Backlog items selected for the Sprint **plus** the plan for delivering them.

```
Sprint 5 Backlog:
┌─────────────────────────────────┬──────────┬───────────┐
│ Task                            │ Assignee │ Status    │
├─────────────────────────────────┼──────────┼───────────┤
│ Design search API endpoints     │ Alice    │ Done      │
│ Implement search indexing       │ Bob      │ In Progress│
│ Create search UI component      │ Carol    │ To Do     │
│ Write unit tests for search     │ Dave     │ To Do     │
│ Integration test search flow    │ Alice    │ To Do     │
└─────────────────────────────────┴──────────┴───────────┘
```

### Sprint Board (Task Board)

Visual representation of work in the sprint.

```
┌──────────┬──────────────┬───────────┬──────────┐
│   To Do  │  In Progress │ In Review │   Done   │
├──────────┼──────────────┼───────────┼──────────┤
│ Create   │ Implement    │ Design    │ Set up   │
│ search   │ search       │ search    │ database │
│ UI       │ indexing     │ API       │ schema   │
│          │              │           │          │
│ Write    │              │           │          │
│ tests    │              │           │          │
└──────────┴──────────────┴───────────┴──────────┘
```

### Burndown Chart

Shows remaining work over time during a sprint.

```
Story
Points
  40 ┤●
     │  ╲
  35 ┤    ╲
     │      ╲
  30 ┤        ●
     │          ╲
  25 ┤            ╲
     │              ╲
  20 ┤                ●
     │                  ╲
  15 ┤                    ╲
     │                      ╲
  10 ┤                        ●
     │                          ╲
   5 ┤                            ╲
     │                              ╲
   0 ┤────────────────────────────────●
     Mon  Tue  Wed  Thu  Fri  Mon  Tue  Wed  Thu  Fri

     ── Actual Progress
     Ideal: straight line from start to end
```

**How to read:**
- Above the ideal line → behind schedule
- Below the ideal line → ahead of schedule
- Flat sections → blocked work
- Sudden drops → large tasks completed

### Burnup Chart

Shows work completed over time, useful for tracking scope changes.

```
Story
Points
  40 ┤                          ╭──── Total Scope
     │                     ╭────╯
  30 ┤                ╭────╯
     │           ╭────╯
  20 ┤      ╭────╯
     │ ╭────╯                    ╭──── Completed
  10 ┤─╯                    ╭────╯
     │                 ╭────╯
   0 ┤─────────────────╯
     Sprint1  Sprint2  Sprint3  Sprint4  Sprint5
```

---

## User Stories

User stories are the primary way to capture requirements in Agile. They follow a simple format that focuses on the **who**, **what**, and **why**.

### Format

```
As a [type of user],
I want [an action/feature],
So that [benefit/value].
```

### Examples

```
As a registered user,
I want to reset my password via email,
So that I can regain access to my account if I forget my password.

As an admin,
I want to view a dashboard of active users,
So that I can monitor system usage and plan capacity.

As a mobile user,
I want the app to work offline,
So that I can access my data without an internet connection.
```

### INVEST Criteria

Good user stories should be:

| Letter | Criterion | Meaning |
|---|---|---|
| **I** | Independent | Stories should not depend on each other |
| **N** | Negotiable | Details can be discussed and refined |
| **V** | Valuable | Delivers value to the user or business |
| **E** | Estimable | Team can estimate the effort required |
| **S** | Small | Can be completed within a single sprint |
| **T** | Testable | Clear criteria for when it's "done" |

### Acceptance Criteria

Specific conditions that must be met for a story to be considered complete.

**Format (Given/When/Then):**

```
Story: As a user, I want to log in with my email, so that I can access my account.

Acceptance Criteria:

Given a registered user with valid credentials,
When they enter their email and password and click "Log In",
Then they are redirected to their dashboard.

Given a user with invalid credentials,
When they enter a wrong password,
Then they see an error message "Invalid email or password."

Given a user who has failed login 5 times,
When they attempt a 6th login,
Then the account is locked and they see "Account locked. Try again in 30 minutes."

Given the login form,
When displayed on a mobile device,
Then the form is fully usable and responsive.
```

### Story Mapping

Organizes user stories into a visual map based on user activities and priority.

```
User Activities:   Browse    ──▶  Select    ──▶  Purchase  ──▶  Review
                   Products       Items          Product        Product

Release 1 (MVP):   Search        Add to Cart    Checkout       Rate product
                   Filter        View Cart       Payment       Write review
                   Browse        Remove Item     Confirmation

Release 2:         Wishlist      Quantity Edit   Gift Wrap      Photo review
                   Compare       Save for Later  Coupons        Share review

Release 3:         Recommendations  Bundle Deals  Subscription   Helpful votes
```

---

## Story Points & Velocity

### Story Points

Story points are a **relative measure of effort** that considers:
- Complexity — How technically difficult is it?
- Effort — How much work is required?
- Uncertainty — How much is unknown?

Story points are NOT hours. They represent relative sizing.

### Fibonacci Scale

```
1, 2, 3, 5, 8, 13, 21, 34
```

The gaps between numbers increase as estimates get larger, reflecting increasing uncertainty.

### Planning Poker

A consensus-based estimation technique:

```
1. Product Owner presents a user story
2. Team discusses the story
3. Each member selects a card (Fibonacci scale) secretly
4. All cards are revealed simultaneously
5. If estimates differ widely:
   a. Highest and lowest estimators explain their reasoning
   b. Team discusses
   c. Re-vote until convergence
6. Consensus estimate is recorded
```

**Why it works:**
- Prevents anchoring bias (secret selection)
- Encourages discussion of different perspectives
- Leverages team knowledge
- Creates shared understanding

### Velocity

Velocity measures how many **story points** a team completes per sprint.

```
Sprint 1: 23 points completed
Sprint 2: 28 points completed
Sprint 3: 25 points completed
Sprint 4: 27 points completed
Sprint 5: 26 points completed

Average Velocity = (23 + 28 + 25 + 27 + 26) / 5 = 25.8 points/sprint
```

**Uses of velocity:**
- **Sprint planning:** How much work can we commit to?
- **Release planning:** When will we finish? (Remaining points ÷ Velocity = Sprints needed)
- **Trend analysis:** Is the team improving?

**Rules:**
- Velocity is for the **team**, not individuals
- Don't compare velocity between teams
- Velocity takes 3–5 sprints to stabilize
- Don't use velocity as a performance metric

---

## Kanban

**Kanban** (Japanese for "visual signal") is a flow-based method focused on continuous delivery and limiting work in progress.

### Core Principles

1. **Visualize the workflow** — Use a Kanban board
2. **Limit Work in Progress (WIP)** — Set max items per column
3. **Manage flow** — Monitor and optimize the flow of work
4. **Make policies explicit** — Clear rules for how work moves
5. **Implement feedback loops** — Regular reviews
6. **Improve collaboratively** — Evolve experimentally

### Kanban Board with WIP Limits

```
┌──────────┬──────────────┬───────────┬──────────┬──────────┐
│ Backlog  │  In Progress │  Review   │  Testing │   Done   │
│          │   (WIP: 3)   │  (WIP: 2) │ (WIP: 2) │          │
├──────────┼──────────────┼───────────┼──────────┼──────────┤
│ Task F   │ Task C       │ Task A    │ Task D   │ Task X   │
│ Task G   │ Task E       │ Task B    │          │ Task Y   │
│ Task H   │              │           │          │ Task Z   │
│ Task I   │  ← Cannot add more until │          │          │
│          │     one moves out →       │          │          │
└──────────┴──────────────┴───────────┴──────────┴──────────┘
```

### Cumulative Flow Diagram (CFD)

The key Kanban metric — shows work items in each state over time.

```
Items
  30 ┤                    ╭────── Done
     │               ╭────╯
  25 ┤          ╭────╯
     │     ╭────╯  ╭─────── Testing
  20 ┤╭────╯  ╭────╯
     │   ╭────╯  ╭────── Review
  15 ┤───╯  ╭────╯
     │ ╭────╯ ╭────── In Progress
  10 ┤─╯ ╭────╯
     │───╯ ╭────── Backlog
   5 ┤─────╯
     │
   0 ┤──────────────────────────────
     Day1  Day5  Day10  Day15  Day20

  Bands getting wider = bottleneck forming
  Bands getting narrower = flow improving
```

---

## Scrum vs Kanban

| Aspect | Scrum | Kanban |
|---|---|---|
| **Cadence** | Fixed-length sprints | Continuous flow |
| **Roles** | PO, SM, Dev Team | No prescribed roles |
| **Planning** | Sprint planning meetings | Continuous — pull when capacity exists |
| **WIP Limits** | Limited by sprint commitment | Explicit WIP limits per column |
| **Changes** | No changes during sprint | Can change priorities anytime |
| **Metrics** | Velocity | Lead time, cycle time, throughput |
| **Board** | Reset each sprint | Persistent board |
| **Best for** | Product development | Operations, support, maintenance |
| **Delivery** | End of sprint | Continuous |
| **Ceremonies** | Planning, standup, review, retro | Optional — team decides |

### When to Choose Scrum vs Kanban

- **Scrum:** Building a new product, clear sprint goals, team needs structure
- **Kanban:** Maintenance work, support tickets, operations, or when work items arrive unpredictably
- **Scrumban:** Hybrid — Scrum structure with Kanban's flow and WIP limits

---

## Extreme Programming (XP)

**XP** is an Agile methodology that emphasizes technical excellence and frequent releases.

### XP Practices

```
┌─────────────────────────────────────────────────────┐
│                    XP Practices                      │
├─────────────────┬───────────────────────────────────┤
│  Planning       │  Development                     │
│  ├─ User stories│  ├─ Pair programming              │
│  ├─ Spike       │  ├─ Test-driven development (TDD) │
│  ├─ Release plan│  ├─ Refactoring                   │
│  └─ Iteration   │  ├─ Simple design                 │
│                 │  ├─ Collective code ownership      │
├─────────────────┤  ├─ Continuous integration         │
│  Values         │  └─ Coding standards              │
│  ├─ Communication│                                  │
│  ├─ Simplicity  ├───────────────────────────────────┤
│  ├─ Feedback    │  Team                             │
│  ├─ Courage     │  ├─ Sit together                  │
│  └─ Respect     │  ├─ Whole team                    │
│                 │  ├─ Sustainable pace               │
│                 │  └─ Real customer involvement      │
└─────────────────┴───────────────────────────────────┘
```

### Key XP Practices Explained

**Pair Programming:** Two developers work at one computer. One writes code (driver), the other reviews and thinks strategically (navigator). Roles switch frequently.

```
Benefits:
├── Fewer bugs (continuous code review)
├── Knowledge sharing (no single point of failure)
├── Better design decisions (two perspectives)
└── Faster onboarding (junior paired with senior)
```

**Test-Driven Development (TDD):**
```
1. Write a failing test (Red)
2. Write minimal code to pass (Green)
3. Refactor to improve code quality (Refactor)
4. Repeat
```

**Continuous Integration (CI):**
```
Developer commits code
      │
      ▼
Automated build triggered
      │
      ▼
All tests run
      │
      ├──▶ Pass → Deploy to staging
      │
      └──▶ Fail → Notify team, fix immediately
```

---

## SAFe — Scaling Agile

When organizations need to coordinate multiple Agile teams, they use scaling frameworks.

### SAFe (Scaled Agile Framework)

```
┌─────────────────────────────────────────────┐
│              Portfolio Level                 │
│   Strategic themes, Lean Portfolio Mgmt      │
├─────────────────────────────────────────────┤
│              Large Solution                  │
│   Solution Train, multiple ARTs              │
├─────────────────────────────────────────────┤
│              Program Level (ART)             │
│   PI Planning, Features, Dependencies        │
├──────┬──────┬──────┬──────┬─────────────────┤
│Team 1│Team 2│Team 3│Team 4│ Agile Teams     │
│Scrum │Scrum │Kanban│Scrum │ (5-9 members)   │
└──────┴──────┴──────┴──────┴─────────────────┘
```

### Other Scaling Frameworks

| Framework | Focus | Key Concept |
|---|---|---|
| **SAFe** | Enterprise agility | Agile Release Trains (ARTs) |
| **LeSS** | Simplifying Scrum at scale | Minimal additional rules |
| **Nexus** | 3-9 Scrum teams | Integration team |
| **Spotify Model** | Culture and autonomy | Squads, Tribes, Chapters, Guilds |

---

## Interview Questions

### Beginner

**Q1: What is the difference between a Product Owner and a Scrum Master?**

The Product Owner manages the Product Backlog, defines priorities, and represents the customer's interests. The Scrum Master facilitates the Scrum process, removes impediments, and coaches the team. The PO focuses on *what* to build; the SM focuses on *how* the team works.

**Q2: What are the three artifacts in Scrum?**

Product Backlog (ordered list of all work), Sprint Backlog (items selected for the sprint plus the plan), and Product Increment (the sum of all completed backlog items — potentially shippable).

**Q3: How long should a sprint be?**

1–4 weeks, with 2 weeks being most common. Shorter sprints provide more frequent feedback and reduce risk. Longer sprints allow more time for complex work but delay feedback.

### Intermediate

**Q4: What happens if the team cannot complete all sprint backlog items?**

Incomplete items return to the Product Backlog (not the next sprint automatically). The PO reprioritizes them. During the Retrospective, the team analyzes why items weren't completed and adjusts their planning process. The velocity data from this sprint helps calibrate future commitments.

**Q5: Explain the difference between velocity and throughput.**

Velocity measures story points completed per sprint — a measure of effort/complexity handled. Throughput measures the count of items completed per unit time — regardless of size. A team might complete 3 items (throughput) totaling 21 story points (velocity) in a sprint. Both are useful: velocity for planning, throughput for flow analysis.

**Q6: Can you use Scrum and Kanban together?**

Yes — this is called **Scrumban**. You keep Scrum's roles and ceremonies but adopt Kanban's WIP limits, pull-based flow, and continuous delivery. For example: maintain sprint planning and retrospectives, but use a Kanban board with WIP limits instead of a sprint backlog, and deploy completed items continuously rather than at sprint end.

### Advanced

**Q7: Your team's velocity has been dropping for 3 sprints. How do you investigate?**

Investigate systematically: (1) Check for scope changes — did the team take on larger stories? (2) Review impediment logs — are blockers being resolved? (3) Examine team composition — did anyone leave or join? (4) Look at quality metrics — rising defect rates slow velocity. (5) Check for external interruptions — production incidents, meetings, etc. (6) Discuss in the retrospective — the team may have insights. (7) Consider if the team is gold-plating or over-engineering. The solution depends on the root cause, not the symptom.

**Q8: How would you introduce Scrum to a team that has only done Waterfall?**

Phase the transition: (1) Start with daily standups — easiest ceremony to adopt. (2) Introduce a backlog and prioritization. (3) Run 1-2 week iterations with planning and review. (4) Add retrospectives once the team is comfortable with iteration. (5) Coach the team on self-organization gradually — don't remove all structure at once. (6) Address mindset changes explicitly: "We deliver working software every 2 weeks" is a significant shift from "We deliver after 6 months." Expect resistance and adapt.

**Q9: A stakeholder wants to add a high-priority item mid-sprint. What should happen?**

The Scrum Master should facilitate a conversation: (1) Is this truly an emergency (production outage, legal requirement)? If yes, the team can swap it in — but something of equal size must come out to protect the sprint goal. (2) If not an emergency, the PO adds it to the Product Backlog and prioritizes it for the next sprint. (3) The team should not be pressured into "just squeezing it in" — this undermines sprint commitment and sustainable pace. The SM educates the stakeholder on why sprint boundaries matter.
