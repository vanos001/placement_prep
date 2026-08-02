#!/usr/bin/env python3
"""Enhance existing cross-references by adding cross-section links."""
import os
import re

BASE = "/home/work/.openclaw/workspace/placement_prep/src"

# Cross-section links to add: relative_path -> list of (display_name, relative_link)
ENHANCEMENTS = {
    # ===== CONCURRENCY =====
    "concurrency/async-await.md": [
        ("LLM Batching", "../llm/llm-serving/batching.md"),
        ("Cloud Lambda", "../cloud/aws/lambda.md"),
        ("Futures", "./futures.md"),
    ],
    "concurrency/coroutines.md": [
        ("Go Channels", "./go-channels.md"),
        ("Python GIL", "./python-gil.md"),
        ("LLM Inference", "../llm/llm-serving/inference.md"),
    ],
    "concurrency/fork-join.md": [
        ("Thread Pools", "./thread-pools.md"),
        ("ML Training", "../ml/deep-learning/backpropagation.md"),
        ("Cloud Lambda", "../cloud/aws/lambda.md"),
    ],
    "concurrency/futures.md": [
        ("Async/Await", "./async-await.md"),
        ("Java Concurrency", "./java.md"),
        ("LLM Batching", "../llm/llm-serving/batching.md"),
    ],
    "concurrency/go-channels.md": [
        ("Producer-Consumer", "./producer-consumer.md"),
        ("Messaging Systems", "../interview/system-design/hld/messaging-systems.md"),
        ("Coroutines", "./coroutines.md"),
    ],
    "concurrency/java.md": [
        ("Interview LLD Concurrency", "../interview/system-design/lld/concurrency-design.md"),
        ("OS Synchronization", "../os/synchronization/mutex.md"),
        ("Lock-Free", "./lock-free.md"),
    ],
    "concurrency/lock-free.md": [
        ("CAS Operations", "../os/synchronization/cas.md"),
        ("Java Concurrency", "./java.md"),
        ("Storage Distributed", "../storage/distributed.md"),
    ],
    "concurrency/overview.md": [
        ("OS Processes", "../os/processes/zombie-orphan.md"),
        ("Thread Pools", "./thread-pools.md"),
        ("Interview System Design", "../interview/system-design/README.md"),
        ("Cloud Overview", "../cloud/overview.md"),
    ],
    "concurrency/producer-consumer.md": [
        ("Go Channels", "./go-channels.md"),
        ("Messaging Systems", "../interview/system-design/hld/messaging-systems.md"),
        ("LLM Batching", "../llm/llm-serving/batching.md"),
    ],
    "concurrency/python-gil.md": [
        ("ML Training", "../ml/deep-learning/backpropagation.md"),
        ("Coroutines", "./coroutines.md"),
        ("Thread Pools", "./thread-pools.md"),
    ],
    "concurrency/readers-writers.md": [
        ("OS Readers-Writers", "../os/synchronization/readers-writers.md"),
        ("DBMS Concurrency Control", "../dbms/transactions/concurrency-control.md"),
        ("Storage Distributed", "../storage/distributed.md"),
    ],
    "concurrency/rust-ownership.md": [
        ("Lock-Free", "./lock-free.md"),
        ("OS Synchronization", "../os/synchronization/mutex.md"),
        ("Memory Barriers", "../os/synchronization/memory-barriers.md"),
    ],
    "concurrency/thread-pools.md": [
        ("Cloud Lambda", "../cloud/aws/lambda.md"),
        ("LLM Serving Systems", "../llm/llm-serving/systems.md"),
        ("Fork-Join", "./fork-join.md"),
    ],
    "concurrency/transactional-memory.md": [
        ("DBMS Transactions", "../dbms/transactions/acid.md"),
        ("Lock-Free", "./lock-free.md"),
        ("DBMS Two-Phase Commit", "../dbms/transactions/two-phase-commit.md"),
    ],

    # ===== STORAGE =====
    "storage/block-storage.md": [
        ("Cloud EBS", "../cloud/aws/s3.md"),
        ("NVMe", "./nvme.md"),
        ("SSD vs HDD", "./ssd.md"),
    ],
    "storage/ceph.md": [
        ("Distributed Storage", "./distributed.md"),
        ("Erasure Coding", "./erasure-coding.md"),
        ("Cloud S3", "../cloud/aws/s3.md"),
    ],
    "storage/distributed.md": [
        ("Interview Consistency", "../interview/system-design/consistency-patterns.md"),
        ("DBMS Replication", "../dbms/distributed/replication.md"),
        ("Cloud Overview", "../cloud/overview.md"),
        ("Interview DFS", "../interview/system-design/dfs.md"),
    ],
    "storage/erasure-coding.md": [
        ("Distributed Storage", "./distributed.md"),
        ("Ceph", "./ceph.md"),
        ("Cloud S3", "../cloud/aws/s3.md"),
    ],
    "storage/file-storage.md": [
        ("Block Storage", "./block-storage.md"),
        ("Object Storage", "./object-storage.md"),
        ("OS Filesystems", "../os/filesystems/ext4.md"),
    ],
    "storage/hdd.md": [
        ("SSD", "./ssd.md"),
        ("NVMe", "./nvme.md"),
        ("OS Disk Scheduling", "../os/io/disk-scheduling.md"),
    ],
    "storage/nvme.md": [
        ("SSD", "./ssd.md"),
        ("Block Storage", "./block-storage.md"),
        ("Cloud EC2", "../cloud/aws/ec2.md"),
    ],
    "storage/object-storage.md": [
        ("Cloud S3", "../cloud/aws/s3.md"),
        ("Interview DFS", "../interview/system-design/dfs.md"),
        ("Distributed Storage", "./distributed.md"),
        ("Interview Pastebin", "../interview/system-design/pastebin.md"),
    ],
    "storage/overview.md": [
        ("Cloud Overview", "../cloud/overview.md"),
        ("Interview System Design", "../interview/system-design/README.md"),
        ("DBMS Indexing", "../dbms/indexing/b-plus-tree.md"),
        ("Arch Memory Hierarchy", "../arch/memory-hierarchy/cache-basics.md"),
    ],
    "storage/ssd.md": [
        ("HDD", "./hdd.md"),
        ("NVMe", "./nvme.md"),
        ("Latency Numbers", "../interview/system-design/latency-numbers.md"),
    ],

    # ===== CLOUD =====
    "cloud/overview.md": [
        ("Storage Overview", "../storage/overview.md"),
        ("Networking Overview", "../networks/README.md"),
        ("MLOps Infrastructure", "../ml/mlops/infrastructure.md"),
        ("Interview System Design", "../interview/system-design/README.md"),
    ],

    # ===== ML =====
    "ml/overview.md": [
        ("LLM Architecture", "../llm/llm-serving/architecture.md"),
        ("Interview ML Questions", "../interview/ml-questions.md"),
        ("Cloud GPU", "../cloud/virtualization/README.md"),
        ("Deep Learning", "./deep-learning/README.md"),
    ],
    "ml/transformers/architecture.md": [
        ("LLM Architecture", "../../llm/llm-serving/architecture.md"),
        ("Attention Mechanism", "../deep-learning/attention.md"),
        ("GPU Training", "../../cloud/virtualization/README.md"),
        ("ML System Design Model Serving", "../system-design/model-serving.md"),
    ],
    "ml/transformers/positional-encoding.md": [
        ("Self-Attention", "./self-attention.md"),
        ("Transformer Architecture", "./architecture.md"),
        ("LLM Architecture", "../../llm/llm-serving/architecture.md"),
    ],
    "ml/transformers/t5.md": [
        ("BERT", "./bert.md"),
        ("GPT", "./gpt.md"),
        ("LLM SFT", "../../llm/llm-serving/sft.md"),
        ("Transfer Learning", "../deep-learning/transfer-learning.md"),
    ],
    "ml/classical/gradient-boosting.md": [
        ("XGBoost", "./xgboost.md"),
        ("LightGBM", "./lightgbm.md"),
        ("CatBoost", "./catboost.md"),
        ("Feature Engineering", "../foundations/feature-engineering.md"),
    ],
    "ml/deep-learning/backpropagation.md": [
        ("Optimizers", "./optimizers.md"),
        ("Neural Network Basics", "./nn-basics.md"),
        ("GPU Training", "../../cloud/virtualization/README.md"),
        ("Loss Functions", "../foundations/loss-functions.md"),
    ],
    "ml/advanced/edge.md": [
        ("Quantization (ML)", "./quantization.md"),
        ("Pruning", "./pruning.md"),
        ("Model Compression", "./compression.md"),
        ("Cloud Lambda", "../../cloud/aws/lambda.md"),
    ],
    "ml/agents/README.md": [
        ("LLM Tool Calling", "../../llm/llm-serving/systems.md"),
        ("Agent Architecture", "./architecture.md"),
        ("LLM Prompt Engineering", "../../llm/llm-serving/prompt-engineering.md"),
        ("Interview System Design", "../../interview/system-design/README.md"),
    ],
    "ml/agents/architecture.md": [
        ("LLM Architecture", "../../llm/llm-serving/architecture.md"),
        ("Agent Memory", "./memory.md"),
        ("Agent Planning", "./planning.md"),
        ("Distributed Messaging", "../../interview/system-design/hld/messaging-systems.md"),
    ],
    "ml/agents/autogen.md": [
        ("Multi-Agent", "./multi-agent.md"),
        ("CrewAI", "./crewai.md"),
        ("LangChain", "./langchain.md"),
        ("LLM Serving", "../../llm/llm-serving/README.md"),
    ],
    "ml/agents/crewai.md": [
        ("Multi-Agent", "./multi-agent.md"),
        ("AutoGen", "./autogen.md"),
        ("LangChain", "./langchain.md"),
        ("Agent Planning", "./planning.md"),
    ],
    "ml/agents/evaluation.md": [
        ("LLM Evaluation", "../../llm/llm-serving/evaluation.md"),
        ("ML Foundations Evaluation", "../foundations/evaluation.md"),
        ("Agent Safety", "./safety.md"),
        ("MLOps Monitoring", "../mlops/monitoring.md"),
    ],
    "ml/agents/frameworks.md": [
        ("LangChain", "./langchain.md"),
        ("AutoGen", "./autogen.md"),
        ("CrewAI", "./crewai.md"),
        ("MLOps Platforms", "../mlops/platforms.md"),
    ],
    "ml/agents/langchain.md": [
        ("Agent Architecture", "./architecture.md"),
        ("Tool Calling", "./tool-calling.md"),
        ("MCP Protocol", "./mcp.md"),
        ("LLM Serving", "../../llm/llm-serving/README.md"),
    ],
    "ml/agents/mcp.md": [
        ("Tool Calling", "./tool-calling.md"),
        ("LangChain", "./langchain.md"),
        ("Agent Architecture", "./architecture.md"),
        ("API Design", "../../interview/system-design/hld/api-design.md"),
    ],
    "ml/agents/multi-agent.md": [
        ("AutoGen", "./autogen.md"),
        ("CrewAI", "./crewai.md"),
        ("Agent Communication", "./architecture.md"),
        ("Messaging Systems", "../../interview/system-design/hld/messaging-systems.md"),
    ],
    "ml/agents/planning.md": [
        ("Chain-of-Thought", "./chain-of-thought.md"),
        ("Tree-of-Thought", "./tree-of-thought.md"),
        ("ReAct", "./react.md"),
        ("RL Fundamentals", "../rl/fundamentals.md"),
    ],
    "ml/agents/safety.md": [
        ("LLM RLHF", "../../llm/llm-serving/rlhf.md"),
        ("ML RL RLHF", "../rl/rlhf.md"),
        ("Agent Evaluation", "./evaluation.md"),
        ("Interview System Design Security", "../../interview/system-design/hld/security-design.md"),
    ],
    "ml/agents/tree-of-thought.md": [
        ("Chain-of-Thought", "./chain-of-thought.md"),
        ("ReAct", "./react.md"),
        ("Agent Planning", "./planning.md"),
        ("LLM Prompt Engineering", "../../llm/llm-serving/prompt-engineering.md"),
    ],
    "ml/mlops/canary.md": [
        ("Blue-Green", "./blue-green.md"),
        ("Shadow", "./shadow.md"),
        ("A/B Testing", "./ab-testing.md"),
        ("Cloud Deployments", "../../cloud/kubernetes/deployments.md"),
    ],
    "ml/mlops/mlflow.md": [
        ("Model Registry", "./model-registry.md"),
        ("WandB", "./wandb.md"),
        ("MLOps Pipelines", "./pipelines.md"),
        ("Cloud Observability", "../../cloud/observability/README.md"),
    ],
    "ml/mlops/platforms.md": [
        ("Sagemaker", "./sagemaker.md"),
        ("Vertex AI", "./vertex.md"),
        ("Kubeflow", "./kubeflow.md"),
        ("Cloud Kubernetes", "../../cloud/kubernetes/README.md"),
    ],
    "ml/mlops/sagemaker.md": [
        ("Vertex AI", "./vertex.md"),
        ("MLOps Platforms", "./platforms.md"),
        ("Cloud AWS", "../../cloud/aws/README.md"),
        ("Model Deployment", "./deployment.md"),
    ],
    "ml/mlops/shadow.md": [
        ("Canary", "./canary.md"),
        ("Blue-Green", "./blue-green.md"),
        ("A/B Testing", "./ab-testing.md"),
        ("MLOps Monitoring", "./monitoring.md"),
    ],
    "ml/mlops/vertex.md": [
        ("Sagemaker", "./sagemaker.md"),
        ("MLOps Platforms", "./platforms.md"),
        ("Cloud Overview", "../../cloud/overview.md"),
        ("Kubeflow", "./kubeflow.md"),
    ],

    # ===== LLM =====
    "llm/llm-serving/README.md": [
        ("ML Transformers", "../ml/transformers/README.md"),
        ("LLM Architecture", "./architecture.md"),
        ("Cloud GPU", "../cloud/virtualization/README.md"),
        ("ML System Design", "../ml/system-design/model-serving.md"),
    ],
    "llm/llm-serving/architecture.md": [
        ("ML Transformers", "../ml/transformers/architecture.md"),
        ("Attention Mechanism", "../ml/deep-learning/attention.md"),
        ("KV Cache", "./kv-cache.md"),
        ("GPU Architecture", "../cloud/virtualization/README.md"),
    ],
    "llm/llm-serving/batching.md": [
        ("Inference", "./inference.md"),
        ("vLLM", "./vllm.md"),
        ("Concurrency Thread Pools", "../concurrency/thread-pools.md"),
        ("Cloud Auto Scaling", "../cloud/aws/ec2.md"),
    ],
    "llm/llm-serving/embeddings.md": [
        ("RAG", "./rag.md"),
        ("Tokenization", "./tokenization.md"),
        ("ML Feature Engineering", "../ml/foundations/feature-engineering.md"),
        ("Vector Search", "../ml/system-design/search-ranking.md"),
    ],
    "llm/llm-serving/inference.md": [
        ("Batching", "./batching.md"),
        ("KV Cache", "./kv-cache.md"),
        ("Quantization", "./quantization.md"),
        ("Cloud GPU", "../cloud/virtualization/README.md"),
    ],
    "llm/llm-serving/kv-cache.md": [
        ("Inference", "./inference.md"),
        ("Attention", "../ml/deep-learning/attention.md"),
        ("vLLM", "./vllm.md"),
        ("Storage Memory", "../storage/overview.md"),
    ],
    "llm/llm-serving/ollama.md": [
        ("vLLM", "./vllm.md"),
        ("TGI", "./tgi.md"),
        ("Quantization", "./quantization.md"),
        ("ML Edge Deployment", "../ml/advanced/edge.md"),
    ],
    "llm/llm-serving/quantization.md": [
        ("ML Quantization", "../ml/advanced/quantization.md"),
        ("TensorRT", "./tensorrt.md"),
        ("Inference", "./inference.md"),
        ("Model Compression", "../ml/advanced/compression.md"),
    ],
    "llm/llm-serving/sft.md": [
        ("RLHF", "./rlhf.md"),
        ("Pretraining", "./pretraining.md"),
        ("ML RL DPO", "../ml/rl/dpo.md"),
        ("Transfer Learning", "../ml/deep-learning/transfer-learning.md"),
    ],
    "llm/llm-serving/speculative-decoding.md": [
        ("Inference", "./inference.md"),
        ("Batching", "./batching.md"),
        ("vLLM", "./vllm.md"),
        ("ML Transformers GPT", "../ml/transformers/gpt.md"),
    ],
    "llm/llm-serving/systems.md": [
        ("Agent Tool Calling", "../ml/agents/tool-calling.md"),
        ("RAG", "./rag.md"),
        ("Prompt Engineering", "./prompt-engineering.md"),
        ("Cloud API Gateway", "../cloud/aws/vpc.md"),
    ],
    "llm/llm-serving/tensorrt.md": [
        ("Quantization", "./quantization.md"),
        ("vLLM", "./vllm.md"),
        ("TGI", "./tgi.md"),
        ("Cloud GPU", "../cloud/virtualization/README.md"),
    ],
    "llm/llm-serving/tgi.md": [
        ("vLLM", "./vllm.md"),
        ("Ollama", "./ollama.md"),
        ("Inference", "./inference.md"),
        ("Cloud Kubernetes", "../cloud/kubernetes/README.md"),
    ],
    "llm/llm-serving/tokenization.md": [
        ("Embeddings", "./embeddings.md"),
        ("Pretraining", "./pretraining.md"),
        ("ML Transformers", "../ml/transformers/README.md"),
    ],
    "llm/llm-serving/vllm.md": [
        ("TGI", "./tgi.md"),
        ("TensorRT", "./tensorrt.md"),
        ("Batching", "./batching.md"),
        ("KV Cache", "./kv-cache.md"),
    ],
    "llm/moe/architecture.md": [
        ("ML Transformers", "../ml/transformers/architecture.md"),
        ("Routing", "./routing.md"),
        ("Mixtral", "./mixtral.md"),
        ("Cloud Distributed", "../storage/distributed.md"),
    ],
    "llm/moe/routing.md": [
        ("MoE Architecture", "./architecture.md"),
        ("Switch Transformer", "./switch.md"),
        ("ML Deep Learning Attention", "../ml/deep-learning/attention.md"),
    ],
    "llm/vision/object-detection.md": [
        ("ML CNN", "../ml/deep-learning/cnn.md"),
        ("Vision Transformers", "../ml/transformers/vit.md"),
        ("Segmentation", "./segmentation.md"),
        ("CLIP", "./clip.md"),
    ],
    "llm/vision/segmentation.md": [
        ("Object Detection", "./object-detection.md"),
        ("SAM", "./sam.md"),
        ("ML CNN", "../ml/deep-learning/cnn.md"),
        ("Vision Transformers", "../ml/transformers/vit.md"),
    ],

    # ===== INTERVIEW SYSTEM DESIGN =====
    "interview/system-design/ads.md": [
        ("ML Search Ranking", "../../ml/system-design/search-ranking.md"),
        ("Rate Limiter", "./rate-limiter.md"),
        ("Streaming", "./video-streaming.md"),
        ("Cloud AWS", "../../cloud/aws/README.md"),
    ],
    "interview/system-design/estimation.md": [
        ("Capacity Planning", "./hld/capacity-planning.md"),
        ("Latency Numbers", "./latency-numbers.md"),
        ("Cloud Overview", "../../cloud/overview.md"),
    ],
    "interview/system-design/google-maps.md": [
        ("Distributed Storage", "../../storage/distributed.md"),
        ("Cloud AWS", "../../cloud/aws/README.md"),
        ("Networks Routing", "../../networks/routing/ospf.md"),
    ],
    "interview/system-design/latency-vs-throughput.md": [
        ("Concurrency Overview", "../../concurrency/overview.md"),
        ("Cloud Load Balancing", "../../cloud/kubernetes/services.md"),
        ("Storage SSD", "../../storage/ssd.md"),
    ],
    "interview/system-design/payment.md": [
        ("DBMS Transactions", "../../dbms/transactions/acid.md"),
        ("DBMS Distributed", "../../dbms/transactions/distributed.md"),
        ("Cloud AWS", "../../cloud/aws/README.md"),
    ],
    "interview/system-design/hld/api-design.md": [
        ("RPC", "../rpc.md"),
        ("Networks HTTP", "../../networks/http/rest.md"),
        ("Rate Limiter", "../rate-limiter.md"),
        ("Cloud API Gateway", "../../cloud/aws/vpc.md"),
    ],
    "interview/system-design/hld/availability.md": [
        ("Availability Patterns", "../availability-patterns.md"),
        ("Cloud Overview", "../../cloud/overview.md"),
        ("DBMS Replication", "../../dbms/distributed/replication.md"),
    ],
    "interview/system-design/hld/capacity-planning.md": [
        ("Estimation", "../estimation.md"),
        ("Latency Numbers", "../latency-numbers.md"),
        ("Cloud EC2", "../../cloud/aws/ec2.md"),
    ],
    "interview/system-design/hld/consistency-tradeoffs.md": [
        ("Consistency Patterns", "../consistency-patterns.md"),
        ("DBMS Distributed Consistency", "../../dbms/distributed/consistency.md"),
        ("Storage Distributed", "../../storage/distributed.md"),
    ],
    "interview/system-design/hld/data-intensive.md": [
        ("DBMS Overview", "../../dbms/overview.md"),
        ("Storage Overview", "../../storage/overview.md"),
        ("Messaging Systems", "./messaging-systems.md"),
    ],
    "interview/system-design/hld/database-design.md": [
        ("DBMS Overview", "../../dbms/overview.md"),
        ("DBMS Normalization", "../../dbms/normalization/3nf.md"),
        ("Storage Distributed", "../../storage/distributed.md"),
        ("Key-Value Store", "../kv-store.md"),
    ],
    "interview/system-design/hld/load-balancing-design.md": [
        ("Cloud Kubernetes Services", "../../cloud/kubernetes/services.md"),
        ("Networks HTTP", "../../networks/http/rest.md"),
        ("Rate Limiter", "../rate-limiter.md"),
    ],
    "interview/system-design/hld/monitoring-observability.md": [
        ("Cloud Observability", "../../cloud/observability/README.md"),
        ("MLOps Monitoring", "../../ml/mlops/monitoring.md"),
        ("Metrics", "../metrics.md"),
    ],
    "interview/system-design/hld/scalability.md": [
        ("Performance vs Scalability", "../performance-vs-scalability.md"),
        ("Cloud Auto Scaling", "../../cloud/aws/ec2.md"),
        ("Storage Distributed", "../../storage/distributed.md"),
    ],
    "interview/system-design/hld/security-design.md": [
        ("Networks Security", "../../networks/security/ssl.md"),
        ("Cloud VPC", "../../cloud/aws/vpc.md"),
        ("DBMS Transactions", "../../dbms/transactions/acid.md"),
    ],
    "interview/system-design/lld/README.md": [
        ("System Design Framework", "../framework.md"),
        ("HLD Overview", "../hld/README.md"),
        ("OOP Concepts", "./oop-concepts.md"),
    ],
    "interview/system-design/lld/abstraction-interfaces.md": [
        ("SOLID", "./solid.md"),
        ("OOP Concepts", "./oop-concepts.md"),
        ("Design Patterns", "./design-patterns.md"),
    ],
    "interview/system-design/lld/atm.md": [
        ("State Machine", "./design-patterns.md"),
        ("OOP Concepts", "./oop-concepts.md"),
        ("Payment System", "../payment.md"),
    ],
    "interview/system-design/lld/chess.md": [
        ("Design Patterns", "./design-patterns.md"),
        ("OOP Concepts", "./oop-concepts.md"),
        ("Game Design", "./elevator.md"),
    ],
    "interview/system-design/lld/concurrency-design.md": [
        ("Concurrency Overview", "../../../concurrency/overview.md"),
        ("Producer-Consumer", "../../../concurrency/producer-consumer.md"),
        ("Readers-Writers", "../../../concurrency/readers-writers.md"),
        ("OS Synchronization", "../../../os/synchronization/mutex.md"),
    ],
    "interview/system-design/lld/design-patterns.md": [
        ("SOLID", "./solid.md"),
        ("OOP Concepts", "./oop-concepts.md"),
        ("Abstraction", "./abstraction-interfaces.md"),
    ],
    "interview/system-design/lld/elevator.md": [
        ("State Machine", "./design-patterns.md"),
        ("Concurrency Design", "./concurrency-design.md"),
        ("OOP Concepts", "./oop-concepts.md"),
    ],
    "interview/system-design/lld/error-handling.md": [
        ("SOLID", "./solid.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("API Design", "../hld/api-design.md"),
    ],
    "interview/system-design/lld/file-system.md": [
        ("OS Filesystems", "../../../os/filesystems/ext4.md"),
        ("Storage File Storage", "../../../storage/file-storage.md"),
        ("OOP Concepts", "./oop-concepts.md"),
    ],
    "interview/system-design/lld/library-management.md": [
        ("OOP Concepts", "./oop-concepts.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("SOLID", "./solid.md"),
    ],
    "interview/system-design/lld/movie-ticket.md": [
        ("Concurrency Design", "./concurrency-design.md"),
        ("OOP Concepts", "./oop-concepts.md"),
        ("DBMS Transactions", "../../../dbms/transactions/acid.md"),
    ],
    "interview/system-design/lld/oop-concepts.md": [
        ("SOLID", "./solid.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("Abstraction", "./abstraction-interfaces.md"),
    ],
    "interview/system-design/lld/parking-lot.md": [
        ("OOP Concepts", "./oop-concepts.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("Elevator", "./elevator.md"),
    ],
    "interview/system-design/lld/solid.md": [
        ("OOP Concepts", "./oop-concepts.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("Abstraction", "./abstraction-interfaces.md"),
    ],
    "interview/system-design/lld/uml-class-diagrams.md": [
        ("OOP Concepts", "./oop-concepts.md"),
        ("Design Patterns", "./design-patterns.md"),
        ("SOLID", "./solid.md"),
    ],
}

def enhance_crossrefs(filepath, new_refs):
    """Add cross-section links to existing cross-references section."""
    full_path = os.path.join(BASE, filepath)
    with open(full_path, 'r') as f:
        content = f.read()
    
    # Find the cross-references section
    m = re.search(r'(^## .*[Cc]ross.*\n(?:.*\n)*?)(?=^## |\Z)', content, re.MULTILINE)
    if not m:
        print(f"  NO SECTION: {filepath}")
        return False
    
    section = m.group(1)
    
    # Check which links already exist
    existing_links = set(re.findall(r'\(([^)]+)\)', section))
    
    # Filter out already-existing links
    to_add = [(name, link) for name, link in new_refs if link not in existing_links]
    
    if not to_add:
        print(f"  SKIP (all links exist): {filepath}")
        return False
    
    # Add new links at end of section
    addition = ""
    for name, link in to_add:
        addition += f"- [{name}]({link})\n"
    
    new_section = section.rstrip() + "\n" + addition + "\n"
    content = content.replace(section, new_section)
    
    with open(full_path, 'w') as f:
        f.write(content)
    
    print(f"  OK: {filepath} (+{len(to_add)} refs)")
    return True

def main():
    count = 0
    for relpath, refs in sorted(ENHANCEMENTS.items()):
        filepath = os.path.join(BASE, relpath)
        if not os.path.exists(filepath):
            print(f"  MISSING: {filepath}")
            continue
        if enhance_crossrefs(relpath, refs):
            count += 1
    print(f"\nDone. Enhanced {count} files.")

if __name__ == "__main__":
    main()
