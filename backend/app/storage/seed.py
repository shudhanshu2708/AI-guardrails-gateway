SEED_DOCUMENTS = (
    (
        "Q3 Budget Summary",
        "document",
        "Q3 budget: Engineering $420k, Marketing $180k, Operations $95k. Headcount stays flat. The next budget review is on October 14.",
    ),
    (
        "Vacation Policy",
        "document",
        "Employees accrue 1.5 vacation days per month. Requests must be submitted two weeks in advance and approved by a manager.",
    ),
    (
        "Onboarding Checklist",
        "document",
        "Day one: laptop setup, accounts and security training. Week one: meet the team and review the engineering handbook.",
    ),
    (
        "Vendor Invoice March",
        "email",
        "Hello, attached is the March invoice for $12,400 from Northwind Supplies. Payment terms are net 30. Please confirm receipt.",
    ),
    (
        "Incident Postmortem 2026-02",
        "document",
        "On February 9 the API latency rose to 4 seconds for 40 minutes. Root cause: a missing database index. Fix: the index was added and alerting thresholds were lowered.",
    ),
)

SEED_CUSTOMERS = (
    ("Alice Johnson", "alice@client-a.example", "+1-555-0101", "900-12-3456", "Annual contract, renews in May."),
    ("Bob Martins", "bob@client-b.example", "+1-555-0102", "900-23-4567", "Prefers email contact."),
    ("Carla Diaz", "carla@client-c.example", "+1-555-0103", "900-34-5678", "Pilot customer, two open tickets."),
)


def seed(store):
    if store.list_documents():
        return False
    for title, source, content in SEED_DOCUMENTS:
        store.add_document(title, source, content)
    for name, email, phone, ssn, note in SEED_CUSTOMERS:
        store.add_customer(name, email, phone, ssn, note)
    return True
