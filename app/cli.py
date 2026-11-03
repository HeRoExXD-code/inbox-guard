"""Command-line demo.

python -m app.cli "When is my project meeting?" --defense guard
python -m app.cli "When is my project meeting?" --defense none --case a01
python -m app.cli "Summarize my inbox" --inject-file my_attack.json
"""
import argparse
import json
import textwrap

from .agent import run_agent_iter
from .defenses import DEFENSES
from .environment import InboxEnv


def _clip(text: str, n: int = 600) -> str:
    return text if len(text) <= n else text[:n] + " …"


def print_event(ev: dict) -> None:
    kind = ev["type"]
    if kind == "tool_call":
        print(f"[{ev['step']}] -> {ev['tool']}({json.dumps(ev['args'], ensure_ascii=False)})")
    elif kind == "observation":
        print(textwrap.indent(_clip(ev["content"]), "      "))
    elif kind == "blocked":
        print(f"[{ev['step']}] BLOCKED {ev['tool']}: {ev['reason']}")
    elif kind == "tool_error":
        print(f"[{ev['step']}] tool error: {ev['error']}")
    elif kind == "parse_error":
        print(f"[{ev['step']}] invalid reply from model: {ev['error']}")
    elif kind == "final":
        print(f"\nANSWER:\n{ev['answer']}")
    elif kind == "stop":
        print(f"\n(stopped: {ev['reason']} after {ev['step']} step(s))")


def main() -> None:
    p = argparse.ArgumentParser(description="InboxGuard demo")
    p.add_argument("message", help="what you ask the assistant")
    p.add_argument("--defense", choices=list(DEFENSES), default="guard")
    p.add_argument("--case", help="plant the injection from an eval case, e.g. a01")
    p.add_argument("--inject-file", help='JSON file: {"mode": "new_email", "from": ..., "subject": ..., "body": ...}')
    args = p.parse_args()

    env = InboxEnv.load()
    if args.case:
        from evaluation.cases import load_cases
        case = {c["id"]: c for c in load_cases()}[args.case]
        if case.get("injection"):
            print(f"(planted injection from case {args.case}: {case['attack_type']})")
            env.inject(case["injection"])
    if args.inject_file:
        with open(args.inject_file, encoding="utf-8") as f:
            env.inject(json.load(f))

    print(f"defense = {args.defense}\n")
    for ev in run_agent_iter(args.message, env, DEFENSES[args.defense]):
        print_event(ev)
    print(f"\noutbox:   {json.dumps(env.outbox, ensure_ascii=False)}")
    print(f"calendar: {json.dumps(env.calendar, ensure_ascii=False)}")
    print(f"deleted:  {env.deleted}")


if __name__ == "__main__":
    main()
