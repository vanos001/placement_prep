# strace and ltrace — System Call and Library Call Tracing

## Introduction

`strace` and `ltrace` are diagnostic tools that intercept and record system calls and
library calls made by a process. They are indispensable for understanding what a program
actually does at the system interface level, diagnosing failures, and reverse-engineering
program behavior without source code.

- **strace** intercepts system calls (the interface between user space and the kernel)
- **ltrace** intercepts library calls (the interface between your code and shared libraries like libc)

These tools are non-intrusive — they use `ptrace(2)` to attach to the target process and
log calls without modifying the program's behavior.

## strace — System Call Tracing

### How strace Works

strace attaches to a process using `ptrace(2)` (the same mechanism GDB uses). The kernel
delivers a `SIGTRAP` signal to the tracer before and after each system call, allowing strace
to inspect arguments and return values.

```
┌──────────┐    ptrace     ┌──────────────┐
│  strace  │◄─────────────►│ Target Process│
│ (tracer) │               │  (tracee)     │
└──────────┘               └──────┬───────┘
                                  │ syscall
                                  ▼
                           ┌──────────────┐
                           │    Kernel     │
                           │ (syscall handler)│
                           └──────────────┘

Timeline for each syscall:
  1. Process enters syscall → kernel notifies strace (SIGTRAP)
  2. strace reads syscall number + arguments from registers
  3. Kernel executes syscall
  4. Kernel notifies strace again on return
  5. strace reads return value and errno
```

### Basic Usage

```bash
# Trace a command
strace ls -la /tmp

# Attach to a running process
strace -p 1234

# Trace and follow child processes (fork/clone)
strace -f ./myprogram

# Trace only specific system calls
strace -e trace=open,read,write ./myprogram

# Write output to a file
strace -o trace.log ./myprogram

# Include timestamps
strace -t ./myprogram               # HH:MM:SS
strace -tt ./myprogram              # HH:MM:SS.microseconds
strace -ttt ./myprogram             # Unix timestamp with microseconds

# Show time spent in each syscall
strace -T ./myprogram

# Show time relative to previous syscall
strace -r ./myprogram

# Trace with string length limits
strace -s 1024 ./myprogram          # Max 1024 chars per string
strace -v ./myprogram               # No abbreviation (verbose)
```

### Example Output

```
$ strace -e trace=open,read,write cat /etc/hostname
open("/etc/hostname", O_RDONLY)        = 3
read(3, "myserver\n", 4096)            = 9
write(1, "myserver\n", 9)              = 9
close(3)                               = 0
+++ exited with 0 +++
```

Each line shows:
- The system call name and arguments
- The return value (after `=`)
- On error: return value and errno name (e.g., `ENOENT`)

### Filtering System Calls

The `-e trace=` option is powerful for focusing on specific categories:

```bash
# Filter by category
strace -e trace=file ./myprogram     # File-related: open, stat, chmod, ...
strace -e trace=network ./myprogram  # Network: socket, connect, bind, ...
strace -e trace=process ./myprogram  # Process: fork, exec, exit, ...
strace -e trace=memory ./myprogram   # Memory: mmap, brk, mprotect, ...
strace -e trace=signal ./myprogram   # Signals: signal, kill, sigaction, ...
strace -e trace=ipc ./myprogram      # IPC: shmget, semop, msgget, ...
strace -e trace=desc ./myprogram     # File descriptors: read, write, close, ...
strace -e trace=%clock ./myprogram   # Clock: clock_gettime, nanosleep, ...

# Filter by specific calls (comma-separated)
strace -e trace=open,openat,close ./myprogram

# Exclude specific calls (prefix with !)
strace -e trace=!write ./myprogram   # Everything except write

# Multiple filters (combine with comma)
strace -e trace=file,network ./myprogram
```

### Statistics Mode

`strace -c` produces a summary table instead of per-call output — invaluable for
performance analysis:

```bash
$ strace -c ./myprogram
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 45.00    0.125000          12     10000           read
 25.00    0.069444          69      1000           open
 15.00    0.041666          41      1000           close
 10.00    0.027777          27      1000           fstat
  5.00    0.013888          13      1000         2 write
------ ----------- ----------- --------- --------- ----------------
100.00    0.277775                 14002         2 total
```

Columns:
- **% time**: Percentage of total time spent in this syscall
- **seconds**: Total time in this syscall (seconds)
- **usecs/call**: Average time per call (microseconds)
- **calls**: Number of times this syscall was invoked
- **errors**: Number of calls that returned an error

### Following Child Processes and Threads

```bash
# Follow forks (separate processes)
strace -f ./myprogram

# Follow forks but output to separate files
strace -ff -o trace ./myprogram      # Creates trace.1234, trace.1235, ...

# Trace threads (clone with CLONE_THREAD)
strace -f -ff ./myprogram

# Attach to a specific thread
strace -p 1234 -f                    # Attach and follow children
```

### Advanced strace Features

#### Filtering by Path

```bash
# Trace only calls involving a specific path
strace -P /etc/passwd ./myprogram

# Trace only calls involving /tmp
strace -P /tmp ./myprogram
```

#### Counting Calls

```bash
# Count syscalls (no output, just summary)
strace -c -S calls ./myprogram       # Sort by call count

# Sort by time
strace -c -S time ./myprogram

# Combine with filtering
strace -c -e trace=file ./myprogram
```

#### Decode All Flags

```bash
# Decode all flags (not just common ones)
strace -e read=all ./myprogram       # Full decode of read/write buffers
strace -e write=all ./myprogram
strace -e signal=all ./myprogram     # Full signal info
strace -e read=4096 ./myprogram      # Show up to 4096 bytes of data
```

#### Injecting Failures

strace can inject errors to test error-handling code:

```bash
# Fail open() with ENOENT 30% of the time
strace -e inject=open:error=ENOENT:30 ./myprogram

# Delay read() by 100ms
strace -e inject=read:delay_enter=100 ./myprogram

# Fail the 5th call to write with EIO
strace -e inject=write:error=EIO:when=5+2 ./myprogram  # Every 2nd call starting at 5th
```

### strace Output Interpretation

#### Common Return Values

```
open("/nonexistent", O_RDONLY) = -1 ENOENT (No such file or directory)
open("/etc/passwd", O_RDONLY)  = 3
read(3, "root:x:0:0:root:/root:/bin/bash\n"..., 4096) = 1234
mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f1234560000
close(3)                        = 0
exit_group(0)                   = ?
+++ exited with 0 +++
```

#### Signal Handling in Output

```
strace: Process 1234 attached
--- SIGINT {si_signo=SIGINT, si_code=SI_USER, si_pid=1235, si_uid=1000} ---
+++ killed by SIGINT +++
```

### Practical strace Recipes

#### Debug "File Not Found"

```bash
$ strace -e trace=open,openat,access,stat ./myprogram 2>&1 | grep ENOENT
openat(AT_FDCWD, "/lib/libfoo.so", O_RDONLY|O_CLOEXEC) = -1 ENOENT (No such file or directory)
```

#### Find What Files a Program Touches

```bash
$ strace -e trace=file -f ./myprogram 2>&1 | grep -v ENOENT
open("/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
open("/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
open("./config.ini", O_RDONLY) = 3
stat("./data/output.bin", {st_mode=S_IFREG|0644, st_size=1024, ...}) = 0
open("./data/output.bin", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 4
```

#### Debug Network Connections

```bash
$ strace -e trace=network -f ./myprogram 2>&1
socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = 3
connect(3, {sa_family=AF_INET, sin_port=htons(80), sin_addr=inet_addr("93.184.216.34")}, 16) = 0
sendto(3, "GET / HTTP/1.1\r\nHost: example.co"..., 78, MSG_NOSIGNAL, NULL, 0) = 78
recvfrom(3, "HTTP/1.1 200 OK\r\nContent-Type: t"..., 4096, 0, NULL, NULL) = 1234
```

#### Profile System Call Overhead

```bash
$ strace -c -S time ./myprogram 2>&1 | tail -20
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 50.00    0.500000         500      1000           nanosleep
 30.00    0.300000           0    100000           read
 15.00    0.150000           0    100000           write
  5.00    0.050000          50      1000           mmap
------ ----------- ----------- --------- --------- ----------------
100.00    1.000000                202000         0 total
```

## ltrace — Library Call Tracing

### How ltrace Works

While strace intercepts system calls (kernel interface), ltrace intercepts calls to
shared libraries (user-space interface). It works by modifying the Procedure Linkage
Table (PLT) entries for the target process, replacing them with breakpoints.

```
Program calls printf()
       │
       ▼
┌──────────────┐
│ PLT entry    │  ← ltrace sets breakpoint here
│ for printf   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ GOT entry    │  ← resolved address of printf in libc
│ for printf   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ libc printf()│  ← actual library function
└──────────────┘
```

### Basic Usage

```bash
# Trace library calls
ltrace ./myprogram

# Attach to a running process
ltrace -p 1234

# Follow child processes
ltrace -f ./myprogram

# Write output to file
ltrace -o trace.log ./myprogram

# Show call counts
ltrace -c ./myprogram

# Show timestamps
ltrace -t ./myprogram               # HH:MM:SS
ltrace -tt ./myprogram              # HH:MM:SS.microseconds
ltrace -ttt ./myprogram             # Unix timestamp

# Show time spent in each call
ltrace -T ./myprogram

# Verbose (show structures)
ltrace -v ./myprogram
```

### Example Output

```
$ ltrace ./myprogram
__libc_start_main(0x4011a6, 1, 0x7ffd4a3b5a88, 0x401230 <unfinished ...>
printf("Enter your name: "Enter your name: )                                    = 17
fgets(stdin)                                                                    = 0x7ffd4a3b5900
strlen("Alice\n")                                                               = 6
malloc(6)                                                                       = 0x55a1234
memcpy(0x55a1234, "Alice\n", 6)                                                 = 0x55a1234
printf("Hello, %s!\n", "Alice")Hello, Alice!
= 14
free(0x55a1234)                                                                 = <void>
+++ exited (status 0) +++
```

### Filtering Library Calls

```bash
# Trace only specific functions
ltrace -e malloc,free ./myprogram

# Trace only string functions
ltrace -e strlen+strcpy+strcat+strcmp ./myprogram

# Exclude specific functions
ltrace -e !malloc ./myprogram

# Trace libc only (default)
ltrace -l libc.so.6 ./myprogram

# Trace all libraries
ltrace -L ./myprogram

# Trace a specific library
ltrace -l libpthread.so.0 ./myprogram
```

### ltrace Statistics

```bash
$ ltrace -c ./myprogram
% time     seconds  usecs/call     calls      function
------ ----------- ----------- --------- --------------------
 40.00    0.040000          40      1000 printf
 20.00    0.020000          20      1000 strlen
 15.00    0.015000          15      1000 strcmp
 10.00    0.010000          10      1000 malloc
 10.00    0.010000          10      1000 free
  5.00    0.005000           5      1000 memcpy
------ ----------- ----------- --------- --------------------
100.00    0.100000                  6000 total
```

### Decoding Arguments and Return Values

```bash
# Show pointer contents (dereference)
ltrace -e malloc+free -x '*' ./myprogram

# Show file descriptor contents
ltrace -e read+write -e read+write='@%rdi' ./myprogram

# Show array contents
ltrace -e sprintf -x '*' ./myprogram

# Show structures
ltrace -v ./myprogram
```

## strace vs ltrace: When to Use Which

```
┌─────────────────────────────────────────────────────┐
│                    User Space                        │
│                                                     │
│   Application Code                                  │
│       │                                             │
│       ├── ltrace intercepts here ──► Library Calls  │
│       │   (malloc, printf, strlen, ...)             │
│       │                                             │
│       ▼                                             │
│   C Library (glibc)                                 │
│       │                                             │
│       ├── strace intercepts here ──► System Calls   │
│       │   (open, read, write, mmap, ...)            │
│       │                                             │
└───────┼─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                    Kernel                            │
│   (syscall implementation)                           │
└─────────────────────────────────────────────────────┘
```

| Feature | strace | ltrace |
|---------|--------|--------|
| Intercepts | System calls | Library calls |
| Interface | User↔Kernel | User↔Library |
| Overhead | Higher (kernel transitions) | Lower |
| Availability | Always works | Requires PLT |
| Static binaries | Yes | No (needs shared libs) |
| Useful for | I/O debugging, permissions, networking | Memory leaks, logic bugs |
| Works on | Any ELF binary | Dynamically linked only |

### Combining Both

```bash
# Run both simultaneously (useful but noisy)
strace -o strace.log -f ./myprogram &
ltrace -o ltrace.log -f ./myprogram &
wait
```

## Advanced Techniques

### Tracing with Time Analysis

```bash
# strace: find slow syscalls
strace -T -e trace=all ./myprogram 2>&1 | sort -t= -k2 -n -r | head -20

# strace: show cumulative time
strace -c ./myprogram

# ltrace: find slow library calls
ltrace -T ./myprogram 2>&1 | sort -t= -k2 -n -r | head -20
```

### Tracing Multi-Process Applications

```bash
# strace: follow all children, separate files
strace -ff -o /tmp/trace ./myserver

# Then analyze
for f in /tmp/trace.*; do
    echo "=== $f ==="
    strace -c < "$f" 2>/dev/null || cat "$f" | grep -c "syscall"
done

# ltrace: follow children
ltrace -f -o /tmp/lt ./myprogram
```

### Security Analysis

```bash
# Find all files opened by a program
strace -e trace=open,openat -f ./myprogram 2>&1 | grep -v ENOENT

# Find all network connections
strace -e trace=connect,bind,accept -f ./myprogram 2>&1

# Find all signal handling
strace -e trace=signal -f ./myprogram 2>&1

# Find privilege operations
strace -e trace=setuid,setgid,chown,chmod -f ./myprogram 2>&1
```

### Debugging Docker Containers

```bash
# strace inside a container
docker run --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
    myimage strace ./myprogram

# Or nsenter into a running container
PID=$(docker inspect --format '{{.State.Pid}}' mycontainer)
sudo nsenter -t $PID -m -u -i -n -p -- strace -p 1
```

## Limitations and Caveats

1. **ptrace overhead**: Both tools use ptrace, which adds significant overhead
   (2-100x slowdown depending on syscall frequency)
2. **Race conditions**: Tracing can alter timing, potentially masking or creating
   race conditions (observer effect)
3. **Seccomp restrictions**: Containers may block ptrace; need `SYS_PTRACE` capability
4. **Static binaries**: ltrace doesn't work on statically linked binaries
5. **Optimized code**: Inlined functions won't appear in ltrace output
6. **vDSO**: Calls through the vDSO (e.g., `gettimeofday`) bypass both tools
7. **Signal delivery**: strace alters signal delivery timing

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [strace(1) man page](https://man7.org/linux/man-pages/man1/strace.1.html)
- [ltrace(1) man page](https://man7.org/linux/man-pages/man1/ltrace.1.html)
- [strace GitHub](https://github.com/strace/strace)
- [ltrace GitHub](https://github.com/dkogan/ltrace)
- [Brendan Gregg's strace page](https://www.brendangregg.com/strace.html)

## Related Topics

- [GDB](./gdb.md) — Source-level debugging with breakpoints and watchpoints
- [Perf](./perf.md) — Low-overhead performance profiling
- [eBPF](./ebpf.md) — Efficient kernel-level tracing without ptrace overhead

## Practical Debugging Scenarios

### Scenario 1: Application Won't Start

```bash
# "Command not found" or "No such file" errors
strace -e trace=open,openat,access,stat ./myapp 2>&1 | grep -E 'ENOENT|EACCES'

# Missing shared libraries
strace -e trace=open,openat ./myapp 2>&1 | grep '\.so'
# Look for ENOENT on .so files — indicates missing library

# Environment issues
strace -e trace=execve ./myapp 2>&1
# Shows exactly what's being executed and with what environment
```

### Scenario 2: Application Hangs

```bash
# Find where the hang is (what syscall is blocking)
strace -p <PID> -T
# Shows the current syscall and how long it's been running

# Common blocking calls:
# - futex(..., FUTEX_WAIT, ...) — waiting on a lock
# - read(0, ...) — waiting for stdin input
# - poll/select/epoll — waiting for I/O
# - recvfrom — waiting for network data

# Trace with timestamps to find the hang point
strace -p <PID> -tt -T 2>&1 | tail -50
# Look for the last syscall before the hang
```

### Scenario 3: Permission Denied

```bash
# Find what permission is being checked
strace -e trace=open,openat,access,stat,faccessat ./myapp 2>&1 | grep EACCES

# Check what UID/GID the process runs as
strace -e trace=setuid,setgid,setreuid,setregid ./myapp 2>&1

# SELinux/AppArmor denials show as EACCES too
# Check audit logs: ausearch -m AVC
```

### Scenario 4: Slow File I/O

```bash
# Profile I/O time
strace -T -e trace=read,write,open,openat,close ./myapp 2>&1 | \
    awk -F'[<>]' '{print $2, $0}' | sort -rn | head -20

# Count I/O operations
strace -c -e trace=read,write ./myapp 2>&1
# High call count with small read/write sizes = inefficient I/O pattern

# Show read/write sizes
strace -e trace=read,write ./myapp 2>&1 | head -50
# Look for many small reads (should use buffered I/O or larger buffers)
```

### Scenario 5: Network Connection Issues

```bash
# Trace network syscalls
strace -e trace=network -f ./myapp 2>&1

# Common patterns:
# connect() returns ECONNREFUSED — server not listening
# connect() returns ETIMEDOUT — firewall or routing issue
# connect() returns ENETUNREACH — network misconfiguration
# sendto() returns EPIPE — connection closed by peer

# DNS resolution issues
strace -e trace=open,openat,connect,sendto,recvfrom ./myapp 2>&1 | \
    grep -E '(resolv|nameserver|dns)'
```

### Scenario 6: Memory Issues

```bash
# Trace memory allocation
strace -e trace=mmap,brk,mprotect,munmap ./myapp 2>&1 | tail -50

# Count allocations
strace -c -e trace=mmap,brk ./myapp 2>&1
# Excessive mmap/munmap calls = memory fragmentation

# Show allocation sizes
strace -e trace=mmap ./myapp 2>&1 | head -20
# mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f...
```

## strace Alternatives and Complements

### perf trace (kernel-native tracing)

`perf trace` uses the kernel's perf infrastructure instead of ptrace, resulting
in significantly lower overhead:

```bash
# Basic usage (similar to strace)
sudo perf trace ./myprogram
sudo perf trace -p <PID>

# Much lower overhead than strace
sudo perf trace -e read,write ./myprogram

# System-wide tracing
sudo perf trace -a -- sleep 5

# With call stacks
sudo perf trace -e read --call-graph dwarf -p <PID>
```

**Comparison: strace vs perf trace**

| Feature | strace | perf trace |
|---------|--------|-----------|
| Overhead | High (ptrace) | Low (kernel perf) |
| System-wide | No (per-process) | Yes (`-a`) |
| Call stacks | Limited | Full (with `-g`) |
| Container support | Needs SYS_PTRACE | Works with perf events |
| Output | Text | Text (customizable) |

### bpftrace for syscall tracing

```bash
# Trace open() syscalls with bpftrace
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Histogram of read() sizes
sudo bpftrace -e 'tracepoint:syscalls:sys_exit_read /args->ret > 0/ { @bytes = hist(args->ret); }'

# Count syscalls per process
sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
```

### ltrace Alternatives

```bash
# For modern systems, consider:

# 1. LD_DEBUG — dynamic linker debugging
LD_DEBUG=all ./myprogram 2>&1 | head -50
LD_DEBUG=bindings ./myprogram 2>&1  # Show library bindings

# 2. ltrace with filtering
ltrace -e 'malloc+free' -e 'strlen+strcmp' ./myprogram

# 3. eBPF uprobes for specific library functions
sudo bpftrace -e 'uprobe:/lib/x86_64-linux-gnu/libc.so.6:malloc { printf("malloc(%d)\n", arg0); }'
```

## strace Output Analysis Patterns

### Recognizing Common Patterns

```bash
# Pattern: Repeated open/close of same file
# Indicates: missing file caching or resource leak
strace -e trace=open,openat,close ./myapp 2>&1 | sort | uniq -c | sort -rn | head

# Pattern: Many small read() calls
# Indicates: unbuffered I/O
strace -e trace=read ./myapp 2>&1 | awk -F'[()]' '{print $2}' | sort | uniq -c | sort -rn

# Pattern: Excessive futex() calls
# Indicates: lock contention
strace -c ./myapp 2>&1 | grep futex

# Pattern: Many gettimeofday() calls
# Indicates: excessive time checking (common in logging)
strace -c ./myapp 2>&1 | grep -E 'clock_gettime|gettimeofday'
```

### Automated strace Analysis

```bash
#!/bin/bash
# strace-analyze.sh — Quick analysis of strace output

TRACE_FILE=$1

echo "=== Syscall frequency ==="
awk '{print $1}' "$TRACE_FILE" | sort | uniq -c | sort -rn | head -20

echo ""
echo "=== Error frequency ==="
grep -oE '= -[A-Z]+' "$TRACE_FILE" | sort | uniq -c | sort -rn | head -10

echo ""
echo "=== Slowest syscalls ==="
grep -oE '<[0-9.]+>' "$TRACE_FILE" | tr -d '<>' | sort -rn | head -10

echo ""
echo "=== File operations ==="
grep -E 'open|openat' "$TRACE_FILE" | grep -v ENOENT | head -20
```

## Performance Impact of strace

strace adds significant overhead because ptrace requires two context switches
per syscall (entry and exit):

| Workload Type | Overhead Factor | Notes |
|---------------|----------------|-------|
| I/O-heavy (many syscalls) | 10-100x slower | Each syscall pays ptrace cost |
| CPU-heavy (few syscalls) | 1-2x slower | Minimal impact |
| Mixed | 2-10x slower | Depends on syscall frequency |

**Recommendations:**
- Use `perf trace` or `bpftrace` for production tracing (much lower overhead)
- Use `strace -c` (summary mode) when possible — lower overhead than full output
- Use `-e filter` to trace only relevant syscalls
- For long-running traces, write to file (`-o trace.log`) instead of stderr
- [ftrace](./ftrace.md) — Kernel function tracing
