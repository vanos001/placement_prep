# AWS ECS (Elastic Container Service)

Amazon ECS (Elastic Container Service) is AWS's managed container orchestration service, launched in 2014 (before Kubernetes was widely adopted). It runs Docker containers on AWS, with two launch types: EC2 (you manage the EC2 instances) and Fargate (AWS manages the infrastructure). This page covers the architecture, the task definition model, the service scheduler, and the comparison to Kubernetes.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  ECS Control Plane (managed by AWS)                         │
│  - Task scheduler                                          │
│  - Service auto-scaling                                   │
│  - Integration with ALB, CloudWatch, IAM                  │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ API calls                    │ task placement
        ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  Fargate (serverless)     │    │  EC2 launch type           │
│  - AWS manages VMs         │    │  - You manage EC2 instances│
│  - Per-task billing         │    │  - ECS agent on each       │
└──────────────────────────┘    └──────────────────────────┘
```

ECS is simpler than Kubernetes — there's no etcd, no API server to manage. AWS manages the control plane; you define tasks and services.

## The Task Definition

A task definition is a JSON document describing a "task" (a group of containers):

```json
{
  "family": "myapp",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::123:role/ecs-task-execution",
  "taskRoleArn": "arn:aws:iam::123:role/myapp-task",
  "containerDefinitions": [
    {
      "name": "myapp",
      "image": "123.dkr.ecr.us-east-1.amazonaws.com/myapp:latest",
      "portMappings": [
        { "containerPort": 8080, "hostPort": 8080 }
      ],
      "environment": [
        { "name": "DB_HOST", "value": "db.example.com" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/myapp",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

A task definition:
- Has a family (logical name) and revision (each update creates a new revision).
- Specifies CPU/memory (Fargate: limited to specific combinations).
- Lists container definitions (multiple containers per task).
- Specifies IAM roles (task role for app permissions; execution role for ECS to pull images, log).

## Tasks vs. Services

- **Task**: a single instance of a task definition (a running set of containers).
- **Service**: a scheduler that ensures N tasks run continuously.

```bash
# Run a one-off task (e.g., a database migration)
aws ecs run-task --task-definition myapp:5 --cluster my-cluster

# Create a service (long-running)
aws ecs create-service --service-name myapp-svc --task-definition myapp:5 \
    --desired-count 3 --cluster my-cluster
```

A service auto-restarts failed tasks; maintains the desired count; integrates with ALB for load balancing.

## The Scheduler

ECS's service scheduler:
1. Reads the desired count (e.g., 3 tasks).
2. Checks the actual count.
3. If less, schedules new tasks on available capacity (EC2 instances or Fargate).
4. If more, terminates extra tasks.
5. On task failure, restarts.
6. For rolling updates: gradually replaces old tasks with new ones.

For EC2 launch type, the scheduler also:
1. Places tasks on EC2 instances based on resource availability.
2. Respects "placement constraints" (e.g., distinct instances to avoid co-location).
3. Uses "placement strategies" (e.g., spread by AZ, bin-pack by CPU).

## Fargate

Fargate is the serverless launch type:
- No EC2 instances to manage.
- Per-task billing (CPU + memory + duration).
- Tasks run in their own micro-VM (Firecracker) for isolation.

```bash
aws ecs run-task --task-definition myapp-fargate:5 --launch-type FARGATE \
    --network-configuration awsvpcConfiguration='{subnets=["subnet-abc"],securityGroups=["sg-xyz"],assignPublicIp="ENABLED"}'
```

Fargate's pricing: ~$0.040/hour for 0.5 vCPU + 1 GB RAM (us-east-1, 2024). For always-on services, this is more expensive than EC2 but eliminates operational overhead.

## ECS + ALB Integration

For load-balanced services:

```bash
aws ecs create-service --service-name myapp-svc \
    --task-definition myapp:5 \
    --desired-count 3 \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/myapp-tg/...
```

The ALB routes traffic to the tasks; ECS registers/deregisters tasks with the ALB during deployments.

For Fargate with awsvpc networking, the ALB's target type must be `ip` (not `instance`).

## Production Use Cases

### Long-Running Web Service

```bash
aws ecs create-service --service-name web --task-definition web:5 \
    --desired-count 3 --launch-type FARGATE \
    --load-balancers targetGroupArn=... \
    --network-configuration awsvpcConfiguration=...
```

3 tasks across 3 AZs, ALB-fronted, Fargate-managed.

### Scheduled Batch Job

```bash
aws events put-rule --name daily-etl --schedule-expression "cron(0 1 * * ? *)"
aws events put-targets --rule daily-etl --targets Id=1,Arn=arn:aws:ecs:...:cluster/my-cluster,EcsParameters={TaskDefinitionArn=arn:aws:ecs:...:task-definition/etl:5,TaskCount=1}
```

CloudWatch Events triggers an ECS task on a schedule (e.g., 1am daily).

### Worker Queue

```bash
aws ecs create-service --service-name worker --task-definition worker:5 \
    --desired-count 5 --launch-type FARGATE
# Worker tasks read from SQS, process, repeat.
```

For scaling on queue depth, use CloudWatch alarm + Service Auto-Scaling:
- Alarm: `ApproximateNumberOfMessagesVisible > 100`.
- Action: scale up by 2 tasks.

## Comparison to Kubernetes

| Aspect | ECS | Kubernetes (EKS) |
|--------|-----|------------------|
| Control plane | AWS-managed | AWS-managed (EKS) |
| Worker nodes | EC2 or Fargate | EC2 or Fargate (EKS-Fargate) |
| Container runtime | Docker / containerd | containerd |
| Networking | awsvpc (ENI per task) | CNI (Calico, Cilium) |
| Service discovery | Cloud Map | Service (ClusterIP) |
| Load balancing | ALB | Ingress controller + ALB |
| Storage | EBS, EFS | PersistentVolume (EBS, EFS) |
| Simplicity | High | Medium |
| Best for | AWS-native, simple apps | Complex, multi-cloud |

ECS is simpler (less to learn, less to manage). Kubernetes is more powerful (richer ecosystem, portability).

## Common Pitfalls

1. **Forgetting that ECS tasks need an IAM execution role.** Without it, ECS can't pull from ECR or write to CloudWatch Logs.

2. **Forgetting that Fargate tasks have ENIs.** Each Fargate task gets an ENI in your VPC's subnets. Plan subnet IP capacity.

3. **Forgetting that awsvpc networking requires the ALB target type to be "ip".** With `instance` target type, awsvpc tasks can't register.

4. **Forgetting that Fargate has resource limits.** Max 4 vCPU and 30 GB RAM per task. For larger tasks, use EC2 launch type.

5. **Forgetting that ECS doesn't auto-scale without configuration.** Service Auto-Scaling requires CloudWatch alarms and a scaling policy. Set up explicitly.

6. **Forgetting that the task definition revision is immutable.** Once registered, you can't modify it; you must create a new revision. This is for safety (auditable changes) but means deployments create new revisions.

## References

- [AWS ECS documentation](https://docs.aws.amazon/AmazonECS/latest/developerguide/Welcome.html)
- [ECS Task Definitions](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html)
- [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html)
- [ECS Service Auto-Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [ECS + ALB Integration](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/load-balancer-types.html)
- [ECS vs EKS (AWS blog)](https://aws.amazon.com/blogs/containers/amazon-ecs-vs-amazon-eks/)
- [LWN: ECS overview (2021)](https://lwn.net/Articles/820133/)
