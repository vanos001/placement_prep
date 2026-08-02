# System Boot Process

## Overview

The boot process is the sequence of events that occurs from pressing the power button to having a fully operational operating system. Understanding boot is essential for system administration, troubleshooting, and OS interviews — it's where hardware and software meet.

## Motivation

When you press the power button, the CPU has no software running and no memory content. The boot process must:
1. Initialize hardware (CPU, memory, peripherals)
2. Find and load the bootloader
3. The bootloader loads the OS kernel
4. The kernel initializes the system and starts services
5. The system is ready for user login

Each stage must hand off control to the next in a reliable, well-defined manner.

## Boot Sequence Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Boot Sequence                              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  1. Power On → Hardware Initialization                │    │
│  │     POST (Power-On Self-Test)                         │    │
│  │     CPU starts at reset vector (0xFFFFFFF0 on x86)    │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  2. Firmware (BIOS/UEFI)                              │    │
│  │     Initialize hardware, find boot device             │    │
│  │     BIOS: MBR (first 512 bytes of disk)               │    │
│  │     UEFI: EFI System Partition (ESP)                  │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  3. Bootloader (GRUB)                                 │    │
│  │     Present boot menu, load kernel + initramfs        │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  4. Kernel Initialization                             │    │
│  │     Decompress, initialize subsystems, mount root fs  │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  5. Init System (systemd / SysVinit)                  │    │
│  │     Start services, reach target runlevel             │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  6. Login Prompt                                      │    │
│  │     Display manager or TTY login                      │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Topics in This Chapter

| Topic | Description |
|-------|-------------|
| [BIOS/UEFI](bios-uefi.md) | Firmware interfaces |
| [Bootloader](bootloader.md) | GRUB and boot loading |
| [Init Systems](init-systems.md) | systemd, SysVinit, OpenRC |

## Quick Revision

- **BIOS**: Legacy firmware, MBR boot, 16-bit real mode
- **UEFI**: Modern firmware, GPT/ESP boot, 32/64-bit
- **GRUB**: Most common Linux bootloader
- **Kernel**: Initializes hardware, mounts root filesystem
- **Init**: First user-space process (PID 1), starts all other services
- **systemd**: Modern init system (parallel startup, dependency management)

## Cross-References

- [BIOS/UEFI](bios-uefi.md) — Firmware deep dive
- [Bootloader](bootloader.md) — GRUB configuration and usage
- [Init Systems](init-systems.md) — systemd and alternatives


## Cross References

- [BIOS/UEFI](bios-uefi.md)
- [Bootloader](bootloader.md)
- [Init Systems](init-systems.md)
