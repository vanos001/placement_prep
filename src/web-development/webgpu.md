# WebGPU

WebGPU is the next-generation graphics and compute API for the web. It exposes a modern, low-overhead interface to the GPU — explicit pipeline objects, descriptor-allocated resources, and **compute shaders** — that matches the design of Vulkan, Metal, and Direct3D 12. It replaces WebGL (a 2011 API built on OpenGL ES 2.0) as the standard for graphics on the web. It shipped in Chrome 113 (May 2023); Firefox and Safari have partial implementations behind flags as of 2024.

## Why Replace WebGL

WebGL's design reflects OpenGL ES 2.0 — a state-machine API where you bind resources to global slots and call draw commands. Every binding is implicit state, and the driver must validate it on every draw. This made sense in 2011; in 2024, modern GPUs want immutable pipeline state objects and bindless resources. WebGL also has no compute shaders — every GPU computation has to be smuggled in through vertex/fragment shaders.

WebGPU fixes both:

| Aspect | WebGL | WebGPU |
|--------|-------|--------|
| Underlying model | OpenGL ES state machine | Explicit descriptor-based (Vulkan/Metal/D3D12) |
| Shader language | GLSL (transpiled to SPIR-V) | WGSL (native) |
| Compute shaders | No | Yes |
| Bindings | Global slots (`gl.activeTexture(0); bindTexture(...)`) | Bind groups (immutable descriptor) |
| Pipeline objects | Implicit per-draw | `GPURenderPipeline` (precompiled) |
| Multi-threading | Single thread | Workers can hold `GPUDevice` |
| Validation | Runtime, per-call | Baked at pipeline creation |

## The Adapter / Device Abstraction

WebGPU follows the Vulkan/Metal model: you request an **adapter** (a physical GPU + driver), then request a **device** (a logical GPU context with its own queue and memory limits).

```js
// 1. Get an adapter — a request to the browser to enumerate GPUs.
const adapter = await navigator.gpu.requestAdapter({
  powerPreference: 'high-performance',  // or 'low-power'
  featureLevel: 1,                       // optional — request newer features
});

if (!adapter) {
  throw new Error('WebGPU not available on this machine');
}

// 2. Inspect what the adapter supports.
console.log('limits:', adapter.limits);
console.log('features:', adapter.features);  // Set<string>
console.log('isFallbackAdapter:', adapter.isFallbackAdapter);

// 3. Request a logical device with the limits/features you want.
const device = await adapter.requestDevice({
  requiredFeatures: ['depth-clip-control', 'texture-compression-bc'],
  requiredLimits: {
    maxBufferSize: 1 << 30,         // 1 GB
    maxStorageBufferBindingSize: 1 << 28,
  },
});

// 4. The device queue is how you submit work to the GPU.
const queue = device.queue;
```

The `requiredLimits` pattern is key: you ask for what you need; the browser fails fast if the device doesn't support it. WebGL gave you whatever limits the driver had, and you discovered them at runtime.

## Buffers

A `GPUBuffer` is a typed, opaque chunk of GPU memory. The `usage` flags are mandatory and cannot be changed after creation:

```js
const vertexBuffer = device.createBuffer({
  size: 12 * Float32Array.BYTES_PER_ELEMENT,  // 3 vec2s = 6 floats = 24 bytes
  usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
});

// Upload CPU data — the queue is the only path from CPU to GPU memory.
const vertices = new Float32Array([
  -0.7, -0.7,
   0.7, -0.7,
   0.0,  0.7,
]);
device.queue.writeBuffer(vertexBuffer, 0, vertices);
```

The `writeBuffer` method is the modern, high-throughput path — the older `setSubData` was removed from the spec. It does a CPU→GPU transfer, async under the hood. For read-back, you create a **mapped** buffer:

```js
const readback = device.createBuffer({
  size: 16,
  usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
});

// Encode a command to copy from a GPU buffer to the readback buffer.
const encoder = device.createCommandEncoder();
encoder.copyBufferToBuffer(gpuBuffer, 0, readback, 0, 16);
device.queue.submit([encoder.finish()]);

// Map the readback buffer for CPU access (async — wait for prior submits).
await readback.mapAsync(GPUMapMode.READ);
const arrayBuffer = readback.getMappedRange();
const result = new Float32Array(arrayBuffer);
console.log('GPU result:', result);
readback.unmap();
```

## Textures

Textures are 1D/2D/3D arrays of texels with a specific format. Their usage flags determine whether they're render targets, sampled images, or both:

```js
const texture = device.createTexture({
  size: [1024, 768],
  format: 'bgra8unorm',  // matches the canvas context format
  usage: GPUTextureUsage.RENDER_ATTACHMENT |
         GPUTextureUsage.TEXTURE_BINDING |
         GPUTextureUsage.COPY_SRC,
});

// A texture view is the "GPU pointer" used by shaders.
const view = texture.createView();
```

The most important texture in any WebGPU app is the **swapchain texture** — the one you render to and the browser presents to the user:

```js
const canvas = document.querySelector('canvas');
const context = canvas.getContext('webgpu');
const format = navigator.gpu.getPreferredCanvasFormat();
context.configure({ device, format, alphaMode: 'premultiplied' });

// Per frame:
const swapChainTexture = context.getCurrentTexture().createView();
```

## Bind Groups and Layouts

WebGPU groups bindings into **bind groups** — sets of resources (buffers, textures, samplers) that are bound together. The layout of a bind group is a separate object, which lets the driver pre-compile a descriptor table:

```js
const bindGroupLayout = device.createBindGroupLayout({
  entries: [
    { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'uniform' } },
    { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' } },
    { binding: 2, visibility: GPUShaderStage.COMPUTE, buffer: { type: 'storage' } },
  ],
});

const bindGroup = device.createBindGroup({
  layout: bindGroupLayout,
  entries: [
    { binding: 0, resource: { buffer: uniformBuffer } },
    { binding: 1, resource: { buffer: inputBuffer } },
    { binding: 2, resource: { buffer: outputBuffer } },
  ],
});
```

The separation of layout from bind group means you can reuse the layout across many bind groups — and the GPU driver can pre-build the binding tables. This is the core overhead win over WebGL's `gl.uniform1f(...)` calls.

## Pipelines

A `GPURenderPipeline` is an immutable, precompiled state object: shader modules, blend state, vertex layout, depth-stencil state. Creating a pipeline is expensive (it actually compiles shaders); using one is cheap. WebGL re-validated per draw; WebGPU bakes at creation.

```js
const shaderModule = device.createShaderModule({
  code: /* WGSL */ `
    struct VertexIn { @location(0) pos: vec2f };
    struct VertexOut { @builtin(position) clip: vec4f };

    @vertex
    fn vmain(in: VertexIn) -> VertexOut {
      var out: VertexOut;
      out.clip = vec4f(in.pos, 0.0, 1.0);
      return out;
    }

    @fragment
    fn fmain() -> @location(0) vec4f {
      return vec4f(0.8, 0.2, 0.4, 1.0);
    }
  `,
});

const pipeline = device.createRenderPipeline({
  layout: 'auto',  // auto-derive from the shader
  vertex: {
    module: shaderModule,
    entryPoint: 'vmain',
    buffers: [
      {
        arrayStride: 8,
        attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x2' }],
      },
    ],
  },
  fragment: {
    module: shaderModule,
    entryPoint: 'fmain',
    targets: [{ format: 'bgra8unorm' }],
  },
  primitive: { topology: 'triangle-list' },
});
```

## Render Passes

A render pass is a single submit to the GPU containing one or more draw calls. It's encoded into a command buffer:

```js
const encoder = device.createCommandEncoder();
const passEncoder = encoder.beginRenderPass({
  colorAttachments: [{
    view: swapChainTexture,
    clearValue: { r: 0.1, g: 0.1, b: 0.1, a: 1.0 },
    loadOp: 'clear',
    storeOp: 'store',
  }],
});

passEncoder.setPipeline(pipeline);
passEncoder.setBindGroup(0, bindGroup);
passEncoder.setVertexBuffer(0, vertexBuffer);
passEncoder.draw(3);  // 3 vertices, 1 instance
passEncoder.end();

device.queue.submit([encoder.finish()]);
```

The whole pass is built up off the GPU and submitted as one immutable command buffer — the GPU can begin executing it without further CPU round-trips.

## Compute Shaders

This is the headline feature WebGL never had. A compute pipeline dispatches work in **workgroups** of `x × y × z` invocations:

```js
const computeModule = device.createShaderModule({
  code: /* WGSL */ `
    @group(0) @binding(0) var<uniform> params: Params;
    @group(0) @binding(1) var<storage, read>  input: array<f32>;
    @group(0) @binding(2) var<storage, read_write> output: array<f32>;

    struct Params { count: u32 };

    @compute @workgroup_size(64)
    fn cmain(@builtin(global_invocation_id) id: vec3u) {
      let i = id.x;
      if (i >= params.count) { return; }
      output[i] = input[i] * 2.0;
    }
  `,
});

const computePipeline = device.createComputePipeline({
  layout: 'auto',
  compute: { module: computeModule, entryPoint: 'cmain' },
});

// Dispatch.
const encoder = device.createCommandEncoder();
const pass = encoder.beginComputePass();
pass.setPipeline(computePipeline);
pass.setBindGroup(0, bindGroup);
pass.dispatchWorkgroups(Math.ceil(count / 64));  // 64 workgroups
pass.end();
device.queue.submit([encoder.finish()]);
```

`workgroup_size(64)` means each workgroup has 64 invocations. Total threads = `workgroup_count × workgroup_size`. Each invocation reads its own index from `global_invocation_id` and processes one element. This is the same model as CUDA / OpenCL / Vulkan compute shaders — you can port between them straightforwardly.

## WGSL

WebGPU Shading Language is a new language designed specifically for the web. It's safer than GLSL (no preprocessor; first-class types), simpler than HLSL, and maps directly to SPIR-V under the hood. Key features:

- Type suffixes: `vec2f` instead of `vec2<f32>`, `f32` not `float`.
- `@builtin`, `@location`, `@group`/`@binding` annotations for I/O.
- `var<uniform>`, `var<storage, read>`, `var<storage, read_write>` for memory qualifiers.
- No pointers in user code (with limited exceptions for `let` bindings).
- `fn` keyword, no `void` return type needed.

The full WGSL spec is at https://www.w3.org/TR/WGSL/.

## The Portability Layer: Dawn and wgpu

Browsers don't speak directly to Vulkan/Metal/D3D12 from JavaScript. There's a portability layer:

```
  JavaScript (app)                       Rust glue
       |                                    |
       v                                    v
  +-----------------+               +-----------------+
  | WebGPU bindings |               |  WebGPU impl    |
  +-----------------+               +-----------------+
                                            |
              +-----------------------------+---+
              |                                 |
        Chrome (Dawn)                     Firefox/wgpu (Rust)
        C++ wrapper around                 Rust wrapper around
        Vulkan/Metal/D3D12/OpenGL          Vulkan/Metal/D3D12
              |
              v
        GPU driver (vendor)
```

- **Dawn** — Google's C++ implementation, used by Chrome. Open source at https://dawn.googlesource.com/dawn/. Wraps Vulkan (Linux/Android), Metal (macOS/iOS), D3D12 (Windows), and even OpenGL as a fallback.
- **wgpu** — Rust implementation, used by Firefox and Servo. Open source at https://wgpu.rs/. Same backends as Dawn.
- Both pass the same conformance test suite, so the same JS code runs on either.

The `wgpu` Rust crate is also widely used standalone by Rust desktop apps (e.g., the Bevy game engine) — they get one codebase for desktop and web.

## Comparison to WebGL

| Aspect | WebGL 2 | WebGPU |
|--------|---------|--------|
| Compute | No (transform feedback hack) | Native compute shaders |
| Validation | Per-draw, runtime | At pipeline creation, baked |
| Bindings | Global slots, set per draw | Bind groups, descriptor-allocated |
| Shaders | GLSL → SPIR-V (transpiled by browser) | WGSL (native, browser-compiled) |
| Multi-thread | Main thread only | Workers can hold `GPUDevice` |
| Indirect draws | Limited | Full `drawIndirect` / `dispatchIndirect` |
| Memory model | Driver-managed | Explicit (`mapAsync`, `writeBuffer`) |
| Status | Universal | Chrome 113+, partial in FF/Safari |

The biggest practical wins:
1. **Compute shaders** unlock GPU workloads beyond rendering (physics, ML inference, image processing).
2. **Lower per-draw CPU overhead** — bind groups and pipeline objects are precompiled; you can issue 100k draws/frame without the browser re-validating each one.
3. **Worker support** — you can run render logic on a Web Worker, freeing the main thread for UI.

## Real-World Use Cases

### ML Inference

Run ONNX or PyTorch models entirely in the browser using compute shaders. The ONNX Runtime Web EP for WebGPU gets 2-5x the throughput of the WebGL EP on ResNet-50 and BERT.

### Browser-Based Game Engines

Bevy (Rust), Babylon.js, and Three.js have WebGPU backends. The Three.js `WebGPURenderer` is now the recommended path for new projects that don't need to support Safari < 18.

### Procedural Content Generation

Compute shaders can generate terrain, run fluid simulations, and bake textures at frame rate — work that used to require Web Workers + CPU.

## Pitfalls

1. **Pipeline creation is expensive.** Compile shaders off the hot path. Don't recreate pipelines in your render loop.
2. **Async is implicit.** `device.queue.submit()` returns immediately; the GPU runs later. Don't read back mapped buffers before `mapAsync` resolves.
3. **Bind group churn.** Each `setBindGroup` costs CPU. Sort draws by bind group to minimize switches.
4. **Validation is strict.** Wrong usage flags, mismatched formats — the device emits errors via `device.pushErrorScope`. In development, log these aggressively; in production, silence them.
5. **WGSL is strict about types.** `vec4f` ≠ `vec4<i32>`; mixing them is a compile error. The WGSL spec is your friend: https://www.w3.org/TR/WGSL/.

## Interview Questions

**Q1: Why does WebGPU require explicit `usage` flags on buffers and textures?**
A: Because the underlying native APIs (Vulkan, Metal, D3D12) require them — they let the driver pick the right memory pool (e.g., host-visible vs. device-local) and reject conflicting usages at creation rather than during a draw. WebGL let you reuse buffers for anything, but the driver had to assume the worst and often fell back to slow paths.

**Q2: What is a bind group and how does it differ from WebGL uniforms?**
A: A bind group is an immutable descriptor grouping together resources (uniforms, storage buffers, textures) bound to a pipeline at a specific `@group(N)`. The layout is precompiled, so binding a bind group is one CPU call, not a stream of `gl.uniform1f` calls. You change resources by binding a new bind group, not by updating individual uniforms.

**Q3: How do compute shaders work in WebGPU?**
A: You write a `@compute` entry point in WGSL, declare `@workgroup_size(x, y, z)`, and dispatch with `dispatchWorkgroups(countX, countY, countZ)`. Total threads = `countX * countY * countZ * workgroupSize`. Each thread reads its `global_invocation_id` and processes one element. Workgroups execute in parallel; threads within a workgroup can share memory via `var<workgroup>`.

**Q4: What's the difference between Dawn and wgpu?**
A: Both are implementations of the WebGPU spec for the backend native APIs (Vulkan/Metal/D3D12). Dawn is Google's C++ implementation, used by Chrome. wgpu is the Rust implementation, used by Firefox and Servo, and also used standalone by Rust apps (Bevy). They pass the same conformance suite, so the same JS runs on either.

**Q5: Why is WGSL a new language instead of using GLSL?**
A: GLSL has a C preprocessor (security risk), lacks first-class types (you write `vec2<float>`), and was designed for OpenGL's state-machine model. WGSL is safer (no preprocessor), type-suffixed (`vec2f`), and maps cleanly to SPIR-V (which is the underlying IR for both Vulkan and WGSL). It also has a formal specification with a reference interpreter, unlike GLSL.

## References

- [W3C WebGPU Specification](https://www.w3.org/TR/webgpu/)
- [W3C WGSL Specification](https://www.w3.org/TR/WGSL/)
- [MDN: WebGPU API](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API)
- [Chrome Developers: WebGPU](https://developer.chrome.com/docs/web-platform/webgpu/)
- [Dawn — WebGPU implementation in C++](https://dawn.googlesource.com/dawn/)
- [wgpu — WebGPU implementation in Rust](https://wgpu.rs/)
- [webgpu.io — community guide](https://webgpu.github.io/webgpu-samples/)
- [WebGPU samples repository](https://github.com/webgpu/webgpu-samples)
