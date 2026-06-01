from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re

from .data_loader import CaseRecord, KnowledgeBase


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _contains(text: str, *words: str) -> bool:
    lower = text.lower()
    return any(w.lower() in lower for w in words if w)


def _add_feature(features: List[Dict[str, Any]], name: str, weight: int, evidence: str) -> int:
    features.append({"name": name, "weight": weight, "evidence": evidence})
    return weight


def compose_patient_text(patient: Dict[str, Any]) -> str:
    preferred = [
        "sex", "age", "history", "prior_operation", "symptoms", "tumor", "tumor_location",
        "ls", "grade", "tnm", "lymph_node", "imaging", "pathology", "immuno", "free_text"
    ]
    return "\n".join([f"{k}: {_text(patient.get(k))}" for k in preferred if _text(patient.get(k))])


def score_patient(patient: Dict[str, Any]) -> Dict[str, Any]:
    """Transparent screening score for teaching/research demonstration.

    This is not a validated clinical prediction model. It is designed to make the
    evidence chain visible for a prototype presentation.
    """
    features: List[Dict[str, Any]] = []
    score = 0

    all_text = compose_patient_text(patient)
    history = _text(patient.get("history")) + " " + _text(patient.get("free_text"))
    symptoms = _text(patient.get("symptoms")) + " " + _text(patient.get("free_text"))
    tumor = _text(patient.get("tumor")) + " " + _text(patient.get("tumor_location"))
    pathology = _text(patient.get("pathology")) + " " + _text(patient.get("immuno"))
    imaging = _text(patient.get("imaging"))
    tnm = _text(patient.get("tnm"))
    grade = _text(patient.get("grade"))
    lymph = _text(patient.get("lymph_node"))
    ls = _text(patient.get("ls"))

    try:
        age = float(patient.get("age") or 0)
    except Exception:
        age = 0
    if age >= 60:
        score += _add_feature(features, "年龄 ≥60 岁", 7, f"年龄={age:.0f}")
    elif age >= 50:
        score += _add_feature(features, "年龄 50–59 岁", 4, f"年龄={age:.0f}")

    if _contains(_text(patient.get("sex")), "男", "male"):
        score += _add_feature(features, "男性尿道肿瘤目标人群", 3, _text(patient.get("sex")))

    if _contains(ls + " " + all_text, "硬化性苔藓", "lichen sclerosus", "ls"):
        score += _add_feature(features, "LS / 硬化性苔藓相关线索", 18, ls or "文本中出现 LS 相关描述")

    if _contains(history, "尿道狭窄", "狭窄"):
        score += _add_feature(features, "长期尿道狭窄病史", 12, history[:120])
    if _contains(history + " " + _text(patient.get("prior_operation")), "尿道重建", "尿道成形", "尿道扩张", "包皮环切", "术后"):
        score += _add_feature(features, "既往尿道操作/重建/包皮环切史", 10, (history + " " + _text(patient.get("prior_operation")))[:120])

    if _contains(symptoms, "排尿困难", "无法排尿", "尿潴留"):
        score += _add_feature(features, "进行性排尿困难或尿潴留", 8, symptoms[:120])
    if _contains(symptoms + " " + tumor, "肿物", "肿块", "新生物", "赘生物", "包块", "占位", "结节"):
        score += _add_feature(features, "尿道/会阴/阴茎部肿物线索", 13, (symptoms + " " + tumor)[:120])
    if _contains(symptoms, "血尿", "出血"):
        score += _add_feature(features, "血尿/出血", 6, symptoms[:120])
    if _contains(symptoms, "疼痛", "溃疡", "感染", "脓", "瘘"):
        score += _add_feature(features, "疼痛、溃疡、感染或瘘道表现", 5, symptoms[:120])

    if _contains(tumor, "球部", "阴茎部", "前尿道", "近端尿道", "远端尿道"):
        score += _add_feature(features, "尿道关键部位受累", 6, tumor[:120])
    if _contains(imaging + " " + tumor, "浸润", "阻塞", "完全阻塞", "周围软组织", "粘连", "壁增厚", "软组织结节"):
        score += _add_feature(features, "影像/描述提示浸润或阻塞", 12, (imaging + " " + tumor)[:160])
    if _contains(imaging + " " + lymph, "淋巴结", "腹股沟", "腹膜后"):
        score += _add_feature(features, "淋巴结异常线索", 10, (imaging + " " + lymph)[:160])

    if _contains(pathology, "鳞癌", "scc", "squamous", "鳞状细胞癌"):
        score += _add_feature(features, "病理/免疫提示鳞状细胞癌", 25, pathology[:160])
    elif _contains(pathology, "异型增生", "原位癌", "高级别", "重度"):
        score += _add_feature(features, "癌前病变/高级别异型增生线索", 18, pathology[:160])
    if _contains(pathology, "p63", "ck5/6", "p40"):
        score += _add_feature(features, "鳞状分化免疫标志物线索", 7, pathology[:160])
    if _contains(pathology, "ki-67", "ki67"):
        score += _add_feature(features, "Ki-67 增殖指数记录", 4, pathology[:160])

    if _contains(tnm, "t3", "t4"):
        score += _add_feature(features, "T3/T4 局部进展线索", 8, tnm)
    if _contains(tnm + " " + lymph, "n1", "n2", "n3", "淋巴结转移"):
        score += _add_feature(features, "N+ 或明确淋巴结转移", 8, (tnm + " " + lymph).strip())
    if _contains(tnm, "m1"):
        score += _add_feature(features, "M1 远处转移线索", 8, tnm)
    if _contains(grade, "g3", "iii", "3", "低分化"):
        score += _add_feature(features, "高级别/低分化", 8, grade)

    score = max(0, min(100, score))
    if score >= 75:
        level = "高风险"
        interpretation = "存在多项 SCC 或 LS 恶变连续谱相关高危线索，适合进入专科复核、补充证据和病例讨论流程。"
    elif score >= 45:
        level = "中风险"
        interpretation = "存在部分高危线索，建议补全病理、影像、尿道镜/活检等证据后复核。"
    else:
        level = "低-中风险"
        interpretation = "当前输入中的高危线索有限，但不能排除早期病变；如症状持续或影像/病理异常，应继续随访和复核。"

    missing = []
    for key, name in [
        ("ls", "LS/硬化性苔藓状态"), ("pathology", "病理或活检结果"),
        ("imaging", "影像/尿道镜描述"), ("tnm", "TNM 或局部进展信息"),
        ("lymph_node", "淋巴结评估"),
    ]:
        if not _text(patient.get(key)):
            missing.append(name)

    return {
        "score": score,
        "level": level,
        "interpretation": interpretation,
        "features": sorted(features, key=lambda x: x["weight"], reverse=True),
        "missing_items": missing,
        "safety_note": "本结果为教学/科研原型的风险提示，不构成诊断、分期或治疗方案。",
    }


def _char_ngrams(text: str, n: int = 2) -> set[str]:
    text = re.sub(r"\s+", "", text.lower())
    if not text:
        return set()
    if len(text) <= n:
        return {text}
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def _keyword_bonus(query: str, record: CaseRecord) -> float:
    bonus = 0.0
    text = record.searchable_text.lower()
    for kw, weight in [
        ("硬化性苔藓", 0.08), ("ls", 0.04), ("尿道狭窄", 0.06),
        ("鳞癌", 0.10), ("scc", 0.10), ("鳞状细胞癌", 0.10),
        ("肿块", 0.04), ("肿物", 0.04), ("占位", 0.03),
        ("排尿困难", 0.04), ("球部", 0.03), ("阴茎部", 0.03),
        ("淋巴结", 0.05), ("复发", 0.04), ("转移", 0.04),
    ]:
        if kw.lower() in query.lower() and kw.lower() in text:
            bonus += weight
    if record.sheet == "USCC":
        bonus += 0.06
    return bonus



def _similarity_percent(value: float) -> str:
    try:
        pct = float(value) * 100.0 if float(value) <= 1.5 else float(value)
        pct = max(0.0, min(100.0, pct))
        return f"{pct:.0f}%"
    except Exception:
        return "未计算"

def find_similar_cases(kb: KnowledgeBase, patient: Dict[str, Any], top_n: int = 4) -> List[Dict[str, Any]]:
    query = compose_patient_text(patient)
    qgrams = _char_ngrams(query)
    scored: List[Tuple[float, CaseRecord]] = []
    for record in kb.records:
        rgrams = _char_ngrams(record.searchable_text)
        union = len(qgrams | rgrams)
        base = len(qgrams & rgrams) / union if union else 0.0
        score = base + _keyword_bonus(query, record)
        scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[Dict[str, Any]] = []
    if not scored:
        return results
    best = scored[0][0]
    # v19: 医生反馈“至少两个、至多四个”，但仍不机械凑满四个。
    # 做法：先取与最佳结果接近的病例；若不足 2 个，则补入排序最高的病例供人工对照。
    threshold = max(0.10, best * 0.58)
    for sim, rec in scored:
        if len(results) >= top_n:
            break
        if sim < threshold and len(results) >= 2:
            continue
        payload = rec.as_public_dict()
        payload["similarity"] = round(float(sim), 3)
        payload["similarity_percent"] = _similarity_percent(sim)
        payload["evidence_summary"] = _evidence_summary(rec)
        results.append(payload)
    # 若数据库中可用病例足够而高相关结果少于 2 个，补足 2 个，避免医生看不到对照材料。
    if len(results) < min(2, len(scored)):
        used = {r.get("case_id") for r in results}
        for sim, rec in scored:
            if len(results) >= min(2, top_n):
                break
            if rec.case_id in used:
                continue
            payload = rec.as_public_dict()
            payload["similarity"] = round(float(sim), 3)
            payload["similarity_percent"] = _similarity_percent(sim)
            payload["evidence_summary"] = _evidence_summary(rec)
            results.append(payload)
    return results[:top_n]


def _evidence_summary(rec: CaseRecord) -> List[str]:
    items: List[str] = []
    for label, value in [
        ("诊断", rec.diagnosis), ("病史", rec.history), ("症状", rec.symptoms),
        ("肿瘤", rec.tumor), ("LS", rec.ls), ("病理", rec.pathology),
        ("手术", rec.surgery), ("其他治疗", rec.other_treatment),
        ("影像", rec.imaging), ("复发/转移", rec.recurrence), ("随访", rec.followup),
    ]:
        if value:
            items.append(f"{label}: {value[:120]}")
    return items[:5]



def summarize_treatment_outcomes(similar_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize surgery/medication/follow-up information from the top similar cases.

    It is deliberately descriptive: the system compares existing records and produces
    options for clinician discussion rather than a directive plan.
    """
    rows = []
    surgery_count = 0
    other_count = 0
    recurrence_count = 0
    no_recurrence_count = 0
    for case in similar_cases[:4]:
        surgery = _text(case.get("surgery"))
        other = _text(case.get("other_treatment"))
        recurrence = _text(case.get("recurrence"))
        followup = _text(case.get("followup"))
        if surgery:
            surgery_count += 1
        if other:
            other_count += 1
        if _contains(recurrence + " " + followup, "复发", "转移", "死亡", "进展"):
            recurrence_count += 1
        elif recurrence or followup:
            no_recurrence_count += 1
        rows.append({
            "case_id": case.get("case_id"),
            "diagnosis": case.get("diagnosis"),
            "surgery": surgery or "未记录",
            "other_treatment": other or "未记录",
            "recurrence": recurrence or "未记录",
            "followup": followup or "未记录",
        })

    discussion_points = []
    if surgery_count:
        discussion_points.append("相似病例中已有手术治疗记录，优先对照肿瘤位置、T/N/M分期、淋巴结状态和既往尿道重建史讨论局部切除、尿道切除/重建、阴茎部分/全切或更广泛手术的适配性。")
    if other_count:
        discussion_points.append("相似病例中存在非手术治疗记录，可结合病理分化、切缘、淋巴结/远处转移和复发状态讨论放疗、化疗或综合治疗的角色。")
    if recurrence_count:
        discussion_points.append("相似病例中出现复发/转移/进展记录，病例讨论时应重点核对淋巴结评估、切缘、局部浸润范围和随访计划。")
    if not discussion_points:
        discussion_points.append("相似病例的治疗与随访记录不充分，建议先补充病理、分期、影像、淋巴结和既往治疗信息，再比较治疗路径。")

    return {
        "similar_case_treatment_rows": rows,
        "counts": {
            "with_surgery_record": surgery_count,
            "with_other_treatment_record": other_count,
            "with_progression_record": recurrence_count,
            "with_followup_without_progression_keyword": no_recurrence_count,
        },
        "discussion_points": discussion_points,
    }

def format_report_text(report: Dict[str, Any]) -> str:
    lines: List[str] = [
        "病例讨论摘要",
        "",
        "一、相似病例",
    ]
    cases = report.get("similar_cases", [])[:4]
    if cases:
        for i, case in enumerate(cases, 1):
            lines.append(f"{i}. {case.get('case_id')}｜{case.get('sheet')}｜相似度 {case.get('similarity_percent') or case.get('similarity')}｜{case.get('diagnosis', '诊断未记录')}")
            for ev in (case.get("evidence_summary") or [])[:3]:
                lines.append(f"   - {ev}")
    else:
        lines.append("暂无相似病例。")

    missing = (report.get("risk") or {}).get("missing_items") or []
    lines.extend(["", "二、可补充资料"])
    lines.append("、".join(missing) if missing else "当前核心字段已基本填写。")
    return "\n".join(lines)


def generate_traceable_report(kb: KnowledgeBase, patient: Dict[str, Any], top_n: int = 4) -> Dict[str, Any]:
    score = score_patient(patient)
    similar_cases = find_similar_cases(kb, patient, top_n=top_n)
    report = {
        "risk": score,  # 后端保留供内部排序/缺失项识别，前端默认不展示评分。
        "similar_cases": similar_cases,
        "treatment_outcomes": summarize_treatment_outcomes(similar_cases),
        "decision_support": [
            "补全文本病史、尿道镜/影像描述、病理与免疫组化结果。",
            "对照相似病例的 LS、尿道狭窄、肿物位置、病理分化和淋巴结状态。",
            "将新增病例通过“添加病例”或“投喂进入数据库”写入本地知识库，以便后续检索。",
        ],
    }
    report["report_text"] = format_report_text(report)
    return report
