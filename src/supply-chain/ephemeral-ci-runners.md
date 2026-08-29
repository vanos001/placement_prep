# Ephemeral CI Runners: Ephemeral by Construction

The CI runner is the one machine in the fleet that executes untrusted code
while holding credentials that can publish to production. That combination is
why "make runners ephemeral" leads every CI hardening checklist -- and why the
line is so often waved through without understanding what it buys, what it
does not, and what it costs. Ephemerality is really three separable
decisions: what state the runner forgets, who is trusted to boot it, and how
credentials reach a machine that will be destroyed within the hour. The
survey-level checklist lives in [Software Supply Chain](./software-supply-chain.md).

## What a Persistent Runner Remembers

A self-hosted runner accumulates state across jobs by design. GitHub's docs
list it as a feature of self-hosted runners that they "don't need to have a
clean instance for every job execution" -- the selling point is exactly the
attack surface. What persists:

- **Credentials**: static cloud tokens, deploy keys, and the runner registration token.
- **Caches**: ccache/sccache objects, Docker layer cache, package downloads -- writable by job code, read back later.
- **Toolchain state and workspace leftovers**: compilers, site-packages, previous jobs' artifacts and `.git` dirs.
- **Host reach**: the Docker socket, a Kubernetes service account, cron entries, SSH agents.

How that state becomes a chain-of-trust problem on one runner slot:

```text
one runner slot, jobs in sequence (persistent mode)

job 1: benign      -- builds, tests, writes caches
job 2: ADVERSARIAL -- plants residue: poisoned compiler in ccache, stashed
                      deploy key, cron entry; all survive job boundaries
job 3-4: benign    -- resolve the poisoned compiler / read the key -> contaminated
   ...
job 250: slot reimaged (only now does the residue die)
```

The incidents that made this non-theoretical both ended in the same audit
ritual: enumerate every credential that ever passed through a runner and
rotate all of it. The 2021 Codecov bash-uploader compromise exfiltrated, per
Codecov's own notice, "any credentials, tokens, or keys that our customers
were passing through their CI runner that would be accessible when the Bash
Uploader script was executed". The January 2023 CircleCI incident required
rotating environment variables, project API tokens, SSH keys, and runner
tokens. Different entry points, identical blast radius: whatever the runner
could see, the attacker got. GitHub's guide: self-hosted runners "can be
persistently compromised by untrusted code in a workflow" and "should almost
never be used for public repositories".

## Three Durations of Ephemeral

"Ephemeral" hides a choice: which layer is reused, and therefore which
attacks still work. Hosted platforms converge on per-job provisioning and
say so: GitHub-hosted runners "execute code within ephemeral and clean
isolated virtual machines"; Google Cloud Build "provisions a new environment
for each build and then destroys it"; Buildkite hosted agents are "always
ephemeral, destroyed after each job"; the GitLab Kubernetes executor
"creates a pod for each GitLab CI job".

| Mode | Reused across jobs | Dies with the job | What can still cross |
|------|--------------------|-------------------|----------------------|
| Persistent runner | everything: FS, caches, creds, host | nothing | files, caches, tokens, implants |
| Container-per-job on persistent host | kernel, host FS, agent, socket | container filesystem | anything that escaped to the host |
| VM-per-job (cloud runner) | only the cloud account | entire disk and memory | boot-image and account-level state |
| MicroVM-per-job (Firecracker) | only the host's kernel | entire microVM | boot-image state |

The container row is where the caveats live. A fresh container destroys
filesystem residue, but the job shares a kernel with the host and often
inherits host reach: a Docker socket mount is host root, a host-mounted
build cache is writable residue, and the agent holding the registration
token lives outside the container. Security-sensitive pipelines jump to the
VM row, and Firecracker makes it economically sane: a microVM boots in
roughly 125 ms with a ~5 MiB VMM footprint -- the mechanics of
Lambda-style per-request virtualization are in
[the Firecracker page](../cloud/virtualization/firecracker.md).

Cold runners pay on the critical path: queue, boot, clone, restore caches,
install toolchains. Cache re-priming dominates -- a cold layer cache or cold
ccache turns a 90-second build into a 10-minute one -- which is why warm
pools tempt platform teams and quietly reintroduce persistence: a pool
recycling a VM every K jobs is a persistent runner with a shorter reimage
cadence, and the model below prices that knob. The structural fix is
shrinking what must be warmed: hermetic builds with pinned inputs and a
remote cache ([Reproducible and Hermetic Builds](./reproducible-builds.md))
move cache state off the runner, where it is content-addressed and auditable
instead of merely wiped.

| Strategy | Job-start latency | Cost efficiency | Residue risk |
|----------|-------------------|-----------------|--------------|
| Persistent fleet | seconds (warm) | best | highest |
| Warm pool, recycle K jobs | seconds | good | K x per-job residue |
| Cold VM-per-job | 1-5 min | worst | near zero |
| Cold microVM + remote cache | seconds to ~1 min | moderate | near zero |

## Bootstrap Integrity: Who Booted the Runner?

Ephemerality resets the clock; it does not answer who wound it. If the
provisioning path is attacker-controlled, a fresh machine boots fresh
malware every time -- ephemeral by construction, compromised by
construction. The trust handoff is scheduler -> provisioner -> image ->
agent -> registration; each arrow is a control point:

- **Image and agent pinning**: digest-pinned image built by the same attested pipeline it will run; pinned agent, fetched authenticated.
- **Registration tokens**: one-time, short-TTL, rotated -- a leaked token is a machine-identity mint. After CircleCI's disclosure even runner tokens went on the rotation list.
- **Environment attestation**: the platform vouches for where a job ran. In GitHub's documented OIDC example payload, the claim `"runner_environment": "github-hosted"` rides inside the job's JWT -- provenance that survives the runner's destruction.

This is what SLSA's build track formalizes: Build L2 requires provenance
generated by "a hosted build platform"; Build L3 requires the platform to
"prevent runs from influencing one another, even within the same project"
and to keep the provenance-signing secret inaccessible to user-defined build
steps. Ephemeral isolation is the standard mechanism for the first; the
second splits the runner (untrusted, destroyed) from the signer.

## Getting Secrets to a Thing That Will Be Destroyed

| Property | Static secrets on runner | OIDC federation to cloud role |
|----------|--------------------------|-------------------------------|
| Issuance | pasted by a human, once | minted per job by the platform |
| Lifetime | runner uptime (days) | single job, then auto-expires |
| Rotation | manual, incident-driven | nothing to rotate |
| Residue on disk | env vars, config files | none beyond the job's own token |
| Blast radius of one owned job | every secret the runner ever held | one role's permissions for one job |

GitHub's OIDC documentation describes the federated flow: the job requests a
JWT (`permissions: id-token: write`), the cloud trust policy matches the
token's `aud` and `sub` claims -- the documented example subject is
`repo:octo-org/octo-repo:environment:prod` -- and the provider then "issues
a short-lived access token that is only valid for a single job, and then
automatically expires". No long-lived secret exists to steal at rest, which
shrinks the exposure window from half a 30-day runner uptime (360 hours) to
one job's life. What OIDC does not fix: (1) the token is fully usable
*during* the job that holds it -- mid-job exfiltration still works, only
at-rest theft gets harder; (2) a trust policy conditioned too broadly hands
the role to every push; (3) echo the token into a log line and its lifetime
becomes the log-retention lifetime. Federation moves the problem from
storage to policy; both ends need engineering.

## SLSA Build-Level Mapping

| Runner property | SLSA build-track effect | Level served |
|-----------------|-------------------------|--------------|
| Builds run on a service that records how | provenance exists | L1 |
| Platform mints signed provenance, not the job | limits forgery to post-build tampering | L2 |
| Ephemeral isolated environment per run | "prevent runs from influencing one another" | L3 |
| Signing key held away from user-defined steps | provenance signer unreachable from job | L3 |
| Attestations exported before destruction | verifiable after the machine is gone | supports L2/L3 |

Cloud Build documents that it "can generate build provenance for container
images that provide SLSA level 3 assurance" -- an ephemeral-worker claim
backed by an attestation pipeline. The full level walkthrough is in
[SBOM and SLSA](./sbom-slsa.md).

## A Residue-Carryover Model

The numbers below are a MODEL, not measurements: one slot processes 1000
jobs, fraction `p_mal` are adversarial, an adversarial job plants residue
with probability `p`, and the reused layer decides whether residue crosses a
job boundary.

```python
"""Residue-carryover model: persistent vs container-on-host vs VM-per-job.
MODEL, NOT MEASUREMENT. One slot runs N jobs; an adversarial job (p_mal)
plants residue with probability p, and only the reused layer lets residue
cross a job boundary: persistent keeps it until a reimage every L jobs;
container-on-host leaks it to the shared host (probability e_host);
vm-per-job keeps it only if a foothold survives one boundary (q_wipe).
A contaminated job runs while residue is live and activates it (p_eff).
WINDOW: how long one owned job can keep reading that runner's credentials.
"""
import random
import statistics

N, L = 1000, 250
P_MAL, P_RES, P_EFF = 0.05, 0.80, 0.15
E_HOST, Q_WIPE = 0.20, 0.01
U_HOURS, T_TOKEN = 720.0, 1.0     # static-cred lifetime (30 d) vs OIDC TTL (assumed)
S = {"persistent": 1.0, "container-on-host": E_HOST, "vm-per-job": Q_WIPE}
WINDOW = {"persistent": U_HOURS / 2,
          "container-on-host": T_TOKEN + E_HOST * U_HOURS / 2,
          "vm-per-job": T_TOKEN}

def simulate(mode, rng):
    n, live, once = 0, False, False
    for job in range(N):
        if mode != "vm-per-job" and job % L == 0:
            live = False                       # slot reimaged
        if (live or once) and rng.random() < P_EFF:
            n += 1                             # job ran against residue
        once = False
        if rng.random() < P_MAL and rng.random() < P_RES:
            if rng.random() < S[mode]:
                once, live = (True, live) if mode == "vm-per-job" else (False, True)
    return n

def analytic(mode):
    m = P_MAL * P_RES * S[mode]                # per-job poison chance
    if mode == "vm-per-job":                   # reaches exactly one later job
        return N * m * P_EFF
    # reused layer: P(residue live d slots into an epoch) = 1 - (1-m)**d
    return (N // L) * P_EFF * sum(1 - (1 - m) ** d for d in range(L))

TRIALS, SEED = 500, 20260801
rng = random.Random(SEED)
print("residue-carryover model: N=%d p_mal=%.2f p=%.2f p_eff=%.2f" % (N, P_MAL, P_RES, P_EFF))
print("reimage L=%d e_host=%.2f q_wipe=%.2f trials=%d seed=%d" % (L, E_HOST, Q_WIPE, TRIALS, SEED))
print("mode               sim mean   sd  analytic  window(h)  secret-h per %d" % N)
for mode in ("persistent", "container-on-host", "vm-per-job"):
    xs = [simulate(mode, rng) for _ in range(TRIALS)]
    print("%-17s %9.1f %5.1f %9.2f %10.1f %10.0f"
          % (mode, statistics.mean(xs), statistics.stdev(xs), analytic(mode),
             WINDOW[mode], P_MAL * N * WINDOW[mode]))
print("persistent-to-vm contamination ratio: %.0fx" % (analytic("persistent") / analytic("vm-per-job")))
print("persistent-to-vm exposure-window ratio: %.0fx" % (U_HOURS / 2 / T_TOKEN))
```

Output (deterministic; seed fixed):

```text
residue-carryover model: N=1000 p_mal=0.05 p=0.80 p_eff=0.15
reimage L=250 e_host=0.20 q_wipe=0.01 trials=500 seed=20260801
mode               sim mean   sd  analytic  window(h)  secret-h per 1000
persistent            135.0  12.3    135.00      360.0      18000
container-on-host      83.7  25.6     85.07       73.0       3650
vm-per-job              0.1   0.3      0.06        1.0         50
persistent-to-vm contamination ratio: 2250x
persistent-to-vm exposure-window ratio: 360x
```

Three readings worth carrying into an interview. First, the sim matches the
closed form only when residue liveness is a union: the first successful
plant makes residue live, and later plants add nothing until the reimage.
The naive model -- summing each plant's expected reach over the rest of the
epoch -- overcounts by roughly 5x here, a classic error with overlapping
contamination windows. Second, container-per-job buys less than it appears
to: it removes only ~38% of persistent-mode contamination in this model,
because host escape, not filesystem carryover, does most of the damage once
jobs are frequent. Third, the exposure-window ratio (360x) is sturdier than
any contamination number: it follows from credential lifetimes alone, which
is why OIDC federation and ephemerality ship together.

## Where the Ephemeral Story Still Bites

- **Shared remote caches** re-contaminate every cold start -- ephemerality
  does not purify inputs; **bootstrap compromise** (provisioner, registry)
  replicates to every "clean" boot with no forensic residue to find.
- **Warm-pool drift** quietly re-creates persistence; "ephemeral" needs a
  defined recycle count, not a marketing adjective.
- **Mid-job exfiltration**: within the job's own lifetime the runner holds
  real credentials; the window shrinks, it does not close.

The one-line interview answer: ephemerality converts "is this runner
trustworthy?" -- an undecidable forensic question -- into "was this runner
booted from a trusted image, fed trusted inputs, and given a scoped
credential?" -- three auditable ones.

## References

1. [SLSA v1.1 -- Build levels](https://slsa.dev/spec/v1.1/levels) - build track L0-L3; L3 requirement language quoted above (probed HTTP 200).
2. [GitHub Actions -- Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions) - "Hardening for self-hosted runners"; ephemeral-VM quote (200).
3. [GitHub Actions -- About self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners) - persistence as default self-hosted behavior (200).
4. [GitHub Actions -- About security hardening with OpenID Connect](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect) - OIDC claims, `sub` example, `runner_environment`, single-job token lifetime (200).
5. [GitLab Runner -- Kubernetes executor](https://docs.gitlab.com/runner/executors/kubernetes/) - pod-per-job provisioning (200). Note: `docs.gitlab.com/ci/runners/` intermittently serves HTTP 403 bot-block pages to scripted clients; the executor page probed clean.
6. [Google Cloud Build -- Overview](https://cloud.google.com/build/docs/overview) - ephemeral build environment; SLSA L3 provenance claim (200).
7. [Buildkite -- The agent](https://buildkite.com/docs/agent) - hosted agents "always ephemeral, destroyed after each job" (200; former `/docs/agent/v3/ephemeral` URL redirects here).
8. [Codecov -- Bash Uploader Security Update](https://about.codecov.io/security-update/) - April 2021 incident; CI-runner credential exposure list (200).
9. [CircleCI -- January 4, 2023 security alert](https://circleci.com/blog/january-4-2023-security-alert/) - rotation of all stored CI secrets, incl. runner tokens (200).
10. [Firecracker microVM](https://firecracker-microvm.github.io/) - startup-time and footprint targets enabling per-job VMs (200).
