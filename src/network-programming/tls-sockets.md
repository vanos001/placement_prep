# TLS Socket Programming

## Adding TLS to Socket Connections

TLS (Transport Layer Security) encrypts data in transit, providing confidentiality, integrity, and authentication. TLS runs as a layer between TCP and the application protocol (HTTP, SMTP, MQTT, custom protocols).

To add TLS to a plain TCP connection, you perform a **TLS handshake** over the established TCP connection. The handshake negotiates:

- **Protocol version** (TLS 1.2 or 1.3)
- **Cipher suite** (e.g., AES-256-GCM with ECDHE key exchange)
- **Server certificate** (and optional client certificate)
- **Session keys** via Diffie-Hellman key exchange

After the handshake, you read and write through the TLS object (not the raw socket). The TLS library handles encryption, decryption, MAC verification, and record framing.

## OpenSSL Basics

OpenSSL provides both a command-line tool and a C library for TLS. The library-level API has evolved:

- **Legacy SSL API** (`SSL_*` functions): Still works but deprecated for new code
- **OpenSSL BIO API**: Abstraction for I/O sources (file, socket, memory)
- **OpenSSL 3.0+ SSL API**: Recommended interface with cleaner error handling

### Key Objects

| Object | Purpose |
|--------|---------|
| `SSL_CTX` | Global TLS context—holds configuration, certificates, cipher list |
| `SSL` | Per-connection TLS state—created from `SSL_CTX` |
| `X509` | Represents an X.509 certificate |
| `EVP_PKEY` | Represents a private or public key |
| `SSL_METHOD` | Protocol version selection (e.g., `TLS_server_method()`) |

## Certificate Loading

A TLS server needs a certificate and private key:

```c
SSL_CTX *ctx = SSL_CTX_new(TLS_server_method());

// Configure protocol version (minimum TLS 1.2)
SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

// Load certificate chain
if (SSL_CTX_use_certificate_chain_file(ctx, "/path/to/cert.pem") != 1) {
    ERR_print_errors_fp(stderr);
    exit(EXIT_FAILURE);
}

// Load private key
if (SSL_CTX_use_PrivateKey_file(ctx, "/path/to/key.pem", SSL_FILETYPE_PEM) != 1) {
    ERR_print_errors_fp(stderr);
    exit(EXIT_FAILURE);
}

// Verify private key matches certificate
if (SSL_CTX_check_private_key(ctx) != 1) {
    fprintf(stderr, "Private key does not match certificate\n");
    exit(EXIT_FAILURE);
}
```

## TLS Handshake in Code

### Server Side

```c
int conn_fd = accept(listen_fd, NULL, NULL);  // Plain TCP accept

// Create SSL object for this connection
SSL *ssl = SSL_new(ctx);
SSL_set_fd(ssl, conn_fd);

// Perform TLS handshake (blocks until complete)
if (SSL_accept(ssl) <= 0) {
    ERR_print_errors_fp(stderr);
    SSL_free(ssl);
    close(conn_fd);
    return;
}

// Now read/write through SSL (not conn_fd)
char buf[4096];
int n = SSL_read(ssl, buf, sizeof(buf) - 1);
if (n > 0) {
    buf[n] = '\0';
    SSL_write(ssl, buf, n);  // Echo
}

SSL_shutdown(ssl);  // Send close_notify
SSL_free(ssl);
close(conn_fd);
```

### Client Side

```c
SSL_CTX *ctx = SSL_CTX_new(TLS_client_method());
SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

// Load CA certificates for server verification
SSL_CTX_set_default_verify_paths(ctx);

SSL *ssl = SSL_new(ctx);
SSL_set_fd(ssl, fd);
SSL_set_verify(ssl, SSL_VERIFY_PEER, NULL);  // Verify server cert

// Optional: verify server hostname
// (Requires manual SAN checking or SSL_CTRL_SET_TLSEXT_SERVERNAME_CB)

if (SSL_connect(ssl) <= 0) {
    ERR_print_errors_fp(stderr);
    exit(EXIT_FAILURE);
}

// Verify certificate chain
X509 *cert = SSL_get_peer_certificate(ssl);
if (cert) {
    long verify_result = SSL_get_verify_result(ssl);
    if (verify_result != X509_V_OK) {
        fprintf(stderr, "Certificate verification failed: %s\n",
                X509_verify_cert_error_string(verify_result));
    }
    X509_free(cert);
}

SSL_write(ssl, msg, strlen(msg));
int n = SSL_read(ssl, buf, sizeof(buf) - 1);
```

## Common TLS Pitfalls

1. **Ignoring certificate verification**: Never set `SSL_VERIFY_NONE` in production. This enables man-in-the-middle attacks. Always verify the server certificate chain and hostname.

2. **Not checking `SSL_get_verify_result()`**: Even with `SSL_VERIFY_PEER` set, you must check the verification result. The handshake succeeds even if verification fails.

3. **Not handling `SSL_ERROR_WANT_READ`/`SSL_ERROR_WANT_WRITE`**: When using non-blocking sockets, `SSL_read()`/`SSL_write()` may return with these errors, indicating the operation needs to be retried when the underlying socket is ready. This is critical for event-driven servers.

4. **Not calling `SSL_shutdown()`**: Failing to send `close_notify` can cause the peer to log a truncation warning. Call `SSL_shutdown()` (possibly twice for bidirectional shutdown) before `close()`.

5. **Using outdated protocols or ciphers**: Always set a minimum TLS version (1.2+) and prefer AEAD ciphers (AES-GCM, ChaCha20-Poly1305).

6. **Loading only one certificate**: If your certificate has intermediates, load the full chain (leaf + intermediates) with `SSL_CTX_use_certificate_chain_file()`.

## References

- [OpenSSL Documentation](https://www.openssl.org/docs/)
- [OpenSSL Wiki: SSL/TLS Client](https://wiki.openssl.org/index.php/SSL/TLS_Client)
- [RFC 8446 — TLS 1.3](https://datatracker.ietf.org/doc/html/rfc8446)
- [OWASP TLS Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html)

## Interview Questions

1. Explain the TLS handshake. What is exchanged and in what order?
2. What is the difference between TLS 1.2 and TLS 1.3 in terms of the handshake?
3. Why is it dangerous to disable certificate verification (`SSL_VERIFY_NONE`)?
4. How do you handle TLS on non-blocking sockets with `epoll`?
5. What is a cipher suite? Give an example and explain each component.
6. What is forward secrecy and which key exchange mechanisms provide it?
7. How does certificate pinning work? When would you use it?
8. What is the difference between `SSL_read` returning 0 and `SSL_read` returning -1 with `SSL_ERROR_ZERO_RETURN`?
9. Explain session resumption in TLS. Why does it improve performance?
10. A client connects to your TLS server and the handshake fails with "certificate verify failed." Walk through your debugging steps.