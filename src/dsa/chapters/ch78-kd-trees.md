# Chapter 78: KD Trees and Spatial Data Structures

## Prerequisites

- Binary search trees ([Chapter 14](ch14-bst.md))
- Recursion and divide-and-conquer
- Basic geometry (Euclidean distance)

## Interview Frequency: ★★

KD Trees handle k-dimensional queries efficiently. They appear in **Google** interviews for nearest neighbor and range search problems, and are widely used in computer graphics, machine learning, and geographic information systems.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| KD Tree construction | ★★ | Medium | Alternating dimensions |
| Nearest neighbor | ★★★ | Medium | Pruning with bounds |
| Range search | ★★ | Medium | Query rectangular regions |
| Balance concerns | ★★ | Medium | Degenerate cases |
| Ball tree variant | ★ | Hard | Alternative for high dimensions |

---

## Definition

A **KD Tree** (k-dimensional tree) is a binary space partitioning data structure that organizes points in k-dimensional space. At each level of the tree, it splits the space along one dimension using the median point, cycling through dimensions as we go deeper.

## Motivation

Naive nearest-neighbor search requires O(n) distance calculations. For n points in k dimensions:
- **Brute force**: O(nk) per query
- **KD Tree**: O(k log n) average per query (with pruning)

This is critical in applications like:
- **Machine learning**: k-NN classification, recommendation systems
- **Computer graphics**: Ray tracing, photon mapping
- **Geographic systems**: Finding nearby restaurants, points of interest
- **Robotics**: Motion planning, collision detection

## Intuition

Think of organizing a 2D map. First, split all points by x-coordinate (vertical line). Then split each half by y-coordinate (horizontal lines). Then split again by x, and so on. This alternating partitioning creates a hierarchy where we can quickly eliminate large regions of space during search.

```
Split by x (level 0):       Split by y (level 1):
  |  •  •                    ---•---•
  |  •    •                  ---•---•
  |  •  •                    ---•---•
```

---

## 78.1 Construction

### Definition

Build a KD tree by recursively splitting points along alternating dimensions. At depth d, split along dimension d mod k.

### Step-by-Step Walkthrough

Given points: (2,3), (5,4), (9,6), (4,7), (8,1), (7,2), (6,8), (1,9)

**Depth 0 (split on x):**
- Sort by x: (1,9), (2,3), (4,7), (5,4), (6,8), (7,2), (8,1), (9,6)
- Median (index 3): (5,4)
- Left: {(1,9), (2,3), (4,7)} — x < 5
- Right: {(6,8), (7,2), (8,1), (9,6)} — x ≥ 5

**Depth 1 (split on y):**
- Left subtree sort by y: (2,3), (4,7), (1,9)
  - Median: (4,7)
  - Left: {(2,3)} — y < 7
  - Right: {(1,9)} — y ≥ 7
- Right subtree sort by y: (7,2), (8,1), (9,6), (6,8)
  - Median: (9,6)
  - Left: {(7,2), (8,1)} — y < 6
  - Right: {(6,8)} — y ≥ 6

**Result:**
```
        (5,4)           ← split on x
       /     \
    (4,7)   (9,6)       ← split on y
    /   \   /   \
 (2,3) (1,9) (7,2) (6,8) ← split on x
         |
        (8,1)
```

### Dry Run — Nearest Neighbor to (5, 5)

```
1. At root (5,4): dist=1.0, best=(5,4)
   Split on x: target x=5, diff = 0 → code's ternary "diff < 0 ? left : right" sends us right first
2. At (4,7): dist=2.24, best=(5,4) (unchanged)
   Split on y: target y=5, go left (y<7) first
3. At (2,3): dist=3.61, best=(5,4) (unchanged)
   No children, backtrack
4. Back at (4,7): check right child (1,9)
   |1-5|=4 > bestDist=1.0 → PRUNE (skip entire subtree)
5. Back at (5,4): check right child (9,6)
   |9-5|=4 > bestDist=1.0 → PRUNE
6. Result: (5,4) at distance 1.0
```

### C++ Implementation

```cpp
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <float.h>

struct Point {
    std::vector<double> coords;
    int id;
};

struct KDNode {
    Point point;
    KDNode *left, *right;
    int splitDim;
};

class KDTree {
    KDNode* root;
    int k;

    KDNode* build(std::vector<Point>& points, int depth) {
        if (points.empty()) return nullptr;

        int dim = depth % k;
        int mid = points.size() / 2;

        // nth_element is O(n) average — partial sort to find median
        std::nth_element(points.begin(), points.begin() + mid, points.end(),
            [dim](const Point& a, const Point& b) {
                return a.coords[dim] < b.coords[dim];
            });

        KDNode* node = new KDNode();
        node->point = points[mid];
        node->splitDim = dim;

        std::vector<Point> leftPoints(points.begin(), points.begin() + mid);
        std::vector<Point> rightPoints(points.begin() + mid + 1, points.end());

        node->left = build(leftPoints, depth + 1);
        node->right = build(rightPoints, depth + 1);

        return node;
    }

    double dist(const Point& a, const Point& b) {
        double d = 0;
        for (int i = 0; i < k; i++)
            d += (a.coords[i] - b.coords[i]) * (a.coords[i] - b.coords[i]);
        return std::sqrt(d);
    }

    void nearestNeighbor(KDNode* node, const Point& target,
                         KDNode*& best, double& bestDist) {
        if (!node) return;

        double d = dist(node->point, target);
        if (d < bestDist) {
            bestDist = d;
            best = node;
        }

        int dim = node->splitDim;
        double diff = target.coords[dim] - node->point.coords[dim];

        // Visit the side of the split plane containing the target first
        KDNode* first = diff < 0 ? node->left : node->right;
        KDNode* second = diff < 0 ? node->right : node->left;

        nearestNeighbor(first, target, best, bestDist);

        // Only visit the other side if the split plane is closer than bestDist
        if (std::abs(diff) < bestDist) {
            nearestNeighbor(second, target, best, bestDist);
        }
    }

    void rangeSearch(KDNode* node, const Point& lo, const Point& hi,
                     std::vector<Point>& result) {
        if (!node) return;

        bool inside = true;
        for (int i = 0; i < k; i++) {
            if (node->point.coords[i] < lo.coords[i] ||
                node->point.coords[i] > hi.coords[i]) {
                inside = false;
                break;
            }
        }
        if (inside) result.push_back(node->point);

        int dim = node->splitDim;
        if (node->point.coords[dim] >= lo.coords[dim])
            rangeSearch(node->left, lo, hi, result);
        if (node->point.coords[dim] <= hi.coords[dim])
            rangeSearch(node->right, lo, hi, result);
    }

    void freeTree(KDNode* node) {
        if (!node) return;
        freeTree(node->left);
        freeTree(node->right);
        delete node;
    }

public:
    KDTree(const std::vector<Point>& points, int dimensions)
        : k(dimensions) {
        std::vector<Point> pts = points;
        root = build(pts, 0);
    }

    ~KDTree() { freeTree(root); }

    Point nearestNeighbor(const Point& target) {
        KDNode* best = nullptr;
        double bestDist = DBL_MAX;
        nearestNeighbor(root, target, best, bestDist);
        return best->point;
    }

    std::vector<Point> rangeSearch(const Point& lo, const Point& hi) {
        std::vector<Point> result;
        rangeSearch(root, lo, hi, result);
        return result;
    }
};

int main() {
    std::vector<Point> points = {
        {{2, 3}, 0}, {{5, 4}, 1}, {{9, 6}, 2}, {{4, 7}, 3},
        {{8, 1}, 4}, {{7, 2}, 5}, {{6, 8}, 6}, {{1, 9}, 7}
    };

    KDTree tree(points, 2);

    // Nearest neighbor query
    Point query = {{5, 5}, -1};
    Point nearest = tree.nearestNeighbor(query);
    std::cout << "Nearest to (5,5): (" << nearest.coords[0] << ","
              << nearest.coords[1] << ") id=" << nearest.id << "\n";

    // Range search query
    Point lo = {{3, 3}, -1}, hi = {{7, 7}, -1};
    auto inRange = tree.rangeSearch(lo, hi);
    std::cout << "Points in [3,7]x[3,7]:\n";
    for (auto& p : inRange)
        std::cout << "  (" << p.coords[0] << "," << p.coords[1] << ")\n";

    return 0;
}
```

### Python Implementation

```python
import math
from typing import List, Tuple, Optional

class KDNode:
    def __init__(self, point, split_dim):
        self.point = point
        self.split_dim = split_dim
        self.left = None
        self.right = None

class KDTree:
    def __init__(self, points: List[Tuple], k: int = 2):
        self.k = k
        self.root = self._build(points, 0)

    def _build(self, points, depth):
        if not points:
            return None
        dim = depth % self.k
        points.sort(key=lambda p: p[dim])
        mid = len(points) // 2
        node = KDNode(points[mid], dim)
        node.left = self._build(points[:mid], depth + 1)
        node.right = self._build(points[mid+1:], depth + 1)
        return node

    def _dist(self, a, b):
        return math.sqrt(sum((ai - bi)**2 for ai, bi in zip(a, b)))

    def nearest_neighbor(self, target):
        best = [None, float('inf')]  # [point, distance]

        def _search(node):
            if not node:
                return
            d = self._dist(node.point, target)
            if d < best[1]:
                best[0] = node.point
                best[1] = d

            dim = node.split_dim
            diff = target[dim] - node.point[dim]
            first = node.left if diff < 0 else node.right
            second = node.right if diff < 0 else node.left

            _search(first)
            if abs(diff) < best[1]:
                _search(second)

        _search(self.root)
        return best[0], best[1]

    def range_search(self, lo, hi):
        result = []

        def _search(node):
            if not node:
                return
            if all(lo[i] <= node.point[i] <= hi[i] for i in range(self.k)):
                result.append(node.point)
            dim = node.split_dim
            if node.point[dim] >= lo[dim]:
                _search(node.left)
            if node.point[dim] <= hi[dim]:
                _search(node.right)

        _search(self.root)
        return result

# Example
points = [(2,3), (5,4), (9,6), (4,7), (8,1), (7,2), (6,8), (1,9)]
tree = KDTree(points, 2)

nearest, dist = tree.nearest_neighbor((5, 5))
print(f"Nearest to (5,5): {nearest}, dist={dist:.2f}")

in_range = tree.range_search((3, 3), (7, 7))
print(f"Points in [3,7]x[3,7]: {in_range}")
```

### Java Implementation

```java
import java.util.*;

public class KDTree {
    static class Point {
        double[] coords;
        int id;
        Point(double[] coords, int id) { this.coords = coords; this.id = id; }
    }

    static class KDNode {
        Point point;
        KDNode left, right;
        int splitDim;
    }

    private KDNode root;
    private int k;

    public KDTree(List<Point> points, int dimensions) {
        k = dimensions;
        List<Point> pts = new ArrayList<>(points);
        root = build(pts, 0);
    }

    private KDNode build(List<Point> points, int depth) {
        if (points.isEmpty()) return null;
        int dim = depth % k;
        int mid = points.size() / 2;
        points.sort(Comparator.comparingDouble(p -> p.coords[dim]));
        KDNode node = new KDNode();
        node.point = points.get(mid);
        node.splitDim = dim;
        node.left = build(new ArrayList<>(points.subList(0, mid)), depth + 1);
        node.right = build(new ArrayList<>(points.subList(mid + 1, points.size())), depth + 1);
        return node;
    }

    private double dist(Point a, Point b) {
        double d = 0;
        for (int i = 0; i < k; i++)
            d += (a.coords[i] - b.coords[i]) * (a.coords[i] - b.coords[i]);
        return Math.sqrt(d);
    }

    private KDNode bestNode;
    private double bestDist;

    public Point nearestNeighbor(Point target) {
        bestNode = null;
        bestDist = Double.MAX_VALUE;
        nnSearch(root, target);
        return bestNode.point;
    }

    private void nnSearch(KDNode node, Point target) {
        if (node == null) return;
        double d = dist(node.point, target);
        if (d < bestDist) { bestDist = d; bestNode = node; }
        int dim = node.splitDim;
        double diff = target.coords[dim] - node.point.coords[dim];
        KDNode first = diff < 0 ? node.left : node.right;
        KDNode second = diff < 0 ? node.right : node.left;
        nnSearch(first, target);
        if (Math.abs(diff) < bestDist) nnSearch(second, target);
    }

    public static void main(String[] args) {
        List<Point> points = Arrays.asList(
            new Point(new double[]{2,3}, 0), new Point(new double[]{5,4}, 1),
            new Point(new double[]{9,6}, 2), new Point(new double[]{4,7}, 3),
            new Point(new double[]{8,1}, 4), new Point(new double[]{7,2}, 5),
            new Point(new double[]{6,8}, 6), new Point(new double[]{1,9}, 7)
        );
        KDTree tree = new KDTree(points, 2);
        Point nearest = tree.nearestNeighbor(new Point(new double[]{5,5}, -1));
        System.out.println("Nearest to (5,5): (" + nearest.coords[0] + "," + nearest.coords[1] + ")");
    }
}
```

---

## 78.2 Complexity Analysis

| Operation | Average | Worst Case |
|---|---|---|
| Build | O(n log n) | O(n²) — degenerate splits |
| Nearest neighbor | O(log n) | O(n) — all points explored |
| Range search | O(n^(1-1/k) + m) | O(n) — m results found |
| Insert | O(log n) | O(n) |
| Delete | O(log n) | O(n) |

**Note**: The "curse of dimensionality" degrades performance as k grows. For k > ~20, KD trees are no better than brute force. In high dimensions, consider locality-sensitive hashing (LSH) or ball trees.

---

## 78.3 Variants and Extensions

### 1. Range Search

Query: Find all points within an axis-aligned rectangle [lo, hi].

**Pruning rule**: If the node's split coordinate is outside the query range on the split dimension, prune that subtree.

### 2. k-Nearest Neighbors (k-NN)

Maintain a max-heap of size k. At each node, check if it's closer than the farthest in the heap. Prune subtrees that can't contain closer points.

### 3. Ball Tree

Instead of axis-aligned splits, use hyperspheres. Better for high-dimensional data where KD trees degrade.

### 4. R-Tree

For spatial databases. Groups nearby objects using minimum bounding rectangles. Optimized for disk access.

---

## 78.4 Comparison with Other Spatial Structures

| Structure | Best for | Dimensions | Build | Query |
|---|---|---|---|---|
| KD Tree | Static points, low k | k ≤ 20 | O(n log n) | O(log n) avg |
| Ball Tree | High dimensions | Any | O(n log n) | O(log n) avg |
| R-Tree | Spatial databases | Any | O(n log n) | O(log n) |
| Quadtree | 2D points | k=2 | O(n log n) | O(log n) |
| Octree | 3D points | k=3 | O(n log n) | O(log n) |
| Grid | Uniform distribution | Any | O(n) | O(1) avg |

---

## Exercises

1. **Implement k-NN**: Extend the KD tree to find the k nearest neighbors. Use a max-heap to track the k closest points found so far.

2. **Dynamic KD Tree**: Implement insert and delete operations. For delete, consider the "lazy" approach (mark as deleted) vs. the "rebuild" approach.

3. **Nearest neighbor in 3D**: Modify the code to work with 3D points. Test with a dataset of 1000 random 3D points.

4. **Range count**: Implement a function that counts (without listing) the number of points in a given axis-aligned rectangle.

5. **Brute force comparison**: For n = 10000 points in 2D, compare the time of KD tree nearest neighbor vs. brute force. Plot the speedup.

6. **High-dimensional experiment**: Build KD trees for k = 2, 5, 10, 20, 50. Measure nearest neighbor query time. At what k does the KD tree become slower than brute force?

---

## Interview Questions

1. **Q: How does a KD tree differ from a regular BST?**
   A: A BST splits on a single key dimension. A KD tree cycles through k dimensions at each level. A BST organizes 1D data; a KD tree organizes k-dimensional data.

2. **Q: How does nearest neighbor search work in a KD tree?**
   A: Recursively search the side of the split plane containing the query point. After returning, check if the other side could contain a closer point (i.e., if the distance from the query to the split plane is less than the current best distance). If so, search the other side too.

3. **Q: What is the "curse of dimensionality" for KD trees?**
   A: As the number of dimensions k increases, the pruning efficiency decreases. In high dimensions, most of the volume of a hypersphere is near its surface, so the split planes rarely eliminate large portions of space. For k > ~20, KD trees perform no better than brute force.

4. **Q: When would you use a KD tree vs. a hash table for nearest neighbor?**
   A: KD trees give exact nearest neighbors in low dimensions with O(log n) average time. Hash tables (via LSH) give approximate nearest neighbors in high dimensions with O(1) average time. Use KD trees for exact, low-dimensional; use LSH for approximate, high-dimensional.

5. **Q: How do you handle dynamic data (insertions/deletions) in a KD tree?**
   A: Simple approach: insert by traversing to a leaf (O(log n) average). Delete is trickier — either mark nodes as deleted (lazy), or replace with a descendant and rebuild. For highly dynamic data, consider R-trees or brute force.

6. **Q: What data structure would you use for nearest neighbor in 1 million 3D points?**
   A: A KD tree with k=3. Build time O(n log n), query time O(log n) average. The tree fits in memory, and 3 dimensions is low enough that pruning is effective.

---

## Cross-References

- [Chapter 13: Trees](ch13-trees.md) — Tree fundamentals: traversals, recursion, and basic tree properties
- [Chapter 14: Binary Search Trees](ch14-bst.md) — The foundation; KD trees generalize BSTs to k dimensions
- [Chapter 22: Divide and Conquer](ch39-divide-conquer.md) — KD tree construction uses median-based partitioning
- [Chapter 145: Approximation Algorithms](ch145-approximation-algorithms.md) — Approximate nearest neighbor via LSH
- [Chapter 99: Scapegoat and AA Trees](ch99-scapegoat-aa-trees.md) — Other balanced tree variants

---

## Summary

| Aspect | Value |
|---|---|
| Dimensions | k (typically 2 or 3) |
| Build | O(n log n) average |
| Nearest neighbor | O(log n) average, O(n) worst |
| Range search | O(n^(1-1/k) + m) average |
| Best for | Spatial queries, nearest neighbor, low dimensions |
| Limitation | Curse of dimensionality for k > ~20 |
