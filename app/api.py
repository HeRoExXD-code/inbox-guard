"""FastAPI backend + web UI.

uvicorn app.api:app --reload      then open http://127.0.0.1:8000  (API docs at /docs)
"""
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agent import run_agent, run_agent_iter
from .assess import assess
from .defenses import DEFENSES
from .environment import InboxEnv

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(title="InboxGuard", description="Prompt-injection-resistant email agent")


class ExtraEmail(BaseModel):
    mode: Literal["new_email", "append"] = Field(
        default="new_email", description="new_email: a new email from a stranger. append: hide body at the end of target")
    target: str | None = Field(default=None, pattern=r"^e\d{1,4}$", description="email id for mode=append, e.g. e6")
    sender: str = Field(default="someone@external.example", max_length=200)
    subject: str = Field(default="(no subject)", max_length=200)
    body: str = Field(max_length=4000)


class RunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    defense: Literal["none", "spotlight", "guard"] = "guard"
    extra_email: ExtraEmail | None = Field(
        default=None, description="Optional new email (e.g. an attack) added to the inbox for this run")


def _make_env(req: RunRequest) -> InboxEnv:
    env = InboxEnv.load()  # fresh inbox per request
    x = req.extra_email
    if x and x.mode == "append":
        try:
            env.inject({"mode": "append", "target": x.target or "e1", "text": x.body})
        except ValueError:
            raise HTTPException(status_code=422, detail=f"There is no email {x.target} in the inbox.") from None
    elif x:
        env.inject({"mode": "new_email", "from": x.sender, "subject": x.subject, "body": x.body})
    return env


def _world(env: InboxEnv, message: str, answer: str | None) -> dict:
    return {"outbox": env.outbox, "calendar": env.calendar, "deleted": env.deleted,
            "flags": assess(env, message, answer)}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/inbox")
def inbox() -> dict:
    env = InboxEnv.load()
    return {"emails": env.emails, "contacts": env.contacts}


@app.post("/run")
def run(req: RunRequest) -> dict:
    env = _make_env(req)
    try:
        trace = run_agent(req.message, env, DEFENSES[req.defense])
    except Exception as exc:  # e.g. proxy unreachable or key missing
        raise HTTPException(status_code=502, detail=f"The model could not be reached: {exc}") from None
    return {"answer": trace.answer, "stop_reason": trace.stop_reason, "steps": trace.steps,
            "blocked": trace.blocked, "events": trace.events, "world": _world(env, req.message, trace.answer)}


@app.post("/stream")
def stream(req: RunRequest) -> StreamingResponse:
    """Server-sent events: one `data:` line per agent event, then the final world state."""
    env = _make_env(req)

    def gen():
        answer = None
        try:
            for ev in run_agent_iter(req.message, env, DEFENSES[req.defense]):
                if ev["type"] == "final":
                    answer = ev["answer"]
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as exc:  # e.g. proxy unreachable
            yield f"data: {json.dumps({'type': 'error', 'error': f'The model could not be reached: {exc}'})}\n\n"
        yield f"data: {json.dumps({'type': 'world', **_world(env, req.message, answer)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
