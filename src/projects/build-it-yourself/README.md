# Build-It-Yourself Track

The best way to deeply understand a system is to build one yourself. This track provides hands-on project guides across six domains: OS internals, databases, distributed systems, networking, compilers, and blockchain. Each project is scoped for a solo contributor over 2-8 weeks and is designed to teach the core concepts that come up in systems engineering interviews.

## Philosophy

These projects are not about building production software — they are about building *understanding*. You should implement each one from scratch (no frameworks, no copy-paste of full solutions) and be prepared to explain every design decision. The goal is internalized knowledge, not a GitHub repo.

## Projects by Domain

### [OS Projects](./os-projects.md)

Build the fundamental pieces of an operating system: a booting kernel, process scheduler, memory allocator, filesystem, shell, userspace TCP stack, debugger, and eBPF tracer. These projects teach you what happens below your application code.

### [Database Projects](./database-projects.md)

Build the storage engine internals that power every database: B-trees, LSM trees, write-ahead logs, MVCC, query optimizers, vector indexes, and distributed key-value stores.

### [Distributed Systems Projects](./distributed-projects.md)

Build the consensus protocols and infrastructure that make distributed systems work: Raft, Paxos, gossip membership, consistent hashing, distributed locks, and replicated logs.

### [Networking Projects](./networking-projects.md)

Build network protocols from the ground up: TCP, HTTP/1.1, HTTP/2, DNS, reverse proxies, and load balancers. Understand what the kernel does for you every time you call `connect()`.

### [Compiler Projects](./compiler-projects.md)

Build a compiler pipeline from front to back: lexer, parser, interpreter, bytecode VM, optimizer, and a toy JIT compiler. Understand how source code becomes machine code.

## Difficulty Guide

| Level | Description | Example Projects |
|-------|-------------|-----------------|
| **Beginner** | 2-3 weeks, clear algorithms | Lexer, B-tree, DNS resolver, Shell |
| **Intermediate** | 3-5 weeks, system design decisions | Parser, TCP, Raft, LSM tree |
| **Advanced** | 5-8 weeks, deep systems knowledge | JIT compiler, eBPF tracer, Query optimizer, Scheduler |

## Tips for Success

1. **Start small** — get the simplest working version first, then iterate.
2. **Write tests** — property-based tests are especially valuable for data structures.
3. **Compare against production** — test your B-tree against SQLite's, your TCP against the kernel's.
4. **Write it up** — document what you learned and what surprised you. This becomes interview material.
5. **Use C or Rust** — these force you to confront memory management, which is the point.

> **Interview Angle**: When asked "What's the most complex thing you've built?" a well-explained build-it-yourself project demonstrates deep systems understanding far better than listing technologies on a resume.