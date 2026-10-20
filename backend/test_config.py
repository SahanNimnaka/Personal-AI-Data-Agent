
"""Tests for deployment configuration parsing (CORS origins, port)."""

import pytest

from main import DEFAULT_CORS_ORIGINS, parse_cors_origins
from run import DEFAULT_PORT, get_port


def test_unset_returns_local_defaults():
    assert parse_cors_origins(None) == DEFAULT_CORS_ORIGINS


def test_blank_returns_local_defaults():
    assert parse_cors_origins("") == DEFAULT_CORS_ORIGINS
    assert parse_cors_origins("   ") == DEFAULT_CORS_ORIGINS


def test_single_origin_parsed():
    assert parse_cors_origins("https://app.example.com") == [
        "https://app.example.com"
    ]


def test_multiple_origins_parsed_and_trimmed():
    raw = " https://app.example.com , https://www.example.com "
    assert parse_cors_origins(raw) == [
        "https://app.example.com",
        "https://www.example.com",
    ]


def test_empty_entries_ignored():
    raw = "https://a.example.com,,  ,https://b.example.com"
    assert parse_cors_origins(raw) == [
        "https://a.example.com",
        "https://b.example.com",
    ]


def test_duplicate_origins_deduplicated():
    raw = "https://a.example.com,https://a.example.com"
    assert parse_cors_origins(raw) == ["https://a.example.com"]


def test_wildcard_rejected():
    with pytest.raises(ValueError):
        parse_cors_origins("*")
    with pytest.raises(ValueError):
        parse_cors_origins("https://a.example.com,*")


def test_only_commas_returns_defaults():
    assert parse_cors_origins(",,,") == DEFAULT_CORS_ORIGINS


def test_defaults_are_copies():
    """Returned defaults must not share the module-level list."""
    result = parse_cors_origins(None)
    result.append("https://mutated.example.com")
    assert "https://mutated.example.com" not in DEFAULT_CORS_ORIGINS


def test_get_port_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    assert get_port() == DEFAULT_PORT


def test_get_port_reads_env(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    assert get_port() == 9000


def test_get_port_invalid_falls_back(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-port")
    assert get_port() == DEFAULT_PORT


def test_get_port_out_of_range_falls_back(monkeypatch):
    monkeypatch.setenv("PORT", "70000")
    assert get_port() == DEFAULT_PORT
