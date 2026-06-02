# Codex 开发任务书：多模型学生学业发展评价分析系统

> 适用项目：`rsm_academic_eval_app` 本地网页分析系统  
> 推荐文件名：`CODEX_MULTI_MODEL_DEVELOPMENT.md`，放在项目根目录，与 `AGENTS.md`、`README.md` 同级。  
> 开发目标：在现有规则空间模型原型基础上，扩展为“多模型、多子页面、图表详实、可导出报告”的本地教育大数据分析系统。

---

## 0. 给 Codex 的首条任务指令

将下面这段话作为第一次交给 Codex 的任务提示词：

```text
请先阅读 AGENTS.md、CODEX_MULTI_MODEL_DEVELOPMENT.md、README.md、app.py、models/rsm.py、config/indicators.json 和现有 templates/static 文件。

目标是在现有 Flask 本地网页系统基础上，开发多模型学生学业发展评价分析系统。要求：
1. 保留现有 RSM 规则空间模型，不要删除已有功能。
2. 新增“模型中心”首页，展示所有学业发展评价模型入口。
3. 每个模型必须有独立子页面和独立 API，页面包含模型说明、数据质量、关键指标、图表、学生明细、个体诊断、建议和导出入口。
4. 所有模型必须能在演示数据下直接运行；缺少真实题目级数据、Q 矩阵、资源交互数据时，必须使用可解释的降级方案或模拟样例，不允许页面空白或报错。
5. 以 Python + Flask + Pandas + NumPy + scikit-learn + ECharts 为主，避免引入过重依赖；XGBoost、LightGBM、SHAP、statsmodels、PyTorch/TensorFlow 只能作为可选增强，不得作为系统启动必需依赖。
6. 为每个模型补充至少 3 类图表，重要模型至少 5 类图表。
7. 新增模型注册表、统一结果协议、统一图表协议、统一导出服务、统一数据预处理服务。
8. 完成后运行本地测试，确保 http://127.0.0.1:5000 能打开，所有模型子页面能访问。
```

---

## 1. 项目定位

本系统不是学生端、教师端、学校端三类门户系统，而是服务课题展示、模型验证和本地分析的“学生学业发展评价模型分析平台”。

核心闭环：

```text
数据导入 → 数据预处理 → 多模型评价 → 诊断解释 → 图表展示 → 个性化建议 → 报告导出
```

系统要体现以下研究价值：

1. 不只看考试成绩，要综合评价学生学业基础、学习过程表现和发展潜力。
2. 不只输出总分，要解释学生弱在哪里、为什么弱、未来趋势怎样、适合什么学习路径。
3. 不只展示一个模型，要构建综合评价、诊断评价、预测评价、画像分群、风险预警、学习路径推荐、可解释性分析、干预效果评价等模型族。
4. 不依赖外网，不调用外部 API，本地一键启动。
5. 默认演示数据可跑；真实数据上传后也能跑。

---

## 2. 开发硬约束

### 2.1 技术栈

继续使用现有项目技术栈：

```text
后端：Python 3.8+、Flask
数据处理：Pandas、NumPy
机器学习：scikit-learn
图表：ECharts
样式：Bootstrap 或现有 CSS
导出：CSV、Excel、JSON；PDF 可作为后期增强
```

建议更新 `requirements.txt`：

```text
Flask>=2.3
pandas>=1.5
numpy>=1.23
scikit-learn>=1.2
scipy>=1.9
openpyxl>=3.1
networkx>=3.0
joblib>=1.3
```

可选依赖，不得强制：

```text
xgboost
lightgbm
shap
statsmodels
```

开发时必须用 `try/except ImportError` 做可选增强。例如 SHAP 未安装时，页面仍用“局部贡献解释”或“置换重要性”展示。

### 2.2 不允许做的事情

1. 不要把系统改成必须登录才能访问。
2. 不要增加复杂的学生端、教师端、管理员端权限系统。
3. 不要依赖外部网络、外部数据库、外部模型 API。
4. 不要删除当前 RSM 原型、演示数据、上传入口和导出功能。
5. 不要把模型结果硬编码在模板里。所有页面数据必须来自后端模型计算。
6. 不要因为缺少真实标签、题目级数据或资源交互数据而让模型页面报错。必须提供“降级计算逻辑”。

---

## 3. 现有项目结构与目标结构

### 3.1 现有结构

```text
rsm_academic_eval_app/
├─ app.py
├─ config/indicators.json
├─ models/rsm.py
├─ utils/sample_data.py
├─ templates/base.html
├─ templates/index.html
├─ templates/results.html
├─ static/style.css
├─ static/charts.js
├─ data/demo_students.csv
├─ data/rsm_data_template.csv
├─ requirements.txt
├─ run_windows.bat
├─ run_linux_mac.sh
└─ README.md
```

### 3.2 目标结构

请按下面结构扩展，允许在不破坏现有结构的基础上微调：

```text
rsm_academic_eval_app/
├─ app.py
├─ config/
│  ├─ indicators.json
│  ├─ models_catalog.json
│  ├─ subject_indicators.json
│  ├─ recommendation_rules.json
│  └─ thresholds.json
├─ data/
│  ├─ demo_students.csv
│  ├─ demo_exam_records.csv
│  ├─ demo_knowledge_scores.csv
│  ├─ demo_item_responses.csv
│  ├─ demo_q_matrix.csv
│  ├─ demo_learning_behavior.csv
│  ├─ demo_resource_library.csv
│  ├─ demo_resource_interactions.csv
│  ├─ demo_interventions.csv
│  └─ templates/
│     ├─ wide_student_template.csv
│     ├─ exam_records_template.csv
│     ├─ item_response_template.csv
│     ├─ q_matrix_template.csv
│     ├─ resource_interactions_template.csv
│     └─ intervention_template.csv
├─ models/
│  ├─ __init__.py
│  ├─ base.py
│  ├─ registry.py
│  ├─ ahp.py
│  ├─ weighted_index.py
│  ├─ entropy_weight.py
│  ├─ topsis.py
│  ├─ grey_relation.py
│  ├─ rsm.py
│  ├─ cognitive_diagnosis.py
│  ├─ irt.py
│  ├─ weak_knowledge.py
│  ├─ trend_regression.py
│  ├─ logistic_risk.py
│  ├─ random_forest_grade.py
│  ├─ gbdt_potential.py
│  ├─ boosting_advanced.py
│  ├─ svm_classifier.py
│  ├─ time_series.py
│  ├─ clustering.py
│  ├─ latent_profile.py
│  ├─ risk_warning.py
│  ├─ anomaly_detection.py
│  ├─ bkt.py
│  ├─ dkt_lite.py
│  ├─ path_recommendation.py
│  ├─ collaborative_filtering.py
│  ├─ knowledge_graph.py
│  ├─ correlation_analysis.py
│  ├─ feature_importance.py
│  ├─ explainability.py
│  ├─ intervention_effect.py
│  └─ subject_models.py
├─ services/
│  ├─ __init__.py
│  ├─ data_service.py
│  ├─ preprocessing.py
│  ├─ chart_service.py
│  ├─ export_service.py
│  ├─ report_service.py
│  └─ validation_service.py
├─ templates/
│  ├─ base.html
│  ├─ index.html
│  ├─ model_center.html
│  ├─ model_detail.html
│  ├─ model_compare.html
│  ├─ student_profile.html
│  ├─ data_upload.html
│  ├─ results.html
│  └─ partials/
│     ├─ chart_panel.html
│     ├─ student_selector.html
│     ├─ model_explanation.html
│     ├─ data_quality.html
│     └─ recommendation_card.html
├─ static/
│  ├─ style.css
│  ├─ charts.js
│  ├─ model_pages.js
│  ├─ model_compare.js
│  └─ table_tools.js
├─ tests/
│  ├─ test_routes.py
│  ├─ test_preprocessing.py
│  ├─ test_model_protocol.py
│  ├─ test_core_models.py
│  └─ test_exports.py
├─ output/
├─ requirements.txt
├─ run_windows.bat
├─ run_linux_mac.sh
├─ README.md
├─ AGENTS.md
└─ CODEX_MULTI_MODEL_DEVELOPMENT.md
```

---

## 4. 总体架构

### 4.1 模型中心

新增一个模型中心页面：

```text
/models
```

页面展示模型卡片，按类别分组：

```text
A. 综合评分类模型
B. 诊断类模型
C. 预测类模型
D. 学生画像与分群类模型
E. 预警类模型
F. 知识追踪与学习过程模型
G. 学习路径推荐类模型
H. 解释与因果分析类模型
I. 学科专项评价模型
```

每张卡片包含：

```text
模型名称
模型类型
主要用途
输入数据要求
当前数据可用状态：完整 / 降级 / 演示
推荐图表数量
进入分析按钮
```

### 4.2 每个模型一个子页面

所有模型页面统一使用：

```text
/models/<model_id>
```

例如：

```text
/models/ahp
/models/rsm
/models/random_forest_grade
/models/subject_math
```

页面必须包括以下板块：

```text
1. 模型说明
2. 数据质量概览
3. 核心指标卡片
4. 班级/年级整体图表
5. 学生明细表
6. 个体学生诊断区
7. 模型解释与教育含义
8. 个性化建议
9. 导出按钮
```

### 4.3 统一 API

每个模型都要有对应 API：

```text
/api/models/<model_id>/run
/api/models/<model_id>/student/<student_id>
/api/models/<model_id>/export/csv
/api/models/<model_id>/export/excel
/api/models/<model_id>/charts
```

系统也要有模型总览 API：

```text
/api/models/catalog
/api/models/compare
/api/data/quality
/api/data/summary
```

---

## 5. 统一数据规范

### 5.1 支持两种数据形态

系统必须同时支持：

#### A. 宽表数据

适合当前原型和普通教师上传：

```text
student_id,name,class_name,subject,overall_score,exam_midterm,exam_final,knowledge_mastery,homework_quality,...
```

#### B. 长表数据

适合后期标准化教育大数据：

```text
student_id,subject,date,indicator_code,indicator_name,value
```

### 5.2 核心数据表

#### 5.2.1 学生基础表 `students`

```text
student_id       学号，必填，字符串
name             姓名，必填
class_name       班级，必填
grade            年级，默认高一
gender           性别，可选
subject          当前分析学科，可选
learning_style   学习风格，可选：逻辑型、读写型、实验型、听说型等
```

#### 5.2.2 指标宽表 `student_indicators`

至少包含这些通用指标，缺失则自动填补或使用降级方案：

```text
基础成绩水平
成绩波动幅度
进步退步幅度
知识点达标率
知识点应用能力
课堂互动行为
作业提交行为
在线学习行为
自主学习行为
```

建议保留 35 项三级指标字段：

```text
期中期末各科成绩
各科平均成绩
总体平均成绩
成绩标准差
成绩极差
成绩趋势斜率
相邻考试成绩差值
累计进步幅度
各章节知识点正确率
高频考点掌握率
薄弱知识点数量
综合题正确率
知识点迁移题正确率
错题重复犯错率
课堂发言次数
课堂互动参与度
课堂专注度评分
作业按时提交率
作业迟交次数
作业质量评分
作业订正完成率
在线学习时长
在线资源访问次数
在线测试完成率
在线测试正确率
学习平台登录频次
自主预习次数
自主复习次数
错题整理次数
学习计划完成率
课外阅读时长
学科拓展任务完成率
小组合作参与度
探究活动参与度
学习反思记录次数
```

### 5.3 题目级数据 `item_responses`

用于认知诊断、IRT、BKT、DKT-Lite：

```text
student_id       学号
subject          学科
exam_id          考试或练习编号
item_id          题号
knowledge_code   知识点编码，可选；如果使用 Q 矩阵，则可不填
score            得分
max_score        满分
is_correct       是否正确，0/1
answer_time      答题时长，可选
submit_time      提交时间，可选
```

### 5.4 Q 矩阵 `q_matrix`

用于认知诊断与 RSM 属性映射：

```text
item_id          题号
knowledge_code   知识点编码
knowledge_name   知识点名称
weight           题目对知识点的权重，默认 1
```

### 5.5 资源表 `resource_library`

用于学习路径、协同过滤、知识图谱推荐：

```text
resource_id      资源编号
resource_name    资源名称
subject          学科
knowledge_code   对应知识点
resource_type    微课/练习/错题包/阅读材料/实验任务/项目任务
level            基础/巩固/提升/拓展
url              可选，本地系统可为空
```

### 5.6 资源交互表 `resource_interactions`

```text
student_id       学号
resource_id      资源编号
action           view/practice/complete/like
score_gain       使用后提升幅度，可选
timestamp        时间
```

### 5.7 干预记录表 `interventions`

用于干预效果评估：

```text
student_id       学号
subject          学科
intervention_id  干预编号
intervention_type 基础补强/错题订正/阅读提升/实验训练/课堂互动提升等
start_date       开始日期
end_date         结束日期
pre_score        干预前得分
post_score       干预后得分
pre_mastery      干预前知识点掌握度
post_mastery     干预后知识点掌握度
```

---

## 6. 数据预处理要求

新增 `services/preprocessing.py`，至少实现：

```python
class PreprocessingPipeline:
    def validate_schema(self, df): ...
    def normalize_columns(self, df): ...
    def clean_outliers(self, df): ...
    def fill_missing(self, df): ...
    def normalize_scores(self, df): ...
    def derive_features(self, df): ...
    def build_model_dataset(self, raw_inputs): ...
```

### 6.1 缺失值处理

1. 数值型字段：优先使用“班级 + 学科 + 指标”的中位数填补。
2. 如果班级或学科样本不足，则使用全体中位数。
3. 如果整列缺失，则用默认值 60，并在数据质量日志中标记。
4. 分类型字段：填补为“无记录”。

### 6.2 异常值处理

1. 分数、正确率、掌握率统一限制到 `[0, 100]`。
2. 学习时长类指标限制到合理区间，例如单日学习时长不超过 12 小时。
3. 次数型指标不能为负。
4. 过大异常值用 IQR 或百分位数截尾。

### 6.3 标准化

提供两种标准化方式：

```text
Min-Max 到 0-100：用于教育解释和页面展示。
Z-score：用于机器学习和聚类建模。
```

所有模型计算结果最终要转成 0-100 或清晰概率值，便于展示。

---

## 7. 统一模型结果协议

所有模型必须返回同一种结构，便于前端复用。

新增 `models/base.py`：

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class ModelResult:
    model_id: str
    model_name: str
    category: str
    status: str                 # ok / degraded / warning / error
    status_message: str
    summary_cards: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    student_table: List[Dict[str, Any]]
    student_details: Dict[str, Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    explanations: List[Dict[str, Any]]
    data_quality: Dict[str, Any]
    export_payload: Dict[str, Any]
```

### 7.1 `summary_cards` 格式

```json
[
  {"label": "平均综合评分", "value": 72.6, "unit": "分", "trend": "+2.1"},
  {"label": "优秀/良好占比", "value": 48.5, "unit": "%", "trend": "+5.0%"},
  {"label": "需帮扶人数", "value": 12, "unit": "人", "trend": "-3"}
]
```

### 7.2 `charts` 格式

每个图表返回 ECharts option：

```json
{
  "chart_id": "score_distribution",
  "title": "综合评分分布",
  "type": "bar",
  "height": 360,
  "description": "展示不同学业等级学生人数分布。",
  "option": { }
}
```

### 7.3 `student_table` 格式

```json
[
  {
    "student_id": "S001",
    "name": "学生001",
    "class_name": "高一1班",
    "score": 78.3,
    "level": "良好",
    "risk_level": "低风险",
    "weak_points": "函数性质、课堂互动",
    "recommendation": "稳定提升路径"
  }
]
```

### 7.4 个体诊断 `student_details`

```json
{
  "S001": {
    "basic": {"name": "学生001", "class_name": "高一1班"},
    "scores": {"overall": 78.3, "knowledge": 76.0, "behavior": 75.0},
    "diagnosis": ["知识点迁移能力偏弱", "成绩波动较小"],
    "charts": [...],
    "recommendations": [...]
  }
}
```

---

## 8. 模型注册表

新增 `config/models_catalog.json`：

```json
[
  {
    "model_id": "ahp",
    "name": "AHP层次分析综合评价模型",
    "category": "综合评分类模型",
    "route": "/models/ahp",
    "api": "/api/models/ahp/run",
    "module": "models.ahp",
    "class_name": "AHPEvaluationModel",
    "description": "基于三层指标体系和权重计算学生综合学业发展得分。",
    "required_data": ["student_indicators"],
    "charts": ["radar", "stacked_bar", "histogram", "heatmap", "waterfall"],
    "priority": 1
  }
]
```

新增 `models/registry.py`：

```python
class ModelRegistry:
    def list_models(self): ...
    def get_model(self, model_id): ...
    def run_model(self, model_id, dataset, params=None): ...
```

`app.py` 不要为每个模型写大量重复逻辑，应通过 registry 动态加载。

---

## 9. 路由设计

### 9.1 页面路由

```python
@app.route('/')
def index(): ...

@app.route('/models')
def model_center(): ...

@app.route('/models/<model_id>')
def model_detail(model_id): ...

@app.route('/models/compare')
def model_compare(): ...

@app.route('/students/<student_id>')
def student_profile(student_id): ...

@app.route('/data/upload')
def data_upload(): ...
```

### 9.2 API 路由

```python
@app.route('/api/models/catalog')
def api_models_catalog(): ...

@app.route('/api/models/<model_id>/run')
def api_run_model(model_id): ...

@app.route('/api/models/<model_id>/student/<student_id>')
def api_model_student_detail(model_id, student_id): ...

@app.route('/api/models/compare')
def api_model_compare(): ...

@app.route('/api/data/quality')
def api_data_quality(): ...

@app.route('/api/export/<model_id>/<fmt>')
def api_export_model(model_id, fmt): ...
```

---

## 10. 前端页面设计

### 10.1 模型中心页 `model_center.html`

必须展示：

```text
顶部：系统名称、数据状态、当前样本数、最近导入时间
筛选：模型类别、是否需要题目级数据、是否可降级运行
模型卡片：名称、功能、图表数量、推荐优先级、进入按钮
底部：模型开发状态表
```

### 10.2 模型详情页 `model_detail.html`

统一结构：

```text
左侧：模型导航、学生筛选、班级筛选、学科筛选
右侧：模型内容
  1. 模型说明卡
  2. 数据质量卡
  3. 核心指标卡
  4. 图表区
  5. 学生明细表
  6. 个体诊断抽屉/区域
  7. 建议与报告导出
```

### 10.3 图表区布局

重要模型至少 5 个图表，普通模型至少 3 个图表。

优先使用这些图表类型：

```text
柱状图：等级人数、指标均分、特征重要性
折线图：成绩趋势、掌握度变化、干预前后变化
雷达图：三大核心特征、学科能力结构
散点图：RSM Theta-Zeta、聚类分布、TOPSIS距离
热力图：学生-知识点掌握、相关系数矩阵、Q矩阵
箱线图：班级分布、异常值检测
桑基图：知识点 → 薄弱点 → 推荐资源
关系图：知识图谱、资源图谱
树状图：层次聚类结果
仪表盘：风险概率、综合评分
瀑布图：个体解释贡献
```

---

## 11. 模型开发总表

| 序号 | model_id | 模型名称 | 类别 | 页面路由 | 重点图表 |
|---:|---|---|---|---|---|
| 1 | ahp | AHP层次分析综合评价模型 | 综合评价 | `/models/ahp` | 雷达、堆叠柱、热力图 |
| 2 | weighted_index | 加权综合指数模型 | 综合评价 | `/models/weighted_index` | 指标柱状、贡献瀑布、等级分布 |
| 3 | entropy_weight | 熵权法客观赋权模型 | 综合评价 | `/models/entropy_weight` | 权重柱状、信息熵热力图、排名图 |
| 4 | topsis | TOPSIS优劣解评价模型 | 综合评价 | `/models/topsis` | 理想解距离散点、接近度排名、雷达 |
| 5 | grey_relation | 灰色关联评价模型 | 综合评价 | `/models/grey_relation` | 关联度柱状、轨迹折线、热力图 |
| 6 | rsm | 规则空间诊断模型 | 诊断评价 | `/models/rsm` | Theta-Zeta散点、属性热力图、理想状态匹配 |
| 7 | cognitive_diagnosis | 认知诊断模型DINA/DINO/G-DINA | 诊断评价 | `/models/cognitive_diagnosis` | 知识点掌握热力图、Q矩阵图、属性模式图 |
| 8 | irt | IRT能力测量模型 | 诊断评价 | `/models/irt` | 能力分布、题目难度散点、ICC曲线 |
| 9 | weak_knowledge | 薄弱知识点诊断模型 | 诊断评价 | `/models/weak_knowledge` | 薄弱点帕累托、知识点热力图、学生雷达 |
| 10 | trend_regression | 成绩趋势回归模型 | 预测评价 | `/models/trend_regression` | 趋势折线、斜率分布、进退步散点 |
| 11 | logistic_risk | 逻辑回归风险预测模型 | 预测评价 | `/models/logistic_risk` | 风险概率、系数柱状、混淆矩阵 |
| 12 | random_forest_grade | 随机森林学业分级模型 | 预测评价 | `/models/random_forest_grade` | 等级预测、特征重要性、混淆矩阵 |
| 13 | gbdt_potential | GBDT进步潜力预测模型 | 预测评价 | `/models/gbdt_potential` | 潜力分布、预测提升、特征重要性 |
| 14 | boosting_advanced | XGBoost/LightGBM增强预测模型 | 预测评价 | `/models/boosting_advanced` | 模型对比、特征重要性、误差分布 |
| 15 | svm_classifier | SVM学业分类模型 | 预测评价 | `/models/svm_classifier` | 分类边界、等级预测、支持向量摘要 |
| 16 | time_series | 时间序列发展预测模型 | 预测评价 | `/models/time_series` | 移动平均、预测折线、波动箱线图 |
| 17 | kmeans_profile | K-means学生画像聚类模型 | 学生画像 | `/models/kmeans_profile` | 聚类散点、画像雷达、类别人数 |
| 18 | hierarchical_cluster | 层次聚类分层模型 | 学生画像 | `/models/hierarchical_cluster` | 树状图、分层热力图、群体雷达 |
| 19 | latent_profile | 潜在类别/潜在剖面模型 | 学生画像 | `/models/latent_profile` | BIC曲线、类别雷达、概率分布 |
| 20 | risk_warning | 学业风险预警模型 | 风险预警 | `/models/risk_warning` | 红橙黄绿预警、风险矩阵、重点学生表 |
| 21 | anomaly_detection | 异常学生识别模型 | 风险预警 | `/models/anomaly_detection` | 异常散点、箱线图、异常类型分布 |
| 22 | bkt | 贝叶斯知识追踪模型 | 知识追踪 | `/models/bkt` | 掌握概率曲线、知识点轨迹、状态表 |
| 23 | dkt_lite | DKT-Lite深度知识追踪近似模型 | 知识追踪 | `/models/dkt_lite` | 序列预测、下一题正确率、掌握变化 |
| 24 | rule_path_recommendation | 基于规则的学习路径推荐模型 | 路径推荐 | `/models/rule_path_recommendation` | 路径分布、薄弱点到资源桑基图、建议卡 |
| 25 | collaborative_filtering | 协同过滤资源推荐模型 | 路径推荐 | `/models/collaborative_filtering` | 相似学生图、资源推荐排行、提升收益 |
| 26 | knowledge_graph | 知识图谱学习推荐模型 | 路径推荐 | `/models/knowledge_graph` | 知识关系图、路径图、资源匹配图 |
| 27 | correlation_analysis | 指标相关性分析模型 | 解释分析 | `/models/correlation_analysis` | 相关矩阵、散点矩阵、强相关排行 |
| 28 | feature_importance | 特征重要性解释模型 | 解释分析 | `/models/feature_importance` | 重要性柱状、分组重要性、稳定性图 |
| 29 | explainability | SHAP/局部贡献个体解释模型 | 解释分析 | `/models/explainability` | 瀑布图、贡献条形图、个体解释表 |
| 30 | intervention_effect | 干预效果评估模型 | 效果评价 | `/models/intervention_effect` | 前后测折线、提升幅度、效果量分布 |
| 31 | subject_chinese | 语文学科专项评价模型 | 学科专项 | `/models/subject_chinese` | 阅读写作雷达、作文趋势、文言薄弱点 |
| 32 | subject_math | 数学学科专项评价模型 | 学科专项 | `/models/subject_math` | 函数数列雷达、解题趋势、题型热力图 |
| 33 | subject_english | 英语学科专项评价模型 | 学科专项 | `/models/subject_english` | 听说读写雷达、词汇掌握、作文趋势 |
| 34 | subject_physics | 物理学科专项评价模型 | 学科专项 | `/models/subject_physics` | 实验能力、力学掌握、计算题趋势 |
| 35 | subject_biology | 生物学科专项评价模型 | 学科专项 | `/models/subject_biology` | 实验探究、细胞遗传模块、知识网络 |
| 36 | subject_history | 历史学科专项评价模型 | 学科专项 | `/models/subject_history` | 时序图、材料分析、历史解释能力 |

---

# 12. 各模型详细开发要求

下面每个模型都要实现：

```python
class XxxModel(BaseEvaluationModel):
    model_id = "xxx"
    model_name = "xxx"
    category = "xxx"

    def run(self, dataset, params=None) -> ModelResult:
        ...
```

---

## 12.1 AHP 层次分析综合评价模型

### 文件与路由

```text
文件：models/ahp.py
页面：/models/ahp
API：/api/models/ahp/run
```

### 功能目标

基于“三大一级指标—二级指标—三级指标”的层次结构，计算学生综合学业发展分数和等级。

### 输入

```text
student_indicators 宽表或长表
config/indicators.json 权重配置
```

### 核心算法

```text
二级指标得分 = Σ 三级指标标准化得分 × 三级指标权重
一级指标得分 = Σ 二级指标得分 × 二级指标权重
综合评分 = 成绩波动趋势 × 0.35 + 知识点掌握度 × 0.35 + 学习行为活跃度 × 0.30
```

### 输出

```text
综合评分
一级指标得分
二级指标得分
学业等级：优秀、良好、中等、待提高、需帮扶
优势指标 Top 3
薄弱指标 Bottom 3
```

### 图表

至少 5 个：

```text
1. 综合评分等级分布柱状图
2. 三大一级指标班级均分雷达图
3. 学生-一级指标热力图
4. 二级指标贡献堆叠柱状图
5. 单个学生综合评分贡献瀑布图
```

### 页面解释

用通俗语言展示：

```text
该模型体现“综合、过程、发展”的评价思想。分数不是单一考试成绩，而是由成绩趋势、知识掌握和学习行为共同决定。
```

### 验收

```text
1. 与手动权重计算误差小于 0.01。
2. 每个学生都有综合评分和等级。
3. 缺少部分三级指标时仍能通过二级/一级均值降级计算。
```

---

## 12.2 加权综合指数模型

### 文件与路由

```text
文件：models/weighted_index.py
页面：/models/weighted_index
API：/api/models/weighted_index/run
```

### 功能目标

提供一个比 AHP 更直观的手动权重模型，便于教师调整指标权重、比较不同权重策略下的评价结果。

### 输入

```text
学生标准化指标
config/thresholds.json
可选前端权重参数
```

### 核心算法

```text
综合指数 = Σ 指标标准化得分 × 指标权重
```

默认权重：

```text
基础成绩水平 20%
成绩进步趋势 15%
知识点掌握度 30%
学习行为活跃度 20%
作业完成质量 15%
```

### 输出

```text
综合指数
排名
等级
权重贡献
可调权重对比
```

### 图表

```text
1. 综合指数排名柱状图
2. 指标权重饼图或环形图
3. 学生指标贡献瀑布图
4. 权重调整前后排名变化折线图
5. 不同班级综合指数箱线图
```

### 特殊要求

前端允许用户临时调整权重，但不要写死到全局配置，除非点击“保存配置”。

---

## 12.3 熵权法客观赋权模型

### 文件与路由

```text
文件：models/entropy_weight.py
页面：/models/entropy_weight
API：/api/models/entropy_weight/run
```

### 功能目标

根据数据本身的离散程度自动分配权重，作为 AHP 主观赋权的对照模型。

### 核心算法

对正向化后的指标矩阵 `X`：

```text
p_ij = x_ij / Σ_i x_ij
e_j = - 1 / ln(n) × Σ_i p_ij ln(p_ij)
d_j = 1 - e_j
w_j = d_j / Σ_j d_j
score_i = Σ_j w_j × x_ij
```

### 输出

```text
每个指标的信息熵
每个指标的差异系数
客观权重
学生综合得分
与 AHP 得分的差异
```

### 图表

```text
1. 熵权法指标权重柱状图
2. 指标信息熵热力图
3. AHP权重 vs 熵权法权重对比图
4. 学生熵权得分排名图
5. AHP评分与熵权评分散点图
```

### 解释要求

页面说明：

```text
当某指标在学生之间差异较大时，说明它具有更强区分能力，熵权法会自动提高该指标权重。
```

---

## 12.4 TOPSIS 优劣解距离评价模型

### 文件与路由

```text
文件：models/topsis.py
页面：/models/topsis
API：/api/models/topsis/run
```

### 功能目标

计算每名学生距离“理想学生状态”和“最差学生状态”的距离，得到相对接近度。

### 核心算法

```text
1. 指标正向化
2. 标准化矩阵
3. 加权标准化
4. 构造正理想解 A+ 与负理想解 A-
5. 计算 D+ 和 D-
6. 接近度 C = D- / (D+ + D-)
```

### 输出

```text
正理想距离 D+
负理想距离 D-
接近度 C
TOPSIS排名
学生优劣势解释
```

### 图表

```text
1. 正负理想解距离散点图
2. TOPSIS接近度排名条形图
3. 理想解雷达对比图
4. 学生与理想状态差距热力图
5. 班级接近度分布直方图
```

---

## 12.5 灰色关联评价模型

### 文件与路由

```text
文件：models/grey_relation.py
页面：/models/grey_relation
API：/api/models/grey_relation/run
```

### 功能目标

评价学生发展轨迹与“优秀发展轨迹”的相似程度，适合样本量不大但指标较多的教育场景。

### 核心算法

```text
参考序列：优秀学生或理想学生画像
比较序列：每个学生的多指标序列
Δ_ij = |x0_j - xi_j|
γ_ij = (Δ_min + ρΔ_max) / (Δ_ij + ρΔ_max)
关联度 r_i = Σ w_j × γ_ij
```

`ρ` 默认 0.5。

### 输出

```text
灰色关联度
最相似优秀画像
指标关联贡献
发展轨迹解释
```

### 图表

```text
1. 学生灰色关联度排名柱状图
2. 典型学生与优秀轨迹折线对比图
3. 指标关联贡献热力图
4. 班级关联度分布图
5. 低关联学生名单表
```

---

## 12.6 规则空间诊断模型 RSM

### 文件与路由

```text
文件：models/rsm.py，保留并扩展现有实现
页面：/models/rsm
API：/api/models/rsm/run
```

### 功能目标

诊断学生的属性掌握模式，并通过 `Theta` 和 `Zeta` 表示学生掌握程度与理想状态偏离程度。

### 输入

```text
学生指标数据
知识属性配置
可选 Q 矩阵
```

### 属性建议

```text
A1 基础成绩水平
A2 成绩稳定性
A3 进步趋势
A4 知识点达标率
A5 知识点应用能力
A6 课堂互动行为
A7 作业提交行为
A8 在线学习行为
A9 自主学习行为
```

### 核心算法

```text
1. 将连续指标二值化为掌握/未掌握
2. 生成教育逻辑允许的理想属性模式
3. 计算学生属性模式与理想模式的距离
4. Theta = 属性掌握比例或加权掌握度
5. Zeta = 与最近理想模式的偏离度
6. 根据 Theta、Zeta 和综合评分给出等级与建议
```

### 输出

```text
Theta
Zeta
属性掌握向量
最近理想状态
薄弱属性
诊断等级
个性化建议
```

### 图表

```text
1. Theta-Zeta规则空间散点图
2. 学生-属性掌握热力图
3. 理想状态匹配矩阵图
4. 属性薄弱率柱状图
5. 个体属性雷达图
6. RSM诊断等级分布图
```

### 重要要求

RSM 是当前系统的核心特色模型，页面必须比普通模型更完整，模型说明要突出“可解释诊断”。

---

## 12.7 认知诊断模型 DINA/DINO/G-DINA

### 文件与路由

```text
文件：models/cognitive_diagnosis.py
页面：/models/cognitive_diagnosis
API：/api/models/cognitive_diagnosis/run
```

### 功能目标

基于题目作答数据和 Q 矩阵，诊断学生对每个知识点的掌握状态。

### 输入

```text
item_responses
q_matrix
```

### 降级方案

如果缺少题目级数据或 Q 矩阵：

```text
1. 根据知识点掌握度、章节正确率、综合题正确率等指标构造模拟知识点掌握表。
2. 页面状态标记为 degraded。
3. 说明“当前为指标级近似诊断，上传题目级作答数据和 Q 矩阵后可启用完整认知诊断”。
```

### 核心算法

简化 DINA：

```text
η_ij = Π_k α_ik ^ q_jk
P(X_ij=1 | α_i) = (1 - s_j)^η_ij × g_j^(1-η_ij)
```

其中：

```text
α_ik：学生 i 对知识点 k 是否掌握
q_jk：题目 j 是否考查知识点 k
s_j：失误率
g_j：猜测率
```

如果实现完整 EM 太复杂，首版可用穷举属性模式 + 最大似然近似；知识点数量超过 12 时用阈值降级。

### 输出

```text
每个知识点掌握概率
掌握/未掌握状态
知识点组合模式
易错题目
诊断建议
```

### 图表

```text
1. 学生-知识点掌握概率热力图
2. Q矩阵热力图
3. 知识点掌握率班级柱状图
4. 个体知识点雷达图
5. 题目正确率与知识点关系图
6. 属性模式人数分布图
```

---

## 12.8 IRT 能力测量模型

### 文件与路由

```text
文件：models/irt.py
页面：/models/irt
API：/api/models/irt/run
```

### 功能目标

估计学生潜在能力值、题目难度和题目区分度，辅助试题质量分析和学生能力测量。

### 输入

```text
item_responses
```

### 降级方案

如果没有题目级数据：

```text
使用考试成绩和题目得分率模拟 Rasch 近似，不做严格心理测量结论。
页面标记 degraded。
```

### 核心算法

首版实现 Rasch 近似：

```text
P(X=1) = 1 / (1 + exp(-(θ_i - b_j)))
```

可通过学生正确率 logit 近似 `θ`，题目错误率 logit 近似 `b`。

可选增强：2PL。

### 输出

```text
学生能力 theta
题目难度 b
题目区分度 a，可选
能力等级
异常题目提示
```

### 图表

```text
1. 学生能力分布直方图
2. 题目难度-正确率散点图
3. 题目特征曲线 ICC
4. 能力值与考试分数散点图
5. 题目区分度排行图
```

---

## 12.9 薄弱知识点诊断模型

### 文件与路由

```text
文件：models/weak_knowledge.py
页面：/models/weak_knowledge
API：/api/models/weak_knowledge/run
```

### 功能目标

快速识别个人、班级、学科层面的薄弱知识点和能力短板。

### 核心规则

```text
掌握率 < 40：严重薄弱
40 ≤ 掌握率 < 55：需帮扶
55 ≤ 掌握率 < 70：待提高
70 ≤ 掌握率 < 85：基本掌握
≥ 85：熟练掌握
```

### 输出

```text
个人薄弱知识点清单
班级共性薄弱点
薄弱程度等级
补救优先级
推荐资源
```

### 图表

```text
1. 班级薄弱知识点帕累托图
2. 学生-知识点热力图
3. 个体知识点雷达图
4. 薄弱程度等级堆叠柱状图
5. 知识点掌握率趋势折线图
```

---

## 12.10 成绩趋势回归模型

### 文件与路由

```text
文件：models/trend_regression.py
页面：/models/trend_regression
API：/api/models/trend_regression/run
```

### 功能目标

分析学生成绩随时间变化的斜率，判断进步、稳定或退步趋势。

### 输入

```text
exam_records
如果没有 exam_records，则使用宽表中的期初、月考、期中、期末等字段构造序列。
```

### 核心算法

对每个学生每个学科拟合：

```text
score_t = a + b × time_t
```

输出：

```text
b > 1.5：快速进步
0.3 < b ≤ 1.5：稳步进步
-0.3 ≤ b ≤ 0.3：基本稳定
-1.5 ≤ b < -0.3：轻微退步
b < -1.5：明显退步
```

### 输出

```text
趋势斜率
R²
最近一次成绩
预测下一次成绩
趋势类别
```

### 图表

```text
1. 典型学生成绩趋势折线图
2. 班级趋势斜率分布直方图
3. 起始成绩-趋势斜率散点图
4. 进步/稳定/退步人数堆叠图
5. 预测成绩误差图
```

---

## 12.11 逻辑回归风险预测模型

### 文件与路由

```text
文件：models/logistic_risk.py
页面：/models/logistic_risk
API：/api/models/logistic_risk/run
```

### 功能目标

预测学生是否存在学业风险，输出风险概率和影响因素。

### 标签来源

优先级：

```text
1. 如果数据中有 risk_label，使用真实标签。
2. 如果没有标签，则用规则生成伪标签：综合评分 < 55 或知识掌握 < 55 或连续退步。
3. 页面标记“当前使用规则标签训练，仅供模型展示和初步预警”。
```

### 核心算法

```text
LogisticRegression(class_weight='balanced')
```

### 输出

```text
风险概率
风险等级
主要正向/负向因素
模型准确率，若有验证集
```

### 图表

```text
1. 风险概率分布图
2. 逻辑回归系数柱状图
3. 风险学生名单表
4. 混淆矩阵，若可用
5. ROC曲线，若可用
```

---

## 12.12 随机森林学业分级模型

### 文件与路由

```text
文件：models/random_forest_grade.py
页面：/models/random_forest_grade
API：/api/models/random_forest_grade/run
```

### 功能目标

基于多维特征预测学生学业等级，并输出特征重要性。

### 标签来源

```text
1. 如果有 grade_label，使用真实等级。
2. 如果没有，按综合评分生成：优秀/良好/中等/待提高/需帮扶。
```

### 核心算法

```python
RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    random_state=42,
    class_weight="balanced"
)
```

### 输出

```text
预测等级
等级概率
特征重要性
模型准确率
容易误判的等级
```

### 图表

```text
1. 预测等级人数分布图
2. 特征重要性 Top 20 柱状图
3. 等级概率堆叠柱状图
4. 混淆矩阵热力图
5. 学生得分与预测等级散点图
```

---

## 12.13 GBDT 进步潜力预测模型

### 文件与路由

```text
文件：models/gbdt_potential.py
页面：/models/gbdt_potential
API：/api/models/gbdt_potential/run
```

### 功能目标

预测学生未来综合评分或学科成绩提升幅度，判断进步潜力。

### 标签来源

```text
1. 如果有未来成绩或后测成绩，使用真实提升幅度。
2. 如果没有，使用趋势斜率 + 学习行为提升构造潜力标签。
```

### 核心算法

```python
GradientBoostingRegressor(random_state=42)
```

### 输出

```text
预测提升分数
进步潜力类别：快速进步、稳步进步、波动观察、潜力待激发、学业预警
推动因素
制约因素
```

### 图表

```text
1. 预测提升幅度分布图
2. 潜力类别人数柱状图
3. 特征重要性图
4. 实际提升 vs 预测提升散点图，若有真实后测
5. 个体潜力解释瀑布图
```

---

## 12.14 XGBoost/LightGBM 增强预测模型

### 文件与路由

```text
文件：models/boosting_advanced.py
页面：/models/boosting_advanced
API：/api/models/boosting_advanced/run
```

### 功能目标

作为增强机器学习模型页面，比较 XGBoost、LightGBM 与 sklearn GBDT 的效果。

### 依赖要求

```text
如果安装 xgboost，则启用 XGBoost。
如果安装 lightgbm，则启用 LightGBM。
如果均未安装，则使用 GradientBoostingClassifier/Regressor 作为 fallback。
```

### 输出

```text
模型名称
预测结果
准确率/MAE/RMSE
特征重要性
不同模型对比
```

### 图表

```text
1. 模型性能对比柱状图
2. 特征重要性对比图
3. 预测误差分布图
4. 学生预测等级对比表
5. 模型可用状态提示卡
```

---

## 12.15 SVM 学业分类模型

### 文件与路由

```text
文件：models/svm_classifier.py
页面：/models/svm_classifier
API：/api/models/svm_classifier/run
```

### 功能目标

用支持向量机进行学业等级、风险状态或偏科类型分类。

### 核心算法

```python
Pipeline([
    ("scaler", StandardScaler()),
    ("svm", SVC(kernel="rbf", probability=True, class_weight="balanced"))
])
```

### 输出

```text
分类结果
分类概率
支持向量数量
模型准确率
```

### 图表

```text
1. PCA二维降维分类散点图
2. 等级预测人数图
3. 分类概率箱线图
4. 混淆矩阵
5. 高不确定学生列表
```

---

## 12.16 时间序列发展预测模型

### 文件与路由

```text
文件：models/time_series.py
页面：/models/time_series
API：/api/models/time_series/run
```

### 功能目标

分析学生成绩、知识点掌握度、学习行为随时间变化的轨迹，并预测短期发展趋势。

### 首版算法

```text
移动平均
指数平滑
趋势斜率
波动系数
短期外推预测
```

可选增强：如果安装 statsmodels，可使用 ARIMA；否则不启用。

### 输出

```text
未来一次预测分数
趋势类别
波动强度
稳定性等级
```

### 图表

```text
1. 原始序列 + 移动平均折线图
2. 预测结果折线图
3. 学生波动系数箱线图
4. 班级趋势热力图
5. 典型学生轨迹对比图
```

---

## 12.17 K-means 学生画像聚类模型

### 文件与路由

```text
文件：models/clustering.py
类：KMeansProfileModel
页面：/models/kmeans_profile
API：/api/models/kmeans_profile/run
```

### 功能目标

根据多维指标自动识别学生类型。

### 推荐聚类标签

聚类后根据中心点自动命名：

```text
高成绩高行为型
高成绩低行为型
低成绩高努力型
低成绩低行为型
成绩波动型
偏科风险型
```

### 核心算法

```python
KMeans(n_clusters=5, random_state=42)
PCA(n_components=2) 用于可视化
```

### 输出

```text
聚类编号
画像名称
画像解释
每类学生人数
每类干预建议
```

### 图表

```text
1. PCA二维聚类散点图
2. 各类学生人数柱状图
3. 聚类中心雷达图
4. 学生画像热力图
5. 每类典型学生表
```

---

## 12.18 层次聚类分层模型

### 文件与路由

```text
文件：models/clustering.py
类：HierarchicalClusterModel
页面：/models/hierarchical_cluster
API：/api/models/hierarchical_cluster/run
```

### 功能目标

形成可解释的层级分群，便于班级分层教学。

### 核心算法

```python
AgglomerativeClustering
scipy.cluster.hierarchy.linkage 用于树状图数据
```

### 输出

```text
分层类别
层级距离
群体画像
分层教学建议
```

### 图表

```text
1. 层次聚类树状图
2. 分层类别热力图
3. 群体雷达图
4. 班级分层人数图
5. 分层教学建议表
```

---

## 12.19 潜在类别/潜在剖面模型

### 文件与路由

```text
文件：models/latent_profile.py
页面：/models/latent_profile
API：/api/models/latent_profile/run
```

### 功能目标

用概率模型识别隐藏的学生类型，作为 K-means 的高级对照。

### 核心算法

```python
GaussianMixture(n_components=k, covariance_type="full", random_state=42)
```

尝试 `k=2..6`，用 BIC 选择最佳类别数。

### 输出

```text
潜在类别
类别概率
BIC/AIC
类别画像
不确定学生
```

### 图表

```text
1. BIC选择曲线
2. 潜在类别人数柱状图
3. 类别画像雷达图
4. 类别概率热力图
5. 高不确定学生表
```

---

## 12.20 学业风险预警模型

### 文件与路由

```text
文件：models/risk_warning.py
页面：/models/risk_warning
API：/api/models/risk_warning/run
```

### 功能目标

综合多指标识别红、橙、黄、绿四类预警学生。

### 风险规则

```text
红色预警：综合评分 < 40 或连续退步且知识掌握 < 50
橙色预警：40 ≤ 综合评分 < 55 或知识掌握 < 55
黄色预警：55 ≤ 综合评分 < 70 或成绩波动大或行为活跃度低
绿色正常：综合评分 ≥ 70 且无明显异常
```

### 输出

```text
预警颜色
风险原因
干预优先级
班级重点关注名单
建议措施
```

### 图表

```text
1. 红橙黄绿预警人数仪表/柱状图
2. 风险因素矩阵热力图
3. 综合评分-波动幅度风险散点图
4. 重点关注学生表
5. 班级风险地图
```

---

## 12.21 异常学生识别模型

### 文件与路由

```text
文件：models/anomaly_detection.py
页面：/models/anomaly_detection
API：/api/models/anomaly_detection/run
```

### 功能目标

识别成绩突降、行为突变、数据异常、偏科异常等特殊情况。

### 算法

```text
Z-score异常检测
IQR箱线图异常检测
IsolationForest
OneClassSVM，可选
```

### 异常类型

```text
成绩突降型
学习行为骤降型
成绩与行为不一致型
偏科极端型
数据录入异常型
```

### 输出

```text
异常分数
异常类型
异常指标
异常说明
处理建议
```

### 图表

```text
1. 异常检测散点图
2. 指标箱线图
3. 异常类型分布图
4. 个体异常指标雷达图
5. 异常学生清单
```

---

## 12.22 贝叶斯知识追踪 BKT 模型

### 文件与路由

```text
文件：models/bkt.py
页面：/models/bkt
API：/api/models/bkt/run
```

### 功能目标

基于学生连续练习记录，估计某知识点的掌握概率变化。

### 输入

```text
item_responses 按时间排序
knowledge_code
```

### 参数

```text
P(L0)：初始掌握概率，默认 0.30
P(T)：学习转移概率，默认 0.15
P(G)：猜测概率，默认 0.20
P(S)：失误概率，默认 0.10
```

### 更新公式

答对：

```text
P(L|correct) = P(L)(1-S) / [P(L)(1-S) + (1-P(L))G]
```

答错：

```text
P(L|wrong) = P(L)S / [P(L)S + (1-P(L))(1-G)]
```

学习转移：

```text
P(L_next) = P(L_post) + (1 - P(L_post))T
```

### 输出

```text
每次练习后的掌握概率
最终掌握概率
是否建议进入下一知识点
是否需要补救
```

### 图表

```text
1. 知识点掌握概率曲线
2. 学生-知识点最终掌握概率热力图
3. 答题序列正确/错误标记图
4. 知识点达标人数图
5. 个体学习轨迹表
```

---

## 12.23 DKT-Lite 深度知识追踪近似模型

### 文件与路由

```text
文件：models/dkt_lite.py
页面：/models/dkt_lite
API：/api/models/dkt_lite/run
```

### 功能目标

展示深度知识追踪思想，但不强制引入深度学习框架。用序列特征近似预测下一次答题正确概率。

### 特征

```text
最近5次正确率
累计正确率
连续答对次数
连续答错次数
知识点历史练习次数
上一次答题结果
平均答题时长
```

### 算法

```text
首选：MLPClassifier
降级：LogisticRegression
```

### 输出

```text
下一题正确概率
知识点掌握趋势
高风险知识点
推荐复习顺序
```

### 图表

```text
1. 下一题正确概率曲线
2. 序列特征重要性图
3. 学生知识追踪热力图
4. 知识点预测风险排行
5. 个体序列诊断表
```

---

## 12.24 基于规则的学习路径推荐模型

### 文件与路由

```text
文件：models/path_recommendation.py
类：RulePathRecommendationModel
页面：/models/rule_path_recommendation
API：/api/models/rule_path_recommendation/run
```

### 功能目标

根据综合等级、薄弱知识点、学习行为和学科特点，生成个性化学习路径。

### 路径类型

```text
优秀：拓展拔高路径
良好：能力提升路径
中等：基础巩固路径
待提高：基础补漏+方法指导路径
需帮扶：低起点帮扶路径
```

### 规则示例

```text
IF 知识点掌握度 < 60 THEN 推荐基础补强路径
IF 成绩波动幅度 > 20 THEN 推荐稳定训练路径
IF 学习行为活跃度 < 60 THEN 推荐行为改善路径
IF 综合评分 >= 85 THEN 推荐拓展探究路径
IF 学科 = 数学 AND 函数模块 < 70 THEN 推荐函数专题训练
```

### 输出

```text
路径名称
学习目标
学习内容
资源推荐
每周安排
反馈周期
```

### 图表

```text
1. 学习路径类型人数分布图
2. 薄弱点 → 推荐资源桑基图
3. 学生路径匹配表
4. 学科路径雷达图
5. 学习任务进度模拟图
```

---

## 12.25 协同过滤资源推荐模型

### 文件与路由

```text
文件：models/collaborative_filtering.py
页面：/models/collaborative_filtering
API：/api/models/collaborative_filtering/run
```

### 功能目标

根据相似学生的资源使用效果，推荐学习资源。

### 输入

```text
resource_interactions
resource_library
student_indicators
```

### 降级方案

没有资源交互数据时：

```text
根据学生画像相似度 + 资源知识点匹配度进行内容推荐。
```

### 算法

```text
学生-资源矩阵
学生相似度 cosine_similarity
资源得分 = 相似学生使用效果加权平均
```

### 输出

```text
推荐资源 Top N
推荐理由
相似学生群体
预期提升方向
```

### 图表

```text
1. 相似学生网络图
2. 推荐资源排行图
3. 资源类型分布图
4. 资源使用效果散点图
5. 学生-资源匹配热力图
```

---

## 12.26 知识图谱学习推荐模型

### 文件与路由

```text
文件：models/knowledge_graph.py
页面：/models/knowledge_graph
API：/api/models/knowledge_graph/run
```

### 功能目标

建立“知识点—能力—题型—资源—学习路径”的关系图，按薄弱点推荐学习路径。

### 图谱节点

```text
学生
学科
知识点
能力
题型
资源
学习任务
```

### 图谱边

```text
学生 - 薄弱于 - 知识点
知识点 - 依赖 - 前置知识点
知识点 - 对应 - 题型
知识点 - 推荐 - 资源
资源 - 支持 - 能力
```

### 输出

```text
薄弱知识点的前置链条
推荐资源路径
学习顺序
关键节点解释
```

### 图表

```text
1. 知识图谱关系图
2. 学习路径链路图
3. 薄弱知识点前置依赖图
4. 资源匹配度排行图
5. 学生个体推荐路径图
```

---

## 12.27 指标相关性分析模型

### 文件与路由

```text
文件：models/correlation_analysis.py
页面：/models/correlation_analysis
API：/api/models/correlation_analysis/run
```

### 功能目标

分析指标之间、指标与成绩之间、行为与知识掌握之间的相关关系。

### 算法

```text
Pearson相关
Spearman相关
偏相关，可选
```

### 输出

```text
相关系数矩阵
强相关指标对
弱相关指标对
教育解释
```

### 图表

```text
1. 相关系数热力图
2. 强相关指标对排行图
3. 指标散点图矩阵，选择前几个核心指标
4. 行为指标与综合评分散点图
5. 班级相关性对比图
```

---

## 12.28 特征重要性解释模型

### 文件与路由

```text
文件：models/feature_importance.py
页面：/models/feature_importance
API：/api/models/feature_importance/run
```

### 功能目标

解释哪些指标最影响综合评分、学业等级、风险预警和进步潜力。

### 算法

```text
随机森林重要性
GBDT重要性
Permutation Importance
线性模型系数，作为对照
```

### 输出

```text
全局特征重要性
一级指标重要性
二级指标重要性
模型间重要性一致性
```

### 图表

```text
1. 特征重要性 Top 20 柱状图
2. 一级指标重要性环形图
3. 不同模型重要性对比热力图
4. 重要性稳定性图
5. 重要特征解释表
```

---

## 12.29 SHAP/局部贡献个体解释模型

### 文件与路由

```text
文件：models/explainability.py
页面：/models/explainability
API：/api/models/explainability/run
```

### 功能目标

解释单个学生为什么得到当前评分、等级或风险结果。

### 依赖策略

```text
如果安装 shap，使用 SHAP TreeExplainer。
如果未安装 shap，使用局部贡献近似：
局部贡献 = 指标标准化偏离 × 模型/规则权重。
```

### 输出

```text
个体正向贡献因素
个体负向贡献因素
主要原因摘要
改进建议
```

### 图表

```text
1. 个体贡献瀑布图
2. 正负贡献条形图
3. 与班级平均对比雷达图
4. 指标偏离热力图
5. 个体解释文本卡片
```

---

## 12.30 干预效果评估模型

### 文件与路由

```text
文件：models/intervention_effect.py
页面：/models/intervention_effect
API：/api/models/intervention_effect/run
```

### 功能目标

评价个性化学习路径、补弱训练或教学干预是否有效。

### 输入

```text
interventions
exam_records
knowledge_scores
```

### 算法

```text
前后测差值
提升率
Cohen's d 效果量
配对差异检验，可选 scipy
按干预类型分组统计
```

### 输出

```text
干预前均分
干预后均分
平均提升
效果量
有效学生比例
最佳干预类型
```

### 图表

```text
1. 干预前后折线图
2. 提升幅度柱状图
3. 效果量分布图
4. 不同干预类型对比图
5. 学生干预效果明细表
```

---

# 13. 学科专项评价模型

学科专项模型统一放在 `models/subject_models.py`，可以使用同一基类：

```python
class SubjectEvaluationModel(BaseEvaluationModel):
    subject_code: str
    subject_name: str
    dimensions: list
    def run(...): ...
```

每个学科必须有独立页面：

```text
/models/subject_chinese
/models/subject_math
/models/subject_english
/models/subject_physics
/models/subject_biology
/models/subject_history
```

页面共同结构：

```text
学科核心素养说明
学科能力雷达图
学科知识点热力图
成绩趋势图
薄弱模块诊断
分层学习路径建议
推荐资源
```

---

## 13.1 语文学科专项评价模型

### 维度

```text
文言文阅读
现代文阅读
写作表达
语言基础
课外阅读
课堂互动
```

### 输出

```text
语文综合评分
阅读能力等级
写作表达等级
文言薄弱点
作文提升建议
```

### 图表

```text
1. 语文能力雷达图
2. 作文分数趋势折线图
3. 文言文/现代文/写作模块热力图
4. 阅读与写作相关散点图
5. 语文分层路径推荐图
```

### 建议规则

```text
文言文低于60：推荐重点实词、虚词、特殊句式训练。
写作低于70：推荐议论文结构、素材积累、片段训练。
阅读低于70：推荐现代文答题模板和错题复盘。
```

---

## 13.2 数学学科专项评价模型

### 维度

```text
函数
三角函数
数列
数学运算
逻辑推理
数学建模
压轴题能力
自主刷题行为
```

### 输出

```text
数学综合评分
函数模块掌握度
数列模块掌握度
建模能力
解题稳定性
```

### 图表

```text
1. 数学能力雷达图
2. 函数/数列/三角模块掌握热力图
3. 基础题-中档题-压轴题得分率堆叠图
4. 解题正确率趋势折线图
5. 数学薄弱点到专题训练桑基图
```

### 建议规则

```text
函数低于70：推荐函数单调性、奇偶性、图像变换专题。
数列低于70：推荐等差等比基础与递推数列专项。
建模低于70：推荐生活情境建模小项目。
```

---

## 13.3 英语学科专项评价模型

### 维度

```text
词汇
语法
听力
阅读
写作
口语/表达
在线听力练习
课外阅读
```

### 输出

```text
英语综合评分
听说读写分项等级
词汇掌握率
作文提升点
听力薄弱原因
```

### 图表

```text
1. 听说读写雷达图
2. 词汇掌握率趋势图
3. 听力/阅读/写作得分率柱状图
4. 作文分数变化折线图
5. 英语学习路径推荐卡片
```

### 建议规则

```text
词汇低于60：推荐基础词汇+词根词缀。
听力低于70：推荐每日精听+跟读。
写作低于70：推荐句型模板+片段练习。
阅读低于70：推荐真题阅读和长难句拆解。
```

---

## 13.4 物理学科专项评价模型

### 维度

```text
运动学
力学
相互作用
实验操作
物理建模
计算题能力
科学探究行为
```

### 输出

```text
物理综合评分
实验能力等级
力学掌握度
计算题稳定性
物理模型库建议
```

### 图表

```text
1. 物理能力雷达图
2. 运动学/力学/实验模块热力图
3. 实验操作得分趋势图
4. 计算题正确率折线图
5. 物理模型类型薄弱图
```

### 建议规则

```text
实验低于70：推荐基础实验操作视频和实验报告训练。
力学低于70：推荐受力分析、牛顿定律专题。
计算题低于70：推荐过程分析和单位规范训练。
```

---

## 13.5 生物学科专项评价模型

### 维度

```text
细胞生命历程
遗传的细胞基础
稳态与调节
实验探究
生命观念
科学思维
课外阅读
```

### 输出

```text
生物综合评分
核心模块掌握度
实验探究能力
科学思维等级
```

### 图表

```text
1. 生物能力雷达图
2. 细胞/遗传/稳态模块热力图
3. 实验探究题得分趋势图
4. 选择题与综合题得分率对比图
5. 生物知识网络图
```

### 建议规则

```text
细胞模块低于70：推荐细胞结构、代谢与生命历程专题。
遗传低于70：推荐遗传规律题型训练。
实验低于70：推荐实验设计与变量控制专项。
```

---

## 13.6 历史学科专项评价模型

### 维度

```text
历史时序
核心概念
材料分析
历史解释
史料实证
家国情怀
课堂讨论
```

### 输出

```text
历史综合评分
时序掌握度
材料分析能力
历史解释能力
专题探究建议
```

### 图表

```text
1. 历史能力雷达图
2. 时序知识掌握时间轴
3. 材料分析题得分趋势图
4. 核心概念薄弱热力图
5. 历史知识图谱/事件关联图
```

### 建议规则

```text
时序低于70：推荐历史年表和时间轴训练。
材料分析低于70：推荐史料分层解读三步法。
历史解释低于70：推荐原因类、影响类题型专项。
```

---

# 14. 图表服务设计

新增 `services/chart_service.py`，不要在每个模型里硬写过多 ECharts 结构。建议提供工具函数：

```python
def bar_chart(title, x, y, name="") -> dict: ...
def line_chart(title, x, series) -> dict: ...
def radar_chart(title, indicators, values) -> dict: ...
def scatter_chart(title, points, x_name, y_name) -> dict: ...
def heatmap_chart(title, x_labels, y_labels, matrix) -> dict: ...
def boxplot_chart(title, categories, values) -> dict: ...
def sankey_chart(title, nodes, links) -> dict: ...
def graph_chart(title, nodes, links) -> dict: ...
def gauge_chart(title, value, min_value=0, max_value=100) -> dict: ...
def waterfall_chart(title, items) -> dict: ...
```

前端 `static/model_pages.js` 负责遍历 charts：

```javascript
function renderModelCharts(charts) {
  charts.forEach(chart => {
    const el = document.getElementById(chart.chart_id);
    const instance = echarts.init(el);
    instance.setOption(chart.option);
  });
}
```

---

# 15. 导出功能

新增 `services/export_service.py`。

每个模型页面必须支持：

```text
导出学生明细 CSV
导出模型结果 Excel
导出模型 JSON
导出个体诊断报告 HTML
```

Excel 至少包含：

```text
Sheet1：模型概览
Sheet2：学生明细
Sheet3：图表数据
Sheet4：个体建议
Sheet5：数据质量日志
```

---

# 16. 数据质量页面

新增 `/api/data/quality` 和页面中的数据质量卡。

指标：

```text
样本数
班级数
学科数
指标字段数
缺失值比例
异常值数量
可用于题目级模型的数据量
可用于资源推荐的数据量
可用于干预评估的数据量
当前启用完整模型数量
当前降级模型数量
```

图表：

```text
数据完整度雷达图
字段缺失率柱状图
模型可用状态矩阵
数据来源分布图
```

---

# 17. 模型比较页面

新增：

```text
/models/compare
/api/models/compare
```

功能：

```text
选择多个模型
比较同一学生在不同模型下的评分/等级/风险
比较班级整体分布
比较模型输出一致性
显示模型差异解释
```

图表：

```text
模型评分对比雷达图
模型等级一致性热力图
模型排名相关散点图
学生多模型诊断表
```

---

# 18. 单个学生综合画像页

新增：

```text
/students/<student_id>
```

展示该学生在所有模型下的综合结果：

```text
基础信息
AHP综合分
RSM属性模式
薄弱知识点
趋势预测
风险预警
聚类画像
学习路径推荐
可解释性原因
历史干预效果
```

图表：

```text
学生多模型雷达图
学业趋势折线图
薄弱知识点热力图
风险因素瀑布图
推荐路径图
```

---

# 19. 演示数据生成要求

扩展 `utils/sample_data.py`，生成以下演示文件：

```text
demo_students.csv
demo_exam_records.csv
demo_knowledge_scores.csv
demo_item_responses.csv
demo_q_matrix.csv
demo_learning_behavior.csv
demo_resource_library.csv
demo_resource_interactions.csv
demo_interventions.csv
```

演示数据要求：

```text
学生数：至少 120 人
班级数：至少 4 个
学科：语文、数学、英语、物理、生物、历史
时间跨度：至少 6 个月
考试次数：至少 5 次
知识点：每个学科至少 8 个
题目：每个学科至少 30 道模拟题
资源：每个学科至少 20 个学习资源
干预记录：至少 40 条
```

数据要有真实教育逻辑：

```text
高学习行为学生通常成绩更稳定，但允许少量反例。
知识点掌握度高的学生综合题正确率通常较高。
成绩波动大的学生风险更高。
干预后多数学生有所提升，但不是所有学生都提升。
```

---

# 20. 配置文件要求

## 20.1 `config/thresholds.json`

```json
{
  "levels": [
    {"name": "优秀", "min": 85, "max": 100},
    {"name": "良好", "min": 70, "max": 84.99},
    {"name": "中等", "min": 55, "max": 69.99},
    {"name": "待提高", "min": 40, "max": 54.99},
    {"name": "需帮扶", "min": 0, "max": 39.99}
  ],
  "risk": {
    "red": 40,
    "orange": 55,
    "yellow": 70
  },
  "weak_knowledge": {
    "severe": 40,
    "help": 55,
    "weak": 70,
    "mastered": 85
  }
}
```

## 20.2 `config/subject_indicators.json`

必须定义六个学科的核心模块、能力维度、推荐资源关键词。

## 20.3 `config/recommendation_rules.json`

定义规则推荐库，包括：

```text
通用等级规则
学科专项规则
薄弱知识点规则
学习行为规则
风险预警规则
```

---

# 21. 测试要求

新增 `tests/`。可以用 pytest，也可以先用简单脚本，但建议 pytest。

## 21.1 路由测试

`tests/test_routes.py`：

```text
/ 能打开
/models 能打开
所有 /models/<model_id> 能打开
所有 /api/models/<model_id>/run 返回 JSON
```

## 21.2 模型协议测试

`tests/test_model_protocol.py`：

```text
每个模型返回 ModelResult
必须包含 summary_cards、charts、student_table、data_quality
charts 数量普通模型 >= 3，重点模型 >= 5
student_table 不为空
```

## 21.3 核心模型测试

`tests/test_core_models.py`：

```text
AHP 手动计算一致
熵权法权重和为 1
TOPSIS 接近度在 0-1
RSM Theta 在 0-1，Zeta >= 0
风险预警颜色合法
```

## 21.4 导出测试

`tests/test_exports.py`：

```text
CSV 可生成
Excel 可生成且包含多个 Sheet
JSON 可生成
```

---

# 22. 开发顺序建议

## 第一阶段：框架与模型注册

```text
1. 新增 models/base.py
2. 新增 models/registry.py
3. 新增 config/models_catalog.json
4. 新增 model_center.html 和 model_detail.html
5. 改造 app.py，支持统一模型路由
6. 确保现有 RSM 页面不受影响
```

## 第二阶段：综合评价与诊断模型

优先实现：

```text
AHP
weighted_index
entropy_weight
TOPSIS
grey_relation
RSM扩展
weak_knowledge
risk_warning
```

## 第三阶段：预测与机器学习模型

```text
trend_regression
logistic_risk
random_forest_grade
gbdt_potential
boosting_advanced
svm_classifier
time_series
```

## 第四阶段：画像、知识追踪与推荐

```text
kmeans_profile
hierarchical_cluster
latent_profile
anomaly_detection
BKT
DKT-Lite
rule_path_recommendation
collaborative_filtering
knowledge_graph
```

## 第五阶段：解释、干预和学科专项

```text
correlation_analysis
feature_importance
explainability
intervention_effect
subject_chinese
subject_math
subject_english
subject_physics
subject_biology
subject_history
```

## 第六阶段：模型比较、学生画像页和导出

```text
/models/compare
/students/<student_id>
Excel/CSV/JSON导出
测试与README更新
```

---

# 23. 每轮交给 Codex 的开发提示词

## 23.1 第一轮：搭建多模型框架

```text
请根据 CODEX_MULTI_MODEL_DEVELOPMENT.md 第一阶段要求，搭建多模型框架：
1. 新增 BaseEvaluationModel 和 ModelResult。
2. 新增模型注册表和 models_catalog.json。
3. 新增 /models 模型中心页面和 /models/<model_id> 通用详情页面。
4. 新增 /api/models/catalog 和 /api/models/<model_id>/run。
5. 先接入现有 RSM，并增加一个 AHP 模型作为示范。
6. 不破坏现有首页、上传、结果页功能。
7. 完成后运行本地启动测试。
```

## 23.2 第二轮：实现综合评价模型

```text
请实现综合评分类模型：AHP、weighted_index、entropy_weight、TOPSIS、grey_relation。
每个模型必须：
1. 有独立 Python 模块。
2. 注册到 models_catalog.json。
3. 子页面可访问。
4. API 返回统一 ModelResult。
5. 至少 5 个图表。
6. 有学生明细表和个体诊断。
7. 有 CSV/Excel/JSON 导出。
```

## 23.3 第三轮：实现诊断与预警模型

```text
请实现诊断与预警模型：RSM扩展、cognitive_diagnosis、IRT、weak_knowledge、risk_warning、anomaly_detection。
要求缺少题目级数据时使用降级方案，不允许页面报错。
图表包括热力图、散点图、雷达图、箱线图和重点学生表。
```

## 23.4 第四轮：实现预测模型

```text
请实现预测类模型：trend_regression、logistic_risk、random_forest_grade、gbdt_potential、boosting_advanced、svm_classifier、time_series。
要求每个模型能使用演示数据运行，若无真实标签则生成清晰标注的规则标签或降级标签。
输出模型性能、预测结果、特征重要性和教育解释。
```

## 23.5 第五轮：实现画像、追踪和推荐模型

```text
请实现画像、知识追踪和推荐模型：kmeans_profile、hierarchical_cluster、latent_profile、bkt、dkt_lite、rule_path_recommendation、collaborative_filtering、knowledge_graph。
要求生成丰富图表：聚类散点、画像雷达、知识追踪曲线、桑基图、知识图谱关系图、资源推荐排行。
```

## 23.6 第六轮：实现解释、干预与学科专项模型

```text
请实现解释、干预和学科专项模型：correlation_analysis、feature_importance、explainability、intervention_effect、subject_chinese、subject_math、subject_english、subject_physics、subject_biology、subject_history。
要求每个学科专项页面都有学科能力雷达图、知识点热力图、趋势图、薄弱模块和分层学习路径建议。
```

## 23.7 第七轮：完善测试、导出和README

```text
请补充测试、导出和说明文档：
1. 为所有模型增加基本测试。
2. 确保所有模型页面和 API 都能运行。
3. 完善 CSV、Excel、JSON 导出。
4. 新增模型比较页和单个学生综合画像页。
5. 更新 README，写清楚本地运行方式、数据模板、模型列表和开发说明。
```

---

# 24. 页面内容细节要求

每个模型详情页顶部显示：

```text
模型名称
模型类别
适用场景
数据要求
当前运行状态：完整 / 降级 / 演示
样本量
图表数量
导出按钮
```

模型说明区显示：

```text
模型思想
核心公式或流程
教育解释
适用限制
```

数据质量区显示：

```text
参与计算学生数
使用指标数
缺失值数量
填补方式
异常值处理数量
降级原因，若有
```

图表区显示：

```text
每个图表有标题、说明、图表和“如何解读”。
```

学生明细表支持：

```text
搜索
按班级筛选
按学科筛选
按等级筛选
按风险等级筛选
按分数排序
点击查看个体诊断
```

---

# 25. 评分等级与风险等级统一标准

```python
def academic_level(score):
    if score >= 85:
        return "优秀"
    if score >= 70:
        return "良好"
    if score >= 55:
        return "中等"
    if score >= 40:
        return "待提高"
    return "需帮扶"
```

风险等级：

```python
def risk_level(score, trend_slope=None, volatility=None, knowledge=None, behavior=None):
    # 红色、橙色、黄色、绿色
    ...
```

进步潜力：

```text
快速进步
稳步进步
波动观察
潜力待激发
学业预警
```

---

# 26. 报告文本生成规则

每个模型要生成可读文本，不只是表格。

示例：

```text
该生综合评分为 76.4，处于良好等级。三大核心维度中，知识点掌握度为 72.1，低于班级均值 4.3 分，主要薄弱点集中在函数性质和综合迁移题。学习行为活跃度为 81.5，说明该生具备较好的自主学习基础。建议进入“能力提升路径”，重点进行函数专题训练和每周错题复盘。
```

模型解释要包含：

```text
1. 结果是什么
2. 为什么得到这个结果
3. 主要优势是什么
4. 主要短板是什么
5. 下一步怎么做
```

---

# 27. 代码质量要求

1. 每个模型模块不超过合理长度，公共逻辑放到 `services`。
2. 所有模型固定 `random_state=42`，保证演示结果可复现。
3. 函数要有类型提示和必要注释。
4. API 返回错误时要有友好信息，不返回裸异常。
5. 不要在模板中写复杂业务逻辑。
6. 图表数据由后端生成，前端只负责渲染。
7. 上传文件要校验扩展名和字段。
8. 导出文件写入 `output/`，文件名包含模型 ID 和时间戳。

---

# 28. 最终验收清单

完成后必须满足：

```text
[ ] Windows 双击 run_windows.bat 可启动。
[ ] macOS/Linux 执行 run_linux_mac.sh 可启动。
[ ] 首页能打开。
[ ] /models 模型中心能打开。
[ ] 36 个模型子页面都能打开。
[ ] 每个模型 API 返回 JSON。
[ ] 每个模型至少 3 个图表，重点模型至少 5 个图表。
[ ] AHP、RSM、风险预警、薄弱知识点、随机森林、学习路径推荐六个重点模型图表和解释最完整。
[ ] 演示数据无需上传即可跑通全部模型。
[ ] 上传宽表 CSV/Excel 后能重新计算。
[ ] 缺少题目级数据时，认知诊断、IRT、BKT、DKT-Lite 显示降级说明，不报错。
[ ] CSV/Excel/JSON 导出可用。
[ ] 单个学生画像页可用。
[ ] 模型比较页可用。
[ ] README 已更新。
[ ] tests 基本通过。
```

---

# 29. 重点模型展示优先级

课题展示时建议重点展示这些页面：

```text
1. /models/ahp
2. /models/rsm
3. /models/weak_knowledge
4. /models/trend_regression
5. /models/risk_warning
6. /models/random_forest_grade
7. /models/gbdt_potential
8. /models/kmeans_profile
9. /models/rule_path_recommendation
10. /models/explainability
11. /models/intervention_effect
12. /models/subject_math 或 /models/subject_history
```

展示逻辑：

```text
AHP 给综合评价结果。
RSM 解释学生知识属性结构。
薄弱知识点模型说明具体短板。
趋势模型说明未来发展方向。
预警模型找出重点关注学生。
机器学习模型增强预测能力。
聚类模型形成学生画像。
推荐模型输出个性化学习路径。
解释模型说明为什么这样评价。
干预模型证明学习路径是否有效。
学科专项模型体现学科融合。
```

---

# 30. README 更新要点

开发完成后，README 至少包含：

```text
项目简介
本地运行方式
模型列表
数据模板说明
上传数据字段说明
模型页面说明
导出报告说明
常见问题
开发说明
```

模型列表要用表格展示 36 个模型。

---

# 31. 风险与降级策略

| 风险 | 处理策略 |
|---|---|
| 没有题目级数据 | 认知诊断、IRT、BKT、DKT-Lite 使用指标级近似或演示数据 |
| 没有真实标签 | 机器学习分类/预测模型使用规则标签，并明确标记 |
| 样本量过小 | 减少模型复杂度，使用规则模型或简单模型 |
| 缺少资源交互 | 协同过滤降级为内容匹配推荐 |
| 没有 SHAP | 使用局部贡献解释 |
| 没有 XGBoost/LightGBM | 使用 sklearn GBDT |
| 没有 statsmodels | 时间序列使用移动平均与指数平滑 |
| 图表过多加载慢 | 模型页按需加载，先显示核心图表 |

---

# 32. 结论

本开发任务的最终目标不是简单堆算法，而是形成完整的学业发展评价模型体系：

```text
综合评价模型：回答“学生当前水平如何”
诊断模型：回答“学生弱在哪里”
预测模型：回答“未来可能怎样发展”
画像模型：回答“学生属于哪一类”
预警模型：回答“谁需要重点关注”
知识追踪模型：回答“掌握过程如何变化”
推荐模型：回答“下一步应该学什么”
解释模型：回答“为什么这样评价”
干预模型：回答“干预有没有效果”
学科专项模型：回答“不同学科如何精准分析”
```

所有模型都要服务同一个教育目标：

```text
以数据驱动学生学业发展评价，以模型解释学生发展状态，以学习路径促进学生个性化成长。
```
