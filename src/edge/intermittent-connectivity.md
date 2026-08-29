# Intermittent Connectivity and Disconnect-Tolerant Systems

Most distributed-systems material assumes the link is up and merely slow. Offline-first design assumes the opposite: hours without a network, writes continuing on both ends, and a reconciliation moment when the link returns. This page is about that moment -- the local source of truth, store-and-forward relays, reconnect-time conflict resolution, idempotent replay, and the UX and test techniques that hold it together. The CRDT merge algebra referenced below is derived in [CRDTs](../distributed/fundamentals/crdts.md); the protocol alphabet (MQTT, CoAP, LwM2M) lives in the [edge section](iot-protocols.md) and is not repeated here.

## Four failure modes that look alike and are not

| Mode | Client-visible signature | Detection signal | Core remedy |
| --- | --- | --- | --- |
| Clean offline | connect() fails immediately | DNS / socket errors | local store + outbox queue |
| Captive portal | HTTP 200s, DNS hijacked | probe returns HTML, not API JSON | RFC 8908 API poll, user nudge |
| Scheduled partition | up for a window, then gone | known contact schedule | store-and-forward + bundle lifetime |
| Degraded link | high loss, long RTT | loss and RTT measurements | idempotent retries, backoff |

The portal row deserves emphasis: the intercept answers every request with a 200 and a login page, so naive reachability checks pass while every API call fails. RFC 7710 lets the network advertise the portal URI via DHCP or router advertisements; RFC 8908 defines a JSON API whose `"captive"` boolean and portal URL let clients distinguish "no network" from "a network that demands a login".

## Offline-first: the local store is the source of truth

```text
        ONLINE WRITE PATH                    OFFLINE WRITE PATH
 UI --> API client --> server --> ack    UI --> durable local store (write #1)
                                                  + outbox entry (op id, payload)
                                         UI reads are served from the store
                                         row is flagged "pending" (optimistic)
        reconnect: sync engine drains outbox -> server -> reconciler
                   -> server state -> patch applied to local store
```

The local store must provide three properties: durability (the write survives a crash before any ack), queueing (operations carry stable op ids so they can be replayed and deduped), and versioning (so the reconciler can tell concurrent writes from causally ordered ones). Web front ends reach for IndexedDB, native apps for SQLite -- see [IndexedDB](../frontend/indexed-db.md) and [Mobile Engineering](../mobile/mobile-engineering.md). Managed stacks make the shape explicit: the Firebase Realtime Database client "automatically keeps a queue of all write operations that are performed while your app is offline", persisting it to disk and resending everything on reconnect. Service-worker background sync gives web apps a weaker, browser-scheduled version of the outbox ([Service Workers](../web-development/service-workers.md)).

## Store-and-forward: DTN and the Bundle Protocol

Delay-Tolerant Networking is the extreme end of this spectrum: nodes relay data across contacts that are scheduled (a LEO satellite pass), opportunistic (two phones in range), or predicted from history -- the contact taxonomy is in the DTN architecture RFC. The lineage:

- 2003: Fall's "A Delay-Tolerant Network Architecture for Challenged Internets" (SIGCOMM 2003) frames the problem and the store-carry-forward answer.
- RFC 4838 (Informational, April 2007; Cerf, Burleigh, Hooke): the architecture -- late binding, custody, the contact classes above.
- RFC 5050 (Experimental, November 2007): Bundle Protocol version 6.
- RFC 9171 (Standards Track, January 2022): BP version 7, the production-grade rewrite: CBOR-encoded bundles (RFC 8949), an immutable primary block with CRCs, node IDs distinct from endpoint IDs, and delivery feedback via bundle status reports rather than in-band acks. Custody transfer is gone from the core protocol, migrated to a bundle-in-bundle encapsulation spec (BIBE, referenced as work in progress by RFC 9171).
- Security and transport: RFC 9172 (BPSec integrity/confidentiality blocks) with RFC 9173 default security contexts; RFC 9174 defines the TCP Convergence Layer, version 4.

Two mechanics worth internalizing. First, every bundle carries a lifetime, and a node "need no longer retain or attempt to forward" a bundle whose age exceeds it -- TTL is part of the wire format. Second, the source controls feedback granularity with per-event status-report request flags: reception, forwarding, delivery, and deletion (with reason codes). Relays are stateful buffers, not routers:

```text
  node A --contact 1--> node B <. no contact .> node C --contact 2--> node D
  [bundle]              [bundle stored,        [bundle stored]      [delivered;
   lifetime=3600s        age grows]             age grows]           status report
   age=0                                                             to source]
  relay storage is the network's buffer; a full buffer or an expired
  lifetime is the DTN equivalent of a dropped packet
```

## When both sides wrote: reconnect-time conflict resolution

Last-writer-wins on wall clocks is the default answer and the worst one. A skewed clock silently inverts causality -- the device that wrote later in the causal chain loses because its clock is behind -- and the loser vanishes without a trace: no conflict is recorded, nothing is recoverable. LWW survives here for the same reason it survives in multi-primary database replication ([Multi-Primary Replication](../distributed/replication/multi-primary.md)): cheap and always terminating.

| Strategy | Winner rule | Silent-loss risk | Where you meet it |
| --- | --- | --- | --- |
| LWW on wall clocks | max timestamp | yes; skew inverts intent | Firestore per-document writes |
| Version vectors + manual merge | app resolves concurrent pair | flagged, not silent | Dynamo-style systems |
| CRDT merge | join-semilattice laws | no; merge is lossless by construction | collaborative editors |
| Deterministic winner + conflict list | rev-order rule; losers kept | no; losers remain readable | CouchDB / PouchDB replication |
| Tombstone-wins | delete beats update | no; deletes converge | Couchbase Lite pull replication |

Rows two through four rest on the state-versus-operations choice CRDTs face (the merge laws -- commutative, associative, idempotent -- are in [CRDTs](../distributed/fundamentals/crdts.md), not re-derived here). Op-based sync ships small deltas but needs reliable, causally ordered delivery or receive-side dedup; state-based anti-entropy is idempotent but fat; delta-state CRDTs ship compact diffs and fall back to full state on suspicion of loss. The model below reconciles the *same* divergence both ways:

```python
"""Divergence + reconciliation: wall-clock LWW vs version-vector merge."""
class Op:
    def __init__(self, node, seq, value, ts, vc):
        self.node, self.seq = node, seq
        self.value, self.ts, self.vc = value, ts, vc

def dominates(a, b):
    return all(a.get(k, 0) >= b.get(k, 0) for k in set(a) | set(b))

def concurrent(a, b):
    return not dominates(a, b) and not dominates(b, a)

# B writes "archived" -> its state syncs to A -> PARTITION -> A writes
# "shipped" (causally later, clock 20 ms behind B's) -> B writes "reopened".
A_OPS = [Op("A", 1, "shipped", 1000, {"A": 1, "B": 1})]
B_OPS = [Op("B", 1, "archived", 1020, {"B": 1}),
         Op("B", 2, "reopened", 1050, {"B": 2})]
pool = A_OPS + B_OPS
a_op = A_OPS[0]

lww_winner = max(pool, key=lambda o: o.ts)   # (a) global max wall clock
frontier = [o for o in pool                  # (b) ops nobody dominates
            if not any(o is not p and dominates(p.vc, o.vc) for p in pool)]
conflict = concurrent(frontier[0].vc, frontier[1].vc)
tiebreak = max(frontier, key=lambda o: (sum(o.vc.values()), o.node))

# each replica merges in the other side's ops -> durable per-replica logs
log_a = sorted((o.node, o.seq, o.value) for o in A_OPS + B_OPS)
log_b = sorted((o.node, o.seq, o.value) for o in B_OPS + A_OPS)

rows = [
    ("LWW (max wall clock):", "op-log merge (version vectors):"),
    (f"winner: #{lww_winner.node}{lww_winner.seq} '{lww_winner.value}'",
     f"frontier: #{frontier[0].node}{frontier[0].seq} vs "
     f"#{frontier[1].node}{frontier[1].seq}"),
    (f"  ts={lww_winner.ts} beats ts={a_op.ts}",
     f"  vcs {frontier[0].vc} vs {frontier[1].vc}"),
    (f"loser: #{a_op.node}{a_op.seq} '{a_op.value}' -- causally",
     f"concurrent -> {'CONFLICT detected' if conflict else 'ordered'}"),
    ("  LATER write, skewed clock behind)",
     f"tie-break (vsum, node id): #{tiebreak.node}{tiebreak.seq} "
     f"'{tiebreak.value}'"),
    (f"replica A shows: '{lww_winner.value}'",
     f"replica A shows: '{tiebreak.value}'"),
    (f"replica B shows: '{lww_winner.value}'",
     f"replica B shows: '{tiebreak.value}'"),
    ("A's op survives in logs: NO (no trace)",
     "A's op survives in logs: yes"),
    ("replica logs identical: yes (lossy)",
     f"replica logs identical: {'yes' if log_a == log_b else 'no'}"),
    ("verdict: silent data loss", "verdict: surfaced conflict, recoverable"),
]
for left, right in rows:
    print(f"{left:<40} | {right}")
```

Output (both columns reconcile to identical state; only one keeps the loser):

```text
LWW (max wall clock):                    | op-log merge (version vectors):
winner: #B2 'reopened'                   | frontier: #A1 vs #B2
  ts=1050 beats ts=1000                  |   vcs {'A': 1, 'B': 1} vs {'B': 2}
loser: #A1 'shipped' -- causally         | concurrent -> CONFLICT detected
  LATER write, skewed clock behind)      | tie-break (vsum, node id): #B2 'reopened'
replica A shows: 'reopened'              | replica A shows: 'reopened'
replica B shows: 'reopened'              | replica B shows: 'reopened'
A's op survives in logs: NO (no trace)   | A's op survives in logs: yes
replica logs identical: yes (lossy)      | replica logs identical: yes
verdict: silent data loss                | verdict: surfaced conflict, recoverable
```

The point is not that the merge column picks a "better" value -- its tie-break is as arbitrary as any -- but that concurrent writes are *detectable* (both version vectors sit in the frontier) and *survivable* (both ops stay in both replicas' logs), versus LWW's unmarked grave.

## Sync engines in the wild

| Engine | Offline store | Reconnect behavior | Conflict handling |
| --- | --- | --- | --- |
| Firebase RTDB | in-memory queue; on-disk with persistence | queued ops resent when online | queued replay; server timestamps for ordering |
| Cloud Firestore | local cache of active data | cache readable/writable offline, synced later | "For multiple changes to the same document, it's last write wins" |
| CouchDB / PouchDB | append-only revision trees | pull/push of missing revisions | deterministic winner; losers kept under `_conflicts` |
| Couchbase Lite | embedded document store | resolution during pull replication | most-revisions wins; tombstone beats update |

CouchDB's model is the honest one: it "picks one arbitrary revision as the winner, using a deterministic algorithm" and keeps every loser as a conflicting revision, so applications can surface or merge them later; PouchDB implements that replication algorithm unchanged and separates immediate conflicts (409 on a stale `_rev`) from eventual ones found at replication time. The Ink & Switch "local-first software" paper argues this family of designs -- local source of truth plus mergeable state -- is also the multi-device UX endgame.

## Reconnect queues: idempotent replay and dedup

Reconnect delivery is at-least-once by construction: the client cannot distinguish "the server never got it" from "the ack was lost", so it retries, so duplicates arrive. The server therefore needs an apply-once layer keyed by the client-generated op id (or a dedup table), and outbox operations should be expressed as idempotent payloads (a target state) rather than deltas (increment by 5) whenever possible. This is the same exactly-once-versus-idempotency tension message queues solve with consumer offsets ([Message Queues](../distributed/messaging/queues.md)).

```python
"""Outbox replayed at-least-once: naive apply vs idempotent apply."""
OPS = [("op-1", "set_qty", 3), ("op-2", "incr_total", 20),
       ("op-3", "set_note", "gift wrap"), ("op-4", "incr_total", 30), ("op-5", "set_qty", 0)]
BY_ID = dict((o[0], o) for o in OPS)

# at-least-once: ACKs for op-2 and op-4 were lost -> the client retries
# them after reconnect, so each arrives twice
DELIVERY = ["op-1", "op-2", "op-2", "op-3", "op-4", "op-4", "op-5"]

def replay(idempotent):
    seen, dups, apps = set(), 0, 0
    total, qty, note = 0, None, None
    for op_id in DELIVERY:
        if idempotent and op_id in seen:
            dups += 1
            continue
        seen.add(op_id)
        apps += 1
        _, kind, arg = BY_ID[op_id]
        if kind == "incr_total":
            total += arg
        elif kind == "set_qty":
            qty = arg
        elif kind == "set_note":
            note = arg
    return total, qty, note, dups, apps

EXPECTED = 20 + 30
n_total, n_qty, n_note, _, n_apps = replay(idempotent=False)
i_total, i_qty, i_note, i_dups, i_apps = replay(idempotent=True)

print(f"outbox: {len(OPS)} unique ops -> {len(DELIVERY)} at-least-once deliveries")
print(f"intended total: {EXPECTED}")
print(f"naive apply    : total={n_total} qty={n_qty} note='{n_note}' "
      f"apps={n_apps} -> correct={n_total == EXPECTED}")
print(f"idempotent apply: total={i_total} qty={i_qty} note='{i_note}' "
      f"apps={i_apps} deduped={i_dups} -> correct={i_total == EXPECTED}")
```

```text
outbox: 5 unique ops -> 7 at-least-once deliveries
intended total: 50
naive apply    : total=100 qty=0 note='gift wrap' apps=7 -> correct=False
idempotent apply: total=50 qty=0 note='gift wrap' apps=5 deduped=2 -> correct=True
```

## UX patterns

- Optimistic UI: commit the intended result to the UI immediately, flag it pending, roll back on server rejection -- Apollo's `optimisticResponse` documents the canonical shape.
- Tombstones: deletion markers that replicate like writes, so other replicas remove the row instead of resurrecting it; CouchDB keeps the deletion as a revision in the tree, and Couchbase Lite's rule makes tombstone-wins explicit.
- Pending-state affordances: badges and per-row "syncing" states so users understand offline writes are queued, not lost.
- Offline banners that distinguish "no network" from "captive portal", because the user remedy differs (retry vs. log in).

## Mobile and edge realities

Devices switch radios mid-transfer (WiFi to cellular), which kills every open socket; sync must resume from the outbox rather than restart the world. OS background-execution limits mean the sync engine may be frozen for hours, so outbox sizing must assume the worst-case offline window, not the mean. Gateways in industrial deployments buffer store-and-forward queues when the backhaul is down and replay to cloud ingest on restore ([Embedded IoT](../embedded-systems/iot.md)); battery-powered sensors use the same buffering so one TX window covers many samples. The captive-portal trap recurs with split whitelists: the app's telemetry host may be blocked while the portal-check domain resolves, producing false "online" confidence.

## Testing disconnects

- `tc netem` (Linux traffic control): injects delay, loss, duplicate, reorder, and corrupt events on a qdisc.
- Toxiproxy: a TCP proxy with runtime-toggleable "toxics" (timeout, bandwidth limit, slicer).
- Chaos Mesh NetworkChaos: Kubernetes-native partitions, loss, and partition-and-heal schedules.

The scenario matrix that matters: drop the connection between request and response (forces duplicate replay), skew the client clock minutes back (forces LWW inversions), hold the outage past outbox capacity (forces queue-eviction policy), insert a portal interstitial (forces detection), and replay the same delivery twice (forces dedup). Connectivity detection is the easy half; reconciliation is where the bugs live.

## Failure modes

- LWW plus clock skew silently discards the causally latest write.
- Delta semantics in outbox ops multiply under at-least-once replay.
- Collecting tombstones or vector history before the slowest rejoiner syncs resurrects deleted state (GC caveats in [CRDTs](../distributed/fundamentals/crdts.md)).
- Unbounded outbox growth turns a long outage into disk exhaustion.
- Reachability checks that pass behind captive portals gate work on a false online signal.
- "CRDTs remove conflicts" is over-read: they remove convergence conflicts, not business conflicts (two people editing one budget cell).

## Interview questions

- Why is at-least-once delivery unavoidable on reconnect, and what does the server need to absorb it?
- A causally later offline write is lost under LWW -- walk through the mechanism and two defenses.
- When would you choose state-based sync over op-based, given bandwidth and delivery-guarantee trade-offs?
- What does a tombstone protect against, and when is it safe to collect?
- How would you distinguish a captive portal from true offline in code?

## Cross-references

- [CRDTs](../distributed/fundamentals/crdts.md) -- merge laws, delta modes, GC caveats.
- [Multi-Primary Replication](../distributed/replication/multi-primary.md) -- the always-on cousin of the same conflict problem.
- [Message Queues](../distributed/messaging/queues.md) -- delivery semantics and idempotent consumers.
- [Edge Computing](edge-computing.md) -- where the offline layer sits in a fleet design.
- [MQTT Internals](mqtt-internals.md) and [CoAP Deep Dive](coap-deep.md) -- persistent sessions and observe/blockwise for constrained links.
- [PWA](../mobile/pwa.md) and [Service Workers](../web-development/service-workers.md) -- browser offline storage and background sync mechanics.
- [Graceful Degradation](../backend/patterns/graceful-degradation.md) -- server-side degradation when clients cannot reach you.

## References

1. Birrane et al., "Bundle Protocol Version 7", RFC 9171 (Standards Track) -- <https://www.rfc-editor.org/rfc/rfc9171.txt>
2. Cerf, Burleigh, Hooke et al., "Delay-Tolerant Networking Architecture", RFC 4838 -- <https://www.rfc-editor.org/rfc/rfc4838.txt>; Scott, Burleigh, "Bundle Protocol Specification" (BPv6), RFC 5050 -- <https://www.rfc-editor.org/rfc/rfc5050.txt>
3. Birrane, McKeever, "Bundle Protocol Security (BPSec)", RFC 9172 -- <https://www.rfc-editor.org/rfc/rfc9172.txt>; Birrane, White, Heiner, "Default Security Contexts for BPSec", RFC 9173 -- <https://www.rfc-editor.org/rfc/rfc9173.txt>; Sipos, Demmer, Ott, "Delay-Tolerant Networking TCP Convergence-Layer Protocol Version 4", RFC 9174 -- <https://www.rfc-editor.org/rfc/rfc9174.txt>
4. Kumari, "Captive-Portal Identification Using DHCP or Router Advertisements (RAs)", RFC 7710 -- <https://www.rfc-editor.org/rfc/rfc7710.txt>; Pauly, Thakore, "Captive Portal API", RFC 8908 -- <https://www.rfc-editor.org/rfc/rfc8908.txt>
5. Fall, "A Delay-Tolerant Network Architecture for Challenged Internets", SIGCOMM 2003 -- <https://doi.org/10.1145/863955.863960>
6. Firebase: RTDB offline capabilities -- <https://firebase.google.com/docs/database/android/offline-capabilities>; Firestore "Access data offline" -- <https://firebase.google.com/docs/firestore/manage-data/enable-offline>
7. CouchDB, "Replication and conflict model" -- <https://docs.couchdb.org/en/stable/replication/conflicts.html>; PouchDB, "Conflicts" guide -- <https://pouchdb.com/guides/conflicts.html>
8. Couchbase, "Handling Data Conflicts" (Couchbase Lite) -- <https://docs.couchbase.com/couchbase-lite/current/java/conflict.html>
9. Kleppmann, Wiggins, van Hardenberg, McGranaghan, "Local-first software: You own your data, in spite of the cloud", Onward! 2019 -- <https://doi.org/10.1145/3359591.3359737>
10. Shapiro, Preguica, Baquero, Zawirski, "Conflict-free Replicated Data Types" (INRIA report 7687) -- <https://hal.inria.fr/inria-00555588/document>
11. Apollo GraphQL, "Optimistic UI" -- <https://www.apollographql.com/docs/react/performance/optimistic-ui/>
12. tc-netem(8) -- <https://man7.org/linux/man-pages/man8/tc-netem.8.html>; Toxiproxy -- <https://github.com/Shopify/toxiproxy>; Chaos Mesh -- <https://chaos-mesh.org/docs/simulate-network-chaos-on-kubernetes/>
