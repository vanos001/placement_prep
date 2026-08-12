# System Logging

## Introduction

Logging is the backbone of system observability. Every significant event on a Linux system—authentication attempts, service starts/stops, kernel messages, application errors—generates a log entry. Proper logging configuration enables troubleshooting, security auditing, compliance, and performance monitoring.

Linux has evolved from simple text-file-based syslog to the structured, indexed logging of systemd's journald. Modern systems typically run both: journald for structured query and syslog for compatibility and remote forwarding.

## The Linux Logging Ecosystem

```mermaid
graph TD
    Apps["Applications"] -->|"fprintf/syslog()"| Syslog["syslog API"]
    Kernel["Linux Kernel"] -->|"/dev/kmsg"| Journald["systemd-journald"]
    Syslog --> Journald
    Journald --> Journal["Journal Files<br>/var/log/journal/"]
    Journald -->|"ForwardToSyslog=yes"| Rsyslog["rsyslog"]
    Rsyslog --> TextLogs["Text Log Files<br>/var/log/"]
    Rsyslog -->|"Remote"| Remote["Remote Syslog Server<br>logstash, papertrail"]
    Apps -->|"sd_journal_print()"| Journald
    
    style Journald fill:#3182ce,color:#fff
    style Rsyslog fill:#38a169,color:#fff
    style Journal fill:#d69e2e,color:#fff
```

## syslog — The Traditional Logging Framework

### syslog Facility and Severity

Every syslog message has a **facility** (source category) and **severity** (importance level):

| Facility | Code | Description |
|----------|------|-------------|
| `kern` | 0 | Kernel messages |
| `user` | 1 | User-level messages |
| `mail` | 2 | Mail system |
| `daemon` | 3 | System daemons |
| `auth` | 4 | Authentication |
| `syslog` | 5 | syslogd internal |
| `lpr` | 6 | Printer |
| `news` | 7 | Usenet |
| `cron` | 8 | Cron daemon |
| `authpriv` | 9 | Private auth |
| `ftp` | 10 | FTP daemon |
| `local0-7` | 16-23 | Local use |

| Severity | Code | Name | Description |
|----------|------|------|-------------|
| 0 | `emerg` | Emergency | System is unusable |
| 1 | `alert` | Alert | Immediate action required |
| 2 | `crit` | Critical | Critical conditions |
| 3 | `err` | Error | Error conditions |
| 4 | `warning` | Warning | Warning conditions |
| 5 | `notice` | Notice | Normal but significant |
| 6 | `info` | Info | Informational |
| 7 | `debug` | Debug | Debug messages |

### Using `logger`

```bash
# Send a message to syslog
logger "Hello from the command line"

# Specify facility and severity
logger -p auth.info "User admin logged in"
logger -p local0.err "Application error occurred"

# Send to specific syslog socket
logger -u /dev/log "Custom message"

# Tag (identifies the source)
logger -t myapp "Processing complete"

# Multi-line message
echo -e "Line 1\nLine 2\nLine 3" | logger -t multiline

# Read from stdin (piping)
tail -f /var/log/app.log | logger -t myapp -p local0.info
```

### Writing to syslog from Code

```c
#include <syslog.h>

int main() {
    /* Open syslog connection */
    openlog("myapp", LOG_PID | LOG_CONS, LOG_LOCAL0);
    
    /* Log at different levels */
    syslog(LOG_INFO, "Application started, version %s", VERSION);
    syslog(LOG_WARNING, "Disk usage at %d%%", disk_pct);
    syslog(LOG_ERR, "Failed to open config: %s", strerror(errno));
    syslog(LOG_DEBUG, "Processing item %d", item_id);
    
    /* Close when done */
    closelog();
    return 0;
}
```

```python
# Python
import syslog
syslog.openlog("myapp", syslog.LOG_PID, syslog.LOG_LOCAL0)
syslog.syslog(syslog.LOG_INFO, "Application started")
syslog.syslog(syslog.LOG_ERR, "Something went wrong")
```

## journald — systemd's Journal

systemd-journald is the modern logging daemon that collects and manages structured log data. It stores logs in a binary format with rich metadata.

### Querying the Journal

```bash
# View all journal entries
journalctl

# Follow live (like tail -f)
journalctl -f

# Show recent entries
journalctl -n 50               # Last 50 entries

# Show since specific time
journalctl --since "2025-07-21 10:00:00"
journalctl --since "1 hour ago"
journalctl --since today
journalctl --since yesterday --until today

# Filter by service/unit
journalctl -u nginx
journalctl -u nginx -u php-fpm   # Multiple units
journalctl -u sshd --since "1 hour ago"

# Filter by priority
journalctl -p err               # Errors and above
journalctl -p warning           # Warnings and above
journalctl -p err..emerg        # Range

# Filter by PID
journalctl _PID=1234

# Filter by boot
journalctl -b                   # Current boot
journalctl -b -1                # Previous boot
journalctl --list-boots          # List all boots

# Filter by user
journalctl _UID=1000
journalctl _COMM=sshd           # By command name

# Kernel messages
journalctl -k                   # Like dmesg
journalctl -k -p err            # Kernel errors

# Disk usage
journalctl --disk-usage
# Archived and active journals take up 2.3G in the file system.

# Vacuum old logs
journalctl --vacuum-time=30d    # Keep last 30 days
journalctl --vacuum-size=500M   # Keep max 500MB
journalctl --vacuum-files=5     # Keep max 5 files

# Output formats
journalctl -o json-pretty       # JSON format
journalctl -o short-iso         # ISO timestamp
journalctl -o verbose           # All fields
journalctl -o cat               # Message only (no metadata)
```

### journald Configuration

```bash
# /etc/systemd/journald.conf
[Journal]
Storage=persistent          # persistent|volatile|auto|none
SystemMaxUse=2G             # Max disk usage for journal
SystemKeepFree=1G           # Keep this much free space
SystemMaxFileSize=50M       # Max size per journal file
MaxRetentionSec=3month      # Auto-delete after 3 months
MaxFileSec=1week            # Rotate files weekly
ForwardToSyslog=yes         # Forward to rsyslog
RateLimitIntervalSec=30s    # Rate limiting
RateLimitBurst=10000        # Max messages per interval
Compress=yes                # Compress journal files

# Apply changes
systemctl restart systemd-journald
```

### Persistent Journal Storage

```bash
# By default, journald stores logs in /run/log/journal (volatile)
# To make persistent:
mkdir -p /var/log/journal
systemctl restart systemd-journald

# Verify
ls -la /var/log/journal/$(cat /etc/machine-id)/
# -rw-r----- 1 root systemd-journal 8388608 Jul 21 00:00 system.journal
# -rw-r----- 1 root systemd-journal 8388608 Jul 21 12:00 user-1000.journal
```

## rsyslog — Advanced Syslog

`rsyslog` is the most widely used syslog implementation, providing powerful filtering, formatting, and forwarding capabilities.

### Basic Configuration

```bash
# /etc/rsyslog.conf

# Module loading
module(load="imuxsock")    # Local syslog socket
module(load="imklog")      # Kernel logging
module(load="imfile")       # File input module

# Default file creation
$FileCreateMode 0640
$DirCreateMode 0750
$Umask 0022

# Include config directory
include(file="/etc/rsyslog.d/*.conf" mode="optional")
```

### Log File Mapping

```bash
# /etc/rsyslog.d/50-default.conf

# Traditional log files
auth,authpriv.*        /var/log/auth.log
*.*;auth,authpriv.none /var/log/syslog
kern.*                 /var/log/kern.log
mail.*                 /var/log/mail.log
mail.err               /var/log/mail.err
cron.*                 /var/log/cron.log

# All messages to console (for emergencies)
*.emerg                :omusrmsg:*

# Specific application logging
local0.*               /var/log/myapp.log
local1.*               /var/log/myotherapp.log
```

### Application-Specific Logging

```bash
# /etc/rsyslog.d/myapp.conf

# Template for structured app logging
template(name="MyAppFormat" type="string"
    string="%TIMESTAMP:::date-rfc3339% %HOSTNAME% %syslogtag% %msg%\n")

# Log to file with template
local0.*    action(
    type="omfile"
    dynaFile="MyAppLog"
    template="MyAppFormat"
)

# Dynamic file names based on program name
template(name="MyAppLog" type="string"
    string="/var/log/apps/%programname%.log")
```

### Remote Logging

```bash
# === CLIENT: Send logs to remote server ===

# /etc/rsyslog.d/remote.conf
# TCP (reliable)
*.* @@logserver.example.com:514

# UDP (fast, unreliable)
*.* @logserver.example.com:514

# TLS encrypted
module(load="imtcp")
module(load="gtls")
global(DefaultNetstreamDriver="gtls")
global(DefaultNetstreamDriverCAFile="/etc/ssl/ca.pem")
global(DefaultNetstreamDriverCertFile="/etc/ssl/cert.pem")
global(DefaultNetstreamDriverKeyFile="/etc/ssl/key.pem")
*.* @@(o)logserver.example.com:6514

# === SERVER: Receive remote logs ===

# /etc/rsyslog.d/server.conf
module(load="imtcp")
input(type="imtcp" port="514")

# Template for remote logs
template(name="RemoteHost" type="string"
    string="/var/log/remote/%HOSTNAME%/%PROGRAMNAME%.log")

# Store remote logs by host
if $fromhost-ip != '127.0.0.1' then {
    action(type="omfile" dynaFile="RemoteHost")
    stop
}
```

## Log Rotation

### logrotate

`logrotate` manages automatic rotation, compression, and deletion of log files:

```bash
# /etc/logrotate.conf — Global settings
weekly
rotate 4
create
dateext
compress
delaycompress
include /etc/logrotate.d

# /etc/logrotate.d/syslog — System log rotation
/var/log/syslog
/var/log/mail.log
/var/log/kern.log
/var/log/auth.log
{
    rotate 7
    daily
    missingok
    notifempty
    compress
    delaycompress
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}

# /etc/logrotate.d/myapp — Application log rotation
/var/log/myapp/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    dateext
    dateformat -%Y%m%d
    size 100M
    maxsize 200M
    create 0640 myapp myapp
    sharedscripts
    postrotate
        systemctl reload myapp
    endscript
}
```

### logrotate Options

| Option | Description |
|--------|-------------|
| `daily` | Rotate daily |
| `weekly` | Rotate weekly |
| `monthly` | Rotate monthly |
| `rotate N` | Keep N rotated files |
| `size X` | Rotate when file exceeds X |
| `maxsize X` | Rotate when file exceeds X (time-based check too) |
| `compress` | Compress rotated files |
| `delaycompress` | Delay compression by one cycle |
| `missingok` | Don't error if log file missing |
| `notifempty` | Don't rotate empty files |
| `create mode owner group` | Create new file with permissions |
| `postrotate` ... `endscript` | Run command after rotation |
| `prerotate` ... `endscript` | Run command before rotation |
| `sharedscripts` | Run scripts once for all matched files |

### Testing and Debugging

```bash
# Test logrotate configuration (dry run)
logrotate -d /etc/logrotate.conf

# Force rotation
logrotate -f /etc/logrotate.d/myapp

# Verbose output
logrotate -v /etc/logrotate.conf

# Check logrotate status
cat /var/lib/logrotate/status
```

## Centralized Logging

### Architecture

```mermaid
graph LR
    subgraph "Servers"
        S1["Web Server"] -->|"rsyslog/fluentd"| LB["Log Aggregator"]
        S2["DB Server"] -->|"rsyslog/fluentd"| LB
        S3["App Server"] -->|"rsyslog/fluentd"| LB
    end
    LB --> ES["Elasticsearch<br>Index &amp; Search"]
    ES --> Kibana["Kibana<br>Visualization"]
    LB -->|"Alert rules"| Alert["Alerting<br>(PagerDuty, email)"]
    
    style ES fill:#3182ce,color:#fff
    style Kibana fill:#38a169,color:#fff
    style Alert fill:#e53e3e,color:#fff
```

### ELK Stack (Elasticsearch, Logstash, Kibana)

```yaml
# Logstash config: /etc/logstash/conf.d/syslog.conf
input {
  tcp {
    port => 514
    type => "syslog"
  }
  udp {
    port => 514
    type => "syslog"
  }
}

filter {
  if [type] == "syslog" {
    grok {
      match => { "message" => "%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:syslog_hostname} %{DATA:syslog_program}(?:\[%{POSINT:syslog_pid}\])?: %{GREEDYDATA:syslog_message}" }
    }
    date {
      match => [ "syslog_timestamp", "MMM  d HH:mm:ss", "MMM dd HH:mm:ss" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "syslog-%{+YYYY.MM.dd}"
  }
}
```

### Lightweight Alternatives

```bash
# Loki + Promtail (Grafana ecosystem)
# Lower resource usage than ELK, uses labels instead of full-text indexing

# Fluentd / Fluent Bit
# Lightweight log collector, CNCF project
# Fluent Bit is the ultra-light version for containers

# Vector (by Datadog)
# High-performance log router
# Written in Rust, very efficient
```

## Log Analysis

```bash
# Common log analysis commands

# Count errors per hour
awk '/ERROR/{split($3,a,":"); print a[1]":00"}' /var/log/app.log | sort | uniq -c

# Find most frequent errors
grep "ERROR" /var/log/app.log | awk -F'ERROR: ' '{print $2}' | sort | uniq -c | sort -rn | head

# Authentication failures
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn | head -10

# Top IPs accessing web server
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Response time analysis
awk '{print $NF}' /var/log/nginx/access.log | sort -n | tail -10

# Real-time error monitoring
tail -f /var/log/app.log | grep --line-buffered "ERROR\|WARN"

# Search journal for patterns
journalctl -u nginx --since today | grep -i "error\|500\|timeout"

# JSON log parsing (jq)
journalctl -o json -u myapp | jq 'select(.PRIORITY <= 3)' | jq -s 'length'
```

## journald Programmatic API

### sd-journal C API

```c
#include <systemd/sd-journal.h>

/* Write to journal from C */
sd_journal_print(LOG_INFO, "Application started, version %s", VERSION);
sd_journal_print(LOG_ERR, "Failed to connect: %s", strerror(errno));

/* Send with custom fields */
sd_journal_send("MESSAGE=Connection established",
                "PRIORITY=%i", LOG_INFO,
                "APP_NAME=myapp",
                "CONN_ID=%d", connection_id,
                NULL);

/* Open journal for reading */
sd_journal *j;
sd_journal_open(&j, SD_JOURNAL_LOCAL_ONLY);

/* Seek to specific time */
usec_t usec = (time_t)1690000000 * 1000000;
sd_journal_seek_realtime_usec(j, usec);

/* Iterate through entries */
while (sd_journal_next(j) > 0) {
    const char *msg;
    size_t len;
    sd_journal_get_data(j, "MESSAGE", (const void **)&msg, &len);
    printf("%.*s\n", (int)len, msg);
}

sd_journal_close(j);
```

### Python sdjournal

```python
import systemd.journal

# Write to journal
systemd.journal.send("Hello from Python",
                     PRIORITY=systemd.journal.LOG_INFO,
                     APP_NAME="myapp")

# Read journal
j = sdjournal.Journal()
j.seek_tail()
while True:
    entry = j.get_next()
    if not entry:
        break
    print(entry.get('MESSAGE', ''))
```

## Container Logging

### Podman/Docker Logging Drivers

```bash
# Podman logging drivers
podman run -d --log-driver journald nginx
podman run -d --log-driver k8s-file --log-opt path=/var/log/containers/web.log nginx

# Docker logging drivers
docker run -d --log-driver json-file --log-opt max-size=10m --log-opt max-file=3 nginx

# View container logs from journald
journalctl CONTAINER_NAME=web
journalctl CONTAINER_TAG=web
```

## Security and Audit Logging

### Authentication Logging

```bash
# SSH login tracking
grep 'Accepted\|Failed' /var/log/auth.log

# Count failed login attempts by IP
grep 'Failed password' /var/log/auth.log | \
    awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head

# sudo usage tracking
grep 'sudo:' /var/log/auth.log

# PAM authentication events
journalctl -u systemd-logind --since today
```

### Kernel Security Events

```bash
# SELinux denials
journalctl -t setroubleshoot
ausearch -m avc -ts recent

# AppArmor denials
dmesg | grep 'apparmor="DENIED"'

# seccomp violations
dmesg | grep seccomp
```

## Logging Performance Considerations

### Impact of Logging on System Performance

```bash
# Logging I/O impact:
# High-volume logging: 10,000 msg/sec x 200 bytes = 2MB/s
# On a busy system, this can saturate the logging disk

# Mitigations:
# 1. Rate limiting in journald
#    RateLimitIntervalSec=30s
#    RateLimitBurst=10000

# 2. Async logging in rsyslog
#    $OMFileAsyncWriting on

# 3. Remote logging (offload I/O to central server)
#    *.* @@logserver:514
```

### Log Compression

```bash
# Logrotate with zstd compression
/var/log/app.log {
    daily
    rotate 30
    compress
    delaycompress
    compresscmd /usr/bin/zstd
    compressext .zst
}
```

## Logging Best Practices

### Structured Logging

```bash
# Use structured formats (JSON) for machine parsing
template(name="JSONFormat" type="list") {
    constant(value="{")
    constant(value="\"timestamp\":\"")  property(name="timereported" dateFormat="rfc3339")
    constant(value="\",\"host\":\"")  property(name="hostname")
    constant(value="\",\"severity\":\"")  property(name="syslogseverity-text")
    constant(value="\",\"message\":\"")  property(name="msg" format="json")
    constant(value="\"}\n")
}

local0.* action(type="omfile" file="/var/log/app.json" template="JSONFormat")
```

### Log Levels Guidelines

| Level | When to Use | Example |
|-------|-------------|---------|
| `emerg` | System is unusable | Kernel panic, out of memory |
| `alert` | Immediate action needed | Database disk full, SSL cert expired |
| `crit` | Critical conditions | Service crash, hardware failure |
| `err` | Error conditions | Connection refused, file not found |
| `warning` | Warning conditions | High memory usage, slow queries |
| `notice` | Normal but significant | Service started, config reloaded |
| `info` | Informational | Request processed, user logged in |
| `debug` | Debug details | Variable values, function traces |

### Log Retention Policy

```bash
# Define retention based on compliance requirements
# PCI-DSS: 1 year minimum
# HIPAA: 6 years
# SOC 2: 1 year

# logrotate retention example
/var/log/auth.log {
    monthly
    rotate 24    # 2 years of monthly logs
    compress
}

# Archive old logs
find /var/log -name '*.gz' -mtime +365 -exec mv {} /archive/logs/ \;
```

## References

- [journald.conf(5) man page](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html)
- [rsyslog.conf(5) man page](https://man7.org/linux/man-pages/man5/rsyslog.conf.5.html)
- [logrotate(8) man page](https://man7.org/linux/man-pages/man8/logrotate.8.html)
- [journalctl(1) man page](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html)
- [rsyslog documentation](https://www.rsyslog.com/doc/v8-stable/)
- [Loki documentation](https://grafana.com/docs/loki/latest/)
- [sd-journal API](https://www.freedesktop.org/software/systemd/man/sd_journal_print.html)
- [LWN: The journal as a logging framework](https://lwn.net/Articles/475226/)

## Related Topics

- [System Administration Overview](./overview.md) — Monitoring and alerting practices
- [Process Management](./process-management.md) — Service and process monitoring
- [Firewall](./firewall.md) — Firewall log analysis
- [Security Overview](../security/overview.md) — Security auditing and monitoring
