"""TODO CP3 (student): Tool Unit Test Challenge.

Patterns to copy are in test_tools_examples.py. Fixtures are in conftest.py.

Rules:
- Offline only: mock HTTP with `fake_http`, set fake keys with `monkeypatch.setenv`.
- One behaviour per test. Name the test after the behaviour, not the function.
- Done = `pytest tests/ -v` shows 0 skipped, 0 failed.
"""
from __future__ import annotations

import sys

import pytest
import requests

from conftest import FakeResponse
from tools import TOOL_FUNCTIONS

clarify_tool = TOOL_FUNCTIONS["clarify"]
format_tool = TOOL_FUNCTIONS["format"]
send_tool = TOOL_FUNCTIONS["send"]
lookup_tool = TOOL_FUNCTIONS["lookup"]
fetch_tool = TOOL_FUNCTIONS["fetch"]
timeline_tool = TOOL_FUNCTIONS["timeline"]
social_search_tool = TOOL_FUNCTIONS["social_search"]
policy_tool = TOOL_FUNCTIONS["policy"]
hn_search_tool = TOOL_FUNCTIONS["hn_search"]
summarize_tool = TOOL_FUNCTIONS["summarize"]


# ---------------- clarify ----------------

def test_clarify_choice_returns_options_and_awaits_user() -> None:
    result = clarify_tool(question="Chọn nguồn?", response_type="choice", options=["web", "tweet"])

    assert result["response_type"] == "choice"
    assert result["options"] == ["web", "tweet"]
    assert result["awaiting_user"] is True


# ---------------- format ----------------

def test_format_sections_groups_items_by_section() -> None:
    items = [
        {"title": "a1", "section": "A"},
        {"title": "b1", "section": "B"},
        {"title": "a2", "section": "A"},
    ]
    markdown = format_tool(items=items, template="sections")["markdown"]

    assert markdown.count("## A") == 1
    assert markdown.count("## B") == 1
    assert markdown.index("a2") < markdown.index("## B")


def test_format_thread_numbers_items() -> None:
    items = [{"title": "first"}, {"title": "second"}, {"title": "third"}]
    lines = format_tool(items=items, template="thread")["markdown"].split("\n\n")

    assert [line.split(" ", 1)[0] for line in lines] == ["1/", "2/", "3/"]
    assert lines[1].startswith("2/ second")


def test_format_empty_items_does_not_crash() -> None:
    for items in (None, []):
        result = format_tool(items=items, template="sections")
        assert result["item_count"] == 0
        assert result["markdown"] == ""


# ---------------- send (guardrail) ----------------

def test_send_confirmed_posts_to_telegram(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    calls = fake_http(FakeResponse({"ok": True}))

    result = send_tool(text="Bản tin AI", confirmed=True)

    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert "test-token" in calls[0]["url"]
    assert calls[0]["json"]["chat_id"] == "-100123"
    assert calls[0]["json"]["text"] == "Bản tin AI"
    assert result["status"] == "sent"


def test_send_confirmed_without_env_returns_error_and_no_request(fake_http) -> None:
    calls = fake_http(FakeResponse({"ok": True}))

    result = send_tool(text="Bản tin AI", confirmed=True)

    assert result["error"] == "RuntimeError"
    assert "TELEGRAM_BOT_TOKEN" in result["message"]
    assert calls == []


# ---------------- lookup ----------------

def test_lookup_without_timeframe_omits_time_range(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = lookup_tool(query="AI", timeframe=None)

    assert "time_range" not in calls[0]["json"]
    assert result["items"] == []


# ---------------- fetch ----------------

def test_fetch_maps_firecrawl_response(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"data": {
        "markdown": "# Body",
        "metadata": {"title": "T", "sourceURL": "https://www.example.com/post"},
    }}))

    result = fetch_tool(url="https://www.example.com/post")

    assert calls[0]["url"] == "https://api.firecrawl.dev/v1/scrape"
    assert calls[0]["json"]["url"] == "https://www.example.com/post"
    assert result["items"][0] == {
        "title": "T", "url": "https://www.example.com/post",
        "source": "example.com", "summary": "# Body",
    }


def test_fetch_truncates_markdown_to_4000_chars(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    fake_http(FakeResponse({"data": {"markdown": "x" * 5000, "metadata": {}}}))

    summary = fetch_tool(url="https://example.com")["items"][0]["summary"]

    assert len(summary) == 4000


# ---------------- timeline / social_search ----------------

def test_timeline_respects_limit_and_skips_items_without_id(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "test-key")
    raw = [{"text": "no id", "screen_name": "sama"}]
    raw += [{"tweet_id": str(i), "text": f"tweet {i}", "screen_name": "sama"} for i in range(6)]
    calls = fake_http(FakeResponse({"timeline": raw}))

    result = timeline_tool(screenname="sama", limit=3)

    assert calls[0]["params"] == {"screenname": "sama"}
    assert len(result["items"]) == 3
    assert [item["url"] for item in result["items"]] == [
        "https://x.com/sama/status/0", "https://x.com/sama/status/1", "https://x.com/sama/status/2",
    ]


def test_social_search_passes_search_type(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "test-key")
    calls = fake_http(FakeResponse({"timeline": []}))

    result = social_search_tool(query="GPT-5", search_type="Top")

    assert calls[0]["url"].endswith("/search.php")
    assert calls[0]["params"] == {"query": "GPT-5", "search_type": "Top"}
    assert result["search_type"] == "Top"


# ---------------- policy (local knowledge + trust boundary) ----------------

def test_policy_empty_query_returns_no_results() -> None:
    assert policy_tool(query="")["results"] == []


def test_policy_area_filter_only_returns_that_area() -> None:
    results = policy_tool(query="data privacy personal", policy_area="data_privacy", top_k=10)["results"]

    assert results
    assert all(item["policy_area"] == "data_privacy" for item in results)


def test_policy_instruction_like_lines_go_to_untrusted_text() -> None:
    results = policy_tool(query="citation injection probe", policy_area="source_citation", top_k=10)["results"]
    probe = [item for item in results if item["section"] == "Injection probe"]

    assert probe, "the Injection probe section should be retrieved"
    assert any("ignore the citation policy" in line for line in probe[0]["untrusted_text"])
    assert all("ignore the citation policy" not in item["facts"] for item in results)


# ---------------- NEW TOOL: hn_search ----------------
# 1. happy path (mocked API)  2. bad input from the model  3. failure path -> error dict

HN_HITS = {"hits": [
    {
        "objectID": "111", "title": "LLM agents in production", "url": "https://www.example.com/agents",
        "points": 250, "num_comments": 80, "created_at": "2026-11-10T08:00:00Z",
    },
    {
        "objectID": "222", "title": "Ask HN: Best eval tools?", "url": None,
        "story_text": "What do you use?<p>See <a href=\"https:&#x2F;&#x2F;x.dev\">x.dev</a> &amp; more",
        "points": 40, "num_comments": 12, "created_at": "2026-11-09T08:00:00Z",
    },
]}


def test_hn_search_sends_expected_request_and_maps_hits(monkeypatch, fake_http) -> None:
    # `tools.hn_search` is the registered function, so reach the module through sys.modules.
    monkeypatch.setattr(sys.modules["tools.hn_search.tool"].time, "time", lambda: 1_000_000)
    calls = fake_http(FakeResponse(HN_HITS))

    result = hn_search_tool(query="LLM agents", sort_by="date", timeframe="week", limit=2)

    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search_by_date"
    assert calls[0]["params"] == {
        "query": "LLM agents", "tags": "story", "hitsPerPage": 2,
        "numericFilters": f"created_at_i>{1_000_000 - 7 * 86_400}",
    }
    assert result["items"][0] == {
        "title": "LLM agents in production", "url": "https://www.example.com/agents", "source": "example.com",
        "summary": "", "date": "2026-11-10T08:00:00Z",
        "discussion_url": "https://news.ycombinator.com/item?id=111",
        "metrics": {"points": 250, "comments": 80},
    }
    # Ask HN has no external url -> falls back to the discussion page
    assert result["items"][1]["url"] == "https://news.ycombinator.com/item?id=222"
    assert result["items"][1]["source"] == "news.ycombinator.com"
    # HTML story_text is converted to plain text
    assert result["items"][1]["summary"] == "What do you use? See x.dev & more"


def test_hn_search_default_relevance_without_time_filter(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    result = hn_search_tool(query="rust")

    assert calls[0]["url"] == "https://hn.algolia.com/api/v1/search"
    assert "numericFilters" not in calls[0]["params"]
    assert calls[0]["params"]["hitsPerPage"] == 5
    assert result["items"] == []


@pytest.mark.parametrize("kwargs, message_part", [
    ({"query": ""}, "query"),
    ({"query": "   "}, "query"),
    ({"query": None}, "query"),
    ({"query": "ai", "sort_by": "Top"}, "sort_by"),
    ({"query": "ai", "timeframe": "hour"}, "timeframe"),
    ({"query": "ai", "limit": "five"}, "limit"),
])
def test_hn_search_bad_input_returns_error_dict_without_request(fake_http, kwargs, message_part) -> None:
    calls = fake_http(FakeResponse(HN_HITS))

    result = hn_search_tool(**kwargs)

    assert result["tool"] == "hn_search"
    assert result["error"] == "ValueError"
    assert message_part in result["message"]
    assert calls == []


def test_hn_search_coerces_string_limit_and_clamps_to_20(fake_http) -> None:
    calls = fake_http(FakeResponse({"hits": []}))

    hn_search_tool(query="ai", limit="5")
    hn_search_tool(query="ai", limit=500)
    hn_search_tool(query="ai", limit=0)

    assert [call["params"]["hitsPerPage"] for call in calls] == [5, 20, 1]


@pytest.mark.parametrize("status", [429, 500])
def test_hn_search_http_error_returns_error_dict(fake_http, status) -> None:
    fake_http(FakeResponse(status_code=status))

    result = hn_search_tool(query="ai")

    assert result == {"tool": "hn_search", "error": "HTTPError", "message": f"HTTP {status}"}


def test_hn_search_timeout_returns_error_dict(fake_http) -> None:
    fake_http(requests.Timeout("read timed out"))

    result = hn_search_tool(query="ai")

    assert result["error"] == "Timeout"
    assert "timed out" in result["message"]


# ---------------- NEW TOOL: summarize ----------------
# 1. happy path — dedupe   2. happy path — score ranking
# 3. bad input (mode)      4. bad input (limit type)   5. empty / bad items


def test_summarize_dedupe_keeps_one_item_per_source() -> None:
    items = [
        {"title": "A1", "source": "openai.com", "score": 0.9},
        {"title": "A2", "source": "openai.com", "score": 0.8},  # trùng domain
        {"title": "B1", "source": "arxiv.org",  "score": 0.7},
    ]
    result = summarize_tool(items=items, mode="dedupe", limit=10)

    assert result["tool"] == "summarize"
    assert result["mode"] == "dedupe"
    assert result["input_count"] == 3
    assert result["output_count"] == 2
    titles = [i["title"] for i in result["items"]]
    assert "A1" in titles
    assert "A2" not in titles           # bị loại vì trùng openai.com
    assert "B1" in titles


def test_summarize_score_ranks_by_keyword_overlap() -> None:
    items = [
        {"title": "LLM agent eval framework", "summary": "benchmarks for agents"},
        {"title": "Weather today",             "summary": "sunny skies"},
        {"title": "Agent routing in LLM",      "summary": "tool use"},
    ]
    result = summarize_tool(items=items, mode="score", query="LLM agent", limit=3)

    assert result["tool"] == "summarize"
    assert result["query"] == "LLM agent"
    assert result["output_count"] == 3
    ranked_titles = [i["title"] for i in result["items"]]
    # 2 bài có "LLM" và "agent" phải lên trước "Weather today"
    assert ranked_titles.index("Weather today") > ranked_titles.index("LLM agent eval framework")


@pytest.mark.parametrize("mode", ["top", "newest", "", None])
def test_summarize_invalid_mode_returns_error_dict(mode) -> None:
    result = summarize_tool(items=[{"title": "x"}], mode=mode)

    assert result["tool"] == "summarize"
    assert result["error"] == "ValueError"
    assert "mode" in result["message"]


@pytest.mark.parametrize("bad_limit", [True, False, "nhiều", [5]])
def test_summarize_invalid_limit_returns_error_dict(bad_limit) -> None:
    result = summarize_tool(items=[], limit=bad_limit)

    assert result["tool"] == "summarize"
    assert result["error"] == "ValueError"
    assert "limit" in result["message"]


@pytest.mark.parametrize("items", [None, [], [42, "bad", None]])
def test_summarize_empty_or_bad_items_returns_zero_output(items) -> None:
    for mode in ("highlights", "by_date", "dedupe", "score"):
        result = summarize_tool(items=items, mode=mode)
        assert result["output_count"] == 0
        assert result["items"] == []
        assert "error" not in result
