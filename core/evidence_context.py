from __future__ import annotations

from typing import Any, Callable

from .chat_routing import ChatRoute


def build_evidence_report(
    *,
    route: ChatRoute,
    question: str,
    patient: dict[str, Any],
    attachments: list[dict[str, Any]],
    generate_case_report: Callable[..., dict[str, Any]],
    search_articles: Callable[..., list[dict[str, Any]]],
    find_candidates: Callable[..., list[dict[str, Any]]],
    knowledge_digest: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    if route.retrieve_evidence:
        report = generate_case_report(patient, top_n=4)
        article_query = " ".join([
            question,
            str(patient.get("free_text") or ""),
            str(patient.get("diagnosis") or ""),
            str(patient.get("pathology") or ""),
            str(patient.get("surgery") or ""),
        ])
        candidate_query = " ".join([
            question,
            str(patient.get("free_text") or ""),
            str(patient.get("age") or ""),
            str(patient.get("sex") or ""),
            str(patient.get("diagnosis") or ""),
        ])
        report["related_articles"] = search_articles(article_query, limit=4)
        report["candidate_matches"] = find_candidates(attachments, candidate_query, limit=4)
        report["knowledge_digest"] = knowledge_digest()
        report["display_evidence_cards"] = True
        return report

    related_articles = search_articles(question, limit=4) if route.use_article_context else []
    return {
        "similar_cases": [],
        "related_articles": related_articles,
        "candidate_matches": [],
        "treatment_outcomes": {},
        "risk": {"missing_items": []},
        "answer_mode": route.mode,
        "knowledge_digest": knowledge_digest() if route.use_article_context or route.use_case_context else {},
        "display_evidence_cards": False,
    }
