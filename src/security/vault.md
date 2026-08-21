# HashiCorp Vault

Vault is a secret management tool, originally developed by HashiCorp in 2015 and released as open source (MPL 2.0) with a commercial Enterprise version. It provides secure storage, access control, audit logging, and dynamic secret generation for credentials, certificates, API keys, and other sensitive data. This page covers the architecture, the seal/unseal mechanism, the secret backends, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Vault Cluster (3-5 nodes, HA via Raft or Consul backend)   │
│  ┌─────────────────────┐                                   │
│  │  Active Node         │                                   │
│  │  - Serves requests   │                                   │
│  │  - Raft leader       │                                   │
│  └─────────────────────┘                                   │
│  ┌─────────────────────┐                                   │
│  │  Standby Node        │                                   │
│  │  - Replicates state  │                                   │
│  │  - Doesn't serve     │                                   │
│  └─────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
        │
        │ API (HTTPS)
        ▼
    Applications, CI/CD pipelines, operators
```

Vault is unique among secret managers in its design:
- **Encrypted storage**: all secrets are encrypted at rest with a master key.
- **Shamir's secret sharing**: the master key is split into N shares; K of N are needed to reconstruct.
- **Seal/unseal**: when sealed, Vault can't decrypt or serve secrets. Unsealing requires K shares.

## The Seal/Unseal Mechanism

When Vault starts, it's sealed. To unseal:

1. The operator provides K unseal keys (out of N total).
2. Vault reconstructs the master key (Shamir's secret sharing).
3. Vault decrypts the encryption key (stored on disk, encrypted with the master key).
4. Vault can now decrypt stored secrets and serve requests.

This protects against:
- **Disk theft**: the disk has only the encrypted master key; without K shares, the data is unrecoverable.
- **Operator compromise**: no single operator can unseal Vault alone (K of N).
- **Cold restart**: a restarted Vault requires manual unseal (or auto-unseal via cloud KMS).

For production, HashiCorp offers **auto-unseal** via cloud KMS (AWS KMS, GCP KMS, Azure Key Vault). The unseal key is stored in the cloud KMS; Vault fetches it on startup, eliminating manual unseal.

## Secret Backends

Vault has many "secret backends" — each generates, stores, or manages a different type of secret:

### Static Secrets (KV backend)

```bash
# Store a static secret
vault kv put secret/myapp/db_password value=supersecret

# Read it
vault kv get secret/myapp/db_password
```

The KV backend is a simple key-value store. Useful for static credentials that don't change frequently.

### Dynamic Secrets (Database backend)

```bash
# Configure a database backend
vault write database/config/my-db \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@db:5432/mydb" \
    allowed_roles="readonly"

# Define a role (creates a temporary user)
vault write database/roles/readonly \
    db_name=my-db \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}'; \
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Get a temporary credential
vault read database/creds/readonly
# Returns: { "username": "v-token-readonly-abc123", "password": "..." , "lease_id": "...", "lease_duration": 3600 }
```

The database backend dynamically creates database users, each with a short TTL (e.g., 1 hour). No long-lived shared credentials; each request gets a unique user.

Other dynamic backends: AWS (creates IAM users), PKI (issues X.509 certs), SSH (issues SSH certs).

### Encryption as a Service (Transit backend)

```bash
# Create an encryption key
vault write -f transit/keys/my-key

# Encrypt data
vault write transit/encrypt/my-key plaintext=$(base64 <<< "Hello, world")
# Returns: { "ciphertext": "vault:v1:..." }

# Decrypt
vault write transit/decrypt/my-key ciphertext="vault:v1:..."
# Returns: { "plaintext": "SGVsbG8sIHdvcmxk" }
```

The Transit backend does encryption without storing the data. Applications use Vault as an encryption service; the master key never leaves Vault.

## Authentication Methods

Vault needs to authenticate clients before issuing secrets. Methods include:

- **AppRole**: role-based for machines (role_id + secret_id).
- **Kubernetes**: Kubernetes service accounts.
- **AWS IAM**: IAM roles.
- **GitHub**: GitHub teams.
- **LDAP/AD**: enterprise SSO.
- **OIDC/JWT**: identity providers.

```bash
# Configure Kubernetes auth
vault auth enable kubernetes
vault write auth/kubernetes/config \
    kubernetes_host="https://k8s.default.svc:443"

# Create a role for the "myapp" service account
vault write auth/kubernetes/role/myapp \
    bound_service_account_names=myapp \
    bound_service_account_namespaces=default \
    policies=myapp-policy \
    ttl=1h
```

A pod authenticates by mounting its service account token and sending it to Vault:

```bash
# From inside a pod
vault write auth/kubernetes/login role=myapp jwt=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
# Returns a Vault token; use it for subsequent secret reads.
```

## Policies

Policies define what a client can do:

```hcl
# myapp-policy.hcl
path "secret/data/myapp/*" {
    capabilities = ["read"]
}

path "database/creds/readonly" {
    capabilities = ["read"]
}

path "transit/encrypt/my-key" {
    capabilities = ["update"]
}

path "transit/decrypt/my-key" {
    capabilities = ["update"]
}
```

Each client (via their auth method) gets assigned policies. The policy language is HCL (HashiCorp Configuration Language).

## Audit Logging

Vault can log every API call to one or more audit backends:

```bash
# Enable file audit
vault audit enable file file_path=/var/log/vault/audit.log

# Enable syslog audit
vault audit enable syslog
```

Each audit entry includes:
- Timestamp, request ID, operation type.
- Auth info (which client, via which method).
- The path accessed.
- The response (with sensitive fields hashed).

Audit logs are essential for compliance (SOC 2, HIPAA, PCI).

## Production Deployment

```hcl
# vault.hcl (config file)
ui = true
disable_mlock = false

storage "raft" {
  path = "/var/lib/vault/data"
  node_id = "vault-1"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_cert_file = "/etc/vault/tls/vault.crt"
  tls_key_file = "/etc/vault/tls/vault.key"
}

api_addr = "https://vault-1:8200"
cluster_addr = "https://vault-1:8201"
```

Key flags:
- `storage raft`: Raft-replicated storage (Vault 0.4+).
- `listener tcp`: HTTPS listener.
- `disable_mlock = false`: enable mlock (prevents swap-out of secrets).

For HA, run 3-5 Vault nodes with Raft storage. The active node serves; standbys replicate.

## Production Performance

Vault's published performance on a 3-node cluster:
- Static secret read: ~10 ms.
- Dynamic secret (DB user creation): ~100 ms (depends on the database).
- Transit encryption: ~1 ms per encrypt/decrypt.
- Throughput: ~1000 ops/sec per node.

For high-throughput encryption (e.g., encrypting every DB row), use the Transit backend with client-side caching.

## Common Pitfalls

1. **Forgetting that Vault requires careful planning for unseal.** A restarted Vault requires unseal. For HA, use auto-unseal (cloud KMS).

2. **Forgetting that dynamic secrets have TTLs.** A database user created by Vault expires; the application must request a new one. Don't cache the credential for longer than the TTL.

3. **Forgetting that the audit log is required.** Without audit logging, you can't trace who accessed what. Configure it before going to production.

4. **Forgetting that Vault's storage backend is critical.** The Raft backend requires fast disk (NVMe SSD). Don't use cloud object storage for the Raft backend.

5. **Forgetting that mlock prevents swap-out but doesn't prevent memory dumps.** A core dump of a Vault process reveals the master key in memory. Disable core dumps for the Vault process.

6. **Forgetting that policies need to be specific.** A policy like `path "secret/*" { capabilities = ["read"] }` gives access to all secrets. Use specific paths per application.

## Comparison to Other Secret Managers

| Aspect | Vault | AWS Secrets Manager | GCP Secret Manager | Azure Key Vault |
|--------|-------|---------------------|---------------------|------------------|
| Deployment | Self-hosted or HCP Vault | AWS-managed | GCP-managed | Azure-managed |
| Dynamic secrets | Yes | Limited | No | Yes |
| Transit (EaaS) | Yes | No | No | Yes |
| Multi-cloud | Yes | AWS only | GCP only | Azure only |
| Open source | Yes (MPL 2.0) | No | No | No |

Vault's strength is multi-cloud and dynamic secrets. Cloud-native secret managers are simpler for single-cloud.

## References

- [HashiCorp Vault documentation](https://developer.hashicorp.com/vault/docs)
- [Vault GitHub repository](https://github.com/hashicorp/vault)
- [Vault: Internals (Architecture)](https://developer.hashicorp.com/vault/docs/internals/architecture)
- [Vault: Dynamic Secrets](https://developer.hashicorp.com/vault/docs/secrets/databases)
- [Vault: Auto-Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal#auto-unseal)
- [Vault: Kubernetes Auth](https://developer.hashicorp.com/vault/docs/auth/kubernetes)
- [Vault vs AWS Secrets Manager](https://www.hashicorp.com/blog/vault-vs-aws-secrets-manager)
- [LWN: Vault overview (2020)](https://lwn.net/Articles/820130/)
