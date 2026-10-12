# `pipe` / `pipe2` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

**Signature** -- `int pipe(int pipefd[2]);` `int pipe2(int pipefd[2],
int flags);` -- `unistd.h`.

**Libc side** -- `pipe` returns `0` with `pipefd[0]` = read end and
`pipefd[1]` = write end (the manual's mnemonic: like `stdin`/`stdout`
order), or `-1`+`errno` (`EMFILE`, `ENFILE`); on Linux the wrapper
issues the `pipe2` syscall (manual, *Creating a Pipe*). `pipe2` is GNU
(`_GNU_SOURCE`, symbol `GLIBC_2.9`) accepting `O_CLOEXEC` and
`O_NONBLOCK` atomically -- the fix for the `FD_CLOEXEC` race the
flagless `pipe` cannot avoid. Writing to a pipe without readers raises
`SIGPIPE`/`EPIPE`; writes up to `PIPE_BUF` are atomic (manual, *Pipe
Atomicity*). `mkfifo(path, mode)` (`sys/stat.h`, POSIX.1) creates the
named variant, a FIFO special file opened by name, returning `0`/`-1`
(`EEXIST`, `EROFS`, `ENOSPC`, manual, *FIFO Special Files*).
