# ML Interview Questions

## Foundational Questions

### Q1: Explain the bias-variance tradeoff.
**Answer:** Bias measures how far predictions are from correct values (systematic error). Variance measures how much predictions vary across different training sets (sensitivity to data). Total error = bias² + variance + irreducible noise. High bias → underfitting (too simple). High variance → overfitting (too complex). The goal is to find the sweet spot.

**Follow-up:** How do you diagnose which one you have?
→ Plot learning curves. High bias: both train and val error are high. High variance: low train error, high val error.

### Q2: When would you use L1 vs L2 regularization?
**Answer:** L1 (Lasso) adds |w| penalty → produces sparse weights (feature selection). L2 (Ridge) adds w² penalty → produces small but non-zero weights (no feature selection). Use L1 when you suspect many irrelevant features. Use L2 when all features might be relevant. Elastic Net combines both.

### Q3: How does random forest reduce overfitting compared to a single decision tree?
**Answer:** Random forest uses bagging (bootstrap sampling) + random feature subsets at each split. This decorrelates trees, reducing variance without significantly increasing bias. Averaging many diverse trees cancels out individual overfitting. OOB error provides built-in validation.

### Q4: Explain cross-validation and when you'd use different types.
**Answer:** K-Fold: split data into K folds, train on K-1, validate on 1, rotate. Stratified: preserves class distribution in each fold (classification). Time Series: always forward-looking splits (no future data leakage). Leave-One-Out: K = n (expensive, small datasets). Use 5-fold for most cases, stratified for imbalanced data.

### Q5: What's the difference between precision and recall? When do you prioritize each?
**Answer:** Precision = TP/(TP+FP) — of predicted positives, how many correct? Recall = TP/(TP+FN) — of actual positives, how many found? Prioritize precision when false positives are costly (spam filtering). Prioritize recall when false negatives are costly (cancer detection). F1 balances both.

## Deep Learning Questions

### Q6: Explain the vanishing gradient problem and how to mitigate it.
**Answer:** In deep networks, gradients shrink exponentially through backpropagation (sigmoid/tanh activations compound small gradients). Mitigations: ReLU activation, residual connections (skip connections), batch normalization, proper weight initialization (He/Xavier), LSTM/GRU for RNNs.

### Q7: What is batch normalization and why does it help?
**Answer:** BN normalizes layer inputs to zero mean and unit variance across the batch, then applies learned scale and shift. Benefits: reduces internal covariate shift, allows higher learning rates, acts as mild regularization. Applied during training (batch stats) and inference (running averages). Alternatives: Layer Norm (transformers), Group Norm (small batches).

### Q8: Explain the attention mechanism.
**Answer:** Attention computes weighted sums of values based on query-key similarity. Attention(Q,K,V) = softmax(QK^T/√d_k) × V. Multi-head attention runs multiple attention in parallel to capture different relationships. Self-attention: Q, K, V from same sequence. Cross-attention: Q from one sequence, K,V from another.

### Q9: How does transfer learning work?
**Answer:** Pre-train on large dataset (ImageNet, large text corpus) → fine-tune on target task. Feature extraction: freeze pre-trained layers, train only new head. Fine-tuning: unfreeze some/all layers with small learning rate. Works because early layers learn general features (edges, textures, syntax), later layers are task-specific.

### Q10: Explain dropout and when to use it.
**Answer:** During training, randomly zero out neurons with probability p. At inference, use all neurons (scale by 1-p or use inverted dropout). Effect: prevents co-adaptation, acts as ensemble of sub-networks, implicit regularization. Use in fully connected layers (less common in modern architectures with batch norm).

## Transformer & LLM Questions

### Q11: Walk through the transformer architecture.
**Answer:** Encoder: input → embedding + positional encoding → [self-attention → add&norm → FFN → add&norm] × N. Decoder: same but with masked self-attention + cross-attention to encoder. Key innovation: parallelizable (vs sequential RNN), captures long-range dependencies via attention. Complexity: O(n²d) for sequence length n.

### Q12: What is KV cache and why is it important for LLM inference?
**Answer:** During autoregressive generation, each new token needs to attend to all previous tokens. Without KV cache, you'd recompute K and V for all tokens at each step (O(n²)). KV cache stores computed K, V tensors, so each step only computes Q for the new token. Speedup: 10-100x for long sequences. Trade-off: memory (scales with sequence length × layers × heads × d_head).

### Q13: Compare RLHF and DPO for LLM alignment.
**Answer:** RLHF: (1) train reward model on preference data, (2) optimize policy with PPO + KL penalty against reference. Complex, 3 models, can be unstable. DPO: directly optimize policy on preference pairs without explicit reward model. Simpler, 1 model, more stable. DPO loss = -log σ(β log π(y_w)/π_ref(y_w) - β log π(y_l)/π_ref(y_l)).

### Q14: Explain speculative decoding.
**Answer:** Use a small, fast "draft" model to generate candidate tokens. Then verify all candidates in parallel with the large "target" model. Accept tokens that match the target's distribution, reject and resample from the rest. Speedup: 2-3x (limited by draft model's acceptance rate). The output distribution is identical to the target model.

### Q15: What is RAG and what are its failure modes?
**Answer:** Retrieval-Augmented Generation: retrieve relevant documents → inject into prompt → generate answer. Failure modes: (1) retrieval misses relevant docs, (2) retrieval returns irrelevant docs (noise), (3) context window overflow, (4) LLM ignores retrieved context, (5) conflicting information in retrieved docs. Mitigations: reranking, hybrid search, query decomposition, citation verification.

## System Design for ML

### Q16: Design a recommendation system.
**Answer:** Two-tower model: user tower + item tower → dot product → ranking. Features: user history, item metadata, context. Training: implicit feedback (clicks, purchases) with contrastive loss. Serving: pre-compute item embeddings, ANN search (FAISS, ScaNN). Features: collaborative filtering (user-item matrix) + content-based (item features). Scale: sharding, caching, real-time feature updates.

### Q17: How do you handle data drift in production ML?
**Answer:** Monitor input feature distributions (statistical tests: KS test, PSI, KL divergence) and model performance metrics. Detect: compare recent data to training data distribution. Address: retrain model on recent data, use online learning, adjust features. Tools: Evidently AI, WhyLabs, custom dashboards. Alert on significant drift.

### Q18: Design an ML pipeline for fraud detection.
**Answer:** Data: transactions, user history, device info → Feature Store (real-time + batch features) → Model (ensemble: gradient boosting + neural network) → Serving (real-time scoring, <100ms) → Decision engine (threshold, rules) → Monitoring (drift, feedback loop). Key: handle class imbalance (SMOTE, class weights), minimize false negatives, explainability for regulators.

## Coding Questions

### Q19: Implement K-Means from scratch.
```python
import numpy as np

def kmeans(X, k, max_iters=100):
    # Random initialization
    centroids = X[np.random.choice(len(X), k, replace=False)]
    
    for _ in range(max_iters):
        # Assign clusters
        distances = np.linalg.norm(X[:, None] - centroids, axis=2)
        labels = np.argmin(distances, axis=1)
        
        # Update centroids
        new_centroids = np.array([X[labels == i].mean(axis=0) for i in range(k)])
        
        if np.allclose(centroids, new_centroids):
            break
        centroids = new_centroids
    
    return labels, centroids
```

### Q20: Implement a simple neural network forward pass.
```python
import numpy as np

def forward(X, W1, b1, W2, b2):
    # Layer 1 with ReLU
    z1 = X @ W1 + b1
    a1 = np.maximum(0, z1)  # ReLU
    
    # Layer 2 with softmax
    z2 = a1 @ W2 + b2
    exp_z = np.exp(z2 - np.max(z2, axis=1, keepdims=True))
    softmax = exp_z / exp_z.sum(axis=1, keepdims=True)
    
    return softmax
```

## Common Mistakes to Avoid

1. **Data leakage**: Using test data info during training (future data, target-derived features)
2. **Not handling class imbalance**: Using accuracy alone for imbalanced datasets
3. **Ignoring feature scaling**: Not scaling features for distance-based algorithms
4. **Overfitting to validation set**: Tuning hyperparameters until val score is perfect
5. **Not checking data quality**: Missing values, duplicates, label errors
6. **Using the wrong metric**: Accuracy for imbalanced data, MSE for classification
7. **Ignoring baseline**: Jumping to complex models without trying simple baselines

## Cross-References

- [ML Fundamentals](../ml/foundations/README.md)
- [Deep Learning](../ml/deep-learning/README.md)
- [Transformers](../ml/transformers/README.md)
- [ML System Design](../ml/system-design/README.md)
- [Interview Overview](./overview.md)

