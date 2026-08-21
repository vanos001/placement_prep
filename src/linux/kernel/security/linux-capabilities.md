# Linux Capabilities — Fine-Grained Privilege Decomposition

## Introduction: Why Capabilities Exist

Traditional UNIX uses a binary privilege model: a process is either
root (UID 0) or not. As root, the process bypasses essentially every
permission check the kernel performs — file mode bits, privileged
socket operations, reserved port binding, `kexec`, raw I/O, kernel
module loading, scheduling overrides, you name it. This is dangerous
because the application does not need *all* of root's powers. A web
server binding to port 80 needs to bind to a privileged port exactly
once; afterward it wants to do nothing that requires privilege. Yet
the classic answer was "start as root, then drop privileges by calling
`setuid(nobody)`."

That works in principle but has subtle traps:

- The window between "start as root" and "drop privileges" is the
  entire vulnerable surface. A buffer overflow during config parsing,
  which runs *before* the drop, gives the attacker root.
- If the binary is setuid-root, anyone can ask the kernel to run it,
  and the kernel will do so as root before the program has any say.
- A daemon that needs to re-bind after `SIGHUP` (e.g. to honor new TLS
  cert paths) has to remain root forever.

Capabilities decompose root into roughly forty orthogonal bits. The web
server can be granted *only* `CAP_NET_BIND_SERVICE`, dropped into a
normal user, and the bind will still succeed because the kernel checks
the capability bit, not the UID. The setuid bit becomes largely
unnecessary.

The feature shipped in Linux 2.2 (January 1999) and has been refined
since — most notably with the *ambient* set (Linux 4.3, 2015), which
fixed long-standing problems with setuid binaries.

> **Man page:** capabilities(7) — `https://man7.org/linux/man-pages/man7/capabilities.7.html`
> **Header:** `include/uapi/linux/capability.h`
> **Last capability:** `cat /proc/sys/kernel/cap_last_cap` (today: 41)

## The Capability Catalog

The full list, as of kernel 6.x, with the bits most ops people need to
remember highlighted:

```
 0  CAP_CHOWN              chown() arbitrary files
 1  CAP_DAC_OVERRIDE       bypass DAC (file mode) checks
 2  CAP_DAC_READ_SEARCH    bypass read/search DAC
 3  CAP_FOWNER             bypass file-owner checks
 4  CAP_FSETID             set setuid/setgid bits
 5  CAP_KILL               bypass signal perms
 6  CAP_SETGID             setgid/setgroups
 7  CAP_SETUID             setuid/setfsuid
 8  CAP_SETPCAP            grant caps to others
 9  CAP_LINUX_IMMUTABLE    chattr +i
10  CAP_NET_BIND_SERVICE   bind <1024             <-- here
11  CAP_NET_BROADCAST      broadcast listening
12  CAP_NET_ADMIN          interface config, routing, firewall
13  CAP_NET_RAW            RAW sockets             <-- here
14  CAP_IPC_LOCK           mlock, IPC_SHM lock
15  CAP_IPC_OWNER          bypass IPC owner check
16  CAP_SYS_MODULE         insmod / init_module
17  CAP_SYS_RAWIO          ioperm, iopl, /dev/port
18  CAP_SYS_CHROOT         chroot
19  CAP_SYS_PTRACE         ptrace
20  CAP_SYS_PACCT          configure process accounting
21  CAP_SYS_ADMIN          "the new root"          <-- here
22  CAP_SYS_BOOT           reboot
23  CAP_SYS_NICE           renice, scheduling
24  CAP_SYS_RESOURCE       ulimits
25  CAP_SYS_TIME           settimeofday
26  CAP_SYS_TTY_CONFIG     vhangup, TTY config
27  CAP_MKNOD              mknod
28  CAP_LEASE              file leases
29  CAP_AUDIT_WRITE        kernel audit log
30  CAP_AUDIT_CONTROL      configure audit
31  CAP_SETFCAP            set file capabilities
32  CAP_MAC_OVERRIDE       MAC policy (SELinux)
33  CAP_MAC_ADMIN          MAC config
34  CAP_SYSLOG             dmesg
35  CAP_WAKE_ALARM         clock_nanosleep / rtc
36  CAP_BLOCK_SUSPEND      block system sleep
37  CAP_AUDIT_READ          read audit
38  CAP_PERFMON            perf_event_open          <-- new (5.8)
39  CAP_BPF                bpf(2)                   <-- new (5.8)
40  CAP_CHECKPOINT_RESTORE CRIU                     <-- new (5.13)
41  CAP_PERFMON (dep)       (above)
```

Three of these dominate the conversation:

- **`CAP_NET_BIND_SERVICE`** — the canonical "let a non-root process
  bind to port 80." Modern systems often avoid this entirely by using
  `systemd` socket activation or `iptables`-based NAT, but the
  capability remains the kernel's primitive.
- **`CAP_NET_RAW`** — required for `socket(AF_PACKET, SOCK_RAW,
  ...)`, `socket(AF_INET, SOCK_RAW, ...)`, and tools like `tcpdump`,
  `ping`. The latter group was given a `cap_net_raw` setcap on disk
  on some distributions precisely so they no longer have to be
  setuid-root.
- **`CAP_SYS_ADMIN`** — famous as the "new root" because it covers
  chroot, mount, most namespaces operations, the majority of system
  administration knobs, and historically became the dumping ground
  for "I need this operation to require privilege but no existing
  cap fits." Docker drops `CAP_SYS_ADMIN` by default and lives to tell
  the tale.

## The Five Capability Sets

Every task has a credential (`struct cred` in `kernel/cred.c`)
carrying five capability bitmasks. To understand them, read them in
the right order:

```
P = permitted       What you *could* have. The hard ceiling.
E = effective       What you currently have, *right now*.
I = inheritable     What you can pass across execve, preserving
                    across the setuid boundary. (Often near-empty.)
B = bounding        The maximum permitted/inheritable set after execve.
                    Can only be *shrunk* during the life of a process.
A = ambient         Caps in this set are automatically in E and P, and
                    survive execve of a non-suid binary. (Linux 4.3+)
```

At exec time the kernel computes new `P'` and `E'`:

```
P'(exec) = (P_inheritable & F_inheritable) | (F_permitted & Bounding)
           | Ambient                          (for non-suid binaries)
E'(exec) = F_effective ? P'(exec) : 0         (file's "effective" flag)
```

For a normal (non-suid, non-file-cap) binary:

```
P' = Bounding | Ambient     (modulo ambient)
E' = Ambient                 (effectively, ambient only)
```

That last line is what makes ambient caps powerful: set them once in
a launcher and *every* child process — including ones that themselves
call `system("foo")` — inherits the capability without needing file
caps on each binary.

### Setting caps on files: `setcap`

The kernel stores file capabilities in the `security.capability`
extended attribute. `libcap` provides `setcap` to write it:

```
# Give ping the right to open raw sockets without setuid
sudo setcap cap_net_raw=eip /usr/bin/ping

# Confirm
getcap /usr/bin/ping
# /usr/bin/ping cap_net_raw=eip
```

The `eip` suffix encodes three bits:

- `e` — file's *effective* flag set; turn the cap on in E at exec.
- `i` — file's *inheritable* flag set; matches the task's inheritable set.
- `p` — file's *permitted* flag set; the cap is in P' after exec.

Without `e`, a non-suid file cap is dormant — in P but not E — and
the program has to call `cap_set_flag()` + `cap_set_proc()` itself to
make it active. The convention is "set all three (`eip`)" unless you
specifically want the program to opt-in.

### Ambient caps in practice

Ambient caps are simpler for daemons that exec helpers:

```c
/* Lower bounding set, raise ambient cap, drop root, exec the helper. */
#include <sys/capability.h>
#include <sys/prctl.h>
#include <unistd.h>

int enable_bind(void) {
    cap_t caps = cap_get_proc();
    cap_value_t wanted = CAP_NET_BIND_SERVICE;

    /* Make the cap permitted + inheritable + effective on us */
    cap_set_flag(caps, CAP_PERMITTED,   1, &wanted, CAP_SET);
    cap_set_flag(caps, CAP_INHERITABLE, 1, &wanted, CAP_SET);
    cap_set_flag(caps, CAP_EFFECTIVE,  1, &wanted, CAP_SET);
    if (cap_set_proc(caps) < 0) return -1;
    cap_free(caps);

    /* Raise the ambient set so children inherit without file caps */
    if (prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_RAISE,
              CAP_NET_BIND_SERVICE, 0, 0))
        return -1;

    /* Now drop root and exec the worker; it will still bind <1024 */
    setgid(65534); setuid(65534);
    execl("/usr/local/bin/worker", "worker", NULL);
}
```

## Bounding Set: the Ceiling You Cannot Raise

`CAP_SYS_ADMIN`, `CAP_NET_ADMIN`, and friends are dangerous in the
hands of an attacker. A common pattern when spawning a worker is to
*shrink* the bounding set first, so even if the worker is compromised
and acquires root it cannot add caps back:

```
# Drop bounding set down to only CAP_NET_BIND_SERVICE
capsh --drop=cap_sys_admin,cap_sys_module,cap_net_admin \
      --bounds=-all,+cap_net_bind_service -- -c worker
```

`prctl(PR_CAPBSET_DROP, cap)` is the underlying syscall. Once dropped,
the cap cannot come back for any descendant.

## Comparison to sudo

`sudo` and capabilities solve different problems and are often
confused. A summary:

| Aspect                 | sudo                            | Capabilities                        |
|------------------------|---------------------------------|-------------------------------------|
| Scope                  | Entire command line as root     | Single capability bits              |
| Lifetime               | Process lifecycle               | Tied to task or file                |
| Granularity            | Binary                          | 40+ orthogonal bits                 |
| Audit                  | Centralized via sudoers         | Kernel audit per cap                |
| Privilege retention    | Drops back to user after exec   | Stays in `cred`                     |
| Defeats shell escapes? | No (`sudo vi` → `:!sh`)         | Yes (no root at all)                |
| Used by                | Admins running tasks            | Daemons binding ports, sandboxing   |

The crucial difference: capabilities are *checked by the kernel* at
the moment a privileged operation is attempted. They are not "run as
root" plus "drop root." The program never had root.

## Docker: the Default Cap Set

Docker, by default, drops *everything* except fourteen caps — far
fewer than a typical sudo-protected setup. The default permitted set:

```
CAP_AUDIT_WRITE          CAP_CHOWN            CAP_DAC_OVERRIDE
CAP_FOWNER               CAP_FSETID           CAP_KILL
CAP_MKNOD                CAP_NET_BIND_SERVICE  CAP_NET_RAW
CAP_SETGID               CAP_SETUID           CAP_SETPCAP
CAP_SETFCAP              CAP_SYS_CHROOT
```

Notable absentees — what a default container *cannot* do without
`--cap-add`:

- `CAP_NET_ADMIN` — no iptables, no adding interfaces
- `CAP_SYS_ADMIN` — no mount inside the container, no namespaces
- `CAP_SYS_MODULE` — no loading kernel modules
- `CAP_SYS_PTRACE` — no ptracing host processes
- `CAP_SYS_RAWIO` — no raw I/O to disk
- `CAP_SYS_BOOT` — no reboot

The point is **least privilege**: a typical web container needs the
network caps and chown, but no system administration. Adding
`--cap-add SYS_ADMIN` is a frequent mistake — that single switch
effectively restores much of root's power inside the namespace, and
combined with the default unprivileged user inside the container is
the canonical path of container escapes (CVE-2019-5736 runc and
friends relied on precisely the absence of the kind of isolation that
dropping `CAP_SYS_ADMIN` would have preserved).

## Inspecting a Running Process

The canonical tool is `getpcaps`:

```
$ getpcaps 1234
Capabilities for `1234': = cap_net_bind_service+ep
```

The format mirrors file caps: `+ep` means effective + permitted. The
kernel exposes the same info via `/proc/<pid>/status`:

```
$ grep -i cap /proc/self/status
CapInh: 0000000000000000
CapPrm: 0000000000000000
CapEff: 0000000000000000
CapBnd: 000001ffffffffff     <-- bounding set
CapAmb: 0000000000000000
```

The masks are hex of the bitfield. To decode:

```
$ capsh --decode=000001ffffffffff
0x000001ffffffffff=cap_chown,cap_dac_override,...,cap_sys_admin,...
```

## The Security Failure Modes

Capabilities are not magic — they have specific traps:

1. **`CAP_SYS_ADMIN` is the new root.** Adding it to a container
   restores ~90% of what root used to mean. If you are thinking about
   `--cap-add SYS_ADMIN`, you usually want a different solution.
2. **The ambient set is per-process.** A setuid-root binary clears it
   on exec — that is by design; otherwise ambient `CAP_SYS_ADMIN` on
   a `setuid(0)` program would be catastrophic.
3. **File caps on script interpreters are ignored.**
   `setcap cap_net_raw=eip /usr/bin/python3` does nothing for
   `python3 -c "..."` because the kernel applies the cap to the
   *interpreter*, then the interpreter execs the script which does its
   own exec of `/usr/bin/python3` again, by which point the
   inheritance is broken. Use ambient caps or `setcap` on the final
   binary.
4. **Caps do not bypass MAC.** SELinux/AppArmor still apply; a
   process with `CAP_NET_BIND_SERVICE` can be denied a bind by
   SELinux policy.

## References

1. **capabilities(7) manpage** —
   <https://man7.org/linux/man-pages/man7/capabilities.7.html>
2. **`capability.h` kernel header** —
   <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/uapi/linux/capability.h>
3. **`libcap` source (user-space library + `setcap`/`getcap`/`capsh`)** —
   <https://git.kernel.org/pub/scm/linux/kernel/git/morgan/libcap.git>
4. **Docker security reference (capability profile and `--cap-add`)** —
   <https://docs.docker.com/engine/security/>
5. **LWN: "A brief history of capabilities"** —
   <https://lwn.net/Articles/432981/>
6. **LWN: capabilities discussions (ambient set)** —
   <https://lwn.net/Articles/605176/> and related threads
7. **cred(7) manpage** —
   <https://man7.org/linux/man-pages/man7/credentials.7.html>
8. **Kernel source: `security/commoncap.c`** —
   <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/security/commoncap.c>
