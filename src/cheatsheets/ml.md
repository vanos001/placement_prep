# Machine Learning Cheat Sheet

## Supervised Learning

| Algorithm | Type | Pros | Cons | Use When |
|-----------|------|------|------|----------|
| Linear Regression | Regression | Simple, interpretable | Assumes linearity | Baseline, linear relationships |
| Logistic Regression | Classification | Fast, probabilistic | Linear boundary | Binary/multiclass baseline |
| Decision Trees | Both | Interpretable, no scaling | Overfitting | Explainability needed |
| Random Forest | Both | Reduces overfitting | Slow inference | General purpose |
| XGBoost | Both | State-of-art tabular | Harder to tune | Competitions, tabular data |
| LightGBM | Both | Fast, memory efficient | Sensitive to hyperparams | Large datasets |
| SVM | Both | Works in high-dim | Slow on large data | Small-medium data, high-dim |
| KNN | Both | Simple, no training | Slow inference, memory | Small data, similarity-based |
| Naive Bayes | Classification | Fast, works with little data | Feature independence | Text classification |

## Key Formulas

```
Accuracy  = (TP + TN) / (TP + TN + FP + FN)
Precision = TP / (TP + FP)          → "Of predicted positive, how many correct?"
Recall    = TP / (TP + FN)          → "Of actual positive, how many found?"
F1        = 2 × (Precision × Recall) / (Precision + Recall)
AUC-ROC   = Area under TPR vs FPR curve

MSE  = (1/n) Σ(y - ŷ)²
MAE  = (1/n) Σ|y - ŷ|
RMSE = √MSE
R²   = 1 - (SS_res / SS_tot)
Cross-Entropy = -Σ yᵢ log(ŷᵢ)
```

## Bias-Variance Tradeoff

```
Total Error = Bias² + Variance + Irreducible Error

High Bias → Underfitting → More complex model
High Variance → Overfitting → Regularization, more data
```

## Regularization

| Type | Formula | Effect |
|------|---------|--------|
| L1 (Lasso) | + λΣ\|wᵢ\| | Feature selection (sparse) |
| L2 (Ridge) | + λΣwᵢ² | Small weights, smooth |
| Elastic Net | L1 + L2 | Combined |
| Dropout | Random neurons off | Ensemble effect |
| Early Stop | Stop before overfit | Implicit regularization |

## Feature Engineering

- **Scaling**: StandardScaler (μ=0, σ=1), MinMaxScaler (0-1), RobustScaler (median/IQR)
- **Encoding**: One-hot (nominal), Label/Ordinal (ordinal), Target encoding (high cardinality)
- **Missing**: Mean/median/mode imputation, KNN imputation, indicator variable
- **Selection**: Mutual information, chi-squared, correlation filter, RFE

## Cross-Validation

```
K-Fold: Split into K folds, train on K-1, test on 1, rotate
Stratified: Preserves class distribution
Leave-One-Out: K = n (expensive)
Time Series: Always forward-looking (no future leakage)
```

## Evaluation Metrics Quick Reference

| Metric | Range | Best | Use Case |
|--------|-------|------|----------|
| Accuracy | 0-1 | 1 | Balanced classes |
| Precision | 0-1 | 1 | Cost of false positive high |
| Recall | 0-1 | 1 | Cost of false negative high |
| F1 | 0-1 | 1 | Imbalanced classes |
| AUC-ROC | 0-1 | 1 | Ranking, threshold-independent |
| Log Loss | 0-∞ | 0 | Probabilistic predictions |
| RMSE | 0-∞ | 0 | Regression (penalizes large errors) |
| MAE | 0-∞ | 0 | Regression (robust to outliers) |

## Ensemble Methods

```
Bagging: Train models on random subsets → aggregate (Random Forest)
Boosting: Train sequentially, each fixing previous errors (XGBoost, LightGBM)
Stacking: Train meta-model on base model predictions
Voting: Hard (majority) or Soft (average probabilities)
```

## Interview Quick Tips

1. Always ask: classification or regression? Supervised or unsupervised?
2. Start simple (logistic regression), then complex
3. Check for data leakage (future info, target-derived features)
4. Handle class imbalance: SMOTE, class weights, undersampling, threshold tuning
5. Feature importance: tree-based → impurity; linear → coefficients
