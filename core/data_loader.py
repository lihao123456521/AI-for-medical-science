from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import math
import re

import pandas as pd

MISSING = {"", "nan", "none", "null", "/", "\\", "NaT"}


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    if text.lower() in MISSING:
        return ""
    # Excel datetime strings are acceptable, but remove trailing .0 style noise.
    return re.sub(r"\s+", " ", text)


def _is_blank(value: Any) -> bool:
    return _clean_cell(value) == ""


def _dedupe_columns(cols: Iterable[str]) -> List[str]:
    seen: Dict[str, int] = {}
    result: List[str] = []
    for i, col in enumerate(cols):
        base = _clean_cell(col) or f"字段_{i + 1}"
        base = base.replace("\n", " ").strip()
        if base not in seen:
            seen[base] = 0
            result.append(base)
        else:
            seen[base] += 1
            result.append(f"{base}_{seen[base]}")
    return result


def _flatten_two_row_header(raw: pd.DataFrame) -> pd.DataFrame:
    """The uploaded workbook uses broad merged headers plus a second clinical sub-header row.
    This function creates stable clinical column names while preserving the source columns.
    """
    if raw.shape[0] < 2:
        return raw

    top = list(raw.iloc[0].values)
    sub = list(raw.iloc[1].values)
    columns: List[str] = []
    for idx, (a, b) in enumerate(zip(top, sub)):
        a_txt = _clean_cell(a)
        b_txt = _clean_cell(b)
        if b_txt and not b_txt.lower().startswith("unnamed"):
            columns.append(b_txt)
        elif a_txt and not a_txt.lower().startswith("unnamed"):
            columns.append(a_txt)
        else:
            columns.append(f"字段_{idx + 1}")
    df = raw.iloc[2:].copy()
    df.columns = _dedupe_columns(columns)
    df = df.dropna(how="all")
    return df


def _first_present(row: Dict[str, Any], candidates: Iterable[str]) -> str:
    for key in candidates:
        if key in row and not _is_blank(row[key]):
            return _clean_cell(row[key])
    return ""


def _value_contains(value: str, patterns: Iterable[str]) -> bool:
    return any(p.lower() in value.lower() for p in patterns if p)


@dataclass
class CaseRecord:
    case_id: str
    sheet: str
    diagnosis: str
    sex: str
    age: Optional[float]
    history: str
    prior_operation: str
    symptoms: str
    tumor: str
    grade: str
    tnm: str
    lymph_node: str
    ls: str
    immuno: str
    imaging: str
    pathology: str
    surgery: str
    other_treatment: str
    recurrence: str
    followup: str
    remarks: str
    source_row: int
    medical_images: List[Dict[str, Any]] = field(default_factory=list)

    def as_public_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "sheet": self.sheet,
            "diagnosis": self.diagnosis,
            "sex": self.sex,
            "age": self.age,
            "history": self.history,
            "prior_operation": self.prior_operation,
            "symptoms": self.symptoms,
            "tumor": self.tumor,
            "grade": self.grade,
            "tnm": self.tnm,
            "lymph_node": self.lymph_node,
            "ls": self.ls,
            "immuno": self.immuno,
            "imaging": self.imaging,
            "pathology": self.pathology,
            "surgery": self.surgery,
            "other_treatment": self.other_treatment,
            "recurrence": self.recurrence,
            "followup": self.followup,
            "remarks": self.remarks,
            "source_row": self.source_row,
            "medical_images": self.medical_images or [],
        }

    @property
    def searchable_text(self) -> str:
        parts = [
            self.sheet, self.diagnosis, self.sex, str(self.age or ""), self.history,
            self.prior_operation, self.symptoms, self.tumor, self.grade, self.tnm,
            self.lymph_node, self.ls, self.immuno, self.imaging, self.pathology,
            self.surgery, self.other_treatment, self.recurrence, self.followup, self.remarks,
            " ".join(str(x.get("filename", "")) + " " + str(x.get("note", "")) for x in (self.medical_images or []) if isinstance(x, dict)),
        ]
        return "\n".join([p for p in parts if p])


class KnowledgeBase:
    def __init__(self, excel_path: str | Path):
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"知识库文件不存在: {self.excel_path}")
        self.records: List[CaseRecord] = []
        self.sheet_shapes: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        xl = pd.ExcelFile(self.excel_path)
        records: List[CaseRecord] = []
        for sheet in xl.sheet_names:
            raw = pd.read_excel(self.excel_path, sheet_name=sheet, header=None)
            df = _flatten_two_row_header(raw)
            self.sheet_shapes[sheet] = {"rows": int(df.shape[0]), "columns": int(df.shape[1])}
            for i, row_series in df.iterrows():
                row = {str(k): v for k, v in row_series.to_dict().items()}
                diagnosis = _first_present(row, ["疾病名称/诊断", "主要诊断", "诊断", "病理诊断"])
                # Skip rows that have nearly no clinical content.
                if not diagnosis and not _first_present(row, ["病史要点", "病史", "症状/体征", "肿瘤情况", "病理信息", "病理诊断"]):
                    continue
                age_text = _first_present(row, ["年龄（岁）", "年龄"])
                try:
                    age = float(age_text) if age_text else None
                except ValueError:
                    age = None
                rec = CaseRecord(
                    case_id=f"{sheet}-{len(records) + 1:03d}",
                    sheet=sheet,
                    diagnosis=diagnosis,
                    sex=_first_present(row, ["性别"]),
                    age=age,
                    history=_first_present(row, ["病史要点", "病史"]),
                    prior_operation=_first_present(row, ["既往尿道重建手术", "既往尿道重建术", "临床操作史"]),
                    symptoms=_first_present(row, ["症状/体征"]),
                    tumor=_first_present(row, ["肿瘤情况"]),
                    grade=_first_present(row, ["肿瘤分化程度（Grade分级）", "分化情况", "TNM分期/分级"]),
                    tnm=_first_present(row, ["TNM分期/Grade分级", "TNM分期/分级"]),
                    lymph_node=_first_present(row, ["有无淋巴结转移"]),
                    ls=_first_present(row, ["有无硬化性苔藓（LS）", "高危因素"]),
                    immuno=_first_present(row, ["免疫", "免疫组化", "病理检查"]),
                    imaging=_first_present(row, ["影像信息", "影像检查", "复发影像", "术后影像"]),
                    pathology=_first_present(row, ["病理诊断", "病理信息", "病理检查"]),
                    surgery=_first_present(row, ["手术治疗"]),
                    other_treatment=_first_present(row, ["其他治疗", "药物治疗"]),
                    recurrence=_first_present(row, ["术后复发/转移情况", "术后复发/转移", "复发情况", "术后转移"]),
                    followup=_first_present(row, ["随访结果"]),
                    remarks=_first_present(row, ["备注", "并发症"]),
                    source_row=int(i) + 1,
                )
                records.append(rec)
        self.records = records

    def summary(self) -> Dict[str, Any]:
        by_sheet: Dict[str, int] = {}
        scc_count = 0
        ls_mentions = 0
        recurrence_mentions = 0
        ages: List[float] = []
        for r in self.records:
            by_sheet[r.sheet] = by_sheet.get(r.sheet, 0) + 1
            text = r.searchable_text
            if _value_contains(text, ["鳞癌", "SCC", "squamous"]):
                scc_count += 1
            if _value_contains(text, ["硬化性苔藓", "LS", "lichen"]):
                ls_mentions += 1
            if _value_contains(r.recurrence, ["复发", "转移"]):
                recurrence_mentions += 1
            if r.age is not None:
                ages.append(r.age)
        return {
            "total_cases": len(self.records),
            "sheets": by_sheet,
            "sheet_shapes": self.sheet_shapes,
            "scc_related_cases": scc_count,
            "ls_mentions": ls_mentions,
            "recurrence_or_metastasis_mentions": recurrence_mentions,
            "age_min": min(ages) if ages else None,
            "age_max": max(ages) if ages else None,
            "age_mean": round(sum(ages) / len(ages), 1) if ages else None,
        }

    def get_records(self, sheet: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        rows = [r for r in self.records if sheet is None or r.sheet == sheet]
        return [r.as_public_dict() for r in rows[:limit]]
