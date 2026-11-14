const TONES = {
  allowed: "ok",
  allow: "ok",
  approved: "ok",
  completed: "ok",
  denied: "bad",
  deny: "bad",
  block: "bad",
  blocked: "bad",
  quarantine: "bad",
  redact: "bad",
  pending: "hold",
  attack_succeeded: "bad",
  attack_stopped: "ok",
  task_done: "ok",
  task_failed: "bad",
};

const LABELS = {
  allowed: "Allowed",
  allow: "Allowed",
  approved: "Approved",
  completed: "Completed",
  denied: "Denied",
  deny: "Denied",
  block: "Blocked",
  blocked: "Blocked",
  quarantine: "Quarantined",
  redact: "Redacted",
  pending: "Held for approval",
  attack_succeeded: "Attack succeeded",
  attack_stopped: "Attack stopped",
  task_done: "Task completed",
  task_failed: "Task failed",
};

export default function Stamp({ value }) {
  const tone = TONES[value] || "neutral";
  return <span className={`stamp stamp-${tone}`}>{LABELS[value] || value}</span>;
}
