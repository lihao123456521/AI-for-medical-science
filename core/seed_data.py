from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


CASE_FIELDS = (
    "sheet", "diagnosis", "sex", "age", "history", "prior_operation", "symptoms", "tumor",
    "grade", "tnm", "lymph_node", "ls", "immuno", "imaging", "pathology", "surgery",
    "other_treatment", "recurrence", "followup", "remarks", "imaging_findings", "tags",
)
ARTICLE_FIELDS = (
    "title", "authors", "journal", "year", "doi", "source_url", "keywords", "abstract", "content", "notes",
)

IDENTITY_LINE_RE = re.compile(
    r"(?im)^.*?(?:姓名|患者姓名|住院号|病案号|身份证号|身份证|联系电话|手机号|家庭住址|地址)\s*[：:]\s*[^\r\n]*$"
)
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\s，。；;]+\\)*[^\s，。；;]*")
API_KEY_RE = re.compile(r"\b(?:sk|sk-proj|sk-ant|key)-[A-Za-z0-9_-]{12,}\b", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
LABELED_ID_RE = re.compile(r"(?:住院号|病案号|身份证号|身份证|影像号|检查号|门诊号)\s*[：:]?\s*[A-Za-z0-9-]{5,}", re.I)
EXACT_DATE_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})[-/.年](?:0?[1-9]|1[0-2])[-/.月](?:0?[1-9]|[12]\d|3[01])日?(?!\d)")


def _sanitize_text(value: Any, identity_values: list[str] | None = None) -> str:
    text = str(value or "")
    for identity in identity_values or []:
        if identity:
            text = text.replace(identity, "[已脱敏]")
    text = IDENTITY_LINE_RE.sub("[身份信息已脱敏]", text)
    text = LABELED_ID_RE.sub("[身份编号已脱敏]", text)
    text = WINDOWS_PATH_RE.sub("[本机路径已移除]", text)
    text = API_KEY_RE.sub("[API密钥已移除]", text)
    text = EMAIL_RE.sub("[邮箱已脱敏]", text)
    text = PHONE_RE.sub("[电话已脱敏]", text)
    text = EXACT_DATE_RE.sub(lambda m: f"{m.group(1)}年", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _sanitize_value(value: Any, identity_values: list[str] | None = None) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value, identity_values)
    if isinstance(value, list):
        return [_sanitize_value(item, identity_values) for item in value]
    if isinstance(value, dict):
        allowed = {"text", "date", "source_page", "annotation", "physician_annotation"}
        return {key: _sanitize_value(item, identity_values) for key, item in value.items() if key in allowed}
    return value


def _public_case(row: dict[str, Any], index: int) -> dict[str, Any]:
    identities = [str(row.get("patient_name") or "").strip()]
    result: dict[str, Any] = {"case_id": f"SEED-CASE-{index:03d}"}
    for key in CASE_FIELDS:
        if key not in row:
            continue
        value = _sanitize_value(row.get(key), identities)
        if value not in (None, "", [], {}):
            result[key] = value
    result["medical_images"] = []
    return result


def _public_article(row: dict[str, Any], index: int) -> dict[str, Any]:
    result: dict[str, Any] = {"article_id": f"SEED-ARTICLE-{index:03d}"}
    for key in ARTICLE_FIELDS:
        if key not in row:
            continue
        value = _sanitize_value(row.get(key))
        if key == "source_url" and value and not str(value).lower().startswith(("http://", "https://")):
            continue
        if value not in (None, "", [], {}):
            result[key] = value
    return result


def build_seed_payload(cases: list[dict[str, Any]], articles: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": [_public_case(row, index) for index, row in enumerate(cases, 1) if isinstance(row, dict)],
        "articles": [_public_article(row, index) for index, row in enumerate(articles, 1) if isinstance(row, dict)],
    }


def audit_seed_payload(payload: Any) -> list[str]:
    findings: list[str] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            forbidden_fields = {"patient_name", "source_document", "source_hash", "source_import_key", "stored_as", "source_file", "api_key"}
            for key, item in value.items():
                if key in forbidden_fields:
                    findings.append(f"identity-field:{path}.{key}")
                visit(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
        elif isinstance(value, str):
            checks = (
                ("identity", re.compile(r"(?:姓名|住院号|病案号|身份证号|影像号|检查号|门诊号|联系电话|家庭住址)\s*[：:]\s*(?!\[)[^\r\n]+")),
                ("secret", API_KEY_RE),
                ("windows-path", WINDOWS_PATH_RE),
                ("email", EMAIL_RE),
                ("phone", PHONE_RE),
                ("upload-reference", re.compile(r"/uploads/|\\uploads\\", re.I)),
            )
            for label, pattern in checks:
                if pattern.search(value):
                    findings.append(f"{label}:{path}")

    visit(payload, "$" )
    return sorted(set(findings))


def initialize_runtime_from_seed(runtime_dir: Path | str, seed_dir: Path | str) -> dict[str, Any]:
    runtime = Path(runtime_dir)
    seed = Path(seed_dir)
    runtime.mkdir(parents=True, exist_ok=True)
    case_target = runtime / "user_cases.json"
    article_target = runtime / "articles.json"

    def read_list(path: Path) -> list[Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except Exception:
            return []

    if read_list(case_target) or read_list(article_target):
        return {"initialized": False, "reason": "runtime-not-empty"}
    case_seed = read_list(seed / "user_cases.json")
    article_seed = read_list(seed / "articles.json")
    if not case_seed and not article_seed:
        return {"initialized": False, "reason": "seed-missing"}
    case_target.write_text(json.dumps(case_seed, ensure_ascii=False, indent=2), encoding="utf-8")
    article_target.write_text(json.dumps(article_seed, ensure_ascii=False, indent=2), encoding="utf-8")
    migration_path = runtime / "migration_state.json"
    migration_path.write_text(json.dumps({
        "public_seed_initialized_at": datetime.now().isoformat(timespec="seconds"),
        "public_seed_case_count": len(case_seed),
        "public_seed_article_count": len(article_seed),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"initialized": True, "case_count": len(case_seed), "article_count": len(article_seed)}
