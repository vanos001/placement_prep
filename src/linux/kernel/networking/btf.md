# BTF: The BPF Type Format

BTF is a compact binary metadata format that encodes C types (structs, enums,
pointers, typedefs) plus function and variable signatures, designed to ship
*inside the running kernel image* rather than in a side debug package. Two
subsystems need a machine-readable type model of the kernel: the eBPF
verifier, which type-checks programs against real kernel structs
(`PTR_TO_BTF_ID`), and libbpf's CO-RE relocation engine, which rewrites field
accesses to match whichever kernel loads the program. DWARF can answer the
same questions but weighs two orders of magnitude more; BTF is what you get
after pahole converts DWARF to BTF and dedups it. Program-side mechanics are
in [eBPF](./ebpf.md); this page is the format itself -- what an interviewer
means by "how does BPF know `task_struct`'s layout without kernel headers?"

## One format, three homes

| Artifact | Location | Contents |
|----------|----------|----------|
| Kernel BTF | `/sys/kernel/btf/vmlinux` | every type in the kernel image (0444, mmap-able) |
| Module BTF | `/sys/kernel/btf/<module-name>` | split BTF add-on per loaded module |
| Object BTF | `.BTF` / `.BTF.ext` ELF sections | types + func_info/line_info/CO-RE relos |

Kernel BTF is embedded in vmlinux as a `.BTF` section during the final link
(`scripts/link-vmlinux.sh`, `gen_btf()`) and surfaced by
`kernel/bpf/sysfs_btf.c` as a read-only sysfs binary attribute. Module BTF is
*split BTF*: only the types a module adds or modifies, referring back to root
vmlinux BTF for the rest. Verified timeline (commit history of
`include/uapi/linux/btf.h` plus in-tree ABI docs): format introduced in 4.18;
`FUNC`/`FUNC_PROTO` in 5.0; `VAR`/`DATASEC` and `CONFIG_DEBUG_INFO_BTF`
kbuild integration in 5.2; `/sys/kernel/btf/vmlinux` in 5.5; module BTF +
`CONFIG_DEBUG_INFO_BTF_MODULES` in 5.11; `FLOAT`, `DECL_TAG`, `TYPE_TAG`,
`ENUM64` through 2021-2022; a per-kind layout table in the UAPI in 2026.

## The wire format

```c
struct btf_header {                 /* include/uapi/linux/btf.h */
    __u16   magic;                  /* 0xeB9F */
    __u8    version;                /* 1 */
    __u8    flags;
    __u32   hdr_len;                /* 24 in the classic header */
    __u32   type_off, type_len;     /* offsets relative to END of header */
    __u32   str_off, str_len;       /* string section */
    __u32   layout_off, layout_len; /* optional, 2026 extension */
};
```

```text
offset 0      24                       24+type_len       end
  |           |                        |                 |
  v           v                        v                 v
  +-----------+------------------------+-----------------+
  | header    | type section           | string section  |
  | (24 B)    | type ids 1..N, packed  | NUL-terminated  |
  +-----------+------------------------+-----------------+
              type id 0 == void, never stored
```

The magic doubles as an endianness detector: on a little-endian target `0xeB9F`
is stored as the bytes `9F EB`, so a loader can tell whether a blob needs
byte-swapping. The string section is a flat table of NUL-terminated strings and
its *first string must be empty*, so `name_off = 0` means "no name" (anonymous
pointers, return types); every name is a `u32` offset into that table. Types
are parsed sequentially and IDs assigned from 1; each record starts with the
12-byte `struct btf_type`, whose `info` word packs vlen, kind, and a flag:

```text
struct btf_type.info (u32):
 bit 31   bit 30 ......... bit 24   bit 23 .................... bit 0
 +------+---------------------+-----------------------------------+
 | flag |     kind (7 bits)    |           vlen (24 bits)          |
 +------+---------------------+-----------------------------------+
 name_off (u32)         -> string section
 union { size; type; }  -> byte size OR referenced type id
```

`kind_flag` repurposes payloads: for struct/union members it splits `offset`
into `BTF_MEMBER_BITFIELD_SIZE(val) >> 24` plus a 24-bit bit offset; for `FWD`
it selects struct-vs-union; for `ENUM` it selects signedness.

| ID | Kind | Extra bytes after btf_type | size/type field |
|----|------------------|----------------------------------|-----------------|
| 1 | INT | u32: encoding/offset/bits | size |
| 2 | PTR | none | type (pointee) |
| 3 | ARRAY | one btf_array | type (element) |
| 4-5 | STRUCT, UNION | vlen x btf_member | size |
| 6 | ENUM | vlen x btf_enum | size |
| 7 | FWD | none | unused |
| 8-11 | TYPEDEF, VOLATILE, CONST, RESTRICT | none | type |
| 12 | FUNC | none (vlen = linkage) | type (FUNC_PROTO) |
| 13 | FUNC_PROTO | vlen x btf_param | type (return) |
| 14 | VAR | one btf_var (linkage) | type |
| 15 | DATASEC | vlen x btf_var_secinfo | size (section) |
| 16 | FLOAT | none | size |
| 17-18 | DECL_TAG, TYPE_TAG | btf_decl_tag / none | type |
| 19 | ENUM64 | vlen x btf_enum64 | size |

Kind 0 (`UNKN`) is invalid. Fixed limits: `BTF_MAX_TYPE` = 0xfffff (~1M ids),
`BTF_MAX_VLEN` = 0xffffff. `BTF_KIND_INT` carries a bit-level encoding
(`BTF_INT_ENCODING/OFFSET/BITS`) -- how BTF represents bitfields and the
`char`-vs-`u8` distinction; pahole emits `BTF_INT_OFFSET() = 0` everywhere in
practice. The 2026 `struct btf_layout { info_sz, elem_sz, flags }` extension
lets future kernels widen vlen/kind into unused bits without breaking old
parsers; classic 24-byte-header blobs stay valid and docs.kernel.org still
specifies the classic layout.

## Hand-decoding a blob

The demo builds a valid 110-byte BTF blob for the C snippet
`int probe_fn(int *arg, int *arg);` and parses it back with `struct.unpack`
only -- `INT`, `PTR`, a two-parameter `FUNC_PROTO`, and a `FUNC` record with
`GLOBAL` linkage:

```python
#!/usr/bin/env python3
# Build + decode a 110-byte BTF blob (INT + PTR + FUNC_PROTO + FUNC),
# per include/uapi/linux/btf.h. Pure stdlib: struct only.
import struct

INT, PTR, FUNC_PROTO, FUNC = 1, 2, 13, 12          # BTF_KIND_* values
LINKAGE = {0: "STATIC", 1: "GLOBAL", 2: "EXTERN"}  # enum btf_func_linkage

names = (b"", b"int", b"probe_fn", b"arg")   # strings; first must be empty
str_off, strings, off = {}, b"", 0
for s in names:
    str_off[s.decode()], off = off, off + len(s) + 1
    strings += s + b"\x00"

hdr_i = lambda kind, vlen=0: (kind << 24) | vlen      # btf_type "info" word
recs = [
    struct.pack("<III", str_off["int"], hdr_i(INT), 4) + struct.pack("<I", (1 << 24) | 32),
    struct.pack("<III", 0, hdr_i(PTR), 1),                        # PTR -> id 1
    struct.pack("<III", 0, hdr_i(FUNC_PROTO, 2), 1)               # ret = id 1
        + struct.pack("<IIII", str_off["arg"], 2, str_off["arg"], 2),
    struct.pack("<III", str_off["probe_fn"], hdr_i(FUNC, 1), 3),  # FUNC -> id 3
]
types = b"".join(recs)
# header: magic, version, flags, hdr_len=24, type_off, type_len, str_off, str_len
blob = struct.pack("<HBBIIIII", 0xEB9F, 1, 0, 24, 0, len(types), len(types),
                   len(strings)) + types + strings
s_base = 24 + len(types)

def name_at(off):   # NUL-terminated string at str_off
    return blob[s_base + off:blob.index(b"\x00", s_base + off)].decode()

magic, ver, flags, hdr_len, t_off, t_len, s_off, s_len = struct.unpack_from(
    "<HBBIIIII", blob, 0)
print(f"BTF blob: {len(blob)} bytes")
print(f"header : magic=0x{magic:04X} ver={ver} hdr_len={hdr_len} "
      f"type_len={t_len} str_off={s_off} str_len={s_len}")
print(f"         first 24 bytes: {blob[:24].hex()}")
pos, tid, ok = 24 + t_off, 1, 0
while pos < 24 + t_off + t_len:
    name_off, info, val = struct.unpack_from("<III", blob, pos)
    kind, vlen = (info >> 24) & 0x7F, info & 0xFFFFFF
    nm, pos = name_at(name_off) or "<anon>", pos + 12
    if kind == INT:
        extra = struct.unpack_from("<I", blob, pos)[0]; pos += 4
        enc = [e for e, b in (("SIGNED", 1), ("CHAR", 2), ("BOOL", 4))
               if extra & (b << 24)]
        print(f"  id {tid}: INT name={nm!r} size={val} "
              f"encoding={'+'.join(enc)} bits={extra & 0xFF}")
        ok += (val == 4) * ((extra & 0xFF) == 32)
    elif kind == PTR:
        print(f"  id {tid}: PTR name={nm!r} -> type {val}")
        ok += (val == 1)
    elif kind == FUNC_PROTO:
        p = struct.unpack_from("<" + "II" * vlen, blob, pos); pos += 8 * vlen
        ps = ", ".join(f"{name_at(p[i])}:type{p[i + 1]}"
                       for i in range(0, 2 * vlen, 2))
        print(f"  id {tid}: FUNC_PROTO name={nm!r} vlen={vlen} "
              f"ret=type {val} params=[{ps}]")
        ok += (vlen == 2) * (val == 1)
    elif kind == FUNC:
        print(f"  id {tid}: FUNC name={nm!r} -> type {val} linkage={LINKAGE[vlen]}")
        ok += (val == 3) * (vlen == 1) * (nm == "probe_fn")
    tid += 1
ok += (magic == 0xEB9F) + (hdr_len == 24) + (s_off == t_off + t_len) + (blob[s_base] == 0)
print(f"self-check: {ok}/8 assertions passed")
```

Real output of the script above (re-runnable, pure stdlib):

```text
BTF blob: 110 bytes
header : magic=0xEB9F ver=1 hdr_len=24 type_len=68 str_off=68 str_len=18
         first 24 bytes: 9feb01001800000000000000440000004400000012000000
  id 1: INT name='int' size=4 encoding=SIGNED bits=32
  id 2: PTR name='<anon>' -> type 1
  id 3: FUNC_PROTO name='<anon>' vlen=2 ret=type 1 params=[arg:type2, arg:type2]
  id 4: FUNC name='probe_fn' -> type 3 linkage=GLOBAL
self-check: 8/8 assertions passed
```

Read the header hex: `9feb` is `0xEB9F` stored little-endian; `18 00 00 00` is
`hdr_len = 24`; `44 00 00 00` is 68 -- both the type length and the string
offset, because the sections are contiguous. The `FUNC` record carries its
*linkage* in the vlen bits; that is how `bpftool` distinguishes static from
global functions.

## Who consumes BTF, and how

**Map creation.** `BPF_MAP_CREATE` takes `btf_fd`, `btf_key_type_id`,
`btf_value_type_id`; struct_ops maps instead take `btf_vmlinux_value_type_id`
(the kernel rejects it for any other map type). This is what makes
`bpftool map dump` print typed key/value structs instead of hex.

**Program load.** `BPF_PROG_LOAD` carries `prog_btf_fd` plus arrays of
`struct bpf_func_info { insn_off, type_id }` and
`struct bpf_line_info { insn_off, file_name_off, line_off, line_col }`
(`.BTF.ext` func_info/line_info, re-offsetted by libbpf). func_info names
BPF-to-BPF subprograms and lets the verifier check each global callee against
its `FUNC_PROTO` (function-by-function verification); it is also the attach
target when fentry/fexit hooks *another BPF program*. line_info is what
resolves verifier-log addresses and `bpftool prog dump -f` to source lines.
Only `BTF_FUNC_STATIC` and `BTF_FUNC_GLOBAL` linkages are supported in kernel.

**Verifier types and kernel references.** Tracing programs attach via
`attach_btf_id` -- a type id into vmlinux or module BTF (`attach_btf_obj_fd`),
how fentry/fexit bind to a concrete function signature at load time.
`BPF_PSEUDO_BTF_ID` relocations let a program reference kernel variables: the
loader swaps in the symbol address and the verifier types it `PTR_TO_BTF_ID`
or `PTR_TO_MEM`.

**CO-RE field relocations.** CO-RE emits `struct bpf_core_relo { insn_off,
type_id, access_str_off, kind }` records; *libbpf*, not the kernel, resolves
them against `/sys/kernel/btf/vmlinux` at load time and patches immediates.
Each kind is a question about the target kernel:

| Value | bpf_core_relo_kind | Question |
|-------|---------------------------|------------------------------------|
| 0 | FIELD_BYTE_OFFSET | where is this field now? |
| 1 | FIELD_BYTE_SIZE | how big is it now? |
| 2 | FIELD_EXISTS | does the field exist? |
| 3 | FIELD_SIGNED | is it signed? |
| 4-5 | FIELD_LSHIFT_U64, FIELD_RSHIFT_U64 | bitfield extraction shifts |
| 6-7 | TYPE_ID_LOCAL, TYPE_ID_TARGET | local vs target type id |
| 8 | TYPE_EXISTS | does the type exist? |
| 9 | TYPE_SIZE | type size in target kernel? |
| 10 | ENUMVAL_EXISTS | does this enumerator exist? |
| 11 | ENUMVAL_VALUE | what is its value now? |

Usage-level coverage (`BPF_CORE_READ`, `bpf_core_field_exists`, compatibility
rules) lives in [BPF CO-RE](../../performance/bpf-co-re.md).

## Producing BTF: pahole and dedup

`CONFIG_DEBUG_INFO_BTF` makes kbuild convert vmlinux DWARF to BTF with
**pahole** (the dwarves project) during the final link -- current Kconfig
requires pahole >= 1.22 -- then dedups it; introspection afterwards is one
command: `bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h`.
Dedup (libbpf `btf__dedup`, designed in the 2018 Facebook BTF blog) runs seven
passes: (1) string dedup; (2) primitive dedup (int, enum, fwd); (3)
struct/union dedup by name and shape; (4) resolve unambiguous forward
declarations -- a `FWD` merges into a full `STRUCT` when one appears; (5)
reference-type dedup (pointers, typedefs, arrays, funcs, func protos;
const/volatile/restrict wrappers collapse when they wrap the same type); (6)
compaction; (7) id remapping. Per-CU duplication and forward-declaration
fragmentation vanish, which is why a distro kernel's BTF is a few MB while its
DWARF is ~100x larger.

Rapid-fire questions this page answers:

1. Why `0xEB9F` as magic? It is byte-order-asymmetric: the first two bytes
   reveal the endianness the blob was encoded for.
2. What breaks with `CONFIG_DEBUG_INFO_BTF=n`? No vmlinux BTF: fentry/fexit
   and CO-RE loads fail (`attach_btf_id`, field relos have nothing to consult)
   and `vmlinux.h` cannot be generated.
3. How does BTF represent a bitfield? `kind_flag` on the struct +
   `BTF_MEMBER_BITFIELD_SIZE` in the member's high byte, and `BTF_INT_BITS`
   on the underlying int.
4. FUNC vs FUNC_PROTO? `FUNC_PROTO` is the signature (params + return);
   `FUNC` is a subprogram record referencing one, linkage stored in vlen.

## Cross-references

[eBPF](./ebpf.md) (execution model, program types), [BPF
Networking](./bpf-networking.md) (where BTF-typed programs plug in), [AF_XDP
Internals](./af-xdp-internals.md) (XDP sockets and BTF-described metadata),
and [BPF CO-RE](../../performance/bpf-co-re.md) (relocation macros) build
directly on this format.

## References

1. BPF Type Format (BTF) specification, kernel docs: https://docs.kernel.org/bpf/btf.html
2. `include/uapi/linux/btf.h` (raw kernel-source mirror; git.kernel.org may refuse curl): https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/btf.h
3. sysfs BTF ABI doc (vmlinux 5.5, modules 5.11): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/ABI/testing/sysfs-kernel-btf
4. `include/uapi/linux/bpf.h` -- `bpf_core_relo`, `bpf_func_info`, map-create BTF fields: https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/bpf.h
5. Facebook BPF blog, "BTF deduplication" (original dedup design, 2018): https://facebookmicrosites.github.io/bpf/blog/2018/11/14/btf-enhancement.html
6. Andrii Nakryiko, "BTF deduplication and Linux kernel BTF": https://nakryiko.com/posts/btf-dedup/
7. Andrii Nakryiko, "BPF CO-RE reference guide": https://nakryiko.com/posts/bpf-core-reference-guide/
8. pahole (dwarves) source repository: https://github.com/acmel/dwarves
