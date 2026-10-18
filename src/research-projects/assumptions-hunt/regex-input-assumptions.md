# Regex Input Assumptions: What "Just Use a Regex" Silently Promises

## Overview

Regular expressions are the most widely deployed DSL in software, and the assumptions people make about them are rarely about the engine — they are about the *input*. This chapter audits four of those: that a regex applied to user input is bounded by the input's nominal size, that a matching search always terminates, that the pattern means what its author reads it as, and that Unicode classes like `\w` and `\d` match characters the way the author means them. Each fails silently and then suddenly: a pattern that ran fine for two years meets one 200-character body and consumes a CPU core for an hour; a pattern ported between Python, JavaScript, and Go changes meaning without a syntax error; a validation that "checks for letters" accepts or rejects differently per runtime.

The engine-internal mechanics — how NFAs, DFAs, and backtracking automata execute patterns — are the follow-up tree's regex-engine chapter; this chapter stays on the *caller's* side of the boundary: what you may assume when you point a pattern at data you do not control. The distinction matters for interviews because the famous incident here — Cloudflare's July 2, 2019 global outage, triggered by one CPU-exhausting regex in a WAF rule and documented in the failure casebook — is usually retold as an engine story, when its operational lesson is an input story: the pattern had processed billions of benign requests before one body walked its pathological path. The failure mode is therefore statistical, not immediate — which is why linting and fuzzing must be automated rather than performed by hope.

## Assumption 1: "Regex Over User Input Is Bounded"

### The taught rule

The input is at most a few kilobytes (a form field, a header value, a filename), so even an inefficient pattern runs in microseconds; there is nothing to bound.

### How it fails

The cost of a backtracking regex is not a function of input size alone but of input size *times* the number of ways the pattern can partition the input — the backtracking search space. The canonical pathological shapes are innocent: `(a+)+b` against a string of `a`s; `(a|a)*$` with alternation that matches the same text two ways; `.*.*=.*.*` where multiple greedy wildcards can each split the input anywhere. On those shapes a 30-character input can force millions of steps, and 60 characters can force more than a CPU can execute in the age of the universe — exponential in the length of the ambiguity run, not linear. "Bounded input" therefore bounds nothing: the attacker does not need size, only *ambiguity*, and ambiguity needs a few dozen characters.

The assumption also fails on the quiet side: unbounded quantifiers over genuinely large inputs (`.*` against a 50 MB request body) are not pathological but still scan whole-buffer, so a "small validation" becomes a memory and latency cost multiplied by traffic. And the boundary the author measured (the field's UI limit) is not the boundary the regex sees (the raw HTTP body, the header before trimming, the decoded form) — every layer between the UI validation and the regex invocation is a place where the assumed bound silently disappears, the same gap the sibling chapter on input constraints audits for length and format checks generally.

### Failure scenario

A comment form validates with a "strip markup" pipeline whose last rule is a cleanup regex written to catch stray tags: `/(\s*\w+\s*)+.*<\s*\/\s*(\w+)\s*>/` — contrived, but shaped exactly like the real offenders (a nested quantifier over a repeated group followed by more matching). Inputs of up to 80 characters from real users cost microseconds. One request — a paste artifact containing 90 repeated tokens — enters the catastrophic regime: the backtracking search doubles per token, the worker's CPU pinwheels at 100%, the request queue behind it fills, and autoscaling adds workers that receive the *same queued body* and pinwheel too. What saved the fleet was the proxy timeout — which then produced the second incident: clients retrying, re-queuing the poison input. The fix was not tuning the regex but changing the execution model for that pipeline (a linear-time engine, see Assumption 2) plus a hard length bound at the actual regex boundary.

### Detection heuristic and what to assume instead

Detection: fuzz every user-facing pattern with repetition-heavy inputs (`aaaa...b`, `aXaXaX...`, `((((((`); run the suite under a timeout — any pattern whose match time grows non-linearly between the 20-character and 40-character fuzz cases is flagged. Static linters (RE2's parser, ESLint's `no-super-regex`-class rules, safe-regex analyzers) catch the nested-quantifier shape before runtime. Corrected statement: *bound the input at the regex's own boundary and assume the cost is proportional to size × ambiguity; audit patterns for nested quantifiers over the same text and prefer linear-time engines for anything touched by untrusted data.*

## Assumption 2: "A Matching Pattern Always Terminates"

### The taught rule

A regex either matches or does not; the call returns; there is no "runs forever" case to design for.

### How it fails

Termination is an engine property, not a regex property — the same pattern string can be guaranteed-terminating in one engine and unbounded in another. Backtracking engines (PCRE, Python `re`, JavaScript's built-in RegExp, Java's `Pattern`, Oniguruma) explore the exponential search space of Assumption 1, which means "terminate" degenerates to "terminate within a number of steps nobody has waited for" — and most offer no timeout parameter at all — Python's `re` and JavaScript's RegExp famously have none — so the mitigation must come from elsewhere: worker processes with kill switches, or never using those engines on untrusted input. Linear-time engines (RE2, the Go and Rust standard regex packages, derived from the same automata theory) guarantee termination in O(n·m), but pay for it in expressiveness: no backreferences, no lookaheads (in RE2's default mode) — so a codebase that "just switched the engine" discovers its patterns do not compile, and the temptation is to reintroduce a backtracking engine for those patterns, reinstalling the unbounded case exactly where the input is hostile.

The subtle variant is *bounded-but-huge*: a pattern that terminates with catastrophic constants — a lookbehind over a 10 MB subject, or an unanchored scan that walks the entire buffer for every candidate position — is not infinite, but a timeout of 100 ms still fires. Termination guarantees say nothing about deadline guarantees; a search that must finish in 5 ms needs a linear engine plus a length bound, not a proof of termination.

### Failure scenario

An API gateway runs request-body validation with a backtracking engine; after a ReDoS near-miss, the team rewrites the hot validation in a linear engine — except one rule that needs a backreference ("the closing tag must match the opening tag"), which the linear engine rejects. The team routes just that rule to the old backtracking engine, input-tagged as "trusted internal traffic." Six months later an internal service starts forwarding user-derived HTML through that path; the "trusted" tag is enforced by a header that any internal caller can set, and one request body with 40 nested spans pins a gateway worker for 40 minutes. The lesson is structural: expressiveness holes become unbounded-execution holes, and the boundary of "trusted" moved without the engine assignment being revisited.

### Detection heuristic and what to assume instead

Detection: inventory every pattern with the engine it runs on and whether its input crosses a trust boundary; any backtracking engine on untrusted input is a finding by default. Set an execution deadline at the call site where the engine allows none, and test it. Corrected statement: *termination is a property of the engine-input pair, not of the pattern string; for untrusted input use a linear-time engine or an enforced deadline, and treat every "trusted" tag guarding a backtracking engine as a security boundary that must be named, owned, and tested.*

## Assumption 3: "The Pattern Means What I Read It As"

### The taught rule

Regex syntax is regex syntax: `^` means start, `$` means end, `.` means any character, and a pattern ported between languages behaves identically.

### How it fails

Regex dialects differ in documented, opinion-splitting ways, and the differences do not raise porting errors. Anchors: in most engines `$` matches at end of string, but in several (and under multiline variants) it also matches *before a trailing newline* — so `/^abc$/` in multiline-ish modes accepts `"abc\n"`, and a validator built on it admits a payload with a newline suffix that downstream parsers then see differently. Flags: JavaScript's `g` flag makes the pattern object *stateful* (the `lastIndex` cursor advances across calls), so a shared, stateful regex under concurrency validates some inputs wrong non-deterministically; Python's `re.MULTILINE` changes both anchors; Go's RE2 lacks lookaheads and backreferences outright. Character classes: `.` excludes newline by default everywhere, but "any character" writers forget it; `\s` is ASCII whitespace in one engine and Unicode whitespace in another (Assumption 4's territory at the boundary). Possessive quantifiers and atomic groups exist in PCRE and Java but not Python or JavaScript — a pattern copied for safety silently loses its anti-backtracking protection when ported into a language that lacks them. Even "empty match" semantics (can `*` match zero characters at the same position repeatedly?) differ per engine.

The common mechanism is that the pattern's meaning is a property of the *pattern-engine-flag triple*, and all three parts of the triple are usually implicit: the engine is whatever the file imports, the flags are whatever was on the literal when it was copied.

### Failure scenario

A security filter written in PCRE-style syntax forbids `^/api/(v1|v2)/admin$` paths. It is ported to a Python service with `re.match()` and no flags — and `re.match` anchors at the start but the pattern's `$` still permits a trailing newline, so the path `/api/v1/admin\n` passes the filter; the router framework, which strips or normalizes the newline differently, forwards it to the admin controller. The vulnerability class is a *parser differential* — two components disagreeing about the same string — and the fix is not another regex but eliminating the ambiguity: normalize and validate the path once, compare against an allowlist, and use `\A`/`\z`-style true-string anchors, with a test asserting the newline case.

### Detection heuristic and what to assume instead

Detection: port every pattern's test suite across engines and diff the accepted set — especially with trailing-newline, unicode-flag, and repeated-call (stateful `g`) cases; grep for shared regex objects under the `g` flag in concurrent code. Corrected statement: *a pattern's meaning is pinned by its engine and flags; record both next to every pattern (as tests), use strict anchors and explicit flags rather than inherited defaults, and treat a cross-language port of a regex like a port of any other parser — with a differential test, not a visual diff.*

## Assumption 4: "Unicode Classes Match Characters"

### The taught rule

`\w` matches word characters, `\d` matches digits, `\b` is a word boundary, and `.` matches a character — the classes abstract over exactly what a human means by those words.

### How it fails

Each class is a treaty between the engine and Unicode, negotiated per flag. `\d` is ASCII-only in JavaScript (without the `u` flag), Go, and PCRE's default mode, but matches all Unicode decimal digits (`Nd` — Arabic-Indic ٣, Devanagari ३) in Python 3 strings and in PCRE with the Unicode-property option. The security-relevant direction: a validation "digits only" written in Python accepts `٣` and then fails a downstream system that parses ASCII digits — or worse, an `int()` conversion that behaves differently. `\w` in Python matches letters of every script plus underscore and digits, so `\w+` "word" validation accepts `日本語`; the same pattern in Go rejects it. `\b` is defined in terms of `\w`, so it inherits the divergence and moves per script. The `.`-versus-character confusion deepens with Unicode: a JavaScript regex without the `u` flag iterates UTF-16 *code units*, so `.` matches half of an emoji (a lone surrogate) and a one-emoji length check returns 2; with the `u` flag it matches a code point — but a grapheme cluster (a family emoji with ZWJ sequences) is still several code points, so even `u`-flagged patterns do not match "what the user sees as one character." Unicode property classes (`\p{Script=Greek}`, `\p{Lu}`) are the *precise* tool, and they are exactly the ones with the most uneven engine support — Python has them, Go does not, JavaScript gates them behind `u`.

### Failure scenario

A username policy is enforced as `/^[\w-]{3,20}$/` in a Python microservice ("word characters, reasonable"). Turkish, Greek, and Japanese users register names in their own scripts — accepted, stored, displayed. Three years later, a Go-based enforcement service re-implements the policy with Go's `\w` (ASCII-only) as part of a login hardening: every non-ASCII username fails validation at login. The incident is not the code — both implementations are "correct" — it is that the *policy* was defined by an engine behavior instead of by a character-class decision. The fix writes the policy in Unicode terms (property classes or an explicit script allowlist), adds it as a shared test-vector set, and pins per-service engines and flags so the classes cannot drift again.

### Detection heuristic and what to assume instead

Detection: run one cross-engine test fixture for every class-based pattern: `٣`, `٣`→`int()`, `日本語`, `é`, and a family emoji (with and without the `u`/UNICODE flag) — then diff which inputs each engine accepts. Any divergence on a validation path is a policy bug, not an engine bug. Corrected statement: *`\w`, `\d`, `\b`, and `.` are engine-and-flag-parameterized approximations; policies must be stated in Unicode property terms (or explicit script/ASCII allowlists), tested as shared fixtures, and code-point versus grapheme distance must be chosen deliberately wherever lengths or positions matter.*

## Interview Questions

1. **How can 30 characters of input consume a CPU core for minutes in a regex?** Nested or ambiguous quantifiers create an exponential backtracking search space: `(a+)+b` against `aaaaaaaaaaaaaaaaaaaaaaaaaaaab` forces the engine to re-explore every partition of the run of `a`s. The bound is size × ambiguity, not size.
2. **Your language's regex has no timeout parameter. What are your options for untrusted input?** Move to a linear-time engine (RE2-family), isolate the call in a worker with a kill switch, bound the input at the regex boundary, or statically reject dangerous pattern shapes. "The pattern looks fine" is not an option.
3. **Why is porting a regex between languages riskier than porting it between files?** The meaning is the pattern-engine-flag triple: anchors (`$` and trailing newlines), stateful `g` flags, missing possessive quantifiers, and ASCII-versus-Unicode classes all diverge silently. A differential test suite is required, not a visual check.
4. **What does `\d` match in Python versus JavaScript, and why is the difference a security issue?** Python: all Unicode `Nd` digits; JavaScript (without `u`): ASCII only. A validation accepting ٣ in one layer and rejecting it in another creates parser differentials — the same string means different things to adjacent components.
5. **Cloudflare's 2019 outage is retold as an engine story. What is the input-side lesson?** One pattern, billions of benign requests, then one body hit the pathological shape — the failure was statistical over inputs, not deterministic over code. That is why pattern linting and fuzzing must be automated: no reviewer can simulate the search space mentally.

## Key Takeaways

- Regex cost scales with input size × ambiguity; nested quantifiers turn tens of characters into exponential work, so "bounded input" bounds nothing.
- Termination is an engine-input property: backtracking engines (Python, JavaScript, PCRE) have no built-in timeouts; linear engines (RE2 family) guarantee O(n·m) but drop backreferences — the expressiveness hole becomes an execution-policy hole.
- A pattern's meaning is the pattern-engine-flag triple: anchors, flags, and class semantics diverge per dialect, and the divergences never raise porting errors.
- `\w`, `\d`, `\b`, and `.` are flag-parameterized approximations of human words; validation policies must be written in Unicode property terms and tested as shared cross-engine fixtures.
- The Cloudflare 2019 outage is the family's proof that regex risk is statistical over inputs — automate pattern auditing (linting, fuzzing, differential tests) rather than relying on review.

## Cross-References

- [Regex engines](../followup-tree/regex-engines.md) — the internals side of the boundary: NFA/DFA execution, backtracking, and linear-time automata (this chapter audits the *input* assumptions, that one the *engine* mechanics).
- [Cloudflare regex outage, July 2019](../failure-casebook/cloudflare-regex-2019.md) — the casebook entry with the timeline, the culprit pattern, and the primary sources.
- [Input constraints](input-constraints.md) — the general family: length bounds, format checks, and the UI-to-boundary gap behind Assumption 1.
- [Regex engine internals](../../compilers/advanced/regex-engine-internals.md) — the book chapter on how automata implement the patterns whose inputs this chapter audits.
- [Regex in the shell](../../linux/shell/regex.md) — POSIX BRE/ERE dialects, the oldest split in Assumption 3's family.
- [RE2](https://github.com/google/re2) — the linear-time engine's documentation, including its stated feature trade-offs (verified); OWASP's ReDoS entry — [verified](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS). Russ Cox's regular-expression article series cited by title.
