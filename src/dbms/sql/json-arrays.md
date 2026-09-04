# JSON and Arrays: Semi-Structured Data in SQL

Relational engines absorbed semi-structured data because applications need
it: API payloads, configuration documents, attribute bags, and per-tenant
custom fields all arrive as JSON with no fixed schema. Every major engine
now stores, queries, and indexes it — but each made different storage
trade-offs, and the difference between a fast and a pathological JSON query
is almost always *whether the data stays parsed between statements*. This
page covers the storage models, the query operators, indexing, the
standard's `JSON_TABLE`, and the schema-discipline that keeps document
columns from becoming write-only graveyards.

The engine-level storage background is in
[Record Formats](../storage/record-formats.md) and
[GIN Index](../indexing/gin.md); the NoSQL-native side of document models
is in [Document Databases](../nosql/document.md).

## Two storage philosophies: parse-per-read vs parse-per-write

| | Binary parsed (PostgreSQL `jsonb`, Oracle 21c Binary JSON, MongoDB BSON) | Text as-is (PostgreSQL `json`, MySQL JSON older versions, SQL Server NVARCHAR) |
|---|---|---|
| Write path | parse + normalize once | bytes in, bytes out |
| Read path | direct field access (pre-parsed) | re-parse per access |
| Whitespace/duplicate keys | dropped/last-wins | preserved |
| Equality/indexing | yes (btree on jsonb, GIN) | no (unless computed columns) |
| Best for | read-heavy documents | write-once, archive, pass-through |

The interview-worthy consequence: **`jsonb` trades write cost for read
cost.** A hot path that rewrites a document per request pays parse +
normalize + TOAST churn each time; a hot *read* path pays nothing after the
first parse. Picking the type is a workload decision, not a style choice —
and switching after the fact is a table rewrite.

```sql
-- PostgreSQL: the canonical pair
CREATE TABLE products (
  id          bigserial PRIMARY KEY,
  attrs       jsonb NOT NULL,            -- parsed, indexable
  raw_payload json      NOT NULL         -- exact vendor payload, archive
);
```

## Accessing fields: path operators and functions

```sql
-- PostgreSQL operators: -> (json) vs ->> (text), #> (path)
SELECT attrs ->> 'color'                  AS color_text,   -- text
       (attrs -> 'dimensions') ->> 'h'    AS height,       -- nested
       attrs #> '{dimensions,h}'          AS same_path,    -- path form
       (attrs ->> 'price')::numeric       AS price         -- cast to use in math
FROM products
WHERE attrs @> '{"color": "red"}';        -- containment: index-friendly!
```

Three rules that separate correct usage from the common bugs:

1. **`->>` returns text.** Comparing `attrs->>'price' > 10` compares
   *strings* ("9" > "10" lexicographically) — cast to numeric first. This
   is the JSON analogue of the
   [implicit-cast trap](../interview-problems/interview-traps.md), and it
   silently corrupts filters and sorts.
2. **Missing key ≠ NULL key ≠ `null` value.** `->> 'absent'` yields NULL,
   but a key present with JSON `null` also yields NULL — the
   [three-valued logic](../null-semantics.md) now has a fourth ambiguity
   layer ("was the key absent, or explicitly null?"). `?` (key exists) and
   `jsonb_typeof` disambiguate.
3. **Containment beats extraction for filters.** `attrs @> '{"color":"red"}'`
   is semantically "has color red" *and* is the predicate form GIN indexes
   serve; `attrs->>'color' = 'red'` is not. Same answer, two plan shapes.

Other engines use functions instead of operators — `JSON_EXTRACT(col,
'$.a.b')` (MySQL), `JSON_VALUE`/`JSON_QUERY` (SQL Server, Oracle) — with
the same semantics and the same text-returning trap (`JSON_VALUE` returns
NVARCHAR; SQL Server needs `CAST` or `WITH CONVERT`).

## Indexing JSON: three escalation levels

```sql
-- 1. Expression index on the known hot path (precise, btree semantics)
CREATE INDEX idx_products_color ON products ((attrs ->> 'color'));

-- 2. Generated column: the query optimizer treats it as a plain column
ALTER TABLE products
  ADD color text GENERATED ALWAYS AS (attrs ->> 'color') STORED;
CREATE INDEX idx_products_color2 ON products (color);

-- 3. GIN over the whole document: index any key's values
CREATE INDEX idx_products_attrs ON products USING gin (attrs);
CREATE INDEX idx_products_attrs_path ON products
  USING gin (attrs jsonb_path_ops);          -- smaller, containment-only
```

Escalation logic: expression indexes and generated columns serve *known,
hot* predicates with ordinary B-tree plans; whole-document GIN serves
*ad-hoc* key filters (`@>`, `?`, `jsonb_path_exists`) at the cost of
insert-heavy index maintenance — the GIN trade-offs are dissected in
[GIN Index](../indexing/gin.md). SQL Server reaches level 2 its own way:
computed columns over `JSON_VALUE` persisted + indexed, because its storage
is plain NVARCHAR with no native index.

## JSON_TABLE: the standard's answer to unnesting

Filtering documents is half the problem; the other half is *relational*
treatment of nested arrays — joining each array element to other tables.
SQL:2016 standardized `JSON_TABLE`, and PostgreSQL 16+ / Oracle / MySQL 8 /
SQL Server (as `OPENJSON`) all implement it:

```sql
SELECT p.id, ord.sku, ord.qty
FROM products p,
     JSON_TABLE(p.attrs, '$.orders[*]'
       COLUMNS (sku text PATH '$.sku',
                qty int  PATH '$.qty')) AS ord
WHERE ord.qty > 1;
```

This is the point where document-in-relational patterns either graduate to
a real design or rot: every "loop over elements in SQL" that isn't
`JSON_TABLE`/`OPENJSON`/`unnest` tends to become row-by-row application
code — the N+1 pattern with the network hop removed (see
[Correlated Subqueries](./correlated-subqueries.md) for the plan-shape
story).

## Arrays in SQL: containment, unnest, and the relational shape

```sql
-- PostgreSQL arrays: store, contain, expand
SELECT * FROM articles WHERE tags @> ARRAY['postgres'];   -- containment (GIN-indexable)
SELECT unnest(tags)                          FROM articles;  -- expand to rows
SELECT array_agg(tag ORDER BY tag) FROM article_tags GROUP BY article_id;  -- fold back
```

The design fork is real: **array column vs child table**. Array columns
win for read-mostly tag-like attributes queried by containment; child
tables win once elements need their own lifecycle (FKs, per-element
updates, [indexes on element attributes](../indexing/composite-index.md)).
The `unnest`-and-join form also powers
[relational division over array values](./relational-division.md) and the
[interval-union patterns](./temporal-sql-patterns.md) — arrays as a
temporary relational shape, not a permanent storage one.

## When NOT to put JSON in a column

- **Hot filter/join keys.** Every predicate on `attrs->>'status'` is an
  index miss waiting to happen (or an expression index to maintain).
  Promote frequently-filtered fields to real columns (generated or
  application-maintained) — schema-on-read is for the *long tail* of
  fields, not the hot head.
- **Cross-document constraints.** Foreign keys, uniqueness, and CHECK
  constraints stop at the document boundary; the relational model's
  enforcement story ([constraints](../advanced/README.md)) does not
  penetrate a JSON blob without `JSON_TABLE`-based triggers.
- **Row-per-element write patterns.** Appending to a 10k-element array
  rewrites the whole document (and its TOAST) per append — event streams
  want rows, not documents ([Record Formats](../storage/record-formats.md)).

The balanced production pattern: *narrow relational columns for identity
and hot predicates + one `jsonb` attribute bag for the long tail +
generated columns as the promoted subset* — schema-on-write for structure
that matters, schema-on-read for everything else.

## Interview questions

1. **`json` vs `jsonb` in PostgreSQL — when would you deliberately pick `json`?**
   Archive/pass-through of vendor payloads where exact byte preservation
   matters (order of keys, duplicates, whitespace for signatures), or
   write-once ingest where parse cost on write is pure overhead and reads
   are full-document.
2. **Why is `attrs->>'price' > 10` wrong?** Text comparison — "9" > "10".
   Cast, use a numeric expression index, or a generated column; then note
   the same class of bug in `JSON_VALUE` (returns NVARCHAR).
3. **How would you index "any key can be filtered" dashboards?** GIN on
   `jsonb` (optionally `jsonb_path_ops` for smaller footprint,
   containment-only); discuss write amplification on insert-heavy tables
   and when to fall back to promoted columns.
4. **What breaks when you store a 50 MB document in one row?** TOAST
   detoasting cost on every field access, no partial updates (whole-value
   rewrite per change), autovacuum pressure on hot rewrites — the
   [record format](../storage/record-formats.md) consequences, not just
   "it's big."

## Key Takeaways

- Parsed-binary (jsonb) vs text-as-is is a workload trade: parse once on
  write vs re-parse on every read; equality/indexing only exists on the
  parsed side.
- `->>` returns text (compare numerically after casting); containment
  operators (`@>`) are the indexable filter form; missing-key vs
  null-valued-key needs `?`/`jsonb_typeof`.
- Escalate indexing deliberately: expression index → generated column →
  whole-document GIN; each has a distinct write cost and query shape.
- `JSON_TABLE`/`OPENJSON`/`unnest` are the only set-based way to treat
  nested elements relationally; promote hot fields to real columns and
  keep JSON for the long tail.

## Cross-References

- [GIN Index](../indexing/gin.md) — inverted-index mechanics behind jsonb indexing.
- [Record Formats](../storage/record-formats.md) — TOAST and the cost model of wide documents.
- [Document Databases](../nosql/document.md) — the native-document alternative and its consistency story.
- [Null Semantics](../null-semantics.md) — the missing-key vs null-key ambiguity.
- [Correlated Subqueries](./correlated-subqueries.md) — the N+1 shape JSON element loops become.

## References

- PostgreSQL Documentation, "[JSON Types](https://www.postgresql.org/docs/current/datatype-json.html)" and "[JSON Functions and Operators](https://www.postgresql.org/docs/current/functions-json.html)" — jsonb storage, operators, containment, and `JSON_TABLE`.
- Microsoft Learn, "[JSON Data in SQL Server](https://learn.microsoft.com/en-us/sql/relational-databases/json/json-data-sql-server)" — `JSON_VALUE`/`OPENJSON` and computed-column indexing.
- Oracle Database 19c, "[JSON in Oracle Database](https://docs.oracle.com/en/database/oracle/oracle-database/19/adjsn/json-in-oracle-database.html)" — Binary JSON and `JSON_TABLE`.
- J. Michels, T. Hare, K. Kulkarni, C. Zuzarte, "[The New and Improved SQL](https://doi.org/10.1145/3299887.3299897)", *ACM SIGMOD Record* 46(4), 2018 — the SQL:2016 standard's JSON support.
