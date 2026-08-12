# PostgreSQL Interview Questions

**Q: What is the difference between VARCHAR and TEXT in PostgreSQL?**
A: No performance difference. VARCHAR(n) has a length constraint; TEXT does not. PostgreSQL internally stores both the same way. Use TEXT unless you need a constraint for data integrity.

**Q: What is a CTE and when would you use it?**
A: Common Table Expression — a temporary named result set defined with `WITH`. Use for: (1) readability (break complex queries), (2) recursion (hierarchical data), (3) reusing subqueries. Materialized CTEs (PostgreSQL 12+) are evaluated once; non-materialized may be inlined.

**Q: Explain PostgreSQL's EXPLAIN output.**
A: Shows the query execution plan. Key fields: node type (Seq Scan, Index Scan, etc.), actual rows, planned rows, startup cost, total cost, loops. `EXPLAIN ANALYZE` actually runs the query. `BUFFERS` shows cache hits vs disk reads. Large discrepancy between planned and actual rows → run ANALYZE.

**Q: What is TOAST in PostgreSQL?**
A: The Oversized-Attribute Storage Technique. Large field values are compressed and stored in a separate TOAST table. Transparent to users. Allows rows to exceed the 8KB page size. TOAST-ed values are fetched on demand.

**Q: How do you handle schema migrations in production?**
A: (1) Use migration tools (Flyway, Alembic, Rails migrations), (2) make migrations backward-compatible (add column, don't remove), (3) lock tables minimally, (4) test on staging with production-like data, (5) have a rollback plan, (6) use `CREATE INDEX CONCURRENTLY` to avoid locks.

## References

- [PostgreSQL Wiki](https://wiki.postgresql.org/)
- [PostgreSQL Exercises](https://pgexercises.com/)
