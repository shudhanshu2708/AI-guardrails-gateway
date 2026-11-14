import { useEffect, useState } from "react";
import { api } from "./api.js";
import Playground from "./pages/Playground.jsx";
import Approvals from "./pages/Approvals.jsx";
import Events from "./pages/Events.jsx";
import Evaluation from "./pages/Evaluation.jsx";
import Overview from "./pages/Overview.jsx";

const PAGES = [
  { id: "overview", label: "Overview", component: Overview },
  { id: "playground", label: "Playground", component: Playground },
  { id: "approvals", label: "Approvals", component: Approvals },
  { id: "events", label: "Security log", component: Events },
  { id: "evaluation", label: "Red-team eval", component: Evaluation },
];

export default function App() {
  const [page, setPage] = useState("overview");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const Current = PAGES.find((p) => p.id === page).component;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>Guardrails Console</span>
        </div>
        <nav>
          {PAGES.map((p) => (
            <button key={p.id} className={p.id === page ? "nav active" : "nav"} onClick={() => setPage(p.id)}>
              {p.label}
            </button>
          ))}
        </nav>
        <div className="rail-foot">
          API: {health ? health.status : "checking"}
          {health && health.llm_provider ? <div>Agent model: {health.llm_provider}</div> : null}
        </div>
      </aside>
      <main className="main">
        <Current onNavigate={setPage} />
      </main>
    </div>
  );
}
