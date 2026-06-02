"""Load official registries and match entity names from video analysis."""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_DIR = Path(__file__).resolve().parents[1] / "data" / "registries"

_load_lock = threading.Lock()
_loaded = False
_foreign_agents: list[dict] = []
_extremist_orgs: list[dict] = []
_meta: dict = {}


@dataclass(frozen=True)
class RegistryMatch:
    registry: str
    registry_title: str
    matched_name: str
    law: str
    article: str
    source_url: str
    inclusion_date: str | None = None
    excluded: bool = False


def _normalize(text: str) -> str:
    text = (text or "").lower().replace("ё", "е")
    text = re.sub(r"[«»\"'`]", " ", text)
    text = re.sub(r"[^\w\s.@+-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(text: str) -> list[str]:
    return [t for t in _normalize(text).split() if len(t) >= 2]


# Короткие предлоги/союзы дают ложные совпадения («на» в «татьяна»).
_STOP_TOKENS = frozenset(
    {
        "на",
        "и",
        "в",
        "во",
        "не",
        "по",
        "за",
        "от",
        "до",
        "для",
        "из",
        "о",
        "об",
        "the",
        "of",
        "or",
        "and",
    }
)


def _significant_tokens(text: str, *, min_len: int = 3) -> list[str]:
    return [t for t in _tokens(text) if len(t) >= min_len and t not in _STOP_TOKENS]


def _token_match(query_token: str, name_token: str) -> bool:
    if query_token == name_token:
        return True
    short, long = (
        (query_token, name_token)
        if len(query_token) <= len(name_token)
        else (name_token, query_token)
    )
    if len(short) < 4 or short not in long:
        return False
    # «егор» в «егоров» — допустимо; «мир» в «владимировна» — нет.
    return len(short) / len(long) >= 0.75


def _word_boundary_contains(haystack: str, needle: str) -> bool:
    if len(needle) < 5:
        return False
    pat = re.escape(needle)
    return bool(
        re.search(
            rf"(?:^|[^а-яa-zё]){pat}(?:[^а-яa-zё]|$)",
            haystack,
            flags=re.IGNORECASE,
        )
    )


_ORG_NAME_MARKERS = re.compile(
    r"(ооо|ао|пао|нко|фонд|проект|издание|газет|медиа|телекан|"
    r"сми|news|media|org|«|»|\"|\')",
    re.IGNORECASE,
)


def _looks_like_organization(name: str) -> bool:
    if _ORG_NAME_MARKERS.search(name or ""):
        return True
    return len(_significant_tokens(name)) <= 1


def _query_too_ambiguous(query: str) -> bool:
    return len(_significant_tokens(query)) < 2


def is_registry_query_supported(name: str, entity_type: str | None = None) -> bool:
    tokens = _significant_tokens(name)
    if not tokens:
        return False
    etype = (entity_type or "").lower()
    if etype in {"organization", "media", "channel", "организация", "сми"}:
        return len(tokens) >= 2
    # Для физлиц проверяем только полное ФИО (фамилия+имя+отчество).
    return len(tokens) >= 3


# Платформы/бренды — не считаем «возможным иноагентом» по частичному совпадению.
_MEDIA_SKIP = frozenset(
    {
        "more.tv",
        "more tv",
        "kinopoisk",
        "кинопоиск",
        "okko",
        "wink",
        "ivi",
        "premier",
        "start.ru",
        "youtube",
        "vk",
        "rutube",
    }
)


def _should_skip_query(query: str) -> bool:
    q = _normalize(query)
    if not q or len(q) < 3:
        return True
    return q in _MEDIA_SKIP or any(q.startswith(p + " ") or q == p for p in _MEDIA_SKIP)


def _load_registries() -> None:
    global _loaded, _foreign_agents, _extremist_orgs, _meta

    with _load_lock:
        if _loaded:
            return

        meta_path = REGISTRY_DIR / "meta.json"
        if meta_path.exists():
            _meta.update(json.loads(meta_path.read_text(encoding="utf-8")))

        fa_path = REGISTRY_DIR / "foreign_agents.json"
        if fa_path.exists():
            raw = json.loads(fa_path.read_text(encoding="utf-8"))
            _foreign_agents.extend(raw.get("entries", raw) if isinstance(raw, dict) else raw)
            logger.info("Loaded %d foreign-agent registry entries", len(_foreign_agents))
        else:
            logger.warning("Foreign agents registry missing at %s", fa_path)

        ext_path = REGISTRY_DIR / "extremist_orgs.json"
        if ext_path.exists():
            raw = json.loads(ext_path.read_text(encoding="utf-8"))
            _extremist_orgs.extend(raw.get("entries", raw) if isinstance(raw, dict) else raw)
            logger.info("Loaded %d extremist-org registry entries", len(_extremist_orgs))

        _loaded = True


def registry_status() -> dict:
    _load_registries()
    return {
        "loaded": _loaded,
        "foreign_agents": len(_foreign_agents),
        "extremist_orgs": len(_extremist_orgs),
        "meta": _meta,
    }


def _match_full(query: str, entry_name: str) -> bool:
    """Полное совпадение: все части названия из реестра — точные токены в запросе."""
    q_norm = _normalize(query)
    n_norm = _normalize(entry_name)
    if q_norm == n_norm:
        return True

    q_tokens = _significant_tokens(query)
    n_tokens = _significant_tokens(entry_name)
    if len(q_tokens) < 2 or len(n_tokens) < 2:
        return False

    if _looks_like_organization(entry_name):
        return all(any(nt == qt for qt in q_tokens) for nt in n_tokens)
    if len(q_tokens) < 3:
        return False

    return all(any(nt == qt for qt in q_tokens) for nt in n_tokens)


def _members_parts(members: str) -> list[str]:
    text = (members or "").strip().strip("[]")
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;]", text) if part.strip()]


def _entry_match_label(query: str, entry: dict) -> str | None:
    """Return display name if query matches registry row (title or members list)."""
    full_name = (entry.get("fullName") or entry.get("name") or "").strip()
    if not full_name:
        return None

    q_norm = _normalize(query)
    n_norm = _normalize(full_name)
    if _match_full(query, full_name):
        return full_name

    for member in _members_parts(entry.get("members") or ""):
        if _match_full(query, member):
            return f"{full_name} (участник: {member})"
    return None


def _match_organization(query: str, entry_name: str) -> bool:
    q = _normalize(query)
    name = _normalize(entry_name)
    if len(q) < 5:
        return False
    if q == name:
        return True
    return _word_boundary_contains(name, q) or _word_boundary_contains(q, name)


def search_foreign_agent(name: str) -> RegistryMatch | None:
    _load_registries()
    if _should_skip_query(name):
        return None

    query = name.strip()
    if _query_too_ambiguous(query):
        return None

    for entry in _foreign_agents:
        if (entry.get("dateOut") or "").strip():
            continue

        matched_name = _entry_match_label(query, entry)
        if not matched_name:
            continue

        return RegistryMatch(
            registry="foreign_agents",
            registry_title="Реестр иностранных агентов (Минюст РФ)",
            matched_name=matched_name,
            law="255-ФЗ",
            article="ст. 9 — распространение материалов иноагента с маркировкой",
            source_url=_meta.get(
                "foreign_agents_source",
                "https://minjust.gov.ru/ru/pages/reestr-inostryannykh-agentov/",
            ),
            inclusion_date=(entry.get("dateIn") or None),
        )

    return None


def search_extremist_org(name: str) -> RegistryMatch | None:
    _load_registries()
    if _should_skip_query(name):
        return None

    query = name.strip()
    q_norm = _normalize(query)
    if len(q_norm) < 4:
        return None

    for entry in _extremist_orgs:
        org_name = (entry.get("name") or "").strip()
        if not org_name:
            continue
        n_norm = _normalize(org_name)
        if q_norm == n_norm or _match_organization(query, org_name):
            return RegistryMatch(
                registry="extremist_orgs",
                registry_title="Перечень экстремистских организаций (Минюст РФ)",
                matched_name=org_name,
                law="114-ФЗ",
                article="ст. 9 — запрет деятельности экстремистской организации",
                source_url=_meta.get(
                    "extremist_orgs_source",
                    "https://minjust.gov.ru/ru/pages/extremist-organizations/",
                ),
                inclusion_date=entry.get("date_in"),
            )

    return None


def search_entity(name: str, entity_type: str | None = None) -> RegistryMatch | None:
    if not name or not name.strip():
        return None

    etype = (entity_type or "").lower()
    if etype in {"person", "физ", "лицо"}:
        return search_foreign_agent(name) or search_extremist_org(name)

    if etype in {"organization", "media", "channel", "организация", "сми"}:
        hit = search_extremist_org(name) or search_foreign_agent(name)
        return hit

    return search_foreign_agent(name) or search_extremist_org(name)


FOREIGN_AGENT_MARKING_TEMPLATE = (
    "Содержится материал, произведенный и (или) распространенный "
    "иностранным агентом {name}, 18+"
)
