# Multipath I/O

## Introduction

Multipath I/O (MPIO) allows a server to access the same storage device through multiple physical paths—multiple HBAs, cables, switches, or controllers. This provides both **redundancy** (if one path fails, I/O continues through another) and **load balancing** (distributing I/O across paths for better performance).

Linux implements multipath through the **device-mapper multipath** (`dm-multipath`) subsystem. This is essential in enterprise SAN environments where a single LUN may be accessible through 4, 8, or even 16 paths.

## Why Multipath?

```mermaid
graph TD
    subgraph "Without Multipath"
        S1["Server HBA 0"] --> SW1["Switch A"]
        SW1 --> C1["Controller A"]
        C1 --> LUN1["LUN 0<br>/dev/sdb"]
        S1 -.->|"Single point of failure"| C1
    end
    subgraph "With Multipath"
        S2["Server HBA 0"] --> SW2["Switch A"]
        S3["Server HBA 1"] --> SW3["Switch B"]
        SW2 --> C2["Controller A"]
        SW3 --> C3["Controller B"]
        C2 --> LUN2["LUN 0<br>/dev/mapper/mpatha"]
        C3 --> LUN2
    end
```

Without multipath, a single cable failure, HBA failure, or switch failure can sever access to storage. With multipath, the same LUN is visible through multiple `/dev/sd*` devices, all mapped to a single `/dev/mapper/mpath*` device.

## Device-Mapper Multipath Architecture

```mermaid
graph TD
    APP[Application] --> FS[Filesystem]
    FS --> DMP["dm-multipath<br>/dev/mapper/mpatha"]
    DMP --> PS["Path Selector"]
    PS --> PATH1["Path 1: /dev/sdb"]
    PS --> PATH2["Path 2: /dev/sdc"]
    PS --> PATH3["Path 3: /dev/sdd"]
    PS --> PATH4["Path 4: /dev/sde"]
    PATH1 --> SAN["SAN Storage<br>LUN 0"]
    PATH2 --> SAN
    PATH3 --> SAN
    PATH4 --> SAN
```

### How It Works

1. The storage array presents the same LUN through multiple target ports
2. The server sees multiple `/dev/sd*` devices (one per path)
3. `multipathd` identifies which devices are paths to the same LUN (using SCSI identifiers)
4. A device-mapper multipath device is created that wraps all paths
5. The filesystem uses the multipath device instead of individual paths

## Installation and Configuration

```bash
# Install multipath tools
apt install multipath-tools        # Debian/Ubuntu
yum install device-mapper-multipath  # RHEL/CentOS

# Load the dm-multipath module
modprobe dm-multipath

# Enable and start multipathd
systemctl enable multipathd
systemctl start multipathd
```

### Configuration File

The main configuration is `/etc/multipath.conf`:

```bash
cat /etc/multipath.conf
defaults {
    # Polling interval to check path health (seconds)
    polling_interval        30
    
    # Path selector algorithm
    path_grouping_policy    multibus
    
    # Path checker method
    path_checker            tur
    
    # Failback mode
    failback                immediate
    
    # User-friendly names (mpatha, mpathb, etc.)
    user_friendly_names     yes
    
    # Flush queue on path failure
    flush_on_last_del       yes
    
    # Maximum number of paths
    max_fds                 8192
    
    # Reservation key (for SCSI persistent reservations)
    reservation_key         0x12345678
}

# Blacklist devices that should NOT be multipathed
blacklist {
    wwid "SATA_Samsung_SSD_870_ABC123"
    devnode "^sd[a-c]$"    # Don't multipath sda, sdb, sdc
    device {
        vendor  "Dell"
        product "Virtual"
    }
}

# Whitelist exceptions (override blacklist)
blacklist_exceptions {
    wwid "3600508b4001234567890123456789012"
}

# Device-specific configurations
devices {
    device {
        vendor                  "NETAPP"
        product                 "LUN.*"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
        failback                immediate
        no_path_retry           queue
        rr_min_io               100
        rr_min_io_rq            1
    }
    
    device {
        vendor                  "PURE"
        product                 "FlashArray"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
        failback                immediate
    }
    
    device {
        vendor                  "IBM"
        product                 "2145"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
        failback                immediate
    }
}

# Multipath device configuration
multipaths {
    multipath {
        wwid        "3600508b4001234567890123456789012"
        alias       oracle_data
        path_grouping_policy    group_by_prio
        failback                immediate
        rr_min_io               100
    }
}
```

## Path Selectors

The path selector determines how I/O is distributed across paths:

### round-robin (Default)

```bash
# Round-robin: alternate between all active paths
path_selector "round-robin 0"
# The "0" means use the default number of I/Os before switching (1000 for reads)
```

### service-time

```bash
# Weighted by service time (faster paths get more I/O)
path_selector "service-time 0"
```

### queue-length

```bash
# Weighted by queue length (less busy paths get more I/O)
path_selector "queue-length 0"
```

## Path Priorities and ALUA

### ALUA (Asymmetric Logical Unit Access)

ALUA is a SCSI feature that allows storage controllers to report the preferred path to a LUN. In active-passive arrays, only one controller is "optimized" for a given LUN.

```mermaid
graph TD
    subgraph "ALUA Active-Passive"
        LUN["LUN 0"]
        CA["Controller A<br>Active/Optimized<br>TPGS: 1"]
        CB["Controller B<br>Active/Non-optimized<br>TPGS: 1"]
        LUN --> CA
        LUN --> CB
    end
```

```bash
# Check ALUA state
multipathd show paths
# hcil    dev  dev_t  pri dm_st   chk_st  dev_st
# 0:0:0:1 sdb  8:16   1   active  ready   running
# 0:0:1:1 sdc  8:32   1   active  ready   running
# 1:0:0:1 sdd  8:48   0   active  ready   running
# 1:0:1:1 sde  8:64   0   active  ready   running

# ALUA priority groups:
# Group 0 (optimized) = preferred paths
# Group 1 (non-optimized) = alternate paths

# Configure ALUA priority in multipath.conf
devices {
    device {
        vendor  "NETAPP"
        product "LUN.*"
        prio    alua
    }
}
```

## Failover and Failback

### Failover: Path Failure Detection

```mermaid
sequenceDiagram
    participant MD as multipathd
    participant P1 as Path 1 (active)
    participant P2 as Path 2 (standby)
    participant HW as Storage

    Note over MD: Health check (tur)
    MD->>P1: TEST UNIT READY
    P1-->>MD: FAILURE (timeout/error)
    MD->>MD: Mark Path 1 as failed
    MD->>P2: Switch I/O to Path 2
    P2->>HW: I/O requests
    HW-->>P2: Responses
    Note over MD: All I/O now on Path 2
```

### Failback: Path Recovery

```mermaid
sequenceDiagram
    participant MD as multipathd
    participant P1 as Path 1 (failed)
    participant P2 as Path 2 (active)
    participant HW as Storage

    Note over MD: Health check (tur)
    MD->>P1: TEST UNIT READY
    P1-->>MD: SUCCESS
    MD->>MD: Mark Path 1 as active
    
    alt failback=immediate
        MD->>MD: Rebalance I/O to all paths
    else failback=manual
        MD->>MD: Keep Path 1 active but don't rebalance
    else failback=deferred +N
        MD->>MD: Wait N seconds, then rebalance
    end
```

### No Path Retry

```bash
# What to do when all paths fail
# queue: queue I/O until a path returns (dangerous for hung apps)
# fail: fail I/O immediately
# N: retry N times, then fail

no_path_retry queue   # Queue until path returns
no_path_retry 5       # Retry 5 times
no_path_retry fail    # Immediate failure
```

## Multipath Commands

### View Multipath Status

```bash
# Show all multipath devices
multipath -ll
# mpatha (3600508b4001234567890123456789012) dm-0 NETAPP,LUN C-Mode
# size=500G features='4 queue_if_no_path' hwhandler='1 alua' wp=rw
# |-+- policy='round-robin 0' prio=50 status=active
# | |- 0:0:0:1 sdb 8:16  active ready running
# | `- 0:0:1:1 sdc 8:32  active ready running
# `-+- policy='round-robin 0' prio=10 status=enabled
#   |- 1:0:0:1 sdd 8:48  active ready running
#   `- 1:0:1:1 sde 8:64  active ready running

# Show multipath topology
multipathd show topology
# mpatha (3600508b4001234567890123456789012) dm-0 NETAPP,LUN C-Mode
# [size=500G][features=4 queue_if_no_path][hwhandler=1 alua][n=0]
# |-+- policy=round-robin 0 [prio=50][status=active]
# | |- 0:0:0:1 sdb 8:16  [active][ready]
# | `- 0:0:1:1 sdc 8:32  [active][ready]
# `-+- policy=round-robin 0 [prio=10][status=enabled]
#   |- 1:0:0:1 sdd 8:48  [active][ready]
#   `- 1:0:1:1 sde 8:64  [active][ready]
```

### Interactive multipathd Console

```bash
# Enter multipathd console
multipathd -k
# multipathd> show maps
# name   sysfs   uuid
# mpatha dm-0    3600508b4001234567890123456789012
#
# multipathd> show paths
# hcil    dev  dev_t  pri dm_st   chk_st  dev_st
# 0:0:0:1 sdb  8:16   50  active  ready   running
# 0:0:1:1 sdc  8:32   50  active  ready   running
# 1:0:0:1 sdd  8:48   10  active  ready   running
# 1:0:1:1 sde  8:64   10  active  ready   running
#
# multipathd> show map mpatha status
# mpatha: dm-0 NETAPP,LUN C-Mode
# size=500G features='4 queue_if_no_path' hwhandler='1 alua' wp=rw
#
# multipathd> fail path mpatha sdb
# ok
#
# multipathd> reinstate path mpatha sdb
# ok
#
# multipathd> resize map mpatha
# ok
#
# multipathd> quit
```

## Device Identification

Multipath identifies devices using SCSI identifiers:

```bash
# View SCSI identifiers
/lib/udev/scsi_id -g -u /dev/sdb
# 3600508b4001234567890123456789012

# Multipath uses the WWID (World Wide Identifier) to group paths
# The WWID comes from:
# 1. SCSI Unit Serial Number (VPD page 0x80)
# 2. SCSI Device Identification (VPD page 0x83)
# 3. ATA serial number (for SATA devices via libata)
```

## Multipath with LVM

Multipath and LVM work together seamlessly:

```bash
# After creating multipath devices, create PVs on them
pvcreate /dev/mapper/mpatha

# Create VG
vgcreate myvg /dev/mapper/mpatha /dev/mapper/mpathb

# Create LV
lvcreate -L 100G -n lv_data myvg

# Mount
mkfs.xfs /dev/myvg/lv_data
mount /dev/myvg/lv_data /data
```

### LVM Configuration for Multipath

```bash
# In /etc/lvm/lvm.conf, filter out individual paths
devices {
    filter = ["a|/dev/mapper/.*|", "r|/dev/sd.*|", "r|.*|"]
    # Accept only dm-multipath devices, reject raw sd* devices
}
```

## Performance Tuning

### Path Group Policy

```bash
# multibus: all paths in one group (load balanced)
path_grouping_policy multibus

# failover: one path active, others standby
path_grouping_policy failover

# group_by_prio: group paths by ALUA priority
path_grouping_policy group_by_prio

# group_by_node_name: group by SCSI node name
path_grouping_policy group_by_node_name

# group_by_serial: group by SCSI serial number
path_grouping_policy group_by_serial
```

### Round-Robin Tuning

```bash
# Minimum I/O count before switching path (for reads)
rr_min_io 1000

# Minimum I/O requests before switching (for newer kernels)
rr_min_io_rq 1

# Both control how many I/Os are sent down one path before
# switching to the next path in the round-robin group
```

## Troubleshooting

### Path Not Appearing

```bash
# Check if device is blacklisted
multipath -v3 2>&1 | grep -i blacklist
# Jul 21 10:00:00 | sdb: blacklisted (udev property match)

# Check SCSI identifiers
/lib/udev/scsi_id -g -u /dev/sdb
# Compare with multipath.conf blacklist/whitelist
```

### Stale Multipath Device

```bash
# Flush and remove stale multipath device
multipath -f mpatha

# If stuck, remove device-mapper table
dmsetup remove mpatha

# Force remove
dmsetup remove --force mpatha
```

### All Paths Down

```bash
# Check path status
multipathd show paths
# All paths show "faulty" or "ghost"

# Check physical connectivity
# Check switch status
# Check storage controller status
# Check for SCSI reservation conflicts

# Force path reinstatement
multipathd reinstate path mpatha sdb
```

## References

- [device-mapper multipath documentation](https://www.kernel.org/doc/html/latest/admin-guide/device-mapper/dm-mpath.html)
- [Red Hat DM Multipath Guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/dm_multipath/)
- [multipath.conf(5) man page](https://man7.org/linux/man-pages/man5/multipath.conf.5.html)
- [SCSI ALUA specification](https://www.t10.org/drafts.htm)

## Multipath with NVMe (ANA)

NVMe devices use Asymmetric Namespace Access (ANA) instead of SCSI ALUA. The Linux NVMe multipath driver (built into the NVMe driver) handles multipath natively.

### NVMe Native Multipath

```bash
# NVMe multipath is enabled by default in modern kernels
# Check if native multipath is active
cat /sys/module/nvme_core/parameters/multipath
# Y

# When native multipath is active, only one /dev/nvmeXnY is visible
# (not multiple /dev/sd* devices like SCSI multipath)

# View NVMe multipath topology
nvme list-subsys
# nvme-subsys0 - NQN=nqn.2026-07.example:storage
# \n +- nvme0 pcie traddr=0000:03:00.0 live optimized
# \n +- nvme1 pcie traddr=0000:04:00.0 live non-optimized

# ANA states:
# optimized: preferred path, lowest latency
# non-optimized: alternate path
# inaccessible: path temporarily unavailable
# persistent-loss: path permanently failed

# Switch ANA path policy
echo "round-robin" > /sys/class/nvme/nvme0/sysfs_path_policy
# Or via kernel boot parameter: nvme_core.multipath=Y
```

### NVMe-oF Multipath

```bash
# NVMe-oF supports multipath via multiple connections
echo "options nvme_core multipath=Y" >> /etc/modprobe.d/nvme.conf

# Connect to same subsystem via multiple paths
nvme connect -t tcp -a 192.168.1.100 -s 4420 -n nqn.example:storage
nvme connect -t tcp -a 192.168.1.101 -s 4420 -n nqn.example:storage

# Both paths appear under one subsystem
nvme list-subsys
# nvme-subsys1 - NQN=nqn.example:storage
# \n +- nvme2 tcp traddr=192.168.1.100 live optimized
# \n +- nvme3 tcp traddr=192.168.1.101 live non-optimized

# Path failover is automatic
# If 192.168.1.100 fails, traffic moves to 192.168.1.101
```

### NVMe Multipath vs SCSI dm-multipath

| Feature | NVMe Native MPIO | SCSI dm-multipath |
|---------|-----------------|-------------------|
| Kernel component | NVMe driver (built-in) | device-mapper + multipathd |
| User-space tool | nvme-cli | multipath/multipathd |
| Path selection | ANA (kernel) | Path selector policy |
| Failover latency | ~1-5ms | ~5-30ms |
| Device visibility | Single /dev/nvmeXnY | /dev/mapper/mpathX |
| Configuration | Minimal (auto) | /etc/multipath.conf |
| Multipath type | Native | SCSI layer + DM |

## DM Multipath with iSCSI

```bash
# iSCSI multipath: multiple sessions to same target
# Each session provides a separate path

# Create multiple iSCSI sessions
iscsiadm -m node -T iqn.example:target -p 192.168.1.100:3260 --login
iscsiadm -m node -T iqn.example:target -p 192.168.1.101:3260 --login

# Each session creates a separate /dev/sd* device
# multipathd combines them into one multipath device

# Configure in /etc/multipath.conf
devices {
    device {
        vendor                  "LIO-ORG"
        product                 ".*"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
    }
}
```

## Advanced Multipath Patterns

### Active-Active with Priority Groups

```mermaid
graph TD
    subgraph "Active-Active Configuration"
        MP["/dev/mapper/mpatha"]
        PG1["Path Group 1 (prio=50)<br>Active/Optimized"]
        PG2["Path Group 2 (prio=10)<br>Active/Non-optimized"]
        MP --> PG1
        MP --> PG2
        PG1 --> P1["Path 1: /dev/sdb"]
        PG1 --> P2["Path 2: /dev/sdc"]
        PG2 --> P3["Path 3: /dev/sdd"]
        PG2 --> P4["Path 4: /dev/sde"]
    end
```

```bash
# Round-robin across all active paths
path_grouping_policy multibus
path_selector "round-robin 0"

# Group by priority (ALUA)
path_grouping_policy group_by_prio

# Failover only (one path at a time)
path_grouping_policy failover
```

### Multipath Configuration for Specific Storage Arrays

```bash
# NetApp ONTAP
devices {
    device {
        vendor                  "NETAPP"
        product                 "LUN.*"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
        failback                immediate
        no_path_retry           queue
        rr_min_io               128
        fast_io_fail_tmo        10
        dev_loss_tmo            600
    }
}

# Pure Storage
devices {
    device {
        vendor                  "PURE"
        product                 "FlashArray"
        path_grouping_policy    group_by_prio
        path_selector           "service-time 0"
        path_checker            tur
        prio                    alua
        failback                immediate
        no_path_retry           queue
    }
}

# Dell PowerStore
devices {
    device {
        vendor                  "DELL"
        product                 "PowerStore"
        path_grouping_policy    group_by_prio
        path_selector           "round-robin 0"
        path_checker            tur
        prio                    alua
        failback                immediate
    }
}
```

## Multipath Monitoring and Alerting

```bash
#!/bin/bash
# multipath-monitor.sh - Check path health and alert

while true; do
    # Check for failed paths
    FAILED=$(multipathd show paths | grep -c "faulty\|ghost")
    
    if [ "$FAILED" -gt 0 ]; then
        echo "WARNING: $FAILED failed multipath paths detected"
        multipathd show paths | grep "faulty\|ghost"
        # Send alert (example: email or webhook)
        # curl -X POST https://hooks.slack.com/... \
        #   -d "{'text': 'Multipath failure: $FAILED paths down'}"
    fi
    
    # Check for path state changes
    CURRENT=$(multipathd show paths -f | md5sum)
    if [ "$CURRENT" != "$LAST" ]; then
        echo "Path state change detected at $(date)"
        multipathd show paths
        LAST="$CURRENT"
    fi
    
    sleep 30
done
```

### Performance Monitoring

```bash
# Per-path I/O statistics
multipathd show paths stats
# hcil    dev  dev_t  dm_st  checker  rd_cnt  rd_bytes  wr_cnt  wr_bytes
# 0:0:0:1 sdb  8:16   active ready    12345   50MB      67890   270MB
# 0:0:1:1 sdc  8:32   active ready    12345   50MB      67890   270MB
# 1:0:0:1 sdd  8:48   active ready    12345   50MB      67890   270MB
# 1:0:1:1 sde  8:64   active ready    12345   50MB      67890   270MB

# iostat for multipath device
iostat -x -d /dev/mapper/mpatha 5
# Device  r/s   w/s   rMB/s  wMB/s  await  svctm  %util
# mpatha  5000  2000  19.5   7.8    0.5    0.1    70.0

# Per-path latency comparison
for path in sdb sdc sdd sde; do
    echo "$path:"
    iostat -x -d /dev/$path 1 2 | tail -1
done
```

## Multipath Troubleshooting Decision Tree

```mermaid
graph TD
    A["Multipath issue"] --> B{"multipath -ll works?"}
    B -->|No| C{"multipathd running?"}
    C -->|No| D["systemctl start multipathd"]
    C -->|Yes| E{"dm-multipath module loaded?"}
    E -->|No| F["modprobe dm-multipath"]
    E -->|Yes| G{"Devices in /dev/mapper?"}
    G -->|No| H{"Devices blacklisted?"}
    H -->|Yes| I["Update blacklist in multipath.conf"]
    H -->|No| J["Check SCSI identifiers"]
    B -->|Yes| K{"Paths healthy?"}
    K -->|No| L{"Physical connection OK?"}
    L -->|No| M["Check cables/HBA/switch"]
    L -->|Yes| N{"SCSI reservations?"}
    N -->|Yes| O["Clear reservations"]
    N -->|No| P["Reinstate path: multipathd reinstate"]
    K -->|Yes| Q{"Performance OK?"}
    Q -->|No| R{"Path selector policy?"}
    R --> S["Tune rr_min_io or use service-time"]
    Q -->|Yes| T["All good!"]
```

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- <https://christopherco.github.io/multipath-tools/> - multipath-tools documentation
- <https://access.redhat.com/articles/165953> - Multipath troubleshooting guide
- <https://www.snia.org/sites/default/files/SNIA_DMTF_DDC_Multipathing_WP.pdf> - Multipathing best practices

## Related Topics

- [Storage Overview](overview.md)
- [SCSI and NVMe](scsi-nvme.md)
- [Storage Area Networks](san.md)
- [LVM Deep Dive](lvm-deep-dive.md)
