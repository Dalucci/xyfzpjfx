# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from models.base import ModelResult


def export_model_result(result: ModelResult, output_dir: str | Path, fmt: str) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{result.model_id}_{timestamp}"
    fmt = fmt.lower()

    if fmt == "json":
        path = output_path / f"{stem}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    if fmt == "csv":
        path = output_path / f"{stem}.csv"
        pd.DataFrame(result.student_table).to_csv(path, index=False, encoding="utf-8-sig")
        return path

    if fmt == "excel":
        path = output_path / f"{stem}.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(result.summary_cards).to_excel(writer, index=False, sheet_name="模型概览")
            pd.DataFrame(result.student_table).to_excel(writer, index=False, sheet_name="学生明细")
            pd.DataFrame(_chart_rows(result)).to_excel(writer, index=False, sheet_name="图表数据")
            pd.DataFrame(result.recommendations).to_excel(writer, index=False, sheet_name="个体建议")
            pd.DataFrame([_flat_quality(result.data_quality)]).to_excel(writer, index=False, sheet_name="数据质量")
        return path

    raise ValueError("仅支持 csv、excel、json 导出。")


def _chart_rows(result: ModelResult) -> list[Dict[str, Any]]:
    rows = []
    for chart in result.charts:
        rows.append(
            {
                "chart_id": chart.get("chart_id"),
                "title": chart.get("title"),
                "type": chart.get("type"),
                "description": chart.get("description"),
            }
        )
    return rows


def _flat_quality(data_quality: Dict[str, Any]) -> Dict[str, Any]:
    flat = dict(data_quality)
    for key, value in list(flat.items()):
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, ensure_ascii=False)
    return flat
