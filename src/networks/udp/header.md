# UDP Header Format

## Overview

The UDP header is one of the simplest headers in the TCP/IP protocol stack — just **8 bytes** (64 bits). This minimalism is by design: UDP provides only the essential features needed for process-to-process communication (port numbers) and basic data integrity (checksum), leaving everything else to the application layer.

Understanding the UDP header is essential for packet analysis, protocol design, and interview questions about why UDP is so lightweight compared to TCP's 20+ byte header.

## Detailed Explanation

### UDP Header Layout

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            Length             |           Checksum            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         Data (payload)                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Field Descriptions

#### 1. Source Port (16 bits)
- **Range**: 0–65535
- **Purpose**: Identifies the sending application
- **Optional**: Can be set to 0 if no reply is expected
- **Ephemeral ports**: Typically 49152–65535 (IANA) or 32768–60999 (Linux)

```
Source Port = 0:
  Sender doesn't care about replies
  Used for one-way notifications
  
Source Port > 0:
  Normal case
  Receiver can send replies to this port
```

#### 2. Destination Port (16 bits)
- **Range**: 0–65535
- **Purpose**: Identifies the receiving application
- **Required**: Must be specified
- **Well-known ports**: 0–1023 (DNS=53, DHCP=67/68, NTP=123)

```
Common UDP ports:
  53    - DNS
  67    - DHCP Server
  68    - DHCP Client
  69    - TFTP
  123   - NTP
  161   - SNMP
  500   - IKE (IPsec)
  514   - Syslog
  1194  - OpenVPN
  4500  - NAT-T (IPsec)
```

#### 3. Length (16 bits)
- **Range**: 8–65535 bytes
- **Purpose**: Total datagram size (header + data)
- **Minimum**: 8 (header only, 0 bytes data)
- **Maximum**: 65535 (theoretical), limited by IP and MTU

```
Length = 8:   Header only, no data (empty datagram)
Length = 9:   Header + 1 byte data
Length = 1472: Header + 1464 bytes data (typical Ethernet)
Length = 65535: Maximum theoretical size

Data size = Length - 8
```

#### 4. Checksum (16 bits)
- **IPv4**: Optional (can be 0 to skip)
- **IPv6**: Mandatory (RFC 2460)
- **Purpose**: Detect corruption in header + data + pseudo-header
- **Algorithm**: One's complement sum of all 16-bit words

### Checksum Calculation

The UDP checksum is computed over three parts:

```
1. Pseudo-Header (not transmitted, only for calculation)
2. UDP Header (8 bytes)
3. UDP Data (variable length)
```

**Pseudo-Header Format (IPv4):**
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Source Address                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Destination Address                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      zero     |   Protocol    |         UDP Length            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

Protocol = 17 (UDP)
UDP Length = same as Length field in UDP header
```

**Checksum Algorithm:**
```python
def udp_checksum(src_ip, dst_ip, udp_header, data):
    # Build pseudo-header
    pseudo = struct.pack('!4s4sBBH',
        socket.inet_aton(src_ip),
        socket.inet_aton(dst_ip),
        0,      # reserved
        17,     # UDP protocol
        len(udp_header) + len(data)  # UDP length
    )
    
    # Combine pseudo-header + UDP header + data
    packet = pseudo + udp_header + data
    
    # Pad to even length if needed
    if len(packet) % 2:
        packet += b'\x00'
    
    # One's complement sum
    checksum = 0
    for i in range(0, len(packet), 2):
        word = (packet[i] << 8) + packet[i+1]
        checksum += word
    
    # Fold 32-bit sum to 16 bits
    while checksum >> 16:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    
    # One's complement
    checksum = ~checksum & 0xFFFF
    
    return checksum
```

### Why Include Pseudo-Header?

The pseudo-header verifies that the datagram was delivered to the **correct host and port**:
- **IP addresses**: Catches misdelivery (IP header corrupted)
- **Protocol number**: Catches demultiplexing errors
- **UDP length**: Catches length field corruption

Without the pseudo-header, a corrupted IP header could deliver the datagram to the wrong host, and UDP wouldn't detect it.

### UDP Datagram Size Limits

```
Theoretical maximum: 65,535 bytes (16-bit Length field)
IP maximum: 65,535 bytes (16-bit Total Length field)
Ethernet MTU: 1,500 bytes
Practical UDP payload: ~1,472 bytes (Ethernet)
                      ~1,452 bytes (PPPoE)

Large datagrams → IP fragmentation:
  > MTU → IP splits into fragments
  Fragments reassembled at receiver
  One lost fragment → entire UDP datagram lost
  Reassembly buffer overflow → fragments dropped
```

**Fragmentation Impact:**
```
Sending 8000-byte UDP datagram over Ethernet (MTU 1500):

IP fragments:
  Fragment 1: [IP 20][UDP 8][Data 1472] = 1500 bytes
  Fragment 2: [IP 20][Data 1480]         = 1500 bytes
  Fragment 3: [IP 20][Data 1480]         = 1500 bytes
  Fragment 4: [IP 20][Data 1480]         = 1500 bytes
  Fragment 5: [IP 20][Data 1480]         = 1500 bytes
  Fragment 6: [IP 20][Data 608]          = 628 bytes

If ANY fragment is lost → entire UDP datagram discarded
Probability of loss increases with more fragments
```

### UDP vs TCP Header Comparison

```
UDP Header (8 bytes):
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            Length             |           Checksum            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

TCP Header (20+ bytes):
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |       |U|A|P|R|S|F|                                  |
| Offset| Rsrvd |R|C|S|S|Y|I|            Window                |
|       |       |G|K|H|T|N|N|                                   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |         Urgent Pointer        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options (variable)                         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### Reading UDP Headers in tcpdump

```bash
# Basic UDP capture
$ tcpdump -i eth0 -nn udp port 53 -v

# Output:
17:42:00.123456 IP (tos 0x0, ttl 64, id 12345, offset 0, flags [none],
    proto UDP (17), length 60)
    192.168.1.1.54321 > 8.8.8.8.53: [udp sum ok] 4+ A? example.com. (32)

# Breakdown:
# proto UDP (17) - UDP protocol
# length 60 - Total IP packet size
# 192.168.1.1.54321 - Source IP and port
# 8.8.8.8.53 - Destination IP and port
# [udp sum ok] - Checksum verified
# 4+ - DNS query ID
# A? example.com - DNS query
# (32) - UDP payload size
```

### Hex Dump of UDP Header

```
Example DNS query:
Source Port: 54321 (0xD431)
Destination Port: 53 (0x0035)
Length: 32 (0x0020)
Checksum: 0x1234

Hex dump:
D4 31 00 35 00 20 12 34
│   │   │   │   │   │   │   │
│   │   │   │   │   │   │   └─ Checksum high byte
│   │   │   │   │   │   └───── Checksum low byte
│   │   │   │   │   └───────── Length high byte
│   │   │   │   └───────────── Length low byte
│   │   │   └───────────────── Dest port high byte
│   │   └───────────────────── Dest port low byte
│   └───────────────────────── Source port high byte
└───────────────────────────── Source port low byte
```

## Example: UDP Header Analysis

### Complete DNS Query Datagram

```
Ethernet Header (14 bytes):
  Dst MAC: 00:11:22:33:44:55
  Src MAC: AA:BB:CC:DD:EE:FF
  Type: 0x0800 (IPv4)

IPv4 Header (20 bytes):
  Version: 4, IHL: 5
  Total Length: 52
  Protocol: 17 (UDP)
  Src IP: 192.168.1.100
  Dst IP: 8.8.8.8

UDP Header (8 bytes):
  Source Port: 43210
  Destination Port: 53
  Length: 32
  Checksum: 0xABCD

DNS Query (24 bytes):
  Transaction ID: 0x1234
  Flags: 0x0100 (standard query)
  Questions: 1
  Query: example.com A

Total UDP payload: 24 bytes
Total datagram: 8 + 24 = 32 bytes ✓
```

### Checksum Verification (Wireshark)

```
Frame 1: 52 bytes on wire (416 bits)
Ethernet II: 14 bytes
Internet Protocol: 20 bytes
User Datagram Protocol: 8 bytes
    Source Port: 43210
    Destination Port: 53
    Length: 32
    Checksum: 0xabcd [correct]
    [Checksum Status: Good]
```

## Interview Questions

### Q1: How many bytes is the UDP header and what are its fields?
**A:** The UDP header is **8 bytes** (64 bits) with 4 fields: Source Port (16 bits), Destination Port (16 bits), Length (16 bits), and Checksum (16 bits). This is much simpler than TCP's 20+ byte header with 10+ fields.

### Q2: Why is the UDP checksum optional in IPv4 but mandatory in IPv6?
**A:** IPv4 has its own header checksum that protects the IP header. IPv6 removed the IP header checksum for efficiency (link-layer CRCs catch most errors). To compensate, IPv6 mandates the UDP checksum to ensure data integrity. In practice, most IPv4 UDP implementations calculate the checksum anyway.

### Q3: What is the UDP pseudo-header and why is it included in the checksum?
**A:** The pseudo-header includes source/destination IP addresses and protocol number. It's included in the checksum calculation (but not transmitted) to verify the datagram reached the correct host. Without it, a corrupted IP header could deliver data to the wrong host undetected.

### Q4: What is the maximum UDP datagram size?
**A:** Theoretically 65,535 bytes (16-bit Length field). Practically limited by IP MTU — typically 1,472 bytes for Ethernet. Larger datagrams are fragmented at the IP layer, which increases loss probability (one lost fragment = entire datagram lost).

### Q5: Can the UDP source port be 0?
**A:** Yes. A source port of 0 means the sender doesn't expect a reply. This is valid per RFC 768. However, most implementations use an ephemeral port as the source port even when no reply is expected.

### Q6: How does UDP handle message boundaries?
**A:** Each `sendto()` creates one UDP datagram. The receiver's `recvfrom()` returns exactly one datagram. If the receive buffer is too small, the excess is truncated (or an error occurs). Unlike TCP, UDP preserves message boundaries — no need for delimiters or length prefixes.

### Q7: What happens when a UDP datagram is too large for the MTU?
**A:** IP fragments the datagram into multiple fragments. Each fragment has the same IP Identification field but different Fragment Offset. The receiver reassembles all fragments before passing to UDP. If any fragment is lost, the entire UDP datagram is discarded — no partial delivery.

### Q8: Why does UDP not need sequence numbers?
**A:** UDP doesn't guarantee ordering — each datagram is independent. If the application needs ordered delivery, it must implement its own sequence numbers. This is by design: UDP provides minimal overhead, and applications that don't need ordering (VoIP, gaming) save the overhead.

## Common Mistakes

1. **Forgetting the pseudo-header in checksum calculation**: The checksum must include the pseudo-header (IP addresses, protocol, UDP length). Forgetting this means the checksum only protects the payload, not the delivery context.

2. **Not realizing checksum is mandatory in IPv6**: Many developers assume the UDP checksum is always optional. In IPv6, it's mandatory and must be calculated correctly. A zero checksum in IPv6 means the packet is dropped.

3. **Confusing UDP Length with IP Total Length**: UDP Length = header (8) + payload. IP Total Length = IP header (20+) + UDP header (8) + payload. They're different!

4. **Assuming small UDP datagrams avoid fragmentation**: Even small datagrams can be fragmented if the path MTU is smaller than expected (e.g., PPPoE reduces MTU to 1492, or VPN tunnels reduce it further).

5. **Not understanding that one lost fragment loses the whole datagram**: This is a critical difference from TCP. TCP can retransmit individual segments. With UDP, if any IP fragment is lost, the entire UDP datagram is discarded by the receiver's IP layer.

6. **Thinking the Length field includes the pseudo-header**: The Length field only covers the UDP header (8 bytes) + payload. The pseudo-header is only used for checksum calculation, not transmitted.

7. **Using payload > 1472 bytes without considering fragmentation**: The safe UDP payload size for Ethernet is ~1472 bytes (1500 MTU - 20 IP - 8 UDP). Larger payloads trigger IP fragmentation, which has significant performance and reliability implications.

## Summary

| Field | Size | Range | Purpose |
|-------|------|-------|---------|
| **Source Port** | 16 bits | 0–65535 | Sender's port (optional) |
| **Destination Port** | 16 bits | 0–65535 | Receiver's port (required) |
| **Length** | 16 bits | 8–65535 | Header + payload size |
| **Checksum** | 16 bits | 0–65535 | Integrity check (optional IPv4, mandatory IPv6) |

| Aspect | Value |
|--------|-------|
| **Header size** | 8 bytes (fixed) |
| **Maximum datagram** | 65,535 bytes (theoretical), ~1472 bytes (practical) |
| **Minimum datagram** | 8 bytes (header only) |
| **Pseudo-header** | Used for checksum only, not transmitted |
| **Fragmentation** | Handled by IP, not UDP |

The UDP header's simplicity is its strength — 8 bytes of overhead provides process-to-process communication with minimal cost, making it ideal for applications where speed and simplicity matter more than guaranteed delivery.

## Cross-References

- [UDP Overview](README.md) — General UDP concepts and characteristics
- [TCP vs UDP](tcp-vs-udp.md) — Detailed comparison with TCP
- [UDP Applications](applications.md) — Real-world use cases
- [DNS Overview](../dns/README.md) — DNS uses UDP port 53
- [TCP Options](../tcp/options.md) — TCP header options (UDP has none)
