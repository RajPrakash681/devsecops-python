import { hhmm, minutesBetween } from "../api.js";
import StatusBadge from "./StatusBadge.jsx";


// Day view: one column per doctor, one row per slot. Opening hours and slot length come from
// the backend (/api/info), so the grid always matches what the API will accept. Empty future slots are clickable
// and open the booking form pre-filled with that doctor and time. On phones the CSS swaps this
// grid for the agenda list below it.
export default function ScheduleGrid({ date, doctors, appointments, nowISO, hours, onOpen, onBookAt }) {
  const { opening_hour: OPEN = 8, closing_hour: CLOSE = 21, slot_minutes: STEP = 30 } = hours ?? {};
  const ROWS = ((CLOSE - OPEN) * 60) / STEP;
  const rowOf = (iso) => (Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16)) - OPEN * 60) / STEP;
  const label = (i) => {
    const m = OPEN * 60 + i * STEP;
    return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  };
  const visible = appointments.filter((a) => a.status !== "CANCELLED");
  const nowRow = nowISO.slice(0, 10) === date ? Math.floor(rowOf(nowISO)) : -1;
  if (!doctors.length) return <div className="empty">Add a doctor first (Doctors page).</div>;
  return (
    <>
      <div className="schedule-wrap">
        <div className="schedule" style={{ gridTemplateColumns: `58px repeat(${doctors.length}, minmax(140px, 1fr))` }}>
          <div className="corner" />
          {doctors.map((d, c) => (
            <div className="doc-head" key={d.id} style={{ gridColumn: c + 2 }}>
              <b>{d.name}</b>
              <small>{d.specialty} · room {d.room || "–"}</small>
            </div>
          ))}
          {Array.from({ length: ROWS }, (_, r) => (
            <div key={`t${r}`} className={`time ${r === nowRow ? "now" : ""}`} style={{ gridRow: r + 2 }}>{label(r)}</div>
          ))}
          {doctors.map((d, c) =>
            Array.from({ length: ROWS }, (_, r) => {
              const at = `${date}T${label(r)}:00`;
              const past = at <= nowISO;
              return (
                <button key={`${d.id}-${r}`} className={`cell ${past ? "past" : ""} ${r === nowRow ? "now" : ""}`}
                  style={{ gridColumn: c + 2, gridRow: r + 2 }} disabled={past}
                  title={past ? "" : `Book ${d.name} at ${label(r)}`} onClick={() => onBookAt(d.id, at)} />
              );
            }))}
          {visible.map((a) => {
            const c = doctors.findIndex((d) => d.id === a.doctor_id);
            if (c < 0) return null;
            const start = rowOf(a.starts_at);
            const span = Math.max(1, Math.ceil(minutesBetween(a.starts_at, a.ends_at) / STEP));
            if (start < 0 || start >= ROWS) return null;
            return (
              <button key={a.id} className={`appt ${a.status.toLowerCase()} ${span === 1 ? "short" : ""}`} onClick={() => onOpen(a)}
                title={`${a.patient_name} · ${hhmm(a.starts_at)}–${hhmm(a.ends_at)} · ${a.reason || "consultation"}`}
                style={{ gridColumn: c + 2, gridRow: `${Math.floor(start) + 2} / span ${span}` }}>
                <b>{a.patient_name}</b>
                <small>{hhmm(a.starts_at)}–{hhmm(a.ends_at)}<span className="why"> · {a.reason || "consultation"}</span></small>
                <StatusBadge value={a.status} />
              </button>
            );
          })}
        </div>
      </div>
      <div className="agenda">
        {visible.map((a) => (
          <button key={a.id} className={`agenda-row ${a.status.toLowerCase()}`} onClick={() => onOpen(a)}>
            <span className="agenda-time">{hhmm(a.starts_at)}</span>
            <span className="agenda-body">
              <b>{a.patient_name}</b>
              <small>{a.doctor_name} · {a.reason || "consultation"}</small>
            </span>
            <StatusBadge value={a.status} />
          </button>
        ))}
        {!visible.length && <div className="empty">No appointments on this day.</div>}
      </div>
    </>
  );
}
