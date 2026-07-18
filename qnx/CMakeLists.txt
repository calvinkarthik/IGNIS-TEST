cmake_minimum_required(VERSION 3.20)
project(ignis_edge VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(ignis_common
    common/src/geometry.cpp
    common/src/incident.cpp
    common/src/protocol.cpp)
target_include_directories(ignis_common PUBLIC common/include)
target_compile_options(ignis_common PRIVATE -Wall -Wextra -Wpedantic)

enable_testing()
foreach(test_name geometry_tests incident_engine_tests protocol_tests model_decoder_tests)
    add_executable(${test_name} tests/${test_name}.cpp)
    target_include_directories(${test_name} PRIVATE tests)
    target_link_libraries(${test_name} PRIVATE ignis_common)
    add_test(NAME ${test_name} COMMAND ${test_name})
endforeach()

add_executable(camera_service
    camera_service/src/main.cpp
    camera_service/src/frame_sources.cpp)
target_include_directories(camera_service PRIVATE camera_service/include)
target_link_libraries(camera_service PRIVATE ignis_common)

add_executable(inference_service
    inference_service/src/main.cpp
    inference_service/src/inference_engine.cpp)
target_include_directories(inference_service PRIVATE inference_service/include)
target_link_libraries(inference_service PRIVATE ignis_common)

foreach(service incident_engine stream_service watchdog_service alarm_service)
    add_executable(${service} ${service}/src/main.cpp)
    target_link_libraries(${service} PRIVATE ignis_common)
endforeach()
