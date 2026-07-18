#include "ignis/protocol.hpp"

#include <iostream>
#include <string>
#include <vector>

#include "test_support.hpp"

int main() {
    using namespace ignis;
    Packet hello;
    hello.type = PacketType::Hello;
    hello.sequence = 0x0102030405060708ULL;
    hello.monotonic_ns = 99;
    const std::string json = "{\"device_id\":\"test\"}";
    hello.payload.assign(json.begin(), json.end());
    std::vector<std::uint8_t> encoded = serialize_packet(hello);
    REQUIRE(kPacketHeaderSize == 32);
    REQUIRE(encoded[0] == 'I' && encoded[1] == 'G' && encoded[2] == 'N' && encoded[3] == 'S');
    REQUIRE(encoded[12] == 0x01 && encoded[19] == 0x08);

    Packet ping;
    ping.type = PacketType::Ping;
    ping.sequence = 2;
    ping.monotonic_ns = 100;
    const std::vector<std::uint8_t> ping_bytes = serialize_packet(ping);
    encoded.insert(encoded.end(), ping_bytes.begin(), ping_bytes.end());

    PacketParser parser;
    std::vector<Packet> packets;
    for (std::size_t index = 0; index < 17; ++index) {
        auto result = parser.feed(&encoded[index], 1);
        REQUIRE(result.ok());
        packets.insert(packets.end(), result.value().begin(), result.value().end());
    }
    auto result = parser.feed(encoded.data() + 17, encoded.size() - 17);
    REQUIRE(result.ok());
    packets.insert(packets.end(), result.value().begin(), result.value().end());
    REQUIRE(packets.size() == 2);
    REQUIRE(packets[0].sequence == hello.sequence);
    REQUIRE(std::string(packets[0].payload.begin(), packets[0].payload.end()) == json);

    std::vector<std::uint8_t> corrupt = serialize_packet(hello);
    corrupt.back() ^= 0xFF;
    REQUIRE(!PacketParser{}.feed(corrupt).ok());
    corrupt = serialize_packet(hello);
    corrupt[0] = 'X';
    REQUIRE(!PacketParser{}.feed(corrupt).ok());
    corrupt = serialize_packet(hello);
    corrupt[5] = 99;
    REQUIRE(!PacketParser{}.feed(corrupt).ok());

    const std::vector<std::uint8_t> jpeg{0xFF, 0xD8, 0x01, 0xFF, 0xD9};
    const auto frame = make_frame_payload("{\"width\":640}", jpeg);
    REQUIRE(frame.size() == 4 + 13 + jpeg.size());
    REQUIRE(frame[0] == 0 && frame[3] == 13);
    std::cout << "protocol_tests: all assertions passed\n";
    return 0;
}

