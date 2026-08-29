# SBOM Formats: SPDX 3.0 vs CycloneDX

[SBOM and SLSA](./sbom-slsa.md) covers what an SBOM is *for*; this page is
the format deep dive - how the two standards encode an inventory, what each
spec mandates versus merely allows, how identity and dependency edges are
spelled, how vulnerability status is exported, which tools emit which
dialect, and where in the pipeline the SBOM should be generated. The
standards agree on requirements and disagree on philosophy, and the
disagreements are what interviewers probe.

## Version Timeline

| Format | Version | Date | What it changed |
|--------|---------|------|-----------------|
| SPDX | 2.3 | Nov 2022 | Last 2.x edition; ISO/IEC 5962:2021 lineage |
| SPDX | 3.0 | Apr 2024 | Full model rewrite: element-based graph + profiles |
| SPDX | 3.0.1 | Dec 2024 | Patch release; the currently published version |
| SPDX | 3.1-RC1 | Jan 2026 | Draft circulating; not final |
| CycloneDX | 1.5 | Jun 2023 | ML-BOM, Formulation (MBOM), evidence, lifecycles |
| CycloneDX | 1.6 | Apr 2024 | CBOM, Attestations (CDXA); became Ecma standard ECMA-424 in Jul 2024 |
| CycloneDX | 1.7 | Oct 2025 | Final 1.x: CBOM algorithm/curve registries, Citations, top-level signature |
| CycloneDX | 2.0 | announced Aug 2026 | Threat models, risk, controls, materials provenance; Ecma ratification expected Dec 2026 |

Misconception this table kills: SPDX 3.0 is **not** a 2025 release. The SPDX
team tagged v3.0 in April 2024 and shipped 3.0.1 that December; as of
August 2026 the published spec is 3.0.1 with 3.1 in release-candidate. In
practice 2.x remains the interop default: syft's `spdx-json` output and
spdx-sbom-generator (v2.2) still target the 2.x line.

## Two Document Shapes

SPDX 2.3 and CycloneDX are both document-centric; SPDX 3.0 abandons the
envelope for a flat graph where the "document" is just another node.

```text
SPDX 2.3 (document envelope)
  Doc[ spdxVersion=SPDX-2.3, dataLicense=CC0-1.0, creationInfo{creator, created} ]
   +-- packages[]:      { SPDXID, name, versionInfo, downloadLocation, ... }
   +-- relationships[]: { SPDXRef-DOCUMENT    DESCRIBES   SPDXRef-Package-app }
                        { SPDXRef-Package-app DEPENDS_ON  SPDXRef-Package-lib }
      typed edge rows in ONE array; large relationshipType vocabulary
      (DEPENDS_ON, CONTAINS, BUILD_DEPENDENCY_OF, PATCH_FOR, ...)

SPDX 3.0 (element graph, JSON-LD)
  SpdxDocument(Bom) --rootElement--> Package, File, Relationship, Agent, ...
  every node = Element { spdxId, creationInfo, verifiedUsing[Hash], externalRef }
  profiles: Core + Software / Security / ExpandedLicensing / Build / AI /
            Dataset / Hardware; SPDX Lite annex for constrained producers

CycloneDX 1.5-1.7 (document envelope, stable since 1.0)
  bom{ bomFormat, specVersion, serialNumber=urn:uuid, metadata{timestamp, tools} }
   +-- components[]:   { type, name, bom-ref, purl, version, licenses[] }
   +-- dependencies[]: { ref: "app@2.3.1", dependsOn: ["express@4.18.2"] }
      per-node adjacency lists only; VEX lives in vulnerabilities[]
```

The shape difference drives everything else. SPDX 3.0 gives every Element
uniform `externalIdentifier` / `externalRef` / `verifiedUsing` metadata,
where 2.3 defined these per section; its profile system reaches
multi-domain BOMs (crypto, AI, hardware). CycloneDX reaches the same goal
from the other side - one stable envelope, domain sections and capability
labels (SBOM, HBOM, SaaSBOM, ML-BOM, CBOM, OBOM, MBOM, VDR/VEX, BOV, CDXA,
BOM-Link) - which is why tool support tracks each minor release quickly
while 3.0 ecosystem adoption lags its 2024 spec release.

## Identity: purl Is What Both Sides Agreed On

A purl (`pkg:type/namespace/name@version?qualifiers#subpath`) names exactly
one package in exactly one ecosystem, which is what lets an SBOM row join
against a CVE feed without human guessing. The encodings differ:

| Aspect | SPDX 2.3 | SPDX 3.0 | CycloneDX 1.5-1.7 |
|--------|----------|----------|-------------------|
| purl | `externalRefs[]`: `referenceCategory: PACKAGE-MANAGER`, `referenceType: purl` | first-class `packageUrl` on Package | first-class `purl` on component |
| Other ids | CPE via externalRefs | `externalIdentifier` (CPE, CVE, ...) on any Element | `cpe`, `swid`, `swhid` |
| Local handle | `SPDXID` (`SPDXRef-...`) | `spdxId` (IRI) | `bom-ref` |

## Required vs Optional: What the Specs Mandate

The asymmetry surprises people: CycloneDX mandates almost nothing; SPDX
mandates "unknown" markers.

| Requirement | CycloneDX 1.5-1.7 (JSON schema) | SPDX 2.3 (spec sections 6-7) |
|-------------|---------------------------------|------------------------------|
| Document level | `bomFormat`, `specVersion` - that is all the schema requires | `spdxVersion`, `dataLicense` (fixed `CC0-1.0`), `SPDXID`, `name`, `documentNamespace`, `creationInfo.created`, `creationInfo.creators` |
| Per component/package | `type` + `name` only; version, purl, hashes, licenses optional | `name`, `SPDXID`, `downloadLocation`, `filesAnalyzed`, `licenseConcluded`, `licenseDeclared`, `copyrightText` mandatory; verification code iff `filesAnalyzed` true |
| Unknown values | omit the field | must emit `NOASSERTION` |
| Author/timestamp | optional in `metadata` | mandatory in `creationInfo` |

Interview framing: CycloneDX optimizes for producers and gatekeepers (say
what you know); SPDX 2.3 optimizes for downstream audit (say what you do
not know, explicitly). A 12-line CycloneDX file can be schema-valid and
useless; a minimal SPDX document must already answer who created it, when,
and under what license assertions.

## Relationships: Typed Edges vs Adjacency Lists

SPDX 2.3's `relationships[]` holds typed triples plus the mandatory
`DESCRIBES` edge from document to primary package. SPDX 3.0 keeps
relationships as Elements and adds `lifecycleScope` (design/build/ship) and
`completeness` (complete/incomplete/unknown) - an edge can say "this
dependency statement applies at build time and the list is known to be
incomplete." CycloneDX has one `dependencies[]` section of `{ref,
dependsOn[]}` adjacency entries (plus `provides[]` since 1.6) - no edge
types, deliberately, so reachability tools walk it without a vocabulary
parser.

## Serializations

| Format | Serializations |
|--------|----------------|
| SPDX 2.3 | tag-value, RDF/XML, JSON, YAML, XLSX |
| SPDX 3.0 | JSON-LD (normative, published context), RDF model annex |
| CycloneDX 1.5-1.7 | JSON, XML, Protobuf (`vnd.cyclonedx+json` / `+xml` / `+protobuf`) |

## Vulnerability Export: CycloneDX VEX vs SPDX Security Profile

CycloneDX embeds VEX natively: a `vulnerabilities[]` entry carries `id`,
`ratings`, `affects[]`, and an `analysis` object whose enums are the VEX
contract (verified from the 1.6 JSON schema):

| Field | Allowed values (bom-1.6.schema.json) |
|-------|--------------------------------------|
| `analysis.state` | `resolved`, `resolved_with_pedigree`, `exploitable`, `in_triage`, `false_positive`, `not_affected` |
| `analysis.justification` | `code_not_present`, `code_not_reachable`, `requires_configuration`, `requires_dependency`, `requires_environment`, `protected_by_compiler`, `protected_at_runtime`, `protected_at_perimeter`, `protected_by_mitigating_control` |
| `analysis.response` | `can_not_fix`, `will_not_fix`, `update`, `rollback`, `workaround_available` |

CycloneDX also names two capabilities: VDR (all findings disclosed, drawn
from the SBOM) vs VEX (exploitability statements only). SPDX 2.3 has **no
native vulnerability model** - security data rides as external references.
SPDX 3.0's Security profile makes `Vulnerability` an Element and expresses
the same VEX semantics as graph edges: `VexAffected`, `VexFixed`,
`VexNotAffected` vuln-assessment relationships plus `CvssV2/V3/V4`, `Epss`,
`Ssvc`, and `ExploitCatalog` assessment relationships.

## A Minimal Emitter, Both Formats

One inventory (an app with a transitive chain), two hand-rolled emitters,
and a checklist validating each spec's required fields plus NTIA 2021
minimum-element coverage. Pure stdlib, deterministic:

```python
# Compact: one inventory -> CycloneDX-1.5-style and SPDX-2.3-style JSON.
# Pure stdlib; deterministic (uuid5 + fixed timestamp).
import json
import re
import uuid

CREATED = "2026-08-14T09:30:00Z"
SERIAL = uuid.uuid5(uuid.NAMESPACE_DNS, "payments-api-release-4911")
# name -> (version, license, purl, [direct deps]); payments-api is the app
INV = [("payments-api", "2.3.1", "Apache-2.0", "pkg:npm/payments-api@2.3.1", ["express"]),
       ("express", "4.18.2", "MIT", "pkg:npm/express@4.18.2", ["accepts"]),
       ("accepts", "1.3.8", "MIT", "pkg:npm/accepts@1.3.8", [])]
APP, VER = "payments-api", dict((n, v) for n, v, *_ in INV)


def emit_cdx():
    comps = [{"type": "application" if n == APP else "library",
              "bom-ref": n + "@" + v, "name": n, "version": v, "purl": p,
              "licenses": [{"expression": lic}]} for n, v, lic, p, _ in INV]
    deps = [{"ref": n + "@" + v, "dependsOn": [d + "@" + VER[d] for d in ds]}
            for n, v, _, _, ds in INV]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5",
            "serialNumber": "urn:uuid:%s" % SERIAL, "version": 1,
            "metadata": {"timestamp": CREATED},
            "components": comps, "dependencies": deps}


def emit_spdx():
    pkgs = [{"name": n, "SPDXID": "SPDXRef-Package-" + n, "versionInfo": v,
             "downloadLocation": "NOASSERTION", "filesAnalyzed": False,
             "licenseConcluded": lic, "licenseDeclared": lic,
             "copyrightText": "NOASSERTION",
             "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER",
                               "referenceType": "purl", "referenceLocator": p}]}
            for n, v, lic, p, _ in INV]
    rels = [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
             "relatedSpdxElement": "SPDXRef-Package-" + APP}]
    rels += [{"spdxElementId": "SPDXRef-Package-" + n,
              "relationshipType": "DEPENDS_ON",
              "relatedSpdxElement": "SPDXRef-Package-" + d}
             for n, _, _, _, ds in INV for d in ds]
    return {"spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0",
            "SPDXID": "SPDXRef-DOCUMENT", "name": "payments-api-2.3.1-sbom",
            "documentNamespace": "https://example.com/sbom/%s" % SERIAL,
            "creationInfo": {"created": CREATED,
                             "creators": ["Tool: sbom-emitter-0.1"]},
            "packages": pkgs, "relationships": rels}


def checks(bom, sx):
    ty = [r["relationshipType"] for r in sx["relationships"]]
    yield "CDX top required = bomFormat+specVersion", bom["bomFormat"] == "CycloneDX" and bom["specVersion"]
    yield "CDX component required = type+name", all(c.get("type") and c.get("name") for c in bom["components"])
    yield "CDX serialNumber urn:uuid:<uuid>", bool(re.match(r"^urn:uuid:[0-9a-f-]{36}$", bom["serialNumber"]))
    yield "SPDX doc-level fields (6.1-6.9)", all(sx[k] for k in ("spdxVersion", "dataLicense", "SPDXID", "name", "documentNamespace", "creationInfo"))
    yield "SPDX package mandatory fields (7.1-7.16)", all(p.get(k) is not None for p in sx["packages"] for k in ("name", "SPDXID", "downloadLocation", "licenseConcluded", "licenseDeclared", "copyrightText", "filesAnalyzed"))
    yield "SPDX DESCRIBES x1 + DEPENDS_ON x2", ty.count("DESCRIBES") == 1 and ty.count("DEPENDS_ON") == 2
    yield "purl pkg:npm/<name>@x.y.z on all 3", all(re.match(r"^pkg:npm/[^/]+@\d+\.\d+\.\d+$", c["purl"]) for c in bom["components"])
    yield "NTIA: name+version+unique id per component", all(c["name"] and c["version"] and c.get("purl") for c in bom["components"])
    yield "NTIA: dependency relationships", len(bom["dependencies"]) == 3
    yield "NTIA: SBOM author + timestamp", sx["creationInfo"]["creators"] and sx["creationInfo"]["created"] == CREATED


bom, sx = emit_cdx(), emit_spdx()
for label, ok in checks(bom, sx):
    print("[%s] %s" % ("PASS" if ok else "FAIL", label))
c = json.dumps(bom, indent=2).splitlines()
print("--- CycloneDX 1.5-style (trimmed) ---")
print("\n".join(c[:9]))
print("  ... (%d more lines; %d components, %d dependency entries)"
      % (len(c) - 9, len(bom["components"]), len(bom["dependencies"])))
s = json.dumps(sx, indent=2).splitlines()
print("--- SPDX 2.3-style (trimmed) ---")
print("\n".join(s[:10]))
print("  ... (%d more lines; %d packages, %d relationships)"
      % (len(s) - 10, len(sx["packages"]), len(sx["relationships"])))
```

Real output (uuid5-derived, identical on every run):

```text
[PASS] CDX top required = bomFormat+specVersion
[PASS] CDX component required = type+name
[PASS] CDX serialNumber urn:uuid:<uuid>
[PASS] SPDX doc-level fields (6.1-6.9)
[PASS] SPDX package mandatory fields (7.1-7.16)
[PASS] SPDX DESCRIBES x1 + DEPENDS_ON x2
[PASS] purl pkg:npm/<name>@x.y.z on all 3
[PASS] NTIA: name+version+unique id per component
[PASS] NTIA: dependency relationships
[PASS] NTIA: SBOM author + timestamp
--- CycloneDX 1.5-style (trimmed) ---
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "serialNumber": "urn:uuid:0866702c-4097-53c7-bca3-7bd45ae76b29",
  "version": 1,
  "metadata": {
    "timestamp": "2026-08-14T09:30:00Z"
  },
  "components": [
  ... (56 more lines; 3 components, 3 dependency entries)
--- SPDX 2.3-style (trimmed) ---
{
  "spdxVersion": "SPDX-2.3",
  "dataLicense": "CC0-1.0",
  "SPDXID": "SPDXRef-DOCUMENT",
  "name": "payments-api-2.3.1-sbom",
  "documentNamespace": "https://example.com/sbom/0866702c-4097-53c7-bca3-7bd45ae76b29",
  "creationInfo": {
    "created": "2026-08-14T09:30:00Z",
    "creators": [
      "Tool: sbom-emitter-0.1"
  ... (73 more lines; 3 packages, 3 relationships)
```
The output makes the asymmetry concrete: the SPDX document must say
`NOASSERTION` twice per package and license its own data `CC0-1.0`; the
CycloneDX equivalent omits all of that; both express the same
`app -> express -> accepts` chain - typed `DEPENDS_ON` rows vs adjacency
lists.

## NTIA Minimum Elements: 2021 Baseline, 2026 Update

Executive Order 14028 work produced the NTIA "Minimum Elements" (October
2021) - seven data fields plus practices. The SPDX project's NTIA HOWTO
gives the canonical field mapping:

| NTIA 2021 element | SPDX 2.3 field (section) | CycloneDX 1.5+ field |
|-------------------|--------------------------|----------------------|
| Supplier name | `PackageSupplier` (7.5) | `component.supplier` / `metadata.supplier` |
| Component name | `PackageName` (7.1) | `component.name` |
| Version of the component | `PackageVersion` (7.3) | `component.version` |
| Other unique identifiers | `DocumentNamespace`, `SPDXID` (6.5, 7.2) | `purl`, `bom-ref`, `serialNumber` |
| Dependency relationship | `Relationship` `CONTAINS` (11.1) | `dependencies[].dependsOn` |
| Author of SBOM data | `Creator` (6.8) | `metadata.tools` / `metadata.authors` |
| Timestamp | `Created` (6.9) | `metadata.timestamp` |

What is *not* in the 2021 list: a component hash was only recommended - the
single most-tested trick question in this area. In **July 2026, CISA (with
NSA, FBI, and 14 partner agencies) published the 2026 Minimum Elements**,
replacing the 2021 baseline: component hashes are now mandatory, component
license is a core field, the generating tool must be identified, an "SBOM
context" field records lifecycle stage, and unknown values must be marked
(unknown/redacted/N-A) rather than silently omitted. Terminology shifted
too: "Supplier" became "Software Producer". Know both editions and the
switch date; regulators quote the vocabulary. The SPDX project ships
`ntia-conformance-checker` for validating SPDX documents against the 2021
checklist.

## Tooling: Who Emits What

| Tool | Role | Formats |
|------|------|---------|
| syft (Anchore) | Catalogs container images, filesystems, OCI; converts between SBOM formats | `spdx-json`, `cyclonedx-json`, Syft JSON |
| trivy (Aqua) | Vulnerability scanner that also generates SBOMs from images and lock files | CycloneDX, SPDX |
| spdx-sbom-generator (SPDX project) | Per-package-manager source-tree generator (go, cargo, maven, npm, ...); SPDX v2.2, NTIA-aligned; its README now points generation at trivy + parlay enrichment | SPDX |
| ntia-conformance-checker (SPDX project) | Validates an SPDX document against NTIA minimum elements | SPDX 2.x |

## Decision Table and Generation Point

| Situation | Reach for | Why |
|-----------|-----------|-----|
| License-compliance audit trail | SPDX 2.3 | Mandatory license/copyright fields with NOASSERTION semantics; rich relationship types |
| Runtime scanning, admission control, VEX exchange | CycloneDX | Minimal required fields, first-class VEX states, single adjacency graph, fast tool adoption |
| Government/defense deliverable (US) | Either; NTIA/2026 fields mandatory | Contract names format + minimum elements; check the current edition |
| Multi-domain BOM (crypto, AI models, hardware) | CycloneDX 1.6+ or SPDX 3.0 | CBOM/ML-BOM/HBOM capabilities vs SPDX profiles |
| Greenfield pipeline, no legacy | CycloneDX, keep SPDX export | Lowest emitter burden; convert for compliance consumers |

Where to generate matters as much as which format:

- **Build time (lock files):** cheap and CI-native, captures *intended*
  dependencies - but drifts from the shipped artifact when later layers add
  or strip packages. Deriving the graph from the build tool's own graph is
  the rigorous version; see [Bazel build graphs](./bazel-build-graphs.md).
- **Post-build, at the artifact:** scan the final OCI image and attach the
  SBOM to the digest (OCI referrer) so it travels with the artifact - the
  default syft/trivy deployment, and the only version that answers "what is
  actually in prod?"
- **Deploy time:** admission controllers can require a signature-verified
  attached SBOM before scheduling - the consumption half of the loop,
  pairing with signing as in [Sigstore signing](./sigstore-signing.md).

Trust is the real variable: an SBOM is a claim, not evidence. Attaching it
next to signed provenance makes it one pipeline (see
[SBOM and SLSA](./sbom-slsa.md)); reproducible builds let you re-derive and
check it instead of trusting it, per
[reproducible builds](./reproducible-builds.md).

## References

1. [SPDX Specification 3.0.1](https://spdx.github.io/spdx-spec/v3.0.1/) - element model, profiles, JSON-LD serializations
2. [SPDX 2.3 spec - package information](https://spdx.github.io/spdx-spec/v2.3/package-information/) - mandatory fields and cardinalities
3. [spdx-spec releases](https://github.com/spdx/spdx-spec/releases) - v3.0 Apr 2024, 3.0.1 Dec 2024, v3.1-RC1 Jan 2026, v2.3 Nov 2022
4. [CycloneDX specification overview](https://cyclonedx.org/specification/overview/) - current version 1.7 (2025-10-21), JSON/XML/Protobuf, ECMA-424
5. [CycloneDX 1.6 JSON schema](https://cyclonedx.org/docs/1.6/json/) - required fields, VEX analysis enums
6. [CycloneDX v1.7 release](https://cyclonedx.org/news/cyclonedx-v1.7-released/) and [v1.5 release](https://cyclonedx.org/news/cyclonedx-v1.5-released/) - capability history
7. [NTIA, Minimum Elements For a Software Bill of Materials (2021)](https://www.ntia.gov/report/2021/minimum-elements-software-bill-materials-sbom) - the seven elements
8. [CISA, 2026 Minimum Elements for a Software Bill of Materials](https://www.cisa.gov/resources-tools/resources/2026-minimum-elements-software-bill-materials-sbom) - July 2026 update (cisa.gov returned 403 to curl; verified via search and agency press listings)
9. [SPDX and NTIA Minimum Elements HOWTO](https://spdx.github.io/spdx-ntia-sbom-howto/) - element-to-field mapping; hash-not-mandatory note
10. [package-url/purl-spec](https://github.com/package-url/purl-spec) - purl syntax; [anchore/syft](https://github.com/anchore/syft) and [spdx/spdx-sbom-generator](https://github.com/spdx/spdx-sbom-generator) - emitter tooling
