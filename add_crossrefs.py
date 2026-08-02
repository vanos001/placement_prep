#!/usr/bin/env python3
"""Add cross-references to OS and DBMS pages."""

import os
import re

BASE = "/home/work/.openclaw/workspace/placement_prep/src"

# Cross-reference mapping: keyword in path -> list of (display_name, relative_path_from_os_or_dbms_section)
# We'll compute actual relative paths dynamically

# Master list of all pages in other sections with display names
CROSS_REF_DB = {
    # Architecture
    "arch/cpu": [("CPU Architecture", "arch/cpu/README.md"), ("Registers", "arch/cpu/registers.md"), ("ISA", "arch/cpu/isa.md")],
    "arch/memory-hierarchy": [("Cache Hierarchy", "arch/memory-hierarchy/README.md"), ("Cache Basics", "arch/memory-hierarchy/cache-basics.md"), ("Cache Mapping", "arch/memory-hierarchy/cache-mapping.md"), ("Write Policies", "arch/memory-hierarchy/write-policies.md"), ("Cache Coherence", "arch/memory-hierarchy/coherence.md"), ("MESI Protocol", "arch/memory-hierarchy/mesi.md")],
    "arch/io": [("I/O Architecture", "arch/io/README.md"), ("Buses", "arch/io/buses.md"), ("PCIe", "arch/io/pcie.md"), ("NVMe", "arch/io/nvme.md")],
    "arch/pipelining": [("CPU Pipelining", "arch/pipelining/README.md"), ("Branch Prediction", "arch/pipelining/branch-prediction.md"), ("Data Hazards", "arch/pipelining/data-hazards.md")],
    "arch/parallelism": [("Parallelism", "arch/parallelism/README.md"), ("GPU Architecture", "arch/parallelism/gpu.md"), ("SIMD", "arch/parallelism/simd.md"), ("SMT", "arch/parallelism/smt.md"), ("Multicore", "arch/parallelism/multicore.md")],
    "arch/memory-tech": [("DRAM", "arch/memory-tech/dram.md"), ("SRAM", "arch/memory-tech/sram.md"), ("DDR", "arch/memory-tech/ddr.md")],
    # Networks
    "networks/sockets": [("Sockets", "networks/sockets/README.md"), ("TCP Sockets", "networks/sockets/tcp.md"), ("UDP Sockets", "networks/sockets/udp.md"), ("Unix Sockets", "networks/sockets/unix.md"), ("I/O Multiplexing", "networks/sockets/io-multiplexing.md")],
    "networks/tcp": [("TCP Protocol", "networks/tcp/README.md"), ("TCP States", "networks/tcp/states.md"), ("Congestion Control", "networks/tcp/congestion-control.md"), ("Flow Control", "networks/tcp/flow-control.md"), ("Three-Way Handshake", "networks/tcp/three-way.md")],
    "networks/osi": [("OSI Model", "networks/osi/README.md"), ("Transport Layer", "networks/osi/transport.md"), ("Network Layer", "networks/osi/network.md")],
    "networks/http": [("HTTP Protocol", "networks/http/README.md"), ("HTTP/2", "networks/http/http2.md"), ("gRPC", "networks/http/grpc.md"), ("WebSocket", "networks/http/websocket.md")],
    "networks/dns": [("DNS", "networks/dns/README.md"), ("DNS Resolution", "networks/dns/resolution.md")],
    "networks/security": [("TLS/SSL", "networks/security/tls.md"), ("Firewalls", "networks/security/firewalls.md")],
    # Distributed
    "distributed/consensus": [("Consensus", "distributed/consensus/README.md"), ("Raft", "distributed/consensus/raft.md"), ("Paxos", "distributed/consensus/paxos.md")],
    "distributed/fundamentals": [("CAP Theorem", "distributed/fundamentals/cap.md"), ("Consistency Models", "distributed/fundamentals/consistency.md"), ("Vector Clocks", "distributed/fundamentals/vector-clocks.md"), ("Lamport Clocks", "distributed/fundamentals/lamport.md")],
    "distributed/replication": [("Replication", "distributed/replication/README.md"), ("Quorum", "distributed/replication/quorum.md"), ("Primary-Backup", "distributed/replication/primary-backup.md")],
    "distributed/partitioning": [("Partitioning", "distributed/partitioning/README.md"), ("Consistent Hashing", "distributed/partitioning/consistent-hashing.md")],
    "distributed/messaging": [("Kafka", "distributed/messaging/kafka.md"), ("Message Queues", "distributed/messaging/queues.md"), ("RabbitMQ", "distributed/messaging/rabbitmq.md")],
    # Concurrency
    "concurrency": [("Concurrency Overview", "concurrency/overview.md"), ("Thread Pools", "concurrency/thread-pools.md"), ("Producer-Consumer", "concurrency/producer-consumer.md"), ("Lock-Free", "concurrency/lock-free.md"), ("Readers-Writers", "concurrency/readers-writers.md"), ("Transactional Memory", "concurrency/transactional-memory.md")],
    # Cloud
    "cloud/kubernetes": [("Kubernetes", "cloud/kubernetes/README.md"), ("K8s Pods", "cloud/kubernetes/pods.md"), ("K8s Deployments", "cloud/kubernetes/deployments.md")],
    "cloud/virtualization": [("Hypervisors", "cloud/virtualization/hypervisors.md"), ("VM vs Container", "cloud/virtualization/vm-vs-container.md")],
    # Storage
    "storage": [("Storage Overview", "storage/overview.md"), ("SSD", "storage/ssd.md"), ("HDD", "storage/hdd.md"), ("NVMe Storage", "storage/nvme.md"), ("Distributed Storage", "storage/distributed.md"), ("Block Storage", "storage/block-storage.md"), ("Object Storage", "storage/object-storage.md")],
    # ML
    "ml": [("ML Overview", "ml/overview.md"), ("Feature Engineering", "ml/foundations/feature-engineering.md"), ("Model Serving", "ml/system-design/model-serving.md")],
}


def get_relative_prefix(file_path, section):
    """Get relative path prefix from a file to the src/ root.
    e.g., os/memory/paging.md -> ../../
    e.g., os/synchronization/deadlocks/avoidance.md -> ../../../
    """
    # file_path is like os/memory/paging.md
    # We need to go up to src/ level
    # Count depth: section/subsection/file.md -> need ../../
    rel = os.path.relpath(BASE, os.path.dirname(os.path.join(BASE, file_path)))
    return rel


def get_crossrefs_for_file(file_path):
    """Determine appropriate cross-references based on file path and content."""
    path_lower = file_path.lower()
    refs = []
    
    # OS files
    if path_lower.startswith("os/memory/paging"):
        refs = [
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("TLB", "../os/memory/tlb.md"),
            ("Page Tables", "../os/memory/page-tables.md"),
        ]
    elif path_lower.startswith("os/memory/tlb"):
        refs = [
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
            ("Paging", "../os/memory/paging.md"),
            ("Page Tables", "../os/memory/page-tables.md"),
            ("Cache Mapping", "../arch/memory-hierarchy/cache-mapping.md"),
        ]
    elif path_lower.startswith("os/memory/page-tables"):
        refs = [
            ("Paging", "../os/memory/paging.md"),
            ("TLB", "../os/memory/tlb.md"),
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("Multi-Level Page Tables", "../os/memory/multi-level-page-tables.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
        ]
    elif path_lower.startswith("os/memory/multi-level-page-tables"):
        refs = [
            ("Page Tables", "../os/memory/page-tables.md"),
            ("Paging", "../os/memory/paging.md"),
            ("Cache Mapping", "../arch/memory-hierarchy/cache-mapping.md"),
            ("Inverted Page Tables", "../os/memory/inverted-page-tables.md"),
        ]
    elif path_lower.startswith("os/memory/inverted-page-tables"):
        refs = [
            ("Page Tables", "../os/memory/page-tables.md"),
            ("Paging", "../os/memory/paging.md"),
            ("TLB", "../os/memory/tlb.md"),
            ("Hash Index", "../dbms/indexing/hash-index.md"),
        ]
    elif path_lower.startswith("os/memory/segmentation"):
        refs = [
            ("Paging", "../os/memory/paging.md"),
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("Memory Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("Buffer Management", "../dbms/storage/buffer-management.md"),
        ]
    elif path_lower.startswith("os/memory/swapping"):
        refs = [
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("Thrashing", "../os/virtual-memory/thrashing.md"),
            ("SSD", "../storage/ssd.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("os/memory/allocation-algorithms"):
        refs = [
            ("Buddy System", "../os/memory/buddy-system.md"),
            ("Slab Allocator", "../os/memory/slab-allocator.md"),
            ("Contiguous Allocation", "../os/memory/contiguous.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    elif path_lower.startswith("os/memory/buddy-system"):
        refs = [
            ("Allocation Algorithms", "../os/memory/allocation-algorithms.md"),
            ("Slab Allocator", "../os/memory/slab-allocator.md"),
            ("Memory Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    elif path_lower.startswith("os/memory/slab-allocator"):
        refs = [
            ("Buddy System", "../os/memory/buddy-system.md"),
            ("Allocation Algorithms", "../os/memory/allocation-algorithms.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Cache Basics", "../arch/memory-hierarchy/cache-basics.md"),
        ]
    elif path_lower.startswith("os/memory/contiguous"):
        refs = [
            ("Allocation Algorithms", "../os/memory/allocation-algorithms.md"),
            ("Segmentation", "../os/memory/segmentation.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
        ]
    elif path_lower.startswith("os/memory/mmap"):
        refs = [
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("Demand Paging", "../os/virtual-memory/demand-paging.md"),
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("Buffer Management", "../dbms/storage/buffer-management.md"),
            ("Memory-Mapped I/O", "../arch/io/README.md"),
        ]
    elif path_lower.startswith("os/memory/huge-pages"):
        refs = [
            ("Paging", "../os/memory/paging.md"),
            ("TLB", "../os/memory/tlb.md"),
            ("NUMA", "../os/memory/numa.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
        ]
    elif path_lower.startswith("os/memory/numa"):
        refs = [
            ("Cache Coherence", "../arch/memory-hierarchy/coherence.md"),
            ("MESI Protocol", "../arch/memory-hierarchy/mesi.md"),
            ("Huge Pages", "../os/memory/huge-pages.md"),
            ("Multicore", "../arch/parallelism/multicore.md"),
        ]
    elif path_lower == "os/memory/readme.md":
        refs = [
            ("Virtual Memory", "../os/virtual-memory/README.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("DRAM", "../arch/memory-tech/dram.md"),
        ]
    # Virtual Memory
    elif path_lower.startswith("os/virtual-memory/page-replacement"):
        refs = [
            ("LRU", "../os/virtual-memory/lru.md"),
            ("FIFO", "../os/virtual-memory/fifo.md"),
            ("Clock Algorithm", "../os/virtual-memory/clock.md"),
            ("Optimal", "../os/virtual-memory/optimal.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/lru"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("Clock Algorithm", "../os/virtual-memory/clock.md"),
            ("Cache Replacement", "../arch/memory-hierarchy/replacement.md"),
            ("Buffer Pool Replacement", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/fifo"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("LRU", "../os/virtual-memory/lru.md"),
            ("Clock Algorithm", "../os/virtual-memory/clock.md"),
            ("Cache Replacement", "../arch/memory-hierarchy/replacement.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/clock"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("LRU", "../os/virtual-memory/lru.md"),
            ("FIFO", "../os/virtual-memory/fifo.md"),
            ("Cache Replacement", "../arch/memory-hierarchy/replacement.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/optimal"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("LRU", "../os/virtual-memory/lru.md"),
            ("Cache Replacement", "../arch/memory-hierarchy/replacement.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/lfu"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("LRU", "../os/virtual-memory/lru.md"),
            ("Redis Caching", "../dbms/caching/redis.md"),
            ("Cache Replacement", "../arch/memory-hierarchy/replacement.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/demand-paging"):
        refs = [
            ("Paging", "../os/memory/paging.md"),
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("Thrashing", "../os/virtual-memory/thrashing.md"),
            ("Working Set", "../os/virtual-memory/working-set.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/thrashing"):
        refs = [
            ("Working Set", "../os/virtual-memory/working-set.md"),
            ("Demand Paging", "../os/virtual-memory/demand-paging.md"),
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("CPU Scheduling", "../os/scheduling/README.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/working-set"):
        refs = [
            ("Thrashing", "../os/virtual-memory/thrashing.md"),
            ("Demand Paging", "../os/virtual-memory/demand-paging.md"),
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("Cache Performance", "../arch/memory-hierarchy/performance.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/cow"):
        refs = [
            ("Process Creation", "../os/processes/creation.md"),
            ("Paging", "../os/memory/paging.md"),
            ("Fork", "../os/processes/creation.md"),
            ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/compression"):
        refs = [
            ("Swapping", "../os/memory/swapping.md"),
            ("Thrashing", "../os/virtual-memory/thrashing.md"),
            ("SSD", "../storage/ssd.md"),
        ]
    elif path_lower.startswith("os/virtual-memory/page-rejection"):
        refs = [
            ("Page Replacement", "../os/virtual-memory/page-replacement.md"),
            ("Thrashing", "../os/virtual-memory/thrashing.md"),
            ("Working Set", "../os/virtual-memory/working-set.md"),
        ]
    elif path_lower == "os/virtual-memory/readme.md":
        refs = [
            ("Paging", "../os/memory/paging.md"),
            ("Page Tables", "../os/memory/page-tables.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    # Processes
    elif path_lower.startswith("os/processes/context-switching"):
        refs = [
            ("CPU Scheduling", "../os/scheduling/README.md"),
            ("PCB", "../os/processes/pcb.md"),
            ("Process States", "../os/processes/states.md"),
            ("Pipelining", "../arch/pipelining/README.md"),
            ("Thread Pools", "../concurrency/thread-pools.md"),
        ]
    elif path_lower.startswith("os/processes/creation"):
        refs = [
            ("Process States", "../os/processes/states.md"),
            ("Zombie/Orphan", "../os/processes/zombie-orphan.md"),
            ("Copy-on-Write", "../os/virtual-memory/cow.md"),
            ("IPC", "../os/processes/ipc.md"),
        ]
    elif path_lower.startswith("os/processes/states"):
        refs = [
            ("PCB", "../os/processes/pcb.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
            ("Process Creation", "../os/processes/creation.md"),
            ("CPU Scheduling", "../os/scheduling/README.md"),
        ]
    elif path_lower.startswith("os/processes/pcb"):
        refs = [
            ("Process States", "../os/processes/states.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
            ("Registers", "../arch/cpu/registers.md"),
        ]
    elif path_lower.startswith("os/processes/zombie-orphan"):
        refs = [
            ("Process Creation", "../os/processes/creation.md"),
            ("Process States", "../os/processes/states.md"),
            ("Signals", "../os/processes/ipc-signals.md"),
        ]
    elif path_lower.startswith("os/processes/daemons"):
        refs = [
            ("Init Systems", "../os/boot/init-systems.md"),
            ("Process Creation", "../os/processes/creation.md"),
            ("Kubernetes Pods", "../cloud/kubernetes/pods.md"),
        ]
    elif path_lower.startswith("os/processes/ipc-message-queues"):
        refs = [
            ("IPC Overview", "../os/processes/ipc.md"),
            ("Message Queues", "../distributed/messaging/queues.md"),
            ("Kafka", "../distributed/messaging/kafka.md"),
            ("Sockets", "../os/processes/ipc-sockets.md"),
        ]
    elif path_lower.startswith("os/processes/ipc-pipes"):
        refs = [
            ("IPC Overview", "../os/processes/ipc.md"),
            ("Unix Sockets", "../networks/sockets/unix.md"),
            ("IPC Sockets", "../os/processes/ipc-sockets.md"),
            ("Process Creation", "../os/processes/creation.md"),
        ]
    elif path_lower.startswith("os/processes/ipc-shared-memory"):
        refs = [
            ("IPC Overview", "../os/processes/ipc.md"),
            ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
            ("Cache Coherence", "../arch/memory-hierarchy/coherence.md"),
            ("Shared Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("os/processes/ipc-signals"):
        refs = [
            ("IPC Overview", "../os/processes/ipc.md"),
            ("Zombie/Orphan", "../os/processes/zombie-orphan.md"),
            ("Interrupts", "../os/io/interrupts.md"),
        ]
    elif path_lower.startswith("os/processes/ipc-sockets"):
        refs = [
            ("IPC Overview", "../os/processes/ipc.md"),
            ("Network Sockets", "../networks/sockets/README.md"),
            ("TCP Sockets", "../networks/sockets/tcp.md"),
            ("Unix Sockets", "../networks/sockets/unix.md"),
        ]
    elif path_lower.startswith("os/processes/ipc"):
        refs = [
            ("Pipes", "../os/processes/ipc-pipes.md"),
            ("Shared Memory", "../os/processes/ipc-shared-memory.md"),
            ("Message Queues", "../os/processes/ipc-message-queues.md"),
            ("Signals", "../os/processes/ipc-signals.md"),
            ("Sockets", "../os/processes/ipc-sockets.md"),
        ]
    elif path_lower == "os/processes/readme.md":
        refs = [
            ("Threads", "../os/threads/README.md"),
            ("CPU Scheduling", "../os/scheduling/README.md"),
            ("IPC", "../os/processes/ipc.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
        ]
    # Scheduling
    elif path_lower.startswith("os/scheduling/fcfs"):
        refs = [
            ("SJF", "../os/scheduling/sjf.md"),
            ("Round Robin", "../os/scheduling/round-robin.md"),
            ("Scheduling Metrics", "../os/scheduling/metrics.md"),
            ("CPU Architecture", "../arch/cpu/README.md"),
        ]
    elif path_lower.startswith("os/scheduling/sjf"):
        refs = [
            ("FCFS", "../os/scheduling/fcfs.md"),
            ("Priority Scheduling", "../os/scheduling/priority.md"),
            ("Scheduling Metrics", "../os/scheduling/metrics.md"),
            ("CPU Architecture", "../arch/cpu/README.md"),
        ]
    elif path_lower.startswith("os/scheduling/round-robin"):
        refs = [
            ("FCFS", "../os/scheduling/fcfs.md"),
            ("Multilevel Queue", "../os/scheduling/multilevel-queue.md"),
            ("Scheduling Metrics", "../os/scheduling/metrics.md"),
            ("Timer Interrupts", "../os/io/interrupts.md"),
        ]
    elif path_lower.startswith("os/scheduling/priority"):
        refs = [
            ("SJF", "../os/scheduling/sjf.md"),
            ("Multilevel Feedback", "../os/scheduling/multilevel-feedback.md"),
            ("Real-Time Scheduling", "../os/scheduling/realtime.md"),
            ("Starvation", "../os/scheduling/metrics.md"),
        ]
    elif path_lower.startswith("os/scheduling/multilevel-feedback"):
        refs = [
            ("Multilevel Queue", "../os/scheduling/multilevel-queue.md"),
            ("Round Robin", "../os/scheduling/round-robin.md"),
            ("Priority Scheduling", "../os/scheduling/priority.md"),
            ("Linux CFS", "../os/scheduling/linux-cfs.md"),
        ]
    elif path_lower.startswith("os/scheduling/multilevel-queue"):
        refs = [
            ("Multilevel Feedback", "../os/scheduling/multilevel-feedback.md"),
            ("Priority Scheduling", "../os/scheduling/priority.md"),
            ("Round Robin", "../os/scheduling/round-robin.md"),
        ]
    elif path_lower.startswith("os/scheduling/realtime"):
        refs = [
            ("Priority Scheduling", "../os/scheduling/priority.md"),
            ("Rate Monotonic", "../os/scheduling/realtime.md"),
            ("CPU Architecture", "../arch/cpu/README.md"),
            ("Interrupts", "../os/io/interrupts.md"),
        ]
    elif path_lower.startswith("os/scheduling/linux-cfs"):
        refs = [
            ("Multilevel Feedback", "../os/scheduling/multilevel-feedback.md"),
            ("Red-Black Trees", "../dbms/indexing/b-tree.md"),
            ("Scheduling Metrics", "../os/scheduling/metrics.md"),
            ("Process States", "../os/processes/states.md"),
        ]
    elif path_lower.startswith("os/scheduling/metrics"):
        refs = [
            ("FCFS", "../os/scheduling/fcfs.md"),
            ("SJF", "../os/scheduling/sjf.md"),
            ("Round Robin", "../os/scheduling/round-robin.md"),
            ("CPU Performance", "../arch/performance/equation.md"),
        ]
    elif path_lower == "os/scheduling/readme.md":
        refs = [
            ("CPU Architecture", "../arch/cpu/README.md"),
            ("Process States", "../os/processes/states.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
            ("Thread Pools", "../concurrency/thread-pools.md"),
        ]
    # Threads
    elif path_lower.startswith("os/threads/user-vs-kernel"):
        refs = [
            ("Thread Models", "../os/threads/models.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
            ("SMT", "../arch/parallelism/smt.md"),
            ("Green Threads", "../os/threads/green-threads.md"),
        ]
    elif path_lower.startswith("os/threads/models"):
        refs = [
            ("User vs Kernel Threads", "../os/threads/user-vs-kernel.md"),
            ("Thread Pools", "../os/threads/pools.md"),
            ("Thread Safety", "../os/threads/safety.md"),
            ("Concurrency Overview", "../concurrency/overview.md"),
        ]
    elif path_lower.startswith("os/threads/pools"):
        refs = [
            ("Thread Models", "../os/threads/models.md"),
            ("Thread Pools (Concurrency)", "../concurrency/thread-pools.md"),
            ("Producer-Consumer", "../concurrency/producer-consumer.md"),
            ("Fork-Join", "../concurrency/fork-join.md"),
        ]
    elif path_lower.startswith("os/threads/safety"):
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Lock-Free", "../os/synchronization/lock-free.md"),
            ("Readers-Writers", "../os/synchronization/readers-writers.md"),
            ("Thread Safety (Concurrency)", "../concurrency/lock-free.md"),
        ]
    elif path_lower.startswith("os/threads/green-threads"):
        refs = [
            ("User vs Kernel Threads", "../os/threads/user-vs-kernel.md"),
            ("Coroutines", "../concurrency/coroutines.md"),
            ("Async/Await", "../concurrency/async-await.md"),
            ("Go Channels", "../concurrency/go-channels.md"),
        ]
    elif path_lower == "os/threads/readme.md":
        refs = [
            ("Process vs Thread", "../os/processes/README.md"),
            ("Thread Models", "../os/threads/models.md"),
            ("Synchronization", "../os/synchronization/README.md"),
            ("Concurrency Overview", "../concurrency/overview.md"),
        ]
    # Synchronization
    elif path_lower.startswith("os/synchronization/mutex"):
        refs = [
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Spinlocks", "../os/synchronization/spinlocks.md"),
            ("Monitors", "../os/synchronization/monitors.md"),
            ("Deadlocks", "../os/synchronization/deadlocks/README.md"),
            ("Lock-Based Concurrency", "../dbms/transactions/lock-based.md"),
        ]
    elif path_lower.startswith("os/synchronization/semaphores"):
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Critical Section", "../os/synchronization/critical-section.md"),
            ("Dining Philosophers", "../os/synchronization/dining-philosophers.md"),
            ("Producer-Consumer", "../concurrency/producer-consumer.md"),
        ]
    elif path_lower.startswith("os/synchronization/spinlocks"):
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("CAS", "../os/synchronization/cas.md"),
            ("Lock-Free", "../os/synchronization/lock-free.md"),
            ("Cache Coherence", "../arch/memory-hierarchy/coherence.md"),
        ]
    elif path_lower.startswith("os/synchronization/critical-section"):
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Peterson's", "../os/synchronization/petersons.md"),
            ("Monitors", "../os/synchronization/monitors.md"),
            ("Serializability", "../dbms/transactions/serializability.md"),
        ]
    elif path_lower.startswith("os/synchronization/petersons"):
        refs = [
            ("Critical Section", "../os/synchronization/critical-section.md"),
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
            ("CPU Architecture", "../arch/cpu/README.md"),
        ]
    elif path_lower.startswith("os/synchronization/monitors"):
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Condition Variables", "../os/synchronization/monitors.md"),
            ("Java Concurrency", "../concurrency/java.md"),
        ]
    elif path_lower.startswith("os/synchronization/dining-philosophers"):
        refs = [
            ("Deadlocks", "../os/synchronization/deadlocks/README.md"),
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Resource Allocation", "../os/synchronization/deadlocks/bankers.md"),
        ]
    elif path_lower.startswith("os/synchronization/readers-writers"):
        refs = [
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Mutex", "../os/synchronization/mutex.md"),
            ("MVCC", "../dbms/transactions/mvcc.md"),
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
            ("Readers-Writers (Concurrency)", "../concurrency/readers-writers.md"),
        ]
    elif path_lower.startswith("os/synchronization/sleeping-barber"):
        refs = [
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Dining Philosophers", "../os/synchronization/dining-philosophers.md"),
            ("Producer-Consumer", "../concurrency/producer-consumer.md"),
        ]
    elif path_lower.startswith("os/synchronization/cas"):
        refs = [
            ("Spinlocks", "../os/synchronization/spinlocks.md"),
            ("Lock-Free", "../os/synchronization/lock-free.md"),
            ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
            ("Atomic Operations", "../arch/cpu/README.md"),
        ]
    elif path_lower.startswith("os/synchronization/lock-free"):
        refs = [
            ("CAS", "../os/synchronization/cas.md"),
            ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
            ("Lock-Free (Concurrency)", "../concurrency/lock-free.md"),
            ("Optimistic Concurrency", "../dbms/transactions/optimistic.md"),
        ]
    elif path_lower.startswith("os/synchronization/memory-barriers"):
        refs = [
            ("Cache Coherence", "../arch/memory-hierarchy/coherence.md"),
            ("MESI Protocol", "../arch/memory-hierarchy/mesi.md"),
            ("CAS", "../os/synchronization/cas.md"),
            ("Lock-Free", "../os/synchronization/lock-free.md"),
        ]
    elif path_lower == "os/synchronization/readme.md":
        refs = [
            ("Mutex", "../os/synchronization/mutex.md"),
            ("Semaphores", "../os/synchronization/semaphores.md"),
            ("Deadlocks", "../os/synchronization/deadlocks/README.md"),
            ("Concurrency Overview", "../concurrency/overview.md"),
            ("Lock-Based Concurrency", "../dbms/transactions/lock-based.md"),
        ]
    # Deadlocks
    elif path_lower.startswith("os/synchronization/deadlocks/avoidance"):
        refs = [
            ("Banker's Algorithm", "../os/synchronization/deadlocks/bankers.md"),
            ("Deadlock Prevention", "../os/synchronization/deadlocks/prevention.md"),
            ("Deadlock Detection", "../os/synchronization/deadlocks/detection.md"),
        ]
    elif path_lower.startswith("os/synchronization/deadlocks/bankers"):
        refs = [
            ("Deadlock Avoidance", "../os/synchronization/deadlocks/avoidance.md"),
            ("Resource Allocation", "../os/synchronization/deadlocks/README.md"),
            ("Dining Philosophers", "../os/synchronization/dining-philosophers.md"),
        ]
    elif path_lower.startswith("os/synchronization/deadlocks/detection"):
        refs = [
            ("Deadlock Avoidance", "../os/synchronization/deadlocks/avoidance.md"),
            ("Deadlock Recovery", "../os/synchronization/deadlocks/recovery.md"),
            ("Deadlock Prevention", "../os/synchronization/deadlocks/prevention.md"),
            ("Wait-For Graph", "../os/synchronization/deadlocks/README.md"),
        ]
    elif path_lower.startswith("os/synchronization/deadlocks/prevention"):
        refs = [
            ("Deadlock Avoidance", "../os/synchronization/deadlocks/avoidance.md"),
            ("Deadlock Detection", "../os/synchronization/deadlocks/detection.md"),
            ("Two-Phase Locking", "../dbms/transactions/lock-based.md"),
        ]
    elif path_lower.startswith("os/synchronization/deadlocks/recovery"):
        refs = [
            ("Deadlock Detection", "../os/synchronization/deadlocks/detection.md"),
            ("Process Termination", "../os/processes/states.md"),
            ("Transaction Recovery", "../dbms/transactions/recovery.md"),
        ]
    elif path_lower == "os/synchronization/deadlocks/readme.md":
        refs = [
            ("Deadlock Prevention", "../os/synchronization/deadlocks/prevention.md"),
            ("Deadlock Avoidance", "../os/synchronization/deadlocks/avoidance.md"),
            ("Deadlock Detection", "../os/synchronization/deadlocks/detection.md"),
            ("Dining Philosophers", "../os/synchronization/dining-philosophers.md"),
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
        ]
    # I/O
    elif path_lower.startswith("os/io/interrupts"):
        refs = [
            ("Device Drivers", "../os/io/device-drivers.md"),
            ("DMA", "../os/io/dma.md"),
            ("CPU Control Unit", "../arch/cpu/control-unit.md"),
            ("Context Switching", "../os/processes/context-switching.md"),
        ]
    elif path_lower.startswith("os/io/dma"):
        refs = [
            ("Interrupts", "../os/io/interrupts.md"),
            ("I/O Hardware", "../os/io/hardware.md"),
            ("Buses", "../arch/io/buses.md"),
            ("PCIe", "../arch/io/pcie.md"),
        ]
    elif path_lower.startswith("os/io/device-drivers"):
        refs = [
            ("Interrupts", "../os/io/interrupts.md"),
            ("I/O Software Layers", "../os/io/software-layers.md"),
            ("I/O Hardware", "../os/io/hardware.md"),
            ("VFS", "../os/filesystems/vfs.md"),
        ]
    elif path_lower.startswith("os/io/hardware"):
        refs = [
            ("DMA", "../os/io/dma.md"),
            ("Interrupts", "../os/io/interrupts.md"),
            ("Buses", "../arch/io/buses.md"),
            ("I/O Architecture", "../arch/io/README.md"),
        ]
    elif path_lower.startswith("os/io/software-layers"):
        refs = [
            ("Device Drivers", "../os/io/device-drivers.md"),
            ("VFS", "../os/filesystems/vfs.md"),
            ("Buffering", "../os/io/buffering.md"),
            ("I/O Architecture", "../arch/io/README.md"),
        ]
    elif path_lower.startswith("os/io/buffering"):
        refs = [
            ("I/O Software Layers", "../os/io/software-layers.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Buffer Management", "../dbms/storage/buffer-management.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    elif path_lower.startswith("os/io/disk-scheduling"):
        refs = [
            ("FCFS", "../os/io/disk-fcfs.md"),
            ("SSTF", "../os/io/disk-sstf.md"),
            ("SCAN", "../os/io/disk-scan.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("os/io/disk-fcfs"):
        refs = [
            ("Disk Scheduling Overview", "../os/io/disk-scheduling.md"),
            ("SSTF", "../os/io/disk-sstf.md"),
            ("SCAN", "../os/io/disk-scan.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("os/io/disk-sstf"):
        refs = [
            ("Disk Scheduling Overview", "../os/io/disk-scheduling.md"),
            ("FCFS", "../os/io/disk-fcfs.md"),
            ("SCAN", "../os/io/disk-scan.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("os/io/disk-scan"):
        refs = [
            ("Disk Scheduling Overview", "../os/io/disk-scheduling.md"),
            ("C-SCAN", "../os/io/disk-cscan.md"),
            ("LOOK", "../os/io/disk-look.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("os/io/disk-cscan"):
        refs = [
            ("SCAN", "../os/io/disk-scan.md"),
            ("LOOK", "../os/io/disk-look.md"),
            ("Disk Scheduling Overview", "../os/io/disk-scheduling.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("os/io/disk-look"):
        refs = [
            ("SCAN", "../os/io/disk-scan.md"),
            ("C-SCAN", "../os/io/disk-cscan.md"),
            ("Disk Scheduling Overview", "../os/io/disk-scheduling.md"),
        ]
    elif path_lower == "os/io/readme.md":
        refs = [
            ("I/O Architecture", "../arch/io/README.md"),
            ("Device Drivers", "../os/io/device-drivers.md"),
            ("Interrupts", "../os/io/interrupts.md"),
            ("DMA", "../os/io/dma.md"),
            ("Storage Overview", "../storage/overview.md"),
        ]
    # Filesystems
    elif path_lower.startswith("os/filesystems/vfs"):
        refs = [
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("Device Drivers", "../os/io/device-drivers.md"),
            ("I/O Software Layers", "../os/io/software-layers.md"),
            ("File Organization (DBMS)", "../dbms/storage/file-organization.md"),
        ]
    elif path_lower.startswith("os/filesystems/file-concepts"):
        refs = [
            ("VFS", "../os/filesystems/vfs.md"),
            ("Directory Structure", "../os/filesystems/directory-structure.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("Record Formats", "../dbms/storage/record-formats.md"),
        ]
    elif path_lower.startswith("os/filesystems/directory-structure"):
        refs = [
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("VFS", "../os/filesystems/vfs.md"),
            ("B-Tree Indexing", "../dbms/indexing/b-tree.md"),
        ]
    elif path_lower.startswith("os/filesystems/disk-allocation"):
        refs = [
            ("Contiguous Allocation", "../os/memory/contiguous.md"),
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("HDD", "../storage/hdd.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    elif path_lower.startswith("os/filesystems/free-space"):
        refs = [
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("Bitmap Index", "../dbms/indexing/bitmap-index.md"),
        ]
    elif path_lower.startswith("os/filesystems/journaling"):
        refs = [
            ("ext4", "../os/filesystems/ext4.md"),
            ("WAL", "../dbms/internals/wal.md"),
            ("Recovery", "../dbms/transactions/recovery.md"),
            ("ARIES", "../dbms/transactions/aries.md"),
        ]
    elif path_lower.startswith("os/filesystems/raid"):
        refs = [
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
            ("HDD", "../storage/hdd.md"),
            ("SSD", "../storage/ssd.md"),
            ("Erasure Coding", "../storage/erasure-coding.md"),
            ("Replication", "../distributed/replication/README.md"),
        ]
    elif path_lower.startswith("os/filesystems/ext4"):
        refs = [
            ("Journaling", "../os/filesystems/journaling.md"),
            ("VFS", "../os/filesystems/vfs.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
        ]
    elif path_lower.startswith("os/filesystems/btrfs"):
        refs = [
            ("Journaling", "../os/filesystems/journaling.md"),
            ("ZFS", "../os/filesystems/zfs.md"),
            ("Copy-on-Write", "../os/virtual-memory/cow.md"),
        ]
    elif path_lower.startswith("os/filesystems/zfs"):
        refs = [
            ("Btrfs", "../os/filesystems/btrfs.md"),
            ("RAID", "../os/filesystems/raid.md"),
            ("Erasure Coding", "../storage/erasure-coding.md"),
            ("Copy-on-Write", "../os/virtual-memory/cow.md"),
        ]
    elif path_lower.startswith("os/filesystems/xfs"):
        refs = [
            ("Journaling", "../os/filesystems/journaling.md"),
            ("VFS", "../os/filesystems/vfs.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
        ]
    elif path_lower.startswith("os/filesystems/ntfs"):
        refs = [
            ("Journaling", "../os/filesystems/journaling.md"),
            ("VFS", "../os/filesystems/vfs.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
        ]
    elif path_lower.startswith("os/filesystems/fuse"):
        refs = [
            ("VFS", "../os/filesystems/vfs.md"),
            ("Device Drivers", "../os/io/device-drivers.md"),
            ("User vs Kernel", "../os/threads/user-vs-kernel.md"),
            ("Object Storage", "../storage/object-storage.md"),
        ]
    elif path_lower == "os/filesystems/readme.md":
        refs = [
            ("VFS", "../os/filesystems/vfs.md"),
            ("File Concepts", "../os/filesystems/file-concepts.md"),
            ("Disk Allocation", "../os/filesystems/disk-allocation.md"),
            ("File Organization (DBMS)", "../dbms/storage/file-organization.md"),
            ("Storage Overview", "../storage/overview.md"),
        ]
    # Containers
    elif path_lower.startswith("os/containers/docker"):
        refs = [
            ("Namespaces", "../os/containers/namespaces.md"),
            ("Cgroups", "../os/containers/cgroups.md"),
            ("VM vs Container", "../cloud/virtualization/vm-vs-container.md"),
            ("Kubernetes", "../os/containers/kubernetes.md"),
        ]
    elif path_lower.startswith("os/containers/kubernetes"):
        refs = [
            ("Docker", "../os/containers/docker.md"),
            ("K8s Pods", "../cloud/kubernetes/pods.md"),
            ("K8s Deployments", "../cloud/kubernetes/deployments.md"),
            ("Service Discovery", "../distributed/microservices/discovery.md"),
        ]
    elif path_lower.startswith("os/containers/namespaces"):
        refs = [
            ("Cgroups", "../os/containers/cgroups.md"),
            ("Docker", "../os/containers/docker.md"),
            ("Security", "../os/security/README.md"),
            ("Process Creation", "../os/processes/creation.md"),
        ]
    elif path_lower.startswith("os/containers/cgroups"):
        refs = [
            ("Namespaces", "../os/containers/namespaces.md"),
            ("Docker", "../os/containers/docker.md"),
            ("Scheduling", "../os/scheduling/README.md"),
            ("Resource Management", "../os/memory/numa.md"),
        ]
    elif path_lower == "os/containers/readme.md":
        refs = [
            ("Docker", "../os/containers/docker.md"),
            ("Kubernetes", "../os/containers/kubernetes.md"),
            ("Namespaces", "../os/containers/namespaces.md"),
            ("VM vs Container", "../cloud/virtualization/vm-vs-container.md"),
            ("Hypervisors", "../cloud/virtualization/hypervisors.md"),
        ]
    # Boot
    elif path_lower.startswith("os/boot/bios-uefi"):
        refs = [
            ("Bootloader", "../os/boot/bootloader.md"),
            ("Init Systems", "../os/boot/init-systems.md"),
            ("I/O Hardware", "../os/io/hardware.md"),
        ]
    elif path_lower.startswith("os/boot/bootloader"):
        refs = [
            ("BIOS/UEFI", "../os/boot/bios-uefi.md"),
            ("Init Systems", "../os/boot/init-systems.md"),
            ("Kernel Threads", "../os/threads/user-vs-kernel.md"),
        ]
    elif path_lower.startswith("os/boot/init-systems"):
        refs = [
            ("Bootloader", "../os/boot/bootloader.md"),
            ("Daemons", "../os/processes/daemons.md"),
            ("Kubernetes Pods", "../cloud/kubernetes/pods.md"),
            ("Process Creation", "../os/processes/creation.md"),
        ]
    elif path_lower == "os/boot/readme.md":
        refs = [
            ("BIOS/UEFI", "../os/boot/bios-uefi.md"),
            ("Bootloader", "../os/boot/bootloader.md"),
            ("Init Systems", "../os/boot/init-systems.md"),
        ]
    # Security
    elif path_lower.startswith("os/security/access-control"):
        refs = [
            ("Capabilities", "../os/security/capabilities.md"),
            ("SELinux", "../os/security/selinux.md"),
            ("Namespaces", "../os/containers/namespaces.md"),
            ("TLS/SSL", "../networks/security/tls.md"),
        ]
    elif path_lower.startswith("os/security/capabilities"):
        refs = [
            ("Access Control", "../os/security/access-control.md"),
            ("SELinux", "../os/security/selinux.md"),
            ("Namespaces", "../os/containers/namespaces.md"),
        ]
    elif path_lower.startswith("os/security/selinux"):
        refs = [
            ("Access Control", "../os/security/access-control.md"),
            ("Capabilities", "../os/security/capabilities.md"),
            ("Namespaces", "../os/containers/namespaces.md"),
            ("Firewalls", "../networks/security/firewalls.md"),
        ]
    elif path_lower == "os/security/readme.md":
        refs = [
            ("Access Control", "../os/security/access-control.md"),
            ("Capabilities", "../os/security/capabilities.md"),
            ("SELinux", "../os/security/selinux.md"),
            ("Namespaces", "../os/containers/namespaces.md"),
        ]
    # OS Overview
    elif path_lower == "os/overview.md":
        refs = [
            ("CPU Architecture", "../arch/cpu/README.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("Networks Overview", "../networks/overview.md"),
            ("DBMS Overview", "../dbms/overview.md"),
            ("Concurrency Overview", "../concurrency/overview.md"),
        ]
    
    # ===== DBMS FILES =====
    # Caching
    elif path_lower.startswith("dbms/caching/buffer-pool"):
        refs = [
            ("Paging (OS)", "../os/memory/paging.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
            ("Buffer Management", "../dbms/storage/buffer-management.md"),
            ("LRU (OS)", "../os/virtual-memory/lru.md"),
            ("DRAM", "../arch/memory-tech/dram.md"),
        ]
    elif path_lower.startswith("dbms/caching/redis"):
        refs = [
            ("Memcached", "../dbms/caching/memcached.md"),
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("Pub/Sub", "../distributed/messaging/pubsub.md"),
        ]
    elif path_lower.startswith("dbms/caching/memcached"):
        refs = [
            ("Redis", "../dbms/caching/redis.md"),
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("LRU (OS)", "../os/virtual-memory/lru.md"),
        ]
    elif path_lower.startswith("dbms/caching/query-cache"):
        refs = [
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Redis", "../dbms/caching/redis.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    elif path_lower == "dbms/caching/readme.md":
        refs = [
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Redis", "../dbms/caching/redis.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("Paging (OS)", "../os/memory/paging.md"),
        ]
    # Transactions
    elif path_lower.startswith("dbms/transactions/acid"):
        refs = [
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
            ("Concurrency Control", "../dbms/transactions/concurrency-control.md"),
            ("WAL", "../dbms/internals/wal.md"),
            ("Serializability", "../dbms/transactions/serializability.md"),
            ("Consensus", "../distributed/consensus/raft.md"),
        ]
    elif path_lower.startswith("dbms/transactions/mvcc"):
        refs = [
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
            ("Timestamp-Based", "../dbms/transactions/timestamp-based.md"),
            ("Readers-Writers (OS)", "../os/synchronization/readers-writers.md"),
            ("Consistency Models", "../distributed/fundamentals/consistency.md"),
            ("Optimistic Concurrency", "../dbms/transactions/optimistic.md"),
        ]
    elif path_lower.startswith("dbms/transactions/lock-based"):
        refs = [
            ("Mutex (OS)", "../os/synchronization/mutex.md"),
            ("Deadlocks (OS)", "../os/synchronization/deadlocks/README.md"),
            ("Two-Phase Locking", "../dbms/transactions/lock-based.md"),
            ("Concurrency Control", "../dbms/transactions/concurrency-control.md"),
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
        ]
    elif path_lower.startswith("dbms/transactions/optimistic"):
        refs = [
            ("MVCC", "../dbms/transactions/mvcc.md"),
            ("Timestamp-Based", "../dbms/transactions/timestamp-based.md"),
            ("CAS (OS)", "../os/synchronization/cas.md"),
            ("Lock-Free (OS)", "../os/synchronization/lock-free.md"),
        ]
    elif path_lower.startswith("dbms/transactions/timestamp-based"):
        refs = [
            ("MVCC", "../dbms/transactions/mvcc.md"),
            ("Optimistic Concurrency", "../dbms/transactions/optimistic.md"),
            ("Lamport Clocks", "../distributed/fundamentals/lamport.md"),
            ("Vector Clocks", "../distributed/fundamentals/vector-clocks.md"),
        ]
    elif path_lower.startswith("dbms/transactions/isolation-levels"):
        refs = [
            ("ACID", "../dbms/transactions/acid.md"),
            ("MVCC", "../dbms/transactions/mvcc.md"),
            ("Serializability", "../dbms/transactions/serializability.md"),
            ("Concurrency Control", "../dbms/transactions/concurrency-control.md"),
            ("Consistency Models", "../distributed/fundamentals/consistency.md"),
        ]
    elif path_lower.startswith("dbms/transactions/serializability"):
        refs = [
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
            ("Concurrency Control", "../dbms/transactions/concurrency-control.md"),
            ("Lock-Based", "../dbms/transactions/lock-based.md"),
            ("Critical Section (OS)", "../os/synchronization/critical-section.md"),
        ]
    elif path_lower.startswith("dbms/transactions/concurrency-control"):
        refs = [
            ("Lock-Based", "../dbms/transactions/lock-based.md"),
            ("MVCC", "../dbms/transactions/mvcc.md"),
            ("Optimistic", "../dbms/transactions/optimistic.md"),
            ("Timestamp-Based", "../dbms/transactions/timestamp-based.md"),
            ("Mutex (OS)", "../os/synchronization/mutex.md"),
        ]
    elif path_lower.startswith("dbms/transactions/two-phase-commit"):
        refs = [
            ("Three-Phase Commit", "../dbms/transactions/three-phase-commit.md"),
            ("Distributed Transactions", "../dbms/transactions/distributed.md"),
            ("Consensus (Raft)", "../distributed/consensus/raft.md"),
            ("Paxos", "../distributed/consensus/paxos.md"),
            ("Deadlocks (OS)", "../os/synchronization/deadlocks/README.md"),
        ]
    elif path_lower.startswith("dbms/transactions/three-phase-commit"):
        refs = [
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
            ("Distributed Transactions", "../dbms/transactions/distributed.md"),
            ("Consensus (Raft)", "../distributed/consensus/raft.md"),
        ]
    elif path_lower.startswith("dbms/transactions/distributed"):
        refs = [
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
            ("CAP Theorem", "../distributed/fundamentals/cap.md"),
            ("Consistency Models", "../distributed/fundamentals/consistency.md"),
            ("Sharding", "../dbms/distributed/sharding.md"),
            ("Saga Pattern", "../dbms/transactions/saga.md"),
        ]
    elif path_lower.startswith("dbms/transactions/saga"):
        refs = [
            ("Distributed Transactions", "../dbms/transactions/distributed.md"),
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
            ("Circuit Breakers", "../distributed/microservices/circuit-breakers.md"),
            ("Eventual Consistency", "../distributed/fundamentals/consistency.md"),
        ]
    elif path_lower.startswith("dbms/transactions/recovery"):
        refs = [
            ("WAL", "../dbms/internals/wal.md"),
            ("ARIES", "../dbms/transactions/aries.md"),
            ("Checkpointing", "../dbms/transactions/checkpointing.md"),
            ("Deadlock Recovery (OS)", "../os/synchronization/deadlocks/recovery.md"),
        ]
    elif path_lower.startswith("dbms/transactions/aries"):
        refs = [
            ("WAL", "../dbms/internals/wal.md"),
            ("Recovery", "../dbms/transactions/recovery.md"),
            ("Checkpointing", "../dbms/transactions/checkpointing.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("dbms/transactions/checkpointing"):
        refs = [
            ("WAL", "../dbms/internals/wal.md"),
            ("ARIES", "../dbms/transactions/aries.md"),
            ("Recovery", "../dbms/transactions/recovery.md"),
        ]
    elif path_lower.startswith("dbms/transactions/log-recovery"):
        refs = [
            ("WAL", "../dbms/internals/wal.md"),
            ("ARIES", "../dbms/transactions/aries.md"),
            ("Recovery", "../dbms/transactions/recovery.md"),
        ]
    elif path_lower.startswith("dbms/transactions/states"):
        refs = [
            ("ACID", "../dbms/transactions/acid.md"),
            ("Process States (OS)", "../os/processes/states.md"),
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
        ]
    elif path_lower == "dbms/transactions/readme.md":
        refs = [
            ("ACID", "../dbms/transactions/acid.md"),
            ("Concurrency Control", "../dbms/transactions/concurrency-control.md"),
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
            ("Synchronization (OS)", "../os/synchronization/README.md"),
            ("Distributed Consensus", "../distributed/consensus/raft.md"),
        ]
    # Indexing
    elif path_lower.startswith("dbms/indexing/b-tree"):
        refs = [
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
            ("Disk Scheduling (OS)", "../os/io/disk-scheduling.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    elif path_lower.startswith("dbms/indexing/b-plus-tree"):
        refs = [
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Disk Scheduling (OS)", "../os/io/disk-scheduling.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("SSD", "../storage/ssd.md"),
        ]
    elif path_lower.startswith("dbms/indexing/hash-index"):
        refs = [
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("Cache Mapping", "../arch/memory-hierarchy/cache-mapping.md"),
        ]
    elif path_lower.startswith("dbms/indexing/bitmap-index"):
        refs = [
            ("Composite Index", "../dbms/indexing/composite-index.md"),
            ("Column Stores", "../dbms/storage/column-stores.md"),
            ("SIMD", "../arch/parallelism/simd.md"),
        ]
    elif path_lower.startswith("dbms/indexing/clustered-vs-nonclustered"):
        refs = [
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Disk Allocation (OS)", "../os/filesystems/disk-allocation.md"),
        ]
    elif path_lower.startswith("dbms/indexing/composite-index"):
        refs = [
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("Covering Index", "../dbms/indexing/covering-index.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
        ]
    elif path_lower.startswith("dbms/indexing/covering-index"):
        refs = [
            ("Composite Index", "../dbms/indexing/composite-index.md"),
            ("Clustered vs Nonclustered", "../dbms/indexing/clustered-vs-nonclustered.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
        ]
    elif path_lower.startswith("dbms/indexing/gin"):
        refs = [
            ("GiST", "../dbms/indexing/gist.md"),
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Inverted Index", "../dbms/indexing/gin.md"),
        ]
    elif path_lower.startswith("dbms/indexing/gist"):
        refs = [
            ("GIN", "../dbms/indexing/gin.md"),
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
        ]
    elif path_lower.startswith("dbms/indexing/tuning"):
        refs = [
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("Composite Index", "../dbms/indexing/composite-index.md"),
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
        ]
    elif path_lower == "dbms/indexing/readme.md":
        refs = [
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Hash Index", "../dbms/indexing/hash-index.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    # Internals
    elif path_lower.startswith("dbms/internals/wal"):
        refs = [
            ("Recovery", "../dbms/transactions/recovery.md"),
            ("ARIES", "../dbms/transactions/aries.md"),
            ("Journaling (OS)", "../os/filesystems/journaling.md"),
            ("Checkpointing", "../dbms/transactions/checkpointing.md"),
            ("Write Policies", "../arch/memory-hierarchy/write-policies.md"),
        ]
    elif path_lower.startswith("dbms/internals/lsm-trees"):
        refs = [
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Compaction", "../dbms/internals/compaction.md"),
            ("WAL", "../dbms/internals/wal.md"),
            ("SSD", "../storage/ssd.md"),
            ("Write Policies", "../arch/memory-hierarchy/write-policies.md"),
        ]
    elif path_lower.startswith("dbms/internals/compaction"):
        refs = [
            ("LSM Trees", "../dbms/internals/lsm-trees.md"),
            ("WAL", "../dbms/internals/wal.md"),
            ("SSD", "../storage/ssd.md"),
            ("Garbage Collection", "../os/memory/swapping.md"),
        ]
    elif path_lower.startswith("dbms/internals/engines"):
        refs = [
            ("LSM Trees", "../dbms/internals/lsm-trees.md"),
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    elif path_lower == "dbms/internals/readme.md":
        refs = [
            ("WAL", "../dbms/internals/wal.md"),
            ("LSM Trees", "../dbms/internals/lsm-trees.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
        ]
    # Storage
    elif path_lower.startswith("dbms/storage/buffer-management"):
        refs = [
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Paging (OS)", "../os/memory/paging.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    elif path_lower.startswith("dbms/storage/file-organization"):
        refs = [
            ("Record Formats", "../dbms/storage/record-formats.md"),
            ("File Concepts (OS)", "../os/filesystems/file-concepts.md"),
            ("Disk Allocation (OS)", "../os/filesystems/disk-allocation.md"),
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("HDD", "../storage/hdd.md"),
        ]
    elif path_lower.startswith("dbms/storage/record-formats"):
        refs = [
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("File Concepts (OS)", "../os/filesystems/file-concepts.md"),
            ("Column Stores", "../dbms/storage/column-stores.md"),
        ]
    elif path_lower.startswith("dbms/storage/column-stores"):
        refs = [
            ("Record Formats", "../dbms/storage/record-formats.md"),
            ("Bitmap Index", "../dbms/indexing/bitmap-index.md"),
            ("SIMD", "../arch/parallelism/simd.md"),
            ("Compression", "../ml/advanced/compression.md"),
        ]
    elif path_lower == "dbms/storage/readme.md":
        refs = [
            ("Buffer Management", "../dbms/storage/buffer-management.md"),
            ("File Organization", "../dbms/storage/file-organization.md"),
            ("Storage Overview", "../storage/overview.md"),
            ("File Systems (OS)", "../os/filesystems/README.md"),
        ]
    # Query Processing
    elif path_lower.startswith("dbms/query-processing/joins"):
        refs = [
            ("Nested Loop", "../dbms/query-processing/nested-loop.md"),
            ("Hash Join", "../dbms/query-processing/hash-join.md"),
            ("Sort Merge", "../dbms/query-processing/sort-merge.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/nested-loop"):
        refs = [
            ("Hash Join", "../dbms/query-processing/hash-join.md"),
            ("Sort Merge", "../dbms/query-processing/sort-merge.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("Cache Performance", "../arch/memory-hierarchy/performance.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/hash-join"):
        refs = [
            ("Nested Loop", "../dbms/query-processing/nested-loop.md"),
            ("Sort Merge", "../dbms/query-processing/sort-merge.md"),
            ("Hash Index", "../dbms/indexing/hash-index.md"),
            ("Cache Hierarchy", "../arch/memory-hierarchy/README.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/sort-merge"):
        refs = [
            ("Nested Loop", "../dbms/query-processing/nested-loop.md"),
            ("Hash Join", "../dbms/query-processing/hash-join.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
            ("External Sorting", "../dbms/query-processing/sort-merge.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/optimization"):
        refs = [
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
            ("Cost Estimation", "../dbms/query-processing/cost-estimation.md"),
            ("Indexing", "../dbms/indexing/README.md"),
            ("Query Cache", "../dbms/caching/query-cache.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/execution-plans"):
        refs = [
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Cost Estimation", "../dbms/query-processing/cost-estimation.md"),
            ("Join Algorithms", "../dbms/query-processing/joins.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/cost-estimation"):
        refs = [
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Buffer Pool", "../dbms/caching/buffer-pool.md"),
        ]
    elif path_lower.startswith("dbms/query-processing/parsing"):
        refs = [
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
            ("SQL DDL", "../dbms/sql/ddl.md"),
        ]
    elif path_lower == "dbms/query-processing/readme.md":
        refs = [
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Join Algorithms", "../dbms/query-processing/joins.md"),
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
            ("Indexing", "../dbms/indexing/README.md"),
        ]
    # Distributed DBMS
    elif path_lower.startswith("dbms/distributed/cap"):
        refs = [
            ("CAP Theorem (Distributed)", "../distributed/fundamentals/cap.md"),
            ("Consistency Models", "../distributed/fundamentals/consistency.md"),
            ("Sharding", "../dbms/distributed/sharding.md"),
            ("Replication", "../dbms/distributed/replication.md"),
        ]
    elif path_lower.startswith("dbms/distributed/consensus"):
        refs = [
            ("Raft", "../distributed/consensus/raft.md"),
            ("Paxos", "../distributed/consensus/paxos.md"),
            ("Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
            ("Distributed Transactions", "../dbms/transactions/distributed.md"),
        ]
    elif path_lower.startswith("dbms/distributed/consistency"):
        refs = [
            ("Consistency Models (Distributed)", "../distributed/fundamentals/consistency.md"),
            ("CAP Theorem", "../dbms/distributed/cap.md"),
            ("Replication", "../dbms/distributed/replication.md"),
            ("Isolation Levels", "../dbms/transactions/isolation-levels.md"),
        ]
    elif path_lower.startswith("dbms/distributed/paxos"):
        refs = [
            ("Raft", "../dbms/distributed/raft.md"),
            ("Paxos (Distributed)", "../distributed/consensus/paxos.md"),
            ("Consensus", "../dbms/distributed/consensus.md"),
        ]
    elif path_lower.startswith("dbms/distributed/raft"):
        refs = [
            ("Paxos", "../dbms/distributed/paxos.md"),
            ("Raft (Distributed)", "../distributed/consensus/raft.md"),
            ("Consensus", "../dbms/distributed/consensus.md"),
            ("Leader Election", "../distributed/consensus/raft.md"),
        ]
    elif path_lower.startswith("dbms/distributed/replication"):
        refs = [
            ("Consistency Models", "../dbms/distributed/consistency.md"),
            ("Replication (Distributed)", "../distributed/replication/README.md"),
            ("Quorum", "../distributed/replication/quorum.md"),
            ("CAP Theorem", "../dbms/distributed/cap.md"),
        ]
    elif path_lower.startswith("dbms/distributed/sharding"):
        refs = [
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("CAP Theorem", "../dbms/distributed/cap.md"),
            ("Replication", "../dbms/distributed/replication.md"),
            ("Range Partitioning", "../distributed/partitioning/range.md"),
        ]
    elif path_lower == "dbms/distributed/readme.md":
        refs = [
            ("CAP Theorem", "../dbms/distributed/cap.md"),
            ("Consensus", "../dbms/distributed/consensus.md"),
            ("Sharding", "../dbms/distributed/sharding.md"),
            ("Replication", "../dbms/distributed/replication.md"),
            ("Distributed Overview", "../distributed/overview.md"),
        ]
    # Normalization
    elif path_lower.startswith("dbms/normalization/1nf"):
        refs = [
            ("2NF", "../dbms/normalization/2nf.md"),
            ("Keys", "../dbms/relational-model/keys.md"),
            ("ER Diagrams", "../dbms/relational-model/er-diagrams.md"),
        ]
    elif path_lower.startswith("dbms/normalization/2nf"):
        refs = [
            ("1NF", "../dbms/normalization/1nf.md"),
            ("3NF", "../dbms/normalization/3nf.md"),
            ("Keys", "../dbms/relational-model/keys.md"),
        ]
    elif path_lower.startswith("dbms/normalization/3nf"):
        refs = [
            ("2NF", "../dbms/normalization/2nf.md"),
            ("BCNF", "../dbms/normalization/bcnf.md"),
            ("Denormalization", "../dbms/normalization/denormalization.md"),
        ]
    elif path_lower.startswith("dbms/normalization/bcnf"):
        refs = [
            ("3NF", "../dbms/normalization/3nf.md"),
            ("4NF/5NF", "../dbms/normalization/4nf-5nf.md"),
            ("Keys", "../dbms/relational-model/keys.md"),
        ]
    elif path_lower.startswith("dbms/normalization/4nf-5nf"):
        refs = [
            ("BCNF", "../dbms/normalization/bcnf.md"),
            ("Denormalization", "../dbms/normalization/denormalization.md"),
            ("Relational Algebra", "../dbms/relational-model/relational-algebra.md"),
        ]
    elif path_lower.startswith("dbms/normalization/denormalization"):
        refs = [
            ("3NF", "../dbms/normalization/3nf.md"),
            ("BCNF", "../dbms/normalization/bcnf.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Redis Caching", "../dbms/caching/redis.md"),
        ]
    elif path_lower == "dbms/normalization/readme.md":
        refs = [
            ("1NF", "../dbms/normalization/1nf.md"),
            ("3NF", "../dbms/normalization/3nf.md"),
            ("BCNF", "../dbms/normalization/bcnf.md"),
            ("Keys", "../dbms/relational-model/keys.md"),
        ]
    # Relational Model
    elif path_lower.startswith("dbms/relational-model/er-diagrams"):
        refs = [
            ("Keys", "../dbms/relational-model/keys.md"),
            ("Relational Algebra", "../dbms/relational-model/relational-algebra.md"),
            ("1NF", "../dbms/normalization/1nf.md"),
        ]
    elif path_lower.startswith("dbms/relational-model/keys"):
        refs = [
            ("ER Diagrams", "../dbms/relational-model/er-diagrams.md"),
            ("Indexing", "../dbms/indexing/README.md"),
            ("Normalization", "../dbms/normalization/README.md"),
        ]
    elif path_lower.startswith("dbms/relational-model/relational-algebra"):
        refs = [
            ("Relational Calculus", "../dbms/relational-model/relational-calculus.md"),
            ("Query Processing", "../dbms/query-processing/README.md"),
            ("SQL DML", "../dbms/sql/dml.md"),
        ]
    elif path_lower.startswith("dbms/relational-model/relational-calculus"):
        refs = [
            ("Relational Algebra", "../dbms/relational-model/relational-algebra.md"),
            ("SQL Subqueries", "../dbms/sql/subqueries.md"),
            ("Query Processing", "../dbms/query-processing/README.md"),
        ]
    elif path_lower == "dbms/relational-model/readme.md":
        refs = [
            ("ER Diagrams", "../dbms/relational-model/er-diagrams.md"),
            ("Keys", "../dbms/relational-model/keys.md"),
            ("Relational Algebra", "../dbms/relational-model/relational-algebra.md"),
            ("SQL DDL", "../dbms/sql/ddl.md"),
        ]
    # SQL
    elif path_lower.startswith("dbms/sql/joins"):
        refs = [
            ("Query Joins", "../dbms/query-processing/joins.md"),
            ("Nested Loop", "../dbms/query-processing/nested-loop.md"),
            ("Subqueries", "../dbms/sql/subqueries.md"),
            ("Execution Plans", "../dbms/query-processing/execution-plans.md"),
        ]
    elif path_lower.startswith("dbms/sql/indexes"):
        refs = [
            ("Indexing", "../dbms/indexing/README.md"),
            ("B+ Tree", "../dbms/indexing/b-plus-tree.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Covering Index", "../dbms/indexing/covering-index.md"),
        ]
    elif path_lower.startswith("dbms/sql/subqueries"):
        refs = [
            ("SQL Joins", "../dbms/sql/joins.md"),
            ("CTEs", "../dbms/sql/ctes.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
            ("Relational Calculus", "../dbms/relational-model/relational-calculus.md"),
        ]
    elif path_lower.startswith("dbms/sql/ctes"):
        refs = [
            ("Subqueries", "../dbms/sql/subqueries.md"),
            ("Views", "../dbms/sql/views.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
        ]
    elif path_lower.startswith("dbms/sql/views"):
        refs = [
            ("CTEs", "../dbms/sql/ctes.md"),
            ("Stored Procedures", "../dbms/sql/stored-procedures.md"),
            ("Triggers", "../dbms/sql/triggers.md"),
        ]
    elif path_lower.startswith("dbms/sql/stored-procedures"):
        refs = [
            ("Views", "../dbms/sql/views.md"),
            ("Triggers", "../dbms/sql/triggers.md"),
            ("SQL DML", "../dbms/sql/dml.md"),
        ]
    elif path_lower.startswith("dbms/sql/triggers"):
        refs = [
            ("Stored Procedures", "../dbms/sql/stored-procedures.md"),
            ("Views", "../dbms/sql/views.md"),
            ("ACID", "../dbms/transactions/acid.md"),
        ]
    elif path_lower.startswith("dbms/sql/window-functions"):
        refs = [
            ("CTEs", "../dbms/sql/ctes.md"),
            ("SQL DML", "../dbms/sql/dml.md"),
            ("Query Optimization", "../dbms/query-processing/optimization.md"),
        ]
    elif path_lower.startswith("dbms/sql/ddl"):
        refs = [
            ("DML", "../dbms/sql/dml.md"),
            ("ER Diagrams", "../dbms/relational-model/er-diagrams.md"),
            ("Normalization", "../dbms/normalization/README.md"),
        ]
    elif path_lower.startswith("dbms/sql/dml"):
        refs = [
            ("DDL", "../dbms/sql/ddl.md"),
            ("SQL Joins", "../dbms/sql/joins.md"),
            ("Subqueries", "../dbms/sql/subqueries.md"),
            ("Query Processing", "../dbms/query-processing/README.md"),
        ]
    elif path_lower == "dbms/sql/readme.md":
        refs = [
            ("DDL", "../dbms/sql/ddl.md"),
            ("DML", "../dbms/sql/dml.md"),
            ("Joins", "../dbms/sql/joins.md"),
            ("Query Processing", "../dbms/query-processing/README.md"),
        ]
    # NoSQL
    elif path_lower.startswith("dbms/nosql/key-value"):
        refs = [
            ("Redis", "../dbms/caching/redis.md"),
            ("Memcached", "../dbms/caching/memcached.md"),
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("LSM Trees", "../dbms/internals/lsm-trees.md"),
        ]
    elif path_lower.startswith("dbms/nosql/document"):
        refs = [
            ("Key-Value", "../dbms/nosql/key-value.md"),
            ("B-Tree", "../dbms/indexing/b-tree.md"),
            ("Relational Model", "../dbms/relational-model/README.md"),
        ]
    elif path_lower.startswith("dbms/nosql/column-family"):
        refs = [
            ("Column Stores", "../dbms/storage/column-stores.md"),
            ("LSM Trees", "../dbms/internals/lsm-trees.md"),
            ("Consistent Hashing", "../distributed/partitioning/consistent-hashing.md"),
            ("Sharding", "../dbms/distributed/sharding.md"),
        ]
    elif path_lower.startswith("dbms/nosql/graph"):
        refs = [
            ("ER Diagrams", "../dbms/relational-model/er-diagrams.md"),
            ("GNN", "../ml/gnn/README.md"),
            ("BFS/DFS", "../distributed/fundamentals/README.md"),
        ]
    elif path_lower.startswith("dbms/nosql/newsql"):
        refs = [
            ("ACID", "../dbms/transactions/acid.md"),
            ("Distributed Transactions", "../dbms/transactions/distributed.md"),
            ("Sharding", "../dbms/distributed/sharding.md"),
            ("Consensus", "../dbms/distributed/consensus.md"),
        ]
    elif path_lower == "dbms/nosql/readme.md":
        refs = [
            ("Key-Value", "../dbms/nosql/key-value.md"),
            ("Document", "../dbms/nosql/document.md"),
            ("Column Family", "../dbms/nosql/column-family.md"),
            ("Graph", "../dbms/nosql/graph.md"),
            ("Relational Model", "../dbms/relational-model/README.md"),
        ]
    # DBMS Overview
    elif path_lower == "dbms/overview.md":
        refs = [
            ("Relational Model", "../dbms/relational-model/README.md"),
            ("SQL", "../dbms/sql/README.md"),
            ("Transactions", "../dbms/transactions/README.md"),
            ("OS Overview", "../os/overview.md"),
            ("Storage Overview", "../storage/overview.md"),
        ]
    
    return refs


def process_file(file_path):
    """Process a single file, adding cross-references if not already present."""
    full_path = os.path.join(BASE, file_path)
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Skip if already has cross-references
    if "## Cross References" in content:
        return False
    
    refs = get_crossrefs_for_file(file_path)
    if not refs:
        return False
    
    # Build the cross-references section
    crossref_section = "\n\n## Cross References\n\n"
    for name, path in refs:
        crossref_section += f"- [{name}]({path})\n"
    
    # Append to file
    content = content.rstrip() + "\n" + crossref_section
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def main():
    # Process OS files
    os_files = []
    for root, dirs, files in os.walk(os.path.join(BASE, "os")):
        for f in files:
            if f.endswith('.md'):
                rel = os.path.relpath(os.path.join(root, f), BASE)
                os_files.append(rel)
    
    # Process DBMS files
    dbms_files = []
    for root, dirs, files in os.walk(os.path.join(BASE, "dbms")):
        for f in files:
            if f.endswith('.md'):
                rel = os.path.relpath(os.path.join(root, f), BASE)
                dbms_files.append(rel)
    
    all_files = sorted(os_files + dbms_files)
    
    processed = 0
    skipped = 0
    
    for fp in all_files:
        if process_file(fp):
            processed += 1
            print(f"  ✓ {fp}")
        else:
            skipped += 1
            print(f"  - {fp} (no refs or already has cross-refs)")
    
    print(f"\nDone: {processed} files updated, {skipped} skipped")


if __name__ == "__main__":
    main()
