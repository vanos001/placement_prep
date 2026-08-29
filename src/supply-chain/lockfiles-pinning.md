# Lockfiles and Dependency Pinning

A manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`)
is a *request*: it declares ranges and lets the resolver pick concrete versions
at install time. A lockfile is the *receipt*: a machine-written record of which
artifacts that resolution produced, so every later install reproduces the same
tree instead of re-negotiating it against a moving registry. This page covers
the defense mechanics; the offense -- in-range bait that range resolvers
happily pick up -- is dissected in [Dependency Confusion](dependency-confusion.md),
whose punchline: pinning stops *drift*, not *first contact*.

## What a Lockfile Actually Records

Two properties separate lockfiles from "a file that lists versions": it
covers **the whole transitive tree** (the install graph is hundreds of
packages deep; none of the transitive nodes appear in any manifest, yet each
is a resolution decision that changes between builds if re-derived), and it
carries **per-artifact integrity**, so pinned *content* -- not just pinned
*version* -- is what gets installed.

```text
manifest (ranges)                lockfile (receipt)
+----------------------+  resolve   |http-kit  2.3.1  sha512-AAAA...      |
| "http-kit": "^2.3.0" |  ------->  |mini-log  1.1.0  sha512-BBBB...      |
| "json-fast": "^0.8.2"|  once,     |json-fast 0.8.2  sha512-CCCC...      |
|                      |  commit    |(every transitive node: version,     |
+----------------------+            | integrity, source)                  |
  re-resolve later = new tree;  install from lock = same tree
```

npm's `package-lock.json` documents `integrity` as "a sha512 or sha1 Standard
Subresource Integrity string for the artifact that was unpacked in this
location", and its `lockfileVersion` semantics are explicit in the npm docs:
1 = npm 5/6, 2 = npm 7/8 (backwards compatible with 1), 3 = npm 9 and later
(backwards compatible with 7). Why the whole tree? Resolution depends on
registry state at resolution time: the demo at the bottom runs a toy resolver
twice against the same manifest and gets two different trees, because between
the two dates the registry gained an in-range version of a transitive
dependency. Only the lockfile makes that a non-event.

## One Problem, Six Formats

| Ecosystem | File | What it records | CI-side guard |
|-----------|------|-----------------|---------------|
| npm | `package-lock.json` | Full resolved tree, SRI integrity per package | `npm ci` |
| Rust / Cargo | `Cargo.lock` | Exact versions + checksums, machine-written | `cargo build --locked` |
| Python (Pipenv) | `Pipfile.lock` | Exact versions + per-version hashes | `pipenv install --deploy` |
| Python (Poetry) | `poetry.lock` | Resolved versions, machine-written | `poetry install --sync` |
| Ruby (Bundler) | `Gemfile.lock` | Resolved specs for the bundle | deployment mode |
| Gradle | `gradle.lockfile` | Locked versions per configuration | strict lock mode |
| Go | `go.mod` + `go.sum` | MVS requirements + content hashes | `-mod=readonly` (default) |

Notes the table cannot carry:

- **Cargo splits authorship explicitly.** The Cargo book: `Cargo.toml`
  "describes dependencies in a broad sense, and is written by you";
  `Cargo.lock` "contains exact information about your dependencies", is
  "maintained by Cargo and should not be manually edited", and "when in
  doubt, check Cargo.lock into the version control system". For published
  *libraries* the file is advisory: the Cargo FAQ is candid that `Cargo.lock`
  "does not affect the consumers of your package" -- they resolve their own
  tree, so the guarantee is for the project's own CI and collaborators.
- **Python is split-brained.** Pipenv's `--deploy` will "Abort if Pipfile.lock
  is out-of-date". Plain pip has no lockfile; the substitute is hash-checking
  mode (`--require-hashes`), where every requirement must be pinned *and*
  hashed -- pip's docs are blunt: "By default, pip does not perform any
  checks to protect against remote tampering". Poetry writes `poetry.lock`,
  expects it committed, and `poetry install --sync` synchronizes the
  environment "with the locked packages and the specified groups". Bundler
  requires `Gemfile.lock` for deployment-mode installs and errors when the
  `Gemfile` changes underneath a locked bundle.
- **Gradle locks per configuration.** Lock state lands in `gradle.lockfile`
  at the root of each project; `--update-locks` bumps selected entries on
  purpose. Lenient mode still pins dynamic versions but treats other
  resolution changes as non-errors; strict mode turns drift into a failure.

## Go: No Lockfile, On Purpose

Go is the outlier, deliberately: no `go.lock`. `go.mod` records requirements
(including `// indirect` ones), `go.sum` records content hashes, and the
resolution algorithm itself is deterministic, so a lockfile would be
redundant for reproducibility.

- **MVS -- Minimal Version Selection.** Go picks the highest of the
  *required* versions in the module graph and nothing newer -- never
  "latest". The result is a pure function of the requirement sets, not of
  registry timing. (Mechanics and `go mod tidy` are detailed in
  [Go Modules & Interfaces](../languages/go/modules-interfaces.md).)
- **`go.sum` is verification, not resolution.** Lines are
  `module-path version h1:<hash>` (plus `/go.mod` lines for module metadata).
  Per the module reference, all module-aware commands "verify that hashes in
  the main module's go.sum file match hashes recorded for modules downloaded
  into the module cache"; a missing hash is checked against the checksum
  database unless the module matches `GOPRIVATE`/`GONOSUMDB`. The default
  database is `sum.golang.org`, operated by Google.
- **The gate is read-only by default.** Since Go 1.16 the go command behaves
  as if `-mod=readonly` were set: a build needing to edit `go.mod`/`go.sum`
  fails until `go mod tidy` runs and the change is committed.

Other ecosystems freeze a resolved *tree*; Go freezes *requirements plus
hashes* and resolves deterministically at build time. Both end reproducible,
but Go shifts trust from "the file lists correct versions" to "the algorithm
plus the checksum database is honest" -- which is why Go supply-chain attacks
concentrate on getting a bad version *required* and a bad hash into `go.sum`
in the same commit.

## Ranges Versus Exact Pins

The SemVer spec defines the version grammar and precedence; `^` and `~` are
resolver conventions layered on top. npm's caret deserves precise memory:
`^1.1.0` admits `>=1.1.0 <2.0.0`, but zero-major narrows -- `^0.8.2` admits
only `<0.9.0`, and `^0.0.3` only `<0.0.4` -- because a zero major means the
API itself is unstable.

| Choice | Upside | Cost |
|--------|--------|------|
| Ranges in manifest + committed lockfile | Recipients get your tested tree; upgrades are explicit `npm update`/`cargo update` diffs | Lockfile churn in PRs; CI discipline required |
| Exact pins everywhere in the manifest | Zero ambiguity even without a lockfile | Upgrades become manual edits; stale-pin risk replaces drift |
| Ranges, no lockfile | Smallest repo state | Every install re-resolves; builds reproduce nothing; in-range bait wins |

The working consensus: keep ranges in the manifest, commit the lockfile, and
treat any change to it as the only route by which dependency versions move.
Renovate's dedicated `lockFileMaintenance` configuration and Dependabot
version updates both produce PRs that are, structurally, lockfile diffs -- a
plausible version bump arriving with a new source URL is exactly the review
surface [Dependency Confusion](dependency-confusion.md) recommends defending.

## Frozen Modes in CI

A committed lockfile is only a pin if CI's install is forbidden from rewriting
it; each tool has a loud-failure mode, and it should be the default. `npm ci`
requires an existing `package-lock.json`, errors if it disagrees with
`package.json`, and "will exit with an error, instead of updating the package
lock". `cargo build --locked` "asserts that the exact same dependencies and
versions are used as when the existing Cargo.lock file was originally
created"; `--frozen` is exactly `--locked` plus `--offline`. pip's
`--require-hashes` refuses unpinned or unhashed requirements; `pipenv
install --deploy` aborts on an out-of-date lock; Bundler deployment mode
fails when `Gemfile` and `Gemfile.lock` disagree; Gradle strict lock mode
fails on unlocked drift; Go's `-mod=readonly` default fails a build that
would mutate `go.mod` or `go.sum`.

These modes enforce *internal consistency*, not *trustworthiness*: a lockfile
whose bad entry was committed in a hasty or malicious PR passes every frozen
check.

## Monorepo Nuances

- **npm/pnpm workspaces**: one root lockfile -- consistent, but every team's
  upgrades collide in the same file, so conflict rates are high.
- **Cargo workspaces**: a single `Cargo.lock` at the workspace root; a
  member crate's new dependency changes everyone's lockfile.
- **Gradle**: lock state per subproject, trading one source of truth for
  smaller diffs.
- **Go**: verification is per module, and the workspace file `go.work` is
  explicitly not for committing -- the module reference calls it "generally
  inadvisable" to check in, since it overrides developers' environments.

## Auditing the Locked Tree

The lockfile is also the audit input, which is why scanners read it rather
than manifests: `npm audit` checks the tree as recorded in `package-lock.json`
against the npm advisory database; `cargo-audit` reads `Cargo.lock` and
matches crates against the RustSec Advisory Database; `osv-scanner` consumes
lockfiles and SBOMs and matches them against the cross-ecosystem OSV database.
Advisory audit is point-in-time and version-based. The [Artifact Registries](artifact-registries.md)
layer adds digest immutability, and [SBOM and SLSA](sbom-slsa.md) adds the
next step: SLSA provenance attests what the build *actually consumed*, closing
the gap between "the lockfile says so" and "the builder did so". A
[Reproducible and Hermetic Builds](reproducible-builds.md) pipeline is the end
state a lockfile only approximates: pins fix inputs' *identity*, not the
build's *execution*.

## Worked Model: Registry Drift vs Pinned Tree

A stdlib-only model: the registry is a dict of published versions with publish
dates; `^` implements npm caret semantics including zero-major narrowing. One
pass resolves a manifest on day 20 and day 80 with ranges only; a second
installs from a lockfile frozen on day 20, then re-checks integrity after a
same-version registry tamper.

```python
#!/usr/bin/env python3
"""Toy resolver: range resolution drifts with the registry; a lockfile pins
the tree, and integrity digests catch same-version tamper."""
import hashlib

def semver(v): return tuple(int(x) for x in v.split("."))
def digest(name, version, body):
    return hashlib.sha256(f"{name}@{version}:{body}".encode()).hexdigest()[:16]

# name -> version -> (publish_day, deps, artifact-body)
REGISTRY = {
    "http-kit": {"2.3.1": (10, {"mini-log": "^1.1.0"}, "body-A1"),
                 "2.4.0": (40, {"mini-log": "^1.2.0"}, "body-A2")},
    "mini-log": {"1.1.0": (5, {}, "body-C1"), "1.2.0": (50, {}, "body-C2"),
                 "1.9.9": (70, {}, "body-BAIT")},  # bait, still inside ^1.1.0
    "json-fast": {"0.8.2": (12, {}, "body-D1"), "0.8.3": (60, {}, "body-D2")},
}

def satisfies(rng, version):  # npm caret: ^1.1.0 <2.0.0 | ^0.8.2 <0.9.0 | ^0.0.3 <0.0.4
    a, b, c = semver(rng[1:])
    top = (a + 1, 0, 0) if a > 0 else (0, b + 1, 0) if b > 0 else (0, 0, c + 1)
    return semver(rng[1:]) <= semver(version) < top

def resolve_range(root_deps, day):
    tree, order = {}, []
    def rec(name, rng):
        if name in tree: return
        cands = [v for v, (d, _, _) in REGISTRY[name].items()
                 if d <= day and satisfies(rng, v)]
        assert cands, f"no satisfying {name}@{rng} on day {day}"
        tree[name] = max(cands, key=semver)
        order.append(name)
        for dep, drng in REGISTRY[name][tree[name]][1].items(): rec(dep, drng)
    for n, r in root_deps.items(): rec(n, r)
    return tree, order

def install_lock(lock):
    return [(n, v, p, digest(n, v, REGISTRY[n][v][2])) for n, (v, p) in sorted(lock.items())]

MANIFEST = {"http-kit": "^2.3.0", "json-fast": "^0.8.2"}
print("== resolve from manifest (ranges) on day 20 ==")
t1, order1 = resolve_range(MANIFEST, 20)
for n in order1: print(f"  {n}@{t1[n]}")
print("== resolve the SAME manifest on day 80 ==")
t2, order2 = resolve_range(MANIFEST, 80)
for n in order2: print(f"  {n}@{t2[n]}")
print(f"  trees differ: {t1 != t2}  day-80 picks: "
      f"http-kit@{t2['http-kit']}, mini-log@{t2['mini-log']}, json-fast@{t2['json-fast']}")
print("== install from a day-20 lockfile on day 80 (frozen mode) ==")
lock = {n: (v, digest(n, v, REGISTRY[n][v][2])) for n, v in t1.items()}
ok = True
for name, version, pin, got in install_lock(lock):
    ok = ok and pin == got
    print(f"  {name}@{version}  lock sha256:{pin}  registry sha256:{got}  -> {'OK' if pin == got else 'MISMATCH'}")
print("== tamper test: same version, mutated artifact body in registry ==")
REGISTRY["json-fast"]["0.8.2"] = (12, {}, "body-D1-TAMPERED")
for name, version, pin, got in install_lock(lock):
    if pin != got:
        print(f"  {name}@{version}  expected sha256:{pin}  got sha256:{got}  -> BUILD FAILS")
        ok = False
print(f"  integrity check caught the tamper: {not ok}")
```

Output (byte-identical across runs):

```text
== resolve from manifest (ranges) on day 20 ==
  http-kit@2.3.1
  mini-log@1.1.0
  json-fast@0.8.2
== resolve the SAME manifest on day 80 ==
  http-kit@2.4.0
  mini-log@1.9.9
  json-fast@0.8.3
  trees differ: True  day-80 picks: http-kit@2.4.0, mini-log@1.9.9, json-fast@0.8.3
== install from a day-20 lockfile on day 80 (frozen mode) ==
  http-kit@2.3.1  lock sha256:44b5a404c91f9fd0  registry sha256:44b5a404c91f9fd0  -> OK
  json-fast@0.8.2  lock sha256:66433f65fc456e22  registry sha256:66433f65fc456e22  -> OK
  mini-log@1.1.0  lock sha256:6be14b3bcada0535  registry sha256:6be14b3bcada0535  -> OK
== tamper test: same version, mutated artifact body in registry ==
  json-fast@0.8.2  expected sha256:66433f65fc456e22  got sha256:38f3edc506cdbac3  -> BUILD FAILS
  integrity check caught the tamper: True
```

Three claims in the transcript: range resolution is *time-dependent* (the
identical manifest produced different trees, and the day-80 tree contains a
bait version of a transitive dependency no manifest ever mentioned); the
lockfile makes resolution *time-independent*; integrity fields make the
install *content-checked*.

## References

1. [npm Docs: package-lock.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-lock.json) -- `integrity` SRI field, `lockfileVersion` semantics (1/2/3).
2. [npm Docs: npm ci](https://docs.npmjs.com/cli/v10/commands/npm-ci) -- clean-install contract: lockfile required, mismatch is an error, never updates the lock.
3. [Cargo Book: Cargo.toml vs Cargo.lock](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) -- authorship split and commit guidance.
4. [Cargo Book FAQ](https://doc.rust-lang.org/cargo/faq.html) -- deterministic builds; lockfiles do not affect library consumers.
5. [Cargo Book: cargo build](https://doc.rust-lang.org/cargo/commands/cargo-build.html) -- `--locked` and `--frozen` exact definitions.
6. [Go Modules Reference](https://go.dev/ref/mod) -- go.sum verification, `-mod=readonly` default, `sum.golang.org`, `go.work` commit advice.
7. [pip: Secure Installs](https://pip.pypa.io/en/stable/topics/secure-installs/) -- tampering caveat, hash-checking mode.
8. [Pipenv Command Reference](https://pipenv.pypa.io/en/latest/commands.html) -- `--deploy` aborts on out-of-date `Pipfile.lock`.
9. [Poetry CLI: install --sync](https://python-poetry.org/docs/cli/) -- synchronizing the environment with locked packages.
10. [Gradle: Dependency Locking](https://docs.gradle.org/current/userguide/dependency_locking.html) -- `gradle.lockfile`, lock modes, `--update-locks`.
11. [RubyGems Guides: bundle install](https://guides.rubygems.org/command-reference/bundle-install/) -- `Gemfile.lock` and deployment mode.
12. [Renovate: lockFileMaintenance](https://docs.renovatebot.com/configuration-options/) -- scheduled lockfile-maintenance PRs.
13. [google/osv-scanner](https://github.com/google/osv-scanner) -- lockfile/SBOM scanning against OSV.
14. [RustSec cargo-audit](https://github.com/RustSec/rustsec/tree/main/cargo-audit) -- auditing `Cargo.lock` against RustSec advisories.
