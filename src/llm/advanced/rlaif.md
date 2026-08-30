# RLAIF: Scaling Alignment Feedback with AI Raters

RLAIF (Reinforcement Learning from AI Feedback) keeps the RLHF training loop and swaps
out the one component that does not scale: the human labeler. A frozen LLM judge turns
out preference pairs at thousands of comparisons per minute for cents per pair, where
a human contractor manages roughly a hundred per day at dollars per pair. The reward
model, the PPO loop, and the KL penalty are unchanged; only the label source moves.
That swap is what let Anthropic train a harmless assistant without "any human labels
identifying harmful outputs" (Bai et al., 2022) -- and it inherited every bias of the
judge model you prompted.

## Position in the Alignment Stack

Each post-pretraining stage replaced a bottleneck in the stage before it:

```text
 pretrain            SFT                  RLHF                       RLAIF
    |                 |                    |                          |
 base LM  -->  instruction following  -->  human-labeled  -->  model-labeled
                                          preference pairs    preference pairs
                                      (~100 pairs/day,      (1000s/min, $0.01-
                                       $0.50-5.00/pair)      $0.10/pair)
```

Human preference annotation is slow, expensive, and inconsistent precisely on the
cases alignment cares most about: ambiguous harmfulness, long-form quality, and
specialist correctness where only experts can judge. Label budgets cap preference-pair
volume, which caps reward-model quality, which caps policy quality. RLAIF attacks the
bottleneck at its source; Constitutional AI (Bai et al., 2022) pushed it to its end.

Recap of the shared machinery, then this page stays focused on the label source (full
mechanics live in [RLHF & DPO](../llm-serving/rlhf.md)): RLHF fits a Bradley-Terry
reward model on human rankings with loss `-log sigma(r_chosen - r_rejected)`, then
optimizes the policy with PPO against that reward plus a KL penalty to the SFT
reference policy ([SFT](../llm-serving/sft.md)). RLAIF changes only step one.

## The RLAIF Pipeline

```text
 prompts --> policy (SFT) --> samples (y_A, y_B) --> AI annotator (frozen judge)
                                                       | pairwise ranking
                                                       | position-swap check
                                                       | CoT rationale
                                                       v
                                          AI labels: y_A > y_B
                                                       |
                     +---------------------------------+---------------------------------+
                     v                                                                   v
        reward model (Bradley-Terry fit)                       DPO on AI-labeled pairs (offline)
                     |
                     v
        PPO / GRPO with KL penalty to the reference policy
```

Stages mirror RLHF exactly; the differences worth engineering around sit inside the
annotator box: how pairs are ranked, and how the ranking is debiased. The DPO route
(judge once, optimize offline) is the cheap iteration loop; the online-vs-offline
trade is the same one [Inference Systems](inference-systems.md) covers for production.

### AI Annotator: Pairwise Ranking with Position-Swap Debiasing

The annotator is prompted to compare a pair and reason before deciding:

```text
You are a strict grader. Compare two assistant responses to the same request.
User request: <prompt>
Response A:   <response A>
Response B:   <response B>
Think step by step about which response is more helpful, accurate, and less harmful.
End with exactly one line: "Verdict: A" or "Verdict: B".
```

Two refinements, both used in Lee et al. (2023):

1. **Position-swap debiasing.** LLM judges are positionally biased: the verdict can
   shift when A and B are presented in the other order. Run each comparison twice,
   swapped, and keep the label only when both orders agree. A high flip rate signals
   indistinguishable responses or an under-specified rubric.
2. **Chain-of-thought rationales.** Critiquing against each principle before the
   verdict improves label quality and makes bad labels debuggable -- you can read why
   the judge chose what it chose.

## Constitutional AI: The Flagship Instance

Constitutional AI (Bai et al., 2022, arXiv:2212.08073) is RLAIF's most complete
realization: humans are removed from harmfulness labeling entirely; the only oversight
input is a short list of natural-language principles -- the "constitution":

1. **Red-team generation.** An initial model generates adversarial (harmful) queries
   and samples responses to them, building the harmfulness dataset without humans
   writing toxic prompts.
2. **Self-critique and revision.** The model critiques its own response against a
   principle, then rewrites the response per its own critique.
3. **Supervised phase.** Per the abstract, the process "involves both a supervised
   learning and a reinforcement learning phase": the team samples from an initial
   model, generates self-critiques and revisions, then fine-tunes on the revisions.
4. **RLAIF phase.** Pairs of responses are sampled from the fine-tuned model and
   judged by the model itself; a preference model is trained on this dataset of AI
   preferences, then RL uses it as the reward signal -- the paper names this "RL from
   AI Feedback" (RLAIF).

Verified abstract claims: the assistant is trained through self-improvement "without
any human labels identifying harmful outputs", with "the only human oversight ...
provided through a list of rules or principles"; the result is a harmless, non-evasive
assistant that engages with harmful queries by explaining the nature of the content
([Claude](../sota/claude.md) traces the model-line recipe).

## Reward-Model Overoptimization: The Goodhart Ceiling

Gao, Schulman, and Hilton measured the deepest problem in reward-based alignment in
"Scaling Laws for Reward Model Overoptimization" (arXiv:2210.10760): a synthetic setup
where "a fixed 'gold-standard' reward model plays the role of humans"; the gold score
is tracked as a policy optimizes the proxy via RL or best-of-n sampling. Findings:

- Goodhart, measured: "because the reward model is an imperfect proxy, optimizing its
  value too much can hinder ground truth performance, in accordance with Goodhart's
  law". In the RL runs the gold reward rises, peaks, then falls as KL keeps growing.
- The relationship "follows a different functional form depending on the method of
  optimization, and ... its coefficients scale smoothly with the number of reward
  model parameters". The RL case is fit with a broken power law: steady gold gains at
  small KL, accelerating losses past the peak.
- The levers are real: the paper varies reward-model dataset size, reward-model and
  policy parameter counts, and "the coefficient of the KL penalty added to the reward
  in the reinforcement learning setup". Larger reward models are harder to hack, and
  the KL coefficient is the production knob for how far the policy may travel.

## Feedback Quality: Where AI Raters Go Wrong

AI judges fail in structured, documented ways (Zheng et al., 2023, arXiv:2306.05685;
Panickssery et al., 2024, arXiv:2404.13076):

- **Position bias and label flipping**: verdicts change with presentation order;
  keep only swap-consistent labels, and track the flip rate as a reliability metric.
- **Length/verbosity bias**: judges prefer longer responses -- a reward-hacking
  channel that trains the policy toward bloat.
- **Self-preference / self-enhancement bias**: judges rate outputs from their own
  family higher; Panickssery et al. link this to recognizing one's own generations.

Is AI feedback as good as human feedback? Task-dependent. Lee et al. (2023) show that
across summarization, helpful dialogue, and harmless dialogue generation, "RLAIF
achieves comparable performance to RLHF" at a fraction of the per-label cost, and
GPT-4-as-a-judge reaches over 80% agreement with human raters (Zheng et al.). Those
are general domains with strong judges; with a weak judge, a specialist domain, or a
judge from the policy's own family, none of it transfers for free.

## RLHF vs RLAIF vs DPO-Style Direct Alignment

| Aspect | RLHF (human labels) | RLAIF (AI labels) | DPO-style direct |
|---|---|---|---|
| Label source | Human annotators | Frozen LLM judge | Existing pairs (any) |
| Annotation cost | ~$0.50-5.00/comparison | ~$0.01-0.10/comparison | None (reuses pairs) |
| Throughput | ~100 pairs/day per labeler | Thousands of pairs per minute | n/a (offline data) |
| Consistency | Rater fatigue, disagreement | Repeatable, but biased | Inherits label quality |
| Machinery | Reward model + PPO | RM + PPO, or DPO on AI pairs | Single loss (policy + ref) |
| Failure modes | Cost, rater noise | Judge bias, judge hacking | Overfits pairs, inherits bias |
| Best suited for | Novel preferences, safety | Scaling label volume | Cheap iteration, good pairs |

## Demo: Goodhart in Miniature

A one-dimensional policy has parameter `theta`, reference `theta = 0`; KL distance is
`theta**2`. The gold reward is concave with one peak; the proxy reward adds a spurious
cubic term that correlates with quality near the reference but is pure reward-model
hallucination far out. The optimizer ascends `r_proxy - beta * KL` (KL as only brake).

```python
# goodhart_toy.py -- reward-model overoptimization in miniature (stdlib only).
# KL(theta) = theta**2;  gold r(theta) = 1.50*theta - 0.40*theta**2 (peak at theta = 1.875)
# proxy r(theta) = gold r(theta) + 0.055*theta**3  (spurious curvature the RM hallucinated)
# Optimizer: gradient ascent on r_proxy - beta*KL, projected to a KL budget.
import math

def r_gold(theta):
    return 1.50 * theta - 0.40 * theta * theta

def r_proxy(theta):
    return r_gold(theta) + 0.055 * theta ** 3

def grad(theta, beta):
    return 1.50 - 0.80 * theta + 0.165 * theta * theta - 2.0 * beta * theta

def optimize(beta, budget, steps=1000, lr=0.10):
    theta, cap = 0.0, math.sqrt(budget)
    for _ in range(steps):
        theta += lr * grad(theta, beta)
        theta = max(-cap, min(cap, theta))
    return theta

print("Part 1: chase the raw proxy reward (beta = 0) under a growing KL budget")
print("KL budget |  theta | proxy_r | gold_r | gold status")
for budget in (1.0, 3.515625, 9.0, 36.0):
    th = optimize(0.0, budget)
    status = ("GOLD PEAK" if abs(th - 1.875) < 0.01 else
              "climbing" if th < 1.875 else "DECLINING")
    print("%9.3f | %6.3f | %7.3f | %6.3f | %s" % (budget, th, r_proxy(th), r_gold(th), status))

print("\nPart 2: the KL penalty beta as the knob (no budget cap)")
print("beta |  theta |  KL   | proxy_r | gold_r")
for beta in (0.0, 0.05, 0.10, 0.15, 0.50):
    th = optimize(beta, 400.0)  # budget 20**2: effectively uncapped
    print("%4.2f | %6.3f | %5.2f | %7.3f | %6.3f" % (beta, th, th*th, r_proxy(th), r_gold(th)))
```

Real output from the run above:

```text
Part 1: chase the raw proxy reward (beta = 0) under a growing KL budget
KL budget |  theta | proxy_r | gold_r | gold status
    1.000 |  1.000 |   1.155 |  1.100 | climbing
    3.516 |  1.875 |   1.769 |  1.406 | GOLD PEAK
    9.000 |  3.000 |   2.385 |  0.900 | DECLINING
   36.000 |  6.000 |   6.480 | -5.400 | DECLINING

Part 2: the KL penalty beta as the knob (no budget cap)
beta |  theta |  KL   | proxy_r | gold_r
0.00 | 20.000 | 400.00 | 310.000 | -130.000
0.05 | 20.000 | 400.00 | 310.000 | -130.000
0.10 |  2.727 |  7.44 |   2.231 |  1.116
0.15 |  1.912 |  3.66 |   1.790 |  1.406
0.50 |  0.909 |  0.83 |   1.074 |  1.033
```

Read the tables together. In Part 1 the proxy reward rises monotonically with the KL
budget while the gold reward peaks near `theta = 1.875` and then falls: the optimizer
faithfully maximizes a target that stopped measuring quality. In Part 2 the KL penalty
is the knob: too small and gold collapses at the cap; `beta = 0.15` finds the peak.

## Interview Angle

**Q: RLAIF removes humans from the loop. What new risks replace the ones it removes?**
A: Judge-bias risk replaces rater-noise risk: documented position, verbosity, and
self-preference biases, a reward model that can be Goodharted like any human-labeled
one, and -- if the judge is too close to the policy -- labels that silently reinforce
the policy's own quirks. Mitigate with swap filtering, CoT rubrics, a stronger judge
from a different model family, and held-out gold evaluation during RL.

## Cross-References

- [RLHF & DPO](../llm-serving/rlhf.md) -- the mechanics this page reuses
- [Fine-tuning (SFT)](../llm-serving/sft.md) -- the supervised stage before alignment
- [DPO](../../ml/rl/dpo.md) -- the direct-preference alternative for consuming AI labels
- [Inference Systems](inference-systems.md) -- alignment stages in production pipelines
- [Claude](../sota/claude.md) -- the Claude model line and its Constitutional AI sketch

## References

1. Bai, Y. et al., *Constitutional AI: Harmlessness from AI Feedback*, arXiv:2212.08073
   (2022) -- <https://arxiv.org/abs/2212.08073>
2. Gao, L., Schulman, J., Hilton, J., *Scaling Laws for Reward Model Overoptimization*,
   arXiv:2210.10760 (2022) -- <https://arxiv.org/abs/2210.10760>
3. Lee, H. et al., *RLAIF vs. RLHF: Scaling Reinforcement Learning from Human
   Feedback with AI Feedback*, arXiv:2309.00267 (2023) -- <https://arxiv.org/abs/2309.00267>
4. Zheng, L. et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*,
   arXiv:2306.05685 (2023) -- <https://arxiv.org/abs/2306.05685>
5. Panickssery, A. et al., *LLM Evaluators Recognize and Favor Their Own Generations*,
   arXiv:2404.13076 (2024) -- <https://arxiv.org/abs/2404.13076>
6. Ouyang, L. et al., *Training language models to follow instructions with human
   feedback* (InstructGPT), arXiv:2203.02155 (2022) -- <https://arxiv.org/abs/2203.02155>
7. Rafailov, R. et al., *Direct Preference Optimization: Your Language Model Is
   Secretly a Reward Model*, arXiv:2305.18290 (2023) -- <https://arxiv.org/abs/2305.18290>
