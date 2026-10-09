# tload — ASCII graph of the system load average

## Overview

`tload` draws the system load average as a live ASCII graph in your terminal: a text line with the 1/5/15-minute averages on top and a scrolling column-per-sample chart underneath. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/tload`, reads one file — `/proc/loadavg` — and is one of the oldest tools in the package (Branko Lankester, David Engel, and Michael K. Johnson wrote it for the original procps in the early 1990s).

Its niche is the zero-setup load history: on any box, over any slow SSH link, `tload` turns the three numbers from `uptime` into a trend line without gnuplot, node exporters, or scrollback archaeology. When the CPU spiked at 14:32 and you only thought to look at 14:50, `tload` has been drawing the whole time.

`tload` is often confused with `uptime`/`w` (which print the current averages once — same source data, no history) and with `top` (per-process detail; tload has no notion of processes at all). It is also mistaken for a data logger: its output is terminal control sequences, not parseable records.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/tload |
| First appeared | original procps, early 1990s (Lankester, Engel, Johnson) |
| Standards | None; Linux `/proc/loadavg` |

## Synopsis

```
tload [options] [tty]
```

Common one-line forms:

```
tload                # full-screen graph, default scale, 1-second refresh
tload -d 5           # sample every 5 seconds
tload -s 8           # more sensitive: 1.00 of load = 8 screen rows
tload -s 2 -d 1      # fast, coarse view while stress-testing
```

## How It Works

### Repainting one screen forever

`tload` never scrolls and never prints newlines. Each update it emits a cursor-home escape, then redraws the whole screen by wrapping at terminal width:

```
row 0   0.89, 0.30, 0.14                     <- three load averages
rows 1..n       the graph area
```

The graph area below row 0 is a column-per-sample strip chart:

```
 0.89, 0.30, 0.14                                   <- row 0: 1/5/15-min averages
----------------                                    <- tick line: 5.00 load
                                                    (blank rows between ticks)
----------------                                    <- tick line: 4.00 load

----------------                                    <- tick line: 3.00 load

----------------                                    <- tick line: 2.00 load

----------------                                    <- tick line: 1.00 load
              **
         *******                                    <- one '*' bar per sample,
    ************                                       rising from the bottom row
```

- **One column per sample.** Each refresh appends one column; history fills left to right, and once the terminal width is exhausted, old samples drop off the left edge. The history buffer lives inside the tload process — scrolling your terminal back shows nothing, and the redrawn screen *is* the history.
- **Bar height encodes load.** Each sample draws `*` characters from the bottom row upward; the height tracks the **one-minute** average scaled by the `-s` value (the text row shows all three averages, but the chart plots the first).
- **Tick lines mark whole units of load.** Every `-s` rows the kernel's load has climbed by 1.00, tload draws a horizontal `-` grid line across the history. With `-s 4`, one full load unit is 4 screen rows; the line four rows up the screen is load 1.00, eight rows up is 2.00.
- **Default scale is 24.** On a default-height terminal the single tick line lands on row 0 — underneath the load-average text — so a default `tload` shows no visible grid, and the entire screen height corresponds to about 1.00 of load. Idle machines therefore draw a single `-`/`*` row at the bottom; anything spiking to load 1.0+ needs a smaller `-s` to stay on-screen.

### Reading the numbers row

The text line is `uptime`'s output living in your graph, and the three numbers' *relationship* is diagnostic on its own:

- `1min ≫ 15min` — something started recently; the chart's right edge shows what.
- `15min ≫ 1min` — the burst is over; the chart is already calm while the headline number still looks scary.
- all three high, CPU mostly idle — D-state (IO) load; the chart keeps climbing as long as the stall does.

Because the chart plots only the 1-minute figure, the 5/15 numbers in the text row are your memory of the longer past — tload gives you the window, the text row gives you the trend context.

### Scaling, precisely

Measured behavior on a 24-row terminal (procps-ng 4.0.4):

- A sample's bar is `⌊1-minute load × scale⌋` rows of `*`, drawn upward from the bottom row.
- Horizontal tick lines sit every `scale` rows; the lowest tick marks load 1.00, the next 2.00, and so on. With `-s 4` the ticks land at rows 20/16/12/8/4 for loads 1–5.
- The default scale is 24 — one full screen per 1.00 of load — so the only tick coincides with the text row and you see no grid at all; any load ≥ 1.00 runs off the top of the chart.
- Choosing `-s`: cores/2 for a coarse "are we busy" view, `-s 4`-`-s 8` for typical servers, large values (10–20) for small VMs where tenths of load matter.

Sanity check with a synthetic load: four busy-loops drive the 1-minute average up ~0.07/second; with `-s 4 -d 1` the newest column gains one `*` roughly every three to four seconds, matching the ramp, while the 5- and 15-minute numbers in the text row barely move.

### The tty operand

The optional `[tty]` argument is an *output* device: `tload` prints to the named terminal (e.g. `/dev/pts/2`) or, without one, to its own controlling terminal. That makes it usable as a crude broadcast — a long-running graph on a shared demo screen — though anything fancier wants a real dashboard.

### Refresh timing

`-d` sets the seconds between samples and is implemented with `alarm(2)`: tload sleeps on SIGALRM between redraws. The documented BUGS section notes the edge: `-d 0` sets `alarm(0)`, which cancels the alarm, so the display simply never updates.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d, --delay <secs>` | Seconds between samples (default refresh; `0` freezes per the alarm bug) |
| `-s, --scale <num>` | Rows per 1.00 of load — *smaller value = larger scale* |
| `-h`, `-V` | Help / version |

The scale inversion is the classic trap: `-s 2` makes bars twice as tall as `-s 4` (fewer characters between graph ticks = more sensitive), which is backwards from what "scale" means in most plotting tools.

## Usage Patterns

```bash
# Watch a deployment's load profile while it happens
tload

# A busy many-core box: full height = 1.0 is too coarse, zoom out
tload -s 2

# A small VM where 0.1 matters: zoom in
tload -s 15

# Slow the sampling during a long soak test
tload -d 30 -s 4

# Leave a live graph on a shared ops terminal
tload -s 4 /dev/pts/2

# Compare with the numbers tool it visualizes
uptime && tload -d 2

# In scripts, skip tload: read the same file it does
while :; do awk '{print systime(), $1}' /proc/loadavg >> load.log; sleep 60; done

# One-shot load snapshot when tload is overkill
cut -d' ' -f1-3 /proc/loadavg

# Graph while a stress test runs, from another terminal
stress-ng --cpu 8 --timeout 300 & tload -s 2 -d 1

# Correlate the graph with the raw file it renders
cat /proc/loadavg ; tload -s 4 -d 1

# Give a coarse-but-visible view on a tiny 40-column window
tload -s 6

# Keep a graph running in a detached pane for the whole release cycle
tmux new-session -d -s loadgraph 'tload -s 4 -d 5'   # attach: tmux attach -t loadgraph

# Sanity-check a load spike report before trusting the alert system
tload -s 4 ; uptime ; ps -eo stat,comm | grep -c '^D'

# Teaching/demo: show how a busy loop bends the 1-minute needle
( while :; do :; done ) & tload -s 4 -d 1

# Watch the needle fall once the burst ends (damping in action)
kill %1 ; tload -s 4 -d 1

# Two scales side by side in tmux panes: zoomed and coarse
tmux split-window -h 'tload -s 4 -d 1' ; tmux split-window -v 'tload -s 12 -d 1'

# Spot-check the load on a machine you just SSH'd into, then leave it running
uptime ; tload

# Demonstrate the alarm bug documented in the man page (screen never updates)
tload -d 0   # Ctrl-C to escape
```

## Nuances and Gotchas

- **Output is not pipe-friendly.** Even redirected to a file, tload writes cursor-home escapes and NUL-padded screen dumps (verified: every frame is `ESC[H` plus a fixed-size screen buffer). It is a terminal display, not a logger; for data, poll `/proc/loadavg` yourself or run `vmstat`/`sar`.
- **`-d 0` freezes the display.** Documented BUGS: the delay is handed to `alarm(2)`, and `alarm(0)` cancels the timer, so the screen never refreshes. Use `-d 1`, not `-d 0`, for "as fast as possible".
- **The graph plots the one-minute average.** That number is heavily smoothed by design — a 100%-CPU burst that just started moves it slowly (roughly, a new task adds 1/60th per second to the 1-minute figure). People stare at tload right after starting a stress test and conclude "it's not loading" — it is; the needle is damped. `-s` adjusts the *y-axis*, never the damping.
- **Load is system-wide and un-namespaced.** `/proc/loadavg` reflects the whole host (or the host behind lxcfs fakery in containers), so tload inside a container graphs the host, not the container's cgroup.
- **Load includes D-state tasks.** Disk stalls inflate the graph with idle CPUs showing — same interpretation rules as `uptime`/`top` load figures.
- **History fills, then scrolls.** Columns append left to right; once the width is exhausted the strip chart scrolls, oldest sample dropping off the left edge. There is no pause, no rewind, and no zoom — the visible window is all the history there is.
- **History dies with the process.** The sample buffer lives inside tload: close the SSH session, kill it, or detach, and the accumulated graph is gone with it. Long histories need a real recorder.
- **Default refresh is one second.** Without `-d`, a new column appears every second; on slow links `-d 5` cuts the traffic fivefold, since every frame is a full screen repaint.
- **No config, no color, no units.** tload predates all of it and has stayed deliberately minimal — three flags total. If you need them, that's the cue to graduate to `vmstat -t` logging or time-series tooling.
- **Geometry assumptions.** The redraw assumes the terminal honors cursor-home and wraps at its width; with stdout not a tty, tload falls back to an 80-column screen image (verified), so piping it into anything produces 80-column escape-sequence soup rather than an error.

## Exit Status

No exit-status table is documented. tload runs until signaled (SIGINT/SIGTERM); error paths (unknown option, unwritable tty) fail with a usage/error message and nonzero status before any graph is drawn.

## Related Commands

- [`uptime`](./uptime.md) — the same three averages, one snapshot, no history.
- [`w`](./w.md) — uptime plus who is logged in and what they run.
- [`vmstat`](./vmstat.md) — parseable interval stats (run queue, CPU, IO), the scriptable counterpart.
- [`top`](./top.md) — from load trend to the processes causing it.
- [`ps`](./ps.md) — identify D-state tasks when the graph climbs but CPU idles.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — what load average measures in the scheduler's terms.

## Interview Questions

### Q: What exactly does the load average number that tload graphs represent?

Linux load average is an exponentially damped moving average of tasks in the runnable state *plus* tasks in uninterruptible sleep (D state) — a design inherited from BSD. It is not CPU utilization and not a queue length snapshot. That is why a disk-stalled server can show load 50 on an idle CPU: the D-state tasks count. The 1/5/15 numbers are the same metric over different damping horizons, and tload charts the 1-minute one.

### Q: Why does the man page say a smaller `-s` value represents a larger scale?

`-s` is the number of screen rows between graph ticks — the characters per 1.00 of load. With `-s 4` a full load unit occupies 4 rows; with `-s 2` it occupies 2, so the same load draws twice as tall a bar: the chart is more zoomed in ("larger scale" on the y-axis). The default of 24 makes the full terminal height equal to 1.00, which suits idle desktops but clips any real server load — a candidate who has actually run tload remembers to drop `-s` on busy boxes.

### Q: tload's output to a log file is garbage. Why, and what do you use instead?

tload repaints a terminal: each frame is a cursor-home escape sequence followed by a fixed-size screen image (it never prints newlines), so the "log" is an overlay stream, not records. For retention, sample the same source directly — `awk '{print systime(), $1}' /proc/loadavg` on a loop, `vmstat -t 60`, or `sar -q` — all of which produce timestamped parseable lines that can be graphed after the fact.

### Q: What does `tload -d 0` do, and what does that tell you about the implementation?

Nothing, forever: the BUGS section explains that `-d` feeds `alarm(2)`, and `alarm(0)` cancels the pending alarm, so no SIGALRM ever arrives and the screen never updates. It is a nice window into the tool's age — refresh timing via signals rather than a poll loop — and a reminder that zero-valued intervals are usually special-cased badly in old UNIX tools.

### Q: How would you reconstruct what load looked like an hour ago on a box with no monitoring?

You cannot from tload — its history buffer is in-process, sized to the terminal width, and gone the moment it exits (closing the SSH session loses everything). Post-hoc reconstruction needs recorded data: systemd journal/sar archives, `vmstat` history, or CloudWatch-style metrics. The operational lesson is to start `tload` (or better, a `sar`/`vmstat` logger) *before* the load happens; tload is for watching, not remembering.

### Q: On a 64-core server, load 64 is "normal". How do you make tload's default display usable?

The default scale makes the screen height equal 1.00, so load 64 runs far off the top. Scale the view: `-s 1` gives one row per load unit (a 64-high bar only fits with terminal height to spare, but ticks every row keep the trend readable), or normalize by sampling `awk '{print $1/NR}'`-style per-core load from `/proc/loadavg` yourself. The deeper point for interviews: load averages must always be interpreted relative to core count.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/tload.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
