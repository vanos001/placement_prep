# LLM & AI Cheat Sheet

## Transformer Architecture

```
Input → Tokenization → Embedding + Positional Encoding
  → [Encoder: Multi-Head Attention → Add&Norm → FFN → Add&Norm] × N
  → [Decoder: Masked MHA → Cross-Attention → FFN] × N
  → Linear → Softmax → Output Probabilities
```

## Key Concepts

| Concept | What | Why It Matters |
|---------|------|----------------|
| Self-Attention | Q·K^T/√d → softmax → V | Captures long-range dependencies |
| Multi-Head | Parallel attention heads | Different relationship types |
| Positional Encoding | Inject sequence order | Attention is permutation-invariant |
| KV Cache | Cache past K,V during generation | Avoid recomputation, 10-100x speedup |
| Residual Connection | x + F(x) | Gradient flow, training stability |
| Layer Norm | Normalize across features | Stabilizes training |

## Attention Formulas

```
Attention(Q,K,V) = softmax(QK^T / √d_k) × V
MultiHead = Concat(head_1, ..., head_h) × W^O
where head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)

Complexity: O(n²d) time, O(n² + nd) memory
```

## LLM Training Pipeline

```
1. Pre-training (next token prediction on massive corpus)
   → Foundation model (GPT, Llama, Mistral)
2. Supervised Fine-Tuning (SFT)
   → Instruction-following on curated examples
3. Alignment (RLHF / DPO / GRPO)
   → Human preferences → helpful, harmless, honest
4. Deployment (quantization, serving optimization)
```

## RLHF vs DPO

| | RLHF | DPO |
|---|---|---|
| Approach | Train reward model → PPO | Direct preference optimization |
| Complexity | High (3 models) | Lower (1 model) |
| Stability | Can be unstable | More stable |
| Formula | Reward + KL penalty | Loss on preference pairs |

## Inference Optimization

| Technique | Speedup | Trade-off |
|-----------|---------|-----------|
| KV Cache | 10-100x | Memory |
| Quantization (INT8/INT4) | 2-4x | Slight quality loss |
| Speculative Decoding | 2-3x | Extra small model needed |
| Continuous Batching | 2-5x | Implementation complexity |
| Flash Attention | 2-4x | Memory efficient |
| PagedAttention | 1.5-3x | Virtual memory for KV |
| Tensor Parallelism | Linear w/ GPUs | Communication overhead |

## Quantization

```
FP32 → FP16/BF16 → INT8 → INT4
  4B     2B        1B     0.5B  (per param)

Post-Training (PTQ): Calibrate after training (GPTQ, AWQ, GGUF)
Quantization-Aware (QAT): Simulate during training
```

## RAG (Retrieval-Augmented Generation)

```
Query → Embed → Vector Search → Retrieved Docs → LLM + Context → Answer

Components: Embedding model, Vector DB, Chunking strategy, Reranker
Chunking: Fixed-size, Recursive, Semantic
Vector DBs: Pinecone, Weaviate, Milvus, ChromaDB, FAISS
```

## AI Agents

```
User → LLM → [Think → Act → Observe] loop → Response

ReAct: Reasoning + Acting (interleaved)
Chain-of-Thought: Step-by-step reasoning
Tool Calling: LLM invokes external tools/APIs
MCP: Model Context Protocol (standardized tool interface)
Multi-Agent: Multiple specialized agents collaborating
```

## Tokenization

| Method | Used By | Pros |
|--------|---------|------|
| BPE | GPT, Llama | Good balance |
| WordPiece | BERT | Linguistic awareness |
| SentencePiece | T5, mBART | Language-agnostic |
| Unigram | Some models | Probabilistic |

## Positional Encoding Types

| Type | Max Length | Extrapolation |
|------|-----------|---------------|
| Sinusoidal | Fixed | Poor |
| Learned | Fixed | Poor |
| RoPE | Flexible | Good |
| ALiBi | Very long | Excellent |

## Key Models Quick Reference

| Model | Params | Key Feature |
|-------|--------|-------------|
| GPT-4/4o | ~1.8T (MoE) | Multimodal, best reasoning |
| Claude 3.5 | Unknown | Long context, safety |
| Gemini 1.5 | Up to 1T | 1M+ context, multimodal |
| Llama 3 | 8B-405B | Open source leader |
| Mistral/Mixtral | 7B-8x22B | MoE, efficient |
| DeepSeek-V3 | 671B MoE | Open, strong coding |
| Qwen 2.5 | 0.5B-72B | Multilingual |

## Serving Systems

| System | Key Feature |
|--------|-------------|
| vLLM | PagedAttention, continuous batching |
| TensorRT-LLM | NVIDIA optimized |
| TGI | HuggingFace production |
| Ollama | Local, easy setup |
| SGLang | Structured generation |

## Embeddings

```
Text → Embedding Model → Dense Vector (768-4096 dim)
Similarity: cosine(q, d) = (q·d) / (||q|| × ||d||)
Models: text-embedding-3-large (OpenAI), BGE, E5, GTE
```

## Interview Quick Tips

1. Know the transformer architecture cold (encoder, decoder, attention)
2. Explain KV cache and why it matters for inference
3. Compare RLHF vs DPO trade-offs
4. Describe RAG pipeline with failure modes
5. Discuss agent architectures (ReAct, tool calling)
6. Know quantization types and trade-offs
7. Understand scaling laws (Chinchilla)
