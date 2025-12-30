from __future__ import annotations

import logging
import sys
import types
from types import SimpleNamespace

import pytest

from pptx_generator.layout_ai.client import OpenAIChatLayoutClient, LayoutAIRequest
from pptx_generator.layout_ai.policy import LayoutAIPolicy
from pptx_generator.prepare_ai.client import OpenAIPrepareLLMClient, AzureOpenAIPrepareLLMClient
from pptx_generator.prepare_ai.client import PrepareLLMResult
from pptx_generator.slide_ai.client import OpenAIChatClient, AIGenerationRequest
from pptx_generator.slide_ai.policy import SlideAIPolicy
from pptx_generator.models import JobSpec, Slide, JobMeta, JobAuth
from pptx_generator.template_ai.client import AnthropicTemplateAIClient
from pptx_generator.template_ai.client import TemplateAIRequest
from pptx_generator.template_ai.policy import TemplateAIPolicy


def test_slide_ai_logs_latency(caplog: pytest.LogCaptureFixture) -> None:
    class _FakeResponse:
        def __init__(self) -> None:
            self.choices = [SimpleNamespace(message=SimpleNamespace(content='{"title": "t", "body": ["b"], "intent": "overview"}'), finish_reason="stop")]

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self) -> None:
            self.chat = _FakeChat()

    for name in ["pptx_generator.slide_ai.client", "pptx_generator.slide_ai.llm"]:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    caplog.clear()
    client = OpenAIChatClient(client=_FakeOpenAI(), model="gpt-4o-mini", temperature=0.0, max_tokens=64)
    policy = SlideAIPolicy(id="default", name="default", model="gpt-4o-mini")
    meta = JobMeta(schema_version="1.0", title="t")
    auth = JobAuth(created_by="tester")
    spec = JobSpec(meta=meta, auth=auth, slides=[Slide(id="s1", layout="cover", title="T", bullets=[], tables=[], charts=[], textboxes=[], auto_draw_anchors=[], auto_draw_boxes={})])
    req = AIGenerationRequest(prompt="p", policy=policy, spec=spec, slide=spec.slides[0], intent="overview")

    with caplog.at_level(logging.INFO):
        client.generate(req)

    assert any("slide_ai call start" in msg for msg in caplog.messages)
    assert any("slide_ai call done" in msg for msg in caplog.messages)


def test_layout_ai_logs_latency(caplog: pytest.LogCaptureFixture) -> None:
    payload = '{"recommended": [{"layout_id": "cover", "score": 0.9}]}'

    # Fake openai.types.responses classes to satisfy isinstance checks
    ResponseOutputText = type("ResponseOutputText", (), {"__init__": lambda self, text: setattr(self, "text", text)})
    ResponseOutputMessage = type(
        "ResponseOutputMessage",
        (),
        {
            "__init__": lambda self, content, status="complete": (setattr(self, "content", content), setattr(self, "status", status)),
        },
    )
    ResponseOutputRefusal = type("ResponseOutputRefusal", (), {})
    fake_module = types.SimpleNamespace(
        ResponseOutputText=ResponseOutputText,
        ResponseOutputMessage=ResponseOutputMessage,
        ResponseOutputRefusal=ResponseOutputRefusal,
    )
    sys.modules["openai.types.responses"] = fake_module

    message = ResponseOutputMessage([ResponseOutputText(payload)])
    mock_response = SimpleNamespace(output=[message], model="layout-model", status="complete")

    fake_client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: mock_response))
    for name in ["pptx_generator.layout_ai.client", "pptx_generator.layout_ai.llm"]:
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
    client = OpenAIChatLayoutClient(fake_client, model="layout-model", temperature=0.0, max_tokens=128)
    policy = LayoutAIPolicy(id="p", name="n")
    request = LayoutAIRequest(prompt="prompt", policy=policy, card_payload={}, layout_candidates=["cover"], layout_metadata={})

    caplog.clear()
    with caplog.at_level(logging.INFO):
        client.recommend(request)

    assert any("layout AI call start" in msg for msg in caplog.messages)
    assert any("layout AI call done" in msg for msg in caplog.messages)


def test_template_ai_logs_latency(caplog: pytest.LogCaptureFixture) -> None:
    class _FakeResponse:
        def __init__(self) -> None:
            self.content = [SimpleNamespace(type="text", text='{"usage_tags": ["cover"], "model": "claude"}')]
            self.model = "claude"

    class _FakeMessages:
        def create(self, **kwargs):
            return _FakeResponse()

    fake_client = SimpleNamespace(messages=_FakeMessages())
    client = AnthropicTemplateAIClient(fake_client, model="claude", max_tokens=64, temperature=0.0)
    req = TemplateAIRequest(prompt="classify", policy=TemplateAIPolicy(id="p", name="n", prompt_template="t"), payload={})

    caplog.clear()
    with caplog.at_level(logging.INFO):
        client.classify(req)

    assert any("template_ai call start" in msg for msg in caplog.messages)
    assert any("template_ai call done" in msg for msg in caplog.messages)


def test_prepare_ai_logs_latency_openai(caplog: pytest.LogCaptureFixture) -> None:
    class _FakeResponse:
        def __init__(self) -> None:
            self.choices = [SimpleNamespace(message=SimpleNamespace(content='{"chapters": []}'), finish_reason="stop")]

    class _FakeCompletions:
        def create(self, **kwargs):
            return _FakeResponse()

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    client = OpenAIPrepareLLMClient(client=fake_client, model="gpt-4o-mini", temperature=0.0, max_tokens=64)

    caplog.clear()
    with caplog.at_level(logging.INFO):
        client.generate("prompt")

    assert any("prepare_ai call start: provider=openai" in msg for msg in caplog.messages)
    assert any("prepare_ai call done: provider=openai" in msg for msg in caplog.messages)


def test_prepare_ai_logs_latency_azure(caplog: pytest.LogCaptureFixture) -> None:
    fake_response = SimpleNamespace(
        output=[SimpleNamespace(content=[SimpleNamespace(text="{}")])],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        output_text=None,
    )

    class _FakeResponses:
        def create(self, **kwargs):
            return fake_response

    fake_client = SimpleNamespace(responses=_FakeResponses())
    client = AzureOpenAIPrepareLLMClient(
        client=fake_client,
        deployment="dep",
        api_version="2024-02-15-preview",
        temperature=0.0,
        max_tokens=64,
    )

    caplog.clear()
    with caplog.at_level(logging.INFO):
        client.generate("prompt")

    assert any("prepare_ai call start: provider=azure" in msg for msg in caplog.messages)
    assert any("prepare_ai call done: provider=azure" in msg for msg in caplog.messages)
