# Secrets Management

## Overview

Secrets management is the practice of securely storing, distributing, rotating, and auditing sensitive credentials like API keys, database passwords, encryption keys, and certificates. Poor secrets management is one of the most common causes of data breaches.

```
┌─────────────────────────────────────────────┐
│              Secrets Lifecycle                │
│                                              │
│  Generate → Store → Distribute → Use →      │
│  Rotate → Revoke → Audit                     │
└─────────────────────────────────────────────┘
```

## Types of Secrets

```
┌─────────────────────────────────────────────┐
│              Secret Types                     │
├─────────────┬───────────────────────────────┤
│ Credentials │ Passwords, API keys, tokens   │
│ Keys        │ Encryption keys, signing keys │
│ Certificates│ TLS certs, SSH keys           │
│ Connection  │ Database URLs, connection strs │
│ Tokens      │ OAuth tokens, session tokens  │
└─────────────┴───────────────────────────────┘
```

## Environment Variables

The most common (but basic) approach to secrets management.

### Basic Usage

```bash
# .env file (NEVER commit to git)
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
API_KEY=sk-1234567890abcdef
JWT_SECRET=super-secret-key-here
REDIS_URL=redis://localhost:6379
```

```python
import os
from dotenv import load_dotenv

# Load .env file (development only)
load_dotenv()

# Access secrets
DATABASE_URL = os.environ['DATABASE_URL']  # Raises KeyError if missing
API_KEY = os.environ.get('API_KEY')  # Returns None if missing
JWT_SECRET = os.environ.get('JWT_SECRET', 'default-for-dev')  # With fallback

# Validate required secrets at startup
REQUIRED_SECRETS = ['DATABASE_URL', 'JWT_SECRET', 'API_KEY']

def validate_secrets():
    missing = [s for s in REQUIRED_SECRETS if s not in os.environ]
    if missing:
        raise RuntimeError(f"Missing required secrets: {missing}")
```

### Risks of .env Files

```
┌─────────────────────────────────────────────┐
│           .env File Risks                     │
├─────────────────────────────────────────────┤
│ ❌ Committed to git accidentally            │
│ ❌ Stored in plaintext on disk              │
│ ❌ No access control (any process can read) │
│ ❌ No rotation mechanism                    │
│ ❌ No audit trail                           │
│ ❌ Shared across team via insecure channels │
│ ❌ Left in Docker images                    │
│ ❌ Visible in /proc/<pid>/environ           │
└─────────────────────────────────────────────┘
```

### Safer .env Practices

```bash
# .gitignore - ALWAYS include
.env
.env.local
.env.*.local
*.pem
*.key

# Pre-commit hook to prevent accidental commits
#!/bin/bash
if git diff --cached --name-only | grep -E '\.env$|\.pem$|\.key$'; then
    echo "ERROR: Attempting to commit secret files!"
    exit 1
fi
```

## HashiCorp Vault

Vault is the industry standard for secrets management.

### Vault Architecture

```
┌─────────────────────────────────────────────┐
│              Vault Architecture               │
│                                              │
│  ┌──────────┐     ┌──────────────────────┐  │
│  │ Clients  │────▶│    Vault Server      │  │
│  │ (Apps)   │     │                      │  │
│  └──────────┘     │  ┌────────────────┐  │  │
│                   │  │  Secret Engine  │  │  │
│                   │  │  (KV, Database, │  │  │
│                   │  │   AWS, PKI)     │  │  │
│                   │  └────────────────┘  │  │
│                   │                      │  │
│                   │  ┌────────────────┐  │  │
│                   │  │  Auth Method   │  │  │
│                   │  │  (Token, LDAP, │  │  │
│                   │  │   AWS, K8s)    │  │  │
│                   │  └────────────────┘  │  │
│                   │                      │  │
│                   │  ┌────────────────┐  │  │
│                   │  │  Audit Backend │  │  │
│                   │  │  (File, Syslog)│  │  │
│                   │  └────────────────┘  │  │
│                   └──────────────────────┘  │
│                          │                  │
│                          ▼                  │
│                   ┌──────────────┐          │
│                   │  Storage     │          │
│                   │  (Consul,    │          │
│                   │   PostgreSQL)│          │
│                   └──────────────┘          │
└─────────────────────────────────────────────┘
```

### Vault Usage

```python
import hvac  # HashiCorp Vault Python client

class VaultSecretsManager:
    def __init__(self, url, token):
        self.client = hvac.Client(url=url, token=token)
    
    def get_secret(self, path, key=None):
        """Retrieve a secret from Vault KV engine."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        data = response['data']['data']
        if key:
            return data.get(key)
        return data
    
    def set_secret(self, path, data):
        """Store a secret in Vault."""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=data
        )
    
    def rotate_secret(self, path, key):
        """Rotate a specific secret value."""
        import secrets
        new_value = secrets.token_urlsafe(32)
        current = self.get_secret(path)
        current[key] = new_value
        self.set_secret(path, current)
        return new_value
    
    def delete_secret(self, path):
        """Delete a secret."""
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)

# Usage
vault = VaultSecretsManager(
    url='https://vault.example.com:8200',
    token=os.environ['VAULT_TOKEN']
)

# Get database credentials
db_creds = vault.get_secret('database/creds/postgresql')
# Returns: {'username': 'v-token-abc-123', 'password': 'A1b2-C3d4...'}

# Dynamic database credentials (Vault generates them)
def get_db_connection():
    creds = vault.get_secret('database/creds/my-app')
    return create_engine(
        f"postgresql://{creds['username']}:{creds['password']}@db:5432/mydb"
    )
```

### Dynamic Secrets

```
Traditional: Static credentials (created once, used forever)
             ┌──────────┐
             │ App      │──uses──▶ DB (user: admin, pass: static123)
             └──────────┘         (same creds for months)

Vault Dynamic: Credentials generated on-demand, auto-expire
             ┌──────────┐         ┌──────────┐
             │ App      │──asks──▶│  Vault   │
             │          │◀──gets──│          │
             │          │         │ Generates│
             │          │         │ temp DB  │
             │          │         │ creds    │
             └──────────┘         └──────────┘
                  │
                  │ uses temp creds (valid 1 hour)
                  ▼
             ┌──────────┐
             │ Database │
             └──────────┘
```

## AWS Secrets Manager

```python
import boto3
import json

class AWSSecretsManager:
    def __init__(self, region='us-east-1'):
        self.client = boto3.client('secretsmanager', region_name=region)
    
    def get_secret(self, secret_name):
        """Retrieve a secret."""
        response = self.client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    
    def create_secret(self, name, description, secret_dict):
        """Create a new secret."""
        self.client.create_secret(
            Name=name,
            Description=description,
            SecretString=json.dumps(secret_dict)
        )
    
    def rotate_secret(self, secret_name):
        """Enable automatic rotation."""
        self.client.rotate_secret(
            SecretId=secret_name,
            RotationRules={'AutomaticallyAfterDays': 30}
        )

# Usage
secrets = AWSSecretsManager()
db_creds = secrets.get_secret('prod/database/credentials')
connection = create_engine(
    f"postgresql://{db_creds['username']}:{db_creds['password']}@host/db"
)
```

## Key Rotation

Key rotation is the practice of periodically replacing cryptographic keys.

```
┌─────────────────────────────────────────────┐
│              Key Rotation Strategy            │
│                                              │
│  Key Version 1 (created Jan)                 │
│  ├── Active: encrypts new data              │
│  ├── Used to decrypt old data               │
│  │                                           │
│  Key Version 2 (created Apr)                 │
│  ├── Active: encrypts new data              │
│  ├── Key 1 still decrypts old data          │
│  │                                           │
│  Key Version 3 (created Jul)                 │
│  ├── Active: encrypts new data              │
│  ├── Re-encrypt old data with Key 3         │
│  └── Retire Key 1                           │
└─────────────────────────────────────────────┘
```

```python
class KeyRotator:
    def __init__(self, key_store):
        self.key_store = key_store
    
    def get_current_key(self):
        """Get the current active encryption key."""
        return self.key_store.get_active_key()
    
    def rotate_key(self):
        """Generate new key and re-encrypt critical data."""
        # Generate new key
        new_key = os.urandom(32)
        new_version = self.key_store.get_next_version()
        
        # Store new key as active
        self.key_store.add_key(
            version=new_version,
            key=new_key,
            status='active'
        )
        
        # Mark old key as 'retiring'
        old_key = self.key_store.get_active_key()
        self.key_store.update_status(old_key.version, 'retiring')
        
        # Re-encrypt high-priority data (background job)
        self.schedule_re_encryption(old_key, new_key)
        
        # After re-encryption complete, mark old key as 'retired'
        return new_version
    
    def decrypt_with_version(self, ciphertext, key_version):
        """Decrypt using the specified key version."""
        key = self.key_store.get_key(key_version)
        return decrypt(key, ciphertext)
```

## Secret Injection Patterns

### Sidecar Pattern (Kubernetes)

```yaml
# Kubernetes pod with Vault sidecar
apiVersion: v1
kind: Pod
metadata:
  name: my-app
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
      readOnly: true
  
  - name: vault-agent
    image: hashicorp/vault:latest
    args: ['agent', '-config=/etc/vault/config.hcl']
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
    - name: vault-config
      mountPath: /etc/vault
  
  volumes:
  - name: secrets
    emptyDir:
      medium: Memory  # tmpfs, never written to disk
  - name: vault-config
    configMap:
      name: vault-agent-config
```

### Init Container Pattern

```yaml
apiVersion: v1
kind: Pod
spec:
  initContainers:
  - name: secret-fetcher
    image: vault-init:latest
    env:
    - name: VAULT_ADDR
      value: "https://vault:8200"
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
  
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: secrets
      mountPath: /etc/secrets
      readOnly: true
```

### Environment Variable Injection

```python
# Docker Compose with secrets
# docker-compose.yml
services:
  app:
    image: my-app:latest
    environment:
      - DATABASE_URL_FILE=/run/secrets/db_url
    secrets:
      - db_url

secrets:
  db_url:
    file: ./secrets/db_url.txt
```

```python
# Application code to read Docker/K8s secrets
def get_secret_from_file(env_var):
    """Read secret from file (Docker/K8s secrets)."""
    file_path = os.environ.get(f"{env_var}_FILE")
    if file_path:
        with open(file_path, 'r') as f:
            return f.read().strip()
    return os.environ.get(env_var)

DATABASE_URL = get_secret_from_file('DATABASE_URL')
```

## Secrets in CI/CD

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Deploy
      env:
        # GitHub encrypted secrets
        DATABASE_URL: ${{ secrets.DATABASE_URL }}
        API_KEY: ${{ secrets.API_KEY }}
      run: |
        echo "Deploying with encrypted secrets..."
        ./deploy.sh
```

### Avoiding Secret Leaks in CI/CD

```bash
# Mask secrets in logs
echo "::add-mask::${SECRET_VALUE}"

# Use environment files instead of env vars (more secure)
echo "DATABASE_URL=${SECRET_DB_URL}" >> $GITHUB_ENV

# Scan for leaked secrets
# Install gitleaks or trufflehog
gitleaks detect --source . --verbose
```

## Secret Scanning

```python
import re
import subprocess

SECRET_PATTERNS = {
    'AWS Access Key': r'AKIA[0-9A-Z]{16}',
    'AWS Secret Key': r'[0-9a-zA-Z/+]{40}',
    'GitHub Token': r'gh[ps]_[A-Za-z0-9_]{36,}',
    'Generic API Key': r'[aA][pP][iI]_?[kK][eE][yY].*["\'][0-9a-zA-Z]{32,}["\']',
    'Private Key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
    'JWT': r'eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_.+/=]+',
    'Database URL': r'(postgres|mysql|mongodb)://[^\s]+',
}

def scan_for_secrets(content, filename=""):
    """Scan content for potential secrets."""
    findings = []
    for name, pattern in SECRET_PATTERNS.items():
        matches = re.finditer(pattern, content)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            findings.append({
                'type': name,
                'file': filename,
                'line': line_num,
                'match': match.group()[:20] + '...'  # Truncate for safety
            })
    return findings

# Pre-commit hook
def pre_commit_scan():
    """Scan staged files for secrets before commit."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        capture_output=True, text=True
    )
    
    for filename in result.stdout.strip().split('\n'):
        if not filename:
            continue
        try:
            with open(filename, 'r') as f:
                content = f.read()
            findings = scan_for_secrets(content, filename)
            if findings:
                print(f"⚠️ Potential secrets found in {filename}:")
                for f in findings:
                    print(f"  Line {f['line']}: {f['type']} - {f['match']}")
                return True
        except (FileNotFoundError, UnicodeDecodeError):
            continue
    return False
```

## Best Practices Summary

```
┌─────────────────────────────────────────────┐
│           Secrets Management Rules            │
├─────────────────────────────────────────────┤
│ 1. Never commit secrets to version control  │
│ 2. Use a secrets manager (Vault, AWS SM)    │
│ 3. Rotate secrets regularly                 │
│ 4. Use least-privilege access               │
│ 5. Audit secret access                      │
│ 6. Encrypt secrets at rest and in transit   │
│ 7. Use dynamic/short-lived credentials      │
│ 8. Scan for leaked secrets                  │
│ 9. Have a secret incident response plan     │
│10. Automate secret management               │
└─────────────────────────────────────────────┘
```

## Interview Questions

### Q1: Why shouldn't you store secrets in environment variables?

**Answer**: Environment variables are visible in `/proc/<pid>/environ`, can leak in error messages and logs, are inherited by child processes, have no access control, no rotation mechanism, no audit trail, and can be exposed in crash dumps. They're better than hardcoding but worse than a secrets manager. For production, use Vault or cloud-native secret managers.

### Q2: How does dynamic secret generation work?

**Answer**: Instead of static credentials, systems like Vault generate temporary credentials on-demand. For databases, Vault creates a temporary user with limited permissions and a TTL. When the TTL expires, the credentials are automatically revoked. Benefits: no shared long-lived credentials, automatic rotation, fine-grained access control, audit trail.

### Q3: How do you handle secrets in a microservices architecture?

**Answer**: Use a centralized secrets manager (Vault). Each service authenticates to Vault using its identity (Kubernetes service account, AWS IAM role). Vault issues short-lived credentials per service. Use service mesh (Istio) for mTLS between services. Implement secret rotation without downtime using dual-key periods.

### Q4: What is the envelope encryption pattern?

**Answer**: A data encryption key (DEK) encrypts the actual data. A key encryption key (KEK) encrypts the DEK. The encrypted DEK is stored alongside the data. To decrypt, use the KEK to decrypt the DEK, then use the DEK to decrypt the data. This limits KEK usage and allows easy re-encryption by just re-wrapping the DEK.

### Q5: How do you handle a secret leak in production?

**Answer**: (1) Immediately rotate the compromised secret, (2) Revoke all sessions/tokens using that secret, (3) Audit access logs for unauthorized usage, (4) Identify the scope of the leak, (5) Notify affected parties if necessary, (6) Fix the root cause (how was it leaked?), (7) Implement preventive measures (scanning, access controls), (8) Document the incident.
