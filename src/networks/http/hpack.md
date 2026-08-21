# HPACK — HTTP/2 Header Compression (RFC 7541)

> See also [HTTP/2](./http2.md) for the framing layer that HPACK sits
> inside, and [QPACK](./qpack.md) for how HPACK had to be re-engineered
> for HTTP/3. This page covers the byte-level mechanics: integer
> encoding, the static and dynamic tables, Huffman coding, and the
> per-stream state machine that makes HPACK work.

## 1. Why HPACK Exists

HTTP/1.x ships headers as plain ASCII lines, one per line, terminated
by CRLF. A typical modern request — with cookies, auth tokens, content
negotiation, browser fingerprints, and security headers — easily runs
800–1500 bytes of header per request, most of it repeated identically
on every subsequent request to the same origin. Over HTTP/1.1, where
the client typically opens 6 parallel TCP connections and pipelines a
few requests each, the wasted bandwidth is real but tolerable. Over
HTTP/2, where dozens of multiplexed streams share one TCP connection
and one TLS context, the repetition becomes the dominant cost.

HPACK (defined alongside HTTP/2 in 2015) cuts that cost with three
techniques layered together:

1. A **shared static table** of 61 common headers (e.g.
   `:method: GET`, `accept-encoding: gzip`), indexed by a small
   integer.
2. A **shared dynamic table** maintained on both sides — when the
   encoder emits a header it has not seen before, it adds it to the
   table so that the next occurrence is one integer.
3. **Huffman coding** of header names and values using a fixed code
   tuned for the most common bytes seen in HTTP headers.

A 1.4 kB headers-only HTTP/1.1 request typically compresses to under
100 bytes after the first few requests in an HPACK session. That ratio
is the practical reason HTTP/2 wire size looks so much smaller than
HTTP/1.1 in the lab.

## 2. The Three Layers, Conceptually

```
   encoder side                                  decoder side
   ┌────────────────────────────────────┐        ┌────────────────────────────────────┐
   │  for each header in the request:    │        │  for each header in the block:     │
   │   1. (name, value) match in        │ byte   │   1. read representation byte      │
   │      static or dynamic table?      │ stream │   2. branch on representation type │
   │   2. if yes → emit index           │ ─────> │   3. apply Huffman + integer       │
   │   3. if no → literal encoding +    │ over   │      decoding                     │
   │      optionally add to dyn. table  │ TCP+TLS│   4. optionally insert into dyn.   │
   │   4. huffman-encode any strings    │        │      table                         │
   └────────────────────────────────────┘        └────────────────────────────────────┘
```

Three things to internalise:

- The dynamic table is **per HTTP/2 connection**, not per stream.
  Every stream on the same connection shares one HPACK context.
- The dynamic table is **strictly FIFO**: insertions append to the
  end, evictions drop from the front when the total size exceeds the
  agreed-upon `SETTINGS_HEADER_TABLE_SIZE`.
- All state must converge on both sides: any divergence between
  encoder and decoder dynamic tables means every subsequent request
  is broken. This is why HPACK is fundamentally **order-dependent**
  — and why HTTP/3 had to invent QPACK.

## 3. Integer Encoding

HPACK integers are variable-length, big-endian, and use a clever
encoding that packs the value into the low bits of a "representation"
byte and extends into continuation bytes when needed. This is the
single most reused primitive in the spec, used for indexes, lengths,
and dynamic-table size updates.

The function takes two parameters: an integer value `I`, and a prefix
length `N` (the number of low bits available in the representation
byte, 1..8). The algorithm:

```
if I < 2^N - 1:
    encode I in the N low bits of the representation byte, done.
else:
    set the N low bits of the representation byte to all-ones (2^N-1)
    I -= 2^N - 1
    while I >= 128:
        emit (I % 128 + 128)   ← continuation byte, MSB = 1
        I /= 128
    emit I                     ← final byte, MSB = 0
```

Concretely, with `N = 5` (the prefix used for the index in a *literal
with incremental indexing* representation), here's how various values
encode:

```
   value   encoded bytes (hex)
   -----   -------------------------
   0       0x00                      ← fits in 5 bits
   10      0x0a
   30      0x1e
   31      0x1f                     ← saturates the prefix
   31 →    0x1f 0x00                ← after saturation, continuation = 0
   1337 →  0x1f 0x9a 0x0a           ← (1337 - 31 = 1306; 1306 = 10 + 9*128 + 0*16384)
```

The decoder reads the prefix bits from the first byte; if they equal
`2^N - 1`, it reads continuation bytes — each contributing 7 bits —
until it finds a byte whose MSB is 0. The continuation bytes are
little-endian in their low 7 bits, which is slightly unusual but
matches the protobuf varint scheme (see
[Protocol Buffers Encoding](../../backend/serialization/protobuf-encoding.md)).

Why a prefix? Because every HPACK header representation byte doubles
as a *type tag*: its high bits encode "indexed header literal" vs
"literal with incremental indexing" vs "literal without indexing" vs
"literal never-indexed" vs "dynamic table size update". The low bits
then carry either an index, or the starting value of a length field.
Reusing one byte for two purposes is what keeps HPACK dense.

## 4. The Static Table (61 Entries)

The static table is hardcoded in RFC 7541 Appendix A. The first 61
entries (index 0 is reserved as "not in the table"). A small excerpt:

```
   idx   name                        value (example)
   ---   --------------------------  ----------------------------------
   1     :authority                  (no value, used with literal)
   2     :method                     GET
   3     :method                     POST
   4     :path                       /
   5     :path                       /index.html
   6     :scheme                     http
   7     :scheme                     https
   8     :status                    200
   9     :status                    204
   ...
   15    accept-encoding             gzip, deflate
   ...
   23    authorization               (no value)
   24    cache-control               (no value)
   ...
   31    if-modified-since           (no value)
   ...
   38    cookie                     (no value)
   ...
   59    via                        (no value)
   60    x-forwarded-for
   61    x-request-id
```

The convention: indexes 1..61 are *static*; indexes 62+ refer to the
*dynamic* table at offset (index - 62). When the dynamic table has 5
entries, index 66 refers to the 5th entry.

Most "easy" HTTP/2 requests — `GET /index.html` with standard headers —
compress to almost nothing because every field is in the static table.
A typical first-line of headers for an idempotent GET might be five
bytes:

```
   0x82    → indexed header, idx=2     (:method: GET)
   0x86    → indexed header, idx=6     (:scheme: http)
   0x84    → indexed header, idx=4     (:path: /index.html)
   0x41 0x8c 0xf1 0xe3 0xc2 0xe3 0x62
            → literal-with-incremental-indexing, name idx=1
              (:authority), value = Huffman-encoded "example.com"
```

The Huffman blob `0x8c 0xf1 0xe3 0xc2 0xe3 0x62` decodes to
`example.com` — 11 bytes down to 6. Combined with the static-table
hits, the whole `:method: GET, :scheme: http, :path: /index.html,
:authority: example.com` request line occupies 11 bytes on the wire,
vs. ~70 bytes in HTTP/1.1.

## 5. The Dynamic Table

The dynamic table is the heart of HPACK. Its semantics:

- Insertions happen at the *front* (newer entries have smaller
  indexes). When you emit a "literal with incremental indexing"
  representation, the header is appended to the front of the dynamic
  table and gets index 62.
- The table has a maximum size in bytes, negotiated via the
  `SETTINGS_HEADER_TABLE_SIZE` setting (default 4096). Size is the
  sum of `(name_length + value_length + 32)` per entry; the 32-byte
  overhead accounts for the data structure.
- When an insertion would exceed the size limit, entries are evicted
  from the *tail* until it fits. If a single new entry is larger
  than the entire table, the table is cleared and the new entry is
  *not* inserted.
- The encoder may emit a *dynamic table size update*
  (representation byte `0x20 + N` with prefix 5) at any point to
  shrink the table, which forces the decoder to evict entries from
  the tail. The new size cannot exceed the value the peer signalled
  in `SETTINGS_HEADER_TABLE_SIZE`.

The size-update mechanism is the lever that lets a server say "I only
have 4 KB to spare for your headers" and the client immediately drops
its table to fit. In practice the value bounces between 4096 (default)
and 65536 (Cloudflare's typical server setting).

## 6. Huffman Encoding

RFC 7541 Appendix B specifies a fixed Huffman table tuned for HTTP
header bytes. The table is asymmetric: the most common bytes (e.g.
lowercase 'a'-'z', '/', '.', ':') get short codes (5 bits), while
rare bytes (high-bit set, control characters) get long codes (20+
bits). The longest code in the table is 30 bits, for ASCII byte
255.

The encoder is straightforward: walk the input bytes, emit the
corresponding Huffman code bit-by-bit into an output buffer. After
the last byte, the bit buffer is padded with `1`s to a byte
boundary. The decoder is symmetric: walk the bit stream, descend the
Huffman tree, emit a byte when it reaches a leaf.

Encoding choice is left to the encoder: it may Huffman-encode or
leave strings as-is. The high bit of the length prefix tells the
decoder which (1 = Huffman, 0 = raw). A well-tuned encoder Huffman-
encodes strings that come out shorter, and leaves short or
uncompressible strings raw. A 5-character cookie value of `abcde`
might actually be longer after Huffman coding (the length prefix
overhead + 5 * 5 bits = 26 bits, vs. 5 raw bytes = 40 bits but with
simpler decode). The breakeven depends on the actual byte
distribution.

The 30-bit code length matters because it caps the worst-case
expansion: a 0xFF byte Huffman-codes to 30 bits, so an attacker who
sends a string of N 0xFF bytes can inflate HPACK's encoded output to
~3.7× the input size before decoding. HPACK implementations must cap
the literal header field size and reject expansions beyond a sane
limit (the spec recommends 12× — see CVE-2020-1xxx-class
"HPACK bomb" attacks). A 4096-byte `SETTINGS_HEADER_TABLE_SIZE` plus
a 3.7× expansion means ~15 KB of compressed input could blow up to
~64 MB of decoded state if the encoder were malicious — so the
decoder also needs a hard cap on the table size, not just the
compressed size.

## 7. The Four Representation Types

A header representation starts with one byte whose top 3-4 bits
encode the type:

| Prefix bits        | Type                                | Effect on dynamic table            |
|--------------------|-------------------------------------|-------------------------------------|
| `1`                | Indexed Header Field                | (no change)                        |
| `01`               | Literal Header Field with Incremental Indexing | Appends to dynamic table |
| `0000`             | Literal Header Field without Indexing          | No change                |
| `0001`             | Literal Header Field Never Indexed             | No change; "never index this"   |
| `001`              | Dynamic Table Size Update                      | Shrinks the dynamic table |

The "never indexed" form is the subtle one. It tells every
intermediary along the path: do not ever index this header. It is
mandatory when the header value is sensitive to value-based
correlation attacks — for example `Authorization: Bearer …` or
`Cookie: session=…`. Without it, an attacker who can plant a chosen
prefix in a victim's session cookie can recover the value byte-by-byte
using the difference in compression ratio between an indexed and a
non-indexed hit (the CRIME/BREACH family of attacks on TLS
compression). The default in good HPACK implementations is to never
index `Authorization`, `Cookie`, `Set-Cookie`, and any header the
server explicitly marks via the `never-indexed` hint.

## 8. Per-Stream State, Per-Connection Tables

HPACK's central design constraint is that **header blocks are decoded
in order**. The HTTP/2 spec mandates that an endpoint must not
process a `HEADERS` or `CONTINUATION` frame for one stream until the
`HEADERS` frame of any prior stream on the connection has been
completely decoded.

That ordering requirement is fine on HTTP/2 because HTTP/2 runs over
TCP, which delivers bytes in order. There's no risk that stream A's
header block arrives after stream B's, even if stream B's `HEADERS`
frame was sent later.

This single sentence is exactly why HPACK cannot be reused for
HTTP/3: QUIC's streams are independent and can be reordered across
the wire. If HPACK ran over QUIC directly, a stream blocked on
header-block arrival would block every other stream on the
connection — recreating head-of-line blocking at the header layer,
which HTTP/3 was supposed to eliminate.

QPACK (RFC 9204) solves this by:

- Splitting the dynamic table into a separate "encoder stream" and
  "decoder stream" so that inserts and acks are out-of-band relative
  to any request stream.
- Adding a `Required Insert Count` and a `Base` to every field
  section. The decoder can decode *if the inserts it references have
  been received* — otherwise it can either block (rare) or skip
  (with explicit signalling).
- Introducing a `NeverIndexed` literal representation identical to
  HPACK's, plus an explicit acknowledgement protocol so the encoder
  can evict entries the decoder has confirmed.

The upshot: HPACK is dense and simple but assumes a reliable,
in-order byte stream; QPACK is denser in the steady state but adds
~4 bytes per field section for the synchronization references.

## 9. Worked Encoding

Take this HTTP/1.1 request:

```
GET / HTTP/1.1
Host: example.com
User-Agent: curl/8.0.0
Accept: */*
```

A naive HTTP/1.1 encoding is ~80 bytes of header text. A
representative HPACK encoding produces something close to:

```
   82          indexed  2   → :method: GET
   86          indexed  6   → :scheme: http
   04          indexed  4   → :path: /
   41 8c f1 e3 c2 e3 62     literal with incremental indexing,
                            name=idx 1 (:authority),
                            value=Huffman("example.com") [6 bytes]
   5f c1 a8 b1 e3 a2 65 b6
   5f 8d 9b d9 ab           literal with incremental indexing,
                            name=idx 24 (cache-control — wait, actually
                            idx for user-agent is 57? in older tables
                            user-agent was 58)
   50                         ← literal without indexing, prefix 4
   ...
```

The point is: most of the request line collapses to one-byte indexed
hits, and even the variable fields go through Huffman coding. After
two requests to the same origin, `Host: example.com` and `User-Agent:
curl/8.0.0` are both in the dynamic table — the third request becomes
two indexed header bytes each.

## 10. Common Pitfalls

1. **Forgetting to apply the size update on SETTINGS_HEADER_TABLE_SIZE
   update.** When a peer sends a smaller table size mid-connection,
   the encoder must emit a dynamic-table-size-update representation
   *before* any further header block. Otherwise the decoder's table
   has stale entries that the encoder's does not.
2. **Indexing sensitive headers.** Cookies and bearer tokens must be
   sent with the never-indexed representation. Static-table matches
   against `Authorization` (idx 23) are an easy pitfall.
3. **Reusing the dynamic table across connections.** HPACK state is
   *per connection*. Don't try to share a dynamic table across HTTP/2
   connections even to the same origin — the encryption and the
   SETTINGS exchange may differ.
4. **HPACK bombs.** Cap the decoded size at the negotiated table
   size *plus* a small slack, and reject header blocks whose
   declared length would push past it. Otherwise a malicious peer
   can balloon memory.
5. **Forgetting that `:status` is in the static table.** Many
   implementations hard-code the literal encoding for response
   status. Index 8 (`:status 200`) is a single byte and saves 7
   bytes per response.

## References

- RFC 7541 — *HPACK: Header Compression for HTTP/2*.
  https://www.rfc-editor.org/rfc/rfc7541.html
- RFC 7540 — *Hypertext Transfer Protocol Version 2 (HTTP/2)*.
  https://www.rfc-editor.org/rfc/rfc7540.html
- RFC 9113 — *HTTP/2* (the 2022 revision, obsoletes 7540; HPACK
  itself is unchanged). https://www.rfc-editor.org/rfc/rfc9113.html
- RFC 9204 — *QPACK: Field Compression for HTTP/3*. The successor
  spec; reading the differences section explains HPACK's limits.
  https://www.rfc-editor.org/rfc/rfc9204.html
- h2spec — conformance test tool for HTTP/2 and HPACK.
  https://github.com/summerwind/h2spec
- Cloudflare — *"Optimising the HPACK header table in Go's HTTP/2"*
  by Marie Janssen — engineering notes on the Go `golang.org/x/net/http2/hpack`
  implementation. https://blog.cloudflare.com/optimizing-http-2-header-compression-in-go/
- h2o — *h2o HTTP/2 server, HPACK implementation* (C, used in
  benchmarks). https://github.com/h2o/h2o
- RFC 7685 — *TLS ClientHello Padding* and CRIME/BREACH attacks (the
  threat model that motivates the never-indexed representation).
  https://www.rfc-editor.org/rfc/rfc7685.html

## Cross-References

- [HTTP/2](./http2.md) — the framing layer.
- [QPACK](./qpack.md) — HPACK's HTTP/3 successor.
- [QUIC internals](./quic-internals.md) — why HPACK had to be
  redesigned for HTTP/3.
- [HTTPS / TLS](./https.md) — the record layer below HTTP/2.
