function renderModelPage(modelResult) {
  if (!modelResult || !Array.isArray(modelResult.charts)) return;
  renderModelCharts(modelResult);
  bindStudentSearch();
  bindModelResize(modelResult);
}

function renderModelCharts(modelResult) {
  modelResult.charts.forEach(chart => {
    renderProtocolChart(chart);
  });
}

function renderProtocolChart(chart) {
  if (!chart || !chart.chart_id) return;
  if (typeof drawProtocolChart === 'function') {
    drawProtocolChart(chart.chart_id, chart);
  }
}

function bindStudentSearch() {
  const input = document.getElementById('studentSearch');
  const table = document.getElementById('modelStudentTable');
  if (!input || !table) return;
  if (input.dataset.bound === '1') return;
  input.dataset.bound = '1';
  input.addEventListener('input', () => {
    const keyword = input.value.trim().toLowerCase();
    table.querySelectorAll('[data-student-row]').forEach(row => {
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(keyword) ? '' : 'none';
    });
  });
}

function bindModelResize(modelResult) {
  if (window.__modelResizeBound) return;
  window.__modelResizeBound = true;
  let timer = null;
  window.addEventListener('resize', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => renderModelCharts(modelResult), 120);
  });
}
