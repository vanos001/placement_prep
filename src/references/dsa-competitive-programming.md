# DSA, Competitive Programming & Competitive Math Reference Library

This page is a verified index of primary sources for data structures and algorithms, contest programming, and the competition-math side of contest work: the judges themselves, their official documentation and APIs, the curricula and textbooks, tooling and judge infrastructure, editorial archives, free university course material, and open-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document, judge, or repository to open for the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Three domains in one index, because in practice they are one training pipeline: DSA is the subject matter, competitive programming is where it is tested under a clock, and competitive math is the part that no CP curriculum teaches properly.

The overlap contract: the [CS Theory](../cs-theory/README.md) chapters own complexity classes, computability, randomized algorithms and approximation as *concepts*; the [Mathematics](../mathematics/README.md) chapters own calculus, linear algebra, probability and statistics. The [DSA](../dsa/README.md), [Competitive Programming](../competitive-programming/README.md) and [Competitive Math](../competitive-math/README.md) chapters own the explanations. This page owns the **sources** — the documents, judges and repositories those chapters point out from.

**170 entries** across 9 categories, plus **72 education & reference resources** (37 basic / 35 advanced), **30 research sources**, **35 video resources** (24 channel entries in category 8 and 11 lecture playlists in the education track) and **3 conference sources**.

Every link HTTP-verified on **2026-10-09**.

> LeetCode, AoPS `community`, Reddit, Blind, InterviewQuery, SPOJ, `en.cppreference.com`, `dl.acm.org`, `epubs.siam.org` and ScienceDirect return 403 or 429 to automated clients while loading normally in a browser — all are kept with an explicit note. `a2oj.com`, `cftracker.net`, `livearchive.onlinejudge.org`, `icpcarchive.ecs.baylor.edu`, `algorithms.wtf`, `kt.cs.princeton.edu`, `datastructur.es`, `web.evanchen.us`, `code-drills.com` and `www.topcoder.com` are dead or no longer resolve; the working replacements are used and noted in Honest notes.

## Contents

- [1. Contest platforms & judges](#1-contest-platforms--judges) — 27
- [2. Curricula, textbooks & reference implementations](#2-curricula-textbooks--reference-implementations) — 14
- [3. Competitive math](#3-competitive-math) — 21
- [4. Tooling, judge infrastructure & analytics](#4-tooling-judge-infrastructure--analytics) — 18
- [5. Interview & online-assessment platforms](#5-interview--online-assessment-platforms) — 21
- [6. Editorials & solution archives](#6-editorials--solution-archives) — 10
- [7. University & MOOC course material](#7-university--mooc-course-material) — 18
- [8. Community, video & aggregators](#8-community-video--aggregators) — 35
- [9. Repositories & awesome lists](#9-repositories--awesome-lists) — 6
- [Education & reference implementations](#education--reference-implementations) — 72 (37 basic / 35 advanced)
- [Research papers & open-access literature](#research-papers--open-access-literature) — 30
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 3


## 1. Contest platforms & judges

### Codeforces

- **Docs:** [codeforces.com/problemset](https://codeforces.com/problemset) · [tag + rating filters](https://codeforces.com/problemset?tags=number+theory) · [catalog](https://codeforces.com/catalog) · [edu/courses](https://codeforces.com/edu/courses)
- **Developer / API:** [codeforces.com/apiHelp](https://codeforces.com/apiHelp)
- **SDKs & repos:** [contests](https://codeforces.com/contests) · [gyms](https://codeforces.com/gyms) · [groups](https://codeforces.com/groups) · [acmsguru](https://codeforces.com/problemsets/acmsguru)
- **Downloadable / offline:** Nothing official — snapshot the blog posts you depend on
- *Note:* The centre of gravity for CP. Largest tagged problem bank, a rating system people actually optimise for, and `/edu/courses` is the only official course system on any judge. Editorials come from the setters, in the blog.

### AtCoder

- **Docs:** [atcoder.jp/contests](https://atcoder.jp/contests/) · [archive](https://atcoder.jp/contests/archive?ratedTypeStart%5B0%5D=1)
- **SDKs & repos:** [Beginners Selection](https://atcoder.jp/contests/abs) · [Typical 90](https://atcoder.jp/contests/typical90) · [AtCoder Library docs](https://atcoder.github.io/ac-library/production/document_en/)
- **Downloadable / offline:** Contest statements and editorials stay online indefinitely
- *Note:* The cleanest problem statements in CP and the best difficulty calibration. ABC A–D is the correct ramp below Codeforces 1600; ARC/AGC take over after.

### LeetCode

- **Docs:** [leetcode.com/problemset](https://leetcode.com/problemset/) · [study plans](https://leetcode.com/studyplan/top-interview-150/) · [explore](https://leetcode.com/explore/) · [contests](https://leetcode.com/contest/)
- **SDKs & repos:** [official solutions tab](https://leetcode.com/problems/two-sum/solutions/) · [tag pages](https://leetcode.com/tag/number-theory) · [/tag/combinatorics](https://leetcode.com/tag/combinatorics) · [/tag/math](https://leetcode.com/tag/math)
- **Downloadable / offline:** None
- *Note:* A different sport from CP — pattern recall in 25 minutes, no I/O tuning, no math depth. Paywalled parts: company tags and much of the solutions content. ⚠ URL shapes drift between redesigns; `leetcode.com` 403s automated clients.

### CSES Problem Set

- **Docs:** [cses.fi/problemset](https://cses.fi/problemset/) · [list view](https://cses.fi/problemset/list/)
- **Downloadable / offline:** [Competitive Programmer's Handbook (PDF)](https://cses.fi/book/book.pdf) — the paired textbook, free
- *Note:* ~300 problems, no filler, ordered by topic. The de-facto "am I ready for CF 1600" benchmark, and the only problem set with a matching free textbook.

### USACO

- **Docs:** [usaco.org](https://usaco.org/) · [training pages](https://usaco.org/index.php?page=training)
- **SDKs & repos:** [past contests](https://usaco.org/index.php?page=contests)
- **Downloadable / offline:** Every past contest with official solutions
- *Note:* The official US olympiad ladder, and still the best difficulty ramp anywhere. ⚠ The legacy training pages are mid-migration: new usaco.org accounts are not recognised there and a separate legacy account is needed.

### CodeChef

- **Docs:** [codechef.com/practice](https://www.codechef.com/practice/) · [contests](https://www.codechef.com/contests) · [learn](https://www.codechef.com/learn)
- **SDKs & repos:** [discuss.codechef.com](https://discuss.codechef.com/) — editorials and Q&A · [practice root](https://www.codechef.com/practice)
- **Downloadable / offline:** Practice problems persist; editorials live on Discuss
- *Note:* India-heavy and underrated: the 10-day Long Challenge format teaches persistence and partial scoring in a way two-hour contests cannot. Its free `/learn` track is a genuine structured DSA course.

### DMOJ

- **Docs:** [dmoj.ca/problems](https://dmoj.ca/problems/)
- **Source:** [github.com/DMOJ/online-judge](https://github.com/DMOJ/online-judge)
- **Downloadable / offline:** Judge server is open source — self-hostable
- *Note:* The only large judge with an *editorial filter* in problem search. Carries CCC/CCO/IOI/COCI and a huge Canadian contest archive.

### Kattis

- **Docs:** [open.kattis.com/problems](https://open.kattis.com/problems)
- **SDKs & repos:** Problem archive tags; course-integration features used by many universities
- *Note:* Huge bank, clean UI, and the judge most university algorithms courses actually use. Good for volume, thin on editorials.

### ICPC

- **Docs:** [icpc.global](https://icpc.global/)
- **SDKs & repos:** [icpcarchive.github.io](https://icpcarchive.github.io/) — community finals/regional collection
- **Downloadable / offline:** Problem sets via the archive and Codeforces gyms
- *Note:* The governing body: rules, regional structure, World Finals. For problems, use the archive or CF gyms — see Honest notes on the Live Archive.

### IOI

- **Docs:** [ioinformatics.org](https://ioinformatics.org/) · [Syllabus (IOI 2025 PDF)](https://ioinformatics.org/files/ioi-syllabus-2025.pdf) · [syllabus page](https://ioinformatics.org/page/syllabus/12)
- **SDKs & repos:** [Olympiads in Informatics journal](https://ioinformatics.org/journal/)
- **Downloadable / offline:** Syllabus PDF; contest PDFs by year, e.g. [ioi2011.pdf](https://ioinformatics.org/files/ioi2011.pdf)
- *Note:* Read the Syllabus once. It is the only authoritative statement of what "competitive DSA" is scoped to include — and it is much narrower than most prep plans assume.

### oj.uz

- **Docs:** [oj.uz](https://oj.uz/)
- **SDKs & repos:** [IOI 2011 Race](https://oj.uz/problem/view/IOI11_race) · [IOI 2016 Aliens](https://oj.uz/problem/view/IOI16_aliens)
- *Note:* The best English-language mirror of national olympiad and IOI problems, with subtask scoring preserved. Where you go when you want olympiad-style problems without Chinese or Polish.

### QOJ

- **Docs:** [qoj.ac](https://qoj.ac/)
- *Note:* Modern judge with a large gym of OI/ICPC problem sets. ⚠ Cloudflare-gated; automated checkers get an interstitial rather than the page.

### SPOJ

- **Docs:** [spoj.com/problems/classical](https://www.spoj.com/problems/classical/)
- **Downloadable / offline:** None
- *Note:* Enormous and old. Excellent for drilling a single technique to death; weak statements and uneven test data. ⚠ Canonical host is `spoj.com` — `spoj.pl` is a dead end, and the site 403s automated clients on some paths.

### UVa Online Judge

- **Docs:** [onlinejudge.org](https://onlinejudge.org/)
- **SDKs & repos:** [uHunt](https://uhunt.onlinejudge.org/) — topic ladders, CP-book mapping and a virtual contest generator
- **Downloadable / offline:** Problem PDFs by volume; uHunt keeps a full catalogue
- *Note:* Thousands of classic problems, weak statements by modern standards. uHunt is the reason to bother: it gives UVa the topic-ladder structure the judge itself never had.

### Timus

- **Docs:** [acm.timus.ru](https://acm.timus.ru/) · mirror [timus.online](https://timus.online)
- *Note:* A classic hard bank with deliberately unforgiving I/O. Good training for "the statement is one sentence and the edge cases are yours to find".

### ACMP

- **Docs:** [acmp.ru](https://acmp.ru/)
- *Note:* Russian olympiad-style archive, unusually good for high-volume beginner practice with tight time limits.

### beecrowd (URI)

- **Docs:** [judge.beecrowd.com/en](https://judge.beecrowd.com/en)
- *Note:* Large beginner-friendly bank, strong in LATAM, English/Portuguese statements. Best used as warm-up volume, not for hard problems.

### Luogu

- **Docs:** [luogu.com.cn](https://www.luogu.com.cn/)
- *Note:* The largest problem set anywhere, Chinese statements. Worth it for the solution discussions if you can read them or use machine translation; otherwise a last resort.

### HDU

- **Docs:** [acm.hdu.edu.cn](https://acm.hdu.edu.cn/)
- *Note:* Massive Chinese archive with weak editorial culture. Use for volume on a specific tag.

### Nowcoder

- **Docs:** [nowcoder.com](https://www.nowcoder.com/)
- *Note:* Chinese contests plus campus/OA-style problem sets — useful if you want to see how Chinese placement exams are shaped.

### LightOJ

- **Docs:** [lightoj.com](https://lightoj.com/)
- *Note:* Topic-categorised bank, popular in South Asia. Some content sits behind an account.

### e-olymp

- **Docs:** [eolymp.com/en](https://www.eolymp.com/en/)
- *Note:* Multi-language training sets and school-level olympiad material. Broad, shallow.

### Toph

- **Docs:** [toph.co](https://toph.co/)
- *Note:* Bangladeshi judge with a genuinely good problem set and clean editorial support. ⚠ Returns 405 to automated HEAD checks; loads in a browser.

### CS Academy

- **Docs:** [csacademy.com](https://csacademy.com/)
- *Note:* Clean archive plus its own rounds. Small but well-curated; a nice change of pace.

### VJudge

- **Docs:** [vjudge.net/problem](https://vjudge.net/problem) · [vjudge.net/contest](https://vjudge.net/contest)
- *Note:* Not a judge — a proxy. It pulls problems from other OJs so you can host your own virtual or mashup contest with teammates. Indispensable for team practice, useless as a source of truth.

### Library Checker

- **Docs:** [judge.yosupo.jp](https://judge.yosupo.jp/)
- **Source:** [github.com/yosupo06/library-checker-problems](https://github.com/yosupo06/library-checker-problems)
- **SDKs & repos:** e.g. [range_chmin_chmax_add_range_sum](https://judge.yosupo.jp/problem/range_chmin_chmax_add_range_sum)
- *Note:* Submit your own segtree, NTT, flow or matroid-intersection implementation and have it machine-verified against ~200 known-hard cases. The fastest way to find the bug in a library you trusted.

### Project Euler

- **Docs:** [projecteuler.net/archives](https://projecteuler.net/archives) · [recent](https://projecteuler.net/recent)
- **Downloadable / offline:** Problems are permanent; solutions are yours
- *Note:* 1000+ problems that are half number theory, half implementation. The bridge between proofy math and code, and the strongest argument for learning modular arithmetic properly.


## 2. Curricula, textbooks & reference implementations

### USACO Guide

- **Docs:** [usaco.guide](https://usaco.guide/) · [bronze](https://usaco.guide/bronze) · [silver](https://usaco.guide/silver) · [gold](https://usaco.guide/gold) · [plat](https://usaco.guide/plat) · [adv](https://usaco.guide/adv)
- **Source:** [github.com/usaco-guide/usaco-guide](https://github.com/usaco-guide/usaco-guide)
- **SDKs & repos:** [plat/centroid](https://usaco.guide/plat/centroid) · [plat/dp-sos](https://usaco.guide/plat/dp-sos) · [adv/lagrange](https://usaco.guide/adv/lagrange)
- **Downloadable / offline:** Git clone; each module is Markdown with its own problem list
- *Note:* The fastest "I can code" → contest-ready path, and the only CP curriculum with per-division entry points. Start at your division, not the homepage. Platinum and `/adv` are thinner than Bronze–Gold.

### Competitive Programmer's Handbook

- **Docs:** [cses.fi/book/index.php](https://cses.fi/book/index.php)
- **Downloadable / offline:** [book.pdf](https://cses.fi/book/book.pdf) — free, complete draft
- *Note:* The one coherent free CP textbook. Chapters 21–24 (number theory, combinatorics, matrices, probability) are the only free CP-math treatment sized right. The published Springer version (*Guide to Competitive Programming*) adds chapters if you want more.

### CP3 book site (Halim & Halim)

- **Docs:** [cpbook.net](https://cpbook.net/)
- **Downloadable / offline:** Book is paid; the site is free
- *Note:* The book is the standard reference for problem *taxonomy*; the site's topic index is free and is the best "what should I learn next" map after USACO Guide.

### cp-algorithms

- **Docs:** [cp-algorithms.com](https://cp-algorithms.com/) · [topic index](https://cp-algorithms.com/index.html)
- **Source:** [github.com/cp-algorithms/cp-algorithms](https://github.com/cp-algorithms/cp-algorithms)
- **SDKs & repos:** [segment_tree](https://cp-algorithms.com/data_structures/segment_tree.html) · [centroid decomposition](https://cp-algorithms.com/graph/centroid_decomposition.html) · [min_cost_flow](https://cp-algorithms.com/graph/min_cost_flow.html) · [convex_hull_trick](https://cp-algorithms.com/geometry/convex_hull_trick.html) · [FFT](https://cp-algorithms.com/algebra/fft.html) · [euclid](https://cp-algorithms.com/algebra/euclid-algorithm.html) · [module-inverse](https://cp-algorithms.com/algebra/module-inverse.html) · [phi-function](https://cp-algorithms.com/algebra/phi-function.html) · [primitive-root](https://cp-algorithms.com/algebra/primitive-root.html) · [continued fractions](https://cp-algorithms.com/algebra/continued-fractions.html)
- **Downloadable / offline:** Static site; clone the repo
- *Note:* The de-facto CP reference, and the successor to e-maxx — the project was renamed, so links to `e-maxx.ru` or `e-maxx-eng.github.io` are stale. Code-first and correct; weak on *why*.

### IOI Syllabus

- **Docs:** [ioinformatics.org/page/syllabus/12](https://ioinformatics.org/page/syllabus/12)
- **Downloadable / offline:** [ioi-syllabus-2025.pdf](https://ioinformatics.org/files/ioi-syllabus-2025.pdf)
- *Note:* The authoritative scope document for olympiad-level DSA, maintained by the ISC. Cross-check your prep plan against it: it excludes calculus, statistics and combinatorial game theory outright.

### Algorithms — Jeff Erickson

- **Docs:** [jeffe.cs.illinois.edu/teaching/algorithms](https://jeffe.cs.illinois.edu/teaching/algorithms/)
- **Downloadable / offline:** [Algorithms-JeffE.pdf](https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf) — free, CC BY 4.0, 472pp
- **Source:** [github.com/jeffgerickson/algorithms](https://github.com/jeffgerickson/algorithms) — errata and source
- *Note:* The best free *rigorous* algorithms textbook: recursion, backtracking, DP, greedy, graphs, flows, NP-hardness — plus hundreds of pages of extra lecture notes. Assumes discrete math and basic DS; not a first book. ⚠ The `algorithms.wtf` shortcut is dead.

### Open Data Structures

- **Docs:** [opendatastructures.org](https://opendatastructures.org/)
- **Downloadable / offline:** Free PDF by chapter; C++/Java/Python editions
- *Note:* Free, complete, multi-language, and better written than most paid data-structure books. The proofs are short and the code is real.

### Algorithms, 4th Edition

- **Docs:** [algs4.cs.princeton.edu](https://algs4.cs.princeton.edu/)
- **Source:** [github.com/kevin-wayne/algs4](https://github.com/kevin-wayne/algs4) · [code](https://algs4.cs.princeton.edu/code/)
- **Downloadable / offline:** All code and booksite materials
- *Note:* Sedgewick/Wayne, used as a textbook in several IOI training camps. The booksite ships every implementation and the test data.

### Algorithm Design (Kleinberg & Tardos)

- **Docs:** [cs.princeton.edu/~wayne/kleinberg-tardos](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/)
- **Downloadable / offline:** Slides and errata free; book is paid
- *Note:* The clearest writing on algorithm *design* technique, with the best network-flow chapter of any textbook. ⚠ `kt.cs.princeton.edu` is dead — this is the working official page.

### The Algorithm Design Manual (Skiena)

- **Docs:** [algorist.com](https://www.algorist.com/)
- **Downloadable / offline:** Lecture videos and resources free; book is paid
- *Note:* Skiena's "catalogue of algorithmic problems" is the best shortcut in existence for the question "what standard problem is this, actually?".

### KACTL

- **Source:** [github.com/kth-competitive-programming/kactl](https://github.com/kth-competitive-programming/kactl)
- **SDKs & repos:** [LineContainer.h](https://github.com/kth-competitive-programming/kactl/blob/main/content/data-structures/LineContainer.h) · [LinearRecurrence.h](https://github.com/kth-competitive-programming/kactl/blob/main/content/numerical/LinearRecurrence.h)
- **Downloadable / offline:** Print it — designed as a physical contest reference card
- *Note:* ~25 pages that cover a World Finals toolkit. Read it as a checklist of things you should be able to implement.

### AtCoder Library

- **Docs:** [atcoder.github.io/ac-library/production/document_en](https://atcoder.github.io/ac-library/production/document_en/)
- **Source:** [github.com/atcoder/ac-library](https://github.com/atcoder/ac-library) · [ac-library-rs](https://github.com/rust-lang-ja/ac-library-rs)
- **SDKs & repos:** [AtCoder Library Practice Contest](https://atcoder.jp/contests/practice2)
- **Downloadable / offline:** Header-only; vendor it into your template
- *Note:* Official, maintained, and the reference implementation the whole community converges on. Read it before reimplementing a segment tree or modint, then beat it.

### OI Wiki

- **Docs:** [oi-wiki.org](https://oi-wiki.org/)
- *Note:* Deep, continuously updated, Chinese-first. ⚠ The English mirror at `oi-wiki.org/en/` 404s; use browser translation or USACO Guide instead.

### PEG Wiki

- **Docs:** [wcipeg.com/wiki](https://wcipeg.com/wiki/)
- **SDKs & repos:** [Convex hull trick](https://wcipeg.com/wiki/Convex_hull_trick)
- *Note:* Older, unglamorous, and genuinely deep on CP-specific tricks. Better than Wikipedia for the things that only exist in contests.


## 3. Competitive math

### IMO official

- **Docs:** [imo-official.org](https://www.imo-official.org/) · [problems.aspx](https://www.imo-official.org/problems.aspx) · [results.aspx](https://www.imo-official.org/results.aspx)
- **Downloadable / offline:** Every IMO problem and result, 1959–present
- *Note:* The primary archive. Use it rather than a scraper; the results page lets you calibrate how hard a given year's P1 versus P3 actually was.

### AoPS Wiki

- **Docs:** [artofproblemsolving.com/wiki](https://artofproblemsolving.com/wiki/index.php)
- **Downloadable / offline:** MediaWiki — printable by page
- *Note:* The reference corpus for competition math: theory pages plus per-year AMC/AIME/IMO/USAMO solutions. Free, community-maintained, uneven depth.

### AoPS Community

- **Docs:** [artofproblemsolving.com/community](https://artofproblemsolving.com/community)
- **SDKs & repos:** [IMO forum (c6)](https://artofproblemsolving.com/community/c6) · [practice contests](https://artofproblemsolving.com/contests/practice)
- *Note:* Where hard olympiad solutions actually get explained, usually three different ways, within a day of the contest. ⚠ 403s automated clients.

### AoPS Alcumus

- **Docs:** [artofproblemsolving.com/alcumus](https://artofproblemsolving.com/alcumus)
- *Note:* Free adaptive math trainer with topic targeting. The single best free drill tool in this category — it does spaced repetition of *problem types*, which is exactly what contest training needs.

### TU Eindhoven IMO collection

- **Docs:** [olympiads.win.tue.nl/imo](https://olympiads.win.tue.nl/imo/)
- **Downloadable / offline:** Problem and shortlist PDFs by year
- *Note:* One of the few organised collections of IMO **shortlists**, which — not the contests themselves — are the real training set at IMO level.

### Kalva

- **Docs:** [prase.cz/kalva](https://prase.cz/kalva/) · mirror [mks.mff.cuni.cz/kalva](https://mks.mff.cuni.cz/kalva/)
- *Note:* John Scholes' classic archive: IMO, USAMO and national olympiads with solutions alongside statements. Two independent mirrors exist for a reason — keep both.

### Evan Chen

- **Docs:** [web.evanchen.cc](https://web.evanchen.cc/) · [olympiad](https://web.evanchen.cc/olympiad.html) · [problem sets](https://web.evanchen.cc/problems.html) · [mock AIME](https://web.evanchen.cc/mockaime.html) · [recommendations](https://web.evanchen.cc/recommend.html)
- **Downloadable / offline:** [Napkin](https://web.evanchen.cc/napkin.html) — free PDF, a fast higher-math cheat-sheet
- *Note:* The best free olympiad-math training index on the internet, from an IMO gold medallist. `Napkin` is the fastest route from "I know contest math" to "I can read the language real mathematicians use". ⚠ `web.evanchen.us` no longer resolves.

### Yufei Zhao

- **Docs:** [yufeizhao.com](https://yufeizhao.com/)
- **Downloadable / offline:** Lecture notes and handouts as PDFs
- *Note:* MIT faculty and a former olympiad medallist; his handouts (combinatorics, number theory, graph theory) are short, modern and pitched exactly at the olympiad/research boundary.

### MAA — AMC

- **Docs:** [maa.org/student-programs/amc](https://maa.org/student-programs/amc/) · [amcreg](https://maa.org/amcreg/)
- *Note:* Official home of AMC 8/10/12 — the entry rung of the US ladder. ⚠ Old `maa.org/math-competitions/*` paths now 404; these are the current ones.

### MAA — invitational competitions

- **Docs:** [maa.org/maa-invitational-competitions](https://maa.org/maa-invitational-competitions/)
- *Note:* AIME, USAMO and USAJMO — the invitation-only tiers. Past papers here, discussion on AoPS.

### MAA — Putnam archive

- **Docs:** [maa.org/maa-putnam-archive](https://maa.org/maa-putnam-archive/) · [maa.org/putnam](https://maa.org/putnam/)
- **Downloadable / offline:** Official problems **and** solutions by year
- *Note:* This is the official archive — the one that used to be awkward to find. The premier undergraduate exam in North America; median score is frequently zero, which tells you how to use it.

### Kedlaya's Putnam archive

- **Docs:** [kskedlaya.org/putnam-archive](https://kskedlaya.org/putnam-archive/)
- *Note:* Long-standing mirror covering older years, results and winner lists the official archive does not surface as conveniently. Keep it alongside the MAA one.

### USAMTS

- **Docs:** [usamts.org](http://www.usamts.org/)
- *Note:* Free, proof-graded, by-mail US contest with generous deadlines. Rare and valuable: full-solution grading by a human is the only way to learn to write proofs.

### UKMT

- **Docs:** [ukmt.org.uk](https://www.ukmt.org.uk/)
- *Note:* The UK ladder (Junior/Senior/BMO). Its mentoring scheme and past papers are high quality and less saturated than AoPS material.

### IMC

- **Docs:** [imc-math.org.uk](https://www.imc-math.org.uk/)
- *Note:* International Mathematics Competition for University Students. Problems and solutions free; a good step up from olympiad geometry into analysis-flavoured contest math.

### AwesomeMath

- **Docs:** [awesomemath.org](https://www.awesomemath.org/)
- **Downloadable / offline:** Free sample problems and course outlines
- *Note:* Summer camps plus a book line by olympiad coaches, several of them former IMO team leaders. The books are the reason it is indexed here — they sit between AoPS's introductory texts and research-level problem books.

### HBCSE Olympiads (India)

- **Docs:** [olympiads.hbcse.tifr.res.in](https://olympiads.hbcse.tifr.res.in)
- *Note:* The official Indian olympiad programme: PRMO, RMO, INMO and the IMOTC. If you are in India this is the actual pipeline, and its past papers are the realistic difficulty reference — not AoPS highlight reels.

### MATHCOUNTS

- **Docs:** [mathcounts.org](https://www.mathcounts.org/)
- *Note:* The US middle-school competition pipeline. Only relevant if you are starting from a weak math base — but if you are, it is the correct rung to start on rather than jumping to AMC 10.

### OEIS

- **Docs:** [oeis.org](https://oeis.org/)
- **SDKs & repos:** e.g. [A002188](https://oeis.org/A002188)
- *Note:* Turns "1, 2, 6, 22, 101…" into a closed form, recurrence, generating function and citations. On CP problems with a combinatorial flavour this is close to an unfair advantage.

### generatingfunctionology (Wilf)

- **Docs:** [Penn Online Books record](https://onlinebooks.library.upenn.edu/webbin/book/lookupid?key=olbp31833) — stable catalogue entry with the download link
- **Downloadable / offline:** Free PDF, 2nd edition, from the author's publisher-sanctioned copy
- *Note:* The best single source for generating functions once combinatorics starts hurting; the enumerative tool CP counting problems quietly assume. ⚠ I could not confirm a durable direct PDF URL — the UPenn pages block automated clients. Use the catalogue record above, or search `Wilf generatingfunctionology pdf site:upenn.edu`.

### Shoup — A Computational Introduction to Number Theory and Algebra

- **Docs:** [shoup.net/ntb](https://shoup.net/ntb/)
- **Downloadable / offline:** [ntb-v2.pdf](https://shoup.net/ntb/ntb-v2.pdf) — free, author-hosted
- *Note:* The only number-theory-and-algebra book written for people who will implement the algorithms. Free from the author, rigorous, and it covers modular arithmetic properly — which almost no CP resource does.


## 4. Tooling, judge infrastructure & analytics

### clist.by

- **Docs:** [clist.by](https://clist.by/) · [problems](https://clist.by/problems/)
- **Developer / API:** [clist.by/api/v4/doc](https://clist.by/api/v4/doc/)
- *Note:* The only reliable single calendar for Codeforces, AtCoder, CodeChef and ICPC mirrors, in your timezone, plus a cross-judge problem search. ⚠ `clist.by/api/` (bare) 404s — the docs path above is the working one.

### Codeforces API

- **Developer / API:** [codeforces.com/apiHelp](https://codeforces.com/apiHelp)
- **SDKs & repos:** e.g. `api/problemset.problems`, `api/user.rating`, `api/user.info`
- *Note:* Unofficial and undocumented in places, but stable for a decade. The only way to build your own rating tracker or problem recommender without scraping HTML.

### AtCoder Problems (kenkoooo)

- **Docs:** [kenkoooo.com/atcoder](https://kenkoooo.com/atcoder/)
- **Source:** [github.com/kenkoooo/AtCoderProblems](https://github.com/kenkoooo/AtCoderProblems)
- *Note:* Difficulty-coloured AtCoder problem browser, progress tracking and virtual-contest generation. The single best per-judge analytics tool in CP.

### online-judge-tools/oj

- **Source:** [github.com/online-judge-tools/oj](https://github.com/online-judge-tools/oj)
- **SDKs & repos:** Sibling [verification-helper](https://github.com/online-judge-tools/verification-helper)
- *Note:* Submit, download samples and run local tests from the command line across Codeforces, AtCoder, AOJ and more. Once you use it, browser submission feels like a regression.

### cf-tool

- **Source:** [github.com/xalanq/cf-tool](https://github.com/xalanq/cf-tool)
- *Note:* Codeforces from the terminal: parse, generate, submit, watch verdicts. Pairs with competitive-companion.

### competitive-companion

- **Source:** [github.com/jmerle/competitive-companion](https://github.com/jmerle/competitive-companion)
- *Note:* Browser extension that hands a problem — statement, samples, limits — straight to your editor. The missing link between reading a problem and writing code.

### atcoder-cli

- **Source:** [github.com/Tatamo/atcoder-cli](https://github.com/Tatamo/atcoder-cli) · [kyuridenamida/atcoder-tools](https://github.com/kyuridenamida/atcoder-tools)
- *Note:* Scaffold and submit AtCoder contests locally. Two tools, same job, different ergonomics — try both.

### testlib

- **Source:** [github.com/MikeMirzayanov/testlib](https://github.com/MikeMirzayanov/testlib)
- *Note:* `testlib.h`, by Codeforces' author — the standard checker/generator/validator library. If you ever host a contest or generate stress tests, this is what the ecosystem uses.

### Library Checker problems

- **Source:** [github.com/yosupo06/library-checker-problems](https://github.com/yosupo06/library-checker-problems)
- **Docs:** [judge.yosupo.jp](https://judge.yosupo.jp/)
- *Note:* A ~200-problem verification suite for algorithm libraries. Wire it into CI and your template stops rotting.

### DMOJ judge server

- **Source:** [github.com/DMOJ/online-judge](https://github.com/DMOJ/online-judge) · [hydro-dev/Hydro](https://github.com/hydro-dev/Hydro)
- *Note:* Two production-quality open-source judges. Self-host one if you want full control over time limits, checkers and scoring — or just to understand what a judge actually does.

### Compiler Explorer

- **Docs:** [godbolt.org](https://godbolt.org)
- *Note:* Read the assembly your solution actually compiles to. The fastest cure for cargo-cult "optimisation" in hot loops.

### cppreference

- **Docs:** [en.cppreference.com/w](https://en.cppreference.com/w/)
- **Downloadable / offline:** Offline archive builds available
- *Note:* The C++ standard's readable form. ⚠ 403s automated clients; loads fine in a browser.

### StopStalk

- **Docs:** [stopstalk.com](https://stopstalk.com/)
- *Note:* Cross-judge activity tracker, popular in India: aggregates solves and ratings across Codeforces, CodeChef, SPOJ, HackerRank and more.

### Nayuki — fast Fibonacci algorithms

- **Docs:** [nayuki.io/page/fast-fibonacci-algorithms](https://www.nayuki.io/page/fast-fibonacci-algorithms)
- *Note:* The clearest treatment of fast doubling and matrix methods for linear recurrences, with proofs and implementations. The reference to reach for before implementing Berlekamp–Massey or Bostan–Mori.

### Chess Programming Wiki

- **Docs:** [chessprogramming.org](https://www.chessprogramming.org/Transposition_Table) · [Zobrist hashing](https://www.chessprogramming.org/Zobrist_Hashing) · [MCTS](https://www.chessprogramming.org/Monte-Carlo_Tree_Search)
- *Note:* Not a chess resource in this context — it is the best free writing on hashing, transposition tables, bitboards and adversarial search anywhere. Directly transferable to CP game and search problems.

### Apache DataSketches

- **Docs:** [datasketches.apache.org](https://datasketches.apache.org/docs/Theta/ThetaSketches.html)
- **Source:** [github.com/apache/datasketches-cpp](https://github.com/apache/datasketches-cpp)
- *Note:* Production-grade probabilistic data structures (HyperLogLog, theta sketches, quantiles). Read it when CP's toy sketches meet real cardinality-estimation requirements.

### Sorting implementations

- **Source:** [orlp/pdqsort](https://github.com/orlp/pdqsort) · [boostorg/sort](https://github.com/boostorg/sort) · [cmuparlay/pbbsbench](https://github.com/cmuparlay/pbbsbench)
- *Note:* pdqsort is what libstdc++ and Rust now ship; PBBS is the parallel-algorithms benchmark suite. The fastest way to learn what "fast sort" means after 2015. See the [pdqsort paper](https://arxiv.org/abs/2106.05123).

### Complexity Zoo

- **Docs:** [complexityzoo.net](https://complexityzoo.net/Complexity_Zoo:N)
- *Note:* The catalogue of complexity classes. Use it to stop hand-waving about NP-hardness in interviews.


## 5. Interview & online-assessment platforms

### LeetCode (company / premium)

- **Docs:** [leetcode.com/company](https://leetcode.com/company/)
- *Note:* The company-tag filters are **Premium**. Most "company-wise preparation" advice silently assumes you have it; if you do not, the free substitutes below are the fallback.

### HackerRank

- **Docs:** [hackerrank.com/domains/algorithms](https://www.hackerrank.com/domains/algorithms) · [Interview Preparation Kit](https://www.hackerrank.com/interview/interview-preparation-kit)
- *Note:* Clean statements and easy filters; a good warm-up venue. ⚠ The contest product has been shrinking — ProjectEuler+ still loads but is login-gated.

### CodeSignal

- **Docs:** [app.codesignal.com/arcade](https://app.codesignal.com/arcade)
- *Note:* CodeSignal is a real OA vendor, and Arcade mirrors its problem style. Practising in the vendor's idiom is worth more than it sounds.

### Codility

- **Docs:** [codility.com/programmers/lessons](https://codility.com/programmers/lessons/)
- *Note:* Another OA vendor, and their own free lessons are the best preparation for their format.

### CoderPad

- **Docs:** [coderpad.io](https://coderpad.io/)
- *Note:* The live-coding environment many companies conduct interviews in. Practise in the actual tool — the muscle memory matters when someone is watching.

### Pramp

- **Docs:** [pramp.com](https://www.pramp.com/)
- *Note:* **Free peer mock interviews.** The highest-value free item in this category: speaking practice is the skill nobody drills and every candidate fails.

### interviewing.io

- **Docs:** [interviewing.io](https://interviewing.io/)
- *Note:* Mock interviews with real interviewers, anonymised until the end. Paid beyond the free content.

### Exponent

- **Docs:** [tryexponent.com](https://www.tryexponent.com/)
- *Note:* SWE/PM/EM tracks with structured mocks. Limited free tier.

### Hello Interview

- **Docs:** [hellointerview.com](https://www.hellointerview.com/)
- *Note:* Currently the best free structured behavioural *and* coding prep, with a genuinely usable question bank and frameworks.

### Blind

- **Docs:** [teamblind.com](https://www.teamblind.com/)
- *Note:* The largest crowdsourced bank of real OA and interview questions, tagged by company. Treat every entry as a dated anecdote, not a syllabus. ⚠ 403s automated clients.

### Naukri Code360

- **Docs:** [naukri.com/code360](https://www.naukri.com/code360/) · [problems](https://www.naukri.com/code360/problems)
- *Note:* India-centric, free, with company-tagged problem sets. A real substitute for LeetCode Premium's company filters.

### Coding Ninjas Studio

- **Docs:** [codingninjas.com/studio](https://www.codingninjas.com/studio/) · [interview questions](https://www.codingninjas.com/studio/interview-questions)
- *Note:* India-centric free problems and company-wise questions. (Their paid bootcamps are deliberately not indexed here — see Honest notes.)

### GeeksforGeeks company-wise

- **Docs:** [geeksforgeeks.org/companies](https://www.geeksforgeeks.org/companies/) · [must-do company-wise](https://www.geeksforgeeks.org/must-coding-questions-company-wise) · [recently asked, product companies](https://www.geeksforgeeks.org/dsa/recently-asked-interview-questions-in-product-based-companies/)
- *Note:* The closest free substitute for LeetCode Premium's company tags. Checklist value only — the solutions are not model answers.

### InterviewQuery

- **Docs:** [interviewquery.com](https://www.interviewquery.com/)
- *Note:* Data/ML-leaning interview prep; some free questions, most behind a paywall. ⚠ Rate-limits automated clients (429).

### takeUforward (Striver's SDE sheet)

- **Docs:** [takeuforward.org — Striver's SDE Sheet](https://takeuforward.org/interviews/strivers-sde-sheet-top-coding-interview-problems)
- *Note:* ~190 problems, the default India placement sheet. ⚠ The site root intermittently returns 522 (Cloudflare) while deep links resolve fine.

### Sean Prashad — LeetCode patterns

- **Docs:** [seanprashad.com/leetcode-patterns](https://seanprashad.com/leetcode-patterns/)
- *Note:* The fastest pattern → problem map: from "I cannot solve this" to "this is a monotonic stack". A lookup table, not a course — pair it with an ordered list like NeetCode's roadmap.

### AlgoDaily

- **Docs:** [algodaily.com](https://www.algodaily.com/)
- *Note:* Daily concept review; good for maintenance, weak for depth.

### Structy

- **Docs:** [structy.net](https://structy.net/)
- *Note:* Pattern-based course with built-in visualisation. Paid, cheap, and unusually well-structured for absolute beginners.

### ByteByteGo

- **Docs:** [bytebytego.com](https://www.bytebytego.com/)
- *Note:* The best free system-design visual reference. Adjacent to DSA, but system design is the other half of the same interview loop.

### DataLemur

- **Docs:** [datalemur.com](https://datalemur.com/)
- *Note:* Free SQL and stats with some coding. Only relevant if you are targeting data or analytics roles.

### Adjacent practice platforms

- **Docs:** [exercism.org](https://exercism.org/) · [tracks](https://exercism.org/tracks) · [codewars.com](https://www.codewars.com/) · [kata search](https://www.codewars.com/kata) · [adventofcode.com](https://adventofcode.com/) · [codingame.com](https://www.codingame.com/) · [coderbyte.com](https://coderbyte.com/)
- *Note:* Language fluency (Exercism), short-kata drills (Codewars), and implementation-plus-ad-hoc-reasoning (Advent of Code). Advent of Code is the best "fun" practice there is.


## 6. Editorials & solution archives

### LeetCode official solutions

- **Docs:** [leetcode.com/problems/&lt;slug&gt;/solutions](https://leetcode.com/problems/two-sum/solutions/)
- *Note:* Primary when available; much of it is login-gated. Prefer it over third-party mirrors.

### Codeforces editorials

- **Docs:** Linked from each contest's tutorial blog post on [codeforces.com/contests](https://codeforces.com/contests)
- *Note:* Written by the setters. Always prefer these to third-party write-ups — intent is not inferable from an accepted solution.

### AtCoder editorials

- **Docs:** Per-contest "Editorial" tab on [atcoder.jp/contests](https://atcoder.jp/contests/)
- *Note:* Short, precise, official, and reliably present — the best editorial culture among the big three.

### CodeChef Discuss

- **Docs:** [discuss.codechef.com](https://discuss.codechef.com/)
- *Note:* Where CodeChef editorials and the per-problem Q&A live. Search before asking; almost everything has been answered.

### algo.monster

- **Docs:** [algo.monster](https://algo.monster/) · [editorials](https://algo.monster/editorials)
- *Note:* Structured LeetCode-style editorials plus pattern guides. The pattern pages are the useful part.

### walkccc.me

- **Docs:** [walkccc.me](https://walkccc.me/) · [LeetCode index](https://walkccc.me/LeetCode/)
- *Note:* The best searchable per-problem LeetCode index, with multi-language code. Fast lookup, minimal prose.

### leetcode.ca

- **Docs:** [leetcode.ca](https://leetcode.ca/) · [all problems](https://leetcode.ca/all/)
- *Note:* Full-text searchable solutions and discussion mirror. Works without a LeetCode account.

### doocs/leetcode

- **Docs:** [leetcode.doocs.org](https://leetcode.doocs.org/) · mirror [doocs.github.io/leetcode](https://doocs.github.io/leetcode/)
- **Source:** [github.com/doocs/leetcode](https://github.com/doocs/leetcode)
- *Note:* Open source, PR-driven, actively maintained, broad language coverage. The most durable of the LeetCode repositories.

### neetcode.io/solutions

- **Docs:** [neetcode.io/solutions](https://neetcode.io/solutions) · [practice](https://neetcode.io/practice) · [courses](https://neetcode.io/courses)
- *Note:* Consistent quality with video walkthroughs for the hard problems. Use the [roadmap](https://neetcode.io/roadmap) for ordering.

### Petr Mitrichev's blog

- **Docs:** [petr-mitrichev.blogspot.com](https://petr-mitrichev.blogspot.com/)
- *Note:* A top competitor's running analysis of every major contest, for over a decade. The best available model of how a strong contestant actually thinks.


## 7. University & MOOC course material

### MIT OpenCourseWare

- **Docs:** [ocw.mit.edu](https://ocw.mit.edu)
- **SDKs & repos:** [6.006](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/) · [6.046J](https://ocw.mit.edu/courses/6-046j-design-and-analysis-of-algorithms-spring-2015/) · [6.851](https://ocw.mit.edu/courses/6-851-advanced-data-structures-spring-2012/) · [6.854J](https://ocw.mit.edu/courses/6-854j-advanced-algorithms-fall-2008/) · [6.042](https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/) · [18.781](https://ocw.mit.edu/courses/18-781-theory-of-numbers-spring-2012/) · [18.06SC](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)
- **Downloadable / offline:** Lecture notes, assignments and exams as PDFs
- *Note:* The free core of a theory CS degree. 6.006 for foundations, 6.046J/6.854J for proofs, 6.851 past CLRS-level structures, 6.042 for the discrete math that CP assumes, 18.781 for number theory.

### Stanford CS 97SI

- **Docs:** [web.stanford.edu/class/cs97si](https://web.stanford.edu/class/cs97si/)
- *Note:* "Introduction to Programming Contests" — one of very few university courses aimed straight at contests. Dense, free, and short.

### Stanford CS 161

- **Docs:** [web.stanford.edu/class/cs161](https://web.stanford.edu/class/cs161/)
- *Note:* Current-term design and analysis of algorithms, with notes and problem sets posted publicly.

### Princeton Algorithms (Coursera)

- **Docs:** [coursera.org/learn/algorithms-part1](https://www.coursera.org/learn/algorithms-part1)
- *Note:* Sedgewick's course — the best-paced implementation-first algorithms course. ⚠ Coursera audit access varies by course and changes without notice.

### Stanford Algorithms Specialization

- **Docs:** [coursera.org/specializations/algorithms](https://www.coursera.org/specializations/algorithms)
- *Note:* Roughgarden's sequence. Strengthens correctness arguments and the theory side; *Algorithms Illuminated* is the paid companion.

### UCSD DSA Specialization

- **Docs:** [coursera.org/specializations/data-structures-algorithms](https://www.coursera.org/specializations/data-structures-algorithms)
- *Note:* The most practical of the three: graded coding over proofs.

### Discrete Mathematics Specialization

- **Docs:** [coursera.org/specializations/discrete-mathematics](https://www.coursera.org/specializations/discrete-mathematics)
- *Note:* The formal backbone underneath all of the math section — logic, combinatorics, graphs.

### NPTEL — Design & Analysis of Algorithms (IIT Bombay)

- **Docs:** [nptel.ac.in/courses/106101060](https://nptel.ac.in/courses/106101060)
- **Downloadable / offline:** Free video lectures and assignments
- *Note:* Aligned to Indian B.Tech syllabi and GATE, free, and certifiable. The local canonical for this subject.

### NPTEL — DAA (CMI)

- **Docs:** [nptel.ac.in/courses/106106131](https://nptel.ac.in/courses/106106131)
- *Note:* A second opinion with a CS-theory flavour; NP-completeness is done properly.

### SWAYAM

- **Docs:** [swayam.gov.in](https://swayam.gov.in/) · course index at [nptel.ac.in/courses](https://nptel.ac.in/courses)
- *Note:* India's credit-bearing MOOC platform. Filter Computer Science → Algorithms / Discrete Mathematics.

### Harvard CS50x

- **Docs:** [cs50.harvard.edu/x](https://cs50.harvard.edu/x/)
- *Note:* Only if DSA still feels blocked by programming basics. Skip otherwise.

### Khan Academy

- **Docs:** [khanacademy.org/math](https://www.khanacademy.org/math)
- *Note:* Free remediation for pre-college math gaps. Do this *before* attempting olympiad material, not alongside it.

### Brilliant

- **Docs:** [brilliant.org](https://www.brilliant.org/)
- *Note:* Paid. Builds intuition interactively; does not build contest volume.

### OSSU Computer Science

- **Source:** [github.com/ossu/computer-science](https://github.com/ossu/computer-science)
- *Note:* A full self-taught CS curriculum assembled from free university courses. Use its algorithms and discrete-math slots to sequence everything above.

### Course directories

- **Source:** [prakhar1989/awesome-courses](https://github.com/prakhar1989/awesome-courses) · [Developer-Y/cs-video-courses](https://github.com/Developer-Y/cs-video-courses) · [vhf/free-programming-books](https://github.com/vhf/free-programming-books)
- *Note:* Discovery mechanisms. `free-programming-books` is the canonical "what is legally free" index, with Algorithms, Competitive Programming and Mathematics sections.

### Commonlounge

- **Docs:** [commonlounge.com](https://www.commonlounge.com/)
- *Note:* Text-based CP and algorithms courses with a discussion layer. Beginner-friendly and occasionally stale; useful as a second explanation when the primary one does not land.

### CMU 15-210

- **Docs:** [cs.cmu.edu/~15210](https://www.cs.cmu.edu/~15210/)
- *Note:* Parallel and sequential data structures, with a free textbook. The best treatment of the functional/parallel DS perspective most CP resources skip.

### MIT 6.042 Mathematics for Computer Science

- **Downloadable / offline:** [mcs.pdf](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf) — free, complete
- *Note:* Proof techniques, induction, counting, probability. Fixes the actual deficit most CP learners have: it is not coding, it is proof and counting.


## 8. Community, video & aggregators

### Codeforces blog

- **Docs:** [codeforces.com/blog/entry/23054](https://codeforces.com/blog/entry/23054) — "An awesome list for competitive programming"
- *Note:* The best single directory of CP resources, maintained in the open on the largest CP site. Start here when you want something this page does not list.

### r/competitiveprogramming

- **Docs:** [reddit.com/r/competitiveprogramming](https://www.reddit.com/r/competitiveprogramming/)
- *Note:* Q&A, resource threads and the endless "how do I reach X rating" archive. ⚠ Reddit 403s automated clients.

### r/leetcode

- **Docs:** [reddit.com/r/leetcode](https://www.reddit.com/r/leetcode/)
- *Note:* Interview-prep side of the community: offer timelines, OA reports, company-specific threads.

### r/algorithms

- **Docs:** [reddit.com/r/algorithms](https://www.reddit.com/r/algorithms/)
- *Note:* Smaller and more theory-leaning; good for "why does this work" questions.

### Errichto (video)

- **Docs:** [youtube.com/@Errichto](https://www.youtube.com/@Errichto)
- *Note:* Contest strategy and live solving. The closest thing to watching a strong contestant think out loud.

### SecondThread (video)

- **Docs:** [youtube.com/@SecondThread](https://www.youtube.com/@SecondThread)
- *Note:* USACO/IOI-level walkthroughs with unusually honest explanations of wrong turns.

### Algorithms Live! (video)

- **Docs:** [youtube.com/@AlgorithmsLive](https://www.youtube.com/@AlgorithmsLive)
- *Note:* Advanced contest technique, aimed past Div1-C. Watch once you can follow the references without pausing.

### Tushar Roy (video)

- **Docs:** [youtube.com/@tusharroy2525](https://www.youtube.com/@tusharroy2525)
- *Note:* Classic DSA explained slowly and completely. Best for first exposure to a structure.

### Abdul Bari (video)

- **Docs:** [youtube.com/@abdul_bari](https://www.youtube.com/@abdul_bari)
- *Note:* Exam-oriented algorithm analysis; excellent for complexity derivations.

### NeetCode (video)

- **Docs:** [youtube.com/@NeetCode](https://www.youtube.com/@NeetCode)
- *Note:* LeetCode pattern walkthroughs, matched to the [roadmap](https://neetcode.io/roadmap).

### take U forward (video)

- **Docs:** [youtube.com/@takeUforward](https://www.youtube.com/@takeUforward)
- *Note:* India placement DSA, Hindi/English. Large, systematic, beginner-friendly.

### Algorithmist — Programming Live with Larry

- **Docs:** [youtube.com/@Algorithmist](https://www.youtube.com/@Algorithmist) · [videos](https://www.youtube.com/@Algorithmist/videos)
- *Note:* The best pure "video solutions" channel: Larry was a red Topcoder, a Google Code Jam finalist, top-100 on Advent of Code and top-50 on LeetCode, and he has run 500+ interviews. He solves live and explains as *both* interviewer and interviewee — nobody else shows you both sides of that dialogue.

### Colin Galen

- **Docs:** [youtube.com/@colingalen](https://www.youtube.com/@colingalen)
- *Note:* USACO Silver/Gold and Codeforces solution videos, with the reasoning left in. Best CP video resource between "I can do ABC C" and "I want Platinum".

### Back To Back SWE

- **Docs:** [youtube.com/@backtobackswe](https://www.youtube.com/@backtobackswe)
- *Note:* Interview-pattern walkthroughs that spend real time on *why the obvious approach fails* before presenting the right one. The closest thing to a good mock interviewer on video.

### Kevin Naughton Jr.

- **Docs:** [youtube.com/@kevinnaughtonjr](https://www.youtube.com/@kevinnaughtonjr)
- *Note:* Calm, complete LeetCode walkthroughs, one problem at a time. Good for your first pass over a new pattern, before you try it alone.

### CS Dojo

- **Docs:** [youtube.com/@CSdojo](https://www.youtube.com/@CSdojo)
- *Note:* Beginner-friendly DSA from an ex-Google engineer. The right first exposure if arrays and recursion are still shaky — too slow past that point.

### mycodeschool

- **Docs:** [youtube.com/@mycodeschool](https://www.youtube.com/@mycodeschool)
- *Note:* The classic DSA lecture series — pointers, linked lists, trees, hashing, DP — still among the clearest explanations ever recorded. The channel is dormant; treat it as an archive, not a feed.

### William Fiset

- **Docs:** [youtube.com/channel/UCD8yeTczadqdARzQUp29PJw](https://www.youtube.com/channel/UCD8yeTczadqdARzQUp29PJw)
- **SDKs & repos:** [github.com/williamfiset/Algorithms](https://github.com/williamfiset/Algorithms) — every structure in the videos has code here
- **Downloadable / offline:** The full "Data Structures Easy to Advanced" course is mirrored on freeCodeCamp
- *Note:* A complete DSA course in Java plus a dedicated graph-theory series, and the only channel whose videos and repository line up one-to-one. ⚠ The channel lives at the legacy `/channel/UC…` URL — the `@williamfiset` handle 404s.

### Aditya Verma

- **Docs:** [youtube.com/@AdityaVerma](https://www.youtube.com/@AdityaVerma)
- *Note:* The dynamic-programming series that most Indian placement aspirants actually learn DP from, plus CP topic playlists. Slow, cumulative, and worth the hours if DP is your wall.

### Indian DSA & placement channels

- **Docs:** [CodeHelp — by Babbar](https://www.youtube.com/@CodeHelp) · [Apna College](https://www.youtube.com/@ApnaCollegeOfficial) · [PepCoding](https://www.youtube.com/@PepCoding) · [CodeNCode](https://www.youtube.com/@CodeNCode) · [Kunal Kushwaha](https://www.youtube.com/@KunalKushwaha) · [Jenny's Lectures CS IT](https://www.youtube.com/@JennyslecturesCSIT) · [Neso Academy](https://www.youtube.com/@NesoAcademy) · [Gate Smashers](https://www.youtube.com/@GateSmashers) · [GeeksforGeeks](https://www.youtube.com/@geeksforgeeksvideos)
- *Note:* Where the Indian placement-prep consensus is formed — 450-question sheets, complete DSA playlists, and GATE material. Mostly Hindi or Hinglish. Apply the same rule as the aggregator sites: excellent for first exposure, verify every claim before repeating it.

### University & course channels

- **Docs:** [MIT OpenCourseWare](https://www.youtube.com/@mitocw) · [Stanford Online](https://www.youtube.com/@StanfordOnline) · [freeCodeCamp](https://www.youtube.com/@freecodecamp)
- *Note:* Full lecture recordings — MIT 6.006 and Stanford CS161 among them — and freeCodeCamp hosts complete multi-hour DSA courses (Fiset's data-structures course lives there). Slow, but they are the only videos here with an accompanying problem set.

### More contest & interview video solutions

- **Docs:** [William Lin (tmwilliamlin168)](https://www.youtube.com/@tmwilliamlin168) · [Neal Wu](https://www.youtube.com/@neal_wu) · [Bo Qian](https://www.youtube.com/@BoQianTheProgrammer)
- *Note:* Three competitors who post worked solutions with the reasoning intact. William Lin and Neal Wu sit at the Codeforces/ICPC end; Bo Qian is LeetCode-style but unusually rigorous about data-structure internals. Watch one, attempt the next one yourself.

### Algorithm concept channels

- **Docs:** [Reducible](https://www.youtube.com/@Reducible) · [3Blue1Brown](https://www.youtube.com/@3blue1brown) · [ByteByteGo](https://www.youtube.com/@ByteByteGo)
- *Note:* Concept-first videos for when the algorithm still feels like magic: Reducible on DP, graph algorithms and NP-completeness; 3Blue1Brown on the visual intuition behind linear algebra, calculus and Fourier methods; ByteByteGo for system-design diagrams. These teach *why*, never the implementation.

### Math channels (contest & intuition)

- **Docs:** [Art of Problem Solving](https://www.youtube.com/@ArtofProblemSolving) · [Michael Penn](https://www.youtube.com/@MichaelPennMath) · [SyberMath](https://www.youtube.com/@SyberMath) · [blackpenredpen](https://www.youtube.com/@blackpenredpen) · [MindYourDecisions](https://www.youtube.com/@MindYourDecisions) · [Numberphile](https://www.youtube.com/@numberphile)
- *Note:* AoPS's own channel is the only official one here; Michael Penn and SyberMath work through olympiad-style problems on camera, blackpenredpen is the algebra/olympiad grind, MindYourDecisions is puzzle-shaped counting and probability, Numberphile is exposure. All are supplementary — none replaces working problems on paper.

### More course & lecture channels

- **Docs:** [Khan Academy](https://www.youtube.com/@khanacademy) · [Dr. Trefor Bazett](https://www.youtube.com/@DrTrefor) · [AlgoExpert](https://www.youtube.com/@AlgoExpert) · [HELLO INTERVIEW](https://www.youtube.com/@hellointerview)
- *Note:* Khan Academy for math remediation, Trefor Bazett for discrete math and linear algebra at university pace, AlgoExpert and Hello Interview for structured interview content with free samples. Paid upsells behind two of them — the free material stands on its own.

### More Indian DSA channels

- **Docs:** [CodeWithHarry](https://www.youtube.com/@CodeWithHarry) · [Coding Blocks](https://www.youtube.com/@CodingBlocks) · [Scaler](https://www.youtube.com/@ScalerOfficial)
- *Note:* The second tier of the Indian placement ecosystem: full DSA playlists, C++ and Java tracks, and interview series. Same caveat as the first cluster — first exposure is fine, verification is on you, and the paid bootcamps behind two of these are deliberately not indexed here.

### UC Berkeley CS 61B (video)

- **Docs:** [youtube.com/@cs61b](https://www.youtube.com/@cs61b) · [Data structures playlist](https://www.youtube.com/playlist?list=PLF9CE525A9F89EDC5)
- *Note:* Hug's data-structures course, in Berkeley's order, with the labs. The Java-flavoured counterpart to MIT 6.006, and better paced for a first pass.

### DSA full-course playlist (video)

- **Docs:** [youtube.com playlist — Data structures & algorithms, start to finish](https://www.youtube.com/playlist?list=PL9Dk8axBIC8Tr_AfR928n7t7UTtFp5pRC)
- *Note:* One continuous course rather than a topic lookup. Use it for momentum when the curated material above feels fragmented, and verify everything against CLRS or cp-algorithms.


### GeeksforGeeks DSA tutorial

- **Docs:** [geeksforgeeks.org/dsa/dsa-tutorial-learn-data-structures-and-algorithms](https://www.geeksforgeeks.org/dsa/dsa-tutorial-learn-data-structures-and-algorithms/) · [practice](https://practice.geeksforgeeks.org/) · [top-100](https://www.geeksforgeeks.org/dsa/top-100-data-structure-and-algorithms-dsa-interview-questions-topic-wise/)
- *Note:* Breadth-first coverage in the idiom Indian placement prep actually uses. Derivative and uneven; "last updated" dates are cosmetic. Read here, verify against cp-algorithms or CPH, never cite it.

### Programiz

- **Docs:** [programiz.com/dsa](https://www.programiz.com/dsa)
- *Note:* Clean visual explanations for absolute beginners. Thin past intermediate level.

### TutorialsPoint

- **Docs:** [tutorialspoint.com/data_structures_algorithms](https://www.tutorialspoint.com/data_structures_algorithms/index.htm)
- *Note:* Old-school reference text, largely frozen. Check anything language-specific.

### W3Schools DSA

- **Docs:** [w3schools.com/dsa](https://www.w3schools.com/dsa/)
- *Note:* Five-minute orientation only.

### freeCodeCamp

- **Docs:** [freecodecamp.org/news](https://www.freecodecamp.org/news/)
- *Note:* Community articles — quality varies by author, but the search coverage is enormous.

### basecs

- **Docs:** [medium.com/basecs](https://medium.com/basecs)
- *Note:* Illustrated, careful explainers on fundamental DS and algorithms. Excellent writing; ⚠ Medium 403s automated clients.

### Educative — Grokking the Coding Interview

- **Docs:** [educative.io/courses/grokking-the-coding-interview](https://www.educative.io/courses/grokking-the-coding-interview)
- *Note:* Paid. The pattern taxonomy is what you are buying, not the code.


## 9. Repositories & awesome lists

### TheAlgorithms

- **Docs:** [github.com/TheAlgorithms](https://github.com/TheAlgorithms)
- **Source:** [github.com/TheAlgorithms/Python](https://github.com/TheAlgorithms/Python)
- **SDKs & repos:** [keon/algorithms](https://github.com/keon/algorithms) · [trekhleb/javascript-algorithms](https://github.com/trekhleb/javascript-algorithms) · [ADJA/algos](https://github.com/ADJA/algos) · [williamfiset/Algorithms](https://github.com/williamfiset/Algorithms)
- **Downloadable / offline:** Clone any of them; they are plain source trees
- *Note:* Algorithm libraries written to be *read*, not shipped. Ideal for seeing a clean implementation of something you have only used — but never copy from them into a contest: they optimise for clarity, not constant factors.

### LeetCode solution repositories

- **Docs:** [doocs/leetcode](https://github.com/doocs/leetcode) — the most actively maintained
- **SDKs & repos:** [walkccc/LeetCode](https://github.com/walkccc/LeetCode) · [neetcode-gh/leetcode](https://github.com/neetcode-gh/leetcode) · [youngyangyang04/leetcode-master](https://github.com/youngyangyang04/leetcode-master) · [labuladong/fucking-algorithm](https://github.com/labuladong/fucking-algorithm) · [azl397985856/leetcode](https://github.com/azl397985856/leetcode) · [halfrost/LeetCode-Go](https://github.com/halfrost/LeetCode-Go) · [grandyang/leetcode](https://github.com/grandyang/leetcode) · [haoel/leetcode](https://github.com/haoel/leetcode) · [soulmachine/leetcode](https://github.com/soulmachine/leetcode) · [fishercoder1534/Leetcode](https://github.com/fishercoder1534/Leetcode)
- **Downloadable / offline:** Git clone
- *Note:* Eleven of the long-running LeetCode archives. `leetcode-master` and `fucking-algorithm` are Chinese and are genuinely books, not solution dumps — the two highest-value entries here. Use them after you have tried the problem, never instead of.

### Interview-prep repositories

- **Source:** [yangshun/tech-interview-handbook](https://github.com/yangshun/tech-interview-handbook)
- **SDKs & repos:** [kdn251/interviews](https://github.com/kdn251/interviews) · [mission-peace/interview](https://github.com/mission-peace/interview) · [jwasham/coding-interview-university](https://github.com/jwasham/coding-interview-university) · [donnemartin/interactive-coding-challenges](https://github.com/donnemartin/interactive-coding-challenges) · [DopplerHQ/awesome-interview-questions](https://github.com/DopplerHQ/awesome-interview-questions) · [overide/gfg-company-wise-practice](https://github.com/overide/gfg-company-wise-practice) · [Ebazhanov/linkedin-skill-assessments-quizzes](https://github.com/Ebazhanov/linkedin-skill-assessments-quizzes) · [kunal-kushwaha](https://github.com/kunal-kushwaha)
- **Downloadable / offline:** Git clone; most render as static sites
- *Note:* `interviews` and `coding-interview-university` are the two canonical curated lists. `overide/gfg-company-wise-practice` mirrors the GeeksforGeeks company lists into folders by company — the closest free thing to LeetCode Premium's company tags in repository form.

### Awesome lists & discovery

- **Docs:** [lnishan/awesome-competitive-programming](https://github.com/lnishan/awesome-competitive-programming)
- **SDKs & repos:** [tayllan/awesome-algorithms](https://github.com/tayllan/awesome-algorithms) · [Programmers-Paradise/Competitive-Programming-Resources](https://github.com/Programmers-Paradise/Competitive-Programming-Resources) · [rossant/awesome-math](https://github.com/rossant/awesome-math) · [topic: competitive-programming](https://github.com/topics/competitive-programming) · [topic: data-structures](https://github.com/topics/data-structures) · [topic: coding-interview-questions](https://github.com/topics/coding-interview-questions)
- **Downloadable / offline:** Git clone; GitHub topic pages are live queries
- *Note:* `lnishan` is the best CP list and `rossant/awesome-math` the best math one; GitHub topics are the discovery mechanism when neither covers what you need. Treat every list as a starting point — they are not curated for correctness and several entries in all of them are now dead.

### CP template libraries

- **Docs:** [ShahjalalShohag/code-library](https://github.com/ShahjalalShohag/code-library)
- **SDKs & repos:** [the-tourist/algo](https://github.com/the-tourist/algo) · [ecnerwala/cp-book](https://github.com/ecnerwala/cp-book) · [beet-aizu/library](https://github.com/beet-aizu/library) · [SuprDewd/CompetitiveProgramming](https://github.com/SuprDewd/CompetitiveProgramming) · [mostafa-saad/MyCompetitiveProgramming](https://github.com/mostafa-saad/MyCompetitiveProgramming) · [bqi343/USACO](https://github.com/bqi343/USACO)
- **Downloadable / offline:** Clone and vendor
- *Note:* Personal and team template libraries from world-class competitors. Read two solutions to the same problem side by side — that comparison is worth more than either. **Fork whatever you adopt:** two of the most-linked template repositories on the internet (`Ashishgup1/Competitive-Programming`, `edsomjr/Competitive-Programming`) vanished in the last few years.

### Visualisation repositories

- **Source:** [algorithm-visualizer/algorithm-visualizer](https://github.com/algorithm-visualizer/algorithm-visualizer)
- **SDKs & repos:** [VisuAlgo](https://visualgo.net/en) · [USFCA Data Structure Visualizations](https://www.cs.usfca.edu/~galles/visualization/)
- **Downloadable / offline:** Run the visualiser locally from the repo
- *Note:* Intuition builders, not training. ⚠ The hosted `algorithm-visualizer.org` site did not resolve at verification time — build it from the repository instead. USFCA's Galles visualisations are the ones university courses embed, and they are the most reliable of the three.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*37 resources across 7 topics.*


#### Where to start

- **[USACO Guide](https://usaco.guide/)** — Start at your division (Bronze or Silver for most readers) and work the modules in order. The only CP curriculum with a proper ramp.
- **[Competitive Programmer's Handbook](https://cses.fi/book/book.pdf)** — Read chapters 1–10 alongside the CSES problem set. Free, coherent, and short enough to finish.
- **[AtCoder Beginners Selection](https://atcoder.jp/contests/abs)** — Eleven problems that tell you whether you can actually implement what you think you understand.
- **[Stanford CS 97SI](https://web.stanford.edu/class/cs97si/)** — A university course about contests specifically. One sitting, high density.


#### The algorithm theory floor

- **[MIT 6.006 lecture notes](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/pages/lecture-notes/)** — When you know *what* an algorithm does but not why it is O(n log n).
- **[Jeff Erickson — Algorithms](https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf)** — Free, rigorous, and genuinely funny. Chapters on recursion, DP, greedy and graphs.
- **[Open Data Structures](https://opendatastructures.org/)** — The data-structure half, free and complete, with real code.
- **[Sedgewick & Wayne — booksite](https://algs4.cs.princeton.edu/)** — Illustrations and every implementation, if you prefer pictures to prose.


#### The math floor

- **[MIT 6.042 MCS](https://courses.csail.mit.edu/6.042/spring18/mcs.pdf)** — Proofs, induction, counting, probability. The deficit almost every self-taught programmer has.
- **[MIT 18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/)** — Matrices, needed before linear recurrences and Gaussian elimination mod p.
- **[Project Euler](https://projecteuler.net/archives)** — Three to five problems a week. Forces modular arithmetic and big integers on you.
- **[AoPS Alcumus](https://artofproblemsolving.com/alcumus)** — Free adaptive trainer. Best free drill tool for competition math.
- **[Khan Academy](https://www.khanacademy.org/math)** — Remediation first if pre-college math is shaky.


#### Building the habit

- **[AtCoder ABC archive](https://atcoder.jp/contests/archive?ratedTypeStart%5B0%5D=1)** — One ABC per week, timed, all problems you can reach.
- **[Codeforces EDU courses](https://codeforces.com/edu/courses)** — Structured tracks on the judge you will actually contest on.
- **[clist.by](https://clist.by/)** — Put the calendar in front of you so contests stop sneaking up on you.
- **[CSES Problem Set](https://cses.fi/problemset/)** — The topic-ordered drill set; the benchmark for "ready for CF 1600".


#### Reading and writing code that judges accept

- **[cppreference](https://en.cppreference.com/w/)** — The C++ standard in readable form. Look things up here, not on a forum.
- **[Compiler Explorer](https://godbolt.org)** — Look at the assembly once. It cures most cargo-cult micro-optimisation.
- **[online-judge-tools/oj](https://github.com/online-judge-tools/oj)** — Submit and test from the command line; stop clicking through the browser.
- **[competitive-companion](https://github.com/jmerle/competitive-companion)** — Problem statement and samples straight into your editor.


#### Video courses & playlists

- **[MIT 6.006 — Introduction to Algorithms, Fall 2011](https://www.youtube.com/playlist?list=PLUl4u3cNGP61Oq3tWYp6V_F-5jb5L2iHb)** — The full lecture recordings of the OCW course above. Watch in parallel with the notes.
- **[MIT 18.06 Linear Algebra, Spring 2005](https://www.youtube.com/playlist?list=PLE7DDD91010BC51F8)** — Strang, complete. Watch lectures 1–15 and stop; that is the part CP needs.
- **[3Blue1Brown — Essence of linear algebra](https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab)** — The geometric intuition behind matrices, in four hours. Watch before Strang, not after.
- **[3Blue1Brown — Essence of calculus](https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr)** — Optional; only for the bounding-and-asymptotics intuition.
- **[William Fiset — Data Structures Easy to Advanced Course](https://www.youtube.com/watch?v=RBSGKlAvoiM)** — A complete, free, eight-hour data-structures course from a Google engineer, with every structure implemented in Java.
- **[William Fiset — Data structures playlist](https://www.youtube.com/playlist?list=PLDV1Zeh2NRsB6SWUrDFW2RmDotAfPbeHu)** — The same material broken into individual topics; use it as a lookup, not a course.
- **[mycodeschool — Data structures](https://www.youtube.com/playlist?list=PL2_aWCzGMAwI3W_JlcBbtYTwiQSsOTa6P)** — The classic lecture series, in order. Dormant channel, permanently good explanations.
- **[Aditya Verma — Dynamic Programming](https://www.youtube.com/playlist?list=PL_z_8CaSLPWekqhdCPmFohncHwz8TY2Go)** — The DP series most Indian placement aspirants learn from. Slow, cumulative, and worth the hours if DP is your wall.
- **[William Fiset — Graph theory playlist](https://www.youtube.com/playlist?list=PLDV1Zeh2NRsDGO4--qE8yH72HFL1Km93P)** — BFS/DFS through shortest paths, MST and network flow, in the same visual style as his course.
- **[UC Berkeley CS 61B — Data structures](https://www.youtube.com/playlist?list=PLF9CE525A9F89EDC5)** — Asymptotics through graphs in one sequence, with the Berkeley lab schedule alongside it.
- **[Data structures & algorithms — full course](https://www.youtube.com/playlist?list=PL9Dk8axBIC8Tr_AfR928n7t7UTtFp5pRC)** — A single start-to-finish course; good for momentum, weaker on proof depth.


#### If your target is interviews, not contests

- **[NeetCode roadmap](https://neetcode.io/roadmap)** — The best free ordering of LeetCode by pattern.
- **[Grind 75](https://www.techinterviewhandbook.org/grind75)** — The best time-boxed list, with a schedule generator.
- **[Tech Interview Handbook](https://www.techinterviewhandbook.org/)** — Free, opinionated, no paywall; the [SWE interview guide](https://www.techinterviewhandbook.org/software-engineering-interview-guide/) covers the loop itself, not just the problems.
- **[Pramp](https://www.pramp.com/)** — Free peer mock interviews. Do at least three before a real loop.
- **[Codility lessons](https://codility.com/programmers/lessons/)** — Practise in an actual OA vendor's idiom.


### Advanced

*35 resources across 6 topics.*


#### Reference implementations worth reading

- **[KACTL](https://github.com/kth-competitive-programming/kactl)** — Print it. Then check your template against it.
- **[AtCoder Library](https://atcoder.github.io/ac-library/production/document_en/)** — Official, maintained, correct. Read the lazy-segtree and convolution implementations.
- **[the-tourist/algo](https://github.com/the-tourist/algo)** · **[ecnerwala/cp-book](https://github.com/ecnerwala/cp-book)** · **[beet-aizu/library](https://github.com/beet-aizu/library)** — Three different world-class personal libraries. Comparing their solutions to the same problem is the fastest way to see what taste looks like.
- **[bqi343/USACO](https://github.com/bqi343/USACO)** and **[usaco-guide/usaco-guide](https://github.com/usaco-guide/usaco-guide)** — Implementations for the olympiad track, and the curriculum's own source.
- **[stanfordacm](https://github.com/jaehyunp/stanfordacm)** · **[t3nsor/codebook](https://github.com/t3nsor/codebook)** — Full team notebooks: the World Finals toolkit in two different styles.
- **[SuprDewd/CompetitiveProgramming](https://github.com/SuprDewd/CompetitiveProgramming)** · **[mostafa-saad/MyCompetitiveProgramming](https://github.com/mostafa-saad/MyCompetitiveProgramming)** — Long-running personal archives, useful for finding a worked solution to a named problem.


#### Algorithms past CLRS

- **[MIT 6.851 Advanced Data Structures](https://ocw.mit.edu/courses/6-851-advanced-data-structures-spring-2012/)** — Succinct, geometric and cache-aware structures.
- **[MIT 6.854J Advanced Algorithms](https://ocw.mit.edu/courses/6-854j-advanced-algorithms-fall-2008/)** — Flows, LP, randomised and amortised analysis at proof level.
- **[CMU 15-210](https://www.cs.cmu.edu/~15210/)** — Parallel and functional data structures, an angle CP resources skip.
- **[cp-algorithms](https://cp-algorithms.com/index.html)** — Implementation recipes when you need the algorithm now, not the theory.
- **[PEG Wiki](https://wcipeg.com/wiki/)** — The tricks that only exist inside contests.
- **[Library Checker](https://judge.yosupo.jp/)** — Machine-verify your library. Wire it into CI.


#### Math for the top end of contests

- **[Shoup — NTB](https://shoup.net/ntb/ntb-v2.pdf)** — Number theory and algebra for implementers.
- **[MIT 18.781 Theory of Numbers](https://ocw.mit.edu/courses/18-781-theory-of-numbers-spring-2012/)** — Proof-based number theory, pairs with Shoup.
- **[Evan Chen — Napkin](https://web.evanchen.cc/napkin.html)** — The fastest route from contest math to the language real mathematicians use.
- **[Evan Chen — olympiad resources](https://web.evanchen.cc/olympiad.html)** — Handouts and training advice from an IMO gold medallist.
- **[Yufei Zhao](https://yufeizhao.com/)** — Short modern handouts at the olympiad/research boundary.
- **[Kalva](https://prase.cz/kalva/)** and **[TU Eindhoven IMO collection](https://olympiads.win.tue.nl/imo/)** — Problems with solutions, and the shortlists.
- **[OEIS](https://oeis.org/)** — Turn a computed sequence into a closed form or recurrence.
- **[Nayuki — fast Fibonacci](https://www.nayuki.io/page/fast-fibonacci-algorithms)** — Fast doubling and matrix methods done properly.
- **[Chess Programming Wiki](https://www.chessprogramming.org/Transposition_Table)** — Hashing, transposition tables and adversarial search, better written than any CP page on the subject.


#### Olympiad problems, properly hosted

- **[oj.uz](https://oj.uz/)** — English-language olympiad problems with subtask scoring.
- **[IOI Syllabus](https://ioinformatics.org/files/ioi-syllabus-2025.pdf)** — Know the actual scope; it excludes calculus, statistics and combinatorial game theory.
- **[DMOJ](https://dmoj.ca/problems/)** — Search by category *and* by "has editorial".
- **[COCI](https://hsin.hr/coci/)** · **[POI](https://oi.edu.pl/)** · **[USACO past contests](https://usaco.org/index.php?page=contests)** — The national archives with real difficulty ladders.
- **[QOJ](https://qoj.ac/)** — Modern gym of OI/ICPC sets.


#### Team and contest infrastructure

- **[testlib](https://github.com/MikeMirzayanov/testlib)** — Checkers, generators and validators; the ecosystem standard.
- **[VJudge contests](https://vjudge.net/contest)** — Host a virtual or mashup contest for your team.
- **[DMOJ judge](https://github.com/DMOJ/online-judge)** · **[Hydro](https://github.com/hydro-dev/Hydro)** — Self-host a judge and learn what the black box actually does.
- **[Codeforces API](https://codeforces.com/apiHelp)** · **[clist API](https://clist.by/api/v4/doc/)** — Build your own tracker or problem recommender.


#### Reading research

- **[arXiv](https://arxiv.org/)** and **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Preprints, and the same papers as readable HTML.
- **[ECCC](https://eccc.weizmann.ac.il/)** — The theory community's own preprint server; where algorithms results appear first.
- **[DROPS/LIPIcs](https://drops.dagstuhl.de/)** — Fully open conference proceedings (ICALP, ESA, STACS, SWAT).
- **[DBLP](https://dblp.org/)** · **[Semantic Scholar](https://www.semanticscholar.org/)** · **[OpenAlex](https://openalex.org/)** — Bibliography, citation graph, and the fully open catalogue.
- **[Theory of Computing](https://theoryofcomputing.org/)** · **[Algorithmica](https://link.springer.com/journal/453)** · **[EJC](https://www.combinatorics.org/)** · **[INTEGERS](https://math.colgate.edu/~integers/)** · **[JIS](https://cs.uwaterloo.ca/journals/JIS/)** · **[Olympiads in Informatics](https://ioinformatics.org/journal/)** — Free or partly-free journals worth browsing by table of contents.


## Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; algorithms work lands here first
- **Downloadable / offline:** Every paper is a free PDF; bulk access documented at [info.arxiv.org/help/bulk_data](https://info.arxiv.org/help/bulk_data/index.html)
- *Note:* Not peer-reviewed. An arXiv-only paper is a claim, not a result — but it is where almost everything is first readable.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* When a paper is contested, the discussion is where you find the critique.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring, TLDRs
- **Downloadable / offline:** Free Graph API; bulk datasets on request
- *Note:* "Highly influential citations" is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions
- **Downloadable / offline:** Free API, no key; complete database snapshots downloadable
- *Note:* The only large bibliographic database that is open all the way down.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to see everything one researcher published, or one conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **SDKs & repos:** Papers plus full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading reviews and rebuttals teaches you how a field evaluates work.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **SDKs & repos:** Aggregates open-access repositories worldwide
- **Downloadable / offline:** Free API
- *Note:* The best broad search when you cannot remember which venue a paper appeared in.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **SDKs & repos:** Legal free full-text lookup by DOI
- **Downloadable / offline:** Free API and browser extension
- *Note:* The legitimate route around paywalls: it finds the author's copy, not a pirate PDF.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **SDKs & repos:** Curated papers with recorded talks
- *Note:* Start here when you do not yet know which papers matter.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Around a thousand papers summarised in plain language
- **Downloadable / offline:** Free, complete archive
- *Note:* Adrian Colyer's summaries are the fastest way to triage a paper before reading it.

### ECCC

- **Docs:** [eccc.weizmann.ac.il](https://eccc.weizmann.ac.il/)
- **Downloadable / offline:** All reports free
- *Note:* The theory community's own preprint server — algorithms results often appear here before or alongside arXiv.

### DROPS / LIPIcs

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **Downloadable / offline:** Fully open proceedings
- *Note:* Where ICALP, ESA, STACS and SWAT live — the main European algorithms venues, and entirely open access.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **Downloadable / offline:** ACM Open articles free; rest paywalled
- *Note:* STOC, FOCS (via IEEE), SODA-hosted and TALG content. ⚠ 403s automated clients; loads in a browser. Search authors' pages and arXiv first.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **Downloadable / offline:** Mostly paywalled; the legal free route is arXiv plus author pages
- *Note:* FOCS proceedings and a long tail of algorithms papers. Always check arXiv first.

### SIAM — SICOMP

- **Docs:** [epubs.siam.org/journal/smjcat](https://epubs.siam.org/journal/smjcat)
- **Downloadable / offline:** Paywalled; preprints usually free via authors or arXiv
- *Note:* *SIAM Journal on Computing* — the venue for the hard results on graph algorithms and complexity. ⚠ 403s automated clients.

### SODA / ALENEX / SOSA

- **Docs:** name-only — SIAM conference pages are year-scoped and move annually; search the conference name plus the year
- *Note:* SODA is the flagship algorithms conference; ALENEX is implementation and experimentation; SOSA is simplified/practical algorithms. Most papers have free preprints.

### ICALP / ESA / STACS / SWAT

- **Docs:** name-only; proceedings via [DROPS/LIPIcs](https://drops.dagstuhl.de/) — fully open
- *Note:* The European counterpart to SODA, and easier to read for free because LIPIcs is open by default.

### WADS / IPEC / TAMC

- **Docs:** name-only — WADS (algorithms and data structures), IPEC (parameterized complexity), TAMC (algorithms and computation)
- *Note:* Where the "small parameter, huge input" half of modern algorithms lives. If you read one book on it, read Cygan et al. below.

### Theory of Computing

- **Docs:** [theoryofcomputing.org](https://theoryofcomputing.org/)
- **Downloadable / offline:** Fully open access
- *Note:* Free, rigorous, and free of the paywall politics of the commercial journals.

### Algorithmica

- **Docs:** [link.springer.com/journal/453](https://link.springer.com/journal/453)
- **Downloadable / offline:** Some open-access articles; most paywalled
- *Note:* The main journal for algorithmic engineering — where a result becomes a usable algorithm.

### Theory of Computing Systems / TALG

- **Docs:** name-only — ToCT has no stable standalone host (`acmtoct.acm.org` did not resolve at verification time); TALG lives at `dl.acm.org/journal/talg`
- *Note:* Both are paywalled in part; find authors' copies.

### IPL & Discrete Applied Mathematics

- **Docs:** name-only — `sciencedirect.com/journal/information-processing-letters` and `/discrete-applied-mathematics`
- **Downloadable / offline:** Paywalled; ⚠ ScienceDirect 403s automated clients
- *Note:* Short-paper venues where many classic CP-adjacent tricks were first published. Use Unpaywall.

### Electronic Journal of Combinatorics

- **Docs:** [combinatorics.org](https://www.combinatorics.org/)
- **Downloadable / offline:** Fully open
- *Note:* Free and the natural home for the enumerative combinatorics that CP's counting problems draw on.

### INTEGERS

- **Docs:** [math.colgate.edu/~integers](https://math.colgate.edu/~integers/)
- **Downloadable / offline:** Fully open
- *Note:* The Electronic Journal of Combinatorial Number Theory — combinatorial game theory and integer-sequence work, both CP-relevant.

### Journal of Integer Sequences

- **Docs:** [cs.uwaterloo.ca/journals/JIS](https://cs.uwaterloo.ca/journals/JIS/)
- **Downloadable / offline:** Fully open
- *Note:* The journal behind OEIS. Where you go when a sequence turns out to be new.

### Mathematics of Computation

- **Docs:** [ams.org — mcom](https://www.ams.org/publications/journals/journalsframework/mcom)
- **Downloadable / offline:** Partly open; older volumes free
- *Note:* Computational number theory at research level — the deep end of Shoup.

### Olympiads in Informatics

- **Docs:** [ioinformatics.org/journal](https://ioinformatics.org/journal/)
- **Downloadable / offline:** Fully open
- *Note:* A peer-reviewed journal about olympiad problems and informatics education, from the IOI itself. Free, niche, and the only academic venue for the thing you are actually practising.

### Parameterized Algorithms (Cygan, Fomin, Kowalik, Lokshtanov, Marx, Pilipczuk, Pilipczuk, Saurabh)

- **Docs:** [link.springer.com/book/10.1007/978-3-319-21275-3](https://link.springer.com/book/10.1007/978-3-319-21275-3)
- **Downloadable / offline:** Paid; the authors circulate free copies and lecture notes on it
- *Note:* The standard text on FPT and kernelization — the branch of algorithms most relevant to contest-hard problems. ⚠ Springer returned a client challenge to automated checks; loads in a browser.

### Papers worth reading first

- **[Pattern-defeating Quicksort](https://arxiv.org/abs/2106.05123)** — pdqsort, the sort now shipping in libstdc++ and Rust. Modern sorting, and a lesson in engineering around adversarial inputs.
- **[A Simple and Fast Algorithm for Computing the N-th Term of a Linearly Recurrent Sequence](https://arxiv.org/abs/2008.08822)** — The Bostan–Mori write-up. Read it before implementing Kitamasa or Berlekamp–Massey from a blog post.
- **[Graph Sparsification by Effective Resistances](https://arxiv.org/abs/0803.0929)** and **[Spectral Sparsification of Graphs](https://arxiv.org/abs/0808.4134)** — Spielman–Srivastava sparsification; the start of the "nearly-linear-time everything" era.
- **[Twice-Ramanujan Sparsifiers](https://arxiv.org/abs/0808.0163)** — The optimal sparsification result, and a beautiful application of the interlacing family method.
- **[Approximate Gaussian Elimination for Laplacians](https://arxiv.org/abs/1605.02353)** — Where sparsification meets solver design.
- **[Linear-time Kernelization for Feedback Vertex Set](https://arxiv.org/abs/1608.01463)** — A concrete, contest-adjacent result in parameterized complexity.
- **Union-find, Fibonacci heaps, Hopcroft–Karp, Karger–Klein–Tarjan, Dor–Halperin–Zwick** — name-only: the classic analyses (Tarjan 1975; Fredman–Tarjan 1987; Hopcroft–Karp 1973; Karger–Klein–Tarjan 1995; Dor–Halperin–Zwick 2000). Free copies are easy to find via DBLP plus authors' pages; the *original analyses* are still clearer than most secondary write-ups.
- **Flajolet's probabilistic counting, and Cormode–Muthukrishnan's sketch survey** — name-only: the origin of HyperLogLog and the count-min sketch. Read these before trusting a "sketching" blog post.

## Conference videos, notes & archives

*3 resources across 1 group.* Competitive programming has no talk circuit. The archive that matters here is the task archive, not the video — so this section is short, and it points at problem sets rather than slides. Every URL returned 200 on **2026-10-09**.

### Competition archives

- **[IOI — International Olympiad in Informatics](https://ioinformatics.org/)** — Every IOI task, results table and regulation since 1989; the primary source for olympiad-level problems.
- **[ICPC](https://icpc.global/)** — The ICPC organisation: problem archives, regional results and the official rule set behind the contest format.
- **[IMO — International Mathematical Olympiad](https://www.imo-official.org/)** — Every IMO problem and result since 1959; the competitive-math primary source.

*Note:* No official YouTube channel exists for Codeforces, AtCoder, CodeChef or the ICPC — checked across several rounds on **2026-10-09**, every plausible handle either 404s or belongs to someone else. The community channels in category 8 are the only video source for contest material, and the task archives above are the only authoritative one.


## If you only do three things

1. **Finish one curriculum, not four.** Pick USACO Guide or the CPH + CSES pair and take it to completion, solving ≥80% of the problems in order. The failure mode in this field is not starting the wrong resource — it is starting five right ones.
2. **Write a template and verify it.** Build your own segment tree, modint, DSU and maxflow, then submit them to [Library Checker](https://judge.yosupo.jp/) until they pass. A library you have verified is worth more than a library you have read about.
3. **Do the math block every week, separately.** One chapter of MIT 6.042 or Shoup plus three Project Euler problems. Contest performance past ~1800 is gated far more by counting, modular arithmetic and proof than by knowing another data structure.

## Honest notes

- **The CP curriculum market is saturated and the interview-prep market is worse.** There are more "complete DSA roadmaps" than there are distinct ideas in them. Depth in one beats breadth across five; the ordering in USACO Guide exists because someone sequenced the dependencies.
- **Aggregators are fine to read and wrong to cite.** GFG, Programiz, TutorialsPoint and W3Schools carry real breadth and no accountability — off-by-one errors and wrong complexity claims survive for years because the "last updated" date is cosmetic. Verify against cp-algorithms, CPH or Erickson before you trust a claim you intend to repeat.
- **Company-prep data is crowdsourced or paywalled.** LeetCode's company tags are Premium; Blind, GFG and Code360 lists are anecdotes with dates. There is no authoritative free source, and anyone who says otherwise is selling something.
- **Dead links in this field are epidemic, and they are load-bearing.** A2OJ (the ladders), the ICPC Live Archive, `cftracker.net`, `algorithms.wtf`, `kt.cs.princeton.edu`, `datastructur.es`, `web.evanchen.us` and `code-drills.com` all died or stopped resolving, and every one of them is still linked from popular roadmaps. `www.topcoder.com` returned 404 to automated checks at verification time. If a guide you are following predates 2024, re-verify its links before trusting its plan.
- **Mirror your dependencies.** Both `Ashishgup1/Competitive-Programming` and `edsomjr/Competitive-Programming` 404'd — years of "start from this template" advice now points at nothing. Fork anything you build on.
- **OI Wiki's English version is gone**; `oi-wiki.org/en/` 404s and only the Chinese site remains.
- **USACO's legacy training pages are mid-migration.** They still work, but new usaco.org accounts are not recognised there — you may need a separate legacy account. Prefer USACO Guide as primary.
- **e-maxx was renamed, not deleted.** The English mirror `e-maxx-eng.github.io` is a dead end; the project is cp-algorithms.com and `github.com/cp-algorithms/cp-algorithms`.
- **LeetCode URL shapes drift** between redesigns (`/problemset/`, `/explore/`, `/studyplan/…`), and `leetcode.com` 403s automated clients. Bot-blocked does not mean broken.
- **Coursera "free" means "audit access varies".** Enrollment pages are not content; check what is actually unlocked before planning around a course.
- **GitHub 504s during verification were rate-limiting, not deletions** — `ossu/computer-science`, `vhf/free-programming-books`, `jeffgerickson/algorithms`, `boostorg/sort`, `cmuparlay/pbbsbench` and `Abhinav-Kumar012/dsa_book_2` all resolved on retry.
- **YouTube handles are not authoritative.** `@AtCoder` is a Vietnamese coder's channel and `@nick_white` resolves to a different channel entirely — both 200 OK, both wrong. Check the channel *name* before linking, and prefer legacy `/channel/UC…` URLs when a handle 404s (as with William Fiset).
- **No big platform runs an official YouTube channel.** `youtube.com/@leetcode`, `/@hackerrank` and `/@codechef` all 404, as do the legacy `/user/` and `/c/` forms; `@icpc` resolves to an unrelated channel named "ic Pc" and `@ICPCNews` is a news feed, not the organisation. Treat every "official" contest channel as suspect until you check the channel name.
- **Bot-blocked sources kept on purpose:** LeetCode, AoPS `community`, Reddit, Blind, InterviewQuery, SPOJ, `en.cppreference.com`, `dl.acm.org`, `epubs.siam.org` and ScienceDirect all return 403 or 429 to automated clients while loading normally in a browser.

---

## Related sections of this book

- [DSA](../dsa/README.md) — the explanatory chapters this index points out from
- [Competitive Programming](../competitive-programming/README.md) — contest strategy, per-judge guides and workflow
- [Competitive Math](../competitive-math/README.md) — the olympiad-math chapters, including the IMO guide
- [CS Theory](../cs-theory/README.md) — complexity classes, computability, randomized algorithms and approximation as concepts
- [Mathematics](../mathematics/README.md) — discrete math, linear algebra, probability, number theory
- [Reference Libraries index](./README.md) — the other topic indexes
