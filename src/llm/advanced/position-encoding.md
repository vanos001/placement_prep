# Position Encoding (RoPE, ALiBi, etc.)

Position encoding is how transformers inject information about token order into the model. Unlike RNNs (which process tokens sequentially) or CNNs (which use spatial locality), transformers are permutation-invariant — without position encoding, "dog bites man" and "man bites dog" would have identical representations. This page covers absolute position encoding (original transformer), relative position encoding (T5), Rotary Position Embedding (RoPE, used in Llama and most modern LLMs), and Attention with Linear Biases (ALiBi).

## Why Position Encoding Matters

The transformer's self-attention computes a weighted average of values, where weights are softmax of Q K^T. The weights are invariant to token order — if you permute the input tokens, the attention weights are correspondingly permuted, but the model can't distinguish order without additional signal.

Position encoding adds a per-position vector to each token's embedding, so the model can distinguish "the" at position 0 from "the" at position 5.

## Absolute Position Encoding (Vaswani et al., 2017)

The original transformer adds a position vector `p_i` to each token's embedding:

```text
emb_i = token_emb(token_i) + position_emb(i)
```

The position embeddings can be:
- **Learned** (BERT, GPT-2): a lookup table of size (max_seq_len, hidden_dim), trained as parameters.
- **Sinusoidal** (Vaswani et al.): a fixed function:
  ```text
  p_i, 2k   = sin(i / 10000^(2k/d))
  p_i, 2k+1 = cos(i / 10000^(2k/d))
  ```
  The sinusoidal encoding has a nice property: for any offset `k`, `p_{i+k}` is a linear function of `p_i`, so attention can learn to attend by relative position.

Absolute position encoding's limitation: the model can't extrapolate beyond the max_seq_len it was trained on. A model trained with max_seq_len=512 will behave poorly on sequences of 1024.

## Relative Position Encoding (T5, Shaw et al., 2018)

T5's relative position encoding adds a learned bias to the attention scores:

```text
Score(q_i, k_j) = q_i^T * k_j + bias(i - j)
```

The bias is a learned lookup table indexed by the relative distance `i - j`. Distances are bucketed (e.g., buckets of size 1 for |i-j| < 8, size 2 for 8 ≤ |i-j| < 16, etc.) to share parameters across positions.

Relative encoding is more expressive than absolute (the model can directly learn "attend to tokens N positions back") and somewhat extrapolates (the bias for large |i-j| can generalize).

## Rotary Position Embedding (RoPE, Su et al., 2021)

RoPE rotates the Q and K vectors based on their position, so that the dot product depends only on the relative position:

```text
For position i and dimension d (paired as 2D subspaces):
  q_i, 2k:2k+2 → rotate by angle θ_i, 2k = i / 10000^(2k/d)
  k_j, 2k:2k+2 → rotate by angle θ_j, 2k = j / 10000^(2k/d)

After rotation, the dot product:
  q_i · k_j = f(i - j)  ← depends only on relative position
```

The rotation is a 2D rotation matrix applied to each pair of dimensions. The angles increase with position.

RoPE's advantage: the attention score naturally depends on relative position, with no extra parameters. The model extrapolates to longer sequences (up to ~2× the training length, with NTK-aware scaling).

```python
def apply_rope(q, k, positions):
    # q, k: (batch, num_heads, seq_len, head_dim)
    # positions: (batch, seq_len)
    
    # Compute rotation angles for each position and dimension pair
    angles = positions[..., None] / (10000 ** (torch.arange(0, head_dim, 2) / head_dim))
    cos = torch.cos(angles).repeat_interleave(2, dim=-1)
    sin = torch.sin(angles).repeat_interleave(2, dim=-1)
    
    # Rotate q and k
    q_rot = (q * cos) + (rotate_half(q) * sin)
    k_rot = (k * cos) + (rotate_half(k) * sin)
    
    return q_rot, k_rot
```

## ALiBi (Press et al., 2021)

ALiBi (Attention with Linear Biases) doesn't use position embeddings at all. Instead, it adds a linear bias to the attention scores based on distance:

```text
Score(q_i, k_j) = q_i^T * k_j - m * |i - j|
```

where `m` is a per-head constant (e.g., `1/2^head_index`).

The bias is a simple linear decay with distance — tokens far apart have lower attention scores. This biases the model toward attending to nearby tokens.

ALiBi's advantage: it extrapolates to arbitrary sequence lengths with no parameter changes. A model trained with max_seq_len=512 works fine on 4096-token sequences.

ALiBi's disadvantage: the linear decay is a strong inductive bias; it may not be optimal for tasks where distant tokens are equally important.

## Comparison

| Method | Parameters | Extrapolation | Quality (typical) | Used in |
|--------|------------|---------------|-------------------|---------|
| Absolute (learned) | max_seq_len × d | None | Baseline | BERT, GPT-2 |
| Absolute (sinusoidal) | 0 | Weak | Baseline | Vaswani transformer |
| Relative (T5) | small (bucketed) | Moderate | +1% vs absolute | T5, BART |
| RoPE | 0 | Strong (with NTK) | +1% vs absolute | Llama, Mistral |
| ALiBi | 0 (head slopes) | Very strong | -1% vs absolute | MPT, BLOOM |

For modern LLMs (Llama-2/3, Mistral, DeepSeek), RoPE is the standard. ALiBi is used in some models (MPT, BLOOM) for its extrapolation property. Absolute is used in older models (BERT, T5, GPT-2).

## RoPE Length Extension

A Llama-2 model trained with max_seq_len=4096 can't directly handle 32K-token sequences (RoPE's angles were trained for positions 0-4095). Extensions:

### Position Interpolation

Linearly scale positions: position `i` in [0, 32K) is mapped to `i * 4096 / 32K = i / 8` in [0, 4095). The RoPE angles are computed with the scaled positions.

```python
positions = torch.arange(seq_len) * (original_max / seq_len)
apply_rope(q, k, positions)
```

Requires fine-tuning on a small dataset to recover quality. Llama-2-7B-chat-32K uses this technique.

### NTK-Aware Scaling

Instead of linear scaling, scale the angle's frequency:

```python
def ntk_rope(dim, max_position, base=10000):
    # Scale the base by (max_position / original_max_position)
    new_base = base * (max_position / original_max) ** (dim / (dim - 2))
    angles = positions / (new_base ** (torch.arange(0, dim, 2) / dim))
    return angles
```

NTK-aware scaling doesn't require fine-tuning; the model extrapolates naturally.

### YaRN (Yet another RoPE extensioN)

YaRN (2023) combines NTK scaling with attention temperature scaling. It's the current SOTA for RoPE extension; Llama-3 uses it for 128K context.

## Production Use

```python
# Llama-2 / Llama-3 with RoPE
class LlamaAttention(nn.Module):
    def __init__(self, config):
        self.q_proj = nn.Linear(config.hidden, config.hidden)
        self.k_proj = nn.Linear(config.hidden, config.hidden)
        self.v_proj = nn.Linear(config.hidden, config.hidden)
        self.rope_theta = config.rope_theta  # Llama-2: 10000, Llama-3: 500000
    
    def forward(self, hidden, positions):
        q = self.q_proj(hidden)
        k = self.k_proj(hidden)
        v = self.v_proj(hidden)
        
        q, k = apply_rope(q, k, positions, base=self.rope_theta)
        # Attention as usual
        return F.scaled_dot_product_attention(q, k, v)
```

The `rope_theta` parameter controls the frequency of the rotation. Higher values (like Llama-3's 500000) reduce the angle's growth rate, allowing for longer contexts.

## Common Pitfalls

1. **Using learned absolute embeddings for long contexts.** The model can't extrapolate; you must train with the full target seq_len.

2. **Forgetting that RoPE's `theta` parameter affects length capability.** Default 10000 works up to ~8K; for 128K, use 500000 or YaRN.

3. **Forgetting that RoPE needs position IDs in attention.** Some libraries compute positions internally; others expect them as input. Be explicit.

4. **Forgetting that ALiBi's slope per head matters.** Different heads use different slopes; the assignment matters for quality.

5. **Forgetting that position encoding needs to be re-trained if the model's max_seq_len changes.** A model trained with seq_len=4096 can't just be loaded with seq_len=32768 — extend with interpolation or YaRN.

6. **Forgetting that RoPE is applied to Q and K, not V.** V is position-independent in standard attention.

## References

- Vaswani et al., "[Attention Is All You Need](https://arxiv.org/abs/1706.03762)" (NeurIPS 2017)
- Shaw et al., "[Self-Attention with Relative Position Representations](https://arxiv.org/abs/1803.02155)" (NAACL 2018)
- Su et al., "[RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)" (Neurocomputing 2021)
- Press et al., "[Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation](https://arxiv.org/abs/2108.12409)" (ICLR 2022)
- Chen et al., "[YaRN: Efficient Context Window Extension of Large Language Models](https://arxiv.org/abs/2309.00071)" (ICLR 2024)
- [Eleuther AI: Rotary Position Embedding blog post](https://blog.eleuther.ai/rotary-position-embeddings/)
- [Llama 3 architecture (Meta blog)](https://ai.meta.com/blog/meta-llama-3/)
