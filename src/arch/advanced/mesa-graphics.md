# Mesa 3D — The Open-Source OpenGL & Vulkan Implementation

Mesa is the open-source implementation of every graphics API on Linux: OpenGL (1.x–4.6), OpenGL ES (1–3.2), Vulkan (1.3+), OpenCL, OpenVG, and the Gallium3D "state tracker" framework that front-ends all of these onto a single per-driver backend. When you run `glxgears` or `vkcube` on an Intel iGPU, an AMD GPU, an ARM Mali, or a Qualcomm Adreno — all four of those drivers are Mesa. When you install `mesa-vulkan-drivers` on Debian, you get RADV (AMD), ANV (Intel), Turnip (Adreno), lavapipe (software) and venus (virtio-gpu passthrough) — all from the same source tree.

This page covers the Mesa architecture: state trackers, Gallium3D driver model, NIR (the new IR), Vulkan's different structure, the shader compiler stack, and the WSI (Window System Integration) layer.

## The High-Level Stack

```text
       Application (SDL, Qt, GTK, game engines, Blender, browsers)
            │
            │  libGL.so / libEGL.so / libvulkan.so   (loader)
            ▼
       ┌─────────────────────────────────────────────────────────────┐
       │                          Mesa                              │
       │                                                            │
       │   OpenGL state tracker    Vulkan runtime (radv, anv, ...)  │
       │   (mesa main + GLSL → NIR)  (vk pipeline, CmdBuffer, ...)  │
       │            │                          │                    │
       │            ▼                          ▼                    │
       │   ┌─────────────────────────────────────────┐              │
       │   │  NIR (NIR Intermediate Representation)   │              │
       │   │   SSA, passes, lowering, optimisation   │              │
       │   └─────────────────────────────────────────┘              │
       │            │                                               │
       │            ▼                                               │
       │   per-driver backend codegen → hardware ISA                │
       │   (i965 → Gen ASM; radeonsi → GCN/RDNA; ir3 → Adreno)     │
       │            │                                               │
       │            ▼                                               │
       │   winsys (DRM ioctl + buffer manager)                      │
       │   (e.g. iris winsys = iris, amdgpu winsys = radeonsi)     │
       └────────────────────────────────────────────────────────────┘
            │
            ▼
       /dev/dri/renderD128  +  /dev/dri/card0  (for KMS-flip)
       Linux kernel DRM subsystem (i915, amdgpu, nouveau, msm, panfrost, ...)
```

A typical `libGL.so.1` shipped by your distro is just a thin shim — the loader shim — that uses `libglvnd` (the vendor-neutral GL dispatch library) to find the real per-vendor implementation. For Intel/AMD open-source stacks, that resolves to `libGLX_mesa.so.0` which is built from Mesa and dispatches into the per-driver backend.

## State Trackers → Drivers → Winsys

This is the Gallium3D separation of concerns, designed by Keith Whitwell and Zack Rusin around 2008–2009. The idea: write the OpenGL/Vega/OMX state tracking once, write the per-hardware driver once, and the winsys layer provides the DMA-buf/DRM glue that lets the same driver binary work on different windowing environments (X, Wayland, headless, Android).

- **State tracker** — a front-end implementation of one API (e.g., `src/mesa/state_tracker/st_glsl_to_nir.cpp`). It does state validation, command list construction, and translates API state into pipe state. Most state trackers have collapsed over the years (Gallium3D/OpenVG, Gallium3D/OMX video decode); today only `st/mesa` (the OpenGL state tracker) is a major one.

- **Driver** — the per-hardware backend implementing the Gallium3D `pipe_context` interface: `set_framebuffer_state`, `bind_rasterizer_state`, `bind_vs_shader`, `bind_sampler_states`, `resource_copy_region`, `clear`, `flush`, `draw_vbo`. There are roughly eight in production: `i915` (legacy Intel Gen2–4), `iris` (modern Intel Gen8+), `radeonsi` (AMD GCN+), `crocus` (Intel Gen4–7), `nouveau` (NVIDIA), `panfrost` (Mali), `lima` (Mali Utgard), `asahi` (Apple M1).

- **Winsys** — the low-level OS interface: how to allocate buffers, talk to the DRM driver, import dma-buf, etc. Examples: `iris_drm_winsys`, `amdgpu_winsys`. The winsys is wrapped by the per-driver `pipe_screen` for memory allocation.

## Mesa Classic vs Gallium

Mesa has two coexisting OpenGL architectures:

**Mesa classic (`src/mesa/drivers/dri/`)** — the pre-Gallium path where each driver had its own `brw_context` (i965) or `radeon_context` structure, its own GL state copy, and its own glsl IR (`IR`). All OpenGL state changes hit a `gen*` file. `i965` was the last surviving classic driver, and was replaced by `iris` in Mesa 19.1 (2019) for Gen8+ hardware. The classic architecture's chief problem: every driver reimplemented buffer management, samplers, and state tracking.

**Gallium (`src/gallium/`)** — state tracker + pipe context. New drivers are pure Gallium (`iris`, `radeonsi`, `panfrost`). The OpenGL state tracker (`st/mesa`) does the API work, the driver just implements the pipe interface. State tracking is shared; new drivers get OpenGL, OpenCL, etc., "for free" once they implement pipe.

```text
       ┌──────────────────┐
       │  Application GL  │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │   st/mesa        │   ←── single GL state tracker (Gallium3D)
       │  GLSL → NIR      │       shared by iris, radeonsi, panfrost...
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │   pipe_context   │   ←── per-driver backend
       │  (iris_context)  │
       └────────┬─────────┘
                │
                ▼
       ┌──────────────────┐
       │  i915 winsys     │   ←── DRM ioctl wrapper
       └────────┬─────────┘
                │
                ▼
          /dev/dri/renderD128
```

## NIR — The Intermediate Representation

NIR (NIR IR, "Near IR" or "New IR") was introduced by Connor Abbott in 2014–2015 and replaced GLSL IR (`IR`) as the shared optimisation layer. Every modern Mesa driver — Vulkan or Gallium — uses NIR as the front-end representation of every shader.

NIR is SSA-based, typed by `nir_alu_type` (uint/int/float/bool, with bit sizes 1/8/16/32/64), and supports 1D/2D/3D/4D vectors like LLVM IR. Key properties:

- **SSA form** for values, with registers for non-SSA temporaries (used during register allocation by back-ends).
- **Pass-based** architecture: each optimisation is a single pass with explicit in/out contracts. There are 60+ passes — constant folding, algebraic simplification, dead code, copy propagation, loop unrolling, vectorise, lower_int64, lower_pack, lower_subgroup, lower_fma, opt_if, lower_locals_regs, etc.
- **Lowering** — when a backend doesn't natively support an op (e.g., `fmod`, `dot4`, `imageAtomicAdd` with a 64-bit pixel), a lowering pass rewrites it into ops the hardware does support. Each driver registers its lowerings via `nir_shader_compiler_options`.

```text
   GLSL source
        │
        ▼
   ┌──────────────┐
   │ _mesa_glsl_  │   glsl compiler (front-end, AST → IR)
   │   compile_   │
   │   shader()   │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  glsl_to_nir │   convert legacy IR to NIR (preserves types)
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │     NIR      │   shared shader representation
   │   passes     │   (algebraic, inlining, vectorise, ...)
   └──────┬───────┘
          │
          ▼   ── per-driver backend codegen ──
          │
   ┌──────┴───────┐  ┌─────────────────┐  ┌──────────────────┐
   │  brw_eu.cpp  │  │  ac_nir_to_llvm │  │  ir3_nir_to_..   │
   │  (i965/iris) │  │  → LLVM IR →    │  │  → Adreno ISA    │
   │  → Gen ASM   │  │  AMDGPU codegen │  │  (Turnip, Freedreno)│
   └──────────────┘  └─────────────────┘  └──────────────────┘
```

NIR is also the integration point for SPIR-V — Vulkan shaders are SPIR-V binaries, and `vtn/spirv_to_nir.cpp` translates them. NIR can round-trip a SPIR-V shader to GLSL via `nir_to_glsl` (used for shader caches, decompilers).

## The Vulkan Implementation

Vulkan Mesa is structurally different from the OpenGL path: it does not use the Gallium3D state tracker. Vulkan is so low-level that there is nothing for a state tracker to track — the application manages pipelines, command buffers, descriptor sets, fences, and the driver just records hardware commands. Each Vulkan driver is therefore a self-contained implementation that shares NIR, shared Mesa utilities (`u_printf`, `util_pack`, `ralloc`, etc.), and the WSI layer.

| Driver | Hardware             | Status                                       |
|--------|---------------------|----------------------------------------------|
| RADV   | AMD GCN 1.0 → RDNA3  | Primary AMD driver, ships in Debian/Ubuntu    |
| ANV    | Intel Gen8 → Xe HPG  | Primary Intel driver (replaces Beignet)       |
| Turnip | Qualcomm Adreno 6xx/7xx | Reverse-engineered, freedreno-derived    |
| v3dv   | Broadcom V3D 7.x (Pi 4) | Fully featured ( conformant on Pi 4)     |
| pvr    | Imagination PowerVR  | New, still maturing                           |
| panvk  | Mali Bifrost/Valhall | New, maturing                                 |
| lavapipe | software (llvmpipe) | CPU Vulkan 1.3 implementation (slow but correct) |
| venus  | virtio-gpu passthrough | Guest sees a host Vulkan instance         |

A Vulkan "driver" inside Mesa is roughly 60 KLoC. RADV is ~80 KLoC (with Navi-3x raytracing), ANV ~70 KLoC. They use the same NIR shaders, the same pipeline cache serialisation, and largely the same descriptor set layout logic. Ray tracing (RT) has its own ABI in the Vulkan extension — RADV implemented it via an LLVM shader on a separate "compute-like" engine.

The shader compiler path differs per driver. RADV uses **ACO** ("Amd Compiler Object", written in C++, hand-rolled, deliberately bypassing LLVM for compute shaders) as its primary backend for GFX9+; for ray tracing and some edge cases it still falls back to `ac_nir_to_llvm`. ACO was added by Daniel Schürmann and Timur Kristóf in 2019 and gives RADV dramatically lower shader compile times than the LLVM backend (typical: 5× faster GLSL compile).

ANV uses `brw_nir` (Intel's NIR → Gen ISA backend, shared with the OpenGL `iris` driver), and Intel maintains a hand-written instruction scheduler and register allocator.

Turnip and Freedreno share `ir3_nir_to_ir3`, but Turnip's shader packer is simpler.

## Shader Cache

Mesa maintains a per-driver on-disk shader cache (`$XDG_CACHE_HOME/mesa_shader_cache/`) keyed on the (pipeline-state-hash + driver-version). A cache hit skips the entire compile pipeline. For Steam Proton, the cache is also shipped with games (shader pre-warming). The cache format is per-driver, and `_mesa_shader_cache_write` uses a serialized blob of the post-NIR (or pre-codegen) state.

## WSI (Window System Integration)

Vulkan's `VK_KHR_*_swapchain` family is implemented per-platform inside Mesa's `src/vulkan/wsi/`. On Linux this is `wsi_common_drm.c` (used by RADV/ANV/Turnip/panvk) and `wsi_common_x11.c` / `wsi_common_wayland.c`.

```text
   Application calls vkCreateSwapchainKHR()
             │
             ▼
   wsi_common_wsi.c   ──── picks the backend (Wayland/X11/drm headless)
             │
             ▼
   wsi_common_wayland.c  ──── uses zwp_linux_dmabuf_v1 to get a dmabuf
             │                    from the compositor
             ▼
   Creates VkImage backed by that dma-buf fd
   (VK_IMAGE_TILING_DRM_FORMAT_MODIFIER_EXT)
             │
             ▼
   vkQueuePresentKHR  ──── wl_surface.attach + wl_surface.commit
                          + roundtrip on presentation engine
```

For Wayland, the application never allocates the buffer — the compositor suggests formats and modifiers, and the WSI layer picks one that the GPU driver supports. This is how HiDPI, fractional scaling, HDR (if the compositor supports it), and explicit modifier negotiation all work without application code.

## Comparison to Proprietary Drivers

| Aspect             | Mesa (open)                                | NVIDIA proprietary                       | AMD proprietary (amdgpu-pro)         |
|--------------------|--------------------------------------------|-----------------------------------------|--------------------------------------|
| OpenGL on Linux     | `iris`, `radeonsi` (Gallium3D)             | `libGL.so.1` (legacy GL in driver)     | `amdgpu-pro-core` (DGX variant)     |
| Vulkan              | RADV / ANV (in-tree Mesa)                  | Driver's `libvulkan_radeon.so`/`nvidia` | "amdgpu-pro" overlay, often Proton   |
| Shader compiler     | NIR + ACO (RADV) / brw_nir (ANV)           | Proprietary compiler (single source)    | LLVM-derived "SC2"                  |
| Shipped kernel mod  | Already in `linux` (i915, amdgpu, nouveau)| Out-of-tree `nvidia.ko` + DKMS         | Optional `amdgpu-pro-dkms` overlay  |
| Wayland support     | First-class, Mutter/KWin/Sway default      | Added 2022+ (NV 510+)                  | Same as radeonsi for Vulkan          |
| GBM & EGL           | Standard `gbm`, `egl`                      | External NV EGL/GBM shim, EGLOutput    | Bundled `libgl` overrides Mesa      |
| Code visibility     | GitLab, code review, `mesa-dev` mailing    | Closed source, public symbols only     | Closed-source user-space             |

NVIDIA's proprietary driver took until 2022 to ship a KMS-capable Linux driver (`nvidia-drm modeset=1`), and only in 525+ did it ship a Wayland-acceptable GBM backend (`nvidia-drm` was KMS master, and `libnvidia-egl-wayland` was the compositor-facing shim). The experience gap remains: GBM modifier enumeration, sync files, and explicit sync all trail Mesa's implementations. NVIDIA's open GPU kernel modules (`open-gpu-kernel-modules`, 2022+) opened the kernel side only; user-space remains closed.

## Real-World Tuning and Pitfalls

- **`MESA_LOADER_DRIVER_OVERRIDE=iris,zink`** forces a specific driver; useful for testing `zink` (OpenGL-over-Vulkan) on NVIDIA.
- **`RADV_PERFTEST=...`** toggles ACO features. `RADV_PERFTEST=nocswave32`, `drc` change compute subgroup modes — sometimes 30% perf.
- **`MESA_GLSL=cache_disable=true`** — for benchmarking compile times without cache hits.
- **`vkcube --gpu N`** — switch driver instance on multi-GPU systems.
- **Stale shader cache after Mesa upgrade**: the on-disk cache is keyed on driver version, so a Mesa update invalidates everything, and the first launch of any game looks like it has frozen. Use `rm -rf $XDG_CACHE_HOME/mesa_shader_cache*` to clear it deliberately.
- **`ZINK_DESCRIPTORS=lazy`** is now default — the older `lazy` mode that always allocates full descriptor sets can leak memory under dynamic workloads.
- **llvmpipe vs softpipe**: llvmpipe is the JIT'd software rasteriser (LLVM-targeted); softpipe is the older C-only software rasteriser. For CI: use `GALLIUM_DRIVER=llvmpipe`, it's 3–10× faster than softpipe.

## References

- Mesa 3D documentation — https://docs.mesa3d.org/
- Mesa source and CI — https://gitlab.freedesktop.org/mesa/mesa
- NIR (NIR IR) — https://docs.mesa3d.org/nir/index.html
- Gallium3D — https://docs.mesa3d.org/gallium/index.html
- Vulkan drivers in Mesa (RADV/ANV/Turnip) — https://docs.mesa3d.org/vulkan/index.html
- ACO compiler for RADV — https://gitlab.freedesktop.org/mesa/mesa/-/tree/main/src/amd/compiler
- LWN: "A look at the open NVIDIA driver" (Jonathan Corbet, 2022) — https://lwn.net/Articles/892642/
- LWN: "Gallium3D: a new architecture for graphics drivers" (2009) — https://lwn.net/Articles/348730/
- Wayland WSI in Mesa (`wsi_common_wayland.c`) — https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/src/vulkan/wsi/
- glvnd (vendor-neutral GL dispatch) — https://gitlab.freedesktop.org/glvnd/libglvnd
