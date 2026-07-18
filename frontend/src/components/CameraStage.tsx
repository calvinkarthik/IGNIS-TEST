import { useEffect, useMemo, useRef, useState } from "react";
import type { DetectionPacket, FramePacket, ZoneConfiguration } from "../types";

export interface Letterbox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function computeLetterbox(
  containerWidth: number,
  containerHeight: number,
  imageWidth: number,
  imageHeight: number,
): Letterbox {
  if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }
  const scale = Math.min(containerWidth / imageWidth, containerHeight / imageHeight);
  const width = imageWidth * scale;
  const height = imageHeight * scale;
  return { x: (containerWidth - width) / 2, y: (containerHeight - height) / 2, width, height };
}

export function normalizedPoint(letterbox: Letterbox, x: number, y: number): [number, number] {
  return [letterbox.x + x * letterbox.width, letterbox.y + y * letterbox.height];
}

function base64BlobUrl(base64: string): string {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return URL.createObjectURL(new Blob([bytes], { type: "image/jpeg" }));
}

interface Props {
  frame: FramePacket | null;
  detections: DetectionPacket | null;
  zones: ZoneConfiguration | null;
  staleAfterMs?: number;
}

export function CameraStage({ frame, detections, zones, staleAfterMs = 1_000 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [now, setNow] = useState(Date.now());
  const frameAge = frame ? now - frame.receivedAt : Infinity;
  const stale = frameAge > staleAfterMs;

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const update = () => setSize({ width: element.clientWidth, height: element.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const letterbox = useMemo(
    () => computeLetterbox(size.width, size.height, frame?.width ?? 640, frame?.height ?? 480),
    [frame?.height, frame?.width, size.height, size.width],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !size.width || !size.height) return;
    const scale = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(size.width * scale);
    const pixelHeight = Math.round(size.height * scale);
    if (canvas.width !== pixelWidth) canvas.width = pixelWidth;
    if (canvas.height !== pixelHeight) canvas.height = pixelHeight;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.setTransform(scale, 0, 0, scale, 0, 0);

    const clearStage = () => {
      context.clearRect(0, 0, size.width, size.height);
      context.fillStyle = "#090d0f";
      context.fillRect(0, 0, size.width, size.height);
    };

    const drawOverlays = () => {
      context.lineJoin = "round";
      for (const zone of zones?.zones ?? []) {
        if (zone.points.length < 3) continue;
        context.beginPath();
        zone.points.forEach(([x, y], index) => {
          const [px, py] = normalizedPoint(letterbox, x, y);
          if (index === 0) context.moveTo(px, py);
          else context.lineTo(px, py);
        });
        context.closePath();
        context.fillStyle = "rgba(246, 173, 72, 0.06)";
        context.strokeStyle = "rgba(246, 173, 72, 0.56)";
        context.lineWidth = 1;
        context.fill();
        context.stroke();
        const [labelX, labelY] = normalizedPoint(letterbox, zone.points[0][0], zone.points[0][1]);
        context.fillStyle = "rgba(8, 12, 13, 0.84)";
        context.fillRect(labelX, labelY - 24, context.measureText(zone.name).width + 18, 22);
        context.fillStyle = "#f6ad48";
        context.font = "600 11px system-ui";
        context.fillText(zone.name.toUpperCase(), labelX + 9, labelY - 9);
      }
      for (const detection of detections?.detections ?? []) {
        const [x1, y1] = normalizedPoint(letterbox, detection.bbox.x_min, detection.bbox.y_min);
        const [x2, y2] = normalizedPoint(letterbox, detection.bbox.x_max, detection.bbox.y_max);
        const fire = detection.class_name === "fire";
        context.strokeStyle = fire ? "#ff6b35" : "#b7d8d0";
        context.lineWidth = 2;
        context.strokeRect(x1, y1, x2 - x1, y2 - y1);
        const label = `${detection.class_name.toUpperCase()} ${Math.round(detection.confidence * 100)}%`;
        context.font = "700 12px system-ui";
        const labelWidth = context.measureText(label).width + 18;
        context.fillStyle = fire ? "#ff6b35" : "#d9e9e5";
        context.fillRect(x1, Math.max(letterbox.y, y1 - 24), labelWidth, 24);
        context.fillStyle = fire ? "#160b07" : "#0a1211";
        context.fillText(label, x1 + 9, Math.max(letterbox.y + 16, y1 - 7));
      }
    };

    if (!frame) {
      clearStage();
      context.fillStyle = "#8a9b97";
      context.font = "500 14px system-ui";
      context.textAlign = "center";
      context.fillText("WAITING FOR PI CAMERA STREAM", size.width / 2, size.height / 2);
      context.textAlign = "start";
      return;
    }
    let cancelled = false;
    const image = new Image();
    const objectUrl = base64BlobUrl(frame.jpeg_base64);
    image.onload = () => {
      if (cancelled) return;
      clearStage();
      context.drawImage(image, letterbox.x, letterbox.y, letterbox.width, letterbox.height);
      drawOverlays();
      URL.revokeObjectURL(objectUrl);
    };
    image.onerror = () => URL.revokeObjectURL(objectUrl);
    image.src = objectUrl;
    return () => {
      cancelled = true;
      URL.revokeObjectURL(objectUrl);
    };
  }, [detections, frame, letterbox, size.height, size.width, zones]);

  return (
    <div className="camera-stage" ref={containerRef} aria-label="Live camera and detection overlays">
      <canvas ref={canvasRef} />
      <div className="camera-topline">
        <span className="live-dot" />
        <span>{frame?.source_mode === "LAPTOP_SIMULATOR" ? "SIMULATED REPLAY" : "PI CAMERA"}</span>
        <span className="frame-id">FRAME {frame?.frame_sequence ?? "—"}</span>
      </div>
      <div className={`stale-badge ${stale ? "is-stale" : ""}`} role="status">
        {stale ? "VIDEO STALE" : `${Math.max(0, Math.round(frameAge))} MS`}
      </div>
      {frame?.source_mode === "LAPTOP_SIMULATOR" && (
        <div className="simulated-ribbon">LAPTOP SIMULATOR — NOT QNX HARDWARE</div>
      )}
    </div>
  );
}

