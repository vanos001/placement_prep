# curl

## Overview

`curl` (Client URL) is a command-line tool for transferring data with URLs. It supports HTTP, HTTPS, FTP, SCP, and many other protocols. It's essential for testing APIs, debugging HTTP issues, and automating web requests.

## Basic Syntax

```bash
curl [options] [URL]
```

## Common Usage

### Simple Requests

```bash
# GET request (default)
curl https://api.example.com/users

# GET with verbose output
curl -v https://api.example.com/users

# Follow redirects
curl -L https://example.com/redirect

# Silent (no progress bar)
curl -s https://api.example.com/users

# Show only HTTP status code
curl -s -o /dev/null -w "%{http_code}" https://api.example.com/users

# Save output to file
curl -o output.html https://example.com

# Save with original filename
curl -O https://example.com/file.zip
```

### HTTP Methods

```bash
# GET (default)
curl https://api.example.com/users

# POST with JSON body
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}'

# PUT
curl -X PUT https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Updated"}'

# PATCH
curl -X PATCH https://api.example.com/users/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice Patched"}'

# DELETE
curl -X DELETE https://api.example.com/users/1

# HEAD (headers only)
curl -I https://api.example.com/users

# OPTIONS
curl -X OPTIONS https://api.example.com/users -v
```

### Headers and Authentication

```bash
# Custom headers
curl -H "Authorization: Bearer token123" https://api.example.com/users
curl -H "Accept: application/json" https://api.example.com/users
curl -H "X-Custom-Header: value" https://api.example.com/users

# Multiple headers
curl -H "Authorization: Bearer token" \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     https://api.example.com/users

# Basic authentication
curl -u username:password https://api.example.com/users

# Bearer token
curl -H "Authorization: Bearer $(cat token.txt)" https://api.example.com/users

# Cookie
curl -b "session=abc123" https://api.example.com/users

# Save cookies
curl -c cookies.txt https://example.com/login

# Send saved cookies
curl -b cookies.txt https://api.example.com/users
```

### Debugging Options

```bash
# Verbose (show full request/response)
curl -v https://api.example.com/users

# Very verbose (TLS details)
curl -vv https://api.example.com/users

# Show timing
curl -w "\n\nTime DNS:    %{time_namelookup}s\n\
Time Connect: %{time_connect}s\n\
Time TLS:     %{time_appconnect}s\n\
Time TTFB:    %{time_starttransfer}s\n\
Time Total:   %{time_total}s\n\
Speed:        %{speed_download} bytes/sec\n" \
  -o /dev/null -s https://api.example.com/users

# Show only headers
curl -I https://api.example.com/users

# Include response headers in output
curl -i https://api.example.com/users

# Show error details
curl --trace-ascii - https://api.example.com/users
```

### Common curl Timing Variables

| Variable | Description |
|----------|-------------|
| `time_namelookup` | DNS resolution time |
| `time_connect` | TCP connection time |
| `time_appconnect` | TLS/SSL handshake time |
| `time_pretransfer` | Time before transfer starts |
| `time_starttransfer` | Time to first byte (TTFB) |
| `time_total` | Total request time |
| `speed_download` | Download speed (bytes/sec) |
| `size_download` | Total bytes downloaded |

### File Upload

```bash
# Upload file (multipart form)
curl -X POST https://api.example.com/upload \
  -F "file=@/path/to/file.pdf" \
  -F "description=My document"

# Upload with custom filename
curl -X POST https://api.example.com/upload \
  -F "file=@/path/to/file.pdf;filename=report.pdf"

# Upload raw file
curl -X PUT https://api.example.com/upload \
  -H "Content-Type: application/octet-stream" \
  --data-binary @/path/to/file.bin
```

### Proxy

```bash
# HTTP proxy
curl -x http://proxy.example.com:8080 https://api.example.com

# SOCKS proxy
curl --socks5 proxy.example.com:1080 https://api.example.com

# Proxy with authentication
curl -x http://user:pass@proxy.example.com:8080 https://api.example.com
```

### TLS/SSL Options

```bash
# Skip certificate verification (testing only!)
curl -k https://self-signed.example.com

# Use specific TLS version
curl --tlsv1.2 https://api.example.com

# Client certificate
curl --cert client.pem --key key.pem https://api.example.com

# Show TLS certificate info
curl -vI https://api.example.com 2>&1 | grep -i "ssl\|certificate"
```

## Practical Scenarios

### API Testing

```bash
# Test REST API
# GET
curl -s https://api.example.com/users | jq .

# POST
curl -s -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice"}' | jq .

# Check status code
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.example.com/users)
if [ "$STATUS" -eq 200 ]; then echo "OK"; else echo "FAIL: $STATUS"; fi
```

### Performance Testing

```bash
# Measure response time
curl -o /dev/null -s -w "DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" https://api.example.com

# Loop for average
for i in {1..10}; do
  curl -o /dev/null -s -w "%{time_total}\n" https://api.example.com
done | awk '{sum+=$1} END {print "Avg:", sum/NR, "s"}'
```

### Health Check Script

```bash
#!/bin/bash
URL="https://api.example.com/health"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$URL")
if [ "$STATUS" -ne 200 ]; then
  echo "ALERT: $URL returned $STATUS"
  # Send alert
fi
```

## wget vs curl

| Feature | curl | wget |
|---------|------|------|
| **Primary use** | API testing, data transfer | File downloading |
| **Recursive download** | No | Yes |
| **Resume downloads** | Yes (-C -) | Yes (-c) |
| **Output** | stdout | File |
| **Protocols** | More (25+) | Fewer |
| **Library** | libcurl | Standalone |
| **Scripting** | Excellent | Good |

## Interview Questions

1. **Q: How do you test an API endpoint with curl?**
   A: `curl -X POST https://api.example.com/users -H "Content-Type: application/json" -d '{"name":"Alice"}'`. Use `-v` for verbose output, `-i` to see response headers, and pipe to `jq` for JSON formatting.

2. **Q: How do you measure request latency with curl?**
   A: Use the `-w` flag with timing variables: `curl -o /dev/null -s -w "TTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n" URL`. This shows DNS, connect, TLS, TTFB, and total times.

3. **Q: What does `curl -L` do?**
   A: Follows HTTP redirects (301, 302, 307, 308). Without `-L`, curl shows the redirect response but doesn't follow it. Always use `-L` when you want the final response.

4. **Q: How do you upload a file with curl?**
   A: `curl -F "file=@/path/to/file.pdf" https://api.example.com/upload`. The `@` prefix tells curl to read the file. Use `-F` for multipart form data, `--data-binary @file` for raw upload.

5. **Q: What's the difference between `-d` and `-F`?**
   A: `-d` sends data as application/x-www-form-urlencoded (or with -H "Content-Type: application/json" as JSON). `-F` sends multipart/form-data (required for file uploads). `-d` is for API calls, `-F` for form submissions.

6. **Q: How do you skip TLS certificate verification?**
   A: `curl -k` or `curl --insecure`. This disables certificate validation. Use only for testing with self-signed certificates. Never in production — it defeats the purpose of TLS.

## Common Mistakes

- Not using `-L` for redirects
- Forgetting `-H "Content-Type: application/json"` with `-d` for JSON APIs
- Using `-k` in production (disables TLS verification)
- Not using `-s` in scripts (progress bar pollutes output)
- Confusing `-o` (specify filename) with `-O` (use original filename)

## Summary

curl is the Swiss Army knife of HTTP. Master `-X` for methods, `-H` for headers, `-d` for body, `-v` for debugging, and `-w` for timing. It's essential for API testing, debugging, and automation.

## Cross-References

- [Tools Overview](README.md)
- [ping & traceroute](ping-traceroute.md) — Network-level testing
- [tcpdump](tcpdump.md) — Packet-level analysis
- [TLS](../security/tls.md) — HTTPS connections

## Cross References

- [HTTP](../http/README.md)
- [REST](../http/rest.md)
- [HTTPS](../http/https.md)
