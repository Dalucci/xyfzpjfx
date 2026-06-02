# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from models.rsm import RSMAcademicEvaluator
from models.subject_models import build_subject_model_context, load_subject_model_config
from utils.sample_data import generate_demo_data


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "indicators.json"

REQUIRED_OUTPUT_COLUMNS = {
    "学号",
    "姓名",
    "班级",
    "学科",
    "综合评分",
    "RSM调整分",
    "学业等级",
    "发展潜力",
    "规则空间Theta",
    "规则空间Zeta",
    "最近理想状态",
    "成长动能指数",
    "学习稳定性指数",
    "知行耦合指数",
    "预警风险指数",
    "风险预警等级",
    "学业发展画像",
    "干预优先级",
    "薄弱属性",
    "建议摘要",
}


def test_demo_data_can_be_analyzed(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo_students.csv"
    generate_demo_data(demo_path, n=24)

    evaluator = RSMAcademicEvaluator(CONFIG_PATH)
    artifacts = evaluator.analyze_file(demo_path)

    assert artifacts.summary["student_count"] == 24
    assert artifacts.summary["indicator_count"] == 35
    assert REQUIRED_OUTPUT_COLUMNS.issubset(set(artifacts.results.columns))
    assert len(artifacts.details) == 24
    assert artifacts.results["RSM调整分"].between(0, 100).all()
    assert artifacts.results["规则空间Theta"].between(0, 100).all()
    assert artifacts.results["规则空间Zeta"].between(0, 100).all()
    assert artifacts.results["成长动能指数"].between(0, 100).all()
    assert artifacts.results["学习稳定性指数"].between(0, 100).all()
    assert artifacts.results["知行耦合指数"].between(0, 100).all()
    assert artifacts.results["预警风险指数"].between(0, 100).all()
    assert artifacts.summary["model_cards"]
    assert artifacts.summary["risk_counts"]
    assert artifacts.summary["profile_counts"]
    assert artifacts.summary["subject_dimension_matrix"]
    assert artifacts.summary["score_histogram"]


def test_aliases_partial_indicators_missing_values_and_outliers_are_supported() -> None:
    df = pd.DataFrame(
        {
            "student_id": ["A001", "A002", "A003"],
            "name": ["测试学生1", "测试学生2", "测试学生3"],
            "class": ["一班", "一班", "二班"],
            "subject": ["数学", "数学", "数学"],
            "score": [92, 110, None],
            "avg_score": [88, 72, 65],
            "overall_score": [90, 75, -5],
            "trend_slope": [12, 150, -12],
            "chapter_accuracy": [85, None, 55],
            "comprehensive_accuracy": [78, 62, 48],
            "speak_count": [8, -1, 2],
            "homework_on_time_rate": [95, 80, None],
            "unused_column": ["保留但不参与模型", "x", "y"],
        }
    )

    evaluator = RSMAcademicEvaluator(CONFIG_PATH)
    artifacts = evaluator.analyze_dataframe(df)

    assert artifacts.summary["student_count"] == 3
    assert artifacts.summary["indicator_count"] == 8
    assert REQUIRED_OUTPUT_COLUMNS.issubset(set(artifacts.results.columns))
    assert "Z_期中期末各科成绩" in artifacts.normalized.columns
    assert "字段识别" in artifacts.summary["logs"][0]
    assert artifacts.normalized["期中期末各科成绩"].between(0, 100).all()
    assert artifacts.normalized["成绩趋势斜率"].between(0, 100).all()
    assert "advanced_models" in next(iter(artifacts.details.values()))


def test_no_indicator_columns_raises_clear_error() -> None:
    evaluator = RSMAcademicEvaluator(CONFIG_PATH)
    df = pd.DataFrame({"姓名": ["测试学生1"], "班级": ["一班"]})

    with pytest.raises(ValueError, match="未识别到任何评价指标字段"):
        evaluator.analyze_dataframe(df)


def test_rule_space_ideal_states_respect_prerequisites() -> None:
    evaluator = RSMAcademicEvaluator(CONFIG_PATH)

    assert evaluator.ideal_states
    for state in evaluator.ideal_states:
        vector = state["vector"]
        if vector["知识点应用能力"] == 1:
            assert vector["知识点达标率"] == 1
        if vector["进步退步幅度"] == 1:
            assert vector["基础成绩水平"] == 1 or vector["知识点达标率"] == 1
        if vector["自主学习行为"] == 1:
            assert vector["在线学习行为"] == 1 or vector["作业提交行为"] == 1


def test_subject_model_contexts_can_be_built(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo_students.csv"
    generate_demo_data(demo_path, n=90)
    evaluator = RSMAcademicEvaluator(CONFIG_PATH)
    artifacts = evaluator.analyze_file(demo_path)
    subject_config = load_subject_model_config(BASE_DIR / "config" / "subjects" / "subject_models.json")

    expected_order = ["chinese", "math", "foreign", "physics", "chemistry", "bio", "history", "geography", "politics"]
    assert list(subject_config.keys()) == expected_order

    for subject_key in expected_order:
        context = build_subject_model_context(artifacts.results, artifacts.summary, subject_config, subject_key)
        assert context is not None
        assert context["student_count"] > 0
        assert context["core_literacies"]
        assert context["evaluation_focus"]
        assert context["level_comments"]
        assert context["attribute_suggestions"]
        assert context["competency_weights"]
        assert context["module_means"]
        assert context["literacy_means"]
        assert context["competency_means"]
        assert context["model_suite"]
        assert context["weak_modules"]
        assert context["chart_data"]["literacy_heatmap"]
        assert context["chart_data"]["trend_line"]
