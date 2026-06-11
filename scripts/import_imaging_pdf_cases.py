from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from core.case_document import CaseSegment, extract_pdf_case_segments


SOURCE_DOCUMENT = "影像片子汇总.pdf"
SOURCE_GROUP = "影像片子汇总"
BACKUP_FILES = (
    "user_cases.json",
    "articles.json",
    "deleted_cases.json",
    "case_tags.json",
    "library_state.json",
    "storage_manifest.json",
)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_storage_backup(data_dir: Path, timestamp: str | None = None) -> Path:
    stamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    target = data_dir / "backups" / f"{stamp}-imaging-import"
    target.mkdir(parents=True, exist_ok=False)
    for name in BACKUP_FILES:
        source = data_dir / name
        if source.exists():
            shutil.copy2(source, target / name)
    return target


def _next_user_number(rows: list[dict[str, Any]]) -> int:
    numbers: list[int] = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if not case_id.startswith("USER-"):
            continue
        try:
            numbers.append(int(case_id.split("-", 1)[1]))
        except ValueError:
            continue
    return max(numbers, default=0) + 1


def _normalize_import_row(row: dict[str, Any], case_id: str, source_hash: str) -> dict[str, Any]:
    number = int(row["source_case_number"])
    now = datetime.now().isoformat(timespec="seconds")
    medical_images = [dict(item) for item in (row.get("medical_images") or []) if isinstance(item, dict)]
    return {
        "case_id": case_id,
        "sheet": str(row.get("sheet") or SOURCE_GROUP),
        "diagnosis": str(row.get("diagnosis") or f"影像资料病例（原编号 {number}）"),
        "sex": str(row.get("sex") or ""),
        "age": row.get("age") if row.get("age") not in {"", None} else "",
        "history": str(row.get("history") or ""),
        "prior_operation": str(row.get("prior_operation") or ""),
        "symptoms": str(row.get("symptoms") or ""),
        "tumor": str(row.get("tumor") or ""),
        "grade": str(row.get("grade") or ""),
        "tnm": str(row.get("tnm") or ""),
        "lymph_node": str(row.get("lymph_node") or ""),
        "ls": str(row.get("ls") or ""),
        "immuno": str(row.get("immuno") or ""),
        "imaging": str(row.get("imaging") or ""),
        "pathology": str(row.get("pathology") or ""),
        "surgery": str(row.get("surgery") or ""),
        "other_treatment": str(row.get("other_treatment") or ""),
        "recurrence": str(row.get("recurrence") or ""),
        "followup": str(row.get("followup") or ""),
        "remarks": str(row.get("remarks") or "来源于医生提供的影像汇总 PDF；影像所见与标注需由临床医生结合原片复核。"),
        "source_row": number,
        "medical_images": medical_images,
        "patient_name": str(row.get("patient_name") or ""),
        "source_case_number": number,
        "source_document": str(row.get("source_document") or SOURCE_DOCUMENT),
        "source_pages": [int(page) for page in (row.get("source_pages") or [])],
        "source_hash": source_hash,
        "source_import_key": f"{source_hash}:{number}",
        "imaging_findings": [dict(item) for item in (row.get("imaging_findings") or []) if isinstance(item, dict)],
        "case_signature": "",
        "tags": [SOURCE_GROUP],
        "persisted_at": now,
    }


def import_segments(data_dir: Path, case_rows: list[dict[str, Any]], source_hash: str) -> dict[str, Any]:
    data_dir = Path(data_dir)
    user_cases_path = data_dir / "user_cases.json"
    articles_path = data_dir / "articles.json"
    existing = _read_json(user_cases_path, [])
    if not isinstance(existing, list):
        raise RuntimeError("user_cases.json is not a JSON list")
    articles = _read_json(articles_path, [])
    if not isinstance(articles, list):
        raise RuntimeError("articles.json is not a JSON list")

    before = len(existing)
    known_keys = {str(row.get("source_import_key") or "") for row in existing if isinstance(row, dict)}
    next_number = _next_user_number([row for row in existing if isinstance(row, dict)])
    added_rows: list[dict[str, Any]] = []
    for row in sorted(case_rows, key=lambda item: int(item["source_case_number"])):
        import_key = f"{source_hash}:{int(row['source_case_number'])}"
        if import_key in known_keys:
            continue
        normalized = _normalize_import_row(row, f"USER-{next_number:03d}", source_hash)
        existing.append(normalized)
        added_rows.append(normalized)
        known_keys.add(import_key)
        next_number += 1

    if added_rows:
        _atomic_write_json(user_cases_path, existing)

    deleted_ids = _read_json(data_dir / "deleted_cases.json", [])
    state = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "user_cases": existing,
        "articles": articles,
        "deleted_case_ids": deleted_ids if isinstance(deleted_ids, list) else [],
    }
    _atomic_write_json(data_dir / "library_state.json", state)
    _atomic_write_json(
        data_dir / "storage_manifest.json",
        {
            "updated_at": state["updated_at"],
            "storage_version": "v37",
            "data_dir": str(data_dir),
            "user_cases_path": str(user_cases_path),
            "user_case_count": len(existing),
            "articles_path": str(articles_path),
            "article_count": len(articles),
            "deleted_cases_path": str(data_dir / "deleted_cases.json"),
            "uploads_path": str(data_dir / "uploads"),
        },
    )
    return {
        "before_case_count": before,
        "added": len(added_rows),
        "after_case_count": len(existing),
        "article_count": len(articles),
        "case_ids": [row["case_id"] for row in added_rows],
        "source_numbers": [row["source_case_number"] for row in added_rows],
    }


def _structured_findings(segment: CaseSegment) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    current_date = ""
    for raw_line in segment.text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        date_match = re.search(r"(20\d{2}[-年/.]\d{1,2}[-月/.]\d{1,2})", line)
        if date_match:
            current_date = date_match.group(1)
        if re.match(r"^\d{1,2}\s*[\.、:：]", line) and not re.match(r"^\d{1,3}\s*[\.、:：]\s*姓名", line):
            findings.append({"text": line, "date": current_date})
        elif any(marker in line for marker in ("检查结果", "检查结论", "考虑恶性", "转移可能", "肿瘤性病变")):
            findings.append({"text": line, "date": current_date})
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for finding in findings:
        key = (str(finding.get("date") or ""), str(finding.get("text") or ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def build_case_rows(pdf_path: Path, upload_dir: Path) -> tuple[list[dict[str, Any]], str]:
    pdf_path = Path(pdf_path)
    upload_dir = Path(upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    source_hash = _file_sha256(pdf_path)
    short_hash = source_hash[:12]
    stored_pdf = f"imaging-summary-{short_hash}.pdf"
    shutil.copy2(pdf_path, upload_dir / stored_pdf)

    rows: list[dict[str, Any]] = []
    for segment in extract_pdf_case_segments(pdf_path):
        images: list[dict[str, Any]] = []
        for image_index, image in enumerate(segment.images, 1):
            extension = re.sub(r"[^a-z0-9]", "", str(image.get("extension") or "jpg").lower()) or "jpg"
            stored_as = f"imaging-{short_hash}-case-{segment.source_case_number:02d}-{image_index:02d}-p{int(image.get('page') or 0):02d}.{extension}"
            (upload_dir / stored_as).write_bytes(bytes(image.get("data") or b""))
            images.append(
                {
                    "type": "image",
                    "filename": f"原编号{segment.source_case_number}-第{image_index}张.{extension}",
                    "stored_as": stored_as,
                    "url": f"/uploads/{stored_as}",
                    "source_page": int(image.get("page") or 0),
                    "physician_annotation": str(image.get("physician_annotation") or ""),
                    "note": "从医生提供的影像汇总 PDF 提取；黄色框线/文字为原资料人工标注。",
                    "width": int(image.get("width") or 0),
                    "height": int(image.get("height") or 0),
                }
            )
        rows.append(
            {
                "sheet": SOURCE_GROUP,
                "diagnosis": f"影像资料病例（原编号 {segment.source_case_number}）",
                "patient_name": segment.patient_name,
                "source_case_number": segment.source_case_number,
                "source_document": SOURCE_DOCUMENT,
                "source_pages": segment.pages,
                "imaging": segment.text,
                "imaging_findings": _structured_findings(segment),
                "medical_images": images,
                "remarks": f"来源文件：{SOURCE_DOCUMENT}（保存为 {stored_pdf}）。原资料编号 {segment.source_case_number}；影像报告与人工标注需结合原片复核。",
            }
        )
    return rows, source_hash


def import_pdf(pdf_path: Path, data_dir: Path) -> dict[str, Any]:
    data_dir = Path(data_dir)
    backup_dir = create_storage_backup(data_dir)
    rows, source_hash = build_case_rows(Path(pdf_path), data_dir / "uploads")
    result = import_segments(data_dir, rows, source_hash)
    manifest = {
        **result,
        "imported_at": datetime.now().isoformat(timespec="seconds"),
        "source_document": SOURCE_DOCUMENT,
        "source_hash": source_hash,
        "backup_dir": str(backup_dir),
        "source_numbers": [row["source_case_number"] for row in rows],
        "added_source_numbers": result.get("source_numbers", []),
        "missing_source_numbers": [11],
    }
    _atomic_write_json(data_dir / "imaging_import_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Import numbered annotated imaging cases into persistent storage.")
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path.home() / ".uscc_scc_flask_data")
    args = parser.parse_args()
    result = import_pdf(args.pdf_path, args.data_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
