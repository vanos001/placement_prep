# Chapter 190: Coordinate Geometry for Competitive Programming

Computational geometry is essential in competitive programming. This chapter covers the core primitives: **cross product, convex hull, point-in-polygon, and polygon area**.

---

## Cross Product

The **cross product** of vectors AB and AC determines orientation:

```
cross(A, B, C) = (B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x)
```

| Result | Meaning |
|---|---|
| > 0 | C is left of AB (counter-clockwise turn) |
| < 0 | C is right of AB (clockwise turn) |
| = 0 | Collinear |

```cpp
using Point = pair<long long, long long>;
long long cross(Point a, Point b, Point c) {
    return (b.first - a.first) * (c.second - a.second)
         - (b.second - a.second) * (c.first - a.first);
}
```

---

## Convex Hull — Andrew's Monotone Chain

Build upper and lower hulls in O(n log n).

```cpp
vector<Point> convexHull(vector<Point> pts) {
    sort(pts.begin(), pts.end());
    vector<Point> hull;
    // Lower hull
    for (auto& p : pts) {
        while (hull.size() >= 2 && cross(hull[hull.size()-2], hull.back(), p) <= 0)
            hull.pop_back();
        hull.push_back(p);
    }
    // Upper hull
    int lower = hull.size() + 1;
    for (int i = (int)pts.size() - 2; i >= 0; i--) {
        while ((int)hull.size() >= lower && cross(hull[hull.size()-2], hull.back(), pts[i]) <= 0)
            hull.pop_back();
        hull.push_back(pts[i]);
    }
    hull.pop_back();
    return hull;
}
```

**Complexity:** O(n log n) time, O(n) space.

---

## Point-in-Polygon (Ray Casting)

Shoot a ray from the point rightward; count edge crossings. Odd → inside.

```cpp
bool pointInPolygon(Point p, vector<Point>& poly) {
    int n = poly.size(), inside = false;
    for (int i = 0, j = n - 1; i < n; j = i++) {
        if (((poly[i].second > p.second) != (poly[j].second > p.second)) &&
            p.first < (poly[j].first - poly[i].first) * (p.second - poly[i].second)
                      / (poly[j].second - poly[i].second) + poly[i].first)
            inside = !inside;
    }
    return inside;
}
```

**Complexity:** O(n) per query.

---

## Polygon Area (Shoelace Formula)

```
Area = 0.5 * |Σ (xᵢ * yᵢ₊₁ - xᵢ₊₁ * yᵢ)|
```

```cpp
long long polygonArea(vector<Point>& poly) {
    long long area = 0, n = poly.size();
    for (int i = 0; i < n; i++)
        area += poly[i].first * poly[(i+1)%n].second
              - poly[(i+1)%n].first * poly[i].second;
    return abs(area) / 2;
}
```

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Integer overflow in cross product | Use `long long`; coordinates up to 10⁹ need 128-bit for area |
| Collinear points on hull | Use `< 0` (strict) or `<= 0` (keep collinear) depending on requirements |
| Ray passing through a vertex | The ray-casting formula handles this with strict inequality on one side |

---

## Practice Problems

| # | Problem | Hint |
|---|---|
| 1 | Convex Hull (SPOJ BSHEEP) | Andrew's monotone chain |
| 2 | Point in Polygon (Kattis) | Ray casting |
| 3 | Polygon Area (UVa 10065) | Shoelace formula |
| 4 | Rotating Calipers — Diameter | Use convex hull + two pointers |
| 5 | Line Intersection (LeetCode 1615 variant) | Cross product + parametric intersection |
| 6 | Minimum Area Rectangle (LeetCode 939) | Combine with hash maps |

---

## See Also

- [Chapter 64: Geometry](ch64-geometry.md)
- [Chapter 161: Advanced Geometry](ch161-adv-geometry.md)
- [Chapter 189: Sweep-Line Geometry](ch189-sweep-line-geometry.md)
- [Chapter 78: KD-Trees](ch78-kd-trees.md)
