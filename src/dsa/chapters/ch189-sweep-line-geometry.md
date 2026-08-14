# Chapter 189: Sweep-Line Geometry

The **sweep-line paradigm** processes geometric events in sorted order, maintaining an **active set** of currently relevant objects. It transforms O(n²) pairwise checks into O(n log n) by exploiting ordering.

---

## Core Idea

1. **Sort** all events (points, segment endpoints, intersections) by x-coordinate.
2. **Sweep** a vertical line left to right, maintaining an ordered set of active objects.
3. At each event, update the active set and process interactions.

---

## Line Segment Intersection

Detect if any two line segments intersect.

```cpp
struct Event {
    double x, y;
    int type; // 0 = start, 1 = end
    int seg_id;
    bool operator<(const Event& o) const {
        return tie(x, type, y) < tie(o.x, o.type, o.y);
    }
};

bool segmentsIntersect(vector<Segment>& segs) {
    vector<Event> events;
    for (int i = 0; i < (int)segs.size(); i++) {
        events.push_back({segs[i].x1, segs[i].y1, 0, i});
        events.push_back({segs[i].x2, segs[i].y2, 1, i});
    }
    sort(events.begin(), events.end());
    // Active set ordered by y-coordinate at current x
    set<pair<double,int>> active;
    for (auto& e : events) {
        if (e.type == 0) {
            auto it = active.insert({e.y, e.seg_id}).first;
            if (it != active.begin() && intersect(*prev(it), *it)) return true;
            if (next(it) != active.end() && intersect(*it, *next(it))) return true;
        } else {
            auto it = active.lower_bound({e.y, e.seg_id});
            if (it != active.begin() && next(it) != active.end())
                if (intersect(*prev(it), *next(it))) return true;
            active.erase(it);
        }
    }
    return false;
}
```

**Complexity:** O(n log n) time, O(n) space.

---

## Closest Pair of Points

Sort by x, sweep left to right. Maintain a strip of points within distance `d` of the sweep line. Only check against neighbors in y-order within the strip.

**Complexity:** O(n log n) (sort dominates).

---
## Applications

| Problem | Events | Active Structure |
|---|---|---|
| Segment intersection | Endpoints | Ordered set by y |
| Closest pair | Points (sorted by x) | Strip of candidates |
| Rectangle area union | Left/right edges | Interval tree or count |
| Manhattan MST | Points | Balanced BST |

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Floating-point precision in event sorting | Use epsilon comparisons or rational arithmetic |
| Forgetting to check neighbors on removal | When a segment is removed, its neighbors may now intersect |
| Using O(n²) pairwise checks | The sweep line exists precisely to avoid this |

---

## Practice Problems

| # | Problem | Hint |
|---|---|
| 1 | Number of Intersecting Segments | Count intersections, not just detect |
| 2 | Skyline Problem (LeetCode 218) | Sweep with max-heap for active buildings |
| 3 | Rectangle Area II (LeetCode 850) | Sweep vertical edges, active interval sum |
| 4 | Closest Pair (classic) | Sort + strip check |
| 5 | Union of Rectangles | Merge overlapping intervals during sweep |

---

## See Also

- [Chapter 93: Sweep Line](ch93-sweep-line.md)
- [Chapter 64: Geometry](ch64-geometry.md)
- [Chapter 190: Coordinate Geometry for CP](ch190-coordinate-geometry-cp.md)
- [Chapter 161: Advanced Geometry](ch161-adv-geometry.md)
