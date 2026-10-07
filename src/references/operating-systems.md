# Operating Systems Reference Library

This page is a verified index of primary sources for operating systems: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Production kernels, teaching kernels, RTOSes, the POSIX and OCI interfaces, observability tooling, and a two-track path from OSTEP to reading production kernel source.

**68 entries** across 8 categories, plus **58 education & reference-implementation resources** (24 basic / 34 advanced).

Every link HTTP-verified on **2026-10-07**.

> The OSDev Wiki returns 403 to automated clients but loads normally in a browser.

## Contents

- [1. Production kernels & their documentation](#1-production-kernels--their-documentation) — 11
- [2. Embedded & real-time operating systems](#2-embedded--real-time-operating-systems) — 4
- [3. Teaching kernels — read and modify these](#3-teaching-kernels--read-and-modify-these) — 7
- [4. Interfaces, standards & ABIs](#4-interfaces-standards--abis) — 5
- [5. Observability, debugging & tracing](#5-observability-debugging--tracing) — 7
- [6. Community & currency](#6-community--currency) — 4
- [7. Kernel learning material, labs & testing](#7-kernel-learning-material-labs--testing) — 9
- [8. Research papers & open-access literature](#8-research-papers--open-access-literature) — 21
- [Education & reference implementations](#education--reference-implementations) — 58 (24 basic / 34 advanced)


## 1. Production kernels & their documentation

### Linux

- **Docs:** [docs.kernel.org](https://docs.kernel.org/)
- **Developer / API:** [kernel.org/doc/html/latest](https://www.kernel.org/doc/html/latest/)
- **Source:** [github.com/torvalds/linux](https://github.com/torvalds/linux)
- **SDKs & repos:** The entire kernel is the SDK. Subsystem docs under Documentation/; `elixir.bootlin.com` for fast cross-referenced browsing
- **Downloadable / offline:** Kernel docs build to HTML/PDF from source (`make htmldocs`); full tree cloneable
- *Note:* Read `docs.kernel.org/process/howto.html` before anything else if you intend to contribute.

### FreeBSD

- **Docs:** [docs.freebsd.org/en/books/handbook](https://docs.freebsd.org/en/books/handbook/)
- **Developer / API:** [docs.freebsd.org/en/books/developers-handbook](https://docs.freebsd.org/en/books/developers-handbook/)
- **Source:** [github.com/freebsd/freebsd-src](https://github.com/freebsd/freebsd-src)
- **SDKs & repos:** Unified base system — kernel and userland in one tree, which makes it far easier to study than Linux
- **Downloadable / offline:** Handbook and Developer's Handbook as HTML/PDF/EPUB
- *Note:* The Handbook is the best-written OS documentation in existence. Worth reading even if you never run FreeBSD.

### OpenBSD

- **Docs:** [man.openbsd.org](https://man.openbsd.org/)
- **Source:** [github.com/openbsd/src](https://github.com/openbsd/src)
- **SDKs & repos:** pledge/unveil, OpenSSH, LibreSSL, pf all originate here
- **Downloadable / offline:** man pages are the documentation, and they are complete
- *Note:* Famous for correctness-first culture. The man pages are normative, not supplementary.

### NetBSD

- **Docs:** [netbsd.org/docs](https://www.netbsd.org/docs/)
- **Developer / API:** [netbsd.org/docs/internals/en](https://www.netbsd.org/docs/internals/en/)
- **Source:** [github.com/NetBSD/src](https://github.com/NetBSD/src)
- **SDKs & repos:** rump kernels — run kernel components in userspace, a genuinely unusual capability
- **Downloadable / offline:** Guide + internals docs
- *Note:* Best codebase for studying portability across architectures.

### illumos

- **Docs:** [illumos.org/docs](https://illumos.org/docs/)
- **Developer / API:** [illumos.org/books](https://illumos.org/books/)
- **Source:** [github.com/illumos/illumos-gate](https://github.com/illumos/illumos-gate)
- **SDKs & repos:** DTrace, ZFS and Zones originated in this lineage
- **Downloadable / offline:** Online books
- *Note:* The Solaris heritage. DTrace's architecture is still worth studying.

### Haiku

- **Docs:** [haiku-os.org/docs/userguide/en/contents.html](https://www.haiku-os.org/docs/userguide/en/contents.html)
- **Developer / API:** [haiku-os.org/guides](https://www.haiku-os.org/guides/)
- **Source:** [github.com/haiku/haiku](https://github.com/haiku/haiku)
- **SDKs & repos:** BeOS-compatible, pervasively multithreaded design
- **Downloadable / offline:** User guide + API docs
- *Note:* A modern, complete, readable OS that isn't Unix. Valuable precisely for that.

### ReactOS

- **Docs:** [reactos.org/wiki/Main_Page](https://reactos.org/wiki/Main_Page)
- **Source:** [github.com/reactos/reactos](https://github.com/reactos/reactos)
- **SDKs & repos:** Open reimplementation of the Windows NT kernel and userland
- **Downloadable / offline:** Wiki
- *Note:* The most accessible way to understand NT internals.

### Redox

- **Docs:** [doc.redox-os.org/book](https://doc.redox-os.org/book/)
- **Source:** [github.com/redox-os/redox](https://github.com/redox-os/redox)
- **SDKs & repos:** Microkernel OS written in Rust, with its own userland
- **Downloadable / offline:** The Redox Book
- *Note:* Shows what a memory-safe systems language does to OS design.

### Fuchsia (Zircon)

- **Docs:** [fuchsia.dev/fuchsia-src](https://fuchsia.dev/fuchsia-src)
- **Developer / API:** [fuchsia.dev/fuchsia-src/development](https://fuchsia.dev/fuchsia-src/development)
- **SDKs & repos:** Capability-based microkernel; component framework; FIDL IPC
- **Downloadable / offline:** Online docs
- *Note:* Google's from-scratch OS. The capability model documentation is excellent.

### XNU (macOS/iOS)

- **Docs:** [github.com/apple-oss-distributions/xnu](https://github.com/apple-oss-distributions/xnu)
- **Developer / API:** [developer.apple.com/documentation](https://developer.apple.com/documentation/)
- **Source:** [github.com/apple-oss-distributions/xnu](https://github.com/apple-oss-distributions/xnu)
- **SDKs & repos:** Mach + BSD hybrid; source released per OS version
- **Downloadable / offline:** Source only — Apple publishes little kernel prose
- *Note:* Source is released but undocumented. Read it alongside the Mach papers.

### Windows

- **Docs:** [learn.microsoft.com/en-us/…](https://learn.microsoft.com/en-us/windows-hardware/drivers/)
- **Developer / API:** [learn.microsoft.com/en-us/windows/win32](https://learn.microsoft.com/en-us/windows/win32/)
- **SDKs & repos:** WDK, WinDbg, ETW, Sysinternals
- **Downloadable / offline:** Microsoft Learn supports offline/PDF export per section
- *Note:* No source, but the driver and Win32 documentation is extensive and precise.


## 2. Embedded & real-time operating systems

### Zephyr

- **Docs:** [docs.zephyrproject.org/latest](https://docs.zephyrproject.org/latest/)
- **Developer / API:** [docs.zephyrproject.org/latest/develop](https://docs.zephyrproject.org/latest/develop/)
- **Source:** [github.com/zephyrproject-rtos/zephyr](https://github.com/zephyrproject-rtos/zephyr)
- **SDKs & repos:** West build tool, device tree, Kconfig; 750+ supported boards
- **Downloadable / offline:** Sphinx docs per release; repo cloneable
- *Note:* The Linux Foundation RTOS. Device-tree-driven, which makes it feel like a small Linux.

### FreeRTOS

- **Docs:** [freertos.org/Documentation/00-Overview](https://www.freertos.org/Documentation/00-Overview)
- **Source:** [github.com/FreeRTOS/FreeRTOS-Kernel](https://github.com/FreeRTOS/FreeRTOS-Kernel)
- **SDKs & repos:** Tiny kernel, very wide MCU support; AWS-maintained
- **Downloadable / offline:** Free PDF reference manual and the 'Mastering FreeRTOS' book
- *Note:* The kernel is a few thousand lines — read the scheduler directly.

### Apache NuttX

- **Docs:** [nuttx.apache.org/docs/latest](https://nuttx.apache.org/docs/latest/)
- **Source:** [github.com/apache/nuttx](https://github.com/apache/nuttx)
- **SDKs & repos:** POSIX-compliant RTOS — you can run near-standard code on a microcontroller
- **Downloadable / offline:** Sphinx docs
- *Note:* Unusual: real POSIX semantics at tiny scale.

### seL4

- **Docs:** [docs.sel4.systems](https://docs.sel4.systems/)
- **Source:** [github.com/seL4/seL4](https://github.com/seL4/seL4)
- **SDKs & repos:** Formally verified microkernel; machine-checked proofs of functional correctness
- **Downloadable / offline:** Reference manual PDF: [sel4.systems/Info/Docs/seL4-manual-latest.pdf](https://sel4.systems/Info/Docs/seL4-manual-latest.pdf)
- *Note:* The only general-purpose kernel with a full functional-correctness proof. The proof approach is as interesting as the kernel.


## 3. Teaching kernels — read and modify these

### xv6-riscv

- **Docs:** [pdos.csail.mit.edu/6.1810](https://pdos.csail.mit.edu/6.1810/)
- **Source:** [github.com/mit-pdos/xv6-riscv](https://github.com/mit-pdos/xv6-riscv)
- **SDKs & repos:** A complete Unix-like kernel in about 10,000 lines of C
- **Downloadable / offline:** The xv6 book (free PDF) — the companion text that explains every subsystem
- *Note:* The single best artefact in OS education. Read the book and the source side by side.

### Pintos

- **Docs:** [web.stanford.edu/class/…](https://web.stanford.edu/class/cs140/projects/pintos/pintos.html)
- **SDKs & repos:** Skeleton kernel with four staged projects: threads, user programs, VM, filesystem
- **Downloadable / offline:** Project documentation online
- *Note:* Harder than xv6 because you implement the missing parts yourself.

### OS/161

- **Docs:** [ops-class.org](https://www.ops-class.org/)
- **Source:** [github.com/ops-class/os161](https://github.com/ops-class/os161)
- **SDKs & repos:** Teaching OS with a full graded assignment sequence and public autograder
- **Downloadable / offline:** ops-class.org hosts everything
- *Note:* The most complete free OS course-in-a-box.

### MINIX 3

- **Docs:** [minix3.org](https://www.minix3.org/)
- **Source:** [github.com/Stichting-MINIX-Research-Foundation/…](https://github.com/Stichting-MINIX-Research-Foundation/minix)
- **SDKs & repos:** Microkernel designed for teaching, with Tanenbaum's textbook behind it
- **Downloadable / offline:** Book + source
- *Note:* Historically important — the system Linux was written in reaction to.

### Writing an OS in Rust

- **Docs:** [os.phil-opp.com](https://os.phil-opp.com/)
- **Source:** [github.com/phil-opp/blog_os](https://github.com/phil-opp/blog_os)
- **SDKs & repos:** Incremental blog-series kernel: bootloader, interrupts, paging, async
- **Downloadable / offline:** Online, with full source per post
- *Note:* The best modern from-scratch tutorial, in any language.

### The Little OS Book

- **Docs:** [littleosbook.github.io](https://littleosbook.github.io/)
- **SDKs & repos:** Short x86 kernel-from-scratch guide
- **Downloadable / offline:** Online + PDF
- *Note:* Minimal and honest about scope.

### OSDev Wiki

- **Docs:** [wiki.osdev.org/Main_Page](https://wiki.osdev.org/Main_Page)
- **SDKs & repos:** The community reference for bare-metal development: boot, A20, GDT, paging, ACPI
- **Downloadable / offline:** Wiki, exportable
- *Note:* Uneven in quality but irreplaceable. 403s to bots; fine in a browser.


## 4. Interfaces, standards & ABIs

### POSIX / Single UNIX Specification

- **Docs:** [pubs.opengroup.org/onlinepubs/9699919799](https://pubs.opengroup.org/onlinepubs/9699919799/)
- **SDKs & repos:** The normative definition of Unix system and shell interfaces
- **Downloadable / offline:** Free to read online in full
- *Note:* When documentation and implementation disagree, this is the arbiter.

### Linux man-pages

- **Docs:** [man7.org/linux/man-pages](https://man7.org/linux/man-pages/)
- **SDKs & repos:** Section 2 (syscalls) and 7 (overviews) are the real Linux API documentation
- **Downloadable / offline:** Installable via package manager; browsable online
- *Note:* The section 7 overview pages (`man 7 signal`, `man 7 capabilities`) are underused and excellent.

### OCI Runtime Specification

- **Docs:** [github.com/opencontainers/runtime-spec](https://github.com/opencontainers/runtime-spec)
- **Source:** [github.com/opencontainers/runtime-spec](https://github.com/opencontainers/runtime-spec)
- **SDKs & repos:** Defines what a container actually is, in terms of namespaces and cgroups
- **Downloadable / offline:** Markdown spec in-repo
- *Note:* Short. Read it and container magic disappears.

### runc

- **Docs:** [github.com/opencontainers/runc](https://github.com/opencontainers/runc)
- **Source:** [github.com/opencontainers/runc](https://github.com/opencontainers/runc)
- **SDKs & repos:** The reference OCI runtime — where the namespace and cgroup calls actually happen
- **Downloadable / offline:** In-repo docs
- *Note:* The bridge between 'container' and 'Linux kernel feature'.

### containerd

- **Docs:** [containerd.io/docs](https://containerd.io/docs/)
- **Source:** [github.com/containerd/containerd](https://github.com/containerd/containerd)
- **SDKs & repos:** Container runtime used by Docker and Kubernetes
- **Downloadable / offline:** Docs site


## 5. Observability, debugging & tracing

### eBPF / bpftrace

- **Docs:** [github.com/iovisor/bpftrace](https://github.com/iovisor/bpftrace)
- **Developer / API:** [bpftrace.org](https://bpftrace.org/)
- **Source:** [github.com/iovisor/bpftrace](https://github.com/iovisor/bpftrace)
- **SDKs & repos:** High-level tracing language over eBPF; one-liners that replace whole tools
- **Downloadable / offline:** In-repo reference guide
- *Note:* The modern way to ask the kernel arbitrary questions.

### Brendan Gregg's site

- **Docs:** [brendangregg.com](https://www.brendangregg.com/)
- **SDKs & repos:** Flame graphs, USE method, systems performance methodology
- **Downloadable / offline:** Articles + free tooling
- *Note:* If you measure Linux performance, this is the reference body of work.

### FlameGraph

- **Docs:** [github.com/brendangregg/FlameGraph](https://github.com/brendangregg/FlameGraph)
- **Source:** [github.com/brendangregg/FlameGraph](https://github.com/brendangregg/FlameGraph)
- **SDKs & repos:** The visualization that made profiling legible
- **Downloadable / offline:** In-repo

### perf

- **Docs:** [perf.wiki.kernel.org/index.php/Main_Page](https://perf.wiki.kernel.org/index.php/Main_Page)
- **Source:** [git.kernel.org](https://git.kernel.org/)
- **SDKs & repos:** Kernel-integrated profiler and counter interface
- **Downloadable / offline:** man pages + wiki

### strace

- **Docs:** [strace.io](https://strace.io/)
- **Source:** [github.com/strace/strace](https://github.com/strace/strace)
- **SDKs & repos:** Syscall tracer — still the fastest way to find out what a program actually does
- **Downloadable / offline:** man page

### Valgrind

- **Docs:** [valgrind.org/docs](https://www.valgrind.org/docs/)
- **SDKs & repos:** Memory error detection, cachegrind, callgrind
- **Downloadable / offline:** Manual online + PDF

### GDB

- **Docs:** [sourceware.org/gdb/current/onlinedocs/gdb.html](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)
- **Source:** [sourceware.org/git/binutils-gdb.git](https://sourceware.org/git/binutils-gdb.git)
- **SDKs & repos:** Including kernel debugging via QEMU + gdbstub
- **Downloadable / offline:** Full manual online and as PDF/info
- *Note:* Debugging a kernel under QEMU with GDB is the highest-leverage skill in OS work.


## 6. Community & currency

### LWN.net

- **Docs:** [lwn.net](https://lwn.net/)
- **SDKs & repos:** Kernel development reporting of exceptional technical quality
- **Downloadable / offline:** Subscriber articles become free after a week
- *Note:* The best single source for what is actually changing in Linux and why.

### Elixir cross-referencer

- **Docs:** [elixir.bootlin.com/linux/latest/source](https://elixir.bootlin.com/linux/latest/source)
- **SDKs & repos:** Browse any kernel version with symbol cross-referencing
- **Downloadable / offline:** Web
- *Note:* Far faster than grepping a local tree when you're orienting.

### KernelNewbies

- **Docs:** [kernelnewbies.org](https://kernelnewbies.org/)
- **SDKs & repos:** Per-release changelogs and first-patch guidance
- **Downloadable / offline:** Wiki

### Linux From Scratch

- **Docs:** [linuxfromscratch.org](https://www.linuxfromscratch.org/)
- **SDKs & repos:** Build a working distribution from source, step by step
- **Downloadable / offline:** Books as HTML/PDF
- *Note:* Teaches how a userland is assembled, which kernel study alone will not.


## 7. Kernel learning material, labs & testing

### Linux Kernel Module Programming Guide

- **Docs:** [sysprog21.github.io/lkmpg](https://sysprog21.github.io/lkmpg/)
- **Source:** [github.com/sysprog21/lkmpg](https://github.com/sysprog21/lkmpg)
- **SDKs & repos:** Actively maintained modern rewrite of the classic LKMPG
- **Downloadable / offline:** Online and as PDF from the repo
- *Note:* The fastest path from C programmer to writing a loadable kernel module.

### Linux Inside

- **Docs:** [0xax.gitbooks.io/linux-insides/content](https://0xax.gitbooks.io/linux-insides/content/)
- **Source:** [github.com/0xAX/linux-insides](https://github.com/0xAX/linux-insides)
- **SDKs & repos:** A guided walk through the kernel source from the boot process onward
- **Downloadable / offline:** GitBook, repo cloneable
- *Note:* Reads the actual source with you, line by line. Occasionally dated, still the best tour available.

### Linux Kernel Labs

- **Docs:** [linux-kernel-labs.github.io](https://linux-kernel-labs.github.io/)
- **Source:** [github.com/linux-kernel-labs/linux](https://github.com/linux-kernel-labs/linux)
- **SDKs & repos:** University lab series on device drivers, memory management and filesystems with QEMU setups
- **Downloadable / offline:** Sphinx docs + prepared VM images
- *Note:* Structured exercises with working skeletons — rare for kernel-level teaching material.

### Bootlin training materials

- **Docs:** [bootlin.com/docs](https://bootlin.com/docs/)
- **SDKs & repos:** Full slide decks and lab manuals for embedded Linux, kernel and driver development
- **Downloadable / offline:** Hundreds of pages of PDF slides, Creative Commons licensed
- *Note:* Commercial training material given away free. Among the best embedded Linux resources in existence.

### syzkaller

- **Docs:** [github.com/google/syzkaller](https://github.com/google/syzkaller)
- **Developer / API:** [github.com/google/syzkaller/tree/master/docs](https://github.com/google/syzkaller/tree/master/docs)
- **Source:** [github.com/google/syzkaller](https://github.com/google/syzkaller)
- **SDKs & repos:** Coverage-guided kernel fuzzer; syzbot reports bugs continuously upstream
- **Downloadable / offline:** In-repo docs
- *Note:* Reading syzbot reports is an education in how kernels actually fail.

### Rust for Linux

- **Docs:** [rust-for-linux.com](https://rust-for-linux.com/)
- **Developer / API:** [docs.kernel.org/rust](https://docs.kernel.org/rust/)
- **Source:** [github.com/Rust-for-Linux/linux](https://github.com/Rust-for-Linux/linux)
- **SDKs & repos:** Rust support merged into the mainline kernel; abstractions and example drivers
- **Downloadable / offline:** Project site + in-tree docs
- *Note:* The most consequential change to kernel development practice in decades. Still evolving quickly.

### Tock OS

- **Docs:** [tockos.org](https://www.tockos.org/)
- **Developer / API:** [book.tockos.org](https://book.tockos.org/)
- **Source:** [github.com/tock/tock](https://github.com/tock/tock)
- **SDKs & repos:** Embedded OS in Rust with memory-isolated applications on microcontrollers
- **Downloadable / offline:** The Tock Book
- *Note:* Shows what type-safety buys you at the embedded level, where you have no MMU to fall back on.

### Hubris

- **Docs:** [github.com/oxidecomputer/hubris](https://github.com/oxidecomputer/hubris)
- **Developer / API:** [hubris.oxide.computer/reference](https://hubris.oxide.computer/reference/)
- **Source:** [github.com/oxidecomputer/hubris](https://github.com/oxidecomputer/hubris)
- **SDKs & repos:** Oxide Computer’s embedded OS, with an unusually candid design rationale
- **Downloadable / offline:** Reference manual online
- *Note:* The documentation explains why each design decision was made, including the rejected alternatives.

### Asahi Linux

- **Docs:** [asahilinux.org](https://asahilinux.org/)
- **Developer / API:** [asahilinux.org/docs](https://asahilinux.org/docs/)
- **Source:** [github.com/AsahiLinux](https://github.com/AsahiLinux)
- **SDKs & repos:** Apple Silicon reverse engineering and Linux port
- **Downloadable / offline:** Documentation and extensive progress reports
- *Note:* Currently better documentation of Apple Silicon internals than Apple provides.


## 8. Research papers & open-access literature

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

### arXiv cs.OS (Operating Systems)

- **Docs:** [arxiv.org/list/cs.OS/recent](https://arxiv.org/list/cs.OS/recent)
- **SDKs & repos:** Preprints in OS research
- **Downloadable / offline:** Free
- *Note:* Low volume — OS work mostly goes straight to OSDI/SOSP rather than arXiv.

### USENIX OSDI

- **Docs:** [usenix.org/conference/osdi26](https://www.usenix.org/conference/osdi26)
- **SDKs & repos:** The flagship OS and systems venue
- **Downloadable / offline:** Every paper free, plus talk recordings
- *Note:* Alternates with SOSP. Start with the best-paper awards from the last five years.

### ACM SOSP

- **Docs:** [sosp.org](https://sosp.org/)
- **SDKs & repos:** The other flagship OS venue, running since 1967
- **Downloadable / offline:** Recent proceedings open via ACM OA
- *Note:* Historically where most of the field's landmark papers appeared.

### ACM SIGOPS

- **Docs:** [sigops.org](https://www.sigops.org/)
- **SDKs & repos:** The OS special interest group; hosts HotOS and Operating Systems Review
- **Downloadable / offline:** Much of it free
- *Note:* HotOS papers are short, speculative and unusually fun to read.

### EuroSys

- **Docs:** [eurosys.org](https://www.eurosys.org/)
- **SDKs & repos:** The leading European systems conference
- **Downloadable / offline:** Proceedings via ACM OA
- *Note:* Often more practical and implementation-focused than OSDI.

### USENIX ATC

- **Docs:** [usenix.org/conference/atc25](https://www.usenix.org/conference/atc25)
- **SDKs & repos:** Annual Technical Conference — applied systems work
- **Downloadable / offline:** All papers free
- *Note:* Where a lot of real production-systems engineering gets published.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*24 resources across 6 topics.*


#### The one book to start with

- **[Operating Systems: Three Easy Pieces (OSTEP)](https://pages.cs.wisc.edu/~remzi/OSTEP/)** — Free, complete, and better written than the paid alternatives. Virtualization, concurrency, persistence. Start here and finish it.
- **[xv6 book (PDF)](https://pdos.csail.mit.edu/6.828/2018/xv6/book-rev11.pdf)** — Short companion text explaining a real kernel line by line. Read with the source open.
- **[FreeBSD Handbook](https://docs.freebsd.org/en/books/handbook/)** — Even if you use Linux. It is the clearest systems documentation anywhere.


#### Courses with full public materials

- **[MIT 6.1810 Operating System Engineering](https://pdos.csail.mit.edu/6.1810/)** — xv6-based labs, all public, with a real autograder. The gold standard.
- **[Berkeley CS162](https://cs162.org/)** — Pintos-style projects, public slides and handouts.
- **[ops-class.org (OS/161)](https://www.ops-class.org/)** — Complete course: videos, assignments, autograder.
- **[UW CSE 451](https://courses.cs.washington.edu/courses/cse451/)** — Archived offerings with full materials.
- **[Stanford Pintos projects](https://web.stanford.edu/class/cs140/projects/pintos/pintos.html)** — Four staged projects, public documentation.


#### Read a real kernel

- **[xv6-riscv source](https://github.com/mit-pdos/xv6-riscv)** — ~10k lines. Read all of it. Few people regret doing this.
- **[Writing an OS in Rust](https://os.phil-opp.com/)** — Build from the bootloader up, with working code at every step.
- **[The Little OS Book](https://littleosbook.github.io/)** — Shorter alternative if the Rust series is too long.
- **[OSDev Wiki](https://wiki.osdev.org/Main_Page)** — The reference for every bare-metal detail you will hit.


#### The interfaces you must know

- **[Linux man-pages](https://man7.org/linux/man-pages/)** — Section 2 and section 7. Learn to read these fluently; it pays forever.
- **[POSIX / SUS](https://pubs.opengroup.org/onlinepubs/9699919799/)** — The normative definition. Free online.
- **[Linux kernel documentation](https://docs.kernel.org/)** — Start with the process and admin guides, not the subsystem internals.


#### Tools to learn alongside

- **[strace](https://strace.io/)** — Find out what a program actually asks the kernel for.
- **[GDB](https://sourceware.org/gdb/current/onlinedocs/gdb.html/)** — Learn it properly, including with QEMU for kernel work.
- **[QEMU](https://www.qemu.org/docs/master/)** — Your kernel development machine. Boot, break, repeat, with no hardware at risk.
- **[Linux From Scratch](https://www.linuxfromscratch.org/)** — Assemble a userland by hand once; you will never be confused about a distribution again.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*34 resources across 6 topics.*


#### Production kernel source — where to start reading

- **[Linux kernel tree](https://github.com/torvalds/linux)** — Do not start at the top. Pick one subsystem and follow a single syscall through it.
- **[Elixir cross-referencer](https://elixir.bootlin.com/linux/latest/source)** — Essential for navigating. Jump by symbol, not by grep.
- **[Kernel documentation](https://docs.kernel.org/)** — Subsystem maintainers write these; they are far better than the reputation suggests.
- **[FreeBSD source](https://github.com/freebsd/freebsd-src)** — One unified tree. Significantly easier to study end to end than Linux.
- **[OpenBSD source](https://github.com/openbsd/src)** — Smaller and more consistent. Read it when Linux feels impenetrable.
- **[illumos](https://github.com/illumos/illumos-gate)** — For DTrace and ZFS specifically.
- **[Contribution howto](https://docs.kernel.org/process/howto.html)** — Read before your first patch, not after it bounces.


#### Microkernels, verification & alternative designs

- **[seL4](https://github.com/seL4/seL4)** — The formally verified microkernel. Read the manual first.
- **[seL4 reference manual (PDF)](https://sel4.systems/Info/Docs/seL4-manual-latest.pdf)** — Capability-based design stated precisely.
- **[Fuchsia / Zircon](https://fuchsia.dev/fuchsia-src)** — A serious modern capability-based system with real documentation.
- **[Redox](https://doc.redox-os.org/book/)** — Microkernel in Rust, including the userland.
- **[MINIX 3](https://github.com/Stichting-MINIX-Research-Foundation/minix)** — The historically important microkernel argument, in code.
- **[Haiku](https://github.com/haiku/haiku)** — A complete non-Unix design. Useful for breaking Unix-shaped assumptions.


#### Containers, isolation & virtualization

- **[OCI Runtime Spec](https://github.com/opencontainers/runtime-spec)** — Short and demystifying. Read before any container tooling.
- **[runc](https://github.com/opencontainers/runc)** — Where namespaces and cgroups are actually configured.
- **[containerd](https://containerd.io/docs/)** — The layer above runc.
- **[QEMU](https://github.com/qemu/qemu)** — TCG translation and the KVM interface — read `accel/`.
- **[gVisor](https://github.com/google/gvisor)** — A userspace kernel intercepting syscalls. An unusual and instructive point in the design space.


#### Observability & performance at depth

- **[eBPF.io](https://ebpf.io/)** — Programmable kernel instrumentation, now the centre of Linux observability.
- **[Kernel BPF docs](https://docs.kernel.org/bpf/)** — The verifier's rules, and how to live with them.
- **[bpftrace](https://github.com/iovisor/bpftrace)** — Ask the kernel arbitrary questions in one line.
- **[BCC](https://github.com/iovisor/bcc)** — Dozens of production tracing tools; read them as examples.
- **[Brendan Gregg](https://www.brendangregg.com/)** — Methodology, not just tools. The USE method is the useful part.
- **[FlameGraph](https://github.com/brendangregg/FlameGraph)** — Visualize where time actually goes.
- **[perf](https://perf.wiki.kernel.org/index.php/Main_Page)** — Hardware counters, correctly interpreted.


#### Embedded & real-time

- **[Zephyr](https://docs.zephyrproject.org/latest/)** — Device-tree-driven RTOS with serious scale and governance.
- **[FreeRTOS kernel](https://github.com/FreeRTOS/FreeRTOS-Kernel)** — Small enough to read the scheduler in an afternoon.
- **[NuttX](https://github.com/apache/nuttx)** — POSIX semantics on microcontrollers.
- **[seL4](https://docs.sel4.systems/)** — Where real-time guarantees meet formal verification.


#### Staying current

- **[LWN.net](https://lwn.net/)** — The best technical reporting on kernel development. Weekly.
- **[KernelNewbies](https://kernelnewbies.org/)** — Per-release summaries of what changed.
- **[USENIX OSDI](https://www.usenix.org/conference/osdi25)** — The main OS research venue; papers are free.
- **[ACM SOSP](https://sosp.org/)** — The other one. Alternates years with OSDI.
- **[ASPLOS](https://asplos-conference.org/)** — Where OS research meets architecture and compilers.


---

## If you only do three things

1. **Read OSTEP cover to cover.** It is free, complete, and better than the textbooks people pay for.
2. **Read all of xv6** with the xv6 book open beside it. Ten thousand lines, one complete Unix.
3. **Do MIT 6.1810's labs.** Public, autograded, and they force the knowledge in.

## Honest notes

- **Do not start by reading Linux.** It is 40 million lines. Read xv6 first; Linux becomes navigable afterwards.
- **The FreeBSD Handbook is the best OS documentation written**, regardless of which OS you use.
- **`man 7` pages are underrated.** `man 7 signal`, `man 7 capabilities`, `man 7 namespaces` are concise and authoritative.
- **Containers are not a kernel feature.** Read the OCI runtime spec and runc and the mystery evaporates in an hour.
- **XNU source is published but undocumented.** Treat it as source, not as a reference.

---

## Related sections of this book

- [Operating Systems](../os/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other six topic indexes
