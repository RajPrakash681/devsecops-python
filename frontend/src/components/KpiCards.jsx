export default function KpiCards({ stats }) {
  const s = stats ?? { total_today: 0, by_status: {}, waiting_now: 0, no_show_rate_30d: 0 };
  const done = s.by_status.COMPLETED ?? 0;
  const live = s.total_today - (s.by_status.CANCELLED ?? 0);
  const cards = [
    { label: "Appointments", value: s.total_today, hint: `${s.by_status.CANCELLED ?? 0} cancelled`, icon: "▦" },
    { label: "Waiting now", value: s.waiting_now, hint: "checked in, not yet seen", icon: "◔", tone: s.waiting_now > 3 ? "warn" : "" },
    { label: "Completed", value: done, hint: live ? `${Math.round((done / live) * 100)}% of the day` : "nothing yet", icon: "✓", tone: "ok" },
    { label: "No-show rate", value: `${Math.round(s.no_show_rate_30d * 100)}%`, hint: "last 30 days", icon: "∅", tone: s.no_show_rate_30d > 0.2 ? "warn" : "" },
  ];
  return (
    <section className="stats">
      {cards.map((c) => (
        <div className={`stat ${c.tone ?? ""}`} key={c.label}>
          <div className="stat-icon">{c.icon}</div>
          <div>
            <small>{c.label}</small>
            <strong>{c.value}</strong>
            <span>{c.hint}</span>
          </div>
        </div>
      ))}
    </section>
  );
}
