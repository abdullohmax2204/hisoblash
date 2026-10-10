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

  // Render Category Breakdown
  const topList = document.getElementById('topCategoriesList');
  if (topList) {
    if (!stats.top_categories || !stats.top_categories.length) {
      topList.innerHTML = '<div class="empty-state">За этот период расходов не найдено</div>';
    } else {
      topList.innerHTML = stats.top_categories.map(c => `
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
  renderChart(stats.top_categories || []);
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
