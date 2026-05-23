"""Tests for digest.py"""
from __future__ import annotations
from pathlib import Path

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


def test_is_ai_repo_matches_name():
    from digest import is_ai_repo
    assert is_ai_repo({"name": "openai/gpt-5-tools", "description": ""}) is True


def test_is_ai_repo_matches_description():
    from digest import is_ai_repo
    assert is_ai_repo({"name": "cool/project", "description": "RAG pipeline for documents"}) is True


def test_is_ai_repo_no_match():
    from digest import is_ai_repo
    assert is_ai_repo({"name": "torvalds/linux", "description": "Linux kernel source tree"}) is False


def test_is_ai_repo_case_insensitive():
    from digest import is_ai_repo
    assert is_ai_repo({"name": "foo/bar", "description": "An LLM-based summarizer"}) is True


def test_filter_ai_repos_keeps_ai():
    from digest import filter_ai_repos
    repos = [
        {"name": "openai/gpt-5-tools", "description": "GPT-5 API", "stars_today": 500, "url": ""},
        {"name": "torvalds/linux", "description": "kernel", "stars_today": 300, "url": ""},
        {"name": "anthropic/mcp-python", "description": "MCP SDK", "stars_today": 200, "url": ""},
    ]
    result = filter_ai_repos(repos)
    assert len(result) == 2
    assert all(r["name"] != "torvalds/linux" for r in result)


def test_filter_ai_repos_empty_input():
    from digest import filter_ai_repos
    assert filter_ai_repos([]) == []


def test_is_ai_repo_no_false_positive_on_substring():
    from digest import is_ai_repo
    # "railway" contains "ai" as substring but not as whole word
    assert is_ai_repo({"name": "foo/railway", "description": "Train scheduling"}) is False
    # "repair" contains "ai" as substring
    assert is_ai_repo({"name": "foo/repair-tool", "description": "Fix things"}) is False
