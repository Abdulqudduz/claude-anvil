"""Tests for the OpenAlex HTTP client: auth, retry policy, budget handling.

Offline: requests go through httpx.MockTransport, and backoff sleeps are
stubbed out, so the suite never touches the network or waits.
"""

import logging

import httpx
import pytest

from vista.sources import openalex
from vista.sources.openalex import OpenAlexBudgetExhausted, OpenAlexClient

WORK = {"id": "https://openalex.org/W1", "display_name": "A work"}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Record backoff waits instead of sleeping."""
    waits: list[float] = []
    monkeypatch.setattr(openalex, "_sleep", waits.append)
    return waits


@pytest.fixture(autouse=True)
def no_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.setattr(openalex, "_warned_no_key", False)


def scripted(*responses):
    """A MockTransport that replays responses in order and records requests."""
    requests: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return queue.pop(0)

    return httpx.MockTransport(handler), requests


def ok():
    return httpx.Response(200, json=WORK)


# --- auth -------------------------------------------------------------------


def test_api_key_from_env_sent_as_bearer_header_not_in_url(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-key")
    transport, requests = scripted(ok())
    with OpenAlexClient(transport=transport) as c:
        c.work_by_id("W1")
    assert requests[0].headers["Authorization"] == "Bearer secret-key"
    assert "secret-key" not in str(requests[0].url)


def test_explicit_api_key_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "env-key")
    transport, requests = scripted(ok())
    with OpenAlexClient(api_key="arg-key", transport=transport) as c:
        c.work_by_id("W1")
    assert requests[0].headers["Authorization"] == "Bearer arg-key"


def test_no_key_works_and_warns_once(caplog):
    transport, requests = scripted(ok(), ok())
    with caplog.at_level(logging.WARNING, logger="vista.sources.openalex"):
        with OpenAlexClient(transport=transport) as c:
            c.work_by_id("W1")
        with OpenAlexClient(transport=transport) as c:
            c.work_by_id("W1")
    assert "Authorization" not in requests[0].headers
    warnings = [r for r in caplog.records if "OPENALEX_API_KEY" in r.getMessage()]
    assert len(warnings) == 1


def test_user_agent_carries_package_version():
    from vista.config import VERSION

    transport, requests = scripted(ok())
    with OpenAlexClient(transport=transport) as c:
        c.work_by_id("W1")
    assert requests[0].headers["User-Agent"].startswith(f"vista/{VERSION} ")
    assert VERSION != "0.1"


# --- retry policy -----------------------------------------------------------


def test_404_is_not_retried_and_maps_to_none():
    transport, requests = scripted(httpx.Response(404))
    with OpenAlexClient(transport=transport) as c:
        assert c.work_by_doi("10.1/x") is None
    assert len(requests) == 1


def test_other_4xx_raises_immediately():
    transport, requests = scripted(httpx.Response(400))
    with OpenAlexClient(transport=transport) as c, pytest.raises(httpx.HTTPStatusError):
        c.work_by_id("W1")
    assert len(requests) == 1


def test_5xx_is_retried_then_succeeds():
    transport, requests = scripted(httpx.Response(503), httpx.Response(502), ok())
    with OpenAlexClient(transport=transport) as c:
        assert c.work_by_id("W1").id == "W1"
    assert len(requests) == 3


def test_5xx_gives_up_after_max_attempts_with_original_error():
    transport, requests = scripted(*[httpx.Response(500) for _ in range(4)])
    with OpenAlexClient(transport=transport) as c, pytest.raises(httpx.HTTPStatusError):
        c.work_by_id("W1")
    assert len(requests) == 4


def test_per_second_429_is_retried_honoring_retry_after(no_sleep):
    throttled = httpx.Response(429, headers={"Retry-After": "2", "x-ratelimit-remaining": "500"})
    transport, requests = scripted(throttled, ok())
    with OpenAlexClient(transport=transport) as c:
        assert c.work_by_id("W1").id == "W1"
    assert len(requests) == 2
    assert no_sleep == [2.0]


def test_budget_exhausted_429_fails_fast_with_key_hint():
    exhausted = httpx.Response(429, headers={"x-ratelimit-remaining": "0"})
    transport, requests = scripted(exhausted)
    with OpenAlexClient(transport=transport) as c, pytest.raises(OpenAlexBudgetExhausted) as e:
        c.work_by_id("W1")
    assert len(requests) == 1
    assert "OPENALEX_API_KEY" in str(e.value)


def test_connection_error_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return ok()

    with OpenAlexClient(transport=httpx.MockTransport(handler)) as c:
        assert c.work_by_id("W1").id == "W1"
    assert calls["n"] == 2
