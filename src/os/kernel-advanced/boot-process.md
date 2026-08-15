# Boot Process — From Power-On to PID 1

## Overview

The Linux boot process spans firmware → bootloader → kernel decompression → early boot → initcalls → PID 1. Understanding each stage is critical for debugging boot failures, reducing boot time (critical in cloud autoscaling), and answering kernel architecture questions. This chapter goes beyond [BIOS/UEFI](../boot/bios-uefi.md) and [bootloader](../boot/bootloader.md) to cover kernel-internal boot mechanics.

## The Full Boot Chain

```text
Power-on → UEFI firmware (SEC → PEI → DXE → BDS)
  → GRUB2 EFI binary (grubx64.efi) loaded from ESP
    → GRUB reads grub.cfg, loads vmlinuz + initramfs into memory
      → GRUB calls EFI Boot Services: ExitBootServices()
        → Kernel entry point: startup_64 (arch/x86/boot/compressed/head_64.S)
          → Kernel decompression (decompress_kernel)
            → Relocate kernel to final virtual address
              → early_idt_setup, early page tables (identity + kernel mapping)
                → start_kernel() — the C entry point
                  → console_init, lockdep_init, sched_init, mm_init, ...
                  → rest_init() → kernel_init() on PID 1 kernel thread
                    → kernel_init_freeable() → do_basic_setup()
                      → do_initcalls() — all __initcall levels
                        → PID 1 calls /sbin/init (or systemd)
```

## EFI / UEFI Handoff to the Kernel

UEFI firmware runs in 64-bit long mode with firmware-provided services. GRUB2 is an EFI application that uses `EFI_BOOT_SERVICES` to:

1. **Read the GPT partition table** to find the EFI System Partition (ESP).
2. **Load `vmlinuz` and `initramfs** into memory, placing them below the 4 GiB boundary (required for the decompressor's identity-mapped region).
3. **Collect the EFI memory map** (descriptors for RAM, MMIO, reserved regions).
4. **Install a custom GDT/IDT** and set up a minimal 64-bit environment.
5. **Call `ExitBootServices()`** — this terminates all firmware boot services, invalidates the memory map, and hands full control to the loaded image. After this call, GRUB cannot call any boot service.

GRUB passes a **boot parameters struct** (`struct boot_params`, defined in `include/uapi/linux/bootparam.h`) to the kernel at a fixed physical address (0x10000 or passed via register). This contains:

- `e820_table` — memory map entries
- `hdr.cmd_line_ptr` — pointer to the kernel command line
- `efi_info` — EFI system table address, firmware revision
- `screen_info` — framebuffer geometry (for early fbcon)
- `acpi_rsdp_addr` — RSDP for ACPI table discovery

> **Interview Angle**: "Why does the kernel need the EFI memory map?" Because UEFI may have allocated runtime services (SMM, boot services remnants) in physical memory that must not be overwritten. The kernel marks these regions as reserved in `e820`/`memblock`.

## Kernel Decompression

The kernel image (`vmlinuz`) is not raw ELF — it's a small stub (`arch/x86/boot/compressed/head_64.S`) followed by a compressed payload (LZ4, LZMA, XZ, ZSTD — selectable at build time via `CONFIG_KERNEL_XZ` etc.).

Decompression sequence (`arch/x86/boot/compressed/misc.c`):

```c
// Simplified from arch/x86/boot/compressed/head_64.S + misc.c
startup_64:
    // 1. Set up identity-mapped page tables (boot page tables)
    //    Maps first 4 GB 1:1 (phys = virt) for decompressor to work
    // 2. Enable PAE / long mode via CR4, EFER MSR
    // 3. Load kernel's GDT (boot_gdt)
    // 4. Call extract_kernel()

asmlinkage __visible void *extract_kernel(void *rmode, memptr heap,
                                          unsigned char *input_data,
                                          unsigned long input_len,
                                          unsigned char *output)
{
    // inflate() or corresponding decompressor
    // output goes to the final kernel virtual address (e.g., 0xffffffff81000000)
    return output + uncompressed_size;
}
```

After decompression, the stub **jumps to the extracted kernel's `startup_64`** (the "real" one in `arch/x86/kernel/head_64.S`), which:

1. Sets up **kernel page tables** (KPTI: two sets — user PGD and kernel PGD, `arch/x86/mm/kpti.c`).
2. Enables **SMEP/SMAP** via CR4.
3. Jumps to `x86_64_start_kernel()` → `start_kernel()`.

> **Interview Angle**: "Why does the kernel decompress itself instead of having the bootloader do it?" Self-decompression allows the kernel to control its own load address (KASLR offset), verify integrity (if signed), and work across bootloaders with no decompression support.

## Early Boot Memory Management

Before the page allocator is ready, the kernel uses **memblock** (`mm/memblock.c`):

```c
// memblock is a simple array-based allocator used during early boot
// Regions: memory (usable RAM) and reserved (firmware, initrd, kernel image)
struct memblock {
    phys_addr_t current_limit;  // upper bound for allocations
    struct memblock_type memory;   // usable regions
    struct memblock_type reserved; // reserved regions
};
```

`memblock_alloc()` does a first-fit over the memory regions, skipping reserved. This is used for:
- Page table pages
- Early boot data structures (per-CPU areas, SMP boot stacks)
- The initrd (copied from the boot parameters-provided address)

Transition: `mem_init()` → `page_alloc_init()` switches to the buddy allocator. After this, `memblock` is freed.

## Kernel Command Line

Parsed by `parse_early_param()` and `parse_args()` in `start_kernel()`. Notable parameters:

| Parameter | Effect | Source File |
|-----------|--------|-------------|
| `ro` | Mount root filesystem read-only | `init/do_mounts.c` |
| `root=/dev/nvme0n1p2` | Root device | `init/do_mounts.c` |
| `root=UUID=...` | Root by UUID | `init/do_mounts.c` |
| `rootfstype=ext4` | Hint for root FS type | `init/do_mounts.c` |
| `init=/sbin/init` | PID 1 binary | `init/main.c` |
| `console=ttyS0,115200` | Serial console | `kernel/printk/printk.c` |
| `quiet` / `loglevel=4` | Suppress boot messages | `kernel/printk/printk.c` |
| `crashkernel=256M` | Reserve memory for kdump | `kernel/kexec_core.c` |
| `mitigations=off` | Disable CPU mitigations | `kernel/cpu.c` |
| `nohz_full=1-3` | Tickless on CPUs 1-3 | `kernel/time/tick-sched.c` |
| `isolcpus=1,2` | Isolate CPUs from scheduler | `kernel/sched/core.c` |
| `hugepages=1024` | Pre-allocate huge pages | `mm/hugetlb.c` |
| `modules_disabled=1` | Disable module loading | `kernel/module.c` |

## The initcall Mechanism

The kernel uses a **level-based initialization system** — every subsystem registers itself via `__initcall` macros, and `do_initcalls()` calls them in order:

```c
// include/linux/init.h
#define pure_initcall(fn)       __define_initcall("0", fn, 0)
#define core_initcall(fn)       __define_initcall("1", fn, 1)
#define postcore_initcall(fn)   __define_initcall("2", fn, 2)
#define arch_initcall(fn)       __define_initcall("3", fn, 3)
#define subsys_initcall(fn)     __define_initcall("4", fn, 4)
#define fs_initcall(fn)         __define_initcall("5", fn, 5)
#define device_initcall(fn)     __define_initcall("6", fn, 6)
#define late_initcall(fn)       __define_initcall("7", fn, 7)
```

These place function pointers into ELF sections `.initcallN.init`, which the linker collects. `do_initcalls()` in `init/main.c` iterates:

```c
static void __init do_initcalls(void)
{
    for (int level = 0; level < 8; level++) {
        do_initcall_level(level);
        // Each level: iterate __initcallN_start to __initcallN_end
        // Call: fn()
    }
}
```

| Level | Purpose | Examples |
|-------|---------|----------|
| 0 (`pure`) | Essential, no dependencies | `printk` setup |
| 1 (`core`) | Core subsystems | interrupt descriptor table, timer framework |
| 2 (`postcore`) | Bus subsystems, IRQ chips | PCI, ACPI core, GIC (ARM) |
| 3 (`arch`) | Architecture-specific | APIC setup, CPU feature detection |
| 4 (`subsys`) | Kernel subsystems | networking, VFS, security (LSM) |
| 5 (`fs`) | File systems | ext4, xfs, btrfs registration |
| 6 (`device`) | Drivers | NIC, disk, GPU driver `module_init` |
| 7 (`late`) | Final setup | `kexec`, `sysctl` init, debugging interfaces |

> **Interview Angle**: "What order do drivers initialize?" Built-in drivers register at level 6 (`device_initcall`). Loadable modules run their `module_init` when loaded via `insmod`/`modprobe`, which is equivalent to a level-6 initcall. This is why networking is up before disks (level 4 vs 6), and why `mount` works for root filesystem at level 5.

## Module Loading and Symbol Resolution

### ELF Section Layout of a `.ko`

```text
.ko (ELF relocatable object):
  .text        — code
  .rodata      — constants
  .data        — initialized data
  .bss         — zero-init data
  .gnu.linkonce.this_module — struct module
  .modinfo     — author, license, version, depends, vermagic
  __ksymtab    — exported kernel symbols this module provides
  __ksymtab_gpl — GPL-only exports
  __param      — module parameters
  .init.text   — module_init function (discarded after init)
```

### Loading Sequence (`kernel/module/main.c`)

```c
// Simplified load_module() flow
SYSCALL_DEFINE3(finit_module, int, fd, const char __user *, uargs, int, flags)
{
    // 1. Read ELF from fd into kernel buffer
    // 2. Layout: lay_out_sections() — calculate sizes, alignments
    // 3. Allocate vmalloc'd memory for each section
    // 4. Copy ELF sections into allocated memory
    // 5. Relocate: apply ELF relocations using kernel symbol table
    //    resolve_symbol() — search kernel's exported symbols (ksymtab)
    // 6. Sanity checks: vermagic match, version CRC check
    // 7. module_arch_cleanup(), add module to list
    // 8. Run module->init() (the module_init function)
    // 9. Enable module (mark MOD_STATE_LIVE)
}
```

### Symbol Resolution

```c
// kernel/kallsyms.c + kernel/module/kallsyms.c
// Each module's symbols are added to a global tree
struct kernel_symbol {
    int value_offset;  // offset within module
    int name_offset;
    int namespace_offset;
};

// find_symbol() searches:
// 1. Built-in kernel's __ksymtab (compiled-in exports)
// 2. Loaded modules' __ksymtab (in load order)
// Returns symbol value (address) + owner module (for refcounting)
```

When module A depends on module B: `modprobe A` triggers automatic loading of B via `request_module("B")` if symbol resolution fails, using the `modules.dep` file generated by `depmod`.

### Module Reference Counting

```c
// include/linux/module.h
static inline int try_module_get(struct module *module)
{
    return atomic_inc_not_zero(&module->refcnt);
}
static inline void module_put(struct module *module)
{
    atomic_dec(&module->refcnt);
}
```

`rmmod` checks `module->refcnt == 0` before allowing removal. If a file is open, a network device is UP, or another module holds a reference, removal fails with EBUSY.

## initramfs — The Early Root Filesystem

The initramfs (initial RAM filesystem) is a **cpio archive** embedded in the kernel image (or loaded separately by the bootloader). It's extracted into `rootfs` (a minimal tmpfs) by `init/initramfs.c:populate_rootfs()`.

```text
// initramfs unpack flow:
start_kernel() → rest_init() → kernel_init()
  → kernel_init_freeable() → populate_rootfs()
    → unpack_to_rootfs() — decompresses cpio/gzip/xz
      → Files appear under /
  → do_basic_setup() → do_initcalls()
    → Built-in initramfs contents available (e.g., /init)
  → kernel_init() tries to run /init
```

Why initramfs exists:
1. **Load modules** needed to access the real root (e.g., NVMe driver, LUKS crypto, network for NFS root).
2. **Early userspace setup** — `udev` to create device nodes, `mdadm` to assemble RAID, `cryptsetup` to open LUKS.
3. **Boot-time decision making** — Plymouth splash, boot-time fsck, dropbear for remote unlock.

Modern systems use **dracut** or **mkinitcpio** to generate the initramfs. The initramfs `/init` script ultimately executes `switch_root /sysroot /sbin/init` to pivot to the real root.

## From start_kernel() to PID 1

```c
// init/main.c — start_kernel() (runs on the boot CPU, interruptible)
start_kernel(void)
{
    set_task_stack_end_magic(&init_task);  // stack canary
    cgroup_init_early();
    local_irq_disable();
    boot_cpu_init();             // mark boot CPU online
    page_address_init();
    pr_notice("%s", linux_banner);
    setup_arch(&command_line);   // arch-specific: memblock, page tables
    setup_per_cpu_areas();       // per-CPU data allocation
    smp_prepare_boot_cpu();
    boot_cpu_hotplug_init();
    build_all_zonelists(NULL);   // NUMA zones
    page_alloc_init();           // buddy allocator ready
    // ... 50+ more init calls ...
    rest_init();                 // spawns kernel threads
}

// rest_init() — spawns PID 1 (kernel_init) and PID 2 (kthreadd)
static noinline void __init rest_init(void)
{
    pid = kernel_thread(kernel_init, NULL, CLONE_FS);  // PID 1
    // ...
    pid = kernel_thread(kthreadd, NULL, CLONE_FS);     // PID 2
    // ...
    cpu_startup_entry(CPUHP_ONLINE);  // boot CPU becomes idle
}
```

`kernel_init()` (the PID 1 kernel thread) runs all initcalls, then attempts to open the real root device and execute `/sbin/init`. If systemd is PID 1, it takes over all further service management (see [Namespaces & cgroups](./namespaces-cgroups.md)).

## Interview Questions

### Q: What happens between UEFI ExitBootServices and start_kernel()?

The decompressor (`arch/x86/boot/compressed/head_64.S`) runs. It sets up identity-mapped boot page tables (first 4 GiB), enables long mode (if not already), decompresses the kernel image into its final virtual address, then jumps to the extracted kernel's entry point. The extracted kernel then sets up KPTI page tables, initializes the GDT/IDT, and enters `start_kernel()`.

### Q: Why are there 8 initcall levels?

Dependency ordering. The kernel cannot initialize the PCI bus (level 2) before the interrupt framework (level 1). Drivers (level 6) depend on subsystems (level 4) and file systems (level 5). This avoids fragile manual ordering — each component declares its level, and the linker collects them.

### Q: How does module symbol resolution work across versions?

The kernel uses `CONFIG_MODVERSIONS` to generate CRC checksums of exported symbol signatures. When a module loads, the kernel checks that the module's expected CRC matches the kernel's actual CRC for each symbol. A mismatch (e.g., struct field reordered) causes `Invalid module format`. This is why out-of-tree modules break across kernel upgrades.

### Q: How is the initramfs different from an initrd?

**initramfs** is a cpio archive unpacked into rootfs (tmpfs) — it's part of the kernel image and doesn't need a block device. **initrd** (legacy) is a block-device image (ext2) loaded by the bootloader. initramfs is simpler, smaller, and the only mechanism used in modern kernels. The `initrd` path still exists for compatibility but is deprecated.

## References

- `arch/x86/boot/compressed/head_64.S` — decompressor entry, boot page tables
- `arch/x86/boot/compressed/misc.c` — `extract_kernel()`
- `init/main.c` — `start_kernel()`, `rest_init()`, `do_initcalls()`, `kernel_init()`
- `include/linux/init.h` — `__initcall` macro definitions
- `kernel/module/main.c` — `load_module()`, `finit_module()` syscall
- `init/initramfs.c` — `populate_rootfs()`
- `Documentation/driver-model/driver.txt` — driver initcall ordering
- [bootlin.com — Linux Kernel Booting Process](https://bootlin.com/docx/boot-process/)

## Related Topics

- [BIOS/UEFI](../boot/bios-uefi.md) — firmware details, secure boot
- [Bootloader](../boot/bootloader.md) — GRUB2, kernel loading
- [Init Systems](../boot/init-systems.md) — systemd, runlevels, service management
- [Kernel Modules](../kernel/modules.md) — module basics, modprobe, depmod
- [Namespaces & cgroups](./namespaces-cgroups.md) — systemd's cgroup management
