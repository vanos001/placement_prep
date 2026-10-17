# Cloudflare, July 2, 2019: Catastrophic Backtracking and a 27-Minute Global Outage

## Overview

On July 2, 2019, Cloudflare deployed a change to a WAF Managed Rule targeting cross-site scripting (XSS) detection. One regular expression in that rule backtracked catastrophically in the Lua WAF's PCRE engine, exhausting CPU on every core that served HTTP/HTTPS traffic across Cloudflare's worldwide network. Customers saw 502 errors on Cloudflare-proxied domains.

CONFIRMED (per Cloudflare's own post-incident post by John Graham-Cumming [1]): the outage lasted **27 minutes** — from the 13:42 UTC deployment to 14:09 UTC, when a "global terminate" of the WAF restored traffic levels and CPU usage worldwide. Cloudflare reported losing **80% of its traffic** during the incident and noted it was their first global outage in six years. The company subsequently re-introduced a CPU-usage protection that had been removed weeks earlier during refactoring, manually inspected all 3,868 WAF Managed Rules, and committed to moving off the backtracking PCRE engine to an engine with **linear-time run-time guarantees** (re2 or Rust regex).

The incident is the canonical case study for: catastrophic backtracking (why a regex can be an accidental denial-of-service against its own host), why *run-time guarantees* in the regex engine are the only robust fix, and the mechanics of a global kill switch when the kill switch itself is hard to reach.

## System Context

- **The edge fleet.** Cloudflare terminates HTTP/HTTPS for millions of domains across 180+ cities. The Lua WAF runs inside the edge proxy on every request; rules are deployed globally in seconds via **Quicksilver**, Cloudflare's globally replicated key-value store (p99 of 2.29 seconds for a change to reach every machine; roughly 350 configuration changes per second on average) [1].
- **The WAF deployment model.** WAF Managed Rules are updated continuously — 476 change requests in the 60 days before the incident, about one every three hours — because the WAF must respond quickly to new vulnerabilities. By design, the WAF **does not** follow the staged DOG/PIG/Canary rollout used for Cloudflare's other software: an SOP explicitly allows a rule change to go global in one step [1].
- **The engine.** "The Lua WAF uses PCRE internally, and it uses backtracking for matching and has no mechanism to protect against a runaway expression" [1]. Weeks before the incident, a refactoring intended to *reduce* WAF CPU usage accidentally **removed a protection** that would have prevented excessive CPU use by a regular expression [1].

## What Happened

| Time (UTC, Jul 2, 2019) | Event | Source |
|---|---|---|
| 13:31 | Engineer merges a pull request containing the new XSS-detection rule (after approval) | [1] |
| 13:37 | TeamCity builds the rules and runs the WAF test suite — a large collection of unit tests plus HTTP request/rejection corpora. It did **not** test for runaway CPU utilization; logs from prior builds show no runtime increase from this rule | [1] |
| 13:42 | TeamCity automatically deploys the change; the rule propagates globally via Quicksilver within seconds. The rule was intended to run in "simulate" mode (match, don't block) — but simulate mode still executes the regex | [1] |
| 13:45 | First PagerDuty page: a synthetic WAF-functionality test fails. Rapidly followed by pages for end-to-end tests, a global traffic-drop alert, widespread 502s, and PoP reports of CPU exhaustion. SRE sees ~80% traffic loss, declares a P0, escalates. Initial speculation: an unknown attack | [1] |
| 14:00 | WAF identified as the component: live CPU data, `strace`, and error logs converge | [1] |
| 14:02 | Team proposes the **global terminate** — a built-in mechanism to disable one component worldwide. Execution is blocked: Cloudflare's own Access service was down (it runs through the edge), so engineers could not authenticate to the internal control panel; Jira and the build system were unreachable; a rarely-used bypass mechanism had to be found and used; some team members' credentials had been auto-disabled by a security feature for infrequent use | [1] |
| 14:07 | A team member executes the global WAF termination | [1] |
| 14:09 | Traffic levels and CPU back to expected worldwide. Front-line servers had generated the 502s: they still had CPU but could not reach the processes that serve HTTP/HTTPS | [1] |
| 14:52 | After negative and positive tests in a single city (paying customers' traffic removed), WAF re-enabled globally | [1] |

All rows are CONFIRMED to [1]. Every occurrence "up to the point the rules were deployed was done 'correctly': a pull request was raised, it was approved, CI/CD built the code and tested it, a change request was submitted with an SOP detailing rollout and rollback, and the rollout was executed" [1].

## Technical Mechanism

### 1. Catastrophic backtracking

The rule's expression contained, as its critical part, the fragment `.*(?:.*=.*)` — which for understanding the failure can be reduced to `.*.*=.*`: "match zero or more characters, then zero or more characters, then a literal `=`, then zero or more characters" [1].

A backtracking engine (PCRE) tries the greedy path first and, on failure, returns to earlier choice points and tries alternatives — depth-first search over an exponential number of ways to split the input among the `.*` terms. Cloudflare's own worked example [1]:

- Matching `x=x` against `.*.*=.*` takes **23 steps**: the first `.*` grabs everything, fails at `=`, backtracks, retries a shorter match, fails, backtracks again — five distinct backtrack points before the final split succeeds.
- `x=xx` takes **33 steps**; `x=xxx` takes **45**. The growth is super-linear.
- `x=` followed by 20 `x`s takes **555 steps** — and if the `=` is missing (a pure non-match), **4,067 steps**.
- With a trailing literal (the blog's `.*.*=.*;` variant), the non-match case becomes *exponentially* bad: **5,353 steps** for the same 20-`x` input.

```text
 .*.*=.*  against "x=xxxxxxxxxxxxxxxxxxxx"

 attempt 1:  .* = "x=x...x" (all)   .* = ""   need "=" -> FAIL, backtrack
 attempt 2:  .* = "x=x...x" (n-1)  .* = "x"  need "=" -> FAIL, backtrack
 ...
 attempt k:  .* = "x="             .* = ""   need "=" -> FAIL (already consumed)
 ...
 success only after enumerating split points  ->  super-linear step count
 with a trailing literal that never matches   ->  exponential step count
```

Two properties make this lethal at an edge CDN. First, the input is **attacker-influenced request content** — every HTTP request touching the rule is a fresh input to the exponential. Second, the cost is paid on the **hot path** of every server simultaneously, because Quicksilver propagated the rule everywhere within seconds [1]. One bad expression plus global-in-seconds distribution equals network-wide CPU exhaustion.

Lazy quantifiers (`.*?`) reduce but do not eliminate backtracking — Cloudflare shows a case where a lazy rewrite leaves the worst-case count unchanged [1]. The robust fix is an engine whose worst case is linear by construction.

### 2. Why PCRE had to go: linear-time engines

The alternative architecture dates to Ken Thompson's 1968 algorithm: compile the regular expression to an NFA and simulate it by tracking the *set* of reachable states per input character — every alternative is explored simultaneously, so each character is processed once and matching is **linear in the input length** [1]. No choice points, no backtracking, no exponential. re2 and the Rust `regex` crate implement this discipline (with minor feature trade-offs, e.g., no backreferences), which is why Cloudflare's remediation list included "Switching to either the re2 or Rust regex engine which both have run-time guarantees" [1], and why the theoretical background lives in this repository's [regex engine internals page](../../compilers/advanced/regex-engine-internals.md).

### 3. The defense-in-depth that wasn't

The expression was the spark. The fuel, in Cloudflare's own enumeration [1]:

- A CPU-excess protection had been **removed by mistake** during a WAF refactoring weeks earlier — a refactoring whose *purpose* was reducing CPU use.
- The regex engine had **no complexity guarantees**.
- The test suite **could not detect excessive CPU consumption** — unit and corpus tests measure correctness, not cost; the rule caused no measurable runtime increase in CI.
- The SOP **allowed a non-emergency rule change to go straight to global production**, skipping the DOG/PIG/Canary staging used for all other software.
- The **rollback plan required running the complete WAF build twice** — too slow to matter during the incident.
- The first **global-traffic-drop alert fired late**; the status page was updated too slowly.

### 4. The kill switch under duress

Cloudflare had a purpose-built control — the "global terminate," able to disable a single component worldwide. Executing it took from proposal (14:02) to execution (14:07) — five minutes that are the most instructive part of the incident [1]:

- **Access (SSO) ran through the edge** — so the authentication system for internal tools was a victim of the outage it was needed to fight.
- **Jira and the build system were unreachable** by the same dependency path; a **bypass mechanism existed but was rarely used** and not drilled.
- **A security feature had auto-disabled credentials** of team members who hadn't used the internal control panel frequently.
- **Customers could not reach the Cloudflare dashboard or API at all**, because those pass through the Cloudflare edge — the control plane for customers and for Cloudflare's own engineers shared the failure mode.

INTERPRETATION: this is not a "failed" kill switch in the sense of a button that did nothing — when executed, it worked immediately. It was a kill switch whose *access path* shared fate with the system it killed. A kill switch is only as available as its least-available dependency.

### Trigger vs Contributing Factors

**Trigger (CONFIRMED):** global deployment at 13:42 UTC of a WAF rule whose regex backtracked catastrophically on request content.

**Contributing factors (CONFIRMED):** removed CPU protection; engine without run-time guarantees; CI blind to CPU cost; staging-free global deploy SOP; slow rollback plan; late traffic-drop alert; slow status-page updates; edge-dependent access paths for Cloudflare's own tooling and the customer dashboard; credential auto-expiry; unfamiliar bypass procedures.

**Contributing factors (INTERPRETATION):** the tension between *speed of protective response* (WAF rules must ship fast to counter active attacks) and *staged rollout* is structural: the WAF's deployment model was a deliberate trade-off that traded blast radius for latency. The incident shows the tail cost of that trade-off.

## Why Safeguards Didn't Prevent It

- **CI tested correctness, not cost.** Every test asked "does it match / does it over-block?" — none asked "how much CPU does the worst legitimate input cost?"
- **The one protection that mattered had been deleted.** Defense-in-depth works when the layers are independent; here the CPU guard and the test suite were the only two layers, and one was gone while the other had never covered the failure mode.
- **The SOP encoded an outdated risk model.** Global-in-one-step was survivable when a CPU guard existed in the engine path; when that layer silently disappeared, the SOP's risk assumption became stale — and nothing detected the staleness.
- **Distribution outpaced reaction.** Quicksilver's seconds-scale propagation is a feature; combined with no canary stage and no cost test, it meant the entire fleet was exposed before the first synthetic test failed.
- **Recovery paths shared fate with the outage.** Internal auth, project tracking, builds, and the customer dashboard all depended on the edge; the incident consumed the tools needed to fix it.

## Lessons & Mitigations

1. **Prefer engines with worst-case linear-time guarantees** for anything evaluating patterns on untrusted input. This is a language/runtime selection problem, not a code-review problem — see [regex engine internals](../../compilers/advanced/regex-engine-internals.md).
2. **Test cost, not just correctness.** Performance profiling of rules (Cloudflare's added fix [1]) belongs in CI for anything on a hot path; a rule set that can cost O(2ⁿ) must be budgeted like any other resource.
3. **Never remove a protection without an integration test that proves it exists.** The deleted CPU guard had no test asserting its behavior, so its removal was invisible until the outage.
4. **Stage configuration changes like code.** Cloudflare's fix: staged rollouts for WAF rules in the same manner as other software, with an explicit emergency lane for active attacks [1] — the standard canary discipline of [canary releases](../../sre/canary-releases.md).
5. **Give kill switches an out-of-band access path.** A global terminate that authenticates through the system being terminated is not an independent control. Break shared fate deliberately (separate credentials, separate network path, regularly drilled bypass — all Cloudflare remediations [1]).
6. **Control planes should not ride the data plane they control.** The customer dashboard and API going down *with* the edge meant customers could not even disable or reconfigure their own accounts during the outage; Cloudflare added an emergency ability to take the dashboard and API off the edge [1].

## Connection to This Repository

- [Regex engine internals](../../compilers/advanced/regex-engine-internals.md) — NFA simulation, backtracking, and run-time guarantees in depth.
- [Canary releases](../../sre/canary-releases.md) — the staged-rollout discipline the WAF SOP bypassed.
- [Feature flags](../../sre/feature-flags.md) — the "simulate mode" rule was effectively a flag; its evaluation still executed the dangerous code.
- [Chaos engineering](../../sre/chaos-engineering.md) — drilling the kill-switch path before the day you need it.
- [Load testing strategies](../../sre/load-testing-strategies.md) — why CPU-cost budgets belong in automated testing.
- [Incident management](../../sre/incident-management.md) — P0 declaration, escalation, and status-page mechanics during a global event.
- [Common failure modes](../../failure-modes/common-failures.md) — resource-exhaustion and bad-deployment patterns in generic form.

## Interview Questions

1. Explain catastrophic backtracking with `.*.*=.*` on a whiteboard: why is matching super-linear, when does it become exponential, and what property of a regex engine makes the worst case linear?
2. Your WAF/API-gateway evaluates user-supplied patterns with a backtracking engine. Aside from rewriting the engine, what three compensating controls would you add first, and what does each miss?
3. Design a global kill switch for a component running in 180 cities. Requirements: independent of the component's own serving path; drillable; auditable. What dependencies must it not share with the component?
4. A test suite passes a new rule because it checks correctness only. What CI-visible signal would have caught Cloudflare's rule, and how do you prevent that signal from being noisy for benign rules?
5. Cloudflare's WAF skipped staging to respond to attacks in hours. Argue for and against that trade-off, and design the compromise they landed on (staged by default, emergency lane for active attacks).

## Key Takeaways

- One regular expression took down ~80% of a global CDN's traffic for 27 minutes; the propagation speed of configuration (seconds) converted a code smell into a planetary event.
- Backtracking engines make worst-case cost data-dependent and attacker-influenced; only run-time guarantees (Thompson NFA simulation, re2/Rust regex) remove the class of failure.
- The deepest failure was not the regex but the removal, weeks earlier, of the one protection against runaway CPU — with no test to notice.
- The kill switch worked when pressed but took five minutes to reach because internal auth, wikis, and builds shared fate with the edge. Independence of safety controls is a property you must design and drill.

## Sources

1. John Graham-Cumming, "Details of the Cloudflare outage on July 2, 2019," Cloudflare Blog, July 2, 2019. https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/ (fetched and quoted; URL verified at time of writing)

## Cross-References

- [AWS S3 us-east-1, 2017](./aws-s3-us-east-1-2017.md) — another one-command global event; shared-fate control planes in both incidents.
- [Facebook BGP, 2021](./facebook-bgp-2021.md) — internal tools unreachable because they lived behind the failed layer; the same coupling, different mechanism.
- [Knight Capital, 2012](./knight-capital-2012.md) — configuration at machine speed with no staging lane; the trading-system analogue of Quicksilver's seconds-scale propagation.
- [Regex engine internals](../../compilers/advanced/regex-engine-internals.md) — the theoretical fix: linear-time matching.
- [Canary releases](../../sre/canary-releases.md) — the process fix.
- [Postmortem culture](../../sre/postmortem-culture.md) — this post is a model public postmortem: mechanism, timeline, contributing-factor list, and dated remediations.
