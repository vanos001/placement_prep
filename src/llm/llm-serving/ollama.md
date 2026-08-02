# Ollama

## Overview

Ollama is a lightweight tool for running LLMs locally. It provides a simple CLI and API for downloading, managing, and running models. Ollama uses the GGUF format (from llama.cpp) and is optimized for consumer hardware (CPU and consumer GPUs). It's the go-to tool for local LLM development and testing.

## Key Features

| Feature | Description |
|---|---|
| **Simple CLI** | `ollama run llama3` to start chatting |
| **Model management** | Download, list, remove models easily |
| **GGUF quantization** | Run 7B models on 8GB RAM |
| **API** | OpenAI-compatible REST API |
| **Modelfile** | Docker-like model configuration |
| **Cross-platform** | macOS, Linux, Windows |
| **GPU support** | Metal (macOS), CUDA (NVIDIA), ROCm (AMD) |

## Installation

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Or download from ollama.com
```

## Usage

### CLI

```bash
# Download and run a model
ollama run llama3

# List downloaded models
ollama list

# Pull a model without running
ollama pull mistral

# Remove a model
ollama rm llama3

# Show model info
ollama show llama3
```

### API

```bash
# Chat completion (OpenAI-compatible)
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# Text generation
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3", "prompt": "Hello!"}'
```

### Python

```python
import requests

response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "llama3",
        "messages": [{"role": "user", "content": "Hello!"}],
    },
)
print(response.json()["choices"][0]["message"]["content"])
```

## Modelfile

Similar to a Dockerfile, defines model configuration:

```
FROM llama3

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

SYSTEM You are a helpful Python programming assistant.

TEMPLATE """{{ if .System }}<|system|>
{{ .System }}<|end|>
{{ end }}{{ if .Prompt }}<|user|>
{{ .Prompt }}<|end|>
{{ end }}<|assistant|>
{{ .Response }}<|end|>
"""
```

```bash
# Create custom model
ollama create myassistant -f Modelfile
ollama run myassistant
```

## Quantization Levels

| Quant | Bits | 7B Size | 13B Size | Quality | Use Case |
|---|---|---|---|---|---|
| Q4_0 | 4.5 | 4.0 GB | 7.4 GB | Good | Standard |
| Q4_K_M | 4.8 | 4.3 GB | 7.9 GB | Good | Recommended |
| Q5_K_M | 5.7 | 5.1 GB | 9.5 GB | Very good | Quality focus |
| Q6_K | 6.6 | 5.9 GB | 10.9 GB | Excellent | Near-lossless |
| Q8_0 | 8.5 | 7.2 GB | 13.3 GB | Lossless | Quality maximum |

## Resource Requirements

| Model | Minimum RAM | Recommended RAM | GPU VRAM |
|---|---|---|---|
| 7B (Q4) | 8 GB | 16 GB | 6 GB |
| 13B (Q4) | 16 GB | 32 GB | 10 GB |
| 70B (Q4) | 64 GB | 128 GB | 48 GB |

## Interview Questions

### Q1: How does Ollama differ from vLLM?
**Answer:**
- **Ollama**: Local-first, simple CLI, GGUF format, CPU+GPU, no batching optimization, for development/testing
- **vLLM**: Production-grade, PagedAttention, continuous batching, FP16/GPTQ/AWQ, for production serving
- Use Ollama for development, vLLM for production.

### Q2: What is GGUF and why does Ollama use it?
**Answer:** GGUF (GPT-Generated Unified Format) is the model format from llama.cpp. It supports various quantization levels (Q2-Q8), runs on CPU and consumer GPUs, and is self-contained (single file with metadata). Ollama uses GGUF because it's optimized for consumer hardware, supports many quantization levels, and has a large ecosystem of pre-quantized models.

## Common Mistakes

- ❌ Using Ollama for production serving (no continuous batching)
- ❌ Not checking available RAM before pulling large models
- ❌ Confusing Ollama (tool) with llama.cpp (library it's built on)

## Summary

Ollama is the simplest way to run LLMs locally. It wraps llama.cpp with a user-friendly CLI and API, supports GGUF quantization for consumer hardware, and is ideal for development and testing. For production, use vLLM or TensorRT-LLM instead.

## Cross-References

- [Quantization →](quantization.md) GGUF format details
- [Systems Overview →](systems.md) Comparison with other systems
- [vLLM →](vllm.md) Production alternative
