# Android Development

## Android Architecture

```
┌──────────────────────────────┐
│     Applications             │
├──────────────────────────────┤
│     Jetpack / Framework      │  (Activity, Fragment, ViewModel, Room)
├──────────────────────────────┤
│     Android Runtime (ART)    │  (Dex bytecode, AOT compilation)
├──────────────────────────────┤
│     Hardware Abstraction     │  (Camera, Bluetooth, Sensors)
├──────────────────────────────┤
│     Linux Kernel             │  (Drivers, Process management, Memory)
└──────────────────────────────┘
```

## Activity Lifecycle

```
onCreate → onStart → onResume → [Running] → onPause → onStop → onDestroy
                                      ↑                  ↓
                                  onRestart ←────────────
```

| Method | When Called |
|---|---|
| `onCreate` | Activity first created |
| `onStart` | Activity becomes visible |
| `onResume` | Activity gains focus (interactive) |
| `onPause` | Activity loses focus (partially visible) |
| `onStop` | Activity no longer visible |
| `onDestroy` | Activity being destroyed |

## Jetpack Compose

Modern declarative UI toolkit:

```kotlin
@Composable
fun UserCard(user: User) {
    var expanded by remember { mutableStateOf(false) }
    
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { expanded = !expanded }
            .padding(16.dp)
    ) {
        Column {
            Text(text = user.name, style = MaterialTheme.typography.h6)
            if (expanded) {
                Text(text = user.email)
                Text(text = user.bio)
            }
        }
    }
}
```

## ViewModel

```kotlin
class UserViewModel(private val repository: UserRepository) : ViewModel() {
    private val _users = MutableStateFlow<List<User>>(emptyList())
    val users: StateFlow<List<User>> = _users.asStateFlow()
    
    fun loadUsers() {
        viewModelScope.launch {
            _users.value = repository.getUsers()
        }
    }
}
```

## Room (Database)

```kotlin
@Entity(tableName = "users")
data class User(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "email") val email: String
)

@Dao
interface UserDao {
    @Query("SELECT * FROM users")
    fun getAll(): Flow<List<User>>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(user: User)
}

@Database(entities = [User::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
}
```

## Coroutines

```kotlin
viewModelScope.launch {
    try {
        val user = withContext(Dispatchers.IO) {
            api.getUser(id)  // Network call on IO thread
        }
        _user.value = user   // Update UI on Main thread
    } catch (e: Exception) {
        _error.value = e.message
    }
}
```

## Interview Questions

**Q: Explain the Android Activity lifecycle.**
A: onCreate (initialization), onStart (visible), onResume (interactive), onPause (losing focus), onStop (no longer visible), onDestroy (being destroyed). onSaveInstanceState for preserving state across config changes.

**Q: What is Jetpack Compose and why use it?**
A: Declarative UI toolkit for Android. Instead of XML layouts, describe UI as composable functions. Benefits: less boilerplate, reactive updates, better preview, type-safe. State drives UI — when state changes, UI recomposes.

**Q: What is the difference between LiveData and StateFlow?**
A: Both are observable data holders. LiveData is lifecycle-aware (auto-stops observing), simple API. StateFlow is Kotlin coroutines-based, more flexible, supports operators (map, filter), works with Compose. Prefer StateFlow for new projects.

## References

- [Android Developer Documentation](https://developer.android.com/docs)
- [Jetpack Compose Documentation](https://developer.android.com/jetpack/compose)
