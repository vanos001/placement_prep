# Autonomous Vehicle Compute Stacks: Sensors, Silicon, and the Safety Case

An autonomous vehicle is a real-time control system wrapped around a small
data center: 8-11 cameras, 1-5 lidars, half a dozen radars, and one SoC that
must turn that firehose into steering and braking decisions inside a 100 ms
loop, for the life of the vehicle. [Embedded AI](./embedded-ai.md) covers
on-device inference in general; [V2X](./v2x.md) covers the radio link to
other vehicles; this page covers what sits between -- sensor budget, silicon,
safety case, and the software making it all deterministic.

## The workload: sensors first, silicon second

The canonical AD stack runs perception -> fusion -> prediction -> planning -> control at 10 Hz with a faster control inner loop:

```text
 8-11 cameras ---RAW12---> ISP (3A, demosaic) --> perception DNNs --> fusion
 1-5 lidars  ---points--> voxelize/pillar -----> 3D detectors -->   (BEV object
 5 radars    ---cloud---> CFAR, chirp DSP ------> velocity (MMW)     list)
 12 ultrasonics -echo---> envelope -----------------> parking ranges      |
                                                                          v
                                                prediction --> planner --> control
                                                (0.1-1 s)     (10 Hz)     (50-100 Hz)
      [ safety island: lockstep MCU -- heartbeats, plausibility monitors,
        watchdog chain, safe state / minimal risk maneuver (ASIL-D) ]
```

Two properties shape everything below. First, the accelerator never sees raw
sensor bytes: the ISP converts RAW12 to RGB tensors, lidar points are
voxelized, radar chirp cubes become point clouds in the sensor's DSP.
Second, the pipeline is latency-chained: a frame must clear detection,
fusion, prediction, and planning and still reach the actuators within the
fault-tolerant time interval the safety case assumes. Raw ingest is
camera-dominated -- eight 3840x2160 cameras at 30 fps RAW12 stream ~3 GB/s
before a single network runs; Intel's widely cited estimate put an
autonomous car's data generation at 4 TB per roughly 90 minutes of driving,
the same order as the demo's bottom-up budgets. Most of that stream is logged
for fleet learning, not consumed by the driving compute.

## The platform landscape

Peaks are vendor-quoted; the Verification column says what a scripted probe confirmed. Precision suffixes move numbers 2-4x.

| Platform | Peak AI compute | Architecture notes | Verification |
|---|---|---|---|
| NVIDIA DRIVE Orin | 254 TOPS (INT8) | Ampere-class GPU + DLA accelerators, 12x Cortex-A78AE | NVIDIA newsroom (probed) |
| NVIDIA DRIVE Thor | 2,000 TFLOPS (FP8) | central computer: ADAS + cockpit + parking unified; transformer engine | NVIDIA newsroom (probed) |
| Mobileye EyeQ6 High | 34 TOPS | fixed-function accelerator cores + CPU cluster | Mobileye EyeQ page (probed) |
| Mobileye EyeQ Ultra | 176 TOPS | single-package "AV-on-chip" aimed at consumer L4 | Mobileye EyeQ page (probed) |
| Tesla FSD computer (HW3) | 144 TOPS (2 SoCs x 2x36-TOPS NNAs) | 12x Cortex-A72 per SoC; whole-computer duplication for fault tolerance | Hot Chips 31 talk via Cadence writeup (probed) |
| Qualcomm Snapdragon Ride Flex | no single headline TOPS | one SoC family mixing cockpit + ADAS at mixed criticality | vendor page (not probed) |
| Huawei MDC 810 | 400+ TOPS (vendor claim) | Ascend-based AI cores; compute platform sold to OEMs | 2021 launch, press (not probed) |
| Horizon Journey 6 series | 10-560 TOPS span | BPU (Bayesian NN) cores; predecessor Journey 5 = 128 TOPS | vendor page (probed) |

The table cannot carry: DRIVE Thor's headline moved between announcements --
2,000 TFLOPS FP8 in the 2022 release, restated in current NVIDIA materials as
1,000 INT8 TOPS / 2,000 FP4 TFLOPS. Tesla's "144 TOPS" is a board number (two
SoCs x two NNAs x 36 TOPS) next to chip-level ones. HW3 buys fault tolerance
by duplicating the entire computer, unlike the islands below.

## Inside the stack: ASIL decomposition and the safety island

ISO 26262 grades functions QM, A, B, C, D by risk, ASIL-D strictest. One AD
computer mixes all of them, and ISO 26262-9 resolves that with
**decomposition**: an ASIL D requirement may be split across independent
elements -- ASIL B(D) + ASIL B(D), or ASIL D(D) + QM(D) -- if the
independence argument holds.

```text
+------------------------------------------------------------------+
| DRIVE-Orin-class SoC                                             |
|  +--------------------+   +-----------------------------------+  |
|  | safety island      |   | main compute (no ASIL-D claim)    |  |
|  | lockstep MCU cores |   | GPU + DLA: perception DNNs        |  |
|  | watchdog, FTM      |<--| Cortex-A78AE: planner, monitors   |  |
|  | safe-state logic   |   +-------------------+---------------+  |
+-------------|-----------------------------|----------------------+
              v                             v
   +---------------------+    +------------------------+
   | actuator MCU        |<---| plausibility monitor:  |
   | (ASIL D, lockstep,  |    | is the DNN output      |
   | external watchdog)  |    | physically possible?   |
   +---------------------+    +------------------------+
```

| Function | Typical ASIL | How it is met |
|---|---|---|
| Actuator interface, final braking/steering | ASIL D | lockstep MCU, dual-channel actuation |
| Trajectory planning + fallback planner | ASIL D (or B(D)+B(D)) | decomposed across redundant planner paths |
| Perception DNN outputs | QM output, ASIL-wrapped | plausibility/range checks + safe-state fallback |
| Comfort features (parking assist UI, cluster) | QM | no safety argument required |

The "DNN outputs are QM" line is the load-bearing trick: neural perception is
not certifiable to ASIL D, so it is treated as advisory and the ASIL-D budget
is spent on an independent monitor-plus-fallback. NVIDIA ships Orin with a
dedicated lockstep safety island; Tesla duplicates the whole computer -- both
bound the damage of a wrong main computer. The watchdog chain completes the
argument: sensor heartbeat, preprocessing aliveness, DNN output plausibility,
planner heartbeat, actuator-MCU watchdog, external supervisor -- any miss
drives the safe state (hold lane, decelerate) within the FTTI.

## Software: making heterogeneous silicon deterministic

| Middleware / OS | Role in the stack |
|---|---|
| ROS 2 | DDS-based messaging, QoS policies; de facto research standard |
| Apex.OS | API-compatible, determinism-hardened ROS 2 derivative for production |
| Autoware | open-source full AD stack built on ROS 2 |
| NVIDIA DriveOS | vendor OS: hypervisor, GPU/DLA scheduling, safety-separated partitions |
| QNX OS for Safety | POSIX RTOS with ASIL D certification, common under ADAS compute |
| AUTOSAR Adaptive | service-oriented in-vehicle middleware, bridges to classic ECUs |

Determinism on a CPU+GPU+DLA partition is the daily fight: control gets
fixed-priority or deadline scheduling on isolated CPU clusters (see
[real-time systems](./real-time-systems.md)); perception runs batched on GPU
and fixed-function DLA; the enemies are DVFS clock jitter, shared-memory
contention, and executor queuing. Mitigations: sensor-time timestamping,
preallocated DMA buffers, graph replay, time-triggered middleware phases.
Accelerator design: [hardware accelerators](../arch/advanced/accelerators.md).

The other software axis is what stays on the car versus what the fleet
provides: perception and control must be local, but HD maps, fleet-learned
policies, and shadow-mode evaluation are cloud tasks -- the
[edge computing](./edge-computing.md) pattern, and the reason AD fleets log
terabytes per vehicle per day. Infrastructure assists arrive via [V2X](./v2x.md).

## Power, thermals, and the TOPS honesty problem

Full-autonomy computers draw on the order of 100-500 W: robotaxi-class
machines need liquid cooling; L2+ units stay air-cooled below ~100 W. The
procurement metric, though, is TOPS -- where vendors exercise creative
freedom:

- **Precision base.** 2,000 TFLOPS FP8 (Thor, 2022) vs 1,000 INT8 TOPS /
  2,000 FP4 TFLOPS (current Thor materials): same story, three divisors.
- **Sparsity.** "With sparsity" assumes 2:4 structured sparsity real
  networks rarely exhibit end to end.
- **Utilization.** Peak assumes perfect problem fit; real pipelines see a
  fraction of it once memory-bound layers and pre/post processing take
  their cut. The survey below (ref. 6) works through this gap.
- **Board vs chip.** Tesla's 144 TOPS is a two-SoC board; Orin's 254 TOPS is
  one SoC. Both honest; comparing them as chips is not.

The demo prints saturation points because utilization ratios, not peak TOPS,
decide what a platform can run.

## Demo: sensor data budget and compute saturation calculator

The script sums raw ingest for two reference suites, then maps camera
megapixels to required TOPS using one verified anchor: ResNet-50 costs ~4.1
GFLOPs per 224x224 frame (He et al., CVPR 2016) = ~82 GOP/MP; K scales that anchor.

```python
#!/usr/bin/env python3
"""AV sensor data budget and compute saturation model.
VERIFIED anchors: Orin = 254 TOPS INT8 (NVIDIA newsroom, 2022);
ResNet-50 = ~4.1 GFLOPs per 224x224 frame (He et al., CVPR 2016) =
81.7 GOP/MP, the anchor for camera workload intensity K.
MODEL INPUTS: sensor formats/counts, GOP per lidar sweep, utilization u.
GB/s are decimal (1e9 bytes/s)."""
ORIN_TOPS = 254.0                                     # newsroom, Sep 2022
RESNET_K = 4.1e9 / ((224 * 224) / 1e6) / 1e9          # ~81.7 GOP/MP
CAM8, CAMHD = (3840, 2160, 30), (1920, 1080, 30)      # w, h, fps; RAW12
LIDAR = dict(pts_s=2_621_440, bpt=20, hz=10)          # 128ch x 2048 x 10 Hz
SUITES = {"L2+ ADAS (camera-only)": (3, 5, 0, 3, 6),  # (cam8MP, camHD,
          "L4 robotaxi suite":      (6, 4, 4, 5, 12)} #  lidar, radar, US

def main():
    print("VERIFIED anchors: Orin = 254 TOPS INT8 (NVIDIA newsroom); "
          f"ResNet-50 -> K = {RESNET_K:.1f} GOP/MP\n")
    print("Raw sensor ingest (decimal GB/s)")
    print(f"{'suite':24s} {'cams':>6s} {'lidar':>6s} {'radar':>6s} "
          f"{'total':>6s} {'TB/h':>6s}")
    mp_s = lid_tops = None
    for name, (c8, chd, nl, nr, nu) in SUITES.items():
        c = c8 * CAM8[0] * CAM8[1] * CAM8[2] * 1.5 / 1e9 \
            + chd * CAMHD[0] * CAMHD[1] * CAMHD[2] * 1.5 / 1e9
        l = nl * LIDAR["pts_s"] * LIDAR["bpt"] / 1e9
        r = nr * 0.003 + nu * 0.0002          # point-cloud output rates
        print(f"{name:24s} {c:6.2f} {l:6.2f} {r:6.3f} {c + l + r:6.2f} "
              f"{(c + l + r) * 3600 / 1000:6.1f}")
        if name.startswith("L4"):             # params for the compute model
            mp_s = (c8 * CAM8[0] * CAM8[1] * CAM8[2]
                    + chd * CAMHD[0] * CAMHD[1] * CAMHD[2]) / 1e6
            lid_tops = nl * LIDAR["hz"] * 20.0 / 1000.0
    print(f"\nL4 suite: {mp_s:.0f} MP/s of camera data, {lid_tops:.1f} TOPS lidar")
    print("Camera workload intensity K (GOP per megapixel) -> required TOPS:")
    print(f"{'K':>6s} {'anchor':>18s} {'camera':>8s} {'+lidar':>8s} "
          f"{'vs Orin peak':>13s}")
    for k, anchor in [(82, "ResNet-50 class"), (250, "detector x3"),
                      (500, "BEV/transformer"), (1000, "video transformer")]:
        cam_tops = mp_s * k / 1000.0
        print(f"{k:6d} {anchor:>18s} {cam_tops:8.0f} {cam_tops + lid_tops:8.0f}"
              f" {(cam_tops + lid_tops) / ORIN_TOPS:12.1f}x")
    print("\nWhere a 254-TOPS platform (Orin) saturates, L4 suite:")
    for u in (1.0, 0.4):
        k_star = (ORIN_TOPS * u - lid_tops) * 1000.0 / mp_s
        print(f"  u={u:.1f}: useful {ORIN_TOPS * u:5.0f} TOPS -> saturates at "
              f"K* = {k_star:5.1f} GOP/MP = {k_star / RESNET_K:4.2f}x ResNet-50")
    per = CAM8[0] * CAM8[1] * CAM8[2] / 1e6 * 250.0 / 1000.0
    for u in (1.0, 0.4):
        print(f"  u={u:.1f}, K=250: fits {ORIN_TOPS * u / per:4.1f} full-res "
              f"8.3 MP streams ({per:.0f} TOPS each)")

if __name__ == "__main__":
    main()
```

Output (verbatim):

```text
VERIFIED anchors: Orin = 254 TOPS INT8 (NVIDIA newsroom); ResNet-50 -> K = 81.7 GOP/MP

Raw sensor ingest (decimal GB/s)
suite                      cams  lidar  radar  total   TB/h
L2+ ADAS (camera-only)     1.59   0.00  0.010   1.60    5.7
L4 robotaxi suite          2.61   0.21  0.017   2.84   10.2

L4 suite: 1742 MP/s of camera data, 0.8 TOPS lidar
Camera workload intensity K (GOP per megapixel) -> required TOPS:
     K             anchor   camera   +lidar  vs Orin peak
    82    ResNet-50 class      143      144          0.6x
   250        detector x3      435      436          1.7x
   500    BEV/transformer      871      872          3.4x
  1000  video transformer     1742     1743          6.9x

Where a 254-TOPS platform (Orin) saturates, L4 suite:
  u=1.0: useful   254 TOPS -> saturates at K* = 145.4 GOP/MP = 1.78x ResNet-50
  u=0.4: useful   102 TOPS -> saturates at K* =  57.9 GOP/MP = 0.71x ResNet-50
  u=1.0, K=250: fits  4.1 full-res 8.3 MP streams (62 TOPS each)
  u=0.4, K=250: fits  1.6 full-res 8.3 MP streams (62 TOPS each)
```

At ResNet-50-class intensity the L4 suite needs ~144 dense TOPS -- 57% of a
254-TOPS Orin at perfect utilization, past its budget at a realistic 40%. A
BEV/transformer-class stack (K=500, a model-input guess) needs several Orins
of dense peak -- hence Thor-class parts, sparsity claims, precision relabeling.
The raw GB/s never bind: the accelerator sees tensors, not raw sensor bytes.

## Interview drill

- **Why is TOPS a weak procurement metric?** Precision base, sparsity,
  board-vs-chip accounting, utilization -- 2-10x of drift; see the demo.
- **How do you get ASIL D out of a non-certifiable DNN?** You do not:
  perception is QM, wrapped by an independently rated monitor (ISO 26262-9).
- **Safety island vs Tesla's duplicated SoCs?** Both bound the damage of a
  wrong computer: lockstep certifiable domain vs cross-checked duplication.
- **Where does the sensor bandwidth go?** The accelerator sees ISP tensors;
  most raw ingest is logged for fleet learning, not consumed by driving.
- **Lidar vs camera-only compute mix?** Camera-only stacks push more
  GOP/MP (depth from video); lidar stacks lean on direct range, shifting
  load toward 3D detection, fusion, and the planner.

## References

1. NVIDIA newsroom, "NVIDIA Unveils DRIVE Thor" (Sep 2022) -- https://nvidianews.nvidia.com/news/nvidia-unveils-drive-thor-centralized-car-computer-unifying-cluster-infotainment-automated-driving-and-parking-in-a-single-cost-saving-system
2. NVIDIA, In-Vehicle Computing page -- https://www.nvidia.com/en-us/solutions/autonomous-vehicles/in-vehicle-computing
3. Mobileye, "The Evolution of EyeQ" product page -- https://www.mobileye.com/technology/eyeq-chip
4. Cadence, "HOT CHIPS: The Tesla Full Self-Driving Computer" (Sep 2019) -- https://community.cadence.com/cadence_blogs_8/b/breakfast-bytes/posts/hc19-tesla (digest of the Hot Chips 31 Tesla presentation)
5. ISO 26262:2018, "Road vehicles -- Functional safety" -- https://www.iso.org/standard/68383.html
6. K. Power, "Hardware Accelerators in Autonomous Driving," arXiv:2308.06054 (2023) -- https://arxiv.org/abs/2308.06054
7. Horizon Robotics, Journey 6 Series page -- https://www.horizon.auto/en/solutions/horizon-journey/horizon-journey6
8. Intel editorial, "For Self-Driving Cars, There's Big Meaning Behind One Big Number: 4 Terabytes" (Apr 2017) -- https://www.intc.com/news-events/press-releases/detail/237/intel-editorial-for-self-driving-cars-theres-big
