# Web Server Interview Questions

## Nginx

**Q: How does Nginx handle concurrent connections?**
A: Event-driven model using epoll/kqueue. Workers don't block on I/O — they handle connections via events. One worker can manage thousands of connections. `worker_connections` sets the limit per worker.

**Q: What is the difference between `proxy_pass` with and without trailing slash?**
A: With trailing slash (`proxy_pass http://backend/`), the matched location prefix is stripped. Without it, the full URI is passed. Example: `location /api/` + `proxy_pass http://backend/` → `/api/users` becomes `/users` on backend.

## Load Balancing

**Q: Compare Nginx load balancing algorithms.**
A: Round Robin (default, even distribution), Least Connections (best for varying request times), IP Hash (session affinity), Weighted (proportional to server capacity). Use Least Connections for general purpose; IP Hash when session state isn't externalized.

**Q: How do you handle session affinity with Nginx?**
A: (1) `ip_hash` — same client IP goes to same server, (2) `sticky cookie` (Nginx Plus) — server sets a cookie, (3) externalize sessions to Redis/Memcached (best approach, avoids affinity).

## TLS

**Q: How does TLS termination at a reverse proxy work?**
A: The proxy handles TLS handshake with clients, decrypts requests, forwards plain HTTP to backends. Benefits: (1) single cert management point, (2) backends don't need TLS, (3) offloads CPU-intensive crypto from app servers, (4) easier cert rotation.

## Caching

**Q: How does Nginx caching work?**
A: `proxy_cache_path` defines cache storage. `proxy_cache_valid` sets TTL per status code. Nginx caches responses based on cache key (default: scheme+host+URI). `proxy_cache_use_stale` serves stale content on backend errors. `X-Cache-Status` header shows HIT/MISS/EXPIRED.

## References

- [Nginx Admin Guide](https://nginx.org/en/docs/admin_guide.html)
- [Apache Performance Tuning](https://httpd.apache.org/docs/2.4/misc/perf-tuning.html)
