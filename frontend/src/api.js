// All calls are relative (/api/...): nginx (compose) or the Ingress (Kubernetes) routes them.
async function request(path, options = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (res.status === 204) return null;
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join("; ")
      : body.detail;
    throw new Error(detail || `${res.status} ${res.statusText}`);
  }
  return body;
}

const qs = (params) => {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  return q.size ? `?${q}` : "";
};
const json = (method, body) => ({ method, body: JSON.stringify(body) });

export const api = {
  info: () => request("/api/info"),
  stats: (date) => request(`/api/stats${qs({ date })}`),
  events: (limit = 12) => request(`/api/events?limit=${limit}`),
  doctors: () => request("/api/doctors"),
  addDoctor: (d) => request("/api/doctors", json("POST", d)),
  updateDoctor: (id, d) => request(`/api/doctors/${id}`, json("PUT", d)),
  slots: (doctorId, date) => request(`/api/doctors/${doctorId}/slots?date=${date}`),
  appointments: (params) => request(`/api/appointments${qs(params)}`),
  book: (a) => request("/api/appointments", json("POST", a)),
  reschedule: (id, a) => request(`/api/appointments/${id}`, json("PUT", a)),
  remove: (id) => request(`/api/appointments/${id}`, { method: "DELETE" }),
  setStatus: (id, status, note = "") => request(`/api/appointments/${id}/status`, json("POST", { status, note })),
};

export const STATUS = {
  BOOKED: { label: "Booked", next: ["CHECKED_IN", "NO_SHOW", "CANCELLED"] },
  CHECKED_IN: { label: "Waiting", next: ["COMPLETED", "CANCELLED"] },
  COMPLETED: { label: "Completed", next: [] },
  CANCELLED: { label: "Cancelled", next: [] },
  NO_SHOW: { label: "No-show", next: [] },
};
export const ACTION_LABEL = { CHECKED_IN: "Check in", COMPLETED: "Complete", NO_SHOW: "No-show", CANCELLED: "Cancel" };

// Dates are clinic-local wall-clock strings ("2026-10-16T10:30:00"): never shift them through UTC.
export const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const addDays = (iso, n) => {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const hhmm = (iso) => iso.slice(11, 16);
export const prettyDate = (iso) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
export const minutesBetween = (a, b) => (new Date(b) - new Date(a)) / 60000;
