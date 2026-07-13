from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict
from itertools import combinations
from typing import Iterable

from .models import Finding, RunResult, WorkRecord


SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

ACTION_VERBS = (
    "ثبت", "بررسی", "بازبینی", "تهیه", "تدوین", "تعریف", "تکمیل", "اجرای",
    "اجرا", "استخراج", "اعتبارسنجی", "ساخت", "طراحی", "تعیین", "محاسبه",
    "اصلاح", "به‌روزرسانی", "اتصال", "آزمایش", "تست", "تحلیل", "مقایسه",
    "جمع‌آوری", "ارسال", "دریافت", "قفل", "مستندسازی"
)

VAGUE_PATTERNS = (
    r"^ادامه\s+کار",
    r"^پیگیری\s+شود$",
    r"^بررسی\s+شود$",
    r"^روی\s+پروژه\s+کار",
    r"^تکمیل\s+پروژه$",
    r"^اقدام\s+لازم",
)

STOPWORDS = {
    "و", "در", "به", "از", "برای", "با", "را", "یا", "پس", "طبق", "بدون",
    "یک", "این", "آن", "شود", "شده", "کردن", "فعال", "مدل", "طراحی", "تکمیل",
    "ساخت", "تعریف", "استخراج", "نسخه", "رسمی", "اطلس"
}


def snapshot_hash(records: Iterable[WorkRecord]) -> str:
    payload = [asdict(r) for r in records]
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> list[str]:
    text = text.replace("ي", "ی").replace("ك", "ک").lower()
    tokens = re.findall(r"[\w\u0600-\u06FF]+", text)
    return [t for t in tokens if len(t) > 2 and t not in STOPWORDS]


def jaccard(a: str, b: str) -> float:
    aa, bb = set(normalize_text(a)), set(normalize_text(b))
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def is_next_action_valid(text: str) -> tuple[bool, str]:
    clean = re.sub(r"\s+", " ", text.strip())
    if not clean:
        return False, "اقدام بعدی خالی است."
    if len(clean) < 18:
        return False, "اقدام بعدی بیش از حد کوتاه است."
    if any(re.search(pattern, clean, re.IGNORECASE) for pattern in VAGUE_PATTERNS):
        return False, "اقدام بعدی کلی و فاقد خروجی مشخص است."
    if not any(verb in clean for verb in ACTION_VERBS):
        return False, "فعل اجرایی مشخص در اقدام بعدی شناسایی نشد."
    return True, ""


def _prerequisite_appears_satisfied(record: WorkRecord) -> bool:
    if not record.prerequisite:
        return True
    note = record.control_note
    positive_markers = ("انجام شده", "ایجاد شده", "تأیید شده", "تثبیت شده", "محقق شده")
    return any(marker in record.prerequisite or marker in note for marker in positive_markers)


def evaluate_records(
    records: list[WorkRecord],
    *,
    wip_limit: int | None = None,
    allowed_active_codes: set[str] | None = None,
    run_id: str = "ATLAS-RUN-LOCAL",
) -> RunResult:
    wip_limit = wip_limit if wip_limit is not None else int(os.getenv("ATLAS_WIP_LIMIT", "2"))
    if allowed_active_codes is None:
        env_codes = os.getenv(
            "ATLAS_ALLOWED_ACTIVE_CODES",
            "ATLAS-WORK-0001,ATLAS-WORK-0018",
        )
        allowed_active_codes = {x.strip() for x in env_codes.split(",") if x.strip()}

    before = snapshot_hash(records)
    findings: list[Finding] = []
    active = [r for r in records if r.status == "Active"]
    active_codes = [r.code for r in active]

    # R-001: WIP
    if len(active) > wip_limit:
        findings.append(Finding(
            rule_id="R-001",
            severity="Critical",
            code="WIP",
            title="تخطی سقف WIP",
            message=f"{len(active)} فعالیت Active وجود دارد؛ سقف مجاز {wip_limit} است.",
            recommendation="فعالیت اضافی را فقط پس از تصمیم انسانی به Waiting یا Paused منتقل کنید.",
            related_codes=tuple(active_codes),
        ))

    unexpected_active = [r.code for r in active if allowed_active_codes and r.code not in allowed_active_codes]
    if unexpected_active:
        findings.append(Finding(
            rule_id="R-001B",
            severity="Critical",
            code="WIP",
            title="فعالیت Active خارج از دامنه مجاز",
            message="کدهای Active خارج از فهرست مجاز شناسایی شد.",
            recommendation="فعال‌سازی باید بررسی و تأیید انسانی شود.",
            related_codes=tuple(unexpected_active),
        ))

    # R-002: Owner
    for r in records:
        if r.status == "Active" and not r.owners:
            findings.append(Finding(
                "R-002", "Critical", r.code, r.title,
                "فعالیت Active بدون مالک است.",
                "مالک تعیین شود؛ Agent هیچ تغییری اعمال نمی‌کند."
            ))
        elif (
            r.status in {"Waiting", "Blocked"}
            and not r.owners
            and (r.priority.startswith("P0") or r.priority.startswith("P1") or r.forgetting_risk in {"بالا", "بسیار بالا"})
        ):
            findings.append(Finding(
                "R-002B", "High", r.code, r.title,
                "رکورد مهم در صف بدون مالک است.",
                "در بازبینی هفتگی مالک یا تصمیم توقف تعیین شود."
            ))

    # R-003: Next action
    for r in records:
        valid, reason = is_next_action_valid(r.next_action)
        if not valid:
            severity = "Critical" if r.status == "Active" else "High"
            findings.append(Finding(
                "R-003", severity, r.code, r.title,
                reason,
                "اقدام بعدی با فعل اجرایی، خروجی، مرجع و شرط پایان بازنویسی شود."
            ))

    # R-004: Prerequisite
    for r in records:
        if r.activation_requested and r.prerequisite and not _prerequisite_appears_satisfied(r):
            findings.append(Finding(
                "R-004", "Critical", r.code, r.title,
                f"درخواست فعال‌سازی با پیش‌نیاز حل‌نشده: {r.prerequisite}",
                "وضعیت پیشنهادی: Blocked for Approval؛ بدون تغییر خودکار."
            ))
        elif r.status == "Active" and r.prerequisite and not _prerequisite_appears_satisfied(r):
            findings.append(Finding(
                "R-004B", "Critical", r.code, r.title,
                f"فعالیت Active دارای پیش‌نیاز اثبات‌نشده است: {r.prerequisite}",
                "ادامه اجرا نیازمند تأیید انسانی است."
            ))

    # R-005: Forgetting risk
    for r in records:
        if r.forgetting_risk == "بسیار بالا":
            findings.append(Finding(
                "R-005", "Critical", r.code, r.title,
                "ریسک فراموش‌شدن بسیار بالا است.",
                "در Critical Attention نمایش داده شود."
            ))
        elif r.forgetting_risk == "بالا":
            findings.append(Finding(
                "R-005B", "High", r.code, r.title,
                "ریسک فراموش‌شدن بالا است.",
                "در بازبینی هفتگی نمایش داده شود."
            ))

    # R-006: Duplicate/rework clusters. No automatic merge.
    candidates = [
        r for r in records
        if r.rework_risk in {"بالا", "بسیار بالا"} and r.status not in {"Completed", "Cancelled"}
    ]
    graph: dict[str, set[str]] = {r.code: set() for r in candidates}
    by_code = {r.code: r for r in candidates}
    for left, right in combinations(candidates, 2):
        same_area = left.area == right.area and bool(left.area)
        score = jaccard(
            f"{left.title} {left.expected_output}",
            f"{right.title} {right.expected_output}",
        )
        # A lower threshold is intentional for same-area high-rework records.
        if score >= 0.20 or (same_area and score >= 0.12):
            graph[left.code].add(right.code)
            graph[right.code].add(left.code)

    visited: set[str] = set()
    for code in graph:
        if code in visited or not graph[code]:
            continue
        stack = [code]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(graph[current] - visited)
        if len(component) >= 2:
            titles = " | ".join(by_code[c].title for c in sorted(component))
            findings.append(Finding(
                "R-006", "High", "CLUSTER", "خوشه احتمالی دوباره‌کاری",
                f"خوشه مشابهت شناسایی شد: {titles}",
                "فقط پیشنهاد تجمیع منطقی ثبت شود؛ حذف یا ادغام خودکار ممنوع است.",
                tuple(sorted(component)),
            ))

    # R-007: Status/parking control
    for r in records:
        if r.status in {"Paused", "Parking Lot"} and not r.parking_reason:
            findings.append(Finding(
                "R-007", "Medium", r.code, r.title,
                "وضعیت توقف ثبت شده اما دلیل توقف خالی است.",
                "دلیل توقف و شرط بازگشت ثبت شود."
            ))

    # R-008: Current review date is intentionally left to the adapter because
    # the simplified WorkRecord does not carry the date field in v0.1.

    after = snapshot_hash(records)
    findings.sort(key=lambda x: (SEVERITY_ORDER.get(x.severity, 9), x.rule_id, x.code))

    return RunResult(
        run_id=run_id,
        input_count=len(records),
        findings=findings,
        active_codes=active_codes,
        snapshot_hash_before=before,
        snapshot_hash_after=after,
    )
