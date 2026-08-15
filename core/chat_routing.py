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

# 定义/科普类问题即使已确认病例也走通用医学回答，避免把患者上下文强加给概念解释
DEFINITION_TERMS = (
    "什么是", "是什么意思", "是什么", "是指", "定义", "解释一下", "科普", "介绍一下",
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


def select_llm_attachments(attachments: list[dict[str, Any]] | None, route: ChatRoute) -> list[dict[str, Any]]:
    items = [item for item in (attachments or []) if isinstance(item, dict)]
    if route.use_case_context or any(item.get("type") == "image" for item in items):
        return items
    return []


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

    # 选择患者后的轻量摘要：只带病例上下文，不触发相似病例/文献检索
    if mode == "initial_patient_brief" and has_confirmed_case:
        return ChatRoute(True, False, "initial_patient_brief", False)

    explicit_retrieval = any(term.lower() in q.lower() for term in EXPLICIT_RETRIEVAL_TERMS)
    if explicit_retrieval and has_confirmed_case:
        return ChatRoute(True, True, "explicit_retrieval", True)

    is_medical = any(term.lower() in q.lower() for term in MEDICAL_TERMS)
    is_definition = any(term in q for term in DEFINITION_TERMS)
    case_reference = any(term in q for term in CASE_REFERENCE_TERMS)

    # 已确认病例后，医学问题（含“TNM 呢？”这类短追问）默认携带病例上下文；
    # 检索行为仍由显式检索词单独触发，概念定义类问题走通用医学回答。
    if has_confirmed_case and (case_reference or (is_medical and not is_definition)):
        return ChatRoute(True, False, "case_followup", True)

    if is_medical:
        return ChatRoute(False, False, "general_medical", True)

    return ChatRoute(False, False, "general", False)
