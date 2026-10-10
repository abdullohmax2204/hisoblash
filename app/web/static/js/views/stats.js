/**
 * Statistics and analytics view with Chart.js donut graph.
 */

import { state } from '../state.js';
import { formatMoney, haptic } from '../utils.js';

export function renderStats(stats) {
  const titleEl = document.getElementById('statsPeriodTitle');
  const incEl = document.getElementById('statsIncome');
  const expEl = document.getElementById('statsExpense');
  const netEl = document.getElementById('statsNet');

  if (titleEl) titleEl.textContent = `Период: ${stats.title}`;
  if (incEl) incEl.textContent = formatMoney(stats.total_income);
  if (expEl) expEl.textContent = formatMoney(stats.total_expense);
  if (netEl) netEl.textContent = formatMoney(stats.net_income);

  // Render Category Breakdown & Chart
  const topList = document.getElementById('topCategoriesList');
  const chartWrapper = document.querySelector('.chart-container');
  const categories = stats.top_categories || [];

  if (topList) {
    if (!categories.length) {
      if (chartWrapper) chartWrapper.style.display = 'none';
      topList.innerHTML = `
        <div class="chart-empty-state">
          <div class="chart-empty-icon">
            <svg viewBox="0 0 24 24" width="28" height="28" stroke="currentColor" stroke-width="2" fill="none">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
          </div>
          <div class="chart-empty-title">Нет расходов за выбранный период</div>
          <div class="chart-empty-sub">Запишите расход кнопкой на главной или выберите другой период выше</div>
        </div>
      `;
    } else {
      if (chartWrapper) chartWrapper.style.display = 'block';
      topList.innerHTML = categories.map(c => `
        <div class="cat-row">
          <div class="cat-row-left">
            <span>${c.icon || '🛍'}</span>
            <span>${c.name}</span>
          </div>
          <div class="text-red font-bold">${formatMoney(c.total)}</div>
        </div>
      `).join('');
    }
  }

  // Render Chart.js
  renderChart(categories);
}

export function renderChart(categories) {
  const canvas = document.getElementById('categoriesChart');
  const ctx = canvas?.getContext('2d');
  if (!ctx || typeof window.Chart === 'undefined') return;

  if (state.chartInstance) {
    state.chartInstance.destroy();
  }

  if (!categories.length) {
    return;
  }

  const labels = categories.map(c => `${c.icon || ''} ${c.name}`);
  const data = categories.map(c => Number(c.total));
  const colors = [
    '#f43f5e', '#fb7185', '#fda4af',
    '#38bdf8', '#818cf8', '#a78bfa',
    '#34d399', '#fbbf24', '#f97316'
  ];

  state.chartInstance = new window.Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.slice(0, categories.length),
        borderWidth: 2,
        borderColor: '#1e293b',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', boxWidth: 12, padding: 12 },
        },
      },
    },
  });
}

export function changePeriod(period, btn, loadStatsCallback) {
  haptic('light');
  document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.statsPeriod = period;
  if (typeof loadStatsCallback === 'function') {
    loadStatsCallback(period);
  }
}
