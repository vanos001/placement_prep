# Wayland — The Modern Linux Display Protocol

Wayland is a communication protocol between a display server (the *compositor*) and its clients, designed by Kristian Høgsberg in 2008 to replace the X.Org Server that had accreted 35 years of legacy. The core design choice is radical: every pixel a client wants on screen is produced by that client into a buffer the compositor can sample, and the compositor — never the client — performs the final composite and page-flip. There is no network-transparent rendering path, no global resource namespace, and no input grab hierarchy that an untrusted client can hijack.

## Why X Had to Go

The X11 protocol was specified in 1984–1987 for a world where the server owned the framebuffer and clients drew into it directly via Xlib calls (`XDrawLine`, `XFillRectangle`). Modern toolkits abandoned this model in the early 2000s — they render to client-side pixmaps using Cairo or Skia and only push the result via `MIT-SHM` or `XShm` shared-memory extensions. The result was that X11 carried two stacks: the legacy drawing API (still there, still taking IPC) and the modern composite path (Render + Composite + Damage extensions stacked on top). Every frame a compositing window manager produced went: client pixmap → X server → compositor reads back → compositor composites → compositor pushes back to X server → X server page-flips. Three copies, two round trips, every frame.

Worse, the security model was irreparable. Any X client could query and grab input from any other client via the core XInput grab primitives; the X server was a *global screen locker*. `xdotool` typing into another app's window, `xclip` reading the clipboard of every process, and screen-recording via `XGetImage` from the root window all "just worked" because the server had no concept of application isolation. This became untenable once we wanted sandboxed apps (Flatpak, browser tabs, compositing portals).

Wayland's answer: every client gets a private surface, the compositor arbitrates input and output, and no client can touch pixels or receive events it was not explicitly given.

## The Object Model

The Wayland protocol is an *object-oriented* binary protocol defined in XML files that `wayland-scanner` compiles into C headers and marshalling code. The wire format is 32-bit aligned, message header is `(object_id: u32, opcode: u16, length: u16)`, followed by arguments. There are no opcodes for connection setup — instead, every client connects to a Unix domain socket (`$WAYLAND_DISPLAY` or `/run/user/$UID/wayland-0`) and immediately receives object `1` of type `wl_display` as the registry.

Every object has an interface name, a version, and a set of requests (client → server) and events (server → client). The protocol is *bound* on demand: a client lists server globals via `wl_registry`, then issues `wl_registry.bind(name, interface, version, new_id)` for each one it wants. This lazy binding is how Wayland achieves extensibility — adding a new protocol like `wp_tearing_control_v1` does not touch old clients.

The core interfaces:

```text
wl_display ──── the connection: get_registry(), sync(), roundtrip
     │
wl_registry ─── global → "bind" → new object (interface@version)
     │
wl_compositor ─ wl_surface (one per window) ── wl_region (clip / opaque)
     │
wl_shm ─────── wl_buffer (CPU-shared mmap'd pool, XRGB8888 / C8 / etc.)
wl_drm ─────── wl_buffer (GPU GEM handle → dmabuf, hardware zero-copy)
zwp_linux_dmabuf_v1 ─ wl_buffer (modern explicit modifier-aware dmabuf)
     │
wl_seat ─────── wl_keyboard, wl_pointer, wl_touch (per-seat input devices)
     │
wl_output ───── monitor geometry, mode, scale (HiDPI factor)
     │
xdg_wm_base ─── xdg_surface → xdg_toplevel / xdg_popup (the shell)
```

A window on screen is `wl_surface` → `wl_buffer` → page-flipped. The surface holds the *role* (toplevel, popup, cursor), the buffer, the input region, the damage, and a `frame_callback` for vsync.

## Buffer Passing: The Zero-Copy Path

The defining feature of Wayland is that the client produces the buffer and the compositor consumes it — never the other way around. There are three production paths:

**1. `wl_shm` (CPU shared memory).** The client mmaps a shared tmpfs file, writes pixels with CPU rasterisation, and hands the resulting `wl_buffer` to the compositor with `wl_surface.attach`. Damage is communicated with `wl_surface.damage(buffer_x, buffer_y, w, h)`. The compositor copies this into its own GPU textures on every redraw. Used by, e.g., simple toolkits and screenshot pickers.

**2. `wl_drm` (legacy GPU).** The client allocates a GPU buffer through a private driver interface, gets a GEM (Graphics Execution Manager) name, and the compositor imports it directly. Limited — no format modifiers, no cross-driver.

**3. `zwp_linux_dmabuf_v1` (modern zero-copy).** This is the production path. The client allocates a `gbm_bo` via Mesa's GBM, exports it as a Linux dma-buf file descriptor (with a fourcc format like `DRM_FORMAT_ARGB8888`, plus *modifiers* describing the tiling/compression the driver chose — e.g. `I915_FORMAT_MOD_Y_TILED_CCS` for Intel CCS compression). The compositor imports the dma-buf as a GL/EGL `EGLImage` or Vulkan `VK_EXTERNAL_MEMORY_HANDLE_TYPE_DMA_BUF_BIT_EXT`, samples it as a texture, and composites with its own GPU command stream. Zero copy across the entire pipeline.

```text
   Client process                              Compositor process
   ┌──────────────────────┐                   ┌──────────────────────┐
   │  Renderer (GL/Vulkan)│                   │  Compositor GL/Vk    │
   │        │             │                   │        ▲             │
   │        ▼             │                   │        │             │
   │  GBM allocate        │                   │  EGLImage-from-dmabuf│
   │        │             │                   │        │             │
   │        ▼             │                   │        │             │
   │  dmabuf fd (w/modifier) ───── sendfd ────▶  import dmabuf fd   │
   │                      │   wl_surface.attach(buffer)             │
   │  wl_surface.damage() │                   │  glTexSubImage2D    │
   │  wl_surface.commit() │                   │  Composite + flip  │
   └──────────────────────┘                   └──────────────────────┘
                       │
                       ▼
                  KMS atomic flip (drmModeAtomicCommit)
```

The `wl_surface.commit` request is *the* synchronisation primitive. Until `commit`, all preceding `attach`/`damage`/`set_input_region` requests are queued; on `commit` the surface state is applied atomically and a frame is scheduled.

## Input: Seat and Devices

`wl_seat` aggregates keyboard, pointer, and touch for one "seat" (a set of devices a single user uses at one time). The client binds `wl_seat`, receives `wl_seat.capabilities`, and then `get_keyboard` / `get_pointer` / `get_touch` to obtain the specific device objects. This replaces X11's XI2 with something far simpler — there is no per-client device grab API, no passive grabs, no event masks. The compositor decides who has keyboard focus (the toplevel that is on top and clicked), and sends `wl_keyboard.keymap`, `wl_keyboard.enter`, and per-key events only to that client.

The keymap is communicated as an *xkbcommon* keymap string in `wl_keyboard.keymap(format: 1 /* xkb_v1 */, fd, size)`. The compositor writes a serialized `xkb_keymap` into a shared mmap'd file descriptor; the client parses it with `xkbcommon`. Scancodes (Linux input-event codes) are sent in `wl_keyboard.key`; the client translates to `xkb_keysym` and finally to text via the dead-key/compose machinery in `xkb_state`. This avoids the historical X11 problem of `Xkb` being a separate, broken, decades-old extension.

Pointer events come as `wl_pointer.motion`, `wl_pointer.button`, and `wl_pointer.axis` (scroll). There is no global pointer — the compositor only sends events to the surface under the cursor (or the one with pointer grab, set during drag operations via `wl_data_device.start_drag`). Touch events are `wl_touch.down`, `wl_touch.up`, `wl_touch.motion`, `wl_touch.frame` (batching marker).

## XDG Shell: Toplevels and Popups

`wl_surface` alone has no notion of "window". Roles are assigned by separate protocols. The production one is `xdg_wm_base`, which defines `xdg_surface` as a base, and `xdg_toplevel` (a normal window with title, min/max size, maximized/fullscreen state, and `configure` events describing what size to render at) and `xdg_popup` (menus, tooltips, positioned relative to a parent).

The configure / ack handshake is critical: the compositor sends `xdg_toplevel.configure(width, height, states)` and the client must `ack_configure(serial)` before committing a buffer of that size. This prevents the classic X11 race where the window manager resizes a window and the client renders the old size into the new frame, producing visual tearing or garbage.

```text
   Compositor                              Client
   ───────────                              ──────
   xdg_toplevel.configure(800, 600, [activated])
                              ────▶
                              render 800x600 buffer
                              ack_configure(serial) ────▶
                              wl_surface.attach(buf)
                              wl_surface.commit()    ────▶  flip
```

## XWayland

Legacy X11 applications cannot be ported instantly, so XWayland runs an X server as a Wayland client. The X server allocates its own `wl_surface` for each top-level X window and renders into it via the standard X composite path; the host compositor then composites that surface alongside native Wayland clients. The rootless mode (where each X top-level is a separate Wayland surface) is what every distribution uses today — `Xwayland -rootless` is the default in GNOME and KDE.

XWayland is a one-way compatibility shim: it does not give X11 apps network transparency, and they still cannot grab global input. But it does run unmodified: GTK3, Qt5, Motif, anything.

## Comparison with X11

| Property                | X11                                          | Wayland                                          |
|-------------------------|----------------------------------------------|--------------------------------------------------|
| Wire protocol           | X11 (XCB/Xlib), 200+ extensions              | Wayland (XML-scanned, ~50 protocols)            |
| Network transparency    | Yes (TCP/socket), barely usable               | No (only local Unix socket)                      |
| Compositing             | Optional, after-thought via Composite ext.   | Mandatory, central design                       |
| Input grabs            | Global, any client can grab anything          | Per-surface, compositor-mediated only            |
| Clipboard               | Global via `xclip` (any app reads)            | Per-seat, mediated by `wl_data_device`           |
| Screen recording        | Root window grab (`XGetImage`)               | Via `xdg-desktop-portal` ScreenCast (portal)    |
| Frame timing            | Ad-hoc (`Present` extension)                  | `wl_surface.frame` callback, vsync-tied          |
| HiDPI                   | Afterthought (`Xft.dpi` xrandr property)      | `wl_output.scale` + per-surface viewporter      |
| Tearing                 | Common, no compositor guarantee              | By design vsync; `wp_tearing_control_v1` opts in |
| Code size               | ~700 KLoC (xserver.git)                      | ~50 KLoC (libwayland) + compositor               |

## Compositors in Production

Wayland is *only* a protocol. The actual server is a separate program — Weston (reference), Mutter (GNOME), KWin (KDE Plasma), Sway (wlroots-based tiling), Hyprland (wlroots-based, animation-heavy), and gamescope (Valve's embedded compositor for Steam Deck and SteamVR). All share the same wire protocol; they differ in feature surface (HDR, tearing, color management), and in what they expose via extensions like `wp_viewporter`, `wp_fractional_scale_v1`, and `wp_alpha_modifier_v1`.

The `wlroots` library (used by Sway, Hyprland, cage, wayfire, and many more) is the closest thing Wayland has to a "reference compositor framework" — it implements the protocol,_seat/input handling, output management, and KMS backend in ~80 KLoC of C, so new compositors can focus on policy.

## Pitfalls and Real-World Notes

- **`wl_shm` format set is fixed**: ARGB8888, XRGB8888, C8, and a few RGB565. No fp16. For HDR you must use dmabuf.
- **Modifiers are mandatory for performance**: passing an `ARGB8888` linear dmabuf to Intel Gen12+ hardware forces a stall on the memory controller; passing `I915_FORMAT_MOD_Y_TILED_CCS` lets the sampler hit the L3 cache. Skipping `linux-dmabuf` modifier negotiation causes a silent 3–5× perf cliff.
- **`wl_display.sync` and `wl_display.roundtrip`** are different: `sync` queues a `wl_callback`, `roundtrip` blocks the calling thread until the server has processed the queue to that callback. Use `roundtrip` for one-shot setup; never inside a hot render loop.
- **`XDG_POPUP` positioning is non-negotiable**: the compositor validates every popup position; the client gets `xdg_popup.configure(x, y)`, not what it asked for. This breaks naive "show menu at (event_x, event_y)" code.

## References

- Wayland — official documentation and architecture overview — https://wayland.freedesktop.org/docs/html/
- The Wayland Book (Drew DeVault, Simon Ser) — comprehensive tutorial — https://wayland-book.com/
- `wayland-protocols` repository — XDG shell, dmabuf, viewporter XML — https://gitlab.freedesktop.org/wayland/wayland-protocols
- LWN: "Wayland: the future of Linux graphics" (2012) — https://lwn.net/Articles/424134/
- LWN: "Wayland and X" (2010, Jon Corbet) — https://lwn.net/Articles/413487/
- Kristian Høgsberg, "Wayland: an X replacement" (XDC 2008) — https://www.x.org/wiki/Events/XDC2008/Proceedings/
- `xkbcommon` documentation (keymap format) — https://xkbcommon.org/doc/current/
- `wlroots` library and design notes — https://gitlab.freedesktop.org/wlroots/wlroots
- Linux dma-buf synchronization and format modifiers — https://www.kernel.org/doc/html/latest/driver-api/dma-buf.html
