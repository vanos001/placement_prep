# API Versioning Deep Dive — URL Path, Header, Query, and the Deprecation Lifecycle

## Overview

Every breaking change you ship without a version contract becomes someone else's
production incident. API versioning is the discipline of letting clients pin a
contract while the server evolves underneath them. The four canonical
strategies — URL path (`/v1/`), request header (`Accept` vendor media types
or `X-API-Version`), query parameter (`?version=1`), and Stripe-style
date-based pinning — make different trade-offs between discoverability,
cacheability, routing complexity, and purity. Knowing which to pick, and how
to retire the old one with `Sunset`/`Deprecation`, is a near-guaranteed
placement interview topic.

> Related: [Versioning](./versioning.md) (the short version), [REST](./rest.md),
> [API Gateway](./api-gateway.md) (per-version routing),
> [Idempotency](../patterns/idempotency.md), [gRPC](./grpc.md) (protobuf
> evolution rules), [OpenAPI](./openapi-spec.md).

## What Counts as a Breaking Change

Before picking a strategy, fix the vocabulary. A change is **breaking** if a
correctly-written client can break because of it. Concretely:

| Change | Breaking? | Why |
|---|---|---|
| Add new endpoint | No | Old clients don't know it exists |
| Add optional request field | No | Old clients don't send it |
| Add new response field | No | Tolerant readers ignore unknown fields (Postel's law) |
| Add new enum value | Maybe | Clients that `switch` over enum may not have a default |
| Rename field | **Yes** | Old client can't read the new name |
| Change field type (int → string) | **Yes** | Deserialization fails |
| Make optional field required | **Yes** | Old client doesn't send it |
| Remove field | **Yes** | Old client reads it; gone |
| Change auth scheme | **Yes** | Old client doesn't send new credentials |
| Change pagination shape | **Yes** | Old client can't walk pages |
| Change error semantics (404 → 422) | **Yes** | Old client branches on status |

The rule of thumb: **additive changes are free; subtractive or
shape-changing ones cost a version bump**. Push hard for additive-only evolution
and you can avoid most version bumps entirely.

## The Four Strategies

### 1. URL Path Versioning — `/v1/resource`

```http
GET /v1/users/42 HTTP/1.1
GET /v2/users/42?fields=id,name,team HTTP/1.1
```

Used by GitHub (`/repos/{owner}/{repo}` under `2022-11-28` media), Twitter,
Twilio, AWS (`/2012-08-10/` for DynamoDB), Google Calendar. The version lives
in the path; the gateway routes `/v1/` to the v1 cluster and `/v2/` to v2.

**Pros**

- Trivial to route at the gateway (Kong, Envoy, NGINX `location`):
  ```nginx
  location /v1/ { proxy_pass http://usersvc-v1:8080; }
  location /v2/ { proxy_pass http://usersvc-v2:8080; }
  ```
- Trivial to test with `curl`. No headers required.
- Cache key naturally varies by URL — CDNs do the right thing without a
  `Vary` header.
- Operations dashboards group by URL; you can see v1 vs v2 traffic split
  directly in your logs.

**Cons**

- Impure REST: the URL identifies the resource, not its representation.
  Fielding explicitly criticized URI-versioning in his blog
  ([*Versioning, Hypermedia, and the IETF*](https://www.youtube.com/watch?v=hdSrT_6X2K0))
  — but REST purity rarely pays the bills.
- Multiple versions of every endpoint co-exist in the router; you must support
  them in parallel until deprecation completes.
- Bumps the URL length; some proxies have path-length limits.

### 2. Header Versioning — `Accept` Vendor Media Type

```http
GET /users/42 HTTP/1.1
Accept: application/vnd.acme.v1+json
```

Or the cruder custom header form:

```http
GET /users/42 HTTP/1.1
X-API-Version: 1
```

GitHub uses the vendor-media-type form: the default is
`application/vnd.github+json`, preview features require a media type like
`application/vnd.github.mercy-preview+json`. Stripe allows per-request
overrides via the `Stripe-Version` header.

**Pros**

- Clean URLs: `/users/42` always means "user 42"; the header picks the
  representation. This is RESTfully correct.
- Multiple versions coexist on the same URL.

**Cons**

- **Cache fragmentation**: by default, a CDN keys on URL only. Two requests for
  `/users/42` with different `Accept` values collide unless the origin sends
  `Vary: Accept` (or `Vary: X-API-Version`). `Vary` reduces hit rate and can
  cause some CDNs to disable caching entirely if not configured carefully.
- **Discoverability**: you can't `curl /users/42` and see what version you got
  without setting headers. Postman/Swagger UI/OpenAPI tooling struggle more
  with header-versioned APIs.
- **Browser clients** can't easily set `Accept` for `<img>` tags or simple
  fetches; you end up writing a thin BFF anyway.

### 3. Query Parameter — `?version=1`

```http
GET /users/42?version=1 HTTP/1.1
```

This is the **anti-pattern**. It looks easy (no router changes, no header
tricks), but it inherits every problem of header versioning plus URL
pollution:

- Query parameters are part of the cache key in most CDNs *only if* the CDN is
  configured to honor them; many default to ignoring unknown query params.
- Query parameters tend to be ephemeral — clients drop them, gateways strip
  them, log aggregators collapse them.
- The `version=1` query competes with legitimate resource-filtering queries
  (`?status=active`), creating namespace collisions.

Use it only as a temporary escape hatch while migrating an unversioned API
to URL path versioning.

### 4. Content Negotiation (Strict REST)

Full HTTP content negotiation per [RFC 7231](https://www.rfc-editor.org/rfc/rfc7231)
§5.3: the client declares what it can accept via `Accept`,
`Accept-Language`, `Accept-Encoding`, and the server picks a representation.
This is what header versioning *should* look like in theory. In practice
almost nobody does it strictly — the tooling cost outweighs the purity.

The REST API Design Rulebook (MuleSoft) prescribes media-type versioning
exclusively. It is the canonical reference for the "URL path versioning is a
REST violation" position.

## Stripe's Date-Based Pinning

Stripe never publishes `/v2/`. Instead they pin every account to a date
version (`Stripe-Version: 2024-06-20`) and evolve the API additively.
Breaking changes ship, but only the new version sees them.

```
                client request
                      |
                      v
   ┌────────────────────────────────────┐
   │  Gateway reads Stripe-Version hdr │
   │  (or account-pinned default)      │
   └────────────────────────────────────┘
                      |
                      v
   ┌────────────────────────────────────┐
   │  Compatibility Layer               │
   │  - translate v(2023-08-01) -> latest   │
   │  - strip new fields the old client │
   │    won't understand                │
   │  - remap renamed fields back       │
   └────────────────────────────────────┘
                      |
                      v
   ┌────────────────────────────────────┐
   │  Latest service code (one binary)  │
   └────────────────────────────────────┘
```

Mechanics, as documented at <https://docs.stripe.com/api/versioning>:

1. Every account has a pinned version, set in the Dashboard or via
   `stripe.com/v1/accounts` update. The server sends
   `Stripe-Version: <date>` in every response so the client knows what it got.
2. The client can override per-request by setting the `Stripe-Version`
   header.
3. New fields are returned additively; old clients ignore them.
4. Breaking changes are gated behind a newer date — bumping the date exposes
   the new shape. Old-date clients keep working unchanged.
5. Internally a **compatibility layer** translates old-version request shapes
   to the latest internal representation, and the latest response shape back
   to the requested version.

The win is that the URL space stays stable forever; old integrations
written in 2018 still work in 2026. The cost is a non-trivial translation
layer that must be maintained forever — but Stripe has decided that cost is
worth it because every breaking change at Stripe would be a breaking change
for hundreds of thousands of integrations.

## Comparison Table

| Strategy | Example | Cacheability | Testability | Tooling | REST purity | Best for |
|---|---|---|---|---|---|---|
| **URL path** | `/v1/users` | Excellent (URL varies) | Trivial (`curl`) | First-class | Low | Public APIs, default |
| **Accept vendor media type** | `Accept: application/vnd.x.v1+json` | Needs `Vary: Accept` | Hard (headers) | Partial | High | REST-purist, enterprise |
| **Custom header** | `X-API-Version: 1` | Needs `Vary: X-API-Version` | Moderate | Partial | Medium | Internal microservices |
| **Query param** | `?version=1` | CDN-config-dependent | Easy | Easy | Low | Migration escape hatch only |
| **Date pinning** | `Stripe-Version: 2024-06-20` | Per-version header | Moderate | Moderate | Medium | Large public APIs w/ additive evolution |
| **No versioning** | `/users` | Excellent | Trivial | Easy | High | Internal, additive-only |

## The Deprecation Lifecycle

Retiring a version is harder than introducing one. RFC 8594
([*The Sunset HTTP Header Field*](https://www.rfc-editor.org/rfc/rfc8594))
defines the mechanism; the `Deprecation` header (RFC draft,
[draft-ietf-httpapi-deprecation-header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-deprecation-header/))
signals it.

```http
HTTP/1.1 200 OK
Deprecation: Sun, 01 Jun 2026 00:00:00 GMT
Sunset:      Sat, 31 Dec 2026 23:59:59 GMT
Link:        <https://docs.acme.com/migrations/v2>; rel="sunset"
```

- `Deprecation` carries the date the version became deprecated. Clients
  should warn (log, telemetry, console) but the API still works.
- `Sunset` carries the date the version will be removed. After this date,
  requests to the deprecated version return `410 Gone` (or `404`).
- `Link: ...; rel="sunset"` points the client to a migration guide.

A complete deprecation timeline looks like:

```
T-0      T-deprecate       T-sunset           T-removal
  |            |                 |                  |
  v            v                 v                  v
  ┌──────────────────────────────────────────────────┐
  │  v1 live   │ v1 deprecated   │ v1 sunset banner  │ 410 Gone
  │  v2 RC     │ v2 GA           │ v2 only            │
  └──────────────────────────────────────────────────┘
                  |                 |
                  v                 v
            Deprecation: hdr   Sunset: hdr
            + email dashboard   + deprecation banner
            + 6-month runway   + final 30-day hard stop
```

Practical rules:

1. **Always emit `Deprecation` before `Sunset`**. A 6-to-12-month runway is
   the minimum for public APIs; 18 months is safer for B2B integrations
   that move slowly.
2. **Log deprecation hits server-side**. Tag every request to a deprecated
   version with the caller's API key or tenant ID, and report weekly to the
   team that owns the integration.
3. **Don't change `Sunset` once published**. Once a client has been told a
   date, moving it earlier is a breaking change of its own kind. Moving it
   later is fine but communicate it loudly.
4. **Never silently keep a deprecated version alive past `Sunset`**. If you
   do, no one will believe your next `Sunset` either.
5. **Set up synthetic checks against the old version** so you know the
   moment it actually breaks.

## Implementation Patterns

### Gateway Routing (URL path versioning)

```yaml
# Kong declarative config
services:
  - name: usersvc-v1
    url: http://usersvc-v1.internal:8080
    routes:
      - name: users-v1
        paths: [ "/v1/users" ]
        strip_path: false

  - name: usersvc-v2
    url: http://usersvc-v2.internal:8080
    routes:
      - name: users-v2
        paths: [ "/v2/users" ]
        strip_path: false
```

The gateway can also do request/response transformation between versions
when fields are renamed, giving you a single point of compatibility.

### Header Dispatch (header versioning)

```go
// net/http middleware
func VersionMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        ver := r.Header.Get("Accept")
        switch {
        case strings.Contains(ver, "vnd.acme.v2"):
            r = withVersion(r, "v2")
        case strings.Contains(ver, "vnd.acme.v1"):
            r = withVersion(r, "v1")
        default:
            r = withVersion(r, "v1") // default
        }
        w.Header().Set("Vary", "Accept") // critical for CDN correctness
        next.ServeHTTP(w, r)
    })
}
```

The `Vary: Accept` is not optional — without it, Cloudflare/Fastly cache a
v1 response under `/users/42` and serve it to v2 clients. This single
omission is the most common production bug in header-versioned APIs.

### Stripe-Style Date Pinning

```python
# pseudo-compat layer
def handle_request(req, account):
    requested = req.headers.get("Stripe-Version") or account.pinned_version
    latest_payload = business_logic(req)  # always the latest shape

    if requested < CURRENT_DATE:
        return downgrade(latest_payload, requested)
    return latest_payload


def downgrade(payload, target_version):
    """Translate latest response shape back to target_version's shape."""
    if target_version < "2024-06-20":
        # customer.email was renamed to customer.contact_email in 2024-06-20
        payload["customer"]["email"] = payload["customer"].pop("contact_email", "")
    if target_version < "2023-08-01":
        # amount was integer cents until 2023-08-01; now a decimal string
        payload["amount"] = int(round(float(payload["amount"]) * 100))
    return payload
```

The `downgrade` function grows monotonically; you never delete branches
because some old client may still be pinned to that date.

## gRPC and Protobuf Versioning

Protobuf has a different model. Field numbers are the contract; once
assigned they are **never reused**. Evolution rules:

- Add fields with new numbers — old binaries ignore them.
- Mark removed fields `reserved` so the number is not reused.
- Use `oneof` for additive optional variants.
- For service-level breaking changes, ship a new package:
  `acme.users.v1` → `acme.users.v2`, run both, route at the gateway.

See [gRPC deep dive](./grpc.md) for wire-format details.

## Common Pitfalls

1. **Picking URL path versioning and then bumping major versions every
   month**. The point of versioning is to give clients stability; if you
   bump constantly you've just renamed "no versioning" to "v1, v2, v3, ...".
2. **Forgetting `Vary: Accept` with header versioning** — silent
   cross-version cache poisoning.
3. **No deprecation runway** — announcing `Sunset` two weeks before
   removal is a great way to lose your biggest customers.
4. **Renaming fields inside an additive version bump** — that's a breaking
   change, even if you call it v1.1.
5. **Keeping two divergent codepaths**. The Stripe model has *one* business
   logic and a translation layer; if you find yourself maintaining two
   divergent services behind `/v1/` and `/v2/`, you've already lost.

## Interview Questions

### Q: URL path vs header versioning — which do you pick and why?

URL path dominates for public APIs because it's cacheable without `Vary`,
trivially testable with `curl`, and routers group by version in logs.
Header versioning is RESTfully purer (URL identifies the resource, header
selects the representation) but needs `Vary` for CDN correctness, harder to
test, less discoverable. For internal microservices where you control all
clients, header versioning is acceptable.

### Q: How does Stripe avoid v1/v2 URLs?

Date-based version pinning. Each account is locked to a `Stripe-Version`
date. New fields are returned additively; breaking changes are gated
behind newer dates. A compatibility layer translates the latest internal
shape to the requested version. Clients upgrade by setting the
`Stripe-Version` header per-request or bumping the account default in the
dashboard. Result: the URL space never changes, but the API still evolves.

### Q: When can you avoid a version bump?

Additive changes only: new endpoint, new optional request field, new
response field (assuming tolerant readers), new enum value (assuming clients
have a default branch). You must version on renames, type changes, removals,
auth changes, pagination-shape changes, or error-semantics changes.

### Q: What does RFC 8594 add?

The `Sunset` HTTP header, which carries the date a resource or API version
will be removed. Clients can read it to schedule migration. Paired with
the `Deprecation` header (separate draft), it forms the standard
deprecation lifecycle: `Deprecation` says "this is going away", `Sunset`
says "this is the date". Both are HTTP headers — no out-of-band channel
needed.

## Cross-References

- [Versioning](./versioning.md) — short-form versioning notes
- [REST](./rest.md) — REST principles and the uniform interface
- [API Gateway](./api-gateway.md) — per-version routing at the edge
- [gRPC](./grpc.md) — protobuf evolution rules (field numbers, `reserved`)
- [OpenAPI](./openapi-spec.md) — versioning the schema document itself
- [Idempotency](../patterns/idempotency.md) — safe retries across versions

## References

- Stripe API versioning — <https://docs.stripe.com/api/versioning>
- GitHub REST API versioning (media types and `X-GitHub-Api-Version`) — <https://docs.github.com/rest/overview/api-versions>
- RFC 8594 — *The Sunset HTTP Header Field* — <https://www.rfc-editor.org/rfc/rfc8594>
- RFC 7231 — *HTTP/1.1 Semantics and Content* (content negotiation) — <https://www.rfc-editor.org/rfc/rfc7231>
- MuleSoft — *REST API Design Rulebook* (MuleSoft Anypoint), media-type versioning prescription
- draft-ietf-httpapi-deprecation-header — <https://datatracker.ietf.org/doc/draft-ietf-httpapi-deprecation-header/>
- Roy Fielding — *REST APIs must be hypertext-driven* (blog, 2008) — <https://roy.gbiv.com/untangled/2008/rest-apis-must-be-hypertext-driven>
