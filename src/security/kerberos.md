# Kerberos Authentication

Kerberos is a network authentication protocol that uses symmetric-key cryptography to let a client prove its identity to a service without ever sending a password over the network, and without the service needing to know the client's password. Built at MIT in the late 1980s for Project Athena, formalized in RFC 4120 (2005), and now the default authentication protocol in Active Directory, Kerberos relies on a trusted third party — the Key Distribution Center (KDC) — that vouches for clients by issuing short-lived "tickets."

## The Three-Headed Dog

The protocol is named after Cerberus, the three-headed dog of Greek mythology, because three principals are involved in every authentication:

```text
              +----------------+
              |  KDC           |
              | (AS + TGS)     |
              +-------+--------+
                      |
        +-------------+-------------+
        |                           |
        v                           v
   +---------+                 +---------+
   | Client  | <-- ticket --> | Service |
   |         |                 | (target)|
   +---------+                 +---------+
```

- **Client (principal `alice@REALM`)** — wants to access a service. Holds a long-term key derived from her password.
- **KDC (`krbtgt@REALM`)** — trusted third party. Holds the long-term keys of every principal in the realm. Composed of two logical services running on the same host: the Authentication Server (AS) and the Ticket-Granting Server (TGS).
- **Service (e.g., `host/web.example.com@REALM`)** — the target. Has its own long-term key (stored in a keytab file).

The KDC's master database maps `principal → long-term key`. The long-term key of a human user is `PBKDF2(password, salt, iterations)`; for a service it is a random key in a keytab file. The KDC's own key (called the `krbtgt` key) is what protects the TGT — only the KDC can decrypt the TGT.

## The Six-Message Flow

A complete Kerberos login + service access is six messages. The first two get the client a Ticket-Granting Ticket (TGT); the next two get a service ticket; the last two are the actual client→service request and (optionally) the server's mutual-auth response.

### Step 1: AS-REQ / AS-REP — Getting the TGT

```text
Client                              KDC (AS)
   |                                    |
   | AS-REQ:                            |
   |  - principal = alice@REALM         |
   |  - padata (PA-ENC-TIMESTAMP):      |  <-- pre-auth: timestamp encrypted
   |      timestamp encrypted with      |      with client's long-term key
   |      client's long-term key        |
   |  - nonce                           |
   |----------------------------------->|
   |                                    |
   | AS-REP:                            |
   |  - TGT (encrypted with krbtgt key):|
   |      client=alice, flags,          |
   |      session_key_K1, lifetime       |
   |  - session_key_K1, TGT lifetime     | <-- encrypted with client's
   |                                    |     long-term key
   |<-----------------------------------|
```

The TGT itself is opaque to the client — the client cannot read it. The client can only read the `session_key_K1`, which is encrypted with the client's long-term key (derived from her password). If she types the wrong password, the decryption fails.

Important: the AS does not return an AS-REP without pre-auth. Modern Kerberos requires `PA-ENC-TIMESTAMP` pre-authentication — the client must encrypt a timestamp with her long-term key and send it. Without it, the AS returns `KDC_ERR_PREAUTH_REQUIRED`. This stops offline password guessing: an attacker who captures network traffic cannot use the KDC as a password oracle.

The TGT contains:
- The client's identity
- A fresh session key `K1`, also given to the client (encrypted with her long-term key)
- A lifetime (typically 10 hours in AD)
- Flags (forwardable, renewable, pre-auth-required, etc.)

### Step 2: TGS-REQ / TGS-REP — Getting a Service Ticket

```text
Client                              KDC (TGS)
   |                                    |
   | TGS-REQ:                           |
   |  - service=host/web.example.com    |
   |  - TGT (opaque to client)          |
   |  - authenticator (encrypted with K1):
   |      client=alice, timestamp, nonce |
   |----------------------------------->|
   |                                    |
   | TGS-REP:                           |
   |  - service ticket (encrypted with  |
   |    service's long-term key):       |
   |      client=alice, session_key_K2, |
   |      lifetime, flags                |
   |  - session_key_K2                  | <-- encrypted with K1
   |<-----------------------------------|
```

The TGS decrypts the TGT using the `krbtgt` key (which only the KDC has), extracts `K1`, uses `K1` to verify the authenticator (which proves the client actually has `K1`, not just the TGT), and issues a service ticket. The service ticket is encrypted with the service's long-term key — only the service can read it.

The authenticator contains a timestamp (must be within the clock-skew tolerance, typically 5 minutes) and is single-use. The replay cache on the service rejects duplicate authenticators.

### Step 3: AP-REQ / AP-REP — Using the Service Ticket

```text
Client                              Service
   |                                    |
   | AP-REQ:                            |
   |  - service ticket (opaque to client)
   |  - authenticator (encrypted with K2):
   |      client=alice, timestamp, subkey
   |----------------------------------->|
   |                                    |
   | (service decrypts ticket with its  |
   |  own long-term key, gets K2,       |
   |  decrypts and verifies             |
   |  authenticator, checks replay      |
   |  cache, sets session)               |
   |                                    |
   | AP-REP (optional, for mutual auth):|
   |  - timestamp+1 encrypted with K2   |
   |<-----------------------------------|
```

The service never talks to the KDC during AP-REQ — the ticket is a self-contained credential that the service can validate offline using its own key. This is the central performance property of Kerberos: the KDC is consulted once per login (for the TGT) and once per service per TGT lifetime. The remaining interactions are offline.

AP-REP is optional. It is used when the client requires mutual authentication — the service proves it has the service's long-term key by returning a timestamp encrypted with `K2`. SSH with GSSAPI uses this to authenticate the server.

## Session Keys and Replay Protection

Each ticket carries a fresh symmetric key (`K1` for the TGT, `K2` for the service ticket). The crypto suite, per RFC 3961:

- **AES256-CTS-HMAC-SHA1-96** — the workhorse in modern AD
- **AES256-CTS-HMAC-SHA256-128** — newer, RFC 8009
- **RC4-HMAC** — deprecated, kept only for legacy compat

This key:

1. Is the channel key for the application session (e.g., GSS-API wrap/seal between client and service).
2. Is the key the client uses to encrypt the authenticator.

The authenticator defeats replay because:
- It contains a client-chosen timestamp.
- The service caches `(client_principal, timestamp)` tuples in a replay cache.
- A replayed authenticator's `(client, timestamp)` is already in the cache → rejected.

Clock skew tolerance (typically 5 minutes, configurable via `clockskew` in `krb5.conf`) bounds the replay window.

### Credential cache vs replay cache

Two distinct caches live on a Kerberos-enabled host:

- **Credential cache** (`/tmp/krb5cc_<uid>` or `$KRB5CCNAME`) — the client's TGT and service tickets. Written by the client, read by the client.
- **Replay cache** (`/var/tmp/`) — `(principal, timestamp, hash)` tuples seen by services. Written by the service, read by the service. Distinct from the credential cache.

A typical `klist` output:

```text
$ klist
Ticket cache: FILE:/tmp/krb5cc_1000
Default principal: alice@EXAMPLE.COM

Valid starting       Expires              Service principal
08/01/2025 09:00:00  08/01/2025 19:00:00  krbtgt/EXAMPLE.COM@EXAMPLE.COM
        renew until 08/08/2025 09:00:00
08/01/2025 09:01:00  08/01/2025 19:00:00  host/web.example.com@EXAMPLE.COM
```

The `krbtgt/EXAMPLE.COM@EXAMPLE.COM` line is the TGT. The second line is a service ticket for `host/web.example.com`. Both expire in 10 hours. The TGT is renewable for 7 days, which means the client can ask the KDC for a fresh 10-hour TGT without re-entering her password — until the renewable lifetime ends.

## Cross-Realm Authentication

In a multi-domain environment (e.g., `EXAMPLE.COM` and `PARTNER.COM`), the KDC of one realm cannot issue tickets for services in another. Cross-realm auth uses a chain of trust: a `krbtgt/PARTNER.COM@EXAMPLE.COM` principal exists in both realms, with the same long-term key.

```text
Client (alice@EXAMPLE.COM)
   |
   | TGS-REQ: service=host/web.partner.com@PARTNER.COM
   |         sent to EXAMPLE.COM KDC
   v
EXAMPLE.COM KDC
   |
   | TGS-REP: cross-realm TGT encrypted with
   |          krbtgt/PARTNER.COM@EXAMPLE.COM key
   v
Client uses cross-realm TGT to contact PARTNER.COM KDC

PARTNER.COM KDC
   |
   | TGS-REP: service ticket for host/web.partner.com
   v
Client → Service (in PARTNER.COM)
```

For each hop in the chain, the client gets a new TGT for the next realm. The trust is transitive in AD (via shortcut trusts in the forest) but in MIT Kerberos the operator must configure `capaths` explicitly to override the suffix-walking default:

```ini
# /etc/krb5.conf
[capaths]
    EXAMPLE.COM = {
        PARTNER.COM = .
    }
    PARTNER.COM = {
        EXAMPLE.COM = .
    }
```

Without `capaths`, MIT Kerberos walks the realm-name hierarchy by suffix (e.g., `DEV.EU.EXAMPLE.COM` → `EU.EXAMPLE.COM` → `EXAMPLE.COM`), which can be wrong if the actual trust path is different.

## GSS-API: The Programmatic Surface

Kerberos is rarely used directly via ASN.1 messages. Application code goes through GSS-API (RFC 4121), which wraps AP-REQ/AP-REP into a token format that can be sent over any transport. A minimal mutual-auth exchange using `python-gssapi`:

```python
import gssapi

# Client: build a SecurityContext for the target service principal.
service_name = gssapi.Name(
    'host/web.example.com@EXAMPLE.COM',
    name_type=gssapi.NameType.kerberos_principal,
)
ctx = gssapi.SecurityContext(
    name=service_name,
    flags=[gssapi.RequirementFlag.mutual_authentication],
)

# step() with no input returns the AP-REQ token to send to the server.
ap_req_token = ctx.step()  # bytes: contains the service ticket + authenticator

# Server: accept the AP-REQ, return an AP-REP for mutual auth if requested.
server_creds = gssapi.Credentials(usage='accept')
server_ctx = gssapi.SecurityContext(creds=server_creds)
ap_rep_token = server_ctx.step(ap_req_token)

# Client: consume the AP-REP, completing mutual authentication.
ctx.step(ap_rep_token)
assert ctx.complete, "mutual authentication failed"
print("Server authenticated client:", server_ctx.initiator_name)
```

The `ap_req_token` is the wire format that carries the Kerberos AP-REQ to the server. The server's `ap_rep_token` (if non-empty) proves the server holds the service's long-term key. Real applications wrap this in a transport protocol: SSH (GSSAPIAuthentication), HTTP Negotiate, or RPCSEC_GSS in NFSv4.

## Common Pitfalls

1. **Clock skew.** If the client's clock drifts more than `clockskew` (default 300s) from the KDC, authenticators are rejected. NTP is mandatory on Kerberos deployments. The KDC log will show `Preauthentication failed: Clock skew too great (37)`.

2. **Keytab permissions.** A service's keytab file contains the service's long-term key. If `chmod 644 /etc/krb5.keytab`, anyone on the host can impersonate the service. Use `chmod 600` and the service account owner.

3. **Forwardable TGT leakage.** A forwardable TGT can be delegated to a service, which can then impersonate the client elsewhere. This is Kerberos Constrained Delegation (KCD) when scoped, or unconstrained delegation (dangerous) when not. The `S4U2Proxy` extension (RFC 4120 section 3.5) constrains delegation to specific target SPNs.

4. **Roaming user keys.** If a user's password is changed at machine A, the long-term key changes. The user's existing TGT on machine B becomes invalid. AD tracks password version in `PwdLastSet`; the TGT's encrypted session key uses the user's current key.

5. **Long TGT lifetimes.** AD defaults to 10 hours, renewable to 7 days. A stolen TGT is valid for that entire window. The "Pass-the-Hash" attack vector in AD partially mitigates this — modern AD can require the AES key, not RC4, and the KDC enforces encryption type downgrade protection.

## Comparison to Other Auth Protocols

| Property | Kerberos | OAuth 2.0 + OIDC | mTLS |
|---|---|---|---|
| Trust model | Trusted third party (KDC) | Identity Provider (IdP) | CA-issued certs |
| Key type | Symmetric (AES) | Asymmetric (RS256/ES256) | Asymmetric (RSA/ECDSA) |
| Token type | Ticket (encrypted, opaque) | JWT (signed, transparent) | X.509 cert |
| Replay protection | Authenticator + replay cache | Nonce + state | TLS handshake nonce |
| Online validation | Per-ticket TGS call | Per-request IdP call (introspection) | Per-handshake OCSP |
| Lifetime | 10h (AD default) | 1h access token | Cert validity |
| Mutual auth | Built-in (AP-REP) | Token verification | Built-in |

## References

- [RFC 4120: The Kerberos Network Authentication Service (V5)](https://datatracker.ietf.org/doc/html/rfc4120)
- [RFC 4121: The Kerberos V5 GSS-API mechanism](https://datatracker.ietf.org/doc/html/rfc4121)
- [RFC 3961: Encryption and Checksum Specifications for Kerberos 5](https://datatracker.ietf.org/doc/html/rfc3961)
- [RFC 6806: Kerberos V5 Transited Path / Canonicalize](https://datatracker.ietf.org/doc/html/rfc6806)
- [RFC 8009: AES Encryption with HMAC-SHA-256 for Kerberos 5](https://datatracker.ietf.org/doc/html/rfc8009)
- [MIT Kerberos documentation](https://web.mit.edu/kerberos/krb5-latest/doc/)
- [MIT Kerberos project overview](https://web.mit.edu/kerberos/)
- [Microsoft: How the Kerberos V5 protocol works](https://learn.microsoft.com/en-us/windows-server/security/kerberos/how-the-kerberos-version-5-authentication-protocol-works)
- [Microsoft: Kerberos Constrained Delegation (S4U2Proxy)](https://learn.microsoft.com/en-us/windows-server/security/kerberos/kerberos-constrained-delegation-overview)
- [Heimdal Kerberos project](https://www.h5l.org/)
