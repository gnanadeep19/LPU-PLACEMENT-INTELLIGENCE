"""Audit repository datasets for schema, quality, provenance, and leakage risks.

This tool intentionally does not alter source CSV files. It produces a JSON
report and a Markdown summary that must be reviewed before a dataset is used
for training or institutional decisions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "dataset"
REPORT_DIR = ROOT / "reports" / "data-audit"

DATASET_CATALOG: dict[str, dict[str, Any]] = {
    "students.csv": {
        "role": "primary_training_candidate",
        "source_status": "unverified_curated_or_synthetic",
        "target": "placement_ready",
        "permitted_use": "prototype_only_until_provenance_and_label_review",
        "declared_features": [
            "cgpa",
            "technical_score",
            "aptitude_score",
            "communication_score",
            "coding_score",
            "projects",
            "internships",
            "certifications",
            "backlogs",
        ],
    },
    "college_placement_engineering.csv": {
        "role": "external_benchmark_candidate",
        "source_status": "external_source_claim_requires_verification",
        "target": "PlacedOrNot",
        "permitted_use": "external_validation_only_until_license_and_provenance_review",
    },
    "campus_recruitment_kaggle.csv": {
        "role": "external_benchmark_candidate",
        "source_status": "external_source_claim_requires_verification",
        "target": "status",
        "permitted_use": "external_validation_only_until_license_and_provenance_review",
    },
    "job_placement_features.csv": {
        "role": "external_benchmark_candidate",
        "source_status": "external_source_claim_requires_verification",
        "target": "status",
        "permitted_use": "external_validation_only_until_license_and_provenance_review",
    },
    "engineering_skills_placement.csv": {
        "role": "external_benchmark_candidate",
        "source_status": "external_source_claim_requires_verification",
        "target": "placed",
        "permitted_use": "external_validation_only_until_license_and_provenance_review",
    },
    "placement_package_salary.csv": {
        "role": "separate_regression_benchmark",
        "source_status": "external_source_claim_requires_verification",
        "target": "package",
        "permitted_use": "salary_research_only_not_readiness_training",
    },
    "placement_iq_academic.csv": {
        "role": "external_benchmark_candidate",
        "source_status": "external_source_claim_requires_verification",
        "target": "placement",
        "permitted_use": "external_validation_only_until_license_and_provenance_review",
    },
}

RANGE_RULES: dict[str, tuple[float, float]] = {
    "cgpa": (0, 10),
    "CGPA": (0, 10),
    "ssc_p": (0, 100),
    "hsc_p": (0, 100),
    "degree_p": (0, 100),
    "etest_p": (0, 100),
    "mba_p": (0, 100),
    "ssc_percentage": (0, 100),
    "hsc_percentage": (0, 100),
    "degree_percentage": (0, 100),
    "emp_test_percentage": (0, 100),
    "mba_percent": (0, 100),
    "technical_score": (0, 100),
    "aptitude_score": (0, 100),
    "communication_score": (0, 100),
    "coding_score": (0, 100),
    "attendance": (0, 100),
    "iq": (0, 250),
}


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _target_distribution(series: pd.Series) -> dict[str, int]:
    return {str(_json_value(key)): int(value) for key, value in series.value_counts(dropna=False).items()}


def _range_violations(frame: pd.DataFrame) -> dict[str, int]:
    violations: dict[str, int] = {}
    for column, (minimum, maximum) in RANGE_RULES.items():
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        count = int(((values < minimum) | (values > maximum)).sum())
        if count:
            violations[column] = count
    return violations


def _potential_leakage(frame: pd.DataFrame, target: str | None) -> list[str]:
    findings: list[str] = []
    if not target or target not in frame.columns:
        return findings

    normalized_target = re.sub(r"[^a-z0-9]", "", target.lower())
    for column in frame.columns:
        normalized_column = re.sub(r"[^a-z0-9]", "", column.lower())
        if column != target and (
            normalized_target in normalized_column or normalized_column in {"placed", "status", "salary", "package"}
        ):
            findings.append(
                f"Column '{column}' may encode or closely represent target '{target}'; review before training."
            )

    if target in {"status", "PlacedOrNot", "placed", "placement", "placement_ready"}:
        for column in frame.columns:
            if column == target:
                continue
            unique_count = frame[column].nunique(dropna=True)
            if unique_count == len(frame):
                findings.append(
                    f"Column '{column}' is unique for every row; check whether it is an identifier or post-outcome field."
                )
    return findings


def audit_dataset(path: Path) -> dict[str, Any]:
    catalog = DATASET_CATALOG.get(path.name, {})
    frame = pd.read_csv(path)
    target = catalog.get("target")
    missing = {column: int(count) for column, count in frame.isna().sum().items() if count}
    duplicate_rows = int(frame.duplicated().sum())
    target_distribution = (
        _target_distribution(frame[target]) if target and target in frame.columns else None
    )

    return {
        "file": path.name,
        "path": str(path.relative_to(ROOT)),
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)),
        "column_names": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing_values": missing,
        "missing_value_total": int(frame.isna().sum().sum()),
        "duplicate_rows": duplicate_rows,
        "target": target,
        "target_present": bool(target and target in frame.columns),
        "target_distribution": target_distribution,
        "range_violations": _range_violations(frame),
        "potential_leakage": _potential_leakage(frame, target),
        "role": catalog.get("role", "unclassified"),
        "source_status": catalog.get("source_status", "not_cataloged"),
        "permitted_use": catalog.get("permitted_use", "do_not_use_until_review"),
        "declared_features": catalog.get("declared_features"),
        "review_status": "blocked" if missing or duplicate_rows or _range_violations(frame) else "review_required",
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dataset audit report",
        "",
        f"Generated from `{report['root']}`.",
        "",
        "This report is an evidence snapshot, not provenance approval. External source, license, consent, and label claims remain unverified until documented by the data owner.",
        "",
        f"**Datasets:** {report['dataset_count']}  ",
        f"**Rows:** {report['total_rows']}  ",
        f"**Blocking findings:** {report['blocking_finding_count']}",
        "",
        "| Dataset | Rows | Missing | Duplicates | Target | Status | Permitted use |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for item in report["datasets"]:
        lines.append(
            f"| `{item['file']}` | {item['rows']} | {item['missing_value_total']} | "
            f"{item['duplicate_rows']} | `{item['target'] or 'none'}` | {item['review_status']} | "
            f"{item['permitted_use']} |"
        )
    lines.extend(["", "## Blocking findings", ""])
    if not report["blocking_findings"]:
        lines.append("No automated blocking findings were detected.")
    else:
        lines.extend(f"- {finding}" for finding in report["blocking_findings"])
    lines.extend(["", "## Required human review", ""])
    lines.extend(
        [
            "- Verify source, license, collection date, owner, and permitted use for every dataset.",
            "- Document how every target label was collected or generated.",
            "- Confirm that duplicate rows are expected or remove/deduplicate through an approved process.",
            "- Investigate missing values before imputation or exclusion.",
            "- Review every potential leakage finding before model training.",
            "- Do not combine datasets with different populations, feature meanings, or target definitions without a documented mapping.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    datasets = [audit_dataset(path) for path in sorted(DATASET_DIR.glob("*.csv"))]
    blocking_findings: list[str] = []
    for item in datasets:
        if item["missing_value_total"]:
            blocking_findings.append(
                f"{item['file']}: {item['missing_value_total']} missing values require a documented treatment."
            )
        if item["duplicate_rows"]:
            blocking_findings.append(
                f"{item['file']}: {item['duplicate_rows']} duplicate rows require investigation."
            )
        for column, count in item["range_violations"].items():
            blocking_findings.append(
                f"{item['file']}: {count} values violate the configured range for '{column}'."
            )

    report = {
        "schema_version": "1.0",
        "root": str(ROOT),
        "dataset_count": len(datasets),
        "total_rows": sum(item["rows"] for item in datasets),
        "blocking_finding_count": len(blocking_findings),
        "blocking_findings": blocking_findings,
        "datasets": datasets,
    }
    (REPORT_DIR / "dataset_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (REPORT_DIR / "dataset_audit.md").write_text(_render_markdown(report), encoding="utf-8")
    print(f"Audited {len(datasets)} datasets and {report['total_rows']:,} rows.")
    print(f"Blocking findings: {len(blocking_findings)}")
    for finding in blocking_findings:
        print(f"- {finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
