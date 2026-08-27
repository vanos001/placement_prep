# Bazel and the Build Graph

Bazel's real contribution is not a faster compiler wrapper -- it is the
insistence that a build **is** a directed acyclic graph of actions, and that
parallelism, incrementality, caching, remote execution, and correctness all
fall out of taking that graph seriously. This page works through the model
and its failure modes. For a survey of build systems, see
[Build Systems](./build-systems.md); for why bit-identical output matters to
security, see [Reproducible and Hermetic Builds](./reproducible-builds.md).

## Why a Graph at All

Bazel's docs frame the choice as task-based vs artifact-based systems (its
Build Basics track treats them as separate chapters). The distinction
explains almost everything else:

- A **task-based** system (Make with phony targets, npm scripts) executes
  commands the author promises correspond to some effect; it schedules what
  it is told and cannot reason about what a task actually reads.
- An **artifact-based** system requires every command to declare its exact
  inputs and outputs. Once declarations exist the build *is* a graph, and
  the runtime can schedule, cache, and invalidate it on its own.

Bazel descends from Google's internal Blaze, built for a multi-million-file,
multi-language, single-repository world and open-sourced in 2015. At that
scale "recompile everything on one machine" is not an option: the graph model
plus distributed execution is the architecture that survives.

## Targets, Actions, Artifacts

Three levels. **Targets** are what users declare in `BUILD` files: a label
like `//server:main` names a `cc_binary` or `java_library` rule, and
`visibility` attributes constrain which packages may reference it. During
analysis, each target expands into **actions** -- a command, declared
inputs, declared outputs, an environment, execution requirements -- and
**artifacts** are the files flowing between actions:

```text
  //src:util.c  //lib:util.h  //src:app.c  //src:gen.proto
        |             |             |              |
        v             v             v              v
  (cc util.c)   (cc app.c)   (cc app.c)   (protoc genrule)
        |             +>[app.o]<+       [gen.proto.cc]
        v                                     |
  [util.o] --------> (link: cc -o app) <------+
```

Two property families are enforced against this graph. **Strict deps**: a
compile action sees exactly the headers its declaration lists -- reaching
for `#include "undeclared.h"` fails in the sandbox instead of silently
working, which turns accidental coupling into a build error. And analysis is
a pure function of the `BUILD` files, so every machine computes the same
action graph.

## Hermetic Actions: the Foundation

An action is [hermetic](https://bazel.build/concepts/hermeticity) when its
outputs depend only on its declared inputs and tools. Bazel approximates
this by running each action in a sandbox -- on Linux, filesystem namespaces
exposing only the declared inputs, a scratch directory, and the toolchain
resolved through the graph. The host's `/usr` is invisible.

The classic pathology this prevents is the implicit system include: a `gcc`
invocation whose declared sources are just `util.c` and `util.h`, but which
quietly reads `/usr/include/stdio.h` as well. It compiles on the author's
machine and breaks on a CI host with a different glibc. Under a sandbox the
same action fails immediately *on the author's machine* with "file not
found": the correct, cheap place to discover the missing edge. Bazel can
also *verify* hermeticity (run the action twice in different sandboxes and
diff the outputs). Either way, hermeticity is the precondition for the next
section: a key is only complete if nothing undeclared participates in the
output.

## Caching: Content-Addressed Action Keys

Because an action is fully described by its declaration, Bazel computes an
**action key**: a hash over the command, the digests of every input, the
environment, and the execution platform. Same key implies same outputs, so
the outputs can be looked up instead of computed. Three tiers:

1. **Local action cache** -- an on-disk map from keys to outputs, reused
   across builds on one machine.
2. **[Remote cache](https://bazel.build/remote/caching)** -- the same key
   space shared by a team through the content-addressable storage of the
   [Remote Execution API](https://github.com/bazelbuild/remote-apis)
   (`ActionCache` and `ContentAddressableStorage` gRPC services): a developer
   who pulls a dependency hits entries CI built last night.
3. **[Remote execution](https://bazel.build/docs/remote-execution)** -- same
   keys, but unmatched actions ship to a worker pool that runs them and
   uploads outputs by digest; hit lookup and execution are one protocol.

```text
(cmd, input digests, env, platform) --hash--> key K
  |-> [local action cache]        hit -> materialize outputs
    miss -> [remote action cache] hit -> download by digest
          miss -> [remote execution] worker runs it, uploads outputs
```

Cache hits skip work; stale hits are the failure mode. The key is only as
honest as the declaration behind it: if the command reads an undeclared
file, an environment variable, or `~/.gitconfig`, the key stays constant
while the true inputs changed, and the cache serves yesterday's output with
complete confidence. That is how impure actions poison a shared remote
cache: one non-hermetic action's stale outputs get distributed to every
developer and CI job computing the same key. Caching does not create the
correctness problem -- it amplifies it, at team scale.

## Incrementality: the Correctness/Speed Contract

The incremental engine (Skyframe) keys its in-memory state off the same
graph: change a source and only downstream actions re-run; change nothing
and every action is a cache hit (the demo shows a no-change rebuild
costing three lookups, zero compiles). The contract reads:

> Outputs are always correct for their declared inputs. Speed comes from
> skipping actions whose key already has outputs -- never from assuming
> unchanged files mean unchanged outputs.

Every discipline above keeps one side of that contract from being traded away:

| Contract breaker | Symptom | Where the model catches it |
|---|---|---|
| Undeclared header (`-I /usr/include`) | Stale objects after system update | Sandbox: read fails or verification diffs |
| Tool reads `$TZ` / `$LC_ALL` | Cache key misses an input | Environment must be declared per action |
| Absolute paths in commands | Rebuilds everywhere, nothing caches | Path is part of the key, differs per host |
| Tool writes extra undeclared outputs | Missing outputs for dependents | Output declaration checked post-run |
| Non-hermetic wrapper script | Random stale hits across the team | Rebuild-verification flags |

## The Ecosystem Around the Model

Several systems share the build-as-graph model (claims kept to what each
project's own materials state):

| System | Steward / origin | Implementation language | Notable differentiator |
|---|---|---|---|
| Bazel | Google lineage, community | Java, Starlark rules | Origin of the Remote Execution API; largest rule ecosystem |
| [Buck2](https://github.com/facebook/buck2) | Meta | Rust | Successor to Buck; remote-execution-first, concurrent incremental engine |
| [Pants](https://www.pantsbuild.org/) | Pantsbuild (ex-Toolchain) | Rust engine, Python plugins | Infers dependencies from imports; fine-grained invalidation |
| [Please](https://please.build/) | Thought Machine | Go | Bazel-style `BUILD` files, lighter-weight core |
| Gradle | Gradleware | Java/Kotlin DSL | Dominant JVM/mobile position; [task-output caching](https://docs.gradle.org/current/userguide/build_cache.html) |

The bets differ: Buck2 on Rust-speed graph evaluation with remote execution
first; Pants on inferring the graph from imports; Please on Bazel's model,
minus the surface area; Gradle on meeting JVM users where they are.

## When NOT to Adopt Bazel

Bazel's model earns its cost at scale; below that it is a tax:

- **Small repositories, fast full builds.** If a clean build takes two
  minutes on a laptop, the action cache solves a problem you do not have,
  while `BUILD` maintenance, rule versioning, and CI setup last forever.
- **Plugin-heavy legacy builds.** Maven/Gradle builds whose plugins read
  arbitrary state do not become hermetic by being wrapped; each plugin needs
  its inputs catalogued or rewritten -- a project, not a configuration task
  (see the migration questions in [Build Systems](./build-systems.md)).
- **No build-infrastructure appetite.** Remote caches and execution clusters
  are real systems with capacity planning; a team that will not own them
  should not adopt the architecture that presumes them.
- **Churning, exploratory codebases.** Heavy codegen and constant structural
  experiments mean constant `BUILD` churn; the graph pays off once structure
  stabilizes.

The honest adoption test: count the cost of *declaring everything*. If the
build has a well-defined structure and a hungry CI queue, the graph converts
that structure into parallelism and caching; if the structure lives in
people's heads, write it down first.

## Demonstration: An Action Cache, Including Its Poisoning

The script implements the model in miniature: actions with declared inputs,
content-addressed keys, a shared cache -- and one undeclared header in
`/usr/include` that `compile_util` reads but nobody declared. Watch the cold
build, the all-hit no-change rebuild, an edit re-running only downstream
actions, then the header drifting under a static key.

```python
import hashlib

def dg(b): return hashlib.sha256(b).hexdigest()[:12]

# (command, declared file inputs, action inputs) -- an Action proto in miniature
ACTIONS = {
    "compile_util": ("cc -c util.c -o util.o", ["//src:util.c"],                []),
    "compile_app":  ("cc -c app.c  -o app.o",  ["//src:app.c", "//lib:util.h"], []),
    "link":         ("ld app.o util.o -o app", [], ["compile_app", "compile_util"]),
}
FILES0 = {"//src:util.c": "int helper(){return 42;}",
          "//src:app.c":  "int main(){return helper();}",
          "//lib:util.h": "int helper(void);"}
# meanwhile /usr/include/stdio.h exists as printf-decl-v1: read, never declared

def execute(graph, files, cache, log, tag, target="link"):
    def val(name):
        cmd, file_in, act_in = graph[name]
        material = [cmd] + [f + "=" + files[f] for f in sorted(file_in)] \
                        + ["dep:" + val(d) for d in act_in]
        key = hashlib.sha256("|".join(material).encode()).hexdigest()
        if key in cache:
            out, mark = cache[key], "HIT "          # content-addressed lookup
        else:
            out, mark = dg((key + "|built").encode()), "MISS"
            cache[key] = out
        log.append("  [%s] %s %-13s key=%s -> %s" % (tag, mark, name, key[:10], out))
        return out
    return val(target)

cache, log = {}, []
execute(ACTIONS, FILES0, cache, log, "run1")            # cold
execute(ACTIONS, FILES0, cache, log, "run2")            # nothing changed
print("run 1 (cold cache) and run 2 (nothing changed):"); print("\n".join(log), end="\n\n")

log = []
files1 = dict(FILES0, **{"//src:app.c": "int main(){return helper()+1;}"})
execute(ACTIONS, files1, cache, log, "run3")
print("run 3 (app.c edited):"); print("\n".join(log), end="\n\n")

# the undeclared header drifts under the build; the key cannot see it
log = []
execute(ACTIONS, FILES0, cache, log, "run4")
stale = execute(ACTIONS, FILES0, cache, [], "x", target="compile_util")
print("run 4 (undeclared stdio.h changed to v2):"); print("\n".join(log))
hk = hashlib.sha256(("[cc -c util.c -o util.o]//src:util.c=" + FILES0["//src:util.c"] + "|stdio.h=printf-decl-v2").encode()).hexdigest()
honest = dg((hk + "|built").encode())
print("  hermetic key (stdio.h declared):", hk[:10], "| cache miss:", hk not in cache)
print("  hermetic rebuild would produce:", honest)
print("  cache served compile_util:      ", stale)
print("  stale output served:            ", honest != stale)
```

Verbatim output (Python 3.12; the script is deterministic):

```text
run 1 (cold cache) and run 2 (nothing changed):
  [run1] MISS compile_app   key=395c463b3a -> 62173dc11e9b
  [run1] MISS compile_util  key=24a0972bf5 -> 648cf5b3d408
  [run1] MISS link          key=6351873eeb -> 406633457756
  [run2] HIT  compile_app   key=395c463b3a -> 62173dc11e9b
  [run2] HIT  compile_util  key=24a0972bf5 -> 648cf5b3d408
  [run2] HIT  link          key=6351873eeb -> 406633457756

run 3 (app.c edited):
  [run3] MISS compile_app   key=4f415b81f9 -> 4f36c30e701b
  [run3] HIT  compile_util  key=24a0972bf5 -> 648cf5b3d408
  [run3] MISS link          key=22665c7147 -> 7782e1ce3429

run 4 (undeclared stdio.h changed to v2):
  [run4] HIT  compile_app   key=395c463b3a -> 62173dc11e9b
  [run4] HIT  compile_util  key=24a0972bf5 -> 648cf5b3d408
  [run4] HIT  link          key=6351873eeb -> 406633457756
  hermetic key (stdio.h declared): e30fb661a3 | cache miss: True
  hermetic rebuild would produce: c4ff0ac4ca43
  cache served compile_util:       648cf5b3d408
  stale output served:             True
```

Note what run 4 does *not* show: an error. The stale hit is indistinguishable
from a good one at the cache level -- exactly why hermeticity is enforced at
execution time, not at the cache.

## References

1. [Bazel -- Hermeticity](https://bazel.build/concepts/hermeticity) -- benefits, identification, and troubleshooting of non-hermetic actions.
2. [Bazel -- Remote caching](https://bazel.build/remote/caching) -- shared cache semantics and cache-hit requirements.
3. [Bazel -- Concepts: build refs](https://bazel.build/concepts/build-ref) -- labels, packages, targets, visibility.
4. [bazelbuild/remote-apis](https://github.com/bazelbuild/remote-apis) -- Remote Execution API specification (ActionCache, CAS, execution services).
5. [facebook/buck2](https://github.com/facebook/buck2) -- Meta's Rust build system, remote-execution-first design.
