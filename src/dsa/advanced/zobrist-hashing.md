# Zobrist Hashing and Transposition Tables: The Incremental Hash Behind Game-Tree Search

Adversarial search revisits the same positions through different move orders, and a 40-ply chess search may evaluate the same position millions of times. Zobrist hashing (Albert Zobrist, UW-Madison TR #88, 1970) solves the bookkeeping problem: it assigns each state a ~64-bit fingerprint built from XOR-composable random keys, so a fingerprint can be updated in O(1) while a move is made and unmade. Those fingerprints index the engine's **transposition table** (TT) — the cache that lets Stockfish and its peers avoid re-searching repeated positions, order moves, and bound-propagate results across the tree.

Scope split, since this repo already covers parts of the topic: [Hashing Deep Dive](../chapters/ch94-hashing-deep-dive.md) introduces Zobrist hashing as a general XOR-based *set* fingerprint (order-independence, add/remove) with a minimal implementation, and [Minimax and Alpha-Beta](../chapters/ch180-minimax-alpha-beta.md) shows where a TT plugs into the alpha-beta skeleton. This page is the game-engine deep dive: how the random table is built, why 64 bits suffice (birthday math, honestly computed), what a real TT entry stores, replacement and aging policies, mate-score and repetition pitfalls when probing, and where the same technique is used outside chess. [Basic Game-Tree Search](../chapters/ch06-searching.md) has the un-memoized search baseline; [Cuckoo Hashing](./cuckoo-hashing.md) covers the general hash-table toolbox this page applies.

## Random-Table Construction

The whole scheme rests on one array of pseudorandom bitstrings, generated once at startup: one key per *feature* of the state. For chess that is 781 keys — 12 piece types × 64 squares, plus 1 side-to-move key, 4 castling-right keys, and 8 en-passant file keys (chessprogramming.org's canonical count). A position's hash is the XOR of the keys of all its active features.

Two engineering warnings from practice:

- **Seed quality matters.** Jonathan Schaeffer reported that his program Phoenix generated keys from a seed equal to his student ID; when he later added hash-error detection, the error rate was high — changing the seed dropped it dramatically. Engines therefore ship their own PRNG with a fixed seed so keys are identical (and portable, e.g. for opening books) on every platform.
- **Linear independence beats Hamming distance.** Scoring keys by minimum Hamming distance is misleading: keys can look pairwise distant yet XOR to zero in small combinations (Sven Reichard's analysis on chessprogramming.org). What actually matters is that no *small* subset of keys XORs to zero — a good PRNG achieves this in practice, which is why engines take the keys as generated.

## XOR Make/Unmake: O(1) Fingerprint Maintenance

Because XOR is its own inverse, one key per feature serves for both insertion and removal. A capture move touches four keys (the canonical knight example from chessprogramming.org):

```text
zobrist make/unmake dataflow: White knight b1->c3 captures black bishop

   h_old --^--[piece W knight][b1]   xor out: knight leaves b1
           ^--[piece B bishop][c3]   xor out: captured bishop leaves c3
           ^--[piece W knight][c3]   xor in:  knight arrives on c3
           ^--[side to move]         flip: black was to move, now white
           v  h_new
   unmake = the same four XORs (self-inverse) -> h_old restored bit-exactly
   cost: 4 XORs per move, independent of board size; a full rehash is O(pieces)
```

The side-to-move key is what makes transpositions match correctly: the same piece placement with the other player to move is a *different* position with a different score. Engines XOR exactly this way inside `make()`/`unmake()`; the worked demo below asserts incremental == rehash after every step of a real game. Null-move pruning needs the same care: a null move toggles only the side key (and must not be repeated), which is precisely why the side key exists as a separate feature.

## Why 64 Bits: the Birthday Bound, Honestly Computed

Collision probability for n stored keys of b bits is, to first order, n²/2^(b+1) — the birthday bound. The reachable-state space dwarfs any key space: an upper bound for chess is ~10⁴⁶ positions (Chinchalkar 1996), against 2⁶⁴ ≈ 1.84·10¹⁹ different 64-bit keys, so key collisions (type-1 errors) are *inherent*; what engines control is their frequency and cost. James Gillogly's WCCC 1989 table (reproduced on chessprogramming.org) gives bits needed for a target collision probability; it matches the closed form b = ⌈2·log₂(n) − 1 − log₂(p)⌉ exactly:

| Positions stored | Bits for P ≤ 1% | Bits for P ≤ 0.01% |
|-----------------:|----------------:|-------------------:|
| 1e5              | 39              | 46                 |
| 1e6              | 46              | 53                 |
| 1e8              | 59              | 66                 |
| 1e10             | 73              | 79                 |

Hyatt and Cozzie's 2005 study (ICGA Journal 28(3), doi 10.3233/ICG-2005-28302) asked whether all this collision avoidance is worth it and concluded 64-bit signatures are more than sufficient — occasional collisions cost less elo than the slowdown of wider keys. Stockfish's `tt.h` says the same thing from the engine side: collisions "may cause chess playing issues (bizarre blunders, faulty mate reports, etc)", but fixing them completely would also cost elo, and "such risk decreases quickly with larger TT size". The demo below measures 16-, 32-, and 64-bit collision counts over all 5,478 valid tic-tac-toe states and compares against the birthday prediction — including an instructive mismatch: for one fixed seed, a single 16-bit slice lands far from the prediction, because XOR composition makes collision events *correlated* (the linear-independence issue above), so the bound holds in expectation, not per seed.

## Inside a Real Transposition Table

A TT is a fixed-size array of slots; the index comes from the hash key, and a truncated check key disambiguates. Stockfish splits its 64-bit key three ways: the index is `mul_hi64(key, clusterCount)` (multiplicative hashing), each 32-byte cluster — exactly one cache line, 3 entries — is scanned, and the *low* 16 bits are stored inside the entry as the check key `key16`. Index collisions (type-2) happen constantly and are handled by the check key; key collisions (type-1) are the rare birthday-bound event. Per chessprogramming.org, the TT supplies "75% of cutoffs produced in a position with hash moves" via the stored hash move alone in Stockfish.

```text
TT probe flow (Stockfish-style, 3-entry clusters)
  64-bit zobrist key k
     |  index = mul_hi64(k, clusterCount)          [check key = low 16 bits of k]
     v
  cluster (3 entries, 32 B = one cache line)
     |-- entry with key16 == u16(k)? --no--> victim = max(depth - 8*age);
     |                                       store key16, move, value, eval, depth, bound|pv|gen
     | yes
     v
  stored depth >= remaining depth? --no--> keep only the hash move (ordering)
     | yes
     v
  bound test against current (alpha, beta) window
     EXACT -> return stored | LOWER & s>=beta -> cutoff | UPPER & s<=alpha -> cutoff
     otherwise -> re-search, then store (possibly replacing)
```

Entry layout (Stockfish `tt.cpp`, 10 bytes per entry):

| Field      | Bits | Purpose                                     |
|------------|-----:|---------------------------------------------|
| key        |   16 | check key (low bits of the 64-bit key)      |
| depth      |    8 | draft the position was searched to          |
| pv         |    1 | PV-node flag, boosts replacement priority   |
| bound      |    2 | EXACT / LOWER / UPPER                       |
| generation |    5 | search age counter, wraps "like a clock"    |
| move       |   16 | best move (hash move)                       |
| value      |   16 | search score for the node                   |
| eval       |   16 | cached static evaluation                    |

Bound flags encode what alpha-beta actually learned: EXACT (PV-node, true score), LOWER (cut-node, fail high, score ≥ beta), UPPER (all-node, fail low, score ≤ alpha). A stored score is usable only when its depth is at least the remaining depth *and* its bound type fits the current window — otherwise the entry still helps by supplying the hash move for ordering.

### Replacement Schemes

When a probe misses, something must be evicted. The two classic poles, per chessprogramming.org's taxonomy:

| Scheme                       | Rule                                            | Bias                       |
|------------------------------|-------------------------------------------------|----------------------------|
| Always replace               | every store overwrites                          | recency                    |
| Depth-preferred              | overwrite only if the new entry is deeper       | work saved per future hit  |
| Two-tier (Thompson & Condon) | one depth-preferred + one always-replace slot   | both                       |
| Bucket / n-way               | overwrite lowest-depth entry in the cache-line  | both                       |
| Aging                        | generation byte marks stale entries for reuse   | relevance across root moves|

Real engines mix all of it. Stockfish's `save()` overwrites when the bound is EXACT, the slot holds a different position, the newcomer is deeper (PV entries weighted ×2), or the old entry is from a previous generation; on a probe miss the victim is the cluster entry maximizing `depth − 8·relative_age` — each generation of age costs 8 pseudo-depth units, with 5-bit generations subtracted via unsigned wraparound ("we count generations like clocks count hours"). The demo's mini-search shows the schemes are not free wins: at a forced 1024-slot table, always-replace searched fewer nodes than naive depth-preferred, because with shallow drafts recency outranks depth — exactly why production schemes blend considerations instead of picking a side.

### Probing Pitfalls: Mate Scores, Repetitions, GHI

Two classic correctness bugs live at the probe site:

- **Mate scores are ply-relative.** "Mate in 3 from here" is meaningless without knowing *here*. Stockfish stores with `value_to_tt(v, ply)` ("adjusts a mate or TB score from 'plies to mate from the root' to 'plies to mate from the current position'") and converts back on probe with `value_from_tt(v, ply, rule50_count)`; the demo's toy search dodges this by using node-relative terminal scores only. `value_from_tt` additionally downgrades mate claims that the 50-move rule could invalidate, "to avoid potentially false mate or TB scores related to the 50 moves rule and the graph history interaction".
- **Repetitions and path dependence (GHI).** Draw-by-repetition needs a position's *history*, not just its score. Engines keep the chain of Zobrist keys since the last irreversible move (capture or pawn move) and test two/threefold matches against it — the FIDE-equality definition (same piece placement, same castling rights, same en-passant availability) maps exactly onto "equal Zobrist keys". The subtlety is Graph History Interaction: the same placement reached by different paths can have different repetition status, so a TT score cached under one path can be wrong under another; CPW's GHI page and Stockfish's 50-move guard in `value_from_tt` are the standard reminders. [ch94](../chapters/ch94-hashing-deep-dive.md)'s set-hash view does not cover any of this — the side key and history are what turn a set fingerprint into a game-state fingerprint.

## Beyond Chess

The same fingerprint machinery recurs wherever search states repeat. Monte-Carlo tree search implementations use transposition handling so identical nodes reached by different move sequences share visit statistics — the "Transpositions and Move Groups" work of Childs, Brodeur and Kocsis (2008) and Monte-Carlo graph search for AlphaZero-style engines, both surveyed via chessprogramming.org's MCTS page and the Browne et al. survey (doi 10.1109/TCIAIG.2012.2186810). In metaheuristics, Woodruff and Zemel's hashing vectors (doi 10.1007/BF02022565) memorize visited solutions in tabu search to prevent cycling — the same detect-you've-been-here trick with a smaller state. Puzzle solvers (sliding puzzles, Rubik's cube BFS/IDA*) use Zobrist-style XOR keys for their visited sets, inheriting both the O(1) make/unmake and the birthday-bound caveats.

## Worked Demo

```python
import random, itertools
from collections import Counter
# ---------- 1. seeded 64-bit Zobrist table for 3x3 tic-tac-toe ----------
CELLS, X, O = 9, 1, 2
rng = random.Random(1970)                                   # fixed seed -> reproducible keys
PIECE_SQ = [[rng.getrandbits(64) for _ in range(CELLS)] for _ in range(2)]
SIDE = rng.getrandbits(64)                                  # toggle when O is to move
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
def rehash(b, side):                                        # full O(cells) recompute
    h = 0
    for s in range(CELLS):
        if b[s]: h ^= PIECE_SQ[b[s]-1][s]
    return h ^ SIDE if side == O else h
class Game:
    def __init__(self):
        self.b, self.side, self.h, self.hist = [0]*CELLS, X, 0, []
    def legal(self):
        return [s for s in range(CELLS) if not self.b[s]]
    def make(self, sq):                                     # O(1) incremental update
        self.b[sq] = self.side
        self.h ^= PIECE_SQ[self.side-1][sq]                 # XOR is self-inverse: one key for add AND remove
        self.side = X + O - self.side
        self.h ^= SIDE
        self.hist.append(sq)
    def unmake(self):                                       # exact inverse, no saved hash needed
        sq = self.hist.pop()
        self.side = X + O - self.side
        self.h ^= SIDE
        self.h ^= PIECE_SQ[self.b[sq]-1][sq]
        self.b[sq] = 0
    def winner(self):
        for a, c, d in LINES:
            if self.b[a] and self.b[a] == self.b[c] == self.b[d]:
                return self.b[a]
        return 0
g, grng, pres, nm, nu = Game(), random.Random(7), [], 0, 0
while not g.winner() and len(g.hist) < 9:                   # play a full deterministic game
    pre = g.h
    sq = grng.choice(g.legal())
    g.make(sq)
    assert g.h == rehash(g.b, g.side)                       # incremental == rehash after every make
    if nm == 0: first_sq, first_delta = sq, g.h ^ pre
    nm += 1
    pres.append(pre)
while g.hist:                                               # unwind; every unmake must restore bit-exact
    g.unmake()
    assert g.h == pres.pop() and g.h == rehash(g.b, g.side)
    nu += 1
assert g.h == 0 and not any(g.b)
print(f"make/unmake walk: {nm} makes + {nu} unmakes, incremental==rehash asserted every step")
print(f"first move: X to sq {first_sq}, delta = piece[X][{first_sq}] ^ SIDE = {first_delta:#018x}")
# ---------- 2. alpha-beta with a fixed-size transposition table ----------
class TT:
    def __init__(self, slots, depth_pref):
        self.t, self.dp, self.mask = [None]*slots, depth_pref, slots-1
        self.probes = self.hits = self.stores = self.cut = self.evict = 0
    def probe(self, h):
        self.probes += 1
        e = self.t[h & self.mask]
        if e and e[0] == (h >> 12) & 0xFFFF:                # stored key guards index collisions
            self.hits += 1
            return e                                        # (key16, depth, flag, score, best)
        return None
    def store(self, h, depth, flag, score, best):
        old = self.t[h & self.mask]
        if self.dp and old and old[1] >= depth:
            return                                          # depth-preferred: keep the deeper entry
        self.evict += old is not None                       # always-replace: unconditional overwrite
        self.t[h & self.mask] = ((h >> 12) & 0xFFFF, depth, flag, score, best)
        self.stores += 1
def ab(g, depth, alpha, beta, tt, nodes, use_tt):
    nodes[0] += 1
    w = g.winner()
    if w:                                                   # terminal: node-relative score, no ply fixup needed
        return -(10 - len(g.hist))
    if depth == 0:
        return 0
    e = tt.probe(g.h) if use_tt else None
    if e and e[1] >= depth:                                 # bound-aware cutoff (entry depth must suffice)
        f, s = e[2], e[3]
        if f == 2 or (f == 1 and s >= beta) or (f == 0 and s <= alpha):
            tt.cut += 1
            return s
    best, a0, bmove = -99, alpha, None
    moves = g.legal()
    if e and e[4] in moves:                                 # hash move searched first
        moves.remove(e[4]); moves.insert(0, e[4])
    for sq in moves:
        g.make(sq)
        s = -ab(g, depth-1, -beta, -alpha, tt, nodes, use_tt)
        g.unmake()
        if s > best:
            best, bmove = s, sq
        if s > alpha:
            alpha = s
            if alpha >= beta:
                break
    flag = 2 if a0 < best < beta else 1 if best >= beta else 0   # 0 upper, 1 lower, 2 exact
    if use_tt:
        tt.store(g.h, depth, flag, best, bmove)
    return best
n0 = [0]; v0 = ab(Game(), 9, -99, 99, TT(8, False), n0, False)
dp = TT(1024, True);  n1 = [0]; v1 = ab(Game(), 9, -99, 99, dp, n1, True)
ar = TT(1024, False); n2 = [0]; v2 = ab(Game(), 9, -99, 99, ar, n2, True)
assert v0 == v1 == v2
print(f"plain alpha-beta          : {n0[0]:>6} nodes, value {v0:+d}")
print(f"TT depth-preferred (1024) : {n1[0]:>6} nodes, value {v1:+d}  probes {dp.probes}, hits {dp.hits}, stores {dp.stores}, evictions {dp.evict}, tt-cutoffs {dp.cut}")
print(f"TT always-replace (1024)  : {n2[0]:>6} nodes, value {v2:+d}  probes {ar.probes}, hits {ar.hits}, stores {ar.stores}, evictions {ar.evict}, tt-cutoffs {ar.cut}")
# ---------- 3. honest collision measurement over a fixed state set ----------
def valid(b):
    xs, os_ = b.count(X), b.count(O)
    if xs - os_ not in (0, 1): return False
    wx = any(b[a] == b[c] == b[d] == X for a, c, d in LINES)
    wo = any(b[a] == b[c] == b[d] == O for a, c, d in LINES)
    return not (wx and wo or wx and xs != os_+1 or wo and xs != os_)
states = [b for b in itertools.product((0, 1, 2), repeat=9) if valid(b)]
n = len(states)
KEYS = []
for b in states:                                            # hash = XOR of piece keys, side fixed
    h = 0
    for s, p in enumerate(b):
        if p: h ^= PIECE_SQ[p-1][s]
    KEYS.append(h)
def pairs_at(shift, mask):
    c = Counter((k >> shift) & mask for k in KEYS)
    return sum(v*(v-1)//2 for v in c.values())
pairs = n*(n-1)//2
s16 = [pairs_at(sh, 0xFFFF) for sh in (0, 16, 32, 48)]
print(f"collision check over n={n} valid boards ({pairs} pairs):")
print(f"  16-bit keys: observed pairs per slice {s16}, mean {sum(s16)/4:.1f} vs birthday-expected {pairs/2**16:.1f}")
print(f"  32-bit keys: birthday-expected {pairs/2**32:.4g}, observed {pairs_at(32, 0xFFFFFFFF)}")
print(f"  64-bit keys: birthday-expected {pairs/2**64:.4g}, observed {pairs_at(0, 2**64-1)}")
```

```text
make/unmake walk: 9 makes + 9 unmakes, incremental==rehash asserted every step
first move: X to sq 5, delta = piece[X][5] ^ SIDE = 0x1bd3b01b43c8cca1
plain alpha-beta          :  20866 nodes, value +0
TT depth-preferred (1024) :   9384 nodes, value +0  probes 6256, hits 1846, stores 1274, evictions 392, tt-cutoffs 1236
TT always-replace (1024)  :   7324 nodes, value +0  probes 5518, hits 2428, stores 3376, evictions 2495, tt-cutoffs 2142
collision check over n=5478 valid boards (15001503 pairs):
  16-bit keys: observed pairs per slice [302, 392, 185, 110], mean 247.2 vs birthday-expected 228.9
  32-bit keys: birthday-expected 0.003493, observed 0
  64-bit keys: birthday-expected 8.132e-13, observed 0
```

Reading the numbers: the TT more than halves the node count (20,866 → 7,324) with the table holding only 1,024 of the 5,478 possible states; always-replace's higher eviction count (2,495 vs 392) is *not* a defect here — fresher entries win on a 9-ply game, which is the recency half of the trade-off production engines blend. The 16-bit slices realize 110–392 colliding pairs against a 228.9 expectation — the mean over slices (247.2) approaches the prediction while individual slices swing widely, a live demonstration that XOR-composed keys have *correlated* collision events; at 32 and 64 bits the expected counts (0.0035 and 8.1e-13) make zero collisions the overwhelmingly likely outcome, which is exactly the regime engines live in.

## Interview Questions

1. **Why not store full board descriptions in the TT instead of hash keys?** A chess position as a structure costs dozens of bytes and comparing it is O(pieces); the TT needs a fast index anyway. The Zobrist key gives both: index bits for addressing, 16 stored check bits for verification, all in a 10-byte entry that packs three-to-a-cache-line. You accept a birthday-bound type-1 collision risk in exchange for speed — quantified as acceptable by Hyatt & Cozzie and by Stockfish's own comments.
2. **Your engine plays a bizarre move after probing the TT. Walk through the suspects in order.** Check bound-vs-window fit and stored depth ≥ remaining depth first (most "TT bugs" are misuse of LOWER/UPPER bounds), then mate-score ply adjustment (stored "mate in n" is node-relative), then partial-key collision (with only 16 check bits, verify the stored move is at least pseudo-legal), and finally path-dependent repetition state (GHI) — a score cached under one move history may be wrong under another.
3. **Why does depth-preferred replacement not always beat always-replace?** Depth-preferred maximizes work saved per future hit but ignores recency; entries kept for their depth may never be probed again, while always-replace keeps the freshest lines. The demo shows always-replace winning at shallow drafts; production schemes (two-tier, buckets, Stockfish's exact-bound/deeper/newer-generation rule) blend depth, recency, and bound type — and aging via a generation byte sweeps entries from earlier root positions.
4. **Where does Zobrist hashing break down?** It requires the state to decompose into independently-keyed *features* that toggle cleanly: no toggleable feature for something like "current path-dependent repetition count" or clock values, so those live outside the hash; and 32-bit-float-only languages (JavaScript numbers) can't hold 64-bit XOR results, forcing two-lane 32-bit keys or additive 48-bit variants. Proof-style search where one wrong bound is fatal treats collisions less tolerantly than elo-optimizing game engines do.

## References

1. Zobrist, A. L. (1970). *A New Hashing Method with Application for Game Playing*. Technical Report #88, Computer Sciences Dept., University of Wisconsin–Madison — scanned copy: https://minds.wisc.edu/items/992e8337-5597-4a51-89d3-3fbe3559201a
2. Zobrist, A. L. (1990). Reprint of TR #88 in *ICGA Journal* 13(2):69–73. https://doi.org/10.3233/ICG-1990-13203
3. chessprogramming.org, *Zobrist Hashing* (key counts, make/unmake example, seed anecdote, linear independence). https://www.chessprogramming.org/Zobrist_Hashing
4. chessprogramming.org, *Transposition Table* (entry contents, bound types, collisions, Gillogly bits table, replacement taxonomy). https://www.chessprogramming.org/Transposition_Table
5. Hyatt, R. & Cozzie, A. (2005). *The Effect of Hash Signature Collisions in a Chess Program*. ICGA Journal 28(3):131–139. https://doi.org/10.3233/ICG-2005-28302
6. Stockfish, `src/tt.h` and `src/tt.cpp` (entry layout, cluster/size asserts, replacement and age rules, racy-shared-TT comments). https://github.com/official-stockfish/Stockfish/blob/master/src/tt.h
7. Stockfish, `src/search.cpp` (`value_to_tt`/`value_from_tt` mate-score conversion, 50-move and GHI guard). https://github.com/official-stockfish/Stockfish/blob/master/src/search.cpp
8. chessprogramming.org, *Repetitions* (FIDE equality definition, key-chain detection). https://www.chessprogramming.org/Repetitions
9. chessprogramming.org, *Graph History Interaction* (path dependence in search). https://www.chessprogramming.org/Graph_History_Interaction
10. Browne, C. et al. (2012). *A Survey of Monte Carlo Tree Search Methods*. IEEE Trans. Comp. Intell. and AI in Games 4(1):1–43. https://doi.org/10.1109/TCIAIG.2012.2186810
11. Woodruff, D. & Zemel, E. (1993). *Hashing Vectors for Tabu Search*. Annals of Operations Research 41. https://doi.org/10.1007/BF02022565
12. chessprogramming.org, *Monte-Carlo Tree Search* (transposition handling in MCTS: Childs/Brodeur/Kocsis 2008, Monte-Carlo graph search). https://www.chessprogramming.org/Monte-Carlo_Tree_Search
