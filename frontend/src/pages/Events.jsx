import { Fragment, useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import Stamp from "../components/Stamp.jsx";

const LAYERS = ["", "input_detection", "content_detection", "permissions", "approval", "output_filter", "tool_call"];
const DECISIONS = ["", "allow", "block", "deny", "quarantine", "redact", "pending", "approved", "denied"];

export default function Events() {
  const [rows, setRows] = useState([]);
  const [layer, setLayer] = useState("");
  const [decision, setDecision] = useState("");
  const [open, setOpen] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.events({ layer, decision, limit: 200 }).then(setRows).catch((e) => setError(e.message));
  }, [layer, decision]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="page">
      <h1>Security log</h1>
      <p className="lede">Blocked attacks, allowed actions, tool calls and policy decisions.</p>
      {error ? <p className="error">{error}</p> : null}
      <div className="presets">
        <select value={layer} onChange={(e) => setLayer(e.target.value)} aria-label="Layer filter">
          {LAYERS.map((l) => <option key={l} value={l}>{l || "all layers"}</option>)}
        </select>
        <select value={decision} onChange={(e) => setDecision(e.target.value)} aria-label="Decision filter">
          {DECISIONS.map((d) => <option key={d} value={d}>{d || "all decisions"}</option>)}
        </select>
        <button className="btn secondary" onClick={load}>Refresh</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Time</th><th>Layer</th><th>Decision</th><th>Tool</th><th>Score</th><th>Run</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.id}>
                <tr onClick={() => setOpen(open === r.id ? null : r.id)} className="clickable">
                  <td>{new Date(r.created_at).toLocaleTimeString()}</td>
                  <td>{r.layer}</td>
                  <td><Stamp value={r.decision} /></td>
                  <td>{r.tool || ""}</td>
                  <td>{r.score != null ? r.score.toFixed(2) : ""}</td>
                  <td>{r.run_id.slice(0, 8)}</td>
                </tr>
                {open === r.id ? (
                  <tr>
                    <td colSpan={6}><pre className="payload">{JSON.stringify(r.detail, null, 2)}</pre></td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
        {rows.length === 0 ? <p className="muted pad">No events yet.</p> : null}
      </div>
    </div>
  );
}
