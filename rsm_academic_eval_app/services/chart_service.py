# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List


def bar_chart(chart_id: str, title: str, labels: List[str], values: List[float], description: str = "") -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "bar",
        "height": 340,
        "description": description,
        "option": {"labels": labels, "values": values},
        "interpretation": description,
    }


def donut_chart(chart_id: str, title: str, data: Dict[str, int], description: str = "") -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "donut",
        "height": 340,
        "description": description,
        "option": {"data": data},
        "interpretation": description,
    }


def line_chart(chart_id: str, title: str, points: List[Dict[str, Any]], description: str = "") -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "line",
        "height": 340,
        "description": description,
        "option": {"points": points},
        "interpretation": description,
    }


def radar_chart(chart_id: str, title: str, indicators: List[str], values: List[float], description: str = "") -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "radar",
        "height": 360,
        "description": description,
        "option": {"indicators": indicators, "values": values},
        "interpretation": description,
    }


def scatter_chart(
    chart_id: str,
    title: str,
    points: List[Dict[str, Any]],
    x_name: str,
    y_name: str,
    description: str = "",
) -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "scatter",
        "height": 360,
        "description": description,
        "option": {"points": points, "x_name": x_name, "y_name": y_name},
        "interpretation": description,
    }


def horizontal_bar_chart(chart_id: str, title: str, items: List[Dict[str, Any]], description: str = "") -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "horizontal_bar",
        "height": 360,
        "description": description,
        "option": {"items": items},
        "interpretation": description,
    }


def heatmap_chart(
    chart_id: str,
    title: str,
    rows: List[Dict[str, Any]],
    dimensions: List[str],
    description: str = "",
) -> Dict[str, Any]:
    return {
        "chart_id": chart_id,
        "title": title,
        "type": "heatmap",
        "height": 360,
        "description": description,
        "option": {"rows": rows, "dimensions": dimensions},
        "interpretation": description,
    }
