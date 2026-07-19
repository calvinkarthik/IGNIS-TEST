import type { TimelineEvent } from "../types";

function friendly(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());
}

export function Timeline({ events }: { events: TimelineEvent[] }) {
  const visible = events.slice(-8).reverse();
  return (
    <section className="timeline-panel card" aria-label="Incident event timeline">
      <div className="panel-heading">
        <div><span className="section-kicker">Preserved evidence</span><h2>Event timeline</h2></div>
        <span className="timeline-count">{events.length} EVENTS</span>
      </div>
      {visible.length === 0 ? (
        <p className="empty-copy">The timeline will preserve Pi observations and communication actions.</p>
      ) : (
        <ol className="timeline-list">
          {visible.map((event, index) => (
            <li key={event.id ?? `${event.event_type}-${index}`}>
              <span className="timeline-node" />
              <div>
                <strong>{friendly(event.event_type)}</strong>
                <span>{event.source}</span>
              </div>
              <time>{event.received_at ? new Date(event.received_at).toLocaleTimeString() : "live"}</time>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

