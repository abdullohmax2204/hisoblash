/**
 * Overview tab view: Capital hero card, fast action carousel, accounts, stress analysis, recent transactions.
 */

import { state } from '../state.js';
import { formatMoney, formatDate } from '../utils.js';
import { getCategoryIcon, getIconHTML } from '../icons.js';
import { populateAccountDropdowns } from '../components/modals.js';

export function createTxItemHTML(tx, allowDelete = false) {
  let sign = '';
  let colorClass = 'expense';
  let iconKey = tx.category_name || tx.category_icon || 'expense';

  if (tx.type === 'income' || tx.type === 'INCOME') {
    sign = '+';
    colorClass = 'income';
  } else if (tx.type === 'expense' || tx.type === 'EXPENSE') {
    sign = '-';
    colorClass = 'expense';
  } else if (tx.type === 'transfer' || tx.type === 'TRANSFER') {
    sign = '';
    colorClass = 'transfer';
    iconKey = 'transfer';
  } else if (tx.type === 'saving' || tx.type === 'SAVING') {
    sign = '';
    colorClass = 'saving';
    iconKey = 'target';
  } else if (tx.type === 'saving_withdraw' || tx.type === 'SAVING_WITHDRAW') {
    sign = '+';
    colorClass = 'income';
    iconKey = 'target';
  } else if (tx.type === 'debt_given' || tx.type === 'DEBT_GIVEN' || tx.type === 'debt_taken' || tx.type === 'DEBT_TAKEN' || tx.type === 'debt_return' || tx.type === 'DEBT_RETURN') {
    sign = '';
    colorClass = 'debt';
    iconKey = 'debt';
  }

  const title = tx.category_name || tx.description || 'Операция';
  const iconHTML = getCategoryIcon(iconKey);
  const meta = `${tx.account_name || 'Счет'} • ${formatDate(tx.created_at)}`;

  const deleteBtn = allowDelete
    ? `<button class="tx-del-btn" onclick="window.deleteTransaction(${tx.id})">Удалить</button>`
    : '';

  return `
    <div class="tx-item">
      <div class="tx-left">
        <div class="tx-icon-box ${colorClass}">${iconHTML}</div>
        <div class="tx-info">
          <div class="tx-title">${title}</div>
          <div class="tx-meta">${meta}</div>
        </div>
      </div>
      <div class="tx-right">
        <div class="tx-amount ${colorClass}">${sign}${formatMoney(tx.amount)}</div>
        ${deleteBtn}
      </div>
    </div>
  `;
}

export function renderRecentTx(transactions) {
  const container = document.getElementById('recentTxList');
  if (!container) return;
  if (!transactions.length) {
    container.innerHTML = `
      <div class="tx-empty-state">
        <div class="tx-empty-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
            <polyline points="12 8 12 12 14 14"></polyline>
            <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
          </svg>
        </div>
        <div class="tx-empty-title">Нет недавних операций</div>
        <div class="tx-empty-sub">Добавьте расход или доход кнопками выше</div>
      </div>
    `;
    return;
  }
  container.innerHTML = transactions.map(tx => createTxItemHTML(tx)).join('');
}

export function renderDashboard() {
  if (!state.summary) return;

  const s = state.summary;
  const totalEl = document.getElementById('totalCapital');
  const availEl = document.getElementById('availableFunds');
  const saveEl = document.getElementById('savingsBalance');
  const debtsNetEl = document.getElementById('debtsNet');

  if (totalEl) totalEl.textContent = formatMoney(s.total_capital);
  if (availEl) availEl.textContent = formatMoney(s.available_funds);
  if (saveEl) saveEl.textContent = formatMoney(s.savings_balance);

  const debtsNet = (Number(s.debts_given || 0) - Number(s.debts_taken || 0));
  if (debtsNetEl) {
    debtsNetEl.textContent = formatMoney(debtsNet);
    debtsNetEl.className = `mini-val ${debtsNet >= 0 ? 'text-green' : 'text-red'}`;
  }

  // Mini Goals Widget if present
  const widget = document.getElementById('goalsMiniWidget');
  if (widget) {
    if (s.has_goals) {
      widget.style.display = 'block';
      const pctEl = document.getElementById('overallGoalsPct');
      const barEl = document.getElementById('overallGoalsBar');
      const subEl = document.getElementById('goalsMiniSub');
      if (pctEl) pctEl.textContent = `${s.overall_goals_pct}%`;
      if (barEl) barEl.style.width = `${Math.min(s.overall_goals_pct, 100)}%`;
      if (subEl) subEl.textContent = `Накоплено: ${formatMoney(s.savings_balance)}`;
    } else {
      widget.style.display = 'none';
    }
  }

  // Recent Transactions
  renderRecentTx(s.recent_transactions || []);
}

export function renderAccountsList() {
  const scrollContainer = document.getElementById('accountsList');
  const allGrid = document.getElementById('allAccountsList');
  if (!state.accounts) return;

  const html = state.accounts.map(acc => `
    <div class="account-card-item">
      <div class="acc-icon-badge">${getIconHTML(acc.icon || 'card')}</div>
      <div class="acc-info">
        <div class="acc-name">${acc.name}</div>
        <div class="acc-balance">${formatMoney(acc.balance, acc.currency)}</div>
      </div>
    </div>
  `).join('');

  const emptyHTML = `
    <div class="account-empty-card" onclick="openModal('modalNewAccount')">
      <div class="account-empty-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
          <rect x="2" y="5" width="20" height="14" rx="2"></rect>
          <line x1="2" y1="10" x2="22" y2="10"></line>
          <line x1="12" y1="13" x2="12" y2="17"></line>
          <line x1="10" y1="15" x2="14" y2="15"></line>
        </svg>
      </div>
      <div class="account-empty-info">
        <div class="account-empty-title">+ Добавить первый счет</div>
        <div class="account-empty-sub">Uzcard, Humo, Visa, Наличные</div>
      </div>
    </div>
  `;

  if (scrollContainer) scrollContainer.innerHTML = html || emptyHTML;
  if (allGrid) allGrid.innerHTML = html || emptyHTML;

  populateAccountDropdowns();
}

export function renderLoadAnalysis(a) {
  if (!a) return;

  const badge = document.getElementById('loadStatusBadge');
  const monthlyVal = document.getElementById('loadMonthlyVal');
  const val15Day = document.getElementById('load15DayVal');
  const barFill = document.getElementById('stressBarFill');
  const recText = document.getElementById('loadRecommendationText');
  const breakdownContainer = document.getElementById('loadGoalsBreakdown');

  if (badge) {
    const levelLabel = a.stress_level === 'green' ? 'Безопасно' : (a.stress_level === 'yellow' ? 'Умеренно' : 'Высокая');
    badge.innerHTML = `<span class="status-dot ${a.stress_level}"></span> ${a.stress_pct}% • ${levelLabel}`;
    badge.className = `status-badge ${a.stress_level}`;
  }

  if (monthlyVal) monthlyVal.textContent = `${formatMoney(a.total_required_monthly)}/мес`;
  if (val15Day) val15Day.textContent = `${formatMoney(a.total_required_15day)}/15дн`;

  if (barFill) {
    barFill.style.width = `${Math.min(a.stress_pct, 100)}%`;
    barFill.className = `stress-bar-fill ${a.stress_level}`;
  }

  if (recText) {
    recText.textContent = a.recommendation;
  }

  if (breakdownContainer) {
    if (!a.goals || !a.goals.length) {
      breakdownContainer.innerHTML = '<div style="font-size: 11px; color: var(--text-tertiary); text-align: center; padding: 6px 0;">Нет активных целей накоплений. Нажмите «+ Цель», чтобы добавить цель.</div>';
      return;
    }

    breakdownContainer.innerHTML = a.goals.map(g => {
      const dateInfo = g.target_date ? `дедлайн: ${formatDate(g.target_date)} (${g.months_left} мес)` : 'без даты (расчет на 12 мес)';
      return `
        <div class="load-goal-item">
          <div>
            <div class="load-goal-name">${g.name}</div>
            <div class="load-goal-details" style="text-align: left; font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">${dateInfo}</div>
          </div>
          <div class="load-goal-details">
            <div class="load-goal-req">${formatMoney(g.required_monthly)}/мес</div>
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">(${formatMoney(g.required_15day)}/15дн)</div>
          </div>
        </div>
      `;
    }).join('');
  }
}
