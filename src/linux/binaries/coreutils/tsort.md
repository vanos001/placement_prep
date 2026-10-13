# tsort — Topological sort of a directed graph

## Overview

`tsort` reads a list of directed edges (whitespace-separated pairs: "A B" meaning A must come before B) and prints the nodes in a topological order — a sequence where every node appears before all nodes it points to. It is the smallest dependency-resolution tool in Unix: no options, no flags beyond the trivial, just "here are constraints, give me a valid order".

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/tsort`. It has been in Unix since the Seventh Edition era, where its first great job was feeding `lorder`: listing object-file dependencies so the single-pass linkers of the day received symbols in an order that resolved in one sweep. Build systems and package managers internalized the same algorithm decades later — `make`'s dependency graph, `dpkg`/`rpm` ordering, `maven`/`bazel` build plans — and `tsort` remains the shell-native way to answer "what order?" from any pair list. POSIX covers `tsort` (XSI), so it is dependable in portable scripts.

Reach for `tsort` whenever a dependency relation lives in shell-reachable data: ordering package installs, sequencing migration scripts, planning task execution, generating deterministic build orders, or teaching/verifying what a DAG is. It is often confused with `sort` (lexical ordering of lines — unrelated), with `sort -k1,1 -k2,2` on edge lists (also unrelated), and with graph tools like `dot`/Graphviz (which *draw* graphs; `tsort` *orders* them).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/tsort` |
| First appeared / lineage | Seventh Edition AT&T UNIX; classic companion of `lorder` for linker ordering |
| Standards | POSIX (XSI) |

## Synopsis

```
tsort [FILE]
```

```bash
tsort edges.txt                  # topologically order pairs listed in edges.txt
command | tsort                  # order pairs from a pipeline
tsort                            # order pairs from standard input
```

One form, zero options. Input is a whitespace-separated sequence of *pairs* of strings; each pair `A B` is an edge "A precedes B". Nodes are arbitrary non-whitespace strings.

## How It Works

### From edges to an order

A topological sort exists **if and only if** the graph is a DAG — a directed acyclic graph. `tsort` builds the adjacency list, then repeatedly emits nodes with no unemitted predecessors (GNU's variant outputs them in a way influenced by pair order; different implementations may produce different — equally valid — orders):

```
edges:              build order:
  gcc  binutils      ┌──────────────────────────────────────────┐
  binutils libc      │  no preds: gcc ──► emit                  │
  libc  base-files   │  no preds: binutils, libc ──► emit either│
                     │  no preds: base-files ──► emit last      │
                     └──────────────────────────────────────────┘
tsort output: gcc, binutils, libc, base-files   (one valid order of several)
```

Two properties surprise newcomers:

1. **The order is not unique.** Any order respecting the edges is correct; which one you get depends on the implementation and input order. Do not build logic that depends on a *specific* valid order.
2. **Duplicate pairs are accepted** and collapsed — `a b` appearing twice is not an error (verified: GNU tsort exits 0).

Ground truth from the shell:

```bash
$ printf 'a b\nb c\nc d\n' | tsort
a
b
c
d
```

### Cycles are fatal

If the constraints contain a loop, no valid order exists and `tsort` reports every node on the loop:

```bash
$ printf 'a b\nb c\nc a\n' | tsort
tsort: -: input contains a loop:
tsort: a
tsort: b
tsort: c
$ echo $?
1
```

The error names *all* nodes in the cycle — useful diagnostically: in a real dependency set, a cycle is a bug in the data, and the message is the bug report. Self-loops (`a a`) are likewise a loop.

### The classic pipeline use

`tsort` shines when edges come from other tools. A worked Makefile-like example — derive a build order from a declarative dependency list:

```bash
# deps.txt: "target prerequisite" edges, like a flattened Makefile
$ cat deps.txt
app main.o
app utils.o
main.o main.c
utils.o utils.c
$ tsort deps.txt
app
utils.o
main.o
utils.c
main.c
```

Every edge is respected (each target precedes its prerequisites), but GNU's order often *looks reversed* relative to intuition — the algorithm's worklist discipline picks a valid order that leans late. Two idiomatic fixes:

```bash
# Write edges prerequisite-first and the output reads build-order-first
printf 'main.c main.o\nutils.c utils.o\nmain.o app\nutils.o app\n' | tsort
# main.c, utils.c, main.o, utils.o, app
```

```bash
# Or reverse the output of target-first edges — reversing a valid order of
# the "target prereq" graph yields a valid order of the "prereq target" graph
tsort deps.txt | tac
```

From a real Makefile fragment, flatten `target: prereq...` lines into one edge per line, then order:

```bash
# Turn "target: prereq1 prereq2 ..." lines into per-prerequisite edges, then order
awk -F': ' 'NF==2 {n=split($2,a," "); for(i=1;i<=n;i++) print $1, a[i]}' Makefile \
  | tsort
```

Package-ordering works the same way: emit `pkg dependency` pairs (e.g. from a package list) and `tsort` gives an install order; migration scripts (`001-x`, `002-y` with cross-dependencies) sequence the same way.

### Algorithmic character

GNU tsort is linear-time in edges+nodes (Kahn-style worklist over predecessor counts), trivially fast for millions of edges. Memory is O(graph). There is no heuristics layer: no priority, no "longest path", no stability guarantee — if you need a *preferred* order among valid ones, encode it as additional edges, or post-process with a weighted scheduler.

## Options That Matter

| Option | Effect |
|---|---|
| (none) | `tsort` takes no options beyond `--help`/`--version`; the single argument is an input file, default stdin |

This is the entire interface — a feature worth stating in interviews: the tool does one thing, on one input format, with one exit code pair.

## Usage Patterns

```bash
# Order package installation from a "pkg dependency" list
tsort packages.edges
```

```bash
# Sequence database migration scripts declared as dependencies
printf '002-indexes 001-tables\n003-seed 002-indexes\n' | tsort
```

```bash
# Feed a build plan from a flattened Makefile fragment
awk -F': ' 'NF==2 {print $1, $2}' rules.mk | tr ' ' '\n' | paste -d' ' - - | tsort
```

```bash
# Validate a dependency dataset: a clean exit means the graph is a DAG
tsort deps.txt > /dev/null && echo 'graph is acyclic'
```

```bash
# Find which nodes sit on a dependency cycle (error output names them)
tsort deps.txt 2>&1 >/dev/null | tail -n +2
```

```bash
# Order tasks for parallel execution: same-level tasks are independent
printf 'test compile\ndeploy test\n' | tsort
```

```bash
# Reverse a relation (B depends on A → emit A before B) without editing data
awk '{print $2, $1}' depends.txt | tsort
```

```bash
# Sanity-check before handing the order to a scheduler
plan=$(tsort deps.txt) && xargs -n1 run_task <<< "$plan"
```

```bash
# lorder-style usage: order object files for a linker that resolves in one pass
lorder *.o | tsort
```

## Nuances and Gotchas

- **"Input contains a loop" is usually your data's bug.** Real dependency sets grow cycles via carelessness (A's build needs B's headers and vice versa). The fix is refactoring the dependency, not coaxing the tool.
- **Order is valid, not canonical — and may look reversed.** GNU tsort's worklist discipline often emits targets before the things they depend on appear intuitive (yet every constraint holds; see the worked example above). Never diff tsort outputs between systems to compare datasets, and don't assume "prerequisites print first".
- **Tokens are consumed pairwise across the whole input.** `tsort` reads whitespace-separated tokens two at a time, ignoring line boundaries: `printf 'a b\nc d\n'` and `printf 'a b c d\n'` are the same four edges. Consequence: a stray odd token anywhere triggers the odd-token error, and misaligned lines silently pair the wrong nodes. Emit exactly one pair per line.
- **Duplicate pairs are collapsed, silently.** Harmless in dependency data, but it also means duplicated edges cannot express multiplicity — tsort is not a flow tool.
- **Isolated nodes need an anchor.** A node mentioned in no pair never appears in the input and thus never in the output; a self-pair (`node node`) is the idiomatic anchor — GNU tsort treats it as trivial and exits 0 (verified: `printf 'a a\n' | tsort` prints `a`).
- **Not a scheduler.** tsort gives an order, not parallel waves or critical paths. Level-based parallelism (what `make -j` computes) needs level annotation — derive it by repeated "emit all no-predecessor nodes" passes if you need depth.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | A topological order was produced |
| 1 | Input contains a loop (message lists the cycle's nodes), or an input file could not be read |

There are no warning or strictness codes: the contract is binary — DAG or error.

## Related Commands

- [`uniq`](./uniq.md) — cleanup of duplicated pair lines feeding `tsort` (duplicates are collapsed anyway).
- [`wc`](./wc.md) — pair-list validation helper (`wc -l` for edge counts, and odd-token detection via byte counts).
- [`printenv`](./printenv.md) — fellow zero-option, single-purpose coreutils tool; a study in Unix interface minimalism.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: What is a topological sort, and what input property guarantees one exists?

An ordering of a graph's nodes such that every directed edge `A → B` places A before B. It exists exactly when the graph is acyclic (a DAG); any cycle makes it impossible because the cycle's members would each need to precede the others. `tsort` proves the property constructively: exit 0 plus output means DAG, exit 1 with a node list means it found the cycle. Kahn's algorithm and DFS-based approaches both run in linear time.

### Q: Why did linkers need tsort via lorder historically, and why don't we anymore?

Single-pass linkers resolved symbols in input order: if object A referenced a symbol defined in B, B had to appear *after* A in the link line. `lorder` derived the reference pairs from object files and `tsort` produced the safe order. Modern linkers resolve iteratively or index archives, so ordering stopped mattering — but the pipeline (`lorder *.o | tsort`) survives as the textbook example of composing small tools over derived data.

### Q: Your package installer receives "package depends-on package" data and must install in order. Sketch the shell design and its failure mode.

Emit one `pkg dependency` edge per line (flattening multi-dependency lines), run `tsort`, install in the printed order. The failure mode is cycles: packages that (directly or transitively) depend on each other — `tsort` exits 1 and names the loop, which becomes the operator's bug report. Real installers add policy layers (priorities, version pins) on top of the topological layer; `tsort` is the ordering kernel, not the whole scheduler.

### Q: How would you get a "parallel-safe" grouping from tsort's output?

tsort gives a sequence, not waves. Two options: derive levels yourself — repeatedly emit all nodes with no unemitted predecessors (that's what `make -j` computes per level) — or encode your preference into the graph: adding edges serializes what you want serialized, letting tsort keep genuinely independent tasks in any order. The interview point: a topological order is a *constraint solution*; parallelism policy is extra structure you add or extract.

### Q: Input has duplicate edges and a node that appears only in the second position. How does tsort treat each?

Duplicate pairs are collapsed — the graph is a set of edges, so `a b` twice is one edge. A node appearing only as a target is fine: it's in the graph as a successor and will be emitted once its predecessors are emitted. The reverse case — a node appearing in *no* pair — is the one that vanishes; anchor it with a self-pair if it must appear in the output.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tsort.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — tsort](https://pubs.opengroup.org/onlinepubs/9699919799/)
