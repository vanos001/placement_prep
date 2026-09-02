# Federated Learning: Systems and Algorithms

Federated Learning (FL) is a distributed training paradigm in which the data never leaves its origin device. A central *coordinator* broadcasts a model, each participant runs several local SGD steps, and only the resulting model updates are sent back. McMahan, Moore, Ramage, Hampson, and y Arcas introduced the canonical algorithm, **FedAvg**, in 2017. It now trains Google's Gboard next-word prediction on hundreds of millions of phones, is the backbone of Apple's "private on-device" models, and is being standardised by the Linux Foundation's OpenMined/PySyft and Google's TensorFlow Federated (TFF) projects.

This chapter covers the formal FL framework, the FedAvg algorithm and its convergence properties, the practical engineering of secure aggregation and differential privacy in FL, the open-source frameworks, and the production deployments that have moved FL from research curiosity to deployed infrastructure.

## The FL Framework

A *federated learning* problem is the tuple `(K, P_k, n_k, F_k, T)`, where `K` clients are available for participation, `P_k` is the local data distribution of client `k`, `n_k = |P_k|`, `F_k` is the local objective `F_k(w) = E_{x ∼ P_k}[ℓ(w; x)]`, and `T` is the round budget. The global objective is the *weighted* average:

```text
F(w) = Σ_k (n_k / n) · F_k(w)         where n = Σ_k n_k
```

The minimiser of `F` may differ from any individual `F_k`'s minimiser — this is the **non-IID** situation that distinguishes FL from conventional distributed training. In the IID case (every `P_k` equal), `F_k = F` and the problem reduces to distributed SGD. In the non-IID case, the gradients `∇F_k` can point in opposite directions, and naive averaging can slow convergence or even diverge.

The four canonical FL challenges (from McMahan et al., 2017):

1. **Non-IID data** — clients have heterogeneous distributions.
2. **Unbalanced** — some clients have 10 examples, others 10M.
3. **Massively distributed** — K can be 10^6–10^9.
4. **Limited communication** — mobile bandwidth is ~1 MB/s uplink, and clients disappear mid-round.

## The FedAvg Algorithm

FedAvg is **local SGD with periodic averaging**. Each round:

```text
Server state: w_t (current global model)
─────────────────────────────────────────
1. Server broadcasts w_t to a subset S_t of m clients.
2. Each client k ∈ S_t initializes w_k ← w_t, then runs
   E local epochs of SGD on its n_k examples:
       for e = 1..E:
           for batch B ⊂ P_k of size B:
               w_k ← w_k - η · (1/|B|) Σ_{x ∈ B} ∇ℓ(w_k; x)
3. Each client sends w_k back (or the delta Δw_k = w_k - w_t).
4. Server aggregates:
       w_{t+1} = Σ_{k ∈ S_t} (n_k / n_{S_t}) · w_k
       where n_{S_t} = Σ_{k ∈ S_t} n_k.
```

The two key hyperparameters beyond vanilla SGD: `E` (local epochs — typically 1–5 for mobile, more for cross-silo) and `m` (clients per round — typically a small fraction of `K`, e.g., 0.1% of available devices).

### Convergence

Under convexity, FedAvg with appropriate step sizes converges to the global optimum at rate `O(1/√T)` — the same asymptotic rate as centralised SGD, but with an additive bias term proportional to the variance of `∇F_k - ∇F` (the non-IID drift). Li, Sahu, Zaheer, Sanjabi, Talwalkar and Smith (2020) proved that FedAvg with `E → ∞` can diverge; with decaying `η` and bounded `E`, it converges in expectation. In practice, **FedProx** (Li et al., 2018) adds a proximal term `μ/2 · ||w_k - w_t||²` to the local objective, keeping clients close to the broadcast model and giving theoretical guarantees for arbitrary heterogeneity.

### Communication cost

A naive FedAvg round transfers `2 |w|` bytes per client per round (`|w|` down + `|w|` up). For a 100M-parameter model at fp32, that is 400 MB per round per client — unaffordable on mobile. Two standard optimisations:

- **Gradient/Update sparsification** — send only the top-k largest components (e.g., top 1% of update deltas by absolute value); combined with error feedback, near-lossless.
- **Quantization** — encode each parameter with 8 or fewer bits; often paired with a 4-bit "QSGD" scheme.

With both, the per-round cost drops to ~5–20 MB — feasible over cellular networks at off-peak hours.

### FedAvg in pseudocode (server side)

```python
def fedavg(num_rounds, num_clients_per_round, local_epochs, clients,
           model, learning_rate, batch_size):
    w = get_params(model)
    for t in range(num_rounds):
        # 1. Sample a subset of clients (typically uniformly at random)
        S_t = random.sample(clients, num_clients_per_round)
        # 2. Broadcast w to selected clients; each runs local SGD
        results = parallel_map(run_local_training,
                               [(c, w, local_epochs, learning_rate,
                                 batch_size) for c in S_t])
        # 3. Aggregate using n_k / n_{S_t} weights
        n_total = sum(c.n_examples for c in S_t)
        w = {name: sum(c.n_examples / n_total * delta[name]
                       for c, delta in zip(S_t, results))
             for name in w}
        set_params(model, w)
    return model
```

## Local SGD: Why It Works

The intuition for *why* running multiple local SGD steps before averaging still converges is the **drift bound**. After `E` steps of SGD on client `k` with step size `η`, the model drifts away from the broadcast `w_t` by at most:

```text
||w_k - w_t|| ≤ η E G + O(η² E² G²)
```

where `G` is the gradient bound. For small `η E`, the drift is small enough that averaging still works; the aggregation recovers most of the gradient signal. As `E` grows, the *gradient staleness* becomes a problem — clients optimise on stale versions of the model.

The **Scaffold** algorithm (Karimireddy et al., 2020) fixes this with control variates: each client tracks its gradient drift relative to the global, and the server adjusts aggregation with this correction. **FedAvgM** (Hsu et al., 2019) adds server-side momentum to compensate for client drift. **FedAdam** (Reddi et al., 2020) applies Adam at the server level to the aggregated update.

## Privacy in FL

Federated learning alone is **not** privacy-preserving — the model updates `Δw_k` leak information about the local dataset. Two attacks have been demonstrated:

1. **Gradient leakage** (Zhu, Liu, Han, 2019): for a cross-entropy loss, an adversary can recover the input batch from the gradient via optimisation. On a mini-batch of size 1 with a transformer, the recovery is near-perfect.

2. **Membership inference** (Shokri et al., 2017): an attacker can determine whether a specific example was in a client's training set, by observing the change in per-example loss across rounds.

Three defence layers, in increasing strength:

### Secure Aggregation (Bonawitz et al., 2017)

The server must average `m` updates without seeing any individual one. This is implementable with Shamir secret sharing + Diffie-Hellman pairwise masks:

```text
Round 1: pairwise key exchange
    Each pair (i, j) establishes a random scalar u_{ij} = u_{ji}.
    (Using Diffie-Hellman over the secp256k1 curve.)

Round 2: masked update submission
    Client i sends:  v_i + Σ_{j≠i} u_{ij}   (mod p)
    (Sums of pairwise masks are zero across all clients, since
     u_{ij} + u_{ji} = 0 mod p by construction.)

Server: sums all received values; pairwise masks cancel,
        yielding Σ v_i — the desired sum — without ever
        seeing any individual v_i.
```

Cost: ~3× communication overhead vs naive FL, plus two extra rounds. The 2017 Bonawitz scheme handles up to `m` dropouts out of `n` clients using Shamir secret sharing (t-of-n threshold). Google deployed this in Gboard by 2018.

### Differential Privacy in FL (DP-FedAvg)

DP-FedAvg (McMahan, Ramage, Talwar, Zhang, 2018) clips each client's update to bound sensitivity and adds Gaussian noise to the aggregate:

```text
For each client k:
    Δ_k ← Δ_k / max(1, ||Δ_k||_2 / S)        # clip to L2 norm S
Aggregate:
    Δ_global = (1/m) (Σ_k Δ_k + N(0, σ² S² I))
```

The privacy analysis uses the moments accountant (Abadi et al., 2016), tracking Rényi DP across rounds, with a *subsampling amplification* — because each round samples only `m/K` of clients, the per-round privacy amplifies by `~m/K`. With `m=1000` clients out of `K=10^6` and noise `σ = 1.0`, a single round gives ε ≈ 10⁻⁵; over `T=1000` rounds, ε ≈ 1.

Trade-off: the clipping norm `S` is a hyperparameter; setting it too tight destroys useful signal, too loose allows pathological clients to poison the aggregate. Apple's deployment uses adaptive clipping (median `||Δ_k||`).

### Fully Homomorphic / MPC Aggregation

For the strictest threat model (server colludes with subset of clients), FL + FHE provides the strongest guarantee: clients encrypt their updates under a shared public key, the server computes the sum ciphertext homomorphically, and only the decryption (an aggregate sum) is revealed. Apple's iOS 14+ "Private Set Intersection" features use this. Throughput is the bootstrapping-bottleneck cost discussed in the [Homomorphic Encryption](../../llm/advanced/homomorphic-encryption.md) chapter.

## Frameworks

### TensorFlow Federated (TFF)

TFF is the production-grade FL framework from Google. It defines two APIs:

- **Federated Computation API** — for orchestrating the round logic. Compositions are written in a functional, declarative style that TFF serialises to a portable form.
- **Federated Learning API** — high-level training loops (FedAvg, FedProx, FedAdam) with built-in DP and secure aggregation.

```python
import tensorflow as tf
import tensorflow_federated as tff

def model_fn():
    return tff.learning.from_keras_model(
        keras_model=build_keras_model(),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        input_spec=client_data.element_spec,
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()])

iterative_process = tff.learning.build_federated_averaging_process(
    model_fn,
    client_optimizer_fn=lambda: tf.keras.optimizers.SGD(0.1),
    server_optimizer_fn=lambda: tf.keras.optimizers.SGD(1.0))

state = iterative_process.initialize()
for round_num in range(NUM_ROUNDS):
    state, metrics = iterative_process.next(state, train_data)
    print(f"round {round_num}: {metrics}")
```

TFF runs the same code in simulation (one process) as in production (gRPC-fanout to phones). The C++ runtime has been used at Google to train Gboard models since 2017.

### PySyft

PySyft (OpenMined) is the more research-oriented framework, integrating with PyTorch. Beyond vanilla FedAvg, it supports secure multiparty computation, FHE, and DP in a composable "tenseal" stack:

```python
import syft as sy
import torch

hook = sy.TorchHook(torch)
# Simulated workers
alice = sy.VirtualWorker(hook, id="alice")
bob = sy.VirtualWorker(hook, id="bob")
# Send data to workers
dataset = torch.tensor([1., 2., 3., 4.]).send(alice)
model = torch.nn.Linear(1, 1).send(bob)  # actually lives on bob
# Federated training loop ... (omitted for brevity)
```

PySyft 0.7+ (the "Sandbox" architecture) supports grid-based deployment across organisations and integrates with TF-Encrypted and OpenFHE for the cryptographic layers.

### Other frameworks

- **FATE** (WeBank) — enterprise FL, popular in Chinese fintech for cross-bank modelling.
- **Flower** — framework-agnostic, light on infrastructure, popular in academic and edge deployments.
- **NVIDIA FLARE** — federated learning runtime with a focus on healthcare imaging (NVFlare partners with NVIDIA Clara).

## Production Deployments

### Google Gboard

Gboard is the canonical FL deployment (Hard et al., 2018; Ramaswamy et al., 2019). The task: train next-word-prediction models on user typing data on phones, without uploading any text.

Scale: ~10^8 Android phones participate. In each round, ~10^4 phones are sampled. Phones that agree (battery > 50%, charging, idle, on Wi-Fi) download the model, run 5 local epochs on a few hundred to a few thousand typing examples, and upload the update via secure aggregation + DP. Training runs continuously.

Reported gains: +20–30% reduction in incorrect next-word-prediction clicks vs. server-trained baseline on smaller populations. The on-device personalisation (each phone fine-tunes the global model further on its own data after each round) provides additional gains.

Apple uses a similar architecture for next-word prediction (Apple 2017 white paper, Bonawitz et al. learned about it via publication), with secure aggregation being deployed in iOS 13+.

### Federated analytics

Beyond training, FL is used for **federated analytics** — counting how many users use each emoji, the distribution of Safari homepage URLs, etc. Google's "Federated Analytics" pipeline applies the same secure-aggregation + DP stack but the "model" is a histogram. The 2020 Google paper "Federated Heavy Hitters Discovery" describes discovering top-k frequent strings across devices using FL primitives (it's the *private string discovery* problem).

### Healthcare cross-silo FL

Hospitals cannot share patient data (HIPAA in the US, GDPR in Europe). FL trains a model jointly across hospitals without data exchange: each hospital holds its EHR, runs local epochs, shares gradients. The **MELLODDY** consortium (10 pharma companies) trains drug-discovery models across federated internal datasets using FL + DP. **EXAM** (NVIDIA + 20 hospitals, 2020) trained a COVID-19 patient-outcome model in 2 weeks across geographically-separated institutions; without FL, no single institution had enough cases.

## Open Problems and Pitfalls

1. **Client selection bias.** Phones that participate are not random (charged, on Wi-Fi, idle). The model over-fits to *active* users. FedAvg with non-uniform sampling can mitigate but not eliminate.

2. **Free-riders and poisoning.** A malicious client can submit any update — backdoor the model (Bagdasaryan et al., 2020), or simply send garbage. Robust aggregation (Krum, median-of-means) defends but trades off convergence speed.

3. **Stragglers and dropouts.** In production, only ~10% of selected clients complete a round (phones go offline, run out of battery). Secure aggregation must handle dropouts — Bonawitz et al. (2017) handles up to `n/3` dropouts via threshold secret sharing.

4. **Communication vs computation asymmetry.** Modern LLMs (>= 1B params) are too large to ship to phones over cellular networks per round. Compression (8-bit, sparse) helps but does not bridge the gap; on-device LLM training is currently only feasible with cross-silo FL on GPUs.

5. **Forgetting that DP-FedAvg is much weaker than central DP-SGD.** At equal privacy budget, DP-FedAvg gets *worse* utility than central DP-SGD because the per-client gradient is clipped to a single `S` and noise is added per *client* not per *example*. Plan ε accordingly — ε = 8 is barely private for FL training.

6. **Treating "secure aggregation" as a complete privacy solution.** Secure aggregation hides individual updates from the server, but the *aggregate* is still visible. If only one client updates in a round, the aggregate is that client's update — exposed. Use a minimum `m` and consider DP on top.

## References

- Brendan McMahan, Eider Moore, Daniel Ramage, Seth Hampson, Blaise Agüera y Arcas, "[Communication-Efficient Learning of Deep Networks from Decentralized Data](https://arxiv.org/abs/1602.05629)" (AISTATS 2017) — the FedAvg paper
- Keith Bonawitz, Vladimir Ivanov, Ben Kreuter, Antonio Marcedone, Brendan McMahan, Sarvar Patel, Daniel Ramage, Aaron Segal, Karn Seth, "[Practical Secure Aggregation for Privacy-Preserving Machine Learning](https://eprint.iacr.org/2017/281)" (CCS 2017)
- Brendan McMahan, Daniel Ramage, Kunal Talwar, Li Zhang, "[Learning Differentially Private Recurrent Language Models](https://arxiv.org/abs/1710.06963)" (ICLR 2018)
- [TensorFlow Federated documentation](https://www.tensorflow.org/federated)
- [PySyft documentation](https://github.com/OpenMined/PySyft)
- Andrew Hard, Kanishka Rao, Rajiv Mathews, Swaroop Ramaswamy, Françoise Beaufays, Sean Augenstein, Hubert Eichner, Daniel Ramage, "[Federated Learning for Mobile Keyboard Prediction](https://arxiv.org/abs/1811.03604)" (2018) — Gboard deployment
- Teresa Shokri, Marco Stronati, Congzheng Song, Vitaly Shmatikov, "[Membership Inference Attacks Against Machine Learning Models](https://arxiv.org/abs/1610.05820)" (S&P 2017)
- Ligeng Zhu, Zhijian Liu, Song Han, "[Deep Leakage from Gradients](https://arxiv.org/abs/1906.08935)" (NeurIPS 2019) — gradient leakage attacks
- Tian Li, Anit Kumar Sahu, Manzil Zaheer, Maziar Sanjabi, Ameet Talwalkar, Virginia Smith, "[Federated Optimization in Heterogeneous Networks](https://arxiv.org/abs/1812.06127)" (MLSys 2020) — FedProx
- Sai Praneeth Karimireddy, Satyen Kale, Mehryar Mohri, Sashank Reddi, Sebastian Stich, Ananda Theertha Suresh, "[Scaffold: Stochastic Controlled Averaging for Federated Learning](https://arxiv.org/abs/1910.06378)" (ICML 2020)
- S. Reddi, Z. Charles, M. Zaheer, et al., "[Adaptive Federated Optimization](https://arxiv.org/abs/2003.00295)" (ICLR 2021) — FedAdam
- [Flower: A Friendly Federated Learning Framework](https://flower.dev/) — framework-agnostic FL
- Rieke et al., "[The Future of Digital Health with Federated Learning](https://www.nature.com/articles/s41746-020-00323-1)" (npj Digital Medicine, September 2020, doi 10.1038/s41746-020-00323-1) — healthcare FL survey
- Eugene Bagdasaryan, Arjun Veerubhotla, Praneeth Vepakomma, et al., "[How to Backdoor Federated Learning](https://arxiv.org/abs/1907.02933)" (AISTATS 2020)
