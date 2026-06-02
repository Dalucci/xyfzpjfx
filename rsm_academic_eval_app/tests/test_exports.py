# -*- coding: utf-8 -*-
from __future__ import annotations

from app import app


def test_model_exports_are_available() -> None:
    app.config.update(TESTING=True)
    client = app.test_client()
    client.get("/demo", follow_redirects=True)

    for fmt in ["csv", "json", "excel"]:
        response = client.get(f"/api/models/rsm/export/{fmt}")
        assert response.status_code == 200
        assert response.data
        assert "attachment" in response.headers["Content-Disposition"]
