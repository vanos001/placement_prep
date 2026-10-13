# uuidgen — generate universally unique identifiers

## Overview

`uuidgen` creates RFC 4122 **UUIDs** — 128-bit identifiers printed as 36 characters (`xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx`) whose uniqueness comes from randomness or time/space coordinates rather than a central registry. It is the command-line front end of libuuid and ships in the Debian `uuid-runtime` package (upstream: util-linux) at `/usr/bin/uuidgen`.

You reach for `uuidgen` whenever something needs a collision-free identifier without coordination: test fixtures, database keys where you accept the index cost, temporary filenames, Kubernetes/network object names, request IDs in logs. It is often confused with `dbus-uuidgen` (generates machine IDs for D-Bus specifically — a different tool with different output semantics), `uuidparse` (analyzes existing UUIDs instead of creating them), and shell tricks like `cat /proc/sys/kernel/random/uuid` (kernel-provided v4 UUID, no libuuid involved).

| Field | Value |
| --- | --- |
| Package | uuid-runtime (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/uuidgen |
| First appeared | e2fsprogs libuuid lineage; moved to util-linux in the 2.15 era |
| Standards | RFC 4122 / ITU-T X.667 UUID format; not POSIX |

## Synopsis

```
uuidgen [options]
```

Main one-line forms:

```
uuidgen                 # random v4 UUID (default)
uuidgen -r              # explicit random
uuidgen -t              # time-based v1 UUID (MAC-address derived)
uuidgen | tr -d '-'     # 32-hex-char form, the usual postprocessing
```

## How It Works

### The two generation strategies

UUID layout and version bit (the `M` nibble after the first dash):

```
xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
                 │   │
                 │   └── variant bits (N in [89ab] for RFC 4122)
                 └────── version: 1 = time-based, 4 = random
```

- **`-r` (v4, the default)**: 122 bits come from the OS CSPRNG (`getrandom`/`/dev/urandom`), 6 bits are fixed version/variant. Collision odds are astronomically small; nothing about the host leaks. Output is lowercase; you uppercase it yourself if needed.
- **`-t` (v1)**: 60-bit timestamp (100 ns units since 1582-10-15) + 14-bit clock sequence + the node field, normally the interface MAC address. Guaranteed unique for one node without any RNG — but it *encodes when and which machine*, a privacy property people often miss.

### The versions, briefly

Context for what `-r` and `-t` actually produce, and what other tools emit:

```
ver  name            meaning                        uuidgen makes it?
---  --------------  -----------------------------  ----------------
1    time-based      clock(1582) + clock seq + MAC  -t
2    DCE security    POSIX uid/gid embedded         no
3    name (MD5)      hash of namespace UUID + name  no (API only)
4    random          122 CSPRNG bits                -r (default)
5    name (SHA-1)    v3 with a stronger hash        no (API only)
6,7  reordered time  v1/v4 with time sort order     recent libuuid APIs
8    custom          vendor-defined payloads        no
```

The v6/v7 rows explain the "sortable UUIDs" trend: they keep v1/v4's generation model but re-order the time bits so lexicographic sort ≈ creation order — the property databases actually want. Bookworm-era CLI offers v1/v4; newer language runtimes fill the rest.

### Entropy and quality notes

v4 quality rests entirely on the OS CSPRNG: libuuid seeds from `getrandom(2)`/`/dev/urandom`, so on a healthy kernel all 122 bits are unpredictable and unsuitable for brute-force prediction. v1 has *zero* entropy requirements (uniqueness comes from clock+node coordination) — which is exactly why its timestamps are meaningful and its privacy is poor. If a compliance checklist says "UUIDv4 from a CSPRNG", `uuidgen` (default mode) or the `/proc/sys/kernel/random/uuid` file both qualify.

### What libuuid does underneath

`uuidgen -r` calls `uuid_generate_random()`, which prefers the kernel CSPRNG. `uuidgen -t` goes through libuuid's time path, which has a uniqueness pitfall: two processes generating v1 UUIDs in the same clock tick must not share a clock sequence. libuuid solves this two ways — a persistent state file (clock sequence under `/var/lib/libuuid/`) and, when available, the **uuidd** daemon (see Variants below) that serializes generation machine-wide. If no usable MAC address exists, libuuid substitutes a random multicast-bit node, so v1 output remains valid but is no longer location-stable.

```bash
$ uuidgen
e3c89b41-9a2f-4c7e-a6d3-1f5b2c9d8e01
$ uuidgen -t
b1c2d3e4-5f60-11ef-9cd2-0242ac120002      # '1' version nibble, MAC-derived tail
```

### Choosing a strategy

```
need                              choose
--------------------------------  -------------------------------------
just an opaque unique id          v4 (default)   — never leaks, no state
sortable by creation time         v1, or newer v6/v7 in recent libuuid
compat with legacy v1 consumers   -t
identifiers derived from names    v3/v5 (not exposed by uuidgen CLI;
                                  use uuid_generate_* APIs or other tools)
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-r, --random` | Generate a random (version 4) UUID. This is the default. |
| `-t, --time` | Generate a time-based (version 1) UUID from clock + node address. |
| `-h, -V` | Help / version. |

Recent upstream releases add further time-based UUID versions (v6/v7-style reordered timestamps) to the libuuid family; bookworm's CLI exposes the classic `-r`/`-t` pair, and name-based v3/v5 generation is left to the library API.

## Usage Patterns

```bash
# One throwaway identifier for a test fixture
uuidgen
```

```bash
# Unique temp directory name that survives concurrent runs
dir=$(mktemp -d /tmp/build-$(uuidgen)-XXXX)
```

```bash
# 32-hex form for systems that dislike dashes
uuidgen | tr -d '-'
```

```bash
# Uppercase form (some registries expect it)
uuidgen | tr 'a-f' 'A-F'
```

```bash
# Generate a batch of ids for seeding test data
for i in $(seq 1 10); do uuidgen; done
```

```bash
# Request id for log correlation across services
curl -H "X-Request-Id: $(uuidgen)" https://api.example.test/
```

```bash
# Check whether an id was random or time-based (see uuidparse)
uuidgen -t | uuidparse
```

```bash
# Use the kernel's built-in v4 source instead (same shape, no package needed)
cat /proc/sys/kernel/random/uuid
```

```bash
# Sortable-ish ids: v1 groups by generation time
uuidgen -t; uuidgen -t
```

```bash
# Assign a stable id to a config object in a deploy script
printf 'id: %s\n' "$(uuidgen)" >> objects.yaml
```

```bash
# Naming k8s-style resources where DNS labels are required
printf '%s' "$(uuidgen)" | tr -d '-' | cut -c1-10
```

```bash
# Seed a SQLite table with unique external keys
for i in $(seq 1 100); do echo "INSERT INTO ext_ids VALUES ('$(uuidgen)');"; done | sqlite3 app.db
```

```bash
# Compare v1 vs v4 for leak testing with uuidparse
uuidgen -t | uuidparse; uuidgen | uuidparse
```

```bash
# Prewarm the daemon: generate a batch of ids through uuidd in one call
uuidd -r -n 100 > request_ids.txt
```

## Variants — the uuidd daemon

`uuid-runtime` also ships **uuidd**, a small daemon whose only job is to issue UUIDs atomically to local clients over the unix socket `/run/uuidd/request` (run as the unprivileged `uuidd` user; on systemd systems it is socket-activated by `uuidd.socket` and idles away between requests).

- **Why it exists.** Time-based (v1) UUID generation has a concurrency hazard: two processes in the same clock tick can produce identical timestamps, and the clock-sequence increment must be serialized. `uuid_generate_time_safe()` asks uuidd to hand out v1 UUIDs so uniqueness is guaranteed machine-wide; without the daemon libuuid falls back to in-process generation with the state file.
- **Random UUIDs via the daemon.** The daemon can also serve random UUIDs and, crucially, *bulk* requests — one round trip for N ids:

```bash
$ uuidd -r              # one random UUID from the running daemon
$ uuidd -r -n 5         # five random UUIDs in one request
$ uuidd -t              # one time-based UUID via the daemon
$ uuidd -k              # kill the running daemon
```

- **Daemon options worth knowing:** `-r`/`-t` request type, `-n <count>` batch size, `-p`/`-s` pid/socket paths, `-T` timeout, `-d` debug (foreground, no daemonize), `-k` kill, `-q` quiet.
- **uuidgen vs uuidd:** the `uuidgen` CLI itself never contacts the daemon; the daemon is consumed through libuuid's `*_safe` calls (which is what database drivers and language bindings typically use). If a stack depends on strict v1 uniqueness under high concurrency, ensure `uuidd.socket` is enabled.
- **Socket-activation details.** On systemd systems, `uuidd.socket` listens on `/run/uuidd/request` and spawns `uuidd.service` on first use; the daemon then idles out after its timeout. If a `uuidd -t` request fails with *connection refused*, the unit is masked, the socket was removed, or the package's `uuidd` user is missing — libuuid's client side then silently falls back to non-daemon (state-file) generation, which loses the cross-process uniqueness guarantee.

## Nuances and Gotchas

- **v1 leaks identity.** `-t` output embeds your MAC address and a clock readable since 1582; pasted into logs or commits, it fingerprints the generating machine. Default to v4 unless you specifically need time order.
- **v4 is lowercase, and that matters occasionally.** Some consumers compare UUIDs case-sensitively; RFC 4122 says generate lowercase, compare case-insensitively — normalize before storing or diffing.
- **`cat /proc/sys/kernel/random/uuid` is not uuidgen.** It is a kernel-synthesized v4 UUID — fine for scripts, but it bypasses libuuid entirely (no v1, no uuidd integration) and each read costs a CSPRNG draw.
- **Do not confuse with `dbus-uuidgen`.** That tool produces machine-scoped ids for D-Bus' machine UUID file and is a separate package/tool with different semantics; substituting one for the other in provisioning scripts is a classic error.
- **UUID collisions are not zero.** v4 has 122 random bits — collisions are negligible, but if you generate ids on multiple uncoordinated hosts and *insert into a unique index*, plan for the retry path anyway; interviewers like hearing the number (roughly: half the keyspace used at ~2^61 ids).
- **Minimal containers may lack it.** `uuid-runtime` is often not installed in slim images even though `util-linux` is; the `/proc` fallback or a language runtime's uuid library avoids the dependency.
- **Name-based v3/v5 are not available via this CLI.** They are libuuid API features (`uuid_generate_md5`/`sha1`); `uuidgen` only creates fresh v4/v1 identifiers.
- **uuidgen is not a CSPRNG API.** Its output contains exactly 122 random bits — fine for identifiers, never for keys or secrets. For key material use `openssl rand`/`head -c` on /dev/random-backed sources; interviewers sometimes probe whether people confuse "random-looking" with "cryptographic".
- **BusyBox and musl images.** Alpine/busybox containers ship `uuidgen` only via the `uuidgen` package (or libuuid); CI scripts should fall back to `/proc/sys/kernel/random/uuid` when the binary is absent rather than failing the build.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | UUID generated and printed. |
| nonzero | Usage error, or UUID generation failed (e.g. CSPRNG unavailable in restricted environments). |

## Related Commands

- [`uuidparse`](./uuidparse.md) — decode a UUID's variant/type/time/node instead of generating one.
- [`mcookie`](./mcookie.md) — generates random magic cookies for X authentication; the "random id" sibling for that niche.
- [`blkid`](./blkid.md) — filesystem UUIDs (a different namespace of UUIDs you will meet in `fstab`).
- [`../../reference/man-pages.md`](../../reference/man-pages.md) — how section-1 tools and their libraries are documented.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What are the differences between v1 and v4 UUIDs, and when would you deliberately pick v1?

v1 = timestamp + clock sequence + node (MAC); v4 = 122 random bits. v4 is the default choice: no identity leakage, no coordination state. You pick v1 (or the newer reordered time variants) when ids must be roughly sortable by creation time, when you need uniqueness without a CSPRNG, or when a legacy system derives meaning from the embedded node/timestamp.

### Q: Why does libuuid ship a whole daemon (uuidd) for something "uuidgen does alone"?

v1 uniqueness under concurrency needs serialization: two processes generating in the same 100 ns tick must not reuse a clock sequence. libuuid persists clock-sequence state and, when uuidd is running, delegates v1 generation to it via a local socket so uniqueness is machine-wide and batches can be served in one round trip. The CLI `uuidgen` itself doesn't use the daemon — library callers (`uuid_generate_time_safe`) do.

### Q: A teammate pasted `uuidgen -t` output into a public bug report. What information leaked?

The v1 UUID encodes the generating host's interface MAC address (node field) and a timestamp with 100 ns resolution counting from 1582. From it you can derive the machine's MAC (hence vendor and network identity) and when the id was minted — enough to correlate infrastructure. Rotating the leaked id (just generate a v4 replacement) is the fix.

### Q: Is `uuidgen` output safe to use as a database primary key? Discuss trade-offs.

Uniqueness-wise yes; index-wise it is costly: random v4 keys scatter across a B-tree, wrecking locality and cache hits, and at 16 raw bytes they bloat indexes versus 8-byte sequences. Common mitigations: UUIDv7-style time-ordered ids, key-prefix schemes, or using the UUID only as an external identifier with a monotonic internal key.

### Q: How does `uuidgen -r` differ from `cat /proc/sys/kernel/random/uuid`?

Both produce v4 identifiers, but via different generators: `uuidgen` calls libuuid (`uuid_generate_random`, CSPRNG-backed), while the sysfs file is synthesized by the kernel on read. Functionally interchangeable for scripts; the difference matters when you need libuuid's other machinery (v1, daemon, parsing) or when the `uuid-runtime` package is unavailable in a minimal image.

### Q: Your load test shows duplicate time-based UUIDs from multiple app servers. What went wrong at the protocol level?

Classic v1 coordination failure: the servers share a virtual MAC (cloned VMs/containers), so the node field matches while their clocks and clock sequences race in the same tick — the exact scenario uuidd prevents on a single host, and which no daemon can fix across hosts. Fixes: generate v4 everywhere (CSPRNG needs no coordination), or ensure distinct node fields and serialize via a central generator. This is also why cloned VMs are told to regenerate machine-id/UUID state at first boot.

### Q: What does the version nibble and variant bits tell you about `9f8b7c6d-5e4f-3a2b-8c9d-0e1f2a3b4c5d`?

The nibble after the second dash (`3`) marks version 3 — name-based MD5 — and the variant bits in the fourth group's first character (`8` in `8c9d`) indicate the RFC 4122 variant. So this identifier was derived by hashing a namespace UUID plus a name, not generated randomly or from a clock — the kind of fact `uuidparse` prints mechanically.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/uuid-runtime/uuidgen.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
