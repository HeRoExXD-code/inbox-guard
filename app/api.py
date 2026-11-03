"""FastAPI backend.  Run: uvicorn app.api:app --reload   (docs at /docs)"""
import json
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent import run_agent, run_agent_iter
from .defenses import DEFENSES
from .environment import InboxEnv

app = FastAPI(title="InboxGuard", description="Prompt-injection-resistant email agent")


class ExtraEmail(BaseModel):
    sender: str = Field(default="someone@external.example", max_length=200)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=4000)


class RunRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    defense: Literal["none", "spotlight", "guard"] = "guard"
    extra_email: ExtraEmail | None = Field(
        default=None, description="Optional new email (e.g. an attack) added to the inbox for this run")


def _make_env(req: RunRequest) -> InboxEnv:
    env = InboxEnv.load()  # fresh inbox per request
    if req.extra_email:
        env.inject({"mode": "new_email", "from": req.extra_email.sender,
                    "subject": req.extra_email.subject, "body": req.extra_email.body})
    return env


def _world(env: InboxEnv) -> dict:
    return {"outbox": env.outbox, "calendar": env.calendar, "deleted": env.deleted}


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
    trace = run_agent(req.message, env, DEFENSES[req.defense])
    return {"answer": trace.answer, "stop_reason": trace.stop_reason, "steps": trace.steps,
            "blocked": trace.blocked, "events": trace.events, "world": _world(env)}


@app.post("/stream")
def stream(req: RunRequest) -> StreamingResponse:
    """Server-sent events: one `data:` line per agent event, then the final world state."""
    env = _make_env(req)

    def gen():
        try:
            for ev in run_agent_iter(req.message, env, DEFENSES[req.defense]):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as exc:  # e.g. proxy unreachable
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        yield f"data: {json.dumps({'type': 'world', **_world(env)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
