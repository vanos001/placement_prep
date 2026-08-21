# Self-Supervised Learning

Self-supervised learning (SSL) is a paradigm where a model learns representations from unlabeled data by setting up a "pretext task" — a supervised learning problem constructed from the data itself. The labels are derived from the data's structure, not human annotation. This page covers the major pretext tasks (masked language modeling, contrastive learning, next-frame prediction), the fine-tuning paradigm, and the production use cases (foundation models for transfer learning).

## Why SSL Exists

Supervised learning requires labeled data. For most ML tasks, labels are expensive (human annotation, expert review). The bottleneck isn't compute — it's data labeling.

SSL's insight: the data itself contains supervisory signal. For language:
- The next word is a label for the previous words.
- A masked word is a label for the surrounding context.

For images:
- Two augmented views of the same image are "the same" (a contrastive label).
- Predictions of the next patch in a jigsaw puzzle.

SSL scales with the amount of unlabeled data, which is essentially infinite (the web has billions of images and trillions of text tokens).

## The Pretext Task Taxonomy

### Masked Language Modeling (MLM)

The canonical NLP pretext task (BERT, RoBERTa, GPT's early training):

```text
Input: "The capital of France is [MASK]."
Target: "Paris"

Loss: cross-entropy on the masked token
```

The model learns to predict masked tokens from context. After training, the encoder's representation is useful for downstream tasks (classification, NER, etc.).

### Causal Language Modeling (CLM)

Used for GPT-style models:

```text
Input: "The capital of France is"
Target: "Paris"

Loss: cross-entropy on the next token
```

The model learns to generate text by predicting the next token. After training, the model can generate text autoregressively.

### Contrastive Learning

Used for image and multimodal models (SimCLR, MoCo, CLIP). See [Contrastive Learning](./contrastive-learning.md).

### Masked Image Modeling (MIM)

Used for Vision Transformers (ViT, BEiT, MAE):

```text
Input: an image with patches masked (e.g., 75% of patches)
Target: the masked patches (reconstructed from the unmasked)

Loss: MSE on pixel values of masked patches
```

MAE (He et al., 2021) is the canonical MIM model. The encoder sees only 25% of patches; the decoder reconstructs the rest. The encoder's representation is the deliverable.

### Next-Frame Prediction

Used for video models (TimeSformer, VideoMAE):

```text
Input: frames 0, 1, 2, 3 of a video
Target: frame 4 (the next frame)

Loss: MSE on frame 4's pixels
```

The model learns video dynamics. Useful for action recognition, video classification.

## The Fine-Tuning Paradigm

SSL produces a "foundation model" with strong general representations. For specific tasks, fine-tune the foundation on labeled data:

```text
1. Pre-train on unlabeled data (no labels).
   - Cost: huge compute (CLIP used 256 V100-days for pre-training).
   - Output: foundation model with strong representations.

2. Fine-tune on task-specific labeled data (small amount, e.g., 10K samples).
   - Cost: small compute (single GPU, hours).
   - Output: task-specific model.
```

The economics: amortize the pre-training cost across many tasks. CLIP's $1M pre-training cost is justified by its use in 1000+ downstream applications.

## Self-Supervised + Supervised = Modern Deep Learning

Most modern ML pipelines are:

1. **Pre-train with SSL** on huge unlabeled data (text, images, video).
2. **Fine-tune** on small labeled data for the specific task.
3. **Inference**: deploy the fine-tuned model.

Examples:
- BERT: pre-trained on BookCorpus + Wikipedia (~3B tokens), fine-tuned on GLUE/SQuAD.
- ResNet-50: pre-trained on ImageNet (1M labeled images, but SSL-pretrained weights are common).
- GPT-4: pre-trained on web-scale text (no labels), fine-tuned with RLHF on human-preference data.

## The Scale Laws

Pre-training scale correlates with downstream quality. Kaplan et al. (2020) found that:
- Larger models improve quality, but the gain is sub-linear.
- More data improves quality, but the gain is sub-linear.
- Compute (model size × data size) is the main predictor.

For optimal scaling:
- For a given compute budget C, the optimal model size scales as C^0.6.
- The optimal data size scales as C^0.4.

This is the basis of LLM scaling: from GPT-2 (1.5B parameters) to GPT-4 (~1T parameters), compute scaled 1000×.

## Production Use Cases

### LLMs

GPT-4, Llama-3, Claude 3 are all SSL-pre-trained on web text. The fine-tuning (instruction tuning, RLHF) is a small fraction of the total compute.

### Vision Models

CLIP, ViT, MAE: pre-trained on large image-text or image datasets. Fine-tuned for specific tasks (image classification, detection, segmentation).

### Speech

Whisper (OpenAI 2022): pre-trained on 680K hours of audio (multilingual). Fine-tuned for transcription.

### Multimodal

ALIGN, FLAVA, ImageBind: pre-trained on image-text-audio-video pairs. Useful for cross-modal retrieval.

## Common Pitfalls

1. **Under-training the SSL phase.** Models with insufficient pre-training (e.g., only 10% of recommended compute) have weak representations. The fine-tuning can't fully recover.

2. **Choosing a bad pretext task.** Some pretext tasks don't transfer well. For example, colorization (predicting colors from grayscale) gives weaker representations than MIM.

3. **Forgetting that the SSL phase needs the same data distribution as the downstream task.** A model pre-trained on Wikipedia may not transfer to code (different vocabulary, structure).

4. **Forgetting that fine-tuning can destroy pre-trained features.** Fine-tuning with too high a learning rate (e.g., 1e-3) can overwrite the SSL-learned representations. Use lower learning rates (1e-5 to 5e-5).

5. **Forgetting that the SSL model's representation is the deliverable, not the pretext-task performance.** A model with high pretext-task accuracy but poor downstream transfer is a failure.

6. **Forgetting that SSL needs lots of data.** With <1M samples, SSL often underperforms supervised learning on the same data. SSL's advantage emerges at scale.

## References

- Devlin et al., "[BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://arxiv.org/abs/1810.04805)" (NAACL 2019)
- He et al., "[MAE: Masked Autoencoders Are Scalable Vision Learners](https://arxiv.org/abs/2111.06377)" (CVPR 2022)
- Kaplan et al., "[Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)" (2020)
- Brown et al., "[GPT-3: Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165)" (NeurIPS 2020)
- [Self-Supervised Learning tutorial (Lilian Weng)](https://lilianweng.github.io/posts/2021-08-28-self-supervised-comparison/)
- [Stanford CS25: Transformers United (SSL lectures)](https://web.stanford.edu/class/cs25/)
- [LWN: Self-supervised learning (2022)](https://lwn.net/Articles/905675/)
