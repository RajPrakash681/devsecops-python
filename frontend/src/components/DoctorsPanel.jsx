import { useState } from "react";
import { api } from "../api.js";

export default function DoctorsPanel({ doctors, stats, onChanged }) {
  const [error, setError] = useState("");
  const load = Object.fromEntries((stats?.doctors ?? []).map((d) => [d.doctor_id, d]));

  async function add(e) {
    e.preventDefault();
    const form = e.currentTarget;
    const f = new FormData(form);
    try {
      await api.addDoctor({ name: f.get("name").trim(), specialty: f.get("specialty").trim(), room: f.get("room").trim(), active: true });
      form.reset();
      setError("");
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  }
  const toggle = async (d) => {
    await api.updateDoctor(d.id, { ...d, active: !d.active });
    onChanged();
  };

  return (
    <>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Doctor</th><th>Specialty</th><th>Room</th><th>Today</th><th>Status</th></tr>
          </thead>
          <tbody>
            {doctors.map((d) => (
              <tr key={d.id} className={d.active ? "" : "inactive"}>
                <td data-label="Doctor"><b>{d.name}</b></td>
                <td data-label="Specialty">{d.specialty}</td>
                <td data-label="Room">{d.room || "—"}</td>
                <td data-label="Today">{load[d.id] ? `${load[d.id].booked} booked` : "—"}</td>
                <td className="actions">
                  <button className={`chip ${d.active ? "completed" : "cancelled"}`} onClick={() => toggle(d)}>
                    {d.active ? "Taking bookings" : "On leave"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <form className="inline-form" onSubmit={add}>
        <input name="name" required minLength={3} placeholder="Dr. Full Name" />
        <input name="specialty" required minLength={2} placeholder="Specialty" />
        <input name="room" placeholder="Room" />
        <button className="primary">＋ Add doctor</button>
      </form>
      {error && <div className="alert inset">{error}</div>}
    </>
  );
}
