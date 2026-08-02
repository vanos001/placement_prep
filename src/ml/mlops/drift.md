# Data Drift Detection

## Overview

Data drift occurs when the statistical properties of input data change over time, causing model performance to degrade. It's one of the most common reasons ML models fail in production. Drift detection identifies these changes early, triggering retraining or alerts before business impact.

## Types of Drift

```mermaid
graph TD
    A[Types of Drift] --> B[Data Drift / Covariate Shift]
    A --> C[Concept Drift]
    A --> D[Label Drift / Prior Probability Shift]
    A --> E[Feature Drift]
    B --> F[P X changes, P Y|X same]
    C --> G[P Y|X changes, P X same or different]
    D --> H[P Y changes]
```

| Type | Definition | Example |
|------|-----------|---------|
| Data Drift | P(X) changes | User demographics shift |
| Concept Drift | P(Y\|X) changes | What was fraud before is now normal |
| Label Drift | P(Y) changes | Class balance shifts |
| Feature Drift | Individual feature distribution changes | Age distribution shifts |

## Detection Methods

### 1. Statistical Tests

```python
from scipy.stats import ks_2samp, chi2_contingency, mannwhitneyu

def ks_test_drift(reference, current, alpha=0.05):
    """Kolmogorov-Smirnov test for continuous features"""
    stat, p_value = ks_2samp(reference, current)
    return {
        'statistic': stat,
        'p_value': p_value,
        'drift': p_value < alpha
    }

def chi2_test_drift(reference, current, alpha=0.05):
    """Chi-squared test for categorical features"""
    # Create contingency table
    ref_counts = reference.value_counts()
    cur_counts = current.value_counts()
    all_categories = set(ref_counts.index) | set(cur_counts.index)

    contingency = []
    for cat in all_categories:
        contingency.append([
            ref_counts.get(cat, 0),
            cur_counts.get(cat, 0)
        ])

    stat, p_value, _, _ = chi2_contingency(contingency)
    return {'statistic': stat, 'p_value': p_value, 'drift': p_value < alpha}
```

### 2. Population Stability Index (PSI)

```python
def calculate_psi(reference, current, bins=10):
    """PSI: industry standard for distribution shift"""
    # Create bins from reference
    breakpoints = np.percentile(reference, np.linspace(0, 100, bins + 1))
    breakpoints[0], breakpoints[-1] = -np.inf, np.inf

    ref_hist = np.histogram(reference, bins=breakpoints)[0] / len(reference)
    cur_hist = np.histogram(current, bins=breakpoints)[0] / len(current)

    # Avoid log(0)
    ref_hist = np.clip(ref_hist, 1e-4, None)
    cur_hist = np.clip(cur_hist, 1e-4, None)

    psi = np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist))

    # Interpretation
    if psi < 0.1:
        status = "No significant drift"
    elif psi < 0.25:
        status = "Moderate drift - investigate"
    else:
        status = "Significant drift - retrain"

    return {'psi': psi, 'status': status}
```

### 3. Maximum Mean Discrepancy (MMD)

Non-parametric test comparing distributions in kernel space:

```python
def mmd_test(reference, current, kernel='rbf', gamma=1.0):
    """Maximum Mean Discrepancy test"""
    from sklearn.metrics.pairwise import rbf_kernel

    K_rr = rbf_kernel(reference, reference, gamma=gamma)
    K_cc = rbf_kernel(current, current, gamma=gamma)
    K_rc = rbf_kernel(reference, current, gamma=gamma)

    mmd = K_rr.mean() + K_cc.mean() - 2 * K_rc.mean()
    return mmd
```

### 4. Domain Classifier

Train a classifier to distinguish reference from current data:

```python
def domain_classifier_drift(reference, current):
    """If a classifier can distinguish them, drift exists"""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score

    X = np.vstack([reference, current])
    y = np.concatenate([np.zeros(len(reference)), np.ones(len(current))])

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    scores = cross_val_score(clf, X, y, cv=5)

    auc = scores.mean()
    drift = auc > 0.6  # Significantly better than random

    return {'auc': auc, 'drift_detected': drift}
```

## Drift Detection Pipeline

```python
class DriftDetector:
    def __init__(self, reference_data, feature_types):
        self.reference = reference_data
        self.feature_types = feature_types

    def detect(self, current_data):
        results = {}
        for col in current_data.columns:
            if self.feature_types[col] == 'continuous':
                results[col] = ks_test_drift(
                    self.reference[col].dropna(),
                    current_data[col].dropna()
                )
            else:
                results[col] = chi2_test_drift(
                    self.reference[col].dropna(),
                    current_data[col].dropna()
                )

        # Summary
        drifted = [k for k, v in results.items() if v['drift']]
        return {
            'details': results,
            'drifted_features': drifted,
            'drift_fraction': len(drifted) / len(results)
        }
```

## Interview Questions

1. **What is the difference between data drift and concept drift?** — Data drift: input distribution P(X) changes (e.g., new user demographics). Concept drift: the relationship P(Y|X) changes (e.g., fraud patterns evolve).

2. **How do you choose a drift detection method?** — KS test for continuous features, chi-squared for categorical, PSI for business-friendly reporting, MMD for multivariate, domain classifier for complex shifts.

3. **What PSI threshold indicates significant drift?** — PSI < 0.1: stable. 0.1-0.25: moderate, investigate. > 0.25: significant, retrain.

4. **How do you handle drift in production?** — Detect → Alert → Investigate → Retrain with recent data → Validate → Deploy. Automate the retraining pipeline.

5. **Can you have concept drift without data drift?** — Yes. If P(X) stays the same but P(Y|X) changes, the same inputs now have different correct outputs. This is harder to detect since input monitoring won't catch it.

## Summary

Data drift detection uses statistical tests (KS, chi-squared), distribution metrics (PSI, MMD), and domain classifiers to identify when input data diverges from training data. Early detection enables proactive retraining, preventing silent model degradation. PSI is the industry standard for business reporting, while KS/MMD are more statistically rigorous.

## Cross-References

- [Model Monitoring](./monitoring.md) — Broader monitoring context
- [Time Series Anomaly Detection](../time-series/anomaly.md) — Anomaly in drift
- [Evaluation Metrics](../foundations/evaluation.md) — Performance tracking
- [ML Pipeline](./pipelines.md) — Retraining pipelines
- [A/B Testing](./ab-testing.md) — Testing new models after drift
