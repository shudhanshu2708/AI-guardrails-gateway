from app.core import leakage
from app.core.domain import Privilege
from app.core.policy import PolicyContext, evaluate, is_grounded


def ctx(**overrides):
    base = dict(
        user_message="Summarize document 3.",
        max_privilege=int(Privilege.EXTERNAL),
        tainted=False,
        allowed_domains=("company.example",),
        permissions=True,
        approval=True,
    )
    base.update(overrides)
    return PolicyContext(**base)


def test_redacts_keys_canaries_and_cards():
    text = "key sk-live-abcdefghijklmnop1234 ref CANARY-0123456789 card 4111 1111 1111 1111 plain 1234 5678"
    redacted, leaks = leakage.redact(text)
    assert "sk-live" not in redacted and "CANARY-" not in redacted and "4111" not in redacted
    assert {l.kind for l in leaks} == {"api_key", "canary", "credit_card"}


def test_luhn_rejects_random_numbers():
    assert not leakage.scan("order 1234 5678 9012 3456")


def test_known_secret_and_skip_kinds():
    assert leakage.scan("value hunter2-secret", secrets=["hunter2-secret"])
    assert not leakage.scan("ssn 900-12-3456", skip_kinds=("ssn",))
    assert leakage.scan("ssn 900-12-3456")


def test_read_tools_are_allowed():
    assert evaluate("read_document", {"document_id": 3}, ctx(tainted=True)).action == "allow"


def test_ungrounded_sensitive_action_denied_after_untrusted_read():
    decision = evaluate("lookup_customer", {"name": "*"}, ctx(tainted=True))
    assert decision.action == "deny" and decision.rule == "ungrounded_action"


def test_grounded_action_is_not_denied():
    context = ctx(user_message="Look up customer Alice.", tainted=True)
    assert evaluate("lookup_customer", {"name": "Alice"}, context).action == "allow"


def test_external_and_write_require_approval():
    context = ctx(user_message="Email bob@company.example", tainted=True)
    assert evaluate("send_email", {"to": "bob@company.example"}, context).action == "require_approval"
    assert evaluate("delete_document", {"document_id": 2}, ctx(user_message="Delete document 2")).action == "require_approval"


def test_privilege_cap_denies():
    decision = evaluate("send_email", {"to": "bob@company.example"}, ctx(max_privilege=int(Privilege.READ)))
    assert decision.action == "deny" and decision.rule == "privilege_cap"


def test_unknown_tool_denied():
    assert evaluate("format_disk", {}, ctx()).action == "deny"


def test_grounding_matches_whole_tokens():
    assert is_grounded("delete_document", {"document_id": 2}, "Delete document 2 please")
    assert not is_grounded("delete_document", {"document_id": 2}, "Delete document 25 please")
    assert not is_grounded("send_email", {"to": "a@evil.example"}, "send to ba@evil.example")
