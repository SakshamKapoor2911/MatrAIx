import json
import pytest
from persona_eval.openai_client import OpenAIChatClient, coerce_json


class _FakeMessage:
    def __init__(self, content): self.content = content
class _FakeChoice:
    def __init__(self, content): self.message = _FakeMessage(content)
class _FakeCompletion:
    def __init__(self, content): self.choices = [_FakeChoice(content)]
class _FakeCompletions:
    def __init__(self, content): self._c = content; self.last_kwargs = None
    def create(self, **kwargs): self.last_kwargs = kwargs; return _FakeCompletion(self._c)
class _FakeChat:
    def __init__(self, content): self.completions = _FakeCompletions(content)
class _FakeOpenAI:
    def __init__(self, content): self.chat = _FakeChat(content)


def test_coerce_json_plain_and_fenced():
    assert coerce_json('{"a": 1}') == {"a": 1}
    assert coerce_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_complete_json_parses_and_requests_json_mode():
    fake = _FakeOpenAI('{"message": "hi", "decision": "continue"}')
    client = OpenAIChatClient(model="gpt-4o-mini", client=fake)
    out = client.complete_json("sys", "user")
    assert out == {"message": "hi", "decision": "continue"}
    kw = fake.chat.completions.last_kwargs
    assert kw["model"] == "gpt-4o-mini"
    assert kw["response_format"] == {"type": "json_object"}
    assert kw["messages"][0]["role"] == "system" and kw["messages"][1]["role"] == "user"


def test_complete_json_raises_on_unparseable():
    client = OpenAIChatClient(model="gpt-4o-mini", client=_FakeOpenAI("not json at all"))
    with pytest.raises(ValueError):
        client.complete_json("s", "u")
