# Chapter 151: Linear Programming

## Prerequisites
- Matrix operations (matrix multiplication, transpose)
- Basic optimization concepts (objective function, constraints)
- Gaussian elimination
- Graph algorithms (for network flow connections)

## Interview Frequency: ★★

Linear Programming (LP) is the foundation of mathematical optimization. Many algorithmic problems — from network flow to resource allocation — can be formulated as LPs. Understanding LP is essential for operations research, machine learning (SVMs), and advanced algorithm design.

> **Key Insight:** Every LP has a dual. The dual provides a lower bound (for minimization) on the primal solution. At optimality, primal = dual (strong duality). This is one of the deepest results in optimization theory.

| Concept | Frequency | Difficulty | Notes |
|---|---|---|---|
| LP formulation | ★★★ | Medium | Modeling real problems |
| Simplex method | ★★ | Hard | Most common algorithm |
| LP duality | ★★★ | Hard | Key theoretical tool |
| LP relaxation | ★★★ | Medium | Bridge to integer programming |

---

## 151.1 What Problem Does It Solve?

### The Optimization Template

Many real-world problems share this structure:

**Maximize** (or minimize) a **linear objective** subject to **linear constraints**.

Examples:
- **Resource allocation:** Maximize profit given limited resources.
- **Scheduling:** Minimize cost subject to time and capacity constraints.
- **Network flow:** Maximize flow subject to capacity constraints.
- **Diet problem:** Minimize cost while meeting nutritional requirements.
- **Game theory:** Find optimal mixed strategies.

---

## 151.2 Standard Form

A linear program in **standard form** is:

```
Minimize    c^T x
Subject to  Ax ≤ b
            x ≥ 0
```

Where:
- `x ∈ R^n` — decision variables
- `c ∈ R^n` — cost coefficients (objective)
- `A ∈ R^{m×n}` — constraint matrix
- `b ∈ R^m` — right-hand side (resource limits)

### Converting to Standard Form

Any LP can be converted to standard form:

| Original Form | Conversion |
|---|---|
| Maximize c^T x | Minimize (-c)^T x |
| a^T x ≥ b | (-a)^T x ≤ -b |
| a^T x = b | a^T x ≤ b AND (-a)^T x ≤ -b |
| x free | x = x⁺ - x⁻ where x⁺, x⁻ ≥ 0 |

### Example

**Original:**
```
Maximize  3x₁ + 4x₂
Subject to:
  x₁ + 2x₂ ≤ 8
  3x₁ + 2x₂ ≤ 12
  x₁, x₂ ≥ 0
```

**Standard form:**
```
Minimize  -3x₁ - 4x₂
Subject to:
  x₁ + 2x₂ ≤ 8
  3x₁ + 2x₂ ≤ 12
  x₁, x₂ ≥ 0
```

---

## 151.3 Geometric Intuition

### The Feasible Polytope

Each constraint `a_i^T x ≤ b_i` defines a **half-space**. The intersection of all half-spaces is the **feasible region** — a convex polytope.

**Key facts:**
- If the feasible region is non-empty, it's a convex polyhedron.
- The optimal solution (if it exists) is always at a **vertex** of the polytope.
- If the objective is parallel to a face, there may be multiple optimal solutions (all on that face).

### Visual Example

For the LP above:
```
  x₂
  4 |  /\
    | / .\      ← Feasible region (shaded)
  3 |/..*..\    ← * is optimal (2, 3)
    |......\
  2 |.......\   x₁ + 2x₂ = 8
    |........\
  1 |.........\ 3x₁ + 2x₂ = 12
    |..........\
  0 +--+--+--+--→ x₁
    0  1  2  3  4
```

The vertices of the feasible region are: (0,0), (4,0), (2,3), (0,4).
The optimal solution is at vertex (2,3) with objective value 3(2) + 4(3) = **18**.

---

## 151.4 The Simplex Method

The simplex method is the most widely used algorithm for solving LPs. Despite its exponential worst-case complexity, it's extremely fast in practice.

### Algorithm

1. **Start** at a feasible vertex of the polytope.
2. **Find an edge** that improves the objective (entering variable).
3. **Move** to the adjacent vertex along that edge (pivoting).
4. **Repeat** until no improving edge exists (optimality).

### Tableau Form

The simplex method uses a **tableau** — a matrix representation of the LP in a form that makes pivoting easy.

**Initial tableau for our example:**

```
| Basis | x₁ | x₂ | s₁ | s₂ | RHS |
|-------|----|----|----|----|-----|
| s₁    |  1 |  2 |  1 |  0 |   8 |
| s₂    |  3 |  2 |  0 |  1 |  12|
| Z     | -3 | -4 |  0 |  0 |   0 |
```

Where s₁, s₂ are slack variables (converting inequalities to equalities).

### Pivot Steps

**Iteration 1:**
- Entering variable: x₂ (most negative in Z row: -4)
- Leaving variable: s₁ (min ratio: 8/2 = 4 < 12/2 = 6)
- Pivot on element (1, 2)

**After pivot:**
```
| Basis | x₁  | x₂ | s₁  | s₂ | RHS |
|-------|-----|----|-----|----|-----|
| x₂    | 1/2 |  1 | 1/2 |  0 |   4 |
| s₂    |  2  |  0 | -1  |  1 |   4 |
| Z     | -1  |  0 |  2  |  0 |  16 |
```

**Iteration 2:**
- Entering variable: x₁ (negative in Z row: -1)
- Leaving variable: s₂ (min ratio: 4/2 = 2)
- Pivot on element (2, 1)

**After pivot:**
```
| Basis | x₁ | x₂ | s₁  | s₂  | RHS |
|-------|----|----|-----|-----|-----|
| x₂    |  0 |  1 | 3/4 | -1/4|   3 |
| x₁    |  1 |  0 |-1/2 | 1/2 |   2 |
| Z     |  0 |  0 | 3/2 | 1/2 |  18 |
```

No negative entries in Z row → **optimal!**

**Solution:** x₁ = 2, x₂ = 3, Z = 18 ✓

---

## 151.5 LP Duality

Every LP (the **primal**) has an associated **dual** LP.

### Primal-Dual Relationship

| Primal (Min) | Dual (Max) |
|---|---|
| Minimize c^T x | Maximize b^T y |
| Ax ≥ b | A^T y ≤ c |
| x ≥ 0 | y ≥ 0 |

### Weak Duality Theorem

For any feasible x (primal) and feasible y (dual):
```
c^T x ≥ b^T y
```

The dual objective is always a **lower bound** on the primal objective.

### Strong Duality Theorem

If both primal and dual are feasible, then at optimality:
```
c* x* = b^T y*
```

The optimal values are **equal**.

### Complementary Slackness

At optimality, for each constraint:
- Either the constraint is tight (equality holds), or
- The corresponding dual variable is zero.

This gives us a way to verify optimality and is the basis for sensitivity analysis.

### Example

**Primal:**
```
Minimize  8y₁ + 12y₂
Subject to:
  y₁ + 3y₂ ≥ 3
  2y₁ + 2y₂ ≥ 4
  y₁, y₂ ≥ 0
```

**Dual:**
```
Maximize  3x₁ + 4x₂
Subject to:
  x₁ + 2x₂ ≤ 8
  3x₁ + 2x₂ ≤ 12
  x₁, x₂ ≥ 0
```

This is exactly our earlier example! The dual of the dual is the primal.

---

## 151.6 LP Relaxation

**Integer Linear Programming (ILP)** requires variables to be integers. ILP is NP-hard.

**LP relaxation** drops the integer constraint, giving an LP that can be solved in polynomial time.

```
ILP:   maximize c^T x,  Ax ≤ b,  x ∈ {0, 1}^n
Relax: maximize c^T x,  Ax ≤ b,  0 ≤ x ≤ 1
```

**Properties:**
- LP relaxation gives an **upper bound** (for maximization) on the ILP optimal.
- If the LP solution happens to be integral, it's also optimal for the ILP.
- LP relaxation is the foundation of **branch and bound** algorithms for ILP.
- For some problems (e.g., network flow, matching), LP relaxation always gives integral solutions.

---

## 151.7 Applications

### Network Flow as LP

Max flow can be formulated as an LP:
```
Maximize  Σ f(s,v) - Σ f(v,s)    (flow out of source)
Subject to:
  f(u,v) ≤ c(u,v)               for all edges (capacity)
  f(u,v) ≥ 0                    for all edges (non-negativity)
  Σ f(u,v) = Σ f(v,w)           for all non-source/sink v (flow conservation)
```

### Shortest Path as LP

```
Minimize  Σ c(u,v) · x(u,v)
Subject to:
  Σ x(s,v) - Σ x(v,s) = 1      (source sends 1 unit)
  Σ x(t,v) - Σ x(v,t) = -1     (sink receives 1 unit)
  Σ x(u,v) - Σ x(v,u) = 0      for all other nodes
  x(u,v) ≥ 0
```

### Minimum Cost Flow

Combines flow conservation with cost minimization. The dual gives potentials (node prices).

---

## 151.8 Implementation

### C++ — Simplex Method (Full Implementation)

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <limits>

// Simplex method for LP in standard form:
// Minimize c^T x
// Subject to Ax = b, x >= 0
// (Convert ≤ constraints by adding slack variables)

class Simplex {
    int m, n; // m constraints, n variables
    std::vector<std::vector<double>> tableau;
    std::vector<int> basis; // basis[i] = variable in row i

public:
    // Solve: Minimize c^T x, subject to Ax <= b, x >= 0
    // Returns {optimal_value, solution_vector}
    // Returns {+inf, {}} if infeasible, {-inf, {}} if unbounded
    std::pair<double, std::vector<double>> solve(
        std::vector<std::vector<double>> A,
        std::vector<double> b,
        std::vector<double> c
    ) {
        m = b.size();
        n = c.size();

        // Build tableau: [A | I | b]
        //                    [c | 0 | 0]
        tableau.assign(m + 1, std::vector<double>(n + m + 1, 0));
        basis.resize(m);

        for (int i = 0; i < m; i++) {
            for (int j = 0; j < n; j++)
                tableau[i][j] = A[i][j];
            tableau[i][n + i] = 1.0; // slack variable
            tableau[i][n + m] = b[i];
            basis[i] = n + i;
        }

        for (int j = 0; j < n; j++)
            tableau[m][j] = -c[j]; // negated for minimization

        // Simplex iterations
        while (true) {
            // Find entering variable (most negative in objective row)
            int enter = -1;
            for (int j = 0; j < n + m; j++) {
                if (tableau[m][j] < -1e-9) {
                    enter = j;
                    break;
                }
            }
            if (enter == -1) break; // Optimal

            // Find leaving variable (minimum ratio test)
            int leave = -1;
            double minRatio = std::numeric_limits<double>::max();
            for (int i = 0; i < m; i++) {
                if (tableau[i][enter] > 1e-9) {
                    double ratio = tableau[i][n + m] / tableau[i][enter];
                    if (ratio < minRatio) {
                        minRatio = ratio;
                        leave = i;
                    }
                }
            }

            if (leave == -1) return {-std::numeric_limits<double>::max(), {}}; // Unbounded

            // Pivot
            pivot(leave, enter);
            basis[leave] = enter;
        }

        // Extract solution
        std::vector<double> x(n, 0);
        for (int i = 0; i < m; i++) {
            if (basis[i] < n)
                x[basis[i]] = tableau[i][n + m];
        }

        double optimal = tableau[m][n + m];
        return {optimal, x};
    }

private:
    void pivot(int row, int col) {
        double pivotVal = tableau[row][col];

        // Scale pivot row
        for (int j = 0; j <= n + m; j++)
            tableau[row][j] /= pivotVal;

        // Eliminate other rows
        for (int i = 0; i <= m; i++) {
            if (i == row) continue;
            double factor = tableau[i][col];
            for (int j = 0; j <= n + m; j++)
                tableau[i][j] -= factor * tableau[row][j];
        }
    }
};

int main() {
    // Maximize 3x + 4y
    // Subject to: x + 2y ≤ 8, 3x + 2y ≤ 12, x,y ≥ 0

    // Convert to minimize: -3x - 4y
    std::vector<std::vector<double>> A = {
        {1, 2},
        {3, 2}
    };
    std::vector<double> b = {8, 12};
    std::vector<double> c = {3, 4}; // maximize, so negate in solver

    Simplex solver;
    auto [val, sol] = solver.solve(A, b, c);

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Optimal value: " << val << "\n";
    std::cout << "x = " << sol[0] << ", y = " << sol[1] << "\n";
    // Expected: x=2, y=3, value=18

    return 0;
}
```

### Python — Simplex Method

```python
import numpy as np

def simplex(A, b, c):
    """
    Solve: Minimize c^T x, subject to Ax <= b, x >= 0
    Returns (optimal_value, solution) or (None, None) if infeasible/unbounded.
    """
    m, n = len(A), len(A[0])
    # Build tableau: [A | I | b]
    #                [-c| 0 | 0]
    tableau = np.zeros((m + 1, n + m + 1))
    for i in range(m):
        tableau[i, :n] = A[i]
        tableau[i, n + i] = 1.0
        tableau[i, -1] = b[i]
    tableau[m, :n] = -np.array(c)

    basis = list(range(n, n + m))

    while True:
        # Find entering variable
        enter = -1
        for j in range(n + m):
            if tableau[m, j] < -1e-9:
                enter = j
                break
        if enter == -1:
            break  # Optimal

        # Find leaving variable (minimum ratio)
        leave = -1
        min_ratio = float('inf')
        for i in range(m):
            if tableau[i, enter] > 1e-9:
                ratio = tableau[i, -1] / tableau[i, enter]
                if ratio < min_ratio:
                    min_ratio = ratio
                    leave = i

        if leave == -1:
            return None, None  # Unbounded

        # Pivot
        pivot_val = tableau[leave, enter]
        tableau[leave] /= pivot_val
        for i in range(m + 1):
            if i != leave:
                tableau[i] -= tableau[i, enter] * tableau[leave]
        basis[leave] = enter

    # Extract solution
    x = np.zeros(n)
    for i in range(m):
        if basis[i] < n:
            x[basis[i]] = tableau[i, -1]

    return tableau[m, -1], x


if __name__ == "__main__":
    # Maximize 3x + 4y subject to x + 2y <= 8, 3x + 2y <= 12
    A = [[1, 2], [3, 2]]
    b = [8, 12]
    c = [3, 4]  # We negate in the tableau

    val, sol = simplex(A, b, c)
    print(f"Optimal value: {val:.2f}")
    print(f"x = {sol[0]:.2f}, y = {sol[1]:.2f}")
    # Expected: x=2.00, y=3.00, value=18.00
```

### Java — Simplex Method

```java
public class Simplex {
    private double[][] tableau;
    private int m, n;
    private int[] basis;

    public double[] solve(double[][] A, double[] b, double[] c) {
        m = b.length;
        n = c.length;
        tableau = new double[m + 1][n + m + 1];
        basis = new int[m];

        for (int i = 0; i < m; i++) {
            System.arraycopy(A[i], 0, tableau[i], 0, n);
            tableau[i][n + i] = 1.0;
            tableau[i][n + m] = b[i];
            basis[i] = n + i;
        }
        for (int j = 0; j < n; j++)
            tableau[m][j] = -c[j];

        while (true) {
            int enter = -1;
            for (int j = 0; j < n + m; j++) {
                if (tableau[m][j] < -1e-9) { enter = j; break; }
            }
            if (enter == -1) break;

            int leave = -1;
            double minRatio = Double.MAX_VALUE;
            for (int i = 0; i < m; i++) {
                if (tableau[i][enter] > 1e-9) {
                    double ratio = tableau[i][n + m] / tableau[i][enter];
                    if (ratio < minRatio) { minRatio = ratio; leave = i; }
                }
            }
            if (leave == -1) return null; // Unbounded

            pivot(leave, enter);
            basis[leave] = enter;
        }

        double[] x = new double[n];
        for (int i = 0; i < m; i++)
            if (basis[i] < n) x[basis[i]] = tableau[i][n + m];

        double[] result = new double[n + 1];
        result[0] = tableau[m][n + m];
        System.arraycopy(x, 0, result, 1, n);
        return result;
    }

    private void pivot(int row, int col) {
        double pv = tableau[row][col];
        for (int j = 0; j < tableau[0].length; j++) tableau[row][j] /= pv;
        for (int i = 0; i <= m; i++) {
            if (i == row) continue;
            double f = tableau[i][col];
            for (int j = 0; j < tableau[0].length; j++)
                tableau[i][j] -= f * tableau[row][j];
        }
    }

    public static void main(String[] args) {
        Simplex s = new Simplex();
        double[][] A = {{1, 2}, {3, 2}};
        double[] b = {8, 12};
        double[] c = {3, 4};
        double[] result = s.solve(A, b, c);
        System.out.printf("Optimal: %.2f, x=%.2f, y=%.2f%n",
                          result[0], result[1], result[2]);
    }
}
```

### Python — Using scipy (Production-Ready)

```python
from scipy.optimize import linprog

# Maximize 3x + 4y subject to x + 2y <= 8, 3x + 2y <= 12
# linprog minimizes, so negate the objective
c = [-3, -4]
A_ub = [[1, 2], [3, 2]]
b_ub = [8, 12]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=[(0, None), (0, None)])

print(f"Optimal value: {-result.fun:.2f}")  # Negate back
print(f"x = {result.x[0]:.2f}, y = {result.x[1]:.2f}")
```

---

## 151.9 Complexity Analysis

| Method | Time Complexity | Notes |
|---|---|---|
| Simplex | Exponential worst case | Fast in practice (polynomial average) |
| Ellipsoid method | O(n⁶ log(1/ε)) | First polynomial LP algorithm |
| Interior point (Karmarkar) | O(n^{3.5} log(1/ε)) | Practical polynomial method |
| Network simplex | O(n² m) | Specialized for network problems |

Where n = number of variables, m = number of constraints, ε = precision.

**Practical considerations:**
- Simplex typically requires O(m) to O(3m) iterations.
- Each iteration is O(mn) for the pivot operation.
- Total practical time: O(m² n) — very fast for most problems.
- Interior point methods are better for very large, sparse LPs.

---

## 151.10 Exercises

1. **Formulate as LP:** A factory produces two products. Product A requires 2 hours of labor and 1 unit of material, yielding $5 profit. Product B requires 1 hour of labor and 3 units of material, yielding $7 profit. There are 8 hours of labor and 12 units of material available. Formulate and solve the LP.

2. **Convert to standard form:** Convert the following LP to standard form:
   ```
   Maximize 2x - y
   Subject to: x + y ≥ 3, x - y = 1, x ≥ 0, y free
   ```

3. **Write the dual:** Write the dual of the LP in Exercise 1. Verify strong duality by solving both.

4. **LP relaxation of set cover:** Given a set cover ILP, write its LP relaxation. What does the LP solution tell you about the optimal integer solution?

5. **Implement interior point method:** Research and implement Karmarkar's interior point method for LP. Compare its performance with the simplex method on large random LPs.

6. **Network flow as LP:** Formulate the max flow problem as an LP. Solve it with your simplex implementation and verify it gives the same answer as a max flow algorithm.

---

## 151.11 Interview Questions

1. **Q: What is the standard form of a linear program?**
   A: Minimize c^T x subject to Ax ≤ b, x ≥ 0. Any LP can be converted to this form by negating objectives, splitting equalities, and replacing free variables.

2. **Q: What is LP duality and why is it important?**
   A: Every LP has a dual. The dual provides bounds on the primal: weak duality gives c^T x ≥ b^T y for any feasible pair, and strong duality says they're equal at optimality. Duality is used in sensitivity analysis, approximation algorithms, and game theory.

3. **Q: What is LP relaxation and when is it useful?**
   A: LP relaxation drops integer constraints from an ILP. It gives a bound on the optimal ILP value and is the foundation of branch-and-bound. For some problems (matching, flow), the LP relaxation always gives integer solutions.

4. **Q: Why is the simplex method fast in practice despite exponential worst case?**
   A: The number of pivots is typically linear in the number of constraints. The pathological cases (Klee-Minty cube) are contrived. Real-world LPs have structure that simplex exploits efficiently.

5. **Q: How does LP relate to network flow?**
   A: Max flow, min cost flow, and shortest path can all be formulated as LPs. The LP dual of max flow gives min cut. The LP dual of shortest path gives node potentials.

6. **Q: When would you use LP vs a specialized algorithm?**
   A: Use specialized algorithms when available (e.g., Dijkstra for shortest path, Ford-Fulkerson for max flow) — they're faster. Use LP when the problem doesn't fit a known pattern, or when you need a general-purpose solver.

---

## 151.12 Cross-References

- **Chapter 152 (Network Flow):** Network flow is a special case of LP. The LP perspective gives duality (min-cut = max-flow).
- **Chapter 153 (Matching):** Bipartite matching can be solved as an LP. The LP relaxation always gives integer solutions.
- **Chapter 154 (Approximation Algorithms):** LP relaxation and rounding is a standard technique for approximation algorithms.
- **Chapter 155 (Game Theory):** Finding Nash equilibria in zero-sum games reduces to LP.
- **Chapter 127 (Dynamic Programming):** Some DP problems can be reformulated as LPs, and vice versa.
- **Chapter 101 (Segment Trees):** LP and segment trees both appear in resource allocation problems.

---

## Summary

| Method | Time | Use Case |
|---|---|---|
| Simplex | Exponential worst, fast practice | General LP |
| Interior Point | O(n^{3.5} log(1/ε)) | Large sparse LP |
| Ellipsoid | Polynomial | Theoretical |
| LP Relaxation | Same as LP | Approximation, branch-and-bound |
| Duality | — | Bounds, sensitivity, theory |
