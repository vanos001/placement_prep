# Bare-Metal Clouds: When You Rent the Whole Machine

A VM is a slice of a server; a bare-metal instance is the server. The provider
still owns the rack and a management presence, but the hypervisor between your
guest OS and the silicon is gone -- and that deletion cascades through
provisioning speed, CPU isolation, PCIe depth, and per-core licensing.

The market keeps testing the model. Oracle's compute docs state it plainly:
a bare metal instance gives "dedicated physical server access for highest
performance and strong isolation." IBM Cloud sells bare metal as a first-class
option with its own ordering, imaging, and hourly/monthly billing tracks;
Hetzner's Robot platform has sold dedicated root servers that way for two
decades. Equinix Metal -- the purest "bare metal as an API" product, born as
Packet in 2015 -- announced end-of-sale in November 2024 and shut down on
June 30, 2026: whole-machine renting is a narrow, durable niche, not a volume
cloud business.

## The boundary: what you are actually renting

```text
        VM fleet                        Bare-metal fleet
+---------------------------+   +---------------------------+
| your app                  |   | your app                  |
| guest OS (you patch)      |   | your OS (you patch)       |
| hypervisor (provider)     |   | nothing -- or YOUR hyper. |
| host OS + mgmt (provider) |   | provider agent (BMC, NIC, |
| silicon + NICs + disks    |   | offload cards), silicon   |
+---------------------------+   +---------------------------+
 tenant owns a slice;             tenant owns the stack;
 provider kernel sits in the      provider lives below the
 data path for every packet       OS, not inside it
```

The provider does not vanish: on AWS, `*.metal` instances still carry the
Nitro offload cards that terminate VPC networking and EBS I/O; what disappears
is the host hypervisor scheduling your vCPUs. EC2 Mac instances go further --
they "do not use the Nitro hypervisor" at all, which is why macOS
virtualization licensing works there.

## The trade ledger

| Dimension          | VM fleet                             | Bare-metal fleet                           |
|--------------------|--------------------------------------|--------------------------------------------|
| Time to first boot | ~1 minute (API to running guest)     | tens of minutes (netboot + wipe + image)   |
| Resize             | stop, change shape, start            | reprovision, or buy the bigger machine     |
| Live migration     | provider moves you off bad hosts     | not offered; maintenance = reboot window   |
| Noisy neighbor     | possible (steal time, L3, memory BW) | none on CPU: every core and cache is yours |
| CPU features       | whatever the shape exposes           | full PMU, SMT on/off, RDT/MBA, deep counters |
| PCIe passthrough   | limited, special-cased               | default state: GPUs, NVMe, DPDK poll NICs  |
| Licensing          | often per vCPU, provider-pinned      | license physical cores; move BYOL images   |

The middle column is a schedulable illusion; the right column is physical
truth (a provider can oversubscribe a VM host's DRAM, never your machine).
Most workloads happily trade truth for elasticity; this page is about the
ones that cannot.

## Provisioning: PXE, not a hypervisor API call

Provisioning a VM is bookkeeping; provisioning a machine is a ritual that
OpenStack Ironic implements as a first-class state machine. The probed Ironic
docs (38.x, pages updated 2026) show the pieces every bare-metal cloud needs:

- **Network boot** -- boot interfaces `pxe`, `ipxe`, and (since the 2024.1
  cycle) `http`/`http-ipxe`; a DHCP handout steers the machine into a ramdisk,
  because there is no hypervisor to inject an image into.
- **Inspection** -- the ramdisk inventories CPUs, DRAM, NICs, disks and writes
  them into the node record, so the scheduler sees real hardware.
- **Cleaning** -- between tenants Ironic runs *clean steps* (disk wipes, RAID
  zapping, firmware resets) so that, quoting the docs, "the tenant will get a
  consistent bare metal node deployed every time." Automated on
  `manageable -> available` (first use) and `active -> available` (recycle);
  skip it and tenant B inherits tenant A's RAID layout -- a compliance incident.
- **Deploy** -- netboot again, write the tenant image, boot into it: `active`.

Hetzner Robot exposes the ritual unabashedly: order a specific hardware
configuration, boot the Rescue system, run `installimage` yourself. AWS and
Oracle hide it behind an API, but the physics does not negotiate.

**Reprovision latency math.** Suppose a deploy takes 20 minutes end to end
(ramdisk boot + inventory + clean + image write): an autoscaler needing 50
machines for a spike waits `50 * 20 / parallelism` -- 3.3 hours at 5-way
concurrency, versus under a minute for 50 VM launches. If a pool of 500
churns 20 machines a day the tax is noise -- hence warm pools of `available`
machines, sized like a buffer.

## Tenancy, networking, and how deep the bus goes

Single tenancy is the product: compliance regimes that forbid multi-tenant
hypervisors are satisfied by construction, and no co-tenant shares your LLC,
memory controllers, or DRAM. Networking is where the provider still lives --
your machine attaches to the VPC through a provider NIC (on AWS, a Nitro card)
that enforces security groups outside your kernel; Hetzner's Robot adds
separately orderable failover IPs routable to any of your servers.

Passthrough depth is the quiet superpower: on a VM, passing through a GPU or
NVMe device is a special case; on metal it is the default state. DPDK can
drive line rate on every queue, perf reads the PMU unmasked, and you can
disable SMT, pin IRQs, and set RDT classes like you own the place -- because
you do.

## Workload fit

- **Licensed databases (Oracle, SQL Server, SAP).** Per-core licenses applied
  to 48 physical cores rather than 96 vCPUs; BYOL images move between on-prem
  and cloud. Often the whole business case.
- **HPC and tightly coupled jobs.** No steal time, full PMU, MPI wanting every
  core (scheduler side: [HPC Infrastructure](../hpc/hpc-infra.md)).
- **Storage engines (Ceph, object stores).** Every NVMe device passed through,
  every core for the OSD threads; a hypervisor adds a virtio hop to the
  hottest I/O path in the stack.
- **Latency-sensitive services.** Tail latency comes from interference --
  cache evictions, SMT contention, hypervisor bookkeeping; metal removes the
  co-tenant variables.
- **Bring-your-own-hypervisor.** AWS's FAQ: workloads needing "access to
  hardware virtualization extensions" that are "performance sensitive" should
  evaluate bare metal. ESXi on metal also unlocks vMotion, impossible from a
  tenant VM.

## Cost and elasticity: a model, not a quote

The runnable model below (prices in the c7i/m7i ballpark, labeled MODEL)
compares steady-state demand of 5,000 physical-core-equivalents (PCE) over
three years. It charges the VM fleet for (a) a hypervisor tax swept from 2 to
10 percent and (b) shape-granularity rounding via `ceil`, with matched
license-per-silicon economics: a vCPU license costs half a core license.

```python
# MODEL (not a quote): steady-state fleet TCO -- VM fleet vs bare-metal fleet.
# VM: 96-vCPU shape = 48 PCE of silicon at $4.608/h, hypervisor tax v% makes
# effective PCE per VM = 48*(1-v), licenses billed per vCPU (half rate).
# BM: 48-core machine at $4.680/h, no tax, licenses per physical core; ceil
# rounding gives machine-granularity waste. 3-year on-demand horizon.
import math

HOURS = 24 * 365 * 3
DEMAND = 5000
CORES = 48
VM_PRICE, BM_PRICE = 4.608, 4.680
LIC = 0.12                      # $ per licensed core-hour (physical)

def fleet(demand, pce, price_h, lic_units, lic_rate, overhead):
    eff = pce * (1.0 - overhead)
    n = math.ceil(demand / eff)
    return n, eff * n, n * price_h, n * lic_units * lic_rate

def show(tag, fl):
    print("%-10s %4d  %6d  %5.1f%%  $%9.2f  $%8.2f  $%10.2f  $%.5f"
          % (tag, fl[0], fl[1], 100.0 * DEMAND / fl[1], fl[2], fl[3],
             fl[2] + fl[3], (fl[2] + fl[3]) / DEMAND))

bm = fleet(DEMAND, CORES, BM_PRICE, CORES, LIC, 0.0)
bm_rate = (bm[2] + bm[3]) / DEMAND

print("MODEL: VM fleet vs bare-metal fleet | demand = %d PCE | 3-year horizon" % DEMAND)
print("VM shape: 96 vCPU (48 PCE) at $%.3f/h | BM machine: 48 cores at $%.3f/h"
      % (VM_PRICE, BM_PRICE))
print("license: $%.2f/core-h physical, $%.4f/vCPU-h virtualized (half rate)"
      % (LIC, LIC / 2))
print()
print("hourly fleet cost by part and effective $/PCE-hour:")
print("fleet      n    eff-PCE  util   compute/h   license/h     total/h    $/PCE-h")
show("BM (0%)", bm)
for pct in (2, 4, 6, 8, 10):
    show("VM (%d%%)" % pct, fleet(DEMAND, CORES, VM_PRICE, 2 * CORES, LIC / 2, pct / 100.0))

tot = lambda fl: fl[2] + fl[3]
vm5 = fleet(DEMAND, CORES, VM_PRICE, 2 * CORES, LIC / 2, 0.05)
print()
print("3-year totals at 5%% overhead: VM = $%.2f | BM = $%.2f | delta = $%.2f (%.2f%%)"
      % (tot(vm5) * HOURS, tot(bm) * HOURS, (tot(vm5) - tot(bm)) * HOURS,
         100.0 * (tot(vm5) - tot(bm)) / tot(bm)))

v = 0.0
while tot(fleet(DEMAND, CORES, VM_PRICE, 2 * CORES, LIC / 2, v)) / DEMAND < bm_rate:
    v += 0.00001
print("overhead crossover: VM fleet stops winning once hypervisor tax > %.2f%%"
      % (100 * v))

d = 0.0
while tot(fleet(DEMAND, CORES, VM_PRICE, 2 * CORES, LIC * d, 0.05)) / DEMAND < bm_rate:
    d += 0.001
print("license crossover: at 5%% overhead, VM wins only if vCPU license < %.1f%%"
      % (100 * d))
print("of the physical-core rate; at the modeled 50% rate BM wins by ~4%")
```

Output (verbatim run):

```text
MODEL: VM fleet vs bare-metal fleet | demand = 5000 PCE | 3-year horizon
VM shape: 96 vCPU (48 PCE) at $4.608/h | BM machine: 48 cores at $4.680/h
license: $0.12/core-h physical, $0.0600/vCPU-h virtualized (half rate)

hourly fleet cost by part and effective $/PCE-hour:
fleet      n    eff-PCE  util   compute/h   license/h     total/h    $/PCE-h
BM (0%)     105    5040   99.2%  $   491.40  $  604.80  $   1096.20  $0.21924
VM (2%)     107    5033   99.3%  $   493.06  $  616.32  $   1109.38  $0.22188
VM (4%)     109    5022   99.5%  $   502.27  $  627.84  $   1130.11  $0.22602
VM (6%)     111    5008   99.8%  $   511.49  $  639.36  $   1150.85  $0.23017
VM (8%)     114    5034   99.3%  $   525.31  $  656.64  $   1181.95  $0.23639
VM (10%)    116    5011   99.8%  $   534.53  $  668.16  $   1202.69  $0.24054

3-year totals at 5% overhead: VM = $29971814.40 | BM = $28808136.00 | delta = $1163678.40 (4.04%)
overhead crossover: VM fleet stops winning once hypervisor tax > 0.79%
license crossover: at 5% overhead, VM wins only if vCPU license < 46.6%
of the physical-core rate; at the modeled 50% rate BM wins by ~4%
```

Three readings. First, the **overhead crossover sits at 0.79 percent**, below
the realistic 2-10 percent hypervisor-tax band, so for steady demand metal
wins the whole sweep by 1-9 percent of the hourly bill. Second, the decisive
variable is not overhead but **license pricing**: below 46.6 percent of the
physical-core rate the VM fleet flips back to winning -- vendors know this,
which is why BYOL images are priced so carefully. Third, the model has no
term for elasticity: if demand is spiky, the metal fleet's 105 machines idle
through the trough while VMs shed instances, a term that usually dwarfs the
4 percent -- the honest answer to "why not always metal?"

## When NOT to rent the whole machine

- **Spiky demand.** Machine granularity is the coarsest unit there is; a fleet
  that sheds 80 percent nightly cannot shed it on metal.
- **Autoscaler-heavy architectures.** Tens-of-minutes reprovisioning fights
  reactive scaling (VM-side machinery: [Autoscaling](./autoscaling.md)).
- **Short-lived compute.** CI runners and minutes-scale batch pay the
  reprovision tax per episode, which dwarfs the 2-10 percent overhead.
- **Anything needing live migration.** Host maintenance on metal is a
  scheduled reboot; VM fleets absorb the same event invisibly.

## References

All URLs probed August 2026; probe status stated honestly.

1. AWS, Amazon EC2 bare metal instances (EC2 User Guide):
   <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/bare-metal-instances.html>
   -- HTTP 200 (JS frame shell; quotes cross-checked against the EC2 FAQ,
   HTTP 200: <https://aws.amazon.com/ec2/faqs/>).
2. Oracle, Overview of the Compute Service:
   <https://docs.oracle.com/iaas/Content/Compute/Concepts/computeoverview.htm>
   -- HTTP 200; quoted above. Product page also 200:
   <https://www.oracle.com/cloud/compute/bare-metal/>.
3. IBM Cloud, Bare metal server options:
   <https://cloud.ibm.com/docs/bare-metal?topic=bare-metal-about-bm> and
   <https://cloud.ibm.com/docs/bare-metal> -- both HTTP 200.
4. Equinix Metal shutdown FAQ: <https://docs.equinix.com/metal/eos-faq> --
   HTTP 200; EOL "June 30, 2026 at 11:59 PM PST", announced November 7, 2024
   (<https://docs.equinix.com/releases/end-of-life/eol-products-services>).
   Legacy host metal.equinix.com returns HTTP 403 to curl (bot block). The
   "Equinix Metal now IBM" assumption is wrong: Equinix discontinued the
   product outright; it was not acquired by IBM.
5. OpenStack Ironic 38.x (pages updated 2026), all HTTP 200:
   <https://docs.openstack.org/ironic/latest/>,
   <https://docs.openstack.org/ironic/latest/admin/cleaning.html> (cleaning
   quotes), <https://docs.openstack.org/ironic/latest/admin/inspection.html>,
   <https://docs.openstack.org/ironic/latest/install/configure-pxe.html>
   (`pxe`/`ipxe`/`http`/`http-ipxe` boot interfaces; DHCP provider=neutron).
6. Hetzner, Robot dedicated server docs:
   <https://docs.hetzner.com/robot/dedicated-server/> -- HTTP 200; Rescue
   system, failover IPs. VM-side contrast also 200:
   <https://docs.hetzner.cloud/>.
7. AWS EC2 instance types catalog (metal SKUs; model pricing ballpark):
   <https://docs.aws.amazon.com/ec2/latest/instancetypes/instance-types.html>
   -- HTTP 200.
