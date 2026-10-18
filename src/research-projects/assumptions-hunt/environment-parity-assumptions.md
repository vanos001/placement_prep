# Environment Parity Assumptions: What "Works on My Machine" Silently Promises

## Overview

"Works on my machine" is not a joke; it is a parity claim. It asserts that the developer laptop, the CI runner, the staging cluster, and production are the same environment wearing different hostnames. That claim rests on assumptions nobody wrote down: that the filesystem behaves identically everywhere, that default tools and locales match, that versions of everything outside the lockfile are pinned, and that the local topology at least resembles production. Each assumption fails quietly and specifically — a module resolves on a case-insensitive laptop and vanishes in a Linux container, a shell script that runs for years starts dying the day CI moved to a leaner image, a build that passed yesterday fails today because a floating base image moved underneath it.

The deeper pattern is that *an environment is a contract, not a machine*: operating system, libc lineage, filesystem semantics, shell, locale, time zone, resource limits, and the versions of every transitive system dependency — none of which appear in an application lockfile. Parity is therefore transitive-dependency management at the operating-system layer, and it decays on its own because every environment drifts independently. This chapter audits the four assumptions above in the collection's five-step pattern. It complements the sibling [configuration assumptions](configuration-assumptions.md) chapter, which audits the config surface itself; this one audits the ground that surface stands on.

## Assumption 1: "The Filesystem Behaves the Same Everywhere"

### The taught rule

A file path is a file path. `src/App.js` names a file; if it exists on one machine it exists on all machines, and the build is portable.

### The hidden assumptions

- The rule assumes the *same case semantics*: macOS volumes (APFS and older HFS+) are case-insensitive by default, Linux ext4 volumes are case-sensitive, and NTFS is case-preserving but compares case-insensitively. A repository that contains both `App.js` and `app.js` — or an import spelled with the wrong case that still resolves on the laptop — behaves differently the moment it lands on Linux.
- It assumes the *same case-conflict behavior*: on the laptop, creating `readme.md` when `README.md` exists silently opens or replaces the same file; on Linux it creates a second file, and a checkout that was "clean" for years can fail mid-clone with a collision.
- It assumes the *same metadata travels with the code*: the executable bit. A script committed without the bit runs when invoked through an interpreter during development and fails with `Permission denied` in CI, where it is invoked directly.
- It assumes the *same path separators and device quirks*: code written against `/` breaks on Windows shells, and drive-letter or UNC paths leak into config files that later fail on Unix.

### Counterexample

A web repository holds 240 source files, including `utils/Formatters.js`, imported in 40 places as `utils/formatters.js`. Development happens on macOS: every import resolves, because the case-insensitive volume folds the two names together. The Docker build runs on Linux: 40 imports now resolve to nothing, and the build fails with "Module not found" in a code path untouched by the change under review. The bug was committed months earlier; only the environment change made it visible. The standard defense is to make the development environment match the target — develop and test inside the same container image that production runs, or at minimum enable case-sensitive volumes for repos that deploy to Linux — plus a CI gate that runs the build on the production OS family, since only a case-sensitive filesystem can even express this class of failure.

### What changes when the assumption is removed

Corrected statement: *filesystem semantics — case handling, metadata, separators, name normalization — are part of the deployment target, and any build or test result produced on a different filesystem is evidence about that different environment, not about production.* Practically: pin the development and CI filesystem family to the production family; treat "works locally, fails in CI" on a case-mismatch as a parity bug with a known cause rather than a flaky test; and audit imports and paths with a case-sensitive checker regardless of where developers work.

### Consequences

In interviews, "why do monorepos deploy to Linux and develop on Macs keep hitting case bugs?" is a probe for the answer above: the laptop was silently rewriting the program's file graph. In code review, an import with mismatched case that passes local tests is a defect even before CI catches it.

## Assumption 2: "Default Tools and Locales Match"

### The taught rule

Shell scripts and data processing run anywhere: `sh script.sh`, `sort`, `date`, and number parsing are portable utilities with stable behavior.

### The hidden assumptions

- It assumes `/bin/sh` is the same shell everywhere. Debian and Ubuntu have pointed `/bin/sh` at dash for years (Ubuntu since 6.10 in 2006, documented on the [Debian wiki](https://wiki.debian.org/Shell)); dash implements POSIX sh, so bashisms — `source` instead of `.`, `==` inside `[ ]`, arrays, `local` quirks — fail at runtime on one machine and run on another. The script's shebang says `#!/bin/sh`; the developer's laptop has bash installed as `/bin/sh` or ignores the shebang.
- It assumes locale-independent ordering and parsing. `sort` under `LC_ALL=C` orders by byte value; under `en_US.UTF-8` it ignores case and punctuation, so two environments produce two different "sorted" outputs — which matters whenever the sort feeds a diff, a merge, or a deterministic artifact. Numeric parsing inverts the trap: `1,234.56` parsed under a German locale reads as 1.23456.
- It assumes default locale and time-zone variables exist and agree. A container with no `LANG` and `TZ=UTC` parses, formats, and sorts differently than the developer shell that has both set — the failure looks like a data bug, not a config bug (the time-zone half of this is the sibling [clocks-and-time](clocks-and-time.md) chapter's subject; here the audit is that the *default* is environment-dependent at all).
- It assumes the same auxiliary tools exist: `jq`, `make`, `git` version, `sed` (GNU vs BSD dialects differ in `-i` and character classes), installed at different versions or not at all.

### Counterexample

A release script uses `[[ $ver == v* ]]`, arrays, and `source ./lib.sh`, and has run successfully for two years on development laptops and an old CI image that linked `sh` to bash. The platform team migrates CI to a minimal Debian image where `/bin/sh` is dash; the script now dies on line 3 with `Syntax error: "(" unexpected`. Nothing in the repository changed; the interpreter changed. The corrected practice: declare the interpreter explicitly (`#!/usr/bin/env bash` when bash is meant), lint shell with a dialect checker in CI, and pin `LC_ALL=C` (or an explicit locale) plus `TZ` in every script and job that orders, parses, or formats data.

### What changes when the assumption is removed

Corrected statement: *default behavior of `sh`, `sort`, parsing, and formatting is an environment variable — in both senses — and portable scripts name their interpreter and their locale explicitly instead of inheriting the ambient one.* A team that writes "this script requires bash ≥ 4 and LC_ALL=C" into the script header has converted an unstated parity assumption into a checkable contract.

### Consequences

The interview probe "why did your pipeline break after switching CI images?" has a compact senior answer: the environment is part of the program, minimal images change `/bin/sh` and drop tools, and the fix is explicit interpreters, explicit locales, and pinned tool versions in the image.

## Assumption 3: "Versions Are Pinned Because the Lockfile Exists"

### The taught rule

Dependency management is solved: `package-lock.json` (or equivalents) pins every version, so building today and building in six months produce the same artifact.

### The hidden assumptions

- The lockfile pins *application* packages, not the *environment*: the runtime version, the base image, the system libraries, the crypto stack underneath everything. Any of those can drift while the lockfile never changes.
- "Pinned" tags are frequently floating: `FROM node:latest`, `FROM python:3`, or an unpinned action reference re-resolves at every build, so two builds of the same commit use different environments, and the difference surfaces only when the base moved far enough.
- The environment has its own dependency graph with its own breaking changes. Node.js 17 shipped OpenSSL 3.0 (the [release notes](https://nodejs.org/en/blog/release/v17.0.0) document the upgrade), and the legacy crypto primitives some toolchains referenced were removed — builds that ran on Node 16 began failing on Node 17 with `ERR_OSSL_EVP_UNSUPPORTED` despite a byte-identical repository.
- Translations of "same version" differ per language: a Python interpreter pinned to 3.11 still varies with the patch release, the OS SSL library it links, and the wheel availability per platform; a "pinned" Alpine image swaps libc (glibc vs musl) entirely versus a Debian image.

### Counterexample

A build pipeline pins application dependencies exactly and builds `FROM node:latest`. In May 2021 the image resolves to Node 16 and the build succeeds; in October 2021 the same commit resolves to Node 17, which ships OpenSSL 3.0, and the content-hash step fails with `ERR_OSSL_EVP_UNSUPPORTED` at the same line every time. The repository's lockfile is untouched between the passing and failing runs, proving it was never the actual contract. The corrected practice: pin the full lineage — base image by digest (`FROM node:16.20.2-bullseye@sha256:...`), runtime version in CI matrices, and the crypto stack that ships with it — and reproduce builds from that digest rather than from a tag someone may move.

### What changes when the assumption is removed

Corrected statement: *a lockfile pins one layer; the environment is a stack of layers (base image, runtime, system libraries, crypto, tools), and reproducibility requires pinning every layer the build can see, by digest rather than by mutable tag.* The audit question for any "it just started failing" build is: which layer changed underneath the code? — answered by diffing image digests and runtime versions, not the application lockfile.

### Consequences

The interview follow-up "the lockfile is identical on two machines, can the builds still differ?" is exactly this assumption: yes — via base image drift, runtime differences, and system-library lineage. The production discipline this maps to is digest-pinned images and reproducible-build tooling, the same levers the [build-caches and reproducibility](../connection-atlas/build-caches-reproducibility.md) atlas page develops.

## Assumption 4: "Dev Topology Approximates Production"

### The taught rule

Developers run one process locally, CI runs the test suite, and the differences between that world and production are scale, not kind — so green local runs predict production behavior.

### The hidden assumptions

- *Resource limits are part of the environment.* A laptop has 32 GB of RAM, no CPU quota, and a high file-descriptor ceiling; the container in production may have 512 MiB, one CPU of quota, and a 1,024-descriptor soft limit. Code that opens a connection per request passes locally and dies with `too many open files` around the 1,021st concurrent socket in production. The sibling [containers and resources](containers-and-resources.md) chapter audits the quota mechanics; the parity failure is assuming the limits differ only by headroom.
- *Data shape parity is assumed but rarely built.* Local development runs against a database with six months of handcrafted rows; CI's empty database skips every migration-ordering bug; a query that returns in 40 ms on 50,000 rows returns in 9 s on 50,000,000 because an index was never needed locally.
- *The service graph is flattened.* Locally, one process reaches everything; in production, six services sit behind a mesh, and the connection-pool, timeout, and retry settings that are no-ops with N=1 become load multipliers with N=40. The compose-versus-Kubernetes gap — running the full graph in a single VM versus a scheduler with its own networking — is audited as a mechanism choice in [docker-compose-vs-kubernetes](../why-not-handbook/docker-compose-vs-kubernetes.md); here the audit is the belief that the flattened graph is a valid proxy.
- *Failure injection is absent locally:* nothing times out, no cert rotates mid-run, no registry returns stale data — so the code paths that production exercises most are the ones local testing exercises least, which is why progressive-delivery stages (the [canary versus blue-green](../why-not-handbook/canary-vs-blue-green.md) comparison) exist as parity instruments rather than just rollout tools.

### Counterexample

A notification service runs fine locally and in CI. Its first production week shows `too many open files` under load: developers each see at most a handful of concurrent requests on machines with a 1M-descriptor limit, while the container carries a 1,024 soft limit and opens one socket plus one file handle per queued message. At 1,021 concurrent handles the open fails, the error handler logs it, and the backlog keeps growing. The fix has two halves — a bounded handle pool in code, and parity instrumentation in dev: run the same `ulimit -n`, the same memory limit, and the same concurrency shape as production so the ceiling is met in rehearsal, not on call.

### What changes when the assumption is removed

Corrected statement: *topology, limits, and data volume are dimensions of the environment as real as its OS, and "parity" means matching the constraint set (limits, concurrency shape, data scale, failure injection), not merely running the same binary.* A practical ladder: identical images (Assumption 1's rule), identical limits and locale, then progressively production-shaped data and topology — with the acceptance criterion that every environment-specific limit has been hit at least once before the code reaches production.

### Consequences

In system-design interviews, "how would you catch environment-specific failures before launch?" separates candidates who name the dimensions (filesystem, locale, versions, limits, topology, data) from candidates who repeat "staging": staging only helps if it shares the constraint set, and the cheapest instrument is running the production image under production limits in CI.

## Interview Questions

1. **A build passes on every laptop and fails only in the Linux CI container with "Module not found". Diagnose it.** A case-sensitivity mismatch: the macOS volume folds `Formatters.js` and `formatters.js` together; ext4 does not. The fix is to correct the imports, enable case-sensitive volumes for the target-family repos, and run the build on the production OS family so the failure class is expressible where the tests run.
2. **Why can two builds of the same commit with identical lockfiles differ?** The lockfile pins only the application layer. Base images by mutable tag, runtime minor upgrades, system libraries, and the crypto stack (Node 17's OpenSSL 3.0 removing legacy digests) all drift independently; reproducibility needs digest-pinned images and pinned runtime/tool versions.
3. **A shell script breaks only on the new minimal CI image. What most likely changed, and what is the durable fix?** `/bin/sh` now points to dash instead of bash, so bashisms fail. Fix: declare `#!/usr/bin/env bash` (or port to POSIX sh), lint the dialect, and pin tool versions and locale in the image so the contract is explicit.
4. **Name three environment dimensions that a test suite cannot see but production always enforces.** Resource limits (file descriptors, memory quota, CPU quota), default locale and time zone, and data volume/shape — plus failure injection and the real service topology. Each needs a deliberate parity instrument, because none appear in the code or the lockfile.

## Key Takeaways

- "Works on my machine" is a parity claim about an unstated contract: filesystem semantics, shell and tools, locale and time zone, the full version stack, resource limits, topology, and data shape.
- The lockfile pins one layer of many; base-image tags are floating, runtimes upgrade under them, and digest pinning is the only stable reference.
- Case-insensitive development volumes rewrite the program's file graph; only a production-family filesystem can express that failure class, so the build must run where production runs.
- Defaults are environment variables: `/bin/sh`, `sort` order, number parsing, and time zone all inherit ambient configuration, so portable scripts declare interpreter and locale explicitly.
- Parity decays automatically because every environment drifts independently; the defense is not one cleanup but instruments — same-image CI, limit-parity rehearsal, digest pinning — that re-check the contract continuously.

## Cross-References

- [Configuration assumptions](configuration-assumptions.md) — the config surface (defaults, flags, per-environment drift) that sits on top of the parity ground audited here.
- [Testing assumptions](testing-assumptions.md) — "passing tests imply correctness" assumes the test environment shares production's constraint set, the assumption this chapter breaks.
- [Containers and resources](containers-and-resources.md) — the quota mechanics (CPU, memory, file descriptors) behind the topology-parity failures above.
- [Clocks and time](clocks-and-time.md) — the time-zone and clock defaults that environments silently supply, audited from the timing side.
- [Why-not: canary vs blue-green](../why-not-handbook/canary-vs-blue-green.md) — progressive delivery as a parity instrument: production-shaped rehearsal before full traffic.
- [Why-not: docker-compose vs Kubernetes](../why-not-handbook/docker-compose-vs-kubernetes.md) — the flattened local service graph versus scheduler-managed topology, the mechanism choice behind Assumption 4.
- [Connection atlas: build caches and reproducibility](../connection-atlas/build-caches-reproducibility.md) — digest pinning and reproducible builds as the enforcement layer for Assumption 3.
- The [Debian wiki Shell page](https://wiki.debian.org/Shell) (dash as `/bin/sh`) and the [Node.js 17 release notes](https://nodejs.org/en/blog/release/v17.0.0) (OpenSSL 3.0 upgrade) are the primary sources for the tool-version claims above; both were fetched and verified this session.
