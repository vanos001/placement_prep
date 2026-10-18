# Real-World Failure Casebook

Twenty-two named production incidents, each reconstructed from primary sources and analyzed the way an engineer would analyze them: what the system was, what actually happened, the deep technical mechanism of the failure, and why the safeguards that existed did not stop it.

This project is the *specific-case* counterpart of the [generic failure-mode catalog](../../failure-modes/common-failures.md). The catalog teaches you to recognize the pattern ("cache outage", "DNS outage", "failover gone wrong"). The casebook teaches the harder skill: reading a real incident end to end, checking each claim against evidence, and extracting design lessons that survive contact with the details.

## Why Study Real Incidents?

### Patterns are the beginning, not the end

A failure pattern like "database failover produces split-brain" compresses hundreds of distinct events into one sentence. The compression is useful for design discussions and useless for diagnosis. In the [GitHub October 2018 incident](./github-october-2018.md), the pattern label fits — automatic failover produced divergent writes across two data centers — but the specifics are what mattered: a Raft-based failover tool that behaved *exactly as configured*, an application tier that could not tolerate cross-region latency, and a 43-second network partition that no one had ever stress-tested. The pattern tells you what to look for. The case tells you what it looks like in the wild, including all the ways mitigation itself is slow and awkward.

### Reading postmortems is an engineering skill

A written incident report is a compressed, partial, occasionally self-serving document. Reading one well means being able to answer:

- **What does the source actually say?** Not "Knight Capital lost money because of a typo" — the [SEC order](./knight-capital-2012.md) describes a failed copy of new code to one of eight servers, which activated dormant, defective code on that server.
- **What does the source conspicuously not say?** AWS's S3 statement describes a typo'd parameter but does not describe the command's interactive safeguards; drawing conclusions about what was missing requires care and labeling.
- **Where is the boundary between mechanism and cause?** Cloudflare's July 2, 2019 outage had a proximate trigger (one regular expression) and a chain of contributing factors (a removed CPU protection, a test suite that could not measure CPU, a deployment SOP that skipped staging). Singling out one "root cause" is how organizations learn nothing.

Every page in this casebook therefore separates **CONFIRMED** facts (traced to a named primary source) from **INTERPRETATION** (our analysis, clearly labeled). This mirrors the [blameless postmortem discipline](../../sre/postmortem-culture.md): the value of an incident document is exactly proportional to how trustworthy its facts are.

### Cases connect theory to everything else in this repository

Each case page maps its mechanism back to concept pages — concurrency [shared-memory hazards](../../concurrency/memory-model.md), database [replication](../../dbms/distributed/replication.md), [BGP](../../networks/routing/bgp.md), [recovery from logs](../../dbms/transactions/log-recovery.md) — so the incident becomes a way to *use* the theory rather than just know it. This is the same cross-linking philosophy as the rest of the research projects.

## How Each Case Page Is Structured

Every case file follows the same shape, deliberately similar to the [postmortem template](../../sre/postmortem-culture.md#the-postmortem-template) but organized for study rather than review:

1. **Overview** — the incident in one screen: dates, blast radius, headline numbers, all tied to sources.
2. **System Context** — what the system was for and how it was designed *before* the failure. You cannot judge a failure without knowing what "working" looked like.
3. **What Happened** — the narrative, plus a timeline table where the primary source supports one. Every row names its source; where the source gives no timestamp, there is no timestamp.
4. **Technical Mechanism** — the deep "how". This is the heart of each page: catastrophic backtracking in a backtracking regex engine, BGP withdrawal propagation, MySQL promotion across a WAN, shared-memory race windows. Explained from first principles, with a diagram where it earns its space.
5. **Trigger vs Contributing Factors** — separating the spark from the fuel.
6. **Why Safeguards Didn't Prevent It** — the most instructive section: each safeguard is named, and the reason it failed is stated.
7. **Lessons & Mitigations** — generalizable design principles, not a checklist of "the company fixed X".
8. **Connection to This Repository** — links to concept pages that carry the theory.
9. **Interview Questions** — 3–5 questions of the kind this case equips you to answer.
10. **Key Takeaways** — compressed summary.
11. **Sources** — numbered, primary sources first, with URLs verified at time of writing.
12. **Cross-References** — sibling case pages and related repository pages.

## Inventory

| Case | Date | Domain | Headline failure | Mechanism focus |
|------|------|--------|------------------|-----------------|
| [Knight Capital, 2012](./knight-capital-2012.md) | Aug 1, 2012 | Trading systems | $460M+ loss in ~45 minutes | Dead code + repurposed flag + partial deployment |
| [AWS S3 us-east-1, 2017](./aws-s3-us-east-1-2017.md) | Feb 28, 2017 | Cloud storage | Region-wide S3 API failure, 3–4 hours | Destructive command, cold-critical subsystems, recovery order |
| [Cloudflare regex, 2019](./cloudflare-regex-2019.md) | Jul 2, 2019 | Edge/CDN | Global 502s for ~27 minutes | Catastrophic backtracking, linear-time regex engines |
| [GitHub, October 2018](./github-october-2018.md) | Oct 21–22, 2018 | Developer platform | 24h 11min degraded service | Cross-region failover, split-brain writes, backup-restore recovery |
| [Facebook BGP, 2021](./facebook-bgp-2021.md) | Oct 4, 2021 | Global platform | ~6 hours unreachable from the internet | BGP withdrawal, DNS-coupled control plane, manual recovery |
| [Therac-25, 1985–87](./therac-25.md) | 1985–1987 | Medical devices | Six massive radiation overdoses; three deaths tied to overdoses | Race conditions, software-only interlocks, code reuse |
| [Ariane 5 Flight 501, 1996](./ariane-5-1996.md) | Jun 4, 1996 | Space systems | Vehicle destroyed ~40s after liftoff | Data-dependent overflow, exception strategy, code reuse outside validated envelope |
| [Heartbleed, 2014](./heartbleed-2014.md) | Apr 2014 | Internet security | Mass memory disclosure from TLS endpoints | Missing bounds check on attacker-controlled length, `memcpy` overrun |
| [GitLab.com data loss, 2017](./gitlab-2017-data-loss.md) | Jan 31, 2017 | Developer platform | ~300GB production database deleted; ~18h recovery | Destructive command on wrong host, five failed recovery mechanisms, untested backups |
| [CrowdStrike, 2024](./crowdstrike-july-2024.md) | Jul 19, 2024 | Endpoint security | ~8.5M Windows hosts in BSOD loops | Kernel-mode content update without memory-safe parsing, validator gap |
| [Fastly, June 2021](./fastly-june-2021.md) | Jun 8, 2021 | Edge/CDN | Global 500/503 spike, ~1h | Latent bug triggered by valid customer config, global propagation |
| [AWS us-east-1, 2021](./aws-us-east-1-2021.md) | Dec 7, 2021 | Cloud platform | ~11h control-plane degradation in US-EAST-1 | Internal scaling automation, retry amplification, shared network substrate |
| [Mars Climate Orbiter, 1999](./mars-climate-orbiter-1999.md) | Sep 23, 1999 | Space systems | Spacecraft lost at Mars insertion | Unit mismatch in an interface contract, systems-engineering process gaps |
| [AWS DynamoDB us-east-1, 2015](./aws-dynamodb-2015.md) | Sep 20, 2015 | Cloud database | ~5h degraded metadata operations, cascade to dependent services | GSI-inflated membership metadata, network disruption, retry storm |
| [Toyota unintended acceleration, 2009–2011](./toyota-unintended-acceleration.md) | 2009–2011 | Automotive embedded software | Recalls, NHTSA/NASA investigation, criminal litigation | Embedded control software defects, missing memory protection, contested evidence |
| [UK Post Office Horizon, 1999–2025](./uk-post-office-horizon.md) | 1999–2025 | Enterprise systems / law | Hundreds of wrongful prosecutions of subpostmasters | Defective audit logs, presumption of computer correctness, institutional failure |
| [Boeing 737 MAX MCAS, 2018–2020](./boeing-737-max-mcas.md) | Oct 2018–Nov 2020 | Aerospace flight controls | Two crashes, 346 deaths, ~20-month global grounding | Single-sensor dependency, gated safety alert, incremental certification drift |
| [Cloudflare control plane, 2025](./cloudflare-november-2025.md) | Nov 18, 2025 | Edge/CDN control plane | Global 5xx spike, worst outage since 2019 | Database permission change corrupting a security feature file, control-plane/data-plane coupling |
| [Equifax, 2017](./equifax-2017.md) | May–Jul 2017 | Web application security | PII of 145M+ consumers exfiltrated over 76 days | Missed Struts patch via inventory gap, expired monitoring certificate, flat database access |
| [Target, 2013](./target-2013-breach.md) | Nov 27–Dec 15, 2013 | Retail payments | 40M cards + up to 70M records from POS systems | Third-party credentials, weak segmentation, POS RAM-scraping malware, unacted alerts |
| [Ericsson, 2018](./ericsson-certificate-2018.md) | Dec 6, 2018 | Telecom core networks | Nationwide mobile data outages across 11 countries | Expired certificate in vendor SGSN-MME software, synchronized fleet failure |
| [Cloudflare Workers KV, 2025](./cloudflare-june-2025.md) | Jun 12, 2025 | Edge platform storage | 2h28m outage across Workers KV and dependent products | Third-party storage failure behind KV's central store, cascading dependencies, recovery overload |

## Coverage Ledger

The ledger states, for each case, what is verified against a primary source and what is explicitly *not* claimed. This is the fact-checking contract for the whole project.

| Case | Primary source used | URL verified? | Known gaps / unverified items |
|------|--------------------|---------------|-------------------------------|
| Knight Capital 2012 | SEC Administrative Proceeding File No. 3-15570, Release No. 34-70694 (Oct 16, 2013); SEC Press Release 2013-222; Knight 8-K (Aug 6, 2012) | Yes — sec.gov PDF and press release fetched and quoted | Exact clock time the erroneous trading stopped is not stated in the SEC order; only a "~45-minute period". Popular accounts sometimes say "9:47 a.m. ET" — not used here. |
| AWS S3 2017 | "Summary of the Amazon S3 Service Disruption in the Northern Virginia (US-EAST-1) Region", AWS Message (Feb 28, 2017) | Yes — aws.amazon.com/message/41926/ fetched and quoted | AWS does not state which parameter was mistyped or what interactive checks the tool had; we describe only what the statement says and label the rest as interpretation. |
| Cloudflare 2019 | "Details of the Cloudflare outage on July 2, 2019", blog.cloudflare.com (Jul 2, 2019), John Graham-Cumming | Yes — fetched and quoted | The post describes the global-kill execution being blocked by internal access failures; it does not say the kill switch "failed" per se — see the case page for the precise wording. |
| GitHub Oct 2018 | "October 21 post-incident analysis", github.blog (Oct 30, 2018), Jason Warner | Yes — fetched and quoted | The partition is described as 43 seconds of lost connectivity, restored; other figures circulating (e.g., "31.5-second link flaps") do not appear in the primary post and are not used. |
| Facebook Oct 2021 | "More details about the October 4 outage", engineering.fb.com (Oct 5, 2021); "Update about the October 4th outage" (Oct 4, 2021); Cloudflare's contemporaneous measurement post (Oct 4, 2021) | Yes — all three fetched | Facebook's own posts give no UTC timestamps; external timings used here come from Cloudflare's measurement post and are attributed to it. |
| Therac-25 | N. G. Leveson and C. S. Turner, "An Investigation of the Therac-25 Accidents", *IEEE Computer* 26(7), July 1993, pp. 18–41 (reprinted at web.mit.edu) | Yes — all four parts fetched | The authors themselves note that AECL's internal development records were unavailable; per-accident dose figures are estimates from hospital physicists as reported in the paper. |
| Ariane 5 1996 | J. L. Lions et al., *Ariane 5 Flight 501 Failure — Report by the Inquiry Board*, ESA, July 1996 | Yes — full text via cs.unibo.it mirror fetched and quoted | Component-level telemetry traces summarized from the report's appendixes; no independent re-derivation of the alignment-timing figures |
| Heartbleed 2014 | OpenSSL Security Advisory "TLS heartbeat read overrun (CVE-2014-0160)" (Apr 7, 2014); heartbleed.com | Yes — advisory text fetched and quoted | Which specific organizations were exploited is NOT asserted; the page states only what memory *could* be exposed per the advisory |
| GitLab 2017 | GitLab, "Postmortem of database outage of January 31" (Feb 10, 2017) | Yes — fetched and quoted | The day-of announcement post is cited by title only; per-hour restore figures come from the postmortem's timeline |
| CrowdStrike 2024 | CrowdStrike, "Channel File 291 Incident — External Technical Root Cause Analysis" (Aug 6, 2024); Microsoft blog | URL verified via search; PDF not full-text fetchable — key facts cross-checked against verbatim mirrors | Per-industry outage figures and litigation outcomes are not covered |
| Fastly 2021 | Fastly, "Summary of June 8 outage" (Jun 8, 2021) | URL verified via search; page not fetchable at writing — facts quoted via verbatim excerpts in contemporaneous coverage [2][3] | The customer identity behind the triggering config is not public and is not named |
| AWS us-east-1 2021 | AWS, "Summary of the AWS Service Event in the Northern Virginia (US-EAST-1) Region" (Dec 10, 2021) | Yes — aws.amazon.com/message/12721/ fetched and quoted | The specific internal service whose scaling triggered the event and device-level details are not stated by AWS; those parts are labeled interpretation |
| Mars Climate Orbiter 1999 | MCO Mishap Investigation Board, *Phase I Report* (Nov 10, 1999); NASA LLIS entry 641 | Yes — llis.nasa.gov PDF fetched and full text extracted | Component-level telemetry summarized from report appendixes; no independent re-derivation of the trajectory figures |
| AWS DynamoDB 2015 | AWS, "Summary of the Amazon DynamoDB Service Disruption and Related Impacts in the US-East Region" (Sep 20, 2015) | Yes — aws.amazon.com/message/5467D2/ fetched and quoted | Only the four dependent services AWS names are covered; no third-party impact estimates used |
| Toyota 2009–2011 | NASA Engineering & Safety Center, *Technical Assessment Report: Toyota Unintended Acceleration Investigation* (Feb 2011); NHTSA EA11-001; DoT press release; Barr, *Bookout v. Toyota* slides (2013); Koopman CMU case study (2014) | Yes — NHTSA PDF, DoT press release, Barr mirror, and Koopman PDF fetched; NESC report URL live but content quoted via secondary full texts | Barr's software-defect claims remain litigation testimony, not regulator findings; the page labels contested points as contested |
| UK Post Office Horizon 1999–2025 | *Report of the Post Office Horizon IT Inquiry, Volume 1* (HC 1119, Jul 2025); Fraser J, *Bates (No. 6) "Horizon Issues"* [2019] EWHC 3408 (QB); *Hamilton v Post Office* [2021] EWCA Crim 577 | Yes — inquiry report PDF and both judgments fetched and quoted | Prosecution counts vary by source and date; the page uses inquiry-report figures and labels the range |
| Boeing 737 MAX MCAS 2018–2020 | NTSB, *Aviation Safety Report ASR-19/01* (Sep 2019); KNKT final report; JATR summary; U.S. House Committee report (Sep 2020); DoJ deferred prosecution agreement (Jan 2021) | Yes — NTSB report PDF fetched; other sources cited by title+org+year without URLs | Exact certification-meeting content is sealed/not public; the page labels reconstructed internal decision-making as interpretation |
| Cloudflare Nov 2025 | Matthew Prince, "Cloudflare outage on November 18, 2025", blog.cloudflare.com (Nov 18, 2025) | Yes — fetched and quoted | Internal operational details outside the post's scope are not covered; downstream-customer figures are those the post states |
| Equifax 2017 | GAO, *Data Protection: Actions Taken by Equifax and Federal Agencies in Response to the 2017 Breach*, GAO-18-559P (Aug 30, 2018); House Oversight staff report *The Equifax Data Breach* (Dec 2018); Senate PSI, *How Equifax Neglected Cybersecurity...* (Dec 2018); Equifax statement on CVE-2017-5638 (Sept 15, 2017, via EPIC archive) | Yes — GAO product page fetched and quoted; GAO PDF title verified via fetch; House/PSI/EPIC URLs verified via search | Report PDFs not machine-extractable at writing: exact certificate-expiry duration and per-country record counts not re-quoted from full text; SEC/FTC settlement amounts described qualitatively only |
| Target 2013 | Senate Commerce staff report, *A "Kill Chain" Analysis of the 2013 Target Data Breach* (Mar 26, 2014); KrebsOnSecurity (Feb 5, 2014); Target press statements (Dec 19, 2013; Jan 10, 2014) | Yes — Senate PDF URL verified via search and fetch (title); KrebsOnSecurity URL verified | Senate PDF full text not machine-extractable: alert-level details quoted from the report's indexed narrative; Verizon forensic report is non-public and described via press reporting only; financial-cost figures not used |
| Ericsson 2018 | Ericsson press statements (Dec 6–7, 2018, quoted verbatim); SoftBank incident statement (Dec 6, 2018); O2/Telefónica UK statements — all as quoted by ZDNet | Yes — ZDNet article fetched and quoted; ericsson.com cited without URL (returns 403 to automated fetch) | Swisscom impact and O2 subscriber counts marked reported-but-unverified; node/interface naming varies across accounts (SGSN-MME per the statement; S1-MME in some third-party accounts); exact certificate embedding not public |
| Cloudflare Jun 2025 | Jeremy Hartman and CJ Desai, "Cloudflare service outage June 12, 2025", blog.cloudflare.com (Jun 12, 2025) | Yes — fetched and quoted in full | The third-party storage provider is not named in the post; provider share of the backend and per-customer figures outside the post's tables are not covered |

Reading rules used across all pages:

- **CONFIRMED** marks a statement traceable to the cited primary source.
- **INTERPRETATION** marks our own analysis — reasonable engineering inference, clearly separated from evidence.
- Where a widely repeated detail could not be traced to a primary source, it is either omitted or explicitly marked *reported but unverified*. No URLs, quotes, timeline entries, or root causes are invented.

## How to Use This Casebook

1. **Before interviews**: pick two cases closest to your target role (e.g., S3 + GitHub for infrastructure roles). Read the Technical Mechanism sections until you can re-derive the failure on a whiteboard.
2. **As practice for postmortem reading**: for each case, first read only the Overview and What Happened sections, write your own diagnosis, then compare against the Technical Mechanism section. This trains exactly the skill a real incident response demands: forming hypotheses from incomplete evidence.
3. **As design input**: the Lessons sections are written as principles you can apply in system design interviews — staged deployment, recovery-order planning, quorum discipline, and safety-architecture arguments all generalize.
4. **Alongside the pattern catalog**: after reading a case, find its pattern in the [failure-mode catalog](../../failure-modes/common-failures.md) and notice how much detail the pattern hides.

## Cross-References

- [Failure modes: common failures catalog](../../failure-modes/common-failures.md) — the generic-pattern counterpart to these specific cases.
- [Postmortem and incident response culture](../../sre/postmortem-culture.md) — the process framework these cases are written in.
- [Incident management](../../sre/incident-management.md) — command structures, severity, and communication during incidents.
- [Distributed systems overview](../../distributed/overview.md) — theoretical background for the replication and consensus failures in these cases.
- [DBMS overview](../../dbms/overview.md) — database internals referenced by the GitHub and AWS cases.
- [Networking overview](../../networks/overview.md) — BGP, DNS, and routing background for the Facebook and Cloudflare cases.
- [SRE README](../../sre/README.md) — reliability engineering hub for canary releases, feature flags, chaos engineering, and on-call practice.
