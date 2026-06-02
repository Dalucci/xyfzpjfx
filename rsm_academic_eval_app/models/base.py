# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ModelResult:
    model_id: str
    model_name: str
    category: str
    status: str
    status_message: str
    summary_cards: List[Dict[str, Any]] = field(default_factory=list)
    charts: List[Dict[str, Any]] = field(default_factory=list)
    student_table: List[Dict[str, Any]] = field(default_factory=list)
    student_details: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    explanations: List[Dict[str, Any]] = field(default_factory=list)
    data_quality: Dict[str, Any] = field(default_factory=dict)
    export_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseEvaluationModel:
    def __init__(self, catalog_entry: Dict[str, Any]):
        self.catalog_entry = catalog_entry
        self.model_id = str(catalog_entry["model_id"])
        self.model_name = str(catalog_entry["name"])
        self.category = str(catalog_entry["category"])

    def run(self, dataset: Any, params: Dict[str, Any] | None = None) -> ModelResult:
        raise NotImplementedError
