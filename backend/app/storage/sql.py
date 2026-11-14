from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from .base import Store, search_terms


def utcnow():
    return datetime.now(timezone.utc)


def iso(value):
    return value.isoformat() if value else None


class Base(DeclarativeBase):
    pass


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(40))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CustomerRow(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(50))
    ssn: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")


class EmailRow(Base):
    __tablename__ = "outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    to: Mapped[str] = mapped_column(String(300))
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EventRow(Base):
    __tablename__ = "security_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    layer: Mapped[str] = mapped_column(String(40), index=True)
    decision: Mapped[str] = mapped_column(String(40), index=True)
    tool: Mapped[str] = mapped_column(String(60), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ApprovalRow(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    tool: Mapped[str] = mapped_column(String(60))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), index=True, default="pending")
    result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class RunRow(Base):
    __tablename__ = "agent_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EvalRow(Base):
    __tablename__ = "eval_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    report: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


def make_engine(url):
    if url.startswith("sqlite"):
        options = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            options["poolclass"] = StaticPool
        return create_engine(url, **options)
    return create_engine(url, pool_pre_ping=True)


def make_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)


def _document(row):
    return {"id": row.id, "title": row.title, "source": row.source, "content": row.content, "created_at": iso(row.created_at)}


def _customer(row):
    return {"id": row.id, "name": row.name, "email": row.email, "phone": row.phone, "ssn": row.ssn, "note": row.note}


def _email(row):
    return {"id": row.id, "run_id": row.run_id, "to": row.to, "subject": row.subject, "body": row.body, "created_at": iso(row.created_at)}


def _event(row):
    return {
        "id": row.id,
        "run_id": row.run_id,
        "layer": row.layer,
        "decision": row.decision,
        "tool": row.tool,
        "score": row.score,
        "detail": row.detail or {},
        "created_at": iso(row.created_at),
    }


def _approval(row):
    return {
        "id": row.id,
        "run_id": row.run_id,
        "tool": row.tool,
        "arguments": row.arguments or {},
        "reason": row.reason,
        "status": row.status,
        "result": row.result,
        "created_at": iso(row.created_at),
        "resolved_at": iso(row.resolved_at),
    }


def _run(row):
    return {**row.payload, "created_at": iso(row.created_at)}


class SqlStore(Store):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def add_document(self, title, source, content):
        with self.session_factory.begin() as s:
            row = DocumentRow(title=title, source=source, content=content)
            s.add(row)
            s.flush()
            return _document(row)

    def get_document(self, document_id):
        with self.session_factory() as s:
            row = s.get(DocumentRow, int(document_id))
            return _document(row) if row else None

    def list_documents(self):
        with self.session_factory() as s:
            return [_document(r) for r in s.scalars(select(DocumentRow).order_by(DocumentRow.id))]

    def search_documents(self, query):
        terms = search_terms(query)
        if not terms:
            return []
        clauses = [
            or_(
                func.lower(DocumentRow.title).contains(t, autoescape=True),
                func.lower(DocumentRow.content).contains(t, autoescape=True),
            )
            for t in terms
        ]
        with self.session_factory() as s:
            return [_document(r) for r in s.scalars(select(DocumentRow).where(or_(*clauses)).order_by(DocumentRow.id))]

    def delete_document(self, document_id):
        with self.session_factory.begin() as s:
            row = s.get(DocumentRow, int(document_id))
            if row is None:
                return False
            s.delete(row)
            return True

    def add_customer(self, name, email, phone, ssn, note=""):
        with self.session_factory.begin() as s:
            row = CustomerRow(name=name, email=email, phone=phone, ssn=ssn, note=note)
            s.add(row)
            s.flush()
            return _customer(row)

    def find_customers(self, name):
        needle = (name or "").strip()
        with self.session_factory() as s:
            query = select(CustomerRow).order_by(CustomerRow.id)
            if needle.lower() not in ("*", "all", ""):
                query = query.where(func.lower(CustomerRow.name).contains(needle.lower(), autoescape=True))
            return [_customer(r) for r in s.scalars(query)]

    def add_email(self, run_id, to, subject, body):
        with self.session_factory.begin() as s:
            row = EmailRow(run_id=run_id, to=to, subject=subject, body=body)
            s.add(row)
            s.flush()
            return _email(row)

    def list_emails(self):
        with self.session_factory() as s:
            return [_email(r) for r in s.scalars(select(EmailRow).order_by(EmailRow.id.desc()))]

    def add_event(self, run_id, layer, decision, tool=None, score=None, detail=None):
        with self.session_factory.begin() as s:
            row = EventRow(run_id=run_id, layer=layer, decision=decision, tool=tool, score=score, detail=detail or {})
            s.add(row)
            s.flush()
            return _event(row)

    def list_events(self, layer=None, decision=None, run_id=None, limit=100):
        query = select(EventRow).order_by(EventRow.id.desc()).limit(limit)
        if layer:
            query = query.where(EventRow.layer == layer)
        if decision:
            query = query.where(EventRow.decision == decision)
        if run_id:
            query = query.where(EventRow.run_id == run_id)
        with self.session_factory() as s:
            return [_event(r) for r in s.scalars(query)]

    def event_counts(self):
        with self.session_factory() as s:
            by_decision = dict(s.execute(select(EventRow.decision, func.count()).group_by(EventRow.decision)).all())
            by_layer = dict(s.execute(select(EventRow.layer, func.count()).group_by(EventRow.layer)).all())
        return {"total": sum(by_decision.values()), "by_decision": by_decision, "by_layer": by_layer}

    def add_approval(self, run_id, tool, arguments, reason):
        with self.session_factory.begin() as s:
            row = ApprovalRow(run_id=run_id, tool=tool, arguments=arguments, reason=reason, status="pending", result="")
            s.add(row)
            s.flush()
            return _approval(row)

    def get_approval(self, approval_id):
        with self.session_factory() as s:
            row = s.get(ApprovalRow, int(approval_id))
            return _approval(row) if row else None

    def list_approvals(self, status=None):
        query = select(ApprovalRow).order_by(ApprovalRow.id.desc())
        if status:
            query = query.where(ApprovalRow.status == status)
        with self.session_factory() as s:
            return [_approval(r) for r in s.scalars(query)]

    def update_approval(self, approval_id, status, result=""):
        with self.session_factory.begin() as s:
            row = s.get(ApprovalRow, int(approval_id))
            if row is None:
                return None
            row.status = status
            row.result = result
            row.resolved_at = utcnow()
            s.flush()
            return _approval(row)

    def save_run(self, run):
        with self.session_factory.begin() as s:
            s.merge(RunRow(run_id=run["run_id"], status=run["status"], payload=run))

    def get_run(self, run_id):
        with self.session_factory() as s:
            row = s.get(RunRow, run_id)
            return _run(row) if row else None

    def list_runs(self, limit=50):
        with self.session_factory() as s:
            return [_run(r) for r in s.scalars(select(RunRow).order_by(RunRow.created_at.desc()).limit(limit))]

    def save_eval(self, report):
        with self.session_factory.begin() as s:
            row = EvalRow(report=report)
            s.add(row)
            s.flush()
            return {**report, "id": row.id}

    def get_eval(self, eval_id):
        with self.session_factory() as s:
            row = s.get(EvalRow, int(eval_id))
            return {**row.report, "id": row.id} if row else None

    def list_evals(self, limit=20):
        with self.session_factory() as s:
            return [{**r.report, "id": r.id} for r in s.scalars(select(EvalRow).order_by(EvalRow.id.desc()).limit(limit))]
