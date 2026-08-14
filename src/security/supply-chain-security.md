# Software Supply Chain Security

## Overview

Software supply chain attacks target the dependencies, build pipelines, and distribution mechanisms of software rather than the application code itself. The SolarWinds breach (2020) demonstrated that compromising the build process can silently backdoor thousands of downstream organizations.

## Attack Vectors

| Vector | Description | Example |
--------|-------------|--------|
| **Dependency confusion** | Internal package name registered on public registry | `company-utils` on npm, resolved over private registry |
| **Typosquatting** | Packages with names similar to popular ones | `lod-ash` instead of `lodash` |
| **Account takeover** | Compromised maintainer account publishes malicious release | `ua-parser-js` (2021), `event-stream` (2018) |
| **Build compromise** | Tampered CI/CD pipeline injects backdoor | SolarWinds SUNBURST |
| **Malicious PRs** | Contributor submits code that looks benign but contains a backdoor | `xz-utils` backdoor (2024) |

## Package Manager Security

### Lockfiles and Integrity

```bash
# npm — always commit package-lock.json
npm ci  # install from lockfile, fail if mismatch

# Use --ignore-scripts to prevent postinstall attacks
npm install --ignore-scripts

# Python — pin hashes in requirements.txt
pip install --require-hashes -r requirements.txt

# Go — verify checksums
GONOSUMCHECK=none go mod verify
```

### Dependency Scanning

| Tool | Language | Function |
------|----------|----------|
| `npm audit` | JS | Check known CVEs in dependencies |
| `pip-audit` | Python | Audit Python dependencies |
| `trivy` | Multi | Container + dependency scanning |
| `osv-scanner` | Multi | Google's OSV database scanner |
| `Dependabot` | Multi | Automated PR-based updates |

## SLSA and Sigstore

**SLSA** (Supply-chain Levels for Software Artifacts) defines four levels of supply chain integrity:

| Level | Requirement | Protection |
-------|-------------|------------|
| L1 | Documented build process | Provenance exists |
| L2 | Hosted build platform | Authentic provenance |
| L3 | Hardened build platform | Non-falsifiable provenance |
| L4 | Hermetic + reproducible builds | Maximum guarantee |

**Sigstore** provides code signing infrastructure: `cosign` signs container images, `fulcio` issues certificates keyed to OIDC identity, `rekor` provides a transparent tamper-evident log.

## SBOM (Software Bill of Materials)

An SBOM is a machine-readable inventory of all components in a software artifact.

```json
{
  "bomFormat": "CycloneDX",
  "components": [
    {"name": "express", "version": "4.18.2", "purl": "pkg:npm/express@4.18.2"},
    {"name": "lodash", "version": "4.17.21", "purl": "pkg:npm/lodash@4.17.21"}
  ]
}
```

Formats: **CycloneDX**, **SPDX**. Required by US executive order 14028 for software sold to the government.

## Interview Questions

**Q: What is a dependency confusion attack?**
A: An attacker publishes a package with the same name as a company's internal package on a public registry. If the build system resolves public packages first (or with lower specificity), it installs the malicious public package instead of the private one.

**Q: How would you secure your CI/CD pipeline against supply chain attacks?**
A: Pin dependency versions with lockfiles, use SLSA L3+ build platforms, sign artifacts with Sigstore/cosign, generate SBOMs, scan for known vulnerabilities, restrict postinstall scripts, and implement code review requirements for dependency updates.

## References

- [SLSA Specification](https://slsa.dev/spec/v1.0/)
- [Sigstore](https://www.sigstore.dev/)
- [CycloneDX SBOM Standard](https://cyclonedx.org/)
- [OpenSSF Scorecard](https://securityscorecards.dev/)
- See also: [Web Security](./web-security.md), [Secrets Management](./secrets-management.md), [Interview Questions](./interview-questions.md)
