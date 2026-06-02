# 学生学业发展规则空间分析系统（本地原型）

这是一个可本地运行的前后端网页分析系统，核心功能围绕“学生学业发展评价”展开，不包含学生端、教师端、学校端三类门户，也不包含复杂权限系统。

## 1. 主要功能

- 上传 Excel/CSV 数据。
- 自动识别学生基本信息与 35 项三级指标字段。
- 异常值处理、缺失值按“班级-学科-指标”中位数填补。
- 生成 0-100 标准化评分和 Z-score 审计列。
- 按 AHP 权重聚合为三类一级维度：成绩波动趋势、知识点掌握度、学习行为活跃度。
- 采用规则空间模型输出：Theta、Zeta、最近理想状态、学业等级、发展潜力、薄弱属性和建议。
- 增加辅助评价模型：成长动能模型、学习稳定性模型、知行耦合模型、风险预警模型、学业发展画像分群。
- 本地网页可视化：等级分布、多模型指数、风险结构、画像分布、得分区间、一级维度雷达、学科热力图、知行耦合散点图、薄弱属性图、规则空间散点图。
- 增加学科化子页面：语文、数学、外语、物理、化学、生物、历史、地理、政治，每个页面独立展示学科核心特征、趋势推导、薄弱模块和重点学生。
- 新增多模型评价分析平台：模型中心、统一模型结果协议、统一模型详情页、统一 API、模型比较、学生综合画像和模型级 CSV/Excel/JSON 导出。
- 导出 CSV、标准化数据、Excel 报告、JSON 明细。

## 2. 快速运行

### Windows

双击：

```text
run_windows.bat
```

启动后浏览器打开：

```text
http://127.0.0.1:5000
```

### macOS / Linux

```bash
bash run_linux_mac.sh
```

启动后浏览器打开：

```text
http://127.0.0.1:5000
```

## 3. 手动运行

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用 .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 4. 测试与检查

修改代码后建议执行：

```bash
python -m compileall .
pytest -q
```

## 5. GitHub Pages 静态部署

项目已内置 GitHub Pages 静态演示站导出脚本和 Actions 工作流：

- 导出脚本：`utils/export_static_site.py`
- 工作流：仓库根目录 `.github/workflows/github-pages.yml`

本地生成静态站：

```bash
python utils/export_static_site.py --output site
```

生成后 `site/index.html` 可作为静态演示首页。推送到 GitHub 后，工作流会自动生成并发布 GitHub Pages。发布完成后页面通常位于：

```text
https://<你的GitHub用户名>.github.io/<仓库名>/
```

注意：GitHub Pages 只能托管静态文件。该静态版可以展示演示数据、总览图表、模型中心、各学科模型页和模型详情页，但不能在线上传新数据或执行 Flask 后端分析。

## 6. 完整 Flask 服务部署

如果需要公网访问时仍保留“上传数据、运行模型、导出报告”等动态功能，需要把 GitHub 仓库连接到支持 Python Web 服务的平台。项目已提供 Render Blueprint 配置：

```text
render.yaml
```

在 Render 中选择该 GitHub 仓库并使用 Blueprint 部署后，会按以下命令运行完整服务：

```bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT
```

## 7. 数据格式

系统支持 CSV、XLSX、XLS。建议先在首页下载“规则空间模型数据模板.csv”。

必须或建议保留的基本字段：

- 学号
- 姓名
- 班级
- 学科

三级指标可不全部具备。系统会按实际识别到的指标进行加权重算，并在日志中显示可用指标数。

## 8. 规则空间模型说明

系统将 9 个二级指标视为属性空间：

1. 基础成绩水平
2. 成绩波动幅度
3. 进步退步幅度
4. 知识点达标率
5. 知识点应用能力
6. 课堂互动行为
7. 作业提交行为
8. 在线学习行为
9. 自主学习行为

每个属性按阈值转化为“掌握/未掌握”。系统根据教育逻辑设置前置约束，例如“知识点应用能力”通常依赖“知识点达标率”；再生成所有合法理想状态，并计算学生当前掌握模式与最近理想状态之间的距离。

- Theta：加权属性掌握度，越高越好。
- Zeta：与最近理想状态的偏离度，越低越稳定。
- RSM调整分：综合评分、Theta、Zeta 的加权结果。

辅助模型用于解释和展示，不替代 RSM 主模型：

- 成长动能指数：结合进步幅度、学习行为、知识掌握、Theta 和 Zeta。
- 学习稳定性指数：由成绩波动幅度属性反向刻画，越高表示波动越小。
- 知行耦合指数：衡量知识掌握度和学习行为活跃度是否同步发展。
- 预警风险指数：综合低分、偏离度、行为不足、薄弱属性和波动因素。
- 学业发展画像：把学生分为高掌握-高活跃、低掌握-高投入、波动风险型等可解释画像。

## 9. 学科化模型子页面

系统在总览结果页之外提供 9 个学科模型页面，顺序为语文、数学、外语、物理、化学、生物、历史、地理、政治：

- `/model/chinese`：语文学业发展评价模型。
- `/model/math`：数学学业发展评价模型。
- `/model/foreign`：外语学业发展评价模型。
- `/model/physics`：物理学业发展评价模型。
- `/model/chemistry`：化学学业发展评价模型。
- `/model/bio`：生物学业发展评价模型。
- `/model/history`：历史学业发展评价模型。
- `/model/geography`：地理学业发展评价模型。
- `/model/politics`：政治学业发展评价模型。

兼容说明：`/model/english` 会继续显示外语模型，便于旧链接访问。

学科配置维护在 `config/subjects/subject_models.json`。每个学科配置包含课程标准核心素养、优化二级指标、权重维度、模块映射和建议模板。页面统一复用 `templates/subject_model.html` 和 `static/charts.js`，避免为每个学科复制大量模板代码。

学科页面展示内容包括：

- 核心素养雷达图、优化二级指标雷达图、权重维度柱状图。
- 知识点掌握热力图、学业趋势图、薄弱模块图。
- RSM、AHP、趋势预测、画像聚类、知识追踪、学习路径推荐、特征解释等模型族运行概览。
- 重点学生、薄弱模块和个性化干预建议。

## 10. 多模型分析平台

新增模型中心：

- `/models`：模型中心，展示全部模型入口。
- `/models/<model_id>`：统一模型详情页，例如 `/models/ahp`、`/models/rsm`、`/models/risk_warning`、`/models/subject_math`。
- `/models/compare`：重点模型对比页。
- `/students/<student_id>`：单个学生跨模型综合画像页。

统一 API：

- `/api/models/catalog`：模型注册表。
- `/api/models/<model_id>/run`：运行并返回统一 `ModelResult`。
- `/api/models/<model_id>/student/<student_id>`：单个学生在指定模型下的诊断。
- `/api/models/<model_id>/charts`：指定模型图表数据。
- `/api/models/<model_id>/export/csv`、`/excel`、`/json`：模型级导出。
- `/api/models/compare`：重点模型比较。
- `/api/data/quality`：当前数据质量概览。

当前注册表维护在 `config/models_catalog.json`，覆盖综合评价、诊断、预测、画像、预警、知识追踪、路径推荐、解释分析、干预效果和 9 个学科专项模型。缺少题目级数据、Q 矩阵、资源交互或干预记录时，相关模型以“降级运行”方式复用指标级数据和 RSM 结果，不让页面空白或报错。

## 11. 目录结构

```text
rsm_academic_eval_app/
├─ app.py
├─ config/indicators.json
├─ config/models_catalog.json
├─ config/subjects/subject_models.json
├─ models/base.py
├─ models/registry.py
├─ models/rsm.py
├─ models/platform_models.py
├─ models/subject_models.py
├─ services/
├─ utils/sample_data.py
├─ templates/
├─ static/
├─ data/
├─ output/
├─ requirements.txt
├─ run_windows.bat
└─ run_linux_mac.sh
```

## 12. 后续可扩展方向

- 增加学科专属 Q 矩阵，把语文、数学、外语、物理、化学、生物、历史、地理、政治等学科知识点作为更细粒度属性。
- 把当前的二级属性阈值从固定值改为“班级/学科分位数阈值”。
- 增加本地 SQLite 存储历史分析记录。
- 增加教师可配置权重与阈值页面。
- 接入真实题目级数据、资源交互和干预记录后，把降级模型升级为完整算法版本。
