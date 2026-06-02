# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Dict, List

from models.base import BaseEvaluationModel, ModelResult
from models.platform_models import CatalogEvaluationModel


class ModelRegistry:
    def __init__(self, catalog_path: str | Path):
        self.catalog_path = Path(catalog_path)
        with self.catalog_path.open("r", encoding="utf-8") as f:
            self._models: List[Dict[str, Any]] = json.load(f)
        self._resolve_paths()
        self._by_id = {item["model_id"]: item for item in self._models}

    def list_models(self) -> List[Dict[str, Any]]:
        return sorted(self._models, key=lambda item: (item.get("priority", 999), item["model_id"]))

    def categories(self) -> List[str]:
        seen = []
        for item in self.list_models():
            category = item["category"]
            if category not in seen:
                seen.append(category)
        return seen

    def get_model(self, model_id: str) -> Dict[str, Any] | None:
        return self._by_id.get(model_id)

    def run_model(self, model_id: str, dataset: Any, params: Dict[str, Any] | None = None) -> ModelResult:
        entry = self.get_model(model_id)
        if not entry:
            raise KeyError(f"未找到模型：{model_id}")
        model = self._build_model(entry)
        return model.run(dataset, params=params)

    def _build_model(self, entry: Dict[str, Any]) -> BaseEvaluationModel:
        module_name = entry.get("module")
        class_name = entry.get("class_name")
        if not module_name or not class_name:
            return CatalogEvaluationModel(entry)
        try:
            module = importlib.import_module(str(module_name))
            cls = getattr(module, str(class_name))
            return cls(entry)
        except Exception:
            return CatalogEvaluationModel(entry)

    def _resolve_paths(self) -> None:
        base_dir = self.catalog_path.resolve().parents[1]
        for item in self._models:
            config_path = item.get("subject_config_path")
            if config_path and not Path(str(config_path)).is_absolute():
                item["subject_config_path"] = str(base_dir / str(config_path))
