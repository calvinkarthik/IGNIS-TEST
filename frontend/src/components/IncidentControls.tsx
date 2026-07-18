import { useState } from "react";
import { api } from "../api";
import type { Incident } from "../types";

type Action = "confirm" | "cancel" | "call" | "reset";

interface Props {
  incident: Incident | null;
  callsEnabled: boolean;
}

export function IncidentControls({ incident, callsEnabled }: Props) {
  const [pending, setPending] = useState<Action | null>(null);
  const [confirming, setConfirming] = useState<Action | null>(null);
  const [result, setResult] = useState("");
  const confirmed = incident?.confirmed_at != null;
  const cancelled = incident?.response_state === "CANCELLED";

  const execute = async (action: Action) => {
    if (!incident) return;
    setPending(action);
    setResult("");
    try {
      if (action === "confirm") await api.confirm(incident.incident_id, "manual", "Operator confirmed emergency");
      if (action === "cancel") await api.cancel(incident.incident_id, "false_alarm", "manual", "Operator marked false alarm");
      if (action === "call") await api.callDemo(incident.incident_id);
      if (action === "reset") await api.reset(incident.incident_id);
      setResult(action === "call" ? "Call request accepted; connection status remains unknown." : "Backend accepted the action.");
    } catch (error) {
      setResult(error instanceof Error ? error.message.replaceAll("_", " ") : "Action failed");
    } finally {
      setPending(null);
      setConfirming(null);
    }
  };

  return (
    <section className="controls-panel" aria-label="Incident controls">
      <div className="control-buttons">
        <button disabled={!confirmed || cancelled || pending !== null} onClick={() => setConfirming("confirm")}>
          Confirm emergency
        </button>
        <button className="secondary" disabled={!incident || cancelled || pending !== null} onClick={() => setConfirming("cancel")}>
          False alarm
        </button>
        <button
          className="dispatch"
          disabled={!confirmed || cancelled || !callsEnabled || pending !== null || Boolean(incident?.call_status)}
          onClick={() => setConfirming("call")}
        >
          Call demo contact
        </button>
        <button
          className="ghost"
          disabled={!incident || !["CANCELLED", "CALL_COMPLETED", "CALL_FAILED"].includes(incident.response_state) || pending !== null}
          onClick={() => setConfirming("reset")}
        >
          Reset reviewed incident
        </button>
      </div>
      <div className="action-status" role="status">
        {pending ? `Submitting ${pending}…` : result || "Every action is validated and recorded by FastAPI."}
      </div>
      {confirming && (
        <div className="confirmation-backdrop" role="presentation">
          <div className="confirmation-card" role="dialog" aria-modal="true" aria-label={`Confirm ${confirming}`}>
            <span className="section-kicker">Deliberate action</span>
            <h3>{confirming === "call" ? "Request the demo dispatch call?" : `Confirm ${confirming}?`}</h3>
            <p>
              {confirming === "call"
                ? "Only the server-side allowlisted demo number is eligible. This does not contact emergency services."
                : "The action will be preserved in the incident timeline."}
            </p>
            <div className="modal-actions">
              <button className="secondary" onClick={() => setConfirming(null)}>Go back</button>
              <button onClick={() => void execute(confirming)}>Confirm action</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

