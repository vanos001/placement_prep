# Reference Libraries

Thirteen verified indexes of **primary sources** — one per major systems topic. Where the rest of this book explains concepts, these pages tell you *which document to open* for the authoritative answer, and in what order to read things.

Each entry records, where it exists:

- **Official documentation** and the **developer / API portal**
- The **source repository**
- **SDKs** and notable related repos
- **Downloadable or offline** documentation (PDFs, doc tarballs, offline bundles)
- A short honest **note** — what the source is actually good for, and where it misleads

Each page then has a two-track **Education** section (Basic and Advanced, with university course material in both) and a **Research papers & open-access literature** section covering free paper sources for that field.

## The indexes

| Topic | Entries | Education | Verified links |
|---|---|---|---|
| [Computer Networks](./networking.md) | 196 | 196 | 736 |
| [Computer Architecture](./computer-architecture.md) | 63 | 53 | 119 |
| [Operating Systems](./operating-systems.md) | 68 | 58 | 134 |
| [Database Systems](./database-systems.md) | 68 | 53 | 153 |
| [NoSQL & Distributed Systems](./distributed-systems.md) | 74 | 54 | 164 |
| [Machine Learning, Deep Learning & AI](./machine-learning-ai.md) | 89 | 57 | 205 |
| [Programming Languages, Compilers & Runtimes](./languages-compilers.md) | 82 | 59 | 171 |
| [Cloud Computing](./cloud-computing.md) | 93 | 57 | 212 |
| [Prompt Engineering](./prompt-engineering.md) | 70 | 53 | 118 |
| [Agentic Engineering](./agentic-engineering.md) | 71 | 54 | 120 |
| [Security Engineering](./security-reference.md) | 81 | 46 | 206 |
| [Concurrency & Parallelism](./concurrency-reference.md) | 68 | 58 | 156 |
| [Storage Systems](./storage-reference.md) | 64 | 58 | 160 |

**1,101 entries, 2,344 unique URLs** across the thirteen indexes. The original ten batches were HTTP-verified on 2026-10-07; the security, concurrency and storage indexes were verified on 2026-10-08. Every URL in the three newest indexes was fetched with the same method — redirects followed, 25-second timeout, final status and resolved URL recorded.

## Research papers

Every index except the networking one ends with a research section. Fifteen sources are shared across all nine — arXiv (with its API and bulk-data endpoints), ar5iv, alphaXiv, Semantic Scholar, OpenAlex, DBLP, OpenReview, CORE, Unpaywall, Papers We Love, The Morning Paper archive, USENIX Proceedings, the ACM DL, IEEE Xplore and DROPS/LIPIcs — and each page adds the venues specific to its field. (The networking index instead carries RFC/standards bodies, NOG communities and operator resources in its own categories.)

The **access model is recorded for every venue**: which are fully open (USENIX, PVLDB, PMLR, JMLR, ACL Anthology, CVF, LIPIcs, PACMPL), which are partially open (ACM), and which are mostly paywalled with a legal free route around them (IEEE Xplore → arXiv, author pages, Unpaywall).

## Verification method

Every URL was fetched with redirects followed and a 25-second timeout, and recorded with its final status and resolved URL.

- **Dead links were replaced, not kept.** Where a documented path 404'd, the working replacement is used.
- **Bot-blocked sources are flagged, not dropped.** Several important sources (the Intel SDM, `developer.arm.com`, the OSDev Wiki, `dev.mysql.com`, cppreference, the ACM DL) return 403 to automated clients while working normally in a browser. These are kept with an explicit note, because dropping them would make the indexes worse.
- **Ownership and naming changes are noted inline** where they affect whether a link or a search will work: Linode → Akamai Cloud Computing, Timescale → TigerData, Redis → the Valkey fork, Terraform → OpenTofu, Coq → Rocq, Talos docs → `docs.siderolabs.com`, Spirent → absorbed into Keysight, OpenZiti docs → hosted under NetFoundry, NS1 → IBM NS1 Connect.
- **Two sources are kept with a browser-only flag** in the newest indexes: `ai.google.dev` redirects automated clients to a Google sign-in page, and `openai.com/research/` returns 403 to them. Both load normally in a browser.

## Machine-readable data

Each index also ships as CSV, one row per entry, with the same columns:

`Category, Name, Documentation, Developer / API portal, Source / GitHub, SDKs & notable repos, Downloadable / offline docs, Notes`

- [networking.csv](./data/networking.csv)
- [computer-architecture.csv](./data/computer-architecture.csv)
- [operating-systems.csv](./data/operating-systems.csv)
- [database-systems.csv](./data/database-systems.csv)
- [distributed-systems.csv](./data/distributed-systems.csv)
- [machine-learning-ai.csv](./data/machine-learning-ai.csv)
- [languages-compilers.csv](./data/languages-compilers.csv)
- [cloud-computing.csv](./data/cloud-computing.csv)
- [prompt-engineering.csv](./data/prompt-engineering.csv)
- [agentic-engineering.csv](./data/agentic-engineering.csv)
- [security.csv](./data/security.csv)
- [concurrency.csv](./data/concurrency.csv)
- [storage.csv](./data/storage.csv)

## How to use these pages

1. **Starting a topic?** Read that page's *Education → Basic* track in order. It is deliberately short and opinionated.
2. **Need the authoritative answer?** Go to the entry for the system and open its **Docs** link, not a blog post.
3. **Going deep?** The *Advanced* track points at the source you should be reading — teaching kernels before production kernels, LevelDB before RocksDB, nanoGPT before `transformers`.
4. **Writing something original?** Start from the research section and the access notes, so you spend your time reading rather than hunting for PDFs.

Every page ends with an **"If you only do three things"** box and an **honest notes** section covering the traps — which documentation is genuinely excellent, which is stale, and which project renamed itself out from under its own links.

## Driving these indexes with a model

[Documentation Navigator — Generic Prompt Library](../meta/prompt-library.md) is a set of 16 topic-agnostic prompts built for exactly this corpus. Set `{{TOPIC}}`, attach the relevant index, and the model answers by pointing at documents and a reading order instead of improvising prose.
