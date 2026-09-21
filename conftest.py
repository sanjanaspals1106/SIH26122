"""Repo-wide pytest configuration."""
import pytest


@pytest.fixture(autouse=True)
def _no_extraction_fallback_by_default(monkeypatch):
    """The demo .env enables EXTRACTION_FALLBACK=rules. Tests assert the strict contract
    (extraction failures raise) unless a test opts in with monkeypatch.setenv."""
    monkeypatch.delenv("EXTRACTION_FALLBACK", raising=False)
