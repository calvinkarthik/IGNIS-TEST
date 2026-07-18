#include "ignis/geometry.hpp"

#include <algorithm>
#include <cmath>

namespace ignis {

bool Box::valid() const noexcept {
    return std::isfinite(x_min) && std::isfinite(y_min) && std::isfinite(x_max) &&
           std::isfinite(y_max) && x_min >= 0 && y_min >= 0 && x_max <= 1 && y_max <= 1 &&
           x_min < x_max && y_min < y_max;
}

double Box::area() const noexcept {
    return std::max(0.0, x_max - x_min) * std::max(0.0, y_max - y_min);
}

double polygon_area(const std::vector<Point>& polygon) noexcept {
    if (polygon.size() < 3) return 0;
    double twice_area = 0;
    for (std::size_t i = 0; i < polygon.size(); ++i) {
        const Point& current = polygon[i];
        const Point& next = polygon[(i + 1) % polygon.size()];
        twice_area += current.x * next.y - next.x * current.y;
    }
    return std::abs(twice_area) / 2.0;
}

bool valid_polygon(const std::vector<Point>& polygon) noexcept {
    if (polygon.size() < 3 || polygon_area(polygon) < 0.0001) return false;
    for (const Point& point : polygon) {
        if (!std::isfinite(point.x) || !std::isfinite(point.y) || point.x < 0 || point.x > 1 ||
            point.y < 0 || point.y > 1) {
            return false;
        }
    }
    return true;
}

namespace {

enum class Edge { Left, Right, Top, Bottom };

bool inside(const Point& point, const Box& box, Edge edge) {
    switch (edge) {
        case Edge::Left: return point.x >= box.x_min;
        case Edge::Right: return point.x <= box.x_max;
        case Edge::Top: return point.y >= box.y_min;
        case Edge::Bottom: return point.y <= box.y_max;
    }
    return false;
}

Point intersection(const Point& a, const Point& b, const Box& box, Edge edge) {
    Point result = a;
    const double dx = b.x - a.x;
    const double dy = b.y - a.y;
    if (edge == Edge::Left || edge == Edge::Right) {
        const double x = edge == Edge::Left ? box.x_min : box.x_max;
        const double t = std::abs(dx) < 1e-12 ? 0 : (x - a.x) / dx;
        result.x = x;
        result.y = a.y + t * dy;
    } else {
        const double y = edge == Edge::Top ? box.y_min : box.y_max;
        const double t = std::abs(dy) < 1e-12 ? 0 : (y - a.y) / dy;
        result.x = a.x + t * dx;
        result.y = y;
    }
    return result;
}

std::vector<Point> clip(const std::vector<Point>& input, const Box& box, Edge edge) {
    std::vector<Point> output;
    if (input.empty()) return output;
    Point previous = input.back();
    for (const Point& current : input) {
        const bool current_inside = inside(current, box, edge);
        const bool previous_inside = inside(previous, box, edge);
        if (current_inside) {
            if (!previous_inside) output.push_back(intersection(previous, current, box, edge));
            output.push_back(current);
        } else if (previous_inside) {
            output.push_back(intersection(previous, current, box, edge));
        }
        previous = current;
    }
    return output;
}

}  // namespace

double box_polygon_intersection_area(const Box& box, const std::vector<Point>& polygon) {
    if (!box.valid() || !valid_polygon(polygon)) return 0;
    std::vector<Point> clipped = polygon;
    for (Edge edge : {Edge::Left, Edge::Right, Edge::Top, Edge::Bottom}) {
        clipped = clip(clipped, box, edge);
        if (clipped.empty()) return 0;
    }
    return polygon_area(clipped);
}

ZoneMatch associate_zone(const Box& box, const std::vector<Zone>& zones, double minimum_overlap) {
    ZoneMatch best;
    if (!box.valid() || box.area() <= 0) return best;
    for (const Zone& zone : zones) {
        if (!valid_polygon(zone.points)) continue;
        const double ratio = box_polygon_intersection_area(box, zone.points) / box.area();
        if (ratio > best.overlap_ratio) {
            best.zone_name = zone.name;
            best.overlap_ratio = ratio;
        }
    }
    if (best.overlap_ratio < minimum_overlap) return ZoneMatch{};
    return best;
}

}  // namespace ignis

