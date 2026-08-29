# Credential Rotation: From Static Secrets to Short-Lived Identity

[Secrets Management](../secrets-management.md) answers *where secrets live*; this page answers
*when secrets die* and how to kill them without an outage. In a distributed system rotation is
a coordination problem across an issuer, stores, and every consumer that cached a copy -- a
live schema migration whose failure mode is an auth storm instead of a 500. This page builds
the taxonomy, derives the overlap-window math, contrasts each credential family's rotation
story, and explains the endgame: making rotation disappear into issuance (short-lived identity;
see [SPIFFE/SPIRE](./spiffe-spire.md)).

## Three Clocks: Expiration, Rotation, Revocation

Every credential has up to three timers; conflating them is where interview answers fail:

| Timer | Trigger | Who initiates | Notice given | Blast radius if missed |
|---|---|---|---|---|
| Expiration | TTL lapses | The credential itself | Planned (TTL is known) | Outage, not a leak |
| Scheduled rotation | Policy calendar | Owner, proactively | Full (overlap plannable) | Slow drift back toward the old radius |
| Revocation | Suspected/real compromise | Incident responder | None (must be instant) | Full remaining lifetime of the credential |

NIST SP 800-57 calls the policy version the **cryptoperiod**: the span a key is authorized
for use, weighing risk against replacement cost (Part 1 Rev. 5, Section 5.3). The practical
point: **revocation is rotation with zero notice.** A team that has never rotated on schedule
has no working path to rotate during an incident; drills are the only evidence that the
emergency path exists.

## Why Rotation Windows Exist: Bounding the Blast Radius

The case rests on one observation: a leaked credential's value decays only when its
validity does. If detection takes days and rotation minutes, a 365-day key carries a year
of detection risk; a 1-hour key carries at most an hour. Lifetime is a risk ceiling chosen
in advance.

Why not rotate hourly? Each rotation is a mini-deployment with its own failure modes -- a
half-executed rotation is an outage with the leak still open. The window balances
**security** (blast radius = remaining lifetime) against **reliability** (every consumer
must pick up the new value before the old dies; longer windows forgive stragglers).

Real cadences balance the two: session tokens 15-60 minutes, mTLS workload certs ~1-24 hours,
database passwords 30-90 days, signing keys weeks-to-months, long-lived API keys quarterly
with secret scanning compensating in between.

## The Hard Problem: One Invariant, Three Tiers

A rotation must propagate issuer -> store -> consumers, and the tiers move at different
speeds. The zero-downtime invariant: *when the issuer retires version v, no consumer may
hold only v, and v+1 must already be fetchable.* Since consumers refresh lazily, the only
guarantee is an **overlap window**: publish v+1 early, accept both versions, and wait out
worst-case staleness before retiring v:

```text
T_publish                      T_retire
|<------- overlap O --------->|
|                              |
v+1 live in store              issuer rejects v
issuer accepts v AND v+1       (only v+1 accepted)
|
      ^ worst case: a consumer fetched v one tick before T_publish and may keep
      | using it for up to (r + c + d) after publication, where d = store-to-
      | consumer latency, s = clock skew.  Requirement: O >= max_i(r_i + c_i) + d + s
```

**Dual acceptance is the crux.** Some issuers do it natively: JWT verifiers accept old and
new signing `kid`s, TLS servers can serve both chains, cloud IAM principals hold multiple
active keys. Where it is impossible -- a database with *one* password per user -- the
workaround is structural: two accounts, alternating. AWS Secrets Manager ships exactly
this as its "alternating users" template family, alongside "single user" templates that
accept a brief credentialless window. Which family you are in decides whether rotation
is a non-event or a maintenance risk.

## Credential-Type Rotation Stories

Rotation is not one mechanism; each family has a different issuer contract:

| Credential | Issuer | Dual-accept mechanism | Consumer pickup | Typical window | Classic failure |
|---|---|---|---|---|---|
| DB password (single user) | DB user table | None -- one live password | Connection reload + pool drain | Minutes of risk | Pooled sessions killed mid-transaction |
| DB password (alternating users) | Two DB users | Both users valid simultaneously | Secret-store watcher | Days-weeks | Second user drifts out of password policy |
| Cloud API key | IAM (console/API) | Multiple active keys per principal | Redeploy / config reload | Hours of overlap | Old key left active "temporarily" forever |
| Cloud STS token | STS / federation | None needed -- fresh token per session | Re-issue on expiry | 15-60 min | Hard dependency on token endpoint uptime |
| mTLS cert (internal CA) | CA / SPIRE (see [mTLS](../mtls.md)) | Old chain valid until expiry; new handshakes use new cert | Agent / SVID renewal | 1-24 h TTL | Clock skew rejects valid certs |
| JWT/OIDC signing key | Auth server, JWKS endpoint | Old `kid` verifiable until token TTL passes | JWKS refresh on unknown `kid` | Weeks-months | JWKS cache outlives old key -> mass 401s |

The pattern: **the harder it is for the issuer to accept two versions, the more rotation
pain lands on consumers.** STS-style credentials flip this -- "rotation" is just issuance,
and consumers already know how to re-authenticate.

## Model: Computing the Required Overlap Window

The planner takes a deploy latency, per-consumer-class refresh/cache behavior, and a policy
cap on dual-accept time, then prints the class table and the chosen schedule (labeled
**model**: values illustrative; the invariant is the point):

```python
"""Overlap-window planner (model): how long must two credential versions
coexist so no consumer is ever caught holding only the retired key?

  issuer retires version v at T_retire; v+1 is published T_retire - O and
  dual-accepted in between. Consumer class i refreshes every r_i, caches
  c_i seconds; worst case it fetched v just before publication and keeps
  it until its next refresh. d = store-to-consumer latency, s = clock skew.
  Invariant: O >= max_i(r_i + c_i) + d + s. Under policy cap W on dual-
  accept time, class i is safe only if r_i + c_i + d + s <= W; violators
  need capped jobs, mid-run broker fetch, or short-lived identity.
"""
D, S, W = 90, 30, 3600  # deploy latency, skew, policy cap (seconds)

CLASSES = [             # (name, refresh r_i, cache c_i)
    ("edge-api  ",   60,    60),
    ("worker    ",  300,   900),
    ("batch-job ",    0, 43200),   # reads secret once at start, runs up to 12h
]

def fmt(sec):
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"

print(f"deploy latency d={D}s  skew s={S}s  policy cap W={fmt(W)}")
print()
print("class         refresh  cache    stale bound  safe under W   max safe cache")
for name, r, c in CLASSES:
    ok = r + c + D + S <= W
    cmax = W - D - S - r
    flag = "yes" if ok else "NO "
    print(f"{name}   {fmt(r):>8}  {fmt(c):>7}  {fmt(r + c):>11}   {flag}          {fmt(cmax)}")

overlap = max(r + c for _, r, c in CLASSES) + D + S
print()
print(f"required overlap = max(r+c) + d + s = {fmt(overlap)}; fits cap W: {overlap <= W}")
print()
print("chosen schedule (per rotation):")
print(f"  T_publish = T_retire - {fmt(overlap)}   v+1 live in store; issuer accepts v and v+1")
print( "  T_retire                                v rejected; only v+1 accepted")
```

Output (real run of the script above):

```text
deploy latency d=90s  skew s=30s  policy cap W=01:00:00

class         refresh  cache    stale bound  safe under W   max safe cache
edge-api     00:01:00  00:01:00     00:02:00   yes          00:57:00
worker       00:05:00  00:15:00     00:20:00   yes          00:53:00
batch-job    00:00:00  12:00:00     12:00:00   NO           00:58:00

required overlap = max(r+c) + d + s = 12:02:00; fits cap W: False

chosen schedule (per rotation):
  T_publish = T_retire - 12:02:00   v+1 live in store; issuer accepts v and v+1
  T_retire                                v rejected; only v+1 accepted
```

Read the verdict honestly: a long-running batch job that reads its secret once at startup
*forces* a 12-hour dual-accept window or an outage -- under a 1-hour cap it is structurally
unsafe, and the fixes are the docstring's three: cap job duration, fetch mid-run, or give
the job short-lived identity. Asked "why do our keys live 90 days?", the honest answer is
usually "because some consumer's cache TTL silently dictates it"; the fix is consumer-side.

## The Short-Lived Pivot: Rotation Becomes Issuance

The endgame is to stop coordinating rotation and start issuing credentials that die on
their own:

- **STS / session tokens.** Cloud session credentials last 15-60 minutes (AWS STS; IAM
  Roles Anywhere extends the model off-cloud via X.509 client certs). Sessions
  re-authenticate anyway, so "rotation" is issuance under a policy changed at the issuer.
- **Vault dynamic secrets.** Vault's database engine mints per-request credentials with a
  lease; expiry revokes them without touching consumers (see [Vault](../vault.md)).
- **OIDC federation for CI.** GitHub Actions and friends mint short-lived OIDC tokens
  that a cloud trusts to assume a role -- no stored cloud key exists to rotate at all.
- **Workload identity.** SPIRE issues X.509 SVIDs with ~1-hour TTLs that agents renew
  continuously; revocation collapses into expiry. The full attestation story lives in
  [SPIFFE/SPIRE](./spiffe-spire.md); this page deliberately does not re-derive it.

The trade is real: short-lived credentials convert one rare coordination event into a
*constant dependency on the issuer's availability* -- a dead token endpoint is now an outage;
that is the price of making blast radius equal remaining TTL.

## Exposure Detection: Rotation's Sensor

Scheduled rotation bounds the damage of a *known* leak; scanning is how leaks become
known. Secret scanning runs over repositories (push-time protection, git history) and
increasingly provider-side: GitHub's secret scanning detects leaked tokens from dozens of
partner providers and can alert or auto-revoke; the OWASP cheat sheet treats detection as
lifecycle, not add-on.

- **Rotate, don't rewrite.** Purging a secret from git history does nothing once the repo
  has been cloned; the credential is burned the moment it hits a remote. Rotation plus
  revocation is the response; history rewriting is hygiene.
- **Scanning without rotation is alert fatigue**: you surface leaks you cannot cleanly fix
  because the emergency path was never exercised. The two capabilities are one system.

## Automation Patterns and the Last-Hop Problem

| Pattern | Who writes v+1 | How consumers switch | Residual gap |
|---|---|---|---|
| Rotation function (AWS SM) | Provider-triggered Lambda | Pull on next read | Caches beyond the window |
| Vault Agent / sidecar fetch | Vault engine (lease/renew) | Agent renders templates / pushes | Process must re-read files |
| External Secrets Operator | ESO syncs provider -> k8s Secret | kubelet updates mounted volumes (sync period + cache delay) | env-injected values never update; needs restart |
| CI OIDC federation | Nobody -- token minted per run | Token expires with the job | Issuer availability |

ESO automates the *store* hop; Kubernetes automates the *volume* hop, eventually (kubelet
sync period plus propagation delay); but a process that read the value into an environment
variable at boot never sees any of it. **The last hop -- the consumer's own reload
semantics -- is the hard one**; short-lived identity solves it by letting expiry, not
consumer cooperation, do the work.

## Audit Evidence

Rotation's evidence is nearly free if you log the right things. A reviewer should be able
to pull: (1) **coverage** -- every credential with an owner, a policy TTL, and a
last-rotated timestamp, with a "% within policy" metric that stays at 100; (2) **the dual
window itself** -- issuer logs showing v+1 accepted before v retired, zero auth failures
attributable to the cutover; (3) **drill evidence** -- an emergency rotation rehearsed in
staging, signal-to-rotated time measured. Without these, rotation is folklore.

## Failure Patterns (Recurring Post-Mortem Shapes)

These shapes recur across public post-mortems; none is pinned to a named incident here:

1. **Rotation faster than pickup.** A TTL is shortened for compliance without recomputing
   the overlap; a weekend batch job holds the retired key, and Monday brings an auth-failure
   storm. Fix: run the planner; size TTLs from consumer staleness bounds.
2. **Revocation that kills in-flight work.** Rotating a single-user DB password terminates
   pooled connections; retries stampede the database, and a contained rotation becomes an
   outage. Fix: alternating users or a graceful drain before cutover.
3. **JWKS cache skew.** Verifiers cache signing keys longer than the old key stays
   verifiable; after rotation, valid tokens fail. Fix: refresh JWKS on unknown `kid`, and
   keep the previous key verify-only for one token TTL.
4. **KMS rotation misread as retro-protection.** Rotating a managed KMS key re-keys *future*
   operations; existing ciphertexts stay under the old key material (decrypted
   transparently). Treating rotation as re-encryption overstates the compliance posture.

## References

- [OWASP Cheat Sheet Series: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [NIST SP 800-57 Part 1 Rev. 5 -- Key Management (cryptoperiods, Section 5.3)](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final)
- [AWS Secrets Manager: Rotation templates (single user vs alternating users)](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html)
- [AWS IAM Roles Anywhere (X.509-based short-lived sessions off-cloud)](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/introduction.html)
- [Google Cloud IAM: Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [HashiCorp Vault: Database Secrets Engine (dynamic credentials with leases)](https://developer.hashicorp.com/vault/docs/secrets/databases)
- [External Secrets Operator (provider-to-Kubernetes sync)](https://external-secrets.io/latest/)
- [GitHub Docs: Secret scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)
- [GitHub Docs: OIDC federation for Actions deployments](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [Kubernetes: Secrets concepts (mounted-volume update semantics)](https://kubernetes.io/docs/concepts/configuration/secret/)
