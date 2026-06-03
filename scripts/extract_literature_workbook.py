from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


PLACEHOLDERS = {"", "nan", "none", "null", "/", "\\"}
LINK_HEADERS = {"\u94fe\u63a5", "doi\u94fe\u63a5", "url", "link"}
DOI_HEADERS = {"doi"}
IF_HEADERS = {"if", "impactfactor", "impact factor"}


def clean(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in PLACEHOLDERS else text


def header_key(value: Any) -> str:
    return re.sub(r"\s+", "", clean(value).lower())


def extract_doi(*values: Any) -> str:
    for value in values:
        match = re.search(r"10\.\d{4,9}/[-._;()/:a-z0-9]+", clean(value), re.I)
        if match:
            return match.group(0).rstrip(".,;")
    return ""


def build_labels(columns: list[Any], subheaders: list[Any]) -> list[str]:
    labels: list[str] = []
    group = ""
    for top_raw, sub_raw in zip(columns, subheaders):
        top = clean(top_raw)
        sub = clean(sub_raw)
        if top and not top.lower().startswith("unnamed"):
            group = top
        if sub and sub != group:
            labels.append(f"{group}/{sub}" if group else sub)
        else:
            labels.append(group or top or "\u8865\u5145\u5185\u5bb9")
    return labels


def extract_rows(workbook_path: Path) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    xl = pd.ExcelFile(workbook_path)
    for sheet_name in xl.sheet_names:
        frame = pd.read_excel(workbook_path, sheet_name=sheet_name, dtype=str).fillna("")
        if frame.empty:
            continue
        columns = list(frame.columns)
        subheaders = frame.iloc[0].tolist()
        labels = build_labels(columns, subheaders)
        metadata_indexes = {0, 1, 2, 3}
        link_indexes: list[int] = []
        doi_indexes: list[int] = []
        if_indexes: list[int] = []
        for index, column in enumerate(columns):
            key = header_key(column)
            if key in LINK_HEADERS:
                metadata_indexes.add(index)
                link_indexes.append(index)
            elif key in DOI_HEADERS:
                metadata_indexes.add(index)
                doi_indexes.append(index)
            elif key in IF_HEADERS:
                metadata_indexes.add(index)
                if_indexes.append(index)

        for row_index, series in frame.iloc[1:].iterrows():
            values = [clean(value) for value in series.tolist()]
            title = values[0] if values else ""
            if not title:
                continue
            source_url = next((values[index] for index in link_indexes if values[index]), "")
            doi = extract_doi(*(values[index] for index in doi_indexes + link_indexes))
            impact_factor = next((values[index] for index in if_indexes if values[index]), "")
            sections: list[str] = []
            for index, value in enumerate(values):
                if index in metadata_indexes or not value:
                    continue
                sections.append(f"\u3010{labels[index]}\u3011\n{value}")
            content = "\n\n".join(sections)
            if not content:
                content = title
            notes = [
                f"\u7531{workbook_path.name}\u5bfc\u5165",
                f"\u6765\u6e90\u5de5\u4f5c\u8868\uff1a{sheet_name}",
                f"Excel \u884c\uff1a{int(row_index) + 2}",
            ]
            if impact_factor:
                notes.append(f"IF\uff1a{impact_factor}")
            extracted.append({
                "title": title,
                "authors": values[1] if len(values) > 1 else "",
                "year": values[2] if len(values) > 2 else "",
                "journal": values[3] if len(values) > 3 else "",
                "doi": doi,
                "source_url": source_url or (f"https://doi.org/{doi}" if doi else ""),
                "source_file": f"{workbook_path.name}/{sheet_name}:row-{int(row_index) + 2}",
                "keywords": f"{sheet_name}; USCC; urethral squamous cell carcinoma",
                "abstract": content[:3000],
                "content": content,
                "notes": "\uff1b".join(notes),
            })
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    rows = extract_rows(args.workbook)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"workbook": str(args.workbook), "extracted_rows": len(rows)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
