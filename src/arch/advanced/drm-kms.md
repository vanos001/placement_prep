# DRM/KMS — The Linux Direct Rendering Manager & Kernel Mode Setting

The Linux DRM (Direct Rendering Manager) subsystem is the kernel layer between userspace graphics stacks (Mesa, NVIDIA proprietary, ROCm) and the actual GPU hardware. It exposes two distinct services over the same character devices: an **ioctl-based rendering API** (command submission, memory allocation, sync) and a **KMS** (Kernel Mode Setting) API that owns mode configuration — the CRTC→encoder→connector→frame-buffer chain. KMS is what makes Linux boot to a graphical console without an X server, what makes `sway`/`gnome-shell` able to drive a display directly, and what makes the multi-monitor hotplug experience not be a 1987 nightmare.

## The DRI Devices

Every modern Linux GPU shows up under `/dev/dri/`:

```text
$ ls -l /dev/dri/
crw-rw---- 1 root render  226,   0 Sep 12 09:01 card0
crw-rw---- 1 root render  226, 128 Sep 12 09:01 renderD128
```

- **`/dev/dri/cardN`** — the "primary" node. Holds the *master* privilege. Opened by the compositor (Mutter, KWin, sway) to do KMS: enumerate connectors, set modes, perform atomic page-flips. Only one process at a time can be DRM master; that's enforced by `drmSetMaster()` / `drmDropMaster()`. Multiple compositors on a multi-GPU box each take a different `cardN`.
- **`/dev/dri/renderDN`** — the render node, with N = minor + 128. Has no mode-setting, no privileged operations. Can be opened by *any* user in the `render` group (or granted via ACL/seatd) without root. This is how Chromium sandboxed GPU processes, Steam game processes, FFmpeg encoding, and ML inference all access the GPU without escalation. The split was introduced in kernel 3.12 (2013) and is the foundation of per-app GPU sandboxing.

A machine with two GPUs gets `card0`/`renderD128` and `card1`/`renderD129`. PRIME lets one process allocate on `renderD128`, export the buffer via dma-buf, and import it on `card1` for scanout.

## The KMS Object Model

KMS exposes five types of objects, each with a property list. A "modeset" is the act of programming them so a frame buffer appears on screen.

```text
    ┌──────────────┐   plane   ┌──────────────┐              ┌──────────────┐
    │  framebuffer │──────────▶│     CRTC     │──────────────│   encoder    │
    │ (DMA-buf +   │ (primary  │  (timing    │  (TMDS/LVDS/ │ (HDMI/DSI/   │
    │  fmt+mod)    │  or cursor │   gen, scan │   eDP/eDP)    │  DP bridge) │
    └──────────────┘   sprite)  │   out, vbl) │              └──────────────┘
                              └──────┬───────┘                     │
                                     │                               ▼
                                     │                          ┌──────────────┐
                                     │                          │  connector   │
                                     │                          │ (HDMI-1, eDP,│
                                     │                          │  DisplayPort)│
                                     │                          └──────────────┘
                                     │
                              possible_clones, possible_crtcs
```

- **`framebuffer`** (`DRM_MODE_OBJECT_FB`, `fb_id`). Created from a dmabuf plus a pixel-format fourcc and tiling modifiers. The actual storage is a GPU buffer object; the framebuffer object is a small book-keeping wrapper that knows dimensions, format, and modifiers.

- **`plane`** (`DRM_MODE_OBJECT_PLANE`). A rectangular source crop into a framebuffer that gets composed onto a CRTC. Each CRTC has a *primary* plane (must cover the whole active area), zero or more *overlay* planes (sprites — for hardware video overlays), and an optional *cursor* plane (small, often 64×64, optimized for sub-frame mouse updates). Modern hardware (Intel Gen12+, AMD DCN) has 5–7 planes per pipe.

- **`CRTC`** (`DRM_MODE_OBJECT_CRTC`). The scan-out engine. Holds the active mode (`hdisplay`, `vdisplay`, `vrefresh`, sync polarities), the source rectangle from the primary plane, the framebuffer, and a vblank event source. There's one per display pipe. A CRTC can drive multiple connectors (mirroring) but a connector attaches to exactly one active CRTC.

- **`encoder`** (`DRM_MODE_OBJECT_ENCODER`). Bridges the CRTC's digital pixel stream to a connector's physical signalling. Some chips merge this with the connector (eDP panels), others have separate silicon (an external DP-to-HDMI bridge, e.g. ANX7816).

- **`connector`** (`DRM_MODE_OBJECT_CONNECTOR`). The physical port — HDMI-A-1, eDP-1, DisplayPort-1. Has a status (`connected`/`disconnected`/`unknown`), an EDID (parsed into mode list), a list of possible encoders, and properties like `Broadcast RGB`, `Colorspace`, `max bpc`.

Every object has **properties** (originally a flat prop list, now scoped as `DRM_MODE_PROP_ATOMIC`, `DRM_MODE_PROP_BLOB`). Examples: `"ACTIVE"`, `"mode_id"` (a blob), `"CRTC_ID"`, `"src_x"`, `"src_y"`, `"src_w"`, `"src_h"`, `"crtc_x"`, `"crtc_y"`, `"crtc_w"`, `"crtc_h"`, `"IN_FENCE_FD"`, `"OUT_FENCE_PTR"`. Blobs are typed binary lumps (mode info, gamma LUT, color-management matrices, HDR static metadata, EDID).

## Legacy vs Atomic API

The legacy API is the `drmModeSetCrtc` family — one ioctl per state change. This is fine for a single display and a software cursor, but it has two fatal flaws for modern desktops: you cannot apply a *single atomic update* across multiple CRTCs (e.g. setting primary + cursor + overlay on three monitors in the same vblank), and there's no way to TEST an update without committing it.

The atomic API (`DRM_IOCTL_MODE_ATOMIC` since kernel 4.0, 2015) takes a flat `struct drm_mode_atomic`:

```c
struct drm_mode_atomic {
    __u32 flags;            /* DRM_MODE_ATOMIC_TEST_ONLY | NONBLOCK | ALLOW_MODESET */
    __u32 count_objs;
    __u64 objs_ptr;         /* array of object IDs          */
    __u64 count_props_ptr;  /* array of prop counts         */
    __u64 props_ptr;        /* flat array of prop IDs       */
    __u64 prop_values_ptr;  /* flat array of u64 values     */
    __u32 reserved;
    __u64 user_data;        /* returned in vblank event      */
};
```

You set up three parallel arrays: object IDs (FB, plane, CRTC, connector), per-object prop ID list, and a flat 64-bit value list. The kernel validates them all atomically. If `DRM_MODE_ATOMIC_TEST_ONLY` is set, the kernel validates everything (memory availability, hardware limits, format compatibility, modifier support) and returns 0 or -errno *without applying*. If `DRM_MODE_ATOMIC_NONBLOCK` is set, an update that cannot be done without a modeset returns `EBUSY` immediately. If `ALLOW_MODESET` is missing, anything that would require reprogramming the PLL (changing resolution, pixel clock, or link) fails.

The atomic API is what makes modern Wayland compositors correct: every frame is one ioctl that either fully succeeds or fully fails, and the vblank event that acknowledges it carries back the `user_data` pointer Mutter uses to schedule the next `frame_callback`. Page-flips are atomic, vsync-tied, and testable in advance.

### Page Flip and Vblank

`drmModeAtomicCommit(NONBLOCK)` on a modeset-free update is the page flip — the CRTC's `FB_ID` is swapped, hardware double-buffers, and at the next vblank the new FB is latched and the old one becomes free. The kernel sends a `drm_event_vblank` to the file descriptor:

```text
  client commits             next vblank (~16.6ms later on 60Hz)
       │                              │
       ▼                              ▼
  drmModeAtomicCommit ──── wait ──── kernel emits DRM_EVENT_VBLANK
  (NONBLOCK)                          with user_data
       │                              │
       ▼                              ▼
  release old buffer <──── reads event from fd ◀── poll(POLLIN)
  schedule next render             next wl_surface.frame callback
```

This is the synchronisation heartbeat of every Wayland compositor — and modern X with `Present`.

## Prime / Dma-Buf for Buffer Sharing

PRIME is the umbrella name for DRM's dma-buf integration (kernel 3.4, 2012). The two relevant ioctls:

- `DRM_IOCTL_PRIME_HANDLE_TO_FD` — takes a GPU-internal `bo_handle` and returns a file descriptor backed by a `dma_buf` kernel object. Pass across processes, drivers, hardware. The receiver (or the compositor) calls `DRM_IOCTL_PRIME_FD_TO_HANDLE` to import it as a local `bo_handle`. Format and modifiers travel out-of-band via the user-space API (`gbm_bo_get_modifier`, EGL/Vulkan dmabuf extensions).

- The `dma-buf` itself supports `sync_file` fences (kernel 3.7, `DRM_IOCTL_SYNCOBJ_CREATE`). A sync file is a file descriptor that signals readiness when read access becomes coherent — explicit GPU-side synchronization between drivers without spin-waiting on CPU.

This is what enables:
- The Wayland `zwp_linux_dmabuf_v1` buffer path (client allocates on `renderD128`, exports as dmabuf, compositor imports on `card0` and scans out).
- PRIME offloading: discrete GPU renders, integrated GPU scans out (`DRI_PRIME=1`).
- VA-API decode producing a dmabuf → compositor zero-copy overlays it as a sprite plane → zero CPU copy throughout the decode→display path.

## Render Node vs KMS

Render-only processes (game, ML inference, encode pipeline) should never need to scan out — they should never be able to. The render node is the security boundary:

- It exposes only the renderer ioctls: `DRM_IOCTL_GEM_*`, `DRM_IOCTL_SYNCOBJ_*`, `DRM_IOCTL_MODE_CREATE_DUMB` for dumb buffers (CPU staging), but *not* `DRM_IOCTL_MODE_SETCRTC`, `DRM_IOCTL_MODE_ATOMIC`, etc. — those return `EINVAL`.
- It has no master privilege. Multiple processes can open the same `renderD128` simultaneously, the kernel arbitrates GPU scheduling between them.
- It does not see KMS objects at all (no connectors, no CRTCs). `drmModeGetResources()` returns 0 counts.

This is why a Flatpak sandbox can grant the GPU to its child without root — `--device=all` in the bubblewrap profile exposes `/dev/dri/renderD128` to the sandbox, and that's enough for hardware-accelerated WebGL.

## Comparison to fbdev

Pre-2000s, Linux graphics meant `fbdev` (`/dev/fb0`) — a single, dumb, mmap'd linear framebuffer. The kernel didn't know about resolutions, monitors, or hotplug; XFree86 did its own mode setting in user space by poking PLL and DAC registers directly. The fbdev API is essentially `ioctl(FBIOPAN_DISPLAY)` for double-buffering and `FBIO_WAITFORVSYNC`.

| Concern                | fbdev                                  | DRM/KMS                                          |
|------------------------|----------------------------------------|--------------------------------------------------|
| Driver model           | One framebuffer per device             | Many planes/CRTCs/connectors per device           |
| Mode setting           | Userspace, often broken, no hotplug    | Kernel-owned, hotplug via udev, EDID parsing      |
| Multi-monitor          | Effectively impossible                  | First-class; arbitrary CRTC→connector routing     |
| Hardware overlays      | None                                   | Sprite planes, cursor plane, hw video             |
| GPU rendering          | CPU-only mmap                          | ioctl-command-submission to GPU engines           |
| Buffer sharing         | None                                   | dma-buf, sync_file, modifier negotiation           |
| Permissions            | World-readable/writable by default     | Master vs render, CAP_SYS_ADMIN only for modeset |
| Atomicity             | Per-ioctl, racy                        | Testable, atomic, vsync-tied                      |

The fbdev compatibility layer (`DRM_IOCTL_MODESET_LEGACYFB` / `drm_fbdev_generic_setup`) exists purely so legacy kernels and early-boot userspace (syslinux replacements, plymouth, fbcon) can use the KMS frame buffer as if it were a dumb fbdev. It is a one-way shim: anything serious uses KMS directly.

## Atomic Properties of Interest

| Object    | Property                  | Meaning                                                |
|-----------|---------------------------|--------------------------------------------------------|
| Connector | `EDID`                    | parsed monitor descriptor (blob)                       |
| Connector | `Broadcast RGB`, `Colorspace`, `max bpc` | HDMI/DP colour control                   |
| Connector | `HDR_OUTPUT_METADATA`     | SMPTE ST.2086 + CTA-861.3 HDR static metadata blob    |
| CRTC      | `ACTIVE`, `mode_id`, `OUT_FENCE_PTR` | basic mode state + out-fence for nonblock   |
| CRTC      | `GAMMA_LUT`, `DEGAMMA_LUT`, `CTM` | colour management pipeline                  |
| Plane     | `IN_FENCE_FD`, `FB_ID`, `IN_FORMATS` | per-plane explicit modifier enumeration       |
| Plane     | `rotation`, `alpha`, `zposition` | hw rotation, per-plane alpha, z-order             |

The `IN_FORMATS` blob on a plane lists every `(format, [modifiers])` the plane can scan out. Compositors query it at init and pick the most efficient format the client and the plane both support — this is what tells Mutter that an `ARGB8888` dmabuf with `I915_FORMAT_MOD_Y_TILED_CCS` can be scanned out as a primary plane directly without GPU compositing.

## Real-World Notes

- **`drmModeAtomicCommit` with `NONBLOCK | ALLOW_MODESET` is racy**: a non-blocking modeset can return `EBUSY`; compositors should retry the same commit on next vblank.
- **Atomic test_only is the cheapest perf query on the system**: a 60Hz compositor might call it 60 times per second per plane to decide whether to use scanout or fall back to GPU composite.
- **Cursor plane quirks**: some hardware (older Intel, some AMD DCN) requires the cursor to be 64×64 ARGB8888 only, can't be scaled, and must be in VRAM — failure to honour this silently disables hardware cursors and falls back to software.
- **Hotplug events arrive via udev**, not via poll on the DRM fd: `/sys/class/drm/card0-HDMI-A-1/status` flips, udev emits a `change` event, the compositor's udev monitor thread re-probes connectors. There is no in-band KMS hotplug notification.

## References

- Linux DRM/KMS documentation — https://www.kernel.org/doc/html/latest/gpu/index.html
- DRM Mode Setting (KMS) — https://www.kernel.org/doc/html/latest/gpu/drm-kms.html
- DRM Memory Management & dma-buf — https://www.kernel.org/doc/html/latest/driver-api/dma-buf.html
- DRM Mode-Setting Helper Library — https://www.kernel.org/doc/html/latest/gpu/drm-kms-helper.html
- LWN: "DRM rendering and memory management" — https://lwn.net/Articles/283793/
- LWN: "Atomic mode setting design overview, part 1" (Daniel Vetter, 2014) — https://lwn.net/Articles/652878/
- LWN: "Atomic mode setting design overview, part 2" — https://lwn.net/Articles/652879/
- Direct Rendering Infrastructure (DRI) project — https://dri.freedesktop.org/wiki/
- `libdrm` source and documentation — https://gitlab.freedesktop.org/mesa/drm
- DRM atomic commit and sync objects — https://www.kernel.org/doc/html/latest/gpu/drm-uapi.html
