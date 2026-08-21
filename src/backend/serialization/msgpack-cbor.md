# MessagePack and CBOR — Compact Binary JSON Replacements

JSON is the lingua franca of the web, but it carries a price: every key is a UTF-8 string, every value carries its type implicitly via delimiters, and parsing requires a stateful UTF-8 / number / structural-char machine. For high-throughput systems that spend significant CPU on parsing, the binary alternatives **MessagePack** and **CBOR** (Concise Binary Object Representation) preserve JSON's six-type data model while cutting wire size by 30-60% and parse latency by 3-10x. They are self-describing (no schema required) and dynamically typed, which makes them drop-in replacements for many JSON pipelines.

## Why a Binary JSON?

Consider a representative API payload:

```json
{"id":42,"name":"Alice","active":true,"tags":["staff","admin"],"balance":3.14}
```

That is 71 bytes of UTF-8 plus the parsing cost: the parser must tokenize `{`, `"id"`, `:`, `42`, `,`, `"name"`, `:`, `"Alice"`, …, switching state at every delimiter. The same data in MessagePack:

```
85       fixmap of length 5
a2 69 64        fixstr(2) "id"     2a       positive fixint 42
a4 6e 61 6d 65  fixstr(4) "name"  a5 41 6c 69 63 65   fixstr(5) "Alice"
a6 61 63 74 69 76 65   fixstr(6) "active"  c3  true
a4 74 61 67 73  fixstr(4) "tags"
  92             fixarray of length 2
    a5 73 74 61 66 66   fixstr(5) "staff"
    a5 61 64 6d 69 6e   fixstr(5) "admin"
a7 62 61 6c 61 6e 63 65   fixstr(7) "balance"
cb 40 09 1e b8 51 eb 85 1f   float64 3.14
```

~70 bytes — only marginally smaller than JSON for this case, but the parser's job is dramatically simpler: every byte's first 3 bits tell it the type and length. There are no delimiters to track.

## MessagePack

MessagePack was created by Sadayuki Furuhashi in 2009 (msgpack.org). Its design goal was minimalism: a strict superset of JSON's data model with the smallest possible encodings for common cases.

### Encoding Categories

MessagePack's spec defines ~8 broad categories of leading-byte ranges, each with a few specialized encodings. The byte's high 3 bits select the category.

| Leading byte range | Type | Encoding |
|--------------------|------|----------|
| `0x00`–`0x7f` | positive fixint | value is the byte itself |
| `0xe0`–`0xff` | negative fixint | value is `byte - 0x100` |
| `0x80`–`0x8f` | fixmap | count = byte & 0x0f |
| `0x90`–`0x9f` | fixarray | count = byte & 0x0f |
| `0xa0`–`0xbf` | fixstr | length = byte & 0x1f |
| `0xc0` | nil | (no payload) |
| `0xc1` | (never used — reserved as error marker) | — |
| `0xc2`–`0xc3` | false, true | (no payload) |
| `0xc4`–`0xc6` | bin 8 / 16 / 32 | 1/2/4-byte length, then bytes |
| `0xc7`–`0xc9` | ext 8 / 16 / 32 | length, type byte, then payload |
| `0xca`–`0xcb` | float 32 / float 64 | IEEE 754 |
| `0xcc`–`0xcf` | uint 8 / 16 / 32 / 64 | big-endian |
| `0xd0`–`0xd3` | int 8 / 16 / 32 / 64 | big-endian, two's complement |
| `0xd4`–`0xd8` | fixext 1 / 2 / 4 / 8 / 16 | type byte + fixed payload |
| `0xd9`–`0xdb` | str 8 / 16 / 32 | 1/2/4-byte length, then UTF-8 |
| `0xdc`–`0xdd` | array 16 / 32 | 2/4-byte count, then items |
| `0xde`–`0xdf` | map 16 / 32 | 2/4-byte count, then key/value pairs |

The `fix*` encodings are the secret to MessagePack's compactness. A small map of 5 entries needs only 1 byte of overhead (`0x85`); in JSON the same overhead is 4 chars (`,`, `{`, `}`, `:`). A small string under 32 bytes needs 1 byte of overhead; in JSON that overhead is 2 bytes (the quotes).

The trade-off: there is **no integer wider than 64 bits**, **no native date/time**, **no distinct binary vs string type distinction at the parsing canonical level** (str and bin are separate categories, but historically the spec was ambiguous — pre-2.0 packs sometimes used str for binary data, breaking interop).

### Code Example

```python
import msgpack

data = {
    "id": 42,
    "name": "Alice",
    "active": True,
    "tags": ["staff", "admin"],
    "balance": 3.14,
}

packed = msgpack.packb(data, use_bin_type=True)
# 67 bytes (vs 71 for JSON)

unpacked = msgpack.unpackb(packed, raw=False)
# {'id': 42, 'name': 'Alice', 'active': True, 'tags': ['staff','admin'], 'balance': 3.14}
```

The `use_bin_type=True` and `raw=False` flags exist because of the legacy ambiguity: pre-2.0 MessagePack treated all strings as `bin`. New code should always set both.

### Extension Types

MessagePack supports user-defined extension types via the `ext` family. An ext is `(type byte, payload bytes)` — the type byte is a single signed value (`-128` to `127`); the payload is the raw bytes. Application code is responsible for serializing and deserializing the payload.

```python
import msgpack
from datetime import datetime, timezone

def encode_dt(obj):
    if isinstance(obj, datetime):
        return msgpack.packb(obj.timestamp())
    return obj

def ext_hook(code, data):
    if code == 1:
        return datetime.fromtimestamp(msgpack.unpackb(data), tz=timezone.utc)
    return msgpack.ExtType(code, data)

packed = msgpack.packb({"ts": datetime.now(timezone.utc)},
                       default=encode_dt,
                       datetime=True)
```

The `datetime=True` shortcut uses the built-in timestamp extension type (`-1`), which is one of the few "standard" extensions MessagePack informally standardized (negative type IDs are reserved for application use; positive IDs are reserved for future spec).

## CBOR — RFC 8949

CBOR (Concise Binary Object Representation, RFC 8949, December 2020) is the IETF's standardization of the same idea. CBOR was designed by Carsten Bormann after the IoT community realized MessagePack's spec was too informal for critical infrastructure. Where MessagePack is "good enough for interop, meh for spec", CBOR is "spec-first, exhaustive, forward-compatible".

### Major Types

CBOR's first byte is split: high 3 bits are the **major type** (0-7), low 5 bits are **additional information** (0-23 directly, 24-27 mean "next 1/2/4/8 bytes hold the value", 28-30 are reserved, 31 is the indefinite-length terminator).

```
+----+----+----+----+----+----+----+----+
| mt     | ai (additional information)    |
+----+----+----+----+----+----+----+----+
 bits 7-5  |        bits 4-0
```

| Major type | Meaning |
|-----------|---------|
| 0 | unsigned integer |
| 1 | negative integer (subtract from -1) |
| 2 | byte string |
| 3 | text string (UTF-8) |
| 4 | array |
| 5 | map |
| 6 | tag (semantic annotation on the next item) |
| 7 | floats, simple values, break |

Examples of single-byte encodings:

```
0x00 = unsigned int 0
0x0a = unsigned int 10
0x17 = unsigned int 23
0x18 = "next byte is uint" — payload 0xff means 255
0x20 = negative int -1
0x39 = "next 2 bytes are negative int"
0x40 = float16 0.0
0x41 = float16 1.0
0xc6 = tag 22 (expected base64 when encoded as string)
0xf6 = null (simple value 22)
0xf5 = true (simple value 21), 0xf4 = false
0x9f = indefinite-length array, terminated by 0xff (break)
```

### Indefinite Length

CBOR supports **indefinite-length encoding** for streams where the total count is unknown at write time. The opening byte for an array is `0x9f` (instead of a fixed `0x80 + count`), and a special **break** byte `0xff` terminates the array. The same works for maps (`0xbf`) and strings (a sequence of text-string chunks).

```
9f         # start indefinite array
  01       # uint 1
  02       # uint 2
  03       # uint 3
ff         # break
```

This is invaluable for real-time streaming: a producer can emit values as they arrive without buffering the whole array first.

### Tags

Tags (major type 6) annotate the *next* item with a semantic meaning. RFC 8949 defines a registry of standard tags; the most useful:

| Tag | Meaning |
|-----|---------|
| 0 | standard date-time string (RFC 3339) |
| 1 | epoch-based date/time (int or float seconds) |
| 2 | positive bignum (byte string, base 256 big-endian) |
| 3 | negative bignum |
| 4 | decimal fraction (`[exponent, mantissa]`) |
| 5 | bigfloat |
| 21 | expected base64url encoding |
| 22 | expected base64 encoding |
| 23 | expected base16 encoding |
| 24 | encoded CBOR data item (the byte string is itself CBOR) |
| 32 | URI |
| 33 | base64url string |
| 34 | base64 string |
| 35 | MIME message |
| 36 | CBOR Web Token (CWT) |
| 55 | self-described CBOR |
| 64 | extended time (RFC 9581) |
| 257 | array of sets (set semantics) |

Tags let CBOR carry types JSON cannot express: big integers (arbitrary precision), decimal fractions, URIs, MIME blobs, embedded CBOR. The tag registry is IANA-controlled; new tags require a registration but unregistered tags above 32767 are also valid for application use.

### Maps with non-string keys

Unlike JSON, CBOR allows any type as a map key — integers, byte strings, even other maps. This enables compact representations of sets (use map with bool values) and value-keyed lookups.

### Code Example

```python
import cbor2
from datetime import datetime, timezone

data = {
    "id": 42,
    "name": "Alice",
    "active": True,
    "tags": ["staff", "admin"],
    "balance": 3.14,
    "ts": datetime.now(timezone.utc),  # native, no custom encoder needed
}

packed = cbor2.dumps(data)            # ~80 bytes
# Note: bigger than msgpack because the datetime gets tag 1 + int payload

restored = cbor2.loads(packed)
assert restored["ts"].tzinfo is not None
```

```javascript
// Node.js — cbor package
const cbor = require('cbor');
const buf = cbor.encode({ id: 42, name: 'Alice', tags: ['staff'] });
// <Buffer a3 63 69 64 18 2a 64 6e 61 6d 65 65 41 6c 69 63 65 64 74 61 67 73 82 65 73 74 61 66 66>
const decoded = cbor.decode(buf);
```

### Self-Described CBOR

Tag 55 wraps a CBOR data item to make the bytes self-identifying on the wire. The bytes `d9 d9 f7` (the tag's encoding) prefix any CBOR payload to signal "the bytes that follow are CBOR." This is the equivalent of the `0x{}` magic byte sequence for other formats and is how a parser detects "is this CBOR?" without configuration.

## BSON — A Third Binary JSON, Used by MongoDB

BSON (Binary JSON, bsonspec.org) is a third format in the same family. It is **not** a MessagePack/CBOR descendant — it has its own spec. BSON is a length-prefixed, ordered document format used by MongoDB for both storage and wire protocol.

```
+-----------------+--------------------------------+
| int32 total len | elements                       |
+-----------------+--------------------------------+
| ...             | 0x00 terminator                |
+-----------------+--------------------------------+
```

Each element is `(type byte, name C-string, value)`. Type bytes include 0x01 (float64), 0x02 (string), 0x03 (document), 0x04 (array), 0x05 (binary with subtype), 0x08 (bool), 0x09 (datetime int64), 0x0a (null), 0x10 (int32), 0x12 (int64).

BSON is bigger than JSON on the wire (length prefixes, type bytes per element) but supports types JSON cannot (binary, datetime, int64, regex). Its strength is fast **field-by-field skipping** — a MongoDB query that projects one field does not need to parse the whole document. This is what MessagePack/CBOR cannot match without a schema: their tagless style forces full decode to find a field.

## Redis Internals

Redis uses MessagePack-adjacent encoding for its `HASH` field storage when memory pressure is high (via `listpack` / `intset` encoding in modern Redis 7+). The `ziplist` (older) and `listpack` (current) formats are MessagePack-inspired: small maps use 1-byte length prefixes, small integers are encoded inline as `int8`/`int16`/`int24`/`int32`/`int64`/`int64-LZF`. The convention "leading byte's range determines type" is borrowed wholesale.

Redis Streams (`XRANGE`) use a similar compact encoding for entry data, choosing between intset, listpack, and Quicklist (a doubly-linked list of ziplist nodes) based on size and access patterns.

## Performance Benchmarks

Approximate numbers, parsing the 71-byte JSON-vs-binary payload above on an x86-64:

| Format | Encode (ns) | Decode (ns) | Size (bytes) |
|--------|-------------|-------------|--------------|
| JSON (Python `json`) | 4 200 | 6 800 | 71 |
| MessagePack (Python `msgpack`) | 1 100 | 1 600 | 67 |
| CBOR (Python `cbor2`) | 1 500 | 2 100 | 78 |
| CBOR (Rust `ciborium`) | 280 | 420 | 78 |
| MessagePack (Rust `rmp-serde`) | 220 | 340 | 67 |
| JSON (Rust `serde_json`) | 480 | 780 | 71 |

Numbers will vary dramatically with payload shape (small ints vs floats vs strings), language runtime, and allocator. The robust takeaway: **MessagePack and CBOR cut parse latency by 3-5x vs JSON in interpreted languages** and by 1.5-2.5x in compiled languages, while shaving 10-30% off wire size. For pure-RPC microservices, Protobuf/Avro still win because schemas eliminate type dispatch.

## When to Use What

| Scenario | Best choice | Reason |
|----------|-------------|--------|
| Browser→server payloads you cannot put on a binary protocol | JSON | Universal support |
| Internal microservice RPC at high QPS | Protobuf / Avro | Schema-driven, faster, smaller |
| Cache values in Redis or local KV store | MessagePack | Compact, dynamic, no schema coupling |
| IoT / embedded systems needing standardization | CBOR | RFC 8949 + IANA tag registry, indefinite length |
| Cryptographic protocols (COSE, CWT) | CBOR | Native tag-based extensibility |
| MongoDB wire or persistent documents | BSON | Field-skip projection support |
| Long-running streams where you don't know the count upfront | CBOR | Indefinite-length encoding |

## Common Mistakes

- **Using MessagePack's legacy str type for binary data** — set `use_bin_type=True` everywhere, or old data will be decoded as UTF-8 strings.
- **Forgetting that MessagePack ints are big-endian** — when writing a custom encoder, BE is required.
- **Expecting CBOR's tag 0 (datetime string) and tag 1 (epoch int) to be interchangeable** — they are not; tag 1 is timezone-naive unless you also store an offset tag.
- **Treating CBOR's `0xf7` (undefined) as `null`** — undefined is distinct from null in CBOR; JavaScript's `undefined` maps to it, but JSON has no equivalent.
- **Comparing formats by size alone** — for hot paths, decode latency matters more than wire bytes if your network is not the bottleneck.
- **Picking MessagePack because "it's simpler"** — if you need datetime, decimal, bignum, or any semantic type, CBOR's tags save you from inventing a per-application extension type registry.

## Interview Questions

1. **What is the difference between MessagePack and CBOR?**
   MessagePack is a community spec with a minimal type system; CBOR (RFC 8949) is an IETF spec with major types, tags (semantic annotations), and indefinite-length encoding. CBOR is more extensible; MessagePack is simpler.

2. **Why is MessagePack smaller than JSON?**
   Single-byte leading prefixes encode type + length for short maps/arrays/strings/integers; no delimiters or repeated field-name quotes are needed.

3. **What does a "tag" mean in CBOR?**
   A tag (major type 6) annotates the next data item with a semantic meaning (e.g., tag 1 = epoch datetime, tag 2 = bignum). The tag registry is IANA-controlled. Tags let CBOR express types JSON cannot.

4. **What is indefinite-length encoding?**
   An array, map, or string opened with a special leading byte (e.g., `0x9f` for arrays) is followed by items until a `0xff` "break" byte. Useful when the producer doesn't know the count when starting to write.

5. **Why doesn't Redis just use JSON for hash fields?**
   JSON is verbose (string keys, structural delimiters) and slow to parse. Compact binary formats like listpack/intset are byte-dense and CPU-cheap, which matters at Redis's QPS.

## References

- MessagePack specification: https://github.com/msgpack/msgpack/blob/master/spec.md
- MessagePack website: https://msgpack.org/
- RFC 8949 — Concise Binary Object Representation (CBOR): https://www.rfc-editor.org/rfc/rfc8949.html
- RFC 9581 — CBOR extended time tag (tag 64): https://www.rfc-editor.org/rfc/rfc9581.html
- IANA CBOR tag registry: https://www.iana.org/assignments/cbor-tags/cbor-tags.xhtml
- BSON specification: https://bsonspec.org/
- MongoDB BSON reference: https://www.mongodb.com/docs/manual/reference/bson-types/
- Redis listpack / intset internals: https://redis.io/docs/reference/internals/
- ciborium (Rust CBOR library): https://docs.rs/ciborium
- cbor2 (Python CBOR library): https://cbor2.readthedocs.io/
- rmp-serde (Rust MessagePack): https://docs.rs/rmp-serde
- Carsten Bormann, "CBOR — a binary serialization format": https://datatracker.ietf.org/doc/html/rfc8949
