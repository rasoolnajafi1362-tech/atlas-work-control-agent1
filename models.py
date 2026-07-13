from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class WorkRecord:
    code: str
    title: str
    area: str = ""
    priority: str = ""
    status: str = ""
    owners: tuple[str, ...] = ()
    next_action: str = ""
    expected_output: str = ""
    prerequisite: str = ""
    parking_reason: str = ""
    forgetting_risk: str = ""
    rework_risk: str = ""
    control_note: str = ""
    url: str = ""
    activation_requested: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkRecord":
        owners = data.get("owners") or data.get("مالک") or ()
        if isinstance(owners, str):
            owners = (owners,) if owners.strip() else ()
        elif isinstance(owners, list):
            owners = tuple(str(x) for x in owners if str(x).strip())
        elif isinstance(owners, tuple):
            owners = owners
        else:
            owners = ()

        return cls(
            code=str(data.get("code") or data.get("کد فعالیت") or "").strip(),
            title=str(data.get("title") or data.get("عنوان فعالیت") or "").strip(),
            area=str(data.get("area") or data.get("حوزه") or "").strip(),
            priority=str(data.get("priority") or data.get("اولویت") or "").strip(),
            status=str(data.get("status") or data.get("وضعیت") or "").strip(),
            owners=owners,
            next_action=str(data.get("next_action") or data.get("اقدام بعدی") or "").strip(),
            expected_output=str(data.get("expected_output") or data.get("خروجی مورد انتظار") or "").strip(),
            prerequisite=str(data.get("prerequisite") or data.get("پیش‌نیاز فعال‌سازی") or "").strip(),
            parking_reason=str(data.get("parking_reason") or data.get("دلیل توقف یا Parking") or "").strip(),
            forgetting_risk=str(data.get("forgetting_risk") or data.get("ریسک فراموش‌شدن") or "").strip(),
            rework_risk=str(data.get("rework_risk") or data.get("ریسک دوباره‌کاری") or "").strip(),
            control_note=str(data.get("control_note") or data.get("یادداشت کنترل") or "").strip(),
            url=str(data.get("url") or "").strip(),
            activation_requested=bool(data.get("activation_requested", False)),
        )


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    code: str
    title: str
    message: str
    recommendation: str = ""
    related_codes: tuple[str, ...] = ()


@dataclass
class RunResult:
    run_id: str
    input_count: int
    findings: list[Finding] = field(default_factory=list)
    active_codes: list[str] = field(default_factory=list)
    focus_brief: str = ""
    snapshot_hash_before: str = ""
    snapshot_hash_after: str = ""

    @property
    def read_only_passed(self) -> bool:
        return self.snapshot_hash_before == self.snapshot_hash_after
