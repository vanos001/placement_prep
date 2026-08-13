# TLS/SSL: Transport Layer Security

## Introduction

TLS (Transport Layer Security) and its predecessor SSL (Secure Sockets Layer) are cryptographic protocols that provide secure communication over a network. TLS is the foundation of HTTPS, secure email, VPNs, and many other applications. This chapter covers the TLS handshake, certificates, cipher suites, and practical OpenSSL usage.

## TLS Protocol Overview

### Protocol Stack

```mermaid
graph TB
    subgraph "TLS Protocol Layers"
        APP[Application Data]
        HS[Handshake Protocol]
        CCS[Change Cipher Spec]
        ALERT[Alert Protocol]
    end

    subgraph "TLS Record Protocol"
        RECORD[Record Protocol]
    end

    subgraph "Transport"
        TCP[TCP Connection]
    end

    APP --> RECORD
    HS --> RECORD
    CCS --> RECORD
    ALERT --> RECORD
    RECORD --> TCP
```

### TLS Versions

| Version | Year | Status | Key Features |
|---------|------|--------|--------------|
| SSL 2.0 | 1995 | Insecure | Deprecated |
| SSL 3.0 | 1996 | Insecure | Deprecated (POODLE) |
| TLS 1.0 | 1999 | Deprecated | RFC 2246 |
| TLS 1.1 | 2006 | Deprecated | RFC 4346 |
| TLS 1.2 | 2008 | Current | RFC 5246, AEAD ciphers |
| TLS 1.3 | 2018 | Recommended | RFC 8446, 0-RTT, faster handshake |

## TLS Handshake

### TLS 1.2 Handshake

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: ClientHello
    Note right of C: Supported TLS versions<br>Cipher suites<br>Random number<br>Extensions

    S->>C: ServerHello
    Note left of S: Selected TLS version<br>Selected cipher suite<br>Random number<br>Session ID

    S->>C: Certificate
    Note left of S: Server's X.509 certificate chain

    S->>C: ServerKeyExchange
    Note left of S: DH/ECDH parameters<br>Signed with server key

    S->>C: ServerHelloDone

    C->>C: Verify certificate
    C->>C: Generate pre-master secret

    C->>S: ClientKeyExchange
    Note right of C: Pre-master secret<br>encrypted with server's<br>public key

    C->>S: ChangeCipherSpec
    C->>S: Finished (encrypted)

    S->>S: Derive session keys
    S->>S: Verify Finished message

    S->>C: ChangeCipherSpec
    S->>C: Finished (encrypted)

    Note over C,S: Encrypted application data flows
```

### TLS 1.3 Handshake

TLS 1.3 simplifies the handshake to one round-trip:

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: ClientHello
    Note right of C: Supported cipher suites<br>Key share (ECDHE)<br>Supported versions<br>PSK identity (optional)

    S->>C: ServerHello
    Note left of S: Selected cipher suite<br>Key share<br>Supported version

    S->>C: EncryptedExtensions
    S->>C: Certificate
    S->>C: CertificateVerify
    S->>C: Finished

    C->>C: Verify certificate
    C->>C: Derive session keys

    C->>S: Finished

    Note over C,S: Encrypted application data flows
```

**Key differences in TLS 1.3:**
- Only AEAD cipher suites
- No RSA key exchange (only (EC)DHE)
- 0-RTT resumption
- Encrypted certificate exchange
- Removed insecure features

## Certificates

### X.509 Certificate Structure

```
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 1234567890 (0x499602d2)
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN = Let's Encrypt Authority X3, O = Let's Encrypt, C = US
        Validity
            Not Before: Jan  1 00:00:00 2024 GMT
            Not After : Mar 31 23:59:59 2024 GMT
        Subject: CN = example.com
        Subject Public Key Info:
            Public Key Algorithm: rsaEncryption
                RSA Public-Key: (2048 bit)
        X509v3 extensions:
            X509v3 Subject Alternative Name:
                DNS:example.com, DNS:www.example.com
            X509v3 Basic Constraints:
                CA:FALSE
            X509v3 Key Usage:
                Digital Signature, Key Encipherment
    Signature Algorithm: sha256WithRSAEncryption
```

### Certificate Chain

```mermaid
graph TB
    ROOT[Root CA Certificate]
    INTER[Intermediate CA Certificate]
    SERVER[Server Certificate]

    ROOT -->|Signs| INTER
    INTER -->|Signs| SERVER
```

**Root CAs** are pre-installed in operating systems and browsers:
- Let's Encrypt
- DigiCert
- GlobalSign
- Comodo

### Let's Encrypt (ACME)

```bash
# Install certbot
$ sudo apt install certbot

# Obtain certificate (standalone)
$ sudo certbot certonly --standalone -d example.com -d www.example.com

# Using nginx plugin
$ sudo certbot --nginx -d example.com

# Using webroot
$ sudo certbot certonly --webroot -w /var/www/html -d example.com

# Certificate locations
/etc/letsencrypt/live/example.com/fullchain.pem   # Certificate + chain
/etc/letsencrypt/live/example.com/privkey.pem     # Private key
/etc/letsencrypt/live/example.com/cert.pem        # Certificate only
/etc/letsencrypt/live/example.com/chain.pem       # Chain only

# Auto-renewal
$ sudo certbot renew --dry-run
$ sudo systemctl enable certbot.timer
```

## Cipher Suites

### Cipher Suite Components

A cipher suite specifies four algorithms:

```
TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
│    │      │      │      │   │    │
│    │      │      │      │   │    └─ PRF Hash
│    │      │      │      │   └─ AEAD Mode
│    │      │      │      └─ AES Key Size
│    │      │      └─ Symmetric Encryption
│    │      └─ Authentication
│    └─ Key Exchange
└─ Protocol
```

### TLS 1.2 Cipher Suites

| Suite | Key Exchange | Authentication | Encryption | Status |
|-------|--------------|----------------|------------|--------|
| `ECDHE-RSA-AES256-GCM-SHA384` | ECDHE | RSA | AES-256-GCM | Secure |
| `ECDHE-RSA-AES128-GCM-SHA256` | ECDHE | RSA | AES-128-GCM | Secure |
| `ECDHE-ECDSA-AES256-GCM-SHA384` | ECDHE | ECDSA | AES-256-GCM | Secure |
| `DHE-RSA-AES256-GCM-SHA384` | DHE | RSA | AES-256-GCM | Secure |
| `RSA-AES256-GCM-SHA384` | RSA | RSA | AES-256-GCM | Avoid |
| `ECDHE-RSA-AES256-SHA` | ECDHE | RSA | AES-256-CBC | Avoid |

### TLS 1.3 Cipher Suites

TLS 1.3 only supports five cipher suites:

```
TLS_AES_128_GCM_SHA256
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
TLS_AES_128_CCM_SHA256
TLS_AES_128_CCM_8_SHA256
```

## OpenSSL Commands

### Certificate Operations

```bash
# View certificate details
$ openssl x509 -in cert.pem -text -noout

# View certificate expiry
$ openssl x509 -in cert.pem -enddate -noout
notAfter=Mar 31 23:59:59 2024 GMT

# View certificate fingerprint
$ openssl x509 -in cert.pem -fingerprint -noout
SHA1 Fingerprint=AA:BB:CC:DD:EE:FF...

# Convert DER to PEM
$ openssl x509 -inform DER -in cert.der -out cert.pem

# Convert PEM to DER
$ openssl x509 -outform DER -in cert.pem -out cert.der

# Create PKCS12 bundle
$ openssl pkcs12 -export -in cert.pem -inkey key.pem -out bundle.p12
```

### Key Operations

```bash
# Generate RSA private key
$ openssl genrsa -out private.key 4096

# Generate EC private key
$ openssl ecparam -genkey -name prime256v1 -out ec_private.key

# Extract public key
$ openssl rsa -in private.key -pubout -out public.key

# View key details
$ openssl rsa -in private.key -text -noout

# Encrypt private key
$ openssl rsa -in private.key -aes256 -out private_enc.key

# Decrypt private key
$ openssl rsa -in private_enc.key -out private.key
```

### CSR (Certificate Signing Request)

```bash
# Generate CSR
$ openssl req -new -key private.key -out request.csr

# Generate CSR with subject
$ openssl req -new -key private.key -out request.csr \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=example.com"

# Generate CSR with SAN
$ openssl req -new -key private.key -out request.csr \
    -config <(cat <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C = US
ST = State
L = City
O = Organization
CN = example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
EOF
)

# Verify CSR
$ openssl req -in request.csr -text -noout

# Self-sign a certificate
$ openssl x509 -req -in request.csr -signkey private.key -out cert.pem -days 365
```

### TLS Connection Testing

```bash
# Test TLS connection
$ openssl s_client -connect example.com:443

# Test with specific TLS version
$ openssl s_client -connect example.com:443 -tls1_2
$ openssl s_client -connect example.com:443 -tls1_3

# Test with SNI
$ openssl s_client -connect example.com:443 -servername example.com

# Show certificate chain
$ openssl s_client -connect example.com:443 -showcerts

# Test STARTTLS
$ openssl s_client -connect mail.example.com:587 -starttls smtp

# Show session details
$ openssl s_client -connect example.com:443 -sess_out session.pem

# Resume session
$ openssl s_client -connect example.com:443 -sess_in session.pem
```

### Certificate Verification

```bash
# Verify certificate against CA bundle
$ openssl verify -CAfile ca-bundle.crt cert.pem

# Verify certificate chain
$ openssl verify -CAfile ca.pem -untrusted intermediate.pem cert.pem

# Check certificate matches private key
$ openssl x509 -noout -modulus -in cert.pem | openssl md5
$ openssl rsa -noout -modulus -in private.key | openssl md5

# Check certificate matches CSR
$ openssl req -noout -modulus -in request.csr | openssl md5
```

## TLS Configuration

### Nginx TLS Configuration

```nginx
# /etc/nginx/sites-available/example.com
server {
    listen 443 ssl http2;
    server_name example.com;

    # Certificate and key
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # TLS version
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;

    # Session caching
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

### Apache TLS Configuration

```apache
# /etc/apache2/sites-available/example.com.conf
<VirtualHost *:443>
    ServerName example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/example.com/cert.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem
    SSLCertificateChainFile /etc/letsencrypt/live/example.com/chain.pem

    # TLS configuration
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    SSLHonorCipherOrder off

    # OCSP Stapling
    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/ssl_stapling(128000)"
</VirtualHost>
```

## Certificate Pinning

### HTTP Public Key Pinning (HPKP)

HPKP is deprecated but worth understanding:

```bash
# HPKP header (deprecated)
# Public-Key-Pins: pin-sha256="base64=="; max-age=5184000
```

### Certificate Transparency

```bash
# Check CT logs
$ curl -s "https://crt.sh/?q=example.com&output=json" | jq .

# Monitor CT logs for your domain
$ watch -n 3600 'curl -s "https://crt.sh/?q=example.com&output=json" | jq length'
```

### Expect-CT Header

```bash
# Expect-CT header
# Expect-CT: max-age=86400, enforce, report-uri="https://example.com/report"
```

## TLS Performance

### Session Resumption

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    Note over C,S: Initial Handshake
    C->>S: ClientHello
    S->>C: ServerHello + Session ID
    Note over C,S: Full handshake...
    C->>S: Application Data

    Note over C,S: Resumption (later connection)
    C->>S: ClientHello + Session ID
    S->>C: ServerHello + ChangeCipherSpec
    Note over C,S: Abbreviated handshake (1-RTT)
    C->>S: Application Data
```

### TLS 1.3 0-RTT

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    Note over C,S: First connection (full handshake)
    C->>S: ClientHello + KeyShare
    S->>C: ServerHello + KeyShare
    Note over C,S: Complete handshake...

    Note over C,S: Resumption with 0-RTT
    C->>S: ClientHello + PSK + KeyShare + EarlyData
    Note right of C: Application data sent immediately
    S->>C: ServerHello + Finished
    Note over C,S: 0-RTT data processed
```

**Warning**: 0-RTT data is vulnerable to replay attacks.

## Troubleshooting TLS

### Common Issues

```bash
# Certificate expired
$ echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -dates
notBefore=Jan  1 00:00:00 2024 GMT
notAfter=Mar 31 23:59:59 2024 GMT

# Certificate name mismatch
$ echo | openssl s_client -connect example.com:443 2>/dev/null | \
    openssl x509 -noout -text | grep -A1 "Subject Alternative Name"

# Self-signed certificate
$ echo | openssl s_client -connect example.com:443 2>&1 | \
    grep "verify return code"

# Protocol version mismatch
$ openssl s_client -connect example.com:443 -tls1
```

### Debugging Commands

```bash
# Full TLS debug
$ openssl s_client -connect example.com:443 -debug

# Show all ciphers
$ openssl ciphers -v 'HIGH:!aNULL:!MD5'

# Test specific cipher
$ openssl s_client -connect example.com:443 -cipher ECDHE-RSA-AES256-GCM-SHA384

# Check OCSP response
$ openssl s_client -connect example.com:443 -status

# Test with specific SNI
$ openssl s_client -connect example.com:443 -servername example.com

# Using nmap
$ nmap --script ssl-enum-ciphers -p 443 example.com

# Using sslyze
$ sslyze --regular example.com
```

## Security Best Practices

### TLS Configuration Checklist

```bash
# 1. Use TLS 1.2 and 1.3 only
ssl_protocols TLSv1.2 TLSv1.3;

# 2. Use strong cipher suites
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

# 3. Enable HSTS
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

# 4. Enable OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;

# 5. Disable session tickets (for forward secrecy)
ssl_session_tickets off;

# 6. Use strong DH parameters
ssl_dhparam /etc/ssl/dhparam.pem;
```

### Generate DH Parameters

```bash
# Generate strong DH parameters
$ openssl dhparam -out /etc/ssl/dhparam.pem 4096
```

## Kernel TLS (kTLS)

From the [kernel TLS documentation](https://docs.kernel.org/networking/tls.html), the Linux kernel supports TLS as an Upper Layer Protocol (ULP) over TCP. Kernel TLS (kTLS) handles symmetric encryption/decryption in the kernel, while the TLS handshake remains in userspace. This offloads the data path from userspace TLS libraries, reducing system call overhead and enabling zero-copy optimizations.

### Why Kernel TLS?

Userspace TLS implementations (OpenSSL, GnuTLS) require:
1. Reading encrypted data from the socket into userspace
2. Decrypting in userspace
3. Copying plaintext to the application buffer

kTLS eliminates copies 1 and 3 by decrypting directly into the application buffer and encrypting directly from the application buffer.

### Creating a kTLS Connection

```c
/* 1. Create and connect a TCP socket */
int sock = socket(AF_INET, SOCK_STREAM, 0);
connect(sock, addr, addrlen);

/* 2. Set the TLS ULP (after handshake completes in userspace) */
setsockopt(sock, SOL_TCP, TCP_ULP, "tls", sizeof("tls"));

/* 3. Configure TX and/or RX crypto parameters */
struct tls12_crypto_info_aes_gcm_128 crypto_info = {
    .info.version = TLS_1_2_VERSION,
    .info.cipher_type = TLS_CIPHER_AES_GCM_128,
};
memcpy(crypto_info.iv, iv_write, TLS_CIPHER_AES_GCM_128_IV_SIZE);
memcpy(crypto_info.key, cipher_key, TLS_CIPHER_AES_GCM_128_KEY_SIZE);
memcpy(crypto_info.salt, implicit_iv, TLS_CIPHER_AES_GCM_128_SALT_SIZE);
memcpy(crypto_info.rec_seq, seq_number, TLS_CIPHER_AES_GCM_128_REC_SEQ_SIZE);

/* Enable TX encryption */
setsockopt(sock, SOL_TLS, TLS_TX, &crypto_info, sizeof(crypto_info));
/* Enable RX decryption */
setsockopt(sock, SOL_TLS, TLS_RX, &crypto_info, sizeof(crypto_info));
```

### Sending and Receiving

After setting `TLS_TX`, all `send()` data is automatically encrypted. After setting `TLS_RX`, all `recv()` data is automatically decrypted.

```c
/* Send encrypted data — encryption happens in kernel */
send(sock, msg, strlen(msg));

/* sendfile() — zero-copy file transfer over TLS */
int file = open(filename, O_RDONLY);
struct stat st;
fstat(file, &st);
sendfile(sock, file, &offset, st.st_size);

/* Receive decrypted data */
char buffer[16384];
recv(sock, buffer, sizeof(buffer));
```

`sendfile()` with kTLS achieves true zero-copy: file data is encrypted directly from the page cache without intermediate copies.

### Control Messages (Alerts, Handshake)

TLS control messages (alerts, handshake re-key) are sent via `sendmsg()` with `SOL_TLS` / `TLS_SET_RECORD_TYPE` cmsg:

```c
struct msghdr msg = {0};
struct cmsghdr *cmsg;
char buf[CMSG_SPACE(sizeof(unsigned char))];

msg.msg_control = buf;
msg.msg_controllen = sizeof(buf);
cmsg = CMSG_FIRSTHDR(&msg);
cmsg->cmsg_level = SOL_TLS;
cmsg->cmsg_type = TLS_SET_RECORD_TYPE;
cmsg->cmsg_len = CMSG_LEN(sizeof(unsigned char));
*CMSG_DATA(cmsg) = 21;  /* TLS alert record type */
msg.msg_controllen = cmsg->cmsg_len;

struct iovec iov = { .iov_base = alert_data, .iov_len = alert_len };
msg.msg_iov = &iov;
msg.msg_iovlen = 1;
sendmsg(sock, &msg, 0);
```

Receiving control messages uses `TLS_GET_RECORD_TYPE` cmsg to distinguish alerts from application data.

### TLS 1.3 Key Updates

In TLS 1.3, `KeyUpdate` handshake messages signal key rotation. The kernel pauses RX decryption when a KeyUpdate is received until new keys are provided via `TLS_RX` setsockopt. Reads during this window fail with `EKEYEXPIRED`. TX is not paused.

### Optional Optimizations

| Option | Description |
|--------|-------------|
| `TLS_TX_ZEROCOPY_RO` | Device offload: sendfile() data transmitted directly to NIC without kernel copy (read-only data only) |
| `TLS_RX_EXPECT_NO_PAD` | TLS 1.3: expect no padding, enabling direct decryption into userspace buffers |
| `TLS_TX_MAX_PAYLOAD_LEN` | Limit plaintext payload size per record (RFC 8449 Record Size Limit) |

### Statistics

Per-namespace stats available at `/proc/net/tls_stat`:

| Statistic | Description |
|-----------|-------------|
| `TlsCurrTxSw` / `TlsCurrRxSw` | Active software-encrypted sessions |
| `TlsCurrTxDevice` / `TlsCurrRxDevice` | Active NIC-offloaded sessions |
| `TlsTxSw` / `TlsRxSw` | Total software sessions opened |
| `TlsDecryptError` | Failed decryptions (bad auth tag) |
| `TlsDeviceRxResync` | RX resyncs sent to offloading NICs |
| `TlsDecryptRetry` | Records re-decrypted due to `TLS_RX_EXPECT_NO_PAD` misprediction |
| `TlsTxRekeyOk` / `TlsRxRekeyOk` | Successful TLS 1.3 key updates |
| `TlsRxRekeyReceived` | KeyUpdate handshake messages received |

### NIC Hardware Offload

Modern NICs (Mellanox ConnectX-6, Intel E810) can offload TLS encryption/decryption entirely to hardware:

```bash
# Check if NIC supports TLS offload
ethtool -k eth0 | grep tls
# tx-udp_tnl-segmentation: on

# Enable TLS offload (driver-dependent)
# Typically enabled automatically when kTLS is used with capable NIC
```

With NIC offload, TLS sessions use `TlsCurrTxDevice` / `TlsCurrRxDevice` instead of software crypto.

### Integration with Userspace TLS Libraries

kTLS replaces the **record layer** of a userspace TLS library. The handshake (certificate verification, key exchange) still happens in userspace. After the handshake, the library passes crypto parameters to the kernel and all subsequent data path is kernel-handled.

OpenSSL supports kTLS via the `SSL_sendfile()` API and automatic detection when `TCP_ULP` is available.

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

1. **RFC 8446** — The Transport Layer Security (TLS) Protocol Version 1.3
2. **RFC 5246** — The Transport Layer Security (TLS) Protocol Version 1.2
3. **RFC 6066** — Transport Layer Security (TLS) Extensions
4. **Let's Encrypt** — [letsencrypt.org](https://letsencrypt.org/)
5. **Mozilla SSL Configuration Generator** — [ssl-config.mozilla.org](https://ssl-config.mozilla.org/)
6. **SSL Labs** — [www.ssllabs.com/ssltest/](https://www.ssllabs.com/ssltest/)
7. **OpenSSL Documentation** — [www.openssl.org/docs/](https://www.openssl.org/docs/)
8. [Kernel TLS documentation — docs.kernel.org](https://docs.kernel.org/networking/tls.html) — kTLS ULP, NIC offload, TLS 1.3 key updates, statistics

## Related Topics

- [Network Fundamentals](fundamentals.md) — OSI model and network basics
- [TCP/IP Suite](tcpip-suite.md) — TCP/IP protocol details
- [SSH](ssh.md) — Secure Shell
- [DNS](dns.md) — Domain Name System
