# Glossary

A comprehensive glossary of terms used throughout this knowledge base.

## A

| Term | Definition |
|------|-----------|
| **ACID** | Atomicity, Consistency, Isolation, Durability — properties guaranteeing reliable database transactions |
| **ALU** | Arithmetic Logic Unit — digital circuit performing arithmetic and bitwise operations |
| **API** | Application Programming Interface — set of protocols for building software |
| **ARP** | Address Resolution Protocol — maps IP addresses to MAC addresses |
| **ASLR** | Address Space Layout Randomization — security technique randomizing memory addresses |
| **AVX** | Advanced Vector Extensions — SIMD instruction set for x86 CPUs |

## B

| Term | Definition |
|------|-----------|
| **B+ Tree** | Self-balancing tree structure optimized for disk-based indexing |
| **BBR** | Bottleneck Bandwidth and Round-trip propagation time — TCP congestion control algorithm |
| **BCNF** | Boyce-Codd Normal Form — stricter version of 3NF |
| **BIOS** | Basic Input/Output System — firmware for hardware initialization |
| **BGP** | Border Gateway Protocol — protocol for routing between autonomous systems |
| **Btrfs** | B-tree file system — modern Linux copy-on-write filesystem |

## C

| Term | Definition |
|------|-----------|
| **Cache** | Small, fast memory storing frequently accessed data |
| **CAP Theorem** | States a distributed system can guarantee only 2 of: Consistency, Availability, Partition tolerance |
| **CAS** | Compare-and-Swap — atomic operation for lock-free programming |
| **CDN** | Content Delivery Network — distributed servers for content delivery |
| **CIDR** | Classless Inter-Domain Routing — IP address allocation method |
| **CISC** | Complex Instruction Set Computing |
| **COW** | Copy-on-Write — optimization deferring copies until modification |
| **CFS** | Completely Fair Scheduler — Linux default process scheduler (being superseded by EEVDF) |
| **Cgroup** | Control Group — kernel facility limiting/accounting CPU, memory and I/O for process groups |
| **CPU** | Central Processing Unit |
| **Core Dump** | On-disk image of a process's memory written on abnormal termination (e.g. SIGSEGV) for post-mortem debugging |
| **CTE** | Common Table Expression — named temporary result set in SQL |

## D

| Term | Definition |
|------|-----------|
| **Daemon** | Background process detached from any controlling terminal, usually started at boot |
| **DMA** | Direct Memory Access — allows hardware to access memory without CPU |
| **DNS** | Domain Name System — translates domain names to IP addresses |
| **DRAM** | Dynamic Random-Access Memory |
| **DAC** | Discretionary Access Control |

## E

| Term | Definition |
|------|-----------|
| **EEPROM** | Electrically Erasable Programmable Read-Only Memory |
| **EEVDF** | Earliest Eligible Virtual Deadline First — Linux CFS replacement scheduler (6.6+) |
| **epoll** | Linux I/O event notification facility |
| **Errno** | Thread-local error code set by system calls on failure (see `errno(3)`) |
| **Exec** | Replacing the current process image with a new program (`execve(2)`) — the process PID survives |
| **Exit Status** | 8-bit value a process reports to its parent on termination (`$?` in shells); 0 = success by convention |
| **ext4** | Fourth extended filesystem — default Linux filesystem |

## F

| Term | Definition |
|------|-----------|
| **FCFS** | First-Come, First-Served scheduling |
| **FIFO** | First-In, First-Out |
| **File Descriptor** | Non-negative integer indexing a process's open-file table (files, sockets, pipes) |
| **Fork** | Duplicating the calling process — child gets a copy of the address space and inherits file descriptors |
| **FUSE** | Filesystem in Userspace |
| **FLP** | Fischer-Lynch-Paterson impossibility result |

## G

| Term | Definition |
|------|-----------|
| **GiST** | Generalized Search Tree — PostgreSQL index type |
| **GIN** | Generalized Inverted Index — PostgreSQL index type |
| **GPU** | Graphics Processing Unit |

## H

| Term | Definition |
|------|-----------|
| **HBM** | High Bandwidth Memory |
| **HDD** | Hard Disk Drive |
| **Huge Pages** | Large memory pages (2MB or 1GB) reducing TLB misses |
| **HTTP** | Hypertext Transfer Protocol |

## I

| Term | Definition |
|------|-----------|
| **Init (PID 1)** | First userspace process; ancestor of all processes, reaps orphans and never stops by default |
| **I/O** | Input/Output |
| **ICMP** | Internet Control Message Protocol |
| **IEEE 754** | Standard for floating-point arithmetic |
| **IOPS** | Input/Output Operations Per Second |
| **ISA** | Instruction Set Architecture |
| **ISR** | Interrupt Service Routine |

## J

| Term | Definition |
|------|-----------|
| **Job Control** | Shell facility for managing process groups: foreground/background, `Ctrl-Z`, `fg`, `bg`, `jobs` |

## K

| Term | Definition |
|------|-----------|
| **Kernel** | Core component of an OS managing hardware and system resources |

## L

| Term | Definition |
|------|-----------|
| **LRU** | Least Recently Used — cache/page replacement policy |
| **LFU** | Least Frequently Used |
| **LSM** | Log-Structured Merge-tree — storage engine data structure |
| **LKM** | Loadable Kernel Module |

## M

| Term | Definition |
|------|-----------|
| **MAC** | Media Access Control address |
| **MESI** | Modified, Exclusive, Shared, Invalid — cache coherence protocol |
| **Mmap** | Memory-mapped file |
| **MLFQ** | Multilevel Feedback Queue scheduling |
| **MVCC** | Multi-Version Concurrency Control |

## N

| Term | Definition |
|------|-----------|
| **NAT** | Network Address Translation |
| **Namespace** | Kernel isolation feature (pid, net, mnt, uts, ipc, user, cgroup) making processes see a private system view |
| **NUMA** | Non-Uniform Memory Access |
| **NVMe** | Non-Volatile Memory Express |
| **NVM** | Non-Volatile Memory |

## O

| Term | Definition |
|------|-----------|
| **OOM Killer** | Out-Of-Memory Killer — kernel mechanism selecting and SIGKILLing processes under memory exhaustion |
| **OOO** | Out-of-Order execution |
| **Orphan Process** | Process whose parent died; re-parented to init (PID 1) or a subreaper, which reaps it |
| **OSPF** | Open Shortest Path First — routing protocol |

## P

| Term | Definition |
|------|-----------|
| **PCB** | Process Control Block |
| **PCIe** | Peripheral Component Interconnect Express |
| **Paxos** | Consensus algorithm for distributed systems |
| **PID** | Process Identifier — the kernel-assigned unique ID of a process or process-group leader |
| **POSIX** | Portable Operating System Interface |
| **Process Group** | Set of related processes sharing a PGID for job-control signal delivery |
| **PTY** | Pseudo Terminal — kernel device pair emulating a terminal (ssh, tmux, containers) |

## Q

| Term | Definition |
|------|-----------|
| **QUIC** | Quick UDP Internet Connections — transport protocol |

## R

| Term | Definition |
|------|-----------|
| **RAID** | Redundant Array of Independent Disks |
| **RISC** | Reduced Instruction Set Computing |
| **Raft** | Understandable consensus algorithm |
| **Reaping** | Parent reading a terminated child's exit status via `wait()`/`waitpid()`, freeing the zombie's kernel slot |
| **RIP** | Routing Information Protocol |

## S

| Term | Definition |
|------|-----------|
| **Session** | Process-group collection tied to a controlling terminal, led by a session leader (see `setsid(2)`) |
| **SIGCHLD** | Signal sent to a parent when a child stops, resumes or terminates |
| **SIGHUP** | Hangup signal — controlling terminal closed; daemons use it to reload configuration |
| **SIGINT** | Interrupt signal from `Ctrl-C`; catchable and default-terminating |
| **SIGKILL** | Uncatchable, unignorable termination signal (9) — the kernel's last-resort kill |
| **SIGSEGV** | Signal raised on invalid memory access; default action terminates with a core dump |
| **SIGTERM** | Default termination request (15) — polite, catchable; the standard `kill` signal |
| **Signal** | Asynchronous notification delivered to a process (numbered, with a disposition: default/ignore/handler) |
| **Signal Disposition** | Per-signal process-wide policy: default action, ignore (`SIG_IGN`), or installed handler |
| **Signal Mask** | Set of signals temporarily blocked from delivery; inspected/changed via `sigprocmask(2)`/`pthread_sigmask(3)` |
| **SLAB** | Linux kernel memory allocator |
| **SMP** | Symmetric Multiprocessing |
| **SMT** | Simultaneous Multithreading (Hyperthreading) |
| **SRAM** | Static Random-Access Memory |
| **SSD** | Solid State Drive |
| **STAR** | Situation, Task, Action, Result — behavioral interview framework |

## T

| Term | Definition |
|------|-----------|
| **TCP** | Transmission Control Protocol |
| **TLB** | Translation Lookaside Buffer |
| **TLS** | Transport Layer Security |
| **TSC** | Time Stamp Counter |
| **TTY** | Teletypewriter — terminal device abstraction; a process's controlling terminal drives its signals |

## U

| Term | Definition |
|------|-----------|
| **UDP** | User Datagram Protocol |
| **UEFI** | Unified Extensible Firmware Interface |

## V

| Term | Definition |
|------|-----------|
| **VFS** | Virtual File System |
| **VM** | Virtual Machine |
| **VPN** | Virtual Private Network |
| **VPC** | Virtual Private Cloud |

## W

| Term | Definition |
|------|-----------|
| **Wait / waitpid** | System calls blocking a parent until a child changes state and returning its exit status |
| **WAL** | Write-Ahead Logging |
| **WSS** | Working Set Size |

## X

| Term | Definition |
|------|-----------|
| **XFS** | High-performance filesystem |

## Z

| Term | Definition |
|------|-----------|
| **ZFS** | Zettabyte File System |
| **ZAB** | ZooKeeper Atomic Broadcast |
| **Zombie Process** | Terminated process whose exit status the parent has not reaped yet; only its kernel PCB remains |
