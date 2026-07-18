CXX ?= g++
CXXFLAGS ?= -std=c++1z -O2 -Wall -Wextra -Wpedantic
INCLUDES = -Icommon/include -Itests
COMMON_SOURCES = common/src/geometry.cpp common/src/incident.cpp common/src/protocol.cpp
BUILD_DIR = build/portable
TESTS = geometry_tests incident_engine_tests protocol_tests model_decoder_tests

.PHONY: portable-test portable-build clean qnx-build

portable-build: $(addprefix $(BUILD_DIR)/,$(TESTS))

portable-test: portable-build
	$(BUILD_DIR)/geometry_tests
	$(BUILD_DIR)/incident_engine_tests
	$(BUILD_DIR)/protocol_tests
	$(BUILD_DIR)/model_decoder_tests

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/geometry_tests: tests/geometry_tests.cpp common/src/geometry.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

$(BUILD_DIR)/incident_engine_tests: tests/incident_engine_tests.cpp common/src/incident.cpp common/src/geometry.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

$(BUILD_DIR)/protocol_tests: tests/protocol_tests.cpp common/src/protocol.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

$(BUILD_DIR)/model_decoder_tests: tests/model_decoder_tests.cpp common/src/geometry.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

qnx-build:
	./scripts/build-qnx.sh release

clean:
	rm -rf build

