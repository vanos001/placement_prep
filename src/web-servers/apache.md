# Apache HTTP Server

## Architecture

Apache uses Multi-Processing Modules (MPMs):

### MPM prefork
```
Client → Master → Worker Process (handles entire request)
                → Worker Process
                → Worker Process
```
One process per connection. Safe for non-thread-safe modules (PHP mod_php). High memory usage.

### MPM worker
```
Client → Master → Worker Process → Thread 1 (handles request)
                                  → Thread 2
                                  → Thread 3
```
Multiple threads per process. Better memory efficiency. Thread-safe modules required.

### MPM event
```
Client → Master → Worker Process → Thread (async keep-alive)
                                  → Thread (active request)
```
Like worker but handles keep-alive connections asynchronously. Best performance. Closest to Nginx model.

## Configuration

### Virtual Hosts
```apache
<VirtualHost *:80>
    ServerName example.com
    ServerAlias www.example.com
    DocumentRoot /var/www/example
    
    <Directory /var/www/example>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

### .htaccess
Per-directory configuration (slower than central config):
```apache
# /var/www/example/.htaccess
RewriteEngine On
RewriteRule ^api/(.*)$ http://backend:8080/$1 [P,L]

# Caching
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType text/css "access plus 1 month"
</IfModule>
```

### mod_rewrite
```apache
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]

RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /index.html [L]
```

### mod_proxy (Reverse Proxy)
```apache
ProxyPass /api/ http://localhost:8080/
ProxyPassReverse /api/ http://localhost:8080/
ProxyPreserveHost On
ProxyPass /ws/ ws://localhost:8080/ws/
```

## .htaccess Performance

| Aspect | .htaccess | Central Config |
|---|---|---|
| Performance | Slower (read per request) | Fast (parsed once) |
| Flexibility | Per-directory | Server-wide |
| Restart needed | No | Yes |
| Security | User-controllable | Admin-only |
| Recommendation | Disable in production | Use `AllowOverride None` |

## Modules

| Module | Purpose |
|---|---|
| mod_rewrite | URL rewriting |
| mod_proxy | Reverse proxy |
| mod_ssl | TLS/SSL |
| mod_deflate | Compression |
| mod_expires | Cache headers |
| mod_security | WAF |
| mod_php | PHP processing (prefork only) |
| mod_fastcgi | FastCGI proxy |

## References

- [Apache Documentation](https://httpd.apache.org/docs/)
- [Apache MPM Documentation](https://httpd.apache.org/docs/2.4/mpm.html)
