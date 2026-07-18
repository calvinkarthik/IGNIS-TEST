export function DemoBanner({ callsEnabled }: { callsEnabled: boolean }) {
  return (
    <div className="demo-banner" role="note" data-testid="demo-banner">
      <span className="demo-mark">DEMO SYSTEM</span>
      <span>Not a certified fire alarm or life-safety device</span>
      <span className="demo-dispatch">
        DEMO DISPATCH NUMBER · {callsEnabled ? "SERVER ALLOWLIST ONLY" : "CALLING DISABLED"}
      </span>
    </div>
  );
}

