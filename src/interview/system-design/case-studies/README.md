# System Design Case Studies

## Overview

This section contains full interview-format system design case studies: each one walks the six-step framework from requirements to follow-ups with explicit numbers, trade-off decisions, and deep dives, the way a strong candidate would drive a 45-minute design round. The pages complement [real-world architectures](../real-world/netflix.md), which analyze how actual companies built things; these pages optimize for *practicing the design conversation itself*.

Each case study follows the same structure so you can drill them like past papers:

1. **Requirements & estimation** — functional/non-functional, QPS, storage, bandwidth math
2. **API + data model** — concrete schemas, not hand-waving
3. **High-level architecture** — one diagram you should be able to redraw from memory
4. **Deep dives** — the two or three genuinely hard parts, with alternatives compared
5. **Bottlenecks & follow-ups** — where the design bends, what the interviewer asks next

## The case studies

| Case study | Core difficulty | Classic probes |
|---|---|---|
| [Ticketmaster](./ticketmaster.md) | seat inventory without oversell under flash demand | locking model, waiting rooms, idempotent payment |
| [Stock exchange](./stock-exchange.md) | deterministic matching at microsecond budgets | order book structures, sequencer, DR |
| [Ad tech / RTB](./ad-tech.md) | 100ms auction with budget pacing | profile caches, frequency capping, attribution |
| [Distributed task scheduler](./distributed-task-scheduler.md) | lease-based distributed cron | at-least-once vs exactly-once, DAG orchestration |
| [Metrics & monitoring](./metrics-monitoring.md) | write-heavy TSDB at trillions of samples | pull vs push, Gorilla encoding, downsampling |
| [Distributed tracing](./distributed-tracing.md) | tracing without drowning in spans | head vs tail sampling, propagation, storage engines |
| [Log analytics pipeline](./log-analytics.md) | firehose ingestion → queryable store | label models vs inverted index, retention tiers |
| [Live auction platform](./live-auction.md) | real-time bid state + fair soft close | websocket fanout, clock skew, sharded rooms |
| [ML feature store](./feature-store.md) | training/serving consistency | point-in-time correctness, online/offline duality |
| [CI/CD system](./ci-cd-system.md) | build DAGs at org scale | artifact CAS, runner pools, merge queues, canary |

## How to practice

- Read the case, then close it and sketch the architecture diagram from memory.
- Do the estimation section with your own numbers first; compare against the page and note where your order-of-magnitude slipped.
- For every deep dive, articulate the rejected alternative and *why* out loud — that reasoning, not the final diagram, is what the interviewer scores.
- Cross-check the primitives each case leans on: [consistency patterns](../consistency-patterns.md), [backpressure](../backpressure.md), [messaging systems](../hld/messaging-systems.md), and the [probabilistic data structures](../probabilistic-data-structures.md) that show up in every counting-adjacent design.

## Cross-References

- [Design Framework](../framework.md) — the six-step method these pages apply
- [Real-World Architectures](../real-world/netflix.md) — how real companies actually built related systems
- [HLD Core Topics](../hld/README.md) — the building blocks referenced repeatedly
- [Metrics & Monitoring](./metrics-monitoring.md) — pairs with the SRE section of the book
- [Backpressure](../backpressure.md) — the load-shedding vocabulary used throughout
