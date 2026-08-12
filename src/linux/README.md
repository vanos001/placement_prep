# Linux Track

This track brings the practical and systems-focused material from the
[lb2 Linux book](https://github.com/Abhinav-Kumar012/lb2) into the placement
preparation knowledge base. It complements, rather than replaces, the
conceptual [Operating Systems](../os/overview.md) section: use the OS section
to learn the models, and use this track to operate, debug, secure, and profile
a real Linux system.

## Suggested progression

1. **Foundations and history** — understand Unix/Linux, distributions, POSIX,
   and the kernel's development model.
2. **Shell and commands** — become fluent with pipelines, quoting, text
   processing, `find`, `xargs`, `sed`, `awk`, and Bash scripting.
3. **System programming** — connect processes, system calls, IPC, ELF,
   dynamic linking, `epoll`, and `io_uring` to OS theory.
4. **Administration and networking** — practise users, permissions, packages,
   services, storage, routing, DNS, SSH, TLS, and firewalling.
5. **Observability and performance** — form hypotheses with `/proc`, tracing,
   `perf`, eBPF, flame graphs, and the USE method before changing code.
6. **Security, containers, kernel, and virtualization** — study capabilities,
   namespaces, cgroups, seccomp, LSMs, KVM, drivers, filesystems, and kernel
   synchronization.

## Placement-focused additions

The imported book is intentionally navigated as a Linux deep dive. The short
[Linux Tools for Placement Preparation](./tools.md) chapter is an original
bridge for interview revision: it groups the commands by the question they
answer, gives safe examples, and records common traps. The imported chapters
then provide the deeper reference material for each area.

## How to use the material

- Run commands in a disposable VM or container when they modify networking,
  mounts, users, services, or kernel state.
- Check the local manual page (`man command`) because options vary by GNU,
  util-linux, BusyBox, and BSD implementations.
- Prefer read-only inspection first: observe with `ps`, `ss`, `ip`, `df`,
  `findmnt`, `/proc`, and tracing tools before applying a change.
- Treat examples containing `sudo`, `rm`, `kill`, firewall rules, or mounts as
  demonstrations, not copy-paste production procedures.
- Follow links within this track for depth, then cross back to OS, Networks,
  Security, Storage, and Cloud chapters for the interview-level trade-offs.

## Source and reference policy

The educational Markdown was imported from `lb2` without its Git history,
workflows, generated output, JavaScript/CSS deployment files, or repository
metadata. Relative links were rewritten to the integrated paths; stale source
links were converted to nearby explanatory text rather than left broken.

Primary references used for the original additions and for checking current
command behaviour:

- [Linux kernel documentation](https://docs.kernel.org/)
- [Linux man-pages project](https://man7.org/linux/man-pages/)
- [GNU Coreutils manual](https://www.gnu.org/software/coreutils/manual/)
- [GNU Findutils manual](https://www.gnu.org/software/findutils/manual/)
- [Bash Reference Manual](https://www.gnu.org/software/bash/manual/)
- [Open Group POSIX utilities](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [systemd documentation](https://systemd.io/)
- [eBPF documentation](https://ebpf.io/docs/)
- [curl documentation](https://curl.se/docs/)
- [OpenSSH manuals](https://man.openbsd.org/)

See the individual chapters for topic-specific references.
