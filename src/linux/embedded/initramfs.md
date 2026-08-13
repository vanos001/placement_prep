# Initramfs

## Overview

**initramfs** (initial RAM filesystem) is a temporary root filesystem loaded into memory by the bootloader. It runs the first userspace process (`init`) before the real root filesystem is mounted. Initramfs handles tasks that must happen before the root filesystem is available:

- Loading kernel modules needed to access the root device
- Assembling RAID arrays or LVM volumes
- Unlocking encrypted root partitions (LUKS)
- Running early userspace utilities
- Pivoting to the real root filesystem

> **See also:** [Boot Process](../kernel/boot-process.md), dracut, Root Filesystem

---

## cpio Format

### What is cpio?

Initramfs uses the **cpio** (copy in/out) archive format. Unlike an initrd (which is a filesystem image), initramfs is a cpio archive that the kernel unpacks into a tmpfs:

```
Bootloader → Kernel → Unpacks cpio into tmpfs → Runs /init
```

### Creating a Basic cpio Archive

```bash
# Create a minimal initramfs
mkdir -p initramfs/{bin,sbin,etc,proc,sys,dev}

# Copy busybox (statically linked)
cp /bin/busybox initramfs/bin/
cd initramfs/bin
for cmd in sh mount umount mkdir cat echo ls; do
    ln -s busybox $cmd
done
cd ../..

# Create the init script (see below)
# ...

# Pack as cpio
cd initramfs
find . | cpio -o -H newc | gzip > ../initramfs.cpio.gz
cd ..
```

### cpio Formats

| Format | Description                    | Kernel Support |
|--------|--------------------------------|----------------|
| `newc` | SVR4 "new" format (required)   | Yes            |
| `odc`  | POSIX.1 portable format        | Yes            |
| `crc`  | Like newc but with CRC         | Yes            |

The kernel requires `newc` or `crc` format for initramfs.

### Multiple cpio Archives

The kernel can unpack multiple concatenated cpio archives:

```bash
# Combine base + microcode + custom
cat base.cpio.gz intel-ucode.cpio.gz custom.cpio.gz > initramfs.cpio.gz
```

This is how CPU microcode updates are applied early in boot.

---

## The init Script

### Minimal init Script

```bash
#!/bin/sh
# /init — First userspace process in initramfs

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

# Load necessary modules
modprobe ext4
modprobe ahci

# Wait for root device to appear
echo "Waiting for root device..."
while [ ! -b /dev/sda1 ]; do
    sleep 0.1
done

# Mount the real root
mount -t ext4 /dev/sda1 /mnt/root

# Clean up
umount /proc
umount /sys
umount /dev

# Pivot to real root
exec switch_root /mnt/root /sbin/init
```

### More Complete Example

```bash
#!/bin/sh
set -e

PATH=/sbin:/bin:/usr/sbin:/usr/bin

# Mount virtual filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /tmp

# Parse kernel command line
ROOT=""
for param in $(cat /proc/cmdline); do
    case $param in
        root=*) ROOT="${param#root=}";;
        rootdelay=*) ROOTDELAY="${param#rootdelay=}";;
    esac
done

# Wait for root device
if [ -n "$ROOTDELAY" ]; then
    sleep "$ROOTDELAY"
fi

# Handle different root device types
case "$ROOT" in
    UUID=*)
        ROOT_DEV=$(blkid -U "${ROOT#UUID=}")
        ;;
    LABEL=*)
        ROOT_DEV=$(blkid -L "${ROOT#LABEL=}")
        ;;
    /dev/*)
        ROOT_DEV="$ROOT"
        ;;
    *)
        echo "Unknown root device: $ROOT"
        exec /bin/sh
        ;;
esac

# Load filesystem module
FSTYPE=$(blkid -s TYPE -o value "$ROOT_DEV")
modprobe "$FSTYPE" 2>/dev/null || true

# Mount root read-only first
mount -t "$FSTYPE" -o ro "$ROOT_DEV" /mnt/root

# Optionally mount submounts
if [ -f /mnt/root/etc/fstab ]; then
    # Mount /proc, /sys, /dev in new root
    mount -t proc proc /mnt/root/proc
    mount -t sysfs sysfs /mnt/root/sys
    mount -o bind /dev /mnt/root/dev
fi

# Switch to real root
echo "Switching to real root..."
exec switch_root /mnt/root /sbin/init

# If switch_root fails, drop to shell
echo "Failed to switch root!"
exec /bin/sh
```

### Kernel Command Line

The kernel passes parameters to init via `/proc/cmdline`:

```
root=/dev/sda1 ro rootfstype=ext4 rootdelay=5 init=/sbin/init
```

| Parameter    | Description                              |
|-------------|------------------------------------------|
| `root=`     | Root device (UUID, LABEL, or path)       |
| `rootfstype`| Root filesystem type                     |
| `rootdelay` | Seconds to wait for root device          |
| `init=`     | Path to init program on root             |
| `rd.*`      | dracut-specific parameters               |

---

## gen_init_cpio

### Purpose

`gen_init_cpio` is a kernel utility that creates cpio archives from a **specification file**. It provides more control than `find | cpio`.

### Building gen_init_cpio

```bash
# It's in the kernel source
cd /usr/src/linux
make usr/gen_init_cpio
```

### Specification File Format

```
# /path/to/initramfs.list

# Directory
dir /bin 755 0 0
dir /sbin 755 0 0
dir /etc 755 0 0
dir /proc 755 0 0
dir /sys 755 0 0
dir /dev 755 0 0

# File with inline content
file /init /path/to/init.sh 755 0 0

# File from host filesystem
file /bin/busybox /bin/busybox 755 0 0

# Symlink
slink /bin/sh /bin/busybox 755 0 0

# Special files
nod /dev/console 644 0 0 c 5 1
nod /dev/null 644 0 0 c 1 3
nod /dev/tty 644 0 0 c 5 0
nod /dev/sda1 644 0 0 b 8 1

# Concatenate external cpio
# external_cpio /path/to/extra.cpio
```

### Generating the Archive

```bash
# From specification file
./usr/gen_init_cpio initramfs.list | gzip > initramfs.cpio.gz

# Compressed
./usr/gen_init_cpio initramfs.list | xz > initramfs.cpio.xz
```

### Embedded in Kernel

```bash
# Embed initramfs in kernel image
# In .config:
CONFIG_INITRAMFS_SOURCE="/path/to/initramfs.list"
# Then build the kernel — initramfs is built into vmlinuz
```

---

## dracut

### What is dracut?

**dracut** is an event-driven initramfs infrastructure used by Fedora, RHEL, CentOS, SUSE, and others. It generates initramfs images automatically based on the current system configuration.

### Basic Usage

```bash
# Generate initramfs for current kernel
dracut /boot/initramfs-$(uname -r).img $(uname -r)

# Force regeneration
dracut --force /boot/initramfs-$(uname -r).img $(uname -r)

# Add specific modules
dracut --add "lvm crypt" /boot/initramfs-$(uname -r).img $(uname -r)

# List included modules
dracut --list-modules

# Show what would be included (dry run)
dracut --print-cmdline
```

### dracut Modules

dracut is modular — each module adds specific functionality:

| Module        | Description                              |
|---------------|------------------------------------------|
| `base`        | Core initramfs functionality             |
| `lvm`         | LVM volume assembly                     |
| `crypt`       | LUKS/dm-crypt decryption                |
| `mdraid`      | Software RAID assembly                  |
| `nfs`         | NFS root filesystem                     |
| `iscsi`       | iSCSI root device                       |
| `multipath`   | Multipath device handling               |
| `plymouth`    | Boot splash screen                      |
| `systemd`     | systemd as init in initramfs            |
| `dracut-systemd` | systemd-based dracut boot          |

### dracut Configuration

```bash
# /etc/dracut.conf.d/custom.conf
# Add LVM and crypto support
add_dracutmodules+=" lvm crypt "

# Include specific kernel modules
add_drivers+=" ahci ext4 "

# Set compression
compress="xz"

# Host-only mode (default: yes)
hostonly="yes"

# Add custom files
install_items+=" /usr/bin/cryptsetup "
```

### dracut Command Line

```bash
# Add modules
dracut --add "lvm crypt" initramfs.img

# Exclude modules
dracut --omit "network plymouth" initramfs.img

# Include firmware
dracut --fwdir /lib/firmware initramfs.img

# Minimal initramfs
dracut --hostonly --no-hostonly-cmdline initramfs.img

# Debug mode
dracut --debug initramfs.img
```

---

## Other initramfs Generators

### mkinitcpio (Arch Linux)

```bash
# Generate initramfs
mkinitcpio -P  # All presets
mkinitcpio -p linux  # Specific preset

# Configuration: /etc/mkinitcpio.conf
HOOKS="base udev autodetect modconf block filesystems keyboard fsck"
```

### initramfs-tools (Debian/Ubuntu)

```bash
# Generate initramfs
update-initramfs -u  # Update current kernel
update-initramfs -c -k $(uname -r)  # Create new

# Configuration: /etc/initramfs-tools/
```

### Comparison

| Tool           | Distribution           | Config Location          |
|----------------|------------------------|--------------------------|
| `dracut`       | Fedora, RHEL, SUSE    | `/etc/dracut.conf.d/`   |
| `mkinitcpio`   | Arch Linux, Manjaro   | `/etc/mkinitcpio.conf`  |
| `initramfs-tools` | Debian, Ubuntu      | `/etc/initramfs-tools/` |

---

## Root Pivot (switch_root)

### The Pivot Process

`switch_root` is the critical step that transitions from initramfs to the real root:

```bash
# 1. Mount real root
mount /dev/sda1 /mnt/root

# 2. Move virtual filesystems
mount --move /proc /mnt/root/proc
mount --move /sys /mnt/root/sys
mount --move /dev /mnt/root/dev

# 3. Switch root
exec switch_root /mnt/root /sbin/init
```

### How switch_root Works

1. **Deletes** all files in the initramfs (frees memory)
2. **chdir** to the new root
3. **chroot** to the new root
4. **exec** the init program

### Alternative: pivot_root

`pivot_root` is a lower-level syscall that `switch_root` wraps:

```c
#include <sys/syscall.h>
#include <unistd.h>

/* pivot_root(new_root, put_old) */
syscall(__NR_pivot_root, "/mnt/root", "/mnt/root/initramfs");
```

```bash
# Manual pivot_root
cd /mnt/root
mkdir -p .initramfs
pivot_root . .initramfs
exec chroot . /sbin/init
```

---

## Debugging Initramfs

### Extracting an Existing Initramfs

```bash
# Check the format
file /boot/initramfs-$(uname -r).img

# Extract (gzip-compressed cpio)
mkdir /tmp/initramfs
cd /tmp/initramfs
zcat /boot/initramfs-$(uname -r).img | cpio -idmv

# For xz-compressed
xzcat /boot/initramfs-$(uname -r).img | cpio -idmv

# For newer systems with unified kernel images
objcopy -O binary -j .initrd /boot/efi/EFI/Linux/linux.efi initramfs.cpio
```

### Adding Debug Shell

```bash
# In init script, add:
exec /bin/sh

# Or drop to shell on error
mount /dev/sda1 /mnt/root || {
    echo "Failed to mount root!"
    exec /bin/sh
}
```

### Breakpoints in dracut

```bash
# Boot with dracut breakpoints
# Add to kernel command line:
# rd.break=pre-mount rd.break=mount

# Available breakpoints:
# pre-udev, pre-trigger, pre-mount, mount, pre-pivot, pre-shutdown
```

### Verbose Boot

```bash
# Add to kernel command line:
# rd.shell rd.debug rd.log=console

# This shows:
# - All dracut actions
# - Shell on errors
# - Full debug logging
```

---

## Advanced Topics

### Custom Init Programs

initramfs doesn't have to run shell scripts. Any statically-linked binary can be `/init`:

```c
/* minimal_init.c */
#include <sys/mount.h>
#include <unistd.h>
#include <stdio.h>

int main(void)
{
    mount("proc", "/proc", "proc", 0, NULL);
    mount("sysfs", "/sys", "sysfs", 0, NULL);
    mount("devtmpfs", "/dev", "devtmpfs", 0, NULL);

    /* Load modules, unlock crypto, etc. */

    mount("/dev/sda1", "/mnt/root", "ext4", MS_RDONLY, NULL);

    chdir("/mnt/root");
    mount(".", "/", NULL, MS_MOVE, NULL);
    chroot(".");
    chdir("/");

    execl("/sbin/init", "init", NULL);
    return 1;
}
```

### Microcode Updates

CPU microcode must be loaded before any user code runs. The initramfs mechanism handles this:

```bash
# Intel microcode
cpio -idmv < /boot/intel-ucode.img

# AMD microcode
cpio -idmv < /boot/amd-ucode.img

# Concatenated with main initramfs
cat /boot/intel-ucode.img /boot/initramfs-$(uname -r).img > /tmp/combined.img
```

### Encrypted Root (LUKS)

```bash
#!/bin/sh
# init script for encrypted root

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev

modprobe dm-crypt
modprobe aes

# Prompt for passphrase
/lib/cryptsetup/askpass "Enter passphrase: " | \
    cryptsetup luksOpen /dev/sda1 cryptroot

mount /dev/mapper/cryptroot /mnt/root

exec switch_root /mnt/root /sbin/init
```

### Size Optimization

```bash
# Use busybox instead of individual binaries
# Use static linking
# Strip binaries
strip --strip-all initramfs/bin/*

# Use xz compression (best ratio)
find . | cpio -o -H newc | xz -9 --check=crc32 > initramfs.cpio.xz

# Remove unnecessary files
rm -rf initramfs/usr/share/locale
rm -rf initramfs/usr/share/man
```

---

## Further Reading

- [kernel.org: initramfs](https://www.kernel.org/doc/html/latest/filesystems/ramfs-rootfs-initramfs.html)
- [kernel.org: Early userspace support](https://www.kernel.org/doc/html/latest/driver-api/early-userspace/early_userspace_support.html)
- [dracut documentation](https://man7.org/linux/man-pages/man8/dracut.8.html)
- [initramfs-tools](https://man7.org/linux/man-pages/man8/initramfs-tools.8.html)
- [mkinitcpio](https://man.archlinux.org/man/mkinitcpio.8.en)
- [Arch Linux Wiki: mkinitcpio](https://wiki.archlinux.org/title/Mkinitcpio)
- [LWN: An introduction to initramfs](https://lwn.net/Articles/210235/)
- [gen_init_cpio source](https://elixir.bootlin.com/linux/latest/source/usr/gen_init_cpio.c)

> **Related topics:** [Boot Process](../kernel/boot-process.md), Kernel Command Line, Root Filesystem, [LUKS/dm-crypt](../kernel/drivers/dm-crypt.md)
