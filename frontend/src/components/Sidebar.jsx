const NAV = [
  { key: "schedule", icon: "▦", label: "Day schedule" },
  { key: "list", icon: "☰", label: "Appointments" },
  { key: "doctors", icon: "✚", label: "Doctors" },
];

export default function Sidebar({ view, onView, info }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark">✚</span>
        <div>
          <b>ClinicFlow</b>
          <small>Front desk</small>
        </div>
      </div>
      <nav>
        {NAV.map((n) => (
          <button key={n.key} className={view === n.key ? "active" : ""} onClick={() => onView(n.key)}>
            <i>{n.icon}</i> <span>{n.label}</span>
          </button>
        ))}
      </nav>
      <div className="side-bottom">
        <div className="build">
          <strong>Running build</strong>
          {info ? (
            <p>
              <code>{info.version}</code> · {info.environment}
              <br />
              <span title="pod that answered">{info.pod}</span>
            </p>
          ) : (
            <p>backend unreachable</p>
          )}
        </div>
        <div className="profile">
          <div className="avatar">RP</div>
          <div>
            <b>Raj Prakash</b>
            <small>Front-desk admin</small>
          </div>
        </div>
      </div>
    </aside>
  );
}
