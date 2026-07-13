from __future__ import annotations

from copy import deepcopy

from atlas_work_control.focus_brief import build_focus_brief
from atlas_work_control.models import WorkRecord
from atlas_work_control.rules import evaluate_records, is_next_action_valid


def rec(**overrides):
    base = dict(
        code="ATLAS-WORK-X",
        title="فعالیت آزمایشی",
        area="ATLAS Core",
        priority="P1 — کنترل پروژه",
        status="Waiting",
        owners=("رسول",),
        next_action="بررسی رکورد و ثبت خروجی کنترل‌شده در گزارش.",
        expected_output="گزارش کنترل.",
        prerequisite="",
        parking_reason="",
        forgetting_risk="پایین",
        rework_risk="پایین",
        control_note="",
        url="",
        activation_requested=False,
    )
    base.update(overrides)
    return WorkRecord(**base)


def test_001_two_active_is_allowed():
    records = [
        rec(code="ATLAS-WORK-0001", status="Active"),
        rec(code="ATLAS-WORK-0018", status="Active"),
    ]
    result = evaluate_records(records)
    assert not any(f.rule_id == "R-001" for f in result.findings)


def test_002_third_active_is_critical():
    records = [
        rec(code="ATLAS-WORK-0001", status="Active"),
        rec(code="ATLAS-WORK-0018", status="Active"),
        rec(code="ATLAS-WORK-9999", status="Active"),
    ]
    result = evaluate_records(records)
    assert any(f.rule_id == "R-001" and f.severity == "Critical" for f in result.findings)


def test_003_active_without_owner():
    result = evaluate_records([
        rec(code="ATLAS-WORK-0001", status="Active", owners=()),
    ], allowed_active_codes={"ATLAS-WORK-0001"})
    assert any(f.rule_id == "R-002" and f.severity == "Critical" for f in result.findings)


def test_004_waiting_without_owner_high():
    result = evaluate_records([
        rec(code="ATLAS-WORK-0003", status="Waiting", owners=(), forgetting_risk="بالا"),
    ])
    assert any(f.rule_id == "R-002B" and f.severity == "High" for f in result.findings)


def test_005_specific_next_action_is_valid():
    valid, reason = is_next_action_valid(
        "ثبت تاریخ امتحان، منابع کامل و زمان آزاد روزانه در رکورد MBA."
    )
    assert valid, reason


def test_006_vague_next_action_is_rejected():
    valid, _ = is_next_action_valid("ادامه کار روی پروژه")
    assert not valid


def test_007_very_high_forgetting_risk_is_critical():
    result = evaluate_records([
        rec(code="ATLAS-WORK-0001", forgetting_risk="بسیار بالا"),
    ])
    assert any(f.rule_id == "R-005" and f.severity == "Critical" for f in result.findings)


def test_008_opvise_similarity_cluster_is_detected():
    records = [
        rec(
            code="ATLAS-WORK-0011",
            title="تکمیل Opvise Service Delivery Model",
            area="Opvise Partners",
            expected_output="مدل تحویل خدمات Opvise",
            rework_risk="بالا",
        ),
        rec(
            code="ATLAS-WORK-0012",
            title="طراحی Department Service Matrix برای Opvise",
            area="Opvise Partners",
            expected_output="ماتریس خدمات واحدهای Opvise",
            rework_risk="بالا",
        ),
        rec(
            code="ATLAS-WORK-0013",
            title="طراحی Service Catalogue رسمی Opvise",
            area="Opvise Partners",
            expected_output="کاتالوگ رسمی خدمات Opvise",
            rework_risk="بالا",
        ),
    ]
    result = evaluate_records(records)
    clusters = [f for f in result.findings if f.rule_id == "R-006"]
    assert clusters
    combined = set().union(*(set(f.related_codes) for f in clusters))
    assert {"ATLAS-WORK-0011", "ATLAS-WORK-0012", "ATLAS-WORK-0013"} <= combined


def test_009_activation_with_unmet_prerequisite_is_blocked():
    result = evaluate_records([
        rec(
            code="ATLAS-WORK-0006",
            status="Paused",
            prerequisite="پایان تمرکز P0 روی MBA و تأیید ادامه SCOR.",
            activation_requested=True,
        )
    ])
    assert any(f.rule_id == "R-004" and f.severity == "Critical" for f in result.findings)


def test_010_engine_is_read_only_and_brief_is_generated():
    records = [
        rec(code="ATLAS-WORK-0001", status="Active"),
        rec(code="ATLAS-WORK-0018", status="Active"),
    ]
    original = deepcopy(records)
    result = evaluate_records(records)
    brief = build_focus_brief(result, records)
    assert records == original
    assert result.read_only_passed
    assert "Read-only: PASS" in brief
