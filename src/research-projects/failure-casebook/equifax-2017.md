# Equifax, May–July 2017: An Unpatched Struts Vulnerability, an Expired Certificate, and 76 Days of Dwell Time

## Overview

Between May and July 2017, attackers accessed the web application Equifax used for online consumer credit disputes, extracted personal data from the databases behind it, and shipped the data out of the company over an encrypted channel that the company's own monitoring tooling could not read — because the certificate on that monitoring infrastructure had expired months earlier. The [U.S. Government Accountability Office][1] states that the attackers accessed personal information of **at least 145.5 million individuals**, and the House Committee on Oversight and Government Reform's staff report [2] states that the attack **lasted 76 days before Equifax employees discovered it**. The exploited weakness was later publicly identified by Equifax itself as **CVE-2017-5638, a remote code execution vulnerability in Apache Struts** that had been disclosed and patched in March 2017 [4].

CONFIRMED (per GAO [1]): Equifax's own investigation identified four major factors that let the attacker gain access and extract data — identification, detection, segmenting of access to databases, and data governance. Those four labels compress almost every classic failure this casebook studies: an asset that nobody could reliably enumerate, a detection path that was dark for months, a network that did not contain the compromise, and archives of unencrypted identity data with no reason to exist in that form. The case is the canonical security counterpart to fleet-scale operational incidents like [CrowdStrike, July 2024](./crowdstrike-july-2024.md): a single unremediated item on one internet-facing system, multiplied by an inventory and monitoring estate that could not see itself.

## System Context

Equifax is one of the three dominant U.S. consumer reporting agencies. Its core product is a dossier on more than a hundred million people — names, Social Security numbers, dates of birth, addresses, and credit histories — assembled from lenders and sold to decision-makers. This is the most monetizable identity data in circulation, because it is exactly the data needed to impersonate someone when opening new accounts [1]. The company also operated the **online dispute portal** — the web application consumers use to challenge items on their credit file. The House staff report identifies this application by its internal name, **ACIS (Automated Credit Inquiry System)** [2]; GAO describes it functionally as "the online dispute portal that maintained documents used to resolve consumer disputes" [1]. GAO confirms the attackers' initial foothold was precisely this portal, reached "via the Internet" [1].

The dispute portal ran on the **Apache Struts** web application framework [4]. In early March 2017, a Struts vulnerability affecting the file-upload path was publicly disclosed with a working proof of concept, and patched releases were published within days (CVE-2017-5638) [4]. This matters because of the asymmetry it created: from March onward, every unpatched Struts instance on the internet was a known, scripted target, and Equifax — one of the most data-rich companies in the world — had at least one. The House report documents that Equifax staff had in fact encountered Struts on the affected systems earlier that year during remediation of an unrelated vulnerability, so the framework's presence was not a secret inside the company [2]. What failed was the connection between "we know this component exists" and "this component is on the list of systems that must be patched."

## What Happened

| Time (2017) | Event | Source |
|---|---|---|
| Early March | CVE-2017-5638 disclosed and patched in Apache Struts; Equifax later states it began efforts to apply the patch | [4][2] |
| March–April | Patching effort misses the dispute portal; the House report describes the application being inadequately catalogued in the asset inventory used to drive remediation | [2] |
| From May 13 (per House report) | Attackers exploit the unpatched portal and establish access; the attack "lasted 76 days before it was discovered" | [2] |
| Over the following weeks | Attackers obtain credentials, move to databases well beyond the portal, and stage extracted data | [2] |
| Mid-July | Exfiltration of the staged data begins, over an encrypted channel invisible to monitoring because the monitoring SSL certificate had expired | [2] |
| Night of July 29 | Equifax installs dozens of new SSL certificates to replace expired ones, including on the monitoring infrastructure | [3] |
| July 29–30 | Administrators discover unauthorized access to the dispute portal; anomalous traffic becomes visible; the portal is taken offline | [1][2][3] |
| September 2017 | Equifax publicly identifies the exploited vulnerability as Apache Struts CVE-2017-5638; FTC and CFPB open an investigation | [4][1] |
| Sept 2018 / Jul 2019 | SEC charges Equifax with internal-accounting-controls violations (settled); the joint FTC/CFPB/state settlement is announced — reported at the time at a minimum of $575 million and up to $700 million depending on consumer redress uptake | [5][6] |

CONFIRMED (per GAO [1]): the company's own post-incident investigation attributed the success of the attack to the four factors listed above, and Equifax reported taking steps to mitigate them. INTERPRETATION: the timeline rows for March–July compress the two reports' narratives into one table; where the two government reports differ in emphasis, this page follows the House report for the operational sequence and GAO for the company-level findings.

## Technical Mechanism

The attack is a chain in which each link is unremarkable alone. The Struts file-upload parser mishandled a malformed `Content-Type` header, letting an attacker execute commands on the web server (CVE-2017-5638) [4]. A scriptable exploit existed from the day of disclosure, which converts "unpatched" from a risk into a near-certainty on any internet-reachable instance. Once on the portal, the attackers did not stop there: per the House report [2], they escalated, obtained credentials that unlocked the broader environment, and reached databases containing consumer identity records that had no functional relationship to a dispute-resolution application. GAO's four-factor summary names the structural reasons this traversal worked — failures of **identification** (the asset estate was not fully known, so the patch did not reach the portal) and **segmenting of access to databases** (a public web tier and the crown-jewel identity store shared trust) [1].

The exfiltration stage is the part every engineer should internalize:

```text
attacker exfil -> HTTPS from inside the network -> monitored by SSL-inspection gear
                                                     |
                                             inspection certificate EXPIRED
                                                     |
                                        encrypted traffic rendered invisible
```

Per the House report [2], an expired **Secure Sockets Layer (SSL) certificate** on the monitoring path prevented Equifax from seeing the data leaving its network; the Senate Permanent Subcommittee on Investigations report records that Equifax "installed dozens of new SSL certificates on the night of July 29, 2017, to replace certificates that had expired" [3]. In other words, the sensor that existed precisely to watch outbound data had been blind for a substantial period, and nobody noticed a *sensor* outage — only the absence of its output. The certificate is a lease on visibility with a hard expiry date, and visibility infrastructure needs the same expiry management, alerting, and verification as the services it watches.

### Trigger vs Contributing Factors

**Trigger (CONFIRMED):** exploitation of CVE-2017-5638 on the internet-facing dispute portal after the March patch deadline, by attackers who had already selected the target [2][4].

**Contributing factors (CONFIRMED):** the patch effort that missed the portal due to inventory/cataloguing gaps [2]; dwell time of 76 days [2]; the expired monitoring certificate hiding exfiltration [2][3]; GAO's four factors as identified by Equifax — identification, detection, database-access segmentation, and data governance [1]; unencrypted staging of extracted identity data [2].

**Contributing factors (INTERPRETATION):** the incentive structure of credit-data monopolies — vast archives retained because they might be valuable, thin margins on security operations relative to data operations — is our reading of why the four factors persisted at a company of this scale. Neither government report claims a motive structure; we label this analysis, not fact.

## Why Safeguards Didn't Prevent It

Each safeguard that should have stopped this chain was present in degraded form:

- **Patch management existed, but its input data was wrong.** The House report [2] describes a patching process that was executed against an incomplete inventory: the dispute portal was inadequately catalogued, so the March remediation wave passed it by. A patch pipeline is only as good as the asset list that feeds it — a fleet-heterogeneity failure identical in shape to the one-server-out-of-eight copy failure in [Knight Capital, 2012](./knight-capital-2012.md), except here the divergence lasted months and the payload was chosen by an attacker.
- **Perimeter monitoring existed, but was dark.** The SSL-inspection capability was real infrastructure, deployed for exactly this purpose — and an expired certificate silently disabled it [2][3]. Controls fail in two modes: by absence and by silent degradation. The second mode is worse, because dashboards keep asserting the control is healthy.
- **Network segmentation was insufficient.** GAO records "segmenting of access to databases" as one of the four factors [1]: the compromise of a consumer-facing web app conferred reach into identity databases. There was no meaningful air gap between "the tier we expose to strangers" and "the tier we would publish to the world rather than lose."
- **Data governance did not bound the blast radius.** The same GAO factor list names data governance [1]; the House report describes identity data staged in unencrypted form and reachable from the compromised application [2]. Data that is not needed by an application should not be accessible to it — least privilege applies to data at rest, not just to API calls.
- **Detection existed as an activity, not as a property.** GAO lists "detection" among the factors [1]. The company eventually discovered the intrusion through administrators noticing the access, not through automated alerting on the exfiltration that had been running for days.

## Lessons & Mitigations

1. **Patch velocity is bounded by inventory accuracy.** The March Struts patch was available for two months before the intrusion; the failure was not awareness but targeting — knowing *where* to patch. Maintain a reconciled, continuously verified asset inventory (deployed-binary attestation, service registration, periodic external scanning) and treat "internet-reachable component missing a disclosed-vuln patch" as a page-worthy exception.
2. **Treat certificates as production dependencies with expiries.** The monitoring certificate was a single point of invisibility with a countdown clock. Certificate lifecycle belongs in the same discipline as TLS rotation everywhere else — inventory, automated renewal, expiry alerting, and dead-man monitoring that alerts when the *sensor* stops seeing traffic. The [certificate lifecycle](../../security/letsencrypt-acme.md) page covers the mechanics; the Ericsson 2018 case in this casebook shows the same class of failure bricking telecom cores.
3. **Segment so that one web app cannot reach identity stores.** The dispute portal and the PII databases should have shared nothing — separate credentials, separate networks, separate access paths. A zero-trust posture ([security: zero trust](../../security/zero-trust.md)) would have forced the portal to authenticate to the data tier for specific, logged operations.
4. **Bound data exposure, not just data storage.** Encrypting the archives would not have prevented theft of the keys co-located with them, but the deeper fix is structural: an application reads the minimum fields it needs, retention is enforced, and blast radius is a design input. The failure of "data governance" that GAO records is a failure of least privilege applied to data at rest.
5. **Monitor the monitors.** An expired certificate produced months of silence rather than an alert. Any control whose failure mode is "stops producing evidence" needs its own heartbeat. This is the same principle as Knight Capital's 97 unreviewed warning emails: signals that exist but are not instrumented do not count as detection.
6. **Compliance is a floor, not a boundary.** The regulatory aftermath — the SEC's internal-accounting-controls action [5] and the FTC/CFPB settlement [6] — treated the absence of functioning controls, not merely a missed patch, as the violation. Design reviews should ask the question the SEC effectively asked: would this control have changed the outcome?

## Interview Questions

1. Your organization runs an automated patch pipeline that remediated 95 percent of hosts for a critical disclosed vulnerability within a week. How do you find and reason about the remaining 5 percent, and what data structures make "which hosts still run version X" answerable in minutes?
2. A TLS certificate on your egress-monitoring appliance expires tonight. What alerts fire? If the answer is "none," design the detection: how do you notice that an inspection path has gone dark without waiting for an incident?
3. A public-facing web application needs to look up identity records. Walk through a design that keeps a compromise of that application from yielding bulk extraction of the identity store, and explain which property fails first at Equifax.
4. How would you reconcile two sources of truth about your fleet — a CMDB and what is actually listening on the network — and which one should drive patch SLAs? Relate to the cataloguing failure in this case.
5. GAO lists four factors (identification, detection, segmentation, data governance). For each, name one concrete engineering artifact (not a policy document) whose existence would demonstrate the factor was addressed.

## Key Takeaways

- 76 days of dwell time and at least 145.5 million individuals affected [1][2] — from one unpatched internet-facing component and one expired certificate on the monitoring path.
- The breach was not stopped by a missing tool. Every control existed: patching, SSL inspection, network boundaries, retention. Each was disconnected from its input data — inventory, expiry dates, segmentation boundaries, retention rules.
- Equifax's own investigation, via GAO, named identification, detection, segmentation, and data governance [1] — four systems-engineering failures wearing a security label. None of the four is exotic; all four are properties an engineering organization can build, measure, and rehearse.
- The regulatory aftermath priced the absence of working controls, not the presence of a bug — an external confirmation that prevention is an architecture problem, exactly as the SEC concluded for Knight Capital.
- The most durable lesson: a control that degrades silently is indistinguishable from a control that works. Instrument the control's own liveness, and treat months of sensor silence as an incident rather than as peace.

## Sources

1. U.S. Government Accountability Office, *Data Protection: Actions Taken by Equifax and Federal Agencies in Response to the 2017 Breach*, GAO-18-559P, published August 30, 2018. https://www.gao.gov/assets/gao-18-559.pdf (URL fetched; PDF title verified; product-page highlights text with key figures extracted and quoted). GAO product page: https://www.gao.gov/products/gao-18-559
2. U.S. House Committee on Oversight and Government Reform, *The Equifax Data Breach*, staff report, December 2018. https://oversight.house.gov/wp-content/uploads/2018/12/Equifax-Report.pdf (URL and title verified via search; PDF not machine-extractable at writing — 76-day figure and certificate narrative confirmed via the report's indexed text)
3. U.S. Senate Committee on Homeland Security and Governmental Affairs, Permanent Subcommittee on Investigations, *How Equifax Neglected Cybersecurity and Suffered a Devastating Data Breach*, staff report, December 2018. https://www.hsgac.senate.gov/subcommittees/investigations/library/files/majority-and-minority-staff-report_-how-equifax-neglected-cybersecurity-and-suffered-a-devestating-data-breach (URL and title verified via search; July 29, 2017 certificate-replacement detail from the report's indexed text)
4. Equifax Inc., statement confirming the exploited vulnerability as Apache Struts CVE-2017-5638, September 15, 2017 — text archived in EPIC's Equifax Data Breach timeline: https://archive.epic.org/privacy/data-breach/equifax (URL verified via search)
5. U.S. Securities and Exchange Commission, charges and settlement with Equifax Inc. regarding internal accounting controls, September 2018. Cited by title+org+year; URL not verified this session.
6. Federal Trade Commission / Consumer Financial Protection Bureau / state attorneys general settlement with Equifax, July 2019. Cited by title+org+year; URL not verified this session.

## Cross-References

- [Heartbleed, April 2014](./heartbleed-2014.md) — a disclosed vulnerability in trust infrastructure with a known fix window; both cases turn on the gap between "the patch exists" and "every instance is patched."
- [CrowdStrike, July 2024](./crowdstrike-july-2024.md) — fleet-scale distribution of security content with an unverified edge; the operational inverse of Equifax's fleet-scale patching gap.
- [Knight Capital, 2012](./knight-capital-2012.md) — partial deployment invisible to the operator; Equifax shows the same fleet-heterogeneity failure with an attacker supplying the trigger.
- [GitLab.com data loss, 2017](./gitlab-2017-data-loss.md) — safeguards that existed in degraded form (backups, certificates here; replication and warnings there) discovered only when needed.
- [Incident response](../../security/incident-response.md) — the detection and triage discipline whose absence GAO records as one of the four factors.
- [Zero trust](../../security/zero-trust.md) — the segmentation posture whose absence let a dispute portal reach identity databases.
- [Postmortem culture](../../sre/postmortem-culture.md) — how two congressional reports and a GAO review serve as the regulatory-grade postmortems this case never received from the company in public.
