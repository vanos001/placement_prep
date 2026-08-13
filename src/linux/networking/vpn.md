# VPN Technologies

## Introduction

A **Virtual Private Network (VPN)** creates an encrypted tunnel over a public network, enabling secure communication between remote sites or users. VPNs are essential for protecting data in transit, connecting distributed infrastructure, bypassing geographic restrictions, and providing remote access to corporate networks. Linux offers exceptional VPN support with multiple protocols — from the modern WireGuard to the battle-tested OpenVPN and kernel-integrated IPsec. This chapter covers the major VPN technologies, their architectures, and practical Linux configuration.

## VPN Architecture Types

```mermaid
graph TB
    subgraph "VPN Types"
        S2S["<b>Site-to-Site</b><br>Connect two networks<br>Router-to-router"]
        R2S["<b>Remote Access</b><br>Client connects to network<br>Road warrior"]
        MESH["<b>Mesh</b><br>Every node connects<br>to every other node"]
    end

    S2S -->|"Example"| S2S_EX["Branch office ↔ HQ<br>Data center ↔ DR site"]
    R2S -->|"Example"| R2S_EX["Employee laptop ↔ Corp VPN<br>Admin SSH via VPN"]
    MESH -->|"Example"| MESH_EX["Zero-trust overlay<br>Cloud service mesh"]
```

## WireGuard

**WireGuard** is a modern, high-performance VPN protocol written by Jason A. Donenfeld. It was merged into Linux kernel 5.6 (March 2020) and is praised for its simplicity, speed, and small codebase (~4,000 lines vs OpenVPN's ~100,000).

### Key Properties

| Property | Details |
|----------|---------|
| **Protocol** | UDP only (port 51820 default) |
| **Encryption** | ChaCha20-Poly1305, Curve25519, BLAKE2s, SipHash24 |
| **Authentication** | Public/private key pairs (like SSH) |
| **Performance** | Runs in kernel space; ~1 Gbps+ throughput |
| **Roaming** | Survives IP changes (uses public keys, not IPs) |
| **Code size** | ~4,000 lines of C (auditable) |
| **Overhead** | ~60 bytes per packet |

### Architecture

```mermaid
graph LR
    subgraph "Site A (10.0.1.0/24)"
        A1["Host 10.0.1.10"]
        A2["Host 10.0.1.11"]
        AWG["wg0: 10.10.0.1<br>Endpoint: 203.0.113.1:51820<br>PublicKey: AAAA..."]
    end

    subgraph "WireGuard Tunnel (UDP)"
        T["Encrypted UDP<br>ChaCha20-Poly1305"]
    end

    subgraph "Site B (10.0.2.0/24)"
        B1["Host 10.0.2.10"]
        B2["Host 10.0.2.11"]
        BWG["wg0: 10.10.0.2<br>Endpoint: 198.51.100.1:51820<br>PublicKey: BBBB..."]
    end

    A1 --> AWG --> T --> BWG --> B1
    A2 --> AWG
    B2 --> BWG
```

### Site-to-Site Configuration

**Server (Site A — 203.0.113.1):**

```bash
# Install WireGuard
$ apt install wireguard   # Debian/Ubuntu
$ dnf install wireguard-tools   # RHEL/Fedora

# Generate key pair
$ wg genkey | tee /etc/wireguard/private.key | wg pubkey > /etc/wireguard/public.key
```

```ini
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <server-private-key>
Address = 10.10.0.1/24
ListenPort = 51820
# Enable IP forwarding for site-to-site
PostUp = sysctl -w net.ipv4.ip_forward=1
PostDown = sysctl -w net.ipv4.ip_forward=0

# NAT for traffic from VPN to internet (optional)
PostUp = iptables -t nat -A POSTROUTING -s 10.10.0.0/24 -o eth0 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -s 10.10.0.0/24 -o eth0 -j MASQUERADE

[Peer]
# Site B
PublicKey = <site-b-public-key>
AllowedIPs = 10.0.2.0/24, 10.10.0.2/32
Endpoint = 198.51.100.1:51820
PersistentKeepalive = 25
```

**Client (Site B — 198.51.100.1):**

```ini
# /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <site-b-private-key>
Address = 10.10.0.2/24
ListenPort = 51820
PostUp = sysctl -w net.ipv4.ip_forward=1
PostDown = sysctl -w net.ipv4.ip_forward=0

[Peer]
# Site A
PublicKey = <site-a-public-key>
AllowedIPs = 10.0.1.0/24, 10.10.0.1/32
Endpoint = 203.0.113.1:51820
PersistentKeepalive = 25
```

### Management Commands

```bash
# Start the tunnel
$ wg-quick up wg0
[#] ip link add wg0 type wireguard
[#] wg setconf wg0 /dev/fd/63
[#] ip -4 address add 10.10.0.1/24 dev wg0
[#] ip link set mtu 1420 up dev wg0

# View tunnel status
$ wg show
interface: wg0
  public key: <key>
  private key: (hidden)
  listening port: 51820

peer: <peer-key>
  endpoint: 198.51.100.1:51820
  allowed ips: 10.0.2.0/24, 10.10.0.2/32
  latest handshake: 42 seconds ago
  transfer: 1.48 GiB received, 3.21 GiB sent

# Enable at boot
$ systemctl enable wg-quick@wg0

# Test connectivity
$ ping 10.10.0.2
PING 10.10.0.2 (10.10.0.2) 56(84) bytes of data.
64 bytes from 10.10.0.2: icmp_seq=1 ttl=64 time=15.3 ms
```

### Road Warrior Configuration

```ini
# Client laptop config
[Interface]
PrivateKey = <laptop-private-key>
Address = 10.10.0.100/24
DNS = 10.0.1.5   # Use corporate DNS

[Peer]
PublicKey = <server-public-key>
AllowedIPs = 10.0.0.0/8, 172.16.0.0/12   # Route corporate networks
Endpoint = vpn.example.com:51820
PersistentKeepalive = 25
```

## OpenVPN

**OpenVPN** is the most widely deployed open-source VPN solution. It uses TLS for key exchange and can operate over TCP or UDP.

### Key Properties

| Property | Details |
|----------|---------|
| **Protocol** | UDP or TCP (port 1194 default) |
| **Encryption** | AES-256-GCM, ChaCha20-Poly1305 (via OpenSSL) |
| **Authentication** | Certificates (PKI), username/password, pre-shared keys |
| **Performance** | Userspace; ~200–500 Mbps typical |
| **Flexibility** | Highly configurable; supports complex topologies |
| **Platform** | Linux, Windows, macOS, Android, iOS |

### PKI Setup

```bash
# Install EasyRSA for certificate management
$ apt install openvpn easy-rsa

# Initialize PKI
$ cd /etc/openvpn
$ make-cadir easy-rsa
$ cd easy-rsa
$ ./easyrsa init-pki
$ ./easyrsa build-ca nopass
$ ./easyrsa gen-req server nopass
$ ./easyrsa sign-req server server
$ ./easyrsa gen-dh
$ openvpn --genkey secret ta.key

# Generate client certificate
$ ./easyrsa gen-req client1 nopass
$ ./easyrsa sign-req client client1
```

### Server Configuration

```
# /etc/openvpn/server.conf
port 1194
proto udp
dev tun

ca /etc/openvpn/easy-rsa/pki/ca.crt
cert /etc/openvpn/easy-rsa/pki/issued/server.crt
key /etc/openvpn/easy-rsa/pki/private/server.key
dh /etc/openvpn/easy-rsa/pki/dh.pem
tls-auth /etc/openvpn/easy-rsa/ta.key 0

# Network topology
server 10.8.0.0 255.255.255.0
topology subnet

# Push routes and DNS to clients
push "route 192.168.1.0 255.255.255.0"
push "dhcp-option DNS 10.0.0.5"
push "dhcp-option DOMAIN example.com"

# Security
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
tls-cipher TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384

# Performance
sndbuf 524288
rcvbuf 524288
push "sndbuf 524288"
push "rcvbuf 524288"

# Logging
status /var/log/openvpn/status.log
log-append /var/log/openvpn/openvpn.log
verb 3

# Allow clients to see each other
client-to-client

# Keep tunnel alive
keepalive 10 120

# Reduce privileges after init
user nobody
group nogroup
persist-key
persist-tun
```

```bash
# Start OpenVPN
$ systemctl start openvpn@server
$ systemctl enable openvpn@server

# Check status
$ cat /var/log/openvpn/status.log
OpenVPN CLIENT LIST
Updated,Mon Jan 15 12:00:00 2024
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
client1,198.51.100.50:54321,1048576,2097152,Mon Jan 15 10:00:00 2024
ROUTING TABLE
Virtual Address,Common Name,Real Address,Last Ref
10.8.0.2,client1,198.51.100.50:54321,Mon Jan 15 11:59:00 2024
```

### Client Configuration

```
# /etc/openvpn/client.ovpn
client
dev tun
proto udp
remote vpn.example.com 1194
resolv-retry infinite
nobind

<ca>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</ca>

<cert>
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
</cert>

<key>
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
</key>

<tls-auth>
-----BEGIN OpenVPN Static key V1-----
...
-----END OpenVPN Static key V1-----
</tls-auth>
key-direction 1

cipher AES-256-GCM
auth SHA256
verb 3
```

```bash
# Connect
$ openvpn --config client.ovpn

# Or via systemd
$ cp client.ovpn /etc/openvpn/client.conf
$ systemctl start openvpn@client
```

## IPsec

**IPsec** (Internet Protocol Security) operates at the network layer (Layer 3) and can encrypt any IP traffic. It is the standard for site-to-site VPNs between routers and firewalls.

### IPsec Components

```mermaid
graph TB
    subgraph "IPsec Protocol Suite"
        IKE["<b>IKEv2</b><br>Key exchange, SA negotiation<br>UDP 500/4500"]
        ESP["<b>ESP</b><br>Encapsulation Security Payload<br>Protocol 50"]
        AH["<b>AH</b><br>Authentication Header<br>Protocol 51 (rarely used)"]
        NATT["<b>NAT-T</b><br>NAT Traversal<br>UDP 4500"]
    end

    IKE -->|"Establishes"| SA["Security Associations"]
    SA -->|"Defines"| ESP
    ESP -->|"Modes"| TRANSPORT["Transport Mode<br>(encrypt payload only)"]
    ESP -->|"Modes"| TUNNEL["Tunnel Mode<br>(encrypt entire packet)"]
```

### IPsec with strongSwan

```bash
# Install strongSwan
$ apt install strongswan strongswan-pki libcharon-extra-plugins
```

**Site-to-site configuration:**

```
# /etc/ipsec.conf — Site A (203.0.113.1)
config setup
    charondebug="ike 2, knl 2, cfg 2"

conn site-to-site
    type=tunnel
    authby=secret
    left=203.0.113.1           # Local public IP
    leftsubnet=10.0.1.0/24     # Local network
    right=198.51.100.1         # Remote public IP
    rightsubnet=10.0.2.0/24    # Remote network
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256-modp2048!
    keyingtries=0
    ikelifetime=1h
    lifetime=8h
    dpddelay=30
    dpdtimeout=120
    dpdaction=restart
    auto=start
```

```
# /etc/ipsec.secrets
203.0.113.1 198.51.100.1 : PSK "your-pre-shared-key-here"
```

```bash
# Start IPsec
$ systemctl start strongswan
$ systemctl enable strongswan

# Check status
$ ipsec status
site-to-site[1]: ESTABLISHED 5 minutes ago, 203.0.113.1[203.0.113.1]...198.51.100.1[198.51.100.1]
site-to-site{1}: INSTALLED, TUNNEL, reqid 1, ESP SPIs: c1234567_i c7654321_o
site-to-site{1}: 10.0.1.0/24 === 10.0.2.0/24

# View Security Associations
$ ip xfrm state
src 203.0.113.1 dst 198.51.100.1
    proto esp spi 0xc7654321 reqid 1 mode tunnel
    replay-window 0 flag af-unspec
    auth-trunc hmac(sha256) 0x... 128
    enc cbc(aes) 0x...
```

### IKEv2 with Certificates

```bash
# Generate CA and certificates
$ ipsec pki --gen --type rsa --size 4096 --outform pem > ca-key.pem
$ ipsec pki --self --ca --lifetime 3650 --in ca-key.pem \
    --type rsa --dn "CN=VPN CA" --outform pem > ca-cert.pem

# Server certificate
$ ipsec pki --gen --type rsa --size 4096 --outform pem > server-key.pem
$ ipsec pki --pub --in server-key.pem --type rsa | \
    ipsec pki --issue --lifetime 1825 --cacert ca-cert.pem --cakey ca-key.pem \
    --dn "CN=vpn.example.com" --san="vpn.example.com" --flag serverAuth \
    --flag ikeIntermediate --outform pem > server-cert.pem

# Install certificates
$ cp ca-cert.pem /etc/ipsec.d/cacerts/
$ cp server-cert.pem /etc/ipsec.d/certs/
$ cp server-key.pem /etc/ipsec.d/private/
```

## VPN Protocol Comparison

| Feature | WireGuard | OpenVPN | IPsec (IKEv2) |
|---------|-----------|---------|---------------|
| **Kernel module** | Yes (since 5.6) | No (userspace) | Yes (kernel) |
| **Transport** | UDP only | UDP or TCP | UDP 500/4500 |
| **Speed** | Very fast (~1 Gbps) | Moderate (~500 Mbps) | Fast (~800 Mbps) |
| **Code size** | ~4,000 lines | ~100,000 lines | ~400,000 lines (kernel) |
| **Setup complexity** | Very simple | Moderate | Complex |
| **Roaming** | Excellent (public key based) | Limited | Good (MOBIKE) |
| **NAT traversal** | Built-in | Good | NAT-T (UDP 4500) |
| **Mobile support** | Android, iOS, Linux | All platforms | Native on most OSes |
| **Auditability** | Easy (small code) | Moderate | Difficult |
| **Use case** | General purpose, mesh | Complex configs, TCP fallback | Enterprise, site-to-site |

## Split Tunneling vs Full Tunnel

```bash
# Split tunnel — only specific traffic goes through VPN
# WireGuard AllowedIPs controls this:
AllowedIPs = 10.0.0.0/8, 172.16.0.0/12
# Only 10.x and 172.16.x traffic uses the VPN

# Full tunnel — ALL traffic goes through VPN (including internet)
AllowedIPs = 0.0.0.0/0, ::/0
# DNS also pushed to use VPN DNS
```

```mermaid
graph LR
    subgraph "Split Tunnel"
        S_CLIENT["Client"] -->|"10.0.0.0/8"| S_VPN["VPN"]
        S_CLIENT -->|"Internet"| S_DIRECT["Direct"]
    end

    subgraph "Full Tunnel"
        F_CLIENT["Client"] -->|"All traffic"| F_VPN["VPN"]
        F_VPN --> F_INTERNET["Internet"]
    end
```

## VPN Performance Tuning

```bash
# Increase buffer sizes (WireGuard)
$ sysctl -w net.core.rmem_max=26214400
$ sysctl -w net.core.wmem_max=26214400

# Enable BBR congestion control for VPN traffic
$ sysctl -w net.ipv4.tcp_congestion_control=bbr

# Optimize MTU (avoid fragmentation)
# WireGuard default: 1420 (1500 - 60 - 20)
# OpenVPN default: 1500 (may need reduction for TCP)
$ ip link set mtu 1420 dev wg0

# Enable hardware offloading (if supported)
$ ethtool -K eth0 tx-udp-segmentation on   # GSO for WireGuard
```

## WireGuard Internals

### Noise Protocol Framework

WireGuard is built on the Noise Protocol Framework, specifically the `Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s` handshake pattern:

```
Noise_IKpsk2:
  → Initiator: Handshake Initiation (ephemeral key + encrypted static key)
  ← Responder: Handshake Response (ephemeral key + encrypted static key)
  → Both: Transport Data (encrypted with derived session keys)
```

The handshake involves:
1. **Key Exchange**: Curve25519 ECDH between ephemeral and static keys
2. **Authentication**: BLAKE2s-based MAC verifies peer identity
3. **Key Derivation**: HKDF derives session keys from shared secrets
4. **Forward Secrecy**: New ephemeral keys per handshake; old keys discarded

### Cookie Mechanism (DoS Protection)

WireGuard includes a built-in cookie mechanism to mitigate DoS attacks:

```
Client → Server: Initiation (valid static key)
Server → Client: Response + Cookie (MAC of client IP + timestamp)
Client → Server: Initiation + Cookie (proves it received the response)
```

If the server is under load, it may require the cookie before accepting new handshakes. This prevents IP spoofing attacks.

### Cryptographic Routing

WireGuard uses a routing table based on public keys, not IP addresses:

```c
/* Simplified WireGuard peer lookup */
struct wg_peer {
    struct wg_device *device;
    struct list_head peer_list;
    struct noise_keypairs keypairs;
    struct endpoint endpoint;      /* Current IP:port */
    struct allowedips allowed_ips; /* Cryptokey routing table */
    /* ... */
};

/* Allowed IPs → peer lookup is a trie */
struct allowedips {
    struct allowedips_node __rcu *root4;
    struct allowedips_node __rcu *root6;
};
```

This means WireGuard can survive IP changes (roaming) — the peer is identified by its public key, and the endpoint is updated dynamically.

### Performance Characteristics

| Metric | WireGuard | OpenVPN | IPsec |
|--------|-----------|---------|-------|
| Throughput (Gbps) | 1.0 – 3.0 | 0.2 – 0.5 | 0.8 – 2.0 |
| Latency (ms) | 5 – 20 | 15 – 50 | 10 – 30 |
| CPU usage | Low | High | Medium |
| Memory usage | Minimal | Moderate | Moderate |
| Handshake time | ~1 ms | ~50 ms | ~100 ms |

## OpenVPN Data Channel Offload (DCO)

OpenVPN DCO moves the data channel processing from userspace to kernel space, dramatically improving performance:

```bash
# Load the OVPN DCO kernel module
$ modprobe ovpn-dco

# OpenVPN with DCO
$ openvpn --config server.conf --data-ciphers AES-256-GCM --ovpn-dco
```

DCO is available since Linux 6.x and brings OpenVPN performance closer to WireGuard:

| Mode | Throughput |
|------|-----------|
| OpenVPN (userspace) | ~300 Mbps |
| OpenVPN DCO (kernel) | ~2 Gbps |
| WireGuard (kernel) | ~3 Gbps |

## IPsec NAT Traversal (NAT-T)

IPsec ESP packets are encrypted IP payloads, which breaks through NAT devices that modify packet headers. NAT-T solves this:

1. **Detection**: During IKE negotiation, peers detect NAT in the path
2. **Encapsulation**: ESP packets are wrapped in UDP port 4500
3. **Keepalive**: NAT-T keepalives prevent NAT table expiry

```
Original: [IP Header][ESP Header][Encrypted Payload]
NAT-T:    [IP Header][UDP 4500][ESP Header][Encrypted Payload]
```

```bash
# Enable NAT-T in strongSwan
conn nat-t-example
    left=203.0.113.1
    right=198.51.100.1
    forceencaps=yes  # Force UDP encapsulation
```

## VPN and IPv6

Modern VPNs should support IPv6 to avoid leaks:

```bash
# WireGuard: dual-stack tunnel
[Interface]
Address = 10.10.0.1/24, fd00::1/64

[Peer]
AllowedIPs = 10.0.0.0/8, fd00::/48

# OpenVPN: push IPv6
server-ipv6 fd00:dead:beef::/48
push "route-ipv6 fd00::/48"

# IPsec: dual-stack SA
conn dual-stack
    leftsubnet=10.0.1.0/24,fd00:1::/48
    rightsubnet=10.0.2.0/24,fd00:2::/48
```

### IPv6 Leak Prevention

When using a full-tunnel VPN, ensure IPv6 traffic is also routed through the tunnel:

```bash
# Disable IPv6 on physical interface when VPN is active
sysctl -w net.ipv6.conf.eth0.disable_ipv6=1

# Or use policy routing
ip -6 rule add from fd00::/48 table vpn
ip -6 route add ::/0 dev wg0 table vpn
```

## Kill Switch Implementation

A kill switch prevents traffic from leaking outside the VPN tunnel:

```bash
#!/bin/bash
# WireGuard kill switch using nftables

# Flush existing rules
nft flush ruleset

# Allow loopback
nft add rule inet filter input iif lo accept
nft add rule inet filter output oif lo accept

# Allow VPN server endpoint
nft add rule inet filter output oifname "eth0" ip daddr 203.0.113.1 udp dport 51820 accept

# Allow DNS (through VPN only)
nft add rule inet filter output oifname "wg0" udp dport 53 accept

# Allow traffic through VPN tunnel
nft add rule inet filter output oifname "wg0" accept
nft add rule inet filter input iifname "wg0" accept

# Drop everything else
default drop
```

Alternatively, use WireGuard's `AllowedIPs` with policy routing:

```bash
# Route only VPN server IP outside the tunnel
ip rule add from all table main suppress_prefixlength 0
ip rule add from all to 203.0.113.1 table main
ip route add default dev wg0 table vpn
```

## Troubleshooting VPN Connections

```bash
# WireGuard debugging
$ wg show wg0
$ tcpdump -i eth0 port 51820 -n
$ ping -c 3 10.10.0.2

# OpenVPN debugging
$ openvpn --config client.ovpn --verb 6   # Maximum verbosity
$ journalctl -u openvpn@server -f

# IPsec debugging
$ ipsec statusall
$ ip xfrm state
$ ip xfrm policy
$ journalctl -u strongswan -f

# General VPN debugging
$ traceroute 10.10.0.2
$ ss -ulnp | grep -E "51820|1194|500"
$ iptables -L -n -v | grep -i vpn

# Check for MTU issues (fragmentation)
ping -M do -s 1400 10.10.0.2
# If this fails, reduce MTU on the VPN interface
```

## Cross-References

- [tcpip-suite](./tcpip-suite.md) — TCP/IP protocol suite overview
- [sockmap](../kernel/networking/sockmap.md) — BPF socket redirection (alternative to VPN for local proxying)
- [TLS](./tls.md) — TLS encryption used by OpenVPN and IKEv2
- [IP Addressing](./ip-addressing.md) — VPN address planning
- [IPv6](./ipv6.md) — IPv6 in VPN tunnels
- [Routing Protocols](./routing-protocols.md) — Dynamic routing over VPN
- [Firewalls](../security/) — VPN firewall rules
- [Network Troubleshooting](./troubleshooting.md) — Debugging VPN connectivity

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [WireGuard Official Website](https://www.wireguard.com/)
- [WireGuard Documentation](https://www.wireguard.com/quickstart/)
- [OpenVPN Documentation](https://openvpn.net/community-resources/)
- [strongSwan Documentation](https://docs.strongswan.org/)
- [RFC 7296 — IKEv2](https://www.rfc-editor.org/rfc/rfc7296)
- [RFC 4301 — IPsec Architecture](https://www.rfc-editor.org/rfc/rfc4301)
- [Tailscale — WireGuard-based Mesh VPN](https://tailscale.com/)
- [WireGuard vs OpenVPN Benchmarks](https://www.wireguard.com/performance/)

## Related Topics

- [TLS](./tls.md) — TLS encryption used by OpenVPN and IKEv2
- [IP Addressing](./ip-addressing.md) — VPN address planning
- [IPv6](./ipv6.md) — IPv6 in VPN tunnels
- [Routing Protocols](./routing-protocols.md) — Dynamic routing over VPN
- [Firewalls](../security/) — VPN firewall rules
- [Network Troubleshooting](./troubleshooting.md) — Debugging VPN connectivity
