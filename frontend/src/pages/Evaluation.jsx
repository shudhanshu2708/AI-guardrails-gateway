import { useEffect, useState } from "react";
import { api } from "../api.js";
import { percent } from "../components/Metric.jsx";
import Stamp from "../components/Stamp.jsx";

const LABELS = {
  none: "No guardrails",
  detection: "Detection only",
  permissions: "Permissions and approval only",
  output: "Output filter only",
  full: "All layers",
};

function Bar({ value, tone }) {
  return (
    <div className="bar">
      <div className={`bar-fill bar-${tone}`} style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  );
}

export default function Evaluation() {
  const [report, setReport] = useState(null);
  const [selected, setSelected] = useState("full");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .evals()
      .then((list) => (list.length ? api.evalReport(list[0].id) : null))
      .then(setReport)
      .catch((e) => setError(e.message));
  }, []);

  const run = async () => {
    setBusy(true);
    setError("");
    try {
      setReport(await api.runEval());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const config = report && report.configs[selected];

  return (
    <div className="page">
      <h1>Red-team evaluation</h1>
      <p className="lede">
        A fixed set of direct and indirect injection attacks and legitimate tasks, replayed against each guardrail configuration on an isolated database.
      </p>
      {error ? <p className="error">{error}</p> : null}
      <button className="btn" onClick={run} disabled={busy}>{busy ? "Running" : "Run evaluation"}</button>

      {report ? (
        <>
          <p className="muted">
            {report.dataset.attacks} attacks, {report.dataset.benign} legitimate tasks, agent: {report.llm}.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Configuration</th>
                  <th>Attack success</th>
                  <th>Missed</th>
                  <th>False positives</th>
                  <th>Task completion</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.configs).map(([name, c]) => (
                  <tr key={name} className={name === selected ? "clickable selected" : "clickable"} onClick={() => setSelected(name)}>
                    <td>{LABELS[name] || name}</td>
                    <td>
                      {percent(c.metrics.attack_success_rate)}
                      <Bar value={c.metrics.attack_success_rate} tone="bad" />
                    </td>
                    <td>{percent(c.metrics.false_negative_rate)}</td>
                    <td>{percent(c.metrics.false_positive_rate)}</td>
                    <td>
                      {percent(c.metrics.task_completion_rate)}
                      <Bar value={c.metrics.task_completion_rate} tone="ok" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            Missed means an attack where no layer intervened. False positives are legitimate tasks where a guardrail blocked, denied or redacted something.
          </p>

          {config ? (
            <section className="panel">
              <h2>Cases: {LABELS[selected] || selected}</h2>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Case</th><th>Category</th><th>Outcome</th><th>Layers that fired</th></tr>
                  </thead>
                  <tbody>
                    {config.results.map((r) => (
                      <tr key={r.case_id}>
                        <td>{r.case_id}</td>
                        <td>{r.category}</td>
                        <td>
                          <Stamp value={r.kind === "attack" ? (r.attack_succeeded ? "attack_succeeded" : "attack_stopped") : r.task_completed ? "task_done" : "task_failed"} />
                        </td>
                        <td>{r.fired_layers.join(", ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </>
      ) : (
        <p className="muted">No report yet.</p>
      )}
    </div>
  );
}
