export default function DoctorLoad({ stats }) {
  const rows = stats?.doctors ?? [];
  return (
    <div className="panel workload">
      <div className="panel-head"><div><h2>Doctor utilisation</h2><p className="muted">Booked minutes / opening hours</p></div></div>
      {rows.map((r) => (
        <div className="bar-row" key={r.doctor_id}>
          <span title={r.doctor_name}>{r.doctor_name.replace(/^Dr\.\s*/, "Dr ")}</span>
          <div className="bar"><i style={{ width: `${Math.min(100, r.utilization * 100)}%` }} className={r.utilization > 0.8 ? "hot" : ""} /></div>
          <em>{Math.round(r.utilization * 100)}%</em>
        </div>
      ))}
      {!rows.length && <div className="empty small">No active doctors</div>}
    </div>
  );
}
