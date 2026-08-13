# Further Reading

A curated collection of books, websites, courses, tutorials, and other resources
for learning Linux in depth. Resources are organized by topic and difficulty level.

---

## Books

### Essential Books — Start Here

#### *Linux Kernel Development* (3rd Edition) — Robert Love
The best introduction to Linux kernel internals. Covers process management, scheduling,
system calls, memory management, the VFS, and more. Written in an accessible style with
real kernel source examples.

- **Author:** Robert Love
- **Publisher:** Addison-Wesley, 2010
- **ISBN:** 978-0672329463
- **Level:** Intermediate
- **Topics:** Kernel architecture, process management, scheduling, system calls, interrupt handling, kernel synchronization, memory management, VFS, page cache, block I/O, module programming
- **Best for:** Developers who want to understand how the kernel works
- **Companion:** [lwn.net](https://lwn.net/) for ongoing kernel development news

#### *Understanding the Linux Kernel* (3rd Edition) — Daniel P. Bovet, Marco Cesati
The definitive deep dive into Linux kernel internals. More detailed and academic than
Love's book. Covers data structures, memory addressing, processes, interrupts, timing,
synchronization, memory management, process scheduling, I/O, and filesystems in extraordinary detail.

- **Authors:** Daniel P. Bovet, Marco Cesati
- **Publisher:** O'Reilly Media, 2005
- **ISBN:** 978-0596005658
- **Level:** Advanced
- **Topics:** Kernel data structures, memory addressing, processes, interrupts, timing, synchronization, memory management, scheduling, I/O architecture, block device drivers, VFS, ext2/ext3
- **Best for:** Those who want a complete understanding of kernel internals
- **Note:** Based on 2.6 kernel, but concepts remain relevant

#### *The Linux Programming Interface* — Michael Kerrisk
The definitive reference for Linux and UNIX system programming. Written by the maintainer
of the Linux man-pages project. Covers system calls, library functions, and programming
techniques with exceptional clarity.

- **Author:** Michael Kerrisk
- **Publisher:** No Starch Press, 2010
- **ISBN:** 978-1593272203
- **Level:** Intermediate to Advanced
- **Topics:** System calls, file I/O, processes, signals, threads, IPC (pipes, message queues, shared memory, semaphores), sockets, timers, daemons, capabilities, namespaces, seccomp
- **Best for:** Linux/UNIX system programmers
- **Website:** [man7.org/tlpi/](https://man7.org/tlpi/)

### Advanced and Specialized Books

#### *Linux Device Drivers* (3rd Edition) — Jonathan Corbet, Alessandro Rubini, Greg Kroah-Hartman
The classic guide to writing Linux device drivers. Covers char, block, and network drivers,
hardware management, interrupts, DMA, and the driver model.

- **Authors:** Jonathan Corbet, Alessandro Rubini, Greg Kroah-Hartman
- **Publisher:** O'Reilly Media, 2005
- **ISBN:** 978-0596005900
- **Level:** Advanced
- **Topics:** Kernel modules, char/block/net drivers, interrupts, DMA, PCI, USB, network drivers, TTY subsystem
- **Free online:** [lwn.net/LDP/LDD3/](https://lwn.net/Kernel/LDD3/)
- **Note:** Based on 2.6 kernel; check kernel source for API changes

#### *Linux Kernel in a Nutshell* — Greg Kroah-Hartman
A concise guide to building, installing, and configuring the Linux kernel.

- **Author:** Greg Kroah-Hartman
- **Publisher:** O'Reilly Media, 2006
- **ISBN:** 978-0596100797
- **Level:** Intermediate
- **Topics:** Kernel source, configuration, building, installation, kernel modules, debugging
- **Free online:** [kernel.org/pub/linux/kernel/people/gregkh/lkn/](http://www.kroah.com/lkn/)

#### *Professional Linux Kernel Architecture* — Wolfgang Mauerer
An in-depth analysis of kernel architecture with extensive source code analysis.

- **Author:** Wolfgang Mauerer
- **Publisher:** Wrox, 2008
- **ISBN:** 978-0470343432
- **Level:** Advanced

#### *Linux System Programming* (2nd Edition) — Robert Love
Direct system call and I/O programming. Covers file I/O, process management, memory management,
signals, timers, threading, and debugging.

- **Author:** Robert Love
- **Publisher:** O'Reilly Media, 2013
- **ISBN:** 978-1449339531
- **Level:** Intermediate

#### *UNIX and Linux System Administration Handbook* (5th Edition) — Evi Nemeth et al.
The "bible" of Linux/UNIX system administration. Comprehensive coverage of networking,
storage, security, monitoring, and troubleshooting.

- **Authors:** Evi Nemeth, Garth Snyder, Trent R. Hein, Ben Whaley, Dan Mackin
- **Publisher:** Addison-Wesley, 2017
- **ISBN:** 978-0134277554
- **Level:** Intermediate to Advanced
- **Best for:** System administrators

#### *How Linux Works* (3rd Edition) — Brian Ward
A practical guide to the Linux system. Explains how the boot process, kernel, networking,
and system administration work from the ground up.

- **Author:** Brian Ward
- **Publisher:** No Starch Press, 2021
- **ISBN:** 978-1718500402
- **Level:** Beginner to Intermediate

### Networking Books

#### *TCP/IP Illustrated, Volume 1* (2nd Edition) — W. Richard Stevens, Kevin R. Fall
The definitive reference on TCP/IP protocols. Essential for understanding Linux networking.

- **Authors:** W. Richard Stevens, Kevin R. Fall
- **Publisher:** Addison-Wesley, 2011
- **ISBN:** 978-0321336316
- **Level:** Advanced

#### *Linux Networking Cookbook* — Carla Schroder
Practical recipes for Linux networking. Covers routing, firewalls, VPNs, wireless, and more.

- **Author:** Carla Schroder
- **Publisher:** O'Reilly Media, 2007
- **ISBN:** 978-0596102487
- **Level:** Intermediate

### Security Books

#### *Linux Security Cookbook* — Daniel J. Barrett, Richard Silverman, Robert G. Byrnes
Practical security recipes for Linux systems.

#### *SELinux System Administration* (2nd Edition) — Sven Vermeulen
Comprehensive guide to SELinux configuration and administration.

### Container and Cloud Books

#### *Docker Deep Dive* — Nigel Poulton
A comprehensive guide to Docker and container technology.

#### *Kubernetes in Action* (2nd Edition) — Marko Lukša
Deep dive into Kubernetes container orchestration.

---

## Websites and Online Resources

### Essential Websites

#### [LWN.net](https://lwn.net/)
The premier source for Linux kernel development news. Weekly kernel development summaries,
in-depth articles on new features, and detailed coverage of the Linux development community.

- **Content:** Kernel development, free software news, conference coverage
- **Key feature:** [Kernel index](https://lwn.net/Kernel/Index) — comprehensive kernel topic index
- **Subscription:** Some content requires subscription after 2 weeks

#### [kernel.org](https://www.kernel.org/)
The official Linux kernel source repository. Download kernel source, view changelogs,
and track release candidates.

- **Content:** Kernel source tarballs, PGP signatures, changelogs
- **Key pages:**
  - [Kernel releases](https://www.kernel.org/category/releases.html)
  - [Git repositories](https://git.kernel.org/)
  - [Documentation](https://www.kernel.org/doc/html/latest/)

#### [The Linux Documentation Project (TLDP)](https://tldp.org/)
A comprehensive collection of Linux guides, HOWTOs, and FAQs.

- **Content:** HOWTOs, Guides, FAQs, Man pages
- **Notable guides:**
  - [Linux Installation and Getting Started](https://tldp.org/LDP/install-guide/)
  - [Advanced Bash-Scripting Guide](https://tldp.org/LDP/abs/html/)
  - [Bash Guide for Beginners](https://tldp.org/LDP/Bash-Beginners-Guide/html/)

#### [Linux Man Pages Online](https://man7.org/linux/man-pages/)
The authoritative online source for Linux man pages. Maintained by Michael Kerrisk.

- **Content:** All section 1-8 man pages, HTML formatted
- **Key feature:** Full-text search

### Kernel Development

#### [Kernel Newbies](https://kernelnewbies.org/)
Resources for Linux kernel beginners. Includes an FAQ, tutorials, and a helpful community.

- **Content:** Beginner guides, kernel coding style, first kernel patch tutorial
- **Key pages:**
  - [KernelNewbies FAQ](https://kernelnewbies.org/FAQ)
  - [Kernel Janitors](https://kernelnewbies.org/KernelJanitors)

#### [Linux Kernel Labs](https://linux-kernel-labs.github.io/)
Hands-on labs for learning Linux kernel development. Used in university courses.

- **Content:** Labs on kernel modules, character drivers, kernel debugging, scheduling, memory management
- **Format:** Step-by-step exercises with QEMU

#### [The Linux Kernel Module Programming Guide](https://tldp.org/LDP/lkmpg/2.6/html/)
A guide to writing Linux kernel modules.

#### [kernel.org Documentation](https://www.kernel.org/doc/html/latest/)
The kernel's own documentation in Sphinx format. Covers admin guides, driver APIs,
filesystem documentation, and security.

- **Key sections:**
  - [Admin Guide](https://www.kernel.org/doc/html/latest/admin-guide/)
  - [Development Process](https://www.kernel.org/doc/html/latest/process/)
  - [Driver API](https://www.kernel.org/doc/html/latest/driver-api/)
  - [Security](https://www.kernel.org/doc/html/latest/security/)

### Community and Q&A

#### [Ask Ubuntu](https://askubuntu.com/)
Q&A site for Ubuntu users. Great for distribution-specific questions.

#### [Unix & Linux Stack Exchange](https://unix.stackexchange.com/)
Q&A for Linux, BSD, and other UNIX-like systems. High-quality answers.

#### [Server Fault](https://serverfault.com/)
Q&A for system administrators and network professionals.

#### [Reddit — r/linux](https://www.reddit.com/r/linux/)
General Linux discussion. Also:
- [r/linuxadmin](https://www.reddit.com/r/linuxadmin/) — System administration
- [r/kernel](https://www.reddit.com/r/kernel/) — Kernel development
- [r/commandline](https://www.reddit.com/r/commandline/) — Command-line tools

### Distribution Documentation

#### [Arch Wiki](https://wiki.archlinux.org/)
The gold standard of Linux distribution documentation. Even non-Arch users find it invaluable.

- **Content:** Comprehensive guides on virtually every Linux topic
- **Key pages:**
  - [Installation guide](https://wiki.archlinux.org/title/Installation_guide)
  - [System administration](https://wiki.archlinux.org/title/System_administration)
  - [Networking](https://wiki.archlinux.org/title/Networking)
  - [Kernel](https://wiki.archlinux.org/title/Kernel)

#### [Ubuntu Documentation](https://help.ubuntu.com/)
Official Ubuntu documentation. Community-maintained and comprehensive.

#### [Fedora Documentation](https://docs.fedoraproject.org/)
Official Fedora project documentation.

#### [Gentoo Wiki](https://wiki.gentoo.org/)
Excellent technical documentation, especially for kernel configuration and optimization.

---

## Online Courses

### Free Courses

#### [Linux Foundation — Free Training Courses](https://training.linuxfoundation.org/full-catalog/?_sft_technology=linux)
The Linux Foundation offers several free introductory courses:

- **LFS101x** — Introduction to Linux (edX)
- **LFS101** — Introduction to Linux
- **LFS201** — Essentials of Linux System Administration

#### [Linux From Scratch](https://www.linuxfromscratch.org/)
A step-by-step guide to building your own Linux system from source code.

- **Content:** Building a complete Linux system from scratch
- **Difficulty:** Advanced
- **Key books:**
  - [Linux From Scratch](https://www.linuxfromscratch.org/lfs/) — Build a basic system
  - [Beyond Linux From Scratch](https://www.linuxfromscratch.org/blfs/) — Add packages

#### [OverTheWire — Bandit](https://overthewire.org/wargames/bandit/)
Learn Linux command line basics through a security wargame.

- **Difficulty:** Beginner
- **Format:** SSH into a server and solve challenges

#### [The Missing Semester of Your CS Education (MIT)](https://missing.csail.mit.edu/)
Covers shell, scripting, version control, and other practical computing skills.

- **Content:** Shell, scripting, editors, version control, debugging, security
- **Format:** Video lectures + exercises

### Paid Courses

#### [Linux Foundation Training](https://training.linuxfoundation.org/)
Official Linux Foundation courses and certifications.

- **LFCS** — Linux Foundation Certified System Administrator
- **LFCE** — Linux Foundation Certified Engineer
- **CKA** — Certified Kubernetes Administrator
- **CKAD** — Certified Kubernetes Application Developer

#### [Red Hat Training](https://www.redhat.com/en/services/training)
Official Red Hat training and certifications.

- **RHCSA** — Red Hat Certified System Administrator
- **RHCE** — Red Hat Certified Engineer

#### [Pluralsight / A Cloud Guru / Udemy](https://www.udemy.com/)
Various Linux courses from beginner to advanced. Look for highly-rated instructors.

---

## Tutorials and Guides

### Bash and Shell Scripting

#### [Bash Guide (Greg Wooledge)](https://mywiki.wooledge.org/BashGuide)
A comprehensive and accurate guide to Bash scripting.

#### [ShellCheck](https://www.shellcheck.net/)
A static analysis tool for shell scripts. Catches common errors and bad practices.

#### [Explain Shell](https://explainshell.com/)
Paste a shell command and get an explanation of each part.

### Networking

#### [Computer Networking: A Top-Down Approach — Wireshark Labs](https://gaia.cs.umass.edu/kurose_ross/wiwi.php)
Hands-on networking labs using Wireshark.

#### [Practical Networking](https://practicalnetworking.net/)
Clear explanations of networking concepts with practical examples.

### Containers

#### [Docker Documentation](https://docs.docker.com/)
Official Docker documentation with tutorials and references.

#### [Kubernetes Documentation](https://kubernetes.io/docs/)
Official Kubernetes documentation. Includes tutorials and concepts.

### Security

#### [Linux Security for Beginners](https://www.linuxsecurity.com/resource-center)
Security resources and tutorials.

#### [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
Security hardening benchmarks for Linux distributions.

---

## Video Resources

### YouTube Channels

#### [LiveOverflow](https://www.youtube.com/@LiveOverflow)
Security and hacking content. Excellent for understanding Linux security internals.

#### [DistroTube](https://www.youtube.com/@DistroTube)
Linux distribution reviews, tutorials, and open-source software.

#### [LearnLinuxTV](https://www.youtube.com/@LearnLinuxTV)
Linux tutorials and system administration guides.

#### [The Linux Experiment](https://www.youtube.com/@TheLinuxExperiment)
Linux news, reviews, and tutorials.

### Conference Talks

#### [Linux Plumbers Conference](https://lpc.events/)
The premier conference for Linux developers. Talks cover kernel, networking, security, and more.

#### [Kernel Recipes](https://kernel-recipes.org/)
European conference focused on Linux kernel development.

#### [All Systems Go!](https://all-systems-go.io/)
Conference on systemd, low-level user space, and containers.

---

## Podcasts

#### [Linux Unplugged](https://linuxunplugged.com/)
Weekly Linux discussion podcast.

#### [LINUX Unplugged](https://latenightlinux.com/)
Linux and open-source news and discussion.

#### [Kernel Report](https://www.kernel.org/)
Periodic updates on Linux kernel development.

---

## Reference Tools

#### [Explainshell](https://explainshell.com/)
Break down shell commands into their component parts.

#### [tldr pages](https://tldr.sh/)
Simplified and community-driven man pages. Install the client:
```bash
npm install -g tldr
tldr tar
```

#### [commandlinefu.com](https://www.commandlinefu.com/)
Community-driven repository of command-line tricks and tips.

#### [cheat.sh](https://cheat.sh/)
Unified command-line cheat sheet service:
```bash
curl cheat.sh/tar
curl cheat.sh/find
curl cheat.sh/python/lambda
```

#### [tldr.inbrowser.app](https://tldr.inbrowser.app/)
Web-based tldr pages viewer.

---

## Kernel Source References

#### [Linux Kernel Source (GitHub Mirror)](https://github.com/torvalds/linux)
GitHub mirror of the official kernel repository. Easier to browse than kernel.org.

#### [elixir.bootlin.com](https://elixir.bootlin.com/)
Linux kernel source cross-reference. Search for symbols, types, and functions across all kernel versions.

#### [kernel.org Git](https://git.kernel.org/)
Official git repositories for the Linux kernel and related projects.

#### [LKML (Linux Kernel Mailing List)](https://lkml.org/)
The Linux Kernel Mailing List. Where kernel development is discussed.

#### [lore.kernel.org](https://lore.kernel.org/)
Archived kernel mailing lists. Searchable. Better than LKML for finding specific patches.

---

## Modern Kernel Development

### Rust in the Linux Kernel

Linux 6.1 (2022) added initial Rust support. By 2025, Rust is increasingly used for new kernel modules:

- **[Rust for Linux Documentation](https://docs.kernel.org/rust/)** — Official kernel Rust docs
- **[Rust Kernel Modules Book](https://rust-for-linux.com/)** — Guide to writing kernel modules in Rust
- **[LWN: Rust in the kernel](https://lwn.net/Articles/rust-kernel/)** — Ongoing coverage of Rust adoption
- **[Asahi Linux](https://asahilinux.org/)** — Apple Silicon support with Rust GPU drivers

### eBPF

eBPF (extended Berkeley Packet Filter) has become a major kernel programmability mechanism:

- **[eBPF.io](https://ebpf.io/)** — Official eBPF documentation and tutorials
- **[BPF Performance Tools (Brendan Gregg)](https://www.brendangregg.com/bpf-performance-tools-book.html)** — The definitive book on BPF-based performance analysis
- **[Cilium BPF Documentation](https://docs.cilium.io/en/latest/bpf/)** — Deep BPF documentation
- **[bpftrace Reference Guide](https://github.com/bpftrace/bpftrace/blob/master/docs/reference_guide.md)** — bpftrace language reference
- **[libbpf-bootstrap](https://github.com/libbpf/libbpf-bootstrap)** — Template for BPF CO-RE applications

### io_uring

io_uring is Linux's modern async I/O interface (kernel 5.1+):

- **[io_uring and networking in 2024 (Axboe)](https://kernel.dk/io_uring.pdf)** — Jens Axboe's overview
- **[LWN: io_uring](https://lwn.net/Kernel/Index/#io_uring)** — LWN coverage
- **[liburing](https://github.com/axboe/liburing)** — Userspace io_uring library

---

## Performance and Observability

### Books

- **[BPF Performance Tools](https://www.brendangregg.com/bpf-performance-tools-book.html)** — Brendan Gregg (2019). Linux performance analysis with BPF.
- **[Systems Performance](https://www.brendangregg.com/systems-performance-2nd-edition-book.html)** — Brendan Gregg (2020). Enterprise and cloud performance analysis.
- **[Performance Analysis and Tuning on Modern CPUs](https://book.easyperf.net/perf_book)** — Denis Bakhvalov (2020). CPU-level performance tuning.

### Tools and References

- **[Brendan Gregg's Linux Performance](https://www.brendangregg.com/linuxperf.html)** — One-page Linux performance tools diagram
- **[USE Method](https://www.brendangregg.com/usemethod.html)** — Utilization, Saturation, Errors methodology
- **[Flame Graphs](https://www.brendangregg.com/flamegraphs.html)** — CPU/profile visualization technique
- **[bcc-tools](https://github.com/iovisor/bcc)** — BPF Compiler Collection (Python-based BPF tools)

---

## Security Resources

### Books

- **[Linux Kernel Security (LWN)](https://lwn.net/Kernel/Index/#Security)** — Comprehensive security topic index
- **[The Art of Software Security Assessment](https://www.amazon.com/Art-Software-Security-Assessment-Vulnerabilities/dp/0321444426)** — Mark Dowd et al. Covers kernel exploitation.
- **[A Guide to Kernel Exploitation](https://www.amazon.com/Guide-Kernel-Exploitation-Attacking-Core/dp/1597494860)** — Attacking the kernel.

### References

- **[kernel-hardening mailing list](https://lore.kernel.org/kernel-hardening/)** — Kernel security hardening patches
- **[Kconfig-hardened](https://github.com/a13xp0p0v/kconfig-hardened-check)** — Tool to check kernel security configuration
- **[KSPP (Kernel Self Protection Project)](https://kspp.github.io/)** — Kernel self-protection initiative

---

## Distribution-Specific Resources

### Arch Linux

- **[Arch Wiki](https://wiki.archlinux.org/)** — Exceptional documentation for all Linux topics
- **[Arch Linux Forums](https://bbs.archlinux.org/)** — Active community

### Ubuntu

- **[Ubuntu Wiki](https://wiki.ubuntu.com/)** — Ubuntu-specific documentation
- **[Ask Ubuntu](https://askubuntu.com/)** — Q&A site (Stack Exchange)

### RHEL / Fedora

- **[Red Hat Documentation](https://docs.redhat.com/)** — Enterprise Linux docs
- **[Fedora Wiki](https://fedoraproject.org/wiki/)** — Fedora project wiki

### Gentoo

- **[Gentoo Wiki](https://wiki.gentoo.org/)** — Excellent kernel and optimization docs
- **[Gentoo Forums](https://forums.gentoo.org/)** — Technical discussions

### Debian

- **[Debian Handbook](https://debian-handbook.info/)** — Comprehensive Debian administration guide, free online
- **[Debian Wiki](https://wiki.debian.org/)** — Community-maintained documentation

### openSUSE

- **[openSUSE Documentation](https://doc.opensuse.org/)** — Official docs with YaST and Btrfs focus
- **[openSUSE Wiki](https://en.opensuse.org/Portal:Wiki)** — Community wiki

---

## Podcasts and Newsletters

### Podcasts

- **[Linux Unplugged](https://linuxunplugged.com/)** — Weekly Linux discussion podcast
- **[Late Night Linux](https://latenightlinux.com/)** — Linux and open-source news
- **[Kernel Report](https://www.kernel.org/)** — Periodic kernel development updates
- **[The Linux Cast](https://thelinuxcast.com/)** — Linux news and tutorials
- **[BSD Now](https://www.bsdnow.tv/)** — BSD and UNIX news (relevant to Linux users)

### Newsletters

- **[LWN.net Weekly Edition](https://lwn.net/)** — Premier kernel/free software newsletter (subscription recommended)
- **[Phoronix](https://www.phoronix.com/)** — Linux hardware and kernel news
- **[The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/)** — Engineering deep dives including kernel topics
- **[This Week in Rust](https://this-week-in-rust.org/)** — Rust ecosystem news (relevant for kernel Rust)
- **[Brendan Gregg's Blog](https://www.brendangregg.com/blog/)** — Performance and observability articles

---

## Community and Q&A

#### [Ask Ubuntu](https://askubuntu.com/)
Q&A site for Ubuntu users. Great for distribution-specific questions.

#### [Unix & Linux Stack Exchange](https://unix.stackexchange.com/)
Q&A for Linux, BSD, and other UNIX-like systems. High-quality answers.

#### [Server Fault](https://serverfault.com/)
Q&A for system administrators and network professionals.

#### [Reddit](https://www.reddit.com/)
- [r/linux](https://www.reddit.com/r/linux/) — General Linux discussion
- [r/linuxadmin](https://www.reddit.com/r/linuxadmin/) — System administration
- [r/kernel](https://www.reddit.com/r/kernel/) — Kernel development
- [r/commandline](https://www.reddit.com/r/commandline/) — Command-line tools
- [r/linuxquestions](https://www.reddit.com/r/linuxquestions/) — Linux help

#### [Kernel Newbies](https://kernelnewbies.org/)
Resources for Linux kernel beginners. Includes an FAQ, tutorials, and a helpful community.

- **Content:** Beginner guides, kernel coding style, first kernel patch tutorial
- **Key pages:**
  - [KernelNewbies FAQ](https://kernelnewbies.org/FAQ)
  - [Kernel Janitors](https://kernelnewbies.org/KernelJanitors)
  - [Kernel Newbies Tutorial](https://kernelnewbies.org/KernelTutorial)

---

## Reference Tools

#### [Explainshell](https://explainshell.com/)
Break down shell commands into their component parts.

#### [tldr pages](https://tldr.sh/)
Simplified and community-driven man pages. Install the client:
```bash
npm install -g tldr
tldr tar
```

#### [commandlinefu.com](https://www.commandlinefu.com/)
Community-driven repository of command-line tricks and tips.

#### [cheat.sh](https://cheat.sh/)
Unified command-line cheat sheet service:
```bash
curl cheat.sh/tar
curl cheat.sh/find
curl cheat.sh/python/lambda
```

#### [tldr.inbrowser.app](https://tldr.inbrowser.app/)
Web-based tldr pages viewer.

#### [DevDocs](https://devdocs.io/)
API documentation browser. Includes Linux man pages.

#### [cpuid](https://github.com/tycho/cpuid)
Detailed CPU feature information from the command line.

---

## Related Chapters

- [Glossary](glossary.md) — Definitions of terms used in these resources
- [Man Pages](man-pages.md) — How to use Linux documentation
- [Kernel Config](kernel-config.md) — Kernel configuration reference
- [Syscall Table](syscall-table.md) — System call interfaces
- [Commands Reference](commands.md) — Essential Linux commands
