# Bootloaders: From Reset Vector to Kernel Entry

Every boot is a relay race across links that share almost nothing: 16-bit real mode, then flat 32/64-bit firmware code, then a freestanding loader, then the kernel's own entry protocol. Each handoff is defined by a *contract* -- a fixed address, a magic value, a struct the receiver reads -- and each link can only use the primitives the previous one left behind. This page owns that chain end to end. It complements the sibling pages: [Kernel Boot](../core/kernel-boot.md) continues from kernel entry to PID 1, the [OS-side bootloader page](../../../os/boot/bios-uefi.md) covers GRUB administration, and [Boot Process](../boot-process.md) is the user-visible story.

## 1. The chain at a glance

```text
        x86 boot chain: BIOS path (left) vs UEFI path (right)

 reset vector 0xFFFF_FFF0
        |
        v
 +--------------------+       +---------------------------------+
 | legacy BIOS        |       | UEFI firmware (spec 2.11, 2024) |
 | real mode, int 13h |       | DXE/BDS phases, 64-bit, GPT-    |
 | reads sector 0     |       | aware; Boot Manager runs        |
 +---------+----------+       +----------------+----------------+
           |                                   |
           v                                   v
 MBR LBA 0 -> 0x7C00                NVRAM Boot#### entry, fallback
 (446 usable bytes)                 \EFI\BOOT\BOOTX64.EFI on ESP
           |                                   |
           v                                   v
 boot.img -> diskboot.img ->        shimx64.EFI -> grubx64.EFI or
 core.img (gap or BIOS boot         systemd-bootx64.EFI (plain
 partition) -> grub.cfg             PE images, no sector staging)
           |                                   |
           +-----------------+-----------------+
                             v
        load bzImage + initrd + cmdline, fill boot_params,
        jump: setup entry (0x200) or code32_start with
        boot_params in %rsi (64-bit protocol)
                             |
                             v
        kernel: early setup -> ExitBootServices() if UEFI ->
        decompress -> start_kernel()   [see kernel-boot.md]
```

## 2. Layer 0: the reset vector

The CPU fetches its first instruction at physical `0xFFFF_FFF0` -- the top of the first 4 GiB, where chipset logic remaps the firmware flash. State is minimal: 16-bit real mode, interrupts off, A20 possibly still gated. On a UEFI Class 3 machine that first fetch lands straight in the firmware's own PEI/DXE code; on a legacy-BIOS machine it lands in the POST code that then scans the boot order and reads sector 0 of the chosen disk.

## 3. Layer 1: the firmware contract

The BIOS contract is tiny: load the 512-byte MBR (LBA 0) to `0x7C00` and jump to it in real mode. Anything more -- reading the rest of the loader, enumerating disks -- must go through BIOS interrupts, chiefly `int 13h`. The bootloader gets 440 bytes of code (the other 66 bytes are partition table and the `0x55AA` signature) and has to bootstrap the rest of itself.

The UEFI contract is a C ABI into a table of *boot services*: `LoadImage()`/`StartImage()` run PE32+ executables (the OS loader), and `AllocatePages()`, `GetMemoryMap()`, `OpenProtocol()` and friends remain callable until the loader calls `ExitBootServices()`, after which only runtime services survive (with the `SetVirtualAddressMap()` dance and heavy restrictions). The firmware Boot Manager picks an entry from the `Boot####` NVRAM variables or falls back to `\EFI\BOOT\BOOTX64.EFI` on the EFI System Partition. Note the polarity flip versus BIOS: on UEFI the *kernel itself* is often the OS loader (the EFI stub), not just a blob being loaded.

The Compatibility Support Module (CSM) that let UEFI firmware emulate a BIOS is being squeezed out: Intel directed client platforms to UEFI Class 3 (no CSM) from 2020, and Windows 11 requires UEFI plus Secure Boot, so on current hardware the legacy path on the left of the diagram is mostly a server/retro niche.

## 4. Layer 2: disk geometry -- MBR vs GPT

The partition layout is the bootloader's first data structure, and the two schemes differ sharply in what they let the loader assume.

| Layout | Addressing | Max usable, 512e | Max usable, 4Kn | BIOS boot? | UEFI boot? |
|--------|-----------|------------------|-----------------|------------|------------|
| MBR | 32-bit LBA + 16-bit count | 2 TiB | 16 TiB (arithmetic only) | yes | no |
| GPT | 64-bit LBA | 8 ZiB | 64 ZiB | only via BIOS boot partition | yes |

MBR sector 0 is 446 bytes of code, 64 bytes of partition table (4 entries x 16 bytes), and the `0x55AA` signature. GPT puts a *protective* MBR (partition type `0xEE`) in sector 0, the GPT header in LBA 1, and a 128-entry, 128-byte-per-entry partition array in LBA 2-33, mirrored at the end of the disk; the first usable LBA is therefore 34. Two type GUIDs matter for booting: the ESP (`C12A7328-F81F-11D2-BA4B-00A0C93EC93B`) and the BIOS boot partition (`21686148-6449-6E6F-744E-656564454649`) -- the latter's on-disk mixed-endian bytes spell `Hah!IdontNeedEFI`, which the worked model below verifies arithmetically. The practical boot ceiling for 512-byte-sector MBR disks is the classic 2 TiB line; 4Kn drives raise the arithmetic limit 8x but cannot be BIOS-booted in practice, so beyond 2 TiB it is GPT + UEFI regardless.

## 5. Layer 3: GRUB's staging problem

On BIOS, GRUB must fit a chain of ever-larger images into what the firmware allows it to touch (GRUB manual, "GRUB image files"):

1. `boot.img` -- 446 bytes in the MBR code area. It understands no filesystem; `grub-install` hardcodes a blocklist (first sector of `core.img`) into it.
2. `diskboot.img` -- the first sector of `core.img`; its only job is to read the rest of `core.img` using that blocklist and jump onward.
3. `core.img` -- an LZMA-compressed core with embedded modules (`biosdisk`, `part_gpt`, `ext2`, ...), enough to read real files.
4. Stage 2 -- `/boot/grub/`: `grub.cfg`, theme, and loadable `.mod` files, read through the filesystem drivers in `core.img`.

Where can `core.img` live? Either in the post-MBR gap, or -- on GPT -- in a dedicated BIOS boot partition. The old DOS default of starting the first partition at sector 63 leaves a 31.5 KiB gap that frequently no longer fits a modern `core.img`; the modern 1 MiB partition alignment leaves roughly 1007 KiB, which is the quiet reason `grub-install` stopped warning about embedding. On UEFI none of this exists: `grubx64.efi` is a plain PE file on the ESP, and shim (Section 9) precedes it.

## 6. Layer 4: boot managers vs loaders, and the BLS

It pays to separate *policy* from *mechanism*. A boot manager picks an entry (systemd-boot, rEFInd; GRUB is both manager and loader); an OS loader jumps to a kernel. The UEFI spec gives firmware the first hop (its Boot Manager chapter) and calls the OS-side pieces "UEFI OS Loaders". The [Boot Loader Specification](https://uapi-group.org/specifications/specs/boot_loader_specification/) standardizes the entries a manager reads: **Type #1** entries are text files in `\loader\entries\<id>.conf` with keys `title`, `linux`, `initrd`, `options`, `devicetree`; **Type #2** entries are Unified Kernel Images (UKIs) -- a single PE file built from systemd-stub plus kernel image, initrd, cmdline and os-release, dropped into `\EFI\Linux\`. UKIs matter beyond tidiness: they turn "verify the kernel, the initrd *and* the cmdline" into "verify one signed file", and they enable boot counting and A/B fallback for atomic-update systems.

## 7. Layer 5: the x86 handoff contract

A `bzImage` is the real-mode setup code followed by the protected-mode payload, and its first 4 KiB double as `struct boot_params` -- the "zeropage". The bootloader zeroes it, fills the writable `setup_header` fields (offsets from the [x86 boot protocol](https://docs.kernel.org/arch/x86/boot.html) doc), loads the pieces, and jumps:

| Offset | Field | Writer | Meaning |
|--------|-------|--------|---------|
| 0x1F1 | `setup_sects` | build | setup size in 512-byte sectors (0 means 4) |
| 0x210 | `type_of_loader` | bootloader | loader identity; 0xFF if unknown |
| 0x211 | `loadflags` | bootloader | bit 0 `LOADED_HIGH` = bzImage loads high |
| 0x214 | `code32_start` | both | 32-bit entry point, default 0x100000 |
| 0x218 | `ramdisk_image` | bootloader | initrd physical address |
| 0x228 | `cmd_line_ptr` | bootloader | where the command line string lives |
| 0x236 | `xloadflags` | build | bit 1 `XLF_CAN_BE_LOADED_ABOVE_4G`: kernel/boot_params/cmdline/initrd may sit above 4 GiB |
| 0x264 | `handover_offset` | build | EFI handover entry (the handover protocol is now documented as deprecated) |

Three entry modes exist. The 16-bit path jumps to offset 0x200 of the image (the setup code) with the header fields filled. The 32-bit path jumps to `code32_start` with flat segments, interrupts disabled, and `boot_params` in `%esi`. The 64-bit boot protocol (protocol 2.12+) passes `boot_params` in `%rsi` instead and, per `xloadflags`, allows everything to be placed above 4 GiB -- the mode modern 64-bit-only loaders use. Under UEFI the boot params come pre-filled from firmware, and the EFI handover protocol let the loader call the kernel at `handover_offset` with the EFI system table so the *kernel* calls `ExitBootServices()` itself; today's headline path is the EFI stub loading a signed UKI directly. From there the kernel's early setup consumes `boot_params`, decompresses the payload, and enters `start_kernel()` -- the handoff the [kernel boot page](../core/kernel-boot.md) picks up, with cmdline details in [cmdline-params](../cmdline-params.md).

## 8. Layer 6: the architecture split -- device tree vs ACPI

x86 hands off self-describing: the kernel finds ACPI tables (RSDP) via `boot_params` or the EFI configuration table and probes everything else. ARM64 and RISC-V invert this: the bootloader hands the kernel a flattened device tree blob (DTB) -- in `x0` on ARM64, in `a1` (with the boot hartid in `a0`) on RISC-V -- and the `/chosen` node inside it carries `bootargs`, `initrd-start`/`initrd-end` and `stdout-path`. That is why U-Boot patches `/chosen` before jumping and why a "wrong DTB" on an ARM board fails in ways no x86 user ever sees; the DT source of truth lives in the [device tree pages](../../embedded/device-tree.md) and the kernel-side view is in [device-tree drivers](../drivers/device-tree.md).

## 9. Layer 7: the trust chain

UEFI Secure Boot defines a key hierarchy in firmware: Platform Key (PK) -> Key Exchange Keys (KEK) -> the `db` allow list and `dbx` revocation list; PCR 7 in the TPM tracks changes to that state. Since almost no vendor will sign arbitrary loaders, distributions ship **shim**: a tiny first-stage loader signed by Microsoft's 3rd-party UEFI CA. Per its README, shim first tries the normal `LoadImage()`/`StartImage()` boot services, and if Secure Boot rejects the target, validates it against a built-in certificate before executing it -- which is how a distro-signed GRUB boots on any Secure Boot machine. Users add their own keys through the **Machine Owner Key (MOK)** mechanism: `mokutil` queues a key, MokManager (invoked by shim on the next boot) enrolls it in NVRAM, and shim trusts it alongside its embedded cert. GRUB's `shim_lock` verifier then checks kernel signatures, and the kernel's lockdown mode follows from the secure state. Measured boot is the orthogonal, *observing* half: firmware extends PCRs 0-7, GRUB extends PCR 8 with each command and PCR 9 with each file it reads (kernel, initrd), while systemd-boot/stub extend PCRs 11-13 (kernel/initrd, cmdline, extensions), all logged to the TPM event log. Verification details live in [secure-boot](../../security/secure-boot.md), TPM mechanics in [tpm](../security/tpm.md).

## 10. The embedded variant: U-Boot and the network path

Embedded SoCs repeat the whole staging game inside the chip. The mask-ROM BootROM loads a TPL ("tertiary" loader, when SRAM is too small even for DRAM init), which brings up enough to load the SPL -- the U-Boot xPL docs describe the SPL as the component that "sets up SDRAM and loads U-Boot proper" -- which then loads U-Boot proper from eMMC/NAND/SPI. U-Boot proper boots the kernel from a FIT image (kernel + DTB + initrd in one, optionally signature-verified) via `booti`/`bootm`, and its standard-boot (`bootstd`) framework automates scanning for distro-style boot media. Because U-Boot also implements UEFI boot services, GRUB and systemd-boot run on ARM boards too. The network path replaces the disk: PXE is DHCP plus TFTP, and [iPXE](https://ipxe.org/) extends it with HTTP fetching, scripting and `sanboot`, chaining into UEFI HTTP Boot -- the standard way clusters and clouds provision bare metal. Board-level detail is in [U-Boot](../../embedded/uboot.md).

## 11. Where the chain breaks (interview angles)

- `grub-install` fails with "embedding is not possible": no post-MBR gap, no BIOS boot partition, or the partition starts at sector 63 -- the Layer 2/3 geometry bite.
- Another installer writes 512 bytes of its own MBR: `boot.img`'s hardcoded blocklist now points at garbage; repair via live USB + `grub-install`.
- Disk moved from one controller to another: NVRAM `Boot####` entries reference stale device paths; UEFI falls back to `\EFI\BOOT\BOOTX64.EFI` if present.
- Secure Boot enabled with a self-built kernel: shim refuses; enroll a MOK or build a signed UKI (Layer 7).
- 4 Kn drive with an MBR layout: boots nothing -- the 16 TiB arithmetic limit in the table above is unreachable because firmware never BIOS-boots 4 Kn.
- `ExitBootServices()` called twice or memory map used after it: classic early-boot crash; the kernel must `GetMemoryMap()` again after the first failed attempt.

## 12. Worked model: sector math and stage placement

The demo below is a **model** -- it computes on-disk geometry from protocol constants (MBR anatomy, GPT entry array, GRUB blocklists); it does not parse or emulate a disk. It answers the "max bootable disk" question for 512e vs 4Kn drives, lays out GRUB's stages on a 1 MiB-aligned GPT disk, and decodes the BIOS boot partition GUID.

```python
#!/usr/bin/env python3
"""Disk-layout math behind the boot chain.

A MODEL of on-disk structures (MBR/GPT geometry, GRUB stage placement)
computed from protocol constants -- it does not parse or emulate a disk.
"""

SECTORS = (512, 4096)          # logical sector sizes: 512e vs native 4Kn
GRUB_CORE_SECTORS = 90         # typical core.img, ~45 KiB (varies by build)


def fmt(n):
    """Render a byte count in the largest binary unit that is >= 1."""
    for unit, exp in (("ZiB", 70), ("EiB", 60), ("PiB", 50), ("TiB", 40),
                      ("GiB", 30), ("MiB", 20), ("KiB", 10)):
        if n >= 1 << exp:
            return f"{n / (1 << exp):g} {unit}"
    return f"{n} B"


def part1():
    print("== Part 1: max usable capacity (addressing limits) ==")
    print(f"{'layout':<7}{'LBA field':>10}{'512e (512 B)':>15}{'4Kn (4096 B)':>15}")
    for name, bits in (("MBR", 32), ("GPT", 64)):
        cells = [fmt((1 << bits) * s) for s in SECTORS]
        print(f"{name:<7}{bits:>10}{cells[0]:>15}{cells[1]:>15}")
    print(f"LBA48 interface cap, 512 B sectors: {fmt((1 << 48) * 512)}")


def part2():
    print()
    print("== Part 2: GRUB stage layout model (GPT disk, 512 B sectors) ==")
    p_entry = 128 * 128                       # entry array: 128 x 128 B
    regions = [
        ("protective MBR (LBA 0)", 0, 1),
        ("primary GPT header (LBA 1)", 1, 1),
        ("partition entry array", 2, p_entry // 512),
        ("unallocated post-GPT gap", 34, 2048 - 34),
        ("BIOS boot partition (1 MiB)", 2048, 2048),
    ]
    for name, start, n in regions:
        print(f"{name:<30} LBA {start:>5}..{start + n - 1:<5} {n * 512:>8} B")
    core = GRUB_CORE_SECTORS * 512
    print(f"first usable LBA: {2 + p_entry // 512}; "
          f"core.img model: {core} B -> fits BIOS boot partition: "
          f"{core <= 2048 * 512}")


def part3():
    print()
    print("== Part 3: sector-0 anatomy and the BIOS boot GUID ==")
    print("MBR sector: 446 B code | 64 B partition table (4 x 16 B) | 0x55AA")
    g = "21686148-6449-6E6F-744E-656564454649"
    f = [bytes.fromhex(x) for x in g.split("-")]
    raw = f[0][::-1] + f[1][::-1] + f[2][::-1] + f[3] + f[4]
    print(f"BIOS boot GUID {g}")
    print(f"on-disk (mixed-endian) bytes spell: {raw.decode('latin-1')!r}")


part1()
part2()
part3()
```

Output (real run, byte-identical across reruns):

```text
== Part 1: max usable capacity (addressing limits) ==
layout  LBA field   512e (512 B)   4Kn (4096 B)
MBR            32          2 TiB         16 TiB
GPT            64          8 ZiB         64 ZiB
LBA48 interface cap, 512 B sectors: 128 PiB

== Part 2: GRUB stage layout model (GPT disk, 512 B sectors) ==
protective MBR (LBA 0)         LBA     0..0          512 B
primary GPT header (LBA 1)     LBA     1..1          512 B
partition entry array          LBA     2..33       16384 B
unallocated post-GPT gap       LBA    34..2047   1031168 B
BIOS boot partition (1 MiB)    LBA  2048..4095   1048576 B
first usable LBA: 34; core.img model: 46080 B -> fits BIOS boot partition: True

== Part 3: sector-0 anatomy and the BIOS boot GUID ==
MBR sector: 446 B code | 64 B partition table (4 x 16 B) | 0x55AA
BIOS boot GUID 21686148-6449-6E6F-744E-656564454649
on-disk (mixed-endian) bytes spell: 'Hah!IdontNeedEFI'
```

Read it interview-first: MBR's 32-bit sector fields are why the 2 TiB boot limit exists, GPT's 64-bit fields are why it "goes away" (interface limits like LBA48's 128 PiB then dominate), and the 1 MiB-aligned layout exists so `core.img` always has room -- whether in the gap or in the `Hah!IdontNeedEFI` partition.

## References

- x86 Boot Protocol, kernel documentation -- field offsets and entry modes verified against the live page: https://docs.kernel.org/arch/x86/boot.html
- UEFI Specification 2.11 (December 2024), HTML edition: https://uefi.org/specs/UEFI/2.11/ (landing page: https://uefi.org/specifications -- both reject curl with 403; verified via search index)
- GNU GRUB Manual 2.14, "GRUB image files" and "Embedded blocklists"/"BIOS Boot Partition" sections: https://www.gnu.org/software/grub/manual/grub/ (gnu.org unreachable from this sandbox; content verified through the GNU Guix mirror: https://doc.guix.gnu.org/grub/latest/en/grub.html)
- Boot Loader Specification (UAPI group, successor of the systemd.io page): https://uapi-group.org/specifications/specs/boot_loader_specification/
- Linux TPM PCR Registry (UAPI group) -- GRUB PCRs 8/9, systemd PCRs 11-13: https://uapi-group.org/specifications/specs/linux_tpm_pcr_registry/
- U-Boot documentation: xPL/SPL framework and Standard Boot: https://docs.u-boot.org/en/latest/develop/spl.html and https://docs.u-boot.org/en/latest/develop/bootstd/overview.html
- shim, first-stage UEFI bootloader (rhboot) -- README describing LoadImage/StartImage plus built-in-certificate fallback: https://github.com/rhboot/shim
- Rod Smith, "Managing EFI Boot Loaders for Linux: Dealing with Secure Boot" (MOK definitions; page renders only for browsers): https://www.rodsbooks.com/efi-bootloaders/secureboot.html
- iPXE -- open source network boot firmware (PXE/HTTP chain loading): https://ipxe.org/
- Windows 11 requirements (UEFI + Secure Boot mandate): https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements
