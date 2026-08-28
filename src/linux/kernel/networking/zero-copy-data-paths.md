# Zero-Copy Data Paths: From sendfile(2) to AF_XDP UMEM

Every syscall that ships a byte decides who moves that byte: the CPU, a DMA
engine, or nobody at all. Each rung of the kernel's zero-copy spectrum trades
generality for throughput; this page walks the spectrum end to end.

## 1. What a Copy Actually Costs

A "single copy" bills three accounts at once:

1. **Bandwidth tax**: `S / memcpy_bandwidth` CPU-seconds. At ~10 GB/s per
   core, serving 10 Gb/s with a read/write loop spends most of a core on
   copy_to_user()/copy_from_user() alone.
2. **Cache pollution**: each pass streams S/64 cache lines through L1/L2,
   evicting the hot working set; four passes on 1 MiB is ~65k line touches.
3. **Latency serialization**: copies sit on the critical path. A copy that
   overlaps DMA does not; a copy that *replaces* DMA does not exist. The
   checksum pass is the classic double hit -- hence checksum offload is the
   sibling of every zero-copy API below.

## 2. The Spectrum

```text
more CPU per byte  <---------------------------------->  less CPU per byte

 read()+write()       sendfile(2)         splice(2)/vmsplice(2)
   user buf             page cache          user pages / page cache
      |  copy 1           |  page refs         |  page refs into pipe
      v                  v                     v
   kernel skb <---- SG-DMA scatter-gather (NIC assembles from frags)
      |  copy 2           |                     |
      v                  v                     v
   NIC ring            NIC ring             NIC ring
 MSG_ZEROCOPY          io_uring SEND_ZC      AF_XDP UMEM
   pinned user pages    pinned / reg. bufs    reg. frames, FILL/COMP
   page refs into skb   CQE on done           no skb, no kernel buffer
   frags; done via      (SENDZC_NOTIF);       FILL/COMP trade frames
   MSG_ERRQUEUE ticket  done via CQE          with the driver
```

Rule of thumb: further right = more constraints on the data, fewer CPU sightings of it.

## 3. sendfile(2): File to NIC Without the CPU

`sendfile(out_fd, in_fd, NULL, count)` serves a file from page cache to a
socket (`out_fd` must, since Linux 2.6.33, be a socket). The win: the payload
never enters the CPU domain. The socket layer builds an skb whose payload is
a **scatter-gather fragment list** pointing at the page-cache pages
(`skb_fill_page_desc`, `NETIF_F_SG`); the NIC's SG-DMA engine walks the list
and pulls each page straight from memory -- no CPU instruction touches it.

**When TLS defeats it.** Userspace TLS (OpenSSL, GnuTLS) kills sendfile:
ciphertext must be produced by userspace, so data round-trips page cache ->
user buffer -> (encrypt) -> socket buffer, restoring both copies plus the
crypto. kTLS (`setsockopt(SOL_TLS, TLS_TX, ...)`) moves record framing and
encryption into the kernel or NIC, restoring sendfile()/splice() zero-copy:
[tls-offload.md](./tls-offload.md).

**Caveats.** sendfile() blocks mid-file when the peer's receive window fills,
and cannot touch data generated in application memory.

## 4. splice(2) and vmsplice(2): The Pipe as Page Conveyor

A Linux pipe is a ring of 16 `struct pipe_buffer` slots (64 KiB default,
growable via `F_SETPIPE_SZ`). Each slot holds a **page reference**, an offset,
a length, and an ops vector -- not bytes. So:

- `splice(file_fd, &off, pipe_wr, ...)`: page refs from page cache into the
  pipe; `splice(pipe_rd, NULL, sock_fd, ...)`: those refs into the socket's
  skb fragment list. No bytes move in either hop.
- `vmsplice(pipe_wr, iov, n, SPLICE_F_GIFT)`: gifts your user pages into the
  pipe (reverse direction); do not modify the buffer until consumed.

`SPLICE_F_MOVE` asks for refs to be *moved* rather than copied -- relevant
pipe-to-pipe and some file paths; for network sockets it is mostly a no-op
hint, the skb frag path already being reference-based. `SPLICE_F_MORE` is an
MSG_MORE-style coalescing hint. The 16-slot ring also throttles: it bounds
in-flight data before splice() blocks or returns short -- natural for
streaming relays, meaningless for random access. sendpage(), sendfile()'s
pipe-less cousin, is deprecated; splice(2) is the canonical page-ref API.
The relay idiom -- `splice(file_fd, &offset, pipefd[1], NULL, CHUNK,
SPLICE_F_MOVE)` then `splice(pipefd[0], NULL, sock_fd, NULL, CHUNK,
SPLICE_F_MORE)` -- streams the file through the pipe without a CPU touch.

## 5. MSG_ZEROCOPY: Zero-Copy Sends With Completion Tickets

MSG_ZEROCOPY covers the case sendfile() cannot: the bytes live in *your* memory.

1. One-time: `setsockopt(fd, SOL_SOCKET, SO_ZEROCOPY, &val, sizeof(val))`;
   per send: `send(fd, buf, len, MSG_ZEROCOPY)`.
2. The kernel **pins** your pages (long-term GUP pinning -- see
   [gup.md](../memory/gup.md)) and hangs them off the skb as fragments.
3. The send returns a completion cookie range; the real completion arrives
   on the socket's **error queue**: `recvmsg(fd, &msg, MSG_ERRQUEUE)` yields
   `SO_EE_ORIGIN_ZEROCOPY` records saying a range is now free.

The fine print is where interviews live:

- **Pinning and page faults**: pages must be resident; the pin is long-term
  and interacts with CMA/migration, hence the push for large, reused buffers.
- **Fallback copies**: if the kernel had to copy anyway (fragmentation, no SG
  support, loopback), the record is flagged `SO_EE_CODE_ZEROCOPY_COPIED` -- you
  paid the complexity for nothing.
- **Size threshold**: man-page guidance is roughly >= 10 KiB per call; below
  that, pin/account/notify overhead exceeds the memcpy it replaced (section 9
  reproduces this crossover). TCP only; loopback not at all. See
  [sockets.md](./sockets.md).

## 6. io_uring: IORING_OP_SEND_ZC and Registered Buffers

io_uring generalizes the ticket idea to the async completion model you already use:

- `IORING_OP_SEND_ZC` -- async zero-copy send; the kernel signals "done with
  your pages" as a CQE, paired with a companion notification op
  (`IORING_OP_SENDZC_NOTIF`) instead of an error queue. Verified in liburing's
  `include/liburing/io_uring.h`: `IORING_OP_SEND_ZC` and
  `IORING_SEND_ZC_REPORT_USAGE` exist in the current header.
- **Registered buffers** (`io_uring_register_buffers`) pre-pin memory once,
  removing the per-send pinning cost that dominates small sends; the same GUP
  pinning powers the block side (`IORING_OP_READ_FIXED`):
  [io-uring-block.md](../block/io-uring-block.md). SEND_ZC's edge is not the
  copy count (both are zero-copy) but completion as a CQE in a ring you
  already poll -- no error-queue syscall, natural batching.

## 7. AF_XDP: The UMEM as a Full Zero-Copy Packet Path

Everything above still builds skbs and runs the TCP stack. AF_XDP removes the
kernel from the payload path entirely: the application registers a **UMEM** --
a fixed region of user memory chopped into frames -- and a driver with XDP ZC
support points the NIC's DMA at UMEM frames directly. RX: the NIC DMAs the
packet *into your memory*; TX: you write a frame and the NIC DMAs it out;
`FILL`/`COMP` rings trade frame ownership with the driver. No skb, no kernel
buffer, no copy -- and the price: driver ZC support, fixed-size frames, and
the stack is your problem. Mechanics: [af-xdp-internals.md](./af-xdp-internals.md);
frame-level processing: [af-packet.md](./af-packet.md), [xdp.md](./xdp.md).

## 8. Copy Bypass in Storage Fabrics: NVMe-oF and RDMA

The same discipline powers storage fabrics, with the fabric replacing the
socket layer. **RDMA verbs**: the application registers memory (`ibv_reg_mr`)
exactly like io_uring registration; the NIC DMAs it directly (`RDMA_WRITE`,
`RDMA_READ`) -- the copy skipped is the initiator's double-buffer.
**NVMe-oF**: commands and data cross the fabric inside RDMA transports, so a
host read lands DMA-directly into the pinned destination buffer, the CQE
playing the completion ticket ([nvmeof.md](../../../storage/nvmeof.md)).
Lesson: every zero-copy API is *memory registration* plus a *completion
protocol*; change the transport and both survive.

## 9. A Byte-Accounting Cost Model

The model prices three send paths for the same payload: a memcpy send
(read()+write() of generated data), sendfile() (file-backed only), and
MSG_ZEROCOPY; assumptions live in the code, as constants not measurements.

```python
#!/usr/bin/env python3
"""Byte-accounting model: memcpy send vs sendfile vs MSG_ZEROCOPY.
Assumptions (order-of-magnitude, not benchmarks): MEMCPY_GB_S = single-core
memcpy bandwidth; ZC_PAGE_CYC = per-page kernel overhead (GUP pin, frag
fill, cookies); ZC_CALL_US = fixed per-call pin setup + one MSG_ERRQUEUE
read; memcpy path = 2 payload copies, 4 cacheline (64 B) touch passes."""
PAGE, LINE = 4096, 64
MEMCPY_GB_S, CYCLE_NS, ZC_PAGE_CYC, ZC_CALL_US = 10.0, 0.3, 120, 1.5

def stats(size, path):
    if path == "memcpy-send":
        copies, lines = 2 * size, 4 * size // LINE
        cpu_us = copies / (MEMCPY_GB_S * 1e9) * 1e6
    elif path == "sendfile":
        copies = lines = 0                     # SG-DMA assembles from pages
        cpu_us = 0.0                           # CPU sees headers only
    else:                                      # msg_zerocopy
        copies = lines = 0
        cpu_us = ZC_CALL_US + max(1, size // PAGE) * ZC_PAGE_CYC * CYCLE_NS / 1e3
    return copies, lines, cpu_us

def main():
    hdr = "payload      path           copies     line-touches   CPU time"
    sizes = [4 * 1024, 64 * 1024, 1024 * 1024, 64 * 1024 * 1024]
    paths = ["memcpy-send", "sendfile", "msg_zerocopy"]  # sendfile: file-backed only
    print(hdr); print("-" * len(hdr))
    for s in sizes:
        rows = [stats(s, p) for p in paths]
        for p, (c, l, us) in zip(paths, rows):
            print(f"{s:>9,} B  {p:<13}  {c / 1e6:>7.2f} MB  {l:>10,}     {us:>9.2f} us")
        best = min(zip([r[2] for r in rows], paths))[1]
        print(f"{'':>14}-> winner at this size: {best}\n")
    # crossover scan: smallest payload where MSG_ZEROCOPY beats memcpy
    s = 1024
    while stats(s, "msg_zerocopy")[2] > stats(s, "memcpy-send")[2]:
        s += 1024
    print(f"MSG_ZEROCOPY overtakes memcpy-send near payload = {s / 1024:.0f} KiB/call")

main()
```

Real output (sandbox, Python 3.12.14; run twice, byte-identical):

```text
payload      path           copies     line-touches   CPU time
--------------------------------------------------------------
    4,096 B  memcpy-send       0.01 MB         256          0.82 us
    4,096 B  sendfile          0.00 MB           0          0.00 us
    4,096 B  msg_zerocopy      0.00 MB           0          1.54 us
              -> winner at this size: sendfile

   65,536 B  memcpy-send       0.13 MB       4,096         13.11 us
   65,536 B  sendfile          0.00 MB           0          0.00 us
   65,536 B  msg_zerocopy      0.00 MB           0          2.08 us
              -> winner at this size: sendfile

1,048,576 B  memcpy-send       2.10 MB      65,536        209.72 us
1,048,576 B  sendfile          0.00 MB           0          0.00 us
1,048,576 B  msg_zerocopy      0.00 MB           0         10.72 us
              -> winner at this size: sendfile

67,108,864 B  memcpy-send     134.22 MB   4,194,304      13421.77 us
67,108,864 B  sendfile          0.00 MB           0          0.00 us
67,108,864 B  msg_zerocopy      0.00 MB           0        591.32 us
              -> winner at this size: sendfile

MSG_ZEROCOPY overtakes memcpy-send near payload = 8 KiB/call
```

First, the crossover lands in the 8-16 KiB/call region, consistent with the
man page's "typically > 10 KiB" guidance -- below it, pin-plus-ticket overhead
exceeds the two copies it eliminated. Second, sendfile() "wins" only because
the model ignores its constraint (file-backed, static data); for generated
data the honest fight is memcpy-send vs msg_zerocopy, and the crossover above
is the whole decision.

## 10. When Zero-Copy Loses

- **Small sends.** Pinning, fragment filling, and completion accounting have
  fixed floors; at 4 KiB they exceed the 0.82 us memcpy (model below).
- **Short-lived buffers.** Serialize on one buffer and the ticket has built
  you a slower memcpy; zero-copy wants ring-of-buffers lifetimes.
- **Transforming middleboxes.** Fragmentation, userspace TLS, compression --
  anything that rewrites the body forces a materialization copy, reported via
  `SO_EE_CODE_ZEROCOPY_COPIED`.
- **Loopback and tail latency.** Loopback silently falls back to copying
  (never extrapolate a loopback benchmark), and a pinned-page fault or CMA
  stall is a rare, huge outlier -- small-message systems stay memcpy-based.

## 11. Interview Angles

- "Why does sendfile() help even though the NIC still reads the bytes from
  RAM?" -- the CPU never executes loads/stores on the payload; SG-DMA does the
  reads; the skb is a fragment list of page references.
- "Your MSG_ZEROCOPY server shows no speedup and logs
  SO_EE_CODE_ZEROCOPY_COPIED. Diagnose." -- the kernel copied anyway: check
  message size, SG/checksum offload, loopback in tests.

## References

1. `sendfile(2)` -- Linux man-pages: <https://man7.org/linux/man-pages/man2/sendfile.2.html> (verified 200)
2. `splice(2)` -- Linux man-pages: <https://man7.org/linux/man-pages/man2/splice.2.html> (verified 200)
3. `vmsplice(2)` -- Linux man-pages: <https://man7.org/linux/man-pages/man2/vmsplice.2.html> (verified 200)
4. Kernel docs, "MSG_ZEROCOPY": <https://docs.kernel.org/networking/msg_zerocopy.html> (verified 200)
5. io_uring / liburing -- `IORING_OP_SEND_ZC` in `include/liburing/io_uring.h`: <https://github.com/axboe/liburing> (verified 200)
