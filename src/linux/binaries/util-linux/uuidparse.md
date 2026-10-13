# uuidparse — decode the structure of a UUID

## Overview

`uuidparse` takes one or more UUID strings and prints their *internal structure*: which **variant** they belong to (NCS, DCE/RFC 4122, Microsoft, other), which **type/version** they are (v1 time-based, v2 DCE-security, v3 MD5-name, v4 random, v5 SHA-1-name, nil, invalid), and — for time-based UUIDs — the decoded **timestamp** and **node** (usually the MAC address) they encode. It ships in the Debian `uuid-runtime` package (upstream: util-linux, built on libuuid) and reads stdin when no arguments are given.

You reach for it when a UUID must be interpreted rather than merely generated: sorting out why two "UUIDs" from different vendors don't compare, checking whether an identifier leaks a MAC address (v1), detecting nil/placeholder values in data feeds, or classifying identifiers found in logs. It is often confused with `uuidgen` (creates UUIDs — the opposite direction) and with `blkid`/`findfs` (which resolve *filesystem* UUIDs to devices; uuidparse works purely on the string's bit layout).

| Field | Value |
| --- | --- |
| Package | uuid-runtime (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/uuidparse |
| First appeared | added to util-linux in the 2.31 era (2017) |
| Standards | RFC 4122 / ITU-T X.667 field semantics |

## Synopsis

```
uuidparse [options] [uuid ...]
```

Main one-line forms:

```
uuidgen | uuidparse                   # classify a freshly generated id
uuidparse 7d444840-9dc0-11d1-b245-5ffdce74fad2
uuidparse -J < uuids.txt              # JSON report over a list
uuidparse -o UUID,TYPE < id.list      # project specific columns
uuidparse -n < ids.txt                # headerless table for scripts
```

## How It Works

### What the bits mean

A UUID is 128 bits laid out as five fields; two of them carry the classification payload:

```
time_low  time_mid  ver  variant   node/remainder
xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
           M = version nibble (1..5 for RFC 4122 types)
           N = variant bits:  0xxx NCS (obsolete)
                              10xx RFC 4122 / DCE
                              110x Microsoft
                              111x reserved/other
```

For each input, `uuidparse` runs the libuuid parse and derives:

- **VARIANT** — the header interpretation: `DCE` (the RFC 4122 family you almost always see), `NCS`, `Microsoft`, `other`, plus `nil` for the all-zero UUID and `invalid` for garbage.
- **TYPE** — for DCE-variant ids, the version: `v1` time-based, `v2` DCE-security, `v3` name+MD5, `v4` random, `v5` name+SHA-1; non-DCE and nil/invalid ids have no type.
- **TIME** — only v1/v2 carry a real timestamp: the 60-bit count of 100 ns intervals since 1582-10-15, rendered as a date/time (UTC offset shown).
- **NODE** — for v1/v2, the 48-bit node: a MAC address, or a random node with the multicast bit set when no usable hardware address was available at generation time.

### Version cheat sheet

What each TYPE value means and what it implies for the other columns:

```
TYPE   name            TIME decodable?  NODE decodable?  notes
-----  --------------  ---------------  ---------------  ------------------
v1     time-based      yes (60-bit)     yes (MAC/fake)   privacy-sensitive
v2     DCE security    variant layout   variant layout   embeds uid/gid; rare
v3     name (MD5)      no               no               hash bits, deterministic
v4     random          no               no               the common case
v5     name (SHA-1)    no               no               deterministic, stronger
nil    special         -                -                all zero bits
(else) invalid/other  -                -                malformed or foreign variant
```

Two consequences worth internalizing: only the time-carrying versions answer "when was this created", and only they leak a node identity. Everything else in a UUID string is opaque payload — which is exactly why structure inspection is occasionally necessary and otherwise ignorable.

### Variants in the wild

```
DCE        RFC 4122 — virtually everything modern (databases, k8s, APIs)
NCS        Apollo NCS ids from the 1980s — museum pieces, old data only
Microsoft  COM CLSIDs, .NET Guids, Windows event/registry ids
other      reserved encodings; usually a sign of corruption
```

A Microsoft-variant GUID can still carry a meaningful version nibble, so uuidparse reports both; tools that assume "UUID ⇒ DCE" misread Windows-ecosystem identifiers. Spotting the variant is the first step when debugging cross-platform id mismatches (e.g. a .NET `Guid.ToByteArray` ordering surprise, which is an *endian* issue of the wire format, not the string form).

### Reading typical output

```
$ uuidparse 7d444840-9dc0-11d1-b245-5ffdce74fad2 $(uuidgen) 00000000-0000-0000-0000-000000000000
UUID                                  VARIANT  TYPE   TIME                     NODE
7d444840-9dc0-11d1-b245-5ffdce74fad2  DCE      v1     1998-02-19 21:22:04+...  5f:fd:ce:74:fa:d2
e3c89b41-9a2f-4c7e-a6d3-1f5b2c9d8e01  DCE      v4     -                        -
00000000-0000-0000-0000-000000000000  nil      nil    -                        -
```

The v1 row shows a genuine MAC-derived node (`5f:fd:ce:74:fa:d2`) — with the multicast bit clear, a real hardware address; a generated-elsewhere v4 row has nothing to decode; the all-zero UUID is reported as `nil`. Version nibbles outside 1-5 still report their variant with an unknown type.

### Scripting surface

Output follows the util-linux "smart columns" convention (`-o` to select columns, `-n` to drop headers, `-J` for JSON), and with no operands it reads UUIDs from stdin — so it pipes naturally out of `uuidgen`, log greps, or database dumps.

```
stdin/args ──> libuuid parse ──> column formatter (table / raw / JSON)
```

### Input formats worth normalizing

UUIDs travel in many costumes; `uuidparse` accepts the canonical dashed-lowercase form and tolerates case, but pipelines feeding it from heterogeneous sources should normalize first:

```bash
sed -E 's/[{}]//g; s/^urn:uuid://I; s/([0-9a-fA-F]{8})([0-9a-fA-F]{4})/\1-\2/' \
  | tr 'A-F' 'a-f' < raw_ids.txt | uuidparse
```

Braces (`{...}`), URN prefixes (`urn:uuid:`), and the 32-hex no-dash form all appear in the wild; a three-line normalizer beats per-tool surprises.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-o, --output <list>` | Comma-separated columns: `UUID`, `VARIANT`, `TYPE`, `TIME`, `NODE`. |
| `-J, --json` | JSON output format (stable machine interface). |
| `-n, --noheadings` | Suppress the header row for clean scripting output. |
| `-h, -V` | Help / version. |

## Usage Patterns

```bash
# Classify ids collected from an application log
grep -oE '[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}' app.log | sort -u | uuidparse
```

```bash
# Are these identifiers leaking host identities?
uuidparse -o UUID,TYPE,NODE 7d444840-9dc0-11d1-b245-5ffdce74fad2
```

```bash
# Machine-readable report for a data-quality check
uuidgen | uuidparse -J
```

```bash
# Validate a batch: invalid entries surface as variant/type invalid
uuidparse < candidate_ids.txt
```

```bash
# Prove a timestamp embedded in a legacy id (v1 decode)
uuidparse 7d444840-9dc0-11d1-b245-5ffdce74fad2
```

```bash
# Quick sanity check in a shell one-liner
uuidgen -t | uuidparse -n -o TYPE,NODE
```

```bash
# Detect nil placeholders in an export before import
uuidparse -n -o UUID,VARIANT < export.csv > parsed; grep nil parsed
```

```bash
# Compare vendor GUIDs: which are Microsoft-variant?
uuidparse -o UUID,VARIANT,TYPE < guids.txt
```

```bash
# Prove an id is deterministic: same name-based UUID re-derived
uuidparse 6ba7b810-9dad-11d1-80b4-00c04fd430c8   # the RFC 4122 DNS namespace UUID
```

```bash
# Feed ids straight from a Postgres dump line by line
cut -d'|' -f2 export.tbl | uuidparse -n -o UUID,TYPE
```

```bash
# Spot node-colliding v1 ids (same MAC reused across cloned VMs)
uuidparse -n -o NODE,UUID < ids.txt | awk '{print $1}' | sort | uniq -d
```

```bash
# JSON ingest for a data-quality dashboard
uuidparse -J < ids.txt | jq '.uuid[] | select(.variant=="invalid")'
```

## Nuances and Gotchas

- **`invalid` is reported, not fatal.** Malformed strings appear as a row marked invalid rather than a hard tool failure — scripts must filter on the VARIANT/TYPE column, not rely on exit status alone.
- **TIME/NODE columns are mostly decoration for v4.** Only v1/v2 UUIDs decode to a timestamp and node; for random ids those columns are dashes. Interviews often trip on "can you get the creation time from this UUID?" — only for v1/v2.
- **Node may be a fake MAC.** A v1 UUID generated on a machine without a usable hardware address (or by privacy-conscious code) carries a random node with the multicast bit set; treat "MAC address" conclusions with that caveat.
- **v2 is rare and weird.** DCE-security UUIDs embed a POSIX user/group id in the `time_low` field; decoding tools show a type but the timestamp interpretation differs — don't over-trust TIME for v2.
- **Microsoft-variant GUIDs are common in the wild** (COM CLSIDs, some Windows artifacts) and their version nibble semantics still apply, but tooling that assumes RFC 4122 may mis-handle them.
- **Case and braces.** `uuidparse` accepts the canonical lowercase-with-dashes form; forms like `{...}`, uppercase, or URN (`urn:uuid:`) handling varies by libuuid release — normalize input (strip braces, lowercase) in pipelines.
- **Not a validity oracle for *uniqueness*.** It classifies structure; a perfectly-formed v4 UUID can still be duplicated by a buggy generator. Structure ≠ guarantee.
- **v1 timestamps have a fixed epoch.** The 60-bit field counts 100 ns ticks from 1582-10-15 — not Unix epoch — which is why tools (not mental math) should decode it, and why uuidparse's TIME column is the trustworthy rendering.
- **stdin behavior is the scripting sweet spot.** With no file arguments uuidparse reads ids from standard input one per line; forgetting this and passing a filename as an "id" yields an invalid row instead of an error — filter your inputs before the pipe.
- **JSON keys follow the column names.** With `-J`, consume `variant`/`type`/`time`/`node` fields (lowercase) as reported by the tool on your target release; don't hardcode expectations without checking the installed man page.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Parsing/reporting succeeded (invalid *inputs* are reported in the output, not via exit status). |
| nonzero | Output/IO failure (e.g. cannot open output, malformed options). |

## Related Commands

- [`uuidgen`](./uuidgen.md) — generates UUIDs; the natural producer whose output this tool classifies.
- [`findfs`](./findfs.md) — resolves a *filesystem* LABEL/UUID to a device — UUIDs in the block-device world.
- [`blkid`](./blkid.md) — lists block-device signatures including filesystem UUIDs.
- [`../../reference/man-pages.md`](../../reference/man-pages.md) — libuuid's API and related section-3 documentation.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: Given the string `e3c89b41-9a2f-4c7e-a6d3-1f5b2c9d8e01`, what can you say without tools?

The version nibble is `4` (random) and the variant nibble `a` marks RFC 4122 — so it is a v4 random UUID; no timestamp or MAC is encoded, and uniqueness rests entirely on the generator's randomness. Reading those two nibbles is the core skill `uuidparse` automates.

### Q: A security review flags v1 UUIDs in your API logs. What exactly leaks and what is the fix?

v1 embeds the generating node's MAC address (or a random node if none was available) and a high-resolution timestamp, so logs correlate infrastructure identity and generation time across services. Fix by generating v4 (or the newer reordered time variants with randomized node fields), and scrub existing ids where the MAC itself is sensitive.

### Q: How would you use uuidparse in a data-validation pipeline?

Pipe candidate identifiers through it and gate on the output columns: VARIANT `invalid` for malformed strings, `nil` for placeholder zeros, and TYPE to enforce policy (e.g. require v4). Use `-n -o` for clean scripting output or `-J` when the downstream consumer is a program; filter on columns rather than exit codes since invalid inputs are reported, not fatal.

### Q: Can you recover the creation time of any UUID? Explain precisely.

Only for v1 and v2: their 60-bit time field encodes 100 ns ticks since 1582-10-15, which uuidparse renders as a date/time. v3/v5 are hash-derived (their "time" bits carry hash output), v4 is random — their timestamps are meaningless. A common interview trap is assuming "UUIDs contain creation time"; that's a property of specific versions, not of the format.

### Q: What is the nil UUID and where do you meet it?

The all-zero UUID (`00000000-0000-0000-0000-000000000000`), parsed as variant/type `nil`. It appears as a default/placeholder value in databases, APIs, and configs (Go's zero `uuid.UUID`, empty PostgreSQL uuid columns) — uuidparse makes such values easy to detect when cleaning data feeds.

### Q: Why does uuidparse report `invalid` in the table instead of failing?

So batch validation doesn't die on the first bad row: one pass over a corpus yields a full classification report, with malformed entries visible inline. Exit status stays reserved for tool-level failures (I/O, usage), keeping it composable in pipelines — the same philosophy as `sort` on unsorted garbage input.

### Q: Two services log different UUIDs for "the same" object. How can uuidparse help explain the mismatch?

Decode both: if one is v1 and the other v4, they were generated by different code paths with different semantics (clock-derived vs random) — never byte-comparable. If both are v3/v5 with the same type, they hash (namespace, name) pairs, so a mismatch means different namespaces or different canonical names (case, slashes). If one shows the Microsoft variant, you are comparing a .NET Guid with an RFC 4122 UUID and may be facing the well-known byte-order quirk of Guid serialization. Structure inspection turns "ids don't match" into a named, fixable cause.

### Q: Where does uuidparse sit relative to blkid and findfs when the word "UUID" appears in an incident?

Different namespaces of UUIDs: uuidparse classifies *abstract* identifiers (API objects, logs), while blkid/findfs resolve *filesystem* UUIDs recorded in superblocks to devices. Correlating a filesystem UUID from `blkid` output through uuidparse tells you its version (usually v4-random for ext4/xfs, sometimes v1 from old tooling) — useful narrative, but the actual device lookup goes through blkid/findfs, not the parser.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/uuid-runtime/uuidparse.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
