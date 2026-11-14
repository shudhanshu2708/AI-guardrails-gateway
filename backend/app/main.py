from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .core.llm import build_llm
from .storage.seed import seed
from .storage.sql import Base, SqlStore, make_engine, make_session_factory


def create_app(settings=None, store=None, llm=None):
    settings = settings or get_settings()
    if store is None:
        engine = make_engine(settings.database_url)
        Base.metadata.create_all(engine)
        store = SqlStore(make_session_factory(engine))
    if settings.seed_on_start:
        seed(store)

    app = FastAPI(title="AI Guardrails Gateway", version="1.0.0")
    app.state.settings = settings
    app.state.store = store
    app.state.llm = llm or build_llm(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app
