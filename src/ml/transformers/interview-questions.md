# Transformer Interview Questions

## Overview

This page consolidates the most frequently asked Transformer interview questions across FAANG and top ML companies. Questions range from fundamentals to advanced design trade-offs.

## Foundational Questions

### 1. What is the Transformer architecture and why was it revolutionary?

The Transformer (Vaswani et al., 2017) replaced recurrent architectures with **pure self-attention**, enabling:
- **Parallelization**: All positions processed simultaneously (vs. sequential RNN)
- **Long-range dependencies**: Direct attention between any two positions ($O(1)$ hops vs. $O(n)$ for RNN)
- **Scalability**: Efficiently leverages GPUs, scales to billions of parameters

### 2. Explain the scaled dot-product attention mechanism.

\\[\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V\\]

- $Q$ (query), $K$ (key), $V$ (value) are linear projections of the input
- $d_k$ is the key dimension — scaling prevents softmax saturation for large $d_k$
- Complexity: $O(n^2 d)$ for sequence length $n$ and dimension $d$

### 3. Why do we scale by $\sqrt{d_k}$?

Without scaling, when $d_k$ is large, the dot products $QK^T$ grow in magnitude, pushing softmax into regions with extremely small gradients. Dividing by $\sqrt{d_k}$ keeps the variance of the dot products at approximately 1, ensuring stable gradient flow.

### 4. What is multi-head attention and why use it?

Multi-head attention runs $h$ parallel attention operations with different learned projections:

\\[\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)W^O\\]
\\[\text{head}_i = \text{Attention}(QW_i^Q, KW_i^K, VW_i^V)\\]

Benefits:
- Different heads can attend to different types of relationships (syntactic, semantic, positional)
- Each head operates in a lower-dimensional space ($d_k = d_{\text{model}} / h$)
- No additional computational cost vs. single-head with full dimension

### 5. Why does the Transformer use positional encoding?

Self-attention is **permutation-equivariant** — it treats the input as a set, not a sequence. Positional encoding injects information about token order, enabling the model to distinguish "the cat sat on the mat" from "the mat sat on the cat."

### 6. Explain the difference between sinusoidal and learned positional encodings.

| Aspect | Sinusoidal | Learned |
|--------|-----------|---------|
| Type | Fixed mathematical function | Trainable parameters |
| Generalization | Can extrapolate to unseen lengths | Limited to training length |
| Parameters | Zero additional | $L \times d$ parameters |
| Used in | Original Transformer | BERT, GPT-2+ |

### 7. What is the role of residual connections and layer normalization?

**Residual connections**: $x + \text{Sublayer}(x)$ — prevent vanishing gradients in deep networks, enable training of 24+ layer models.

**Layer normalization**: Normalize across the feature dimension for each token, stabilizing training. Applied as Post-LN (original) or Pre-LN (more stable, used in GPT).

```python
# Pre-LN (more stable, used in modern transformers)
x = x + self.attention(self.ln1(x))
x = x + self.feedforward(self.ln2(x))

# Post-LN (original Transformer)
x = self.ln1(x + self.attention(x))
x = self.ln2(x + self.feedforward(x))
```

### 8. What is the feed-forward network (FFN) in a Transformer?

Each layer has a position-wise FFN applied independently to each token:

\\[\text{FFN}(x) = \text{ReLU}(xW_1 + b_1)W_2 + b_2\\]

- Typically $d_{ff} = 4 \times d_{\text{model}}$ (e.g., 3072 for $d=768$)
- Acts as a key-value memory (Geva et al., 2021)
- Modern variants use SwiGLU or GELU instead of ReLU

### 9. Compare encoder-only, decoder-only, and encoder-decoder architectures.

| Aspect | Encoder-Only | Decoder-Only | Encoder-Decoder |
|--------|-------------|-------------|-----------------|
| Example | BERT | GPT | T5, BART |
| Attention | Bidirectional | Causal | Enc: bidirectional, Dec: causal |
| Pre-training | MLM | Next token prediction | Denoising / span corruption |
| Best for | Understanding | Generation | Seq2seq |
| Fine-tuning | Task heads | Prompting | Text-to-text |

### 10. What is causal masking in decoder-only models?

A lower-triangular mask that prevents position $i$ from attending to positions $j > i$, ensuring autoregressive generation:

```python
def causal_mask(seq_len):
    return torch.tril(torch.ones(seq_len, seq_len))
```

## Intermediate Questions

### 11. How does the KV cache work during inference?

During autoregressive generation, previously computed key and value vectors are cached and reused, avoiding redundant computation:

- Without KV cache: $O(n^2)$ per token (recompute all keys/values)
- With KV cache: $O(n)$ per token (only compute new token's Q, K, V)
- Memory: $2 \times L \times n \times d$ floats (K and V for all layers)

### 12. What is FlashAttention and why is it important?

FlashAttention is an IO-aware exact attention algorithm that:
- Tiles the attention computation to fit in SRAM (fast on-chip memory)
- Avoids writing the full $n \times n$ attention matrix to HBM (slow GPU memory)
- Reduces memory from $O(n^2)$ to $O(n)$ with recomputation in backward pass
- 2-4x faster than standard attention on modern GPUs

### 13. Explain rotary positional embeddings (RoPE).

RoPE encodes position by rotating query and key vectors:

\\[f(q, m) = q e^{im\theta}\\]

where $m$ is position and $\theta$ is a frequency. The dot product $f(q,m)^T f(k,n)$ naturally depends on relative position $(m-n)$, providing:
- Relative position awareness without explicit relative embeddings
- Smooth extrapolation to longer sequences
- Used in LLaMA, PaLM, and most modern LLMs

### 14. What is ALiBi (Attention with Linear Biases)?

ALiBi adds a linear bias to attention scores based on distance:

\\[\text{score}_{ij} = q_i^T k_j - m \cdot |i - j|\\]

where $m$ is a head-specific slope. Benefits:
- No positional embeddings needed
- Better length extrapolation than sinusoidal or learned positions
- Used in BLOOM and MPT models

### 15. How do Vision Transformers (ViT) process images?

1. Split image into patches (e.g., 16×16 pixels)
2. Flatten and linearly project each patch to embedding dimension
3. Prepend a learnable [CLS] token
4. Add positional embeddings
5. Process through standard Transformer encoder
6. Use [CLS] token output for classification

### 16. What is the Swin Transformer and why is it more efficient?

Swin Transformer uses **shifted window attention**:
- Compute attention within local windows (e.g., 7×7 patches)
- Shift windows between layers for cross-window connections
- Complexity: $O(n)$ instead of $O(n^2)$ for image size $n$
- Hierarchical: merge patches at deeper layers (like CNN feature pyramids)

### 17. Explain mixture of experts (MoE) in Transformers.

MoE replaces the FFN with multiple "expert" FFNs and a gating network:

\\[y = \sum_{i=1}^{E} g_i(x) \cdot \text{Expert}_i(x)\\]

where $g(x) = \text{TopK}(\text{softmax}(W_g x))$ activates only the top-$k$ experts.

Benefits: Increase model capacity without proportionally increasing computation. Used in Switch Transformer, Mixtral, GPT-4.

### 18. What is the difference between Pre-LN and Post-LN Transformers?

| Aspect | Post-LN (Original) | Pre-LN (Modern) |
|--------|-------------------|-----------------|
| Order | LN after residual | LN before sublayer |
| Training stability | Requires warmup | More stable |
| Final performance | Slightly better at convergence | Slightly worse |
| Used in | Original Transformer | GPT-2, LLaMA, most LLMs |

### 19. How does BERT's [CLS] token work?

- A special token prepended to every input sequence
- Its final hidden state is used as the aggregate sequence representation
- For classification: add a linear head on top of [CLS] embedding
- For sentence pairs: [CLS] sentence_a [SEP] sentence_b [SEP]

### 20. What is the context window of different models?

| Model | Context Window |
|-------|---------------|
| BERT | 512 tokens |
| GPT-2 | 1024 tokens |
| GPT-3 | 2048 tokens |
| GPT-4 | 8K / 32K / 128K tokens |
| Claude 3 | 200K tokens |
| Gemini 1.5 | 1M+ tokens |

## Advanced Questions

### 21. Why does self-attention have $O(n^2)$ complexity and what are the solutions?

Self-attention computes $n \times n$ pairwise interactions. Solutions:
- **Sparse attention**: Longformer, BigBird — $O(n)$ with local + global patterns
- **Linear attention**: Performer, RWKV — approximate softmax with random features
- **FlashAttention**: Exact attention with better hardware utilization
- **Sliding window**: Mistral — fixed-size local attention window

### 22. What is grouped-query attention (GQA)?

GQA uses fewer key-value heads than query heads:
- MHA: $h$ query heads, $h$ KV heads (full)
- GQA: $h$ query heads, $g$ KV heads ($g < h$)
- MQA: $h$ query heads, 1 KV head (extreme)

Reduces KV cache memory by $h/g$ while maintaining quality. Used in LLaMA 2 (70B), Mistral.

### 23. How does sparse mixture of experts scale?

Switch Transformer (Fedus et al., 2021) showed:
- 1.6T parameters with same compute as 10B dense model
- Top-1 routing: each token goes to 1 expert
- Load balancing loss prevents expert collapse
- Communication overhead in distributed setting is the bottleneck

### 24. What is knowledge distillation for Transformers?

Train a smaller "student" model to mimic a larger "teacher":
- **Logit distillation**: Match softmax outputs with temperature scaling
- **Feature distillation**: Match intermediate representations
- **Attention distillation**: Match attention patterns
- Example: DistilBERT retains 97% of BERT performance with 60% fewer parameters

### 25. Explain the difference between BERT and RoBERTa.

| Aspect | BERT | RoBERTa |
|--------|------|---------|
| NSP | Yes | Removed |
| Masking | Static | Dynamic (new mask each epoch) |
| Batch size | 256 | 8K |
| Training data | 16GB | 160GB |
| Tokenization | WordPiece | BPE (byte-level) |
| Performance | Baseline | Significantly better |

### 26. How does cross-attention work in encoder-decoder models?

The decoder attends to encoder outputs:
- $Q$ comes from the decoder's previous layer
- $K, V$ come from the encoder's final output
- Allows the decoder to "look at" the input sequence when generating each output token
- Only the decoder has causal masking; encoder attention is bidirectional

### 27. What is DeBERTa and its key innovations?

DeBERTa (Decoding-enhanced BERT with disentangled attention):
- **Disentangled attention**: Separate embeddings for content and position, compute attention between content-content, content-position, and position-content
- **Enhanced mask decoder**: Absolute position information added after all attention layers
- Outperforms BERT and RoBERTa on most benchmarks

### 28. How do you handle sequences longer than the training context?

- **Position interpolation**: Scale positions to fit within trained range
- **YaRN**: Yet another RoPE extension for longer contexts
- **Sliding window**: Process in chunks with overlap
- **ALiBi**: Naturally extrapolates to longer sequences
- **Sparse attention**: Reduce complexity to handle longer sequences

### 29. What is the "attention sink" phenomenon?

In decoder-only models, the first token receives disproportionately high attention even though it's often meaningless (e.g., BOS token). This is because:
- Softmax requires attention scores to sum to 1
- Early tokens serve as a "sink" for excess attention weight
- StreamingLLM exploits this: keep first few tokens + recent window for infinite-length generation

### 30. Design a Transformer for a new modality (e.g., audio). What choices would you make?

Key decisions:
- **Tokenization**: How to convert raw signal to tokens (e.g., mel spectrogram patches, learned encoders)
- **Positional encoding**: Relative positions (RoPE) for variable-length sequences
- **Architecture**: Encoder-only (classification) vs. decoder-only (generation)
- **Context length**: Audio has high frame rates — need efficient attention
- **Pre-training**: Masked prediction (like BERT) or autoregressive (like GPT)
- Examples: Whisper (encoder-decoder for speech), MusicGen (decoder-only for music)

### 31. What are the memory requirements for serving a Transformer model?

For a model with $P$ parameters in FP16:
- **Model weights**: $2P$ bytes
- **KV cache** (per token per batch): $2 \times L \times d \times 2$ bytes
- **Activations**: Depends on batch size and sequence length
- Example: LLaMA-7B in FP16 = 14GB weights + ~1.4MB KV cache per token per batch

### 32. How does FlashAttention-2 improve over FlashAttention-1?

- Better work partitioning between GPU warps
- Reduced non-matmul FLOPs
- Support for variable sequence lengths (block-sparse attention)
- ~2x speedup over FlashAttention-1
- Head-dimension parallelism for small head dimensions

## Common Mistakes in Interviews

1. **Confusing self-attention with cross-attention**: Self-attention has Q=K=V from same sequence; cross-attention has Q from one sequence and K,V from another
2. **Forgetting the scaling factor**: Not mentioning $\sqrt{d_k}$ when explaining attention
3. **Misunderstanding causal masking**: Saying decoder has "no bidirectional attention" is correct but explain WHY (autoregressive generation)
4. **Omitting the FFN**: The feed-forward network is ~2/3 of Transformer parameters — don't ignore it
5. **Confusing BERT and GPT for the same tasks**: BERT = understanding, GPT = generation

## Cross-References

- [Transformer Architecture](./architecture.md) — Original design details
- [Self-Attention](./self-attention.md) — Deep dive into attention
- [Transformer Variants](./variants.md) — BERT, GPT, T5, ViT
- [Training Transformers](./training.md) — Optimization techniques
- [LLM Interview Questions](../llm/README.md) — LLM-specific questions
- [GPU Computing](../../arch/parallelism/gpu.md) — Hardware for Transformers
