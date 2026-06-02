const CHART_COLORS = ['#2563eb', '#0f766e', '#f97316', '#7c3aed', '#dc2626', '#64748b', '#16a34a', '#b45309'];

function getCanvas(id) {
  const canvas = document.getElementById(id);
  if (!canvas) return null;
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(260, rect.width || canvas.clientWidth || 260);
  const height = Math.max(260, rect.height || canvas.clientHeight || 260);
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  return { canvas, ctx, w: width, h: height };
}

function clear(ctx, w, h) {
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);
}

function title(ctx, text, x, y) {
  ctx.fillStyle = '#0f172a';
  ctx.font = '700 15px Microsoft YaHei, Arial';
  ctx.textAlign = 'left';
  ctx.fillText(text || '', x, y);
}

function noData(ctx, w, h, chartTitle) {
  title(ctx, chartTitle, 18, 25);
  ctx.fillStyle = '#64748b';
  ctx.font = '13px Microsoft YaHei, Arial';
  ctx.textAlign = 'center';
  ctx.fillText('暂无可展示数据', w / 2, h / 2);
}

function drawGrid(ctx, pad, chartW, chartH, ticks = 5) {
  ctx.strokeStyle = '#e2e8f0';
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= ticks; i++) {
    const y = pad.t + chartH * i / ticks;
    ctx.moveTo(pad.l, y);
    ctx.lineTo(pad.l + chartW, y);
  }
  ctx.stroke();
}

function drawBarChart(id, data, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const entries = Object.entries(data || {}).filter(([_, v]) => Number(v) >= 0);
  if (!entries.length) return noData(ctx, w, h, chartTitle);
  const pad = { l: 54, r: 24, t: 46, b: 72 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  const maxV = Math.max(1, ...entries.map(([_, v]) => Number(v)));
  title(ctx, chartTitle, pad.l, 25);
  drawGrid(ctx, pad, chartW, chartH);
  ctx.strokeStyle = '#94a3b8';
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + chartH);
  ctx.lineTo(pad.l + chartW, pad.t + chartH);
  ctx.stroke();
  const step = chartW / entries.length;
  const bw = Math.min(54, step * 0.58);
  entries.forEach(([label, value], i) => {
    const x = pad.l + i * step + (step - bw) / 2;
    const barH = Number(value) / maxV * chartH;
    const y = pad.t + chartH - barH;
    ctx.fillStyle = CHART_COLORS[i % CHART_COLORS.length];
    ctx.fillRect(x, y, bw, barH);
    ctx.fillStyle = '#0f172a';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.textAlign = 'center';
    ctx.fillText(Number(value).toFixed(Number(value) % 1 ? 1 : 0), x + bw / 2, y - 7);
    ctx.save();
    ctx.translate(x + bw / 2, pad.t + chartH + 16);
    ctx.rotate(-Math.PI / 6);
    ctx.textAlign = 'right';
    ctx.fillStyle = '#475569';
    ctx.fillText(label, 0, 0);
    ctx.restore();
  });
}

function drawDonutChart(id, data, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const entries = Object.entries(data || {}).filter(([_, v]) => Number(v) > 0);
  if (!entries.length) return noData(ctx, w, h, chartTitle);
  title(ctx, chartTitle, 18, 25);
  const compact = w < 520;
  const cx = compact ? w / 2 : Math.min(w * 0.36, 150);
  const cy = compact ? h * 0.36 : h / 2 + 12;
  const radius = compact ? Math.min(72, h * 0.22, w * 0.25) : Math.min(86, h * 0.30, w * 0.22);
  const total = entries.reduce((sum, [_, v]) => sum + Number(v), 0);
  let start = -Math.PI / 2;
  entries.forEach(([_, value], i) => {
    const angle = Number(value) / total * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = CHART_COLORS[i % CHART_COLORS.length];
    ctx.fill();
    start += angle;
  });
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.58, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.fill();
  ctx.fillStyle = '#0f172a';
  ctx.font = '700 24px Microsoft YaHei, Arial';
  ctx.textAlign = 'center';
  ctx.fillText(String(total), cx, cy + 8);
  const legendX = compact ? 26 : Math.min(w * 0.62, cx + radius + 55);
  const legendY = compact ? cy + radius + 30 : 58;
  entries.forEach(([label, value], i) => {
    const y = legendY + i * (compact ? 23 : 28);
    ctx.fillStyle = CHART_COLORS[i % CHART_COLORS.length];
    ctx.fillRect(legendX, y - 10, 12, 12);
    ctx.fillStyle = '#334155';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.textAlign = 'left';
    const pct = total ? (Number(value) / total * 100).toFixed(1) : '0.0';
    const text = `${label}  ${value}人 (${pct}%)`;
    ctx.fillText(compact && text.length > 20 ? text.slice(0, 20) + '...' : text, legendX + 18, y);
  });
}

function drawHistogram(id, items, chartTitle) {
  const data = {};
  (items || []).forEach(item => { data[item.range] = item.count; });
  drawBarChart(id, data, chartTitle);
}

function drawLineChart(id, points, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const data = points || [];
  if (!data.length) return noData(ctx, w, h, chartTitle);
  const pad = { l: 58, r: 28, t: 48, b: 58 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  title(ctx, chartTitle, pad.l, 25);
  drawGrid(ctx, pad, chartW, chartH);
  ctx.strokeStyle = '#94a3b8';
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + chartH);
  ctx.lineTo(pad.l + chartW, pad.t + chartH);
  ctx.stroke();
  const step = chartW / Math.max(data.length - 1, 1);
  ctx.beginPath();
  data.forEach((point, i) => {
    const value = Math.max(0, Math.min(100, Number(point.value || 0)));
    const x = pad.l + i * step;
    const y = pad.t + chartH - value / 100 * chartH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 3;
  ctx.stroke();
  data.forEach((point, i) => {
    const value = Math.max(0, Math.min(100, Number(point.value || 0)));
    const x = pad.l + i * step;
    const y = pad.t + chartH - value / 100 * chartH;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#0f172a';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.textAlign = 'center';
    ctx.fillText(value.toFixed(1), x, y - 10);
    ctx.fillStyle = '#475569';
    ctx.save();
    ctx.translate(x, pad.t + chartH + 18);
    ctx.rotate(-Math.PI / 7);
    ctx.textAlign = 'right';
    ctx.fillText(point.stage || point.label || '', 0, 0);
    ctx.restore();
  });
}

function drawRadarChart(id, data, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const entries = Object.entries(data || {}).filter(([_, v]) => Number(v) >= 0);
  if (!entries.length) return noData(ctx, w, h, chartTitle);
  title(ctx, chartTitle, 18, 25);
  const cx = w / 2;
  const cy = h / 2 + 18;
  const radius = Math.min(w, h) * (w < 520 ? 0.24 : 0.28);
  const count = entries.length;
  ctx.strokeStyle = '#e2e8f0';
  ctx.fillStyle = '#64748b';
  ctx.font = '12px Microsoft YaHei, Arial';
  for (let ring = 1; ring <= 4; ring++) {
    ctx.beginPath();
    entries.forEach((_, i) => {
      const angle = -Math.PI / 2 + i * Math.PI * 2 / count;
      const r = radius * ring / 4;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  }
  entries.forEach(([label], i) => {
    const angle = -Math.PI / 2 + i * Math.PI * 2 / count;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius);
    ctx.stroke();
    ctx.textAlign = Math.cos(angle) > 0.25 ? 'left' : Math.cos(angle) < -0.25 ? 'right' : 'center';
    ctx.fillText(label, cx + Math.cos(angle) * (radius + 18), cy + Math.sin(angle) * (radius + 18));
  });
  ctx.beginPath();
  entries.forEach(([_, value], i) => {
    const angle = -Math.PI / 2 + i * Math.PI * 2 / count;
    const r = Math.max(0, Math.min(100, Number(value))) / 100 * radius;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = 'rgba(37, 99, 235, .22)';
  ctx.fill();
  ctx.strokeStyle = '#2563eb';
  ctx.lineWidth = 2;
  ctx.stroke();
}

function drawHorizontalBar(id, items, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const data = (items || []).map(x => [x.attribute || x[0], Number(x.unmastered_rate || x[1] || 0)]);
  if (!data.length) return noData(ctx, w, h, chartTitle);
  const pad = { l: w < 520 ? 92 : 122, r: w < 520 ? 42 : 56, t: 48, b: 26 };
  const chartW = w - pad.l - pad.r;
  const rowH = (h - pad.t - pad.b) / Math.max(data.length, 1);
  title(ctx, chartTitle, 18, 25);
  data.forEach(([label, value], i) => {
    const y = pad.t + i * rowH + Math.max(5, (rowH - 18) / 2);
    const barW = Math.max(2, value / 100 * chartW);
    ctx.fillStyle = '#475569';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.textAlign = 'right';
    const displayLabel = String(label).length > (w < 520 ? 6 : 10) ? String(label).slice(0, w < 520 ? 6 : 10) + '...' : label;
    ctx.fillText(displayLabel, pad.l - 8, y + 14);
    ctx.textAlign = 'left';
    ctx.fillStyle = '#f1f5f9';
    ctx.fillRect(pad.l, y, chartW, 18);
    ctx.fillStyle = value >= 60 ? '#dc2626' : value >= 35 ? '#f97316' : '#0f766e';
    ctx.fillRect(pad.l, y, barW, 18);
    ctx.fillStyle = '#1f2937';
    ctx.fillText(value.toFixed(1) + '%', pad.l + barW + 6, y + 14);
  });
}

function drawScatter(id, data, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const pad = { l: 54, r: 24, t: 46, b: 48 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  title(ctx, chartTitle, pad.l, 25);
  drawGrid(ctx, pad, chartW, chartH);
  ctx.strokeStyle = '#94a3b8';
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t + chartH);
  ctx.lineTo(pad.l + chartW, pad.t + chartH);
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + chartH);
  ctx.stroke();
  (data || []).forEach(p => {
    const theta = Number(p['规则空间Theta'] || 0);
    const zeta = Number(p['规则空间Zeta'] || 0);
    const x = pad.l + theta / 100 * chartW;
    const y = pad.t + chartH - zeta / 100 * chartH;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = riskColor(p['风险预警等级']) || levelColor(p['学业等级']);
    ctx.fill();
  });
  axisLabel(ctx, 'Theta：属性掌握度', pad.l + chartW - 128, pad.t + chartH + 32);
  verticalLabel(ctx, 'Zeta：偏离度', 16, pad.t + 145);
}

function drawCouplingScatter(id, data, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const pad = { l: 62, r: 30, t: 46, b: 52 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  title(ctx, chartTitle, pad.l, 25);
  drawGrid(ctx, pad, chartW, chartH);
  ctx.strokeStyle = '#cbd5e1';
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.moveTo(pad.l + chartW * 0.65, pad.t);
  ctx.lineTo(pad.l + chartW * 0.65, pad.t + chartH);
  ctx.moveTo(pad.l, pad.t + chartH * 0.35);
  ctx.lineTo(pad.l + chartW, pad.t + chartH * 0.35);
  ctx.stroke();
  ctx.setLineDash([]);
  (data || []).forEach(p => {
    const xValue = Number(p['学习行为活跃度'] || 0);
    const yValue = Number(p['知识点掌握度'] || 0);
    const rsm = Number(p['RSM调整分'] || 50);
    const x = pad.l + xValue / 100 * chartW;
    const y = pad.t + chartH - yValue / 100 * chartH;
    const radius = 3 + Math.max(0, Math.min(100, rsm)) / 100 * 4;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = riskColor(p['风险预警等级']);
    ctx.globalAlpha = 0.82;
    ctx.fill();
    ctx.globalAlpha = 1;
  });
  axisLabel(ctx, '学习行为活跃度', pad.l + chartW - 116, pad.t + chartH + 34);
  verticalLabel(ctx, '知识点掌握度', 18, pad.t + 150);
  ctx.fillStyle = '#64748b';
  ctx.font = '12px Microsoft YaHei, Arial';
  ctx.fillText('右上：高掌握、高活跃', pad.l + chartW - 140, pad.t + 18);
}

function drawHeatmap(id, rows, dimensions, chartTitle) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const data = rows || [];
  if (!data.length || !dimensions.length) return noData(ctx, w, h, chartTitle);
  const pad = { l: 100, r: 26, t: 52, b: 34 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  const cellW = chartW / dimensions.length;
  const cellH = Math.min(34, chartH / data.length);
  title(ctx, chartTitle, 18, 25);
  dimensions.forEach((dim, i) => {
    ctx.fillStyle = '#334155';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.textAlign = 'center';
    ctx.fillText(dim, pad.l + i * cellW + cellW / 2, pad.t - 12);
  });
  data.forEach((row, r) => {
    const y = pad.t + r * cellH;
    ctx.fillStyle = '#334155';
    ctx.textAlign = 'right';
    ctx.font = '12px Microsoft YaHei, Arial';
    ctx.fillText(row['学科'], pad.l - 10, y + cellH / 2 + 4);
    dimensions.forEach((dim, c) => {
      const value = Number(row[dim] || 0);
      const x = pad.l + c * cellW;
      ctx.fillStyle = heatColor(value);
      ctx.fillRect(x + 1, y + 1, cellW - 2, cellH - 2);
      ctx.fillStyle = value >= 55 ? '#ffffff' : '#0f172a';
      ctx.textAlign = 'center';
      ctx.fillText(value.toFixed(1), x + cellW / 2, y + cellH / 2 + 4);
    });
  });
}

function axisLabel(ctx, text, x, y) {
  ctx.fillStyle = '#475569';
  ctx.font = '12px Microsoft YaHei, Arial';
  ctx.textAlign = 'left';
  ctx.fillText(text, x, y);
}

function verticalLabel(ctx, text, x, y) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(-Math.PI / 2);
  axisLabel(ctx, text, 0, 0);
  ctx.restore();
}

function heatColor(value) {
  const v = Math.max(0, Math.min(100, value));
  if (v >= 80) return '#047857';
  if (v >= 65) return '#0f766e';
  if (v >= 50) return '#f97316';
  return '#dc2626';
}

function riskColor(level) {
  if (level === '红色预警') return '#dc2626';
  if (level === '橙色关注') return '#f97316';
  if (level === '黄色观察') return '#b45309';
  return '#0f766e';
}

function levelColor(level) {
  if (level === '优秀') return '#16a34a';
  if (level === '良好') return '#2563eb';
  if (level === '中等') return '#b45309';
  if (level === '待提高') return '#f97316';
  return '#dc2626';
}

function drawProtocolChart(id, chart) {
  const option = chart.option || {};
  if (chart.type === 'bar') {
    const data = {};
    (option.labels || []).forEach((label, i) => { data[label] = Number((option.values || [])[i] || 0); });
    return drawBarChart(id, data, chart.title);
  }
  if (chart.type === 'donut') {
    return drawDonutChart(id, option.data || {}, chart.title);
  }
  if (chart.type === 'radar') {
    const data = {};
    (option.indicators || []).forEach((label, i) => { data[label] = Number((option.values || [])[i] || 0); });
    return drawRadarChart(id, data, chart.title);
  }
  if (chart.type === 'line') {
    return drawLineChart(id, option.points || [], chart.title);
  }
  if (chart.type === 'horizontal_bar') {
    return drawHorizontalBar(id, option.items || [], chart.title);
  }
  if (chart.type === 'heatmap') {
    return drawHeatmap(id, option.rows || [], option.dimensions || [], chart.title);
  }
  if (chart.type === 'scatter') {
    return drawGenericScatter(id, option.points || [], chart.title, option.x_name || 'X', option.y_name || 'Y');
  }
  return drawBarChart(id, {}, chart.title);
}

function drawGenericScatter(id, data, chartTitle, xName, yName) {
  const item = getCanvas(id);
  if (!item) return;
  const { ctx, w, h } = item;
  clear(ctx, w, h);
  const points = data || [];
  if (!points.length) return noData(ctx, w, h, chartTitle);
  const pad = { l: 62, r: 30, t: 48, b: 54 };
  const chartW = w - pad.l - pad.r;
  const chartH = h - pad.t - pad.b;
  title(ctx, chartTitle, pad.l, 25);
  drawGrid(ctx, pad, chartW, chartH);
  ctx.strokeStyle = '#94a3b8';
  ctx.beginPath();
  ctx.moveTo(pad.l, pad.t);
  ctx.lineTo(pad.l, pad.t + chartH);
  ctx.lineTo(pad.l + chartW, pad.t + chartH);
  ctx.stroke();
  points.forEach(p => {
    const xValue = Math.max(0, Math.min(100, Number(p.x || 0)));
    const yValue = Math.max(0, Math.min(100, Number(p.y || 0)));
    const x = pad.l + xValue / 100 * chartW;
    const y = pad.t + chartH - yValue / 100 * chartH;
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = riskColor(p.risk) || levelColor(p.level);
    ctx.fill();
  });
  axisLabel(ctx, xName, pad.l + chartW - 128, pad.t + chartH + 34);
  verticalLabel(ctx, yName, 18, pad.t + 146);
}
