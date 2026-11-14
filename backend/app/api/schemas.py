from typing import Literal, Optional

from pydantic import BaseModel, Field

PresetName = Literal["none", "detection", "permissions", "output", "full"]


class GuardConfigIn(BaseModel):
    input_detection: bool = False
    content_detection: bool = False
    spotlighting: bool = False
    permissions: bool = False
    approval: bool = False
    output_filter: bool = False
    max_privilege: int = Field(4, ge=1, le=4)
    detection_threshold: float = Field(0.5, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    preset: PresetName = "full"
    guard: Optional[GuardConfigIn] = None


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source: Literal["document", "email", "webpage"] = "document"
    content: str = Field(min_length=1, max_length=20000)


class DetectIn(BaseModel):
    text: str = Field(max_length=20000)
    scope: Literal["user", "untrusted"] = "untrusted"
    threshold: float = Field(0.5, ge=0.0, le=1.0)


class EvalRunIn(BaseModel):
    configs: Optional[list[PresetName]] = None
    use_configured_llm: bool = False
