# TinyML: Machine Learning on Microcontrollers

TinyML is the strictest compression target in the field: running ML inference on microcontrollers with kilobytes — not megabytes — of RAM, often clocked at single-digit megahertz, drawing milliwatts from a coin cell. The TinyML Foundation and Pete Warden's eponymous book (Warden & Situnayake, O'Reilly 2019) set the working definition at "models under 100 KB on devices under 1 MB of RAM". The Harvard TinyML course (CS249R, "TinyML and Efficient Deep Learning Computing", led by Song Han and colleagues) is the academic reference, covering the algorithmic, system, and hardware co-design required to make neural networks run on the smallest compute.

This chapter walks through the resource constraints, the model sizes that fit, the training-to-deployment pipeline, the sensor-fusion architectures, the power budget, and three real-world deployments: keyword spotting, anomaly detection, and gesture recognition.

## The Resource Envelope

A typical TinyML target (the *Arduino Nano 33 BLE Sense* used in most TinyML pedagogy) has:

```text
MCU:           nRF52840 (Cortex-M4F @ 64 MHz)
Flash:          1 MB
RAM:            256 KB
Battery:        CR2032 coin cell (220 mAh @ 3 V) or LiPo (~400 mAh)
Active power:   ~10 mA @ 64 MHz = ~30 mW at 3 V
Sleep power:    ~5 µA (≈15 µW)
Sensors:        on-board IMU (LSM9DS1), microphone (MP34DT05),
                humidity/temperature/pressure (HTS221/LPS22),
                gesture/colour (APDS9960)
```

Compare this to a Raspberry Pi (1 GB RAM, 1.5 GHz, 5 W active) or an iPhone (8 GB RAM, 3 GHz, 5 W peak on the NPU). The TinyML envelope is 1000× tighter on every axis. The Harvard TinyML lectures make the numbers concrete: a single `fp32` multiply-accumulate on a Cortex-M4F takes ~16 ns (one cycle on the FPU pipeline), while an int8 multiply takes ~16 ns as well (no int8 dot-product instruction on M4 — there's `SMLAD` for int16 pairs, but no native int8 dot). So a 1 MMAC model runs in ~16 ms at 64 MHz, drawing ~30 mW — about 0.5 mJ per inference.

The "less than 1 MHz CPU" target in the working definition refers to the lowest-end TinyML deployments: ARC EM4 (Synopsys) and the *Ambiq Apollo* family (Cortex-M4F with subthreshold voltage operation) which run at 48 MHz but at 6 µA/MHz — 200× more efficient than the nRF52840. An Ambiq Apollo4 can run continuous keyword spotting on a hearing-aid battery for weeks.

## Model Sizes That Fit

The model size budget on a 256 KB-RAM microcontroller is roughly:

```text
Flash budget    100-500 KB of firmware, including model + interpreter
                -> model: 50-250 KB after int8 PTQ
                -> interpreter (TFLite Micro): ~50 KB compiled

RAM budget      64-128 KB of static arena (after stack + heap)
                -> activation tensors live in the arena
                -> weights stay in flash (XIP) or are copied to RAM on demand
                -> bigger models = smaller activations (tradeoff!)

MAC budget      100k-10M per inference (latency-bound on slow CPUs)
                -> 100k MACs ≈ 1.6 ms on a 64 MHz M4F int8
                -> 10M MACs ≈ 160 ms (too slow for keyword spotting @ 10 Hz)
```

Real TinyML architectures and their footprint (from the TinyML book and TFLite Micro examples):

| Model | Application | MACs | Size (int8) | Latency on M4F |
|---|---|---|---|---|
| **DS-CNN (Depthwise Separable CNN)** | Keyword spotting (12 keywords) | ~5 M | ~46 KB | ~80 ms |
| **MicroNet / MobileNet-v1 0.25** | Image classification (10 classes, 32×32 input) | ~600 k | ~100 KB | ~10 ms |
| **TinyVisualWakeWord** | Person-detection (96×96 input) | ~25 M | ~250 KB | ~400 ms |
| **1D CNN / 3-layer MLP** | Anomaly detection (accelerometer) | ~50 k | ~10 KB | ~0.8 ms |
| **TinyBERT-2-layer (distilled)** | Intent classification (3 intents) | ~3 M | ~80 KB | ~50 ms |
| **Autoencoder** | Vibration anomaly | ~200 k | ~30 KB | ~3 ms |

The pattern: every TinyML model is *distilled* into a tiny architecture (DS-CNN, MobileNet-tiny, distilled 2-layer BERT) and *quantised* to int8 (per-channel scales), with the interpreter kernel set pruned to exactly the ops the model uses. Skipping any one of these steps pushes the model out of the budget.

## The Training-to-Deployment Pipeline

```text
┌──────────────────────────────────────────────────────────────┐
│ 1. TRAIN                                                      │
│    PyTorch / TF Keras on a desktop GPU.                       │
│    Architecture: depthwise-separable CNNs, TinyBERT, etc.     │
│    Often distilled from a large teacher.                      │
│    Typical: 1-100 M MACs, fp32, 5-100 MB on disk.             │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. PRUNE + DISTIL                                             │
│    Magnitude / structured pruning to 50-90% sparsity.        │
│    Distillation from the fp32 teacher if accuracy drops.     │
│    Result: 2-10x smaller, still fp32.                        │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. QUANTIZE (QAT)                                             │
│    QAT with per-channel weight scales, int8 weights,         │
│    asymmetric int8 activations.                              │
│    Result: 4x smaller than fp32, near-lossless accuracy.     │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. CONVERT TO .tflite                                         │
│    TFLite converter, OpsSet.TFLITE_BUILTINS_INT8,            │
│    representative_dataset for activation calibration.        │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. COMPILE INTO FIRMWARE                                      │
│    xxd -i model.tflite > model.cc                            │
│    Link with TFLite Micro (only the kernels you use).        │
│    Build with PlatformIO / Arm GNU toolchain.                 │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. BENCHMARK ON TARGET                                        │
│    Measure: latency, peak RAM (tensor arena size), energy.  │
│    Iterate on architecture if misses SLO.                    │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. FLASH + RUN                                                │
│    Firmware image flashed to the device via SWD/UART/USB.   │
│    Inference runs in a static arena; no malloc anywhere.    │
└──────────────────────────────────────────────────────────────┘
```

The Arduino TinyML examples (in the *Arduino_TinyML* library by Pete Warden et al.) implement steps 4–7 as a single sketch that loads a pre-compiled `.tflite` model array and runs inference in `loop()`.

### The C++ skeleton on Arduino

```cpp
#include <TensorFlowLite.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/system_helpers.h"
#include "model.h"   // the .tflite compiled in as a C array

constexpr int kArenaSize = 16 * 1024;
uint8_t arena[kArenaSize];

tflite::AllOpsResolver resolver;
tflite::MicroInterpreter interpreter(tflite::GetModel(model_tflite),
                                     resolver, arena, kArenaSize);

void setup() {
  interpreter.AllocateTensors();
  // Wire up sensors, set sampling rate.
}

void loop() {
  // 1. Read IMU + microphone into input tensor (int8).
  fill_input(interpreter.input(0));
  // 2. Run inference.
  interpreter.Invoke();
  // 3. Read output, act on it.
  TfLiteTensor* out = interpreter.output(0);
  int8_t* logits = out->data.int8;
  float scale = out->params.scale;
  // ...decode prediction, update LED or motor...
  delay(50);   // 20 Hz inference rate
}
```

The `AllOpsResolver` links in *every* op TFLite Micro supports (~50 KB of code). For real deployments you switch to `MicroMutableOpResolver` and register only the specific ops the model uses — typically bringing the interpreter down to ~10 KB and the full firmware under 100 KB.

## Sensor Fusion: Accelerometer + Microphone + Camera

Most TinyML deployments are *multi-modal* — the device has several cheap sensors and the model fuses them. The reason is mechanical: a 1-axis accelerometer alone is too ambiguous (running looks like walking looks like falling); a microphone alone is too noisy in a pocket; a low-res camera alone burns too much energy. Three small models, each per-modality, fused at the application layer, beat one big model on every axis.

The canonical pattern, exemplified by the Arduino Nano 33 BLE Sense's stock examples (Warden 2019, *TinyML* Chapter 7):

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  IMU @ 100 Hz│   │ Mic @ 16 kHz │   │ Cam @ 1 Hz   │
│  (3 axes)    │   │ (256-sample  │   │ (96x96 RGB)  │
│              │   │  windows)    │   │              │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                   │
       ▼                  ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 1D CNN       │   │ DS-CNN       │   │ MobileNetV1  │
│ (3-layer)    │   │ (keyword     │   │ 0.25 (person │
│  ~10 KB      │   │  spotter)    │   │  detect)     │
│              │   │  ~46 KB      │   │  ~250 KB     │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                   │
       └──────────────────┼───────────────────┘
                          ▼
              ┌───────────────────────┐
              │  Application fusion   │
              │  (if camera sees face│
              │   AND mic hears "yes"│
              │   AND IMU shows nod →│
              │   trigger gesture)   │
              └───────────────────────┘
```

Each sub-model has its own sampling rate and is invoked at the rate the application needs — the IMU CNN runs at 50 Hz (one inference per 20 ms), the keyword spotter at 4 Hz (one per 250 ms), the camera at 1 Hz. This staggering is what makes fusion power-feasible: the camera — by far the most expensive sensor — runs least often.

## The Power Budget

TinyML deployments are almost always battery-powered, and the inference rate is fixed by the *energy* per inference, not just the latency. A CR2032 coin cell holds ~220 mAh at 3 V = ~2400 J. At 30 mW active and 15 µW sleep, the duty-cycle maths is:

```text
P_avg = (inference_rate × inference_duration × P_active)
      + (1 - duty_cycle) × P_sleep

At 1 Hz inference, 100 ms each, on the nRF52840:
  P_avg = 1 × 0.1 × 30 mW + 0.9 × 15 µW
        = 3 mW + 13.5 µW  ≈ 3 mW
  Battery life ≈ 2400 J / 0.003 W = 800 000 s ≈ 9 days

At 0.1 Hz (every 10 s, e.g. anomaly detector):
  P_avg ≈ 0.3 mW + ~0.015 mW ≈ 0.31 mW
  Battery life ≈ 2400 / 0.00031 ≈ 90 days
```

The arithmetic is brutal: every extra millisecond of active inference time on a CR2032 costs a day of battery life at 1 Hz. This is why TinyML papers obsess over *energy per inference* — the Harvard group's "Once-for-All" (Cai et al., ICLR 2020) and Song Han's MCUNet / MCUNetV2 (Lin et al., NeurIPS 2020 and 2021) explicitly co-optimise the architecture for energy on a specific MCU, achieving ImageNet-level accuracy at <1 mJ per inference on a Cortex-M7.

Three concrete levers to extend battery life:

1. **Run inference less often.** A 1 Hz duty cycle is 10× more expensive than 0.1 Hz. Use a low-power "wake-on-event" sensor (e.g. an always-on accelerometer threshold detector at 1 µA) to gate the CNN.
2. **Use a slower, more efficient MCU.** Ambiq's Apollo family runs the same int8 model at 1/10 the energy of an nRF52840. The bill of materials is higher but the battery is smaller.
3. **Aggressively enter sleep between inferences.** TFLite Micro's `Invoke()` returns control to the application; if your `loop()` keeps the CPU awake, you waste the entire duty-cycle advantage. Always `WFI` (wait-for-interrupt) between inferences.

## Real-World Deployments

### Keyword Spotting (KWS)

The "hello world" of TinyML. The task: detect 1 of ~12 wake-words ("yes", "no", "on", "off", etc.) from 1-second audio windows. The reference dataset is Google's Speech Commands v2 (Warden, 2018) — 35 word classes, 105k clips.

The reference architecture (Zhang et al., 2017, "Hello Edge: Keyword Spotting on Microcontrollers") is a **DS-CNN**: 3 layers of depthwise-separable 1D convolutions over log-Mel spectrograms. The spectrogram extraction (FFT, Mel filterbank) is itself ~10% of the inference energy — the rest is the CNN. The deployed model is ~46 KB int8, runs in ~80 ms on a Cortex-M7, and gets ~90% accuracy on the 12-word subset.

The application-level decision is "did the user say *the* wake-word in the last second?". A confidence threshold (e.g. softmax > 0.7) gates a system action; a CTC-based sequence model handles phrases ("hey siri", "ok google") at the cost of more memory. Production deployments (Arm Cortex-M-based hearing aids, smart speakers) co-design the audio front-end (noise suppression, beamforming) with the KWS model.

### Anomaly Detection

A 1D CNN or small autoencoder monitors an industrial accelerometer or microphone for out-of-distribution vibration patterns — a failing bearing, an unusual motor current, a stuck valve. The reference is the Harvard *TinyML Anomaly Detection* tutorial: a 3-layer autoencoder trained on *normal* operation, deployed as the encoder + a fixed reconstruction-error threshold.

```text
Autoencoder: input (128) -> dense(16) -> dense(8) -> dense(16) -> dense(128)
Train: minimise MSE reconstruction on normal data.
Deploy: only the encoder + a fixed decoder matrix; compute reconstruction
        error; raise alarm if error > rolling-95th-percentile threshold.
Size: ~30 KB int8; latency ~3 ms; sampling at 1 kHz on a magnetometer.
```

The deployment wins are operational: no need to label anomalous data (only "normal" data is used in training), the threshold is set per-device from its own first-week baseline, and the device sends a single byte ("anomaly / no anomaly") over LoRa or NB-IoT — bandwidth and energy both tiny. A factory floor with 500 vibration sensors runs for years on coin cells.

### Gesture Recognition

A wearable detects hand gestures (wrist flick, double-tap, shake) from a 3-axis accelerometer + 3-axis gyro at 100 Hz. The reference architecture is a small 1D CNN or GRU over 1–2 second windows (Warden 2019, Chapter 5). The deployed model is ~10 KB int8, runs in ~1 ms — the IMU itself dominates the per-inference energy at this scale.

The deployment is *interactive*: gesture → UI action must complete in <100 ms or the user perceives lag. This bounds the inference rate at ~20 Hz (one window per 50 ms) and the model size at ~1 ms latency. The gesture vocabulary is small (3–6 classes) because the wearable's UX is small.

## Common Pitfalls

1. **Forgetting the audio/sensor front-end.** The Mel-spectrogram extraction for KWS is itself ~10 KB of code and ~10 ms of CPU. Budget for it.
2. **Using `float` in the hot path.** On a Cortex-M0/M3 (no FPU), a single `float` multiply is 100× slower than an int8 multiply. Everything in the hot path must be int8; even the input pre-processing (Mel bins, normalisation) should be quantised.
3. **The "activation peak" trap.** A model with 50 KB of weights can require 80 KB of activation RAM if the architecture doesn't reuse buffers. Use TFLite Micro's memory planner reports (it prints the peak arena usage at allocation time) to catch this before flashing.
4. **OTA updates are hard.** A 100 KB model on a coin-cell device means a 100 KB firmware delta over BLE — which at 10 KB/s is 10 s of radio-on time, killing battery. Plan for infrequent updates, and ship the model compiled into the firmware rather than as a separate downloadable blob.
5. **Not benchmarking on the actual target.** QEMU and `tflite_micro_benchmark` on x86 give completely wrong numbers — the memory access patterns dominate on a 64 MHz M4F with no cache. Always profile on the real chip with a logic analyser on the power rail.

## References

- Pete Warden, Daniel Situnayake, "[TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers](https://www.oreilly.com/library/view/tinyml/9781492052036/)" (O'Reilly 2019) — the canonical TinyML book
- Robert David et al., "[TensorFlow Lite Micro: Embedded Machine Learning for TinyML Systems](https://arxiv.org/abs/2104.06772)" (MLSys 2021)
- [Harvard CS249R: TinyML and Efficient Deep Learning Computing](https://hanlab.mit.edu/course) — Song Han's TinyML course
- [TensorFlow Lite Micro documentation](https://www.tensorflow.org/lite/microcontrollers)
- [Arduino TinyML examples — petewarden/arduino_tinyml](https://github.com/petewarden/arduino_tinyml) — Warden's open-source pedagogy examples
- Yundong Zhang, Naveen Suda, Liangzhen Lai, Anand Krishnan, "[Hello Edge: Keyword Spotting on Microcontrollers](https://arxiv.org/abs/1711.07128)" (2017)
- Pete Warden, "[Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition](https://arxiv.org/abs/1804.03209)" (2018) — the KWS dataset
- Han Cai, Chuang Gan, Song Han, "[Once-for-All: Train One Network and Specialize it for Efficient Deployment](https://arxiv.org/abs/1908.09791)" (ICLR 2020)
- Ji Lin, Wei-Ming Chen, Han Cai, et al., "[MCUNet: Deep Learning on IoT Devices without Offloading](https://arxiv.org/abs/2007.10319)" (NeurIPS 2020) and "[MCUNetV2: Memory-Efficient Patch-based Inference for Fast Object Detection on TinyML Devices](https://arxiv.org/abs/2110.15352)" (2021)
- [Ambiq Apollo4 product family](https://ambiq.com/apollo4-plus/) — the most efficient TinyML-class MCU in production
- [Arm Cortex-M4 instruction set summary](https://developer.arm.com/documentation/dui0552/a/The-Cortex-M4-Instruction-Set) — note the absence of a native int8 dot-product on M4

## Cross-References

- [Edge Inference](./edge-inference.md) — broader edge runtime landscape
- [Quantization-Aware Training](./quantization-aware-training.md) — int8 training details
- [Model Compression](./model-compression.md) — pruning, distillation, low-rank
- [Edge ML](./edge.md) — overview page
