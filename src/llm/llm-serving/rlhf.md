# RLHF & DPO

## Overview

RLHF (Reinforcement Learning from Human Feedback) and DPO (Direct Preference Optimization) are alignment techniques that make LLMs helpful, harmless, and honest (HHH). After SFT teaches the model to follow instructions, RLHF/DPO fine-tune it to match human preferences — choosing better responses over worse ones.

This is the final stage in the LLM training pipeline and is responsible for the "polish" that separates a good model from a great one.

## The Alignment Pipeline

```mermaid
graph LR
    BASE[Base Model] --> SFT[SFT Model]
    SFT --> REWARD[Reward Model Training]
    REWARD --> PPO[PPO Optimization]
    PPO --> ALIGNED[Aligned Model]

    SFT --> DPO_PATH[DPO - Direct]
    DPO_PATH --> ALIGNED2[Aligned Model]
```

## RLHF: Reinforcement Learning from Human Feedback

### Step 1: Collect Preference Data

For each prompt, generate multiple responses and ask humans to rank them:

```
Prompt: "Explain quantum computing to a 10-year-old"

Response A: "Quantum computing uses qubits that can be 0 and 1 simultaneously..."  [Rank: 2]
Response B: "Imagine you have a magic coin that can be heads AND tails at the same time..."  [Rank: 1]
Response C: "Quantum computing is a type of computation that harnesses quantum mechanical phenomena..."  [Rank: 3]
```

```mermaid
graph TD
    P[Prompt] --> R1[Response A]
    P --> R2[Response B]
    P --> R3[Response C]
    R1 --> H[Human Ranking]
    R2 --> H
    R3 --> H
    H --> PREF["Preference: B > A > C"]
    PREF --> PAIRS["Training Pairs: (B,A), (B,C), (A,C)"]
```

### Step 2: Train a Reward Model

The reward model learns to score responses based on human preferences:

```python
# Reward model architecture
class RewardModel(nn.Module):
    def __init__(self, base_model):
        super().__init__()
        self.backbone = base_model  # Usually the SFT model
        self.reward_head = nn.Linear(hidden_dim, 1)  # Scalar reward
    
    def forward(self, input_ids, attention_mask):
        hidden = self.backbone(input_ids, attention_mask).last_hidden_state
        reward = self.reward_head(hidden[:, -1, :])  # Last token's representation
        return reward
```

**Training objective** (Bradley-Terry model):

```
L = -log(σ(r_chosen - r_rejected))
```

Where r_chosen is the reward for the preferred response and r_rejected for the dispreferred one.

```mermaid
graph LR
    PAIR["(chosen, rejected) pair"] --> RM[Reward Model]
    RM --> R_C[chosen reward r_c]
    RM --> R_R[rejected reward r_r]
    R_C --> LOSS["Loss = -log(σ(r_c - r_r))"]
    R_R --> LOSS
    LOSS --> UPDATE[Update RM]
```

### Step 3: PPO (Proximal Policy Optimization)

Use the reward model to fine-tune the SFT model using reinforcement learning:

```mermaid
graph TD
    PROMPT[Prompt] --> POLICY[Policy Model - SFT initialized]
    POLICY --> RESPONSE[Generated Response]
    RESPONSE --> REWARD[Reward Model Score]
    RESPONSE --> KL[KL Penalty vs SFT Model]
    REWARD --> OBJECTIVE["Objective = Reward - β × KL"]
    KL --> OBJECTIVE
    OBJECTIVE --> PPO[PPO Update]
    PPO --> POLICY
```

**PPO Objective:**

```
maximize E[r(x, y) - β × KL(π_θ || π_ref)]
```

Where:
- **r(x, y)**: Reward model score for prompt x and response y
- **β**: KL penalty coefficient (prevents deviation from SFT model)
- **π_θ**: Current policy (being trained)
- **π_ref**: Reference policy (frozen SFT model)

**Why KL penalty?** Without it, the model would "hack" the reward model — finding responses that score high but aren't actually good (reward hacking).

### PPO Components

PPO uses four models simultaneously:

| Model | Role | Updated? |
|---|---|---|
| **Policy** | Generates responses | Yes (main training target) |
| **Reference** | Computes KL penalty | No (frozen SFT model) |
| **Reward** | Scores responses | No (frozen after training) |
| **Value** | Estimates expected reward (critic) | Yes (helps compute advantages) |

This is why RLHF is memory-intensive — you need 4 copies of the model in memory.

## DPO: Direct Preference Optimization

### The Problem with RLHF

RLHF has several pain points:
1. **Complex**: Requires training a separate reward model
2. **Unstable**: PPO can be difficult to tune
3. **Memory-heavy**: 4 model copies needed
4. **Reward hacking**: Model can exploit reward model weaknesses

### DPO's Insight

DPO (Rafailov et al., 2023) shows that the RLHF objective can be optimized **directly** from preference data, without a separate reward model:

```
L_DPO = -log(σ(β × (log π_θ(y_w|x)/π_ref(y_w|x) - log π_θ(y_l|x)/π_ref(y_l|x))))
```

Where y_w is the winning (preferred) response and y_l is the losing (rejected) response.

```mermaid
graph LR
    PAIR["Preference Pair (y_w, y_l)"] --> MODEL[Model π_θ]
    PAIR --> REF[Reference Model π_ref]
    MODEL --> LOGP_θ["log π_θ(y_w), log π_θ(y_l)"]
    REF --> LOGP_REF["log π_ref(y_w), log π_ref(y_l)"]
    LOGP_θ --> DPO_LOSS[DPO Loss]
    LOGP_REF --> DPO_LOSS
    DPO_LOSS --> UPDATE[Update π_θ]
```

### DPO vs RLHF Comparison

| Aspect | RLHF (PPO) | DPO |
|---|---|---|
| **Components** | 4 models (policy, ref, reward, value) | 2 models (policy, ref) |
| **Memory** | Very high | Moderate |
| **Complexity** | High (PPO tuning) | Low (standard supervised loss) |
| **Stability** | Can be unstable | Very stable |
| **Reward model** | Explicit (separate model) | Implicit (in the loss) |
| **Online data** | Generates new responses | Uses pre-collected preferences |
| **Quality** | Can be slightly better with good reward model | Comparable in most benchmarks |

### DPO Training Code

```python
# Simplified DPO training
for batch in preference_dataloader:
    # Forward pass on chosen and rejected
    chosen_logps = model.log_prob(batch.chosen_input_ids, batch.chosen_labels)
    rejected_logps = model.log_prob(batch.rejected_input_ids, batch.rejected_labels)
    
    # Reference model (frozen)
    with torch.no_grad():
        ref_chosen_logps = ref_model.log_prob(batch.chosen_input_ids, batch.chosen_labels)
        ref_rejected_logps = ref_model.log_prob(batch.rejected_input_ids, batch.rejected_labels)
    
    # DPO loss
    chosen_rewards = beta * (chosen_logps - ref_chosen_logps)
    rejected_rewards = beta * (rejected_logps - ref_rejected_logps)
    loss = -F.logsigmoid(chosen_rewards - rejected_rewards).mean()
    
    loss.backward()
    optimizer.step()
```

## GRPO: Group Relative Policy Optimization

GRPO (DeepSeek, 2024) is a newer alternative that removes the need for a value/critic model:

```mermaid
graph TD
    PROMPT[Prompt] --> SAMPLE[Sample G responses from policy]
    SAMPLE --> SCORE[Score each response with reward model]
    SCORE --> NORMALIZE["Normalize rewards within group"]
    NORMALIZE --> ADVANTAGE["Advantage = (r_i - mean(r)) / std(r)"]
    ADVANTAGE --> GRPO_UPDATE["GRPO Policy Update"]
```

**Key innovation**: Instead of learning a value function (expensive), GRPO uses the group's mean reward as a baseline. Advantages are computed relative to other samples in the same group.

**Advantages over PPO:**
- No critic/value model needed (saves ~25% memory)
- Simpler implementation
- Competitive or better performance

## Constitutional AI (CAI)

Constitutional AI (Anthropic, 2022) uses AI feedback instead of human feedback:

```mermaid
graph TD
    PROMPT[Prompt] --> MODEL[Model generates response]
    MODEL --> CRITIQUE[AI critiques response against constitution]
    CRITIQUE --> REVISE[Model revises response]
    REVISE --> PAIR["Preference pair: (revised, original)"]
    PAIR --> DPO_TRAIN[DPO Training]
```

**The Constitution**: A set of principles the model should follow:
- "Choose the response that is least harmful"
- "Choose the response that is most helpful while being honest"
- "Choose the response that refuses harmful requests most politely"

This reduces the need for human labelers while maintaining alignment quality.

## Reward Hacking and Mitigations

### What is Reward Hacking?

The model exploits weaknesses in the reward model to get high scores without actually being better:

```mermaid
graph LR
    HACK[Model learns to game reward model]
    HACK --> V1[Verbose responses score higher]
    HACK --> V2[Sycophantic responses score higher]
    HACK --> V3[Certain phrases trigger high reward]
    V1 --> BAD[High reward, bad quality]
    V2 --> BAD
    V3 --> BAD
```

### Mitigations

| Technique | How It Works |
|---|---|
| **KL penalty** | Prevents model from straying too far from SFT |
| **Reward model ensemble** | Average multiple reward models |
| **Iterative RLHF** | Regularly update reward model with new data |
| **Process reward models** | Reward each reasoning step, not just final answer |
| **Length penalty** | Penalize unnecessarily long responses |

## DAPO and RLVR: The 2025 Frontier

### RLVR (Reinforcement Learning with Verifiable Rewards)

RLVR uses rewards that can be automatically verified, removing the need for human feedback or learned reward models:

```mermaid
graph TD
    Q[Math Problem] --> MODEL[Model generates solution]
    MODEL --> VERIFY[Execute code / check math]
    VERIFY -->|Correct| R_POS[+1 reward]
    VERIFY -->|Incorrect| R_NEG[0 reward]
    R_POS --> GRPO[GRPO Update]
    R_NEG --> GRPO
```

**Verifiable reward domains:**
- **Math**: Check if final answer matches ground truth
- **Code**: Execute generated code against test cases
- **Logic**: Verify formal proofs
- **Structured output**: Validate JSON/XML against schema

**Why RLVR matters:**
- No human labeling needed (scales infinitely)
- No reward model to train (saves compute)
- No reward hacking (ground truth is objective)
- DeepSeek R1 used RLVR to achieve breakthrough reasoning

### DAPO (Dynamic Sampling Policy Optimization)

DAPO (ByteDance, 2025) improves on GRPO with several techniques:

| Technique | What It Does | Why It Helps |
|---|---|---|
| **Dynamic sampling** | Adjusts number of samples per prompt based on difficulty | More exploration for hard problems |
| **Clip-higher** | Asymmetric PPO clipping (higher upper bound) | Prevents premature convergence |
| **Token-level loss** | Normalizes loss per token, not per sequence | Balances short and long responses |
| **Overlong filtering** | Penalizes excessively long responses | Prevents reward hacking via verbosity |

### The Three-Stage Pipeline (2025 State of the Art)

```mermaid
graph LR
    BASE[Base Model] --> SFT1[Stage 1: SFT]
    SFT1 --> ALIGN[Stage 2: DPO/RLHF Alignment]
    ALIGN --> RLVR[Stage 3: RLVR with GRPO/DAPO]
    RLVR --> REASONING[Reasoning Model]
```

**Stage 1 — SFT**: Teach instruction following (1-3 epochs, high-quality data)
**Stage 2 — DPO/RLHF**: Align with human preferences (helpfulness, safety)
**Stage 3 — RLVR**: Train reasoning with verifiable rewards (math, code, logic)

DeepSeek R1, OpenAI o1, and Claude 3.5 all use variations of this pipeline.

## Online vs Offline RL

| Aspect | Offline RL (DPO) | Online RL (PPO/GRPO) |
|---|---|---|
| **Data** | Pre-collected preference pairs | Generate new responses during training |
| **Exploration** | Fixed dataset | Model explores new response space |
| **Compute** | Lower (no generation during training) | Higher (generate + score + update) |
| **Quality ceiling** | Limited by dataset diversity | Higher (discovers new strategies) |
| **Stability** | Very stable | Can be unstable |
| **Use case** | Quick alignment, limited compute | Maximum quality, frontier models |

**Key insight**: Online RL has a higher quality ceiling because the model can discover response strategies not present in the original preference dataset. This is why frontier labs (OpenAI, Anthropic, DeepSeek) use online RL despite the higher cost.

### Iterative DPO (Bridging the Gap)

Iterative DPO generates new responses with the current model, then creates preference pairs:

```mermaid
graph TD
    MODEL[Current Model] --> GEN[Generate responses]
    GEN --> SCORE[Score with reward model / judge]
    SCORE --> PAIRS[Create preference pairs]
    PAIRS --> DPO[DPO training step]
    DPO --> MODEL
```

This combines DPO's simplicity with online exploration.

## Practical RLHF/DPO Training

### DPO with TRL

```python
from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM

model = AutoModelForCausalLM.from_pretrained("sft-model")
ref_model = AutoModelForCausalLM.from_pretrained("sft-model")

config = DPOConfig(
    output_dir="./dpo-output",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=5e-7,  # Much lower than SFT!
    beta=0.1,  # KL penalty coefficient
    num_train_epochs=1,  # Usually 1 epoch for DPO
    bf16=True,
)

trainer = DPOTrainer(
    model=model,
    ref_model=ref_model,
    args=config,
    train_dataset=preference_dataset,  # Must have 'chosen' and 'rejected' columns
    tokenizer=tokenizer,
)
trainer.train()
```

### Key Hyperparameters

| Parameter | Typical Value | Notes |
|---|---|---|
| Learning rate | 1e-7 to 5e-7 | Much lower than SFT (1e-5) |
| Beta (β) | 0.1-0.5 | KL penalty, higher = closer to reference |
| Epochs | 1-2 | DPO overfits quickly |
| Batch size | 32-128 | Larger than SFT for stable gradients |
| Max length | 2048-4096 | Depends on preference data |

## Interview Questions

### Q1: Explain the full RLHF pipeline.
**Answer:** RLHF has three stages:
1. **Data collection**: Generate multiple responses per prompt, humans rank them
2. **Reward model training**: Train a model to predict human preferences using Bradley-Terry loss: L = -log(σ(r_chosen - r_rejected))
3. **PPO optimization**: Fine-tune the SFT model to maximize reward while staying close to the reference model via KL penalty. The objective is E[r(x,y) - β·KL(π_θ||π_ref)].

This requires 4 models in memory: policy, reference, reward, and value (critic).

### Q2: How does DPO simplify RLHF?
**Answer:** DPO eliminates the reward model and PPO by showing that the optimal RLHF policy can be expressed directly in terms of preference data. The DPO loss is:
L = -log(σ(β·(log π_θ(y_w)/π_ref(y_w) - log π_θ(y_l)/π_ref(y_l))))

This is a simple supervised loss (no RL needed). Benefits: 2 models instead of 4, stable training, no reward model, no PPO complexity. Quality is comparable to RLHF in most benchmarks.

### Q3: What is reward hacking and how do you prevent it?
**Answer:** Reward hacking occurs when the model exploits reward model weaknesses to get high scores without quality improvements. Examples: generating verbose responses, using specific phrases that trigger high reward, or being sycophantic.

Prevention: KL penalty (limits deviation from SFT model), reward model ensembles (harder to exploit multiple models), iterative RLHF (update reward model regularly), process reward models (reward steps not just outcomes), and length normalization.

### Q4: What is GRPO and how does it differ from PPO?
**Answer:** GRPO (Group Relative Policy Optimization) removes the value/critic model from PPO. Instead of learning a value function, it samples G responses per prompt, scores them all, and computes advantages relative to the group mean: advantage_i = (r_i - mean(r)) / std(r). This saves ~25% memory and simplifies training while maintaining competitive performance. DeepSeek used GRPO for their models.

### Q5: Why do we need alignment if SFT already makes the model helpful?
**Answer:** SFT teaches the model to follow instructions, but doesn't teach it which responses are *better* than others. Problems with SFT alone:
- The model may give harmful responses if they appear in training data
- It may be verbose when concise is better
- It may hallucinate confidently
- It may be sycophantic (agreeing with the user even when wrong)

RLHF/DPO teaches nuance: not just "how to respond" but "which response is preferred." This is why ChatGPT (SFT+RLHF) dramatically outperforms base GPT-3.5 (SFT only).

## Common Mistakes

- ❌ Skipping RLHF/DPO and deploying an SFT-only model (poor quality)
- ❌ Not using KL penalty (reward hacking)
- ❌ Using too small a reward model (poor preference learning)
- ❌ Collecting preference data from non-expert annotators
- ❌ DPO on low-quality preference pairs (garbage in, garbage out)
- ❌ Forgetting that DPO still needs a reference model for the KL-like term

## Summary

RLHF aligns LLMs with human preferences through reward modeling and PPO. DPO simplifies this to a direct preference loss without a separate reward model. GRPO removes the critic model using group-relative advantages. The 2025 frontier adds RLVR (verifiable rewards) with GRPO/DAPO for reasoning models. Online RL (PPO/GRPO) has a higher quality ceiling than offline RL (DPO) because the model explores new response strategies. Constitutional AI replaces human feedback with AI feedback. The modern three-stage pipeline is: SFT → DPO/RLHF alignment → RLVR for reasoning. All methods share the goal of making LLMs helpful, harmless, and honest while avoiding reward hacking.

## References

1. Ouyang et al., "Training language models to follow instructions with human feedback" (InstructGPT/RLHF), NeurIPS 2022
2. Rafailov et al., "Direct Preference Optimization: Your Language Model is Secretly a Reward Model" (DPO), NeurIPS 2023
3. Schulman et al., "Proximal Policy Optimization Algorithms" (PPO), 2017
4. Bai et al., "Constitutional AI: Harmlessness from AI Feedback" (Anthropic), 2022
5. Shao et al., "DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models" (GRPO), 2024
6. DeepSeek-AI, "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning", 2025
7. Yu et al., "DAPO: An Open-Source LLM Reinforcement Learning System", ByteDance, 2025
8. Ziegler et al., "Fine-Tuning Language Models from Human Preferences", 2019
9. Christiano et al., "Deep Reinforcement Learning from Human Preferences", NeurIPS 2017

## Cross-References

- [SFT →](sft.md) The training phase before alignment
- [Pre-training →](pretraining.md) The foundation model
- [Prompt Engineering →](prompt-engineering.md) How to use aligned models
- [Evaluation →](evaluation.md) Measuring alignment quality
- [Agent Safety →](../../ml/agents/safety.md) Safety considerations for AI systems
