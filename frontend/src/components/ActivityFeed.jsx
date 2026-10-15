import { STATUS } from "../api.js";

const ICON = { booked: "＋", rescheduled: "↻", updated: "✎", status: "→" };

function ago(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

function describe(e) {
  if (e.action === "status") return <>{STATUS[e.from_status]?.label} → <b>{STATUS[e.to_status]?.label}</b>{e.note && <> · {e.note}</>}</>;
  if (e.action === "booked") return <>booked with {e.note}</>;
  if (e.action === "rescheduled") return <>moved to {e.note}</>;
  return <>{e.note}</>;
}

export default function ActivityFeed({ items }) {
  return (
    <div className="panel activity">
      <div className="panel-head"><div><h2>Front-desk activity</h2><p className="muted">Audit trail from the database</p></div></div>
      {items.map((e) => (
        <div className="activity-row" key={e.id}>
          <span className={`activity-icon ${e.action} ${(e.to_status ?? "").toLowerCase()}`}>{ICON[e.action] ?? "•"}</span>
          <div>
            <b>{e.patient_name}</b>
            <small>{describe(e)}</small>
            <small className="time">{ago(e.created_at)}</small>
          </div>
        </div>
      ))}
      {!items.length && <div className="empty small">No activity yet</div>}
      <div className="pipeline"><span>pytest</span><i /><span>Trivy</span><i /><span>GHCR</span><i /><span>Argo CD</span></div>
    </div>
  );
}
