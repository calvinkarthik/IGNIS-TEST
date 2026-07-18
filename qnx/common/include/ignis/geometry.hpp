#pragma once

#include <string>
#include <vector>

namespace ignis {

struct Point {
    double x{0};
    double y{0};
};

struct Box {
    double x_min{0};
    double y_min{0};
    double x_max{0};
    double y_max{0};

    bool valid() const noexcept;
    double area() const noexcept;
};

struct Zone {
    std::string id;
    std::string name;
    std::vector<Point> points;
};

struct ZoneMatch {
    std::string zone_name{"Unconfigured area"};
    double overlap_ratio{0};
};

double polygon_area(const std::vector<Point>& polygon) noexcept;
bool valid_polygon(const std::vector<Point>& polygon) noexcept;
double box_polygon_intersection_area(const Box& box, const std::vector<Point>& polygon);
ZoneMatch associate_zone(const Box& box, const std::vector<Zone>& zones, double minimum_overlap);

}  // namespace ignis

