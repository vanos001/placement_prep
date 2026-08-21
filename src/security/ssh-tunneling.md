# SSH Tunneling

SSH tunneling is the use of the SSH protocol's port forwarding features to securely route arbitrary TCP traffic through an SSH connection. Originally part of SSH 1.x (1995) and extended in SSH 2.0 (2006), tunneling is a powerful tool for accessing services on remote networks, bypassing firewalls, and encrypting otherwise-unencrypted protocols. This page covers the three tunneling modes, the security considerations, and the production patterns.

## The Three Modes

### Local Port Forwarding (-L)

Forwards a local port to a remote host:port via the SSH server:

```bash
ssh -L 8080:remote-server:80 user@ssh-server
```

```text
Localhost:8080 → SSH tunnel → SSH server → remote-server:80
```

The local port 8080 listens; connections are forwarded through the SSH server to `remote-server:80` (which the SSH server can reach, even if the local host can't).

Example use: access an internal-only web service:
```bash
ssh -L 8080:internal-web:80 user@bastion.example.com
# Now http://localhost:8080 reaches internal-web:80 via the bastion
```

### Remote Port Forwarding (-R)

Forwards a port on the SSH server back to a local host:port:

```bash
ssh -R 9090:localhost:80 user@ssh-server
```

```text
SSH server:9090 → SSH tunnel → Localhost:80
```

The SSH server's port 9090 listens; connections are forwarded back through the SSH tunnel to the local host's port 80.

Example use: expose a local development server to the internet via a remote SSH server:
```bash
ssh -R 8080:localhost:3000 user@my-remote-server
# Now my-remote-server:8080 → localhost:3000
```

### Dynamic Port Forwarding (-D)

Creates a SOCKS proxy on the local host:

```bash
ssh -D 1080 user@ssh-server
```

```text
Localhost:1080 → SOCKS5 proxy → SSH tunnel → SSH server → any remote TCP
```

Applications that support SOCKS5 (browsers, curl, etc.) can use the local port 1080 as a proxy; all traffic is tunneled through the SSH server.

Example use: route all browser traffic through an SSH server (VPN-like):
```bash
ssh -D 1080 user@ssh-server
# Configure browser to use SOCKS5 proxy at localhost:1080
```

## Common Patterns

### Bastion Host / Jump Host

For accessing a private network via a public bastion:

```bash
ssh -J user@bastion.example.com user@internal-host.internal.example.com
```

`-J` (ProxyJump) is the modern way: it tunnels the SSH connection to `internal-host` through `bastion`. The internal host is reachable only via the bastion.

### Database Access

```bash
# Forward PostgreSQL port (5432) from the remote DB server
ssh -L 5432:db-host.internal:5432 user@bastion.example.com
# Now psql -h localhost -p 5432 connects to db-host.internal via the bastion
psql -h localhost -p 5432 mydb
```

This avoids exposing the database port to the internet; the SSH connection (with key auth) is the only entry point.

### Reverse Tunnel for NAT Traversal

For a machine behind NAT (e.g., a home server) that wants to be reachable:

```bash
# On the home server (behind NAT), establish a reverse tunnel to a public server
ssh -R 2222:localhost:22 user@public-server.example.com
# Now public-server:2222 → home server:22 (SSH)
# From anywhere: ssh -p 2222 user@public-server.example.com → reaches the home server
```

Use autossh to keep the tunnel alive:
```bash
autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" \
    -R 2222:localhost:22 user@public-server.example.com -N
```

`-N` means "no command" — only forward ports.

### Tunneling HTTP Through SSH

For unencrypted HTTP traffic:

```bash
ssh -L 8080:internal-http:80 user@bastion.example.com
curl http://localhost:8080/
```

The HTTP traffic is encrypted through the SSH tunnel; only the SSH server to `internal-http:80` leg is plaintext (within the private network).

## SSH Configuration

For persistent tunnels, configure SSH:

```sshconfig
# ~/.ssh/config
Host bastion
  HostName bastion.example.com
  User myuser
  IdentityFile ~/.ssh/id_ed25519
  
  # Persistent reverse tunnel
  RemoteForward 2222 localhost:22
  
  # Keepalive (prevents idle disconnects)
  ServerAliveInterval 30
  ServerAliveCountMax 3
  
  # No shell (for tunnel-only use)
  RequestTTY no
  RemoteCommand exit 0  # or just use -N
```

Then:
```bash
ssh -N bastion  # establish the tunnel without a shell
```

## Security Considerations

### Gateway Ports (-g)

By default, SSH only listens on `localhost` for forwarded ports. To listen on all interfaces (allowing other machines to use the tunnel), use `-g` or `GatewayPorts yes`:

```bash
ssh -g -L 8080:internal:80 user@bastion
# Now other machines can connect to this machine:8080
```

Security implication: anyone who can reach this machine's port 8080 can use the tunnel. Use sparingly.

### Tunnel-Only Users

For SSH users that should only tunnel (no shell), create a restricted user:

```bash
# Create a user with no shell
sudo useradd -m -s /usr/sbin/nologin tunnel-only
sudo passwd tunnel-only

# Configure SSH (with forced command for tunneling)
sudo tee -a /etc/ssh/sshd_config << EOF
Match User tunnel-only
  ForceCommand internal-sftp  # or just no shell
  AllowTcpForwarding yes
  PermitTTY no
  X11Forwarding no
EOF
```

### Key Authentication Only

Disable password auth for tunnels:

```sshconfig
# /etc/ssh/sshd_config
PasswordAuthentication no
PubkeyAuthentication yes
```

For tunnel-only users, this is essential.

### Time-Limited Keys

For temporary access, generate keys with validity periods:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/temp_key -O force-command='internal-sftp' -O no-port-forwarding -V '+1d'
```

The key is valid for 1 day; useful for contractors or one-off access.

## Production Use Cases

### Dev/Staging Database Access

Developers tunnel to a staging database without exposing it to the internet:

```bash
# In ~/.ssh/config
Host staging-db-tunnel
  HostName bastion.staging.example.com
  User developer
  LocalForward 5432 staging-db.internal:5432
  ServerAliveInterval 30
```

```bash
# Connect
ssh -N staging-db-tunnel
# Now psql -h localhost connects to staging-db
```

### Accessing Services in a Private VPC

```bash
ssh -L 8080:internal-service.vpc:80 user@bastion
```

The internal service is never exposed; the bastion (with MFA-enforced SSH) is the only entry.

### Web-Based Administration

For accessing web admin interfaces (e.g., admin panels, Grafana, Prometheus) that should not be public:

```bash
ssh -L 3000:grafana.internal:3000 user@bastion
# Open http://localhost:3000
```

## Common Pitfalls

1. **Forgetting that SSH tunnels don't scale.** A single SSH tunnel has a TCP throughput limit (~1 Gbps on modern hardware). For high-throughput, use a proper VPN (WireGuard, IPSec).

2. **Forgetting that the SSH server's CPU is the bottleneck.** SSH encrypts every byte; for high-throughput, the server's CPU saturates. Use AES-GCM (hardware-accelerated) or ChaCha20-Poly1305.

3. **Forgetting that tunnels can be hijacked.** A compromised local user can use an established tunnel. Use restrictive config (no shell, forced commands) for tunnel-only users.

4. **Forgetting that local forwards can conflict.** Two SSH tunnels to the same local port (`-L 8080:...`) conflict; only the first works. Use different ports.

5. **Forgetting that DNS isn't tunneled.** The tunnel forwards TCP/UDP ports, not DNS. For DNS resolution of internal hosts, use a separate DNS tunnel or configure `/etc/hosts`.

6. **Forgetting that tunnels die when the SSH connection dies.** For persistent tunnels, use autossh or systemd to restart on failure.

## Comparison to Other Tunneling Solutions

| Solution | Use case | Performance | Security |
|----------|----------|-------------|----------|
| SSH tunnel | Ad-hoc, single-user, dev | ~1 Gbps | Strong (SSH encryption) |
| WireGuard | VPN, many users | ~3 Gbps | Strong (modern crypto) |
| IPSec | Site-to-site VPN | ~5 Gbps | Strong (mature) |
| SSLH / TLS termination | Multiplex on port 443 | High | TLS |
| Cloudflare Tunnel | Expose local to internet | Variable | TLS + Cloudflare auth |

For occasional access, SSH tunnels are the simplest. For persistent VPN, WireGuard. For site-to-site, IPSec. For web exposure, Cloudflare Tunnel.

## References

- [SSH port forwarding (OpenSSH documentation)](https://www.openssh.com/txt/release-1.2.3)
- [SSH Config: LocalForward, RemoteForward](https://www.ssh.com/academy/ssh/config)
- [autossh: Keep-alive SSH tunnels](https://www.harding.motd.ca/autossh/)
- [SSH ForceCommand and tunnel-only users](https://man.openbsd.org/sshd_config#ForceCommand)
- [SSH jump host (ProxyJump)](https://www.redhat.com/sysadmin/ssh-jump-host)
- [Tailscale / Cloudflare Tunnel alternatives](https://tailscale.com/)
- [LWN: SSH tunneling overview (2020)](https://lwn.net/Articles/815575/)
