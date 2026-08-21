# AWS CloudFormation

AWS CloudFormation is an infrastructure-as-code (IaC) service, launched in 2011. It allows users to define AWS resources in a declarative template (YAML or JSON), and CloudFormation provisions and manages those resources as a "stack". This page covers the template model, the stack lifecycle, the drift detection, and the comparison to Terraform.

## The Template Model

A CloudFormation template is a YAML or JSON document:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: My web app stack

Parameters:
  InstanceType:
    Type: String
    Default: t3.micro
    AllowedValues: [t3.micro, t3.small, t3.medium]
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, staging, prod]

Resources:
  EC2Instance:
    Type: AWS::EC2::Instance
    Properties:
      InstanceType: !Ref InstanceType
      ImageId: ami-0abcdef1234567890
      SubnetId: subnet-abc123
      SecurityGroupIds:
        - !Ref InstanceSecurityGroup
      Tags:
        - Key: Environment
          Value: !Ref Environment
  
  InstanceSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Properties:
      GroupDescription: Allow HTTP/HTTPS
      VpcId: vpc-abc123
      SecurityGroupIngress:
        - IpProtocol: tcp
          FromPort: 80
          ToPort: 80
          CidrIp: 0.0.0.0/0
        - IpProtocol: tcp
          FromPort: 443
          ToPort: 443
          CidrIp: 0.0.0.0/0

Outputs:
  InstancePublicIP:
    Description: Public IP of the EC2 instance
    Value: !GetAtt EC2Instance.PublicIp
```

A template has:
- **Parameters**: user-supplied values at stack creation.
- **Resources**: AWS resources to create (the heart of the template).
- **Outputs**: values exported for cross-stack references or for user reference.
- **Mappings**: static lookup tables (e.g., region → AMI).
- **Conditions**: conditional resource creation.
- **Metadata**: template metadata.

## The Stack Lifecycle

A stack is a deployment of a template:

```bash
# Create a stack
aws cloudformation create-stack --stack-name my-stack \
    --template-body file://template.yaml \
    --parameters ParameterKey=Environment,ParameterValue=prod

# Update a stack (e.g., change instance type)
aws cloudformation update-stack --stack-name my-stack \
    --template-body file://template.yaml \
    --parameters ParameterKey=Environment,ParameterValue=prod

# Delete a stack (deletes all resources)
aws cloudformation delete-stack --stack-name my-stack
```

The stack lifecycle:
1. **CREATE**: CloudFormation creates all resources in dependency order. On failure, rolls back (deletes created resources).
2. **UPDATE**: CloudFormation computes the diff with the current state, then applies changes (creates, updates, deletes). On failure, rolls back.
3. **DELETE**: CloudFormation deletes all resources. Some resources (e.g., S3 buckets with content) need explicit `DeletionPolicy: Retain` to avoid deletion.

## Resource Dependencies

CloudFormation tracks dependencies automatically via `!Ref` and `!GetAtt`:

```yaml
Resources:
  VPC:
    Type: AWS::EC2::VPC
    Properties:
      CidrBlock: 10.0.0.0/16
  
  InternetGateway:
    Type: AWS::EC2::InternetGateway
  
  InternetGatewayAttachment:
    Type: AWS::EC2::VPCGatewayAttachment
    Properties:
      VpcId: !Ref VPC  ← depends on VPC
      InternetGatewayId: !Ref InternetGateway  ← depends on IGW
```

CloudFormation creates VPC and InternetGateway in parallel (no dependency); then creates the attachment (depends on both).

For explicit dependencies, use `DependsOn`:

```yaml
Resources:
  MyDatabase:
    Type: AWS::RDS::DBInstance
    DependsOn: MyDBSubnetGroup  ← explicit dependency
    Properties:
      DBSubnetGroupName: !Ref MyDBSubnetGroup
```

## Intrinsic Functions

CloudFormation has many built-in functions:

- `!Ref`: reference a parameter or resource.
- `!GetAtt`: get an attribute of a resource (e.g., `!GetAtt EC2Instance.PublicIp`).
- `!Sub`: string substitution (`!Sub "${Environment}-bucket"`).
- `!Join`: join strings (`!Join ["-", ["my", "bucket"]]`).
- `!Select`: select from a list (`!Select [0, !Ref AZs]`).
- `!If`: conditional (`!If [IsProd, "m5.large", "t3.small"]`).
- `!FindInMap`: lookup in a Mappings section.
- `!ImportValue`: import a value exported by another stack.
- `!GetAZs`: get availability zones for a region.
- `!Cidr`: compute subnet CIDR blocks from a VPC CIDR.

These functions make templates dynamic without external scripts.

## Nested Stacks and Cross-Stack References

For large templates, use nested stacks:

```yaml
Resources:
  VpcStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/vpc.yaml
      Parameters:
        CidrBlock: 10.0.0.0/16
  
  DatabaseStack:
    Type: AWS::CloudFormation::Stack
    Properties:
      TemplateURL: https://s3.amazonaws.com/my-bucket/db.yaml
      Parameters:
        VpcId: !GetAtt VpcStack.Outputs.VpcId  ← output of VpcStack
```

Nested stacks break a large template into reusable pieces.

Cross-stack references export values:

```yaml
# Stack A: outputs
Outputs:
  VpcId:
    Value: !Ref VPC
    Export:
      Name: my-vpc-id

# Stack B: imports
Resources:
  Database:
    Type: AWS::RDS::DBInstance
    Properties:
      VpcId: !ImportValue my-vpc-id
```

The export is global (within the account/region); any stack can import it. Deleting the exporting stack is blocked until importers are updated.

## Drift Detection

CloudFormation can detect "drift" — manual changes to resources:

```bash
aws cloudformation detect-stack-drift --stack-name my-stack
# Returns a drift detection ID.
# Wait for completion, then:
aws cloudformation describe-stack-resource-drifts --stack-name my-stack
```

Drift detection identifies resources whose config differs from the template. Common drifts: tags added manually, security groups modified, IAM policies updated.

For production, drift detection should run periodically; drifts should be either reconciled (the manual change is rolled back) or the template should be updated (to reflect the desired change).

## CloudFormation vs. Terraform

| Aspect | CloudFormation | Terraform |
|--------|---------------|-----------|
| Vendor | AWS | HashiCorp |
| State | AWS-managed | Self-managed (state file in S3, etc.) |
| Resources | AWS-only | Multi-cloud |
| Language | YAML/JSON | HCL |
| Cost | Free (you pay for resources) | Free (OSS) or paid (Terraform Cloud) |
| Drift detection | Built-in | Limited |
| Best for | AWS-only | Multi-cloud, hybrid |

CloudFormation is the choice for AWS-only; Terraform for multi-cloud. Both are mature; Terraform's HCL is more readable than CloudFormation's YAML.

## Production Patterns

### Pattern 1: Pipeline-Based Deployment

```text
Template → CodeCommit (git) → CodePipeline → CloudFormation (deploy to staging) → approval → CloudFormation (deploy to prod)
```

Use CodePipeline to deploy templates across environments with approval gates.

### Pattern 2: Cross-Stack References for VPC Sharing

```text
vpc-stack (creates VPC, subnets, gateways) → exports VpcId, SubnetIds
app-stack (deploys app) → imports VpcId, SubnetIds
db-stack (deploys DB) → imports VpcId, SubnetIds
```

The VPC is shared; app and db stacks are independent.

### Pattern 3: StackSets for Multi-Account/Region

```bash
aws cloudformation create-stack-set --stack-set-name my-stack-set \
    --template-body file://template.yaml \
    --capabilities CAPABILITY_NAMED_IAM

aws cloudformation create-stack-instances --stack-set-name my-stack-set \
    --accounts 123456789012,210987654321 \
    --regions us-east-1,eu-west-1
```

StackSets deploy a template to multiple accounts and regions in one operation. Useful for governance baselines (e.g., a default security group in every account).

## Common Pitfalls

1. **Forgetting that CloudFormation creates resources in dependency order, but deletes in reverse order.** Deleting a stack with a dependent resource (e.g., an RDS instance still in use) requires manual intervention.

2. **Forgetting that resource deletion can fail.** A non-empty S3 bucket can't be deleted by CloudFormation. Use a custom resource or `DeletionPolicy: Retain` to handle this.

3. **Forgetting that stack updates can replace resources.** Some property changes (e.g., RDS instance type) require replacement (the old resource is deleted, a new one is created). Plan for downtime.

4. **Forgetting that nested stacks can hit template limits.** Each stack is limited to 200 resources; nested stacks can exceed this if not broken up.

5. **Forgetting that CloudFormation doesn't roll back IAM changes.** A failed stack creation may leave IAM roles/policies behind (for safety). Manually clean up.

6. **Forgetting that stack drift detection is per-resource, not deep.** Some attributes (e.g., DynamoDB table's items) aren't checked. Use a custom monitoring tool for full drift detection.

## References

- [AWS CloudFormation documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html)
- [CloudFormation Template Reference](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-reference.html)
- [CloudFormation Drift Detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/detect-stack-drift.html)
- [CloudFormation StackSets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html)
- [CloudFormation vs Terraform](https://aws.amazon.com/blogs/infrastructure-and-automation/best-practices-for-using-cloudformation-and-terraform-together/)
- [AWS Quick Start (pre-built templates)](https://aws.amazon.com/quickstart/)
- [LWN: AWS CloudFormation overview (2020)](https://lwn.net/Articles/820133/)
