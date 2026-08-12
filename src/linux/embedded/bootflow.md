# Embedded Boot Flow

The Linux embedded boot flow is the sequence of stages that bring a device
from power-on reset to a running Linux kernel.  Understanding this flow is
essential for board bring-up, secure boot, firmware updates, and debugging
boot failures.  This page covers the standard flow: ROM → SPL → U-Boot →
Kernel, along with modern topics like FIT images and verified boot.

---

## 1. Overview: The Boot Chain

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Power   │    │   ROM    │    │   SPL    │    │  U-Boot  │    │  Linux   │
│  On      │───►│ Boot     │───►│ (pre-    │───►│ (full    │───►│ Kernel   │
│  Reset   │    │ ROM      │    │  loader) │    │  loader) │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                              │
                                              ├──► FIT image verification
                                              ├──► Kernel decompression
                                              ├──► DTB loading
                                              └──► Root filesystem
```

Each stage initializes more hardware and loads the next stage with
increasing capability.

---

## 2. Stage 1: ROM Boot Loader

### 2.1 What It Is

The ROM boot loader is **mask ROM** (read-only memory) burned into the SoC
during manufacturing.  It is the first code that executes after reset.

### 2.2 What It Does

1. **Minimal hardware init** — configure the clock, basic DRAM controller
   (or SRAM), and the boot media interface (eMMC, SD, SPI, UART).
2. **Read the boot image** — load the SPL from a predefined location on
   the boot media.
3. **Basic verification** — some SoCs verify a signature before loading.
4. **Jump to SPL** — transfer execution to the loaded SPL.

### 2.3 Boot Media Selection

Most SoCs select the boot media via hardware pins (boot pins / boot switch):

| Pins | Media |
|---|---|
| 000 | eMMC |
| 001 | SD card |
| 010 | SPI NOR flash |
| 011 | SPI NAND flash |
| 100 | USB DFU |
| 101 | UART (serial download) |
| 110 | NAND (raw) |

The ROM checks each media in a predefined order or follows the boot pin
configuration.

### 2.4 SoC-Specific ROM Boot

| SoC | ROM Name | Boot Media |
|---|---|---|
| NXP i.MX | HAB (High Assurance Boot) | eMMC, SD, SPI, NAND |
| Texas Instruments | ROM bootloader | eMMC, SD, SPI, UART |
| Broadcom BCM2835 | GPU boot ROM | SD, SPI, USB |
| Qualcomm | PBL (Primary Boot Loader) | eMMC, UFS |
| Allwinner | BROM | eMMC, SD, SPI, NAND |
| Rockchip | BootROM | eMMC, SD, SPI |
| Xilinx Zynq | BootROM | eMMC, SD, QSPI, JTAG |

---

## 3. Stage 2: SPL — Secondary Program Loader

### 3.1 Why SPL Is Needed

The ROM can only load a small image (typically 24-128 KB) because:

* SRAM is limited (no DRAM yet).
* The ROM code is simple and can only read from basic media.

The SPL initializes DRAM and loads the full U-Boot.

### 3.2 What SPL Does

1. **Initialize DRAM** — configure the DDR controller (timing, frequency,
   training).
2. **Configure clocks** — set up PLLs for the CPU and peripherals.
3. **Load U-Boot** — read U-Boot from eMMC/SD/SPI into DRAM.
4. **Verify U-Boot** — check a signature or hash (optional).
5. **Jump to U-Boot** — transfer execution.

### 3.3 SPL in U-Boot

U-Boot's build system produces both SPL and U-Boot from the same source
tree:

```bash
# Build SPL
make spl/u-boot-spl.bin

# Build both SPL and U-Boot
make

# Output files:
# spl/u-boot-spl.bin       — SPL binary
# u-boot.bin                — U-Boot binary
# u-boot-spl-with-spl.bin  — combined image (some platforms)
```

### 3.4 SPL Memory Map

```
0x0000_0000  ┌───────────────────────┐
             │  SRAM (used by SPL)  │  ← SPL runs here
             │  (typically 64-256KB) │
0x000x_xxxx  └───────────────────────┘

0x8000_0000  ┌───────────────────────┐
             │  DRAM (initialized    │  ← U-Boot loaded here
             │  by SPL)              │
             │  (256MB – 8GB)        │
0x8FFF_FFFF  └───────────────────────┘
```

### 3.5 SPL Boot Order

U-Boot SPL tries multiple boot sources in order:

```
CONFIG_SPL_BOOT_ORDER = "mmc0,mmc1,mmc2,spi,nand,usb"
```

Each source has a driver that knows how to read the next-stage image.

---

## 4. Stage 3: U-Boot

### 4.1 Overview

Das U-Boot (Universal Boot Loader) is the de facto standard boot loader for
embedded Linux.  It initializes remaining hardware and boots the kernel.

### 4.2 What U-Boot Does

1. **Hardware init** — serial, Ethernet, USB, storage, display.
2. **Environment** — load environment variables from storage.
3. **Load kernel** — read kernel image, DTB, and rootfs from storage.
4. **Verify** — check signatures (verified boot).
5. **Boot** — jump to kernel with DTB address in register.

### 4.3 U-Boot Commands

```bash
# U-Boot command line (hit a key during boot)

# List storage devices
mmc list
mmc info

# Load kernel from eMMC
load mmc 0:1 $kernel_addr_r Image
load mmc 0:1 $fdt_addr_r board.dtb

# Boot the kernel
booti $kernel_addr_r - $fdt_addr_r

# Or use a boot script
load mmc 0:1 $scriptaddr boot.scr
source $scriptaddr
```

### 4.4 Environment Variables

```bash
# Set boot arguments
setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p2 rootwait"

# Define boot command
setenv bootcmd "load mmc 0:1 $kernel_addr_r Image; load mmc 0:1 $fdt_addr_r board.dtb; booti $kernel_addr_r - $fdt_addr_r"

# Save environment
saveenv
```

### 4.5 Boot Scripts (`boot.scr`)

```
# boot.cmd source file
setenv bootargs "console=ttyS0,115200 root=/dev/mmcblk0p2"
load mmc 0:1 ${kernel_addr_r} Image
load mmc 0:1 ${fdt_addr_r} board.dtb
booti ${kernel_addr_r} - ${fdt_addr_r}
```

Compile with:

```bash
mkimage -C none -A arm64 -T script -d boot.cmd boot.scr
```

---

## 5. FIT Images

### 5.1 What Is FIT?

**FIT** (Flattened Image Tree) is a U-Boot image format based on the
Flattened Device Tree (FDT) structure.  It bundles multiple images (kernel,
DTB, ramdisk, scripts) into a single file with cryptographic verification.

### 5.2 FIT Image Structure

```
fit.itb (FIT Image Tree Blob)
├── images/
│   ├── kernel@1 {
│       data = <kernel binary>;
│       hash@1 { algo = "sha256"; };
│       signature@1 { algo = "rsa2048"; };
│   };
│   ├── fdt@1 {
│       data = <device tree blob>;
│       hash@1 { ... };
│   };
│   └── ramdisk@1 {
│       data = <initramfs>;
│       hash@1 { ... };
│   };
├── configurations {
│     default = "conf@1";
│     conf@1 {
│         kernel = "kernel@1";
│         fdt = "fdt@1";
│         ramdisk = "ramdisk@1";
│     };
│ };
```

### 5.3 Creating FIT Images

```dts
/* fit-image.its */
/dts-v1/;

/ {
    description = "Linux FIT Image";
    images {
        kernel@1 {
            description = "Linux kernel";
            data = /incbin/("Image");
            type = "kernel";
            arch = "arm64";
            os = "linux";
            compression = "none";
            load = <0x80080000>;
            entry = <0x80080000>;
            hash@1 {
                algo = "sha256";
            };
        };
        fdt@1 {
            description = "Device tree";
            data = /incbin/("board.dtb");
            type = "flat_dt";
            arch = "arm64";
            compression = "none";
            hash@1 {
                algo = "sha256";
            };
        };
    };
    configurations {
        default = "conf@1";
        conf@1 {
            description = "Boot Linux";
            kernel = "kernel@1";
            fdt = "fdt@1";
        };
    };
};
```

Build:

```bash
mkimage -f fit-image.its fit.itb
```

### 5.4 Loading FIT Images

```bash
# In U-Boot
load mmc 0:1 $loadaddr fit.itb
bootm $loadaddr
# U-Boot automatically extracts kernel, DTB, and ramdisk from the FIT
```

---

## 6. Verified Boot

### 6.1 Why Verified Boot?

Verified boot ensures that only authenticated code runs on the device.  It
prevents:

* Loading modified firmware.
* Booting a tampered kernel.
* Persistent rootkits.

### 6.2 U-Boot Verified Boot (CONFIG_SECURE_BOOT)

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│  ROM      │───►│  SPL     │───►│  U-Boot  │
│  verify   │    │  verify  │    │  verify  │
│  SPL sig  │    │  U-Boot  │    │  FIT sig │
│           │    │  sig     │    │          │
└──────────┘    └──────────┘    └──────────┘
```

### 6.3 Signing FIT Images

```bash
# Generate RSA key
openssl genrsa -F4 -out signing_key.pem 2048

# Create certificate
openssl req -new -x509 -key signing_key.pem -out signing_key.crt

# Sign the FIT image (add signature node to .its)
mkimage -f fit-image.its -K dtb -k keys-dir -r fit.itb
```

### 6.4 Key Storage

| Method | Security Level |
|---|---|
| Software key (file) | Low — key can be extracted |
| OTP fuse hash | Medium — hash burned in SoC |
| HSM (Hardware Security Module) | High — key never leaves HSM |
| TPM | High — key sealed to TPM |
| TrustZone / Secure World | High — key in secure memory |

### 6.5 Chain of Trust

```
SoC Root of Trust (ROM)
  └── SPL (signed, verified by ROM)
        └── U-Boot (signed, verified by SPL)
              └── FIT Image (signed, verified by U-Boot)
                    ├── Kernel (hash verified)
                    ├── DTB (hash verified)
                    └── Rootfs (hash verified or dm-verity)
```

---

## 7. Device Tree (DTB)

### 7.1 Role in Boot

The Device Tree Blob (DTB) describes the hardware to the kernel.  U-Boot
loads it and passes its address to the kernel.

### 7.2 DTB Loading Methods

| Method | How |
|---|---|
| Separate file | `load mmc 0:1 $fdt_addr_r board.dtb` |
| FIT image | Embedded in FIT, loaded automatically |
| In-kernel | `CONFIG_ARM64_APPENDED_DTB` (appended to kernel) |
| ACPI | x86 and some ARM64 servers use ACPI instead |

### 7.3 DTB Selection

Some boards have multiple DTBs.  U-Boot can select based on:

* Board revision (read from EEPROM)
* Hardware detection (GPIO straps)
* Environment variable (`fdtfile`)

```bash
# U-Boot auto-detection
setenv fdtfile am335x-boneblack.dtb
```

---

## 8. Root Filesystem

### 8.1 Root Filesystem Types

| Type | Storage | Use Case |
|---|---|---|
| **initramfs** | RAM (built into kernel or separate) | Minimal boot, then pivot |
| **ext4 on block** | eMMC/SD/NVMe | Full Linux system |
| **SquashFS** | NOR/NAND flash | Read-only embedded |
| **UBIFS** | NAND flash | Read-write NAND |
| **NFS** | Network | Development |
| **tmpfs** | RAM | Stateless systems |

### 8.2 Passing Root to Kernel

```bash
# Block device
setenv bootargs "root=/dev/mmcblk0p2 rootwait"

# NFS
setenv bootargs "root=/dev/nfs nfsroot=192.168.1.1:/export/rootfs ip=dhcp"

# Initramfs (built into kernel)
setenv bootargs "root=/dev/ram0"

# PARTUUID
setenv bootargs "root=PARTUUID=abcd1234-02"
```

---

## 9. Modern Boot Flow Variants

### 9.1 UEFI on Embedded

Some embedded platforms (ARM64 servers, RISC-V) use UEFI instead of U-Boot:

```
ROM → UEFI firmware (TF-A + U-Boot as UEFI payload) → GRUB/shim → Kernel
```

### 9.2 Coreboot + U-Boot

Some x86 embedded boards use Coreboot as the initial firmware, with U-Boot
or GRUB as the payload:

```
Coreboot (replaces BIOS) → U-Boot/GRUB payload → Kernel
```

### 9.3 Android Verified Boot (AVB)

Android devices use a similar chain with `vbmeta` structures:

```
BootROM → Bootloader (ABL) → vbmeta verification → boot.img (kernel + ramdisk)
```

### 9.4 Raspberry Pi Boot

The Raspberry Pi has a unique flow:

```
GPU ROM → bootcode.bin (first stage, on SD) → start*.elf (GPU firmware) → kernel
```

The GPU boots first, initializes SDRAM, and then loads the ARM kernel.

---

## 10. Debugging Boot Issues

### 10.1 Serial Console

A serial console (UART) is the most important debug tool:

```bash
# Connect with minicom/screen
screen /dev/ttyUSB0 115200

# Or with picocom
picocom -b 115200 /dev/ttyUSB0
```

### 10.2 Common Problems

| Symptom | Likely Cause |
|---|---|
| No output at all | Wrong baud rate, wrong UART, power issue |
| U-Boot hangs | DDR training failure, wrong DTB |
| Kernel panic: no init | Wrong root= argument, missing rootfs |
| Kernel panic: DTB | Wrong DTB, missing nodes |
| Boot loop | Watchdog, power supply instability |

### 10.3 U-Boot Debugging

```bash
# Enable verbose boot
setenv bootargs "... loglevel=7"

# Break into U-Boot
# Press a key during the "Hit any key to stop autoboot" countdown

# Test memory
mw.l 0x80000000 0xDEADBEEF 100
md.l 0x80000000 100

# Read boot media
mmc read $loadaddr 0 0x100
md.l $loadaddr 20
```

### 10.4 JTAG

For hard-to-debug issues (SPL crashes, ROM boot failures), JTAG provides
direct CPU debugging:

```bash
# OpenOCD with JTAG adapter
openocd -f interface/jlink.cfg -f target/cortex-a53.cfg

# GDB
arm-none-eabi-gdb
(gdb) target remote :3333
(gdb) hbreak *0x80000000
(gdb) continue
```

---

## 11. Further Reading

* **U-Boot documentation: https://docs.u-boot.org/**
* **U-Boot FIT image docs: `doc/uImage.FIT/`**
* **LWN: [Booting Linux](https://lwn.net/Articles/636902/)**
* **ARM Trusted Firmware-A (TF-A): https://trustedfirmware-a.readthedocs.io/**
* **Device Tree specification: https://devicetree.org/**
* **OpenBMC boot flow: https://github.com/openbmc/docs**
* **Raspberry Pi boot flow: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-boot-modes**

---

## A/B Partition Schemes

For reliable field updates, embedded systems use A/B (dual) partition schemes:

### How A/B Works

```
┌─────────────────────────────────────────────┐
│  Storage (eMMC/NVMe)                        │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Boot A   │  │ Boot B   │  │ Shared   │ │
│  │ (kernel  │  │ (kernel  │  │ (data,   │ │
│  │  + rootfs│  │  + rootfs│  │  config) │ │
│  │  active) │  │  standby)│  │          │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────┘
```

```bash
# U-Boot A/B boot selection
# Check which slot is active
fw_printenv boot_active
# boot_active=A

# Switch to B after OTA update
fw_setenv boot_active=B

# Mark slot as successful (prevents rollback)
fw_setenv boot_B_successful=1

# Rollback if new kernel fails to boot
# (watchdog resets, bootloader detects failure, switches slot)
```

### RAUC (Robust Auto-Update Controller)

RAUC is a popular open-source update framework for embedded Linux:

```bash
# Install RAUC
sudo apt install rauc

# Create a RAUC update bundle (.raucb)
rauc bundle --cert cert.pem --key key.pem \
    update-dir/ update-2024.07.raucb

# Install the bundle
rauc install update-2024.07.raucb

# RAUC manages:
# - A/B slot switching
# - Boot count tracking
# - Rollback on failure
# - Signed update bundles
# - Hooks for custom update logic

# RAUC configuration: /etc/rauc/system.conf
# [system]
# compatible=MyBoard
# bootloader=uboot
# 
# [slot.rootfs.0]
# device=/dev/mmcblk0p2
# type=ext4
# bootname=A
# 
# [slot.rootfs.1]
# device=/dev/mmcblk0p3
# type=ext4
# bootname=B
```

### SWUpdate

SWUpdate is another embedded update framework with web UI support:

```bash
# SWUpdate supports:
# - Single and double copy (A/B)
# - SURICATTA (hawkBit backend) for OTA
# - Web-based update server
# - Pre/post install hooks
# - Artifact verification (RSA, SHA256)

# Check current version
swupdate -v

# Apply update from file
swupdate -i update.swu

# Apply update from network (hawkBit server)
swupdate -u "-u http://hawkbit:8080"
```

### ChromeOS Verified Boot (depthcharge)

ChromeOS uses a sophisticated verified boot chain:

```
ROM → depthcharge (payload in coreboot) → kernel (vboot verified)
```

```bash
# ChromeOS uses vboot (verified boot) library
# Key features:
# - Two firmware slots (A/B) with separate keys
# - Kernel partition has its own verification
# - Developer mode allows custom keys
# - Recovery mode from USB

# Check ChromeOS boot status
crossystem
# dev_boot_usb=0
# dev_boot_signed_only=0
# mainfw_type=normal
# tpm_fwver=0x00010001
```

### Android Verified Boot (AVB)

Android uses AVB (Android Verified Boot) for boot chain verification:

```bash
# AVB uses vbmeta (verified boot metadata) structures
# vbmeta contains:
# - Hash descriptors for boot, dtbo, system, vendor partitions
# - Chain descriptors for linking vbmeta partitions
# - Hash tree descriptors for dm-verity

# Verify Android boot image
avbtool verify_image --image boot.img

# Extract vbmeta info
avbtool info_image --image vbmeta.img

# Android boot chain:
# BootROM → bootloader (ABL) → vbmeta → boot.img → system (dm-verity)
```

## Filesystem Considerations for Boot

### SquashFS for Read-Only Root

```bash
# SquashFS is common for embedded read-only rootfs
# Advantages:
# - Excellent compression (LZ4, LZMA, ZSTD)
# - Fast random access
# - No journaling overhead
# - Integrity via dm-verity

# Create SquashFS rootfs
mksquashfs rootfs/ rootfs.squashfs -comp zstd -b 256K

# Mount at boot (via initramfs or fstab)
mount -t squashfs /dev/mmcblk0p3 /rootfs

# Writable overlay for data persistence
mount -t tmpfs tmpfs /rootfs/var
# Or use overlayfs:
mount -t overlay overlay \
    -o lowerdir=/rootfs,upperdir=/data/upper,workdir=/data/work \
    /merged
```

### NAND Flash File Systems

```bash
# For raw NAND flash (no FTL):
# - JFFS2: Journaling Flash File System v2
#   Good for small partitions (<256MB)
#   Wear leveling built-in
#   Slow mount on large partitions

# - UBIFS: Unsorted Block Image File System
#   Better for larger NAND (>256MB)
#   Requires UBI (Unsorted Block Images) layer
#   Faster mount, better wear leveling

# Create UBI volume
ubinfo -a
ubiformat /dev/mtd1
ubiattach -m 1 -d 0
ubimkvol /dev/ubi0 -N rootfs -m

# Create UBIFS
mkfs.ubifs -m 2048 -e 129024 -c 2048 -r rootfs/ ubifs.img

# Mount UBIFS
mount -t ubifs ubi0:rootfs /mnt
```

## Power Management During Boot

```bash
# Minimize boot time by:
# 1. Use initramfs with minimal tools (BusyBox)
# 2. Disable unused kernel features (CONFIG_EMBEDDED=y)
# 3. Use kernel modules only for non-essential drivers
# 4. Parallel init (systemd or custom parallel scripts)
# 5. Read-only root filesystem (no fsck at boot)
# 6. Skip unnecessary hardware init

# Measure boot time
systemd-analyze
systemd-analyze blame
systemd-analyze critical-chain

# Or for non-systemd:
dmesg | head -1
# [    0.000000] Linux version 6.1.0 (builder@host)

# Boot time breakdown
dmesg | grep -E '^\[[0-9.]+\]' | tail -1
# Shows total kernel boot time
```

## Cross-References

* U-Boot — detailed U-Boot reference
* Device Tree — hardware description format
* [dm-verity](../kernel/drivers/dm-verity.md) — block-level verified boot
* ARM TrustZone — secure world boot
* Kernel Command Line — boot parameters
* [initramfs](initramfs.md) — early userspace
* NAND/NOR Flash — flash storage subsystems

