import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api";
import type { Zone, ZoneConfiguration } from "../types";

interface Props {
  configuration: ZoneConfiguration | null;
  onSaved: (configuration: ZoneConfiguration) => void;
}

function polygonArea(points: [number, number][]) {
  return Math.abs(
    points.reduce((sum, [x, y], index) => {
      const [nextX, nextY] = points[(index + 1) % points.length] ?? [0, 0];
      return sum + x * nextY - nextX * y;
    }, 0) / 2,
  );
}

export function ZoneEditor({ configuration, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<ZoneConfiguration | null>(configuration);
  const [selected, setSelected] = useState(0);
  const [status, setStatus] = useState("");
  const surfaceRef = useRef<HTMLDivElement>(null);

  useEffect(() => setDraft(configuration), [configuration]);
  const zone = draft?.zones[selected] ?? null;
  const valid = useMemo(
    () => Boolean(zone && zone.name.trim() && zone.points.length >= 3 && polygonArea(zone.points) >= 0.0001),
    [zone],
  );

  const updateZone = (update: (zone: Zone) => Zone) => {
    if (!draft || !zone) return;
    setDraft({
      ...draft,
      zones: draft.zones.map((item, index) => (index === selected ? update(item) : item)),
    });
  };

  const addPoint = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!zone || event.target !== event.currentTarget) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const point: [number, number] = [
      Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    ];
    updateZone((item) => ({ ...item, points: [...item.points, point] }));
  };

  const movePoint = (index: number, event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    const move = (moveEvent: PointerEvent) => {
      const rect = surfaceRef.current?.getBoundingClientRect();
      if (!rect) return;
      const point: [number, number] = [
        Math.max(0, Math.min(1, (moveEvent.clientX - rect.left) / rect.width)),
        Math.max(0, Math.min(1, (moveEvent.clientY - rect.top) / rect.height)),
      ];
      updateZone((item) => ({
        ...item,
        points: item.points.map((current, pointIndex) => (pointIndex === index ? point : current)),
      }));
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const newZone = () => {
    if (!draft) return;
    const next: Zone = { id: `zone-${Date.now()}`, name: "New zone", points: [] };
    setDraft({ ...draft, zones: [...draft.zones, next] });
    setSelected(draft.zones.length);
  };

  const deleteZone = () => {
    if (!draft || !zone) return;
    setDraft({ ...draft, zones: draft.zones.filter((_, index) => index !== selected) });
    setSelected(Math.max(0, selected - 1));
  };

  const save = async () => {
    if (!draft || !valid) return;
    setStatus("Saving and awaiting Pi delivery…");
    try {
      const next = { ...draft, configuration_version: draft.configuration_version + 1 };
      const result = await api.saveZones(next);
      onSaved(result.configuration);
      setStatus(result.acknowledged ? "Pi acknowledged the configuration." : "Saved; Pi acknowledgement pending.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message.replaceAll("_", " ") : "Save failed");
    }
  };

  if (!open) {
    return <button className="zone-edit-trigger" onClick={() => setOpen(true)}>Edit configured zones</button>;
  }

  return (
    <div className="zone-editor-backdrop">
      <section className="zone-editor" role="dialog" aria-modal="true" aria-label="Zone editor">
        <div className="zone-editor-header">
          <div><span className="section-kicker">Configuration v{draft?.configuration_version ?? "—"}</span><h2>Camera zones</h2></div>
          <button className="ghost" onClick={() => { setDraft(configuration); setOpen(false); }}>Cancel</button>
        </div>
        <div className="zone-editor-body">
          <aside>
            {(draft?.zones ?? []).map((item, index) => (
              <button key={item.id} className={index === selected ? "selected" : ""} onClick={() => setSelected(index)}>{item.name}</button>
            ))}
            <button className="secondary" onClick={newZone}>+ New zone</button>
          </aside>
          <div>
            {zone ? (
              <>
                <label>Zone name<input value={zone.name} maxLength={48} onChange={(event) => updateZone((item) => ({ ...item, name: event.target.value }))} /></label>
                <div className="zone-surface" ref={surfaceRef} onClick={addPoint}>
                  <span>Click to add vertices · drag to move</span>
                  {zone.points.map(([x, y], index) => (
                    <button
                      key={`${index}-${x}-${y}`}
                      className="zone-vertex"
                      style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
                      aria-label={`Move vertex ${index + 1}`}
                      onPointerDown={(event) => movePoint(index, event)}
                      onDoubleClick={() => updateZone((item) => ({ ...item, points: item.points.filter((_, pointIndex) => pointIndex !== index) }))}
                    >{index + 1}</button>
                  ))}
                </div>
                <p className={valid ? "valid-zone" : "invalid-zone"}>{valid ? "Valid normalized polygon" : "Add at least three non-collinear points"}</p>
                <button className="danger-link" onClick={deleteZone}>Delete zone</button>
              </>
            ) : <p>Create a zone to begin.</p>}
          </div>
        </div>
        <div className="zone-editor-footer"><span role="status">{status || "Pi keeps its last valid local configuration while disconnected."}</span><button disabled={!valid} onClick={() => void save()}>Save zone configuration</button></div>
      </section>
    </div>
  );
}

