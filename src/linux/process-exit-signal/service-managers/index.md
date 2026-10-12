# Service Managers Compared — Exit Statuses, Signals, and Restarts

Four managers, four supervision philosophies. systemd *policies* restarts
with an exit-code vocabulary; OpenRC makes supervision an opt-in module
(`supervise-daemon`) bolted onto a runlevel engine; runit and s6
*always* restart and push interpretation of a death into your `./finish`
script (s6 adding one documented exception: finish exit 125). The
per-manager details live in [systemd.md](./systemd.md),
[openrc.md](./openrc.md), [runit.md](./runit.md), and
[s6.md](./s6.md); the broader init-system comparison is
[../../init-systems/comparison.md](../../init-systems/comparison.md).
Behavior marked *(config)* is set per service; *(design)* is fixed by the
supervisor's model.

## The one table that matters (SM-012)

| Dimension | systemd | OpenRC (+ supervise-daemon) | runit | s6 |
|---|---|---|---|---|
| Supervision model | cgroup per unit; one manager process; main PID tracked | s-s-d: none (start/stop only) *(config)*; supervise-daemon: parent-child fork of a foreground daemon | tree: `runit`(PID 1) → `runsvdir` → `runsv` per service dir | tree: `s6-svscan` → `s6-supervise` per service dir |
| Restart policy model | policy matrix `Restart=` (default **`no`**) *(config)*; success/failure/abnormal/watchdog classes | respawn **always** on unexpected exit *(design)*; unsupervised services never restart | restart **always**, regardless of exit code or signal *(design)* | restart **always**, unless `./finish` exits **125** (permanent failure) or `-O` *(design)* |
| Clean vs abnormal | exit 0 + `SIGHUP/INT/TERM/PIPE` (non-oneshot) + `SuccessExitStatus=` = clean; other signals = abnormal; wait-status split exited/killed/dumped | none — death is binary; logged as "exited with return code N" vs "terminated by signal N" | not classified; `./finish` gets `$1` exit code (or `-1`), `$2` = signal number or 0 | not classified by default; `./finish` gets `$1` exit code (or 256), `$2` = signal number |
| Exit-code-based restart conditions | `SuccessExitStatus=`, `RestartPreventExitStatus=`, `RestartForceExitStatus=` (codes, status names, **signal names**) | none | none | finish exit **125** only |
| Stop signal config | `KillSignal=` (SIGTERM), `RestartKillSignal=`, `SendSIGHUP=`; SIGCONT always follows *(config)* | `stopsig=` (SIGTERM) *(config)*; `stopgroup=` for process group | fixed `TERM`+`CONT` on `d`/`x`; control chars for others; custom `control/t` hooks | `down-signal` file (SIGTERM default) + `SIGCONT` *(config)* |
| Stop timeout config | `TimeoutStopSec=` (default `DefaultTimeoutStopSec=` **90s**) *(config)* | `retry=` schedule, e.g. `SIGTERM/5` *(config)* | none — `sv` waits 7 s by default, that's all | none by default — **never force-killed unless `timeout-kill` is set** |
| Escalation to SIGKILL | `FinalKillSignal=` (SIGKILL) after timeout, unless `SendSIGKILL=no` *(config)* | only if your retry schedule includes `SIGKILL` (default `SIGTERM/5` does not) | only explicit `sv kill` / control `k` | `SIGKILL` after `timeout-kill` ms (pid or group via `flag-timeout-killpg`), or explicit `s6-svc -k` |
| Restart limits / loop brake | `StartLimitIntervalSec=` (10s) + `StartLimitBurst=` (5) → refuse + `StartLimitAction=` (reboot…); `systemctl reset-failed` flushes | `respawn_delay=0`, `respawn_max=10` (0=unlimited), `respawn_period=12s`; give-up logged to syslog | **none** — 1 s anti-busyloop delay only *(design)* | **none** — 1 s minimum respawn delay; `max-death-tally` records deaths for external throttling |
| Restart timing | `RestartSec=` 100 ms; opt-in backoff `RestartSteps=/RestartMaxDelaySec=` (v254+) | `respawn_delay` + per-retry step 128 ms capped 30 s | fixed 1 s if the service exits immediately | fixed 1 s if not ready when it dies |
| Failure reporting | `failed` state; `systemctl status/show`; `Result=` / `$SERVICE_RESULT` vocabulary; `$EXIT_CODE/$EXIT_STATUS` to hooks | `rc-service status` / `rc-status`; supervise-daemon syslog lines; no failed-state machine | `sv status` state word (`run`/`down`/`finish`), flags, sv exit codes | `s6-svstat` (incl. last `exitcode`/`signal`), `s6-svdt` death tally, `./event` fifodir |
| Readiness notification | `Type=notify` (`sd_notify`, `READY=1`), watchdog | `notify=fd:N` or `socket:ready` (`READY=1` datagram) | `./check` program for `sv` availability (exit 0) | `notification-fd` + `s6-notifyoncheck`; `s6-svstat -o up,ready` |
| Zombie reaping | PID 1 manager reaps all unit processes | supervise-daemon reaps its direct child | `runsv` reaps `./run`/`./finish`; orphans re-parent to PID 1 | explicit: `s6-svscan` reaper waits *every* child ("especially important when run as process 1"); `s6-supervise` reaps run/finish |
| Logging model | journald (manager-integrated) | files / `output_logger=` / `--stdout-logger` | `log/` subservice → `svlogd` rotation | `log/` subservice → `s6-log` pipeline, log-loss-averse |

## Reading the table — three mental models

1. **Policy-driven (systemd).** The manager owns a vocabulary of exit
   codes and signals and a policy engine (`Restart=` × rate limiter ×
   escalation chain). Power: per-condition behavior
   (`RestartPreventExitStatus=75 250 SIGKILL`). Cost: defaults matter —
   `Restart=no`, 90 s stop timeout, `control-group` teardown.
2. **Opt-in supervision (OpenRC).** The base system never restarts
   anything; `supervise-daemon` adds runit-style always-restart with a
   respawn window, and health checks. Exit codes influence nothing except
   your own scripts.
3. **Always-restart supervision (runit, s6).** The manager never
   interprets a death — it just re-runs `./run`, bounded only by a 1 s
   anti-busyloop delay. All interpretation is delegated to `./finish`
   (and in s6, to the single documented `125` permanent-failure contract).
   No restart limits by design: braking loops is *your* script's job or
   an external watchdog's.

## Which failure signals are observable where

| Question | systemd | OpenRC | runit | s6 |
|---|---|---|---|---|
| "What was the last exit code?" | `systemctl show -p ExecMainStatus,Result` | supervise-daemon syslog | infer via `./finish` logging | `s6-svstat -o exitcode` |
| "Was it killed by which signal?" | `Result=signal|core-dump` + `$EXIT_STATUS` | supervise-daemon syslog | `./finish` `$2` | `s6-svstat -o signal` / `s6-svdt` |
| "How many times has it died recently?" | journal + start-limit state | supervise-daemon logs | not recorded | `s6-svdt` (tally up to 4096) |
| "Why did it stop restarting?" | `Result=start-limit-hit` | syslog "respawned too many times" | never stops restarting | finish exit 125 / `-O` (`wantedup=false`) |

## Further reading in this part

- [systemd.md](./systemd.md) — SM-001…SM-005: `Restart=` matrix, start
  rate limiting, kill procedure, exit-code tables, worked unit example.
- [openrc.md](./openrc.md) — SM-006…SM-007: openrc-run flow,
  start-stop-daemon vs supervise-daemon, respawn bounds, retry schedules.
- [runit.md](./runit.md) — SM-008…SM-009: stages, `./run`/`./finish`
  contract, `sv status` fields, svlogd.
- [s6.md](./s6.md) — SM-010…SM-011: supervision tree, finish-125
  semantics, `timeout-kill` escalation, death tally.
- Init-system foundations:
  [../../init-systems/comparison.md](../../init-systems/comparison.md),
  [../../init-systems/systemd/overview-architecture.md](../../init-systems/systemd/overview-architecture.md),
  [../../init-systems/openrc/overview-architecture.md](../../init-systems/openrc/overview-architecture.md),
  [../../init-systems/runit/overview-philosophy.md](../../init-systems/runit/overview-philosophy.md),
  [../../init-systems/runit/stages-services.md](../../init-systems/runit/stages-services.md).

## References

- systemd.service(5), systemd.kill(5), systemd.exec(5),
  systemd-system.conf(5), systemd.unit(5) — freedesktop.org man pages:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>
- OpenRC user guide and man pages (official repository):
  <https://github.com/OpenRC/openrc/blob/master/user-guide.md>,
  <https://github.com/OpenRC/openrc/blob/master/man/supervise-daemon.8>
- runit official documentation: <http://smarden.org/runit/>
- s6 official documentation: <https://skarnet.org/software/s6/>
- Full per-manager reference lists are at the end of each page above.

## Related Topics

- [Containers](../containers/index.md) — the same stop-signal and grace-period semantics re-implemented by runtimes and orchestrators
- [Exit-status lifecycle](../exit-status/index.md) — what the supervisor actually observes when a child exits or dies by signal
- [Operational troubleshooting](../troubleshooting/index.md) — diagnosing restart loops and shutdown failures in the field
- [Init Systems Compared (existing chapter)](../../init-systems/comparison.md) — broader init-system comparison beyond the exit/signal angle
