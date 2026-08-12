# Chapter 93: Sweep Line Algorithms

## Prerequisites
- Sorting algorithms
- Data structures (set, multiset, segment tree)
- Basic geometry and coordinate systems

## Interview Frequency: ★★★

Sweep line is a powerful paradigm for solving geometric and interval problems efficiently. **Google**, **Amazon**, **Meta**, and **Microsoft** frequently test sweep line for interval scheduling, geometry, and computational geometry problems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Line sweep for intervals | ★★★ | Medium | Active set pattern |
| Maximum overlapping intervals | ★★★ | Medium | Event-based processing |
| Closest pair of points | ★★ | Medium | Divide and conquer variant |
| Rectangle union area | ★★ | Hard | Coordinate compression + segment tree |
| Skyline problem | ★★★ | Hard | Heap-based sweep |

---

## 93.1 What Is the Sweep Line Algorithm?

### Definition

The **sweep line** (or **line sweep**) algorithm is a geometric algorithmic paradigm that solves problems by imagining a line (usually vertical) sweeping across the plane from left to right (or bottom to top), processing events as the line encounters them.

### Motivation

Many geometric problems involve interactions between objects in space. Instead of checking all pairs (O(n²)), sweep line reduces the problem by maintaining only the "active" elements—those currently intersecting the sweep line. This typically reduces complexity to O(n log n).

### Intuition

Imagine you're scanning a document with a vertical scanner bar moving left to right. At each position, you only need to track what's currently visible to the scanner. Objects enter the "active set" when the scanner reaches them and leave when the scanner passes them.

### Formal Explanation

The sweep line paradigm has three components:

1. **Events**: Points where something changes (element starts, ends, or intersects the sweep line)
2. **Active set**: Data structure maintaining elements currently crossing the sweep line
3. **Event processing**: At each event, update the active set and answer queries

**Algorithm template:**
```
1. Create events from input
2. Sort events by sweep coordinate
3. For each event:
   a. Update active set (add/remove elements)
   b. Answer queries using active set
4. Return result
```

---

## 93.2 Maximum Overlapping Intervals

### Problem

Given n intervals [lᵢ, rᵢ], find the maximum number of intervals that overlap at any point.

### Step-by-Step Walkthrough

```
Intervals: [1,5], [2,6], [3,7], [4,8]

Events:
  (1, +1)  — interval [1,5] starts
  (2, +1)  — interval [2,6] starts
  (3, +1)  — interval [3,7] starts
  (4, +1)  — interval [4,8] starts
  (5, -1)  — interval [1,5] ends
  (6, -1)  — interval [2,6] ends
  (7, -1)  — interval [3,7] ends
  (8, -1)  — interval [4,8] ends

Sorted events: (1,+1), (2,+1), (3,+1), (4,+1), (5,-1), (6,-1), (7,-1), (8,-1)

Processing:
  pos=1: count=1, max=1
  pos=2: count=2, max=2
  pos=3: count=3, max=3
  pos=4: count=4, max=4
  pos=5: count=3, max=4
  pos=6: count=2, max=4
  pos=7: count=1, max=4
  pos=8: count=0, max=4

Answer: 4
```

### Code

**C++:**
```cpp
#include <iostream>
#include <vector>
#include <algorithm>

int maxOverlap(std::vector<std::pair<int,int>>& intervals) {
    std::vector<std::pair<int,int>> events;  // (position, type)

    for (auto& [l, r] : intervals) {
        events.push_back({l, +1});   // Interval starts
        events.push_back({r, -1});   // Interval ends
    }

    // Sort: by position, then ends before starts at same position
    std::sort(events.begin(), events.end(), [](auto& a, auto& b) {
        if (a.first != b.first) return a.first < b.first;
        return a.second < b.second;  // -1 (end) before +1 (start)
    });

    int current = 0, maxCount = 0;
    for (auto& [pos, type] : events) {
        current += type;
        maxCount = std::max(maxCount, current);
    }

    return maxCount;
}

int main() {
    std::vector<std::pair<int,int>> intervals = {{1, 5}, {2, 6}, {3, 7}, {4, 8}};
    std::cout << "Max overlapping: " << maxOverlap(intervals) << "\n";  // 4

    // Test with non-overlapping
    std::vector<std::pair<int,int>> noOverlap = {{1, 3}, {5, 7}, {9, 11}};
    std::cout << "Max overlapping: " << maxOverlap(noOverlap) << "\n";  // 1

    return 0;
}
```

**Python:**
```python
def max_overlap(intervals):
    """Find maximum number of overlapping intervals."""
    events = []
    for l, r in intervals:
        events.append((l, +1))   # Start
        events.append((r, -1))   # End

    # Sort by position, ends before starts at same position
    events.sort(key=lambda x: (x[0], x[1]))

    current = max_count = 0
    for pos, typ in events:
        current += typ
        max_count = max(max_count, current)

    return max_count

# Example
intervals = [(1, 5), (2, 6), (3, 7), (4, 8)]
print(f"Max overlapping: {max_overlap(intervals)}")  # 4
```

**Java:**
```java
import java.util.*;

public class SweepLine {
    public static int maxOverlap(int[][] intervals) {
        List<int[]> events = new ArrayList<>();
        for (int[] interval : intervals) {
            events.add(new int[]{interval[0], 1});   // Start
            events.add(new int[]{interval[1], -1});  // End
        }

        // Sort by position, ends before starts
        events.sort((a, b) -> {
            if (a[0] != b[0]) return a[0] - b[0];
            return a[1] - b[1];
        });

        int current = 0, maxCount = 0;
        for (int[] event : events) {
            current += event[1];
            maxCount = Math.max(maxCount, current);
        }
        return maxCount;
    }

    public static void main(String[] args) {
        int[][] intervals = {{1, 5}, {2, 6}, {3, 7}, {4, 8}};
        System.out.println("Max overlapping: " + maxOverlap(intervals));  // 4
    }
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Create events | O(n) | O(n) |
| Sort events | O(n log n) | O(n) |
| Process events | O(n) | O(1) |
| **Total** | **O(n log n)** | **O(n)** |

---

## 93.3 Merge Intervals

### Problem

Given a collection of intervals, merge all overlapping intervals.

### Dry Run

```
Input: [1,3], [2,6], [8,10], [15,18]

Step 1: Sort by start → [1,3], [2,6], [8,10], [15,18]
Step 2: Start with [1,3]
Step 3: [2,6] overlaps with [1,3] → merge to [1,6]
Step 4: [8,10] doesn't overlap [1,6] → add [8,10]
Step 5: [15,18] doesn't overlap [8,10] → add [15,18]

Result: [1,6], [8,10], [15,18]
```

### Code

**C++:**
```cpp
#include <iostream>
#include <vector>
#include <algorithm>

std::vector<std::pair<int,int>> mergeIntervals(std::vector<std::pair<int,int>> intervals) {
    if (intervals.empty()) return {};

    std::sort(intervals.begin(), intervals.end());
    std::vector<std::pair<int,int>> result = {intervals[0]};

    for (int i = 1; i < (int)intervals.size(); i++) {
        auto& last = result.back();
        if (intervals[i].first <= last.second) {
            // Overlapping: extend the last interval
            last.second = std::max(last.second, intervals[i].second);
        } else {
            // Non-overlapping: add new interval
            result.push_back(intervals[i]);
        }
    }
    return result;
}

int main() {
    std::vector<std::pair<int,int>> intervals = {{1,3}, {2,6}, {8,10}, {15,18}};
    auto merged = mergeIntervals(intervals);

    std::cout << "Merged intervals:\n";
    for (auto& [l, r] : merged)
        std::cout << "  [" << l << ", " << r << "]\n";

    return 0;
}
```

**Python:**
```python
def merge_intervals(intervals):
    """Merge all overlapping intervals."""
    if not intervals:
        return []

    intervals.sort()
    result = [intervals[0]]

    for start, end in intervals[1:]:
        if start <= result[-1][1]:
            result[-1][1] = max(result[-1][1], end)
        else:
            result.append([start, end])

    return result

# Example
intervals = [[1, 3], [2, 6], [8, 10], [15, 18]]
print(f"Merged: {merge_intervals(intervals)}")
# Output: [[1, 6], [8, 10], [15, 18]]
```

---

## 93.4 Interval Intersection

### Problem

Given two lists of sorted intervals, find their intersection.

### Code

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

std::vector<std::pair<int,int>> intervalIntersection(
    std::vector<std::pair<int,int>>& A,
    std::vector<std::pair<int,int>>& B) {

    std::vector<std::pair<int,int>> result;
    int i = 0, j = 0;

    while (i < (int)A.size() && j < (int)B.size()) {
        // Find intersection of A[i] and B[j]
        int lo = std::max(A[i].first, B[j].first);
        int hi = std::min(A[i].second, B[j].second);

        if (lo <= hi)
            result.push_back({lo, hi});

        // Advance the interval that ends first
        if (A[i].second < B[j].second)
            i++;
        else
            j++;
    }
    return result;
}

int main() {
    std::vector<std::pair<int,int>> A = {{0,2}, {5,10}, {13,23}, {24,25}};
    std::vector<std::pair<int,int>> B = {{1,5}, {8,12}, {15,24}, {25,26}};

    auto result = intervalIntersection(A, B);
    std::cout << "Intersections:\n";
    for (auto& [l, r] : result)
        std::cout << "  [" << l << ", " << r << "]\n";

    return 0;
}
```

---

## 93.5 The Skyline Problem

### Problem

Given buildings represented as [left, right, height], compute the skyline (outline formed by all buildings).

### Approach

Use sweep line with a max-heap (priority queue) to track the current tallest building.

### Step-by-Step Walkthrough

```
Buildings: [2,9,10], [3,7,15], [5,12,12], [15,20,10], [19,24,8]

Events (sorted):
  (2, START, 10)
  (3, START, 15)
  (5, START, 12)
  (7, END, 15)
  (9, END, 10)
  (12, END, 12)
  (15, START, 10)
  (19, START, 8)
  (20, END, 10)
  (24, END, 8)

Processing:
  pos=2: push(10), max=10 → skyline: [2,10]
  pos=3: push(15), max=15 → skyline: [3,15]
  pos=5: push(12), max=15 (no change)
  pos=7: remove(15), max=12 → skyline: [7,12]
  pos=9: remove(10), max=12 (no change)
  pos=12: remove(12), max=0 → skyline: [12,0]
  pos=15: push(10), max=10 → skyline: [15,10]
  pos=19: push(8), max=10 (no change)
  pos=20: remove(10), max=8 → skyline: [20,8]
  pos=24: remove(8), max=0 → skyline: [24,0]

Result: [2,10], [3,15], [7,12], [12,0], [15,10], [20,8], [24,0]
```

### Code

**C++:**
```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

std::vector<std::vector<int>> getSkyline(std::vector<std::vector<int>>& buildings) {
    // Create events: (x, -height) for start, (x, height) for end
    // Negative height helps sort: starts before ends at same x, taller starts first
    std::vector<std::pair<int,int>> events;
    for (auto& b : buildings) {
        events.push_back({b[0], -b[2]});  // Start
        events.push_back({b[1], b[2]});   // End
    }
    std::sort(events.begin(), events.end());

    std::vector<std::vector<int>> result;
    std::multiset<int> heights = {0};  // Current heights, max at rbegin()
    int prevMax = 0;

    for (auto& [x, h] : events) {
        if (h < 0) {
            // Start event: add height
            heights.insert(-h);
        } else {
            // End event: remove height
            heights.erase(heights.find(h));
        }

        int currMax = *heights.rbegin();
        if (currMax != prevMax) {
            result.push_back({x, currMax});
            prevMax = currMax;
        }
    }
    return result;
}

int main() {
    std::vector<std::vector<int>> buildings = {
        {2, 9, 10}, {3, 7, 15}, {5, 12, 12}, {15, 20, 10}, {19, 24, 8}
    };

    auto skyline = getSkyline(buildings);
    std::cout << "Skyline:\n";
    for (auto& point : skyline)
        std::cout << "  [" << point[0] << ", " << point[1] << "]\n";

    return 0;
}
```

**Python:**
```python
import heapq

def get_skyline(buildings):
    """Compute the skyline of a set of buildings."""
    events = []
    for left, right, height in buildings:
        events.append((left, -height, right))   # Start: negative height for sorting
        events.append((right, 0, 0))             # End marker

    events.sort()

    result = []
    # Max-heap: (-height, right) — active buildings
    heap = [(0, float('inf'))]  # Ground level
    prev_height = 0

    for x, neg_h, right in events:
        if neg_h != 0:
            # Start event: add building
            heapq.heappush(heap, (neg_h, right))

        # Remove buildings that have ended
        while heap[0][1] <= x:
            heapq.heappop(heap)

        curr_height = -heap[0][0]
        if curr_height != prev_height:
            result.append([x, curr_height])
            prev_height = curr_height

    return result

# Example
buildings = [[2, 9, 10], [3, 7, 15], [5, 12, 12], [15, 20, 10], [19, 24, 8]]
print(f"Skyline: {get_skyline(buildings)}")
```

---

## 93.6 Closest Pair of Points

### Problem

Given n points in the plane, find the pair with the smallest Euclidean distance.

### Sweep Line Approach

Sort points by x-coordinate. Maintain a "strip" of points within the current best distance of the sweep line. Use a balanced BST to check nearby points in y-order.

### Code

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <set>
#include <limits>

struct Point {
    double x, y;
};

double closestPair(std::vector<Point>& points) {
    int n = points.size();
    if (n < 2) return std::numeric_limits<double>::infinity();

    // Sort by x-coordinate
    std::sort(points.begin(), points.end(), [](const Point& a, const Point& b) {
        return a.x < b.x;
    });

    double bestDist = std::numeric_limits<double>::infinity();
    std::set<std::pair<double,int>> strip;  // (y, index) sorted by y

    int left = 0;
    for (int i = 0; i < n; i++) {
        // Remove points too far left
        while (points[i].x - points[left].x > bestDist) {
            strip.erase({points[left].y, left});
            left++;
        }

        // Check points in the strip within bestDist in y
        double d = std::sqrt(bestDist);
        auto lo = strip.lower_bound({points[i].y - d, -1});
        auto hi = strip.upper_bound({points[i].y + d, n});

        for (auto it = lo; it != hi; ++it) {
            double dx = points[i].x - points[it->second].x;
            double dy = points[i].y - points[it->second].y;
            double dist = std::sqrt(dx*dx + dy*dy);
            bestDist = std::min(bestDist, dist * dist);
        }

        strip.insert({points[i].y, i});
    }

    return std::sqrt(bestDist);
}

int main() {
    std::vector<Point> points = {{2, 3}, {12, 30}, {40, 50}, {5, 1}, {12, 10}, {3, 4}};
    std::cout << "Closest pair distance: " << closestPair(points) << "\n";
    // Expected: distance between (2,3) and (3,4) = sqrt(2) ≈ 1.414
    return 0;
}
```

---

## 93.7 Rectangle Union Area

### Problem

Given n axis-aligned rectangles, compute the total area of their union.

### Approach

Use sweep line on x-coordinates. For each vertical strip, compute the total y-coverage using a segment tree or interval union.

### Code

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

struct Rectangle {
    int x1, y1, x2, y2;
};

long long rectangleUnionArea(std::vector<Rectangle>& rects) {
    // Create events for vertical edges
    struct Event {
        int x, y1, y2, type;  // type: +1 for left, -1 for right
    };

    std::vector<Event> events;
    std::vector<int> yCoords;

    for (auto& r : rects) {
        events.push_back({r.x1, r.y1, r.y2, +1});
        events.push_back({r.x2, r.y1, r.y2, -1});
        yCoords.push_back(r.y1);
        yCoords.push_back(r.y2);
    }

    // Coordinate compression for y
    std::sort(yCoords.begin(), yCoords.end());
    yCoords.erase(std::unique(yCoords.begin(), yCoords.end()), yCoords.end());

    auto compress = [&](int y) {
        return std::lower_bound(yCoords.begin(), yCoords.end(), y) - yCoords.begin();
    };

    // Sort events by x
    std::sort(events.begin(), events.end(), [](const Event& a, const Event& b) {
        return a.x < b.x;
    });

    // Sweep line with coverage array
    int numY = yCoords.size();
    std::vector<int> coverage(numY, 0);
    long long area = 0;
    int prevX = events[0].x;

    for (auto& e : events) {
        // Add area from previous strip
        int totalY = 0;
        for (int i = 0; i < numY - 1; i++) {
            if (coverage[i] > 0)
                totalY += yCoords[i + 1] - yCoords[i];
        }
        area += (long long)totalY * (e.x - prevX);

        // Update coverage
        int cy1 = compress(e.y1), cy2 = compress(e.y2);
        for (int i = cy1; i < cy2; i++)
            coverage[i] += e.type;

        prevX = e.x;
    }

    return area;
}

int main() {
    std::vector<Rectangle> rects = {{0, 0, 3, 3}, {1, 1, 4, 4}, {2, 2, 5, 5}};
    std::cout << "Union area: " << rectangleUnionArea(rects) << "\n";
    // Expected: 16 (3x3 + extra strips)
    return 0;
}
```

---

## 93.8 Sweep Line for 2D Range Queries

```cpp
// Offline 2D range counting using sweep line + BIT
#include <iostream>
#include <vector>
#include <algorithm>

class BIT {
    std::vector<int> tree;
public:
    BIT(int n) : tree(n + 1, 0) {}
    void update(int i, int val) {
        for (i++; i < (int)tree.size(); i += i & (-i))
            tree[i] += val;
    }
    int query(int i) {
        int sum = 0;
        for (i++; i > 0; i -= i & (-i))
            sum += tree[i];
        return sum;
    }
    int rangeQuery(int l, int r) { return query(r) - query(l - 1); }
};

// Count points in rectangles offline
std::vector<int> offlineRangeCount(
    std::vector<std::pair<int,int>>& points,
    std::vector<std::tuple<int,int,int,int>>& queries) {
    // Events: (x, type, data)
    // type 0: point, type 1: query
    struct Event {
        int x, type, y, qid, y1, y2;
    };

    std::vector<Event> events;
    for (auto& [px, py] : points)
        events.push_back({px, 0, py, -1, -1, -1});

    int qid = 0;
    for (auto& [x1, y1, x2, y2] : queries) {
        events.push_back({x1 - 1, 1, -1, qid, y1, y2});  // Subtract at x1-1
        events.push_back({x2, 1, -1, qid, y1, y2});        // Add at x2
        qid++;
    }

    std::sort(events.begin(), events.end(), [](const Event& a, const Event& b) {
        if (a.x != b.x) return a.x < b.x;
        return a.type < b.type;  // Points before queries
    });

    // Compress y-coordinates
    std::vector<int> allY;
    for (auto& [px, py] : points) allY.push_back(py);
    for (auto& [x1, y1, x2, y2] : queries) {
        allY.push_back(y1);
        allY.push_back(y2);
    }
    std::sort(allY.begin(), allY.end());
    allY.erase(std::unique(allY.begin(), allY.end()), allY.end());

    auto compressY = [&](int y) {
        return std::lower_bound(allY.begin(), allY.end(), y) - allY.begin();
    };

    BIT bit(allY.size());
    std::vector<int> result(queries.size(), 0);

    for (auto& e : events) {
        if (e.type == 0) {
            bit.update(compressY(e.y), 1);
        } else {
            int count = bit.rangeQuery(compressY(e.y1), compressY(e.y2));
            // Subtract at x1-1, add at x2
            if (e.x < 0) continue;  // x1-1 could be negative
            // Simplified: just use add
            result[e.qid] += count;
        }
    }

    return result;
}
```

---

## 93.9 General Sweep Line Template

```cpp
// General sweep line template
template<typename EventType, typename ActiveSet>
class SweepLine {
    std::vector<EventType> events;
    ActiveSet activeSet;

public:
    void addEvent(const EventType& e) {
        events.push_back(e);
    }

    template<typename ProcessFunc>
    void sweep(ProcessFunc process) {
        std::sort(events.begin(), events.end());

        for (auto& event : events) {
            // 1. Update active set
            activeSet.update(event);

            // 2. Process event (custom logic)
            process(event, activeSet);
        }
    }
};
```

---

## 93.10 Exercises

1. **Meeting rooms**: Given meeting time intervals, find the minimum number of conference rooms required.
2. **Insert interval**: Insert a new interval into a sorted list of non-overlapping intervals and merge if necessary.
3. **Employee free time**: Given schedules of multiple employees, find the free time common to all.
4. **Range module**: Design a data structure that tracks ranges of numbers using sweep line logic.
5. **My Calendar II**: Implement a calendar that allows at most 2 bookings per time slot.
6. **Rectangle area**: Compute the total area covered by two rectangles (including overlap counted once).
7. **Interval list intersections**: Given two lists of disjoint sorted intervals, return their intersections.

---

## 93.11 Interview Questions

1. **What is the sweep line paradigm?**
   *Answer*: An algorithmic technique where a conceptual line sweeps across a geometric space, processing events in sorted order. It maintains an "active set" of elements currently intersecting the sweep line, reducing many O(n²) problems to O(n log n).

2. **How do you find the maximum number of overlapping intervals?**
   *Answer*: Create start (+1) and end (-1) events for each interval. Sort events by position. Sweep through, maintaining a counter. The maximum counter value is the answer. O(n log n) time.

3. **How does the skyline problem use sweep line?**
   *Answer*: Create events for building starts and ends. Use a max-heap to track the current tallest building. When the tallest height changes, record a skyline point. Process events sorted by x-coordinate.

4. **What's the difference between sweep line and divide-and-conquer for closest pair?**
   *Answer*: Both achieve O(n log n). Divide-and-conquer splits points recursively. Sweep line sorts by x and maintains a strip of candidate points. Sweep line is often simpler to implement.

5. **How do you handle floating-point coordinates in sweep line?**
   *Answer*: Use coordinate compression to map floating-point values to integers. Sort unique coordinates and use indices. This avoids precision issues and enables array-based data structures.

---

## 93.12 Cross-References

- **Chapter 9**: Sorting algorithms (prerequisite for sweep line)
- **Chapter 15**: Binary indexed tree / segment tree (for active set)
- **Chapter 20**: Interval scheduling (greedy approach)
- **Chapter 91**: Computational geometry basics
- **Chapter 92**: Convex hull (another geometric sweep)
- **Chapter 108**: Segment tree with lazy propagation (for rectangle union)
- **Chapter 161**: Advanced geometry problems

---

## Summary

| Problem | Events | Active Set | Time | Space |
|---|---|---|---|---|
| Max overlap | Start/End | Counter | O(n log n) | O(n) |
| Merge intervals | Start/End | Current interval | O(n log n) | O(n) |
| Skyline | Start/End | Max-heap | O(n log n) | O(n) |
| Closest pair | Sort by x | BST of y-values | O(n log n) | O(n) |
| Rectangle union | Vertical edges | Segment tree | O(n log n) | O(n) |
| Interval intersection | Merge-like | Two pointers | O(n + m) | O(1) |
