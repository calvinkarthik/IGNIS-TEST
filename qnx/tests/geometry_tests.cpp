#include "ignis/geometry.hpp"

#include <cmath>
#include <iostream>

#include "test_support.hpp"

int main() {
    using namespace ignis;
    const Box box{0.25, 0.25, 0.75, 0.75};
    REQUIRE(box.valid());
    REQUIRE(std::abs(box.area() - 0.25) < 1e-9);

    const std::vector<Point> half{{0, 0}, {0.5, 0}, {0.5, 1}, {0, 1}};
    REQUIRE(valid_polygon(half));
    REQUIRE(std::abs(box_polygon_intersection_area(box, half) - 0.125) < 1e-9);

    const std::vector<Zone> zones{
        {"left", "Stovetop", half},
        {"right", "Battery charging area", {{0.5, 0}, {1, 0}, {1, 1}, {0.5, 1}}},
    };
    const ZoneMatch match = associate_zone(Box{0.05, 0.1, 0.45, 0.9}, zones, 0.25);
    REQUIRE(match.zone_name == "Stovetop");
    REQUIRE(match.overlap_ratio > 0.99);
    REQUIRE(associate_zone(Box{0.46, 0.4, 0.54, 0.6}, zones, 0.6).zone_name == "Unconfigured area");
    REQUIRE(!valid_polygon({{0, 0}, {0, 0}, {0, 0}}));
    const Box invalid_box{0.8, 0.1, 0.2, 0.4};
    REQUIRE(!invalid_box.valid());
    std::cout << "geometry_tests: all assertions passed\n";
    return 0;
}
