# Embedded AI & Edge Intelligence

## Overview

Embedded AI brings machine learning to resource-constrained devices—microcontrollers, system-on-chips, and mobile processors—enabling inference without cloud connectivity. This chapter covers the full spectrum from tinyML on 32-bit MCUs to full-scale autonomous vehicle compute stacks.

## Embedded ML & TinyML

**TinyML** is the practice of running ML models on microcontrollers with as little as 32 KB RAM and 256 KB flash. It requires aggressive optimization across the model and runtime stack:

### Model Optimization Pipeline

```
Full Model (Cloud) → Pruning → Quantization → Distillation → Compilation → MCU Binary
   (millions params)  (50%+ sparsity) (FP16→INT8)  (student model) (TFLM/CMSIS-NN)  (< 100 KB)
```

- **Pruning**: remove weights below a threshold; create structured sparsity for hardware acceleration
- **Quantization**: convert FP32 weights to INT8 or INT4 with minimal accuracy loss; post-training quantization (PTQ) vs. quantization-aware training (QAT)
- **Knowledge distillation**: train a small "student" model to mimic a larger "teacher"
- **Neural Architecture Search (NAS)**: automatically find efficient architectures for target hardware (e.g., TinyNAS, MCUNet)

### TinyML Frameworks

| Framework | Target | Key Feature |
|-----------|--------|-------------|
| TensorFlow Lite Micro | ARM Cortex-M, RISC-V | XNNPACK delegate, CMSIS-NN integration |
| Edge Impulse SDK | Wide MCU support | AutoML pipeline, EON tuner for memory-constrained targets |
| STM32Cube.AI | STM32 MCUs | Optimized for STM32 hardware with quantization tooling |
| Apache TVM Micro | Various | Compiler-driven optimization, ahead-of-time compilation |
| MicroTVM | Bare metal | Target-specific code generation for custom accelerators |

## MCU Inference & Hardware Accelerators

Modern MCUs integrate specialized hardware for ML workloads:

- **ARM Cortex-M55/M85**: Helium vector extension (MVE) for SIMD ML operations, up to 4.8x speedup over M4
- **DSP extensions**: multiply-accumulate (MAC) operations for convolution layers
- **Custom accelerators**: Google Edge TPU (Coral), Hailo-8 (26 TOPS/W), Syntiant NDP100 (always-on voice)
- **FPGA-based**: Lattice iCE40, Xilinx Zynq for reconfigurable inference pipelines

Key metric: **TOPS/W (tera-operations per second per watt)**. Edge AI accelerators achieve 5–50 TOPS/W, compared to ~1 TOPS/W for desktop GPUs—because power budgets at the edge are measured in milliwatts, not watts.

## Energy-Aware Inference

Energy consumption, not just latency or accuracy, is the primary constraint for battery-powered edge AI:

### Energy Breakdown

```
Total Energy = (Computation Energy) + (Memory Access Energy) + (Communication Energy)

Memory access often dominates: reading a weight from SRAM costs ~100x more than a MAC operation.
```

Optimization strategies:

- **Operator fusion**: combine consecutive operations (conv + batchnorm + relu) to reduce memory traffic
- **Loop tiling**: keep data in on-chip SRAM rather than accessing external DRAM
- **Approximate computing**: skip inference on low-confidence inputs, use lower-precision for less important layers
- **Early exit networks**: branch architecture that exits at shallower layers for "easy" inputs

## Intermittent Computing & Energy Harvesting

Devices powered by energy harvesting (solar, vibration, thermal gradients) face **intermittent execution**—power may drop mid-computation, losing volatile state:

- **Checkpoint/restore**: periodically save processor state to non-volatile memory (FRAM, MRAM); restore on power recovery
- **Idempotent execution**: design computation so partial results can be safely discarded and recomputed
- **Task partitioning**: decompose work into power-budget-sized chunks

Research systems like **Alpaca** (intermittent computing with hardware support) and **Mementos** (programming model for intermittent execution) provide abstractions for these challenges.

## Wearable Computing

Wearables push energy-awareness further: continuous sensing (heart rate, SpO2, motion) with multi-day battery life:

- **Always-on inference**: wake-on-voice, fall detection, atrial fibrillation detection
- **Sensor hubs**: dedicated low-power coprocessors (e.g., Apple W-series, Qualcomm Sensing Hub) offload continuous sensor processing from the main CPU
- **On-device personalization**: fine-tune models locally with user data without sending data to the cloud (differential privacy, federated learning)

## Smart Cities

Smart city deployments aggregate edge AI across thousands of nodes:

- **Traffic management**: camera-based vehicle detection, pedestrian flow analysis, adaptive traffic signal control
- **Environmental monitoring**: air quality sensors with anomaly detection (predictive maintenance for sensors themselves)
- **Smart lighting**: adaptive brightness based on pedestrian presence, reducing energy consumption by 30–50%
- **Waste management**: fill-level sensors on dumpsters optimize collection routes

Architecture pattern: **hierarchical edge**—sensors report to neighborhood edge gateways, which aggregate and preprocess before forwarding to city-level edge nodes or cloud analytics.

## Connected Vehicles & V2X

**V2X (Vehicle-to-Everything)** communication enables vehicles to exchange information with other vehicles (V2V), infrastructure (V2I), pedestrians (V2P), and networks (V2N):

- **C-V2X**: cellular-based (3GPP Release 16+), using PC5 sidelink for direct vehicle-to-vehicle without base station
- **DSRC**: IEEE 802.11p-based, dedicated 5.9 GHz spectrum, mature but limited adoption
- **Messages**: BSM (Basic Safety Message), CAM (Cooperative Awareness Message), DENM (Decentralized Environmental Notification Message)

### Vehicular Edge Computing

Vehicular edge computing (VEC) leverages vehicles themselves as mobile edge nodes:

- **Computation offloading**: vehicles with spare compute assist others with heavier workloads
- **RSU-assisted edge**: Roadside Units (RSUs) provide localized processing for safety applications
- **Predictive handover**: pre-position content at edge nodes along a vehicle's predicted route

### Autonomous Vehicle Compute Stack

An autonomous vehicle's compute stack is one of the most demanding edge AI systems:

```
┌──────────────────────────────────────────────────────┐
│               Planning & Decision                    │
│    Path planning, behavior prediction, route search   │
├──────────────────────────────────────────────────────┤
│                  Perception                           │
│   Camera (multi-view), LiDAR 3D detection, radar       │
│   fusion, tracking, semantic segmentation             │
├──────────────────────────────────────────────────────┤
│               Sensor Processing                       │
│    Image signal processing, point cloud generation,   │
│    radar signal processing, GNSS/IMU integration       │
├──────────────────────────────────────────────────────┤
│                   Hardware                            │
│  NVIDIA Orin (254 TOPS), multiple GPUs/FPGAs,         │
│  safety island (lockstep MCU for ASIL-D functions)    │
└──────────────────────────────────────────────────────┘
```

Safety requirements: **ASIL-D** (Automotive Safety Integrity Level D) for critical functions—redundant compute paths, watchdog timers, lockstep processors. The "safety island" handles fail-safe operations even if the main compute stack fails.

Latency budget: perception → planning → actuation loop must complete in **10–100 ms** depending on vehicle speed. At 70 mph, 100 ms of latency means 3 meters of travel—critical for collision avoidance.

## Interview Angle

> **"How would you run a CNN on a microcontroller with 256 KB RAM?"**

Walk through: choose a small architecture (MobileNetV1 width multiplier 0.25 → ~250 KB params), quantize to INT8 (4x memory reduction → ~63 KB), use TensorFlow Lite Micro with CMSIS-NN for ARM-optimized kernels, partition inference into layers that fit in on-chip buffers, and benchmark latency/accuracy trade-offs. Mention that feature maps (activations) often consume more memory than weights, so operator fusion is critical.

> **"Design a smart traffic management system for a city with 5,000 intersections."**

Describe the hierarchical edge architecture: cameras at each intersection with on-device person/vehicle detection, neighborhood edge gateways aggregating data from ~50 intersections for corridor-level optimization, city-level edge for city-wide coordination, cloud for long-term analytics and model retraining. Address communication (fiber to neighborhood gateways, 5G to cameras), failure modes (local fallback when gateway fails), and cost optimization (adaptive frame rate based on traffic density).

## Key References

- "TinyML: Machine Learning with TensorFlow Lite on Arduino and Ultra-Low-Power Microcontrollers" (Warden & Situnayake)
- MCUNet/ TinyNAS (Lin et al., 2020)
- IEEE P2853 — Standard for Energy-Aware Machine Learning
- C-V2X: 3GPP TR 36.885, Release 16+
- ISO 26262 — Road vehicles Functional Safety
