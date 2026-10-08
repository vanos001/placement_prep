# Security Engineering Reference Library

This page is a verified index of primary sources for security engineering: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Standards and exposure feeds, fuzzers, SAST/SCA and secret scanners, supply-chain signing, web and API tooling, network and host defense, runtime and cloud security, identity and applied crypto, and the reverse-engineering bench — plus a two-track path from the PortSwigger Web Security Academy to reading Project Zero write-ups.

**81 entries** across 9 categories, plus **46 education & reference-implementation resources** (20 basic / 26 advanced).

Every link HTTP-verified on **2026-10-08**.

> `cwe.mitre.org` and `boringssl.googlesource.com` return 403 or an auth wall to automated clients but load normally in a browser. The same applies to `datatracker.ietf.org` (RFC 6749), the CISA KEV catalog page, and GitLab-hosted repositories such as AppArmor. The ACM Digital Library, in the research section below, behaves the same.

## Contents

- [1. Standards, vulnerability & exposure data](#1-standards-vulnerability--exposure-data) — 10
- [2. Fuzzing & dynamic testing](#2-fuzzing--dynamic-testing) — 8
- [3. SAST, SCA & secrets](#3-sast-sca--secrets) — 11
- [4. Supply chain & signing](#4-supply-chain--signing) — 8
- [5. Web & API attack & defense](#5-web--api-attack--defense) — 8
- [6. Network & infrastructure security](#6-network--infrastructure-security) — 7
- [7. Runtime, container & cloud security](#7-runtime-container--cloud-security) — 9
- [8. Identity, authN/authZ & applied crypto](#8-identity-authnauthz--applied-crypto) — 13
- [9. Reverse engineering, malware & forensics](#9-reverse-engineering-malware--forensics) — 7
- [Education & reference implementations](#education--reference-implementations) — 46 (20 basic / 26 advanced)
- [Research papers & open-access literature](#research-papers--open-access-literature) — 22


## 1. Standards, vulnerability & exposure data

### NIST NVD

- **Docs:** [nvd.nist.gov](https://nvd.nist.gov/)
- **Developer / API:** [nvd.nist.gov/developers](https://nvd.nist.gov/developers/)
- **SDKs & repos:** The curated, scored view of every CVE; JSON 2.0 is the current feed format
- **Downloadable / offline:** Vulnerability data feeds as JSON from [nvd.nist.gov/vuln/data-feeds](https://nvd.nist.gov/vuln/data-feeds); full API, free key available
- *Note:* NVD is CVE plus enrichment (CWE mapping, CVSS, CPE ranges). Its enrichment has had real backlogs, so tooling that assumed NVD analysis is current has had to learn to read CVE records directly — know which layer you are consuming.

### CVE Program

- **Docs:** [cve.org](https://www.cve.org/)
- **Source:** [github.com/CVEProject/cvelist](https://github.com/CVEProject/cvelist)
- **SDKs & repos:** CVE IDs are issued by CNAs and reserved/published through CVE Services; the record list itself is a git repository
- **Downloadable / offline:** The CVE List is cloneable from the cvelist repo; bulk downloads from cve.org
- *Note:* The authoritative registry — cve.org is the program site, individual records live at `cve.org/CVERecord/?id=...`. NVD adds the analysis layer on top.

### CWE (Common Weakness Enumeration)

- **Docs:** [cwe.mitre.org](https://cwe.mitre.org/)
- **Downloadable / offline:** The full list as XML/CSV/HTML from the site's data pages
- *Note:* The taxonomy of software weaknesses — what NVD maps findings to and what SAST tools classify against. `cwe.mitre.org` 403s some automated clients; fine in a browser.

### CAPEC (Common Attack Pattern Enumeration and Classification)

- **Docs:** [capec.mitre.org](https://capec.mitre.org/)
- **Downloadable / offline:** Attack-pattern library as XML/CSV from the site's data pages
- *Note:* CWE describes the weakness; CAPEC describes how attackers exploit it. Read them as two halves of one vocabulary.

### OWASP

- **Docs:** [owasp.org](https://owasp.org/)
- **Developer / API:** [owasp.org/Top10](https://owasp.org/Top10/)
- **Source:** [github.com/OWASP](https://github.com/OWASP)
- **SDKs & repos:** Hundreds of community projects; the Top 10 lists and the Cheat Sheet Series are the two most-cited artefacts
- **Downloadable / offline:** Everything is versioned in the org's repos; project pages export to PDF
- *Note:* A foundation, not a product. Quality varies by project; the Cheat Sheet Series is the consistently excellent part.

### OWASP ASVS

- **Docs:** [owasp.org/www-project-application-security-verification-standard](https://owasp.org/www-project-application-security-verification-standard/)
- **SDKs & repos:** The standard for verifying application security — levels 1-3, per-control requirements
- **Downloadable / offline:** The standard as PDF plus machine-readable checklists from the project page
- *Note:* The document you attach to a vendor contract. ASVS turns "is it secure?" into a numbered checklist someone can be held to.

### OWASP WSTG

- **Docs:** [owasp.org/www-project-web-security-testing-guide](https://owasp.org/www-project-web-security-testing-guide/)
- **SDKs & repos:** The standard methodology for testing web applications, test by test
- **Downloadable / offline:** PDF/EPUB built from the project repo
- *Note:* If a pentest report's methodology section references anything, it is this. Read the stable version.

### CIS Controls & Benchmarks

- **Docs:** [cisecurity.org/controls](https://www.cisecurity.org/controls/)
- **Downloadable / offline:** CIS Benchmarks (per-product hardening guides) as PDFs with free registration from [cisecurity.org/cis-benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- *Note:* The Controls are the 18 things to do first; the Benchmarks are how to configure each specific product. Nearly every compliance conversation starts here.

### MITRE ATT&CK

- **Docs:** [attack.mitre.org](https://attack.mitre.org/)
- **Source:** [github.com/mitre-attack/attack-stix-data](https://github.com/mitre-attack/attack-stix-data)
- **SDKs & repos:** The tactics/techniques matrix; the ATT&CK Navigator is the standard browsing layer
- **Downloadable / offline:** STIX/JSON bundles of the full matrix from the data repo
- *Note:* The shared vocabulary for adversary behaviour. Detection engineering starts when your alert names match technique IDs.

### CISA KEV

- **Docs:** [cisa.gov/known-exploited-vulnerabilities-catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog/)
- **Downloadable / offline:** The catalog as JSON/CSV feeds from the same page
- *Note:* CVSS says "severe"; KEV says "someone is using it". It is the only vulnerability list that should directly drive your patch SLA.


## 2. Fuzzing & dynamic testing

### AFL++

- **Docs:** [github.com/AFLplusplus/AFLplusplus](https://github.com/AFLplusplus/AFLplusplus)
- **Source:** [github.com/AFLplusplus/AFLplusplus](https://github.com/AFLplusplus/AFLplusplus)
- **SDKs & repos:** Coverage-guided file fuzzer; instrumentation via compiler plugins (afl-clang-fast); persistent mode
- **Downloadable / offline:** Clone and build; the in-repo docs/ directory is the manual
- *Note:* The maintained fork of AFL and still the first tool to reach for. Read `docs/README.md` top to bottom; it is a fuzzing education in itself.

### libFuzzer

- **Docs:** [llvm.org/docs/LibFuzzer.html](https://llvm.org/docs/LibFuzzer.html)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** In-process, coverage-guided fuzzing engine that ships with clang — no separate install
- **Downloadable / offline:** Ships with the compiler toolchain
- *Note:* Pairs with sanitizer builds (`-fsanitize=fuzzer,address`). The in-process model is what makes it fast — and what makes one crash kill the whole run.

### honggfuzz

- **Docs:** [github.com/google/honggfuzz](https://github.com/google/honggfuzz)
- **Source:** [github.com/google/honggfuzz](https://github.com/google/honggfuzz)
- **SDKs & repos:** Feedback-driven fuzzer with hardware-performance-counter feedback
- **Downloadable / offline:** Clone and build
- *Note:* Development has slowed; AFL++ and libFuzzer see more use. Still worth reading for its hardware-feedback approach.

### OSS-Fuzz

- **Docs:** [google.github.io/oss-fuzz](https://google.github.io/oss-fuzz/)
- **Source:** [github.com/google/oss-fuzz](https://github.com/google/oss-fuzz)
- **SDKs & repos:** Free continuous fuzzing for open-source projects; AFL++, libFuzzer and honggfuzz under the hood
- **Downloadable / offline:** Docker-based local reproduction; build scripts in-repo
- *Note:* Thousands of projects, public corpora and bug statistics. Reading a project's OSS-Fuzz integration shows you what real fuzz targets look like.

### Fuzzilli

- **Docs:** [github.com/googleprojectzero/Fuzzilli](https://github.com/googleprojectzero/Fuzzilli)
- **Source:** [github.com/googleprojectzero/Fuzzilli](https://github.com/googleprojectzero/Fuzzilli)
- **SDKs & repos:** Coverage-guided JavaScript engine fuzzer built on a custom IR (FuzzIL)
- **Downloadable / offline:** Clone and build; Swift toolchain required
- *Note:* Found dozens of JIT and interpreter bugs in V8, SpiderMonkey and JavaScriptCore. The design write-ups explain why naive JS fuzzing fails.

### Jazzer

- **Docs:** [github.com/CodeIntelligenceTesting/jazzer](https://github.com/CodeIntelligenceTesting/jazzer)
- **Source:** [github.com/CodeIntelligenceTesting/jazzer](https://github.com/CodeIntelligenceTesting/jazzer)
- **SDKs & repos:** libFuzzer for the JVM; fuzz targets are ordinary Java methods; runs in OSS-Fuzz
- **Downloadable / offline:** Maven/Gradle artifact; Bazel rules
- *Note:* The reason most Java projects take fuzzing seriously. Hook-based coverage, so you do not instrument bytecode by hand.

### Atheris

- **Docs:** [github.com/google/atheris](https://github.com/google/atheris)
- **Source:** [github.com/google/atheris](https://github.com/google/atheris)
- **SDKs & repos:** Fuzzing for Python; covers native extensions via sanitizer instrumentation
- **Downloadable / offline:** pip-installable
- *Note:* Catches both Python-level exception bugs and memory corruption in C extensions — the latter is the actual reason to run it.

### cargo-fuzz

- **Docs:** [github.com/rust-fuzz/cargo-fuzz](https://github.com/rust-fuzz/cargo-fuzz)
- **Source:** [github.com/rust-fuzz/cargo-fuzz](https://github.com/rust-fuzz/cargo-fuzz)
- **SDKs & repos:** libFuzzer driver for Rust; `cargo fuzz init/add/run` manages targets, corpus and artifacts
- **Downloadable / offline:** cargo-installable
- *Note:* Aim it at `unsafe` blocks and parsers. Even a memory-safe language needs fuzzing at every FFI boundary.


## 3. SAST, SCA & secrets

### GitHub CodeQL

- **Docs:** [codeql.github.com](https://codeql.github.com/)
- **Developer / API:** [codeql.github.com/docs](https://codeql.github.com/docs/)
- **Source:** [github.com/github/codeql](https://github.com/github/codeql)
- **SDKs & repos:** Queries are logic programs over a relational database of your code; the ql/ tree is a library of vulnerability classes
- **Downloadable / offline:** CLI free for research and open source; query packs distributed via the GitHub registry
- *Note:* Read a query for a CVE class you already know and you will understand the vulnerability better than most write-ups manage.

### Semgrep

- **Docs:** [semgrep.dev/docs](https://semgrep.dev/docs/)
- **Source:** [github.com/semgrep/semgrep](https://github.com/semgrep/semgrep)
- **SDKs & repos:** Pattern-based SAST whose rules are short enough to read on the spot; community rules registry
- **Downloadable / offline:** pip/brew-installable CLI; runs offline
- *Note:* The lowest-friction way to write your own organizational rules. Start with `--config auto`, then replace it with rules you actually own.

### Bandit

- **Docs:** [bandit.readthedocs.io](https://bandit.readthedocs.io/en/latest/)
- **Source:** [github.com/PyCQA/bandit](https://github.com/PyCQA/bandit)
- **SDKs & repos:** AST-based security linter for Python
- **Downloadable / offline:** pip-installable
- *Note:* Modest but honest. Its findings list doubles as a syllabus of Python-specific footguns.

### Brakeman

- **Docs:** [brakemanscanner.org](https://brakemanscanner.org/)
- **Source:** [github.com/presidentbeef/brakeman](https://github.com/presidentbeef/brakeman)
- **SDKs & repos:** Static analysis purpose-built for Rails; does not need to boot the application
- **Downloadable / offline:** gem-installable
- *Note:* One of the few SAST tools tuned to a single framework's idioms, and better for it.

### FindSecBugs

- **Docs:** [find-sec-bugs.github.io](https://find-sec-bugs.github.io/)
- **Source:** [github.com/find-sec-bugs/find-sec-bugs](https://github.com/find-sec-bugs/find-sec-bugs)
- **SDKs & repos:** SpotBugs plugin doing taint analysis over Java bytecode; 100+ detector types
- **Downloadable / offline:** Maven/Gradle plugin
- *Note:* The default answer for Java SAST before CodeQL; still the easiest to wire into an existing build.

### Gitleaks

- **Docs:** [github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)
- **Source:** [github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks)
- **SDKs & repos:** Secret scanner for git history, working trees and streams; TOML rule format
- **Downloadable / offline:** Single static binary
- *Note:* Put it in pre-receive hooks and CI. Rotating a leaked credential costs more than every scanner on this page combined.

### TruffleHog

- **Docs:** [github.com/trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog)
- **Source:** [github.com/trufflesecurity/trufflehog](https://github.com/trufflesecurity/trufflehog)
- **SDKs & repos:** 800+ credential detectors, most of which verify whether the secret still works
- **Downloadable / offline:** Single binary; Docker image
- *Note:* Verification is the differentiator — a "possible key" you can confirm valid is a different incident entirely.

### Trivy

- **Docs:** [trivy.dev](https://trivy.dev/)
- **Source:** [github.com/aquasecurity/trivy](https://github.com/aquasecurity/trivy)
- **SDKs & repos:** One scanner for container images, filesystems, git repos, IaC and secrets; SBOM generation built in
- **Downloadable / offline:** Single binary; offline vulnerability DB download supported
- *Note:* The pragmatic default: one tool, `trivy image/fs/config`, done. Depth varies by ecosystem; breadth is unmatched.

### Grype & Syft

- **Docs:** [github.com/anchore/grype](https://github.com/anchore/grype)
- **Source:** [github.com/anchore/grype](https://github.com/anchore/grype)
- **SDKs & repos:** Syft ([github.com/anchore/syft](https://github.com/anchore/syft)) builds the SBOM; Grype matches it against vulnerability feeds
- **Downloadable / offline:** Single static binaries for both
- *Note:* The SBOM-first pipeline in two commands: `syft` then `grype`. Understanding why the two are separate teaches you what an SBOM actually is.

### OSV-Scanner

- **Docs:** [google.github.io/osv-scanner](https://google.github.io/osv-scanner/)
- **Source:** [github.com/google/osv-scanner](https://github.com/google/osv-scanner)
- **SDKs & repos:** Queries the OSV database ([osv.dev](https://osv.dev/)) with lockfile-aware version resolution
- **Downloadable / offline:** Binary releases; the OSV API and data dumps are free
- *Note:* Resolves transitive dependencies instead of pattern-matching filenames, which is where most other scanners quietly go wrong.

### Dependency-Track

- **Docs:** [dependencytrack.org](https://dependencytrack.org/)
- **Source:** [github.com/DependencyTrack/dependency-track](https://github.com/DependencyTrack/dependency-track)
- **SDKs & repos:** OWASP project; consumes CycloneDX SBOMs continuously and tracks risk over time
- **Downloadable / offline:** Docker deployment; REST API
- *Note:* This is the "keep the inventory current" half of SCA. One-off scans are trivia; a tracked SBOM is a capability.


## 4. Supply chain & signing

### Sigstore

- **Docs:** [sigstore.dev](https://www.sigstore.dev/)
- **Source:** [github.com/sigstore](https://github.com/sigstore)
- **SDKs & repos:** Keyless signing backed by Fulcio (certificate authority) and Rekor (transparency log); adopted by npm, PyPI and GitHub
- **Downloadable / offline:** CLI clients per platform
- *Note:* The bet: certificates short-lived like TLS, identities tied to OIDC, everything logged publicly. Read the trust specification, not just the README.

### cosign

- **Docs:** [docs.sigstore.dev](https://docs.sigstore.dev/)
- **Source:** [github.com/sigstore/cosign](https://github.com/sigstore/cosign)
- **SDKs & repos:** `cosign sign` / `cosign verify` for containers and blobs; integrates with Kubernetes admission
- **Downloadable / offline:** Single binary
- *Note:* `cosign verify` in an admission controller is the shortest path from supply-chain theory to enforcement.

### in-toto

- **Docs:** [in-toto.io](https://in-toto.io/)
- **Source:** [github.com/in-toto/in-toto](https://github.com/in-toto/in-toto)
- **SDKs & repos:** Signed attestations about each step of a software pipeline; the layout file is the policy
- **Downloadable / offline:** Python reference implementation; SLSA generators reuse the spec
- *Note:* "Who ran what, on which input, producing which artifact" — answered cryptographically instead of by trusting CI folklore.

### SLSA

- **Docs:** [slsa.dev](https://slsa.dev/)
- **Source:** [github.com/slsa-framework/slsa](https://github.com/slsa-framework/slsa)
- **SDKs & repos:** Build-platform requirements in levels; provenance-generating GitHub Actions
- **Downloadable / offline:** The specification is a static site, freely readable
- *Note:* The framework for answering "did this artifact come from where it claims?". Start at the threat-model page; the levels only make sense after it.

### TUF (The Update Framework)

- **Docs:** [theupdateframework.io](https://theupdateframework.io/)
- **Source:** [github.com/theupdateframework/python-tuf](https://github.com/theupdateframework/python-tuf)
- **SDKs & repos:** Metadata format and reference implementation; the specification lives at [theupdateframework.io/specification](https://theupdateframework.io/specification/)
- **Downloadable / offline:** Specification on the site; reference implementation in-repo
- *Note:* Designed against key compromise, rollback and freeze attacks. Update systems you build in an afternoon have none of these properties; TUF is the checklist.

### Notation (Notary Project)

- **Docs:** [notaryproject.dev](https://notaryproject.dev/)
- **Source:** [github.com/notaryproject/notation](https://github.com/notaryproject/notation)
- **SDKs & repos:** `notation sign/verify` for OCI artifacts; plugin model for key stores (KMS, HSM)
- **Downloadable / offline:** CLI releases
- *Note:* The Notary-v2 lineage that became the OCI signing approach most registries now implement. The alternative to Sigstore when you want key-based, not keyless.

### SPIFFE / SPIRE

- **Docs:** [spiffe.io](https://spiffe.io/)
- **Source:** [github.com/spiffe/spire](https://github.com/spiffe/spire)
- **SDKs & repos:** Workload identity via SVIDs (SPIFFE Verifiable Identity Documents); SPIRE is the reference node/workload-attestation runtime
- **Downloadable / offline:** The specification documents are static and freely readable
- *Note:* The zero-trust answer to service credentials: no shared secrets, identities attested from the platform up. mTLS with actual attestation behind it.

### OpenSSF Scorecard

- **Docs:** [github.com/ossf/scorecard](https://github.com/ossf/scorecard)
- **Source:** [github.com/ossf/scorecard](https://github.com/ossf/scorecard)
- **SDKs & repos:** Automated supply-chain posture checks on a repository (branch protection, pinned dependencies, token permissions); public results for major projects
- **Downloadable / offline:** Runs locally against any repo
- *Note:* The checks list doubles as a review checklist for your own repositories — that alone is worth the install.


## 5. Web & API attack & defense

### OWASP ZAP

- **Docs:** [zaproxy.org](https://www.zaproxy.org/)
- **Source:** [github.com/zaproxy/zaproxy](https://github.com/zaproxy/zaproxy)
- **SDKs & repos:** Interception proxy + active scanner; scriptable via the ZAP API; add-on marketplace
- **Downloadable / offline:** Desktop releases; Docker images for CI scanning
- *Note:* The free DAST that runs in CI. Slower and noisier than Burp's scanner; infinitely cheaper and scriptable.

### Burp Suite Community

- **Docs:** [portswigger.net/burp](https://portswigger.net/burp/)
- **Downloadable / offline:** Free Community Edition download from the site
- *Note:* Community lacks the automated scanner; the proxy, Repeater and the act of reading raw requests are the actual education. The Pro edition is what professionals run at work.

### PortSwigger Web Security Academy

- **Docs:** [portswigger.net/web-security](https://portswigger.net/web-security/)
- **Downloadable / offline:** All materials free; labs run in hosted environments
- *Note:* The best free hands-on web security curriculum in existence, maintained by the Burp vendors. If you only use one resource on this page, use this one.

### Nuclei

- **Docs:** [github.com/projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei)
- **Source:** [github.com/projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei)
- **SDKs & repos:** Template-driven scanner; thousands of community templates in [nuclei-templates](https://github.com/projectdiscovery/nuclei-templates)
- **Downloadable / offline:** Single binary; templates update via the project's tooling
- *Note:* YAML templates make "check for this specific CVE" a file you can diff and review. That reviewability is the whole point.

### ffuf

- **Docs:** [github.com/ffuf/ffuf](https://github.com/ffuf/ffuf)
- **Source:** [github.com/ffuf/ffuf](https://github.com/ffuf/ffuf)
- **SDKs & repos:** Fast web fuzzer for directories, parameters, headers and virtual hosts
- **Downloadable / offline:** Single Go binary
- *Note:* The successor to dirb/gobuster in most toolkits. Learning to filter on response size and status is the actual skill.

### sqlmap

- **Docs:** [sqlmap.org](https://sqlmap.org/)
- **Source:** [github.com/sqlmapproject/sqlmap](https://github.com/sqlmapproject/sqlmap)
- **SDKs & repos:** Automated SQL injection detection and exploitation; supports every mainstream DBMS
- **Downloadable / offline:** Clone or download a release; Python
- *Note:* Ancient-looking, still effective, and unforgiving of careless use — it fires real payloads. Authorized targets only.

### JWT (jwt.io)

- **Docs:** [jwt.io](https://jwt.io/)
- **Developer / API:** [jwt.io/libraries](https://jwt.io/libraries)
- **SDKs & repos:** The spec is RFC 7519; jwt.io maintains the library index and the famous debugger
- *Note:* The classic vulnerabilities (`alg: none`, algorithm confusion, `kid` injection) are library and integration bugs. Pick a maintained library and pin the expected algorithm server-side.

### OWASP API Security Top 10

- **Docs:** [owasp.org/API-Security](https://owasp.org/API-Security/)
- **SDKs & repos:** BOLA, broken authentication, SSRF and friends, ranked for API-shaped systems
- **Downloadable / offline:** PDF and JSON from the project page
- *Note:* Read alongside the OWASP Top 10, not instead of it — APIs fail differently, and BOLA is the classic one the Web Top 10 undersells.


## 6. Network & infrastructure security

### Nmap

- **Docs:** [nmap.org](https://nmap.org/)
- **Developer / API:** [nmap.org/book](https://nmap.org/book/)
- **Source:** [github.com/nmap/nmap](https://github.com/nmap/nmap)
- **SDKs & repos:** NSE scripting engine with hundreds of bundled scripts; Zenmap GUI
- **Downloadable / offline:** The official book is free online; installers for every platform
- *Note:* Scanning well is a skill: timing templates, scan types and NSE. The free book is genuinely good.

### tcpdump

- **Docs:** [tcpdump.org](https://www.tcpdump.org/)
- **Source:** [github.com/the-tcpdump-group/tcpdump](https://github.com/the-tcpdump-group/tcpdump)
- **SDKs & repos:** libpcap's reference consumer; its filter syntax is the one every downstream tool copies
- **Downloadable / offline:** Man page and FAQ on the site; present on every Unix
- *Note:* The lingua franca of packet capture. If you can write `tcpdump -i any 'tcp port 443'` from memory, Wireshark displays become trivial.

### CrowdSec

- **Docs:** [docs.crowdsec.net](https://docs.crowdsec.net/)
- **Source:** [github.com/crowdsecurity/crowdsec](https://github.com/crowdsecurity/crowdsec)
- **SDKs & repos:** Log-analysis agent + remediation components; crowdsourced blocklist signals
- **Downloadable / offline:** Packages and Docker images; a hub of parser/scenario collections
- *Note:* fail2ban's modern sibling: local decisions plus shared reputation. Reading its scenarios teaches detection-as-code.

### fail2ban

- **Docs:** [fail2ban.org](https://www.fail2ban.org/)
- **Source:** [github.com/fail2ban/fail2ban](https://github.com/fail2ban/fail2ban)
- **SDKs & repos:** Log-watching daemon that bans IPs via firewall rules; Python
- **Downloadable / offline:** Packaged in every distribution
- *Note:* Still the default on every VPS for a reason. The jail/filter model is crude, transparent and easy to reason about.

### OpenSCAP

- **Docs:** [open-scap.org](https://www.open-scap.org/)
- **Source:** [github.com/OpenSCAP/openscap](https://github.com/OpenSCAP/openscap)
- **SDKs & repos:** The `oscap` CLI evaluating XCCDF/OVAL content; SCAP Workbench GUI
- **Downloadable / offline:** Ships in RHEL/Fedora; content packages per platform
- *Note:* The bridge between CIS/STIG hardening PDFs and machine-checkable reality. Evaluate, remediate, then generate the report auditors want.

### Wazuh

- **Docs:** [documentation.wazuh.com](https://documentation.wazuh.com/)
- **Source:** [github.com/wazuh/wazuh](https://github.com/wazuh/wazuh)
- **SDKs & repos:** Open-source SIEM/XDR on OpenSearch; agents for every OS; FIM, vulnerability detection, log triage
- **Downloadable / offline:** All-in-one Docker deployment; OVA image
- *Note:* The free baseline for "we need a SIEM". Noisy out of the box — tuning it is the actual exercise.

### osquery

- **Docs:** [osquery.io](https://www.osquery.io/)
- **Source:** [github.com/osquery/osquery](https://github.com/osquery/osquery)
- **SDKs & repos:** SQL over your operating system — processes, sockets, packages and users as tables; Fleet (fleetdm.com) for fleet management
- **Downloadable / offline:** Packages for all platforms
- *Note:* `SELECT pid, name FROM processes WHERE ...` changes how you think about endpoint state. The schema is the documentation.


## 7. Runtime, container & cloud security

### Falco

- **Docs:** [falco.org](https://falco.org/)
- **Source:** [github.com/falcosecurity/falco](https://github.com/falcosecurity/falco)
- **SDKs & repos:** CNCF project; syscall-level rule engine with a small rules language; modern eBPF driver
- **Downloadable / offline:** Packages, Helm chart, Docker images
- *Note:* The default open-source runtime threat detector. Rules read like "spawned process" + "parent is shell" — readable is why it gets adopted.

### Tetragon

- **Docs:** [tetragon.io](https://tetragon.io/)
- **Source:** [github.com/cilium/tetragon](https://github.com/cilium/tetragon)
- **SDKs & repos:** eBPF-based security tracing and enforcement from the Cilium project; policies as Kubernetes CRDs
- **Downloadable / offline:** Helm deployment; docs online
- *Note:* Where Falco detects, Tetragon can enforce — policy applied at the syscall, process blocked in place. Read a TracingPolicy CRD; it is the whole design.

### AppArmor

- **Docs:** [apparmor.net](https://apparmor.net/)
- **Source:** [gitlab.com/apparmor/apparmor](https://gitlab.com/apparmor/apparmor)
- **SDKs & repos:** Path-based LSM; profiles compiled into kernel-enforced policy; the Ubuntu default
- **Downloadable / offline:** Userspace tools packaged per distribution
- *Note:* Easier to adopt than SELinux, weaker at scale. Kubernetes has supported it for years and most people never turn it on — check yours.

### SELinux

- **Docs:** [docs.fedoraproject.org — SELinux](https://docs.fedoraproject.org/en-US/quick-docs/selinux/)
- **Source:** [github.com/SELinuxProject/selinux](https://github.com/SELinuxProject/selinux)
- **SDKs & repos:** Type-enforcement LSM; labels on everything, allow rules between types; userspace tools (`semanage`, `sealert`, `ausearch`)
- **Downloadable / offline:** Kernel documentation under `Documentation/admin-guide/LSM/`; userspace in-repo
- *Note:* RHEL-family containers are genuinely sandboxed because of it. The learning curve is labels, not rules — draw the type graph first.

### Linux Audit (auditd)

- **Source:** [github.com/linux-audit/audit-userspace](https://github.com/linux-audit/audit-userspace)
- **SDKs & repos:** Kernel audit subsystem + userspace (`auditd`, `auditctl`, `ausearch`, `aureport`)
- **Downloadable / offline:** Packaged everywhere; the documentation is the man pages (`auditd(8)`, `audit.rules(7)`) and your distribution's security guide
- *Note:* Listed by name because there is no documentation portal to link — and because "what did that process actually do" is a question auditd answers and everything else infers.

### kube-bench

- **Docs:** [github.com/aquasecurity/kube-bench](https://github.com/aquasecurity/kube-bench)
- **Source:** [github.com/aquasecurity/kube-bench](https://github.com/aquasecurity/kube-bench)
- **SDKs & repos:** Implements the CIS Kubernetes Benchmark as runnable Go tests per node role
- **Downloadable / offline:** Single binary; container image; Job manifests
- *Note:* Run it against any cluster you inherit. The failed checks are a prioritized hardening backlog you did not have to write.

### kube-hunter

- **Docs:** [github.com/aquasecurity/kube-hunter](https://github.com/aquasecurity/kube-hunter)
- **Source:** [github.com/aquasecurity/kube-hunter](https://github.com/aquasecurity/kube-hunter)
- **SDKs & repos:** External and internal cluster attack-surface scanner; passive and active modes
- **Downloadable / offline:** Container image; runs as a pod
- *Note:* Run it from outside first — what an attacker sees is usually more than the owner expects.

### Checkov

- **Docs:** [checkov.io](https://www.checkov.io/)
- **Source:** [github.com/bridgecrewio/checkov](https://github.com/bridgecrewio/checkov)
- **SDKs & repos:** Misconfiguration scanner for Terraform, CloudFormation, Kubernetes, Helm and more; policies in Python or YAML
- **Downloadable / offline:** pip-installable; pre-commit and CI integrations
- *Note:* The point is not the scanner — it is that "public S3 bucket" becomes a failing test before the PR merges.

### Prowler

- **Docs:** [github.com/prowler-cloud/prowler](https://github.com/prowler-cloud/prowler)
- **Source:** [github.com/prowler-cloud/prowler](https://github.com/prowler-cloud/prowler)
- **SDKs & repos:** Multi-cloud posture assessment (AWS/Azure/GCP) implementing CIS and other frameworks; documentation site at docs.prowler.com
- **Downloadable / offline:** pip/Docker; runs with read-only credentials
- *Note:* The open-source answer to a CSPM subscription. The first run on any cloud account is always educational.


## 8. Identity, authN/authZ & applied crypto

### Keycloak

- **Docs:** [keycloak.org/documentation](https://www.keycloak.org/documentation)
- **Source:** [github.com/keycloak/keycloak](https://github.com/keycloak/keycloak)
- **SDKs & repos:** OIDC and SAML identity provider; admin REST API; SPI extensions; themes
- **Downloadable / offline:** Container-first deployment; docs per major version
- *Note:* The default open-source IAM. Standing it up is an afternoon; understanding realms, clients and mappers properly is what interviews probe.

### Ory

- **Docs:** [ory.sh/docs](https://www.ory.sh/docs)
- **Source:** [github.com/ory](https://github.com/ory)
- **SDKs & repos:** Composable identity stack in Go: Kratos (identity), Hydra (OAuth2/OIDC server), Keto (permissions), Oathkeeper (proxy)
- **Downloadable / offline:** Docker images; each service standalone
- *Note:* For when one monolithic IdP is the wrong shape. Hydra alone is the cleanest open-source OAuth2 server to read.

### Dex

- **Docs:** [dexidp.io](https://dexidp.io/)
- **Source:** [github.com/dexidp/dex](https://github.com/dexidp/dex)
- **SDKs & repos:** Federated OIDC provider — LDAP, GitHub, Google, static passwords in; one OIDC client contract out
- **Downloadable / offline:** Single binary; Helm chart
- *Note:* The standard "make Kubernetes authenticate against the corporate IdP" glue. Small enough to read the connectors.

### OAuth 2.0 (RFC 6749)

- **Docs:** [datatracker.ietf.org/doc/html/rfc6749](https://datatracker.ietf.org/doc/html/rfc6749)
- **Downloadable / offline:** Text/HTML/PDF from [rfc-editor.org](https://www.rfc-editor.org/rfc/rfc6749)
- *Note:* Read 6749 (framework), 6750 (bearer tokens), 7636 (PKCE) — and then the OAuth Security Best Current Practice, which quietly deprecates half of what the original RFC permits. Authorization-code-with-PKCE is the only flow to default to.

### OpenID Connect

- **Docs:** [openid.net/developers/how-connect-works](https://openid.net/developers/how-connect-works/)
- **Downloadable / offline:** The OIDC specifications are free on openid.net
- *Note:* OAuth says "access the resource"; OIDC adds "and who is the user" via the ID token. If a login page calls itself OAuth, it is OIDC underneath or it is wrong.

### FIDO2 / WebAuthn

- **Docs:** [webauthn.guide](https://webauthn.guide/)
- **Developer / API:** [w3.org/TR/webauthn](https://www.w3.org/TR/webauthn/)
- **SDKs & repos:** Browser API + CTAP authenticators; server libraries for every platform
- **Downloadable / offline:** W3C spec free online
- *Note:* Phishing-resistant by construction: origin binding kills credential forwarding. The guide is the fastest read; the spec answers the "actually, how" questions.

### libsodium

- **Docs:** [doc.libsodium.org](https://doc.libsodium.org/)
- **Source:** [github.com/jedisct1/libsodium](https://github.com/jedisct1/libsodium)
- **SDKs & repos:** Portable fork of NaCl; bindings in every language
- **Downloadable / offline:** Full documentation online; source builds everywhere
- *Note:* If you are choosing between AES and ChaCha20 by hand, you have already failed the API-design test libsodium passed for you. High-level constructs first, primitives never.

### OpenSSL

- **Docs:** [docs.openssl.org](https://docs.openssl.org/)
- **Source:** [github.com/openssl/openssl](https://github.com/openssl/openssl)
- **SDKs & repos:** The `openssl` CLI (x509, s_client, genpkey); libcrypto/libssl; the providers model since 3.0
- **Downloadable / offline:** Man pages; the CLI is on every system you will ever SSH into
- *Note:* Installed everywhere, misused everywhere. `openssl s_client -connect host:443` is still the fastest TLS reality check.

### BoringSSL

- **Docs:** [boringssl.googlesource.com/boringssl](https://boringssl.googlesource.com/boringssl/)
- **Source:** [boringssl.googlesource.com/boringssl](https://boringssl.googlesource.com/boringssl/)
- **SDKs & repos:** Google's OpenSSL fork used by Chrome and Chromium; no versioned releases, no stable API
- **Downloadable / offline:** Git checkout; documentation minimal
- *Note:* `googlesource.com` rejects some automated clients; loads normally in a browser. Read it to see what a hardened, de-featured crypto library looks like.

### RustCrypto

- **Docs:** [github.com/RustCrypto](https://github.com/RustCrypto)
- **Source:** [github.com/RustCrypto](https://github.com/RustCrypto)
- **SDKs & repos:** Pure-Rust crates per algorithm: `sha2`, `aes-gcm`, `chacha20poly1305`, `rsa`, the elliptic-curve family
- **Downloadable / offline:** crates.io; docs.rs per crate
- *Note:* The interesting engineering is in the audited cores and constant-time discipline. Use `argon2` for passwords, not a bare hash — the repos say so; believe them.

### Google Tink

- **Docs:** [developers.google.com/tink](https://developers.google.com/tink)
- **Source:** [github.com/tink-crypto](https://github.com/tink-crypto)
- **SDKs & repos:** Per-language libraries (Java, C++, Go, Python) with key management as a first-class concept; rotation built into the API
- **Downloadable / offline:** Maven/PyPI/npm artifacts
- *Note:* The library that treats key rotation as a type-system concern. Read the crypto-configuration rationale even if you never ship it.

### age

- **Docs:** [age-encryption.org](https://age-encryption.org/)
- **Source:** [github.com/FiloSottile/age](https://github.com/FiloSottile/age)
- **SDKs & repos:** Simple, modern file encryption; recipients (keys, ssh keys, plugins) compose into one file format; spec on the site
- **Downloadable / offline:** Single binary; spec as Internet-Draft
- *Note:* What PGP should have been for files: one format, no web of trust, no algorithm negotiation. Use it before you need it.

### SOPS

- **Docs:** [github.com/getsops/sops](https://github.com/getsops/sops)
- **Source:** [github.com/getsops/sops](https://github.com/getsops/sops)
- **SDKs & repos:** Encrypts values in YAML/JSON/ENV files while keeping keys readable; AWS/GCP/Azure KMS, age and Vault backends
- **Downloadable / offline:** Single binary; editor plugins
- *Note:* The pragmatic GitOps secrets answer: secrets live in the repo, encrypted, and diffs stay readable. Mind the rename — it moved from Mozilla to getsops.


## 9. Reverse engineering, malware & forensics

### Ghidra

- **Docs:** [ghidra-sre.org](https://ghidra-sre.org/)
- **Source:** [github.com/NationalSecurityAgency/ghidra](https://github.com/NationalSecurityAgency/ghidra)
- **SDKs & repos:** NSA's open RE platform; decompiler for many architectures; scripting in Java and Python; headless analyzer
- **Downloadable / offline:** Release binaries include full offline documentation
- *Note:* The free IDA. Decompiler output plus version tracking makes whole malware families tractable without a commercial license.

### radare2

- **Docs:** [book.rada.re](https://book.rada.re/) — the radare2 book
- **Source:** [github.com/radareorg/radare2](https://github.com/radareorg/radare2)
- **SDKs & repos:** Unix-style RE toolkit: disassemble, patch, diff, debug, forensics; `r2` scripting and pipeability
- **Downloadable / offline:** Builds everywhere; the radare2 book is free online
- *Note:* Steep, idiosyncratic, extremely powerful. Learn `aaa`, `pdf` and `axt` and you can survive; the rest arrives by need.

### Cutter

- **Docs:** [cutter.re](https://cutter.re/)
- **Source:** [github.com/rizinorg/cutter](https://github.com/rizinorg/cutter)
- **SDKs & repos:** Qt GUI for rizin (the radare2 fork); decompiler plugins; plugin API
- **Downloadable / offline:** Installers and AppImages
- *Note:* The friendliest entry into binary analysis. Start here; drop to the `r2`/`rz` CLI when the GUI gets in the way.

### YARA

- **Docs:** [virustotal.github.io/yara](https://virustotal.github.io/yara/)
- **Source:** [github.com/VirusTotal/yara](https://github.com/VirusTotal/yara)
- **SDKs & repos:** Pattern-matching rules for identifying and classifying malware; the de-facto industry rule format; large public rule collections
- **Downloadable / offline:** Single binary; libyara for embedding
- *Note:* Writing three rules against real samples teaches strings, PE modules and conditions faster than any tutorial. False positives are the actual lesson.

### Volatility 3

- **Docs:** [volatility3.readthedocs.io](https://volatility3.readthedocs.io/)
- **Source:** [github.com/volatilityfoundation/volatility3](https://github.com/volatilityfoundation/volatility3)
- **SDKs & repos:** Memory forensics framework; symbol tables per kernel build; plugins for process, network and malware analysis
- **Downloadable / offline:** pip-installable; framework and plugins in-repo
- *Note:* RAM never lies about what ran. Running `windows.pslist` on a memory image you captured yourself is the fastest forensics lesson available.

### capa

- **Docs:** [github.com/mandiant/capa](https://github.com/mandiant/capa)
- **Source:** [github.com/mandiant/capa](https://github.com/mandiant/capa)
- **SDKs & repos:** Detects capabilities in executables against thousands of rules ([capa-rules](https://github.com/mandiant/capa-rules)); Ghidra and IDA plugins
- **Downloadable / offline:** Single binary; rules database in-repo
- *Note:* The polite way to start malware triage: ask capa "what can this do?" before reversing anything by hand.

### Executable formats: ELF & PE

- **Docs:** ELF — [man7.org elf(5)](https://man7.org/linux/man-pages/man5/elf.5.html); PE — [learn.microsoft.com PE format](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
- **Downloadable / offline:** Both free online; the System V ABI ELF archives are hosted at refspecs.linuxfoundation.org
- *Note:* Read both once. Every loader, packer and memory-forensics plugin is an opinion about these two documents, and Ghidra's loaders encode them literally.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about exploiting, defending and reading real research. Everything listed is free or has a meaningful free tier.


### Basic

*20 resources across 5 topics.*


#### Start here

- **[PortSwigger Web Security Academy](https://portswigger.net/web-security/)** — Free, hands-on, per-vulnerability labs with solutions. The single best starting point in security education.
- **[OWASP Top 10](https://owasp.org/Top10/)** — Short, and every entry maps to a class of bug you will actually meet. Read it in an hour, return to it for years.
- **[OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)** — The consistently excellent part of OWASP: dense, correct, per-topic guidance on sessions, authentication, XSS prevention and dozens more.
- **[OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)** — The methodology behind most pentest reports. Skim now, use it when you test something real.


#### Wargames and vulnerable applications

- **[OverTheWire](https://overthewire.org/wargames/)** — SSH wargames; Bandit teaches the Linux command line as a security instrument.
- **[picoCTF](https://picoctf.org/)** — CMU's beginner CTF, permanently open, with the gentlest difficulty curve of any platform.
- **[Root-Me](https://www.root-me.org/)** — Large free challenge catalogue across web, crypto, network and forensics.
- **[OWASP Juice Shop](https://owasp.org/www-project-juice-shop/)** — A deliberately vulnerable Node.js app covering the OWASP Top 10 and far beyond, with a scoring board.
- **[DVWA](https://github.com/digininja/DVWA)** — The classic deliberately vulnerable PHP app; set it to "low" and exploit, then to "impossible" and see why it holds.
- **TryHackMe** — Freemium guided rooms (listed name-only: commercial platform with a substantial free tier).
- **Hack The Box** — Freemium lab machines (listed name-only: commercial platform; the free tier rotates machines).


#### Cryptography from first principles

- **[Cryptopals Challenges](https://cryptopals.com/)** — Build the attacks, not just the defences: padding oracles, CBC bit-flipping, MD length extension. Nothing else makes crypto bugs visceral.


#### Secure coding and ops fundamentals

- **[SEI CERT Coding Standards](https://wiki.sei.cmu.edu/)** — Carnegie Mellon's per-language secure-coding rules (C, C++, Java). The C standard alone is an education in memory safety.
- **[Linux Upskill Challenge](https://linuxupskillchallenge.org/)** — Free month-long server-administration course; security work is mostly being competent on the box.
- **Secure Code Warrior** — Commercial secure-coding training with a free tier (listed name-only).


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language, security included. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*26 resources across 6 topics.*


#### University courses with full public materials

- **[MIT 6.858 Computer Systems Security](https://ocw.mit.edu/courses/6-858-computer-systems-security-fall-2014/)** — Full lectures and labs on OpenCourseWare; the buffer-overflow and capability-system lectures are the classics.
- **[Stanford CS155 Computer and Network Security](https://crypto.stanford.edu/cs155/)** — Web security, network attacks and malware with public slides and projects.
- **[Berkeley CS161 Computer Security](https://cs161.org/)** — The three-pillar structure (crypto, systems, web) with projects and public notes.
- **[Online Cryptography Course (Dan Boneh)](https://crypto.stanford.edu/~dabo/courses/OnlineCrypto/)** — The free crypto course. Build the intuition before touching the standards.
- **Carnegie Mellon security courses (14-741 / 18-631)** — Listed name-only; materials vary by semester, but the syllabi are useful reading maps.


#### Binary exploitation and offensive tooling

- **[pwn.college](https://pwn.college/)** — ASU's structured exploitation curriculum: shellcode to heap, with a dojo of practice infrastructure. Do it in order.
- **[Nightmare](https://github.com/guyinatuxedo/nightmare)** — A curated sequence of binary-exploitation challenges with write-ups, from ret2libc to ROP.
- **[Exploit Education](https://exploit.education/)** — Self-study VMs (Phoenix, Nebula, Protostar) that you attack locally.
- **[pwntools](https://docs.pwntools.com/)** — The Python exploit-writing framework; the documentation doubles as a methodology.
- **[angr](https://angr.io/)** — Symbolic execution and binary analysis framework; solving a crackme with a constraint solver is a rite of passage.
- **[Smashing the Stack for Fun and Profit (Phrack 49)](https://phrack.org/issues/49/14.html)** — The 1996 article that started stack exploitation. Still readable, still the mental model.


#### Reverse engineering

- **[Reverse Engineering for Beginners](https://beginners.re/)** — Dennis Yurichev's free book; x86/x64/ARM assembly through RE exercises.
- **[Azeria Labs](https://azeria-labs.com/)** — ARM assembly and exploit development tutorials; the best free ARM RE material.
- **LiveOverflow** — Video series on binary exploitation and browser internals (listed name-only; watch the "bin 0x" series in order).


#### Vulnerability research and bug bounty

- **[Google Project Zero](https://googleprojectzero.blogspot.com/)** — Real 0-day research with full technical write-ups; every post is a masterclass.
- **[Google Bug Hunters portal](https://bughunters.google.com/)** — How Google's vulnerability reward program works, with rules and write-up guidance that teach triage thinking.
- **[PortSwigger Research](https://portswigger.net/research)** — James Kettle's web research (HTTP request smuggling, desync attacks). Read everything; then read it again.
- **[Hacker101](https://www.hacker101.com/)** — HackerOne's free training, with a CTF that gates invitations to private bug-bounty programs.


#### Applied platform security challenges

- **[flAWS.cloud](http://flaws.cloud/)** — Step-by-step AWS misconfiguration challenges; the fastest way to internalize IAM and S3 failure modes.
- **[OWASP MASTG](https://mas.owasp.org/)** — The Mobile Application Security Testing Guide and its checklist; the mobile counterpart of the WSTG.
- **[REMnux](https://remnux.org/)** — A Linux toolkit distro for malware analysis; its tool list is itself a syllabus.


#### Cryptography practice, competitions and archives

- **[CryptoHack](https://cryptohack.org/)** — Crypto challenges bridging Cryptopals and modern research problems.
- **[CTFtime](https://ctftime.org/)** — The CTF calendar, team rankings and event archive; write-ups from past events are the real library.
- **[Google CTF archive](https://github.com/google/google-ctf)** — Past challenge sets with source and solutions.
- **[Black Hat Briefings](https://www.blackhat.com/)** — Briefing archives with free white papers; decades of applied research.
- **[DEF CON Media Server](https://media.defcon.org/)** — Every DEF CON talk, archived and free.


---

## Research papers & open-access literature

Security research publishes at four core venues — USENIX Security, IEEE S&P, ACM CCS and NDSS — plus PETS, RAID and DIMVA in their niches. The general-purpose paper infrastructure comes first.

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

### USENIX Security

- **Docs:** [usenix.org/conference/usenixsecurity26](https://www.usenix.org/conference/usenixsecurity26)
- **SDKs & repos:** The top systems-security venue, with three review cycles a year and a strong artifact-evaluation culture
- **Downloadable / offline:** Every paper free on publication, plus talk recordings
- *Note:* If you read one security venue, make it this one — and check its SoK papers first (see below).

### IEEE Symposium on Security & Privacy (S&P)

- **Docs:** [computer.org/csdl/proceedings/sp](https://www.computer.org/csdl/proceedings/sp) — the IEEE CSDL proceedings archive
- **SDKs & repos:** "Oakland" — the oldest and most formal security venue; each year also gets a conference site at sp<year>.ieee-security.org
- **Downloadable / offline:** Paywalled via IEEE Xplore; author copies are widely posted — try the author's page or Unpaywall first
- *Note:* Where measurement, formal-methods and theory-heavy work lands. The `ieee-security.org` conference sites refused automated connections while this page was built; they load normally in a browser.

### ACM CCS

- **Docs:** [sigsac.org/ccs](https://www.sigsac.org/ccs/)
- **SDKs & repos:** The broadest ACM security venue, run by SIGSAC
- **Downloadable / offline:** Partly open: ACM Open papers are free; the rest via the ACM DL, which 403s bots but works in browsers
- *Note:* Large and uneven — mine it for applied crypto and web papers, and check arXiv before paying for anything.

### NDSS

- **Docs:** [ndss-symposium.org](https://ndss-symposium.org/)
- **SDKs & repos:** The fourth core venue; web security and systems work feature heavily
- **Downloadable / offline:** Proceedings are open access — free PDFs, every year
- *Note:* Historically the "fast and practical" venue; now co-equal with the other three.

### PoPETs (Proceedings on Privacy Enhancing Technologies)

- **Docs:** [petsymposium.org](https://petsymposium.org/)
- **SDKs & repos:** PETS symposium and journal hybrid; FOCI (Free and Open Communications on the Internet) is its sibling for censorship and anonymity research
- **Downloadable / offline:** Fully open access, every issue
- *Note:* Where traffic analysis, censorship measurement and anonymity work lives.

### RAID (Recent Advances in Intrusion Detection)

- **Docs:** No single stable portal — each year is hosted separately; search "RAID conference \<year\>"
- *Note:* The intrusion-detection and malware-analysis venue. Proceedings are usually behind Springer; author copies are findable.

### DIMVA (Detection of Intrusions and Malware, and Vulnerability Assessment)

- **Docs:** No single stable portal — European venue, hosted per year; search "DIMVA \<year\>"
- *Note:* Smaller sibling of RAID; solid malware and vulnerability-assessment papers.

**A note on SoK papers.** Security is the field with a working culture of *Systematization of Knowledge* papers — literature reviews that are themselves rigorous, peer-reviewed contributions, published mostly at USENIX Security and IEEE S&P. Before reading anything else in a new subfield, search "SoK \<topic\>" across the venues above: a good SoK has already sorted the literature for you and told you which papers were superseded.

---

## If you only do three things

**Work through the PortSwigger Web Security Academy, fuzz something real until it crashes, and read one Project Zero write-up end to end.** Concretely:

1. **Finish the PortSwigger Web Security Academy's core material.** All materials are free, the easy labs included. It is the fastest route from "heard of XSS" to "found one".
2. **Build AFL++ or cargo-fuzz and fuzz a real target.** A parser in your own codebase, or an OSS-Fuzz project. Reading the crash and writing the reproducer is the part that teaches.
3. **Read a single Project Zero post carefully.** Preferably one about a bug class you thought you understood. The discipline of their write-ups is the transferable skill.

## Honest notes

- **The best documentation on this page is free and underused:** the PortSwigger Web Security Academy (the de-facto web security textbook), MITRE ATT&CK's technique pages, and the OWASP Cheat Sheet Series. None of it hides behind a login.
- **The classic trap is treating NVD as the CVE database.** CVE is the registry; NVD is one enrichment layer over it, and that enrichment has had real backlogs. Tooling that assumes NVD analysis is current will mislead you.
- **Stale but working:** sqlmap's site looks ancient and honggfuzz's development has slowed — both still function. OWASP project pages vary wildly in freshness; prefer the Cheat Sheet Series and WSTG over per-project wikis.
- **Bot-blocked but browser-fine:** `cwe.mitre.org` and `boringssl.googlesource.com` return 403 or an auth wall to automated clients; `wiki.sei.cmu.edu` and `media.defcon.org` drop non-browser connections; `ieee-security.org` (the S&P conference sites) refused automated connections entirely when this page was built; and the ACM DL behaves the same (see its note above). Nothing here is dead; some of it just checks for a browser.
- **Commercial training is name-only on purpose.** TryHackMe, Hack The Box and Secure Code Warrior are freemium platforms; this index lists them without links so the genuinely free resources are never crowded out by the upsell.
- **CIS Benchmarks PDFs require registration.** Free as in money, not as in anonymous.
- **The overlap contract:** nmap, tcpdump, Wireshark, Suricata and Zeek are indexed in the networking reference; Vault and SLSA-adjacent platform tooling live in the cloud index; MITRE ATLAS, garak and the OWASP LLM Top 10 belong to the prompt-engineering and agentic indexes. This page covers classical security engineering only — no ML-security entries here.
