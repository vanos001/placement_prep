# Mobile Push Notifications: APNs and FCM Deep Dive

## Table of Contents

- [The Push Delivery Chain](#the-push-delivery-chain)
- [APNs (Apple Push Notification service)](#apns-apple-push-notification-service)
  - [Device Token Registration](#device-token-registration)
  - [APNs Protocol: Binary (Legacy) vs HTTP/2](#apns-protocol-binary-legacy-vs-http2)
  - [APNs Payload Structure](#apns-payload-structure)
  - [Silent Pushes (content-available)](#silent-pushes-content-available)
- [FCM (Firebase Cloud Messaging)](#fcm-firebase-cloud-messaging)
  - [FCM Protocols: XMPP (deprecated) vs HTTP v1](#fcm-protocols-xmpp-deprecated-vs-http-v1)
  - [Registration Token and Topic Messaging](#registration-token-and-topic-messaging)
  - [FCM Payload (notification vs data)](#fcm-payload-notification-vs-data)
- [APNs vs FCM Comparison](#apns-vs-fcm-comparison)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## The Push Delivery Chain

A push notification does not travel directly from your server to a device. The chain on
both iOS and Android looks like this:

```
   Your App (on device)            Your Provider Server           APNs / FCM               Device
   ─────────────────────           ────────────────────           ──────────               ──────
        │                                  │                          │                      │
        │  1. registerForRemote            │                          │                      │
        │ ────────────────────────────────▶│                          │                      │
        │  (obtain device token)           │                          │                      │
        │                                  │  2. POST /3/device/      │                      │
        │                                  │     {token, payload}     │                      │
        │                                  │ ────────────────────────▶│                      │
        │                                  │                          │  3. push to device   │
        │                                  │                          │ ────────────────────▶│
        │                                  │                          │                      │ 4. app wakes,
        │                                  │                          │                      │    handler fires
```

1. **App → Provider.** The app calls `registerForRemoteNotifications()` (iOS) or
   `FirebaseMessaging.getInstance().token` (Android). The OS itself talks to APNs/FCM to
   get a device token, then hands it back to the app. The app forwards this token to its
   own provider server over HTTPS.
2. **Provider → APNs/FCM.** The provider holds the token and decides *when* and *what* to
   push. It opens a connection (HTTP/2 for APNs, HTTPS for FCM) and sends a request per
   token, possibly batching in FCM.
3. **APNs/FCM → Device.** The platform's push infrastructure maintains a long-lived
   connection (APNs uses HTTP/2 with multiplexed streams; FCM uses an XMPP-like persistent
   socket internally). It pushes the payload to the device.
4. **Device → App.** The OS receives it, wakes the app if needed, and calls the app's
   delegate: `UNUserNotificationCenter.delegate.userNotificationCenter(_:didReceive:withCompletionHandler:)`
   (iOS) or `FirebaseMessagingService.onMessageReceived` (Android).

A critical implication: **the provider never speaks directly to the device.** APNs/FCM are
the only brokers, which is why both platforms enforce a single push service per OS —
without it, every app would need a permanently open socket, which destroys battery life.

---

## APNs (Apple Push Notification service)

### Device Token Registration

The device token is *not* a static identifier. It can change when:

- The user restores from backup.
- The user reinstalls the OS.
- A new device is restored from a backup of a different device.

Apple therefore recommends re-registering on every launch:

```swift
import UIKit
import UserNotifications

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .badge, .sound]) { granted, _ in
            DispatchQueue.main.async {
                if granted { UIApplication.shared.registerForRemoteNotifications() }
            }
        }
        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let tokenString = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        // Send tokenString to provider server over HTTPS.
        APIClient.registerToken(tokenString)
    }

    func application(_ application: UIApplication,
                     didFailToRegisterForRemoteNotificationsWithError error: Error) {
        // Common in simulator (APNs unsupported), or missing APNs entitlement.
        NSLog("APNs registration failed: \(error)")
    }
}
```

The token returned is a 32-byte opaque identifier. It is *not* the device UDID and is
unique per app+device pair — installing the same app twice on the same device yields two
different tokens.

### APNs Protocol: Binary (Legacy) vs HTTP/2

Apple introduced a binary streaming protocol in 2005 that supported up to five concurrent
TCP/TLS streams. It was deprecated in 2020 and is no longer documented. All new
integrations must use **HTTP/2** (released with iOS 9 in 2015).

HTTP/2 APNs endpoint:

- **Production**: `https://api.push.apple.com/443`
- **Development**: `https://api.development.apple.com/443`

Authentication is by **JWT provider token** signed with an ES256 key you generate in the
Apple Developer portal. The token is sent in the `authorization` header:

```
POST /3/device/<device_token>
HTTP/2
authorization: bearer <JWT>
apns-topic: com.yourcompany.yourapp
apns-push-type: alert       // or background, voip, location, ...
apns-priority: 10           // 10 = immediate, 5 = conserve power
apns-expiration: 1700000000 // unix epoch; 0 = store forever until delivered
content-type: application/json

{ "aps": { "alert": "Hello", "badge": 1, "sound": "default" } }
```

Server-side provider example (Node.js, `jsonwebtoken` + `http2`):

```javascript
const http2 = require('http2');
const jwt = require('jsonwebtoken');
const fs = require('fs');

const teamId  = 'ABCDE12345';
const keyId   = 'FGHIJ67890';
const keyPath = './AuthKey_FGHIJ67890.p8';
const key     = fs.readFileSync(keyPath, 'utf8');

const token = jwt.sign({}, key, { algorithm: 'ES256', issuer: teamId, keyid: keyId });

const client = http2.connect('https://api.push.apple.com');

const req = client.request({
  ':method': 'POST',
  ':path': `/3/device/${deviceTokenHex}`,
  'authorization': `bearer ${token}`,
  'apns-topic': 'com.yourcompany.yourapp',
  'apns-push-type': 'alert',
  'apns-priority': '10',
  'content-type': 'application/json'
});

req.write(JSON.stringify({ aps: { alert: 'Hello', badge: 1 } }));
req.end();

req.on('response', (headers) => {
  if (headers[':status'] === 200) console.log('Delivered to APNs');
});
```

Apple's HTTP/2 implementation allows multiplexing: a single TCP+TLS connection can carry
many concurrent pushes, each on its own stream. If the stream returns `:status = 410` with
`reason: Unregistered`, the device has uninstalled the app and you must delete the token.

### APNs Payload Structure

```json
{
  "aps": {
    "alert": {
      "title": "New message",
      "body": "Tap to read",
      "subtitle": "From Alice",
      "title-loc-key": "msg_title",
      "loc-key": "msg_body_%d",
      "loc-args": [3],
      "action-loc-key": "read_action"
    },
    "badge": 5,
    "sound": "default",
    "thread-id": "message-thread-1",
    "category": "MESSAGE_CATEGORY",
    "mutable-content": 1,
    "content-available": 1,
    "interruption-level": "active"
  },
  "messageId": "abc123",
  "senderId": "u_alice"
}
```

The `aps` dictionary is interpreted by the OS — everything outside `aps` is opaque to the
OS and is delivered to your app as a `userInfo` dictionary. `interruption-level` controls
Focus Mode behavior and was added in iOS 15. `mutable-content: 1` opts into a
`UNNotificationServiceExtension` that has ~30 seconds to mutate the payload before display
— used for media attachments and end-to-end decrypted messaging apps.

### Silent Pushes (content-available)

Set `"content-available": 1` and `"apns-push-type": "background"` to wake the app without
showing UI. iOS will deliver the push to your app delegate silently, with up to 30 seconds
of background runtime to refresh data, sync, or pre-fetch.

```swift
func application(_ application: UIApplication,
                 didReceiveRemoteNotification userInfo: [AnyHashable: Any],
                 fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
    MessagingEngine.syncFromServer(userInfo) { result in
        completionHandler(.newData)
    }
}
```

Apple throttles silent pushes heavily. If a device is in low-power mode, the push may be
coalesced or delayed until the device is plugged in. Apple also imposes a per-device
budget (~70 silent pushes per day) — exceeding it silently stops delivery.

---

## FCM (Firebase Cloud Messaging)

### FCM Protocols: XMPP (deprecated) vs HTTP v1

Firebase inherited GCM's XMPP CCS (Connection Cloud Server) protocol for upstream messages
and high-throughput downstream. **XMPP CCS was deprecated on June 21, 2023 and removed in
June 2024.** All new integrations must use the **HTTP v1 API**, which:

- Uses OAuth2 access tokens instead of long-lived server keys.
- Routes iOS pushes through APNs transparently (you write a single payload and FCM
  translates it).
- Permits per-platform overrides (`android`, `apns`, `webpush`).

HTTP v1 endpoint:

```
POST https://fcm.googleapis.com/v1/projects/<project-id>/messages:send
Authorization: Bearer <oauth2_access_token>
Content-Type: application/json

{
  "message": {
    "token": "<registration_token>",
    "notification": { "title": "Hello", "body": "World" },
    "data": { "orderId": "abc" },
    "android": { "priority": "high", "ttl": "86400s" },
    "apns": { "headers": { "apns-priority": "10" }, "payload": { "aps": { "badge": 1 } } }
  }
}
```

OAuth2 access token (Google-administered, 1 hour TTL):

```bash
gcloud auth application-default print-access-token
```

Or from a service account JSON:

```python
from google.oauth2 import service_account
from google.auth.transport.requests import Request

creds = service_account.Credentials.from_service_account_file(
    'service-account.json',
    scopes=['https://www.googleapis.com/auth/firebase.messaging']
)
creds.refresh(Request())
print(creds.token)  # use as Bearer token
```

### Registration Token and Topic Messaging

On Android (and iOS via the FCM SDK), the registration token is returned asynchronously:

```kotlin
class MyApp : Application() {
    override fun onCreate() {
        super.onCreate()
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                ApiClient.registerToken(token)
            }
        }
    }
}

class MyFirebaseMessagingService : FirebaseMessagingService() {
    // Called when the OS rotates the token (rare, but happens on data clear/reinstall).
    override fun onNewToken(token: String) {
        ApiClient.updateToken(token)
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        if (remoteMessage.data.isNotEmpty()) {
            // data payload — always delivered, even in background
            handleData(remoteMessage.data)
        }
        remoteMessage.notification?.let {
            // notification payload — only delivered when app is foreground on Android
            showNotification(it.title, it.body)
        }
    }
}
```

**Topic messaging** lets you fan-out a single send to millions of devices that subscribed
to a topic string (e.g. `/topics/weather_europe`). FCM handles the subscription state and
broadcast internally — you only make one HTTP call. Useful for breaking news, weather, or
sports scores.

```kotlin
// Subscribe on client.
FirebaseMessaging.getInstance().subscribeToTopic("weather_europe")
```

```bash
# Send via REST.
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "topic": "weather_europe",
      "data": { "temp_c": "18", "city": "Berlin" }
    }
  }' \
  https://fcm.googleapis.com/v1/projects/my-project/messages:send
```

### FCM Payload (notification vs data)

| Field | Foreground | Background (Android, killed) | Background (iOS) |
|-------|------------|------------------------------|------------------|
| `notification` | Delivered to `onMessageReceived` | Displayed by system tray; `onMessageReceived` **not** called | Displayed by system; `didReceiveRemoteNotification` called on tap |
| `data`         | Delivered to `onMessageReceived` | Delivered to `onMessageReceived` (app woken in background) | Delivered via `content-available: 1` silent push |

This is a frequent interview gotcha: a `notification`-only payload on Android is **handled
by the system tray** when the app is killed. Your `onMessageReceived` is never invoked, so
you cannot customise the icon, route the user, or trigger a sync. To always run your own
code on Android, use `data` payloads only.

---

## APNs vs FCM Comparison

| Aspect | APNs | FCM |
|--------|------|-----|
| Owner | Apple | Google |
| Auth | JWT signed with ES256 p8 key | OAuth2 access token (1h TTL) |
| Transport | HTTP/2 multiplexed | HTTPS, single send per request |
| Topic/broadcast | n/a (use provider's fan-out) | Native `/topics/foo` |
| iOS support | Native | Translates to APNs internally |
| Android support | n/a | Native |
| Web push | n/a (Safari uses W3C Push, RFC 8291) | Native via VAPID (RFC 8291) |
| Upstream messages | n/a | Was XMPP; now via Firestore/callable functions |
| Payload size | 4 KB | 4 KB (legacy) / 4 KB (HTTP v1) |
| Throttling | Silent pushes budgeted (~70/day) | 240k/min per project default |

A common production pattern is to use **FCM for both platforms** to keep a single backend
code path, with platform-specific overrides in the HTTP v1 payload. FCM transparently
forwards to APNs for iOS, but you lose direct control over APNs features like
`apns-push-type: voip` (used for VoIP calls).

---

## Interview Questions

1. **Why does the device token change, and how should a server handle it?**
   Tokens can change on OS reinstall, device restore, or new device. Apple explicitly
   recommends re-registering on every launch and re-posting the token to your server
   idempotently. Apple also returns `410 Unregistered` on a push attempt for an uninstalled
   app — the provider must treat this as a signal to delete the token from its database.

2. **What is the difference between `notification` and `data` payloads in FCM?**
   `notification` is interpreted by the system tray — on Android when the app is killed,
   it is shown directly and `onMessageReceived` is *not* invoked. `data` is opaque and
   always delivered to your code. For full control on Android, use `data` payloads only.

3. **How do silent pushes work and what throttles them?**
   Set `content-available: 1` and `apns-push-type: background`. iOS wakes the app for up to
   30 seconds of background execution time without UI. Apple throttles heavily — Low Power
   Mode may delay them, and there is an undocumented per-device daily budget (~70). Exceed
   the budget and Apple silently drops further silent pushes for the day.

4. **Why did Firebase deprecate the XMPP-based CCS protocol?**
   XMPP CCS required a long-lived XML stream with stream-management stanzas, which was
   complex to operate and impossible to load-balance cleanly. HTTP v1 is stateless, uses
   OAuth2 instead of a long-lived server key (which is revocable and per-project-scoped),
   and routes iOS pushes through APNs transparently. Upstream messages that used XMPP are
   now handled via Firestore or callable Cloud Functions.

5. **What is RFC 8291 and how does web push relate to mobile push?**
   RFC 8291 ("Voluntary Application Server Identification (VAPID) for Web Push") defines
   how a web application server identifies itself to a push service using an ECDSA P-256
   key pair. Apple's Safari implements W3C Push + RFC 8291 for web pushes on macOS, while
   FCM uses VAPID for Chrome/Firefox web push. It is unrelated to native APNs/FCM, but
   shares the same conceptual delivery chain.

---

## References

- [Apple Developer — APNs Overview](https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/APNSOverview.html)
- [Apple Developer — Sending Push Notifications Using APNs (HTTP/2)](https://developer.apple.com/documentation/usernotifications/sending-push-messages-using-the-apple-push-notification-service)
- [Apple Developer — Establishing a Connection to APNs (JWT provider tokens)](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/establishing_a_certificate-based_connection_to_apns)
- [Firebase Cloud Messaging — HTTP v1 protocol](https://firebase.google.com/docs/cloud-messaging/http-server-ref)
- [Firebase — Send messages to topics](https://firebase.google.com/docs/cloud-messaging/send-message#topic_messages)
- [Firebase Cloud Messaging — HTTP v1 API documentation](https://firebase.google.com/docs/cloud-messaging)
- [RFC 8291 — Voluntary Application Server Identification (VAPID) for Web Push](https://www.rfc-editor.org/rfc/rfc8291)
- [RFC 8030 — Generic Event Delivery Using HTTP Push](https://www.rfc-editor.org/rfc/rfc8030)
- [Apple Developer — Local and Remote Programming Guide — The APNs payload keys](https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/ModifyingthePayload.html)
