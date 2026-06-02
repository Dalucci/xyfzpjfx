# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


@dataclass
class RunDataset:
    run_dir: Path
    results: pd.DataFrame
    summary: Dict[str, Any]
    details: Dict[str, Dict[str, Any]]
    normalized: pd.DataFrame


def load_run_dataset(run_dir: str | Path) -> RunDataset:
    run_path = Path(run_dir)
    results = pd.read_csv(run_path / "rsm_results.csv", encoding="utf-8-sig")
    summary = _load_json(run_path / "summary.json", {})
    details = _load_json(run_path / "student_details.json", {})
    normalized_path = run_path / "normalized_data.csv"
    normalized = pd.read_csv(normalized_path, encoding="utf-8-sig") if normalized_path.exists() else pd.DataFrame()
    return RunDataset(run_dir=run_path, results=results, summary=summary, details=details, normalized=normalized)


def build_data_quality(dataset: RunDataset, required_data: List[str] | None = None) -> Dict[str, Any]:
    required_data = required_data or ["student_indicators"]
    available_sources = {"student_indicators": True, "rsm_results": True}
    for name in [
        "item_responses",
        "q_matrix",
        "resource_library",
        "resource_interactions",
        "interventions",
        "exam_records",
        "knowledge_scores",
    ]:
        available_sources[name] = (dataset.run_dir / f"{name}.csv").exists()

    missing_required = [name for name in required_data if not available_sources.get(name, False)]
    results = dataset.results
    normalized = dataset.normalized
    missing_values = int(normalized.isna().sum().sum()) if not normalized.empty else 0
    total_cells = int(normalized.shape[0] * normalized.shape[1]) if not normalized.empty else 0
    missing_ratio = round(missing_values / total_cells * 100, 2) if total_cells else 0.0
    logs = dataset.summary.get("logs", [])
    return {
        "sample_count": int(len(results)),
        "class_count": int(results["班级"].nunique()) if "班级" in results else 0,
        "subject_count": int(results["学科"].nunique()) if "学科" in results else 0,
        "indicator_count": int(dataset.summary.get("indicator_count", 0)),
        "missing_values": missing_values,
        "missing_ratio": missing_ratio,
        "available_sources": available_sources,
        "required_data": required_data,
        "missing_required": missing_required,
        "status": "degraded" if missing_required else "complete",
        "logs": logs,
    }


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
