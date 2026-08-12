# Linux Glossary

A comprehensive glossary of Linux and related terminology used throughout this book.
Terms are organized alphabetically; cross-references link to detailed explanations elsewhere.

---

## A

**ACL (Access Control List)**
A list of permissions attached to an object (file, directory) that specifies which users or system processes are granted access and what operations are allowed. See `getfacl(1)`, `setfacl(1)`.

**Address Space**
The range of memory addresses available to a process. Each process has its own virtual address space managed by the kernel. See [Syscall Table](syscall-table.md) for `mmap`, `brk`.

**AGP (Accelerated Graphics Port)**
A high-speed point-to-point channel for attaching a video card to the system motherboard. Largely superseded by PCI Express.

**Anacron**
A periodic command scheduler that does not assume the system is running continuously. Complements `cron` for laptops and workstations.

**API (Application Programming Interface)**
A set of functions, protocols, and tools for building software. Linux exposes APIs through system calls, library functions, and kernel interfaces.

**AppArmor**
A Linux Security Module (LSM) that confines programs based on per-program profiles loaded at boot. Alternative to SELinux with a simpler syntax.

**ASLR (Address Space Layout Randomization)**
A security technique that randomizes the memory address positions of key data areas (stack, heap, shared libraries) to prevent exploitation.

**ATA (AT Attachment)**
A standard interface for connecting storage devices. Includes PATA (parallel) and SATA (serial) variants. See `/dev/sd*`.

**auditd**
The Linux Audit daemon. Logs system calls and security-relevant events for compliance and intrusion detection.

**Autofs**
A kernel-based automounter that automatically mounts filesystems on demand (e.g., NFS shares when accessed).

**awk**
A powerful text-processing language. Used extensively in shell pipelines for column extraction, pattern matching, and data transformation.

---

## B

**bind mount**
A mount operation that makes a directory visible at another location in the filesystem tree. Created with `mount --bind`.

**BIOS (Basic Input/Output System)**
Firmware interface that initializes hardware during the boot process. Superseded by UEFI on modern systems.

**Block Device**
A device that transfers data in fixed-size blocks (e.g., hard drives, SSDs). Appears under `/dev/`. Contrast with character devices.

**Bootloader**
Software that loads the operating system kernel into memory. Common Linux bootloaders: GRUB2, systemd-boot, Syslinux.

**BPF (Berkeley Packet Filter)**
A technology for running sandboxed programs in the Linux kernel. Extended BPF (eBPF) enables tracing, networking, and security observability without kernel modules.

**Bridge**
A network device that forwards traffic between two or more network segments at Layer 2. Implemented via `bridge` or `brctl` commands.

**Btrfs**
A copy-on-write (CoW) filesystem for Linux supporting snapshots, checksums, compression, RAID, and subvolumes. See [Kernel Config](kernel-config.md) `CONFIG_BTRFS_FS`.

**Buffer Cache**
Kernel memory that caches recently read disk blocks to avoid repeated I/O. Managed by the page cache subsystem.

**Built-in Command**
A command built into the shell itself (e.g., `cd`, `echo`, `export`). Does not require an external binary. See `type` command.

---

## C

**cgroup (Control Group)**
A Linux kernel feature that limits, accounts for, and isolates the resource usage (CPU, memory, I/O, network) of process groups. Foundation for container runtimes. See [Kernel Config](kernel-config.md) `CONFIG_CGROUPS`.

**Character Device**
A device that transfers data character by character (e.g., terminals, serial ports, `/dev/null`). Contrast with block devices.

**chroot**
An operation that changes the apparent root directory for a process, providing filesystem isolation. Predecessor to containers.

**CIFS (Common Internet File System)**
The modern SMB protocol used for Windows file sharing. Linux client: `mount -t cifs`. Server: Samba.

**CLI (Command-Line Interface)**
A text-based interface for interacting with the computer via typed commands. See [Commands Reference](commands.md).

**Container**
An isolated user-space instance sharing the host kernel. Implemented using namespaces, cgroups, and seccomp. Runtimes: Docker, Podman, containerd, CRI-O.

**Core Dump**
A file containing the memory image of a crashed process, used for post-mortem debugging. Controlled by `ulimit -c` and `/proc/sys/kernel/core_pattern`.

**CPU Affinity**
Binding a process to specific CPU cores using `taskset` or `sched_setaffinity(2)`.

**cron**
A time-based job scheduler daemon. Reads crontab files from `/etc/crontab`, `/var/spool/cron/`, and `/etc/cron.d/`.

**CRUD**
Create, Read, Update, Delete — the four basic operations on data.

**cURL**
A command-line tool for transferring data with URLs. Supports HTTP, HTTPS, FTP, SCP, and many more protocols.

---

## D

**DAC (Discretionary Access Control)**
The traditional Unix permission model where the owner of a resource controls who can access it. Contrast with MAC (Mandatory Access Control).

**daemon**
A background process that runs without direct user interaction. Typically starts at boot via systemd or init. Examples: `sshd`, `httpd`, `cron`.

**DDoS (Distributed Denial of Service)**
A cyberattack where multiple compromised systems flood a target with traffic.

**debugfs**
An interactive filesystem debugger for ext2/ext3/ext4. Also a virtual filesystem mounted at `/sys/kernel/debug/` for kernel debugging information.

**Device File**
A special file in `/dev/` that provides an interface to a device driver. Can be block or character type. Created by `udevd` or `devtmpfs`.

**Device Tree**
A data structure describing hardware components to the kernel, common on ARM platforms. Files: `*.dts` (source), `*.dtb` (binary).

**DHCP (Dynamic Host Configuration Protocol)**
A network management protocol that automatically assigns IP addresses and network configuration to devices. Server: `dhcpd`, Client: `dhclient`.

**Disk Quota**
Limits on disk space or number of files per user/group. Managed via `quotacheck`, `quotaon`, `edquota`.

**Distribution (Distro)**
A packaged Linux operating system. Major families: Debian/Ubuntu, RHEL/Fedora, Arch, SUSE, Gentoo.

**DNS (Domain Name System)**
The hierarchical naming system that translates domain names to IP addresses. Resolver: `/etc/resolv.conf`. Server: BIND, Unbound, dnsmasq.

**Docker**
A platform for developing, shipping, and running applications in containers. Uses namespaces, cgroups, and overlay filesystems.

**DTrace**
A dynamic tracing framework (originally from Solaris). Linux equivalent: BPF/eBPF, ftrace, SystemTap.

**dmesg**
A command that displays kernel ring buffer messages. Essential for hardware debugging and boot troubleshooting.

---

## E

**eBPF (extended BPF)**
A kernel technology for running sandboxed programs in privileged context. Used for tracing (bpftrace), networking (XDP), and security (Falco). See [Kernel Config](kernel-config.md) `CONFIG_BPF_SYSCALL`.

**ECC (Error-Correcting Code)**
Memory that can detect and correct data corruption. Used in servers for reliability.

**EFI System Partition (ESP)**
A FAT-formatted partition that stores UEFI boot loaders and related files. Typically mounted at `/boot/efi`.

**ELF (Executable and Linkable Format)**
The standard binary format for executables, object code, shared libraries, and core dumps on Linux.

**encryption**
The process of encoding data so only authorized parties can read it. Linux tools: LUKS, dm-crypt, GPG, OpenSSL.

**epoll**
A scalable I/O event notification mechanism. Replaces `select(2)` and `poll(2)` for large numbers of file descriptors. See `epoll_create(2)`, `epoll_wait(2)`.

**ext4**
The default filesystem for many Linux distributions. Fourth extended filesystem with journaling, extents, and large file support. See [Kernel Config](kernel-config.md) `CONFIG_EXT4_FS`.

---

## F

**FAT (File Allocation Table)**
A simple filesystem family (FAT12, FAT16, FAT32, exFAT). Used on USB drives and SD cards. Linux kernel module: `vfat`.

**fd (file descriptor)**
A non-negative integer representing an open file, socket, pipe, or device. Standard: 0=stdin, 1=stdout, 2=stderr. See `/proc/[pid]/fd/`.

**FHS (Filesystem Hierarchy Standard)**
The directory structure standard for Linux systems. Defines `/bin`, `/sbin`, `/etc`, `/var`, `/usr`, `/home`, etc.

**FIFO (First In, First Out)**
A named pipe. A special file for inter-process communication where data is read in the order written. Created with `mkfifo(1)`.

**Firewall**
A network security system that monitors and controls traffic. Linux: iptables/nftables (packet filtering), firewalld (management daemon).

**firmware**
Software embedded in hardware devices. Stored in `/lib/firmware/`. Loaded by the kernel at device initialization.

**FUSE (Filesystem in Userspace)**
A mechanism allowing non-privileged users to create filesystems without kernel code. Examples: sshfs, ntfs-3g, fuse-zip.

**ftrace**
The Linux kernel's internal tracer for function calls, latency, and events. Interface: `/sys/kernel/debug/tracing/`.

---

## G

**GCC (GNU Compiler Collection)**
The standard C/C++ compiler for Linux. Also supports Fortran, Ada, Go, and others. `gcc --version` to check.

**GDB (GNU Debugger)**
The standard debugger for Linux. Supports C, C++, Rust, and more. Use with `gdb ./program` or attach to running process with `-p PID`.

**GID (Group Identifier)**
A numeric identifier for a group in the Linux permission system. Mapped in `/etc/group`.

**GNU (GNU's Not Unix)**
The free software project providing most userland tools for Linux (coreutils, bash, gcc, gdb, etc.).

**GPG (GNU Privacy Guard)**
A free implementation of the OpenPGP standard for encryption and digital signing.

**GPL (GNU General Public License)**
A widely used free software license. The Linux kernel is licensed under GPLv2.

**GRUB (GRand Unified Bootloader)**
The most common Linux bootloader. GRUB2 configuration: `/boot/grub/grub.cfg` (generated by `grub-mkconfig`).

**Guest OS**
An operating system running inside a virtual machine, as opposed to the host OS that runs the hypervisor.

---

## H

**HAL (Hardware Abstraction Layer)**
A layer that provides a uniform interface to hardware. Modern Linux uses udev and sysfs instead of HAL.

**Hard Link**
A directory entry that maps a filename to an existing inode. Multiple hard links share the same inode number. Cannot cross filesystems. See `ln(1)`.

**Header File**
C header files (`.h`) in `/usr/include/` and kernel headers in `/usr/src/linux-headers-*`. Required for compiling kernel modules and programs.

**heartbeat**
A periodic signal indicating a system or service is alive. Used in high-availability clusters.

**Huge Pages**
Large memory pages (2MB or 1GB) that reduce TLB misses for memory-intensive workloads. Configured via `/proc/sys/vm/nr_hugepages`.

**Hypervisor**
Software that creates and runs virtual machines. Type 1 (bare-metal): KVM, Xen. Type 2 (hosted): VirtualBox, VMware Workstation.

---

## I

**inode**
A data structure containing metadata about a file (permissions, ownership, timestamps, data block pointers). Does not contain the filename. See `stat(1)`, `ls -i`.

**init**
The first process (PID 1) started by the kernel. Traditionally SysVinit; modern systems use systemd.

**initrd / initramfs**
A temporary root filesystem loaded into memory during boot. Contains drivers needed to mount the real root filesystem. See [Kernel Config](kernel-config.md) `CONFIG_BLK_DEV_INITRD`.

**Interrupt**
A signal from hardware or software that causes the CPU to stop current execution and handle the event. Hardware IRQs are listed in `/proc/interrupts`.

**IO Scheduler**
Kernel component that reorders I/O requests for efficiency. Linux offers mq-deadline, bfq, kyber, and none (for NVMe). See `/sys/block/*/queue/scheduler`.

**IPC (Inter-Process Communication)**
Mechanisms for data exchange between processes: pipes, message queues, shared memory, semaphores, sockets, signals.

**iptables**
The traditional Linux packet filtering framework. Successor: nftables. Chains: INPUT, OUTPUT, FORWARD. Tables: filter, nat, mangle, raw.

**I/O uring**
A high-performance asynchronous I/O interface introduced in Linux 5.1. See `io_uring_setup(2)`.

---

## J

**JFS (Journaled File System)**
A high-performance journaling filesystem originally from IBM AIX.

**Journal**
A log of filesystem changes that enables quick recovery after a crash. Used by ext4, XFS, Btrfs, JFS.

**Journalctl**
The systemd journal query tool. Use `journalctl -u service` for service logs, `-f` to follow, `--since` for time ranges.

**Journald**
The systemd journal daemon that collects and stores system logs. Replaces traditional syslog for many distributions.

---

## K

**KASAN (Kernel Address Sanitizer)**
A dynamic memory error detector for the Linux kernel. Detects use-after-free, out-of-bounds access. See [Kernel Config](kernel-config.md) `CONFIG_KASAN`.

**Kconfig**
The Linux kernel's configuration system. Used by `make menuconfig`, `make xconfig`, etc. Files: `Kconfig` in each source directory.

**Kdump**
A kernel crash dumping mechanism. Uses a secondary kernel (kexec) to capture memory dumps after a crash.

**Kerberos**
A network authentication protocol using tickets. Integrated with Active Directory. Tools: `kinit`, `klist`, `kdestroy`.

**Kernel**
The core of the operating system. Manages hardware, processes, memory, filesystems, and networking. See [Kernel Config](kernel-config.md).

**Kernel Module**
Loadable code that extends kernel functionality at runtime. Commands: `lsmod`, `modprobe`, `insmod`, `rmmod`. See `modprobe(8)`.

**Kernel Space**
Memory region where the kernel executes with full hardware access. Contrast with user space.

**kexec**
A system call that loads and boots into another kernel from the running kernel. Used for fast reboots and crash dumps.

**KVM (Kernel-based Virtual Machine)**
A Linux kernel module that turns the kernel into a hypervisor. Uses hardware virtualization (VT-x/AMD-V).

---

## L

**LACP (Link Aggregation Control Protocol)**
A protocol for combining multiple network links into a single logical link for increased bandwidth and redundancy.

**LDAP (Lightweight Directory Access Protocol)**
A protocol for accessing distributed directory services. Commonly used for centralized authentication.

**LVM (Logical Volume Manager)**
A device mapper framework providing logical volume management. Allows flexible disk allocation, resizing, and snapshots. Components: PV, VG, LV.

**LSM (Linux Security Module)**
A framework for implementing security policies. Supports SELinux, AppArmor, TOMOYO, Smack, and others.

**Loadable Kernel Module (LKM)**
See Kernel Module.

**Loopback Device**
A virtual device (`lo`) that routes traffic back to the same host. Network: 127.0.0.1/8. Block: `/dev/loop*` for mounting files as devices.

**LUKS (Linux Unified Key Setup)**
A disk encryption specification. Used with dm-crypt for transparent filesystem encryption. Tools: `cryptsetup`, `luksFormat`.

---

## M

**MAC (Mandatory Access Control)**
A security model where access policies are enforced by the system, not the resource owner. Implemented by SELinux, AppArmor.

**Magic SysRq**
A key combination (Alt+SysRq+key) that allows low-level kernel commands regardless of system state. Enabled via `/proc/sys/kernel/sysrq`.

**Makefile**
A build automation file defining how to compile and link programs. The kernel build system uses Kbuild (Makefile-based).

**MBR (Master Boot Record)**
The first 512-byte sector of a disk containing the partition table and bootloader code. Superseded by GPT.

**Memory-Mapped I/O (MMIO)**
Accessing device registers through memory addresses. The kernel maps device memory into the virtual address space.

**Mergerfs**
A union filesystem for combining multiple mount points into a single virtual filesystem. Popular for storage pooling.

**Metadata**
Data about data. In filesystems: inodes, directory entries, extended attributes. In networking: headers, trailers.

**mkinitramfs / dracut**
Tools for generating the initial RAM filesystem (initramfs) used during boot.

**mount**
The operation of making a filesystem accessible at a directory point. Managed by `/etc/fstab` for persistence. See `mount(8)`.

**MQ (Multi-Queue)**
Modern block device architecture using multiple hardware queues for parallel I/O. Essential for NVMe performance.

---

## N

**namespace**
A Linux kernel feature that partitions kernel resources so that one set of processes sees one set of resources while another set sees a different set. Types: PID, NET, MNT, UTS, IPC, USER, CGROUP. Foundation for containers.

**NAS (Network Attached Storage)**
A dedicated file storage device providing data access to a network. Protocols: NFS, SMB/CIFS.

**Netfilter**
The kernel framework for packet filtering, NAT, and connection tracking. Hooks: PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING.

**NetworkManager**
A daemon for managing network connections. Tools: `nmcli`, `nmtui`, `nm-applet`.

**NFS (Network File System)**
A distributed filesystem protocol allowing a user to access files over a network. Server: `nfs-kernel-server`. Client: `mount -t nfs`.

**nftables**
The successor to iptables. Provides a unified framework for packet filtering with a simpler syntax. Command: `nft`.

**NOHZ (No HZ)**
A kernel configuration that reduces timer interrupts on idle CPUs for power savings. See [Kernel Config](kernel-config.md) `CONFIG_NO_HZ_IDLE`.

**NUMA (Non-Uniform Memory Access)**
A memory architecture where memory access time depends on the memory's location relative to the processor. Tools: `numactl`, `numastat`.

---

## O

**OOM Killer (Out of Memory Killer)**
A kernel mechanism that terminates processes when the system is critically low on memory. Adjusted via `/proc/[pid]/oom_score_adj`.

**OpenSSH**
The premier connectivity tool for remote login using the SSH protocol. Components: `ssh`, `scp`, `sftp`, `sshd`, `ssh-keygen`.

**OpenSSL**
A robust toolkit for TLS/SSL and general-purpose cryptography. Commands: `openssl req`, `openssl s_client`, `openssl enc`.

**OverlayFS**
A union mount filesystem that combines multiple directories into one. Used by Docker for image layers. See [Kernel Config](kernel-config.md) `CONFIG_OVERLAY_FS`.

---

## P

**Page**
The smallest unit of memory management (typically 4KB). The kernel allocates and manages memory in pages.

**Page Cache**
Kernel memory caching file contents and block device data in RAM. Reduces disk I/O significantly.

**Partition**
A logical division of a disk. Tools: `fdisk`, `parted`, `gdisk`. Types: primary, extended, logical (MBR) or standard (GPT).

**PCI (Peripheral Component Interconnect)**
A standard for connecting hardware devices. Modern variant: PCIe. View devices with `lspci`.

**PID (Process Identifier)**
A unique number assigned to each running process. PID 1 is init/systemd. See `/proc/[pid]/`.

**Pipe**
A unidirectional inter-process communication channel. Anonymous pipes: `cmd1 | cmd2`. Named pipes (FIFOs): `mkfifo`.

**POSIX (Portable Operating System Interface)**
A family of standards for maintaining compatibility between operating systems. Linux is largely POSIX-compliant.

**procfs**
A virtual filesystem mounted at `/proc/` exposing kernel and process information. Essential for system monitoring and debugging.

**Process**
A running program instance. Consists of address space, file descriptors, signal handlers, and execution context.

**PulseAudio / PipeWire**
Sound server systems. PipeWire is the modern replacement for PulseAudio, handling audio and video streams.

---

## Q

**QEMU**
A generic and open-source machine emulator and virtualizer. Often used with KVM for hardware-accelerated virtualization.

**Quantum**
The time slice allocated to a process by the scheduler. Linux uses the Completely Fair Scheduler (CFS) with dynamic time slices.

---

## R

**RAID (Redundant Array of Independent Disks)**
A storage technology combining multiple drives for performance and/or redundancy. Levels: 0, 1, 5, 6, 10. Tools: `mdadm`.

**RAM (Random Access Memory)**
Volatile memory used by running programs and the kernel for data storage. Managed by the kernel's memory subsystem.

**Real-Time (RT)**
A system with deterministic timing guarantees. Linux supports RT scheduling policies: `SCHED_FIFO`, `SCHED_RR`. See `chrt(1)`.

**RPM (RPM Package Manager)**
A package management system used by RHEL, Fedora, CentOS, SUSE. Tools: `rpm`, `yum`, `dnf`.

**rsync**
A fast, versatile file-copying tool that transfers only changed portions of files. Common: `rsync -avz src/ user@host:/dest/`.

**runlevel**
A SysVinit concept defining the system state. Modern equivalent: systemd targets (`multi-user.target`, `graphical.target`).

---

## S

**SAN (Storage Area Network)**
A high-speed network providing block-level storage access. Protocols: iSCSI, Fibre Channel, NVMe-oF.

**Scheduler**
The kernel component that decides which process runs on which CPU. Linux default: CFS (Completely Fair Scheduler). RT: SCHED_FIFO, SCHED_RR.

**seccomp (Secure Computing Mode)**
A kernel facility that restricts system calls a process can make. Used by containers and sandboxes for security. See [Kernel Config](kernel-config.md) `CONFIG_SECCOMP`.

**SELinux (Security-Enhanced Linux)**
A mandatory access control (MAC) security module. Uses security contexts and policies for fine-grained access control.

**Semaphore**
A synchronization primitive used for controlling access to shared resources in concurrent programming.

**Shell**
A command-line interpreter. Common shells: bash, zsh, fish, dash, mksh. See `/etc/shells`.

**Signal**
A software interrupt delivered to a process. Common: SIGHUP(1), SIGINT(2), SIGKILL(9), SIGTERM(15), SIGSEGV(11). See `signal(7)`.

**SLAB / SLUB**
Kernel memory allocators for small objects. SLUB is the modern default. See `/proc/slabinfo`.

**SMB (Server Message Block)**
A network file-sharing protocol. Linux implementation: Samba. Client: `smbclient`, `mount -t cifs`.

**Snapshot**
A point-in-time copy of a filesystem or volume. Supported by LVM, Btrfs, ZFS. Used for backups and rollbacks.

**Socket**
An endpoint for network communication. Types: stream (TCP), datagram (UDP), raw. See `socket(2)`, `ss(8)`.

**Soft Link (Symbolic Link)**
A file that contains a path to another file. Can cross filesystems. Created with `ln -s`. See `symlink(2)`.

**SquashFS**
A compressed read-only filesystem. Used for live CDs, embedded systems, and Snap packages.

**SSH (Secure Shell)**
A cryptographic network protocol for secure remote access. See OpenSSH.

**Strace**
A diagnostic tool that traces system calls and signals. Essential for debugging: `strace -f -p PID`.

**Swap**
Disk space used as an extension of RAM. Can be a partition or file. Managed by the kernel's page reclaim mechanism. See `swapon(8)`.

**sysfs**
A virtual filesystem mounted at `/sys/` exposing kernel device model information. Complements procfs.

**systemd**
A system and service manager. Manages services (units), logging (journald), timers, networking (networkd), and more. See `systemctl(1)`.

**SysVinit**
The traditional System V init system. Uses `/etc/init.d/` scripts and runlevels. Superseded by systemd on most distributions.

---

## T

**TCP (Transmission Control Protocol)**
A reliable, connection-oriented transport protocol. Socket type: `SOCK_STREAM`. See `tcp(7)`.

**Terminal**
A text input/output environment. Types: physical (tty), virtual console, pseudo-terminal (pty), terminal emulator.

**Timer**
A kernel mechanism for scheduling future actions. Linux provides per-CPU timers, high-resolution timers, and hrtimers.

**tmpfs**
A memory-based filesystem mounted at `/tmp`, `/dev/shm`, `/run`. Contents are lost on unmount or reboot.

**TLS (Transport Layer Security)**
Cryptographic protocol for secure communication. Used in HTTPS, IMAPS, etc. Configuration: `/etc/ssl/`.

**TOMOYO**
A pathname-based mandatory access control Linux Security Module. Simpler than SELinux.

**Trap**
A software-generated interrupt. In shells: `trap 'command' SIGNAL` to handle signals.

**TTL (Time to Live)**
In networking: a field in IP packets limiting their lifetime (hop count). In DNS: the duration a record is cached.

**tty**
A teletypewriter; the original terminal device. Modern usage: any terminal device. See `tty(1)`, `/dev/tty*`.

---

## U

**udev**
The device manager for the Linux kernel. Dynamically creates and removes device nodes in `/dev/` based on rules in `/etc/udev/rules.d/`.

**UDP (User Datagram Protocol)**
A connectionless, unreliable transport protocol. Socket type: `SOCK_DGRAM`. See `udp(7)`.

**UEFI (Unified Extensible Firmware Interface)**
The modern firmware interface replacing BIOS. Supports GPT partitions, Secure Boot, and a graphical setup.

**UID (User Identifier)**
A numeric identifier for a user. Root is UID 0. Mapped in `/etc/passwd`. See `id(1)`.

**union mount**
A filesystem overlay that combines multiple directories into a single view. See OverlayFS, mergerfs.

**Unix**
The original operating system developed at Bell Labs. Linux is a Unix-like system, largely POSIX-compliant.

**User Space**
Memory and execution context where user processes run. Cannot directly access hardware. Contrast with kernel space.

**UUID (Universally Unique Identifier)**
A 128-bit identifier used for partition identification in `/etc/fstab` and other configurations. Generated by `uuidgen`.

---

## V

**Virtual Machine (VM)**
A software emulation of a physical computer. Runs a complete OS (guest) on a hypervisor. Technologies: KVM, VirtualBox, VMware.

**Virtual Memory**
A memory management technique that uses both RAM and disk to give processes the illusion of contiguous memory.

**VFS (Virtual Filesystem Switch)**
The kernel layer that provides a common interface for different filesystem implementations (ext4, XFS, procfs, etc.).

**VLAN (Virtual LAN)**
A logical subdivision of a network at Layer 2. Created with `ip link add link eth0 name eth0.10 type vlan id 10`.

**Volume Group (VG)**
A pool of storage from one or more physical volumes in LVM. See LVM.

**vmlinuz**
The compressed Linux kernel image. Located in `/boot/`. The bootloader loads it into memory at boot.

---

## W

**Wayland**
A display server protocol replacing X11. Compositors: Sway, GNOME Shell, KDE Plasma. See `WAYLAND_DISPLAY`.

**WAL (Write-Ahead Log)**
A logging technique where changes are written to a log before being applied. Used in databases and filesystems.

**WC (Word Count)**
A command-line utility. `wc -l` counts lines, `-w` words, `-c` bytes.

**workqueue**
A kernel mechanism for deferring work to be executed later in process context.

---

## X

**X11 (X Window System, Version 11)**
The traditional display server protocol for Unix-like systems. Implementation: X.Org Server. Successor: Wayland.

**XDP (eXpress Data Path)**
A high-performance programmable network data path in the Linux kernel. Uses eBPF for packet processing at the driver level.

**XFS**
A high-performance 64-bit journaling filesystem. Default on RHEL 7+. Supports online resizing, quotas, and reflinks. See [Kernel Config](kernel-config.md) `CONFIG_XFS_FS`.

**XZ**
A compression format using LZMA2. Common for kernel source archives (`.tar.xz`). Tools: `xz`, `unxz`, `xzcat`.

---

## Y

**YAML (YAML Ain't Markup Language)**
A human-readable data serialization format. Used in Kubernetes configs, Ansible playbooks, and CI/CD pipelines.

**yum / dnf**
Package managers for RPM-based distributions. `dnf` is the modern replacement for `yum` on Fedora and RHEL 8+.

---

## Z

**Zero-Copy**
Techniques that avoid copying data between kernel and user space. Examples: `sendfile(2)`, `splice(2)`, `mmap(2)`.

**ZFS**
An advanced filesystem and volume manager combining filesystem, volume manager, and RAID. Features: snapshots, checksums, compression, deduplication.

**zombie process**
A process that has terminated but whose parent has not yet called `wait(2)` to read its exit status. Shown as `Z` in `ps`. Cleaned when parent exits or calls `wait`.

**zram**
A compressed RAM-based block device used as swap. Reduces disk I/O by compressing pages in memory. See [Kernel Config](kernel-config.md) `CONFIG_ZRAM`.

**zswap**
A compressed write-back cache for swap. Pages are compressed in memory before being written to disk. See [Kernel Config](kernel-config.md) `CONFIG_ZSWAP`.

---

## Cross-References

- [Man Pages](man-pages.md) — Where to find documentation for these terms
- [Kernel Config](kernel-config.md) — CONFIG_* options for kernel features mentioned above
- [Syscall Table](syscall-table.md) — System call interfaces for kernel features
- [Commands Reference](commands.md) — Command-line tools related to these concepts
- [Further Reading](further-reading.md) — Books, websites, and resources for deeper understanding
