import pytest

from app.schemas import FinalAnswer, ToolCall, parse_action
from app.tools import validate_args


def test_parses_tool_call_inside_code_fence_and_chatter():
    a = parse_action('Sure!\n```json\n{"action": "tool", "tool": "read_email", "args": {"email_id": "e1"}}\n```')
    assert isinstance(a, ToolCall) and a.args == {"email_id": "e1"}


def test_parses_final_answer_with_braces_in_string():
    a = parse_action('{"action": "final", "answer": "use {curly} braces"}')
    assert isinstance(a, FinalAnswer) and a.answer == "use {curly} braces"


@pytest.mark.parametrize("bad", ["no json here", '{"action": "dance"}', '{"action": "final"}',
                                 '{"action": "final", "answer": "x", "extra": 1}', '{"action": "tool",'])
def test_rejects_invalid_replies(bad):
    with pytest.raises(ValueError):
        parse_action(bad)


def test_tool_allow_list_and_argument_schemas():
    with pytest.raises(ValueError, match="unknown tool"):
        validate_args("run_shell", {"cmd": "rm -rf /"})
    with pytest.raises(ValueError):
        validate_args("send_email", {"to": "not-an-email", "subject": "x", "body": "y"})
    with pytest.raises(ValueError):
        validate_args("create_event", {"title": "x", "date": "8 Dec", "time": "09:00"})
    assert validate_args("read_email", {"email_id": "e3"}).email_id == "e3"


TOOL_NAMES = frozenset({"search_emails", "read_email", "send_email"})


def test_normalises_tool_name_used_as_action():
    a = parse_action('{"action": "search_emails", "args": {"query": "Mint"}}', TOOL_NAMES)
    assert isinstance(a, ToolCall) and a.tool == "search_emails" and a.args == {"query": "Mint"}


def test_normalises_other_common_slips():
    assert parse_action('{"tool": "read_email", "arguments": {"email_id": "e1"}}', TOOL_NAMES).args == {"email_id": "e1"}
    assert isinstance(parse_action('{"answer": "done"}', TOOL_NAMES), FinalAnswer)


def test_normalisation_does_not_let_unknown_tools_through():
    with pytest.raises(ValueError):
        parse_action('{"action": "run_shell", "args": {"cmd": "ls"}}', TOOL_NAMES)
    # without the tool list the old strict behaviour is unchanged
    with pytest.raises(ValueError):
        parse_action('{"action": "search_emails", "args": {"query": "x"}}')
