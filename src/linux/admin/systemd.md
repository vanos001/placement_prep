# systemd — System and Service Manager

systemd is the init system and service manager for modern Linux distributions. It manages the boot process, services, mounts, timers, logging, and much more. Despite controversy over its design philosophy, systemd has become the standard init system on virtually all major Linux distributions including RHEL, CentOS, Fedora, Ubuntu, Debian, SUSE, and Arch.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    systemd Architecture                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PID 1: systemd (init)                                  │
│  ├── systemd-journald    (logging)                      │
│  ├── systemd-logind      (login sessions)               │
│  ├── systemd-networkd    (network management)           │
│  ├── systemd-resolved    (DNS resolution)               │
│  ├── systemd-timesyncd   (time synchronization)         │
│  ├── systemd-udevd       (device management)            │
│  ├── systemd-tmpfiles    (temporary files)              │
│  └── systemd-userdb      (user/group management)        │
│                                                         │
│  Unit Files:                                            │
│  /etc/systemd/system/     (local admin overrides)       │
│  /run/systemd/system/     (runtime units)               │
│  /lib/systemd/system/     (distribution packages)       │
│                                                         │
│  Targets (runlevels):                                   │
│  poweroff.target  →  runlevel 0                         │
│  rescue.target    →  runlevel 1                         │
│  multi-user.target→  runlevel 3                         │
│  graphical.target →  runlevel 5                         │
│  reboot.target    →  runlevel 6                         │
└─────────────────────────────────────────────────────────┘
```

## Unit Types

systemd manages resources through **units**. Each unit has a type that determines what it manages.

### Unit Types Table

| Type | Extension | Purpose |
|------|-----------|---------|
| Service | `.service` | Daemons, processes |
| Socket | `.socket` | IPC sockets, network sockets |
| Timer | `.timer` | Scheduled tasks (cron replacement) |
| Mount | `.mount` | Filesystem mounts |
| Automount | `.automount` | On-demand mounts |
| Swap | `.swap` | Swap partitions/files |
| Target | `.target` | Grouping of units (like runlevels) |
| Device | `.device` | Device units (udev) |
| Slice | `.slice` | Cgroup hierarchy |
| Scope | `.scope` | Externally-created processes |
| Path | `.path` | Path-based activation |
| Snapshot | `.snapshot` | Saved state of systemd |
| Journal | `.journal` | Journal files |
| Timer | `.timer` | Timer-based activation |

## Service Units

### Basic Service Unit Structure

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application Service
Documentation=https://example.com/docs
After=network.target postgresql.service
Requires=postgresql.service
Wants=redis.service

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
Environment=NODE_ENV=production
EnvironmentFile=-/etc/myapp/env
ExecStartPre=/usr/bin/myapp-check
ExecStart=/usr/bin/myapp --config /etc/myapp/config.yaml
ExecStartPost=/usr/bin/myapp-post-start
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/usr/bin/myapp-stop
Restart=on-failure
RestartSec=5
StartLimitBurst=3
StartLimitIntervalSec=60

# Security
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/myapp /var/log/myapp
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Service Types

```ini
# Type=simple (default)
# Process started by ExecStart is the main process
[Service]
Type=simple
ExecStart=/usr/bin/myapp

# Type=forking
# Process forks and parent exits; systemd tracks child via PIDFile
[Service]
Type=forking
PIDFile=/var/run/myapp.pid
ExecStart=/usr/bin/myapp --daemon

# Type=oneshot
# Process exits after completion; use RemainAfterExit=yes to keep unit "active"
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/myapp-init
ExecStop=/usr/bin/myapp-cleanup

# Type=notify
# Process sends readiness notification via sd_notify()
[Service]
Type=notify
ExecStart=/usr/bin/myapp
# In code: sd_notify(0, "READY=1")

# Type=dbus
# Process acquires a D-Bus name
[Service]
Type=dbus
BusName=com.example.myapp
ExecStart=/usr/bin/myapp

# Type=idle
# Like simple, but waits until all jobs are dispatched
[Service]
Type=idle
ExecStart=/usr/bin/myapp
```

### Service Dependencies and Ordering

```ini
[Unit]
# Ordering: start after these units
After=network.target syslog.target

# Requirement: these units must be active
Requires=postgresql.service

# Weak requirement: try to start, but don't fail if unavailable
Wants=redis.service

# Reverse of Requires: if this unit stops, stop that one too
BindsTo=postgresql.service

# Conflict: cannot run simultaneously with these units
Conflicts=iptables.service

# Requisite: must already be active (don't try to start)
Requisite=network.target

# PartOf: if this unit restarts, restart related units too
PartOf=myapp.target
```

### Dependency Resolution

```
┌─────────────────────────────────────────────────────┐
│  Dependency Types                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Type        │  Start    │  Stop     │  Failure     │
│  ────────────┼───────────┼───────────┼───────────── │
│  Requires    │  Start    │  No effect│  Stop both   │
│  Requisite   │  Must be  │  No effect│  Fail        │
│              │  active   │           │              │
│  Wants       │  Try start│  No effect│  No effect   │
│  BindsTo     │  Start    │  Stop both│  Stop both   │
│  PartOf      │  Nothing  │  Stop     │  Nothing     │
│  Conflicts   │  Stop     │  Start    │  —           │
│              │  other    │  other    │              │
│                                                     │
│  Ordering (After/Before) does NOT imply dependency! │
│  Requires=a.service After=a.service                 │
│  → Start a first, then this. If a fails, stop this.│
└─────────────────────────────────────────────────────┘
```

### Dependency Resolution Internals

systemd resolves dependencies using a **transaction** mechanism:

```c
/* src/core/transaction.c (simplified) */

/* When starting a unit, systemd: */
static int transaction_add_job_and_dependencies(
    Manager *m, JobType type, Unit *unit,
    Job *by, bool matters, Job **ret)
{
    /* 1. Add the requested job (e.g., START for unit) */
    /* 2. Recursively add Requires/Wants dependencies */
    /* 3. Add After ordering for each dependency */
    /* 4. Check for conflicts (Conflicts=) */
    /* 5. Verify no circular dependencies exist */
    /* 6. Merge with existing transaction */
}
```

```bash
# View the complete dependency tree of a unit
$ systemctl list-dependencies nginx.service
nginx.service
● ├─-.mount
● ├─system.slice
● ├─network.target
● │ └─NetworkManager.service
● └─sysinit.target
●   ├─dev-hugepages.mount
●   └─...

# Reverse dependencies (what depends on this unit)
$ systemctl list-dependencies --reverse nginx.service
# Shows what would be affected if nginx.service stops

# View all ordering dependencies
$ systemctl show nginx.service --property=After
After=sysinit.target basic.target network.target

# View all requirement dependencies
$ systemctl show nginx.service --property=Requires,Wants
Requires=system.slice
Wants=network.target
```

### Target Ordering and Dependencies

Targets can have their own dependency chains:

```ini
# multi-user.target depends on:
[Unit]
Requires=basic.target
After=basic.target
AllowIsolate=yes

# graphical.target depends on:
[Unit]
Requires=multi-user.target
After=multi-user.target
Conflicts=rescue.target
```

```bash
# View target dependency chain
$ systemctl list-dependencies graphical.target
graphical.target
└─multi-user.target
  ├─basic.target
  │ ├─sockets.target
  │ │ ├─dbus.socket
  │ │ └─...
  │ ├─slices.target
  │ └─...
  ├─getty.target
  └─remote-fs.target
```

## Target Units

Targets group units together and replace the SysV init runlevel concept.

### Built-in Targets

```bash
# List all targets
systemctl list-units --type=target

# Common targets
systemctl get-default                    # Current default target
systemctl set-default multi-user.target  # Set default target

# Target equivalents
# poweroff.target   →  runlevel 0
# rescue.target     →  runlevel 1 (single-user)
# multi-user.target →  runlevel 3 (multi-user, no GUI)
# graphical.target  →  runlevel 5 (multi-user + GUI)
# reboot.target     →  runlevel 6
# emergency.target  →  Emergency shell
# rescue.target     →  Rescue mode
```

### Custom Target

```ini
# /etc/systemd/system/myapp.target
[Unit]
Description=My Application Stack
Requires=postgresql.service myapp.service nginx.service
After=network.target
AllowIsolate=yes

[Install]
WantedBy=multi-user.target
```

```bash
# Switch to custom target
systemctl isolate myapp.target

# Start all units required by target
systemctl start myapp.target
```

## Timer Units

Timers replace cron jobs with more flexible scheduling.

### Timer Unit Structure

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily backup timer

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=300
Unit=backup.service

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Daily backup

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup.sh
User=backup
```

### Timer Specifications

```ini
[Timer]
# Real-time (wall clock)
OnCalendar=*-*-* 02:00:00           # Every day at 2 AM
OnCalendar=Mon *-*-* 09:00:00       # Every Monday at 9 AM
OnCalendar=*-01,04,07,10-01 00:00   # Quarterly
OnCalendar=hourly                    # Every hour
OnCalendar=daily                     # Every day at midnight
OnCalendar=weekly                    # Every Monday at midnight
OnCalendar=monthly                   # 1st of month at midnight

# Monotonic (relative to boot/unit activation)
OnBootSec=5min                       # 5 min after boot
OnStartupSec=10min                   # 10 min after systemd starts
OnUnitActiveSec=1h                   # 1 hour after unit last activated
OnUnitInactiveSec=30min              # 30 min after unit last deactivated

# Calendar format details
# DOW YYYY-MM-DD HH:MM:SS
# DOW: Mon,Tue,Wed,Thu,Fri,Sat,Sun (optional)
# YYYY, MM, DD: ranges and wildcards
# Special: minutely, hourly, daily, weekly, monthly, yearly

# Examples
OnCalendar=Mon..Fri *-*-* 09:00:00  # Weekdays at 9 AM
OnCalendar=*-*-* 00/6:00:00         # Every 6 hours
OnCalendar=*-*-1,15 00:00:00        # 1st and 15th of month
```

### Timer Options

```ini
[Timer]
# Don't start missed timers (default: no)
Persistent=true

# Random delay to prevent thundering herd
RandomizedDelaySec=1h

# Accuracy
AccuracySec=1s                       # Default: 1min

# Run even if system was off
WakeSystem=true

# Don't run if on battery
OnACPower=true

# Deactivate after running
DeactivateSec=30min
```

### Timer Management

```bash
# List all timers
systemctl list-timers --all

# Enable timer
systemctl enable backup.timer
systemctl start backup.timer

# Check timer status
systemctl status backup.timer

# View timer schedule
systemctl list-timers backup.timer

# Check next run time
systemctl show backup.timer --property=NextElapseUSecRealtime

# Manually trigger associated service
systemctl start backup.service
```

## Socket Activation

Socket activation starts services on-demand when a connection arrives.

### Socket Unit

```ini
# /etc/systemd/system/myapp.socket
[Unit]
Description=My App Socket

[Socket]
ListenStream=8080
# Or Unix socket:
# ListenStream=/run/myapp/myapp.sock
# ListenFIFO=/run/myapp/myapp.fifo
Accept=no
MaxConnections=100

[Install]
WantedBy=sockets.target
```

### Service for Socket Activation

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My App Service
Requires=myapp.socket

[Service]
Type=simple
ExecStart=/usr/bin/myapp --socket-activation
# The service inherits the socket fd from systemd
```

### How Socket Activation Works

```
┌─────────────────────────────────────────────────────┐
│  Socket Activation Flow                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. systemd creates socket (e.g., port 8080)        │
│  2. Client connects to port 8080                     │
│  3. systemd starts myapp.service                     │
│  4. myapp receives the socket fd                     │
│  5. myapp handles the connection                     │
│  6. myapp stays running for future connections       │
│                                                     │
│  Benefits:                                           │
│  - No startup latency until first request            │
│  - No race conditions during boot                    │
│  - Zero-downtime restarts                            │
│  - Parallel startup without port conflicts           │
└─────────────────────────────────────────────────────┘
```

### Socket Activation with Accept=yes

```ini
# /etc/systemd/system/myapp@.socket
[Unit]
Description=My App Per-Connection Socket

[Socket]
ListenStream=8080
Accept=yes

[Install]
WantedBy=sockets.target
```

```ini
# /etc/systemd/system/myapp@.service
[Unit]
Description=My App Per-Connection Service

[Service]
Type=simple
ExecStart=/usr/bin/myapp
StandardInput=socket
# Each connection gets its own service instance
```

### Socket Activation Internals

systemd implements socket activation through file descriptor passing:

```c
/* src/core/socket.c (simplified) */

/* When Accept=yes: */
static int socket_accept(struct Socket *s)
{
    /* 1. Accept new connection on listening socket */
    int fd = accept4(s->fd, NULL, NULL, SOCK_NONBLOCK | SOCK_CLOEXEC);

    /* 2. Spawn new service instance */
    /* The connection fd is passed as fd 3 (or via stdin) */
    Service *service = service_new(s->service_template);
    service->stdin_fd = fd;

    /* 3. Start the service */
    service_start(service);
}

/* When Accept=no: */
static int socket_start_no_accept(struct Socket *s)
{
    /* 1. Create listening socket */
    int fd = socket(s->address.family, s->address.type, 0);
    bind(fd, s->address.sockaddr, s->address.size);
    listen(fd, s->backlog);

    /* 2. Pass fd to service */
    /* Service inherits the socket fd */
}
```

### Socket Types and Protocols

```ini
[Socket]
# TCP stream socket
ListenStream=8080
ListenStream=127.0.0.1:9090
ListenStream=[::1]:9090

# Unix stream socket
ListenStream=/run/myapp/myapp.sock

# Unix datagram socket
ListenDatagram=/run/myapp/myapp.dgram

# UDP socket
ListenDatagram=0.0.0.0:5353

# FIFO (named pipe)
ListenFIFO=/run/myapp/myapp.fifo

# Netlink socket
ListenNetlink=kobject-uevent 1

# Sequential packet socket
ListenSequentialPacket=/run/myapp/myapp.seqpacket
```

### Socket Options

```ini
[Socket]
# Socket permissions
SocketMode=0660
SocketUser=myapp
SocketGroup=myapp

# Reuse address (SO_REUSEADDR)
ReusePort=true

# Backlog
Backlog=128

# Keep alive
KeepAlive=true
KeepAliveTimeSec=60
KeepAliveIntervalSec=10
KeepAliveProbes=6

# Buffer sizes
ReceiveBuffer=1M
SendBuffer=1M

# Connection limits
MaxConnections=100
MaxConnectionsPerSource=10

# Trigger limit (prevent DoS)
TriggerLimitIntervalSec=2s
TriggerLimitBurst=200

# Idle timeout (close after no activity)
TimeoutIdleSec=300
```

## cgroups Integration

systemd uses cgroups to organize processes and manage resources.

### Resource Control

```ini
# /etc/systemd/system/myapp.service
[Service]
# CPU
CPUQuota=200%                    # Max 2 CPU cores
CPUWeight=100                    # Relative weight (default: 100)
CPUAccounting=true

# Memory
MemoryLimit=2G                   # Max memory
MemoryHigh=1G                    # Soft limit (triggers reclaim)
MemoryMax=2G                     # Hard limit
MemoryAccounting=true

# I/O
IOWeight=100                     # Relative I/O weight
IOReadBandwidthMax=/dev/sda 50M  # Max read bandwidth
IOWriteBandwidthMax=/dev/sda 20M # Max write bandwidth
IOAccounting=true

# Tasks
TasksMax=512                     # Max processes/threads
TasksAccounting=true

# Network
IPAccounting=true
IPAddressAllow=10.0.0.0/8
IPAddressDeny=0.0.0.0/0

# Block I/O
BlockIOWeight=100
BlockIOReadBandwidthMax=/dev/sda 100M
```

### Runtime Resource Modification

```bash
# View current resource usage
systemctl status myapp.service
systemd-cgtop

# Modify resources at runtime
systemctl set-property myapp.service CPUQuota=300%
systemctl set-property myapp.service MemoryMax=4G

# Make changes persistent
systemctl edit myapp.service
# Add [Service] section with resource limits

# View cgroup hierarchy
systemd-cgls

# View resource usage
systemd-cgtop
```

### cgroup v2 Hierarchy

```bash
# View cgroup tree
systemd-cgls

# Output example:
# Control group /:
# ├─user.slice
# │ ├─user-1000.slice
# │ │ ├─session-1.scope
# │ │ │ ├─ 1234 bash
# │ │ │ └─ 5678 vim
# ├─system.slice
# │ ├─nginx.service
# │ │ ├─1111 nginx: master process
# │ │ └─1112 nginx: worker process
# │ ├─postgresql.service
# │ │ └─2222 postgres

# Check cgroup version
stat -fc %T /sys/fs/cgroup/
# cgroup2fs = cgroup v2
# tmpfs = cgroup v1
```

## journald — The systemd Journal

The journal is systemd's logging system, replacing traditional syslog.

### Journal Query Commands

```bash
# View all logs
journalctl

# Follow new logs
journalctl -f

# View logs for specific unit
journalctl -u nginx.service
journalctl -u nginx.service -f    # Follow

# View logs since time
journalctl --since "2024-01-01 00:00:00"
journalctl --since "1 hour ago"
journalctl --since "yesterday"
journalctl --since today

# View logs until time
journalctl --until "2024-01-01 12:00:00"

# Time range
journalctl --since "2024-01-01" --until "2024-01-02"

# View by priority
journalctl -p err                  # Errors only
journalctl -p warning              # Warnings and above
journalctl -p emerg..err           # Emergency to error

# Priority levels:
# 0: emerg
# 1: alert
# 2: crit
# 3: err
# 4: warning
# 5: notice
# 6: info
# 7: debug

# View by boot
journalctl -b                      # Current boot
journalctl -b -1                   # Previous boot
journalctl --list-boots            # List all boots

# View kernel messages
journalctl -k                      # Like dmesg
journalctl -k -b                   # Current boot only

# View by PID
journalctl _PID=1234

# View by UID
journalctl _UID=1000

# View by syslog facility
journalctl -t sshd

# Output formats
journalctl -o json-pretty          # JSON format
journalctl -o short-iso            # ISO timestamps
journalctl -o verbose              # All fields
journalctl -o cat                  # Message only

# Disk usage
journalctl --disk-usage

# Verify journal files
journalctl --verify

# Vacuum old logs
journalctl --vacuum-time=30d       # Keep 30 days
journalctl --vacuum-size=500M      # Keep 500MB max
journalctl --vacuum-files=10       # Keep 10 files max
```

### Journal Filtering Deep Dive

The journal supports rich field-based filtering:

```bash
# Filter by any journal field
journalctl CONTAINER_NAME=webapp
journalctl _SYSTEMD_UNIT=docker.service
journalctl _COMM=sshd
journalctl _EXE=/usr/sbin/sshd
journalctl _CMDLINE=\"nginx -g daemon off;\"

# Combine multiple filters (AND)
journalctl _UID=1000 _COMM=bash

# Combine with OR using +
journalctl -u nginx.service -u apache2.service

# Exclude specific units
journalctl -u nginx.service --no-pager | grep -v healthcheck

# Full-text search
journalctl -g "connection refused"
journalctl -g "OOM"               # Out-of-memory kills
journalctl -g "segfault"          # Segfaults

# Regex search (ERE)
journalctl -g "error|fail|denied" -p err

# Filter by executable path
journalctl /usr/bin/python3

# View all fields of a log entry
journalctl -o verbose -u nginx.service | head -20
# Shows: _PID, _UID, _GID, _COMM, _EXE, _CMDLINE,
#        _SYSTEMD_UNIT, _BOOT_ID, _MACHINE_ID, etc.

# Export specific fields
journalctl -u nginx.service -o json-pretty | jq '.[] | {timestamp: .__REALTIME_TIMESTAMP, message: .MESSAGE}'

# Rate limiting: view messages that were suppressed
journalctl --rate-limit
# Shows rate-limited messages and limits

# Filter by container/Podman
journalctl CONTAINER_NAME=myapp
journalctl _UID=100000 CONTAINER_NAME=webapp
```

### Structured Logging with journald

Applications can send structured fields to the journal:

```c
#include <systemd/sd-journal.h>

/* Send structured log message */
sd_journal_send("MESSAGE=Connection accepted",
                "PRIORITY=6",
                "MYAPP_CLIENT_IP=10.0.0.1",
                "MYAPP_REQUEST_ID=abc123",
                NULL);

/* Or via stdout with structured fields */
printf("Connection accepted\n"
       "MYAPP_CLIENT_IP=10.0.0.1\n"
       "MYAPP_REQUEST_ID=abc123\n");
```

```bash
# Query custom fields
journalctl MYAPP_CLIENT_IP=10.0.0.1
journalctl MYAPP_REQUEST_ID=abc123

# View all unique values for a field
journalctl -F MYAPP_CLIENT_IP
```

### Journal Configuration

```ini
# /etc/systemd/journald.conf
[Journal]
Storage=persistent                 # persistent, volatile, auto, none
SystemMaxUse=500M                  # Max disk usage
SystemKeepFree=1G                  # Keep this much free
SystemMaxFileSize=50M              # Max single file size
SystemMaxFiles=10                  # Max number of journal files
MaxRetentionSec=3month             # Max retention time
MaxFileSec=1month                  # Max time per file
ForwardToSyslog=yes                # Forward to syslog
Compress=yes                       # Compress journal data
Seal=yes                           # Sign journal with FSeal
SplitMode=uid                      # Split by UID
RateLimitIntervalSec=30s           # Rate limit window
RateLimitBurst=10000               # Max messages per window
```

### Persistent Journal Setup

```bash
# Create journal directory (if not using Storage=persistent)
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal

# Restart journald
sudo systemctl restart systemd-journald

# Verify
journalctl --disk-usage
```

### Journal Remote (Centralized Logging)

```ini
# /etc/systemd/journal-remote.conf
[Remote]
SplitMode=host
Seal=false

# /etc/systemd/journal-upload.conf
[Upload]
URL=https://logserver.example.com:19532
ServerCertificateFile=/etc/ssl/certs/logserver.pem
ServerKeyFile=/etc/ssl/private/logserver.key
TrustedCertificateFile=/etc/ssl/certs/ca.pem
```

## Path Units

Path units activate services when filesystem events occur.

```ini
# /etc/systemd/system/watch-config.path
[Unit]
Description=Watch config file for changes

[Path]
PathModified=/etc/myapp/config.yaml
PathExists=/etc/myapp/enable
PathChanged=/etc/myapp/state
MakeDirectory=yes

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/watch-config.service
[Unit]
Description=Reload myapp on config change

[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl reload myapp.service
```

## ExecStart Modifiers

```ini
[Service]
# Prefixes modify command behavior
ExecStart=-/usr/bin/may-fail        # - : Ignore exit code
ExecStart=!/usr/bin/must-succeed    # ! : Run with elevated privileges
ExecStart=+/usr/bin/privileged      # + : Run as root (ignoring User=)
ExecStart=!!/usr/bin/privileged     # !!: Run as root (full privilege)

# Commands
ExecStartPre=                       # Run before main command
ExecStart=                          # Main command
ExecStartPost=                      # Run after main command
ExecReload=                         # Reload command
ExecStop=                           # Stop command
ExecStopPost=                       # Run after stop
```

## Security Hardening

```ini
[Service]
# Filesystem protection
ProtectSystem=strict                # Read-only / and /boot
ProtectHome=true                    # No access to /home, /root, /run/user
PrivateTmp=true                     # Private /tmp
PrivateDevices=true                 # No access to physical devices
PrivateNetwork=true                 # No network access
ProtectKernelTunables=true          # No /proc, /sys modification
ProtectKernelModules=true           # No module loading
ProtectKernelLogs=true              # No kernel log access
ProtectControlGroups=true           # No cgroup modification
ProtectClock=true                   # No clock modification
ProtectHostname=true                # No hostname change

# Capabilities
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
NoNewPrivileges=true

# System call filtering
SystemCallFilter=@system-service
SystemCallArchitectures=native

# Network
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
IPAddressAllow=10.0.0.0/8
IPAddressDeny=0.0.0.0/0

# Namespaces
MountAPIVFS=true
TemporaryFileSystem=/ro
BindPaths=/data:/ro/data
BindReadOnlyPaths=/etc/ssl:/ro/ssl

# Miscellaneous
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true
RestrictSUIDSGID=true
RemoveIPC=true
```

## systemctl Commands

### Service Management

```bash
# Start/stop/restart
systemctl start nginx.service
systemctl stop nginx.service
systemctl restart nginx.service
systemctl reload nginx.service     # Reload config without restart
systemctl try-restart nginx.service # Restart only if running
systemctl reload-or-restart nginx.service

# Enable/disable (start at boot)
systemctl enable nginx.service
systemctl disable nginx.service
systemctl enable --now nginx.service  # Enable and start
systemctl is-enabled nginx.service

# Status
systemctl status nginx.service
systemctl is-active nginx.service
systemctl is-failed nginx.service

# List units
systemctl list-units --type=service
systemctl list-units --type=service --state=running
systemctl list-units --failed
systemctl list-unit-files --type=service

# Mask/unmask (completely disable)
systemctl mask nginx.service       # Links to /dev/null
systemctl unmask nginx.service

# Show properties
systemctl show nginx.service
systemctl show nginx.service --property=MainPID,ActiveState,SubState

# Edit unit files
systemctl edit nginx.service       # Create override
systemctl edit --full nginx.service # Edit full unit file
systemctl revert nginx.service     # Revert to vendor defaults

# Daemon reload (after editing unit files)
systemctl daemon-reload

# Show dependency tree
systemctl list-dependencies nginx.service
systemctl list-dependencies --reverse nginx.service

# Environment
systemctl show-environment
systemctl set-environment MY_VAR=value
systemctl unset-environment MY_VAR
```

### System Commands

```bash
# Power management
systemctl poweroff
systemctl reboot
systemctl suspend
systemctl hibernate
systemctl hybrid-sleep

# Target management
systemctl get-default
systemctl set-default multi-user.target
systemctl isolate rescue.target
systemctl list-dependencies graphical.target

# System state
systemctl is-system-running
systemctl status

# Analyze boot time
systemd-analyze
systemd-analyze blame
systemd-analyze critical-chain
systemd-analyze plot > boot.svg
systemd-analyze verify nginx.service

# Temporary files
systemd-tmpfiles --clean
systemd-tmpfiles --create
systemd-tmpfiles --remove
```

## Drop-in Overrides

Instead of editing vendor unit files, use drop-in overrides:

```bash
# Create override directory
systemctl edit nginx.service
# Opens $EDITOR with empty override file

# Example override: add environment variables
# /etc/systemd/system/nginx.service.d/override.conf
[Service]
Environment="NGINX_WORKER_PROCESSES=4"
Environment="NGINX_WORKER_CONNECTIONS=1024"

# Example override: change restart behavior
[Service]
Restart=always
RestartSec=10

# Apply changes
systemctl daemon-reload
systemctl restart nginx.service

# View effective unit (merged)
systemctl cat nginx.service

# View just overrides
systemctl cat nginx.service | grep -A 20 '# /etc/systemd/system'
```

## Debugging systemd

```bash
# View unit logs
journalctl -u nginx.service
journalctl -u nginx.service -e    # Jump to end

# Debug startup
systemd-analyze plot > boot.svg
systemd-analyze blame | head -20
systemd-analyze critical-chain nginx.service

# Debug unit dependencies
systemctl list-dependencies nginx.service
systemctl list-dependencies --reverse nginx.service

# Debug failed units
systemctl --failed
systemctl status nginx.service -l
journalctl -u nginx.service --no-pager -n 50

# Debug systemd itself
journalctl -b -u systemd
systemd-analyze verify nginx.service

# Test unit file without starting
systemd-analyze security nginx.service
```

## Cross-References

- [Cron and Systemd Timers](cron.md) — Timer-based task scheduling
- [Users and Groups](users-groups.md) — User management for services
- [File Permissions](permissions.md) — Security hardening with capabilities
- [LVM](lvm.md) — Mount units for LVM volumes

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [systemd Official Documentation](https://systemd.io/) — Project documentation
- [systemd.unit(5) Man Page](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) — Unit file reference
- [systemd.service(5) Man Page](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — Service unit reference
- [systemd.timer(5) Man Page](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) — Timer unit reference
- [systemd.journal-fields(7)](https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html) — Journal field reference
- [Freedesktop systemd Pages](https://www.freedesktop.org/wiki/Software/systemd/) — Wiki and specifications
- [The systemd for Administrators Blog Series](https://0pointer.de/blog/projects/systemd-for-admins-1.html) — Lennart Poettering's guide
