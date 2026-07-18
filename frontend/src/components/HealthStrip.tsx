import type { Health } from "../types";

function HealthItem({ label, value }: { label: string; value: string | number | undefined }) {
  const shown = value ?? "UNKNOWN";
  const status = String(shown).toUpperCase();
  const tone = ["HEALTHY", "LIVE", "TRUE"].includes(status)
    ? "healthy"
    : ["FAILED", "UNAVAILABLE", "OFFLINE", "FALSE"].includes(status)
      ? "failed"
      : "warning";
  return (
    <div className="health-item">
      <span className={`health-light ${tone}`} />
      <span>{label}</span>
      <strong>{String(shown)}</strong>
    </div>
  );
}

export function HealthStrip({ health, connection }: { health: Health; connection: string }) {
  return (
    <section className="health-strip" aria-label="Pi and service health">
      <HealthItem label="Laptop link" value={connection} />
      <HealthItem label="QNX Pi" value={health.qnx_connected ? "LIVE" : "OFFLINE"} />
      <HealthItem label="Camera" value={health.camera} />
      <HealthItem label="Inference" value={health.inference} />
      <HealthItem label="Incident engine" value={health.incident_engine} />
      <div className="health-number"><span>Inference</span><strong>{health.inference_latency_ms?.toFixed(0) ?? "—"} ms</strong></div>
      <div className="health-number"><span>Watchdog restarts</span><strong>{health.watchdog_restart_count ?? 0}</strong></div>
    </section>
  );
}

