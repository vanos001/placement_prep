# Package Management

Package management is one of the defining features of Linux distributions. A package manager handles the installation, upgrade, configuration, and removal of software, managing dependencies and maintaining system consistency. This chapter covers the major package management systems: dpkg/apt (Debian/Ubuntu), rpm/dnf (RHEL/Fedora), pacman (Arch), and portage (Gentoo).

## Package Management Concepts

### What a Package Manager Does

```
┌─────────────────────────────────────────────────────────┐
│  Package Manager Responsibilities                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Package Installation                                │
│     ├── Download packages from repositories              │
│     ├── Verify integrity (GPG signatures)               │
│     ├── Extract and install files                       │
│     └── Run pre/post install scripts                    │
│                                                         │
│  2. Dependency Resolution                               │
│     ├── Calculate required packages                     │
│     ├── Resolve version conflicts                       │
│     └── Install/remove dependencies automatically       │
│                                                         │
│  3. System Tracking                                     │
│     ├── Maintain package database                       │
│     ├── Track installed files                           │
│     └── Record configuration changes                    │
│                                                         │
│  4. Upgrade Management                                  │
│     ├── Check for available updates                     │
│     ├── Handle configuration file changes               │
│     └── Support rollback (where available)              │
│                                                         │
│  5. Repository Management                               │
│     ├── Configure software sources                      │
│     ├── Handle GPG keys                                 │
│     └── Cache package metadata                          │
└─────────────────────────────────────────────────────────┘
```

### Package Types

```
┌─────────────────────────────────────────────────────┐
│  Package Formats by Distribution                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Distribution    │ Format  │ Manager  │ Tools       │
│  ────────────────┼─────────┼──────────┼───────────  │
│  Debian/Ubuntu   │ .deb    │ dpkg     │ apt, apt-   │
│                  │         │          │ get, apt-   │
│                  │         │          │ cache       │
│  RHEL/CentOS/Fed │ .rpm    │ rpm      │ dnf, yum   │
│  SUSE/openSUSE   │ .rpm    │ rpm      │ zypper     │
│  Arch Linux      │ .pkg.tar│ pacman   │ pacman     │
│  Gentoo          │ .tbz2   │ portage  │ emerge     │
│  Alpine          │ .apk    │ apk      │ apk        │
│  Void Linux      │ .xbps   │ xbps     │ xbps       │
│  NixOS           │ .nar    │ nix      │ nix-env    │
└─────────────────────────────────────────────────────┘
```

## dpkg and apt (Debian/Ubuntu)

### dpkg — Low-Level Package Manager

dpkg is the base package manager for Debian-based systems. It handles individual `.deb` files but does **not** resolve dependencies automatically.

```bash
# Install a local .deb file
sudo dpkg -i package.deb

# Install with dependency resolution (use apt instead)
sudo apt install -f    # Fix broken dependencies after dpkg -i

# Remove package (keep config)
sudo dpkg -r package

# Remove package and config
sudo dpkg -P package    # Purge

# List installed packages
dpkg -l
dpkg -l | grep nginx

# Show package info
dpkg -s package

# List files owned by package
dpkg -L package

# Find which package owns a file
dpkg -S /usr/bin/vim
dpkg -S $(which vim)

# Check if package is installed
dpkg -l package 2>/dev/null | grep -q "^ii" && echo "installed"

# Reconfigure package
sudo dpkg-reconfigure package

# Configure unpacked but unconfigured packages
sudo dpkg --configure -a

# Force overwrite (dangerous)
sudo dpkg -i --force-overwrite package.deb

# Architecture info
dpkg --print-architecture    # amd64
dpkg --print-foreign-architectures

# Add 32-bit support
sudo dpkg --add-architecture i386
sudo apt update
```

### apt — High-Level Package Manager

apt provides a user-friendly interface with automatic dependency resolution, repository management, and caching.

```bash
# Update package index
sudo apt update

# Upgrade all packages
sudo apt upgrade

# Full upgrade (handles dependency changes)
sudo apt full-upgrade

# Install package
sudo apt install package
sudo apt install package1 package2
sudo apt install package=1.2.3-1    # Specific version
sudo apt install package/jammy       # From specific release

# Remove package
sudo apt remove package

# Remove package and config
sudo apt purge package

# Remove unused dependencies
sudo apt autoremove
sudo apt autoremove --purge

# Search packages
apt search keyword
apt-cache search keyword

# Show package info
apt show package
apt-cache show package

# List all available versions
apt-cache policy package

# List files owned by package
apt-file list package      # Requires apt-file package
dpkg -L package

# Find which package provides a file
apt-file search /usr/bin/vim
apt-file search "*/nginx.conf"

# Update apt-file database
sudo apt-file update

# Download package without installing
apt download package

# Show package changelog
apt-get changelog package

# Mark package as manually installed
sudo apt-mark manual package

# Mark package as automatically installed
sudo apt-mark auto package

# Hold package at current version
sudo apt-mark hold package

# Unhold package
sudo apt-mark unhold package

# Show held packages
apt-mark showhold

# List all installed packages
apt list --installed
dpkg -l

# List upgradable packages
apt list --upgradable

# Simulate (dry run)
sudo apt install --simulate package
sudo apt upgrade --simulate
```

### apt Repository Configuration

```bash
# Modern sources format: /etc/apt/sources.list.d/*.sources
# /etc/apt/sources.list.d/ubuntu.sources
Types: deb
URIs: http://archive.ubuntu.com/ubuntu
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

# Traditional format: /etc/apt/sources.list
# deb http://archive.ubuntu.com/ubuntu noble main restricted
# deb http://archive.ubuntu.com/ubuntu noble-updates main restricted
# deb http://archive.ubuntu.com/ubuntu noble universe
# deb http://security.ubuntu.com/ubuntu noble-security main restricted

# Add a third-party repository
# 1. Add GPG key
curl -fsSL https://example.com/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/example.gpg

# 2. Add repository
echo "deb [signed-by=/usr/share/keyrings/example.gpg] https://repo.example.com/apt stable main" | \
    sudo tee /etc/apt/sources.list.d/example.list

# 3. Update and install
sudo apt update
sudo apt install example-package

# Using add-apt-repository (Ubuntu)
sudo add-apt-repository ppa:user/ppa-name
sudo apt update

# Using apt-add-repository (Debian)
sudo apt-add-repository 'deb https://repo.example.com/apt stable main'
```

### apt Preferences (Pinning)

```bash
# /etc/apt/preferences.d/pin-example
# Prefer packages from a specific repository
Package: *
Pin: origin repo.example.com
Pin-Priority: 900

# Hold a package at a specific version
Package: nginx
Pin: version 1.24.*
Pin-Priority: 1000

# Never install from a repository
Package: *
Pin: origin untrusted.example.com
Pin-Priority: 1

# Pin priority ranges:
# > 1000: Force version (even downgrade)
# 990-1000: Install unless already installed
# 500-989: Default priority (normal)
# 100-499: Only install if not available elsewhere
# < 100: Only installed if no other version exists
```

## rpm and dnf (RHEL/Fedora)

### rpm — Low-Level Package Manager

```bash
# Install package
sudo rpm -ivh package.rpm

# Upgrade package
sudo rpm -Uvh package.rpm

# Fresh install (fail if not already installed)
sudo rpm -Fvh package.rpm

# Remove package
sudo rpm -e package

# Query installed packages
rpm -qa                        # All installed packages
rpm -qa | grep nginx           # Search
rpm -q package                 # Check if installed
rpm -qi package                # Info
rpm -ql package                # List files
rpm -qf /usr/bin/vim           # Which package owns file
rpm -qc package                # Config files only
rpm -qd package                # Documentation files
rpm -qR package                # Dependencies
rpm -q --changelog package     # Changelog

# Query package file (not installed)
rpm -qip package.rpm
rpm -qlp package.rpm

# Verify package
rpm -V package                 # Verify against package database
rpm -Vp package.rpm            # Verify against RPM file

# Import GPG key
sudo rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-CentOS-Official

# Rebuild database
sudo rpm --rebuilddb

# Force install (dangerous)
sudo rpm -ivh --force package.rpm
sudo rpm -ivh --nodeps package.rpm    # Skip dependency check
```

### dnf — High-Level Package Manager

dnf is the successor to yum, providing better dependency resolution and performance.

```bash
# Install package
sudo dnf install package
sudo dnf install package1 package2

# Install specific version
sudo dnf install package-1.2.3

# Install from RPM URL
sudo dnf install https://example.com/package.rpm

# Remove package
sudo dnf remove package

# Update all packages
sudo dnf update

# Update specific package
sudo dnf update package

# Check for updates
sudo dnf check-update

# Search packages
dnf search keyword

# Show package info
dnf info package

# List installed packages
dnf list installed
dnf list installed | grep nginx

# List available packages
dnf list available

# List upgradable packages
dnf list upgrades

# Find which package provides a file
dnf provides /usr/bin/vim
dnf provides "*/nginx.conf"

# History
dnf history
dnf history info 5            # Transaction 5
dnf history undo 5            # Undo transaction 5
dnf history rollback 3        # Rollback to transaction 3

# Group operations
dnf group list
dnf group info "Development Tools"
sudo dnf group install "Development Tools"

# Module streams (RHEL 8+)
dnf module list
dnf module info nodejs
sudo dnf module enable nodejs:18
sudo dnf module install nodejs:18/common

# Clean cache
sudo dnf clean all
sudo dnf clean packages

# Download without install
dnf download package
dnf download --resolve package    # Include dependencies

# Reinstall
sudo dnf reinstall package

# Remove unused dependencies
sudo dnf autoremove

# Local install with dependency resolution
sudo dnf localinstall package.rpm
sudo dnf install ./package.rpm    # Modern syntax
```

### dnf Repository Configuration

```bash
# Repository files: /etc/yum.repos.d/*.repo

# Example: /etc/yum.repos.d/example.repo
[example]
name=Example Repository
baseurl=https://repo.example.com/centos/$releasever/$basearch/
        https://mirror.example.com/centos/$releasever/$basearch/
enabled=1
gpgcheck=1
gpgkey=https://repo.example.com/RPM-GPG-KEY-example
priority=90
cost=1000

# Variables:
# $releasever  → OS version (8, 9)
# $basearch    → Architecture (x86_64, aarch64)

# Add EPEL repository
sudo dnf install epel-release                    # RHEL/CentOS
sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm

# Enable PowerTools/CRB (for build dependencies)
sudo dnf config-manager --set-enabled crb        # RHEL 9
sudo dnf config-manager --set-enabled powertools # RHEL 8

# Add repository via dnf config-manager
sudo dnf config-manager --add-repo https://repo.example.com/example.repo

# Disable repository
sudo dnf config-manager --set-disabled example

# Enable repository
sudo dnf config-manager --set-enabled example
```

### dnf Automatic Updates

```bash
# Install dnf-automatic
sudo dnf install dnf-automatic

# Configure: /etc/dnf/automatic.conf
[commands]
upgrade_type = default
random_sleep = 0
download_updates = yes
apply_updates = yes

[emitters]
system_name = myserver
emit_via = stdio

[email]
email_from = root@example.com
email_to = admin@example.com
email_host = localhost

# Enable timer
sudo systemctl enable --now dnf-automatic.timer
```

## pacman (Arch Linux)

### Basic Operations

```bash
# Synchronize and update system
sudo pacman -Syu                    # Full system upgrade

# Update package database only
sudo pacman -Sy

# Install package
sudo pacman -S package
sudo pacman -S package1 package2

# Install specific version
sudo pacman -S "package>=1.2"

# Remove package
sudo pacman -R package
sudo pacman -Rns package            # Remove, cascade, save config

# Search packages
pacman -Ss keyword                   # Search repositories
pacman -Qs keyword                   # Search installed

# Show package info
pacman -Si package                   # Repository info
pacman -Qi package                   # Installed info

# List files owned by package
pacman -Ql package

# Find which package owns a file
pacman -Qo /usr/bin/vim

# List all installed packages
pacman -Q
pacman -Qe                           # Explicitly installed
pacman -Qd                           # Dependencies
pacman -Qm                           # Foreign (AUR)

# List orphaned packages
pacman -Qdt

# Remove orphans
sudo pacman -Rns $(pacman -Qdtq)

# Clean package cache
sudo pacman -Sc                      # Remove uninstalled
sudo pacman -Scc                     # Remove all cached

# Install from local file
sudo pacman -U package.pkg.tar.zst

# Force install
sudo pacman -S --force package

# Download without install
pacman -Sw package
```

### AUR (Arch User Repository)

```bash
# AUR helpers (install from AUR manually first)
# yay (most popular)
yay -S package                       # Search and install from AUR
yay -Syu                             # Update including AUR
yay -Ss keyword                      # Search AUR

# paru
paru -S package
paru -Syu

# Manual AUR install
git clone https://aur.archlinux.org/package.git
cd package
makepkg -si
```

## Portage (Gentoo)

### emerge — Package Manager

```bash
# Sync repository
sudo emerge --sync
sudo emaint -a sync

# Update system
sudo emerge --update --deep --newuse @world

# Install package
sudo emerge package
sudo emerge --ask package            # Ask before installing

# Remove package
sudo emerge --deselect package
sudo emerge --depclean               # Remove unused

# Search packages
emerge --search keyword
emerge --searchdesc keyword

# Show package info
emerge --info package
emerge -pv package                   # Pretend verbose

# Use flags
emerge -pv package                   # Show current USE flags
sudo USE="flag1 -flag2" emerge package    # One-time USE flags

# /etc/portage/package.use/myflags
# www-servers/nginx ssl http2
# dev-lang/python sqlite

# /etc/portage/make.conf
# USE="X gtk3 systemd -pulseaudio"
# CFLAGS="-march=native -O2 -pipe"
# MAKEOPTS="-j$(nproc)"

# World set
# @world = @system + @selected
# @system = base system packages
# @selected = packages you explicitly installed

# Rebuild reverse dependencies
sudo emerge --changed-use --deep @world

# Clean world
sudo emerge --depclean
sudo revdep-rebuild                  # Fix broken linkage
```

## Building Packages

### Building .deb Packages

```bash
# Install build tools
sudo apt install build-essential devscripts debhelper

# Create package directory structure
mkdir -p mypackage-1.0/DEBIAN
mkdir -p mypackage-1.0/usr/local/bin

# Create control file
cat > mypackage-1.0/DEBIAN/control <<EOF
Package: mypackage
Version: 1.0-1
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Name <email@example.com>
Description: My package description
 Longer description goes here.
EOF

# Copy files
cp myprogram mypackage-1.0/usr/local/bin/

# Build package
dpkg-deb --build mypackage-1.0
# Creates: mypackage-1.0.deb

# Build with proper packaging (recommended)
mkdir mypackage-1.0
cd mypackage-1.0
# Create upstream tarball: mypackage_1.0.orig.tar.gz
# Create debian/ directory with control, rules, changelog, etc.
debuild -us -uc
```

### Building .rpm Packages

```bash
# Install build tools
sudo dnf install rpm-build rpmdevtools
rpmdev-setuptree    # Creates ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create spec file: ~/rpmbuild/SPECS/mypackage.spec
cat > ~/rpmbuild/SPECS/mypackage.spec <<'EOF'
Name:           mypackage
Version:        1.0
Release:        1%{?dist}
Summary:        My package description
License:        MIT
URL:            https://example.com
Source0:        %{name}-%{version}.tar.gz

%description
Long description goes here.

%prep
%autosetup

%build
%configure
%make_build

%install
%make_install

%files
%license LICENSE
%doc README.md
/usr/local/bin/myprogram

%changelog
* Mon Jan 01 2024 Name <email@example.com> - 1.0-1
- Initial package
EOF

# Download source to SOURCES
cp mypackage-1.0.tar.gz ~/rpmbuild/SOURCES/

# Build package
rpmbuild -ba ~/rpmbuild/SPECS/mypackage.spec
# Binary RPM: ~/rpmbuild/RPMS/x86_64/mypackage-1.0-1.el9.x86_64.rpm
# Source RPM: ~/rpmbuild/SRPMS/mypackage-1.0-1.el9.src.rpm

# Build binary only
rpmbuild -bb ~/rpmbuild/SPECS/mypackage.spec
```

### Building with fpm (Effing Package Management)

```bash
# Install fpm
gem install fpm

# Create .deb from directory
fpm -s dir -t deb -n mypackage -v 1.0 --iteration 1 \
    -d "nginx" -d "postgresql" \
    --description "My package" \
    --license MIT \
    --url "https://example.com" \
    /usr/local/bin/myprogram=/usr/local/bin/myprogram \
    /etc/myapp/config=/etc/myapp/config

# Create .rpm from directory
fpm -s dir -t rpm -n mypackage -v 1.0 \
    -d "nginx" \
    --description "My package" \
    /usr/local/bin/myprogram=/usr/local/bin/myprogram

# Convert between formats
fpm -s deb -t rpm package.deb

# Create from git
fpm -s git -t deb -n mypackage https://github.com/user/repo.git

# Create from Python package
fpm -s python -t deb django
```

## Cross-References

- [Users and Groups](users-groups.md) — Package ownership and service users
- [systemd](systemd.md) — Service management for installed packages
- [File Permissions](permissions.md) — File permissions during installation

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/) — Debian packaging standards
- [RPM Packaging Guide](https://rpm-packaging-guide.github.io/) — RPM packaging tutorial
- [Arch Wiki: pacman](https://wiki.archlinux.org/title/Pacman) — pacman documentation
- [Gentoo Handbook](https://wiki.gentoo.org/wiki/Handbook:Main_Page) — Gentoo administration
- [fpm Documentation](https://fpm.readthedocs.io/) — fpm packaging tool
- [apt(8) Man Page](https://man7.org/linux/man-pages/man8/apt.8.html) — apt reference
- [dnf(8) Man Page](https://dnf.readthedocs.io/en/latest/command_ref.html) — dnf reference
