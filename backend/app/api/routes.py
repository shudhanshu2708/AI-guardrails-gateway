from fastapi import APIRouter, HTTPException, Query, Request

from ..core.agent import Agent, resolve_approval
from ..core.detector import detect
from ..core.domain import PRESETS, GuardConfig
from ..core.llm import NaiveLLM
from ..evals.dataset import DATASET
from ..evals.runner import DEFAULT_CONFIGS, run_evaluation
from .schemas import ChatRequest, DetectIn, DocumentIn, EvalRunIn

router = APIRouter(prefix="/api")


def _store(request):
    return request.app.state.store


def _summary(report):
    return {
        "id": report["id"],
        "created_at": report["created_at"],
        "llm": report["llm"],
        "dataset": report["dataset"],
        "configs": {name: {"layers": c["layers"], "metrics": c["metrics"]} for name, c in report["configs"].items()},
    }


@router.get("/health")
def health(request: Request):
    return {"status": "ok", "llm_provider": request.app.state.settings.llm_provider}


@router.get("/presets")
def presets():
    return {name: cfg.to_dict() for name, cfg in PRESETS.items()}


@router.post("/chat")
def chat(body: ChatRequest, request: Request):
    guard = GuardConfig.from_dict(body.guard.model_dump()) if body.guard else PRESETS[body.preset]
    agent = Agent(_store(request), request.app.state.llm, request.app.state.settings)
    return agent.run(body.message, guard).to_dict()


@router.get("/runs")
def list_runs(request: Request, limit: int = Query(50, ge=1, le=200)):
    return _store(request).list_runs(limit)


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request):
    run = _store(request).get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.get("/events")
def list_events(
    request: Request,
    layer: str = None,
    decision: str = None,
    run_id: str = None,
    limit: int = Query(100, ge=1, le=500),
):
    return _store(request).list_events(layer=layer, decision=decision, run_id=run_id, limit=limit)


@router.get("/stats")
def stats(request: Request):
    store = _store(request)
    latest = store.list_evals(1)
    return {
        "events": store.event_counts(),
        "pending_approvals": len(store.list_approvals("pending")),
        "runs": len(store.list_runs(200)),
        "emails_sent": len(store.list_emails()),
        "latest_eval": _summary(latest[0]) if latest else None,
    }


@router.get("/approvals")
def list_approvals(request: Request, status: str = None):
    return _store(request).list_approvals(status)


def _resolve(request, approval_id, approve):
    approval, outcome = resolve_approval(_store(request), approval_id, approve)
    if outcome == "not_found":
        raise HTTPException(404, "Approval not found")
    if outcome == "already_resolved":
        raise HTTPException(409, f"Approval already {approval['status']}")
    return approval


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: int, request: Request):
    return _resolve(request, approval_id, True)


@router.post("/approvals/{approval_id}/deny")
def deny(approval_id: int, request: Request):
    return _resolve(request, approval_id, False)


@router.get("/documents")
def list_documents(request: Request):
    return _store(request).list_documents()


@router.post("/documents", status_code=201)
def create_document(body: DocumentIn, request: Request):
    return _store(request).add_document(body.title, body.source, body.content)


@router.get("/documents/{document_id}")
def get_document(document_id: int, request: Request):
    doc = _store(request).get_document(document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/outbox")
def outbox(request: Request):
    return _store(request).list_emails()


@router.post("/detect")
def detect_text(body: DetectIn):
    return detect(body.text, body.scope, body.threshold).to_dict()


@router.get("/evals/dataset")
def eval_dataset():
    return [
        {"id": c.id, "kind": c.kind, "category": c.category, "message": c.message, "documents": [d[2] for d in c.documents]}
        for c in DATASET
    ]


@router.post("/evals/run")
def run_evals(body: EvalRunIn, request: Request):
    llm = request.app.state.llm if body.use_configured_llm else NaiveLLM()
    report = run_evaluation(llm, request.app.state.settings, configs=body.configs or DEFAULT_CONFIGS)
    return _store(request).save_eval(report)


@router.get("/evals")
def list_evals(request: Request):
    return [_summary(r) for r in _store(request).list_evals()]


@router.get("/evals/{eval_id}")
def get_eval(eval_id: int, request: Request):
    report = _store(request).get_eval(eval_id)
    if report is None:
        raise HTTPException(404, "Evaluation not found")
    return report
