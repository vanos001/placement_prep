# Model Compression: Pruning, Distillation, Low-Rank Decomposition

A modern transformer has billions of weights; an ImageNet ResNet-50 has ~25M; a MobileNet still has ~4M. None of these fit comfortably on a 256 KB microcontroller, a 4G-connected doorbell, or even a 4 GB phone running multiple models simultaneously. **Model compression** is the family of techniques that shrinks a model's storage footprint and inference cost while preserving accuracy. The four canonical methods — *pruning*, *knowledge distillation*, *low-rank decomposition*, and *quantization* — are orthogonal, and most production pipelines combine three of them.

Han, Mao and Dally's "Deep Compression" (ICLR 2016 best-paper honourable mention) showed that AlexNet could be shrunk 35× and VGG-16 49× with no loss of accuracy by chaining pruning → quantization → Huffman coding. That pipeline remains the template. This chapter dives into the three "structural" compressors; quantization has its own chapter at [Quantization-Aware Training](./quantization-aware-training.md).

## Why Compression Works: Over-Parameterisation

Two empirical facts make compression possible.

1. **The Lottery Ticket Hypothesis** (Frankle & Carbin, ICLR 2019 Best Paper). A randomly initialised dense network contains a small, lucky subnetwork ("the lottery ticket") that, trained in isolation from the original initialisation, reaches the dense model's accuracy. If a subnetwork of, say, 10% of weights suffices, the other 90% are removable.

2. **Singular value spectrum.** Weight matrices of trained networks have a few dominant singular values and a long tail. The matrix is *numerically low-rank* even when it is not shaped so — most of the energy lies in an `r ≪ min(m, n)` subspace, so it factorises cleanly.

Together these mean that 50–95% of a trained network's parameters are *redundant*: they don't move the loss much. Compression finds and removes them.

## Pruning

Pruning removes weights from a trained network. Three granularities, with very different hardware consequences.

```text
Pruning granularity (and what each buys you)
─────────────────────────────────────────────────────────────────
Unstructured     remove individual weights anywhere
                 -> sparse matrix, needs CSR/CSC kernels
                 -> near-zero speedup on dense BLAS/GEMM
                 -> 5-10x size reduction (CSR storage) is real

Structured       remove whole filters / channels / heads
                 -> still dense matrix, runs on any HW
                 -> direct wall-clock speedup, no special kernels
                 -> usually 2-4x before accuracy drops

Semi-structured  in each block of M weights, keep N non-zero (N:M)
                 -> NVIDIA 2:4 sparsity on Ampere (A100, RTX 30xx)
                 -> ~1.5-2x speedup with the structured-sparse GEMM
─────────────────────────────────────────────────────────────────
```

### Magnitude pruning

The simplest criterion: rank weights by absolute value, remove the smallest. Han et al. 2015 ("Learning both Weights and Connections for Efficient Neural Networks", NeurIPS) showed that simply thresholding the smallest-magnitude weights in each layer recovers a 9× compression on AlexNet with no accuracy loss — *provided* you fine-tune afterwards. The recipe is *iterative*:

```python
import torch

def magnitude_prune(weight: torch.Tensor, sparsity: float) -> torch.Tensor:
    """Set the smallest (sparsity)-fraction of weights to zero."""
    threshold = torch.quantile(weight.abs().flatten(), sparsity)
    mask = (weight.abs() > threshold).float()
    return weight * mask

def iterative_prune(model, target_sparsity, finetune_steps, train_loader):
    # Train -> prune 20% -> finetune -> prune 20% -> finetune -> ...
    cur_sparsity = 0.0
    while cur_sparsity < target_sparsity:
        cur_sparsity = min(target_sparsity, cur_sparsity + 0.2)
        for name, p in model.named_parameters():
            if "weight" in name:
                p.data = magnitude_prune(p.data, cur_sparsity)
        finetune(model, finetune_steps, train_loader)  # ~1 epoch
    return model
```

The `+0.2` step is critical. One-shot pruning to 90% sparsity destroys accuracy; 5 rounds of 20% with fine-tuning recover it. This is the iterative magnitude pruning (IMP) protocol that Frankle and Carbin used to find lottery tickets.

### First-order (Taylor) criteria

Better than raw magnitude: weights with small `weight · gradient` (`taylor = w · ∂L/∂w`) contribute little to the loss if removed. The Taylor criterion is what NVIDIA's `apex` and PyTorch's `torch.nn.utils.prune` use, and it consistently beats magnitude at high sparsity (80%+). Molchanov et al. (ICLR 2017) showed Taylor pruning matches or beats the more elaborate saliency criteria at a fraction of the cost.

### The Lottery Ticket Hypothesis in practice

Frankle and Carbin asked: instead of pruning a *trained* model and fine-tuning, can we *reset* the surviving weights to their original initialisation and retrain from scratch? Surprisingly, yes — for IMP with iterative mask training, the pruned architecture + initial weights ("the ticket") reaches dense-model accuracy on MNIST/CIFAR/ImageNet at 50–90% sparsity. A randomly re-initialised network of the same *architecture* does not.

The follow-up "Rethinking the Value of Network Pruning" (Liu et al., ICLR 2019) showed that for *structured* pruning the winning-ticket effect largely disappears — retraining from scratch on the pruned architecture matches fine-tuning. So:

- *Unstructured* pruning: fine-tune the pruned model, don't retrain from scratch (the mask encodes information you don't want to lose).
- *Structured* pruning: retrain from scratch on the pruned architecture; both work, and starting fresh is simpler.

### 2:4 structured sparsity on Ampere

NVIDIA Ampere added hardware support for *N:M sparsity* — every block of 4 weights contains exactly 2 non-zeros, encoded in a 2-bit mask per quad. The `cublasLt` kernel then does a 2×-effective-density GEMM at near-full dense speed. The constraint is strict (50% sparsity in groups of 4), but `torch.sparse.to_sparse_semi_structured` will repack a magnitude-pruned weight into the right layout:

```python
# PyTorch 2.x: 2:4 semi-structured sparsity on NVIDIA Ampere or later
from torch.sparse import to_sparse_semi_structured
W = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
W = magnitude_prune(W, 0.5)        # 50% zeros
W_sp = to_sparse_semi_structured(W) # re-pack to 2:4
y = torch.nn.functional.linear(x, W_sp)  # cuBLASLt 2:4 path
```

This gives a 1.5–1.7× wall-clock speedup at zero accuracy cost (the freed-up FLOPs are real; the sparsity is regular enough that the dense ops path stays efficient). Ada, Hopper, and Blackwell all inherit the 2:4 unit.

## Knowledge Distillation

Hinton, Vinyals and Dean's "Distilling the Knowledge in a Neural Network" (NeurIPS Deep Learning Workshop 2014, arXiv 2015) introduced the modern formulation: train a small *student* to match a large *teacher*'s output distribution, not just the hard labels. The teacher's "soft" outputs encode **dark knowledge** — class-similarity structure that hard labels throw away. A teacher that produces `[0.7, 0.2, 0.08, 0.02]` for `[cat, dog, car, frog]` is telling the student "dog is more cat-like than car", information absent from `[1, 0, 0, 0]`.

### The loss

Distillation scales the teacher's logits by a *temperature* `T` before softmax — higher `T` reveals more of the dark knowledge:

```text
softmax_T(z)_i = exp(z_i / T) / Σ_j exp(z_j / T)

L = α · CE(y_hard, σ(z_student))         # hard-label loss
  + (1-α) · T² · KL(softmax_T(z_teacher), softmax_T(z_student))
                                                            # distill loss
```

The `T²` factor rescales the gradients: since softmax with high `T` has small derivatives (`~1/T`), the KL term's gradient magnitude scales as `1/T²` — multiplying by `T²` keeps it on the same scale as the CE loss regardless of `T`. Typical settings: `T ∈ [3, 20]`, `α ∈ [0.1, 0.5]`.

```python
def distillation_step(teacher, student, x, y, T=4.0, alpha=0.5):
    with torch.no_grad():
        t_logits = teacher(x) / T
    s_logits = student(x) / T

    # KL divergence between softened distributions
    loss_kd = torch.nn.functional.kl_div(
        input=torch.log_softmax(s_logits, dim=-1),
        target=torch.softmax(t_logits, dim=-1),
        reduction='batchmean') * (T * T)

    # Hard-label CE on the *temperature-scaled* logits
    loss_ce = torch.nn.functional.cross_entropy(s_logits * T, y)
    loss = alpha * loss_ce + (1 - alpha) * loss_kd
    loss.backward()
    return loss
```

A few practical wrinkles:

- Use the student's pre-softmax logits for the CE loss (`s_logits * T`), not the post-softmax — temperature-scaling the CE stabilises training.
- *Hint-based* distillation (FitNets, Romero et al. 2015) adds a term matching a teacher's penultimate layer to a projection of the student's penultimate layer. This is what makes DistilBERT (Sanh et al. 2019) reach 97% of BERT's GLUE score at 40% the parameter count and 60% faster inference.
- *Logits-only distillation* scales to LLMs — Anthropic's Constitutional AI, OpenAI's `gpt-3.5-turbo-instruct` lineage and Tulu's distillation recipes all distil large models into smaller ones via pure logits matching. Llama-3-70B → 8B-style students use this; `T = 7` is typical.

Distillation is *not* "training a small model on the teacher's outputs" — that would propagate only the argmax, losing all dark knowledge. The KL on softened distributions is the entire point.

## Low-Rank Decomposition

A weight matrix `W ∈ R^(m × n)` of rank `r` can be factored as `W = U · V` with `U ∈ R^(m × r)`, `V ∈ R^(r × n)`. If `r ≪ min(m, n)`, storage drops from `m·n` to `r·(m + n)` and the matmul from `O(m·n)` to `O(r·(m+n))` FLOPs.

The catch: trained weight matrices are *not* exactly low-rank. But their *singular value spectra* decay fast — the top-k captures most of the energy, so truncation works.

### SVD truncation

```python
def svd_compress(weight: torch.Tensor, rank: int):
    """W ≈ U_k Σ_k V_k^T  ->  U_k @ (Σ_k V_k^T)
    Stores two matrices instead of one. Drops FLOPs by ~r/min(m,n)."""
    U, S, Vh = torch.linalg.svd(weight.float(), full_matrices=False)
    U_k = U[:, :rank]                                # (m, r)
    SV_k = (Vh[:rank, :] * S[:rank].unsqueeze(-1))   # (r, n)
    return U_k, SV_k

# Replace nn.Linear(4096, 4096) [16.7M params] with two layers:
#   nn.Linear(4096, 512) -> nn.Linear(512, 4096)  [4.2M params, 4x fewer]
```

Two issues:

1. The factorisation is *post-hoc*; you typically re-fine-tune the factored form. Without fine-tuning, top-k SVD loses 2–5% accuracy.
2. SVD is per-matrix; for convolutional weights `(out_ch, in_ch, k_h, k_w)` you have to unfold or use *Tucker decomposition*.

### Tucker decomposition

Tucker decomposes a tensor along each mode independently:

```text
W ∈ R^(I_out × I_in × k_h × k_w)
W ≈ core × A_1 × A_2 × A_3 × A_4

where core ∈ R^(r_out × r_in × r_h × r_w), each A_i ∈ R^(I_i × r_i).
Storage: Π r_i + Σ I_i r_i   (vs Π I_i)
```

For a typical conv `W ∈ R^(256, 256, 3, 3) = 589k` weights, Tucker with ranks `(64, 64, 3, 3)` gives `64·64·9 + 256·64·4 ≈ 102k` weights — ~5.8× smaller. The original paper (Kim et al., CVPR 2016) and the follow-up CP-decomposition (Lebedev et al., 2015) showed this with no accuracy loss on ImageNet after fine-tuning.

A modern variant: the LoRA paper (Hu et al., ICLR 2022) is, mechanically, *SVD-Tucker applied to the weight update* — `ΔW = A · B` with `A, B` learned — and it is now the standard efficient-fine-tuning technique for LLMs. The fact that low-rank *updates* work better than low-rank *weights* is itself evidence that the trained network moves along a low-dimensional manifold during fine-tuning.

## When to Use Which

| Technique | Storage win | Latency win | Accuracy risk | Setup cost | Best for |
|---|---|---|---|---|---|
| Magnitude pruning (unstructured) | 5–10× | ~1× (needs sparse kernels) | low at <80% sparsity | one fine-tune pass | LLMs (compress via sparse storage), research |
| Structured pruning (channels) | 2–4× | 2–4× direct | moderate, needs retrain | expensive retrain | CNNs on phones, edge |
| 2:4 semi-structured | 1.5× size | 1.5–1.7× on Ampere | low | one fine-tune pass | NVIDIA GPU inference |
| Knowledge distillation | 2–10× (arch-dependent) | 2–10× | low if data is plentiful | full training run | changing architecture, e.g. BERT→DistilBERT |
| Low-rank (SVD/Tucker) | 2–4× | 2–4× on big matmuls | low with fine-tune | one fine-tune pass | big FC/embedding layers, LLMs |
| Quantization (INT8) | 4× | 3–4× | low with QAT | retrain (QAT) or calibration (PTQ) | universal, the cheapest win |

Rules of thumb:

1. **Start with quantization.** It is the highest-ratio, lowest-complexity win; almost every deployed model is INT8. See [Quantization-Aware Training](./quantization-aware-training.md).
2. **Add distillation when changing architecture.** If you are going MobileNet, distil from the teacher you trained. The student gets the teacher's *intuition* for free.
3. **Add pruning when storage/latency is still over budget.** Structured for edge, 2:4 for NVIDIA GPUs, unstructured only when you control the inference stack (e.g. with Neural Magic's sparse kernels).
4. **Add low-rank for the biggest layers.** A 4096×4096 attention feed-forward compresses 4× with SVD and barely moves accuracy; an embedding table of 100k×768 compresses 10× with the same SVD.
5. **Don't ship without measuring on the target hardware.** A pruned ResNet that is 2× smaller can be *slower* on a CPU without structured-sparse BLAS. Always profile end-to-end on the deployment device.

The canonical full pipeline (Han et al. 2016, "Deep Compression") stacks pruning → quantization → Huffman coding. The first two together deliver 25–50× on standard CNNs. A modern equivalent on a BERT-base: structured prune 30% → distil into a 6-layer student → INT8 QAT → 4× smaller, 4× faster, within 1% of original F1.

## References

- Song Han, Huizi Mao, William J. Dally, "[Deep Compression: Compressing Deep Neural Networks with Pruning, Trained Quantization and Huffman Coding](https://arxiv.org/abs/1510.00149)" (ICLR 2016)
- Song Han, Jeff Pool, John Tran, William J. Dally, "[Learning both Weights and Connections for Efficient Neural Networks](https://arxiv.org/abs/1506.02626)" (NeurIPS 2015)
- Jonathan Frankle, Michael Carbin, "[The Lottery Ticket Hypothesis: Finding Sparse, Trainable Neural Networks](https://arxiv.org/abs/1803.03635)" (ICLR 2019 Best Paper)
- Geoffrey Hinton, Oriol Vinyals, Jeff Dean, "[Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531)" (NeurIPS Deep Learning Workshop 2014)
- Victor Sanh, Lysandre Debut, Julien Chaumond, Thomas Wolf, "[DistilBERT, a distilled version of BERT: smaller, faster, cheaper and lighter](https://arxiv.org/abs/1910.01108)" (NeurIPS 2019 Workshop)
- Adriana Romero, Nicolas Ballas, Samira Ebrahimi Kahou, et al., "[FitNets: Hints for Thin Deep Nets](https://arxiv.org/abs/1412.6550)" (ICLR 2015) — hint-based distillation
- Yong-Deok Kim, et al., "[Compression of Deep Convolutional Neural Networks under Fast Unitary Transforms](https://arxiv.org/abs/1511.06477)" (CVPR 2016) — Tucker decomposition
- Edward J. Hu, et al., "[LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685)" (ICLR 2022)
- Zhuang Liu, Mingjie Sun, et al., "[Rethinking the Value of Network Pruning](https://arxiv.org/abs/1810.05270)" (ICLR 2019)
- Pavlo Molchanov, Stephen Tyree, et al., "[Pruning Convolutional Neural Networks for Resource Efficient Inference](https://arxiv.org/abs/1611.06440)" (ICLR 2017) — Taylor criterion
- [PyTorch pruning tutorial](https://pytorch.org/tutorials/intermediate/pruning_tutorial.html)
- [NVIDIA 2:4 structured sparsity documentation](https://docs.nvidia.com/deeplearning/frameworks/inference-performance-guide/index.html#structured-sparse)

## Cross-References

- [Quantization-Aware Training](./quantization-aware-training.md) — INT8 training and inference
- [Edge Inference](./edge-inference.md) — deployment targets for compressed models
- [TinyML](./tinyml.md) — extreme compression for microcontrollers
- [Distillation](./distillation.md) — companion survey page on distillation
- [Pruning](./pruning.md) — companion page on pruning methods
- [Compression](./compression.md) — overview page
