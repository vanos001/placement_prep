# WebSocket Protocol Internals (RFC 6455)

> See [WebSocket](./websocket.md) for the API-level overview and
> [HTTP/1.1](./http1.md) for the upgrade mechanism. This page covers
> the byte-level frame format, masking math, opcode semantics,
> fragmentation, the `permessage-deflate` extension (RFC 7692), and the
> subprotocol negotiation. The reference is RFC 6455.

## 1. Where WebSocket Sits

WebSocket is a **message-framing protocol on top of a single TCP
connection**. It starts life as an HTTP/1.1 request, performs an
`Upgrade` handshake (which is the only HTTP exchange), and from
there on the same TCP socket carries bidirectional, length-prefixed
*frames*. A frame is the unit of transport; one or more frames may
make up one logical *message* (via fragmentation).

```
   client                                            server
   ──────                                            ─────
   GET /chat HTTP/1.1                          ────>
   Upgrade: websocket
   Connection: Upgrade
   Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
   Sec-WebSocket-Version: 13
   Sec-WebSocket-Protocol: chat
   Sec-WebSocket-Extensions: permessage-deflate
                                              <────  HTTP/1.1 101 Switching Protocols
                                                      Upgrade: websocket
                                                      Connection: Upgrade
                                                      Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
                                                      Sec-WebSocket-Protocol: chat
                                                      Sec-WebSocket-Extensions: permessage-deflate
   [ from here on, the socket carries WebSocket frames in both directions ]
   binary frame: opcode=2, FIN=1, payload=…  ────>
                                              <────  text frame:  opcode=1, FIN=1, payload="hi"
   ping:    opcode=9, FIN=1, payload=4-byte    ────>
                                              <────  pong:    opcode=A, FIN=1, payload=4-byte
   close:   opcode=8, FIN=1, payload=03 E8     ────>  close:   opcode=8, FIN=1, payload=03 E8
                                              (TCP FIN)
```

The key insight: after the upgrade, there is no more HTTP semantics.
The bytes on the wire are pure WebSocket frames. Intermediaries
(proxies, load balancers) that pass HTTP but cannot speak WebSocket
will break here — that's why `Upgrade: websocket` and `Connection:
Upgrade` are hop-by-hop headers in HTTP/1.1.

## 2. The Handshake: `Sec-WebSocket-Key` and `Sec-WebSocket-Accept`

The handshake is a one-shot proof that both sides speak WebSocket
and not just plain HTTP. The mechanism is deliberately old-fashioned:

1. The client generates 16 random bytes, base64-encodes them, and
   sends them as `Sec-WebSocket-Key`.
2. The server concatenates that key with the magic GUID
   `258EAFA5-E914-47DA-95CA-C5AB0DC85B11` (hardcoded in RFC 6455
   §1.3), takes the SHA-1 of the concatenation, and base64-encodes the
   20-byte digest. That becomes `Sec-WebSocket-Accept`.
3. The client does the same computation and compares; if it matches,
   the server is WebSocket-aware, and the client switches to frame
   mode. If it doesn't, the server is just an HTTP server that
   ignored the Upgrade request, and the client must fall back.

In code (Python):

```python
import base64, hashlib, os

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def make_key():
    return base64.b64encode(os.urandom(16)).decode()

def make_accept(key: str) -> str:
    digest = hashlib.sha1((key + GUID).encode()).digest()
    return base64.b64encode(digest).decode()

# client → "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=="
# server reply: base64(sha1(key + GUID))
#   = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=" (matches the RFC 6455 example)
```

The handshake is **not** a security mechanism — SHA-1 of a known GUID
plus a public value is trivially computable by any party. The point
is to *detect* intermediaries that don't speak WebSocket (cache
proxies that would happily serve back a cached 200 response). It's a
protocol-version liveness check, not authentication. Authentication
and confidentiality come from running the upgrade over TLS (the
`wss://` scheme) and from application-layer tokens in the headers
(e.g. `Sec-WebSocket-Protocol` or `Authorization`).

## 3. Frame Format

Once the handshake completes, every byte on the wire is part of a
WebSocket frame. The frame header layout (RFC 6455 §5.2):

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/63)           |
|N|V|V|V|       |S|             |   (only present when needed) |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127   |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set (32)   |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+--------------------------------+-------------------------------+
|                     Payload Data …                            |
+---------------------------------------------------------------+
```

Field by field:

- **FIN (1 bit)** — set if this frame is the final one of a message.
  Cleared on continuation frames (see §5).
- **RSV1, RSV2, RSV3 (3 bits)** — reserved. Must be 0 unless an
  extension was negotiated. The most common use: RSV1 set = the
  frame's payload is compressed with `permessage-deflate` (RFC 7692,
  see §7).
- **Opcode (4 bits)** — defines what this frame is. See §4.
- **MASK (1 bit)** — set if the payload is XOR-masked with a 32-bit
  masking key. **MUST be 1 for frames sent from client to server**;
  the server MUST close the connection if it receives an unmasked
  client frame. MAY be 0 for server-to-client frames; the client
  SHOULD close the connection if it receives a masked server frame.
- **Payload length (7 bits)** — overloaded:
  - 0–125 → the actual payload length in bytes.
  - 126 → the next 2 bytes are an unsigned 16-bit big-endian length.
  - 127 → the next 8 bytes are an unsigned 64-bit big-endian length.
  The 64-bit case is the only reason WebSocket requires a 64-bit
  length-aware reader. In practice implementations cap it at the
  receiver's configured maximum (often 1–16 MB).
- **Masking-key (32 bits)** — present iff MASK=1. Used to XOR the
  payload, byte by byte, cyclically (see §5).
- **Payload Data** — application bytes, masked if MASK=1.

A simple server-side frame parser in Python:

```python
def read_frame(sock) -> tuple[int, bytes]:
    b0, b1 = sock.recv(2)
    fin     = b0 & 0x80
    rsv     = b0 & 0x70
    opcode  = b0 & 0x0F
    masked  = b1 & 0x80
    plen    = b1 & 0x7F

    if plen == 126:
        plen = int.from_bytes(sock.recv(2), "big")
    elif plen == 127:
        plen = int.from_bytes(sock.recv(8), "big")

    if masked:
        mask = sock.recv(4)
        raw  = sock.recv(plen)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
    else:
        payload = sock.recv(plen)

    return opcode, payload
```

The first byte `b0` is read with `& 0x80` (high bit) for FIN, `& 0x70`
for RSV, `& 0x0F` for opcode. The second byte `b1` is read with `&
0x80` for the MASK bit and `& 0x7F` for the 7-bit payload length.

## 4. Opcodes

The 4-bit opcode carries the *type* of frame. Only the low 4 bits are
defined:

```
   opcode   frame type       semantic
   ------   --------------   ----------------------------------------------
   0x0      continuation     continues a fragmented message
   0x1      text             payload is UTF-8 text (MUST be valid UTF-8)
   0x2      binary           payload is opaque bytes
   0x3-0x7  reserved         reserved for further non-control frames
   0x8      close            close the connection; carries 2-byte status
   0x9      ping             keepalive / liveness probe
   0xA      pong             reply to a ping
   0xB-0xF  reserved         reserved for further control frames
```

Two important rules:

- Control frames (0x8–0xA) carry at most 125 bytes of payload (the
  7-bit length only; extended length is forbidden). They also MUST
  set FIN=1; they cannot be fragmented. They MAY be inserted in the
  middle of a fragmented data message — the receiver must service them
  before continuing the data stream.
- A new data message (text or binary) MUST NOT start until the
  previous one is complete. Continuation frames (opcode 0) carry the
  rest of a fragmented message.

The close frame carries a 2-byte big-endian status code, optionally
followed by UTF-8 reason text. Standard codes:

```
   1000  normal closure
   1001  endpoint going away (page closed, server restarting)
   1002  protocol error
   1003  unsupported data type
   1005  no status received (never on the wire — local-only)
   1006  abnormal closure (never on the wire — connection lost)
   1007  invalid UTF-8 in text frame
   1008  policy violation
   1009  message too big
   1011  internal server error
   1015  TLS handshake failure (local-only)
```

When closing, the side that initiates sends a close frame; the other
side MUST echo a close frame back before tearing down TCP. If the
peer doesn't echo within a reasonable timeout, the connection is
abandoned (status 1006 locally).

## 5. Masking

Client-to-server frames MUST be XOR-masked. The masking key is a
freshly generated 32-bit random value, sent in the clear in the
header. The payload is XORed with the 4-byte key cyclically:

```
   transformed[i] = original[i] XOR mask[i mod 4]
```

Decode is identical: XOR is its own inverse. Why do this, when the key
is sent in plaintext? The answer is *not* cryptographic — it's a
defense against protocol-confusion attacks on intermediary caches
(see the original rationale, the "cold-cache attack" described in
the WebSocket Threat Model RFC 6455 §10.7). Some pre-2010 HTTP
servers and caching proxies would interpret bytes that *looked* like
HTTP requests inside the body of a request as pipeline commands. A
malicious page could craft a WebSocket payload that, to such an
intermediary, looked like a POST to an internal endpoint — a cache
poisoning vector.

XOR masking the payload with a fresh per-frame key invalidates any
fixed-pattern attack. The attacker can't predict the masking key at
the time they construct the payload, so they can't pre-construct a
masked payload that decodes to a chosen plaintext. The 4-byte key
is sufficient because the threat model is *intermediary confusion*,
not confidentiality — TLS provides confidentiality when needed
(`wss://`).

Server-to-server frames need not be masked: the server is a trusted
endpoint, and the threat model doesn't apply. The client should still
enforce: if it receives a masked server frame, it should fail the
connection.

A trivial implementation of masking using Python's `int.from_bytes`
for speed:

```python
def apply_mask(data: bytes, mask: bytes) -> bytes:
    out = bytearray(len(data))
    m = int.from_bytes(mask, "big")
    # process 4 bytes at a time
    for i in range(0, len(data) - 3, 4):
        w = int.from_bytes(data[i:i+4], "big")
        out[i:i+4] = (w ^ m).to_bytes(4, "big")
    # tail
    for i in range(len(data) - (len(data) % 4), len(data)):
        out[i] = data[i] ^ mask[i % 4]
    return bytes(out)
```

Real implementations either process in 4-byte chunks like the above,
or use a vectorized approach (e.g. SIMD XOR or `bytes(0 for _ in
mask)` then `bytes-translated`). The masking step is the dominant CPU
cost on the client side for large frames.

## 6. Fragmentation

A single logical message can be split across multiple frames. The
first frame has the actual opcode (text or binary) and `FIN=0`; each
subsequent frame has opcode 0 (continuation) and `FIN=0` on all but
the last, which has `FIN=1`. So a 200 KB binary message sent in 64 KB
chunks looks like:

```
   frame 1: FIN=0, opcode=2, len=65536
   frame 2: FIN=0, opcode=0, len=65536
   frame 3: FIN=0, opcode=0, len=65536
   frame 4: FIN=1, opcode=0, len=32768
   total: 200000 bytes
```

Why fragment?

1. The sender doesn't know the total message size when it starts
   sending — typical of streamed TTS, ASR, or chat. Fragmentation
   lets you emit frames as data is produced, without buffering the
   whole message.
2. To interleave with control frames. A long-running message can be
   paused to send a PING/PONG, then resumed.
3. To respect the receiver's backpressure. Sending a 100 MB message in
   one frame would block the TCP socket for the entire duration;
   chunking lets the receiver's ACKs throttle the sender.

Control frames MAY arrive mid-message. The receiver must service them
*immediately* and then continue the data stream. This means a
fragmented data message is not actually atomic at the transport layer
— a PONG frame can be wedged in between any two fragments.

The receiver reassembles the message by concatenating the payloads of
all frames of the same message in order. The text-message decoder must
also re-validate UTF-8 only after the final frame — the boundary
between two fragments may fall in the middle of a multi-byte UTF-8
sequence. So a 4-byte UTF-8 emoji split across two fragments must not
be individually validated.

## 7. Subprotocols (`Sec-WebSocket-Protocol`)

A client may advertise a list of application-layer subprotocols it
speaks:

```
   Sec-WebSocket-Protocol: chat, superchat, mqtt-3.1.1
```

The server picks one (or none) and echoes it back:

```
   Sec-WebSocket-Protocol: chat
```

The chosen subprotocol is then the *contract* for what bytes mean on
the wire. WebSocket is just a transport; `chat`, `superchat`, and
`mqtt-3.1.1` define entirely different framing on top. This is
important: WebSocket's own opcodes (text, binary) carry no application
semantics. They're just transport hints.

Common subprotocols include:

- **MQTT over WebSocket** — `mqtt-3.1.1`, `mqtt-5`. Many IoT backends
  expose MQTT over WebSocket so they can be reached from a browser.
- **STOMP** — `v10.stomp`, `v11.stomp`, `v12.stomp`. A simple
  text-oriented messaging protocol popular in Spring Boot.
- **WAMP** — `wamp.2.json` etc. RPC + PubSub, popular in JavaScript
  frameworks.
- Custom — `chat.v1`, `live-transcription.v2` — versioned in the
  subprotocol name to allow schema evolution.

If the server doesn't accept any of the offered subprotocols, it MUST
send back the 101 with no `Sec-WebSocket-Protocol` header (or fail the
handshake). The client then decides whether to proceed without a
contract.

## 8. Extensions: `permessage-deflate` (RFC 7692)

The single widely-deployed WebSocket extension is
`permessage-deflate`, which zlib-compresses the payload of data
messages. It is negotiated via the `Sec-WebSocket-Extensions`
header:

```
   Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits
```

The server replies with the parameters it accepts:

```
   Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits=10; server_max_window_bits=10
```

Once negotiated, the RSV1 bit (the high RSV bit) is overloaded: set
RSV1=1 on the *first* frame of a message to indicate that the
message's payload is a zlib-compressed stream (using the DEFLATE
algorithm with no zlib header, the raw DEFLATE blocks). The receiver
decompresses by feeding the concatenated payload bytes into a
zlib stream initialized with `wbits = -window_bits` (negative, raw,
no header).

The wrinkle is the **context takeover**. By default, the zlib stream
persists across messages — the compressor keeps its dictionary, so
small repeated messages like `{ "type": "tick", "v": 42 }` can be
compressed to a few bytes after the first one. To disable this,
either side can negotiate `client_no_context_takeover` and/or
`server_no_context_takeover`; each message then resets the zlib
state, trading compression ratio for memory.

A careful server implementation will:

- Cap the decompression buffer. A 1 kB compressed payload can
  decompress to megabytes — the classic "WebSocket zip-bomb"
  attack. Apply a hard limit on decompressed size and abort the
  connection if exceeded.
- Reset the zlib stream on protocol error.
- Not enable `permessage-deflate` for binary frames whose semantics
  require no transformation (e.g. binary streams that are already
  gzip-compressed — double compression only hurts).

The `Sec-WebSocket-Extensions` header can also carry other extensions
(e.g. `permessage-brotli` in drafts), but `permessage-deflate` is the
only standardized one.

## 9. Common Pitfalls

1. **Reading a partial frame.** A single `recv()` on the underlying
   TCP socket may return any number of bytes from 1 to N — there is
   no guarantee that a frame's bytes arrive in one read. Always loop
   until you have a full frame's worth, or use a buffered reader.
2. **Forgetting to mask client frames.** A server that accepts
   unmasked client frames violates the spec and exposes itself to
   cache-confusion attacks via confused intermediaries. Always mask
   on the client side and reject unmasked client frames on the server
   side.
3. **Sending the close frame without an echoed close.** The initiating
   side should send close, wait for the peer's close frame, then tear
   down TCP. Tearing down immediately can cause the peer to receive
   a TCP RST and report status 1006 (abnormal closure) instead of
   the intended status.
4. **Mis-validating UTF-8.** Text frames must be valid UTF-8 *when
   reassembled* — not per-frame. If you validate each fragment
   independently and a multi-byte character spans the boundary, you'll
   reject a valid message.
5. **Compression bombs.** With `permessage-deflate`, an attacker can
   send a small compressed payload that decompresses to gigabytes.
   Cap decompression in flight, not just final size.
6. **Trusting `Origin` for security.** The `Origin` header is for the
   server to decide whether to accept the upgrade; it does not
   authenticate the user. Cross-site request forgery is still
   possible — pair `Origin` checks with CSRF tokens or session
   cookies.
7. **Sending binary data as text.** Text frames MUST be valid UTF-8.
   A binary frame (opcode 2) is for opaque bytes. Pick the right
   opcode — mixing them confuses intermediaries and browsers.

## References

- RFC 6455 — *The WebSocket Protocol*. https://www.rfc-editor.org/rfc/rfc6455.html
- RFC 7692 — *Compression Extensions for WebSocket*
  (`permessage-deflate`). https://www.rfc-editor.org/rfc/rfc7692.html
- RFC 8441 — *Bootstrapping WebSockets with HTTP/2*. Defines the
  `:protocol` extended CONNECT that lets WebSocket run over HTTP/2
  streams. https://www.rfc-editor.org/rfc/rfc8441.html
- RFC 7935 — *The WebSocket Protocol's Handshake Security* (the
  SHA-1/GUID liveness check rationale, RFC 6455 §1.3 + §10.7).
- MDN Web Docs — *Writing WebSocket servers* (byte-level tutorial
  with parser examples).
  https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API/Writing_WebSocket_servers
- MDN Web Docs — *WebSocket* (browser API).
  https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- WHATWG — *HTML Living Standard*, §9 The WebSocket API (the
  browser interface). https://html.spec.whatwg.org/multipage/web-sockets.html
- IETF — *websocket* WG archive (history of the spec).
  https://datatracker.ietf.org/wg/hybi/documents/
- Wikipedia — *WebSocket* (overview and history).
  https://en.wikipedia.org/wiki/WebSocket

## Cross-References

- [WebSocket (API overview)](./websocket.md) — high-level usage.
- [HTTP/1.1](./http1.md) — the protocol that the Upgrade handshake
  runs on top of.
- [HTTP/2](./http2.md) — RFC 8441 lets WebSocket run over HTTP/2
  streams.
- [TLS / HTTPS](./https.md) — the `wss://` transport.
- [QUIC internals](./quic-internals.md) — comparison: why QUIC's
  multiplexed streams don't require WebSocket's framing tricks.
