# Unit Files — Syntax, Loading, Drop-ins and Templating

## Overview

A unit file is a small key=value configuration fragment with three kinds of
sections: the universal `[Unit]` section (identity and dependencies), the
type-specific section (`[Service]`, `[Socket]`, `[Mount]`, ...), and the
optional `[Install]` section that describes enablement. The interesting
engineering is around the file, not in it: how the manager *finds* fragments
across four directories plus generators, how drop-in `*.d/override.conf`
files let admins patch vendor units without touching them, and how `@`
templates let one file express a family of instances (`getty@tty1`,
`getty@ttyS0`).

This page covers that machinery end to end: the load path and precedence
rules, the grammar and specifiers, `[Install]` semantics and what `enable`
physically does, drop-in override workflows (`systemctl edit`/`revert`),
template units, masking and linking, generators, and validation with
`systemd-analyze verify`.

## File Locations and Precedence

Unit files are loaded from a compiled-in list of directories; **for the main
unit file, earlier entries win** — the first fragment with a given name is
the one loaded. The documented system-mode order:

| Priority | Path | Role |
|---|---|---|
| 1 | `/etc/systemd/system.control` | Persistent config created via the D-Bus API (e.g. `set-property`) |
| 2 | `/run/systemd/system.control` | Same, runtime-only |
| 3 | `/run/systemd/transient` | Transient units created by `systemd-run` |
| 4 | `/run/systemd/generator.early` | Generator output with priority *above* admin config |
| 5 | `/etc/systemd/system` | **Admin** units and symlinks — the place for your own units |
| 6 | `/run/systemd/system` | **Runtime** units (`systemctl edit` at boot-time images, volatile systems) |
| 7 | `/run/systemd/generator` | Normal generator output (fstab, cryptsetup, getty...) |
| 8 | `/usr/local/lib/systemd/system` | Units installed by the local administrator/packages built from source |
| 9 | `/usr/lib/systemd/system` | **Vendor** units shipped by the distribution (on split-`/usr` systems this is `/lib/systemd/system`) |
| 10 | `/run/systemd/generator.late` | Generator output with priority *below* everything (fstab units land here so they never shadow admin files) |

The three tiers people actually quote — `/etc` over `/run` over `/usr/lib` —
are the stable core; the `.control`, `transient` and `generator*` entries
are the modern refinements. On merged-`/usr` distributions (all current
Fedora, Debian since 12, Arch) `/lib` is a symlink to `/usr/lib`, so both
names resolve to the same vendor directory. Initramfs systems carry a second
copy of the world under `/sysroot` during the initrd phase.

Runtime hygiene commands:

```
$ systemctl cat sshd.service          # print the *effective* unit: fragment + drop-ins
$ systemctl show sshd.service         # all resolved properties
$ systemctl show -p FragmentPath,DropInPaths sshd.service
FragmentPath=/usr/lib/systemd/system/ssh.service
DropInPaths=/etc/systemd/system/ssh.service.d/override.conf
```

Units no longer referenced by anything are garbage-collected from memory;
`daemon-reload` rescans the directories, re-runs generators, and rebuilds the
loaded-unit generation — it does **not** restart anything, but changed
fragment contents take effect on the next start/reload of each unit.

## Grammar Fundamentals

```ini
[Unit]
Description=Foo daemon           # a description string
Documentation=man:foo(8)
After=network.target foo-db.service

[Service]
ExecStart=/usr/bin/foo --listen 9000
Environment="FOO_THREADS=4" FOO_LOG=info
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Rules that matter when reading or writing these files:

- **Sections** are `[Bracketed]`; unknown sections are ignored with a
  warning; unknown keys inside known sections log a warning but *do not
  abort loading*. `X-` prefixed sections/keys are explicitly reserved for
  external parsers.
- **Key=Value** pairs; whitespace around the `=` is tolerated. Keys are
  matched case-insensitively in practice, but write them exactly as
  documented.
- **List-type directives** (e.g. `Environment=`, `Wants=`, `ExecStartPre=`)
  accumulate: repeating the directive appends. Assigning an **empty value
  resets the list** — `ExecStart=` followed by a new `ExecStart=...` in a
  drop-in is the canonical override idiom.
- **Booleans** accept `1`, `yes`, `true` and `0`, `no`, `false`.
- **Time spans**: bare numbers mean seconds; `90s`, `5min 20s`,
  `infinity` are valid. **Sizes**: `1M`, `2G` (base 1024 unless suffixed `B`).
- **Comments**: `#` and `;` to end of line. **Line continuation**: a trailing
  backslash joins the next line (useful for long `ExecStart=` lines).
- The unit's filename must match its name; a `[Service]` section in a
  `.socket` file is ignored, and vice versa.

## Specifiers

Unit files expand `%`-specifiers at load time. The ones used in real life,
with their value for the instance `foo@bar.service` running as a system unit:

| Specifier | Meaning | For `foo@bar.service` |
|---|---|---|
| `%n` | Full unit name | `foo@bar.service` |
| `%N` | Full name without type suffix | `foo@bar` |
| `%p` | Prefix — text before `@` (for non-instantiated units: name without suffix) | `foo` |
| `%i` | Instance name (escaped form) | `bar` |
| `%I` | Instance name, unescaped | e.g. `/data/x` if the instance was escaped from it |
| `%f` | Unescaped instance or prefix with `/` prepended — the "filename" form | `/bar` (or the mount path for `.mount` units) |
| `%t` | Runtime dir root | `/run` (system) / `$XDG_RUNTIME_DIR` (user) |
| `%S` | State dir root | `/var/lib` |
| `%C` | Cache dir root | `/var/cache` |
| `%E` | Config dir root | `/etc` |
| `%L` | Log dir root | `/var/log` |
| `%h` | Home directory of the *manager's* user | `/root` (system manager) |
| `%u` / `%U` | User name / UID of the manager | `root` / `0` |
| `%m` / `%b` | Machine ID / boot ID | hex strings |
| `%H` / `%v` | Hostname / kernel release (`uname -r`) | strings |
| `%T` / `%V` | `/tmp` / `/var/tmp` (TMPDIR-aware) | paths |

Two traps worth knowing: `%u`/`%U`/`%h` describe the **manager's** user, not
the `User=` the service will run as (a documented, surprising choice), and
`%i` vs `%I` differ only in whether path-style escaping has been undone.
Per-directory writable spaces are better obtained from `StateDirectory=`
(see [service-units.md](./service-units.md)) than from specifiers.

## The [Unit] Section

The universal section — identity, dependencies, ordering, conditions:

- `Description=`, `Documentation=` — presentation and pointers.
- `Wants=`, `Requires=`, `Requisite=`, `BindsTo=`, `Upholds=`, `PartOf=`,
  `Conflicts=` — requirement dependencies; semantics in
  [dependency-management.md](./dependency-management.md).
- `Before=`, `After=` — pure ordering; no requirement implied.
- `OnFailure=`, `OnSuccess=` — units to start when this one fails/succeeds
  (the `on-failure@%n` template pattern).
- `RequiresMountsFor=` — Requires+After for the mount units of given paths.
- `StopWhenUnneeded=`, `IgnoreOnIsolate=`, `CollectMode=` — lifecycle fine
  tuning.
- `Condition*=`, `Assert*=` — see below.

**Conditions vs asserts** share one predicate syntax and differ in failure
handling: a failed `Condition*` *skips* the unit silently (start job
succeeds; the unit just never starts), while a failed `Assert*` *fails* the
start job. Predicates include `ConditionPathExists=`,
`ConditionPathIsDirectory=`, `ConditionFileNotEmpty=`,
`ConditionDirectoryNotEmpty=`, `ConditionKernelCommandLine=`,
`ConditionHost=`, `ConditionUser=`, `ConditionGroup=`,
`ConditionVirtualization=`, `ConditionArchitecture=`, `ConditionSecurity=`,
`ConditionCapability=`, `ConditionMemory=`, `ConditionCPUs=`,
`ConditionFirstBoot=`, `ConditionControlGroupController=` and
`ConditionNeedsUpdate=`. Prefix semantics: `!` negates; `|` makes the line
OR-ed with other condition lines (all un-prefixed lines are ANDed). Typical
use: `ConditionPathExists=/etc/foo/enabled` as a config-file kill switch, or
`ConditionVirtualization=!container` to keep a unit off containers.

## The [Install] Section and What enable Does

`[Install]` exists solely for `systemctl enable`. It records which
targets/units should want this unit:

| Directive | Effect of enable |
|---|---|
| `WantedBy=multi-user.target` | Create symlink `/etc/systemd/system/multi-user.target.wants/foo.service -> /usr/lib/systemd/system/foo.service` |
| `RequiredBy=<unit>` | Same, into `<unit>.requires/` |
| `Alias=bar.service` | Create `/etc/systemd/system/bar.service -> foo.service` |
| `Also=bar.service` | When enabling `foo`, also enable `bar` |
| `DefaultInstance=bar` | For templates: the instance enabled when the template itself is enabled |

So `enable` is **symlink creation plus daemon-reload** — nothing more,
nothing less. `systemctl disable` removes the symlinks;
`disable --now` also stops; `enable --now` also starts;
`reenable` cleans and re-creates. `is-enabled` then reports one of:

| State | Meaning |
|---|---|
| `enabled` | Symlink in `/etc/systemd/system/*.wants/` |
| `enabled-runtime` | Symlink in `/run` — enable with `--runtime`, lost on reboot |
| `linked` / `linked-runtime` | Unit file made visible via symlink from outside the load path |
| `alias` | The unit is itself an alias symlink |
| `static` | No `[Install]` section — only started as a dependency (typical for socket-triggered services and templates) |
| `generated` | Created by a generator (e.g. an `/etc/init.d` script via sysv-generator) |
| `indirect` | Not enabled itself, but its `Also=` peers are (or an alias exists) |
| `transient` | Created at runtime via the API (`systemd-run`) |
| `disabled` | No enablement symlinks |
| `masked` / `masked-runtime` | A symlink to `/dev/null` — cannot be started at all |

**Presets** make enablement declarative: `systemctl preset foo` consults
policy files in `/etc/systemd/system-preset/` (then `/run/`, then
`/usr/lib/systemd/system-preset/`), whose lines look like:

```ini
# /etc/systemd/system-preset/20-myorg.preset
enable   sshd.service
disable  fstrim.timer
enable   anacron.timer *.socket
```

`systemctl preset-all` applies the policy to every unit — what distribution
installers effectively do so that "first boot state" is data, not a
hand-curated symlink farm.

## Drop-in Overrides

Any unit may be extended by files in `<name>.d/*.conf` next to it:

```
/etc/systemd/system/sshd.service.d/override.conf     <- admin override (highest precedence)
/run/systemd/system/sshd.service.d/*.conf            <- runtime
/usr/lib/systemd/system/sshd.service.d/*.conf        <- vendor-provided extras
```

Drop-ins are merged into the effective unit in directory-precedence order;
within one directory, files apply in filename order (hence the `override.conf`
convention). List-type directives accumulate across drop-ins; to *replace* a
value, clear it first with an empty assignment:

```ini
# /etc/systemd/system/sshd.service.d/override.conf  (produced by systemctl edit)
[Service]
ExecStart=                              # clear the vendor command line
ExecStart=/usr/sbin/sshd -D -e -p 2222
Restart=on-failure                      # scalar: just reassign
```

The interactive workflow:

- `systemctl edit foo.service` — opens `$EDITOR` on a fresh
  `/etc/systemd/system/foo.service.d/override.conf`; on save, runs
  `daemon-reload` for you. This is *the* sanctioned way to customize vendor
  units.
- `systemctl edit --full foo.service` — copies the whole fragment to
  `/etc/systemd/system/foo.service` so you can edit everything (use when
  reordering `[Unit]` directives or renaming).
- `systemctl revert foo.service` — deletes your drop-ins (and your
  `/etc` copy from `--full`), restoring the vendor state. There is no
  SysVinit-era equivalent of "put it back the way the package had it";
  this is it.

Drop-ins only *merge* — they cannot remove a `Wants=` entry (that needs a
full override via `edit --full` or masking) and they cannot change the unit
type. A drop-in for a template (`foo@.service.d/`) applies to all instances;
a drop-in for a specific instance (`foo@bar.service.d/`) applies to just it.

## Template Units

A template unit ends in `@` before the suffix (`foo@.service`) and is
instantiated as `foo@ARG.service` for any ARG — the ARG lands in `%i`.
Templates power every "one config, N instances" need: `getty@tty1`,
`getty@ttyS0`, `sshd@`-per-port, `user@1000`:

```ini
# getty@.service (vendor, simplified)
[Unit]
Description=Getty on %I
After=systemd-user-sessions.service

[Service]
ExecStart=-/sbin/agetty --noclear %I $TERM
Restart=always

[Install]
WantedBy=getty.target
```

Semantics worth stating precisely:

- Instances are units in their own right: `systemctl start foo@bar` works if
  the template exists; `systemctl status foo@bar` shows its own state and
  its own cgroup (`foo@bar.service` — and instances of a template share an
  implicit per-template slice, see [cgroups-resource-control.md](./cgroups-resource-control.md)).
- `DefaultInstance=` in the template makes bare `systemctl start foo` start
  `foo@bar`.
- Enabling a *template* (`WantedBy=` in the template's `[Install]`) creates
  the wants-symlink for the template; enabling a specific *instance* creates
  `getty.target.wants/getty@tty1.service`. Instances whose names contain
  spaces or odd characters must be escaped — `systemd-escape
  --template=foo@.service 'my instance'` prints the right name
  (`foo@my\x20instance.service`).
- The instance string may be a path fragment: `systemd-fsck@dev-sda1` style
  names come from escaping device paths with `systemd-escape -p`.

## Masking, Linking and Transient Units

- **Mask**: `systemctl mask foo` replaces the unit name (in `/etc/systemd/system/`)
  with a symlink to `/dev/null`. Masked units cannot be started — not
  manually, not as dependencies, not by activation. It is the only way to
  make "this unit never runs, whatever wants it" stick; `disable` merely
  removes wants-symlinks and a `Wants=` elsewhere will still pull the unit
  in. `systemctl unmask` restores. `--runtime` masks live in `/run` only.
- **Link**: `systemctl link /opt/myapp/myapp.service` makes a unit file
  outside the load path visible to the manager (a symlink into
  `/etc/systemd/system`). Modern alternative: drop a symlink there yourself
  or use `--now` to start it immediately too.
- **Transient units**: `systemd-run --unit=foo ...` creates a unit that
  exists only in memory (under `/run/systemd/transient`), with full
  directive control (`--property=`) but no file at all. The development and
  API story is in [apis-development.md](./apis-development.md).

## Generators

Generators are small executables in `/usr/lib/systemd/system-generators/`
(and `/etc/systemd/system-generators/`, `/usr/local/lib/systemd/system-generators/`)
run by the manager at boot and at every `daemon-reload`. Each receives three
output directories and may write unit files, drop-ins, or symlinks into
them:

- `generator.early/` — output that beats even `/etc` (rarely used),
- `generator/` — normal priority (beats vendor, loses to admin),
- `generator.late/` — lowest priority (fstab generator's choice, so a
  hand-written `etc-fstab.mount`-style admin unit wins over the fstab row).

Generators are the bridge between legacy formats and the unit model. The
ones you meet on every system:

| Generator | Synthesizes |
|---|---|
| `systemd-fstab-generator` | `.mount`/`.automount`/`.swap` units from `/etc/fstab` (and `rd.fstab=` in the initrd) |
| `systemd-gpt-auto-generator` | Mounts from GPT partition type GUIDs (discoverable partitions: ESP, `/home`, swap...) |
| `systemd-cryptsetup-generator` | `cryptsetup@*.service` from `/etc/crypttab` |
| `systemd-veritysetup-generator` | dm-verity units from kernel cmdline / veritytab |
| `systemd-getty-generator` | `getty@ttyN` instances for the console(s), honoring `console=` |
| `systemd-debug-generator` | Implements `systemd.mask=`, `systemd.wants=`, `systemd.debug_shell=` |
| `systemd-system-update-generator` | Redirects `default.target` to `system-update.target` when `/system-update` exists (offline updates) |
| `systemd-network-generator` | `systemd.network`/`netdev` files from kernel cmdline (`ip=`) |

Writing one is deliberately boring: a program that prints unit files to
`argv[1..3]` — the canonical extension point, covered in
[apis-development.md](./apis-development.md).

## Validation and Common Errors

`systemd-analyze verify` parses units statically and reports real problems —
missing ExecStart executables, unknown directives, bad dependencies,
circular ordering — without running anything:

```
$ systemd-analyze verify /etc/systemd/system/foo.service
Unit foo.service has a bad unit file setting:
/etc/systemd/system/foo.service:6: Unknown key name 'Execstart' in section 'Service', ignoring.
foo.service: Command ExecStart=/usr/bin/fooo is not executable: No such file or directory
```

The error patterns that account for most broken units: a typo'd key
(`Execstart=` — silently warned, then "no ExecStart"), a missing section
header, relative instead of absolute paths in `Exec*=` (commands must be
absolute; `ExecStart=-/usr/bin/foo` with `-` prefix only means "ignore
failure"), forgetting that repeated list directives accumulate (two
`ExecStart=` lines in one file only work for `Type=oneshot`), and editing a
fragment without `daemon-reload` (the manager keeps serving the old
generation). `systemctl --no-pager cat foo` is always the first debugging
step: it shows the *effective* unit, so a stale expectation versus a bad
drop-in is immediately visible.

## Interview Questions

### Q: What exactly does systemctl enable do?

It creates filesystem symlinks as prescribed by the unit's `[Install]`
section — typically `/etc/systemd/system/multi-user.target.wants/foo.service`
pointing at the fragment — then reloads the manager so it notices. Nothing
starts. The reverse (`disable`) removes those symlinks; `--now` variants
also start/stop; `preset` applies policy files instead of hardcoding the
choice; and `mask` is the stronger sibling that points the unit name at
`/dev/null` so the unit cannot be started even as a dependency.

### Q: How do you override a vendor unit without editing the vendor file?

Drop-ins: `systemctl edit foo.service` creates
`/etc/systemd/system/foo.service.d/override.conf`, which is merged over the
vendor fragment. To *replace* a list directive rather than append, clear it
first inside the drop-in (`ExecStart=` empty line, then the new
`ExecStart=`). `systemctl edit --full` copies the whole unit for
restructuring, and `systemctl revert` removes your overrides, restoring the
package's file. Package upgrades keep working because the vendor file is
untouched.

### Q: Explain the unit load path precedence, and where fstab mounts come from.

For the main fragment, highest priority first: `.control`/`transient` dirs,
`generator.early`, `/etc/systemd/system`, `/run/systemd/system`,
`generator`, `/usr/local/lib/systemd/system`, `/usr/lib/systemd/system`
(vendor), then `generator.late` — first hit wins. Drop-ins from all of
these merge instead. Mount units usually come from `systemd-fstab-generator`,
which writes `/run/systemd/generator.late` — the lowest priority — precisely
so an administrator's own mount unit or drop-in outranks an fstab row.

### Q: How do template units work, and when would you write one?

`foo@.service` defines a family; `foo@bar.service` is an instance whose
instance string arrives as `%i` (and unescaped as `%I`). Instances are
independent units with their own state and cgroups, started on demand or
enabled individually (`getty@tty1`), and a `DefaultInstance=` makes the bare
name work. Write one whenever N configurable variants exist — per-terminal
gettys, per-port sshd, per-device backup jobs — and remember that instance
names with spaces/slashes must be passed through `systemd-escape`.

### Q: What is the difference between disable and mask?

`disable` removes enablement symlinks: the unit will not start *at boot*,
but it can still be started explicitly or pulled in by another unit's
`Wants=`/`Requires=`. `mask` symlinks the unit name to `/dev/null`, making
the unit unstartable by any path, including dependencies. To keep a vendor
service off even though something Requires it, mask; to merely change boot
behavior, disable. `systemctl unmask` reverses the mask.

### Q: A colleague edited /usr/lib/systemd/system/nginx.service directly. What is wrong with that?

Three things. Package upgrades will silently overwrite it (vendor files are
package-owned); the change is invisible to `systemctl revert` and to other
admins auditing `/etc`; and drop-ins already solve the common cases
without copying the file. The right move is `systemctl edit nginx.service`
for value overrides or `edit --full` (which places the copy in `/etc`,
where it belongs and where upgrades leave it alone).

## References

- [systemd.unit(5) — grammar, load path, specifiers, conditions, [Install]](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.service(5) — drop-in semantics examples for the service type](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.generator(7) — generator contract and directory priorities](https://www.freedesktop.org/software/systemd/man/latest/systemd.generator.html)
- [systemd.directives(7) — index of every directive by name](https://www.freedesktop.org/software/systemd/man/latest/systemd.directives.html)
- [systemd.unit(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.unit.5.en.html)
- [systemd.service(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.service.5.en.html)
- [systemd.generator(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.generator.7.en.html)
- [systemd.directives(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.directives.7.en.html)

## Cross-References

- [Unit types](./unit-types.md) — what each file type configures and the name/escaping rules.
- [Service units in depth](./service-units.md) — the [Service] section in full.
- [Dependencies and ordering](./dependency-management.md) — the Wants/Requires/After machinery behind [Unit].
- [systemctl command reference](./systemctl-cli.md) — enable/edit/revert/verify in operational context.
- [systemd API development](./apis-development.md) — transient units and writing your own generators.
- [systemd hands-on (admin)](../../admin/systemd.md) — everyday unit editing workflows.
- [SysVinit init scripts](../sysvinit/init-scripts.md) — the shell-script format unit files replaced (and the generator that wraps it).
