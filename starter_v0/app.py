"""Streamlit UI cho Research Agent.

Chạy từ starter_v0/:
    streamlit run app.py

Bố cục:
- Trang "Chat": khung chat ở giữa, sidebar trái liệt kê tool của phiên chat, câu hỏi mẫu nằm
  ngay trên ô nhập, cài đặt (provider/model/prompt+tools) trong nút ⚙️ góc trên.
  Chọn chat với file đang sửa (artifacts/) hoặc một snapshot artifacts/versions/<v>/
  (tạo bằng `python scripts/snapshot_version.py <v>`).
  Tái dùng vòng lặp model -> tool của chat.py và ghi transcript cùng format
  (transcripts/*.transcript.json).
- Trang "Eval runs": đọc runs/*.json do run_eval.py sinh ra, hiện summary, case FAIL,
  expected vs actual tool calls và version_log.csv.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    ROOT,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
VERSION_LOG = ARTIFACTS_DIR / "version_log.csv"
VERSIONS_DIR = ARTIFACTS_DIR / "versions"
CURRENT_ARTIFACTS = "current"
PROVIDERS = ["openrouter", "openai", "anthropic", "gemini", "ollama"]

# Tool có sẵn trong starter. Tool nào trong tools.yaml không nằm ở đây sẽ được gắn nhãn "MỚI".
STARTER_TOOLS = {
    "clarify", "timeline", "social_search", "lookup", "fetch",
    "format", "send", "policy", "papers", "paper_text",
}

# Icon + mô tả ngắn cho người dùng. Tool mới chưa có ở đây thì lấy câu đầu trong tools.yaml.
TOOL_INFO = {
    "clarify": ("❓", "Hỏi lại khi thiếu thông tin hoặc cần bạn xác nhận"),
    "timeline": ("🐦", "Xem tweet gần đây của một tài khoản X"),
    "social_search": ("🔍", "Tìm tweet theo từ khóa (Latest / Top)"),
    "lookup": ("🌐", "Tìm trên web, có chế độ tin tức theo thời gian"),
    "fetch": ("📄", "Đọc nội dung một URL cụ thể"),
    "format": ("📰", "Trình bày kết quả thành bản tin markdown"),
    "send": ("📤", "Gửi lên Telegram, chỉ sau khi bạn xác nhận"),
    "policy": ("📚", "Tra chính sách nội bộ của công ty"),
    "papers": ("🎓", "Tìm paper trên arXiv"),
    "paper_text": ("📑", "Đọc nội dung PDF của paper arXiv"),
    # Tool nhóm tự viết
    "hn_search": ("🟧", "Tìm bài thảo luận trên Hacker News"),
    "summarize": ("🧹", "Lọc, xếp hạng, loại trùng kết quả trước khi trình bày"),
}

# Câu hỏi mẫu hiện dưới khung chat, đồng bộ với mục A3 của group_report.md.
# Chỉ giữ câu đã chạy đúng ở v4 (R01 "Sam Altman" vẫn FAIL nên không đưa vào).
SAMPLE_QUESTIONS = [
    "Tin tức AI hôm nay có gì nổi bật?",
    "Tweet mới nhất của Elon Musk là gì?",
    "Trên Hacker News tuần này mọi người đang bàn gì về LLM agents?",
    "Tìm 3 paper mới nhất về LLM agents trên arXiv",
    "Tóm tắt 5 tweet mới nhất giúp mình",
    "Đăng bản tin AI hôm nay lên Telegram",
]

STATUS_BADGE = {
    "answered": ("Đã trả lời", "green", "✅"),
    "waiting_for_user": ("Agent đang hỏi lại", "orange", "❓"),
    "max_tool_rounds": ("Dừng vì quá số vòng tool", "orange", "⚠️"),
    "provider_error": ("Lỗi provider", "red", "❌"),
}

st.set_page_config(page_title="QwenChana Research Agent", page_icon="🔎", layout="wide")


# ----------------------------------------------------------------------------
# Helpers chung
# ----------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_provider(name: str):
    return make_provider(name)


@st.cache_data(show_spinner=False)
def read_tool_declarations(path: str, mtime: float) -> list[dict[str, Any]]:
    return load_tool_declarations(Path(path))


def version_key(name: str) -> tuple:
    """Sắp xếp v0, v1, ..., v10 theo số; tên khác (v4-local) xếp sau theo chữ."""
    digits = name[1:] if name.startswith("v") else ""
    return (0, int(digits), name) if digits.isdigit() else (1, 0, name)


def list_snapshots() -> list[str]:
    """Các snapshot trong artifacts/versions/<v>/, mới nhất trước."""
    if not VERSIONS_DIR.exists():
        return []
    names = [
        p.name for p in VERSIONS_DIR.iterdir()
        if p.is_dir() and (p / "system_prompt.md").exists() and (p / "tools.yaml").exists()
    ]
    return sorted(names, key=version_key, reverse=True)


def list_artifact_sets() -> list[str]:
    """Snapshot (mới nhất trước) + 'current' (artifacts/ đang sửa) ở cuối."""
    return [*list_snapshots(), CURRENT_ARTIFACTS]


def artifact_paths(artifact_set: str) -> tuple[Path, Path]:
    base = ARTIFACTS_DIR if artifact_set == CURRENT_ARTIFACTS else VERSIONS_DIR / artifact_set
    return base / "system_prompt.md", base / "tools.yaml"


def artifact_set_label(artifact_set: str) -> str:
    if artifact_set == CURRENT_ARTIFACTS:
        return "current (artifacts/ đang sửa)"
    return f"{artifact_set} (artifacts/versions/{artifact_set})"


def session_tools() -> list[dict[str, Any]]:
    """Tool của phiên chat hiện tại (đúng snapshot đã chọn), không phải file đang sửa."""
    tools_path = ROOT / st.session_state.transcript["tools"]
    return read_tool_declarations(str(tools_path), tools_path.stat().st_mtime)


def pretty(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def first_sentence(text: str, limit: int = 90) -> str:
    text = (text or "").strip().split(". ")[0].rstrip(".")
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ----------------------------------------------------------------------------
# Session / agent
# ----------------------------------------------------------------------------
def init_settings() -> None:
    s = st.session_state
    s.setdefault("cfg_provider", "openrouter")
    s.setdefault("cfg_model", "")
    s.setdefault("cfg_artifact_set", list_artifact_sets()[0])
    s.setdefault("cfg_dev_version", "dev")
    s.setdefault("cfg_history_window", 5)
    s.setdefault("cfg_max_tool_rounds", 4)
    if s.cfg_artifact_set not in list_artifact_sets():  # snapshot bị xoá/đổi tên
        s.cfg_artifact_set = list_artifact_sets()[0]


def cfg_model() -> str | None:
    return st.session_state.cfg_model.strip() or None


def cfg_version() -> str:
    """Snapshot thì version = tên snapshot; file đang sửa thì dùng nhãn tự nhập."""
    s = st.session_state
    if s.cfg_artifact_set == CURRENT_ARTIFACTS:
        return s.cfg_dev_version.strip() or "dev"
    return s.cfg_artifact_set


def new_session() -> None:
    s = st.session_state
    version = cfg_version()
    prompt_path, tools_path = artifact_paths(s.cfg_artifact_set)
    artifact_version = build_artifact_version(version, prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(s.cfg_provider), "ui", timestamp])
    s.transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    s.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": s.cfg_provider,
        "model": cfg_model(),
        "artifact_set": s.cfg_artifact_set,
        "system_prompt": prompt_path.relative_to(ROOT).as_posix(),
        "tools": tools_path.relative_to(ROOT).as_posix(),
        "history_window": int(s.cfg_history_window),
        "max_tool_rounds": int(s.cfg_max_tool_rounds),
        "ui": "streamlit",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    s.history = []   # message gửi lại cho model
    s.display = []   # turn_record để render lại khung chat
    s.turn_index = 0


def run_turn(user_text: str) -> dict[str, Any]:
    s = st.session_state
    # Dùng đúng prompt/tools của phiên chat (chọn trong Cài đặt), không phải file đang sửa.
    system_prompt = (ROOT / s.transcript["system_prompt"]).read_text(encoding="utf-8")
    openai_tools = to_openai_tools(session_tools())
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(s.history, int(s.transcript["history_window"])),
        {"role": "user", "content": user_text},
    ]
    s.turn_index += 1
    turn_record: dict[str, Any] = {
        "turn_index": s.turn_index,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    try:
        result = run_model_tool_loop(
            provider=get_provider(s.transcript["provider"]),
            messages=messages,
            tools=openai_tools,
            model=s.transcript["model"],
            max_tool_rounds=int(s.transcript["max_tool_rounds"]),
        )
        turn_record.update(result)
        s.history.append({"role": "user", "content": user_text})
        s.history.append({"role": "assistant", "content": result["assistant_text"]})
    except Exception as exc:  # lỗi provider là bằng chứng, ghi vào transcript thay vì sập UI
        turn_record.update({"status": "provider_error", "error": f"{type(exc).__name__}: {exc}"})

    turn_record["ended_at"] = now_iso()
    s.transcript["turns"].append(turn_record)
    write_transcript(s.transcript_path, s.transcript)
    return turn_record


def queue_question(question: str) -> None:
    st.session_state.pending_prompt = question


# ----------------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------------
CHAT_CSS = """
<style>
.block-container {max-width: 960px; padding-top: 2.2rem;}
.hero-title {font-size: 1.9rem; font-weight: 750; line-height: 1.2; margin: 0;
  background: linear-gradient(90deg, #5B5BD6, #0EA5E9); -webkit-background-clip: text;
  background-clip: text; color: transparent;}
.hero-sub {opacity: .7; margin: .2rem 0 0 0; font-size: .95rem;}
.welcome {border: 1px solid rgba(128,128,128,.25); border-radius: 14px; padding: 1.1rem 1.3rem;
  margin: 1.2rem 0; background: rgba(91,91,214,.06);}
.welcome b {color: #5B5BD6;}
.samples-label {font-size: .8rem; opacity: .65; margin: 1rem 0 .3rem 0; text-transform: uppercase;
  letter-spacing: .04em;}
.tool-card {border: 1px solid rgba(128,128,128,.22); border-radius: 10px; padding: .5rem .65rem;
  margin-bottom: .45rem; display: flex; gap: .55rem; align-items: flex-start;}
.tool-icon {font-size: 1.15rem; line-height: 1.3;}
.tool-name {font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 650;
  font-size: .85rem;}
.tool-desc {font-size: .78rem; opacity: .75; line-height: 1.3;}
.tag {font-size: .62rem; font-weight: 700; padding: 1px 6px; border-radius: 999px; margin-left: 4px;
  vertical-align: middle;}
.tag-new {background: #16A34A; color: #fff;}
.tag-guard {background: rgba(245,158,11,.18); color: #B45309;}
.side-meta {font-size: .75rem; opacity: .6;}
</style>
"""


def render_tool_sidebar() -> None:
    tools = session_tools()
    t = st.session_state.transcript
    with st.sidebar:
        st.markdown("### 🧰 Tool của agent")
        st.markdown(f"<div class='side-meta'>{len(tools)} tool · <b>{t['version']}</b> · "
                    f"<code>{t['tools']}</code></div>", unsafe_allow_html=True)
        st.write("")
        cards = []
        for tool in tools:
            name = tool["name"]
            icon, desc = TOOL_INFO.get(name, ("🧩", first_sentence(tool.get("description", ""))))
            tags = ""
            if name not in STARTER_TOOLS:
                tags += "<span class='tag tag-new'>MỚI</span>"
            if name == "send":
                tags += "<span class='tag tag-guard'>cần xác nhận</span>"
            cards.append(
                f"<div class='tool-card'><div class='tool-icon'>{icon}</div>"
                f"<div><div class='tool-name'>{name}{tags}</div><div class='tool-desc'>{desc}</div></div></div>"
            )
        st.markdown("".join(cards), unsafe_allow_html=True)


def render_settings_popover() -> None:
    s = st.session_state
    with st.popover("⚙️ Cài đặt", width="stretch"):
        st.selectbox("Provider", PROVIDERS, key="cfg_provider")
        st.text_input("Model", key="cfg_model", placeholder="Bỏ trống = mặc định của provider")
        st.selectbox(
            "Prompt + tools", list_artifact_sets(), key="cfg_artifact_set", format_func=artifact_set_label,
            help="Chat với snapshot của một version, hoặc với file đang sửa. "
                 "Tạo snapshot: python scripts/snapshot_version.py <version>",
        )
        if s.cfg_artifact_set == CURRENT_ARTIFACTS:
            st.text_input("Version label", key="cfg_dev_version",
                          help="Nhãn ghi vào transcript khi chat với file đang sửa, ví dụ v3.")
        c1, c2 = st.columns(2)
        c1.number_input("History window", min_value=0, max_value=20, key="cfg_history_window")
        c2.number_input("Max tool rounds", min_value=1, max_value=10, key="cfg_max_tool_rounds")

        t = s.transcript
        changed = (t["version"] != cfg_version() or t.get("artifact_set") != s.cfg_artifact_set
                   or t["provider"] != s.cfg_provider or t["model"] != cfg_model()
                   or t["history_window"] != int(s.cfg_history_window)
                   or t["max_tool_rounds"] != int(s.cfg_max_tool_rounds))
        if changed:
            st.warning("Cài đặt đã đổi. Bấm **Cuộc chat mới** để áp dụng.")
        st.divider()
        st.caption("Phiên hiện tại")
        st.code(f"{t['artifact_version']}\nprovider={t['provider']}  model={t['model'] or 'default'}\n"
                f"{t['system_prompt']}\n{t['tools']}", language=None)
        st.caption("Transcript")
        st.code(str(Path(s.transcript_path).relative_to(ROOT)), language=None)


def render_tool_events(events: list[dict[str, Any]]) -> None:
    """Hiện mọi tool call và kết quả thật, kể cả error dict. Không che lỗi tool."""
    for event in events or []:
        result = event.get("result")
        is_error = isinstance(result, dict) and "error" in result
        icon = TOOL_INFO.get(event.get("tool"), ("🧩", ""))[0]
        args_text = json.dumps(event.get("args", {}), ensure_ascii=False, sort_keys=True)
        label = f"{'🔴' if is_error else icon} {event.get('tool')}({args_text})"
        with st.expander(label, expanded=is_error):
            if is_error:
                st.error(f"{result.get('error')}: {result.get('message', '')}")
            st.code(pretty(result), language="json")


def render_assistant(record: dict[str, Any]) -> None:
    label, color, icon = STATUS_BADGE.get(record["status"], (record["status"], "gray", "•"))
    n_tools = len(record.get("tool_events") or [])
    badge_text = f"{label} · {n_tools} tool" if n_tools else label
    st.badge(badge_text, icon=icon, color=color)
    render_tool_events(record.get("tool_events", []))
    if record["status"] == "provider_error":
        st.error(record.get("error", "provider_error"))
    elif record.get("assistant_text"):
        st.markdown(record["assistant_text"])


def chat_page() -> None:
    init_settings()
    if "transcript" not in st.session_state:
        new_session()
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    render_tool_sidebar()

    head, settings_col, new_col = st.columns([6, 1.6, 1.8], vertical_alignment="center")
    with head:
        st.markdown("<p class='hero-title'>🔎 Research Agent</p>"
                    "<p class='hero-sub'>Tìm tin, đọc URL, xem tweet, tra paper và tổng hợp bản tin bằng tool thật.</p>",
                    unsafe_allow_html=True)
    with settings_col:
        render_settings_popover()
    with new_col:
        if st.button("➕ Cuộc chat mới", width="stretch"):
            new_session()
            st.rerun()

    prompt = st.chat_input("Nhập yêu cầu research…")
    prompt = prompt or st.session_state.pop("pending_prompt", None)

    if not st.session_state.display and not prompt:
        st.markdown(
            "<div class='welcome'>👋 Xin chào! Hãy hỏi agent một câu, hoặc bấm một <b>câu hỏi mẫu</b> bên dưới.<br>"
            "Mọi tool agent gọi và kết quả thật, kể cả lỗi, đều hiện ngay trong câu trả lời. "
            "Agent sẽ <b>hỏi lại</b> khi thiếu thông tin và <b>xin xác nhận</b> trước khi gửi Telegram.</div>",
            unsafe_allow_html=True,
        )

    for record in st.session_state.display:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(record["user"])
        with st.chat_message("assistant", avatar="🔎"):
            render_assistant(record)

    if prompt and prompt.strip():
        prompt = prompt.strip()
        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🔎"):
            with st.spinner("Agent đang chọn tool và gọi API…"):
                record = run_turn(prompt)
            render_assistant(record)
        st.session_state.display.append(record)

    st.markdown("<div class='samples-label'>Câu hỏi mẫu</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for i, question in enumerate(SAMPLE_QUESTIONS):
        cols[i % 3].button(question, key=f"sample_{i}", on_click=queue_question, args=(question,),
                           width="stretch")


# ----------------------------------------------------------------------------
# Trang Eval runs
# ----------------------------------------------------------------------------
def load_runs() -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if not RUNS_DIR.exists():
        return runs
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            st.warning(f"Không đọc được {path.name}: {exc}")
            continue
        data["_path"] = path
        runs.append(data)
    return runs


def is_valid_run(summary: dict[str, Any]) -> bool:
    return summary.get("provider_error_cases", 1) == 0 and summary.get("measured_cases") == summary.get("total_cases")


def pct(value: Any) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def tool_calls_str(calls: list[dict[str, Any]] | None) -> str:
    if not calls:
        return "—"
    return "\n".join(
        f"{c.get('name')}({json.dumps(c.get('args', {}), ensure_ascii=False, sort_keys=True)})" for c in calls
    )


def case_input_text(case: dict[str, Any]) -> str:
    raw = case.get("input")
    if isinstance(raw, list):
        return " ⟶ ".join(m.get("content", "") for m in raw if isinstance(m, dict))
    return str(raw or "")


def eval_page() -> None:
    st.title("📊 Eval runs")
    runs = load_runs()
    if not runs:
        st.info("Chưa có file nào trong `runs/`. Chạy `python run_eval.py --provider openrouter --version v0 "
                "--suite base --eval-cases data/eval_base.json` trước.")
    else:
        st.subheader("Tất cả run")
        overview = []
        for r in runs:
            s = r.get("summary", {})
            overview.append({
                "run_file": r["_path"].name,
                "version": r.get("version"),
                "suite": r.get("suite"),
                "model": r.get("model"),
                "hợp lệ": "✅" if is_valid_run(s) else "❌",
                "case_acc": s.get("case_accuracy"),
                "routing_acc": s.get("tool_routing_accuracy"),
                "arg_acc": s.get("argument_accuracy"),
                "multiturn_acc": s.get("multiturn_accuracy"),
                "passed/total": f"{s.get('passed_cases')}/{s.get('total_cases')}",
                "generated_at": r.get("generated_at"),
            })
        st.dataframe(overview, width="stretch", hide_index=True)

        st.subheader("Chi tiết run")
        names = [r["_path"].name for r in runs]
        chosen = st.selectbox("Chọn run", names, index=0)
        run = next(r for r in runs if r["_path"].name == chosen)
        summary = run.get("summary", {})

        if is_valid_run(summary):
            st.success("Run hợp lệ: provider_error_cases == 0 và measured_cases == total_cases. Dùng được làm bằng chứng.")
        else:
            st.error("Run KHÔNG hợp lệ (có provider error hoặc thiếu case đo). Không dùng làm bằng chứng, hãy chạy lại.")

        meta_cols = st.columns(4)
        meta_cols[0].markdown(f"**Version**\n\n`{run.get('version')}`")
        meta_cols[1].markdown(f"**Suite / phase**\n\n`{run.get('suite')}` / `{run.get('phase')}`")
        meta_cols[2].markdown(f"**Provider / model**\n\n`{run.get('provider')}` / `{run.get('model')}`")
        meta_cols[3].markdown(f"**Generated at**\n\n`{run.get('generated_at')}`")
        st.markdown(f"**artifact_version:** `{run.get('artifact_version')}`")
        with st.expander("prompt_hash / tools_hash đầy đủ"):
            st.code(f"prompt_hash: {run.get('prompt_hash')}\ntools_hash:  {run.get('tools_hash')}", language=None)

        m = st.columns(5)
        m[0].metric("Case accuracy", pct(summary.get("case_accuracy")))
        m[1].metric("Tool routing", pct(summary.get("tool_routing_accuracy")))
        m[2].metric("Argument", pct(summary.get("argument_accuracy")))
        m[3].metric("Multiturn", pct(summary.get("multiturn_accuracy")))
        m[4].metric("Passed / total", f"{summary.get('passed_cases')} / {summary.get('total_cases')}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Failure type của case FAIL**")
            fc = summary.get("failure_counts") or {}
            st.dataframe([{"failure_type": k, "count": v} for k, v in fc.items()] or [{"failure_type": "—", "count": 0}],
                         width="stretch", hide_index=True)
        with c2:
            st.markdown("**Observed mismatch**")
            oc = summary.get("observed_mismatch_counts") or {}
            st.dataframe([{"observed_mismatch": k, "count": v} for k, v in oc.items()]
                         or [{"observed_mismatch": "—", "count": 0}], width="stretch", hide_index=True)

        st.subheader("Từng case")
        only_fail = st.checkbox("Chỉ hiện case FAIL", value=True)
        results = run.get("results", [])
        rows = []
        for case in results:
            res = case.get("result", {})
            if only_fail and res.get("passed"):
                continue
            expect = case.get("expect", {})
            expected = "no_tool" if expect.get("no_tool") else tool_calls_str(expect.get("tool_calls"))
            rows.append({
                "PASS": "✅" if res.get("passed") else "❌",
                "id": case.get("id"),
                "multi": "🔁" if case.get("is_multiturn") else "",
                "input": case_input_text(case),
                "expected": expected,
                "actual": tool_calls_str(res.get("actual_tool_calls")),
                "failure_type": res.get("failure_type") or "",
                "observed_mismatch": res.get("observed_mismatch") or "",
                "failures": " | ".join(res.get("failures") or []),
            })
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.success("Không có case FAIL trong run này.")

        case_ids = [c.get("id") for c in results]
        picked = st.selectbox("Xem chi tiết case", case_ids)
        case = next(c for c in results if c.get("id") == picked)
        res = case.get("result", {})
        st.markdown(
            f"{'✅ PASS' if res.get('passed') else '❌ FAIL'} · **{case.get('id')}** · "
            f"{case.get('metadata', {}).get('what_it_tests', '')}"
        )
        d1, d2 = st.columns(2)
        with d1:
            st.markdown("**Input**")
            st.code(pretty(case.get("input")), language="json")
            st.markdown("**Expected**")
            st.code(pretty(case.get("expect")), language="json")
        with d2:
            st.markdown("**Actual tool calls**")
            st.code(pretty(res.get("actual_tool_calls")), language="json")
            st.markdown("**Chấm**")
            st.code(pretty({k: res.get(k) for k in (
                "routing_correct", "args_correct", "failure_type", "observed_mismatch", "failures", "actual_text")}),
                language="json")
        with st.expander("Tool results thật (kết quả API)"):
            st.code(pretty(case.get("tool_results")), language="json")

    st.subheader("version_log.csv")
    if VERSION_LOG.exists():
        rows = list(csv.DictReader(StringIO(VERSION_LOG.read_text(encoding="utf-8"))))
        if rows:
            st.dataframe(rows, width="stretch", hide_index=True)
        else:
            st.caption("Chưa có dòng version nào.")
    else:
        st.caption("Không tìm thấy artifacts/version_log.csv.")


# ----------------------------------------------------------------------------
# Điều hướng
# ----------------------------------------------------------------------------
nav = st.navigation(
    [
        st.Page(chat_page, title="Chat", icon="💬", url_path="chat", default=True),
        st.Page(eval_page, title="Eval runs", icon="📊", url_path="eval"),
    ],
    position="top",
)
nav.run()
