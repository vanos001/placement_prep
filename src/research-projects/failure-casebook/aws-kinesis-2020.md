# AWS Kinesis, November 25, 2020: A Thread Limit, a Fully-Meshed Front End, and a Day-Long Region Event

## Overview

On November 25, 2020, Amazon Kinesis in the US-EAST-1 region began failing PUT and GET operations and did not fully recover for roughly twenty hours. AWS's own post-incident summary — the sole source for this page — states that a "relatively small addition of capacity" to Kinesis's front-end fleet, applied between 2:44 AM and 3:47 AM PST, pushed every server in that fleet past an operating-system thread limit [1]. The servers' shard-map caches could no longer be built, so front-end servers could not route requests to the back-end clusters that actually process streams. Recovery required carefully restarting thousands of front-end servers at a rate of only a few hundred per hour; Kinesis returned to normal at 10:23 PM PST [1].

Because Kinesis sits underneath other AWS services, the failure cascaded: Cognito could not authenticate users or issue temporary credentials, CloudWatch dropped the vast majority of metrics and pushed alarms to INSUFFICIENT_DATA, Lambda hit error rates from memory contention caused by buffered metrics, and CloudWatch Events/EventBridge delayed event delivery that ECS and EKS depend on [1]. The event is a textbook study in how a shared, fully-meshed control tier converts a routine capacity change into a fleet-wide outage — and why the cellularization that protected Kinesis's back end did not yet protect its front end.

## System Context

Amazon Kinesis enables real-time processing of streaming data, and — critically for this incident — is also an internal building block for several other AWS services [1]. The service has a two-tier architecture that AWS describes in the postmortem. The "back end" consists of a large number of cell-clusters that process streams; each back-end cluster owns many shards and is a "consistent scaling unit and fault-isolation" boundary [1]. The "front end" is a separate fleet of servers whose job is "small but important": authentication, throttling, and request-routing to the correct stream-shards on the back-end clusters [1]. All customer traffic to Kinesis in the region passes through this front end.

Each front-end server maintains a cache called a shard-map — membership details and shard ownership for the back-end clusters [1]. That cache is assembled from three sources: a microservice that vends membership information, configuration retrieved from DynamoDB, and continuous message processing from other Kinesis front-end servers [1]. The last source is the structural detail that matters most: each front-end server creates operating-system threads for each of the other servers in the front-end fleet, and it takes up to an hour for an existing member to learn of new participants [1]. In other words, the front end behaves as a fully-connected mesh whose per-server resource consumption grows with fleet size — the post states this explicitly when it notes that "the total threads each server must maintain is directly proportional to the number of servers in the fleet" [1].

AWS had already cellularized the back end, and cellularization of the front end "had been under way... but unfortunately the work is significant and had not yet been completed" [1]. So on the morning of the event, one shared front-end fleet served the region's entire Kinesis workload, plus internal dependencies for services like CloudWatch that were still co-located on it [1].

## What Happened

The sequence below is drawn entirely from AWS's post-incident summary [1]; all times are PST on November 25, 2020, as AWS states them.

| Time (PST, Nov 25, 2020) | Event | Source |
|---|---|---|
| 2:44 AM | Capacity addition to the front-end fleet begins | [1] |
| 3:47 AM | Capacity addition completes | [1] |
| 5:15 AM | First alarms fire for errors on putting and getting Kinesis records | [1] |
| 7:51 AM | Root cause narrowed to a couple of candidates; all candidates require a full front-end fleet restart; work begins in parallel on a configuration to fetch cache data directly from the authoritative metadata store during bootstrap | [1] |
| 9:39 AM | Root cause confirmed: the new capacity caused every server in the fleet to exceed the maximum number of threads allowed by an operating-system configuration; shard-map construction was failing, leaving servers with useless shard-maps | [1] |
| 10:07 AM | First group of restarted front-end servers begins taking traffic | [1] |
| ~noon | Kinesis error rate steadily dropping from noon onward | [1] |
| 10:23 PM | Kinesis fully returned to normal | [1] |

CONFIRMED details around the main timeline: as a precaution the new capacity was removed while other errors were researched, but diagnosis was slowed because errors appeared "in all aspects of the various calls being made by existing and new members of the front-end fleet," making side-effects hard to separate from the root cause [1]. Restart had to be throttled because the resources a front-end server uses to populate its shard-map compete with the resources used to process incoming requests; servers brought back too quickly would look unhealthy and be removed, setting recovery back [1]. The front end comprises "many thousands of servers," and only a few hundred per hour could be added [1].

CONFIRMED dependent impacts: Cognito's best-effort Kinesis streaming, buffered locally, hit a latent bug under prolonged Kinesis unavailability — its web servers began blocking on backlogged buffers, causing elevated API failures for Cognito User Pools and Identity Pools that prevented users from authenticating or obtaining temporary AWS credentials; error rates rose significantly by 7:01 AM, a dependency-reducing change began deploying at 10:15 AM, impact was significantly reduced by 12:15 PM, and Cognito operated normally by 2:18 PM PST [1]. CloudWatch, which uses Kinesis to process metric and log data, saw elevated PutMetricData and PutLogEvents errors and alarms moving to INSUFFICIENT_DATA from 5:15 AM, with full recovery at 10:31 PM PST and backfilling over subsequent hours [1]. Lambda's metric agents buffer metric data locally when CloudWatch is unavailable; from 6:15 AM the buffers grew until they caused memory contention on invocation hosts and increased function error rates, mitigated by 10:36 AM [1]. CloudWatch Events and EventBridge had increased API errors and event-delays from 5:15 AM, and because ECS and EKS use EventBridge to drive internal workflows, cluster provisioning, scaling, and task de-provisioning were impacted until the majority of issues resolved by 4:15 PM [1]. AWS also could not update the Service Health Dashboard early in the event because the posting tool itself uses Cognito [1].

## Technical Mechanism

The failure mechanism is an operating-system resource limit meeting an O(N) control-plane design. Every front-end server keeps one operating-system thread per peer front-end server, used to exchange the messages from which each server builds its shard-map [1]. When the fleet grows by a handful of servers, every existing server must create a handful of new threads. When the addition pushed the fleet past the configured thread maximum, cache construction "failed to complete" fleet-wide and front-end servers ended up "with useless shard-maps that left them unable to route requests to the correct stream-shards on the back-end clusters" [1]. The capacity change did not overload any single server; it changed a global property — fleet size — that every server's thread budget depends on:

```
front-end server S(i) maintains one OS thread per peer:
    threads(S_i) = N - 1        (N = fleet size)
    cache(S_i)   = shard-map built from N-1 peer message feeds
                   + membership microservice + DynamoDB config
add 1 server  ->  every server needs 1 more thread
cross the OS thread limit  ->  cache construction fails on ALL servers
                           ->  no shard-map, no routing, region-wide PUT/GET errors
```

INTERPRETATION: this is the arithmetic of a shared fate domain. Any resource that scales with fleet size — threads here, but it could be connection pools, timers, or file descriptors — turns "add a few servers" into a change that every existing server must absorb simultaneously. AWS's remediation confirms the diagnosis: moving to "larger CPU and memory servers, reducing the total number of servers and, hence, threads required by each server" works precisely because fewer servers means a smaller N [1].

The second mechanism is recovery contention. Shard-map population and request processing draw on the same server resources, so restarting servers quickly produces slow, cache-cold servers that health checks remove from the fleet — which resets their bootstrap progress and "would set back the recovery process" [1]. Hence the few-hundred-servers-per-hour ramp against a fleet of many thousands, and hence the ~20-hour tail after a root cause was confirmed at 9:39 AM. The third mechanism is diagnostic: with every server partially broken, the error stream mixed genuine symptoms with side-effects, and the team could not at first distinguish errors "that were unrelated to the new capacity" from the core failure [1]. The eventual fix strategy — bootstrap shard-maps directly from the authoritative metadata store instead of from neighbors — attacks the mesh dependency itself [1].

## Trigger vs Contributing Factors

The trigger is unambiguous, and AWS labels it precisely: "The trigger, though not root cause, for the event was a relatively small addition of capacity" applied over about an hour starting at 2:44 AM PST [1]. A routine, small scaling action is the spark.

The contributing factors are structural. First, the fully-meshed front end: per-server thread consumption proportional to fleet size means the fleet had an implicit capacity limit measured in servers, not requests — a limit invisible until crossed [1]. Second, incomplete cellularization: the back end was already partitioned into fault-isolated clusters, but the front end was a single shared fleet serving all of Kinesis, including internal traffic from large services like CloudWatch [1]. Third, a cache whose construction path shares resources with the request path, which made both the failure mode (cache construction starved) and the cure (restarting servers) rate-limited by the same contention [1]. Fourth, observability gaps: alarms existed and fired at 5:15 AM, but thread consumption specifically had no fine-grained alarm — AWS lists adding one among the immediate learnings [1]. Fifth, a diagnostic environment where every call path was erroring at once, which slowed the isolation of root cause for over four hours [1]. INTERPRETATION: none of these factors is a defect on its own; each was a reasonable engineering choice that happened to compose badly. That composition — small change times dense coupling times untested limit — is the general shape of the incident.

## Why Safeguards Didn't Prevent It

- **Back-end cellularization** existed and worked as a fault-isolation boundary for stream processing — but the front end was not yet cellularized, so the shared shard-map cache tier had no cell wall to stop the propagation [1]. AWS's own remediation is to "greatly accelerate the cellularization of the front-end fleet to match what we've done with the back-end" [1].
- **Redundant cache inputs** (membership microservice, DynamoDB, peer messages) provided source diversity, but all three population paths ran inside the same thread budget on each server; diversity of inputs cannot compensate for a shared compute limit [1]. INTERPRETATION: the redundancy protected against any one source being wrong, not against the cache-building process itself failing.
- **Precautionary rollback** of the added capacity was performed, but it could not undo the state change: thread counts fell back under the limit, yet the fleet's caches were already broken and the recovery path (restart) remained [1]. Rolling back the trigger is not rolling back the effect.
- **Health checks and automatic removal**, normally protective, actively threatened recovery: fast-restarted servers looked unhealthy and would have been removed, so the restart had to be artificially slow [1]. The safeguard tuned for steady state misfired during recovery.
- **Alarming** caught the customer-visible symptom (PUT/GET errors at 5:15 AM) but not the proximity signal (thread consumption approaching the OS limit) — the event ran for nearly three hours before the first alarm and four more hours to confirmed root cause [1].
- **The status-communication tooling** was itself a casualty: the Service Health Dashboard posting tool used Cognito, which was impacted, so AWS fell back to a manual backup tool that operators were less familiar with, delaying customer updates [1]. The safeguard for communicating about an outage depended on a service inside the outage.

## Lessons & Mitigations

1. **Cellularize the front end, not just the back end.** The most repeated word in AWS's remediation is partitioning: a dedicated cache fleet, a separate front-end partition for large internal consumers like CloudWatch, and accelerated cellularization so the shard-map cache "operat[es] within a previously tested and operated range" [1]. The lesson generalizes: fault isolation must cover every tier that all requests transit, not only the data-processing tier. This is the core argument of [cell architecture](../../sre/cell-architecture.md).
2. **Treat fleet size as a capacity dimension.** Capacity planning usually reasons about request volume; here the binding constraint was the number of peers per server. Any design where per-server state or fan-out grows with fleet membership needs an explicit, alarmed budget — the same discipline as any other [capacity planning](../../sre/capacity-planning.md) exercise [1].
3. **Bootstrap from the authoritative source.** The mitigation built during the event — fetching membership data directly from the authoritative metadata store during bootstrap rather than from neighbors — removes the peer-to-peer dependency from the most fragile moment of a server's life [1]. Cold-start paths deserve simpler dependency graphs than steady-state paths.
4. **Plan the restart rate before you need it.** Recovery contention made a full-fleet restart a multi-hour, deliberately throttled operation [1]. If a component's recovery is self-throttling, that rate belongs in the design — in runbooks, in [incident management](../../sre/incident-management.md) drills, and in the architecture review, not discovered mid-incident.
5. **Best-effort buffering needs backpressure.** Cognito's local buffering of Kinesis writes was designed to ride out short unavailability; a prolonged outage triggered a latent bug and turned buffering into blocking [1]. Components that degrade gracefully for minutes must be tested for hours — this is the [bulkhead](../../sre/bulkheads.md) and load-shedding question applied to internal dependencies.
6. **Decouple the incident-response plane.** A health dashboard that depends on an impacted service cannot report on the outage of that service; AWS retrained operators on a low-dependency backup tool and moved CloudWatch to keep 3 hours of metrics locally so Auto Scaling and Lambda would keep working during metric-pipeline failures [1].

## Interview Questions

1. Kinesis's front end kept one OS thread per peer server, so fleet growth consumed resources on every existing server. What other familiar designs have per-node costs proportional to fleet size, and how would you bound or eliminate them?
2. AWS could confirm root cause only at 9:39 AM, four-plus hours after alarms. The post says errors "in all aspects" of front-end calls made side-effects hard to separate from the root cause. What observability would have separated them faster?
3. Recovery required restarting thousands of servers slowly because fast restarts produced "unhealthy" servers. How would you design a health check that distinguishes "cold and loading" from "broken"?
4. Cognito buffered Kinesis writes as best-effort and failed anyway under a prolonged outage. How do you test and bound graceful degradation so it survives an outage an order of magnitude longer than designed?
5. The Service Health Dashboard's posting tool depended on Cognito. Where should the "incident communication plane" sit in a dependency graph, and what does its failure cost during a major event?

## Key Takeaways

- A "relatively small addition of capacity" to a fully-meshed front-end fleet pushed every server past an OS thread limit; shard-map construction failed fleet-wide and Kinesis PUT/GET operations errored from 5:15 AM until 10:23 PM PST on November 25, 2020 [1].
- The back end was cellularized; the front end was not — one shared cache-and-routing tier propagated a local change region-wide, and AWS's remediations (dedicated cache fleet, partitioned front end for CloudWatch, accelerated cellularization) are all partitions [1].
- Recovery was bounded by contention between cache population and request handling: a few hundred servers per hour, thousands of servers, ~20 hours total [1].
- The cascade ran through Kinesis's dependents — Cognito (buffering bug, authentication failures), CloudWatch (metric and alarm gaps), Lambda (memory contention from buffered metrics), EventBridge and the ECS/EKS workflows above it — and even reached the dashboard used to report the event [1].
- Read together, the event argues that fault isolation, resource budgeting, and recovery-rate design are one discipline, each present in one tier and absent in the tier above it.

## Sources

1. AWS, "Summary of the Amazon Kinesis Event in the Northern Virginia (US-EAST-1) Region," aws.amazon.com/message/11201/ (published November 25, 2020, updated December 2020). https://aws.amazon.com/message/11201/ — fetched and quoted in full; all timestamps, mechanisms, dependent-service impacts, and remediations on this page are from this statement. AWS labels the capacity addition as "the trigger, though not root cause"; the page's architectural inferences beyond the statement (mesh arithmetic, shared-fate interpretation) are labeled INTERPRETATION above.

This page is deliberately single-source. AWS's post-incident summary is the first-party account, and everything material traces to it. Where the statement is silent — the specific operating-system limit and its value, the exact fleet size, per-customer impacts, external measurements of the outage — this page is silent too. No secondary coverage is cited, and figures circulating in contemporaneous reporting that do not appear in the statement are not used. The URL was fetched in full during the writing of this page; quotations are verbatim.

## Cross-References

- [AWS DynamoDB, 2015](./aws-dynamodb-2015.md) — a metadata-plane disruption cascading into dependent services; Kinesis's shard-map even reads configuration from DynamoDB, so the two incidents share a substrate.
- [AWS S3 us-east-1, 2017](./aws-s3-us-east-1-2017.md) — a subsystem supporting the main service failing and taking the region's API surface with it.
- [AWS us-east-1, 2021](./aws-us-east-1-2021.md) — internal automation and recovery dynamics prolonging a region event; the closest sibling in recovery-shape.
- [Cloudflare Workers KV, 2025](./cloudflare-june-2025.md) — a storage dependency behind a platform product cascading into the products built on it.
- [Cell architecture](../../sre/cell-architecture.md) — the pattern AWS names as the fix: isolate failure within a service by construction.
- [Bulkheads](../../sre/bulkheads.md) — partitioning and degradation for the buffering and metric-agent failures in Cognito and Lambda.
- [Thread pools](../../concurrency/thread-pools.md) — why thread budgets are finite, how exhaustion manifests, and sizing per-server resources against fleet-wide fan-out.

The four sibling cases bracket this incident: DynamoDB 2015 and us-east-1 2021 supply the dependency-cascade and recovery-shape mechanics inside AWS's own fleet, S3 2017 shows a supporting subsystem taking a region down with it, and the Cloudflare KV case repeats the pattern at another company. The three repository pages carry the theory: cell architecture for the partition AWS says it will build, bulkheads for the buffering failures downstream, and thread pools for the resource whose limit was crossed.
