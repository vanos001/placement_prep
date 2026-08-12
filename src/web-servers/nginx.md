# Web Servers — Nginx, Apache, Caddy

## Nginx

### Architecture

Nginx uses an **event-driven, asynchronous** architecture:

```
Master Process (root)
├── Worker Process 1 (epoll/kqueue event loop)
├── Worker Process 2
├── Worker Process 3
└── Worker Process 4
```

- **Master**: Reads config, binds ports, manages workers
- **Workers**: Handle connections via event loop (non-blocking)
- Each worker can handle thousands of concurrent connections
- No thread-per-connection model (unlike Apache prefork)

### Configuration

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
events {
    worker_connections 1024;
}

http {
    upstream backend {
        least_conn;
        server 10.0.0.1:8080 weight=3;
        server 10.0.0.2:8080;
        server 10.0.0.3:8080 backup;
    }

    server {
        listen 80;
        server_name example.com;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name example.com;

        ssl_certificate /etc/ssl/cert.pem;
        ssl_certificate_key /etc/ssl/key.pem;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://backend;
        }
    }
}
```

### Load Balancing Algorithms

| Algorithm | Directive | Behavior |
|---|---|---|
| Round Robin | (default) | Distributes requests evenly |
| Least Connections | `least_conn` | Sends to server with fewest active connections |
| IP Hash | `ip_hash` | Same client IP always goes to same server |
| Weighted | `weight=N` | Proportional distribution |
| Random | `random two least_conn` | Random with two choices |

### Reverse Proxy

```nginx
location /api/ {
    proxy_pass http://backend;  # trailing slash strips /api/
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_connect_timeout 5s;
    proxy_read_timeout 60s;
    proxy_send_timeout 60s;
}
```

### Caching

```nginx
http {
    proxy_cache_path /var/cache/nginx levels=1:2 
                     keys_zone=my_cache:10m max_size=10g;
    
    location / {
        proxy_cache my_cache;
        proxy_cache_valid 200 1h;
        proxy_cache_valid 404 1m;
        proxy_cache_use_stale error timeout updating;
        add_header X-Cache-Status $upstream_cache_status;
    }
}
```

### Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn:10m;
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_conn conn 10;
    }
}
```

## Apache

### Architecture (MPM Modules)

| MPM | Model | Use Case |
|---|---|---|
| **prefork** | Process per connection | Legacy, PHP mod_php |
| **worker** | Threads per process | Better memory usage |
| **event** | Async keep-alive | Best performance, closest to Nginx |

### Key Features

```apache
# Virtual Host
<VirtualHost *:80>
    ServerName example.com
    DocumentRoot /var/www/html
    
    # Reverse Proxy
    ProxyPass /api/ http://localhost:8080/
    ProxyPassReverse /api/ http://localhost:8080/
    
    # URL Rewriting
    RewriteEngine On
    RewriteRule ^/old/(.*)$ /new/$1 [R=301,L]
    
    # Caching
    CacheEnable disk /
    CacheDefaultExpire 3600
</VirtualHost>
```

### Nginx vs Apache

| Aspect | Nginx | Apache |
|---|---|---|
| Architecture | Event-driven | Process/thread-based |
| Static files | Excellent | Good |
| Dynamic content | Proxy to app server | mod_php, mod_python |
| Configuration | Centralized | .htaccess per directory |
| Memory usage | Low | Higher (prefork) |
| Concurrent connections | 10K+ per worker | Limited by processes/threads |
| Load balancing | Built-in | mod_proxy_balancer |

## Interview Questions

**Q: Why is Nginx faster than Apache for static files?**
A: Nginx uses event-driven I/O (epoll/kqueue) — a single worker handles thousands of connections without blocking. Apache prefork creates a process per connection, consuming more memory and CPU for context switching. Apache's event MPM narrows the gap.

**Q: What is a reverse proxy and why use it?**
A: A server that forwards client requests to backend servers. Benefits: (1) SSL termination at proxy, (2) load balancing, (3) caching static content, (4) rate limiting, (5) hiding backend topology, (6) compression.

**Q: How does Nginx handle 10,000 concurrent connections with 4 workers?**
A: Each worker runs a non-blocking event loop using epoll (Linux) or kqueue (BSD). Connections are event-driven — a worker doesn't block waiting for I/O. A single worker can handle thousands of idle/active connections because only active connections consume CPU.

## References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Apache HTTP Server Documentation](https://httpd.apache.org/docs/)
- [Caddy Documentation](https://caddyserver.com/docs/)
