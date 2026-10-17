# "TCP guarantees the application receives the data"

## Overview

TCP is called "reliable", and the adjective silently grows a second clause:
reliable *to the application*. It is not. TCP guarantees reliable, ordered
byte delivery from one kernel socket buffer to another, for as long as the
connection lives — it cannot promise anything about what happens at the
receiving application, and it explicitly discards buffered data on reset.
This page states the real guarantee, the three failure classes the slogan
ignores, the exact RFC 9293 language on reset handling, and the design
pattern (application-level acknowledgement plus idempotency) that provides
what TCP never did.

## The Claim, Stated Fairly

The strongest common form: "If `send()` returns, the data will be delivered;
the receiving process will get every byte, in order. That is what 'reliable
transport' means." Stated fairly, this is what most engineers believe, and it
is even what most observed behavior shows — in the happy regime where both
endpoints live, the network converges, and the receiver reads promptly. The
claim is the *unconditional* version of a *conditional* guarantee.

## Verdict

**False.** TCP guarantees in-order byte delivery to the receiving OS socket
buffer while the connection survives; it cannot guarantee the peer
application ever reads the data, and on reset the buffered data is discarded.

## Why People Believe It

The kernel of truth is substantial. TCP really does retransmit lost packets,
reorder segments, checksum payloads, and flow-control the sender against the
receiver's buffer — RFC 9293, the current TCP specification, defines exactly
these mechanisms. `send()` returning does mean the bytes are accepted into
the local send buffer, and TCP will keep trying to deliver them. For
processes that stay alive and read their sockets, the observed behavior
matches the slogan perfectly, often for years at a time.

The gap opens at the boundary TCP never owned: the kernel-to-application
edge. Reliability terminates at the socket buffer. Whether a human-readable
"the application got it" event occurs depends on the receiving process
existing, being healthy, and calling `read()` — none of which TCP controls
or even observes.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Data is guaranteed delivered" | Bytes are delivered *in order to the receive buffer* while the connection is alive |
| "`send()` returning means sent" | It means accepted into the local send buffer; the data may still be lost with the connection |
| "An ACK confirms receipt" | An ACK confirms receipt *by the peer's TCP*, not a read by the peer's application |
| "Keepalive proves the peer is alive" | Keepalive proves the *network path and TCP stack* respond, not that the application is healthy |
| "Close flushes everything" | On RST, RFC 9293 directs that all segment queues are flushed — buffered data is gone |

The precise statement: TCP provides *reliability of transport*, an
endpoint-to-endpoint property between kernel buffers. *Delivery assurance to
the application* — the property "some process consumed this data and acted
on it" — requires an application-level acknowledgement protocol, which is why
every reliable messaging system (queues, RPC frameworks with acks, database
commits) exists on top of TCP rather than trusting it.

## Where It Breaks

**Reset discards buffered data.** RFC 9293 Section 3.10.7 (SEGMENT ARRIVES),
for a connection in ESTABLISHED state receiving a valid RST: "any outstanding
RECEIVEs and SEND should receive 'reset' responses. All segment queues should
be flushed." Concretely: a sender pushes 1 MB; the receiver's TCP ACKs it
into the receive buffer; the receiver's application crashes without reading;
the peer's kernel then sends RST (for example because the socket closes with
unread data). Everything buffered — both directions — is flushed, and the
sender that saw successful ACKs now learns nothing except "connection reset".
The ACKs were true; "the application has the data" was never claimed by them.

**Peer crash.** If the receiving host dies mid-connection, its memory —
including the receive buffer and all socket state — dies with it. TCP on the
sender side will retransmit into the void until timeout or RST, then report
an error. Bytes that were ACKed seconds before the crash never reached any
application and never will.

**The receiver never reads.** A wedged consumer stops calling `read()`. The
receive buffer fills, the advertised window goes to zero, and the sender's
buffer holds the backlog. The connection is "healthy" — keepalive probes are
answered by the peer's kernel — but delivery to the *application* has been
stalled indefinitely. TCP's flow control is doing its job; the application
level has failed in a way TCP cannot see.

**Keepalive is not application liveness.** TCP keepalive (RFC 9293
Section 3.8.4) asks the peer's TCP stack for proof of the *connection*, not
proof that any process is making progress. A deadlocked server answers
keepalives flawlessly while never reading another byte.

**Close semantics.** Calling `close()` discards unsent data silently unless
the application checks for errors and retries; with `SO_LINGER` zero, close
sends RST and discards both unsent and unacknowledged data immediately.
"Trust close()" is the same misconception one layer down.

## Practical Implications

- Design for application-level acknowledgement: the sender must learn, from
  the peer's *application* (a response message, a commit record, a queue
  ack), that the data was consumed — anything less is transport optimism.
- Make retries idempotent. If the sender cannot distinguish "never arrived"
  from "arrived but the ack was lost", duplicate delivery is inevitable and
  handlers must tolerate it.
- Detect receiver wedging at the application layer: request timeouts,
  heartbeat messages, and in-flight limits — not TCP keepalive.
- On shutdown, use orderly close (half-close, flush checks, error handling on
  `send()`/`close()`) rather than trusting the kernel to finish the job.
- Message queues turn "TCP delivered it" into "a broker acknowledged it",
  which is the same idea packaged correctly.

## Interview Questions

### If TCP ACKs my data, can I be sure the peer application processed it?

No. An ACK acknowledges receipt by the peer's TCP into its buffers. The
application may crash, never read, or read later; on a reset, RFC 9293
directs that all segment queues are flushed. Only an application-level ack
carries the "processed" meaning.

### What exactly does RFC 9293 say happens to buffered data when a connection is reset?

For ESTABLISHED-state connections receiving a valid RST: outstanding
RECEIVEs and SENDs get "reset" responses, all segment queues are flushed, and
the user receives an unsolicited "connection reset" signal. Buffered, already
ACKed data is discarded — transport reliability does not survive the reset.

### How do you build "guaranteed delivery" on top of TCP?

You do not get it from TCP; you add it: sender keeps the message until the
receiver's application acknowledges it (store-and-forward, queue semantics),
retries on timeout, and the receiver deduplicates via idempotency keys or
transactional dedupe. This is precisely the design of message brokers and
exactly-once-ish pipelines.

## Key Takeaways

- TCP's reliability ends at the socket buffer: ordered, checked, retransmitted
  bytes *between kernels* — nothing more.
- ACK means "my TCP has it"; it never meant "my application read it".
- RST discards buffered data by specification, not by accident.
- Keepalive proves path liveness, not application health.
- Delivery assurance is an application property: acks, idempotency, retries.

## Cross-References

- [Follow-up Tree: TCP Lifecycle](../followup-tree/tcp-lifecycle.md) —
  interview escalation on connection states, close, and reset
- [Assumptions Hunt: Network and Distributed](../assumptions-hunt/network-distributed.md)
  — the reliable-network assumption examined at every layer
- [TCP Overview](../../networks/tcp/README.md) — retransmission, ordering,
  and flow control mechanics
- [TCP Keepalive](../../networks/tcp/keepalive.md) — what the probes do and
  do not prove
- [Sockets](../../networks/sockets/README.md) — the buffer boundary where the
  guarantee stops
- [TCP Connection Teardown](../../networks/tcp/four-way.md) — orderly close
  versus reset in detail
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- W. Eddy (ed.). *Transmission Control Protocol (TCP)*, RFC 9293, IETF,
  August 2022 — see Section 3.10.7 (RST handling in ESTABLISHED state) and
  Section 3.8.4 (keep-alives).
  <https://datatracker.ietf.org/doc/html/rfc9293>
