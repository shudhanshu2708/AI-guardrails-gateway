export function percent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

export default function Metric({ label, value, tone = "neutral" }) {
  return (
    <div className={`metric metric-${tone}`}>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}
