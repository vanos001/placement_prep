# Web Servers Overview

## Key Web Servers

| Server | Model | Best For |
|---|---|---|
| **Nginx** | Event-driven | Reverse proxy, static files, high concurrency |
| **Apache** | Process/thread (MPM) | .htaccess, mod_php, legacy apps |
| **Caddy** | Go-based, automatic TLS | Simplicity, auto-HTTPS |

## Why Web Servers Matter

- Every web application needs one (or more)
- TLS termination, compression, caching, rate limiting
- Load balancing across application servers
- Serving static content efficiently
- Security layer (WAF, IP filtering)
