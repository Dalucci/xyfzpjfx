# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from models.base import BaseEvaluationModel, ModelResult
from models.subject_models import build_subject_model_context, load_subject_model_config
from services.chart_service import (
    bar_chart,
    donut_chart,
    heatmap_chart,
    horizontal_bar_chart,
    line_chart,
    radar_chart,
    scatter_chart,
)
from services.data_service import RunDataset, build_data_quality


CORE_DIMENSIONS = ["成绩波动趋势", "知识点掌握度", "学习行为活跃度"]
RSM_ATTRIBUTES = [
    "基础成绩水平",
    "成绩波动幅度",
    "进步退步幅度",
    "知识点达标率",
    "知识点应用能力",
    "课堂互动行为",
    "作业提交行为",
    "在线学习行为",
    "自主学习行为",
]


class CatalogEvaluationModel(BaseEvaluationModel):
    def run(self, dataset: RunDataset, params: Dict[str, Any] | None = None) -> ModelResult:
        results = dataset.results.copy()
        data_quality = build_data_quality(dataset, self.catalog_entry.get("required_data", ["student_indicators"]))
        score_label, score_series = self._model_score(results)
        status = "degraded" if data_quality["missing_required"] else "ok"
        status_message = self._status_message(data_quality)
        summary_cards = self._summary_cards(results, score_label, score_series, data_quality)
        charts = self._charts(dataset, score_label, score_series)
        student_table = self._student_table(results, score_series)
        student_details = self._student_details(dataset, score_label, score_series)
        recommendations = self._recommendations(results, score_series)
        explanations = self._explanations(status_message, score_label)
        export_payload = {"score_label": score_label, "model_id": self.model_id, "row_count": len(student_table)}
        return ModelResult(
            model_id=self.model_id,
            model_name=self.model_name,
            category=self.category,
            status=status,
            status_message=status_message,
            summary_cards=summary_cards,
            charts=charts,
            student_table=student_table,
            student_details=student_details,
            recommendations=recommendations,
            explanations=explanations,
            data_quality=data_quality,
            export_payload=export_payload,
        )

    def _model_score(self, results: pd.DataFrame) -> tuple[str, pd.Series]:
        column = self.catalog_entry.get("score_column")
        if column and column in results:
            return str(column), pd.to_numeric(results[column], errors="coerce").fillna(0).clip(0, 100)

        model_id = self.model_id
        if model_id in {"risk_warning", "logistic_risk", "anomaly_detection"} and "预警风险指数" in results:
            return "预警风险指数", pd.to_numeric(results["预警风险指数"], errors="coerce").fillna(0).clip(0, 100)
        if model_id in {"trend_regression", "gbdt_potential", "time_series"} and "成长动能指数" in results:
            return "成长动能指数", pd.to_numeric(results["成长动能指数"], errors="coerce").fillna(0).clip(0, 100)
        if model_id in {"kmeans_profile", "hierarchical_cluster", "latent_profile"} and "知行耦合指数" in results:
            return "知行耦合指数", pd.to_numeric(results["知行耦合指数"], errors="coerce").fillna(0).clip(0, 100)
        if model_id in {"weak_knowledge", "cognitive_diagnosis", "irt", "bkt", "dkt_lite"} and "知识点掌握度" in results:
            return "知识点掌握度", pd.to_numeric(results["知识点掌握度"], errors="coerce").fillna(0).clip(0, 100)
        if model_id in {"rule_path_recommendation", "collaborative_filtering", "knowledge_graph"} and "学习行为活跃度" in results:
            return "学习行为活跃度", pd.to_numeric(results["学习行为活跃度"], errors="coerce").fillna(0).clip(0, 100)
        if model_id in {"correlation_analysis", "feature_importance", "explainability"} and "RSM调整分" in results:
            return "RSM调整分", pd.to_numeric(results["RSM调整分"], errors="coerce").fillna(0).clip(0, 100)
        return "综合评分", pd.to_numeric(results.get("综合评分", pd.Series(0, index=results.index)), errors="coerce").fillna(0).clip(0, 100)

    def _status_message(self, data_quality: Dict[str, Any]) -> str:
        if not data_quality["missing_required"]:
            return "当前模型使用已生成的指标宽表与 RSM 结果完整运行。"
        missing = "、".join(data_quality["missing_required"])
        return f"缺少 {missing}，本页采用指标级近似与演示降级逻辑，保证结果可解释且页面不空白。"

    def _summary_cards(
        self,
        results: pd.DataFrame,
        score_label: str,
        score_series: pd.Series,
        data_quality: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        focus_count = int(results["风险预警等级"].isin(["红色预警", "橙色关注"]).sum()) if "风险预警等级" in results else 0
        high_count = int(results["学业等级"].isin(["优秀", "良好"]).sum()) if "学业等级" in results else 0
        high_rate = round(high_count / max(len(results), 1) * 100, 1)
        return [
            {"label": f"平均{score_label}", "value": round(float(score_series.mean()), 2), "unit": "分", "trend": "当前样本"},
            {"label": "优秀/良好占比", "value": high_rate, "unit": "%", "trend": f"{high_count}人"},
            {"label": "重点关注人数", "value": focus_count, "unit": "人", "trend": "红橙预警"},
            {"label": "可用指标数", "value": data_quality["indicator_count"], "unit": "项", "trend": data_quality["status"]},
        ]

    def _charts(self, dataset: RunDataset, score_label: str, score_series: pd.Series) -> List[Dict[str, Any]]:
        results = dataset.results.copy()
        level_counts = dataset.summary.get("level_counts", {})
        risk_counts = dataset.summary.get("risk_counts", {})
        primary_means = {col: _mean(results, col) for col in CORE_DIMENSIONS if col in results}
        weak_items = dataset.summary.get("top_weak_attributes", [])
        top_students = results.assign(_model_score=score_series).sort_values("_model_score", ascending=False).head(12)
        top_labels = [str(x) for x in top_students["姓名"].tolist()] if "姓名" in top_students else []
        top_values = [round(float(x), 2) for x in top_students["_model_score"].tolist()]
        trend_points = _trend_points(score_series, _mean(results, "成长动能指数"), _mean(results, "学习稳定性指数"))
        scatter_points = []
        for _, row in results.head(300).iterrows():
            scatter_points.append(
                {
                    "name": str(row.get("姓名", "")),
                    "x": float(row.get("规则空间Theta", 0)),
                    "y": float(row.get("规则空间Zeta", 0)),
                    "level": str(row.get("学业等级", "")),
                    "risk": str(row.get("风险预警等级", "")),
                }
            )

        charts = [
            bar_chart("model_score_top", f"{score_label}学生排名", top_labels, top_values, "展示当前模型下得分较高学生，便于观察优势样本。"),
            radar_chart(
                "model_core_radar",
                "三类核心维度结构",
                list(primary_means.keys()),
                list(primary_means.values()),
                "三类一级指标越均衡，说明学生群体发展结构越稳定。",
            ),
            donut_chart("model_level_distribution", "学业等级分布", level_counts, "用于观察不同等级学生的人数结构。"),
            scatter_chart("model_rsm_scatter", "Theta-Zeta规则空间分布", scatter_points, "规则空间Theta", "规则空间Zeta", "右侧表示属性掌握较高，下方表示偏离度较低。"),
            horizontal_bar_chart("model_weak_attributes", "薄弱属性优先级", weak_items, "未掌握率越高，越应优先进入集体讲评或专项训练。"),
            line_chart("model_trend_projection", "阶段发展趋势推导", trend_points, "基于当前均分、成长动能和稳定性生成的可解释趋势线。"),
            donut_chart("model_risk_distribution", "风险预警结构", risk_counts, "红橙预警学生需要优先查看个体诊断和干预建议。"),
        ]
        matrix = dataset.summary.get("subject_dimension_matrix", [])
        if matrix:
            charts.append(
                heatmap_chart("model_subject_heatmap", "学科-核心维度热力图", matrix, CORE_DIMENSIONS, "观察各学科在成绩、知识和行为三类维度上的差异。")
            )
        return charts

    def _student_table(self, results: pd.DataFrame, score_series: pd.Series) -> List[Dict[str, Any]]:
        rows = []
        ordered = results.assign(_model_score=score_series).sort_values(["_model_score"], ascending=False)
        for _, row in ordered.head(300).iterrows():
            rows.append(
                {
                    "student_id": str(row.get("学号", "")),
                    "name": str(row.get("姓名", "")),
                    "class_name": str(row.get("班级", "")),
                    "subject": str(row.get("学科", "")),
                    "score": round(float(row.get("_model_score", 0)), 2),
                    "level": str(row.get("学业等级", "")),
                    "risk_level": str(row.get("风险预警等级", "")),
                    "weak_points": str(row.get("薄弱属性", "")),
                    "recommendation": str(row.get("建议摘要", "")),
                }
            )
        return rows

    def _student_details(self, dataset: RunDataset, score_label: str, score_series: pd.Series) -> Dict[str, Dict[str, Any]]:
        details: Dict[str, Dict[str, Any]] = {}
        results = dataset.results.assign(_model_score=score_series)
        for _, row in results.head(300).iterrows():
            student_id = str(row.get("学号", ""))
            raw_detail = dataset.details.get(student_id, {})
            weak_points = str(row.get("薄弱属性", "暂无明显薄弱项"))
            details[student_id] = {
                "basic": {
                    "name": str(row.get("姓名", "")),
                    "class_name": str(row.get("班级", "")),
                    "subject": str(row.get("学科", "")),
                },
                "scores": {
                    "model_score": round(float(row.get("_model_score", 0)), 2),
                    "score_label": score_label,
                    "overall": _safe(row.get("综合评分")),
                    "rsm": _safe(row.get("RSM调整分")),
                    "theta": _safe(row.get("规则空间Theta")),
                    "zeta": _safe(row.get("规则空间Zeta")),
                },
                "diagnosis": [
                    f"{score_label}为 {round(float(row.get('_model_score', 0)), 2)} 分，学业等级为 {row.get('学业等级', '')}。",
                    f"主要薄弱项：{weak_points}。",
                    f"风险状态：{row.get('风险预警等级', '')}，干预优先级：{row.get('干预优先级', '')}。",
                ],
                "charts": [],
                "recommendations": str(row.get("建议摘要", "")).split("；"),
                "rsm_detail": raw_detail,
            }
        return details

    def _recommendations(self, results: pd.DataFrame, score_series: pd.Series) -> List[Dict[str, Any]]:
        focus = results.assign(_model_score=score_series).sort_values(["预警风险指数", "_model_score"], ascending=[False, True]).head(8)
        rows = []
        for _, row in focus.iterrows():
            rows.append(
                {
                    "student_id": str(row.get("学号", "")),
                    "name": str(row.get("姓名", "")),
                    "priority": str(row.get("干预优先级", "")),
                    "reason": str(row.get("薄弱属性", "")),
                    "suggestion": str(row.get("建议摘要", "")),
                }
            )
        return rows

    def _explanations(self, status_message: str, score_label: str) -> List[Dict[str, str]]:
        return [
            {
                "title": "模型思想",
                "body": self.catalog_entry.get("description", "基于学生指标宽表生成可解释的学业发展评价结果。"),
            },
            {
                "title": "当前计算方式",
                "body": f"本页以 {score_label} 作为核心输出，并结合等级、风险、薄弱属性和建议摘要形成统一诊断视图。",
            },
            {
                "title": "运行状态",
                "body": status_message,
            },
        ]


class AHPEvaluationModel(CatalogEvaluationModel):
    def _model_score(self, results: pd.DataFrame) -> tuple[str, pd.Series]:
        return "AHP综合评分", pd.to_numeric(results.get("综合评分", pd.Series(0, index=results.index)), errors="coerce").fillna(0).clip(0, 100)


class RSMDiagnosticModel(CatalogEvaluationModel):
    def _model_score(self, results: pd.DataFrame) -> tuple[str, pd.Series]:
        return "RSM调整分", pd.to_numeric(results.get("RSM调整分", pd.Series(0, index=results.index)), errors="coerce").fillna(0).clip(0, 100)


class SubjectEvaluationModel(CatalogEvaluationModel):
    def run(self, dataset: RunDataset, params: Dict[str, Any] | None = None) -> ModelResult:
        config_path = self.catalog_entry.get("subject_config_path")
        subject_key = self.catalog_entry.get("subject_key")
        if not config_path or not subject_key:
            return super().run(dataset, params)
        subject_config = load_subject_model_config(config_path)
        context = build_subject_model_context(dataset.results, dataset.summary, subject_config, str(subject_key))
        if not context:
            return super().run(dataset, params)

        module_means = context.get("module_means", {})
        literacy_means = context.get("literacy_means", {})
        competency_means = context.get("competency_means", {})
        model_suite = context.get("model_suite", {})
        chart_data = context.get("chart_data", {})
        quality = build_data_quality(dataset, self.catalog_entry.get("required_data", ["student_indicators"]))
        status = "ok" if context.get("student_count", 0) else "degraded"
        charts = [
            radar_chart(
                "subject_literacy_radar",
                f"{context['short_name']}核心素养雷达图",
                list(literacy_means.keys()) or list(module_means.keys()),
                list(literacy_means.values()) or list(module_means.values()),
                "展示该学科课程标准核心素养维度的平均发展水平。",
            ),
            radar_chart(
                "subject_ability_radar",
                f"{context['short_name']}二级指标雷达图",
                list(module_means.keys()),
                list(module_means.values()),
                "展示优化二级指标的平均掌握结构。",
            ),
            bar_chart(
                "subject_competency_bar",
                f"{context['short_name']}权重维度得分",
                list(competency_means.keys()),
                list(competency_means.values()),
                "按知识技能、过程方法、态度价值等权重维度汇总学科评价结果。",
            ),
            bar_chart(
                "subject_score_bar",
                f"{context['short_name']}学生得分排行",
                list(chart_data.get("student_scores", {}).keys()),
                list(chart_data.get("student_scores", {}).values()),
                "展示该学科模型下当前样本中的高分学生。",
            ),
            line_chart(
                "subject_trend_line",
                f"{context['short_name']}阶段趋势推导",
                chart_data.get("trend_line", []),
                "基于进步幅度和稳定性生成该学科阶段发展趋势。",
            ),
            horizontal_bar_chart(
                "subject_weak_modules",
                f"{context['short_name']}薄弱模块",
                chart_data.get("weak_modules", []),
                "平均分较低或未达标比例较高的模块优先安排专项训练。",
            ),
            heatmap_chart(
                "subject_literacy_heatmap",
                f"{context['short_name']}班级核心素养热力图",
                chart_data.get("literacy_heatmap", []),
                chart_data.get("literacy_dimensions", []),
                "按班级观察核心素养维度差异，颜色越深表示均分越高。",
            ),
            bar_chart(
                "subject_model_suite_bar",
                f"{context['short_name']}多模型运行概览",
                list(model_suite.keys()),
                list(model_suite.values()),
                "将RSM、AHP、薄弱诊断、趋势预测、画像、知识追踪、路径推荐和解释模型放在同一尺度展示。",
            ),
            donut_chart(
                "subject_level_distribution",
                f"{context['short_name']}等级分布",
                chart_data.get("level_counts", {}),
                "显示该学科样本学生的等级结构。",
            ),
            donut_chart(
                "subject_risk_distribution",
                f"{context['short_name']}风险结构",
                chart_data.get("risk_counts", {}),
                "显示该学科样本的风险预警结构。",
            ),
        ]

        student_table = []
        subject_names = set(subject_config[str(subject_key)].get("subject_names", []))
        subject_df = dataset.results[dataset.results["学科"].astype(str).isin(subject_names)].copy()
        if subject_df.empty:
            subject_df = dataset.results.copy()
        subject_df = subject_df.sort_values("RSM调整分", ascending=False)
        for _, row in subject_df.head(300).iterrows():
            recommendation = _subject_specific_recommendation(row, context)
            student_table.append(
                {
                    "student_id": str(row.get("学号", "")),
                    "name": str(row.get("姓名", "")),
                    "class_name": str(row.get("班级", "")),
                    "subject": str(row.get("学科", "")),
                    "score": _safe(row.get("RSM调整分")),
                    "level": str(row.get("学业等级", "")),
                    "risk_level": str(row.get("风险预警等级", "")),
                    "weak_points": str(row.get("薄弱属性", "")),
                    "recommendation": recommendation,
                    "level_comment": _subject_level_comment(row, context),
                }
            )
        details = {
            row["student_id"]: {
                "basic": {"name": row["name"], "class_name": row["class_name"], "subject": row["subject"]},
                "scores": {"model_score": row["score"], "score_label": f"{context['short_name']}RSM调整分"},
                "diagnosis": [
                    f"{context['short_name']}模型得分为 {row['score']} 分，学业等级为 {row['level']}。",
                    row["level_comment"] or f"{context['short_name']}模型重点关注核心素养结构和阶段发展稳定性。",
                    f"薄弱属性：{row['weak_points']}；风险状态：{row['risk_level']}。",
                ],
                "charts": [],
                "recommendations": _split_recommendation(row["recommendation"]),
            }
            for row in student_table
        }
        recommendations = [
            {
                "student_id": str(row.get("学号", "")),
                "name": str(row.get("姓名", "")),
                "priority": str(row.get("风险预警等级", "")),
                "reason": str(row.get("薄弱属性", "")),
                "suggestion": _subject_specific_recommendation(row, context),
            }
            for row in context.get("focus_students", [])
        ]
        explanations = [
            {"title": "学科评价重点", "body": context.get("evaluation_focus", "") or context.get("focus_text", "")},
            {"title": "学科核心素养", "body": "、".join(context.get("core_literacies", [])) or context.get("focus_text", "")},
            {"title": "优化二级指标", "body": "、".join(context.get("core_indicators", []))},
            {"title": "权重设计", "body": "；".join([f"{k} {round(v * 100)}%" for k, v in context.get("competency_weights", {}).items()])},
            {"title": "分层评价用语", "body": _format_level_comments(context.get("level_comments", {}))},
            {"title": "运行说明", "body": "当前使用通用 RSM 属性映射学科核心素养；题目级数据、Q矩阵和资源交互数据接入后可升级为完整认知诊断、知识追踪和路径推荐模型。"},
        ]
        summary_cards = [
            {"label": "样本数", "value": context.get("student_count", 0), "unit": "人", "trend": context["short_name"]},
            {"label": "核心素养均分", "value": context.get("literacy_mean", 0), "unit": "分", "trend": "课程标准"},
            {"label": "权重综合", "value": context.get("competency_weighted_score", 0), "unit": "分", "trend": "学科权重"},
            {"label": "RSM均分", "value": context.get("rsm_mean", 0), "unit": "分", "trend": "规则空间"},
            {"label": "成长动能", "value": context.get("growth_mean", 0), "unit": "分", "trend": "发展潜力"},
        ]
        return ModelResult(
            model_id=self.model_id,
            model_name=self.model_name,
            category=self.category,
            status=status,
            status_message="学科专项模型已基于当前演示或上传数据运行。",
            summary_cards=summary_cards,
            charts=charts,
            student_table=student_table,
            student_details=details,
            recommendations=recommendations,
            explanations=explanations,
            data_quality=quality,
            export_payload={
                "subject_key": subject_key,
                "row_count": len(student_table),
                "core_literacies": context.get("core_literacies", []),
                "competency_weights": context.get("competency_weights", {}),
                "model_suite": model_suite,
            },
        )


def _subject_level_comment(row: Dict[str, Any] | pd.Series, context: Dict[str, Any]) -> str:
    level = str(row.get("学业等级", "") or row.get("level", ""))
    return str(context.get("level_comments", {}).get(level, ""))


def _subject_specific_recommendation(row: Dict[str, Any] | pd.Series, context: Dict[str, Any]) -> str:
    level_comment = _subject_level_comment(row, context)
    attribute_suggestions = context.get("attribute_suggestions", {})
    weak_text = str(row.get("薄弱属性", "") or row.get("weak_points", ""))
    pieces = []
    if level_comment:
        pieces.append(level_comment)

    normalized = weak_text.replace(",", "、").replace("，", "、").replace("/", "、")
    weak_attributes = [item.strip() for item in normalized.split("、") if item.strip()]
    for attribute in weak_attributes[:3]:
        suggestion = attribute_suggestions.get(attribute)
        if suggestion:
            pieces.append(f"{attribute}：{suggestion}")

    if pieces:
        return "；".join(pieces)

    raw = str(row.get("建议摘要", "") or row.get("recommendation", "")).strip()
    if raw:
        return raw
    return f"结合{context.get('short_name', '本学科')}核心素养开展模块化巩固、错题复盘和阶段跟踪。"


def _split_recommendation(text: str) -> List[str]:
    parts = [part.strip(" 。") for part in str(text).replace("\n", "；").split("；") if part.strip(" 。")]
    return parts or ["结合当前薄弱项安排专项练习、课堂反馈和阶段复测。"]


def _format_level_comments(level_comments: Dict[str, str]) -> str:
    if not level_comments:
        return "按优秀、良好、中等、待提高、需帮扶分层生成学科化评价用语。"
    return "；".join([f"{level}：{comment}" for level, comment in level_comments.items()])


def _mean(df: pd.DataFrame, column: str) -> float:
    if column not in df or df.empty:
        return 0.0
    return round(float(pd.to_numeric(df[column], errors="coerce").fillna(0).mean()), 2)


def _safe(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return round(float(value), 2)
    except Exception:
        return 0.0


def _trend_points(score_series: pd.Series, growth_mean: float, stability_mean: float) -> List[Dict[str, Any]]:
    current = float(score_series.mean()) if len(score_series) else 0.0
    growth_delta = (growth_mean - 50) * 0.18
    stability_delta = max(0, stability_mean - 50) * 0.06
    values = [
        ("入学基线", current - growth_delta * 2.4),
        ("阶段一", current - growth_delta * 1.4),
        ("阶段二", current - growth_delta * 0.6),
        ("最近表现", current),
        ("目标预测", current + max(growth_delta, 0) + stability_delta),
    ]
    return [{"stage": label, "value": round(float(np.clip(value, 0, 100)), 2)} for label, value in values]
