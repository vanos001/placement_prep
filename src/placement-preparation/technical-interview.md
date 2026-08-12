# Technical Interview Preparation

A technical interview tests problem solving, communication, correctness, and
trade-off awareness—not only whether code compiles. Treat the interview as a
small engineering design review with a time budget.

## A repeatable sequence

1. **Clarify:** restate inputs, outputs, constraints, mutability, duplicates,
   ordering, and invalid cases.
2. **Model:** choose a data structure or system boundary and explain why.
3. **Baseline:** state a simple correct approach and its complexity.
4. **Optimize:** use constraints to remove repeated work or improve locality.
5. **Prove:** state the invariant, induction, exchange argument, or safety
   property that makes the approach correct.
6. **Implement:** write readable code with explicit names and bounds.
7. **Test:** dry-run normal, empty, singleton, duplicate, boundary, and adversarial
   inputs.
8. **Analyze:** give time, space, latency, capacity, and failure trade-offs.

## Communication patterns

Say the decision before the code:

> “Because the input is sorted and we need logarithmic search, I will maintain
> an inclusive interval and use a lower-bound invariant.”

Ask clarifying questions instead of silently assuming. If a requirement is
ambiguous, state the assumption and explain how the design changes if it is
false.

## Coding checklist

- Define the invariant before writing the loop.
- Avoid integer overflow in midpoint, multiplication, and capacity calculations.
- Decide whether ownership, mutation, and aliasing are allowed.
- Do not hide complexity inside a library call without knowing its behavior.
- Keep error handling consistent with the requested API.
- Compile mentally after each structural change.

## System-design interview outline

For a system-design question:

1. Clarify users, traffic, latency, consistency, retention, and failure goals.
2. Estimate request rate, storage, bandwidth, and peak multipliers.
3. Draw the request path and data ownership.
4. Choose APIs, storage, queues, caches, indexes, and partitions.
5. Explain consistency and failure behavior before adding scale.
6. Address observability, security, migrations, and operations.
7. Identify bottlenecks and the next scaling boundary.

## Behavioral and experience bridge

Technical answers are stronger when connected to evidence. Prepare concise
stories covering an incident, a disagreement, a trade-off, a failure, a
performance improvement, and a project you would redesign. State the situation,
action, result, and what you learned; quantify impact without inventing numbers.

## Common failure modes

- Coding before confirming the problem.
- Giving an optimal algorithm without explaining correctness.
- Ignoring constraints until the solution is complete.
- Claiming “exactly once” without defining the failure boundary.
- Treating average latency as the user experience while ignoring p99.
- Overfitting to a familiar pattern even when the data model differs.
- Running out of time because edge cases were postponed until the end.

## Practice rubric

After each practice problem, record:

| Dimension | Question |
|---|---|
| Understanding | Did I identify the actual contract and constraints? |
| Approach | Could I explain the baseline and optimization? |
| Correctness | What invariant or proof makes it work? |
| Implementation | Did the code expose unsafe assumptions? |
| Testing | Which case would fail first? |
| Complexity | Can I justify every term? |
| Communication | Would another engineer be able to review it? |

## Cross-references

- [DSA problem-solving chapter](../dsa/chapters/ch47-problem-solving.md)
- [Technical communication](../dsa/chapters/ch48-technical-communication.md)
- [System design](../interview/system-design/README.md)
- [Behavioral interviews](../behavioral-interviews/README.md)
- [Coding patterns](../interview/coding/patterns.md)
- [Company preparation](../interview/companies/README.md)

## References

- [MIT 6.006 Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/)
- [MIT 6.046J Design and Analysis of Algorithms](https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/)
- [Google technical interviewing resources](https://careers.google.com/how-we-hire/interview/)
