# Requirements Engineering

## Table of Contents

- [What is Requirements Engineering?](#what-is-requirements-engineering)
- [Types of Requirements](#types-of-requirements)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [User Stories and Use Cases](#user-stories-and-use-cases)
- [Acceptance Criteria](#acceptance-criteria)
- [Requirements Gathering Techniques](#requirements-gathering-techniques)
- [MoSCoW Prioritization](#moscow-prioritization)
- [Requirements Traceability](#requirements-traceability)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)

---

## What is Requirements Engineering?

**Requirements Engineering (RE)** is the process of defining, documenting, and maintaining requirements throughout the software development lifecycle. It is the bridge between what stakeholders need and what developers build.

### The Requirements Engineering Process

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Elicitation │───▶│  Analysis    │───▶│ Specification│
│  (Gathering) │    │  & Modeling  │    │ (Writing)    │
└──────────────┘    └──────────────┘    └──────────────┘
                                              │
┌──────────────┐    ┌──────────────┐          │
│  Management  │◀───│  Validation  │◀─────────┘
│  (Tracking)  │    │  (Checking)  │
└──────────────┘    └──────────────┘
```

| Phase | Activities |
|---|---|
| **Elicitation** | Interviews, workshops, observation, surveys |
| **Analysis** | Categorize, resolve conflicts, model requirements |
| **Specification** | Write SRS, user stories, use cases |
| **Validation** | Reviews, prototyping, acceptance testing |
| **Management** | Track changes, traceability, version control |

---

## Types of Requirements

```
Requirements
├── Functional Requirements
│   └── What the system DOES
│       (features, behaviors, functions)
│
└── Non-Functional Requirements
    └── HOW WELL the system does it
        (performance, security, usability)
```

### Quick Comparison

| Aspect | Functional | Non-Functional |
|---|---|---|
| **Defines** | System behavior | System qualities |
| **Question** | "What should it do?" | "How well should it do it?" |
| **Example** | "User can log in" | "Login response < 2 seconds" |
| **Testing** | Functional tests, integration tests | Performance tests, security audits |
| **Visibility** | Visible to users | Often invisible to users |
| **Documented** | User stories, use cases | Quality attributes, SLAs |

---

## Functional Requirements

Functional requirements describe **specific behaviors and functions** the system must provide.

### Characteristics of Good Functional Requirements

```
✅ Specific     — "The system shall send a confirmation email within 60 seconds"
✅ Measurable   — Clear pass/fail criteria
✅ Achievable   — Technically feasible
✅ Traceable    — Linked to a business need
✅ Complete     — Covers all scenarios including edge cases
```

### Examples by Domain

**E-Commerce:**
```
FR-001: The system shall allow users to register using email or social login.
FR-002: The system shall display product search results with pagination (20 per page).
FR-003: The system shall apply discount codes at checkout.
FR-004: The system shall send order confirmation emails after successful payment.
FR-005: The system shall allow users to track order status in real-time.
```

**Banking:**
```
FR-010: The system shall process fund transfers between accounts within 5 seconds.
FR-011: The system shall require two-factor authentication for transfers > $10,000.
FR-012: The system shall generate monthly account statements in PDF format.
FR-013: The system shall flag suspicious transactions for manual review.
```

**Healthcare:**
```
FR-020: The system shall maintain a complete audit trail of all patient record access.
FR-021: The system shall alert nurses when patient vitals exceed defined thresholds.
FR-022: The system shall integrate with lab systems to display test results.
```

---

## Non-Functional Requirements

Non-functional requirements (NFRs) define **quality attributes, constraints, and properties** of the system. They are often called the "-ilities" of software.

### Categories of NFRs

```
Non-Functional Requirements
├── Performance
│   ├── Response time: "API responds within 200ms (p95)"
│   ├── Throughput: "Handle 10,000 requests/second"
│   ├── Latency: "Page load < 3 seconds on 3G"
│   └── Resource usage: "Memory < 512MB under normal load"
│
├── Scalability
│   ├── "Scale to 1 million concurrent users"
│   ├── "Auto-scale based on CPU utilization > 70%"
│   └── "Support horizontal scaling across 3 regions"
│
├── Availability
│   ├── "99.9% uptime (8.76 hours downtime/year)"
│   ├── "99.99% for payment processing"
│   └── "Recovery time objective (RTO) < 1 hour"
│
├── Security
│   ├── "All data encrypted at rest and in transit (AES-256)"
│   ├── "OWASP Top 10 compliance"
│   ├── "RBAC with principle of least privilege"
│   └── "Session timeout after 15 minutes of inactivity"
│
├── Usability
│   ├── "New user completes first task in < 5 minutes"
│   ├── "WCAG 2.1 AA accessibility compliance"
│   └── "Support for 5 languages (i18n)"
│
├── Reliability
│   ├── "Mean Time Between Failures (MTBF) > 720 hours"
│   ├── "Mean Time To Recovery (MTTR) < 30 minutes"
│   └── "Zero data loss on system failure"
│
├── Maintainability
│   ├── "Code coverage > 80%"
│   ├── "New developer productive within 2 weeks"
│   └── "Modular architecture for component replacement"
│
├── Portability
│   ├── "Runs on Linux, Windows, macOS"
│   ├── "Supports Chrome, Firefox, Safari, Edge"
│   └── "Docker containerized deployment"
│
└── Compliance
    ├── "GDPR compliant data handling"
    ├── "PCI DSS Level 1 for payment processing"
    └── "HIPAA compliant for healthcare data"
```

### How to Write Good NFRs

Use the **SMART** framework:

| Component | Poor Example | Good Example |
|---|---|---|
| **Specific** | "Fast response time" | "API response time" |
| **Measurable** | "Should be quick" | "< 200ms at p95" |
| **Achievable** | "Instant response" | "< 200ms with current infra" |
| **Relevant** | "Response time" | "Checkout API response time" |
| **Time-bound** | "200ms" | "200ms during peak hours (8-10 PM)" |

**Good NFR:** "The checkout API shall respond within 200ms at the 95th percentile during peak hours (8-10 PM), supporting up to 5,000 concurrent users with the current infrastructure."

---

## User Stories and Use Cases

### User Stories (Agile)

```
Format:
  As a [role],
  I want [feature],
  So that [benefit].

Example:
  As a returning customer,
  I want to save my shipping address,
  So that I don't have to re-enter it every time I order.
```

### Use Cases (Traditional)

A use case describes interactions between actors and the system to achieve a goal.

```
Use Case: Place Order
━━━━━━━━━━━━━━━━━━━━
Actor:         Registered Customer
Precondition:  User is logged in, cart has items
Trigger:       User clicks "Place Order"

Main Flow:
  1. System displays order summary
  2. User selects shipping address
  3. User selects payment method
  4. User clicks "Confirm Order"
  5. System validates payment
  6. System creates order record
  7. System sends confirmation email
  8. System displays order confirmation

Alternative Flows:
  3a. User adds new payment method
      3a.1 User enters card details
      3a.2 System validates card
      3a.3 Return to step 4

  5a. Payment fails
      5a.1 System displays error message
      5a.2 User selects different payment method
      5a.3 Return to step 5

Exception Flows:
  5b. Payment gateway timeout
      5b.1 System retries (max 3 times)
      5b.2 If still failing, system holds order for 30 minutes
      5b.3 System notifies user to retry later

Postcondition: Order is created and confirmation email sent
```

### User Story vs Use Case

| Aspect | User Story | Use Case |
|---|---|---|
| **Format** | Simple sentence | Detailed template |
| **Detail level** | Low — conversation starter | High — comprehensive |
| **Scope** | Small, focused | Can cover complex flows |
| **Audience** | Agile teams | Traditional/waterfall teams |
| **Documentation** | Lightweight | Heavy |
| **Best for** | Short iterations | Complex systems, contracts |

---

## Acceptance Criteria

Acceptance criteria define the **conditions that must be met** for a user story to be considered complete. They are the "definition of done" for a specific story.

### Formats

**Given/When/Then (Gherkin):**
```
Story: As a user, I want to search for products so that I can find what I need.

Scenario 1: Basic search
  Given I am on the homepage
  When I type "laptop" in the search bar and press Enter
  Then I see a list of products matching "laptop"
  And results are sorted by relevance

Scenario 2: No results
  Given I am on the homepage
  When I type "xyznonexistent" in the search bar and press Enter
  Then I see a message "No products found"
  And I see suggestions for related searches

Scenario 3: Empty search
  Given I am on the homepage
  When I click the search button without typing anything
  Then the search bar is highlighted with an error
  And I see "Please enter a search term"
```

**Checklist Format:**
```
Story: As a user, I want to reset my password.

Acceptance Criteria:
□ User receives a password reset email within 2 minutes
□ Reset link expires after 24 hours
□ New password must meet complexity requirements
□ Old password is invalidated after reset
□ User is redirected to login page after successful reset
□ Used reset links cannot be reused
□ Rate limited to 5 reset requests per hour per email
```

### Rules for Good Acceptance Criteria

```
✅ Independent — Each criterion can be tested separately
✅ Negotiable — Details can be discussed
✅ Testable — Clear pass/fail conditions
✅ Focused on "what" not "how" — No implementation details
✅ Concise — One sentence per criterion
✅ Covers happy path AND edge cases
```

---

## Requirements Gathering Techniques

### 1. Stakeholder Interviews

```
Types:
├── Structured — Predefined questions, formal
├── Semi-structured — Guided conversation with flexibility
└── Unstructured — Open-ended exploration

Tips:
├── Prepare questions in advance
├── Listen more than you talk (80/20 rule)
├── Ask "Why?" to uncover root needs
├── Use open-ended questions: "Walk me through..."
├── Avoid leading questions: "Don't you think X is better?"
└── Record and transcribe (with permission)
```

### 2. Workshops (JAD Sessions)

**Joint Application Development (JAD)** brings together stakeholders, users, and developers for facilitated workshops.

```
Workshop Structure:
├── 1. Define objectives (15 min)
├── 2. Present current state (30 min)
├── 3. Brainstorm requirements (60 min)
├── 4. Categorize and prioritize (30 min)
├── 5. Resolve conflicts (30 min)
└── 6. Document and confirm (15 min)

Participants:
├── Facilitator (neutral, keeps discussion on track)
├── Subject matter experts (domain knowledge)
├── End users (actual system users)
├── Developers (technical feasibility)
└── Business analysts (documentation)
```

### 3. Prototyping

```
Types:
├── Low-fidelity: Paper sketches, wireframes
│   └── Quick, cheap, good for early feedback
│
├── Medium-fidelity: Clickable mockups (Figma, Balsamiq)
│   └── Simulates user flow, good for UX validation
│
└── High-fidelity: Working prototype with sample data
    └── Near-real experience, expensive but very effective
```

### 4. Observation (Ethnography)

Watch users perform tasks in their natural environment. Reveals requirements that users wouldn't think to mention.

```
Types:
├── Passive observation — Watch without interacting
├── Active observation — Watch and ask questions
└── Contextual inquiry — Observe while user explains their work
```

### 5. Surveys and Questionnaires

```
Best for:
├── Gathering input from large groups
├── Quantifying preferences (rating scales)
├── Validating assumptions from interviews

Tips:
├── Keep it short (10-15 questions max)
├── Mix multiple-choice and open-ended
├── Pilot test with a small group first
└── Offer incentives for completion
```

### 6. Document Analysis

```
Sources:
├── Existing system documentation
├── Business process models
├── Regulatory requirements
├── Competitor analysis
├── Industry standards
└── User feedback/bug reports from current system
```

### 7. Brainstorming

```
Rules:
├── No criticism — all ideas are valid
├── Quantity over quality — generate many ideas
├── Build on others' ideas — "Yes, and..."
├── Encourage wild ideas — think outside the box
└── Stay focused on the topic

Techniques:
├── Round robin — Each person contributes one idea in turn
├── Silent brainstorming — Write ideas on sticky notes first
├── Mind mapping — Visual organization of related ideas
└── Reverse brainstorming — "How could we make this fail?"
```

---

## MoSCoW Prioritization

**MoSCoW** is a technique for prioritizing requirements by categorizing them into four levels.

### Categories

```
┌─────────────────────────────────────────────────────────┐
│                    MoSCoW Matrix                         │
├──────────────┬──────────────────────────────────────────┤
│  M - Must    │ Critical for launch. Without these, the  │
│    Have      │ product fails. Non-negotiable.            │
│              │ Example: "User can log in"                │
├──────────────┼──────────────────────────────────────────┤
│  S - Should  │ Important but not vital. Product can      │
│    Have      │ launch without them, but they add         │
│              │ significant value.                        │
│              │ Example: "User can filter search results"  │
├──────────────┼──────────────────────────────────────────┤
│  C - Could   │ Desirable but not necessary. Nice-to-have │
│    Have      │ features that improve experience.         │
│              │ Example: "Dark mode support"               │
├──────────────┼──────────────────────────────────────────┤
│  W - Won't   │ Explicitly excluded from this release.    │
│    Have      │ Acknowledged but deferred.                │
│  (this time) │ Example: "Social media integration"       │
└──────────────┴──────────────────────────────────────────┘
```

### Example: E-Commerce Platform

```
MUST HAVE (MVP):
├── User registration and login
├── Product catalog with search
├── Shopping cart
├── Checkout with payment processing
├── Order confirmation email
└── Basic admin dashboard

SHOULD HAVE (v1.1):
├── Product reviews and ratings
├── Wishlist functionality
├── Email notifications for order status
├── Advanced search with filters
└── Customer support chat

COULD HAVE (v1.2):
├── Dark mode
├── Product comparison
├── Loyalty program
├── Social media sharing
└── Recommended products

WON'T HAVE (this time):
├── AR product preview
├── Voice search
├── Blockchain-based supply tracking
└── Multi-vendor marketplace
```

### Rules for Effective MoSCoW

```
1. "Must Have" should not exceed 60% of the effort
   (If everything is a must, nothing is prioritized)

2. Assign effort/cost alongside priority
   (A "Should Have" that costs 2 days beats a "Could Have" that costs 2 hours)

3. Review priorities regularly
   (Business needs change — priorities should too)

4. Involve stakeholders in prioritization
   (Not just the PO — include users, developers, and business)

5. "Won't Have" is as important as "Must Have"
   (Explicitly saying no protects scope)
```

---

## Requirements Traceability

**Requirements Traceability** tracks the lifecycle of each requirement from origin to implementation and testing.

### Traceability Matrix

```
┌───────────┬────────────────────┬──────────┬──────────┬──────────┐
│ Req ID    │ Description        │ Source   │ Design   │ Test Case│
├───────────┼────────────────────┼──────────┼──────────┼──────────┤
│ FR-001    │ User registration  │ Stakehold│ Auth     │ TC-001   │
│           │                    │ er inter.│ Module   │ TC-002   │
├───────────┼────────────────────┼──────────┼──────────┼──────────┤
│ FR-002    │ Product search     │ User surv│ Search   │ TC-010   │
│           │                    │ ey       │ Service  │ TC-011   │
│           │                    │          │          │ TC-012   │
├───────────┼────────────────────┼──────────┼──────────┼──────────┤
│ NFR-001   │ Response < 200ms   │ SLA doc  │ Caching  │ TC-050   │
│           │                    │          │ Layer    │ TC-051   │
├───────────┼────────────────────┼──────────┼──────────┼──────────┤
│ NFR-002   │ 99.9% uptime       │ Business │ Redundant│ TC-060   │
│           │                    │ require. │ infra    │ TC-061   │
└───────────┴────────────────────┴──────────┴──────────┴──────────┘
```

### Types of Traceability

```
Forward Traceability:
  Requirement → Design → Code → Test
  "Is every requirement implemented and tested?"

Backward Traceability:
  Test → Code → Design → Requirement
  "Is every piece of code traceable to a requirement?"

Bidirectional Traceability:
  Both directions combined
  "Can we trace in both directions and identify orphan code or untested requirements?"
```

### Why Traceability Matters

```
├── Impact analysis — "If we change FR-001, what code and tests are affected?"
├── Coverage — "Do we have tests for all requirements?"
├── Compliance — Regulatory audits require proof of traceability
├── Change management — Track which requirements changed and why
└── Stakeholder confidence — Demonstrates thoroughness
```

---

## Common Pitfalls

### 1. Ambiguous Requirements

```
❌ Bad:  "The system should be fast"
✅ Good: "The search API shall return results within 200ms at the 95th percentile
         for queries against a catalog of up to 1 million products"

❌ Bad:  "The system should handle many users"
✅ Good: "The system shall support 10,000 concurrent users with < 500ms
         response time for all API endpoints"
```

### 2. Solution in Requirements

```
❌ Bad:  "The system shall use a MySQL database to store user data"
✅ Good: "The system shall persist user data with ACID compliance and
         support for relational queries"

(Requirements should say WHAT, not HOW)
```

### 3. Missing Non-Functional Requirements

```
Common overlooked NFRs:
├── Data retention — How long to keep data?
├── Backup/recovery — RTO and RPO?
├── Logging — What events to log?
├── Monitoring — What metrics to track?
├── Migration — How to move from old system?
└── Sunset — How to decommission the system?
```

### 4. Stakeholder Conflicts

```
Resolution strategies:
├── Data-driven — Use analytics to show user behavior
├── Prototype — Build it and let users decide
├── Escalate — Let the PO or business sponsor decide
├── Compromise — Find a middle ground
└── Defer — Move to a future release
```

---

## Interview Questions

### Beginner

**Q1: What is the difference between functional and non-functional requirements?**

Functional requirements describe what the system *does* — features, behaviors, and functions (e.g., "User can add items to cart"). Non-functional requirements describe how well the system does it — quality attributes like performance, security, and usability (e.g., "Cart updates within 200ms").

**Q2: What is MoSCoW prioritization?**

MoSCoW categorizes requirements into Must Have (critical for launch), Should Have (important but not vital), Could Have (nice-to-have), and Won't Have (deferred). It helps teams deliver the most important features first and manage scope.

**Q3: Why are acceptance criteria important?**

They define when a user story is "done." Without them, there's ambiguity about what's expected. Acceptance criteria provide testable conditions, reduce misunderstandings between developers and stakeholders, and serve as the basis for test cases.

### Intermediate

**Q4: How do you handle conflicting requirements from different stakeholders?**

First, document all perspectives. Then facilitate a discussion to understand each stakeholder's underlying need (not just their stated requirement — often the same need manifests differently). Use data and prototypes to resolve disagreements. If still conflicting, escalate to the Product Owner or business sponsor for a decision. Prioritize based on business value and user impact.

**Q5: What is requirements traceability and why is it important?**

Requirements traceability links each requirement to its source (stakeholder need), design decisions, implementation code, and test cases. It's important for: (1) Impact analysis — knowing what's affected when requirements change, (2) Coverage — ensuring all requirements are tested, (3) Compliance — regulatory audits often require traceability, (4) Accountability — tracking who requested what and why.

**Q6: Explain the difference between a user story and a use case.**

A user story is a lightweight, conversational format ("As a... I want... So that...") that serves as a placeholder for a conversation. A use case is a detailed document describing actor-system interactions, including main flows, alternative flows, and exception flows. User stories are better for Agile teams that prefer face-to-face communication; use cases are better for complex systems, contracts, or when documentation is required.

### Advanced

**Q7: You're gathering requirements for a system where users can't articulate what they need. How do you proceed?**

Use observation (watch users perform their current tasks), prototyping (build low-fidelity mockups and iterate based on reactions), and contextual inquiry (ask users to explain their workflow while performing it). Also analyze existing data — support tickets, analytics, and competitor products reveal pain points users have normalized. Create journey maps to visualize current workflows and identify friction. Sometimes users need to see what's possible before they can articulate what they want.

**Q8: How do you manage requirements in a large project with 500+ requirements?**

(1) Use a requirements management tool (Jira, Azure DevOps, IBM DOORS). (2) Organize requirements into hierarchical groups (epics → features → stories). (3) Assign unique IDs and maintain a traceability matrix. (4) Use baselines — snapshot requirements at key milestones. (5) Implement a formal change control process — every change request is evaluated for impact. (6) Regularly review and prune stale requirements. (7) Use MoSCoW to prioritize within each release.

**Q9: A client says "I know what I want" and provides a 200-page specification. How do you handle this?**

(1) Acknowledge the effort — they've done significant work. (2) Review the document and identify ambiguities, contradictions, and gaps — there will be many in 200 pages. (3) Propose a validation workshop to walk through key sections and confirm understanding. (4) Translate the specification into user stories or use cases for development. (5) Identify the highest-risk areas and suggest prototyping. (6) Establish a change process upfront — a 200-page spec will need updates. (7) Don't blindly follow it — use it as a starting point for conversation, not as gospel.
