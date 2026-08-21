# API Caching Deep Dive — HTTP Caching, Conditional Requests, CDNs, and `stale-while-revalidate`

## Overview

Caching is the single biggest latency and cost lever in an HTTP API. Done
right, you serve 80%+ of read traffic from the CDN edge in 10-30 ms
instead of round-tripping to your origin in 100-300 ms. Done wrong, you
serve stale data, leak user data across tenants, or pollute the cache so
the hit rate collapses. The HTTP caching machinery — `Cache-Control`,
`ETag`, `Last-Modified`, `Vary`, conditional requests, and the `304`
response — is specified by [RFC 7234](https://www.rfc-editor.org/rfc/rfc7234)
and is the *single most under-used* feature of public APIs. This page
covers the header vocabulary, the conditional request dance, CDN caching
vs origin caching, and how `stale-while-revalidate` gives you both freshness
and high hit rate.

> Related: [REST](./rest.md), [API Gateway](./api-gateway.md), [Rate
> Limiting](./rate-limiting.md), [Caching Strategies](../../sre/cache-patterns.md),
> [Redis](../messaging/redis.md), [Buffer Pool](../../dbms/caching/buffer-pool.md).

## The HTTP Caching Vocabulary

### `Cache-Control` — the master directive

```http
Cache-Control: public, max-age=300, s-maxage=600, stale-while-revalidate=86400
```

| Directive | Who honors it | Meaning |
|---|---|---|
| `public` | All caches | Response may be cached even if normally non-cacheable (e.g., authenticated response) |
| `private` | Browser cache only | Don't cache in a shared CDN — contains user-specific data |
| `no-store` | All caches | Never cache. **Only** use when freshness is critical (bank balances). Often overused. |
| `no-cache` | All caches | Cache *may* store, but must revalidate with origin before using |
| `max-age=N` | Browser, CDN | Fresh for N seconds in the browser |
| `s-maxage=N` | CDN only | Fresh for N seconds in the shared CDN; overrides `max-age` for shared caches |
| `stale-while-revalidate=N` | CDN | Serve stale response for up to N seconds after expiry while revalidating in the background |
| `stale-if-error=N` | CDN | Serve stale response if the origin returns 5xx, for up to N seconds |
| `must-revalidate` | All caches | Once stale, must revalidate. Don't serve stale on origin failure |
| `proxy-revalidate` | CDN only | Like `must-revalidate` but only for shared caches |
| `immutable` | Browser | The response will never change; safe to skip revalidation entirely |

`public` vs `private` is the single most-violated directive. A
logged-in user's profile response is **not** cacheable in a shared CDN
unless you carefully partition the cache key (see *Vary*, below). Mark it
`private` to keep it out of the CDN and only in the user's browser.

### `ETag` — content fingerprint

```http
ETag: "deadbeef-1234-5678"
```

The `ETag` is a string that uniquely identifies the current representation
of a resource. It is typically a hash (MD5, SHA-256 truncated) of the
response body or a version identifier. When the resource changes, the
`ETag` must change. The client sends `If-None-Match: "deadbeef-..."` on the
next request, the server compares, and if equal, returns `304 Not Modified`
with an empty body — saving bandwidth and serialization cost on the
origin, even if it can't save the round trip.

```http
# request 1
GET /api/products/42 HTTP/1.1
→ 200 OK
   ETag: "v3-aabbcc"
   Cache-Control: public, max-age=300
   Content-Type: application/json
   { ... body ... }

# request 2 (after max-age=300 expires, or no-cache)
GET /api/products/42 HTTP/1.1
If-None-Match: "v3-aabbcc"
→ 304 Not Modified
   ETag: "v3-aabbcc"
   Cache-Control: public, max-age=300
   (empty body)
```

Two flavors of `ETag`:

- **Strong** — `ETag: "v3-aabbcc"`. The quoted string is unique per byte
  representation. Bytes must match exactly.
- **Weak** — `ETag: W/"v3-aabbcc"`. Semantically equivalent but byte
  equivalent not guaranteed (e.g., whitespace differs). Suitable when
  the resource is logically the same.

Generating an `ETag` is cheap if it piggybacks on work you're already doing
— e.g., the version field on a row, or a hash of the canonical JSON
serialization. If you have to compute it by hashing the body after
serialization, you've saved bandwidth but not CPU; consider a
content-addressed key (row version, generation number) instead.

### `Last-Modified` / `If-Modified-Since`

```http
Last-Modified: Wed, 01 Jun 2026 12:34:56 GMT
```

The HTTP/1.0-era predecessor of `ETag`. The client sends
`If-Modified-Since: Wed, 01 Jun 2026 12:34:56 GMT` and the server returns
`304` if the resource hasn't changed since that timestamp. Resolution is
one second — too coarse for fast-moving resources. Prefer `ETag` when
possible; provide `Last-Modified` for backward compatibility and proxies
that don't implement `ETag`.

### `Vary` — the cache-partition directive

```http
Vary: Accept-Encoding, Accept-Language
```

`Vary` tells the cache to include the named request headers in the cache
key alongside the URL. Without `Vary: Accept-Encoding`, a CDN might serve
a gzip-encoded response to a client that asked for `br` (brotli) — or vice
versa. The result is doubly-broken: a malformed response, *and* a poisoned
cache entry for the next client.

The most common pitfalls:

- **Forgetting `Vary: Authorization`** when caching authenticated responses
  — the classic cross-user data leak. If `Cache-Control: public` is set
  on `/api/me` and the CDN keys only on URL, Alice's profile gets served
  to Bob. Mark `Authorization`-varying responses `private` and partition
  by user, or set `Cache-Control: private` and let only the browser cache.
- **`Vary: *`** — disables caching entirely ("this response varies on
  something the server can't describe"). Useful as an escape hatch.
- **Varying on too much** — every distinct value of every `Vary`-listed
  header creates a new cache entry. `Vary: User-Agent` is the canonical
  anti-pattern because UA strings vary per browser version, OS, patch
  level; hit rate collapses.

## Conditional Requests

The conditional request headers form a 4-tuple that pairs with response
headers:

| Request header | Response header | Meaning |
|---|---|---|
| `If-None-Match: "<etag>"` | `ETag` | "If the current ETag matches, send 304" |
| `If-Modified-Since: <date>` | `Last-Modified` | "If unchanged since, send 304" |
| `If-Match: "<etag>"` | `ETag` | "Only apply this write if the ETag matches" — optimistic concurrency (RFC 7232) |
| `If-Unmodified-Since: <date>` | `Last-Modified` | "Only apply if unchanged since" |

`If-None-Match` / `If-Modified-Since` are read-path conditionals (return
304 if not changed). `If-Match` / `If-Unmodified-Since` are write-path
conditionals (return 412 Precondition Failed if not matched), useful for
optimistic concurrency control on `PUT`/`PATCH`:

```http
# client fetched version v3 earlier; now wants to update
PUT /api/articles/42 HTTP/1.1
If-Match: "v3-aabbcc"
Content-Type: application/json
{"title": "Updated Title"}

# if someone else updated between v3 and now, the server returns:
→ 412 Precondition Failed
   ETag: "v4-deadbeef"
```

The client re-fetches, gets v4, and retries with the new ETag — a
conflict-resolution loop that's far more efficient than retrying blindly.

## The 304 Not Modified Response

```http
HTTP/1.1 304 Not Modified
ETag: "v3-aabbcc"
Cache-Control: public, max-age=300
Date: Wed, 01 Jun 2026 12:35:00 GMT
```

`304` is **not** a successful response with empty body — it's a
cache-freshness signal. The body is empty, but the headers must be sent:
any `Cache-Control` refresh, any updated `ETag`, any `Vary`. The client
uses its cached copy of the body and treats the headers as updated.

The win is enormous: a `304` is typically tens of bytes versus a multi-KB
response body. On a 100 K QPS API with a 95% cache hit rate, that's the
difference between a few hundred Mbps of origin egress and several Gbps.

## CDN Caching

A CDN (Cloudflare, Fastly, Akamai, CloudFront) is a layer of caches that
sits between your clients and your origin. Edge PoPs cache your responses
geographically close to clients. With `Cache-Control: public, s-maxage=600`,
the CDN caches for 10 minutes regardless of `max-age`.

```
   client (Mumbai)  ──→  PoP Mumbai  ──→  PoP Singapore  ──→  origin (us-east-1)
                         (cache)         (cache, no hit)
                         │
                         ├─ HIT: 5 ms, no origin traffic
                         ├─ MISS: fetch from upstream, store, return
                         └─ STALE: serve stale + revalidate in background
```

CDN behaviors worth knowing:

1. **Cache key normalization**. By default, the CDN key includes URL path
   + query string. Some clients add cache-busting params (`?ts=1234567890`)
   that defeat the cache. Configure query-string whitelisting.
2. **Surrogate-key / Cache-Tag for purging**. Cloudflare's
   `Cache-Tag: product-42`, Fastly's `Surrogate-Key: product/42` headers
   let you selectively purge all cached responses associated with a key
   (e.g., when product 42 changes, purge every URL that returned its
   representation).
3. **Origin shield**. A single upstream cache between edge PoPs and your
   origin. Without an origin shield, every cache miss from every PoP hits
   your origin; an origin shield collapses those into one.
4. **Stale content on origin failure**. `stale-if-error=86400` lets the
   CDN serve stale responses if the origin returns 5xx, providing graceful
   degradation during outages.

## `stale-while-revalidate` — the best of both worlds

The fundamental tension in caching: short `max-age` = fresh data but low
hit rate; long `max-age` = high hit rate but stale data.
`stale-while-revalidate` (RFC 5861) splits the difference:

```http
Cache-Control: public, max-age=60, stale-while-revalidate=86400
```

- For the first 60 seconds after fetch, the response is **fresh** and the
  cache serves it with zero origin contact.
- For the next 86,400 seconds, the cache serves the **stale** response
  *immediately* (low latency for the client) and *simultaneously* issues
  a background fetch to the origin. The response is replaced in cache;
  the next client gets the fresh copy.

This pattern is the *modern default* for read-heavy public APIs. It gives
you sub-second p99 (the cache hit path), tolerates brief origin outages
(serve stale), and bounds staleness to one `max-age` window (the
background revalidation).

Cloudflare, Fastly, and Varnish all implement `stale-while-revalidate`
natively. The MDN
([*HTTP Caching*](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching))
and web.dev ([*Prevent unnecessary network requests with the HTTP Cache*](https://web.dev/articles/http-caching))
references are the canonical intro.

## Application-Level Caching vs HTTP Caching

| Aspect | HTTP caching (CDN, browser) | Application-level caching (Redis, Memcached) |
|---|---|---|
| **Where** | Edge PoPs, browser | Origin-side, in-memory or cluster |
| **Latency** | 5-30 ms (closest PoP) | 0.5-5 ms (in-process), 1-10 ms (Redis) |
| **Hit-rate ceiling** | Bounded by cache key cardinality (URLs) | Bounded by key cardinality (any string) |
| **Cost** | Free (CDN absorbs bytes) | Network RTT + Redis CPU |
| **Invalidation** | `Cache-Tag` purge, `s-maxage=0`, versioned URL | Direct `DEL` by app code |
| **Freshness** | `max-age` + `stale-while-revalidate` | TTL or explicit eviction |
| **Cross-tenant safety** | Requires careful `Vary` / cache-key partitioning | Naturally per-tenant (different keys) |
| **Cache misses** | Full request to origin | Cache miss still hits origin DB |
| **Authorization** | Hard — `Vary: Authorization` hurts hit rate | Easy — the app knows the caller |

The standard pattern is **both**: a CDN out front for hot public reads, a
Redis cluster behind the origin for hot authenticated reads. The CDN
absorbs the bulk of traffic; Redis protects the database from the misses.

## Implementation Patterns

### A Read API with HTTP Caching

```python
import hashlib, json
from fastapi import FastAPI, Request, Response, HTTPException

app = FastAPI()

@app.get("/api/products/{product_id}")
async def get_product(product_id: int, request: Request):
    product = await db.get(product_id)
    if product is None:
        raise HTTPException(404)

    body = json.dumps(product, separators=(",", ":")).encode()
    etag = '"' + hashlib.sha256(body).hexdigest()[:16] + '"'

    # conditional request
    if_none_match = request.headers.get("if-none-match")
    if if_none_match == etag:
        return Response(status_code=304, headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=60, stale-while-revalidate=600",
        })

    return Response(
        content=body,
        media_type="application/json",
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=60, stale-while-revalidate=600",
            "Vary": "Accept-Encoding",
        },
    )
```

The body is hashed once per request to generate the ETag. If you have a
cheap version column on the row, use that instead.

### Cache Invalidation with Surrogate Keys

```python
@app.put("/api/products/{product_id}")
async def update_product(product_id: int, ...):
    await db.update(product_id, ...)
    # purge every CDN-cached response that contained this product
    return Response(
        status_code=200,
        headers={
            "Cache-Tag": f"product-{product_id}",   # Cloudflare
            "Surrogate-Key": f"product/{product_id}",  # Fastly
            "Cache-Control": "no-store",   # never cache the PUT response
        },
    )
```

The CDN purges every cached entry with that tag/key when triggered via
the CDN's API. This gives you surgical invalidation without nuking the
entire cache.

## Common Pitfalls

1. **Authed responses marked `public`**. `/api/me` returning the logged-in
   user's data, marked `Cache-Control: public, max-age=300`, with no
   `Vary: Authorization` — cross-user data leak. Mark `private` or
   partition the cache key per user.
2. **Forgetting `Vary: Accept-Encoding`**. Compressed responses get
   served to clients that requested different encodings; some break.
3. **`no-store` everywhere**. "Caching is dangerous, so don't cache" is
   a real engineering decision that ships low-latency p99 disasters.
4. **`ETag` containing the response body verbatim**. Some naive
   implementations hash the full body — fine for bandwidth saving, useless
   for CPU saving.
5. **Long `max-age` without versioned URLs**. The cache holds a stale
   response for a week; the only way to invalidate is to deploy a new
   versioned URL (`/v2/products/42`) or purge the cache.
6. **No `stale-while-revalidate`**. Missing the easy win on the freshness
   vs hit-rate trade-off.
7. **CDN cache key includes the entire query string**. Random
   cache-busting tokens (`?ts=...`) collapse the hit rate to zero.
   Whitelist the query params that actually vary the response.

## Interview Questions

### Q: What's the difference between `no-cache` and `no-store`?

`no-store` says "do not store the response in any cache." `no-cache`
says "you may store the response, but you must revalidate with the origin
before using it." In practice, `no-cache` is rarely the right choice —
you pay the latency of a conditional request every time, and the body is
still re-sent if the version changed. Use `no-store` when freshness is
critical, and `max-age=0, must-revalidate` when you want the cache to
store but always revalidate (slightly cheaper than `no-cache` because
of how some caches implement them).

### Q: How does `stale-while-revalidate` work?

The cache serves the stale response immediately to the client, and
simultaneously issues a background fetch to the origin. The new response
replaces the stale entry in the cache; subsequent clients get the fresh
copy. The client that triggered the revalidation sees stale (one
`max-age`-window-old) data but does not pay the origin latency. Bounded
staleness, high hit rate.

### Q: How do you invalidate a CDN-cached response?

Three mechanisms: (1) let `max-age` expire and the cache revalidates;
(2) issue a purge via the CDN's API, keyed by URL or by surrogate key
(`Cache-Tag`, `Surrogate-Key`); (3) versioned URLs (`/v2/products/42`)
which are immutable and never need invalidation. The last is the most
robust — `Cache-Control: public, max-age=31536000, immutable` on
content-addressed assets.

### Q: What does `Vary: Authorization` do, and when does it hurt?

It tells the cache to include the `Authorization` header in the cache
key. This is *necessary* to safely cache authenticated responses
without cross-user data leaks — but `Authorization` values change per
user (different tokens), so the cache hit rate collapses to near zero.
For authenticated responses, prefer `Cache-Control: private` (browser
only) or partition the cache key explicitly (e.g., by `X-User-Id`
header) rather than varying on the raw `Authorization` value.

### Q: How do you cache GraphQL queries?

Hard. GraphQL queries are `POST` with bodies, so they don't fit HTTP
caching out of the box. Two workarounds: (1) **automatic persisted
queries** — the client first sends a SHA of the query, gets back an ID,
then sends the ID as `GET /graphql?id=<id>` which is cacheable; (2)
cache the response at the application layer (Redis) keyed by the query
hash + variables. Neither is as clean as REST's URL-based caching.

## Cross-References

- [REST](./rest.md) — REST is built around cacheability (the Cacheable constraint)
- [API Gateway](./api-gateway.md) — gateway-level response caching
- [Rate Limiting](./rate-limiting.md) — orthogonal resilience mechanism
- [Caching Strategies](../../sre/cache-patterns.md) — application-level cache patterns (write-through, write-back)
- [Redis](../messaging/redis.md) — common application-level cache store
- [Buffer Pool](../../dbms/caching/buffer-pool.md) — the DB-side analog (page cache)
- [Webhooks](./webhooks.md) — invalidation via event push

## References

- RFC 7234 — *Hypertext Transfer Protocol (HTTP/1.1): Caching* — <https://www.rfc-editor.org/rfc/rfc7234>
- RFC 7232 — *Hypertext Transfer Protocol (HTTP/1.1): Conditional Requests* — <https://www.rfc-editor.org/rfc/rfc7232>
- RFC 5861 — *HTTP Cache-Control Extensions for Stale Content* (`stale-while-revalidate`, `stale-if-error`) — <https://www.rfc-editor.org/rfc/rfc5861>
- MDN — *HTTP caching* — <https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching>
- web.dev — *Prevent unnecessary network requests with the HTTP Cache* — <https://web.dev/articles/http-caching>
- Cloudflare — *What is HTTP caching? How does it work?* — <https://www.cloudflare.com/learning/cdn/what-is-caching/>
- Fastly — *Surrogate keys for cache invalidation* — <https://www.fastly.com/blog/surrogate-keys-explained-fastly-cdn-cache-purging-logic-for-dynamic-content>
