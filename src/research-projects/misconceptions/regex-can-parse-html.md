# "A regex can parse HTML"

## Overview

This page audits the claim that reappears in every scraping project and
half of all input-validation debates: a regular expression is enough to
parse HTML — or XML, or any nested markup. The claim sits at the
intersection of theory and tooling, which is why it survives so well: on
the theory side, it is provably false, because the language of
arbitrarily nested tags is not a regular language and no regex can match
it at unbounded depth; on the tooling side, it is pragmatically true
daily, because real scrapers extract flat fields with regexes and ship
for years. The resolution is to state what each side is actually doing.
Matching a *token* — one `<img>` tag, one attribute value — is lexical
scanning, which regular expressions are built for. *Parsing* a document —
recovering a tree, balancing open and close tags, applying error
recovery — requires memory proportional to nesting depth, which is
exactly what finite automata do not have. This page states the claim
fairly, walks the depth-bound disproof that ends the theory argument,
and marks the boundary where the pragmatic kernel legitimately lives.

## The Claim, Stated Fairly

The strongest common form is: "For our page, a regex is simpler and
faster than dragging in a parser; we just need the prices out of this
known markup." Stated this way, the claim is not a strawman. It is the
correct decision for a large class of real tasks: extracting a fixed
field from a stable, machine-generated page; validating that a
configuration fragment contains the expected single element; scraping a
flat table. It also has famous support in folklore — the "You can't
parse [X]HTML with regex" answer is one of the most quoted strings on
Stack Overflow, and just as many threads open with "everyone says that,
but my regex works".

The kernel deserves its fairness because the regex usually *does* work:
generator output is flat, stable, and known, and the regex is inspected
against the actual bytes. The failure arrives when the input stops being
the generated page — a human edits it, a variant ships, an attacker
crafts it — and the pattern meets nesting one level deeper than it
handles, or content that makes a nested quantifier explode.

## Verdict

**False.** The claim is contradicted outright: parsing arbitrary HTML
requires recognizing arbitrarily nested structure, and the language of
balanced nesting is context-free, not regular — a finite automaton has a
fixed number of states and cannot count unbounded depth, so any regex
handles exactly some maximum nesting level and fails on deeper input.
HTML adds a second, independent refutation: real-world HTML is not
well-formed at all, and "parsing it" means implementing the error
recovery rules the WHATWG HTML standard specifies — adoption agency
algorithms, implied tags, misnested-element reconstruction — which no
regular expression encodes. What remains true is a narrower statement
about tokens: regular expressions are the right tool for lexical
extraction from known, flat, trusted markup, and the claim becomes
dangerous when that kernel is promoted to a parsing guarantee.

## Why People Believe It

Three forces keep this claim alive. First, the kernel dominates
experience: most pages a developer regexes are flat, and the pattern is
written against the actual bytes in front of them. A tool that works on
every input tried so far is indistinguishable from a correct parser
until depth or error recovery arrives.

Second, the theory is felt but misassigned. Developers know regexes are
"powerful" — backreferences, lookarounds, Unicode classes — and the
feature list reads like it should cover structure. But every feature on
that list keeps the machine finite: none of it allocates memory
proportional to input depth. The intuition "regexes are powerful
therefore they can nest" fails exactly at the property that nesting
requires — an unbounded counter.

Third, the refutation is usually stated as a slogan ("you can't parse
HTML with regex") rather than a mechanism, and slogans invite exceptions.
Each exception then looks like a win for the claim ("look, this pattern
handles my whole page"), when in fact every such pattern demonstrates
the real theorem: a regex handles precisely the nesting depth someone
wrote into it, and no more.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Regex can parse HTML" | Regular expressions recognize regular languages; balanced tag nesting is context-free, so any regex handles a fixed maximum depth and fails beyond it |
| "It works on our pages" | It works on inputs at or below the depth the pattern encodes, from the generator the pattern was written against — a token-extraction guarantee, not a parse |
| "The pattern is clever enough" | No amount of cleverness removes the depth bound; each additional nesting level requires editing the pattern, forever |
| "HTML is well-formed anyway" | Browsers do not assume it: the WHATWG parsing algorithm specifies error recovery for misnesting, implied tags, and reparenting that no regex encodes |
| "Parsers are heavyweight" | The regex path pays its own unbounded cost: nested quantifiers on crafted input give exponential backtracking, the catastrophic case that has caused production outages |
| "What regexes are for here" | Lexical scanning: one tag, one attribute, one flat field — from trusted or tolerant sources, with a parser doing the structure |

The correct sentence: "A regex matches tokens, not trees: it can find
the `<img>` tags and attribute values in known markup, and it cannot,
at any level of cleverness, balance arbitrarily nested tags — that
requires memory proportional to depth, which finite automata do not
have, and real HTML parsing additionally requires the error-recovery
algorithm the HTML standard specifies."

## Where It Breaks

**The depth-bound disproof, run live.** Take the simplest nesting
problem — balanced brackets, the tag-nesting shape with less syntax — and
a regex that handles two levels:

```python
import re
r2 = re.compile(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]")
print(bool(r2.fullmatch("[a[b]c]")))      # True  - depth 2 handled
print(bool(r2.fullmatch("[a[b[c]d]e]")))  # False - depth 3 defeats it
```

The pattern is not buggy; it is *finished*. Handling depth 3 means
adding one more alternation level, depth 4 another — for every depth, a
new edit, forever. This is the pumping-lemma fact made concrete: the
language of balanced brackets (hence balanced tags) is not regular, so
no single regex recognizes it. Real documents do not carry a depth
bound — a page with fifteen nested `div`s is ordinary — so the
"parser" the team shipped is a parser for depth k, where k is whatever
the author tolerated before giving up.

**The error-recovery gap is independent of depth.** Even at shallow
nesting, real HTML parsing means deciding what `<b><p>x</b>y` *means* —
which element contains `y`, how the stray `</b>` is handled — and the
WHATWG HTML standard answers that with explicit tree-construction and
adoption-agency rules that browsers implement identically so the web
renders the same everywhere. A regex has no way to express "reconstruct
the stack of open elements and reparent"; the question "does my regex
parse this page like Chrome does?" is therefore not hard but
type-mismatched. Two regex-based extractors disagree with each other and
with every browser on misnested input, which is why scraped fields
drift silently when markup shifts.

**The backtracking bomb is the same claim with a timer.** The nested
quantifier idiom that makes the depth-2 pattern above plausible —
`(a+)+$` is the canonical form — runs in time exponential in input
length on a backtracking engine: a crafted 30-character string defeats
the matcher with roughly 2^30-plus steps, hanging the thread that ran
it. This is not hypothetical: the 2019 Cloudflare outage was a single
regex with a pathological backtracking case consuming CPU until global
traffic failed. Linear-time engines (RE2-style automata) defuse the
blow-up by refusing the features that cause it — which is the same
boundary in a different costume: the power that looks like "parsing
ability" is backtracking, and backtracking is the bomb. (The engine
mechanics are the follow-up tree's territory; here the point is that
the claim's own tool pays for its apparent power with this failure
mode.)

**The kernel, stated as engineering.** None of this forbids regexes in
scraping or validation; it prices them. The legitimate uses: single-tag
lexical extraction (`<img\s+[^>]*src="([^"]+)"`) from markup you
control or can inspect; tolerant extraction where a missed variant
costs a retry, not a wrong number; log and config formats that are
genuinely flat. The disqualifying uses: anything where an unbalanced or
deeper input changes meaning (security checks on markup, "strip all
tags" sanitizers — the classic bypass is nesting the sanitizer never
sees), and anything feeding decisions on untrusted input. The boundary
question is one sentence: does correctness require knowing the *tree*,
or only a *token*? Regexes do tokens; the tree needs a real parser —
and for HTML, that parser is the standard algorithm, not a well-formed
XML parser either, because the web is not well-formed.

## Practical Implications

- Before writing the pattern, decide token versus tree: field
  extraction from known markup is a token job; anything that must
  balance, count, or reparent is a tree job for a real parser.
- For HTML and XML, use the platform parser (the WHATWG algorithm's
  browser implementations, or the language's HTML5-compliant library);
  for well-formed machine formats, use the XML or JSON parser.
- If a regex must touch markup from untrusted input, bound everything:
  explicit length limits, no nested quantifiers over overlapping
  classes, and a linear-time engine or a fuzzed timeout in front of it.
- Treat "my regex works on the current page" as a fixture result, not a
  specification: pin the generator version, and diff extracted output in
  CI when the upstream markup can change.
- For sanitization ("remove all tags"), regex is the known-wrong tool —
  parse, walk the tree, serialize; the bypass literature is a catalogue
  of nesting the pattern did not cover.
- Prefer linear-time engines or bounded-input guards for any pattern
  that runs on untrusted bytes: the same nesting power that tempts the
  "parser" regex is what the backtracking bomb rides on.

## Interview Questions

### Why exactly can't a regular expression match arbitrarily nested tags?

Regular expressions compile to finite automata, which have a fixed
number of states and no input-proportional memory. Recognizing balanced
nesting requires counting open elements up to arbitrary depth — a
counter of unbounded size — which is the definition of a
context-free (not regular) language. Any given regex encodes a maximum
depth it can handle; the demo pattern that matches depth 2 fails on
depth 3, and every repair is another edit with a new bound.

### A scraper's regex works on the target site today. What are the two most likely failure modes when it breaks?

Structure drift: the page gains one more nesting level or a variant the
pattern never encoded, and the match silently misses (or over-captures)
— the depth-bound failure. Resource failure: a nested-quantifier
pattern meets input that makes the backtracking engine explode,
hanging the request — the catastrophic-backtracking failure. Both are
resolved by moving structure to a parser and bounding the regex to
lexical tokens.

### Is "never parse HTML with regex" the correct rule?

No — the correct rule is "regexes match tokens, parsers build trees".
Extracting attribute values from known, trusted, flat markup is a
legitimate, stable use. The rule bites when correctness depends on
structure: balancing, sanitization, security decisions, or anything
where a deeper or misnested input changes meaning — there, the WHATWG
parsing algorithm (including its error recovery) is the tool, because
real HTML is not well-formed and browsers agree on the recovery, not on
regex behavior.

### What does the WHATWG HTML specification have to do with the claim?

Everything practical: "parsing HTML" means implementing its
tokenization and tree-construction algorithm, including the
error-recovery rules (implied tags, misnesting repair via the adoption
agency procedure) that make browsers render broken markup identically.
Those rules are imperative tree surgery that no regular expression can
express, so even a depth-bounded regex "parser" is not parsing HTML —
it is scanning a subset of well-formed HTML and hoping.

## Key Takeaways

- Regular languages cannot count unbounded depth: balanced nesting is
  context-free, so every regex handles a fixed maximum nesting level
  and fails beyond it — provably, not as a style opinion.
- Real HTML parsing is the WHATWG algorithm with error recovery; regex
  extractors disagree with browsers (and each other) on exactly the
  inputs where parsing matters.
- The kernel is tokens, not trees: single-tag and flat-field extraction
  from known markup is the legitimate, durable use.
- Nested quantifiers trade apparent parsing power for exponential
  backtracking — the same tool claim that caused production outages.
- The boundary question is one sentence: does correctness need the tree
  or a token? Trees need the parser; tokens are what regexes are for.

## Cross-References

- [Follow-up Tree: Regex Engines](../followup-tree/regex-engines.md) —
  backtracking versus automata, RE2-style linear time, and the engine
  mechanics behind the blow-up this claim's patterns invite.
- [Why-Not Handbook: Regex vs Parser](../why-not-handbook/regex-vs-parser.md)
  — the decision framework for when each tool wins, with the cost model
  this page's boundary question formalizes.
- [Assumptions Hunt: Regex Input Assumptions](../assumptions-hunt/regex-input-assumptions.md)
  — the hidden assumptions about what input a pattern will meet, the
  input-side twin of the depth-bound failure.
- [Failure Casebook: Cloudflare Regex Outage 2019](../failure-casebook/cloudflare-regex-2019.md)
  — the production instance of the backtracking bomb, one pattern, one
  global outage.
- [Practical Problems: Parsers](../../practical-problems/parsers.md) —
  the engineering of real parsers, the tool the claim's kernel says to
  reach for.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- WHATWG. *HTML Standard* — the parsing section defining tokenization,
  tree construction, and error recovery for real-world HTML.
  <https://html.spec.whatwg.org/>
- R. Cox. *Regular Expression Matching Can Be Simple And Fast (but is
  slow in Java, Perl, PHP, Python, Ruby,...)* — the automata-versus-
  backtracking analysis that explains where the depth-bound and the
  blow-up come from.
  <https://swtch.com/~rsc/regexp/regexp1.html>
