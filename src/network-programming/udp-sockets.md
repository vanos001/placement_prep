# UDP Socket Programming

UDP provides a connectionless, message-oriented transport. Each `sendto()` emits a datagram, and each `recvfrom()` receives one. There is no handshake, no connection state, and no guarantees about delivery or ordering.

## When to Use UDP

Use UDP when:

- **Latency matters more than reliability**: Real-time gaming, VoIP, live video streaming
- **You can tolerate data loss**: Sensor telemetry, periodic health checks, metrics
- **You implement your own reliability layer**: QUIC, custom game protocols, STUN/TURN
- **Broadcast/multicast delivery**: Service discovery, mDNS, SSDP
- **Simple request-response with small payloads**: DNS (typically < 512 bytes)

Do **not** use UDP when:

- You need guaranteed in-order delivery (use TCP)
- You are transferring large files (TCP's congestion control handles this)
- Your application is not prepared to handle reordering, duplication, or loss

## UDP Server in C

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>

#define PORT 9090
#define BUF_SIZE 65535  // Maximum UDP datagram size

int main(void) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return EXIT_FAILURE;
    }

    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr = {
        .sin_family      = AF_INET,
        .sin_port        = htons(PORT),
        .sin_addr.s_addr = INADDR_ANY
    };

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(fd);
        return EXIT_FAILURE;
    }

    printf("UDP server listening on port %d\n", PORT);

    char buf[BUF_SIZE];
    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);

    for (;;) {
        ssize_t n = recvfrom(fd, buf, sizeof(buf), 0,
                             (struct sockaddr *)&client_addr, &client_len);
        if (n < 0) {
            perror("recvfrom");
            continue;
        }

        buf[n] = '\0';
        printf("Received %zd bytes from %s:%d: %s",
               n,
               inet_ntoa(client_addr.sin_addr),
               ntohs(client_addr.sin_port),
               buf);

        // Echo back to the same client
        sendto(fd, buf, n, 0,
               (struct sockaddr *)&client_addr, client_len);
    }

    close(fd);
    return 0;
}
```

## UDP Client in C

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define SERVER_IP "127.0.0.1"
#define PORT 9090

int main(void) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return EXIT_FAILURE;
    }

    struct sockaddr_in server_addr = {
        .sin_family = AF_INET,
        .sin_port   = htons(PORT)
    };
    inet_pton(AF_INET, SERVER_IP, &server_addr.sin_addr);

    const char *msg = "Hello, UDP Server!";
    sendto(fd, msg, strlen(msg), 0,
           (struct sockaddr *)&server_addr, sizeof(server_addr));

    char buf[1024];
    struct sockaddr_in from_addr;
    socklen_t from_len = sizeof(from_addr);
    ssize_t n = recvfrom(fd, buf, sizeof(buf) - 1, 0,
                         (struct sockaddr *)&from_addr, &from_len);
    if (n > 0) {
        buf[n] = '\0';
        printf("Server replied: %s\n", buf);
    }

    close(fd);
    return 0;
}
```

## Datagram Boundaries

A critical difference from TCP: **UDP preserves message boundaries**. If you call `sendto()` with 100 bytes, `recvfrom()` will receive exactly 100 bytes in one call (assuming the buffer is large enough and the datagram was not truncated). If the buffer is too small, the excess bytes are silently discarded (on Linux; `MSG_TRUNC` flag can detect this).

This means:

```c
// Sender sends two messages
sendto(fd, "AB", 2, ...);   // Datagram 1: "AB"
sendto(fd, "CDE", 3, ...);  // Datagram 2: "CDE"

// Receiver gets them separately
recvfrom(fd, buf, 100, ...); // Returns 2, buf = "AB"
recvfrom(fd, buf, 100, ...); // Returns 3, buf = "CDE"
```

With TCP, the receiver might get "ABCDE" in a single `recv()` or "A" then "BCDE" or any other split. UDP never merges or splits your data.

## UDP Reliability Techniques

When you need some reliability without full TCP, common techniques include:

### Sequence Numbers
Add a monotonically increasing sequence number to each datagram. The receiver detects gaps (missing packets) and reordering.

### Acknowledgments and Retransmission
The receiver acknowledges each datagram (or a range of datagrams, as in TCP SACK). The sender retransmits unacknowledged datagrams after a timeout.

### Checksums
UDP already includes a 16-bit checksum, but applications often add their own stronger checksum (e.g., CRC32) for data integrity verification.

### Forward Error Correction (FEC)
Encode redundant data so the receiver can reconstruct lost packets without retransmission. Used in real-time streaming where retransmission latency is unacceptable.

### Congestion Control
UDP has no built-in congestion control. If you send UDP at line rate, you can cause packet loss for other traffic. QUIC implements TCP-style congestion control (Cubic by default) over UDP.

## Important Socket Options for UDP

| Option | Purpose |
|--------|---------|
| `SO_REUSEADDR` | Allow multiple sockets to bind to the same port (useful for multicast) |
| `SO_BROADCAST` | Enable sending broadcast packets |
| `SO_RCVBUF` / `SO_SNDBUF` | Increase socket buffer size to reduce drops |
| `IP_MULTICAST_TTL` | Set TTL for multicast datagrams |
| `IP_ADD_MEMBERSHIP` | Join a multicast group |

## Interview Questions

1. What is the maximum size of a UDP datagram? What happens if you exceed it?
2. Explain how UDP preserves message boundaries while TCP does not.
3. How would you implement reliable delivery over UDP? Describe the components you would need.
4. Why does DNS use UDP? Under what circumstances does it fall back to TCP?
5. What is the difference between `send()` and `sendto()` on a UDP socket?
6. How can you detect truncated UDP datagrams on Linux?
7. Why does UDP not need a listen/accept sequence?
8. What is multicast? How does it differ from broadcast?
9. A UDP server receives out-of-order packets. How would you handle this in a gaming application?
10. What is QUIC and why does it run over UDP instead of TCP?