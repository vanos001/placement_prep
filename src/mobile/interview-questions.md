# Mobile Development Interview Questions

**Q: What is the difference between Activities and Fragments?**
A: Activity = single screen with UI. Fragment = reusable UI portion within an Activity. Fragments have their own lifecycle, can be added/removed dynamically, enable multi-pane layouts. Activities are the container; Fragments are the content.

**Q: How do you handle configuration changes (rotation) in Android?**
A: (1) ViewModel survives config changes (recommended), (2) onSaveInstanceState/onRestoreInstanceState for small data, (3) `configChanges` in manifest to handle yourself, (4) remember/rememberSaveable in Compose.

**Q: What is the repository pattern in Android?**
A: Single source of truth for data. ViewModel → Repository → Remote (API) + Local (Room). Repository decides whether to fetch from network or cache. Benefits: testability, separation of concerns, single responsibility.

## References

- [Android Developer Documentation](https://developer.android.com/docs)
