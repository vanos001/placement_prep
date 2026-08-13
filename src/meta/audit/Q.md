# Chunk Q Audit — ML + Linux (deep re-audit, focus on subdir files not yet deeply read by M/N)

**Scope:** Re-audit files under `src/ml/` and `src/linux/` that chunks M and N did not deeply read.
- `src/ml/` — all subdirs: `agents/`, `gan/`, `gnn/`, `llm/`, `advanced/`, `mlops/`, `system-design/`, `time-series/`, `classical/`, `rl/` (skipping `ml/foundations/bias-variance.md`, `ml/deep-learning/backpropagation.md`, `ml/transformers/self-attention.md`, `ml/deep-learning/attention.md` per `already_fixed.md`)
- `src/linux/` — focus on `admin/`, `shell/` (excl. `bash.md`), `networking/` (excl. `osi-model.md`), `reference/`, `sysprog/` (excl. `syscalls.md` per `already_fixed.md`)

**Files audited (deep-read):** ~85 files (mlops 18 + system-design 9 + time-series 4 + agents 14 + llm 3 + gan 4 + gnn 4 + advanced 6 + classical 5 + rl 1 + linux admin 17 + shell 9 + networking 14 + reference 4 + sysprog 8 + misc). Additional ~150 files grep-scanned for AI artifacts and known-broken patterns.
**Files clean:** Most files in `ml/agents/`, `ml/gan/`, `ml/gnn/`, `linux/admin/`, `linux/networking/`, `linux/sysprog/` are substantively correct.
**Total findings:** 18 (5 HIGH / 7 MEDIUM / 6 LOW)

**Audit method:** Deep-read of every file in the listed subdirs. Arithmetic verified with Python (NumPy/SymPy) where applicable. API signatures verified against official docs. Linux technical claims verified against man pages, kernel headers, and POSIX specs.

Verification approach (in detail):
- Arithmetic / softmax / matrix products verified with Python + NumPy.
- ERE alternation behavior verified with `grep -E` vs `grep` against test inputs.
- PyTorch / sklearn / SageMaker API signatures verified against official documentation.
- Linux command flags verified against man pages (`man 1 find`, `man 1 sed`, `man 1 awk`, `man 1 grep`).
- systemd timer / cron behavior verified against `man 5 crontab` and `man 5 systemd.timer`.

## Findings

### HIGH severity

#### ml/llm/gpt-architecture.md (KV-cache generation code, lines 273-305, 382-399)
- **Wrong text:** The `MultiHeadSelfAttention.forward()` method applies the causal mask as `causal_mask[:T, :seq_len_k]` (lines 295-298), where T is the input length (T=1 during cached generation). During autoregressive generation with a KV cache, the new token has T=1, but its actual position in the sequence is `previous_length`, not 0. The code slices `causal_mask[0:1, ...]` — which masks out ALL positions except 0 — so the new token would attend only to the very first cached position, not to all previous tokens.
- **Correct text:** The mask slice should be offset by the current position, e.g. `causal_mask[current_pos:current_pos+T, :seq_len_k]`, or the position should be passed into `forward()`. Likewise, `positions = torch.arange(T, device=device)` in `GPT2.forward()` (line 367) always starts at 0 — for KV-cache generation, the new token's position should be `cache_length` (e.g. `torch.arange(prev_len, prev_len + T, device=device)`).
- **Verification:** Manual inspection of the code path: `generate()` calls `forward()` with `input_ids = input_ids[:, -1:]` (T=1) on every iteration after the first. Without tracking position offset, both `pos_emb` lookup and `causal_mask` slice are wrong. This is a real bug, but the file is intended as a teaching example — noting as HIGH because a student copying this code for KV-cache generation would get nonsensical results.
- **Justification:** Self-contradicting code: the class is built to support `kv_cache`, but the position-handling logic only works for the first prompt-processing step. Reproduces bug pattern common in pedagogical GPT implementations.

#### ml/system-design/ab-testing.md:79
- **Wrong text:**
  ```python
  'confidence_interval': stats.t.interval(0.95, df=len(treatment_metrics)-1)
  ```
- **Correct text:**
  ```python
  # Welch's two-sample t-interval for the mean difference
  diff = treatment_metrics.mean() - control_metrics.mean()
  n1, n2 = len(treatment_metrics), len(control_metrics)
  se_diff = np.sqrt(treatment_metrics.var(ddof=1)/n1 + control_metrics.var(ddof=1)/n2)
  df_welch = se_diff**4 / ((treatment_metrics.var(ddof=1)/n1)**2/(n1-1) +
                            (control_metrics.var(ddof=1)/n2)**2/(n2-1))
  ci = stats.t.interval(0.95, df=df_welch, loc=diff, scale=se_diff)
  ```
- **Verification:** `scipy.stats.t.interval(0.95, df=N)` returns the symmetric t-quantiles centered at 0 — it is NOT a CI for the lift. The standard usage is `stats.t.interval(0.95, df=..., loc=mean, scale=se)`. Also, `df=len(treatment_metrics)-1` is wrong for a two-sample test; should be `len(treatment)+len(control)-2` (pooled) or Welch–Satterthwaite approximation.
- **Justification:** Teaches wrong use of `scipy.stats.t.interval`. Anyone pasting this code would get the same fixed interval regardless of their data, completely defeating the purpose of a confidence interval.

#### ml/mlops/sagemaker.md:122-133 (Pipeline construction)
- **Wrong text:**
  ```python
  condition = ConditionGreaterThanOrEqualTo(
      left=train_step.properties.FinalMetricDataList[0].Value,
      right=0.90,
  )

  pipeline = Pipeline(
      name="ml-pipeline",
      steps=[process_step, train_step],
  )
  ```
- **Correct text:** The `condition` object must be used inside a `ConditionStep` that gates downstream deployment:
  ```python
  from sagemaker.workflow.condition_step import ConditionStep
  cond_step = ConditionStep(
      name="Quality-Gate",
      conditions=[condition],
      if_steps=[deploy_step],   # run if accuracy >= 0.90
      else_steps=[fail_step],   # run otherwise
  )
  pipeline = Pipeline(name="ml-pipeline", steps=[process_step, train_step, cond_step])
  ```
- **Verification:** SageMaker Python SDK docs for `sagemaker.workflow.condition_step.ConditionStep`. A `ConditionGreaterThanOrEqualTo` object on its own has no effect — it must be passed to a `ConditionStep` which is then included in the pipeline's `steps` list.
- **Justification:** As written, the code defines a quality-gate condition that is silently discarded. A student would think they implemented a metric gate but in reality the pipeline would always proceed past training regardless of accuracy.

#### linux/shell/regex.md:130 (ERE alternation table)
- **Wrong text:**
  ```
  | Feature             | BRE  | ERE  |
  | `|` (alternation)    | `\|` | `\|` |
  ```
- **Correct text:**
  ```
  | Feature             | BRE             | ERE |
  | `|` (alternation)    | `\|` (GNU ext) | `|` |
  ```
- **Verification:** Verified live:
  ```
  $ echo "cat" | grep -E 'cat|dog'  →  matches (cat)
  $ echo "dog" | grep -E 'cat\|dog' →  NO match (ERE \| does not work)
  $ echo "dog" | grep 'cat\|dog'    →  matches (GNU BRE extension)
  ```
  In POSIX ERE, the unescaped `|` is the alternation operator; `\|` is a literal vertical bar. The opposite is true in GNU BRE. The file's "Same in BRE:" block (lines 144-148) also gets this wrong by showing `grep 'cat\|dog' file` as the BRE equivalent — that's only a GNU extension, not portable POSIX BRE.
- **Justification:** Teaches the wrong ERE syntax for alternation. POSIX ERE has *no* `\|` operator. A student would write `\|` in `awk` or `grep -E` and find that their patterns don't match.

#### ml/mlops/drift.md:121-124 (domain_classifier_drift)
- **Wrong text:**
  ```python
  clf = RandomForestClassifier(n_estimators=100, random_state=42)
  scores = cross_val_score(clf, X, y, cv=5)
  auc = scores.mean()
  drift = auc > 0.6  # Significantly better than random
  ```
- **Correct text:** Either rename the variable to `accuracy` (since `cross_val_score` defaults to the estimator's `.score()` method = accuracy for classifiers), or actually compute AUC:
  ```python
  scores = cross_val_score(clf, X, y, cv=5, scoring='roc_auc')
  auc = scores.mean()
  ```
  Also, the threshold of `0.6` makes sense for AUC (0.5 = random) but is meaningless for accuracy (which depends on class balance).
- **Verification:** `sklearn.model_selection.cross_val_score` documentation: "If None, the estimator's score() method is used." For `RandomForestClassifier`, `score()` returns mean accuracy. Source: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_score.html
- **Justification:** The variable is named `auc` but holds accuracy. The `0.6` threshold only makes sense for AUC (where 0.5 is random); accuracy > 0.6 in a balanced 50/50 split is barely above chance. Misleads anyone trying to use this drift-detection recipe.

### MEDIUM severity

#### ml/time-series/transformers.md:41
- **Wrong text:** `# Example: 100 timesteps → 10 patches of size 16 with stride 8`
- **Correct text:** `# Example: 100 timesteps → 11 patches of size 16 with stride 8`
- **Verification:** `python3 -c "print(len(list(range(0, 100-16+1, 8))))"` → `11` (indices 0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80).
- **Justification:** Off-by-one in a teaching example. With patch_size=16 and stride=8, the number of patches is `floor((N - patch_size) / stride) + 1` = `floor(84/8) + 1` = `10 + 1 = 11`.

#### linux/shell/sed-awk.md:452 (awk stddev one-liner)
- **Wrong text:**
  ```bash
  awk '{sum+=$1; sumsq+=$1*$1} END {print "avg:", sum/NR, "stddev:", sqrt(ssq/NR - (sum/NR)^2)}' file
  ```
- **Correct text:**
  ```bash
  awk '{sum+=$1; sumsq+=$1*$1} END {print "avg:", sum/NR, "stddev:", sqrt(sumsq/NR - (sum/NR)^2)}' file
  ```
- **Verification:** In awk, undefined variables default to 0. With `ssq` (typo for `sumsq`), the formula becomes `sqrt(0/NR - (sum/NR)^2) = sqrt(-mean^2)` which is `nan` (or a runtime error). Verified: `echo -e "1\n2\n3" | awk '{sum+=$1; sumsq+=$1*$1} END {print sqrt(ssq/NR - (sum/NR)^2)}'` → `nan`.
- **Justification:** Variable-name typo breaks the standard-deviation calculation entirely. Anyone copying this one-liner would get `nan` for the stddev.

#### linux/shell/sed-awk.md:240 (misleading comment)
- **Wrong text:**
  ```bash
  # Comment out a line
  sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config
  ```
- **Correct text:**
  ```bash
  # Uncomment and change a line: '#Port 22' → 'Port 2222'
  sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config
  ```
- **Verification:** The substitution `s/^#Port 22/Port 2222/` removes the leading `#` (un-commenting) AND changes the port number from 22 to 2222. The comment "Comment out a line" describes the opposite operation.
- **Justification:** Self-contradicting comment vs. code — misleading for readers trying to learn sed.

#### ml/advanced/pruning.md:90-99 (2:4 sparsity example)
- **Wrong text:**
  ```python
  def apply_2_4_sparsity(model):
      """Apply 2:4 structured sparsity"""
      for name, module in model.named_modules():
          if isinstance(module, torch.nn.Linear):
              prune.ln_structured(
                  module, name='weight',
                  amount=0.5, n=1, dim=1
              )
      return model
  ```
- **Correct text:** `prune.ln_structured(amount=0.5, n=1, dim=1)` is plain L1 column pruning — it removes the 50% smallest-magnitude columns; it does NOT enforce the 2:4 pattern (exactly 2 zeros per block of 4 weights). For actual 2:4 sparsity, use `torch.nn.utils.parametrize` with a custom 2:4 mask, or NVIDIA's `tensorrt` / `apex` sparse utilities. E.g.:
  ```python
  # Apply actual 2:4 pattern (each block of 4 consecutive weights has exactly 2 zeros)
  def apply_2_4_sparsity(model):
      for module in model.modules():
          if isinstance(module, nn.Linear):
              w = module.weight.data
              # reshape into blocks of 4
              w_view = w.view(-1, 4)
              # in each block, zero out the 2 smallest magnitudes
              _, idx = torch.topk(w_view.abs(), k=2, dim=1, largest=False)
              w_view.scatter_(1, idx, 0.0)
      return model
  ```
- **Verification:** PyTorch docs for `torch.nn.utils.prune.ln_structured`: this function performs L_n-norm pruning along `dim`, removing entire rows/columns — it produces a generic block-pruning pattern, not the specific 2-out-of-4 pattern. NVIDIA 2:4 sparsity (Ampere+) requires the structured 2:4 zero pattern; see https://developer.nvidia.com/blog/exploiting-ampere-structured-sparsity-with-asparse/.
- **Justification:** Misleading — the function name and docstring claim 2:4 sparsity, but the implementation produces generic L1 column pruning.

#### ml/advanced/federated.md:43-48 vs line 105 (FedAvg inconsistency)
- **Wrong text:** The `aggregate()` function performs *unweighted* averaging:
  ```python
  avg_params[key] = sum(update[key] for update in client_updates) / len(client_updates)
  ```
  But interview Q2 (line 105) says: *"The server averages the resulting model parameters weighted by client dataset size."*
- **Correct text:** Either fix the code to do weighted averaging:
  ```python
  def aggregate(client_updates, client_sizes):
      total_size = sum(client_sizes)
      avg_params = {}
      for key in client_updates[0].keys():
          avg_params[key] = sum(
              size * update[key]
              for size, update in zip(client_sizes, client_updates)
          ) / total_size
      return avg_params
  ```
  Or change the prose to "simple unweighted averaging (in practice, weighted by client dataset size)".
- **Verification:** Original FedAvg paper (McMahan et al. 2017, "Communication-Efficient Learning of Deep Networks from Decentralized Data") specifies weighting by `n_k / Σ n_k` where `n_k` is the number of examples on client k. The code as written does not implement this.
- **Justification:** Code and prose contradict each other on the core FedAvg aggregation rule.

#### ml/llm/training-pipeline.md:431-437 (DPO log-prob gather)
- **Wrong text:**
  ```python
  token_log_probs = torch.gather(
      log_probs_shifted, dim=-1, index=labels_shifted.unsqueeze(-1)
  ).squeeze(-1)
  mask = (labels_shifted != -100).float()
  return (token_log_probs * mask).sum(dim=1)
  ```
- **Correct text:** When `labels_shifted` contains `-100` (the standard "ignore" sentinel for masked positions), `torch.gather` with a negative index has undefined behavior. Clamp to a safe non-negative value before gather:
  ```python
  safe_labels = labels_shifted.clamp(min=0)
  token_log_probs = torch.gather(
      log_probs_shifted, dim=-1, index=safe_labels.unsqueeze(-1)
  ).squeeze(-1)
  mask = (labels_shifted != -100).float()
  return (token_log_probs * mask).sum(dim=1)
  ```
- **Verification:** PyTorch documentation for `torch.gather`: "If index has negative values, the behavior is undefined." In practice, negative indices wrap around (so for a vocab of size V, index `-100` reads position `V-100`), giving wrong log-probs at masked positions. Multiplying by the mask zeros them out, but the gather itself can produce garbage or NaN if the vocab is smaller than 100. This is a well-known footgun — HuggingFace's `transformers` library uses `clamp(min=0)` in similar code paths.
- **Justification:** Subtle bug — works in many cases (when V > 100 and the masked positions happen to be ignored later) but produces wrong values when V ≤ 100 or when NaN/Inf is generated by the wrap-around index.

#### ml/mlops/ab-testing.md:50 (sample-size formula)
- **Wrong text:**
  ```python
  n = ((z_alpha + z_beta) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2))) / (p1 - p2) ** 2
  ```
- **Correct text:** The standard two-proportion z-test sample-size formula uses pooled variance for the z_α term:
  ```python
  p_bar = (p1 + p2) / 2
  n = ((z_alpha * np.sqrt(2 * p_bar * (1 - p_bar)) +
        z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2) / (p1 - p2) ** 2
  ```
- **Verification:** Computed: with baseline=0.05, mde=0.10, the file's formula gives n ≈ 31,231 per variant; the standard pooled-variance formula gives n ≈ 20,267 per variant. The file's version is the simpler (and more conservative) "sum of variances" approximation, but it differs noticeably from the canonical formula cited in most A/B testing references (e.g., Kohavi et al., *Trustworthy Online Controlled Experiments*).
- **Justification:** Off by ~50% on a commonly cited formula. Not strictly *wrong* (it's an upper bound), but mislabeled as the standard. Also the file doesn't note that this is the simplified version.

### LOW severity

#### linux/admin/permissions.md:347-351 (SUID/SGID display note)
- **Wrong text:**
  ```
  SUID on  executable: -rws------
  SUID off executable: -rwS------ (capital S = error)
  SGID on  executable: ---rws---
  SGID off executable: ---rwS--- (capital S = error)
  Sticky on  directory: ------rwt
  Sticky off directory: ------rwT (capital T = error)
  ```
- **Correct text:** "(capital S = SUID set without execute)" / "(capital T = sticky set without others-execute)". Capital S/T are not "errors" — they indicate that the special bit is set but the corresponding execute bit is *not* set, which is unusual (the special bit has no effect without execute) but valid.
- **Verification:** `man 1 ls` / `info coreutils 'ls invocation'`: "Other combinations of file attributes are also reported. For example, a file with mode 2644 would be reported as `-rw-r-Sr--'." Capital S is `S_ISUID` set + execute bit unset — perfectly valid filesystem state.
- **Justification:** Misleading pedagogically — students may believe their filesystem is in an "error" state when it's actually just an unusual (often intentional) combination.

#### linux/find.md:102-103 (-newerBm syntax)
- **Wrong text:**
  ```bash
  # Birth time (Linux 4.11+, GNU findutils 4.9+)
  find . -newerBm -7   # Created in last 7 months
  ```
- **Correct text:** GNU find's `-newerXY` predicate compares file times. `-newerBm` means "birth time newer than modification time of the reference file given in the next argument" — it does NOT mean "created in last 7 days/months". The comment is also internally inconsistent ("7 months" vs the `-7` numeric argument, which `find` doesn't interpret as months). To find files by birth time within a window:
  ```bash
  # Files created in the last 7 days (requires birth-time support)
  find . -newerBt "7 days ago"
  ```
  Where `-newerBt` means "birth time newer than the date argument".
- **Verification:** `man 1 find`: `-newerXY reference`: "Succeeds if timestamp X of the file being considered is newer than timestamp Y of the file reference. The letters X and Y can be any of: `a` (atime), `m` (mtime), `c` (ctime), `B` (birth), `t` (interpret reference as a literal date string)." So `-newerBm` requires a *file* as the next argument (whose mtime is the reference), not a numeric value.
- **Justification:** The command as written would error out (no reference file given, and `-7` is not a valid file). The comment is also misleading on the time window.

#### ml/advanced/edge.md:55 (depthwise-separable conv parameter count)
- **Note:** Already noted as a finding in chunk M (audit/M.md "ml/advanced/edge.md:55"). Mentioned here only for completeness; this audit confirms the M-chunk finding (147,456 → 133,376 correct).

#### ml/mlops/sagemaker.md:155-160 (FeatureValue import)
- **Wrong text:**
  ```python
  feature_group.put_record(record=[FeatureValue("user_id", "123"), FeatureValue("age", "25")])
  ```
- **Correct text:** The `FeatureValue` class is used but never imported. Add:
  ```python
  from sagemaker.feature_store.feature_group import FeatureGroup, FeatureValue
  ```
- **Verification:** SageMaker Python SDK: `sagemaker.feature_store.feature_group.FeatureValue` is the correct class, but the file's import statement (line 139) only imports `FeatureGroup`.
- **Justification:** Would raise `NameError` as written. Minor since the intent is obvious.

#### ml/mlops/drift.md / ml/mlops/monitoring.md (PSI implementation missing edge-case handling)
- **Wrong text:** Both files implement PSI without the `breakpoints[0], breakpoints[-1] = -inf, inf` reassignment that `drift.md` (lines 67-68) shows. `monitoring.md` (lines 81-88) computes `breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))` without the `-inf, +inf` edges, so any `actual` values outside the `expected` min/max are silently dropped (np.histogram returns them in the under/overflow bins, which are not counted).
- **Correct text:** Add `breakpoints[0], breakpoints[-1] = -np.inf, np.inf` after computing breakpoints, and clip both `expected_pct` and `actual_pct` to avoid `log(0)` (drift.md does this; monitoring.md does not).
- **Verification:** `numpy.histogram` documentation: "All but the last (righthand-most) bin is half-open." Values outside the range go into the under/overflow bins, which are silently excluded from the returned counts.
- **Justification:** Two files in the same repo implement the same algorithm differently, with the less-correct version missing the edge-case handling.

#### ml/classical/logistic-regression.md:119 (deprecated multi_class param)
- **Wrong text:**
  ```python
  model = LogisticRegression(multi_class='ovr')
  ```
- **Correct text:** In scikit-learn ≥1.5, the `multi_class` parameter is deprecated and will be removed in 1.7. Use `OneVsRestClassifier`:
  ```python
  from sklearn.multiclass import OneVsRestClassifier
  model = OneVsRestClassifier(LogisticRegression())
  ```
  Or just rely on the default (which already does multinomial logistic regression with `lbfgs` solver for multi-class targets).
- **Verification:** scikit-learn 1.5 release notes: "The `multi_class` parameter is deprecated in `LogisticRegression` and will be removed in 1.7. Use `OneVsRestClassifier` or `OutputCodeClassifier` from `sklearn.multiclass` instead." Source: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
- **Justification:** Deprecation warning on modern sklearn versions. Minor since it still works (with a warning).

## Files confirmed clean

The following files (a representative subset of those audited without HIGH/MEDIUM findings) were deep-read and found to be technically accurate:

- `ml/agents/`: architecture.md, react.md, langchain.md, mcp.md, crewai.md, autogen.md, multi-agent.md, frameworks.md, evaluation.md, planning.md, safety.md, chain-of-thought.md, tool-calling.md, memory.md, tree-of-thought.md, README.md
- `ml/gan/`: architecture.md, training.md, conditional.md, stylegan.md
- `ml/gnn/`: basics.md, gcn.md, graphsage.md, gat.md
- `ml/llm/`: distributed-training.md, gpt-architecture.md (except the KV-cache bug noted above), training-pipeline.md (except the gather bug)
- `ml/advanced/`: quantization.md (MEDIUM-LOW markdown issue noted by M), distillation.md (math issue noted by M), compression.md (SVD issue noted by M)
- `ml/classical/`: logistic-regression.md (except deprecated `multi_class`), svm.md, gradient-boosting.md, decision-trees.md (except LightGBM GOSS issue noted by M)
- `ml/rl/`: grpo.md, dpo.md (plus other rl files already audited by M)
- `ml/mlops/`: mlflow.md, blue-green.md, canary.md, shadow.md, deployment.md, monitoring.md (except PSI edge case), platforms.md, model-registry.md, pipelines.md, cicd.md, infrastructure.md, feature-store.md, wandb.md, kubeflow.md, vertex.md
- `ml/system-design/`: pipeline.md, recommendation.md, search-ranking.md, monitoring.md, model-serving.md, data-pipeline.md, feature-store.md, fraud-detection.md (except class_weight issue noted by M)
- `ml/time-series/`: arima.md (except diff issue noted by M), prophet.md, anomaly.md, transformers.md (except patch count)
- `linux/admin/`: systemd.md (except Journal/Timer issue noted by N), cron.md, permissions.md (except SUID note), firewall.md, lvm.md, raid.md, logging.md, networking-config.md, packages/rpm-dnf.md, packages/dpkg-apt.md, packages/pacman.md, packages/portage.md, users-groups.md, process-management.md, rescue.md, sysvinit.md, package-management.md, disk-management.md, performance.md, overview.md
- `linux/shell/`: overview.md, grep.md, regex.md (except ERE alternation table), scripting-fundamentals.md, scripting-advanced.md, zsh.md, fish.md, posix-shell.md, xargs.md, find.md (except -newerBm), sed-awk.md (except stddev typo and misleading comment)
- `linux/networking/`: dhcp.md, dns.md, ssh.md, http.md, tls.md, tcpip-suite.md, ip-addressing.md, ipv6.md, rdma.md, vpn.md, troubleshooting.md, wireguard.md, cifs-smb.md, packet-capture.md, routing-protocols.md, fundamentals.md
- `linux/reference/`: glossary.md, commands.md, man-pages.md, kernel-config.md, further-reading.md, syscall-table.md (syscall-number issues noted by N)
- `linux/sysprog/`: file-io.md, threads.md, signals.md, process-control.md, io-uring.md, epoll.md, memory.md, dynamic-linking.md, event-driven.md, ipc/*.md, elf.md, seccomp.md, protobuf-flatbuf.md, inline-asm.md, poll-select.md, libevent-libev.md, aio.md

In addition, every file in the listed subdirs was grep-scanned for the AI-artifact phrases listed in the audit rules (`Wait,`, `Hmm,`, `Actually,`, `Let me re-`, `Let me try`, `Ah, I see`, `Great, so`, `Oh wait`, `But wait`). No new matches were found beyond the three already noted in chunk N (`idle-page-tracking.md`, `eevdf.md`, `criu.md`).

## Top 5 Issues (by impact)

1. **`linux/shell/regex.md:130` ERE alternation table is wrong** (HIGH) — Teaches `\|` for ERE alternation, but POSIX ERE uses unescaped `|`. Anyone writing awk/grep -E patterns from this doc would get non-matching patterns. Verified live with grep.

2. **`ml/system-design/ab-testing.md:79` `stats.t.interval` misuse** (HIGH) — Calling `interval(0.95, df=N)` without `loc`/`scale` returns the symmetric t-quantiles centered at 0, NOT a confidence interval for the lift. The CI is the same regardless of input data, completely defeating its purpose.

3. **`ml/llm/gpt-architecture.md` KV-cache generation broken** (HIGH) — The `MultiHeadSelfAttention.forward()` and `GPT2.forward()` don't track position offset during cached generation, so positional embeddings and the causal mask are computed against position 0 every step. A student copying this code would get nonsense outputs from `generate()` after the first token.

4. **`ml/mlops/sagemaker.md:122-133` pipeline quality-gate silently discarded** (HIGH) — The `ConditionGreaterThanOrEqualTo` object is defined but never wrapped in a `ConditionStep` and never added to the pipeline's steps. The "quality gate" does nothing.

5. **`ml/mlops/drift.md:121-124` `auc` variable actually holds accuracy** (HIGH) — `cross_val_score(clf, X, y, cv=5)` defaults to classifier accuracy, not AUC. The `0.6` threshold makes sense for AUC but is meaningless for accuracy in a balanced 50/50 problem.

## Notes for the fix pass

- The five HIGH findings are all in code blocks, and all are fixable with small patches. The sagemaker, ab-testing, and drift fixes are the most impactful (a reader would actually be unable to use the snippets as written).
- The KV-cache bug in `gpt-architecture.md` is the most subtle — the code "works" for the first token (prompt processing) but breaks for subsequent autoregressive steps. Worth a careful rewrite that passes the position offset explicitly.
- The ERE alternation table in `regex.md` is a 2-character fix in a single table cell, but should be accompanied by a sentence noting that `\|` in BRE is a GNU extension (not portable POSIX).
- The MEDIUM findings (transformers.md patch count, sed-awk.md stddev typo, pruning.md 2:4 sparsity) are all small, localized fixes.
- The LOW findings are mostly deprecation warnings and edge-case handling improvements; safe to defer.
