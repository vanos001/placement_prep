# Differential Privacy

Differential privacy (DP) is a mathematical definition of what it means for a data-release mechanism to "preserve privacy." It does not promise that no information about individuals leaks — that is information-theoretically impossible for any useful mechanism. It promises something subtler: that *the probability of any output* differs by at most a small multiplicative factor depending on whether any single individual's record is in the dataset. This chapter covers the (ε, δ)-definition, the canonical mechanisms (Laplace, Gaussian, exponential), composition theorems, the moments accountant, and how these ideas now power the US Census, Apple's telemetry, and Google's RAPPOR.

## The Problem DP Solves

Anonymization fails. Famously, in 2006, Netflix released 100M "anonymized" movie ratings (just `(user_id, movie, rating, date)`) and within weeks Narayanan and Shmatikov linked the supposedly-anonymous records to public IMDb profiles, de-anonymizing subscribers and exposing political-orientation inferences. Massachusetts released "anonymized" insurance group statistics; Latanya Sweeney famously sent then-Governor Weld's health records to his office, having re-identified him from {zip, birth date, sex} that appeared in both.

These failures share a pattern: the release is exact, and an adversary with side information can uniquely fingerprint individuals. DP's response is to add calibrated noise so that no individual record can move the output by more than a small factor.

## The Definition

A randomized mechanism `M : D → R` is (ε, δ)-differentially private if for all datasets `D, D'` differing in one record (called *neighbors*, `D ∼ D'`), and for all measurable `S ⊆ R`:

```text
Pr[M(D) ∈ S] ≤ e^ε · Pr[M(D') ∈ S] + δ
```

When δ = 0, this is *pure* DP. When δ > 0, it is *approximate* DP; δ is a "failure probability" — a small chance the guarantee does not hold. In practice, δ is set to something much smaller than `1/n` (e.g., δ = 10⁻⁸ for a million-record dataset), so the failure mode is collectively negligible.

The interpretation: an adversary's posterior beliefs about whether your record was in `D` differ by at most `e^ε` between the two worlds. With ε = 1, that's a factor of `e ≈ 2.71` — noticeable but bounded. With ε = 0.1, the factor is ~1.1, nearly undetectable. With ε = 10, the factor is ~22000 — basically no privacy.

The US Census uses ε = 19.61 (their 2020 TopDown algorithm, with advanced composition accounting); Apple uses per-event ε between 1 and 8; Google's RAPPOR uses ε between 2 and 9.

## Randomized Response (the ancestor)

Before DP was formalized, Stanley Warner (1965) invented *randomized response* for sensitive survey questions. When asked "did you commit crime X?", the respondent secretly flips a fair coin. If heads, they answer truthfully. If tails, they flip again and answer "yes" if heads, "no" if tails — regardless of truth.

```text
Pr[respondent answers "yes"]:
  - If truthful answer is "yes": 0.5 (truth) + 0.5·0.5 (forced yes) = 0.75
  - If truthful answer is "no":  0 + 0.5·0.5 = 0.25
```

The interviewer cannot tell whether a "yes" was truthful or forced, yet the statistician can subtract the coin noise to recover the population frequency: `f_yes = 2 · (observed_yes_rate - 0.25)`. This is exactly (ln 3)-DP and is the prototype for every DP mechanism since.

## The Laplace Mechanism

The Laplace mechanism is the workhorse of pure (ε, 0)-DP. It applies to functions `f : D → ℝ^k` that return real-valued statistics. Define the **sensitivity** of `f`:

```text
Δf = max_{D ∼ D'} ||f(D) - f(D')||_1
```

For a count query (e.g., number of HIV-positive patients in `D`), `Δf = 1` — adding or removing one patient changes the count by at most 1. For a histogram with `k` bins, `Δf = 1` (an individual falls in one bin). For a sum of values bounded in `[0, 1]`, `Δf = 1`. For the mean of `n` values in `[0, 1]`, `Δf = 1/n` (an individual moves the mean by at most `1/n`).

The Laplace mechanism releases:

```text
M(D) = f(D) + Laplace(Δf / ε)
```

where `Laplace(b)` has density `(1/2b) · e^(-|x|/b)`. The noise scale `b = Δf / ε`.

### Worked example

Database: 100 patients, of whom 8 have HIV. Honest count: 8. Sensitivity: Δ = 1.

If we want ε = 1 DP, we release `8 + Lap(1.0)`. The noise has mean 0 and standard deviation `√2 ≈ 1.41`. So the released count is something like 8 ± 1 most of the time, occasionally 11 or 5. The HIV patient who knows they were in the dataset cannot tell from the released value (8 → 9 is indistinguishable from 8 → 8 with `+1` noise added).

If we tighten to ε = 0.1, the noise becomes `Lap(10.0)` — std dev 14. The release is now "between -22 and 38" — useless for the data analyst but extremely private. The (privacy, utility) trade-off is governed by `1/ε`.

## The Gaussian Mechanism

For (ε, δ)-DP with δ > 0, the Gaussian mechanism is preferable: it adds Gaussian noise of standard deviation `σ = Δf · √(2 ln(1.25/δ)) / ε`. The Gaussian gives better utility at the cost of an additive `δ` failure probability.

For `ε = 1, δ = 10⁻⁵, Δf = 1`: σ ≈ `√(2·11.5)/1 ≈ 4.8`. Compare to Laplace, where `b = 1.0`, std dev ≈ `1.41`. The Gaussian is noisier in absolute terms, but it generalizes to multiple queries much better (see composition).

## Composition Theorems

The power of DP comes from composition: if you run two DP mechanisms with parameters (ε₁, δ₁) and (ε₂, δ₂), the *combined* mechanism is DP. The question is: what are the combined parameters?

**Basic composition.** For pure DP: k queries each at ε are jointly 2ε-DP. Linear in `k`. Bad for many queries — k=1000 queries at ε=0.1 each gives ε=100 total, no privacy left.

**Parallel composition.** If each query touches a *disjoint* subset of the data, ε's add — but the effective per-individual privacy loss is `max ε_i`, not the sum. This is why histogram queries are cheap: each bin counts a disjoint partition of the data.

**Post-processing.** Any function of a DP output is DP at the same parameters. You can sort, threshold, fit a model — all post-processing is "free" in privacy budget.

**Advanced composition (Dwork-Rothblum-Vadhan, 2010).** k mechanisms at (ε, 0) compose to roughly `(k · ε²/2 + ε · √(2k ln(1/δ)), δ)` — much better than linear for small ε. For k=1000, ε=0.01: total ε ≈ 9 instead of 10.

## Rényi DP and the Moments Accountant

Even better composition bounds come from going through **Rényi divergence**. A mechanism is (α, ε)-Rényi DP if for all neighbors `D, D'`:

```text
D_α(M(D) || M(D')) = (1/(α-1)) · ln E_{x ~ M(D)} [(M(D')(x) / M(D)(x))^α] ≤ ε
```

Rényi DP at level α composes *additively*: k mechanisms at (α, ε) compose to (α, kε). Then we convert Rényi to (ε, δ)-DP at the end: `(α, ε_RDP) ⇒ (ε_RDP + ln(1/δ)/α - 1)/α, δ)` and minimize over α.

This is the **moments accountant** (Abadi et al., 2016) — it gives bounds that are 5–10× tighter than advanced composition. Google's TensorFlow Privacy and Opacus (PyTorch) use it to track the privacy loss of DP-SGD during model training.

## The Exponential Mechanism

What if the output is not a number, but a discrete choice? The **exponential mechanism** (McSherry and Talwar, 2007) handles "select the best item" queries. Given a utility function `u : D × R → ℝ` with sensitivity `Δu`, the mechanism samples output `r` with probability proportional to `exp(ε · u(D, r) / (2 Δu))`. This is ε-DP and selects high-utility outputs with high probability.

Example: selecting the most common diagnosis from a set of 1000 candidate diagnoses. The Laplace-on-counts approach would be ε-DP per query but require a separate query per candidate. The exponential mechanism does it in one query: sample diagnosis `i` with probability proportional to `exp(ε · count_i / 2)`. The most common diagnosis is exponentially likely to be selected; the others have non-trivial but small probability.

## DP-SGD: Training ML with Privacy

The killer application of the moments accountant is **DP-SGD** (Abadi et al., 2016). Standard SGD updates parameters as `θ ← θ - η · ∇L(θ; x)` where `x` is one example (or mini-batch). DP-SGD adds:

1. Compute per-example gradients `g_i = ∇L(θ; x_i)`.
2. Clip each gradient to a fixed L2 norm `C`: `g_i ← g_i / max(1, ||g_i||/C)`. This bounds sensitivity at `C`.
3. Sum and add noise: `g̃ = (1/B) · (Σ g_i + N(0, σ²C²I))`.
4. Update: `θ ← θ - η · g̃`.

The privacy analysis uses the moments accountant to track the total ε over all T steps. A useful rule of thumb (Mironov's estimate): with batch size B, n examples, T steps, sampling rate `q = B/n`, and noise multiplier `σ`:

```text
ε ≈ q²·T / σ²  ·  (small constants)
```

To get ε = 1 over T = 1000 steps with n = 1M, you need `σ ≈ 1.0`, batch size 1000. The noise dominates the gradient — accuracy drops by 1–10% on most tasks. DP-SGD-tuned models for CIFAR-10 reach ~70% (vs. 92% non-private); for language tasks, the gap is larger.

## Real-World Deployments

### US Census 2020

The 2020 US Census used the **TopDown Algorithm** (Abowd et al., 2019). Every Census release — state populations, county-level tables, block-level data — passes through a DP mechanism with ε = 19.61 (a value so high that some privacy researchers argued it provides little real protection; the Census Bureau responded that the noise floor of `~6` people per block is more meaningful than ε alone). The algorithm:

1. Compute the exact statistics on the raw Census.
2. Add Laplace or discrete Gaussian noise to each statistic.
3. Run a post-processing step (constraint optimization) to ensure the noisy statistics are *consistent* (state populations sum to US total, county populations sum to state total, no negative counts, etc.).

The 2020 release was the first national census with formal privacy guarantees. Controversy: census data is used for political redistricting; small noise perturbations can flip a congressional district. The Census Bureau argued that exact release (the prior status quo) was already leaking more information than was defensible in 2020.

### Apple's Privacy Preserving Measurement

Apple uses local DP (LDP, the ε-only setting where each user perturbs their own data before sending it to the server). For collecting emoji usage statistics, Apple uses the count-mean-sketch mechanism: clients hash their emoji into a 2^16-bit Bloom-filter, flip each bit with probability `p = 1/(1 + e^ε)`, and submit. The server aggregates submissions, recovers the per-bit count, and combines the hash function outputs to recover the most popular emojis.

The published parameters (Apple's 2017 white paper) are ε = 4 for daily emoji statistics, ε = 8 for Safari browsing-pattern telemetry. Privacy is achieved because the noise is added *on the user's device*, before the network — the server sees only the noisy bit-flipped vector and can prove (information-theoretically) that no single user's contribution is identifiable.

### Google RAPPOR

RAPPOR (Erlingsson, Pihur, Korolova, 2014) collects strings — e.g., the homepage URL of Chrome users — under LDP. It combines:

1. The **Bloom filter** of the string (typically 1280 bits).
2. **Permanent randomized response**: each bit is flipped with probability `f = 0.5` once per user, *kept* across all reports (this is the long-term privacy layer).
3. **Instantaneous randomized response**: each report samples from the permanent record with another `f` — this prevents longitudinal correlation.

Given N reports, the server uses an L1-regularized linear regression (`LASSO`) to recover the underlying string distribution. RAPPOR is (ε, 0)-DP per report at ε = ln((1-p)/p) for a flip probability `p`. Google used it for homepage, default search engine, and other Chrome telemetry; the published parameters give ε ≈ 2 per report.

## Common Pitfalls

1. **Choosing ε too high.** ε = 10 is not "private" in any meaningful sense; the privacy loss is bounded only by `e^10 ≈ 22000`. Privacy budgets in academic papers often report "ε = 1 over the whole training," which is reasonable; "ε = 8 per query" is much weaker.

2. **Forgetting post-processing is not free composition.** Post-processing (sorting, fitting, thresholding) is free, but running the *mechanism again* consumes privacy budget. A common error: "we ran our DP algorithm once, then re-ran it with different parameters" — that's two queries, ε doubles.

3. **Ignoring parallel composition.** If you query each *bin* separately with budget ε, that's k queries at ε and total is kε. But if the bins are disjoint, the *individuals* are each only in one bin — total privacy loss per individual is ε, not kε.

4. **DP-SGD clipping too tight.** Setting `C` (the gradient clip) to a tiny value (e.g., `C = 0.1`) makes gradients mostly noise. Set `C` to the *median* gradient norm, not the 99th percentile, to balance utility and sensitivity.

5. **Believing LDP is "more private" than central DP.** LDP is *much* weaker at the same ε because each user adds full-magnitude noise. To match the accuracy of central DP at ε = 1 over 1M users, LDP needs ~10⁶× more users. Always compare at equal utility.

6. **Confusing privacy and security.** DP does not protect against re-identification by an attacker who already knows the full dataset; it protects against information leakage from the *release*. It is a release mechanism, not a database security mechanism.

## References

- Cynthia Dwork, Aaron Roth, "[The Algorithmic Foundations of Differential Privacy](https://www.cis.upenn.edu/~aaroth/Papers/privacybook.pdf)" (2014) — canonical textbook
- Cynthia Dwork, Frank McSherry, Kobbi Nissim, Adam Smith, "[Calibrating Noise to Sensitivity in Private Data Analysis](https://privacytools.seas.harvard.edu/files/privacytools/files/calibrating.pdf)" (TCC 2006) — the original DP paper
- Martin Abadi et al., "[Deep Learning with Differential Privacy](https://arxiv.org/abs/1607.00133)" (CCS 2016) — DP-SGD + moments accountant
- Úlfar Erlingsson, Vasyl Pihur, Aleksandra Korolova, "[RAPPOR: Randomized Aggregatable Privacy-Preserving Ordinal Response](https://arxiv.org/abs/1407.4981)" (CCS 2014)
- Apple Inc., "[Differential Privacy Overview](https://www.apple.com/privacy/docs/Differential_Privacy_Overview.pdf)" (2017) — technical white paper
- US Census Bureau, "[Disclosure Avoidance for the 2020 Census](https://www.census.gov/library/working-papers/2018/adrm/DSDP-working-paper.html)" — TopDown algorithm documentation
- Ilya Mironov, "[Rényi Differential Privacy](https://arxiv.org/abs/1702.07476)" (CSF 2017)
- Frank McSherry, Kunal Talwar, "[Mechanism Design via Differential Privacy](https://www.microsoft.com/en-us/research/publication/mechanism-design-via-differential-privacy/)" (FOCS 2007) — exponential mechanism
- Latanya Sweeney, "[Simple Demographics Often Identify People Uniquely](https://dataprivacylab.org/dataprivacylab/kanonymous/)" (2000) — the de-anonymization motivation
- Arvind Narayanan, Vitaly Shmatikov, "[Robust De-anonymization of Large Sparse Datasets](https://www.cs.utexas.edu/~shmat/shmat_oak08netflix.pdf)" (S&P 2008) — Netflix de-anonymization
- [TensorFlow Privacy library](https://github.com/tensorflow/privacy) — reference DP-SGD implementation
- [Opacus: PyTorch DP training](https://opacus.ai/)
