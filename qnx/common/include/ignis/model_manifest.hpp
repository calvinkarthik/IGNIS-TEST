#pragma once

#include <map>
#include <string>

#include "ignis/result.hpp"

namespace ignis {

struct ModelManifest {
    int schema_version{1};
    std::string model_name;
    std::string model_sha256;
    int input_width{0};
    int input_height{0};
    int input_channels{3};
    std::string input_dtype;
    std::string color_order;
    std::string decoder{"ssd"};
    int boxes_index{0};
    int classes_index{1};
    int scores_index{2};
    int count_index{3};
    int predictions_index{0};
    std::map<int, std::string> labels;

    Result<void> validate() const {
        if (schema_version != 1) return Result<void>::failure("unsupported manifest schema");
        if (model_name.empty()) return Result<void>::failure("model name is required");
        if (input_width <= 0 || input_height <= 0 || input_channels != 3)
            return Result<void>::failure("invalid model input dimensions");
        if (input_dtype != "uint8" && input_dtype != "int8" && input_dtype != "float32")
            return Result<void>::failure("unsupported input dtype");
        if (color_order != "RGB" && color_order != "BGR")
            return Result<void>::failure("unsupported color order");
        if (decoder != "ssd" && decoder != "yolo_v8")
            return Result<void>::failure("unsupported output decoder");
        const bool ordered_fire_smoke = labels.count(0) != 0 && labels.count(1) != 0 &&
                                        labels.at(0) == "fire" && labels.at(1) == "smoke";
        const bool ordered_smoke_fire = labels.count(0) != 0 && labels.count(1) != 0 &&
                                        labels.at(0) == "smoke" && labels.at(1) == "fire";
        if (!ordered_fire_smoke && !ordered_smoke_fire)
            return Result<void>::failure("fire/smoke labels do not match the decoder contract");
        return Result<void>::success();
    }
};

}  // namespace ignis
