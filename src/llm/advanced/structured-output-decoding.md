# Constrained Decoding: How Structured Output Is Actually Enforced

Every LLM serving stack now advertises "structured output" or "JSON mode": you hand the
model a JSON Schema, a regex, or a full context-free grammar, and every completion matches
it — no retries, no parsing failures. The mechanism is never prompt trickery. It is
**grammar-masked sampling**: at each decode step, every token that would move the string
outside the grammar has its logit set to `-inf` before the softmax, so the model cannot
possibly emit it. This page is about how that mask is computed, what it costs, and the
four ways teams get bitten by it in production.

One vocabulary note first: *constrained decoding* (the general mechanism), *guided
generation*, and *structured output* (the product feature) refer to the same loop. The
formal guarantee is a language-membership one: output ∈ L(G) for grammar G.

## The Per-Token Contract

```text
      logits (vocab, float)                     valid-token set V(s_t)
            |                                          |
            |   DFA state s_t ----advance by token---> DFA state s_(t+1)
            v                                          v
      +------------------------------ mask ------------------------------+
      |  logit[t] = -inf   for t not in V(s_t)                           |
      |  logit[t] unchanged for t in V(s_t)                              |
      +------------------------------------------------------------------+
            v
      softmax -> sample -> t_i  (only grammar-legal tokens have mass)
            v
      append t_i, advance DFA, repeat
```

Three properties define the contract:

1. **Soundness**: any string the loop can emit is in L(G). This is a hard invariant —
   the mask is applied *after* the model's preferences, so no prompt engineering can
   break it.
2. **Termination**: decoders must guarantee the grammar can still finish (EOS reachability).
   A naive mask over `{` `}` nesting without an EOS state can produce infinitely nested
   output until the context window is exhausted.
3. **Nothing about semantics**: soundness is syntactic. `"age": -999999999` satisfies a
   JSON grammar for an integer; it does not satisfy your business rules. Constrained
   decoding removes a failure class; it does not remove validation.

## Where the Mask Comes From

The interesting engineering is all in one question: given partial output
`{"user": "ada", ` and a grammar, which of the ~128k vocab entries are legal continuations?

### Strategy 1: Regex / FSM over the token alphabet

For regular languages (regex, most JSON-primitive fields), compile the pattern to a DFA
whose alphabet is *tokenizer units*, not characters. This is the approach of the Outlines
paper (Willard & Louf, 2023): build the FSM over characters, then "align" it with the
vocabulary by finding, for each FSM state, the set of tokens whose character sequence is
compatible with some path from that state. The result is a map:

```text
state  ->  {token : next_state}        precomputed once per (grammar, tokenizer) pair
```

Per decode step the cost is then O(1): look up the state, read the precomputed set.

### Strategy 2: Prefix trie over the vocabulary

For closed-world outputs (identifiers, tool names, enum values), index the vocabulary in a
trie and mark the branch set from the current prefix. This is effectively what modern
serving stacks do for *tool-call arguments*: the legal continuations are literally the
listed choices.

### Strategy 3: Pushdown automata for context-free grammars

JSON with arbitrary nesting is context-free, not regular: a DFA cannot balance braces.
Full CFG tracking requires a stack (LR/LALR parser states, or GLL), and naive per-step
parsing is too slow for batch serving. XGrammar (Dong et al., MLSys 2025) attacks this
with two ideas:

- **Context-independent vs context-dependent masks.** Most parser states admit a fixed
  token set regardless of history (e.g., right after `:` in JSON you need a value start).
  Those masks are computed once and cached — a single bitmask AND against the logits
  buffer. Only the rare stack-dependent states (inside arbitrarily nested containers) get
  a per-sequence recomputation, done in C++ with bitset tricks.
- **Adaptive token compilation**: instead of enumerating every vocabulary token at every
  parser state, XGrammar's preprocessor organizes the vocab so each state's token test is
  a small set operation, and tokens that can never appear in the current context are
  excluded from the check entirely.

The published claim is roughly an order-of-magnitude reduction in grammar-compile time
versus FS string-traversal baselines, with per-step mask application approaching zero
marginal cost in batched serving. The generic lesson survives any implementation:
**separate the per-sequence dynamic state (tiny) from the per-grammar static mask (huge,
cacheable), and cache the static part across requests.**

### What the engines actually ship

| Engine | Grammar accepted | Mask strategy | Notable restriction |
|---|---|---|---|
| Outlines (dottxt) | Regex, CFG, JSON Schema | FSM compiled over tokenizer alphabet | Compile pass can be slow for big schemas |
| XGrammar (vLLM default backend) | EBNF/CFG, JSON Schema | Adaptive token masks, context-independent cache | JSON Schema subset ("basic" constructs) |
| llama.cpp GBNF | GBNF (BNF-like CFG) | Grammar-stepped sampling over CPPM trie | Entire grammar written by hand in GBNF |
| TGI (HF) | JSON Schema, regex | Logit masking via outlines-style FSM | Single backend, less tunable |
| SGLang | JSON Schema, EBNF | xgrammar / outlines backends, batched mask apply | Backend choice per request |

GBNF is worth a look as the "manual transmission" option: because llama.cpp exposes the
grammar directly, you can express exactly the dialect you want (say, a log line with
fixed fields) without JSON Schema's rigidity.

## Executed Demo: The Mask, Step by Step

The following pure-stdlib program compiles a one-member JSON-object grammar into a DFA
over a 9-token vocabulary, decodes with logit masking, and quantifies how much the
constraint shrinks the output space. Real output follows the code.

```python
# Grammar-constrained decoding, mechanically:
# 1. compile a toy JSON grammar into a DFA over a small token vocabulary
# 2. at each decode step, mask logits of tokens the DFA rejects
# 3. sample with a seeded RNG -> deterministic, reproducible output
# 4. enumerate the full constrained language vs the unconstrained one
import random

VOCAB = ['{', '"a"', '"b"', ':', ',', '1', '2', '}', 'EOS']

# DFA states: (state) -> {token: next_state}
# Grammar L = { ( "a" | "b" ) : ( 1 | 2 ) }  (single-member JSON object)
TRANS = {
    'S0':  {'{': 'S1'},
    'S1':  {'"a"': 'S2', '"b"': 'S2'},
    'S2':  {':': 'S3'},
    'S3':  {'1': 'S4', '2': 'S4'},
    'S4':  {'}': 'S5'},
    'S5':  {'EOS': 'ACCEPT'},
    'ACCEPT': {},
}

def allowed(state):
    return sorted(TRANS.get(state, {}).keys())

def greedy_decode(pref_logits, seed=7):
    rng = random.Random(seed)
    state, out, log = 'S0', [], []
    while state != 'ACCEPT':
        valid = allowed(state)
        # logits for invalid tokens are masked to -inf -> prob 0
        masked = [(t, pref_logits[t] if t in valid else float('-inf'))
                  for t in VOCAB]
        choice, _ = max(masked, key=lambda p: (p[1], rng.random()))
        out.append(choice)
        log.append((state, valid, choice, pref_logits[choice]))
        state = TRANS[state][choice]
    return out, log

# deterministic "model preference" over the vocab (arbitrary but fixed)
BASE = {'{': 2.9, '"a"': 2.1, '"b"': 2.6, ':': 2.4, ',': 1.7,
        '1': 2.2, '2': 2.0, '}': 2.8, 'EOS': 1.9}
toks, log = greedy_decode(BASE)

print("Step-by-step constrained decoding (model prefers '\"b\"', '1', '}'):")
print(f"{'step':>4} {'DFA state':<8} {'valid tokens':<28} {'picked':<6} raw_logit")
for i, (state, valid, choice, lg) in enumerate(log):
    print(f"{i:>4} {state:<8} {', '.join(valid):<28} {choice:<6} {lg:.1f}")
print("\nOutput string:", ''.join(t for t in toks if t != 'EOS'))

# How big is each space?
# unconstrained: any of 9 tokens x 8 steps (9th slot must be EOS to terminate)
unconstrained = len(VOCAB) ** 8 * 1
language = [f'{{"{k}":{v}}}' for k in ('a', 'b') for v in ('1', '2')]
print(f"\nUnconstrained space (8 free tokens): 9^8 = {unconstrained:,}")
print(f"Constrained language: {len(language)} strings -> {unconstrained/len(language):,.0f}x tighter")
print("Accepted strings:", language)

# mask-cache view (XGrammar-style): which states are context-independent?
ci = [s for s in TRANS if all(t in ('{', ':', '}') for t in TRANS[s])]
cd = [s for s in TRANS if s not in ci]
print(f"\nContext-independent mask states (branch on fixed token): {ci}")
print(f"Context-dependent mask states (branch on model choice):   {cd}")
```

```text
Step-by-step constrained decoding (model prefers '"b"', '1', '}'):
step DFA state valid tokens                 picked raw_logit
   0 S0       {                            {      2.9
   1 S1       "a", "b"                     "b"    2.6
   2 S2       :                            :      2.4
   3 S3       1, 2                         1      2.2
   4 S4       }                            }      2.8
   5 S5       EOS                          EOS    1.9

Output string: {"b":1}

Unconstrained space (8 free tokens): 9^8 = 43,046,721
Constrained language: 4 strings -> 10,761,680x tighter
Accepted strings: ['{"a":1}', '{"a":2}', '{"b":1}', '{"b":2}']

Context-independent mask states (branch on fixed token): ['S0', 'S2', 'S4', 'ACCEPT']
Context-dependent mask states (branch on model choice):   ['S1', 'S3', 'S5']
```

Read the table as the whole algorithm: six decode steps, each with a mask that
*dominates* the model's own preference (at step 0 the model's second choice `"b"` is
masked out entirely), and an output that is valid by construction. The last two lines are
the XGrammar insight in miniature: 4 of the 7 states branch on a fixed token (mask
cacheable forever), and only the states where the *model's choice* determines the future
need per-sequence handling.

## The Cost Model

Constrained decoding moves LLM serving's bottleneck around, so profile it as three costs:

| Cost | Where | Scale | Mitigation |
|---|---|---|---|
| Grammar compile | Request start | 10 µs – 10 s (schema size, vocab size) | Cache compiled mask per schema; adaptive compilation |
| Per-step mask apply | Every decode step | 1 bitmask AND, ~O(vocab/64) words | Precomputed context-independent masks |
| Prefix-state tracking | Every decode step | Parser stack ops, branch on token | Keep stack minimal; batch across requests |
| Output-length shift | End-to-end | Grammar can force longer outputs than free decoding | Budget tokens; design grammars with short paths |

The compile/apply split is the one interviewers probe: a stack that re-parses the whole
grammar at every step is O(steps × states × vocab) and will melt under load; a stack with
a warm mask cache pays almost nothing per step but needs an LRU keyed on
(schema hash, tokenizer hash).

## Four Ways This Bites in Production

**1. Tokenizer boundary mismatches.** The FSM alphabet is tokenizer units, and
tokenizers merge characters in surprising ways: `"address"` may be one token, a
multi-byte emoji is several, and some vocabularies contain a token that is literally
`{"a":`. If the grammar compiler maps character-level states to tokens naively, a token
can be admitted that straddles a state boundary, emitting text that *looks* fine but
fails the parser — the exact bug the Outlines paper's alignment procedure exists to
prevent. Whitespace handling in JSON is the classic trigger: the schema says no trailing
commas, but a token like `,\n` or ` }` silently smuggles one past an over-permissive FSM.

**2. Constrained ≠ distributed-as-trained.** Masking is a conditional distribution:
p(t | grammar) = p_model(t) · 1[t ∈ V(s)] / Z. Renormalization amplifies whatever the
model put on the surviving tokens — including tokens the model considered nearly
implausible before masking. Practically: constrained JSON often reads *worse* than free
JSON from the same model, and prompt-side format instructions fight the grammar. Teams
that care about quality re-tune (or fine-tune) with the constraint active, rather than
assuming the mask is neutral.

**3. Semantic vs syntactic validity.** A schema can require `priority ∈ {low, med, high}`,
not that the model pick the priority matching the ticket text. Structured output moved
the failure from "invalid JSON" (now ~never) to "valid JSON, wrong content" (now the
dominant failure). Keep your post-parse validators; the grammar is a pre-filter.

**4. Termination and escape hatches.** Under a strict grammar, a model that "wants" to
stop can't: EOS is not in V(s) until the structure can close. Without a max-tokens cap
that is grammar-aware, you get outputs that fill the context window with valid-but-unwanted
JSON. Production systems pair every grammar with (a) hard token budgets, (b) an
EOF-forcing fallback, and (c) a validity check *at the boundary* — a stream cut at the
token limit must be handled as a parse failure, not silently returned.

A fifth, quieter trap: **compile-time latency on the hot path**. First request with a new
10k-line JSON Schema can take seconds to compile; ship schema precompilation as a
deploy-time artifact, not a per-request cost.

## Where This Sits in the Serving Stack

The mask lives in the sampler, which means it composes with everything else the serving
layer does: continuous batching applies one batched masked-softmax over the union of
requests (each with its own mask), and speculative/verification paths must apply the
mask at verification time too, or accepted draft tokens can violate the grammar. For the
batching interactions, see [vLLM internals](vllm-internals.md) and
[batching strategies](../llm-serving/batching.md); for what the logits tensor is before
masking, see [transformer internals](transformer-internals.md). TGI exposes the feature
as grammar/regex constraints on request ([TGI notes](../llm-serving/tgi.md)), and the
prompt-level "JSON mode" you get from model APIs is the same mechanism with the schema
chosen server-side ([prompt engineering](../prompt-engineering.md)).

## Rapid-Fire Q&A

**Q: Why not just prompt the model and retry on parse failure?**
A: Retries are latency × cost multipliers with unbounded tail; masking is a constant-factor
logit op with a hard soundness guarantee. Use retries as a backstop for semantic errors,
not syntax.

**Q: Does the mask change the model's distribution?**
A: Yes — it conditions and renormalizes. The *support* changes (impossible tokens removed);
conditional mass on legal tokens is amplified. That is a feature (you wanted the
constraint) but it also shifts style and needs evaluation, not assumption.

**Q: Why is CFG harder than regex here?**
A: FSM masks are per-state functions of the token set only; CFGs need a parse stack, so
the legal set depends on unbounded history. The engineering fix is decomposing states
into context-independent (cacheable) vs context-dependent (per-request) masks.

**Q: What does the grammar do to latency percentiles?**
A: Adds a one-time compile cost (cacheable) and a small per-step cost; the bigger effect
is usually output length, since grammars force structural tokens (quotes, braces, commas)
that free decoding might have elided.

## References

1. Willard & Louf, *Efficient Guided Generation for Large Language Models* (Outlines),
   arXiv:2307.09702 — <https://arxiv.org/abs/2307.09702>
2. Dong et al., *XGrammar: Flexible and Efficient Structured Generation Engine for Large
   Language Models*, MLSys 2025 — <https://arxiv.org/abs/2411.15100>
3. Geng et al., *Grammar-Constrained Decoding for Structured NLP Tasks without
   Finetuning*, EMNLP 2023 — <https://arxiv.org/abs/2305.13971>
4. llama.cpp GBNF grammars documentation —
   <https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md>
5. vLLM Structured Outputs documentation —
   <https://docs.vllm.ai/en/latest/features/structured_outputs.html>
