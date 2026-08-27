# SBOM and SLSA: Inventories vs. Provenance

An SBOM (Software Bill of Materials) answers one question: **what is inside this
artifact?** SLSA (Supply-chain Levels for Software Artifacts) answers a different
one: **who built it, on what platform, and can that claim be forged?** They fail
in opposite ways: an SBOM is a claim about artifact *contents* with no
authenticity of its own, while SLSA provenance is a claim about the *build
process* whose value comes entirely from who signs for it. This page dissects
what each format contains at the field level, runs the "Log4j day" exercise
that shows where inventories stop helping, then takes apart SLSA v1.0's
build-track levels, the in-toto attestation format that carries provenance, and
the policy flow that consumes attestations in CI/CD.
The survey-level tour of tools (Syft, Grype, Dependency-Track, CI hardening)
lives in [Software Supply Chain](./software-supply-chain.md); the threat-model
fundamentals are in [Supply Chain Security](../security/supply-chain-security.md).

## What an SBOM Actually Contains

Both major standards - SPDX 2.3 (ISO/IEC 5962, Linux Foundation) and
CycloneDX 1.6 (OWASP) - express the same four ideas: component inventory,
cryptographic hashes, machine-resolvable package identifiers, and a dependency
graph. The field-level translation between them matters in practice, because
your scanner emits one and your customer's compliance pipeline consumes the other.

| Concept | SPDX 2.3 JSON | CycloneDX 1.6 JSON |
|---------|---------------|--------------------|
| Document header | `spdxVersion`, `SPDXID`, `creationInfo` | `bomFormat`, `specVersion`, `serialNumber`, `metadata` |
| Component identity | `packages[].SPDXID` (`SPDXRef-` prefix) | `components[].bom-ref` |
| Name and version | `name`, `versionInfo` | `name`, `version` |
| Supplier | `supplier: "Organization: ACME"` | `supplier: {name: "ACME"}` |
| Hashes | `checksums: [{algorithm: "SHA256", ...}]` | `hashes: [{alg: "SHA-256", content}]` |
| Package identifier | `externalRefs[]`, `referenceType: "purl"` | first-class `purl` property |
| Dependency graph | `relationships[]`, `relationshipType: "DEPENDS_ON"` | `dependencies[]`, `dependsOn: [refs]` |
| License data | `licenseConcluded`, `licenseDeclared` | `licenses: [{expression}]` |

Two engineering details in this table carry most of the real-world value.

**The purl (package URL)** is the one identifier both ecosystems agree on. Its
syntax is `scheme:type/namespace/name@version?qualifiers#subpath`, and it
resolves to exactly one package in exactly one ecosystem:

```text
pkg:npm/%40angular/animation@12.3.1
pkg:pypi/django@1.11.1
pkg:deb/debian/curl@7.50.3-1?arch=i386&distro=jessie
```

A vulnerable-version report that says "log4j-core 2.14.1" is ambiguous (which
registry, which vendor fork?); `pkg:maven/org.apache.logging.log4j/log4j-core@2.14.1`
joins against CVE feeds with no human guessing. SPDX wraps purls in
`externalRefs` with `referenceCategory: "PACKAGE-MANAGER"`; CycloneDX carries a
`purl` field on every component (spec: `github.com/package-url/purl-spec`).

**The dependency graph is the hard part.** Flat component lists are easy;
`relationships`/`dependencies` are where generators earn their keep. SPDX
defines dozens of typed relationships beyond `DEPENDS_ON` (`BUILD_DEPENDENCY_OF`,
`PATCH_FOR`), which is why license-compliance teams prefer it; CycloneDX keeps
only the `dependsOn` adjacency list, which is why reachability tools prefer it.
A generator that emits components but an empty `dependencies` section has
produced something close to useless: you know `log4j-core` is in the image, but
not *which of your services pulled it in transitively*.

## Necessary, Not Sufficient: The Log4j Day Exercise

When CVE-2021-44228 (Log4Shell) landed in December 2021, the misery of that week
was not a lack of information - the CVE, the PoC, and the fix were public within
days - it was that most organizations could not answer three operational
questions quickly. An SBOM helps with each and is sufficient for none.

| Question on disclosure day | What an SBOM gives you | What the SBOM alone cannot tell you |
|----------------------------|------------------------|-------------------------------------|
| Am I affected? | Exact purls and versions per artifact; join against the CVE range in minutes | Whether the vulnerable path is reachable (JNDI lookups enabled? logged strings attacker-controlled?) |
| Where is it deployed? | Maps image -> components, so inventory DBs can be searched | Where images are actually *running* - needs SBOMs attached to deployed artifacts plus a fleet inventory |
| How fast can I rebuild? | Nothing. This is the gap | The build process, its inputs, and a trusted platform to re-run them on - provenance territory |

The third row is the one teams discovered the hard way. Knowing that
`payments-api:2.3.1` contains `log4j-core 2.14.1` does not tell you whether a
patched image ships in twenty minutes or twenty days, because the SBOM carries
no record of how the image was built: which builder, which source revision,
which dependency mirror. Worse, `mvn dependency:tree` on a developer laptop
tells you what *should* be true, while the artifact in the registry may have
been built from stale or tampered inputs.

Mature incident response therefore pairs SBOMs with two complementary
mechanisms. **VEX** (Vulnerability Exploitability eXchange) documents, per
artifact, whether a listed component is actually exploitable - "not affected:
logging of attacker-controlled data is disabled" saves you from rebuilding
hundreds of services. **Rebuild capability** comes from hermetic, reproducible
builds with provenance: [Build Systems](./build-systems.md) covers the
engineering; SLSA covers the guarantees.

## SLSA v1.0: Tracks, Levels, and the Responsibility Split

SLSA was published by the OpenSSF after the SolarWinds incident. Much of what
circulates - including material elsewhere in this book - describes the v0.1
ladder of four levels culminating in an L4 requiring hermetic, reproducible,
two-person-reviewed builds. **Version 1.0 (April 2023) restructured the model**:

- **Tracks replace the single ladder.** Levels are scoped to one aspect of
  supply-chain security per track, so progress in one aspect is not blocked by
  an unrelated one.
- **v1.0 is deliberately a build specification.** The spec states that the
  source aspects were removed to focus on the Build track, with a Source track
  deferred; it subsequently landed in v1.2 (current at the time of writing),
  which defines Source levels from "version controlled" through "two-party
  review".
- **The old L4 is gone.** Hermeticity and reproducibility are no longer a SLSA
  level; they remain excellent build-system engineering, but nothing in v1.0
  requires them.
- **Formats are informative.** v1.0 requires provenance with equivalent
  information, recommending but not mandating the SLSA Provenance format.

The Build track levels, in intent per the v1.0 spec (L0 is the implicit
starting point - no requirements, dev/test builds):

| Level | Name | Requirement | Focus / threat addressed |
|-------|------|-------------|--------------------------|
| Build L1 | Provenance exists | Provenance showing how the package was built | Mistakes; trivially forged |
| Build L2 | Hosted build platform | Signed provenance, generated by a hosted build platform | Tampering *after* the build |
| Build L3 | Hardened builds | Hardened build platform; provenance non-falsifiable | Tampering *during* the build |

The L1 -> L2 -> L3 progression is not "more metadata"; it is a progression in
**who is able to lie**. At L1 anyone can generate provenance, so it catches
accidents only. At L2 the provenance is signed by a hosted platform (GitHub
Actions, Cloud Build), so the producer cannot forge it - but the producer still
controls what runs on the platform. At L3 the provenance must be generated by
the platform's control plane rather than by the tenant's build steps, with
builds isolated from each other: the producer cannot falsify it even though
they own the repository.

Second conceptual change: **v1.0 splits responsibility explicitly between the
producer and the build platform**, and each level says which party guarantees
what. From the v1.0 requirements tables:

| Implementer | Requirement | L1 | L2 | L3 |
|-------------|-------------|----|----|----|
| Producer | Choose an appropriate build platform | Yes | Yes | Yes |
| Producer | Follow a consistent build process | Yes | Yes | Yes |
| Producer | Distribute provenance | Yes | Yes | Yes |
| Build platform | Provenance generation: exists | Yes | Yes | Yes |
| Build platform | Provenance generation: authentic | - | Yes | Yes |
| Build platform | Provenance generation: unforgeable | - | - | Yes |
| Build platform | Isolation strength: hosted | Yes | Yes | - |
| Build platform | Isolation strength: isolated | - | - | Yes |

Consumers close the loop: the verification model has the consumer fix
*expectations* for a package's provenance (which builder id, which source
repository, which build type) and compare each artifact's actual provenance
against them. The platform guarantees authenticity; the consumer guarantees
the comparison happens. A signed provenance nobody verifies is SLSA theater.

## Provenance as an in-toto Statement

SLSA does not define a wire format of its own; it rides on **in-toto
attestations**. The statement layer binds a claim to an immutable subject and
names the predicate type:

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [{"name": "app-1.4.2.tar.gz", "digest": {"sha256": "9a1f..."}}],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": { "...": "typed payload" }
}
```

The fields each do a specific job:

- `_type` pins the statement schema version, so verifiers reject structures
  they were not built to parse.
- `subject` is matched **purely by digest** - the name is advisory - which
  binds the attestation to the artifact rather than to a mutable tag.
- `predicateType` is a URI namespace switch: the same envelope carries SLSA
  provenance (`https://slsa.dev/provenance/v1`), SBOMs (CycloneDX and SPDX
  have registered predicate types), and vulnerability scan results.

For SLSA Provenance v1 the payload has two required sections,
`buildDefinition` and `runDetails`, and the split encodes the threat model:
`externalParameters` are the inputs the producer admits to choosing (repo,
ref, workflow), `internalParameters` are what the platform asserts (base image,
toolchain), `resolvedDependencies` lists immutable inputs with digests, and
`builder.id` names the transitive closure of everything you must trust.
`runDetails` adds `metadata` (`invocationId`, `startedOn`, `finishedOn`) and
`byproducts` (stdout, SCA reports). Releases built with the
`slsa-github-generator` carry this shape, signed by the workflow identity.

## The Verification Flow

Everything above converges on this pipeline - what "SLSA compliant" means
operationally:

```text
 source repo              build platform                       registry
 -------------  trigger  -------------------------   push   -------------
 | commit SHA | -------> | runs build steps        | -----> | image:1.4.2 |
 -------------            | inside isolation        |        | (digest D)  |
                          |                         |        ------+------
                          | control plane generates |              |
                          | in-toto statement       |              | attach as
                          |  subject = digest D     |              | OCI referrer
                          |  predicateType =        |              |
                          |    slsa.dev/provenance  |              |
                          |  sign (platform key)    |              |
                          -------------------------                v
                                                                attestation

  consumer CI/CD or admission control
  -----------------------------------------------------------
  | pull artifact; fetch attestation by digest D            |
  | verify signature chain against trusted platform keys
  | compare predicate to expectations: builder.id? repo/ref?
  |   buildType? scan-result attestation: no critical CVEs?
  | pass -> deploy          fail -> reject + alert
  -----------------------------------------------------------
```

The policy engine is the load-bearing component: `cosign verify-attestation`
does the cryptographic check, Kubernetes admission controllers (Sigstore's
policy-controller, Kyverno) enforce the expectation comparison at deploy time,
and the Verification Summary Attestation formalized in SLSA v1.1 lets a
producer pre-verify once and hand consumers a compact signed result. The
engine's question is never "is there provenance?" but "does it match what I
expect this build to look like?"

## The Transferable Lesson

If you take one idea from this page: **provenance is about the build platform's
guarantees, not the artifact list.** An SBOM is a list of claims; nothing makes
a list true, and an attacker who controls a build can emit an SBOM describing a
clean artifact. SLSA never tries to make the list truer - it moves the
*attestation* of everything (contents via attached SBOMs, process via
provenance) to a party whose incentives diverge from the attacker's: a hosted,
isolated platform that will not sign what it did not run. Every level, the
producer/platform responsibility split, and the digest-matched `subject` are
variations on moving trust from "whoever hands me the file" to "the
infrastructure that claims to have built it". Design any attestation system -
build provenance, scan results, deployment records - by asking: who can forge
this, and what would it cost them?

## Where This Breaks in Practice

- **SBOM drift.** An SBOM generated from the lock file misrepresents the image
  if later layers add or strip packages. Generate from the final artifact,
  attach it as an OCI referrer so it travels with the digest.
- **Provenance without consumption.** Many CI systems emit signed provenance
  now; almost nothing rejects on it unless a policy engine is wired in. The
  unverified half of the v1.0 split is the half that fails silently.
- **Builder allowlist monoculture.** Policy accepting exactly one `builder.id`
  turns that platform into a single point of failure - for you and for attackers.
- **Reproducibility is not a level.** Post-v1.0, nothing forces two independent
  rebuilds to agree bit-for-bit; teams needing that implement it at the
  build-system layer and record evidence in byproducts.

## References

1. [SLSA v1.0 - Security Levels](https://slsa.dev/spec/v1.0/levels) - build track L0-L3 and the track model
2. [SLSA v1.0 - Producing Artifacts](https://slsa.dev/spec/v1.0/requirements) - producer vs. build-platform responsibility matrices
3. [in-toto Attestation Spec - Statement layer](https://github.com/in-toto/attestation) - `_type`/`subject`/`predicateType` schema
4. [SLSA Provenance predicate v1](https://slsa.dev/provenance/v1) - `buildDefinition` and `runDetails` fields
5. [SPDX](https://spdx.dev/) and [CycloneDX](https://cyclonedx.org/) - the two SBOM standards compared above
