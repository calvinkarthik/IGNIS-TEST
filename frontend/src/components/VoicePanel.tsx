import { useMemo, useState } from "react";
import { useConversation } from "@elevenlabs/react";
import { api } from "../api";
import type { Incident } from "../types";

interface TranscriptLine {
  speaker: "IGNIS" | "OCCUPANT" | "SYSTEM";
  text: string;
}

function readMessage(value: unknown): TranscriptLine | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  const text = record.message ?? record.text;
  if (typeof text !== "string" || !text.trim()) return null;
  const source = String(record.source ?? record.role ?? "system").toLowerCase();
  return {
    speaker: source.includes("user") ? "OCCUPANT" : source.includes("ai") || source.includes("agent") ? "IGNIS" : "SYSTEM",
    text,
  };
}

export function VoicePanel({ incident }: { incident: Incident | null }) {
  const [voiceState, setVoiceState] = useState("VOICE DISABLED");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [toolActivity, setToolActivity] = useState("No tool activity");

  const conversation = useConversation({
    onConnect: () => setVoiceState("LISTENING"),
    onDisconnect: () => setVoiceState("DISCONNECTED"),
    onError: (message: unknown) => {
      setVoiceState("ERROR");
      setTranscript((current) => [
        ...current,
        { speaker: "SYSTEM", text: typeof message === "string" ? message : "Voice session failed." },
      ]);
    },
    onMessage: (message: unknown) => {
      const line = readMessage(message);
      if (line) setTranscript((current) => [...current, line].slice(-30));
    },
    clientTools: {
      confirm_emergency: async (parameters: {
        incident_id: string;
        confirmation: boolean;
        occupant_statement: string;
      }) => {
        setToolActivity("Validating emergency confirmation with FastAPI");
        if (!parameters.confirmation) return JSON.stringify({ success: false, error: "confirmation_required" });
        try {
          const result = await api.confirm(
            parameters.incident_id,
            "voice_agent",
            parameters.occupant_statement,
          );
          return JSON.stringify({ success: true, result });
        } catch (error) {
          return JSON.stringify({ success: false, error: error instanceof Error ? error.message : "request_failed" });
        }
      },
      cancel_escalation: async (parameters: {
        incident_id: string;
        reason: "controlled_flame" | "false_alarm" | "testing" | "other";
        occupant_statement: string;
      }) => {
        setToolActivity("Validating cancellation with FastAPI");
        try {
          const result = await api.cancel(
            parameters.incident_id,
            parameters.reason,
            "voice_agent",
            parameters.occupant_statement,
          );
          return JSON.stringify({ success: true, result });
        } catch (error) {
          return JSON.stringify({ success: false, error: error instanceof Error ? error.message : "request_failed" });
        }
      },
      call_demo_dispatch: async (parameters: { incident_id: string }) => {
        setToolActivity("Backend is enforcing demo-call safety rules");
        try {
          return JSON.stringify({ success: true, result: await api.callDemo(parameters.incident_id) });
        } catch (error) {
          return JSON.stringify({ success: false, error: error instanceof Error ? error.message : "request_failed" });
        }
      },
      get_incident_context: async (parameters: { incident_id: string }) => {
        setToolActivity("Retrieving authoritative incident context");
        try {
          return JSON.stringify({ success: true, context: await api.context(parameters.incident_id) });
        } catch (error) {
          return JSON.stringify({ success: false, error: error instanceof Error ? error.message : "request_failed" });
        }
      },
    },
  });

  const sessionActive = useMemo(
    () => !["VOICE DISABLED", "DISCONNECTED", "ERROR"].includes(voiceState),
    [voiceState],
  );

  const enable = async () => {
    if (!incident) return;
    setVoiceState("REQUESTING MICROPHONE");
    try {
      const permission = await navigator.mediaDevices.getUserMedia({ audio: true });
      permission.getTracks().forEach((track) => track.stop());
      setVoiceState("CONNECTING");
      const { signed_url: signedUrl, context } = await api.signedUrl(incident.incident_id);
      await conversation.startSession({ signedUrl });
      conversation.sendContextualUpdate(JSON.stringify(context));
      setTranscript((current) => [
        ...current,
        { speaker: "SYSTEM", text: "Authoritative incident context supplied to the occupant agent." },
      ]);
    } catch (error) {
      setVoiceState("ERROR");
      setTranscript((current) => [
        ...current,
        {
          speaker: "SYSTEM",
          text: error instanceof Error ? error.message.replaceAll("_", " ") : "Microphone or voice connection failed.",
        },
      ]);
    }
  };

  const disable = async () => {
    await conversation.endSession();
    setVoiceState("VOICE DISABLED");
  };

  return (
    <section className="voice-panel" aria-label="Voice verification and escalation">
      <div className="voice-orb" aria-hidden="true"><span /></div>
      <div className="voice-summary">
        <span className="section-kicker">Occupant verification</span>
        <h2>IGNIS voice</h2>
        <div className="voice-state"><span />{voiceState}</div>
        <p>Voice is opt-in and constrained to typed, backend-validated incident tools.</p>
        <button disabled={!incident} onClick={() => void (sessionActive ? disable() : enable())}>
          {sessionActive ? "End voice session" : "Enable IGNIS voice"}
        </button>
      </div>
      <div className="transcript" aria-live="polite">
        <div className="transcript-heading"><span>Live transcript</span><small>{toolActivity}</small></div>
        <div className="transcript-lines">
          {transcript.length === 0 ? (
            <p>Voice remains silent until enabled by an operator.</p>
          ) : (
            transcript.map((line, index) => (
              <p key={`${line.speaker}-${index}`}><strong>{line.speaker}</strong>{line.text}</p>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
