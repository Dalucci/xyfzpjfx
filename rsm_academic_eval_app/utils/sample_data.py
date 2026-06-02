# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

SUBJECTS = ["语文", "数学", "英语", "物理", "化学", "生物", "历史", "政治", "地理"]

GRADE_CLASS_COUNTS = {
    "高一": 29,
    "高二": 12,
    "高三": 10,
}

COMBINATION_SUBJECTS = {
    "物化生": ["语文", "数学", "英语", "物理", "化学", "生物"],
    "物化政": ["语文", "数学", "英语", "物理", "化学", "政治"],
    "物生地": ["语文", "数学", "英语", "物理", "生物", "地理"],
    "历地政": ["语文", "数学", "英语", "历史", "地理", "政治"],
    "体育生": ["语文", "数学", "英语", "政治", "历史", "地理"],
    "艺术生": ["语文", "数学", "英语", "政治", "历史", "地理"],
}

COMBINATION_PROBS = {
    "物化生": 0.30,
    "物化政": 0.18,
    "物生地": 0.16,
    "历地政": 0.20,
    "体育生": 0.08,
    "艺术生": 0.08,
}

LEVEL_PARAMS = {
    "好": {
        "base": 84,
        "knowledge": 83,
        "behavior": 82,
        "trend": 6,
        "noise": 6,
        "std": 6,
        "range": 14,
        "weak": 3,
        "repeat_error": 14,
        "late_homework": 0.6,
    },
    "中": {
        "base": 66,
        "knowledge": 65,
        "behavior": 64,
        "trend": 1,
        "noise": 9,
        "std": 11,
        "range": 25,
        "weak": 9,
        "repeat_error": 32,
        "late_homework": 3.0,
    },
    "坏": {
        "base": 43,
        "knowledge": 44,
        "behavior": 45,
        "trend": -5,
        "noise": 11,
        "std": 18,
        "range": 39,
        "weak": 20,
        "repeat_error": 53,
        "late_homework": 8.0,
    },
}


def _clip(x, lo=0, hi=100):
    return np.clip(x, lo, hi)


def _allocate_students(total: int) -> dict[str, int]:
    class_total = sum(GRADE_CLASS_COUNTS.values())
    raw = {grade: total * count / class_total for grade, count in GRADE_CLASS_COUNTS.items()}
    allocation = {grade: int(np.floor(value)) for grade, value in raw.items()}
    remaining = total - sum(allocation.values())
    order = sorted(raw, key=lambda grade: raw[grade] - allocation[grade], reverse=True)
    for grade in order[:remaining]:
        allocation[grade] += 1
    return allocation


def _class_plan(total: int) -> list[tuple[str, int, int]]:
    plan: list[tuple[str, int, int]] = []
    allocation = _allocate_students(total)
    for grade, student_count in allocation.items():
        class_count = GRADE_CLASS_COUNTS[grade]
        base_size = student_count // class_count
        remainder = student_count % class_count
        for class_no in range(1, class_count + 1):
            size = base_size + (1 if class_no <= remainder else 0)
            plan.append((grade, class_no, size))
    return plan


def _choose_level(rng: np.random.Generator, combination: str) -> str:
    if combination in {"体育生", "艺术生"}:
        probs = [0.16, 0.58, 0.26]
    else:
        probs = [0.25, 0.55, 0.20]
    return str(rng.choice(["好", "中", "坏"], p=probs))


def _choose_subject(rng: np.random.Generator, combination: str) -> str:
    subjects = COMBINATION_SUBJECTS[combination]
    mandatory = {"语文", "数学", "英语"}
    probs = []
    for subject in subjects:
        probs.append(0.15 if subject in mandatory else 0.55 / max(len(subjects) - 3, 1))
    return str(rng.choice(subjects, p=np.array(probs) / sum(probs)))


def _normal_score(rng: np.random.Generator, mean: float, noise: float) -> float:
    return round(float(_clip(rng.normal(mean, noise))), 1)


def _nonnegative_int(rng: np.random.Generator, mean: float, noise: float) -> int:
    return int(max(0, round(float(rng.normal(mean, noise)))))


def generate_large_test_data(path: str | Path, n: int = 5000, seed: int = 20260530) -> pd.DataFrame:
    """Generate a large synthetic high-school data set for system testing.

    The data is fully synthetic and follows the current RSM template columns.
    It contains three grades, 51 classes, six new-gaokao combinations and
    explicit high/middle/low academic strata for stress-testing charts.
    """
    rng = np.random.default_rng(seed)
    combo_names = list(COMBINATION_PROBS.keys())
    combo_probs = np.array([COMBINATION_PROBS[name] for name in combo_names], dtype=float)
    combo_probs = combo_probs / combo_probs.sum()
    grade_score_offset = {"高一": 0.0, "高二": 1.2, "高三": 2.0}
    grade_behavior_offset = {"高一": 1.5, "高二": 0.0, "高三": -1.2}
    grade_trend_offset = {"高一": 0.0, "高二": 0.8, "高三": 1.5}

    rows = []
    global_index = 1
    for grade, class_no, class_size in _class_plan(n):
        class_name = f"{grade}{class_no:02d}班"
        class_score_effect = float(rng.normal(0, 2.2))
        class_behavior_effect = float(rng.normal(0, 2.0))
        for class_seq in range(1, class_size + 1):
            combination = str(rng.choice(combo_names, p=combo_probs))
            level = _choose_level(rng, combination)
            params = LEVEL_PARAMS[level]
            subject = _choose_subject(rng, combination)
            student_type = "体育" if combination == "体育生" else "艺术" if combination == "艺术生" else "普通"

            special_score_adjust = -5.5 if combination in {"体育生", "艺术生"} else 0.0
            special_behavior_adjust = 4.0 if combination in {"体育生", "艺术生"} else 0.0
            science_subject_adjust = 2.0 if combination in {"物化生", "物化政", "物生地"} and subject in {"物理", "化学", "生物"} else 0.0
            humanities_subject_adjust = 2.0 if combination == "历地政" and subject in {"历史", "地理", "政治"} else 0.0

            base_mu = (
                params["base"]
                + grade_score_offset[grade]
                + class_score_effect
                + special_score_adjust
                + science_subject_adjust
                + humanities_subject_adjust
            )
            knowledge_mu = params["knowledge"] + grade_score_offset[grade] + class_score_effect * 0.8 + special_score_adjust * 0.7
            behavior_mu = params["behavior"] + grade_behavior_offset[grade] + class_behavior_effect + special_behavior_adjust
            trend_mu = params["trend"] + grade_trend_offset[grade]
            noise = params["noise"]

            std = max(0.5, rng.normal(params["std"], 2.5))
            score_range = max(1.0, rng.normal(params["range"], 6.0))
            weak_points = _nonnegative_int(rng, params["weak"], 3.0)
            late_homework = _nonnegative_int(rng, params["late_homework"], 1.8)
            reading_boost = 4 if combination == "艺术生" or subject == "语文" else 0
            practice_boost = 22 if subject in {"数学", "物理", "化学"} else 0

            row = {
                "学号": f"XS2026{global_index:05d}",
                "姓名": f"测试学生{global_index:05d}",
                "班级": class_name,
                "学科": subject,
                "年级": grade,
                "班内序号": class_seq,
                "选科组合": combination,
                "考生类别": student_type,
                "样本层次": level,
                "期中期末各科成绩": _normal_score(rng, base_mu, noise),
                "各科平均成绩": _normal_score(rng, base_mu, noise * 0.65),
                "总体平均成绩": _normal_score(rng, base_mu, noise * 0.70),
                "成绩标准差": round(float(std), 1),
                "成绩极差": round(float(score_range), 1),
                "成绩趋势斜率": round(float(np.clip(rng.normal(trend_mu, 5.5), -35, 35)), 1),
                "相邻考试成绩差值": round(float(np.clip(rng.normal(trend_mu, 7.0), -45, 45)), 1),
                "累计进步幅度": round(float(np.clip(rng.normal(trend_mu * 2.2, 9.0), -70, 70)), 1),
                "各章节知识点正确率": _normal_score(rng, knowledge_mu, noise),
                "高频考点掌握率": _normal_score(rng, knowledge_mu, noise * 0.9),
                "薄弱知识点数量": weak_points,
                "综合题正确率": _normal_score(rng, knowledge_mu - 2.5, noise),
                "知识点迁移题正确率": _normal_score(rng, knowledge_mu - 4.0, noise),
                "错题重复犯错率": _normal_score(rng, params["repeat_error"], 8.0),
                "课堂发言次数": _nonnegative_int(rng, {"好": 19, "中": 10, "坏": 4}[level] + special_behavior_adjust, 4.0),
                "课堂互动参与度": _normal_score(rng, behavior_mu, noise),
                "课堂专注度评分": _normal_score(rng, behavior_mu, noise),
                "课堂小组合作评分": _normal_score(rng, behavior_mu + (2 if combination in {"体育生", "艺术生"} else 0), noise),
                "作业按时提交率": _normal_score(rng, behavior_mu, noise),
                "作业迟交次数": late_homework,
                "作业质量评分": _normal_score(rng, (base_mu + behavior_mu) / 2, noise),
                "作业订正完成率": _normal_score(rng, behavior_mu, noise),
                "学习任务完成率": _normal_score(rng, behavior_mu, noise),
                "在线学习时长": round(float(max(0, rng.normal({"好": 43, "中": 28, "坏": 13}[level], 7.0))), 1),
                "资源访问次数": _nonnegative_int(rng, {"好": 96, "中": 58, "坏": 24}[level], 12.0),
                "在线测验完成率": _normal_score(rng, behavior_mu, noise),
                "视频学习完成率": _normal_score(rng, behavior_mu, noise),
                "在线讨论参与次数": _nonnegative_int(rng, {"好": 16, "中": 7, "坏": 2}[level], 3.0),
                "平台登录频率": _nonnegative_int(rng, {"好": 52, "中": 32, "坏": 15}[level], 7.0),
                "自主学习时长": round(float(max(0, rng.normal({"好": 38, "中": 23, "坏": 10}[level], 6.0))), 1),
                "课外阅读量": _nonnegative_int(rng, {"好": 17, "中": 9, "坏": 3}[level] + reading_boost, 3.0),
                "自主刷题数量": _nonnegative_int(rng, {"好": 260, "中": 135, "坏": 48}[level] + practice_boost, 38.0),
                "学习计划完成率": _normal_score(rng, behavior_mu, noise),
                "错题整理次数": _nonnegative_int(rng, {"好": 25, "中": 13, "坏": 5}[level], 4.0),
                "预习完成率": _normal_score(rng, behavior_mu, noise),
            }
            rows.append(row)
            global_index += 1

    df = pd.DataFrame(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


def generate_demo_data(path: str | Path, n: int = 120, seed: int = 2025) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        level = rng.choice([0, 1, 2, 3, 4], p=[0.10, 0.25, 0.35, 0.20, 0.10])
        # level 0 highest, 4 lowest
        base_mu = [88, 76, 63, 49, 35][level]
        behavior_mu = [86, 74, 62, 50, 38][level]
        knowledge_mu = [87, 75, 61, 48, 33][level]
        trend_mu = [12, 6, 1, -3, -8][level]
        noise = [5, 7, 9, 10, 12][level]

        subject = SUBJECTS[i % len(SUBJECTS)]
        cls = f"高一（{(i % 10) + 1}）班"
        score1 = _clip(rng.normal(base_mu, noise))
        avg = _clip(rng.normal(base_mu, noise * 0.6))
        overall = _clip(rng.normal(base_mu, noise * 0.7))
        std = abs(rng.normal([5, 8, 12, 16, 20][level], 3))
        score_range = abs(rng.normal([12, 18, 25, 32, 42][level], 7))
        slope = rng.normal(trend_mu, 6)
        last_diff = rng.normal(trend_mu, 8)
        total_progress = rng.normal(trend_mu * 2, 10)

        weak_points = int(max(0, rng.normal([2, 5, 10, 16, 24][level], 3)))
        late_homework = int(max(0, rng.normal([0, 1, 3, 6, 10][level], 2)))

        row = {
            "学号": f"S2025{str(i + 1).zfill(3)}",
            "姓名": f"学生{str(i + 1).zfill(3)}",
            "班级": cls,
            "学科": subject,
            "期中期末各科成绩": round(score1, 1),
            "各科平均成绩": round(avg, 1),
            "总体平均成绩": round(overall, 1),
            "成绩标准差": round(std, 1),
            "成绩极差": round(score_range, 1),
            "成绩趋势斜率": round(slope, 1),
            "相邻考试成绩差值": round(last_diff, 1),
            "累计进步幅度": round(total_progress, 1),
            "各章节知识点正确率": round(_clip(rng.normal(knowledge_mu, noise)), 1),
            "高频考点掌握率": round(_clip(rng.normal(knowledge_mu, noise * 0.9)), 1),
            "薄弱知识点数量": weak_points,
            "综合题正确率": round(_clip(rng.normal(knowledge_mu - 3, noise)), 1),
            "知识点迁移题正确率": round(_clip(rng.normal(knowledge_mu - 5, noise)), 1),
            "错题重复犯错率": round(_clip(rng.normal([12, 20, 32, 45, 58][level], 8)), 1),
            "课堂发言次数": int(max(0, rng.normal([22, 16, 10, 5, 2][level], 4))),
            "课堂互动参与度": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "课堂专注度评分": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "课堂小组合作评分": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "作业按时提交率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "作业迟交次数": late_homework,
            "作业质量评分": round(_clip(rng.normal((base_mu + behavior_mu) / 2, noise)), 1),
            "作业订正完成率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "学习任务完成率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "在线学习时长": round(max(0, rng.normal([42, 34, 26, 18, 10][level], 7)), 1),
            "资源访问次数": int(max(0, rng.normal([95, 75, 54, 35, 18][level], 12))),
            "在线测验完成率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "视频学习完成率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "在线讨论参与次数": int(max(0, rng.normal([18, 12, 7, 3, 1][level], 3))),
            "平台登录频率": int(max(0, rng.normal([52, 42, 30, 20, 12][level], 8))),
            "自主学习时长": round(max(0, rng.normal([38, 30, 22, 15, 8][level], 6)), 1),
            "课外阅读量": int(max(0, rng.normal([16, 12, 8, 4, 2][level], 3))),
            "自主刷题数量": int(max(0, rng.normal([260, 190, 125, 70, 35][level], 40))),
            "学习计划完成率": round(_clip(rng.normal(behavior_mu, noise)), 1),
            "错题整理次数": int(max(0, rng.normal([26, 19, 12, 7, 3][level], 4))),
            "预习完成率": round(_clip(rng.normal(behavior_mu, noise)), 1)
        }
        rows.append(row)
    df = pd.DataFrame(rows)
    if len(df) >= 12:
        missing_cols = ["高频考点掌握率", "作业订正完成率", "在线测验完成率", "自主学习时长"]
        for offset, col in enumerate(missing_cols):
            df.loc[df.index[offset::17], col] = np.nan
        # Add a few controlled synthetic anomalies so the demo can show
        # validation, invalid-value masking and median imputation in action.
        df.loc[df.index[5], "期中期末各科成绩"] = 108
        df.loc[df.index[11], "成绩趋势斜率"] = 145
        df.loc[df.index[17], "课堂发言次数"] = -3
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成学生学业发展评价系统合成数据。")
    parser.add_argument("--large", action="store_true", help="生成 5000 人大样本测试数据。")
    parser.add_argument("--n", type=int, default=5000, help="大样本测试数据人数。")
    parser.add_argument("--seed", type=int, default=20260530, help="随机种子。")
    parser.add_argument("--output", type=Path, default=None, help="输出 CSV 路径。")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    if args.large:
        output = args.output or root / "data" / "synthetic_5000_students.csv"
        generate_large_test_data(output, n=args.n, seed=args.seed)
    else:
        output = args.output or root / "data" / "demo_students.csv"
        generate_demo_data(output)
