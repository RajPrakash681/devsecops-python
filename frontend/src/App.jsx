import { useCallback, useEffect, useMemo, useState } from "react";
import { addDays, api, prettyDate, STATUS, todayISO } from "./api.js";
import ActivityFeed from "./components/ActivityFeed.jsx";
import AppointmentModal from "./components/AppointmentModal.jsx";
import AppointmentTable from "./components/AppointmentTable.jsx";
import BookingModal from "./components/BookingModal.jsx";
import DoctorLoad from "./components/DoctorLoad.jsx";
import DoctorsPanel from "./components/DoctorsPanel.jsx";
import KpiCards from "./components/KpiCards.jsx";
import ScheduleGrid from "./components/ScheduleGrid.jsx";
import Sidebar from "./components/Sidebar.jsx";

const TITLES = { schedule: "Day schedule", list: "Appointments", doctors: "Doctors" };

function localNowISO() {
  const d = new Date();
  return `${todayISO()}T${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}:00`;
}

export default function App() {
  const [view, setView] = useState("schedule");
  const [date, setDate] = useState(todayISO());
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({ doctor: "", status: "", q: "" });
  const [opened, setOpened] = useState(null);       // appointment shown in the details modal
  const [booking, setBooking] = useState(null);     // {appointment?} or {preset?} -> booking modal

  const load = useCallback(async () => {
    try {
      const [d, a, s, e, i] = await Promise.all([api.doctors(), api.appointments({ date }), api.stats(date), api.events(), api.info()]);
      setDoctors(d);
      setAppointments(a);
      setStats(s);
      setEvents(e);
      setInfo(i);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000); // other desks' changes appear without a reload
    return () => clearInterval(id);
  }, [load]);

  const active = doctors.filter((d) => d.active);
  const listed = useMemo(() => {
    const q = filters.q.toLowerCase();
    return appointments.filter((a) =>
      (!filters.doctor || a.doctor_id === Number(filters.doctor)) &&
      (!filters.status || a.status === filters.status) &&
      (!q || a.patient_name.toLowerCase().includes(q) || a.patient_phone.includes(q)));
  }, [appointments, filters]);

  const setStatus = async (a, status, note = "") => {
    await api.setStatus(a.id, status, note);
    setOpened(null);
    load();
  };
  const remove = async (a) => {
    if (!window.confirm(`Delete the booking for ${a.patient_name}? (Use Cancel to keep it on record.)`)) return;
    await api.remove(a.id);
    setOpened(null);
    load();
  };
  const saved = () => {
    setBooking(null);
    load();
  };

  return (
    <div className="app">
      <Sidebar view={view} onView={setView} info={info} />
      <main className="main">
        <header>
          <div>
            <p className="eyebrow">CLINIC / {TITLES[view].toUpperCase()}</p>
            <h1>{prettyDate(date)}</h1>
            <div className="day-nav">
              <button onClick={() => setDate(addDays(date, -1))} aria-label="Previous day">‹</button>
              <button onClick={() => setDate(todayISO())} className={date === todayISO() ? "on" : ""}>Today</button>
              <button onClick={() => setDate(addDays(date, 1))} aria-label="Next day">›</button>
              <input type="date" value={date} onChange={(e) => e.target.value && setDate(e.target.value)} />
            </div>
          </div>
          <button className="primary" disabled={!active.length} onClick={() => setBooking({})}>＋ Book appointment</button>
        </header>

        {error && <div className="alert">⚠ Backend unavailable ({error}). Start the backend and PostgreSQL, then refresh.</div>}
        <KpiCards stats={stats} />

        <section className="content-grid">
          <div className="panel main-panel">
            <div className="panel-head">
              <div>
                <h2>{TITLES[view]}</h2>
                <p className="muted">
                  {view === "doctors" ? `${active.length} of ${doctors.length} taking bookings`
                    : view === "list" ? `${listed.length} of ${appointments.length} appointments`
                    : `${active.length} doctors · click a free slot to book`}
                </p>
              </div>
              {view === "list" && (
                <div className="toolbar">
                  <input className="search" placeholder="Patient name or phone…" value={filters.q}
                    onChange={(e) => setFilters({ ...filters, q: e.target.value })} />
                  <select value={filters.doctor} onChange={(e) => setFilters({ ...filters, doctor: e.target.value })}>
                    <option value="">All doctors</option>
                    {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                  <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                    <option value="">All statuses</option>
                    {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                  </select>
                </div>
              )}
            </div>
            {loading ? <div className="empty">Loading…</div>
              : view === "schedule" ? <ScheduleGrid date={date} doctors={active} appointments={appointments} nowISO={localNowISO()} hours={info}
                  onOpen={setOpened} onBookAt={(doctor_id, starts_at) => setBooking({ preset: { doctor_id, starts_at } })} />
              : view === "list" ? <AppointmentTable appointments={listed} onOpen={setOpened} onStatus={(a, s) => setStatus(a, s)} />
              : <DoctorsPanel doctors={doctors} stats={stats} onChanged={load} />}
          </div>
          <div className="side-col">
            <DoctorLoad stats={stats} />
            <ActivityFeed items={events} />
          </div>
        </section>
      </main>
      {opened && <AppointmentModal appointment={opened} onStatus={setStatus} onDelete={remove} onClose={() => setOpened(null)}
        onReschedule={(a) => { setOpened(null); setBooking({ appointment: a }); }} />}
      {booking && <BookingModal doctors={active} appointment={booking.appointment} preset={booking.preset} onSaved={saved} onClose={() => setBooking(null)} />}
    </div>
  );
}
