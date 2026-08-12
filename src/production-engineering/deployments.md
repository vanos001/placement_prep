# Deployment Strategies

Deployment strategy is one of the most critical decisions in production engineering. The way you release code to production directly impacts availability, user experience, and your ability to recover from failures. This document covers the major deployment strategies, their trade-offs, and practical implementation considerations.

## Blue-Green Deployments

### Concept
Blue-green deployment maintains two identical production environments. At any given time, only one environment serves live traffic (let's call it "blue"). The new version is deployed to the idle environment ("green"). Once green is verified healthy, traffic is switched from blue to green. If something goes wrong, traffic switches back to blue instantly.

### Architecture
```
                    ┌─────────────┐
  Users ──→ Load   │  Blue (v1)  │ ← Currently serving
          Balancer  │  Green (v2) │ ← New version deployed
                    └─────────────┘
```

The load balancer or router is the single point that controls which environment receives traffic. The switch can be a DNS change, a load balancer configuration update, or a router rule modification.

### Advantages
- **Instant rollback**: If the new version has issues, switching back to the old environment takes seconds
- **Zero downtime**: Traffic switches atomically; there is no period where both old and new code serve traffic simultaneously
- **Full environment testing**: The green environment can be thoroughly tested with production-equivalent data before the switch
- **Simplicity**: The concept is straightforward and easy to explain to stakeholders

### Disadvantages
- **Resource duplication**: You need double the infrastructure, which can be expensive
- **Database migrations**: Schema changes must be backward-compatible since both environments may share the database
- **Stateful services**: Sessions, in-memory caches, and other stateful components complicate the switch
- **Long-lived environments**: If the old environment stays idle too long, it may drift from the desired state

### Implementation Considerations
- Use infrastructure-as-code to ensure both environments are truly identical
- Implement health checks that verify the green environment before switching
- Consider using feature flags in conjunction with blue-green for finer control
- Automate the switch and rollback processes to minimize human error

## Canary Deployments

### Concept
Canary deployment gradually routes a small percentage of traffic to the new version while the majority continues using the old version. The new version is monitored closely for errors, latency spikes, or other anomalies. If the canary performs well, traffic is gradually shifted until it reaches 100%.

### Traffic Progression
```
Phase 1: 95% old, 5% new    → Monitor for 15-30 minutes
Phase 2: 80% old, 20% new   → Monitor for 15-30 minutes
Phase 3: 50% old, 50% new   → Monitor for 30-60 minutes
Phase 4: 0% old, 100% new   → Deployment complete
```

### Advantages
- **Risk mitigation**: Only a small fraction of users are exposed to potential issues
- **Real-world validation**: The new version is tested with real production traffic and data
- **Gradual rollout**: Issues are caught early before they affect all users
- **Cost-effective**: Does not require double the infrastructure

### Disadvantages
- **Complex routing**: Requires sophisticated load balancing or service mesh configuration
- **Monitoring dependency**: Effectiveness depends on having good observability to detect problems
- **Longer rollout**: Takes more time than blue-green since traffic shifts gradually
- **Inconsistent user experience**: During the rollout, users may see different versions

### Canary Analysis
Automated canary analysis compares metrics between the canary and baseline:
- **Error rates**: Is the canary producing more errors?
- **Latency**: Is the canary slower (p50, p95, p99)?
- **Business metrics**: Are conversion rates, click-through rates, etc. affected?
- **Resource usage**: Is the canary consuming more memory or CPU?

Tools like Kayenta (Netflix), Spinnaker, and Flagger automate canary analysis.

## Rolling Deployments

### Concept
Rolling deployment replaces instances of the old version with new instances incrementally. At any point during the rollout, a mix of old and new instances serve traffic. The deployment proceeds in batches until all instances are updated.

### Rolling Update Pattern
```
Step 1: [v1] [v1] [v1] [v1] [v1]    → All old
Step 2: [v1] [v1] [v1] [v1] [v2]    → Replace 1
Step 3: [v1] [v1] [v1] [v2] [v2]    → Replace 1
Step 4: [v1] [v1] [v2] [v2] [v2]    → Replace 1
Step 5: [v1] [v2] [v2] [v2] [v2]    → Replace 1
Step 6: [v2] [v2] [v2] [v2] [v2]    → All new
```

### Kubernetes Rolling Update
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max extra pods during update
      maxUnavailable: 0   # Max pods that can be down
  template:
    spec:
      containers:
      - name: my-app
        image: my-app:v2
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
```

### Advantages
- **No extra infrastructure**: Uses the same resources, just updates incrementally
- **Continuous availability**: Old instances keep serving while new ones start up
- **Simple implementation**: Most orchestration platforms support this natively
- **Gradual validation**: Each batch can be validated before proceeding

### Disadvantages
- **Mixed versions**: Both old and new code run simultaneously, which can cause compatibility issues
- **Slower rollback**: Rolling back requires another rolling update to the previous version
- **Capacity reduction**: During the update, some capacity is temporarily lost (unless maxSurge is used)
- **No instant switch**: Cannot go from 0% to 100% new version instantly

## Feature Flags

### Concept
Feature flags (also called feature toggles) decouple deployment from release. Code for new features is deployed to production behind a flag that is disabled by default. The feature can be enabled for specific users, percentages, or conditions without redeployment.

### Types of Feature Flags
- **Release toggles**: Hide incomplete features during development; removed after full release
- **Experiment toggles**: A/B testing; serve different experiences to different user segments
- **Ops toggles**: Operational controls; enable/disable features based on system health
- **Permission toggles**: Premium features gated by subscription tier or user role

### Implementation Example
```python
class FeatureFlagService:
    def __init__(self, config_store):
        self.config_store = config_store
        self.cache = {}
    
    def is_enabled(self, flag_name, user_id=None, default=False):
        flag_config = self.config_store.get(flag_name)
        if not flag_config:
            return default
        
        if not flag_config.get('enabled', False):
            return False
        
        # Percentage-based rollout
        rollout_pct = flag_config.get('rollout_percentage', 100)
        if rollout_pct < 100 and user_id:
            hash_val = hash(f"{flag_name}:{user_id}") % 100
            return hash_val < rollout_pct
        
        # User allowlist
        allowed_users = flag_config.get('allowed_users', [])
        if allowed_users and user_id:
            return user_id in allowed_users
        
        return True

# Usage
flags = FeatureFlagService(redis_config_store)

def checkout(request):
    if flags.is_enabled('new-checkout-flow', user_id=request.user.id):
        return new_checkout(request)
    return legacy_checkout(request)
```

### Feature Flag Best Practices
- **Clean up flags**: Remove flags after features are fully released; stale flags create technical debt
- **Default to off**: New flags should be disabled by default; enable explicitly
- **Audit changes**: Log all flag state changes for debugging and compliance
- **Test both paths**: Ensure both the flagged and unflagged code paths are tested
- **Limit scope**: Keep flags small and focused; avoid compound flags

## Zero-Downtime Deployments

### Database Migrations
The most challenging aspect of zero-downtime deployments is database schema changes. The key principle is that every migration must be backward-compatible.

**Expand and Contract Pattern:**
1. **Expand**: Add new columns/tables without removing old ones
2. **Migrate data**: Write to both old and new structures
3. **Switch reads**: Read from the new structure
4. **Contract**: Remove the old structure

```sql
-- Phase 1: Expand (add new column, old code ignores it)
ALTER TABLE users ADD COLUMN email_normalized VARCHAR(255);

-- Phase 2: Backfill (populate new column)
UPDATE users SET email_normalized = LOWER(TRIM(email));

-- Phase 3: Switch (new code reads/writes email_normalized)
-- Phase 4: Contract (once no code uses 'email' for normalization)
ALTER TABLE users DROP COLUMN email;
```

### Connection Draining
When replacing instances, new connections must not be routed to instances being terminated, and existing connections must be allowed to complete:

```
1. Mark instance as "draining" in load balancer
2. Stop sending new connections to the instance
3. Wait for existing connections to complete (with timeout)
4. Terminate the instance
```

### Session Handling
During deployments with mixed versions, sessions must work across both versions:
- Use external session stores (Redis, Memcached) instead of in-memory sessions
- Ensure session data format is backward-compatible
- Consider sticky sessions during short deployment windows

## Rollback Strategies

### Automatic Rollback
Automate rollback based on health metrics:
```python
def deploy_with_rollback(new_version, health_check, timeout=300):
    deploy(new_version)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        health = health_check()
        if health.error_rate > THRESHOLD:
            rollback()
            raise DeploymentFailed(f"Error rate {health.error_rate}% exceeded threshold")
        if health.latency_p99 > LATENCY_THRESHOLD:
            rollback()
            raise DeploymentFailed(f"Latency {health.latency_p99}ms exceeded threshold")
        time.sleep(10)
    
    mark_deployment_successful(new_version)
```

### Rollback Considerations
- **Database rollbacks**: Forward-fix is often easier than rolling back database migrations
- **State compatibility**: Ensure the previous version can handle data written by the new version
- **Cache invalidation**: Stale cached data from the new version may cause issues after rollback
- **External integrations**: Third-party APIs called by the new version may have side effects that persist

## Deployment Pipeline

A complete deployment pipeline typically includes:

1. **Build**: Compile code, build container images, tag with version
2. **Test**: Run unit tests, integration tests, security scans
3. **Stage**: Deploy to staging environment for final validation
4. **Approve**: Manual or automated approval gate
5. **Deploy**: Execute chosen deployment strategy (canary, rolling, etc.)
6. **Verify**: Monitor health metrics, run smoke tests
7. **Promote**: Shift all traffic to new version (for canary)
8. **Cleanup**: Remove old version artifacts

## Summary

| Strategy | Downtime | Rollback Speed | Resource Cost | Complexity |
|----------|----------|----------------|---------------|------------|
| Blue-Green | None | Instant | High (2x) | Low |
| Canary | None | Fast | Low | Medium |
| Rolling | Minimal | Slow | Low | Low |
| Feature Flags | None | Instant | Low | Medium |

The best deployment strategy depends on your specific requirements: how critical zero-downtime is, how much infrastructure budget you have, how sophisticated your monitoring is, and how comfortable your team is with operational complexity. Many organizations combine strategies—for example, using canary deployments with feature flags for maximum control.
