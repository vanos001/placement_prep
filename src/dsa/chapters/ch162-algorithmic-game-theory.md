# Chapter 162: Algorithmic Game Theory

## Prerequisites
- Game theory basics
- Graph algorithms (Chapters 22-29, 81-84, 107-111)
- Linear programming (Chapter 151)
- Probability (Chapter 72)

## Interview Frequency: ★★

Algorithmic game theory combines economics, game theory, and computer science to analyze strategic interactions in computational systems. It's fundamental to auction design, network routing, ad placement, and blockchain protocols. **Google**, **Amazon**, and **Microsoft** use these concepts in ad auctions and cloud pricing.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Stable matching | ★★★ | Medium | Gale-Shapley |
| Nash equilibrium | ★★ | Hard | PPAD-complete |
| Mechanism design | ★★ | Hard | Vickrey auctions |
| Price of anarchy | ★ | Medium | Efficiency loss |
| Congestion games | ★ | Medium | Routing, networks |

---

## 162.1 Stable Matching (Gale-Shapley)

### Definition

Given two sets of equal size (e.g., hospitals and applicants), where each member has a preference ordering over the other set, find a matching where no pair would prefer to be matched with each other over their current assignment. Such a pair is called a **blocking pair**, and a matching without blocking pairs is **stable**.

### Motivation

The National Resident Matching Program (NRMP) matches medical school graduates to hospital residencies. Before algorithmic matching, the process was chaotic — students and hospitals made offers and counteroffers, leading to unstable outcomes where graduates would break agreements for better positions.

### Intuition

Imagine a dance where everyone has preferences. If Alice is paired with Bob but prefers Charlie, and Charlie prefers Alice over his current partner, they'd "break" their matches. A stable matching prevents this — no one has an incentive to deviate.

### Formal Explanation

**Input**: Two sets A and B, each of size n. Each a ∈ A has a strict preference ordering over B. Each b ∈ B has a strict preference ordering over A.

**Output**: A matching M ⊆ A × B where:
- Each a ∈ A is matched to exactly one b ∈ B
- No blocking pair (a, b) exists where both prefer each other over their M-partners

**Theorem**: A stable matching always exists (Gale and Shapley, 1962).

### Algorithm

```
Gale-Shapley(proposerPrefs, acceptorPrefs):
    All proposers start as "free"
    Each proposer has a pointer to their next preferred acceptor

    While some proposer p is free:
        a = next acceptor on p's list
        if a is free:
            match(p, a)
        else if a prefers p over current partner p':
            unmatch(p', a)
            match(p, a)
            p' becomes free
        else:
            p remains free (rejected), advance pointer
    Return matching
```

### Step-by-Step Walkthrough

**Proposers** (0, 1, 2) and **Acceptors** (A, B, C):

| Proposer | Preferences |
|---|---|
| 0 | A > B > C |
| 1 | B > A > C |
| 2 | A > B > C |

| Acceptor | Preferences |
|---|---|
| A | 1 > 0 > 2 |
| B | 0 > 1 > 2 |
| C | 0 > 1 > 2 |

**Step 1**: Proposer 0 proposes to A (first choice). A is free → match(0, A).

**Step 2**: Proposer 1 proposes to B (first choice). B is free → match(1, B).

**Step 3**: Proposer 2 proposes to A (first choice). A prefers 0 (current match) over 2 → rejected.

**Step 4**: Proposer 2 proposes to B (second choice). B prefers 1 (current match) over 2 → rejected.

**Step 5**: Proposer 2 proposes to C (third choice). C is free → match(2, C).

**Result**: {0→A, 1→B, 2→C} — stable matching ✓

### Complexity Analysis

| Metric | Value |
|---|---|
| Time | O(n²) — each proposer proposes at most n times |
| Space | O(n²) — storing preference lists |
| Proposals | At most n² |

### Key Properties

1. **Proposer-optimal**: Proposers get their best possible stable match
2. **Acceptor-pessimal**: Acceptors get their worst possible stable match
3. **Strategy-proof for proposers**: No proposer benefits from lying about preferences
4. **Not strategy-proof for acceptors**: Acceptors can sometimes benefit from misreporting

### Code Example (C++)

```cpp
#include <iostream>
#include <vector>
#include <queue>

std::vector<int> galeShapley(
    const std::vector<std::vector<int>>& proposerPrefs,
    const std::vector<std::vector<int>>& acceptorPrefs)
{
    int n = proposerPrefs.size();
    std::vector<int> match(n, -1);           // acceptor -> proposer
    std::vector<int> proposerMatch(n, -1);   // proposer -> acceptor
    std::vector<int> nextProposal(n, 0);     // next acceptor index for each proposer
    std::vector<std::vector<int>> acceptorRank(n, std::vector<int>(n));

    // Build acceptor ranking: acceptorRank[a][p] = rank of proposer p for acceptor a
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            acceptorRank[i][acceptorPrefs[i][j]] = j;

    std::queue<int> freeProposers;
    for (int i = 0; i < n; i++) freeProposers.push(i);

    while (!freeProposers.empty()) {
        int p = freeProposers.front(); freeProposers.pop();
        int a = proposerPrefs[p][nextProposal[p]++];

        if (match[a] == -1) {
            // Acceptor is free
            match[a] = p;
            proposerMatch[p] = a;
        } else if (acceptorRank[a][p] < acceptorRank[a][match[a]]) {
            // Acceptor prefers new proposer
            int oldP = match[a];
            proposerMatch[oldP] = -1;
            freeProposers.push(oldP);
            match[a] = p;
            proposerMatch[p] = a;
        } else {
            // Acceptor rejects
            freeProposers.push(p);
        }
    }

    return proposerMatch;
}

int main() {
    // Proposers: 0, 1, 2 | Acceptors: 0, 1, 2
    std::vector<std::vector<int>> propPref = {
        {0, 1, 2},  // Proposer 0: A > B > C
        {1, 0, 2},  // Proposer 1: B > A > C
        {0, 1, 2}   // Proposer 2: A > B > C
    };
    std::vector<std::vector<int>> accPref = {
        {1, 0, 2},  // Acceptor A: 1 > 0 > 2
        {0, 1, 2},  // Acceptor B: 0 > 1 > 2
        {0, 1, 2}   // Acceptor C: 0 > 1 > 2
    };

    auto match = galeShapley(propPref, accPref);
    std::cout << "Stable matching:\n";
    for (int i = 0; i < 3; i++)
        std::cout << "  Proposer " << i << " -> Acceptor " << match[i] << "\n";

    return 0;
}
```

### Code Example (Python)

```python
from collections import deque


def gale_shapley(proposer_prefs, acceptor_prefs):
    """
    Gale-Shapley stable matching algorithm.

    Args:
        proposer_prefs: List of lists, proposer_prefs[i] = acceptor indices in preference order
        acceptor_prefs: List of lists, acceptor_prefs[j] = proposer indices in preference order

    Returns:
        List where result[i] = acceptor matched to proposer i
    """
    n = len(proposer_prefs)

    # Build acceptor ranking: acceptor_rank[a][p] = rank of proposer p for acceptor a
    acceptor_rank = [[0] * n for _ in range(n)]
    for a in range(n):
        for rank, p in enumerate(acceptor_prefs[a]):
            acceptor_rank[a][p] = rank

    match = [-1] * n            # acceptor -> proposer
    proposer_match = [-1] * n   # proposer -> acceptor
    next_proposal = [0] * n     # next acceptor index for each proposer

    free_proposers = deque(range(n))

    while free_proposers:
        p = free_proposers.popleft()
        a = proposer_prefs[p][next_proposal[p]]
        next_proposal[p] += 1

        if match[a] == -1:
            # Acceptor is free
            match[a] = p
            proposer_match[p] = a
        elif acceptor_rank[a][p] < acceptor_rank[a][match[a]]:
            # Acceptor prefers new proposer
            old_p = match[a]
            proposer_match[old_p] = -1
            free_proposers.append(old_p)
            match[a] = p
            proposer_match[p] = a
        else:
            # Acceptor rejects
            free_proposers.append(p)

    return proposer_match


# Demo
prop_pref = [
    [0, 1, 2],  # Proposer 0: A > B > C
    [1, 0, 2],  # Proposer 1: B > A > C
    [0, 1, 2],  # Proposer 2: A > B > C
]
acc_pref = [
    [1, 0, 2],  # Acceptor A: 1 > 0 > 2
    [0, 1, 2],  # Acceptor B: 0 > 1 > 2
    [0, 1, 2],  # Acceptor C: 0 > 1 > 2
]

match = gale_shapley(prop_pref, acc_pref)
print("Stable matching:")
for i, a in enumerate(match):
    print(f"  Proposer {i} -> Acceptor {a}")
```

### Code Example (Java)

```java
import java.util.*;

public class GaleShapley {
    static int[] galeShapley(int[][] proposerPrefs, int[][] acceptorPrefs) {
        int n = proposerPrefs.length;
        int[] match = new int[n];           // acceptor -> proposer
        int[] proposerMatch = new int[n];   // proposer -> acceptor
        int[] nextProposal = new int[n];
        Arrays.fill(match, -1);
        Arrays.fill(proposerMatch, -1);

        // Build acceptor ranking
        int[][] acceptorRank = new int[n][n];
        for (int a = 0; a < n; a++)
            for (int rank = 0; rank < n; rank++)
                acceptorRank[a][acceptorPrefs[a][rank]] = rank;

        Queue<Integer> freeProposers = new LinkedList<>();
        for (int i = 0; i < n; i++) freeProposers.add(i);

        while (!freeProposers.isEmpty()) {
            int p = freeProposers.poll();
            int a = proposerPrefs[p][nextProposal[p]++];

            if (match[a] == -1) {
                match[a] = p;
                proposerMatch[p] = a;
            } else if (acceptorRank[a][p] < acceptorRank[a][match[a]]) {
                int oldP = match[a];
                proposerMatch[oldP] = -1;
                freeProposers.add(oldP);
                match[a] = p;
                proposerMatch[p] = a;
            } else {
                freeProposers.add(p);
            }
        }
        return proposerMatch;
    }

    public static void main(String[] args) {
        int[][] propPref = {{0,1,2},{1,0,2},{0,1,2}};
        int[][] accPref = {{1,0,2},{0,1,2},{0,1,2}};
        int[] match = galeShapley(propPref, accPref);
        System.out.println("Stable matching:");
        for (int i = 0; i < 3; i++)
            System.out.println("  Proposer " + i + " -> Acceptor " + match[i]);
    }
}
```

---

## 162.2 Nash Equilibrium

### Definition

A **Nash Equilibrium** is a strategy profile where no player can improve their payoff by unilaterally changing their strategy, given that all other players keep their strategies fixed.

### Motivation

In competitive systems (routing, auctions, resource allocation), participants act selfishly. Nash equilibrium predicts the outcome when everyone plays optimally. Understanding it helps design systems where selfish behavior leads to good outcomes.

### Intuition

Consider drivers choosing between two routes. If everyone takes the highway, it's congested and slow. Some switch to back roads. At equilibrium, no one wants to switch — the highway is just fast enough to keep some drivers, and the back roads are just fast enough for the rest.

### Types of Nash Equilibrium

| Type | Description | Existence |
|---|---|---|
| Pure Nash | Deterministic strategies | May not exist |
| Mixed Nash | Randomized strategies | Always exists (Nash, 1950) |
| Correlated | Shared random signal | Always exists |

### Example: Prisoner's Dilemma

| | Cooperate | Defect |
|---|---|---|
| **Cooperate** | (3, 3) | (0, 5) |
| **Defect** | (5, 0) | (1, 1) |

**Nash Equilibrium**: (Defect, Defect) — neither player benefits from switching. But (Cooperate, Cooperate) gives a better outcome for both. This illustrates the tension between individual and collective rationality.

### Example: Rock-Paper-Scissors

| | Rock | Paper | Scissors |
|---|---|---|---|
| **Rock** | (0, 0) | (-1, 1) | (1, -1) |
| **Paper** | (1, -1) | (0, 0) | (-1, 1) |
| **Scissors** | (-1, 1) | (1, -1) | (0, 0) |

**Unique Nash Equilibrium**: Each player plays Rock, Paper, Scissors with probability 1/3. No pure Nash exists (every pure strategy is exploitable).

### Computing Nash Equilibrium

| Players | Complexity | Method |
|---|---|---|
| 2 (zero-sum) | Polynomial | Linear programming |
| 2 (general) | PPAD-complete | Lemke-Howson, support enumeration |
| 3+ | PPAD-complete | Approximation algorithms |

### Code: Finding Mixed Nash in 2×2 Game

```cpp
#include <iostream>
#include <vector>
#include <cmath>

// Find mixed Nash equilibrium for 2-player 2x2 game
// Player 1 chooses rows, Player 2 chooses columns
void findMixedNash(double A[2][2], double B[2][2]) {
    // Player 1 mixes rows with probability p
    // Player 2 mixes columns with probability q

    // For Player 1 to be indifferent:
    // A[0][0]*q + A[0][1]*(1-q) = A[1][0]*q + A[1][1]*(1-q)
    // q*(A[0][0] - A[0][1] - A[1][0] + A[1][1]) = A[1][1] - A[0][1]
    double denom_q = A[0][0] - A[0][1] - A[1][0] + A[1][1];
    if (std::abs(denom_q) < 1e-9) {
        std::cout << "No interior mixed Nash (degenerate game)\n";
        return;
    }
    double q = (A[1][1] - A[0][1]) / denom_q;

    // For Player 2 to be indifferent:
    // B[0][0]*p + B[1][0]*(1-p) = B[0][1]*p + B[1][1]*(1-p)
    double denom_p = B[0][0] - B[1][0] - B[0][1] + B[1][1];
    if (std::abs(denom_p) < 1e-9) {
        std::cout << "No interior mixed Nash (degenerate game)\n";
        return;
    }
    double p = (B[1][1] - B[1][0]) / denom_p;

    if (p >= 0 && p <= 1 && q >= 0 && q <= 1) {
        std::cout << "Mixed Nash Equilibrium:\n";
        std::cout << "  Player 1: Row 0 with p=" << p << ", Row 1 with p=" << (1-p) << "\n";
        std::cout << "  Player 2: Col 0 with q=" << q << ", Col 1 with q=" << (1-q) << "\n";

        double eu1 = p * (q * A[0][0] + (1-q) * A[0][1]) +
                     (1-p) * (q * A[1][0] + (1-q) * A[1][1]);
        double eu2 = q * (p * B[0][0] + (1-p) * B[1][0]) +
                     (1-q) * (p * B[0][1] + (1-p) * B[1][1]);
        std::cout << "  Expected payoff P1: " << eu1 << ", P2: " << eu2 << "\n";
    } else {
        std::cout << "No valid mixed Nash in (0,1)\n";
    }
}

int main() {
    // Matching Pennies: P1 wants same, P2 wants different
    double A[2][2] = {{1, -1}, {-1, 1}};  // P1 payoffs
    double B[2][2] = {{-1, 1}, {1, -1}};  // P2 payoffs

    std::cout << "Matching Pennies:\n";
    findMixedNash(A, B);

    // Battle of the Sexes
    double A2[2][2] = {{3, 0}, {0, 2}};
    double B2[2][2] = {{2, 0}, {0, 3}};

    std::cout << "\nBattle of the Sexes:\n";
    findMixedNash(A2, B2);

    return 0;
}
```

### Code Example (Python)

```python
import numpy as np
from scipy.optimize import linprog


def find_mixed_nash_2x2(A, B):
    """Find mixed Nash equilibrium for 2x2 game."""
    # Player 1 mixes rows with probability p
    # Player 2 mixes columns with probability q

    # Player 1 indifferent: q*A[0,0] + (1-q)*A[0,1] = q*A[1,0] + (1-q)*A[1,1]
    denom_q = A[0, 0] - A[0, 1] - A[1, 0] + A[1, 1]
    if abs(denom_q) < 1e-9:
        return None
    q = (A[1, 1] - A[0, 1]) / denom_q

    # Player 2 indifferent
    denom_p = B[0, 0] - B[1, 0] - B[0, 1] + B[1, 1]
    if abs(denom_p) < 1e-9:
        return None
    p = (B[1, 1] - B[1, 0]) / denom_p

    if 0 <= p <= 1 and 0 <= q <= 1:
        eu1 = p * (q * A[0, 0] + (1-q) * A[0, 1]) + (1-p) * (q * A[1, 0] + (1-q) * A[1, 1])
        eu2 = q * (p * B[0, 0] + (1-p) * B[1, 0]) + (1-q) * (p * B[0, 1] + (1-p) * B[1, 1])
        return {'p': p, 'q': q, 'eu1': eu1, 'eu2': eu2}
    return None


# Matching Pennies
A = np.array([[1, -1], [-1, 1]], dtype=float)
B = np.array([[-1, 1], [1, -1]], dtype=float)
result = find_mixed_nash_2x2(A, B)
print(f"Matching Pennies: p={result['p']:.3f}, q={result['q']:.3f}")

# Rock-Paper-Scissors (3x3, use support enumeration)
# Unique mixed Nash: (1/3, 1/3, 1/3) for both players
print("\nRock-Paper-Scissors: each action with probability 1/3")
```

---

## 162.3 Mechanism Design

### Definition

Mechanism design is "reverse game theory" — designing the rules of a game so that self-interested players' behavior leads to a desired outcome. The goal is to create incentive-compatible systems where truthful reporting is optimal.

### Motivation

In auctions, we want the item to go to the person who values it most, but bidders have incentive to underbid. Mechanism design creates rules where honest bidding is the best strategy.

### Key Properties

| Property | Definition | Example |
|---|---|---|
| Incentive compatibility | Truth-telling is a dominant strategy | Vickrey auction |
| Individual rationality | Participation is beneficial (non-negative utility) | Reserve prices |
| Budget balance | No external subsidies needed | Double auctions |
| Efficiency | Social welfare is maximized | VCG mechanism |

### Vickrey (Second-Price) Auction

Each bidder submits a sealed bid. The highest bidder wins but pays the *second-highest* bid.

**Why it works**: Bidding your true value is a dominant strategy. If you bid higher, you might win but pay more than your value. If you bid lower, you might lose an auction you could have won profitably.

**Example**: Three bidders value an item at $100, $80, $60.

| Bidder | True Value | Bid (truthful) | Outcome |
|---|---|---|---|
| A | \\(100 |\\)100 | Wins, pays $80 |
| B | \\(80 |\\)80 | Loses |
| C | \\(60 |\\)60 | Loses |

If A bids \\(90 instead of\\)100: Still wins, still pays $80. No benefit from lying.
If A bids $70: Loses to B. A missed a profitable opportunity.

### VCG Mechanism (Vickrey-Clarke-Groves)

Generalizes Vickrey auctions to multiple items. Each player pays the "externality" they impose on others.

**Payment rule**: Player i pays = (social welfare of others without i) - (social welfare of others with i's allocation)

### Code Example: Vickrey Auction (C++)

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Bidder {
    int id;
    double value;
    double bid;
};

void vickreyAuction(std::vector<Bidder>& bidders) {
    // Sort by bid (descending)
    std::sort(bidders.begin(), bidders.end(),
        [](const Bidder& a, const Bidder& b) { return a.bid > b.bid; });

    if (bidders.size() < 2) {
        std::cout << "Need at least 2 bidders\n";
        return;
    }

    Bidder& winner = bidders[0];
    double price = bidders[1].bid;  // Second-highest bid

    std::cout << "Vickrey Auction Result:\n";
    std::cout << "  Winner: Bidder " << winner.id
              << " (bid=" << winner.bid << ", value=" << winner.value << ")\n";
    std::cout << "  Price paid: $" << price << "\n";
    std::cout << "  Utility: $" << (winner.value - price) << "\n";

    std::cout << "\n  All bids:\n";
    for (auto& b : bidders)
        std::cout << "    Bidder " << b.id << ": bid=" << b.bid
                  << ", value=" << b.value << "\n";
}

int main() {
    std::vector<Bidder> bidders = {
        {0, 100, 100},
        {1, 80, 80},
        {2, 60, 60},
        {3, 40, 40}
    };

    vickreyAuction(bidders);

    // Demonstrate incentive compatibility
    std::cout << "\n--- What if Bidder 0 underbids? ---\n";
    std::vector<Bidder> bidders2 = {
        {0, 100, 70},  // Underbids
        {1, 80, 80},
        {2, 60, 60},
        {3, 40, 40}
    };
    vickreyAuction(bidders2);

    return 0;
}
```

### Code Example (Python)

```python
def vickrey_auction(bidders):
    """
    Run a Vickrey (second-price) auction.

    Args:
        bidders: List of (id, value, bid) tuples
    Returns:
        Winner info and price
    """
    # Sort by bid descending
    sorted_bidders = sorted(bidders, key=lambda x: x[2], reverse=True)

    winner = sorted_bidders[0]
    price = sorted_bidders[1][2]  # Second-highest bid

    print(f"Winner: Bidder {winner[0]} (bid={winner[2]}, value={winner[1]})")
    print(f"Price paid: ${price}")
    print(f"Utility: ${winner[1] - price}")

    return winner, price


# Demo
bidders = [
    (0, 100, 100),  # (id, true_value, bid)
    (1, 80, 80),
    (2, 60, 60),
    (3, 40, 40),
]

print("=== Truthful bidding ===")
vickrey_auction(bidders)

print("\n=== Bidder 0 underbids (70 instead of 100) ===")
bidders_liar = [(0, 100, 70), (1, 80, 80), (2, 60, 60), (3, 40, 40)]
winner, price = vickrey_auction(bidders_liar)
print(f"Note: Bidder 0 loses! Missed utility of ${100 - 80}")
```

### Code Example (Java)

```java
import java.util.*;

public class VickreyAuction {
    static class Bidder {
        int id;
        double value, bid;
        Bidder(int id, double value, double bid) {
            this.id = id; this.value = value; this.bid = bid;
        }
    }

    static void runAuction(List<Bidder> bidders) {
        bidders.sort((a, b) -> Double.compare(b.bid, a.bid));
        Bidder winner = bidders.get(0);
        double price = bidders.get(1).bid;
        System.out.printf("Winner: Bidder %d (bid=%.0f, value=%.0f)%n",
            winner.id, winner.bid, winner.value);
        System.out.printf("Price: $%.0f, Utility: $%.0f%n", price, winner.value - price);
    }

    public static void main(String[] args) {
        List<Bidder> bidders = Arrays.asList(
            new Bidder(0, 100, 100),
            new Bidder(1, 80, 80),
            new Bidder(2, 60, 60)
        );
        runAuction(bidders);
    }
}
```

---

## 162.4 Price of Anarchy

### Definition

The **Price of Anarchy (PoA)** measures the efficiency loss when players act selfishly. It's the ratio of the worst Nash equilibrium social welfare to the optimal social welfare.

```
PoA = (Social welfare of worst Nash) / (Optimal social welfare)
```

### Motivation

When designing systems where users make selfish choices (routing, resource allocation), we need to know: how much worse is the selfish outcome compared to a centrally optimized one?

### Example: Braess's Paradox

Adding a road to a network can *increase* travel time when drivers act selfishly.

```
Network: Two routes from S to T
- Route 1: S → A → T (cost: x/100 on S→A, 45 on A→T)
- Route 2: S → B → T (cost: 45 on S→B, x/100 on B→T)

With 4000 drivers:
- Nash: Each route has 2000 drivers, cost = 2000/100 + 45 = 65 per driver
- Optimal: Split 2000/2000, same cost = 65

Now add a zero-cost road A → B:
- Nash: Everyone takes S→A→B→T, cost = 4000/100 + 0 + 4000/100 = 80 per driver!
- Optimal: Still 65 per driver

PoA = 80/65 ≈ 1.23 — adding capacity made things worse!
```

### PoA for Common Games

| Game | PoA | Notes |
|---|---|---|
| Routing (linear costs) | 4/3 | Roughgarden & Tardos, 2002 |
| Routing (polynomial degree d) | Θ(d/log d) | — |
| Load balancing | 2 - 2/(n+1) | — |
| Network design | O(log n) | — |
| Selfish routing (general) | Unbounded | Without cost functions |

---

## 162.5 Congestion Games

### Definition

A congestion game is a game where players choose subsets of resources, and each resource's cost depends on the number of players using it.

### Motivation

Modeling network routing, where each link's latency increases with traffic. Each driver chooses a path (set of links), and each link's cost depends on congestion.

### Properties

**Theorem (Rosenthal, 1973)**: Every congestion game has a pure Nash equilibrium.

**Theorem (Monderer & Shapley, 1996)**: A game is a congestion game if and only if it is a potential game (has an exact potential function).

### Rosenthal's Potential Function

```
Φ(s) = Σ_e Σ_{k=1}^{n_e} c_e(k)
```

Where n_e is the number of players using resource e, and c_e(k) is the cost of resource e with k users.

### Code Example: Congestion Game (Python)

```python
import numpy as np
from itertools import product


class CongestionGame:
    def __init__(self, n_players, resources, strategies, cost_functions):
        """
        Args:
            n_players: Number of players
            resources: List of resource names
            strategies: List of lists, strategies[i] = list of resource subsets for player i
            cost_functions: Dict mapping resource -> function(n) -> cost given n users
        """
        self.n_players = n_players
        self.resources = resources
        self.strategies = strategies
        self.cost_functions = cost_functions

    def compute_cost(self, strategy_profile):
        """Compute cost for each player given a strategy profile."""
        # Count resource usage
        usage = {r: 0 for r in self.resources}
        for player_strategy in strategy_profile:
            for r in player_strategy:
                usage[r] += 1

        # Compute cost for each player
        costs = []
        for player_strategy in strategy_profile:
            cost = sum(self.cost_functions[r](usage[r]) for r in player_strategy)
            costs.append(cost)
        return costs

    def find_pure_nash(self):
        """Find all pure Nash equilibria by exhaustive search."""
        all_strats = [self.strategies[i] for i in range(self.n_players)]
        nash_equilibria = []

        for profile in product(*all_strats):
            costs = self.compute_cost(profile)
            is_nash = True

            for i in range(self.n_players):
                for alt in self.strategies[i]:
                    if alt == profile[i]:
                        continue
                    alt_profile = list(profile)
                    alt_profile[i] = alt
                    alt_costs = self.compute_cost(tuple(alt_profile))
                    if alt_costs[i] < costs[i]:
                        is_nash = False
                        break
                if not is_nash:
                    break

            if is_nash:
                nash_equilibria.append((profile, costs))

        return nash_equilibria

    def potential(self, strategy_profile):
        """Compute Rosenthal's potential function."""
        usage = {r: 0 for r in self.resources}
        for player_strategy in strategy_profile:
            for r in player_strategy:
                usage[r] += 1

        total = 0
        for r in self.resources:
            for k in range(1, usage[r] + 1):
                total += self.cost_functions[r](k)
        return total


# Example: Two players, two resources (roads)
# Each player chooses one road
# Cost = number of users on that road
game = CongestionGame(
    n_players=2,
    resources=['road_A', 'road_B'],
    strategies=[
        [['road_A'], ['road_B']],  # Player 0 strategies
        [['road_A'], ['road_B']],  # Player 1 strategies
    ],
    cost_functions={
        'road_A': lambda n: n,
        'road_B': lambda n: n,
    }
)

print("Congestion Game: 2 players, 2 roads")
print("Cost = number of users on road\n")

nash_eqs = game.find_pure_nash()
print(f"Pure Nash Equilibria: {len(nash_eqs)}")
for profile, costs in nash_eqs:
    print(f"  Profile: {profile}, Costs: {costs}")

# Braess's Paradox example
print("\n=== Braess's Paradox ===")
# Without shortcut: two routes S->A->T and S->B->T
# With shortcut: adds A->B with cost 0
# Cost functions model congestion
```

---

## 162.6 Applications

| Domain | Application | Technique |
|---|---|---|
| Ad auctions | Google, Facebook ads | VCG, GSP auctions |
| Spectrum allocation | FCC spectrum auctions | Combinatorial auctions |
| Cloud computing | Spot instances, pricing | Mechanism design |
| Network routing | Internet traffic | Congestion games |
| Kidney exchange | Organ donation matching | Stable matching |
| Blockchain | MEV, transaction ordering | Game theory |
| Ride sharing | Driver-rider matching | Market design |

---

## Exercises

### Exercise 1: Gale-Shapley Implementation
Implement the Gale-Shapley algorithm and verify that the proposer-optimal matching is indeed the best stable matching for proposers. Find a case where an acceptor could benefit from misreporting preferences.

### Exercise 2: Find All Nash Equilibria
For the 3×3 game matrix below, find all pure and mixed Nash equilibria:
```
(2,1) (0,0) (1,2)
(0,0) (1,2) (2,1)
(1,2) (2,1) (0,0)
```

### Exercise 3: Vickrey Auction
Simulate a Vickrey auction with 10 bidders whose values are drawn uniformly from [0, 100]. Run 1000 auctions and compute the average revenue. Compare with a first-price auction where bidders bid 50% of their value.

### Exercise 4: Braess's Paradox
Build a network with 4 nodes and demonstrate Braess's paradox. Show that adding an edge increases total travel time under selfish routing.

### Exercise 5: Price of Anarchy
For a load balancing game with n identical machines and n jobs of size 1, compute the exact Price of Anarchy. (Hint: It's 2 - 2/(n+1).)

---

## Interview Questions

### Question 1: Explain the Gale-Shapley algorithm and its properties.
**Answer**: Gale-Shapley finds a stable matching by having proposers propose to their most preferred available acceptor. If the acceptor prefers the proposer over their current match, they swap. It runs in O(n²) time, always terminates with a stable matching, and is proposer-optimal (proposers get their best possible stable match). It's used in NRMP residency matching and school choice.

### Question 2: Why is the Vickrey auction incentive-compatible?
**Answer**: In a Vickrey (second-price) auction, the winner pays the second-highest bid, not their own. Bidding your true value is a dominant strategy: overbidding risks winning and paying more than your value; underbidding risks losing an auction you could have won profitably. Since the price you pay doesn't depend on your bid (only on others' bids), there's no incentive to misreport.

### Question 3: What is the Price of Anarchy and why does it matter?
**Answer**: The Price of Anarchy measures the ratio of the worst-case Nash equilibrium welfare to the optimal welfare. A PoA of 1 means selfish behavior is efficient; a high PoA means significant efficiency loss. It matters for system design: if PoA is high, we need mechanisms (tolls, incentives) to guide behavior. For example, congestion pricing reduces the PoA of traffic routing.

### Question 4: Explain Braess's paradox.
**Answer**: Braess's paradox occurs when adding capacity to a network (e.g., a new road) increases total travel time under selfish routing. Each driver independently minimizes their own travel time, but the new equilibrium is worse for everyone. This happens because the new route creates an incentive for drivers to shift from other routes, increasing congestion on shared links.

### Question 5: How does mechanism design differ from game theory?
**Answer**: Game theory analyzes outcomes given fixed rules — "what will players do?" Mechanism design asks the reverse: "what rules should we set to achieve a desired outcome?" It's the engineering side of game theory. Key challenges: ensuring incentive compatibility (truth-telling is optimal), individual rationality (participation is beneficial), and efficiency (good outcomes).

---

## Cross-References

- **Graph Algorithms** (Chapters 97-105): Network flow, shortest paths in routing games
- **Linear Programming** (Chapter 140): Finding mixed Nash equilibria
- **Probability** (Chapter 150): Mixed strategies, expected payoffs
- **Dynamic Programming** (Chapter 45): Optimal bidding strategies
- **Greedy Algorithms** (Chapter 40): Approximation in mechanism design
- **Network Flow** (Chapter 104): Applications in kidney exchange, matching markets

---

## Summary

| Concept | Definition | Complexity | Application |
|---|---|---|---|
| Stable Matching | No blocking pair exists | O(n²) | NRMP, school choice |
| Nash Equilibrium | No unilateral deviation helps | PPAD-complete | Routing, auctions |
| Mechanism Design | Reverse game theory | Varies | Auctions, voting |
| Price of Anarchy | Efficiency loss from selfishness | Game-dependent | System design |
| Congestion Games | Resources with load-dependent costs | PNE exists | Network routing |
| Vickrey Auction | Second-price sealed bid | O(n log n) | Ad auctions |
