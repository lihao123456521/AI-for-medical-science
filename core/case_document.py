from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import re


CASE_START_RE = re.compile(
    r"(?m)^\s*(?P<number>\d{1,3})\s*[\.、:：]\s*(?:姓名|患者姓名)\s*[：:]\s*(?P<name>[^\n]+?)\s*$"
)
NUMBERED_FINDING_RE = re.compile(r"^\s*\d{1,2}\s*[\.、:：]\s*\S+")


@dataclass
class CaseSegment:
    source_case_number: int
    patient_name: str
    text: str
    pages: list[int] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)


def segment_numbered_cases(text: str) -> list[CaseSegment]:
    source = str(text or "")
    matches = list(CASE_START_RE.finditer(source))
    rows: list[CaseSegment] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        rows.append(
            CaseSegment(
                source_case_number=int(match.group("number")),
                patient_name=match.group("name").strip(),
                text=source[match.start():end].strip(),
            )
        )
    return rows


def assign_layout_events(
    events: list[dict[str, Any]],
    starting_case_number: int | None = None,
) -> dict[int, dict[str, Any]]:
    current = starting_case_number
    owned: dict[int, dict[str, Any]] = {}
    ordered = sorted(
        events,
        key=lambda row: (
            int(row.get("page") or 0),
            float(row.get("y") or 0),
            0 if row.get("kind") == "text" else 1,
        ),
    )
    for event in ordered:
        if event.get("kind") == "text":
            match = CASE_START_RE.search(str(event.get("text") or ""))
            if match:
                current = int(match.group("number"))
        if current is None:
            continue
        bucket = owned.setdefault(current, {"texts": [], "images": [], "pages": []})
        page = int(event.get("page") or 0)
        if page and page not in bucket["pages"]:
            bucket["pages"].append(page)
        target = "texts" if event.get("kind") == "text" else "images"
        bucket[target].append(event)
    return owned


def _line_text(line: dict[str, Any]) -> str:
    return "".join(str(span.get("text") or "") for span in line.get("spans", [])).strip()


def _pdf_layout_events(path: Path) -> list[dict[str, Any]]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF layout extraction requires PyMuPDF.") from exc

    events: list[dict[str, Any]] = []
    document = fitz.open(str(path))
    try:
        for page_index, page in enumerate(document, 1):
            layout = page.get_text("dict")
            image_index = 0
            for block in layout.get("blocks", []):
                bbox = block.get("bbox") or (0, 0, 0, 0)
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        text = _line_text(line)
                        if not text:
                            continue
                        line_bbox = line.get("bbox") or bbox
                        events.append(
                            {
                                "kind": "text",
                                "page": page_index,
                                "y": float(line_bbox[1]),
                                "text": text,
                            }
                        )
                elif block.get("type") == 1 and block.get("image"):
                    image_index += 1
                    events.append(
                        {
                            "kind": "image",
                            "page": page_index,
                            "y": float(bbox[1]),
                            "xref": int(block.get("xref") or 0),
                            "placement_index": image_index,
                            "extension": str(block.get("ext") or "png").lower(),
                            "width": int(block.get("width") or 0),
                            "height": int(block.get("height") or 0),
                            "data": bytes(block.get("image") or b""),
                        }
                    )
    finally:
        document.close()
    return events


def _nearby_annotation(image: dict[str, Any], texts: list[dict[str, Any]]) -> str:
    same_page = [row for row in texts if row.get("page") == image.get("page")]
    if not same_page:
        return ""
    image_y = float(image.get("y") or 0)
    numbered = [row for row in same_page if NUMBERED_FINDING_RE.match(str(row.get("text") or ""))]
    candidates = numbered or same_page
    candidates.sort(key=lambda row: abs(float(row.get("y") or 0) - image_y))
    return str(candidates[0].get("text") or "").strip() if candidates else ""


def extract_pdf_case_segments(path: str | Path) -> list[CaseSegment]:
    pdf_path = Path(path)
    events = _pdf_layout_events(pdf_path)
    owned = assign_layout_events(events)
    rows: list[CaseSegment] = []
    for number, bucket in owned.items():
        texts = bucket.get("texts", [])
        text = "\n".join(str(row.get("text") or "").strip() for row in texts if str(row.get("text") or "").strip())
        match = CASE_START_RE.search(text)
        if not match:
            continue
        images = []
        for image in bucket.get("images", []):
            item = dict(image)
            item["physician_annotation"] = _nearby_annotation(item, texts)
            images.append(item)
        rows.append(
            CaseSegment(
                source_case_number=number,
                patient_name=match.group("name").strip(),
                text=text,
                pages=sorted(set(int(page) for page in bucket.get("pages", []) if int(page) > 0)),
                images=images,
            )
        )
    return sorted(rows, key=lambda row: row.source_case_number)
