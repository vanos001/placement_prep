# Terraform

## HCL Syntax

```hcl
# Variables
variable "region" {
  type    = string
  default = "us-east-1"
}

# Provider
provider "aws" {
  region = var.region
}

# Resource
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"
  
  tags = {
    Name = "web-server"
  }
}

# Output
output "instance_ip" {
  value = aws_instance.web.public_ip
}
```

## Core Concepts

### Resources
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

### Data Sources
```hcl
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*"]
  }
}
```

### Modules
```hcl
# modules/vpc/main.tf
variable "cidr" { type = string }
resource "aws_vpc" "main" {
  cidr_block = var.cidr
}
output "vpc_id" { value = aws_vpc.main.id }

# Root module
module "vpc" {
  source = "./modules/vpc"
  cidr   = "10.0.0.0/16"
}
```

## State Management

```bash
# State file stores resource mappings
terraform state list
terraform state show aws_instance.web
terraform state mv aws_instance.web aws_instance.app
terraform state rm aws_instance.old

# Remote state (S3 backend)
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
    dynamodb_table = "terraform-locks"  # state locking
  }
}
```

## Workflow

```bash
terraform init          # Initialize, download providers
terraform plan          # Preview changes
terraform apply         # Apply changes
terraform destroy       # Destroy all resources
terraform import        # Import existing resources
terraform fmt           # Format files
terraform validate      # Validate syntax
```

## Drift Detection

```bash
# Detect manual changes
terraform plan  # Shows differences between state and real infrastructure

# Fix drift
terraform apply  # Reconciles real infrastructure with config
```

## Interview Questions

**Q: What is Terraform state and why is it needed?**
A: State maps Terraform config to real-world resources. It tracks metadata, enables performance (knows what changed), and supports collaboration (remote state with locking). Without state, Terraform wouldn't know which resources to update vs create vs delete.

**Q: How do you handle secrets in Terraform?**
A: (1) Use `sensitive = true` on variables, (2) store secrets in Vault/SSM and use `data` sources, (3) never commit `.tfvars` with secrets, (4) use remote state with encryption, (5) mark outputs as sensitive.

**Q: What is the difference between `terraform plan` and `terraform apply`?**
A: `plan` is a dry-run that shows what changes will be made without applying them. `apply` executes those changes. Always review `plan` output before `apply`. `terraform apply -auto-approve` skips the confirmation prompt (use in CI/CD only).

## References

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
