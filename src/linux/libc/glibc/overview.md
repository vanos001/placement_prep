# glibc function pages

One page per function (or tight family), split from the chapter documentation. Status is the best rank among the page's ledger rows; the [glibc ledger](../ledger-glibc.md) has per-function rows. This index grows as families are (re-)authored.

## stdio

| Page | Entry | Status |
|---|---|---|
| [`access` / `faccessat`](./stdio/access-faccessat.md) | `access-faccessat` | documented |
| [`dup` / `dup2` / `dup3`](./stdio/dup-dup2-dup3.md) | `dup-dup2-dup3` | documented |
| [`err` / `errx` / `warn` / `warnx` (verr, verrx, vwarn, vwarnx)](./stdio/err-errx-warn-warnx-verr-verrx-vwarn-vwarnx.md) | `err-errx-warn-warnx-verr-verrx-vwarn-vwarnx` | documented |
| [`errno`](./stdio/errno.md) | `errno` | documented |
| [`error` / `error_at_line` / `error_message_count`](./stdio/error-error-at-line-error-message-count.md) | `error-error-at-line-error-message-count` | documented |
| [`fflush`](./stdio/fflush.md) | `fflush` | documented |
| [`fgetc` / `getc` / `getchar` / `ungetc`](./stdio/fgetc-getc-getchar-ungetc.md) | `fgetc-getc-getchar-ungetc` | documented |
| [`fgets` / `getline` / `getdelim`](./stdio/fgets-getline-getdelim.md) | `fgets-getline-getdelim` | documented |
| [`fileno` / `feof` / `ferror` / `clearerr`](./stdio/fileno-feof-ferror-clearerr.md) | `fileno-feof-ferror-clearerr` | documented |
| [`flockfile` / `ftrylockfile` / `funlockfile`](./stdio/flockfile-ftrylockfile-funlockfile.md) | `flockfile-ftrylockfile-funlockfile` | documented |
| [`fopen` / `fdopen` / `freopen` / `fclose`](./stdio/fopen-fdopen-freopen-fclose.md) | `fopen-fdopen-freopen-fclose` | documented |
| [`fputc` / `putc` / `putchar` / `fputs` / `puts`](./stdio/fputc-putc-putchar-fputs-puts.md) | `fputc-putc-putchar-fputs-puts` | documented |
| [`fread` / `fwrite`](./stdio/fread-fwrite.md) | `fread-fwrite` | documented |
| [`fseeko` / `ftello` (fseek, ftell, rewind, fgetpos, fsetpos)](./stdio/fseeko-ftello-fseek-ftell-rewind-fgetpos-fsetpos.md) | `fseeko-ftello-fseek-ftell-rewind-fgetpos-fsetpos` | documented |
| [`fsync` / `fdatasync`](./stdio/fsync-fdatasync.md) | `fsync-fdatasync` | documented |
| [`isatty`](./stdio/isatty.md) | `isatty` | documented |
| [`lseek`](./stdio/lseek.md) | `lseek` | documented |
| [`open` / `close`](./stdio/open-close.md) | `open-close` | documented |
| [`perror`](./stdio/perror.md) | `perror` | documented |
| [`pipe` / `pipe2`](./stdio/pipe-pipe2.md) | `pipe-pipe2` | documented |
| [`popen` / `pclose`](./stdio/popen-pclose.md) | `popen-pclose` | documented |
| [`printf` (printf, fprintf, dprintf, sprintf, snprintf, asprintf)](./stdio/printf-printf-fprintf-dprintf-sprintf-snprintf-asprintf.md) | `printf-printf-fprintf-dprintf-sprintf-snprintf-asprintf` | documented |
| [Program-name variables](./stdio/program-name-variables.md) | `program-name-variables` | documented |
| [`read` / `write`](./stdio/read-write.md) | `read-write` | documented |
| [`readv` / `writev` / `pread` / `pwrite`](./stdio/readv-writev-pread-pwrite.md) | `readv-writev-pread-pwrite` | documented |
| [`remove` / `rename`](./stdio/remove-rename.md) | `remove-rename` | documented |
| [`scanf` (scanf, fscanf, sscanf)](./stdio/scanf-scanf-fscanf-sscanf.md) | `scanf-scanf-fscanf-sscanf` | documented |
| [`setvbuf` / `setbuf` / `setbuffer` / `setlinebuf`](./stdio/setvbuf-setbuf-setbuffer-setlinebuf.md) | `setvbuf-setbuf-setbuffer-setlinebuf` | documented |
| [Stream extensions (one-line notes)](./stdio/stream-extensions-one-line-notes.md) | `stream-extensions-one-line-notes` | researched |
| [`tmpfile` / `tmpnam` / `mkstemp` / `mkdtemp`](./stdio/tmpfile-tmpnam-mkstemp-mkdtemp.md) | `tmpfile-tmpnam-mkstemp-mkdtemp` | documented |
| [`vprintf` / `vfprintf` / `vsnprintf` / `vdprintf` / `vasprintf`](./stdio/vprintf-vfprintf-vsnprintf-vdprintf-vasprintf.md) | `vprintf-vfprintf-vsnprintf-vdprintf-vasprintf` | documented |

## process

| Page | Entry | Status |
|---|---|---|
| [`exec` family: `execl`, `execlp`, `execle`, `execv`, `execvp`, `execvpe`, `execve`, `fexecve`](./process/exec-family-execl-execlp-execle-execv-execvp-execvpe-execve-fexecve.md) | `exec-family-execl-execlp-execle-execv-execvp-execvpe-execve-fexecve` | documented |
| [`fork`](./process/fork.md) | `fork` | documented |
| [`getpid`, `getppid`, `gettid` (and pidfd relatives)](./process/getpid-getppid-gettid-and-pidfd-relatives.md) | `getpid-getppid-gettid-and-pidfd-relatives` | documented |
| [`posix_spawn` and `posix_spawnp`](./process/posix-spawn-and-posix-spawnp.md) | `posix-spawn-and-posix-spawnp` | documented |
| [`pthread_cancel` and the cancellation family](./process/pthread-cancel-and-the-cancellation-family.md) | `pthread-cancel-and-the-cancellation-family` | documented |
| [`pthread_cond_*` (init, wait, signal, broadcast, timedwait + condattr)](./process/pthread-cond-init-wait-signal-broadcast-timedwait-condattr.md) | `pthread-cond-init-wait-signal-broadcast-timedwait-condattr` | documented |
| [`pthread_create`](./process/pthread-create.md) | `pthread-create` | documented |
| [`pthread_join` and `pthread_detach`](./process/pthread-join-and-pthread-detach.md) | `pthread-join-and-pthread-detach` | documented |
| [`pthread_key_create` / `pthread_getspecific` (TSD family)](./process/pthread-key-create-pthread-getspecific-tsd-family.md) | `pthread-key-create-pthread-getspecific-tsd-family` | documented |
| [`pthread_mutex_*` (init, lock, unlock, trylock, timedlock, destroy + mutexattr)](./process/pthread-mutex-init-lock-unlock-trylock-timedlock-destroy-mutexattr.md) | `pthread-mutex-init-lock-unlock-trylock-timedlock-destroy-mutexattr` | documented |
| [`pthread_once`](./process/pthread-once.md) | `pthread-once` | documented |
| [`sleep`, `usleep`, `nanosleep`](./process/sleep-usleep-nanosleep.md) | `sleep-usleep-nanosleep` | documented |
| [`system`](./process/system.md) | `system` | documented |
| [`vfork`](./process/vfork.md) | `vfork` | documented |
| [`wait` and `waitpid`](./process/wait-and-waitpid.md) | `wait-and-waitpid` | documented |
| [`wait3` and `wait4`](./process/wait3-and-wait4.md) | `wait3-and-wait4` | documented |
| [`waitid`](./process/waitid.md) | `waitid` | documented |

