# Amazon Interview Guide

## 🎯 Amazon's Interview Process

```
Typical Amazon SDE Interview:
├── Online Assessment (OA):
│   ├── Coding problems (2-3)
│   └── Work simulation / Logical reasoning
├── Phone Screen (1): Coding + behavioral
├── On-site (4-5 rounds):
│   ├── Coding Round 1: Data structures
│   ├── Coding Round 2: Algorithms
│   ├── System Design (SDE II+): Distributed systems
│   ├── Behavioral (Loop): Leadership Principles (2-3 rounds)
│   └── "Bar Raiser": Independent evaluator
└── Bar Raiser has veto power
```

## 📊 Amazon's Leadership Principles

**This is the most important section.** Amazon maps EVERY behavioral question to their 16 Leadership Principles (LPs). Failing the behavioral round = no offer, regardless of technical performance.

```
┌─────────────────────────────────────────────────────────┐
│           AMAZON LEADERSHIP PRINCIPLES                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  CUSTOMER OBSESSION                                      │
│  "Leaders start with the customer and work backwards"   │
│  Q: "Tell me about a time you went above and beyond     │
│      for a customer"                                    │
│                                                         │
│  OWNERSHIP                                               │
│  "Leaders are owners"                                   │
│  Q: "Tell me about a time you took on something         │
│      outside your role"                                 │
│                                                         │
│  INVENT AND SIMPLIFY                                     │
│  "Leaders expect and require innovation"                │
│  Q: "Tell me about the most innovative thing you've     │
│      done"                                              │
│                                                         │
│  ARE RIGHT, A LOT                                        │
│  "Leaders are right a lot"                              │
│  Q: "Tell me about a time you made a difficult          │
│      decision with limited data"                        │
│                                                         │
│  LEARN AND BE CURIOUS                                    │
│  "Leaders are never done learning"                      │
│  Q: "Tell me about a time you learned something new     │
│      to solve a problem"                                │
│                                                         │
│  HIRE AND DEVELOP THE BEST                               │
│  "Leaders raise the performance bar"                    │
│  Q: "Tell me about a time you mentored someone"         │
│                                                         │
│  INSIST ON THE HIGHEST STANDARDS                         │
│  "Leaders have relentlessly high standards"             │
│  Q: "Tell me about a time you raised the bar"           │
│                                                         │
│  THINK BIG                                               │
│  "Leaders create and communicate a bold direction"      │
│  Q: "Tell me about a time you proposed a vision"        │
│                                                         │
│  BIAS FOR ACTION                                         │
│  "Speed matters in business"                            │
│  Q: "Tell me about a time you had to make a quick       │
│      decision"                                          │
│                                                         │
│  FRUGALITY                                               │
│  "Accomplish more with less"                            │
│  Q: "Tell me about a time you did more with less"       │
│                                                         │
│  EARN TRUST                                              │
│  "Leaders listen attentively and speak candidly"        │
│  Q: "Tell me about a time you had to deliver bad news"  │
│                                                         │
│  DIVE DEEP                                               │
│  "Leaders operate at all levels"                        │
│  Q: "Tell me about a time you found a root cause"       │
│                                                         │
│  HAVE BACKBONE; DISAGREE AND COMMIT                      │
│  "Leaders respectfully challenge decisions"             │
│  Q: "Tell me about a time you disagreed with your       │
│      manager"                                           │
│                                                         │
│  DELIVER RESULTS                                         │
│  "Leaders focus on key inputs and deliver with quality" │
│  Q: "Tell me about a time you met a tight deadline"     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🎯 How to Prepare LP Stories

### Story Mapping Template

Prepare **8-10 stories** that can cover **multiple LPs**:

| Story | LPs Covered |
|-------|------------|
| Led team through crisis | Ownership, Deliver Results, Bias for Action |
| Improved system performance | Customer Obsession, Dive Deep, Insist on Highest Standards |
| Mentored junior developer | Hire and Develop, Earn Trust |
| Proposed new architecture | Think Big, Invent and Simplify, Are Right A Lot |
| Handled production incident | Ownership, Dive Deep, Deliver Results |
| Disagreed with tech lead | Have Backbone, Earn Trust |

### STAR Format for Amazon

Amazon explicitly expects STAR format. Interviewers are trained to probe for each component:

```
Situation: "In Q3 2024, our payment processing service was experiencing
           2% failure rate during peak hours, affecting 50K customers daily."

Task: "As the technical lead, I needed to identify the root cause and
      reduce failures below 0.1% within 2 weeks."

Action: "I set up distributed tracing to identify the bottleneck.
        Found that our database connection pool was undersized.
        I implemented connection pooling with dynamic sizing,
        added circuit breakers for external service calls,
        and set up real-time alerting for connection exhaustion.
        I also created a runbook for the on-call team."

Result: "Failure rate dropped from 2% to 0.05% within 1 week.
        Saved an estimated $200K in lost revenue per month.
        The approach was adopted by 3 other teams."
```

## 💻 Coding at Amazon

### What Makes Amazon Different
- **Practical focus:** Problems often relate to real scenarios
- **OA is important:** Online assessment screens many candidates
- **Optimization matters:** Discuss time/space complexity
- **Working code required:** Must compile and pass test cases

### Common Amazon Coding Topics
1. **Arrays & Strings** — Most common
2. **Trees & Graphs** — Especially BFS/DFS
3. **Dynamic Programming** — Medium difficulty
4. **System Design** — Practical, Amazon-scale

## 🏗️ System Design at Amazon

### Amazon-Specific Design Topics
- Design Amazon.com (e-commerce platform)
- Design Prime Video (streaming)
- Design Alexa (voice assistant)
- Design Amazon's recommendation system
- Design a distributed cache

### Amazon's Design Focus
- **Customer-centric:** Always start with customer needs
- **Scale:** Amazon handles massive traffic
- **Reliability:** 99.99% uptime expected
- **Cost optimization:** Frugality principle

## 💡 Tips for Amazon

1. **Prepare LPs thoroughly** — This is non-negotiable
2. **Use STAR format** — Interviewers are trained to look for it
3. **Include metrics** — Quantify your impact
4. **Show ownership** — "I" not "we" for your contributions
5. **Be specific** — Vague answers score low on LPs
6. **Prepare for "Tell me more"** — Interviewers dig deep

## 🔗 Cross-References

- [STAR Method](../behavioral/star.md) — Amazon's expected format
- [Common Behavioral Questions](../behavioral/common.md) — LP-mapped questions
- [System Design](../system-design/README.md) — Amazon-scale design
