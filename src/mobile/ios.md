# iOS Development

## Table of Contents

- [Swift Fundamentals for Interviews](#swift-fundamentals-for-interviews)
- [SwiftUI Basics](#swiftui-basics)
- [iOS App Lifecycle](#ios-app-lifecycle)
- [UIKit vs SwiftUI](#uikit-vs-swiftui)
- [Networking with URLSession](#networking-with-urlsession)
- [Data Persistence](#data-persistence)
- [Concurrency](#concurrency)
- [Push Notifications (APNs)](#push-notifications-apns)
- [App Signing & Provisioning](#app-signing--provisioning)
- [iOS Security](#ios-security)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Swift Fundamentals for Interviews

### Optionals

Optionals represent a value that may be absent. This is Swift's primary safety
mechanism against null pointer exceptions.

```swift
var name: String? = nil
name = "Alice"
let upper = name?.uppercased()  // Optional(String)
let forced = name!.uppercased()  // Crash if nil — avoid in production
if let unwrapped = name {
    print(unwrapped)  // Safe unwrapping
}
let defaulted = name ?? "Unknown"  // Nil coalescing
```

Key points: **Implicitly unwrapped optionals** (`String!`) are for cases where
nil is impossible after initialization (IBOutlets pre-Swift 4.2). **Optional chaining**
(`?.`) short-circuits the entire expression if any link is nil.

### Protocols

Protocols define a contract of requirements (methods, properties) that conforming
types must implement:

```swift
protocol Fetchable {
    associatedtype Item
    func fetch() async throws -> [Item]
}

struct UserFetcher: Fetchable {
    typealias Item = User
    func fetch() async throws -> [User] { ... }
}
```

Protocols with associated types require **opaque return types** (`some Fetchable`) or
**existentials** (`any Fetchable`) at call sites. Protocol-oriented programming
favors protocols and value types over class inheritance.

### Generics

Generics enable type-safe, reusable code:

```swift
func first<T>(_ array: [T]) -> T? {
    array.first
}
```

Generics can be constrained: `func merge<T: Comparable>(a: T, b: T) -> T`.
Swift uses **existential containers** (`any`) for type erasure when storing heterogeneous
collections of protocol-conforming types.

### Memory Management

Swift uses **Automatic Reference Counting (ARC)**:

- **Strong reference** — Increments reference count (default).
- **Weak reference** — Does not increment count; automatically nils when deallocated (`weak var`).
- **Unowned reference** — Like weak but not optional — assumes the reference outlives the holder. Crashes if accessed after deallocation.

**Retain cycles** occur when two objects hold strong references to each other.
Break with `weak` (delegates, parent-child) or `unowned` (closures capturing `self`).

```swift
// Closure capture list to break retain cycle
viewModel.onUpdate = { [weak self] result in
    self?.updateUI(with: result)
}
```

**Value types** (struct, enum) are copied on assignment — no ARC needed. Prefer structs
for data models; use classes only when reference semantics or inheritance are required.

## SwiftUI Basics

SwiftUI is Apple's declarative UI framework introduced in iOS 13:

```swift
struct ContentView: View {
    @State private var count = 0
    
    var body: some View {
        VStack {
            Text("Count: \(count)")
            Button("Increment") { count += 1 }
        }
    }
}
```

Key property wrappers:

| Wrapper | Scope | Behavior |
|---------|-------|----------|
| `@State` | View-local | Value type, triggers view re-render on change |
| `@Binding` | Parent-to-child | Two-way reference to a `@State` |
| `@ObservedObject` | Reference type | Observable class; view redraws on `objectWillChange` |
| `@StateObject` | View-owned | Creates and owns the observable object |
| `@EnvironmentObject` | Dependency injection | Shared object from ancestor view |
| `@Environment` | System values | Injected system values (e.g., `\(.dismiss)`) |

## iOS App Lifecycle

The app lifecycle is managed by `UIWindowSceneDelegate` (iOS 13+) or `UIApplicationDelegate`:

1. **`willFinishLaunchingWithOptions`** — App launched, no UI yet.
2. **`didFinishLaunchingWithOptions`** — Final initialization, restore state.
3. **`applicationDidBecomeActive`** — App is foreground and interactive.
4. **`applicationWillResignActive`** — Incoming call, notification center — save state.
5. **`applicationDidEnterBackground`** — App is in background. Release resources, save data.
6. **`applicationWillEnterForeground`** — Undo background changes.
7. **`applicationWillTerminate`** — App is being killed (rare; iOS may terminate without calling this).

**Scene lifecycle** (multi-window support on iPad):
- `sceneWillEnterForeground`, `sceneDidBecomeActive`, `sceneDidEnterBackground`.

## UIKit vs SwiftUI

| Aspect | UIKit | SwiftUI |
|--------|-------|----------|
| Paradigm | Imperative (command-based) | Declarative (state-driven) |
| Maturity | 15+ years, battle-tested | iOS 13+, still evolving |
| Complexity | Steeper learning curve | Lower entry barrier |
| Custom layout | Manual `Auto Layout` constraints | Stacks, grids, custom `Layout` protocol |
| Reusability | `UICollectionView`, `UITableView` with cells | `ForEach`, `List` with views |
| Integration | Full access to all APIs | Some APIs still UIKit-only |
| Testing | Harder to unit test views | ViewInspector for snapshot testing |
| Performance | Fine-grained control | Optimized by framework, less manual tuning |

In practice, most production apps use **SwiftUI with UIKit interop** (`UIViewRepresentable`,
`UIViewControllerRepresentable`) for legacy or unsupported components.

## Networking with URLSession

`URLSession` is the built-in networking API:

```swift
func fetchUsers() async throws -> [User] {
    let (data, response) = try await URLSession.shared
        .data(from: URL(string: "https://api.example.com/users")!)
    guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
        throw NetworkError.invalidResponse
    }
    return try JSONDecoder().decode([User].self, from: data)
}
```

Key concepts:
- **URLSessionConfiguration** — `.default` (disk caching), `.ephemeral` (memory only), `.background` (out-of-process transfers).
- **URLCache** — Handles HTTP caching per RFC 7234.
- **TLS certificate pinning** — Via `URLSessionDelegate.didReceive challenge` or `Network.framework`.
- **Multipart form data** — Build manually with `boundary` strings or use Alamofire.

## Data Persistence

| Solution | Type | Best For |
|----------|------|----------|
| **Core Data** | ORM / object graph | Complex models, relationships, migrations |
| **SwiftData** | Modern ORM (iOS 17+) | New projects, `@Model` macro, Core Data backend |
| **SQLite (via GRDB/FMDB)** | Raw SQL | Performance-critical, complex queries |
| **Realm** | Object database | Fast writes, offline-first, real-time sync |
| **UserDefaults** | Key-value | Small preferences (not large data) |
| **File System** | Plists, JSON, binary | Documents, caches, exports |

### Core Data Stack
Core Data requires: **NSPersistentContainer** (manages the stack), **NSManagedObjectModel**
(defined in `.xcdatamodeld`), **NSManagedObjectContext** (read/write operations).

- **NSFetchRequest** with `NSPredicate` for querying.
- **NSFetchedResultsController** for table view integration with change tracking.
- **Lightweight migration** for schema changes; **custom migration** for complex changes.

## Concurrency

### Structured Concurrency (Swift 5.5+)

```swift
func fetchAndProcess() async throws -> Result {
    async let users = fetchUsers()
    async let posts = fetchPosts()
    let (u, p) = try await (users, posts)  // Concurrent execution
    return merge(users: u, posts: p)
}
```

- **`async/await`** — Structured concurrency with task trees. Parent tasks wait for children.
- **`Task`** — Fire-and-forget top-level concurrent unit.
- **`TaskGroup`** — Dynamic collection of concurrent child tasks.
- **`@MainActor`** — Ensures code runs on the main thread (UI updates).
- **`Sendable`** protocol — Types safe to pass across concurrency boundaries.

### Grand Central Dispatch (GCD)
Legacy but still relevant:

```swift
DispatchQueue.global(qos: .userInitiated).async {
    let result = heavyComputation()
    DispatchQueue.main.async {
        self.updateUI(with: result)
    }
}
```

QoS levels: `.userInteractive`, `.userInitiated`, `.default`, `.utility`, `.background`.

## Push Notifications (APNs)

Apple Push Notification service (APNs) delivers remote notifications:

1. App registers for remote notifications (`UNUserNotificationCenter.requestAuthorization`).
2. App receives a **device token** from APNs (unique per device-app pair).
3. Device token is sent to your backend server.
4. Backend sends a POST to `https://api.push.apple.com/3/device/{token}` with a JWT or certificate.
5. APNs delivers to the device; if offline, APNs queues (limited time).

**Notification types:**
- **Alert** — Banner, sound, badge.
- **Background** — Silent content-available notification; app wakes in background (30s limit).
- **VoIP** — Persistent connection for calling apps.

Use **Notification Service Extension** to modify payload before display (e.g., decrypt content).
Use **Notification Content Extension** for custom UI (images, actions).

## App Signing & Provisioning

| Concept | Purpose |
|---------|---------|
| **Certificate** | Identifies the developer; issued by Apple |
| **Provisioning Profile** | Links certificate + App ID + devices (development) or certificate + App ID (distribution) |
| **App ID** | Unique bundle identifier (`com.company.app`) with configured capabilities |
| **Entitlements** | Permissions (push notifications, keychain sharing, iCloud) |
| **Capabilities** | Features enabled in the Apple Developer portal |

Distribution methods: **App Store**, **TestFlight** (beta), **Ad Hoc** (registered devices),
**Enterprise** (internal distribution, requires Enterprise Program), **MDM** (managed devices).

Xcode manages signing automatically via **Automatic Signing** with a development team.
For CI/CD, use **manual signing** with `.p12` certificates and `.mobileprovision` profiles
installed on the build machine.

## iOS Security

| Feature | Purpose |
|---------|---------|
| **Keychain Services** | Secure storage for passwords, tokens, certificates |
| **Secure Enclave** | Hardware-isolated crypto operations (Touch ID, Face ID, key generation) |
| **App Transport Security (ATS)** | Enforces TLS 1.2+ for all network connections |
| **Data Protection** | File-level encryption tied to device lock state |
| **BioMetric (LocalAuthentication)** | Touch ID / Face ID via `LAContext` |
| **String Encryption** | Obfuscate hardcoded strings at rest |
| **Jailbreak Detection** | Runtime checks (file system, symlink, dyld) |

### Keychain vs UserDefaults
- **Keychain**: Encrypted, backed up to iCloud Keychain, survives app reinstalls. Use for tokens, passwords, API keys.
- **UserDefaults**: Plaintext (encrypted at rest only if device is locked with Data Protection). Use for preferences only.

### Secure Enclave
A dedicated coprocessor that stores encryption keys in hardware. Keys generated in the
Secure Enclave never leave it — all cryptographic operations happen inside. This is
the foundation for Face ID, Touch ID, and Apple Pay.

---

## Interview Questions

1. **What is the difference between a struct and a class in Swift?**
   Structs are value types (copied on assignment, stack-allocated), have no inheritance, and use memberwise initializers. Classes are reference types (shared via pointers, heap-allocated), support inheritance and deinitializers (`deinit`). Prefer structs for data models; use classes when you need reference semantics, identity, or Objective-C interoperability.

2. **How does ARC work and what causes memory leaks?**
   ARC tracks the number of strong references to each class instance. When the count reaches zero, the instance is deallocated. Memory leaks (retain cycles) occur when two objects hold strong references to each other (e.g., a view controller holding a strong reference to a closure that captures `self` strongly). Break with `weak` or `unowned`.

3. **Explain the difference between `@State`, `@ObservedObject`, and `@StateObject`.**
   `@State` is for view-local value types owned by the view. `@ObservedObject` is for reference-type objects passed in from a parent — the parent owns the lifecycle. `@StateObject` is for reference-type objects owned and created by the view itself. Use `@StateObject` when the view creates the object; use `@ObservedObject` when it's injected.

4. **How does structured concurrency improve over GCD?**
   Structured concurrency (`async/await`, `TaskGroup`) creates a parent-child relationship between tasks. Cancellation propagates automatically from parent to children. Errors propagate in a structured way. GCD dispatches work to queues with no parent-child relationship, making cancellation and error handling manual and error-prone.

5. **What is the difference between Core Data and Realm?**
   Core Data is Apple's framework built on SQLite (or in-memory). It has a steep learning curve, complex migrations, and verbose API, but integrates deeply with the Apple ecosystem. Realm is an object database with zero-copy architecture, simpler API, live objects (auto-updating UI), and built-in sync. Realm is faster for writes; Core Data offers more control over the underlying SQL.

6. **Explain how APNs delivery works end-to-end.**
   The app registers with APNs and receives a device token. This token is sent to your server. When you want to send a notification, your server authenticates with APNs (using a JWT or certificate) and POSTs a payload to `api.push.apple.com/3/device/{token}`. APNs routes the notification to the correct device. If the device is offline, APNs holds the notification briefly (not indefinitely). On delivery, iOS displays it or wakes the app for background processing.

7. **What is the Secure Enclave and when would you use it?**
   The Secure Enclave is a hardware coprocessor that performs cryptographic operations in isolation. Keys generated inside it never leave. Use it for biometric authentication (Face ID/Touch ID key generation via `SecAccessControlCreateFlag.biometryAny`), secure key storage for encryption, and Apple Pay. Access it via the Security framework (`SecKeyCreateRandomKey` with `kSecAttrTokenIDSecureEnclave`).

8. **How do you handle backward compatibility when adopting new iOS APIs?**
   Use `if #available(iOS 17, *)` for runtime checks. Use `@available` attribute on types and functions. For SwiftUI features, provide fallback views. For deprecated APIs, use `@available(*, deprecated)` on your own wrappers and migrate incrementally.

## References

- [Swift Documentation](https://docs.swift.org/)
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- [Swift Concurrency](https://docs.swift.org/docs/swift-book/LanguageGuide/Concurrency.html)
- [Core Data Programming Guide](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CoreData/)
- [Apple Push Notification Service](https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server)
- [Secure Enclave](https://developer.apple.com/documentation/security/certificate_key_and_trust_services/keys/protecting_keys_with_the_secure_enclave)