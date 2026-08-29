# Bootloader (GRUB)

## Overview

A **bootloader** is the first software program that runs when a computer starts. Its primary job is to load the operating system kernel into memory and transfer control to it. The most widely used bootloader in the Linux world is **GRUB** (GRand Unified Bootloader), specifically **GRUB2**.

Without a bootloader, the CPU would have no way to find and load the kernel — the firmware (BIOS/UEFI) only knows how to read a small amount of code from disk, and the kernel is far too large and complex to be loaded directly.

---

## Boot Process Overview

```text
Power On
  |
  v
Firmware (BIOS/UEFI)
  |
  v
Bootloader (GRUB)
  |
  v
Load kernel image (vmlinuz)
  |
  v
Load initramfs/initrd
  |
  v
Kernel initialization
  |
  v
Mount root filesystem
  |
  v
Execute init system (systemd, PID 1)
  |
  v
User-space services
```

---

## GRUB2 Architecture

GRUB2 (the current version, as opposed to legacy GRUB) is a modular, multi-stage bootloader.

### Stages of GRUB2

```
┌──────────────────────────────────────────────────┐
│ Stage 1: boot.img (MBR)                          │
│   → 446 bytes in MBR                             │
│   → Just enough to load the next stage            │
│   → Knows location of core.img                    │
├──────────────────────────────────────────────────┤
│ Stage 1.5: core.img                               │
│   → Stored in the gap between MBR and first       │
│     partition (post-MBR gap, ~1 MB)               │
│   → Contains filesystem drivers                   │
│   → Can read /boot/grub/ on the filesystem        │
├──────────────────────────────────────────────────┤
│ Stage 2: /boot/grub/ modules + config             │
│   → grub.cfg — menu configuration                 │
│   → *.mod — loadable modules (filesystem,         │
│     video, crypto, etc.)                          │
│   → Displays boot menu                            │
│   → Loads kernel and initramfs                    │
└──────────────────────────────────────────────────┘
```

### UEFI Boot Path

For UEFI systems, the stages are different:

```
UEFI Firmware
  └── ESP: /EFI/<distro>/shimx64.efi   (Secure Boot shim)
        └── /EFI/<distro>/grubx64.efi   (GRUB EFI binary)
              └── /boot/grub/grub.cfg   (configuration)
                    ├── linux  /vmlinuz-xxx
                    └── initrd /initrd-xxx.img
```

The UEFI path skips the MBR-based Stage 1 and 1.5 entirely — GRUB is a single `.efi` binary loaded directly from the EFI System Partition.

---

## GRUB2 Configuration

### Main Configuration File

The main configuration file is `/boot/grub/grub.cfg` (or `/boot/grub2/grub.cfg` on RHEL-based systems). **This file should not be edited directly** — it is auto-generated.

```bash
# /boot/grub/grub.cfg (auto-generated, do NOT edit)

set default=0
set timeout=5

menuentry 'Ubuntu' {
    insmod gzio
    insmod part_gpt
    insmod ext2
    set root='hd0,gpt2'
    linux /vmlinuz-5.15.0-58-generic root=/dev/mapper/ubuntu--vg-root ro quiet splash
    initrd /initrd.img-5.15.0-58-generic
}

menuentry 'Ubuntu (recovery mode)' {
    insmod gzio
    insmod part_gpt
    insmod ext2
    set root='hd0,gpt2'
    linux /vmlinuz-5.15.0-58-generic root=/dev/mapper/ubuntu--vg-root ro recovery nomodeset
    initrd /initrd.img-5.15.0-58-generic
}
```

### User Configuration Files

To customize GRUB, edit `/etc/default/grub`:

```bash
# /etc/default/grub
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR=`lsb_release -i -s 2> /dev/null || echo Debian`
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""
```

After editing, regenerate the config:

```bash
# Debian/Ubuntu
sudo update-grub
# or
sudo grub-mkconfig -o /boot/grub/grub.cfg

# RHEL/CentOS/Fedora
sudo grub2-mkconfig -o /boot/grub2/grub.cfg
```

### Custom Entries

Add custom scripts in `/etc/grub.d/40_custom`:

```bash
#!/bin/sh
exec tail -n +3 $0
# This file provides an easy way to add custom menu entries.

menuentry "Custom OS" {
    set root='hd0,gpt1'
    linux /boot/vmlinuz-custom root=/dev/sda1
    initrd /boot/initrd-custom.img
}
```

---

## GRUB2 Command Line

If GRUB fails to find its config, it drops to a rescue shell. Essential commands:

```grub
# List available disks and partitions
grub> ls
(hd0) (hd0,gpt2) (hd0,gpt1)

# Inspect a partition's filesystem
grub> ls (hd0,gpt2)/
# Shows root filesystem contents

# Manually boot a kernel
grub> set root=(hd0,gpt2)
grub> linux /vmlinuz-5.15.0 root=/dev/sda2
grub> initrd /initrd.img-5.15.0
grub> boot
```

---

## The Role of initramfs/initrd

### What is initramfs?

The **initial RAM filesystem** (initramfs) is a temporary root filesystem loaded into memory by GRUB before the real root filesystem is mounted. It contains:

- Essential kernel modules (storage drivers, filesystem drivers)
- The `init` script (or `init` binary)
- Utilities like `mount`, `modprobe`, `udev`

### Why is initramfs Needed?

Modern systems often have root filesystems on:
- LVM (Logical Volume Manager)
- RAID arrays
- Encrypted partitions (LUKS)
- Network storage (iSCSI, NFS)

The kernel can't access these without the appropriate drivers, but the drivers are stored on the root filesystem — a chicken-and-egg problem. initramfs solves this by providing a minimal environment with the necessary drivers.

### initramfs Boot Sequence

```text
GRUB loads kernel + initramfs
  |
  v
Kernel unpacks initramfs into rootfs tmpfs
  |
  v
Execute /init
  |
  v
Load required kernel modules (dm-crypt, lvm, ahci, ...)
  |
  v
Discover and mount the real root filesystem
  |
  v
pivot_root / switch_root to the real rootfs
  |
  v
Execute /sbin/init (systemd)
```

### Inspect initramfs

```bash
# List contents of initramfs
lsinitramfs /boot/initrd.img-$(uname -r) | head -30

# Extract initramfs to a directory
mkdir /tmp/initrd
cd /tmp/initrd
unmkinitramfs /boot/initrd.img-$(uname -r) .

# On RHEL/CentOS
lsinitrd /boot/initramfs-$(uname -r).img | head -30
dracut --unpack /boot/initramfs-$(uname -r).img
```

### Rebuild initramfs

```bash
# Debian/Ubuntu
sudo update-initramfs -u

# RHEL/CentOS/Fedora
sudo dracut --force

# Arch Linux
sudo mkinitcpio -P
```

---

## Installing and Repairing GRUB

### Install GRUB to Disk

```bash
# BIOS/MBR
sudo grub-install /dev/sda

# UEFI
sudo grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu
```

### Repair GRUB from Live USB

```bash
# Boot from live USB, then:
sudo mount /dev/sda2 /mnt              # root partition
sudo mount /dev/sda1 /mnt/boot/efi     # EFI partition (UEFI only)
sudo mount --bind /dev /mnt/dev
sudo mount --bind /proc /mnt/proc
sudo mount --bind /sys /mnt/sys
sudo mount --bind /run /mnt/run

sudo chroot /mnt

# Inside chroot:
grub-install /dev/sda                   # BIOS
# or
grub-install --target=x86_64-efi --efi-directory=/boot/efi  # UEFI
update-grub
exit

sudo umount -R /mnt
sudo reboot
```

---

## Other Bootloaders

| Bootloader | Platform | Notes |
|---|---|---|
| **GRUB2** | Linux, multi-boot | Most common Linux bootloader |
| **systemd-boot** | UEFI only | Simple, fast, used by Arch, Pop!_OS |
| **rEFInd** | UEFI | Graphical, auto-detects OSes |
| **LILO** | Legacy Linux | Deprecated, replaced by GRUB |
| **Windows Boot Manager** | Windows | `bootmgfw.efi` on ESP |
| **U-Boot** | Embedded/ARM | Common on Raspberry Pi, routers |
| **barebox** | Embedded | Successor to U-Boot for some platforms |

### systemd-boot Example

```bash
# Install systemd-boot
bootctl install

# Configuration: /boot/loader/loader.conf
timeout 3
default ubuntu-*

# Entries: /boot/loader/entries/ubuntu-5.15.0.conf
title   Ubuntu
linux   /vmlinuz-5.15.0-generic
initrd  /initrd.img-5.15.0-generic
options root=/dev/sda2 rw
```

---

## Interview Questions

### Q1: What are the stages of GRUB2?
**A:** GRUB2 has three stages:
1. **Stage 1 (boot.img)**: 446 bytes in the MBR, just enough to find and load Stage 1.5.
2. **Stage 1.5 (core.img)**: Located in the post-MBR gap, contains filesystem drivers to read /boot/grub/.
3. **Stage 2**: The full GRUB environment in /boot/grub/, with modules, config files, and the boot menu.

For UEFI, GRUB is a single `.efi` binary on the EFI System Partition — the MBR-based stages are not used.

### Q2: What is the purpose of initramfs?
**A:** initramfs is a temporary root filesystem loaded into RAM by the bootloader. It provides the kernel modules and utilities needed to mount the real root filesystem. This is essential when the root filesystem is on LVM, RAID, encrypted partitions, or network storage — the kernel needs drivers to access these, but the drivers are on the root filesystem itself.

### Q3: How do you fix a broken GRUB installation?
**A:** Boot from a live USB, mount the root partition (and EFI partition for UEFI), chroot into it, then run `grub-install` and `update-grub` (or `grub2-mkconfig`). This reinstalls GRUB to the disk and regenerates the configuration.

### Q4: What is the difference between initramfs and initrd?
**A:** **initrd** is an older mechanism that creates a virtual disk (block device) in RAM. **initramfs** is a newer approach that uses a tmpfs (ramfs) — it's simpler, doesn't require a block device driver, and is the standard in modern Linux. The terms are often used interchangeably, but modern systems almost always use initramfs.

### Q5: What happens when GRUB can't find grub.cfg?
**A:** GRUB drops to its **rescue shell** (`grub>` prompt). From there, you can manually specify the root partition, kernel path, and initrd path, then boot. This is a critical skill for system recovery.

---

## Common Mistakes

1. **Editing grub.cfg directly**: Always edit `/etc/default/grub` and run `update-grub`. Direct edits to `grub.cfg` are overwritten on kernel updates.
2. **Forgetting to run update-grub**: Changes to `/etc/default/grub` don't take effect until the config is regenerated.
3. **Not mounting the EFI partition**: On UEFI systems, `/boot/efi` must be mounted before running `grub-install`.
4. **Confusing GRUB Legacy and GRUB2**: They have different configuration syntax and file locations. `menu.lst` is GRUB Legacy; `grub.cfg` is GRUB2.
5. **Not rebuilding initramfs after hardware changes**: Adding new storage controllers or changing root filesystem type requires rebuilding initramfs with `update-initramfs -u` or `dracut --force`.

---

## Summary

The bootloader is the critical bridge between firmware and the operating system. GRUB2 is the de facto Linux bootloader, operating in multiple stages to progressively load more complex code until the kernel is running. Understanding the boot chain (firmware → bootloader → initramfs → kernel → init) is essential for system administration and troubleshooting.

**Key points for interviews:**
- GRUB2 stages: boot.img (MBR) → core.img (post-MBR gap) → /boot/grub/ modules and config
- UEFI path uses a single `.efi` binary on the ESP
- initramfs provides temporary drivers to mount the real root filesystem
- Always use `/etc/default/grub` + `update-grub` for configuration changes
- Know how to repair GRUB from a live USB (chroot + grub-install)


## Cross References

- [BIOS/UEFI](bios-uefi.md)
- [Init Systems](init-systems.md)
- [Kernel Threads](../threads/user-vs-kernel.md)
