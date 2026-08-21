# Strangler Fig Pattern

The Strangler Fig is an incremental migration pattern for replacing a legacy system: put a facade in front of the old system, route new functionality to a new implementation alongside the old, and gradually "strangle" the old code out of existence. When the old system is no longer needed, you delete it. The pattern was named by Martin Fowler in 2004 after a strangler fig tree he saw in Australia — a seed sprouts in the upper branches of a host tree, grows its own trunk down to the ground, and eventually the host tree rots away inside the new trunk, leaving the fig standing in its place. The pattern is the same: the new system grows around the old, the old shrinks, and at the end you remove the old.

## Why the pattern exists

The pattern is a direct answer to the **big-bang rewrite** failure mode. A big-bang rewrite means: stop adding features to the old system, build a replacement from scratch, switch over in one deployment. Empirically this almost always goes wrong, for four reasons:

1. **You don't know the old system's full behavior.** The legacy code encodes business rules in branches nobody remembers. Re-implementing them from spec means you will get some wrong, and the bugs surface only after cutover.
2. **The business cannot freeze.** Stakeholders will not halt new features for 18 months while you rebuild. The new system falls behind, and when it ships it is already wrong for current needs.
3. **There is no rollback.** The day the new system goes live, every bug is a sev1 with no escape hatch except "roll back to old system" — which is what you were trying to escape.
4. **The team that builds the new system is not the team that maintains the old.** Knowledge transfer is asymmetric. By the time the new system is "done," the people who understood the old system have left.

The Strangler Fig avoids all four by **never stopping the old system cold**. The old system keeps running and serving users. The new system grows up around it, one route at a time. At every step the old system is the safety net; if the new system misbehaves for a route, you flip that route back.

## The routing mechanism

The pattern hinges on one piece: a **routing facade** that decides, per request, whether the old or new system handles it. Three routing mechanisms are common.

### URL-based routing

The cleanest. The facade is an HTTP router. Different URL prefixes go to different backends. Old `/api/v1/orders` continues to the legacy monolith; new `/api/v2/orders` goes to the new service. During migration, clients are progressively moved from v1 to v2.

```
                    ┌─────────────────────────────┐
   client  ───────▶ │        Ingress / Facade      │
                    └──────────┬──────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
     /api/v1/*           /api/v2/*           /api/v3/*
            │                  │                  │
            ▼                  ▼                  ▼
     ┌─────────────┐  ┌─────────────────┐  ┌────────────┐
     │ Legacy      │  │ New Order Svc   │  │ New Carts  │
     │ Monolith    │  │ (migrated)      │  │ Svc (new)  │
     └─────────────┘  └─────────────────┘  └────────────┘
```

This is brittle because it forces clients to migrate URLs. But it is the simplest to reason about and trivial to reverse.

### Header / cookie / feature-flag based routing

The facade routes the **same URL** to old or new based on a header or feature flag. Internal employees get the new system first; then 1% of users; then 5%; then 100%.

```python
# Facade: FastAPI / Starlette router
from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()
LEGACY = "http://legacy-monolith.internal"
NEW = "http://new-orders-svc.internal"

@app.api_route("/{path:path}", methods=["GET","POST","PUT","DELETE"])
async def router(request: Request, path: str):
    # Feature flag: percentage rollout to new system
    rollout_pct = flag_service.get("orders-v2-rollout", default=0)
    user_id = request.headers.get("X-User-Id", "")
    bucket = (hash(user_id) % 100) + 1  # 1..100, stable per user

    target = NEW if bucket <= rollout_pct else LEGACY
    # Force-override for canary testing
    if request.headers.get("X-Backend") == "new":
        target = NEW

    async with httpx.AsyncClient(timeout=5.0) as c:
        upstream = await c.request(
            request.method, f"{target}/{path}",
            headers=request.headers.raw, content=await request.body())
    return Response(content=upstream.content,
                    status_code=upstream.status_code,
                    headers=dict(upstream.headers))
```

The key property is **stable bucketing**: a given user always lands on the same backend during a rollout window, so they do not see inconsistency between requests. Changing `rollout_pct` from 1 to 5 to 25 to 100 moves traffic progressively. A `kill switch` flag (set `rollout_pct = 0`) returns all traffic to legacy in one config change, with no deploy.

### Domain-capability routing

For non-HTTP systems (batch jobs, event consumers), routing is by topic or queue. The old consumer and new consumer both subscribe to the same Kafka topic during migration, with the old consumer's writes going to the legacy database and the new consumer's writes going to the new database. A backfill job reconciles them. Eventually the old consumer is unsubscribed.

This is the same idea, applied to async flows.

## The two-phase deployment

The pattern always deploys in two phases.

**Phase 1 — shadow / parallel.** The new system is deployed alongside the old, and the facade **copies** traffic to both (shadow traffic). The new system processes requests and the responses are compared with the old system's responses. Discrepancies are logged but not returned to users. This is the period where you discover the schemas are subtly different, the timezone handling is wrong, the new auth library accepts tokens the old rejected, etc.

```
   request ──┬──▶ LEGACY ──▶ response ──▶ user
             │
             └──▶ NEW (shadow) ──▶ comparator ──▶ metrics
                                                  │
                                                  ▼
                                          diff rate, latency,
                                          schema mismatches
```

**Phase 2 — incremental switch.** When the shadow comparison shows acceptable agreement (typically <0.1% meaningful diff), the facade begins sending real traffic to the new system: 1% → 5% → 25% → 50% → 100%. At each step, error rate, latency, and business metrics (conversion, revenue) are watched against SLO. If the new system regresses, the rollout is paused or rolled back.

When 100% of traffic for a route goes to the new system, the corresponding code in the old system is **dead**. It can be removed. That removal is the strangling.

## Comparison to big-bang rewrite

| Dimension | Big-bang rewrite | Strangler Fig |
|---|---|---|
| Duration | Months to years before any user sees value | Days to weeks per slice; value each slice |
| Risk profile | All-or-nothing at cutover | One slice at a time, always reversible |
| Business freeze | Required | Not required |
| Knowledge transfer | Required up front | Discovered slice by slice |
| Cost | 2× systems during rebuild (old + new) | 2× systems during migration (same cost, shorter) |
| Failure mode | Sev1 at cutover, no rollback | Per-slice rollback to old |
| Schema migration | Big, scary, atomic | Per-slice, backward-compatible |

The Strangler Fig is not free. You pay in three places:

1. **The facade is now critical infrastructure.** It must be highly available, observable, and faster than the legacy it fronts. A naive facade adds latency; a good one adds <5 ms.
2. **You run two systems during migration.** Compute cost, schema compatibility, and bug-count go up temporarily.
3. **You must not regress the legacy during the migration.** If you let the old system rot while building the new, you will be forced to cutover before the new is ready. The discipline: every feature still ships, in the old system if not yet migrated.

## Schema migration: the hidden hard problem

Most strangler projects succeed at code migration and fail at **data migration**. The new system needs its own database schema, but the old system's data is still the source of truth during the transition. Three patterns handle this:

1. **Dual-write with the old system authoritative.** New writes go to both old and new databases; reads come from old until new is verified. Eventually flip reads to new.
2. **CDC-based backfill.** Old system is the source of truth; a CDC stream (e.g., Debezium) reads the old DB's WAL and writes changes into the new DB in near-real-time. The new system reads from the new DB. Once converged, writes flip to new, and the CDC pipeline is decommissioned.
3. **Expand/contract migrations.** Schema changes are made backward-compatible (expand), both systems run, then old columns are dropped (contract). Never make a breaking schema change while both systems share a database.

The expand/contract pattern is what allows the Strangler Fig to proceed without coordination locks on the database:

```
   Phase expand:    ALTER TABLE orders ADD COLUMN status_v2;   -- both old & new can use
   Migrate:         BACKFILL status_v2 FROM legacy_status;
   Coexist:         App reads status_v2 (prefers) else legacy_status
   Contract:        ALTER TABLE orders DROP COLUMN legacy_status;  -- only after old system retired
```

## Pitfalls observed in real migrations

- **The facade becomes a single point of failure.** If it goes down, both systems are unreachable. Mitigate by running it on the same infra standards as the most critical service: multiple AZs, autoscaling, alerting on p99 latency.
- **Routing logic drifts over time.** Each slice adds a special case to the facade. After 20 slices, nobody knows what the facade does. Mitigate by keeping routing rule-driven (one config source of truth) and code-minimal.
- **The "last 10%" never migrates.** The hard cases — admin endpoints, batch jobs, the one feature that depends on legacy state — sit in the old system forever. Plan for them: budget for the last 10% being as expensive as the first 50%.
- **Stateful sessions break.** If the legacy system holds session state in memory and the new system holds it in Redis, switching mid-session logs users out. Pin users to a backend for the duration of their session, or migrate session state externally first.
- **The "secondary writes" trap.** A code path in the new system writes to a table the old system also reads — but the new system's schema is subtly different. The old system silently corrupts the data. Mitigate with the expand/contract rule: never let two writers with different mental models touch the same column.

## When to use it, and when not to

Use the Strangler Fig when:

- The legacy system is too large to rewrite in one project.
- The legacy system is in production and cannot be frozen.
- You can identify a clear routing seam (URL, queue, feature).
- You have a schema migration strategy that supports backward compatibility (expand/contract).

Don't use it when:

- The legacy system is fundamentally broken (e.g., data is corrupt) and you must replace it as a unit.
- The legacy system is small enough to rewrite in a quarter.
- The cost of running two systems during migration is higher than the cost of a clean rebuild (rare, but true for very small systems).
- The system has no extractable seams (everything calls everything else via shared in-process state). In this case you must first refactor to create seams, then strangle.

## Production examples

- **Amazon's early service decomposition (2001–onward).** The Strangler Fig approach is widely attributed to Amazon's early service decomposition; they built a routing layer that exposed service endpoints behind a single DNS, then moved services one at a time. The facade pattern is foundational to the AWS service framework.
- **ThoughtWorks' deployments in retail banking.** Documented in their Technology Radar as the recommended approach for mainframe migration in finance — the radar entry on strangler fig application appears in Adopt and has stayed there for many volumes.
- **GitHub's migration from a Rails monolith to a service-oriented architecture.** Their `github/http_router` and the gradual deprecation of old endpoints is a textbook Strangler Fig applied at HTTP granularity.

## Interview questions

**Q: When is a big-bang rewrite preferable to a Strangler Fig?**

When the legacy system is small (rewrite in under a quarter), fundamentally broken (data corrupt), or has no extractable seams (shared in-process state only) and refactoring to create seams costs more than a clean rebuild.

**Q: How do you migrate stateful session data during a Strangler Fig?**

Externalize session state first (move it from in-memory to a shared store like Redis), then run both systems against the shared store. The migration then becomes stateless at the routing layer.

**Q: What is the role of feature flags in the Strangler Fig?**

Feature flags provide the routing mechanism at the request level. A flag controls the percentage of traffic going to the new system. Crucially, flags make routing **runtime-configurable** — you can roll back without a deploy.

**Q: What is the biggest risk of the Strangler Fig?**

The facade becomes a single point of failure and a maintenance liability. If not designed carefully, it accumulates special-case routing rules that nobody understands.

**Q: How do you handle the schema during a Strangler Fig migration?**

Expand/contract migrations: add new columns/tables compatible with both systems, run dual-write or CDC backfill, switch reads to new, then drop old columns only after the old system is fully retired.

## Cross-references

- [Microservices](./microservices.md) — service decomposition is often the destination of a Strangler Fig migration
- [Anti-Corruption Layer](./anti-corruption-layer-deep.md) — the facade in a Strangler Fig often plays the ACL role
- [Progressive Delivery](./progressive-delivery.md) — canary / blue-green for the new system once routing is in place
- [Feature Flags](../../sre/feature-flags.md) — runtime rollout mechanism
- [CDC and the Transactional Outbox](./cdc-outbox.md) — the data-backfill mechanism

## References

- [Martin Fowler — StranglerFigApplication (bliki)](https://martinfowler.com/bliki/StranglerFigApplication.html) — the canonical original write-up
- [Martin Fowler & James Lewis — Microservices (article)](https://martinfowler.com/articles/microservices.html) — discusses brownfield decomposition including the strangler approach
- [ThoughtWorks Technology Radar — Strangler Fig Application (Adopt)](https://www.thoughtworks.com/radar/techniques/strangler-fig-application) — the industry-wide entry
- [ThoughtWorks Technology Radar (current edition)](https://www.thoughtworks.com/radar) — broader context on legacy migration patterns
- [Sam Newman, "Building Microservices, 2nd ed." (O'Reilly, 2021), Ch. 8 — Refactoring to Microservices](https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/) — chapter-length treatment of the strangler approach
- [AWS Prescriptive Guidance — Strangler Fig pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler.html) — cloud-pattern write-up
