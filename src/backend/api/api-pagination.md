# API Pagination Deep Dive — Offset, Cursor, Keyset, and the Relay Connection Model

## Overview

Pagination is the part of API design that quietly metastasizes. The naive
`?page=2&limit=20` works on a 200-row table and falls over at 20 million.
Every public API of any scale — Stripe, GitHub, Slack, Twitter, Twitter's
v2 follower endpoint famously — has migrated from offset pagination to
cursor pagination for the same reason: offset pagination is **O(offset)**
in the database, and that cost compounds as clients deep-page. This page
covers the four families of pagination, the **total count problem**, the
**Relay Connection spec** that GraphQL standardized, and the trade-offs
that drive the choice.

> Related: [REST](./rest.md), [GraphQL](./graphql.md) (Relay connections
> are native here), [Idempotency](../patterns/idempotency.md), [Database
> Indexing](../../dbms/indexing/README.md) (keyset pagination depends on
> an index), [PostgreSQL advanced features](../../dbms/postgresql/advanced-features.md).

## The Four Pagination Strategies

### 1. Offset / Limit (a.k.a. Page-Number) Pagination

```http
GET /api/orders?offset=20&limit=20 HTTP/1.1
GET /api/orders?page=2&per_page=20 HTTP/1.1   # same thing
```

SQL is trivial:

```sql
SELECT id, total, status
FROM orders
ORDER BY created_at DESC
LIMIT 20 OFFSET 20;
```

Implementation is one line. The client UX is also trivial: page numbers,
"jump to page 7", total pages badge.

**The cost is hidden in the `OFFSET 20`**. Most database engines (Postgres,
MySQL, Oracle) implement `OFFSET N` by *scanning and discarding* the first N
rows. The database still does the index scan, still reads the rows, still
materializes them, and then throws them away. So page 1 of 20-row pages is
fast; page 1,000 of 20-row pages scans and discards 19,980 rows; page
50,000 scans and discards 999,980 rows. **Deep pagination is O(offset)
in time and I/O**. This is exactly the failure mode that
[*Use The Index, Luke!*](https://use-the-index-luke.com/no-offset) catalogues
in detail.

```
  rows scanned (log scale)
                  │
  1,000,000 ──────┤██████████████████████████████  page 50,000
  100,000   ──────┤████████████████████████        page 5,000
  10,000    ──────┤████████████████                page 500
  1,000     ──────┤███████                         page 50
  100       ──────┤██                              page 5
                  └───────────────────────────────  page #
```

Two further pathologies of offset pagination:

1. **The missing-row problem (skew)**. While the client is paging, new rows
   get inserted at the head of the result set. Each page shifts: the client
   sees row #21 twice (once at the bottom of page 1's window, again at the
   top of page 2's window) or skips a row. For mutable feeds this makes
   offset pagination visibly broken.
2. **Stale totals**. The `total_count` shown at the top of the page is
   computed once per request; the more pages you have, the more out-of-date
   the total becomes.

### 2. Cursor-Based Pagination

```http
GET /api/orders?limit=20 HTTP/1.1
→ returns 20 rows + a cursor

GET /api/orders?cursor=eyJzayI6WyIyMDI0LTA2LTAxIiwiNDIiXX0&limit=20 HTTP/1.1
```

The cursor is an **opaque, server-issued token** that encodes the position
of the last row returned. The client treats it as a black box — never
inspects, never constructs one client-side. The server decodes it, applies
a `WHERE` predicate that resumes from that position.

```python
# pseudo: server-side decode + query
def list_orders(cursor_b64, limit):
    cursor = json.loads(base64decode(cursor_b64)) if cursor_b64 else None
    if cursor:
        # (created_at, id) of the last row returned previously
        last_sk = (cursor["created_at"], cursor["id"])
        rows = db.query(
            "SELECT id, total, status, created_at "
            "FROM orders "
            "WHERE (created_at, id) < %s "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT %s",
            (last_sk, limit + 1),
        )
    else:
        rows = db.query(
            "SELECT id, total, status, created_at "
            "FROM orders "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT %s",
            (limit + 1,),
        )
    has_next = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode({"created_at": rows[-1].created_at,
                          "id": rows[-1].id}) if has_next else None
    return {"data": rows, "next_cursor": next_cursor}
```

Two things to notice:

1. **The cursor is opaque.** It is base64 of a small JSON document, signed
   with an HMAC to prevent client tampering. The client does not parse it.
   This is what lets the server change the encoding later (e.g., add a sort
   key) without breaking existing cursors in flight.
2. **The `WHERE (created_at, id) < (last_created_at, last_id)` is a
   composite keyset predicate.** Postgres uses an index on
   `(created_at DESC, id DESC)` to satisfy this in O(log n + limit). No row
   scanning. No skew because the predicate is monotonic — new rows that
   arrive after the cursor position are not visible to this pagination
   walk.

This is what GitHub does — see
[*List issues for a repository*](https://docs.github.com/rest/issues/issues#list-issues-assigned-to-the-authenticated-user)
where `since` and `before` cursors are returned in `Link` headers — and
what Stripe documents at
[*Pagination*](https://docs.stripe.com/api/pagination).

### 3. Keyset Pagination

Keyset is the underlying technique used by cursor pagination. The cursor
is just an encoded keyset. The defining property: **the `WHERE` clause
resumes from the last key seen**.

```sql
-- page 1
SELECT id, created_at, total FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- page 2 (assume last row was created_at='2024-06-01', id=42)
SELECT id, created_at, total FROM orders
WHERE (created_at, id) < ('2024-06-01', 42)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Keyset requires:

1. A **stable, unique sort key**. `created_at` alone is not unique enough
   (rows can collide on the same timestamp); pair it with `id` for a
   composite `(created_at, id)` key.
2. An **index on that composite key**, in the same direction as the
   `ORDER BY`. Otherwise the database falls back to a sort-then-limit
   plan and you've lost the benefit.
3. **Idempotent predicates**. The `WHERE` predicate must be a strict
   less-than (or greater-than) over the composite key.

Pros of keyset/cursor:

- **O(log n + limit)** per page — page 50,000 is as fast as page 1.
- **No skew** under inserts (new rows before the cursor are invisible).
- **Resumable** — the cursor can be persisted and resumed later.

Cons:

- **No "jump to page 47"** — you can only walk forward and (with a
  symmetric cursor) backward.
- **No total count** — see below.
- **Cursor tied to sort order** — if the client requests a different
  `ORDER BY`, you need a different cursor.

### 4. The Relay Connection Spec (GraphQL Standard)

Facebook's Relay team published the [*Connection Model*](https://relay.dev/graphql/connections.htm)
specification to standardize cursor pagination in GraphQL. The shape is:

```graphql
type Query {
  orders(first: Int, after: String, last: Int, before: String): OrderConnection!
}

type OrderConnection {
  edges: [OrderEdge!]!
  pageInfo: PageInfo!
  totalCount: Int
}

type OrderEdge {
  cursor: String!
  node: Order!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

A query:

```graphql
query {
  orders(first: 20, after: "eyJjcmVhdGVkX2F0IjoiMjAyNC0wNi0wMSIsImlkIjo0Mn0") {
    edges {
      cursor
      node { id total status createdAt }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
    totalCount
  }
}
```

The model is opinionated and **fully cursor-based** — `first`/`after` walk
forward, `last`/`before` walk backward. `totalCount` is optional precisely
because it's expensive (see below). The Relay spec was adopted so widely
that even non-GraphQL APIs now mimic the shape (`edges`, `pageInfo`,
`hasNextPage`).

## The Total Count Problem

```http
HTTP/1.1 200 OK
Content-Type: application/json
{
  "data": [ ...20 rows... ],
  "total": 14_829_113,            ← this is the killer
  "page": 3,
  "page_size": 20
}
```

Computing `total` requires a `SELECT COUNT(*) FROM orders` (often with the
same filters the list query applies). On a 15M-row table this is a full
scan, every request. Postgres' MVCC requires walking the visibility map
to count — there is no constant-time count of live rows. The cost
shows up directly in p99 latency.

Mitigations:

| Approach | How | Cost |
|---|---|---|
| **Omit `total`** | Return only `{data, next_cursor}`. Show "Load more" instead of page numbers. | Cheapest; the modern default |
| **Approximate count** | Postgres `pg_class.reltuples` (post-analyze estimate); HyperLogLog for distinct counts | ±5-10% error, sub-millisecond |
| **Cached count** | Cache `COUNT(*)` for 60s in Redis; accept staleness | Stale, but bounded |
| **Separate endpoint** | `/orders/count` with its own cache + backpressure; clients opt in | Decouples from list latency |
| **Materialized view** | Pre-aggregate counts per filter combination; refresh nightly or via triggers | Operations cost, freshness lag |

The Stripe API explicitly omits total counts: the response gives you
`has_more: true/false` and a `next_page` URL. This is the
design-choice that says "I will not let `COUNT(*)` decide my p99".

## Comparison Table

| Strategy | Cost per page | Deep-page cost | Supports random access | Stable under inserts | Total count available | Best for |
|---|---|---|---|---|---|---|
| **Offset / limit** | O(offset + limit) — linear in offset | O(n) at page n/limit | Yes (jump to page k) | No (skew) | Yes (but expensive) | Admin UIs, ≤1k rows |
| **Cursor (opaque)** | O(log n + limit) | Constant | No (sequential only) | Yes | No (omit, or extra cost) | Public APIs, mutable feeds |
| **Keyset (raw)** | O(log n + limit) | Constant | No | Yes | No | Internal services, single sort |
| **Relay Connection** | O(log n + limit) | Constant | No | Yes | Optional (`totalCount`) | GraphQL, modern REST |

## Real-World Examples

### Stripe

Documented at <https://docs.stripe.com/api/pagination>. Stripe lists return
a `has_more: bool` and a `next_page` URL containing an encoded cursor.
There is no `total_count` field. The cursor is opaque; clients are warned
not to construct it.

```http
GET /v1/charges?limit=10 HTTP/1.1
→ {
    "data": [...10 charges...],
    "has_more": true,
    "next_page": "/v1/charges?cursor=xyz123&limit=10"
  }
```

### GitHub

Documented at <https://docs.github.com/rest/guides/traversing-with-pagination>.
GitHub uses `Link` headers (RFC 8288 — Web Linking) instead of a body
field:

```http
HTTP/1.1 200 OK
Link: <https://api.github.com/repos/octocat/hello-world/issues?page=2>; rel="next",
      <https://api.github.com/repos/octocat/hello-world/issues?page=53>; rel="last"
```

For endpoints where cursor pagination is supported (most v2 REST endpoints),
GitHub uses `before`/`after` query parameters with opaque string cursors.
The `Link: rel="next"` pattern lets the client follow pagination without
parsing URL templates.

### Slack

Slack's `conversations.list` returns both `response_metadata.next_cursor`
(cursor pagination) and is one of the earliest public APIs to
aggressively deprecate total counts.

## Bidirectional Pagination

For UIs that need to walk backward (e.g., "show me the page before this
one"), cursor pagination needs two cursors per response: a forward cursor
(after the last row) and a backward cursor (before the first row). The
Relay spec bakes this in: `pageInfo.endCursor` for forward, `pageInfo.startCursor`
for backward, with `first/after` and `last/before` argument pairs.

```http
GET /api/orders?limit=20&after=<endCursor>   # forward
GET /api/orders?limit=20&before=<startCursor> # backward
```

Implementing backward pagination requires a **symmetric index** — you walk
the index in reverse order. The composite key becomes
`(created_at DESC, id DESC)` for forward and
`(created_at ASC, id ASC)` for backward, and you need both indexes if
you're not on a database that can scan an index backward (Postgres can).

## Implementation Patterns

### Composite Keyset in SQL

```sql
-- schema
CREATE INDEX orders_created_at_id_idx
    ON orders (created_at DESC, id DESC);

-- page 1
SELECT id, created_at, total, status
FROM orders
ORDER BY created_at DESC, id DESC
LIMIT 21;     -- fetch one extra to know if there's a next page

-- page N+1 (cursor = (created_at, id) of last row of page N)
SELECT id, created_at, total, status
FROM orders
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC
LIMIT 21;
```

The `(created_at, id) < ($1, $2)` form is a **row-value comparison** that
Postgres supports natively (it expands to `(created_at < $1) OR
(created_at = $1 AND id < $2)`). The composite index supports it without
backtracking.

### Cursor Encoding (HMAC-signed, opaque)

```python
import base64, json, hmac, hashlib

SECRET = b"server-side-secret"

def encode_cursor(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    sig = hmac.new(SECRET, raw, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(raw + sig).decode().rstrip("=")

def decode_cursor(token: str) -> dict:
    pad = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + pad)
    body, sig = raw[:-16], raw[-16:]
    expected = hmac.new(SECRET, body, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(sig, expected):
        raise ValueError("invalid cursor")
    return json.loads(body)
```

HMAC-signing prevents clients from crafting arbitrary cursors (which could
enable index-bypassing queries or sort-order abuse). The cursor payload
should be small — just the keyset tuple — so the URL doesn't balloon.

## Common Pitfalls

1. **Cursors that aren't truly opaque.** Returning `?after=42` where `42`
   is the raw row ID lets clients construct cursors, which couples them to
   your internal schema and lets them page out-of-order in ways your server
   can't predict.
2. **Sort key without an index.** Cursor pagination without a matching
   composite index degrades to a sort-then-limit plan. `EXPLAIN ANALYZE`
   your queries.
3. **Sort key that isn't unique.** Sorting by `created_at` alone means
   rows with the same timestamp may be returned twice or skipped because
   the predicate `WHERE created_at < '2024-06-01'` excludes some rows with
   the same timestamp. Pair with a tiebreaker (`id`).
4. **Returning `total` with cursor pagination.** You're paying for both
   the cursor's fast list query and the slow `COUNT(*)` in the same
   request. Omit `total`, or move to a separate cached endpoint.
5. **Stale cursors after schema migration.** If you rename a column that
   the cursor encodes, all in-flight cursors break. Version the cursor
   payload (`{"v": 2, "sk": [...]}`) so old cursors can be migrated.

## Interview Questions

### Q: Why is `OFFSET 100000` slow?

Most databases implement `OFFSET N` by scanning and discarding the first
N rows. They still execute the index scan, still read pages from disk, still
materialize rows in memory — then throw them away. So page 5,000 of 20-row
pages scans 99,980 rows. Use cursor or keyset pagination to make it
O(log n + limit).

### Q: What does a cursor contain?

The cursor encodes the keyset tuple of the last row returned — typically
`(sort_field, tiebreaker_id)`, e.g., `(created_at, id)`. It is opaque
(base64 + HMAC-signed by the server) so clients can't construct or modify
it. The server decodes the cursor and uses the tuple in a `WHERE` predicate
that resumes the scan from that position.

### Q: How do you do "jump to page 7" with cursor pagination?

You don't — that's a real limitation. Cursor pagination is sequential:
forward and backward only. If the UI truly requires random page access
(e.g., admin dashboards over ≤1k rows), use offset pagination. For
infinite-scroll feeds, "load more" buttons, and most public APIs, cursor
is strictly better.

### Q: What is the Relay Connection model?

A GraphQL spec from Facebook's Relay team that standardizes cursor
pagination. The shape is: a `Connection` has `edges` (each edge has a
`cursor` and a `node`), plus `pageInfo` with `hasNextPage`,
`hasPreviousPage`, `startCursor`, `endCursor`. Arguments are
`first`/`after` (forward) and `last`/`before` (backward). `totalCount` is
optional. The spec is so widely adopted that many REST APIs mimic the
shape.

### Q: Why doesn't Stripe return `total_count`?

`SELECT COUNT(*) FROM orders` on a 15M-row table is a full scan under
Postgres MVCC. Stripe returns `has_more` (computed by fetching one extra
row) and a `next_page` cursor. This keeps p99 latency bounded; the total
is approximated client-side from `has_more` if the UI needs it.

## Cross-References

- [REST](./rest.md) — pagination as a REST design concern
- [GraphQL](./graphql.md) — Relay connections native to GraphQL
- [Database Indexing](../../dbms/indexing/README.md) — composite indexes power keyset
- [PostgreSQL Advanced Features](../../dbms/postgresql/advanced-features.md) — `pg_class.reltuples` for approximate counts
- [Idempotency](../patterns/idempotency.md) — pagination cursors aren't idempotency keys
- [REST](./rest.md) — `Link: rel="next"` for pagination URLs

## References

- Stripe — *Pagination* — <https://docs.stripe.com/api/pagination>
- GitHub — *Traversing with pagination* — <https://docs.github.com/rest/guides/traversing-with-pagination>
- Relay — *GraphQL Cursor Connections Specification* — <https://relay.dev/graphql/connections.htm>
- Use The Index, Luke — *No Offset* (keyset pagination deep dive) — <https://use-the-index-luke.com/no-offset>
- Use The Index, Luke — *Pagination Done the PostgreSQL Way* — <https://use-the-index-luke.com/sql/paging-results>
- Markus Winand — *Pagination Done the PostgreSQL Way* (talk) — <https://www.postgresql.org/about/news/pagination-done-the-postgresql-way-1766/>
- RFC 8288 — *Web Linking* (the `Link` header used by GitHub) — <https://www.rfc-editor.org/rfc/rfc8288>
- Slack API — *Pagination* (`response_metadata.next_cursor`) — <https://api.slack.com/docs/pagination>
