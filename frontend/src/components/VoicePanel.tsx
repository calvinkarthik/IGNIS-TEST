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

function dynamicVariables(context: Record<string, unknown>): Record<string, string | number | boolean> {
  const variables: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(context)) {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      variables[key] = value;
    } else if (value === null || value === undefined) {
      variables[key] = "unknown";
    } else {
      variables[key] = JSON.stringify(value);
    }
  }
  return variables;
}

function incidentVoicePrompt(context: Record<string, unknown>): string {
  return [
    "You are IGNIS calling about the active camera fire/smoke demo incident.",
    "You already have the incident information. Do not ask the occupant to tell you what incident you are calling about.",
    "Open by saying IGNIS detected a sustained fire or smoke signature in the camera view.",
    "Ask exactly whether this is a real emergency or the planned phone/still-image demo.",
    "If the occupant says demo, test, phone image, video, screenshot, controlled, or false alarm, call cancel_escalation.",
    "If the occupant says real emergency, call confirm_emergency, tell them to move away and leave if safe, then call_demo_dispatch.",
    "Use this incident context:",
    JSON.stringify(context),
  ].join("\n");
}

export function VoicePanel({ incident }: { incident: Incident | null }) {
  const [voiceState, setVoiceState] = useState("VOICE DISABLED");
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [, setToolActivity] = useState("No tool activity");

  const conversation = useConversation({
    volume: 0,
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
  const isError = voiceState === "ERROR";
  const isListening = voiceState === "LISTENING";
  const isSpeaking = conversation.isSpeaking;
  const lastSystemLine = [...transcript].reverse().find((line) => line.speaker === "SYSTEM");
  const visibleTranscript = transcript.filter((line) => line.speaker !== "SYSTEM").slice(-6);

  const enable = async () => {
    if (!incident) return;
    setVoiceState("REQUESTING MICROPHONE");
    try {
      const permission = await navigator.mediaDevices.getUserMedia({ audio: true });
      permission.getTracks().forEach((track) => track.stop());
      setVoiceState("CONNECTING");
      const { signed_url: signedUrl, context } = await api.signedUrl(incident.incident_id);
      const variables = dynamicVariables(context);
      await conversation.startSession({
        signedUrl,
        dynamicVariables: variables,
        overrides: {
          agent: {
            firstMessage: `IGNIS detected a sustained fire or smoke signature in the camera view. Is this a real emergency, or is this the phone demo image?`,
            prompt: { prompt: incidentVoicePrompt(context) },
          },
        },
      });
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
    <section className="voice-panel card" aria-label="Voice verification and escalation">
      <div className="voice-header">
        <div className={`voice-mic ${sessionActive ? "active" : ""}`} aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <rect x="9" y="2" width="6" height="12" rx="3" />
            <path d="M5 10v1a7 7 0 0 0 14 0v-1" />
            <path d="M12 18v3M9 21h6" />
          </svg>
        </div>
        <div className={`voice-wave ${isSpeaking ? "active" : ""}`} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
        <div className="voice-live">
          <span className={`voice-live-dot ${isListening ? "active" : ""}`} />
          {isListening ? "Live" : sessionActive ? "Connecting" : "Idle"}
        </div>
      </div>
      <div className="voice-quote" aria-live="polite">
        {isError ? (
          <>
            <span className="voice-status-label">Error</span>
          <p className="quote-text">{lastSystemLine?.text ?? "Voice session failed."}</p>
          </>
        ) : visibleTranscript.length ? (
          <ol className="voice-transcript">
            {visibleTranscript.map((line, index) => (
              <li key={`${line.speaker}-${index}`}>
                <span>{line.speaker}</span>
                <p>{line.text}</p>
              </li>
            ))}
          </ol>
        ) : (
          <p className="quote-text quote-placeholder">
            IGNIS transcript will appear here when the voice session starts.
          </p>
        )}
      </div>
      <button disabled={!incident} onClick={() => void (sessionActive ? disable() : enable())}>
        {sessionActive ? "End conversation" : "Talk to IGNIS"}
      </button>
      <span className="voice-credit">Powered by ElevenLabs</span>
    </section>
  );
}
