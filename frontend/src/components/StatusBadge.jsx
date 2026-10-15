import { STATUS } from "../api.js";

export default function StatusBadge({ value }) {
  return <span className={`status ${value.toLowerCase()}`}>{STATUS[value]?.label ?? value}</span>;
}
