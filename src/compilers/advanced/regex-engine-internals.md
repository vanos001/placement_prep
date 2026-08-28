# Regex Engine Internals: Backtracking Machines, Automata, and the Linear-Time Divide

A regex pattern is a small program, and every mainstream engine executes it in one of two fundamentally different ways: as a **backtracking virtual machine** that commits to one path at a time and undoes choices on failure (Perl, PCRE2, Python `re`, V8's Irregexp, Oniguruma), or as an **automaton simulator** that advances every viable path simultaneously (Thompson NFA simulation, subset-constructed DFAs, RE2, Go's `regexp`, Rust's `regex`, Hyperscan). The choice is not an implementation detail: it fixes the worst-case complexity, decides which features can exist at all (backreferences? captures? lookaround?), determines whether captures cost extra, and decides whether one hostile input can pin a CPU core for hours. Russ Cox's three-part essay series remains the clearest map of this divide [1], and its central claim - that Thompson's 1968 construction was already linear-time - still surprises interviewers.

## One pattern, two execution families

```text
                 regex pattern string
                          |
                   parse to AST, desugar
                          |
        +-----------------+------------------+
        |                                    |
  backtracking VM                      automaton engines
  compile to a node program:      compile to an NFA, then:
    char c, split(a,b),             - simulate the NFA with state
    jmp, save slot k                  SETS per input char (Thompson)
  execute one path;                 - build DFA states lazily (RE2)
  push alternatives on a            - run "threads" carrying capture
  backtrack stack; undo               slots (Pike VM)
  on failure                        - literal-trigger + confirm
                                      decomposition (Hyperscan)
        |                                    |
  one path at a time                  all viable paths at once
  worst case exponential              worst case linear in input
  full feature soup                   features pruned to stay linear
```

The same input can be matched by engines from both families with identical results on benign patterns - and wildly different behavior on hostile ones:

| Engine | Family | Worst case | Captures | Signature traits |
|---|---|---|---|---|
| PCRE2 | backtracking VM | exponential | native | `match_limit` fuse, atomic groups, possessive quantifiers |
| V8 Irregexp | backtracking VM (JIT) | exponential | native | compiles patterns to native code; powers JS `RegExp` |
| Python `re`, Oniguruma | backtracking VM | exponential | native | classic ReDoS incidents |
| RE2 | lazy DFA + NFA sim | linear | two-pass DFA / Pike VM | memory budget; no backrefs, no lookaround |
| Go `regexp`, Rust `regex` | RE2 lineage | linear | yes | same syntax pruning as RE2 |
| Hyperscan | literal + NFA/DFA hybrid | linear | none | streaming mode, thousands of patterns |

## The backtracking VM: how PCRE-style engines really run

The pattern compiles to a program of `char`, `class`, `split`, `jmp`, and `save` nodes. `split(a, b)` encodes preference order: try branch `a` first, branch `b` only if everything downstream of `a` fails. Execution keeps a program counter and a stack of saved `(pc, position, capture slots)` continuation points. Greedy and lazy quantifiers differ only in the order branches are pushed. This one mechanism gives Perl-style **leftmost-first** semantics for free: the first path that reaches acceptance in priority order wins, so `cat|category` prefers `cat`.

The same mechanism is the vulnerability. For `^(a+)+$`, the outer plus iterates the inner `(a+)` group; when the subject is a run of `a` characters that ultimately fails (say `"aaaa...aX"`), the engine cannot know that the `X` dooms every path, so it rules out every ordered split of the a-run:

```text
^(a+)+$ vs "aaaaX": every split of the 4-char a-run is one doomed path

   aaaa  |  aaa|a  |  aa|aa  |  aa|a|a  |  a|aaa  |  a|aa|a  |  a|a|aa  |  a|a|a|a
          |         |          |           |          |          |           |
         fail      fail       fail        fail       fail       fail        fail

ordered splits of n items into chunks = compositions of n = 2^(n-1)
```

A run of 25 `a` characters has 16,777,216 splits to rule out, and each split costs stack traffic - the textbook exponential. Nested quantifiers over overlapping alternatives (`(a|aa)+`, `(.*)*`, `(\w+\.)*`) all compile to this shape. PCRE2's answer is a fuse, not a fix: by default the interpreter aborts after **10,000,000 steps** (`MATCH_LIMIT`, with a separate recursion depth limit) and reports an error instead of hanging. Atomic groups `(?>...)` and possessive quantifiers `a++` are the manual patches: they discard backtrack points so the engine cannot re-enter a group - moving work from "wait for the fuse" to "user redesigned the pattern". None of this is a guarantee; it is damage control. The executed probe below measures the explosion directly.

V8's Irregexp sits in the same family: it compiles patterns to native code (with a bytecode interpreter as a cold-path tier), which makes ordinary matches extremely fast, but JavaScript's `RegExp` supports backreferences and lookbehind, so no automaton-based engine can replace it - the exponential search space is the price of the feature set. In Node.js this matters structurally: one event loop serves every request, so a single hostile pattern blocks all of them; the V8/event-loop mechanics live in [Node.js](../../languages/javascript/nodejs.md).

## Thompson's answer: track every path at once

Thompson's construction compiles the pattern into an NFA with epsilon transitions, and simulation never backtracks: after each input character, keep the **set** of all states reachable now. A character transition consumes the set in one sweep; an empty set means the match has failed; acceptance is "the accept state is in the final set". Failure is no longer an event that triggers undoing - it is just a set becoming empty.

```text
simulate (a+)+ over "aab" by carrying the alive-state set forward:

   'a' : every state that can consume 'a' stays alive - first chunk AND
         loop-back edge; ambiguity is absorbed, nothing needs undoing
   'b' : only exit-edge targets survive
   end : accept iff accept state is in the final set

per char: O(m) states x O(1) outgoing edges each  =>  O(n * m) total work
```

This is where the executed probe's second column comes from: for a 6-state NFA, 26 input characters cost 130 state visits, period. What the plain simulation cannot do is almost as important. Captures require remembering *which* iteration of a loop produced each substring - per-thread history that a state set deliberately discards. Backreferences are not merely expensive but inexpressible: `\1` matches "whatever group 1 captured at runtime", which is not a property of the pattern's structure. And Perl's leftmost-first ordering is extra machinery, though automata get **leftmost-longest** (POSIX) semantics almost for free, since they implicitly see every match and can pick the longest.

## Subset construction and the DFA memory wall

Run the powerset construction offline and each set of NFA states becomes one DFA state, giving the fastest known matchers: per input character, one table lookup (often SIMD- and cache-tuned), independent of pattern size at match time. The wall is the state count: a DFA state is a set of NFA states, and there are up to `2^m` of them.

```text
pattern (a|b)*a(a|b){3}    ("the 4th-from-last char is an 'a'")

NFA : a handful of states; the trailing (a|b){3} soaks up any three chars
DFA : one table row per state means a state encodes the last three
      characters -> 2^3 = 8 core states; m trailing chars -> 2^m states
```

Counted repetition inflates the same wall: `a{1,100}` compiles to a hundred copied fragments, so `m` grows before the powerset ever runs. Engines that promised compile-time determinization (classic `flex`, `grep`-style tools) live or die by this blowup - which is why the modern answer is to refuse to build the DFA up front.

## Building DFAs on demand: the lazy DFA and RE2

The lazy DFA inverts the order: simulate, and materialize a DFA state only the first time the input actually reaches it. Real inputs visit a tiny fraction of the theoretical state space, so the cache stays small - each cached entry is one transition row over byte equivalence classes. RE2's architecture (documented across its repo and Cox's "in the wild" write-up [1][2]) stacks this with fallbacks:

```text
             input byte -> class c
                     |
        is the cached transition row for the current
        DFA state already built?
             | hit                | miss
             v                    v
        next state = row[c]   build the state from the NFA program,
                              store its row, check the memory budget
                                       |
              budget exhausted -> abandon the DFA mid-match, finish on NFA engines
```

RE2 compiles to a small NFA program and selects among engines: a one-pass engine when every state has a single viable exit (captures come cheap), the lazy DFA for the heavy lifting, a bounded BitState backtracker with a visited bitmap, and Pike-VM-style NFA simulation with threads when captures must be recovered. The README states the contract directly: match time is linear in input length, memory usage stays inside a configurable budget with graceful failure, and recursion is avoided outright so stack overflow cannot happen [2]. Those guarantees are bought in the syntax, not just the runtime: backreferences and lookaround are explicitly unsupported [2], because admitting them would forfeit linearity. Go's `regexp` and Rust's `regex` are RE2-lineage engines with the same pruning.

## Pike VM: captures without backtracking

The missing piece is captures at linear cost. The Pike VM runs Thompson simulation, but each active thread carries its own capture-slot vector; when a `save` instruction fires, the thread records its current input position. Threads are kept in priority order (higher-priority first), and a lower-priority thread may not overwrite slots that a higher-priority one already wrote - which reproduces Perl's leftmost-first semantics exactly, without a backtrack stack. Cost is `O(n * m)` time with a constant-factor hit from slot copying, and `O(m)` live threads; the worst case stays polynomial regardless of how pathological the pattern or input is. This is the engine RE2, Go, and Rust fall back to when the fast paths cannot deliver capture groups.

## Hyperscan: literal-first automata at packet speed

Hyperscan (Intel) solves a different regime: thousands of patterns, untrusted streaming input, DPI-grade throughput, no capture groups. Its compiler decomposes patterns into the Rose engine's structure: cheap **literal triggers** do the filtering, and expensive confirmation automata run only where a literal already fired - most of the input never touches an NFA at all. Literal scanning itself is SIMD-accelerated (the FDR/Teddy matchers, visible in the repo as `src/fdr/teddy.c`).

Two more tricks matter for interviews. First, **character-class acceleration**: before running automata, the input is scanned for classes like `[a-z0-9]` with dedicated SIMD kernels - Shufti uses nibble-indexed lookup tables and Truffle uses per-character bit masks, both shipped as `src/nfa/shufti.c` and `src/nfa/truffle.c` [3][4]. Second, **streaming mode**: matching state is checkpointed between calls with a fixed, bounded per-stream footprint, so memory scales with the number of concurrent flows rather than with input length - the property network inspection stacks need. The USENIX ATC 2019 paper describes how engine selection per pattern (literal vs. NFA vs. DFA) keeps worst-case behavior bounded across huge pattern sets [5]. Note the family resemblance to RE2: backreferences and lookaround are unsupported here too.

## What each feature costs

The whole page compresses into one accounting table: automata buy linearity by giving up features, and the features they give up are precisely the ones that make backtracking unbounded.

| Feature | Backtracking VM | Linear automata | Why automata struggle |
|---|---|---|---|
| chars, classes, repetition | native | linear; lazy vs greedy = thread priority | both orderings fold into simulation order |
| capture groups | two save slots per group | Pike VM threads; plain DFA loses them | a DFA state cannot carry per-path history |
| backreferences `\1` | native | not expressible | matching depends on runtime-captured text |
| lookaround `(?=...)` `(?!...)` | native | dropped (RE2, Hyperscan) | unbounded lookahead is a second automaton needing coordination |
| atomic `(?>...)` / possessive `++` | native | dropped | they prune the search order automata must fully explore |
| counted repetition `a{2,100}` | compile-time expansion | NFA state inflation | `m` grows; DFA worst case is `2^m` |
| POSIX leftmost-longest | must exhaust all paths | natural | automata already track every path simultaneously |

## The neighboring family: PEG, packrat, and ANTLR

When the language has recursive structure - nested JSON, expression grammars, protocol headers - no automaton trick helps, because regular expressions recognize regular languages and nesting is not regular. That is the parser family's job: Parsing Expression Grammars with packrat memoization get linear-time recognition by trading `O(input * grammar)` memory for memoized results (Ford, POPL 2004), and ANTLR's adaptive `ALL(*)` prediction decides on the fly how much lookahead is needed. Backtracking still exists there, but it is bounded by grammar structure rather than detonated by input shape. The recognizer-vs-matcher split, and where LL/LR/GLR fit, are covered in [Parsing](../parsing.md) and [Parsing, Advanced](../parsing-advanced.md); the regex engines above are the fast, narrow specialization for flat patterns.

## The classic probe, executed

Both engines of this page, in pure Python: a textbook backtracker for `^(a+)+$` and a Thompson NFA simulator built from a tiny AST, run against unmatchable subjects `"a"*n + "X"`.

```python
# Classic ReDoS probe: pattern ^(a+)+$ against "a"*n + "X" (unmatchable).
# A backtracking engine must try every split of the a-run into (a+) chunks
# (2^n search-tree nodes); a Thompson NFA simulator only ever keeps a set of
# active states per input character (linear in n * pattern size).

def backtrack_steps(subject):            # Perl/PCRE-style engine
    n = 0
    while n < len(subject) and subject[n] == "a":
        n += 1
    steps, stack = 0, [0]                # stack = positions after chunk ends
    while stack:
        i = stack.pop()
        steps += 1
        if i == len(subject):            # $ anchor holds -> match
            return steps, True
        if i < n:                        # chunks may only cover 'a' chars
            stack.extend(range(n, i, -1))   # greedy: longest chunk first
    return steps, False

class State:                             # epsilon-NFA node
    __slots__ = ("eps", "char", "out")
    def __init__(self):
        self.eps, self.char, self.out = [], None, None

def thompson(ast):                       # Thompson construction from AST
    states = []
    def new():
        s = State()
        states.append(s)
        return s
    def build(nd):
        kind = nd[0]
        if kind == "char":
            s = new()
            s.char, s.out = nd[1], new()
            return s, s.out
        if kind == "cat":
            a, b = build(nd[1]), build(nd[2])
            a[1].eps.append(b[0])
            return a[0], b[1]
        if kind == "plus":               # e+ == e e*
            s1, f1 = build(nd[1])
            s, f = new(), new()
            s.eps += [s1, f]             # enter e, or skip it
            f1.eps += [f, s1]            # exit, or loop back into e
            return s, f
        raise ValueError(kind)
    start, accept = build(ast)
    return start, accept

def nfa_steps(subject):                  # Thompson NFA simulation
    start, accept = thompson(("plus", ("plus", ("char", "a"))))
    def closure(seeds):
        seen, work = set(seeds), list(seeds)
        while work:
            s = work.pop()
            for t in s.eps:
                if t not in seen:
                    seen.add(t)
                    work.append(t)
        return seen
    current = closure([start])
    visits = len(current)
    for ch in subject:
        nxt = [s.out for s in current if s.char == ch]
        if not nxt:
            return visits, False
        current = closure(nxt)
        visits += len(current)
    return visits, accept in current

if __name__ == "__main__":
    print("pattern ^(a+)+$  vs  subject 'a'*n + 'X'  (no match possible)")
    print(f"{'n':>3} {'backtrack steps':>16} {'NFA state visits':>17} {'ratio':>12}")
    for n in (10, 15, 20, 25):
        subj = "a" * n + "X"
        b, m1 = backtrack_steps(subj)
        v, m2 = nfa_steps(subj)
        assert not m1 and not m2, "subject must NOT match"
        print(f"{n:>3} {b:>16,} {v:>17,} {b / v:>11,.0f}x")
    print()
    print("backtrack steps = 2^n exactly: one search-tree node per chunk-split")
    print("prefix. PCRE2's default MATCH_LIMIT is 10,000,000 steps, so real")
    print("PCRE2 aborts (MATCH_LIMIT error) on the n=25 input instead of hanging.")
```

Real output of the run above (CPython 3, executed in full):

```text
pattern ^(a+)+$  vs  subject 'a'*n + 'X'  (no match possible)
  n  backtrack steps  NFA state visits        ratio
 10            1,024                55          19x
 15           32,768                80         410x
 20        1,048,576               105       9,986x
 25       33,554,432               130     258,111x

backtrack steps = 2^n exactly: one search-tree node per chunk-split
prefix. PCRE2's default MATCH_LIMIT is 10,000,000 steps, so real
PCRE2 aborts (MATCH_LIMIT error) on the n=25 input instead of hanging.
```

Read the two columns as the two theses of this page: the backtracker's cost doubles with every extra character of hostile input, while the simulator's grows by 25 visits per 5 characters - and note that the NFA column counts *total work across the whole input*, not per character. Real PCRE2 would trip its 10,000,000-step fuse between `n = 23` and `n = 24`; an engine without a fuse (JavaScript's `RegExp`, Python's `re`) just hangs the process.

## Field notes

- The ReDoS shape to memorize: nested quantifiers over **overlapping** alternatives `(a|a?)+`, `(a+)+`, `(.*)*\.`, placed in front of a match that ultimately fails near the end of a long input.
- The fix ladder, in order of preference: collapse the nested quantifier (`(a+)+` is just `a+`), add anchors, use atomic groups/possessive quantifiers, and as a last resort add a step limit - but only engines with a linear-time guarantee (RE2 lineage) make the last line unnecessary.
- "Why can't DFAs do captures?" - a DFA state is a set of NFA states and cannot carry per-path history; the Pike VM restores history by giving every live thread its own slots.
- Why lookaround is dropped by RE2 and Hyperscan rather than "optimized": it is an assertion over unbounded lookahead, and admitting it forfeits the linear-time contract the rest of the engine is built to keep.
- Engine choice is workload-shaped: trusted patterns on short strings - PCRE2's feature set is fine; untrusted input in a request path - RE2 lineage; many patterns over streams - Hyperscan.

## References

1. Russ Cox, "Implementing Regular Expressions" series (verified: https://swtch.com/~rsc/regexp/ ; Part 1 "Regular Expression Matching Can Be Simple And Fast" at https://swtch.com/~rsc/regexp/regexp1.html ; Part 2 "Regular Expression Matching: the Virtual Machine Approach" at https://swtch.com/~rsc/regexp/regexp2.html ; Part 3 "Regular Expression Matching in the Wild" at https://swtch.com/~rsc/regexp/regexp3.html )
2. RE2 repository and README (linear-time guarantee, memory budget, unsupported-syntax list): https://github.com/google/re2 and https://github.com/google/re2/wiki/Syntax
3. Hyperscan repository, Intel: https://github.com/intel/hyperscan (engine sources incl. `src/nfa/shufti.c`, `src/nfa/truffle.c`, `src/fdr/teddy.c`, `src/rose/`)
4. Hyperscan Developer Reference (pattern support, engine concepts, streaming mode): https://intel.github.io/hyperscan/dev-reference/
5. PCRE2 documentation (matching algorithm, `MATCH_LIMIT`, atomic groups, possessive quantifiers): https://pcre2project.github.io/pcre2/
