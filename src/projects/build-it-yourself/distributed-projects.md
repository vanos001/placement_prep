# Distributed Systems Build-It-Yourself Projects

## 1. Build Raft

Implement the Raft consensus algorithm with leader election (randomized election timeouts, RequestVote RPC), log replication (AppendEntries RPC, matching log entries, commit index advancement), and log compaction via snapshots (serialize state, install snapshot RPC). Support a cluster of 3-5 nodes communicating over gRPC or raw TCP. Add a simple key-value state machine on top.

**Key concepts**: Leader election, term numbers, split vote prevention, log matching property, commit index, snapshotting, linearizability, network partitions. **Complexity**: Advanced (5-7 weeks). **References**: Raft paper (Ongaro & Ousterhout), `etcd/raft` source, MIT 6.824 Raft lab, pingcap/raft-rs.

## 2. Build Paxos

Implement single-decree Paxos (proposer, acceptor, learner roles; prepare/promise, accept/accepted phases) then extend to Multi-Paxos for agreeing on a sequence of values (log replication). Implement a distinguished leader to skip the prepare phase for most proposals. Handle duplicate accept messages and stale proposals correctly.

**Key concepts**: Quorum, proposal numbers, promises, accept, learning a chosen value, leader election in Paxos, Multi-Paxos log optimization, liveness vs safety. **Complexity**: Advanced (5-7 weeks). **References**: "Paxos Made Simple" (Lamport), Google Chubby paper, "Paxos Made Live" (Chandra et al.), ZooKeeper ZAB protocol.

## 3. Build a Gossip Protocol

Implement a SWIM-style (Scalable Weakly-consistent Infection-style Process group Membership) protocol. Nodes periodically pick a random peer, ping it, and if the ping fails, indirectly probe through a third node. Suspect nodes are marked after a configurable timeout and confirmed dead after another timeout. Disseminate membership updates via piggybacking on ping/ack messages.

**Key concepts**: Epidemic/gossip protocols, SWIM suspicion mechanism, indirect probing, dissemination (piggybacking vs anti-entropy), eventual consistency of membership views, failure detector accuracy. **Complexity**: Intermediate (3-4 weeks). **References**: SWIM paper (Das et al.), Serf membership protocol, Hashicorp Memberlist source, Cassandra gossip.

## 4. Build Consistent Hashing

Implement consistent hashing with a ring of virtual nodes (hash each physical node to K virtual positions on a 0-2^160 ring). Support adding and removing nodes with minimal key remapping (only keys in the affected range move). Measure the distribution uniformity and remapping cost. Extend with bounded loads to prevent any single node from receiving more than (1 + ε) × average load.

**Key concepts**: Hash ring, virtual nodes for load balancing, minimal remapping on topology change, bounded loads, hash function choice (MD5, MurmurHash), replication on the ring. **Complexity**: Beginner-Intermediate (2-3 weeks). **References**: Dynamo paper, `hashring` Go library, libketama, "Consistent Hashing and Random Trees" (Karger et al.).

## 5. Build a Distributed Lock

Implement a lease-based distributed lock with fencing tokens. The lock holder receives a monotonically increasing fencing token that must be checked on every resource access (e.g., write to storage includes the token). On lease expiry, a new holder gets a higher token, and stale holders are rejected. Handle clock drift with Time-To-Last-Beat (TTLB) or a simple lease extension mechanism.

**Key concepts**: Distributed mutual exclusion, lease-based locking, fencing tokens for liveness safety, clock drift problems, lock expiration and renewal, split-brain prevention, Chubby/etcd lock service. **Complexity**: Intermediate (3-4 weeks). **References**: "How to do distributed locking" (Martin Kleppmann), Redlock debate, etcd distributed locks doc, ZooKeeper recipes.

## 6. Build a Replicated Log

Implement a segmented replicated log backed by disk storage. Support appending entries, reading from a given offset, and truncating after a given index. Implement quorum-based writes (write to majority before acknowledging). Add log compaction (snapshot the state and truncate the log). Build a simple state machine that replays the log for crash recovery.

**Key concepts**: Write-ahead log, segment files, index/offset mapping, quorum writes, log truncation, compaction/snapshotting, sequential I/O, recovery replay. **Complexity**: Intermediate (3-4 weeks). **References**: Kafka log implementation (`Log` class), etcd WAL, BookKeeper ledger, Apache Pulsar managed ledger.

## 7. Build a Distributed Scheduler

Implement a task scheduler with a coordinator and a pool of worker nodes. The coordinator maintains a task queue, dispatches tasks to workers via heartbeats or pull-based requests, and detects stragglers (tasks taking significantly longer than the median). Implement speculative execution: re-launch a straggler task on another worker and accept whichever finishes first. Support task dependencies (DAG-based scheduling).

**Key concepts**: Master-worker architecture, task queue, heartbeat-based health checks, straggler detection, speculative execution, DAG scheduling, fault tolerance (task retry on worker failure). **Complexity**: Intermediate-Advanced (4-5 weeks). **References**: MapReduce paper (Dean & Ghemawat), Apache Spark DAGScheduler, Mesos scheduler, Ray scheduler.

> **Interview Angle**: "Design a distributed lock service" is a classic system design question. Having actually implemented fencing tokens and lease expiry makes your answer concrete — you can discuss real failure modes, edge cases, and trade-offs from experience rather than theory.