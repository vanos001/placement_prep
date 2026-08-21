# AWS IAM Internals

AWS Identity and Access Management (IAM) is the access control service for AWS, launched in 2010. It manages users, roles, groups, and policies that control who can do what in AWS. This page covers the architecture, the policy evaluation logic, the role assumption mechanism, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  IAM Service (global, multi-region)                         │
│  - Stores users, groups, roles, policies                    │
│  - Evaluates access decisions                              │
│  - Issues temporary credentials (STS)                       │
└─────────────────────────────────────────────────────────────┘
        ▲
        │ API call (with credentials)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Service (S3, EC2, Lambda, etc.)                       │
│  - Receives the API call                                    │
│  - Asks IAM: "Does this caller have permission?"            │
│  - IAM returns Allow or Deny                                │
│  - Service executes or returns 403                          │
└─────────────────────────────────────────────────────────────┘
```

IAM is global — there's no per-region IAM. Policies are evaluated in the region where the API call is made (for latency), but the policy data is global.

## The Policy Model

IAM policies are JSON documents that define permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::my-bucket/*",
      "Condition": {
        "StringEquals": {
          "aws:SourceIp": ["10.0.0.0/8"]
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

Each statement:
- `Effect`: Allow or Deny.
- `Action`: list of AWS API actions (e.g., `s3:GetObject`).
- `Resource`: ARN of the resource (e.g., `arn:aws:s3:::my-bucket/*`).
- `Condition`: optional conditions (e.g., MFA, IP, time).

## The Policy Evaluation Logic

When a principal (user or role) makes an API call, AWS evaluates all applicable policies:

```text
1. Default Deny: if no policy applies, deny.
2. Explicit Deny: any policy with Effect=Deny and matching Action/Resource → deny.
   (Deny wins, regardless of Allow statements.)
3. Explicit Allow: if any policy with Effect=Allow and matching Action/Resource → allow.
4. Default Deny: if no Allow applies, deny.
```

The order:
- Explicit Deny > Explicit Allow > Default Deny.

Policies evaluated:
- **Identity-based**: attached to the user/role/group (managed or inline).
- **Resource-based**: attached to the resource (e.g., S3 bucket policy, KMS key policy).
- **Permission boundaries**: max-permissions boundary on a user/role.
- **Service Control Policies (SCPs)**: organization-level max-permissions.
- **Session policies**: temporary, attached to an STS session.

All these are intersected: the effective permission is the intersection of all applicable policies.

## Users, Groups, Roles

### Users

A long-lived IAM identity with credentials:
- Access key ID + secret access key (for API/CLI).
- Username + password (for AWS console).

Users are deprecated for most use cases; use roles (with temporary credentials) instead.

### Groups

A collection of users with shared policies. Useful for managing permissions across teams.

### Roles

An IAM identity that can be assumed (with temporary credentials):
- No long-lived credentials.
- Assumed via STS (Security Token Service).
- Temporary credentials expire (15 minutes to 12 hours).

```bash
# Assume a role
aws sts assume-role --role-arn arn:aws:iam::123:role/my-role --role-session-name my-session
# Returns: AccessKeyId, SecretAccessKey, SessionToken, Expiration
```

The assumed credentials are used for subsequent API calls until expiration.

## The Trust Policy

A role has a "trust policy" that defines who can assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

This trust policy allows EC2 to assume the role. Other principals (users, other roles, AWS services) can be added.

## EC2 Instance Profiles

For EC2 instances to assume a role, AWS uses "instance profiles":

```text
1. Create a role with the desired permissions.
2. Create an instance profile that wraps the role.
3. Launch the EC2 instance with the instance profile.
4. The instance's metadata service (169.254.169.254) provides temporary credentials.
5. Applications on the instance read the credentials and use them for AWS API calls.
```

The credentials auto-rotate (~6 hours), so no long-lived credentials on the instance.

## IAM Roles for Service Accounts (IRSA)

For EKS (Kubernetes) pods, AWS uses IRSA:

```text
1. Create an IAM role with trust for the Kubernetes OIDC provider.
2. Create a Kubernetes Service Account annotated with the role ARN.
3. The pod uses the Service Account; the token is exchanged for AWS credentials.
```

This is the equivalent of EC2 instance profiles for Kubernetes — pods get temporary AWS credentials.

## STS (Security Token Service)

STS issues temporary credentials:

```bash
# Assume a role
aws sts assume-role --role-arn arn:aws:iam::123:role/x --role-session-name y

# Get credentials for the current caller (federated)
aws sts get-session-token

# Get caller identity
aws sts get-caller-identity
# Returns: UserId, Account, Arn
```

STS is a global service. The credentials are valid for the duration specified (default 1 hour, max 12 hours).

## Federation

For enterprise SSO, AWS supports federation:
- **SAML 2.0**: e.g., Okta, Azure AD.
- **OIDC**: e.g., Google Workspace.
- **Custom**: e.g., a custom identity broker.

The federation flow:
1. User authenticates to the IdP (Okta).
2. IdP issues a SAML assertion.
3. User sends the SAML assertion to AWS STS `AssumeRoleWithSAML`.
4. STS returns temporary AWS credentials.
5. User uses the credentials for AWS API access.

This avoids long-lived IAM users; users authenticate via their corporate IdP.

## Production Patterns

### Pattern 1: Role-Based Access

```text
Users (or federated identities) → assume role by environment
  dev-role (low privileges)
  staging-role (medium privileges)
  prod-role (high privileges, with MFA required)
```

Each environment has its own role; users assume the appropriate one. Production role requires MFA.

### Pattern 2: Cross-Account Access

```text
Account A's role (dev-deploy) → assume role in Account B (staging-deploy)
```

Cross-account access via trust policy: Account B's role trusts Account A's role. The AssumeRole API call is signed with Account A's credentials; STS issues Account B's credentials.

### Pattern 3: Service-to-Service

```text
EC2 instance (with role A) → assume role B (in another account) → call API
```

The instance's role A has permission to assume role B; the application calls AssumeRole with role B's ARN.

## Common Pitfalls

1. **Creating IAM users with long-lived access keys.** Compromised keys are catastrophic. Use roles (with temporary credentials) instead.

2. **Forgetting that explicit Deny wins.** A "deny all" policy anywhere in the chain overrides all Allows. Audit your SCPs and permission boundaries.

3. **Forgetting that resource-based policies are evaluated differently.** For S3 bucket policies, the principal can be in a different account; cross-account access needs both the bucket policy AND the principal's identity policy.

4. **Forgetting that SCPs are organization-level.** An SCP can restrict what users/roles in an OU can do, even if their IAM policy allows it. Audit SCPs at the org level.

5. **Forgetting that IAM changes take time to propagate.** After a policy change, the change takes ~5-15 seconds to propagate globally. Don't be confused by intermittent access right after a change.

6. **Forgetting that the IAM policy simulator is your friend.** The simulator lets you test what a principal can do before deploying. Use it.

## Comparison to Other IAM Systems

| Aspect | AWS IAM | Azure AD | GCP IAM | Okta |
|--------|---------|----------|---------|------|
| Cloud | AWS | Azure | GCP | Any (SaaS) |
| Identity model | Users, roles, groups | Users, groups, service principals | Users, service accounts | Users, groups |
| Auth | Long-lived + STS | OAuth/OIDC | OAuth/OIDC | SAML, OIDC |
| Best for | AWS | Azure | GCP | Cross-cloud SSO |

AWS IAM is AWS-specific; Azure AD and GCP IAM are similar but for their respective clouds. Okta is the cross-cloud SSO choice.

## References

- [AWS IAM documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html)
- [IAM Policy evaluation logic](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation_logic.html)
- [IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [AWS STS documentation](https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html)
- [IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [AWS Federation with SAML](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_saml.html)
- [IAM Policy Simulator](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_simulator.html)
- [LWN: AWS IAM overview (2021)](https://lwn.net/Articles/820133/)
