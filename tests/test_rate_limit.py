
import httpx
import pytest
from app import agent


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    async def post(self, url, *, headers, json):
        index = min(self.calls, len(self.responses)-1)
        self.calls += 1
        status, body = self.responses[index]
        return httpx.Response(status, json=body, request=httpx.Request('POST', url))


@pytest.mark.asyncio
async def test_retry_temporary_429_then_success(monkeypatch):
    async def fake_sleep(value):
        assert value >= 5
    monkeypatch.setattr(agent.asyncio, 'sleep', fake_sleep)
    client = FakeClient([(429, {'error': {'code': 'rate_limit_exceeded', 'type': 'rate_limit_error'}}),
                         (200, {'output': []})])
    result = await agent._post_llm_with_rate_limit(client, 'https://example.test/responses', 'fake-key', {})
    assert result.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_no_retry_for_quota_error(monkeypatch):
    async def fake_sleep(value):
        pytest.fail('No debe esperar ni reintentar para cuota agotada')
    monkeypatch.setattr(agent.asyncio, 'sleep', fake_sleep)
    client = FakeClient([(429, {'error': {'code': 'credit_balance_exhausted', 'type': 'insufficient_quota'}})])
    with pytest.raises(httpx.HTTPStatusError):
        await agent._post_llm_with_rate_limit(client, 'https://example.test/responses', 'fake-key', {})
    assert client.calls == 1


@pytest.mark.asyncio
async def test_retry_stops_after_two_attempts(monkeypatch):
    async def fake_sleep(value):
        return None
    monkeypatch.setattr(agent.asyncio, 'sleep', fake_sleep)
    client = FakeClient([(429, {'error': {'code': 'rate_limit_exceeded'}})])
    with pytest.raises(httpx.HTTPStatusError):
        await agent._post_llm_with_rate_limit(client, 'https://example.test/responses', 'fake-key', {})
    assert client.calls == 3
