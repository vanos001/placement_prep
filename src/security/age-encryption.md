# age (Actually Good Encryption)

`age` is a file-encryption tool and format designed by Filippo Valsorda (formerly on the Go crypto team at Google, on the Python Cryptographic Authority board) and first released in 2019. The full name is a backronym: "Actually Good Encryption." The motivation, laid out in the project's design notes, is that GnuPG has a 30-year-old security posture, a configuration surface in the hundreds of options, a key format that mixes signing and encryption keys, and a CLI that is hostile to scripting. `age` aims to be the `git` of file encryption: small, opinionated, hard to misuse, with a stable wire format and no knobs.

## The Wire Format

An age file begins with a textual header listing one stanza per recipient, followed by a body that is the encrypted payload. The format is line-oriented for the header, then a binary stream-cipher body:

```text
age-encryption.org/v1
-> X25519 <ephemeral-public> <wrapped-file-key>
-> ssh-ed25519 <fingerprint> <wrapped-file-key>
-> ssh-rsa <fingerprint> <wrapped-file-key>
-> scrypt <salt> <wrapped-file-key>
--- <header-MAC>
<stream of ChaCha20-Poly1305 chunks, up to 64 KiB each>
```

The header is parseable by `awk` if necessary. The `---` line terminates the header; the bytes after the `\n` following it are the body. The MAC is an HMAC-SHA-256 over the header (everything before `---`), keyed with the file key — any tampering with the stanzas makes the MAC check fail before any decryption starts.

The body uses a streaming AEAD: each 64 KiB chunk has its own Poly1305 tag, with a "last chunk" flag in the nonce that distinguishes the final chunk from intermediate ones, so truncation is detected at decryption time. This is the same streaming-AEAD pattern used in TLS 1.3 record-layer chunking.

## The Crypto

Each stanza is one recipient. age supports these recipient types:

| Recipient type | Key exchange | Spec |
|---|---|---|
| `X25519` | ECDH on Curve25519 with HKDF-SHA256 | RFC 7748, RFC 5869 |
| `ssh-ed25519` | Ed25519 converted to X25519, then ECDH | RFC 8032 |
| `ssh-rsa` | RSA-OAEP with SHA-256 | RFC 8017 |
| `scrypt` | Password-based, scrypt KDF | RFC 7914 |
| `ssh-sk` (FIDO/U2F) | Ed25519 with hardware attestation | FIDO2 |

The core flow per X25519 recipient:

1. Generate an ephemeral X25519 keypair `(e, E)`.
2. Compute `shared = X25519(e, R)` where `R` is the recipient's X25519 public key.
3. Derive `wrap_key = HKDF-SHA256(salt = "age-encryption.org/v1/X25519", ikm = E || R, info = "")`.
4. Wrap the random 16-byte file key `F`: `share = ChaCha20-Poly1305(key = wrap_key, nonce = 0, plaintext = F)`.
5. The stanza stores `(E, share)`.

Any recipient that holds the private key `r` can recover `shared = X25519(r, E)`, derive `wrap_key`, decrypt `F`, and proceed to body decryption. The same `F` is wrapped once per recipient — multi-recipient files just have multiple stanzas, all of which decrypt to the same `F`.

The conversion from Ed25519 to X25519 is one subtle point: an Ed25519 secret scalar is the SHA-512 hash of the secret seed, clamped per RFC 7748 §5; the corresponding X25519 public key is `scalbase_mult(clamped_hash)` on Curve25519. This map is well-defined and unambiguous — the same Ed25519 key always produces the same X25519 key. SSH `ssh-ed25519` keys are accepted directly because the conversion is deterministic.

## SSH Key Recipients

The single most useful feature of age is that it reuses SSH public keys as recipients:

```bash
# Encrypt a file for a host's SSH key
age -R /etc/ssh/ssh_host_ed25519_key.pub -o backup.tar.gz.age backup.tar.gz

# Decrypt on the host
age -d -i /etc/ssh/ssh_host_ed25519_key backup.tar.gz.age > backup.tar.gz
```

No key generation, no keyserver, no PGP keyring. Every machine that has SSH has an `age` recipient available — the same key that grants shell access also decrypts secrets for that host. This collapses two key infrastructures into one.

The recipient format for an SSH key is the SSH wire-format public key (RFC 4251 §6 + RFC 4252 §6.6). age reads the file, identifies the key type (`ssh-ed25519`, `ssh-rsa`, `ecdsa-sha2-*`), and produces the appropriate stanza. For `ssh-ed25519`, this means converting the Ed25519 public key to X25519 and running the X25519 flow above.

## GitHub Key Discovery

GitHub publishes every user's public SSH keys at a stable URL:

```bash
$ curl -sL https://github.com/octocat.keys
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEVk2PmT8i... cardno:23 487
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ... ...
```

age's `-R` flag accepts a file path; a common pattern is to encrypt to "all of GitHub user X's SSH keys":

```bash
# Encrypt to all of octocat's GitHub keys
age -R <(curl -sL https://github.com/octocat.keys) -o secret.age secret.txt
```

The `rage` (Rust implementation of age) tool supports this directly:

```bash
rage -e -R github.com/octocat -o secret.age secret.txt
```

This is a building block for "encrypt secrets to the user, not the server" patterns in CI: a CI job can encrypt an artifact to a developer's GitHub SSH key without the developer ever publishing an age-specific public key.

The trust model: GitHub's HTTPS API is the source of truth for "what keys does user X have." A MITM could substitute keys, but TLS protects the API call. A compromised GitHub account means a compromised recipient list — same as any keyserver model. For high-sensitivity deployments, pin a specific key fingerprint rather than resolving a username to keys.

## CLI Idioms

age's CLI is deliberately tiny. The complete public surface is:

```bash
age -r <recipient> -o <output> <input>      # encrypt
age -d -i <identity> <input>                 # decrypt
age-keygen -o key.txt                        # generate identity
age-keygen -y > recipient.txt                # derive recipient from identity
```

That is the entire CLI. There is no `--armor`, no `--cipher-algo`, no `--default-preference-list` — the cipher, the cipher mode, the key size, and the encoding are fixed by the spec.

Identities are plain text files:

```text
# created: 2025-08-01T10:00:00Z
# public key: age1q...y4a
AGE-SECRET-KEY-1QZ...3FP
```

The `age1q...` prefix is the public key, bech32-encoded per BIP-173; the `AGE-SECRET-KEY-1...` line is the secret scalar, also bech32. The bech32 encoding includes a checksum, so typos in public keys are caught at encryption time, not at decryption time when it is too late.

## Comparison to GPG

| Property | GPG | age |
|---|---|---|
| First release | 1991 (PGP) / 1999 (GnuPG) | 2019 (beta), 2021 (1.0) |
| Cipher negotiation | Yes (preference lists) | None (fixed: ChaCha20-Poly1305) |
| Key types | RSA, DSA, ElGamal, EdDSA, ECDH, subkeys | X25519, ssh-ed25519, ssh-rsa, scrypt |
| Key format | OpenPGP packet format (binary, complex) | Bech32 (text, trivial) |
| Web of trust | Yes (key signing parties) | None (use known keys) |
| Configuration options | Hundreds | Zero |
| Compression | Built-in (attack surface: ZIP quines, CVE-2019-13050) | None |
| ASCII armor | Optional (`--armor`) | None (use `age \| base64`) |
| Auditability | Hundreds of CVEs over 30 years | No reported crypto CVEs to date |
| Default key lifetime | Forever, manual rotation | Whatever you make it |

The GPG problems that motivated age:

1. **Malleable ciphertext.** GPG's CFB mode is unauthenticated; attackers can flip bits in the ciphertext to produce predictable plaintext changes. age's streaming AEAD rejects any modification.

2. **Compression side channels.** GPG compresses before encrypting; an attacker who can submit a chosen plaintext to a victim's GPG session can detect whether a target string is present in the victim's plaintext (the CRIME/BREACH pattern). age does not compress.

3. **Key server network.** GPG relies on SKS keyservers, which had a 2019 spam attack that left most keys unusable; the keyservers were never properly deprecated. age has no keyservers — discoverability is via GitHub SSH keys, DNS, or out-of-band channels.

4. **Configuration footguns.** GPG's `gpg.conf` allows the user to enable insecure ciphers (SHA-1, 3DES, CAST5); an attacker who can write to `~/.gnupg/gpg.conf` downgrades all encryption. age has no config file — every option is a CLI flag.

## Worked Example: Encrypting a Secret for Two Recipients

A common pattern: encrypt a deploy key for both a production host and a backup operator. age's multi-recipient syntax:

```bash
# Generate two age identities
age-keygen -o host.key    # public: age1q...host
age-keygen -o backup.key   # public: age1q...backup

# Encrypt to both
age -r age1q...host -r age1q...backup -o deploy.key.age deploy.key

# The file has two stanzas:
$ head -3 deploy.key.age
age-encryption.org/v1
-> X25519 k7Vr2Q0n...    <-- host's stanza
-> X25519 N3xJL...       <-- backup operator's stanza
```

Either party can decrypt; the file key is wrapped twice. The "encrypt once, decrypt by N-of-M" pattern requires explicit recipient enumeration, unlike Shamir secret sharing; for that, use `age` plus `ssss` or `shamir`.

A more advanced pattern: encrypt to an SSH key and an age recipient, so a CI worker (using the SSH key) and a human (using the age key) can both decrypt:

```bash
age -R host.pub -r age1q...operator -o config.age config.yaml
```

## Worked Example: Streaming Decryption

age's streaming design means decryption does not buffer the entire file:

```bash
# Encrypt a 50 GB backup
tar cf - /var/lib/postgres | age -r age1q...offsite -o backup.tar.age

# Decrypt and extract without buffering the whole thing
age -d -i offsite.key backup.tar.age | tar xf -
```

Each 64 KiB chunk is decrypted as it arrives. A truncated file fails at the truncation point with `error: failed to authenticate chunk 472`. The chunked design also means the streaming `age` tool consumes O(1) memory — you can encrypt a terabyte through a 64 MiB process.

## Operational Patterns

1. **Committing secrets to git.** A team can commit `secrets.age` (encrypted to all team members' age recipients listed in `recipients.txt`) and the corresponding `recipients.txt` to the repo. To rotate: re-encrypt with a new `recipients.txt` and commit. This is the pattern SOPS implements, but age alone works for the no-template case.

2. **Cross-machine backup.** Encrypt local files to a remote machine's SSH key, then push to S3/Backblaze with `rclone`. The remote machine's private SSH key never leaves its host; the backup is unreadable even if S3 is breached.

3. **Decrypting in CI.** Store the age identity as a CI secret. The CI job runs `age -d -i $AGE_IDENTITY secrets.age > secrets.json`. The identity file is short (~100 bytes) and base64-friendly for use as a CI secret variable.

## Common Pitfalls

1. **Committing the identity.** A `key.txt` file containing `AGE-SECRET-KEY-1...` accidentally committed to git is a permanent compromise. Use `.gitignore` and store identities in password managers or the OS keychain.

2. **Losing the identity.** Unlike GPG's revocation certificates, age has no recovery mechanism. The identity is the only way to decrypt; if lost, the ciphertexts are unrecoverable. Make offline backups of identity files.

3. **Treating `age` as an email signature tool.** age is only encryption — no signatures, no key management UI, no identity metadata. Use `minisign` or `sigstore` for signatures. The author explicitly rejects scope expansion to signatures.

4. **Using `scrypt` for shared-password encryption with a weak password.** The `scrypt` recipient uses scrypt (parameters tuned per spec) to derive a key from a passphrase; weak passphrases can be brute-forced. Use generated passwords from a password manager.

5. **Mixing identity formats.** An SSH private key (`id_ed25519`) and an age identity (`AGE-SECRET-KEY-1...`) are different files. age accepts both via `-i`, but mixing them up leads to "no identity matched any recipient" errors. Use age identities for new deployments; SSH keys are a convenience, not the default.

## References

- [age-encryption.org — the official specification (v1)](https://age-encryption.org/v1)
- [age GitHub repository (FiloSottile/age)](https://github.com/FiloSottile/age)
- [rage — the Rust implementation of age](https://github.com/str4d/rage)
- [Filippo Valsorda's blog (age author)](https://words.filippo.io/)
- [RFC 7748: X25519](https://datatracker.ietf.org/doc/html/rfc7748)
- [RFC 8439: ChaCha20-Poly1305 AEAD](https://datatracker.ietf.org/doc/html/rfc8439)
- [RFC 5869: HKDF](https://datatracker.ietf.org/doc/html/rfc5869)
- [RFC 7914: scrypt KDF](https://datatracker.ietf.org/doc/html/rfc7914)
- [RFC 8032: Ed25519](https://datatracker.ietf.org/doc/html/rfc8032)
- [RFC 8017: PKCS #1 v2.2 (RSA-OAEP)](https://datatracker.ietf.org/doc/html/rfc8017)
- [BIP-173: Bech32 (used for age public keys)](https://github.com/bitcoin/bips/blob/master/bip-0173.mediawiki)
- [GitHub REST API: User SSH keys](https://docs.github.com/en/rest/users/keys)
- [OpenSSH PROTOCOL.key format](https://github.com/openssh/openssh-portable/blob/master/PROTOCOL.key)
