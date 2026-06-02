# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd


def load_subject_model_config(path: str | Path) -> Dict[str, Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def subject_model_nav(config: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {
            "key": key,
            "display_name": item["display_name"],
            "short_name": item.get("short_name", item["display_name"]),
            "theme": item.get("theme", "#2563eb"),
        }
        for key, item in config.items()
    ]


def build_subject_model_context(
    df: pd.DataFrame,
    summary: Dict[str, Any],
    config: Dict[str, Dict[str, Any]],
    subject_key: str,
) -> Dict[str, Any] | None:
    model = config.get(subject_key)
    if not model:
        return None

    subject_names = set(model.get("subject_names", []))
    subject_df = df[df["学科"].astype(str).isin(subject_names)].copy() if subject_names else df.copy()
    if subject_df.empty:
        subject_df = df.copy()

    module_scores = _compute_module_scores(subject_df, model.get("modules", []))
    module_means = {col: round(float(module_scores[col].mean()), 2) for col in module_scores.columns}
    literacy_scores = _compute_mapped_scores(subject_df, module_scores, model.get("literacies", []))
    literacy_means = {col: round(float(literacy_scores[col].mean()), 2) for col in literacy_scores.columns}
    competency_scores = _competency_scores(module_scores, model.get("competency_groups", {}))
    competency_means = {col: round(float(competency_scores[col].mean()), 2) for col in competency_scores.columns}
    competency_weighted_score = _weighted_dict_score(competency_means, model.get("competency_weights", {}))
    weak_modules = _weak_modules(module_scores, model.get("suggestions", {}))
    student_scores = _student_scores(subject_df)
    trend_line = _trend_line(subject_df)
    focus_students = _focus_students(subject_df)
    risk_counts = _ordered_counts(subject_df, "风险预警等级", ["红色预警", "橙色关注", "黄色观察", "正常"])
    level_counts = _ordered_counts(subject_df, "学业等级", ["优秀", "良好", "中等", "待提高", "需帮扶"])
    literacy_heatmap = _literacy_heatmap(subject_df, module_scores, model.get("literacies", []))
    model_suite = _model_suite(subject_df, module_scores, literacy_scores)

    return {
        "key": subject_key,
        "display_name": model["display_name"],
        "short_name": model.get("short_name", model["display_name"]),
        "theme": model.get("theme", "#2563eb"),
        "focus_text": model.get("focus_text", ""),
        "evaluation_focus": model.get("evaluation_focus", ""),
        "inputs": model.get("inputs", []),
        "core_literacies": model.get("core_literacies", []),
        "core_indicators": model.get("core_indicators", []),
        "level_comments": model.get("level_comments", {}),
        "attribute_suggestions": model.get("attribute_suggestions", {}),
        "competency_weights": model.get("competency_weights", {}),
        "competency_groups": model.get("competency_groups", {}),
        "student_count": int(len(subject_df)),
        "overall_mean": _mean(subject_df, "综合评分"),
        "rsm_mean": _mean(subject_df, "RSM调整分"),
        "growth_mean": _mean(subject_df, "成长动能指数"),
        "risk_mean": _mean(subject_df, "预警风险指数"),
        "literacy_mean": round(float(np.mean(list(literacy_means.values()))), 2) if literacy_means else 0.0,
        "competency_weighted_score": competency_weighted_score,
        "module_means": module_means,
        "literacy_means": literacy_means,
        "competency_means": competency_means,
        "model_suite": model_suite,
        "weak_modules": weak_modules,
        "focus_students": focus_students,
        "summary": summary,
        "chart_data": {
            "module_means": module_means,
            "literacy_means": literacy_means,
            "competency_means": competency_means,
            "competency_weights": model.get("competency_weights", {}),
            "model_suite": model_suite,
            "literacy_heatmap": literacy_heatmap,
            "literacy_dimensions": list(literacy_means.keys()),
            "student_scores": student_scores,
            "trend_line": trend_line,
            "weak_modules": weak_modules,
            "risk_counts": risk_counts,
            "level_counts": level_counts,
        },
    }


def _compute_module_scores(df: pd.DataFrame, modules: List[Dict[str, Any]]) -> pd.DataFrame:
    scores = pd.DataFrame(index=df.index)
    for module in modules:
        pieces: List[pd.Series] = []
        weights: List[float] = []
        for column, weight in module.get("weights", {}).items():
            if column in df.columns:
                pieces.append(pd.to_numeric(df[column], errors="coerce").fillna(50))
                weights.append(float(weight))
        if pieces:
            total = sum(weights) or 1.0
            value = sum(piece * weight for piece, weight in zip(pieces, weights)) / total
            scores[module["name"]] = value.clip(0, 100).round(2)
        else:
            scores[module["name"]] = 50.0
    return scores


def _compute_mapped_scores(
    df: pd.DataFrame,
    module_scores: pd.DataFrame,
    mappings: List[Dict[str, Any]],
) -> pd.DataFrame:
    scores = pd.DataFrame(index=df.index)
    for item in mappings:
        pieces: List[pd.Series] = []
        weights: List[float] = []
        for column, weight in item.get("weights", {}).items():
            series = _source_series(df, module_scores, column)
            if series is not None:
                pieces.append(series)
                weights.append(float(weight))
        if pieces:
            total = sum(weights) or 1.0
            value = sum(piece * weight for piece, weight in zip(pieces, weights)) / total
            scores[item["name"]] = value.clip(0, 100).round(2)
        else:
            scores[item["name"]] = 50.0
    return scores


def _source_series(df: pd.DataFrame, module_scores: pd.DataFrame, column: str) -> pd.Series | None:
    if column in module_scores.columns:
        return pd.to_numeric(module_scores[column], errors="coerce").fillna(50)
    if column in df.columns:
        return pd.to_numeric(df[column], errors="coerce").fillna(50)
    return None


def _competency_scores(module_scores: pd.DataFrame, groups: Dict[str, List[str]]) -> pd.DataFrame:
    scores = pd.DataFrame(index=module_scores.index)
    for name, columns in groups.items():
        pieces = [pd.to_numeric(module_scores[col], errors="coerce").fillna(50) for col in columns if col in module_scores]
        if pieces:
            scores[name] = (sum(pieces) / len(pieces)).clip(0, 100).round(2)
        else:
            scores[name] = 50.0
    return scores


def _weighted_dict_score(values: Dict[str, float], weights: Dict[str, float]) -> float:
    if not values:
        return 0.0
    total = 0.0
    weight_sum = 0.0
    for name, value in values.items():
        weight = float(weights.get(name, 1.0))
        total += float(value) * weight
        weight_sum += weight
    return round(total / (weight_sum or 1.0), 2)


def _literacy_heatmap(
    df: pd.DataFrame,
    module_scores: pd.DataFrame,
    mappings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if df.empty or not mappings:
        return []
    rows = []
    if "班级" in df:
        groups = df.groupby("班级")
    else:
        groups = [("整体", df)]
    for class_name, group in groups:
        scoped_modules = module_scores.loc[group.index]
        scoped_literacy = _compute_mapped_scores(group, scoped_modules, mappings)
        row = {"学科": str(class_name)}
        for column in scoped_literacy.columns:
            row[column] = round(float(scoped_literacy[column].mean()), 2)
        rows.append(row)
    return sorted(rows, key=lambda item: str(item["学科"]))


def _model_suite(df: pd.DataFrame, module_scores: pd.DataFrame, literacy_scores: pd.DataFrame) -> Dict[str, float]:
    literacy_mean = float(literacy_scores.mean().mean()) if not literacy_scores.empty else 0.0
    weak_repair = float((module_scores >= 60).mean().mean() * 100) if not module_scores.empty else 0.0
    trend_prediction = _trend_line(df)[-1]["value"] if len(df) else 0.0
    risk_reverse = 100 - _mean(df, "预警风险指数")
    return {
        "AHP综合评价": _mean(df, "综合评分"),
        "RSM素养诊断": _mean(df, "RSM调整分"),
        "薄弱知识点诊断": round(weak_repair, 2),
        "趋势预测": round(float(trend_prediction), 2),
        "聚类画像": _mean(df, "知行耦合指数"),
        "知识追踪": round(literacy_mean, 2),
        "路径推荐适配": round(float(np.clip(risk_reverse, 0, 100)), 2),
        "特征贡献解释": round(float(np.clip((literacy_mean + _mean(df, "规则空间Theta")) / 2, 0, 100)), 2),
    }


def _weak_modules(module_scores: pd.DataFrame, suggestions: Dict[str, str]) -> List[Dict[str, Any]]:
    rows = []
    if module_scores.empty:
        return rows
    for column in module_scores.columns:
        series = module_scores[column]
        rows.append(
            {
                "attribute": column,
                "module": column,
                "avg_score": round(float(series.mean()), 2),
                "unmastered_rate": round(float((series < 60).mean() * 100), 2),
                "suggestion": suggestions.get(column, "围绕该模块安排诊断练习、错题复盘和阶段性跟踪。"),
            }
        )
    return sorted(rows, key=lambda item: (item["avg_score"], -item["unmastered_rate"]))[:5]


def _student_scores(df: pd.DataFrame) -> Dict[str, float]:
    if df.empty or "RSM调整分" not in df:
        return {}
    top = df.sort_values("RSM调整分", ascending=False).head(12)
    return {str(row["姓名"]): round(float(row["RSM调整分"]), 2) for _, row in top.iterrows()}


def _trend_line(df: pd.DataFrame) -> List[Dict[str, Any]]:
    current = _mean(df, "RSM调整分")
    progress = _mean(df, "进步退步幅度") - 50
    stability = _mean(df, "学习稳定性指数")
    volatility_penalty = max(0, 60 - stability) * 0.08
    points = [
        ("入学基线", current - progress * 0.80 - volatility_penalty),
        ("阶段一", current - progress * 0.45),
        ("阶段二", current - progress * 0.18),
        ("最近表现", current),
        ("目标预测", current + max(progress, 0) * 0.35 + max(0, stability - 55) * 0.08),
    ]
    return [{"stage": label, "value": round(float(np.clip(value, 0, 100)), 2)} for label, value in points]


def _focus_students(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df.empty:
        return []
    cols = ["学号", "姓名", "班级", "RSM调整分", "学业等级", "风险预警等级", "薄弱属性", "建议摘要"]
    available = [col for col in cols if col in df.columns]
    focus = df.sort_values(["预警风险指数", "RSM调整分"], ascending=[False, True]).head(8)
    return focus[available].to_dict("records")


def _ordered_counts(df: pd.DataFrame, column: str, order: List[str]) -> Dict[str, int]:
    if column not in df:
        return {}
    return df[column].value_counts().reindex(order, fill_value=0).to_dict()


def _mean(df: pd.DataFrame, column: str) -> float:
    if column not in df or df.empty:
        return 0.0
    return round(float(pd.to_numeric(df[column], errors="coerce").mean()), 2)
