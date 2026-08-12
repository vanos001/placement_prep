# Elasticsearch

## Architecture

```
Cluster
├── Node 1 (master)
│   ├── Shard 0 (primary)
│   └── Shard 1 (replica)
├── Node 2
│   ├── Shard 1 (primary)
│   └── Shard 0 (replica)
└── Node 3
    └── Shard 2 (primary)
```

- **Cluster**: Collection of nodes
- **Node**: Single server
- **Index**: Collection of documents (like a database table)
- **Shard**: Subset of an index (enables horizontal scaling)
- **Replica**: Copy of a shard (high availability)
- **Document**: JSON object stored in an index

## Inverted Index

```
Term    → Document List
"cat"   → [doc1, doc3, doc7]
"dog"   → [doc2, doc3, doc5]
"fish"  → [doc1, doc4]
```

Each term also stores: frequency, position, offset.

## Mapping (Schema)

```json
{
  "mappings": {
    "properties": {
      "title": { "type": "text", "analyzer": "english" },
      "price": { "type": "float" },
      "tags": { "type": "keyword" },
      "created": { "type": "date" },
      "location": { "type": "geo_point" }
    }
  }
}
```

| Field Type | Use Case |
|---|---|
| `text` | Full-text search (analyzed) |
| `keyword` | Exact match, sorting, aggregations |
| `long/integer/float` | Numeric range queries |
| `date` | Date range queries |
| `boolean` | True/false filters |
| `geo_point` | Geographic queries |

## Query DSL

### Full-Text Search

```json
{
  "query": {
    "match": {
      "title": "elasticsearch tutorial"
    }
  }
}
```

### Bool Query

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "title": "elasticsearch" } }
      ],
      "filter": [
        { "range": { "price": { "gte": 10, "lte": 50 } } },
        { "term": { "status": "published" } }
      ],
      "must_not": [
        { "term": { "tags": "draft" } }
      ],
      "should": [
        { "match": { "body": "tutorial" } }
      ]
    }
  }
}
```

| Clause | Affects Score | Purpose |
|---|---|---|
| `must` | Yes | Must match (AND) |
| `filter` | No | Must match (cached, faster) |
| `should` | Yes | Should match (OR, boosts score) |
| `must_not` | No | Must not match |

### Aggregations

```json
{
  "aggs": {
    "by_category": {
      "terms": { "field": "category", "size": 10 },
      "aggs": {
        "avg_price": {
          "avg": { "field": "price" }
        }
      }
    }
  }
}
```

## Performance Tuning

- Use `filter` instead of `query` when scoring isn't needed
- Use `keyword` for exact matches, `text` for full-text
- Set appropriate shard count (aim for 10-50GB per shard)
- Use replicas for read scaling
- Bulk API for batch operations

## Interview Questions

**Q: What is an inverted index?**
A: A data structure mapping terms to the documents containing them. Like a book index — look up a word, find which pages it appears on. Enables fast full-text search without scanning every document.

**Q: What is the difference between `text` and `keyword` field types?**
A: `text` is analyzed (tokenized, lowercased, stemmed) for full-text search. `keyword` is stored as-is for exact match, sorting, and aggregations. Use `text` for "search by relevance", `keyword` for "filter by exact value".

**Q: Explain `must` vs `filter` in Elasticsearch bool queries.**
A: Both require the condition to match. `must` affects the relevance score (how well it matches). `filter` doesn't affect scoring and is cached, making it faster. Use `filter` for yes/no conditions (dates, status, ranges).

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/)
- [Elasticsearch: The Definitive Guide](https://www.elastic.co/guide/en/elasticsearch/guide/master/)
