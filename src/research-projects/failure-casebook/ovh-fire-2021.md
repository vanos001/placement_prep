# OVHcloud Strasbourg, March 10, 2021: A Datacenter Fire, 120,000 Services, and the Limits of Digital Redundancy

## Overview

At 00:47 CET on Wednesday, March 10, 2021, a fire broke out in a room at SBG2, one of OVHcloud's four datacenter buildings in Strasbourg, France. OVHcloud's own communications — the sole primary source for this page — record that by 04:09 the fire had destroyed SBG2 and "continued to present risks to the nearby datacenters" until the fire brigade brought it under control; SBG1 was partially damaged (4 of its 12 rooms destroyed), while SBG3 and SBG4 were switched off but undamaged [1]. No one was injured. In OVHcloud's 23 April 2021 situation update, the company estimated that 120,000 customer services had been fully or partially affected, with 113,000 fully recovered by that date; 14,046 servers in operation in SBG2 were destroyed [1].

The distinctive feature of this incident is that the destructive agent was physical. Fire does not respect VLANs, replicas, or availability zones declared in a control panel: it destroyed the building in which customer servers, and — for many customers — the only copies of their data, were located. Recovery was not a failover but an industrial campaign: firefighters required electrical power cut for the entire four-building site before operating; surviving servers had to be cleaned of soot and rebooted room by room, aisle by aisle, rack by rack, server by server; and data in the destroyed building could be pursued only by physically recovering hard drives from the fire-affected rooms [1]. The cause of the fire was still under investigation in the company's last update on this page [1].

## System Context

OVHcloud is a vertically integrated European cloud provider: the company operates its own server factories in France and Canada, and its communications from the period describe a fleet of roughly 400,000 servers across 32 datacenters [1]. The Strasbourg campus (SBG) comprised four datacenter buildings, SBG1 through SBG4, with SBG5 under construction. Customers ran services across OVHcloud's product lines — Bare Metal (dedicated physical servers), VPS, Public Cloud, and Hosted Private Cloud — many of them single-tenant workloads provisioned into one building [1]. This is the model described in [bare-metal clouds](../../cloud/bare-metal-clouds.md): maximum customer control over hardware, with the operational responsibilities that entails.

That division of responsibility is central to understanding the blast radius. OVHcloud's updates repeatedly describe supporting SBG2 customers "with replacement solutions, as well as implementing their disaster recovery plans" and "offer support for customers in implementing their Disaster Recovery Plan (DRP) mechanisms" [1] — that is, for a large share of the affected services, off-building replication was the customer's arrangement to make, not a property of the product. OVHcloud's own managed backups for some product lines existed (the company's status tables list Veeam Cloud Connect and Veeam Managed Backup among restored Hosted Private Cloud services, and note that backups "hosted on Public Cloud Storage services" would become available as those services restarted) [1]. But a backup hosted in the same site as the primary is not an independent copy in any physical sense — a theme this incident made infamous. Widely reported accounts of OVHcloud's customer communications state that backups stored in the same building as the affected services were lost with them; that specific statement circulated via OVHcloud status updates and social media and is treated here as reported but not verified against a fetched primary source.

## What Happened

The timeline below is drawn from OVHcloud's rolling press release, which carries dated entries from 10 March through 23 April 2021 [1]. Times are CET as stated by the company.

| Time (CET, 2021) | Event | Source |
|---|---|---|
| Mar 10, 00:47 | Fire breaks out in a room in SBG2; firefighters intervene | [1] |
| Mar 10, 02:54 | Site isolated; perimeter closed off | [1] |
| Mar 10, by 04:09 | Fire had destroyed SBG2 and continued to present risks to nearby datacenters until brought under control | [1] |
| Mar 10, 05:30 | Site unavailable to OVHcloud teams for security reasons, under prefecture direction | [1] |
| Mar 10 (daytime) | 2,000-server stock released from Roubaix/Gravelines for customer migration; ~10,000 new servers announced for production | [1] |
| Mar 17 | Gradual restart of SBG1, SBG3, SBG4 begins under a stringent safety protocol | [1] |
| Mar 19 | Smoke detected in an SBG1 battery room; power cut again to SBG1 and SBG4; firefighters intervene at 7 pm; service resumption delayed | [1] |
| Mar 22 | Restarted services resume; reboot protocol proceeds room by room, rack by rack, server by server | [1] |
| Mar 16–Apr 16 | Soot cleaning campaign: 80+ specialists, 600–700 servers per day, ~7 hours per rack; billing stopped for affected services; vouchers prepared | [1] |
| Apr 23 | OVHcloud estimates 120,000 services fully or partially affected; 113,000 fully recovered; 14,472 replacement Bare Metal servers delivered; 30,775 VPS restored | [1] |

CONFIRMED details from the same source: smoke was detected in the energy rooms and teams responded "according to the protocol in place" for those rooms; firefighters "arrived on site very quickly," but their operations "could only be carried out after the electrical power was switched off for the entire site, including all four datacentres" [1]. SBG3 and SBG4 servers were switched off but undamaged; the restart from 17 March proceeded under a safety protocol, interrupted on 19 March by the battery-room smoke, with services resuming 22 March [1]. Data recovery specialists worked "to try and recover data from hard drives in the rooms affected by the fire" [1]. OVHcloud reviewed footage from 300 site surveillance cameras as part of its lessons-learned work; investigations by authorities and insurers into the fire's cause and spread were ongoing and expected to take months; the company committed to rebuilding SBG1, SBG2, and SBG4 "on the basis of new standards" and to sharing expert-review findings [1]. Reuters reporting the same day headlined that millions of websites were offline after the fire at the French cloud firm [2].

## Technical Mechanism

The mechanism of this failure is blast radius in the physical sense. Digital redundancy is defined by independence of failure domains, and the failure domain that matter maps to is the building. Two services are independent only if no single event can break both; a fire in one room of one building broke every service whose entire existence — primary copies, and for many customers the only backups — was inside SBG2. The four SBG buildings were geographically distinct, but they were not operationally independent: firefighting required cutting electrical power "for the entire site, including all four datacentres" [1], so the remaining three buildings went dark in a correlated shutdown. The campus behaved as one failure domain exactly when it mattered most.

```
SBG campus, one electrical + fire perimeter:
  SBG1 (partially burned: 4/12 rooms)  --power cut--.
  SBG2 (destroyed; data recoverable only            }  ONE physical
        via hard-drive recovery)                     }  failure domain
  SBG3 (undamaged, powered off)                     }  = the site
  SBG4 (undamaged, powered off)                     }  (firefighting)
customer with primary in SBG2 + backup in SBG2       ->  lost both
customer with primary in SBG2 + backup elsewhere     ->  survivable
customer with everything outside SBG                 ->  unaffected
```

INTERPRETATION: the incident also demonstrates that physical recovery is an industrial process with its own throughput limits. Servers in SBG1 and SBG3 had to be uninstalled, cleaned, inspected, and reinstalled in a fixed sequence — 7 hours per rack — before they could take traffic; smoke in a battery room re-cut power to SBG1 and SBG4 on 19 March and pushed resumption to 22 March [1]. Restarting a datacenter is closer to remanufacturing than to rebooting: every step consumes specialist labor (80+ cleaning specialists, 600–700 servers per day), logistics (express containers for network and high-voltage power shipped from the Croix factory), and production capacity (Croix's rate doubled from 1,500 to 3,000+ servers per week to replace the 14,046 destroyed) [1]. None of these quantities can be scaled by configuration. Finally, data in SBG2 was reachable, if at all, only through physical media recovery from fire-affected rooms [1] — the endpoint of any redundancy design in which all copies shared the building.

## Trigger vs Contributing Factors

The trigger is the ignition itself, at 00:47 CET on 10 March, with smoke detected in the energy rooms [1]. Critically, the cause was not established by the primary source: OVHcloud states that investigations by the authorities and insurance companies were ongoing and expected to take months, and it committed to publishing expert-review findings [1]. This page accordingly makes no claim about what ignited.

The contributing factors are what turned a building fire into a mass service-loss event. First, single-site tenancy: a large population of customer services had no off-site copy, because for those products disaster recovery was a customer-implemented mechanism [1]. Second, backup colocation: where backups existed on OVHcloud infrastructure in Strasbourg — for example, backups hosted on Public Cloud Storage services — they were unavailable until the Strasbourg services themselves restarted [1], and press accounts of OVHcloud's customer communications describe same-building backup loss (reported but unverified here). Third, site-level coupling: shared electrical infrastructure and a firefighting protocol requiring total site power-off made the four buildings one failure domain [1]. Fourth, recovery-path physics: soot contamination made restart a cleaning-and-inspection pipeline measured in racks per day, and a second smoke event delayed even that [1]. Fifth, external constraints: prefecture-controlled site access from 05:30 and Covid-era logistics for workers complicated the response [1]. INTERPRETATION: remove any one of the first three factors and the same fire is a recoverable hardware loss instead of a six-week restoration campaign.

## Why Safeguards Didn't Prevent It

- **Detection and response worked, within their scope.** OVHcloud states that "our detection systems were instantly activated and our teams were able to respond according to the protocol in place for the energy rooms" [1]. Detection sensed smoke in seconds; it could not extinguish a building-scale fire. An alarm is a sensor, not a barrier.
- **Fire containment** prevented spread beyond the campus and protected life — no injuries — but SBG2 was destroyed by 04:09 and SBG1 lost four of twelve rooms [1]. Containment bounded the physical damage; it did not bound the service damage, because service damage had been outsourced to whatever redundancy customers had (or had not) arranged.
- **Multi-building presence** was real — SBG3 and SBG4 stood undamaged — yet it provided no service continuity for SBG2 tenants, because provisioning, not architecture, decides whether a customer's service spans buildings [1]. Redundancy that the workload does not use is decoration.
- **Provider-managed backups** existed for some product lines, but their placement shared the site's fate: backups hosted on Public Cloud Storage in Strasbourg returned only as those services restarted, and OVHcloud's own DRP-support messaging implies customers' alternatives were their own arrangements [1].
- **The restart safety protocol** — full power-off for firefighting, stringent re-energization rules, the 19 March battery-room smoke event — repeatedly paused recovery [1]. Safety interlocks during physical incidents are correct behavior, but they mean recovery time is governed by physical-system checks no software runbook anticipates.
- **Communication channels** scaled reasonably (status platform, FAQ, daily updates, real-time rack-level restart monitoring at vms.status-ovhcloud.com/sbg/), yet the company still had to manage expectations across six weeks of restoration, free pricing measures, and stopped billing [1]. No communication safeguard can substitute for lost data.

## Lessons & Mitigations

1. **The building is a failure domain; plan for it to burn.** Availability-zone thinking must extend to physical infrastructure: if all copies of a service sit in one building, the design's real failure domain is that building. True independence means distinct sites with distinct power, network, and organizational perimeters — the multi-region discipline in [multi-region design](../../sre/multi-region.md) and the physical-isolation argument of [bulkheads](../../sre/bulkheads.md).
2. **A backup that shares a site with its primary is not a backup.** The generalizable rule: a restore path is only as independent as its most-colocated copy. Verify where backups physically live, who can destroy them simultaneously with the primary, and rehearse [disaster recovery](../../cloud/disaster-recovery.md) from the off-site copy — including the case where the provider itself is the disaster.
3. **Provider failure is a scenario, not a hypothetical.** The affected customers faced replacement hardware, changed IP addresses, and DRP execution under emergency conditions [1]. Architecture reviews should include a "provider loses a site" scenario with an explicit, tested exit path — data egress, DNS, and re-provisioning automation — rather than assuming provider-level redundancy.
4. **Recovery throughput is a designed quantity.** This restoration ran at 600–700 servers cleaned per day, 7 hours per rack, weeks of server production — all physical limits [1]. For any estate, know the physical recovery rate (spares, cleaning, logistics, people) and size expectations accordingly; recovery-time objectives for physical disasters must be derived from these rates, not from software restart times.
5. **Correlated shutdown is part of the blast radius.** Firefighting cut power to all four datacenters, and a later battery-room smoke event re-cut it [1]. Adjacent "healthy" sites in a shared perimeter will go down with the wounded one; perimeters — electrical, fire-suppression, organizational — define domain boundaries as much as geography does.
6. **Separate the physical and digital incident-response planes.** The response combined firefighters, prefecture access control, environmental experts, civil engineering, and data-recovery specialists with customer communication at scale [1]. Physical incidents demand [incident management](../../sre/incident-management.md) structures that can run an industrial recovery and a communication campaign in parallel — a different shape from the purely technical incident this casebook's other cases describe.

## Interview Questions

1. A customer runs production in one datacenter with nightly backups to storage in the same building. Walk through which single events destroy both copies, and design a backup topology whose restore path survives a building-scale fire.
2. Firefighters required the entire four-building site to be de-energized. How does a shared physical perimeter (power, fire suppression, access control) change the effective size of an availability zone, and how would you represent that in architecture diagrams?
3. OVHcloud's recovery was throughput-limited: 600–700 servers cleaned per day, 7 hours per rack. How would you set a realistic RTO for a physical disaster, and what would you measure to know it?
4. Many affected customers had no off-site copy because DR was their responsibility. Where should the line sit between provider-managed resilience and customer-managed DR, and how should a provider make that line unambiguous at purchase time?
5. Compare this incident with a purely digital cascade like the Kinesis 2020 event: what safeguards transfer between physical and digital disaster recovery, and which ones do not?

## Key Takeaways

- Fire at 00:47 CET on March 10, 2021 destroyed the SBG2 datacenter (14,046 servers in operation), damaged SBG1 (4 of 12 rooms), and forced a site-wide power cut across all four Strasbourg buildings for firefighting [1].
- OVHcloud estimated 120,000 services fully or partially affected; recovery was an industrial campaign — server cleaning at 600–700 per day, doubled factory production, data recovery from burned rooms — with 113,000 services recovered by 23 April and the cause still under investigation [1].
- The deep lesson is failure-domain honesty: a backup or replica colocated in the same site as its primary shares its fate, and adjacent buildings in one electrical/fire perimeter fail together [1].
- Digital safeguards (detection, containment, monitoring, communication) all worked as designed and none prevented mass service loss, because the redundancy customers needed had to exist outside the burned building before the fire started [1].
- The case sits deliberately at the physical end of this casebook's spectrum: every other mechanism here is defeated by logic or configuration, and this one is defeated by combustion — yet the design lesson, honest failure domains, is the same one the digital cases teach.

## Sources

1. OVHcloud, "Strasbourg datacentre: latest information," corporate newsroom press release, rolling updates from 10 March 2021 (11:00 CET first statement) through 23 April 2021. https://corporate.ovhcloud.com/en/newsroom/news/informations-site-strasbourg — fetched and quoted in full; all timestamps, damage assessments, service-impact figures, recovery statistics, and remediation commitments on this page are from this document. The cause of the fire is not established in the source; this page makes no claim about it.
2. Reuters, "Millions of websites offline after fire at French cloud services firm," March 10, 2021 — title and date verified via search at time of writing; not fetched, so cited by title+org+year without reliance on its contents beyond the headline scope of the outage.

The incident-tracking platform entry linked from the verified OVHcloud press release (network.status-ovhcloud.com/incidents/vlcqgm66ffnz) and the rack-level restart monitor (vms.status-ovhcloud.com/sbg/) are referenced as first-party resources named on the verified page but were not themselves fetched. Items marked *reported but not verified* — notably the widely reported statement that customer backups stored in the same building were lost with the affected services — come from contemporaneous press accounts of OVHcloud customer communications, are not quoted from a fetched primary source, and are excluded from all CONFIRMED claims. No cause-of-fire hypothesis appears on this page because no primary source states one.

## Cross-References

- [GitLab.com data loss, 2017](./gitlab-2017-data-loss.md) — every announced recovery mechanism failing when disaster strikes; the digital counterpart to colocated-backup loss.
- [GitHub, October 2018](./github-october-2018.md) — degradation resolved by backup-restore rather than failover, and the operational weight of restore-based recovery.
- [AWS us-east-1, 2021](./aws-us-east-1-2021.md) — how one provider region concentrates failure domains that customers implicitly share.
- [Facebook BGP, 2021](./facebook-bgp-2021.md) — a different layer's blast radius: physical-site loss versus control-plane self-isolation, both breaking "unaffected" redundant capacity.
- [Disaster recovery](../../cloud/disaster-recovery.md) — RTO/RPO planning, backup independence, and DR testing discipline this incident made concrete.
- [Multi-region](../../sre/multi-region.md) — designing service topologies whose domains survive the loss of an entire site.
- [Bulkheads](../../sre/bulkheads.md) — physical and logical partitioning as the general principle behind firewalls of every kind.

The sibling cases triangulate this one from three directions: GitLab 2017 and GitHub 2018 show digital disasters whose recoveries were throttled by restore mechanics the way SBG2's was throttled by cleaning mechanics; us-east-1 2021 and Facebook 2021 show how customers and sibling systems inside a supposedly shared-safe perimeter lose service anyway. The repository pages turn the fire into design language — disaster recovery for backup independence and rehearsed restore paths, multi-region for topology that survives site loss, and bulkheads for the partitioning principle underneath both.
