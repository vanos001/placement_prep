# Infrastructure as Code Overview

## Imperative vs Declarative

| Aspect | Imperative | Declarative |
|---|---|---|
| Approach | "How to do it" | "What I want" |
| Example | Bash scripts, Pulumi | Terraform, CloudFormation |
| State | You manage | Tool manages |
| Idempotency | Manual | Built-in |

## Mutable vs Immutable Infrastructure

| Aspect | Mutable | Immutable |
|---|---|---|
| Updates | SSH + configure in place | Replace entire instance |
| Tools | Ansible, Puppet | Packer + Terraform |
| Drift | Common | Impossible |
| Rollback | Manual | Switch to old image |

## Key Tools

| Tool | Type | Language | Approach |
|---|---|---|---|
| **Terraform** | Provisioning | HCL | Declarative |
| **Ansible** | Configuration | YAML | Procedural |
| **Pulumi** | Provisioning | Any language | Imperative |
| **CloudFormation** | Provisioning | JSON/YAML | Declarative |
| **CDK** | Provisioning | Any language | Imperative → declarative |
