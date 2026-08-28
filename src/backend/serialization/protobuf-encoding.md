# Protocol Buffers — Wire Encoding Deep Dive

> See the [serialization overview](../serialization.md) for the broader
> landscape (text vs binary, schema vs schemaless, zero-copy). This
> page covers the byte-level encoding of Protocol Buffers as defined
> by Google's official spec, the `.proto` file syntax (proto2 vs
> proto3), and a practical comparison with Avro, Thrift, and JSON.
> Sibling page: [Avro](./avro.md).

## 1. The Design Idea

A protobuf message is a sequence of `(field_number, wire_type, value)`
triples. The encoder writes them in any order; the decoder reads them
in any order; missing fields take their default; unknown fields are
skipped silently. There is no length prefix on the message itself and
no schema on the wire — the schema is a contract shared out-of-band
between the writer and the reader (typically checked into a repo as a
`.proto` file).

The wire format is built from exactly two primitives:

1. **Varints** — variable-length integers, encoded 7 bits per byte
   with the high bit (the *continuation bit*) signalling "more bytes
   follow".
2. **Length-delimited records** — a varint length followed by that
   many raw bytes. Sub-messages, strings, bytes, and packed repeated
   fields all use this.

On top of these primitives the spec defines six wire types:

```
   wire type   meaning                  payload
   ----------  -----------------------  ---------------------------------
   0           VARINT                  int32/64, uint32/64, sint32/64,
                                       bool, enum, *packed* scalars
   1           I64                     fixed64, sfixed64, double
   2           LEN                     string, bytes, embedded message,
                                       packed repeated
   3           SGROUP  (deprecated)   start-group  (proto2 only)
   4           EGROUP  (deprecated)   end-group    (proto2 only)
   5           I32                     fixed32, sfixed32, float
```

Each tag prefix is `(field_number << 3) | wire_type`, encoded as a
varint. So the first byte of every field tells you which field it is
and how to skip it. That is the entire framing model.

## 2. Varint Encoding

Varints are LEB128 with a twist: each byte carries 7 payload bits in
its low 7 bits and uses the high bit (0x80) as the *continuation*
flag. The lowest 7 bits come first; the encoder keeps emitting bytes
until the value is exhausted.

Example — encode the integer `300`:

```
   300 = 0b100101100 = 0x012C
   split into 7-bit groups (LSB first):
       0b0101100  (= 44, value bits)        ← low group
       0b0000010  (=  2, value bits)        ← high group
   add continuation bits:
       0xAC = 1010_1100   ← continuation bit set, payload = 0b0101100
       0x02 = 0000_0010   ← continuation bit clear, payload = 0b0000010
   wire bytes:  AC 02
```

Decode: read 0xAC, MSB=1 so continue; accumulate `0b0101100` in the
low 7 bits. Read 0x02, MSB=0 so stop; accumulate `0b0000010` in the
next 7 bits. Result = `0b0000010_0101100 = 0x12C = 300`.

A few values to build intuition:

```
   value        wire bytes
   ---------    -------------
   0            00
   1            01
   127          7F
   128          80 01
   300          AC 02
   16384        80 80 01
   2^32 - 1     FF FF FF FF 0F  (5 bytes max for uint32)
   2^63 - 1     FF FF FF FF FF FF FF FF 7F  (10 bytes max for int64)
```

Worst-case overhead is +25% (a 64-bit value taking 10 bytes), but
small integers — field numbers, status codes, sizes — are nearly free
at one byte each. That asymmetry is why protobuf shines for messages
dominated by short scalars (control-plane RPCs) and less so for messages
dominated by large 64-bit hashes (use `fixed64` instead).

## 3. Zig-Zag Encoding for Signed Ints

If you naively varint-encode `int32 = -1`, the two's-complement
representation is `0xFFFFFFFF`, which varints to 10 bytes (`FF FF FF
FF FF FF FF FF FF 01`). That is a 10× size blow-up for what is
semantically a single bit of information.

The `sint32` and `sint64` types fix this with **zig-zag** encoding, a
bijection from signed integers to unsigned integers that puts 0 at 0,
-1 at 1, 1 at 2, -2 at 3, 2 at 4, and so on:

```
   zigzag(n)  = (n << 1) ^ (n >> 31)            for int32
   zigzag(n)  = (n << 1) ^ (n >> 63)            for int64

   signed     zigzag   wire (varint)
   -------    -------  ----------------
        0          0   00
       -1          1   01
        1          2   02
       -2          3   03
        2          4   04
   2147483647  4294967294  FE FF FF FF 0F
   -2147483648 4294967295  FF FF FF FF 0F
```

The decode side: `signed = (zigzag >>> 1) ^ -(zigzag & 1)`. The XOR
trick means small-magnitude negative and positive values both fit in 1
byte — exactly the distribution of common deltas and status codes.

The takeaway: declare your fields `sint32` / `sint64` when they can be
negative; `int32` / `int64` only when they're known to be non-negative
(IDs, counts). The type tag is on the wire, so switching is a wire-
incompatible change.

## 4. Field Tags and Wire Types

Every field starts with a tag varint. The tag is

```
   tag = (field_number << 3) | wire_type
```

So a field numbered 1 with wire type 0 (VARINT) has tag = `(1 << 3) |
0` = `0x08`. A field numbered 2 with wire type 2 (LEN) has tag =
`(2 << 3) | 2` = `0x12`. A field numbered 5 with wire type 5 (I32)
has tag = `(5 << 3) | 5` = `0x2D`.

Practical ranges:

- field numbers 1–15 → tags fit in one byte. Reserve these for the
  most frequent fields.
- 16–2047 → tags take 2 bytes. Fine but uses 2 bytes per field
  instance.
- 2048–2^29−1 → tags take 3-4 bytes. Allowed but expensive.
- 19000–19999 are reserved by the implementation; the compiler rejects
  them.
- 0 is not a valid field number at all (tag bytes of 0x00 are rejected
  by conforming parsers — a zero tag would be a 0-length field number);
  never use it.

## 5. The Length-Prefixed Records (wire type 2)

Strings, bytes, embedded messages, and packed repeated fields all use
wire type 2. The format is:

```
   tag (varint, wire_type=2)  length (varint)  payload (length bytes)
```

The decoder reads the tag, reads the length, then reads exactly
`length` bytes. If the decoder does not recognize the field, it can
skip in O(1) by reading the length and seeking past the payload —
this is the fundamental forward-compatibility guarantee.

Embedded messages are themselves protobuf messages, recursively. So
you can compose:

```
   message Order {
     uint64      order_id  = 1;   // tag 08
     Customer    customer  = 2;   // tag 12, length-delimited
     repeated LineItem items = 3; // tag 1A, length-delimited each
   }
```

A nested message's wire representation is the same as if it had been
serialized standalone, then prefixed with its length. There is no
inherent recursion limit beyond stack depth on the decoder — a
malicious deeply-nested message can blow the stack, which is why every
production parser has a recursion-depth cap.

## 6. Packed Repeated Fields

A `repeated` field of scalar type (numbers, enums, bools) can be
declared `[packed=true]` (in proto3 this is the default for scalar
repeated fields). The encoder collects all the values into a single
length-delimited record, back-to-back, with no per-element tag:

```
   repeated int32 xs = 7 [packed=true];   // values: 3, 270, 86942

   wire:
   3A 06 03 8E 02 9E A7 05
   ── ── ── ────── ────────
   │  │  │  │      └─ 86942 varint (9E A7 05)
   │  │  │  └─ 270 varint (8E 02)
   │  │  └─ 3 varint
   │  └─ length 6
   └─ tag = (7 << 3) | 2 = 0x3A
```

(These are the encodings from Google's own protobuf developer docs:
270 = 0b100001110 → continuation groups 0x0E | 0x02 → `8E 02`, and
86942 = 0b10101001110011110 → `9E A7 05`.)

Compare to the non-packed alternative, where every element carries its
own 1-byte tag (here `0x38`):

```
   non-packed:  38 03 38 8E 02 38 9E A7 05   = 9 bytes
   packed:      3A 06 03 8E 02 9E A7 05      = 8 bytes
```

For a 1000-element list, the savings are ~1 kB. Packed encoding also
skips cleanly: an unknown packed field is one length-prefix seek,
not 1000 individual tag-length skips.

A decoder must accept both packed and unpacked encodings of the same
field, even for the same message, for forward/backward compatibility.
The encoder chooses packed whenever the field type allows it.

## 7. Maps, Oneofs, and Unknown Field Retention

Some higher-level constructs are desugared at the wire level:

- **Maps** are sugar for `repeated MapEntry { Key key = 1; Value
  value = 2; }`. Each entry is a length-delimited sub-message with
  field 1 = key, field 2 = value. Iteration order on the wire is
  unspecified; do not rely on it.
- **oneof** picks exactly one of N fields at the message level. On the
  wire, a `oneof` is just a regular field — the type system enforces
  "at most one is set"; the wire format doesn't know the concept.
- **Unknown fields**: in proto3 the parser *retains* unknown fields by
default and round-trips them through encode/decode. This is critical
for intermediary forwarding (a proxy that doesn't know the latest
schema must still pass the bytes through untouched). Earlier proto3
parsers dropped unknown fields silently — that was a bug fixed in
the 3.5 release.

## 8. The `.proto` File: proto2 vs proto3

A `.proto` file is the IDL. Syntax is selected with `syntax =
"proto3";` (or `"proto2";`) at the top. The differences matter for
interviews:

```
   // proto2 example
   syntax = "proto2";
   package demo.v1;
   message User {
     optional string name  = 1;            // presence tracked
     required int64  id    = 2;            // wire-incompatible to remove
     repeated string roles = 3;
     optional int32  age   = 4 [default = 18];  // explicit default
   }

   // proto3 example
   syntax = "proto3";
   package demo.v1;
   message User {
     string name  = 1;                      // presence NOT tracked
     int64  id    = 2;                      // implicit; cannot be required
     repeated string roles = 3;
     int32  age   = 4;                      // defaults to 0, no presence
   }
```

The headline differences:

| Feature                  | proto2                                | proto3                                                |
|--------------------------|---------------------------------------|-------------------------------------------------------|
| Field presence           | `optional` and `required` keywords   | Scalars have no presence; use `optional` (since 3.15) |
| Defaults                 | Explicit `[default=…]`                | Implicit (0, "", false, empty bytes)                 |
| `required`               | Allowed (but discouraged)             | Removed; cannot be expressed                          |
| Enums                     | Open by default? No, closed           | Open enums; first value must be `0` (UNSPECIFIED)    |
| Unknown fields           | Retained by default                    | Retained by default (since 3.5; earlier dropped)      |
| JSON mapping             | Generated via plugin                   | Native, with canonical lowerCamelCase                |
| Maps / oneofs            | Both supported                         | Both supported                                        |

The single biggest practical rule: **never use `required`** in
proto2. A `required` field is a wire-compatibility trap — removing it
later is a breaking change, because old readers reject messages that
omit it. The proto3 designers removed `required` entirely for this
reason. The recommended pattern in either version is "all scalar
fields are optional, repeated fields express multiplicity, presence
is tracked only where business logic cares".

## 9. A Complete Worked Example

Take this proto3 message:

```
   syntax = "proto3";
   message Person {
     string   name      = 1;
     int32    id        = 2;
     string   email     = 3;
     repeated PhoneNumber phones = 4;     // packed? no — sub-message, so unpacked
     int32    age       = 5;
     enum PhoneType { MOBILE = 0; HOME = 1; WORK = 2; }
     message PhoneNumber {
       string    number = 1;
       PhoneType type   = 2;
     }
   }
```

Encode a sample Person:

```
   {
     "name":   "Alice",
     "id":     42,
     "email":  "",
     "phones": [{ "number": "555-1212", "type": "HOME" }],
     "age":    30
   }
```

Wire bytes (tag varint in brackets):

```
   0A 05 41 6C 69 63 65                       ← name="Alice"  (field 1, LEN)
   10 2A                                       ← id=42         (field 2, VARINT)
   (no bytes for email="")                     ← proto3 omits zero-value scalars
   22 0B 0A 07 35 35 35 2D 31 32 31 32 10 01   ← phones[0]: {number="555-1212", type=HOME=1}
   18 1E                                       ← age=30        (field 3, VARINT)
```

Decoding walkthrough:

- `0A` = tag `(1 << 3) | 2` → field 1, LEN. Length = `0x05`. Read 5
  bytes: "Alice".
- `10` = tag `(2 << 3) | 0` → field 2, VARINT. Read `0x2A` = 42.
  (No continuation bit; value fits in 7 bits.)
- `22` = tag `(4 << 3) | 2` → field 4 (phones), LEN. Length = `0x0B`
  = 11 bytes. Read 11 bytes as a sub-message:
    - `0A 07 35 35 35 2D 31 32 31 32` → field 1, LEN, length 7,
      payload "555-1212"
    - `10 01` → field 2, VARINT, value 1 → HOME
- `18` = tag `(3 << 3) | 0` → field 3, VARINT. Read `0x1E` = 30.

Total wire size: 25 bytes for a 4-field message with one nested
sub-message and a 7-byte string. The equivalent JSON is ~80 bytes.
For a control-plane RPC that fires 10 000 times a second, that's a
6× bandwidth win.

## 10. Comparison to JSON, Avro, Thrift

| Property           | Protobuf                                  | Avro                                        | Thrift (compact)                         | JSON                                   |
|--------------------|-------------------------------------------|---------------------------------------------|-------------------------------------------|----------------------------------------|
| Schema             | Required (`.proto`)                       | Required (`.avsc`, exchanged at handshake)  | Required (`.thrift`)                       | Optional (self-describing)             |
| Wire format        | Tagged (field_number + wire_type)         | Untagged (schema dictates layout)            | Tagged (field_id + type)                   | Tagged (string keys)                   |
| Schema on wire     | No                                        | Yes (single schema fingerprint per stream)   | No                                         | Yes (every key)                        |
| Forward compatibility | Yes (unknown fields retained)          | Yes (reader-schema projection)              | Yes (unknown fields skipped)               | Yes (extra keys ignored)              |
| Backward compatibility | Yes (defaults, optional fields)        | Yes (defaults, reader-writer resolution)    | Yes (defaults)                             | Yes (extra keys ignored)              |
| Recompilation cost | Codegen per language                     | Codegen per language                          | Codegen per language                      | None                                   |
| Size (typical)     | 1.0×                                      | ~0.7× (smaller — no tags)                    | ~1.0× (similar to proto)                  | ~3–5× larger                            |
| Self-describing?   | No                                        | Yes (with schema embedded — used in Parquet)| No                                         | Yes                                    |
| Streaming?         | Yes (length-delimited messages)           | Yes                                          | Yes                                       | Awkward (NDJSON, JSONL)               |
| Strong typing?     | Yes                                       | Yes                                          | Yes                                        | No (JSON-Schema as add-on)             |

Practically:

- **Protobuf** is the default for internal RPC and config storage. It
  wins on tooling, language coverage, and the freedom to evolve
  schemas by adding new fields. It loses on introspection (you cannot
  decode without the schema).
- **Avro** wins when you store many records of the same schema (e.g.,
  Kafka topics, data lake) because per-record tags would dominate the
  wire size. The cost is that producer and consumer must coordinate
  on schema identity, which is why Avro is paired with a Schema
  Registry in practice.
- **Thrift compact** is roughly wire-equivalent to Protobuf and ships
  with a richer RPC framework. It predates Protobuf and is rare
  outside Apache-ecosystem codebases.
- **JSON** remains the right choice for human-facing APIs, browser
  payloads, and any place where debuggability beats wire size.

## 11. Common Pitfalls

1. **Switching `int32` to `sint32` on a populated field.** They
   encode differently — `int32` writes the two's-complement varint,
   `sint32` writes the zig-zag varint. Old data re-read with the new
   schema will be silently corrupted.
2. **Reusing a field number with a different type.** The wire bytes
   will be valid protobuf but the semantic will change. Always pick a
   new field number for changed types; reserve the old one with
   `reserved 7;` to prevent reuse.
3. **Removing a `required` field from proto2.** Removing `required`
   is a wire-incompatible change. Old binaries will reject messages
   from new writers. Use `optional` from the start, or migrate to
   proto3.
4. **Declaring large enums and reusing values.** The proto3 spec
   requires the first enum value to be `0`. If you renumber an enum
   partway through its lifetime, values that were "X" on the wire
   become "Y" after the change. Use `reserved` for removed values.
5. **Forgetting the recursion cap.** A hostile payload like
   `<message><field>msg</field><message>...` can recurse arbitrarily
   deep. Cap recursion at a few hundred levels and reject the message.
6. **Using `int32` for negative-heavy IDs.** Use `sint32` instead. A
   signed ID of `-1` takes 5 bytes as `int32`, 1 byte as `sint32`.
7. **Trusting the parser not to retain unknown fields.** In proto3
  before 3.5, unknown fields were silently dropped. If you proxy
  messages through such a parser, you lose forward compatibility.
  Upgrade or pin the version.

## References

- Google Developers — *Protocol Buffers Language Guide (proto3)*.
  https://protobuf.dev/programming-guides/proto3/
- Google Developers — *Protocol Buffers Encoding* (the canonical wire
  spec; integer examples reproduced from this page).
  https://protobuf.dev/programming-guides/encoding/
- Google Developers — *Protocol Buffers Language Guide (proto2)*.
  https://protobuf.dev/programming-guides/proto/
- Google Developers — *Editions* — the proto3/proto2 unification
  effort, with `edition = "2023"` syntax.
  https://protobuf.dev/editions/overview/
- Apache Avro — *Specification 1.11* (for comparison).
  https://avro.apache.org/docs/1.11.1/specification/
- Apache Thrift — *Compact Protocol Specification*.
  https://github.com/apache/thrift/blob/master/doc/specs/thrift-compact-protocol.md
- Kenton Varda — *Protocol Buffers: Serialization for the 21st
  Century* (Cap'n Proto author's perspective, useful critique).
  https://capnproto.org/
- Martin Kleppmann — *Schema Evolution in Avro, Protobuf, and Thrift*,
  chapter 4 of *Designing Data-Intensive Applications*.
  https://dataintensive.net/
- IETF — *CBOR (RFC 8949)* — schemaless binary alternative to JSON,
  worth comparing.
  https://www.rfc-editor.org/rfc/rfc8949.html

## Cross-References

- [Serialization overview](../serialization.md) — format landscape.
- [Avro encoding](./avro.md) — schema-on-wire alternative.
- [gRPC](../api/grpc.md) — Protobuf's most common transport.
- [Data formats](../../data-engineering/data-formats.md) — for storage
  (Parquet, ORC) which sit between Avro and Protobuf on the schema
  axis.
