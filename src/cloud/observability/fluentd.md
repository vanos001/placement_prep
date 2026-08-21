# Fluentd and Fluent Bit

Fluentd and Fluent Bit are open-source log collectors developed by Treasure Data (Fluentd in 2011, Fluent Bit in 2014). Both are CNCF graduated projects. Fluent Bit is the lightweight, performant successor to Fluentd, designed for edge and Kubernetes environments where Fluentd's Ruby-based runtime was too heavy. This page covers the architecture, the unified log layer (input/filter/output), and the production deployment patterns.

## The Two Tools

```text
Fluentd (Ruby, ~40 MB binary):
  - Plugins in Ruby (slow startup, GC overhead)
  - Rich ecosystem (700+ plugins)
  - Used for: heavy processing pipelines (parse, enrich, route)

Fluent Bit (C, ~2 MB binary):
  - Plugins in C (fast startup, no GC)
  - Smaller ecosystem (50+ plugins)
  - Used for: edge collection (Kubernetes DaemonSet, IoT)

Hybrid pattern:
  Edge (Fluent Bit) → Heavy pipeline (Fluentd) → Backend (Elasticsearch, Loki, etc.)
```

For most modern Kubernetes deployments, Fluent Bit alone suffices. Fluentd is used when complex processing is needed (e.g., enrichment with a database lookup).

## The Unified Log Architecture

Both Fluentd and Fluent Bit use the same pipeline model:

```text
Input → Parser → Filter → Buffer → Output (one or more)
```

### Fluent Bit Configuration

```yaml
# fluent-bit.yaml (Kubernetes ConfigMap)
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
    
    [INPUT]
        Name              tail
        Path              /var/log/containers/*.log
        Parser            docker
        Tag               kube.*
        Refresh_Interval  5
        Mem_Buf_Limit     50MB
    
    [FILTER]
        Name  kubernetes
        Match kube.*
        Kube_URL  https://kubernetes.default.svc:443
        Merge_Log  true
    
    [OUTPUT]
        Name  es
        Match kube.*
        Host  elasticsearch
        Port  9200
        Logstash_Format  On
        Logstash_Prefix  kube-logs
```

### Input Plugins

```ini
[INPUT]
    Name  tail
    Path  /var/log/containers/*.log
    Tag   kube.*
    Parser  docker
```

Each input has a `Name` (plugin), parameters, and a `Tag` (used for routing).

Common inputs:
- `tail`: tail files.
- `systemd`: read from journald.
- `cpu`, `mem`, `disk`: collect metrics.
- `http`: receive logs via HTTP.
- `kafka`: consume from Kafka.

### Filter Plugins

```ini
[FILTER]
    Name  kubernetes
    Match kube.*
    Kube_URL  https://kubernetes.default.svc
    Merge_Log  true
```

Filters transform records between input and output. Common filters:
- `kubernetes`: enriches logs with pod metadata (labels, annotations).
- `grep`: filter records by content.
- `record_modifier`: add/remove fields.
- `lua`: run Lua scripts for custom logic.
- `parser`: parse fields (json, regex).

### Output Plugins

```ini
[OUTPUT]
    Name  es
    Match kube.*
    Host  elasticsearch
    Port  9200
```

Each output has a `Match` (routing rule based on tag) and target config. Common outputs:
- `es`: Elasticsearch.
- `loki`: Grafana Loki.
- `kafka`: send to Kafka.
- `s3`: write to S3.
- `stdout`: print to stdout (for debugging).
- `null`: discard.

Multiple outputs can be configured for the same match (fan-out).

## Routing via Tags

Tags are dot-separated identifiers. The `Match` field uses globbing:

```ini
[OUTPUT]
    Name  es
    Match kube.*         # matches kube.nginx, kube.frontend, etc.
    
[OUTPUT]
    Name  s3
    Match kube.audit.*   # matches kube.audit only
```

A record with tag `kube.audit.signin` matches both outputs (sent to both ES and S3). A record with tag `kube.frontend.error` matches only the first output.

## Buffering

Fluent Bit buffers records between input and output to handle backpressure:

```ini
[OUTPUT]
    Name  es
    Match *
    Host  elasticsearch
    Buffer_Type  filesystem
    Buffer_Path  /var/log/flb-buffer/
    Flush_Interval  5
    Retry_Limit  5
```

Two buffer types:
- **Memory**: fast, lost on crash.
- **Filesystem**: persistent (records survive restart), slower.

For production, use filesystem buffering. Records are written to disk; on restart, they're replayed.

## Production Performance

Fluent Bit's published performance:
- Throughput: 1M+ records/sec per instance.
- Memory: ~30 MB resident.
- CPU: ~5% of one core for 100K records/sec.

For comparison, Fluentd (Ruby) on the same hardware: 100K records/sec, 500 MB memory.

## Production Deployment

### Kubernetes DaemonSet

The standard pattern: one Fluent Bit DaemonSet per Kubernetes node, tailing all container logs:

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: kube-system
spec:
  template:
    spec:
      serviceAccountName: fluent-bit
      containers:
        - name: fluent-bit
          image: fluent/fluent-bit:2.2.0
          resources:
            requests: { cpu: 5m, memory: 50Mi }
            limits:   { cpu: 100m, memory: 200Mi }
          volumeMounts:
            - { name: varlog, mountPath: /var/log, readOnly: true }
            - { name: varlibdockercontainers, mountPath: /var/lib/docker/containers, readOnly: true }
            - { name: config, mountPath: /fluent-bit/etc }
      volumes:
        - { name: varlog, hostPath: { path: /var/log } }
        - { name: varlibdockercontainers, hostPath: { path: /var/lib/docker/containers } }
        - { name: config, configMap: { name: fluent-bit-config } }
```

Each node's Fluent Bit tails `/var/log/containers/*.log` (the symlink to Docker/containerd logs) and sends to the configured output.

### Multi-Output (Fan-Out)

For sending logs to multiple backends:

```ini
[OUTPUT]
    Name  es
    Match *
    Host  elasticsearch
    
[OUTPUT]
    Name  s3
    Match *
    Region us-east-1
    Bucket my-logs-bucket
```

Each log is sent to both ES and S3. For high-throughput, the S3 output can be configured to batch (write 100 MB chunks to S3 instead of one record at a time).

### Hybrid: Fluent Bit + Fluentd

For complex processing:

```text
Kubernetes (Fluent Bit DaemonSets) → Fluentd (heavy processing) → Elasticsearch
```

Fluent Bit at the edge is light; Fluentd at the central location does the heavy lifting (parsing, enrichment, routing).

## Common Pitfalls

1. **Forgetting that buffer files accumulate on disk.** If the output is unavailable, buffer files grow until disk fills. Set `Buffer_Max_Size`.

2. **Forgetting to set `Mem_Buf_Limit`.** Without it, Fluent Bit's memory grows unboundedly under backpressure. Set `Mem_Buf_Limit 50MB` per input.

3. **Forgetting that the Kubernetes filter makes API calls.** Each new container's metadata is fetched via K8s API. For a busy cluster, cache the API responses.

4. **Forgetting that the `tail` input may miss logs on restart.** The default `DB` (offset tracking) is off; enable it to track positions across restarts.

5. **Forgetting that `Match` is globbing, not regex.** `kube.*` matches `kube.nginx` but not `kubenginx`. Be careful with tag design.

6. **Forgetting that the parser must match the log format.** A `json` parser on a plain-text log produces empty records. Test parsers before deploying.

## Comparison to Other Log Collectors

| Aspect | Fluent Bit | Fluentd | Promtail | Vector |
|--------|-----------|---------|----------|--------|
| Language | C | Ruby | Go | Rust |
| Binary size | 2 MB | 40 MB | 30 MB | 30 MB |
| Throughput | 1M/sec | 100K/sec | 500K/sec | 1M+/sec |
| Memory | 30 MB | 500 MB | 100 MB | 50 MB |
| Plugin count | 50+ | 700+ | 30+ | 100+ |
| Best for | Edge, K8s | Heavy pipelines | Loki integration | Modern, Rust performance |

Fluent Bit and Promtail are similar; the choice depends on the backend (Elasticsearch → Fluent Bit, Loki → Promtail). Vector is the modern alternative with better performance.

## References

- [Fluentd documentation](https://docs.fluentd.org/)
- [Fluent Bit documentation](https://docs.fluentbit.io/manual)
- [Fluentd GitHub repository](https://github.com/fluent/fluentd)
- [Fluent Bit GitHub repository](https://github.com/fluent/fluent-bit)
- [Fluent Bit vs Fluentd comparison (Fluent blog)](https://www.fluent.co/blog/fluent-bit-vs-fluentd/)
- [Fluent Bit Kubernetes DaemonSet](https://docs.fluentbit.io/manual/installation/kubernetes)
- [Vector: alternative log collector](https://vector.dev/)
- [LWN: Fluent Bit overview (2021)](https://lwn.net/Articles/856775/)
