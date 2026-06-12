from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.seed_data import audit_seed_payload, build_seed_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build audited de-identified public seed data.")
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cases", type=int, required=True)
    parser.add_argument("--expected-articles", type=int, required=True)
    args = parser.parse_args()

    cases = json.loads((args.runtime_dir / "user_cases.json").read_text(encoding="utf-8"))
    articles = json.loads((args.runtime_dir / "articles.json").read_text(encoding="utf-8"))
    payload = build_seed_payload(cases, articles)
    if len(payload["cases"]) != args.expected_cases or len(payload["articles"]) != args.expected_articles:
        raise SystemExit(f"count mismatch: cases={len(payload['cases'])}, articles={len(payload['articles'])}")
    findings = audit_seed_payload(payload)
    if findings:
        raise SystemExit("privacy audit failed:\n" + "\n".join(findings[:100]))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "user_cases.json").write_text(json.dumps(payload["cases"], ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output_dir / "articles.json").write_text(json.dumps(payload["articles"], ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "version": "2026-06-12-v38",
        "case_count": len(payload["cases"]),
        "article_count": len(payload["articles"]),
        "images_included": 0,
        "privacy_audit_findings": 0,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
