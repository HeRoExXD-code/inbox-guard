"""Tool registry = the allow-list. Only tools named here can ever run."""
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from .environment import InboxEnv
from .schemas import CreateEventArgs, EmailIdArgs, NoArgs, SearchArgs, SendEmailArgs, short_error


@dataclass(frozen=True)
class ToolSpec:
    name: str
    args_model: type[BaseModel]
    signature: str
    description: str
    untrusted_output: bool  # output contains third-party text (emails)
    side_effect: bool       # changes the world


TOOLS: dict[str, ToolSpec] = {t.name: t for t in [
    ToolSpec("list_emails", NoArgs, "list_emails()",
             "List all emails (id, date, sender, subject).", True, False),
    ToolSpec("read_email", EmailIdArgs, 'read_email(email_id)  e.g. {"email_id": "e1"}',
             "Read one email in full.", True, False),
    ToolSpec("search_emails", SearchArgs, "search_emails(query)",
             "Search sender, subject and body; returns the 5 best matches, best first.", True, False),
    ToolSpec("get_contacts", NoArgs, "get_contacts()",
             "List the user's saved contacts.", False, False),
    ToolSpec("send_email", SendEmailArgs, "send_email(to, subject, body)",
             "Send an email from the user's account.", False, True),
    ToolSpec("create_event", CreateEventArgs, 'create_event(title, date "YYYY-MM-DD", time "HH:MM")',
             "Add an event to the user's calendar.", False, True),
    ToolSpec("delete_email", EmailIdArgs, "delete_email(email_id)",
             "Permanently delete an email.", False, True),
]}


def describe_tools() -> str:
    return "\n".join(f"- {t.signature}: {t.description}" for t in TOOLS.values())


def validate_args(name: str, args: dict) -> BaseModel:
    """Allow-list + schema check. Raises ValueError with a message the model can act on."""
    spec = TOOLS.get(name)
    if spec is None:
        raise ValueError(f"unknown tool '{name}'. Allowed tools: {', '.join(TOOLS)}")
    try:
        return spec.args_model.model_validate(args)
    except ValidationError as exc:
        raise ValueError(f"bad arguments for {name}: {short_error(exc)}") from None


def execute(env: InboxEnv, name: str, args: BaseModel) -> str:
    assert name in TOOLS  # validate_args must run first
    return getattr(env, name)(**args.model_dump())
