"""Data-quality framework — validate a batch of records against rules.

Real data engineers don't just move data, they *trust* it. This module runs a
suite of declarative checks over the records and produces a pass/fail report
(the kind of thing you'd wire into a pipeline to block a bad load).

The design is OOP again: ``QualityCheck`` is an abstract rule; concrete rules
(not-null, range, uniqueness, allowed-values, row-count) plug into a
``QualitySuite`` that runs them all and aggregates the result.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable, Sequence


@dataclass
class CheckResult:
    name: str
    passed: bool
    failed_rows: int
    total_rows: int
    severity: str           # "error" blocks the load, "warning" just reports
    detail: str = ""

    @property
    def pass_rate(self) -> float:
        if self.total_rows == 0:
            return 1.0
        return round(1 - self.failed_rows / self.total_rows, 4)


class QualityCheck(ABC):
    """One declarative rule over a list of row dicts."""

    severity: str = "error"

    def __init__(self, severity: str | None = None) -> None:
        if severity:
            self.severity = severity

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def run(self, rows: Sequence[dict]) -> CheckResult:
        raise NotImplementedError

    def _result(self, rows: Sequence[dict], failed: int, detail: str = "") -> CheckResult:
        return CheckResult(
            name=self.name, passed=failed == 0, failed_rows=failed,
            total_rows=len(rows), severity=self.severity, detail=detail,
        )


class NotNullCheck(QualityCheck):
    """Fail rows where any required column is missing/None/empty-string."""

    def __init__(self, columns: list[str], **kw) -> None:
        super().__init__(**kw)
        self.columns = columns

    @property
    def name(self) -> str:
        return f"not_null({', '.join(self.columns)})"

    def run(self, rows: Sequence[dict]) -> CheckResult:
        failed = sum(
            1 for r in rows
            if any(r.get(c) is None or r.get(c) == "" for c in self.columns)
        )
        return self._result(rows, failed)


class RangeCheck(QualityCheck):
    """Fail rows where ``column`` falls outside [min_value, max_value]."""

    def __init__(self, column: str, min_value: float | None = None,
                 max_value: float | None = None, **kw) -> None:
        super().__init__(**kw)
        self.column = column
        self.min_value = min_value
        self.max_value = max_value

    @property
    def name(self) -> str:
        return f"range({self.column})"

    def run(self, rows: Sequence[dict]) -> CheckResult:
        failed = 0
        for r in rows:
            v = r.get(self.column)
            if v is None:
                continue
            if self.min_value is not None and v < self.min_value:
                failed += 1
            elif self.max_value is not None and v > self.max_value:
                failed += 1
        return self._result(rows, failed,
                            f"expected {self.min_value}..{self.max_value}")


class UniqueCheck(QualityCheck):
    """Fail when ``column`` has duplicate values across the batch."""

    def __init__(self, column: str, **kw) -> None:
        super().__init__(**kw)
        self.column = column

    @property
    def name(self) -> str:
        return f"unique({self.column})"

    def run(self, rows: Sequence[dict]) -> CheckResult:
        seen: set = set()
        dups = 0
        for r in rows:
            key = r.get(self.column)
            if key in seen:
                dups += 1
            seen.add(key)
        return self._result(rows, dups)


class AllowedValuesCheck(QualityCheck):
    """Fail rows where ``column`` is not in the allowed set."""

    def __init__(self, column: str, allowed: Iterable[Any], **kw) -> None:
        super().__init__(**kw)
        self.column = column
        self.allowed = set(allowed)

    @property
    def name(self) -> str:
        return f"allowed_values({self.column})"

    def run(self, rows: Sequence[dict]) -> CheckResult:
        failed = sum(1 for r in rows if r.get(self.column) not in self.allowed)
        return self._result(rows, failed)


class RowCountCheck(QualityCheck):
    """Fail if the batch has fewer than ``min_rows`` (freshness/completeness)."""

    def __init__(self, min_rows: int, **kw) -> None:
        super().__init__(**kw)
        self.min_rows = min_rows

    @property
    def name(self) -> str:
        return f"row_count(>= {self.min_rows})"

    def run(self, rows: Sequence[dict]) -> CheckResult:
        failed = 0 if len(rows) >= self.min_rows else 1
        return self._result(rows, failed, f"got {len(rows)} rows")


@dataclass
class QualityReport:
    total_rows: int
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """The batch passes only if no *error*-severity check failed."""
        return all(r.passed for r in self.results if r.severity == "error")

    def to_dict(self) -> dict:
        return {
            "total_rows": self.total_rows,
            "passed": self.passed,
            "checks": [asdict(r) | {"pass_rate": r.pass_rate} for r in self.results],
        }

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    def pretty(self) -> str:
        lines = [f"Data-quality report - {self.total_rows} rows - "
                 f"{'PASS' if self.passed else 'FAIL'}"]
        for r in self.results:
            mark = "ok " if r.passed else ("ERR" if r.severity == "error" else "warn")
            lines.append(
                f"  [{mark}] {r.name:<28} {r.failed_rows} failed "
                f"({r.pass_rate:.1%} pass)"
            )
        return "\n".join(lines)


class QualitySuite:
    """Runs a list of checks over the rows and aggregates a report."""

    def __init__(self, checks: list[QualityCheck]) -> None:
        self.checks = checks

    def run(self, rows: Sequence[dict]) -> QualityReport:
        report = QualityReport(total_rows=len(rows))
        for check in self.checks:
            report.results.append(check.run(rows))
        return report


def default_coin_suite() -> QualitySuite:
    """The quality contract for the crypto warehouse."""
    return QualitySuite([
        NotNullCheck(["coin_id", "symbol", "name"]),
        RangeCheck("price_usd", min_value=0),
        RangeCheck("change_24h_pct", min_value=-100, max_value=1000, severity="warning"),
        UniqueCheck("coin_id"),
        RowCountCheck(min_rows=5),
    ])
