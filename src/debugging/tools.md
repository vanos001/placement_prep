# Debugging Tools

Effective debugging requires the right tools for the right layer. This guide covers the essential debugging tools across native code, interpreted languages, browsers, and systems programming.

## Native Debuggers: GDB and LLDB

### GDB (GNU Debugger)

The standard debugger for C/C++ (and other compiled languages) on Linux.

**Essential Commands:**

| Command | Purpose |
|---------|---------|
| `break main` / `break file.c:42` | Set breakpoint at function or line |
| `run` / `run <args>` | Start program (optionally with arguments) |
| `next` (n) | Step over (execute line, do not enter functions) |
| `step` (s) | Step into (enter functions) |
| `continue` (c) | Run until next breakpoint |
| `print var` / `print &var` | Print variable value or address |
| `backtrace` (bt) | Show call stack |
| `frame N` | Select stack frame N |
| `info locals` | Show local variables in current frame |
| `info args` | Show function arguments |
| `watch var` | Break when variable value changes |
| `rwatch var` | Break when variable is read |
| `set var = value` | Change variable value |
| `finish` | Execute until current function returns |
| `thread apply all bt` | Backtrace all threads |
| `catch throw` | Break when C++ exception is thrown |

**Conditional Breakpoints:**
```
(gdb) break file.c:100 if x > 1000
```

**Starting GDB with a core dump:**
```bash
gdb ./myapp core
```

### LLDB

The default debugger on macOS and often used with the LLVM toolchain.

| GDB Command | LLDB Equivalent |
|------------|-----------------|
| `break main` | `breakpoint set --name main` or `b main` |
| `run` | `process launch` or `run` |
| `next` | `thread step-over` or `n` |
| `step` | `thread step-in` or `s` |
| `backtrace` | `thread backtrace` or `bt` |
| `print var` | `frame variable var` or `p var` |
| `continue` | `process continue` or `c` |

---

## Memory Debuggers: Valgrind

### Memcheck (Memory Error Detection)
Detects memory leaks, use-after-free, out-of-bounds access, uninitialized reads.

```bash
valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./myapp
```

**Key Output Flags:**
- `definitely lost`: Memory leaked with no pointer to it.
- `indirectly lost`: Memory pointed to by a definitely lost block.
- `possibly lost`: Memory that might be leaked (e.g., pointer to interior of block).
- `still reachable`: Memory still reachable at exit (often false positive for global state).

### Callgrind (Profiling)
Cache and branch prediction profiling.

```bash
valgrind --tool=callgrind ./myapp
callgrind_annotate callgrind.out.<pid>
# Or use KCachegrind for GUI visualization
```

### Cachegrind
Simulates cache behavior to identify cache misses.

```bash
valgrind --tool=cachegrind ./myapp
cg_annotate cachegrind.out.<pid>
```

---

## Sanitizers

Compiler-instrumented memory and undefined behavior detection. Faster than Valgrind with lower overhead.

### AddressSanitizer (ASan)
Detects memory errors: buffer overflows, use-after-free, memory leaks, stack buffer overflows.

```bash
# Compile with:
gcc -g -fsanitize=address -fno-omit-frame-pointer -O1 myapp.c -o myapp
# Or for CMake:
-DCMAKE_C_FLAGS="-fsanitize=address" -DCMAKE_LINKER_FLAGS="-fsanitize=address"
```

### UndefinedBehaviorSanitizer (UBSan)
Detects undefined behavior: integer overflow, null pointer dereference, shift overflow, alignment violations.

```bash
gcc -g -fsanitize=undefined myapp.c -o myapp
```

### ThreadSanitizer (TSan)
Detects data races and deadlocks in multi-threaded programs.

```bash
gcc -g -fsanitize=thread myapp.c -o myapp
```

### MemorySanitizer (MSan)
Detects use of uninitialized memory.

```bash
clang -g -fsanitize=memory myapp.c -o myapp
```

**Combining Sanitizers:**
ASan and UBSan can be combined: `-fsanitize=address,undefined`. TSan must be used alone (incompatible with ASan).

---

## Browser DevTools

### Sources Panel
- **Breakpoints**: Line breakpoints, conditional breakpoints, logpoints.
- **Stepping**: Step over, into, out.
- **Watch expressions**: Monitor specific variables.
- **Call stack**: Inspect the full call chain.
- **Scope**: Local, closure, global variables.

### Network Panel
- **Waterfall view**: Visualize request timing (DNS, TCP, TLS, TTFB, download).
- **Filtering**: By type, status code, URL pattern.
- **Throttling**: Simulate slow networks (3G, offline).
- **HAR export**: Capture and analyze request data.
- **Blocking requests**: Identify render-blocking resources.

### Performance Panel
- **Flame chart**: CPU usage over time.
- **Main thread activity**: Identify long tasks (>50ms).
- **Screenshots**: Correlate visual changes with JS execution.
- **Bottom-up analysis**: Find the most expensive functions.

### Memory Panel
- **Heap snapshot**: Identify detached DOM nodes, object retention.
- **Allocation timeline**: Track memory allocations over time.
- **Comparison**: Compare snapshots to find leaked objects.
- **Three snapshot technique**: Take baseline → perform action → take snapshot → clean up → take snapshot. Objects in snapshot 2 but not 3 are leaked.

---

## System-Level Tools

### strace
Trace system calls and signals. Essential for understanding what a program does at the OS level.

```bash
# Trace all syscalls:
strace ./myapp

# Trace specific syscalls:
strace -e trace=open,read,write ./myapp

# Trace a running process:
strace -p <pid>

# Filter by duration (find slow syscalls):
strace -T ./myapp

# Count syscalls (profiling):
strace -c ./myapp
```

### ltrace
Trace library calls (dynamic library function calls).

```bash
ltrace ./myapp
ltrace -e strlen,strcmp ./myapp   # Trace specific functions
```

### tcpdump
Capture and analyze network packets at the packet level.

```bash
# Capture all traffic on eth0:
tcpdump -i eth0

# Capture HTTP traffic:
tcpdump -i eth0 -A -s 0 'tcp port 80'

# Capture traffic to/from a specific host:
tcpdump host 192.168.1.100

# Write to pcap file for Wireshark:
tcpdump -w capture.pcap -i eth0
```

### Wireshark
GUI-based network protocol analyzer. Opens pcap files from tcpdump or captures live traffic. Provides protocol-level decoding for hundreds of protocols.

---

## Core Dumps

### Enabling Core Dumps
```bash
# Check current limit:
ulimit -c

# Enable unlimited core dumps:
ulimit -c unlimited

# Set core dump pattern (where to write):
echo "/tmp/core.%e.%p.%t" | sudo tee /proc/sys/kernel/core_pattern

# Persistent setting:
echo "* soft core unlimited" | sudo tee -a /etc/security/limits.conf
```

### Analyzing Core Dumps
```bash
gdb ./myapp /tmp/core.myapp.12345.1700000000
# Inside GDB:
(gdb) backtrace full    # Full backtrace with local variables
(gdb) info registers     # CPU register state
(gdb) thread apply all bt  # All threads
```

---

## Language-Specific Debuggers

### Python: pdb and breakpoint()
```python
# Programmatic breakpoint (Python 3.7+):
def process(data):
    breakpoint()  # Drops into pdb
    result = transform(data)
    return result

# Command-line:
python -m pdb myscript.py

# Post-mortem:
python -m pdb myscript.py  # After exception, pdb drops you at the point of failure
import pdb; pdb.pm()        # Post-mortem on last exception
```

**Key pdb commands:** `n` (next), `s` (step), `c` (continue), `p var` (print), `l` (list), `w` (where/backtrace), `b func` (break), `q` (quit).

### Java: jdb and JFR
```bash
# jdb - command-line debugger:
jdb -attach <port>    # Connect to a JVM started with -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005

# Java Flight Recorder (JFR) - production profiling:
jcmd <pid> JFR.start name=recording settings=profile duration=60s filename=recording.jfr
jcmd <pid> JFR.dump recording=recording filename=recording.jfr
# Analyze with jvisualvm or Java Mission Control

# Thread dump:
jcmd <pid> Thread.print
kill -3 <pid>  # Sends SIGQUIT to Java process
```

---

## Interview Questions

1. **"How would you debug a memory leak in a C++ application?"**
   Run under Valgrind with `--leak-check=full`. If the leak only occurs in production, use AddressSanitizer with a custom allocator that tracks allocations, or use heap profiling (`gperftools` / `tcmalloc`). Review the leak summary to identify allocation sites.

2. **"A web page is slow. How do you diagnose the cause?"**
   Open Chrome DevTools: Network tab to check for slow requests or render-blocking resources, Performance tab to identify long tasks on the main thread, Memory tab for garbage collection pauses. Lighthouse audit for a comprehensive report.

3. **"How would you debug a segfault in production?"**
   Ensure core dumps are enabled. When the crash occurs, load the core dump in GDB with the binary and debug symbols (`backtrace full`, inspect registers and variables). If the crash is rare, use AddressSanitizer in a canary environment and monitor for the error report.

4. **"strace shows your program is spending most time in `futex`. What does that mean?"**
   The program is blocked waiting on a lock or condition variable. This indicates a synchronization issue—either contention on a shared lock, a deadlock, or threads waiting on a condition that is never signaled.

5. **"When would you use ThreadSanitizer instead of a traditional debugger?"**
   When debugging intermittent data races that are timing-dependent and hard to reproduce. TSan instruments the program at compile time to detect unsynchronized access to shared memory, catching races that may only manifest once in thousands of runs.
