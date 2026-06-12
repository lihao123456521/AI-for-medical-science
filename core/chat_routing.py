from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EXPLICIT_RETRIEVAL_TERMS = (
    "相似病例", "检索病例", "查找病例", "比较病例", "病例对照",
    "参考文献", "检索文献", "查找文献", "文献证据", "查指南", "证据依据",
)
MEDICAL_TERMS = (
    "疾病", "诊断", "治疗", "手术", "药物", "检查", "影像", "病理", "肿瘤", "癌",
    "尿道", "膀胱", "阴茎", "淋巴结", "复发", "转移", "随访", "症状", "医学", "患者",
    "SCC", "TNM", "CT", "MRI",
)

CASE_REFERENCE_TERMS = (
    "这个患者",
    "该患者",
    "当前患者",
    "这个病例",
    "该病例",
    "当前病例",
    "上述病例",
    "这位患者",
    "他的病",
    "她的病",
)
CASE_DETAIL_KEYS = (
    "age",
    "sex",
    "diagnosis",
    "history",
    "symptoms",
    "tumor",
    "imaging",
    "pathology",
    "tnm",
    "grade",
    "lymph_node",
    "surgery",
)
CASE_TEXT_MARKERS = (
    "年龄",
    "性别",
    "诊断",
    "病史",
    "症状",
    "影像",
    "CT",
    "MRI",
    "病理",
    "TNM",
    "淋巴结",
    "手术史",
)


@dataclass(frozen=True)
class ChatRoute:
    use_case_context: bool
    retrieve_evidence: bool
    mode: str
    use_article_context: bool = False


def has_detailed_case(patient: dict[str, Any] | None) -> bool:
    values = patient if isinstance(patient, dict) else {}
    structured_count = sum(bool(str(values.get(key) or "").strip()) for key in CASE_DETAIL_KEYS)
    if structured_count >= 3:
        return True
    free_text = str(values.get("free_text") or "").strip()
    marker_count = sum(marker.lower() in free_text.lower() for marker in CASE_TEXT_MARKERS)
    return len(free_text) >= 80 and marker_count >= 3


def classify_chat_request(
    question: str,
    has_confirmed_case: bool,
    mode: str = "",
) -> ChatRoute:
    q = str(question or "").strip()
    if mode == "initial_patient_analysis" and has_confirmed_case:
        return ChatRoute(True, True, "initial_patient_analysis", True)

    explicit_retrieval = any(term.lower() in q.lower() for term in EXPLICIT_RETRIEVAL_TERMS)
    if explicit_retrieval and has_confirmed_case:
        return ChatRoute(True, True, "explicit_retrieval", True)

    case_reference = any(term in q for term in CASE_REFERENCE_TERMS)
    if case_reference and has_confirmed_case:
        return ChatRoute(True, False, "case_followup", True)

    if any(term.lower() in q.lower() for term in MEDICAL_TERMS):
        return ChatRoute(False, False, "general_medical", True)

    return ChatRoute(False, False, "general", False)
