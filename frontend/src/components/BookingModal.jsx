import { useEffect, useState } from "react";
import { api, hhmm, minutesBetween, todayISO } from "../api.js";
import Modal from "./Modal.jsx";

// New booking, or reschedule when `appointment` is given. The time picker only offers the
// doctor's free slots; the API still re-checks for overlaps under a row lock.
export default function BookingModal({ doctors, appointment, preset, onSaved, onClose }) {
  const editing = Boolean(appointment);
  const init = appointment ?? preset ?? {};
  const [doctorId, setDoctorId] = useState(init.doctor_id ?? doctors[0]?.id ?? "");
  const [date, setDate] = useState((init.starts_at ?? "").slice(0, 10) || todayISO());
  const [time, setTime] = useState(init.starts_at ? hhmm(init.starts_at) : "");
  const [duration, setDuration] = useState(editing ? minutesBetween(init.starts_at, init.ends_at) : 30);
  const [slots, setSlots] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!doctorId || !date) return;
    api.slots(doctorId, date).then(setSlots).catch((e) => setError(e.message));
  }, [doctorId, date]);

  const own = editing ? hhmm(appointment.starts_at) : null;
  const options = slots.filter((s) => s.available || (editing && hhmm(s.starts_at) === own && date === appointment.starts_at.slice(0, 10)));

  async function submit(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const body = {
      doctor_id: Number(doctorId),
      patient_name: f.get("patient_name").trim(),
      patient_phone: f.get("patient_phone").trim(),
      reason: f.get("reason").trim(),
      starts_at: `${date}T${time}:00`,
      duration_min: Number(duration),
    };
    setBusy(true);
    setError("");
    try {
      if (editing) await api.reschedule(appointment.id, body);
      else await api.book(body);
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Modal eyebrow={editing ? `APPOINTMENT #${appointment.id}` : "NEW APPOINTMENT"} title={editing ? "Reschedule" : "Book an appointment"} onClose={onClose}>
      <form onSubmit={submit}>
        <div className="form-row">
          <label>Patient name<input name="patient_name" required minLength={2} defaultValue={init.patient_name} placeholder="e.g. Ananya Sharma" /></label>
          <label>Phone<input name="patient_phone" required defaultValue={init.patient_phone} placeholder="+91 98xxx xxxxx" /></label>
        </div>
        <label>Reason for visit<input name="reason" defaultValue={init.reason} placeholder="e.g. fever for 3 days" /></label>
        <div className="form-row">
          <label>Doctor
            <select value={doctorId} onChange={(e) => { setDoctorId(e.target.value); setTime(""); }}>
              {doctors.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.specialty}</option>)}
            </select>
          </label>
          <label>Date<input type="date" value={date} onChange={(e) => { setDate(e.target.value); setTime(""); }} /></label>
        </div>
        <label>Time <small className="muted">({options.length} free slots)</small></label>
        <div className="slot-grid">
          {options.map((s) => {
            const t = hhmm(s.starts_at);
            return <button type="button" key={t} className={time === t ? "selected" : ""} onClick={() => setTime(t)}>{t}</button>;
          })}
          {!options.length && <span className="muted">No free slots on this day.</span>}
        </div>
        <label>Duration
          <select value={duration} onChange={(e) => setDuration(e.target.value)}>
            {[15, 30, 45, 60].map((m) => <option key={m} value={m}>{m} minutes</option>)}
          </select>
        </label>
        {error && <div className="alert">{error}</div>}
        <button className="primary full" disabled={busy || !time}>{busy ? "Saving…" : editing ? "Save changes" : time ? `Book ${time}` : "Pick a time"}</button>
      </form>
    </Modal>
  );
}
