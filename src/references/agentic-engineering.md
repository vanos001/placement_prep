# Agentic Engineering Reference Library

This page is a verified index of primary sources for agentic engineering: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Protocols (MCP, A2A), agent frameworks, coding agents, sandboxed execution and durable workflows, tracing and benchmarks, agent security, and a two-track path from reading a thousand-line agent loop to evaluating and isolating production agents.

**71 entries** across 7 categories, plus **54 education & reference-implementation resources** (21 basic / 33 advanced), plus **9 video resources** and **5 conference sources**.

Every link HTTP-verified on **2026-10-07**.

> This is the fastest-moving topic in the set. Check publication dates on everything — framework APIs here break more often than anywhere else in this series.

## Contents

- [1. Protocols & interoperability](#1-protocols--interoperability) — 5
- [2. Agent frameworks](#2-agent-frameworks) — 11
- [3. Coding agents — read these, they are the most mature](#3-coding-agents--read-these-they-are-the-most-mature) — 8
- [4. Runtime, sandboxing & durability](#4-runtime-sandboxing--durability) — 4
- [5. Observability, evaluation & benchmarks](#5-observability-evaluation--benchmarks) — 8
- [6. Guardrails, permissions & agent security](#6-guardrails-permissions--agent-security) — 6
- [7. Research papers & open-access literature](#7-research-papers--open-access-literature) — 29
- [Education & reference implementations](#education--reference-implementations) — 54 (21 basic / 33 advanced)
- [Video courses, channels & talks](#video-courses-channels--talks) — 9
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 5


## 1. Protocols & interoperability

### Model Context Protocol (MCP)

- **Docs:** [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **Developer / API:** [modelcontextprotocol.io/specification/…](https://modelcontextprotocol.io/specification/2025-06-18)
- **Source:** [github.com/modelcontextprotocol](https://github.com/modelcontextprotocol)
- **SDKs & repos:** SDKs for Python, TypeScript, Java, Kotlin, C#, Go, Rust; Inspector debugging tool
- **Downloadable / offline:** Spec is a single readable document, versioned by date
- *Note:* The emerging standard for connecting models to tools and data. Read the spec directly — it is short, and it explains the trust boundaries most integrations get wrong.

### MCP reference servers

- **Docs:** [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- **Source:** [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- **SDKs & repos:** Reference implementations for filesystem, git, databases, fetch and more
- **Downloadable / offline:** Repo cloneable
- *Note:* Read two or three before writing your own. The patterns are not obvious from the spec alone.

### A2A (Agent2Agent)

- **Docs:** [a2a-protocol.org/latest](https://a2a-protocol.org/latest/)
- **Source:** [github.com/a2aproject/A2A](https://github.com/a2aproject/A2A)
- **SDKs & repos:** Agent-to-agent communication: agent cards, task delegation, streaming
- **Downloadable / offline:** Spec + SDKs
- *Note:* Complements MCP rather than competing with it — MCP connects agents to tools, A2A connects agents to each other. Linux Foundation governed.

### OpenAI function calling

- **Docs:** [platform.openai.com/docs/…](https://platform.openai.com/docs/guides/function-calling)
- **Developer / API:** [platform.openai.com/docs](https://platform.openai.com/docs)
- **SDKs & repos:** The tool-call interface most frameworks ultimately target
- **Downloadable / offline:** Docs site
- *Note:* Learn the raw protocol before adopting a framework. Most agent bugs are tool-schema bugs.

### OpenTelemetry GenAI semantic conventions

- **Docs:** [opentelemetry.io/docs/specs/semconv/gen-ai](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- **Source:** [github.com/open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions)
- **SDKs & repos:** Standard span and attribute names for model calls, tool calls and agent steps
- **Downloadable / offline:** Spec online
- *Note:* Instrument to this rather than a vendor SDK. It is the one observability choice that is hard to reverse.


## 2. Agent frameworks

### OpenAI Agents SDK

- **Docs:** [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/)
- **Source:** [github.com/openai/openai-agents-python](https://github.com/openai/openai-agents-python)
- **SDKs & repos:** Agents, handoffs, guardrails, sessions, built-in tracing
- **Downloadable / offline:** Docs site
- *Note:* Deliberately small. A good first framework precisely because it does not hide much.

### Claude Agent SDK

- **Docs:** [docs.claude.com/en/api/agent-sdk/overview](https://docs.claude.com/en/api/agent-sdk/overview)
- **Source:** [github.com/anthropics](https://github.com/anthropics)
- **SDKs & repos:** The harness behind Claude Code, exposed as a library; subagents, hooks, MCP
- **Downloadable / offline:** Docs site
- *Note:* Unusually valuable because the production system built on it is one you can observe directly.

### LangGraph

- **Docs:** [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- **Source:** [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **SDKs & repos:** Agents as explicit state graphs; checkpointing, human-in-the-loop, time travel
- **Downloadable / offline:** Docs site
- *Note:* The graph model is the right abstraction once control flow matters. Durable checkpointing is the feature that makes agents operable.

### Pydantic AI

- **Docs:** [ai.pydantic.dev](https://ai.pydantic.dev/)
- **Source:** [github.com/pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai)
- **SDKs & repos:** Type-safe agents with validated structured output and dependency injection
- **Downloadable / offline:** Docs site
- *Note:* Feels like normal Python rather than a DSL. Strong choice if your codebase already uses Pydantic.

### smolagents

- **Docs:** [huggingface.co/docs/smolagents](https://huggingface.co/docs/smolagents)
- **Source:** [github.com/huggingface/smolagents](https://github.com/huggingface/smolagents)
- **SDKs & repos:** Minimal agent library centred on code-writing agents
- **Downloadable / offline:** Docs site
- *Note:* About a thousand lines. Read the whole thing — it is the fastest way to understand what an agent loop actually is.

### CrewAI

- **Docs:** [docs.crewai.com](https://docs.crewai.com/)
- **Source:** [github.com/crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)
- **SDKs & repos:** Role-based multi-agent teams with tasks and processes
- **Downloadable / offline:** Docs site

### AutoGen

- **Docs:** [microsoft.github.io/autogen](https://microsoft.github.io/autogen/)
- **Source:** [github.com/microsoft/autogen](https://github.com/microsoft/autogen)
- **SDKs & repos:** Microsoft's multi-agent conversation framework; event-driven core
- **Downloadable / offline:** Docs site
- *Note:* The most research-driven of the multi-agent frameworks; papers accompany the design.

### Semantic Kernel

- **Docs:** [learn.microsoft.com/en-us/semantic-kernel](https://learn.microsoft.com/en-us/semantic-kernel/)
- **Source:** [github.com/microsoft/semantic-kernel](https://github.com/microsoft/semantic-kernel)
- **SDKs & repos:** Enterprise-oriented orchestration for .NET, Python and Java
- **Downloadable / offline:** Learn docs

### Google Agent Development Kit

- **Docs:** [google.github.io/adk-docs](https://google.github.io/adk-docs/)
- **Source:** [github.com/google/adk-python](https://github.com/google/adk-python)
- **SDKs & repos:** Google's agent framework; multi-agent, evaluation, deployment to Vertex
- **Downloadable / offline:** Docs site

### LlamaIndex Workflows

- **Docs:** [docs.llamaindex.ai/en/…](https://docs.llamaindex.ai/en/stable/module_guides/workflow/)
- **Developer / API:** [docs.llamaindex.ai/en/stable](https://docs.llamaindex.ai/en/stable/)
- **Source:** [github.com/run-llama/llama_index](https://github.com/run-llama/llama_index)
- **SDKs & repos:** Event-driven agent workflows with strong retrieval integration
- **Downloadable / offline:** Docs site

### Mastra

- **Docs:** [mastra.ai/docs](https://mastra.ai/docs)
- **Source:** [github.com/mastra-ai/mastra](https://github.com/mastra-ai/mastra)
- **SDKs & repos:** TypeScript agent framework: workflows, RAG, evals
- **Downloadable / offline:** Docs site
- *Note:* The most complete option if your stack is TypeScript rather than Python.


## 3. Coding agents — read these, they are the most mature

### Claude Code

- **Docs:** [docs.claude.com/en/docs/claude-code/overview](https://docs.claude.com/en/docs/claude-code/overview)
- **SDKs & repos:** Terminal coding agent; hooks, subagents, MCP, skills
- **Downloadable / offline:** Docs site
- *Note:* Study the hooks and permissions model — it is a worked answer to 'how do you let an agent act without letting it act freely'.

### OpenHands

- **Docs:** [docs.all-hands.dev](https://docs.all-hands.dev/)
- **Source:** [github.com/All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)
- **SDKs & repos:** Open-source software-development agent with a sandboxed runtime
- **Downloadable / offline:** Docs site
- *Note:* Fully open and genuinely capable. The runtime isolation design is the part to read.

### SWE-agent

- **Docs:** [swe-agent.com/latest](https://swe-agent.com/latest/)
- **Source:** [github.com/SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent)
- **SDKs & repos:** The Princeton research agent that established the agent-computer interface idea
- **Downloadable / offline:** Docs site
- *Note:* The ACI paper is the key insight: agent performance depends more on tool design than on prompting.

### Aider

- **Docs:** [aider.chat/docs](https://aider.chat/docs/)
- **Source:** [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider)
- **SDKs & repos:** Terminal pair programmer with repository mapping and git integration
- **Downloadable / offline:** Docs site
- *Note:* The repo-map approach to context selection is clever and well documented.

### Cline

- **Docs:** [docs.cline.bot](https://docs.cline.bot/)
- **Source:** [github.com/cline/cline](https://github.com/cline/cline)
- **SDKs & repos:** Autonomous coding agent in VS Code with plan/act separation
- **Downloadable / offline:** Docs site

### Continue

- **Docs:** [docs.continue.dev](https://docs.continue.dev/)
- **Source:** [github.com/continuedev/continue](https://github.com/continuedev/continue)
- **SDKs & repos:** Open-source IDE assistant, model-agnostic
- **Downloadable / offline:** Docs site

### browser-use

- **Docs:** [docs.browser-use.com](https://docs.browser-use.com/)
- **Source:** [github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)
- **SDKs & repos:** Agents that drive a real browser via the accessibility tree
- **Downloadable / offline:** Docs site

### Playwright MCP

- **Docs:** [github.com/microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- **Source:** [github.com/microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp)
- **SDKs & repos:** Browser automation exposed as an MCP server
- **Downloadable / offline:** In-repo docs
- *Note:* Uses the accessibility tree rather than screenshots — far more reliable than vision-based clicking.


## 4. Runtime, sandboxing & durability

### E2B

- **Docs:** [e2b.dev/docs](https://e2b.dev/docs)
- **Source:** [github.com/e2b-dev/E2B](https://github.com/e2b-dev/E2B)
- **SDKs & repos:** Firecracker-backed sandboxes for running agent-generated code
- **Downloadable / offline:** Docs site; self-hostable
- *Note:* If your agent executes code it wrote, it needs one of these. Not optional.

### Modal

- **Docs:** [modal.com/docs](https://modal.com/docs)
- **SDKs & repos:** Serverless containers with fast cold starts; common agent execution backend
- **Downloadable / offline:** Docs site

### Temporal

- **Docs:** [docs.temporal.io](https://docs.temporal.io/)
- **Developer / API:** [docs.temporal.io/develop](https://docs.temporal.io/develop)
- **Source:** [github.com/temporalio/temporal](https://github.com/temporalio/temporal)
- **SDKs & repos:** Durable execution — workflows that survive crashes and restarts
- **Downloadable / offline:** Docs site
- *Note:* The right substrate for long-running agents. Agent loops are workflows, and most frameworks reinvent this badly.

### LangGraph persistence

- **Docs:** [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- **Source:** [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **SDKs & repos:** Checkpointers, interrupts and resumable state
- **Downloadable / offline:** Docs site
- *Note:* The closest thing to durable execution inside an agent framework itself.


## 5. Observability, evaluation & benchmarks

### Langfuse

- **Docs:** [langfuse.com/docs](https://langfuse.com/docs)
- **Source:** [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)
- **SDKs & repos:** Open-source tracing for multi-step agent runs; self-hostable
- **Downloadable / offline:** Docs site
- *Note:* Agent debugging is trace debugging. Without this you are reading logs and guessing.

### LangSmith

- **Docs:** [docs.smith.langchain.com](https://docs.smith.langchain.com/)
- **SDKs & repos:** Tracing, datasets and evaluation
- **Downloadable / offline:** Docs site

### Phoenix (Arize)

- **Docs:** [arize.com/docs/phoenix](https://arize.com/docs/phoenix)
- **Source:** [github.com/Arize-ai/phoenix](https://github.com/Arize-ai/phoenix)
- **SDKs & repos:** OpenTelemetry-native tracing and evaluation
- **Downloadable / offline:** Docs site

### OpenLLMetry

- **Docs:** [github.com/traceloop/openllmetry](https://github.com/traceloop/openllmetry)
- **Source:** [github.com/traceloop/openllmetry](https://github.com/traceloop/openllmetry)
- **SDKs & repos:** OpenTelemetry instrumentation for LLM and agent frameworks
- **Downloadable / offline:** In-repo docs

### Inspect AI

- **Docs:** [inspect.aisi.org.uk](https://inspect.aisi.org.uk/)
- **Source:** [github.com/UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai)
- **SDKs & repos:** Evaluation framework with first-class agent and tool support
- **Downloadable / offline:** Docs site
- *Note:* From the UK AI Safety Institute. The most rigorous open framework for evaluating agents.

### SWE-bench

- **Docs:** [swebench.com](https://www.swebench.com/)
- **Source:** [github.com/SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench)
- **SDKs & repos:** Real GitHub issues from real repositories; the dominant coding-agent benchmark
- **Downloadable / offline:** Harness and datasets in the repo
- *Note:* Verified, Lite and Full are different benchmarks. Scores get quoted without saying which — always check.

### Terminal-Bench

- **Docs:** [tbench.ai](https://www.tbench.ai/)
- **SDKs & repos:** Agents operating a real terminal on real tasks
- **Downloadable / offline:** Free
- *Note:* Less saturated than SWE-bench and harder to game.

### Berkeley Function-Calling Leaderboard

- **Docs:** [gorilla.cs.berkeley.edu/leaderboard.html](https://gorilla.cs.berkeley.edu/leaderboard.html)
- **SDKs & repos:** Standardised tool- and function-calling evaluation
- **Downloadable / offline:** Free
- *Note:* The most useful single signal for whether a model can call tools reliably.


## 6. Guardrails, permissions & agent security

### OWASP Top 10 for LLM Applications

- **Docs:** [genai.owasp.org](https://genai.owasp.org/)
- **Developer / API:** [owasp.org/…](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- **SDKs & repos:** 'Excessive agency' and 'insecure output handling' are the agent-specific entries
- **Downloadable / offline:** Free PDFs
- *Note:* Agents turn prompt injection from an information-disclosure bug into a remote-code-execution bug. Read this first.

### Simon Willison — the lethal trifecta

- **Docs:** [simonwillison.net/tags/prompt-injection](https://simonwillison.net/tags/prompt-injection/)
- **Developer / API:** [simonwillison.net](https://simonwillison.net/)
- **SDKs & repos:** Private data + untrusted content + external communication = unsafe, regardless of prompting
- **Downloadable / offline:** Free archive
- *Note:* The single most useful design rule in agent engineering. Remove one leg of the trifecta.

### Guardrails AI

- **Docs:** [guardrailsai.com/docs](https://www.guardrailsai.com/docs)
- **Source:** [github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails)
- **SDKs & repos:** Input and output validators
- **Downloadable / offline:** Docs site

### NeMo Guardrails

- **Docs:** [docs.nvidia.com/nemo/…](https://docs.nvidia.com/nemo/guardrails/latest/index.html)
- **Source:** [github.com/NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails)
- **SDKs & repos:** Programmable dialogue and action rails
- **Downloadable / offline:** Docs site

### garak

- **Docs:** [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)
- **Source:** [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)
- **SDKs & repos:** Vulnerability scanning, including tool-abuse probes
- **Downloadable / offline:** In-repo docs

### MITRE ATLAS

- **Docs:** [atlas.mitre.org](https://atlas.mitre.org/)
- **SDKs & repos:** Adversarial taxonomy for AI systems
- **Downloadable / offline:** Free
- *Note:* Use it to structure an agent threat model.


## 7. Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### arXiv cs.AI / cs.MA

- **Docs:** [arxiv.org/list/cs.AI/recent](https://arxiv.org/list/cs.AI/recent)
- **SDKs & repos:** Agent architectures and multi-agent systems. See also [arxiv.org/list/cs.MA/recent](https://arxiv.org/list/cs.MA/recent)
- **Downloadable / offline:** Free
- *Note:* Agent papers are overwhelmingly preprints; very little is peer reviewed yet.

### arXiv cs.SE (Software Engineering)

- **Docs:** [arxiv.org/list/cs.SE/recent](https://arxiv.org/list/cs.SE/recent)
- **SDKs & repos:** Coding agents, program repair, SWE-bench-style evaluation
- **Downloadable / offline:** Free
- *Note:* Where the coding-agent literature actually lives — easy to miss if you only watch cs.AI.

### ACL Anthology

- **Docs:** [aclanthology.org](https://aclanthology.org/)
- **Source:** [github.com/acl-org/acl-anthology](https://github.com/acl-org/acl-anthology)
- **SDKs & repos:** Tool use, ReAct-lineage and dialogue-agent work, peer reviewed
- **Downloadable / offline:** 100% open access

### COLM

- **Docs:** [colmweb.org](https://colmweb.org/)
- **SDKs & repos:** Language-modelling venue carrying a growing share of agent work
- **Downloadable / offline:** Open via OpenReview

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **SDKs & repos:** Reviews and rebuttals for agent papers
- **Downloadable / offline:** Free; API
- *Note:* Agent benchmarks attract methodological criticism; the reviews are where you find it.

### SWE-bench

- **Docs:** [swebench.com](https://www.swebench.com/)
- **Source:** [github.com/SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench)
- **SDKs & repos:** The dominant coding-agent benchmark, with a public leaderboard
- **Downloadable / offline:** Free; harness in the repo
- *Note:* Read the harness before believing a score. Verified, Lite and Full are different tasks and get conflated constantly.

### Terminal-Bench

- **Docs:** [tbench.ai](https://www.tbench.ai/)
- **SDKs & repos:** Benchmark for agents operating a real terminal
- **Downloadable / offline:** Free
- *Note:* Harder and less saturated than SWE-bench.

### Berkeley Function-Calling Leaderboard

- **Docs:** [gorilla.cs.berkeley.edu/leaderboard.html](https://gorilla.cs.berkeley.edu/leaderboard.html)
- **SDKs & repos:** Standardised evaluation of tool- and function-calling ability
- **Downloadable / offline:** Free
- *Note:* The most useful single number for 'can this model call tools reliably'.

### Papers with Code

- **Docs:** [paperswithcode.com](https://paperswithcode.com/)
- **SDKs & repos:** Leaderboards and linked implementations
- **Downloadable / offline:** Free

### Hugging Face Papers

- **Docs:** [huggingface.co/papers](https://huggingface.co/papers)
- **SDKs & repos:** Daily curation, usually with the agent repos linked
- **Downloadable / offline:** Free

### Anthropic Engineering

- **Docs:** [anthropic.com/engineering](https://www.anthropic.com/engineering)
- **SDKs & repos:** Practitioner write-ups including 'Building effective agents'
- **Downloadable / offline:** Free
- *Note:* Currently the best-written practical material on agent design from any lab.

### Google DeepMind publications

- **Docs:** [deepmind.google/research/publications](https://deepmind.google/research/publications/)
- **SDKs & repos:** Planning, tool use and multi-agent research
- **Downloadable / offline:** Free

### Microsoft Research publications

- **Docs:** [microsoft.com/en-us/research/publications](https://www.microsoft.com/en-us/research/publications/)
- **SDKs & repos:** AutoGen and multi-agent orchestration research
- **Downloadable / offline:** Free

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** Where the systems and security consequences of agents are starting to appear
- **Downloadable / offline:** All papers free
- *Note:* As agents get deployment surface, the serious failure analysis will land here rather than at ML venues.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*21 resources across 6 topics.*


#### Read this before you pick a framework

- **[Building Effective Agents (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents)** — The most useful thing written on this topic. Its central argument — that most problems need a workflow, not an agent, and that you should start with the simplest thing that works — will save you months.
- **[ReAct paper](https://arxiv.org/abs/2210.03629)** — The reasoning-and-acting loop every framework is a variation on. Short.
- **[smolagents](https://github.com/huggingface/smolagents)** — About a thousand lines. Read it end to end and the magic disappears — an agent is a loop, a tool schema, and a stopping condition.


#### Learn the protocol layer

- **[Model Context Protocol](https://modelcontextprotocol.io/)** — The emerging standard for tool and data access. Learn it before any framework's bespoke tool abstraction.
- **[MCP specification](https://modelcontextprotocol.io/specification/2025-06-18)** — Short and readable. The trust-boundary section is the part most integrations get wrong.
- **[MCP reference servers](https://github.com/modelcontextprotocol/servers)** — Read two or three before writing your own.
- **[OpenAI function calling](https://platform.openai.com/docs/guides/function-calling)** — The raw tool-call interface underneath every framework. Most agent bugs are schema bugs.


#### A first framework

- **[OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)** — Small, clear, with tracing built in. Hides little, which is what you want while learning.
- **[Pydantic AI](https://ai.pydantic.dev/)** — Type-safe and idiomatic Python. Good if you want validation from day one.
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — Move here when control flow and durability start to matter. The graph model is worth the learning curve.


#### Watch mature agents work

- **[Claude Code docs](https://docs.claude.com/en/docs/claude-code/overview)** — A production coding agent you can run and inspect. The hooks and permissions design is the lesson.
- **[OpenHands](https://github.com/All-Hands-AI/OpenHands)** — Fully open and capable. Read the sandboxed runtime.
- **[Aider](https://aider.chat/docs/)** — The repository-map approach to context selection, clearly documented.
- **[SWE-agent](https://swe-agent.com/latest/)** — The agent-computer-interface idea: tool design matters more than prompt wording.


#### Safety, from the start

- **[OWASP Top 10 for LLM Applications](https://genai.owasp.org/)** — Excessive agency and insecure output handling are the entries that will bite you.
- **[The lethal trifecta](https://simonwillison.net/tags/prompt-injection/)** — Private data, untrusted content, external communication. Any two is fine; all three is not.
- **[E2B](https://e2b.dev/docs)** — If your agent runs code it generated, sandbox it. This is a hard requirement, not a nice-to-have.


#### Finding and reading papers

- **[Hugging Face Papers](https://huggingface.co/papers)** — Daily curation, usually with the agent repo linked alongside.
- **[arXiv cs.SE](https://arxiv.org/list/cs.SE/recent)** — Where coding-agent research actually appears. Easy to miss if you only watch cs.AI.
- **[SWE-bench](https://www.swebench.com/)** — Read the harness, not just the leaderboard.
- **[Anthropic Engineering](https://www.anthropic.com/engineering)** — Practitioner write-ups with more signal than most preprints.


### Advanced

*33 resources across 6 topics.*


#### Architecture & control flow

- **[LangGraph](https://github.com/langchain-ai/langgraph)** — Explicit state graphs, checkpointing, interrupts, time travel. Read the checkpointer implementations.
- **[Temporal](https://docs.temporal.io/)** — Durable execution done properly. Agent loops are long-running workflows; most frameworks reimplement this badly.
- **[AutoGen](https://github.com/microsoft/autogen)** — Event-driven multi-agent core, with research behind the design decisions.
- **[Google ADK](https://google.github.io/adk-docs/)** — Multi-agent composition plus a deployment story.
- **[A2A protocol](https://github.com/a2aproject/A2A)** — Agent-to-agent delegation as a wire protocol rather than a library abstraction.
- **[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)** — Re-read it after you have shipped one. The workflow-versus-agent distinction lands differently then.


#### Context engineering

- **[Aider repository map](https://aider.chat/docs/)** — Tree-sitter-driven repo mapping to fit a large codebase into a small context.
- **[Claude Agent SDK](https://docs.claude.com/en/api/agent-sdk/overview)** — Compaction, subagents and context editing in a production harness.
- **[SWE-agent](https://github.com/SWE-agent/SWE-agent)** — The ACI argument: design the tools for the model, not for the human.
- **[LlamaIndex Workflows](https://docs.llamaindex.ai/en/stable/module_guides/workflow/)** — Retrieval tightly coupled to agent control flow.
- **[tree-sitter](https://tree-sitter.github.io/tree-sitter/)** — The parsing layer under most code-aware context selection. See the compilers index.


#### Execution isolation

- **[E2B](https://github.com/e2b-dev/E2B)** — Firecracker microVMs per sandbox. Read the architecture, not just the SDK.
- **[gVisor](https://github.com/google/gvisor)** — Userspace kernel syscall interception — a different isolation point in the design space.
- **[Firecracker](https://firecracker-microvm.github.io/)** — The microVM monitor underneath much of this. See the cloud index.
- **[OpenHands runtime](https://github.com/All-Hands-AI/OpenHands)** — A complete open implementation of sandboxed agent execution.
- **[Modal](https://modal.com/docs)** — Fast cold starts matter when every tool call provisions a container.


#### Evaluating agents honestly

- **[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai)** — Agent-aware solvers and scorers. The framework to use if results must withstand scrutiny.
- **[SWE-bench harness](https://github.com/SWE-bench/SWE-bench)** — Read the evaluation harness. Contamination and variant confusion make most quoted numbers unreliable.
- **[Terminal-Bench](https://www.tbench.ai/)** — Less saturated, harder to game.
- **[Berkeley Function-Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html)** — Isolates tool-calling ability from everything else.
- **[Langfuse](https://github.com/langfuse/langfuse)** — Trace every step. Agent failures are almost never visible in the final output alone.
- **[OpenTelemetry GenAI semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/)** — Standard span names, so your traces survive a framework change.


#### Agent security in depth

- **[MITRE ATLAS](https://atlas.mitre.org/)** — Structure your threat model on an existing taxonomy.
- **[OWASP GenAI](https://genai.owasp.org/)** — The deeper guides beyond the Top 10 list, including agentic-specific material.
- **[garak](https://github.com/NVIDIA/garak)** — Probe your deployed agent, including tool-abuse paths.
- **[PyRIT](https://github.com/Azure/PyRIT)** — Automated red-teaming with orchestrators and converters.
- **[NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails)** — Action rails — constraining what an agent may do, not just what it may say.
- **[Simon Willison's archive](https://simonwillison.net/tags/prompt-injection/)** — Keep reading it. This problem is not solved and the attack surface keeps growing.


#### Primary papers

- **[ReAct](https://arxiv.org/abs/2210.03629)** — Reasoning interleaved with acting. The foundation.
- **[Reflexion](https://arxiv.org/abs/2303.11366)** — Verbal self-critique as a learning signal across attempts.
- **[Toolformer](https://arxiv.org/abs/2302.04761)** — Models learning when to call tools, self-supervised.
- **[arXiv cs.MA](https://arxiv.org/list/cs.MA/recent)** — Multi-agent systems, where the coordination literature lives.
- **[OpenReview](https://openreview.net/)** — Agent benchmarks attract methodological criticism; the reviews are where you find it.


---

## Video courses, channels & talks

*9 resources across 1 group.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[LangChain](https://www.youtube.com/@LangChain)** — Framework walkthroughs for agents and RAG; vendor content, verify against the docs.
- **[Hugging Face](https://www.youtube.com/@HuggingFace)** — The open LLM ecosystem: transformers, datasets, agents, tool calling.
- **[Dave Ebbelaar](https://www.youtube.com/@daveebbelaar)** — Practical LLM and agent app builds, end to end, in Python.
- **[Machine Learning Street Talk](https://www.youtube.com/@MachineLearningStreetTalk)** — Long-form research interviews; useful for context around current papers.
- **[OpenAI](https://www.youtube.com/@OpenAI)** — Model releases and DevDay talks; primary for API and product behaviour.
- **[Google DeepMind](https://www.youtube.com/@GoogleDeepMind)** — Research overviews and model announcements from DeepMind.
- **[InfoQ](https://www.youtube.com/@InfoQ)** — Conference keynotes and architecture talks — good for orientation, verify specifics elsewhere.
- **[Latent Space](https://www.youtube.com/@LatentSpacePod)** — Agent-tooling interviews; current, but the frameworks discussed age within months.
- **[TWIML AI Podcast](https://www.youtube.com/@twimlai)** — Applied-agent interviews, including RAG and evaluation practice.

*Note:* Framework channels dominate agent video and they age badly; watch for the pattern, then re-implement against current docs.

## Conference videos, notes & archives

*5 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

Agent work has no dedicated peer-reviewed venue yet; it appears at the main ML conferences and is demonstrated at framework dev days.

### Conference channels & video archives

- **[ICLR](https://iclr.cc/)** — Most agent-paper activity; the open reviews are useful for seeing what reviewers actually object to.
- **[NeurIPS proceedings](https://neurips.cc/Conferences/2025)** — The other half of agent research, especially tool use and evaluation.
- **[ICML](https://icml.cc/)** — Proceedings portal.
- **[AI Engineer World's Fair](https://ai.engineer/)** — The closest thing to a dedicated conference for applied LLM and agent work; recordings published by the organisers, vendor-heavy.

### Notes, proceedings & paper-adjacent archives

- **Framework dev days are release notes** — LangChain, OpenAI and Hugging Face agent talks describe the API as it was on the day. Re-check the docs before building on them.

## If you only do three things

1. **Read Anthropic's "Building Effective Agents".** Its argument that most problems want a workflow rather than an agent is the most load-bearing idea in the field.
2. **Read smolagents end to end.** A thousand lines. Afterwards no agent framework can mystify you.
3. **Learn MCP from the spec**, not from a framework's wrapper around it.

## Honest notes

- **Most things called agents should be workflows.** A fixed pipeline with one model call per step is more reliable, cheaper and easier to debug. Reach for autonomy only when the task genuinely cannot be decomposed ahead of time.
- **Tool design beats prompt design.** SWE-agent's central finding. If the agent is failing, fix the tools and their schemas before rewriting the system prompt.
- **Agents escalate prompt injection into remote code execution.** The lethal trifecta — private data, untrusted content, external communication — is an architecture constraint. No prompt fixes it.
- **Sandbox generated code. Always.** E2B, gVisor or Firecracker. There is no safe version of running model-written code on your own machine.
- **SWE-bench scores are routinely quoted without naming the variant.** Verified, Lite and Full are different benchmarks. Ask which, and ask about contamination.
- **This documentation ages in months.** Several frameworks here have had breaking rewrites within a year. Trust the protocols and the papers over any individual framework's API.

---

## Related sections of this book

- [AI Agents Engineering](../llm/agents.md) — the explanatory chapters this index points out from
- [Prompt Engineering in Production](../llm/prompt-engineering.md)
- [RAG Systems](../llm/rag-systems.md)
- [LLM Security & Safety](../llm/llm-security.md)
- [Prompt Library](../meta/prompt-library.md)
- [Reference Libraries index](./README.md) — the other topic indexes
