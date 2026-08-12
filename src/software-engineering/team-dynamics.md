# Team Dynamics

## Table of Contents

- [Code Review Best Practices](#code-review-best-practices)
- [Communication](#communication)
- [Collaboration](#collaboration)
- [Conflict Resolution](#conflict-resolution)
- [Knowledge Sharing](#knowledge-sharing)
- [Team Formation](#team-formation)
- [Interview Questions](#interview-questions)

---

## Code Review Best Practices

Code review is one of the most impactful practices for improving code quality, sharing knowledge, and building team culture.

### Why Code Review Matters

```
Benefits:
├── Catches bugs before production
├── Ensures code quality and consistency
├── Shares knowledge across the team
├── Mentors junior developers
├── Reduces bus factor
├── Improves design through peer feedback
└── Builds shared coding standards
```

### For the Author (Pull Request Creator)

```
Before Submitting:
□ Self-review your own code first
□ Run all tests and ensure they pass
□ Run linters and fix all warnings
□ Keep PRs small (< 400 lines changed, ideally < 200)
□ Write a clear PR description:
  - What does this change do?
  - Why is it needed?
  - How does it work?
  - Any known limitations?
□ Link to the relevant issue/ticket
□ Add screenshots for UI changes
□ Tag appropriate reviewers
□ Break large changes into a stack of PRs

PR Description Template:
## What
Brief description of the change.

## Why
Link to issue or business context.

## How
Technical approach and key decisions.

## Testing
How was this tested? What test cases were added?

## Screenshots (if applicable)
Before/after screenshots.

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Self-reviewed
```

### For the Reviewer

```
Review Priorities (in order):
1. Design — Is the approach correct?
2. Functionality — Does it work? Are edge cases handled?
3. Complexity — Is it unnecessarily complex?
4. Tests — Are they adequate and meaningful?
5. Naming — Are names clear and consistent?
6. Comments — Are they helpful, not noisy?
7. Style — Does it follow team conventions?

Feedback Guidelines:
├── Be specific — point to exact lines
├── Explain WHY — not just "change this"
├── Offer alternatives — "Consider using X because..."
├── Ask questions — "What happens if Y?" instead of "This is wrong"
├── Praise good code — "Nice clean abstraction here"
├── Distinguish blockers from suggestions
│   ├── "Must fix:" — Blocks approval
│   ├── "Should fix:" — Strong recommendation
│   └── "Nit:" — Minor style preference, optional
├── Be timely — Review within 4 business hours
└── Be respectful — Review the code, not the person
```

### What NOT to Do in Code Review

```
❌ For the Author:
├── Submitting a 2000-line PR
├── Not responding to feedback
├── Taking feedback personally
├── "It works on my machine" as a defense
├── Submitting without self-reviewing
└── Force-pushing after review has started (without discussion)

❌ For the Reviewer:
├── "LGTM" without actually reading the code
├── Nitpicking style (use a linter instead)
├── Being condescending: "Why would you do this?"
├── Blocking PRs over personal preferences
├── Reviewing only the last commit (miss the big picture)
├── Taking days to review
└── Rewriting the code yourself instead of guiding
```

### Code Review Turnaround Times

```
PR Size          Expected Review Time
───────────      ────────────────────
< 100 lines      Within 2 hours
100-400 lines    Within 4 hours
400-1000 lines   Within 1 day
> 1000 lines     Should be broken up

Key insight: Review speed and PR size are inversely correlated.
Smaller PRs get faster, better reviews.
```

---

## Communication

### Why Communication Matters in Engineering

```
Engineers spend:
├── 30-50% of time communicating (meetings, Slack, email)
├── 10-20% of time in meetings
├── Rest on actual coding

Communication failures cause:
├── Misunderstood requirements → rework
├── Unclear expectations → frustration
├── Missed dependencies → delays
├── Knowledge silos → single points of failure
└── Team conflict → reduced productivity
```

### Communication Patterns

```
Synchronous (Real-time):
├── In-person / Video meetings
├── Phone calls
├── Instant messaging (Slack, Teams)
├── Pair programming
└── Daily standups

Best for:
├── Complex discussions requiring back-and-forth
├── Sensitive topics
├── Brainstorming
├── Urgent issues
└── Building relationships

Asynchronous (Not real-time):
├── Email
├── Pull request comments
├── Documentation (ADRs, RFCs)
├── Ticket comments (Jira, GitHub Issues)
├── Recorded video (Loom)
└── Wiki/knowledge base

Best for:
├── Non-urgent decisions
├── Detailed technical discussions
├── Information that needs to be referenced later
├── Distributed teams across time zones
└── Deep work that shouldn't be interrupted
```

### Meeting Best Practices

```
Every meeting should have:
├── A clear purpose (decide, discuss, or inform)
├── An agenda (shared before the meeting)
├── The right people (and only the right people)
├── A time limit (and a facilitator to enforce it)
├── Notes/action items (assigned to specific people)
└── A follow-up (were action items completed?)

Meeting Types:
├── Decision meeting → 30 min, small group, clear outcome
├── Brainstorming → 60 min, diverse group, no judgment
├── Status update → 15 min, use async instead if possible
├── 1:1 → 30 min, personal development and feedback
└── Retrospective → 60 min, team improvement
```

### Writing Effective Messages

```
Slack/Teams Messages:
├── Lead with the ask: "Need a decision on X by Friday"
├── Provide context: Link to PR, issue, or document
├── Be specific: "Can you review PR #42?" not "Can you look at something?"
├── Use threads: Keep conversations organized
├── Respect focus time: Don't expect instant replies
└── Summarize decisions: "To summarize: we agreed to use approach B"

Email:
├── Subject line: Clear, specific ("Decision needed: API versioning approach")
├── First paragraph: The ask or key information
├── Body: Supporting details
├── Action items: Who does what by when
└── Keep it short: If it takes > 5 min to write, consider a meeting
```

### Remote Communication

```
Challenges:
├── No body language cues
├── Time zone differences
├── "Zoom fatigue"
├── Harder to build relationships
└── Asynchronous delays

Solutions:
├── Default to async, sync when needed
├── Use video for complex/sensitive discussions
├── Over-communicate context (assume reader has no background)
├── Record meetings for absent team members
├── Use collaborative documents for real-time editing
├── Create virtual "water cooler" spaces
└── Respect working hours across time zones
```

---

## Collaboration

### Effective Collaboration Patterns

```
Pair Programming:
├── Driver writes code, navigator reviews and thinks
├── Switch roles every 25-30 minutes (Pomodoro)
├── Best for: complex problems, knowledge transfer, onboarding
└── Tools: VS Code Live Share, Tuple, Screen sharing

Mob/Ensemble Programming:
├── Whole team works on one problem together
├── Rotating driver, group navigation
├── Best for: critical code, team learning, complex architecture
└── Use for 1-2 hours, not all day

Design Reviews:
├── Present proposed design to the team before implementation
├── Use RFC or ADR format
├── Gather feedback on approach, not just code
├── Time-box to 30-60 minutes
└── Document the decision and rationale

Tech Talks / Brown Bags:
├── 30-minute presentations on technical topics
├── Team members take turns presenting
├── Topics: new technology, architecture patterns, lessons learned
├── Record for async viewing
└── Builds shared knowledge and presentation skills

Hackathons / Innovation Time:
├── Dedicated time for exploration and creativity
├── Can be 1 day/month or 10% time
├── Encourages experimentation and learning
├── Some best features come from hackathons
└── Present results to the team
```

### Cross-Team Collaboration

```
Challenges:
├── Different priorities and timelines
├── Different tech stacks and conventions
├── Communication overhead
├── Dependency management
└── Competing resources

Solutions:
├── Shared Slack channels for cross-team communication
├── Regular sync meetings (not too frequent)
├── Clear API contracts between teams
├── Shared documentation and architecture diagrams
├── Cross-team code reviews for shared components
├── Dedicated liaison or integration team
└── Aligned sprint schedules for dependency management
```

---

## Conflict Resolution

### Types of Technical Conflict

```
1. Technical Disagreement
   "We should use React vs. Vue"
   → Resolve with data, prototypes, or RFCs

2. Priority Conflict
   "We should fix tech debt vs. add features"
   → Resolve with business value analysis and PO decision

3. Process Conflict
   "We should do TDD vs. write tests after"
   → Resolve with team discussion and experimentation

4. Style Conflict
   "Tabs vs. spaces, functional vs. OOP"
   → Resolve with coding standards and automated formatting

5. Personality Conflict
   "Alice and Bob don't work well together"
   → Address directly, involve manager if needed
```

### The Conflict Resolution Framework

```
Step 1: Acknowledge
├── Recognize the conflict exists
├── Don't avoid it — it won't go away
└── Approach with curiosity, not judgment

Step 2: Understand
├── Listen to all perspectives
├── Ask "Why?" to understand underlying concerns
├── Separate positions (what they want) from interests (why they want it)
└── Example: "We need more tests" (position) → "I'm worried about bugs" (interest)

Step 3: Find Common Ground
├── Both sides want a successful product
├── Both sides want clean, maintainable code
├── Identify shared goals
└── Build from there

Step 4: Explore Options
├── Brainstorm solutions that address both interests
├── Consider prototypes or experiments
├── Look for hybrid approaches
└── "Can we try both for a week and compare?"

Step 5: Decide
├── Use data when possible
├── If no data, use a decision framework (ADR, RFC)
├── Time-box the discussion
├── Accept the decision even if you disagree (disagree and commit)
└── Document the decision and rationale

Step 6: Follow Up
├── Check if the decision is working
├── Be willing to revisit if new information emerges
├── Don't hold grudges
└── Learn from the process
```

### Healthy vs. Unhealthy Conflict

```
Healthy Conflict:                 Unhealthy Conflict:
├── Focuses on ideas              ├── Focuses on people
├── Respectful tone               ├── Personal attacks
├── Data-driven arguments         ├── Emotional arguments
├── Open to changing minds        ├── Entrenched positions
├── Seeks best solution           ├── Seeks to win
├── Ends with commitment          ├── Ends with resentment
└── Builds trust                  └── Erodes trust
```

### When to Escalate

```
Escalate to a manager when:
├── Personal attacks are occurring
├── The conflict is affecting team productivity
├── A decision can't be reached after reasonable discussion
├── There's a pattern of conflict with the same person
├── The conflict involves harassment or discrimination
└── Technical disagreement has become political
```

---

## Knowledge Sharing

### Why Knowledge Sharing Matters

```
Without knowledge sharing:
├── Single points of failure (bus factor = 1)
├── Slow onboarding for new team members
├── Repeated mistakes
├── Inconsistent code and practices
├── Knowledge lost when people leave
└── Reduced innovation (no cross-pollination)

With knowledge sharing:
├── Higher bus factor
├── Faster onboarding
├── Consistent practices
├── Better problem-solving (diverse perspectives)
├── Team growth and development
└── Resilient team (no single point of failure)
```

### Knowledge Sharing Techniques

```
1. Pair Programming
   ├── Real-time knowledge transfer
   ├── Junior learns from senior (and vice versa)
   ├── Best for: code-level knowledge, design patterns, tools
   └── Frequency: Regular (e.g., 2-3 sessions/week)

2. Code Reviews
   ├── Every PR is a learning opportunity
   ├── Reviewer learns the codebase, author gets feedback
   ├── Best for: code quality, conventions, patterns
   └── Frequency: Every PR

3. Tech Talks / Lunch & Learn
   ├── 30-60 minute presentations
   ├── Topics: new tech, architecture, lessons learned
   ├── Best for: broader concepts, team alignment
   └── Frequency: Weekly or bi-weekly

4. Documentation
   ├── ADRs for architectural decisions
   ├── Runbooks for operational knowledge
   ├── READMEs for project context
   ├── Best for: persistent knowledge
   └── Frequency: Continuous

5. Mob Programming
   ├── Whole team solves one problem together
   ├── Everyone learns the same thing simultaneously
   ├── Best for: complex problems, critical code
   └── Frequency: For specific challenges

6. Knowledge Base / Wiki
   ├── Central repository of team knowledge
   ├── Searchable, organized by topic
   ├── Best for: tribal knowledge, onboarding
   └── Frequency: Ongoing maintenance

7. Rotation Programs
   ├── Rotate team members across projects/components
   ├── Each person learns different parts of the system
   ├── Best for: broadening expertise, reducing silos
   └── Frequency: Quarterly rotation

8. Mentoring
   ├── Senior pairs with junior for ongoing guidance
   ├── Regular 1:1 meetings
   ├── Best for: career development, deep learning
   └── Frequency: Weekly 1:1s
```

### Onboarding New Team Members

```
Week 1: Orientation
├── Set up development environment
├── Introduce team members and stakeholders
├── Walk through architecture and system overview
├── Assign onboarding buddy
├── First PR: documentation fix or small bug
└── Read key documentation (ADRs, README, runbooks)

Week 2: Guided Development
├── Pair with buddy on a real feature
├── Attend all team ceremonies
├── Ask questions (encourage this!)
├── Complete a small, well-scoped task
└── Shadow an on-call rotation

Week 3-4: Independent Work
├── Take on a medium-complexity task
├── Buddy available for questions
├── Code review feedback on their PRs
├── Present a "What I've learned" to the team
└── Gradually increase responsibility

Success Metrics:
├── First PR merged within 2 days
├── Contributing independently within 2 weeks
├── Comfortable with full workflow within 1 month
└── Fully productive within 3 months
```

---

## Team Formation

### Tuckman's Stages of Group Development

```
┌─────────────────────────────────────────────────────────┐
│                  Tuckman's Model                         │
├──────────┬──────────────────────────────────────────────┤
│ Forming  │ Team comes together. Polite, cautious.       │
│          │ Members are getting to know each other.       │
│          │ Role: Leader provides clear direction.        │
├──────────┼──────────────────────────────────────────────┤
│ Storming │ Conflicts emerge. Disagreements about        │
│          │ approach, roles, and priorities.              │
│          │ Role: Leader facilitates, addresses conflict. │
├──────────┼──────────────────────────────────────────────┤
│ Norming  │ Team establishes norms and ways of working.  │
│          │ Trust builds. Collaboration improves.        │
│          │ Role: Leader steps back, team self-organizes.│
├──────────┼──────────────────────────────────────────────┤
│ Performing│ Team is highly effective and autonomous.     │
│          │ Members support each other. High trust.      │
│          │ Role: Leader focuses on removing obstacles.  │
├──────────┼──────────────────────────────────────────────┤
│ Adjourning│ Team disbands after project completion.     │
│          │ Celebrate achievements, reflect on learnings.│
│          │ Role: Leader ensures knowledge transfer.     │
└──────────┴──────────────────────────────────────────────┘
```

### Psychological Safety

```
Google's Project Aristotle found that the #1 factor
in high-performing teams is PSYCHOLOGICAL SAFETY.

Psychological safety means:
├── Team members feel safe to take risks
├── It's okay to admit mistakes
├── Questions are welcomed, not punished
├── Diverse opinions are valued
├── People speak up without fear of embarrassment
└── Failures are treated as learning opportunities

How to build it:
├── Leader goes first — admit your own mistakes
├── Respond to mistakes with curiosity, not blame
├── Actively invite quiet voices to share
├── Thank people for raising concerns
├── Separate idea critique from person critique
├── Celebrate learning from failure
└── No blameless retrospectives — truly blameless
```

### Team Topologies

```
┌─────────────────────────────────────────────────────────┐
│ Team Topologies (Skelton & Pais)                        │
├──────────────┬──────────────────────────────────────────┤
│ Stream-aligned│ Aligned to a business flow.             │
│ Team         │ Delivers end-to-end value.               │
│              │ The primary team type.                    │
├──────────────┼──────────────────────────────────────────┤
│ Enabling     │ Helps other teams acquire capabilities.  │
│ Team         │ Example: DevOps, security, performance.  │
│              │ Temporary — teams become self-sufficient. │
├──────────────┼──────────────────────────────────────────┤
│ Complicated- │ Manages complex subsystems.              │
│ Subsystem    │ Example: ML models, payment processing.  │
│ Team         │ Requires deep specialist knowledge.      │
├──────────────┼──────────────────────────────────────────┤
│ Platform     │ Provides internal services to reduce     │
│ Team         │ cognitive load on stream-aligned teams.  │
│              │ Example: CI/CD, monitoring, infrastructure│
└──────────────┴──────────────────────────────────────────┘
```

---

## Interview Questions

### Beginner

**Q1: Why are code reviews important?**

Code reviews catch bugs before production, ensure code quality and consistency, share knowledge across the team, mentor junior developers, and reduce the bus factor. They're one of the most cost-effective quality practices — every PR is a learning opportunity for both author and reviewer.

**Q2: What makes a good code review comment?**

Good comments are specific (point to exact lines), explain the "why" (not just "change this"), offer alternatives ("Consider using X because..."), ask questions ("What happens if Y?"), and distinguish blockers from suggestions. Be respectful — review the code, not the person.

**Q3: What is psychological safety?**

Psychological safety is the belief that you won't be punished or humiliated for speaking up with ideas, questions, concerns, or mistakes. Google's Project Aristotle found it's the #1 factor in high-performing teams. It's built when leaders model vulnerability, respond to mistakes with curiosity, and actively invite diverse perspectives.

### Intermediate

**Q4: How do you handle a disagreement about a technical approach in a code review?**

(1) Acknowledge the other person's perspective — "I see why you'd suggest that." (2) Present your reasoning with data or examples. (3) Ask for their reasoning — "Help me understand the benefits of your approach." (4) If still disagreeing, propose an experiment or prototype. (5) If no clear winner, use the team's decision framework (ADR, RFC, team vote). (6) Once decided, commit fully — even if it wasn't your preferred choice. Don't let disagreements block PRs for days.

**Q5: How do you build a knowledge-sharing culture?**

(1) Lead by example — share what you learn. (2) Make it easy — use existing tools (Slack, wiki, PR descriptions). (3) Create dedicated time — tech talks, brown bags, learning Fridays. (4) Reward sharing — recognize contributors publicly. (5) Make it part of the process — documentation in Definition of Done, PR descriptions required. (6) Rotate responsibilities — on-call, code review assignments, project leads. (7) Pair programming — the most effective real-time knowledge transfer.

**Q6: How do you handle a team member who doesn't participate in code reviews?**

(1) Understand why — are they too busy? Uncomfortable giving feedback? Don't see the value? (2) Set clear expectations — code review participation is part of the job. (3) Make it easier — assign specific PRs for review, provide review guidelines. (4) Start small — ask for a review of a simple PR. (5) Pair them with an experienced reviewer to learn the process. (6) If it's a workload issue, address capacity. (7) If it's a cultural issue, address it in the retrospective.

### Advanced

**Q7: You're joining a team with low psychological safety. How do you improve it?**

(1) Start with yourself — openly admit your own mistakes and knowledge gaps. "I don't know, let me look into that" is powerful. (2) Ask questions instead of making statements — "What do you think about...?" rather than "We should..." (3) Thank people for raising concerns — "Thanks for catching that" reinforces the behavior. (4) In retrospectives, focus on processes, not people — "The deployment process failed" not "Bob broke production." (5) Celebrate learning from failure — share post-mortems as learning exercises. (6) Have 1:1 conversations with team members who are quiet — they may have insights they don't feel safe sharing publicly. (7) Be patient — psychological safety takes months to build but can be destroyed in seconds.

**Q8: How do you manage knowledge silos in a team?**

(1) Identify silos — map who knows what. Use a skills matrix or knowledge map. (2) Start with the highest-risk silo — the one with the most critical knowledge held by one person. (3) Pair the knowledge holder with others — pair programming, shadowing, documentation. (4) Rotate responsibilities — on-call, feature ownership, code review assignments. (5) Create a documentation culture — every time you learn something, write it down. (6) Establish team norms — no single-person projects, all code reviewed by at least 2 people. (7) Measure progress — track bus factor improvement over time.

**Q9: A remote team is struggling with communication and collaboration. What would you do?**

Diagnose first: (1) Are people communicating too much or too little? (2) Are meetings ineffective? (3) Is there timezone friction? (4) Are people feeling isolated? Then apply solutions: (1) Default to async — use written communication (PR descriptions, ADRs, RFCs) over meetings. (2) Over-communicate context — remote teams need more written context than co-located ones. (3) Create virtual social spaces — casual Slack channels, virtual coffee chats. (4) Establish clear communication norms — response time expectations, when to use sync vs. async. (5) Record important meetings for timezone-challenged team members. (6) Use collaborative tools — shared documents, virtual whiteboards. (7) Invest in periodic in-person gatherings — even 1-2 times/year builds relationships that improve daily collaboration.
