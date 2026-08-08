# Prompt Engineering

## Overview

Prompt engineering is the art and science of crafting inputs to LLMs to get desired outputs. Since LLMs are instruction-following systems, how you ask determines what you get. For placement interviews, prompt engineering shows you understand LLM behavior and can use them effectively.

## Prompting Techniques

```mermaid
graph TD
    PE[Prompt Engineering]
    PE --> BASIC[Basic]
    PE --> ADVANCED[Advanced]
    PE --> STRUCTURED[Structured]

    BASIC --> ZS[Zero-Shot]
    BASIC --> FS[Few-Shot]

    ADVANCED --> COT[Chain-of-Thought]
    ADVANCED --> SC[Self-Consistency]
    ADVANCED --> TOT[Tree-of-Thought]

    STRUCTURED --> SYS[System Prompts]
    STRUCTURED --> XML[XML/Markdown Templates]
    STRUCTURED --> FUNC[Function Calling]
```

## Zero-Shot Prompting

The simplest approach — give the model a task with no examples:

```
Classify the sentiment of the following review as positive, negative, or neutral:
"The food was amazing but the service was terrible."
```

**When it works:** Simple tasks where the model has seen similar patterns during pre-training.

**When it fails:** Complex tasks, specific output formats, domain-specific terminology.

## Few-Shot Prompting

Provide examples before the task:

```
Classify the sentiment:

Review: "I loved every minute of it!" → Positive
Review: "Waste of money and time." → Negative
Review: "It was okay, nothing special." → Neutral

Review: "The food was amazing but the service was terrible." →
```

**Key principles:**
- Examples should be diverse and representative
- Order matters (put the most similar example last)
- 3-5 examples is usually optimal
- Match the format you want in the output

```mermaid
graph LR
    E1[Example 1] --> PROMPT[Prompt Construction]
    E2[Example 2] --> PROMPT
    E3[Example 3] --> PROMPT
    TASK[Task Input] --> PROMPT
    PROMPT --> MODEL[LLM]
    MODEL --> OUTPUT[Structured Output]
```

## Chain-of-Thought (CoT) Prompting

Encourage the model to reason step-by-step before answering.

### Few-Shot CoT

```
Q: Roger has 5 tennis balls. He buys 2 more cans of tennis balls. Each can has 3 tennis balls. How many tennis balls does he have now?
A: Roger started with 5 balls. 2 cans of 3 balls each is 2 × 3 = 6 balls. 5 + 6 = 11. The answer is 11.

Q: The cafeteria had 23 apples. They used 20 for lunch and bought 6 more. How many apples do they have?
A:
```

### Zero-Shot CoT

Simply append "Let's think step by step" or "Think carefully before answering":

```
Q: If a train travels 60 mph for 2.5 hours, how far does it go?
A: Let's think step by step.
```

**Why CoT works:**
- Breaks complex problems into manageable steps
- Allows the model to use intermediate computations
- Reduces errors on multi-step reasoning
- Provides transparency into the model's reasoning

```mermaid
graph TD
    Q[Question] --> COT["Let's think step by step"]
    COT --> S1[Step 1: Identify what we know]
    S1 --> S2[Step 2: Break into sub-problems]
    S2 --> S3[Step 3: Solve each sub-problem]
    S3 --> S4[Step 4: Combine results]
    S4 --> ANS[Final Answer]
```

### CoT Variants

| Technique | Description | Use Case |
|---|---|---|
| **Zero-shot CoT** | "Let's think step by step" | General reasoning |
| **Few-shot CoT** | Examples with reasoning chains | Math, logic |
| **Auto-CoT** | Model generates its own examples | When you lack examples |
| **Self-Consistency** | Sample multiple CoT paths, majority vote | High-stakes reasoning |
| **Tree-of-Thought** | Explore multiple reasoning branches | Complex problems |

## Self-Consistency

Instead of one answer, sample multiple reasoning paths and take the majority vote:

```mermaid
graph TD
    Q[Question] --> PATH1[Reasoning Path 1]
    Q --> PATH2[Reasoning Path 2]
    Q --> PATH3[Reasoning Path 3]
    PATH1 --> A1[Answer: 42]
    PATH2 --> A2[Answer: 42]
    PATH3 --> A3[Answer: 38]
    A1 --> VOTE[Majority Vote]
    A2 --> VOTE
    A3 --> VOTE
    VOTE --> FINAL[Final: 42]
```

**Why it works:** Different reasoning paths may make different mistakes. The correct answer is more likely to appear across multiple paths.

**Trade-off:** More samples = better accuracy but higher cost and latency.

## System Prompts

System prompts set the model's behavior, persona, and constraints:

```
You are an expert Python developer specializing in data engineering.
You always:
- Write clean, well-documented code
- Include type hints
- Handle edge cases
- Suggest improvements

You never:
- Use deprecated APIs
- Write code without error handling
- Assume the user knows advanced concepts without explanation
```

### System Prompt Best Practices

| Element | Example |
|---|---|
| **Role** | "You are a senior data engineer at a Fortune 500 company" |
| **Constraints** | "Only respond in JSON format" |
| **Style** | "Be concise. Use bullet points." |
| **Knowledge** | "You have expertise in Python, SQL, and Spark" |
| **Boundaries** | "If you don't know, say 'I don't know' rather than guessing" |

## Structured Output Prompts

### JSON Mode

```
Extract the following information from the text and return as JSON:
- name (string)
- age (integer)
- occupation (string)
- skills (array of strings)

Text: "John is a 35-year-old data scientist who knows Python, SQL, and TensorFlow."
```

Expected output:
```json
{
  "name": "John",
  "age": 35,
  "occupation": "data scientist",
  "skills": ["Python", "SQL", "TensorFlow"]
}
```

### XML Tags for Structure

```
<instructions>
Summarize the article in 3 bullet points.
Each bullet should be one sentence.
</instructions>

<article>
{article text}
</article>

<output_format>
- Bullet 1
- Bullet 2
- Bullet 3
</output_format>
```

## Advanced Techniques

### Role Prompting

```
Act as a senior DevOps engineer reviewing a production incident.
The application is a Python Flask API running on Kubernetes.
The error is: "OOMKilled" in pod logs.
```

### Negative Prompting

Tell the model what NOT to do:
```
Explain Docker to a beginner.
Do NOT:
- Use jargon without explaining it
- Assume they know Linux
- Write more than 200 words
```

### Prompt Chaining

Break complex tasks into sequential prompts:

```mermaid
graph LR
    P1["Prompt 1: Extract key facts"] --> R1[Facts]
    R1 --> P2["Prompt 2: Analyze facts"]
    R2[Analysis] --> P3["Prompt 3: Generate recommendation"]
    P2 --> R2
    P3 --> FINAL[Final Output]
```

### Meta-Prompting

Ask the model to improve your prompt:
```
I want to get the model to generate Python unit tests.
My current prompt is: "Write tests for this function."
How can I improve this prompt to get better test coverage?
```

## Common Prompt Patterns

### The CRISPE Framework

| Component | Description | Example |
|---|---|---|
| **C**apacity | Role/persona | "You are a Python expert" |
| **R**equest | Task description | "Write a function that..." |
| **I**nsight | Context/background | "The function will be used in..." |
| **S**tyle | Output format | "Use Google-style docstrings" |
| **P**ersonality | Tone | "Be direct and technical" |
| **E**xperiment | Iterate | "Provide 3 alternatives" |

### ReAct Pattern (for Agents)

```
Question: What is the population of the capital of France?

Thought: I need to find the capital of France first.
Action: Search("capital of France")
Observation: Paris is the capital of France.
Thought: Now I need to find Paris's population.
Action: Search("population of Paris 2024")
Observation: Paris has approximately 2.1 million people.
Thought: I have the answer.
Answer: The population of Paris (capital of France) is approximately 2.1 million.
```

## Interview Questions

### Q1: What is Chain-of-Thought prompting and why does it work?
**Answer:** CoT prompting encourages the model to show intermediate reasoning steps before giving a final answer. It works because:
1. It decomposes complex problems into simpler sub-problems
2. Each step can be verified independently
3. It allows the model to use intermediate "scratchpad" computations
4. It reduces errors on multi-step reasoning tasks (math, logic, code)

Zero-shot CoT ("Let's think step by step") is simple but effective. Few-shot CoT (providing examples with reasoning chains) is more reliable for complex tasks.

### Q2: How do you choose between zero-shot, few-shot, and CoT prompting?
**Answer:**
- **Zero-shot**: Simple tasks the model has seen during training (classification, translation)
- **Few-shot**: Tasks requiring specific format or domain knowledge; 3-5 diverse examples
- **CoT**: Multi-step reasoning (math, logic, planning); use few-shot CoT for reliability
- **Self-Consistency**: High-stakes reasoning where accuracy matters more than cost
- **Rule of thumb**: Start with zero-shot. If quality is low, try few-shot. If reasoning is needed, add CoT.

### Q3: What makes a good system prompt?
**Answer:** A good system prompt defines:
1. **Role**: Who the model is ("You are a senior Python developer")
2. **Constraints**: What to do/not do ("Always include error handling")
3. **Output format**: How to respond ("Return valid JSON")
4. **Tone**: How to communicate ("Be concise and technical")
5. **Knowledge boundaries**: What the model knows/don't know ("If unsure, say 'I don't know'")

Bad system prompts are vague ("Be helpful"). Good ones are specific and actionable.

### Q4: What is self-consistency and when should you use it?
**Answer:** Self-consistency samples multiple reasoning paths for the same question and takes the majority vote of the final answers. It works because different paths may make different mistakes, but the correct answer is more likely to appear consistently. Use it when:
- Accuracy is critical (medical, legal, financial)
- The task involves multi-step reasoning
- You can afford the extra cost/latency (typically 3-5x)
- Single-path CoT is unreliable

## Common Mistakes

- ❌ Vague prompts ("Tell me about Python" → too broad)
- ❌ No output format specification (model may return paragraphs when you want JSON)
- ❌ Too many examples in few-shot (confuses the model, wastes context window)
- ❌ Not testing prompts across different inputs (edge cases)
- ❌ Ignoring token limits (prompt + output must fit in context window)
- ❌ Assuming the model "understands" — it follows patterns, not instructions literally

## Summary

Prompt engineering is the primary interface for using LLMs. Techniques range from simple zero-shot to advanced CoT and self-consistency. System prompts set behavior, few-shot examples teach format, and CoT enables reasoning. The key is matching the technique to the task complexity and iterating based on results.

## Cross-References

- [Chain-of-Thought →](../../ml/agents/chain-of-thought.md) Detailed CoT techniques
- [ReAct →](../../ml/agents/react.md) Reasoning + Acting pattern
- [RAG →](rag.md) Augmenting prompts with retrieved context
- [SFT →](sft.md) How models learn to follow prompts
- [Tool Calling →](../../ml/agents/tool-calling.md) Function calling with prompts
