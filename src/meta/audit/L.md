# Chunk L Audit — Git + Testing + SRE + Projects + Resume + Placement + Cheatsheets + Mobile + ML + Linux

**Scope:** All files in `git/`, `testing/`, `sre/`, `projects/`, `resume/`, `placement-preparation/`, `cheatsheets/`, `mobile/`, `ml/`, `linux/` (and root `introduction.md` + `glossary.md`), skipping the files listed in `already_fixed.md` (git/internals.md, git/stashing.md, git/worktrees-submodules.md, git/rebasing.md, testing/integration-testing.md, cheatsheets/system-design.md, cheatsheets/python.md, cheatsheets/linux.md, linux/networking/osi-model.md, linux/shell/bash.md).

**Files audited:** 51 (full reads) + ~60 sampled from `ml/` and `linux/` (large directories)
**Files clean:** most files in git/, testing/, sre/, projects/, resume/, placement-preparation/, cheatsheets/, mobile/, introduction.md, glossary.md — see "Files confirmed clean" below.
**Total findings:** 16 (3 HIGH, 6 MEDIUM, 7 LOW)

## Findings

### HIGH severity

#### L-H1 — `ml/transformers/self-attention.md` lines 102–117 — Worked numerical example has multiple wrong matrix entries

The "Detailed Computation Example" walks readers through Q, K, V, scores, softmax, and output for a 3-token sequence. Running the actual matrix multiplication in Python (see verification below) shows the file's claimed values are wrong for Q row 0, for the entire V matrix, and for two rows of the scores matrix:

```text
File claims:           Actual (verified with NumPy):
Q = [[1, 0], ...]      Q = [[2, 0], [0, 2], [1, 1]]      # Row 0 wrong
K = [[0, 2], ...]      K = [[0, 2], [2, 0], [1, 1]]      # OK
V = [[1, 0], ...]      V = [[1, 1], [1, 1], [1, 1]]      # All three rows wrong
scores = [[0, 2, 1],   scores = [[0, 4, 2], [4, 0, 2],  # Rows 0 and 2 wrong
          [4, 0, 2],             [2, 2, 2]]
          [1, 2, 2]]
```

Downstream, the file then claims `softmax([4, 0, 2]/√2) ≈ [0.79, 0.05, 0.16]` and `output[1] = [0.95, 0.26]`. With the *file's* (incorrect) scores the softmax actually gives `[0.768, 0.045, 0.187]`, and with the correct V = `[[1,1],[1,1],[1,1]]` the output row collapses to `[1.0, 1.0]` (since every value vector is identical). The example is a teaching aid meant to build intuition; with multiple inconsistent intermediate values, a reader following along will be unable to reproduce the math.

Verification:
```bash
python3 -c "
import numpy as np
X = np.array([[1,0,1,0],[0,1,0,1],[1,1,0,0]], float)
Wq = np.array([[1,0],[0,1],[1,0],[0,1]], float)
Wk = np.array([[0,1],[1,0],[0,1],[1,0]], float)
Wv = np.array([[1,0],[0,1],[0,1],[1,0]], float)
print(X@Wq); print(X@Wk); print(X@Wv); print((X@Wq)@(X@Wk).T)
"
```

Suggested fix: Either (a) correct the displayed Q, V, and scores to match the math, or (b) change the input/weight matrices so the displayed values are correct (e.g. set `X[0] = [1,0,0,0]` so that `Q[0] = [1,0]`), and re-derive the softmax/output lines accordingly.

#### L-H2 — `ml/deep-learning/backpropagation.md` line 51–57 — `backward_pass()` references undefined variable `y_onehot`

The standalone function signature takes `y_true`, but the body uses `y_onehot`, which is never defined in that function scope:

```python
def backward_pass(activations, z_values, weights, y_true):
    """Compute gradients using backpropagation"""
    n = len(y_true)
    gradients = {'W': [], 'b': []}

    # Output layer gradient (softmax + cross-entropy)
    delta = activations[-1] - y_onehot  # (n, output_dim)  ← NameError
```

Calling `backward_pass(...)` raises `NameError: name 'y_onehot' is not defined`. The class method later in the file (line 138 `def backward(self, y_true):`) correctly builds `y_onehot` from `y_true` via `np.zeros_like(...)` + scatter assignment, but the standalone function omits this step.

Suggested fix: insert a one-hot conversion at the top of `backward_pass`, e.g.:
```python
y_onehot = np.zeros_like(activations[-1])
y_onehot[np.arange(n), y_true] = 1
```
(Or change the function signature to accept `y_onehot` directly and document the expected shape.)

#### L-H3 — `ml/foundations/bias-variance.md` line 218 — Variance-of-averaged-correlated-variables formula is wrong

The file presents the variance reduction formula for bagging as:

```text
Var(X̄) = (ρ σ²)/n + ((1-ρ) σ²)/n
```

Both terms are divided by `n`, which collapses the expression to `σ²/n` regardless of `ρ` — i.e. it would predict that bagging drives variance to zero as `n → ∞` *even when* the base learners are perfectly correlated. The correct formula (see e.g. Elements of Statistical Learning, Eq. 15.1) is:

```text
Var(X̄) = ρ σ² + (1-ρ) σ² / n
```

I.e. the first term has *no* `/n`. With the correct formula, `Var(X̄) → ρ σ²` as `n → ∞`, which is exactly why correlated base learners (high `ρ`) limit bagging's benefit — the central pedagogical point of the surrounding paragraph.

Suggested fix: drop `/n` from the first term so the formula reads `ρ σ² + (1-ρ) σ² / n`.

### MEDIUM severity

#### L-M1 — `resume/technical-skills.md` line 186 — "Pandas" listed twice on same line

Under the "ML Engineer" skills template:
```text
Data: Pandas, NumPy, Spark, SQL, Pandas
```
Pandas appears at both ends of the list. Likely a copy-paste leftover.

Suggested fix: drop the trailing "Pandas" (or replace it with another library such as "PyTorch" or "Dask").

#### L-M2 — `linux/kernel/processes/scheduler.md` lines 34–49 vs line 86 — Internal contradiction about `SCHED_IDLE`

The diagram on lines 34–49 labels the lowest scheduling class as:
```
IDLE["idle_sched_class<br>(SCHED_IDLE)"]
```
implying that `SCHED_IDLE` policy tasks run in `idle_sched_class`. The table on line 86, however, correctly states:
```
| SCHED_IDLE (5) | fair_sched_class | Lowest priority, runs when system is idle |
```
These are two different things in the Linux kernel (verified against `kernel/sched/core.c` `__setscheduler()`):
- `SCHED_IDLE` is a *policy value* (5) — tasks with this policy are placed in `fair_sched_class` with the lowest weight.
- `idle_sched_class` is the *scheduling class* that runs the per-CPU idle task (PID 0 / swapper) when no other task is runnable.

The diagram conflates the two and contradicts the table that appears later in the same file.

Suggested fix: in the diagram, change the bottom node to `IDLE["idle_sched_class<br>(per-CPU idle task, PID 0)"]` (and separately note that `SCHED_IDLE` policy tasks live in `fair_sched_class`).

#### L-M3 — `linux/admin/systemd.md` line 56 — `.journal` is not a systemd unit type

In the "Unit Types Table":
```
| Journal | `.journal` | Journal files |
```
systemd defines 12 unit types: `.service`, `.socket`, `.target`, `.device`, `.mount`, `.automount`, `.swap`, `.timer`, `.path`, `.slice`, `.scope`, and (legacy/deprecated) `.snapshot`. There is no `.journal` unit type — the journal is a runtime artifact produced by `systemd-journald`, not a unit managed by the unit system. Verified against `systemd.unit(5)` man page.

Also note line 57: `| Timer | .timer | Timer-based activation |` duplicates line 46 `| Timer | .timer | Scheduled tasks (cron replacement) |` — the same unit type is listed twice in the same table.

Suggested fix: delete the `.journal` row and one of the duplicate `.timer` rows.

#### L-M4 — `ml/transformers/bert.md` line 161 — Misleading "Trained longer (500K vs. 1M steps)"

Under "Why did RoBERTa outperform BERT?", bullet 4 reads:
```
4. Trained longer (500K vs. 1M steps)
```
This is internally contradictory: 500K *is fewer* steps than 1M, not "longer". RoBERTa trained for fewer optimizer steps but with a much larger batch size (8K vs. BERT's 256), so total token throughput (≈4B vs. ≈256M) was higher — that is where the "longer training" comes from. As written, a reader looking at the parenthetical will conclude the opposite of what the bullet claims.

Suggested fix: rewrite as e.g. "Trained with much larger batches (8K vs. 256) for 500K steps, exposing the model to ~16× more tokens than BERT's 1M steps."

#### L-M5 — `ml/foundations/evaluation.md` line 197 — Deprecated sklearn API call

```python
rmse = mean_squared_error(y_true, y_pred, squared=False)  # Root MSE
```
The `squared` parameter of `sklearn.metrics.mean_squared_error` was deprecated in scikit-learn 1.4 (Jan 2024) and **removed** in scikit-learn 1.6 (2025). On a current sklearn install this raises `TypeError`. Source: <https://scikit-learn.org/stable/modules/generated/sklearn.metrics.mean_squared_error.html>.

Suggested fix:
```python
from sklearn.metrics import root_mean_squared_error
rmse = root_mean_squared_error(y_true, y_pred)
```

#### L-M6 — `linux/kernel/memory/idle-page-tracking.md` lines 86–94 — Self-contradiction about clearing idle bits

The paragraph on lines 86–90 explains how to clear idle bits in the idle-page bitmap by writing 0-valued bits, even noting "OR with 0 is a no-op" — which means the suggested procedure does *nothing*. The very next paragraph (line 92) then opens with "Actually, the kernel uses a different approach: writing sets bits via OR, and there is no direct 'clear' operation via the bitmap file. The kernel clears the idle bit automatically when the page is accessed." So the second paragraph directly refutes the procedure described in the first paragraph. The "Actually," prefix is also one of the listed AI-artifact trigger phrases.

Suggested fix: delete or rewrite the first paragraph. Replace with: "Writing to the bitmap performs an OR operation — bits are only set, never cleared. The kernel clears idle bits automatically when the corresponding page is accessed; there is no userspace 'clear' operation via the bitmap file."

### LOW severity

#### L-L1 — `cheatsheets/networking.md` line 12 — ARP listed at OSI Layer 3

```
| 3 | Network | Packet | IP, ICMP, ARP | Router |
```
ARP (Address Resolution Protocol, RFC 826) is most commonly classified as Layer 2 (Data Link) or "Layer 2.5" because it operates below IP and maps IP addresses to MAC addresses. Tanenbaum, Kurose & Ross, and the Linux kernel (`net/ipv4/arp.c` registers ARP as a packet type under `dev_add_pack()`) all place it at Layer 2. Listing it alongside IP/ICMP at L3 is defensible in some textbooks but misleading for an interview-oriented cheatsheet.

Suggested fix: move ARP to the Layer 2 row, or annotate it as "L2/L3 boundary" in the protocols column.

#### L-L2 — `git/branching.md` line 96 — "renamed from 'recursive'" is misleading

```bash
git merge -s ort feature      # default (renamed from 'recursive')
```
The `ort` strategy is a *rewrite* of `recursive`, not a rename — `recursive` still exists as a separate selectable strategy (`git merge -s recursive` is still valid and is internally distinct from `git merge -s ort`). The git documentation describes `ort` as "Ostensibly Recursive's Twin", a fresh implementation that supersedes `recursive` as the default since git 2.33.

Suggested fix: change comment to `# default (successor to 'recursive', which is still available)`.

#### L-L3 — `linux/admin/permissions.md` lines 14–23 — ASCII diagram of `-rwxr-xr--` is misaligned

The 9-bar legend below the permission string is meant to label each permission bit, but the labels are shifted by one column relative to the bars. Counting bars in each label line shows that the topmost label `Other: read` actually points at position 8 (Other's *write* bit, which is `-`), not position 9 (Other's *read* bit, which is `r`). All subsequent labels inherit the same one-column offset. As a result the diagram effectively mislabels several bits (e.g. "Group: execute" pointing at Group's *read* position, etc.).

Suggested fix: add one more `│` to the right of each label line so the rightmost label lines up with position 9, and ensure the topmost label reads "Other: (no execute)" rather than "Other: read".

#### L-L4 — `cheatsheets/distributed.md` line 9 — MongoDB as unqualified CP

```
CP: ZooKeeper, HBase, MongoDB (strong consistency, may reject requests)
```
MongoDB's CAP classification depends on `readConcern` / `writeConcern` configuration: with `writeConcern=majority` + `readConcern=majority` it behaves CP; with the pre-3.2 default (`{w:1}`) it could be considered AP. Listing MongoDB as unqualified CP without qualification can confuse interviewees who learned the older convention. The current default (`majority`) does match the CP label, so this is borderline.

Suggested fix: append a brief qualifier, e.g. "MongoDB (default `writeConcern=majority` since v3.2)".

#### L-L5 — `ml/transformers/training.md` lines 92–95 — Deprecated `torch.cuda.amp` API

```python
scaler = torch.cuda.amp.GradScaler()
...
with torch.cuda.amp.autocast():
```
The `torch.cuda.amp` namespace has been deprecated in PyTorch 2.0+ in favor of the device-agnostic `torch.amp` module. Source: <https://pytorch.org/docs/stable/amp.html>. The old API still works but emits deprecation warnings.

Suggested fix:
```python
scaler = torch.amp.GradScaler('cuda')
with torch.amp.autocast('cuda'):
```

#### L-L6 — `linux/kernel/processes/eevdf.md` line 197 — "Actually," AI-artifact lead-in

```text
Actually, the real implementation uses a more efficient O(log n) search:
```
"Actually," is one of the listed AI-artifact trigger phrases. The surrounding pedagogy (showing a naive O(n) implementation first, then the real O(log n) version) is fine; only the lead-in word reads like an AI conversational turn. This is purely a stylistic flag.

Suggested fix: replace "Actually, the real implementation uses…" with "The kernel's actual implementation uses…".

#### L-L7 — `mobile/android.md` line 52 — `MaterialTheme.typography.h6` is Material 2 only

```kotlin
Text(text = user.name, style = MaterialTheme.typography.h6)
```
`h6` is a Material Design 2 typography token (Material 2 Compose). The current recommended Compose UI toolkit is Material 3, where the corresponding token is `titleLarge`. Using `h6` requires the `androidx.compose.material:material` (M2) dependency rather than the default `androidx.compose.material3:material3`. The snippet doesn't import either, so it would fail to compile on a fresh Material 3 Compose project.

Suggested fix: either annotate the snippet as "Material 2", or switch to `style = MaterialTheme.typography.titleLarge` (Material 3).

## Files confirmed clean (full reads, no issues)

- `git/README.md`, `git/branching.md`, `git/interview-questions.md`, `git/workflows.md`, `git/fundamentals.md`, `git/cheat-sheet.md`, `git/remotes.md`, `git/hooks.md`, `git/advanced.md`, `git/github.md`, `git/tags.md`
- `testing/README.md`, `testing/tdd-bdd.md`, `testing/unit-testing.md`, `testing/interview-questions.md`, `testing/test-strategy.md`, `testing/mocking.md`, `testing/e2e-testing.md`
- `sre/README.md`, `sre/interview-questions.md`, `sre/slo-sli-sla.md`, `sre/incident-management.md`, `sre/chaos-engineering.md`
- `projects/README.md`, `projects/project-ideas.md`, `projects/explaining-projects.md`
- `resume/README.md`, `resume/projects.md`, `resume/writing-bullets.md`, `resume/common-mistakes.md`, `resume/structure.md`, `resume/technical-skills.md` (except L-M1), `resume/ats-optimization.md`
- `placement-preparation/README.md`, `placement-preparation/online-assessment.md`, `placement-preparation/hr-interview.md`, `placement-preparation/group-discussion.md`, `placement-preparation/campus-placement.md`, `placement-preparation/technical-interview.md`
- `cheatsheets/cloud.md`, `cheatsheets/os.md`, `cheatsheets/networking.md` (except L-L1), `cheatsheets/distributed.md` (except L-L4), `cheatsheets/sql.md`, `cheatsheets/llm.md`, `cheatsheets/ml.md`, `cheatsheets/architecture.md`, `cheatsheets/git.md`, `cheatsheets/dbms.md`
- `mobile/README.md`, `mobile/interview-questions.md`, `mobile/android.md` (except L-L7)
- `introduction.md`, `glossary.md`
- ML sampled clean: `ml/foundations/loss-functions.md`, `ml/foundations/optimization.md`, `ml/foundations/bias-variance.md` (except L-H3), `ml/foundations/evaluation.md` (except L-M5), `ml/deep-learning/backpropagation.md` (except L-H2), `ml/deep-learning/optimizers.md` (uses deprecated API but functional), `ml/deep-learning/activation.md`, `ml/deep-learning/cnn.md`, `ml/deep-learning/dropout.md`, `ml/classical/linear-regression.md`, `ml/classical/logistic-regression.md`, `ml/classical/gradient-boosting.md`, `ml/classical/svm.md`, `ml/transformers/self-attention.md` (except L-H1), `ml/transformers/positional-encoding.md`, `ml/transformers/bert.md` (except L-M4), `ml/transformers/training.md` (except L-L5), `ml/rl/q-learning.md`
- Linux sampled clean: `linux/README.md`, `linux/introduction.md`, `linux/foundations/posix.md`, `linux/foundations/what-is-linux.md`, `linux/tools.md`, `linux/sysprog/process-control.md`, `linux/sysprog/threads.md`, `linux/kernel/processes/cfs.md`, `linux/kernel/processes/scheduler.md` (except L-M2), `linux/kernel/memory/oom-killer.md`, `linux/admin/systemd.md` (except L-M3), `linux/admin/permissions.md` (except L-L3), `linux/networking/ssh.md`, `linux/networking/dns.md`, `linux/containers/cgroups-v2.md`

## Method notes

- All SLO/SLA downtime figures in `sre/slo-sli-sla.md` (43.8 min/4.38 min/26.3 sec for 99.9/99.99/99.999%) were verified with Python; they correspond to the average-month convention (365.25/12 = 43830 min), which is internally consistent across the file (although the Google SRE Workbook uses the 30-day convention of 43200 min/month giving 43.2/4.32/26 sec — both conventions are widely cited, so this is not flagged).
- The `git merge -s ort` claim of being "renamed from 'recursive'" is the only technically inaccurate git statement found; the rest of the git commands match `git-merge(1)`.
- The Q-learning update rule, Adam/AdamW formulas, scaled-dot-product attention formula, and Huber/focal/triplet losses in the sampled ML files were checked against Vaswani et al. (2017), Kingma & Ba (2014), Loshchilov & Hutter (2019), and the standard ESL/PRML references — all match.
- AI-artifact trigger-phrase search (`Wait,`, `Hmm,`, `Actually,`, `Let me re-`, `Let me try`, `Ah, I see`, `Great, so`, `Oh wait`, `But wait`) across all in-scope directories returned 3 hits, all in `linux/`; two are legitimate technical writing and one is a self-contradiction (L-M6).
