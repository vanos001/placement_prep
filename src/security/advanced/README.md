# Advanced Security Research — Section L (Topics 991–1060)

## Overview

This section dives into the cutting edge of systems security: the attacks and defenses that operate at the hardware level, the cryptographic primitives that will survive the quantum era, the sandboxing mechanisms that isolate untrusted code, the supply-chain integrity frameworks that ensure trust from source to deployment, and the side-channel countermeasures that make constant-time programming a discipline rather than a suggestion.

These topics separate candidates who can *talk* about security from those who can *reason* about hardware-software co-design for trust. They are high-leverage for FAANG-level security engineering, kernel security, platform security, and applied cryptography roles. Interviewers at Google, Microsoft, Meta, AWS, and cloud-native security companies frequently probe these areas to distinguish candidates who have read the headlines from those who understand the mechanisms.

```mermaid
mindmap
  root((Advanced Security
  Topics 991-1060))
    Microarch Attacks
      Spectre v1-v4, BHB, RSB
      Meltdown, Foreshadow, MDS
      RowHammer / DRAM Attacks
      Cache Side Channels
      Branch Predictor Attacks
      Transient Execution Taxonomy
      SGX / SEV / TDX Attacks
      Confidential Computing
      Trusted / Measured / Secure Boot
      Remote Attestation
    Supply Chain Advanced
      SBOM: SPDX, CycloneDX
      SLSA Levels 1-4
      Reproducible Builds
      Sigstore: Cosign, Fulcio, Rekor
      Software Provenance
      Dependency Confusion
      Typosquatting / Malicious Packages
      CI/CD Pipeline Security
      Secrets Leakage & Rotation
      Workload Identity: SPIFFE/SPIRE
      Zero Trust & Identity-Aware Proxies
      in-toto Attestation
    Sandboxing & Isolation
      seccomp-bpf Filters & Profiles
      SECCOMP_RET_USER_NOTIF
      AppArmor Profiles & Enforcement
      SELinux Policy & Type Transitions
      Landlock: Unprivileged Sandboxing
      Kubernetes Pod Security
      Network Policies
      Container Escape Techniques
      WebAssembly (WASM) Sandbox
      WASI Capability Model
      Browser Site Isolation & Process Model
    Side-Channel Resistant
      Timing: Cache, Branch, Algorithm
      Power: SPA, DPA, CPA
      EM Side Channels & Acoustic
      Fault Injection: Voltage/Clock/Glitch
      Differential Fault Analysis (DFA)
      Constant-Time Programming
      Blinding & Masking Techniques
      CRYSTALS Constant-Time Implementations
    Crypto Advanced
      Post-Quantum: Lattice, Code, Hash
      LWE, SIS, Ring-LWE, Module-LWE
      Zero-Knowledge: SNARKs, STARKs
      Polynomial Commitments: KZG, FRI
      Multi-Party Computation
      Garbled Circuits & Secret Sharing
      Homomorphic Encryption (FHE)
      Searchable Encryption (SSE, PEKS)
      Private Information Retrieval
      Differential Privacy
```

## Reading Order

The files in this section are ordered to build knowledge incrementally. Each file assumes familiarity with the fundamentals listed in the prerequisites column.

| # | File | Prerequisites | Core Focus | Est. Lines |
|---|------|---------------|------------|------------|
| 1 | [Microarchitectural Attacks](microarch-attacks.md) | [Cryptography](../cryptography.md), [Web Security](../web-security.md), basic CPU architecture | Hardware-level data leakage, speculative execution, transient execution, TEE security, confidential computing | ~480 |
| 2 | [Supply Chain Advanced](supply-chain-advanced.md) | [Supply Chain Security](../supply-chain-security.md), [Secrets Management](../secrets-management.md), CI/CD basics | SLSA L3-L4, reproducible builds, Sigstore provenance, dependency confusion, zero trust, SPIFFE/SPIRE | ~470 |
| 3 | [Sandboxing & Isolation](sandboxing.md) | [Authorization](../authorization.md), basic Linux permissions, container fundamentals | Container escapes, LSM hooks, seccomp-bpf, AppArmor, SELinux, Landlock, WASM sandboxing, browser isolation | ~480 |
| 4 | [Side-Channel Resistant Crypto](side-channel-resistant.md) | [Cryptography](../cryptography.md), basic statistics (mean, variance, t-test) | Timing attacks, power analysis, fault injection, constant-time programming discipline, DFA countermeasures | ~460 |
| 5 | [Advanced Cryptography](crypto-advanced.md) | [Cryptography](../cryptography.md), [Post-Quantum](../../cryptography/post-quantum.md), linear algebra basics | Lattice crypto, ZKPs, MPC, FHE, searchable encryption, PIR, differential privacy | ~490 |

## Fundamental vs. Advanced

| Dimension | Fundamentals ([../](../README.md)) | This Section |
|-----------|--------------------------------------|--------------|
| Threat model | Application-level (XSS, SQLi, CSRF) | Hardware-level (Spectre, RowHammer), systemic (supply chain), physical (power analysis) |
| Crypto | AES, RSA, TLS 1.2/1.3 handshakes, HMAC | Lattice-based PQC, ZKPs, MPC, FHE, searchable encryption, PIR |
| Isolation | Process separation, chroot, basic Docker | seccomp-bpf, SELinux type transitions, Landlock, WASM capability model, TEE enclaves |
| Supply chain | Dependency pinning, lock files, npm audit | SLSA L3-L4, reproducible builds, Sigstore, SPIFFE workload identity, in-toto |
| Side channels | Mentioned conceptually, basic timing awareness | Constant-time discipline, DPA/CPA countermeasures, DFA, EM attacks, blinding |
| Boot integrity | Not covered | Secure Boot (UEFI), Measured Boot (TPM), Trusted Boot, remote attestation |
| Network identity | API keys, OAuth tokens | SPIFFE/SPIRE SVIDs, zero trust, identity-aware proxies, workload attestation |

## Learning Paths by Role

Different security roles will prioritize different files in this section. Use the table below to focus your study time based on your target role.

### Platform / Infrastructure Security Engineer
**Priority order**: Microarch Attacks → Sandboxing → Supply Chain → Side-Channel → Crypto Advanced
Focus on hardware mitigations, container escape techniques, seccomp/AppArmor/SELinux policies, and CI/CD hardening. You need to defend production infrastructure.

### Cryptography / Applied Crypto Engineer
**Priority order**: Side-Channel Resistant → Crypto Advanced → Microarch Attacks → Supply Chain → Sandboxing
Focus on constant-time implementation, post-quantum migration, FHE schemes, and ZKP system design. You need to build and verify cryptographic software.

### Cloud-Native / DevSecOps Engineer
**Priority order**: Supply Chain → Sandboxing → Crypto Advanced → Microarch → Side-Channel
Focus on SLSA/Sigstore, Kubernetes security, SPIFFE/SPIRE, and reproducible builds. You need to secure the software delivery pipeline.

### Security Researcher / Red Team
**Priority order**: Microarch Attacks → Side-Channel Resistant → Sandboxing → Crypto Advanced → Supply Chain
Focus on speculative execution exploitation, cache timing, fault injection, and container escape chains. You need to find novel bypasses.

## Cross-References

### Within This Section
- **Microarch ↔ Side-Channel**: [microarch-attacks.md](microarch-attacks.md) covers cache timing attacks (Prime+Probe, Flush+Reload) which are side channels; [side-channel-resistant.md](side-channel-resistant.md) covers countermeasures. Read them as a pair.
- **Sandboxing ↔ Supply Chain**: [sandboxing.md](sandboxing.md) covers runtime isolation; [supply-chain-advanced.md](supply-chain-advanced.md) covers build-time integrity. Defense in depth requires both.
- **Crypto Advanced ↔ Side-Channel**: Post-quantum schemes (ML-KEM, ML-DSA) must be implemented in constant-time. [crypto-advanced.md](crypto-advanced.md) covers the algorithms; [side-channel-resistant.md](side-channel-resistant.md) covers the implementation discipline.

### To Other Sections
- **Cryptography fundamentals**: [../cryptography.md](../cryptography.md) — AES, RSA, ECC, TLS handshake details
- **Post-quantum overview**: [../../cryptography/post-quantum.md](../../cryptography/post-quantum.md) — high-level PQC landscape
- **Supply chain basics**: [../supply-chain-security.md](../supply-chain-security.md) — dependency scanning, lock files, basic SLSA
- **Web security**: [../web-security.md](../web-security.md) — XSS, CSRF, CSP headers
- **Authentication/Authorization**: [../authentication.md](../authentication.md), [../authorization.md](../authorization.md) — OAuth, JWT, RBAC/ABAC
- **Secrets management**: [../secrets-management.md](../secrets-management.md) — Vault, secret rotation, CI secrets
- **Network security**: [../network-security.md](../network-security.md) — TLS, mTLS, network segmentation
- **OS internals**: [../../systems-programming/linux-internals.md](../../systems-programming/linux-internals.md) — kernel, syscalls, namespaces

## Key Tools and Systems Referenced

This section references numerous real-world tools, CVEs, and systems. The tables below serve as a quick reference.

| Category | Tools / Systems |
|----------|----------------|
| CPU Mitigations | KPTI, Retpoline, eIBRS, SSBD, VERW |
| Attestation | Intel SGX Quote, AMD VCEK, Intel TDX Quote |
| Supply Chain | Sigstore (Cosign, Fulcio, Rekor), Syft, Grype, in-toto |
| SBOM | CycloneDX, SPDX, Syft, Trivy, cdxgen |
| Sandboxing | seccomp-bpf, AppArmor, SELinux, Landlock, Firejail |
| Container Security | Podman, Docker, containerd, runc, Kata Containers |
| Workload Identity | SPIFFE/SPIRE, Istio, Cert-Manager |
| Zero Trust | Pomerium, Ory Oathkeeper, BeyondCorp, Cloudflare Access |
| Side-Channel Testing | dudect, Valgrind/Cachegrind, ChipWhisperer |
| PQC Libraries | PQClean, liboqs, pqcrypto, CRYSTALS reference |
| ZK Libraries | libsnark, arkworks, halo2, Plonky2 |
| FHE Libraries | SEAL (Microsoft), HElib (IBM), TFHE, Pyfhel |
| Differential Privacy | OpenDP, Google DP Library, TensorFlow Privacy |

## Interview Angle

Advanced security questions probe whether you understand that security is a *systems* problem. These questions frequently appear in L5+ (Staff+) security engineering loops at FAANG companies and in PhD-level research positions. Expect multi-part questions that require connecting concepts across this entire section:

- "How does Spectre v2 differ from v4, and what are the respective mitigations?"
- "Design a supply-chain integrity system from source to production deployment."
- "How would you sandbox an untrusted WASM module processing user uploads?"
- "Write a constant-time string comparison in C. Why does `strcmp` leak?"
- "What's the difference between zk-SNARKs and zk-STARKs? When would you choose each?"
- "Explain how SEV-SNP prevents a malicious hypervisor from modifying guest memory."
- "You find RowHammer bit flips in your cloud fleet. What's your incident response?"
- "Compare Landlock, seccomp-bpf, and SELinux for isolating a network service."

## Topic Depth by File

Each file in this section covers its topics with a target of 800–2000 words of dense technical content. Below is a summary of the key technical depth markers — if you understand these points, you're ready for interview questions on that topic.

### Microarchitectural Attacks
- Trace a complete Spectre v1 attack: branch mistraining → transient execution → cache side channel → Flush+Reload disclosure
- Explain why KPTI fixes Meltdown but not Spectre (page permissions vs. branch prediction)
- Compare Retpoline, eIBRS, and IBRS: which CPU generations need which mitigation, and the performance costs
- Describe SEV vs. SEV-ES vs. SEV-SNP: confidentiality-only, register encryption, and integrity protection
- Walk through the remote attestation flow for both AMD SEV-SNP and Intel TDX

### Supply Chain Advanced
- Explain the SolarWinds attack chain and why code signing alone did not prevent it
- Compare CycloneDX vs. SPDX SBOM formats and when to use each
- Walk through Sigstore's keyless signing flow: OIDC → Fulcio → Rekor → verification
- Design a dependency confusion prevention strategy for an organization with internal npm packages
- Implement a zero-trust architecture using SPIFFE/SPIRE + OPA + Pomerium

### Sandboxing and Isolation
- Write a seccomp-bpf filter in C that allows only specific syscalls
- Compare AppArmor vs. SELinux: when to choose each, and their policy models
- Explain how Landlock differs from seccomp and why it matters for unprivileged processes
- Walk through CVE-2019-5736 (runc escape) and the fix (memfd_create)
- Design a Kubernetes Pod security context for a multi-tenant cluster (Restricted profile)

### Side-Channel Resistant Crypto
- Write a constant-time Montgomery ladder for RSA in C (with cmov, no branches)
- Explain the DPA attack: how partitioning traces by intermediate value reveals key bytes
- Describe the DFA attack on AES: single-byte fault in round 8, differential analysis
- Explain why `memcmp` leaks and write `ct_memcmp` that does not
- Connect Plundervolt to DFA: how undervolting enables fault injection on SGX enclaves

### Advanced Cryptography
- Explain the LWE problem and why Module-LWE is preferred for ML-KEM/ML-DSA
- Compare zk-SNARK (Groth16, PLONK) vs. zk-STARK: trusted setup, proof size, quantum resistance
- Describe how garbled circuits work: wire labels, truth table encryption, oblivious transfer
- Explain CKKS approximate FHE: encoding, noise growth, and bootstrapping
- Formalize differential privacy: ε, δ, Laplace mechanism, composition theorem

## How to Study This Section

1. **Read in order** the first time through. Each file builds on concepts from the previous one.
2. **Practice with code**: Many files include C, Rust, and assembly snippets. Type them out, compile them, and experiment. For constant-time code, use `dudect` to verify your implementation.
3. **Trace attack chains**: For each CVE described, walk through the attack step-by-step. Understand *why* it works — what hardware/software mechanism is exploited, and what property makes the attack possible.
4. **Build comparison tables**: Memorize the comparison tables. Being able to articulate trade-offs (SNARK vs STARK, SELinux vs AppArmor, SEV-SNP vs TDX, Prime+Probe vs Flush+Reload) is a key interview skill. Interviewers frequently ask "compare X and Y."
5. **Connect the dots**: The best interview answers connect concepts across files (e.g., "Spectre is a cache timing attack → use constant-time design principles → but even constant-time code leaks on speculative hardware → thus we need hardware mitigations like eIBRS"). Cross-file connections demonstrate systems-level thinking.
6. **Build mental models**: For each defense mechanism, understand what it protects against, what it doesn't, and the performance cost. This enables rapid design of defense-in-depth solutions.
7. **Stay current**: Many of these topics are actively evolving (PQC migration, FHE performance, new CVEs). Follow the reference links and read new papers as they appear.
