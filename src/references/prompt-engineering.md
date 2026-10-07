# Prompt Engineering Reference Library

This page is a verified index of primary sources for prompt engineering: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Vendor prompting documentation, open guides, programmatic prompting and constrained decoding, evaluation frameworks, injection and red-teaming tooling, and a two-track path from hands-on tutorials to DSPy, token-level constraints and defensible evals.

**70 entries** across 6 categories, plus **53 education & reference-implementation resources** (22 basic / 31 advanced).

Every link HTTP-verified on **2026-10-07**.

> ai.google.dev redirects automated clients to an authentication page and openai.com/research returns 403; both load normally in a browser.

## Contents

- [1. Vendor prompting documentation](#1-vendor-prompting-documentation) — 8
- [2. Open guides, courses & curricula](#2-open-guides-courses--curricula) — 8
- [3. Programmatic prompting & constrained generation](#3-programmatic-prompting--constrained-generation) — 8
- [4. Evaluation — the part that makes prompting real](#4-evaluation--the-part-that-makes-prompting-real) — 11
- [5. Prompt injection, red-teaming & risk](#5-prompt-injection-red-teaming--risk) — 8
- [6. Research papers & open-access literature](#6-research-papers--open-access-literature) — 27
- [Education & reference implementations](#education--reference-implementations) — 53 (22 basic / 31 advanced)


## 1. Vendor prompting documentation

### OpenAI prompt engineering guide

- **Docs:** [platform.openai.com/docs/…](https://platform.openai.com/docs/guides/prompt-engineering)
- **Developer / API:** [platform.openai.com/docs](https://platform.openai.com/docs)
- **Source:** [github.com/openai/openai-cookbook](https://github.com/openai/openai-cookbook)
- **SDKs & repos:** Model-specific guidance; reasoning-model prompting differs materially from chat-model prompting
- **Downloadable / offline:** Docs site
- *Note:* Read the reasoning-model section separately. Advice that helps GPT-4-class models often actively hurts reasoning models.

### OpenAI Cookbook

- **Docs:** [cookbook.openai.com](https://cookbook.openai.com/)
- **Source:** [github.com/openai/openai-cookbook](https://github.com/openai/openai-cookbook)
- **SDKs & repos:** Runnable notebooks for structured output, function calling, evaluation, RAG
- **Downloadable / offline:** Repo cloneable; every example executable
- *Note:* More useful than the guide. Working code beats prose advice in this field.

### Anthropic prompt engineering

- **Docs:** [docs.claude.com/en/…](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)
- **Developer / API:** [docs.claude.com/en/home](https://docs.claude.com/en/home)
- **Source:** [github.com/anthropics/anthropic-cookbook](https://github.com/anthropics/anthropic-cookbook)
- **SDKs & repos:** XML tagging, prefilling, chain-of-thought, long-context technique
- **Downloadable / offline:** Docs site
- *Note:* The most substantive vendor documentation on prompting. Techniques are ordered by how much they actually help, which no one else does.

### Anthropic prompt library

- **Docs:** [docs.claude.com/en/…](https://docs.claude.com/en/resources/prompt-library/library)
- **SDKs & repos:** Dozens of worked production prompts across task types
- **Downloadable / offline:** Web
- *Note:* Read these as examples of structure, not as prompts to copy.

### Anthropic Cookbook

- **Docs:** [github.com/anthropics/anthropic-cookbook](https://github.com/anthropics/anthropic-cookbook)
- **Source:** [github.com/anthropics/anthropic-cookbook](https://github.com/anthropics/anthropic-cookbook)
- **SDKs & repos:** Notebooks for tool use, retrieval, sub-agents, evaluation
- **Downloadable / offline:** Repo

### Google Gemini prompting strategies

- **Docs:** [ai.google.dev/gemini-api/…](https://ai.google.dev/gemini-api/docs/prompting-strategies)
- **Developer / API:** [ai.google.dev](https://ai.google.dev/)
- **Source:** [github.com/google-gemini/cookbook](https://github.com/google-gemini/cookbook)
- **SDKs & repos:** Prompt design for Gemini; long-context and multimodal specifics
- **Downloadable / offline:** Docs site; cookbook notebooks in the repo
- *Note:* Google devsite redirects automated clients to an auth page; loads in a browser.

### Azure OpenAI prompt engineering

- **Docs:** [learn.microsoft.com/en-us/…](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering)
- **Developer / API:** [learn.microsoft.com/en-us/…](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- **SDKs & repos:** Enterprise framing: system messages, grounding, safety
- **Downloadable / offline:** Learn, offline export

### OpenAI structured outputs

- **Docs:** [platform.openai.com/docs/…](https://platform.openai.com/docs/guides/structured-outputs)
- **Developer / API:** [platform.openai.com/docs](https://platform.openai.com/docs)
- **SDKs & repos:** Constrained generation against a JSON Schema
- **Downloadable / offline:** Docs site
- *Note:* Prefer schema-constrained output over asking politely for JSON. It is the single highest-leverage change in most pipelines.


## 2. Open guides, courses & curricula

### Prompt Engineering Guide (DAIR.AI)

- **Docs:** [promptingguide.ai](https://www.promptingguide.ai/)
- **Developer / API:** [promptingguide.ai/papers](https://www.promptingguide.ai/papers)
- **Source:** [github.com/dair-ai/Prompt-Engineering-Guide](https://github.com/dair-ai/Prompt-Engineering-Guide)
- **SDKs & repos:** Technique-by-technique coverage with the originating paper linked for each
- **Downloadable / offline:** Repo cloneable; translated into many languages
- *Note:* The best vendor-neutral reference. Its paper index is the fastest route from a technique's name to its source.

### Learn Prompting

- **Docs:** [learnprompting.org/docs/introduction](https://learnprompting.org/docs/introduction)
- **SDKs & repos:** Structured free course from basics through adversarial prompting
- **Downloadable / offline:** Web
- *Note:* Good sequencing for beginners; broader and shallower than the DAIR guide.

### Anthropic interactive tutorial

- **Docs:** [github.com/anthropics/…](https://github.com/anthropics/prompt-eng-interactive-tutorial)
- **Source:** [github.com/anthropics/…](https://github.com/anthropics/prompt-eng-interactive-tutorial)
- **SDKs & repos:** Nine chapters of hands-on exercises with solutions
- **Downloadable / offline:** Notebooks in-repo
- *Note:* The best single way to actually learn this rather than read about it.

### Anthropic courses

- **Docs:** [github.com/anthropics/courses](https://github.com/anthropics/courses)
- **Source:** [github.com/anthropics/courses](https://github.com/anthropics/courses)
- **SDKs & repos:** Prompt engineering, evaluation, tool use, RAG
- **Downloadable / offline:** Repo

### Generative AI for Beginners (Microsoft)

- **Docs:** [microsoft.github.io/…](https://microsoft.github.io/generative-ai-for-beginners/)
- **Source:** [github.com/microsoft/…](https://github.com/microsoft/generative-ai-for-beginners)
- **SDKs & repos:** 21-lesson course with runnable code
- **Downloadable / offline:** Repo cloneable

### DeepLearning.AI short courses

- **Docs:** [deeplearning.ai/short-courses](https://www.deeplearning.ai/short-courses/)
- **SDKs & repos:** Hour-long free courses, many built with the model vendors
- **Downloadable / offline:** Free with registration

### LLM Course (mlabonne)

- **Docs:** [github.com/mlabonne/llm-course](https://github.com/mlabonne/llm-course)
- **Source:** [github.com/mlabonne/llm-course](https://github.com/mlabonne/llm-course)
- **SDKs & repos:** Roadmap with notebooks spanning fundamentals to deployment
- **Downloadable / offline:** Repo

### Chat templating (Hugging Face)

- **Docs:** [huggingface.co/docs/…](https://huggingface.co/docs/transformers/main/en/chat_templating)
- **Source:** [github.com/huggingface/transformers](https://github.com/huggingface/transformers)
- **SDKs & repos:** How chat messages actually become tokens for open-weight models
- **Downloadable / offline:** Docs site
- *Note:* Essential and widely skipped. Most 'the open model ignores my prompt' bugs are template bugs.


## 3. Programmatic prompting & constrained generation

### DSPy

- **Docs:** [dspy.ai](https://dspy.ai/)
- **Source:** [github.com/stanfordnlp/dspy](https://github.com/stanfordnlp/dspy)
- **SDKs & repos:** Declare the task signature, let an optimizer compile the prompt against a metric
- **Downloadable / offline:** Docs site
- *Note:* The most serious attempt to make prompting an engineering discipline instead of a craft. Stanford NLP.

### Outlines

- **Docs:** [dottxt-ai.github.io/outlines](https://dottxt-ai.github.io/outlines/)
- **Source:** [github.com/dottxt-ai/outlines](https://github.com/dottxt-ai/outlines)
- **SDKs & repos:** Structured generation via regex, JSON Schema and context-free grammars
- **Downloadable / offline:** Docs site
- *Note:* Constrains at the token level, so invalid output is impossible rather than merely unlikely.

### Instructor

- **Docs:** [python.useinstructor.com](https://python.useinstructor.com/)
- **Source:** [github.com/567-labs/instructor](https://github.com/567-labs/instructor)
- **SDKs & repos:** Pydantic models as the output contract, with validation and retries
- **Downloadable / offline:** Docs site
- *Note:* The pragmatic choice when you just want typed objects out of an API.

### Guidance

- **Docs:** [github.com/guidance-ai/guidance](https://github.com/guidance-ai/guidance)
- **Source:** [github.com/guidance-ai/guidance](https://github.com/guidance-ai/guidance)
- **SDKs & repos:** Interleave control flow and generation in one program
- **Downloadable / offline:** In-repo docs

### BAML

- **Docs:** [docs.boundaryml.com](https://docs.boundaryml.com/)
- **Source:** [github.com/BoundaryML/baml](https://github.com/BoundaryML/baml)
- **SDKs & repos:** A dedicated language for prompts with typed schemas and generated clients
- **Downloadable / offline:** Docs site
- *Note:* Treats the prompt as a function signature with a compiler. Unusual and worth a look.

### LMQL

- **Docs:** [lmql.ai](https://lmql.ai/)
- **Source:** [github.com/eth-sri/lmql](https://github.com/eth-sri/lmql)
- **SDKs & repos:** Query language for LLMs with constraints as first-class syntax
- **Downloadable / offline:** Docs site
- *Note:* ETH Zurich research project.

### LiteLLM

- **Docs:** [docs.litellm.ai](https://docs.litellm.ai/)
- **Source:** [github.com/BerriAI/litellm](https://github.com/BerriAI/litellm)
- **SDKs & repos:** One OpenAI-compatible interface across 100+ providers; routing, fallbacks, cost tracking
- **Downloadable / offline:** Docs site
- *Note:* Makes prompts portable across vendors, which is what lets you A/B them honestly.

### OpenRouter

- **Docs:** [openrouter.ai/docs](https://openrouter.ai/docs)
- **SDKs & repos:** Single API across many hosted models
- **Downloadable / offline:** Docs site


## 4. Evaluation — the part that makes prompting real

### promptfoo

- **Docs:** [promptfoo.dev/docs/intro](https://www.promptfoo.dev/docs/intro/)
- **Source:** [github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)
- **SDKs & repos:** Declarative prompt testing, side-by-side comparison, CI integration, red-teaming
- **Downloadable / offline:** Docs site; runs locally
- *Note:* The easiest way to stop guessing. Write assertions, run the matrix, see which prompt actually wins.

### OpenAI Evals

- **Docs:** [github.com/openai/evals](https://github.com/openai/evals)
- **Source:** [github.com/openai/evals](https://github.com/openai/evals)
- **SDKs & repos:** Framework and registry for model evaluations
- **Downloadable / offline:** Repo

### Inspect AI

- **Docs:** [inspect.aisi.org.uk](https://inspect.aisi.org.uk/)
- **Source:** [github.com/UKGovernmentBEIS/inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai)
- **SDKs & repos:** Evaluation framework from the UK AI Safety Institute: solvers, scorers, agent support
- **Downloadable / offline:** Docs site
- *Note:* The most rigorously designed open eval framework. Built for work that has to withstand scrutiny.

### Ragas

- **Docs:** [docs.ragas.io](https://docs.ragas.io/)
- **Source:** [github.com/explodinggradients/ragas](https://github.com/explodinggradients/ragas)
- **SDKs & repos:** Reference-free metrics for retrieval-augmented pipelines
- **Downloadable / offline:** Docs site
- *Note:* Faithfulness and context-precision are the metrics that catch real RAG regressions.

### DeepEval

- **Docs:** [deepeval.com/docs/getting-started](https://deepeval.com/docs/getting-started)
- **Source:** [github.com/confident-ai/deepeval](https://github.com/confident-ai/deepeval)
- **SDKs & repos:** Pytest-style LLM testing with a metric library
- **Downloadable / offline:** Docs site

### LangSmith

- **Docs:** [docs.smith.langchain.com](https://docs.smith.langchain.com/)
- **SDKs & repos:** Tracing, datasets, evaluation and prompt versioning
- **Downloadable / offline:** Docs site

### Langfuse

- **Docs:** [langfuse.com/docs](https://langfuse.com/docs)
- **Source:** [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse)
- **SDKs & repos:** Open-source tracing, prompt management and evaluation
- **Downloadable / offline:** Docs site; self-hostable
- *Note:* The self-hostable option, which matters if prompts or data cannot leave your infrastructure.

### Phoenix (Arize)

- **Docs:** [arize.com/docs/phoenix](https://arize.com/docs/phoenix)
- **Source:** [github.com/Arize-ai/phoenix](https://github.com/Arize-ai/phoenix)
- **SDKs & repos:** Open-source tracing and evaluation, OpenTelemetry-native
- **Downloadable / offline:** Docs site

### Braintrust

- **Docs:** [braintrust.dev/docs](https://www.braintrust.dev/docs)
- **SDKs & repos:** Evaluation, logging and prompt iteration
- **Downloadable / offline:** Docs site

### HELM

- **Docs:** [crfm.stanford.edu/helm](https://crfm.stanford.edu/helm/)
- **Source:** [github.com/stanford-crfm/helm](https://github.com/stanford-crfm/helm)
- **SDKs & repos:** Stanford's holistic evaluation framework and public results
- **Downloadable / offline:** Free results + repo
- *Note:* Multi-metric by design — accuracy, calibration, robustness, bias, efficiency — rather than one headline number.

### lm-evaluation-harness

- **Docs:** [github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- **Source:** [github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- **SDKs & repos:** The framework behind most published benchmark numbers
- **Downloadable / offline:** In-repo docs
- *Note:* Read the task definition before comparing anyone's reported score to your own.


## 5. Prompt injection, red-teaming & risk

### OWASP Top 10 for LLM Applications

- **Docs:** [genai.owasp.org](https://genai.owasp.org/)
- **Developer / API:** [owasp.org/…](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- **SDKs & repos:** Prompt injection, insecure output handling, excessive agency and the rest
- **Downloadable / offline:** Free PDFs per release
- *Note:* Prompt injection is #1 and remains unsolved. Read this before shipping anything that reads untrusted text.

### Simon Willison on prompt injection

- **Docs:** [simonwillison.net/tags/prompt-injection](https://simonwillison.net/tags/prompt-injection/)
- **Developer / API:** [simonwillison.net](https://simonwillison.net/)
- **SDKs & repos:** The longest-running and clearest ongoing analysis of the problem
- **Downloadable / offline:** Free archive
- *Note:* He coined the framing. The 'lethal trifecta' — private data, untrusted content, external communication — is the most useful mental model available.

### MITRE ATLAS

- **Docs:** [atlas.mitre.org](https://atlas.mitre.org/)
- **SDKs & repos:** Adversarial threat landscape for AI systems, structured like ATT&CK
- **Downloadable / offline:** Free; matrices downloadable
- *Note:* Use it to structure a threat model rather than inventing categories.

### garak

- **Docs:** [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)
- **Source:** [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)
- **SDKs & repos:** LLM vulnerability scanner with dozens of probe families
- **Downloadable / offline:** In-repo docs
- *Note:* Point it at your deployment and read the report. NVIDIA-maintained.

### PyRIT

- **Docs:** [azure.github.io/PyRIT](https://azure.github.io/PyRIT/)
- **Source:** [github.com/Azure/PyRIT](https://github.com/Azure/PyRIT)
- **SDKs & repos:** Microsoft's Python risk identification toolkit for automated red-teaming
- **Downloadable / offline:** Docs site

### Guardrails AI

- **Docs:** [guardrailsai.com/docs](https://www.guardrailsai.com/docs)
- **Source:** [github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails)
- **SDKs & repos:** Input and output validators with a shared hub
- **Downloadable / offline:** Docs site

### NeMo Guardrails

- **Docs:** [docs.nvidia.com/nemo/…](https://docs.nvidia.com/nemo/guardrails/latest/index.html)
- **Source:** [github.com/NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails)
- **SDKs & repos:** Programmable dialogue rails in a dedicated modelling language
- **Downloadable / offline:** Docs site

### NIST AI Risk Management Framework

- **Docs:** [nist.gov/itl/ai-risk-management-framework](https://www.nist.gov/itl/ai-risk-management-framework)
- **SDKs & repos:** Governance framework; the generative AI profile is the relevant part
- **Downloadable / offline:** Free PDFs
- *Note:* What compliance teams will ask about. Worth skimming before they do.


## 6. Research papers & open-access literature

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

### arXiv cs.CL (Computation and Language)

- **Docs:** [arxiv.org/list/cs.CL/recent](https://arxiv.org/list/cs.CL/recent)
- **SDKs & repos:** Where prompting, reasoning and evaluation papers appear first. See also [arxiv.org/list/cs.AI/recent](https://arxiv.org/list/cs.AI/recent)
- **Downloadable / offline:** Free
- *Note:* Very high volume. Use a curation layer rather than reading the listing.

### ACL Anthology

- **Docs:** [aclanthology.org](https://aclanthology.org/)
- **Source:** [github.com/acl-org/acl-anthology](https://github.com/acl-org/acl-anthology)
- **SDKs & repos:** Every ACL, EMNLP and NAACL paper — the peer-reviewed home of this field
- **Downloadable / offline:** 100% open access; full metadata dumps in the repo
- *Note:* Prompting results that survived review live here, not on arXiv. Check both.

### COLM

- **Docs:** [colmweb.org](https://colmweb.org/)
- **SDKs & repos:** Conference on Language Modeling — a venue created specifically for LLM research
- **Downloadable / offline:** Papers open via OpenReview
- *Note:* Newer and more focused than NeurIPS/ICML for this material.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **SDKs & repos:** ICLR and COLM submissions with full public review threads
- **Downloadable / offline:** Free; API
- *Note:* For a contested prompting claim, the reviews are often more useful than the paper.

### Papers with Code

- **Docs:** [paperswithcode.com](https://paperswithcode.com/)
- **SDKs & repos:** Benchmark leaderboards linked to implementations
- **Downloadable / offline:** Free
- *Note:* Prompting leaderboards are especially gameable — check the evaluation protocol before trusting a delta.

### Hugging Face Papers

- **Docs:** [huggingface.co/papers](https://huggingface.co/papers)
- **SDKs & repos:** Daily curated arXiv selection with discussion
- **Downloadable / offline:** Free
- *Note:* The most practical daily filter.

### ML Papers of the Week

- **Docs:** [github.com/dair-ai/ML-Papers-of-the-Week](https://github.com/dair-ai/ML-Papers-of-the-Week)
- **Source:** [github.com/dair-ai/ML-Papers-of-the-Week](https://github.com/dair-ai/ML-Papers-of-the-Week)
- **SDKs & repos:** Weekly curated digest from the DAIR.AI team
- **Downloadable / offline:** Repo
- *Note:* Same group that maintains the Prompt Engineering Guide.

### Prompting Guide — paper index

- **Docs:** [promptingguide.ai/papers](https://www.promptingguide.ai/papers)
- **SDKs & repos:** The foundational prompting papers, organised by technique
- **Downloadable / offline:** Free
- *Note:* The fastest way to find the original paper behind a named technique.

### Anthropic Research

- **Docs:** [anthropic.com/research](https://www.anthropic.com/research)
- **SDKs & repos:** Interpretability, alignment, and model-behaviour work
- **Downloadable / offline:** Free

### Google DeepMind publications

- **Docs:** [deepmind.google/research/publications](https://deepmind.google/research/publications/)
- **SDKs & repos:** Chain-of-thought, self-consistency and scaling work originated here
- **Downloadable / offline:** Free PDFs

### OpenAI Research

- **Docs:** [openai.com/research](https://openai.com/research/)
- **SDKs & repos:** Model and method papers
- **Downloadable / offline:** Free
- *Note:* 403s to automated clients; loads in a browser.

### Lil'Log

- **Docs:** [lilianweng.github.io](https://lilianweng.github.io/)
- **SDKs & repos:** Survey-grade technical posts, including the standard prompt-engineering overview
- **Downloadable / offline:** Free
- *Note:* Read [lilianweng.github.io/posts/…](https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/) before the primary papers.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*22 resources across 6 topics.*


#### Do this first

- **[Anthropic interactive prompt engineering tutorial](https://github.com/anthropics/prompt-eng-interactive-tutorial)** — Nine chapters of exercises with solutions. Hands-on, and you will learn more in an afternoon than from a month of reading threads.
- **[Anthropic prompt engineering docs](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)** — The techniques, ordered by how much they actually help. Applies well beyond Claude.
- **[Prompt Engineering Guide](https://www.promptingguide.ai/)** — The vendor-neutral reference. Keep it open while you work.


#### Learn to measure, early

- **[promptfoo](https://www.promptfoo.dev/docs/intro/)** — Write assertions, run prompts side by side, see which one wins. Start measuring before your prompts get complicated, not after.
- **[OpenAI Cookbook](https://cookbook.openai.com/)** — Runnable notebooks, including evaluation. Code you can execute beats advice you have to trust.
- **[Hamel Husain on evals](https://hamel.dev/)** — The clearest practical writing on building evaluation for LLM products. Start with the 'Your AI Product Needs Evals' post.
- **[What We Learned from a Year of Building with LLMs](https://applied-llms.org/)** — Six practitioners, written jointly, no vendor agenda. The most honest overview of what works in production.


#### The things that make prompts reliable

- **[Structured outputs](https://platform.openai.com/docs/guides/structured-outputs)** — Constrain output to a JSON Schema instead of asking for JSON. Removes an entire class of failure.
- **[Instructor](https://python.useinstructor.com/)** — Pydantic models as the contract, with automatic validation and retry.
- **[Chat templating](https://huggingface.co/docs/transformers/main/en/chat_templating)** — If you use open-weight models, learn this. Most mysterious failures are template mismatches.
- **[LiteLLM](https://docs.litellm.ai/)** — One interface across providers, so you can compare models on the same prompt fairly.


#### Know the failure modes before you ship

- **[OWASP Top 10 for LLM Applications](https://genai.owasp.org/)** — Prompt injection is number one and has no general fix. Read this before exposing a model to untrusted input.
- **[Simon Willison's prompt injection archive](https://simonwillison.net/tags/prompt-injection/)** — Years of worked examples. The 'lethal trifecta' framing will change how you scope features.
- **[garak](https://github.com/NVIDIA/garak)** — Scan your own deployment and read what comes back.


#### Courses, if you want structure

- **[Learn Prompting](https://learnprompting.org/docs/introduction)** — Free, sequenced, beginner-friendly.
- **[Generative AI for Beginners](https://microsoft.github.io/generative-ai-for-beginners/)** — 21 lessons with runnable code.
- **[DeepLearning.AI short courses](https://www.deeplearning.ai/short-courses/)** — Short, free, often co-built with the labs themselves.
- **[Anthropic courses](https://github.com/anthropics/courses)** — Prompting, evaluation, tool use and RAG in one repo.


#### Finding and reading papers

- **[Prompting Guide paper index](https://www.promptingguide.ai/papers)** — Technique name to source paper, directly. The fastest lookup in this field.
- **[Lil'Log on prompt engineering](https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/)** — A survey with citations. Read it before the primary papers.
- **[ACL Anthology](https://aclanthology.org/)** — Peer-reviewed NLP, fully open. Where prompting claims that survived review live.
- **[Hugging Face Papers](https://huggingface.co/papers)** — A daily filter on an unmanageable arXiv firehose.


### Advanced

*31 resources across 6 topics.*


#### Stop writing prompts by hand

- **[DSPy](https://dspy.ai/)** — Declare a signature and a metric; let an optimizer compile the prompt. The most credible path from craft to engineering.
- **[DSPy source](https://github.com/stanfordnlp/dspy)** — Read the optimizers — MIPROv2 and the bootstrap few-shot approaches are the interesting part.
- **[BAML](https://docs.boundaryml.com/)** — Prompts as typed functions with a compiler and generated clients.
- **[Guidance](https://github.com/guidance-ai/guidance)** — Control flow interleaved with generation.
- **[LMQL](https://lmql.ai/)** — Constraints as language syntax. Research-grade, conceptually clean.


#### Constrained decoding at the token level

- **[Outlines](https://dottxt-ai.github.io/outlines/)** — Regex, JSON Schema and CFG constraints applied during sampling. Invalid output becomes impossible.
- **[Outlines source](https://github.com/dottxt-ai/outlines)** — The finite-state-machine index construction is worth reading on its own.
- **[SGLang](https://github.com/sgl-project/sglang)** — RadixAttention plus a frontend language for structured, multi-call programs.
- **[JSON Schema](https://json-schema.org/)** — Learn the spec properly. Your schema is now part of your prompt, and loose schemas produce loose output.


#### Evaluation you can defend

- **[Inspect AI](https://inspect.aisi.org.uk/)** — UK AI Safety Institute framework. Solvers, scorers, agent evaluation; built for results that get scrutinised.
- **[HELM](https://crfm.stanford.edu/helm/)** — Holistic evaluation across accuracy, calibration, robustness and bias rather than one number.
- **[lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)** — The de facto standard harness. Read task definitions before trusting cross-paper comparisons.
- **[Ragas](https://docs.ragas.io/)** — Retrieval-specific metrics that actually catch regressions.
- **[promptfoo](https://github.com/promptfoo/promptfoo)** — Put the eval matrix in CI so prompt changes are reviewed like code changes.
- **[Langfuse](https://github.com/langfuse/langfuse)** — Self-hostable tracing and prompt versioning, for when data cannot leave your infrastructure.


#### Adversarial prompting

- **[MITRE ATLAS](https://atlas.mitre.org/)** — Structured adversarial taxonomy for AI systems, in ATT&CK's shape.
- **[PyRIT](https://github.com/Azure/PyRIT)** — Automated red-teaming with orchestrators and converters.
- **[garak](https://github.com/NVIDIA/garak)** — Probe families covering jailbreaks, leakage, toxicity and encoding attacks.
- **[promptfoo red-teaming](https://www.promptfoo.dev/docs/intro/)** — Adversarial generation wired into the same harness as your functional evals.
- **[OWASP GenAI](https://genai.owasp.org/)** — Track the project, not just the Top 10 list — the deeper guides are where the substance is.
- **[NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)** — The governance vocabulary your organisation will eventually adopt.


#### Primary papers worth reading in full

- **[Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903)** — The paper that started the technique. Short, and the ablations matter more than the headline.
- **[Self-Consistency](https://arxiv.org/abs/2203.11171)** — Sample multiple reasoning paths and take the majority. Simple, and still one of the most reliable gains.
- **[ReAct](https://arxiv.org/abs/2210.03629)** — Interleaving reasoning and acting — the foundation almost every agent framework builds on.
- **[Tree of Thoughts](https://arxiv.org/abs/2305.10601)** — Search over reasoning states. Expensive, instructive about where simple prompting ends.
- **[Prompting Guide paper index](https://www.promptingguide.ai/papers)** — Everything else, mapped by technique.


#### Where the field publishes

- **[ACL Anthology](https://aclanthology.org/)** — Peer-reviewed, fully open, complete.
- **[COLM](https://colmweb.org/)** — A venue built specifically for language-model research.
- **[OpenReview](https://openreview.net/)** — Reviews and rebuttals. For contested results, read these first.
- **[arXiv cs.CL](https://arxiv.org/list/cs.CL/recent)** — The firehose. Pair with curation.
- **[ML Papers of the Week](https://github.com/dair-ai/ML-Papers-of-the-Week)** — A weekly curated digest from the DAIR.AI team.


---

## If you only do three things

1. **Work through Anthropic's interactive tutorial.** Nine chapters, exercises, solutions. Hands-on beats reading.
2. **Set up promptfoo before your prompts get complicated.** Once you can measure, prompt engineering stops being folklore.
3. **Read OWASP's LLM Top 10 and Simon Willison on prompt injection.** Then decide what your system is allowed to touch.

## Honest notes

- **Most prompt advice online is untested folklore.** The half-life is short and almost none of it is measured. Prefer vendor docs, papers, and your own evals.
- **Reasoning models invert much of the standard advice.** "Think step by step" and elaborate few-shot scaffolding can make them worse. Check the model-specific guidance.
- **Constrain output, do not request it.** JSON Schema or grammar-constrained decoding eliminates a failure class that no amount of prompt wording will.
- **Evaluation is the whole discipline.** A prompt you cannot measure is a guess. This is why the eval section here is longer than the technique section.
- **Prompt injection has no general solution.** Treat it as an architecture constraint, not a prompt-wording problem.
- **Chat templates break open-weight models silently.** If an open model ignores your system prompt, suspect the template before the prompt.

---

## Related sections of this book

- [Prompt Engineering in Production](../llm/prompt-engineering.md) — the explanatory chapters this index points out from
- [AI Agents Engineering](../llm/agents.md)
- [LLM Security & Safety](../llm/llm-security.md)
- [LLM Evaluation](../llm/llm-serving/evaluation.md)
- [Prompt Library](../meta/prompt-library.md)
- [Reference Libraries index](./README.md) — the other topic indexes
