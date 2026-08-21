# AWS CloudFront

CloudFront is Amazon's Content Delivery Network (CDN), launched in 2008. It caches content at edge locations worldwide, serving user requests from the nearest edge rather than the origin. CloudFront supports static assets (images, CSS, JS), dynamic content (API responses), video streaming (HLS, DASH), and live events. This page covers the architecture, the caching model, the security features, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Edge Locations (~400+ worldwide)                          │
│  - Cache content from origins                              │
│  - Serve user requests directly                            │
│  - TLS termination                                          │
│  - URL signing (signed URLs, signed cookies)                │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ user request                 │ cache miss
        │                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  User (browser)       │    │  Origin               │
│                       │    │  - S3 bucket          │
└──────────────────────┘    │  - ALB/EC2             │
                              │  - Lambda function URL │
                              │  - MediaPackage       │
                              │  - MediaStore         │
                              └──────────────────────┘
```

CloudFront has ~400+ edge locations globally. Each edge caches content; on a cache miss, it fetches from the origin and caches the response.

## The Distribution Model

A CloudFront "distribution" is a logical configuration that defines:
- The origin (where to fetch content from).
- The cache behavior (which URLs to cache, for how long).
- The edge locations (typically all, but regional distributions are available).

```text
Distribution: my-website
  Origins:
    - S3 bucket (my-static-assets.s3.amazonaws.com)
    - ALB (my-api.elb.amazonaws.com)
  Cache Behaviors:
    - Path: /static/*
      Origin: S3 bucket
      Cache: 24 hours
    - Path: /api/*
      Origin: ALB
      Cache: 5 minutes (low TTL for dynamic content)
    - Default:
      Origin: ALB
      Cache: 1 minute
```

A distribution can have multiple origins and multiple cache behaviors (path-based routing).

## The Caching Model

CloudFront caches responses at edges based on:
- **Cache-Control headers**: `Cache-Control: max-age=3600` means cache for 1 hour.
- **CloudFront Cache Behaviors**: minimum/maximum TTL overrides.
- **Default TTL**: if no Cache-Control, the default (e.g., 24 hours).

```text
Edge cache state for a request:
  GET /static/image.jpg
  Cache-Control: max-age=86400

  Cache hit: serve from edge. ~5 ms.
  Cache miss: fetch from origin. ~50-100 ms.
```

Cache invalidation: when content changes, the user can invalidate the cache via the CloudFront API:
```bash
aws cloudfront create-invalidation --distribution-id E123456 --paths "/static/*"
```

Invalidation is expensive (slow, takes ~5 minutes); the better pattern is to use versioned URLs (`/static/v2/image.jpg`) so the new content has a different URL.

## Security

### Signed URLs and Cookies

For protected content (e.g., paid video), CloudFront generates signed URLs:

```text
https://d123.cloudfront.net/video.mp4?Expires=1692620400&Signature=abc...&Key-Pair-Id=K1...
```

The signature is signed by a trusted key pair; the URL expires at `Expires`. Without the signature, the request is rejected.

Signed cookies: same idea, but as a cookie (covers all URLs under a path). Useful for subscription content.

### Origin Access Control (OAC)

For S3 origins, CloudFront can use OAC to access the bucket directly, without making the bucket public:

```text
Bucket policy: allow only CloudFront to read.
CloudFront: signs the request to S3 with its service principal.
```

This prevents users from bypassing CloudFront (and bypassing any access controls).

### AWS WAF Integration

CloudFront integrates with AWS WAF (Web Application Firewall) at the edge. WAF rules can block:
- SQL injection patterns.
- Rate-based limits (per IP).
- Geo-based blocking.
- Custom rules (e.g., block if User-Agent matches).

WAF rules run at the edge, before CloudFront's cache lookup — meaning cached requests don't trigger WAF. This is fast (WAF runs in microseconds) but means WAF doesn't see cached content.

### Field-Level Encryption

For sensitive fields (e.g., credit card numbers), CloudFront can encrypt the field at the edge with a public key; the origin (which has the private key) decrypts. This protects the field from being logged in plain text at CloudFront.

## Real-Time Log Streaming

CloudFront can stream access logs to Kinesis Data Streams in real-time:

```text
Edge serves request → logs to Kinesis within ~1 second
Downstream: Lambda function processes logs, alerts on anomalies
```

This is much faster than the default S3 access logs (which can take 5-15 minutes to land).

## Production Use Cases

### Static Website

```yaml
# Distribution
Origins:
  - S3Origin: my-static-website.s3.amazonaws.com
Cache Behaviors:
  - Path: /*
    MinTTL: 0
    DefaultTTL: 86400  # 1 day
    MaxTTL: 31536000  # 1 year
```

A static site with HTML/CSS/JS served from S3, cached at edges for 1 year (per file's versioned URL).

### Dynamic API

```yaml
Origins:
  - CustomOrigin: api.example.com  # ALB
Cache Behaviors:
  - Path: /api/*
    MinTTL: 0
    DefaultTTL: 0  # don't cache API responses
    MaxTTL: 0
    AllowedMethods: [GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE]
```

CloudFront terminates TLS, applies WAF rules, forwards to the ALB. No caching for dynamic responses.

### Video Streaming (HLS)

```text
GET /video/master.m3u8   ← manifest (cache 1 second)
GET /video/segment-1.ts  ← video segment (cache 1 day)
GET /video/segment-2.ts
...
```

CloudFront caches segments at edges; the manifest is re-fetched frequently. This is the basis for streaming services like Prime Video.

### Live Events

CloudFront supports live streaming via:
- MediaLive: encodes the live stream.
- MediaPackage: packages as HLS/DASH.
- CloudFront: serves to viewers.

For a live event, edge caches have very low TTLs (1-2 seconds) so the live content is fresh.

## Comparison to Other CDNs

| Aspect | CloudFront | Cloudflare | Akamai | Fastly |
|--------|-----------|-----------|--------|--------|
| Edge count | ~400 | ~300 | ~4,000+ | ~80 |
| Compute at edge | Lambda@Edge | Workers | EdgeWorkers | Compute@Edge |
| Real-time logs | Kinesis | Logpush | Log Delivery API | Log streaming |
| Best for | AWS-integrated | Broad CDN, security | Global reach | Real-time, customizable |
| Pricing | Per-GB + per-request | Per-GB | Enterprise | Per-GB + per-request |

CloudFront's advantage is AWS integration (WAF, S3, Kinesis). Cloudflare's advantage is breadth and Workers (custom code at edge).

## Common Pitfalls

1. **Forgetting that CloudFront's cache TTL is bounded by the origin's headers.** A long TTL in CloudFront can be overridden by a short `Cache-Control: max-age` from the origin. Set the origin's headers correctly.

2. **Forgetting that invalidations are slow and expensive.** Each invalidation costs $0.005 per path; the first 1,000 per month are free. Use versioned URLs instead.

3. **Forgetting that the same content from different users may cache separately.** CloudFront can cache by request headers (Accept-Language, User-Agent). With Vary headers, different users get different caches (cache fragmentation).

4. **Forgetting that the origin must be reachable from all edges.** A origin in a private VPC needs to be exposed via a public ALB or VPC endpoint.

5. **Forgetting that CloudFront's edge TLS terminates at the edge.** The connection from edge to origin may be unencrypted unless configured. Enable "Origin Protocol Policy: HTTPS only".

6. **Forgetting that Lambda@Edge runs in the region closest to the user.** A Lambda@Edge function may run in any edge region; ensure it's stateless and region-independent.

## References

- [AWS CloudFront documentation](https://docs.aws.amazon.com/cloudfront/)
- [CloudFront Developer Guide](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/)
- [CloudFront signed URLs](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-signed-urls.html)
- [CloudFront + AWS WAF](https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-and-waf.html)
- [Lambda@Edge](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html)
- [CloudFront vs Cloudflare (AWS blog)](https://aws.amazon.com/cloudfront/cloudflare-alternative/)
- [LWN: CloudFront internals (2021)](https://lwn.net/Articles/820133/)
