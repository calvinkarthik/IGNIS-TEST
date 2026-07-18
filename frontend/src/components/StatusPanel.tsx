import type { Incident } from "../types";

const label: Record<string, string> = {
  CLEAR: "No sustained hazard",
  SUSPECTED: "Visual signature suspected",
  VERIFYING: "Accumulating evidence",
  CONFIRMED: "Sustained signature confirmed",
  VISUAL_SIGNATURE_LOST: "Previously confirmed signature not visible",
  RESOLVED: "Incident manually resolved",
  DEGRADED: "Local detection degraded",
};

export function StatusPanel({ incident }: { incident: Incident | null }) {
  const hazard = incident?.hazard_state ?? "CLEAR";
  const response = incident?.response_state ?? "IDLE";
  const fire = Math.round((incident?.peak_fire_confidence ?? 0) * 100);
  const smoke = Math.round((incident?.peak_smoke_confidence ?? 0) * 100);
  return (
    <aside className={`status-panel hazard-${hazard.toLowerCase()}`} aria-label="Incident status">
      <div className="section-kicker">Visual hazard state</div>
      <div className="hazard-state" data-testid="hazard-state">
        {hazard.replaceAll("_", " ")}
      </div>
      <p className="state-explainer">{label[hazard]}</p>
      {hazard === "VISUAL_SIGNATURE_LOST" && (
        <p className="truth-warning">The system cannot determine whether the area is safe.</p>
      )}

      <div className="metric-pair">
        <div>
          <span className="metric-label">Fire signature</span>
          <strong>{fire}%</strong>
        </div>
        <div>
          <span className="metric-label">Smoke signature</span>
          <strong>{smoke}%</strong>
        </div>
      </div>

      <dl className="incident-facts">
        <div><dt>Configured zone</dt><dd>{incident?.first_zone ?? "No active incident"}</dd></div>
        <div><dt>Persistence</dt><dd>{(incident?.seconds_persistent ?? 0).toFixed(1)} s</dd></div>
        <div>
          <dt>Visual growth</dt>
          <dd>{incident?.max_growth_percent ? `+${Math.round(incident.max_growth_percent)}% stable` : "Not established"}</dd>
        </div>
        <div>
          <dt>Observed sequence</dt>
          <dd>
            {incident?.smoke_first === true
              ? `Smoke first · ${Math.round(incident.smoke_to_fire_delay_seconds ?? 0)} s lead`
              : "Not determined"}
          </dd>
        </div>
      </dl>

      <div className="response-block">
        <span className="section-kicker">Communication response</span>
        <strong>{response.replaceAll("_", " ")}</strong>
        <small>
          {incident?.call_status === "INITIATED"
            ? "Call request accepted. Connection status unknown."
            : incident?.call_status ?? "No dispatch activity"}
        </small>
      </div>
      <p className="cause-line">Exact cause unconfirmed.</p>
    </aside>
  );
}

