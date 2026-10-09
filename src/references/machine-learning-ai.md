# Machine Learning, Deep Learning & AI Reference Library

This page is a verified index of primary sources for machine learning & ai: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Frameworks, model hubs, GPU kernels and ML compilers, distributed training, inference serving, MLOps tooling, and a two-track path from building backpropagation by hand to reading vLLM and writing Triton kernels.

**89 entries** across 7 categories, plus **57 education & reference-implementation resources** (25 basic / 32 advanced), plus **22 video resources** and **8 conference sources**.

Every link HTTP-verified on **2026-10-07**.

> Google devsite properties (tensorflow.org, ai.google.dev) redirect automated clients to an authentication page; they load normally in a browser.

## Contents

- [1. Core frameworks](#1-core-frameworks) — 9
- [2. Models, hubs & transformer libraries](#2-models-hubs--transformer-libraries) — 9
- [3. GPU compute, kernels & compilers](#3-gpu-compute-kernels--compilers) — 9
- [4. Training at scale & inference serving](#4-training-at-scale--inference-serving) — 9
- [5. Experiment tracking, data & orchestration](#5-experiment-tracking-data--orchestration) — 6
- [6. Fine-tuning, evaluation, retrieval & RL](#6-fine-tuning-evaluation-retrieval--rl) — 16
- [7. Research papers & open-access literature](#7-research-papers--open-access-literature) — 31
- [Education & reference implementations](#education--reference-implementations) — 57 (25 basic / 32 advanced)
- [Video courses, channels & talks](#video-courses-channels--talks) — 22
- [Conference videos, notes & archives](#conference-videos-notes--archives) — 8


## 1. Core frameworks

### PyTorch

- **Docs:** [pytorch.org/docs/stable/index.html](https://pytorch.org/docs/stable/index.html)
- **Developer / API:** [pytorch.org/tutorials](https://pytorch.org/tutorials/)
- **Source:** [github.com/pytorch/pytorch](https://github.com/pytorch/pytorch)
- **SDKs & repos:** torchvision, torchaudio, torchtune, TorchServe; C++ and Python APIs
- **Downloadable / offline:** Docs built per release and downloadable; source tree cloneable
- *Note:* The research default. `torch.compile` and the dispatcher are where the interesting engineering is — see also the PL/compilers index.

### TensorFlow

- **Docs:** [tensorflow.org/api_docs](https://www.tensorflow.org/api_docs)
- **Developer / API:** [tensorflow.org](https://www.tensorflow.org/)
- **Source:** [github.com/tensorflow/tensorflow](https://github.com/tensorflow/tensorflow)
- **SDKs & repos:** Keras, TFX, TF Lite / LiteRT, TensorFlow.js, TF Serving
- **Downloadable / offline:** API docs per version
- *Note:* Still dominant in some production and mobile settings. Google's devsite redirects automated clients to an auth page; loads fine in a browser.

### JAX

- **Docs:** [docs.jax.dev/en/latest](https://docs.jax.dev/en/latest/)
- **Source:** [github.com/jax-ml/jax](https://github.com/jax-ml/jax)
- **SDKs & repos:** Flax, Optax, Haiku, Equinox; XLA backend
- **Downloadable / offline:** Sphinx docs
- *Note:* Composable transforms (`grad`, `jit`, `vmap`, `pmap`) over NumPy semantics. The cleanest mental model of autodiff in any framework.

### Keras

- **Docs:** [keras.io/api](https://keras.io/api/)
- **Developer / API:** [keras.io/guides](https://keras.io/guides/)
- **Source:** [github.com/keras-team/keras](https://github.com/keras-team/keras)
- **SDKs & repos:** Backend-agnostic across TensorFlow, JAX and PyTorch since Keras 3
- **Downloadable / offline:** Docs site

### scikit-learn

- **Docs:** [scikit-learn.org/stable/user_guide.html](https://scikit-learn.org/stable/user_guide.html)
- **Developer / API:** [scikit-learn.org/stable/modules/classes.html](https://scikit-learn.org/stable/modules/classes.html)
- **Source:** [github.com/scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn)
- **SDKs & repos:** Pipelines, model selection, preprocessing
- **Downloadable / offline:** User guide downloadable as PDF
- *Note:* The user guide is a genuinely good free textbook on classical ML, not just API reference.

### XGBoost

- **Docs:** [xgboost.readthedocs.io](https://xgboost.readthedocs.io/)
- **Developer / API:** [xgboost.readthedocs.io/en/stable/python](https://xgboost.readthedocs.io/en/stable/python/)
- **Source:** [github.com/dmlc/xgboost](https://github.com/dmlc/xgboost)
- **SDKs & repos:** Python, R, JVM, Julia; GPU training
- **Downloadable / offline:** Sphinx docs
- *Note:* Still the thing to beat on tabular data. Try it before any deep model on structured problems.

### LightGBM

- **Docs:** [lightgbm.readthedocs.io](https://lightgbm.readthedocs.io/)
- **Developer / API:** [lightgbm.readthedocs.io/en/…](https://lightgbm.readthedocs.io/en/stable/Python-API.html)
- **Source:** [github.com/microsoft/LightGBM](https://github.com/microsoft/LightGBM)
- **SDKs & repos:** Python, R, C API
- **Downloadable / offline:** Sphinx docs

### PyTorch Lightning

- **Docs:** [lightning.ai/docs/pytorch/stable](https://lightning.ai/docs/pytorch/stable/)
- **Source:** [github.com/Lightning-AI/pytorch-lightning](https://github.com/Lightning-AI/pytorch-lightning)
- **SDKs & repos:** Training loop abstraction, distributed strategies
- **Downloadable / offline:** Docs site

### fastai

- **Docs:** [docs.fast.ai](https://docs.fast.ai/)
- **Source:** [github.com/fastai/fastai](https://github.com/fastai/fastai)
- **SDKs & repos:** Layered API over PyTorch
- **Downloadable / offline:** Docs site
- *Note:* The library and the course are designed together; use both or neither.


## 2. Models, hubs & transformer libraries

### Hugging Face

- **Docs:** [huggingface.co/docs](https://huggingface.co/docs)
- **Developer / API:** [huggingface.co/docs/api-inference/index](https://huggingface.co/docs/api-inference/index)
- **Source:** [github.com/huggingface](https://github.com/huggingface)
- **SDKs & repos:** transformers, datasets, tokenizers, accelerate, peft, trl, diffusers
- **Downloadable / offline:** All docs per library; models and datasets downloadable
- *Note:* The de facto model distribution layer for the field. The `transformers` source is also the best cross-architecture reference for how models are actually implemented.

### Transformers

- **Docs:** [huggingface.co/docs/transformers/index](https://huggingface.co/docs/transformers/index)
- **Source:** [github.com/huggingface/transformers](https://github.com/huggingface/transformers)
- **SDKs & repos:** Thousands of model implementations in a consistent structure
- **Downloadable / offline:** Docs site
- *Note:* Read `modeling_llama.py` to see a modern decoder implemented plainly.

### Diffusers

- **Docs:** [huggingface.co/docs/diffusers/index](https://huggingface.co/docs/diffusers/index)
- **Source:** [github.com/huggingface/diffusers](https://github.com/huggingface/diffusers)
- **SDKs & repos:** Diffusion pipelines, schedulers, training scripts
- **Downloadable / offline:** Docs site

### OpenAI API

- **Docs:** [platform.openai.com/docs](https://platform.openai.com/docs)
- **Developer / API:** [platform.openai.com/docs/api-reference](https://platform.openai.com/docs/api-reference)
- **Source:** [github.com/openai](https://github.com/openai)
- **SDKs & repos:** Python and Node SDKs; Agents SDK; Realtime API
- **Downloadable / offline:** Docs site

### Anthropic / Claude API

- **Docs:** [docs.claude.com/en/home](https://docs.claude.com/en/home)
- **Developer / API:** [docs.claude.com/en/api/getting-started](https://docs.claude.com/en/api/getting-started)
- **Source:** [github.com/anthropics](https://github.com/anthropics)
- **SDKs & repos:** Python, TypeScript SDKs; Agent SDK; MCP
- **Downloadable / offline:** Docs site
- *Note:* The prompt-engineering and tool-use sections are unusually substantive.

### Google Gemini API

- **Docs:** [ai.google.dev](https://ai.google.dev/)
- **Developer / API:** [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)
- **Source:** [github.com/google-gemini](https://github.com/google-gemini)
- **SDKs & repos:** Python, JS, Go SDKs; Vertex AI for enterprise
- **Downloadable / offline:** Docs site
- *Note:* Google devsite redirects bots to an auth page; fine in a browser.

### Mistral AI

- **Docs:** [docs.mistral.ai](https://docs.mistral.ai/)
- **Developer / API:** [docs.mistral.ai/api](https://docs.mistral.ai/api/)
- **Source:** [github.com/mistralai](https://github.com/mistralai)
- **SDKs & repos:** Python and JS clients; open-weight models on Hugging Face
- **Downloadable / offline:** Docs site

### Llama

- **Docs:** [llama.com/docs/overview](https://www.llama.com/docs/overview/)
- **Source:** [github.com/meta-llama](https://github.com/meta-llama)
- **SDKs & repos:** Open-weight models; llama-stack, llama-recipes
- **Downloadable / offline:** Docs site; weights downloadable under licence

### Ollama

- **Docs:** [docs.ollama.com](https://docs.ollama.com/)
- **Developer / API:** [docs.ollama.com/api](https://docs.ollama.com/api)
- **Source:** [github.com/ollama/ollama](https://github.com/ollama/ollama)
- **SDKs & repos:** Local model runner with an OpenAI-compatible API
- **Downloadable / offline:** Docs site
- *Note:* The simplest way to run open-weight models locally.


## 3. GPU compute, kernels & compilers

### CUDA

- **Docs:** [docs.nvidia.com/cuda](https://docs.nvidia.com/cuda/)
- **Developer / API:** [developer.nvidia.com/cuda-toolkit](https://developer.nvidia.com/cuda-toolkit)
- **Source:** [github.com/NVIDIA/cuda-samples](https://github.com/NVIDIA/cuda-samples)
- **SDKs & repos:** cuBLAS, cuDNN, CUTLASS, Nsight, Thrust
- **Downloadable / offline:** Programming Guide and Best Practices Guide as PDFs
- *Note:* The CUDA C++ Programming Guide is the foundational document for GPU performance work.

### cuDNN

- **Docs:** [docs.nvidia.com/deeplearning/cudnn](https://docs.nvidia.com/deeplearning/cudnn/)
- **Developer / API:** [developer.nvidia.com/cudnn](https://developer.nvidia.com/cudnn)
- **SDKs & repos:** Primitive library under most frameworks
- **Downloadable / offline:** Docs + PDF

### Triton (OpenAI)

- **Docs:** [triton-lang.org/main/index.html](https://triton-lang.org/main/index.html)
- **Developer / API:** [triton-lang.org/main/…](https://triton-lang.org/main/getting-started/tutorials/index.html)
- **Source:** [github.com/triton-lang/triton](https://github.com/triton-lang/triton)
- **SDKs & repos:** Python-embedded GPU kernel language
- **Downloadable / offline:** Docs + tutorial series
- *Note:* Write fused kernels without writing CUDA. The tutorials are the fastest route into GPU kernel thinking.

### TensorRT

- **Docs:** [docs.nvidia.com/deeplearning/tensorrt](https://docs.nvidia.com/deeplearning/tensorrt/)
- **Developer / API:** [developer.nvidia.com/tensorrt](https://developer.nvidia.com/tensorrt)
- **Source:** [github.com/NVIDIA/TensorRT](https://github.com/NVIDIA/TensorRT)
- **SDKs & repos:** Inference optimizer; TensorRT-LLM for language models
- **Downloadable / offline:** Docs + PDF

### OpenXLA / XLA

- **Docs:** [openxla.org/xla](https://openxla.org/xla)
- **Source:** [github.com/openxla/xla](https://github.com/openxla/xla)
- **SDKs & repos:** Compiler backend for JAX and TensorFlow; StableHLO
- **Downloadable / offline:** Docs site
- *Note:* Read alongside MLIR — XLA is one of the best-documented production ML compilers.

### MLIR

- **Docs:** [mlir.llvm.org](https://mlir.llvm.org/)
- **Developer / API:** [mlir.llvm.org/docs](https://mlir.llvm.org/docs/)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** Multi-level IR infrastructure underpinning most modern ML compilers
- **Downloadable / offline:** Docs site
- *Note:* Part of LLVM. See the PL/compilers index for context.

### Apache TVM

- **Docs:** [tvm.apache.org/docs](https://tvm.apache.org/docs/)
- **Source:** [github.com/apache/tvm](https://github.com/apache/tvm)
- **SDKs & repos:** Compiler stack targeting CPUs, GPUs and accelerators
- **Downloadable / offline:** Docs per version

### ONNX

- **Docs:** [onnx.ai/onnx](https://onnx.ai/onnx/)
- **Developer / API:** [onnx.ai/onnx/intro](https://onnx.ai/onnx/intro/)
- **Source:** [github.com/onnx/onnx](https://github.com/onnx/onnx)
- **SDKs & repos:** Model interchange format; operator spec
- **Downloadable / offline:** Spec in-repo
- *Note:* Read the operator spec when debugging export problems — most issues are unsupported ops.

### ONNX Runtime

- **Docs:** [onnxruntime.ai/docs](https://onnxruntime.ai/docs/)
- **Developer / API:** [onnxruntime.ai/docs/api](https://onnxruntime.ai/docs/api/)
- **Source:** [github.com/microsoft/onnxruntime](https://github.com/microsoft/onnxruntime)
- **SDKs & repos:** Cross-platform inference with execution providers
- **Downloadable / offline:** Docs site


## 4. Training at scale & inference serving

### DeepSpeed

- **Docs:** [deepspeed.ai](https://www.deepspeed.ai/)
- **Developer / API:** [deepspeed.readthedocs.io](https://deepspeed.readthedocs.io/)
- **Source:** [github.com/deepspeedai/DeepSpeed](https://github.com/deepspeedai/DeepSpeed)
- **SDKs & repos:** ZeRO sharding, pipeline parallelism, offloading
- **Downloadable / offline:** Docs + tutorials
- *Note:* The ZeRO papers and the matching code are the clearest explanation of memory-efficient distributed training.

### Megatron-LM

- **Docs:** [github.com/NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM)
- **Source:** [github.com/NVIDIA/Megatron-LM](https://github.com/NVIDIA/Megatron-LM)
- **SDKs & repos:** Tensor, pipeline and sequence parallelism
- **Downloadable / offline:** In-repo docs + papers
- *Note:* The reference implementation of tensor parallelism.

### Ray Train

- **Docs:** [docs.ray.io/en/latest/train/train.html](https://docs.ray.io/en/latest/train/train.html)
- **Developer / API:** [docs.ray.io/en/latest](https://docs.ray.io/en/latest/)
- **Source:** [github.com/ray-project/ray](https://github.com/ray-project/ray)
- **SDKs & repos:** Distributed training, tuning and serving on one substrate
- **Downloadable / offline:** Docs site

### vLLM

- **Docs:** [docs.vllm.ai/en/latest](https://docs.vllm.ai/en/latest/)
- **Source:** [github.com/vllm-project/vllm](https://github.com/vllm-project/vllm)
- **SDKs & repos:** PagedAttention, continuous batching, OpenAI-compatible server
- **Downloadable / offline:** Docs site
- *Note:* The current default for serving open-weight LLMs. The PagedAttention design is worth reading as a systems idea.

### llama.cpp

- **Docs:** [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- **Source:** [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)
- **SDKs & repos:** GGML/GGUF; CPU and Metal inference; quantization
- **Downloadable / offline:** In-repo docs
- *Note:* Readable C++ and the best practical education in quantization available.

### NVIDIA Triton Inference Server

- **Docs:** [docs.nvidia.com/deeplearning/…](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/)
- **Source:** [github.com/triton-inference-server/server](https://github.com/triton-inference-server/server)
- **SDKs & repos:** Multi-framework serving
- **Downloadable / offline:** Docs site
- *Note:* Unrelated to OpenAI's Triton kernel language, despite the name.

### TorchServe

- **Docs:** [pytorch.org/serve](https://pytorch.org/serve/)
- **Source:** [github.com/pytorch/serve](https://github.com/pytorch/serve)
- **SDKs & repos:** PyTorch model serving
- **Downloadable / offline:** Docs site

### BentoML

- **Docs:** [docs.bentoml.com/en/latest](https://docs.bentoml.com/en/latest/)
- **Source:** [github.com/bentoml/BentoML](https://github.com/bentoml/BentoML)
- **SDKs & repos:** Packaging and serving framework
- **Downloadable / offline:** Docs site

### KServe

- **Docs:** [kserve.github.io/website](https://kserve.github.io/website/)
- **Source:** [github.com/kserve/kserve](https://github.com/kserve/kserve)
- **SDKs & repos:** Kubernetes-native model serving
- **Downloadable / offline:** Docs site


## 5. Experiment tracking, data & orchestration

### MLflow

- **Docs:** [mlflow.org/docs/latest](https://mlflow.org/docs/latest/)
- **Developer / API:** [mlflow.org/docs/latest/api_reference](https://mlflow.org/docs/latest/api_reference/)
- **Source:** [github.com/mlflow/mlflow](https://github.com/mlflow/mlflow)
- **SDKs & repos:** Tracking, model registry, projects, evaluation
- **Downloadable / offline:** Docs site
- *Note:* Open-source and self-hostable, which matters more than it sounds.

### Weights & Biases

- **Docs:** [docs.wandb.ai](https://docs.wandb.ai/)
- **Developer / API:** [docs.wandb.ai/ref](https://docs.wandb.ai/ref/)
- **Source:** [github.com/wandb/wandb](https://github.com/wandb/wandb)
- **SDKs & repos:** Experiment tracking, sweeps, artifacts
- **Downloadable / offline:** Docs site

### DVC

- **Docs:** [dvc.org/doc](https://dvc.org/doc)
- **Developer / API:** [dvc.org/doc/api-reference](https://dvc.org/doc/api-reference)
- **Source:** [github.com/iterative/dvc](https://github.com/iterative/dvc)
- **SDKs & repos:** Git-based data and model versioning
- **Downloadable / offline:** Docs site

### Kubeflow

- **Docs:** [kubeflow.org/docs](https://www.kubeflow.org/docs/)
- **Source:** [github.com/kubeflow/kubeflow](https://github.com/kubeflow/kubeflow)
- **SDKs & repos:** ML workflows on Kubernetes
- **Downloadable / offline:** Docs site

### LangChain

- **Docs:** [python.langchain.com/docs/introduction](https://python.langchain.com/docs/introduction/)
- **Developer / API:** [python.langchain.com/api_reference](https://python.langchain.com/api_reference/)
- **Source:** [github.com/langchain-ai/langchain](https://github.com/langchain-ai/langchain)
- **SDKs & repos:** Python and JS; LangGraph for stateful agents
- **Downloadable / offline:** Docs site

### LlamaIndex

- **Docs:** [docs.llamaindex.ai/en/stable](https://docs.llamaindex.ai/en/stable/)
- **Developer / API:** [docs.llamaindex.ai/en/stable/api_reference](https://docs.llamaindex.ai/en/stable/api_reference/)
- **Source:** [github.com/run-llama/llama_index](https://github.com/run-llama/llama_index)
- **SDKs & repos:** Retrieval and indexing over private data
- **Downloadable / offline:** Docs site


## 6. Fine-tuning, evaluation, retrieval & RL

### PEFT

- **Docs:** [huggingface.co/docs/peft](https://huggingface.co/docs/peft)
- **Source:** [github.com/huggingface/peft](https://github.com/huggingface/peft)
- **SDKs & repos:** LoRA, QLoRA, prefix tuning, adapters
- **Downloadable / offline:** Docs site
- *Note:* Parameter-efficient fine-tuning is how most people actually adapt models. Read the LoRA docs before the paper.

### TRL

- **Docs:** [huggingface.co/docs/trl](https://huggingface.co/docs/trl)
- **Source:** [github.com/huggingface/trl](https://github.com/huggingface/trl)
- **SDKs & repos:** SFT, DPO, GRPO, PPO trainers for language models
- **Downloadable / offline:** Docs site
- *Note:* Reference implementations of the alignment methods, readable and runnable.

### Unsloth

- **Docs:** [docs.unsloth.ai](https://docs.unsloth.ai/)
- **Source:** [github.com/unslothai/unsloth](https://github.com/unslothai/unsloth)
- **SDKs & repos:** Memory- and speed-optimized fine-tuning with hand-written Triton kernels
- **Downloadable / offline:** Docs + free Colab notebooks
- *Note:* The kernels are worth reading if you want to see Triton used for real work.

### Axolotl

- **Docs:** [docs.axolotl.ai](https://docs.axolotl.ai/)
- **Source:** [github.com/axolotl-ai-cloud/axolotl](https://github.com/axolotl-ai-cloud/axolotl)
- **SDKs & repos:** Config-driven fine-tuning across many model families
- **Downloadable / offline:** Docs site

### FlashAttention

- **Docs:** [github.com/Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention)
- **Source:** [github.com/Dao-AILab/flash-attention](https://github.com/Dao-AILab/flash-attention)
- **SDKs & repos:** IO-aware exact attention; now standard in nearly every training stack
- **Downloadable / offline:** In-repo docs + papers
- *Note:* The clearest demonstration that memory movement, not FLOPs, is the real constraint. Read the paper with the CUDA.

### SGLang

- **Docs:** [docs.sglang.ai](https://docs.sglang.ai/)
- **Source:** [github.com/sgl-project/sglang](https://github.com/sgl-project/sglang)
- **SDKs & repos:** High-throughput LLM serving with RadixAttention prefix caching
- **Downloadable / offline:** Docs site
- *Note:* The main alternative to vLLM. Comparing their scheduling designs is instructive.

### TensorRT-LLM

- **Docs:** [nvidia.github.io/TensorRT-LLM](https://nvidia.github.io/TensorRT-LLM/)
- **Source:** [github.com/NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM)
- **SDKs & repos:** NVIDIA’s optimized LLM inference library
- **Downloadable / offline:** Docs site

### lm-evaluation-harness

- **Docs:** [github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- **Source:** [github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
- **SDKs & repos:** The standard framework behind most published LLM benchmark numbers
- **Downloadable / offline:** In-repo docs
- *Note:* If you want to know what a reported score actually measured, read the task definition here.

### FAISS

- **Docs:** [faiss.ai](https://faiss.ai/)
- **Developer / API:** [github.com/facebookresearch/faiss/wiki](https://github.com/facebookresearch/faiss/wiki)
- **Source:** [github.com/facebookresearch/faiss](https://github.com/facebookresearch/faiss)
- **SDKs & repos:** Similarity search and clustering of dense vectors; GPU support
- **Downloadable / offline:** Docs site + wiki
- *Note:* The index-selection guide in the wiki is the practical reference for vector search.

### Sentence Transformers

- **Docs:** [sbert.net](https://sbert.net/)
- **Developer / API:** [sbert.net/docs/package_reference](https://sbert.net/docs/package_reference/)
- **Source:** [github.com/UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers)
- **SDKs & repos:** Embedding and reranking models with a consistent API
- **Downloadable / offline:** Docs site

### Gymnasium

- **Docs:** [gymnasium.farama.org](https://gymnasium.farama.org/)
- **Developer / API:** [gymnasium.farama.org/api/env](https://gymnasium.farama.org/api/env/)
- **Source:** [github.com/Farama-Foundation/Gymnasium](https://github.com/Farama-Foundation/Gymnasium)
- **SDKs & repos:** The maintained successor to OpenAI Gym; the standard RL environment API
- **Downloadable / offline:** Docs site

### CleanRL

- **Docs:** [docs.cleanrl.dev](https://docs.cleanrl.dev/)
- **Source:** [github.com/vwxyzjn/cleanrl](https://github.com/vwxyzjn/cleanrl)
- **SDKs & repos:** Single-file implementations of RL algorithms with logged benchmark runs
- **Downloadable / offline:** Docs site
- *Note:* Every algorithm in one readable file, with reproduced results. The best way to actually understand an RL algorithm.

### Stable-Baselines3

- **Docs:** [stable-baselines3.readthedocs.io](https://stable-baselines3.readthedocs.io/)
- **Source:** [github.com/DLR-RM/stable-baselines3](https://github.com/DLR-RM/stable-baselines3)
- **SDKs & repos:** Reliable reference RL implementations in PyTorch
- **Downloadable / offline:** Sphinx docs

### Flax

- **Docs:** [flax.readthedocs.io](https://flax.readthedocs.io/)
- **Source:** [github.com/google/flax](https://github.com/google/flax)
- **SDKs & repos:** Neural network library for JAX
- **Downloadable / offline:** Sphinx docs

### Optax

- **Docs:** [optax.readthedocs.io](https://optax.readthedocs.io/)
- **Source:** [github.com/google-deepmind/optax](https://github.com/google-deepmind/optax)
- **SDKs & repos:** Composable gradient transformations and optimizers for JAX
- **Downloadable / offline:** Sphinx docs
- *Note:* Reading Optax is the clearest way to understand what an optimizer actually does.

### Mojo

- **Docs:** [docs.modular.com/mojo](https://docs.modular.com/mojo/)
- **Developer / API:** [docs.modular.com/mojo/manual](https://docs.modular.com/mojo/manual/)
- **Source:** [github.com/modular/modular](https://github.com/modular/modular)
- **SDKs & repos:** Python-superset language targeting ML hardware via MLIR
- **Downloadable / offline:** Docs site
- *Note:* Early, and genuinely interesting as a language-design attempt. See the PL/compilers index for the MLIR context.


## 7. Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### arXiv cs.LG / cs.CL / cs.CV

- **Docs:** [arxiv.org/list/cs.LG/recent](https://arxiv.org/list/cs.LG/recent)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Machine learning, computational linguistics and computer vision. See also [arxiv.org/list/cs.CL/recent](https://arxiv.org/list/cs.CL/recent), [arxiv.org/list/cs.CV/recent](https://arxiv.org/list/cs.CV/recent) and [arxiv.org/list/stat.ML/recent](https://arxiv.org/list/stat.ML/recent)
- **Downloadable / offline:** Free; API and bulk access
- *Note:* Volume is overwhelming — hundreds of papers daily. Use curation (Hugging Face Papers, alphaXiv, Lil'Log) rather than reading the firehose.

### Papers with Code

- **Docs:** [paperswithcode.com](https://paperswithcode.com/)
- **SDKs & repos:** Papers linked to implementations, with benchmark leaderboards by task
- **Downloadable / offline:** Free; datasets and results available in bulk
- *Note:* The leaderboards are useful for orientation but gameable — check whether the comparison is fair before believing a ranking.

### Hugging Face Papers

- **Docs:** [huggingface.co/papers](https://huggingface.co/papers)
- **SDKs & repos:** Daily curated arXiv selection with community discussion and linked model weights
- **Downloadable / offline:** Free
- *Note:* The most practical daily filter on the arXiv firehose, because papers are linked to runnable artifacts.

### NeurIPS Proceedings

- **Docs:** [papers.nips.cc](https://papers.nips.cc/)
- **SDKs & repos:** Every NeurIPS paper since 1987
- **Downloadable / offline:** All free PDFs, plus supplementary material
- *Note:* Fully open archive going back nearly four decades.

### PMLR

- **Docs:** [proceedings.mlr.press](https://proceedings.mlr.press/)
- **SDKs & repos:** Proceedings of Machine Learning Research — ICML, AISTATS, CoLLAs, UAI and more
- **Downloadable / offline:** 100% open access
- *Note:* If it was published at ICML, it is free here. No exceptions.

### JMLR

- **Docs:** [jmlr.org](https://www.jmlr.org/)
- **SDKs & repos:** Journal of Machine Learning Research
- **Downloadable / offline:** Open access since 2000
- *Note:* Longer, more rigorous papers than the conference venues. Founded specifically as an open-access protest.

### ACL Anthology

- **Docs:** [aclanthology.org](https://aclanthology.org/)
- **Source:** [github.com/acl-org/acl-anthology](https://github.com/acl-org/acl-anthology)
- **SDKs & repos:** Every NLP paper from ACL, EMNLP, NAACL, COLING and more — 100,000+ papers
- **Downloadable / offline:** All free; full BibTeX and metadata dumps in the repo
- *Note:* The model open-access archive. Complete, searchable, and permanently free.

### CVF Open Access

- **Docs:** [openaccess.thecvf.com/menu](https://openaccess.thecvf.com/menu)
- **SDKs & repos:** CVPR, ICCV, WACV papers in full
- **Downloadable / offline:** All free
- *Note:* The entire computer vision conference output, openly hosted.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **SDKs & repos:** ICLR, NeurIPS and others with full review threads
- **Downloadable / offline:** Free; API
- *Note:* Read the reviews. For contested papers this is more informative than the paper.

### MLCommons / MLPerf

- **Docs:** [mlcommons.org/benchmarks](https://mlcommons.org/benchmarks/)
- **SDKs & repos:** Standardised training and inference benchmarks with audited submissions
- **Downloadable / offline:** Free results and rules
- *Note:* The only ML performance numbers with a credible verification process behind them.

### Google Research publications

- **Docs:** [research.google/pubs](https://research.google/pubs/)
- **SDKs & repos:** Transformers, BERT, TPU architecture, MapReduce, Spanner
- **Downloadable / offline:** Free PDFs
- *Note:* Search here before arXiv for anything Google-originated.

### Microsoft Research publications

- **Docs:** [microsoft.com/en-us/research/publications](https://www.microsoft.com/en-us/research/publications/)
- **SDKs & repos:** DeepSpeed, ZeRO, Phi models, systems and PL work
- **Downloadable / offline:** Free PDFs

### Apple Machine Learning Research

- **Docs:** [machinelearning.apple.com/research](https://machinelearning.apple.com/research)
- **SDKs & repos:** On-device ML, efficiency, privacy-preserving methods
- **Downloadable / offline:** Free

### Amazon Science

- **Docs:** [amazon.science/publications](https://www.amazon.science/publications)
- **SDKs & repos:** Applied ML and large-scale systems
- **Downloadable / offline:** Free

### Lil'Log

- **Docs:** [lilianweng.github.io](https://lilianweng.github.io/)
- **SDKs & repos:** Long-form technical surveys of research areas
- **Downloadable / offline:** Free
- *Note:* Usually the best single explainer on a topic, with full citations. Start here before the primary papers.

### Distill

- **Docs:** [distill.pub](https://distill.pub/)
- **Source:** [github.com/distillpub](https://github.com/distillpub)
- **SDKs & repos:** Interactive visual explanations of ML concepts
- **Downloadable / offline:** Free, archived
- *Note:* No longer publishing, but the back catalogue remains the high-water mark for explaining ML visually.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*25 resources across 5 topics.*


#### Build it from scratch first

- **[Neural Networks: Zero to Hero (Karpathy)](https://karpathy.ai/zero-to-hero.html)** — Build backpropagation, then a language model, then GPT — on video, in order, from nothing. The best free introduction to deep learning that exists.
- **[micrograd](https://github.com/karpathy/micrograd)** — An autograd engine in roughly 100 lines. Read every line; autodiff stops being magic.
- **[nanoGPT](https://github.com/karpathy/nanoGPT)** — A GPT you can train yourself and actually read. ~300 lines of model code.
- **[nn-zero-to-hero repo](https://github.com/karpathy/nn-zero-to-hero)** — The notebooks accompanying the video series.


#### Structured courses

- **[fast.ai Practical Deep Learning](https://course.fast.ai/)** — Top-down: get working models first, derive theory later. Free, and effective for people who learn by doing.
- **[Stanford CS231n](https://cs231n.stanford.edu/)** — Computer vision and CNNs. Notes and assignments public; the notes remain among the clearest written.
- **[Stanford CS224n](https://web.stanford.edu/class/cs224n/)** — NLP with deep learning. Slides and assignments public.
- **[Stanford CS229](https://cs229.stanford.edu/)** — Classical machine learning done properly. The lecture notes are a standalone reference.
- **[MIT Introduction to Deep Learning](https://introtodeeplearning.com/)** — A compact bootcamp with all lectures and labs free.
- **[Hugging Face courses](https://huggingface.co/learn)** — Free courses on NLP, diffusion, RL, audio and agents, each with runnable notebooks.


#### Books, free and complete

- **[Dive into Deep Learning (d2l.ai)](https://d2l.ai/)** — Interactive book with runnable code in PyTorch, TensorFlow and JAX. Used as a textbook at 500+ universities.
- **[Deep Learning (Goodfellow et al.)](https://www.deeplearningbook.org/)** — Free online. The theory reference, though now dated on architectures.
- **[Probabilistic Machine Learning (Murphy)](https://probml.github.io/pml-book/)** — Free PDFs. The modern successor to the classical statistical ML texts.
- **[scikit-learn user guide](https://scikit-learn.org/stable/user_guide.html)** — A free textbook on classical ML hiding inside API documentation.


#### The libraries to learn first

- **[PyTorch tutorials](https://pytorch.org/tutorials/)** — Start with the 60-minute blitz, then the training loop from scratch.
- **[PyTorch docs](https://pytorch.org/docs/stable/index.html)** — Learn to read these rather than searching for examples.
- **[scikit-learn](https://scikit-learn.org/stable/user_guide.html)** — Do not skip classical ML. Most real problems are still tabular.
- **[XGBoost](https://xgboost.readthedocs.io/)** — On structured data this is still frequently the right answer.
- **[Hugging Face Transformers](https://huggingface.co/docs/transformers/index)** — The practical path to using pretrained models.
- **[Ollama](https://docs.ollama.com/)** — Run open-weight models on your own machine in one command.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*32 resources across 6 topics.*


#### Graduate coursework

- **[Stanford CS336 — Language Modeling from Scratch](https://stanford-cs336.github.io/spring2025/)** — Build a language model end to end: tokenizer, architecture, training, systems, alignment. The most relevant advanced course currently public.
- **[Stanford CS224n](https://web.stanford.edu/class/cs224n/)** — Later lectures cover current architectures and training practice.
- **[Stanford CS231n](https://cs231n.stanford.edu/)** — Assignment 3 and the notes on optimization remain worthwhile.
- **[OpenAI Spinning Up in Deep RL](https://spinningup.openai.com/en/latest/)** — The best-structured free entry into reinforcement learning, with clean reference implementations.
- **[Probabilistic Machine Learning](https://probml.github.io/pml-book/)** — For the theory under modern methods, including the advanced volume.


#### Read production model code

- **[Transformers source](https://github.com/huggingface/transformers)** — Every major architecture in one consistent structure. Unmatched as a comparative reference.
- **[nanoGPT](https://github.com/karpathy/nanoGPT)** — Return to it after reading production code; the minimal version clarifies the essentials.
- **[Diffusers](https://github.com/huggingface/diffusers)** — Schedulers and pipelines for diffusion models, readable.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** — Quantization, GGUF, and CPU inference — a systems education in C++.
- **[vLLM](https://github.com/vllm-project/vllm)** — PagedAttention and continuous batching; a genuinely novel systems contribution.


#### GPU kernels & performance

- **[Triton tutorials](https://triton-lang.org/main/index.html)** — Write fused GPU kernels in Python. Work through the matmul and attention tutorials.
- **[CUDA Programming Guide](https://docs.nvidia.com/cuda/)** — The memory hierarchy and occupancy chapters determine most real performance.
- **[CUDA samples](https://github.com/NVIDIA/cuda-samples)** — Reference kernels to compare your own against.
- **[cuDNN docs](https://docs.nvidia.com/deeplearning/cudnn/)** — What the primitives underneath your framework actually do.
- **[TensorRT](https://docs.nvidia.com/deeplearning/tensorrt/)** — Inference-side graph optimization and precision calibration.


#### ML compilers & intermediate representations

- **[OpenXLA / XLA](https://openxla.org/xla)** — Operator fusion and layout assignment, documented properly.
- **[MLIR](https://mlir.llvm.org/)** — The dialect infrastructure under most modern ML compilers. Also read the PL/compilers index.
- **[Apache TVM](https://tvm.apache.org/docs/)** — Autotuning and codegen for heterogeneous targets.
- **[ONNX operator spec](https://onnx.ai/onnx/)** — Read the spec when export breaks — it usually will.
- **[ONNX Runtime](https://onnxruntime.ai/docs/)** — Execution providers and graph optimizations.


#### Distributed training

- **[DeepSpeed](https://www.deepspeed.ai/)** — ZeRO stages 1-3 and offloading, with papers alongside the code.
- **[Megatron-LM](https://github.com/NVIDIA/Megatron-LM)** — Tensor and pipeline parallelism, reference implementation.
- **[PyTorch distributed docs](https://pytorch.org/docs/stable/index.html)** — FSDP, DDP and the collective primitives underneath.
- **[Ray Train](https://docs.ray.io/en/latest/train/train.html)** — Orchestration across the cluster; see the distributed-systems index too.
- **[JAX](https://docs.jax.dev/en/latest/)** — `pmap`, `shard_map` and explicit sharding give the clearest model of parallelism in any framework.


#### Keeping current & research

- **[arXiv cs.LG](https://arxiv.org/list/cs.LG/recent)** — Where the field publishes first. Unfiltered, so pair with curation.
- **[Papers with Code](https://paperswithcode.com/)** — Papers linked to implementations and benchmark tables.
- **[Lil'Log (Lilian Weng)](https://lilianweng.github.io/)** — Long-form technical surveys; usually the best single explainer on a new topic.
- **[Distill.pub](https://distill.pub/)** — Archived but still the high-water mark for visual explanation of ML concepts.
- **[NeurIPS](https://neurips.cc/)** — Proceedings free.
- **[ICML](https://icml.cc/)** — Proceedings free.
- **[ICLR](https://iclr.cc/)** — Reviews are public on OpenReview — reading them teaches you how the field evaluates work.


---

## Video courses, channels & talks

*22 resources across 2 groups.* Every channel and playlist below was fetched and title-verified on **2026-10-09**. Handles drift and several plausible-looking handles resolve to the wrong channel, so a 200 response is not proof of identity — the links here were each checked against the channel title.

### Channels & conference recordings

- **[Andrej Karpathy](https://www.youtube.com/@AndrejKarpathy)** — The best free depth available: backprop, transformers and GPT built from scratch on camera.
- **[Two Minute Papers](https://www.youtube.com/@TwoMinutePapers)** — Fast paper coverage; headlines overstate, so read the abstract before you cite.
- **[Yannic Kilcher](https://www.youtube.com/@YannicKilcher)** — Long-form paper reviews — literature depth you will not get from a blog.
- **[3Blue1Brown](https://www.youtube.com/@3blue1brown)** — Visual linear algebra and calculus — the maths prerequisite for all of ML.
- **[StatQuest](https://www.youtube.com/@StatQuest)** — The clearest intuition available for the statistics that ML assumes.
- **[DeepLearning.AI](https://www.youtube.com/@DeepLearningAI)** — Short courses run by Andrew Ng & co.; vendor-leaning, verify against the papers.
- **[Hugging Face](https://www.youtube.com/@HuggingFace)** — The open LLM ecosystem: transformers, datasets, agents, tool calling.
- **[PyTorch](https://www.youtube.com/@PyTorch)** — Official PyTorch tutorials and PyTorch Conference talks.
- **[TensorFlow](https://www.youtube.com/@TensorFlow)** — Official TensorFlow channel — dev summit talks and tutorials.
- **[OpenAI](https://www.youtube.com/@OpenAI)** — Model releases and DevDay talks; primary for API and product behaviour.
- **[Google DeepMind](https://www.youtube.com/@GoogleDeepMind)** — Research overviews and model announcements from DeepMind.
- **[sentdex](https://www.youtube.com/@sentdex)** — Applied Python ML/NLP walkthroughs; solid for getting something running.
- **[ICML](https://www.youtube.com/@ICMLConf)** — Official ICML channel; plenaries and tutorials, coverage varies by year.
- **[ICLR](https://www.youtube.com/@ICLR)** — Channel titled simply "Iclr" — check the video against the conference site before citing it.
- **[The CVF](https://www.youtube.com/@TheCVF)** — The Computer Vision Foundation: CVPR/ICCV material, fully open access.
- **[Latent Space](https://www.youtube.com/@LatentSpacePod)** — Long-form practitioner interviews; the fastest way to find out what people are actually shipping.
- **[TWIML AI Podcast](https://www.youtube.com/@twimlai)** — Interview archive going back years; uneven, occasionally excellent.
- **[Google TechTalks](https://www.youtube.com/@GoogleTechTalks)** — Foundational ML talks by the authors of the papers you are reading.

### Lectures & playlists

- **[Let's build GPT: from scratch, in code, spelled out](https://www.youtube.com/watch?v=kCc8FmEb1nY)** — Karpathy builds a GPT end-to-end in two hours; the single best ML video here.
- **[Essence of linear algebra](https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab)** — the prerequisite series for every ML index below.
- **[Essence of calculus](https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr)** — derivatives and backprop intuition in visual form.
- **[Stanford CS229 — Machine Learning (Autumn 2018)](https://www.youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU)** — Ng, complete, and still the clearest full-course treatment of the classical material.

*Note:* The only topic here where video is genuinely better than text for prerequisites; treat paper-summary channels as a discovery feed, never as a citation.

## Conference videos, notes & archives

*8 resources across 2 groups.* Conference recordings are the primary-source tier of video: the speaker is usually an author of the paper, and where a talk exists the proceedings entry is often open at the same link. Every URL here returned 200 on **2026-10-09** unless the note says otherwise.

ML publishes more open proceedings than any other field here — and more video of people explaining other people's papers, which is not the same thing.

### Conference channels & video archives

- **[NeurIPS proceedings](https://neurips.cc/Conferences/2025)** — Every paper, with links to the authors' sites; video coverage varies by year.
- **[CVF Open Access](https://openaccess.thecvf.com/)** — CVPR/ICCV/WACV papers with supplementary video — fully open, the model the other venues should copy.
- **[FOSDEM video archive](https://video.fosdem.org/)** — AI/ML and data devrooms; small but free.
- **[MLSys](https://mlsys.org/)** — The ML-systems conference: open proceedings, and the venue for the engineering half of ML (serving, compilation, distributed training).
- **[CVPR 2026](https://cvpr.thecvf.com/)** — Conference site for the vision flagship; papers and supplementary video via the CVF open-access portal above.
- **[KDD](https://www.kdd.org/)** — The applied data-science conference; proceedings partly open, tutorials often published.
- **[EMNLP 2026](https://2026.emnlp.org/)** — The NLP venue; papers in the ACL Anthology, recordings inconsistent.

### Notes, proceedings & paper-adjacent archives

- **[Hugging Face Papers](https://huggingface.co/papers)** — Daily trending papers with discussion attached; the fastest discovery feed, and a mediocre archive.

## If you only do three things

1. **Watch Karpathy's Zero to Hero in order** and type the code yourself. micrograd, then makemore, then GPT.
2. **Read nanoGPT completely** (~300 lines), then read `modeling_llama.py` in Transformers. That gap is production ML.
3. **Do the Triton tutorials.** Once you can write a fused kernel, framework performance stops being a black box.

## Honest notes

- **Do not skip classical ML.** Most real problems are tabular, and XGBoost still beats deep models on them regularly.
- **Two different things are called Triton**: OpenAI's GPU kernel language and NVIDIA's inference server. They are unrelated.
- **JAX gives the clearest mental model** of autodiff and parallelism, even if you ship PyTorch.
- **The `transformers` source is better architecture documentation than most papers** — one consistent structure across hundreds of models.
- **The Goodfellow book is still good on fundamentals and dated on architectures.** Use it for theory, not for current practice.
- **Check framework version in any documentation you read.** This ecosystem deprecates faster than any other in this series.

---

## Related sections of this book

- [Machine Learning & AI](../ml/overview.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other topic indexes
