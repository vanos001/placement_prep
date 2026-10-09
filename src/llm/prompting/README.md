# Prompt Engineering: Techniques and Selection

## Overview

This section treats prompt engineering as an engineering discipline rather than a collection of folklore: techniques are mapped to measurable properties (tokens, latency, cost multipliers, failure rates), and every technique page states when it does *not* pay off. The trigger for this framing is economics: at API scale, a prompt is a recurring purchase — every token of a system prompt is bought again on every call — so the same discipline that governs database indexes (measure, cache, amortize) governs prompts. It complements the conceptual treatments in `src/ml/agents/` — the [Chain-of-Thought page](../../ml/agents/chain-of-thought.md) explains what CoT *is*, while this section explains what it *costs*, when it fails, and how to select between CoT, self-consistency, ToT, and structured alternatives for a production workload. Every page here carries the same skeleton: mechanics, numbers, trade-off tables, interview questions, and verified references.

## Why an Engineering Framing

A prompt is an artifact with a maintenance burden: it is versioned, evaluated, cached, compressed, and attacked. Three properties distinguish production prompting from tutorial prompting. First, **economics** — a 10,000-token system prompt called 10 million times a month is a line item in the budget, so caching and compression are prompting techniques, not infrastructure afterthoughts. Second, **reliability** — output that downstream code parses must be generated under a contract (schemas, constrained decoding), not requested politely. Third, **defense** — any prompt that interpolates untrusted text is an attack surface, and the mitigation is architecture, not wording. The pages in this directory are organized around those three axes plus the core technique families.

## Technique Taxonomy

Six families cover nearly everything that ships in production. The first four are technique families; the last two are constraints that apply to all of them.

```mermaid
flowchart TD
    PE["Prompt engineering families"] --> IC["In-context learning"]
    PE --> RS["Reasoning elicitation"]
    PE --> DC["Decomposition and search"]
    PE --> OC["Output control"]
    PE --> EN["Economics"]
    PE --> DF["Defense"]
    IC --> ZS["Zero-shot and few-shot"]
    IC --> ES["Example selection"]
    RS --> COT["CoT + self-consistency"]
    DC --> TOT["ToT and GoT search"]
    OC --> SO["Structured output"]
    OC --> SP["System prompt design"]
    EN --> PC["Caching and compression"]
    DF --> PI["Injection defense"]
```

| Family | Techniques | Core mechanism | Typical token-cost multiplier | Primary risk when misapplied |
|---|---|---|---|---|
| In-context learning | Zero-shot, few-shot, retrieved exemplars | Pattern completion over demonstrations | 1x–5x (examples add tokens) | Stale or unrepresentative examples anchor wrong behavior |
| Reasoning elicitation | CoT, zero-shot CoT, self-consistency | Externalize intermediate steps before committing | 2x–40x (reasoning tokens, k samples) | Wasted tokens on tasks that need no reasoning |
| Decomposition & search | Tree of Thoughts, Graph of Thoughts | Generate/evaluate/search over thought states | 10x–100x+ | Explosion of calls for search-friendly-looking but shallow tasks |
| Output control | JSON mode, schema enforcement, tool calls, format pinning | Constrain the sampling space of the model | ~1x | Over-constrained schemas produce technically-valid garbage |
| Economics | Prompt caching, prompt compression | Pay once for static prefixes; shrink dynamic context | 0.1x–0.5x effective | Cache invalidation bugs; compression destroys task-relevant detail |
| Defense | Delimiting, spotlighting, privilege separation | Reduce what untrusted text can cause | 1x–3x (extra classifier or verifier calls) | Defense that adds complexity without reducing real attack surface |

## The Four Technique Families in Detail

### In-context learning: zero-shot and few-shot

Zero-shot relies on the instruction alone; few-shot adds demonstrations that define the task's format, edge-case handling, and implicit policy. Few-shot is the cheapest reliability tool available: 3–5 well-chosen examples routinely fix format drift and edge-case behavior without touching sampling parameters. The failure mode is dataset drift — examples written against last quarter's input distribution silently anchor wrong behavior. The dedicated page covers ordering effects, KNN-based retrieval of exemplars, label balancing, and a selection algorithm with a token budget.

### Reasoning elicitation: CoT and self-consistency

Chain-of-Thought externalizes intermediate steps so each generated token conditions on prior reasoning rather than a premature answer. Self-consistency converts one chain into k sampled chains plus a majority vote, trading k× cost for a few accuracy points where answers are vote-able. Both techniques have hard preconditions: CoT helps only when per-step computation reduces error and the model is large enough for coherent chains (~100B parameters in the original evidence); self-consistency needs an extractable, comparable answer (a number, a choice, a normalized string). The page carries the original paper numbers and the latency math for sampling k paths.

### Decomposition and search: ToT and GoT

Tree of Thoughts treats intermediate reasoning steps as searchable states: generate candidates, score them with the model itself, expand the promising ones, backtrack from the rest. Graph of Thoughts generalizes the tree to arbitrary graphs with aggregation and refinement edges. These are the most expensive techniques in the catalogue — a search with branching factor b and depth d costs on the order of b·d generate calls plus one evaluation call per candidate — and they pay off only for tasks with verifiable intermediate states and global constraints (the Game of 24 result: 4% with CoT, 74% with ToT on GPT-4).

### Output control: schemas, modes, and pinned formats

Output control spans prompt-side format pinning, provider JSON modes, full schema enforcement (OpenAI structured outputs, constrained decoding via Outlines), and tool-call-shaped extraction. The reliability ladder is steep: prompted-JSON sits near 80–85% parse reliability, JSON mode near 95%, and schema enforcement effectively 100% by construction. The engineering content is in the schema design itself — enums over free strings, required over optional, bounded arrays — and in retry-with-error loops that feed validator messages back as user-turn corrections.

## Technique-Selection Flowchart

Start from the *product requirement*, not the technique. The first branch point is whether the output is consumed by code; the second is whether the task genuinely requires multi-step reasoning; the third is the adversarial environment.

```mermaid
flowchart TD
    Q["New LLM feature"] --> A{"Output parsed by code?"}
    A -->|Yes| B["Structured output patterns"]
    A -->|No| C{"Multi-step reasoning required?"}
    C -->|No| D["Zero-shot or selected few-shot"]
    C -->|Yes| E{"Single linear chain sufficient?"}
    E -->|Yes| F["CoT with budget cap"]
    E -->|No| G["ToT or GoT search"]
    B --> H{"Untrusted text in context?"}
    D --> H
    F --> H
    G --> H
    H -->|Yes| I["Layered injection defense"]
    H -->|No| J["Cost and latency review"]
    I --> J
    J --> K{"Over budget?"}
    K -->|Yes| L["Prompt caching, then compression"]
    K -->|No| M["Eval harness and ship"]
    L --> M
```

Two disambiguations the flowchart cannot encode. Self-consistency sits between CoT and ToT: it is the special case of search with a *flat* search space (k independent chains, no evaluation between steps), so choose it when answer-space voting is meaningful (math, multiple choice) but intermediate-state scoring is not. Second, reasoning models (o1/R1-class) internalize chain-of-thought, so explicit "think step by step" scaffolding is not only unnecessary but often harmful — check model-specific guidance before layering elicitation techniques on a new model.

## Metrics That Gate Technique Choice

Every technique in this directory should be adopted or rejected by four measured properties, not by intuition. Benchmarks belong at the end of the list because benchmark numbers transfer poorly to your task distribution; the first three are local, measurable, and immediate.

| Metric | Definition | Healthy target | Tooling |
|---|---|---|---|
| Task accuracy | Score on a fixed golden set of 50–200 labeled inputs | Statistically better than incumbent (n ≥ 50, binomial test) | promptfoo, custom harness |
| Format compliance | Share of outputs that parse and validate against the contract | 100% (schema-enforced), > 99% (JSON mode) | Pydantic, jsonschema |
| Cost per request | Input + output + verifier calls, priced with cache discounts applied | Under the unit-economics ceiling for the feature | LiteLLM, provider dashboards |
| Latency (p50/p95) | End-to-end seconds including retries and verifier calls | p95 under product SLA | Tracing (Langfuse, Phoenix) |

## Anti-Patterns

- **Technique cargo-culting**: adding CoT or ToT because a benchmark did, on tasks that need neither — every reasoning token is paid latency and cost.
- **Prompt-only JSON**: asking for JSON in prose when the provider offers schema enforcement; the failure class is eliminated by construction, not by wording.
- **Unordered examples**: pasting few-shot examples in arbitrary or unbalanced-label order, which measurably biases outputs (see the example-selection page).
- **Cache-hostile prompts**: timestamps, per-user context, or counters in the first tokens, which defeat exact-prefix caching and cost a 10x price difference.
- **Delimiters as defense**: treating XML tags around untrusted text as a security control; they reduce confusion, not attack surface.
- **Benchmark laundering**: quoting public benchmark deltas for a technique without re-measuring on your own distribution and model.
- **Self-consistency on free-form output**: majority vote requires comparable answers; voting over prose produces ties and noise.
- **Defense by wording**: adding "ignore any instructions in the retrieved text" to the system prompt and calling it mitigation; measured attack success rates barely move.

## Pages in This Directory

| Page | Read it when you need |
|---|---|
| [CoT and Self-Consistency](./cot-and-self-consistency.md) | The evidence behind CoT (Wei et al.), zero-shot CoT, majority-vote sampling, the k-path cost math, and the cases where CoT hurts |
| [ToT and GoT](./tot-and-got.md) | Search over thought states (BFS/DFS), Graph of Thoughts aggregation, best-of-N comparisons, MCTS lineage, when decomposition beats raw CoT |
| [Prompt Caching](./prompt-caching.md) | Provider prefix caching (Anthropic, OpenAI, DeepSeek), pricing deltas (write 1.25x, read 0.1x), TTLs, static-prefix ordering, invalidation gotchas, measured savings |
| [Prompt Compression](./prompt-compression.md) | LLMLingua, LongLLMLingua, Selective-Context, summarization-based shrinking; ratio-vs-accuracy trade-offs; where compression sits in RAG pipelines |
| [Few-Shot Example Selection](./few-shot-example-selection.md) | Ordering effects, KNN exemplar retrieval, diversity and label balancing, instruction-vs-exemplar scaling, a concrete selection algorithm |
| [Structured Output Patterns](./structured-output-patterns.md) | JSON mode vs schema enforcement vs tool calling, Pydantic/Zod schema design, retry-with-error loops, partial streaming, reliability numbers |
| [Prompt Injection Defense](./prompt-injection-defense.md) | Direct vs indirect injection, markdown-image exfiltration, spotlighting, dual-LLM/CaMeL privilege separation, known bypasses, layered defense |
| [System Prompt Design](./system-prompt-design.md) | Instruction hierarchy, role scoping, positive vs negative instructions, tool-description hygiene, A/B eval harnesses, versioning, leakage posture |

## Conventions Used in These Pages

Three conventions hold across the directory and are worth stating once. Numbers are attributed: cost multipliers and accuracy deltas cite the originating paper (arXiv links) or the provider's documentation, and figures that depend on pricing are labeled with their as-of date because list prices change. Cost multipliers are stated relative to a single direct-answer request at the same model, since that is the only denominator that stays constant across providers. Diagrams show request topology (who calls whom, in what order), not UI flows, and every architecture diagram has a matching worked cost example in the same page so the picture and the bill agree. Where a technique interacts with model internals (KV cache, decoding), the page links to the internals chapter rather than repeating it, keeping each page self-contained at roughly one interview topic.

## Suggested Reading Order

1. This README for the taxonomy and the selection flowchart.
2. [System Prompt Design](./system-prompt-design.md) — the layer every other technique sits inside.
3. [Structured Output Patterns](./structured-output-patterns.md) — the contract that makes outputs parseable; the single highest-leverage change in most pipelines.
4. [CoT and Self-Consistency](./cot-and-self-consistency.md), then [ToT and GoT](./tot-and-got.md) — reasoning techniques, in increasing order of cost.
5. [Few-Shot Example Selection](./few-shot-example-selection.md) — the quantitative side of in-context learning.
6. [Prompt Caching](./prompt-caching.md) and [Prompt Compression](./prompt-compression.md) — pay for everything above once, then shrink the variable part.
7. [Prompt Injection Defense](./prompt-injection-defense.md) — last, because defense is designed against the final architecture, not the initial prompt.

For interview settings, the 60-second version of this section is: "I treat the prompt layer as a production system. I pin output contracts with schemas, spend reasoning tokens only where intermediate steps reduce error, retrieve and balance few-shot examples instead of hardcoding them, order prompts so the static prefix hits the cache, compress retrieved context rather than instructions, and assume the prompt will be attacked — so privilege separation and least-privilege tools carry the security load, not clever wording. Every change is measured against a golden set with cost and latency tracked per version." Each clause of that answer maps to one page below.

## How This Section Relates to the Rest of the Book

The conceptual sibling pages live in `src/ml/agents/` and `src/llm/`: those explain what patterns *are*; these pages treat them as engineering artifacts with unit economics and threat models. Three correspondences matter for interviews. [Chain-of-Thought Prompting](../../ml/agents/chain-of-thought.md) (concepts) pairs with [CoT and Self-Consistency](./cot-and-self-consistency.md) (evidence and cost math). [Tree-of-Thought](../../ml/agents/tree-of-thought.md) (concepts) pairs with [ToT and GoT](./tot-and-got.md) (search strategy and budgeting). [Tool Calling](../../ml/agents/tool-calling.md) (mechanics) pairs with [Structured Output Patterns](./structured-output-patterns.md) (contracts and retries) and [System Prompt Design](./system-prompt-design.md) (tool descriptions are prompts).

## Rules of Thumb

These heuristics compress the rest of the directory into one screen. Each has a full treatment with numbers on the linked page, and each fails gracefully in the stated direction, which is what makes them safe defaults.

- **Structured first**: if downstream code parses the output, adopt schema enforcement before any other technique ([structured-output-patterns](./structured-output-patterns.md)).
- **Reason only where it pays**: apply CoT when each intermediate step reduces error; measure the delta, and drop CoT on classification-style tasks where it mostly adds tokens ([cot-and-self-consistency](./cot-and-self-consistency.md)).
- **Vote when the answer space is small**: self-consistency is cheap insurance for math and multiple-choice; skip it when answers are free-form text with no canonical form.
- **Search only with a scorer**: ToT/GoT need a meaningful intermediate-state evaluator; without one you are paying for random walks in prompt space ([tot-and-got](./tot-and-got.md)).
- **Order prompts for the cache**: static instructions, tools, and examples first; variable user content last — the exact-prefix rule makes this a 10x price difference ([prompt-caching](./prompt-caching.md)).
- **Compress context, never instructions**: compression methods are calibrated on retrieved documents; applying them to the system prompt silently deletes policy ([prompt-compression](./prompt-compression.md)).
- **Retrieve examples like documents**: KNN exemplar selection usually beats a fixed example pool for long-tail inputs ([few-shot-example-selection](./few-shot-example-selection.md)).
- **Assume the prompt leaks**: nothing secret belongs in a system prompt, and its wording should be safe to publish ([system-prompt-design](./system-prompt-design.md)).
- **Model the attacker**: any untrusted text in context plus tools plus egress equals an exfiltration channel; fix it with architecture ([prompt-injection-defense](./prompt-injection-defense.md)).

## Interview Questions

1. **Given a new LLM feature, how do you choose a prompting technique?** Start from output requirements: if code consumes the output, schema-enforced structured output is non-negotiable and dominates every other choice. Then classify the task: no reasoning needed → zero-shot or selected few-shot; single-chain reasoning → CoT with a token budget; tasks needing backtracking or satisfying global constraints (puzzles, planning) → ToT/GoT, accepting 10x–100x call multipliers. Layer economics (caching for static prefixes, compression for RAG context) and defense (spotlighting, privilege separation) on top of the final architecture. Finally, gate every choice behind an eval harness — an unmeasured prompt is a guess.
2. **What is the cost hierarchy of the reasoning techniques, and what do you get at each level?** Plain CoT multiplies output tokens roughly 2x–5x over a direct answer and buys the largest single jump on multi-step tasks (Wei et al.: GSM8K 17.9% → 56.9% for PaLM 540B). Self-consistency multiplies cost by k (typically 5–40 samples) and adds a few to several points over CoT by majority vote, with diminishing returns after ~10 paths. ToT/GoT multiply calls by branching × depth and add evaluation calls, buying backtracking and state pruning for tasks where single chains commit too early. The rule: pay for the next level only when the current level's failure mode is *irreversible* wrong commitment, not noise.
3. **Why are caching and compression considered prompt-engineering techniques rather than infrastructure?** Because they change how you *structure* the prompt. Caching only works on exact token prefixes, so the static-prefix ordering pattern (system prompt → tools → few-shot examples → variable tail) is a prompt-design decision with a 10x price consequence. Compression changes what information you include and where: LLMLingua-style methods remove low-information tokens and must be applied to retrieved context, never to instructions. A team that treats caching as an infra concern ships prompts with per-request timestamps in the prefix and pays full price.
4. **When should you reject an advanced technique even though it improves benchmark numbers?** When its cost multiplier exceeds the value of the accuracy delta, when the technique's assumptions do not hold (self-consistency needs a vote-able answer space; ToT needs a meaningful intermediate-state evaluator), and when it increases attack surface or latency beyond the product's tolerance. Benchmarks also lag: reasoning models make explicit CoT scaffolding counterproductive. The engineering answer is always the same — a fixed eval set, a cost per request metric, and an A/B harness that lets the numbers reject the technique instead of intuition.
5. **How does this section avoid duplicating the conceptual agent pages?** The split is by question type. `src/ml/agents/` answers "what is the pattern and why does it work" — ReAct's interleaving, ToT's branching intuition, agent memory design. This directory answers "how do I engineer it": verified paper numbers, token and dollar math, provider API behavior, failure modes, and defense architecture. Cross-links run in both directions, and the technique pages here assume the conceptual background and spend their lines on economics, reliability, and selection instead.

## Key Takeaways

- Prompt engineering has six families: in-context learning, reasoning elicitation, decomposition/search, output control, economics, and defense — select from requirements, not fashion.
- Output consumed by code should be schema-enforced structured output; "please return JSON" is a ~80%-reliability solution to a 100%-requirement problem.
- The reasoning ladder is CoT (2–5x tokens) → self-consistency (k× cost, few extra points) → ToT/GoT (10–100x calls, only when backtracking matters).
- Economics are prompting decisions: exact-prefix caching rewards static-prefix ordering (0.1x read pricing on Anthropic); compression shrinks RAG context before the prefill bill.
- Any prompt interpolating untrusted text needs architectural defense — privilege separation and least-privilege tools, not clever wording.
- Reasoning models invert part of the advice: explicit "think step by step" and heavy few-shot scaffolding can degrade them; check model-specific guidance.
- Every technique choice must be gated by an eval harness (promptfoo, Inspect, custom golden sets) and a cost-per-request metric.
- This directory is the engineering complement to `src/ml/agents/`: concepts there, contracts, costs, and threats here.

## References

- Prompt Engineering Guide (DAIR.AI) — https://www.promptingguide.ai/
- Prompting Guide paper index — https://www.promptingguide.ai/papers
- Anthropic prompt engineering overview — https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview
- OpenAI prompt engineering guide — https://platform.openai.com/docs/guides/prompt-engineering
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models", NeurIPS 2022 — https://arxiv.org/abs/2201.11903
- Wang et al., "Self-Consistency Improves Chain of Thought Reasoning in Language Models", ICLR 2023 — https://arxiv.org/abs/2203.11171
- Yao et al., "Tree of Thoughts: Deliberate Problem Solving with Large Language Models", NeurIPS 2023 — https://arxiv.org/abs/2305.10601
- Besta et al., "Graph of Thoughts: Solving Elaborate Problems with Large Language Models", AAAI 2024 — https://arxiv.org/abs/2308.09687
- DSPy (Stanford NLP) — https://dspy.ai/
- promptfoo — https://www.promptfoo.dev/docs/intro/
- OWASP Top 10 for LLM Applications — https://genai.owasp.org/
- Lilian Weng, "Prompt Engineering" (survey) — https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/

## Cross-References

- [Prompt Engineering for Production Systems](../prompt-engineering.md) — the production lifecycle: versioning, evaluation, token budgeting
- [Prompting Techniques (serving view)](../llm-serving/prompt-engineering.md) — the compact catalogue of basic and advanced prompting techniques
- [Chain-of-Thought Prompting](../../ml/agents/chain-of-thought.md) — the conceptual treatment this section's CoT page builds on
- [Tree-of-Thought](../../ml/agents/tree-of-thought.md) — conceptual branching intuition behind the ToT/GoT page
- [LLM Security](../llm-security.md) — the security overview feeding the injection-defense page
- [Prompt Engineering Reference Library](../../references/prompt-engineering.md) — the HTTP-verified index of every primary source used here
