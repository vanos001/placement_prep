# LLM Fundamentals

## Overview

Large Language Models (LLMs) are autoregressive Transformer models trained on massive text corpora to predict the next token in a sequence. This page covers the core concepts every LLM engineer must understand: tokenization, position encodings, the training pipeline, and decoding strategies.

## Autoregressive Language Models

An autoregressive LLM generates text one token at a time, conditioning each prediction on all previously generated tokens:

```
P(x_1, x_2, ..., x_T) = Π P(x_t | x_1, x_2, ..., x_{t-1})
```

Key properties that follow from this formulation:

| Property | Implication |
|---|---|
| **Causal masking** | Each token only attends to preceding tokens — no lookahead |
| **Sequential generation** | One token per forward pass during decode (memory-bound bottleneck) |
| **Left-to-right** | The model sees only the prompt prefix, not future tokens |
| **Distribution over vocabulary** | Each step produces logits over the full vocabulary, not a single token |

All modern production LLMs (GPT-4, Claude, LLaMA, Mistral, DeepSeek, Qwen) are decoder-only autoregressive Transformers. Encoder-decoder architectures (T5, BART) are used for specific tasks but have largely been superseded for general-purpose generation.

## Tokenization

Tokenization converts raw text into integer IDs. The choice of algorithm determines vocabulary efficiency, multilingual support, and per-token cost. See [tokenization.md](llm-serving/tokenization.md) for full details.

| Algorithm | Mechanism | Used By |
|---|---|---|
| **BPE** | Iteratively merges most frequent token pair | GPT family, LLaMA, Mistral |
| **WordPiece** | Merges pair maximizing data likelihood | BERT |
| **SentencePiece** | Framework implementing BPE or Unigram on raw text | T5, LLaMA (via SentencePiece) |

**Key interview point:** API pricing is per-token. GPT-4o uses a ~100K vocabulary with efficient multilingual tokenization; older models like GPT-2 (50K vocab) tokenize CJK text 2-3× less efficiently, directly increasing cost.

## Context Windows and Position Encodings

The context window is the maximum sequence length the model can process. It is constrained by the KV cache memory: O(2 × L × d × n_layers × T) where T is sequence length.

Position encodings inject order information into the permutation-equivariant self-attention mechanism. See [positional encoding](../ml/transformers/positional-encoding.md) for full derivations.

| Method | Type | Extrapolation | Models |
|---|---|---|---|
| **Learned absolute** | Absolute | Poor (train-length only) | GPT-2, GPT-3 |
| **RoPE** (Rotary) | Relative | Moderate; extended via YaRN, NTK-aware scaling | LLaMA 2/3, Mistral, Qwen, DeepSeek |
| **ALiBi** | Relative (linear bias) | Good | BLOOM, MPT |

**Why RoPE dominates:** RoPE encodes relative position as a rotation in the attention score computation. This naturally handles relative attention without explicit position matrices and can be extended to longer contexts via interpolation (NTK-aware) or extrapolation (YaRN). Reference: [Su et al., "RoFormer", 2021](https://arxiv.org/abs/2104.09864).

## Training Pipeline

Modern LLMs are trained in three stages. Each stage is covered in depth in dedicated pages.

| Stage | Objective | Data | Key Detail |
|---|---|---|---|
| **Pre-training** | Next-token prediction on internet-scale text | ~1-15T tokens | See [pretraining.md](llm-serving/pretraining.md) |
| **SFT** | Supervised fine-tuning on instruction-response pairs | ~10K-100K demonstrations | See [sft.md](llm-serving/sft.md) |
| **Alignment** | Optimize for human preferences | Preference pairs (chosen/rejected) | See [RLHF](../ml/rl/rlhf.md) and [DPO](../ml/rl/dpo.md) |

**RLHF** trains a reward model on human preference comparisons, then optimizes the LLM policy with PPO to maximize reward while staying close to the SFT model (KL penalty). It is the approach used by OpenAI for ChatGPT.

**DPO** (Direct Preference Optimization) eliminates the reward model and PPO loop entirely. It derives a closed-form loss that directly optimizes the policy on preference pairs, making it simpler and more stable. DPO is now the default for open-source model alignment (LLaMA, Mistral).

| Aspect | RLHF | DPO |
|---|---|---|
| Reward model | Required | Not required |
| Training stability | Complex (PPO hyperparameters) | Stable (single loss) |
| Compute | 4 models (actor, critic, reward, reference) | 2 models (policy, reference) |
| Quality ceiling | Higher (with sufficient reward model data) | Slightly lower but closing |

## Decoding Strategies

After the model produces logits over the vocabulary, a decoding strategy selects the next token. This is one of the most practical levers for controlling LLM output quality.

### Greedy Decoding

Select the token with the highest probability at each step. Deterministic but often produces repetitive or generic text.

### Temperature

Divide logits by temperature τ before softmax:

```
P(x_t) = softmax(logits / τ)
```

| Temperature | Effect | Use Case |
|---|---|---|
| τ → 0 | Near-greedy, deterministic | Factual extraction, code generation |
| τ = 0.3-0.7 | Focused, less random | Instruction following, summarization |
| τ = 1.0 | Model's natural distribution | General chat |
| τ > 1.0 | More random, diverse | Brainstorming, creative writing |

**Implementation note:** OpenAI, Anthropic, and most providers set temperature=0 to mean greedy decoding (not τ→0 literally). Some providers use top-p = 1.0 to disable nucleus sampling.

### Top-k Sampling

Sample from the k highest-probability tokens only (Fan et al., 2018). Set k=50 means the model chooses only from the 50 most likely tokens at each step.

**Problem:** A fixed k is suboptimal. When the distribution is sharp (one token is very likely), k=50 still includes unlikely tokens. When the distribution is flat (many tokens are roughly equally likely), k=50 may truncate too aggressively.

### Top-p (Nucleus) Sampling

Sample from the smallest set of tokens whose cumulative probability exceeds p (Holtzman et al., 2020). The set size varies dynamically at each step.

```
Top-p with p=0.9: select smallest set V' ⊆ V where Σ P(token ∈ V') ≥ 0.9
```

| Method | Adaptive? | Quality | Default in |
|---|---|---|---|
| **Greedy** | No | Deterministic | Code generation tasks |
| **Top-k** | No | Good | HuggingFace default |
| **Top-p** | Yes | Better | OpenAI, Anthropic, Cohere |
| **Temperature + Top-p** | Yes | Best | Most production systems |

**Best practice:** Use temperature=0 for deterministic tasks (classification, extraction), temperature=0.3-0.7 with top-p=0.9-0.95 for general instruction following. Reference: [OpenAI API docs — temperature and sampling](https://platform.openai.com/docs/guides/text-generation).

### Repetition Penalty

Penalize tokens that have already appeared in the generated sequence. Commonly used with open-source models (HuggingFace `repetition_penalty` parameter). Values of 1.1-1.2 reduce repetition without significantly hurting coherence.

## Interview Questions

### Q1: What does "autoregressive" mean and why does it matter for latency?
**Answer:** Autoregressive means the model generates one token at a time, with each token conditioned on all previous tokens. This matters for latency because decode is sequential — you cannot parallelize token generation (each token depends on the previous one's KV cache entry). This makes decode memory-bandwidth bound, not compute bound. The prefill phase (processing the prompt) is compute-bound and parallelizable, but decode dominates latency for long outputs.

### Q2: Why do modern LLMs use RoPE instead of learned positional embeddings?
**Answer:** RoPE (Rotary Position Embedding) encodes relative position information directly into the attention computation via rotation matrices. Advantages over learned absolute positions: (1) naturally handles relative attention, (2) can be extended to longer contexts via NTK-aware scaling or YaRN interpolation, (3) does not require retraining for longer sequences, (4) produces better empirical results on long-context tasks. GPT-2/GPT-3 used learned positions and were strictly limited to their training context length.

### Q3: Explain the difference between top-k and top-p sampling.
**Answer:** Top-k samples from a fixed number (k) of the highest-probability tokens. Top-p (nucleus sampling) dynamically selects the smallest set of tokens whose cumulative probability exceeds p. Top-p is generally preferred because it adapts to the distribution at each step — when the model is confident (sharp distribution), it uses fewer tokens; when uncertain (flat distribution), it uses more. Top-k can include very unlikely tokens when the distribution is sharp, or truncate too aggressively when flat.

### Q4: What is the training pipeline for a production LLM like ChatGPT?
**Answer:** Three stages: (1) Pre-training on ~1-15T tokens of internet text using next-token prediction — produces a base model that can continue text but doesn't follow instructions. (2) SFT on ~10K-100K instruction-response pairs — teaches the model to follow instructions and produce desired formats. (3) Alignment via RLHF (train reward model on human preferences, then PPO optimization) or DPO (directly optimize on preference pairs) — aligns outputs with human values (helpfulness, safety, honesty). DPO is increasingly preferred for open-source due to simplicity.

### Q5: How does temperature affect the output distribution?
**Answer:** Temperature τ divides the logits by τ before applying softmax. Lower temperature (τ → 0) makes the distribution sharper — the highest-probability token dominates, approaching greedy decoding. Higher temperature (τ > 1) flattens the distribution, making unlikely tokens more probable and increasing diversity/randomness. At τ = 1, you get the model's natural probability distribution. For production: use τ = 0 for deterministic tasks, τ = 0.3-0.7 for focused generation, τ = 1+ for creative tasks.

## References

1. Vaswani et al., "Attention Is All You Need", NeurIPS 2017
2. Radford et al., "Language Models are Unsupervised Multitask Learners" (GPT-2), 2019
3. Su et al., "RoFormer: Enhanced Transformer with Rotary Position Embedding", 2021
4. Holtzman et al., "The Curious Case of Neural Text Degeneration" (Nucleus Sampling), ICLR 2020
5. Fan et al., "Hierarchical Neural Story Generation" (Top-k), ACL 2018
6. Rafailov et al., "Direct Preference Optimization", NeurIPS 2023
7. Ouyang et al., "Training Language Models to Follow Instructions with Human Feedback" (InstructGPT), NeurIPS 2022

## Cross-References

- [Tokenization →](llm-serving/tokenization.md) Full tokenization deep dive
- [Position Encodings →](../ml/transformers/positional-encoding.md) RoPE, ALiBi derivations
- [GPT Architecture →](../ml/llm/gpt-architecture.md) Model architecture details
- [Pre-training →](llm-serving/pretraining.md) Pre-training process
- [SFT →](llm-serving/sft.md) Supervised fine-tuning
- [RLHF →](../ml/rl/rlhf.md) Reinforcement Learning from Human Feedback
- [DPO →](../ml/rl/dpo.md) Direct Preference Optimization
- [Sampling & Inference →](llm-serving/inference.md) Production inference optimization
