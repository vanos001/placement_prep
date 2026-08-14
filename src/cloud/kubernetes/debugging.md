# Kubernetes Debugging Deep Dive

## Core Debugging Commands

```bash
# Describe: shows events, conditions, and current state
kubectl describe pod my-pod -n production

# Logs: container stdout/stderr
kubectl logs my-pod -n production
kubectl logs my-pod -c my-container -n production  # Multi-container pod
kubectl logs my-pod --previous -n production        # Last crashed container's logs
kubectl logs -f my-pod --tail=100                   # Follow last 100 lines

# Exec: shell into a running container
kubectl exec -it my-pod -- /bin/sh
kubectl exec -it my-pod -c sidecar -- /bin/sh      # Specific container

# Events: cluster-wide events
kubectl get events --sort-by='.lastTimestamp' -A
kubectl get events --field-selector involvedObject.name=my-pod

# General status
kubectl get pods -o wide          # Shows node, IP, ready state
kubectl get pods -w               # Watch mode
kubectl top pods                  # Resource usage (requires metrics-server)
kubectl top nodes                 # Node resource usage
```

## CrashLoopBackOff

The pod's container starts, crashes, kubelet restarts it, it crashes again—with exponentially increasing backoff delays (10s → 20s → 40s → ... up to 5 minutes).

### Diagnostic flow:

```bash
# 1. Check the events
kubectl describe pod my-pod
# Look for: "Back-off restarting failed container"

# 2. Get the last container's logs (before the crash)
kubectl logs my-pod --previous

# 3. Check exit code
kubectl get pod my-pod -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'
```

### Common causes by exit code:

| Exit Code | Meaning | Typical Cause |
-----------|---------|---------------|
| 0 | Success | Container exits immediately (missing entrypoint, wrong CMD) |
| 1 | Application error | Unhandled exception, config file missing, port conflict |
| 137 | SIGKILL (128+9) | OOMKilled (check limits), or `docker kill` |
| 139 | SIGSEGV (128+11) | Segfault—bug in native code, incompatible binary |
| 143 | SIGTERM (128+15) | Graceful shutdown, preStop hook issue |
| 126 | Permission denied | Entrypoint not executable |
| 127 | Command not found | Entrypoint/binary missing in image |

### CrashLoopBackOff troubleshooting checklist:
1. **Check logs** (`--previous`)
2. **Verify config**: ConfigMaps and Secrets mounted correctly?
3. **Check resources**: Memory limit too low? (OOMKilled → exit 137)
4. **Check dependencies**: Database/other services reachable?
5. **Check image**: Correct tag? Binary present and executable?
6. **Check liveness probe**: Probe too aggressive, killing healthy containers?

## ImagePullBackOff / ErrImagePull

```bash
# Check the event
kubectl describe pod my-pod
# "Failed to pull image": auth failure, wrong tag, registry unreachable
```

| Cause | Fix |
-------|-----|
| Private registry, no imagePullSecrets | Create Secret with `docker-registry` type, add to pod spec |
| Image tag doesn't exist | Fix the tag; avoid `:latest` in production |
| Registry unreachable (network) | Check CNI, DNS, firewall rules |
| Image too large / timeout | Increase `imagePullPolicy` understanding; pre-pull images |

```yaml
# Adding registry credentials
spec:
  imagePullSecrets:
    - name: registry-credentials
  containers:
    - image: registry.internal.com/app:v1.2.0
```

## OOMKilled (Exit Code 137)

The container exceeded its memory limit and the kernel's OOM killer terminated it.

```bash
# Verify OOMKill
kubectl describe pod my-pod | grep -A5 "Last State"
# Output: "Reason: OOMKilled"

# Check current memory usage
kubectl top pod my-pod

# Check limits
kubectl get pod my-pod -o jsonpath='{.spec.containers[0].resources.limits}'
```

Resolution approaches:
1. **Increase memory limit** if the application legitimately needs more
2. **Fix memory leak** if usage grows over time (heap dump, profiler)
3. **Check requests vs. limits**: If requests are much lower than actual usage, the scheduler places too many pods on a node
4. **Add JVM flags**: `-XX:MaxRAMPercentage=75.0` to respect container limits
5. **Monitor with metrics**: Set up `container_memory_working_set_bytes` alerts at 80% of limit

## Network Policy Blocking Traffic

When pods can't communicate despite Services being correct:

```bash
# 1. Verify the Service endpoints are populated
kubectl get endpoints my-service
# Empty endpoints = pods not ready or label mismatch

# 2. Test DNS resolution from inside a pod
kubectl exec -it my-pod -- nslookup my-service.production.svc.cluster.local

# 3. Test connectivity directly to pod IP (bypasses Service)
kubectl exec -it my-pod -- curl http://10.0.1.5:8080

# 4. Check network policies
kubectl get networkpolicy -n production
kubectl describe networkpolicy my-policy

# 5. If using Cilium, check policy enforcement
cilium policy get
```

Common network policy pitfalls:
- Applied a deny-all policy but forgot to allow DNS (port 53 UDP to kube-dns)
- Policy uses wrong label selector—check label match exactly
- Egress blocked but the pod needs external access
- CNI doesn't support NetworkPolicy (Flannel without Calico)

## Events and Conditions

Events are the first place to look for any pod issue. They show the cluster's perspective on what's happening.

```bash
# All events for a pod, sorted by time
kubectl get events --field-selector involvedObject.name=my-pod,involvedObject.namespace=production --sort-by='.lastTimestamp'

# Pod conditions (internal to the pod object)
kubectl get pod my-pod -o jsonpath='{.status.conditions}' | jq
```

Key conditions:

| Condition | Type | Meaning |
-----------|------|---------|
| `PodScheduled` | True | Scheduler assigned a node |
| `Initialized` | True | All init containers completed |
| `Ready` | True | Pod is passing readiness probe and accepting traffic |
| `ContainersReady` | True | All containers are running |

If `Ready` is False, check `message` in the condition for the specific probe failure reason.

## Quick Reference: Common Pod States

| State | Meaning | First Check |
-------|---------|------------|
| `Pending` | Not yet scheduled (no node matches) | `kubectl describe pod` → events |
| `ContainerCreating` | Pulling image or mounting volumes | Events (image pull, volume attach) |
| `Running` | Container started | Readiness probe (Ready True/False) |
| `CrashLoopBackOff` | Container crashes repeatedly | `kubectl logs --previous` |
| `ImagePullBackOff` | Can't pull image | Events, imagePullSecrets, tag |
| `OOMKilled` | Memory limit exceeded | Increase limit, check for leaks |
| `ErrImagePull` | Transient image pull failure | Registry connectivity, credentials |
| `NodeNotReady` | Node is unreachable | Check kubelet, node resources |
| `Completed` | Container exited with code 0 | For Jobs/CronJobs, this is success |

## References

- [Kubernetes Troubleshoot Documentation](https://kubernetes.io/docs/tasks/debug/)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands)

## Interview Questions

### Q1: How do you debug a pod in CrashLoopBackOff?
**Answer**: First, run `kubectl describe pod <name>` to see events—look for "Back-off restarting failed container" and any error messages. Then run `kubectl logs <name> --previous` to get the logs from the container's last run before it crashed. Check the exit code: 1 = application error (check config, dependencies), 137 = OOMKilled (increase memory limit or fix leak), 139 = segfault (native code bug). Also verify the liveness probe isn't too aggressive (causing healthy containers to restart). If the container starts but immediately exits with code 0, the entrypoint or CMD may be missing.

### Q2: A pod is stuck in Pending state. How do you troubleshoot?
**Answer**: Run `kubectl describe pod <name>` and check the Events section. Common reasons: (1) **Insufficient resources**—"Insufficient cpu" or "Insufficient memory" means no node has enough allocatable capacity. (2) **Node selector/affinity**—no node matches the required labels. (3) **Taints**—no toleration for node taints. (4) **PVC pending**—no available PV matches the PVC's storage class/size. (5) **PodDisruptionBudget**—preventing scheduling during disruption. Fix by adding nodes, adjusting resource requests, fixing selectors, or creating matching PVs.

### Q3: How do you debug a pod that can't reach a Service?
**Answer**: Systematic approach: (1) Check `kubectl get endpoints <service>`—empty endpoints mean the selector doesn't match any ready pods. (2) Verify DNS: `nslookup <service>.<namespace>.svc.cluster.local` from within a pod. (3) Test direct pod IP to rule out Service issues. (4) Check if the Service's targetPort matches the container's port. (5) Check for NetworkPolicy that blocks ingress/egress. (6) Check if the Service port is correct (port vs. targetPort confusion). (7) For headless services, verify you're resolving individual pod IPs.

### Q4: What is the difference between `kubectl logs` and `kubectl logs --previous`?
**Answer**: `kubectl logs` shows the **current** container's logs. `kubectl logs --previous` shows logs from the **previous** terminated container instance. This is essential for CrashLoopBackOff debugging—the current container may have just started and crashed before producing meaningful logs, but the previous container's logs show the actual error. Kubernetes keeps logs of the previous container termination available for this purpose.

### Q5: How do you debug OOMKilled containers?
**Answer**: First confirm with `kubectl describe pod <name>`—look for "Last State: OOMKilled". Then check `kubectl top pod <name>` for current memory usage. Compare against the pod's memory limit. Solutions: (1) Increase the memory limit if the workload genuinely needs more. (2) Profile the application for memory leaks (heap dumps, `pprof` for Go, VisualVM for Java). (3) For JVM apps, use `-XX:MaxRAMPercentage=75.0` to automatically size the heap within the container's limit. (4) Set up `container_memory_working_set_bytes` alerting at 80% of the limit to get early warning. (5) Ensure the memory request is close to the actual usage to prevent the scheduler from overcommitting the node.