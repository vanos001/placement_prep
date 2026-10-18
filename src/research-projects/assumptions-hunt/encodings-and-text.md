# Text and Encoding Assumptions: What "It's Just a String" Silently Promises

## Overview

Strings are the data type every tutorial treats as solved and every production system treats as dangerous. The word "string" bundles together at least four distinct layers — bytes, code points, code units, and grapheme clusters — and most code that manipulates text is silently written against the wrong layer. The result is a family of bugs that never show up with ASCII test fixtures: truncated emoji, JavaScript lengths that disagree with human counting, macOS filenames that refuse to compare equal to themselves, Turkish text uppercased into different letters, and identifiers cut in half by a database column that counts bytes where the API counted characters.

This chapter audits the load-bearing text assumptions with the collection's five-step pattern: that a string is a sequence of characters, that one character is one byte is one grapheme, that truncation to N characters is safe, that uppercasing is trivial, and that UI validation is enough. The Unicode model is not exotic knowledge; it is the specification every modern runtime implements. The failing code is not the code that lacks a Unicode library — it is the code that *uses* one but assumes the library's layers coincide. Every layer split below is checkable against the Unicode Standard and the language references cited, and the corrected rules are short enough to apply in code review.

## Assumption 1: "A String Is a Sequence of Characters"

### The taught rule

A string is an array of characters; index it, count it, iterate it like any array.

### The hidden assumptions

- "Character" must mean *one* thing for indexing and counting to work. Unicode defines at least three candidates: the **code point** (a value in U+0000..U+10FFFF), the **code unit** (the fixed-width unit of a specific encoding — 8 bits for UTF-8, 16 bits for UTF-16), and the **grapheme cluster** (what a user perceives as one character). These three counts differ on real text, and each language's `len`/`length` picks a different one.
- Encoding shape: UTF-8 uses 1–4 bytes per code point (ASCII-compatible, which is why ASCII fixtures hide everything); UTF-16 — the in-memory form of Java `String`, JavaScript strings, and Windows APIs — uses one code unit for the Basic Multilingual Plane and a **surrogate pair** (two units, U+D800–U+DFFF) for everything above U+FFFF. Any character above U+FFFF — most emoji, rare CJK — is two code units.
- Composed meaning goes beyond code points: grapheme clusters can be **multi-code-point**. Combining marks (`e` + U+0301 = é), regional-indicator pairs (flags), and Zero-Width Joiner emoji sequences all render as one character while being several. Indexing by code unit can split a surrogate pair; byte addressing can split a UTF-8 sequence — both produce invalid text that downstream parsers reject.

### Counterexample

One glyph, four counts. The family emoji 👨‍👩‍👧‍👦 is four person emoji joined by three U+200D ZERO WIDTH JOINERs: **1 grapheme cluster**, **7 code points**, **11 UTF-16 code units** (each person emoji is a surrogate pair, each ZWJ one unit), and **25 UTF-8 bytes** (4 bytes per person emoji, 3 per ZWJ). JavaScript's `.length` on it returns 11; Python's `len()` returns 7; a database column sized for "25 characters" that means bytes truncates it into a broken half-sequence. None of these numbers is wrong — they answer different questions, and the bug is code that asks one question while assuming it asked another. The same split explains why reversing a string by index produces garbage whenever combining marks or surrogate pairs are present.

### What changes when the assumption is removed

Corrected statement: *text is a sequence of code points encoded into bytes; what users perceive as characters is a third, language-level grouping — name which one every length/index/truncate operation means.* Practical rules: treat `length` as "code units in this runtime's encoding"; use grapheme segmentation (ICU, `Intl.Segmenter` in JavaScript) for anything user-facing such as cursors, limits, and layout; iterate by code point, never by byte or code unit, when transforming text; and store text in encodings that cover the full range (`utf8mb4`, not the legacy 3-byte MySQL `utf8`) so storage and application agree about what a character is.

### Consequences

The interview probe "how many characters is an emoji?" is this assumption in one question; the follow-up "why does your JavaScript counter disagree with your Python counter?" is the layered answer. The production risk is structural: two services that both "handle Unicode" but count different layers will disagree about limits, dedup, and identity — an API-contract bug, not a rendering bug.

## Assumption 2: "Truncating to N Characters Is Safe"

### The taught rule

Enforce a limit by cutting: `s[:100]` for a 100-character title, `LEFT(title, 100)` in SQL, a 255-character column.

### The hidden assumptions

- Cutting at N of the wrong unit can produce an invalid string: a UTF-8 sequence cut mid-code-point is not valid UTF-8; a UTF-16 string cut between the halves of a surrogate pair produces an unpaired surrogate that JSON serializers and validators reject.
- Cutting at N code points can still break *rendering*: a regional-indicator pair (flag emoji) cut in half leaves an orphan indicator, and a ZWJ sequence cut mid-way leaves disconnected emoji.
- Database limits are defined in the database's units, not yours: PostgreSQL `varchar(n)` counts characters (code points); MySQL `VARCHAR(n)` counts characters in the column's charset, but the legacy `utf8` (utf8mb3) charset silently cannot represent 4-byte characters at all — emoji either error out or, in truncation-tolerant modes, get cut without any API-level signal.
- Byte-counting APIs that display "characters" make the effective limit depend on the *content*: 100 bytes is 100 ASCII characters, 50 Cyrillic ones, or 25 emoji.

### Counterexample

Two classic, checkable shapes. First, the macOS filesystem trap: HFS+ and APFS store filenames in **NFD** (decomposed) normalization, so `é` is the two-code-point sequence `e` + U+0301; Linux and most Windows filesystems use whatever bytes the application supplies, typically **NFC** with the single code point U+00E9. The two forms render identically, compare unequal byte-wise, and have different lengths — and a 7-character cut applied to the decomposed form slices the accent off, leaving a different name. Second, the silent database cut: a `utf8mb3` column receiving 👨‍👩‍👧‍👦 either rejects the write or stores a truncated prefix depending on server mode; the application that assumed "the DB accepted my string" now serves broken text. Both failures are invisible in ASCII tests and both surface from real users with real names — precisely the field where truncation does the most harm.

### What changes when the assumption is removed

Corrected statement: *truncation is a transformation of encoded text, not a substring operation — truncate by grapheme clusters at the presentation layer, by code points with validity checks at the storage layer, and validate the result is still well-formed.* Concretely: decide the limit's unit explicitly (bytes, code points, graphemes) wherever a limit is published; on cut, verify the tail is not a partial sequence or an orphaned combining mark; prefer rejecting over-sizes at input to silently cutting them; and normalize (NFC is the usual choice) *before* comparing or limiting, because normalization changes length. The database and the application must agree on the charset — and "UTF-8" in MySQL means `utf8mb4`, a lesson every emoji-in-username incident has re-taught.

### Consequences

"Your truncation broke a user's name" is a support-ticket genre with a spec-level root cause, and interviewers use it to test whether a candidate's text knowledge goes beyond ASCII: the expected answer names the unit mismatch, the normalization split, and validity-after-cut. The review heuristics — normalize first, cut by grapheme for display, verify well-formedness after — are four lines that prevent the entire class.

## Assumption 3: "Uppercasing Is Trivial"

### The taught rule

Case-insensitive matching means calling `lower()` or `upper()` on both sides and comparing. Sorting text means comparing strings with `<`.

### The hidden assumptions

- Case mapping is **locale-dependent**. The dotless Turkish `ı`/dotted `İ` pair means ASCII `I` uppercases to `İ` in Turkish and to `I` everywhere else; the same code under different locale settings produces different letters. Java has both `toUpperCase()` (locale-sensitive) and `toUpperCase(Locale.ROOT)`, and choosing the wrong one is a documented bug source.
- Some mappings are **one-to-many or context-dependent**: German `ß` uppercases to `SS` (length changes), and final-form Greek sigma maps differently at word ends. Any code that assumes `upper()` preserves length or is an involution (`lower(upper(s)) == s`) is wrong for real alphabets.
- Case-insensitive *comparison* is not "lowercase both sides": Unicode defines **case folding** precisely so matching can be locale- and context-stable, and folding still requires normalization first (é as one code point vs `e` + combining accent are case-fold-equal only after NFC/NFD alignment).
- Sorting is not comparing: **collation** is a locale-aware, multi-level comparison (base letters, then accents, then case) defined by the Unicode Collation Algorithm. Naïve code-point ordering puts `Z` before `a`, and puts `ä` after `z` — while a Swedish dictionary expects `ä` near `a` and a German phone book near `ae`. Databases each ship different default collations, which makes "ORDER BY name" a per-database answer.

### Counterexample

A deduplication job matches usernames case-insensitively by calling `.lower()` on both sides. Two accounts register: `McDonald` and `MACDONALD` — fine so far. Then a Turkish locale enters through an unexpected path (a JVM with `-Duser.language=tr` on one worker), where `I`.toLowerCase() produces `ı`; the same input string now lowercases differently on different workers, and the accounts deduplicate inconsistently — sometimes merging, sometimes not. No exception is thrown anywhere; the inconsistency is only observable as duplicate accounts. The repair is mechanical: fold with a locale-independent API (`Locale.ROOT` in Java, `casefold()` in Python), normalize before folding, and store a canonical form so equality does not depend on which machine computed it.

### What changes when the assumption is removed

Corrected statement: *case mapping and ordering are locale-parameterized operations; equality of text is defined only after normalization and folding are pinned.* Rules that hold everywhere: use locale-independent folding for identifiers, keys, and dedup; reserve locale-sensitive casing and collation for display; never assume `upper()`/`lower()` preserve length, are invertible, or are idempotent across locales; and when a database sorts text, name the collation explicitly, because "the default" is a per-engine value. The Unicode case-mapping data (SpecialCasing) and the Collation Algorithm exist precisely because these operations are not trivial.

### Consequences

The interview probe "sort these names the way a German user expects" distinguishes "knows ASCII" from "knows text": the expected answer names collation levels, not `sort()`. The production lesson is broader: any operation on text (length, equality, order) is parameterized by choices — encoding, normalization, locale — and code that does not *name* its choices gets different answers on different machines, a concurrency-of-semantics bug rather than a formatting one.

## Assumption 4: "UI Validation Is Enough"

### The taught rule

The form has a maxlength attribute and a regex; anything that passes the front end is well-formed text the backend can store.

### The hidden assumptions

- Client-side validation is a *usability* feature, not a *security* boundary: any client can be bypassed, and the server receives raw bytes from strangers regardless of what the UI checked. Validation only counts at trust boundaries — server ingress, queue consumers, batch importers — because those are the readers the UI cannot vouch for.
- Character-set assumptions stack invisibly: an HTTP form declares its encoding one way, the framework decodes it another way, the database stores it in a third — a mismatch at any layer yields mojibake (UTF-8 read as Latin-1) or silent replacement characters, neither of which UI validation can prevent.
- Text that is valid *somewhere* is dangerous *elsewhere*: strings safe in a UTF-8 JSON body become injection vectors when re-encoded into HTML, URLs, shell commands, or logs. The web-security chapter's encoding-violence examples are text-assumption failures, not library failures.
- Validation and normalization have an order: validating before normalizing accepts visually identical duplicates (`é` in two encodings), and validating after a lossy transformation can accept text different from what the user typed.

### Counterexample

A registration form limits display names to 30 characters client-side. An attacker skips the form and POSTs a 4,000-byte string, including a half-cut 4-byte emoji sequence and a combining-mark run. The API stores it; the template layer renders it; two downstream consumers break independently — a JSON serializer rejects the unpaired surrogate when the string passes through a UTF-16 intermediary, and an analytics pipeline that counts bytes overflows its fixed field. Every layer trusted the previous layer to have validated; no layer did, because the UI's validation was the only one, and it was bypassed. The structural fix is boundary validation with an explicit contract: the server re-checks encoding validity (reject invalid UTF-8 at ingress), length in named units, normalization form, and permitted character classes — the same re-validation the API-contracts chapter demands for structural fields, applied to text.

### What changes when the assumption is removed

Corrected statement: *treat incoming text as unvalidated bytes until a server-side boundary has checked encoding, length, normalization, and content — the UI's checks are UX, not correctness.* Make the text contract explicit per field: allowed encoding (always UTF-8 on the wire), maximum length and its unit, normalization form (usually NFC), and the character policy. Reject rather than repair where possible, because silent replacement corrupts data more quietly than a 400 response. Finally, test the boundary with hostile text deliberately — surrogate halves, mixed normalizations, 4-byte characters — as part of the property-based tests the testing chapter describes, not after a support ticket.

### Consequences

Interviewers probe this as "the DB accepted it but the page shows garbage — walk the pipeline," and the strong answer moves byte-by-byte through the layers naming each one's charset assumption. The organizational lesson: text bugs are *positional* — the same string is fine in one layer and broken in the next — so the fix is never "use Unicode everywhere" but "define, at each boundary, which Unicode operations and validations apply there."

## Interview Questions

1. **Why does the same emoji have length 11 in JavaScript, 7 in Python, and 25 bytes in UTF-8?** Three different units: UTF-16 code units (surrogate pairs count as 2), code points (Python's `str` is code points), and bytes (4 per astral code point). Grapheme count — what users see — is a fourth, smaller number; name the unit every length means.
2. **How do you truncate a UTF-8 string to 100 "characters" safely?** Decide the unit (graphemes for display, code points for storage), cut at a code-point boundary, verify no surrogate pair or combining sequence was split, and normalize first so the length is stable. DB limits must be converted from the column's units.
3. **Why can `é` fail to equal `é`?** Different code-point sequences: U+00E9 vs `e` + U+0301 (NFC vs NFD), which macOS filesystems and user input produce interchangeably. Fix: pin a normalization form and compare after normalization (and case folding for case-insensitive matching).
4. **What is wrong with "lowercase both sides" for case-insensitive matching?** Case mapping is locale-dependent (Turkish `I` → `ı`) and length-changing (`ß` → `SS`). Use locale-independent case folding (`Locale.ROOT`, Python `casefold()`), normalize first, and reserve locale-sensitive casing for display.
5. **The client validates input; why does the server still need to?** Client checks are bypassable UX, not a boundary. Text arriving at the server is unvalidated bytes: check encoding validity, length in a named unit, normalization, and content policy at ingress — and test with surrogate halves, mixed normalizations, and 4-byte characters.

## Key Takeaways

- Bytes, code points, code units, and graphemes are four different counts; every length, index, and limit operation silently picks one, and the bugs start where two layers pick different ones.
- UTF-16 surrogate pairs and multi-code-point graphemes mean neither byte indexing nor code-unit indexing equals character indexing; user-facing limits need grapheme segmentation, storage needs validity-checked code points.
- Truncation is a transformation: cut at the right unit, normalize first, verify the result is still well-formed — a half-cut emoji is data corruption, not formatting.
- Case mapping and collation are locale-parameterized; equality requires pinned normalization and locale-independent folding, and "sorted order" is meaningless without naming a collation.
- UI validation is presentation; real validation happens at system boundaries, where encoding, length unit, normalization form, and character policy are checked explicitly against a written contract.

## Cross-References

- [Input constraints](input-constraints.md) — the collection's algorithm-level input assumptions, including the ASCII-text precondition this chapter generalizes.
- [API contracts](api-contracts.md) — text fields and contracts that must state units to survive.
- [Testing assumptions](testing-assumptions.md) — why ASCII fixtures hide the entire bug class and what property-based text tests catch instead.
- [Web security](../../security/web-security.md) — encoding mismatches as injection surface; server-side validation at trust boundaries.
- [Full-text search](../../dbms/sql/full-text-search.md) — collation and tokenization choices inside the database layer.
- The Unicode Standard's normalization annexes and the Unicode Collation Algorithm are cited by title (UAX #15, UTS #10); Python's Unicode HOWTO (docs.python.org) is the language-level reference used for the folding and encoding rules.
