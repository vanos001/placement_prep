# Distributed AI Systems & Inference at Scale

This section covers the intersection of distributed systems and large language models — the infrastructure, algorithms, and engineering decisions that make AI work at planetary scale.

## Files

| File | Topics | Key Interview Themes |
|------|--------|---------------------|
| [distributed-ai-infra.md](distributed-ai-infra.md) | Agent execution, GPU scheduling, model placement, federated training, edge inference | "How do you run 10k agents in parallel?" |
| [distributed-rag.md](distributed-rag.md) | Vector DB scaling, semantic caching, multi-tenant RAG, inference queues | "How do you serve RAG to 1M users?" |
| [disaggregated-inference.md](disaggregated-inference.md) | Prefill/decode split, KV cache disaggregation, RDMA/CXL inference | "Why split prefill and decode?" |
| [distributed-training.md](distributed-training.md) | Collective comms, fault-tolerant training, federated learning, Byzantine robustness | "How does GPU training scale to 16k GPUs?" |

## Why This Matters for Interviews

Modern AI systems are *distributed systems problems*. Every company running LLMs at production scale faces:
- **Resource fragmentation** — GPUs are expensive and rarely fully utilized.
- **Communication overhead** — all-reduce on thousands of GPUs dominates training time.
- **Latency vs. throughput** — serving users in real-time while maximizing GPU utilization.
- **Fault tolerance** — a single GPU failure shouldn't kill a 3-week training run.

Understanding these trade-offs signals senior-level systems thinking. Expect questions that start with "how would you design..." and require combining ML knowledge with distributed systems fundamentals.

## Prerequisites

- Basic transformer architecture (see [transformer-internals.md](../transformer-internals.md))
- Inference systems basics (see [inference-systems.md](../inference-systems.md))
- Distributed systems fundamentals (Paxos/Raft, consensus, network models)
- Kubernetes and container orchestration fundamentals
