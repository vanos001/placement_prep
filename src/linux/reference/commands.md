# Commands Reference

A comprehensive reference of 100+ essential Linux commands organized by category.
Each entry includes the command name, brief description, and common flags/options.
Cross-references link to related man pages, glossary entries, and other chapters.

See also: [Man Pages](man-pages.md) for full documentation on each command.

---

## Introduction

Linux provides thousands of commands. This reference covers the most essential ones
every system administrator and developer should know. Commands are organized by category
for quick lookup. Each entry shows:

- **Command** — the executable name
- **Description** — what it does
- **Common flags** — most frequently used options
- **Example** — typical usage

```bash
# Check where a command lives
which ls
# /usr/bin/ls

# Check if a command is built-in or external
type cd
# cd is a shell builtin

type ls
# ls is aliased to 'ls --color=auto'
# ls is /usr/bin/ls
```

---

## File Operations

### ls — List Directory Contents

```bash
ls [OPTION]... [FILE]...

ls -l          # Long format (permissions, owner, size, date)
ls -a          # Show hidden files (dotfiles)
ls -la         # Long format + hidden files
ls -lh         # Human-readable sizes (K, M, G)
ls -lt         # Sort by modification time (newest first)
ls -ltr        # Sort by time, reversed (oldest first)
ls -R          # Recursive listing
ls -d */       # List only directories
ls -1          # One entry per line
ls --color=auto # Colorized output
```

### cp — Copy Files and Directories

```bash
cp [OPTION]... SOURCE DEST

cp file.txt backup.txt         # Copy file
cp -r dir1/ dir2/              # Copy directory recursively
cp -a dir1/ dir2/              # Archive (preserve all attributes)
cp -p file.txt backup.txt      # Preserve permissions and timestamps
cp -u src.txt dst.txt          # Copy only if source is newer
cp -i file.txt existing.txt    # Interactive (prompt before overwrite)
cp -v file.txt backup.txt      # Verbose output
cp --sparse=always big.img copy.img  # Handle sparse files
```

### mv — Move / Rename Files

```bash
mv [OPTION]... SOURCE DEST

mv old.txt new.txt             # Rename file
mv file.txt /other/dir/        # Move to directory
mv -i file.txt existing.txt    # Interactive (prompt before overwrite)
mv -n file.txt existing.txt    # No overwrite (no-clobber)
mv -v file.txt /tmp/           # Verbose output
mv -b file.txt existing.txt    # Create backup of overwritten file
```

### rm — Remove Files

```bash
rm [OPTION]... FILE...

rm file.txt                    # Remove file
rm -r directory/               # Remove directory recursively
rm -f file.txt                 # Force (no prompt for write-protected)
rm -rf directory/              # Force recursive (dangerous!)
rm -i file.txt                 # Interactive (prompt for each file)
rm -I file1 file2 ...          # Prompt once before removing >3 files
```

> ⚠️ **Warning:** `rm -rf /` will destroy your system. Always double-check paths.

### mkdir — Create Directories

```bash
mkdir [OPTION]... DIRECTORY...

mkdir dirname                  # Create directory
mkdir -p path/to/nested/dir   # Create parent directories as needed
mkdir -m 755 dirname          # Set permissions
mkdir -v dirname               # Verbose
```

### rmdir — Remove Empty Directories

```bash
rmdir dirname                  # Remove empty directory
rmdir -p path/to/nested/dir   # Remove parent directories if empty
```

### touch — Create Empty File / Update Timestamp

```bash
touch file.txt                 # Create empty file or update timestamp
touch -t 202601010000 file    # Set specific timestamp
touch -r ref.txt file.txt     # Copy timestamp from reference file
```

### ln — Create Links

```bash
ln file.txt hardlink.txt       # Create hard link
ln -s target symlink           # Create symbolic link
ln -sf new_target symlink     # Force overwrite existing symlink
```

### find — Search for Files

```bash
find [PATH] [EXPRESSION]

find / -name "*.conf"          # Find files by name
find . -type f -size +100M    # Files larger than 100MB
find . -mtime -7               # Modified in last 7 days
find . -user john              # Owned by user john
find . -perm 777               # With exact permissions
find . -name "*.log" -delete  # Find and delete
find . -exec grep -l "TODO" {} \;  # Execute command on each result
find . -type f | wc -l        # Count all files
```

### stat — Display File Status

```bash
stat file.txt                  # Show detailed file information
stat -c "%a %U %G" file.txt   # Custom format (perms, owner, group)
stat -f /                      # Show filesystem status
```

### file — Determine File Type

```bash
file document.pdf              # Identify file type
file -b file.txt               # Brief (no filename)
file -i file.txt               # MIME type
file *.png                     # Check multiple files
```

### du — Disk Usage

```bash
du -sh /var/log                # Summary, human-readable
du -sh *                       # Size of each item in current dir
du -sh --max-depth=1 /        # One level deep
du -sh --exclude='*.log' .    # Exclude pattern
du -sh . | sort -rh | head    # Largest directories first
```

### df — Disk Free Space

```bash
df -h                          # Human-readable disk usage
df -hT                         # Include filesystem type
df -i                          # Show inode usage
df -h /home                    # Specific filesystem
```

### tree — Directory Structure

```bash
tree                           # Show directory tree
tree -L 2                      # Limit depth to 2 levels
tree -d                        # Directories only
tree -a                        # Include hidden files
tree -I "node_modules|.git"   # Exclude patterns
```

### shred — Secure File Deletion

```bash
shred -vfz -n 3 secret.txt   # Overwrite 3 times then zero, verbose
shred -vfz -u secret.txt     # Overwrite and delete
```

---

## Text Processing

### grep — Search Text Patterns

```bash
grep [OPTIONS] PATTERN [FILE...]

grep "error" /var/log/syslog         # Search for pattern
grep -r "TODO" src/                  # Recursive search
grep -i "error" log.txt              # Case-insensitive
grep -v "debug" log.txt              # Invert match (exclude)
grep -n "error" log.txt              # Show line numbers
grep -c "error" log.txt              # Count matches
grep -l "error" *.log                # Show only filenames
grep -w "error" log.txt              # Whole word match
grep -E "err|warn" log.txt           # Extended regex (egrep)
grep -A 3 -B 1 "error" log.txt      # Context: 3 after, 1 before
grep --color=auto "error" log.txt   # Highlight matches
```

### sed — Stream Editor

```bash
sed [OPTIONS] 'COMMAND' [FILE...]

sed 's/old/new/' file.txt            # Replace first occurrence per line
sed 's/old/new/g' file.txt           # Replace all occurrences
sed -i 's/old/new/g' file.txt        # In-place edit
sed -i.bak 's/old/new/g' file.txt   # In-place with backup
sed -n '5,10p' file.txt              # Print lines 5-10
sed '3d' file.txt                     # Delete line 3
sed '/pattern/d' file.txt            # Delete matching lines
sed '1i\Header line' file.txt        # Insert before line 1
sed '$a\Footer line' file.txt        # Append after last line
```

### awk — Pattern Processing

```bash
awk 'pattern {action}' file

awk '{print $1, $3}' file.txt        # Print columns 1 and 3
awk -F: '{print $1}' /etc/passwd     # Custom delimiter
awk '{sum += $1} END {print sum}'    # Sum column
awk 'NR >= 5 && NR <= 10' file.txt  # Print lines 5-10
awk '/pattern/ {print}' file.txt     # Pattern matching
awk '{print NR, $0}' file.txt        # Add line numbers
awk '{total += NF} END {print total}' file.txt  # Count total words
```

### sort — Sort Lines

```bash
sort file.txt                        # Alphabetical sort
sort -n file.txt                     # Numeric sort
sort -r file.txt                     # Reverse sort
sort -u file.txt                     # Unique (remove duplicates)
sort -k2 -t: file.txt               # Sort by field 2, delimiter :
sort -h file.txt                     # Human-numeric sort (K, M, G)
sort -R file.txt                     # Random sort
```

### uniq — Filter Duplicate Lines

```bash
uniq file.txt                        # Remove adjacent duplicates
sort file.txt | uniq                 # Remove all duplicates
sort file.txt | uniq -c              # Count occurrences
sort file.txt | uniq -d              # Only show duplicates
sort file.txt | uniq -u              # Only show unique lines
```

### cut — Extract Columns

```bash
cut -d: -f1 /etc/passwd              # First field, colon-delimited
cut -c1-10 file.txt                  # Characters 1-10
cut -d' ' -f2,4 file.txt            # Fields 2 and 4
```

### tr — Translate / Delete Characters

```bash
tr 'a-z' 'A-Z' < file.txt          # Lowercase to uppercase
tr -d '\r' < file.txt               # Delete carriage returns
tr -s ' ' < file.txt                # Squeeze repeated spaces
tr ':' '\n' < file.txt              # Replace colons with newlines
```

### wc — Word Count

```bash
wc file.txt                          # Lines, words, bytes
wc -l file.txt                       # Line count
wc -w file.txt                       # Word count
wc -c file.txt                       # Byte count
wc -m file.txt                       # Character count
```

### diff — Compare Files

```bash
diff file1.txt file2.txt             # Show differences
diff -u file1.txt file2.txt         # Unified format (patch-style)
diff -r dir1/ dir2/                  # Recursive directory comparison
diff -y file1.txt file2.txt         # Side-by-side comparison
```

### head / tail — View Beginning / End

```bash
head -n 20 file.txt                  # First 20 lines
head -c 100 file.txt                 # First 100 bytes
tail -n 20 file.txt                  # Last 20 lines
tail -f /var/log/syslog              # Follow (live update)
tail -f -n 0 /var/log/syslog        # Follow from end (no history)
tail -F /var/log/syslog              # Follow with retry (handles rotation)
```

### less / more — Pager

```bash
less file.txt                        # View with scrolling
less +F /var/log/syslog              # Follow mode (like tail -f)
less -N file.txt                     # Show line numbers
less -S file.txt                     # No line wrapping
```

---

## Process Management

### ps — Process Status

```bash
ps aux                               # All processes, BSD format
ps -ef                               # All processes, UNIX format
ps -u username                       # User's processes
ps -p 1234                           # Specific PID
ps aux --sort=-%mem                  # Sort by memory usage
ps aux --sort=-%cpu                  # Sort by CPU usage
ps -eo pid,ppid,cmd,%mem,%cpu       # Custom columns
ps -ejH                              # Process tree
```

### top — Real-Time Process Monitor

```bash
top                                   # Interactive process viewer
# Keys: M (sort by memory), P (sort by CPU), k (kill), q (quit)
# 1 (show per-CPU), c (show full command)

top -b -n 1                          # Batch mode, one iteration
top -u username                      # Filter by user
```

### htop — Enhanced Process Viewer

```bash
htop                                  # Interactive process viewer
htop -u username                     # Filter by user
htop -p 1234,5678                    # Monitor specific PIDs
```

### kill — Send Signals

```bash
kill 1234                            # Send SIGTERM (default)
kill -9 1234                         # Send SIGKILL (force kill)
kill -HUP 1234                       # Send SIGHUP (reload config)
kill -USR1 1234                      # Send SIGUSR1 (custom signal)
kill -0 1234                         # Check if process exists
killall httpd                        # Kill by process name
pkill -f "pattern"                   # Kill by command pattern
```

### bg / fg / jobs — Job Control

```bash
command &                            # Run in background
Ctrl+Z                               # Suspend current process
bg %1                                # Resume job 1 in background
fg %1                                # Bring job 1 to foreground
jobs                                 # List background jobs
nohup command &                      # Survive terminal close
disown %1                            # Detach job from shell
```

### nice / renice — Process Priority

```bash
nice -n 10 command                   # Run with lower priority
nice -n -5 command                   # Run with higher priority (needs root)
renice 10 -p 1234                   # Change priority of running process
renice -5 -u username               # Change priority for user's processes
```

### pgrep — Find Process by Name

```bash
pgrep nginx                          # Get PIDs by name
pgrep -a nginx                       # Show full command
pgrep -u www-data                    # Filter by user
pgrep -f "pattern"                   # Match full command line
pgrep -c nginx                       # Count matching processes
```

### wait — Wait for Process

```bash
wait                                 # Wait for all background jobs
wait %1                              # Wait for job 1
wait 1234                            # Wait for PID 1234
```

---

## System Information

### uname — System Information

```bash
uname -a                             # All system information
uname -r                             # Kernel release
uname -m                             # Machine architecture
uname -n                             # Hostname
```

### hostname — Hostname

```bash
hostname                             # Show hostname
hostname -f                          # Fully qualified domain name
hostnamectl                          # Detailed hostname info (systemd)
hostnamectl set-hostname newname     # Set hostname
```

### uptime — System Uptime

```bash
uptime                               # Show uptime and load averages
uptime -p                            # Pretty format
uptime -s                            # Since (boot time)
```

### date — Date and Time

```bash
date                                 # Current date and time
date '+%Y-%m-%d %H:%M:%S'          # Custom format
date -u                              # UTC time
date -d '2026-01-01' '+%s'         # Convert to Unix timestamp
date -d @1735689600                  # Convert from timestamp
timedatectl                          # Timezone info (systemd)
```

### whoami / id — User Information

```bash
whoami                               # Current username
id                                   # UID, GID, groups
id username                          # Info for specific user
groups                               # Current user's groups
groups username                      # Specific user's groups
```

### free — Memory Usage

```bash
free -h                              # Human-readable memory info
free -m                              # In megabytes
free -g                              # In gigabytes
free -h -s 5                         # Refresh every 5 seconds
```

### lscpu — CPU Information

```bash
lscpu                                # CPU architecture info
lscpu -e                             # Extended per-CPU info
lscpu | grep "Model name"           # CPU model
```

### lsblk — Block Devices

```bash
lsblk                                # List block devices
lsblk -f                             # Include filesystem info
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT  # Custom columns
lsblk -d                             # Disks only (no partitions)
```

### lspci / lsusb — Hardware

```bash
lspci                                # List PCI devices
lspci -v                             # Verbose
lspci -nn                            # Include vendor/device IDs
lsusb                                # List USB devices
lsusb -v                             # Verbose
lshw                                 # Detailed hardware info
lshw -short                          # Brief hardware info
```

---

## Networking

### ip — Network Configuration (iproute2)

```bash
ip addr show                         # Show IP addresses
ip addr add 192.168.1.100/24 dev eth0  # Add IP
ip addr del 192.168.1.100/24 dev eth0  # Remove IP
ip link show                         # Show interfaces
ip link set eth0 up                  # Enable interface
ip link set eth0 down                # Disable interface
ip route show                        # Show routing table
ip route add 10.0.0.0/8 via 192.168.1.1  # Add route
ip route del 10.0.0.0/8             # Delete route
ip neigh show                        # ARP table
ip -s link show eth0                 # Interface statistics
ip -br addr show                     # Brief address output
```

### ss — Socket Statistics

```bash
ss -tlnp                             # TCP listening sockets with process
ss -ulnp                             # UDP listening sockets
ss -s                                # Summary statistics
ss -t state established              # Established connections
ss dst 192.168.1.0/24               # Filter by destination
ss -i                                # Show TCP internal info
```

### ping — Network Connectivity

```bash
ping google.com                      # Send ICMP echo requests
ping -c 5 google.com                 # Send 5 packets
ping -i 0.2 google.com              # 200ms interval
ping -s 1400 google.com             # Packet size
ping -W 2 google.com                # 2 second timeout
ping6 ::1                            # IPv6 ping
```

### curl — Transfer Data

```bash
curl https://example.com             # GET request
curl -o file.zip https://example.com/file.zip  # Download to file
curl -O https://example.com/file.zip # Download with original filename
curl -X POST -d 'key=value' URL     # POST request
curl -H "Content-Type: application/json" -d '{}' URL  # JSON POST
curl -L URL                          # Follow redirects
curl -k URL                          # Skip TLS verification
curl -v URL                          # Verbose output
curl -s URL                          # Silent (no progress)
curl -I URL                          # Headers only (HEAD request)
```

### wget — Download Files

```bash
wget URL                             # Download file
wget -c URL                          # Continue partial download
wget -r URL                          # Recursive download
wget -q URL                          # Quiet mode
wget -O filename URL                 # Save as filename
wget --limit-rate=1m URL            # Limit bandwidth
```

### ssh — Secure Shell

```bash
ssh user@host                        # Connect to remote host
ssh -p 2222 user@host               # Custom port
ssh -i ~/.ssh/key.pem user@host     # Use specific key
ssh -L 8080:localhost:80 user@host  # Local port forwarding
ssh -R 9090:localhost:9090 user@host # Remote port forwarding
ssh -D 1080 user@host               # SOCKS proxy
ssh -N -L 8080:localhost:80 user@host # Forward only, no shell
```

### scp / rsync — File Transfer

```bash
scp file.txt user@host:/path/        # Copy to remote
scp user@host:/path/file.txt .       # Copy from remote
scp -r dir/ user@host:/path/         # Copy directory recursively
scp -P 2222 file.txt user@host:/path/ # Custom port

rsync -avz src/ user@host:/dest/     # Sync with compression
rsync -avz --delete src/ dst/        # Mirror (delete extra files)
rsync -avz --exclude='*.log' src/ dst/ # Exclude pattern
rsync -avz --progress src/ dst/      # Show progress
rsync -e "ssh -p 2222" src/ user@host:/dest/ # Custom SSH port
```

### dig / nslookup — DNS Lookup

```bash
dig google.com                       # Full DNS lookup
dig +short google.com                # IP only
dig MX google.com                    # Mail records
dig @8.8.8.8 google.com            # Use specific DNS server
dig -x 142.250.80.46                # Reverse lookup

nslookup google.com                  # Simple DNS lookup
nslookup -type=MX google.com       # Mail records
```

### traceroute — Trace Network Path

```bash
traceroute google.com                # Trace route
traceroute -n google.com            # Skip DNS resolution
traceroute -I google.com            # Use ICMP
traceroute -T -p 80 google.com     # Use TCP port 80
```

### nmap — Network Scanner

```bash
nmap 192.168.1.0/24                 # Scan subnet
nmap -sT -p 80,443 192.168.1.1     # TCP connect scan specific ports
nmap -sV 192.168.1.1               # Service version detection
nmap -sn 192.168.1.0/24            # Ping scan (host discovery)
nmap -O 192.168.1.1                # OS detection
```

### tcpdump — Packet Capture

```bash
tcpdump -i eth0                      # Capture on interface
tcpdump -i any port 80              # HTTP traffic on all interfaces
tcpdump host 192.168.1.1            # Traffic to/from host
tcpdump -nn -i eth0                 # Don't resolve addresses
tcpdump -w capture.pcap             # Write to file
tcpdump -r capture.pcap             # Read from file
tcpdump -c 100 -i eth0             # Capture 100 packets
tcpdump -A 'port 80'               # ASCII output
```

### nc (netcat) — Network Swiss Army Knife

```bash
nc -zv host 80                       # Test port connectivity
nc -l 8080                           # Listen on port 8080
nc host 80 < request.txt            # Send HTTP request
nc -zv host 20-100                  # Port range scan
```

---

## Disk and Storage

### fdisk — Partition Manager

```bash
fdisk -l                             # List all partitions
fdisk /dev/sda                       # Interactive partition editor
# Commands: n (new), d (delete), p (print), w (write), q (quit)
```

### parted — Advanced Partition Manager

```bash
parted /dev/sda                      # Interactive mode
parted /dev/sda print               # Show partition table
parted /dev/sda mkpart primary ext4 0% 100%  # Create partition
```

### mkfs — Create Filesystem

```bash
mkfs.ext4 /dev/sda1                 # Create ext4 filesystem
mkfs.xfs /dev/sda1                  # Create XFS filesystem
mkfs.vfat -F 32 /dev/sda1          # Create FAT32 filesystem
mkfs.btrfs /dev/sda1               # Create Btrfs filesystem
```

### mount / umount — Mount/Unmount

```bash
mount /dev/sda1 /mnt                # Mount device
mount -t nfs server:/share /mnt    # Mount NFS share
mount -o ro /dev/sda1 /mnt         # Mount read-only
mount --bind /src /dst             # Bind mount
mount -a                            # Mount all from fstab
umount /mnt                         # Unmount
umount -l /mnt                      # Lazy unmount
umount -f /mnt                      # Force unmount
```

### fsck — Filesystem Check

```bash
fsck /dev/sda1                       # Check filesystem
fsck -y /dev/sda1                    # Auto-repair
fsck.ext4 -f /dev/sda1             # Force ext4 check
fsck -N /dev/sda1                   # Dry run (show what would be done)
```

### blkid — Block Device Attributes

```bash
blkid                                # Show all block device UUIDs and types
blkid /dev/sda1                     # Specific device
```

### dd — Data Duplication

```bash
dd if=/dev/zero of=file.img bs=1M count=100  # Create 100MB file
dd if=/dev/sda of=disk.img bs=4M status=progress  # Disk image
dd if=image.iso of=/dev/sdb bs=4M status=progress  # Write ISO to USB
dd if=/dev/urandom of=file bs=1M count=10  # Random data file
```

> ⚠️ **Warning:** `dd` can destroy data if `if` and `of` are swapped. Always double-check.

### LVM Commands

```bash
pvcreate /dev/sdb                    # Create physical volume
vgcreate vg0 /dev/sdb               # Create volume group
lvcreate -L 10G -n lv_data vg0     # Create logical volume
lvextend -L +5G /dev/vg0/lv_data   # Extend logical volume
resize2fs /dev/vg0/lv_data          # Resize ext4 filesystem
lvdisplay                            # Show logical volumes
vgdisplay                            # Show volume groups
pvdisplay                            # Show physical volumes
```

---

## Package Management

### APT (Debian/Ubuntu)

```bash
apt update                           # Update package lists
apt upgrade                          # Upgrade all packages
apt install package                  # Install package
apt remove package                   # Remove package
apt autoremove                       # Remove unused dependencies
apt search keyword                   # Search for packages
apt show package                     # Show package info
apt list --installed                 # List installed packages
apt list --upgradable               # List upgradable packages
dpkg -l                              # List all installed (dpkg)
dpkg -L package                      # Files installed by package
dpkg -S /path/to/file               # Which package owns file
```

### DNF/YUM (RHEL/Fedora)

```bash
dnf update                           # Update all packages
dnf install package                  # Install package
dnf remove package                   # Remove package
dnf search keyword                   # Search packages
dnf info package                     # Package info
dnf list installed                   # Installed packages
dnf provides /path/to/file          # Which package provides file
yum history                          # Transaction history
```

### Pacman (Arch)

```bash
pacman -Syu                          # Update system
pacman -S package                    # Install package
pacman -R package                    # Remove package
pacman -Ss keyword                   # Search packages
pacman -Qs keyword                   # Search installed
pacman -Ql package                   # List package files
pacman -Qo /path/to/file            # Which package owns file
```

---

## User and Permission Management

### User Commands

```bash
useradd -m -s /bin/bash username    # Create user with home dir
usermod -aG sudo username           # Add user to group
userdel -r username                  # Delete user and home dir
passwd username                      # Change user password
chage -l username                    # Show password expiry info
chage -M 90 username                # Set max password age
```

### Group Commands

```bash
groupadd groupname                   # Create group
groupdel groupname                   # Delete group
gpasswd -a username groupname       # Add user to group
gpasswd -d username groupname       # Remove user from group
```

### Permission Commands

```bash
chmod 755 file                       # Set permissions (octal)
chmod u+x file                       # Add execute for owner
chmod go-w file                      # Remove write for group/others
chmod -R 644 directory/              # Recursive permissions
chown user:group file                # Change ownership
chown -R user:group directory/       # Recursive ownership
chgrp groupname file                 # Change group
umask 022                            # Set default permissions mask
```

### sudo — Superuser Do

```bash
sudo command                         # Run as root
sudo -u username command             # Run as specific user
sudo -i                              # Root login shell
sudo -s                              # Root shell
sudo visudo                          # Edit sudoers file safely
sudo -l                              # List allowed commands
sudo !!                              # Re-run last command with sudo
```

---

## Service Management (systemd)

### systemctl — Service Control

```bash
systemctl start service              # Start service
systemctl stop service               # Stop service
systemctl restart service            # Restart service
systemctl reload service             # Reload config
systemctl status service             # Show status
systemctl enable service             # Enable at boot
systemctl disable service            # Disable at boot
systemctl is-active service          # Check if running
systemctl is-enabled service         # Check if enabled
systemctl list-units --type=service  # List all services
systemctl list-units --failed        # Show failed services
systemctl daemon-reload              # Reload systemd config
systemctl mask service               # Completely disable service
systemctl unmask service             # Re-enable masked service
```

### journalctl — View Logs

```bash
journalctl                            # All journal entries
journalctl -u service                # Service logs
journalctl -f                        # Follow (like tail -f)
journalctl --since "2026-01-01"     # Since date
journalctl --since "1 hour ago"     # Relative time
journalctl -p err                    # Only errors
journalctl -b                        # Current boot
journalctl -b -1                     # Previous boot
journalctl --disk-usage              # Journal size
journalctl --vacuum-size=500M       # Clean up journal
```

---

## Compression and Archives

### tar — Tape Archive

```bash
tar -czf archive.tar.gz directory/   # Create gzip archive
tar -cjf archive.tar.bz2 directory/  # Create bzip2 archive
tar -cJf archive.tar.xz directory/   # Create xz archive
tar -xzf archive.tar.gz              # Extract gzip archive
tar -xzf archive.tar.gz -C /dest/   # Extract to directory
tar -tzf archive.tar.gz              # List archive contents
tar -xzf archive.tar.gz --strip-components=1  # Strip leading directory
```

### gzip / bzip2 / xz

```bash
gzip file.txt                        # Compress (creates file.txt.gz)
gzip -d file.txt.gz                  # Decompress
gzip -9 file.txt                     # Maximum compression
gunzip file.txt.gz                   # Decompress (same as gzip -d)

bzip2 file.txt                       # Compress with bzip2
bunzip2 file.txt.bz2                # Decompress

xz file.txt                          # Compress with xz
unxz file.txt.xz                    # Decompress
xz -9 file.txt                       # Maximum compression
```

### zip / unzip

```bash
zip -r archive.zip directory/        # Create zip archive
zip -e archive.zip file.txt         # Password-protected
unzip archive.zip                    # Extract
unzip -l archive.zip                 # List contents
unzip archive.zip -d /dest/         # Extract to directory
```

### zstd — Zstandard

```bash
zstd file.txt                        # Compress
zstd -d file.txt.zst                # Decompress
zstd -19 file.txt                    # High compression
unzstd file.txt.zst                 # Decompress (alias)
```

---

## Miscellaneous

### echo / printf — Output

```bash
echo "Hello World"                   # Print text
echo -e "Line1\nLine2"             # Enable escape sequences
echo $PATH                           # Print variable
printf "%-20s %s\n" "Name" "Value" # Formatted output
```

### xargs — Build Command Lines

```bash
find . -name "*.tmp" | xargs rm     # Delete found files
find . -name "*.c" | xargs wc -l   # Count lines in C files
echo "a b c" | xargs -n 1          # One argument per line
cat urls.txt | xargs -I {} curl -O {} # Process each line
find . -name "*.log" -print0 | xargs -0 rm  # Handle spaces in filenames
```

### watch — Run Command Periodically

```bash
watch -n 2 df -h                     # Refresh every 2 seconds
watch -d free -h                     # Highlight changes
watch -n 1 'date; uptime'           # Multiple commands
```

### env / export — Environment

```bash
env                                  # Show all environment variables
export VAR=value                     # Set and export variable
export -n VAR                        # Unexport variable
unset VAR                            # Remove variable
printenv PATH                        # Print specific variable
```

### alias — Command Aliases

```bash
alias ll='ls -la'                    # Create alias
alias                                # List all aliases
unalias ll                           # Remove alias
```

### history — Command History

```bash
history                              # Show command history
history 20                           # Last 20 commands
!!                                   # Re-run last command
!grep                                # Re-run last command starting with grep
Ctrl+R                               # Reverse incremental search
history -c                           # Clear history
```

### crontab — Scheduled Tasks

```bash
crontab -l                           # List cron jobs
crontab -e                           # Edit cron jobs
crontab -r                           # Remove all cron jobs
crontab -u username -l              # List another user's jobs
```

### time — Measure Execution Time

```bash
time command                         # Measure execution time
time -p command                      # POSIX format
/usr/bin/time -v command             # Detailed resource usage
```

### tee — Read and Write

```bash
command | tee output.txt             # Display and save
command | tee -a output.txt         # Append mode
command | tee file1 file2           # Write to multiple files
```

### yes — Repeat String

```bash
yes | command                        # Auto-answer yes
yes "text" | head -100              # Generate repeated text
```

### strings — Extract Printable Strings

```bash
strings binary_file                  # Extract ASCII strings
strings -n 8 binary_file            # Minimum length 8
```

### strace / ltrace — Trace Calls

```bash
strace -f command                    # Trace system calls
strace -p PID                       # Attach to running process
strace -e trace=open,read command   # Filter specific syscalls
strace -c command                   # Summary statistics

ltrace command                       # Trace library calls
ltrace -p PID                       # Attach to running process
```

### ldd — Shared Library Dependencies

```bash
ldd /usr/bin/ls                      # Show shared libraries
ldd -v /usr/bin/ls                  # Verbose (version info)
```

### ldconfig — Library Cache

```bash
ldconfig                             # Update library cache
ldconfig -p                          # Print current cache
ldconfig -n /path/to/libs          # Add directory to cache
```

### update-alternatives — Default Commands

```bash
update-alternatives --list java      # List alternatives
update-alternatives --config java   # Choose default
update-alternatives --install /usr/bin/editor editor /usr/bin/vim 100  # Add
```

---

## Cross-References

- [Man Pages](man-pages.md) — Full documentation for every command
- [Glossary](glossary.md) — Definitions of technical terms
- [Kernel Config](kernel-config.md) — Kernel options affecting command behavior
- [Syscall Table](syscall-table.md) — System calls behind these commands
- [Further Reading](further-reading.md) — Learning resources

---

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [GNU Coreutils Manual](https://www.gnu.org/software/coreutils/manual/)
- [Linux Command Library](https://linuxcommandlibrary.com/)
- [Explainshell](https://explainshell.com/) — Paste a command, get an explanation
- [tldr pages](https://tldr.sh/) — Simplified man pages
- [Commandlinefu](https://www.commandlinefu.com/) — Community-driven command examples
- [The Linux Documentation Project](https://tldp.org/)
