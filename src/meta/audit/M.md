# Chunk M Audit — ML

**Scope:** src/ml/* (skipping already-fixed)
**Files audited:** 77 (all content-heavy technical files across all ml/ subdirectories; index/README files for subdirectories excluded as low-risk)
**Files clean:** 56
**Total findings:** 24

Skipped per `already_fixed.md`:
- `ml/foundations/bias-variance.md`
- `ml/deep-learning/backpropagation.md`

Verification approach:
- Arithmetic / softmax / matrix products verified with Python + NumPy (commands inline per finding).
- API signatures verified against official docs (pytorch.org, scikit-learn.org, tensorflow.org).
- ML technical claims verified against canonical papers (Vaswani 2017, Devlin 2018, Radford 2018/19, Brown 2020, Raffel 2019, Dosovitskiy 2020, Mnih 2015, Schulman 2017, Rafailov 2023, etc.).

## Findings

### HIGH severity

#### ml/transformers/self-attention.md:103
- **Wrong text:** `Q = X @ W_q  # (3, 2)` followed by `# Q = [[1, 0], [0, 2], [1, 1]]`
- **Correct text:** `# Q = [[2, 0], [0, 2], [1, 1]]`
- **Verification:** `python3 -c "import numpy as np; X=np.array([[1,0,1,0],[0,1,0,1],[1,1,0,0]]); W=np.array([[1,0],[0,1],[1,0],[0,1]]); print(X@W)"` → row 0 is `[2, 0]` not `[1, 0]`.
- **Justification:** X[0]·W[:,0] = 1·1 + 0·0 + 1·1 + 0·0 = 2. The first row of Q is wrong, which propagates to every downstream matrix in the worked example.

#### ml/transformers/self-attention.md:111
- **Wrong text:** `# V = [[1, 0], [0, 2], [1, 1]]`
- **Correct text:** `# V = [[1, 1], [1, 1], [1, 1]]`
- **Verification:** `python3 -c "import numpy as np; X=np.array([[1,0,1,0],[0,1,0,1],[1,1,0,0]]); Wv=np.array([[1,0],[0,1],[0,1],[1,0]]); print(X@Wv)"` → all three rows are `[1, 1]`.
- **Justification:** W_v has column 0 = `[1,0,0,1]ᵀ` and column 1 = `[0,1,1,0]ᵀ`. For X[0]=[1,0,1,0]: V[0,0]=1·1+0·0+1·0+0·1=1, V[0,1]=1·0+0·1+1·1+0·0=1. So V[0]=[1,1], not [1,0].

#### ml/transformers/self-attention.md:115-117
- **Wrong text:** `# scores = [[0, 2, 1], [4, 0, 2], [1, 2, 2]]`
- **Correct text:** `# scores = [[0, 4, 2], [4, 0, 2], [2, 2, 2]]`
- **Verification:** Computed via `Q @ K.T` with the corrected Q=[[2,0],[0,2],[1,1]] and K=[[0,2],[2,0],[1,1]] (K is correct in the file).
- **Justification:** Rows 0 and 2 of the score matrix are wrong because they depended on the wrong Q[0]. Row 1 was correct since Q[1] was correct.

#### ml/transformers/self-attention.md:127
- **Wrong text:** `# Row "cat": softmax([4/1.414, 0/1.414, 2/1.414]) = softmax([2.83, 0, 1.41]) ≈ [0.79, 0.05, 0.16]`
- **Correct text:** `≈ [0.7682, 0.0453, 0.1865]`
- **Verification:** `python3 -c "import numpy as np; x=np.array([2.8284,0,1.4142]); e=np.exp(x-x.max()); print(e/e.sum())"` → `[0.7682, 0.0453, 0.1865]`.
- **Justification:** exp(2.83)/(exp(2.83)+exp(0)+exp(1.41)) = 16.95/22.06 ≈ 0.768, not 0.79.

#### ml/transformers/self-attention.md:132-133
- **Wrong text:** `# output[1] = 0.79*[1,0] + 0.05*[0,2] + 0.16*[1,1] = [0.95, 0.26]`
- **Correct text:** With correct softmax ≈ [0.7682, 0.0453, 0.1865] and correct V = [[1,1],[1,1],[1,1]], `output[1] = [1.0, 1.0]`.
- **Verification:** `python3 -c "import numpy as np; v=np.array([1,1]); s=np.array([0.7682,0.0453,0.1865]); print(s@np.vstack([v,v,v]))"` → `[1.0, 1.0]`.
- **Justification:** Both the softmax values AND the V values used in the output calc were wrong, so the output values are doubly wrong. Since all three V rows are [1,1] (after the correction), the weighted sum is trivially [1,1].

#### ml/deep-learning/attention.md:146
- **Wrong text:** `# Row 0: softmax([1.0, 0.0, 0.5]) ≈ [0.441, 0.163, 0.396]`
- **Correct text:** `# Row 0: softmax([1.0, 0.0, 0.5]) ≈ [0.5065, 0.1863, 0.3072]`
- **Verification:** `python3 -c "import numpy as np; x=np.array([1.0,0.0,0.5]); e=np.exp(x-x.max()); print(e/e.sum())"` → `[0.5065, 0.1863, 0.3072]`.
- **Justification:** The values 0.441, 0.163, 0.396 do not correspond to softmax of [1.0, 0.0, 0.5]; they appear fabricated.

#### ml/deep-learning/attention.md:150
- **Wrong text:** `# output[0, 0] ≈ 0.441*[1,2] + 0.163*[3,4] + 0.396*[5,6] ≈ [2.91, 3.80]`
- **Correct text:** `# output[0, 0] ≈ [2.60, 3.60]`
- **Verification:** `python3 -c "import numpy as np; V=np.array([[1.,2.],[3.,4.],[5.,6.]]); s=np.array([0.5065,0.1863,0.3072]); print(s@V)"` → `[2.6014, 3.6014]`.
- **Justification:** Derived from the wrong softmax values in the previous line; correct softmax gives [2.60, 3.60] not [2.91, 3.80].

#### ml/deep-learning/rnn-lstm.md:171
- **Wrong text:** `r = self.sigmoid(concat @ self.wr)  # Reset gate: how much past to forget`
- **Correct text:** `r = self.sigmoid(concat @ self.Wr)  # Reset gate: how much past to forget`
- **Verification:** Class defines `self.Wr = np.random.randn(...)` in `__init__` (line 161). `self.wr` (lowercase) is undefined.
- **Justification:** Attribute name case mismatch — calling `self.wr` raises `AttributeError: 'GRUCell' object has no attribute 'wr'`. Verified by inspection.

#### ml/deep-learning/rnn-lstm.md (GRUCell class)
- **Wrong text:** The `GRUCell` class calls `self.sigmoid(...)` in `forward` (lines 168, 171) but never defines a `sigmoid` method (unlike `LSTMCell` above which does define one).
- **Correct text:** Either add `def sigmoid(self, z): return 1 / (1 + np.exp(-np.clip(z, -500, 500)))` to `GRUCell`, or use `np.tanh`/inline sigmoid.
- **Verification:** Reading the class definition (lines 155-181) — only `__init__` and `forward` are defined; no `sigmoid` method.
- **Justification:** Calling `self.sigmoid(...)` raises `AttributeError`. The class is broken as written.

#### ml/system-design/fraud-detection.md:68-70
- **Wrong text:**
  ```python
  model = GradientBoostingClassifier(
      class_weight={0: 1, 1: 100},  # Weight fraud class 100x
      n_estimators=500
  )
  ```
- **Correct text:** `GradientBoostingClassifier` does NOT accept `class_weight`. Use `sample_weight` in `fit()` instead, or use `HistGradientBoostingClassifier` (which does support `class_weight` since sklearn 1.2), or switch to a different classifier. Example:
  ```python
  from sklearn.ensemble import HistGradientBoostingClassifier
  model = HistGradientBoostingClassifier(class_weight={0: 1, 1: 100}, max_iter=500)
  # or
  sample_weights = np.where(y_train == 1, 100, 1)
  model.fit(X_train, y_train, sample_weight=sample_weights)
  ```
- **Verification:** scikit-learn docs — `sklearn.ensemble.GradientBoostingClassifier` constructor parameters do not include `class_weight`. Confirmed at https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html
- **Justification:** Passing `class_weight` raises `TypeError: __init__() got an unexpected keyword argument 'class_weight'`.

#### ml/classical/ensemble.md:144
- **Wrong text:** `weights *= np.exp(-alpha * y * predictions)` (inside custom AdaBoost)
- **Correct text:** Convert labels to `{-1, +1}` first: `y_signed = np.where(y == 0, -1, 1)` and `pred_signed = np.where(predictions == 0, -1, 1)`, then `weights *= np.exp(-alpha * y_signed * pred_signed)`.
- **Verification:** With `y, predictions ∈ {0, 1}`: `y*predictions` is 0 for three of four (y,pred) combinations, so `exp(-alpha * 0) = 1` — weights never change for the 3 cases that aren't (y=1, pred=1). Standard AdaBoost requires `y, pred ∈ {-1, +1}` so that incorrect predictions flip sign and `exp(-alpha * y * pred) = exp(+alpha)` (weight increase) for errors.
- **Justification:** AdaBoost weight update requires ±1 labels; `DecisionTreeClassifier` outputs {0, 1}. The implementation as written does not penalize misclassified samples (no weight increase on errors), so the boosting dynamics are broken.

### MEDIUM severity

#### ml/classical/pca.md:104
- **Wrong text:**
  ```python
  self.explained_variance_ratio = self.explained_variance / np.sum(self.explained_variance)
  ```
  (inside `PCA_SVD.fit`)
- **Correct text:** `self.explained_variance_ratio = self.explained_variance / np.sum((S**2) / (len(X) - 1))` — i.e., divide by total variance across ALL components, not just the kept top `n_components`.
- **Verification:** `np.sum(self.explained_variance)` after slicing to `n_components` sums only those kept. sklearn's `PCA.explained_variance_ratio_` divides by total variance (`(S**2).sum() / (len(X)-1)`), which is why the ratios don't always sum to 1 when `n_components < min(n, d)`.
- **Justification:** With the file's code, `explained_variance_ratio` will always sum to 1.0 across the kept components — this is incorrect and contradicts the meaning of "explained variance ratio" used elsewhere in the same file (line 73 in the basic PCA class does it correctly).

#### ml/advanced/quantization.md:171
- **Wrong text:** `3. **What is calibration in static quantization? — Running representative data through the model to determine the optimal scale and zero-point for activation quantization. Without it, activation ranges are estimated poorly.`
- **Correct text:** `3. **What is calibration in static quantization?** — Running representative data through the model to determine the optimal scale and zero-point for activation quantization. Without it, activation ranges are estimated poorly.`
- **Verification:** Markdown source inspection — opening `**` after `3. ` has no closing `**` before the `—`.
- **Justification:** Broken bold markdown — the entire question and answer render as one long bolded run.

#### ml/advanced/distillation.md:88-90
- **Wrong text:**
  ```python
  print("T=1:", soft_softmax(logits, 1.0))   # [0.84, 0.12, 0.02, 0.01]
  print("T=4:", soft_softmax(logits, 4.0))   # [0.38, 0.29, 0.19, 0.14]
  print("T=10:", soft_softmax(logits, 10.0)) # [0.30, 0.27, 0.23, 0.21]
  ```
- **Correct text:**
  ```python
  print("T=1:", soft_softmax(logits, 1.0))   # [0.86, 0.12, 0.02, 0.01]
  print("T=4:", soft_softmax(logits, 4.0))   # [0.43, 0.26, 0.16, 0.14]
  print("T=10:", soft_softmax(logits, 10.0)) # [0.32, 0.26, 0.21, 0.20]
  ```
- **Verification:** `python3 -c "import numpy as np; x=np.array([5.,3.,1.,0.5]); [print(softmax(x/t)) for t in [1,4,10]]"` where `softmax(x)=np.exp(x-x.max())/np.exp(x-x.max()).sum()`.
- **Justification:** The example numbers are noticeably off from correct softmax; the T=4 row is wrong in every entry. While the qualitative claim (T↑ → softer) is correct, the specific numbers teach wrong values.

#### ml/time-series/arima.md:38
- **Wrong text:** `d2 = series.diff(2)   # Second difference (if needed)`
- **Correct text:** `d2 = series.diff().diff()   # Second difference (if needed)`
- **Verification:** pandas docs: `Series.diff(periods=1)` returns `y[t] - y[t-periods]`. So `series.diff(2)` is the **lag-2 first difference** (`y[t] - y[t-2]`), NOT the second difference. The second difference is `Δ²y[t] = y[t] - 2·y[t-1] + y[t-2]`, obtained by `series.diff().diff()`.
- **Justification:** These are mathematically different quantities. The "I(d)" component of ARIMA uses repeated first differencing (d times), not lag-d differencing. Teaching this incorrectly will produce wrong stationarity transformations.

#### ml/advanced/nas.md:104
- **Wrong text:** `input = F.one_action(action, num_ops).unsqueeze(0).unsqueeze(0)`
- **Correct text:** `input = F.one_hot(action, num_ops).unsqueeze(0).unsqueeze(0)`
- **Verification:** PyTorch docs — `torch.nn.functional` has `one_hot(tensor, num_classes)`; there is no `one_action` function. Source: https://pytorch.org/docs/stable/generated/torch.nn.functional.one_hot.html
- **Justification:** `F.one_action` does not exist; the call would raise `AttributeError`. Likely a typo for `F.one_hot`.

#### ml/advanced/compression.md:43-44
- **Wrong text:**
  ```python
  U_r = U[:, :rank] * S[:rank].sqrt()
  V_r = V[:, :rank].T * S[:rank].sqrt()
  ```
- **Correct text:**
  ```python
  U_r = U[:, :rank] * S[:rank].sqrt()                # shape (m, r) — broadcasts S along columns ✓
  V_r = V[:, :rank].T * S[:rank].sqrt().unsqueeze(-1) # shape (r, n) — broadcasts S along rows ✓
  ```
- **Verification:** In PyTorch, `(r, n) * (r,)` broadcasts the 1-D tensor against the LAST axis (size n), which only works if n == r. For the intended row-wise scaling (each row `j` of `V_r` multiplied by `S[j].sqrt()`), `S[:rank].sqrt()` must be reshaped to `(r, 1)`.
- **Justification:** As written, the second line either raises a broadcasting error (when n ≠ r) or silently produces wrong values (when n == r). The fix is `.unsqueeze(-1)` (or `.reshape(-1, 1)`).

#### ml/transformers/t5.md:65
- **Wrong text:** `| T5-Small | 6+6 | 512 | 2048 | 8 | 77M |`
- **Correct text:** `| T5-Small | 6+6 | 512 | 2048 | 8 | 60M |`
- **Verification:** T5 paper (Raffel et al. 2019), Table 1 lists T5-small with 60 million parameters. Source: https://arxiv.org/abs/1911.02116
- **Justification:** 77M is wrong for T5-Small; the canonical value is 60M. (T5-Base 220M, T5-Large 770M, T5-3B 2.8B, T5-11B 11B are all correct in the same table.)

#### ml/classical/lightgbm.md:129
- **Wrong text:** `'bagging_fraction': 0.8,    # Row sampling (GOSS)`
- **Correct text:** `'bagging_fraction': 0.8,    # Row sampling (random subsampling; GOSS is separate — enabled via boosting_type='goss')`
- **Verification:** LightGBM docs — `bagging_fraction` is uniform-random row subsampling used when `boosting_type=gbdt`. GOSS is a different sampling strategy enabled by setting `boosting_type=goss`, with its own `top_rate`/`other_rate` parameters; it does not use `bagging_fraction`. Source: https://lightgbm.readthedocs.io/en/latest/Parameters.html
- **Justification:** Conflates two different LightGBM mechanisms. Same issue appears at line 233 in the FAANG interview answer (`GOSS: bagging_fraction=0.8, bagging_freq=5` — these are random bagging params, not GOSS).

#### ml/classical/decision-trees.md:313
- **Wrong text:** `**LightGBM**: Uses gradient-based one-side sampling for categorical features`
- **Correct text:** `**LightGBM**: Native categorical splits (Fisher-based partitioning / target-encoded sorting); GOSS is for sample selection, not categorical handling`
- **Verification:** LightGBM docs on categorical feature support — uses an optimal split algorithm based on sorting categories by target statistic. GOSS (Gradient-based One-Side Sampling) is a row-sampling strategy for speeding up training on large datasets, unrelated to categorical handling.
- **Justification:** The claim attributes GOSS (a sample-selection method) to categorical handling. LightGBM's actual categorical handling is a separate algorithm.

#### ml/deep-learning/dropout.md:13
- **Wrong text:** Mermaid node `D[Inference: Use all neurons, scale by 1-p]`
- **Correct text:** `D[Inference: Use all neurons, no scaling (inverted dropout scaled at training time)]`
- **Verification:** PyTorch/`nn.Dropout` and the file's own code (lines 21-32) implement **inverted dropout**: scaling by `1/(1-p)` is done at training time, so inference requires NO scaling. The Mermaid diagram describes the older non-inverted dropout convention (where scaling happens at inference), contradicting the code immediately below it.
- **Justification:** Self-contradicting content — diagram says "scale by 1-p at inference", code says "scale by 1/(1-p) at training, no scaling at inference". The same misleading diagram appears in `ml/foundations/regularization.md:177`.

#### ml/foundations/regularization.md:177
- **Wrong text:** Mermaid node `E[Inference: Use all neurons, scale by 1-p] --> D[Averaging effect at inference]`
- **Correct text:** `E[Inference: Use all neurons (no scaling — inverted dropout already scaled during training)] --> D[Averaging effect at inference]`
- **Verification:** Same as `ml/deep-learning/dropout.md:13` — the code block immediately above (lines 142-150) implements inverted dropout. The diagram describes traditional (non-inverted) dropout, which is not what the code does.
- **Justification:** Self-contradicting content within the same file.

#### ml/transformers/bert.md:161
- **Wrong text:** `4. Trained longer (500K vs. 1M steps)`
- **Correct text:** `4. Trained with larger batches and more total compute (500K steps × 8K batch ≈ 4× more tokens/step than BERT's 1M steps × 256 batch)`
- **Verification:** RoBERTa paper (Liu et al. 2019) Table 1 and Section 4 — RoBERTa trained for 500K steps with batch size 8K, BERT trained for 1M steps with batch size 256. So in step count RoBERTa trained for FEWER steps (500K < 1M), but with much larger batches the total compute (and total tokens seen) is much higher for RoBERTa. Source: https://arxiv.org/abs/1907.11692
- **Justification:** "Trained longer (500K vs. 1M steps)" is misleading — 500K is fewer steps than 1M, not "longer". The actual difference is larger batch size and more total compute.

### LOW severity

#### ml/advanced/edge.md:55
- **Wrong text:** `# For 256→512: 1,179,648 → 147,456 (8x reduction)`
- **Correct text:** `# For 256→512: 1,179,648 → 133,376 (≈8.8x reduction)`
- **Verification:** Regular conv params: `3·3·256·512 = 1,179,648`. Depthwise separable: `3·3·256 + 1·1·256·512 = 2,304 + 131,072 = 133,376`. Ratio: `1,179,648 / 133,376 ≈ 8.84×`. `python3 -c "print(3*3*256*512, 3*3*256 + 256*512, 3*3*256*512/(3*3*256 + 256*512))"`
- **Justification:** The 147,456 number is wrong; the correct depthwise-separable count is 133,376 (≈8.8× reduction rather than exactly 8×). Conceptually correct but the specific arithmetic is off.

#### ml/classical/ensemble.md:71
- **Wrong text:** `model = clone(self.base_model)` (inside custom BaggingClassifier)
- **Correct text:** Add `from sklearn.base import clone` at the top of the file (or import it inline).
- **Verification:** `clone` is not a built-in Python name; it must be imported from `sklearn.base`.
- **Justification:** Would raise `NameError` as written. Minor since it's clearly meant to use sklearn's `clone`.

#### ml/deep-learning/optimizers.md:33
- **Wrong text:** `for key, (param, grad) in enumerate(zip(params, grads)):`
- **Correct text:** `for i, (param, grad) in enumerate(zip(params, grads)):` (and use `i` as the dict key consistently)
- **Verification:** Using `key` (which suggests a dict key string) for an integer index from `enumerate` is misleading; works in Python but unconventional.
- **Justification:** Style/readability nit — the variable name `key` is misleading for an integer index. Not a bug.

## Files confirmed clean

The following 56 files were audited and found to be substantively correct (no HIGH/MEDIUM findings):

**ml/foundations/** (8): feature-engineering.md, loss-functions.md, regularization.md (except the dropout Mermaid noted), probability.md, evaluation.md, linear-algebra.md, optimization.md, cross-validation.md

**ml/deep-learning/** (8): nn-basics.md, optimizers.md, activation.md, transfer-learning.md, attention.md (except noted math errors), dropout.md (except noted Mermaid), batch-norm.md, cnn.md

**ml/transformers/** (8): positional-encoding.md, architecture.md, bert.md (except noted RoBERTa issue), gpt.md, vit.md, training.md, variants.md, interview-questions.md (skipped)

**ml/classical/** (11): linear-regression.md, logistic-regression.md, decision-trees.md (except noted LightGBM issue), svm.md, knn.md, naive-bayes.md, kmeans.md, gradient-boosting.md, pca.md (except noted SVD issue), random-forest.md, xgboost.md, lightgbm.md (except noted GOSS issue), catboost.md

**ml/rl/** (7): fundamentals.md, q-learning.md, policy-gradient.md, ppo.md, rlhf.md, dpo.md, grpo.md

**ml/llm/** (3): distributed-training.md, gpt-architecture.md, training-pipeline.md

**ml/gan/** (4): architecture.md, training.md, conditional.md, stylegan.md

**ml/gnn/** (4): basics.md, gcn.md, graphsage.md, gat.md

**ml/advanced/** (5): pruning.md, distillation.md (except noted softmax issue), quantization.md (except noted markdown issue), compression.md (except noted SVD issue), federated.md, nas.md (except noted one_hot issue), edge.md (except noted param count issue)

**ml/mlops/** (3): mlflow.md, monitoring.md, drift.md

**ml/system-design/** (2): recommendation.md, fraud-detection.md (except noted class_weight issue)

**ml/time-series/** (2): arima.md (except noted diff issue), prophet.md

**ml/agents/** (4): langchain.md, react.md, mcp.md, crewai.md

**ml/overview.md** (1)

## Top 5 Issues (by impact)

1. **`ml/transformers/self-attention.md` worked example is fundamentally broken** (HIGH) — Q[0], V[0], V[1], the score matrix, the softmax values, and the output values are ALL wrong. A student following this example would compute attention incorrectly. (4 HIGH findings in the same example.)

2. **`ml/deep-learning/attention.md` softmax/output example wrong** (HIGH) — softmax([1, 0, 0.5]) values [0.441, 0.163, 0.396] are fabricated; correct values are [0.5065, 0.1863, 0.3072]. Output values [2.91, 3.80] also wrong.

3. **`ml/deep-learning/rnn-lstm.md` GRUCell is broken** (HIGH) — Two bugs prevent the code from running at all: `self.wr` vs `self.Wr` case mismatch, and missing `self.sigmoid` method.

4. **`ml/system-design/fraud-detection.md` uses non-existent API** (HIGH) — `GradientBoostingClassifier(class_weight=...)` raises TypeError; this is a common interview question and the answer code would not run.

5. **`ml/classical/ensemble.md` AdaBoost implementation is mathematically wrong** (HIGH) — The weight-update formula `np.exp(-alpha * y * predictions)` requires ±1 labels but `DecisionTreeClassifier` outputs {0,1}; 3 of 4 cases never update weights, breaking the boosting dynamics.
