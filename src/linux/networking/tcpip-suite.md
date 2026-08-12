# TCP/IP Suite Deep Dive

## Introduction

The TCP/IP protocol suite is the foundation of modern networking. This chapter provides a deep dive into the core protocols — IP, TCP, UDP, ICMP, and ARP — examining their packet formats, operations, and how they interact to enable reliable network communication.

## Internet Protocol (IP)

### IPv4 Header

The IPv4 header is 20-60 bytes long:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version|  IHL  |Type of Service|          Total Length         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Identification        |Flags|      Fragment Offset    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Time to Live |    Protocol   |         Header Checksum       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       Source Address                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Destination Address                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options                    |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

**Key fields:**

| Field | Bits | Description |
|-------|------|-------------|
| Version | 4 | IP version (4 for IPv4) |
| IHL | 4 | Internet Header Length (in 32-bit words) |
| Type of Service | 8 | QoS and ECN flags |
| Total Length | 16 | Total packet size in bytes |
| Identification | 16 | Fragment identification |
| Flags | 3 | DF (Don't Fragment), MF (More Fragments) |
| Fragment Offset | 13 | Fragment position in original packet |
| Time to Live | 8 | Hop limit (decremented at each router) |
| Protocol | 8 | Transport protocol (6=TCP, 17=UDP, 1=ICMP) |
| Header Checksum | 16 | Header integrity check |

### IP Fragmentation

When a packet exceeds the MTU (Maximum Transmission Unit), it must be fragmented:

```mermaid
flowchart LR
    subgraph "Original Packet (3000 bytes)"
        DATA["Data: 3000 bytes"]
    end

    subgraph "Fragment 1"
        H1[IP Header]
        D1["Data: 1480 bytes"]
        F1["Frag Offset: 0, MF: 1"]
    end

    subgraph "Fragment 2"
        H2[IP Header]
        D2["Data: 1480 bytes"]
        F2["Frag Offset: 1480, MF: 1"]
    end

    subgraph "Fragment 3"
        H3[IP Header]
        D3["Data: 40 bytes"]
        F3["Frag Offset: 2960, MF: 0"]
    end

    DATA --> H1
    DATA --> H2
    DATA --> H3
```
```bash
# Check MTU of interface
$ ip link show eth0 | grep mtu
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500

# Set MTU
$ sudo ip link set eth0 mtu 9000

# Path MTU Discovery
$ ping -c 4 -M do -s 1472 8.8.8.8
PING 8.8.8.8 (8.8.8.8) 1472(1500) bytes of data.
1480 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=5.43 ms
```

### IPv6 Header

IPv6 simplifies the header to a fixed 40 bytes:

```
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Version| Traffic Class |           Flow Label                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Payload Length        |  Next Header  |   Hop Limit   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+                         Source Address                        +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
+                                                               +
|                                                               |
+                      Destination Address                      +
|                                                               |
+                                                               +
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

## Transmission Control Protocol (TCP)

### TCP Header

The TCP header is 20-60 bytes:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        Sequence Number                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Acknowledgment Number                      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Data |       |C|E|U|A|P|R|S|F|                               |
| Offset| Rsrvd |W|C|R|C|S|S|Y|I|            Window             |
|       |       |R|E|G|K|H|T|N|N|                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Checksum            |         Urgent Pointer        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                    Options                    |    Padding    |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### TCP Three-Way Handshake

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: SYN (seq=100)
    Note right of S: Server creates TCB
    S->>C: SYN-ACK (seq=300, ack=101)
    Note left of C: Client creates TCB
    C->>S: ACK (ack=301)
    Note over C,S: Connection ESTABLISHED
```

### TCP Four-Way Teardown

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: FIN (seq=100)
    Note right of S: CLOSE_WAIT
    S->>C: ACK (ack=101)
    Note left of C: FIN_WAIT_2
    S->>C: FIN (seq=300)
    Note right of S: LAST_ACK
    C->>S: ACK (ack=301)
    Note left of C: TIME_WAIT (2MSL)
    Note over C,S: Connection CLOSED
```

### TCP Flags

| Flag | Bit | Description |
|------|-----|-------------|
| CWR | 0 | Congestion Window Reduced |
| ECE | 1 | ECN-Echo |
| URG | 2 | Urgent pointer valid |
| ACK | 3 | Acknowledgment number valid |
| PSH | 4 | Push data to application |
| RST | 5 | Reset connection |
| SYN | 6 | Synchronize sequence numbers |
| FIN | 7 | End of data |

### TCP Flow Control

TCP uses a sliding window for flow control:

```mermaid
flowchart LR
    subgraph "Sender Window"
        SENT["Sent &amp; ACKed"]
        SENT2[Sent, Not ACKed]
        SEND[Can Send]
        WAIT[Cannot Send]
    end

    subgraph "Sequence Numbers"
        N1[1-100]
        N2[101-200]
        N3[201-300]
        N4[301-400]
    end

    SENT --> N1
    SENT2 --> N2
    SEND --> N3
    WAIT --> N4
```
**Window scaling** allows windows larger than 65,535 bytes:

```bash
# Check window scaling
$ sysctl net.ipv4.tcp_window_scaling
net.ipv4.tcp_window_scaling = 1

# View current window size
$ ss -t -i | grep -o 'wscale:[^ ]*'
wscale:7,7
```

### TCP Congestion Control

TCP congestion control prevents network congestion:

```mermaid
flowchart TB
    SS[Slow Start] --> CA[Congestion Avoidance]
    CA --> FR[Fast Retransmit]
    FR --> RR[Recovery]
    RR --> CA
    CA --> SS
    SS --> |Packet Loss| CA
```
**Algorithms:**

- **Reno**: Classic algorithm with fast retransmit and recovery
- **CUBIC**: Default in Linux, cubic growth function
- **BBR**: Bottleneck bandwidth and RTT-based

```bash
# Check current congestion control
$ sysctl net.ipv4.tcp_congestion_control
net.ipv4.tcp_congestion_control = cubic

# Change to BBR
$ sudo sysctl -w net.ipv4.tcp_congestion_control=bbr

# Load BBR module
$ sudo modprobe tcp_bbr
```

### TCP Retransmission

TCP retransmits lost packets:

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    C->>S: Data (seq=100, 100 bytes)
    Note right of S: Packet lost
    C->>C: Retransmission timeout (RTO)
    C->>S: Retransmit (seq=100, 100 bytes)
    S->>C: ACK (ack=200)
```
```bash
# Check retransmission statistics
$ nstat | grep -i retrans
TcpRetransSegs    123    0.0
TcpExtTCPSlowStartRetrans    45    0.0

# Monitor retransmissions in real-time
$ ss -t -i | grep -i retrans
```

## User Datagram Protocol (UDP)

### UDP Header

The UDP header is a fixed 8 bytes:

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Source Port          |       Destination Port        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            Length             |           Checksum            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### UDP Characteristics

- **Connectionless**: No handshake or teardown
- **Unreliable**: No delivery guarantee
- **No ordering**: Packets may arrive out of order
- **Message-oriented**: Preserves message boundaries
- **Low overhead**: 8-byte header vs TCP's 20+ bytes

### UDP Use Cases

| Application | Why UDP? |
|-------------|----------|
| DNS | Small queries, quick response |
| DHCP | Broadcast, no connection |
| VoIP | Low latency, tolerates loss |
| Video streaming | Real-time, tolerates loss |
| Gaming | Low latency critical |
| SNMP | Simple queries |

## ICMP (Internet Control Message Protocol)

### ICMP Header

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Type      |      Code     |          Checksum             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Rest of Header                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### ICMP Message Types

| Type | Name | Description |
|------|------|-------------|
| 0 | Echo Reply | Ping response |
| 3 | Destination Unreachable | Various error conditions |
| 4 | Source Quench | Congestion control (deprecated) |
| 5 | Redirect | Route change notification |
| 8 | Echo Request | Ping |
| 11 | Time Exceeded | TTL expired |

### Destination Unreachable Codes

| Code | Description |
|------|-------------|
| 0 | Network unreachable |
| 1 | Host unreachable |
| 2 | Protocol unreachable |
| 3 | Port unreachable |
| 4 | Fragmentation needed |
| 13 | Administratively prohibited |

## ARP (Address Resolution Protocol)

### ARP Packet Format

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|         Hardware Type         |         Protocol Type         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  HW Addr Len  | Proto Addr Len|           Operation          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Sender Hardware Address                     |
+                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |     Sender Protocol Address   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                   Target Hardware Address                     |
+                               +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                               |     Target Protocol Address   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### ARP Operation

```mermaid
sequenceDiagram
    participant A as Host A
    participant B as Host B
    participant C as Host C

    A->>B: ARP Request (Broadcast)
    A->>C: ARP Request (Broadcast)
    Note right of A: Who has 192.168.1.20?<br>Tell 192.168.1.10
    B->>A: ARP Reply (Unicast)
    Note left of B: 192.168.1.20 is at<br>AA:BB:CC:DD:EE:FF
    Note over A: Cache entry created
```
### ARP Cache Management

```bash
# View ARP cache
$ ip neigh show
192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE
192.168.1.20 dev eth0 lladdr AA:BB:CC:DD:EE:FF STALE

# ARP cache states
# PERMANENT - Static entry, never expires
# NOARP - No ARP resolution needed
# REACHABLE - Recently confirmed
# STALE - May be outdated
# DELAY - Waiting for upper-layer confirmation
# INCOMPLETE - ARP request sent, no reply yet
# FAILED - ARP resolution failed

# Add static entry
$ sudo ip neigh add 192.168.1.100 lladdr 00:11:22:33:44:55 dev eth0

# Delete entry
$ sudo ip neigh del 192.168.1.100 dev eth0

# Flush cache
$ sudo ip neigh flush all
```

## Protocol Interactions

### TCP State Machine

TCP connections transition through a well-defined state machine:

```mermaid
stateDiagram-v2
    [*] --> CLOSED
    CLOSED --> LISTEN: passive open
    CLOSED --> SYN_SENT: active open (connect)
    LISTEN --> SYN_RCVD: SYN received
    SYN_SENT --> ESTABLISHED: SYN-ACK received
    SYN_SENT --> CLOSED: timeout/RST
    SYN_RCVD --> ESTABLISHED: ACK received
    SYN_RCVD --> CLOSED: RST/timeout
    ESTABLISHED --> FIN_WAIT_1: close() called
    ESTABLISHED --> CLOSE_WAIT: FIN received
    FIN_WAIT_1 --> FIN_WAIT_2: ACK received
    FIN_WAIT_1 --> CLOSING: FIN received
    FIN_WAIT_1 --> TIME_WAIT: FIN+ACK received
    FIN_WAIT_2 --> TIME_WAIT: FIN received
    CLOSING --> TIME_WAIT: ACK received
    CLOSE_WAIT --> LAST_ACK: close() called
    LAST_ACK --> CLOSED: ACK received
    TIME_WAIT --> CLOSED: 2MSL timeout
```

### State Descriptions

| State | Description | Typical Duration |
|-------|-------------|------------------|
| `LISTEN` | Waiting for incoming connections | Until connection arrives |
| `SYN_SENT` | SYN sent, waiting for SYN-ACK | ~1-3 seconds (timeout) |
| `SYN_RCVD` | SYN-ACK sent, waiting for ACK | ~1-3 seconds (timeout) |
| `ESTABLISHED` | Connection active | Application-determined |
| `FIN_WAIT_1` | FIN sent, waiting for ACK | ~1-3 seconds |
| `FIN_WAIT_2` | ACK received, waiting for FIN | Application-dependent |
| `CLOSE_WAIT` | FIN received, waiting for app close | Application-dependent |
| `CLOSING` | Both sides closing simultaneously | Brief |
| `LAST_ACK` | FIN sent after CLOSE_WAIT, waiting for ACK | ~1-3 seconds |
| `TIME_WAIT` | Waiting for 2×MSL (typically 60s) | 60 seconds on Linux |

### Monitoring TCP States

```bash
# Count connections per state
$ ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn
    150 ESTABLISHED
     42 TIME_WAIT
     15 CLOSE_WAIT
      8 LISTEN
      3 SYN_SENT

# View TIME_WAIT connections
$ ss -tan state time-wait | head -20

# Tune TIME_WAIT (caution: affects connection reuse)
sysctl -w net.ipv4.tcp_tw_reuse=1
sysctl -w net.ipv4.tcp_max_tw_buckets=100000
```

## Linux Kernel Networking Stack

The Linux kernel networking stack processes packets through several layers:

```mermaid
flowchart TB
    subgraph "Ingress Path"
        NIC["Network Interface"] --> NAPI["NAPI Polling"]
        NAPI --> SKB["sk_buff Creation"]
        SKB --> NETFILTER_IN["Netfilter (PREROUTING)"]
        NETFILTER_IN --> IP_RECV["ip_rcv() -- IP Layer"]
        IP_RECV --> IP_ROUTE["ip_route_input() -- Routing"]
        IP_ROUTE --> NETFILTER_IN2["Netfilter (INPUT)"]
        NETFILTER_IN2 --> TCP_RECV["tcp_v4_rcv() -- TCP Layer"]
        TCP_RECV --> SOCK_QUEUE["Socket Receive Queue"]
        SOCK_QUEUE --> APP_RECV["Application recv()"]
    end
```

```mermaid
flowchart TB
    subgraph "Egress Path"
        APP_SEND["Application send()"] --> SENDMSG["tcp_sendmsg() -- TCP Layer"]
        SENDMSG --> TCP_QUEUE["TCP Write Queue"]
        TCP_QUEUE --> IP_OUTPUT["ip_output() -- IP Layer"]
        IP_OUTPUT --> NETFILTER_OUT["Netfilter (OUTPUT)"]
        NETFILTER_OUT --> NETFILTER_FWD["Netfilter (POSTROUTING)"]
        NETFILTER_FWD --> NEIGH_SEND["neigh_output() -- ARP/Neighbor"]
        NEIGH_SEND --> DEV_QUEUE["dev_queue_xmit() -- Device"]
        DEV_QUEUE --> NIC_OUT["Network Interface"]
    end
```

### sk_buff (Socket Buffer)

The `sk_buff` is the kernel's packet representation:

```c
struct sk_buff {
    /* Linked list pointers */
    struct sk_buff *next, *prev;

    /* Packet data pointers */
    unsigned char *head;    /* Start of buffer */
    unsigned char *data;    /* Start of data */
    unsigned char *tail;    /* End of data */
    unsigned char *end;     /* End of buffer */

    /* Protocol headers */
    __u16 transport_header; /* TCP/UDP header offset */
    __u16 network_header;   /* IP header offset */
    __u16 mac_header;       /* Ethernet header offset */

    /* Metadata */
    unsigned int len;       /* Data length */
    __u32 priority;         /* QoS priority */
    __u8 ip_summed;         /* Checksum state */

    /* Network device */
    struct net_device *dev;
    struct sock *sk;        /* Owning socket */
};
```

The sk_buff uses a clever buffer management design:
- `head`/`end` delimit the entire buffer (including headroom for protocol headers)
- `data`/`tail` delimit the actual packet data
- Protocol headers are prepended (push) or removed (pull) by adjusting `data`

### Netfilter Hooks

Netfilter provides five hook points in the packet path:

```
Ingress:
  ┌─────────┐
  │PREROUTING│ → ip_rcv_finish → routing decision
  └────┬─────┘
       ↓
  ┌────┴─────┐
  │  INPUT    │ → ip_local_deliver → TCP/UDP
  └──────────┘

Egress:
  ┌─────────┐
  │  OUTPUT  │ → ip_output (local traffic)
  └────┬─────┘
       ↓
  ┌────┴──────┐
  │POSTROUTING│ → ip_finish_output → dev_queue_xmit
  └───────────┘

Forward:
  PREROUTING → routing → FORWARD → POSTROUTING
```

```bash
# View netfilter hook statistics
$ sudo iptables -L -v -n

# View conntrack table
$ sudo conntrack -L | head -20

# Count packets per hook
$ sudo nft list ruleset
```

## ECN (Explicit Congestion Notification)

ECN allows routers to signal congestion without dropping packets:

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant S as Server

    C->>S: SYN (ECN capable)
    S->>C: SYN-ACK (ECN capable)
    C->>S: Data (ECT bit set)
    R->>R: Congestion detected
    Note over R: Sets CE bit instead of dropping
    R->>S: Data (CE bit set)
    S->>C: ACK (ECE bit set)
    C->>S: Data (CWR bit set)
    Note over C,S: Sender reduces congestion window
```

```bash
# Enable ECN
$ sysctl -w net.ipv4.tcp_ecn=1
# 0 = disable, 1 = request ECN, 2 = always use ECN

# Check ECN status
$ ss -t -i | grep -i ecn
```

## SCTP (Stream Control Transmission Protocol)

SCTP is a reliable, message-oriented transport protocol that combines features of TCP and UDP:

| Feature | TCP | UDP | SCTP |
|---------|-----|-----|------|
| Connection-oriented | Yes | No | Yes (association) |
| Reliable delivery | Yes | No | Yes |
| Ordered delivery | Yes | No | Configurable |
| Message boundaries | No | Yes | Yes |
| Multi-streaming | No | No | Yes |
| Multi-homing | No | No | Yes |
| Head-of-line blocking | Yes | N/A | Per-stream |

### SCTP Use Cases

- **SS7/SIGTRAN**: Telephony signaling over IP
- **WebRTC**: Data channels use SCTP over DTLS
- **MongoDB**: Database replication
- **5G**: Core network interfaces

```bash
# Check SCTP support
$ lsmod | grep sctp
$ cat /proc/net/sctp/eps

# View SCTP associations
$ ss -s -A sctp
```

## DNS over UDP

```mermaid
sequenceDiagram
    participant C as Client
    participant S as DNS Server (8.8.8.8)

    C->>S: DNS Query (UDP, port 53)
    Note right of C: Source: random port<br>Dest: 53
    S->>C: DNS Response (UDP)
    Note left of S: Source: 53<br>Dest: client port
```

### HTTP over TCP

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Web Server

    C->>S: TCP SYN
    S->>C: TCP SYN-ACK
    C->>S: TCP ACK
    C->>S: HTTP GET / (TCP data)
    S->>C: HTTP 200 OK (TCP data)
    C->>S: TCP FIN
    S->>C: TCP FIN-ACK
    C->>S: TCP ACK
```

### Traceroute using ICMP and UDP

```mermaid
sequenceDiagram
    participant C as Client
    participant R1 as Router 1
    participant R2 as Router 2
    participant D as Destination

    C->>R1: UDP (TTL=1)
    R1->>C: ICMP Time Exceeded
    C->>R2: UDP (TTL=2)
    R2->>C: ICMP Time Exceeded
    C->>D: UDP (TTL=3)
    D->>C: ICMP Port Unreachable
```
## Protocol Analysis with tcpdump

### Capturing Specific Protocols

```bash
# Capture TCP traffic
$ sudo tcpdump -i eth0 tcp

# Capture UDP traffic
$ sudo tcpdump -i eth0 udp

# Capture ICMP traffic
$ sudo tcpdump -i eth0 icmp

# Capture ARP traffic
$ sudo tcpdump -i eth0 arp

# Capture specific TCP flags
$ sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0'
$ sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-rst) != 0'

# Capture DNS queries
$ sudo tcpdump -i eth0 port 53
```

### Packet Dissection

```bash
# Verbose output with packet details
$ sudo tcpdump -i eth0 -vv -c 5 port 80

# Show hex dump
$ sudo tcpdump -i eth0 -X -c 5 port 80

# Show ASCII
$ sudo tcpdump -i eth0 -A -c 5 port 80
```

## Protocol Statistics

```bash
# View IP statistics
$ cat /proc/net/snmp | grep -A1 Ip

# View TCP statistics
$ cat /proc/net/snmp | grep -A1 Tcp

# View UDP statistics
$ cat /proc/net/snmp | grep -A1 Udp

# View ICMP statistics
$ cat /proc/net/snmp | grep -A1 Icmp

# Detailed TCP statistics
$ cat /proc/net/netstat | head -2
```

## Cross-References

- [vpn](./vpn.md) — VPN technologies using TCP/IP tunnels
- [sockmap](../kernel/networking/sockmap.md) — BPF socket redirection for TCP
- [Network Fundamentals](fundamentals.md) — OSI model and network basics
- [DNS](dns.md) — Domain Name System
- [SSH](ssh.md) — Secure Shell
- [TLS](tls.md) — Transport Layer Security
- [Kernel TCP/IP Implementation](../kernel/networking/tcpip.md) — How the kernel implements TCP/IP

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

1. **RFC 791** — Internet Protocol
2. **RFC 793** — Transmission Control Protocol
3. **RFC 768** — User Datagram Protocol
4. **RFC 792** — Internet Control Message Protocol
5. **RFC 826** — Ethernet Address Resolution Protocol
6. **RFC 5681** — TCP Congestion Control
7. *TCP/IP Illustrated, Volume 1* by W. Richard Stevens
8. *TCP/IP Illustrated, Volume 2* by Gary R. Wright and W. Richard Stevens

## Related Topics

- [Network Fundamentals](fundamentals.md) — OSI model and network basics
- [DNS](dns.md) — Domain Name System
- [SSH](ssh.md) — Secure Shell
- [TLS](tls.md) — Transport Layer Security
- [Kernel TCP/IP Implementation](../kernel/networking/tcpip.md) — How the kernel implements TCP/IP
