# Embedded Linux: Build Systems, Kernel, Rootfs, Device Tree, Boot

Embedded Linux is what you get when a Linux kernel, a small userland, a bootloader, and a cross-toolchain are bound together for a specific piece of hardware: an industrial gateway, an automotive head unit, a robotics controller, a smart display, a NAS box. Unlike an RTOS-on-MCU project (which might fit in 64 KB of Flash), an embedded Linux product needs at least ~8 MB of Flash and ~16 MB of RAM to be comfortable, and at that floor you are already fighting for every kilobyte. This page walks through the engineering surface: build systems, kernel configuration, the rootfs, the device tree, cross-compilation, the boot flow, and a comparison to the RTOS alternative.

For the related sibling topics see [Firmware Boot & Watchdogs](./firmware.md) (MCU boot, dual-bank OTA, watchdogs), [RTOS Internals](./rtos-internals.md) (kernel scheduling, IPC), and [Real-Time Systems](./real-time-systems.md) (PREEMPT_RT, SCHED_DEADLINE).

> **Interview one-liner:** "Embedded Linux boots ROM → SPL → U-Boot → zImage + DTB → init; the image is built by Buildroot (single Makefile, one defconfig) or Yocto (layered recipes, bitbake, Kconfig-style); the kernel is stripped with `CONFIG_EMBEDDED` + `CONFIG_TINY` and optionally patched with PREEMPT_RT for ~50 µs worst-case latency; musl libc + BusyBox gives a ~4 MB rootfs; the device tree describes the board so the same kernel runs on many variants; the toolchain is a `arm-poky-linux-gnueabi-` cross-compile tuple plus a sysroot."

## When Embedded Linux (vs RTOS)

A common first question: do you even need Linux on this device? The decision boundary today sits at roughly **8 MB RAM / 8 MB Flash**:

| Footprint class | Examples | Typical OS |
|---|---|---|
| < 64 KB Flash, < 16 KB RAM | Sensor node, smart bulb, USB-C controller | Bare-metal or RTOS (FreeRTOS, Zephyr) |
| 64 KB – 1 MB Flash | Wearable, BLE mesh node, motor controller | RTOS (FreeRTOS, Zephyr, ThreadX) |
| 4 – 16 MB Flash, 16 – 64 MB RAM | Industrial gateway, smart meter, edge sensor | RTOS with networking (Zephyr, ThreadX, FreeRTOS-Plus-TCP) or stripped Linux |
| 16 MB – 128 MB Flash, 64 MB+ RAM | Robotics controller, smart display, NAS, ADAS head unit | Embedded Linux |
| 128 MB+ | Anything with a UI, video, ML | Embedded Linux |

Linux wins when you need **POSIX, a network stack, a real filesystem, drivers for commodity peripherals, security updates, and a development model familiar to backend engineers**. It loses when you need **sub-µs response latency, formal WCET analysis, single-digit-millisecond cold-boot, or sub-1 mA deep sleep** — those are RTOS-on-MCU territory. Many modern SoCs (i.MX8, Renesas RZ, Xilinx Zynq) ship with **both**: an A-class core running Linux for HMI/networking and an M-class core running FreeRTOS for the real-time control loop, communicating via RPMsg shared memory.

## Boot Process: ROM → SPL → U-Boot → Kernel → init

The boot flow on a typical ARM embedded Linux board has five stages:

```
  +----------------+   +-----+   +--------+   +---------+   +------+
  | ROM bootloader |-->| SPL |-->| U-Boot |-->|  Linux  |-->| init |
  | (in-mask ROM)  |   | TPL |   | proper |   | kernel  |   | (sd) |
  +----------------+   +-----+   +--------+   +---------+   +------+
       ~0 KB             32-256KB   256KB-1MB    2-8MB       rootfs
       runs from ROM     SRAM init  DDR init     DDR         DDR
```

1. **ROM bootloader** (also called BootROM, BROM). Burned into the chip at the factory; cannot be changed. It looks for the next stage at a fixed offset in the configured boot media (eMMC, SD, QSPI, NAND, UART, USB). On i.MX this is the fuses + IVT header; on TI AM-series it's the MLO/SPL signature; on STM32MP1 it's the FSBL.
2. **SPL (Secondary Program Loader)** — a tiny (32–256 KB) U-Boot or vendor equivalent that initializes DDR RAM and loads the next stage. SPL lives in on-chip SRAM because DDR isn't up yet.
3. **U-Boot proper** — the Das U-Boot bootloader. Initializes the board, parses the `bootcmd` and `bootargs` environment variables, loads the kernel + DTB into RAM, and jumps to it. U-Boot also drives the boot menu, A/B partition selection, and recovery.
4. **Linux kernel** — decompresses (if zImage/Image.gz), sets up the MMU, mounts the root filesystem, and calls `/sbin/init`.
5. **init** — BusyBox init, SysVinit, systemd, OpenRC, or s6. Mounts the rest of the filesystem, starts services, brings up networking, and execs the application.

A typical U-Boot environment on a BeagleBone Black:

```
=> printenv bootcmd
bootcmd=run findfdt; run mmcboot;
=> printenv mmcboot
mmcboot=echo Booting from mmc...; \
    run loadimage; run loadfdt; run mmcargs; \
    bootz ${loadaddr} - ${fdtaddr}
=> printenv bootargs
bootargs=console=ttyO0,115200 root=/dev/mmcblk0p2 rw rootfstype=ext4 rootwait
```

U-Boot reads `bootcmd` on timeout, which loads the kernel from `mmcblk0p1` to `loadaddr` and the DTB to `fdtaddr`, then `bootz` (or `booti` for ARM64) jumps to the kernel with `r2 = fdtaddr` (the DTB pointer) and `r1 = machine type` (legacy 32-bit only — modern DT-only systems ignore `r1`).

## Build Systems: Buildroot vs Yocto/OpenEmbedded

Two ecosystems dominate embedded Linux image production. **Buildroot** is a single-tree Makefile-based build system that produces a complete, monolithic image (kernel + rootfs + bootloader) from a single `defconfig`. **Yocto/OpenEmbedded** is a layered recipe engine that produces a distribution plus an SDK plus per-recipe packages with package management.

### Buildroot

Buildroot is for "I want one working image and I want it now." It is ~50 KLOC of Makefile + Kconfig. You run `make menuconfig`, pick a defconfig, run `make`, and after 20 minutes you have a kernel + DTB + rootfs tarball + bootloader binaries:

```
$ make menuconfig
   Target architecture (ARM little-endian) --->
   Target architecture variant (cortex-A9) --->
   Toolchain: External ARM A-profile 64-bit --->
   System configuration: hostname = mybox
   Target packages: Networking -> dropbear, wpa_supplicant
   Filesystem images: ext4, squashfs
   Bootloaders: U-Boot 2024.01
$ make -j$(nproc)
$ ls output/images/
   zImage  mybox.dtb  rootfs.ext4  u-boot.bin  sdcard.img
```

A Buildroot `defconfig` is short and self-contained:

```bash
# configs/mybox_defconfig
BR2_arm=y
BR2_cortex_a9=y
BR2_TOOLCHAIN_EXTERNAL=y
BR2_TOOLCHAIN_EXTERNAL_LINARO_ARM=y
BR2_LINUX_KERNEL=y
BR2_LINUX_KERNEL_USE_CUSTOM_CONFIG=y
BR2_LINUX_KERNEL_CUSTOM_CONFIG_FILE="board/mybox/linux.config"
BR2_LINUX_KERNEL_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INT_DTS_SUPPORT=y
BR2_LINUX_KERNEL_INT_DTS_NAME="mybox"
BR2_PACKAGE_BUSYBOX=y
BR2_PACKAGE_DROPBEAR=y
BR2_PACKAGE_WPA_SUPPLICANT=y
BR2_TARGET_UBOOT=y
BR2_TARGET_UBOOT_BUILD_SYSTEM_KCONFIG=y
BR2_TARGET_UBOOT_BOARDNAME="mybox"
BR2_TARGET_ROOTFS_EXT2=y
BR2_TARGET_ROOTFS_EXT2_4=y
```

Buildroot is right when:

- The product is one image, no per-variant packages, no OTA package feeds.
- The team is small and wants reproducible builds with minimal learning curve.
- The image can be rebuilt from scratch in under an hour.

### Yocto / OpenEmbedded

Yocto is for "I want a maintainable distro across many products, with a packaged SDK, package feeds, and reproducible builds across five years." It is layered: a **BSP layer** (silicon vendor), a **distro layer** (your company), a **application layer** (your product). Recipes (`.bb`) and append files (`.bbappend`) compose into images via `bitbake`.

A Yocto project lays out like:

```
meta-mybox/
├── conf/layer.layer
├── recipes-bsp/    u-boot, atf, kernel
├── recipes-core/   init scripts, base files
├── recipes-core/images/mybox-image.bb
├── recipes-connectivity/  wpa-supplicant config
└── recipes-kernel/linux/linux-mybox_5.15.bb
```

A `local.conf` selects the machine and distro:

```bitbake
MACHINE = "mybox"
DISTRO = "poky"
PACKAGE_CLASSES = "package_rpm"
INHERIT += "rm_work"               # drop build artifacts to save disk
IMAGE_INSTALL:append = " openssh dropbear wpa-supplicant"
IMAGE_FSTYPES = "ext4 wic.bz2"
PREFERRED_VERSION_linux-mybox = "5.15%"
DISTRO_FEATURES:remove = "x11 wayland opengl pulseaudio"   # headless
```

A custom image recipe:

```bitbake
SUMMARY = "Mybox production image"
LICENSE = "MIT"
inherit core-image
IMAGE_INSTALL += "packagegroup-core-boot \
                  packagegroup-core-ssh-dropbear \
                  wpa-supplicant \
                  mybox-application"
IMAGE_ROOTFS_SIZE = "262144"   # 256 MB
```

Build with `bitbake mybox-image` and get `tmp/deploy/images/mybox/mybox-image-mybox.ext4`, a U-Boot binary, the kernel + DTB, and an SDK installer (`mybox-glibc-x86_64-meta-toolchain-armv7vet2hf-neon-toolchain-3.1.sh`).

### Comparison

| Property | Buildroot | Yocto |
|---|---|---|
| Lines of code | ~50 KLOC | ~300 KLOC core + layers |
| Build time (first) | 20–60 min | 2–6 hr |
| Build time (incremental) | 1–5 min | 5–20 min (per-recipe) |
| Package management on target | None (rebuild to update) | Full RPM/DEB/IPK feeds, `dnf` on target |
| SDK generation | `make sdk` | `bitbake meta-toolchain` or `populate_sdk` |
| Reproducibility | Per-build cache, deterministic | BitBake hash equivalence + sstate cache |
| BSP support | Per-board `board/` files | Layers per SoC vendor (meta-ti, meta-freescale, meta-arm) |
| Learning curve | Days | Weeks |
| Multi-product | One defconfig per product | Shared distro + per-machine configs |

The practical rule: pick **Buildroot** if you ship one image and want to ship it next month; pick **Yocto** if you ship a family of products, have a dedicated build/release team, and need package feeds for field updates.

## Kernel Configuration for Small Footprint

Stock Linux is configured for servers. For a 16 MB Flash product you must strip the kernel. The most useful options:

```
CONFIG_EMBEDDED=y              # surfaces the "expert" options below
CONFIG_EXPERT=y
CONFIG_MODULES=n               # if you don't load modules at runtime
CONFIG_PRINTK_TIME=n
CONFIG_BUG=n                   # removes BUG_ON warnings (saves ~30 KB)
CONFIG_DEBUG_INFO=n            # no debug symbols in the kernel binary
CONFIG_DEBUG_BUGVERBOSE=n
CONFIG_SYSFS_DEPRECATED=n
CONFIG_UID16=n                 # 32-bit uids only
CONFIG_FHANDLE=n               # no filehandle syscalls
CONFIG_FTRACE=n
CONFIG_KALLSYMS=n              # removes symbol table (~200 KB)
CONFIG_BINFMT_MISC=n           # no Java/Python binfmt
CONFIG_FW_LOADER=y             # keep, needed for some drivers

# Allocator: pick one
CONFIG_SLAB=y                  # default, good general purpose
CONFIG_SLUB=y                  # used by most distros, more debug-friendly
CONFIG_SLOB=y                  # tiny, ~2 KB min, use for < 16 MB systems

# Compression
CONFIG_KERNEL_LZMA=y          # or XZ for tighter compression
CONFIG_INITRAMFS_COMPRESSION_XZ=y
```

For real-time: the **PREEMPT_RT** patch (merged into mainline in 6.12) replaces spinlocks with RT-mutexes, makes ISRs threaded, and turns most kernel code paths preemptible. Enable with `CONFIG_PREEMPT_RT=y` (after applying the patch on older kernels). Verify:

```bash
$ uname -v
#1 SMP PREEMPT_RT Debian 6.1.69-1 (2024-01-05)
```

Measure worst-case scheduling latency with `cyclictest`:

```bash
$ sudo cyclictest -t1 -p80 -i1000 -l100000 --mlockall
# output includes max latency in microseconds; on a stock Cortex-A9
# you'll see 50-200 µs; without RT, 500 µs to several ms
```

The **Linux Tiny** tree (`CONFIG_TINY`, `CONFIG_BASE_FULL=n`, `CONFIG_FUTEX=n`) trims further — useful for sub-8 MB systems. The kernel's `Documentation/process/small-tasks.rst` is the canonical reference.

## The Rootfs: BusyBox, musl vs glibc

The root filesystem on an embedded Linux system typically weighs 2–20 MB. Two pieces dominate: the **C library** and the **shell + coreutils bundle**.

### C library

| libc | Size (shared) | Notes |
|---|---|---|
| **glibc** | ~2 MB shared, ~600 KB static (per-program) | Full i18n, NPTL, XSI features. Default in most distros. |
| **musl** | ~600 KB shared, ~100 KB static | POSIX-compliant, lighter, simpler, modern. Default in Alpine Linux and Buildroot's `musl` config. |
| **uClibc-ng** | ~400 KB shared | Older fork of uClibc; rarely picked now; musl has eaten its niche. |

musl is the right choice for embedded Linux on small systems. Static linking with musl produces a single self-contained binary; with glibc static linking is technically possible but fights NSS/DNS lookups that try to `dlopen` NSS modules at runtime.

### Shell and coreutils: BusyBox

**BusyBox** is one binary (~1 MB stripped) that contains the implementations of `ls`, `cat`, `sh`, `mount`, `init`, `vi`, `wget`, `telnetd`, `httpd`, `udhcpc`, and ~300 other commands. Each is a symlink to the single binary; the binary inspects `argv[0]` to decide what to do. Buildroot and Yocto both produce BusyBox by default.

For a systemd-based image you trade ~5 MB of rootfs for proper service management, journald, socket activation, and cgroup-based resource control. Many embedded products avoid systemd specifically to keep the image small — BusyBox init + a `/etc/init.d/rcS` script suffices.

### Filesystem types

| FS | Use | Compression | Wear-leveling | Notes |
|---|---|---|---|---|
| **initramfs (cpio)** | Boot rootfs | no | n/a | Loaded entirely into RAM; read-write ephemeral |
| **SquashFS** | Read-only rootfs | gzip/xz/zstd | n/a | Great for A/B partition rootfs |
| **JFFS2** | NOR flash rootfs | no | yes (in-FS) | Old, slow on big flash, mostly replaced by UBIFS |
| **UBIFS** | NAND flash rootfs | no | yes (via UBI) | The default for raw NAND |
| **ext4** | eMMC / SD card rootfs | no | no (depends on FTL) | The default for SD-card products |
| **F2FS** | eMMC / SD rootfs | no | yes (log-structured) | Better wear-leveling for flash than ext4 |

For an A/B-update product on eMMC: `SquashFS` for the read-only root + `ext4` (or `F2FS`) for the writable `/data` partition. For raw NAND: `UBIFS`. For a one-shot bootable image entirely in RAM: `initramfs` (cpio archive, decompressed by the kernel into a tmpfs).

## Device Tree: DTS and DTSO

The **device tree** is a data structure describing the hardware (CPU cores, memory map, peripherals, buses, interrupts, regulators, clocks) so that the same kernel binary can run on many board variants. Without it, every board needed its own kernel or its own `arch/arm/mach-*` C file; with it, the board-specific data lives in a `.dtb` blob passed by the bootloader.

A DTS source fragment:

```dts
/dts-v1/;
/ {
    compatible = "myvendor,mybox", "ti,am33xx";
    #address-cells = <1>;
    #size-cells = <1>;

    leds {
        compatible = "gpio-leds";
        pinctrl-names = "default";
        pinctrl-0 = <&led_pins>;

        status_green: led-0 {
            label = "mybox:green:status";
            gpios = <&gpio1 21 GPIO_ACTIVE_HIGH>;
            default-state = "on";
        };
    };
};

&i2c0 {
    status = "okay";
    clock-frequency = <400000>;

    eeprom@50 {
        compatible = "atmel,24c32";
        reg = <0x50>;
        pagesize = <32>;
        status = "okay";
    };
};
```

The `compatible` string is the binding contract between the device tree and the kernel driver — it tells the kernel "this node should be claimed by a driver that lists `atmel,24c32` (or a more general fallback) in its `of_match_table`." The bindings themselves are documented in `Documentation/devicetree/bindings/` in the kernel source; the matching schemas validate the DTS at build time.

### DTSO (Device Tree Overlay)

A **DTSO** is a runtime-applied patch to the live device tree. Used for hot-pluggable hardware: BeagleBone capes, Raspberry Pi HATs, FPGA bitstreams loaded after boot, dynamically-attached sensors on an industrial gateway. The overlay is applied by the bootloader (U-Boot `fdt apply`) or by user-space (`/sys/kernel/config/device-tree/overlays/foo/dtbo`) before the relevant driver probes.

```dts
/dts-v1/;
/plugin/;

&{/leds} {
    cape_led: cape-led-0 {
        label = "cape:blue:aux";
        gpios = <&gpio3 19 GPIO_ACTIVE_HIGH>;
    };
};
```

### Loading

U-Boot passes the DTB to the kernel on the boot command: `bootz ${loadaddr} - ${fdtaddr}` (the second argument is the ramdisk, the third is the DTB). On ARM32 the kernel receives the DTB physical address in `r2`; on ARM64 it is in `x0`. U-Boot can also apply overlays at boot time using `fdt addr ${fdtaddr}` then `fdt apply ${overlayaddr}` before `bootz`.

## Cross-Compilation: Toolchain and Sysroot

A **toolchain** for embedded Linux consists of: a C/C++ compiler (`gcc`), binutils (`as`, `ld`, `objdump`), the C library (`libc.so`, `libm.so`, `libpthread.so`, `ld.so`), and the kernel headers used to build userspace programs. The **target tuple** identifies it; for a Yocto-built ARM toolchain it looks like `arm-poky-linux-gnueabi-`.

Sources of toolchains:

- **Linaro** — prebuilt GCC for ARM A-profile; the long-standing industry default.
- **Bootlin (Free-Electrons) prebuilt toolchains** — clean, well-tested, musl and glibc variants.
- **Yocto's `meta-toolchain`** — produced by `bitbake meta-toolchain` or `populate_sdk_ext`; installs as an SDK shell environment.
- **crosstool-NG** — config-driven toolchain generator (kconfig-style menuconfig for the toolchain itself).
- **ARM ArmGNU** — official GCC toolchain from Arm.

Cross-compiling a program looks like:

```bash
# Source the Yocto SDK environment
$ . /opt/poky/3.1/environment-setup-cortexa9t2hf-neon-poky-linux-gnueabi
$ echo $CC
arm-poky-linux-gnueabi-gcc -mthumb -mfpu=neon -mfloat-abi=hard
      -mcpu=cortex-a9 -fstack-protector-strong -D_FORTIFY_SOURCE=2
      --sysroot=/opt/poky/3.1/sysroots/cortexa9t2hf-neon-poky-linux-gnueabi

$ ${CC} -O2 -o myapp main.c sensors.c -lpthread
$ file myapp
myapp: ELF 32-bit LSB executable, ARM, EABI5, version 1 (SYSV), dynamically linked,
interpreter /lib/ld-linux-armhf.so.3, stripped
```

The **sysroot** is the directory containing the target's `/usr/include`, `/usr/lib`, `/lib` — everything `gcc` needs to find headers and link against libc. Cross-compile frameworks like CMake integrate via a `toolchainfile.cmake` that sets `CMAKE_C_COMPILER`, `CMAKE_SYSROOT`, and `CMAKE_FIND_ROOT_PATH`.

For stripping production binaries to fit in Flash:

```bash
$ arm-poky-linux-gnueabi-strip --strip-unneeded myapp
$ ls -l myapp
-rwxr-xr-x 1 me me 28432 ... myapp   # was 1.3 MB
```

## Comparison to RTOS

| Property | Embedded Linux | RTOS (FreeRTOS/Zephyr) |
|---|---|---|
| Min RAM | 16 MB | 4 KB |
| Min Flash | 8 MB | 6 KB |
| Boot time (cold) | 0.5–5 s | 10–100 ms |
| Worst-case latency | 50 µs (PREEMPT_RT) to ms | < 1 µs to few µs |
| Scheduler | CFS, EDF (SCHED_DEADLINE), priorities | Fixed-priority preemptive, pluggable |
| MMU required | Yes | No (MPU optional) |
| Process isolation | Per-process address spaces | Shared address space (MPU isolation optional) |
| Filesystem | ext4, UBIFS, etc. | Optional (littlefs, FatFS) |
| Networking | Full TCP/IP, TLS, HTTP | FreeRTOS-Plus-TCP or Zephyr native |
| Security | Users/groups, SELinux, IMA | Per-task MPU regions, limited |
| Driver ecosystem | Massive | Per-vendor HAL |
| Certifiability | Hard (DO-178C, ASIL-D) | Practical (existing qualified distributions) |

A heterogeneous SoC like the **NXP i.MX8M** or **Renesas RZ/G2** typically runs Linux on the A-cores and FreeRTOS on the M4 core, connected by **RPMsg** (Remote Processor Messaging) over shared memory. The M4 handles motor control or audio real-time; the A-core handles UI, networking, OTA, ML. The kernel side manages the M4's lifecycle via the **remoteproc** and **rpmsg** subsystems, loading the M4 firmware at boot and exchanging messages over virtqueues.

## References

- [Yocto Project Documentation (current)](https://docs.yoctoproject.org/) — `bitbake` user manual, layer model, devtool, BSP guide.
- [Buildroot Manual](https://buildroot.org/downloads/manual/manual.html) — defconfig, package makefiles, post-build scripts.
- [kernel.org — Embedded Linux](https://www.kernel.org/doc/html/latest/) — start at `admin-guide/`, `process/small-tasks.rst`, and `devicetree/`.
- [U-Boot Official Documentation (DENX)](https://docs.u-boot.org/en/latest/) — boot flow, environment, FIT images, distro boot.
- [Bootlin Free Materials — Embedded Linux, Yocto, Buildroot](https://bootlin.com/docs/) — freely available training slides; the most thorough embedded Linux course material on the web.
- [Mastering the FreeRTOS Kernel book](https://www.freertos.org/Documentation/161204_Mastering_the_FreeRTOS_Real_Time_Kernel-A_Hands-On_Tutorial_Guide.pdf) — chapter on Linux+RTOS AMP scenarios.
- [Device Tree Specification (devicetree.org, v0.4)](https://www.devicetree.org/specifications/) — the formal DT spec, including `/plugin/` overlays and bindings.
- [Christopher Hallinan, *Embedded Linux Primer* (2nd ed., Pearson)](https://www.pearson.com/en-us/subject-catalog/p/embedded-linux-primer-a-practical-real-world-approach/P200000006441) — the standard textbook; older but the boot flow and toolchain chapters are still current.
- [Real-Time Linux Wiki (PREEMPT_RT)](https://wiki.linuxfoundation.org/realtime/) — patch status, latency measurement, configuration.
- See also: [Firmware Boot & Watchdogs](./firmware.md), [RTOS Internals](./rtos-internals.md), [Real-Time Systems](./real-time-systems.md), [FreeRTOS Deep Dive](./freertos.md).

## Interview Questions

1. **Walk through the boot process of an embedded Linux system from power-on to userspace.**
   ROM bootloader runs from on-chip mask ROM and loads SPL from a fixed offset in boot media; SPL initializes DDR and loads U-Boot proper; U-Boot initializes the board, applies any DT overlays, loads the kernel + DTB + (optional) initramfs into RAM, sets `bootargs`, and jumps; the kernel decompresses, sets up MMU and paging, applies the device tree, mounts the root filesystem, and calls `/sbin/init`; init brings up networking and services per `/etc/inittab` (BusyBox) or the systemd unit graph.

2. **Compare Buildroot and Yocto. When would you choose each?**
   Buildroot is a single-tree Makefile producing one image per defconfig; build time 20–60 min; no on-target package management; right when you ship one image and want to ship it next month. Yocto is a layered recipe engine producing a distro + SDK + package feeds; first build 2–6 hr; supports `dnf`/`apt`/`opkg` on target; right when you ship a family of products, need OTA package feeds, and have a dedicated build/release team.

3. **Why use musl instead of glibc on an embedded Linux system?**
   musl is ~600 KB shared vs glibc's ~2 MB; static linking with musl produces self-contained binaries without the NSS-dlopen landmines that make static glibc fragile; musl is POSIX-compliant, simpler to audit, and modern. For a 16 MB rootfs, switching from glibc to musl saves ~1.5 MB.

4. **Explain the role of the device tree and what "compatible" means.**
   The device tree describes the board hardware to the kernel so a single kernel binary runs on many variants. The `compatible` string in a node is the binding contract: it tells the kernel "this node should be claimed by a driver whose `of_match_table` lists this compatible string." The bindings themselves are documented under `Documentation/devicetree/bindings/` and validated by JSON schemas at build time.

5. **What does a DTSO (Device Tree Overlay) do, and when do you need one?**
   A DTSO is a runtime-applied patch to the live device tree, declared with `/dts-v1/; /plugin/;`. It adds nodes, modifies properties, or extends existing nodes — without recompiling the base DTB. Used for hot-pluggable hardware (BeagleBone capes, RPi HATs, FPGA bitstreams loaded post-boot, dynamically attached sensors). Applied by U-Boot (`fdt apply`) before boot or by user-space via `/sys/kernel/config/device-tree/overlays/`.

6. **Why is a sysroot needed when cross-compiling, and what does it contain?**
   The sysroot contains the target's `/usr/include` (all the headers, including libc and any libraries you link against) and `/usr/lib` + `/lib` (the `.so` files and `ld.so` for runtime linking). `gcc`'s `--sysroot=PATH` makes those appear at the right place relative to the toolchain; without it, the cross-compiler would link against your host system's x86 libc instead of the target's ARM libc, producing binaries that don't run.

7. **You need worst-case scheduling latency below 100 µs on an i.MX8M running Linux. How do you configure it?**
   Apply the PREEMPT_RT patch (or run kernel ≥ 6.12 with `CONFIG_PREEMPT_RT=y`); set `isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3` on the kernel command line; pin the RT task to an isolated CPU with `taskset -c 2`; give it `SCHED_FIFO` priority 80 with `chrt -f 80`; `mlockall` its memory; disable SMI in the BIOS if possible; verify with `cyclictest -t1 -p80 -i1000 -l100000 --mlockall`. Expect worst-case 50–100 µs on a 1 GHz Cortex-A53. For sub-µs determinism, you need an M4 core with FreeRTOS — Linux will not get there.

8. **Describe a typical heterogeneous AMP design on an i.MX8-class SoC.**
   Linux runs on the Cortex-A cores for HMI, networking, OTA, and ML inference. FreeRTOS runs on the Cortex-M core for hard-real-time control loops (motor, audio, sensor fusion). The kernel manages the M core's lifecycle via `remoteproc` (load/start/stop the M's firmware) and exchanges messages with it via `rpmsg` over shared memory + virtqueues. The M's firmware is shipped as an `.elf` in the rootfs and loaded at boot; a kernel driver registers with `rpmsg` to receive telemetry and send commands.

9. **Pick a rootfs layout for an A/B-update product on 256 MB eMMC.**
   Two SquashFS root partitions (`rootfs-A`, `rootfs-B`), one writable `ext4` `/data` partition, plus the U-Boot environment in a small partition at the start. On update, write the new SquashFS to the inactive partition, set the bootloader's `boot_slot` to the new partition, reboot. If health checks pass, mark the new slot as `good`; if not, U-Boot reverts on next boot. `/data` is shared between slots (user config, logs). SquashFS is read-only and compressed, so it survives power-cut and ships small.
