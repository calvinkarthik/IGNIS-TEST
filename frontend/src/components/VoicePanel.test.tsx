import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { confirmedIncident } from "../test/fixtures";
import { VoicePanel } from "./VoicePanel";

vi.mock("@elevenlabs/react", () => ({
  useConversation: () => ({
    startSession: vi.fn(),
    endSession: vi.fn(),
    sendContextualUpdate: vi.fn(),
    isSpeaking: false,
  }),
}));

describe("VoicePanel", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error("Microphone permission denied")) },
    });
  });

  it("reports microphone permission failure without starting a session", async () => {
    const user = userEvent.setup();
    render(<VoicePanel incident={confirmedIncident} />);
    await user.click(screen.getByRole("button", { name: "Talk to IGNIS" }));
    expect(await screen.findByText("Error")).toBeInTheDocument();
    expect(await screen.findByText("Microphone permission denied")).toBeInTheDocument();
  });
});

