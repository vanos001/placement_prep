# Nginx Deep Dive

## Architecture

Nginx uses a **master-worker, event-driven, asynchronous** architecture that enables it to handle tens of thousands of concurrent connections with minimal memory per connection (~2-4 KB).

```
┌─────────────────────────────────────────────────────┐
│                  Master Process (root)              │
│  - Reads & validates configuration                  │
│  - Binds to ports (80, 443)                         │
│  - Manages worker processes (fork/restart)           │
│  - Maintains shared memory for cache metadata       │
└────────────┬──────────────────────┬──────────────────┘
             │                      │
    ┌────────▼────────┐   ┌────────▼────────┐
    │  Worker Process  │   │  Worker Process  │  ... (N workers)
    │  ┌────────────┐  │   │  ┌────────────┐  │
    │  │ Event Loop │  │   │  │ Event Loop │  │
    │  │ (epoll)    │  │   │  │ (epoll)    │  │
    │  └────────────┘  │   │  └────────────┘  │
    │  ┌────────────┐  │   │  ┌────────────┐  │
    │  │ Connections│  │   │  │ Connections│  │
    │  └────────────┘  │   │  └────────────┘  │
    └─────────────────┘   └─────────────────┘
```

Each worker runs a single-threaded event loop using **epoll** (Linux), **kqueue** (BSD/macOS), or **eventports** (Solaris). There is no thread-per-connection and no process-per-connection. A single worker handles thousands of connections by multiplexing I/O events.

Worker count: set to `auto` (matches CPU cores) or `worker_processes 4;` for 4-core systems.

## Configuration Structure

Nginx configuration is a hierarchy of **blocks** (contexts) containing **directives**:

```nginx
# main context (global)
worker_processes auto;
error_log /var/log/nginx/error.log warn;

events {                    # events block
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {                     # http block (shared by all servers)
    include       mime.types;
    default_type  application/octet-stream;

    # Shared across all server blocks
    sendfile        on;
    tcp_nopush      on;
    keepalive_timeout 65;

    upstream backend {     # upstream block
        server 10.0.1.10:8080;
        server 10.0.1.11:8080;
    }

    server {                # server block (virtual host)
        listen 80;
        server_name example.com;

        location /api/ {    # location block
            proxy_pass http://backend;
        }

        location /static/ {
            root /var/www/html;
            expires 30d;
        }
    }
}
```

Directive types:
- **Simple directive**: ends with `;` (e.g., `worker_processes auto;`)
- **Block directive**: contains `{ }` (e.g., `server { }`)
- **Inheritance**: child blocks inherit from parent; redefining a directive in a child overrides the parent

## Reverse Proxy Configuration

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://backend;

        # Pass client information
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        # Buffering (stores backend response in temp files if large)
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 16k;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Critical: always set `proxy_set_header Host $host` — without it, Nginx sends the upstream name to the backend, which breaks virtual hosting.

## Load Balancing

```nginx
upstream backend {
    # Load balancing methods
    # least_conn;          # Least connections
    # ip_hash;             # Client IP hash (session affinity)
    # hash $request_uri consistent;  # Consistent hashing on URI

    server 10.0.1.10:8080 weight=3;   # 3x the traffic
    server 10.0.1.11:8080 weight=1;
    server 10.0.1.12:8080 backup;     # Used only when others are down
    server 10.0.1.13:8080 max_fails=3 fail_timeout=30s;
}
```

| Method | Algorithm | Use Case |
--------|-----------|----------|
| **round-robin** (default) | Sequential | Homogeneous backends |
| **least_conn** | Fewest active connections | Variable request duration |
| **ip_hash** | Client IP modulo N | Session affinity (same IP → same server) |
| **hash** | Hash of any variable | Consistent hashing, A/B testing |
| **random** | Random selection | Simple, uniform distribution |

Health checks with `max_fails` and `fail_timeout`: after `max_fails` (default 1) failed requests within `fail_timeout` (default 10s), the server is marked unavailable for `fail_timeout` duration. For active health checks, use **Nginx Plus** (commercial) or the **nginx_upstream_check_module**.

## Caching (proxy_cache)

```nginx
# Define cache zone in http context
proxy_cache_path /var/cache/nginx levels=1:2
    keys_zone=api_cache:10m
    max_size=10g
    inactive=60m
    use_temp_path=off;

server {
    location /api/ {
        proxy_cache api_cache;
        proxy_cache_valid 200 10m;         # Cache 200 responses for 10 min
        proxy_cache_valid 404 1m;          # Cache 404 for 1 min
        proxy_cache_use_stale error timeout updating;  # Serve stale on error
        proxy_cache_bypass $http_cache_control;  # Respect no-cache
        proxy_cache_key "$scheme$request_method$host$request_uri";
        add_header X-Cache-Status $upstream_cache_status;
    }
}
```

| Parameter | Purpose |
-----------|---------|
| `keys_zone` | Shared memory zone for cache keys (1MB ≈ 8,000 keys) |
| `max_size` | Maximum disk usage for cached content |
| `inactive` | Remove items not accessed within this time |
| `proxy_cache_use_stale` | Serve stale content when upstream fails |
| `proxy_cache_lock` | Only one request populates cache for a given key (prevents stampede) |

## Rate Limiting (limit_req)

```nginx
# In http context
defined $binary_remote_addr zone=api_limit:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        limit_req_status 429;
    }
}
```

- `rate=10r/s`: 10 requests per second per IP (average)
- `burst=20`: allows 20 excess requests in a queue, processed at the rate limit
- `nodelay`: process burst requests immediately (without delaying)
- Without `nodelay`: burst requests are processed with 100ms delay each (spread over 2 seconds)
- `limit_conn`: limits concurrent connections (not request rate)

For distributed rate limiting, Nginx's `limit_req` is per-node. Use a shared key (like `$http_x_api_key`) or an external rate limiter (Redis + Lua, or an API gateway).

## TLS Termination

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # Modern TLS configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;    # TLS 1.3 should negotiate, not server-pick
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;           # Forward secrecy

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
}
```

## Compression

```nginx
# Gzip (built-in)
gzip on;
gzip_types text/plain text/css application/json application/javascript text/xml;
gzip_min_length 256;         # Don't compress small responses (overhead > savings)
gzip_comp_level 4;           # 1-9, 4-6 is the sweet spot

# Brotli (requires module: ngx_brotli)
brotli on;
brotli_comp_level 4;
brotli_types text/plain text/css application/json application/javascript;
brotli_min_length 256;
```

Brotli typically achieves 15-25% better compression than gzip at the same level, with similar CPU cost. Check browser support—Brotli is supported in all modern browsers. Serve Brotli with `Accept-Encoding: br` and fallback to gzip.

## References

- [Nginx Official Documentation](https://nginx.org/en/docs/)
- [High Performance Browser Networking — TLS](https://hpbn.co/transport-layer-security-tls/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

## Interview Questions

### Q1: Why can Nginx handle so many concurrent connections compared to Apache (prefork)?
**Answer**: Nginx uses an event-driven, asynchronous architecture with a single-threaded event loop per worker process. Each worker uses epoll/kqueue to multiplex thousands of connections on a single thread — it only does work when I/O events occur (readable, writable). Apache's prefork MPM uses one process per connection, consuming ~2-8 MB per connection. Nginx uses ~2-4 KB per connection (just the connection state structure). This means Nginx can handle 10,000+ concurrent connections on a single worker, while Apache would need 10,000 processes.

### Q2: Explain the proxy_cache and how you'd use it.
**Answer**: proxy_cache stores upstream responses on disk, keyed by a configurable cache key (default: `$scheme$proxy_host$request_uri`). I define a `proxy_cache_path` zone in the http context (specifying disk path, shared memory size, max size), then enable it per location with `proxy_cache zone_name`. I set `proxy_cache_valid` to control TTL per status code (200 for 10m, 404 for 1m). I use `proxy_cache_use_stale` to serve stale content when the upstream is down (improves resilience). `proxy_cache_lock` prevents cache stampede by allowing only one request to populate a cache entry. I add `X-Cache-Status` header to debug hit/miss rates.

### Q3: How does Nginx rate limiting work?
**Answer**: Nginx uses the `limit_req_zone` directive to define a shared memory zone that tracks request rates per key (typically `$binary_remote_addr` for per-IP limiting). The `rate` parameter sets the average rate (e.g., `10r/s`). `burst=20` creates a bucket of 20 excess requests that can be queued. Without `nodelay`, burst requests are processed at the rate limit (spread out); with `nodelay`, they're processed immediately. Requests exceeding burst + rate get a 503 (configurable to 429). This is a **leaky bucket** algorithm. Limitation: it's per-Nginx node, not distributed—use an external store for global rate limiting.

### Q4: What is the difference between proxy_buffering on and off?
**Answer**: With `proxy_buffering on` (default), Nginx reads the entire upstream response into buffers before sending it to the client. This frees up the upstream connection quickly and allows Nginx to serve the response from its buffers (enabling `proxy_cache`). With `proxy_buffering off`, Nginx streams the response to the client as it receives it from the upstream — useful for large file downloads or SSE/streaming where you want immediate delivery. The tradeoff: buffering adds latency (client waits for the full response to buffer) but improves upstream connection reuse. For streaming APIs, WebSockets, and large downloads, turn it off.

### Q5: How do you configure Nginx for zero-downtime deploys?
**Answer**: Nginx itself supports graceful reload (`nginx -s reload`): it starts new worker processes with the new config, which accept new connections while old workers finish their existing requests and then exit. For upstream application deploys, I use: (1) **Blue-green deployments** with upstream switching (change upstream servers, reload Nginx). (2) **Health check endpoints**: Nginx (Plus) or external check marks a server as down before draining. (3) **Slow start**: `slow_start=30s` in upstream config gradually sends traffic to a newly added server. (4) **Connection draining**: `proxy_pass` with `proxy_next_upstream_timeout` and graceful shutdown on the app side. Combined, these ensure no requests are dropped during a deploy.