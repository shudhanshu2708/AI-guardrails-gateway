const base = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${base}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (error) {
      detail = response.statusText;
    }
    throw new Error(detail);
  }
  return response.json();
}

const post = (path, body) => request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export const api = {
  health: () => request("/health"),
  presets: () => request("/presets"),
  chat: (payload) => post("/chat", payload),
  stats: () => request("/stats"),
  events: (params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString();
    return request(`/events${query ? `?${query}` : ""}`);
  },
  approvals: (status) => request(`/approvals${status ? `?status=${status}` : ""}`),
  approve: (id) => post(`/approvals/${id}/approve`),
  deny: (id) => post(`/approvals/${id}/deny`),
  createDocument: (doc) => post("/documents", doc),
  documents: () => request("/documents"),
  outbox: () => request("/outbox"),
  runEval: (configs) => post("/evals/run", configs ? { configs } : {}),
  evals: () => request("/evals"),
  evalReport: (id) => request(`/evals/${id}`),
};
