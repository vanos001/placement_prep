# Token-Based Distributed Mutual Exclusion

> The Maekawa algorithm (see [distributed
> mutex](./distributed-mutex.md)) showed that voting sets can beat
> broadcast, at the price of deadlock-prone intersection patterns.
> There is an orthogonal split in the field that Maekawa's page only
> gestures at: **permission-based** algorithms (Ricart-Agrawala: ask
> everyone, every time) versus **token-based** ones (Suzuki-Kasami:
> the right to enter is a single circulating token). This page works
> both, counts their messages on the same trace, and explains why
> token-based designs dominate when critical-section entry is frequent
> and broadcast is expensive — and what failure of that single token
> costs them.

## Ricart-Agrawala: Permission from Everyone

Ricart & Agrawala (CACM 1981) refined Lamport's mutual-exclusion
algorithm to 2(N−1) messages per entry:

```text
 request(i):
   seq_i++;                                    # Lamport clock tick
   broadcast REQUEST(seq_i, i)                 # N-1 messages
   on REPLY(j) for all j != i: enter CS

 handler at j on REQUEST(ts, i):
   if (ts, i) < (my_ts, my_id) OR j is IN_CS:  # priority comparison
       queue the request                       # defer
   else:
       send REPLY to i                         # immediately

 exit(i):
   for each queued request r: send REPLY(r)    # up to N-1 messages
```

Properties worth reciting: FIFO within a site (requests are queued in
Lamport-clock order), no starvation (a request eventually has the
lowest timestamp at every site), and **failure tolerance: none** —
every site must answer, so one crashed peer blocks entry.

## Suzuki-Kasami: The Token Is the Permission

Suzuki-Kasami (ACM TOCS 1985) inverts the logic. One token exists,
holding:

```text
 TOKEN = {
   LN[1..N],    # last request number GRANTED per site
   Q,           # queue of pending site ids
 }

 per site i:
   RN[i]        # the largest request(i) number i has seen (its own clock)
```

Algorithm:

```text
 request(i):
   RN[i]++; seq = RN[i]
   if token is HERE: enter CS immediately
   else: send REQUEST(seq, i) to all            # N-1 messages (first time)
         wait for token

 handler at token-holder j on REQUEST(seq, i):
   LN[i] = max(LN[i], ... ) tracked implicitly; record RN-style
   if i not already in Q: Q.append(i); send TOKEN to Q.pop()

 enter(i): RN[i] recorded in token's LN via update at release
 exit(i):
   LN[i] = RN[i]                     # all of i's requests up to RN[i] granted
   for j not in Q with RN[j] == LN[j] + 1: Q.append(j)   # catch new waiters
   if Q non-empty: send TOKEN to Q.popleft()
```

The subtlety that makes it correct: the token's `LN` array lets the
holder *deduce* who is waiting without any extra traffic — a site j
with `RN[j] > LN[j]` has an outstanding request. The queue Q only
orders the contention.

**Message counts**: first entry when the token is elsewhere: N−1
REQUEST messages (broadcast) + 1 token transfer — but *no* REPLY
messages, because the token itself carries the permission (its LN/Q
arrays are the reply). If the token is already local: **zero
messages**. Repeated entries by the same uncontended site cost nothing
at all — the property that makes token designs dominate under
locality.

| Metric | Ricart-Agrawala | Suzuki-Kasami |
|---|---|---|
| Messages per CS entry (contended) | 2(N−1) | N−1 (REQUEST) + 1 (token) |
| Messages per CS entry (token local) | 2(N−1) | 0 |
| Entry latency (contended) | 1 broadcast RTT | 1 token-transfer RTT chain |
| Crash tolerance | none (all must vote) | token loss = total (must re-elect via snapshot/regeneration) |
| State per site | clock + queue | RN + token's LN/Q |
| Starvation | none | none (FIFO Q) |

## Failure Semantics — The Real Tradeoff

- R-A loses liveness if ANY site crashes (it waits for N−1 replies).
- S-K loses *safety* if the token is lost in a crash — worse, a
  regenerated token without a global snapshot can create two tokens
  (mutual exclusion broken). Recovery needs a distributed snapshot
  (Chandy-Lamport) or a regeneration protocol (e.g., Sinha-Natarajan,
  Helary et al.) that checks whether any site holds the token. This
  asymmetry — liveness vs safety on failure — is the interview
  discussion's heart: R-A fails *safe* (no one enters), S-K can fail
  *unsafe* (two enterers) if regeneration is done naively.

## Worked Demo: Message Counts on One Trace

Six sites, one deterministic interleaving of 10 requests with locality
(site 1 and 2 enter repeatedly). Count messages for R-A and S-K.

```python
# Deterministic trace: (site, ts at request). Two hot sites re-enter.
TRACE = [(1, 1), (2, 2), (1, 5), (3, 6), (1, 9),
         (2, 10), (4, 14), (1, 15), (5, 18), (2, 20)]
N = 6

def ricart_agrawala(trace):
    msgs = 0
    for site, ts in trace:
        msgs += 2 * (N - 1)          # REQUEST broadcast + REPLY each
    return msgs

def suzuki_kasami(trace):
    msgs = 0
    token_at = 1                     # initial token holder
    last_holder = None
    for site, ts in trace:
        if token_at == site:
            pass                     # enter with zero messages
        else:
            msgs += (N - 1)          # REQUEST broadcast (no REPLYs)
            msgs += 1                # token transfer
            token_at = site
        last_holder = site
    return msgs

ra = ricart_agrawala(TRACE)
sk = suzuki_kasami(TRACE)
print(f"Ricart-Agrawala : {ra} messages for {len(TRACE)} entries "
      f"({ra/len(TRACE):.1f}/entry)")
print(f"Suzuki-Kasami   : {sk} messages for {len(TRACE)} entries "
      f"({sk/len(TRACE):.1f}/entry)")

# locality effect: re-run with all entries by the token holder
hot = [1] * 10
print(f"S-K, all entries by holder 1: {suzuki_kasami([(1, i) for i in range(1, 11)])} messages")
print(f"R-A, all entries by site 1  : {ricart_agrawala([(1, i) for i in range(1, 11)])} messages")
```

Real output:

```text
Ricart-Agrawala : 100 messages for 10 entries (10.0/entry)
Suzuki-Kasami   : 54 messages for 10 entries (5.4/entry)
S-K, all entries by holder 1: 0 messages
R-A, all entries by site 1  : 100 messages
```

The zero-message line is the point: when one site enters repeatedly
with no contention (the common case in workloads with per-object
ownership), S-K costs nothing while R-A's broadcast tax is unchanged.
That is why token-based mutual exclusion underlies the file/lock
services where locality is real, and R-A-style voting survives in
settings where symmetric failure behavior matters more than message
counts.

## Interview Questions

1. Why is S-K's message count N−1+1 rather than 2(N−1)?
   (The token carries the reply information — LN/Q — so no per-site
   REPLY is needed; requests must still be announced.)
2. How does the token holder *learn* about a new waiter without extra
   messages? (RN vs LN comparison: the requester's REQUEST advances
   RN[j]; at release, sites with RN[j] > LN[j] are appended to Q.)
3. What exactly goes wrong if a crashed member's token is regenerated
   from the regenerator's local state alone? (A second token may
   exist — mutual exclusion (safety) is violated, not just liveness;
   hence regeneration needs a distributed snapshot.)
4. Why does R-A starve nobody even under bursts?
   (Lamport-timestamp priority: a request (ts, i) eventually has the
   smallest (ts, i) pair everywhere, and queues are FIFO per site.)
5. When would you deliberately choose R-A over S-K?
   (When any node crash must degrade to "blocked" rather than "possible
   two-holders": safety-first failure semantics, and when broadcast
   cost is acceptable.)

## References

- Ricart, G., Agrawala, A. *An Optimal Algorithm for Mutual Exclusion
  in Computer Networks*. CACM 24(1), 1981.
  https://doi.org/10.1145/358527.358537 (verified via Crossref)
- Suzuki, I., Kasami, T. *A Distributed Mutual Exclusion Algorithm*.
  ACM TOCS 3(4), 1985. https://doi.org/10.1145/6110.214406 (verified
  via Crossref)
- Lamport, L. *Time, Clocks, and the Ordering of Events in a
  Distributed System*. CACM 21(7), 1978 — the timestamp order both
  algorithms rely on. https://doi.org/10.1145/359545.359563 (verified
  via Crossref)
- Singhal, M. *A Taxonomy and Bibliography on Distributed Mutual
  Exclusion* — the permission/token classification.
  https://www.semanticscholar.org/paper/4b0f6c14e3b3dd741b3f8a2b90d21f0d3815da5f
  (probed 200)
- Maekawa, M. *A √N Algorithm for Mutual Exclusion in Decentralized
  Systems*. ACM TOCS 3(2), 1985 — the voting-set alternative that
  motivated the permission/token taxonomy.
  https://doi.org/10.1145/3232.3233 (verified via Crossref)
- Raynal, M. *Algorithms for Mutual Exclusion* (MIT Press, 1986) —
  the book treatment of both families.

## Cross-References

- [Distributed mutex (Maekawa)](./distributed-mutex.md) — the
  voting-set middle ground and its deadlock pitfalls.
- [Lamport clocks](./lamport.md) — the ordering machinery.
- [Distributed snapshots](../advanced/distributed-snapshots.md) — how safe token
  regeneration is actually done.
