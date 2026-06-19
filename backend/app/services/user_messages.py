"""Sanitize user-visible text — no vendor or model names."""

from __future__ import annotations

import re

_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"google/[\w.-]+", re.I), ""),
    (re.compile(r"gemini[\w.-]*", re.I), "AI"),
    (re.compile(r"\breplicate\b", re.I), "сервис анализа"),
    (re.compile(r"google[\s-]*ai[\s-]*studio", re.I), "AI"),
    (re.compile(r"\bopenai\b|\bgpt-[\w.-]+|\bclaude\b|\banthropic\b|\bcohere\b", re.I), "AI"),
    (re.compile(r"block_reason=\S+", re.I), ""),
    (re.compile(r"blocked the input", re.I), "не удалось обработать автоматически"),
    (re.compile(r"контент отклонён моделью[^.]*", re.I), "требуется ручной просмотр"),
)

CONTENT_BLOCKED_USER_REASON = (
    "Не удалось обработать этот фрагмент автоматически — требуется ручной просмотр."
)


def sanitize_user_text(text: str | None) -> str | None:
    if not text:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = pattern.sub(repl, out)
    out = re.sub(r"\s{2,}", " ", out).strip(" .—–-")
    return out or None


def sanitize_user_error(error: str | Exception) -> str:
    msg = sanitize_user_text(str(error)) or "Произошла ошибка анализа."
    return msg[:2000]
