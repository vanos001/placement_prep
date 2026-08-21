# PipeWire — The Modern Linux Multimedia Server

PipeWire is the user-space daemon that unifies audio playback, audio capture, video capture, and pro-audio low-latency work on Linux. It replaced PulseAudio as the default in Fedora 34 (2021), in Ubuntu 22.10, and in Debian 12. Its job: own the alsa-lib backend, expose a single graph of media-processing nodes (sinks, sources, filters, effects), and route streams between applications and hardware. It also implements a JACK-compatible low-latency API and a PulseAudio-compatible IPC shim, so unmodified Ardour, Firefox, OBS Studio, and PipeWire-Pulse all work.

This page covers the graph model, the SPA (Simple Plugin API), the session manager (WirePlumber), the PulseAudio and JACK compatibility layers, video stream support, and the design advantages over PulseAudio.

## The Architecture

PipeWire has a deliberately two-tier architecture:

```text
        ┌────────────────────────────────────────────────────┐
        │  Applications (Firefox, Chromium, OBS, Ardour,     │
        │  mpd, Kodi, Telegram, Bluetooth)                   │
        └───────┬───────────────┬───────────────┬────────────┘
                │               │               │
        Pulse IPC      JACK API         pipewire-alsa
                │               │               │
                ▼               ▼               ▼
        ┌────────────────────────────────────────────────────┐
        │            PipeWire Daemon (libpipewire)           │
        │  ┌────────────────────────────────────────────────┐ │
        │  │  Graph (nodes, ports, links)                   │ │
        │  │  Object registry (pw_registry)                 │ │
        │  │  Data loop (single-threaded, SCHED_FIFO)       │ │
        │  └────────────────────────────────────────────────┘ │
        │              │                                       │
        │              ▼                                       │
        │  ┌────────────────────────────────────────────────┐ │
        │  │  SPA (Simple Plugin API)                       │ │
        │  │  - alsa plugin     - video4linux2 plugin       │ │
        │  │  - audiomixer      - audioconvert              │ │
        │  │  - videonode       - bluez5                    │ │
        │  │  - aucat           - format converter          │ │
        │  └────────────────────────────────────────────────┘ │
        └────────────────────────────────────────────────────┘
                │
                ▼
       ┌──────────────────┐    ┌──────────────────┐
       │ WirePlumber      │    │ pipewire-media-  │
       │ (session mgr)    │    │   session (legacy)│
       └──────────────────┘    └──────────────────┘
                │
                ▼
       Kernel: ALSA, V4L2, BLEZ (BlueZ5), dma-buf
       /dev/snd/* /dev/video* /run/user/$UID/pipewire-0
```

Two levels matter:

- **PipeWire core** — owns the wire protocol, the graph data structures, and the *data loop*, a single POSIX RT thread (SCHED_FIFO at priority 65 by default, see `module-rt.c`) that runs every active node's `process()` callback. This is the path audio takes on every cycle.

- **Session manager** — a separate process (WirePlumber by default; `pipewire-media-session` was the reference, now deprecated). It is *policy*: which app's stream should connect to which output, what to do on a hotplug, default sink/source selection, Bluetooth route negotiation, node suspension on idle. The session manager is *not* on the data path — it sits alongside, issuing commands.

The split is the architectural answer to a decade of PulseAudio pain: PulseAudio mixed policy and mechanism in the same daemon, and could not be cleanly scripted. WirePlumber is scriptable in Lua (`~/.config/wireplumber/`) so site-specific behaviour (a 5.1 setup, a USB dock that needs custom EQ, a music-only Bluetooth headphone route) is achievable without recompiling.

## The Graph Model: Nodes, Ports, Links

PipeWire's data model mirrors a patch bay. Three object types:

- **Node** — a processing element with `process_in` and `process_out` callbacks. Examples: an ALSA sink (writes to hardware), an ALSA source (reads from hardware), a client stream (an application's audio output), a mixer, a convolver, a 3-band EQ. A node has `input` and `output` ports.
- **Port** — a directional endpoint on a node. A port has a *format* (sample rate, channels, sample format, layout, modifier, etc.) negotiated via the SPA format negotiation. Audio ports use SPA format `SPA_PARAM_TYPE` (`Buffers`), video ports use `VideoInfoRaw`.
- **Link** — a connection from an output port to an input port. Each link has one buffer (default 8192 bytes, often one half of a ping-pong). The link carries the negotiated format and a `FOLLOWER`/`DRIVER` flag — the *driver* is the clock master (usually the hardware sink), and the *follower* adapts its clock to the driver.

```text
   ┌─────────────┐ link  ┌─────────────┐ link  ┌──────────────┐
   │ Firefox     │──────▶│  audiomixer │──────▶│  ALSA sink   │── hardware
   │ node (out)  │       │  node       │       │ (driver)     │
   └─────────────┘       └─────────────┘       └──────────────┘
                              ▲
                              │ link
                              │
   ┌─────────────┐ link  ┌─────────────┐
   │ mpd node    │──────▶│  audio-     │
   │ (out)       │       │  convert    │ (resample, format convert)
   └─────────────┘       └─────────────┘
```

Graph topology is dynamic. Connecting a new Bluetooth headset inserts a new sink node, re-links the appropriate streams, and re-establishes format negotiation — all without stopping playback. The `pw-link` command and `wpctl` (WirePlumber CLI) are the tools.

The node `process()` callback chain forms a **pull** model: the driver (sink) calls its own `process_out`, which calls `pull` on its input links, which call `process_in` on the upstream nodes, recursively, until the leaf producers fire. This is the opposite of PulseAudio's push model and is the key to sub-millisecond latency.

## SPA — Simple Plugin API

SPA (Simple Plugin API) is PipeWire's in-process plugin layer. Every node's *mechanism* — the ALSA read/write loop, the resampler kernel, the Bluetooth SBC encoder, the audio mixer arithmetic — is implemented as an SPA plugin. SPA plugins are loaded as `*.so` files into the daemon's address space; there is no IPC overhead on the data path.

Key SPA interfaces:

- `spa_node` — the process/pull/push API (synchronous, called from data loop)
- `spa_buffer` — a buffer with metadata (timestamps, gap flags, video crop, format)
- `spa_format` — negotiated media format (audio PCM, video raw, etc.)
- `spa_pod` — the property container (a recursive, type-tagged, POD object)
- `spa_hook` — the event subscription mechanism (callbacks registered per-object)

The built-in SPA plugins are in `/usr/lib/spa-0.2/`:

```text
$ ls /usr/lib/spa-0.2/  (typical install)
alsa/
audioconvert/
audiomixer/
bluez5/
control/
support/
v4l2/
videotestsrc/
volume/
```

ALSA devices are wrapped by `spa_alsa_device` (a node). Bluetooth is `spa_bluez5_backend_*`. The audio resampler is `spa_plugin_audiotools` — based on the *speexdsp* resampler, extended with sinc-filter taps and quality levels 0–14 (default 4, pro audio 10+).

## WirePlumber — The Session Manager

WirePlumber (`wpd`), introduced in 2020 by George Kiagiadakis (Collabora), replaced the legacy `pipewire-media-session`. It is written in C with an embedded Lua 5.4 interpreter for policy.

The default config ships three Lua files in `/usr/share/wireplumber/`:
- `main.lua` — boot, log level, bluez state, default sink selection
- `policy.lua` — link policy (which streams go where), move-on-hotplug, default devices
- `suspend-node.lua` — idle timeout (suspends sinks after 5s of silence, lets Bluetooth sleep)

The session manager uses `WpPlugin` objects, each implementing a small bit of policy: `default-nodes` (record last selected sink), `device-rescan` (re-probe on hotplug), `policy-duck`, `access-portal` (allow XDG portal streams without elevated privilege).

Why Lua? Because policy needs to be tweakable per-user, per-device, per-application; compiling C for "I want mpd to follow my phone's Bluetooth A2DP route by default" was a non-starter.

## PulseAudio and JACK Compatibility

The two most widely-used audio APIs on Linux before PipeWire were PulseAudio (POSIX desktop audio) and JACK (pro audio, sub-5ms latency). PipeWire exposes both, on the same node graph, simultaneously.

**PulseAudio compatibility** — `pipewire-pulse` (`module-pulse-tunnel` forked) is a drop-in replacement for `pulseaudio --start`. It listens on `/run/user/$UID/pulse/native` (the standard PulseAudio socket) and translates every Pulse IPC message (`PULSE_MESSAGE_PLAYBACK_STREAM`, `RECORD_STREAM`, etc.) into PipeWire node creation. The PulseAudio client libraries (`libpulse.so`) are unchanged; users don't even need to relink applications.

```text
   Application (Firefox, mpv, KDE Plasma, ...)
       │  libpulse.so (unchanged)
       ▼
   /run/user/$UID/pulse/native  ────  pipewire-pulse
                                            │  translate
                                            ▼
                                       pipewire core
```

**JACK compatibility** — `pipewire-jack` ships a `libjack.so` that re-implements the JACK API in terms of PipeWire. Pro audio apps (Ardour, Bitwig, Carla, Guitarix) link against JACK and run unmodified against PipeWire. The classic JACK daemon (`jackd` or `jackdbus`) is not needed.

The PipeWire project's design choice — "be PulseAudio-compatible, be JACK-compatible, and own the data path" — was the single biggest factor in adoption. Distros could ship one daemon, applications didn't need rebuilds, and the pro audio community finally got a sane default with low latency.

## Video Stream Support and Portal Integration

PipeWire is not audio-only. The same graph model carries video streams, and the same IPC, the same session manager, and the same buffer-sharing facilities handle cameras, screen capture, and streaming pipelines.

The killer app is **xdg-desktop-portal ScreenCast**. When OBS Studio, Firefox, or Discord wants to share your screen on Wayland, it cannot grab the root window — Wayland forbids that. Instead:

```text
   App calls ScreenCast portal (xdg-desktop-portal)
            │
            ▼
   xdg-desktop-portal ──── asks compositor (Mutter/KWin/Sway)
            │  to enumerate outputs and windows
            ▼
   User picks one in the picker dialog
            │
            ▼
   Portal calls pipewire → creates a PipeWire node
   representing the chosen output/window
            │
            ▼
   App calls fd → pw_stream_new(fd)
   Connects to PipeWire node, receives frames
   as dma-buf buffers via wlr-screencopy
   or the compositor's dmabuf export
```

The video frames are dma-buf file descriptors. The compositor exports them, PipeWire passes them as opaque buffer pointers between nodes, and the consuming application (OBS) reads them via the EGL/Vulkan dmabuf import. Zero CPU copy from compositor to OBS encoder. This is the foundation for working screen share on every modern Wayland desktop.

Camera handling is similar: `pw-cli ls 2` (the Camera node) shows V4L2 devices as nodes; a WirePlumber policy auto-links the camera to the requesting application; Cheese, OBS, and browser-based video chats use `libcamera` or direct V4L2 nodes without copying pixels.

## Comparison with PulseAudio

| Aspect              | PulseAudio                              | PipeWire                                       |
|---------------------|-----------------------------------------|------------------------------------------------|
| Latency (typical)   | 30–60 ms (push, single thread per sink) | 5–15 ms (pull, RT thread, lock-free graph)     |
| Pro audio (JACK)    | Not compatible; need to bridge          | First-class, `libjack.so` is PipeWire           |
| Video               | Out of scope — no                       | First-class (camera, screen-cast, portals)    |
| Bluetooth           | A2DP only (no LDAC/aptX)                | A2DP/HFP/HSP + LDAC, APTX, AAC, opus in bt-x   |
| Buffer sharing     | memcpy between clients and daemon       | dma-buf pass-through (zero-copy where possible)|
| Hotplug policy      | Hardcoded C, limited config              | WirePlumber Lua scripts                        |
| Resampler            | speex, fixed 4-tap                      | speex + ffmpeg-derived, 0–14 quality levels    |
| API surface          | Native Pulse IPC                         | PipeWire IPC + Pulse + JACK shims              |
| Multi-channel        | Up to 32 (with caveats)                  | Up to 64 (clean), per-port format negotiation   |
| Code size           | ~250 KLoC                                | ~80 KLoC daemon + WirePlumber ~60 KLoC           |

The latency figure is dramatic: a PulseAudio daemon at 44.1 kHz with a 1024-sample buffer at default 5 fragments is `5 × 1024 / 44100 ≈ 116 ms` one-way — the reason pro audio folk shun it. PipeWire defaults to two fragments of 256 samples at 48 kHz → `2 × 256 / 48000 ≈ 10.7 ms` one-way, and at the recommended pro audio setting of `256 × 1` (no multi-buffering) you're at 5.3 ms total round-trip latency to the ALSA hardware buffer.

Bluetooth latency went from PulseAudio's 200–400 ms (resampling every step, no native codec) to PipeWire's 50–150 ms with native LDAC/aptX-HD decode in `spa_bluez5_codec_*` plugins, leveraging BlueZ's `a2dp-source` plugin.

## Real-World Tuning and Pitfalls

- **`PIPEWIRE_LATENCY=256/48000`** — set per-app to override the default quantum. OBS uses `PIPEWIRE_LATENCY=128/48000` for low-latency preview.
- **`PIPEWIRE_QUANTUM=256/48000`** — global default in `pipewire.conf`.
- **`pactl info`** still works — the PulseAudio shim responds; the `Server Name` line shows `PulseAudio (on PipeWire X.Y.Z)`.
- **`pw-top`** is the live data-path profiler (per-node CPU, quantum, errors). Use it.
- **`pw-cli dump short`** lists all nodes; `wpctl status` lists them in a friendly form with the default sink/source marked.
- **Bluetooth audio cutting in/out** is usually a misnegotiated codec: `bluez.properties` in WirePlumber config has `bluez5.codecs` (sbc, aac, ldac, aptx, aptx_hd, faststream). Disabling LDAC if your headphones don't negotiate correctly fixes most dropouts.
- **X11 apps on a Wayland session**: xdg-desktop-portal must be installed (`xdg-desktop-portal-gtk` or `-kde` or `-gnome`). If OBS can't see the screen, the portal is broken — not PipeWire.
- **`pipewire.service` restart drops all streams**: do NOT restart the daemon in production. Reload WirePlumber instead (`systemctl --user restart wireplumber`).

## References

- PipeWire — official documentation and architecture — https://docs.pipewire.org/
- PipeWire source and issues — https://gitlab.freedesktop.org/pipewire/pipewire
- WirePlumber — https://pipewire.pages.freedesktop.org/wireplumber/
- SPA (Simple Plugin API) — https://docs.pipewire.org/page/spa.html
- PipeWire wiki — https://gitlab.freedesktop.org/pipewire/pipewire/-/wikis/home
- LWN: "PipeWire: a media server to replace PulseAudio and JACK" (Jake Edge, 2017) — https://lwn.net/Articles/731117/
- LWN: "PipeWire 1.0 released" (2023) — https://lwn.net/Articles/950483/
- XDG Desktop Portal ScreenCast protocol — https://flatpak.github.io/xdg-desktop-portal/#gdbus-org.freedesktop.portal.ScreenCast
- BlueZ Audio API (a2dp, hfp) — https://bluez.pages.gitlab.freedesktop.org/bluez/
- PulseAudio IPC compatibility layer — https://docs.pipewire.org/page_module_protocol_pulse.html
