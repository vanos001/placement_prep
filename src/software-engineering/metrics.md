# Software Metrics

## Table of Contents

- [Why Metrics Matter](#why-metrics-matter)
- [Code Metrics](#code-metrics)
- [Cyclomatic Complexity](#cyclomatic-complexity)
- [Code Coverage](#code-coverage)
- [DORA Metrics](#dora-metrics)
- [Process Metrics](#process-metrics)
- [Quality Metrics](#quality-metrics)
- [Team Metrics](#team-metrics)
- [Metrics Anti-Patterns](#metrics-anti-patterns)
- [Interview Questions](#interview-questions)

---

## Why Metrics Matter

> "You can't improve what you don't measure." — Peter Drucker

Metrics provide **objective evidence** for decisions that would otherwise be based on gut feeling. They help teams identify problems, track improvement, and communicate progress.

### The Metrics Hierarchy

```
Level 1: Activity Metrics (vanity)
├── Lines of code written
├── Number of commits
├── Hours worked
└── ❌ Easy to game, don't indicate quality

Level 2: Output Metrics (better)
├── Features delivered
├── Story points completed
├── Bugs fixed
└── ⚠️ Measure quantity, not value

Level 3: Outcome Metrics (best)
├── Customer satisfaction
├── Revenue impact
├── Time to market
├── Defect escape rate
└── ✅ Measure actual value delivered

Level 4: Impact Metrics (ultimate)
├── Business goals achieved
├── User behavior changes
├── Market share
└── ✅ Connect engineering to business outcomes
```

---

## Code Metrics

### Lines of Code (LOC)

```
What it measures: Size of the codebase

Uses:
├── Rough estimation of project size
├── Tracking growth over time
├── Comparing module sizes

Problems:
├── More code ≠ better code
├── Language-dependent (Python vs Java)
├── Incentivizes verbose code
└── Says nothing about quality

Verdict: Useful as context, dangerous as a target.
```

### Halstead Complexity Metrics

```
Based on:
├── n1 = number of distinct operators
├── n2 = number of distinct operands
├── N1 = total number of operators
├── N2 = total of operands

Derived metrics:
├── Vocabulary: n = n1 + n2
├── Length: N = N1 + N2
├── Volume: V = N × log2(n)
├── Difficulty: D = (n1/2) × (N2/n2)
├── Effort: E = D × V
└── Time: T = E / 18 seconds

Interpretation:
├── Higher volume = more complex code
├── Higher difficulty = harder to maintain
└── Higher effort = more time to understand/modify
```

### Maintainability Index

```
Formula (simplified):
MI = 171 - 5.2 × ln(V) - 0.23 × CC - 16.2 × ln(LOC)

Where:
├── V = Halstead volume
├── CC = Cyclomatic complexity
└── LOC = Lines of code

Interpretation:
├── MI > 20  → Good maintainability
├── MI 10-20 → Moderate maintainability
└── MI < 10  → Poor maintainability (needs refactoring)
```

---

## Cyclomatic Complexity

Cyclomatic complexity measures the **number of independent paths** through a code segment. Introduced by Thomas McCabe in 1976.

### How to Calculate

```
Formula: M = E − N + 2P

Where:
├── E = number of edges in the control flow graph
├── N = number of nodes in the control flow graph
└── P = number of connected components (usually 1)

Simplified: M = (number of decision points) + 1
```

### Visual Examples

```
Simple function (CC = 1):
┌─────────┐
│  Start   │
└────┬────┘
     ▼
┌─────────┐
│  return  │
│  result  │
└─────────┘

If-else (CC = 2):
┌─────────┐
│  Start   │
└────┬────┘
     ▼
   ◇ condition ◇
  /             \
 ▼               ▼
┌──────┐    ┌──────┐
│ path │    │ path │
│  A   │    │  B   │
└──┬───┘    └──┬───┘
   └─────┬─────┘
         ▼
   ┌─────────┐
   │  return  │
   └─────────┘

If-else-if (CC = 3):
Similar to above but with 3 paths

Switch with 4 cases (CC = 4):
4 paths through the switch + 1 for the entry = 5? No,
each case is a path, default is another. CC = number of cases.
```

### Code Examples

```python
# CC = 1 (no decision points)
def add(a, b):
    return a + b

# CC = 2 (one decision point)
def absolute(n):
    if n < 0:        # +1
        return -n
    return n

# CC = 3 (two decision points)
def classify_age(age):
    if age < 13:       # +1
        return "child"
    elif age < 18:     # +1
        return "teenager"
    else:
        return "adult"

# CC = 4 (three decision points)
def validate_password(password):
    if len(password) < 8:       # +1
        return False
    if not has_uppercase(password):  # +1
        return False
    if not has_number(password):     # +1
        return False
    return True

# CC = 5 (four decision points)
def process_order(order):
    if not order.is_valid():    # +1
        return "invalid"
    if order.is_paid():         # +1
        if order.has_stock():   # +1
            return "ship"
        else:
            return "backorder"
    else:
        if order.payment_failed():  # +1
            return "payment_error"
        else:
            return "pending"
```

### Complexity Thresholds

```
CC Range    Risk Level      Action
────────    ──────────      ──────
1-10        Low             Simple, easy to test
11-20       Moderate        Consider refactoring
21-50       High            Should refactor
50+         Very High       Must refactor immediately
```

### Reducing Cyclomatic Complexity

```python
# Before (CC = 5):
def get_shipping_cost(order):
    if order.country == "US":
        if order.weight < 1:
            return 5.99
        elif order.weight < 5:
            return 9.99
        else:
            return 14.99
    elif order.country == "UK":
        return 12.99
    else:
        return 19.99

# After (CC = 1 — lookup table):
SHIPPING_RATES = {
    "US": [(1, 5.99), (5, 9.99), (float("inf"), 14.99)],
    "UK": [(float("inf"), 12.99)],
}

def get_shipping_cost(order):
    rates = SHIPPING_RATES.get(order.country, [(float("inf"), 19.99)])
    for max_weight, cost in rates:
        if order.weight < max_weight:
            return cost
```

---

## Code Coverage

Code coverage measures the **percentage of code executed** during testing.

### Types of Coverage

```
┌─────────────────────────────────────────────────────────┐
│                    Coverage Types                        │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│ Line         │ What percentage of lines are executed?   │
│ Coverage     │ Simple, most common metric               │
│              │                                          │
├──────────────┼──────────────────────────────────────────┤
│              │                                          │
│ Branch       │ What percentage of branches (if/else,    │
│ Coverage     │ switch cases) are tested?                │
│              │ More meaningful than line coverage        │
│              │                                          │
├──────────────┼──────────────────────────────────────────┤
│              │                                          │
│ Function     │ What percentage of functions are called? │
│ Coverage     │ Catches completely untested functions    │
│              │                                          │
├──────────────┼──────────────────────────────────────────┤
│              │                                          │
│ Condition    │ What percentage of boolean sub-          │
│ Coverage     │ expressions are evaluated both ways?     │
│              │ Most granular, hardest to achieve         │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
```

### Example

```python
def classify(score):
    if score >= 90:          # Branch A
        return "A"
    elif score >= 80:        # Branch B
        return "B"
    elif score >= 70:        # Branch C
        return "C"
    else:                    # Branch D
        return "F"

# Test: classify(95) → "A"
# Line coverage:     ~50% (only lines 2-3 executed)
# Branch coverage:   25% (only branch A tested)

# Test: classify(95), classify(85), classify(75), classify(50)
# Line coverage:     100% (all lines executed)
# Branch coverage:   100% (all 4 branches tested)
```

### Coverage Targets

```
Target      Context
────────    ─────────────────────────────────────────
60-70%      Minimum for legacy codebases starting out
70-80%      Good for most applications
80-90%      Strong coverage for critical systems
90%+        Critical systems (healthcare, finance)
100%        Rarely justified — diminishing returns

Important:
├── 100% coverage ≠ bug-free code
├── Coverage measures breadth, not depth
├── A test that doesn't assert anything still counts
├── Focus on meaningful tests, not percentage
└── Branch coverage > line coverage for quality assessment
```

### Tools

```
Language       Tools
────────       ─────
Python         coverage.py, pytest-cov
JavaScript     Istanbul/nyc, Jest built-in
Java           JaCoCo, Cobertura
Go             go test -cover
C#             dotnet cover, OpenCover
Ruby           SimpleCov
```

---

## DORA Metrics

The **DevOps Research and Assessment (DORA)** team identified four key metrics that predict software delivery performance.

### The Four Key Metrics

```
┌─────────────────────────────────────────────────────────────┐
│                      DORA Metrics                            │
├──────────────────────┬──────────────────────────────────────┤
│                      │                                      │
│  Deployment Frequency│ How often do you deploy to           │
│                      │ production?                          │
│                      │                                      │
│  Elite: Multiple/day │ High: Weekly  │ Low: Monthly+       │
│                      │                                      │
├──────────────────────┼──────────────────────────────────────┤
│                      │                                      │
│  Lead Time for       │ Time from commit to production       │
│  Changes             │ deployment                           │
│                      │                                      │
│  Elite: < 1 hour     │ High: < 1 week  │ Low: > 1 month   │
│                      │                                      │
├──────────────────────┼──────────────────────────────────────┤
│                      │                                      │
│  Change Failure Rate │ Percentage of deployments causing    │
│                      │ failures in production               │
│                      │                                      │
│  Elite: < 5%         │ High: < 20%    │ Low: > 30%        │
│                      │                                      │
├──────────────────────┼──────────────────────────────────────┤
│                      │                                      │
│  Mean Time to        │ Time to restore service after a      │
│  Recovery (MTTR)     │ production failure                   │
│                      │                                      │
│  Elite: < 1 hour     │ High: < 1 day  │ Low: > 1 week     │
│                      │                                      │
└──────────────────────┴──────────────────────────────────────┘
```

### DORA Performance Levels

```
                Elite          High           Medium         Low
                ─────          ────           ──────         ───
Deployment      Multiple/day   Weekly-Monthly Monthly        Monthly-Yearly
Frequency

Lead Time       < 1 hour       1 day-1 week   1 week-1 month > 1 month

Change Failure  0-5%           10-20%         16-30%         > 30%

MTTR            < 1 hour       < 1 day        < 1 week       > 1 week
```

### Why DORA Metrics Matter

```
Research findings:
├── Elite performers deploy 973x more frequently
├── Elite performers have 6570x faster lead time
├── Elite performers have 3x lower change failure rate
├── Elite performers recover 6570x faster
└── These metrics are correlated — improving one improves others

Key insight: Speed and stability are NOT trade-offs.
Elite teams are both faster AND more reliable.
```

### How to Measure DORA Metrics

```
Deployment Frequency:
├── Count deployments to production per time period
├── Source: CI/CD pipeline logs, deployment tools
└── Example: 15 deployments in 5 working days = 3/day

Lead Time for Changes:
├── Start: Timestamp of commit
├── End: Timestamp of production deployment
├── Source: Git log + deployment logs
└── Example: Commit at 10:00 AM, deployed at 11:30 AM = 1.5 hours

Change Failure Rate:
├── Failures: Deployments causing incidents, rollbacks, or hotfixes
├── Total: Total deployments in the period
├── Formula: (Failures / Total) × 100
└── Example: 2 failures out of 50 deployments = 4%

MTTR:
├── Start: Incident detected (alert fired)
├── End: Service restored (monitoring confirms)
├── Source: Incident management tool (PagerDuty, Opsgenie)
└── Example: Alert at 3:00 PM, resolved at 4:30 PM = 1.5 hours
```

---

## Process Metrics

### Velocity

```
Story points completed per sprint.

Sprint 1: 23 pts    Sprint 4: 27 pts
Sprint 2: 28 pts    Sprint 5: 26 pts
Sprint 3: 25 pts    Sprint 6: 28 pts

Average: 26.2 pts/sprint
Trend: Stable (good) or improving (great)

Uses: Sprint planning, release forecasting
Misuse: Performance comparison between teams
```

### Sprint Burndown

```
Remaining work (story points) over the sprint duration.

Points
  30 ┤●
     │ ╲
  25 ┤   ●
     │     ╲
  20 ┤       ╲
     │         ●
  15 ┤           ╲
     │             ●
  10 ┤               ╲
     │                 ●
   5 ┤                   ╲
     │                     ●
   0 ┤───────────────────────●
     Day1 Day2 Day3 Day4 Day5 Day6 Day7 Day8 Day9 Day10

Ideal line: straight diagonal from start to end
Actual: Shows real progress, may deviate

Above ideal line = behind schedule
Below ideal line = ahead of schedule
Flat = blocked work
```

### Cycle Time vs Lead Time

```
Lead Time:  Customer request → Delivery complete
            ├──────────────────────────────────────┤

Cycle Time: Work started → Work complete
                     ├────────────────────────┤

            ┌──────────┬────────────────────┬──────────┐
            │  Queue   │    Active Work     │  Review  │
            │ (wait)   │  (in progress)     │ & Deploy │
            └──────────┴────────────────────┴──────────┘
            ◄── Lead Time ─────────────────────────────►
                     ◄── Cycle Time ──────────►

Why they matter:
├── Lead time measures customer experience
├── Cycle time measures team efficiency
├── Long queue time = prioritization or capacity problem
├── Long cycle time = process or complexity problem
└── Track both to identify bottlenecks
```

### Throughput

```
Number of items completed per unit of time.

Week 1: 8 items    Week 4: 10 items
Week 2: 7 items    Week 5: 9 items
Week 3: 9 items    Week 6: 11 items

Average: 9 items/week

Combined with cycle time:
If cycle time = 3 days and throughput = 9 items/week
Then WIP (work in progress) = throughput × cycle time = 9 × (3/5) ≈ 5.4 items
(Using Little's Law: L = λ × W)
```

---

## Quality Metrics

### Defect Density

```
Formula: Defects per KLOC (thousand lines of code)

Example:
├── 15 defects found in 50,000 lines of code
├── Defect density = 15 / 50 = 0.3 defects/KLOC

Benchmarks (varies by domain):
├── < 0.1 defects/KLOC — Excellent (safety-critical systems)
├── 0.1-0.5 defects/KLOC — Good (commercial software)
├── 0.5-1.0 defects/KLOC — Average
└── > 1.0 defects/KLOC — Needs improvement
```

### Defect Escape Rate

```
Formula: (Defects found in production / Total defects) × 100

Example:
├── 120 defects found during testing
├── 8 defects found in production
├── Total: 128 defects
├── Escape rate: (8 / 128) × 100 = 6.25%

Interpretation:
├── < 5% — Excellent testing process
├── 5-10% — Good
├── 10-20% — Needs improvement
└── > 20% — Testing process is inadequate
```

### Customer-Found Defects

```
Track defects reported by customers (not internal QA).

Metrics:
├── Count per release
├── Severity distribution
├── Time to fix
├── Trend over time (should decrease)
└── By feature/component (identifies problem areas)
```

### Technical Debt Ratio

```
Formula: (Remediation cost / Development cost) × 100

Example:
├── Estimated effort to fix all tech debt: 400 hours
├── Total development effort for the release: 2,000 hours
├── Tech debt ratio: (400 / 2,000) × 100 = 20%

Benchmarks:
├── < 5% — Healthy codebase
├── 5-15% — Manageable debt
├── 15-30% — Significant debt, plan remediation
└── > 30% — Critical debt, prioritize now
```

---

## Team Metrics

### Bus Factor

```
Bus Factor: How many team members would need to be "hit by a bus"
            before the project is in serious trouble?

Bus Factor = 1  → Dangerous (single point of failure)
Bus Factor = 2  → Risky
Bus Factor = 3+ → Healthy

How to measure:
├── For each component/module, who understands it?
├── How many people can deploy, configure, and debug it?
└── What knowledge is held by only one person?

Improving bus factor:
├── Pair programming
├── Code reviews
├── Documentation
├── Knowledge sharing sessions
└── Rotation of responsibilities
```

### Code Review Metrics

```
Metrics to track:
├── Review turnaround time — How long from PR to first review?
├── Review depth — Comments per PR (too few = rubber stamping)
├── Approval rate — First-time approval vs. rework
├── Reviewer distribution — Is one person reviewing everything?
└── PR size — Smaller PRs get faster, better reviews

Targets:
├── First review within 4 business hours
├── PR size < 400 lines changed
├── Multiple reviewers for critical code
└── At least 1-2 substantive comments per PR
```

---

## Metrics Anti-Patterns

```
❌ Anti-Pattern 1: Measuring Individuals
   "John wrote 500 lines of code today!"
   Problem: Incentivizes verbose code, punishes refactoring
   Solution: Measure team-level metrics only

❌ Anti-Pattern 2: Gaming Metrics
   "We need to increase velocity, so let's estimate higher"
   Problem: Metric becomes meaningless
   Solution: Use metrics for learning, not rewards/punishment

❌ Anti-Pattern 3: Too Many Metrics
   Tracking 50 metrics that nobody looks at
   Problem: Information overload, nothing actionable
   Solution: Start with 3-5 key metrics, expand as needed

❌ Anti-Pattern 4: Vanity Metrics
   "We have 1 million lines of code!"
   Problem: Doesn't indicate quality or value
   Solution: Focus on outcome metrics (defect rate, lead time)

❌ Anti-Pattern 5: Using Metrics as Targets
   "Code coverage must be 90% or the PR is rejected"
   Problem: Goodhart's Law — "When a measure becomes a target,
   it ceases to be a good measure"
   Solution: Use metrics as conversation starters, not gates

❌ Anti-Pattern 6: Ignoring Context
   "Team A's velocity is higher than Team B's"
   Problem: Different teams, different stories, different contexts
   Solution: Never compare metrics across teams
```

---

## Interview Questions

### Beginner

**Q1: What is cyclomatic complexity and why does it matter?**

Cyclomatic complexity measures the number of independent paths through a code segment. Higher complexity means more paths to test, higher risk of bugs, and harder maintenance. A function with CC > 10 should be refactored. It matters because it directly correlates with defect density and testing effort.

**Q2: What is code coverage?**

Code coverage measures the percentage of code executed during testing. Types include line coverage (which lines ran), branch coverage (which branches were taken), and function coverage (which functions were called). It's necessary but not sufficient — 100% coverage doesn't mean bug-free code.

**Q3: What are the four DORA metrics?**

Deployment Frequency (how often you deploy), Lead Time for Changes (commit to production), Change Failure Rate (percentage of deployments causing failures), and Mean Time to Recovery (how fast you recover from failures). Elite teams excel at all four — speed and stability are correlated, not opposed.

### Intermediate

**Q4: How do you use velocity effectively without misusing it?**

Use velocity for: sprint planning (how much to commit), release forecasting (when will we finish), and trend analysis (are we improving?). Never use it for: comparing teams, measuring individual performance, or setting targets. If velocity is gamed (inflating estimates), the planning benefit is lost. Keep velocity as a planning tool, not a performance metric.

**Q5: What's the difference between lead time and cycle time?**

Lead time measures the full journey from customer request to delivery (includes waiting in queue). Cycle time measures only the active work period (from start to completion). If lead time is 10 days but cycle time is 3 days, 7 days are spent waiting — indicating a queue or prioritization problem. Both are important: lead time for customer experience, cycle time for team efficiency.

**Q6: Why might high code coverage be misleading?**

Because coverage measures breadth, not depth. A test that calls a function but doesn't assert anything contributes to coverage but catches no bugs. Tests might only cover the happy path and miss edge cases. Coverage doesn't measure test quality — you can have 100% coverage with weak assertions. Focus on branch coverage over line coverage, and combine coverage with mutation testing for better quality assessment.

### Advanced

**Q7: How would you set up a metrics dashboard for an engineering team?**

Layer 1 (always visible): DORA metrics (deployment frequency, lead time, change failure rate, MTTR). Layer 2 (weekly review): Velocity trend, cycle time distribution, code review turnaround, defect escape rate. Layer 3 (monthly review): Technical debt ratio, bus factor, test coverage trend, customer satisfaction. Implementation: Use CI/CD data for deployment metrics, git analytics for lead time and PR metrics, incident management tools for MTTR, and Jira/project tools for velocity and cycle time. Automate data collection — manual tracking fails. Review metrics in retrospectives as conversation starters, not judgments.

**Q8: A team's velocity has been steadily increasing for 6 sprints. Is this good news?**

Not necessarily. Investigate: (1) Are story point estimates consistent? If the team is inflating estimates, velocity increases without real improvement. (2) Is quality maintained? Increasing velocity with increasing defect rate means shipping faster but shipping worse. (3) Has the team composition changed? Adding people temporarily increases capacity, not long-term velocity. (4) Are stories getting smaller? Smaller stories at the same complexity complete faster. (5) Is technical debt accumulating? Short-term velocity gains from skipping refactoring create long-term slowdowns. The best indicator is whether cycle time and defect rate remain stable or improve alongside velocity.

**Q9: How do you measure the ROI of technical debt reduction?**

(1) Measure the current cost: developer time spent working around debt (estimated from sprint velocity impact), incident frequency caused by debt, and time spent on manual processes that should be automated. (2) Track before/after: velocity before and after refactoring, defect rate change, lead time improvement, developer satisfaction surveys. (3) Calculate: if removing debt X costs 40 hours but saves 2 hours/sprint, payback is 20 sprints (40 weeks). (4) Use the tech debt ratio trend: decreasing ratio indicates healthy investment. (5) Present to stakeholders in business terms: "This refactoring will reduce deployment failures by 50%, saving approximately 20 engineering hours per month."
