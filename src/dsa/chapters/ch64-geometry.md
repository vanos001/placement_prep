# Chapter 64: Computational Geometry

## Prerequisites

- Basic math (vectors, dot product, cross product)
- Sorting algorithms
- Stack data structure
- Binary search

## Interview Frequency: ★★

Computational geometry appears in interviews at **Google**, **Meta**, **Amazon**, and companies working with maps/GIS (Uber, Lyft, Google Maps). Convex hull and line sweep are the most common. Orientation tests are fundamental building blocks. These problems are less frequent than standard DSA but are excellent differentiators.

| Topic | Frequency | Typical Companies | Difficulty |
|---|---|---|---|
| Orientation Test | ★★★ | Google, Amazon | Easy |
| Cross Product | ★★★ | Google, Amazon | Easy-Medium |
| Convex Hull | ★★★ | Google, Uber, Lyft | Medium |
| Line Sweep | ★★ | Google, Meta | Medium-Hard |
| Point in Polygon | ★★ | Uber, Google Maps | Medium |
| Rotating Calipers | ★ | Google, competitive programming | Hard |

---

## 64.1 Orientation Test

The **orientation test** determines whether three points make a clockwise turn, counterclockwise turn, or are collinear.

### Cross Product Approach

Given points P, Q, R:
```
val = (Q.y - P.y) * (R.x - Q.x) - (Q.x - P.x) * (R.y - Q.y)
```

| Value | Orientation |
|---|---|
| val > 0 | Clockwise |
| val < 0 | Counterclockwise |
| val = 0 | Collinear |

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

struct Point {
    long long x, y;
    
    Point operator-(const Point& other) const {
        return {x - other.x, y - other.y};
    }
    
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    
    bool operator<(const Point& other) const {
        return x < other.x || (x == other.x && y < other.y);
    }
};

// Cross product of vectors (b-a) and (c-a)
long long cross(const Point& a, const Point& b, const Point& c) {
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

// Orientation: +1 (CCW), -1 (CW), 0 (collinear)
int orientation(const Point& a, const Point& b, const Point& c) {
    long long val = cross(a, b, c);
    if (val > 0) return 1;  // CCW
    if (val < 0) return -1; // CW
    return 0;               // Collinear
}

// Check if point q lies on segment pr
bool onSegment(const Point& p, const Point& q, const Point& r) {
    return q.x <= std::max(p.x, r.x) && q.x >= std::min(p.x, r.x) &&
           q.y <= std::max(p.y, r.y) && q.y >= std::min(p.y, r.y);
}

// Do segments (p1,q1) and (p2,q2) intersect?
bool segmentsIntersect(const Point& p1, const Point& q1, 
                       const Point& p2, const Point& q2) {
    int o1 = orientation(p1, q1, p2);
    int o2 = orientation(p1, q1, q2);
    int o3 = orientation(p2, q2, p1);
    int o4 = orientation(p2, q2, q1);
    
    // General case
    if (o1 != o2 && o3 != o4) return true;
    
    // Special cases (collinear)
    if (o1 == 0 && onSegment(p1, p2, q1)) return true;
    if (o2 == 0 && onSegment(p1, q2, q1)) return true;
    if (o3 == 0 && onSegment(p2, p1, q2)) return true;
    if (o4 == 0 && onSegment(p2, q1, q2)) return true;
    
    return false;
}

int main() {
    Point a = {0, 0}, b = {4, 4}, c = {1, 1};
    
    std::cout << "Orientation of (0,0), (4,4), (1,1): " 
              << orientation(a, b, c) << " (collinear)\n";
    
    Point d = {4, 0};
    std::cout << "Orientation of (0,0), (4,4), (4,0): " 
              << orientation(a, b, d) << " (CW)\n";
    
    Point e = {0, 4};
    std::cout << "Orientation of (0,0), (4,4), (0,4): " 
              << orientation(a, b, e) << " (CCW)\n";
    
    // Segment intersection
    Point p1 = {0, 0}, q1 = {4, 4};
    Point p2 = {0, 4}, q2 = {4, 0};
    std::cout << "\nSegments (0,0)-(4,4) and (0,4)-(4,0) " 
              << (segmentsIntersect(p1, q1, p2, q2) ? "intersect" : "don't intersect") 
              << "\n";
    
    Point p3 = {5, 5}, q3 = {6, 6};
    std::cout << "Segments (0,0)-(4,4) and (5,5)-(6,6) " 
              << (segmentsIntersect(p1, q1, p3, q3) ? "intersect" : "don't intersect") 
              << "\n";
    
    return 0;
}
```

---

## 64.2 Cross Product

### 2D Cross Product

The cross product of vectors (a₁, a₂) and (b₁, b₂) is:

```
a × b = a₁ * b₂ - a₂ * b₁
```

**Geometric meaning**: The magnitude equals the area of the parallelogram formed by the two vectors. The sign indicates the direction of rotation.

### 3D Cross Product

```
a × b = (a₂b₃ - a₃b₂, a₃b₁ - a₁b₃, a₁b₂ - a₂b₁)
```

```cpp
#include <iostream>
#include <cmath>

struct Vec2 {
    double x, y;
    
    double cross(const Vec2& other) const {
        return x * other.y - y * other.x;
    }
    
    double dot(const Vec2& other) const {
        return x * other.x + y * other.y;
    }
    
    double length() const {
        return std::sqrt(x * x + y * y);
    }
};

struct Vec3 {
    double x, y, z;
    
    Vec3 cross(const Vec3& other) const {
        return {y * other.z - z * other.y,
                z * other.x - x * other.z,
                x * other.y - y * other.x};
    }
    
    double dot(const Vec3& other) const {
        return x * other.x + y * other.y + z * other.z;
    }
};

int main() {
    // 2D cross product
    Vec2 a = {3, 4}, b = {2, 1};
    std::cout << "2D cross product: " << a.cross(b) << "\n";
    std::cout << "Area of parallelogram: " << std::abs(a.cross(b)) << "\n";
    
    // Angle between vectors
    double cosAngle = a.dot(b) / (a.length() * b.length());
    double angle = std::acos(cosAngle) * 180.0 / M_PI;
    std::cout << "Angle between vectors: " << angle << " degrees\n";
    
    // 3D cross product
    Vec3 c = {1, 0, 0}, d = {0, 1, 0};
    Vec3 e = c.cross(d);
    std::cout << "\n3D cross product of (1,0,0) × (0,1,0): (" 
              << e.x << "," << e.y << "," << e.z << ")\n";
    
    return 0;
}
```

### Cross Product Applications

| Application | How |
|---|---|
| Orientation | Sign of cross product |
| Area of polygon | Sum of cross products |
| Convex hull | Direction of turn |
| Point in triangle | All cross products same sign |
| Angle between vectors | atan2(cross, dot) |

---

## 64.3 Convex Hull

The **convex hull** of a set of points is the smallest convex polygon containing all points. Think of it as a rubber band stretched around all points.

### Graham Scan

1. Find the bottom-most point (pivot)
2. Sort all other points by polar angle with pivot
3. Process points, maintaining a stack of hull vertices
4. Pop from stack if a right turn is detected

### Andrew's Monotone Chain

1. Sort points by (x, y)
2. Build lower hull (left to right)
3. Build upper hull (right to left)
4. Combine

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <stack>
#include <cmath>

struct Point {
    long long x, y;
    
    bool operator<(const Point& other) const {
        return x < other.x || (x == other.x && y < other.y);
    }
    
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

long long cross(const Point& O, const Point& A, const Point& B) {
    return (A.x - O.x) * (B.y - O.y) - (A.y - O.y) * (B.x - O.x);
}

// Andrew's Monotone Chain - O(n log n)
std::vector<Point> convexHull(std::vector<Point> points) {
    int n = points.size();
    if (n <= 1) return points;
    
    std::sort(points.begin(), points.end());
    
    std::vector<Point> hull;
    
    // Build lower hull
    for (int i = 0; i < n; i++) {
        while (hull.size() >= 2 && 
               cross(hull[hull.size()-2], hull[hull.size()-1], points[i]) <= 0) {
            hull.pop_back();
        }
        hull.push_back(points[i]);
    }
    
    // Build upper hull
    int lowerSize = hull.size();
    for (int i = n - 2; i >= 0; i--) {
        while ((int)hull.size() > lowerSize && 
               cross(hull[hull.size()-2], hull[hull.size()-1], points[i]) <= 0) {
            hull.pop_back();
        }
        hull.push_back(points[i]);
    }
    
    // Remove last point (same as first)
    hull.pop_back();
    
    return hull;
}

// Graham Scan - O(n log n)
std::vector<Point> grahamScan(std::vector<Point> points) {
    int n = points.size();
    if (n <= 2) return points;
    
    // Find bottom-most point
    int minIdx = 0;
    for (int i = 1; i < n; i++) {
        if (points[i].y < points[minIdx].y || 
            (points[i].y == points[minIdx].y && points[i].x < points[minIdx].x)) {
            minIdx = i;
        }
    }
    std::swap(points[0], points[minIdx]);
    Point pivot = points[0];
    
    // Sort by polar angle
    std::sort(points.begin() + 1, points.end(), [&pivot](const Point& a, const Point& b) {
        long long c = cross(pivot, a, b);
        if (c == 0) {
            // Collinear: closer point first
            long long d1 = (a.x - pivot.x) * (a.x - pivot.x) + 
                           (a.y - pivot.y) * (a.y - pivot.y);
            long long d2 = (b.x - pivot.x) * (b.x - pivot.x) + 
                           (b.y - pivot.y) * (b.y - pivot.y);
            return d1 < d2;
        }
        return c > 0;
    });
    
    std::vector<Point> hull;
    for (int i = 0; i < n; i++) {
        while (hull.size() >= 2 && 
               cross(hull[hull.size()-2], hull[hull.size()-1], points[i]) <= 0) {
            hull.pop_back();
        }
        hull.push_back(points[i]);
    }
    
    return hull;
}

double polygonArea(const std::vector<Point>& poly) {
    double area = 0;
    int n = poly.size();
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        area += poly[i].x * poly[j].y;
        area -= poly[j].x * poly[i].y;
    }
    return std::abs(area) / 2.0;
}

int main() {
    std::vector<Point> points = {{0, 0}, {4, 0}, {4, 4}, {0, 4}, 
                                  {2, 2}, {1, 1}, {3, 1}, {3, 3}};
    
    auto hull = convexHull(points);
    
    std::cout << "Convex hull vertices:\n";
    for (auto& p : hull) {
        std::cout << "  (" << p.x << ", " << p.y << ")\n";
    }
    
    std::cout << "Hull area: " << polygonArea(hull) << "\n";
    
    // Graham scan
    auto hull2 = grahamScan(points);
    std::cout << "\nGraham scan hull:\n";
    for (auto& p : hull2) {
        std::cout << "  (" << p.x << ", " << p.y << ")\n";
    }
    
    return 0;
}
```

### Convex Hull Algorithms Comparison

| Algorithm | Time | Space | Notes |
|---|---|---|---|
| Graham Scan | O(n log n) | O(n) | Sort by angle |
| Andrew's Monotone Chain | O(n log n) | O(n) | Sort by coordinates |
| Jarvis March | O(nh) | O n | h = hull size, good for small h |
| Chan's Algorithm | O(n log h) | O(n) | Optimal |
| QuickHull | O(n log n) avg | O(n) | Like QuickSort |

---

## 64.4 Line Sweep

**Line Sweep** processes geometric events in sorted order, maintaining a data structure for the current state.

### Closest Pair of Points

Find the two closest points among n points in O(n log n).

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <float.h>
#include <iomanip>

struct Point {
    double x, y;
    int idx;
};

double dist(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y;
    return std::sqrt(dx * dx + dy * dy);
}

// Divide and conquer approach - O(n log n)
double closestPair(std::vector<Point>& points, int left, int right) {
    if (right - left <= 3) {
        double minDist = DBL_MAX;
        for (int i = left; i < right; i++) {
            for (int j = i + 1; j < right; j++) {
                minDist = std::min(minDist, dist(points[i], points[j]));
            }
        }
        return minDist;
    }
    
    int mid = (left + right) / 2;
    double midX = points[mid].x;
    
    double d = std::min(closestPair(points, left, mid),
                        closestPair(points, mid, right));
    
    // Merge step: check points near the dividing line
    std::vector<Point> strip;
    for (int i = left; i < right; i++) {
        if (std::abs(points[i].x - midX) < d) {
            strip.push_back(points[i]);
        }
    }
    
    std::sort(strip.begin(), strip.end(), [](const Point& a, const Point& b) {
        return a.y < b.y;
    });
    
    for (int i = 0; i < (int)strip.size(); i++) {
        for (int j = i + 1; j < (int)strip.size() && 
             (strip[j].y - strip[i].y) < d; j++) {
            d = std::min(d, dist(strip[i], strip[j]));
        }
    }
    
    return d;
}

int main() {
    std::vector<Point> points = {{2, 3}, {12, 30}, {40, 50}, {5, 1}, 
                                  {12, 10}, {3, 4}, {7, 8}, {9, 2}};
    
    std::sort(points.begin(), points.end(), [](const Point& a, const Point& b) {
        return a.x < b.x;
    });
    
    double minDist = closestPair(points, 0, points.size());
    
    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Closest pair distance: " << minDist << "\n";
    
    return 0;
}
```

### Line Sweep for Rectangle Union Area

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

struct Event {
    double x;
    double y1, y2;
    int type; // +1 for left edge, -1 for right edge
    
    bool operator<(const Event& other) const {
        return x < other.x;
    }
};

// Simplified rectangle union area using line sweep
double rectangleUnionArea(std::vector<std::vector<double>>& rectangles) {
    // rectangles[i] = {x1, y1, x2, y2}
    std::vector<Event> events;
    for (auto& r : rectangles) {
        events.push_back({r[0], r[1], r[3], 1});  // Left edge
        events.push_back({r[2], r[1], r[3], -1}); // Right edge
    }
    
    std::sort(events.begin(), events.end());
    
    double area = 0;
    double prevX = events[0].x;
    std::multiset<std::pair<double, double>> active; // (y1, y2)
    
    for (auto& e : events) {
        // Calculate area since last event
        double dx = e.x - prevX;
        if (dx > 0 && !active.empty()) {
            // Compute total y-coverage
            double totalY = 0;
            double lastEnd = -1e18;
            for (auto& [y1, y2] : active) {
                if (y1 > lastEnd) {
                    totalY += y2 - y1;
                    lastEnd = y2;
                } else if (y2 > lastEnd) {
                    totalY += y2 - lastEnd;
                    lastEnd = y2;
                }
            }
            area += dx * totalY;
        }
        
        if (e.type == 1) {
            active.insert({e.y1, e.y2});
        } else {
            active.erase(active.find({e.y1, e.y2}));
        }
        
        prevX = e.x;
    }
    
    return area;
}

int main() {
    std::vector<std::vector<double>> rects = {
        {0, 0, 3, 3},
        {1, 1, 4, 4},
        {2, 2, 5, 5}
    };
    
    std::cout << "Rectangle union area: " << rectangleUnionArea(rects) << "\n";
    
    return 0;
}
```

---

## 64.5 Point in Polygon

### Ray Casting Algorithm

Cast a ray from the point to infinity. Count how many polygon edges it crosses. If odd, the point is inside; if even, outside.

```cpp
#include <iostream>
#include <vector>
#include <cmath>

struct Point {
    double x, y;
};

// Ray casting: count intersections with ray going right from point
bool pointInPolygon(const Point& p, const std::vector<Point>& poly) {
    int n = poly.size();
    bool inside = false;
    
    for (int i = 0, j = n - 1; i < n; j = i++) {
        if (((poly[i].y > p.y) != (poly[j].y > p.y)) &&
            (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / 
                    (poly[j].y - poly[i].y) + poly[i].x)) {
            inside = !inside;
        }
    }
    
    return inside;
}

int main() {
    // Square polygon
    std::vector<Point> polygon = {{0, 0}, {4, 0}, {4, 4}, {0, 4}};
    
    std::vector<Point> testPoints = {{2, 2}, {5, 5}, {0, 0}, {1, 3}, {-1, -1}};
    
    for (auto& p : testPoints) {
        std::cout << "(" << p.x << ", " << p.y << "): " 
                  << (pointInPolygon(p, polygon) ? "inside" : "outside") << "\n";
    }
    
    // Concave polygon (L-shape)
    std::vector<Point> concave = {{0, 0}, {4, 0}, {4, 2}, {2, 2}, {2, 4}, {0, 4}};
    
    std::cout << "\nL-shaped polygon:\n";
    std::vector<Point> test2 = {{1, 1}, {3, 3}, {1, 3}};
    for (auto& p : test2) {
        std::cout << "(" << p.x << ", " << p.y << "): " 
                  << (pointInPolygon(p, concave) ? "inside" : "outside") << "\n";
    }
    
    return 0;
}
```

---

## 64.6 Rotating Calipers (Overview)

**Rotating Calipers** is a technique for solving problems on convex polygons by maintaining two parallel "caliper" lines that rotate around the polygon.

### Applications

| Problem | Time | Description |
|---|---|---|
| Diameter of convex polygon | O(n) | Farthest pair of points |
| Minimum width | O(n) | Minimum distance between parallel lines |
| Minimum bounding rectangle | O(n) | Smallest rectangle containing polygon |
| Maximum distance between two convex polygons | O(n + m) | Farthest pair across polygons |

### Key Idea

1. Start with two parallel lines (e.g., horizontal)
2. Rotate them, always touching two edges of the hull
3. At each step, the "width" or "distance" changes predictably
4. Process all O(n) edge pairs

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

struct Point {
    long long x, y;
    
    Point operator-(const Point& other) const {
        return {x - other.x, y - other.y};
    }
    
    long long cross(const Point& other) const {
        return x * other.y - y * other.x;
    }
    
    long long dist2() const {
        return x * x + y * y;
    }
};

double dist(const Point& a, const Point& b) {
    return std::sqrt((double)(a - b).dist2());
}

// Diameter of convex polygon using rotating calipers
double convexPolygonDiameter(const std::vector<Point>& hull) {
    int n = hull.size();
    if (n <= 1) return 0;
    if (n == 2) return dist(hull[0], hull[1]);
    
    double maxDist = 0;
    int j = 1;
    
    for (int i = 0; i < n; i++) {
        int ni = (i + 1) % n;
        
        // Advance j while area increases
        while (true) {
            int nj = (j + 1) % n;
            Point edge = hull[ni] - hull[i];
            long long curr = std::abs(edge.cross(hull[j] - hull[i]));
            long long next = std::abs(edge.cross(hull[nj] - hull[i]));
            if (next > curr) {
                j = nj;
            } else {
                break;
            }
        }
        
        maxDist = std::max(maxDist, dist(hull[i], hull[j]));
        maxDist = std::max(maxDist, dist(hull[ni], hull[j]));
    }
    
    return maxDist;
}

int main() {
    // Convex hull of a rectangle
    std::vector<Point> hull = {{0, 0}, {4, 0}, {4, 3}, {0, 3}};
    
    std::cout << "Diameter of convex polygon: " 
              << convexPolygonDiameter(hull) << "\n"; // Should be 5 (diagonal)
    
    // Regular pentagon (approximate)
    std::vector<Point> pentagon;
    for (int i = 0; i < 5; i++) {
        double angle = 2 * M_PI * i / 5;
        pentagon.push_back({(long long)(100 * std::cos(angle)), 
                           (long long)(100 * std::sin(angle))});
    }
    
    std::cout << "Diameter of pentagon: " 
              << convexPolygonDiameter(pentagon) << "\n";
    
    return 0;
}
```

---

## Summary

| Technique | Key Insight | Time | Use Case |
|---|---|---|---|
| Orientation Test | Cross product sign | O(1) | Turn direction |
| Cross Product | Area of parallelogram | O(1) | Angle, area, orientation |
| Convex Hull | Andrew's/Graham | O(n log n) | Smallest enclosing polygon |
| Line Sweep | Process events in order | O(n log n) | Closest pair, union area |
| Point in Polygon | Ray casting | O(n) | Containment test |
| Rotating Calipers | Two parallel lines rotating | O(n) | Diameter, width |

### When NOT to Use Computational Geometry

| Situation | Why Not | Better Alternative |
|---|---|---|
| Integer coordinates only | Floating-point issues | Integer arithmetic with cross product |
| Very small n (≤ 5) | Simple brute force suffices | Direct computation |
| No geometric structure | Geometry overkill | Standard DSA |
| High dimensions (3D+) | Complexity explodes | Specialized libraries |
| Approximate answers OK | Exact geometry is slow | Sampling/heuristics |

### Geometry Trade-offs

| Technique | Pro | Con |
|---|---|---|
| Graham Scan | O(n log n), simple | Needs pivot selection |
| Andrew's Monotone Chain | O(n log n), no angle sort | Same complexity as Graham |
| Jarvis March | O(nh), good for small hull | O(n²) worst case |
| Ray Casting | Simple point-in-polygon | Edge cases on boundary |
| Rotating Calipers | O(n) after hull | Only for convex polygons |
| Line Sweep | Handles many problems | Complex implementation |
| Integer cross product | Exact, no floating-point | Limited to integer coordinates |
