from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .focus_brief import build_focus_brief
from .models import WorkRecord
from .notion_client import NotionError, NotionReadOnlyClient
from .rules import evaluate_records


def load_fixture(path: Path) -> list[WorkRecord]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Fixture باید یک آرایه JSON باشد.")
    return [WorkRecord.from_dict(item) for item in data]


def main() -> int:
    parser = argparse.ArgumentParser(description="ATLAS Work Control Agent v0.1")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", type=Path, help="مسیر فایل JSON")
    mode.add_argument("--notion", action="store_true", help="خواندن زنده از Notion")
    parser.add_argument("--output-dir", type=Path, default=Path("runs"))
    args = parser.parse_args()

    try:
        if args.fixture:
            records = load_fixture(args.fixture)
        else:
            records = NotionReadOnlyClient().query_all()
    except (OSError, ValueError, json.JSONDecodeError, NotionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("ATLAS-RUN-%Y%m%dT%H%M%SZ")
    result = evaluate_records(records, run_id=run_id)
    result.focus_brief = build_focus_brief(result, records)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    brief_path = args.output_dir / f"{run_id}-focus-brief.md"
    log_path = args.output_dir / f"{run_id}-run-log.json"

    brief_path.write_text(result.focus_brief, encoding="utf-8")
    log_payload = {
        "run_id": result.run_id,
        "input_count": result.input_count,
        "active_codes": result.active_codes,
        "read_only_passed": result.read_only_passed,
        "snapshot_hash_before": result.snapshot_hash_before,
        "snapshot_hash_after": result.snapshot_hash_after,
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity,
                "code": f.code,
                "title": f.title,
                "message": f.message,
                "recommendation": f.recommendation,
                "related_codes": list(f.related_codes),
            }
            for f in result.findings
        ],
    }
    log_path.write_text(
        json.dumps(log_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(result.focus_brief)
    print(f"\nFocus Brief: {brief_path}")
    print(f"Run Log: {log_path}")
    return 0 if result.read_only_passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
