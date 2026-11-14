from dataclasses import dataclass, field, fields
from enum import IntEnum


class Privilege(IntEnum):
    READ = 1
    SENSITIVE_READ = 2
    WRITE = 3
    EXTERNAL = 4


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Message:
    role: str
    content: str = ""
    tool_calls: list = field(default_factory=list)
    tool_call_id: str = None


@dataclass
class LLMResponse:
    text: str = ""
    tool_calls: list = field(default_factory=list)


LAYER_FLAGS = (
    "input_detection",
    "content_detection",
    "spotlighting",
    "permissions",
    "approval",
    "output_filter",
)


@dataclass(frozen=True)
class GuardConfig:
    input_detection: bool = False
    content_detection: bool = False
    spotlighting: bool = False
    permissions: bool = False
    approval: bool = False
    output_filter: bool = False
    max_privilege: int = int(Privilege.EXTERNAL)
    detection_threshold: float = 0.5

    @classmethod
    def from_dict(cls, data):
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in names})

    def to_dict(self):
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def layers_enabled(self):
        return [name for name in LAYER_FLAGS if getattr(self, name)]


PRESETS = {
    "none": GuardConfig(),
    "detection": GuardConfig(input_detection=True, content_detection=True, spotlighting=True),
    "permissions": GuardConfig(permissions=True, approval=True),
    "output": GuardConfig(output_filter=True),
    "full": GuardConfig(
        input_detection=True,
        content_detection=True,
        spotlighting=True,
        permissions=True,
        approval=True,
        output_filter=True,
    ),
}


@dataclass
class Step:
    tool: str
    arguments: dict
    decision: str
    reason: str = ""
    result_preview: str = ""
    quarantined: bool = False

    def to_dict(self):
        return {
            "tool": self.tool,
            "arguments": self.arguments,
            "decision": self.decision,
            "reason": self.reason,
            "result_preview": self.result_preview,
            "quarantined": self.quarantined,
        }


@dataclass
class RunResult:
    run_id: str
    message: str
    guard: dict
    status: str = "completed"
    response: str = ""
    steps: list = field(default_factory=list)
    events: list = field(default_factory=list)
    interventions: int = 0
    approvals_queued: int = 0
    fired_layers: list = field(default_factory=list)

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "message": self.message,
            "guard": self.guard,
            "status": self.status,
            "response": self.response,
            "steps": [s.to_dict() for s in self.steps],
            "events": self.events,
            "interventions": self.interventions,
            "approvals_queued": self.approvals_queued,
            "fired_layers": self.fired_layers,
        }
