# Computer Architecture Reference Library

This page is a verified index of primary sources for computer architecture: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

ISA specifications, open-source cores, simulators, EDA toolchains, performance-analysis tooling, and a two-track learning path — from NAND gates to out-of-order execution and open silicon.

**63 entries** across 7 categories, plus **53 education & reference-implementation resources** (22 basic / 31 advanced).

Every link HTTP-verified on **2026-10-07**.

> Intel, AMD and Arm developer portals return 403 to automated clients but load normally in a browser.

## Contents

- [1. Instruction set architectures & vendor documentation](#1-instruction-set-architectures--vendor-documentation) — 8
- [2. Open-source cores & SoC platforms](#2-open-source-cores--soc-platforms) — 8
- [3. Simulators, emulators & modelling tools](#3-simulators-emulators--modelling-tools) — 8
- [4. Hardware description, synthesis & open EDA](#4-hardware-description-synthesis--open-eda) — 5
- [5. Performance analysis & microarchitectural measurement](#5-performance-analysis--microarchitectural-measurement) — 6
- [6. Reverse engineering, commentary & live tooling](#6-reverse-engineering-commentary--live-tooling) — 8
- [7. Research papers & open-access literature](#7-research-papers--open-access-literature) — 20
- [Education & reference implementations](#education--reference-implementations) — 53 (22 basic / 31 advanced)


## 1. Instruction set architectures & vendor documentation

### Intel (x86-64)

- **Docs:** [intel.com/content/…](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)
- **Developer / API:** [intel.com/content/…](https://www.intel.com/content/www/us/en/developer/overview.html)
- **SDKs & repos:** Intel oneAPI, ISPC, VTune, SDE; intrinsics guide
- **Downloadable / offline:** The Software Developer's Manual (SDM) ships as a ~5000-page PDF set, plus the separate Optimization Reference Manual
- *Note:* The SDM is the single most important document in x86 work. Volume 2 (instruction set) is the part you'll actually live in. Site 403s to bots but loads in a browser.

### AMD (x86-64)

- **Docs:** [amd.com/en/search/documentation/hub.html](https://www.amd.com/en/search/documentation/hub.html)
- **SDKs & repos:** AOCC compiler, AOCL libraries, uProf profiler
- **Downloadable / offline:** AMD64 Architecture Programmer's Manual, volumes 1-5, all free PDFs
- *Note:* Read alongside the Intel SDM — they disagree in instructive places, especially on memory ordering.

### Arm

- **Docs:** [developer.arm.com/documentation](https://developer.arm.com/documentation)
- **Developer / API:** [developer.arm.com](https://developer.arm.com/)
- **SDKs & repos:** Arm Compiler, Arm NN, CMSIS, Streamline
- **Downloadable / offline:** Arm Architecture Reference Manual (the 'Arm ARM') free PDF; per-core Technical Reference Manuals
- *Note:* Note the split: the Architecture Reference Manual is the ISA; the TRM is one specific core's implementation. People conflate these constantly.

### RISC-V International

- **Docs:** [riscv.org/technical/specifications](https://riscv.org/technical/specifications/)
- **Developer / API:** [riscv.org](https://riscv.org/)
- **Source:** [github.com/riscv/riscv-isa-manual](https://github.com/riscv/riscv-isa-manual)
- **SDKs & repos:** The whole ISA is developed in the open on GitHub — issues and PRs included
- **Downloadable / offline:** Unprivileged and Privileged spec PDFs built from the repo per ratified release
- *Note:* The only major ISA whose specification you can read the git history of. Hugely valuable for understanding *why* a design is the way it is.

### IBM Power

- **Docs:** [openpowerfoundation.org/specifications/isa](https://openpowerfoundation.org/specifications/isa/)
- **Source:** [github.com/openpowerfoundation](https://github.com/openpowerfoundation)
- **SDKs & repos:** OpenPOWER toolchain, A2O/Microwatt open cores
- **Downloadable / offline:** Power ISA specification PDF, openly licensed
- *Note:* Fully open ISA since 2019.

### SiFive

- **Docs:** [sifive.com/documentation](https://www.sifive.com/documentation)
- **Source:** [github.com/sifive](https://github.com/sifive)
- **SDKs & repos:** Freedom E SDK, core generators, SiFive Insight
- **Downloadable / offline:** Per-core manuals as PDF
- *Note:* Commercial RISC-V implementer; manuals are a good bridge from spec to silicon.

### NVIDIA GPU architecture

- **Docs:** [docs.nvidia.com/cuda](https://docs.nvidia.com/cuda/)
- **Developer / API:** [developer.nvidia.com/cuda-toolkit](https://developer.nvidia.com/cuda-toolkit)
- **Source:** [github.com/NVIDIA/cuda-samples](https://github.com/NVIDIA/cuda-samples)
- **SDKs & repos:** CUDA Toolkit, Nsight Compute/Systems, CUTLASS, cuBLAS
- **Downloadable / offline:** CUDA C++ Programming Guide and the per-architecture whitepapers (Hopper, Blackwell) as PDFs
- *Note:* The CUDA Programming Guide's memory-hierarchy chapters are the best free GPU architecture text available.

### Apple Silicon

- **Docs:** [developer.apple.com/documentation](https://developer.apple.com/documentation/)
- **SDKs & repos:** Metal, Accelerate, Instruments
- **Downloadable / offline:** Apple Silicon CPU Optimization Guide (PDF)
- *Note:* Sparse official microarchitectural detail; the community reverse-engineering (Asahi Linux, Dougall Johnson) fills most of the gap.


## 2. Open-source cores & SoC platforms

### Rocket Chip

- **Docs:** [github.com/chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip)
- **Source:** [github.com/chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip)
- **SDKs & repos:** In-order RISC-V core generator written in Chisel; the original Berkeley generator
- **Downloadable / offline:** README + Chisel source
- *Note:* Start here if you want to read a complete, synthesizable CPU.

### BOOM

- **Docs:** [github.com/riscv-boom/riscv-boom](https://github.com/riscv-boom/riscv-boom)
- **Developer / API:** [docs.boom-core.org](https://docs.boom-core.org/)
- **Source:** [github.com/riscv-boom/riscv-boom](https://github.com/riscv-boom/riscv-boom)
- **SDKs & repos:** Berkeley Out-of-Order Machine — a superscalar OoO RISC-V core you can actually read
- **Downloadable / offline:** Online docs + in-repo
- *Note:* The best available open implementation of out-of-order execution. Read it after you've read Rocket.

### Chipyard

- **Docs:** [chipyard.readthedocs.io](https://chipyard.readthedocs.io/)
- **Source:** [github.com/ucb-bar/chipyard](https://github.com/ucb-bar/chipyard)
- **SDKs & repos:** Full agile SoC design framework: cores, accelerators, RTL sim, VLSI flow
- **Downloadable / offline:** Sphinx docs; repo cloneable
- *Note:* The integration layer that makes the Berkeley ecosystem usable as one thing.

### CVA6 (OpenHW)

- **Docs:** [github.com/openhwgroup/cva6](https://github.com/openhwgroup/cva6)
- **Source:** [github.com/openhwgroup/cva6](https://github.com/openhwgroup/cva6)
- **SDKs & repos:** Application-class 64-bit RISC-V core in SystemVerilog, Linux-capable
- **Downloadable / offline:** In-repo docs
- *Note:* SystemVerilog rather than Chisel — easier if you came from industry RTL.

### Ibex

- **Docs:** [github.com/lowRISC/ibex](https://github.com/lowRISC/ibex)
- **Developer / API:** [ibex-core.readthedocs.io](https://ibex-core.readthedocs.io/)
- **Source:** [github.com/lowRISC/ibex](https://github.com/lowRISC/ibex)
- **SDKs & repos:** Small 32-bit RISC-V core, heavily verified
- **Downloadable / offline:** Sphinx docs
- *Note:* A realistic small core with a serious verification story attached.

### VexRiscv

- **Docs:** [github.com/SpinalHDL/VexRiscv](https://github.com/SpinalHDL/VexRiscv)
- **Source:** [github.com/SpinalHDL/VexRiscv](https://github.com/SpinalHDL/VexRiscv)
- **SDKs & repos:** Highly configurable RISC-V core in SpinalHDL
- **Downloadable / offline:** README
- *Note:* Good demonstration of generator-based hardware design.

### PicoRV32

- **Docs:** [github.com/YosysHQ/picorv32](https://github.com/YosysHQ/picorv32)
- **Source:** [github.com/YosysHQ/picorv32](https://github.com/YosysHQ/picorv32)
- **SDKs & repos:** Tiny size-optimized RISC-V core, single Verilog file
- **Downloadable / offline:** README
- *Note:* ~3000 lines of Verilog. Readable in an afternoon — the best first CPU to study.

### OpenTitan

- **Docs:** [opentitan.org](https://opentitan.org/)
- **Developer / API:** [opentitan.org/book](https://opentitan.org/book/)
- **Source:** [github.com/lowRISC/opentitan](https://github.com/lowRISC/opentitan)
- **SDKs & repos:** Open-source silicon root of trust; exemplary documentation and verification practice
- **Downloadable / offline:** Online book, repo cloneable
- *Note:* Worth reading purely as an example of how hardware projects *should* be documented.


## 3. Simulators, emulators & modelling tools

### gem5

- **Docs:** [gem5.org/documentation](https://www.gem5.org/documentation/)
- **Developer / API:** [gem5.org](https://www.gem5.org/)
- **Source:** [github.com/gem5/gem5](https://github.com/gem5/gem5)
- **SDKs & repos:** The standard architecture research simulator: CPU models, cache hierarchies, full-system boot
- **Downloadable / offline:** Online docs + learning-gem5 tutorial series
- *Note:* If you read an architecture paper with simulated results, it was probably gem5.

### QEMU

- **Docs:** [qemu.org/docs/master](https://www.qemu.org/docs/master/)
- **Developer / API:** [qemu.org](https://www.qemu.org/)
- **Source:** [github.com/qemu/qemu](https://github.com/qemu/qemu)
- **SDKs & repos:** Functional emulation and virtualization across every major ISA; TCG dynamic translation
- **Downloadable / offline:** Sphinx docs per release
- *Note:* Functional, not timing-accurate — know the difference before you cite numbers.

### Spike

- **Docs:** [github.com/riscv-software-src/riscv-isa-sim](https://github.com/riscv-software-src/riscv-isa-sim)
- **Source:** [github.com/riscv-software-src/riscv-isa-sim](https://github.com/riscv-software-src/riscv-isa-sim)
- **SDKs & repos:** The RISC-V golden reference ISA simulator
- **Downloadable / offline:** In-repo
- *Note:* What 'correct' means for RISC-V in practice.

### Verilator

- **Docs:** [verilator.org/guide/latest](https://verilator.org/guide/latest/)
- **Source:** [github.com/verilator/verilator](https://github.com/verilator/verilator)
- **SDKs & repos:** Compiles Verilog/SystemVerilog to fast C++ — the free path to cycle-accurate RTL simulation
- **Downloadable / offline:** Sphinx guide
- *Note:* Fast enough to boot Linux on an RTL model. Makes serious hardware work possible without licences.

### Ramulator 2

- **Docs:** [github.com/CMU-SAFARI/ramulator2](https://github.com/CMU-SAFARI/ramulator2)
- **Source:** [github.com/CMU-SAFARI/ramulator2](https://github.com/CMU-SAFARI/ramulator2)
- **SDKs & repos:** Cycle-accurate DRAM simulator covering modern standards
- **Downloadable / offline:** In-repo + papers
- *Note:* From Onur Mutlu's SAFARI group.

### DRAMsim3

- **Docs:** [github.com/umd-memsys/DRAMsim3](https://github.com/umd-memsys/DRAMsim3)
- **Source:** [github.com/umd-memsys/DRAMsim3](https://github.com/umd-memsys/DRAMsim3)
- **SDKs & repos:** Widely used DRAM timing and power model
- **Downloadable / offline:** In-repo

### CACTI

- **Docs:** [github.com/HewlettPackard/cacti](https://github.com/HewlettPackard/cacti)
- **Source:** [github.com/HewlettPackard/cacti](https://github.com/HewlettPackard/cacti)
- **SDKs & repos:** Cache and memory area/timing/power modelling
- **Downloadable / offline:** In-repo
- *Note:* The standard tool for 'how big and how slow would this cache be?'

### Gemmini

- **Docs:** [github.com/ucb-bar/gemmini](https://github.com/ucb-bar/gemmini)
- **Source:** [github.com/ucb-bar/gemmini](https://github.com/ucb-bar/gemmini)
- **SDKs & repos:** Systolic-array ML accelerator generator integrated with Chipyard
- **Downloadable / offline:** In-repo + papers
- *Note:* The accessible on-ramp to accelerator architecture.


## 4. Hardware description, synthesis & open EDA

### Chisel

- **Docs:** [chisel-lang.org](https://www.chisel-lang.org/)
- **Developer / API:** [chisel-lang.org/docs](https://www.chisel-lang.org/docs)
- **Source:** [github.com/chipsalliance/chisel](https://github.com/chipsalliance/chisel)
- **SDKs & repos:** Scala-embedded hardware construction language behind Rocket, BOOM and Chipyard
- **Downloadable / offline:** Online docs + bootcamp
- *Note:* Generators rather than instances — a genuinely different way to think about RTL.

### Yosys

- **Docs:** [yosyshq.net/yosys](https://yosyshq.net/yosys/)
- **Developer / API:** [yosyshq.readthedocs.io/projects/yosys](https://yosyshq.readthedocs.io/projects/yosys/)
- **Source:** [github.com/YosysHQ/yosys](https://github.com/YosysHQ/yosys)
- **SDKs & repos:** Open-source Verilog synthesis; the backbone of the open silicon toolchain
- **Downloadable / offline:** Sphinx manual

### OpenROAD

- **Docs:** [theopenroadproject.org](https://theopenroadproject.org/)
- **Developer / API:** [openroad.readthedocs.io](https://openroad.readthedocs.io/)
- **Source:** [github.com/The-OpenROAD-Project/OpenROAD](https://github.com/The-OpenROAD-Project/OpenROAD)
- **SDKs & repos:** Complete open RTL-to-GDSII place-and-route flow
- **Downloadable / offline:** Sphinx docs
- *Note:* Tapeout-capable, entirely open.

### OpenLane

- **Docs:** [github.com/The-OpenROAD-Project/OpenLane](https://github.com/The-OpenROAD-Project/OpenLane)
- **Source:** [github.com/The-OpenROAD-Project/OpenLane](https://github.com/The-OpenROAD-Project/OpenLane)
- **SDKs & repos:** Automated RTL-to-GDSII flow wrapping OpenROAD + Yosys
- **Downloadable / offline:** In-repo docs
- *Note:* The practical entry point to open silicon.

### SkyWater SKY130 PDK

- **Docs:** [skywater-pdk.readthedocs.io](https://skywater-pdk.readthedocs.io/)
- **Source:** [github.com/google/skywater-pdk](https://github.com/google/skywater-pdk)
- **SDKs & repos:** The first fully open process design kit — real, fabricable silicon
- **Downloadable / offline:** Sphinx docs
- *Note:* Combined with OpenLane and Efabless shuttles, you can actually tape out a chip.


## 5. Performance analysis & microarchitectural measurement

### Agner Fog's optimization manuals

- **Docs:** [agner.org/optimize](https://www.agner.org/optimize/)
- **SDKs & repos:** Instruction tables, microarchitecture guide, calling conventions, vector class library
- **Downloadable / offline:** Five free PDFs, continuously updated since the 1990s
- *Note:* The instruction tables and the microarchitecture manual are indispensable and have no official equivalent.

### uops.info

- **Docs:** [uops.info](https://uops.info/)
- **SDKs & repos:** Automatically measured latency, throughput and port usage for x86 instructions
- **Downloadable / offline:** Downloadable XML/HTML dataset
- *Note:* Where you go when the vendor manual is vague or wrong about instruction cost.

### llvm-mca

- **Docs:** [llvm.org/docs/CommandGuide/llvm-mca.html](https://llvm.org/docs/CommandGuide/llvm-mca.html)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** Static machine-code analyzer that predicts throughput from LLVM's scheduling models
- **Downloadable / offline:** LLVM docs
- *Note:* Fast way to reason about a hot loop without running it.

### perf

- **Docs:** [perf.wiki.kernel.org/index.php/Main_Page](https://perf.wiki.kernel.org/index.php/Main_Page)
- **Source:** [git.kernel.org](https://git.kernel.org/)
- **SDKs & repos:** Linux hardware performance counter interface
- **Downloadable / offline:** man pages + wiki

### Perf Ninja

- **Docs:** [github.com/dendibakh/perf-ninja](https://github.com/dendibakh/perf-ninja)
- **Developer / API:** [easyperf.net](https://easyperf.net/)
- **Source:** [github.com/dendibakh/perf-ninja](https://github.com/dendibakh/perf-ninja)
- **SDKs & repos:** Self-paced performance-optimization exercises with automated verification
- **Downloadable / offline:** Repo cloneable
- *Note:* Pairs with the free book 'Performance Analysis and Tuning on Modern CPUs'.

### Algorithmica HPC

- **Docs:** [en.algorithmica.org/hpc](https://en.algorithmica.org/hpc/)
- **SDKs & repos:** Free online book on modern hardware performance: caches, SIMD, branch prediction, pipelining
- **Downloadable / offline:** Online, printable
- *Note:* Exceptionally good and far too little known.


## 6. Reverse engineering, commentary & live tooling

### Compiler Explorer (godbolt)

- **Docs:** [godbolt.org](https://godbolt.org/)
- **Source:** [github.com/compiler-explorer/compiler-explorer](https://github.com/compiler-explorer/compiler-explorer)
- **SDKs & repos:** Compile any language with any compiler and see the assembly instantly; self-hostable
- **Downloadable / offline:** Entire site runs locally from the repo
- *Note:* The fastest feedback loop that exists for understanding what the machine actually does. Use it constantly.

### Intel Intrinsics Guide

- **Docs:** [intel.com/content/…](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html)
- **SDKs & repos:** Searchable reference for every x86 SIMD intrinsic with latency and throughput
- **Downloadable / offline:** Web application; data embedded in the page
- *Note:* 403s to bots, loads in a browser. Indispensable for SIMD work.

### Chips and Cheese

- **Docs:** [chipsandcheese.com](https://chipsandcheese.com/)
- **SDKs & repos:** Independent microarchitecture analysis with original microbenchmarks
- **Downloadable / offline:** Free articles
- *Note:* Currently the best independent source for measured details on new CPUs and GPUs that vendors do not publish.

### Real World Technologies

- **Docs:** [realworldtech.com](https://www.realworldtech.com/)
- **SDKs & repos:** David Kanter’s long-form microarchitecture analyses
- **Downloadable / offline:** Free archive
- *Note:* The archive of deep-dive articles on past architectures remains the best written material of its kind.

### OpenSBI

- **Docs:** [github.com/riscv-software-src/opensbi](https://github.com/riscv-software-src/opensbi)
- **Source:** [github.com/riscv-software-src/opensbi](https://github.com/riscv-software-src/opensbi)
- **SDKs & repos:** RISC-V Supervisor Binary Interface reference implementation
- **Downloadable / offline:** In-repo docs
- *Note:* The firmware layer between your core and an operating system. Needed the moment you try to boot Linux on your own design.

### LiteX

- **Docs:** [github.com/enjoy-digital/litex](https://github.com/enjoy-digital/litex)
- **Source:** [github.com/enjoy-digital/litex](https://github.com/enjoy-digital/litex)
- **SDKs & repos:** Python-based SoC builder supporting dozens of FPGA boards and soft cores
- **Downloadable / offline:** In-repo docs and wiki
- *Note:* The quickest practical route from an FPGA board to a working SoC running Linux.

### Amaranth HDL

- **Docs:** [amaranth-lang.org/docs/amaranth/latest](https://amaranth-lang.org/docs/amaranth/latest/)
- **Source:** [github.com/amaranth-lang/amaranth](https://github.com/amaranth-lang/amaranth)
- **SDKs & repos:** Python-embedded HDL, successor to nMigen
- **Downloadable / offline:** Sphinx docs
- *Note:* A gentler entry into generator-based hardware design than Chisel if you already write Python.

### cocotb

- **Docs:** [docs.cocotb.org](https://docs.cocotb.org/)
- **Source:** [github.com/cocotb/cocotb](https://github.com/cocotb/cocotb)
- **SDKs & repos:** Write RTL testbenches in Python against Verilator, Icarus or commercial simulators
- **Downloadable / offline:** Sphinx docs
- *Note:* Verification without learning SystemVerilog testbench constructs. Pairs well with Verilator.


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

### arXiv cs.AR (Hardware Architecture)

- **Docs:** [arxiv.org/list/cs.AR/recent](https://arxiv.org/list/cs.AR/recent)
- **SDKs & repos:** Daily preprints in computer architecture
- **Downloadable / offline:** Free
- *Note:* Lower volume than cs.LG; genuinely feasible to skim weekly.

### ACM SIGARCH

- **Docs:** [sigarch.org](https://www.sigarch.org/)
- **SDKs & repos:** The architecture special interest group; runs 'Computer Architecture Today'
- **Downloadable / offline:** Blog free; proceedings via ACM DL
- *Note:* The blog is the field's informal commentary channel — often where debates happen before they reach papers.

### Hot Chips

- **Docs:** [hotchips.org](https://hotchips.org/)
- **SDKs & repos:** Industry symposium where vendors present real shipping silicon
- **Downloadable / offline:** Slide decks and many talks posted free after each year
- *Note:* The only venue where you reliably get microarchitectural detail on products straight from the designers.

### NVIDIA Research

- **Docs:** [research.nvidia.com/publications](https://research.nvidia.com/publications)
- **SDKs & repos:** GPU architecture, interconnect, accelerators, graphics
- **Downloadable / offline:** Free PDFs
- *Note:* Read with the per-architecture whitepapers; the research papers explain the reasoning.

### Onur Mutlu's publications

- **Docs:** [people.inf.ethz.ch/omutlu](https://people.inf.ethz.ch/omutlu/)
- **SDKs & repos:** Memory systems, RowHammer, processing-in-memory
- **Downloadable / offline:** All papers free from the page
- *Note:* An entire subfield's output, all free, organised by topic, with matching lecture videos.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*22 resources across 5 topics.*


#### Build the whole stack yourself

- **[Nand2Tetris](https://www.nand2tetris.org/)** — From NAND gates to an OS and a compiler, in twelve projects. Free, self-contained, and the single best first course in this field.
- **[Computer Systems: A Programmer's Perspective (CS:APP)](https://csapp.cs.cmu.edu/)** — The textbook that connects C to the machine. Lab assignments (bomb lab, cache lab, attack lab) are public and excellent.
- **[CMU 15-213 Introduction to Computer Systems](https://www.cs.cmu.edu/~213/)** — The course CS:APP was written for. Slides and lab handouts public.
- **[MIT 6.004 Computation Structures](https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/)** — Full OCW materials from digital logic up to a working processor.


#### Architecture courses with public material

- **[Berkeley CS152 — Computer Architecture and Engineering](https://inst.eecs.berkeley.edu/~cs152/)** — Undergraduate pipelining, caches, and out-of-order execution. Slides public per semester.
- **[Berkeley CS252 — Graduate Computer Architecture](https://inst.eecs.berkeley.edu/~cs252/)** — The graduate follow-on, paper-driven.
- **[ETH Zürich Digital Design & Computer Architecture (Onur Mutlu)](https://safari.ethz.ch/digitaltechnik/spring2023/doku.php)** — Complete slide decks, labs and exams, all free.
- **[Onur Mutlu lecture videos](https://people.inf.ethz.ch/omutlu/lecture-videos.html)** — Years of full-length recorded architecture lectures. Probably the largest free architecture video archive anywhere.


#### Specifications to read early

- **[RISC-V unprivileged ISA spec](https://riscv.org/technical/specifications/)** — Start with RISC-V rather than x86. It is small, clean, and designed to be taught.
- **[RISC-V ISA manual source](https://github.com/riscv/riscv-isa-manual)** — Read the spec's git history when a design choice puzzles you.
- **[Intel SDM Volume 2 (instruction reference)](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)** — Reference, not reading. Learn to navigate it rather than to read it.
- **[Arm Architecture Reference Manual](https://developer.arm.com/documentation)** — Read the exception model and memory model chapters — those are where Arm differs most from x86.


#### First hands-on projects

- **[PicoRV32](https://github.com/YosysHQ/picorv32)** — Read a complete working CPU in one sitting, then modify it.
- **[Verilator](https://verilator.org/guide/latest/)** — Simulate your RTL for free, fast enough to be interesting.
- **[Spike (RISC-V reference sim)](https://github.com/riscv-software-src/riscv-isa-sim)** — Compare your implementation against the golden model.
- **[QEMU](https://www.qemu.org/docs/master/)** — Understand emulation before you tackle timing simulation.
- **[learning gem5](https://www.gem5.org/documentation/)** — Follow the 'Learning gem5' tutorial track before touching research configs.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*31 resources across 6 topics.*


#### Microarchitecture in depth

- **[BOOM out-of-order core](https://github.com/riscv-boom/riscv-boom)** — The clearest readable implementation of register renaming, issue queues and speculation.
- **[BOOM documentation](https://docs.boom-core.org/)** — Explains the microarchitecture before you dive into the Chisel.
- **[Rocket Chip](https://github.com/chipsalliance/rocket-chip)** — The in-order counterpart. Diff the two to isolate what OoO actually costs.
- **[CVA6](https://github.com/openhwgroup/cva6)** — Same class of core in SystemVerilog — useful if Chisel is the obstacle.
- **[Agner Fog microarchitecture manual](https://www.agner.org/optimize/)** — Per-generation detail on real Intel, AMD and VIA pipelines that vendors do not publish.
- **[uops.info](https://uops.info/)** — Measured ground truth for instruction cost.


#### Memory systems

- **[Ramulator 2](https://github.com/CMU-SAFARI/ramulator2)** — Model DRAM properly instead of assuming fixed latency.
- **[DRAMsim3](https://github.com/umd-memsys/DRAMsim3)** — Alternative DRAM model; cross-check results across both.
- **[CACTI](https://github.com/HewlettPackard/cacti)** — Put area and energy numbers on your cache design choices.
- **[Linux kernel memory-management docs](https://docs.kernel.org/)** — Where the architecture meets the OS: TLBs, huge pages, NUMA.


#### Build real silicon

- **[Chipyard](https://github.com/ucb-bar/chipyard)** — Integrate cores, accelerators and peripherals into a simulatable, synthesizable SoC.
- **[Chisel](https://www.chisel-lang.org/)** — The generator-based design approach the Berkeley stack is built on.
- **[Yosys](https://yosyshq.net/yosys/)** — Open synthesis.
- **[OpenROAD](https://theopenroadproject.org/)** — Open place and route, all the way to GDSII.
- **[OpenLane](https://github.com/The-OpenROAD-Project/OpenLane)** — The automated flow that ties it together.
- **[SkyWater SKY130 PDK](https://skywater-pdk.readthedocs.io/)** — A real, open process. Your design can actually be fabricated.
- **[OpenTitan](https://github.com/lowRISC/opentitan)** — Study this for verification methodology and documentation discipline, not just the design.


#### Accelerators & domain-specific architecture

- **[Gemmini](https://github.com/ucb-bar/gemmini)** — Systolic-array generator — the accessible route into ML accelerator design.
- **[CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/)** — The memory hierarchy and warp-execution chapters are real architecture documentation.
- **[CUDA samples](https://github.com/NVIDIA/cuda-samples)** — Reference kernels showing what the hardware rewards.
- **[Triton](https://triton-lang.org/main/index.html)** — Where compiler design and GPU architecture meet; see the PL/compilers index too.


#### Performance engineering

- **[Algorithmica HPC](https://en.algorithmica.org/hpc/)** — Free book: SIMD, cache-aware algorithms, branch prediction, with measurements throughout.
- **[Perf Ninja](https://github.com/dendibakh/perf-ninja)** — Graded optimization exercises against real hardware counters.
- **[easyperf](https://easyperf.net/)** — Companion blog and the free performance-tuning book.
- **[llvm-mca](https://llvm.org/docs/CommandGuide/llvm-mca.html)** — Static throughput analysis of your hot loop.
- **[Linux perf](https://perf.wiki.kernel.org/index.php/Main_Page)** — Counter-based measurement on real silicon.


#### Research venues

- **[ISCA](https://www.iscaconf.org/)** — The flagship architecture conference.
- **[MICRO](https://www.microarch.org/)** — Microarchitecture-focused; often the most readable of the four.
- **[ASPLOS](https://asplos-conference.org/)** — Where architecture, OS and languages intersect — the most cross-cutting venue.
- **[HPCA](https://hpca-conf.org/)** — High-performance architecture.
- **[gem5](https://github.com/gem5/gem5)** — Learn it if you intend to publish; most results in these venues are produced with it.


---

## If you only do three things

1. **Nand2Tetris** end to end. Twelve projects, and afterwards nothing in a computer is magic.
2. **Read PicoRV32** (~3000 lines of Verilog), then **BOOM**. The gap between them *is* modern microarchitecture.
3. **Agner Fog's manuals + uops.info**. The moment you need real instruction costs, nothing official is as good.

## Honest notes

- **Start with RISC-V, not x86.** The RISC-V spec is a few hundred readable pages; the Intel SDM is five thousand and assumes you already know the material.
- **The Arm ARM and a core's TRM are different documents.** Confusing them wastes a lot of time.
- **Open silicon is genuinely real now.** Yosys + OpenROAD + SKY130 is a complete, free, tapeout-capable flow. That was not true a few years ago.
- **Apple Silicon has the weakest public documentation** of any major architecture. The community reverse-engineering work is currently better than the vendor material.

---

## Related sections of this book

- [Computer Architecture](../arch/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
