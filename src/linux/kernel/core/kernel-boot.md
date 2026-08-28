# Linux Kernel Boot — From Power-On to PID 1

This page traces the boot of a Linux system at the level of the source code: what runs when, who hands off to whom, and which initcall level is responsible for what subsystem. It is the "what actually happens between reset and `login:`" companion to the more user-visible [Boot Process](../boot-process.md) page.

The chain has five distinct phases, each with its own primitive and conventions:

```
+-----------+    +-----------+    +------------+    +-------------+    +-----------+
| firmware  | -> | bootloader| -> | decompress | -> | start_kernel| -> | userspace |
| BIOS/UEFI |    | GRUB/sd-boot| | bzImage→vmlinux| | initcall levels| | initramfs  |
+-----------+    +-----------+    +------------+    +-------------+    +-----------+
```

## 1. Firmware: BIOS or UEFI

### BIOS (Legacy)
On power-on, the CPU fetches its first instruction from `0xFFFFFFF0` (16-bit real mode, mapped to the top of flash via the chipset). The BIOS performs POST, scans for bootable devices in the configured order, reads the 512-byte **MBR** (Master Boot Record) — sector 0 of the boot disk — into RAM at `0x7C00`, then jumps to it. Only 440 bytes of the MBR are code; the rest is the partition table and the `0x55 0xAA` magic.

### UEFI
UEFI firmware runs in flat 64-bit mode, reads GPT partitions directly, and executes a PE32+ binary stored as a file on the EFI System Partition (ESP, partition type `C12A7328-F81F-11D2-BA4B-00A0C93EC93B`). Boot loaders live at `\EFI\<vendor>\<bootloader>.efi`. UEFI exposes runtime services (`BootServices`, `RuntimeServices`) callable from the kernel during early boot, before the kernel calls `ExitBootServices()`.

Either path hands control to the **bootloader**.

## 2. Bootloader: GRUB2 or systemd-boot

### GRUB2
GRUB2 itself has multiple stages:

1. `boot.img` (440 B, written into the MBR) loads `diskboot.img`.
2. `diskboot.img` reads `core.img` (~30 KiB) which contains enough of the GRUB core to read filesystems.
3. `core.img` loads `grub.cfg`, displays the menu, and either loads a kernel directly or chains another loader.

For Linux, GRUB loads three things into RAM: the **bzImage** (the compressed kernel image at `arch/x86/boot/bzImage`), an optional **initramfs**, and a **command line** string. It then jumps to the 16-bit setup entry point at offset `0x200` of the bzImage.

### systemd-boot
systemd-boot (formerly "gummiboot") is a much simpler UEFI-only boot stub. It lives as `systemd-bootx64.efi` in the ESP and reads entries from loader entries on the ESP:

```
# /boot/loader/entries/linux.conf  (Type 1 loader spec entry)
title   Linux
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=UUID=… rw quiet splash
```

The [Boot Loader Specification](https://systemd.io/BOOT_LOADER_SPECIFICATION/) is the canonical reference. systemd-boot passes the kernel a pointer to the EFI memory map, the cmdline, and (on `initrd=`) the initramfs address.

## 3. Kernel decompression and the early entry path

The bzImage is `setup.bin` (16-bit real-mode setup code) concatenated with `vmlinux.bin` (a self-decompressing compressed kernel). On x86_64 the entry sequence is:

1. **16-bit real mode**: `startup` in `arch/x86/boot/header.S` runs `main()` in `arch/x86/boot/main.c`. It queries BIOS interrupts (int 0x10/0x15) for video mode, memory map, APM, etc., and copies the boot parameters into the `boot_params` structure (the famous `zeropage`). It then transitions to protected mode and to long mode.
2. **64-bit long mode**: `startup_64` in `arch/x86/boot/compressed/head_64.S` sets up an initial page table identity-mapping the first ~4 GiB, and jumps to the decompressor in `arch/x86/boot/compressed/misc.c`.
3. **Decompression**: depending on `CONFIG_KERNEL_*`, `__decompress()` calls one of `decompress\_gzip`, `decompress\_bzip2`, `decompress\_lz4`, `decompress\_xz`, or `decompress\_zstd`. The decompressed `vmlinux` is placed at the address reserved by the bootloader. A final jump enters the **real kernel entry point** at `startup_64` in `arch/x86/kernel/head_64.S`.

Other architectures follow an analogous path. ARM64 starts in `head.S` at EL2 (or EL1), sets up the MMU off the device tree `chosen` node, and jumps to `__primary_entry`. RISC-V starts at `_start` in `head.S`. On all of them, the goal is to land in `start_kernel()` in `init/main.c` with the MMU on and a sane stack.

## 4. The kernel command line

The kernel cmdline is passed in by the bootloader and stored in `boot_command_line` (and `saved_command_line` once frozen). At runtime it is exposed read-only via `/proc/cmdline`:

```bash
$ cat /proc/cmdline
BOOT_IMAGE=(hd0,gpt1)/vmlinuz-6.8 root=UUID=4f… rw quiet splash systemd.unit=emergency.target
```

Parameters are interpreted by:
- `core/param.c` (`__setup` macro) — early setup calls.
- `init/do_mounts.c` — root device handling.
- `kernel/printk.c`, `kernel/sched/*`, `mm/*`, etc. — module-specific `module_param`s.
- systemd via `systemd.unit=`, `systemd.mask=`, `systemd.debug-shell`, `rw`/`ro`, `root=`, `init=`, etc. (see [systemd man page](https://www.freedesktop.org/software/systemd/man/systemd.html)).

The cmdline is parsed in two passes: **early** (before `start_kernel` is fully entered) and **late** (after `parse_args` near the end of `start_kernel`). Early parameters go through `setup_arch()` and friends; late ones through `__setup` and `module_param`.

Common kernel-side parameters (see [`man bootparam(7)`](https://man7.org/linux/man-pages/man7/bootparam.7.html)):

| Parameter | Effect |
|-----------|--------|
| `root=/dev/sda1` or `root=UUID=…` | Root device for the real init |
| `ro` / `rw` | Mount root read-only / read-write |
| `init=/path/to/init` | Override `/sbin/init` (default fallback chain is `/sbin/init`, `/etc/init`, `/bin/init`, `/bin/sh`) |
| `rdinit=/sbin/init` | Pass init path *inside* the initramfs |
| `console=ttyS0,115200` | Add a console device |
| `loglevel=8` | Initial printk level |
| `quiet` / `debug` | Lower/raise printk verbosity |
| `single` / `1` / `S` | Boot to single-user mode (handled by init, not the kernel) |
| `nomodules` | Disable loadable module support |
| `crashkernel=128M@64M` | Reserve memory for kdump capture kernel |
| `loop.max_loop=64` | Set a module parameter from the cmdline |
| `systemd.mask=foo.service` | Tell systemd to mask a unit at boot |
| `systemd.unit=rescue.target` | Override default boot target |

## 5. start_kernel(): the early C entry point

`start_kernel()` in `init/main.c` is the first C code to run on the boot CPU. It is a long sequence of `init_*` calls that bring up each subsystem in dependency order. The exact sequence changes per release; the shape below matches recent 6.x kernels:

```c
asmlinkage __visible void __init start_kernel(void)
{
        set_task_stack_end_magic(&init_task);
        smp_setup_processor_id();
        debug_objects_early_init();
        init_vmlinux_build();
        cgroup_init_rootfs();
        local_irq_disable();
        boot_init_stack_canary();
        boot_cpu_init();
        page_address_init();
        pr_notice("%s", linux_banner);
        early_security_init();
        setup_arch(&command_line);          /* arch/x86/kernel/setup.c */
        mm_core_init();
        ...
        setup_per_cpu_areas();
        boot_cpu_hotplug_init();
        build_all_zonelists(NULL);
        cpuhp_threads_init();
        /* interrupts still disabled here */
        ...
        trap_init();
        rcu_init();
        /* RCU is now "watching" — preemption is safe on this CPU */
        ...
        early_irq_init();
        init_IRQ();
        tick_clock_init();
        init_timers();
        hrtimers_init();
        softirq_init();
        timekeeping_init();
        time_init();
        ...
        sched_clock_init();
        ...
        local_irq_enable();                  /* first time interrupts go on */
        ...
        console_init();
        ...
        rest_init();                         /* spawns kernel_init thread */
}
```

The order is fixed by **dependency**: arch setup → memory → RCU → scheduler → timers → IRQ → console → initcalls → userspace. Enablement of preemption, IRQs, and RCU is gated by specific milestones (`rcu_scheduler_active`, `system_state == SYSTEM_RUNNING`, etc.).

## 6. initcall levels

After `start_kernel` completes its per-subsystem initialisation, the kernel enters the **initcall** phase. Initcalls are functions registered with `__initcall` macros; they are emitted into a special linker section (`__initcall_start` … `__initcall_end`) sorted into "levels" by the linker script. The kernel walks them in order via `do_initcall_level()` in `init/main.c`.

The levels, in execution order:

| Level | Macro | Typical use |
|-------|-------|-------------|
| 0 (pure) | `pure_initcall(fn)` | Prerequisites with no dependencies, e.g. calibrating constants |
| 1 (core) | `core_initcall(fn)` | Architecture-independent core subsys init (e.g. IRQ subsystems) |
| 1s | `core_initcall_sync(fn)` | Sync point after core |
| 2 (postcore) | `postcore_initcall(fn)` | Subsystems that must run before subsys_initcall (e.g. some bus types) |
| 2s | `postcore_initcall_sync(fn)` | Sync point after postcore |
| 3 (arch) | `arch_initcall(fn)` | Architecture-specific setup that depends on core |
| 3s | `arch_initcall_sync(fn)` | Sync point after arch |
| 4 (subsys) | `subsys_initcall(fn)` | Bus drivers, subsystem registration: PCI, USB, I2C, netdev |
| 4s | `subsys_initcall_sync(fn)` | Sync point after subsys |
| 5 (fs) | `fs_initcall(fn)` | Filesystem initialisation (ext4, nfsd, btrfs) |
| 5s | `fs_initcall_sync(fn)` | Sync point after fs |
| 6 (device) | `device_initcall(fn)` | The bulk of driver probe code |
| 6s | `device_initcall_sync(fn)` | Sync point after device |
| 7 (late) | `late_initcall(fn)` | Things that need everything else up: e.g. ACPI final init, trace events, kprobes |
| 7s | `late_initcall_sync(fn)` | Last sync point |
| — | `module_init(fn)` for built-in code | Equivalent to `device_initcall` |

The `_sync` levels exist to introduce a **barrier** between levels; they are not called by any code, they just enforce ordering so that a `subsys_initcall` cannot race ahead of a straggling `core_initcall`.

The `do_initcalls()` function iterates the levels, calling each registered function and checking its return value. A non-zero return is logged via `pr_warn("initcall %pS returned %d after %lld usecs\n", …)`; the kernel keeps booting unless `initcall_debug` is set.

Tracing initcalls:

```bash
$ dmesg | grep initcall
[    0.013456] initcall pci_realloc_setup+0x0/0x30 returned 0 after 12 usecs
[    0.013890] initcall acpi_init+0x0/0x200 returned 0 after 41 usecs
[    0.014321] initcall tty_init+0x0/0x100 returned 0 after 23 usecs
```

Add `initcall_debug` to the kernel cmdline to log every initcall's entry/exit and duration. Combined with `printk.time=1` this is the standard tool for [boot-time optimisation](https://elinux.org/Boot_Time).

## 7. rest_init, kernel_init, and the init hand-off

After all initcalls complete, `start_kernel()` calls `rest_init()` which spawns a kernel thread running `kernel_init()`:

```c
static noinline void __ref rest_init(void)
{
        struct task_struct *tsk;
        ...
        rcu_scheduler_starting();
        ...
        pid = user_mode_thread(kernel_init, NULL, CLONE_FS);
        ...
        cpu_startup_entry(CPUHP_AP_ONLINE_IDLE);
}
```

`kernel_init()` (in `init/main.c`) is the function that ultimately **executes the userspace init**. It does:

1. `wait_for_completion(&kthreadd_done)` — wait for the kernel-threads daemon to be ready.
2. `do_basic_setup()` — run any remaining late initcalls, initialise workqueues, etc.
3. `console_on_rootfs()` — open `/dev/console` as stdin/stdout/stderr.
4. `try_to_run_init_process()` — try in order: `ramdisk_execute_command` (set by `rdinit=`), `execute_command` (set by `init=`), and finally the default search path:
   ```
   /sbin/init, /etc/init, /bin/init, /bin/sh
   ```
5. On a modern system `/sbin/init` is a symlink to `/lib/systemd/systemd`, which becomes **PID 1**.

If all of these fail, the kernel panics with the famous "No init found. Try passing init= option to kernel." message.

## 8. initramfs and switch_root

On almost every modern distro, the init that the kernel executes is *inside an initramfs*. The kernel unpacks the initramfs (a gzip-compressed cpio archive) into a tmpfs at `/` early in `start_kernel` via `populate_rootfs()` in `init/initramfs.c`:

```c
static int __init populate_rootfs(void)
{
        /* If the bootloader placed a ramdisk image, unpack it.
           Otherwise use the build-time __initramfs_start. */
        ...
        err = unpack_to_rootfs((char *)initrd_start, initrd_end - initrd_start);
        ...
}
```

The first userspace process is then `rdinit` (often `/init` inside the initramfs). This `init` is a shell, busybox, or — on systemd-based distros — a separate `systemd` instance running in `--initrd` mode that mounts the real root and does `switch_root`.

### switch_root from the initramfs
The canonical `switch_root` syscall-equivalent is `pivot_root(2)` plus `chroot`. The initramfs `init`:

1. Mounts block devices (resolves `root=UUID=…` via `findfs`/`blkid`).
2. Mounts the real root filesystem at `/sysroot` (read-only first, see `init/do_mounts.c`).
3. Calls `mount --move /sysroot /` (or `switch_root /sysroot /sbin/init` from nash/dracut).
4. Execs the real init (e.g. `/lib/systemd/systemd`).

dracut's `init` script ends with:

```sh
# /usr/lib/dracut/modules.d/99base/init.sh
if [ -e /sysroot/etc/fstab ] || [ -e /sysroot/etc/initrd-release ]; then
    umount /sysroot
    mount "$NEWROOT" /sysroot
fi
exec switch_root "$NEWROOT" "$INIT" "$@"
```

`switch_root` here is a small busybox-style utility that:
1. Recursively deletes everything in the tmpfs root.
2. `mount --move /sysroot /` so the real root becomes `/`.
3. `chroot .` and `exec /sbin/init`.

## 9. PID 1 takes over

Once `/sbin/init` (systemd) is exec'd as PID 1, the kernel's involvement is essentially over. The kernel still owns:

- **kthreadd** (PID 2): the kernel-threads daemon, spawning other kernel threads (kworker, ksoftirqd, migration, etc.).
- **kworker/N/h-D** thread pools.
- **RCU** threads (`rcu_sched`, `rcu_bh`).
- **per-CPU idle tasks** (PID 0 on each CPU).

systemd as PID 1 takes over boot orchestration: it parses `/proc/cmdline`, picks up `systemd.unit=` overrides, activates `default.target`, and runs the [systemd transaction](../../admin/systemd-internals.md). From here on, "the boot" is a userspace story; the kernel is just a service provider.

## References

- The Linux Kernel Archives documentation, https://www.kernel.org/doc/html/latest/
- Documentation/x86/boot in the kernel tree, https://www.kernel.org/doc/html/latest/x86/boot.html
- Documentation/admin-guide/kernel-parameters.txt, https://www.kernel.org/doc/html/latest/admin-guide/kernel-parameters.html
- man bootparam(7), https://man7.org/linux/man-pages/man7/bootparam.7.html
- The Boot Loader Specification (systemd.io), https://systemd.io/BOOT_LOADER_SPECIFICATION/
- LWN: "Booting the Linux kernel" — Jonathan Corbet, https://lwn.net/Articles/299418/
- LWN: "The path to init" — Jake Edge, https://lwn.net/Articles/541317/
- LWN: "A look at initramfs" — Jonathan Corbet, https://lwn.net/Articles/258378/
- elinux.org Boot Time wiki, https://elinux.org/Boot_Time
- init/main.c in the source tree (canonical reference for the actual sequence), https://elixir.bootlin.com/linux/latest/source/init/main.c
- Linux From Scratch book, "Booting" chapter, https://www.linuxfromscratch.org/lfs/view/stable/chapter10/introduction.html
