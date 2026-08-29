# Artifact Registries: Inside the Pull and Push Path

An artifact registry is the content-addressed store behind every `docker pull`: an
HTTP service of immutable blobs keyed by digest, linked into named repositories via
manifests, fronted by bearer-token auth. The
[OCI Distribution Spec](https://github.com/opencontainers/distribution-spec/blob/main/spec.md)
defines the wire contract (latest tagged release v1.1.1; containerd pins its clients
to v1.0.0 compliance). The image format it carries is covered in
[the OCI image spec page](../linux/containers/oci-image-spec.md) and
[OCI overview](../linux/containers/oci.md); this page goes one layer down into
registry behavior itself.

## Content-Addressed Storage

Everything is a blob. A **digest** is `sha256:` plus the hex SHA-256 of the exact
bytes (the spec registers `sha256` and `sha512`, plus a `digest-algorithm` upload
parameter for others). Integrity is free: clients recompute digests after pulling, so
a manifest cannot lie about layer contents. Dedup is global: identical layers,
configs, even manifest bodies are stored once per registry regardless of how many
repositories reference them, because the digest *is* the identity. The reference
implementation (`distribution/distribution`) keeps blobs and per-repository link
files under `/var/lib/registry` (see its `registry/storage/paths.go`):

```text
docker/registry/v2/
  blobs/sha256/<first-two-hex>/<hex>/data        <- global CAS: the actual bytes
  repositories/<name>/_manifests/tags/<tag>/current/link
  repositories/<name>/_layers/sha256/<hex>/link  <- blob referenced by this repo
  repositories/<name>/_uploads/<id>/startedat    <- expires abandoned sessions
```

A repository is a *view* over shared blobs: pushing one base layer to 100
repositories adds 100 link files and zero bytes. The CAS is the single source of
truth; per-repository state is just pointers.

## Push and Pull

Blob upload is a stateful session, deliberately chunk-friendly for flaky CI networks
and big layers. `POST /v2/<name>/blobs/uploads/` with `Content-Length: 0` opens it:
`202 Accepted` plus a session `Location`, optionally advertising `OCI-Chunk-Min-Length`.
Chunks are `PATCH`ed with an inclusive `Content-Range: <start>-<end>`; chunks MUST be
in order starting at byte 0, out-of-order gets `416 Requested Range Not Satisfiable`,
and `GET` on the session URL returns the current offset (`204` plus `Range`) for
resume. `PUT <location>?digest=<digest>` closes the session with the whole-blob
digest and returns `201 Created` with a pullable `Location` - possibly a signed
cloud-storage URL rather than the registry itself. `DELETE` cancels; registries also
expire abandoned sessions (the reference implementation records `startedat` per
upload for purging).

The most under-used push optimization is the **cross-repo mount**:

```text
POST /v2/<name>/blobs/uploads/?mount=<digest>&from=<other_name>
  201 Created + Location   -> blob mounted into <name>, zero bytes transferred
  202 Accepted + Location  -> cannot/won't mount; fall back to a session upload
```

If the blob exists anywhere in the registry, pushing `app:v2` transfers only the
layers changed since `app:v1`; registries MAY treat `from` as optional and mount if
they can find the blob. Manifests go last, after every referenced blob exists. A
manifest with a `subject` field must be accepted even if the subject does not exist
yet; the registry signals referrers support with an `OCI-Subject` response header.

Pulling mirrors this. `GET /v2/` pings (200, or 401 with `WWW-Authenticate`); a
manifest GET carries an `Accept` header listing every manifest media type the client
understands; multi-arch images return an image index whose descriptors point at
per-platform manifests, so a pull is two manifest GETs followed by `HEAD`/`GET` on
blobs, verifying each digest after download. Tag resolution is mutable - the tag's
`current/link` can change between requests, which is exactly why reproducible builds
pin by digest; digest resolution is immutable and cache-safe. Listings paginate via
`n`/`last` parameters plus a `Link` header, tags in lexical order.

## Registry Auth Token Flow

Registries delegate to a separate token issuer. The canonical exchange (from the
distribution token spec, whose example is quoted verbatim):

```text
Client -> Registry:  GET /v2/
Registry -> Client:  401 Unauthorized
     WWW-Authenticate: Bearer realm="https://auth.docker.io/token",
        service="registry.docker.io",scope="repository:samalba/my-app:pull,push"
Client -> Realm:     GET /token?service=...&scope=repository:samalba/my-app:pull,push
Client -> Registry:  Authorization: Bearer <token>    (retry the original request)
```

The bearer token is a short-lived signed JWT encoding the granted scopes; multiple
scopes are space-separated, and an opaque, unexpiring refresh token (`offline_token=1`)
mints fresh scoped tokens without re-login. Upstream authentication differs:

| Registry | How clients get credentials | Distinctive detail |
|---|---|---|
| Docker Hub | access token to auth.docker.io | anonymous pulls get tokens too - that is how the IP-based pull limit is enforced |
| GHCR | GITHUB_TOKEN in Actions for the workflow's own repo; PAT with `read:packages` beyond it | public images are pullable anonymously |
| ECR | IAM principal calls GetAuthorizationToken (base64 `AWS:<password>`) | Docker CLI cannot speak IAM natively; token is valid for 12 hours |
| Artifact Registry | gcloud-managed access tokens | writing to the legacy gcr.io Container Registry shut down March 18, 2025; gcr.io URLs hosted by Artifact Registry keep resolving |

## The Registry Landscape

| Registry | Hosting model | Mechanics worth knowing |
|---|---|---|
| Docker Hub | SaaS, largest public catalog | pull rate limits (below), org namespaces |
| GHCR | SaaS tied to GitHub permissions | packages inherit repo visibility; free for public images |
| ECR | AWS regional service | IAM-native, declarative lifecycle policies, pull-through cache rules for Docker Hub/Quay/GHCR/GitLab/Chainguard and more |
| Artifact Registry | Google regional service | multi-format (containers plus Maven/npm/PyPI); Azure's ACR is the regional analogue, geo-replicating in the Premium tier |
| Harbor / Quay | self-hosted OSS (Harbor is CNCF; `quay/quay` is open too) | registry-to-registry replication, proxy-cache projects, P2P preheat, quotas, Trivy scanning, retention DSL, scheduled GC, Quay geo-replication |
| registry.k8s.io | redirect service, not a store | maps pulls to CDN endpoints and community mirrors; publishes a mirroring guide for heavy users |

## Mirrors and Pull-Through Caches

A mirror intercepts pulls and serves cached blobs; pushes still go upstream or are
disallowed. Docker Engine accepts `--registry-mirror` (`registry-mirrors` in
`daemon.json`) and tries the mirror before falling back upstream. The reference
registry in proxy mode (`proxy.remoteurl`) becomes a pull-through cache with two hard
constraints from its own docs: it mirrors only **one upstream** at a time, and the
upstream URL must be the root of a domain; cluster members are stateless, each
keeping its own copy. containerd (see
[containerd internals](../linux/containers/containerd-internals.md)) uses per-host
`hosts.toml` files under `config_path = "/etc/containerd/certs.d"`, with the older CRI
`registry.mirrors` config explicitly deprecated and no daemon restart needed for host
changes. `registry.k8s.io` is a fifth shape: no storage, just a redirector sending
each pull to a nearby endpoint. Mirrors change pull latency and rate-limit exposure;
they never write upstream, so publishing builds still target a real registry
([Kaniko](../cloud/cicd/kaniko.md) is a common in-CI pusher).

## Retention and Garbage Collection

Deletion is a two-body problem: the manifest is the reference, the blob is the space.
The reference implementation's `registry garbage-collect` is classic mark-and-sweep -
**mark** every digest reachable from any manifest, then **sweep** and delete every
stored blob not in the mark set. It is stop-the-world by design: the docs warn to run
the registry read-only or not at all during GC, because a blob uploaded between the
mark and sweep phases can be swept while a concurrent push has already published a
manifest referencing it - the classic recipe for a corrupted image. `--dry-run`
prints what would be removed; `--delete-untagged` first deletes manifests no tag
references, which is how you reclaim CI's endless ephemeral builds. Deleting a tag
alone frees nothing until GC runs. Harbor wraps this with scheduled GC, a dry-run
mode, a two-hour reservation window so freshly uploaded layers are not swept
mid-push, and an explicit untagged-artifacts toggle. ECR sidesteps GC entirely with
declarative lifecycle policies (`tagStatus`, `tagPatternList`, `countType` values
like `imageCountMoreThan` or `sinceImagePushed`) evaluated on pushes rather than by a
sweeper process.

## Rate Limits and the CI Pull Storm

Docker Hub's fair-use table, per its usage-and-limits page:

| User type | Pull rate limit |
|---|---|
| Business / Team / Pro (authenticated) | unlimited |
| Personal (authenticated) | 200 pulls per 6 hours |
| Unauthenticated | 100 pulls per 6 hours per IPv4 address or IPv6 /64 subnet |

Docker also applies a separate abuse limit (order of thousands of requests per
minute) across all Hub properties: a plain `429 Too Many Requests` means the abuse
limit, while the pull limit returns a longer error message linking to the docs. Why
CI cares: hundreds of jobs behind one NAT egress IP share one anonymous identity, so
a pipeline-wide pull storm exhausts the 100-per-6-hours budget for everyone and fails
on an unrelated build step. Authenticating, pulling through a cache so only the
mirror's IP hits Hub, and promoting base images into your own registry (cross-repo
mount keeps the push cheap) each reduce exposure independently.

## Provenance Artifacts Live in the Registry Too

OCI 1.1 made the registry a discovery point for artifacts attached to images. A
manifest with a `subject` field declares "I refer to that digest"; registries expose
the reverse lookup as the referrers API, `GET /v2/<name>/referrers/<digest>`, which
returns an image index of referrers with `artifactType` filtering (an
`OCI-Filters-Applied` header confirms the filter ran) and must not 404 when empty.
Registries without the API fall back to the referrers tag schema, where cosign stores
signatures under a tag derived from the digest: `sha256:abc123...` becomes the tag
`sha256-abc123....sig`. That is the storage contract only - signature verification
itself is [Sigstore signing's](sigstore-signing.md) domain, SBOM attachment pipelines
live in [SBOM and SLSA](sbom-slsa.md) and [SPDX/CycloneDX](spdx-cyclonedx.md), and the
namespace-squatting risk that makes registry scopes a security boundary is covered in
[dependency confusion](dependency-confusion.md).

## A Runnable Registry Model

The script models the CAS semantics above: a global blob store, cross-repo mount on
shared layers, a CI runner's local cache absorbing pulls, and a mark/sweep GC pass
after a tag is dropped.

```python
#!/usr/bin/env python3
"""Mini OCI registry: CAS blobs, cross-repo mount, pull cache, mark/sweep GC."""
import hashlib
import json

BLOBS, TAGS, MANIFESTS = {}, {}, {}   # digest->bytes, (repo,tag)->digest, digest->manifest
PUSHED = NAIVE = 0                    # bytes on the wire vs a no-dedup registry

dgst = lambda b: "sha256:" + hashlib.sha256(b).hexdigest()

def push_blob(blob):
    global PUSHED, NAIVE
    d = dgst(blob); NAIVE += len(blob)
    if d in BLOBS:
        return d, "mounted"           # POST ?mount=<digest>&from=<repo> -> 201
    BLOBS[d] = blob; PUSHED += len(blob)   # else POST 202 -> PATCH chunks -> PUT
    return d, "uploaded"

def push_manifest(repo, tag, cfg, layers):
    global PUSHED, NAIVE
    for b in [cfg] + layers:          # spec: push all blobs BEFORE the manifest
        d, how = push_blob(b)
        print("    blob %-17s %-7s %6d bytes" % (d[:20], how, len(b)))
    m = {"config": dgst(cfg), "layers": [dgst(b) for b in layers]}
    body = json.dumps(m, sort_keys=True).encode(); d = dgst(body)
    MANIFESTS[d] = m; BLOBS[d] = body; TAGS[(repo, tag)] = d   # manifest = blob too
    PUSHED += len(body); NAIVE += len(body)
    print("    manifest %s:%s -> sha256:%s (%d bytes)" % (repo, tag, d[7:27], len(body)))

def pull(repo, ref, local):
    d = TAGS.get((repo, ref), ref)    # tag resolved once; digest used as-is
    wire = len(BLOBS[d]); got = 0
    for bd in [MANIFESTS[d]["config"]] + MANIFESTS[d]["layers"]:
        if bd not in local:           # local CAS hit = zero bytes on the wire
            local[bd] = BLOBS[bd]; wire += len(BLOBS[bd]); got += 1
    print("    pull %s:%s -> %d blobs fetched, %d bytes on wire" % (repo, ref, got, wire))

def gc():
    mark = set()
    for d in TAGS.values():           # mark: walk only TAGGED manifests
        mark |= {d, MANIFESTS[d]["config"], *MANIFESTS[d]["layers"]}
    swept = sorted(d for d in BLOBS if d not in mark)   # sweep everything else
    freed = sum(len(BLOBS[d]) for d in swept)
    for d in swept:
        del BLOBS[d]; print("    gc dropped %s" % d[:27])
    print("    gc: swept %d blobs, reclaimed %d bytes" % (len(swept), freed))

BASE, DEPS = b"base-layer" * 1250, b"deps-layer" * 3125
CFG_A, CFG_B = b'{"os":"linux"}A' * 30, b'{"os":"linux"}B' * 30
APP_A, APP_B, APP_B2 = b"app-a" * 1000, b"app-b" * 800, b"app-b-v2" * 800

push_manifest("team/svc", "v1", CFG_A, [BASE, DEPS, APP_A])
push_manifest("team/tool", "v1", CFG_B, [BASE, DEPS, APP_B])   # shares BASE+DEPS
print("  pushed %d bytes with dedup vs %d naive" % (PUSHED, NAIVE))
local = {}
pull("team/svc", "v1", local)
pull("team/tool", "v1", local)
print("  runner cache now holds %d blobs" % len(local))
push_manifest("team/tool", "v2", CFG_B, [BASE, DEPS, APP_B2])
del TAGS[("team/tool", "v1")]                                  # untag the old build
gc()
print("  final: %d blobs, %d bytes, %d tagged manifests" % (
    len(BLOBS), sum(len(v) for v in BLOBS.values()), len(TAGS)))
```

Output:

```text
    blob sha256:9c355c2d17611 uploaded    450 bytes
    blob sha256:c3962ef75f695 uploaded  12500 bytes
    blob sha256:67a5a9eee1676 uploaded  31250 bytes
    blob sha256:4271171e3ce65 uploaded   5000 bytes
    manifest team/svc:v1 -> sha256:5bfabc595016b185a2b2 (322 bytes)
    blob sha256:18d0b900b26e0 uploaded    450 bytes
    blob sha256:c3962ef75f695 mounted  12500 bytes
    blob sha256:67a5a9eee1676 mounted  31250 bytes
    blob sha256:1fd595533af65 uploaded   4000 bytes
    manifest team/tool:v1 -> sha256:3f0d5cb1e911d8a81549 (322 bytes)
  pushed 54294 bytes with dedup vs 98044 naive
    pull team/svc:v1 -> 4 blobs fetched, 49522 bytes on wire
    pull team/tool:v1 -> 2 blobs fetched, 4772 bytes on wire
  runner cache now holds 6 blobs
    blob sha256:18d0b900b26e0 mounted    450 bytes
    blob sha256:c3962ef75f695 mounted  12500 bytes
    blob sha256:67a5a9eee1676 mounted  31250 bytes
    blob sha256:26b43ec2bef67 uploaded   6400 bytes
    manifest team/tool:v2 -> sha256:aacc6dcadef28b65f1b6 (322 bytes)
    gc dropped sha256:1fd595533af65a3135b3
    gc dropped sha256:3f0d5cb1e911d8a81549
    gc: swept 2 blobs, reclaimed 4322 bytes
  final: 8 blobs, 56694 bytes, 2 tagged manifests
```

Read the transcript against the claims above: the second push transfers only 4,900
bytes because base and deps mount (54,294 pushed versus 98,044 naive); the second
pull costs 4,772 bytes because the runner's cache holds the shared layers; GC
reclaims exactly the untagged manifest plus its unique app layer.

## Failure Modes Checklist

- **429 during a release cut** - shared-IP pull limit; fix with auth plus a mirror, not retries.
- **Corrupted image after GC** - GC ran while pushes were live; gate it behind read-only mode.
- **Disk grows despite deleting tags** - untagged manifests still pin blobs until `--delete-untagged` GC or lifecycle rules reap them.
- **Signature or SBOM "missing" after re-push** - referrers attach to the *old* manifest digest, not to the tag.

## References

1. OCI Distribution Spec - <https://github.com/opencontainers/distribution-spec/blob/main/spec.md>
2. Distribution registry token authentication spec - <https://distribution.github.io/distribution/spec/auth/token/>
3. Distribution garbage collection docs - <https://distribution.github.io/distribution/about/garbage-collection/>
4. Distribution "Registry as a pull-through cache" recipe - <https://distribution.github.io/distribution/recipes/mirror/>
5. containerd registry host configuration (`hosts.toml`) - <https://github.com/containerd/containerd/blob/main/docs/hosts.md>
6. Docker Hub usage and limits - <https://docs.docker.com/docker-hub/usage/>
7. Amazon ECR pull-through cache rules - <https://docs.aws.amazon.com/AmazonECR/latest/userguide/pull-through-cache.html>
8. Amazon ECR private registry authentication - <https://docs.aws.amazon.com/AmazonECR/latest/userguide/registry_auth.html>
9. GHCR: Working with the Container registry - <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
10. Google Cloud: Transition from Container Registry - <https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr>
11. Harbor garbage collection - <https://goharbor.io/docs/2.12.0/administration/garbage-collection/>
12. Harbor proxy cache - <https://goharbor.io/docs/2.12.0/administration/configure-proxy-cache/>
13. cosign SIGNATURE_SPEC (tag-based discovery) - <https://github.com/sigstore/cosign/blob/main/specs/SIGNATURE_SPEC.md>
14. registry.k8s.io redirect and mirroring service - <https://github.com/kubernetes/registry.k8s.io>
