# Placement Preparation Knowledge Base

A comprehensive, self-improving placement preparation resource for Software Engineering interviews — built as an [mdBook](https://rust-lang.github.io/mdBook/) with 2,800+ pages, 4,800+ Mermaid diagrams, and MathJax-powered equations.

[![Validation](https://img.shields.io/badge/validation-run%20locally%20%C2%B7%20not%20in%20CI-blue)](scripts/README.md)

## Quick Start

```bash
# Clone
gh repo clone vanos001/placement_prep
cd placement_prep

# Build (requires mdBook 0.5.4 — the version CI uses)
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
    ├── validate-all.sh           # Full validation suite (STRICT=1 / EXTERNAL=1 modes)
    ├── validate-mermaid.mjs       # Real Mermaid v11 parser
    ├── validate-mermaid-heuristic.mjs  # Fast heuristic checks
    ├── check-links.py             # Broken link finder (--external: probe URLs)
    ├── check-summary.py           # SUMMARY completeness + duplicate detection
    ├── check-mathjax.py           # MathJax validation
    ├── check-doi.py               # Resolve every DOI via doi.org Handle API
    └── USEFUL_COMMANDS.md        # Workflow reference for humans & agents
```

## Stats

| Metric | Count |
|--------|-------|
| Markdown pages | 2,809 content pages (+ `SUMMARY.md`) |
| Mermaid diagrams | 4,889 across 1,328 files (100% pass the real mermaid@11 parser, not just the heuristic) |
| Topic directories | 61 |
| Math-enabled pages | 128 |
| Words | ~5.79M |
| Unique external URLs | ~4,000 |

## Validation

Validation runs **locally, not in CI** — CI is reserved for builds so hosted
minutes stay available. Run the suite before committing:

```bash
./scripts/validate-all.sh .
```

This runs seven checks: mdBook build, **Markdown fence integrity**, Mermaid
heuristic, Mermaid real parser, broken links + anchors, SUMMARY completeness, and
MathJax. Set `EXTERNAL=1` to add DOI resolution and external-URL probing. See
[`scripts/README.md`](scripts/README.md) for details.

> **Scope of "0 broken links".** The internal link/anchor check is green. A probe
> of the ~6,500 external URLs initially flagged 758 as dead; **161 have since been
> repaired** (129 with a verified live replacement — mostly fabricated
> `docs.kernel.org` paths and man pages man7.org does not mirror — and 32 with an
> archived snapshot). 20 were transient failures that resolve fine. **471 remain
> dead** and are catalogued by host in
> [`scripts/dead-links-report.txt`](scripts/dead-links-report.txt); re-probe with
> `python3 scripts/check-links.py --external src`.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines on content creation, style conventions, and the PR process.

## License

This project is for educational use. See individual pages for attribution of referenced sources.
