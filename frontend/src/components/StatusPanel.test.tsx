import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { confirmedIncident } from "../test/fixtures";
import { StatusPanel } from "./StatusPanel";

describe("StatusPanel", () => {
  it("renders evidence grounded hazard facts", () => {
    render(<StatusPanel incident={confirmedIncident} />);
    expect(screen.getByTestId("hazard-state")).toHaveTextContent("CONFIRMED");
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("Smoke first · 4 s lead")).toBeInTheDocument();
    expect(screen.getByText("Exact cause unconfirmed.")).toBeInTheDocument();
  });

  it("distinguishes accepted call request from connection", () => {
    render(<StatusPanel incident={{ ...confirmedIncident, response_state: "CALL_INITIATED", call_status: "INITIATED" }} />);
    expect(screen.getByText("Call request accepted. Connection status unknown.")).toBeInTheDocument();
    expect(screen.queryByText("Call connected")).not.toBeInTheDocument();
  });
});

