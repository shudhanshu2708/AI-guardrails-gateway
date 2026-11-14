import { useEffect, useState } from "react";
import { api } from "../api.js";
import Metric, { percent } from "../components/Metric.jsx";

export default function Overview({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p className="muted">Loading</p>;

  const decisions = stats.events.by_decision;
  const latest = stats.latest_eval;
  const baseline = latest && latest.configs.none;
  const full = latest && latest.configs.full;

  return (
    <div className="page">
      <h1>Gateway overview</h1>
      <p className="lede">Every tool call, detection and approval that passes through the gateway is recorded here.</p>
      <div className="metrics">
        <Metric label="Agent runs" value={stats.runs} />
        <Metric label="Blocked or denied" value={(decisions.block || 0) + (decisions.deny || 0)} tone="bad" />
        <Metric label="Content quarantined" value={decisions.quarantine || 0} tone="bad" />
        <Metric label="Awaiting approval" value={stats.pending_approvals} tone="hold" />
        <Metric label="Emails actually sent" value={stats.emails_sent} />
      </div>
      <section className="panel">
        <h2>Latest red-team evaluation</h2>
        {latest && baseline && full ? (
          <>
            <p className="muted">
              {latest.dataset.attacks} attack scenarios and {latest.dataset.benign} legitimate tasks, run against the {latest.llm} agent.
            </p>
            <div className="metrics">
              <Metric label="Attack success, no guardrails" value={percent(baseline.metrics.attack_success_rate)} tone="bad" />
              <Metric label="Attack success, full guardrails" value={percent(full.metrics.attack_success_rate)} tone="ok" />
              <Metric label="Legitimate tasks completed" value={percent(full.metrics.task_completion_rate)} />
              <Metric label="False positives" value={percent(full.metrics.false_positive_rate)} />
            </div>
          </>
        ) : (
          <p className="muted">
            No evaluation has been run yet.{" "}
            <button className="link" onClick={() => onNavigate("evaluation")}>Run one</button>
          </p>
        )}
      </section>
    </div>
  );
}
