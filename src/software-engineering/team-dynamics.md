# Team Dynamics & Code Review

## Code Review Best Practices

### As a Reviewer

1. **Understand the context** — Read the PR description and linked issues first
2. **Review in order** — Start with the design, then implementation, then style
3. **Be specific** — "This could cause a race condition on line 42" > "This is buggy"
4. **Use prefixes**:
   - `blocker:` — Must fix before merge
   - `suggestion:` — Nice to have
   - `question:` — Curious, not blocking
   - `nit:` — Trivial style issue
5. **Praise good code** — "Nice use of the strategy pattern here"
6. **Limit review size** — 200-400 lines max per session; quality drops after

### As an Author

1. **Self-review first** — Catch obvious issues before requesting review
2. **Write a clear description** — What, why, how, testing done
3. **Keep PRs small** — Easier to review, faster feedback
4. **Respond to every comment** — Even if just "Done" or "Good point, fixed"
5. **Don't take it personally** — Feedback is about code, not you

### Code Review Checklist

- [ ] Does the code do what the ticket says?
- [ ] Are edge cases handled?
- [ ] Is error handling adequate?
- [ ] Are there tests? Do they cover the new code?
- [ ] Is the code readable? Could a stranger understand it?
- [ ] Are there any security concerns?
- [ ] Is there any performance issue?
- [ ] Are naming conventions followed?

## Communication

### Effective Technical Communication

1. **Start with the "why"** — Context before details
2. **Use concrete examples** — Abstract explanations confuse
3. **Draw diagrams** — A picture replaces 1000 words
4. **State assumptions** — "Assuming X is true..." prevents misunderstandings
5. **Summarize first** — TL;DR at the top, details below

### Meeting Etiquette

- **Daily standup**: What you did, what you'll do, blockers. < 2 minutes per person.
- **Sprint planning**: Break down stories, estimate, commit to scope.
- **Retrospective**: What went well, what didn't, action items. Blameless.
- **Design review**: Present options, trade-offs, get feedback before coding.

## Conflict Resolution

### When You Disagree with a Teammate

1. **Seek to understand** — Ask "Can you walk me through your reasoning?"
2. **Present data** — Benchmarks, metrics, precedents
3. **Propose a compromise** — "What if we try X for now and revisit?"
4. **Know when to escalate** — If unresolved, involve tech lead
5. **Disagree and commit** — Once decided, support the decision fully

### When You Receive Critical Feedback

1. **Listen without defending** — Take notes, process later
2. **Ask for specifics** — "Can you give me an example?"
3. **Thank the reviewer** — Feedback is a gift
4. **Follow up** — Show you acted on the feedback

## Knowledge Sharing

### Effective Practices

- **Documentation**: Write down decisions (ADRs), runbooks, onboarding guides
- **Pair programming**: Real-time knowledge transfer
- **Tech talks**: 30-minute sessions on new technologies
- **Mob programming**: Whole team works on one problem
- **Code comments**: Explain "why", not "what"
- **README files**: Setup instructions, architecture overview

### Onboarding New Team Members

1. **Buddy system**: Assign an experienced team member
2. **Good first issues**: Small, well-scoped tasks
3. **Architecture overview**: System diagram, key decisions
4. **Shadowing**: Observe code reviews, meetings, on-call
5. **30-60-90 day plan**: Clear milestones and expectations

## Interview Questions

**Q: How do you handle disagreements in code review?**
A: (1) Understand the reviewer's perspective, (2) present your reasoning with data, (3) suggest a compromise, (4) if still unresolved, involve a tech lead, (5) once decided, commit fully. The goal is the best code, not being right.

**Q: How do you ensure knowledge isn't siloed in one person?**
A: (1) Code reviews ensure at least 2 people understand each change, (2) pair programming on complex features, (3) document decisions in ADRs, (4) rotate on-call and feature ownership, (5) tech talks for knowledge sharing.

**Q: What makes a good code review?**
A: Focus on correctness, edge cases, readability, and design — not style nits. Be specific and constructive. Use prefixes (blocker/suggestion/nit). Keep PRs small enough to review effectively (< 400 lines). Praise good patterns too.

## References

- [Google Engineering Practices — Code Review](https://google.github.io/eng-practices/review/)
- [SmartBear — Best Practices for Code Review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)
- [The Team Topologies Book](https://teamtopologies.com/)
