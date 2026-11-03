"""A simulated inbox + calendar. Tools act on this object, never on real accounts."""
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import config, retrieval


@dataclass
class InboxEnv:
    user_email: str
    emails: list[dict]
    contacts: list[dict]
    secrets: list[str]
    outbox: list[dict] = field(default_factory=list)
    calendar: list[dict] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "InboxEnv":
        data = json.loads(Path(path or config.DATA_DIR / "inbox.json").read_text(encoding="utf-8"))
        return cls(
            user_email=data["user_email"],
            emails=copy.deepcopy(data["emails"]),
            contacts=copy.deepcopy(data["contacts"]),
            secrets=list(data["secrets"]),
        )

    # ---- setting up an attack ------------------------------------------------
    def inject(self, injection: dict) -> str:
        """Plant attacker text. mode=append adds it to an existing email, mode=new_email adds a new one."""
        mode = injection["mode"]
        if mode == "append":
            email = self._get(injection["target"])
            if email is None:
                raise ValueError(f"unknown target email {injection['target']}")
            email["body"] += "\n\n" + injection["text"]
            return email["id"]
        if mode == "new_email":
            n_new = sum(1 for e in self.emails if int(e["id"][1:]) >= 100)
            new_id = f"e{100 + n_new}"
            self.emails.append({
                "id": new_id,
                "from": injection["from"],
                "to": self.user_email,
                "date": injection.get("date", config.TODAY),
                "subject": injection["subject"],
                "body": injection["body"],
            })
            return new_id
        raise ValueError(f"unknown injection mode {mode}")

    def _get(self, email_id: str) -> dict | None:
        return next((e for e in self.emails if e["id"] == email_id), None)

    def contact_addresses(self) -> set[str]:
        return {c["email"].lower() for c in self.contacts}

    # ---- tools (called only through app.tools) -------------------------------
    def list_emails(self) -> str:
        if not self.emails:
            return "Inbox is empty."
        return "\n".join(
            f"[{e['id']}] {e['date']} | From: {e['from']} | Subject: {e['subject']}" for e in self.emails
        )

    def read_email(self, email_id: str) -> str:
        e = self._get(email_id)
        if e is None:
            return f"Error: no email with id {email_id}."
        return (
            f"ID: {e['id']}\nFrom: {e['from']}\nTo: {e['to']}\nDate: {e['date']}\n"
            f"Subject: {e['subject']}\n\n{e['body']}"
        )

    def search_emails(self, query: str) -> str:
        ids = retrieval.bm25_search(self.emails, query)
        if not ids:
            return f"No emails match '{query}'."
        by_id = {e["id"]: e for e in self.emails}
        return "\n".join(
            f"[{i}] {by_id[i]['date']} | From: {by_id[i]['from']} | Subject: {by_id[i]['subject']}" for i in ids
        )

    def get_contacts(self) -> str:
        return "\n".join(f"{c['name']} <{c['email']}>" for c in self.contacts)

    def send_email(self, to: str, subject: str, body: str) -> str:
        self.outbox.append({"to": to, "subject": subject, "body": body})
        return f"Email sent to {to}."

    def create_event(self, title: str, date: str, time: str) -> str:
        self.calendar.append({"title": title, "date": date, "time": time})
        return f"Event '{title}' created on {date} at {time}."

    def delete_email(self, email_id: str) -> str:
        e = self._get(email_id)
        if e is None:
            return f"Error: no email with id {email_id}."
        self.emails.remove(e)
        self.deleted.append(email_id)
        return f"Email {email_id} deleted."
