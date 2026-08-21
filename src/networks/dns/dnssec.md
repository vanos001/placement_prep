# DNSSEC (DNS Security Extensions)

DNSSEC is a set of DNS extensions that provide cryptographic authentication and integrity for DNS responses. Standardized in RFCs 4033-4035 (2005), DNSSEC lets resolvers verify that a DNS response actually came from the zone's authoritative server and wasn't tampered with in transit. This page covers the cryptographic model, the chain of trust, the key rollover, and the production deployment state.

## The Problem DNSSEC Solves

DNS was designed in 1983 without security. Responses are unsigned; an attacker who can intercept or spoof DNS responses can redirect users to malicious servers (DNS spoofing / cache poisoning):

```text
1. User queries: example.com A
2. Attacker injects a forged response: example.com → 6.6.6.6 (attacker's IP)
3. The resolver caches this; the user connects to the attacker's server.
4. The attacker presents a fake "example.com" website.
```

DNSSEC addresses this by signing responses cryptographically. A resolver that has the zone's public key can verify the signature; forged responses are rejected.

## The Cryptographic Model

DNSSEC adds four new record types:

- **DNSKEY**: a public key (e.g., RSA, ECDSA, EdDSA).
- **RRSIG**: a signature over a set of records (e.g., the A records for example.com).
- **DS**: a "Delegation Signer" — a hash of a child zone's DNSKEY, signed by the parent zone.
- **NSEC / NSEC3**: "next secure" records for proving non-existence (a record doesn't exist).

### The Signing Process

```text
For each RRset (a set of records of the same type for the same name):
  example.com. IN A 1.2.3.4
  example.com. IN A 5.6.7.8
  
  The zone signs with its ZSK (Zone Signing Key):
    RRSIG: example.com. IN A { signature, signature-validity, signer=example.com, key_tag=12345 }
```

The ZSK signs all RRsets in the zone. The KSK (Key Signing Key) signs the DNSKEY RRset (including itself and the ZSK). The KSK's public key is published via the DS record in the parent zone.

### The Chain of Trust

```text
Root zone (.)
  KSK signs DNSKEY of root
  Root publishes DS records for TLDs (e.g., .com)
  
.com zone
  KSK signs DNSKEY of .com
  .com publishes DS records for registrants (e.g., example.com)
  
example.com zone
  KSK signs DNSKEY of example.com
  Publishes its records (A, MX, etc.)
```

A validating resolver:
1. Has a trust anchor for the root zone (the root KSK's public key).
2. Queries the root's DNSKEY → verifies with the trust anchor.
3. Queries the .com's DS (signed by root's ZSK) → verifies with root's DNSKEY.
4. Queries the .com's DNSKEY → matches the DS hash.
5. Queries example.com's DS (signed by .com's ZSK) → verifies.
6. Queries example.com's DNSKEY → matches the DS hash.
7. Queries example.com's A (signed by example.com's ZSK) → verifies.

If all verifications pass, the response is trusted. Any tampering breaks the chain.

## NSEC and NSEC3

For proving non-existence (a record doesn't exist):

### NSEC

```text
Query: nonexistent.example.com A
Response: NSEC:
  alpha.example.com → next.example.com
  Type: A, MX, TXT (but NOT nonexistent)
```

The NSEC record says "between alpha.example.com and next.example.com, there are no records" — proving `nonexistent.example.com` doesn't exist.

Vulnerability: zone walking. An attacker can enumerate all names in the zone by repeatedly querying for non-existent names and reading the NSEC records.

### NSEC3

NSEC3 hashes the names: instead of `alpha.example.com`, the record shows `abc123hash.example.com` (the SHA-1 hash of `alpha`). Zone walking becomes computationally expensive.

NSEC3 is the standard for production zones (RFC 5155).

## Key Rollover

DNSSEC keys must be rotated periodically (compromise, key strength erosion). The rollover process:

### ZSK Rollover (Pre-publish)

1. Generate a new ZSK; publish it in DNSKEY (don't use it for signing yet).
2. Wait for the TTL of the DNSKEY RRset to expire (so all resolvers see the new key).
3. Start signing new RRSIGs with the new ZSK (alongside the old, for a transition period).
4. Wait for RRSIG TTL.
5. Remove the old ZSK from DNSKEY.

### KSK Rollover (Double-DS)

1. Generate a new KSK; publish it in DNSKEY (alongside the old).
2. Submit the new KSK's DS to the parent zone (alongside the old DS).
3. Wait for propagation.
4. Remove the old KSK from DNSKEY.
5. Wait for propagation.
6. Submit a DS update to the parent (remove the old DS).

KSK rollover is more complex because it involves the parent zone (the registrar). Forgetting a step can leave the zone broken.

## Production Deployment State

As of 2024:
- The root zone is signed (since 2010).
- 159 of 1590 TLDs are signed (~10%).
- ~1% of .com domains have DNSSEC.

DNSSEC adoption has been slow due to:
- Complexity (key rollover, DS delegation, RRSIG validity).
- Cost (more queries, larger responses).
- DNSSEC hasn't been the attack vector it was expected to be (TLS provides most of the security people need).

Major DNS providers (Cloudflare, Google) provide DNSSEC validation in their resolvers; signed zones work transparently. Signing your own zone requires DNS provider support (Cloudflare, Route 53, etc.).

## Common Pitfalls

1. **Forgetting to update the DS record at the registrar.** If the KSK changes but the DS at the parent isn't updated, the chain breaks; resolvers reject the zone.

2. **Forgetting that RRSIGs expire.** RRSIGs have a validity window (default 30 days). If the zone isn't re-signed before expiration, responses become untrusted. Automate the re-signing.

3. **Forgetting that DNSSEC responses are larger.** With RRSIG records, a single A query can return 1-2 KB (vs. 50 bytes unsigned). This can cause DNS over UDP truncation, requiring fallback to TCP.

4. **Forgetting that NSEC records expose the zone.** A signed zone with NSEC can be enumerated. Use NSEC3 for hidden zones.

5. **Forgetting that DNSSEC doesn't encrypt.** DNSSEC provides integrity, not confidentiality. Queries and responses are still in plaintext (use DoH/DoT for encryption).

6. **Forgetting that DNSSEC requires time synchronization.** RRSIGs have validity windows based on the signer's clock; if the signer's clock is wrong, signatures may be invalid.

## Comparison to Other DNS Security Solutions

| Solution | What it provides | Limitations |
|----------|------------------|-------------|
| DNSSEC | Authentication, integrity | No confidentiality, complex deployment |
| DoH (DNS over HTTPS) | Confidentiality (encryption) | No authentication of responses |
| DoT (DNS over TLS) | Confidentiality | No authentication |
| DNSCrypt | Both (encryption + auth) | Not standardized; niche adoption |

DNSSEC complements DoH/DoT (which provide confidentiality). For full security, both are needed.

## References

- [RFC 4033: DNSSEC Introduction](https://datatracker.ietf.org/doc/html/rfc4033)
- [RFC 4034: DNSSEC Resource Records](https://datatracker.ietf.org/doc/html/rfc4034)
- [RFC 4035: DNSSEC Protocol Modifications](https://datatracker.ietf.org/doc/html/rfc4035)
- [RFC 5155: NSEC3](https://datatracker.ietf.org/doc/html/rfc5155)
- [ICANN: DNSSEC deployment](https://www.icann.org/dnssec)
- [Verisign: DNSSEC statistics](https://dnssec-stats.verisignlabs.com/)
- [LWN: DNSSEC overview (2020)](https://lwn.net/Articles/820133/)
