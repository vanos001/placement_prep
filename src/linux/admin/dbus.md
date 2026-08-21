# D-Bus — The Linux Desktop IPC Bus

D-Bus is the **inter-process communication** mechanism of choice for the modern Linux desktop and for most system services that need structured, discoverable RPC. It is a **bus** (a many-to-many multiplexer) rather than a point-to-point pipe: a single bus daemon routes messages between many peers, and any peer can broadcast **signals** to all subscribers.

This page covers the on-the-wire protocol, the daemon, service activation, and how systemd's `sd-bus` library implements the bus from inside PID 1. It complements [systemd Internals](systemd-internals.md) which discusses how systemd *uses* D-Bus.

## 1. Two buses: system and session

There are two long-running D-Bus instances on a typical Linux box:

| Bus | Address | Scope | Auth |
|-----|--------|-------|------|
| **System bus** | `unix:path=/run/dbus/system_bus_socket` | Whole machine, persistent | uid 0 + policy file in `/usr/share/dbus-1/system.d/*.conf` and `/etc/dbus-1/system.d/*.conf` |
| **Session bus** | `unix:path=/run/user/$UID/bus` (or autolaunched) | One user login session | `EXTERNAL` auth: same uid via `SO_PEERCRED` |

The system bus hosts privileged services like `org.freedesktop.systemd1`, `org.freedesktop.NetworkManager`, `org.freedesktop.login1`, `org.freedesktop.hostname1`. The session bus hosts desktop services like `org.freedesktop.Notifications`, `org.freedesktop.PowerManagement`, `org.freedesktop.ScreenSaver`, and the per-app buses of browsers, IDEs, and IM clients.

A third bus type — the **systemd private bus** — is exposed by systemd itself at `/run/systemd/private` and speaks the same wire protocol but is only reachable by uid 0. It is what `systemctl` uses by default to avoid round-tripping through `dbus-daemon`.

## 2. The dbus-daemon

`dbus-daemon` is the userspace router. It accepts connections (typically on an `AF_UNIX` socket), authenticates each, and for every message it receives it consults the **match rules** other clients have installed to determine which clients should receive a copy. The daemon does not serialise to disk; it is purely in-memory, with unicast and broadcast semantics.

A bus address is a string like:

```
unix:path=/run/dbus/system_bus_socket
unix:abstract=/tmp/dbus-XXXXXX,guid=…     # session bus on older systems
unix:runtime=yes                          # use $XDG_RUNTIME_DIR/bus
```

The bus daemon is normally started by `dbus.service` (or `dbus.socket` for socket activation) on the system side, and by `dbus-daemon --session` invoked from `dbus-launch` or `systemd --user` on the session side.

Each connection is identified by a **unique name** like `:1.42` (assigned sequentially by the daemon). Clients may then request a **well-known name** like `org.freedesktop.NetworkManager` via `RequestName`; the daemon resolves the unique-name-to-well-known-name mapping, applies name ownership policy, and dispatches.

## 3. The wire protocol

D-Bus messages are binary. Each message has a fixed-size **header** followed by a variable-length **body**.

```
+----------+----------------+------------------+
|  Header  |  Header padding|      Body        |
+----------+----------------+------------------+
      |              |
      v              v
  12 bytes mandatory + 4 bytes optional  aligned to 8 bytes
```

The header layout (`/usr/include/dbus-1.0/dbus/dbus-protocol.h`):

```
byte 0   : 'l' (little-endian) or 'B' (big-endian) — message byte order
byte 1   : message type (1=method_call, 2=method_return, 3=error, 4=signal)
byte 2   : flags (NO_REPLY_EXPECTED, NO_AUTO_START, ...)
byte 3   : protocol version (currently 1)
bytes 4-7: body length (uint32 LE)
bytes 8-11: serial number (uint32 LE) — monotonically increasing per connection
bytes 12+: header fields array
```

The header fields array carries a list of (field code, signature, value) tuples. Standard field codes (from `dbus-protocol.h`):

```
PATH         = 1   object path, e.g. /org/freedesktop/DBus
INTERFACE    = 2   e.g. org.freedesktop.DBus.Properties
MEMBER       = 3   method or signal name, e.g. GetAll
ERROR_NAME   = 4   on error replies, e.g. org.freedesktop.DBus.Error.ServiceUnknown
REPLY_SERIAL = 5   serial of the call this is replying to
DESTINATION  = 6   well-known name of the recipient
SENDER       = 7   unique name of the sender (filled in by daemon)
SIGNATURE    = 8   signature of the body
UNIX_FDS     = 9   number of file descriptors passed (out-of-band via SCM_RIGHTS)
```

The **body** contains arguments whose types are described by the `SIGNATURE` field. Type codes include `y` (byte), `b` (bool), `n` (int16), `i` (int32), `u` (uint32), `x` (int64), `t` (uint64), `d` (double), `s` (UTF-8 string), `o` (object path string), `g` (signature string), `a` (array), `(...)` (struct), `v` (variant), and `a{...}` (dict entry).

Example: the signature `sa{sv}` says "a string followed by an array of dict entries whose key is a string and value is a variant". This is the canonical "properties bag" shape used by the Properties interface and many methods.

## 4. The org.freedesktop.DBus interface

Every connection automatically owns the `org.freedesktop.DBus` interface on the object path `/org/freedesktop/DBus`. It exposes the bus-management API: name registration, list querying, activation, and the message bus match rules.

```bash
$ dbus-send --print-reply --system \
    --dest=org.freedesktop.DBus \
    /org/freedesktop/DBus \
    org.freedesktop.DBus.ListNames
method return time=1717823456.987654 sender=org.freedesktop.DBus -> dest=:1.42 serial=3 reply_serial=2
   array string "org.freedesktop.DBus"
   ...
```

Notable methods:

| Method | Purpose |
|--------|---------|
| `Hello` | Returns the unique name assigned to this connection (`:1.42`); called once at connect time |
| `RequestName(name, flags)` | Ask the bus to assign `name` to this connection |
| `ReleaseName(name)` | Release a previously-requested name |
| `ListNames` | List all unique and well-known names on the bus |
| `GetNameOwner(name)` | Get the unique name owning `name` |
| `NameOwnerChanged(name, old, new)` | Signal emitted when a name is acquired/released |
| `AddMatch(rule)` | Subscribe to signals matching `rule` |
| `RemoveMatch(rule)` | Remove a match rule |
| `GetConnectionCredentials(name)` | Returns uid, pid, SELinux context of `name` |
| `GetId` | Returns the bus's globally-unique UUID |
| `UpdateActivationEnvironment` | Update environment for newly-activated services |

The full interface is documented in the [D-Bus specification, standard interfaces](https://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces).

## 5. Method calls vs. signals

A D-Bus message is one of four types: **method call**, **method return**, **error**, or **signal**.

A **method call** is unicast to the unique name (or well-known name) of the recipient:

```
Client A                          Bus daemon                   Service B
   |  method_call                     |                            |
   |  serial=42                       |                            |
   |  dest=org.freedesktop.NetworkManager                         |
   |  path=/org/freedesktop/NetworkManager                         |
   |  iface=org.freedesktop.NetworkManager                         |
   |  member=GetDevices                                             |
   |  signature=                                                    |
   |  body=()                                                       |
   | ---------------------------->  | ---------------------------->|
   |                                |                             |
   |                                |  method_return              |
   |                                |  reply_serial=42            |
   |                                |  signature=ao               |
   |                                |  body=([/org/freedesktop/…]) |
   |                                | <----------------------------|
   | <---------------------------- | <---------------------------- |
```

A **signal** is broadcast by the daemon to any client whose match rule matches. The sender does not know (or care) who is listening:

```
Service B                         Bus daemon                   Many clients
   |  signal                                                          |
   |  path=/org/freedesktop/NetworkManager/Devices/0                  |
   |  iface=org.freedesktop.NetworkManager                            |
   |  member=PropertiesChanged                                        |
   |  signature=a{sv}as                                               |
   |  body=({"ActiveConnection": "/…"}, [])                          |
   | ----------------------------> | ------------------------------>| (match rule 1)
   |                                | ------------------------------>| (match rule 2)
   |                                | ------------------------------>| (match rule 3)
```

Match rules look like:

```
type='signal',
interface='org.freedesktop.NetworkManager',
member='PropertiesChanged',
path='/org/freedesktop/NetworkManager/Devices/0',
arg0='ActiveConnection'
```

The daemon stores each match rule as a string-tuple key in a hash; for every incoming signal it iterates all match rules and forwards to the matching connections. This O(peers × rules) dispatch is the main cost of the bus daemon and the reason very-high-rate signal paths bypass the bus entirely (e.g. video frames in Wayland).

## 6. Introspection

Every object on the bus with the path `/` and below can be asked "what do you do?" via the `org.freedesktop.DBus.Introspectable.Introspect` method, which returns an XML description of the object's interfaces, methods, signals, and properties:

```bash
$ dbus-send --system --print-reply --dest=org.freedesktop.login1 \
    /org/freedesktop/login1 org.freedesktop.DBus.Introspectable.Introspect
method return time=1717823456.123456 sender=:1.5 -> dest=:1.42 serial=42 reply_serial=2
   string "<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
"http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.freedesktop.login1.Manager">
    <method name="ListSessions">
      <arg name="sessions" type="a(sssussso)" direction="out"/>
    </method>
    <method name="PowerOff">
      <arg name="interactive" type="b" direction="in"/>
    </method>
    ...
    <signal name="SeatNew"/>
    <property name="NCurrentSessions" type="u" access="read"/>
  </interface>
</node>"
```

The XML is human-readable and tooling-friendly. `gdbus introspect`, `busctl introspect`, `d-feet`, and `qdbus` all use it to render tree views of running services.

## 7. Service activation

D-Bus services can be **autostarted**. When a method call's destination is a well-known name that is currently unowned, the daemon checks `/usr/share/dbus-1/system-services/<name>.service` (system bus) or `~/.local/share/dbus-1/services/*.service` (session bus):

```ini
# /usr/share/dbus-1/system-services/org.freedesktop.networkManager.service
[D-BUS Service]
Name=org.freedesktop.NetworkManager
Exec=/usr/sbin/NetworkManager --no-daemon
User=root
SystemdService=NetworkManager.service
```

The daemon then forks/execs `Exec`, waits for the new process to call `RequestName` on the bus, and only then forwards the queued method call. The `SystemdService=` line tells systemd-aware daemons to start the corresponding systemd unit instead — this is **systemd activation**, used to avoid double-forking the service.

If the `NO_AUTO_START` flag is not set on the method call, this is transparent to the caller: a method call to an inactive service looks exactly like one to a long-running service, modulo a one-shot startup latency.

## 8. dbus-send and friends

`dbus-send` is the lowest-common-denominator CLI for D-Bus. It can send method calls and read replies, but **cannot subscribe to signals**. Examples:

```bash
# Suspend the system
dbus-send --system --print-reply --dest=org.freedesktop.login1 \
    /org/freedesktop/login1 org.freedesktop.login1.Manager.Suspend \
    boolean:true

# Get a property
dbus-send --system --print-reply --dest=org.freedesktop.systemd1 \
    /org/freedesktop/systemd1 org.freedesktop.DBus.Properties.Get \
    string:org.freedesktop.systemd1.Manager string:Version

# Start a unit
dbus-send --system --print-reply --dest=org.freedesktop.systemd1 \
    /org/freedesktop/systemd1 \
    org.freedesktop.systemd1.Manager.StartUnit \
    string:nginx.service string:replace
```

Better alternatives:

- **`busctl`** — systemd's all-singing D-Bus inspector: `busctl list`, `busctl tree`, `busctl introspect`, `busctl monitor`, `busctl call`, `busctl emit`.
- **`gdbus`** — GLib's CLI: `gdbus call`, `gdbus introspect`, `gdbus monitor`.
- **`gdbus-codegen`** — generates C bindings from introspection XML.

## 9. sd-bus

`sd-bus` is systemd's own D-Bus client library, written from scratch in C, with no external dependencies. It lives in `src/libsystemd/sd-bus/` in the systemd tree and is exported as `libsystemd.so`. Compared to the traditional `libdbus`, it is significantly faster (zero-copy message construction, varlink-style builder macros), it integrates with `sd-event` for I/O, and it is what PID 1 itself uses to talk to other services.

A typical sd-bus method call looks like:

```c
#include <stdio.h>
#include <systemd/sd-bus.h>

int main(void) {
    sd_bus *bus = NULL;
    sd_bus_error err = SD_BUS_ERROR_NULL;
    sd_bus_message *m = NULL;
    const char *v;

    sd_bus_open_system(&bus);   /* connect to the system bus */

    sd_bus_call_method(bus,
        "org.freedesktop.systemd1",          /* destination */
        "/org/freedesktop/systemd1",         /* path */
        "org.freedesktop.DBus.Properties",   /* interface */
        "Get",                               /* member */
        &err, &m,                            /* error, return message */
        "ss",                                /* input signature */
        "org.freedesktop.systemd1.Manager",  /* arg0 */
        "Version");                          /* arg1 */

    sd_bus_message_read(m, "v", "s", &v);
    printf("systemd version: %s\n", v);

    sd_bus_message_unref(m);
    sd_bus_error_free(&err);
    sd_bus_unref(bus);
    return 0;
}
```

To build:

```bash
gcc example.c -o example $(pkg-config --cflags --libs libsystemd)
```

sd-bus also exposes a high-level **vtable** API for writing service objects declaratively:

```c
static int method_hello(sd_bus_message *m, void *userdata, sd_bus_error *ret_error) {
    return sd_bus_reply_method_return(m, "s", "hello from the bus");
}

static const sd_bus_vtable test_vtable[] = {
    SD_BUS_VTABLE_START(0),
    SD_BUS_METHOD("Hello", "", "s", method_hello, 0),
    SD_BUS_SIGNAL("Pong", "s", 0),
    SD_BUS_VTABLE_END
};

int main(void) {
    sd_bus *bus = NULL;
    sd_bus_slot *slot = NULL;
    sd_bus_open_user(&bus);
    sd_bus_add_object_vtable(bus, &slot, "/org/example/Test",
                             "org.example.Test", test_vtable, NULL);
    sd_bus_request_name(bus, "org.example.Test", 0);
    for (;;) sd_bus_process(bus, NULL);     /* dispatch */
}
```

For the full reference, see the [sd-bus documentation](https://www.freedesktop.org/software/systemd/man/sd-bus.html) and Lennart Poettering's [Writing a D-Bus service in C with sd-bus](https://0pointer.de/blog/projects/the-new-systemd-bus-api.html) blog post.

## 10. D-Bus vs other IPC

| | D-Bus | UNIX socket | gRPC | Avahi/mDNS |
|--|-------|-------------|------|-------------|
| Topology | Bus (N-to-N) | Point-to-point | Point-to-point | Discovery only |
| Format | binary, hand-coded | bytes (you choose) | Protobuf over HTTP/2 | text |
| Discovery | Names on bus | none | none (no service registry) | yes |
| Activation | yes (D-Bus activation) | no | no | no |
| Latency | ~10–100 µs typical | ~10 µs | ~ms (HTTP overhead) | seconds |
| Throughput | low (MB/s) | high (GB/s) | high | n/a |
| Cross-host | no (by default) | no | yes | yes |
| Use case | Desktop IPC, system control | ad-hoc services | microservices | mDNS only |

For hot paths (e.g. Wayland), D-Bus is bypassed in favour of custom UNIX socket protocols because the daemon in the loop adds latency and a single point of failure. For **control plane** ("tell the system to do X"), D-Bus's combination of introspection, activation, and bus semantics makes it the right tool.

## References

- D-Bus specification, https://dbus.freedesktop.org/doc/dbus-specification.html
- D-Bus tutorial, https://dbus.freedesktop.org/doc/dbus-tutorial.html
- man dbus-send(1), https://man7.org/linux/man-pages/man1/dbus-send.1.html
- man dbus-daemon(1), https://man7.org/linux/man-pages/man1/dbus-daemon.1.html
- sd-bus documentation, https://www.freedesktop.org/software/systemd/man/sd-bus.html
- Lennart Poettering, "The New sd-bus API", https://0pointer.de/blog/projects/the-new-systemd-bus-api.html
- LWN: "A look at D-Bus" — Jake Edge, https://lwn.net/Articles/328516/
- LWN: "D-Bus 1.0 released" — Jonathan Corbet, https://lwn.net/Articles/211540/
- busctl(1) man page, https://www.freedesktop.org/software/systemd/man/busctl.html
- gdbus(1) man page, https://man7.org/linux/man-pages/man1/gdbus.1.html
