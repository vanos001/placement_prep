# Model Serving Design

## Overview

Model Serving is the process of making trained ML models available for inference in production. It involves designing scalable, low-latency systems that can handle high throughput while maintaining reliability.

## Serving Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        C1[Web App]
        C2[Mobile App]
        C3[Backend Service]
    end
    
    subgraph "API Gateway"
        LB[Load Balancer]
        AUTH[Authentication]
        RL[Rate Limiting]
    end
    
    subgraph "Serving Layer"
        S1[Server 1]
        S2[Server 2]
        S3[Server N]
    end
    
    subgraph "Model Store"
        M[Model Registry]
        V[Version Manager]
    end
    
    C1 --> LB
    C2 --> LB
    C3 --> LB
    LB --> AUTH
    AUTH --> RL
    RL --> S1
    RL --> S2
    RL --> S3
    S1 --> M
    S2 --> M
    S3 --> M
```

## Serving Patterns

### 1. Real-time Serving
```mermaid
graph LR
    R[Request] --> P[Preprocess]
    P --> M[Model]
    M --> Post[Postprocess]
    Post --> Res[Response]
```

**Requirements:**
- Latency: < 100ms (P99)
- Throughput: 1000+ QPS
- Availability: 99.9%+

### 2. Batch Serving
```mermaid
graph LR
    D[Data Source] --> B[Batch Job]
    B --> M[Model]
    M --> O[Output Store]
    O --> S[Sink]
```

**Requirements:**
- Process millions of records
- Scheduled or triggered
- Cost-efficient

### 3. Streaming Serving
```mermaid
graph LR
    E[Events] --> K[Kafka]
    K --> P[Processor]
    P --> M[Model]
    M --> R[Results]
```

**Requirements:**
- Near real-time (seconds)
- Event-driven
- Scalable

## Model Optimization

| Technique | Description | Use Case |
|-----------|-------------|----------|
| Quantization | Reduce precision (FP32→INT8) | Edge devices, CPU serving |
| Pruning | Remove unnecessary weights | Model compression |
| Distillation | Train smaller model | Custom compression |
| ONNX Export | Framework-agnostic format | Cross-platform serving |
| TensorRT | NVIDIA GPU optimization | GPU serving |

## Serving Frameworks

| Framework | Language | Key Feature |
|-----------|----------|-------------|
| TensorFlow Serving | C++ | TF native, gRPC |
| TorchServe | Python | PyTorch native |
| Triton | C++ | Multi-framework, GPU |
| BentoML | Python | Easy packaging |
| Seldon Core | Python | Kubernetes-native |

## Scaling Strategies

```mermaid
graph TB
    subgraph "Horizontal Scaling"
        H1[Add more instances]
        H2[Load balancer distributes]
        H3[Stateless serving]
    end
    
    subgraph "Vertical Scaling"
        V1[More resources per instance]
        V2[GPU acceleration]
        V3[Model optimization]
    end
    
    subgraph "Auto-scaling"
        A1[Based on QPS]
        A2[Based on latency]
        A3[Based on queue depth]
    end
```

## Caching Strategy

```python
# Feature caching
class FeatureCache:
    def __init__(self, ttl=300):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
```

## Interview Questions

1. **How would you design a model serving system for 10K QPS?**
2. **What are the trade-offs between real-time and batch serving?**
3. **How do you handle model versioning in serving?**
4. **Explain model optimization techniques for deployment.**
5. **How do you ensure low latency in model serving?**

## Common Mistakes

- **No health checks**: Serving fails silently without monitoring
- **Ignoring latency**: Training accuracy means nothing if inference is too slow
- **No caching**: Repeated feature lookups waste resources
- **Over-provisioning**: Without auto-scaling, costs balloon

## Summary

Model Serving design requires balancing latency, throughput, and cost. Key decisions include serving pattern (real-time, batch, streaming), model optimization (quantization, pruning), and scaling strategy (horizontal, vertical, auto-scaling). Use established frameworks (TF Serving, Triton) and implement caching, health checks, and monitoring.
