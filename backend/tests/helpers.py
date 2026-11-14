from app.config import Settings
from app.core.agent import Agent
from app.core.domain import PRESETS
from app.core.llm import NaiveLLM
from app.storage.memory import MemoryStore
from app.storage.seed import seed

SETTINGS = Settings()


def make_store(documents=()):
    store = MemoryStore()
    seed(store)
    for doc in documents:
        store.add_document(*doc)
    return store


def run_agent(message, preset, documents=()):
    store = make_store(documents)
    result = Agent(store, NaiveLLM(), SETTINGS).run(message, PRESETS[preset])
    return result, store
