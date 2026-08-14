# Mobile Security

## Table of Contents

- [Mobile-Specific Security Threats](#mobile-specific-security-threats)
- [Certificate Pinning](#certificate-pinning)
- [Secure Storage](#secure-storage)
- [App Hardening](#app-hardening)
- [Runtime Protection](#runtime-protection)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Mobile-Specific Security Threats

Mobile apps face unique threat vectors compared to web applications:

| Threat | Description | Platform Impact |
|--------|-------------|-----------------|
| **Reverse engineering** | Decompiling APK/IPA to extract logic, API keys, hardcoded secrets | Both |
| **Man-in-the-middle (MITM)** | Intercepting HTTPS traffic via proxy tools (Charles Proxy, Burp Suite) | Both |
| **Insecure data storage** | Sensitive data stored in SharedPreferences/UserDefaults, SQLite without encryption, logs | Both |
| **Jailbreak/Root detection bypass** | Running on compromised devices with elevated privileges | iOS (jailbreak), Android (root) |
| **Clipboard sniffing** | Reading clipboard contents (passwords, OTPs) from other apps | Both |
| **Deep link hijacking** | Malicious apps registering URL schemes to intercept intents/deep links | Both |
| **Screen recording/capture** | Sensitive content visible in screenshots or screen recording | Both |
| **API abuse** | Reverse-engineered API endpoints called outside the app with elevated privileges | Both |
| **Overlay attacks** | Malicious app draws over your app to trick users (tapjacking) | Android primarily |
| **Backup extraction** | Full backup (iTunes/ADB) extracts app data including cached credentials | Both |

## Certificate Pinning

Certificate pinning protects against MITM attacks by ensuring the app only trusts
a specific certificate or public key, regardless of the device's trusted CA store.

### Pinning Strategies

| Strategy | Flexibility | Security | Rotation Effort |
|----------|-----------|----------|----------------|
| **Pin leaf certificate** | Low | High | High — rotate per cert |
| **Pin CA certificate** | High | Medium | Low — CA rotates for you |
| **Pin public key hash (SPKI)** | Medium | High | Medium — same key across cert renewals |

### Implementation

**iOS (URLSession):**
```swift
func urlSession(
    _ session: URLSession,
    didReceive challenge: URLAuthenticationChallenge,
    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
) {
    guard let serverTrust = challenge.protectionSpace.serverTrust,
          let serverCert = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
        completionHandler(.cancelAuthenticationChallenge, nil)
        return
    }
    let serverKey = SecCertificateCopyPublicKey(serverCert)!
    let serverKeyHash = SecKeyCopyExternalRepresentation(serverKey, nil)!
    // Compare against pinned hash
    if pinnedHashes.contains(serverKeyHash) {
        completionHandler(.useCredential, URLCredential(trust: serverTrust))
    } else {
        completionHandler(.cancelAuthenticationChallenge, nil)
    }
}
```

**Android (OkHttp CertificatePinner):**
```kotlin
val client = OkHttpClient.Builder()
    .certificatePinner(
        CertificatePinner.Builder()
            .add("api.example.com", "sha256/AAAAAAA...")
            .build()
    )
    .build()
```

### Bypass Prevention
- **Obfuscate** pinned hashes so they are harder to find in decompiled code.
- Use **multiple pins** (backup keys) to allow rotation without app updates.
- Monitor pinning failures server-side — unexpected failures may indicate
  active MITM or proxy usage.

## Secure Storage

### iOS: Keychain Services

Keychain is the only Apple-blessed location for sensitive data (tokens, passwords,
certificates). It encrypts data using the device's hardware key and optionally ties
access to biometric authentication.

```swift
let query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrAccount as String: "user_token",
    kSecValueData as String: tokenData,
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
]
SecItemAdd(query as CFDictionary, nil)
```

Key `kSecAttrAccessible` values:
- `kSecAttrAccessibleWhenUnlocked` — Available when device is unlocked.
- `kSecAttrAccessibleAfterFirstUnlock` — Available after first unlock post-reboot.
- `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` — No iCloud Keychain backup.

### Android: EncryptedSharedPreferences

Use Jetpack Security's `EncryptedSharedPreferences` for sensitive key-value storage.
It encrypts both keys and values using Android Keystore.

```kotlin
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()
val prefs = EncryptedSharedPreferences.create(
    context, "secret_prefs", masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)
```

### Storage Decision Matrix

| Data Type | iOS | Android |
|-----------|-----|--------|
| Auth tokens | Keychain | EncryptedSharedPreferences + Keystore |
| API keys (non-secret) | Info.plist (obfuscated) | BuildConfig / resources |
| Biometric keys | Secure Enclave (via SecAccessControl) | Android Keystore (biometric auth) |
| User preferences (non-sensitive) | UserDefaults | SharedPreferences |
| Database | Core Data + NSFileProtectionComplete | SQLCipher (encrypted SQLite) |

## App Hardening

1. **Code obfuscation** — ProGuard/R8 (Android) strips unused code and renames
   classes/methods. Swift is harder to obfuscate; use compilation optimization
   and string encryption.
2. **Remove debug symbols** — Release builds should never include `DWARF`/`dSYM`
   (iOS) or debug info (Android). Ship symbols to crash reporting services separately.
3. **Disable logging in production** — Strip `NSLog`/`Log.d` statements or use
   compile-time flags (`#if DEBUG`). Leaked logs expose PII and internal logic.
4. **Enable App Transport Security (ATS)** — Enforce TLS 1.2+ on all connections.
   Only disable for specific domains with `NSExceptionDomains`.
5. **Screenshot/screen recording prevention** — `UIScreen.main.captureDisable` (iOS)
   or `FLAG_SECURE` (Android).
6. **Root/jailbreak detection** — Check for su binary, Cydia substrate, or
   sandbox integrity. Detect but don't block — degrade functionality and report.

## Runtime Protection

Runtime attacks modify the app's behavior after it is loaded into memory:

- **Dynamic instrumentation** — Frida, Cydia Substrate, or Xposed hook methods at
  runtime to bypass security checks, extract keys, or modify business logic.
- **Memory dumping** — Attackers read process memory to extract decrypted data or
  session tokens.
- **DLL/shared library injection** — Loading malicious code into the app's process.

### Mitigations

- **Anti-hooking** — Detect Frida server, check method pointer integrity,
  validate library loading.
- **Memory encryption** — Keep sensitive data encrypted in memory; decrypt only
  in registers during use (zeroize immediately after).
- **Integrity checks** — Verify the app's code signature at runtime using
  `SecCodeCopyValidity` (iOS) or `PackageManager.getPackageInfo` with
  `GET_SIGNATURES` (Android).
- **Third-party RASP** — Runtime Application Self-Protection tools (Promon,
  DexGuard, Arxan) provide commercial-grade obfuscation, anti-tampering, and
  anti-debugging.

---

## Interview Questions

1. **What is certificate pinning and why is it important for mobile apps?**
   Certificate pinning restricts which TLS certificates the app trusts to a specific set (by certificate, CA, or public key hash). This prevents MITM attacks via compromised CAs or proxy tools (Charles, Burp). Without pinning, an attacker on the same network can intercept all API traffic, including tokens and sensitive data.

2. **How does EncryptedSharedPreferences differ from regular SharedPreferences on Android?**
   EncryptedSharedPreferences uses the Android Keystore to encrypt both keys and values. Regular SharedPreferences stores data as XML in plain text on the filesystem. EncryptedSharedPreferences uses AES256-GCM for values and AES256-SIV for keys, making it safe for tokens and credentials. The master key is hardware-backed and never leaves the TEE/StrongBox.

3. **What is the Secure Enclave on iOS and what operations does it protect?**
   The Secure Enclave is a dedicated hardware coprocessor that performs cryptographic operations in isolation. It stores biometric templates, encryption keys, and payment credentials. Keys generated inside never leave the enclave. Access it via `SecAccessControlCreateWithFlags` and `SecKeyCreateRandomKey` with `kSecAttrTokenIDSecureEnclave`. It's the foundation for Face ID, Touch ID, and Apple Pay.

4. **How would you detect a rooted/jailbroken device?**
   iOS: Check for Cydia substrate (`dyld` image check), sandbox path modifications, ability to write to `/private` directories. Android: Check for `su` binary, SuperUser.apk, Magisk, `ro.debuggable` system property, or test if the app can write to `/system`. Best practice: detect and report to backend; degrade functionality rather than crash or block, as sophisticated users can bypass detection.

5. **What is the difference between code obfuscation and encryption?**
   Obfuscation transforms code to make reverse engineering harder without changing behavior — renaming symbols, control flow flattening, string encryption. Encryption transforms data into an unreadable form that requires a key to decrypt. Obfuscation is for protecting logic; encryption is for protecting data at rest or in transit.

6. **How would you secure sensitive API keys in a mobile app?**
   No mobile app can fully protect a hardcoded secret from a determined attacker. Best practices: (1) Don't store secrets in the app if possible — use a backend proxy. (2) If required (e.g., third-party SDK keys), use obfuscation, compile-time injection, and server-side validation. (3) For auth tokens, store in Keychain/EncryptedSharedPreferences. (4) Consider app attestation (iOS DeviceCheck, Android Play Integrity API) to verify the app's integrity with your backend.

## References

- [OWASP Mobile Security Testing Guide](https://owasp.org/www-project-mobile-security-testing-guide/)
- [Apple Secure Enclave](https://developer.apple.com/documentation/security/certificate_key_and_trust_services/keys/protecting_keys_with_the_secure_enclave)
- [Android Jetpack Security](https://developer.android.com/topic/security/data)
- [Apple Keychain Services](https://developer.apple.com/documentation/security/keychain_services)
- [OWASP Mobile Top 10](https://owasp.org/www-project-mobile-top-10/)