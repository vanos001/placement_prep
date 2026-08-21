# Mobile Databases: SQLite, Realm, Core Data, Room

## Table of Contents

- [The Database Landscape on Mobile](#the-database-landscape-on-mobile)
- [SQLite on Mobile](#sqlite-on-mobile)
  - [The SQLite C API](#the-sqlite-c-api)
  - [WAL Mode and Concurrency](#wal-mode-and-concurrency)
- [Room (Android)](#room-android)
  - [Entities, DAOs, and Database](#entities-daos-and-database)
  - [Type-Safe Queries and the @Transaction Boundary](#type-safe-queries-and-the-transaction-boundary)
- [Core Data (iOS)](#core-data-ios)
  - [Object Graph + SQLite Backend](#object-graph--sqlite-backend)
  - [ManagedObjectContext Concurrency](#managedobjectcontext-concurrency)
- [Realm (Object Database, no SQL)](#realm-object-database-no-sql)
- [Key-Value Stores: UserDefaults and SharedPreferences](#key-value-stores-userdefaults-and-sharedpreferences)
- [Comparison Matrix](#comparison-matrix)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## The Database Landscape on Mobile

Mobile apps need persistent storage that survives app restarts and OS reboots, works
without a network, and performs under tight memory and battery limits. The major options:

```
                  ┌──────────────────────┐
                  │  Mobile Storage       │
                  └──────────┬───────────┘
                             │
   ┌──────────────┬──────────┴──────────┬──────────────────┐
   ▼              ▼                     ▼                  ▼
 Key-Value     Relational            Object DB         Object Graph +
 (KVP)         SQL store            (Realm)           SQL backend
   │              │                     │                  │
   │              ▼                     │                  ▼
   │              ┌──────────────┐       │              Core Data
   │              │   SQLite     │       │              (NSManagedObject)
   │              └──────┬───────┘       │                  ▲
   │                     │               │                  │
   │                     ├── Android    │                  │
   │                     │   raw        │                  │
   │                     │              │                  │
   │                     ├── Room       │                  │
   │                     │   (ORM on    │                  │
   │                     │   SQLite)    │                  │
   │                     │              │                  │
   │                     └── Core Data  │                  │
   │                          backend  ─┘                  │
   │                                                                     │
   ▼                                                                     │
 UserDefaults     (iOS plist in Library/Preferences)                       │
 EncryptedSharedPreferences  (Android Keystore-backed)                     │
 SharedPreferences         (Android XML)                                   │
```

Each layer makes different tradeoffs between query expressivity, type safety,
performance, and developer ergonomics.

---

## SQLite on Mobile

SQLite is a **single-file, embedded, serverless relational database engine** that runs
in-process. There is no daemon, no port, no client-server protocol — your app calls the C
library (`libsqlite3.dylib` on iOS, bundled with Android via the system image) directly.

Key characteristics relevant on mobile:

- **Zero config.** A single file at a path you specify is the database.
- **ACID transactions.** Use `BEGIN/COMMIT/ROLLBACK` for atomic writes.
- **Page-based storage.** Default page size is 4 KB; an entire 100 MB database is just
  25,000 pages with a B-tree structure.
- **Cross-platform binary compatibility.** The file format is documented and stable since
  version 3 (2004). You can copy a database from iOS to a server and query it.

### The SQLite C API

Direct usage (iOS via `sqlite3.h`, available without external dependencies):

```c
#import <sqlite3.h>

sqlite3 *db = NULL;
if (sqlite3_open_v2("path/to/db.sqlite3", &db,
                    SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE,
                    NULL) != SQLITE_OK) {
    NSLog(@"open failed: %s", sqlite3_errmsg(db));
    return;
}

sqlite3_stmt *stmt = NULL;
const char *sql = "INSERT INTO users (id, name) VALUES (?, ?);";
if (sqlite3_prepare_v2(db, sql, -1, &stmt, NULL) != SQLITE_OK) {
    NSLog(@"prepare failed: %s", sqlite3_errmsg(db));
    sqlite3_close(db);
    return;
}

sqlite3_bind_text(stmt, 1, "u-918273", -1, SQLITE_TRANSIENT);
sqlite3_bind_text(stmt, 2, "Alice",   -1, SQLITE_TRANSIENT);

if (sqlite3_step(stmt) == SQLITE_DONE) {
    NSLog(@"inserted rowid %lld", sqlite3_last_insert_rowid(db));
}
sqlite3_finalize(stmt);
sqlite3_close(db);
```

Three things matter for performance on mobile:

1. **Always use `?` placeholders.** They let SQLite's query planner cache the prepared
   statement and prevent SQL injection by separating code from data.
2. **Wrap multi-row inserts in `BEGIN/COMMIT`.** Without a transaction, SQLite does a
   full fsync per row (each row is a separate journal write). Inside a transaction, the
   journal is written once.
3. **Reuse prepared statements** in hot paths (you can keep a `sqlite3_stmt *` around and
   rebind+step repeatedly).

### WAL Mode and Concurrency

By default SQLite uses rollback-journal mode: any write blocks all readers until the
write commits. For a mobile app, this means a large write (e.g. cache refresh) can stutter
the UI thread reading from the same database.

**WAL (Write-Ahead Logging)** mode is the standard remedy:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;  -- was FULL by default
```

With WAL:

- All writes append to a separate `db.sqlite3-wal` file.
- Readers see a consistent snapshot via `db.sqlite3-shm` (shared memory).
- Readers and one writer run concurrently — no blocking.
- Multiple readers can run on multiple threads.

Concurrency diagram:

```
           ┌──────────────────┐
           │  db.sqlite3       │   <- committed pages
           └──────────────────┘
                    ▲
                    │ checkpoint runs occasionally
                    │
           ┌──────────────────┐
           │  db.sqlite3-wal   │   <- appended writes
           └──────────────────┘
                    ▲
                    │ every INSERT/UPDATE/DELETE appends here
                    │
           ┌──────┴──────┬──────┬──────┐
           ▼             ▼      ▼      ▼
        Writer T1     Reader  Reader  Reader
                      (snapshot of last commit)
```

WAL is the default mode used by Core Data and is recommended for any non-trivial Room
database.

---

## Room (Android)

Room is Google's official **type-safe ORM over SQLite**. It removes the boilerplate of
cursor management, mapping rows to POJOs, and writing SQL string queries by hand, while
still exposing raw SQL for query control.

The architecture is split into three layers:

```
   ┌────────────────────────────────────────┐
   │  @Database abstract class              │   app code
   │   fun userDao(): UserDao               │
   │   fun repoDao(): RepoDao               │
   └──────────────┬─────────────────────────┘
                  │ depends on
                  ▼
   ┌────────────────────────────────────────┐
   │  @Dao interface                        │   SQL definitions
   │   @Query("SELECT * FROM user") ...     │
   │   @Insert  suspend fun insert(User)    │
   └──────────────┬─────────────────────────┘
                  │ operates on
                  ▼
   ┌────────────────────────────────────────┐
   │  @Entity data class                    │   schema
   │   @PrimaryKey val id: String           │
   │   @ColumnInfo val name: String         │
   └────────────────────────────────────────┘
```

### Entities, DAOs, and Database

```kotlin
// build.gradle.kts — kapt or ksp plugin applies the annotation processor.
plugins {
    id("com.google.devtools.ksp")
    id("androidx.room")
}
dependencies {
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
}

// Entity
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "age") val age: Int,
    @ColumnInfo(name = "created_at") val createdAt: Long
)

// DAO — Room generates the implementation at compile time.
@Dao
interface UserDao {
    @Query("SELECT * FROM users WHERE age >= :minAge ORDER BY name ASC")
    fun usersOlderThan(minAge: Int): List<UserEntity>            // blocking
    @Query("SELECT * FROM users WHERE age >= :minAge ORDER BY name ASC")
    suspend fun usersOlderThanSuspend(minAge: Int): List<UserEntity>  // coroutine
    @Query("SELECT * FROM users WHERE age >= :minAge ORDER BY name ASC")
    fun usersOlderThanFlow(minAge: Int): Flow<List<UserEntity>>  // observable

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(user: UserEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(users: List<UserEntity>)

    @Delete
    suspend fun delete(user: UserEntity)
}

@Database(entities = [UserEntity::class], version = 1, exportSchema = true)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
}

// Use it (singleton + DI)
object DatabaseHolder {
    val db: AppDatabase by lazy {
        Room.databaseBuilder(
            App.context, AppDatabase::class.java, "app.db"
        )
        .addCallback(object : RoomDatabase.Callback() {
            override fun onCreate(db: SupportSQLiteDatabase) {
                db.execSQL("CREATE INDEX idx_users_age ON users(age)")
            }
        })
        .fallbackToDestructiveMigration()  // dev only; use migrations in prod
        .build()
    }
}
```

### Type-Safe Queries and the @Transaction Boundary

Room validates every `@Query` SQL string **at compile time** against the schema you
declared with `@Entity`. If you reference a non-existent column, the build fails — not
the user at runtime.

Two important notes:

1. **Return `Flow`/`LiveData`** to get observable queries. Room registers a SQLite
   trigger listener (`sqlite3_update_hook`) on the relevant tables and re-emits when
   they change. This is the modern reactive pattern for Android UIs.

2. **Use `@Transaction` for batched writes.** Without it, calling `upsertAll` from the
   DAO above executes N `INSERT` statements each in their own implicit transaction
   (slow because of N fsyncs). `@Transaction` wraps them in `BEGIN/COMMIT`.

```kotlin
@Dao
abstract class UserDao {
    @Transaction
    open suspend fun replaceAll(users: List<UserEntity>) {
        clearAll()
        upsertAll(users)
    }

    @Query("DELETE FROM users")
    abstract suspend fun clearAll()

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    abstract suspend fun upsertAll(users: List<UserEntity>)
}
```

**Migrations** are versioned, explicit, and type-checked:

```kotlin
val MIGRATION_1_2 = object : Migration(1, 2) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE users ADD COLUMN email TEXT")
    }
}

Room.databaseBuilder(App.context, AppDatabase::class.java, "app.db")
    .addMigrations(MIGRATION_1_2)
    .build()
```

Forgetting a migration between two releases causes a runtime `IllegalStateException`
("A migration from X to Y was required but not found"). This is by design: a silent
schema change would corrupt data.

---

## Core Data (iOS)

Core Data is Apple's **object-graph and persistence framework**. It is not an ORM (Apple
explicitly distances it from that label) and is not a database — it is an in-memory object
graph with a pluggable backend that is, in 99% of apps, a SQLite file.

### Object Graph + SQLite Backend

The architecture:

```
   ┌─────────────────────────────────────────────┐
   │  NSPersistentContainer                       │  top-level coordinator
   │   ├── NSManagedObjectContext                 │  scratchpad / unit of work
   │   ├── NSPersistentStoreCoordinator           │  ties contexts to stores
   │   └── NSManagedObjectModel (.xcdatamodeld)   │  schema: entities + attributes
   └──────────────┬───────────────────────────────┘
                  │ talks to (one or more) persistent stores
                  ▼
   ┌──────────────────────────────────────────────┐
   │  NSSQLiteStore (the default store type)       │
   │   db.sqlite (WAL mode)                        │
   └──────────────────────────────────────────────┘
```

Bootstrapping:

```swift
import CoreData

class PersistenceController {
    static let shared = PersistenceController()
    let container: NSPersistentContainer

    init(inMemory: Bool = false) {
        container = NSPersistentContainer(name: "AppModel")
        if inMemory {
            container.persistentStoreDescriptions.first!.url = URL(fileURLWithPath: "/dev/null")
        }
        container.loadPersistentStores { description, error in
            if let error = error as NSError? {
                fatalError("CoreData load failed: \(error.userInfo)")
            }
        }
        container.viewContext.automaticallyMergesChangesFromParent = true
    }
}
```

Inserting + querying:

```swift
let ctx = PersistenceController.shared.container.viewContext
let user = User(context: ctx)        // User is an NSManagedObject subclass
user.id = UUID()
user.name = "Alice"
user.age = 30
try? ctx.save()                      // single commit

// Query
let fetch: NSFetchRequest<User> = User.fetchRequest()
fetch.predicate = NSPredicate(format: "age >= %d", 18)
fetch.sortDescriptors = [NSSortDescriptor(key: "name", ascending: true)]
let results = (try? ctx.fetch(fetch)) ?? []
```

### ManagedObjectContext Concurrency

Core Data contexts are **not thread-safe**. Each context is bound to a queue, and you must
always touch it via `perform`/`performAndWait` or by using the appropriate context type:

- `viewContext` — bound to the main queue, used by UI.
- A private-queue context (e.g. `container.newBackgroundContext()`) — for heavy work
  off the main thread.

```swift
func refreshFromNetwork(completion: @escaping ([User]) -> Void) {
    let bg = PersistenceController.shared.container.newBackgroundContext()
    bg.perform {
        // Network call.
        let payload = APIClient.fetchUsers()
        // Delete + insert.
        let delete = NSBatchDeleteRequest(
            fetchRequest: NSFetchRequest<NSFetchRequestResult>(
                entityName: "User"))
        try? bg.execute(delete)
        payload.forEach { p in
            let u = User(context: bg)
            u.id = p.id; u.name = p.name; u.age = p.age
        }
        try? bg.save()
        // Push to view context via merge policy.
        DispatchQueue.main.async {
            PersistenceController.shared.container.viewContext.perform {
                completion((try? PersistenceController.shared.container.viewContext.fetch(User.fetchRequest())) ?? [])
            }
        }
    }
}
```

The classic Core Data bug: touching a context from the wrong queue. Symptoms include
random crashes with no stack trace ("CoreData could not fulfill a fault" or EXC_BAD_ACCESS
inside `_PFObjectReferenceFastQueueGetIndex`). Always use `perform { }`.

---

## Realm (Object Database, no SQL)

Realm is an **object database** — it does not sit on top of SQLite. The on-disk format is
a memory-mapped B+ tree of object graphs. Reads are zero-copy: a Realm object is a thin
wrapper around an offset into the mmap'd file, so a 1 MB object graph loads in constant
time regardless of size.

```kotlin
// build.gradle.kts (Realm Kotlin)
plugins {
    id("io.realm.kotlin")
}
dependencies {
    implementation("io.realm.kotlin:library:1.11.0")
}

// Model
class User : RealmObject {
    @PrimaryKey var id: String = ""
    var name: String = ""
    var age: Int = 0
}

// Use
val config = RealmConfiguration.Builder(schema = setOf(User::class))
    .name("app.realm")
    .build()
val realm = Realm.open(config)

// Insert
realm.writeBlocking {
    copyToRealm(User().apply {
        id = "u-918273"; name = "Alice"; age = 30
    })
}

// Query (sync)
val adults = realm.query<User>("age >= 18").find()
// Query (reactive, Flow)
val flow: Flow<ResultsChange<User>> = realm.query<User>("age >= 18").asFlow()
flow.collect { change ->
    when (change) {
        is InitialResults -> updateUi(change.list)
        is UpdatedResults -> updateUi(change.list)
    }
}
```

Realm advantages:

- **Direct mmap** makes reads extremely fast (no deserialization per row).
- **Live objects**: changes to a `User` in another thread update your `Flow` automatically
  without re-fetching.
- **Cross-platform binary**: the same Realm file works on iOS and Android.

Realm tradeoffs:

- **Mandatory threading rules**: Realm instances are thread-confined. Passing a `User`
  across threads without `freeze()`-ing it is a runtime crash.
- **Class inheritance**: your model classes must inherit from `RealmObject` (iOS) or
  conform to `Object` (Swift) — invasive.
- **File size**: Realm's file format includes indexes and historical versions for live
  reads, so the file is typically larger than the equivalent SQLite DB (often 2-3x).

After MongoDB's acquisition of Realm (2019), Realm is being merged with the
**Atlas Device SDK** and the long-term roadmap points toward MongoDB Sync. For local-only
storage on Android, Google recommends Room; Realm is a strong choice when you need its
live objects and reactive UI patterns.

---

## Key-Value Stores: UserDefaults and SharedPreferences

For small, low-write configuration data, a full database is overkill. Both platforms
provide a key-value store backed by a single plist/XML file.

### iOS — UserDefaults

```swift
let defaults = UserDefaults.standard
defaults.set("Alice", forKey: "username")
defaults.set(30, forKey: "age")
defaults.synchronize()  // deprecated since iOS 12; happens automatically on background

let name = defaults.string(forKey: "username") ?? "Anonymous"
```

Internals: a single `.plist` in `Library/Preferences/<bundle-id>.plist`, written by the
`cfprefsd` daemon (XPC) on iOS. Writes are debounced and flushed periodically. Never store
secrets here — the file is plain XML on disk.

**Secure variant:** Keychain Services for anything sensitive (tokens, credentials). Or
use the open-source `KeychainAccess` Swift wrapper.

### Android — SharedPreferences

```kotlin
val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
prefs.edit().putString("username", "Alice").putInt("age", 30).apply()
// commit() vs apply(): apply() is async (recommended), commit() is sync.
val name = prefs.getString("username", "Anonymous")
```

Internals: a single XML file in `/data/data/<pkg>/shared_prefs/settings.xml`. Written
synchronously to disk in a background thread by `apply()`; synchronously by `commit()`.

**Secure variant:** `EncryptedSharedPreferences` from Jetpack Security — values encrypted
with AES-GCM via a master key in the Android Keystore (hardware-backed on supported
devices).

Common pitfalls:

- SharedPreferences loaded via `MODE_MULTI_PROCESS` historically allowed cross-process
  sharing, but this was broken on Android 6+ and removed entirely on Android Q+. Use a
  `ContentProvider`, `Room`, or `DataStore` (the modern replacement) for cross-process
  shared state.
- Large SharedPreferences files slow down app start (the entire XML is parsed eagerly).
  Google recommends migrating to Room or DataStore if your shared prefs exceed ~100 keys.

---

## Comparison Matrix

| Feature | SQLite (raw) | Room | Core Data | Realm | UserDefaults / SharedPrefs |
|---------|-------------|-----|-----------|-------|----------------------------|
| Backend | self | SQLite | SQLite (default) | own mmap format | plist / XML |
| Query language | SQL strings | SQL (validated at compile time) | NSPredicate | Realm Query Language (RQL) | none (KVP) |
| Type safety | none | compile-time-checked | runtime-checked | compile-time-checked (via codegen) | none |
| Reactive reads | manual | `Flow`/`LiveData` | `NSFetchedResultsController` | `Flow<ResultsChange>` | `OnSharedPreferenceChangeListener` |
| Concurrency | WAL readers + 1 writer | same (built on SQLite) | main + private contexts | MVCC, no read locks | process-wide; IPC broken |
| Migrations | hand-written ALTER scripts | `Migration` classes | `NSMappingModel` / `NSMigrationManager` (heavy); or `NSPersistentHistoryChange` | schema versioned per file | none (no schema) |
| Binary size impact | ~0 (system lib) | ~few hundred KB | 0 (system) | ~2 MB added | 0 (system) |
| Cross-platform file | yes | yes (SQLite is portable) | yes (SQLite portable) | yes (Realm format portable) | no |
| Best for | bulk SQL, custom schema | Android apps needing reactive + type-safe queries | iOS apps with complex object graphs | iOS/Android apps needing extreme read perf + live objects | tiny configs, no sensitive data |

---

## Interview Questions

1. **What is SQLite's WAL mode and why is it the recommended mode for mobile apps?**
   WAL (Write-Ahead Logging) splits writes into a separate `-wal` file appended to on
   every mutation, while readers see a snapshot from the shared memory (`-shm`) file.
   This allows readers and one writer to run concurrently without blocking — critical
   when a UI thread reads while a sync writes. Without WAL, the default rollback-journal
   mode blocks readers during writes and requires a full fsync per transaction. WAL is
   the default for Core Data and is the recommended configuration for any Room DB.

2. **How does Room validate SQL at compile time, and what happens if you write a typo?**
   The KSP/KAPT annotation processor reads your `@Entity` classes, builds an in-memory
   schema, parses each `@Query` SQL string, and resolves every column reference against
   that schema. If the column doesn't exist, the build fails. This is why Room does not
   let you write queries by string concatenation — concatenation would bypass the
   validator.

3. **Why does Core Data use the term "object graph" instead of "ORM"?**
   ORM (like Hibernate on the JVM) maps SQL rows to language objects. Core Data's data
   model is an object graph (entities with relationships, inverse relationships,
   deletion rules) that *may* be persisted to a SQLite store, an XML store, a binary
   store, or an in-memory store. The persistent store is pluggable: switching from
   SQLite to XML is a one-line configuration change. So Core Data is a persistence
   *framework* whose default backend happens to be SQLite — not an ORM.

4. **Why are Core Data contexts thread-confined?**
   Each `NSManagedObjectContext` has a private queue and an internal lock structure. If
   you mutate a managed object from another thread, you race against that queue. The
   crash symptoms are subtle (faults failing, EXC_BAD_ACCESS inside Core Data
  `_PFObjectReferenceFastQueueGetIndex`). The rule: use `viewContext` only on the main
   thread, use `newBackgroundContext()` for heavy work, and use `context.perform { }`
   when in doubt about the current thread.

5. **What's the trade-off of Realm's zero-copy mmap reads vs SQLite?**
   Realm memory-maps the file; a Realm object is a pointer+offset into the mmap region.
   Loading an object graph is therefore O(1) regardless of file size — no row
   deserialization. SQLite must allocate, parse, and decode each row into a cursor, so
   large scans are slower. The tradeoff is that the Realm file is larger (it stores
   indexes and historical versions for live reads), Realm objects are thread-confined
   (the mmap is process-shared but objects have an associated Realm instance), and the
   file format is proprietary — you can't open a Realm DB with a SQL tool.

6. **When should you NOT use SharedPreferences?**
   SharedPreferences is loaded entirely into memory at first access, has no schema and
   no migration story, and historically claimed to be multi-process safe (which was
   broken on Android 6+). Don't use it for: large data (>100 keys), data needing
   schema/migration, cross-process shared state, or sensitive values (use
   EncryptedSharedPreferences or Keystore-backed storage). For new code, prefer
   `DataStore` (Jetpack) for typed, async, observable preferences.

---

## References

- [SQLite — official documentation and SQL syntax](https://www.sqlite.org/docs.html)
- [SQLite — Write-Ahead Logging](https://www.sqlite.org/wal.html)
- [SQLite — Transaction and Concurrency model](https://www.sqlite.org/lockingv3.html)
- [Android Room — Save data in a local database](https://developer.android.com/training/data-storage/room)
- [Android Room — Migration guide](https://developer.android.com/training/data-storage/room/migrating-db-versions)
- [Android Jetpack DataStore (modern KVP replacement)](https://developer.android.com/topic/libraries/architecture/datastore)
- [Apple — Core Data Programming Guide](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/CoreData/)
- [Apple — NSPersistentContainer documentation](https://developer.apple.com/documentation/coredata/nspersistentcontainer)
- [Apple — Concurrency with Core Data](https://developer.apple.com/documentation/coredata/performing_core_data_tasks_on_a_background_task)
- [Realm — Documentation hub](https://www.mongodb.com/docs/realm/)
- [Realm Kotlin SDK](https://www.mongodb.com/docs/realm/sdk/kotlin/)
- [Apple — UserDefaults reference](https://developer.apple.com/documentation/foundation/userdefaults)
- [Android — SharedPreferences docs](https://developer.android.com/training/data-storage/shared-preferences)
- [Android Jetpack Security — EncryptedSharedPreferences](https://developer.android.com/topic/security/data)
