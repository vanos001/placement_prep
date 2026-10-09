# lsirq — interrupt counter table from /proc/interrupts

## Overview

`lsirq` reads the kernel's interrupt accounting file (`/proc/interrupts`) and prints it as a regular table: one row per interrupt source, per-CPU hit counters, and selectable/sortable columns for scripting. It is the non-interactive sibling of `irqtop`, the curses-based live view of the same data, and both landed in util-linux in the early-2020 releases. Before `lsirq` existed, the only way to see interrupt distribution was to read the raw procfs file and cope with its arch-dependent, whitespace-unfriendly layout by hand.

The tool is deliberately thin: it adds column selection, sorting, and machine-readable output formats on top of a kernel file that every Linux system already exports. On Debian bookworm it ships in the `util-linux-extra` split package — minimal container images often lack it even though the rest of util-linux is present.

It is often confused with `irqtop` (same data, interactive top-style UI), with raw `cat /proc/interrupts` (no column handling at all), and with `watch cat /proc/interrupts` shell one-liners (cumulative counters with no delta computation).

| Field | Value |
| --- | --- |
| Package | util-linux-extra (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/lsirq |
| First appeared | util-linux early-2020 releases (2.37 era), together with irqtop |
| Standards | None — Linux procfs-specific |

## Synopsis

```
lsirq [options]
```

Common one-line forms:

```
lsirq                        # default table: per-CPU counters, IRQ, NAME
lsirq -S TOTAL               # sort by a named column
lsirq -J                     # JSON output for scripts
watch -n1 'lsirq -o IRQ,TOTAL,NAME'   # poor man's irqtop
```

## How It Works

### The data source

Everything comes from `/proc/interrupts`, maintained by the kernel's generic IRQ layer. A real sample from a 2-vCPU x86_64 VM:

```
           CPU0       CPU1
  0:          9          0   IO-APIC   2-edge      timer
  1:          0          0   IO-APIC   1-edge      i8042
```

The first field is the IRQ number (or a pseudo-counter label such as `NMI`, `LOC`, `ERR`), the middle fields are per-CPU counters, and the trailing text is the interrupt controller/driver name plus the trigger type (`edge`, `level`). The exact column count and naming differ per architecture (x86 APIC, ARM GIC, s390 I/O interrupts), which is precisely why a normalizing tool is useful.

`lsirq` parses that file, aggregates each interrupt line into a row, and renders it through the same table engine (libsmartcols) used by the other util-linux `ls*` tools:

```
/proc/interrupts
      │ parse (arch-independent view)
      ▼
 rows: per-IRQ CPU0..CPUn counters + IRQ + NAME
      │
      ├── -o/--output-all   select columns
      ├── -S                sort by column
      └── output formats:   table (default), -l list, -r raw, -J JSON
```

### Views and columns

The default table shows the per-CPU counters plus `IRQ` and `NAME`; `TOTAL` and the other columns are available through `-o`/`--output-all`. `-l` switches to list format (one field per line), `-r` strips padding for reliable parsing, `-n` drops the header row, and `-J` emits JSON with the same column names as keys. `-S` sorts by any named column, and `-w` widens the per-CPU columns so large counters do not shift the layout.

### irqtop: the interactive twin

`irqtop` ships in the same package, uses the same reader, and adds a curses loop: periodic refresh with computed deltas, interactive sorting, and an interval setting. Use `lsirq` in scripts and snapshots, `irqtop` when watching a live problem.

### Pseudo-counters: rows with no IRQ number

Not every row of `/proc/interrupts` is a real device line. The kernel also reports architectural counters that have no PIC slot, printed in the same tabular shape:

```
NMI:      0          0     Non-maskable interrupts
LOC:  51234      48102   Local timer interrupts
ERR:      0                Machine check errors
MIS:      0                Timer broadcast interrupts
```

`LOC` (local APIC timer) and function-call IPI rows are usually the biggest counters on an idle x86 server and are normal; `ERR`/`MIS` at non-zero values on APIC systems are worth investigating. `lsirq` keeps these rows alongside device interrupts — filtering by a numeric `IRQ` column is how you separate real lines from pseudo-counters. The exact set is architecture-specific (ARM systems show `IPI0..IPI7` style rows instead), which reinforces the case for a normalizing tool.

### Affinity: why one CPU column stays at zero

The kernel routes each interrupt according to an affinity mask, writable per line in `/proc/irq/<N>/smp_affinity_list`. A row where CPU1 is permanently zero while CPU0 counts everything means the driver (or irqbalance) pinned the line to one CPU — not that the device is broken. Reading distribution is therefore a diagnostic act:

```
# Who handles IRQ 24 today?
cat /proc/irq/24/smp_affinity_list

# Pin it to CPU2 (root) and watch the column move
echo 2 > /proc/irq/24/smp_affinity_list
```

A pathological pattern lsirq makes visible: one hot core (poor spreading, cache-line contention) or round-robin spreading across all cores (irqbalance doing its job).

### Containers and permissions

`/proc/interrupts` is not namespaced — interrupt lines are a host-wide hardware concept. Inside a container `lsirq` therefore shows the host's counters (world-readable procfs), which makes it a legitimate diagnostic inside containers even though the IRQs are not "yours". The counters are cumulative since boot; there is no kernel-side reset.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-S, --sort <column>` | Sort output by a named column (e.g. `TOTAL`, `IRQ`, `NAME`) |
| `-o, --output <list>` | Comma-separated column selection (see `--help` for the supported set) |
| `--output-all` | Output all available columns |
| `-J, --json` | JSON output format, column names as keys |
| `-l, --list` | List format output (one field per line) |
| `-r, --raw` | Raw output — no column padding; safest for parsing |
| `-n, --noheadings` | Omit the header row |
| `-w, --width <num>` | Fixed width for the CPU0..CPU[N-1] counter columns |
| `-h, --help` / `-V, --version` | Help and version |

The column machinery mirrors sibling tools (`lslocks`, `lslogins`, `lsns`): learn it once and the whole `ls*` family behaves the same way.

## Usage Patterns

```bash
# Quick look at which interrupt lines are busy on this host
lsirq
```

```bash
# Sort by total hit count with wide counter columns on a 64-CPU box
lsirq -S TOTAL -w 14
```

```bash
# Machine-readable snapshot for a monitoring script
lsirq -J > "/tmp/irq-$(date +%s).json"
```

```bash
# Only the columns you care about, no header, no padding — grep-friendly
lsirq -n -r -o IRQ,NAME
```

```bash
# Delta over 10 seconds: counters are cumulative, so diff two snapshots
lsirq -o IRQ,TOTAL,NAME > /tmp/irq1; sleep 10; lsirq -o IRQ,TOTAL,NAME > /tmp/irq2
diff /tmp/irq1 /tmp/irq2
```

```bash
# Live view without irqtop installed
watch -n1 'lsirq -o IRQ,TOTAL,NAME'
```

```bash
# Inside a container: shows host-wide counters (procfs is not namespaced)
lsirq | head
```

```bash
# Find the NIC interrupt lines on a server (driver names usually appear in NAME)
lsirq -r -o IRQ,NAME | grep -i eth
```

```bash
# Feed into jq-style processing after JSON output
lsirq -J
```

```bash
# Check whether the tool is present (util-linux-extra split) before scripting it
command -v lsirq >/dev/null || echo "install util-linux-extra"
```

```bash
# Find the single busiest interrupt line right now (sort by TOTAL, take the top)
lsirq -S TOTAL -o IRQ,TOTAL,NAME | tail -3
```

```bash
# Separate real device lines from pseudo-counters (NMI, LOC, IPI rows)
lsirq -r -o IRQ,NAME | grep -E '^[0-9]+:'
```

```bash
# Confirm a pinned IRQ: one CPU column stuck at zero means affinity, not failure
cat /proc/irq/24/smp_affinity_list
```

## Nuances and Gotchas

- **Counters are cumulative since boot.** A large number does not mean "busy now". Compute deltas from two samples, or use `irqtop`/`watch` with manual arithmetic. Interviewers like this one: it catches people who read one snapshot as a rate.
- **The format is architecture-specific.** x86 lines look like `IO-APIC 2-edge timer`; ARM systems use GIC controller names, and pseudo-counters (`NMI`, `LOC`, `ERR`, `MIS`, s390 I/O lines) appear as rows with no real IRQ number. Any parser you write on top of the raw file will meet surprises; that is the parsing burden `lsirq` removes.
- **util-linux-extra split.** On Debian bookworm the tool is in `util-linux-extra`, not `util-linux`. Slim images, older CI runners, and deduplicated containers frequently lack it; check with `command -v lsirq` rather than assuming.
- **No busybox equivalent.** Busybox has no `lsirq`; embedded rescue environments fall back to raw `cat /proc/interrupts`.
- **Do not cut-parse the default table.** Column widths adapt to counter magnitude (a 64-bit counter on a long-running box is wide). Use `-r` (raw) or `-J` (JSON) for machine consumption.
- **Sort keys are columns.** `-S` takes a column name, not a field number; asking for a nonexistent column is a usage error, not a silent no-op.
- **irqtop is not a daemon.** Neither tool changes interrupt affinity or anything else — they are pure readers. Tuning lives in `/proc/irq/<N>/smp_affinity`.
- **Rows appear and disappear at runtime.** Loading or unplugging a driver adds/removes lines in `/proc/interrupts`; MSI-X NICs register dozens of lines named after PCI slots. A snapshot is valid only for the moment it was taken.
- **Per-CPU columns do not sum to TOTAL by accident.** `TOTAL` is the computed sum across CPUs for that line; if your parsing re-adds the CPU columns, expect off-by-one confusion once you realize the tool already did it.
- **Pseudo-counters dwarf device counters on idle systems.** `LOC` and inter-processor interrupt rows typically dominate; panic over them and you misread every capacity report.
- **The `NAME` field is free-form kernel text.** Driver name plus trigger mode, occasionally PCI addresses — treat it as display data, not an API.
- **irqbalance interaction.** On systems running irqbalance, expect the per-CPU distribution to change under you; pinning an IRQ manually can be undone by the daemon unless excluded in its config.
- **Watch mode granularity.** `watch -n1` recomputes deltas visually but coarsely; for per-second rates on many CPUs, snapshot with `-J` and diff programmatically — the table was designed for humans, not for rate math.

## Exit Status

- `0` — output produced successfully.
- `1` — failure: `/proc/interrupts` unreadable, unknown option, or invalid column list.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`lslocks`](./lslocks.md) — fellow procfs tabulator (`/proc/locks` + `/proc/*/fd`).
- [`lslogins`](./lslogins.md) — same table/columns/output-format conventions for account data.
- [`lsns`](./lsns.md) — same family conventions for namespace listings.

## Interview Questions

### Q: Where does lsirq get its data, and is that data namespaced?

It reads `/proc/interrupts`, the generic IRQ layer's accounting file. Interrupts are a hardware-level, host-wide concept, so the file is not namespaced: inside a container `lsirq` shows the host's counters. The counters are cumulative since boot.

### Q: You need "interrupts per second on CPU3" — how do you get that from lsirq?

Take two snapshots separated by a known interval (`lsirq -o CPU3,IRQ,NAME` twice, or `-J` for JSON), subtract per-IRQ values, and divide by the elapsed time. The kernel gives no rate; everything in `/proc/interrupts` is monotonic since boot. `irqtop` is essentially this delta computation wrapped in a curses UI.

### Q: Why does lsirq exist when you can just cat /proc/interrupts?

Because the raw file is a human dump with arch-dependent column counts, no stable field positions, mixed pseudo-counters, and whitespace that changes with counter magnitude. `lsirq` normalizes it into columns you can select (`-o`), sort (`-S`), and consume (`-r`, `-J`), which makes it composable in scripts — the same argument as for `lsblk` over `cat /proc/partitions`.

### Q: Your script works on a Debian server but fails "command not found" in a slim container image. What happened?

Debian splits rarely-used util-linux tools into the `util-linux-extra` package, and `lsirq` (with `irqtop`) is among them. Base images minimize packages, so the tool is absent even though other util-linux binaries are present. Either install the package or fall back to parsing `/proc/interrupts` directly.

### Q: What can you tell about a system from a single lsirq output?

Boot-time interrupt distribution: which devices/drivers registered interrupt lines (NAME column), how counters spread across CPUs (affinity quality), and the CPU count itself. You cannot tell current load or rate from one snapshot — only cumulative history.

### Q: What are the NMI, LOC, and IPI rows — and should you worry about them?

They are architectural pseudo-counters, not device lines: non-maskable interrupts, local APIC timer ticks, and inter-processor interrupts. On an idle server the local-timer and IPI rows are the largest numbers in the whole file and are completely normal. Persistent growth in `ERR`/`MIS` rows on APIC systems, however, indicates hardware-level trouble worth checking. Their presence in the same table is another reason a raw `cat`-based parser meets surprises.

### Q: One CPU column for a NIC interrupt reads zero forever. Broken hardware?

No — that is the affinity mask doing its job: the line is pinned to one CPU (by the driver default or irqbalance), so only that column increments. Confirm with `/proc/irq/<N>/smp_affinity_list` and, if needed, rewrite it. The interview point: zero columns indicate *routing*, while a stuck TOTAL indicates a dead line.

### Q: How do lsirq and irqbalance relate?

lsirq observes; irqbalance decides. The daemon periodically rewrites per-IRQ affinity masks to spread load; lsirq's per-CPU columns are how you verify (or audit) the result. Pinning an IRQ manually fights the daemon unless the line is excluded in its configuration — a common source of "my affinity setting keeps reverting" tickets.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux-extra/lsirq.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
