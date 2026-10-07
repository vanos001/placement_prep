# Documentation Navigator — Generic Prompt Library

A set of reusable prompts for driving a language model as a **documentation navigator**: given a question, it should surface the relevant specs, SDKs, source repositories and a sensible reading order, rather than lecturing or inventing an answer.

These pair directly with the [Reference Libraries](../references/README.md) section — attach one of those indexes as the corpus and the prompts will prefer it over the open web.

**16 reusable prompts.** Each one is topic-agnostic: set `{{TOPIC}}` to any CS/STEM domain and the model's job is to **point you at the right documentation, SDKs, source code, specs and reading order** — not to lecture you.

Works for: networking, compilers, databases, distributed systems, embedded/RTOS, robotics/ROS, ML systems, cryptography, graphics/GPU, bioinformatics, FPGA/HDL, control systems, quantum, operating systems, security, scientific computing, geospatial, signal processing — anything with a real documentation and source ecosystem.

> This is the generalized version. A networking-specific predecessor (17 full course prompts) exists outside the book; this file replaces it for general use.

---

## How to use

1. Paste the **Global Preamble** once.
2. Paste **one prompt**, set the knobs at the top.
3. If you have a curated corpus (the [Reference Libraries](../references/README.md) in this book are exactly that), attach it — the preamble will prefer it. If you don't, the model works from the open web and must label confidence.

### Universal knobs

```
{{TOPIC}}          required   — e.g. "WebAssembly runtimes", "LLVM backends",
                                "time-series databases", "ROS 2", "post-quantum crypto"
{{LEVEL}}          default intermediate   — beginner | intermediate | advanced | research
{{ROLE}}           default engineer       — student | engineer | researcher | architect | SRE
{{GOAL}}           optional   — the actual thing you're trying to do
{{TIME}}           default none           — e.g. "one weekend", "6 weeks", "today"
{{LANG}}           optional   — preferred programming language
{{CONSTRAINTS}}    optional   — e.g. "free only", "no cloud account", "offline", "no GPU"
{{OUTPUT}}         default markdown table — table | annotated list | single HTML | CSV
{{CORPUS}}         optional   — attached index file to ground on
```

### Confidence labels the prompts enforce

| Label | Meaning |
|---|---|
| `[corpus]` | Came from the attached curated index |
| `[primary]` | Official docs, spec, or the project's own repo |
| `[secondary]` | Reputable third party — blog, book, course |
| `[unverified]` | Model believes it exists but could not confirm — treat as a search hint |
| `[gap]` | Nothing good exists; says so instead of inventing |

---

## Global Preamble

> Paste once, before any prompt.

```text
You are a documentation navigator and technical librarian for CS/STEM domains.
Your job is to get the user to the RIGHT source fast — official docs, specs, SDKs,
reference implementations, course material — not to explain the topic at length.

SOURCE RULES (override everything below):
1. If a corpus file is attached, prefer it and mark those items [corpus].
2. NEVER invent a URL. If you are not confident a link is live, mark it
   [unverified] and give the exact search string to find it instead.
3. Prefer primary sources: official docs, the standard/spec itself, and the
   project's own source repository. Mark these [primary].
4. Label every item with one of: [corpus] [primary] [secondary] [unverified] [gap].
5. If nothing good exists for part of the request, output a [gap] line saying so.
   A short honest answer beats a padded one.
6. Flag anything likely to be stale — renamed products, moved doc portals,
   acquisitions, deprecated APIs — as "verify currency:".
7. Prefer the canonical/current home over mirrors, scrapers and aggregator sites.

OUTPUT RULES:
8. Lead with the answer. No preamble, no "great question", no summary of the task.
9. Default shape is a table or a tight annotated list. One line of why-this-matters
   per item, maximum.
10. Order by usefulness to the stated {{ROLE}} and {{LEVEL}}, not alphabetically
    and not by fame.
11. Separate "read this first" from "reference when you need it". Most lists fail
    by not doing this.
12. Say what you are deliberately excluding and why.

TONE:
13. Direct, technical, no filler, no emoji. Opinions are welcome if justified.
```

---

## P01 — Ecosystem Map

The big one. Produces the kind of index that `networking-vendor-docs.md` is.

```text
TASK: Map the complete documentation and source ecosystem for {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{ROLE}}=engineer  {{OUTPUT}}=markdown table  {{CORPUS}}=

PRODUCE a categorized index. Choose 5-12 categories that genuinely fit this
domain (do not force a template onto it). For each entry give:

  | Name | Official docs | Developer/API portal | Source repo | SDKs & notable repos | Downloadable/offline docs | Notes |

Cover, where the domain has them:
- Commercial vendors and their product documentation
- Open-source projects and foundations
- The reference/standard implementation, if one exists
- Specifications and standards bodies
- Tooling, SDKs and client libraries
- Test, simulation and benchmarking infrastructure
- Registries, datasets or package ecosystems

RULES:
- Label every link [corpus] [primary] [secondary] [unverified] [gap].
- Include the dominant commercial players AND the open-source alternatives.
  A map with only one of those is not a map.
- Note recent ownership, rename or portal-move events as "verify currency:".
- End with: the 5-10 entries that matter most and why, and a "CORPUS GAPS"
  list of areas where good public documentation does not exist.
```

---

## P02 — Official Documentation Locator

```text
TASK: Find the authoritative documentation for {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LEVEL}}=  {{GOAL}}=

For each distinct product, project or implementation in scope, give:
- The canonical docs root (not a mirror, not a scraper site)
- The API/reference section specifically
- Version/release notes and the changelog
- Whether it is gated (login, account, NDA, paywall) — state this plainly
- The last-updated signal if you can see one

THEN:
- Flag any doc site that has MOVED in the last few years and give both old and new.
- Distinguish "the docs" from "the marketing site" — these are often confused and
  the marketing site is useless here.
- If a project's real documentation lives in its repo (README, /docs, wiki)
  rather than a doc site, say so and link the directory.

Label everything. Mark gated resources clearly — a link the user cannot open
is worse than no link.
```

---

## P03 — SDK, API and Client Library Navigator

```text
TASK: Find the SDKs, client libraries and API surfaces for {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LANG}}=  {{GOAL}}=

PRODUCE a table:
  | SDK / library | Language | Official or community | Repo | Docs | Maintained? | Notes |

RULES:
- Separate FIRST-PARTY (published by the vendor/project) from COMMUNITY. This
  distinction matters more than anything else here and is usually buried.
- State the maintenance signal honestly: last release, open issue count trend,
  or "appears unmaintained". If you cannot tell, say so.
- Identify the machine-readable interface definition if one exists — OpenAPI
  spec, protobuf/gRPC definitions, GraphQL schema, WSDL, JSON Schema, IDL — and
  link it directly. This is often more useful than any SDK.
- If SDKs are generated from a spec, say which spec, so the user can generate
  their own client for an unsupported language.
- Note auth model per API (API key, OAuth2, mTLS, token) in one phrase.
- Call out which SDK you would actually use for {{LANG}} and why.
```

---

## P04 — Reference Implementation Finder

```text
TASK: Identify the source code worth READING to understand {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LEVEL}}=advanced  {{LANG}}=

For each implementation give:
  - Repo URL and language
  - Its role: reference/canonical | production-grade | teaching/minimal |
    research prototype | historical-but-instructive
  - Approximate size and how approachable the codebase is
  - WHERE TO START — the specific file, directory or entry point. This is the
    single most valuable thing in this output; be concrete.
  - What design decision this implementation makes differently from the others

STRUCTURE the answer as a reading ladder:
  1. The minimal/teaching implementation — read this first, read it fully
  2. The production implementation — read selectively, guided
  3. The canonical/reference one — consult as the authority
  4. The interesting outlier — read for contrast

RULES:
- Prefer implementations with real tests; note where the test suite is, since
  tests are often the best spec.
- If an official conformance or compliance test suite exists, link it.
- Do not list a repo you cannot say something specific about.
```

---

## P05 — Standards and Specification Navigator

```text
TASK: Map the standards, specs and formal references governing {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LEVEL}}=

IDENTIFY the relevant standards bodies for this domain (examples across fields:
IETF/RFC, IEEE, ISO/IEC, W3C, ECMA, 3GPP, OASIS, NIST, ANSI, ITU, Khronos,
OMG, ASTM, IETF-adjacent consortia, or a project's own versioned spec).

PRODUCE a table:
  | Spec ID | Title | Status | Supersedes / superseded by | Free to read? | URL |

THEN give a READING ORDER, and be ruthless:
- The 3-5 specs that must actually be read
- The ones to skim for structure only
- The ones to treat purely as lookup references
- The OBSOLETE ones people still cite by mistake — this is high value, call them
  out explicitly with their replacement

ALSO:
- Note which standards are free vs paywalled, and any free-access programme
  (e.g. IEEE GET, free national-body access).
- Link any errata, bulk-download archive, or offline bundle.
- Identify where the written spec and real-world implementations diverge, if
  that is a known issue in this domain.
```

---

## P06 — Reading Order: Foundations (Basic)

```text
TASK: Build a grounded reading order to go from zero to competent in {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LEVEL}}=beginner  {{TIME}}=  {{CONSTRAINTS}}=free only

PRODUCE a sequenced path, not a pile of links. For each step:
  Step N — what you learn | the resource (title + URL) | time estimate |
           how you know you've got it

REQUIRED COMPONENTS, in this order of priority:
1. One free, complete, authoritative text — a book or full course, not a blog series
2. The 3-6 primary sources/specs that are actually readable at this level
   (most specs are not; pick only the ones that are)
3. Intuition-builders: visual explainers, well-regarded tutorials
4. HANDS-ON from step 2 onward. Name the exact tool, sample data or starter repo.
5. A self-check at each step: something the learner can DO to prove they got it

RULES:
- Hard-prefer free and openly accessible. Mark anything paid clearly.
- No step may be purely passive. Every one needs something to run, build or solve.
- Flag the common trap in this domain — the thing beginners learn wrong and have
  to unlearn later.
- State the prerequisites honestly. If this topic genuinely needs linear algebra
  or C or OS fundamentals first, say so and link that.
- Keep it to 8-12 steps. A 40-step path is a way of not making a decision.
```

---

## P07 — Reading Order: Depth (Advanced)

```text
TASK: Build an advanced path for someone already competent in {{TOPIC}} who wants
real depth.

KNOBS: {{TOPIC}}=  {{LEVEL}}=advanced  {{ROLE}}=  {{TIME}}=

ASSUME the basics are done. Do not re-teach them; state the assumed baseline in
two lines and move on.

STRUCTURE around four tracks, interleaved:
  A. PRIMARY SPECS — the normative text, read properly this time
  B. SOURCE CODE — the implementations to read, with specific entry points
  C. RESEARCH — the foundational papers and the current frontier
  D. BUILD — a substantial thing to implement that forces the knowledge in

For each item: why it earns the reader's time, and what they will be able to do
after it that they cannot do now.

ALSO INCLUDE:
- The unsolved problems / active debates in this domain, with where they are
  being argued (mailing list, working group, conference, issue tracker)
- The performance or correctness pitfalls that only show up at depth
- Where the documentation is known to be wrong, incomplete or aspirational
- The 2-3 people or groups whose output is worth following, and where they publish

RULES:
- Prefer open-access papers; mark paywalled ones and note if a preprint exists.
- The BUILD track is mandatory — advanced understanding without implementation
  is not advanced understanding.
```

---

## P08 — Academic and Courseware Finder

```text
TASK: Find university courses and open courseware for {{TOPIC}} with PUBLIC materials.

KNOBS: {{TOPIC}}=  {{LEVEL}}=  {{CONSTRAINTS}}=free only

PRODUCE two tables.

UNDERGRADUATE / FOUNDATIONAL:
  | Institution | Course code & title | What's public | Assignments? | URL |

GRADUATE / RESEARCH:
  | Institution | Course code & title | Reading list? | Projects? | URL |

"What's public" must be specific: lecture videos, slides, notes, problem sets,
assignment handouts, starter code, solutions, exams.

ALSO INCLUDE:
- Open courseware platforms relevant to this field (MIT OCW, NPTEL, Coursera and
  edX audit tracks, institution-specific archives)
- Courses whose ASSIGNMENTS are the main value — the ones where you build the
  thing. These are worth far more than lecture-only courses; rank them highest.
- Any publicly available starter-code repositories and test harnesses
- Professional/operator training from standards bodies, foundations or industry
  consortia in this field, if it exists and is free

RULES:
- Only list a course if the materials are genuinely reachable without enrolment.
  Verify this claim or mark it [unverified].
- Note archived vs currently-running offerings — archived is often better, since
  everything is already posted.
- Rank by material quality, not institution prestige.
```

---

## P09 — Research Paper Navigator

```text
TASK: Map the research literature for {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{LEVEL}}=research  {{GOAL}}=

PRODUCE:

1. VENUES — the conferences and journals that matter in this field, with open
   access status for each. Note which publish proceedings freely.

2. THE CANON — 5-10 foundational papers. For each: one sentence on the actual
   contribution (not the abstract), and why it still matters.

3. CURRENT FRONTIER — what is being actively worked on now, and where to watch.

4. SURVEYS — the best survey or systematization-of-knowledge paper, if one exists.
   Often the single highest-value starting point; put it first if so.

5. REPRODUCIBILITY — papers with public artifacts, code or datasets. Note any
   artifact-evaluation badge system this field uses.

6. PREPRINT NORMS — does this field use arXiv, bioRxiv, ePrint, or nothing?
   Where do papers appear before publication?

RULES:
- Mark open access vs paywalled. Where paywalled, note if an author preprint
  exists and is findable.
- Do not pad the canon. 5 genuinely foundational papers beats 20 well-cited ones.
- If a paper's result is known to have failed replication or been superseded,
  say so.
```

---

## P10 — Hands-On Environment Finder

```text
TASK: Find the fastest way to get hands-on with {{TOPIC}} today.

KNOBS: {{TOPIC}}=  {{CONSTRAINTS}}=no paid services, no special hardware  {{TIME}}=

PRODUCE, ordered by time-to-first-result:

1. ZERO-INSTALL — browser playgrounds, hosted sandboxes, free tiers, Colab-style
   notebooks. What exactly can you do, and what are the limits?
2. LOCAL — the single best local setup. Give the actual install commands and the
   first thing to run to confirm it works.
3. SIMULATED / EMULATED — where real hardware or scale is normally required, what
   simulates it, and importantly WHAT THE SIMULATION DOES NOT REPRODUCE.
4. REAL HARDWARE — only if genuinely needed. Cheapest viable path, with rough cost.

FOR EACH:
- Starter repo, template, or official tutorial that gets to a working result
- Sample/reference datasets or test fixtures
- The first exercise that actually teaches something, not "hello world"

ALSO:
- Official sandboxes or free developer tiers from vendors in this space
- Any free-for-education or free-for-open-source programme
- The known setup traps: the dependency, driver, version or licence issue that
  wastes everyone's first afternoon

RULES:
- Be concrete. "Install the toolchain" is useless; give the command.
- Be honest about what a simulator cannot teach you.
```

---

## P11 — Question Router

The one you'll use most. Point it at a specific problem.

```text
TASK: I need to do this: {{GOAL}}
      Domain: {{TOPIC}}     My level: {{LEVEL}}     Constraints: {{CONSTRAINTS}}

ROUTE ME. Do not explain the topic. Give me:

1. THE EXACT DOC PAGE — not the docs homepage, the specific page or section that
   answers this. If it is a spec, give the section number.
2. THE AUTHORITATIVE ANSWER in 3-5 lines, with the source it came from.
3. WORKING CODE OR CONFIG — the minimal snippet, from official docs or a real
   repo. Say where it came from.
4. THE GOTCHA — the thing that will bite me that the docs underplay or omit.
5. IF I'M ASKING THE WRONG QUESTION — say so, and give me the right one. Do this
   bluntly; it is the most useful thing you can do here.

RULES:
- Deep links only. A homepage link is a failure.
- If the answer differs by version, platform or vendor, say which you assumed and
  show the fork.
- If the official docs genuinely do not cover this, say [gap] and point at the
  issue tracker thread, mailing list post or source file that does.
- Three sources maximum. This is routing, not a literature review.
```

---

## P12 — Option Comparison

```text
TASK: Compare the real options for {{TOPIC}} so I can choose.

KNOBS: {{TOPIC}}=  {{GOAL}}=  {{CONSTRAINTS}}=  {{ROLE}}=

PRODUCE a comparison table whose columns are the dimensions that ACTUALLY drive
the decision in this domain. Derive the dimensions from the domain — do not use
a generic template. State in one line why you chose these dimensions.

Typical candidates, pick what fits: licence, governance model, maturity, release
cadence, performance envelope, platform support, API stability, ecosystem size,
operational burden, documentation quality, vendor lock-in, community health,
hiring pool, cost at scale.

THEN:
- A one-paragraph RECOMMENDATION for the stated {{GOAL}}, committing to an answer.
- The condition under which that recommendation flips.
- What each option is genuinely BEST at, including the ones you did not recommend.
- Documentation quality rated honestly per option — this is a real selection
  criterion and is almost never in vendor comparisons.
- Migration cost between options, if it is a realistic concern.

RULES:
- No fence-sitting. "It depends" is only acceptable with the dependency named.
- Separate measured facts from your judgement. Label judgement as judgement.
- Include at least one option the user probably has not considered.
- If one option is simply the default for good reasons, say so plainly rather
  than manufacturing a balanced comparison.
```

---

## P13 — Offline and Downloadable Documentation Finder

```text
TASK: Find downloadable, offline-usable documentation for {{TOPIC}}.

KNOBS: {{TOPIC}}=  {{OUTPUT}}=

FIND and link directly:
- Direct PDF / EPUB downloads of the official documentation
- Offline HTML bundles or doc archives
- Docs-as-code repositories that can be cloned and built locally (give the build
  command)
- Man pages, info pages, or in-tool help
- Bulk archives of the specs or standards
- Dash / Zeal / DevDocs docsets, if this domain has them
- Package-manager-installable doc packages

ALSO GIVE the generic tricks that apply to this domain's tooling, for example:
- Read the Docs projects: append /_/downloads/en/latest/pdf/ or /htmlzip/
- Sphinx/MkDocs projects: clone the repo, the docs/ tree is the site
- Vendor portals: locate the per-page PDF/download control
- `<tool> --help`, `man`, or built-in doc commands

RULES:
- Link the file directly where possible, and say the format and rough size.
- Verify the link actually serves the document rather than an HTML landing page.
  If you cannot verify, mark [unverified].
- Note licence/redistribution terms where the docs are not freely redistributable.
```

---

## P14 — Currency and Staleness Audit

```text
TASK: Tell me what has CHANGED in {{TOPIC}} that stale sources get wrong.

KNOBS: {{TOPIC}}=  {{GOAL}}=

PRODUCE:

1. MOVED OR RENAMED — doc portals, projects and products that changed location
   or name. Give old → new for each.
2. OWNERSHIP CHANGES — acquisitions, spin-offs, foundation donations, and what
   it meant for the docs and the licence.
3. DEPRECATED — APIs, versions, specs and tools that are superseded, with the
   replacement and whether the old one still works.
4. SUPERSEDED SPECS — standards replaced by newer ones that people still cite by
   the old number.
5. DEAD — projects that are unmaintained but still rank highly in search results
   and still look alive.
6. STILL TRUE — the things that have NOT changed and that recent sources
   sometimes wrongly claim are obsolete. This section is more useful than it
   sounds; hype churn creates false obsolescence.

RULES:
- Give dates or version numbers wherever possible.
- Mark anything you are not confident about as "verify currency:" rather than
  stating it.
- Note where the OLD documentation is still the better explanation even though
  the product moved on. This happens constantly and nobody writes it down.
```

---

## P15 — Gap Analysis

```text
TASK: Tell me where the documentation for {{TOPIC}} is MISSING or bad.

KNOBS: {{TOPIC}}=  {{ROLE}}=

IDENTIFY:
1. UNDOCUMENTED AREAS — real functionality with no usable public documentation.
2. TRIBAL KNOWLEDGE — what practitioners know that is not written down anywhere
   official. Point at where it does live: issue threads, mailing lists, conference
   talks, specific blog posts, a particular source file.
3. GATED — documentation that exists but is behind login, NDA, paywall or
   partner programme. Say what is behind the wall and whether an open substitute
   exists.
4. WRONG OR ASPIRATIONAL — docs that describe intended rather than actual
   behaviour. Note how to tell, usually by reading the source or the tests.
5. THE BEST UNOFFICIAL SOURCE — for each gap, the community resource that
   actually fills it, and how much to trust it.
6. READ THE SOURCE — where the code is genuinely the only real documentation.
   Give the specific file or directory.

RULES:
- Be specific. "The docs could be better" is not a finding.
- Distinguish "hard to find" from "does not exist" — they need different responses.
- If this domain's documentation is actually good, say so and stop. Do not
  manufacture criticism.
```

---

## P16 — Meta: generate a new navigator prompt

```text
TASK: Write a new prompt for this library.

I want a prompt that does: {{WHAT_IT_SHOULD_DO}}
Domain-agnostic, to be used across CS/STEM topics via a {{TOPIC}} placeholder.

MATCH THE HOUSE STYLE of P01-P15:
- Opens with "TASK:" in the imperative
- A KNOBS line using the universal knobs
- A PRODUCE / FIND / IDENTIFY block specifying exact output structure
- A RULES block with 3-5 constraints that keep the output honest
- Enforces the [corpus]/[primary]/[secondary]/[unverified]/[gap] labels
- Forbids invented URLs
- Demands specificity: deep links not homepages, file paths not repo names,
  commands not instructions

BEFORE WRITING, state in two sentences:
- What makes this task easy for a model to do badly
- The one rule that prevents that failure

Then output the prompt in a single fenced code block, ready to paste.
```

---

## Worked examples

Showing the same prompt across unrelated domains, to demonstrate it is genuinely generic.

| Prompt | `{{TOPIC}}` | What you get back |
|---|---|---|
| P01 Ecosystem Map | `enterprise networking` | Exactly the 18-category index in `networking-vendor-docs.md` |
| P01 Ecosystem Map | `embedded RTOS` | Zephyr, FreeRTOS, NuttX, ThreadX, vendor BSPs, toolchains, cert standards |
| P04 Reference Implementation | `regex engines` | Teaching: Thompson NFA writeups → RE2 → PCRE2 → Rust `regex`, with entry files |
| P04 Reference Implementation | `Raft consensus` | etcd/raft → hashicorp/raft → the TLA+ spec → MIT 6.824 lab as the build track |
| P05 Standards Navigator | `WebAssembly` | W3C core spec, WASI, component model, which are stable vs proposals |
| P05 Standards Navigator | `post-quantum crypto` | NIST FIPS 203/204/205, what they superseded, the free-to-read status |
| P08 Courseware Finder | `compilers` | Stanford CS143, Cornell CS6120, Nand2Tetris, ranked by assignment quality |
| P10 Hands-On Finder | `FPGA / HDL` | Verilator + Yosys locally, free vendor toolchains, cheapest real board |
| P11 Question Router | `ROS 2` + goal | The one page in the ROS 2 docs, the snippet, and the DDS gotcha |
| P13 Offline Docs | `PostgreSQL` | The official PDF/HTML bundles, `postgresql-doc` package, DevDocs set |
| P14 Currency Audit | `Python packaging` | setup.py → pyproject.toml, PEP churn, what still legitimately works |

---

## Choosing a prompt

| If you want to... | Use |
|---|---|
| Survey a whole field you don't know | **P01** |
| Find where the real docs live | **P02** |
| Build against something | **P03** |
| Understand how it actually works | **P04** |
| Settle an argument with the spec | **P05** |
| Learn it from scratch | **P06** |
| Go deeper than your job requires | **P07** |
| Find structured teaching material | **P08** |
| Enter the literature | **P09** |
| Start experimenting in the next hour | **P10** |
| Answer one specific question **(most used)** | **P11** |
| Choose between options | **P12** |
| Work on a plane | **P13** |
| Avoid acting on stale information | **P14** |
| Know what you won't find | **P15** |
| Extend this library | **P16** |

---

## Notes on why these work

- **The anti-invention rule is the whole game.** Rule 2 in the preamble plus the
  `[unverified]` label turns a model's weakest behaviour — confident fake URLs —
  into an explicit, scannable signal. Keep it even if you trim everything else.
- **"Deep links only, a homepage link is a failure"** (P11) changes output quality
  more than any other single line in this file.
- **Every prompt forces a commitment.** P12 forbids fence-sitting, P06 caps the
  path at 12 steps, P09 caps the canon at 10 papers. Ranking is the work; a long
  unranked list is the model avoiding it.
- **`[gap]` is a first-class output.** Prompts that cannot say "this doesn't exist"
  will manufacture something that doesn't exist.
- **P14 and P15 have no equivalent in normal prompting** and are where most of the
  practical value sits — stale docs and undocumented behaviour cause more lost time
  than missing links do.
- **Pair with a corpus when you have one.** Attaching a verified index and using
  `[corpus]` makes the output dramatically more reliable; without one these still
  work, but expect more `[unverified]`.
