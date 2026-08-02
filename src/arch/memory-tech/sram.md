# SRAM (Static Random-Access Memory)

## Overview

**SRAM** (Static RAM) is the fastest type of volatile semiconductor memory, used primarily for CPU caches (L1, L2, L3) and register files. "Static" means it retains data as long as power is supplied — no refresh circuitry is needed.

## How SRAM Works

### 6-Transistor (6T) Cell

Each SRAM bit is stored using **6 transistors** arranged as a bistable latch (cross-coupled inverters):

```
        VDD
         │
    ┌────┴────┐
    │  Inv 1  │──────┐
    │         │      │
    ├─────────┤      ├──── Bit Line (BL)
    │         │      │
    │  Inv 2  │──────┘
    └────┬────┘
         │
        GND

Two access transistors connect to BL and BL_bar
```

The cross-coupled inverters form a **flip-flop** that holds the bit. Access transistors connect the cell to bit lines for reading/writing.

### Read Operation
1. Bit lines precharged to VDD/2
2. Access transistors activated (word line goes high)
3. Cell pulls one bit line high, the other low
4. Sense amplifier detects the differential

### Write Operation
1. Bit lines driven to desired values
2. Access transistors activated
3. Cell flips to match bit line values

## SRAM Characteristics

| Property | Value |
|----------|-------|
| Transistors per bit | 6 |
| Access time | 0.5–2 ns |
| Density | Low (~100 Mbit/cm² in modern processes) |
| Power (static) | Low (leakage only) |
| Power (dynamic) | Moderate |
| Refresh needed | No |
| Volatile | Yes |
| Cost per bit | Very high |

## Why SRAM for Caches?

1. **Speed**: 0.5–2 ns access time matches CPU cycle time
2. **No refresh**: Data available immediately, no timing constraints
3. **Simple interface**: Direct access, no row/column activation sequence
4. **Predictable timing**: No variable latency from refresh or row buffer hits

## SRAM vs DRAM

| Property | SRAM | DRAM |
|----------|------|------|
| Transistors/bit | 6 | 1 (+ capacitor) |
| Access time | ~1 ns | ~50-100 ns |
| Density | Low | High |
| Refresh | No | Yes (every 64 ms) |
| Cost/GB | ~$1000+ | ~$3-5 |
| Use | Caches, registers | Main memory |

## SRAM in Modern CPUs

| Component | Technology | Size |
|-----------|-----------|------|
| L1 Cache | High-speed SRAM | 32–64 KB per core |
| L2 Cache | Dense SRAM | 256 KB–1 MB per core |
| L3 Cache | Dense SRAM | 4–64 MB shared |
| Register File | Multi-ported SRAM | ~1 KB per core |
| TLB | CAM + SRAM | ~1 KB |

## SRAM Scaling Challenges

As process nodes shrink:
- **Leakage current** increases (transistors don't fully turn off)
- **Variability** increases (manufacturing variations affect threshold voltage)
- **Cell stability** decreases (smaller cells are harder to flip)
- **6T cell** doesn't scale as well as DRAM's 1T+1C

### Alternative SRAM Cells
- **8T SRAM**: 8 transistors for better read stability
- **10T SRAM**: 10 transistors for ultra-low voltage operation
- **Assist circuits**: Voltage boosting, write-back mechanisms

## Power Consumption

### Static Power (Leakage)
Even when not switching, SRAM transistors leak current:
```
P_static = V_DD × I_leakage
```
In modern processes, leakage is a significant portion of total cache power.

### Dynamic Power
When switching:
```
P_dynamic = α × C × V² × f
```
Where α = activity factor, C = capacitance, V = voltage, f = frequency.

## Interview Questions

1. **Q**: Why does SRAM have 6 transistors per bit while DRAM has only 1?
   **A**: SRAM uses a cross-coupled inverter pair (bistable latch) for storage, which requires 4 transistors plus 2 access transistors = 6T. DRAM uses 1 transistor and 1 capacitor, where the capacitor stores charge. DRAM is denser but needs refresh; SRAM is faster but larger.

2. **Q**: Why doesn't SRAM need refresh?
   **A**: SRAM stores data in a bistable latch (cross-coupled inverters). The latch is stable indefinitely as long as power is supplied. DRAM stores charge on a capacitor that leaks over time, requiring periodic refresh.

3. **Q**: Why is SRAM used for caches instead of DRAM?
   **A**: Speed. SRAM access time (~1 ns) matches CPU clock speeds. DRAM (~50-100 ns) is too slow for L1/L2 caches. The cost and density disadvantage is acceptable for small cache sizes.

4. **Q**: What is the main challenge with SRAM at smaller process nodes?
   **A**: Leakage current and variability. As transistors shrink, they leak more even when "off," and manufacturing variations become more significant relative to the transistor's characteristics. This makes it harder to maintain stable, low-power SRAM cells.

## Common Mistakes

- ❌ Confusing SRAM and DRAM (SRAM = static, no refresh; DRAM = dynamic, needs refresh)
- ❌ Assuming SRAM is always better (it's much more expensive and less dense)
- ❌ Forgetting that SRAM is volatile (loses data without power)
- ❌ Not knowing the 6-transistor cell structure

## Summary

SRAM uses 6 transistors per bit to form a bistable latch. It's the fastest volatile memory (~1 ns), used for CPU caches and registers. No refresh is needed. The trade-off is low density and high cost. Scaling challenges include leakage and variability at smaller process nodes.

## Cross-References

- [DRAM](dram.md) — Main memory technology
- [Cache Basics](../memory-hierarchy/cache-basics.md) — How SRAM is used in caches
- [Memory Hierarchy](../memory-hierarchy/README.md) — Where SRAM fits
- [HBM](hbm.md) — High-bandwidth memory alternative
