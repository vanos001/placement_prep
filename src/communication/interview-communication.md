# Interview Communication

## How to Communicate in Technical Interviews

### The Think-Aloud Protocol

**Always verbalize your thought process.** Interviewers evaluate HOW you think, not just the answer.

```
❌ Silent coding for 10 minutes, then "Here's my solution."

✅ "Let me think about this... The brute force would be O(n²) because 
    for each element, I'd check all others. Can I do better? 
    If I sort first... but that changes the order. 
    What if I use a hash map to store what I've seen? 
    That gives me O(n) time with O(n) space."
```

### Structure for Problem Solving

1. **Clarify** (2-3 min)
   - "Can the input be empty?"
   - "Are there negative numbers?"
   - "What should I return if there's no solution?"
   - "Is the input sorted?"

2. **Plan** (3-5 min)
   - Start with brute force
   - Identify the bottleneck
   - Propose optimizations
   - Get interviewer buy-in

3. **Implement** (15-20 min)
   - Write clean, readable code
   - Use meaningful variable names
   - Handle edge cases

4. **Test** (3-5 min)
   - Walk through with an example
   - Test edge cases (empty, single element, duplicates)
   - Verify time/space complexity

5. **Discuss** (remaining time)
   - Trade-offs
   - Alternative approaches
   - How to extend the solution

### Asking Clarifying Questions

**Good questions:**
- "What's the expected input size?" → determines if O(n²) is acceptable
- "Can I modify the input?" → in-place vs extra space
- "What should I return for edge cases?" → empty input, no solution
- "Are there duplicates in the input?" → affects algorithm choice
- "Is the data sorted?" → enables binary search

**Don't ask:**
- "What's the answer?" → you're supposed to solve it
- "Can I use library X?" → just use it, mention it

### Handling Silence

- **Thinking pause**: "Let me think about this for a moment..." (10-30 seconds is fine)
- **Stuck**: "I'm stuck on [specific part]. Can I think about it from [alternative angle]?"
- **Need a hint**: "I've considered [X and Y]. Am I on the right track, or should I explore a different direction?"

### Admitting What You Don't Know

**Honest > Bluffing:**

```
❌ "Yes, I'm familiar with that." (then struggle)

✅ "I haven't worked with [technology] directly, but I understand 
    the concept is similar to [something you know]. The key 
    principles would be..."
```

**Framework for "I don't know":**
1. Acknowledge: "I'm not deeply familiar with X"
2. Connect: "But based on my understanding of Y..."
3. Reason: "I would expect it works like Z because..."
4. Learn: "I'd be interested to learn more about how..."

### Whiteboard Communication

- **Draw before coding** — Architecture, data flow, state machine
- **Use the board** — Write key observations, complexity analysis
- **Point while explaining** — "This loop iterates through the array..."
- **Leave space** — Room for corrections and additions

### System Design Communication

1. **Requirements first** — Functional + non-functional (5 min)
2. **High-level design** — Boxes and arrows (10 min)
3. **Deep dive** — Pick 2-3 components (15 min)
4. **Trade-offs** — Why this choice over alternatives (5 min)
5. **Scaling** — How it handles 10x/100x load (5 min)

## Common Communication Mistakes

| Mistake | Fix |
|---|---|
| Jumping to code immediately | Clarify and plan first |
| Silent coding | Think aloud |
| Ignoring the interviewer's hints | Listen and adapt |
| Defending your approach blindly | Consider alternatives |
| Saying "I don't know" and stopping | Reason about it |
| Over-explaining trivial parts | Focus on the interesting parts |
| Not asking questions | Always clarify before coding |

## Interview Questions

**Q: How do you handle a problem you've never seen before?**
A: (1) Break it into smaller subproblems, (2) identify similar problems I've solved, (3) start with brute force, (4) look for patterns (sorted? → binary search; graph? → BFS/DFS), (5) think about data structures that help, (6) communicate my thinking to get hints.

**Q: How do you communicate when you're stuck?**
A: (1) State what I've tried and why it didn't work, (2) explain what I'm uncertain about, (3) propose alternative approaches, (4) ask if I'm on the right track. The interviewer wants to help — give them something to work with.

## References

- [Cracking the Coding Interview — Gayle Laakmann McDowell](https://www.crackingthecodinginterview.com/)
- [Interviewing.io — Mock interviews](https://interviewing.io/)
- [Exponent — System design interview prep](https://www.tryexponent.com/)
