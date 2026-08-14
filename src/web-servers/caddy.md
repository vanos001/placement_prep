# Caddy Web Server

## Overview

Caddy is a modern, open-source web server written in Go. Its headline feature is **automatic HTTPS** — it obtains and renews TLS certificates from Let's Encrypt (or other ACME CAs) with zero configuration. Caddy aims to be the most usable web server by eliminating entire categories of configuration that are error-prone in Nginx and Apache.

## Automatic HTTPS

Caddy provisions TLS certificates automatically when it sees a hostname:

```
# Caddyfile
example.com {
    # That's it. Caddy handles TLS automatically.
    reverse_proxy localhost:8080
}
```

How it works:
1. Caddy starts and sees `example.com` in the Caddyfile
2. It obtains a certificate via ACME (HTTP-01 or DNS-01 challenge)
3. Certificates are stored in `~/.local/share/caddy` (or `/var/lib/caddy`)
4. OCSP stapling is enabled by default
5. Certificates are renewed automatically ~30 days before expiry

For DNS challenges (wildcards, internal services):

```
example.com *.example.com {
    tls {
        dns cloudflare {env.CLOUDFLARE_API_TOKEN}
    }
    reverse_proxy localhost:8080
}
```

## Caddyfile Syntax

The Caddyfile is Caddy's configuration format — simpler and more opinionated than Nginx's config:

```
# Global options block
{
    admin off
    email admin@example.com
}

# Site block
example.com {
    # Static file serving
    root * /var/www/html
    file_server

    # Compression (brotli + gzip by default)
    encode

    # Reverse proxy
    handle /api/* {
        reverse_proxy backend:8080 {
            health_uri /health
            health_interval 10s
        }
    }

    # Rate limiting (Caddy 2.7+)
    handle /login {
        rate_limit {
            zone login
            key {remote_host}
            events 5
            window 1m
        }
        reverse_proxy auth:8080
    }

    # Logging
    log {
        output file /var/log/caddy/access.log
        format json
    }
}
```

Key differences from Nginx:
- No semicolons, no `server`/`location` block nesting for simple cases
- `handle` directives match in order (like Nginx location, but more explicit)
- Most defaults are secure and production-ready out of the box

## Caddy vs. Nginx

| Feature | Caddy | Nginx |
|---------|-------|-------|
| **Language** | Go | C |
| **TLS** | Automatic (ACME, built-in) | Manual config, certbot, or Lua scripts |
| **Config format** | Caddyfile (simple) + JSON (advanced) | nginx.conf (blocks, directives) |
| **Modules** | Plugins via xcaddy | Compile-time or dynamic modules |
| **HTTP/3** | Built-in (QUIC) | Requires nginx-quic build or Nginx 1.25+ | 
| **Reverse proxy** | Built-in, simple syntax | Requires proxy_* directives |
| **Performance** | Very good (Go net/http) | Excellent (epoll, highly optimized) |
| **Caching** | File cache (basic) | Advanced proxy_cache |
| **Rate limiting** | Built-in (v2.7+) | limit_req module |
| **Lua scripting** | No (Go plugins instead) | Yes (OpenResty) |
| **Ecosystem** | Growing, smaller | Massive, well-documented |
| **Configuration reload** | Automatic (file watch) or `caddy reload` | `nginx -s reload` |
| **Windows support** | First-class | Limited |
| **Commercial version** | No (open source) | Nginx Plus |

## When to Use Caddy

**Choose Caddy when:**
- You want zero-config HTTPS (personal projects, internal tools, small services)
- You need HTTP/3/QUIC support out of the box
- Your team values simplicity over fine-grained control
- You're serving static sites or simple reverse proxy setups
- You want automatic config reloading without a separate tool
- You're running in environments where manual TLS management is painful (edge, IoT)

**Choose Nginx when:**
- You need maximum performance at massive scale (top-tier traffic)
- You require advanced caching (proxy_cache with stale-while-revalidate)
- You use Lua/OpenResty for custom logic (authentication, WAF)
- You need mature, battle-tested configuration for complex routing
- Your organization already has Nginx expertise and runbooks
- You need commercial support (Nginx Plus)

## Advanced Caddy Features

### Dynamic configuration via JSON API
Caddy's internal config is JSON. The Caddyfile compiles to JSON. You can also manage Caddy entirely via its admin API:

```bash
# Get current config
curl https://localhost:2019/config/

# Add a site via API
curl -X POST https://localhost:2019/config/apps/http/servers/... \
  -H 'Content-Type: application/json' -d '{...}'
```

### On-demand TLS
Caddy can provision certificates on-demand when it first sees a hostname (useful for multi-tenant platforms):

```
{
    on_demand_tls {
        ask https://check.example.com/allowed
    }
}
https:// {
    tls on_demand
}
```

### Caddy Modules
Extend Caddy with plugins built in Go using `xcaddy`:

```bash
xcaddy build --with github.com/caddy-dns/cloudflare
```

Popular modules: caddy-dns/* (DNS providers), caddy-ratelimit, caddy-security, caddy-trace (OpenTelemetry).

## References

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Caddy vs. Nginx](https://caddyserver.com/docs/comparisons)
- [Caddyfile Reference](https://caddyserver.com/docs/caddyfile)

## Interview Questions

### Q1: What makes Caddy different from Nginx?
**Answer**: Caddy's primary differentiator is **automatic HTTPS** — it provisions and renews TLS certificates from Let's Encrypt with zero configuration. Caddy is written in Go, making it easy to extend with Go plugins via `xcaddy`. It has HTTP/3 support built-in. The Caddyfile syntax is simpler and more opinionated than Nginx's config. However, Nginx has a much larger ecosystem, more mature caching, Lua scripting support (OpenResty), and higher raw performance at massive scale. Caddy is ideal for simplicity and developer experience; Nginx is ideal for complex, high-traffic production setups.

### Q2: How does Caddy's automatic HTTPS work?
**Answer**: When Caddy starts with a hostname in the Caddyfile, it initiates an ACME challenge (HTTP-01 by default). For HTTP-01, Caddy creates a temporary `.well-known/acme-challenge/` endpoint, Let's Encrypt verifies ownership by making an HTTP request, and Caddy receives the certificate. For DNS-01 challenges (needed for wildcards or internal services), Caddy creates a TXT record via a DNS provider plugin. Certificates are stored locally and automatically renewed ~30 days before expiry. OCSP stapling is enabled by default for fast TLS handshakes.

### Q3: When would you choose Nginx over Caddy in a production environment?
**Answer**: I'd choose Nginx when: (1) The system requires advanced caching with stale-while-revalidate, cache locking, and fine-grained cache control. (2) We need Lua scripting for custom authentication, WAF rules, or complex routing logic (OpenResty). (3) The traffic scale demands maximum performance — Nginx's C-based event loop has lower per-request overhead than Go's runtime. (4) The organization has existing Nginx expertise, runbooks, and operational processes. (5) We need commercial support (Nginx Plus) with active health checks and dynamic upstream configuration. Caddy would be the choice for greenfield projects prioritizing simplicity and developer experience.

### Q4: Does Caddy support hot configuration reload?
**Answer**: Yes, Caddy automatically watches the Caddyfile for changes and reloads gracefully. You can also trigger a reload manually with `caddy reload`. During reload, Caddy starts new listeners and gracefully transitions existing connections. Unlike Nginx, which requires you to explicitly run `nginx -s reload` (or set up a file watcher), Caddy handles this natively. The underlying mechanism is similar to Nginx — new configuration is loaded, old connections continue on the old configuration, and new connections use the new configuration.

### Q5: How does Caddy handle HTTP/3?
**Answer**: Caddy has built-in HTTP/3 (QUIC) support — no extra build or configuration required. When Caddy serves HTTPS, it automatically listens on both TCP (HTTP/2) and UDP (HTTP/3). Clients that support HTTP/3 will negotiate it via Alt-Svc headers. Caddy was one of the first web servers to have production-ready HTTP/3. Nginx added experimental HTTP/3 support in 1.25.0 but requires a special build. For a project that wants to serve content over HTTP/3 with minimal effort, Caddy is the strongest choice.