# UK Post Office Horizon, 1999–2025: The Ledger Was Presumed Right, the Operators Were Prosecuted

## Overview

Between 2000 and 2013 the UK Post Office Limited (POL) prosecuted hundreds of its own subpostmasters for theft, fraud, and false accounting on the strength of one premise: that shortfalls shown by the Horizon electronic point-of-sale and accounting system must be real, and therefore must be the operator's fault. CONFIRMED (per the inquiry chaired by Sir Wyn Williams): between 2000 and autumn 2013 POL prosecuted subpostmasters and branch workers in England and Wales "in reliance upon accounting data produced by Horizon", asserting "either expressly, or by implication that the data produced by Horizon was wholly reliable" [1]; the Chair concluded that "many hundreds of people have been convicted, wrongly, of criminal offences, and many thousands of people have been held responsible, wrongly, for losses which were illusory" [1].

CONFIRMED (per the courts): in the group litigation, *Bates and Others v Post Office Ltd* (2019), Mr Justice Fraser found that bugs, errors, and defects in Horizon had the potential to cause apparent shortfalls — and that this "actually has happened, and on numerous occasions" [3]; in *Josephine Hamilton and Others v Post Office Ltd* (2021), the Court of Appeal quashed 39 of 42 convictions because POL's failures of investigation and disclosure meant those appellants "could not have, and did not have, a fair trial" [5]. A statutory public inquiry followed; Volume 1 of its final report, focusing on human impact and redress, was presented to Parliament on 8 July 2025, with further volumes still to come [1][2].

This is the casebook's clearest institutional failure of the "computer says no" kind: a system's output was treated as ground truth, the vendor's records were treated as evidence, the operators' reports were treated as lies, and the audit trail that could have disproved the prosecutions was never searched or disclosed. Every engineering lesson here concerns what happens when a computer system becomes a legal instrument without the evidentiary properties that make it trustworthy.

## System Context

- **The parties.** Subpostmasters (SPMs) are not employees but independent contractors who run branches, operate the Horizon terminal, and are contractually liable for apparent losses in branch [1][3]. Criminal prosecutions are formally brought in the name of the Crown, but each of these cases "was commenced and pursued by POL acting as a private prosecutor", charging its own contract-holders with theft, fraud, and false accounting [5].
- **The system.** POL "introduced a computer system called Horizon in 2000 across all its branches"; in 2010 came the online version, Horizon Online (HNG-X), with the original now called Legacy Horizon [3]. The supplier lineage ran from ICL Pathway to Fujitsu, which the inquiry treats as "Fujitsu" throughout [1].
- **The accounting model.** Branch accounts were held centrally in Horizon; when the numbers did not add up, the discrepancy was a debt the SPM owed POL [5]. The scale of routine correction was invisible to SPMs: POL issued more than 100,000 "transaction corrections" (TCs) per year since 2006 — "more than 2,000 per week" — corrective plumbing that sat outside the definition of Horizon itself [3].
- **The vendor's back door.** Fujitsu support staff held powerful remote-access roles over branch data. The two independent experts agreed that "anyone with the APPSUP role could pretty much do whatever they wanted", and Fraser found these facilities had the potential to affect branch accounts materially — with clear instances where they did [3]. Fujitsu's record-keeping of its own actions he found "plainly inadequate" [3].

## What Happened

| Date | Event | Source |
|---|---|---|
| 2000 | Horizon rolled out across all branches; SPMs begin reporting unexplained shortfalls almost immediately — complaints "continued throughout the life span" of both system generations | [1][3] |
| 2005–2006 | Callendar Square bug (Falkirk branch): transfers between "Stock Units" not visible to the receiving unit, surfacing as a Receipts and Payments mismatch; fixed in the S90 release, March 2006 | [3] |
| 2009 | Justice for Subpostmasters Alliance (JFSA) formed | [1] |
| 2000–2013 | POL prosecutions for theft, fraud, and false accounting proceed on Horizon data; in January 2012 its own board minutes record that the business "has won every criminal prosecution in which it has used evidence based on the Horizon system's integrity" | [1][5] |
| 2010 | Horizon Online (HNG-X) replaces Legacy Horizon; the Dalmellington (outreach-branch) bug family belongs to this generation | [3] |
| 2016 | Group Litigation Order proceeds with approximately 555 claimants | [1] |
| Mar 2019 | *Bates* Common Issues judgment ([2019] EWHC 606 (QB)): the Post Office's conduct of the relationship fails on contract and good faith grounds | [1] |
| Dec 2019 | Group Litigation settled for a total of £57.75m — a sum the inquiry later found left the claimants themselves with far too little after costs | [1] |
| Dec 16, 2019 | *Bates* Horizon Issues judgment: bugs could and did cause shortfalls; the system did not alert SPMs; Legacy Horizon "not remotely robust" | [3] |
| Apr 23, 2021 | Court of Appeal quashes 39 of 42 convictions in *Hamilton* — POL conceded material failures of investigation and disclosure in all but three cases | [5] |
| Jun 1, 2021 | Inquiry converted to a statutory inquiry under the Inquiries Act 2005 | [1] |
| Oct 2021 | A further group of Horizon appeals ([2021] EWCA Crim 1443) succeeds; convictions also quashed at Southwark Crown Court through the period | [1] |
| May 24, 2024 | Post Office (Horizon System) Offences Act 2024 comes into force in England, Wales, and Northern Ireland, exonerating hundreds by legislation; a Scottish equivalent follows; the Horizon Convictions Redress Scheme launches July 30, 2024 | [1] |
| Jul 8, 2025 | Volume 1 of the inquiry's final report (HC 1119) published — human impact and redress; further volumes to follow | [1][2] |

## Technical Mechanism

### 1. Bugs that produced phantom debts

Three named defects carry the technical story. The **Callendar Square bug** (discovered 2005 at a Falkirk branch) corrupted transfers between a branch's Stock Units: the receiving unit could not "see" the transfer made by the sending unit, the discrepancy compounded on retry, and it surfaced to the user precisely as a "Receipts and Payments mismatch" — the shape of an ordinary pilferage or bookkeeping error [3]. The **Dalmellington bug** (Horizon Online) combined a Forced Log Out defect — a script left on the stack of incomplete processes — with a Pouch Delivery script that repeated the remittance recording and receipt printing, producing duplicate pouch identifiers [3]. At Dalmellington itself, an £8,000 transfer from a core branch to an outreach branch replicated four times, generating receipts of £32,000 and a phantom £24,000 discrepancy; Fujitsu's later investigation found 112 occurrences affecting 88 branches in five years [3]. The **Receipts and Payments Mismatch (RPM) bug** completed the family Fraser examined [3][5].

Fraser's summary finding answers the "could a machine cause this?" question directly: bugs, errors, and defects had the potential "to cause apparent or alleged discrepancies or shortfalls relating to Subpostmasters' branch accounts" and to undermine Horizon's reliability — and beyond potential, "it actually has happened, and on numerous occasions" [3]. The Post Office's own expert accepted "strong evidence of at least 12 bugs causing a lasting discrepancy in branch accounts"; Fraser found more [3].

### 2. An alerting system that did not alert

The Horizon Issues trial asked directly whether Horizon alerted users to its own defects. The answer: "No, the Horizon system did not alert SPMs" [3]. Some bugs "lay undiscovered in the Horizon system for years" [3]. What the SPM saw instead was a balance that did not add up — with no indication whether the cause was their own keystroke, a transaction race, or a defect in the machine. The support channel then inverted the burden: Fujitsu would "regularly record user error simply as a 'catch all'" and "require someone to rule it out to Fujitsu's satisfaction" before any bug explanation survived [3]. A defect-reporting system that defaults to blaming the human is not a diagnostic channel; it is a bias amplifier.

### 3. Evidence asymmetry: the audit log as a sealed room

Every prosecution's factual core was an arithmetic claim: the branch shows a shortfall; shortfalls are debts; the debt is dishonesty [1][5]. What made the claim unanswerable in court was the distribution of evidence. The SPM had a terminal and their own word; POL and Fujitsu had the transaction database, the audit records, the remote-access logs, and the incident history — and Fujitsu's records of its own powerful access roles were, in Fraser's finding, inadequate [3]. POL's duty to investigate and disclose material undermining its case failed for years, as POL's own concessions in the 2021 appeal confirmed: material failures of investigation and disclosure meant a fair trial was impossible in 39 cases [5]. The machinery that could have exonerated people existed; it simply was never run on their behalf. One disclosed POL board minute from January 2012 captures the institutional posture in a single sentence: "The Business has also won every criminal prosecution in which it has used evidence based on the Horizon system's integrity" [5].

```text
Horizon shows shortfall --> debt attributed to SPM
SPM disputes --> support log records "user error" catch-all
Prosecution on "wholly reliable" data --> conviction
```

### Trigger vs Contributing Factors

**Trigger (CONFIRMED):** an unexplained shortfall in a branch's Horizon accounts, treated by POL as a debt and, in hundreds of cases, as evidence of dishonesty [1][5].

**Contributing factors (CONFIRMED):** bugs, errors, and defects that could and did cause shortfalls in both Horizon generations [3]; no user-facing alerting of system defects [3]; poorly audited Fujitsu remote-access roles [3]; inadequate vendor record-keeping and unreliable incident closure codes [3]; TCs correcting the books at over 2,000 per week — systemic correction invisible in the accounts [3]; POL's failures of investigation and disclosure across years of prosecutions [5].

**Contributing factors (INTERPRETATION):** the presumption of machine correctness. Nothing in Horizon's design or POL's processes operationalized the hypothesis "the system may be wrong" — the record's reliability was certified by the machine's own supplier. This is the "computer says no" failure in its purest form: the computer's output was accepted as an act of institutional faith, and the humans who disagreed were treated as the anomaly. We present this as an engineering characterization of documented behavior, not as a finding about anyone's state of mind; making those findings is the inquiry's task, and its later volumes are pending [1].

## Why Safeguards Didn't Prevent It

- **The single safeguard was the system itself.** No independent reconciliation channel existed between Horizon's central ledger and the SPM's own records; the machine was the ledger, and the ledger was presumed right. A safety argument consisting of one layer — the machine — is the Horizon version of the software-only interlock pattern in the [Therac-25 case](./therac-25.md).
- **The alerting layer was missing by design.** "The Horizon system did not alert SPMs" [3], and the defect-reporting channel defaulted to "user error" [3]. Both the runtime signal and the support signal pointed away from the truth.
- **The evidentiary layer was captured.** The party alleging dishonesty controlled the database, the audit records, and the expert narrative; the party denying it had none of these [3][5]. Disclosure — the procedural control meant to rebalance this — failed systematically, which is why the Court of Appeal's remedy was framed as abuse of process rather than mere error [5]. Remote-access powers with inadequate logs made the truth permanently indeterminable after the fact — an ambiguity prosecutions resolved in the machine's favor [3].
- **Institutional incentives selected the wrong hypothesis.** Repayment and prosecution were the default paths; investigating Horizon would have invalidated the revenue ledger itself. INTERPRETATION: this is the structural reason "we checked the computer, and the computer is fine" repeated itself for over a decade — the check was always performed by the party with the least incentive to find anything.

## Blast Radius and Impact

- **People.** "Many hundreds" wrongly convicted and "many thousands" wrongly held liable for illusory losses [1]. The inquiry records evidence from at least 59 persons who contemplated suicide, attributing it to their experiences with Horizon and/or the Post Office; ten attempted to take their lives, and the Post Office identified 13 deaths it could not rule out as connected [1]. Convictions brought imprisonment, bankruptcy, and loss of good character; three appellants died before their convictions were quashed [5].
- **Courts and legislation.** 39 convictions quashed in April 2021 [5]; further successful appeals through 2021 and at Southwark Crown Court [1]; the 2024 Acts exonerating "hundreds of persons" by statute [1]; an Overturned Convictions Scheme with 111 claimants [1].
- **Money.** The £57.75m Group Litigation settlement, from which the claimants' recovery was "far less than was necessary" once costs were taken [1]; four successive redress schemes (HSS, OCS, GLOS, HCRS) whose difficulty POL and the Department, in the Chair's words, "simply failed to grasp" [1].
- **Institutions.** A statutory inquiry whose first volume is devoted to human impact and redress [1]; continuing scrutiny of POL and Fujitsu in later volumes; a public reckoning — including the television drama *Mr Bates vs The Post Office* — that turned the case into national political events [1].

## What Changed — Operator and Industry

**The courts re-weighted the presumption.** The 2021 appeal established that where the reliability of computer data was essential to a prosecution, undisclosed defects made a fair trial impossible and the conviction unsafe (Ground 1), and that prosecutions conducted in this manner could be an affront to the public conscience — an abuse regardless of guilt or innocence (Ground 2) [5]. "It worked in every previous prosecution" ceased to be an argument and became, in the Court of Appeal's framing, part of the misconduct [5].

**Parliament removed the presumption entirely for the affected class.** The Post Office (Horizon System) Offences Act 2024 quashed specified convictions by operation of law in England, Wales, and Northern Ireland, with a Scottish equivalent, and a dedicated redress scheme followed [1]. Exoneration by statute is an extraordinary remedial instrument — an admission that ordinary process could not repair the failure at scale.

**The inquiry institutionalized the accounting.** Volume 1 (July 2025) formalizes the human impact on the public record and targets its recommendations at the redress machinery; the system's own story awaits the later volumes [1]. For the industry, the case has become the reference point for two governance demands: that technical evidence relied on by private prosecutors be disclosed and challengeable, and that systems whose outputs carry legal consequences be built and logged as if every record will be read aloud in court — because one day it will be.

## Lessons for Engineers

1. **An audit log you cannot produce is not evidence.** Horizon's records were authoritative in court because POL and Fujitsu were the only parties who could interrogate them — and the records of remote access were inadequate [3]. Logs that carry legal or financial consequences need retention, tamper-evidence, and a disclosure path that does not run exclusively through the party with an interest in the outcome.
2. **A system that can ruin a user must be able to say "it was me."** Horizon's failure to alert SPMs to its own defects [3] inverted the default hypothesis at every support interaction. Surface machine-side explanations for unexplained deltas first; make "user error" an affirmative, evidenced finding, never a catch-all [3].
3. **Vendor attestation is not verification.** POL built prosecutions on Fujitsu witness statements about a system whose defect history, closure codes, and access logs Fraser found unreliable [3]. When a supplier certifies its own product's integrity, require independent, data-backed confirmation — the discipline the [Toyota unintended acceleration case](./toyota-unintended-acceleration.md) shows being skipped, at scale, by a regulator.
4. **Watch the corrective plumbing as a symptom.** Over 2,000 transaction corrections per week [3] was the system quietly confessing that its accounts were not trustworthy. Aggregate correction volume, forced adjustments, and manual overrides are reliability signals; routing them into an invisible back channel converts a measurable defect into an unmeasurable one.
5. **Design for the adversarial read.** Remote-access powers without adequate logging [3] meant no one could later prove what happened in a branch. If an action in your system could ever be disputed, it must leave evidence a third party can evaluate without trusting the system's operator.
6. **Investigate the first "impossible" report as if the institution's integrity depended on it.** The complaints began almost at rollout [1]; each was resolved locally against the reporter. The counterfactual is [postmortem culture](../../sre/postmortem-culture.md): aggregate anomalies, reproduce them, and let the evidence pick the hypothesis — before the institution's story hardens into a prosecutorial one.

## Connection to This Repository

- [Therac-25](./therac-25.md) — the manufacturer that denied its machine could harm; here operator and vendor denied the machine could err, and the denial became prosecutions.
- [Knight Capital, 2012](./knight-capital-2012.md) — a warning signal routed to nobody; Horizon's support channel is the same shape, with liberty rather than money at stake.
- [Toyota unintended acceleration](./toyota-unintended-acceleration.md) — a regulator accepting vendor attestations until adversarial source-code review reframed the truth.
- [Mars Climate Orbiter, 1999](./mars-climate-orbiter-1999.md) — an interface assumption no one validated: that the ledger's data provenance was sound.
- [Postmortem culture](../../sre/postmortem-culture.md) — what a statutory inquiry shares with a blameless postmortem: evidence, aggregation, and the willingness to reproduce.
- [Common failure modes](../../failure-modes/common-failures.md) — the generic "trusted component presumed correct" and evidence-asymmetry patterns.
- [Architecture overview](../../arch/overview.md) — layering reconciliation, alerting, and audit so no component is its own witness.

## Interview Questions

1. Your platform's records are routinely used to charge customers for losses. What properties — retention, tamper-evidence, access logging, disclosure tooling — must those records have before you treat them as evidence, and how would you validate each one?
2. Horizon never alerted users to its own bugs, and support defaults to "user error." Design the detection and triage flow that makes "the system did it" an evidenced, reproducible finding rather than a denial.
3. A supplier certifies the integrity of the system you operate on. Construct the verification regime — data, process, independent review — you would run before letting that certification stand in for your own tests.
4. A remote-access role in your production system can modify user-visible state. What must exist around it so that, three years later, an independent party can determine exactly what happened in a specific account?

## Key Takeaways

- A computer system became a legal instrument without evidentiary properties: bugs caused phantom shortfalls [3], the system could not alert users to its own defects [3], the vendor's records of its own interventions were inadequate [3], and the party with the incentive controlled every source of truth [1][5].
- The presumption of machine correctness did the damage; the 2021 ruling dismantled it by making undisclosed system defects a ground for quashing convictions [5], and Parliament later removed the presumption wholesale by statute [1].
- The system's own behavior — 100,000+ transaction corrections per year [3] — was a standing confession that its accounts were unreliable; nobody was watching the number that mattered.
- "It has won every prosecution" is a governance alarm, not a track record [5]: a flawless win rate on machine-produced evidence should trigger adversarial review of the machine.
- Redress came decades late and cost multiples of what early investigation would have [1] — the arithmetic every organization should run on the cost of believing its own systems.

## Sources

1. The Post Office Horizon IT Inquiry, *Report of the Post Office Horizon IT Inquiry, Volume 1* (HC 1119; presented to Parliament pursuant to section 26 of the Inquiries Act 2005; printed 8 July 2025). https://www.postofficehorizoninquiry.org.uk/sites/default/files/2025-07/Post%20Office%20Horizon%20IT%20Inquiry%20Final%20Report%20Volume%201_0.pdf (fetched and quoted; URL verified live this session)
2. The Post Office Horizon IT Inquiry, official website (report library and hearings record). https://www.postofficehorizoninquiry.org.uk (verified live this session)
3. Mr Justice Fraser, *Bates and Others v Post Office Limited, Judgment (No.6) "Horizon Issues"*, [2019] EWHC 3408 (QB), 16 December 2019. https://www.judiciary.uk/wp-content/uploads/2019/12/bates-v-post-office-judgment.pdf (fetched and quoted)
4. *Alan Bates and Others v Post Office Limited, Judgment (No.3) (Common Issues)*, [2019] EWHC 606 (QB). Cited by neutral citation (as referenced in [1], footnote 10; no URL used)
5. *Josephine Hamilton and Others v Post Office Limited* [2021] EWCA Crim 577 (Holroyde LJ, Picken J, and Farbey J; 23 April 2021). https://www.judiciary.uk/wp-content/uploads/2022/07/Hamilton-Others-v-Post-Office-judgment-230421.pdf (fetched and quoted)
6. *Post Office Horizon Appeals (Ambrose and Others)* [2021] EWCA Crim 1443 (October 2021). Cited by neutral citation (no URL used)

## Cross-References

- [Therac-25, 1985–87](./therac-25.md) — institutional denial in the face of user harm; the original "the machine must be right" template.
- [Knight Capital, 2012](./knight-capital-2012.md) — diagnostic truth present in the system but routed to nobody; alerts that were never alerts.
- [Toyota unintended acceleration, 2009–2011](./toyota-unintended-acceleration.md) — regulator trust in vendor attestations, broken by adversarial code review.
- [Mars Climate Orbiter, 1999](./mars-climate-orbiter-1999.md) — the unvalidated interface assumption as the seed of catastrophic misreading.
- [Postmortem culture](../../sre/postmortem-culture.md) — the investigative discipline whose absence let local denials harden into national injustice.
- [Incident response](../../security/incident-response.md) — evidence, scope, and disclosure when incidents acquire legal dimensions.
- [Common failure modes](../../failure-modes/common-failures.md) — trusted-component and evidence-asymmetry patterns in generic form.
- [Architecture overview](../../arch/overview.md) — layering reconciliation, alerting, and audit so no single component is its own witness.
