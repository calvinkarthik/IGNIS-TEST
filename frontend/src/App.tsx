import { useEffect, useMemo, useState } from "react";
import { CameraStage } from "./components/CameraStage";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { HealthStrip } from "./components/HealthStrip";
import { IncidentControls } from "./components/IncidentControls";
import { StatusPanel } from "./components/StatusPanel";
import { Timeline } from "./components/Timeline";
import { VoicePanel } from "./components/VoicePanel";
import { api } from "./api";
import { useIgnisSocket } from "./hooks/useIgnisSocket";
import type { ZoneConfiguration } from "./types";

export default function App() {
  const { state, refreshEvents } = useIgnisSocket();
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [localZones, setLocalZones] = useState<ZoneConfiguration | null>(null);
  const [armingPending, setArmingPending] = useState(false);
  const incident = useMemo(
    () =>
      state.incidents.find((item) => item.incident_id === selectedIncidentId) ??
      state.incidents[0] ??
      null,
    [selectedIncidentId, state.incidents],
  );

  useEffect(() => {
    if (state.zones) setLocalZones(state.zones);
  }, [state.zones]);

  useEffect(() => {
    if (incident) void refreshEvents(incident.incident_id);
  }, [incident?.incident_id]);

  const toggleArmed = async () => {
    setArmingPending(true);
    try {
      await api.setArmed(!state.armed);
    } finally {
      setArmingPending(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="main-header">
        <div className="brand-block">
          <div className="ignis-mark" aria-hidden="true"><span>I</span></div>
          <div><h1>IGNIS</h1><p>Visual incident intelligence</p></div>
        </div>
        <div className="header-center"><h2>QNX edge authority</h2></div>
        <button
          className={`arming-toggle ${state.armed ? "armed" : "unarmed"}`}
          disabled={armingPending}
          onClick={() => void toggleArmed()}
        >
          {state.armed ? "Armed" : "Unarmed"}
        </button>
        <div className={`connection-pill ${state.connection.toLowerCase()}`}>
          <span />{state.connection}
        </div>
      </header>

      <main>
        <section className="app-grid">
          <StatusPanel incident={incident} />

          <div className="camera-column card">
            <div className="panel-heading">
              <div><span className="section-kicker">Observed evidence</span><h2>Live camera</h2></div>
              <span className="stream-meta">640 × 480 · bounded stream</span>
            </div>
            <CameraStage frame={state.frame} detections={state.detections} zones={localZones} />
            <div className="camera-caption">
              <span>Boxes and zones align to the source image.</span>
              <span>{state.detections?.inference_duration_ms?.toFixed(1) ?? "—"} ms inference</span>
            </div>
          </div>

          <div className="side-column">
            <ErrorBoundary fallbackLabel="IGNIS voice">
              <VoicePanel incident={state.armed ? incident : null} />
            </ErrorBoundary>
            <Timeline events={state.events} />
          </div>
        </section>

        <section className="secondary-grid">
          <aside className="history-panel card">
            <div className="panel-heading">
              <div><span className="section-kicker">SQLite record</span><h2>Incident history</h2></div>
              <span>{state.incidents.length}</span>
            </div>
            {state.incidents.length === 0 ? (
              <p className="empty-copy">No incidents have been received from the Pi.</p>
            ) : (
              <div className="history-list">
                {state.incidents.slice(0, 5).map((item) => (
                  <button
                    key={item.incident_id}
                    className={item.incident_id === incident?.incident_id ? "active" : ""}
                    onClick={() => setSelectedIncidentId(item.incident_id)}
                  >
                    <span>{item.hazard_state.replaceAll("_", " ")}</span>
                    <strong>{item.first_zone ?? "Unconfigured area"}</strong>
                    <small>{new Date(item.updated_at).toLocaleString()}</small>
                  </button>
                ))}
              </div>
            )}
          </aside>
          <IncidentControls incident={incident} callsEnabled={state.demoCallsEnabled && state.armed} />
        </section>
      </main>

      <footer>
        <HealthStrip health={state.health} connection={state.connection} />
        <div className="footer-truth">
          <span>IGNIS prototype · visual observations are not certainty</span>
          <span>Never replaces certified alarms or normal emergency procedures</span>
        </div>
      </footer>
    </div>
  );
}
