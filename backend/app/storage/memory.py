import copy
import threading
from datetime import datetime, timezone

from .base import Store, search_terms


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class MemoryStore(Store):
    def __init__(self):
        self._lock = threading.RLock()
        self._documents = {}
        self._customers = []
        self._emails = []
        self._events = []
        self._approvals = {}
        self._runs = {}
        self._evals = {}
        self._ids = {"document": 0, "customer": 0, "email": 0, "event": 0, "approval": 0, "eval": 0}

    def _next(self, kind):
        self._ids[kind] += 1
        return self._ids[kind]

    def add_document(self, title, source, content):
        with self._lock:
            doc = {"id": self._next("document"), "title": title, "source": source, "content": content, "created_at": utcnow()}
            self._documents[doc["id"]] = doc
            return dict(doc)

    def get_document(self, document_id):
        with self._lock:
            doc = self._documents.get(int(document_id))
            return dict(doc) if doc else None

    def list_documents(self):
        with self._lock:
            return [dict(d) for d in sorted(self._documents.values(), key=lambda d: d["id"])]

    def search_documents(self, query):
        terms = search_terms(query)
        if not terms:
            return []
        with self._lock:
            return [
                dict(d)
                for d in sorted(self._documents.values(), key=lambda d: d["id"])
                if any(t in d["title"].lower() or t in d["content"].lower() for t in terms)
            ]

    def delete_document(self, document_id):
        with self._lock:
            return self._documents.pop(int(document_id), None) is not None

    def add_customer(self, name, email, phone, ssn, note=""):
        with self._lock:
            row = {"id": self._next("customer"), "name": name, "email": email, "phone": phone, "ssn": ssn, "note": note}
            self._customers.append(row)
            return dict(row)

    def find_customers(self, name):
        needle = (name or "").strip().lower()
        with self._lock:
            if needle in ("*", "all", ""):
                return [dict(c) for c in self._customers]
            return [dict(c) for c in self._customers if needle in c["name"].lower()]

    def add_email(self, run_id, to, subject, body):
        with self._lock:
            row = {"id": self._next("email"), "run_id": run_id, "to": to, "subject": subject, "body": body, "created_at": utcnow()}
            self._emails.append(row)
            return dict(row)

    def list_emails(self):
        with self._lock:
            return [dict(e) for e in self._emails]

    def add_event(self, run_id, layer, decision, tool=None, score=None, detail=None):
        with self._lock:
            row = {
                "id": self._next("event"),
                "run_id": run_id,
                "layer": layer,
                "decision": decision,
                "tool": tool,
                "score": score,
                "detail": copy.deepcopy(detail or {}),
                "created_at": utcnow(),
            }
            self._events.append(row)
            return copy.deepcopy(row)

    def list_events(self, layer=None, decision=None, run_id=None, limit=100):
        with self._lock:
            rows = [
                e
                for e in reversed(self._events)
                if (layer is None or e["layer"] == layer)
                and (decision is None or e["decision"] == decision)
                and (run_id is None or e["run_id"] == run_id)
            ]
            return [copy.deepcopy(e) for e in rows[:limit]]

    def event_counts(self):
        with self._lock:
            by_decision, by_layer = {}, {}
            for e in self._events:
                by_decision[e["decision"]] = by_decision.get(e["decision"], 0) + 1
                by_layer[e["layer"]] = by_layer.get(e["layer"], 0) + 1
            return {"total": len(self._events), "by_decision": by_decision, "by_layer": by_layer}

    def add_approval(self, run_id, tool, arguments, reason):
        with self._lock:
            row = {
                "id": self._next("approval"),
                "run_id": run_id,
                "tool": tool,
                "arguments": copy.deepcopy(arguments),
                "reason": reason,
                "status": "pending",
                "result": "",
                "created_at": utcnow(),
                "resolved_at": None,
            }
            self._approvals[row["id"]] = row
            return copy.deepcopy(row)

    def get_approval(self, approval_id):
        with self._lock:
            row = self._approvals.get(int(approval_id))
            return copy.deepcopy(row) if row else None

    def list_approvals(self, status=None):
        with self._lock:
            rows = [a for a in sorted(self._approvals.values(), key=lambda a: -a["id"]) if status is None or a["status"] == status]
            return [copy.deepcopy(a) for a in rows]

    def update_approval(self, approval_id, status, result=""):
        with self._lock:
            row = self._approvals.get(int(approval_id))
            if row is None:
                return None
            row["status"] = status
            row["result"] = result
            row["resolved_at"] = utcnow()
            return copy.deepcopy(row)

    def save_run(self, run):
        with self._lock:
            self._runs[run["run_id"]] = {**copy.deepcopy(run), "created_at": utcnow()}

    def get_run(self, run_id):
        with self._lock:
            row = self._runs.get(run_id)
            return copy.deepcopy(row) if row else None

    def list_runs(self, limit=50):
        with self._lock:
            rows = sorted(self._runs.values(), key=lambda r: r["created_at"], reverse=True)
            return [copy.deepcopy(r) for r in rows[:limit]]

    def save_eval(self, report):
        with self._lock:
            eval_id = self._next("eval")
            row = {**copy.deepcopy(report), "id": eval_id}
            self._evals[eval_id] = row
            return copy.deepcopy(row)

    def get_eval(self, eval_id):
        with self._lock:
            row = self._evals.get(int(eval_id))
            return copy.deepcopy(row) if row else None

    def list_evals(self, limit=20):
        with self._lock:
            rows = sorted(self._evals.values(), key=lambda r: -r["id"])
            return [copy.deepcopy(r) for r in rows[:limit]]
