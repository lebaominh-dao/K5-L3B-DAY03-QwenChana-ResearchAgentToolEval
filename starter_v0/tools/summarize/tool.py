from __future__ import annotations

from typing import Any

from tools._shared import err, terms


VALID_MODES = {"highlights", "by_date", "dedupe", "score"}


def _clean_limit(limit: Any) -> int:
    if isinstance(limit, bool):
        raise ValueError(f"limit must be an integer, got {limit!r}")
    try:
        value = int(str(limit).strip())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"limit must be an integer, got {limit!r}") from exc
    return max(1, min(20, value))


def _score_item(item: dict[str, Any], query_terms: set[str]) -> int:
    text = " ".join([
        str(item.get("title") or ""),
        str(item.get("summary") or ""),
    ])
    return len(query_terms & terms(text))


def summarize(
    items: list[dict[str, Any]] | None = None,
    mode: str = "highlights",
    query: str = "",
    limit: int = 5,
) -> dict[str, Any]:
    """Filter, rank, and deduplicate a list of items produced by other tools.

    No network calls are made. Never raises: invalid input and other errors
    return ``{"tool": "summarize", "error": ..., "message": ...}``.
    """
    try:
        if mode is None or (isinstance(mode, str) and not mode.strip()):
            raise ValueError(
                f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}"
            )
        mode = str(mode).strip().lower()
        if mode not in VALID_MODES:
            raise ValueError(
                f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}"
            )
        limit = _clean_limit(limit)
        safe_items = [i for i in (items or []) if isinstance(i, dict)]

        if mode == "highlights":
            result = sorted(
                safe_items,
                key=lambda i: float(i.get("score") or 0),
                reverse=True,
            )[:limit]

        elif mode == "by_date":
            def _date_key(item: dict[str, Any]) -> str:
                return str(item.get("date") or item.get("published") or "")
            result = sorted(safe_items, key=_date_key, reverse=True)[:limit]

        elif mode == "dedupe":
            seen: set[str] = set()
            result = []
            for item in safe_items:
                src = str(item.get("source") or "")
                if src not in seen:
                    seen.add(src)
                    result.append(item)
                    if len(result) >= limit:
                        break

        else:  # mode == "score"
            query_terms = terms(query or "")
            result = sorted(
                safe_items,
                key=lambda i: _score_item(i, query_terms),
                reverse=True,
            )[:limit]

        out: dict[str, Any] = {
            "tool": "summarize",
            "mode": mode,
            "input_count": len(safe_items),
            "output_count": len(result),
            "items": result,
        }
        if mode == "score":
            out["query"] = query or ""
        return out

    except Exception as exc:
        return err("summarize", exc)
