# Classical Machine Learning

## Overview

Classical ML algorithms are the **workhorses of industry**. While deep learning gets headlines, classical ML models are used extensively in production systems due to their interpretability, efficiency, and strong performance on structured/tabular data.

```mermaid
graph TD
    A[Classical ML] --> B[Supervised Learning]
    A --> C[Unsupervised Learning]
    
    B --> D[Regression]
    B --> E[Classification]
    
    D --> F[Linear Regression]
    D --> G[Decision Trees]
    D --> H[Random Forest]
    D --> I[XGBoost]
    
    E --> J[Logistic Regression]
    E --> K[SVM]
    E --> L[Naive Bayes]
    E --> M[KNN]
    
    C --> N[Clustering]
    C --> O[Dimensionality Reduction]
    
    N --> P[K-Means]
    O --> Q[PCA]
```

## Why Classical ML Still Matters

| Advantage | Deep Learning |
|-----------|--------------|
| Interpretable (trees, linear models) | Often black-box |
| Fast training and inference | Expensive compute |
| Works on small datasets | Needs lots of data |
| No GPU required | GPU essential for large models |
| Strong on tabular data | Strong on images, text, audio |
| Well-understood theory | Active research area |

## Models in This Section

| Model | Type | Key Idea | Interview Frequency |
|-------|------|----------|-------------------|
| [Linear Regression](linear-regression.md) | Regression | Linear relationship | ⭐⭐⭐⭐⭐ |
| [Logistic Regression](logistic-regression.md) | Classification | Sigmoid + cross-entropy | ⭐⭐⭐⭐⭐ |
| [Decision Trees](decision-trees.md) | Both | Recursive partitioning | ⭐⭐⭐⭐ |
| [Random Forest](random-forest.md) | Both | Bagging of trees | ⭐⭐⭐⭐ |
| [Gradient Boosting](gradient-boosting.md) | Both | Sequential error correction | ⭐⭐⭐⭐ |
| [XGBoost](xgboost.md) | Both | Regularized boosting | ⭐⭐⭐⭐⭐ |
| [LightGBM](lightgbm.md) | Both | Histogram-based boosting | ⭐⭐⭐⭐ |
| [CatBoost](catboost.md) | Both | Ordered boosting | ⭐⭐⭐ |
| [SVM](svm.md) | Both | Maximum margin | ⭐⭐⭐⭐ |
| [KNN](knn.md) | Both | Instance-based | ⭐⭐⭐ |
| [Naive Bayes](naive-bayes.md) | Classification | Bayes + independence | ⭐⭐⭐ |
| [K-Means](kmeans.md) | Clustering | Centroid-based | ⭐⭐⭐ |
| [PCA](pca.md) | Dim. Reduction | Variance maximization | ⭐⭐⭐⭐ |
| [Ensemble](ensemble.md) | Meta-method | Combine models | ⭐⭐⭐⭐ |

## When to Use What

```mermaid
graph TD
    A[Start] --> B{Data type?}
    B -->|Tabular| C{Interpretability needed?}
    B -->|Images/Text/Audio| D[Use Deep Learning]
    
    C -->|Yes| E{Linear relationship?}
    C -->|No| F[XGBoost/LightGBM]
    
    E -->|Yes| G[Linear/Logistic Regression]
    E -->|No| H[Decision Trees]
    
    I{Small dataset?} --> J[Linear Models, SVM]
    K{Large dataset?} --> L[Gradient Boosting, Random Forest]
```

## The Ensemble Hierarchy

```mermaid
graph LR
    A[Single Decision Tree] --> B[High Variance]
    B --> C[Random Forest: Bagging reduces variance]
    B --> D[Gradient Boosting: Sequential reduces bias]
    C --> E[XGBoost: Regularized boosting]
    D --> E
    E --> F[LightGBM: Faster, histogram-based]
    E --> G[CatBoost: Better categorical handling]
```

Each subsequent model builds on the ideas of the previous, adding improvements for speed, accuracy, or handling specific data types.

## Cross-References

- [ML Foundations](../foundations/README.md)
- [Deep Learning](../deep-learning/README.md)
- [Ensemble Methods](./ensemble.md)
- [Feature Engineering](../foundations/feature-engineering.md)
- [ML Interview Questions](../../interview/ml-questions.md)
