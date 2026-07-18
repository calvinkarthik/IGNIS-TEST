import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DemoBanner } from "./DemoBanner";

describe("DemoBanner", () => {
  it("always identifies the prototype and disabled calling", () => {
    render(<DemoBanner callsEnabled={false} />);
    expect(screen.getByTestId("demo-banner")).toHaveTextContent("DEMO SYSTEM");
    expect(screen.getByTestId("demo-banner")).toHaveTextContent("Not a certified fire alarm");
    expect(screen.getByTestId("demo-banner")).toHaveTextContent("CALLING DISABLED");
  });
});

