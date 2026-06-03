from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def article_id_number(article_id: Any) -> int:
    try:
        return int(str(article_id or "").split("-", 1)[1])
    except Exception:
        return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    args = parser.parse_args()
    incoming = json.loads(args.input_json.read_text(encoding="utf-8"))
    if not isinstance(incoming, list):
        raise ValueError("Expected a JSON list of literature rows.")

    rows = app._load_articles()
    seen_dois: set[str] = set()
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    seen_sources: set[str] = set()

    def register(row: dict[str, Any]) -> None:
        doi = app._normalize_article_doi(row.get("doi") or row.get("source_url") or "")
        url = app._normalize_article_url(row.get("source_url") or "")
        title = app._normalize_article_title(row.get("title") or "")
        source = str(row.get("source_file") or "").strip().lower()
        if doi:
            seen_dois.add(doi)
        if url:
            seen_urls.add(url)
        if len(title) >= 12:
            seen_titles.add(title)
        if source:
            seen_sources.add(source)

    for row in rows:
        if isinstance(row, dict):
            register(row)

    next_number = max((article_id_number(row.get("article_id")) for row in rows), default=0) + 1
    added = 0
    skipped = 0
    for fields in incoming:
        if not isinstance(fields, dict):
            continue
        doi = app._normalize_article_doi(fields.get("doi") or fields.get("source_url") or "")
        url = app._normalize_article_url(fields.get("source_url") or "")
        title = app._normalize_article_title(fields.get("title") or "")
        source = str(fields.get("source_file") or "").strip().lower()
        duplicate = (
            (doi and doi in seen_dois)
            or (url and url in seen_urls)
            or (len(title) >= 12 and title in seen_titles)
            or (source and source in seen_sources)
        )
        if duplicate:
            skipped += 1
            continue
        base = {
            "title": str(fields.get("title") or "").strip() or "\u672a\u547d\u540d\u6587\u732e",
            "authors": str(fields.get("authors") or "").strip(),
            "journal": str(fields.get("journal") or "").strip(),
            "year": str(fields.get("year") or "").strip(),
            "doi": doi,
            "keywords": str(fields.get("keywords") or "").strip(),
            "abstract": str(fields.get("abstract") or "").strip(),
            "content": str(fields.get("content") or "").strip(),
            "notes": str(fields.get("notes") or "").strip(),
            "source_file": str(fields.get("source_file") or "").strip(),
            "source_url": str(fields.get("source_url") or "").strip(),
            "stored_as": "",
            "article_images": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        article = {
            "article_id": f"ARTICLE-{next_number:03d}",
            **base,
            "signature": app._article_signature_fields(base),
        }
        rows.append(article)
        register(article)
        next_number += 1
        added += 1

    if added:
        app._save_articles(rows)
    else:
        app._save_library_snapshot()
        app._write_storage_manifest()
    print(json.dumps({
        "before": len(rows) - added,
        "incoming": len(incoming),
        "added": added,
        "skipped_duplicates": skipped,
        "after": len(rows),
    }, ensure_ascii=True))


if __name__ == "__main__":
    main()
