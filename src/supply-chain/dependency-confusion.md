# Dependency Confusion: Anatomy, Impact, and Defenses

Dependency confusion inverts the economics of intrusion. The attacker's whole
investment is a `publish` command: upload a package to a public registry under
the exact name of a private one, then wait. The defender's build farm does the
rest - it fetches the package and runs its install scripts inside an
environment holding registry tokens, cloud credentials, and deploy keys.

## The 2021 Disclosure, Verified Line by Line

Alex Birsan's post "Dependency Confusion: How I Hacked Into Apple, Microsoft
and Dozens of Other Companies" appeared February 9, 2021. The primary source
matters because the attack is retold with inflated details; these facts come
from the article text itself:

- Birsan coined the term; the vulnerability "was detected inside more than 35
  organizations," across the three ecosystems he tested: npm, PyPI, RubyGems.
- It began in summer 2020 when bounty hunter Justin Gardner shared
  PayPal-internal Node.js code found on GitHub, whose `package.json` mixed
  public and private dependency names; internal `package.json` data also gets
  "embedded into public script files during their build process," which is
  how names leaked at Apple, Yelp, and Tesla.
- The payload was deliberately benign: npm `preinstall` scripts logging only
  username, hostname, and current path per installation, plus external IPs;
  one variant exfiltrated the data hex-encoded as DNS queries to Birsan's own
  authoritative name server.
- The Python root cause: a manifest using `--extra-index-url` makes pip check
  both indexes, and "if the package exists on both, it defaults to installing
  from the source with the higher version number" - so `library` at
  `9000.0.0` on PyPI hijacks the private dependency. A GitHub search for
  `--extra-index-url` surfaced vulnerable build scripts, including a .NET
  Core build-tools bug (judged out of scope by that bounty program).
- Verified outcomes named in the post: Shopify's build installed his
  `shopify-cloud` Ruby gem within hours of upload ($30,000 bounty); a Node
  package executed on machines inside Apple's network in projects "related to
  Apple's authentication system" ($30,000); an attack on Microsoft's own
  Office 365 cloud build, reported as an Azure Artifacts automation issue,
  paid Azure's maximum $40,000. Netflix, Yelp, and Uber are listed among
  other affected companies. The post states no total; secondary reporting at
  the time put cumulative bounties above $130,000.
- Microsoft published the companion white paper "3 Ways to Mitigate Risk When
  Using Private Package Feeds," still reachable via `aka.ms/pkg-sec-wp`.

Note what the disclosure does not claim: no registry was hacked. Every
malicious upload was a legal publish to a real public registry; only the
victim's resolver behaved wrongly.

## Why Resolvers Choose the Attacker

Two defects must combine: a private-only name gets queried against a public
source, and the resolver ignores source identity when picking among
candidates - usually preferring the highest version:

```text
             need package NAME at version range R
                               |
       is NAME bound to exactly one source? (npm scope,
       |                 NuGet source map, Go module path)
       |                                          |
     yes                                        no
       |                                          |
 query ONLY the bound source          for each configured source S
 (npm docs: "a scope only ever        (private AND public):
 points to one registry")               query S, collect candidates
       |                                          |
 404 -> FAIL LOUDLY                  private hit?  public hit?
 never fall back silently                 |             |
                                     use private,  merge all candidates,
                                     warn on dup   pick HIGHEST version
                                                   -> bait wins if in range
```

The range detail is the most common interview miss. A caret range does not
save you: `^1.2.0` accepts anything from `1.2.0` up to (excluding) `2.0.0`,
so the attacker publishes `1.9.5` - above your internal `1.4.2`, still inside
the range. Bare `*`, `latest`, or `>=1.0.0` make it trivial (`9999.0.0`).
Without a lockfile every install re-resolves, so the bait keeps winning; `~`
behaves like `^` one level down. Only an exact pin (`==1.4.2`) leaves the
attacker no version space to occupy.

## A Name-Collision Taxonomy

These attacks get conflated in interviews; the defenses differ, so the
distinctions matter.

| Attack | Name craft | Victim namespace | Entry point | Primary defense |
|--------|------------|------------------|-------------|-----------------|
| Dependency confusion | Exact copy of an internal name | Private index | CI resolver fetch | Source binding, private-first |
| Scope squatting | Registers org scope (`@acme`) while unclaimed | Public registry scopes | `npm publish` to squat scope | Register scopes early |
| Typosquatting | Near-miss of a popular name (`reqeusts`) | Public registry | Developer typo | Allow-list, linting |
| Brandjacking | Clones name + README/metadata of a real project | Public registry | Registry search | Provenance checks |
| Starjacking | Metadata points at a famous repo it does not ship | Public registry | Tooling showing stars | Repo-to-package verification |

Scope squatting is the bridge case: if your org never registered `@acme` on
npmjs, an attacker can - scope registration and verified-publisher domains
are namespace real estate to claim, not optional hygiene.

## Registry-Side Mitigations Since 2021

- **Azure Artifacts upstream sources**: a feed blocks publishing a version
  that already exists upstream ("you cannot publish a package version that
  already exists in one of those upstream sources"), supports overrides, and
  searches upstreams in a configurable order.
- **AWS CodeArtifact upstreams**: the documented search order is your
  repository first, then each upstream "in the order that they were listed,"
  stopping at the first hit - internal names resolve internally, and external
  connections are the single audited egress path to npmjs/PyPI.
- **npm provenance** (2023): publishes from supported CI attach
  Sigstore-backed provenance linking package to source repo and build.
- **PyPI Trusted Publishing** (2023): OIDC federation mints 15-minute upload
  tokens per project, eliminating long-lived CI API tokens - it shrinks what
  a confused build can leak, but fixes neither resolution nor code exec.
- **pub.dev verified publishers**: a badge proving the publisher owns the
  package's domain (e.g. `dart.dev`); it defeats publisher-identity
  squatting but not same-name collisions - pub.dev has no private mode.
- **Go** was structurally less exposed: module paths embed the source host,
  and `GOPRIVATE`/`GONOPROXY` keep private modules away from the public proxy
  and checksum database.

Caveat: upstream proxies only protect names that already exist inside the
feed. A brand-new internal package, a typo, or a half-migrated name sails
past any upstream configuration - hence client-side binding below.

## Client-Side Defenses

1. **Bind names to sources.** npm scopes map many-to-one to registries, and
   both `npm install` and `npm publish` of a scoped name route there:
   `@myco:registry=https://nexus.internal/repository/npm-hosted/`. NuGet
   Package Source Mapping (NuGet 6.0+, post-disclosure) does the same by ID
   prefix: `MyCo.*` resolves only from the internal feed.
2. **Make the private index the only path.** Point every manifest at the
   internal proxy (npmjs/PyPI configured as upstreams) and remove direct
   public-registry access from build networks. Resolver policy you cannot
   violate from a laptop beats resolver policy in a wiki.
3. **Pin versions and integrity.** Lockfiles (`package-lock.json`,
   `poetry.lock`) freeze resolution and carry per-package integrity hashes;
   pip's hash-checking mode requires every requirement pinned and hashed -
   the docs are blunt that "by default, pip does not perform any checks to
   protect against remote tampering." Honest limitation: a lockfile that
   already contains the attacker's version (merged in a hasty PR) locks in
   the compromise. Pinning stops drift, not first contact.
4. **Allow-list public packages.** Proxy/virtual repositories (Artifactory,
   CodeArtifact, Nexus) that fetch only reviewed package names turn
   typosquats and never-seen-before names into hard failures.
5. **Plant bait.** Pre-register internal names on public registries where
   policy permits, and reference canary packages with fake names from real
   builds. Any fetch of a canary is a zero-false-positive alarm: legitimate
   users cannot know the name. DNS canary tokens (canarytokens.org) are the
   same tripwire for exfiltration paths.
6. **Watch the range.** Treat `*`, `latest`, and bare `>=` in internal
   manifests as findings; pin internal packages exactly.

## The CI Runner Is the Real Target

The resolver executes attacker code on a machine pre-loaded with secrets:
registry publish tokens (with those, an attacker can poison your *future*
releases - a persistent backdoor worth far more than one build), cloud
credentials, deploy keys, signing keys. Birsan's payload logged hostnames; a
criminal one exfiltrates `.npmrc`, dumps environment variables over DNS, or
patches build output. Consequences for pipeline design:

- Install steps run with no secrets in scope; publishing and deploys are
  separate, minimal-permission jobs.
- Runners are ephemeral and network-restricted - only the private proxy is
  reachable, so a `preinstall` script has nothing to phone home to.
- CI identities use short-lived OIDC federation (the mechanism behind
  Trusted Publishing) instead of stored tokens.
- Runner compromise is an artifact-integrity incident: any build that fetched
  bait cannot be trusted and must be rebuilt from a clean runner;
  [Reproducible Builds](reproducible-builds.md) makes that rebuild verifiable.

## Resolver Simulator: Flawed vs. Fixed

One runnable demo ties the mechanisms together (pure stdlib). `flawed()`
reproduces the disclosure's pip behavior - merge both sources, take the
highest version; `fixed()` enforces source binding, an allow-list, and bait
detection:

```python
"""Resolver simulator: flawed flat-merge vs fixed private-first (stdlib only)."""

def vkey(v):
    return tuple(int(x) for x in v.split("."))        # versions are X.Y.Z

def satisfies(c, v):
    """Semver subset: ^, ~, >=, exact pin, * (npm/node-semver rules)."""
    if c == "*":
        c = ">=0.0.0"                                 # any version
    if c.startswith(">="):
        return vkey(v) >= vkey(c[2:])
    if c.startswith("^"):                             # 0.x carets per node-semver
        lo = vkey(c[1:])
        hi = ((lo[0] + 1, 0, 0) if lo[0] else
              (0, lo[1] + 1, 0) if lo[1] else (0, 0, lo[2] + 1))
        return lo <= vkey(v) < hi
    if c.startswith("~"):                             # patch-level bumps only
        lo = vkey(c[1:])
        return lo <= vkey(v) < (lo[0], lo[1] + 1, 0)
    return vkey(v) == vkey(c)                         # exact pin

def pick(sources, name, c):
    """Highest satisfying version across sources; source identity ignored."""
    ok = [(vkey(v), src, v) for src, pkgs in sources
          for v in sorted(pkgs.get(name, ())) if satisfies(c, v)]
    return max(ok)[1:] if ok else None                # (source, version)

def flawed(c, name, private, public):
    """pip --extra-index-url style: merge both indexes, take highest."""
    return pick([("PRIVATE", private), ("PUBLIC", public)], name, c)

def fixed(c, name, private, public, allow, events):
    """Allow-list + scope binding: internal names never touch the public index."""
    internal = name in allow or name.startswith("@acme/")
    if name.startswith("@acme/"):
        events.append("SCOPED-NAME %s bound to private registry" % name)
    if not internal:
        events.append("REJECT-UNAPPROVED %s (no allow-list entry)" % name)
        return None
    bait = sorted(public.get(name, ()))
    if bait:
        events.append("BAIT public copy of internal name %s: %s" % (name, bait))
    return pick([("PRIVATE", private)], name, c)      # public never consulted

SCENARIOS = [
    ("unscoped internal name", "acme-core", "^1.2.0",
     {"acme-core": {"1.4.2"}}, {"acme-core": {"1.9.5"}}, {"acme-core"}),
    ("scoped name", "@acme/auth-lib", "^1.0.0",
     {"@acme/auth-lib": {"1.2.3"}}, {"@acme/auth-lib": {"1.5.0"}}, set()),
    ("typosquat (public-only name)", "reqeusts", "*",
     {}, {"reqeusts": {"2.31.0"}}, {"requests"}),
]

for n, (label, name, c, priv, pub, allow) in enumerate(SCENARIOS, 1):
    ev = []
    fl = flawed(c, name, priv, pub)   # each scenario yields >= 1 candidate
    fx = fixed(c, name, priv, pub, allow, ev)
    print("Scenario %d: %s" % (n, label))
    print("  %s@%s | private: %s | public: %s" % (name, c,
          sorted(priv.get(name, ())) or "-", sorted(pub.get(name, ())) or "-"))
    ok = lambda r: "PWNED" if r and r[0] == "PUBLIC" else "safe"
    print("  flawed -> %s from %s [%s] | fixed -> %s [%s]" % (
        fl[1], fl[0], ok(fl),
        "%s from %s" % (fx[1], fx[0]) if fx else "REJECTED (no install)", ok(fx)))
    if ev:
        print("  events: " + "; ".join(ev))
    print()
```

Output (verbatim from running the script above):

```text
Scenario 1: unscoped internal name
  acme-core@^1.2.0 | private: ['1.4.2'] | public: ['1.9.5']
  flawed -> 1.9.5 from PUBLIC [PWNED] | fixed -> 1.4.2 from PRIVATE [safe]
  events: BAIT public copy of internal name acme-core: ['1.9.5']

Scenario 2: scoped name
  @acme/auth-lib@^1.0.0 | private: ['1.2.3'] | public: ['1.5.0']
  flawed -> 1.5.0 from PUBLIC [PWNED] | fixed -> 1.2.3 from PRIVATE [safe]
  events: SCOPED-NAME @acme/auth-lib bound to private registry; BAIT public copy of internal name @acme/auth-lib: ['1.5.0']

Scenario 3: typosquat (public-only name)
  reqeusts@* | private: - | public: ['2.31.0']
  flawed -> 2.31.0 from PUBLIC [PWNED] | fixed -> REJECTED (no install) [safe]
  events: REJECT-UNAPPROVED reqeusts (no allow-list entry)
```

Read scenario 1 carefully: the bait `1.9.5` is deliberately in-range for
`^1.2.0`, because that is what a real attacker would publish. The fixed
resolver never queries the public registry for allow-listed names, yet still
reports the bait - that detection event is what proxy logs should emit in
production, per build, without human interpretation.

## Detection and Response Checklist

- Scheduled searches of public registries for every internal name; any hit is
  an incident, not a curiosity (Birsan's targets learned they were probed
  only from his reports).
- Proxy alerts on any fetch of an internal name from the public upstream, and
  on canary-package fetches.
- CI egress monitoring: unexpected DNS or HTTPS from a build step means a
  payload got in (Birsan's own exfiltration used DNS queries).
- Lockfile diffs reviewed as code: new names, first-time sources, range
  changes need a human.
- Pre-planned response: rotate CI-adjacent credentials, quarantine the
  build's artifacts, rebuild from a clean runner.

Post-2021 tooling: `osv-scanner` consumes lockfiles and SBOMs and matches
them against the OSV vulnerability database - it catches known-bad versions,
complementary to confusion defenses since a fresh bait has no advisory yet.
Behavioral scanners and provenance verification (see the SCA table in
[Software Supply Chain](software-supply-chain.md)) narrow that window.

## Interview Traps

- "Just use a lockfile" is incomplete: pinning stops drift, not first
  contact; pair it with source binding.
- "`^` ranges are safe" is wrong: scenario 1 shows an in-range bait winning.
- "We have an upstream proxy, so we're covered" fails for names that do not
  exist internally yet - and for typos, which no resolver defends against.
- Scoping helps only if the org actually claimed its scope publicly.

Cross-references: [Software Supply Chain](software-supply-chain.md) (attack
surface overview, SCA tooling), [SBOM, SLSA, and Provenance](sbom-slsa.md)
(attestation for rebuilt artifacts), the survey-level
[Supply Chain Security](../security/supply-chain-security.md) chapter, and
[Reproducible Builds](reproducible-builds.md).

## References

1. A. Birsan, "Dependency Confusion: How I Hacked Into Apple, Microsoft and Dozens of Other Companies," Feb 9, 2021. https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610 (403 to automated fetches; article text verified via a reader mirror and contemporaneous secondary reporting)
2. npm Docs, "scope" - scope-to-registry binding for install and publish. https://docs.npmjs.com/cli/v10/using-npm/scope
3. PyPI, "Trusted Publishing" - OIDC-based short-lived upload tokens. https://docs.pypi.org/trusted-publishers/
4. Microsoft Learn, "What are upstream sources?" (Azure Artifacts). https://learn.microsoft.com/en-us/azure/devops/artifacts/concepts/upstream-sources?view=azure-devops
5. AWS, "Upstream repository priority order" (CodeArtifact). https://docs.aws.amazon.com/codeartifact/latest/ug/repo-upstream-search-order.html
6. Microsoft Learn, "Package Source Mapping" (NuGet). https://learn.microsoft.com/en-us/nuget/consume-packages/package-source-mapping
7. pip, "Secure installs" - hash-checking mode (`--require-hashes`). https://pip.pypa.io/en/stable/topics/secure-installs/
8. npm Docs, "Generating provenance statements" (2023). https://docs.npmjs.com/generating-provenance-statements
9. dart.dev, "Verified publishers" (pub.dev domain-ownership badge). https://dart.dev/tools/pub/verified-publishers
10. The Go Authors, "Go Modules Reference" - `GOPRIVATE`/`GONOPROXY`. https://go.dev/ref/mod
11. Microsoft, "3 Ways to Mitigate Risk When Using Private Package Feeds" (white paper linked from the disclosure). https://aka.ms/pkg-sec-wp
12. google/osv-scanner - lockfile/SBOM scanning against the OSV database. https://github.com/google/osv-scanner
13. Thinkst Canarytokens - DNS/web tripwires for build networks. https://canarytokens.org/generate
