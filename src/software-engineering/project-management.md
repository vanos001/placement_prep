# Project Management

## Table of Contents

- [Estimation Techniques](#estimation-techniques)
- [Planning Poker](#planning-poker)
- [T-Shirt Sizing](#t-shirt-sizing)
- [Risk Management](#risk-management)
- [Project Planning](#project-planning)
- [Capacity Planning](#capacity-planning)
- [Interview Questions](#interview-questions)

---

## Estimation Techniques

Estimation is one of the hardest problems in software engineering. The goal is not to be perfectly accurate — it's to be **good enough to make informed decisions**.

### Why Estimation is Hard

```
Sources of Estimation Error:
├── Optimism bias — "It'll be easy"
├── Unknown unknowns — Things we don't know we don't know
├── Scope creep — Requirements grow after estimation
├── Integration complexity — Components are harder together
├── Human factors — Meetings, interruptions, context switching
├── Technical debt — Existing code slows development
├── Dependencies — Waiting on other teams/systems
└── Estimation inexperience — Haven't done similar work before
```

### Story Points vs Hours

| Aspect | Story Points | Hours |
|---|---|---|
| **Measures** | Relative effort/complexity | Absolute time |
| **Includes** | Complexity + effort + uncertainty | Just time |
| **Stability** | Consistent over time | Varies by person |
| **Team-level** | Yes — team estimates together | No — individual estimates |
| **Gaming risk** | Low | High (pressure to "fit" hours) |
| **Velocity** | Points/sprint | Hours/task |
| **Best for** | Agile teams, long-term planning | Waterfall, fixed-price contracts |

### Fibonacci Scale

```
1  — Trivial, a few hours
2  — Small, less than a day
3  — Medium, about a day
5  — Large, 2-3 days
8  — Very large, about a week
13 — Huge, 1-2 weeks
21 — Epic, needs to be broken down
34 — Way too big — MUST be broken down
```

The gaps increase because estimation precision decreases with size. The difference between 1 and 2 is clear; the difference between 20 and 21 is meaningless.

### Relative Estimation

Instead of asking "How long will this take?", ask "Is this bigger or smaller than that?"

```
Example:
1. Team picks a reference story (e.g., "User login" = 3 points)
2. New story: "User registration"
   - Team: "Similar complexity to login, maybe slightly more"
   - Estimate: 3 points
3. New story: "Password reset"
   - Team: "Simpler than login — just send email and update DB"
   - Estimate: 2 points
4. New story: "Product search with filters"
   - Team: "Much more complex — full-text search, filtering, pagination"
   - Estimate: 8 points
```

---

## Planning Poker

Planning Poker is a consensus-based estimation technique that leverages collective intelligence.

### How It Works

```
Step 1: Product Owner presents the user story
        "As a user, I want to filter products by category, price, and rating"

Step 2: Team discusses the story
        - "Do we have a category taxonomy already?"
        - "What about multiple filters combined?"
        - "Does this include sorting too?"
        - PO clarifies: "Just filtering, sorting is a separate story"

Step 3: Each team member selects a card privately
        (Fibonacci: 1, 2, 3, 5, 8, 13, 21, 34)

Step 4: All cards revealed simultaneously
        Alice: 5    Bob: 8    Carol: 5    Dave: 13

Step 5: Discuss outliers
        Dave (13): "I'm thinking about the search indexing work — we'd need
                    to add category and price to the search index"
        Alice (5): "Good point, but we already have Elasticsearch set up,
                    we just need to add those fields"
        Team discusses...

Step 6: Re-vote
        Alice: 8    Bob: 8    Carol: 8    Dave: 8

Step 7: Consensus reached — 8 story points
```

### Why Planning Poker Works

```
Benefits:
├── Prevents anchoring bias (secret selection)
├── Surfaces hidden assumptions (Dave's concern about indexing)
├── Encourages discussion of scope and approach
├── Leverages team knowledge (junior + senior perspectives)
├── Creates shared understanding of the work
├── Reveals when estimates differ wildly (sign of ambiguity)
└── Builds team ownership of estimates
```

### Common Pitfalls

```
❌ Averaging votes mechanically
   "Alice said 3, Bob said 13, so let's say 8"
   → Discuss WHY they differ instead

❌ Senior developer's estimate wins
   → The goal is consensus, not authority

❌ Spending too long on one story
   → Timebox to 5 minutes per story. If no consensus, spike it.

❌ Converting points to hours
   → "8 points = 16 hours" destroys the purpose of relative estimation

❌ Comparing velocity between teams
   → Team A's 30 points ≠ Team B's 30 points
```

---

## T-Shirt Sizing

T-Shirt Sizing is a fast, relative estimation technique ideal for early-stage planning when detailed estimates aren't needed.

### Scale

```
Size     Effort           Duration        Example
─────    ─────────        ────────        ─────────────────────
XS       Trivial          < 1 day         Fix a typo
S        Small            1-3 days        Add a validation check
M        Medium           3-5 days        Build a CRUD endpoint
L        Large            1-2 weeks       Implement search feature
XL       Extra Large      2-4 weeks       Build payment integration
XXL      Epic             1+ months       MUST be broken down
```

### When to Use T-Shirt Sizing

```
Use T-Shirt Sizing when:
├── Early planning / roadmap creation
├── Large backlog that needs rough prioritization
├── Cross-team estimation (simpler than story points)
├── Stakeholder discussions (non-technical audiences)
└── Quick estimation without detailed analysis

Use Planning Poker when:
├── Sprint planning (need precise estimates)
├── Team needs to commit to specific work
└── Stories are well-defined and understood
```

### T-Shirt to Story Points Mapping

```
If you need to convert for velocity calculations:

XS = 1 point
S  = 2 points
M  = 3-5 points
L  = 8 points
XL = 13-21 points

(These are rough — calibrate to your team's velocity)
```

### Wideband Delphi (Alternative)

A structured estimation method where experts independently estimate, then discuss and re-estimate until convergence. Similar to Planning Poker but without cards — used for non-agile contexts.

---

## Risk Management

Risk management identifies, assesses, and mitigates threats to project success.

### Risk vs Issue

```
Risk:   Something that MIGHT happen (uncertain, future)
Issue:  Something that HAS happened (certain, current)
```

### Risk Identification

```
Categories of Risk:
├── Technical
│   ├── New/unproven technology
│   ├── Integration complexity
│   ├── Performance uncertainty
│   └── Security vulnerabilities
│
├── Schedule
│   ├── Unrealistic deadlines
│   ├── Dependency delays
│   ├── Resource unavailability
│   └── Scope creep
│
├── Organizational
│   ├── Changing priorities
│   ├── Stakeholder conflicts
│   ├── Team turnover
│   └── Budget cuts
│
├── External
│   ├── Vendor failures
│   ├── Regulatory changes
│   ├── Market shifts
│   └── Third-party API changes
│
└── People
    ├── Skill gaps
    ├── Bus factor (key person dependency)
    ├── Communication issues
    └── Burnout
```

### Risk Assessment Matrix

```
           Impact
           Low      Medium    High     Critical
         ┌────────┬─────────┬────────┬──────────┐
High      │ Medium │  High   │ Critical│ Critical │
          ├────────┼─────────┼────────┼──────────┤
Likelihood│ Medium │ Medium  │  High  │ Critical │
Medium    ├────────┼─────────┼────────┼──────────┤
          │  Low   │ Medium  │ Medium │   High   │
Low       ├────────┼─────────┼────────┼──────────┤
          │  Low   │   Low   │ Medium │  Medium  │
Very Low  └────────┴─────────┴────────┴──────────┘
```

### Risk Response Strategies

```
1. AVOID — Change the plan to eliminate the risk
   Example: "We're uncertain about this third-party API"
   Action:  "Build our own implementation instead"

2. MITIGATE — Reduce the probability or impact
   Example: "Database might not handle 10x traffic"
   Action:  "Add caching layer and load testing before launch"

3. TRANSFER — Shift the risk to a third party
   Example: "Payment processing has fraud risk"
   Action:  "Use Stripe's fraud detection instead of building our own"

4. ACCEPT — Acknowledge the risk and prepare a contingency
   Example: "Key developer might leave"
   Action:  "Cross-train team members, document critical knowledge"

5. ESCALATE — Risk is beyond the project's control
   Example: "Regulatory change could require major redesign"
   Action:  "Escalate to legal/compliance for guidance"
```

### Risk Register

```
┌────┬───────────────────────┬────────┬────────┬──────┬──────────────────────┬────────┐
│ ID │ Risk                  │ Like.  │ Impact │ Score│ Mitigation           │ Owner  │
├────┼───────────────────────┼────────┼────────┼──────┼──────────────────────┼────────┤
│ R1 │ Payment gateway       │ Medium │ Crit.  │ High │ Build fallback       │ Alice  │
│    │ downtime              │        │        │      │ payment processor    │        │
├────┼───────────────────────┼────────┼────────┼──────┼──────────────────────┼────────┤
│ R2 │ Key developer leaves  │ Low    │ High   │ Med  │ Document critical    │ Bob    │
│    │                       │        │        │      │ knowledge, cross-train│        │
├────┼───────────────────────┼────────┼────────┼──────┼──────────────────────┼────────┤
│ R3 │ Scope creep from      │ High   │ Med    │ High │ Strict change control│ Carol  │
│    │ stakeholders          │        │        │      │ process, MoSCoW      │        │
├────┼───────────────────────┼────────┼────────┼──────┼──────────────────────┼────────┤
│ R4 │ Performance issues    │ Medium │ High   │ High │ Load testing every   │ Dave   │
│    │ at scale              │        │        │      │ sprint, auto-scaling │        │
└────┴───────────────────────┴────────┴────────┴──────┴──────────────────────┴────────┘
```

---

## Project Planning

### Release Planning

```
Release Planning Process:
├── 1. Define the release goal
│      "Launch MVP with core shopping features"
│
├── 2. Identify features for the release
│      Product Owner prioritizes backlog
│
├── 3. Estimate effort
│      Team estimates stories in story points
│
├── 4. Calculate velocity
│      Average from last 3-5 sprints: 25 points/sprint
│
├── 5. Plan sprints
│      Total points needed: 125
│      Sprints needed: 125 ÷ 25 = 5 sprints
│      At 2 weeks/sprint: 10 weeks
│
├── 6. Identify dependencies
│      - Payment gateway integration depends on vendor API access
│      - Search feature depends on data migration
│
└── 7. Set the release date
       Start: Jan 15 → Release: March 25 (with 2-week buffer)
```

### Milestone Planning

```
Timeline:
Week 1-2:   Sprint 1 — User auth, product catalog
Week 3-4:   Sprint 2 — Shopping cart, search
Week 5-6:   Sprint 3 — Checkout, payment
Week 7-8:   Sprint 4 — Order management, email
Week 9-10:  Sprint 5 — Polish, bug fixes, performance
Week 11-12: Buffer — Integration testing, UAT, deployment

Milestones:
├── M1 (Week 2):  Auth and catalog demo
├── M2 (Week 4):  Cart and search demo
├── M3 (Week 6):  End-to-end purchase flow
├── M4 (Week 8):  Feature complete
├── M5 (Week 10): Release candidate
└── M6 (Week 12): Production launch
```

### Critical Path Method

The **critical path** is the longest sequence of dependent tasks that determines the minimum project duration.

```
Task Dependencies:
A: Design API (3 days) ──────┐
B: Set up database (2 days) ──┼──▶ D: Build backend (5 days) ──┐
C: Design UI (4 days) ────────┘                                ├──▶ F: Integration (3 days)
E: Build frontend (4 days) ────────────────────────────────────┘

Paths:
A → D → F: 3 + 5 + 3 = 11 days
B → D → F: 2 + 5 + 3 = 10 days
C → E → F: 4 + 4 + 3 = 11 days

Critical path: A → D → F (or C → E → F) = 11 days
Any delay on the critical path delays the entire project.
```

### Gantt Charts

```
Task                    Week 1  Week 2  Week 3  Week 4  Week 5
─────────────────────── ──────  ──────  ──────  ──────  ──────
Requirements            ████
Architecture Design     ░░████
Database Setup          ░░░░████
API Development         ░░░░░░░░████████
Frontend Development    ░░░░░░░░████████████
Integration Testing     ░░░░░░░░░░░░░░░░████
Performance Testing     ░░░░░░░░░░░░░░░░░░████
Deployment              ░░░░░░░░░░░░░░░░░░░░████

████ = Active work
░░░░ = Dependency/wait
```

---

## Capacity Planning

Capacity planning determines **how much work** a team can take on in a given time period.

### Team Capacity Calculation

```
Step 1: Calculate available hours
  Team size: 5 developers
  Sprint length: 2 weeks = 10 working days
  Hours per day: 8
  Total hours: 5 × 10 × 8 = 400 hours

Step 2: Subtract overhead
  Meetings (standup, planning, retro): -2 hours/person/sprint = -10 hours
  Code reviews: -3 hours/person/sprint = -15 hours
  Support/on-call rotation: -4 hours/person/sprint = -20 hours
  Time off (PTO, holidays): -16 hours (2 people, 1 day each)
  ─────────────────────────────────────
  Available hours: 400 - 10 - 15 - 20 - 16 = 339 hours

Step 3: Apply focus factor
  Typical focus factor: 70-80% (accounts for interruptions, context switching)
  Effective hours: 339 × 0.75 = 254 hours

Step 4: Convert to story points
  Historical average: 1 story point ≈ 4 hours
  Capacity: 254 ÷ 4 ≈ 63 story points

Step 5: Compare to velocity
  Average velocity: 25 points/sprint
  Available capacity: 63 points
  → Team has room, but velocity reflects real-world delivery
  → Plan based on velocity (25 points), not theoretical capacity
```

### Factors Affecting Capacity

```
Reducing Factors:
├── PTO / holidays / sick days
├── Meetings and ceremonies
├── On-call / support rotation
├── Training and onboarding new members
├── Cross-team dependencies (waiting)
├── Production incidents
├── Technical debt maintenance
└── Context switching between projects

Increasing Factors:
├── New team members (after ramp-up)
├── Process improvements
├── Better tooling / automation
├── Reduced meeting load
├── Clearer requirements (less rework)
└── Pair programming (quality, not speed)
```

### Capacity Planning for Multiple Teams

```
Portfolio Capacity:
┌──────────┬──────────┬───────────┬──────────────┐
│ Team     │ Velocity │ Capacity  │ Allocated To │
│          │ (pts/sp) │ (pts/sp)  │              │
├──────────┼──────────┼───────────┼──────────────┤
│ Team A   │ 30       │ 35        │ Product X    │
│ Team B   │ 25       │ 28        │ Product Y    │
│ Team C   │ 20       │ 22        │ Platform     │
├──────────┼──────────┼───────────┼──────────────┤
│ Total    │ 75       │ 85        │              │
└──────────┴──────────┴───────────┴──────────────┘

Key insight: Don't plan at 100% capacity.
Leave buffer for unplanned work, bugs, and technical debt.
```

---

## Interview Questions

### Beginner

**Q1: What is the difference between story points and hours?**

Story points measure relative effort considering complexity, effort, and uncertainty. Hours measure absolute time. Story points are team-level and stable over time; hours are individual-level and vary. Story points enable velocity-based planning; hours enable task-level scheduling.

**Q2: What is planning poker?**

Planning poker is a consensus-based estimation technique where team members independently select Fibonacci-numbered cards to estimate a user story, reveal simultaneously, discuss differences, and re-vote until reaching consensus. It prevents anchoring bias and surfaces hidden assumptions.

**Q3: What is a risk register?**

A risk register is a document that tracks identified risks, their likelihood, impact, risk score, mitigation strategies, and owners. It's a living document that's reviewed and updated throughout the project.

### Intermediate

**Q4: How do you handle a project that's behind schedule?**

Options in order of preference: (1) Descope — remove lower-priority features. (2) Add resources — but Brooks's Law warns this can slow things down initially. (3) Extend the deadline — if business allows. (4) Reduce quality — only as a last resort, and document the tech debt. (5) Crash the schedule — add resources to critical path tasks specifically. (6) Fast-track — do tasks in parallel that were sequential. Communicate transparently with stakeholders about the trade-offs of each option.

**Q5: What is velocity and how do you use it for planning?**

Velocity is the number of story points a team completes per sprint. Use it to: (1) Plan sprints — don't commit to more points than your velocity. (2) Predict release dates — remaining points ÷ velocity = sprints needed. (3) Identify trends — decreasing velocity signals problems. Important: velocity is a planning tool, not a performance metric. Don't compare velocities between teams.

**Q6: How do you manage scope creep?**

(1) Establish a change control process — all changes go through the PO. (2) Use MoSCoW prioritization — new features must displace existing ones. (3) Track changes formally — log every scope change with impact assessment. (4) Communicate trade-offs — "Adding X means removing Y or extending the deadline." (5) Freeze scope at sprint start — no mid-sprint changes. (6) Reserve capacity for unknowns — plan for 80% of capacity, leaving buffer.

### Advanced

**Q7: You're estimating a project with a new technology the team hasn't used. How do you handle the uncertainty?**

(1) Add explicit spike stories — time-boxed research to reduce uncertainty before estimating implementation. (2) Increase estimates by a factor (e.g., 1.5-2x) for stories involving the new technology. (3) Identify the highest-risk items and tackle them first. (4) Create a proof of concept before committing to the full estimate. (5) Use reference class forecasting — find similar projects and compare. (6) Break stories into smaller pieces — smaller estimates are more accurate. (7) Track actuals vs. estimates and recalibrate after each sprint.

**Q8: How do you do capacity planning when team members split time across multiple projects?**

(1) Calculate each person's available hours per project per sprint. (2) Account for context-switching overhead — typically 15-20% per additional project. (3) Create a capacity spreadsheet showing each person's allocation. (4) Use focused blocks — at least 4-hour uninterrupted blocks per project. (5) Reduce velocity expectations proportionally — a 50% allocation doesn't give 50% of velocity (closer to 40% due to context switching). (6) Advocate for dedicated teams — splitting reduces effectiveness significantly.

**Q9: A stakeholder asks "When will it be done?" for a large project with unclear requirements. How do you answer?**

Be honest about uncertainty: (1) Give a range, not a date — "Q3-Q4 based on current understanding." (2) Explain what you know and don't know — "We've estimated the core features at ~200 points. With our velocity of 25/sprint, that's 8 sprints (16 weeks). But we have 30% of requirements still unclear." (3) Use a cone of uncertainty — early estimates are ±4x, later estimates are ±25%. (4) Propose incremental delivery — "We can deliver the MVP in 6 weeks, full feature set in 16 weeks." (5) Create a probability-based forecast — "70% confident we'll finish by September, 90% by November." (6) Recommend a discovery phase to clarify requirements before giving a firm date.
