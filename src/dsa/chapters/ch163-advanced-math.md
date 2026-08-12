# Chapter 163: Advanced Mathematics for Algorithms

## Prerequisites
- Linear algebra (matrices, eigenvalues)
- Probability and statistics
- Calculus basics
- Discrete mathematics

## Interview Frequency: ★

Advanced mathematical tools underpin many algorithmic techniques: dimensionality reduction, randomized algorithms, compression, optimization, and analysis of convergence. While rarely tested directly in interviews, these tools appear in systems design, machine learning pipelines, and algorithm analysis. Understanding them elevates you from "coder" to "algorithm designer."

---

## 163.1 Motivation and Intuition

### Why Mathematics Matters for Algorithms

Algorithms don't exist in a vacuum. They solve problems that have mathematical structure:
- **Linear algebra**: Matrix operations power graphics, ML, and graph algorithms
- **Probability**: Randomized algorithms, hash functions, load balancing
- **Information theory**: Compression, entropy, coding
- **Markov chains**: Random walks, PageRank, mixing processes
- **Martingales**: Concentration bounds, stopping times

### The Big Picture

| Math Tool | Algorithm Application | Example |
|---|---|---|
| Linear algebra | Graph algorithms, ML | PageRank, PCA |
| Probability | Randomized algorithms | QuickSelect, Bloom filters |
| Entropy | Compression, decision trees | Huffman coding |
| Markov chains | Random walks, sampling | MCMC, PageRank |
| Martingales | Concentration bounds | Chernoff, Azuma |
| Generating functions | Recurrence solving | Counting problems |
| Number theory | Cryptography, hashing | RSA, universal hashing |

---

## 163.2 Linear Algebra Review

### Eigenvalues and Eigenvectors

For matrix A, if Av = λv, then λ is an eigenvalue and v is the corresponding eigenvector.

**Properties**:
- A symmetric n×n matrix has n real eigenvalues
- The largest eigenvalue λ₁ determines growth rate
- The spectral gap (λ₁ - λ₂) determines convergence rate

### Matrix Decompositions

| Decomposition | Form | Conditions | Use |
|---|---|---|---|
| **Eigendecomposition** | A = QΛQ⁻¹ | Square, diagonalizable | Understanding dynamics |
| **SVD** | A = UΣVᵀ | Any matrix | Low-rank approximation |
| **LU** | A = LU | Square, nonsingular | Solving Ax = b |
| **QR** | A = QR | Full column rank | Least squares |
| **Cholesky** | A = LLᵀ | Symmetric positive definite | Fast positive-definite systems |

### Spectral Graph Theory

The adjacency matrix A and Laplacian L = D - A of a graph encode its structure:
- **Algebraic connectivity** (second smallest eigenvalue of L): Measures graph connectivity
- **Spectral partitioning**: Eigenvector of L₂ gives a good graph cut
- **Random walk mixing**: Related to eigenvalues of the transition matrix

---

## 163.3 Singular Value Decomposition (SVD)

Any m×n matrix A can be factored as:

```
A = U Σ Vᵀ
```

Where:
- **U** (m×m): Orthogonal matrix. Columns are left singular vectors.
- **Σ** (m×n): Diagonal matrix. Diagonal entries σ₁ ≥ σ₂ ≥ ... ≥ 0 are singular values.
- **V** (n×n): Orthogonal matrix. Columns are right singular vectors.

### Properties

1. σᵢ² are eigenvalues of AᵀA (or AAᵀ)
2. **Best rank-k approximation**: Aₖ = UₖΣₖVₖᵀ minimizes ‖A - B‖ among all rank-k matrices B (Eckart-Young theorem)
3. **Low-rank approximation** captures most of the "energy" with few components

### Applications

**Principal Component Analysis (PCA)**:
1. Center data (subtract mean)
2. Compute SVD of data matrix
3. Top-k right singular vectors are the principal components
4. Project data onto these components for dimensionality reduction

**Recommendation Systems (Matrix Factorization)**:
- User-item rating matrix R is sparse
- Approximate R ≈ UΣVᵀ with low rank
- Predict missing ratings from the approximation

**PageRank**:
- The dominant eigenvector of the web graph's transition matrix
- Power iteration: v ← Av / ‖Av‖ converges to the dominant eigenvector

### Dry Run: Power Iteration for Dominant Singular Vector

Given A = [[1, 2], [3, 4], [5, 6]]:

```
Initialize: v = [1/√2, 1/√2] ≈ [0.707, 0.707]

Iteration 1:
  u = Av = [1×0.707 + 2×0.707, 3×0.707 + 4×0.707, 5×0.707 + 6×0.707]
        = [2.121, 4.950, 7.778]
  v = Aᵀu = [1×2.121 + 3×4.950 + 5×7.778, 2×2.121 + 4×4.950 + 6×7.778]
        = [55.841, 68.286]
  Normalize: v = [55.841, 68.286] / ‖[55.841, 68.286]‖
        ≈ [0.633, 0.774]

Iteration 2:
  u = Av = [2.181, 5.007, 7.833]
  v = Aᵀu = [56.183, 68.702]
  Normalize: v ≈ [0.634, 0.773]

Converges to v ≈ [0.634, 0.773] (dominant right singular vector)
```

The dominant singular value σ₁ ≈ ‖Av‖ ≈ 9.534.

---

## 163.4 Markov Chains

### Definition

A Markov chain is a stochastic process {X₀, X₁, X₂, ...} where:

```
P(X_{n+1} = j | X₀, X₁, ..., Xₙ) = P(X_{n+1} = j | Xₙ)
```

The future depends only on the present, not the past (memoryless property).

### Transition Matrix

P is an n×n matrix where P_ij = P(X_{n+1} = j | Xₙ = i).

Properties:
- All entries are non-negative
- Each row sums to 1 (stochastic matrix)

### Stationary Distribution

A distribution π is stationary if π = πP. It exists and is unique for:
- **Irreducible** chains: Can reach any state from any state
- **Aperiodic** chains: Not stuck in cycles

**Interpretation**: In the long run, the fraction of time spent in state i is πᵢ.

### Mixing Time

The number of steps until the distribution is "close" to stationary:

```
t_mix(ε) = min{t : max_x ‖P^t(x, ·) - π‖₁ ≤ ε}
```

**Spectral bound**: t_mix ≤ O(log(1/ε) / (1 - λ₂))

where λ₂ is the second-largest eigenvalue of P (spectral gap = 1 - λ₂).

### Example: Random Walk on a Graph

At each step, move to a random neighbor. The transition matrix is:

```
P_ij = 1/deg(i) if (i,j) is an edge, 0 otherwise
```

For a regular graph (all degrees equal d):
```
π = [1/n, 1/n, ..., 1/n]  (uniform distribution)
```

Mixing time depends on the graph's spectral gap. Expander graphs mix in O(log n) steps.

### PageRank

The web graph's transition matrix with a damping factor d (typically 0.85):

```
M = d × P + (1-d) × (1/n) × J
```

where J is the all-ones matrix. This ensures irreducibility and aperiodicity.

PageRank is the dominant eigenvector of M, computed by power iteration.

---

## 163.5 Entropy and Information Theory

### Shannon Entropy

For a discrete random variable X with distribution p:

```
H(X) = -Σₓ p(x) log₂ p(x)
```

**Properties**:
- H(X) ≥ 0
- H(X) ≤ log₂ |X| (maximum when uniform)
- H(X) = 0 iff X is deterministic

### Interpretation

Entropy measures the average "surprise" or information content:
- Fair coin: H = 1 bit (maximum uncertainty)
- Biased coin (90% heads): H ≈ 0.47 bits (less uncertainty)
- Deterministic: H = 0 bits (no information)

### Entropy in Algorithms

**Compression (Huffman, Arithmetic Coding)**:
- Entropy is the theoretical lower bound on average code length
- Huffman coding achieves within 1 bit of entropy per symbol

**Decision Trees**:
- Information gain = H(parent) - weighted H(children)
- ID3/C4.5 use entropy to select the best split

**Machine Learning**:
- Cross-entropy loss: L = -Σ yᵢ log(ŷᵢ)
- KL divergence: D_KL(p||q) = Σ p(x) log(p(x)/q(x))

### Conditional Entropy and Mutual Information

```
H(Y|X) = Σₓ p(x) H(Y|X=x)         (remaining uncertainty about Y given X)
I(X;Y) = H(Y) - H(Y|X)              (information shared between X and Y)
```

**Data Processing Inequality**: If X → Y → Z is a Markov chain, then I(X;Z) ≤ I(X;Y).

---

## 163.6 Probability Generating Functions

### Definition

For a non-negative integer-valued random variable X:

```
G_X(z) = E[z^X] = Σ_{k=0}^∞ P(X=k) × z^k
```

### Key Properties

| Property | Formula |
|---|---|
| G(1) | 1 (normalization) |
| G'(1) | E[X] (mean) |
| G''(1) + G'(1) - (G'(1))² | Var(X) |
| G_X+Y(z) | G_X(z) × G_Y(z) (independent sum) |

### Common Distributions

| Distribution | PGF | Mean | Variance |
|---|---|---|---|
| Bernoulli(p) | (1-p) + pz | p | p(1-p) |
| Geometric(p) | pz/(1-(1-p)z) | 1/p | (1-p)/p² |
| Poisson(λ) | e^{λ(z-1)} | λ | λ |
| Binomial(n,p) | (1-p+pz)^n | np | np(1-p) |

### Application: Solving Recurrences

**Example**: Expected number of comparisons in QuickSelect.

Let T(n) be the expected comparisons to find the median. After partitioning:
- Pivot is at position k with probability 1/n
- Recurse on the larger side

```
T(n) = n-1 + (1/n) Σ_{k=⌈n/2⌉}^{n-1} T(k)
```

Using generating functions or the substitution method, T(n) = O(n).

### Application: Analysis of Hashing

Expected number of collisions in a hash table with n keys and m buckets:

Using PGF of the occupancy distribution:
```
E[collisions] = n - m + m(1 - 1/m)^n ≈ n²/(2m) for n << m
```

---

## 163.7 Martingales

### Definition

A sequence of random variables X₀, X₁, X₂, ... is a martingale if:

```
E[X_{n+1} | X₀, X₁, ..., Xₙ] = Xₙ
```

The expected future value equals the current value — "fair game."

### Examples

1. **Random walk**: Sₙ = X₁ + X₂ + ... + Xₙ where Xᵢ are i.i.d. with E[Xᵢ] = 0
2. **Fair gambling**: Starting wealth w, bet on fair games. Expected wealth stays w.
3. **Polya's urn**: Start with 1 red, 1 blue ball. Draw, replace, add one of same color. Fraction of red is a martingale.

### Doob Martingale

Given random variables X₁, ..., Xₙ and a function f:

```
Mₖ = E[f(X₁, ..., Xₙ) | X₁, ..., Xₖ]
```

This is always a martingale. It "reveals" information about f(X) one variable at a time.

### Key Theorems

**Doob's Martingale Convergence**: If sup E[|Xₙ|] < ∞, then Xₙ converges almost surely.

**Optional Stopping Theorem**: If T is a stopping time with E[T] < ∞, then E[X_T] = E[X₀].

**Azuma-Hoeffding Inequality**: If |Xₖ - Xₖ₋₁| ≤ cₖ (bounded differences), then:

```
P(|Xₙ - X₀| ≥ t) ≤ 2 exp(-t² / (2 Σ cₖ²))
```

### Application: Concentration of Measure

**Example**: Balls into bins. Throw n balls into n bins uniformly at random. Let X = max load.

Using Azuma-Hoeffding (with the Doob martingale for adding one ball at a time):
```
P(X ≥ c log n / log log n) ≤ 1/n
```

This shows that with high probability, no bin has more than O(log n / log log n) balls.

### Application: Randomized Algorithm Analysis

**QuickSort analysis**: The number of comparisons is a random variable. Using the Doob martingale (revealing one comparison at a time) and Azuma-Hoeffding:

```
P(|C - E[C]| ≥ t) ≤ 2 exp(-t² / (2n²))
```

This shows that QuickSort's running time is tightly concentrated around 2n ln n.

---

## 163.8 Number Theory for Algorithms

### Modular Arithmetic

Essential for hashing, cryptography, and randomized algorithms.

**Modular exponentiation**: Compute a^b mod m in O(log b) time using repeated squaring.

```
PowerMod(a, b, m):
    result = 1
    a = a mod m
    while b > 0:
        if b is odd: result = (result × a) mod m
        b = b >> 1
        a = (a × a) mod m
    return result
```

### Prime Testing

**Miller-Rabin**: Probabilistic O(k log² n) test. For k witnesses, error probability ≤ 4^(-k).

**AKS**: Deterministic O(log⁶ n) test. Polynomial but impractical.

### Applications

| Problem | Math Tool | Algorithm |
|---|---|---|
| Hashing | Universal hash families | h(a,b,x) = ((ax+b) mod p) mod m |
| Cryptography | RSA | Modular exponentiation, prime testing |
| Random sampling | Reservoir sampling | Modular arithmetic for random selection |
| Error-correcting codes | Finite fields | Reed-Solomon codes |

---

## 163.9 Implementations

### C++: SVD via Power Iteration

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <random>

class Matrix {
public:
    std::vector<std::vector<double>> data;
    int rows, cols;
    
    Matrix(int r, int c) : rows(r), cols(c), data(r, std::vector<double>(c, 0)) {}
    
    std::vector<double> operator*(const std::vector<double>& v) const {
        std::vector<double> result(rows, 0);
        for (int i = 0; i < rows; i++)
            for (int j = 0; j < cols; j++)
                result[i] += data[i][j] * v[j];
        return result;
    }
    
    std::vector<double> transposeMultiply(const std::vector<double>& v) const {
        std::vector<double> result(cols, 0);
        for (int j = 0; j < cols; j++)
            for (int i = 0; i < rows; i++)
                result[j] += data[i][j] * v[i];
        return result;
    }
};

// Find dominant singular value and right singular vector
std::pair<double, std::vector<double>> powerIterationSVD(
    const Matrix& A, int maxIter = 1000, double tol = 1e-10
) {
    int n = A.cols;
    std::vector<double> v(n);
    
    // Random initialization
    std::mt19937 rng(42);
    std::normal_distribution<double> dist(0, 1);
    for (int i = 0; i < n; i++) v[i] = dist(rng);
    
    // Normalize
    double norm = 0;
    for (double x : v) norm += x * x;
    norm = std::sqrt(norm);
    for (double& x : v) x /= norm;
    
    double sigma = 0;
    for (int iter = 0; iter < maxIter; iter++) {
        // u = Av
        std::vector<double> u = A * v;
        
        // v = Aᵀu
        std::vector<double> newV = A.transposeMultiply(u);
        
        // Compute singular value estimate
        sigma = 0;
        for (double x : newV) sigma += x * x;
        sigma = std::sqrt(sigma);
        
        if (sigma < 1e-15) break;
        
        // Normalize
        double newNorm = 0;
        for (double x : newV) newNorm += x * x;
        newNorm = std::sqrt(newNorm);
        
        // Check convergence
        double diff = 0;
        for (int i = 0; i < n; i++) {
            double scaled = newV[i] / newNorm;
            diff += (scaled - v[i]) * (scaled - v[i]);
            v[i] = scaled;
        }
        
        if (std::sqrt(diff) < tol) break;
    }
    
    return {sigma, v};
}

int main() {
    Matrix A(3, 2);
    A.data = {{1, 2}, {3, 4}, {5, 6}};
    
    auto [sigma, v] = powerIterationSVD(A);
    
    std::cout << "Matrix A:\n";
    for (int i = 0; i < 3; i++)
        std::cout << "  [" << A.data[i][0] << ", " << A.data[i][1] << "]\n";
    
    std::cout << "\nDominant singular value: " << sigma << "\n";
    std::cout << "Right singular vector: (";
    for (int i = 0; i < (int)v.size(); i++)
        std::cout << v[i] << (i + 1 < (int)v.size() ? ", " : ")\n");
    
    // Verify: Av should be parallel to left singular vector, with magnitude sigma
    std::vector<double> Av = A * v;
    std::cout << "Av = (";
    for (int i = 0; i < (int)Av.size(); i++)
        std::cout << Av[i] << (i + 1 < (int)Av.size() ? ", " : ")\n");
    std::cout << "‖Av‖ = " << std::sqrt(Av[0]*Av[0] + Av[1]*Av[1] + Av[2]*Av[2]) << "\n";
    
    return 0;
}
```

### Python: Markov Chain Simulation

```python
import numpy as np
from collections import Counter

class MarkovChain:
    """
    Markov chain with transition matrix P.
    
    Supports:
        - Simulation of chain evolution
        - Stationary distribution computation
        - Mixing time estimation
    """
    
    def __init__(self, transition_matrix, state_labels=None):
        self.P = np.array(transition_matrix)
        self.n = self.P.shape[0]
        self.labels = state_labels or [f"S{i}" for i in range(self.n)]
        
        # Validate
        assert self.P.shape == (self.n, self.n), "Must be square matrix"
        assert np.allclose(self.P.sum(axis=1), 1), "Rows must sum to 1"
    
    def stationary_distribution(self):
        """Compute stationary distribution π where π = πP."""
        # Solve (Pᵀ - I)π = 0 with Σπ = 1
        # Method: eigenvector of Pᵀ for eigenvalue 1
        eigenvalues, eigenvectors = np.linalg.eig(self.P.T)
        
        # Find eigenvalue closest to 1
        idx = np.argmin(np.abs(eigenvalues - 1))
        pi = np.real(eigenvectors[:, idx])
        
        # Normalize to sum to 1
        pi = pi / pi.sum()
        return np.abs(pi)  # Ensure non-negative
    
    def simulate(self, start_state, steps):
        """Simulate the Markov chain for given steps."""
        state = start_state
        history = [state]
        
        for _ in range(steps):
            state = np.random.choice(self.n, p=self.P[state])
            history.append(state)
        
        return history
    
    def mixing_time(self, epsilon=0.01, max_steps=10000):
        """Estimate mixing time: steps until distribution is within epsilon of stationary."""
        pi = self.stationary_distribution()
        
        # Start from worst-case state (furthest from stationary)
        max_dist = 0
        worst_state = 0
        for s in range(self.n):
            dist = np.abs(np.eye(self.n)[s] - pi).sum()
            if dist > max_dist:
                max_dist = dist
                worst_state = s
        
        # Simulate from worst state
        dist = np.eye(self.n)[worst_state]
        for t in range(max_steps):
            dist = dist @ self.P
            tv_distance = 0.5 * np.abs(dist - pi).sum()
            if tv_distance <= epsilon:
                return t + 1
        
        return max_steps  # Didn't converge
    
    def spectral_gap(self):
        """Compute spectral gap (1 - |λ₂|)."""
        eigenvalues = np.sort(np.abs(np.linalg.eigvals(self.P)))[::-1]
        return 1 - eigenvalues[1] if len(eigenvalues) > 1 else 1.0

if __name__ == "__main__":
    # Random walk on a triangle (3 states, each connected to others)
    P = [
        [0.0, 0.5, 0.5],
        [0.5, 0.0, 0.5],
        [0.5, 0.5, 0.0]
    ]
    
    mc = MarkovChain(P, ["A", "B", "C"])
    
    print("Transition Matrix:")
    print(mc.P)
    
    pi = mc.stationary_distribution()
    print(f"\nStationary distribution: {dict(zip(mc.labels, np.round(pi, 4)))}")
    
    gap = mc.spectral_gap()
    print(f"Spectral gap: {gap:.4f}")
    
    mix = mc.mixing_time(epsilon=0.01)
    print(f"Mixing time (ε=0.01): {mix} steps")
    
    # Simulate and check convergence
    history = mc.simulate(start_state=0, steps=1000)
    counts = Counter(history)
    print(f"\nEmpirical distribution (1000 steps from state A):")
    for s in range(3):
        print(f"  {mc.labels[s]}: {counts[s]/1000:.3f} (expected {pi[s]:.3f})")
```

### Java: Entropy and Information Theory

```java
import java.util.*;

/**
 * Information theory utilities: entropy, KL divergence, mutual information.
 */
public class InformationTheory {
    
    /**
     * Shannon entropy H(X) = -Σ p(x) log₂ p(x).
     * @param probs Probability distribution (must sum to 1)
     * @return Entropy in bits
     */
    public static double entropy(double[] probs) {
        double h = 0;
        for (double p : probs) {
            if (p > 0) h -= p * Math.log(p) / Math.log(2);
        }
        return h;
    }
    
    /**
     * Entropy of a discrete dataset (empirical distribution).
     */
    public static double empiricalEntropy(int[] data) {
        Map<Integer, Integer> counts = new HashMap<>();
        for (int x : data) counts.merge(x, 1, Integer::sum);
        
        double n = data.length;
        double h = 0;
        for (int count : counts.values()) {
            double p = count / n;
            h -= p * Math.log(p) / Math.log(2);
        }
        return h;
    }
    
    /**
     * KL divergence D_KL(p || q) = Σ p(x) log₂(p(x)/q(x)).
     * Measures how different distribution q is from p.
     */
    public static double klDivergence(double[] p, double[] q) {
        double kl = 0;
        for (int i = 0; i < p.length; i++) {
            if (p[i] > 0 && q[i] > 0) {
                kl += p[i] * Math.log(p[i] / q[i]) / Math.log(2);
            } else if (p[i] > 0 && q[i] == 0) {
                return Double.POSITIVE_INFINITY;
            }
        }
        return kl;
    }
    
    /**
     * Cross-entropy H(p, q) = -Σ p(x) log₂ q(x).
     * Used as loss function in classification.
     */
    public static double crossEntropy(double[] p, double[] q) {
        double ce = 0;
        for (int i = 0; i < p.length; i++) {
            if (p[i] > 0 && q[i] > 0) {
                ce -= p[i] * Math.log(q[i]) / Math.log(2);
            }
        }
        return ce;
    }
    
    /**
     * Mutual information I(X;Y) from joint distribution.
     * @param joint joint[i][j] = P(X=i, Y=j)
     */
    public static double mutualInformation(double[][] joint) {
        int m = joint.length, n = joint[0].length;
        
        // Marginals
        double[] px = new double[m];
        double[] py = new double[n];
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++) {
                px[i] += joint[i][j];
                py[j] += joint[i][j];
            }
        
        double mi = 0;
        for (int i = 0; i < m; i++)
            for (int j = 0; j < n; j++)
                if (joint[i][j] > 0 && px[i] > 0 && py[j] > 0)
                    mi += joint[i][j] * Math.log(joint[i][j] / (px[i] * py[j])) / Math.log(2);
        
        return mi;
    }
    
    /**
     * Information gain for decision trees.
     * @param parent Parent distribution
     * @param children Array of child distributions (weighted by size)
     */
    public static double informationGain(double[] parent, double[][] children) {
        double parentEntropy = entropy(parent);
        double childEntropy = 0;
        double totalWeight = 0;
        for (double[] child : children) {
            double weight = 0;
            for (double p : child) weight += p;
            totalWeight += weight;
            childEntropy += weight * entropy(normalize(child));
        }
        childEntropy /= totalWeight;
        return parentEntropy - childEntropy;
    }
    
    private static double[] normalize(double[] dist) {
        double sum = 0;
        for (double x : dist) sum += x;
        double[] result = new double[dist.length];
        for (int i = 0; i < dist.length; i++) result[i] = dist[i] / sum;
        return result;
    }
    
    public static void main(String[] args) {
        // Example: Fair coin vs biased coin
        double[] fair = {0.5, 0.5};
        double[] biased = {0.9, 0.1};
        
        System.out.println("=== Entropy ===");
        System.out.printf("Fair coin:   H = %.4f bits%n", entropy(fair));
        System.out.printf("Biased coin: H = %.4f bits%n", entropy(biased));
        
        System.out.println("\n=== KL Divergence ===");
        System.out.printf("D_KL(fair || biased) = %.4f bits%n", klDivergence(fair, biased));
        System.out.printf("D_KL(biased || fair) = %.4f bits%n", klDivergence(biased, fair));
        
        System.out.println("\n=== Cross-Entropy ===");
        System.out.printf("H(fair, biased) = %.4f bits%n", crossEntropy(fair, biased));
        System.out.printf("H(fair, fair)   = %.4f bits%n", crossEntropy(fair, fair));
        
        // Mutual information example
        System.out.println("\n=== Mutual Information ===");
        // X = coin type (fair/biased), Y = outcome (H/T)
        double[][] joint = {
            {0.25, 0.25},  // Fair: P(H)=0.25, P(T)=0.25
            {0.45, 0.05}   // Biased: P(H)=0.45, P(T)=0.05
        };
        System.out.printf("I(X;Y) = %.4f bits%n", mutualInformation(joint));
        
        // Information gain example
        System.out.println("\n=== Information Gain (Decision Tree) ===");
        double[] parent = {5, 5};  // 5 positive, 5 negative
        double[][] children = {{4, 1}, {1, 4}};  // Split result
        System.out.printf("Information gain = %.4f bits%n", informationGain(parent, children));
    }
}
```

---

## 163.10 Exercises

### Conceptual Exercises

1. **SVD**: What do the singular values of a matrix represent geometrically? How does truncating small singular values affect the matrix?

2. **Markov Chains**: Explain why the stationary distribution of a random walk on an undirected graph is proportional to the vertex degrees.

3. **Entropy**: Why is entropy maximized by the uniform distribution? Prove it using Jensen's inequality.

4. **Martingales**: Explain why the "fair game" interpretation makes sense. What happens if the game is biased?

5. **Spectral Gap**: How does the spectral gap of a graph's transition matrix relate to its connectivity?

### Programming Exercises

1. **Power Iteration**: Implement power iteration to find the dominant eigenvector. Test on a 10×10 random symmetric matrix.

2. **PageRank**: Implement PageRank using power iteration on a small web graph.

3. **Entropy Calculator**: Write a function that computes the entropy of a text file (character-level).

4. **Random Walk Simulation**: Simulate a random walk on a graph and empirically verify the stationary distribution.

5. **Huffman Coding**: Implement Huffman coding and verify that the average code length is within 1 bit of the entropy.

---

## 163.11 Interview Questions

### Conceptual Questions

1. **Q**: What is the SVD and why is it useful?
   **A**: SVD decomposes any matrix A into UΣVᵀ where U, V are orthogonal and Σ is diagonal with singular values. It's useful because: (1) the best rank-k approximation is obtained by keeping the top k singular values, (2) it reveals the "important directions" in data (PCA), (3) it solves least-squares problems, (4) it's the basis for recommendation systems and dimensionality reduction.

2. **Q**: Explain the relationship between entropy and compression.
   **A**: Shannon's source coding theorem states that you cannot compress data to fewer than H(X) bits per symbol on average. Huffman coding and arithmetic coding achieve close to this bound. Higher entropy means more randomness and less compressibility. A fair coin (H=1) can't be compressed; a biased coin (H<1) can.

3. **Q**: What is a martingale and how is it used in algorithm analysis?
   **A**: A martingale is a sequence where the expected future value equals the current value. In algorithm analysis, we construct martingales (often Doob martingales) to show concentration: that a random variable (like QuickSort's comparison count) is tightly concentrated around its mean. The Azuma-Hoeffding inequality gives exponential tail bounds.

4. **Q**: How does the spectral gap affect the mixing time of a Markov chain?
   **A**: Mixing time is O(1/(1-λ₂)) where λ₂ is the second-largest eigenvalue. A larger spectral gap means faster mixing. Expander graphs have a constant spectral gap, so they mix in O(log n) steps. This is why random walks on expanders are useful for sampling algorithms.

### Coding Questions

1. **Q**: Implement power iteration to find the dominant eigenvalue/eigenvector.
   **A**: Start with random vector v. Repeat: v ← Av / ‖Av‖. Converges to the dominant eigenvector. The eigenvalue is ‖Av‖ / ‖v‖. Takes O(n²) per iteration, converges in O(log(1/ε) / log(λ₁/λ₂)) iterations.

2. **Q**: Compute the entropy of a probability distribution.
   **A**: H = -Σ pᵢ log₂ pᵢ. Handle pᵢ = 0 by skipping (0 × log 0 = 0 by convention). Time: O(n) where n is the number of outcomes.

3. **Q**: Given a transition matrix, find the stationary distribution.
   **A**: Solve πP = π with Σπᵢ = 1. This is the left eigenvector of P for eigenvalue 1. Use numpy.linalg.eig on P.T, find the eigenvector for eigenvalue 1, normalize to sum to 1.

---

## 163.12 Cross-References

- **Chapter 15: Divide and Conquer** — Recurrences solved by generating functions
- **Chapter 29: Hashing** — Universal hashing uses number theory
- **Chapter 35: Dynamic Programming** — Generating functions for counting
- **Chapter 62: Graph Algorithms** — Spectral graph theory
- **Chapter 158: Succinct Data Structures** — Entropy bounds on compression
- **Chapter 160: Parallel Algorithms** — Randomized parallel algorithms
- **Chapter 102: Bloom Filters** — Probability analysis
- **Chapter 161: External Memory Algorithms** — Cache-efficient matrix operations

---

## Summary

| Tool | Key Formula | Application |
|---|---|---|
| SVD | A = UΣVᵀ | Dimensionality reduction, PCA, recommendations |
| Eigenvalues | Av = λv | PageRank, spectral graph theory |
| Markov Chains | π = πP | Random walks, mixing, PageRank |
| Entropy | H = -Σ p log p | Compression, decision trees, ML |
| KL Divergence | D_KL(p‖q) = Σ p log(p/q) | Distribution comparison |
| Mutual Information | I(X;Y) = H(X) - H(X\|Y) | Feature selection |
| PGF | G(z) = E[z^X] | Moment extraction, recurrences |
| Martingales | E[X_{n+1}\|history] = Xₙ | Concentration bounds |
| Modular Arithmetic | a^b mod m | Cryptography, hashing |

**Key Takeaway**: Mathematics provides the language and tools for analyzing algorithms. SVD reveals structure in data, entropy bounds compression, Markov chains model random processes, and martingales prove concentration. These tools are essential for understanding why algorithms work and how well they perform. In practice, you'll use them in systems design, ML pipelines, and performance analysis — even if they don't appear directly in coding interviews.
