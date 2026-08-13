# Authorization

## Overview

Authorization determines what an authenticated user is allowed to do. While authentication answers "Who are you?", authorization answers "What are you allowed to do?" It's the mechanism that enforces access control policies across systems.

## Access Control Models

### Discretionary Access Control (DAC)

The resource owner decides who can access their resources.

```
┌──────────┐     owns      ┌──────────┐
│  Alice    │──────────────▶│  File A   │
│ (Owner)   │               │           │
└──────────┘               └──────────┘
     │                          ▲
     │ grants read              │
     ▼                          │
┌──────────┐    can read    ┌────┘
│   Bob     │───────────────┘
└──────────┘
```

**Characteristics**:
- Owner-controlled permissions
- Flexible but hard to manage at scale
- Used in Unix file permissions, Windows NTFS

```bash
# Unix DAC example
chmod 750 myfile.txt  # Owner: rwx, Group: r-x, Others: ---
chown alice:devs myfile.txt
```

### Mandatory Access Control (MAC)

A central authority controls access based on security labels.

```
Security Levels:  TOP SECRET > SECRET > CONFIDENTIAL > UNCLASSIFIED

┌─────────────┐           ┌─────────────┐
│ Alice        │           │ Document X   │
│ Clearance:   │           │ Classification:│
│ SECRET       │──can read─▶│ CONFIDENTIAL │
└─────────────┘           └─────────────┘

┌─────────────┐           ┌─────────────┐
│ Bob          │           │ Document Y   │
│ Clearance:   │           │ Classification:│
│ CONFIDENTIAL │──cannot──▶│ TOP SECRET   │
└─────────────┘           └─────────────┘
```

**Characteristics**:
- System-enforced, not owner-controlled
- Used in military/government systems
- Bell-LaPadula model (no read up, no write down)

### Role-Based Access Control (RBAC)

Access is granted based on roles assigned to users.

```
┌──────────┐    assigned    ┌──────────┐    has      ┌──────────┐
│  Users   │───────────────▶│  Roles   │────────────▶│Permissions│
└──────────┘                └──────────┘             └──────────┘

User ──▶ Role ──▶ Permissions

Examples:
  Alice ──▶ Admin ──▶ [read, write, delete, manage_users]
  Bob   ──▶ Editor ──▶ [read, write]
  Carol ──▶ Viewer ──▶ [read]
```

```python
from enum import Enum
from functools import wraps

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"

ROLE_PERMISSIONS = {
    "admin": [p for p in Permission],
    "editor": [Permission.READ, Permission.WRITE],
    "viewer": [Permission.READ],
}

class RBACMiddleware:
    def __init__(self):
        self.user_roles = {}  # user_id -> set of roles
    
    def assign_role(self, user_id, role):
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()
        self.user_roles[user_id].add(role)
    
    def has_permission(self, user_id, required_permission):
        roles = self.user_roles.get(user_id, set())
        for role in roles:
            if required_permission in ROLE_PERMISSIONS.get(role, []):
                return True
        return False
    
    def require_permission(self, permission):
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                user_id = get_current_user_id()
                if not self.has_permission(user_id, permission):
                    raise PermissionError(f"Requires {permission.value}")
                return f(*args, **kwargs)
            return decorated
        return decorator

rbac = RBACMiddleware()

@app.route('/admin/users')
@rbac.require_permission(Permission.MANAGE_USERS)
def manage_users():
    return get_all_users()

@app.route('/documents/<id>', methods=['DELETE'])
@rbac.require_permission(Permission.DELETE)
def delete_document(id):
    return delete_doc(id)
```

**RBAC hierarchy with role inheritance**:

```
         ┌─────────┐
         │ Super    │
         │ Admin    │
         └────┬────┘
              │ inherits
         ┌────┴────┐
         │  Admin   │
         └────┬────┘
              │ inherits
    ┌─────────┼─────────┐
    │         │         │
┌───┴──┐ ┌───┴──┐ ┌───┴──┐
│Editor│ │Moder-│ │Analyst│
│      │ │ator  │ │       │
└───┬──┘ └───┬──┘ └───┬──┘
    │        │        │
    └────────┼────────┘
             │ inherits
         ┌───┴──┐
         │Viewer│
         └──────┘
```

### Attribute-Based Access Control (ABAC)

Access decisions based on attributes of users, resources, and environment.

```
Decision = f(User_Attributes, Resource_Attributes, 
             Action_Attributes, Environment_Attributes)

Example Policy:
  ALLOW if:
    user.department == resource.department AND
    user.clearance >= resource.classification AND
    action == "read" AND
    environment.time BETWEEN 09:00 AND 18:00
```

```python
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

@dataclass
class AccessRequest:
    user: Dict[str, Any]
    resource: Dict[str, Any]
    action: str
    environment: Dict[str, Any]

class ABACEngine:
    def __init__(self):
        self.policies = []
    
    def add_policy(self, name, condition):
        self.policies.append({'name': name, 'condition': condition})
    
    def evaluate(self, request: AccessRequest) -> bool:
        for policy in self.policies:
            if policy['condition'](request):
                return True
        return False

engine = ABACEngine()

# Define policies
engine.add_policy(
    "department_access",
    lambda req: (
        req.user.get('department') == req.resource.get('department')
    )
)

engine.add_policy(
    "business_hours",
    lambda req: (
        9 <= req.environment.get('hour', 0) <= 18 and
        req.environment.get('day_of_week', 0) < 5
    )
)

engine.add_policy(
    "owner_access",
    lambda req: (
        req.user.get('id') == req.resource.get('owner_id')
    )
)

# Evaluate
request = AccessRequest(
    user={'id': 1, 'department': 'engineering', 'clearance': 3},
    resource={'type': 'document', 'department': 'engineering', 'classification': 2, 'owner_id': 1},
    action='read',
    environment={'hour': 14, 'day_of_week': 2}
)

allowed = engine.evaluate(request)
```

**ABAC vs RBAC**:

| Aspect | RBAC | ABAC |
|--------|------|------|
| Basis | Roles | Attributes |
| Flexibility | Moderate | High |
| Complexity | Simple | Complex |
| Scalability | Good for stable orgs | Good for dynamic policies |
| Example | "Admin can delete" | "Manager of dept X can delete during business hours" |

### Capability-Based Access Control

Users hold unforgeable tokens (capabilities) that grant specific access.

```
┌──────────┐  capability_token  ┌──────────┐
│  User    │───────────────────▶│ Resource │
│          │  "read:file_123"   │          │
└──────────┘                    └──────────┘

A capability is like a ticket:
  - It's unforgeable (cryptographically signed)
  - It specifies what you can do
  - You present it to access the resource
```

```python
import jwt
import uuid

SECRET = "capability-signing-key"

def create_capability(subject, resource, actions, expires_in=3600):
    """Create a signed capability token."""
    capability = {
        'sub': subject,
        'resource': resource,
        'actions': actions,  # ['read', 'write']
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'jti': str(uuid.uuid4())
    }
    return jwt.encode(capability, SECRET, algorithm='HS256')

def verify_capability(token, required_action):
    """Verify a capability token grants the required action."""
    try:
        payload = jwt.decode(token, SECRET, algorithms=['HS256'])
        if required_action in payload.get('actions', []):
            return payload
        return None
    except jwt.InvalidTokenError:
        return None

# Usage
cap = create_capability(
    subject="user_123",
    resource="/documents/report.pdf",
    actions=["read"],
    expires_in=1800
)

# Later: verify capability
result = verify_capability(cap, "read")  # Grants access
result = verify_capability(cap, "delete")  # Denied
```

**Used in**: AWS STS, Google Cloud IAM, distributed systems.

## OAuth 2.0 Scopes

Scopes define what specific actions a client application can perform.

```
┌──────────┐     Request scope:      ┌──────────┐
│  Client  │     "read write"        │  Auth    │
│   App    │────────────────────────▶│  Server  │
│          │                          │          │
│          │◀────────────────────────│          │
│          │  Token with granted     │          │
│          │  scopes: ["read"]       │          │
└──────────┘                          └──────────┘

User may grant only "read" even though "write" was requested.
```

```python
from flask import Flask, request, jsonify
from functools import wraps

VALID_SCOPES = {
    'read:profile': 'Read your profile information',
    'write:profile': 'Update your profile',
    'read:posts': 'Read your posts',
    'write:posts': 'Create and edit posts',
    'delete:posts': 'Delete your posts',
    'admin:users': 'Manage all users'
}

def require_scope(required_scope):
    """Decorator to check OAuth scope."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = extract_token(request)
            if not token:
                return jsonify({'error': 'Token required'}), 401
            
            granted_scopes = token.get('scope', '').split()
            
            if required_scope not in granted_scopes:
                return jsonify({
                    'error': 'insufficient_scope',
                    'error_description': f'Required scope: {required_scope}',
                    'required': required_scope,
                    'granted': granted_scopes
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/api/posts', methods=['GET'])
@require_scope('read:posts')
def get_posts():
    return jsonify(get_user_posts(request.user_id))

@app.route('/api/posts', methods=['POST'])
@require_scope('write:posts')
def create_post():
    return jsonify(create_user_post(request.user_id, request.json))

@app.route('/api/posts/<id>', methods=['DELETE'])
@require_scope('delete:posts')
def delete_post(id):
    return jsonify(delete_user_post(request.user_id, id))
```

## Policy Enforcement Patterns

### Middleware-Based Enforcement

```python
class AuthorizationMiddleware:
    def __init__(self, app, policy_engine):
        self.app = app
        self.engine = policy_engine
    
    def __call__(self, environ, start_response):
        request = Request(environ)
        
        # Skip auth for public routes
        if request.path in PUBLIC_ROUTES:
            return self.app(environ, start_response)
        
        # Extract user from token
        user = extract_user(request)
        if not user:
            return self._unauthorized(start_response)
        
        # Check authorization
        resource = self._identify_resource(request)
        action = self._map_method_to_action(request.method)
        
        if not self.engine.is_allowed(user, resource, action):
            return self._forbidden(start_response)
        
        # Attach user context
        environ['user'] = user
        return self.app(environ, start_response)
```

### Decorator-Based Enforcement

```python
def authorize(action, resource_type=None):
    """Universal authorization decorator."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            
            # Determine resource
            if resource_type:
                resource_id = kwargs.get('id')
                resource = get_resource(resource_type, resource_id)
            else:
                resource = {'type': resource_type or 'api'}
            
            # Check permission
            if not check_permission(user, action, resource):
                audit_log(user, action, resource, 'DENIED')
                raise Forbidden("Insufficient permissions")
            
            audit_log(user, action, resource, 'ALLOWED')
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/api/documents/<int:id>', methods=['PUT'])
@authorize('update', 'document')
def update_document(id):
    doc = Document.query.get_or_404(id)
    doc.update(request.json)
    return jsonify(doc.to_dict())
```

### Policy-as-Code (OPA/Rego)

```rego
# policy.rego - Open Policy Agent example
package authz

default allow = false

# Admin can do anything
allow {
    input.user.roles[_] == "admin"
}

# Users can read their own documents
allow {
    input.action == "read"
    input.resource.owner == input.user.id
}

# Editors can write to their department's documents
allow {
    input.action == "write"
    input.user.roles[_] == "editor"
    input.user.department == input.resource.department
}

# Business hours restriction for sensitive resources
allow {
    input.resource.classification <= 2
    input.env.hour >= 9
    input.env.hour <= 18
}
```

## Common Authorization Vulnerabilities

### Insecure Direct Object Reference (IDOR)

```python
# VULNERABLE: Direct object access without authorization check
@app.route('/api/invoices/<int:id>')
def get_invoice(id):
    invoice = Invoice.query.get_or_404(id)  # Any user can access any invoice
    return jsonify(invoice.to_dict())

# SECURE: Check ownership
@app.route('/api/invoices/<int:id>')
def get_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    if invoice.user_id != get_current_user().id:
        raise Forbidden("Not your invoice")
    return jsonify(invoice.to_dict())
```

### Horizontal vs Vertical Privilege Escalation

```
Horizontal: User A accesses User B's data (same privilege level)
Vertical:   Regular user accesses admin functions (higher privilege)
```

### Mass Assignment

```python
# VULNERABLE: User can set any field
@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    user.update(request.json)  # Could include 'role': 'admin'
    return jsonify(user.to_dict())

# SECURE: Whitelist allowed fields
ALLOWED_FIELDS = {'name', 'email', 'bio'}

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    safe_data = {k: v for k, v in request.json.items() if k in ALLOWED_FIELDS}
    user.update(safe_data)
    return jsonify(user.to_dict())
```

## Interview Questions

### Q1: What's the difference between RBAC and ABAC?

**Answer**: RBAC grants access based on predefined roles (e.g., "Admin can delete"). ABAC evaluates attributes dynamically (e.g., "Manager of dept X can delete during business hours if clearance >= 2"). RBAC is simpler to implement and manage. ABAC is more flexible and handles complex policies better. Many systems use RBAC with ABAC-like extensions.

### Q2: How would you implement authorization in a microservices architecture?

**Answer**: Use a centralized authorization service or policy engine (like OPA). Each service validates JWT tokens and checks permissions. Token claims include roles/scopes. Use an API gateway for consistent policy enforcement. Consider using capability-based tokens for service-to-service communication. Implement a shared authorization library to avoid duplication.

### Q3: Explain the principle of least privilege.

**Answer**: Grant the minimum permissions needed to perform a task. This limits the blast radius if an account is compromised. Implementation: default deny, explicit grants, time-limited access, just-in-time provisioning, regular access reviews.

### Q4: How do you handle authorization in a system with millions of users?

**Answer**: Cache permission decisions (Redis/Memcached). Use hierarchical roles to reduce per-user policy size. Pre-compute and denormalize permission sets. Use database indexes on user-role mappings. Implement lazy evaluation. Consider using a dedicated authorization service with sub-millisecond response times.

### Q5: What is the confused deputy problem?

**Answer**: A privileged program is tricked into misusing its authority. Example: A service with database admin access receives a user request to delete a table — it executes it because it has the permission, not checking if the user should have that access. Prevention: always check the original requester's permissions, not just the service's capabilities.

### Q6: How would you design a permission system for a multi-tenant SaaS?

**Answer**: Isolate tenants at the database level (row-level security or separate schemas). Include tenant_id in all authorization checks. Use RBAC within tenants. Implement tenant-level quotas and limits. Consider using PostgreSQL RLS or middleware that injects tenant context into all queries.
