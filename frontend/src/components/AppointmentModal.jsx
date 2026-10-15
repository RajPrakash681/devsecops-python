import { useState } from "react";
import { ACTION_LABEL, hhmm, prettyDate, STATUS } from "../api.js";
import Modal from "./Modal.jsx";
import StatusBadge from "./StatusBadge.jsx";

export default function AppointmentModal({ appointment: a, onStatus, onReschedule, onDelete, onClose }) {
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const next = STATUS[a.status].next;

  const run = async (fn) => {
    try {
      await fn();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <Modal eyebrow={`APPOINTMENT #${a.id}`} title={a.patient_name} onClose={onClose}>
      <dl className="details">
        <dt>When</dt><dd>{prettyDate(a.starts_at.slice(0, 10))}, {hhmm(a.starts_at)}–{hhmm(a.ends_at)}</dd>
        <dt>Doctor</dt><dd>{a.doctor_name}</dd>
        <dt>Phone</dt><dd>{a.patient_phone}</dd>
        <dt>Reason</dt><dd>{a.reason || "—"}</dd>
        <dt>Status</dt><dd><StatusBadge value={a.status} /></dd>
      </dl>
      {next.length > 0 && (
        <>
          <label>Note for the audit log<input value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} placeholder="optional, e.g. arrived 10 min early" /></label>
          <div className="action-row">
            {next.map((s) => (
              <button key={s} className={`chip big ${s.toLowerCase()}`} onClick={() => run(() => onStatus(a, s, note.trim()))}>{ACTION_LABEL[s]}</button>
            ))}
          </div>
        </>
      )}
      {error && <div className="alert">{error}</div>}
      <div className="modal-foot">
        {a.status === "BOOKED" && <button className="ghost" onClick={() => onReschedule(a)}>Reschedule</button>}
        <button className="ghost danger" onClick={() => run(() => onDelete(a))}>Delete booking</button>
      </div>
    </Modal>
  );
}
