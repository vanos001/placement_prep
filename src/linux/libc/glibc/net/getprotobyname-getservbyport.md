# getprotobyname(3) - glibc (protocol and services database lookups)

> File-backed databases, not name-service-resolved at call time: `/etc/protocols` and `/etc/services` (or NSS equivalents, databases `protocols` and `services`).

| Field | Value |
|---|---|
| Header | `netdb.h` |
| Standards | BSD origin; POSIX XSI option for the `ent` iterators |
| Exported | `getprotobyname`, `getprotobynumber`, `getservbyname`, `getservbyport`, `setprotoent`/`getprotoent`/`endprotoent`, `setservent`/`getservent`/`endservent` all `GLIBC_2.2.5` (nm, host glibc 2.41); `_r` twins exported but grouped here as ledger rows |
| Thread-safety | Non-`_r` lookups: MT-Unsafe race:protobyname / race:servbyname, locale; `_r` twins: MT-Safe (man3 ATTRIBUTES; manual safety annotations) |
| Ledger ID | `GLIBC-getprotobyname`, `GLIBC-getservbyport` and siblings (netdb compact-table rows) |

## Declaration and gates

```text
struct protoent *getprotobyname(const char *name);
struct protoent *getprotobynumber(int protocol);
struct servent  *getservbyname(const char *name, const char *proto);
struct servent  *getservbyport(int port, const char *proto);
void setprotoent(int stayopen);  struct protoent *getprotoent(void);  void endprotoent(void);
void setservent(int stayopen);   struct servent  *getservent(void);   void endservent(void);
```

`struct protoent`: `p_name`, `p_aliases`, `p_proto` (host byte order; this is the value `socket()` wants). `struct servent`: `s_name`, `s_aliases`, `s_port` (**network byte order**), `s_proto` (manual nodes *Protocols Database*, *Services Database*).

## Semantics

`getprotobyname("tcp")` turns a protocol name into the number for `socket()`. `getservbyname`/`getservbyport` map service names to ports; servers use them to pick the port to listen on (manual). `getservbyport` takes `port` already in network byte order. The `set*/get*ent` triple scans the whole file, entry by entry; `stayopen` non-zero keeps the database open across lookups for efficiency. Results come from a statically allocated structure: "you must copy the information if you need to save it across calls" (manual).

## Gotchas and portability

- The byte-order asymmetry (`s_port` network order, `p_proto` host order) is a standard interview trap; the manual states it explicitly.
- All six lookup functions share process-global state and are not reentrant; use the `_r` variants in threads.
- musl contrast: musl 1.2.5 reads the same files (`src/network/getservbyname.c`, `src/network/proto.c` for protocols) and provides the `_r` forms; there is no NSS module dispatch and no nscd path.

## References

- glibc manual nodes *Protocols Database* and *Services Database*; man3 `getprotobyname.3`, `getservbyname.3`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
