# Chapter 161: Advanced Computational Geometry

## Prerequisites
- Convex hull (Chapter 156)
- Sweep line basics (Chapter 157)
- Binary search trees
- Divide and conquer

## Interview Frequency: ★★

Advanced computational geometry problems appear at companies building mapping, robotics, CAD, and game engines. While rare in standard interviews, they test strong algorithmic thinking and mathematical maturity.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| Voronoi Diagrams | ★ | Hard | Nearest neighbor partitioning |
| Delaunay Triangulation | ★ | Hard | Mesh generation, dual of Voronoi |
| Half-Plane Intersection | ★★ | Hard | Linear programming, convex regions |
| Range Trees | ★★ | Medium | Multi-dimensional queries |
| BSP Trees | ★ | Medium | Rendering, spatial partitioning |

---

## 161.1 What Is a Voronoi Diagram?

### Definition

Given a set of *n* points called **sites** in the plane, the **Voronoi diagram** partitions the plane into *n* regions (cells). Each cell V(pᵢ) contains all points in the plane that are closer to site pᵢ than to any other site pⱼ (j ≠ i).

Formally:

```
V(pᵢ) = { x ∈ ℝ² : dist(x, pᵢ) ≤ dist(x, pⱼ) for all j ≠ i }
```

### Motivation

Imagine you want to build a hospital in a city. You want every resident to be closest to *your* hospital. The Voronoi cell of your hospital shows exactly which residents you serve. Voronoi diagrams model **nearest-neighbor regions** and appear in:

- **Cell tower placement**: Each tower's coverage region
- **Ecology**: Territories of competing species
- **Meteorology**: Rainfall interpolation from weather stations
- **Robotics**: Motion planning and obstacle regions
- **Computer graphics**: Procedural textures, point cloud analysis

### Properties

- Each Voronoi cell is a **convex polygon** (possibly unbounded)
- The diagram has **O(n)** vertices, edges, and faces
- Each vertex is equidistant from exactly 3 sites (in general position)
- The **dual** of a Voronoi diagram is the **Delaunay triangulation**
- Edge between cells V(pᵢ) and V(pⱼ) is the perpendicular bisector of segment pᵢpⱼ

### Intuition

Think of each site as a stone dropped in a pond at the same time. The expanding ripples from each stone meet at the Voronoi edges. The boundary between two ripples is exactly the perpendicular bisector of the line segment connecting the two stones.

### Algorithm: Fortune's Sweep Line

The standard O(n log n) algorithm uses a sweep line that moves from left to right:

1. **Beach line**: A curve composed of parabolic arcs, each associated with a site
2. **Events**: Site events (new parabolic arc added) and circle events (arc disappears)
3. **Data structures**: A balanced BST for the beach line, a priority queue for events

### Brute Force: Nearest Site Query

For understanding and small inputs, we can find the nearest site for any query point in O(n) time:

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

struct Point {
    double x, y;
    Point() : x(0), y(0) {}
    Point(double x, double y) : x(x), y(y) {}
};

double distSq(const Point& a, const Point& b) {
    double dx = a.x - b.x, dy = a.y - b.y;
    return dx * dx + dy * dy;
}

// Returns index of nearest site to query point q
int nearestSite(const Point& q, const std::vector<Point>& sites) {
    int best = 0;
    double bestDist = 1e18;
    for (int i = 0; i < (int)sites.size(); i++) {
        double d = distSq(q, sites[i]);
        if (d < bestDist) {
            bestDist = d;
            best = i;
        }
    }
    return best;
}

int main() {
    std::vector<Point> sites = {
        {0, 0}, {4, 0}, {0, 4}, {4, 4}, {2, 2}
    };
    std::vector<Point> queries = {
        {1, 1}, {3, 3}, {2, 0}, {0, 5}, {4, 2}
    };

    for (auto& q : queries) {
        int site = nearestSite(q, sites);
        std::cout << "(" << q.x << "," << q.y << ") -> site "
                  << site << " (" << sites[site].x << ","
                  << sites[site].y << ")\n";
    }
    return 0;
}
```

### Dry Run

Input sites: S0=(0,0), S1=(4,0), S2=(0,4), S3=(4,4), S4=(2,2)

Query (1,1):
- dist² to S0 = 1+1 = 2  ← minimum
- dist² to S1 = 9+1 = 10
- dist² to S2 = 1+9 = 10
- dist² to S3 = 9+9 = 18
- dist² to S4 = 1+1 = 2  (tie, first found wins)

Query (3,3):
- dist² to S0 = 9+9 = 18
- dist² to S1 = 1+9 = 10
- dist² to S2 = 9+1 = 10
- dist² to S3 = 1+1 = 2  ← minimum
- dist² to S4 = 1+1 = 2  (tie)

### Complexity Analysis

| Operation | Brute Force | Fortune's Algorithm |
|---|---|---|
| Build | O(n²) | O(n log n) |
| Nearest query | O(n) | O(log n) with point location |
| Space | O(n) | O(n) |

---

## 161.2 Delaunay Triangulation

### Definition

A **Delaunay triangulation** of a point set is a triangulation where **no point lies inside the circumcircle** of any triangle. It is the **dual graph** of the Voronoi diagram.

### Motivation

- **Mesh generation**: Delaunay triangles avoid skinny triangles (maximizes minimum angle)
- **Finite element analysis**: Better numerical stability with well-shaped elements
- **Terrain modeling**: Interpolating elevation from scattered points
- **Computer graphics**: Surface reconstruction from point clouds

### Properties

- Maximizes the minimum angle among all triangulations
- Unique when no four points are cocircular
- O(n) triangles for n points in general position
- Can be constructed in O(n log n) time
- The convex hull edges appear in the triangulation

### Construction: Incremental Insertion

The simplest (though not optimal) approach inserts points one by one:

1. Start with a super-triangle containing all points
2. For each new point p:
   - Find all triangles whose circumcircle contains p
   - Delete those triangles, forming a polygonal cavity
   - Connect p to all vertices of the cavity
3. Remove triangles connected to the super-triangle

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

struct Point {
    double x, y;
    Point() : x(0), y(0) {}
    Point(double x, double y) : x(x), y(y) {}
};

struct Triangle {
    int a, b, c;
    Triangle(int a, int b, int c) : a(a), b(b), c(c) {}
};

// Check if point p is inside circumcircle of triangle (a, b, c)
bool inCircumcircle(const Point& p, const Point& a, const Point& b, const Point& c) {
    double ax = a.x - p.x, ay = a.y - p.y;
    double bx = b.x - p.x, by = b.y - p.y;
    double cx = c.x - p.x, cy = c.y - p.y;
    
    double det = ax * (by * (cx*cx + cy*cy) - cy * (bx*bx + by*by))
               - ay * (bx * (cx*cx + cy*cy) - cx * (bx*bx + by*by))
               + (ax*ax + ay*ay) * (bx * cy - cx * by);
    
    return det > 0;  // assumes CCW orientation
}

int main() {
    std::vector<Point> pts = {{0,0}, {4,0}, {0,4}, {4,4}, {2,2}, {1,3}};
    
    // For demonstration: check Delaunay property
    // A triangle (0,1,2) is Delaunay if no other point is in its circumcircle
    Triangle tri(0, 1, 2);
    bool isDelaunay = true;
    for (int i = 3; i < (int)pts.size(); i++) {
        if (inCircumcircle(pts[i], pts[tri.a], pts[tri.b], pts[tri.c])) {
            isDelaunay = false;
            std::cout << "Point " << i << " violates Delaunay for triangle ("
                      << tri.a << "," << tri.b << "," << tri.c << ")\n";
        }
    }
    if (isDelaunay)
        std::cout << "Triangle (0,1,2) satisfies Delaunay property\n";
    
    return 0;
}
```

### Complexity

| Operation | Time |
|---|---|
| Construction (incremental) | O(n²) worst case, O(n log n) expected |
| Construction (sweep line) | O(n log n) |
| Edge count | O(n) |

---

## 161.3 Half-Plane Intersection

### Definition

A **half-plane** is the region on one side of a line. Given *n* half-planes, find their intersection — a convex polygon (possibly unbounded or empty).

### Motivation

- **Linear programming**: Each constraint defines a half-plane; the feasible region is their intersection
- **Visibility**: What region is visible from a guard in a polygon?
- **Collision detection**: Intersection of constraint regions
- **Operations research**: Finding feasible solutions

### Intuition

Each half-plane "chips away" at the remaining region. Starting with the entire plane, each constraint cuts it down. The result is always convex (intersection of convex sets is convex).

### Algorithm: Sort-and-Sweep (O(n log n))

1. Represent each half-plane as an angle + offset
2. Sort half-planes by angle
3. Process with a deque, removing redundant constraints

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <deque>

struct Point {
    double x, y;
    Point() : x(0), y(0) {}
    Point(double x, double y) : x(x), y(y) {}
    Point operator-(const Point& o) const { return {x - o.x, y - o.y}; }
    Point operator+(const Point& o) const { return {x + o.x, y + o.y}; }
    Point operator*(double t) const { return {x * t, y * t}; }
};

double cross(const Point& a, const Point& b) {
    return a.x * b.y - a.y * b.x;
}

// Half-plane: left side of directed line from p in direction d
struct HalfPlane {
    Point p, d;  // point and direction vector
    double angle;
    HalfPlane() {}
    HalfPlane(Point p, Point d) : p(p), d(d) {
        angle = atan2(d.y, d.x);
    }
    bool operator<(const HalfPlane& o) const { return angle < o.angle; }
};

// Intersection point of two lines
Point lineIntersect(const HalfPlane& a, const HalfPlane& b) {
    double t = cross(b.p - a.p, b.d) / cross(a.d, b.d);
    return a.p + a.d * t;
}

// Check if point is inside half-plane
bool inside(const HalfPlane& hp, const Point& p) {
    return cross(hp.d, p - hp.p) >= -1e-9;
}

// Half-plane intersection using sort-and-sweep
std::vector<Point> halfPlaneIntersect(std::vector<HalfPlane>& hps) {
    std::sort(hps.begin(), hps.end());
    
    // Remove duplicate angles (keep the most restrictive)
    std::vector<HalfPlane> unique;
    for (int i = 0; i < (int)hps.size(); i++) {
        if (i > 0 && fabs(hps[i].angle - hps[i-1].angle) < 1e-9) continue;
        unique.push_back(hps[i]);
    }
    
    std::deque<HalfPlane> dq;
    std::deque<Point> pts;
    
    for (auto& hp : unique) {
        while (!dq.empty() && !inside(hp, pts.back())) {
            dq.pop_back();
            pts.pop_back();
        }
        while (!dq.empty() && !inside(hp, pts.front())) {
            dq.pop_front();
            pts.pop_front();
        }
        
        if (!dq.empty())
            pts.push_back(lineIntersect(dq.back(), hp));
        dq.push_back(hp);
    }
    
    // Remove redundant half-planes at the front
    while (!dq.empty() && !inside(dq.front(), pts.back())) {
        dq.pop_back();
        pts.pop_back();
    }
    
    // Collect result polygon
    std::vector<Point> result;
    if (dq.size() >= 3) {
        pts.push_back(lineIntersect(dq.front(), dq.back()));
        for (auto& p : pts) result.push_back(p);
    }
    return result;
}

int main() {
    // Intersect 4 half-planes forming a unit square [0,1] x [0,1]
    std::vector<HalfPlane> hps = {
        HalfPlane({0, 0}, {0, 1}),    // x >= 0
        HalfPlane({1, 0}, {0, -1}),   // x <= 1
        HalfPlane({0, 0}, {-1, 0}),   // y >= 0
        HalfPlane({0, 1}, {1, 0}),    // y <= 1
    };
    
    auto poly = halfPlaneIntersect(hps);
    std::cout << "Intersection polygon (" << poly.size() << " vertices):\n";
    for (auto& p : poly)
        std::cout << "  (" << p.x << ", " << p.y << ")\n";
    
    return 0;
}
```

### Dry Run

Half-planes for unit square [0,1]×[0,1]:
1. x ≥ 0: left half-plane of vertical line at x=0, direction up
2. x ≤ 1: left half-plane of vertical line at x=1, direction down
3. y ≥ 0: left half-plane of horizontal line at y=0, direction left
4. y ≤ 1: left half-plane of horizontal line at y=1, direction right

After sorting by angle and processing:
- Start with all four
- Each pair of adjacent half-planes intersects at a corner
- Result: 4 vertices (0,0), (1,0), (1,1), (0,1)

### Complexity

| Operation | Time | Space |
|---|---|---|
| Half-plane intersection | O(n log n) | O(n) |

---

## 161.4 Range Trees

### Definition

A **range tree** is a multi-level data structure for **orthogonal range reporting**: given a set of points, find all points within an axis-aligned rectangle.

### Motivation

- **Database queries**: "Find all employees with salary between X and Y and age between A and B"
- **Computational geometry**: Windowing queries in GIS
- **Competitive programming**: Multi-dimensional range queries

### Structure (2D Range Tree)

1. **Primary tree**: BST on x-coordinates (each node represents a subtree's x-range)
2. **Secondary tree**: At each primary node, store a BST on y-coordinates of all points in that subtree
3. **Fractional cascading**: Optimization to reduce query from O(log²n + k) to O(log n + k)

### Query Algorithm

To find all points in rectangle [x₁, x₂] × [y₁, y₂]:
1. Split the x-range [x₁, x₂] into O(log n) canonical subsets using the primary BST
2. For each canonical subset, search the secondary BST for y-values in [y₁, y₂]
3. Report all found points

```cpp
#include <iostream>
#include <vector>
#include <algorithm>

struct Point {
    int x, y, id;
    bool operator<(const Point& o) const { return x < o.x; }
};

// Simplified 2D range tree node
struct Node {
    std::vector<Point> ySorted;  // Points sorted by y
    int lo, hi;                   // x-range boundaries
    Node *left, *right;
};

// Build range tree on points[lo..hi] sorted by x
Node* build(std::vector<Point>& points, int lo, int hi) {
    if (lo > hi) return nullptr;
    Node* node = new Node();
    node->lo = lo;
    node->hi = hi;
    
    // Sort by y for this subtree
    node->ySorted.assign(points.begin() + lo, points.begin() + hi + 1);
    std::sort(node->ySorted.begin(), node->ySorted.end(),
              [](const Point& a, const Point& b) { return a.y < b.y; });
    
    if (lo == hi) return node;
    
    int mid = (lo + hi) / 2;
    node->left = build(points, lo, mid);
    node->right = build(points, mid + 1, hi);
    return node;
}

// Query ySorted array for points with y in [y1, y2]
void queryY(const std::vector<Point>& ySorted, int y1, int y2,
            std::vector<Point>& result) {
    auto lo = std::lower_bound(ySorted.begin(), ySorted.end(), y1,
        [](const Point& p, int val) { return p.y < val; });
    auto hi = std::upper_bound(ySorted.begin(), ySorted.end(), y2,
        [](int val, const Point& p) { return val < p.y; });
    for (auto it = lo; it != hi; ++it)
        result.push_back(*it);
}

// Range query: find all points in [x1,x2] x [y1,y2]
void rangeQuery(Node* node, int x1, int x2, int y1, int y2,
                std::vector<Point>& result) {
    if (!node) return;
    
    // Check if this node's x-range is completely outside [x1, x2]
    // (simplified: we'd need actual x-range tracking)
    
    if (node->lo == node->hi) {
        // Leaf node
        if (node->ySorted[0].x >= x1 && node->ySorted[0].x <= x2)
            queryY(node->ySorted, y1, y2, result);
        return;
    }
    
    // Recurse on children that overlap [x1, x2]
    if (node->left) rangeQuery(node->left, x1, x2, y1, y2, result);
    if (node->right) rangeQuery(node->right, x1, x2, y1, y2, result);
}

int main() {
    std::vector<Point> points = {
        {1, 3, 0}, {2, 7, 1}, {3, 1, 2}, {5, 5, 3},
        {7, 2, 4}, {8, 8, 5}, {4, 4, 6}, {6, 6, 7}
    };
    std::sort(points.begin(), points.end());
    
    Node* root = build(points, 0, points.size() - 1);
    
    // Query: x in [2, 6], y in [3, 7]
    std::vector<Point> result;
    rangeQuery(root, 2, 6, 3, 7, result);
    
    std::cout << "Points in [2,6] x [3,7]:\n";
    for (auto& p : result)
        std::cout << "  (" << p.x << ", " << p.y << ")\n";
    
    return 0;
}
```

### Complexity

| Operation | Time | Space |
|---|---|---|
| Build | O(n log n) | O(n log n) |
| Range query | O(log²n + k) | — |
| With fractional cascading | O(log n + k) | O(n log n) |

---

## 161.5 BSP Trees (Binary Space Partition)

### Definition

A **BSP tree** recursively partitions space using hyperplanes (lines in 2D, planes in 3D). Each internal node stores a splitting hyperplane; each child represents one side.

### Motivation

- **3D rendering**: Painter's algorithm — draw back-to-front using BSP tree traversal
- **Collision detection**: Quickly narrow down which objects to test
- **Ray tracing**: Accelerate ray-scene intersection queries
- **Robotics**: Spatial reasoning about environments

### How It Works

1. Choose a splitting line/plane
2. Split all geometry that crosses the partition
3. Recurse on each half-space
4. Stop when each region has ≤ 1 object (or some threshold)

### Traversal

For rendering (back-to-front):
1. Determine which side of the split plane the camera is on
2. Recursively render the far side first
3. Render the split plane's geometry
4. Recursively render the near side

```cpp
#include <iostream>
#include <vector>
#include <memory>

struct Line {
    double a, b, c;  // ax + by + c = 0
    Line(double a, double b, double c) : a(a), b(b), c(c) {}
};

struct Segment {
    double x1, y1, x2, y2;
    int id;
};

enum Side { LEFT, RIGHT, ON };

Side classify(const Segment& seg, const Line& line) {
    double d1 = line.a * seg.x1 + line.b * seg.y1 + line.c;
    double d2 = line.a * seg.x2 + line.b * seg.y2 + line.c;
    if (d1 > 1e-9 && d2 > 1e-9) return RIGHT;
    if (d1 < -1e-9 && d2 < -1e-9) return LEFT;
    return ON;  // crosses or lies on the line
}

struct BSPNode {
    Line split;
    std::vector<Segment> coplanar;
    std::unique_ptr<BSPNode> front, back;
    
    BSPNode(const Line& s) : split(s) {}
};

// Build BSP tree (simplified: use first segment as splitter)
std::unique_ptr<BSPNode> buildBSP(std::vector<Segment>& segs) {
    if (segs.empty()) return nullptr;
    
    // Use first segment to define split line
    auto& s = segs[0];
    double dx = s.x2 - s.x1, dy = s.y2 - s.y1;
    Line split(dy, -dx, dx * s.y1 - dy * s.x1);  // perpendicular
    
    auto node = std::make_unique<BSPNode>(split);
    
    std::vector<Segment> frontSegs, backSegs;
    for (auto& seg : segs) {
        Side side = classify(seg, split);
        if (side == ON) node->coplanar.push_back(seg);
        else if (side == RIGHT) frontSegs.push_back(seg);
        else backSegs.push_back(seg);
    }
    
    node->front = buildBSP(frontSegs);
    node->back = buildBSP(backSegs);
    return node;
}

int main() {
    std::vector<Segment> segs = {
        {0, 0, 2, 2, 0},
        {1, 0, 0, 1, 1},
        {3, 0, 3, 3, 2},
        {0, 3, 3, 3, 3}
    };
    
    auto root = buildBSP(segs);
    std::cout << "BSP tree built with " << segs.size() << " segments\n";
    std::cout << "Root split: " << root->split.a << "x + "
              << root->split.b << "y + " << root->split.c << " = 0\n";
    std::cout << "Coplanar segments at root: " << root->coplanar.size() << "\n";
    
    return 0;
}
```

### Complexity

| Metric | Average | Worst Case |
|---|---|---|
| Tree size | O(n log n) | O(n²) (many splits) |
| Build time | O(n log n) | O(n²) |
| Query | O(log n) | O(n) |

---

## Summary

| Structure | Build | Query | Space | Application |
|---|---|---|---|---|
| Voronoi | O(n log n) | O(log n) | O(n) | Nearest neighbor regions |
| Delaunay | O(n log n) | — | O(n) | Mesh generation, max-min angle |
| Half-plane intersection | O(n log n) | — | O(n) | Linear programming, feasibility |
| Range Tree | O(n log n) | O(log²n + k) | O(n log n) | Multi-dimensional range queries |
| BSP Tree | O(n log n) avg | O(log n) | O(n log n) | Rendering, collision detection |

---

## Exercises

1. **Voronoi Nearest Neighbor**: Given 10⁵ sites and 10⁵ queries, implement an efficient nearest-site finder using a KD-tree as an approximation to Voronoi point location.

2. **Delaunay Flips**: Implement edge flipping for Delaunay triangulation. Given a triangulation, repeatedly flip non-Delaunay edges until all edges satisfy the Delaunay property.

3. **Half-Plane Feasibility**: Given a system of linear inequalities, determine if the feasible region is non-empty using half-plane intersection.

4. **3D Range Tree**: Extend the 2D range tree to 3D. What is the query time? How would fractional cascading help?

5. **BSP for Ray Tracing**: Given a scene with 1000 triangles, build a BSP tree and trace 10000 rays. Compare performance against brute force.

---

## Interview Questions

1. **Q**: What is the relationship between Voronoi diagrams and Delaunay triangulations?
   **A**: They are dual graphs. Each Voronoi edge corresponds to a Delaunay edge (perpendicular bisector relationship). Each Voronoi vertex corresponds to a Delaunay triangle's circumcenter. Constructing one gives the other in O(n) time.

2. **Q**: How would you find the nearest facility (hospital, fire station) to a given location?
   **A**: Build a Voronoi diagram of all facilities. Use point location in the Voronoi diagram (O(log n) with preprocessing) to find which cell contains the query point — that cell's site is the nearest facility.

3. **Q**: Why does Delaunay triangulation maximize the minimum angle?
   **A**: The empty circumcircle property means no point is "too close" to any triangle's circumcircle, which pushes triangles toward equilateral shapes. Any non-Delaunay edge flip would create a smaller minimum angle.

4. **Q**: When would you use a BSP tree over a KD-tree?
   **A**: BSP trees handle arbitrarily oriented split planes (not just axis-aligned), making them better for scenes with diagonal geometry. KD-trees are simpler and better for point data with axis-aligned queries.

5. **Q**: How does fractional cascading improve range tree queries?
   **A**: It stores pointers between adjacent levels' sorted arrays, allowing binary search results from one level to guide the search at the next level. This reduces the O(log n) factor per level to O(1), giving O(log n + k) total query time.

---

## Cross-References

- **Chapter 156**: Convex Hull — foundation for many geometry algorithms
- **Chapter 157**: Sweep Line — used in Voronoi construction
- **Chapter 162**: Advanced Graph Algorithms — spatial graphs
- **Chapter 158**: Interval Trees — another approach to range queries
- **Chapter 76**: KD-Trees — practical alternative to range trees for nearest neighbor
