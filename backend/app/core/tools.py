TOOL_SPECS = [
    {
        "name": "search_documents",
        "description": "Search internal documents and emails by keyword. Returns titles and ids.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "read_document",
        "description": "Read the full text of a document by id.",
        "parameters": {
            "type": "object",
            "properties": {"document_id": {"type": "integer"}},
            "required": ["document_id"],
        },
    },
    {
        "name": "lookup_customer",
        "description": "Look up customer records by name. Contains sensitive personal data.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "delete_document",
        "description": "Permanently delete a document by id.",
        "parameters": {
            "type": "object",
            "properties": {"document_id": {"type": "integer"}},
            "required": ["document_id"],
        },
    },
]

TOOL_NAMES = {spec["name"] for spec in TOOL_SPECS}


class ToolExecutor:
    def __init__(self, store, run_id):
        self.store = store
        self.run_id = run_id

    def execute(self, name, arguments):
        handler = getattr(self, f"_{name}", None) if name in TOOL_NAMES else None
        if handler is None:
            return f"Error: unknown tool '{name}'."
        try:
            return handler(**arguments)
        except (TypeError, ValueError, KeyError) as exc:
            return f"Error: invalid arguments for {name}: {exc}"

    def _search_documents(self, query):
        rows = self.store.search_documents(query)
        if not rows:
            return "No documents found."
        return "\n".join(f"- [{r['id']}] {r['title']} ({r['source']})" for r in rows)

    def _read_document(self, document_id):
        doc = self.store.get_document(int(document_id))
        if doc is None:
            return f"Error: document {document_id} not found."
        return f"Document {doc['id']} | {doc['title']} | source={doc['source']}\n{doc['content']}"

    def _lookup_customer(self, name):
        rows = self.store.find_customers(str(name))
        if not rows:
            return "No customer found."
        return "\n".join(
            f"Customer {r['id']}: {r['name']} | {r['email']} | {r['phone']} | SSN {r['ssn']} | {r['note']}" for r in rows
        )

    def _send_email(self, to, subject, body):
        if "@" not in str(to):
            return "Error: invalid recipient."
        self.store.add_email(self.run_id, str(to), str(subject), str(body))
        return f"Email sent to {to}."

    def _delete_document(self, document_id):
        if self.store.delete_document(int(document_id)):
            return f"Document {document_id} deleted."
        return f"Error: document {document_id} not found."

