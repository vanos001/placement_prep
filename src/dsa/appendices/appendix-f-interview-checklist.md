# Appendix F: Interview Checklist

A comprehensive checklist to maximize your performance in technical interviews.

---

## Pre-Interview Checklist

### 1 Week Before

- [ ] Review the company's interview format (number of rounds, duration, focus areas)
- [ ] Research the company's products, culture, and recent news
- [ ] Review your resume thoroughly — be ready to discuss anything on it
- [ ] Prepare a 2-minute "tell me about yourself" pitch
- [ ] Review the most common DSA topics for this company (see Appendix M)
- [ ] Do 2-3 mock interviews with a friend or on platforms like Pramp/Interviewing.io
- [ ] Review your past projects and prepare STAR-format stories

### 1 Day Before

- [ ] Get a good night's sleep (7-8 hours)
- [ ] Prepare your environment:
  - [ ] Quiet room with no distractions
  - [ ] Stable internet connection
  - [ ] Backup internet (phone hotspot)
  - [ ] Charged laptop
  - [ ] Pen and paper/whiteboard
  - [ ] Water bottle
- [ ] Review your cheat sheet (data structure operations, complexities)
- [ ] Do 1-2 easy problems to warm up (don't try to learn new material)
- [ ] Prepare questions to ask the interviewer
- [ ] Set multiple alarms

### Day of Interview

- [ ] Eat a proper meal (not too heavy)
- [ ] Arrive/log in 10-15 minutes early
- [ ] Have your ID ready (if in-person)
- [ ] Test your microphone and camera (if virtual)
- [ ] Close unnecessary applications
- [ ] Have a glass of water nearby
- [ ] Take a few deep breaths to calm nerves
- [ ] Review your "tell me about yourself" one last time

---

## During-Interview Checklist

### Phase 1: Problem Understanding (2-3 minutes)

- [ ] **Listen carefully** — don't start coding immediately
- [ ] **Take notes** — write down the problem constraints
- [ ] **Ask clarifying questions:**
  - What are the input constraints? (size, range, type)
  - Can the input be empty?
  - Are there duplicate elements?
  - Is the array sorted?
  - What should I return if no solution exists?
  - Can I use extra space?
  - What's the expected time complexity?
- [ ] **Paraphrase the problem** back to the interviewer
- [ ] **Identify the problem type:**
  - Array/String manipulation?
  - Tree/Graph traversal?
  - Dynamic programming?
  - Binary search?
  - Sliding window/Two pointers?
  - Stack/Queue?

### Phase 2: Example and Edge Cases (1-2 minutes)

- [ ] Walk through 1-2 examples manually
- [ ] Identify edge cases:
  - Empty input (null, empty array, empty string)
  - Single element
  - Two elements
  - All same elements
  - Negative numbers
  - Very large numbers (overflow?)
  - Already sorted/reverse sorted
- [ ] Verify your understanding with the interviewer

### Phase 3: Approach Discussion (3-5 minutes)

- [ ] **Start with brute force** — mention it explicitly
  - "The brute force approach would be O(n²) by checking all pairs..."
- [ ] **Identify bottlenecks** — why is brute force slow?
- [ ] **Propose optimization:**
  - "I notice we're doing redundant work..."
  - "We can use a hash map to avoid the inner loop..."
  - "Since the array is sorted, we can use binary search..."
- [ ] **Discuss trade-offs:**
  - Time vs space complexity
  - Code complexity vs performance
- [ ] **Get buy-in** before coding:
  - "Does this approach sound reasonable?"
  - "I'm thinking of using a trie — does that make sense here?"

### Phase 4: Coding (10-15 minutes)

- [ ] **Write clean, readable code:**
  - Meaningful variable names (not single letters except loop counters)
  - Consistent indentation
  - Comments for complex logic
- [ ] **Talk while coding** — explain your thought process
- [ ] **Handle edge cases** explicitly
- [ ] **Use STL** when appropriate (don't reinvent the wheel)
- [ ] **Common pitfalls to avoid:**
  - Off-by-one errors
  - Integer overflow
  - Null pointer access
  - Missing visited array
  - Wrong comparator

### Phase 5: Testing (3-5 minutes)

- [ ] **Trace through your code** with the examples
- [ ] **Test edge cases:**
  - Empty input
  - Single element
  - Maximum size input
- [ ] **Check for bugs:**
  - Are all variables initialized?
  - Are all loops bounded?
  - Are all pointers checked?
  - Is the return value correct?
- [ ] **Fix any bugs** you find — don't panic

### Phase 6: Complexity Analysis (1-2 minutes)

- [ ] State the time complexity and explain why
- [ ] State the space complexity and explain why
- [ ] Mention if there's a better approach (if you know one)

### Phase 7: Follow-up Questions

- [ ] Be ready for follow-ups:
  - "What if the input is too large to fit in memory?"
  - "What if we need to handle concurrent access?"
  - "Can you optimize further?"
  - "What if we need to support updates?"
- [ ] If you don't know, say so honestly:
  - "I'm not sure about that, but my initial thought would be..."

### Behavioral Questions

- [ ] Use the **STAR method:**
  - **S**ituation: Set the context
  - **T**ask: What was your responsibility?
  - **A**ction: What did you do?
  - **R**esult: What was the outcome?
- [ ] Prepare stories for:
  - A challenging technical problem you solved
  - A time you disagreed with a teammate
  - A time you failed and what you learned
  - A time you showed leadership
  - A project you're proud of
- [ ] Be specific — use numbers and details
- [ ] Be honest — don't exaggerate

### Questions to Ask the Interviewer

Prepare 3-5 questions. Good ones include:

- [ ] "What does a typical day look like for someone in this role?"
- [ ] "What are the biggest challenges the team is facing right now?"
- [ ] "How do you measure success for this role?"
- [ ] "What's the team culture like?"
- [ ] "What opportunities are there for growth and learning?"
- [ ] "What's the tech stack?"
- [ ] "How does the team handle code reviews?"

Avoid asking about salary, benefits, or vacation in the technical round.

---

## Post-Interview Checklist

### Immediately After

- [ ] Write down the questions you were asked
- [ ] Write down your solutions and any follow-ups
- [ ] Note what went well and what could be improved
- [ ] Note any topics you need to review

### Within 24 Hours

- [ ] Send a thank-you email to the recruiter (and interviewer if appropriate)
- [ ] Review the questions and solve them again if needed
- [ ] Update your study plan based on gaps you identified

### If You Get an Offer

- [ ] Don't accept immediately — take time to evaluate
- [ ] Research the compensation range for the role
- [ ] Consider the full package (base, bonus, equity, benefits)
- [ ] Negotiate — it's expected and normal
- [ ] Ask for the offer in writing

### If You Don't Get an Offer

- [ ] Ask for feedback (politely)
- [ ] Don't take it personally — interviews are partly luck
- [ ] Review what went wrong and improve
- [ ] Apply again in 6-12 months (most companies allow this)
- [ ] Keep practicing — every interview makes you better

---

## Interview Day Mental Checklist

### Before Each Question
- Take a breath
- Clear your mind
- Focus on the problem

### When Stuck
- [ ] Don't panic — it's normal to get stuck
- [ ] Go back to examples
- [ ] Think about simpler versions of the problem
- [ ] Consider different data structures
- [ ] Ask the interviewer for a hint (it's okay!)

### Time Management
- Spend ~2 min understanding the problem
- Spend ~1-2 min on examples and edge cases
- Spend ~3-5 min discussing the approach
- Spend ~10-15 min coding
- Spend ~3-5 min testing
- Spend ~2 min on complexity analysis

### Communication Tips
- Think out loud
- Explain your reasoning before coding
- If you're stuck, say what you're thinking
- Don't go silent for more than 30 seconds
- It's okay to say "let me think about this for a moment"
- Ask for clarification if anything is unclear

---

## Red Flags to Avoid

- [ ] Jumping into code without understanding the problem
- [ ] Not asking any clarifying questions
- [ ] Going silent for long periods
- [ ] Refusing to consider hints from the interviewer
- [ ] Being defensive about your approach
- [ ] Not testing your code
- [ ] Giving up too easily
- [ ] Overcomplicating the solution
- [ ] Not knowing the basics of your language
- [ ] Lying about your experience or skills

---

## Green Flags to Aim For

- [ ] Clear communication throughout
- [ ] Systematic problem-solving approach
- [ ] Considering multiple approaches
- [ ] Writing clean, readable code
- [ ] Testing thoroughly
- [ ] Handling edge cases
- [ ] Knowing the complexity of your solution
- [ ] Being open to feedback and hints
- [ ] Showing genuine enthusiasm for the problem
- [ ] Asking thoughtful questions

---

*Print this checklist and review it before every interview. Over time, these habits will become second nature.*
