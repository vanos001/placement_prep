# Network Programming

## What Is Network Programming?

Network programming is the discipline of writing software that communicates across a computer network. It encompasses the APIs, protocols, patterns, and abstractions that enable processes—on the same machine or across the globe—to exchange data reliably and efficiently.

Modern software is inherently networked. Whether you are building web servers, databases, messaging systems, IoT gateways, or distributed services, understanding network programming is essential for designing correct, performant, and resilient systems.

## The Socket API

The **Berkeley Sockets API** (POSIX.1-2008) is the standard interface for network I/O on Unix-like systems. It originated in BSD 4.2 (1983) and provides a uniform abstraction for both local (Unix domain) and network (IPv4/IPv6) communication.

Core operations:

| Operation | Description |
|-----------|-------------|
| `socket()` | Create a communication endpoint |
| `bind()` | Associate the socket with an address/port |
| `listen()` | Mark a socket as passive (server) |
| `accept()` | Accept an incoming connection |
| `connect()` | Initiate a connection (client) |
| `send()`/`recv()` | Send/receive data (TCP) |
| `sendto()`/`recvfrom()` | Send/receive data (UDP) |
| `close()` | Release the socket resource |

Sockets are file descriptors in Unix. This means they integrate with `select()`, `poll()`, `epoll()`, and all standard I/O multiplexing mechanisms.

## TCP vs UDP for Programming

| Aspect | TCP | UDP |
|--------|-----|-----|
| Connection | Connection-oriented (3-way handshake) | Connectionless |
| Reliability | Guaranteed delivery, ordering, error detection | Best-effort delivery |
| Streaming | Byte stream (no message boundaries) | Datagram (message-preserving) |
| Flow control | Built-in (sliding window, congestion control) | None |
| Overhead | Higher (headers, state, retransmissions) | Minimal (8-byte header) |
| Use cases | Web, databases, file transfer, SSH | DNS, gaming, streaming, VoIP, IoT |

**TCP** gives you a reliable byte stream. The API is simple (`send`/`recv`), but understanding what happens underneath—congestion windows, slow start, Nagle's algorithm—is critical for performance.

**UDP** gives you raw datagrams. You must handle reliability, ordering, and flow control yourself. However, the lack of overhead makes it ideal for latency-sensitive applications where occasional packet loss is acceptable.

## The Client-Server Model

Most network programming follows the client-server pattern:

- The **server** binds to a known address, listens for connections, and handles client requests
- The **client** connects to the server's address and sends requests

```
Server:  socket() → bind() → listen() → accept() → recv()/send() → close()
Client:  socket() → connect()              → send()/recv() → close()
```

## Common Communication Patterns

### Request-Response
The client sends a request, the server sends a reply. Used by HTTP, DNS, databases, and most RPC frameworks. Simple to reason about but has higher latency per operation due to round trips.

### Publish/Subscribe
Producers publish messages to topics; consumers subscribe to topics of interest. Decouples producers from consumers. Implemented by Kafka, MQTT, Redis Pub/Sub, and NATS.

### Streaming
A persistent, long-lived connection over which data flows continuously in one or both directions. Used for real-time feeds, video/audio streaming, and server-sent events. WebSockets, gRPC streaming, and TCP persistent connections are common implementations.

## References

- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)
- [POSIX Socket API — IEEE Std 1003.1](https://pubs.opengroup.org/onlinepubs/9699919799/functions/V2_chap02.html#tag_15_10)
- [TCP/IP Illustrated, Volume 1 — W. Richard Stevens](https://www.pearson.com/en-us/subject-catalog/p/tcp-ip-illustrated-volume-1-the-protocols-addison-wesley-professional-computing-series/P200000006626)
- [UNIX Network Programming, Volume 1 — W. Richard Stevens](https://www.unixnetworkprogramming.com/)
- [Linux man pages: socket(7), tcp(7), udp(7), ip(7)](https://man7.org/linux/man-pages/)

## Interview Questions

1. What is the difference between a TCP socket and a UDP socket at the API level?
2. Explain the TCP three-way handshake and four-way teardown.
3. Why are sockets represented as file descriptors in Unix?
4. What is the difference between `send()` and `write()` on a TCP socket?
5. Describe the request-response pattern versus the streaming pattern for network communication.
6. What is a connection-oriented protocol versus a connectionless protocol?
7. When would you choose UDP over TCP for a new application?
8. What is Nagle's algorithm and when might you want to disable it?
9. Explain the TIME_WAIT state. Why does it exist and why can it be a problem for high-connection-rate servers?
10. What are the differences between a Unix domain socket and a TCP socket?