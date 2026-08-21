# Mobile Security Deep Dive: Jailbreak/Root Detection, App Attestation, Code Signing

## Table of Contents

- [iOS Jailbreak Types](#ios-jailbreak-types)
- [Jailbreak Detection Techniques](#jailbreak-detection-techniques)
- [Android Root Detection](#android-root-detection)
- [SafetyNet and Play Integrity API](#safetynet-and-play-integrity-api)
- [iOS App Attest and DeviceCheck](#ios-app-attest-and-devicecheck)
- [Code Signing](#code-signing)
- [Putting It Together: Defense in Depth](#putting-it-together-defense-in-depth)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## iOS Jailbreak Types

A jailbreak exploits a kernel vulnerability to remount the root filesystem (`/`) read-write
and inject unauthorised code (typically the Cydia package manager). They are categorised by
how persistent the exploit is across reboots:

| Type | Boot signature | Reboot impact | Example exploits / tools |
|------|----------------|---------------|--------------------------|
| **Untethered**  | Exploit persists; reboots stay jailbroken on their own | Stays jailbroken | old `limera1n`, `absinthe` (iOS 4-5) |
| **Tethered**    | Device must be plugged into a host running the exploit each boot | Recovery mode (no boot) otherwise | `redsn0w` tethered mode |
| **Semi-untethered** | Boots normally; jailbreak functions re-enabled by re-running an app on device | Stays unjailbroken until app re-run | `checkra1n` (semi-tethered on A11), `palera1n` |
| **Semi-tethered** | Boots normally; jailbreak functions re-enabled by plugging into host | Stays unjailbroken until host run | `palera1n` (semi-tethered mode) |

Modern jailbreaks (Taurine, Dopamine, palera1n) are **semi-untethered**: they survive an
unplugged reboot but require re-running a signed app to re-inject. This matters because
detection techniques that check "is `cydia` mounted at `/`?" may pass on a freshly
rebooted semi-untethered device.

## Jailbreak Detection Techniques

A robust detector combines multiple signals; no single check is reliable because
jailbreak bypass tools (e.g. `A-Bypass`, `Shadow` tweak) hook `stat`, `fopen`, and
`dlopen` to return spoofed results.

### 1. File existence check (the weakest)

```swift
import Foundation

private let suspiciousPaths: [String] = [
    "/Applications/Cydia.app",
    "/Applications/Sileo.app",
    "/Library/MobileSubstrate/MobileSubstrate.dylib",
    "/bin/bash",
    "/usr/sbin/sshd",
    "/etc/apt",
    "/private/var/lib/apt",          // legacy apt path
    "/usr/sbin/sshd", "/usr/libexec/sftp-server",
    "/usr/sbin/sshd", "/var/cache/apt",
    "/var/lib/cydia", "/private/var/lib/apt"
]

func isJailbrokenByFileCheck() -> Bool {
    return suspiciousPaths.contains { FileManager.default.fileExists(atPath: $0) }
}
```

### 2. Sandbox check

iOS apps are sandboxed; on a stock device `fopen("/private/...", "w")` must fail. A
jailbroken device mounts `/` read-write, so writes to system paths succeed:

```swift
func isJailbrokenBySandbox() -> Bool {
    let testPath = "/private/jailbreak_test_\(UUID().uuidString)"
    let result = "test".write(toFile: testPath, atomically: true, encoding: .utf8)
    try? FileManager.default.removeItem(atPath: testPath)
    return result  // true on jailbroken
}
```

### 3. dyld check (most reliable if bypass tools don't hook it)

Every image loaded into the process is enumerable via `<dlfcn.h>`:

```swift
import Darwin

func isJailbrokenByDyld() -> Bool {
    let suspiciousDylibs: Set<String> = [
        "MobileSubstrate", "Substitute", "substrate",
        "libhooker", "ellekit", "TweakInject", "CydiaSubstrate"
    ]
    for i in 0..<_dyld_image_count() {
        let name = String(cString: _dyld_get_image_name(i))
        if suspiciousDylibs.contains(where: { name.lowercased().contains($0.lowercased()) }) {
            return true
        }
    }
    return false
}
```

`MobileSubstrate`/`Substitute`/`libhooker` are the runtime injection frameworks used by
*every* jailbreak to load tweaks. If one of these is in your image list, you are almost
certainly running on a jailbroken device.

### 4. URL scheme check

If your app declares a `cydia://` URL scheme handler, calling `canOpenURL` with a known
Cydia-only scheme returns true only on jailbroken devices:

```swift
func isJailbrokenByURLScheme() -> Bool {
    return UIApplication.shared.canOpenURL(URL(string: "cydia://package/com.example")!)
}
```

Note: This requires listing `cydia` in `LSApplicationQueriesSchemes` in `Info.plist`, which
itself is a tell — sophisticated jailbreakers will know.

## Android Root Detection

Android root detection is more multi-faceted because root can be installed in three ways:

1. **Magisk** (most popular): systemless root that patches the boot image and intercepts
   `mount`/`access` syscalls via MagiskHide/Zygisk to hide from apps.
2. **su binary**: legacy root that drops `/system/bin/su`.
3. **Custom ROMs**: system partition replaced; usually not "rooted" but `/system` is
   untrusted.

```kotlin
object RootDetector {
    private val SU_PATHS = arrayOf(
        "/system/bin/su", "/system/xbin/su", "/sbin/su",
        "/system/sd/xbin/su", "/system/bin/failsafe/su",
        "/data/local/xbin/su", "/data/local/bin/su", "/data/local/su",
        "/su/bin/su", "/magisk/.core/bin/su", "/system/usr/we-need-root/su"
    )

    private val SUSPICIOUS_PACKAGES = setOf(
        "com.topjohnwu.magisk", "eu.chainfire.supersu",
        "com.koushikdutta.superuser", "com.thirdparty.superuser",
        "com.noshufou.android.su", "com.yellowes.su",
        "com.kingouser.com", "com.kingo.root", "com.smedialink.oneclickroot"
    )

    private val SUSPICIOUS_PROPS = mapOf(
        "ro.debuggable" to "1",
        "ro.secure" to "0",
        "service.adb.root" to "1"
    )

    fun isRooted(context: Context): Boolean {
        if (SU_PATHS.any { File(it).exists() }) return true
        val pm = context.packageManager
        if (SUSPICIOUS_PACKAGES.any { runCatching {
            pm.getPackageInfo(it, 0); true }.getOrDefault(false) }) return true
        if (SUSPICIOUS_PROPS.any { (k, v) -> System.getProperty(k) == v }) return true
        if (isBusyboxPresent()) return true
        return false
    }

    private fun isBusyboxPresent(): Boolean =
        listOf("/system/bin/busybox", "/system/xbin/busybox",
               "/data/local/busybox", "/sbin/busybox").any { File(it).exists() }
}
```

**Magisk bypass (DenyList)** renames `su`, hides `/sbin/.magisk`, and intercepts
`access()`/`stat()` calls. So the file existence check above will likely return false on
Magisk-rooted devices with DenyList enabled for your package. This is why root detection
should be paired with **Play Integrity API** for high-assurance use cases.

## SafetyNet and Play Integrity API

Google's attestation services let a backend cryptographically verify that the calling app
is genuine, untouched, and running on a Google-certified (CTS-passing) device.

**SafetyNet Attestation API** is the older service. It returns a JWS (signed JWT) whose
payload includes:

- `ctsProfileMatch`: true if device passed Compatibility Test Suite (i.e. genuine
  Google-certified ROM).
- `basicIntegrity`: true if the device is not rooted and the binary is not tampered with
  (weaker than `ctsProfileMatch`).
- `nonce`: echoes the nonce you supplied to prevent replay.
- `evaluationType`: bitmap of hardware-backed vs basic attestation.

**Play Integrity API** is the replacement (Google recommends migrating). It splits the
signal into three finer-grained results:

| Verdict | What it asserts |
|---------|----------------|
| `MEETS_DEVICE_INTEGRITY` | Genuine Google-certified device (CTS-passing). |
| `MEETS_BASIC_INTEGRITY` | App is genuine, no root (weaker — may not be certified). |
| `MEETS_STRONG_INTEGRITY` | Recent hardware-backed verdict; protected by hardware Keymaster. |

Client side:

```kotlin
class IntegrityManager(private val context: Context) {
    suspend fun requestIntegrityToken(nonce: ByteArray): String {
        val manager: StandardIntegrityManager =
            IntegrityManagerFactory.createStandard(context).standardManager
        val prepared = manager.prepareIntegrityToken(
            StandardIntegrityManager.PrepareIntegrityTokenRequest.builder()
                .setCloudProjectNumber(YOUR_CLOUD_PROJECT_NUMBER)
                .build()
        ).await()
        return manager.requestIntegrityToken(
            StandardIntegrityManager.RequestIntegrityTokenRequest.builder()
                .setNonce(nonce.encodeBase64())
                .build()
        ).await().tokenResponse()
    }
}
```

The token is opaque. The backend sends it to Google's Play Integrity REST endpoint with
the cloud project number, gets back a signed envelope with `deviceRecognitionVerdict`,
`appRecognitionVerdict`, and the echoed nonce.

**Crucial pattern:** the nonce MUST be generated on the backend, sent to the client with
the request that needs protection, included in the Integrity token, and then echoed back
during backend verification. Without this, an attacker can precompute a token from a
genuine device and replay it against your server from a rooted device.

## iOS App Attest and DeviceCheck

Apple offers two complementary services for server-side verification of an app instance:

**DeviceCheck** (`DCDevice`) — answers "have I seen this device before?" Useful for
per-device rate limiting (e.g. limit free trial abuse). Two bits of state per device.

```swift
import DeviceCheck

func pushDeviceToken() {
    DCDevice.current.isSupported ? fetchAndSendToken() : handleUnsupported()
}

func fetchAndSendToken() {
    DCDevice.current.generateToken { token, error in
        guard let token = token else { return }
        let payload: [String: Any] = [
            "device_token": token.base64EncodedString(),
            "app_action": "trial_started",
            "timestamp": Int(Date().timeIntervalSince1970)
        ]
        APIClient.post("/devicecheck", body: payload)  // backend queries Apple
    }
}
```

**App Attest** (`DCAppAttestService`) — per-asset cryptographic attestation. Apple
generates a per-device, per-app CryptographicKey (in the Secure Enclave on supported
hardware). The app requests Apple to attest the public key; Apple returns a CBOR-encoded
attestation object that the backend verifies against the Apple App Attest Environment root
CA. The backend then derives assertions for every subsequent sensitive request.

```swift
import DeviceCheck

class AppAttest {
    let service = DCAppAttestService.shared
    private var storedKey: String?

    func ensureKey(completion: @escaping (Result<String, Error>) -> Void) {
        service.generateKey { [weak self] keyId, error in
            guard let keyId = keyId, error == nil else {
                completion(.failure(error!)); return
            }
            self?.storedKey = keyId
            self?.service.attestKey(keyId) { attestation, error in
                guard let attestation = attestation else {
                    completion(.failure(error!)); return
                }
                let payload = [
                    "key_id": keyId,
                    "attestation_b64": attestation.base64EncodedString()
                ] as [String: String]
                APIClient.post("/attest", body: payload) { _ in
                    completion(.success(keyId))
                }
            }
        }
    }

    func signChallenge(_ challenge: Data, completion: @escaping (Data?) -> Void) {
        guard let keyId = storedKey else { completion(nil); return }
        let hashed = Data(SHA256.hash(data: challenge))
        service.generateAssertion(keyId, clientDataHash: hashed) { assertion, _ in
            completion(assertion)
        }
    }
}
```

The backend flow for an Attestation:

1. Receive attestation object, decode CBOR per WebAuthn's format.
2. Verify the attestation statement's signature using Apple App Attest root cert.
3. Validate the `aaguid` is Apple's
   (`a5d5fc5b-4a24-49f4-aad2-862d28731da9` for Apple App Attest).
4. Extract the credential public key; store it keyed by the keyId.
5. For subsequent sensitive requests, generate a server-side nonce, send it to the app, and
   require an assertion (signature) over the nonce + request hash.

## Code Signing

### iOS provisioning + entitlements

Every iOS app binary must be signed by a certificate trusted by the device. In production
that is your distribution certificate (issued by Apple's iPhone Distribution CA). The
signature is embedded as an embedded signature using the CMS (RFC 5652) format with a chain
back to the Apple Root CA. The structure is:

```
Mach-O executable
├── LC_CODE_LOAD_COMMAND (points to embedded signature)
└── Embedded signature blob
    ├── CodeDirectory (CDHash, SHA256 of every page of the binary)
    ├── CMS signed data (certificate chain + signature)
    └── Entitlements plist (Keychain access groups, push env, etc.)
```

Entitlements unlock TCC-protected capabilities — for example, you cannot read contacts
without `com.apple.security.personalinformation.contacts` and the matching provisioning
profile. The provisioning profile (`.mobileprovision`) is a CMS-signed plist from Apple
that ties together:

- A list of allowed app IDs (the wildcards or explicit bundle IDs).
- A set of developer certificates (their public key hashes).
- A list of enabled entitlements and services (App Groups, iCloud containers,
  Push Notification environment, etc.).

The device validates at install time: signature chains to a trusted root, the binary's
CDHash matches what was signed, the entitlements appear in the provisioning profile, and
the developer cert hash is listed.

### Android APK Signature v2/v3

Android's APK signing has evolved through three schemes:

| Scheme | Scope | Validation | Notes |
|--------|-------|------------|-------|
| v1 (JAR) | Each file | Per-entry digest in META-INF/*.SF/MF | Slow; bypassable; required pre-Android 7 |
| v2 (APK Signature) | Whole file | Merkle-style hash over APK ZIP sections | Introduced in Android 7; protects ZIP central directory too |
| v3 (APK Signature v3) | Whole file + key rotation | Adds key-rotation lineage | Introduced in Android 9; allows rotating signing keys |
| v4 (install-time streaming) | Companion file | `.idsig` next to APK | Required for `adb install --incremental` |

A v2/v3 signature covers the APK bytes excluding the signing block itself. The signing
block sits between the end of the central directory and the end of central directory
record. The signing block contains:

- A magic value (`APK Sig Block 42`).
- One or more signers, each with `signed_data`, `signatures`, and `public_key`.
- `signed_data` lists digests of three APK regions (contents of entries before central
  directory, central directory, end of central directory).

A v3 block additionally carries a lineage array showing the chain of prior signing keys
and a `proof_of_rotation` signature that allows the OS to verify the new key is a
legitimate successor of the old key. This lets you migrate from a compromised key without
breaking update continuity.

Sign with v2+v3:

```bash
apksigner sign \
  --ks release.jks \
  --ks-pass pass:$KS_PASS \
  --key-pass pass:$KEY_PASS \
  --v1-signing-enabled false \
  --v2-signing-enabled true \
  --v3-signing-enabled true \
  app-release-unsigned.apk

apksigner verify --print-certs app-release-unsigned.apk
```

For Play Store distribution, Google Play App Signing re-signs with Google's key; you
upload a single APK or AAB signed with your upload key, and Play re-signs with their
release key for distribution. You retain your upload key for authentication.

---

## Putting It Together: Defense in Depth

A production security strategy combines multiple layers so that defeating any single layer
does not compromise the whole system:

```
   ┌────────────────────────────────────────────────────┐
   │ Server-side request protection                     │
   │   • nonce + App Attest assertion / Play Integrity │
   │   • per-device rate limiting via DeviceCheck       │
   └──────────────┬─────────────────────────────────────┘
                  │
   ┌──────────────▼─────────────────────────────────────┐
   │ Client-side runtime checks (degrade functionality) │
   │   • jailbreak/root signals → restrict              │
   │   • debugger detection (ptrace anti-debug)         │
   │   • code obfuscation (ProGuard/R8, Alliirium)      │
   └──────────────┬─────────────────────────────────────┘
                  │
   ┌──────────────▼─────────────────────────────────────┐
   │ Code signing (install-time integrity)              │
   │   • Apple distribution cert + provisioning profile │
   │   • Android APK Signature v2+v3, Play re-signing   │
   └──────────────┬─────────────────────────────────────┘
                  │
   ┌──────────────▼─────────────────────────────────────┐
   │ OS hardening (vendor-provided)                     │
   │   • iOS Sandbox, Secure Enclave, PAC, Pointer Auth  │
   │   • Android Keystore, TEE/StrongBox, A/B seandroid │
   └────────────────────────────────────────────────────┘
```

A good rule: **detect and degrade, never crash.** Crashing on jailbreak detection tells
the attacker exactly which check failed. Degrading silently (no in-app purchases, no
sensitive data fetch) forces the attacker to reverse the whole app to even understand
which functionality is restricted.

---

## Interview Questions

1. **What are the four types of iOS jailbreaks and which survives a reboot?**
   Untethered survives reboot. Tethered fails to boot without host. Semi-untethered boots
   but requires re-running an on-device app to re-enable the jailbreak. Semi-tethered
   requires re-running a host tool. Modern jailbreaks (Dopamine, palera1n) are
   semi-untethered.

2. **Why is the dyld image check more reliable than file existence checks?**
   Bypass tools like Shadow hook `stat`, `fopen`, and `access` to return ENOENT for
   suspicious paths. They do not typically hook `_dyld_image_count` /
   `_dyld_get_image_name` because those are in-process introspection APIs. So if
   `MobileSubstrate.dylib` appears in your image list, the device is jailbroken even if
   every file check returns false.

3. **How does Magisk's DenyList bypass root detection, and how do you defend?**
   Magisk's Zygisk hooks `access()`/`stat()`/`execve()` and selectively returns
   `ENOENT`/`EPERM` for paths matching your package's DenyList. It also unmounts
   `/sbin/.magisk` and renames `su`. The defense is the **Play Integrity API**: the
   attestation is generated by Play Services on the device and signed by Google's cloud
   using hardware-backed keys; Magisk cannot forge a valid `MEETS_DEVICE_INTEGRITY` verdict
   without a TEE/StrongBox bypass.

4. **What is the difference between App Attest and DeviceCheck?**
   DeviceCheck is a per-device two-bit "have I seen you?" signal — good for trial abuse
   rate limiting. App Attest is per-app-instance, per-key cryptographic attestation: each
   app instance generates its own Secure Enclave-backed keypair, Apple attests it, and
   every subsequent sensitive request carries an assertion signed by that key over a
   server-supplied nonce. App Attest is strictly stronger but more complex to integrate.

5. **Why does APK Signature v2 protect better than v1 (JAR signing)?**
   v1 signs each file inside the ZIP independently, with the metadata stored as files in
   `META-INF`. A v1 attacker can add an unsigned file to the APK and have it loaded,
   because only signed files are verified. v2 hashes the entire APK byte range (entries,
   central directory, and end of central directory), so any modification invalidates the
   signature. v3 additionally supports key rotation, which v1/v2 cannot.

6. **How does iOS code signing work end-to-end?**
   Apple issues you a distribution cert tied to your developer account. Xcode signs the
   Mach-O, producing a CodeDirectory (SHA256 of every 4KB page) plus an embedded CMS
   signature over that directory, with your certificate's chain. Your provisioning profile
   (also CMS-signed by Apple) lists your bundle ID, allowed entitlements, and the hash of
   your certificate. At install time, the device verifies: signature chains to Apple root,
   CDHash matches signed bytes, entitlements are in the profile, and the cert hash is
   listed.

---

## References

- [Apple Developer — App Attest](https://developer.apple.com/documentation/devicecheck/appattest)
- [Apple Developer — DeviceCheck API](https://developer.apple.com/documentation/devicecheck)
- [Apple Platform Security Guide — Code Signing](https://support.apple.com/guide/security/sec1258564c4/web)
- [Apple Platform Security Guide — Secure Enclave](https://support.apple.com/guide/security/sec59b0b31web/web)
- [Google Play Integrity API](https://developer.android.com/google/play/integrity)
- [Google Play — SafetyNet Attestation API (deprecated)](https://developer.android.com/training/safetynet/attestation)
- [Android — APK Signature Scheme v2/v3](https://source.android.com/security/apksigning/v2)
- [OWASP MSTG — iOS and Android testing guides](https://owasp.org/www-project-mobile-security-testing-guide/)
- [OWASP MASVS (Mobile App Security Verification Standard)](https://mobile-security.gitbook.io/masvs/)
- [RFC 5652 — Cryptographic Message Syntax (CMS)](https://www.rfc-editor.org/rfc/rfc5652)
- [Magisk — official repository and docs](https://github.com/topjohnwu/Magisk)
