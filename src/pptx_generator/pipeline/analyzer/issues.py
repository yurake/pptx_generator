from __future__ import annotations

from itertools import count
from typing import Any


class IssueTracker:
    def __init__(self) -> None:
        self._sequence = count(1)

    def next_issue_id(self, issue_type: str, slide_id: str, element_id: str | None) -> str:
        sequence = next(self._sequence)
        parts: list[str] = [issue_type, slide_id]
        if element_id:
            parts.append(element_id)
        parts.append(str(sequence))
        return "-".join(parts)

    @staticmethod
    def extend_results(
        issues: list[dict[str, Any]],
        fixes: list[dict[str, Any]],
        outcome: tuple[dict[str, Any], dict[str, Any]] | None,
    ) -> None:
        if outcome is None:
            return
        issue, fix = outcome
        issues.append(issue)
        if fix:
            fixes.append(fix)

    @staticmethod
    def make_issue(
        *,
        issue_id: str,
        issue_type: str,
        severity: str,
        message: str,
        target: dict[str, Any],
        metrics: dict[str, Any],
        fix: dict[str, Any] | None,
    ) -> dict[str, Any]:
        issue = {
            "id": issue_id,
            "type": issue_type,
            "severity": severity,
            "message": message,
            "target": target,
            "metrics": metrics,
        }
        if fix:
            issue["fix"] = fix
        return issue
