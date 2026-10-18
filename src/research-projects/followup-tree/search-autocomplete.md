# Follow-up Tree: Search Autocomplete

## Overview

"Design autocomplete for the search box" is the friendliest-looking system-design opener precisely because it escalates so well: every naive answer — "use a trie" — is one follow-up away from a memory crisis, a ranking problem, a sharding decision, and a safety question that most candidates have never connected. The ladder here runs from the data structure (trie, its compression, and the sorted-array alternative), through ranking (why frequency alone is wrong and what top-k-per-prefix precomputation buys), into scale (sharding by prefix, FSTs and index-time structures, the latency budget that dictates the architecture), and ends at the design judgment: precompute versus compute, personalization versus privacy, and the abuse surface unique to a feature that *writes your words back at every user*. The thread tying every rung together is *the prefix contract*: a completion system promises the top few suggestions for any prefix in tens of milliseconds, and every follow-up asks what that promise costs in memory, in freshness, or in correctness. This chain is the mechanism-deep companion to the worked design — the requirements-and-estimates version lives in [Typeahead](../../interview/system-design/typeahead.md) and the full search-system ladder in [Search](../../interview/system-design/search.md); the data-structure foundation (hash tables, and why exact-match structures cannot serve prefixes) is owned by [Hash Tables](./hash-tables.md). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"A user types 'neo' in the search box. What must happen for them to see suggestions in the next 50 milliseconds?"**

The expected core answer: the prefix "neo" is looked up in a structure organized for *prefix* retrieval — not exact lookup. The canonical structure is a trie: walking one child per character reaches the node for "neo," and the subtree below it contains every continuation; the suggestions are the highest-ranked terms in that subtree, either found by walking or — the senior addition — read from a small top-k list cached *at the node*. If ranking matters (it always does), each term carries a weight (aggregate popularity, recency-decayed), and the node stores its k best completions so the answer is one pointer-walk plus a sort of a tiny list, not a subtree scan. The alternatives worth naming up front: a sorted dictionary plus binary search for the prefix range (O(log n) locate, then scan until prefix stops matching — elegant, cache-friendly, memory-cheap), and production engines that index completions into an FST or an edge-n-gram index ([Elasticsearch's completion suggester](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-suggesters.html) is the named example).

A weak answer says "store all queries in a hash map" — exact-match thinking applied to a prefix problem (see [Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md) for why the structures are not interchangeable) — or draws a trie and stops, unable to say how "the top 5" is computed. The strong answer states the latency budget first, then the structure, then the ranking, and volunteers that the *whole design* is downstream of that budget: 50 ms end-to-end leaves one in-memory lookup, not a service fan-out. The follow-up that escalates: **"Where do the weights come from, and what is wrong with 'most frequent completions'?"** — which moves the ladder from structure to ranking.

## Level 2: Trie Mechanics and the Memory Bill

**What it tests:** whether the trie is a mechanism you can price — fan-out, node overhead, compression — or a picture you can draw.

**Weak answer:** draws the classic 26-children trie, says lookup is O(length of prefix), and has no answer for why nobody ships that shape.

**Strong answer:** prices the node. A naive per-node array of 26 child pointers is 26 words per node — for English, overwhelmingly pointers to nothing — so real implementations use a map per node (hash overhead, pointer chasing, cache-hostile) or compress: a *radix trie* (Patricia) collapses single-child chains into edge labels, cutting node count by the length of unbranched runs, while an FST/DAWG shares common suffixes as well as prefixes and can represent a whole dictionary in a few hundred MB with ordered iteration intact.

**Escalation trigger:** "The interviewer triples the dictionary to 500 million terms. What breaks first, memory or latency — and what do you change?"

**Answer.** Latency survives; memory and cache behavior do not. Pointer-chasing through hundreds of millions of scattered nodes turns the O(prefix) walk into a chain of cache misses, and node overhead (pointer or map per node) inflates to tens of bytes per *character* of the dictionary — the numbers that force the change from "a trie" to "a compressed, serialized structure." The production answers, in the order a senior reaches for them: radix compression (fewer, fatter nodes — fewer misses per walk); FST or minimal-perfect representations built once at index time (nodes become array offsets, not heap objects — the walk becomes arithmetic); and the *sorted-array + binary search* fallback, which trades the trie's incremental-typing elegance for two cache-friendly binary searches over contiguous memory and a bounded prefix-range scan — the right answer when the dictionary is stable and the machine is memory-poor. The interviewer's real question is workload modeling: autocomplete dictionaries are *hot for the top of the trie and cold for the tail* — the node for "n" is touched millions of times a minute, the node for "zyx" once a day — so the honest architecture keeps the hot upper levels resident and pushes the cold tail to an indexed on-disk structure, which is exactly the hot/cold tiering any cache design makes (the general pattern is the atlas map [Search & Inverted Index](../connection-atlas/search-inverted-index.md)).

The design twist: *the trie serves keys; the suggestions serve value.* Whether the value lives at the node (precomputed top-k) or behind a lookup (compute on read) is the rung-3 decision, and the memory bill of storing k suggestions per node is the price of making reads trivial. The follow-up that escalates: **"How are those top-k lists actually computed — and kept correct?"**

## Level 3: Ranking — Frequency, Decay, and Precomputation

**What it tests:** whether "rank by popularity" decomposes into signal choice, decay, and the precompute-versus-online trade — or stays a slogan.

**Weak answer:** "Show the most frequent completions first" — one raw signal, no time dimension (a query that spiked for one news cycle dominates forever), no personalization boundary, no refresh story.

**Strong answer:** names the signal stack — raw query frequency, *successful* completions (typed fully and clicked, not abandoned), position-weighted evidence, and time decay (exponential half-life so yesterday's spike fades) — then states the architecture consequence: weights are aggregated offline into per-node top-k lists, which makes serving trivial but makes *freshness* a pipeline property (rebuild cadence, incremental updates), and states the personalization boundary: user-history boosting happens as a thin re-rank of a server-provided candidate list, never as a per-user index.

**Escalation trigger:** "Why not compute suggestions live from a counter map on every keystroke?"

**Answer.** Because live ranking converts every keystroke from a lookup into a top-k aggregation over an unbounded candidate set, which is both the latency budget's death and a correctness trap: raw in-memory counters drift from the offline truth, are trivially pollutable (an adversary or a bot farm types a phrase a million times and it becomes the top suggestion for every user — the input-control question of [Input Constraints](../assumptions-hunt/input-constraints.md)), and lose across restarts. Precomputed top-k inverts the cost: aggregation happens offline where it can be debotted, weighted, decayed, and reviewed; serving reads a tiny immutable list; and *updates* become the interesting problem — a breaking-news term must enter the candidate pool between rebuilds, so production systems keep a small online overlay (recently-detected trending terms appended to node results) layered over the frozen index, with the overlay's strict admission rules (absolute minimum volume, source diversity, human review for the top slots) as the abuse control. The senior framing: ranking is a *materialized view* over query logs, and the design questions — rebuild cadence, incremental patching, overlay admission — are materialized-view-refresh questions, not algorithm questions.

The design twist: *trending is a rate problem, not a frequency problem.* A term's share-of-voice against its own baseline (z-score against its trailing average) detects a spike without the term ever being globally frequent — which is how new events surface while long-tail stable terms keep their slots. The follow-up that escalates: **"One service cannot hold the dictionary. How does this shard — and what does sharding do to correctness?"**

## Level 4: Scale, Fuzzy Matching, and the Abuse Surface

**What it tests:** the expert rung — distributed serving, fuzzy prefixes, latency-layer design, and the safety properties that distinguish a shippable completion system from a demo.

**Weak answer:** "Shard by hash of term" — which destroys prefix locality, or "add spell correction" with no mechanism, and no awareness that autocomplete is an attack surface at all.

**Strong answer:** shards *by prefix* (first-letter or first-two-letters partitions, with hot prefixes like common initials split further or replicated), so one query touches exactly one shard; layers the latency path (client cache of recent prefixes → edge/CDN cache for hot prefix responses → service → index) so that keystroke N-1's answer is often already paid for; and treats fuzzy matching as a bounded edit-distance problem served by the same structures — n-gram or character-trie index with candidate generation by Levenshtein automaton (the FST formulation) — where the senior detail is that fuzzy results must *re-rank against the exact-prefix results*, not merge blindly.

**Escalation trigger:** "Walk me through what can go wrong on the worst day of running autocomplete — then design the guardrails."

**Answer.** The failure classes, in the order they make headlines. *Poisoning:* suggestions are generated from collective input and displayed with system authority, so bot-driven volume or coordinated campaigns can make the box say offensive or defamatory things — guardrails are offline aggregation with minimum-evidence thresholds, blocklists enforced at index build (before serving, where removal is cheap) rather than at query time, and rate limits on suggestion-driving traffic ([Rate Limiter Design](./rate-limiter-design.md) is the same admission ladder aimed at a different endpoint). *Privacy leakage:* a personalization signal too eager (typed-in emails, other users' names surfaced by partial input) turns a convenience feature into a disclosure mechanism — the guardrail is that personal re-ranking may *reorder only* the server's public candidate list, never add candidates from user-private data, the same boundary the [Logging and PII](../assumptions-hunt/logging-and-pii.md) audit draws for telemetry. *Availability coupling:* every keystroke is a request, so autocomplete can triple frontend traffic for a fraction of its value — the guardrail is aggressive prefix-response caching, client-side suppression of requests during fast typing (debounce), and a graceful-degradation mode where the box simply waits for the enter key. The Redis path earns a mention as the named small-scale tool: sorted sets with lexicographic ranges ([Redis sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/)) implement the sorted-dictionary design directly for dictionaries that fit in one node. The sentence that ends the chain well: autocomplete is a public-facing write-amplifier — it turns the crowd's keystrokes into everyone's vocabulary — so the design must specify *who can add a suggestion* as precisely as it specifies the lookup structure.

## How to Approach Unfamiliar Variations

The template for autocomplete variations — "multilingual," "typo-tolerant," "suggest products, not queries," "explain the memory footprint":

1. **Reduce the variation to the prefix contract.** Every variant changes what matches the prefix (exact, fuzzy, semantic, translated) or what ranks it (frequency, revenue, personalization). Name which half changed, and the structure choice follows: exact → trie/sorted array; fuzzy → n-gram or automaton index; semantic → embedding retrieval, a different ladder entirely.
2. **Answer memory questions with bytes-per-term, not Big-O.** Naive trie ≈ tens of bytes per character; radix/FST compress to near-raw-text size; sorted arrays are the floor. The number decides the tiering, and tiering decides latency.
3. **Separate the serving path from the learning path.** Keystroke serving must be stateless reads over materialized structures; anything that learns (counters, trending, blocklists) lives in the offline pipeline with its own admission rules. Blurring them is how poisoning and drift get in.
4. **Treat the suggestion list as published content.** Whatever appears there is the system speaking; the design needs removal SLAs, evidence thresholds, and a review path, or it will need them after the incident instead.

## Interview Questions

**Q: Why not just use a hash table keyed by every prefix (store "neo", "neog", ... for every term)?**
A: It works and serves in O(1) — at the cost of materializing every prefix of every term, which multiplies storage by average term length and makes ranking updates touch every prefix's top-k list. It also cannot answer fuzzy or "list all terms under this node" queries without a scan. It is a legitimate space-for-time trade for a small, hot, closed vocabulary; the trie/FST family wins when the dictionary is large or evolving.

**Q: A breaking-news term must appear in suggestions within minutes. Where does it enter your architecture?**
A: Through the online overlay, not the main index: a detector watches query-log share-of-voice against per-term baselines, admits the term under strict evidence rules, and its top-k contribution is patched onto the affected prefix nodes (or merged at serving time) with a short TTL. The main index rebuilds on its normal cadence and absorbs the term permanently only if its sustained volume justifies it — instant response, controlled permanence.

**Q: How do you support typo tolerance without wrecking the exact-prefix hot path?**
A: Keep them separate. Exact prefixes stay on the O(prefix-length) path; the fuzzy path is a different index (character n-grams or a Levenshtein-automaton-over-FST) queried only when exact results are thin or the raw term has no hits, and its candidates are re-scored against edit distance and frequency before being shown. Merging fuzzy results into every keystroke's answer taxes the 99% to serve the 1% — the wrong direction for a 50 ms budget.

**Q: Where do you place caches in an autocomplete serving path, and what is each one's hit pattern?**
A: Client-side memoization of already-typed prefixes (perfect hits as typing deepens), edge/CDN caching of hot prefix responses (the top few thousand prefixes carry most traffic — request-coalescing matters for bursty hot keys), and in-process node-level top-k lists (the materialized ranking itself). The cache hierarchy mirrors any read-heavy system; the autocomplete-specific trick is that cache keys are *prefixes*, so hit rates are extremely skewed and predictable.

## Key Takeaways

- Autocomplete is a prefix-contract system: the data structure must serve "best k under this subtree," and exact-match structures (hash maps) answer a different question.
- Naive tries fail on memory and cache behavior, not on Big-O — radix compression, FSTs, and sorted-array binary search are the production answers.
- Ranking is a materialized view over decayed, success-weighted, debotted query logs; live counters are both a latency and a poisoning liability.
- Sharding is by prefix (locality), latency is bought with a cache hierarchy plus debouncing, and fuzzy matching is a separate index re-ranked against exact results.
- Suggestions are published content: admission thresholds, blocklists at index time, and personal-reorder-only personalization are correctness features, not extras.

## Cross-References

- [Hash Tables](./hash-tables.md) — the exact-match structure whose limits motivate every prefix structure in this chain.
- [Search & Inverted Index](../connection-atlas/search-inverted-index.md) — the sibling retrieval map: how full search indexes relate to completion structures.
- [Binary Search vs Hashing](../why-not-handbook/binary-search-vs-hashing.md) — the structure comparison behind the sorted-array alternative.
- [Rate Limiter Design](./rate-limiter-design.md) — the admission-control ladder applied to the traffic that feeds suggestions.
- [Typeahead](../../interview/system-design/typeahead.md) — the requirements-and-estimates version of this design.
- [Search](../../interview/system-design/search.md) — the full search-system ladder this feature front-ends.
- [Redis Sorted Sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/) — the lexicographic-range primitive that implements the sorted-dictionary design at single-node scale.
- [Elasticsearch Suggesters](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-suggesters.html) — the completion-suggester machinery behind FST-based serving.
