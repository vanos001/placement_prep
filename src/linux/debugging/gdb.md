# GDB — The GNU Debugger

## Introduction

GDB (GNU Debugger) is the standard debugger for Linux and many other Unix-like systems.
It allows you to inspect what is happening inside a program while it executes, or what a
program was doing at the moment it crashed. GDB supports C, C++, Rust, Go, Fortran,
Assembly, and many other languages. It can debug local processes, attach to running
processes, analyze core dumps, and perform remote debugging over serial lines or networks.

GDB is an essential tool in every systems programmer's toolkit. Understanding it deeply
means the difference between staring at a crash for hours and finding the root cause in
minutes.

## Core Concepts

### What GDB Can Do

- Start your program, specifying arguments and environment
- Stop at specific locations (breakpoints) or when conditions are met
- Examine memory, registers, and variable values
- Change variables and memory on the fly to experiment with fixes
- Trace program execution step by step (source line or instruction level)
- Debug programs that fork, creating separate parent/child debugging sessions
- Record execution and replay it deterministically

### How GDB Works Internally

GDB controls the target process through the `ptrace(2)` system call on Linux.
When you set a breakpoint, GDB replaces the instruction at that address with a
trap instruction (`int 3` on x86). When the trap fires, GDB catches the signal,
restores the original instruction, and presents the breakpoint to the user.

```
┌──────────┐    ptrace()    ┌──────────────┐
│   GDB    │◄──────────────►│ Target Process│
│ (parent) │                │   (child)     │
└──────────┘                └──────────────┘
     │                            │
     │  PTRACE_ATTACH             │
     │  PTRACE_PEEKTEXT           │  ← memory reads
     │  PTRACE_POKETEXT           │  ← memory writes (breakpoints)
     │  PTRACE_CONT               │  ← continue execution
     │  PTRACE_SINGLESTEP         │  ← step one instruction
     └────────────────────────────┘
```

## Starting GDB

### Compiling for Debug

Always compile with `-g` to include debug symbols. Add `-O0` to disable optimization
so the debugger shows a faithful mapping between source and machine code:

```bash
gcc -g -O0 -o myprogram myprogram.c
```

You can combine optimization with debug info, but be aware that variables may be
optimized away and execution may appear to jump around:

```bash
gcc -g -O2 -o myprogram myprogram.c
```

### Launch Modes

```bash
# Debug a program
gdb ./myprogram

# Debug with arguments
gdb --args ./myprogram arg1 arg2

# Attach to a running process
gdb -p 1234

# Attach to a process by name
gdb -p $(pidof myprogram)

# Analyze a core dump
gdb ./myprogram core.1234

# Run in batch mode (non-interactive, useful for scripts)
gdb -batch -ex "run" -ex "bt" ./myprogram
```

### GDB Startup Files

GDB reads `~/.gdbinit` on startup, and then `.gdbinit` in the current directory.
These can set default options, define convenience functions, and configure the
debugging environment:

```bash
# ~/.gdbinit
set disassembly-flavor intel
set print pretty on
set pagination off
set confirm off
```

## Breakpoints

Breakpoints are the primary mechanism for controlling program execution. GDB
supports several types of stopping points.

### Setting Breakpoints

```bash
(gdb) break main                    # Break at function "main"
(gdb) break myprogram.c:42          # Break at line 42 of myprogram.c
(gdb) break myprogram.c:42 if x>10  # Conditional breakpoint
(gdb) break myfunc                  # Break at function entry
(gdb) break myclass::method         # C++ member function
(gdb) break myclass::method(int)    # Overloaded C++ function
(gdb) break *0x4005b6               # Break at exact address
(gdb) break +10                     # Break 10 lines from current
```

### Managing Breakpoints

```bash
(gdb) info breakpoints              # List all breakpoints
(gdb) delete 3                      # Delete breakpoint 3
(gdb) delete                        # Delete all breakpoints
(gdb) disable 2                     # Disable breakpoint 2
(gdb) enable 2                      # Re-enable breakpoint 2
(gdb) ignore 5 10                   # Ignore breakpoint 5, next 10 times
(gdb) commands 5                    # Execute commands when breakpoint 5 hits
  > printf "x = %d\n", x
  > continue
  > end
```

### Hardware-Assisted Breakpoints

Hardware breakpoints use CPU debug registers and don't modify memory. They are
essential when debugging read-only memory or flash-based embedded systems:

```bash
(gdb) hbreak *0x4005b6              # Hardware breakpoint
(gdb) hbreak main if argc > 1       # Conditional hardware breakpoint
(gdb) thbreak main                  # Temporary hardware breakpoint (auto-delete)
```

## Watchpoints

Watchpoints stop execution when the value of an expression changes. They are
extremely useful for tracking down memory corruption and unexpected modifications.

```bash
(gdb) watch myvar                   # Stop when myvar is written
(gdb) watch *(int*)0x601040         # Stop when memory at address changes
(gdb) watch myarray[0]              # Stop when array element changes
(gdb) rwatch myvar                  # Stop when myvar is read
(gdb) awatch myvar                  # Stop when myvar is read or written
(gdb) watch myvar if myvar > 100    # Conditional watchpoint
```

Watchpoints can be expensive — GDB may single-step the program and check
the watched expression after each instruction. On x86, GDB can use hardware
debug registers for watchpoints on simple expressions, which is much faster.

## Examining State

### Stack Frames

```bash
(gdb) backtrace                     # Show call stack (also: bt)
(gdb) bt full                       # Show stack with local variables
(gdb) bt 10                         # Show top 10 frames
(gdb) frame 3                       # Switch to frame 3
(gdb) up                            # Move up one frame
(gdb) down                          # Move down one frame
(gdb) info frame                    # Details about current frame
(gdb) info args                     # Show function arguments
(gdb) info locals                   # Show local variables
```

### Variables and Expressions

```bash
(gdb) print myvar                   # Print variable value
(gdb) print /x myvar                # Print in hexadecimal
(gdb) print /t myvar                # Print in binary
(gdb) print *myptr                  # Dereference pointer
(gdb) print myarray[0]@10           # Print 10 elements starting at index 0
(gdb) print sizeof(mystruct)        # Evaluate expression
(gdb) set myvar = 42                # Modify variable
(gdb) display myvar                 # Print myvar every time program stops
(gdb) undisplay 1                   # Remove display 1
(gdb) info display                  # List active displays
```

### Memory Examination

```bash
(gdb) x/20xb 0x601040               # Examine 20 hex bytes at address
(gdb) x/10xw $rsp                    # Examine 10 hex words at stack pointer
(gdb) x/5i $pc                       # Examine 5 instructions at PC
(gdb) x/s 0x400600                   # Examine as string
(gdb) x/20gx $rsp                    # 20 giant (8-byte) hex words
```

The format is `x/<count><format><size> <address>`:
- Formats: `x` hex, `d` decimal, `u` unsigned, `t` binary, `f` float, `i` instruction, `c` char, `s` string
- Sizes: `b` byte, `h` halfword (2B), `w` word (4B), `g` giant (8B)

### Registers

```bash
(gdb) info registers                 # Show all registers
(gdb) info registers rax rbx         # Show specific registers
(gdb) print $rax                     # Read register
(gdb) set $rax = 0                   # Write register
(gdb) info all-registers             # Include FPU/vector registers
```

## Stepping Through Code

```bash
(gdb) next                          # Step over (source line)
(gdb) next 5                        # Step over 5 times
(gdb) step                          # Step into (source line)
(gdb) finish                        # Run until current function returns
(gdb) continue                      # Continue execution
(gdb) nexti                         # Step over one machine instruction
(gdb) stepi                         # Step into one machine instruction
(gdb) advance myfunc                # Run until myfunc is called
(gdb) until 42                      # Run until line 42 (or past current line)
```

## Remote Debugging

Remote debugging is essential for embedded systems, kernel debugging, and
debugging on machines where you can't run GDB directly.

### Architecture

```
┌──────────┐  TCP / Serial  ┌──────────────┐
│   GDB    │◄──────────────►│ gdbserver     │
│ (host)   │   GDB Remote   │ (target)      │
│          │    Protocol     │               │
└──────────┘                └──────┬───────┘
                                   │
                            ┌──────┴───────┐
                            │  Program     │
                            │  Being Debugged│
                            └──────────────┘
```

### Using gdbserver

On the target machine:
```bash
# Start gdbserver with a program
gdbserver :1234 ./myprogram arg1 arg2

# Attach to a running process
gdbserver :1234 --attach $(pidof myprogram)
```

On the host machine:
```bash
gdb ./myprogram
(gdb) target remote 192.168.1.100:1234
(gdb) set sysroot /path/to/target/rootfs
(gdb) set solib-search-path /path/to/target/libs
(gdb) continue
```

### QEMU + GDB for Kernel/Embedded

```bash
# Start QEMU with GDB stub
qemu-system-x86_64 -kernel bzImage -append "console=ttyS0" \
    -nographic -s -S

# Connect from GDB
gdb vmlinux
(gdb) target remote :1234
(gdb) break start_kernel
(gdb) continue
```

The `-S` flag pauses QEMU at startup, and `-s` opens a GDB server on port 1234.

## Core Dump Analysis

Core dumps capture the state of a process at the moment of a crash, allowing
post-mortem debugging.

### Enabling and Generating Core Dumps

```bash
# Enable core dumps (unlimited size)
ulimit -c unlimited

# Set core dump pattern
echo "core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern

# Generate core dump from running process
kill -ABRT $(pidof myprogram)

# Generate core dump with gcore (doesn't kill the process)
gcore 1234
```

### Analyzing Core Dumps

```bash
gdb ./myprogram core.1234

(gdb) bt                            # Where did it crash?
(gdb) bt full                       # With local variables
(gdb) info registers                # Register state at crash
(gdb) info threads                  # All threads at crash time
(gdb) thread 3                      # Examine thread 3
(gdb) print myvar                   # Inspect variables
(gdb) x/20i $pc-10                  # Disassemble around crash point
```

### GDB + coredump_filter

The file `/proc/<pid>/coredump_filter` controls which memory regions are
included in the core dump:

| Bit | Include |
|-----|---------|
| 0x1 | Anonymous private mappings |
| 0x2 | Anonymous shared mappings |
| 0x4 | File-backed private mappings |
| 0x8 | File-backed shared mappings |
| 0x10 | ELF headers |
| 0x20 | Private huge pages |
| 0x40 | Shared huge pages |

## TUI Mode — Text User Interface

GDB's TUI mode provides a visual interface with source code, assembly, and
register views alongside the command prompt.

```bash
# Enter TUI mode
gdb -tui ./myprogram

# Or toggle TUI mode within GDB
(gdb) layout src                    # Show source code window
(gdb) layout asm                    # Show assembly window
(gdb) layout split                  # Show source + assembly
(gdb) layout regs                   # Show source + registers
(gdb) tui reg general               # Show general registers
(gdb) winheight src +5              # Resize source window
(gdb) focus src                     # Focus on source window
(gdb) refresh                       # Refresh display
(gdb) ctrl-x a                      # Toggle TUI mode (key combo)
(gdb) ctrl-x 2                      # Cycle through two-window layouts
```

```
┌─────────────────────────────────────────┐
│  Source Window                           │
│  (showing current source file with       │
│   execution position highlighted)        │
│  ─────────────────────────────────────── │
│  Assembly Window                         │
│  (disassembly at current PC)             │
│  ─────────────────────────────────────── │
│  Register Window                         │
│  (general-purpose registers)             │
│  ─────────────────────────────────────── │
│  (gdb) _                                 │
└─────────────────────────────────────────┘
```

## GDB Scripts (Python GDB)

GDB has a powerful Python scripting interface for automating debugging tasks,
creating custom pretty-printers, and building domain-specific debugging tools.

### Python Commands

```python
# ~/.gdbinit or loaded via source
import gdb

class MyCommand(gdb.Command):
    """Print all global variables of a given type."""

    def __init__(self):
        super().__init__("my-globals", gdb.COMMAND_DATA)

    def invoke(self, arg, from_tty):
        inferior = gdb.selected_inferior()
        block = gdb.selected_frame().block()
        while block:
            if block.is_global:
                for sym in block:
                    if sym.type.name == arg and sym.is_variable:
                        val = sym.value(gdb.selected_frame())
                        print(f"{sym.name} = {val}")
            block = block.superblock

MyCommand()
```

### Pretty-Printers

```python
import gdb
import gdb.printing

class VectorPrinter:
    def __init__(self, val):
        self.val = val

    def to_string(self):
        size = self.val['size']
        data = self.val['data']
        items = [str(data[i]) for i in range(int(size))]
        return f"Vector[{size}] = [{', '.join(items)}]"

def lookup(val):
    if str(val.type) == 'Vector':
        return VectorPrinter(val)
    return None

gdb.printing.register_pretty_printer(gdb.current_objfile(), lookup)
```

### Built-in Python Utilities

```python
# Convenient value access
val = gdb.parse_and_eval("myvar")
frame = gdb.selected_frame()
inferior = gdb.selected_inferior()

# Read memory
mem = inferior.read_memory(address, length)

# Iterate over threads
for thread in gdb.selected_inferior().threads():
    thread.switch()
    print(f"Thread {thread.num}: {gdb.selected_frame().name()}")
```

## rr — Record and Replay Debugger

`rr` is a record-and-replay debugger built on top of GDB. It records program
execution and allows deterministic replay, making intermittent bugs reproducible.

### Recording

```bash
# Record a program execution
rr record ./myprogram arg1 arg2

# Record with specific flags
rr record --chaos ./myprogram        # Randomize scheduling decisions
rr record -M ./myprogram             # Record to a specific trace directory
```

### Replaying

```bash
# Replay the most recent recording
rr replay

# Replay a specific recording
rr replay /home/user/.local/share/rr/myprogram-0

# Replay with GDB
rr replay -f /home/user/.local/share/rr/myprogram-0
```

### rr Workflow

```
┌──────────────┐     Record     ┌──────────────┐
│  Program     │───────────────►│ Trace File   │
│  Execution   │                │ (deterministic│
│              │                │  recording)   │
└──────────────┘                └──────┬───────┘
                                       │
                                       │ Replay
                                       ▼
                                ┌──────────────┐
                                │ GDB Session  │
                                │ (deterministic│
                                │  replay)     │
                                └──────────────┘
```

Key features of rr:

- **Deterministic replay**: Same execution every time — no heisenbugs
- **Reverse execution**: `reverse-continue`, `reverse-next`, `reverse-step`
- **GDB integration**: Full GDB protocol support
- **Multiprocess**: Records forked processes
- **Lightweight**: ~20-50% overhead during recording

```bash
# During rr replay (GDB commands)
(gdb) break myfunction
(gdb) continue
(gdb) reverse-continue               # Run backwards to previous breakpoint
(gdb) reverse-step                    # Step backwards
(gdb) reverse-next                    # Next backwards
(gdb) reverse-finish                  # Go back to before current function call
(gdb) watch myvar
(gdb) reverse-continue               # Find when myvar was last modified
```

## Advanced GDB Features

### Multi-Thread Debugging

```bash
(gdb) info threads                   # List all threads
(gdb) thread 5                       # Switch to thread 5
(gdb) thread apply all bt            # Show backtrace of all threads
(gdb) thread apply all bt full       # With local variables
(gdb) set scheduler-locking on       # Lock scheduler to current thread
(gdb) set scheduler-locking step     # Lock during stepping only
(gdb) set non-stop on                # Non-stop mode (other threads run)
(gdb) set target-async on            # Async mode (non-blocking commands)
```

### Debugging Optimized Code

When debugging `-O2` code, variables may be `<optimized out>`. Strategies:

```bash
(gdb) info locals                    # Some may show <optimized out>
(gdb) frame                         # Try different frames
(gdb) disassemble                   # Look at the actual machine code
(gdb) info registers                # Register values may reveal optimized vars
(gdb) print /x $rdi                 # First argument register (x86-64 ABI)
```

### GDB Checkpoints

Checkpoints save the process state so you can return to it later:

```bash
(gdb) checkpoint                     # Save state (checkpoint 1)
(gdb) info checkpoints               # List checkpoints
(gdb) restart 1                      # Restore checkpoint 1
```

### Catchpoints

Catchpoints stop execution when specific events occur:

```bash
(gdb) catch syscall open             # Stop on open() syscall
(gdb) catch syscall exit             # Stop on exit() syscall
(gdb) catch throw                    # Stop on C++ throw
(gdb) catch catch                    # Stop on C++ catch
(gdb) catch fork                     # Stop on fork()
(gdb) catch exec                     # Stop on exec()
(gdb) catch load libfoo.so           # Stop when shared library is loaded
(gdb) catch signal SIGSEGV           # Stop on segmentation fault
```

### Reverse Debugging (without rr)

GDB supports reverse debugging natively using process record/replay:

```bash
(gdb) target record-full             # Start recording
(gdb) continue                       # Run to some point
(gdb) reverse-stepi                  # Step backwards one instruction
(gdb) reverse-continue               # Continue backwards
(gdb) record stop                    # Stop recording
```

## GDB Command Reference Table

| Command | Short | Description |
|---------|-------|-------------|
| `break` | `b` | Set breakpoint |
| `run` | `r` | Start program |
| `continue` | `c` | Continue execution |
| `next` | `n` | Step over |
| `step` | `s` | Step into |
| `finish` | `fin` | Run until return |
| `print` | `p` | Print value |
| `backtrace` | `bt` | Show call stack |
| `display` | `disp` | Auto-print on stop |
| `watch` | `w` | Set watchpoint |
| `info` | `i` | Show information |
| `x` | — | Examine memory |
| `disassemble` | `disas` | Show disassembly |
| `set` | — | Modify variable/register |
| `thread` | `thr` | Thread operations |

## Best Practices

1. **Always compile with `-g`** — debug symbols are essential; they add no runtime cost
2. **Use `-O0` for debugging** — optimization makes variable values unreliable
3. **Use conditional breakpoints** — `break foo if x==0` is faster than manual checking
4. **Use watchpoints to track corruption** — `watch` on suspected variables
5. **Save time with `.gdbinit`** — automate repetitive setup
6. **Use rr for intermittent bugs** — deterministic replay is transformative
7. **Learn the TUI** — visual context helps during stepping
8. **Use Python scripts** — automate repetitive analysis tasks

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [GDB Official Documentation](https://sourceware.org/gdb/documentation/)
- [GDB Wiki](https://sourceware.org/gdb/wiki/)
- [rr Project](https://rr-project.org/)
- [GDB Python API](https://sourceware.org/gdb/current/onlinedocs/gdb/Python-API.html)
- [GDB Quick Reference (PDF)](https://users.ece.utexas.edu/~adnan/gdb-refcard.pdf)

## Related Topics

- [Strace and Ltrace](./strace-ltrace.md) — System call and library call tracing
- [Perf](./perf.md) — Performance profiling with hardware counters
- [eBPF](./ebpf.md) — Advanced kernel-level tracing and debugging
- [Kernel Debugging](./kernel-debugging.md) — KGDB, KDB, and crash utility
