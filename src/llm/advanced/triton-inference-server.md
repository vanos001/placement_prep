# NVIDIA Triton Inference Server

Triton Inference Server is NVIDIA's open-source inference serving system, designed for production deployment of deep learning models on NVIDIA GPUs. Originally known as "TensorRT Inference Server" (renamed Triton in 2019), it supports multiple model formats (TensorRT, ONNX, PyTorch, TensorFlow, OpenVINO, Python) and provides a unified gRPC and HTTP API. This page covers the architecture, the model repository, the dynamic batching, and the production deployment patterns.

## The Architecture

```text
┌────────────────────────────────────────────────────────────────┐
│  Triton Server (single process per node)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Model Repository (on-disk layout)                        │  │
│  │  - One model per directory                                │  │
│  │  - Config (config.pbtxt) + weights                        │  │
│  │  - Multiple versions per model                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Model Instance Manager                                  │  │
│  │  - Loads model instances per GPU                          │  │
│  │  - Manages concurrent execution                            │  │
│  │  - Supports multiple instances per model for parallelism  │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Dynamic Batcher                                          │  │
│  │  - Collects incoming requests                             │  │
│  │  - Batches by max batch size or max time                  │  │
│  │  - Reduces per-request overhead                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────────────────────────────┐
│  HTTP/gRPC API                                                 │
└────────────────────────────────────────────────────────────────┘
```

## The Model Repository

Triton's model repository is a directory structure:

```text
/model_repository/
├── resnet50/
│   ├── config.pbtxt                ← model configuration
│   ├── 1/                          ← version 1
│   │   └── model.plan              ← TensorRT engine
│   ├── 2/                          ← version 2 (newer)
│   │   └── model.onnx
│   └── labels.txt                  ← class labels
├── bert-base-uncased/
│   ├── config.pbtxt
│   └── 1/
│       ├── model.pt
│       └── vocab.txt
└── ...
```

Each model has a `config.pbtxt` configuration file:

```text
name: "resnet50"
platform: "tensorrt_plan"
max_batch_size: 64
input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [3, 224, 224]
  }
]
output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [1000]
  }
]
dynamic_batching {
  preferred_batch_size: [4, 8, 16, 32, 64]
  max_queue_delay_microseconds: 100000
}
```

The `max_batch_size` enables batching; `dynamic_batching` configures how requests are batched (preferred sizes, max queue time).

## Model Format Support

Triton supports multiple model formats via "backends":

| Backend | Format | Notes |
|---------|--------|-------|
| `tensorrt_plan` | TensorRT engine | Highest performance on NVIDIA |
| `onnxruntime` | ONNX | Cross-platform, runs on CPU/GPU |
| `pytorch` (libtorch) | PyTorch TorchScript | Production PyTorch deployment |
| `tensorflow` (saved_model) | TensorFlow | Production TF deployment |
| `python` | Python script | Custom logic, pre/post-processing |
| `fil` | RAPIDS Forest Inference Library | GPU-accelerated tree models (XGBoost, LightGBM) |
| `openvino` | Intel OpenVINO | Intel hardware |
| `tensorrt_llm` | TensorRT-LLM engine | LLM serving (extension) |

A single Triton instance can serve multiple models of different formats — useful for pipelines that combine a CNN feature extractor (TensorRT), a Python preprocessor (Python), and an XGBoost classifier (FIL).

## Dynamic Batching

Triton's dynamic batcher collects incoming requests and batches them:

```text
Time:    0    1    2    3    4
Req 1:   arrives at t=0
Req 2:   arrives at t=1
Req 3:   arrives at t=2
Req 4:   arrives at t=2.5

Triton waits for:
  - Either 64 requests (preferred batch size), OR
  - 100 ms since the first request arrived.

At t=2.5 (4 requests received, 100ms timer), Triton batches:
  Requests [1, 2, 3, 4] → single GPU kernel execution with batch=4.
```

For ResNet50 with batch=64, the GPU time is ~3 ms; with batch=4, ~2 ms. So batching 4 requests costs ~2 ms (vs. 4 × 3 ms = 12 ms unbatched). Throughput gain: ~6×.

The dynamic batcher's tuning:
- `preferred_batch_size`: sizes the batcher prefers (it waits for one of these).
- `max_queue_delay_microseconds`: maximum wait time (defaults to no wait).
- `preserve_ordering`: ensure in-order responses (slightly slower).

## Model Instance Parallelism

Triton can load multiple instances of the same model on different GPUs:

```text
GPU 0: resnet50 (instance 1)
GPU 1: resnet50 (instance 2)
GPU 2: bert-base (instance 1)
GPU 3: bert-base (instance 2)
```

Each instance is independent; the scheduler load-balances requests across instances. This is critical for high-throughput: a single GPU can only do ~1K inferences/sec for ResNet50, but with 4 instances on 4 GPUs, throughput scales to ~4K/sec.

```text
instance_group [
  {
    kind: KIND_GPU
    count: 4
    gpus: [0, 1, 2, 3]
  }
]
```

## Production Deployment Patterns

### Pattern 1: Single-Model Server

Run one model per Triton instance. Simple, predictable performance.

```bash
tritonserver --model-repository=/models --http-port=8000 --grpc-port=8001
```

### Pattern 2: Multi-Model Pipeline

Multiple models in one Triton instance, with a Python backend for orchestration:

```text
Request → Preprocess (Python) → ResNet50 (TensorRT) → Postprocess (Python) → Response
```

The Python backend can call other models via Triton's internal API, keeping all computation on the GPU.

### Pattern 3: LLM Serving via TensorRT-LLM

For LLM serving, Triton integrates with TensorRT-LLM as a backend:

```text
Triton (Python backend) ↔ TensorRT-LLM (engine)
```

Triton handles the HTTP/gRPC API, batching, and load balancing; TensorRT-LLM handles the model execution.

### Pattern 4: Multi-Node Deployment

Multiple Triton instances behind a load balancer (e.g., NGINX):

```text
LB → Triton (GPU 0)
LB → Triton (GPU 1)
LB → Triton (GPU 2)
LB → Triton (GPU 3)
```

Each Triton instance is independent; the LB routes requests. No shared state.

## Production Performance

Triton's published performance on H100 SXM (80 GB):

| Model | Format | Batch | Throughput | Latency |
|-------|--------|------:|-----------:|--------:|
| ResNet50 | TensorRT | 64 | 10K inferences/sec | 6 ms |
| ResNet50 | ONNX Runtime | 64 | 7K inferences/sec | 9 ms |
| BERT-base | TensorRT | 32 | 5K inferences/sec | 6 ms |
| BERT-base | PyTorch | 32 | 3K inferences/sec | 11 ms |
| Llama-2 70B | TensorRT-LLM FP8 | 256 | 3200 tokens/sec | 50 ms |

For Llama-2 70B with TensorRT-LLM, Triton's throughput matches a direct TensorRT-LLM server — Triton's overhead is <5%.

## Comparison to vLLM and SGLang

| Aspect | Triton | vLLM | SGLang |
|--------|--------|------|--------|
| Model focus | All DL (vision, NLP, ...) | LLM only | LLM only |
| Multi-model | Yes (one server, many models) | No (one model per server) | No |
| Dynamic batching | Yes (TensorRT-style) | Yes (continuous batching) | Yes (continuous batching) |
| LLM serving | Via TensorRT-LLM backend | Native | Native |
| Production maturity | 5+ years | 2 years | 1 year |
| Production users | NVIDIA ecosystem, many | Many (Anthropic, Cohere, ...) | Many |

For multi-model deployment (vision + LLM), Triton is the standard. For LLM-only, vLLM/SGLang are simpler.

## Common Pitfalls

1. **Forgetting to set `max_batch_size`.** Default is 0 (no batching), which gives poor throughput. Always set `max_batch_size` based on the model's expected traffic.

2. **Forgetting to load multiple instances.** A single instance per model underutilizes the GPU. Load 4 instances on a 4-GPU server.

3. **Forgetting that dynamic batching can add latency.** A small batch with high `max_queue_delay` waits 100 ms for the batch to fill. Tune `max_queue_delay` based on latency SLO.

4. **Forgetting that model updates can cause downtime.** Reloading a model after a repository update takes seconds. Use `--model-control-mode=explicit` for managed updates.

5. **Forgetting to handle metric collection.** Triton exposes Prometheus metrics at `/metrics`. Configure the Prometheus exporter to scrape.

6. **Forgetting that the model repository can be on shared storage.** NFS or S3 for multi-node Triton deployments — all instances see the same models. Use `--model-control-mode=poll` for auto-reload.

## References

- [Triton Inference Server documentation](https://docs.nvidia.com/deeplearning/triton-inference-server/)
- [Triton GitHub repository](https://github.com/triton-inference-server/server)
- [Triton model configuration](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/protocol/extension_auto_complete.html)
- [Triton metrics (Prometheus)](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/metrics.html)
- [Triton + TensorRT-LLM integration](https://github.com/triton-inference-server/tensorrtllm_backend)
- [Triton Python backend](https://github.com/triton-inference-server/python_backend)
- [LWN: Triton for production ML serving (2023)](https://lwn.net/Articles/926655/)
