# Edge Inference: TFLite Micro, ONNX Runtime Mobile, TensorRT, Coral Edge TPU

Inference at the edge means the model runs *on the device that produced the input*. The device can be a $0.50 microcontroller with 256 KB of RAM, a $25 ESP32 with Wi-Fi, a $99 Google Coral dev kit with a dedicated Edge TPU, a $199 Jetson Nano with a 128-core Maxwell GPU, or a $1200 iPhone 15 Pro with a Neural Engine pushing 35 TOPS. The common thread: no network round-trip, no server inference bill, data stays on-device, and the model fits inside the device's compute, memory, and power budget.

This chapter covers the four mainstream edge inference stacks — TFLite Micro, ONNX Runtime Mobile, TensorRT (on Jetson), and the Google Coral Edge TPU — and the model-to-edge pipeline that produces deployable artifacts for each.

## The Model-to-Edge Pipeline

Every edge deployment walks the same six steps.

```text
1. TRAIN                 fp32 model in PyTorch / TF / JAX
                         architecture chosen for the target's FLOPs budget
                         (MobileNet, EfficientNet-Lite, MobileBERT, TinyYOLO)

2. COMPRESS              prune + distil + low-rank (see Model Compression)
                         reduce parameter count to the device's flash budget

3. QUANTIZE              QAT or PTQ to int8 (see Quantization-Aware Training)
                         per-channel weight scales, asymmetric activations

4. CONVERT               export to the runtime's flatbuffer format:
                           .tflite   (TFLite / TFLite Micro / Coral Edge TPU)
                           .onnx     (ONNX RT Mobile)
                           .engine   (TensorRT, Jetson)

5. BENCHMARK             profile latency, peak RAM, energy on the actual
                         target device; iterate on architecture if misses

6. DEPLOY                OTA the model binary to the device fleet
                         (firmware update, app update, MLOps push)
```

Steps 1–3 are runtime-agnostic; 4–6 are runtime-specific. The choice of runtime is fixed by the *target silicon* — you don't get to pick TFLite Micro for a Jetson, or TensorRT for a Cortex-M0. The table below fixes the mapping.

## Hardware Targets and Their Runtimes

| Device | Compute | RAM | Flash/Storage | Runtime | Typical model size |
|---|---|---|---|---|---|
| **Cortex-M0/M3/M4/M7** (STM32, NXP, Nordic) | 48 MHz – 480 MHz, no FPU on M0/M3, FPU on M4/M7, int DSP extensions on M4F+ | 64–512 KB | 256 KB – 2 MB flash | **TFLite Micro** | < 100 KB |
| **ESP32 / ESP32-S3** (Espressif) | 240 MHz Xtensa LX6/LX7, vector instructions, dual-core | 320–512 KB SRAM | 4–16 MB PSRAM (off-chip) | **TFLite Micro + ESP-NN** | 100 KB – 1 MB |
| **Raspberry Pi 4/5** | 4× Cortex-A76 @ 1.8–2.4 GHz | 1–8 GB | SD card | **ONNX RT Mobile, TFLite** | 1–50 MB |
| **Google Coral Dev Board / USB Accelerator** | NXP i.M8M + Edge TPU coprocessor (4 TOPS int8) | 1 GB LPDDR4 | 8 GB eMMC | **TFLite + Edge TPU delegate** | 1–100 MB |
| **NVIDIA Jetson Nano / Orin Nano** | 128-core Maxwell / 1024-core Ampere GPU + 6 INT8 TOPS (Nano) to 40 TOPS (Orin) | 4 GB / 8 GB LPDDR | SD card / NVMe | **TensorRT** | 10–500 MB |

Power budgets span four orders of magnitude: a Cortex-M0 draws 10 mW in active inference, an ESP32 ~50 mW, an iPhone NPU ~1–3 W under load, a Jetson Orin pulls 7–25 W. The "edge" is not a single target.

## TensorFlow Lite and TFLite Micro

TFLite is the cross-platform edge runtime. The model format is a FlatBuffer (no parsing, memory-mappable, ~3× smaller than the equivalent SavedModel). The interpreter is a single self-contained C++ library; the "Micro" variant is the same interpreter with the heap allocator stripped out and replaced with a user-supplied static arena.

### The TFLite converter and ops

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model("mobilenet_v2")
converter.optimizations = [tf.lite.Optimize.DEFAULT]   # int8 PTQ
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
converter.representative_dataset = calibration_gen    # required for static PTQ
open("mobilenet_v2_int8.tflite", "wb").write(converter.convert())
```

The converter selects ops from the TFLite op set. The full op set has ~400 ops; the Micro subset has ~120 (no `ArgMax` with int64, no `SparseToDense`, no `DynamicPartition` etc.). If your model uses an unsupported op, the converter either falls back to a slower reference impl or fails outright. The Micro-allowed list is at `tensorflow/lite/micro/kernels`.

### TFLite Micro on bare metal

TFLite Micro (David et al., MLSys 2021 — "TensorFlow Lite Micro: Embedded Machine Learning for TinyML Systems") is designed for microcontrollers. The constraints:

```text
- No malloc() — all tensors live in a fixed-size byte array
  (the "tensor arena"), sized at compile time.
- No floating-point in the hot path on Cortex-M0/M3 (no FPU).
  Even on M4F+ the int8 path is 4-10x faster.
- No operating system (often bare-metal); runtime is a single
  C++ class, ~50 KB compiled.
- No file I/O — the model is compiled into the firmware as a
  C array (generated by `xxd -i model.tflite > model.cc`).
```

Usage on a Cortex-M7 (STM32H7):

```cpp
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_helpers.h"
#include "model.h"   // generated by xxd -i

constexpr int kTensorArenaSize = 64 * 1024;       // 64 KB static arena
uint8_t tensor_arena[kTensorArenaSize];

tflite::AllOpsResolver resolver;
const tflite::Model* model = tflite::GetModel(g_model_data);  // compiled-in
tflite::MicroInterpreter interpreter(model, resolver, tensor_arena,
                                     kTensorArenaSize);
interpreter.AllocateTensors();

TfLiteTensor* input  = interpreter.input(0);
TfLiteTensor* output = interpreter.output(0);
// Fill input->data.int8 with sensor data...
interpreter.Invoke();
// Read output->data.int8...
```

The whole interpreter plus a 250 KB keyword-spotting model fits in ~400 KB of flash and runs in 60 ms on a 216 MHz Cortex-M7 — see the [TinyML](./tinyml.md) chapter for the full TinyML stack.

### The Android path (TFLite + NNAPI)

On Android phones, TFLite delegates to the Android Neural Networks API (NNAPI), which routes to the vendor's NPU (Hexagon, Qualcomm HTPU, Samsung SENeN, MediaTek APU). The model is identical to the micro case (`model.tflite`); only the runtime differs. The delegate picks the right EP at runtime:

```python
delegate = tf.lite.experimental.load_delegate("libhexagon_delegate.so")
interpreter = tf.lite.Interpreter(model_path="model.tflite",
                                 experimental_delegates=[delegate])
```

## ONNX Runtime Mobile

ONNX Runtime Mobile targets Android and iOS, with a smaller binary footprint than desktop ONNX RT (the full package is ~30 MB; the mobile package is ~1 MB after op pruning). The standard use case is cross-platform model serving where the training happens in PyTorch (which exports ONNX natively) and the deployment needs a single runtime across Android, iOS, and edge Linux.

### Quantisation and conversion

```python
import onnx
from onnxruntime.quantization import quantize_static, QuantFormat, QuantType

# Convert PyTorch -> ONNX
torch.onnx.export(model, sample_input, "model.onnx",
                  input_names=["input"], output_names=["output"],
                  opset_version=17)

# Static int8 PTQ
quantize_static("model.onnx", "model_int8.onnx",
                calibration_data_reader,
                format=QuantFormat.QDQ,                 # QDQ for clean EP fusion
                per_channel=True,
                weight_type=QuantType.QInt8,
                activation_type=QuantType.QUInt8)
```

### Mobile packaging

ONNX RT Mobile uses an *ORT format* model — a flatbuffer wrap around the ONNX graph with the runtime's optimisations pre-applied. The `onnxruntime.tools.quantize` step is followed by `onnxruntime.tools.optimize` and a mobile-package step that strips unused op kernels to shrink the binary.

```python
from onnxruntime.tools import mobile_helper
# Prune the runtime to only the ops the model needs:
mobile_helper.create_mobile_runtime_package(
    build_dir="build/mobile",
    model="model_int8.onnx",
    output_dir="artifacts/",
    package_name="onnxruntime-mobile-custom")
```

The result: a ~1 MB Android `.aar` or iOS `.xcframework` containing exactly the kernels your model needs. iOS 16+ also gets the CoreML EP as a delegate — when the ONNX graph contains only CoreML-supported ops, ONNX RT transparently delegates to CoreML and runs on the Apple Neural Engine.

## TensorRT on Jetson

Jetson is NVIDIA's edge line: Nano (4 GB, 10 W, Maxwell), Orin Nano (8 GB, 7–15 W, Ampere), Orin AGX (32 GB, 60 W, Ampere, 275 INT8 TOPS). All run standard Linux and CUDA; the runtime is TensorRT, the same TRT that runs in NVIDIA datacenters. The advantage: a model developed and profiled on a desktop RTX card deploys to Jetson with zero changes — only the SM count and memory bandwidth differ.

### The TensorRT pipeline on Jetson

```bash
# 1. Export PyTorch -> ONNX (with QDQ nodes from QAT for int8)
python export_onnx.py --model resnet50_qat --output resnet50.onnx

# 2. Build the TensorRT engine (ONNX -> .engine, target-specific)
trtexec --onnx=resnet50.onnx \
        --saveEngine=resnet50_int8.engine \
        --int8 --workspace=2048 \
        --minShapes=input:1x3x224x224 \
        --optShapes=input:1x3x224x224 \
        --maxShapes=input:16x3x224x224 \
        --useDLACore=0              # use the Deep Learning Accelerator (DLA) on Jetson

# 3. Deploy with C++ runtime (or Python with the tensorrt package)
```

The `--useDLACore` flag is Jetson-specific: every Jetson since Xavier has a fixed-function **Deep Learning Accelerator (DLA)** alongside the GPU. The DLA is slower than the GPU (e.g. 4 TOPS vs 21 on Orin Nano) but uses 1/5 the power. Conv-heavy models (ResNet, MobileNet) go on the DLA; transformer attention stays on the GPU. The TRT engine file is target-specific — an engine built for Orin won't run on Xavier.

### Power-vs-accuracy tuning on Jetson

Jetson's `nvpmodel` exposes power profiles (e.g. Orin Nano has 15 W / 10 W / 7 W modes). Latency of a YOLOv5s inference at int8 ranges from 12 ms at 15 W to 25 ms at 7 W. Edge deployments typically pin `nvpmodel` to the lowest mode that meets the latency SLO, then verify thermal envelope in the deployment chassis.

## Google Coral Edge TPU

The Edge TPU is Google's ASIC for int8 inference. It runs a *subset* of TFLite ops — the model must (a) be fully int8 PTQ, (b) use only Edge-TPU-supported ops, (c) have tensor shapes that fit the matrix-multiply unit (multiples of 8 for many ops). The compiler enforces these and refuses to map unsupported ops to the TPU (they fall back to CPU on the host).

### The Coral compile step

```bash
# The model must already be an int8 .tflite from the TFLite converter.
edgetpu_compiler -s model_int8.tflite
# Produces: model_int8_edgetpu.tflite
# Layers that can't be mapped to Edge TPU stay on CPU
# (the .tflite has separate buffers for TPU and CPU layers).
```

The Edge TPU's INT8 throughput is 4 TOPS on the Dev Board and the USB Accelerator. A MobileNet-v2 int8 image-classification runs in ~5 ms. The Dev Board's i.M8M CPU is comparatively slow (Cortex-A53 × 4 @ 1.5 GHz); if more than ~10% of ops fall back to CPU, latency dominates.

The Edge TPU was discontinued as a standalone product line in late 2024 (Google Coral moved to a "Coral.ai" services model); new edge-TPU designs today lean on the Hailo-8 (26 TOPS), the Rockchip RK3588 NPU (6 TOPS), the Kendryte K230 (1 TOPS) — but the deployment shape (TFLite + vendor compile step) is identical.

## Comparison: Which Stack for Which Target

| Target | Best runtime | Why |
|---|---|---|
| Cortex-M0/M4/M7, ESP32 | TFLite Micro | the only stack with a no-malloc, no-OS, single-binary footprint |
| ESP32-S3 with NN extensions | TFLite Micro + ESP-NN | Espressif's hand-tuned Xtensa DSP kernels for int8 conv |
| Android phone | TFLite (NNAPI delegate) | vendor NPU access via NNAPI; standard TFLite format |
| iPhone / iPad | ONNX RT Mobile (CoreML EP) or CoreML directly | CoreML is the only path to the Apple Neural Engine |
| Raspberry Pi / Linux edge | TFLite or ONNX RT Mobile | either works; TFLite has slightly more NEON-tuned kernels |
| Jetson | TensorRT | only path to Jetson's GPU + DLA + tensor cores |
| Coral Edge TPU / Hailo / RK3588 NPU | TFLite + vendor delegate | Edge-TPU-class ASICs all expose themselves as TFLite delegates |

## Deployment Operational Concerns

1. **Cold-start latency.** First inference is slow — TFLite interpreter allocates the arena, ONNX RT compiles the kernel, TRT builds the engine (this one can take *minutes*). Build engines once, persist them to disk, and ship the built artifact. TFLite Micro has no cold start (everything is compiled-in).
2. **Memory peak.** The intermediate-activation memory is often the binding constraint on microcontrollers, not the model weights. TFLite Micro's "memory planner" reuses buffers between non-overlapping ops, but you must size the arena at compile time and over-provision by ~20%.
3. **Thermal throttling.** Phones throttle the NPU after ~30 s of continuous inference; drones throttle in seconds. Build a duty-cycle budget into the application.
4. **OTA model updates.** A 250 KB model on a microcontroller means a 250 KB firmware delta over the air. Use a binary-diff protocol (e.g. `bsdiff`) and a bootloader with two banks so the device can roll back on a failed update.
5. **Privacy vs. observability trade-off.** Edge inference is private (data stays on device) but hard to monitor (you can't log the inputs). Add opt-in, on-device quality sampling where the user can consent to a small fraction of inputs being uploaded for evaluation.

## References

- Robert David et al., "[TensorFlow Lite Micro: Embedded Machine Learning for TinyML Systems](https://arxiv.org/abs/2104.06772)" (MLSys 2021)
- [TensorFlow Lite converter — integer quantization](https://www.tensorflow.org/lite/performance/quantization_spec)
- [TensorFlow Lite Micro documentation](https://www.tensorflow.org/lite/microcontrollers)
- [ONNX Runtime Mobile documentation](https://onnxruntime.ai/docs/tutorials/mobile/)
- [NVIDIA Jetson developer documentation](https://developer.nvidia.com/embedded-computing)
- [TensorRT developer guide](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html)
- [Google Coral Edge TPU compiler documentation](https://coral.ai/docs/edgetpu/compiler/)
- Pete Warden, Daniel Situnayake, "[TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers](https://www.oreilly.com/library/view/tinyml/9781492052036/)" (O'Reilly 2019)
- [ESP-NN: optimised NN kernels for ESP32](https://github.com/espressif/esp-nn)
- [Hailo-8 developer documentation](https://hailo.ai/) — modern Edge-TPU-class alternative

## Cross-References

- [Quantization-Aware Training](./quantization-aware-training.md) — int8 training and inference
- [Model Compression](./model-compression.md) — pruning / distillation / low-rank
- [TinyML](./tinyml.md) — extreme microcontroller deployment
- [Edge ML](./edge.md) — companion overview page
- [Model Serving](../system-design/model-serving.md) — cloud-side serving
