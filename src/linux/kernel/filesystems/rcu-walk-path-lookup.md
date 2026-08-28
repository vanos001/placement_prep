# RCU-Walk Pathname Lookup

> A path lookup is the hottest metadata operation the kernel performs —
> every `open`, `stat`, and `exec` walks a string component by component
> through the dcache. Taking a lock or even a reference count per
> component would put the dcache's cache lines on the global bounce list
> (see [false sharing](../../../os/advanced/false-sharing.md)). Linux's
> answer, merged in 3.0-era work and documented in
> `Documentation/filesystems/path-lookup.rst`, is RCU-walk: walk the tree
> with *no atomic increments at all*, validating what you saw with
> sequence counters, and fall back to the slow path only when something
> changes underneath you. This page covers [the dentry
> structure](./dentry.md) and goes one level deeper: the walking
> protocols themselves.

## Two Protocols, One Fast Path

`link_path_walk()` runs in one of two modes, selected per lookup:

```text
 REF-walk (slow, correct-under-anything)
   per component: take parent's i_rwsem (or at least d_lock),
                  dget() reference, dput() at the end
   atomic ops:    2+ per component
   can:           sleep (network fs, realloc), block on renames

 RCU-walk (fast, optimistic)
   per component: rcu_read_lock held once for the whole walk,
                  read d_seq before/after each dereference,
                  verify nothing changed at the end
   atomic ops:    0 in the common case
   cannot:        sleep, take mutexes, run ->d_revalidate that sleeps
                  -> on any such need: unlazy_walk() drops to REF-walk
```

The design philosophy: make the *common* case (static tree, single
thread of lookups, hot dcache) cost nothing but cache traffic, and
detect the rare race cheaply rather than prevent it.

## The d_seq Discipline

Every dentry carries a `seqcount_spinlock_t d_seq` (see
[dentry.md](./dentry.md) for the struct). A sequence counter is a
generation number incremented twice per modification (before and after
the change). A reader:

```c
seq = read_seqcount_begin(&dentry->d_seq);   // odd seq => retry loop
value = dentry->d_inode;                     // speculative read
if (read_seqcount_retry(&dentry->d_seq, seq))
    goto retry;                              // writer ran concurrently
```

The trick that makes lock-free walking possible: after checking
`read_seqcount_retry`, the reader *knows* no rename/unlink committed
during its window — so the pointer it read is stable for as long as the
underlying memory is RCU-protected (freeing is deferred by
`call_rcu`, not synchronous).

Walking `a/b/c` under RCU-walk therefore looks like:

```text
 1. rcu_read_lock()
 2. child = d_hash_lookup(parent, "a")        # no lock; into hlist_bl
 3. seq1 = read_seqcount_begin(parent->d_seq)
    ...validate parent->d_inode still dir, child->d_parent == parent...
    seq2 = read_seqcount_begin(child->d_seq)
 4. repeat for "b", "c"
 5. rcu_read_unlock()
```

`hlist_bl` (the nulls-bucket hash list) deserves a mention: its lock
is only taken by writers; readers traverse without it and use the
"nulls" marker to detect having landed in a different bucket chain
after a concurrent rehash.

## unlazy_walk: The Escape Hatch

RCU-walk cannot sleep or take references. The moment the walk needs
anything of the sort — a symlink whose `->get_link()` allocates, a
network filesystem needing an RPC to revalidate, `LOOKUP_FOLLOW`
through /proc magic links — it calls `unlazy_walk()`: take real
references on the components traversed so far, verify with `d_seq`
that they are still the dentries it thinks, and restart the remainder
in REF-walk mode. The invariant that makes this safe: you may *upgrade*
from optimistic to pessimistic mid-walk, never the reverse.

Failure is cheap by construction: the caller of `link_path_walk` only
sees `-ECHILD` and re-runs the same lookup with `LOOKUP_RCU` cleared.

## Renames: The Cross-Directory Problem

A rename can move a dentry between two directories, breaking the
"validate parent, then child" pattern — child and parent change in
separate sequence-counter updates, and a walker can see a torn pair.
The kernel's answer for cross-directory renames is a global
`rename_lock` seqcount (`rename_lock`): readers that need a consistent
*ancestor chain* (e.g. checking `d_parent` chains for loops or for
exported-filehandle resolution) take it in read mode and revalidate
the whole chain at once. Per-dentry `d_seq` covers the common
single-level validations; `rename_lock` covers the multi-level ones.

```text
 rename("a/x", "b/x") under RCU-walk reader:
   reader validates a->x at seq S_a            ok
   rename commits: x.d_parent: a -> b          (x->d_seq bumps twice)
   reader validates x->d_parent == a at S_x    RETRY (-ECHILD -> REF-walk)
```

## Symlinks and the Name Cache

- Fast symlinks (target fits in `d_iname`) are followed inline with no
  allocation, staying in RCU-walk.
- Slow symlinks require `->get_link()`; if it can sleep (page cache
  read, network fs), that is another `unlazy_walk()` trigger.
- Mount traversal: `LOOKUP_..` crossing into a mountpoint consults the
  mount hash under RCU as well; automount daemons force the lazy path.

## Why It Pays: A Cost Sketch

Per-component cost, common case (from the path-lookup.rst narrative):

```text
 REF-walk:  dget (atomic inc, shared line) + dput (atomic dec)
            + at least one d_lock acquisition attempt
 RCU-walk:  two seqcount reads (plain loads) + hash traversal
```

On an 8-socket box, a shared `d_lockref` is a bounce pad; RCU-walk
removes it from the lookup entirely. The remaining cache traffic is
the dentry and inode lines themselves — which the read-only walk keeps
in S state, shareable across all readers.

## Worked Demo: Sequence-Counter Validation

The demo implements the seqlock read protocol against a simulated
concurrent rename, showing (a) the reader that starts before the
rename must retry, and (b) a reader that completes its validation
window without a bump reads cleanly, and (c) what an unlazy_walk
fallback does.

```python
# d_seq (seqlock) semantics during a concurrent rename.
# seqlock: writer increments counter before and after each change;
# reader retries if it saw an odd counter or the counter changed.

class Seqlock:
    def __init__(self):
        self.seq = 0
        self.value = None

    def write(self, value):
        self.seq += 1                      # odd: writers active
        assert self.seq % 2 == 1
        self.value = value                 # the actual mutation
        self.seq += 1                      # even: writers done

    def read(self, ev_writer):
        """ev_writer: a callable scheduled between our two reads."""
        while True:
            s1 = self.seq
            if s1 % 2 == 1:                # writer mid-flight
                continue
            val = self.value               # speculative read
            ev_writer()                    # possibly mutates now
            if self.seq == s1:             # stable window -> commit
                return val, True
            return val, False              # torn: retry needed

d = Seqlock()
d.value = {"parent": "dir_a"}

# Case 1: reader's window closes cleanly
val, stable = d.read(lambda: None)
print("case1:", val, "stable=", stable)

# Case 2: rename commits inside the reader's window
def rename():
    d.write({"parent": "dir_b"})
val, stable = d.read(rename)
print("case2:", val, "stable=", stable, "-> RCU-walk returns -ECHILD")

# Case 3: unlazy_walk fallback re-runs in REF-walk mode
if not stable:
    val = d.value                          # now under real locks
    print("case3: REF-walk reads", val)
```

Real output:

```text
case1: {'parent': 'dir_a'} stable= True
case2: {'parent': 'dir_a'} stable= False -> RCU-walk returns -ECHILD
case3: REF-walk reads {'parent': 'dir_b'}
```

Case 2 is the interesting line: the reader *returns the value it
speculatively read* (`dir_a`) but marks it torn — it does not silently
mix old and new state. The kernel's version re-reads instead of
returning, but the contract is identical: a validation failure costs a
retry, never a wrong answer.

## Interview Questions

1. Why can RCU-walk not simply take a reference per component instead
   of using `d_seq`? (That's REF-walk — the atomic inc/dec per
   component is exactly the shared-line traffic RCU-walk exists to
   avoid.)
2. What guarantees that a dentry freed by a rename is not unmapped
   while an RCU-walk reader still holds a pointer? (`call_rcu`-deferred
   free — readers hold `rcu_read_lock` for the whole walk.)
3. Why is a *sequence counter* used rather than a per-dentry rwlock for
   validation? (Readers never write the counter, so it stays on the
   reader's line in S state; a rwlock would bounce on every lookup.)
4. When is `unlazy_walk()` mandatory even with a hot dcache?
   (Sleeping work: network-fs revalidation, allocating symlink
   resolution, automount.)
5. What breaks if the kernel validated only `child->d_parent` and not
   the parent's own seq during a cross-directory rename? (A torn
   ancestor chain — the classic race `rename_lock` exists for.)

## References

- Kernel documentation, `Documentation/filesystems/path-lookup.rst`
  (*Path walking*): https://docs.kernel.org/filesystems/path-lookup.html
  (probed 200)
- Brown, N. *Pathwalking* LWN series (the author's own walk-through):
  part 1 https://lwn.net/Articles/649115/ (probed 200)
- Linux source: `fs/namei.c` (`link_path_walk`, `unlazy_walk`,
  `legitimize_path`), `fs/dcache.c` (`__d_lookup_rcu`).
  https://github.com/torvalds/linux/blob/master/fs/namei.c (probed 200)
- Boyd-Wickizer, A., Clements, A. T., Mao, Y., Pesterev, A., Kaashoek,
  M. F., Morris, R., Zeldovich, N. *An Analysis of Linux Scalability to
  Many Cores*. OSDI '10 — quantifies the VFS/dcache/RCU scaling walls
  (incl. the lookups-per-second ceiling RCU-walk raises).
  https://pdos.csail.mit.edu/papers/linux:osdi10.pdf (probed 200)
- LWN: *Read-copy-update* background for the guarantee model:
  https://lwn.net/Articles/262464/ (probed 200)

## Cross-References

- [Dentry](./dentry.md) — the data structure this page's protocols
  protect.
- [RCU](../sync/rcu.md) — the memory-reclamation model RCU-walk rides
  on.
- [False sharing](../../../os/advanced/false-sharing.md) — why per-component
  atomics were the enemy all along.
