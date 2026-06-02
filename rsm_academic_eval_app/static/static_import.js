(function () {
  const root = document.getElementById('staticAnalyzer');
  if (!root) return;

  const config = window.STATIC_IMPORT_CONFIG || {};
  const metaColumns = ['学号', '姓名', '班级', '学科'];
  const statusEl = document.getElementById('staticImportStatus');
  const fileInput = document.getElementById('staticCsvFile');
  const runBtn = document.getElementById('runStaticImport');
  const loadSampleBtn = document.getElementById('loadSampleCsv');
  const exportBtn = document.getElementById('exportStaticCsv');
  const searchInput = document.getElementById('staticTableSearch');
  let lastResults = [];
  let lastSummary = null;

  const indicators = flattenIndicators(config);
  const secondaryMap = buildSecondaryMap(config);
  const primaryMap = config.primary || {};
  const attributeNames = Object.keys(secondaryMap);
  const attributeWeights = buildAttributeWeights();
  const idealStates = generateIdealStates();

  runBtn.addEventListener('click', async () => {
    if (!fileInput.files || !fileInput.files.length) {
      setStatus('请先选择 CSV 文件，或点击“加载线上5000人样例”。', true);
      return;
    }
    const text = await fileInput.files[0].text();
    analyzeCsv(text, fileInput.files[0].name);
  });

  loadSampleBtn.addEventListener('click', async () => {
    try {
      setStatus('正在加载线上 5000 人样例数据...');
      const response = await fetch(sampleCsvUrl(), { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const text = await response.text();
      analyzeCsv(text, 'synthetic_5000_students.csv');
    } catch (error) {
      setStatus(`样例数据加载失败：${error.message}`, true);
    }
  });

  exportBtn.addEventListener('click', () => {
    if (!lastResults.length) return;
    downloadText('浏览器端规则空间分析结果.csv', toCsv(lastResults));
  });

  searchInput.addEventListener('input', () => renderTable(lastResults, searchInput.value));

  function sampleCsvUrl() {
    if (location.hostname.includes('github.io') || location.pathname.endsWith('.html')) {
      return 'downloads/synthetic_5000_students.csv';
    }
    return 'download/synthetic';
  }

  function analyzeCsv(text, sourceName) {
    try {
      const parsed = parseCsv(text);
      if (!parsed.rows.length) {
        setStatus('CSV 中没有可分析的数据行。', true);
        return;
      }
      const analysis = runBrowserRsm(parsed.headers, parsed.rows);
      lastResults = analysis.results;
      lastSummary = analysis.summary;
      renderAll(analysis);
      exportBtn.disabled = false;
      setStatus(`分析完成：${sourceName}，共 ${analysis.results.length} 名学生，识别 ${analysis.available.length} 个指标。`);
    } catch (error) {
      setStatus(`分析失败：${error.message}`, true);
    }
  }

  function runBrowserRsm(headers, rows) {
    const canonicalHeaders = headers.map(header => aliasMap()[normCol(header)] || String(header).trim());
    const prepared = rows.map((row, rowIndex) => {
      const item = {};
      canonicalHeaders.forEach((name, i) => {
        if (item[name] === undefined || item[name] === '') item[name] = row[i];
      });
      item['学号'] = item['学号'] || `S${String(rowIndex + 1).padStart(4, '0')}`;
      item['姓名'] = item['姓名'] || `学生${rowIndex + 1}`;
      item['班级'] = item['班级'] || '未分班';
      item['学科'] = item['学科'] || '综合';
      return item;
    });

    const available = Object.keys(indicators).filter(name => canonicalHeaders.includes(name));
    if (!available.length) throw new Error('未识别到任何评价指标字段，请使用模板字段或字段别名。');

    const cleaned = {};
    available.forEach(name => {
      const conf = indicators[name];
      const values = prepared.map(row => cleanNumber(row[name], conf));
      const median = percentile(values.filter(v => v !== null), 50) || 0;
      cleaned[name] = values.map(value => value === null ? median : value);
    });

    const normalized = {};
    available.forEach(name => {
      normalized[name] = indicatorToScores(cleaned[name], indicators[name]);
    });

    const secondaryScores = {};
    const primaryScores = {};
    Object.entries(secondaryMap).forEach(([secondary, conf]) => {
      secondaryScores[secondary] = weightedIndicatorAverage(conf.indicators, normalized, available);
    });
    Object.entries(primaryMap).forEach(([primary, conf]) => {
      const pieces = {};
      Object.entries(conf.secondary || {}).forEach(([secondary, secConf]) => {
        if (secondaryScores[secondary]) {
          pieces[secondary] = { weight: Number(secConf.weight || 0), values: secondaryScores[secondary] };
        }
      });
      primaryScores[primary] = weightedSeries(pieces);
    });

    const results = prepared.map((row, i) => {
      const overall = weightedPrimaryScore(i, primaryScores);
      const secValues = {};
      attributeNames.forEach(attr => { secValues[attr] = safeNumber(secondaryScores[attr] && secondaryScores[attr][i], 0); });
      const mastery = {};
      attributeNames.forEach(attr => { mastery[attr] = secValues[attr] >= Number(config.mastery_threshold || 65) ? 1 : 0; });
      const theta = attributeNames.reduce((sum, attr) => sum + attributeWeights[attr] * mastery[attr], 0) * 100;
      const nearest = nearestIdealState(mastery);
      const maxDistance = Math.sqrt(Object.values(attributeWeights).reduce((sum, value) => sum + value, 0)) || 1;
      const zeta = clamp(nearest.distance / maxDistance * 100, 0, 100);
      const adjusted = 0.8 * overall + 0.1 * theta + 0.1 * (100 - zeta);
      const level = levelFromScore(adjusted);
      const potential = potentialLabel(primaryScores, secondaryScores, i, zeta);
      const weak = weakAttributes(secValues);
      const advanced = advancedModels(primaryScores, secondaryScores, i, adjusted, theta, zeta, weak.length);

      const result = {
        '学号': String(row['学号']),
        '姓名': String(row['姓名']),
        '班级': String(row['班级']),
        '学科': String(row['学科']),
        '综合评分': round(overall),
        'RSM调整分': round(adjusted),
        '学业等级': level,
        '发展潜力': potential.label,
        '规则空间Theta': round(theta),
        '规则空间Zeta': round(zeta),
        '最近理想状态': nearest.state.label,
        '成长动能指数': advanced.growth,
        '学习稳定性指数': advanced.stability,
        '知行耦合指数': advanced.coupling,
        '预警风险指数': advanced.riskScore,
        '风险预警等级': advanced.riskLevel,
        '学业发展画像': advanced.profile,
        '干预优先级': advanced.priority,
        '薄弱属性': weak.length ? weak.slice(0, 3).map(item => item.name).join('、') : '暂无明显薄弱项',
        '建议摘要': recommendations(level, potential.label, weak).slice(0, 3).join('；')
      };
      Object.entries(primaryScores).forEach(([name, values]) => { result[name] = round(values[i]); });
      Object.entries(secValues).forEach(([name, value]) => { result[name] = round(value); });
      return result;
    });

    return { results, available, summary: buildSummary(results, available) };
  }

  function renderAll(analysis) {
    renderKpis(analysis.summary);
    renderCharts(analysis);
    renderTable(analysis.results, searchInput.value);
    document.getElementById('staticKpis').hidden = false;
    document.getElementById('staticCharts').hidden = false;
    document.getElementById('staticResultTableCard').hidden = false;
  }

  function renderKpis(summary) {
    const kpis = document.getElementById('staticKpis');
    kpis.innerHTML = [
      ['学生数', summary.studentCount, '人'],
      ['识别指标', summary.indicatorCount, '项'],
      ['RSM均分', summary.rsmMean, '分'],
      ['平均Zeta', summary.zetaMean, '分'],
      ['红橙预警', summary.focusCount, '人']
    ].map(([label, value, unit]) => (
      `<div class="metric-card metric-compact"><span class="metric-title">${label}</span><strong>${value}${unit}</strong><span class="metric-desc">浏览器端计算</span></div>`
    )).join('');
  }

  function renderCharts(analysis) {
    drawDonutChart('staticLevelChart', analysis.summary.levelCounts, '学业等级分布');
    drawRadarChart('staticPrimaryChart', analysis.summary.primaryMeans, '三类核心维度均分');
    drawHorizontalBar('staticWeakChart', analysis.summary.weakItems, '薄弱属性未掌握率');
    drawScatter('staticScatterChart', analysis.results.slice(0, 800), 'Theta-Zeta规则空间分布');
  }

  function renderTable(results, keyword) {
    const tbody = document.querySelector('#staticResultTable tbody');
    const key = String(keyword || '').trim().toLowerCase();
    const filtered = results.filter(row => {
      if (!key) return true;
      return ['学号', '姓名', '班级', '学科', '学业等级', '风险预警等级'].some(field => String(row[field] || '').toLowerCase().includes(key));
    }).slice(0, 300);
    tbody.innerHTML = filtered.map(row => `
      <tr>
        <td>${escapeHtml(row['学号'])}</td>
        <td>${escapeHtml(row['姓名'])}</td>
        <td>${escapeHtml(row['班级'])}</td>
        <td>${escapeHtml(row['学科'])}</td>
        <td>${row['综合评分']}</td>
        <td>${row['RSM调整分']}</td>
        <td>${escapeHtml(row['学业等级'])}</td>
        <td>${escapeHtml(row['发展潜力'])}</td>
        <td>${row['规则空间Theta']}</td>
        <td>${row['规则空间Zeta']}</td>
        <td>${escapeHtml(row['风险预警等级'])}</td>
        <td class="wrap-cell">${escapeHtml(row['薄弱属性'])}</td>
        <td class="wrap-cell">${escapeHtml(row['建议摘要'])}</td>
      </tr>
    `).join('');
  }

  function buildSummary(results, available) {
    const primaryMeans = {};
    Object.keys(primaryMap).forEach(name => { primaryMeans[name] = round(mean(results.map(row => Number(row[name] || 0)))); });
    const levelCounts = orderedCounts(results, '学业等级', ['优秀', '良好', '中等', '待提高', '需帮扶']);
    const weakItems = attributeNames.map(attr => {
      const values = results.map(row => Number(row[attr] || 0));
      return {
        attribute: attr,
        avg_score: round(mean(values)),
        unmastered_rate: round(values.filter(value => value < Number(config.mastery_threshold || 65)).length / Math.max(values.length, 1) * 100)
      };
    }).sort((a, b) => b.unmastered_rate - a.unmastered_rate).slice(0, 6);
    return {
      studentCount: results.length,
      indicatorCount: available.length,
      rsmMean: round(mean(results.map(row => Number(row['RSM调整分'] || 0)))),
      zetaMean: round(mean(results.map(row => Number(row['规则空间Zeta'] || 0)))),
      focusCount: results.filter(row => ['红色预警', '橙色关注'].includes(row['风险预警等级'])).length,
      primaryMeans,
      levelCounts,
      weakItems
    };
  }

  function flattenIndicators(conf) {
    const flat = {};
    Object.entries(conf.primary || {}).forEach(([primaryName, primaryConf]) => {
      Object.entries(primaryConf.secondary || {}).forEach(([secondaryName, secondaryConf]) => {
        Object.entries(secondaryConf.indicators || {}).forEach(([indicatorName, indicatorConf]) => {
          flat[indicatorName] = Object.assign({}, indicatorConf, { primary: primaryName, secondary: secondaryName });
        });
      });
    });
    return flat;
  }

  function buildSecondaryMap(conf) {
    const secondaries = {};
    Object.entries(conf.primary || {}).forEach(([primaryName, primaryConf]) => {
      Object.entries(primaryConf.secondary || {}).forEach(([secondaryName, secondaryConf]) => {
        secondaries[secondaryName] = {
          primary: primaryName,
          weight: Number(secondaryConf.weight || 0),
          indicators: secondaryConf.indicators || {}
        };
      });
    });
    return secondaries;
  }

  function aliasMap() {
    if (aliasMap.cache) return aliasMap.cache;
    const map = {};
    [...metaColumns, ...Object.keys(indicators)].forEach(name => { map[normCol(name)] = name; });
    Object.entries(config.aliases || {}).forEach(([canonical, aliases]) => {
      map[normCol(canonical)] = canonical;
      (aliases || []).forEach(alias => { map[normCol(alias)] = canonical; });
    });
    aliasMap.cache = map;
    return map;
  }

  function buildAttributeWeights() {
    const weights = {};
    Object.entries(secondaryMap).forEach(([secondary, secConf]) => {
      const primaryWeight = Number((primaryMap[secConf.primary] || {}).weight || 0);
      weights[secondary] = primaryWeight * Number(secConf.weight || 0);
    });
    const total = Object.values(weights).reduce((sum, value) => sum + value, 0) || 1;
    Object.keys(weights).forEach(key => { weights[key] = weights[key] / total; });
    return weights;
  }

  function generateIdealStates() {
    const states = [];
    const n = attributeNames.length;
    for (let bits = 0; bits < Math.pow(2, n); bits++) {
      const vector = {};
      attributeNames.forEach((attr, i) => { vector[attr] = (bits >> i) & 1; });
      if (!validState(vector)) continue;
      const score = attributeNames.reduce((sum, attr) => sum + attributeWeights[attr] * vector[attr], 0) * 100;
      states.push({ vector, score, label: levelFromScore(score) });
    }
    return states.sort((a, b) => a.score - b.score);
  }

  function validState(vector) {
    if (vector['知识点应用能力'] && !vector['知识点达标率']) return false;
    if (vector['进步退步幅度'] && !(vector['基础成绩水平'] || vector['知识点达标率'])) return false;
    if (vector['自主学习行为'] && !(vector['在线学习行为'] || vector['作业提交行为'])) return false;
    return true;
  }

  function nearestIdealState(mastery) {
    let best = idealStates[0];
    let bestDistance = Infinity;
    idealStates.forEach(state => {
      let dist = 0;
      attributeNames.forEach(attr => {
        const diff = mastery[attr] - Number(state.vector[attr] || 0);
        dist += attributeWeights[attr] * diff * diff;
      });
      dist = Math.sqrt(dist);
      if (dist < bestDistance) {
        bestDistance = dist;
        best = state;
      }
    });
    return { state: best, distance: bestDistance };
  }

  function weightedIndicatorAverage(indicatorConf, normalized, available) {
    const used = Object.entries(indicatorConf || {}).filter(([name]) => available.includes(name) && normalized[name]);
    const rowCount = used.length ? normalized[used[0][0]].length : 0;
    const values = Array(rowCount).fill(0);
    const weights = Array(rowCount).fill(0);
    used.forEach(([name, conf]) => {
      const weight = Number(conf.weight || 0);
      normalized[name].forEach((value, i) => {
        if (!Number.isNaN(value)) {
          values[i] += value * weight;
          weights[i] += weight;
        }
      });
    });
    return values.map((value, i) => weights[i] ? value / weights[i] : 0);
  }

  function weightedSeries(pieces) {
    const entries = Object.values(pieces);
    const rowCount = entries.length ? entries[0].values.length : 0;
    return Array.from({ length: rowCount }, (_, i) => {
      let numerator = 0;
      let denominator = 0;
      entries.forEach(piece => {
        const value = Number(piece.values[i]);
        const weight = Number(piece.weight || 0);
        if (!Number.isNaN(value)) {
          numerator += value * weight;
          denominator += weight;
        }
      });
      return denominator ? numerator / denominator : 0;
    });
  }

  function weightedPrimaryScore(index, primaryScores) {
    let numerator = 0;
    let denominator = 0;
    Object.entries(primaryMap).forEach(([primary, conf]) => {
      const value = Number((primaryScores[primary] || [])[index] || 0);
      const weight = Number(conf.weight || 0);
      numerator += value * weight;
      denominator += weight;
    });
    return denominator ? numerator / denominator : 0;
  }

  function indicatorToScores(values, conf) {
    const direction = conf.direction || 'higher_better';
    let scores;
    if (conf.type === 'score') {
      const range = conf.range || [0, 100];
      const lo = Number(range[0]);
      const hi = Number(range[1]);
      scores = values.map(value => hi !== lo ? (value - lo) / (hi - lo) * 100 : 0);
    } else if (conf.type === 'trend') {
      scores = values.map(value => (value + 100) / 200 * 100);
    } else {
      scores = robustMinmax(values);
    }
    if (direction === 'lower_better') scores = scores.map(value => 100 - value);
    return scores.map(value => clamp(value, 0, 100));
  }

  function robustMinmax(values) {
    const valid = values.filter(value => value !== null && !Number.isNaN(value)).sort((a, b) => a - b);
    const lo = percentile(valid, 1);
    const hi = percentile(valid, 99);
    if (hi <= lo) return values.map(() => 50);
    return values.map(value => (clamp(value, lo, hi) - lo) / (hi - lo) * 100);
  }

  function cleanNumber(value, conf) {
    const num = Number(String(value ?? '').trim());
    if (Number.isNaN(num)) return null;
    if (conf.type === 'score' && (num < 0 || num > 100)) return null;
    if (conf.type === 'trend' && (num < -100 || num > 100)) return null;
    if (conf.type !== 'score' && conf.type !== 'trend' && num < 0) return null;
    return num;
  }

  function potentialLabel(primaryScores, secondaryScores, index, zeta) {
    const progress = safeNumber((secondaryScores['进步退步幅度'] || [])[index], 50);
    const behavior = safeNumber((primaryScores['学习行为活跃度'] || [])[index], 50);
    const knowledge = safeNumber((primaryScores['知识点掌握度'] || [])[index], 50);
    const base = safeNumber((primaryScores['成绩波动趋势'] || [])[index], 50);
    const score = 0.35 * progress + 0.3 * behavior + 0.2 * knowledge + 0.15 * (100 - zeta);
    let label = score >= 78 && progress >= 60 ? '快速进步' : score >= 63 ? '稳步进步' : score >= 48 ? '波动观察' : '学业预警';
    if (base < 45 && behavior >= 65) label = '潜力待激发';
    return { score, label };
  }

  function weakAttributes(secValues) {
    const threshold = Number(config.mastery_threshold || 65);
    return Object.entries(secValues)
      .filter(([, value]) => value < threshold)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => a.value - b.value);
  }

  function advancedModels(primaryScores, secondaryScores, index, adjustedScore, theta, zeta, weakCount) {
    const knowledge = safeNumber((primaryScores['知识点掌握度'] || [])[index], 50);
    const behavior = safeNumber((primaryScores['学习行为活跃度'] || [])[index], 50);
    const progress = safeNumber((secondaryScores['进步退步幅度'] || [])[index], 50);
    const stability = safeNumber((secondaryScores['成绩波动幅度'] || [])[index], 50);
    const weakRate = weakCount / Math.max(attributeNames.length, 1) * 100;
    const growth = clamp(0.3 * progress + 0.25 * behavior + 0.2 * knowledge + 0.15 * theta + 0.1 * (100 - zeta), 0, 100);
    const coupling = clamp(0.6 * Math.min(knowledge, behavior) + 0.4 * (100 - Math.abs(knowledge - behavior)), 0, 100);
    const riskScore = clamp(0.35 * (100 - adjustedScore) + 0.2 * zeta + 0.2 * (100 - behavior) + 0.15 * weakRate + 0.1 * (100 - stability), 0, 100);
    const riskLevel = riskScore >= 72 ? '红色预警' : riskScore >= 55 ? '橙色关注' : riskScore >= 38 ? '黄色观察' : '正常';
    const priority = riskScore >= 72 ? 'P1-立即帮扶' : riskScore >= 55 ? 'P2-重点跟进' : riskScore >= 38 ? 'P3-持续观察' : 'P4-常规支持';
    let profile = '均衡发展型';
    if (knowledge >= 75 && behavior >= 75 && stability >= 65) profile = '高掌握-高活跃';
    else if (knowledge >= 70 && behavior < 60) profile = '高掌握-低活跃';
    else if (knowledge < 60 && behavior >= 70) profile = '低掌握-高投入';
    else if (progress >= 62 && stability >= 55) profile = '进步驱动型';
    else if (stability < 45) profile = '波动风险型';
    else if (knowledge < 55 && behavior < 55) profile = '基础薄弱型';
    return { growth: round(growth), stability: round(stability), coupling: round(coupling), riskScore: round(riskScore), riskLevel, profile, priority };
  }

  function recommendations(level, potentialLabelText, weak) {
    const levelMap = {
      '优秀': '保持高阶拓展：增加跨章节综合题、探究任务或竞赛基础训练',
      '良好': '突出能力提升：稳定基础题，同时突破中档题和迁移应用题',
      '中等': '先做基础巩固：围绕核心知识点建立清单化复习与错题复盘机制',
      '待提高': '实施重点补弱：每天安排短时高频基础训练，优先修复低分知识点',
      '需帮扶': '启动帮扶路径：降低任务难度，采用一对一讲解、模板化练习和正向激励'
    };
    const attrMap = {
      '基础成绩水平': '补齐基础成绩：梳理最近考试错题，按知识点重做基础题和典型例题',
      '成绩波动幅度': '降低成绩波动：固定周测复盘流程，记录失分类型并做稳定性训练',
      '进步退步幅度': '强化进步曲线：设置两周一个小目标，用阶段测验追踪提升幅度',
      '知识点达标率': '补强知识达标：按章节列出低于60%的知识点，优先做概念辨析与基础题',
      '知识点应用能力': '提升迁移应用：训练综合题审题、条件转化和跨章节联系',
      '课堂互动行为': '提升课堂参与：每节课至少完成一次提问、回答或小组表达',
      '作业提交行为': '规范作业闭环：按时提交、及时订正，并记录错因',
      '在线学习行为': '优化线上学习：保证资源浏览、视频学习和在线测验的完成率',
      '自主学习行为': '增强自主学习：固定预习、刷题、错题整理和计划完成打卡'
    };
    const items = [levelMap[level] || '根据薄弱项进行针对性提升'];
    if (['学业预警', '波动观察'].includes(potentialLabelText)) items.push('建议每两周更新一次数据，观察成绩趋势与行为活跃度是否同步改善');
    weak.slice(0, 5).forEach(item => items.push(attrMap[item.name] || `重点关注${item.name}`));
    return items;
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let value = '';
    let quoted = false;
    const content = String(text || '').replace(/^\uFEFF/, '');
    for (let i = 0; i < content.length; i++) {
      const char = content[i];
      const next = content[i + 1];
      if (quoted) {
        if (char === '"' && next === '"') {
          value += '"';
          i++;
        } else if (char === '"') {
          quoted = false;
        } else {
          value += char;
        }
      } else if (char === '"') {
        quoted = true;
      } else if (char === ',') {
        row.push(value);
        value = '';
      } else if (char === '\n') {
        row.push(value);
        rows.push(row);
        row = [];
        value = '';
      } else if (char !== '\r') {
        value += char;
      }
    }
    row.push(value);
    rows.push(row);
    const nonEmptyRows = rows.filter(items => items.some(item => String(item).trim() !== ''));
    const headers = (nonEmptyRows.shift() || []).map(item => String(item).trim());
    return { headers, rows: nonEmptyRows };
  }

  function toCsv(rows) {
    const columns = ['学号', '姓名', '班级', '学科', '综合评分', 'RSM调整分', '学业等级', '发展潜力', '规则空间Theta', '规则空间Zeta', '风险预警等级', '干预优先级', '薄弱属性', '建议摘要'];
    return [columns.join(',')].concat(rows.map(row => columns.map(col => csvCell(row[col])).join(','))).join('\n');
  }

  function downloadText(filename, text) {
    const blob = new Blob(['\ufeff' + text], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  function orderedCounts(rows, field, order) {
    const counts = {};
    order.forEach(item => { counts[item] = 0; });
    rows.forEach(row => { counts[row[field]] = (counts[row[field]] || 0) + 1; });
    return counts;
  }

  function levelFromScore(score) {
    const levels = config.levels || [];
    for (const level of levels) {
      if (score >= Number(level.min_score || 0)) return level.name;
    }
    return '需帮扶';
  }

  function setStatus(text, isError) {
    statusEl.textContent = text;
    statusEl.style.color = isError ? '#b91c1c' : '';
  }

  function mean(values) {
    const valid = values.filter(value => !Number.isNaN(value));
    return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : 0;
  }

  function percentile(values, p) {
    if (!values.length) return 0;
    const sorted = [...values].sort((a, b) => a - b);
    const index = (sorted.length - 1) * p / 100;
    const lo = Math.floor(index);
    const hi = Math.ceil(index);
    if (lo === hi) return sorted[lo];
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (index - lo);
  }

  function clamp(value, lo, hi) {
    return Math.max(lo, Math.min(hi, Number(value) || 0));
  }

  function round(value) {
    return Math.round((Number(value) || 0) * 100) / 100;
  }

  function safeNumber(value, fallback) {
    const num = Number(value);
    return Number.isNaN(num) ? fallback : num;
  }

  function normCol(col) {
    return String(col).trim().toLowerCase().replace(/\s+/g, '').replace(/[/-]/g, '_');
  }

  function csvCell(value) {
    const text = String(value ?? '');
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }
})();
