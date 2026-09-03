# Speed, Distance & Time

Speed, distance, and time problems are a staple of aptitude tests. They involve trains, boats, relative motion, and average speed calculations.

## Core Formula

```
Distance = Speed × Time
Speed = Distance / Time
Time = Distance / Speed
```

### Unit Conversions

| From | To | Multiply by |
|------|-----|-------------|
| km/h → m/s | ÷ 3.6 | 5/18 |
| m/s → km/h | × 3.6 | 18/5 |
| km/h → m/min | ÷ 60 × 1000 | 1000/60 |

**Quick conversion:**
```
72 km/h = 72 × 5/18 = 20 m/s
15 m/s = 15 × 18/5 = 54 km/h
```

## Average Speed

### Equal Distances, Different Speeds

If a person covers distance d at speed s₁ and the same distance d at speed s₂:

```
Average speed = 2s₁s₂/(s₁+s₂) [Harmonic Mean]
```

**Example:** Travel 100 km at 50 km/h, return 100 km at 50 km/h:
```
Average = 2×50×50/(50+50) = 5000/100 = 50 km/h
```

**Example:** Travel 100 km at 40 km/h, return at 60 km/h:
```
Average = 2×40×60/(40+60) = 4800/100 = 48 km/h
```

**Important:** Average speed is NOT the arithmetic mean (which would be 50 here).

### Equal Times, Different Speeds

If a person travels at speed s₁ for time t, then at speed s₂ for time t:

```
Average speed = (s₁+s₂)/2 [Arithmetic Mean]
```

### Three Segments (Equal Distances)

```
Average speed = 3s₁s₂s₃/(s₁s₂+s₂s₃+s₃s₁)
```

## Relative Speed

### Same Direction (Chasing)

```
Relative speed = |s₁ - s₂|
```

### Opposite Direction (Approaching)

```
Relative speed = s₁ + s₂
```

**Example:** Two trains at 60 km/h and 40 km/h in the same direction:
```
Relative speed = 60 - 40 = 20 km/h
```

Same trains approaching each other:
```
Relative speed = 60 + 40 = 100 km/h
```

## Train Problems

### Train Crossing a Pole/Person

Time = Length of train / Speed of train

**Example:** A 200m train at 72 km/h crosses a pole.
```
Speed = 72 × 5/18 = 20 m/s
Time = 200/20 = 10 seconds
```

### Train Crossing a Platform/Bridge

Time = (Length of train + Length of platform) / Speed

**Example:** A 300m train at 36 km/h crosses a 150m platform.
```
Speed = 36 × 5/18 = 10 m/s
Time = (300+150)/10 = 45 seconds
```

### Two Trains Crossing Each Other

**Opposite direction:**
```
Time = (L₁ + L₂) / (s₁ + s₂)
```

**Same direction:**
```
Time = (L₁ + L₂) / |s₁ - s₂|
```

**Example:** Two trains of 200m and 300m at 72 km/h and 54 km/h cross each other (opposite direction):
```
Relative speed = (72+54) × 5/18 = 126 × 5/18 = 35 m/s
Time = (200+300)/35 = 500/35 = 14.29 seconds
```

### Train Passing Through Another Train (Same Direction)

**Example:** A 200m train at 72 km/h overtakes a 150m train at 36 km/h.
```
Relative speed = (72-36) × 5/18 = 10 m/s
Time = (200+150)/10 = 35 seconds
```

## Boats and Streams

### Key Terms

| Term | Meaning |
|------|---------|
| Speed in still water (u) | Boat's own speed |
| Speed of stream (v) | Current speed |
| Downstream speed | u + v |
| Upstream speed | u - v |

### Formulas

```
Speed in still water = (Downstream + Upstream) / 2
Speed of stream = (Downstream - Upstream) / 2
```

**Example:** A boat goes 24 km downstream in 3 hours and 24 km upstream in 6 hours.
```
Downstream speed = 24/3 = 8 km/h
Upstream speed = 24/6 = 4 km/h
Still water speed = (8+4)/2 = 6 km/h
Stream speed = (8-4)/2 = 2 km/h
```

### Time Ratio

```
Time upstream / Time downstream = (u+v)/(u-v)
```

For the same distance:
```
T_up/T_down = (u+v)/(u-v)
```

**Example:** If downstream speed = 10, upstream = 6, same distance:
```
T_up/T_down = 10/6 = 5/3
```

### Finding Distance (Boat Problem)

**Problem:** A boat goes 16 km upstream in 4 hours and 16 km downstream in 2 hours. Find the speed of the stream and the speed of the boat in still water.

**Solution:**
```
Let b = boat speed in still water, s = stream speed.
Upstream speed   = b − s = 16 km / 4 h = 4 km/h
Downstream speed = b + s = 16 km / 2 h = 8 km/h

Solve the two equations:
  b − s = 4
  b + s = 8
  → b = 6 km/h, s = 2 km/h

Stream speed = 2 km/h
Still-water speed = 6 km/h
```

**Sanity check:** With b=6, s=2: upstream = 4 km/h → 16/4 = 4 h ✓; downstream = 8 km/h → 16/8 = 2 h ✓.

> **Key relations:** If `u` = upstream speed and `d` = downstream speed, then `b = (u+d)/2` and `s = (d−u)/2`.

## Circular Motion

### Meeting on a Circular Track

**Same direction:**
```
Time to meet = Track length / |s₁ - s₂|
```

**Opposite direction:**
```
Time to meet = Track length / (s₁ + s₂)
```

### Number of Meetings

**Same direction:** In time T, they meet T × |s₁-s₂|/L times (where L = track length)

**Opposite direction:** In time T, they meet T × (s₁+s₂)/L times

**Example:** Track = 400m, A at 5 m/s, B at 3 m/s (same direction):
```
Time to first meet = 400/(5-3) = 200 seconds
In 1 hour (3600s): 3600/200 = 18 meetings
```

## Escalator Problems

### Concept

Escalator problems are similar to boats and streams:
- Walking speed = person's own speed
- Escalator speed = stream speed
- Same direction (walking up on up-escalator) = speeds add
- Opposite direction = speeds subtract

**Problem:** A person takes 20 steps on a stationary escalator and 10 steps on a moving escalator (both times reaching the top). How many visible steps on the escalator?

**Solution:**
```
Let escalator speed = e steps/second, person speed = p steps/second
Stationary: 20 steps, time = 20/p
Moving: 10 steps by person, escalator adds (e/p)×10 steps
Total steps = 10 + 10e/p
From stationary case: total = 20
20 = 10 + 10e/p → e/p = 1 → escalator speed = person speed
Total visible steps = 20
```

## Speed & Time Ratio Problems

### If Speed Ratio is a:b

For the same distance:
```
Time ratio = b:a (inverse)
```

**Example:** If A's speed is 3/2 of B's speed, and they travel the same distance:
```
Time_A : Time_B = 2:3
```

### If Time Ratio is a:b

For the same distance:
```
Speed ratio = b:a (inverse)
```

## Tricks & Shortcuts

### Trick 1: Quick km/h to m/s

Multiply by 5/18:
```
36 km/h = 36 × 5/18 = 10 m/s
54 km/h = 54 × 5/18 = 15 m/s
72 km/h = 72 × 5/18 = 20 m/s
90 km/h = 90 × 5/18 = 25 m/s
108 km/h = 108 × 5/18 = 30 m/s
```

### Trick 2: Average Speed for Three Equal Distances

If three equal distances at s₁, s₂, s₃:
```
Avg = 3/(1/s₁ + 1/s₂ + 1/s₃)
```

### Trick 3: If A Reaches x Minutes Early and y Minutes Late

If at speed s₁, A is x minutes late, and at speed s₂, A is y minutes early:
```
Distance = s₁ × s₂ × (x+y) / (s₂-s₁)  [times in same units]
```

### Trick 4: Train Problem Shortcut

If a train of length L crosses a pole in t₁ seconds and a platform of length P in t₂ seconds:
```
L/t₁ = (L+P)/t₂
P = L(t₂-t₁)/t₁
```

### Trick 5: Boat Round Trip

Time for round trip of distance d:
```
T = d/(u+v) + d/(u-v) = 2du/(u²-v²)
```

## Practice Questions

### Q1: Average Speed
A car travels from A to B at 40 km/h and returns at 60 km/h. Find average speed.

**Solution:**
```
Average = 2×40×60/(40+60) = 4800/100 = 48 km/h
```

### Q2: Train Crossing
A 150m train at 54 km/h crosses a 250m platform. Find time.

**Solution:**
```
Speed = 54 × 5/18 = 15 m/s
Time = (150+250)/15 = 400/15 = 26.67 seconds
```

### Q3: Two Trains
Two trains of 120m and 80m travel at 60 km/h and 40 km/h in opposite directions. Find crossing time.

**Solution:**
```
Relative speed = (60+40) × 5/18 = 100 × 5/18 = 27.78 m/s
Time = (120+80)/27.78 = 200/27.78 = 7.2 seconds
```

### Q4: Boat Problem
A boat goes 30 km downstream in 3 hours and returns in 5 hours. Find speed in still water.

**Solution:**
```
Downstream = 30/3 = 10 km/h
Upstream = 30/5 = 6 km/h
Still water = (10+6)/2 = 8 km/h
Stream = (10-6)/2 = 2 km/h
```

### Q5: Relative Speed
A 100m train at 36 km/h overtakes a man walking at 4 km/h in the same direction. Find time.

**Solution:**
```
Relative speed = (36-4) × 5/18 = 32 × 5/18 = 8.89 m/s
Time = 100/8.89 = 11.25 seconds
```

### Q6: Meeting Problem
A and B start from two places 100 km apart. A at 20 km/h, B at 30 km/h (towards each other). When do they meet?

**Solution:**
```
Relative speed = 20 + 30 = 50 km/h
Time = 100/50 = 2 hours
```

### Q7: Mixed Journey
A person travels 200 km: first 100 km at 50 km/h, next 50 km at 25 km/h, last 50 km at 10 km/h. Find average speed.

**Solution:**
```
Time = 100/50 + 50/25 + 50/10 = 2 + 2 + 5 = 9 hours
Average speed = 200/9 = 22.22 km/h
```

### Q8: Escalator

**Problem:** A person walks up an escalator that is moving *down*. Walking at normal speed they count 30 steps before reaching the top; walking at twice the speed they count 20 steps. How many steps are visible on the escalator?

**Solution:**

```
Let N = visible steps on the escalator
Let e = escalator speed (steps/sec), p = person's normal walking speed (steps/sec)
Sign convention: walking up is positive, so a downward escalator
contributes −e per second of progress.

At speed p:
  Time to reach top   = 30 / p seconds
  Steps contributed by escalator during that time = −e · (30 / p)
  N = 30 − 30·(e/p)                         ... (1)

At speed 2p:
  Time to reach top   = 20 / (2p) = 10 / p seconds
  Steps contributed by escalator = −e · (10 / p)
  N = 20 − 10·(e/p)                         ... (2)

Equate (1) and (2):
  30 − 30·(e/p) = 20 − 10·(e/p)
  10 = 20·(e/p)
  e/p = 1/2      (escalator runs at half the person's normal walking speed)

Substitute back into (1):
  N = 30 − 30·(1/2) = 30 − 15 = 15
  Cross-check with (2):  N = 20 − 10·(1/2) = 15  ✓

Visible steps on the escalator = 15.
```

**Why the count drops when walking faster:** when the person walks faster, they spend less time on the escalator, so the downward escalator has less time to "subtract" steps. Yet they still reach the top — meaning fewer of their own steps are needed. The two effects reconcile at a single value of N, which is what the equation solves for.

## Summary Table

| Concept | Formula |
|---------|---------|
| Basic | D = S × T |
| km/h → m/s | × 5/18 |
| m/s → km/h | × 18/5 |
| Avg speed (2 equal dist) | 2s₁s₂/(s₁+s₂) |
| Avg speed (2 equal time) | (s₁+s₂)/2 |
| Relative (same dir) | s₁ - s₂ |
| Relative (opp dir) | s₁ + s₂ |
| Train + pole | Time = L/S |
| Train + platform | Time = (L+P)/S |
| Downstream | u + v |
| Upstream | u - v |
| Still water | (D+U)/2 |
| Stream speed | (D-U)/2 |
