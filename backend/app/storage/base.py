from abc import ABC, abstractmethod


class Store(ABC):
    @abstractmethod
    def add_document(self, title, source, content): ...

    @abstractmethod
    def get_document(self, document_id): ...

    @abstractmethod
    def list_documents(self): ...

    @abstractmethod
    def search_documents(self, query): ...

    @abstractmethod
    def delete_document(self, document_id): ...

    @abstractmethod
    def add_customer(self, name, email, phone, ssn, note=""): ...

    @abstractmethod
    def find_customers(self, name): ...

    @abstractmethod
    def add_email(self, run_id, to, subject, body): ...

    @abstractmethod
    def list_emails(self): ...

    @abstractmethod
    def add_event(self, run_id, layer, decision, tool=None, score=None, detail=None): ...

    @abstractmethod
    def list_events(self, layer=None, decision=None, run_id=None, limit=100): ...

    @abstractmethod
    def event_counts(self): ...

    @abstractmethod
    def add_approval(self, run_id, tool, arguments, reason): ...

    @abstractmethod
    def get_approval(self, approval_id): ...

    @abstractmethod
    def list_approvals(self, status=None): ...

    @abstractmethod
    def update_approval(self, approval_id, status, result=""): ...

    @abstractmethod
    def save_run(self, run): ...

    @abstractmethod
    def get_run(self, run_id): ...

    @abstractmethod
    def list_runs(self, limit=50): ...

    @abstractmethod
    def save_eval(self, report): ...

    @abstractmethod
    def get_eval(self, eval_id): ...

    @abstractmethod
    def list_evals(self, limit=20): ...


def search_terms(query):
    import re

    return [w for w in re.findall(r"\w+", (query or "").lower()) if len(w) >= 3]
