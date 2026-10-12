import pytest


@pytest.fixture(autouse=True)
def _no_live_edgar(monkeypatch):
    """Unit tests must not call SEC; tests of agent.edgar itself use mocked transports."""
    async def none(events, today, client=None):
        return []
    monkeypatch.setattr("agent.run.edgar_detect", none)
