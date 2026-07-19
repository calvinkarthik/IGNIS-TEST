import { describe, expect, it, vi } from "vitest";
import { initialState, reducer } from "./state";

describe("live state reducer", () => {
  it("restores a complete snapshot on reconnect", () => {
    vi.spyOn(Date, "now").mockReturnValue(1234);
    const state = reducer(
      { ...initialState, connection: "RECONNECTING" },
      {
        type: "MESSAGE",
        envelope: {
          schema_version: 1,
          type: "system_snapshot",
          sent_at: "2026-07-18T12:00:00Z",
          data: {
            demo_system: true,
            demo_calls_enabled: false,
            armed: true,
            devices: [{ device_id: "ignis-qnxpi-01", connected: true }],
            incidents: [],
            latest_frame: null,
            latest_detections: null,
            health: { camera: "HEALTHY" },
          },
        },
      },
    );
    expect(state.connection).toBe("LIVE");
    expect(state.armed).toBe(true);
    expect(state.health.qnx_connected).toBe(true);
    expect(state.health.camera).toBe("HEALTHY");
  });

  it("applies arming updates", () => {
    const state = reducer(initialState, {
      type: "MESSAGE",
      envelope: {
        schema_version: 1,
        type: "arming_update",
        sent_at: "2026-07-18T12:00:00Z",
        data: { armed: true },
      },
    });
    expect(state.armed).toBe(true);
  });
});

