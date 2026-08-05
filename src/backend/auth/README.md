# Authentication & Authorization

Security is non-negotiable in backend systems. This section covers the protocols and patterns for verifying identity and controlling access.

## In This Section

- [OAuth 2.0](./oauth.md) — Delegated authorization framework
- [JWT](./jwt.md) — JSON Web Tokens for stateless authentication
- [Session Management](./session-management.md) — Server-side session strategies

## Authentication vs Authorization

| Aspect | Authentication | Authorization |
|--------|---------------|---------------|
| Question | "Who are you?" | "What can you do?" |
| Purpose | Verify identity | Grant access |
| Mechanism | Credentials, tokens | Policies, roles |
| Order | First | Second |

## Common Authentication Methods

- **API Keys** — Simple, for server-to-server
- **OAuth 2.0** — Delegated access, user-facing
- **mTLS** — Mutual TLS for service-to-service
- **JWT** — Stateless tokens with claims
- **SAML** — Enterprise SSO
