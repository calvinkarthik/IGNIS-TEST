import { describe, expect, it } from "vitest";
import { computeLetterbox, normalizedPoint } from "./CameraStage";

describe("camera geometry", () => {
  it("maps normalized coordinates through horizontal letterboxing", () => {
    const box = computeLetterbox(1000, 1000, 640, 480);
    expect(box).toEqual({ x: 0, y: 125, width: 1000, height: 750 });
    expect(normalizedPoint(box, 0.5, 0.5)).toEqual([500, 500]);
    expect(normalizedPoint(box, 0, 0)).toEqual([0, 125]);
  });

  it("maps normalized coordinates through vertical letterboxing", () => {
    const box = computeLetterbox(1600, 600, 640, 480);
    expect(box.width).toBe(800);
    expect(box.x).toBe(400);
    expect(normalizedPoint(box, 1, 1)).toEqual([1200, 600]);
  });
});

