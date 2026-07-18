#include "ignis/detections.hpp"
#include "ignis/model_manifest.hpp"

#include <iostream>

#include "test_support.hpp"

int main() {
    using namespace ignis;
    Detection valid{"fire", 0, 1.2, {-0.01, 0.2, 1.01, 0.8}};
    REQUIRE(normalize_detection(valid));
    REQUIRE(valid.confidence == 1.0);
    REQUIRE(valid.bbox.x_min == 0.0 && valid.bbox.x_max == 1.0);
    Detection invalid{"smoke", 1, 0.8, {0.8, 0.2, 0.1, 0.4}};
    REQUIRE(!normalize_detection(invalid));

    ModelManifest manifest;
    manifest.model_name = "ignis_fire_smoke_detector";
    manifest.model_sha256 = "replace-at-export";
    manifest.input_width = 320;
    manifest.input_height = 320;
    manifest.input_dtype = "uint8";
    manifest.color_order = "RGB";
    manifest.labels = {{0, "fire"}, {1, "smoke"}};
    REQUIRE(manifest.validate().ok());
    manifest.labels[1] = "person";
    REQUIRE(!manifest.validate().ok());
    std::cout << "model_decoder_tests: all assertions passed\n";
    return 0;
}

