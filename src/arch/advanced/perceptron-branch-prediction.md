# Perceptron Branch Prediction: Learning Weights Instead of Counters

A 2-bit saturating counter stores one fact per branch: how biased this branch has been lately. The perceptron predictor, introduced by Jimenez and Lin at HPCA 2001, instead stores a signed weight for every position in the branch history and classifies with a dot product. That one structural change buys history lengths no counter-indexed table can afford (the original paper ran h up to 62, where gshare topped out at 18), and it exposes a hard learning limit -- linear separability -- that explains both why perceptrons stall on XOR-type branches and why the hashed-perceptron variant fixes exactly that.

## Scope: this page vs the TAGE deep dive

[Advanced Branch Prediction](./branch-prediction-advanced.md) in this directory owns the modern predictor lineup: TAGE/ITTAGE table mechanics (tags, useful counters, allocation on mispredict), TAGE-SC-L composition, indirect targets, the return address stack, and speculative history checkpointing. None of that is re-derived here. This page is the perceptron family deep dive: the linear-threshold model, the storage argument for weights, threshold tuning (theta = 1.93h + 14), the parity wall, weight-table aliasing, and where the family actually shipped. The two designs are complementary mechanisms: TAGE is a tagged lookup over history lengths, the perceptron a learned linear model over history bits.

## 1. The storage math that forces the issue

A pattern history table indexed by the full h-bit global history is a truth table: learning an arbitrary function of h bits takes 2^h entries. A perceptron takes h + 1 weights, and that gap is the entire motivation:

| History bits h | Full-history PHT entries | Perceptron weights (h+1) | Weight bits at 8b each |
| -------------- | ------------------------ | ------------------------ | ---------------------- |
| 8              | 256                      | 9                        | 72                     |
| 16             | 65,536                   | 17                       | 136                    |
| 32             | 4,294,967,296            | 33                       | 264                    |
| 62             | 4.61 x 10^18             | 63                       | 504                    |

In their SPECint2000 experiments, Jimenez and Lin found gshare's best history length was 18 even with an unrealistically huge table, while the perceptron predictor kept improving up to h = 62, the longest they simulated. Long-range correlations (loop trip counts, or a branch that depends on an event dozens of branches back) are out of reach for counter-indexed designs at realizable budgets. The counter baseline itself -- bimodal and gshare -- is covered in [basic branch prediction](../pipelining/branch-prediction.md).

## 2. The linear-threshold model

History bits are encoded as x[i] = +1 (taken) or -1 (not-taken). Each branch PC hashes to one weight vector in a table of N perceptrons, and prediction is a signed sum:

```text
        global history register:  x[0]    x[1]    x[2]   ...  x[h-1]
        (+1 taken / -1 not-taken)   |       |       |            |
                                    v       v       v            v
  index = hash(PC)  ---->        w[1]    w[2]    w[3]   ...  w[h]
      |                           \       \       \           /
      |                            +--- multiply-add tree ---+--- w[0] (bias)
      v                                         |
  [ table of N weight vectors ]                 v
                                    y = w0 + sum( w[i] * x[i] )
                                                |
                                    y >= 0 ? TAKEN : NOT-TAKEN
```

The bias weight w0 sees a constant input of 1, so it learns the branch's unconditional bias -- the same job a bimodal counter does. Every other weight learns how much one history position matters, and the sign is free: w[i] < 0 means "when the branch i positions ago was taken, this branch tends to be not-taken." A saturating counter cannot express anti-correlation with another branch at all; it only counts its own marginal bias. Correlated branches (an error branch taken only after some other branch failed a check) are where the model starts winning.

## 3. Training and the 1.93h + 14 threshold

Training is one signed add per weight. With t = +1/-1 for the resolved outcome, update whenever the prediction was wrong OR barely right:

```text
  if sign(y) != t or |y| <= theta:
      for i = 0..h:  w[i] += t * x[i]      # x[0] = 1 feeds the bias weight
```

Training on confident correct predictions would be wasted work, but training on weak ones (|y| <= theta) matters: it keeps the margin above theta so a phase change in program behavior shows up quickly instead of hiding inside a coin-flip margin. theta must scale with history length -- with more summed terms, a random or aliased weight vector produces larger |y| by chance, so the "confident" bar has to rise. The HPCA 2001 paper swept both parameters and found the best threshold was always exactly theta = 1.93h + 14, with weight widths from 7 bits (h = 12) to 9 bits (h = 62), clamped to their signed range:

| History h | theta = int(1.93h + 14) | Weights per perceptron | Bits at 8b weights |
| --------- | ----------------------- | ---------------------- | ------------------ |
| 12        | 37                      | 13                     | 104                |
| 16        | 44                      | 17                     | 136                |
| 32        | 75                      | 33                     | 264                |
| 62        | 133                     | 63                     | 504                |

## 4. The parity wall: where linear separability ends

A function is linearly separable if some hyperplane puts all its +1 outputs on one side and all its -1 outputs on the other; perceptrons learn exactly those functions and nothing else. The canonical failure is XOR (parity). In the {-1,+1} domain the XOR of two bits is their product, and demanding a perfect linear classifier ends in contradiction:

```text
  want: w0 + w1*x1 + w2*x2 >= 0  exactly when  y = x1*x2 = +1

    (x1, x2) -> y     constraint
    (+1, +1) -> +1    w0 + w1 + w2 >= 0
    (+1, -1) -> -1    w0 + w1 - w2 <  0
    (-1, +1) -> -1    w0 - w1 + w2 <  0
    (-1, -1) -> +1    w0 - w1 - w2 >= 0

  (first + last):  2*w0 >= 0       (middle two):  2*w0 < 0    ->  impossible
```

The same orthogonality kills longer parities: for outcome = XOR of any subset of history bits, E[t * x[i]] = 0 for every position, so the best linear model is all-zero weights and the error floor is a coin flip. This is not a corner case -- Jimenez measured that linearly inseparable branches account for about 50% of all branches and almost all of the mispredictions (ACM TOCS 2005). The design space is therefore a three-way trade:

| Structure                      | Cost per branch     | Outcome functions learnable                       |
| ------------------------------ | ------------------- | ------------------------------------------------- |
| Full-history PHT (truth table) | 2^h counters        | any function of the h bits                        |
| Classic perceptron             | h + 1 weights       | linearly separable only                           |
| Hashed perceptron (groups)     | a few small tables  | patterns that factor through the group partitions |

The hashed perceptron (Tarjan and Skadron, ACM TACO 2005) subdivides history into segments, hashes each segment (typically XOR with the branch PC) into an index, and looks up one weight per table; every looked-up weight's input is the constant 1. Because a weight is now indexed by a whole group of bits, it learns the conjunction of those bits -- in the paper's words, "each table acts like a small gshare predictor." A group covering exactly the four bits a parity depends on is a 16-entry truth table over them. The demo below shows all three regimes in one run.

## 5. Runnable demo: periodic vs parity vs hashed

Pure standard library, deterministic (fixed seed). The periodic pattern is a loop of 7 taken then 1 not-taken, seen through a 16-bit history register. The parity pattern's outcome is the XOR of 4 fresh independent bits, handed to the predictor directly as its 4 inputs -- the fairest possible test, since extra inputs cannot help a linear model whose target is orthogonal to each input. theta always follows the 1.93h + 14 rule.

```python
import random

H = 16                           # history length in bits
THETA16 = int(1.93 * H + 14)     # 44: empirical threshold rule, HPCA 2001
THETA4 = int(1.93 * 4 + 14)      # 21: same rule for the 4-input variants
CLAMP = 127                      # weights are 8-bit signed in hardware
EPOCHS, STEPS, SEED = 4, 4000, 7

def clamp(v):
    return max(-CLAMP, min(CLAMP, v))

class ClassicPerceptron:
    # y = w0 + sum(w[i]*x[i]), x[i] in {-1,+1}; predict TAKEN iff y >= 0
    def __init__(self, n_inputs, theta):
        self.w = [0] * (n_inputs + 1)        # w[0] is the bias weight
        self.theta = theta
    def predict(self, x):
        return self.w[0] + sum(wi * xi for wi, xi in zip(self.w[1:], x))
    def train(self, x, y, actual):
        t = 1 if actual else -1
        if t * y <= self.theta:              # wrong, or right but weak
            for i, xi in enumerate([1] + list(x)):
                self.w[i] = clamp(self.w[i] + t * xi)

class HashedPerceptron(ClassicPerceptron):
    # weights INDEXED by the whole 4-bit group, input constant 1
    # (Tarjan & Skadron 2005) -- one entry per full history pattern
    def index(self, x):
        idx = 0
        for xi in x:                         # pack +-1 bits into 0..15
            idx = idx * 2 + (1 if xi == -1 else 0)
        return idx
    def predict(self, x):
        return self.w[self.index(x)]
    def train(self, x, y, actual):
        t = 1 if actual else -1
        if t * y <= self.theta:
            self.w[self.index(x)] = clamp(self.w[self.index(x)] + t)

def gen_periodic(step, rng):
    actual = (step % 8) != 7                 # loop: 7 taken, then 1 not-taken
    return PERIODIC_HIST[:], actual          # inputs: last 16 outcomes

def gen_xor(step, rng):
    bits = [rng.getrandbits(1) for _ in range(4)]   # 4 independent bits
    actual = (sum(bits) % 2) == 1            # outcome = XOR (parity)
    return tuple(1 - 2 * b for b in bits), actual   # {-1,+1} encoding

def run(title, note, gen, predictor):
    print(f"[{title}] {note}")
    rng, step = random.Random(SEED), 0
    for epoch in range(EPOCHS):
        wrong = 0
        for _ in range(STEPS):
            x, actual = gen(step, rng)
            y = predictor.predict(x)
            if (y >= 0) != actual:
                wrong += 1
            predictor.train(x, y, actual)
            if title == "A":                 # slide the history register
                PERIODIC_HIST.insert(0, 1 if actual else -1)
                PERIODIC_HIST.pop()
            step += 1
        print(f"  epoch {epoch}: mispredicted {wrong:4d}/{STEPS} = {100.0*wrong/STEPS:5.2f}%")

PERIODIC_HIST = [1] * H          # global history register, most recent first
print("perceptron branch prediction demo (Jimenez & Lin, HPCA 2001)")
print(f"h = {H}, theta = int(1.93*h + 14) = {THETA16}; weights clamped to +/-{CLAMP}")
print(f"each pattern: {EPOCHS} epochs x {STEPS} branches, seed {SEED}")
print()
run("A", f"periodic TTTTTTTN loop, 16 history-bit inputs (theta = {THETA16}) -- linearly separable",
    gen_periodic, ClassicPerceptron(H, THETA16))
print()
run("B", f"parity (XOR) of 4 independent bits, 4 inputs (theta = {THETA4}) -- NOT linearly separable",
    gen_xor, ClassicPerceptron(4, THETA4))
print()
run("C", f"same parity bits, one 16-entry hashed group table (theta = {THETA4}) -- index = the 4 bits",
    gen_xor, HashedPerceptron(16, THETA4))
```

Output (verbatim from one run; re-running reproduces it bit for bit):

```text
perceptron branch prediction demo (Jimenez & Lin, HPCA 2001)
h = 16, theta = int(1.93*h + 14) = 44; weights clamped to +/-127
each pattern: 4 epochs x 4000 branches, seed 7

[A] periodic TTTTTTTN loop, 16 history-bit inputs (theta = 44) -- linearly separable
  epoch 0: mispredicted    8/4000 =  0.20%
  epoch 1: mispredicted    0/4000 =  0.00%
  epoch 2: mispredicted    0/4000 =  0.00%
  epoch 3: mispredicted    0/4000 =  0.00%

[B] parity (XOR) of 4 independent bits, 4 inputs (theta = 21) -- NOT linearly separable
  epoch 0: mispredicted 2034/4000 = 50.85%
  epoch 1: mispredicted 2096/4000 = 52.40%
  epoch 2: mispredicted 2009/4000 = 50.23%
  epoch 3: mispredicted 2012/4000 = 50.30%

[C] same parity bits, one 16-entry hashed group table (theta = 21) -- index = the 4 bits
  epoch 0: mispredicted    8/4000 =  0.20%
  epoch 1: mispredicted    0/4000 =  0.00%
  epoch 2: mispredicted    0/4000 =  0.00%
  epoch 3: mispredicted    0/4000 =  0.00%
```

Reading it: [A] converges almost immediately (8 misses, all from the zero-weight cold start) because a period-8 loop is linearly separable over a 16-bit window. [B] never leaves the ~50% floor no matter how many epochs it gets -- that is the linear-separability limit, not a tuning problem. [C] nails the same bits because the group index turns the weight table into a truth table over them.

## 6. Weight-table aliasing and latency

The storage win has a price. With h + 1 weights per entry, a fixed SRAM budget buys fewer perceptrons as h grows, so PC-hashing aliasing gets worse exactly when accuracy should improve:

| Budget | History h | Bits per perceptron | Perceptrons in the table |
| ------ | --------- | ------------------- | ------------------------ |
| 16 KB  | 12        | 13 x 7 = 91         | ~1,440                   |
| 16 KB  | 62        | 63 x 9 = 567        | ~231                     |

This is why the paper tunes h by exhaustive search per budget; the best h ranged from 12 to 62. Aliasing also hurts differently than in gshare: two conflicting branches share an entire weight vector, so a hostile branch corrupts every learned history correlation at once, and recovery takes many re-trainings rather than one counter flip. Prediction latency is real too: the dot product is h + 1 multiply-accumulates, and the original design needed a dedicated adder tree plus arithmetic shortcuts to fit one cycle, while Tarjan and Skadron's hashed perceptron is ahead-pipelined to a one-cycle effective latency. In a real front end these weights are updated speculatively and restored on mispredicts -- the same checkpointing machinery TAGE needs, described in [Advanced Branch Prediction](./branch-prediction-advanced.md). A mispredict is not just a predictor problem: the whole speculative window refills, as covered in [Out-of-Order Execution](./ooo-execution.md).

## 7. The perceptron family in the wild

**CBP-1 (2004).** The first Championship Branch Prediction, run by JILP in conjunction with MICRO-37, gave every entrant the same storage budget on a common evaluation framework. The champion on the held-out trace set was a perceptron refinement, not a table predictor:

| Finalist (first author) | Predictor family                     | MPKI (final round) |
| ----------------------- | ------------------------------------ | ------------------ |
| Gao & Zhou              | adaptive perceptron                  | 2.574              |
| Seznec                  | O-GEHL (geometric-length linear)     | 2.627              |
| Loh                     | Frankenpredictor                     | 2.700              |
| Jimenez                 | idealized piecewise-linear           | 2.742              |
| Michaud                 | PPM-like tag-based                   | 2.777              |
| Desmet et al.           | 2bcgskew + skewed-history perceptron | 2.807              |
| (reference)             | equal-size gshare                    | 4.520              |

O-GEHL is the linear-sum ancestor of the tagged-geometric lineage; the TAGE design it evolved into, and the TAGE-SC-L composition that today's cores ship, are covered in [Advanced Branch Prediction](./branch-prediction-advanced.md). Tarjan and Skadron's group indexing (index[j] = (history segment[j] XOR branch PC) mod table size) merged gshare's indexing with perceptron weights, handling linearly inseparable branches while keeping one-cycle effective latency via ahead pipelining. AMD never published an academic paper on Zen's predictor, but the public record is consistent: Wikipedia's Zen (first generation) article describes conditional prediction "using a hashed perceptron system with Indirect Target Array similar to the Bobcat microarchitecture", attributing the characterization to AMD lead architect Mike Clark, who discussed the design as neural-network-like in 2016. Treat "Zen is neural" claims in interviews as marketing shorthand for hashed-perceptron weights, sourced from engineer statements rather than a reviewed publication. And the idea survives at the top of the field: TAGE-SC-L's statistical corrector is a set of small linear feature sums correcting systematic biases of the TAGE provider -- perceptron thinking as the corrector rather than the main table.

## 8. Interview drill

- **Why encode history as {-1,+1} instead of {0,1}?** Prediction becomes a multiply-add (in hardware, conditional increments), and weight signs express anti-correlation; a 0/1 encoding can only accumulate positive evidence.
- **Why train when the prediction was correct but |y| <= theta?** To keep the margin above theta; a weight that stops being exercised decays toward the coin-flip zone and the branch silently becomes unpredictable.
- **Why does theta grow with h?** |y| of an untrained or aliased vector scales with the number of summed terms, so the confidence bar must scale too; empirically theta = 1.93h + 14.
- **Why can no perceptron predict a 4-bit parity branch perfectly, given unbounded training time?** Parity is orthogonal to every single history bit (E[t * x[i]] = 0), so the optimal linear model is zero; the perceptron convergence theorem guarantees termination only for separable functions.
- **How does the hashed perceptron escape that without 2^h storage?** It hashes groups of history bits into weight indexes, so each weight learns a conjunction of bits; a group covering the relevant bits acts as a small truth table at a fraction of the entries.
- **Where do perceptrons appear in a modern TAGE-SC-L front end?** As the statistical corrector's linear sums, not as the primary provider table.

## References

1. D. A. Jimenez and C. Lin, "Dynamic Branch Prediction with Perceptrons," HPCA 2001. DOI [10.1109/HPCA.2001.903263](https://doi.org/10.1109/HPCA.2001.903263); open PDF: <https://www.cs.utexas.edu/~lin/papers/hpca01.pdf> (probed, 200).
2. D. A. Jimenez and C. Lin, "Neural Methods for Dynamic Branch Prediction," ACM Transactions on Computer Systems 20(4), 2002. DOI [10.1145/571637.571639](https://doi.org/10.1145/571637.571639) (ACM landing page 403s to curl; record verified via DBLP and Semantic Scholar).
3. D. A. Jimenez, "Improved Latency and Accuracy for Neural Branch Prediction," ACM Transactions on Computer Systems 23(4), 2005. DOI [10.1145/1062247.1062250](https://doi.org/10.1145/1062247.1062250); open PDF: <https://people.engr.tamu.edu/djimenez/pdfs/tocs05.pdf> (probed, 200).
4. D. Tarjan and K. Skadron, "Merging Path and Gshare Indexing in Perceptron Branch Prediction" (the hashed perceptron), ACM Transactions on Architecture and Code Optimization 2(3), 2005. DOI [10.1145/1089008.1089011](https://doi.org/10.1145/1089008.1089011); author PDF: <https://www.cs.virginia.edu/~skadron/Papers/taco_bpred_sep05.pdf> (probed, 200).
5. A. Seznec and P. Michaud, "A case for (partially) TAgged GEometric history length branch prediction," Journal of Instruction-Level Parallelism, vol. 8, 2006: <https://jilp.org/vol8/v8paper1.pdf> (probed, 200).
6. Championship Branch Prediction (CBP-1) site and 2004 workshop results: <https://jilp.org/cbp/> and <https://jilp.org/cbp/Agenda-and-Results.htm> (probed, 200).
7. Wikipedia, "Zen (first generation)" -- hashed-perceptron description of Zen's conditional predictor attributed to AMD architect Mike Clark: <https://en.wikipedia.org/wiki/Zen_(first_generation)> (probed, 200).

## Cross-References

- [Advanced Branch Prediction](./branch-prediction-advanced.md) -- TAGE/ITTAGE mechanics, TAGE-SC-L, indirect targets, RAS, speculative history checkpointing
- [Basic Branch Prediction](../pipelining/branch-prediction.md) -- 2-bit counters, bimodal, gshare: the counter baseline this page replaces
- [Out-of-Order Execution](./ooo-execution.md) -- where predicted paths are consumed and what a front-end flush costs
