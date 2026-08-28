# Placement Preparation Knowledge Base

A comprehensive, self-improving placement preparation resource for Software Engineering interviews — built as an [mdBook](https://rust-lang.github.io/mdBook/) with 2,600+ pages, 4,800+ Mermaid diagrams, and MathJax-powered equations.

[![Validation](https://img.shields.io/badge/validation-links%20%C2%B7%20summary%20%C2%B7%20mathjax%20%C2%B7%20mermaid%20%28real%20parser%29-green)](scripts/README.md)

## Quick Start

```bash
# Clone
gh repo clone vanos001/placement_prep
cd placement_prep

# Build (requires mdBook 0.4.x)
mdbook build
mdbook serve --open          # http://localhost:3000

# Validate before committing
./scripts/validate-all.sh .
```

## What's Inside

| Area | Topics |
|------|--------|
| **Data Structures & Algorithms** | Sorting, graphs, trees, DP, greedy, advanced algorithms |
| **System Design** | Fundamentals, scalability, load balancing, caching, and 40+ case studies |
| **Databases (DBMS)** | SQL, indexing, transactions, query processing, storage engines, PostgreSQL |
| **Distributed Systems** | Consensus (Paxos, Raft), replication, partitioning, messaging (Kafka, Pulsar) |
| **Operating Systems** | Process scheduling, memory, file systems, synchronization, Linux kernel |
| **Computer Networks** | TCP/IP, HTTP/2/3, DNS, load balancing, network security |
| **Computer Architecture** | Pipelining, caches, memory hierarchy, parallelism, modern CPUs |
| **Cloud & DevOps** | AWS services, Kubernetes, Docker, Terraform, CI/CD, observability |
| **Linux** | Shell, kernel, containers, BPF, performance, security, embedded |
| **Concurrency** | Locks, lock-free, async/await, Go channels, Rust ownership |
| **Security** | Crypto, web security, auth, supply chain |
| **Frontend** | React, TypeScript, browser internals, CSS, accessibility |
| **Career** | Resume writing, behavioral interviews, salary negotiation |
| **And more** | Compilers, SRE, embedded systems, storage, Git, machine coding |

Full table of contents: [`src/SUMMARY.md`](src/SUMMARY.md)

## Repository Structure

```
placement_prep/
├── book.toml              # mdBook configuration
├── custom.css             # Custom styling
├── mermaid-init.js        # Mermaid v11 CDN loader
├── src/                   # ← All content lives here
│   ├── SUMMARY.md          # Navigation / table of contents
│   ├── introduction.md
│   ├── dsa/               # Data structures & algorithms
│   ├── system-design/      # System design topics
│   ├── dbms/              # Database management systems
│   ├── distributed/        # Distributed systems
│   ├── os/                # Operating systems
│   ├── networks/           # Computer networks
│   ├── arch/              # Computer architecture
│   ├── cloud/             # Cloud & DevOps
│   ├── linux/             # Linux deep-dive
│   ├── ...                # 50+ topic directories
│   └── meta/              # Internal tracking pages
└── scripts/               # Validation & tooling
    ├── validate-all.sh           # Full validation suite
    ├── validate-mermaid.mjs       # Real Mermaid v11 parser
    ├── validate-mermaid-heuristic.mjs  # Fast heuristic checks
    ├── check-links.py             # Broken link finder
    ├── check-summary.py           # SUMMARY completeness
    ├── check-mathjax.py           # MathJax validation
    └── USEFUL_COMMANDS.md        # Workflow reference for humans & agents
```

## Stats

| Metric | Count |
|--------|-------|
| Markdown pages | 2,640 |
| Mermaid diagrams | 4,875 (100% pass the real mermaid@11 parser, not just the heuristic) |
| Topic directories | 61 |
| Math-enabled pages | 127 |

## Validation

Every change should pass the full validation suite before committing:

```bash
./scripts/validate-all.sh .
```

This runs six checks: mdBook build, Mermaid heuristic, Mermaid real parser, broken links, SUMMARY completeness, and MathJax. See [`scripts/README.md`](scripts/README.md) for details.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines on content creation, style conventions, and the PR process.

## License

This project is for educational use. See individual pages for attribution of referenced sources.
