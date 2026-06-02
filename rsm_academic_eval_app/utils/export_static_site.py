# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = BASE_DIR / "site"
DEFAULT_DATA_PATH = BASE_DIR / "data" / "synthetic_5000_students.csv"
sys.path.insert(0, str(BASE_DIR))

import app as app_module  # noqa: E402
from app import EVALUATOR, MODEL_REGISTRY, OUTPUT_DIR, SUBJECT_MODELS, app  # noqa: E402
from models.rsm import save_artifacts  # noqa: E402
from services.data_service import load_run_dataset as load_dataset_from_files  # noqa: E402

STATIC_NOTICE = (
    '<div id="static-export-note" class="notice">'
    "当前为 GitHub Pages 静态演示版，已同步 5000 人合成测试数据和图表。"
    "可在“导入分析”页上传 CSV 并在浏览器端计算；Excel 上传和后端精确分析需要部署完整 Flask 服务。"
    "</div>"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the Flask demo run as a GitHub Pages static site.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR), help="Static site output directory.")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="CSV/XLSX data file used to build the static demo.")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    _copy_static_assets(output_dir)
    _enable_model_cache()

    client = app.test_client()
    data_path = Path(args.data).resolve()
    if not data_path.exists():
        data_path = BASE_DIR / "data" / "demo_students.csv"
    _prepare_static_run(client, data_path)

    catalog = _json(client, "/api/models/catalog")
    student_rows = _json(client, "/api/results")
    route_map = _build_route_map(catalog, student_rows)

    _write_downloads(client, output_dir, route_map)
    _write_api_files(client, output_dir, catalog, route_map)
    _write_html_pages(client, output_dir, route_map, catalog, student_rows)
    _write_static_readme(output_dir)

    print(f"Static site exported to {output_dir}")


def _enable_model_cache() -> None:
    original_run_model = MODEL_REGISTRY.run_model
    cache = {}

    def cached_run_model(model_id, dataset, params=None):
        params_key = json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
        key = (str(model_id), params_key)
        if key not in cache:
            cache[key] = original_run_model(model_id, dataset, params)
        return cache[key]

    MODEL_REGISTRY.run_model = cached_run_model


def _copy_static_assets(output_dir: Path) -> None:
    static_src = BASE_DIR / "static"
    static_dst = output_dir / "static"
    shutil.copytree(static_src, static_dst)


def _prepare_static_run(client, data_path: Path) -> None:
    run_id = "static_export"
    run_dir = OUTPUT_DIR / run_id
    artifacts = EVALUATOR.analyze_file(data_path)
    save_artifacts(artifacts, run_dir)
    dataset = load_dataset_from_files(run_dir)
    original_load_json = app_module.load_json

    def cached_load_run_dataset(path):
        if Path(path) == run_dir:
            return dataset
        return load_dataset_from_files(path)

    def cached_load_results(path):
        if Path(path) == run_dir:
            return dataset.results
        return app_module.pd.read_csv(Path(path) / "rsm_results.csv", encoding="utf-8-sig")

    def cached_load_json(path, default=None):
        path = Path(path)
        if path.parent == run_dir and path.name == "summary.json":
            return dataset.summary
        if path.parent == run_dir and path.name == "student_details.json":
            return dataset.details
        return original_load_json(path, default)

    app_module.load_run_dataset = cached_load_run_dataset
    app_module.load_results = cached_load_results
    app_module.load_json = cached_load_json
    with client.session_transaction() as sess:
        sess["run_id"] = run_id


def _build_route_map(catalog: list[dict], student_rows: list[dict]) -> Dict[str, str]:
    route_map = {
        "/": "index.html",
        "/demo": "results.html",
        "/results": "results.html",
        "/models": "models.html",
        "/models/compare": "models_compare.html",
        "/static-import": "static_import.html",
        "/template": "downloads/rsm_data_template.csv",
        "/config": "api/config.json",
        "/download/results": "downloads/rsm_results.csv",
        "/download/normalized": "downloads/rsm_normalized.csv",
        "/download/excel": "downloads/rsm_academic_report.xlsx",
        "/download/synthetic": "downloads/synthetic_5000_students.csv",
        "/analyze": "#static-export-note",
        "/api/models/catalog": "api/models_catalog.json",
        "/api/models/compare": "api/models_compare.json",
        "/api/data/quality": "api/data_quality.json",
        "/api/data/summary": "api/data_summary.json",
        "/api/results": "api/results.json",
    }

    for subject_key in SUBJECT_MODELS:
        route_map[f"/model/{subject_key}"] = f"model_{subject_key}.html"
    route_map["/model/english"] = "model_foreign.html"

    for item in catalog:
        model_id = item["model_id"]
        route_map[f"/models/{model_id}"] = f"models_{model_id}.html"
        route_map[f"/api/models/{model_id}/run"] = f"api/models_{model_id}_run.json"
        route_map[f"/api/models/{model_id}/charts"] = f"api/models_{model_id}_charts.json"
        route_map[f"/api/models/{model_id}/export/csv"] = f"exports/{model_id}.csv"
        route_map[f"/api/export/{model_id}/csv"] = f"exports/{model_id}.csv"
        route_map[f"/api/models/{model_id}/export/json"] = f"exports/{model_id}.json"
        route_map[f"/api/export/{model_id}/json"] = f"exports/{model_id}.json"
        route_map[f"/api/models/{model_id}/export/excel"] = "#static-export-note"
        route_map[f"/api/export/{model_id}/excel"] = "#static-export-note"

    for row in student_rows[:300]:
        student_id = str(row.get("学号", ""))
        if student_id:
            route_map[f"/students/{student_id}"] = f"students_{student_id}.html"
            route_map[f"/api/student/{student_id}"] = f"api/student_{student_id}.json"

    return route_map


def _write_downloads(client, output_dir: Path, route_map: Dict[str, str]) -> None:
    downloads = {
        "/template": "downloads/rsm_data_template.csv",
        "/download/synthetic": "downloads/synthetic_5000_students.csv",
        "/download/results": "downloads/rsm_results.csv",
        "/download/normalized": "downloads/rsm_normalized.csv",
        "/download/excel": "downloads/rsm_academic_report.xlsx",
    }
    for route, target in downloads.items():
        response = client.get(route)
        if response.status_code == 200:
            _write_bytes(output_dir / target, response.data)


def _write_api_files(client, output_dir: Path, catalog: list[dict], route_map: Dict[str, str]) -> None:
    simple_api_routes = [
        "/api/models/catalog",
        "/api/models/compare",
        "/api/data/quality",
        "/api/data/summary",
        "/api/results",
        "/config",
    ]
    for route in simple_api_routes:
        _write_json_response(client, output_dir / route_map[route], route)

    for item in catalog:
        model_id = item["model_id"]
        _write_json_response(client, output_dir / route_map[f"/api/models/{model_id}/run"], f"/api/models/{model_id}/run")
        _write_json_response(
            client,
            output_dir / route_map[f"/api/models/{model_id}/charts"],
            f"/api/models/{model_id}/charts",
        )
        _write_export(client, output_dir / f"exports/{model_id}.csv", f"/api/models/{model_id}/export/csv")
        _write_export(client, output_dir / f"exports/{model_id}.json", f"/api/models/{model_id}/export/json")


def _write_html_pages(
    client,
    output_dir: Path,
    route_map: Dict[str, str],
    catalog: list[dict],
    student_rows: list[dict],
) -> None:
    pages = [
        ("/", "index.html"),
        ("/results", "results.html"),
        ("/models", "models.html"),
        ("/models/compare", "models_compare.html"),
        ("/static-import", "static_import.html"),
    ]
    pages.extend((f"/model/{subject_key}", f"model_{subject_key}.html") for subject_key in SUBJECT_MODELS)
    pages.extend((f"/models/{item['model_id']}", f"models_{item['model_id']}.html") for item in catalog)
    pages.extend(
        (f"/students/{row['学号']}", f"students_{row['学号']}.html")
        for row in student_rows[:300]
        if row.get("学号")
    )

    for route, target in pages:
        response = client.get(route)
        if response.status_code != 200:
            continue
        html = response.get_data(as_text=True)
        html = _rewrite_html(html, route_map)
        _write_text(output_dir / target, html)


def _rewrite_html(html: str, route_map: Dict[str, str]) -> str:
    html = html.replace('<main class="container">', f'<main class="container">\n  {STATIC_NOTICE}', 1)

    def replace_attr(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{_static_target(match.group('url'), route_map)}{match.group('suffix')}"

    html = re.sub(
        r"(?P<prefix>\b(?:href|src|action)=['\"])(?P<url>/[^'\"]*)(?P<suffix>['\"])",
        replace_attr,
        html,
    )
    html = html.replace('href="#"', 'href="#static-export-note"')
    return html


def _static_target(url: str, route_map: Dict[str, str]) -> str:
    if url.startswith("/static/"):
        return url.lstrip("/")
    path = url.split("?", 1)[0].split("#", 1)[0]
    return route_map.get(path, url)


def _write_json_response(client, path: Path, route: str) -> None:
    response = client.get(route)
    if response.status_code == 200:
        _write_text(path, json.dumps(response.get_json(), ensure_ascii=False, indent=2))


def _write_export(client, path: Path, route: str) -> None:
    response = client.get(route)
    if response.status_code == 200:
        _write_bytes(path, response.data)


def _json(client, route: str):
    response = client.get(route)
    if response.status_code != 200:
        return []
    return response.get_json()


def _write_static_readme(output_dir: Path) -> None:
    _write_text(
        output_dir / "README.md",
        "\n".join(
            [
                "# 学业发展评价分析平台静态演示站",
                "",
                "此目录由 `python utils/export_static_site.py --output site` 自动生成。",
                "",
                "- `index.html`：静态演示首页",
                "- `results.html`：演示数据总览",
                "- `model_*.html`：各学科评价模型页面",
                "- `models_*.html`：统一模型详情页面",
                "- `static_import.html`：浏览器端 CSV 导入分析页面",
                "",
                "GitHub Pages 静态站已内置 5000 人合成测试数据，并支持浏览器端 CSV 导入分析。Excel 上传和完整后端导出请部署 Python Web 服务。",
            ]
        ),
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


if __name__ == "__main__":
    main()
