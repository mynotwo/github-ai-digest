"""Tests for digest.py"""
from __future__ import annotations
import os
from pathlib import Path
import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "trending.html"


def _fixture_html() -> str:
    return FIXTURE_PATH.read_text()


def test_parse_trending_returns_list():
    from digest import parse_trending
    result = parse_trending(_fixture_html())
    assert isinstance(result, list)


def test_parse_trending_finds_all_repos():
    from digest import parse_trending
    result = parse_trending(_fixture_html())
    assert len(result) == 3


def test_parse_trending_repo_fields():
    from digest import parse_trending
    result = parse_trending(_fixture_html())
    repo = result[0]
    assert repo["name"] == "openai/gpt-5-tools"
    assert repo["url"] == "https://github.com/openai/gpt-5-tools"
    assert "GPT-5" in repo["description"]
    assert repo["stars_today"] == 2345


def test_parse_trending_star_parsing():
    from digest import parse_trending
    result = parse_trending(_fixture_html())
    assert result[1]["stars_today"] == 1000
    assert result[2]["stars_today"] == 876


def test_parse_stars_with_comma():
    from digest import parse_stars
    assert parse_stars("2,345 stars today") == 2345


def test_parse_stars_no_comma():
    from digest import parse_stars
    assert parse_stars("876 stars today") == 876


def test_parse_stars_zero_on_missing():
    from digest import parse_stars
    assert parse_stars("no stars here") == 0
