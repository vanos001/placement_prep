# Backend for Frontend Pattern

A Backend for Frontend (BFF) is a server-side component that is **specialized for one frontend**. A typical setup has a web BFF for the browser SPA, a mobile BFF for the iOS app, and a different mobile BFF for the Android app. Each BFF exposes exactly the endpoints its frontend needs — no more, no less — and translates between the frontend's natural API and the downstream microservices' APIs. The pattern was coined by SoundCloud in 2015 and popularized by Sam Newman and the ThoughtWorks Technology Radar.

## The problem the BFF solves

Before BFFs, a typical setup is a single API gateway that all frontends share:

```
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  Web    │  │  iOS    │  │ Android │
   └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │
        └────────────┼────────────┘
                     ▼
            ┌────────────────┐
            │  API Gateway    │   ← single backend
            │ /users /orders /...│
            └────────┬───────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   UserSvc      OrderSvc    RecSvc
```

This appears clean but breaks down in three ways:

1. **Each frontend needs a different shape of data.** The web homepage wants the user, recommendations, notifications, and cart in one render. Mobile wants a smaller payload (the user only, plus one recommendation) and uses a different field naming (`is_premium` vs `premium`). The shared gateway has to expose a union of all fields, which is bloated.
2. **The frontend team has to file tickets to the backend team** for every endpoint change. The backend team is now the bottleneck.
3. **The gateway accumulates per-frontend logic.** Half its rules say "if the request has a mobile user-agent, transform like this; otherwise, transform like that." This is the gateway doing BFF logic, badly.

The BFF moves that per-frontend logic out of the gateway and into **per-frontend backends** owned by the frontend teams.

## The canonical BFF topology

```
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │  Web    │          │  iOS    │          │ Android │
   │ SPA     │          │  App    │          │  App    │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │  Web    │          │  iOS    │          │ Android │
   │  BFF    │          │  BFF    │          │  BFF    │
   └────┬────┘          └────┬────┘          └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
              ┌──────────────────────────┐
              │   Shared microservices     │
              │ UserSvc OrderSvc RecSvc   │
              └──────────────────────────┘
```

Key properties:

- **One BFF per frontend.** Not "one BFF for all mobile"; one per platform if their needs differ. (If iOS and Android have identical needs, they can share.)
- **The BFF is owned by the frontend team.** The web team owns the web BFF. They can deploy changes to it without coordinating with the backend teams.
- **The BFF is a thin orchestrator**, not a business logic home. It calls downstream services, aggregates their responses, and reshapes the data. The business state lives in the downstream services.

## BFF responsibilities

A BFF typically does four things.

### 1. Aggregation

The web homepage needs user, recommendations, and notifications. Without a BFF, the SPA makes three round-trips; with a BFF, it makes one. The BFF fans out in parallel:

```python
import asyncio

async def homepage(request):
    user_id = request.auth.user_id
    user, recs, notifs = await asyncio.gather(
        user_client.get(user_id),
        recs_client.get_for(user_id, limit=5),
        notif_client.list(user_id, unread=True),
        return_exceptions=False,
    )
    return {
        "user": {
            "id": user["id"],
            "name": user["display_name"],
            "avatar": user["picture_url"],
            "is_premium": user["tier"] == "premium",
        },
        "recommendations": [
            {"id": r["id"], "title": r["title"], "image": r["thumb"]}
            for r in recs["items"]
        ],
        "notifications": notifs["items"],
    }
```

The shape returned to the SPA is exactly what the SPA renders — no field more, no field less. The frontend team owns the shape, because the frontend team owns the BFF.

### 2. Transformation

Different downstream services have different conventions. The user service uses snake_case; the recommendation service uses camelCase; the notification service uses a nested `data.attributes` structure (JSON:API). The BFF flattens all of these into a single convention the frontend prefers.

This is where the BFF acts as an **Anti-Corruption Layer** between the frontend's vocabulary and the backends' vocabularies. The translation happens in the BFF, not in the SPA.

### 3. Protocol adaptation

The web BFF exposes HTTP/JSON. But the iOS app may want to talk to its BFF over a binary protocol (gRPC or Thrift) to reduce payload size and battery use. The BFF exposes the protocol the frontend wants and translates to whatever the downstream services speak.

```
   Web SPA  ──HTTP/JSON──▶  Web BFF  ──HTTP/JSON──▶  services
   iOS app  ──gRPC───────▶  iOS BFF  ──HTTP/JSON──▶  services
```

The downstream services don't know the frontends exist; the frontends don't know about JSON:API, gRPC, or the downstream conventions. Each side is decoupled from the other by the BFF.

### 4. Security trimming

The BFF strips fields the frontend should not see. The user service returns the user's email and phone for internal admin use; the public web BFF never includes them in its response. The mobile BFF may include the phone (because the app needs it for SMS verification) but not the email. This is **field-level security** enforced at the BFF, not at the frontend (where it would be client-side and easy to bypass).

## BFF vs API Gateway

| Aspect | API Gateway | BFF |
|---|---|---|
| One per system? | Yes | No — one per frontend |
| Cross-cutting concerns (TLS, auth, rate limit) | Yes | Usually not |
| Business-aware aggregation | Maybe | Yes, for one frontend |
| Owned by | Platform team | Frontend team |
| Returns one shape per endpoint | Yes | Returns the shape the frontend needs |

The canonical pattern is to have **both**: an API gateway at the edge for TLS, auth, rate limiting, and routing, and one BFF per frontend sitting behind the gateway. The gateway routes `web.example.com/*` to the web BFF, `api.example.com/mobile/*` to the mobile BFF.

```
   client ──▶ API Gateway ──▶ Web BFF   ──▶ services
                          └─▶ Mobile BFF ──▶ services
                          └─▶ Android BFF ──▶ services
```

The gateway is platform-owned and cross-cutting; the BFFs are frontend-team-owned and per-frontend.

## Production examples

### SoundCloud

SoundCloud coined the term in 2015. Their architecture had three frontends (web, iOS, Android) sharing one backend that was growing increasingly tangled. They split it into three BFFs, each owned by the corresponding client team. The web BFF was a Node.js service because the web team was strongest in JS; the iOS BFF was initially Ruby, later rewritten. The choice of language per BFF is a deliberate property of the pattern: the team that owns the BFF gets to pick the tech.

SoundCloud's writeup emphasized that the BFFs were thin and that business logic was kept in shared services downstream. The BFFs were aggregation and adaptation only — they were **not** a place to add features that the frontends needed but the downstream services didn't yet provide.

### Spotify

Spotify's backend evolution followed a similar arc. The Spotify mobile app talks to a BFF (sometimes called the "mobile API gateway") that aggregates data from many downstream services, including the music catalog service, the recommendation service, and the social graph service. The BFF exposes endpoints tailored to specific app screens (`/home`, `/playlist/<id>`, `/artist/<id>`), each returning the exact payload that screen renders. Spotify engineering has discussed the design at conference talks and in blog posts, where the BFF concept is implicit in their "view service" architecture.

### Other adoptions

- **Netflix** runs per-device BFFs (one for TV, one for mobile, one for web) under the umbrella of their "edge" services. The Netflix tech blog has discussed their edge architecture (the "Zuul" gateway family) where per-device logic lives in BFF-like services.
- **ThoughtWorks** promoted the pattern in the Technology Radar (Vol. 16, Adopt) and again in later editions as part of their cloud-native guidance.

## Comparison to GraphQL

GraphQL is sometimes proposed as a replacement for the BFF. They are not interchangeable: GraphQL solves a related but different problem.

| Aspect | BFF | GraphQL |
|---|---|---|
| Who decides the response shape? | The BFF, per endpoint | The client, per query |
| Frontend team autonomy | High — they own the BFF | Higher — they shape queries |
| Backend team overhead | Per-frontend BFF service to maintain | Single GraphQL gateway to maintain |
| Caching | Easy (HTTP caching of BFF responses) | Hard (per-query caches, persisted queries) |
| N+1 problem | BFF developer writes efficient fan-out | Gateway needs dataloader |
| Client-driven schema evolution | No — BFF endpoint changes are explicit | Yes — clients can ask for new fields |
| Security | Server decides what fields each client sees | Server enforces field-level auth |

In practice the two compose: a BFF can expose GraphQL itself. The frontend team owns a GraphQL server as the BFF, and writes the resolvers that fan out to downstream services. This gives the team the autonomy of GraphQL within the per-frontend structure of BFFs.

The argument **for** a BFF over GraphQL: a BFF returns a fixed shape, so caching, monitoring, and security are conventional HTTP-level concerns. GraphQL gives flexibility but moves complexity to the client (query design) and to the gateway's resolver layer (N+1, persisted queries, cache keys). For most teams, fixed-shape BFF endpoints are simpler to operate than a free-form GraphQL API.

## Anti-patterns

- **BFF as business logic home**: the BFF starts to enforce business rules (e.g., "users under 13 cannot see recommendations"). Those rules belong in the recommendation service, not in the BFF. If the BFF enforces them, you have to update three BFFs (web, iOS, Android) when the rule changes.
- **Single BFF for everything**: the team builds "the BFF" and re-creates the shared-gateway problem. The fix is per-frontend BFFs; if you only have one frontend, you don't need the pattern.
- **BFF calls BFF**: BFFs should call shared services, not other BFFs. If web BFF needs data the mobile BFF has, the data should be in a shared service.
- **BFF in a slow language with high latency**: the BFF adds a hop; if it's a slow runtime, it dominates latency. SoundCloud's choice of Node for the web BFF was deliberate — it's fast at I/O.
- **BFF as caching layer**: BFFs can cache, but heavy caching logic drifts into business rules ("when is this stale?"). Cache in the downstream services when possible.

## When to use BFFs, and when not

Use BFFs when:

- You have 2+ frontends with meaningfully different data needs.
- Frontend and backend teams are different and the backend is the bottleneck.
- The frontend frequently needs to make multiple downstream calls to render one screen.
- You're hitting payload-size issues on mobile (a BFF can trim aggressively).

Don't use BFFs when:

- You have one frontend.
- The downstream services already expose exactly what the frontend needs.
- You can't afford the extra hop (latency-bound, single-region, low-throughput systems).
- Your frontend team is not staffed to operate a service. A BFF is a server; it needs monitoring, alerting, on-call rotation.

## BFF lifecycle and team organization

A BFF is owned by the team that owns the frontend. That means:

- **The web team** runs the web BFF, deploys it, fixes its bugs, and is on-call for it.
- **The mobile team** runs the iOS BFF and the Android BFF.

This is the source of the BFF's most important property: **the frontend team no longer needs to wait for the backend team to add or change an endpoint**. They add it to their own BFF. The BFF calls the existing downstream services. The backend team only sees new requests when the BFF needs data the downstream services don't yet expose.

This is also the BFF's biggest organizational risk: if the frontend team is not ready to operate a server (deployments, observability, incident response), the BFF will rot. The pattern is a commitment, not a quick win.

## Cross-references

- [Microservices](./microservices.md) — the downstream services a BFF aggregates
- [API Gateway](../api/api-gateway.md) — the edge component that sits in front of BFFs
- [GraphQL](../api/graphql.md) — alternative / complement
- [Anti-Corruption Layer](./anti-corruption-layer-deep.md) — a BFF is conceptually an ACL between frontend and backend
- [Service Mesh](../containers/service-mesh.md) — for mTLS and retries between BFF and downstream

## References

- [Sam Newman — Pattern: Backends For Frontends](https://samnewman.io/patterns/architectural/bff/) — the canonical pattern reference, by the author who formalized the term
- [SoundCloud Engineering Blog — Building Products at SoundCloud (Part III)](https://developers.soundcloud.com/blog) — the post where the term "BFF" was coined
- [ThoughtWorks Technology Radar — BFF (Adopt)](https://www.thoughtworks.com/radar/techniques/bff) — the industry-wide promotion
- [ThoughtWorks Technology Radar (current edition)](https://www.thoughtworks.com/radar) — broader context on the pattern's evolution
- [Spotify R&D Engineering Blog](https://engineering.atspotify.com/) — backend evolution articles where the BFF pattern is implicit
- [Martin Fowler & James Lewis — Microservices](https://martinfowler.com/articles/microservices.html) — adjacent article that discusses brownfield decomposition including the BFF as a transitional form
- [Netflix Tech Blog — Edge Architecture](https://netflixtechblog.com/) — discusses per-device edge services, a BFF in all but name
