# SGLang

SGLang (Structured Generation Language) is an open-source LLM serving framework developed by Lianmin Zheng, Lianmin Yin, et al. at LMSYS (the same org as vLLM) in 2024. It extends vLLM's continuous batching + PagedAttention with two new features: **RadixAttention** (prefix caching via a radix tree) and a **frontend DSL** for structured LLM programs. This page covers the architecture, the RadixAttention mechanism, the structured generation DSL, and the comparison to vLLM.

## The Two Contributions

SGLang is best understood as vLLM + two enhancements:

1. **RadixAttention**: a radix tree over the KV cache that automatically shares prefixes across requests, including dynamically-discovered prefixes that vLLM's prefix caching can't share.
2. **Frontend DSL**: a Python library (`sgl.gen`, `sgl.gen_batched`, `sgl.few_shot`) for writing structured LLM programs that the runtime optimizes.

## RadixAttention

vLLM's prefix caching is "static": it caches the KV for explicitly-tagged prefixes (e.g., the system prompt). Two requests with the same system prompt share its KV.

SGLang's RadixAttention is "dynamic": it caches the KV for any prefix encountered, automatically. The cache is a radix tree:

```text
Radix tree nodes (each holds the KV for a token range):
  Root
   ├── "The capital of France is" (5 tokens)  ← cached after first query
   │     ├── " Paris."  ← completed queries
   │     └── " in Europe."
   ├── "The capital of Italy is"
   │     └── " Rome."
   └── ...
```

When a new request arrives:
1. The runtime walks the radix tree to find the longest cached prefix.
2. The KV for that prefix is reused (no recompute).
3. The new tokens are added to the tree.

This is faster than vLLM's prefix caching for:
- RAG workloads where the prefix is "the system prompt + retrieved chunks" — each request has a different chunk sequence, so vLLM's static caching misses.
- Few-shot prompts with shared examples.
- Long-context queries with overlapping document ranges.

## The Frontend DSL

SGLang's Python frontend:

```python
import sglang as sgl

@sgl.function
def multi_turn_question(s, question):
    s += "The following is a conversation with an AI assistant.\n"
    s += sgl.system("You are a helpful assistant.")
    s += sgl.user(f"Question: {question}")
    s += sgl.assistant("Answer: " + sgl.gen("answer", max_tokens=100))
    s += sgl.user(f"Why?")
    s += sgl.assistant("Reason: " + sgl.gen("reason", max_tokens=200))

# Run a batch
states = multi_turn_question.run_batch([
    {"question": "What is the capital of France?"},
    {"question": "What is the capital of Italy?"},
    {"question": "What is the capital of Germany?"},
])
# Each state['answer'] and state['reason'] is filled in.
```

The DSL's features:
- `sgl.gen()`: generation call with constraints (max_tokens, temperature, regex).
- `sgl.system()`, `sgl.user()`, `sgl.assistant()`: role-tagged content.
- `sgl.function`: a function decorated for batched execution.

The DSL allows the runtime to:
- Recognize shared prefixes across batched calls.
- Schedule generations for max throughput.
- Apply constraints (e.g., JSON output, regex) efficiently.

## Constrained Generation

SGLang supports constrained generation:

```python
import sglang as sgl
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int
    city: str

@sgl.function
def extract_person(s, text):
    s += "Extract the person from this text:"
    s += text
    s += sgl.gen("person", schema=Person.schema_json())

state = extract_person.run("John Smith, 35, lives in NYC.")
print(state["person"])  # {"name": "John Smith", "age": 35, "city": "NYC"}
```

The runtime compiles the schema into an LL(1) grammar and applies it as a constraint on each generation step. The output is guaranteed to match the schema.

This is 10-100× faster than post-hoc JSON parsing (which retries on malformed output).

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  HTTP API (FastAPI)                                              │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Scheduler (per replica)                                         │
│  - Admits requests with priority by prefix overlap              │
│  - Pre-empts low-overlap requests in memory pressure            │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  RadixAttention Cache Manager                                    │
│  - Maintains the radix tree                                      │
│  - Allocates KV blocks per node                                  │
│  - Evicts LRU nodes when memory pressure                         │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Model Workers (per GPU)                                         │
│  - PagedAttention kernel (same as vLLM)                          │
│  - Tensor parallel within a node                                  │
└─────────────────────────────────────────────────────────────────┘
```

The scheduler's "prefix overlap" priority is the key innovation. When admitting a new request, the scheduler computes its prefix overlap with existing radix tree nodes. Requests with high overlap are admitted first (they have low KV cost); requests with low overlap may be deferred.

## Production Performance

SGLang's published numbers (Llama-2 70B, 4×A100, RAG workload with 4K-token prefixes):

| Workload | vLLM (with prefix caching) | SGLang (RadixAttention) |
|----------|------------------------------|---------------------------|
| RAG, 1K requests/sec | 1K tokens/sec/GPU | 3K tokens/sec/GPU |
| Few-shot Q&A | 800 tokens/sec/GPU | 2.5K tokens/sec/GPU |
| Multi-turn chat | 600 tokens/sec/GPU | 1.8K tokens/sec/GPU |

SGLang's 3× speedup comes from RadixAttention's automatic prefix sharing — most RAG and chat workloads have substantial shared prefixes that vLLM's static caching doesn't exploit.

## When SGLang Wins

- **RAG with shared system prompt + variable retrieved context**: SGLang's RadixAttention caches the system prompt's KV once and reuses it for every query.
- **Multi-turn chat**: the prefix is "previous turns"; SGLang caches incrementally.
- **Few-shot prompting**: shared examples across many queries.
- **Constrained generation**: schema-constrained output (JSON, regex).

## When vLLM Wins

- **Single-turn inference with no prefix sharing**: vLLM is simpler to deploy.
- **Production maturity**: vLLM has been in production longer; more battle-tested.
- **Multi-LoRA serving**: vLLM's multi-LoRA is more mature.
- **Community support**: vLLM has a larger community and more documentation.

## Common Pitfalls

1. **Forgetting that RadixAttention's cache can fill up.** Under sustained load, the LRU eviction policy may evict useful prefixes. Monitor the cache hit rate.

2. **Forgetting that the frontend DSL requires Python.** SGLang's DSL is Python-only; non-Python clients must use the HTTP API (which doesn't get the DSL's optimizations).

3. **Forgetting that schema-constrained generation can slow down the model.** Each step requires the grammar's LL(1) parser to be invoked, adding ~1-5 ms per token. For free-form generation, skip the constraint.

4. **Forgetting that RadixAttention is per-replica.** Multi-replica deployments don't share cache across replicas; each replica has its own tree.

5. **Forgetting that the scheduler's pre-emption can cause latency spikes.** A pre-empted request must be re-run later, adding latency. Set the request's `priority` high if latency matters.

6. **Confusing SGLang (the serving engine) with sgl-Python (the Python library).** The library is the DSL; the engine is the server. Both are needed.

## References

- Zheng et al., "[SGLang: Efficient Execution of Structured Language Model Programs](https://arxiv.org/abs/2312.07104)" (NeurIPS 2024)
- [SGLang GitHub repository](https://github.com/sgl-project/sglang)
- [SGLang documentation](https://docs.sglang.ai/)
- [SGLang vs vLLM comparison](https://docs.sglang.ai/references/supported_models.html)
- [LMSYS: Large Model Systems Organization](https://lmsys.org/)
- [RadixAttention paper](https://arxiv.org/abs/2312.07104) (NeurIPS 2024)
- [LWN: SGLang overview (2024)](https://lwn.net/Articles/936633/)
