# Build Systems & Software Supply Chain

## Chapter Overview

Build systems and supply chain security form the foundation of reliable, reproducible software delivery. As attacks on the software supply chain have grown dramatically—from SolarWinds to Log4j—organizations are investing heavily in build reproducibility, artifact provenance, and dependency management. This section covers both the engineering of build systems and the security of the software supply chain.

| Chapter | Title | Core Focus |
|---------|-------|------------|
| [Build Systems](build-systems.md) | Reproducible & Hermetic Builds | Bazel, Buck2, Nix, remote execution, caching, dependency graphs |
| [Software Supply Chain](software-supply-chain.md) | SBOM, SLSA, Provenance | Artifact signing, SLSA framework, SCA, secure CI/CD, OCI artifacts |

## Why This Matters for Interviews

Build systems and supply chain security are increasingly tested in:

- **Platform/infrastructure roles** — designing CI/CD pipelines, build infrastructure
- **Security engineering** — supply chain threat modeling, vulnerability management
- **Developer tooling** — build tool design, dependency management
- **Staff+ roles** — organizational decisions about build systems, security investment

Expect questions about how to ensure build reproducibility, how to manage dependencies securely, and how to design CI/CD pipelines that resist supply chain attacks.

## Key Themes

1. **Reproducibility** — bit-for-bit identical builds from the same source
2. **Hermeticity** — builds are isolated from the host environment
3. **Provenance** — knowing exactly what went into a build artifact
4. **Verification** — establishing trust chains from source to deployment
