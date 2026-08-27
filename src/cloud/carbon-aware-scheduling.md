# Carbon-Aware and Energy-Aware Scheduling

A data center's carbon footprint is, overwhelmingly, an electricity problem: most of a fleet's
lifetime emissions come from the power it draws, and the carbon content of that power is not a
constant — it varies by region *and by hour* by more than an order of magnitude. That variance
is an opportunity: if the scheduler can see grid carbon intensity as an input, alongside CPU,
memory, and cost, it can move flexible work to clean hours and clean regions. This page covers
the measurement model (carbon intensity, PUE), the two scheduling levers (temporal and spatial
shifting), the emissions-accounting debate that decides whether shifting actually helps, and
how it all lands in Kubernetes. For the cost-side twin of this topic, see
[FinOps and Cloud Cost](../sre/finops-cloud-cost.md).

## How dirty is a kilowatt-hour?

Grid carbon intensity is measured in grams of CO2-equivalent per kilowatt-hour (gCO2eq/kWh),
counting lifecycle emissions of the generation mix feeding a location at a point in time. The
spread is enormous: hydro- and nuclear-heavy zones (France, Sweden, Quebec) sit around 20-60,
while coal- and gas-heavy zones (India, Poland, parts of Australia and the US) run 600-800 —
roughly 10-40x. The same zone swings 2-5x *within a day* as solar rises, wind picks up, and
thermal plants ramp for the evening.

Where do the numbers come from? Electricity Maps (the reference dataset most tooling plugs
into) partitions the world into grid zones, ingests hourly generation and load data from
transmission operators and public agencies, and then **flow-traces** physical imports and
exports between zones — so a French border region consuming German coal power is charged for
the coal, not for France's nuclear fleet. The result is *consumption-based* intensity per zone
per hour, plus forward forecasts. WattTime takes a different slice of the same problem
(marginal emissions — below). Any scheduler that wants a carbon signal starts by picking one
of these feeds and an API polling cadence (typically 5-60 minutes).

## PUE: the multiplier nobody in software controls

Power Usage Effectiveness is the ratio of total facility power to IT power. A PUE of 1.5 means
every joule reaching your pods is accompanied by half a joule of cooling, conversion, and
distribution overhead. Hyperscale fleets run about 1.1; typical enterprise halls sit at
1.5-1.8. The scheduling arithmetic is simply:

```text
kgCO2eq = kWh_IT x PUE x carbon_intensity(g/kWh) / 1000
```

PUE scales the whole bill, so it matters — but it is a property of the facility, fixed at build
time and moved only by capital projects. Carbon intensity moves by the hour. That asymmetry is
the core argument for scheduling: intensity varies 10x+, PUE varies maybe 20% over years.

## Temporal shifting: run when the grid is clean

The cheapest lever for deadline-flexible work: delay, split, or accelerate jobs so their energy
lands in clean hours. The shape of the opportunity depends on the grid's generation mix:

```text
 gCO2eq/kWh
        NNN NN  <- run-ASAP: ml-train h03-07
 610 |                #                                            #  #
 570 |    #  #  #  #  #  #                                   #  #  #  #  #  #
 530 | #  #  #  #  #  #  #  #                                #  #  #  #  #  #
 490 | #  #  #  #  #  #  #  #                             #  #  #  #  #  #  #
 450 | #  #  #  #  #  #  #  #  #                       #  #  #  #  #  #  #  #
 410 | #  #  #  #  #  #  #  #  #                       #  #  #  #  #  #  #  #
 370 | #  #  #  #  #  #  #  #  #  #                 #  #  #  #  #  #  #  #  #
 330 | #  #  #  #  #  #  #  #  #  #  #              #  #  #  #  #  #  #  #  #
 290 | #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #  #
     +----------------------------------------------------------------------> hour
                                                    SSS SSS SSS SSS
        <- shifted run h11-15 sits in the solar trough
       00    02    04    06    08    10    12    14    16    18    20    22
```

Two real-world shapes matter. On solar-heavy grids the trough is midday and the peak is the
evening ramp (exactly what the chart shows). On wind-heavy grids intensity is often
*anticorrelated* with the sun — clean at night — so "shift to daylight" is wrong; the curve
must be read per zone. Not everything can move:

| Workload class          | Deferrable by      | Carbon lever                     |
|-------------------------|--------------------|----------------------------------|
| ML training, offline ETL| hours to days      | temporal shift (biggest win)     |
| VOD transcoding         | hours              | temporal + spatial               |
| Reports, cron, backups  | minutes to hours   | temporal shift                   |
| Interactive APIs        | no                 | spatial, right-sizing            |
| Stateful stores         | no                 | utilization, hardware lifetime   |

The elasticity column is the whole game: a platform team that can attach a deadline to even
30% of its compute can capture most of the achievable savings, because interactive and
stateful workloads were never shiftable anyway.

## Spatial shifting: follow the clean power, within residency

Between regions the lever becomes placement: route the next batch job to the region whose
*forecast* intensity is lowest for the window. Google's carbon-intelligent computing platform
(production since 2021) does exactly this inside its fleet: machine-learned hourly carbon
forecasts per data-center region feed a capacity-aware scheduler that shifts *flexible*
workloads toward cleaner locations, subject to latency, capacity, and availability constraints
— their write-up stresses customer-visible behavior did not change. The IEEE Transactions on
Power Systems paper behind the platform describes the forecasting and shifting architecture in
detail; a follow-up post covers shifting load in *time* as well, including demand-response
coordination with grids.

Hard limits keep spatial shifting honest:

- **Data residency**: GDPR and sector rules pin some workloads to jurisdictions, not regions.
- **Latency**: user-facing serving cannot drift to a clean-but-distant region.
- **State gravity**: petabyte datasets do not move for a 30 g/kWh saving; egress fees and
  copy time dominate.
- **Saturation**: chasing clean power concentrates load; the scheduler must still respect
  local capacity, or the provider fires up peakers and the benefit evaporates.

In practice spatial shifting is a tiebreaker among eligible regions rather than a free move.

## Average vs marginal: what does shifting actually save?

Here the field splits, and knowing the split is what interviewers probe. *Average* intensity
(flow-traced, as Electricity Maps publishes) says what mix supported your consumption.
*Marginal* intensity (WattTime's specialty) says which *plant changed output* because you
showed up — usually the last-dispatched fossil unit, even on a clean grid. The two disagree
most exactly when schedulers act: at midday in a solar-heavy zone, average intensity is at its
minimum, but the marginal plant may be a gas unit still ramping, or curtailed solar — in which
case shifting a job into midday saves nothing (the solar was wasted anyway) or displaces gas
(saves a lot). WattTime's own comparison lays out the argument that time-shifting decisions
should price marginal emissions, while annual *reporting* is stuck with averages because
marginal accounting does not sum to a footprint. The pragmatic platform stance: average for
disclosure, marginal for scheduling decisions, and never claim precision the feed cannot
support.

## Operational vs embodied carbon

Electricity is *operational* carbon. Building the server, the rack, and the building emitted
*embodied* carbon up front — estimates commonly put hardware manufacture around 10-30% of a
fleet's lifetime footprint (higher for idling-rich fleets). Two scheduling consequences: a
utilized server is not just cheaper, it amortizes embodied carbon over more useful work, and
extending server lifetimes (or refusing to refresh for refresh's sake) avoids whole
embodied-carbon batches. Energy-aware scheduling that merely packs more work onto existing
machines is therefore a double win; scheduling that justifies new hardware rarely is.

## Where this lands in Kubernetes

Nothing in upstream Kubernetes knows about the grid today, so platforms assemble the loop from
four kinds of parts:

| Layer            | Tool / mechanism                          | Role                                     |
|------------------|-------------------------------------------|------------------------------------------|
| Carbon signal    | GSF Carbon Aware SDK (WebAPI + CLI)       | one API over grid feeds; forecast queries |
| Energy telemetry | Kepler (eBPF exporter, CNCF)              | per-pod joules, feeds the carbon math     |
| Batch scaling    | Azure carbon-aware KEDA operator          | scales KEDA ScaledObjects on forecasts    |
| Placement        | custom scheduler-framework Score plugin   | biases pod placement by region intensity  |
| Reporting        | Cloud Carbon Footprint                    | cloud emissions estimates incl. PUE       |

Concretely: the [Carbon Aware SDK](https://github.com/Green-Software-Foundation/carbon-aware-sdk)
exposes carbon data as an HTTP service so any controller can consume it; the Azure operator
wraps that SDK in a KEDA-compatible controller that scales batch consumers up in clean windows
and down in dirty ones; and a custom Kubernetes Score plugin is the standard hook for
"prefer the clean region" placement, since the scheduling framework lets each plugin contribute
a score per node per pod. The GSF's pattern catalog (demand shifting, workload shaping) is the
vocabulary these integrations converge on.

## Platform-team checklist

1. Attach explicit deadlines to batch workloads; a job without a deadline cannot be shifted.
2. Pick a carbon feed and cache it; never call grid APIs from a scheduling hot path.
3. Decide the accounting stance: average for reports, marginal for shifting decisions.
4. Multiply by PUE before claiming numbers, and document whose PUE.
5. Gate spatial shifting on residency, latency, and egress policy — encode them as placement
   constraints, not wiki notes.
6. Instrument before and after (Kepler or cloud estimates); unfalsifiable green claims rot.
7. Watch for pollution shifting: deferring jobs into wind-heavy nights can raise *local*
   curtailment or fail deadlines; keep an SLO guard on every shifting policy.
8. Prefer utilization gains and hardware-lifetime extension — they cut embodied carbon too.
9. Make it a controller, not a runbook: carbon-aware scheduling that requires a human at 2 a.m.
   will not survive the on-call rotation.

## Runnable: shift-the-batch simulation

The model below builds a synthetic solar-shaped 24h curve, then schedules eight jobs two ways:
naively at arrival, and greedily in the lowest-intensity window that still meets the deadline.
It shows both the headline saving and the honest spread — tight-deadline jobs save nothing:

```python
# Temporal load shifting: greedy carbon-aware schedule vs run-ASAP baseline.
# Synthetic 24h grid carbon intensity (gCO2eq/kWh), solar-shaped.
INTENSITY = [
    555, 570, 585, 595, 605, 610, 600, 560,   # 00-07h: dark, thermal-heavy
    480, 400, 330, 290, 275, 285, 320, 380,   # 08-15h: solar belt
    450, 520, 570, 600, 615, 620, 600, 575,   # 16-23h: evening ramp
]
JOBS = [  # (id, arrival_h, duration_h, finish_by_h, power_kW)
    ("etl-a",    0, 3,  6, 400),
    ("video-b",  2, 2,  9, 250),
    ("ml-train", 3, 4, 24, 900),
    ("etl-c",    5, 3, 14, 400),
    ("report",   7, 2, 11, 150),
    ("ml-eval",  9, 3, 17, 600),
    ("db-sync", 11, 2, 16, 200),
    ("etl-d",   13, 3, 24, 400),
]

def cost(h, dur, kw):
    return kw * sum(INTENSITY[h:h + dur]) / 1000.0     # kg CO2eq

lo, hi = min(INTENSITY), max(INTENSITY)
print(f"curve: min {lo} at h{INTENSITY.index(lo):02d}, max {hi} at h"
      f"{INTENSITY.index(hi):02d}, avg {sum(INTENSITY)/24:.0f}\n")

naive = aware = 0.0
print("job        naive  kgCO2   best  kgCO2   saved")
for jid, arr, dur, dl, kw in JOBS:
    n = cost(arr, dur, kw)                       # baseline: start ASAP
    starts = range(arr, dl - dur + 1)            # finish by h=dl (exclusive)
    best = min(starts, key=lambda h: cost(h, dur, kw))
    b = cost(best, dur, kw)
    naive += n; aware += b
    print(f"{jid:<9}  h{arr:02d}-{arr+dur:02d} {n:>6.1f}   h{best:02d}"
          f"-{best+dur:02d} {b:>6.1f}  {100.0*(n-b)/n:>6.1f}%")

saved = 100.0 * (naive - aware) / naive
print(f"\ntotal: naive {naive:,.0f} kg vs aware {aware:,.0f} kg "
      f"-> {saved:.1f}% carbon saved")
```

Real output:

```text
curve: min 275 at h12, max 620 at h21, avg 500

job        naive  kgCO2   best  kgCO2   saved
etl-a      h00-03  684.0   h00-03  684.0     0.0%
video-b    h02-04  295.0   h07-09  260.0    11.9%
ml-train   h03-07 2169.0   h11-15 1053.0    51.5%
etl-c      h05-08  708.0   h11-14  340.0    52.0%
report     h07-09  156.0   h09-11  109.5    29.8%
ml-eval    h09-12  612.0   h11-14  510.0    16.7%
db-sync    h11-13  113.0   h12-14  112.0     0.9%
etl-d      h13-16  394.0   h13-16  394.0     0.0%

total: naive 5,131 kg vs aware 3,462 kg -> 32.5% carbon saved
```

A third of the fleet's carbon removed by *only moving when jobs run* — and the per-job rows
explain the mechanism: savings concentrate in the slack-rich, high-power jobs (`ml-train`,
`etl-c`) while deadline-pinned `etl-a` and `etl-d` contribute exactly nothing. That mix is the
realistic result, not marketing rounding.

## References

- [Google Cloud: Carbon-intelligent computing platform (2021 launch)](https://cloud.google.com/blog/topics/sustainability/carbon-intelligent-computing-platform)
- [Radovanović et al., Carbon-Aware Computing for Datacenters (IEEE Trans. Power Systems; arXiv preprint)](https://arxiv.org/abs/2106.11750)
- [Green Software Foundation: Carbon Aware SDK](https://github.com/Green-Software-Foundation/carbon-aware-sdk)
- [Electricity Maps: data and methodology (zones, flow-tracing)](https://www.electricitymaps.com/data/methodology)
- [WattTime: Average vs. Marginal Emissions](https://watttime.org/data-science/data-signals/average-vs-marginal)
