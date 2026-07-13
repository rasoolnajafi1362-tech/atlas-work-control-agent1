from __future__ import annotations

from collections import Counter

from .models import RunResult, WorkRecord


def build_focus_brief(result: RunResult, records: list[WorkRecord]) -> str:
    counts = Counter(f.severity for f in result.findings)
    active_map = {r.code: r for r in records if r.status == "Active"}

    lines = [
        f"# ATLAS Focus Brief — {result.run_id}",
        "",
        "## وضعیت کنترل",
        f"- تعداد رکوردهای بررسی‌شده: {result.input_count}",
        f"- تعداد Active: {len(result.active_codes)}",
        f"- Activeها: {', '.join(result.active_codes) or 'هیچ'}",
        f"- Read-only: {'PASS' if result.read_only_passed else 'FAIL'}",
        f"- Critical: {counts.get('Critical', 0)}",
        f"- High: {counts.get('High', 0)}",
        f"- Medium: {counts.get('Medium', 0)}",
        "",
        "## تمرکز جاری",
    ]

    for code in result.active_codes:
        r = active_map[code]
        lines.extend([
            f"### {r.code} — {r.title}",
            f"- مالک: {', '.join(r.owners) if r.owners else 'تعیین نشده'}",
            f"- اقدام بعدی: {r.next_action or 'ثبت نشده'}",
            f"- خروجی: {r.expected_output or 'ثبت نشده'}",
        ])

    critical = [f for f in result.findings if f.severity == "Critical"]
    lines.extend(["", "## Critical Attention"])
    if not critical:
        lines.append("- مورد Critical شناسایی نشد.")
    else:
        for f in critical:
            related = f" | مرتبط: {', '.join(f.related_codes)}" if f.related_codes else ""
            lines.append(f"- [{f.rule_id}] {f.code}: {f.message}{related}")

    high = [f for f in result.findings if f.severity == "High"]
    lines.extend(["", "## High Attention"])
    if not high:
        lines.append("- مورد High شناسایی نشد.")
    else:
        for f in high[:15]:
            related = f" | مرتبط: {', '.join(f.related_codes)}" if f.related_codes else ""
            lines.append(f"- [{f.rule_id}] {f.code}: {f.message}{related}")

    lines.extend([
        "",
        "## تصمیم کنترلی",
        "- این گزارش هیچ تغییری در ATLAS-WORK ایجاد نکرده است.",
        "- هر تغییر وضعیت، مالک، اقدام بعدی، ادغام یا حذف نیازمند تأیید انسانی است.",
    ])
    return "\n".join(lines)
