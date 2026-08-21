# journald

`systemd-journald` is the structured logging daemon that ships with systemd. It replaced the traditional `syslog`-to-`/var/log/messages` pipeline with an indexed, structured, append-only binary log stored under `/var/log/journal/`. This page covers the binary format, the query API, the forwarding to legacy syslog, and the failure modes that make journald controversial on production servers.

## Why a Binary Log

The pre-systemd Unix pipeline was: each daemon `write(2)`s UTF-8 lines to `/dev/log`, a `syslogd` socket-reads them, prepends a timestamp and a facility/severity, and appends a line to a flat text file. The format is grep-friendly but loses information:

- No structured fields: every value must be regex-extracted.
- No priority/severity indexing; to find `error` messages you scan the whole file.
- No reliable rotation: `logrotate` truncates, leading to lost lines if a writer was mid-`write`.
- No native correlation with kernel events or systemd units.

journald stores each entry as a serialized record with named fields of typed values, indexed by `_HOSTNAME`, `_SYSTEMD_UNIT`, `_PID`, `PRIORITY`, and time. The query tool `journalctl` uses these indexes to filter millions of entries in milliseconds.

## The On-Disk Format

The journal is a set of files in `/var/log/journal/<machine-id>/`, one per boot and rotated by size:

```text
/var/log/journal/<machine-id>/
├── system.journal             ← currently being written
├── system@<uuid>.journal       ← rotated, sealed
├── system@<uuid>.journal
├── user-1000.journal           ← per-UID journal (if persistent user logging enabled)
└── ...
```

Each file is an `sd_journal` archive consisting of:

1. A **header** (`struct Header` in `src/libsystemd/sd-journal/journal-file.h`) — magic bytes, version, machine-id, boot_id, seqnum, file size, arena offsets, and a hash table seed.
2. An **object table** — variable-size objects: `OBJECT_DATA` (a key-value pair, with hash and payload), `OBJECT_FIELD` (a key string), `OBJECT_ENTRY` (a per-record entry listing field pointers + timestamps), `OBJECT_DATA_OBJECT`, `OBJECT_ENTRY_ARRAY`, and `OBJECT_TAG`.
3. **Hash tables** — three of them: key (`field` hash table), entry (`identifier` hash table for entry lookup by seqnum), and data (`data` hash table by content hash).
4. An **entry array** — append-only array of `OBJECT_ENTRY_ARRAY` chained nodes, indexed by `seqnum`.

The format is documented as `journal-file.h` in the systemd source and is intentionally stable across systemd versions; `journalctl --file=` can read journals from older systemd versions transparently.

The `OBJECT_DATA` hash table makes deduplication cheap: every instance of `PRIORITY=6` writes the same hash table entry once and references it. The `OBJECT_FIELD` table deduplicates the key string itself, so an entry with 50 fields costs roughly 50 4-byte pointers + the unique value bytes.

## Sealing and Forward-Secure

journald supports **Forward-Secure Sealing (FSS)**: each journal file is sealed periodically (default every 10 minutes) with a key derived from a periodic rotation of HMAC keys. The seal is computed only over entries written since the previous seal, so a tampering attacker cannot retroactively modify old sealed entries even if they obtain the current key.

```bash
# Initialize FSS
journalctl --setup-keys
# Returns a verification key. The secret key is stored in
# /var/log/journal/<machine-id>/fss.

# Verify a journal against a key
journalctl --verify --verify-key=<key>
```

FSS is opt-in because the verification is one-way: you can prove the journal was not modified after sealing, but you cannot recover the modification. Production deployments that require log integrity (PCI, HIPAA) should enable FSS.

## Writing to journald

Daemons write via three interfaces:

1. **`sd_journal_print()`** — libsystemd C API; similar to `syslog()`.
2. **`systemd-cat`** — pipe stdin into the journal: `./my-script.sh | systemd-cat -t myscript -p info`.
3. **`/dev/log` socket** — syslog-protocol text is parsed, mapped to fields, and stored; this is the default path used by glibc's `syslog(3)`.

Each entry is a set of fields. The conventional fields are:

| Field | Meaning |
|------|---------|
| `MESSAGE`       | The human-readable message string |
| `PRIORITY`      | syslog severity (0–7) |
| `SYSLOG_FACILITY` | syslog facility (0–23) |
| `SYSLOG_IDENTIFIER` | Tag (typically the daemon name) |
| `_PID`          | Process ID of the writer |
| `_UID`          | Effective UID |
| `_GID`          | Effective GID |
| `_COMM`         | Comm name (process name truncated to 15 chars) |
| `_EXE`          | Path to the executable |
| `_CMDLINE`      | Full process command line |
| `_SYSTEMD_UNIT` | systemd unit the writer was in |
| `_SYSTEMD_CGROUP` | cgroup path |
| `_SYSTEMD_SLICE`| slice containing the unit |
| `_HOSTNAME`     | Hostname at write time |
| `_BOOT_ID`      | Boot UUID — changes on each boot |
| `_MACHINE_ID`   | Machine UUID — stable across boots |
| `_TRANSPORT`    | `journal`, `stdout`, `syslog`, `driver`, `audit`, `kernel` |

Custom structured fields are first-class: any field that doesn't start with `_` (reserved for trusted fields journald sets itself) is preserved. From a Python application:

```python
import systemd.journal

logger = logging.getLogger("myservice")
logger.addHandler(systemd.journal.JournalHandler())
logger.setLevel(logging.INFO)

# Structured fields passed as kwargs
logger.info("user login", USERID=42, IP="10.0.0.1",
            EXTRA={"auth_method": "mfa"})
```

The journal entry will then be queryable as `journalctl USERID=42`.

## Querying: journalctl

```bash
# Filter by structured field
journalctl _SYSTEMD_UNIT=nginx.service

# Filter by priority (0=emerg .. 7=debug)
journalctl -p err           # only err, crit, alert, emerg
journalctl -p warning       # warning and above
journalctl -p 3             # equivalent to -p err

# Time range
journalctl --since "2026-08-01 09:00" --until "2026-08-01 17:00"
journalctl --since "1 hour ago"
journalctl --since yesterday

# Across boots
journalctl --list-boots
journalctl -b -1            # previous boot
journalctl -b current       # current boot only

# Follow (like tail -f)
journalctl -f

# JSON output for programmatic consumption
journalctl -o json          # one JSON object per line
journalctl -o json-pretty
journalctl -o json-sse      # Server-Sent Events stream

# Export and re-import
journalctl -o export | xz > journal.xz
journalctl --file=imported.journal
```

The `-o json` output is the canonical way to integrate with log aggregators like Loki, Elasticsearch, or Datadog. Each entry is a JSON object with all fields including the trusted ones.

## Forwarding to Syslog and Kernel

journald forwards to legacy syslog (rshsyslog, rsyslog) via the `/run/systemd/journal/syslog` socket when `ForwardToSyslog=yes` (default `yes` on most distributions). It also forwards to TTYs, to the kernel printk ring (`ForwardToKMsg`), and to the console.

The kernel itself writes to journald: every `printk()` that doesn't get consumed by `dmesg` is captured by `systemd-journald` via the `/dev/kmsg` device. The `_TRANSPORT=kernel` field distinguishes these entries from userspace logs.

## Failure Modes and Criticisms

1. **Disk space exhaustion.** journald's defaults (`SystemMaxUse=`) leave the journal unbounded up to the smaller of 4 GB or 10% of the filesystem. On hosts with low disk space and chatty services, this fills `/var/log` and crashes journald. Set `SystemMaxUse=500M` in `/etc/systemd/journald.conf`.

2. **Slow queries on multi-month journals.** The hash tables index by field value, not by substring. A `journalctl | grep "user 42"` falls back to a full scan. Use `journalctl USERID=42` instead.

3. **Append-only format means corruption requires rotation.** If a journal file is truncated by an external process, journald does not recover — the file must be moved aside and a fresh one created. `journalctl --verify` detects but does not fix corruption.

4. **Logs not visible until journald is running.** Early-boot logs (before journald starts) are buffered in the kernel printk ring and lost if it overflows. The `journalctl --boot=0 _TRANSPORT=kernel` will show what survived.

5. **journald rate-limiting drops messages.** Default `RateLimitIntervalSec=30s` and `RateLimitBurst=10000` drop messages from a single unit exceeding 10000 entries per 30 seconds. Set `RateLimitIntervalSec=` to `0` to disable (carefully).

6. **The binary format is opaque to standard tools.** `grep`, `awk`, `sed`, `less` do not work on `system.journal` directly. Operations teams that built monitoring pipelines around tailing `/var/log/messages` find themselves re-architecting. The standard mitigation is `journalctl -f -o json | <aggregator>`.

## Networked Aggregation

For multi-host log aggregation, two patterns are common:

1. **`systemd-journal-remote`** — pulls/pushes journals over HTTPS to a central server that stores them in the same format. The remote server exposes `journalctl --machine=foo` to query any host's logs.
2. **`journalctl -o json | fluent-bit`** — converts to JSON-lines and ships to Loki, Elasticsearch, or Splunk. This loses the on-disk format but is more compatible with existing pipelines.

```bash
# Run on each host
journalctl -o json -f | \
    fluent-bit -i stdin -o loki -t placement-prep.loki
```

## References

- [systemd.journald(8)](https://www.freedesktop.org/software/systemd/man/systemd-journald.html)
- [journalctl(1)](https://www.freedesktop.org/software/systemd/man/journalctl.html)
- Lennart Poettering, "[Journal: Rationale, Design, and Implementation](https://systemd.io/JOURNAL-FILES/)"
- [systemd source: `src/libsystemd/sd-journal/journal-file.h`](https://github.com/systemd/systemd/blob/main/src/libsystemd/sd-journal/journal-file.h)
- [LWN: "A look at journald" (2012)](https://lwn.net/Articles/510048/)
- [Forward-Secure Sealing](https://systemd.io/JOURNAL_SECURITY/)
