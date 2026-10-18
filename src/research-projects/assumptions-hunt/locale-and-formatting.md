# Locale and Formatting Assumptions: What "Default Formatting" Silently Promises

## Overview

Every program that formats a number, sorts a string, or prints a date quietly consults a locale — and when the locale is missing, the program silently substitutes one, usually a US-English invariant that works on every demo machine. This chapter audits four assumptions that survive development precisely because they hold there: that the decimal point is a dot, that string comparison is alphabetical ordering, that calendar weeks and month names are universal, and that uppercasing and lowercasing are inverse operations. Each is false for large populations of users, and each fails not with an exception but with a *wrong value* — 1.234 parsed as one thousand two hundred thirty-four instead of one point two three four, a customer sorted into the wrong account block, a report dated to the wrong week, an identifier that uppercases differently on two servers and fails an equality check.

The failure signature matters: locale bugs are silent by construction, because the input is always "valid" — it merely means something else. This chapter applies the collection's five-step pattern to the family, leaning on the Unicode Consortium's collation specification (UTS #10), the CLDR locale-data project, and the ECMAScript Internationalization API (ECMA-402) as primary sources, all verified live. Text encoding — how characters become bytes — is the sibling chapter on encodings and text; here the subject is what the decoded characters *mean*: their numeric conventions, their sort order, their calendars, and their case. The common thread is that "format" is not decoration on top of data; it is a parsing contract, and every default is a choice someone else made for your users.

## Assumption 1: "The Decimal Point Is a Dot"

### The taught rule

Numbers are written `1234.56`; parse with `parseFloat` (or `std::stod`, or `float()`), format with the default, and the value round-trips.

### How it fails

Dot-as-decimal is a dialect, not a law. In German, `1234,56` is the number and `1.234` is one thousand two hundred thirty-four; in French, a thin space groups thousands (`1 234,56`); in Indian numbering, grouping runs in twos after the first three (`12,34,567` for 1.2 million, the lakh/crore system). The failure is bidirectional. *Parsing:* user input `1,5` sent to a dot-expecting parser becomes 15 — a fivefold error — or 1 depending on whether the comma is treated as separator or garbage. A Swiss user entering `1'500` (apostrophe grouping) into a dot-locale field gets 1. *Formatting:* a server that renders `1234.56` into an invoice consumed by a German ERP imports it as 1234 dollars and 56 *millions* of cents — the magnitude survives, the scale does not. Data exchange amplifies this: CSVs with comma delimiters and comma decimals require quoting gymnastics that half the tooling ecosystem gets wrong, and spreadsheet imports silently reparse values under the *viewer's* locale, so the same file shows different numbers to two people.

The subtlest variant is *machine* formatting drifting by environment: code that formats via the default locale produces dot-decimals on the CI server and comma-decimals on a developer's French laptop, so tests pass in one environment and fail in another — the environment-dependent default is itself the bug. This connects directly to the floating-point chapter's assumption set: even after parsing correctly, binary floats cannot represent 0.1 exactly, so the formatting decision (how many digits, which rounding mode, which decimal separator) is where financial correctness actually lives.

### Failure scenario

A payment form accepts `1.234,56` from a German user; the backend validates with a regex allowing digits, dot, comma, then parses with `parseFloat("1.234,56")`, which returns `1.234` (JavaScript stops at the comma). The charge is 1.23 euros. The user notices on small transactions and stops using the form; the audit finds three months of sub-euro charges and a support alias full of "it charged the wrong amount" tickets that were dismissed as user error. The fix is a locale-explicit contract: the API accepts a *string plus declared locale* (or better, integer minor units), parsing happens through a locale-aware routine (ECMA-402's `Intl.NumberFormat` constructor with `useGrouping` handled, or the server language's ICU binding), and the canonical machine format (dot decimal, no grouping) exists only at the wire boundary, never inside user-facing flows.

### Detection heuristic and what to assume instead

Detection: grep for `parseFloat`/`atof`/`to_float` on any path that touches user input or third-party files; test each with `1.234,56`, `1,234.56`, and `1'500` — three inputs, three different intended values. Corrected statement: *never parse formatted numbers with the ambient default; the format is part of the data's type, it must be declared per field, and the exchange format between systems should be unambiguous by construction (ISO-formatted or minor-unit integers), not dot-by-convention.*

## Assumption 2: "String Comparison = Alphabetical = Collation"

### The taught rule

Sort the names with the default comparison and they come out alphabetically; equality via `==` (or `equals`) matches strings that look the same.

### How it fails

Three different orderings hide inside "alphabetical." *Code-point order* (what C's `strcmp`, Java's `String.compareTo`, and Rust's `str` Ord deliver) puts every uppercase letter before every lowercase one (`Z` < `a`), puts accented letters after the whole basic alphabet (`é` after `z`), and makes "Ísland" sort after "Zimbabwe." *Dictionary/collation order* (what UTS #10's Unicode Collation Algorithm defines) compares at multiple strengths: primary (base letter, so `a` equals `á` at the primary level), secondary (accents), tertiary (case) — and the *tailoring* is language-specific: German orders `ö` near `o`, Swedish orders it after `z`, so the same input sorts differently under `de` and `sv` tailoring with no bug in either. *Database collation:* engines differ by default — MySQL's common `utf8mb4_*_ci` collations compare case-insensitively, PostgreSQL's C locale compares bytewise — so the same query orders differently, and a unique index that treats "Müller" and "MULLER" as distinct in one engine merges them in another.

Equality has its own trap: visually identical strings can differ in normalization form (composed `é` versus `e` + combining accent), which the sibling chapter on encodings covers; collation adds the case and accent layers on top. The interview-grade example is the Turkish dotless ı: `i`.toUpperCase() in Turkish locale yields `İ`, so an equality check that passes in every other locale fails there — collation and case rules are locale parameters, not constants.

### Failure scenario

A CRM sorts accounts with the ORM's default (bytewise). All accounts whose name starts with an uppercase letter appear before all lowercase ones — fine until a data import writes one legacy record with lowercase names; that customer, "ácme trade," lands at the absolute bottom, after "Zygmunt." The collections team's alphabetical worklist assigns them to the wrong block for a year. Nobody notices because spot checks use names that sort correctly under both rules. The fix chooses ordering explicitly per query (a UCA collation with a *named* tailoring, or an application-side ICU sort key), stores a generated sort-key column for indexed ordering, and documents that "alphabetical" is undefined without a locale — the same discipline the ordering-and-pagination chapter applies to ORDER BY determinism.

### Detection heuristic and what to assume instead

Detection: sort the test fixture names `Zoe`, `alice`, `Émile`, `bob` under your production comparison; any order other than a consciously chosen one is a finding. Corrected statement: *there is no default alphabetical order — there are code-point order, UCA order with a named tailoring, and engine-specific collations; pick one per comparison site, store sort keys where ordering is indexed, and treat case-insensitive equality as a collation decision with per-language exceptions (Turkish i) rather than a tolower() call.*

## Assumption 3: "Calendar Week and Month Names Are Universal"

### The taught rule

Weeks start on Monday (or Sunday — either way, one rule), week 1 is the first week of the year, month names are the English twelve, and formatting a date is a rendering detail.

### How it fails

Week numbering alone carries three independent conventions: the first day of the week (Monday in ISO and most of Europe, Sunday in the US, Saturday in some Middle Eastern contexts), the rule for week 1 (ISO 8601: the week containing the year's first Thursday, so week 1 can start in the previous December), and minimal-days-in-week (US convention counts a week as week 1 if it merely contains January 1). The same Saturday can be "week 52 of 2023" in one convention and "week 1 of 2024" in another — both correct. Financial and manufacturing systems that compare "week numbers" across offices in different locales are comparing integers with different meanings; a report that says "week 28" is ambiguous until the numbering rule is attached. Month names localize further than spelling: CLDR data provides them per locale, and several calendars (Buddhist, Islamic, Hebrew, Persian) are in active civil use with different year arithmetic entirely — a Buddhist-calendar date rendered with Western year numbers is off by 543 years while looking perfectly well-formed.

Weekday arithmetic completes the family: "last Monday" depends on which day weeks start; "the first Monday of March" is stable only when the week start is pinned. This is adjacent to — but distinct from — the timezone and clock assumptions in the sibling clocks-and-time chapter: a correct instant with a wrong calendar convention is still a wrong date for the human reading it. This repo's own `cal` manual page demonstrates the dependency concretely: weekday order and month names come from `LC_TIME`, and week numbering is documented as locale-shaped rather than universal.

### Failure scenario

A multinational retailer runs a promotion "valid through week 29." The German office (ISO: Monday-start, first-Thursday rule) reads week 29 as July 15–21; the US office (Sunday-start, Jan-1 rule) reads it as July 14–20; the regional system generating coupon expiry dates uses the US rule while the global reporting system uses ISO. Coupons expire one day early for a subset of customers; the customer-facing bug is "my coupon said valid through the 20th and died on the 20th at 00:00" — a boundary mismatch nobody can reproduce locally, because each system is correct under its own convention. The fix pins the standard: all cross-organization week references carry the rule (ISO 8601 week dates, `2024-W29-1` format), locale-dependent rendering happens only at the display edge, and stored durations use explicit dates, never week integers.

### Detection heuristic and what to assume instead

Detection: search for week-number arithmetic (`weekOfYear`, `ISO_WEEK`, `WEEK(`) and check whether the numbering rule is named in the same unit of code; grep for hardcoded month-name arrays. Corrected statement: *week numbers and month names are locale data, not constants — exchange instants as dates/timestamps (ISO 8601 forms), attach the numbering rule to any week integer that crosses a boundary, and localize names only at render time via a CLDR-backed formatter.*

## Assumption 4: "Uppercase/Lowercase Conversion Is Symmetric"

### The taught rule

`toUpperCase()` and `toLowerCase()` are inverses; case-folding a string twice returns the original; case conversion preserves length.

### How it fails

Unicode case mapping violates all three. *Asymmetry via locale:* in Turkish, `i` uppercases to `İ` (dotted capital I) and `I` lowercases to `ı` (dotless small i); the round trip `i → İ → ı` does not return the original. The canonical production incident class is the "Dotless I bug": a Turkish-locale server lowercases the identifier `FILE` to `fıle`, which no longer matches the ASCII filename — famously manifesting as the Perl ecosystem's locale-dependent test failures and the reason language runtimes ship locale-independent case operations by default. *Length change:* `ß` uppercases to `SS` (two code points from one); `ﬁ` (the ligature) uppercases to `FI`. Any code that allocates a same-size buffer, or that uses case conversion as a canonicalization (hash the lowercased email) while comparing lengths, breaks. *Non-inverse semantics:* case *folding* (the purpose-built, locale-independent equivalence operation) is not the same function as lowercasing; equality should use fold-or-compare, never lowercase-both-sides, which differs for characters like the Kelvin sign and the Greek final sigma (which lowercases to `ς` mid-word but `σ` at the end — position-dependent mapping that a naive round trip cannot invert).

The assumptions interact: a case-insensitive match implemented as `lower(a) == lower(b)` gives different answers under different default locales on different machines — the environment-dependent default again — while the platform's case-insensitive *comparison* routines (or Unicode caseless matching per the standard) give one deterministic answer.

### Failure scenario

A URL-shortening service canonicalizes codes by lowercasing: user requests for `AB-42` are lowercased to `ab-42` and looked up. A regional deployment runs under a Turkish default locale; `I-95` lowercases to `ı-95`, misses the database row for `i-95`, and 404s. The same code path works in the US region, so the incident is reported as "regional data issue." Worse, one created code was stored under the Turkish lowercasing and now matches nothing anywhere — a permanently orphaned row. The fix is exactly one decision made explicit: canonicalization uses locale-independent case *folding* (or stores the original plus an ASCII-folded lookup key), never ambient-locale case conversion — and the deployment audit adds "default locale of every process" to configuration review, because the ambient locale is a config value nobody set.

### Detection heuristic and what to assume instead

Detection: grep for `toLowerCase()`/`toUpperCase()` used on identifiers, emails, codes, and filenames (canonicalization contexts) as opposed to display text; run the CI suite with `LANG=tr_TR.UTF-8` once — the failures it produces are the inventory. Corrected statement: *case conversion is a locale-parameterized, length-changing, non-invertible transformation; use dedicated caseless comparison or folding for equality, keep the original string as the identifier, and never let the ambient locale decide identity.*

## Interview Questions

1. **A German user enters `1.234,56` and your system charges 1.23 euros. Walk through the failure and the fix.** `parseFloat` stops at the comma after treating `1.234` as dot-formatted — a locale mismatch at parse time. Fix: declared locale (or minor-unit integers) at the input boundary, locale-aware parsing, and an unambiguous machine exchange format; test with `1.234,56`, `1,234.56`, `1'500`.
2. **Why does `Z` sort before `a`, and what are the three orderings hiding behind "alphabetical"?** Code-point order compares scalar values; UCA collation compares at primary/secondary/tertiary strengths with per-language tailoring; database collations layer engine defaults on top. Pick one per comparison site and store sort keys for indexed ordering.
3. **Two offices read "week 29" differently and both are right. Explain.** Week numbering has three parameters — first day of week, week-1 rule, minimal days — and ISO 8601 (first Thursday) differs from the US convention (contains Jan 1). Cross-boundary week references must carry the rule explicitly, e.g. ISO week dates.
4. **Why does `i`.toUpperCase() break in Turkish, and why is toLowerCase the wrong equality tool?** Locale-sensitive case mapping maps `i` to `İ`; case conversion is also length-changing (`ß → SS`) and position-dependent (final sigma). Equality needs Unicode caseless matching or case folding, not ambient-locale lowercase.
5. **Where do locale defaults live that you must audit?** Process environment (`LANG`/`LC_*`), library default locales, database column collations, browser/user locale at the frontend, and the CSV/spreadsheet layer between systems — each is a config value someone else chose.

## Key Takeaways

- Locale bugs fail silently with valid-looking wrong values: a parse that yields 1.234 instead of 1,234.56 raises nothing and still loses money.
- "Alphabetical" is undefined until a comparison rule is named: code-point, UCA-with-tailoring, and engine collation are three different contracts; equality has its own (caseless matching, not lowercase-both).
- Week integers and month names are locale data; ISO 8601 week dates or explicit dates must carry meaning across boundaries, with rendering localized only at the edge.
- Case conversion is locale-parameterized and non-invertible (`ß → SS`, Turkish i); identifiers need folding or original-form storage, never ambient-locale conversion.
- The ambient default locale is untracked configuration; audit environments (`LANG`, library defaults, DB collations) and pin the formats your data contracts depend on.

## Cross-References

- [Encodings and text](encodings-and-text.md) — how characters become bytes and why visually identical strings can differ before collation even starts.
- [Floating-point](floating-point.md) — the numeric representation assumptions underneath decimal formatting, especially for money.
- [Ordering and pagination](ordering-and-pagination.md) — ORDER BY determinism and the tie-breaker discipline that collation choices feed into.
- [Clocks and time](clocks-and-time.md) — instants, timezones, and the calendar conventions this chapter pairs with them.
- [The cal manual page](../../linux/binaries/util-linux/cal.md) — a working example of `LC_TIME`-shaped weekday, month, and week-number behavior.
- [Unicode Collation Algorithm (UTS #10)](https://www.unicode.org/reports/tr10/) — [CLDR](https://cldr.unicode.org/) locale data — [ECMA-402](https://tc39.es/ecma402/) Intl API (all verified). ISO 8601 cited by title.
