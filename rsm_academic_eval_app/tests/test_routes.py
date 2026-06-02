# -*- coding: utf-8 -*-
from __future__ import annotations

from app import app


def test_home_template_and_config_routes() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "本地版学生学业发展评价分析系统".encode("utf-8") in index_response.data
    assert "多学科学业发展评价模型".encode("utf-8") in index_response.data

    template_response = client.get("/template")
    assert template_response.status_code == 200
    content_disposition = template_response.headers["Content-Disposition"]
    assert "attachment" in content_disposition
    assert "filename*=" in content_disposition
    assert ".csv" in content_disposition
    assert "学号,姓名,班级,学科".encode("utf-8") in template_response.data

    config_response = client.get("/config")
    assert config_response.status_code == 200
    assert config_response.get_json()["mastery_threshold"] == 65


def test_demo_results_and_api_routes_are_available() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()

    demo_response = client.get("/demo", follow_redirects=True)
    assert demo_response.status_code == 200
    assert "规则空间模型分析结果".encode("utf-8") in demo_response.data

    results_response = client.get("/results")
    assert results_response.status_code == 200
    assert "重点关注学生".encode("utf-8") in results_response.data
    assert "多模型诊断概览".encode("utf-8") in results_response.data
    assert "学科模型子页面".encode("utf-8") in results_response.data

    api_response = client.get("/api/results")
    assert api_response.status_code == 200
    rows = api_response.get_json()
    assert isinstance(rows, list)
    assert rows
    assert "RSM调整分" in rows[0]
    assert "成长动能指数" in rows[0]
    assert "风险预警等级" in rows[0]

    student_id = rows[0]["学号"]
    student_response = client.get(f"/api/student/{student_id}")
    assert student_response.status_code == 200
    payload = student_response.get_json()
    assert payload["result"]["学号"] == student_id
    assert "secondary_scores" in payload["detail"]

    for subject_key, title in {
        "chinese": "语文学业发展评价模型",
        "math": "数学学业发展评价模型",
        "foreign": "外语学业发展评价模型",
        "physics": "物理学业发展评价模型",
        "chemistry": "化学学业发展评价模型",
        "bio": "生物学业发展评价模型",
        "history": "历史学业发展评价模型",
        "geography": "地理学业发展评价模型",
        "politics": "政治学业发展评价模型",
    }.items():
        response = client.get(f"/model/{subject_key}")
        assert response.status_code == 200
        assert title.encode("utf-8") in response.data
        assert "薄弱知识点与技能模块".encode("utf-8") in response.data

    legacy_english_response = client.get("/model/english")
    assert legacy_english_response.status_code == 200
    assert "外语学业发展评价模型".encode("utf-8") in legacy_english_response.data
