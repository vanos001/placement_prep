# Quantization-Aware Training and Post-Training Quantization

Quantization maps continuous `fp32` weights and activations to a small grid of integers — typically `int8` over `[−128, 127]` (signed) or `[0, 255]` (unsigned). The win is mechanical: an `int8` matmul is 4× smaller in memory and ~3–4× faster than `fp32` on modern CPUs (and far more on NPUs and GPUs with int8 tensor cores). The loss is accuracy: rounding `0.314` to `0` throws away information, and rounding errors compound through a deep network.

Two paths recover that accuracy. **Post-Training Quantization (PTQ)** quantises an already-trained model — fast, no training needed, but degrades 1–5% on hard models (transformers with small activation ranges, recurrent nets). **Quantization-Aware Training (QAT)** inserts "fake quantisation" operators into the training graph so the model learns to be accurate *after* quantisation. QAT recovers nearly all the accuracy gap, at the cost of one full training run.

This chapter is about the mechanics: what fake-quantising actually does, how PTQ calibration chooses scales, and the three production int8 inference paths (TFLite, ONNX Runtime, TensorRT).

## The Quantization Operator

Linear symmetric quantisation (the simplest, what QAT in PyTorch uses by default for weights) maps an `fp32` tensor `x` to an `int8` `q`:

```text
q = clamp( round(x / s), -128, 127 )      s = max|x| / 127
```

For asymmetric activations (e.g. ReLU outputs, always ≥ 0), the unsigned scheme with a zero-point is more efficient:

```text
q = clamp( round(x / s) + z, 0, 255 )
    s = (max(x) - min(x)) / 255     z = -round(min(x) / s)
```

The scale `s` and zero-point `z` are stored alongside the quantised tensor; at inference, the operation `q → x̂ = s · (q − z)` reconstructs an approximation. The key Jacob et al. (CVPR 2018) insight is to *fold the scale into the next layer's bias*: a `conv → bn → relu` can be quantised so the input scale of one layer exactly cancels the output scale of the previous, leaving a single int8 multiply-accumulate per layer.

## Post-Training Quantization

PTQ runs the trained `fp32` model on a small (100–1000 example) "calibration" dataset, observes the activation ranges, picks a `(s, z)` per tensor, and bakes them into the model. No gradient descent, no training-data labels — just forward passes.

### Choosing the range: calibration methods

Three standard schemes:

| Method | What it does | When |
|---|---|---|
| **Min-max** | `(s, z)` from the literal min and max of the observed activation | simplest; very noisy if any single outlier exists |
| **Percentile** (e.g. 99.9%) | discard the top 0.1% tail before computing min/max | standard for transformers; robust to a few wild activations |
| **KL divergence** (entropy) | pick the `(s, z)` that minimises KL divergence between the original fp32 distribution and the dequantised int8 distribution | TensorRT's default for CNNs; best accuracy at slightly more compute |
| **MSE** | minimise mean squared reconstruction error of activations | used by ONNX Runtime's calibration options |

Min-max is almost always wrong for transformers: the softmax output of one in a million tokens can be `[0.99999, …]`, blowing up the range and quantising every other output to `0`. Percentile calibration is the default in `pytorch/ao` and `optimum` for transformer PTQ.

### Bias correction

Even with perfect scales, the *mean* of the quantised activation differs from the fp32 mean by up to half a scale step. *Bias correction* (Banner et al., 2019, "Post-Training 4-Bit Quantization of Convolutional Networks") adds the observed mean error to the layer's bias term, removing systematic drift. Most production PTQ pipelines apply this for free; it is a one-line addition after calibration.

### Code: ONNX Runtime dynamic + static PTQ

```python
import onnxruntime as ort
from onnxruntime.quantization import (
    quantize_dynamic, quantize_static, QuantFormat, QuantType,
    CalibrationDataReader, CalibrationMethod,
)

# Dynamic PTQ: weights only; activations quantised at runtime from their live range
quantize_dynamic("model_fp32.onnx", "model_int8_dynamic.onnx",
                 weight_type=QuantType.QInt8,
                 op_types_to_quantize=["MatMul", "Gemm", "Conv"])

# Static PTQ: weights + activations; needs calibration data
class RandomCalibReader(CalibrationDataReader):
    def __init__(self, n=200):
        self.data = [{"input": np.random.randn(*input_shape).astype(np.float32)}
                     for _ in range(n)]
        self.iter = iter(self.data)
    def get_next(self):
        return next(self.iter, None)

quantize_static("model_fp32.onnx", "model_int8_static.onnx",
                RandomCalibReader(),
                format=QuantFormat.QOperator,
                per_channel=True,                          # per-output-channel weight scales
                activation_type=QuantType.QUInt8,          # asymmetric activations
                weight_type=QuantType.QInt8,               # symmetric weights
                calibrate_method=CalibrationMethod.Percentile)
```

Static PTQ is what you ship. Dynamic PTQ is a fallback when you cannot collect representative calibration data — common for LLMs where the input distribution is open-ended.

### Per-channel vs per-tensor

Per-tensor: one `s, z` for the whole weight matrix. Per-channel: one `s` per output channel (256 of them for a typical conv). Per-channel costs a few bytes of extra storage and `O(out_ch)` extra multiplies per layer — negligible — and recovers most of the accuracy gap from per-tensor. **Always use per-channel for weights.** Activations stay per-tensor (they are dynamic; storing per-channel scales for every activation would explode memory).

## Quantization-Aware Training

PTQ's failure mode is *compounding rounding error*: a 50-layer network with 1% error per layer accumulates to ~50% error at the output. QAT fixes this by *training in the quantised regime*. The trick is the **fake-quantisation** operator:

```text
FakeQuant(x, s, z) = Dequant(Quant(x, s, z), s, z)
                  = s · clamp(round(x/s + z), qmin, qmax) - s·z
```

It looks like an identity but with a *staircase*: each value is snapped to its nearest grid point. The forward pass is the quantised forward pass — exactly what inference will compute. The backward pass uses the **straight-through estimator (STE)** (Bengio et al., 2013): gradients flow through `round()` as if it were the identity. Formally:

```text
∂FakeQuant(x)/∂x = 1   if x ∈ [qmin·s, qmax·s]
                   0   otherwise    (clipping: gradient is 0 outside the range)
```

So QAT does two things during training:

1. The forward pass already sees quantisation noise — the model learns weights that *quantise well*, not just weights that fit in fp32.
2. The backward pass pushes weights into the range where the STE gradient is non-zero — i.e. weights that, when quantised, stay inside the grid. This is why QAT models have a noticeably narrower weight distribution than fp32 models.

### The fake-quantised training step

```python
import torch.ao.quantization as qt

# 1. Insert fake-quant observers into the model
model_fp32.train()
qat_model = qt.prepare_qat(model_fp32,
                           qt.get_default_qat_qconfig('fbgemm'),  # x86 backend
                           inplace=True)

# 2. Train normally — observers track activation ranges, fake-quant
#    operators round every forward pass
for epoch in range(num_epochs):
    for x, y in train_loader:
        logits = qat_model(x)         # fake-quantised forward
        loss = F.cross_entropy(logits, y)
        loss.backward()
        optimizer.step()
        # Observers silently collect min/max; in epoch 1 they "warm up"
        # and fake-quant ranges are initialised from collected stats.

# 3. Convert to real int8 (observers -> scales, fake-quants -> real quants)
model_int8 = qt.convert(qat_model.eval(), inplace=False)
# model_int8 now runs on the int8 kernels (FBGEMM on x86, QNNPACK on ARM)
```

The observers measure activation ranges during the warmup epoch and fix `(s, z)` from those ranges; from then on, every forward pass quantises. At `convert()` time, the observers are replaced with real `(s, z)` constants, the fake-quant nodes disappear, and the graph runs on the int8 kernels.

### The Jacob et al. (2018) inference path

Jacob et al.'s CVPR 2018 paper ("Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference") is the basis for TFLite's int8 path. The key transformation folds:

```text
Conv:    y  = W · x + b        (fp32)
BN:      y' = γ · (y - μ)/σ + β
ReLU:    y'' = max(0, y')

After folding:
   W' = γ · W / sqrt(σ² + ε)   -- folded into the weights (now int8)
   b' = (b - μ) · γ / σ + β    -- folded into the bias (kept in int32)
   y_int8 = int8_conv(W_int8, x_int8, scale_out/scale_x/scale_w)
   y'' = ReLU(scale_out · y_int8)
```

The convolution runs entirely in `int8` with `int32` accumulator; only the bias add (in `int32`) and the rescale to the next layer's int8 happen at the edges. TFLite's int8 ops follow this schema; the operator exposes `(input_scale, weight_scale, output_scale)` triples and the runtime emits a single `int8 → int8` op with no fp32 inside the hot loop.

### The accuracy / latency trade-off

| Scheme | Top-1 on ImageNet (ResNet-50, fp32 baseline 76.1%) | Latency on Cortex-A53 |
|---|---|---|
| fp32 | 76.1% | 1.0× (baseline) |
| PTQ per-tensor | 74.6% | 3.2× |
| PTQ per-channel | 75.9% | 3.2× |
| QAT per-channel | 76.0% | 3.2× |
| PTQ int4 | 65.0% | 5.5× |
| QAT int4 | 73.2% | 5.5× |

PTQ with per-channel scales recovers most of the fp32 accuracy on CNNs. QAT is what makes int4 viable at all (PTQ int4 is unusable). For transformers, the same pattern holds but the gap is bigger — BERT-base fp32 → int8 PTQ loses ~1% F1 on GLUE; QAT recovers to within 0.2%.

Latency-wise, the int8 path is 3–4× faster on ARM with NEON dot-product instructions, 4–6× on x86 with AVX-VNNI, 6–8× on NVIDIA Tensor Cores. Going int4 is barely faster than int8 on current CPUs (no native int4 matmul); it is mostly a memory-bandwidth win for LLMs.

## The Three Production Inference Paths

### TFLite int8 (Android, embedded, micro)

TFLite's FlatBuffer format stores quantised weights as `int8`, scales as `float32`, and zero-points as `int32`. The interpreter dispatches to:

- **x86**: FBGEMM kernels (fast AVX-VNNI int8 GEMM).
- **ARM Cortex-A**: QNNPACK / XNNPACK with NEON dot-product (`SDOT`).
- **ARM Cortex-M**: reference kernels (no vectorisation; TFLite Micro strips even those — see [TinyML](./tinyml.md)).
- **Android NNAPI / Hexagon HVX**: delegated to the vendor driver.

The converter applies Jacob-style folding automatically:

```python
import tensorflow as tf

converter = tf.lite.TFLiteConverter.from_saved_model("model/")
converter.optimizations = [tf.lite.Optimize.DEFAULT]   # int8 PTQ
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type  = tf.int8
converter.inference_output_type = tf.int8
converter.representative_dataset = calibration_data_gen   # required for static PTQ
open("model_int8.tflite", "wb").write(converter.convert())
```

### ONNX Runtime int8 (cross-platform, server, Windows)

ONNX Runtime quantises the ONNX graph in-place: `MatMul` nodes are replaced with `MatMulInteger` (taking two int8 tensors, two scales, two zero-points), `Conv` becomes `ConvInteger`. The QDQ (QuantizeDequantize) format inserts explicit `QuantizeLinear` / `DequantizeLinear` nodes, which lets the runtime fuse them with adjacent ops — preferable to QOperator format when you target multiple EPs (CPU, CUDA, TensorRT EP).

```python
# Static PTQ with QDQ format, per-channel weights, KL-divergence calibration
from onnxruntime.quantization import quantize_static, QuantFormat, CalibrationMethod, QuantType

quantize_static("model_fp32.onnx", "model_int8.onnx",
    calibration_data_reader,
    format=QuantFormat.QDQ,
    activation_type=QuantType.QUInt8,
    weight_type=QuantType.QInt8,
    per_channel=True,
    calibrate_method=CalibrationMethod.Entropy,    # KL-divergence
    op_types_to_quantize=["MatMul", "Conv", "Gemm", "Add"])
```

The CUDA EP runs `MatMulInteger` on tensor cores when the shapes fit; otherwise falls back to fp16 + dequant. The TensorRT EP additionally fuses conv-bn-relu and uses TensorRT's own int8 path.

### TensorRT int8 (NVIDIA GPUs)

TensorRT's int8 path is the most aggressive fuser of the three. You supply a *calibration cache* (the `scales` for each tensor, computed once), and TRT builds a fully-fused int8 engine: conv + bn + relu + bias-add become one CUDA kernel; tensor-core int8 matmul is used where shapes permit. TRT offers the same three calibration methods as ONNX RT (min-max, entropy=KL, percentile); the default `EntropyCalibrator2` is what most people use.

```cpp
// Pseudocode: build an int8 TensorRT engine
nvinfer1::IBuilder* b = createInferBuilder(logger);
auto* config = b->createBuilderConfig();
config->setFlag(nvinfer1::BuilderFlag::kINT8);  // enable int8
config->setInt8Calibrator(new MyEntropyCalibrator2(calib_data));
// MyEntropyCalibrator2 streams batches; TRT calls writeCalibrationCache()
auto* engine = b->buildEngineWithConfig(*network, *config);
// engine->enqueue(...) runs int8 inference
```

The QAT-compatible path in TRT 8+ is "QDQ → TRT": if your ONNX model has explicit `QuantizeLinear`/`DequantizeLinear` nodes (i.e. it went through QAT export), TRT uses *those* scales verbatim and skips its own calibrator. This is the recommended path for transformer models: do QAT in PyTorch, export to ONNX with explicit QDQ nodes, build TRT engine — no TRT-side calibration needed.

## Common Pitfalls

1. **Forgetting to calibrate.** PTQ with no `representative_dataset` silently falls back to dynamic quantisation; you ship an "int8" model that dequantises every activation to fp32 and runs at half the speedup.
2. **Calibrating on the wrong distribution.** If you calibrate on ImageNet-train and ship on a different visual domain (medical, satellite), the activation ranges are wrong. Use a representative slice of production traffic.
3. **Mixing QAT and PTQ.** If you QAT-trained a model and then run PTQ on top, you will get *worse* accuracy than QAT alone — the QAT scales are already optimal. Convert directly from QAT export.
4. **Per-tensor weights on transformers.** Attention softmax has occasional saturations to 1.0; per-tensor weight scales blow up the range and quantise everything else to 0. Always per-channel.
5. **Expecting int8 to make your model faster on an old CPU.** AVX-VNNI (the int8 dot-product instruction) only exists on Cascade Lake Xeons (2019+) and Ice Lake+. Older CPUs have AVX2 but the int8 path is no faster than fp32 — sometimes slower.

## When to Use QAT vs PTQ

- **Start with PTQ (per-channel, percentile calibration).** If the accuracy drop is < 1%, ship it.
- **If PTQ drops > 1% on a hard task, do QAT.** The cost is one training run; the gain is usually 2–4% accuracy recovery.
- **For int4, always QAT.** PTQ int4 is unusable except for very specific layers (e.g. LLM attention down-projection with AWQ).
- **For LLMs, prefer GPTQ / AWQ / GGUF** — these are PTQ methods specialised for transformer weight structure; see [quantization.md](./quantization.md).

## References

- Benoit Jacob, Skirmantas Kligys, Bo Chen, Menglong Zhu, Matthew Tang, Andrew Howard, Hartwig Adam, Dmitry Kalenichenko, "[Quantization and Training of Neural Networks for Efficient Integer-Arithmetic-Only Inference](https://arxiv.org/abs/1712.05877)" (CVPR 2018) — the canonical int8 quantization paper
- Markus Nagel, Martijn van Baalen, Tijmen Blankevoort, "[A White Paper on Neural Network Quantization](https://arxiv.org/abs/2106.08295)" (2021) — comprehensive Qualcomm/ARM survey
- Ron Banner, Yury Nahshan, Daniel Soudry, "[Post-Training 4-Bit Quantization of Convolutional Networks for Acceleration of Mobile Devices](https://arxiv.org/abs/1903.07066)" (2019) — bias correction
- Yoshua Bengio, Nicholas Léonard, Aaron Courville, "[Estimating or Propagating Gradients Through Stochastic Neurons for Conditional Computation](https://arxiv.org/abs/1308.3432)" (2013) — the straight-through estimator
- [TensorFlow Lite converter: integer quantization](https://www.tensorflow.org/lite/performance/quantization_spec)
- [ONNX Runtime quantization documentation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html)
- [NVIDIA TensorRT Developer Guide: INT8 Calibration](https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html#int8-calibration)
- [PyTorch Quantization-Aware Training tutorial](https://pytorch.org/tutorials/prototype/static_quantization_tutorial.html)

## Cross-References

- [Model Compression](./model-compression.md) — broader compression overview
- [Edge Inference](./edge-inference.md) — where int8 lands in deployment
- [TinyML](./tinyml.md) — int8 on microcontrollers
- [Quantization](./quantization.md) — companion LLM-focused page
