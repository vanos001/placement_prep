# PostgreSQL Overview

## Architecture

```
Client → Postmaster (master process)
              ├── Backend Process (per connection)
              │   ├── Parser
              │   ├── Rewriter
              │   ├── Planner/Optimizer
              │   └── Executor
              ├── Shared Buffers (shared memory)
              ├── WAL Buffers
              └── Background Workers
                  ├── bgwriter (writes dirty pages)
                  ├── checkpointer
                  ├── autovacuum
                  ├── stats collector
                  └── WAL archiver
```

## MVCC (Multi-Version Concurrency Control)

Each transaction sees a snapshot of the database. Readers don't block writers, writers don't block readers.

```
Row: (xmin=100, xmax=∞, data="Alice")
  - xmin: transaction that created this row
  - xmax: transaction that deleted this row (0 = live)
  
Transaction 101 reads: sees row (xmin=100 committed, xmax=0)
Transaction 102 updates: creates new row (xmin=102), sets xmax=102 on old row
Transaction 101 still sees old row (its snapshot is from before 102)
```

## VACUUM

MVCC creates dead tuples (old row versions). VACUUM reclaims space.

- **VACUUM**: Marks dead tuple space as reusable (doesn't return to OS)
- **VACUUM FULL**: Rewrites table, returns space to OS (blocks table)
- **autovacuum**: Background process that runs VACUUM automatically

```sql
-- Manual vacuum
VACUUM ANALYZE my_table;

-- Check dead tuples
SELECT relname, n_dead_tup, last_autovacuum 
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
```

## WAL (Write-Ahead Log)

All changes are written to WAL before modifying data files. This ensures:
- **Durability**: Committed changes survive crashes (replay WAL)
- **Atomicity**: Uncommitted changes are rolled back
- **Replication**: WAL shipped to replicas

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PostgreSQL Internals — Egor Rogov](https://postgrespro.com/education/books/internals)
