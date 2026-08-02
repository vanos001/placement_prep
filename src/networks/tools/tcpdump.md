# tcpdump

## Overview

tcpdump is a powerful **command-line packet analyzer** available on most Unix-like systems. It captures and displays network packets in real-time or saves them to pcap files for later analysis.

## Basic Syntax

```bash
tcpdump [options] [filter expression]
```

## Common Options

| Option | Description | Example |
|--------|-------------|---------|
| `-i <interface>` | Capture on interface | `-i eth0` |
| `-c <count>` | Stop after N packets | `-c 100` |
| `-w <file>` | Write to pcap file | `-w capture.pcap` |
| `-r <file>` | Read from pcap file | `-r capture.pcap` |
| `-n` | Don't resolve hostnames | `-n` |
| `-nn` | Don't resolve hostnames or ports | `-nn` |
| `-v, -vv, -vvv` | Verbosity levels | `-vv` |
| `-X` | Show hex and ASCII | `-X` |
| `-A` | Show ASCII only | `-A` |
| `-s <snaplen>` | Capture N bytes per packet | `-s 0` (all) |
| `-e` | Show link-layer header | `-e` |
| `-tttt` | Show human-readable timestamps | `-tttt` |

## Common Capture Examples

### Basic Captures

```bash
# Capture all traffic on eth0
sudo tcpdump -i eth0

# Capture with no DNS resolution (faster)
sudo tcpdump -i eth0 -nn

# Capture 100 packets then stop
sudo tcpdump -i eth0 -c 100

# Capture to file
sudo tcpdump -i eth0 -w capture.pcap

# Read from file
tcpdump -r capture.pcap
```

### Filter by Host

```bash
# Traffic to/from specific host
sudo tcpdump -i eth0 host 10.0.0.1

# Traffic from specific source
sudo tcpdump -i eth0 src host 10.0.0.1

# Traffic to specific destination
sudo tcpdump -i eth0 dst host 10.0.0.1

# Traffic on subnet
sudo tcpdump -i eth0 net 192.168.1.0/24
```

### Filter by Port

```bash
# HTTP traffic
sudo tcpdump -i eth0 port 80

# HTTPS traffic
sudo tcpdump -i eth0 port 443

# DNS traffic
sudo tcpdump -i eth0 port 53

# SSH traffic
sudo tcpdump -i eth0 port 22

# Multiple ports
sudo tcpdump -i eth0 port 80 or port 443
```

### Filter by Protocol

```bash
# TCP only
sudo tcpdump -i eth0 tcp

# UDP only
sudo tcpdump -i eth0 udp

# ICMP only
sudo tcpdump -i eth0 icmp

# ARP only
sudo tcpdump -i eth0 arp
```

### Advanced Filters

```bash
# TCP SYN packets only
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-syn) != 0'

# TCP RST packets (connection resets)
sudo tcpdump -i eth0 'tcp[tcpflags] & (tcp-rst) != 0'

# HTTP GET requests
sudo tcpdump -i eth0 -A 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)' | grep "GET "

# Packets larger than 1000 bytes
sudo tcpdump -i eth0 'greater 1000'

# Packets with specific TTL
sudo tcpdump -i eth0 'ip[8] < 10'
```

## Output Format

```
14:23:45.123456 IP 10.0.0.1.52341 > 10.0.0.2.80: Flags [S], seq 123456789, win 65535, options [mss 1460,sackOK,TS val 123 ecr 0,nop,wscale 7], length 0
│               │              │           │    │         │       │                                    │
│               │              │           │    │         │       │                                    Packet length
│               │              │           │    │         │       TCP options
│               │              │           │    │         Window size
│               │              │           │    Sequence number
│               │              │           TCP flags ([S]=SYN, [.]=ACK, [P]=PSH, [F]=FIN, [R]=RST)
│               │              Destination IP.port
│               Source IP.port
Timestamp
```

### TCP Flags

| Flag | Symbol | Meaning |
|------|--------|---------|
| SYN | `[S]` | Synchronize (connection start) |
| ACK | `[.]` | Acknowledgment |
| PSH | `[P]` | Push (send data immediately) |
| FIN | `[F]` | Finish (connection close) |
| RST | `[R]` | Reset (connection abort) |
| SYN-ACK | `[S.]` | SYN + ACK (connection accept) |

## Practical Scenarios

### Debug TCP Connection

```bash
# Watch TCP handshake to a server
sudo tcpdump -i eth0 -nn 'host example.com and tcp port 80' -c 10

# Expected output for successful handshake:
# 1. [S]     — Client SYN
# 2. [S.]    — Server SYN-ACK
# 3. [.]     — Client ACK
```

### Find DNS Issues

```bash
# Capture DNS queries and responses
sudo tcpdump -i eth0 -nn port 53

# Look for: queries going out, responses coming back
# If queries go out but no responses = DNS server unreachable
# If responses show NXDOMAIN = domain doesn't exist
```

### Monitor Bandwidth

```bash
# Count packets per second (rough bandwidth estimate)
sudo tcpdump -i eth0 -nn -c 1000 2>&1 | tail -1
# "1000 packets captured" / time = packets/sec
```

## Combining with Other Tools

```bash
# Capture and analyze with tshark
sudo tcpdump -i eth0 -w - port 80 | tshark -r - -Y "http.request"

# Capture and count connections
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn) != 0' -c 1000 2>&1 | wc -l

# Capture HTTP headers
sudo tcpdump -i eth0 -A -s 0 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)' 2>/dev/null | grep -A 5 "HTTP/"
```

## Interview Questions

1. **Q: How would you use tcpdump to debug a connection timeout?**
   A: `sudo tcpdump -i eth0 -nn host <server> and tcp`. Look for: 1) SYN packets being sent, 2) No SYN-ACK response (firewall or server down), 3) SYN retransmissions (packet loss), 4) RST response (connection refused).

2. **Q: What's the difference between `-n` and `-nn`?**
   A: `-n` skips DNS resolution (faster). `-nn` skips both DNS resolution AND port name resolution (even faster). Always use `-nn` for performance — port 80 is clearer than "http" in many contexts.

3. **Q: How do you capture only the first 100 bytes of each packet?**
   A: `tcpdump -s 100`. This is useful when you only need headers (not payload). Use `-s 0` to capture full packets.

4. **Q: How do you filter TCP SYN packets?**
   A: `tcpdump 'tcp[tcpflags] & (tcp-syn) != 0'`. This uses BPF byte offset to check the SYN flag bit in the TCP header.

5. **Q: What's the `-X` flag used for?**
   A: `-X` shows packet contents in both hex and ASCII. Useful for inspecting application-layer data (HTTP headers, DNS queries). `-A` shows ASCII only.

## Common Mistakes

- Forgetting `sudo` (needs root to capture)
- Not using `-nn` (slow due to DNS lookups)
- Capturing on wrong interface (check with `ip link` or `ifconfig`)
- Using display filter syntax instead of BPF syntax
- Not capturing enough packets (use `-c` to limit, or `-w` to save)
- Forgetting that `-w` writes binary pcap (use `-r` to read, not `cat`)

## Summary

tcpdump is the essential CLI packet capture tool. Master BPF filters, understand TCP flags in output, and know how to combine with other tools. Use `-nn` for speed, `-w` for saving, and `-X` for payload inspection.

## Cross-References

- [Wireshark](wireshark.md) — GUI alternative with deep analysis
- [ping & traceroute](ping-traceroute.md) — Basic connectivity
- [netstat](netstat.md) — Connection inspection
- [TLS](../security/tls.md) — Analyzing encrypted traffic
