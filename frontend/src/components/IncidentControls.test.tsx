import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { confirmedIncident } from "../test/fixtures";
import { IncidentControls } from "./IncidentControls";

describe("IncidentControls", () => {
  it("disables invalid dispatch and requires deliberate confirmation", async () => {
    const user = userEvent.setup();
    render(<IncidentControls incident={confirmedIncident} callsEnabled={false} />);
    expect(screen.getByRole("button", { name: "Call demo contact" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "False alarm" }));
    expect(screen.getByRole("dialog", { name: "Confirm cancel" })).toBeInTheDocument();
    expect(screen.getByText("The action will be preserved in the incident timeline.")).toBeInTheDocument();
  });
});

