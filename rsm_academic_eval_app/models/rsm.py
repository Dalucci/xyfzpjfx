# -*- coding: utf-8 -*-
"""Rule Space Model based academic development evaluator.

This module implements a transparent, local-first evaluation pipeline:
1. Read/import student academic and process data.
2. Validate, clean and normalize indicator values.
3. Aggregate third-level indicators into secondary and primary scores.
4. Convert secondary indicators into an attribute mastery pattern.
5. Apply a simplified Rule Space Model (RSM) to obtain theta, zeta,
   level, development potential, weaknesses and recommendations.

The implementation is deliberately interpretable so that teachers can inspect
which indicators produced each result.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


META_COLUMNS = ["学号", "姓名", "班级", "学科"]


@dataclass
class AnalysisArtifacts:
    raw: pd.DataFrame
    cleaned: pd.DataFrame
    normalized: pd.DataFrame
    results: pd.DataFrame
    summary: Dict[str, Any]
    logs: List[str]
    details: Dict[str, Dict[str, Any]]


class RSMAcademicEvaluator:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        with self.config_path.open("r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.indicators = self._flatten_indicators()
        self.secondary_map = self._secondary_map()
        self.primary_map = self.config["primary"]
        self.alias_map = self._build_alias_map()
        self.attribute_names = list(self.secondary_map.keys())
        self.attribute_weights = self._attribute_weights()
        self.ideal_states = self._generate_ideal_states()
        self.mastery_threshold = float(self.config.get("mastery_threshold", 65))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def read_data(self, file_path: str | Path) -> pd.DataFrame:
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        if suffix in [".xlsx", ".xls"]:
            # Use the first sheet by default. The user can provide a simple workbook.
            return pd.read_excel(file_path)
        if suffix == ".csv":
            try:
                return pd.read_csv(file_path, encoding="utf-8-sig")
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding="gbk")
        raise ValueError("仅支持 .xlsx/.xls/.csv 文件。")

    def analyze_file(self, file_path: str | Path) -> AnalysisArtifacts:
        raw = self.read_data(file_path)
        return self.analyze_dataframe(raw)

    def analyze_dataframe(self, df: pd.DataFrame) -> AnalysisArtifacts:
        logs: List[str] = []
        raw = df.copy()
        cleaned = self._prepare_columns(df.copy(), logs)
        cleaned = self._ensure_meta_columns(cleaned)
        cleaned, available_indicators = self._validate_and_impute(cleaned, logs)
        normalized = self._normalize(cleaned, available_indicators, logs)
        scores = self._compute_scores(normalized, available_indicators, logs)
        results, details = self._apply_rsm(normalized, scores, available_indicators)
        summary = self._build_summary(results, scores, available_indicators, logs)
        return AnalysisArtifacts(raw=raw, cleaned=cleaned, normalized=normalized,
                                 results=results, summary=summary, logs=logs, details=details)

    def template_dataframe(self) -> pd.DataFrame:
        columns = META_COLUMNS + list(self.indicators.keys())
        return pd.DataFrame(columns=columns)

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------
    def _flatten_indicators(self) -> Dict[str, Dict[str, Any]]:
        flat: Dict[str, Dict[str, Any]] = {}
        for primary_name, primary_conf in self.config["primary"].items():
            for secondary_name, secondary_conf in primary_conf["secondary"].items():
                for ind_name, ind_conf in secondary_conf["indicators"].items():
                    item = dict(ind_conf)
                    item["primary"] = primary_name
                    item["secondary"] = secondary_name
                    flat[ind_name] = item
        return flat

    def _secondary_map(self) -> Dict[str, Dict[str, Any]]:
        secondaries: Dict[str, Dict[str, Any]] = {}
        for primary_name, primary_conf in self.config["primary"].items():
            for secondary_name, secondary_conf in primary_conf["secondary"].items():
                secondaries[secondary_name] = {
                    "primary": primary_name,
                    "weight": float(secondary_conf["weight"]),
                    "indicators": secondary_conf["indicators"],
                }
        return secondaries

    def _build_alias_map(self) -> Dict[str, str]:
        aliases = self.config.get("aliases", {})
        mapping: Dict[str, str] = {}
        for canonical in META_COLUMNS + list(self.indicators.keys()):
            mapping[self._norm_col(canonical)] = canonical
        for canonical, alias_list in aliases.items():
            mapping[self._norm_col(canonical)] = canonical
            for alias in alias_list:
                mapping[self._norm_col(alias)] = canonical
        return mapping

    def _attribute_weights(self) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for sec_name, sec_conf in self.secondary_map.items():
            primary_name = sec_conf["primary"]
            weights[sec_name] = float(self.config["primary"][primary_name]["weight"]) * float(sec_conf["weight"])
        total = sum(weights.values()) or 1
        return {k: v / total for k, v in weights.items()}

    @staticmethod
    def _norm_col(col: Any) -> str:
        return str(col).strip().lower().replace(" ", "").replace("/", "").replace("-", "_")

    # ------------------------------------------------------------------
    # Data cleaning and normalization
    # ------------------------------------------------------------------
    def _prepare_columns(self, df: pd.DataFrame, logs: List[str]) -> pd.DataFrame:
        rename: Dict[str, str] = {}
        duplicate_targets: Dict[str, List[str]] = {}
        for col in df.columns:
            canonical = self.alias_map.get(self._norm_col(col))
            if canonical:
                duplicate_targets.setdefault(canonical, []).append(col)
                rename[col] = canonical

        if rename:
            df = df.rename(columns=rename)
        # If multiple source columns map to same canonical, keep first non-null value row-wise.
        for canonical, original_cols in duplicate_targets.items():
            if len(original_cols) > 1:
                cols = [rename.get(c, c) for c in original_cols]
                cols = [c for c in cols if c in df.columns]
                if len(cols) > 1:
                    combined = df[cols].bfill(axis=1).iloc[:, 0]
                    df = df.drop(columns=cols)
                    df[canonical] = combined
        logs.append(f"字段识别：识别到 {len(set(rename.values()))} 个标准字段。")
        return df

    def _ensure_meta_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in META_COLUMNS:
            if col not in df.columns:
                if col == "学号":
                    df[col] = [f"S{str(i + 1).zfill(4)}" for i in range(len(df))]
                elif col == "姓名":
                    df[col] = [f"学生{i + 1}" for i in range(len(df))]
                elif col == "班级":
                    df[col] = "未分班"
                elif col == "学科":
                    df[col] = "综合"
        return df

    def _validate_and_impute(self, df: pd.DataFrame, logs: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        available = [col for col in self.indicators if col in df.columns]
        if not available:
            raise ValueError("未识别到任何评价指标字段。请先下载模板，或检查表头是否与指标名称一致。")

        # Convert to numeric and mark invalid values.
        invalid_count = 0
        missing_before = int(df[available].isna().sum().sum())
        for col in available:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            conf = self.indicators[col]
            invalid_mask = pd.Series(False, index=df.index)
            if conf.get("type") == "score":
                invalid_mask |= (df[col] < 0) | (df[col] > 100)
            elif conf.get("type") == "trend":
                # Educational score differences are usually within [-100, 100].
                invalid_mask |= (df[col] < -100) | (df[col] > 100)
            else:
                invalid_mask |= (df[col] < 0)
            invalid_count += int(invalid_mask.sum())
            df.loc[invalid_mask, col] = np.nan

        # Impute by class+subject median, then subject median, then global median, then 0.
        imputed = 0
        for col in available:
            before = int(df[col].isna().sum())
            if before == 0:
                continue
            if "班级" in df.columns and "学科" in df.columns:
                df[col] = df[col].fillna(df.groupby(["班级", "学科"])[col].transform("median"))
            if "学科" in df.columns:
                df[col] = df[col].fillna(df.groupby("学科")[col].transform("median"))
            global_median = df[col].median()
            if pd.isna(global_median):
                global_median = 0
            df[col] = df[col].fillna(global_median)
            imputed += before - int(df[col].isna().sum())

        logs.append(f"数据校验：发现并置空异常值 {invalid_count} 个；原始缺失值 {missing_before} 个。")
        logs.append(f"缺失填补：按“班级-学科-指标”中位数优先，共填补 {imputed} 个数值。")
        logs.append(f"可用指标：{len(available)} / {len(self.indicators)}。")
        return df, available

    def _normalize(self, df: pd.DataFrame, available: List[str], logs: List[str]) -> pd.DataFrame:
        normalized = df[META_COLUMNS].copy()
        for col in available:
            conf = self.indicators[col]
            series = df[col].astype(float)
            norm = self._indicator_to_score(series, conf)
            normalized[col] = norm.clip(0, 100).round(2)
            # z-score version for audit/export.
            std = float(series.std(ddof=0))
            if std == 0 or math.isnan(std):
                z = pd.Series(0, index=series.index, dtype=float)
            else:
                z = (series - float(series.mean())) / std
            normalized[f"Z_{col}"] = z.clip(-2, 2).round(4)
        logs.append("标准化：已生成 0-100 评分值，同时保留 Z-score 审计列。")
        return normalized

    def _indicator_to_score(self, series: pd.Series, conf: Dict[str, Any]) -> pd.Series:
        direction = conf.get("direction", "higher_better")
        if conf.get("type") == "score":
            lo, hi = conf.get("range", [0, 100])
            score = (series - lo) / (hi - lo) * 100 if hi != lo else series * 0
        elif conf.get("type") == "trend":
            # Map [-100, 100] to [0, 100]. A zero trend becomes 50.
            score = (series + 100) / 200 * 100
        else:
            score = self._robust_minmax(series)
        if direction == "lower_better":
            score = 100 - score
        return score

    @staticmethod
    def _robust_minmax(series: pd.Series) -> pd.Series:
        series = series.astype(float)
        q1, q99 = np.nanpercentile(series, [1, 99]) if len(series.dropna()) else (0, 1)
        if q99 <= q1:
            return pd.Series(50, index=series.index, dtype=float)
        clipped = series.clip(q1, q99)
        return (clipped - q1) / (q99 - q1) * 100

    # ------------------------------------------------------------------
    # Score aggregation
    # ------------------------------------------------------------------
    def _compute_scores(self, normalized: pd.DataFrame, available: List[str], logs: List[str]) -> Dict[str, pd.DataFrame]:
        sec_scores = pd.DataFrame(index=normalized.index)
        sec_coverage = pd.DataFrame(index=normalized.index)
        for sec_name, sec_conf in self.secondary_map.items():
            score, coverage = self._weighted_average(normalized, sec_conf["indicators"], available)
            sec_scores[sec_name] = score.round(2)
            sec_coverage[sec_name] = coverage.round(2)

        pri_scores = pd.DataFrame(index=normalized.index)
        for primary_name, primary_conf in self.primary_map.items():
            pieces = {}
            for sec_name, sec_conf in primary_conf["secondary"].items():
                if sec_name in sec_scores:
                    pieces[sec_name] = {"weight": float(sec_conf["weight"]), "values": sec_scores[sec_name]}
            pri_scores[primary_name] = self._weighted_series(pieces).round(2)

        overall = pd.Series(0.0, index=normalized.index)
        weight_sum = pd.Series(0.0, index=normalized.index)
        for primary_name, primary_conf in self.primary_map.items():
            values = pri_scores[primary_name]
            valid = values.notna()
            weight = float(primary_conf["weight"])
            overall += values.fillna(0) * weight
            weight_sum += valid.astype(float) * weight
        overall = (overall / weight_sum.replace(0, np.nan)).fillna(0).round(2)

        logs.append("模型计分：已完成三级指标→二级属性→一级维度→综合评分的逐级聚合。")
        return {"secondary": sec_scores, "secondary_coverage": sec_coverage, "primary": pri_scores, "overall": overall}

    def _weighted_average(self, df: pd.DataFrame, indicator_conf: Dict[str, Any], available: List[str]) -> Tuple[pd.Series, pd.Series]:
        pieces = {}
        used_count = pd.Series(0.0, index=df.index)
        total_possible = len(indicator_conf)
        for ind_name, conf in indicator_conf.items():
            if ind_name in available and ind_name in df.columns:
                pieces[ind_name] = {"weight": float(conf["weight"]), "values": df[ind_name]}
                used_count += 1
        if not pieces:
            return pd.Series(np.nan, index=df.index), pd.Series(0.0, index=df.index)
        return self._weighted_series(pieces), used_count / max(total_possible, 1)

    @staticmethod
    def _weighted_series(pieces: Dict[str, Dict[str, Any]]) -> pd.Series:
        if not pieces:
            return pd.Series(dtype=float)
        first = next(iter(pieces.values()))["values"]
        numerator = pd.Series(0.0, index=first.index)
        denominator = pd.Series(0.0, index=first.index)
        for item in pieces.values():
            values = item["values"]
            weight = float(item["weight"])
            valid = values.notna()
            numerator += values.fillna(0) * weight
            denominator += valid.astype(float) * weight
        return numerator / denominator.replace(0, np.nan)

    # ------------------------------------------------------------------
    # RSM
    # ------------------------------------------------------------------
    def _generate_ideal_states(self) -> List[Dict[str, Any]]:
        attrs = list(self.secondary_map.keys())
        states: List[Dict[str, Any]] = []
        for bits in range(2 ** len(attrs)):
            vector = {attr: (bits >> i) & 1 for i, attr in enumerate(attrs)}
            if not self._valid_state(vector):
                continue
            score = sum(self.attribute_weights[attr] * vector[attr] for attr in attrs) * 100
            states.append({"vector": vector, "score": score, "label": self._level_from_score(score)})
        # Add a stable deterministic ordering: low-to-high score, then vector string.
        states.sort(key=lambda s: (s["score"], "".join(str(s["vector"][a]) for a in attrs)))
        return states

    @staticmethod
    def _valid_state(vector: Dict[str, int]) -> bool:
        # Rule-space prerequisites. These educational constraints keep ideal
        # profiles interpretable instead of allowing arbitrary attribute states.
        if vector.get("知识点应用能力", 0) and not vector.get("知识点达标率", 0):
            return False
        if vector.get("进步退步幅度", 0) and not (vector.get("基础成绩水平", 0) or vector.get("知识点达标率", 0)):
            return False
        if vector.get("自主学习行为", 0) and not (vector.get("在线学习行为", 0) or vector.get("作业提交行为", 0)):
            return False
        return True

    def _apply_rsm(self, normalized: pd.DataFrame, scores: Dict[str, pd.DataFrame], available: List[str]) -> Tuple[pd.DataFrame, Dict[str, Dict[str, Any]]]:
        sec_scores = scores["secondary"]
        pri_scores = scores["primary"]
        overall = scores["overall"]
        details: Dict[str, Dict[str, Any]] = {}
        rows: List[Dict[str, Any]] = []
        max_distance = math.sqrt(sum(self.attribute_weights.values())) or 1

        for idx in normalized.index:
            sec_values = {attr: float(sec_scores.loc[idx, attr]) if pd.notna(sec_scores.loc[idx, attr]) else np.nan
                          for attr in self.attribute_names}
            mastery = {attr: 1 if (not pd.isna(value) and value >= self.mastery_threshold) else 0
                       for attr, value in sec_values.items()}
            theta_binary = sum(self.attribute_weights[attr] * mastery[attr] for attr in self.attribute_names) * 100
            nearest_state, distance = self._nearest_ideal_state(mastery)
            zeta = min(100.0, distance / max_distance * 100)
            adjusted = 0.80 * float(overall.loc[idx]) + 0.10 * theta_binary + 0.10 * (100 - zeta)
            level = self._level_from_score(adjusted)
            potential_index, potential_label = self._potential(pri_scores.loc[idx], sec_scores.loc[idx], zeta)
            weak_attrs = self._weak_attributes(sec_values)
            suggestions = self._recommendations(level, potential_label, weak_attrs)
            advanced = self._advanced_models(
                pri_scores.loc[idx],
                sec_scores.loc[idx],
                adjusted,
                theta_binary,
                zeta,
                len(weak_attrs),
                len(mastery),
            )
            risk = advanced["风险预警等级"]

            row = {
                "学号": normalized.loc[idx, "学号"],
                "姓名": normalized.loc[idx, "姓名"],
                "班级": normalized.loc[idx, "班级"],
                "学科": normalized.loc[idx, "学科"],
                "综合评分": round(float(overall.loc[idx]), 2),
                "RSM调整分": round(float(adjusted), 2),
                "学业等级": level,
                "发展潜力指数": round(float(potential_index), 2),
                "发展潜力": potential_label,
                "规则空间Theta": round(float(theta_binary), 2),
                "规则空间Zeta": round(float(zeta), 2),
                "最近理想状态": nearest_state["label"],
                "掌握属性数": int(sum(mastery.values())),
                "未掌握属性数": int(len(mastery) - sum(mastery.values())),
                "成长动能指数": advanced["成长动能指数"],
                "学习稳定性指数": advanced["学习稳定性指数"],
                "知行耦合指数": advanced["知行耦合指数"],
                "预警风险指数": advanced["预警风险指数"],
                "风险预警等级": advanced["风险预警等级"],
                "学业发展画像": advanced["学业发展画像"],
                "干预优先级": advanced["干预优先级"],
                "薄弱属性": "、".join([w[0] for w in weak_attrs[:3]]) if weak_attrs else "暂无明显薄弱项",
                "建议摘要": "；".join(suggestions[:3])
            }
            for primary_name in self.primary_map:
                row[primary_name] = round(float(pri_scores.loc[idx, primary_name]), 2) if pd.notna(pri_scores.loc[idx, primary_name]) else np.nan
            for attr in self.attribute_names:
                row[attr] = round(sec_values[attr], 2) if not pd.isna(sec_values[attr]) else np.nan
                row[f"{attr}_掌握"] = mastery[attr]
            rows.append(row)
            details[str(normalized.loc[idx, "学号"])] = {
                "secondary_scores": {k: None if pd.isna(v) else round(float(v), 2) for k, v in sec_values.items()},
                "primary_scores": {p: round(float(pri_scores.loc[idx, p]), 2) if pd.notna(pri_scores.loc[idx, p]) else None for p in self.primary_map},
                "mastery": mastery,
                "nearest_state": nearest_state,
                "distance": round(float(distance), 4),
                "weak_attributes": weak_attrs,
                "suggestions": suggestions,
                "risk": risk,
                "advanced_models": advanced,
                "used_indicators": available
            }
        return pd.DataFrame(rows), details

    def _nearest_ideal_state(self, mastery: Dict[str, int]) -> Tuple[Dict[str, Any], float]:
        best_state = None
        best_distance = float("inf")
        for state in self.ideal_states:
            dist = 0.0
            for attr in self.attribute_names:
                diff = mastery[attr] - int(state["vector"][attr])
                dist += self.attribute_weights[attr] * (diff ** 2)
            dist = math.sqrt(dist)
            if dist < best_distance:
                best_distance = dist
                best_state = state
        assert best_state is not None
        return best_state, best_distance

    def _potential(self, pri_row: pd.Series, sec_row: pd.Series, zeta: float) -> Tuple[float, str]:
        progress = self._safe(sec_row.get("进步退步幅度"), 50)
        behavior = self._safe(pri_row.get("学习行为活跃度"), 50)
        knowledge = self._safe(pri_row.get("知识点掌握度"), 50)
        base = self._safe(pri_row.get("成绩波动趋势"), 50)
        # High behavior and upward trend indicate active development.
        # Lower zeta indicates the observed pattern is consistent and reliable.
        index = 0.35 * progress + 0.30 * behavior + 0.20 * knowledge + 0.15 * (100 - zeta)
        if index >= 78 and progress >= 60:
            label = "快速进步"
        elif index >= 63:
            label = "稳步进步"
        elif index >= 48:
            label = "波动观察"
        else:
            label = "学业预警"
        if base < 45 and behavior >= 65:
            label = "潜力待激发"
        return float(index), label

    @staticmethod
    def _safe(value: Any, default: float) -> float:
        try:
            if pd.isna(value):
                return default
            return float(value)
        except Exception:
            return default

    def _weak_attributes(self, sec_values: Dict[str, float]) -> List[Tuple[str, float]]:
        weak = []
        for attr, value in sec_values.items():
            if pd.isna(value):
                continue
            if value < self.mastery_threshold:
                weak.append((attr, round(float(value), 2)))
        return sorted(weak, key=lambda x: x[1])

    def _recommendations(self, level: str, potential_label: str, weak_attrs: List[Tuple[str, float]]) -> List[str]:
        level_prefix = {
            "优秀": "保持高阶拓展：增加跨章节综合题、探究任务或竞赛基础训练",
            "良好": "突出能力提升：在稳定基础题的同时，重点突破中档题和迁移应用题",
            "中等": "先做基础巩固：围绕核心知识点建立清单化复习与错题复盘机制",
            "待提高": "实施重点补弱：每天安排短时高频基础训练，优先修复低分知识点",
            "需帮扶": "启动帮扶路径：降低任务难度，采用一对一讲解、模板化练习和正向激励"
        }
        mapping = {
            "基础成绩水平": "补齐基础成绩：梳理最近考试错题，按知识点重做基础题和典型例题",
            "成绩波动幅度": "降低成绩波动：固定周测复盘流程，记录失分类型并做稳定性训练",
            "进步退步幅度": "强化进步曲线：设置两周一个小目标，用阶段测验追踪提升幅度",
            "知识点达标率": "补强知识达标：按章节列出低于60%的知识点，优先做概念辨析与基础题",
            "知识点应用能力": "提升迁移应用：训练综合题审题、条件转化和跨章节联系",
            "课堂互动行为": "提升课堂参与：每节课至少完成一次提问、回答或小组表达",
            "作业提交行为": "规范作业闭环：按时提交、及时订正，并记录错因",
            "在线学习行为": "优化线上学习：保证资源浏览、视频学习和在线测验的完成率",
            "自主学习行为": "增强自主学习：固定预习、刷题、错题整理和计划完成打卡"
        }
        suggestions = [level_prefix.get(level, "根据薄弱项进行针对性提升")]
        if potential_label in ["学业预警", "波动观察"]:
            suggestions.append("建议每两周更新一次数据，观察成绩趋势与行为活跃度是否同步改善")
        elif potential_label == "快速进步":
            suggestions.append("当前趋势较好，可适当增加综合任务，防止只停留在基础层面")
        for attr, _ in weak_attrs[:5]:
            suggestions.append(mapping.get(attr, f"重点关注{attr}"))
        return suggestions

    def _advanced_models(
        self,
        pri_row: pd.Series,
        sec_row: pd.Series,
        adjusted_score: float,
        theta: float,
        zeta: float,
        weak_count: int,
        attribute_count: int,
    ) -> Dict[str, Any]:
        base = self._safe(pri_row.get("成绩波动趋势"), 50)
        knowledge = self._safe(pri_row.get("知识点掌握度"), 50)
        behavior = self._safe(pri_row.get("学习行为活跃度"), 50)
        progress = self._safe(sec_row.get("进步退步幅度"), 50)
        stability = self._safe(sec_row.get("成绩波动幅度"), 50)
        weak_rate = weak_count / max(attribute_count, 1) * 100

        growth = 0.30 * progress + 0.25 * behavior + 0.20 * knowledge + 0.15 * theta + 0.10 * (100 - zeta)
        coupling = 0.60 * min(knowledge, behavior) + 0.40 * (100 - abs(knowledge - behavior))
        risk_score = 0.35 * (100 - adjusted_score) + 0.20 * zeta + 0.20 * (100 - behavior) + 0.15 * weak_rate + 0.10 * (100 - stability)
        profile = self._profile_label(knowledge, behavior, stability, progress)
        risk_label = self._risk_label(risk_score)

        if risk_score >= 72:
            priority = "P1-立即帮扶"
        elif risk_score >= 55:
            priority = "P2-重点跟进"
        elif risk_score >= 38:
            priority = "P3-持续观察"
        else:
            priority = "P4-常规支持"

        return {
            "成长动能指数": round(float(np.clip(growth, 0, 100)), 2),
            "学习稳定性指数": round(float(np.clip(stability, 0, 100)), 2),
            "知行耦合指数": round(float(np.clip(coupling, 0, 100)), 2),
            "预警风险指数": round(float(np.clip(risk_score, 0, 100)), 2),
            "风险预警等级": risk_label,
            "学业发展画像": profile,
            "干预优先级": priority,
        }

    @staticmethod
    def _profile_label(knowledge: float, behavior: float, stability: float, progress: float) -> str:
        if knowledge >= 75 and behavior >= 75 and stability >= 65:
            return "高掌握-高活跃"
        if knowledge >= 70 and behavior < 60:
            return "高掌握-低活跃"
        if knowledge < 60 and behavior >= 70:
            return "低掌握-高投入"
        if progress >= 62 and stability >= 55:
            return "进步驱动型"
        if stability < 45:
            return "波动风险型"
        if knowledge < 55 and behavior < 55:
            return "基础薄弱型"
        return "均衡发展型"

    @staticmethod
    def _risk_label(risk_score: float) -> str:
        if risk_score >= 72:
            return "红色预警"
        if risk_score >= 55:
            return "橙色关注"
        if risk_score >= 38:
            return "黄色观察"
        return "正常"

    def _level_from_score(self, score: float) -> str:
        for level in self.config.get("levels", []):
            if score >= float(level["min_score"]):
                return level["name"]
        return "需帮扶"

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    def _build_summary(self, results: pd.DataFrame, scores: Dict[str, pd.DataFrame], available: List[str], logs: List[str]) -> Dict[str, Any]:
        level_order = [item["name"] for item in self.config.get("levels", [])]
        level_counts = results["学业等级"].value_counts().reindex(level_order, fill_value=0).to_dict()
        potential_counts = results["发展潜力"].value_counts().to_dict()
        primary_means = {p: round(float(results[p].mean()), 2) for p in self.primary_map if p in results}
        secondary_cols = [c for c in self.attribute_names if c in results]
        secondary_means = {c: round(float(results[c].mean()), 2) for c in secondary_cols}
        low_students = results[results["学业等级"].isin(["待提高", "需帮扶"])].sort_values("RSM调整分").head(10)
        model_means = self._model_means(results)
        summary = {
            "student_count": int(len(results)),
            "indicator_count": int(len(available)),
            "overall_mean": round(float(results["综合评分"].mean()), 2) if len(results) else 0,
            "rsm_mean": round(float(results["RSM调整分"].mean()), 2) if len(results) else 0,
            "theta_mean": round(float(results["规则空间Theta"].mean()), 2) if len(results) else 0,
            "zeta_mean": round(float(results["规则空间Zeta"].mean()), 2) if len(results) else 0,
            "level_counts": level_counts,
            "potential_counts": potential_counts,
            "risk_counts": self._ordered_counts(results, "风险预警等级", ["红色预警", "橙色关注", "黄色观察", "正常"]),
            "profile_counts": results["学业发展画像"].value_counts().to_dict() if "学业发展画像" in results else {},
            "intervention_counts": self._ordered_counts(results, "干预优先级", ["P1-立即帮扶", "P2-重点跟进", "P3-持续观察", "P4-常规支持"]),
            "model_means": model_means,
            "model_cards": self._model_cards(model_means),
            "primary_means": primary_means,
            "secondary_means": secondary_means,
            "subject_dimension_matrix": self._subject_dimension_matrix(results),
            "class_overview": self._class_overview(results),
            "score_histogram": self._score_histogram(results["RSM调整分"]),
            "top_weak_attributes": self._top_weak_attributes(results),
            "focus_students": low_students[["学号", "姓名", "班级", "学科", "RSM调整分", "学业等级", "发展潜力", "风险预警等级", "干预优先级", "薄弱属性"]].to_dict("records"),
            "logs": logs
        }
        return summary

    @staticmethod
    def _ordered_counts(results: pd.DataFrame, column: str, order: List[str]) -> Dict[str, int]:
        if column not in results:
            return {}
        return results[column].value_counts().reindex(order, fill_value=0).to_dict()

    @staticmethod
    def _model_means(results: pd.DataFrame) -> Dict[str, float]:
        mapping = {
            "AHP综合评分": "综合评分",
            "RSM调整分": "RSM调整分",
            "成长动能指数": "成长动能指数",
            "学习稳定性指数": "学习稳定性指数",
            "知行耦合指数": "知行耦合指数",
            "风险反向指数": "预警风险指数",
        }
        means: Dict[str, float] = {}
        for label, column in mapping.items():
            if column not in results or not len(results):
                continue
            value = float(results[column].mean())
            if label == "风险反向指数":
                value = 100 - value
            means[label] = round(value, 2)
        return means

    @staticmethod
    def _model_cards(model_means: Dict[str, float]) -> List[Dict[str, Any]]:
        definitions = [
            ("AHP综合评分", "三级指标按配置权重聚合后的原始综合评价"),
            ("RSM调整分", "综合评分、Theta、Zeta 组合后的规则空间主评分"),
            ("成长动能指数", "进步幅度、行为活跃、知识掌握和规则稳定性的综合动能"),
            ("学习稳定性指数", "由成绩波动幅度属性反向刻画，越高表示波动越小"),
            ("知行耦合指数", "知识掌握与学习行为之间的一致性和共同水平"),
            ("风险反向指数", "由预警风险指数反向得到，越高表示整体风险越低"),
        ]
        return [{"name": name, "score": model_means.get(name, 0), "description": desc} for name, desc in definitions]

    def _subject_dimension_matrix(self, results: pd.DataFrame) -> List[Dict[str, Any]]:
        if "学科" not in results or not len(results):
            return []
        columns = [p for p in self.primary_map if p in results]
        grouped = results.groupby("学科")[columns].mean().round(2)
        rows = []
        for subject, values in grouped.iterrows():
            row = {"学科": subject}
            row.update({col: float(values[col]) for col in columns})
            rows.append(row)
        return sorted(rows, key=lambda x: str(x["学科"]))

    @staticmethod
    def _class_overview(results: pd.DataFrame) -> List[Dict[str, Any]]:
        if "班级" not in results or not len(results):
            return []
        rows = []
        grouped = results.groupby("班级")
        for class_name, group in grouped:
            risk_count = int(group["风险预警等级"].isin(["红色预警", "橙色关注"]).sum())
            rows.append({
                "班级": class_name,
                "人数": int(len(group)),
                "RSM调整均分": round(float(group["RSM调整分"].mean()), 2),
                "成长动能均分": round(float(group["成长动能指数"].mean()), 2),
                "重点关注人数": risk_count,
            })
        return sorted(rows, key=lambda x: x["RSM调整均分"], reverse=True)

    @staticmethod
    def _score_histogram(scores: pd.Series) -> List[Dict[str, Any]]:
        bins = [(0, 40), (40, 55), (55, 70), (70, 85), (85, 101)]
        labels = ["0-39", "40-54", "55-69", "70-84", "85-100"]
        rows = []
        for label, (lo, hi) in zip(labels, bins):
            if hi == 101:
                count = int(((scores >= lo) & (scores <= 100)).sum())
            else:
                count = int(((scores >= lo) & (scores < hi)).sum())
            rows.append({"range": label, "count": count})
        return rows

    def _top_weak_attributes(self, results: pd.DataFrame) -> List[Dict[str, Any]]:
        rows = []
        for attr in self.attribute_names:
            mastery_col = f"{attr}_掌握"
            if mastery_col in results:
                unmastered_rate = 1 - float(results[mastery_col].mean())
                rows.append({
                    "attribute": attr,
                    "unmastered_rate": round(unmastered_rate * 100, 2),
                    "avg_score": round(float(results[attr].mean()), 2) if attr in results else None
                })
        return sorted(rows, key=lambda x: x["unmastered_rate"], reverse=True)[:6]


def save_artifacts(artifacts: AnalysisArtifacts, output_dir: str | Path) -> Dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "results_csv": output_dir / "rsm_results.csv",
        "normalized_csv": output_dir / "normalized_data.csv",
        "summary_json": output_dir / "summary.json",
        "details_json": output_dir / "student_details.json",
        "results_xlsx": output_dir / "rsm_analysis_report.xlsx"
    }
    artifacts.results.to_csv(paths["results_csv"], index=False, encoding="utf-8-sig")
    artifacts.normalized.to_csv(paths["normalized_csv"], index=False, encoding="utf-8-sig")
    with paths["summary_json"].open("w", encoding="utf-8") as f:
        json.dump(artifacts.summary, f, ensure_ascii=False, indent=2)
    with paths["details_json"].open("w", encoding="utf-8") as f:
        json.dump(artifacts.details, f, ensure_ascii=False, indent=2)
    # Excel export is optional. If openpyxl is unavailable, skip gracefully.
    try:
        with pd.ExcelWriter(paths["results_xlsx"], engine="openpyxl") as writer:
            artifacts.results.to_excel(writer, index=False, sheet_name="评价结果")
            pd.DataFrame([artifacts.summary]).to_excel(writer, index=False, sheet_name="汇总概览")
            artifacts.normalized.to_excel(writer, index=False, sheet_name="标准化数据")
        return {k: str(v) for k, v in paths.items()}
    except Exception:
        paths.pop("results_xlsx", None)
        return {k: str(v) for k, v in paths.items()}
