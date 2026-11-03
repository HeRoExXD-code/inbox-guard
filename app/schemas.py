"""Schemas for everything that crosses a boundary: model replies and tool arguments."""
import json
import re
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- what the model is allowed to reply with ---------------------------------
class ToolCall(_Strict):
    action: Literal["tool"]
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class FinalAnswer(_Strict):
    action: Literal["final"]
    answer: str = Field(min_length=1, max_length=4000)


AgentAction = Annotated[Union[ToolCall, FinalAnswer], Field(discriminator="action")]
_action_adapter = TypeAdapter(AgentAction)


# ---- tool arguments ----------------------------------------------------------
class NoArgs(_Strict):
    pass


class EmailIdArgs(_Strict):
    email_id: str = Field(pattern=r"^e\d{1,4}$")


class SearchArgs(_Strict):
    query: str = Field(min_length=1, max_length=100)


class SendEmailArgs(_Strict):
    to: str = Field(pattern=EMAIL_PATTERN)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=4000)


class CreateEventArgs(_Strict):
    title: str = Field(min_length=1, max_length=200)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(pattern=r"^\d{2}:\d{2}$")


# ---- parsing -----------------------------------------------------------------
def short_error(err: ValidationError) -> str:
    parts = []
    for e in err.errors()[:3]:
        loc = ".".join(str(x) for x in e["loc"]) or "root"
        parts.append(f"{loc}: {e['msg']}")
    return "; ".join(parts)


def extract_json_object(text: str) -> str | None:
    """Return the first balanced {...} in text (tolerates code fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", text)
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        start = text.find("{", start + 1)
    return None


def _normalize(data: object, tool_names: frozenset[str]) -> object:
    """Repair the format slips a small model makes. This never widens what can run:
    the tool name still has to be in the allow-list and the arguments still pass their schema.

      {"action": "search_emails", "args": {...}}  ->  {"action": "tool", "tool": "search_emails", ...}
      {"tool": "read_email", "args": {...}}       ->  action = "tool"
      {"answer": "..."}                           ->  action = "final"
      "arguments" / "parameters" / "input"        ->  "args"
    """
    if not isinstance(data, dict):
        return data
    d = dict(data)
    for alias in ("arguments", "parameters", "input"):
        if alias in d and "args" not in d:
            d["args"] = d.pop(alias)
    action = d.get("action")
    if isinstance(action, str) and action in tool_names and "tool" not in d:
        d["tool"], d["action"] = action, "tool"
    elif "action" not in d and "tool" in d:
        d["action"] = "tool"
    elif "action" not in d and "answer" in d:
        d["action"] = "final"
    return d


def parse_action(text: str, tool_names: frozenset[str] = frozenset()) -> ToolCall | FinalAnswer:
    """Parse and validate a model reply. Raises ValueError with a short, repairable message."""
    blob = extract_json_object(text)
    if blob is None:
        raise ValueError("no JSON object found")
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from None
    try:
        return _action_adapter.validate_python(_normalize(data, tool_names))
    except ValidationError as exc:
        raise ValueError(short_error(exc)) from None
