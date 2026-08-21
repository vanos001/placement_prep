# Contrastive Learning

Contrastive learning is a paradigm for self-supervised representation learning where a model learns to embed similar inputs close together and dissimilar inputs far apart, without labels. It is the foundation of modern multimodal models (CLIP, ALIGN, FLAVA) and self-supervised image encoders (SimCLR, MoCo, BYOL). This page covers the contrastive loss, the negative sampling problem, the InfoNCE objective, and the production use cases.

## The Setup

Given an input X, create two "views" (augmentations) of it: `X_1` and `X_2`. These should be semantically similar (same content, different presentation). Also have many other inputs `Y_i` which are dissimilar.

The model embeds all of these into vectors. The training objective:

```text
Maximize: similarity(embed(X_1), embed(X_2))     ← positive pair
Minimize: similarity(embed(X_1), embed(Y_i))     ← negative pairs
```

The classic image example: take an image of a cat, apply random crops and color jitter to get `X_1` and `X_2`. These are the positive pair (same cat). Other images of dogs, cars, buildings are negatives.

## The InfoNCE Loss

The most widely used loss is InfoNCE (Information Noise Contrastive Estimation):

```text
For a positive pair (q, k+) and N negative pairs (q, k-):
  L = -log( exp(sim(q, k+) / τ) / sum_i exp(sim(q, k_i) / τ) )
```

where `sim(a, b)` is cosine similarity (or inner product), `τ` is a temperature parameter, and the denominator sums over the positive and all N negatives.

This looks like softmax cross-entropy: the positive should be the "winner" among all candidates. The temperature `τ` controls how sharp the softmax is:
- Low `τ` (e.g., 0.1): the model is pushed hard to separate positives from negatives.
- High `τ` (e.g., 1.0): the gradient is gentler.

Typical: `τ = 0.07` for image contrastive, `τ = 0.1` for text.

## The Negative Sampling Problem

The denominator of InfoNCE sums over all negatives. For a batch of N items, there are N-1 negatives (the other items in the batch are "negatives" for any given positive). The effective number of negatives is `N-1`.

For a useful signal, `N` should be large — at least 1K-10K. But:
- Per-batch N: limited by GPU memory (10K vectors of 768-dim bf16 = 15 GB).
- Per-machine N: limited by available GPUs.

Solutions:

1. **Memory bank** (MoCo): maintain a queue of recent embeddings as negatives. The queue can hold 65K embeddings (65K × 768 × 2 bytes = 96 MB).

2. **Global negatives via AllGather** (SimCLR with distributed training): across 8 GPUs, the per-batch negatives are 8 × N. With N=256, this gives 2K negatives.

3. **In-batch negatives** (CLIP): uses the per-batch negatives only, but with large batches (CLIP used batch=32K, giving 32K negatives per query).

## SimCLR

SimCLR (Chen et al., 2020) is the canonical image contrastive learning framework:

```python
# Augmentations: random crop + color jitter + Gaussian blur
def augment(image):
    image = random_resized_crop(image, size=224)
    image = color_jitter(image, brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1)
    if random() < 0.5:
        image = gaussian_blur(image, kernel=23)
    return image

# Training step
batch = load_batch()  # N images
x1 = [augment(img) for img in batch]
x2 = [augment(img) for img in batch]

h1 = encoder(x1)  # ResNet-50 features
h2 = encoder(x2)
z1 = projection(h1)  # MLP projection to 128-dim
z2 = projection(h2)

# InfoNCE loss with in-batch negatives
loss = info_nce_loss(z1, z2) + info_nce_loss(z2, z1)
```

SimCLR's key components:
- Strong augmentations (the recipe above matters).
- A projection head (MLP) that maps from the encoder's representation to a contrastive space.
- Large batch (default 4096 in the original paper).

## MoCo (Momentum Contrast)

MoCo (He et al., 2020) uses a momentum encoder and a queue:

```text
Query encoder f_q: trained via backprop.
Key encoder f_k: momentum-updated from f_q: f_k.params = 0.999 * f_k.params + 0.001 * f_q.params.

Queue of recent keys (dequeue old, enqueue new). Used as negatives.

Forward:
  q = f_q(X_1)
  k+ = f_k(X_2)  (the positive)
  k_queue = queue contents (negatives)

Loss = InfoNCE(q, k+, k_queue)
```

The momentum encoder ensures the keys are "stable" enough to act as effective negatives. The queue allows for many negatives (65K) without per-batch GPU memory overhead.

## CLIP

CLIP (Radford et al., 2021) is the canonical multimodal contrastive model:

```text
Image encoder (ResNet or ViT)
Text encoder (Transformer)
Batch of N (image, text) pairs

For each image i:
  positive text: the paired text (index i in the text batch)
  negatives: all other texts in the batch (N-1 of them)

For each text j:
  positive image: the paired image (index j in the image batch)
  negatives: all other images in the batch

Loss = InfoNCE(image_emb, text_emb) on both sides
```

CLIP's batch size of 32K gives 32K negatives per query. The training is on a massive dataset (400M image-text pairs from the web).

The trained model produces a unified embedding space for images and text: `embed_image(X)` and `embed_text(Y)` are in the same space, so cosine similarity between them is meaningful.

## Production Use Cases

### Zero-Shot Image Classification

CLIP's image encoder can classify images into any category without training:

```python
import clip
model, preprocess = clip.load("ViT-B/32")
image = preprocess(load_image("cat.jpg")).unsqueeze(0)
text = clip.tokenize(["a photo of a cat", "a photo of a dog", "a photo of a car"])

with torch.no_grad():
    image_features = model.encode_image(image)
    text_features = model.encode_text(text)
    
    similarities = (image_features @ text_features.T).softmax(dim=-1)
# similarities[0] = 0.95 (cat), [1] = 0.04 (dog), [2] = 0.01 (car)
```

### Image Search

Embed all images in a database; embed a query image; find the K nearest images.

### Multimodal RAG

For multimodal RAG: embed images and text into the same vector space. Query with text → retrieve relevant images. Query with image → retrieve relevant text.

### Face Recognition

Face recognition models (FaceNet, ArcFace) use a variant of contrastive learning called triplet loss. The "positive" is another image of the same person; the "negative" is an image of a different person.

## Common Pitfalls

1. **Using too few negatives.** With <1K negatives, the contrastive signal is weak. Use queues or distributed training.

2. **Forgetting that augmentations are critical.** Without strong augmentations, the model can cheat (e.g., color jitter is essential for SimCLR; without it, the model learns color histograms).

3. **Forgetting that temperature matters.** τ=0.07 is standard for image, but text/multimodal may need τ=0.05-0.5. Tune per task.

4. **Forgetting that the projection head is needed.** Without the projection, the encoder's representation is too high-level; contrastive learning fails to learn useful features.

5. **Forgetting that batch size matters more than epochs.** SimCLR with batch=4096 takes 1 epoch; with batch=256, it would need many more epochs to match quality.

6. **Forgetting that the encoder is the deliverable, not the projection.** After training, discard the projection head; use the encoder for downstream tasks.

## References

- Chen et al., "[SimCLR: A Simple Framework for Contrastive Learning of Visual Representations](https://arxiv.org/abs/2002.05709)" (ICML 2020)
- He et al., "[MoCo: Momentum Contrast for Unsupervised Visual Representation Learning](https://arxiv.org/abs/1911.05722)" (CVPR 2020)
- Radford et al., "[CLIP: Learning Transferable Visual Models From Natural Language Supervision](https://arxiv.org/abs/2103.00020)" (ICML 2021)
- Oord et al., "[Representation Learning with Contrastive Predictive Coding](https://arxiv.org/abs/1807.03748)" (2018) — InfoNCE
- [OpenAI CLIP GitHub repository](https://github.com/openai/CLIP)
- [SimCLR PyTorch implementation](https://github.com/sthalles/SimCLR)
- [MoCo PyTorch implementation](https://github.com/facebookresearch/moco)
