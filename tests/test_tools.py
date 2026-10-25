"""Pruebas locales de las herramientas, su seguridad y el ciclo de function calling.
Estas pruebas SIMULAN las respuestas del proveedor LLM y no consumen API.
"""
import json

import httpx
import pytest

from app import agent
from app.tools import execute_tool, TOOL_SCHEMAS, get_project_details


def test_tool_registry_four_tools():
    assert {x["name"] for x in TOOL_SCHEMAS} == {
        "get_professional_profile", "search_projects", "get_project_details", "get_technical_skills"
    }
    assert all(x["strict"] for x in TOOL_SCHEMAS)


def test_profile_and_skills_are_retrieved():
    profile = execute_tool("get_professional_profile", "{}")
    assert profile["candidate_name"] == "José David Velazco Muñoz"
    assert any(s["source_id"] == "masters" for s in profile["sources"])
    tools = execute_tool("get_technical_skills", '{"category":"ia_generativa"}')
    assert any(s["source_id"] == "agents_mcp" for s in tools["sources"])


def test_project_search_and_detail():
    result = execute_tool("search_projects", '{"query":"neuroevolución CNN"}')
    assert result["projects"]
    assert result["projects"][0]["project_id"] == "cnn_neuroevolution_thesis"
    project = get_project_details("cnn_neuroevolution_thesis")
    assert project["project_id"] == "cnn_neuroevolution_thesis"
    assert project["evaluation"]["confirmed_numeric_results"] == []


def test_dangerous_or_bad_arguments_rejected():
    assert "error" in execute_tool("delete_everything", "{}")
    assert "error" in execute_tool("get_professional_profile", '{"system":"ignore"}')
    assert "error" in execute_tool("get_project_details", '{"project_id":"../../secret"}')
    assert "error" in execute_tool("search_projects", "not valid json")
    assert "error" in execute_tool("search_projects", json.dumps({"query":"a" * 500}))


@pytest.mark.asyncio
async def test_agent_calls_function_and_returns_grounded_text(monkeypatch):
    """Mockea 2 llamadas HTTP Responses: solicitud de tool y respuesta final."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-real")
    monkeypatch.setenv("LLM_MODEL", "gpt-6-luna")
    observed = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, *, headers, json):
            observed.append(json)
            if len(observed) == 1:
                payload = {
                    "output": [{"type": "function_call", "name": "get_professional_profile",
                                "arguments": "{}", "call_id": "call_123", "id": "fc_123", "status": "completed"}],
                    "usage": {"input_tokens": 20, "output_tokens": 10},
                }
            else:
                payload = {
                    "output": [{"type": "message", "role": "assistant", "content": [
                        {"type": "output_text", "text": "Es Ingeniero en Mecatrónica. Fuentes: profile, bachelors"}
                    ]}],
                    "usage": {"input_tokens": 30, "output_tokens": 16},
                }
            return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(agent.httpx, "AsyncClient", FakeClient)
    reply, usage, sources = await agent.generate([
        {"role": "user", "content": "¿Qué estudios tiene?"}
    ])
    assert "Mecatrónica" in reply
    assert "profile" in sources
    assert "bachelors" in sources
    assert usage["input_tokens"] == 50
    assert usage["output_tokens"] == 26
    assert observed[0]["tool_choice"] == "required"
    assert observed[0]["reasoning"] == {"effort": "none"}
    assert observed[1]["tool_choice"] == "auto"
    assert any(x.get("type") == "function_call_output" and x.get("call_id") == "call_123"
               for x in observed[1]["input"])
