# Linux Cheatsheet

## 📁 File System Navigation

```bash
pwd                         # Print working directory
ls                          # List files
ls -la                      # List all with details
ls -lh                      # Human-readable sizes
cd /path                    # Change directory
cd ~                        # Home directory
cd -                        # Previous directory
cd ..                       # Parent directory
```

## 📄 File Operations

```bash
touch file.txt              # Create empty file
mkdir dir                   # Create directory
mkdir -p dir/sub/dir        # Create nested directories
cp file1 file2              # Copy file
cp -r dir1 dir2             # Copy directory
mv file1 file2              # Move/rename
rm file                     # Remove file
rm -r dir                   # Remove directory
rm -rf dir                  # Force remove (dangerous!)
ln -s target link           # Create symbolic link
```

## 📖 Reading Files

```bash
cat file.txt                # Print entire file
less file.txt               # View with pagination
head -n 20 file.txt         # First 20 lines
tail -n 20 file.txt         # Last 20 lines
tail -f file.txt            # Follow file (live updates)
wc -l file.txt              # Count lines
wc -w file.txt              # Count words
file file.txt               # Identify file type
```

## 🔍 Searching

```bash
grep "pattern" file         # Search in file
grep -r "pattern" dir       # Recursive search
grep -i "pattern" file      # Case insensitive
grep -n "pattern" file      # Show line numbers
grep -c "pattern" file      # Count matches
grep -v "pattern" file      # Invert (exclude pattern)
grep -E "regex" file        # Extended regex

find . -name "*.txt"        # Find by name
find . -type f -size +1M    # Files larger than 1MB
find . -mtime -7            # Modified in last 7 days
find . -exec grep "pattern" {} \;  # Execute command

which python                # Find command location
whereis python              # Find binary, source, man
locate file.txt             # Quick find (updatedb)
```

## ✏️ Text Processing

```bash
sort file.txt               # Sort lines
sort -n file.txt            # Numeric sort
sort -r file.txt            # Reverse sort
sort -u file.txt            # Unique (remove duplicates)
uniq file.txt               # Remove adjacent duplicates
cut -d',' -f1 file.csv      # Extract column 1 (CSV)
awk '{print $1}' file       # Print first field
sed 's/old/new/g' file      # Replace text
tr 'a-z' 'A-Z' < file      # Convert to uppercase
```

## 📊 Process Management

```bash
ps aux                      # All processes
ps aux | grep python        # Find specific process
top                         # Real-time process viewer
htop                        # Better process viewer
kill PID                    # Send SIGTERM
kill -9 PID                 # Send SIGKILL (force)
killall python              # Kill by name
bg                          # Resume in background
fg                          # Bring to foreground
jobs                        # List background jobs
nohup command &             # Run immune to hangups
```

## 💾 Disk Usage

```bash
df -h                       # Disk space usage
du -sh dir                  # Directory size
du -h --max-depth=1         # Size of subdirectories
du -sh * | sort -rh | head  # Largest files/dirs
```

## 🌐 Networking

```bash
ping google.com             # Test connectivity
curl url                    # HTTP request
curl -I url                 # Headers only
wget url                    # Download file
netstat -tuln               # Open ports
ss -tuln                    # Modern netstat
lsof -i :8080               # Process using port
ip addr                     # IP addresses
ifconfig                    # Network interfaces (legacy)
```

## 🔐 Permissions

```bash
chmod 755 file              # rwxr-xr-x
chmod u+x file              # Add execute for user
chmod go-w file             # Remove write for group/others
chown user:group file       # Change ownership
chown -R user:dir           # Recursive ownership

Permission bits:
  r (read) = 4
  w (write) = 2
  x (execute) = 1

  755 = rwxr-xr-x
  644 = rw-r--r--
  600 = rw-------
```

## 🔄 Redirection & Pipes

```bash
command > file              # Redirect stdout to file
command >> file             # Append stdout to file
command 2> error.log        # Redirect stderr
command > out.txt 2>&1      # Redirect both
command < input.txt         # Read from file
command1 | command2         # Pipe output to input
command1 && command2        # Run command2 if command1 succeeds
command1 || command2        # Run command2 if command1 fails
command ; command           # Run sequentially
```

## 📦 Package Management

```bash
# Ubuntu/Debian
apt update                  # Update package list
apt upgrade                 # Upgrade packages
apt install package         # Install package
apt remove package          # Remove package
apt search keyword          # Search packages

# CentOS/RHEL
yum update                  # Update packages
yum install package         # Install package
yum remove package          # Remove package
```

## 🐚 Shell Shortcuts

```
Ctrl+C                      # Cancel current command
Ctrl+D                      # Exit shell / EOF
Ctrl+Z                      # Suspend process
Ctrl+A                      # Move to beginning of line
Ctrl+E                      # Move to end of line
Ctrl+R                      # Reverse search history
Ctrl+L                      # Clear screen
Tab                         # Auto-complete
!!                          # Repeat last command
!$                          # Last argument of previous command
```

## 📝 Environment Variables

```bash
export VAR="value"          # Set variable
echo $VAR                   # Print variable
env                         # List all variables
unset VAR                   # Remove variable
PATH=$PATH:/new/path        # Add to PATH

# Permanent: add to ~/.bashrc or ~/.profile
```

## 🧰 Useful One-Liners

```bash
# Count lines in all .py files
find . -name "*.py" | xargs wc -l

# Find largest files
find . -type f -exec du -h {} + | sort -rh | head -20

# Replace in multiple files
sed -i 's/old/new/g' *.txt

# Monitor log file
tail -f /var/log/syslog | grep ERROR

# Disk usage by directory
du -sh */ | sort -rh | head -10

# Count occurrences of pattern
grep -c "pattern" *.log | sort -t: -k2 -rn

# Kill all processes matching pattern
ps aux | grep "pattern" | grep -v grep | awk '{print $2}' | xargs kill
```

## ⚡ Quick Reference

| Command | Description |
|---------|-------------|
| `grep -r "text" .` | Recursive search |
| `find . -name "*.log"` | Find files by name |
| `tail -f file` | Follow file changes |
| `ps aux` | All processes |
| `kill -9 PID` | Force kill |
| `chmod 755 file` | Set permissions |
| `du -sh *` | Directory sizes |
| `netstat -tuln` | Open ports |

## 🔗 Cross-References

- [Git Cheatsheet](./git.md) — Version control
- [OS Cheatsheet](./os.md) — OS concepts behind commands
- [OS Interview Questions](../interview/os-questions.md) — Process management details
