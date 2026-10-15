import { statusLabel } from "../api.js";

export const PriorityBadge = ({ value }) => <span className={`priority ${value.toLowerCase()}`}>{value}</span>;
export const StatusBadge = ({ value }) => <span className={`status ${value.toLowerCase()}`}>{statusLabel(value)}</span>;

export function DueDate({ task }) {
  if (!task.due_date) return <span className="due none">no due date</span>;
  const d = new Date(`${task.due_date}T00:00:00`);
  const label = d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return <span className={`due ${task.overdue ? "late" : ""}`}>{task.overdue ? `overdue · ${label}` : `due ${label}`}</span>;
}
