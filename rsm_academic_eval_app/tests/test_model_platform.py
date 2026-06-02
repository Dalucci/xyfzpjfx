# -*- coding: utf-8 -*-
from __future__ import annotations

from app import app


def test_model_center_catalog_and_compare_routes() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()

    center_response = client.get("/models")
    assert center_response.status_code == 200
    assert "学生学业发展评价模型中心".encode("utf-8") in center_response.data

    catalog_response = client.get("/api/models/catalog")
    assert catalog_response.status_code == 200
    catalog = catalog_response.get_json()
    assert len(catalog) >= 39
    assert {item["model_id"] for item in catalog} >= {"ahp", "rsm", "risk_warning", "subject_math", "subject_politics"}

    compare_response = client.get("/models/compare")
    assert compare_response.status_code == 200
    assert "模型比较".encode("utf-8") in compare_response.data

    compare_api = client.get("/api/models/compare")
    assert compare_api.status_code == 200
    compare_payload = compare_api.get_json()
    assert compare_payload["models"]
    assert compare_payload["student_count"] > 0


def test_every_registered_model_returns_unified_protocol() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()
    client.get("/demo", follow_redirects=True)

    catalog = client.get("/api/models/catalog").get_json()
    for item in catalog:
        model_id = item["model_id"]
        page_response = client.get(f"/models/{model_id}")
        assert page_response.status_code == 200
        assert item["name"].encode("utf-8") in page_response.data

        api_response = client.get(f"/api/models/{model_id}/run")
        assert api_response.status_code == 200
        payload = api_response.get_json()
        assert payload["model_id"] == model_id
        assert payload["summary_cards"]
        assert len(payload["charts"]) >= 5
        assert payload["student_table"]
        assert payload["student_details"]
        assert payload["data_quality"]["sample_count"] > 0
        assert payload["status"] in {"ok", "degraded"}

    first_student_id = client.get("/api/results").get_json()[0]["学号"]
    profile_response = client.get(f"/students/{first_student_id}")
    assert profile_response.status_code == 200
    assert "综合画像".encode("utf-8") in profile_response.data
    assert "核心素养画像".encode("utf-8") in profile_response.data

    detail_response = client.get(f"/api/models/rsm/student/{first_student_id}")
    assert detail_response.status_code == 200
    assert detail_response.get_json()["scores"]["score_label"] == "RSM调整分"


def test_subject_model_protocol_contains_core_literacy_charts() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()
    client.get("/demo", follow_redirects=True)

    payload = client.get("/api/models/subject_math/run").get_json()
    chart_ids = {chart["chart_id"] for chart in payload["charts"]}
    assert {
        "subject_literacy_radar",
        "subject_competency_bar",
        "subject_literacy_heatmap",
        "subject_model_suite_bar",
    }.issubset(chart_ids)
    assert any("数学" in row["recommendation"] or "建模" in row["recommendation"] for row in payload["student_table"])
    model_page = client.get("/models/subject_math").data
    assert "学科评价重点".encode("utf-8") in model_page
    assert "分层评价用语".encode("utf-8") in model_page
    assert "数学结构化思维".encode("utf-8") in model_page

    subject_page = client.get("/model/math").data
    assert "数学抽象".encode("utf-8") in subject_page
    assert "学科评价用语".encode("utf-8") in subject_page
    assert "错题订正后追加同结构变式题".encode("utf-8") in subject_page
