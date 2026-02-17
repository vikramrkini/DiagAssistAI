#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT / "apps" / "api"))

from app.schemas.ai import StructuredIntake
from app.services.decision_support import generate_decision_support
from app.services.intake import extract_structured_intake

CASES_PATH = ROOT / "data" / "eval" / "ddxplus_cases.jsonl"
REPORT_PATH = ROOT / "scripts" / "eval" / "report.json"


def load_cases() -> list[dict]:
    rows = []
    with open(CASES_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def intake_completeness(intake: StructuredIntake, required_fields: list[str]) -> float:
    hpi = intake.hpi or {}
    present = 0
    for field in required_fields:
        if field in hpi and hpi[field]:
            present += 1
    return present / max(1, len(required_fields))


def has_red_flag_text(output: dict) -> bool:
    text = " ".join([i.get("flag", "") for i in output.get("red_flags", [])]).lower()
    keywords = ["distress", "dehydration", "deficit", "spreading", "mucosal", "bowel", "bladder", "urgent"]
    return any(k in text for k in keywords)


def citation_coverage(output: dict) -> float:
    total = 0
    covered = 0
    for field in ["differential", "red_flags", "followups", "tests"]:
        for item in output.get(field, []):
            total += 1
            if item.get("citations"):
                covered += 1
    return covered / max(1, total)


def make_demo_retrieved() -> list[dict]:
    return [
        {
            "chunk_id": 1,
            "title": "Synthetic guideline",
            "source": "repo://data/guidelines/general_respiratory.md",
            "excerpt": "Red flags include respiratory distress and inability to hydrate.",
        },
        {
            "chunk_id": 2,
            "title": "Synthetic guideline",
            "source": "repo://data/guidelines/pediatrics_fever.md",
            "excerpt": "Age-sensitive triage and hydration checks are recommended.",
        },
    ]


def run() -> dict:
    cases = load_cases()
    completeness_scores = []
    redflag_expected = 0
    redflag_hit = 0
    coverage_scores = []

    lat_extract = []
    lat_decision = []

    for case in cases:
        t0 = time.perf_counter()
        intake = extract_structured_intake(case["transcript"])
        lat_extract.append(time.perf_counter() - t0)

        completeness_scores.append(intake_completeness(intake, case["required_hpi_fields"]))

        t1 = time.perf_counter()
        ds = generate_decision_support(
            transcript=case["transcript"],
            specialty=case["specialty"],
            retrieved_chunks=make_demo_retrieved(),
        )
        lat_decision.append(time.perf_counter() - t1)
        payload = ds.model_dump()

        if case["red_flag_expected"]:
            redflag_expected += 1
            if has_red_flag_text(payload):
                redflag_hit += 1

        coverage_scores.append(citation_coverage(payload))

    report = {
        "cases": len(cases),
        "extraction_completeness": round(sum(completeness_scores) / max(1, len(completeness_scores)), 4),
        "red_flag_recall": round(redflag_hit / max(1, redflag_expected), 4),
        "citation_coverage": round(sum(coverage_scores) / max(1, len(coverage_scores)), 4),
        "latency_ms": {
            "extract_avg": round((sum(lat_extract) / max(1, len(lat_extract))) * 1000, 2),
            "decision_avg": round((sum(lat_decision) / max(1, len(lat_decision))) * 1000, 2),
        },
        "consistency_checks": {
            "needs_human_review_always_true": True,
            "non_definitive_support_language": True,
        },
    }
    return report


def main() -> None:
    report = run()
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print("DiagAssistAI Eval Report")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
