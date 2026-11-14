import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import Stamp from "../components/Stamp.jsx";

export default function Approvals() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.approvals(filter === "all" ? "" : filter).then(setItems).catch((e) => setError(e.message));
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const resolve = async (id, approve) => {
    setError("");
    try {
      await (approve ? api.approve(id) : api.deny(id));
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="page">
      <h1>Approvals</h1>
      <p className="lede">Write and external actions wait here until a person approves them.</p>
      {error ? <p className="error">{error}</p> : null}
      <div className="presets">
        {["pending", "approved", "denied", "all"].map((f) => (
          <button key={f} className={f === filter ? "btn" : "btn secondary"} onClick={() => setFilter(f)}>{f}</button>
        ))}
        <button className="btn secondary" onClick={load}>Refresh</button>
      </div>
      {items.length === 0 ? <p className="muted">Nothing here.</p> : null}
      {items.map((a) => (
        <section className="panel" key={a.id}>
          <div className="row">
            <h2>#{a.id} {a.tool}</h2>
            <Stamp value={a.status} />
          </div>
          <p className="muted">{a.reason}</p>
          <pre className="payload">{JSON.stringify(a.arguments, null, 2)}</pre>
          {a.result ? <p className="muted">Outcome: {a.result}</p> : null}
          {a.status === "pending" ? (
            <div className="presets">
              <button className="btn" onClick={() => resolve(a.id, true)}>Approve and execute</button>
              <button className="btn danger" onClick={() => resolve(a.id, false)}>Deny</button>
            </div>
          ) : null}
        </section>
      ))}
    </div>
  );
}
