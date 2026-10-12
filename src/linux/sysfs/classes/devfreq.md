# /sys/class/devfreq

| Field | Value |
|---|---|
| Subsystem | devfreq framework (generic device frequency scaling), PM subsystem; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-devfreq` (14 What entries) |
| Since | directory September 2011; `name` November 2019; `timer` July 2020; `related_cpus` June 2025 |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/devfreq |
| Ledger ID | SYSC-devfreq |

## What it represents

One directory per devfreq object, named after the device doing frequency scaling (memory controllers, GPUs, buses). devfreq is the counterpart of cpufreq for non-CPU devices: a governor samples device load and picks an operating frequency from the device's available frequencies. The class exposes the governor choice, the frequency bounds, statistics and the polling machinery.

## Relationship to the device model

Each devfreq object wraps a registered `struct device`; the class directory is a view of that device and its name is the device name. A governor periodically samples load (via devfreq-event counters on some platforms) and re-programs the frequency within the min/max window userspace can narrow; the sysfs files are the observation and policy layer over that loop. Files appear conditionally: `polling_interval` and `timer` exist only for polling governors (the ABI names `simple_ondemand` and `tegra_actmon`), `userspace/set_freq` only for the `userspace` governor, and `related_cpus` only when a devfreq domain is closely associated with a CPU subset. `trans_stat` requires the driver to supply a frequency table.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../name` | RO | device name of the devfreq object | always | ABI, November 2019 |
| `.../governor` | RW | governor name; show or set | always | ABI, September 2011 |
| `.../cur_freq` | RO | Hz; equals target_freq if driver has no get_cur_freq | always | ABI, September 2011 |
| `.../target_freq` | RO | Hz; governor-predicted next frequency | always | ABI, September 2012 |
| `.../trans_stat` | RW | transition table (time per state, counts); write 0 resets; -EFBIG if bigger than PAGE_SIZE | needs profile freq table | ABI, October 2012 |
| `.../available_frequencies` | RO | Hz list, snapshot not limited by min/max | always | ABI, October 2012 |
| `.../available_governors` | RO | governor name list | always | ABI, October 2012 |
| `.../min_freq` | RW | Hz lower bound; 0 = don't care; overrides governors | always | ABI, January 2013 |
| `.../max_freq` | RW | Hz upper bound; overrides governors and min_freq | always | ABI, January 2013 |
| `.../polling_interval` | RW | ms; < 1 jiffy means no polling | polling governors | ABI, September 2011 |
| `.../userspace/set_freq` | RW | Hz; requested frequency | `userspace` governor | ABI, September 2011 |
| `.../timer` | RW | `deferrable` or `delayed` work timer | `simple_ondemand` | ABI, July 2020 |
| `.../related_cpus` | RO | CPU list related to this devfreq domain | CPU-coupled devices | ABI, June 2025 |

## Safety and writes

Reads are safe. Writing `governor`, `min_freq`/`max_freq`, `polling_interval` or `timer` changes live scaling behavior of a hardware block; the ABI notes max_freq is the thermal throttle knob because it overrides min_freq. `trans_stat` accepts only 0 (statistics reset); a frequency table larger than PAGE_SIZE makes reads fail with -EFBIG. As with cpufreq, writes are policy changes and belong to system daemons, not ad hoc shell use.

## References

- `Documentation/ABI/testing/sysfs-class-devfreq` (cached copy; 14 What entries)
- Sibling pages: [devfreq-event](./devfreq-event.md), [powercap](./powercap.md); coverage: [ledger](../ledger.md)
- Live check: /sys/class/devfreq absent (kernel 5.10.134, read-only enumeration)
