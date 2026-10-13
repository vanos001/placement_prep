# mcookie — generate 128-bit random hex cookies for xauth

## Overview

`mcookie` prints a 128-bit random number as 32 hexadecimal characters, in the format X11 authority ("magic cookie") records use. Its historical job is provisioning `.Xauthority` entries: X session starters call it to mint the cookie that the X server and `xauth`-using clients must both present. The name is literal — it generates *magic cookies*.

It ships in the `util-linux` package at `/usr/bin/mcookie`. The tool descends from the X11 ecosystem's `mcookie` of the 1990s and has been part of util-linux for decades. Randomness comes from the kernel (`getrandom()` with `/dev/urandom` fallback); MD5 is used only as a mixing function, not as the entropy source. It is often confused with `uuidgen` (UUID formatting and semantics, different use case), with `sha1sum`/`md5sum` (hashing given data — deterministic, not random), and with the `xauth` program itself (which stores cookies; mcookie only creates them).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mcookie |
| First appeared | X11 tooling of the 1990s; long part of util-linux |
| Standards | None — X11 auth-file convention (32 hex chars) |

## Synopsis

```
mcookie [options]
```

Common one-line forms:

```
mcookie                          # 32 hex chars from kernel randomness
mcookie -f /tmp/seed.bin         # mix in a seed file
mcookie -v                       # show where the randomness came from
xauth add :0 . "$(mcookie)"      # the classic use
```

## How It Works

### Where the 128 bits come from

The tool gathers random material from several sources and reduces them with the MD5 message-digest algorithm to exactly 16 bytes, printed as 32 lowercase hex characters. The primary source is the kernel: it requests 128 bytes via `getrandom()` and also mixes bytes from `/dev/urandom`. Seed files passed with `-f` contribute additional input. A verbose run shows the sources:

```
$ mcookie -v
Got 4096 bytes from /dev/urandom
Got 128 bytes from getrandom() function
72873becf27212396d5c62d1dfac483f
```

```
getrandom() ──128 bytes──┐
/dev/urandom ──4096 B────┤
-f seed files ──≤max─────┼──▶ MD5 ──▶ 16 bytes ──▶ 32 hex chars
```

Because the kernel randomness dominates the mix, a low-quality seed file cannot *weaken* the result — it only adds input to the digest. This design predates `getrandom()`; older implementations relied on `/dev/urandom` alone plus optional seeds (classic recipes mixed in the process ID, `find /` output, or file contents when the kernel source was unavailable).

### Why a "cookie" and not a key

X11's MIT-MAGIC-COOKIE-1 authentication is shared-secret: the client that presents the correct 128-bit cookie is granted the display. The value never needs to be typed by humans and never needs structure — unlike UUIDs, which encode version/variant bits and are meant for identity, not secrecy. That is why mcookie exists separately from uuidgen: different properties for different jobs.

### The canonical consumer

X session scripts (xinit/startx lineage) run `xauth add "$DISPLAY" . "$(mcookie)"` to store the cookie, then pass the same value to the server's `-auth` file. Anything that can read your `.Xauthority` can use your display — which is why the file is mode 0600 and why mcookie output should go straight into xauth rather than through logs.

### The cookie lifecycle

A cookie has two copies and a lifetime:

```
 mcookie ──▶ server side: X server's -auth file  (what it will accept)
         └─▶ client side: ~/.Xauthority record   (what clients present)

xauth list                     # existing records: display, auth name, hex cookie
xauth extract /tmp/key :0      # export a cookie for another host
xauth merge /tmp/key           # import it elsewhere (or ssh -X does this for you)
```

Rotation is just: generate a new cookie, add it to both files, remove the old record. The format has no expiry — cookies live until withdrawn, which is why `xauth remove` belongs in session teardown and why stale cookies on long-lived accounts are a recurring audit finding. When cookie auth is not configured, X falls back to the `xhost` host-based model, which is strictly weaker (any user on a trusted host passes) — the reason modern sessions always run with `-auth` and a fresh mcookie.

### Generator landscape, compared

| Tool | Output | Random? | Structural | Typical use |
| --- | --- | --- | --- | --- |
| `mcookie` | 32 hex chars (128-bit) | kernel CSPRNG | none — pure secret | X11 authority records |
| `uuidgen` | 36 chars with dashes | kernel CSPRNG | version/variant bits | object/session identity |
| `openssl rand -hex 16` | 32 hex chars | kernel CSPRNG | none | generic tokens (needs openssl installed) |
| `md5sum` of chosen input | 32 hex chars | **no** — deterministic | digest of input | checksums — never secrets |

The last row is the anti-pattern mcookie exists to prevent: hashing timestamps, PIDs, or hostnames to "make random-looking" tokens. Deterministic input yields guessable output no matter how the format looks. When openssl is unavailable and mcookie is missing, the `/dev/urandom | od` recipe covers the gap with the same kernel source.

### What -f is really for

The seed-file option descends from an era when `/dev/urandom` was not guaranteed: 1990s systems without it needed *something*, and files (photos, logs, disk noise) plus a fixed recipe provided degraded-but-real entropy. Today the option is a vestige that still has one legitimate use — mixing in true hardware randomness (`-f /dev/hwrng` on devices that expose it) as belt-and-suspenders. The security model is monotonic: more input can add entropy, never remove it, because the kernel sources always participate.

### Entropy deep-dive: getrandom() vs /dev/urandom

The two kernel sources differ in blocking behavior: `getrandom()` blocks until the CSPRNG is initialized on very early boot (guaranteeing good randomness) and then behaves like `/dev/urandom`. mcookie requests its 128 getrandom bytes first and mixes in the larger urandom pull, so even on a freshly booted, low-entropy appliance the output is safe. This matters for embedded images where session scripts run before entropy collection finished — the tool was hardened for exactly that race.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --file <file>` | Read this file and mix its contents into the cookie |
| `-m, --max-size <num>` | Cap how many bytes are read from each seed file (suffixes: KiB, MiB, ...) |
| `-v, --verbose` | Explain what is being done (list randomness sources and byte counts) |
| `-h, --help` / `-V, --version` | Help and version |

## Usage Patterns

```bash
# Generate a cookie (the default job)
mcookie
```

```bash
# Wire a new display into xauth the classic way
xauth add "${DISPLAY}" . "$(mcookie)"
```

```bash
# Fresh random value for a tmpfs-stored auth file
mcookie > /tmp/new-x-cookie && chmod 600 /tmp/new-x-cookie
```

```bash
# See the randomness sources for a sanity check
mcookie -v
```

```bash
# Mix in a hardware-entropy file as additional input
mcookie -f /dev/hwrng
```

```bash
# Cap seed-file reads so a huge file cannot dominate runtime
mcookie -f /var/log/big.log -m 1MiB
```

```bash
# Generate two cookies and confirm they differ (no state, no counters)
[ "$(mcookie)" != "$(mcookie)" ] && echo independent
```

```bash
# Bake randomness into a script variable for later xauth use
COOKIE=$(mcookie); export COOKIE
```

```bash
# 128 bits represented as raw bytes instead of hex (same entropy, other format)
mcookie | xxd -r -p | xxd
```

```bash
# Compare shapes: cookie vs UUID (structure vs pure secret)
mcookie; uuidgen
```

```bash
# Portable fallback when mcookie is unavailable (same recipe, 16 bytes, hex)
head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'
```

```bash
# Inspect existing X authority records before adding a new one
xauth list
```

```bash
# Rotate: add a fresh cookie for the display, then drop the stale one
xauth add "${DISPLAY}" . "$(mcookie)"
```

```bash
# Unbuffered single-line check: exactly one 32-hex-char line per run
mcookie | grep -Ec '^[0-9a-f]{32}$'
```

```bash
# Generate a batch of display cookies for a terminal-server setup
for d in :1 :2 :3; do printf '%s %s\n' "$d" "$(mcookie)"; done
```

```bash
# Feed a cookie to a program that expects it on stdin, not argv
mcookie | ssh host 'cat > ~/.new-cookie'
```

## Nuances and Gotchas

- **MD5 is a mixer, not the entropy source.** Seeing "MD5" in the description makes people assume weakness. The digest is a fixed-size mixing step; the security comes from kernel randomness. Pre-images and collisions of MD5 are irrelevant to the output's unpredictability.
- **Never treat seed files as the source of secrecy.** `-f` input only *adds* material. But if you script cookies from predictable files (dates, hostnames) on a system lacking kernel randomness, the old failure mode returns — always verify a kernel random source exists.
- **Output length is fixed at 32 hex chars.** It is not configurable and not a UUID: no dashes, no version bits. Don't shoehorn it into UUID parsers or vice versa.
- **Command substitution vs leaks.** `xauth add ... $(mcookie)` exposes the cookie in the process arguments (visible in `ps` snapshots) for the duration of the call. Interactive use is fine; high-security contexts write cookies to fd 0600 files and let xauth read them instead.
- **History/logs.** Redirecting mcookie output to a shared-readable file or CI log publishes your display secret. The classic X breach is not weak cookies; it is cookies in world-readable places.
- **Busybox/coreutils have no mcookie.** It is util-linux-specific; portable scripts substitute `head -c 16 /dev/urandom | xxd -p` (or `od -An -tx1`) when the tool is absent.
- **No state, no API.** Each invocation is independent; there is no daemon, no seed file it maintains, and no way to "replay" a previous cookie. Two runs never collide in practice (128 bits).
- **Cookies never expire by themselves.** The X authority format has no TTL; rotation is manual discipline. Audit scripts that check `.Xauthority` records against login sessions are the realistic control.
- **verbose output is for humans.** `-v` prints source diagnostics; do not parse it. The only contract is one line of 32 hex chars on stdout.
- **Seed files are optional and additive.** A missing `-f` file is an error (exit 1), not a silent fallback — scripts treating `-f` as "best effort" must check the exit code.
- **The X11 connection is historical context, not a dependency.** mcookie works on headless servers with no X installed; the output is just 128 random bits. Repurposing it as a generic token generator is fine — it is the format consumers (xauth records) that care about the X11 convention.

## Exit Status

- `0` — cookie generated and printed.
- `1` — failure: seed file unreadable, no usable random source, or invalid options.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`command reference`](../../reference/commands.md) — where the small generator utilities live in the book.

## Interview Questions

### Q: What exactly does mcookie produce, and what consumes it?

Exactly 16 random bytes rendered as 32 lowercase hex characters — the MIT-MAGIC-COOKIE-1 format X11 authority records use. Its canonical consumer is `xauth add` during X session startup: the cookie is stored client-side in `.Xauthority` and must match what the X server expects for the display. It is a shared-secret token, not a key, certificate, or UUID.

### Q: The man page mentions MD5. Is mcookie output cryptographically weak?

No. MD5 is used as a mixing function over inputs that include 128 bytes from `getrandom()` and thousands of bytes from `/dev/urandom`. The digest collapses those inputs to 128 bits; its known collision attacks concern chosen-prefix hashing of attacker-controlled data, not extraction of entropy from a kernel CSPRNG stream. The security of the cookie equals the kernel's randomness, not MD5's collision resistance.

### Q: Why does mcookie exist separately from uuidgen when both print random-looking hex?

Different requirements. UUIDs carry version/variant structure and are designed for uniqueness and identity; cookies are pure 128-bit secrets with zero structure. Conflating them couples auth material to UUID semantics (and uuidgen's `-` separators would even break X authority parsing). Separate tools keep each format's contract clean.

### Q: You need a random 128-bit token in a minimal container without mcookie. What do you reach for?

The same entropy mcookie itself uses: `head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'` (or `xxd -p`). The lesson interviewers want: understand the underlying source — kernel CSPRNG, 16 bytes, hex-encode — rather than treating mcookie as magic. The tool is a convenience wrapper over exactly this.

### Q: What operational mistakes leak X cookies even when they are generated securely?

Printing them into logs or CI output, writing them to world-readable files, passing them as long-lived process arguments visible in `ps`, and storing `.Xauthority` with lax permissions. The generation is the easy part; the cookie's lifetime handling is where displays get hijacked.

### Q: Why is MIT-MAGIC-COOKIE-1 still used when stronger X auth exists?

Because the alternatives trade simplicity for infrastructure. Cookie auth is a single shared secret compared per connection — no keys to distribute, no daemon, no Kerberos realm; the security envelope (network-reachable X displays) matches how most X sessions actually run (local Unix sockets or SSH-forwarded). Stronger schemes (SUN-DES, Kerberos userauth, XCOOKIE-style) bind to environments that largely do not exist on Linux desktops. The cookie plus a 0600 `.Xauthority` and SSH forwarding is the pragmatic equilibrium.

### Q: Why 128 bits for a display token?

It must resist online guessing over the display socket's lifetime. 128 bits makes brute force physically absurd, fits one MD5 block (the historical mixing step), and is one `xauth` field wide — no economy was worth a smaller secret once the format was set. The same width budget reasoning appears in OAuth refresh tokens and session IDs: interactive-secret lengths are chosen so enumeration is hopeless, not so storage is minimal.

### Q: What happens if two users' cookies collide, or a cookie is reused across displays?

Collisions are negligible (128-bit random), but *deliberate* reuse is a real footgun: one cookie value shared across displays/hosts means one leak compromises all of them, and revocation gets tangled. Per-display cookies (the default behavior of generating fresh per session) isolate blast radius — which is why automation should never copy a cookie between auth records instead of minting a new one.

### Q: Walk through how an X session gets its cookie from boot to working display.

The display manager (or startx) calls mcookie, stores the value in a temporary server-side `-auth` file, and starts the X server with it. The same value is added to the user's `.Xauthority` via xauth for the target DISPLAY. Clients connecting to that display present the record from `.Xauthority`; the server compares and grants. Session teardown removes the record. Understanding this loop explains every mcookie-adjacent failure: wrong DISPLAY naming, stale records, unreadable auth files, and why `xhost +` (the host-based escape hatch) is such a dangerous shortcut.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/mcookie.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
