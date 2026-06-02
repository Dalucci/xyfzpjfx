# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for, flash, session
from werkzeug.utils import secure_filename

from models.registry import ModelRegistry
from models.rsm import RSMAcademicEvaluator, save_artifacts
from models.subject_models import build_subject_model_context, load_subject_model_config, subject_model_nav
from services.data_service import build_data_quality, load_run_dataset
from services.export_service import export_model_result

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = BASE_DIR / "config" / "indicators.json"
SUBJECT_CONFIG_PATH = BASE_DIR / "config" / "subjects" / "subject_models.json"
MODELS_CATALOG_PATH = BASE_DIR / "config" / "models_catalog.json"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("RSM_APP_SECRET", "local-rsm-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

EVALUATOR = RSMAcademicEvaluator(CONFIG_PATH)
SUBJECT_MODELS = load_subject_model_config(SUBJECT_CONFIG_PATH)
SUBJECT_MODEL_ALIASES = {"english": "foreign"}
MODEL_REGISTRY = ModelRegistry(MODELS_CATALOG_PATH)


def current_run_dir() -> Path | None:
    run_id = session.get("run_id")
    if not run_id:
        return None
    d = OUTPUT_DIR / run_id
    return d if d.exists() else None


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_results(run_dir: Path) -> pd.DataFrame:
    return pd.read_csv(run_dir / "rsm_results.csv", encoding="utf-8-sig")


def subject_nav() -> list[dict[str, str]]:
    return subject_model_nav(SUBJECT_MODELS)


def subject_key_from_name(subject_name: Any) -> str | None:
    subject = str(subject_name)
    for key, item in SUBJECT_MODELS.items():
        if subject in set(item.get("subject_names", [])):
            return key
    return None


def ensure_demo_run() -> Path:
    run_dir = current_run_dir()
    if run_dir:
        return run_dir
    demo_path = DATA_DIR / "demo_students.csv"
    if not demo_path.exists() or len(pd.read_csv(demo_path, encoding="utf-8-sig")) < 180:
        from utils.sample_data import generate_demo_data
        generate_demo_data(demo_path, n=180)
    run_output_dir = OUTPUT_DIR / "demo"
    run_output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = EVALUATOR.analyze_file(demo_path)
    save_artifacts(artifacts, run_output_dir)
    session["run_id"] = "demo"
    return run_output_dir


def current_dataset_or_demo():
    return load_run_dataset(ensure_demo_run())


@app.route("/")
def index():
    run_dir = current_run_dir()
    summary = load_json(run_dir / "summary.json") if run_dir else None
    return render_template("index.html", summary=summary, subject_models=subject_nav())


@app.route("/template")
def template_file():
    template_path = DATA_DIR / "rsm_data_template.csv"
    EVALUATOR.template_dataframe().to_csv(template_path, index=False, encoding="utf-8-sig")
    return send_file(template_path, as_attachment=True, download_name="规则空间模型数据模板.csv")


@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("请先选择 Excel 或 CSV 数据文件。")
        return redirect(url_for("index"))

    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".csv", ".xlsx", ".xls"]:
        flash("文件格式不支持。请上传 .csv、.xlsx 或 .xls。")
        return redirect(url_for("index"))

    run_id = uuid.uuid4().hex[:12]
    run_upload_dir = UPLOAD_DIR / run_id
    run_output_dir = OUTPUT_DIR / run_id
    run_upload_dir.mkdir(parents=True, exist_ok=True)
    run_output_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(file.filename) or f"upload{suffix}"
    upload_path = run_upload_dir / filename
    file.save(upload_path)

    try:
        artifacts = EVALUATOR.analyze_file(upload_path)
        save_artifacts(artifacts, run_output_dir)
        session["run_id"] = run_id
        flash(f"分析完成：共处理 {artifacts.summary['student_count']} 名学生，识别 {artifacts.summary['indicator_count']} 个指标。")
        return redirect(url_for("results"))
    except Exception as exc:
        flash(f"分析失败：{exc}")
        return redirect(url_for("index"))


@app.route("/demo")
def demo():
    ensure_demo_run()
    flash("已加载演示数据，可直接查看规则空间分析效果。")
    return redirect(url_for("results"))


@app.route("/results")
def results():
    run_dir = current_run_dir()
    if not run_dir:
        flash("当前没有分析结果，请先上传数据或加载演示数据。")
        return redirect(url_for("index"))
    summary = load_json(run_dir / "summary.json", {})
    df = load_results(run_dir)
    records = df.head(300).to_dict("records")
    columns = [
        "学号", "姓名", "班级", "学科", "综合评分", "RSM调整分", "学业等级", "发展潜力",
        "规则空间Theta", "规则空间Zeta", "成长动能指数", "学习稳定性指数", "知行耦合指数",
        "风险预警等级", "干预优先级", "学业发展画像", "薄弱属性", "建议摘要"
    ]
    chart_data = {
        "level_counts": summary.get("level_counts", {}),
        "potential_counts": summary.get("potential_counts", {}),
        "risk_counts": summary.get("risk_counts", {}),
        "profile_counts": summary.get("profile_counts", {}),
        "intervention_counts": summary.get("intervention_counts", {}),
        "model_means": summary.get("model_means", {}),
        "model_cards": summary.get("model_cards", []),
        "primary_means": summary.get("primary_means", {}),
        "secondary_means": summary.get("secondary_means", {}),
        "subject_dimension_matrix": summary.get("subject_dimension_matrix", []),
        "class_overview": summary.get("class_overview", []),
        "score_histogram": summary.get("score_histogram", []),
        "top_weak_attributes": summary.get("top_weak_attributes", []),
        "scatter": df[["姓名", "学号", "规则空间Theta", "规则空间Zeta", "学业等级", "风险预警等级"]].to_dict("records"),
        "coupling_scatter": df[["姓名", "学号", "知识点掌握度", "学习行为活跃度", "RSM调整分", "风险预警等级", "学业发展画像"]].to_dict("records")
    }
    return render_template("results.html", summary=summary, records=records, columns=columns, chart_data=chart_data, subject_models=subject_nav())


@app.route("/model/<subject_key>")
def model_subject(subject_key: str):
    subject_key = SUBJECT_MODEL_ALIASES.get(subject_key, subject_key)
    run_dir = current_run_dir()
    if not run_dir:
        flash("请先上传数据或加载演示数据，再查看学科模型子页面。")
        return redirect(url_for("index"))
    summary = load_json(run_dir / "summary.json", {})
    df = load_results(run_dir)
    model_context = build_subject_model_context(df, summary, SUBJECT_MODELS, subject_key)
    if not model_context:
        flash("未找到对应的学科模型。")
        return redirect(url_for("results"))
    return render_template("subject_model.html", model=model_context, subject_models=subject_nav())


@app.route("/models")
def model_center():
    run_dir = current_run_dir()
    summary = load_json(run_dir / "summary.json", {}) if run_dir else None
    data_quality = build_data_quality(load_run_dataset(run_dir)) if run_dir else None
    models = MODEL_REGISTRY.list_models()
    categories = MODEL_REGISTRY.categories()
    return render_template(
        "model_center.html",
        models=models,
        categories=categories,
        summary=summary,
        data_quality=data_quality,
        subject_models=subject_nav(),
    )


@app.route("/models/compare")
def model_compare():
    compare_payload = _build_compare_payload()
    return render_template(
        "model_compare.html",
        compare=compare_payload,
        models=MODEL_REGISTRY.list_models(),
        subject_models=subject_nav(),
    )


@app.route("/models/<model_id>")
def model_detail(model_id: str):
    entry = MODEL_REGISTRY.get_model(model_id)
    if not entry:
        flash("未找到对应模型。")
        return redirect(url_for("model_center"))
    dataset = current_dataset_or_demo()
    result = MODEL_REGISTRY.run_model(model_id, dataset)
    return render_template(
        "model_detail.html",
        model_entry=entry,
        result=result.to_dict(),
        subject_models=subject_nav(),
    )


@app.route("/students/<student_id>")
def student_profile(student_id: str):
    dataset = current_dataset_or_demo()
    df = dataset.results
    row = df[df["学号"].astype(str) == str(student_id)]
    if row.empty:
        flash("未找到该学生。")
        return redirect(url_for("results"))
    student = row.iloc[0].to_dict()
    subject_key = subject_key_from_name(student.get("学科"))
    subject_context = build_subject_model_context(dataset.results, dataset.summary, SUBJECT_MODELS, subject_key) if subject_key else None
    model_ids = ["ahp", "rsm", "weak_knowledge", "trend_regression", "risk_warning", "rule_path_recommendation"]
    model_cards = []
    for model_id in model_ids:
        result = MODEL_REGISTRY.run_model(model_id, dataset)
        detail = result.student_details.get(str(student_id), {})
        model_cards.append(
            {
                "model_id": model_id,
                "model_name": result.model_name,
                "score": detail.get("scores", {}).get("model_score", 0),
                "score_label": detail.get("scores", {}).get("score_label", "模型得分"),
                "diagnosis": detail.get("diagnosis", []),
                "url": url_for("model_detail", model_id=model_id),
            }
        )
    return render_template(
        "student_profile.html",
        student=student,
        detail=dataset.details.get(str(student_id), {}),
        model_cards=model_cards,
        subject_context=subject_context,
        subject_models=subject_nav(),
    )


@app.route("/api/results")
def api_results():
    run_dir = current_run_dir()
    if not run_dir:
        return jsonify({"error": "no analysis"}), 404
    df = load_results(run_dir)
    return jsonify(df.to_dict("records"))


@app.route("/api/models/catalog")
def api_models_catalog():
    return jsonify(MODEL_REGISTRY.list_models())


@app.route("/api/models/<model_id>/run")
def api_run_model(model_id: str):
    try:
        result = MODEL_REGISTRY.run_model(model_id, current_dataset_or_demo())
        return jsonify(result.to_dict())
    except KeyError:
        return jsonify({"error": "model not found"}), 404


@app.route("/api/models/<model_id>/charts")
def api_model_charts(model_id: str):
    try:
        result = MODEL_REGISTRY.run_model(model_id, current_dataset_or_demo())
        return jsonify(result.charts)
    except KeyError:
        return jsonify({"error": "model not found"}), 404


@app.route("/api/models/<model_id>/student/<student_id>")
def api_model_student_detail(model_id: str, student_id: str):
    try:
        result = MODEL_REGISTRY.run_model(model_id, current_dataset_or_demo())
    except KeyError:
        return jsonify({"error": "model not found"}), 404
    detail = result.student_details.get(str(student_id))
    if not detail:
        return jsonify({"error": "student not found"}), 404
    return jsonify(detail)


@app.route("/api/models/<model_id>/export/<fmt>")
@app.route("/api/export/<model_id>/<fmt>")
def api_export_model(model_id: str, fmt: str):
    try:
        dataset = current_dataset_or_demo()
        result = MODEL_REGISTRY.run_model(model_id, dataset)
        path = export_model_result(result, dataset.run_dir, fmt)
        download_name = {
            "csv": f"{result.model_name}_学生明细.csv",
            "json": f"{result.model_name}_模型结果.json",
            "excel": f"{result.model_name}_模型报告.xlsx",
        }.get(fmt.lower(), path.name)
        return send_file(path, as_attachment=True, download_name=download_name)
    except KeyError:
        return jsonify({"error": "model not found"}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/models/compare")
def api_model_compare():
    return jsonify(_build_compare_payload())


@app.route("/api/data/quality")
def api_data_quality():
    return jsonify(build_data_quality(current_dataset_or_demo()))


@app.route("/api/data/summary")
def api_data_summary():
    return jsonify(current_dataset_or_demo().summary)


@app.route("/api/student/<student_id>")
def api_student(student_id: str):
    run_dir = current_run_dir()
    if not run_dir:
        return jsonify({"error": "no analysis"}), 404
    details = load_json(run_dir / "student_details.json", {})
    df = load_results(run_dir)
    row = df[df["学号"].astype(str) == str(student_id)]
    if row.empty:
        return jsonify({"error": "student not found"}), 404
    return jsonify({"result": row.iloc[0].to_dict(), "detail": details.get(str(student_id), {})})


@app.route("/download/<kind>")
def download(kind: str):
    run_dir = current_run_dir()
    if not run_dir:
        flash("当前没有可下载的分析结果。")
        return redirect(url_for("index"))
    mapping = {
        "results": (run_dir / "rsm_results.csv", "规则空间模型评价结果.csv"),
        "normalized": (run_dir / "normalized_data.csv", "标准化数据.csv"),
        "summary": (run_dir / "summary.json", "分析汇总.json"),
        "details": (run_dir / "student_details.json", "学生明细诊断.json"),
        "excel": (run_dir / "rsm_analysis_report.xlsx", "规则空间模型分析报告.xlsx")
    }
    if kind not in mapping or not mapping[kind][0].exists():
        flash("文件不存在。")
        return redirect(url_for("results"))
    return send_file(mapping[kind][0], as_attachment=True, download_name=mapping[kind][1])


@app.route("/config")
def config_view():
    return jsonify(EVALUATOR.config)


def _build_compare_payload() -> Dict[str, Any]:
    dataset = current_dataset_or_demo()
    requested = request.args.get("ids", "ahp,rsm,weak_knowledge,trend_regression,risk_warning,rule_path_recommendation")
    model_ids = [item.strip() for item in requested.split(",") if item.strip()]
    model_rows = []
    for model_id in model_ids:
        if not MODEL_REGISTRY.get_model(model_id):
            continue
        result = MODEL_REGISTRY.run_model(model_id, dataset)
        first_card = result.summary_cards[0] if result.summary_cards else {"label": "模型均分", "value": 0, "unit": ""}
        model_rows.append(
            {
                "model_id": result.model_id,
                "model_name": result.model_name,
                "category": result.category,
                "status": result.status,
                "score_label": first_card.get("label", "模型均分"),
                "mean_score": first_card.get("value", 0),
                "chart_count": len(result.charts),
            }
        )
    return {
        "models": model_rows,
        "student_count": int(len(dataset.results)),
        "data_quality": build_data_quality(dataset),
    }


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
