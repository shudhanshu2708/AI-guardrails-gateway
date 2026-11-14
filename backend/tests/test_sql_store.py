import pytest

pytest.importorskip("sqlalchemy")

from app.storage.memory import MemoryStore
from app.storage.seed import seed
from app.storage.sql import Base, SqlStore, make_engine, make_session_factory


def sql_store():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlStore(make_session_factory(engine))


def test_sql_store_matches_memory_store_behaviour():
    stores = [MemoryStore(), sql_store()]
    for store in stores:
        assert seed(store) is True and seed(store) is False
        assert [d["id"] for d in store.search_documents("incident postmortem")] == [5]
        assert len(store.find_customers("*")) == 3
        assert store.find_customers("alice")[0]["name"] == "Alice Johnson"
        assert store.delete_document(1) and not store.delete_document(1)
        event = store.add_event("run1", "input_detection", "block", score=0.9, detail={"k": 1})
        assert store.list_events(layer="input_detection")[0]["id"] == event["id"]
        assert store.event_counts()["by_decision"] == {"block": 1}
        approval = store.add_approval("run1", "send_email", {"to": "a@b.c"}, "reason")
        assert store.update_approval(approval["id"], "approved", "ok")["status"] == "approved"
        assert store.list_approvals("pending") == []
        store.save_run({"run_id": "run1", "status": "completed", "response": "hi"})
        assert store.get_run("run1")["response"] == "hi"
        saved = store.save_eval({"created_at": "now", "configs": {}})
        assert store.get_eval(saved["id"])["id"] == saved["id"]
