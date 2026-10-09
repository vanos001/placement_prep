# Reference Libraries

Fourteen verified indexes of **primary sources** — one per major topic. Where the rest of this book explains concepts, these pages tell you *which document to open* for the authoritative answer, and in what order to read things.

Each entry records, where it exists:

- **Official documentation** and the **developer / API portal**
- The **source repository**
- **SDKs** and notable related repos
- **Downloadable or offline** documentation (PDFs, doc tarballs, offline bundles)
- A short honest **note** — what the source is actually good for, and where it misleads

Each page then has a two-track **Education** section (Basic and Advanced, with university course material in both), a **Research papers & open-access literature** section covering free paper sources for that field, a **Video courses, channels & talks** section of verified channels and lecture playlists, and a **Conference videos, notes & archives** section covering the conference channels, video archives, proceedings portals and paper-adjacent note archives for that field. The DSA index is the exception in placement only: its video material sits in its Community & video category and in the Basic education track rather than in a separate section.

## The indexes

| Topic | Entries | Education | Video | Conference | Verified links |
|---|---|---|---|---|---|
| [Computer Networks](./networking.md) | 196 | 196 | 16 | 9 | 761 |
| [Computer Architecture](./computer-architecture.md) | 63 | 53 | 12 | 6 | 135 |
| [Operating Systems](./operating-systems.md) | 68 | 58 | 10 | 7 | 151 |
| [Database Systems](./database-systems.md) | 68 | 53 | 14 | 6 | 173 |
| [NoSQL & Distributed Systems](./distributed-systems.md) | 74 | 54 | 14 | 8 | 186 |
| [Machine Learning, Deep Learning & AI](./machine-learning-ai.md) | 89 | 57 | 22 | 8 | 234 |
| [Programming Languages, Compilers & Runtimes](./languages-compilers.md) | 82 | 59 | 12 | 5 | 187 |
| [Cloud Computing](./cloud-computing.md) | 93 | 57 | 10 | 5 | 227 |
| [Prompt Engineering](./prompt-engineering.md) | 70 | 53 | 10 | 5 | 132 |
| [Agentic Engineering](./agentic-engineering.md) | 71 | 54 | 9 | 5 | 133 |
| [Security Engineering](./security-reference.md) | 81 | 46 | 14 | 7 | 226 |
| [Concurrency & Parallelism](./concurrency-reference.md) | 68 | 58 | 9 | 4 | 168 |
| [Storage Systems](./storage-reference.md) | 64 | 58 | 8 | 8 | 176 |
| [DSA, Competitive Programming & Competitive Math](./dsa-competitive-programming.md) | 170 | 72 | 35 | 3 | 402 |

**1,257 entries, 2,744 unique URLs** across the fourteen indexes (entries counted per index; the URL total is de-duplicated across all fourteen pages and was recomputed on 2026-10-09 — the previous figure did not reconcile with the per-index column).

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

Each index also ships as CSV, with the same columns and **one row per resource**: every entry, every education resource, every video resource and every conference source. Category values are the numbered entry categories (`3. Competitive math`), `Education — Basic`, `Education — Advanced`, `Video — <group>` and `Conference — <group>`. The DSA index keeps the original un-numbered category names; `networking.csv` keeps its older `Vendor / Project` column header.

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
- [dsa-competitive-programming.csv](./data/dsa-competitive-programming.csv)

## How to use these pages

1. **Starting a topic?** Read that page's *Education → Basic* track in order. It is deliberately short and opinionated.
2. **Need the authoritative answer?** Go to the entry for the system and open its **Docs** link, not a blog post.
3. **Going deep?** The *Advanced* track points at the source you should be reading — teaching kernels before production kernels, LevelDB before RocksDB, nanoGPT before `transformers`.
4. **Writing something original?** Start from the research section and the access notes, so you spend your time reading rather than hunting for PDFs.

Every page ends with an **"If you only do three things"** box and an **honest notes** section covering the traps — which documentation is genuinely excellent, which is stale, and which project renamed itself out from under its own links.

## Driving these indexes with a model

[Documentation Navigator — Generic Prompt Library](../meta/prompt-library.md) is a set of 16 topic-agnostic prompts built for exactly this corpus. Set `{{TOPIC}}`, attach the relevant index, and the model answers by pointing at documents and a reading order instead of improvising prose.
