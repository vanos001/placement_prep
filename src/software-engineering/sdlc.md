# Software Development Life Cycle (SDLC) Models

## Table of Contents

- [What is SDLC?](#what-is-sdlc)
- [Phases of SDLC](#phases-of-sdlc)
- [Waterfall Model](#waterfall-model)
- [V-Model](#v-model)
- [Iterative Model](#iterative-model)
- [Incremental Model](#incremental-model)
- [Spiral Model](#spiral-model)
- [Agile Model](#agile-model)
- [Comparison Table](#comparison-table)
- [Choosing the Right Model](#choosing-the-right-model)
- [Interview Questions](#interview-questions)

---

## What is SDLC?

The **Software Development Life Cycle (SDLC)** is a structured framework that defines the processes used to build software from inception to deployment and maintenance. It provides a systematic approach to planning, designing, developing, testing, and deploying software systems.

### Why SDLC Matters

- Provides a clear roadmap for project execution
- Helps estimate costs, timelines, and resources
- Ensures quality through defined checkpoints
- Reduces project risk through structured planning
- Enables better communication among stakeholders

---

## Phases of SDLC

Most SDLC models share these fundamental phases, though they may order and combine them differently:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Requirement  │───▶│    Design    │───▶│ Implementation│───▶│   Testing    │
│   Analysis    │    │              │    │  (Coding)     │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                   │
       ┌───────────────────────────────────────────────────────────┘
       ▼
┌──────────────┐    ┌──────────────┐
│  Deployment  │───▶│ Maintenance  │
└──────────────┘    └──────────────┘
```

| Phase | Purpose | Key Activities |
|---|---|---|
| **Requirements Analysis** | Understand what to build | Stakeholder interviews, use cases, SRS document |
| **Design** | Plan how to build it | Architecture diagrams, database schema, UI mockups |
| **Implementation** | Write the code | Coding, unit testing, code reviews |
| **Testing** | Verify correctness | Integration testing, system testing, UAT |
| **Deployment** | Release to users | Staging, production rollout, monitoring |
| **Maintenance** | Keep it running | Bug fixes, patches, enhancements |

---

## Waterfall Model

The **Waterfall Model** is the earliest SDLC approach, proposed by Winston Royce in 1970. It follows a strict linear-sequential flow where each phase must complete before the next begins.

### Visual Representation

```
  ┌─────────────────────────────────────────────────────┐
  │              Requirements Gathering                  │
  └─────────────────────────┬───────────────────────────┘
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │                    System Design                     │
  └─────────────────────────┬───────────────────────────┘
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │                   Implementation                     │
  └─────────────────────────┬───────────────────────────┘
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │                Integration & Testing                 │
  └─────────────────────────┬───────────────────────────┘
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │                   Deployment                         │
  └─────────────────────────┬───────────────────────────┘
                            ▼
  ┌─────────────────────────────────────────────────────┐
  │                   Maintenance                        │
  └─────────────────────────────────────────────────────┘
```

### Characteristics

- Each phase has specific deliverables and a review process
- No overlapping between phases
- Document-driven: heavy emphasis on documentation
- Progress flows in one direction — downward like a waterfall

### Pros

| Advantage | Explanation |
|---|---|
| Simple and easy to understand | Linear flow is intuitive for teams and stakeholders |
| Well-documented | Each phase produces formal documentation |
| Easy to manage | Clear milestones and deliverables at each stage |
| Works well for small projects | When requirements are well-understood upfront |
| Clear deadlines | Each phase has a defined start and end |

### Cons

| Disadvantage | Explanation |
|---|---|
| Inflexible to changes | Going back to a previous phase is expensive and difficult |
| Late testing | Testing starts only after implementation is complete |
| No working software until late | Stakeholders don't see a product until near the end |
| Poor fit for complex projects | Assumes all requirements can be known upfront |
| High risk for long projects | Requirements may change during extended timelines |

### When to Use

- Requirements are well-documented, clear, and fixed
- The project is short and simple
- Technology stack is well-understood
- The team has done similar projects before
- Regulatory/compliance projects requiring extensive documentation (e.g., healthcare, aerospace)

---

## V-Model

The **V-Model** (Verification and Validation Model) is an extension of the Waterfall model. Each development phase has a corresponding testing phase, forming a "V" shape.

### Visual Representation

```
        Verification                    Validation
        ───────────                     ──────────
              ┌─────────────────┐
              │   Requirements   │──────────────▶ Acceptance Testing
              └────────┬────────┘
                       │  ┌──────────────────────┐
              ┌────────▼──┴──────┐               │
              │      Design      │──────────────▶ System Testing
              └────────┬────────┘
                       │  ┌──────────────────────┐
              ┌────────▼──┴──────┐               │
              │  Detailed Design  │──────────────▶ Integration Testing
              └────────┬────────┘
                       │  ┌──────────────────────┐
              ┌────────▼──┴──────┐               │
              │   Implementation │──────────────▶ Unit Testing
              └─────────────────┘
```

### Mapping: Development ↔ Testing

| Development Phase | Corresponding Testing Phase |
|---|---|
| Requirements Analysis | Acceptance Testing |
| System Design | System Testing |
| Detailed Design | Integration Testing |
| Implementation | Unit Testing |

### Pros

- Testing is planned in parallel with development — no "testing phase" gap
- Defects are found early because each phase is verified
- High success rate due to early verification
- Excellent for projects with well-defined requirements

### Cons

- Still rigid and inflexible like Waterfall
- No early prototypes — working software comes late
- Expensive to make changes once a phase is complete
- Not suitable for projects with evolving requirements

### When to Use

- Safety-critical systems (medical devices, automotive, aerospace)
- Projects with clear, stable requirements
- When regulatory compliance demands rigorous verification

---

## Iterative Model

The **Iterative Model** develops the system through repeated cycles (iterations). Each iteration produces a working version of the software that is progressively enhanced.

### Visual Representation

```
Iteration 1          Iteration 2          Iteration 3
┌───────────┐       ┌───────────┐       ┌───────────┐
│ Req ─ Design│     │ Req ─ Design│     │ Req ─ Design│
│ Code ─ Test │     │ Code ─ Test │     │ Code ─ Test │
└─────┬─────┘       └─────┬─────┘       └─────┬─────┘
      ▼                   ▼                   ▼
   v0.1 (basic)        v0.2 (more)        v1.0 (full)
```

### Characteristics

- Each iteration goes through all SDLC phases
- A working product is delivered at the end of each iteration
- Feedback from each iteration informs the next
- Risk is reduced because high-risk features can be tackled early

### Pros

- Early working software for stakeholder feedback
- Easier to manage risk — address risky parts first
- Easier to test and debug during smaller iterations
- Feedback is incorporated throughout development

### Cons

- Requires careful planning of iterations
- Architecture must be designed to accommodate changes
- Not all requirements may be gathered upfront
- Can lead to scope creep if iterations aren't well-scoped

### When to Use

- Large, complex projects where requirements may evolve
- When early feedback is critical
- Projects with known high-risk components

---

## Incremental Model

The **Incremental Model** delivers the software in increments (pieces). Each increment adds functional capabilities to the previous version.

### Visual Representation

```
     ┌─────────┐     ┌─────────┐     ┌─────────┐
     │ Core    │     │ Feature │     │ Feature │
     │ Module  │────▶│  Set A  │────▶│  Set B  │────▶ Final Product
     └─────────┘     └─────────┘     └─────────┘
     (Increment 1)   (Increment 2)   (Increment 3)
```

### Incremental vs Iterative

| Aspect | Incremental | Iterative |
|---|---|---|
| Approach | Build the system in functional pieces | Refine the entire system through repeated cycles |
| Deliverables | Each increment adds new functionality | Each iteration improves existing functionality |
| Core idea | "Build piece by piece" | "Refine again and again" |
| Architecture | Must plan module boundaries upfront | Must plan for evolution |

Many modern approaches combine both — delivering increments iteratively (e.g., Agile).

### When to Use

- When core functionality needs to be delivered early
- When the system can be naturally divided into modules
- When users need a usable product as soon as possible

---

## Spiral Model

The **Spiral Model**, proposed by Barry Boehm in 1988, combines iterative development with systematic risk analysis. Each loop of the spiral represents a phase of development.

### Visual Representation

```
              ┌─────── Risk Analysis ───────┐
              │                              │
              │    ┌───── Plan ─────┐       │
              │    │                 │       │
              │    │  ┌── Develop ──┐│       │
              │    │  │  & Evaluate ││       │
              │    │  └─────────────┘│       │
              │    └─────────────────┘       │
              └──────────────────────────────┘
                              │
                              ▼
                  (Next loop — larger spiral)
```

Each loop has four phases:

1. **Planning** — Determine objectives, alternatives, constraints
2. **Risk Analysis** — Identify and resolve risks
3. **Engineering** — Develop and test the product
4. **Evaluation** — Review results and plan the next iteration

### Pros

- Risk management is built into every cycle
- Suitable for large, complex, high-risk projects
- Allows for iterative refinement with strong risk controls
- Can incorporate Waterfall or other models within each loop

### Cons

- Expensive — risk analysis requires specialized expertise
- Complex to manage
- Not suitable for small or low-risk projects
- Difficult to determine when to stop spiraling

### When to Use

- Large, expensive, and complicated projects
- High-risk projects (e.g., new technology, mission-critical)
- When requirements are not fully understood
- Research and development projects

---

## Agile Model

The **Agile Model** is a group of iterative and incremental approaches that emphasize flexibility, collaboration, and rapid delivery. Covered in depth in the [Agile & Scrum chapter](./agile.md).

### Core Values (Agile Manifesto)

```
Individuals and interactions   over   Processes and tools
Working software               over   Comprehensive documentation
Customer collaboration         over   Contract negotiation
Responding to change           over   Following a plan
```

### Key Characteristics

- Short iterations (1–4 weeks) called sprints
- Continuous feedback from stakeholders
- Self-organizing, cross-functional teams
- Embraces change at any stage
- Working software is the primary measure of progress

---

## Comparison Table

| Feature | Waterfall | V-Model | Iterative | Incremental | Spiral | Agile |
|---|---|---|---|---|---|---|
| **Approach** | Sequential | Sequential + Testing | Cyclical | Incremental delivery | Risk-driven | Adaptive |
| **Flexibility** | Low | Low | Medium | Medium | Medium | High |
| **Risk Management** | Low | Low | Medium | Medium | High | Medium |
| **Customer Involvement** | Low | Low | Medium | Medium | Medium | High |
| **Documentation** | Heavy | Heavy | Medium | Medium | Medium | Light |
| **Working Software** | Late | Late | Early | Early | Varies | Every sprint |
| **Cost of Change** | High | High | Medium | Medium | Medium | Low |
| **Best For** | Fixed requirements | Safety-critical | Evolving projects | Modular systems | High-risk | Dynamic requirements |
| **Team Size** | Any | Any | Medium | Medium | Large | Small (3-9) |
| **Delivery** | End of project | End of project | Each iteration | Each increment | Each spiral | Every sprint |

---

## Choosing the Right Model

```
                        ┌──────────────────────┐
                        │ Are requirements clear│
                        │ and unlikely to change?│
                        └──────────┬───────────┘
                              ┌────┴────┐
                             YES        NO
                              │         │
                    ┌─────────▼──┐   ┌──▼──────────────┐
                    │ Is it safety│   │ Is it high-risk?│
                    │ critical?   │   └──┬──────────────┘
                    └─────┬──────┘   ┌───┴───┐
                     ┌────┴────┐    YES      NO
                    YES        NO    │       │
                     │         │  ┌──▼──┐ ┌──▼──────┐
                ┌────▼───┐ ┌──▼──┐Spiral│ │  Agile  │
                │V-Model │ │Water-│     │ │         │
                │        │ │fall  │     │ └─────────┘
                └────────┘ └─────┘     │
                                       │
                            ┌──────────▼──────────┐
                            │ Can it be delivered  │
                            │ in functional pieces?│
                            └──────────┬──────────┘
                                  ┌────┴────┐
                                 YES        NO
                                  │         │
                            ┌─────▼───┐ ┌───▼──────┐
                            │Incremental│ │Iterative │
                            └─────────┘ └──────────┘
```

### Quick Decision Guide

| Scenario | Recommended Model |
|---|---|
| Building a compliance/regulatory system | Waterfall or V-Model |
| Startup MVP with changing requirements | Agile |
| Government defense contract with high risk | Spiral |
| Releasing features to users quickly | Incremental |
| Complex system where requirements evolve | Iterative |
| Safety-critical embedded system | V-Model |
| Small team, tight deadlines, clear scope | Waterfall |
| Unclear requirements, new technology | Agile or Spiral |

---

## Interview Questions

### Beginner

**Q1: What is the difference between Waterfall and Agile?**

Waterfall is a linear, sequential model where each phase completes before the next begins. Agile is an iterative approach that delivers working software in short cycles (sprints) with continuous feedback. Waterfall requires fixed upfront requirements; Agile embraces changing requirements.

**Q2: Why is the V-Model called "V"?**

Because the development phases descend on the left side of the "V" and the corresponding testing phases ascend on the right side. Each development phase maps directly to a testing phase, forming a V shape.

**Q3: What is the main advantage of the Spiral model?**

Risk management is integrated into every iteration. Each spiral cycle includes explicit risk analysis, making it ideal for large, high-risk projects where requirements are unclear.

### Intermediate

**Q4: When would you choose Iterative over Incremental development?**

Choose Iterative when you want to refine the entire system through repeated cycles — each iteration improves the overall product. Choose Incremental when you want to deliver functional pieces of the system separately — each increment adds new features. For example, a search engine might benefit from Iterative (refining search quality), while an e-commerce platform might benefit from Incremental (adding checkout, then wishlist, then reviews).

**Q5: Can you combine SDLC models? Give an example.**

Yes. A common hybrid is using a Spiral model at the macro level for risk management, while using Agile sprints within each spiral iteration for development. Another example: using Waterfall for requirements and design phases (when contractually required), then switching to Agile for implementation and testing.

**Q6: How does the choice of SDLC model affect testing strategy?**

In Waterfall/V-Model, testing is a distinct phase with comprehensive test plans written upfront. In Agile, testing is continuous and integrated into each sprint — testers and developers collaborate daily. In Incremental models, regression testing becomes critical because each new increment must work with previous ones.

### Advanced

**Q7: You're leading a 200-person project for a medical device with regulatory requirements. The requirements are 80% clear but 20% will evolve during development. What SDLC approach would you recommend?**

Use a hybrid approach: V-Model for the safety-critical components that require formal verification and regulatory documentation, combined with Agile sprints for the evolving 20% (e.g., user interface, connectivity features). The V-Model portion ensures compliance documentation, while Agile portions allow flexibility. Use integration checkpoints to synchronize both tracks.

**Q8: How do modern DevOps practices map to traditional SDLC phases?**

DevOps doesn't replace the SDLC but accelerates it. CI/CD pipelines automate the implementation → testing → deployment flow. Infrastructure as Code blurs design and implementation. Monitoring extends the maintenance phase into continuous observability. GitOps creates a feedback loop from deployment back to development. The result is that traditional "phases" become concurrent activities rather than sequential gates.

**Q9: A startup has a 6-month runway and needs to launch an MVP in 3 months. Which SDLC model and why?**

Agile with Scrum (2-week sprints). Reasoning: (1) Requirements will evolve based on user feedback — startup ideas pivot frequently. (2) 6 sprints allow incremental delivery with stakeholder review. (3) Each sprint produces working software, enabling early user testing. (4) Prioritization via product backlog ensures the most valuable features ship first. (5) The team can pivot after the MVP based on real user data without wasting 3 months on unused features.
