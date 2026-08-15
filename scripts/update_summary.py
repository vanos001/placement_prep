#!/usr/bin/env python3
"""Append new advanced topic sections to SUMMARY.md before the # Meta line."""

import re

NEW_SECTIONS = """
---

# Advanced Operating Systems Deep Dive

- [Advanced OS Overview](./os/advanced/README.md)
- [Kernel Architectures](./os/advanced/kernel-architectures.md)
- [Virtualization Internals](./os/advanced/virtualization.md)
- [Fast I/O (DPDK, SPDK, io_uring)](./os/advanced/fast-io.md)
- [Scheduler Internals](./os/advanced/scheduler-internals.md)
- [Synchronization Primitives](./os/advanced/sync-primitives.md)
- [Memory Models](./os/advanced/memory-models.md)
- [Memory Internals](./os/advanced/memory-internals.md)
- [I/O Internals](./os/advanced/io-internals.md)

---

# Linux Kernel Deep Dive

- [Kernel Advanced Overview](./os/kernel-advanced/README.md)
- [Boot Process](./os/kernel-advanced/boot-process.md)
- [Tracing & Probes](./os/kernel-advanced/tracing-probes.md)
- [eBPF Deep Dive](./os/kernel-advanced/ebpf-deep.md)
- [Namespaces & Cgroups](./os/kernel-advanced/namespaces-cgroups.md)
- [VFS Internals](./os/kernel-advanced/vfs-internals.md)
- [Network Stack](./os/kernel-advanced/network-stack.md)
- [Block Layer](./os/kernel-advanced/block-layer.md)

---

# Advanced Distributed Systems

- [Advanced Distributed Overview](./distributed/advanced/README.md)
- [Impossibility & Failure Models](./distributed/advanced/impossibility-models.md)
- [Quorum Systems](./distributed/advanced/quorum-systems.md)
- [Clocks & Consistency Models](./distributed/advanced/clocks-ordering.md)
- [CRDTs Deep Dive](./distributed/advanced/crdt-deep.md)
- [Distributed Snapshots & Mutual Exclusion](./distributed/advanced/distributed-snapshots.md)
- [Advanced Consensus](./distributed/advanced/consensus-advanced.md)
- [Advanced Replication](./distributed/advanced/replication-advanced.md)
- [Membership & Hashing](./distributed/advanced/membership-hashing.md)
- [Distributed Transactions](./distributed/advanced/distributed-transactions.md)

---

# Advanced Distributed Storage

- [Advanced Storage Overview](./storage/advanced/README.md)
- [Distributed File Systems](./storage/advanced/distributed-fs.md)
- [Erasure Coding Deep Dive](./storage/advanced/erasure-coding-deep.md)
- [Storage Engines](./storage/advanced/storage-engines.md)
- [Deduplication & CAS](./storage/advanced/dedup-cas.md)
- [Tiered & Persistent Storage](./storage/advanced/tiered-persistent.md)
- [Storage Internals](./storage/advanced/storage-internals.md)

---

# Advanced Database Systems

- [Advanced DB Overview](./dbms/advanced/README.md)
- [Query Optimizers](./dbms/advanced/query-optimizers.md)
- [Execution Engines](./dbms/advanced/execution-engines.md)
- [Advanced Indexing](./dbms/advanced/index-advanced.md)
- [Advanced Concurrency Control](./dbms/advanced/concurrency-advanced.md)
- [Distributed Databases](./dbms/advanced/distributed-databases.md)
- [Vector Databases](./dbms/advanced/vector-databases.md)
- [Graph Databases](./dbms/advanced/graph-databases.md)
- [Temporal & Streaming Databases](./dbms/advanced/temporal-streaming.md)
- [Approximate Query Processing & Privacy](./dbms/advanced/approximate-privacy.md)

---

# Advanced Algorithms

- [Advanced Algorithms Overview](./dsa/advanced/README.md)
- [Network Flow](./dsa/advanced/network-flow.md)
- [Dynamic Trees](./dsa/advanced/dynamic-trees.md)
- [Tree Techniques](./dsa/advanced/tree-techniques.md)
- [DP Optimization](./dsa/advanced/dp-optimization.md)
- [Polynomials & FFT](./dsa/advanced/polynomials.md)
- [Matrix Algorithms](./dsa/advanced/matrix-algorithms.md)
- [Streaming & Sublinear Algorithms](./dsa/advanced/streaming-sublinear.md)
- [Approximation & FPT](./dsa/advanced/approximation-fpt.md)
- [Parallel & Graph Algorithms](./dsa/advanced/parallel-graph-algorithms.md)

---

# Advanced Programming Languages & Compilers

- [Advanced Compilers Overview](./compilers/advanced/README.md)
- [Formal Semantics](./compilers/advanced/formal-semantics.md)
- [Type Systems](./compilers/advanced/type-systems.md)
- [Compilation Techniques](./compilers/advanced/compilation-techniques.md)
- [Type Inference](./compilers/advanced/type-inference.md)
- [Garbage Collection](./compilers/advanced/garbage-collection.md)
- [JIT & Runtime Optimization](./compilers/advanced/jit-optimization.md)
- [Compiler Optimizations](./compilers/advanced/compiler-optimizations.md)
- [WebAssembly & Runtimes](./compilers/advanced/wasm-runtimes.md)

---

# Advanced Computer Architecture

- [Advanced Architecture Overview](./arch/advanced/README.md)
- [Out-of-Order Execution](./arch/advanced/ooo-execution.md)
- [Advanced Branch Prediction](./arch/advanced/branch-prediction-advanced.md)
- [Side Channels & Transient Execution](./arch/advanced/side-channels.md)
- [Cache Coherence Advanced](./arch/advanced/cache-coherence-advanced.md)
- [Advanced Memory Systems](./arch/advanced/memory-system-advanced.md)
- [Modern Interconnects (CXL, Chiplets)](./arch/advanced/modern-interconnects.md)
- [Accelerators & GPUs](./arch/advanced/accelerators.md)

---

# High-Performance Computing

- [HPC Overview](./hpc/README.md)
- [MPI & Parallelism](./hpc/mpi-parallelism.md)
- [Collective Communication & Distributed Training](./hpc/collective-communication.md)
- [HPC Infrastructure](./hpc/hpc-infra.md)

---

# Networking Research

- [Advanced Networking Overview](./networks/advanced/README.md)
- [Programmable Networks (P4, SmartNICs)](./networks/advanced/programmable-networks.md)
- [Advanced Congestion Control](./networks/advanced/congestion-control-advanced.md)
- [Modern Network Architecture](./networks/advanced/modern-network-arch.md)
- [Data Center Topology](./networks/advanced/datacenter-topology.md)
- [Emerging Networks](./networks/advanced/emerging-networks.md)

---

# Formal Methods & Verification

- [Formal Methods Overview](./formal-methods/README.md)
- [Model Checking](./formal-methods/model-checking.md)
- [Temporal Logic](./formal-methods/temporal-logic.md)
- [Program Verification](./formal-methods/program-verification.md)
- [Verified Systems](./formal-methods/verified-systems.md)
- [Testing & Formal Methods](./formal-methods/testing-formal.md)
- [Distributed & Concurrency Verification](./formal-methods/distributed-verification.md)

---

# Security Research

- [Advanced Security Overview](./security/advanced/README.md)
- [Microarchitectural Attacks](./security/advanced/microarch-attacks.md)
- [Supply Chain Security](./security/advanced/supply-chain-advanced.md)
- [Sandboxing](./security/advanced/sandboxing.md)
- [Side-Channel Resistant Crypto](./security/advanced/side-channel-resistant.md)
- [Advanced Cryptography](./security/advanced/crypto-advanced.md)

---

# Blockchain & Decentralized Systems

- [Blockchain Overview](./blockchain/README.md)
- [Consensus Mechanisms](./blockchain/consensus-mechanisms.md)
- [Ethereum Internals](./blockchain/ethereum-internals.md)
- [Blockchain Security](./blockchain/blockchain-security.md)
- [Decentralized Infrastructure](./blockchain/decentralized-infra.md)

---

# AI Systems

- [AI Systems Advanced Overview](./llm/advanced/README.md)
- [Transformer Internals](./llm/advanced/transformer-internals.md)
- [Advanced Training](./llm/advanced/training-advanced.md)
- [Advanced Quantization](./llm/advanced/quantization-advanced.md)
- [Inference Systems](./llm/advanced/inference-systems.md)
- [Advanced RAG](./llm/advanced/rag-advanced.md)
- [Agent Systems](./llm/advanced/agent-systems.md)

---

# AI + Distributed Systems

- [AI Distributed Overview](./llm/advanced/distributed/README.md)
- [Distributed AI Infrastructure](./llm/advanced/distributed/distributed-ai-infra.md)
- [Distributed RAG](./llm/advanced/distributed/distributed-rag.md)
- [Disaggregated Inference](./llm/advanced/distributed/disaggregated-inference.md)
- [Distributed Training](./llm/advanced/distributed/distributed-training.md)

---

# Advanced Cloud & Serverless

- [Advanced Cloud Overview](./cloud/advanced/README.md)
- [Serverless Deep Dive](./cloud/advanced/serverless.md)
- [Multi-Cloud & Disaggregation](./cloud/advanced/multi-cloud-advanced.md)
- [Cloud Scheduling](./cloud/advanced/cloud-scheduling.md)

---

# Edge, IoT & Cyber-Physical Systems

- [Edge Computing Overview](./edge/README.md)
- [Edge Computing](./edge/edge-computing.md)
- [IoT Protocols](./edge/iot-protocols.md)
- [Embedded AI](./edge/embedded-ai.md)
- [Real-Time Systems](./edge/real-time-systems.md)

---

# Quantum Computing

- [Quantum Computing Overview](./quantum/README.md)
- [Quantum Fundamentals](./quantum/quantum-fundamentals.md)
- [Quantum Advanced Topics](./quantum/quantum-advanced.md)

---

# Software Supply Chain & Build Systems

- [Supply Chain Overview](./supply-chain/README.md)
- [Build Systems](./supply-chain/build-systems.md)
- [Software Supply Chain Security](./supply-chain/software-supply-chain.md)

---

# Advanced Observability & Production Systems

- [Advanced Production Engineering Overview](./production-engineering/advanced/README.md)
- [Advanced Observability](./production-engineering/advanced/observability-advanced.md)
- [Chaos Engineering & Resilience](./production-engineering/advanced/chaos-resilience.md)

"""

def main():
    with open("src/SUMMARY.md", "r") as f:
        content = f.read()

    # Find the # Meta line
    meta_pattern = re.compile(r"^(# Meta)", re.MULTILINE)
    match = meta_pattern.search(content)
    if not match:
        print("ERROR: Could not find '# Meta' in SUMMARY.md")
        return

    insert_pos = match.start()
    new_content = content[:insert_pos] + NEW_SECTIONS + content[insert_pos:]

    with open("src/SUMMARY.md", "w") as f:
        f.write(new_content)

    print(f"SUMMARY.md updated. New sections inserted before '# Meta'.")
    print(f"Original length: {len(content)} chars")
    print(f"New length: {len(new_content)} chars")

if __name__ == "__main__":
    main()
