# Communication Assessment Rounds

Communication rounds evaluate how clearly you explain ideas, handle pushback, and adapt your language to different audiences. They are common in consulting, product, and leadership-track roles.

## Types of Communication Rounds

| Type | Format | What They Test |
|------|--------|----------------|
| Technical explanation | Whiteboard or verbal | Simplifying complex concepts |
| System design walkthrough | 30-45 min discussion | Structured thinking, clarity |
| Behavioral communication | STAR-based Q&A | Articulating experience |
| Written assessment | Email, memo, or PR review | Written clarity and tone |

## Explaining Technical Concepts

The core skill is adjusting depth to your audience.

**Framework: ADEPT**

| Step | Action | Example (Explain Caching) |
|------|--------|-----------------------------|
| **A**nalogy | Start with a familiar comparison | "Like keeping frequently used books on your desk" |
| **D**iagram | Draw a simple picture | Client → Cache → Database |
| **E**xample | Give a concrete scenario | "A product page loaded in 50ms instead of 2s" |
| **P**rimer | Define the technical term | "A cache stores computed results for faster reuse" |
| **T**echnical detail | Add depth as needed | "LRU eviction, TTL, cache invalidation strategies" |

**Common mistake:** Jumping to technical detail before establishing context. Always confirm the audience's familiarity first.

## System Design Walkthroughs

When presenting a design, follow a top-down structure:

1. **Restate the problem** to confirm understanding.
2. **State assumptions** and constraints explicitly.
3. **Present the high-level architecture** before components.
4. **Explain each component** with its responsibility and trade-off.
5. **Address failure modes** and how the system degrades.
6. **Summarize** with key decisions and alternatives considered.

## Behavioral Communication

Use the STAR method with emphasis on the **A** (Action) — interviewers want to hear your reasoning, not just outcomes.

> "When the API latency spiked (Situation), I needed to identify the root cause without disrupting users (Task). I added distributed tracing and found the database connection pool was exhausted, so I implemented connection pooling with circuit breakers (Action). Latency dropped from 3s to 200ms p99 (Result)."

**Key principle:** Quantify results. "Improved performance" is weak; "reduced p99 latency by 93%" is strong.

## Written Communication Tests

Companies may ask you to write an email, a design document section, or a code review comment.

**Email structure for a technical audience:**
- Subject line with context and action needed
- One-sentence summary of the issue
- Background (2-3 sentences)
- Proposed solution with rationale
- Next steps with owners and deadlines

**Code review comments:** Focus on the *why*, not the *what*.

```
// Weak: "Use a hash map here."
// Strong: "A hash map gives O(1) lookup vs O(n) for the list,
// which matters because this runs in the request hot path
// with up to 10k entries."
```

## Interview Tips

- Pause before answering; a 3-second silence shows thoughtfulness, not hesitation.
- If interrupted, let the interviewer finish, then acknowledge their point before continuing.
- Ask clarifying questions — it demonstrates active listening.
- Avoid jargon when the interviewer has a different background.
- End explanations with a summary sentence to confirm shared understanding.

## Cross-references

- [Interview communication](../communication/interview-communication.md)
- [Technical communication](../communication/technical-communication.md)
- [Written communication](../communication/written-communication.md)
- [STAR method](../behavioral-interviews/star-method.md)
- [Technical interview preparation](./technical-interview.md)