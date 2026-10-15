import { ACTION_LABEL, hhmm, STATUS } from "../api.js";
import StatusBadge from "./StatusBadge.jsx";

export default function AppointmentTable({ appointments, onOpen, onStatus }) {
  if (!appointments.length) return <div className="empty">No appointments match these filters.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Patient</th>
            <th>Doctor</th>
            <th>Status</th>
            <th aria-label="actions" />
          </tr>
        </thead>
        <tbody>
          {appointments.map((a) => (
            <tr key={a.id}>
              <td data-label="Time"><b className="mono">{hhmm(a.starts_at)}–{hhmm(a.ends_at)}</b></td>
              <td data-label="Patient">
                <button className="linkish" onClick={() => onOpen(a)}>
                  <b>{a.patient_name}</b>
                  <small>{a.patient_phone} · {a.reason || "consultation"}</small>
                </button>
              </td>
              <td data-label="Doctor">{a.doctor_name}</td>
              <td data-label="Status"><StatusBadge value={a.status} /></td>
              <td className="actions">
                {STATUS[a.status].next.map((s) => (
                  <button key={s} className={`chip ${s.toLowerCase()}`} onClick={() => onStatus(a, s)}>{ACTION_LABEL[s]}</button>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
