"""Build law-linked compliance summary with registry verification."""

from __future__ import annotations

from app.services.legal_registry import (
    FOREIGN_AGENT_MARKING_TEMPLATE,
    RegistryMatch,
    is_registry_query_supported,
    registry_status,
    search_entity,
)

# Категории риска → пункты ст. 5 436-ФЗ (ч. 2).
RISK_TO_436: dict[str, str] = {
    "profanity": "ст. 5 ч. 2 п. 6 — нецензурная брань",
    "violence": "ст. 5 ч. 2 п. 5 — насилие",
    "sexual_content": "ст. 3 ч. 2 — сексуальные сцены (ограничение по возрасту)",
    "alcohol": "ст. 3 ч. 2 — алкоголь",
    "smoking": "ст. 3 ч. 2 — табак",
    "drugs": "ст. 5 ч. 2 п. 2 — наркотики",
    "weapons": "ст. 3 ч. 2 — оружие",
    "suicide": "ст. 5 ч. 2 п. 1 — склонение к суициду",
    "crime_glorification": "ст. 5 ч. 2 п. 5 — оправдание противоправного поведения",
    "animal_cruelty": "ст. 5 ч. 2 п. 5 — жестокость к животным",
    "excessive_cruelty": "ст. 5 ч. 2 п. 5 — жестокость",
    "illegal_actions": "ст. 5 ч. 2 п. 5 — противоправное поведение",
    "lgbt_propaganda": "ст. 5 ч. 2 п. 4.1 — НТО (436-ФЗ) + КоАП 6.21",
    "pedophilia": "ст. 5 ч. 2 п. 4.4 — педофилия",
    "discreditation_values": "ст. 5 ч. 2 — дискредитация ценностей",
    "propaganda": "ст. 5 ч. 2 — пропаганда",
    "forbidden_symbols": "114-ФЗ — запрещённая символика",
    "foreign_agent": "255-ФЗ ст. 9 — иноагент без маркировки",
}

_CONTENT_436 = {
    "violence",
    "illegal_actions",
    "profanity",
    "alcohol",
    "smoking",
    "sexual_content",
    "drugs",
    "weapons",
    "excessive_cruelty",
    "crime_glorification",
    "animal_cruelty",
    "suicide",
    "lgbt_propaganda",
    "pedophilia",
}


def _has_foreign_agent_marking(markings: list[dict]) -> bool:
    for m in markings or []:
        mtype = (m.get("type") or "").lower()
        text = (m.get("text") or "").lower()
        if mtype == "foreign_agent":
            return True
        if "иноагент" in text or "иностранн" in text and "агент" in text:
            return True
    return False


def _has_age_marking(markings: list[dict]) -> bool:
    for m in markings or []:
        if (m.get("type") or "") == "age_rating":
            return True
        text = (m.get("text") or "").upper()
        if any(x in text for x in ("0+", "6+", "12+", "16+", "18+")):
            return True
    return False


def verify_entities(entities: list[dict], markings: list[dict]) -> list[dict]:
    """Cross-check AI entities against bundled Minjust registries."""
    results: list[dict] = []
    seen: set[str] = set()
    fa_marking = _has_foreign_agent_marking(markings)

    for entity in entities or []:
        name = (entity.get("name") or "").strip()
        if not name:
            continue
        if not is_registry_query_supported(name, entity.get("type")):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        match: RegistryMatch | None = search_entity(name, entity.get("type"))
        row: dict = {
            "name": name,
            "type": entity.get("type"),
            "scene_number": entity.get("scene_number"),
            "context": entity.get("context"),
            "registry": None,
            "registry_status": "not_in_registry",
            "matched_registry_name": None,
            "law": None,
            "article": None,
            "severity": "ok",
            "required_marking": None,
            "marking_found": fa_marking if match and match.registry == "foreign_agents" else None,
        }

        if match:
            row["registry"] = match.registry
            row["registry_status"] = "in_registry"
            row["matched_registry_name"] = match.matched_name
            row["law"] = match.law
            row["article"] = match.article
            row["source_url"] = match.source_url
            if match.registry == "foreign_agents":
                row["required_marking"] = FOREIGN_AGENT_MARKING_TEMPLATE.format(
                    name=match.matched_name
                )
                row["marking_found"] = fa_marking
                row["severity"] = "violation" if not fa_marking else "attention"
            elif match.registry == "extremist_orgs":
                row["severity"] = "violation"
        elif registry_status().get("foreign_agents", 0) == 0:
            row["registry_status"] = "registry_unavailable"

        results.append(row)

    return results


def build_compliance_checks(
    categories: dict[str, int],
    *,
    registry_verifications: list[dict],
    markings: list[dict],
    age: str | None,
) -> list[dict]:
    n_436 = sum(v for k, v in categories.items() if k in _CONTENT_436)
    n_fa_risk = categories.get("foreign_agent", 0)
    n_lgbt = (
        categories.get("lgbt_propaganda", 0)
        + categories.get("gender_change_propaganda", 0)
        + categories.get("childfree_propaganda", 0)
    )
    n_ext = (
        categories.get("forbidden_symbols", 0)
        + categories.get("banned_extremist_org", 0)
        + categories.get("terrorism", 0)
    )

    in_registry = [v for v in registry_verifications if v.get("registry_status") == "in_registry"]
    fa_hits = [v for v in in_registry if v.get("registry") == "foreign_agents"]
    ext_hits = [v for v in in_registry if v.get("registry") == "extremist_orgs"]
    fa_violations = [v for v in fa_hits if v.get("severity") == "violation"]
    ext_violations = [v for v in ext_hits if v.get("severity") == "violation"]

    age_txt = age or "не определён"
    articles_436 = sorted(
        {RISK_TO_436[k] for k in categories if k in RISK_TO_436 and categories[k] > 0}
    )

    checks: list[dict] = [
        {
            "law": "436-ФЗ",
            "title": "Защита детей от вредной информации",
            "status": "attention" if n_436 else "ok",
            "findings_count": n_436,
            "note": (
                f"Рекомендуемый ценз {age_txt}. Выявлено категорий: {n_436}."
                + (
                    " Основания: " + "; ".join(articles_436[:4])
                    + ("…" if len(articles_436) > 4 else "")
                    if articles_436
                    else ""
                )
            ),
            "articles": articles_436[:8],
        },
        {
            "law": "149-ФЗ ст. 10.5",
            "title": "Обязанности аудиовизуального сервиса (маркировка)",
            "status": "ok" if _has_age_marking(markings) else "attention",
            "findings_count": len(markings or []),
            "note": (
                "Возрастная маркировка в кадре обнаружена."
                if _has_age_marking(markings)
                else "Возрастная плашка не обнаружена — проверить обязанности оператора АВ-сервиса."
            ),
            "articles": ["ст. 10.5 — знак информационной продукции / предупреждение"],
        },
        {
            "law": "255-ФЗ",
            "title": "Иностранные агенты (реестр Минюста)",
            "status": (
                "violation"
                if fa_violations
                else "review"
                if fa_hits or n_fa_risk
                else "ok"
            ),
            "findings_count": len(fa_hits) + n_fa_risk,
            "note": (
                f"Сверка с реестром: {len(fa_hits)} совпадений"
                + (
                    f", без маркировки: {len(fa_violations)}"
                    if fa_violations
                    else " (маркировка в кадре есть)"
                    if fa_hits and not fa_violations
                    else ""
                )
                + (
                    f". AI-флагов иноагента: {n_fa_risk}."
                    if n_fa_risk
                    else "."
                )
            ),
            "articles": ["ст. 9 — маркировка материалов иноагента"],
            "registry_source": registry_status().get("meta", {}).get("foreign_agents_source"),
        },
        {
            "law": "КоАП 6.21 / 6.21.2",
            "title": "Пропаганда НТО / смены пола / отказа от деторождения",
            "status": "expertise" if n_lgbt else "ok",
            "findings_count": n_lgbt,
            "note": (
                "Признаков не выявлено."
                if not n_lgbt
                else "Выявлены признаки — требуется лингвистическая экспертиза (не автоматический вердикт)."
            ),
            "articles": ["ст. 6.21 КоАП", "ст. 6.21.2 КоАП (несовершеннолетние)"],
        },
        {
            "law": "114-ФЗ",
            "title": "Противодействие экстремизму",
            "status": (
                "violation"
                if ext_violations
                else "attention"
                if n_ext or ext_hits
                else "ok"
            ),
            "findings_count": n_ext + len(ext_hits),
            "note": (
                "Не выявлено."
                if not n_ext and not ext_hits
                else (
                    f"Символика/риски: {n_ext}. Совпадений с перечнем орг.: {len(ext_hits)}."
                    if ext_hits
                    else f"Признаков в контенте: {n_ext} — проверить федеральный список."
                )
            ),
            "articles": ["ст. 9 — экстремистские организации", "фед. список экстрем. материалов"],
            "registry_source": registry_status().get("meta", {}).get("extremist_orgs_source"),
        },
    ]

    return checks


def enrich_analysis_summary(summary: dict, gemini_result=None) -> dict:
    """Add registry_verifications and law-linked compliance_checks."""
    entities = summary.get("entities") or []
    markings = summary.get("markings_detected") or []
    categories = summary.get("risk_categories") or {}

    registry_verifications = verify_entities(entities, markings)
    summary["registry_verifications"] = registry_verifications

    for entity in entities:
        name = (entity.get("name") or "").strip().lower()
        hit = next(
            (v for v in registry_verifications if (v.get("name") or "").strip().lower() == name),
            None,
        )
        if hit:
            entity["registry"] = hit.get("registry")
            entity["registry_status"] = hit.get("registry_status")
            entity["matched_registry_name"] = hit.get("matched_registry_name")
            entity["law"] = hit.get("law")
            entity["article"] = hit.get("article")
            entity["severity"] = hit.get("severity")

    summary["compliance_checks"] = build_compliance_checks(
        categories,
        registry_verifications=registry_verifications,
        markings=markings,
        age=summary.get("recommended_age_rating"),
    )
    summary["legal_disclaimer"] = (
        "Проверка по открытым реестрам Минюста РФ и категориям 436-ФЗ. "
        "Не является юридическим заключением."
    )
    return summary
