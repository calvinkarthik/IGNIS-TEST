#pragma once

#include <cstdlib>
#include <iostream>
#include <string>

inline void require(bool condition, const char* expression, const char* file, int line) {
    if (!condition) {
        std::cerr << file << ':' << line << " requirement failed: " << expression << '\n';
        std::exit(1);
    }
}

#define REQUIRE(expression) require(static_cast<bool>(expression), #expression, __FILE__, __LINE__)

