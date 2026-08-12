# Infrastructure as Code Interview Questions

**Q: What is Infrastructure as Code?**
A: Managing infrastructure through machine-readable config files rather than manual processes. Benefits: version control, reproducibility, automation, documentation, collaboration, drift detection.

**Q: How do you manage Terraform state in a team?**
A: (1) Remote state (S3, GCS, Terraform Cloud), (2) state locking (DynamoDB, GCS), (3) workspaces for environments, (4) never commit state files to git, (5) use `terraform import` for existing resources.

**Q: What is drift in IaC?**
A: When real infrastructure diverges from the IaC config (e.g., someone manually changes a security group). Detected by `terraform plan`. Fixed by re-applying or importing changes. Prevented by RBAC (deny manual changes) and CI/CD pipelines.

**Q: How do you test IaC?**
A: (1) `terraform validate` (syntax), (2) `terraform plan` (dry-run), (3) `tflint` (linting), (4) `checkov`/`tfsec` (security scanning), (5) `terratest` (integration tests), (6) policy-as-code (OPA, Sentinel).

## References

- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Ansible Documentation](https://docs.ansible.com/)
