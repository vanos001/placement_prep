# Cron and systemd Timers

Task scheduling is essential for system administration: running backups at night, rotating logs, cleaning temporary files, sending reports. Linux provides two main scheduling systems: the traditional **cron** daemon and the modern **systemd timers**. This chapter covers both in depth, along with `at`/`batch` for one-time scheduling.

## cron — Traditional Job Scheduler

### How cron Works

```
┌─────────────────────────────────────────────────────┐
│  cron Architecture                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  crond (daemon)                                      │
│  ├── /etc/crontab          (system crontab)         │
│  ├── /etc/cron.d/          (additional system jobs)  │
│  ├── /etc/cron.hourly/     (run every hour)         │
│  ├── /etc/cron.daily/      (run every day)          │
│  ├── /etc/cron.weekly/     (run every week)         │
│  ├── /etc/cron.monthly/    (run every month)        │
│  └── /var/spool/cron/crontabs/  (per-user crontabs) │
│                                                     │
│  Every minute, crond:                               │
│  1. Checks all crontab files                        │
│  2. Compares scheduled time with current time       │
│  3. Executes matching commands                      │
│  4. Logs execution to syslog                        │
└─────────────────────────────────────────────────────┘
```

### Crontab Syntax

```
┌─────────────────────────────────────────────────────┐
│  Crontab Fields                                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────── minute (0-59)                           │
│  │ ┌─────── hour (0-23)                             │
│  │ │ ┌───── day of month (1-31)                     │
│  │ │ │ ┌─── month (1-12)                            │
│  │ │ │ │ ┌─ day of week (0-7, 0 and 7 = Sunday)    │
│  │ │ │ │ │                                          │
│  * * * * * command                                  │
│                                                     │
│  Special characters:                                 │
│  *      Any value                                    │
│  ,      List (1,3,5)                                │
│  -      Range (1-5)                                 │
│  /N     Step (*/5 = every 5th)                      │
│                                                     │
│  Special strings:                                    │
│  @reboot    Run at startup                           │
│  @yearly    0 0 1 1 *                               │
│  @monthly   0 0 1 * *                               │
│  @weekly    0 0 * * 0                               │
│  @daily     0 0 * * *                               │
│  @hourly    0 * * * *                               │
└─────────────────────────────────────────────────────┘
```

### Crontab Examples

```bash
# Every minute
* * * * * /usr/local/bin/check.sh

# Every 5 minutes
*/5 * * * * /usr/local/bin/check.sh

# Every hour at minute 0
0 * * * * /usr/local/bin/hourly.sh

# Every day at 2:30 AM
30 2 * * * /usr/local/bin/backup.sh

# Every Monday at 9:00 AM
0 9 * * 1 /usr/local/bin/report.sh

# Every 1st of month at midnight
0 0 1 * * /usr/local/bin/monthly.sh

# Every 15 minutes between 9 AM and 5 PM on weekdays
*/15 9-17 * * 1-5 /usr/local/bin/check.sh

# Twice daily (6 AM and 6 PM)
0 6,18 * * * /usr/local/bin/check.sh

# Every 2 hours
0 */2 * * * /usr/local/bin/check.sh

# First Monday of every month
0 9 1-7 * 1 /usr/local/bin/first-monday.sh

# Last day of month (workaround)
59 23 28-31 * * [ "$(date -d tomorrow +\%d)" = "01" ] && /usr/local/bin/last-day.sh

# At system startup
@reboot /usr/local/bin/startup.sh

# With environment variables
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
MAILTO=admin@example.com
30 2 * * * /usr/local/bin/backup.sh
```

### User Crontabs

```bash
# Edit current user's crontab
crontab -e

# List current user's crontab
crontab -l

# Edit another user's crontab (root only)
sudo crontab -u username -e

# List another user's crontab
sudo crontab -u username -l

# Remove current user's crontab
crontab -r

# Remove another user's crontab (root only)
sudo crontab -u username -r

# Install crontab from file
crontab mycron.txt

# Backup crontab
crontab -l > mycron_backup.txt

# Restore from backup
crontab mycron_backup.txt
```

### System Crontabs

```bash
# /etc/crontab (system-wide, has user field)
# Format: minute hour day month weekday user command
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=root

30 2 * * * root /usr/local/bin/backup.sh

# /etc/cron.d/ (additional system jobs)
# Same format as /etc/crontab
# Each file can have different syntax
cat > /etc/cron.d/myapp <<'EOF'
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
*/5 * * * * myapp /usr/local/bin/myapp-check.sh
EOF

# /etc/cron.{hourly,daily,weekly,monthly}/
# Directories containing scripts (no crontab syntax)
# Executed by run-parts (or anacron)
ls /etc/cron.daily/
# apt-compat  dpkg  logrotate  man-db  passwd

# Scripts must be:
# - Executable
# - Owned by root
# - No dots in filename (unless configured otherwise)
# - Not match any regex in /etc/crontab or anacrontab
```

### Crontab Environment

```bash
# Variables in crontab (set before commands)
SHELL=/bin/bash          # Shell to use (default: /bin/sh)
PATH=/usr/local/bin:/usr/bin:/bin  # PATH is minimal!
MAILTO=admin@example.com # Where to send output
HOME=/root               # Home directory
LOGNAME=root             # Log name

# IMPORTANT: cron has a minimal environment!
# Always use absolute paths or set PATH explicitly

# WRONG:
30 2 * * * backup.sh

# RIGHT:
30 2 * * * /usr/local/bin/backup.sh

# Or set PATH:
PATH=/usr/local/bin:/usr/bin:/bin
30 2 * * * backup.sh
```

### Cron Output and Logging

```bash
# cron sends stdout/stderr via email to MAILTO
# To suppress email:
30 2 * * * /usr/local/bin/backup.sh > /dev/null 2>&1

# To log to file:
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# To append (don't overwrite):
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# To log with timestamp:
30 2 * * * /usr/local/bin/backup.sh 2>&1 | while IFS= read -r line; do echo "$(date '+\%Y-\%m-\%d \%H:\%M:\%S') $line"; done >> /var/log/backup.log

# Syslog logging
# cron logs to syslog (usually /var/log/syslog or /var/log/cron)
grep CRON /var/log/syslog
```

### Crontab Pitfalls

```bash
# Pitfall 1: Percent signs (%) are special
# % is interpreted as newline, everything after first %
# is passed as stdin to the command
# WRONG:
30 2 * * * /usr/bin/date +%Y-%m-%d > /tmp/date.txt
# RIGHT:
30 2 * * * /usr/bin/date +\%Y-\%m-\%d > /tmp/date.txt

# Pitfall 2: Minimal environment
# cron has very limited PATH, no .bashrc sourced
# Use absolute paths for everything

# Pitfall 3: Working directory
# cron runs from user's home directory
# Set explicit working directory:
30 2 * * * cd /opt/app && ./backup.sh

# Pitfall 4: Multiple instances
# cron doesn't prevent overlapping runs
# Use flock or lockfile:
*/5 * * * * flock -n /tmp/myjob.lock /usr/local/bin/myjob.sh

# Pitfall 5: Timezone
# System timezone affects cron
# Per-user timezone (Debian/Ubuntu):
CRON_TZ=America/New_York
30 9 * * * /usr/local/bin/report.sh    # 9:30 AM Eastern

# Pitfall 6: DST transitions
# Jobs may be skipped or run twice during DST changes
# Use UTC or handle DST in your scripts
```

## anacron — For Non-24/7 Systems

anacron runs periodic jobs that may have been missed when the system was off.

```bash
# /etc/anacrontab
# Format: period delay job-id command
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
START_HOURS_RANGE=3-22

# period    delay  job-id         command
1           5      cron.daily     nice run-parts /etc/cron.daily
7           10     cron.weekly    nice run-parts /etc/cron.weekly
@monthly    15     cron.monthly   nice run-parts /etc/cron.monthly
30          5      mybackup       /usr/local/bin/backup.sh

# period: days between runs (or @monthly, @weekly, @daily)
# delay: minutes to wait before running
# job-id: unique identifier (used for timestamp files)
# command: what to run

# anacron timestamps: /var/spool/anacron/
cat /var/spool/anacron/cron.daily
# 20240721

# Run anacron manually
sudo anacron -f    # Force run all jobs
sudo anacron -n    # Run jobs now (ignoring period)
sudo anacron -T    # Test (show what would run)

# anacron in systemd
# On modern systems, anacron is often triggered by systemd timers:
# anacron.timer → anacron.service → runs anacron
```

### How anacron Works

```
┌─────────────────────────────────────────────────────┐
│  anacron Workflow                                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  System boots / anacron starts                       │
│  ├── Read /etc/anacrontab                           │
│  ├── For each job:                                   │
│  │   ├── Check timestamp in /var/spool/anacron/     │
│  │   ├── If (current_date - last_run) >= period:    │
│  │   │   ├── Wait 'delay' minutes                   │
│  │   │   ├── Run command                            │
│  │   │   └── Update timestamp                       │
│  │   └── Else: skip                                 │
│  └── Exit                                            │
│                                                     │
│  Key differences from cron:                          │
│  - Runs missed jobs after system was off             │
│  - Uses delays to spread load at boot                │
│  - Has START_HOURS_RANGE to avoid running at night   │
│  - Timestamps in /var/spool/anacron/                │
└─────────────────────────────────────────────────────┘
```

## systemd Timers

systemd timers are the modern replacement for cron, offering more features and better integration with the system.

### Timer Unit Structure

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily backup timer
Requires=backup.service

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1800

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Backup service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup.sh
User=backup
```

### Timer Specifications

```ini
[Timer]
# Calendar events (like cron)
OnCalendar=*-*-* 02:00:00       # Every day at 2 AM
OnCalendar=Mon *-*-* 09:00:00   # Every Monday at 9 AM
OnCalendar=*-01,04,07,10-01 00:00:00  # Quarterly
OnCalendar=Fri *-*-* 17:00:00   # Every Friday at 5 PM

# Shorthand
OnCalendar=minutely             # Every minute (but not really useful)
OnCalendar=hourly               # Every hour at :00
OnCalendar=daily                # Every day at 00:00
OnCalendar=weekly               # Every Monday at 00:00
OnCalendar=monthly              # 1st of month at 00:00
OnCalendar=yearly               # Jan 1 at 00:00

# Calendar format: DOW YYYY-MM-DD HH:MM:SS
# DOW: Mon,Tue,Wed,Thu,Fri,Sat,Sun
# Wildcards: *, ranges: 1-5, lists: 1,3,5, steps: */5

# Examples:
OnCalendar=Mon..Fri *-*-* 09:00:00   # Weekdays at 9 AM
OnCalendar=*-*-* 00/2:00:00          # Every 2 hours
OnCalendar=*-*-1,15 00:00:00         # 1st and 15th
OnCalendar=*~01-07/7 *-*-* 12:00:00  # Every 7th day starting from 1st

# Monotonic timers (relative)
OnBootSec=5min                  # 5 minutes after boot
OnStartupSec=10min              # 10 minutes after systemd starts
OnUnitActiveSec=1h              # 1 hour after unit last activated
OnUnitInactiveSec=30min         # 30 min after unit last deactivated
OnActiveSec=15min               # 15 minutes after timer activated
```

### Timer Options

```ini
[Timer]
# Run missed timers after system comes back online
Persistent=true                 # Default: false

# Random delay to spread load
RandomizedDelaySec=30m          # Default: 0

# Accuracy
AccuracySec=1s                  # Default: 1min

# Wake system from sleep to run
WakeSystem=false                # Default: false

# Only run on AC power
OnACPower=true                  # Default: unset (always run)

# Deactivate timer after running
DeactivateSec=1h                # Default: unset

# Unit to activate (default: service with same name)
Unit=backup.service
```

### Timer Management Commands

```bash
# List all timers
systemctl list-timers --all

# List specific timer
systemctl list-timers backup.timer

# Enable and start timer
systemctl enable --now backup.timer

# Check timer status
systemctl status backup.timer

# View next run time
systemctl show backup.timer --property=NextElapseUSecRealtime

# Manually trigger associated service
systemctl start backup.service

# Disable timer
systemctl disable backup.timer

# View timer unit file
systemctl cat backup.timer

# Edit timer
systemctl edit backup.timer
systemctl edit --full backup.timer
```

### Timer Examples

```ini
# /etc/systemd/system/log-cleanup.timer
[Unit]
Description=Clean up old log files

[Timer]
OnCalendar=weekly
Persistent=true
RandomizedDelaySec=3600

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/log-cleanup.service
[Unit]
Description=Clean up old log files

[Service]
Type=oneshot
ExecStart=/usr/bin/find /var/log -name "*.gz" -mtime +30 -delete
ExecStart=/usr/bin/journalctl --vacuum-time=30d
```

```ini
# /etc/systemd/system/health-check.timer
[Unit]
Description=System health check

[Timer]
OnCalendar=*:0/15             # Every 15 minutes
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/nightly-maintenance.timer
[Unit]
Description=Nightly maintenance window

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=600

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/cert-renewal.timer
[Unit]
Description=Certificate renewal check

[Timer]
OnCalendar=*-*-1,15 03:00:00  # 1st and 15th at 3 AM
Persistent=true

[Install]
WantedBy=timers.target
```

### Timer vs Cron Comparison

```
┌─────────────────────────────────────────────────────────┐
│  Timer vs Cron Comparison                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Feature            │  cron          │  systemd timer    │
│  ───────────────────┼────────────────┼──────────────────│
│  Missed jobs         │  Lost (anacron │  Persistent=true │
│                      │  helps)        │  catches up      │
│  Randomization       │  Manual        │  Built-in        │
│  Boot dependency     │  @reboot       │  After= ordering │
│  Resource limits     │  None          │  Full cgroup     │
│  Logging             │  Syslog/email  │  journald        │
│  Dependencies        │  None          │  Requires=, etc. │
│  Security            │  Limited       │  Full sandboxing │
│  Monotonic timers    │  No            │  Yes             │
│  Calendar events     │  Simple        │  Rich syntax     │
│  Parallelism         │  Limited       │  Full control    │
│  Monitoring          │  Manual        │  systemctl       │
│  Wake from sleep     │  No            │  WakeSystem=yes  │
│  AC power check      │  No            │  OnACPower=yes   │
│  Random delay        │  Manual        │  Built-in        │
│  Status checking     │  Crude         │  Full status     │
└─────────────────────────────────────────────────────────┘
```

## at and batch — One-Time Scheduling

### `at` — Schedule One-Time Jobs

```bash
# Schedule job
at now + 5 minutes
at> /usr/local/bin/backup.sh
at> <EOT>    # Ctrl+D

# Schedule at specific time
at 2:00 AM
at 2:00 AM tomorrow
at 4 PM + 3 days
at noon
at teatime    # 4 PM
at 2024-12-31 23:59

# Schedule from file
at -f script.sh now + 1 hour

# Schedule from stdin
echo "/usr/local/bin/backup.sh" | at now + 5 minutes

# Schedule with queue
at -q b now + 5 minutes    # Queue b (a-z, a is default)

# List scheduled jobs
atq

# View job details
at -c 5    # Job number 5

# Remove job
atrm 5
atrm 5 10 15    # Remove multiple

# Restrict at access
# /etc/at.allow — only listed users can use at
# /etc/at.deny — listed users cannot use at
# If neither exists, all users can use at (on some distros)
```

### `batch` — Run When System Load Allows

```bash
# Schedule job to run when load average drops below 1.5
batch
at> /usr/local/bin/heavy-task.sh
at> <EOT>

# Or with at -b flag
at -b now
at> /usr/local/bin/heavy-task.sh
at> <EOT>

# batch checks /proc/loadavg before running
# Default threshold: 1.5 (configurable in /etc/atd.conf)
```

### at/batch Configuration

```bash
# /etc/at.deny — users who cannot use at
# /etc/at.allow — users who can use at (overrides deny)

# /etc/atd.conf (Debian/Ubuntu)
# LOAD=1.5    # Load threshold for batch
# BATCH_INTERVAL=60  # Seconds between batch checks

# at jobs run with the submitting user's environment
# Output is mailed to the user (like cron)
```

## Lock Files and Preventing Overlaps

### Using `flock`

```bash
# In crontab
*/5 * * * * flock -n /tmp/myjob.lock /usr/local/bin/myjob.sh

# flock options
# -n: Non-blocking (fail if can't acquire)
# -w 60: Wait up to 60 seconds
# -E 0: Exit code 0 on timeout
# -x: Exclusive lock (default)
# -s: Shared lock

# In script
#!/bin/bash
exec 200>/var/lock/myapp.lock
flock -n 200 || { echo "Already running"; exit 1; }

# ... main logic ...

# Lock is released when fd 200 is closed (script exits)
```

### Using `lockfile` (procmail)

```bash
# Create lock file (blocks until available)
lockfile /tmp/myjob.lock

# ... main logic ...

rm -f /tmp/myjob.lock

# Or with timeout
lockfile -l 300 /tmp/myjob.lock    # Wait 5 minutes max
```

### Using `mkdir` (atomic)

```bash
# mkdir is atomic on most filesystems
LOCK_DIR="/var/lock/myapp"
if mkdir "$LOCK_DIR" 2>/dev/null; then
    trap 'rm -rf "$LOCK_DIR"' EXIT
    # ... main logic ...
else
    echo "Already running" >&2
    exit 1
fi
```

## Monitoring Scheduled Jobs

### Checking cron Jobs

```bash
# View cron logs
grep CRON /var/log/syslog
journalctl -u cron

# Check if crond is running
systemctl status cron    # Debian/Ubuntu
systemctl status crond   # RHEL/CentOS

# View user crontabs
ls -la /var/spool/cron/crontabs/    # Debian/Ubuntu
ls -la /var/spool/cron/              # RHEL/CentOS

# List all crontabs
for user in $(cut -d: -f1 /etc/passwd); do
    crontab_content=$(sudo crontab -u "$user" -l 2>/dev/null)
    if [[ -n "$crontab_content" ]]; then
        echo "=== $user ==="
        echo "$crontab_content"
    fi
done
```

### Checking systemd Timers

```bash
# List all active timers
systemctl list-timers

# List all timers (including inactive)
systemctl list-timers --all

# Check specific timer
systemctl status myjob.timer

# View timer history
journalctl -u myjob.service --since "1 week ago"

# Check next run
systemctl show myjob.timer --property=NextElapseUSecRealtime

# Timer missed runs
systemctl show myjob.timer --property=LastTriggerUSec
```

## Best Practices

### Cron Job Best Practices

```bash
# 1. Always use absolute paths
30 2 * * * /usr/local/bin/backup.sh

# 2. Set PATH and SHELL
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# 3. Redirect output
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# 4. Use flock for non-overlap
*/5 * * * * flock -n /tmp/check.lock /usr/local/bin/check.sh

# 5. Use MAILTO for alerts
MAILTO=admin@example.com
30 2 * * * /usr/local/bin/backup.sh

# 6. Test with temporary cron
# Add test job that runs every minute
* * * * * /usr/local/bin/test.sh >> /tmp/test.log 2>&1
# Remove after testing!

# 7. Document jobs
# Backup database daily at 2:30 AM
30 2 * * * /usr/local/bin/backup.sh

# 8. Handle timezone
CRON_TZ=UTC
30 14 * * * /usr/local/bin/report.sh    # 2:30 PM UTC

# 9. Use flock to prevent overlap
*/5 * * * * flock -n /tmp/myjob.lock /usr/local/bin/myjob.sh

# 10. Log with timestamps
*/5 * * * * /usr/local/bin/check.sh 2>&1 | logger -t myjob
```

### systemd Timer Best Practices

```ini
# 1. Use Persistent=true for important jobs
[Timer]
Persistent=true

# 2. Add RandomizedDelaySec for multiple systems
RandomizedDelaySec=30m

# 3. Use security hardening
[Service]
Type=oneshot
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true

# 4. Set resource limits
[Service]
MemoryMax=1G
CPUQuota=50%

# 5. Use proper logging
[Service]
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myjob

# 6. Handle failures
[Service]
ExecStartPre=/usr/local/bin/precheck.sh
ExecStart=/usr/local/bin/myjob.sh
ExecStartPost=/usr/local/bin/postcheck.sh

# 7. Set timeout
[Service]
TimeoutStartSec=3600
```

## Migration: Cron to systemd Timers

```bash
# Step 1: Create service unit
# /etc/systemd/system/backup.service
[Unit]
Description=Daily backup

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup.sh
User=backup
StandardOutput=journal
StandardError=journal

# Step 2: Create timer unit
# /etc/systemd/system/backup.timer
[Unit]
Description=Run daily backup

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=900

[Install]
WantedBy=timers.target

# Step 3: Enable timer
systemctl daemon-reload
systemctl enable --now backup.timer

# Step 4: Remove cron entry
crontab -e    # Remove the old line

# Step 5: Verify
systemctl list-timers backup.timer
journalctl -u backup.service
```

## Cross-References

- [systemd](systemd.md) — systemd unit files and service management
- [Shell Scripting Fundamentals](../shell/scripting-fundamentals.md) — Writing scripts for scheduled jobs
- [Users and Groups](users-groups.md) — Per-user scheduling permissions

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [crontab(5) Man Page](https://man7.org/linux/man-pages/man5/crontab.5.html) — Crontab syntax reference
- [systemd.timer(5) Man Page](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) — Timer unit reference
- [at(1) Man Page](https://man7.org/linux/man-pages/man1/at.1.html) — at command reference
- [Crontab Guru](https://crontab.guru/) — Online crontab expression editor
- [Arch Wiki: Cron](https://wiki.archlinux.org/title/Cron) — Cron documentation
- [systemd Timers for Cron Users](https://opensource.com/article/20/7/systemd-timers) — Migration guide
