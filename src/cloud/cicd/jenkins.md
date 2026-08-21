# Jenkins (Continuous Integration Server)

Jenkins is an open-source automation server, originally developed as "Hudson" at Sun Microsystems in 2004, forked to Jenkins in 2011 (after Oracle's acquisition of Sun). It is the most widely-used CI/CD server in enterprises, with a plugin ecosystem of 1800+ plugins. This page covers the architecture, the pipeline model, the agent execution, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Jenkins Controller (the master)                           │
│  - Web UI for job configuration                              │
│  - Schedules builds on Agents                                │
│  - Stores build history (in JENKINS_HOME)                    │
│  - Manages plugins                                           │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ schedule build               │ build results
        ▼                              ▼
┌──────────────────────────────┐    ┌──────────────────────┐
│  Static Agents (long-lived)   │    │  Cloud Agents          │
│  - SSH / JNLP connection      │    │  - Kubernetes pods     │
└──────────────────────────────┘    │  - Docker containers   │
                                      │  - EC2 instances        │
                                      └──────────────────────┘
```

The controller is the brain; agents execute builds. The controller can run builds directly (legacy) or delegate to agents.

## The Pipeline Model (Jenkinsfile)

Modern Jenkins uses "Pipeline" (defined in a `Jenkinsfile` in the repo):

```groovy
pipeline {
    agent {
        kubernetes {
            yaml '''
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: docker
    image: docker:20
    command: ['sleep', 'infinity']
    securityContext:
      privileged: true
'''
        }
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'docker build -t my-app .'
            }
        }
        
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
        
        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh 'kubectl apply -f k8s/'
            }
        }
    }
    
    post {
        success {
            slackSend channel: '#deploys', color: 'good', message: "Build succeeded: ${env.BUILD_URL}"
        }
        failure {
            slackSend channel: '#deploys', color: 'danger', message: "Build failed: ${env.BUILD_URL}"
        }
    }
}
```

The Jenkinsfile is Groovy DSL; declarative syntax (shown above) is preferred over scripted (older).

## Stages, Steps, and Parallelism

```groovy
stages {
    stage('Test') {
        parallel {
            stage('Unit') {
                steps { sh 'pytest tests/unit' }
            }
            stage('Integration') {
                steps { sh 'pytest tests/integration' }
            }
            stage('E2E') {
                steps { sh 'pytest tests/e2e' }
            }
        }
    }
}
```

Parallel stages run concurrently (on different agents); stages within a `parallel` block run sequentially.

## Agents and Executors

Each agent has one or more "executors" (slots for concurrent builds). A 4-executor agent can run 4 builds simultaneously.

```groovy
agent {
    label 'linux && docker'
}
```

The job runs on an agent labeled `linux && docker`. Labels let you match jobs to agents by capability.

## The Plugin Ecosystem

Jenkins has 1800+ plugins for:
- Source control (Git, Subversion).
- Build tools (Maven, Gradle, npm).
- Cloud (Kubernetes, AWS, Azure).
- Notifications (Slack, Email, Microsoft Teams).
- Quality (SonarQube, Code Coverage).
- Deployment (Docker, Helm, ArgoCD).

For most CI/CD needs, the existing plugins cover the use case. For custom needs, you can write a plugin in Java.

## Production Deployment

### Controller HA

Jenkins doesn't have built-in HA. For HA, options:
- **Active-passive**: run two controllers; one is standby; promote on failure (via a load balancer).
- **CloudBees CI**: enterprise Jenkins with built-in HA (paid).
- **Multi-controller**: split workloads across multiple controllers (each with its own jobs).

For most teams, a single controller with regular backups is sufficient.

### Backup Strategy

`JENKINS_HOME` contains:
- Job configurations.
- Build history (logs, artifacts).
- Plugin state.

Back up `JENKINS_HOME` daily (or more frequently). For HA, store backups in S3 or a similar durable store.

### Agent Setup

For Kubernetes-based agents (recommended for new deployments):

```yaml
# Jenkins K8s plugin config
apiVersion: v1
kind: ConfigMap
metadata:
  name: jenkins-agent-config
data:
  config.xml: |
    <cloud>
      <kubernetes>
        <name>kubernetes</name>
        <namespace>jenkins-agents</namespace>
        <serverUrl>https://kubernetes.default.svc</serverUrl>
        <defaultsProviderTemplate>jenkins-agent</defaultsProviderTemplate>
        <containerCap>10</containerCap>
      </kubernetes>
    </cloud>
```

Each build spins up a Pod in `jenkins-agents` namespace; on completion, the Pod is deleted. Isolation per build.

## Production Performance

Jenkins' typical performance:
- Controller CPU: 1-2 cores for a small instance (1000 builds/day); 4-8 cores for medium (10K builds/day).
- Controller memory: 4-16 GB (depends on plugins).
- Build latency: ~30 seconds (agent spin-up for K8s); faster for static agents.

For large deployments, multiple Jenkins instances are recommended (e.g., one per team or per environment).

## Comparison to Modern CI/CD Systems

| Aspect | Jenkins | GitLab CI | GitHub Actions | Argo Workflows |
|--------|---------|-----------|-----------------|-----------------|
| Origin | Sun 2004 (Hudson) | GitLab 2015 | GitHub 2019 | BlackRock 2017 |
| Architecture | Controller + Agents | Built-in to GitLab | GitHub-hosted + self-hosted | Kubernetes-native |
| Configuration | Groovy (Jenkinsfile) | YAML (.gitlab-ci.yml) | YAML (workflows) | YAML (Workflow CRD) |
| Plugin ecosystem | Largest (1800+) | Built-in | Marketplace | Catalog |
| Best for | Legacy CI/CD, plugins | All-in-one (code + CI) | GitHub-centric | K8s-native workflows |

Jenkins has the largest plugin ecosystem but is showing its age (Groovy DSL, controller is a SPOF). Modern alternatives are simpler and more cloud-native.

## Common Pitfalls

1. **Forgetting that the controller is a SPOF.** Without HA configuration, controller failure stops all CI/CD. Use a load balancer with active-passive.

2. **Forgetting that plugins can be incompatible.** New Jenkins versions break old plugins; old Jenkins can't use new plugins. Pin plugin versions; test upgrades in staging.

3. **Forgetting that builds are stateful on the controller.** Build artifacts and logs accumulate; clean them periodically.

4. **Forgetting that agent labels matter.** A job with `label 'docker'` won't run on agents without Docker. Configure labels carefully.

5. **Forgetting that the Jenkinsfile can be vulnerable.** Malicious Jenkinsfiles can execute arbitrary code on the agent. Restrict who can modify Jenkinsfiles; use script approval.

6. **Forgetting that Jenkins needs regular maintenance.** Restart weekly (for memory leaks); upgrade plugins monthly; upgrade Jenkins quarterly.

## References

- [Jenkins documentation](https://www.jenkins.io/doc/)
- [Jenkins User Documentation](https://www.jenkins.io/user-docs/)
- [Jenkins Pipeline (Jenkinsfile)](https://www.jenkins.io/doc/book/pipeline/)
- [Jenkins Kubernetes Plugin](https://plugins.jenkins.io/kubernetes/)
- [Jenkins Plugin Index](https://plugins.jenkins.io/)
- [CloudBees CI (enterprise Jenkins)](https://www.cloudbees.com/products/cloudbees-ci)
- [LWN: Jenkins overview (2020)](https://lwn.net/Articles/815575/)
