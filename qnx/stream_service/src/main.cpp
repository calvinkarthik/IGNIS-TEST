#include <atomic>
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <netdb.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include "ignis/logging.hpp"
#include "ignis/protocol.hpp"
#include "ignis/time.hpp"

namespace {
std::atomic<bool> running{true};
void stop(int) { running = false; }

std::string env(const char* name, const char* fallback) {
    const char* value = std::getenv(name);
    return value && *value ? value : fallback;
}

std::string json_escape(const std::string& value) {
    std::string result;
    for (char character : value) {
        if (character == '\\' || character == '"') result.push_back('\\');
        if (static_cast<unsigned char>(character) >= 0x20) result.push_back(character);
    }
    return result;
}

bool send_all(int socket_fd, const std::vector<std::uint8_t>& data) {
    std::size_t sent = 0;
    while (sent < data.size()) {
        const ssize_t count = ::send(socket_fd, data.data() + sent, data.size() - sent, 0);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return false;
        sent += static_cast<std::size_t>(count);
    }
    return true;
}

int connect_tcp(const std::string& host, const std::string& port) {
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    addrinfo* addresses = nullptr;
    if (getaddrinfo(host.c_str(), port.c_str(), &hints, &addresses) != 0) return -1;
    int connected = -1;
    for (addrinfo* current = addresses; current; current = current->ai_next) {
        const int candidate = socket(current->ai_family, current->ai_socktype, current->ai_protocol);
        if (candidate < 0) continue;
        if (connect(candidate, current->ai_addr, current->ai_addrlen) == 0) {
            connected = candidate;
            break;
        }
        close(candidate);
    }
    freeaddrinfo(addresses);
    return connected;
}

}  // namespace

int main() {
    std::signal(SIGINT, stop);
    std::signal(SIGTERM, stop);
    const std::string host = env("IGNIS_BACKEND_HOST", "127.0.0.1");
    const std::string port = env("IGNIS_BACKEND_PORT", "9001");
    const std::string device_id = env("IGNIS_DEVICE_ID", "ignis-qnxpi-01");
    const std::string token = env("IGNIS_DEVICE_TOKEN", "");
    const std::string boot_id = std::to_string(static_cast<unsigned long long>(ignis::monotonic_now_ns()));
    if (token.empty()) {
        ignis::log_event("stream_service", ignis::Severity::Critical, boot_id,
                         "DEVICE_TOKEN_MISSING", "IGNIS_DEVICE_TOKEN is required");
        return 78;
    }

    std::uint64_t sequence = 1;
    unsigned backoff_ms = 250;
    while (running) {
        const int socket_fd = connect_tcp(host, port);
        if (socket_fd < 0) {
            ignis::log_event("stream_service", ignis::Severity::Warning, boot_id,
                             "BACKEND_DISCONNECTED", "connection failed; local authority continues");
            std::this_thread::sleep_for(std::chrono::milliseconds(backoff_ms));
            backoff_ms = std::min(10'000U, backoff_ms * 2);
            continue;
        }
        backoff_ms = 250;
        std::ostringstream hello;
        hello << "{\"device_id\":\"" << json_escape(device_id) << "\",\"boot_id\":\""
              << json_escape(boot_id)
              << "\",\"protocol_version\":1,\"software_version\":\"0.1.0\","
                 "\"device_token\":\""
              << json_escape(token)
              << "\",\"capabilities\":[\"camera\",\"fire_smoke_inference\","
                 "\"incident_engine\",\"evidence_buffer\"]}";
        ignis::Packet hello_packet;
        hello_packet.type = ignis::PacketType::Hello;
        hello_packet.sequence = sequence++;
        hello_packet.monotonic_ns = ignis::monotonic_now_ns();
        const std::string hello_text = hello.str();
        hello_packet.payload.assign(hello_text.begin(), hello_text.end());
        if (!send_all(socket_fd, ignis::serialize_packet(hello_packet))) {
            close(socket_fd);
            continue;
        }
        ignis::log_event("stream_service", ignis::Severity::Info, boot_id,
                         "BACKEND_CONNECTED", "authenticated transport handshake sent");

        while (running) {
            const std::string health =
                "{\"status\":\"DEGRADED\",\"camera\":\"UNKNOWN\","
                "\"inference\":\"UNKNOWN\",\"incident_engine\":\"HEALTHY\","
                "\"stream\":\"HEALTHY\",\"watchdog_restart_count\":0}";
            ignis::Packet health_packet;
            health_packet.type = ignis::PacketType::HealthUpdate;
            health_packet.sequence = sequence++;
            health_packet.monotonic_ns = ignis::monotonic_now_ns();
            health_packet.payload.assign(health.begin(), health.end());
            if (!send_all(socket_fd, ignis::serialize_packet(health_packet))) break;
            // Production integration drains durable incident/control IPC before replaceable frames.
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
        close(socket_fd);
    }
    return 0;
}

