/**
 * Hisoblash Telegram Mini App - Client Logic
 */

// Initialize Telegram WebApp SDK & Theme Detection
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();

  const isLight = tg.colorScheme === 'light' || isLightBg(tg.themeParams?.bg_color);
  if (isLight) {
    document.body.classList.add('light-theme');
  }
}

function isLightBg(hex) {
  if (!hex || typeof hex !== 'string' || !hex.startsWith('#')) return false;
  const rgb = parseInt(hex.slice(1), 16);
  if (isNaN(rgb)) return false;
  const r = (rgb >> 16) & 0xff;
  const g = (rgb >> 8) & 0xff;
  const b = (rgb >> 0) & 0xff;
  const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return luma > 128;
}

// Global Application State
const state = {
  user: null,
  summary: null,
  accounts: [],
  categories: { expense: [], income: [] },
  debts: { given: [], taken: [] },
  currentDebtType: 'given',
  statsPeriod: 'month',
  chartInstance: null,
  historyPage: 0,
  historyHasNext: false,
  balanceVisible: true,
};

// ==================== UTILS ====================

function haptic(type = 'light') {
  try {
    if (tg?.HapticFeedback) {
      if (['light', 'medium', 'heavy', 'rigid', 'soft'].includes(type)) {
        tg.HapticFeedback.impactOccurred(type);
      } else if (['error', 'success', 'warning'].includes(type)) {
        tg.HapticFeedback.notificationOccurred(type);
      }
    }
  } catch (e) {
    console.debug('Haptics not supported');
  }
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : '⚠️'}</span> <span>${message}</span>`;
  container.appendChild(toast);

  haptic(type === 'success' ? 'success' : 'error');

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function formatMoney(amount) {
  if (amount === undefined || amount === null) return '0 сум';
  if (!state.balanceVisible) return '••••••';
  const num = Number(amount);
  const formatted = num.toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).replace(/,/g, ' ');
  return `${formatted} сум`;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const month = months[d.getMonth()];
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day} ${month}, ${hours}:${minutes}`;
}

// ==================== API LAYER ====================

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  }

  const activeProfileId = localStorage.getItem('activeProfileId');
  if (activeProfileId) {
    headers['X-Profile-Id'] = activeProfileId;
  }

  try {
    const res = await fetch(endpoint, {
      ...options,
      headers,
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || `HTTP error ${res.status}`);
    }
    return data;
  } catch (err) {
    console.error(`API Fetch Error (${endpoint}):`, err);
    throw err;
  }
}

// ==================== DATA LOADERS ====================

async function loadSummary() {
  try {
    const data = await apiFetch('/api/summary');
    state.summary = data;
    state.accounts = data.regular_accounts || [];
    renderDashboard();
    renderAccountsList();
    renderGoals();
    await loadLoadAnalysis();
  } catch (err) {
    showToast('Ошибка загрузки данных', 'error');
  }
}

async function loadLoadAnalysis() {
  try {
    const analysis = await apiFetch('/api/savings/load-analysis');
    renderLoadAnalysis(analysis);
  } catch (err) {
    console.error('Error loading load analysis:', err);
  }
}

async function loadCategories() {
  try {
    const data = await apiFetch('/api/categories');
    state.categories = data;
    populateCategoryDropdowns();
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

async function loadDebts() {
  try {
    const data = await apiFetch('/api/debts');
    state.debts = data;
    renderDebtsList();
  } catch (err) {
    showToast('Ошибка загрузки долгов', 'error');
  }
}

async function loadStats(period = state.statsPeriod) {
  try {
    state.statsPeriod = period;
    const data = await apiFetch(`/api/stats?period=${period}`);
    renderStats(data);
  } catch (err) {
    showToast('Ошибка загрузки аналитики', 'error');
  }
}

async function loadHistory(page = 0) {
  try {
    state.historyPage = page;
    const data = await apiFetch(`/api/history?page=${page}&page_size=15`);
    state.historyHasNext = data.has_next;
    renderFullHistory(data.transactions);
  } catch (err) {
    showToast('Ошибка загрузки истории', 'error');
  }
}

// ==================== RENDERERS ====================

function renderDashboard() {
  if (!state.summary) return;

  const s = state.summary;
  document.getElementById('totalCapital').textContent = formatMoney(s.total_capital);
  document.getElementById('availableFunds').textContent = formatMoney(s.available_funds);
  document.getElementById('savingsBalance').textContent = formatMoney(s.savings_balance);

  const debtsNet = (Number(s.debts_given || 0) - Number(s.debts_taken || 0));
  const debtsNetEl = document.getElementById('debtsNet');
  debtsNetEl.textContent = formatMoney(debtsNet);
  debtsNetEl.className = `mini-val ${debtsNet >= 0 ? 'text-green' : 'text-red'}`;

  // Mini Goals Widget
  const widget = document.getElementById('goalsMiniWidget');
  if (s.has_goals) {
    widget.style.display = 'block';
    document.getElementById('overallGoalsPct').textContent = `${s.overall_goals_pct}%`;
    document.getElementById('overallGoalsBar').style.width = `${Math.min(s.overall_goals_pct, 100)}%`;
    document.getElementById('goalsMiniSub').textContent = `Накоплено: ${formatMoney(s.savings_balance)}`;
  } else {
    widget.style.display = 'none';
  }

  // Recent Transactions
  renderRecentTx(s.recent_transactions || []);
}

function renderRecentTx(transactions) {
  const container = document.getElementById('recentTxList');
  if (!transactions.length) {
    container.innerHTML = '<div class="empty-state">Нет недавних операций</div>';
    return;
  }

  container.innerHTML = transactions.map(tx => createTxItemHTML(tx)).join('');
}

function createTxItemHTML(tx, allowDelete = false) {
  let sign = '';
  let colorClass = 'expense';

  if (tx.type === 'income') {
    sign = '+';
    colorClass = 'income';
  } else if (tx.type === 'expense') {
    sign = '-';
    colorClass = 'expense';
  } else if (tx.type === 'transfer') {
    sign = '🔁 ';
    colorClass = 'transfer';
  } else if (tx.type === 'saving') {
    sign = '💵 ';
    colorClass = 'saving';
  } else if (tx.type === 'saving_withdraw') {
    sign = '↩️ ';
    colorClass = 'income';
  } else if (tx.type === 'debt_given' || tx.type === 'debt_taken' || tx.type === 'debt_return') {
    sign = '🤝 ';
    colorClass = 'debt';
  }

  const title = tx.category_name || tx.description || 'Операция';
  const icon = tx.category_icon || '📝';
  const meta = `${tx.account_name || 'Счет'} • ${formatDate(tx.created_at)}`;

  const deleteBtn = allowDelete
    ? `<button class="tx-del-btn" onclick="deleteTransaction(${tx.id})">Удалить</button>`
    : '';

  return `
    <div class="tx-item">
      <div class="tx-left">
        <div class="tx-icon-box">${icon}</div>
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

function renderAccountsList() {
  const scrollContainer = document.getElementById('accountsList');
  const allGrid = document.getElementById('allAccountsList');
  if (!state.accounts) return;

  const html = state.accounts.map(acc => `
    <div class="account-card-item">
      <div class="acc-icon">${acc.icon || '💳'}</div>
      <div class="acc-name">${acc.name}</div>
      <div class="acc-balance">${formatMoney(acc.balance)}</div>
    </div>
  `).join('');

  if (scrollContainer) scrollContainer.innerHTML = html || '<div class="empty-state">Нет счетов</div>';
  if (allGrid) allGrid.innerHTML = html || '<div class="empty-state">Нет счетов</div>';

  populateAccountDropdowns();
}

function renderGoals() {
  if (!state.summary) return;
  const goals = state.summary.goals || [];
  const goalsContainer = document.getElementById('savingsGoalsList');
  document.getElementById('savingsTabBalance').textContent = formatMoney(state.summary.savings_balance);

  if (!goals.length) {
    goalsContainer.innerHTML = '<div class="empty-state">Целей накоплений пока нет. Нажмите "+ Новая цель"</div>';
    return;
  }

  goalsContainer.innerHTML = goals.map(g => `
    <div class="goal-item">
      <div class="goal-top">
        <div class="goal-name">${g.name} ${g.is_funded ? '✅' : ''}</div>
        <div>
          <span class="goal-target">${g.pct}% (${formatMoney(g.target_amount)})</span>
          <button class="goal-delete-btn" onclick="deleteGoal(${g.id})" title="Удалить">✕</button>
        </div>
      </div>
      ${g.target_date ? `<div style="font-size:11px; color:#94a3b8; margin-top:-2px; margin-bottom:6px;">⏳ Дедлайн: ${formatDate(g.target_date)}</div>` : ''}
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${Math.min(g.pct, 100)}%;"></div>
      </div>
    </div>
  `).join('');
}

function renderLoadAnalysis(a) {
  if (!a) return;

  const badge = document.getElementById('loadStatusBadge');
  const monthlyVal = document.getElementById('loadMonthlyVal');
  const val15Day = document.getElementById('load15DayVal');
  const barFill = document.getElementById('stressBarFill');
  const recText = document.getElementById('loadRecommendationText');
  const breakdownContainer = document.getElementById('loadGoalsBreakdown');

  if (badge) {
    badge.textContent = `${a.stress_icon} ${a.stress_pct}%`;
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
      breakdownContainer.innerHTML = '';
      return;
    }

    breakdownContainer.innerHTML = a.goals.map(g => {
      const dateInfo = g.target_date ? `⏳ дедлайн: ${formatDate(g.target_date)} (${g.months_left} мес)` : 'без даты (расчет на 12 мес)';
      return `
        <div class="load-goal-item">
          <div>
            <div class="load-goal-name">${g.name}</div>
            <div class="load-goal-details" style="text-align: left; font-size: 11px; color: #94a3b8;">${dateInfo}</div>
          </div>
          <div class="load-goal-details">
            <div class="load-goal-req">${formatMoney(g.required_monthly)}/мес</div>
            <div style="font-size: 11px; color: #94a3b8;">(${formatMoney(g.required_15day)}/15дн)</div>
          </div>
        </div>
      `;
    }).join('');
  }
}

function renderDebtsList() {
  const container = document.getElementById('debtsList');
  const list = state.debts[state.currentDebtType] || [];

  if (!list.length) {
    container.innerHTML = `<div class="empty-state">Нет активных записей в разделе "${state.currentDebtType === 'given' ? 'Мне должны' : 'Я должен'}"</div>`;
    return;
  }

  container.innerHTML = list.map(d => `
    <div class="debt-item">
      <div class="debt-item-info">
        <div class="person">👤 ${d.person_name}</div>
        <div class="date">Создан: ${formatDate(d.created_at)}</div>
      </div>
      <div class="debt-item-right">
        <div class="rem-amount">${formatMoney(d.remaining_amount)}</div>
        <button class="btn-repay" onclick="openReturnDebtModal(${d.id}, '${d.person_name}', ${d.remaining_amount})">
          ${state.currentDebtType === 'given' ? 'Вернули долг' : 'Погасить'}
        </button>
      </div>
    </div>
  `).join('');
}

function renderStats(stats) {
  document.getElementById('statsPeriodTitle').textContent = `Период: ${stats.title}`;
  document.getElementById('statsIncome').textContent = formatMoney(stats.total_income);
  document.getElementById('statsExpense').textContent = formatMoney(stats.total_expense);
  document.getElementById('statsNet').textContent = formatMoney(stats.net_income);

  // Render Category Breakdown
  const topList = document.getElementById('topCategoriesList');
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

  // Render Chart.js
  renderChart(stats.top_categories || []);
}

function renderChart(categories) {
  const ctx = document.getElementById('categoriesChart')?.getContext('2d');
  if (!ctx) return;

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

  state.chartInstance = new Chart(ctx, {
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

function renderFullHistory(transactions) {
  const container = document.getElementById('fullHistoryList');
  const pagination = document.getElementById('historyPagination');

  if (!transactions.length && state.historyPage === 0) {
    container.innerHTML = '<div class="empty-state">История операций пуста</div>';
    pagination.style.display = 'none';
    return;
  }

  container.innerHTML = transactions.map(tx => createTxItemHTML(tx, true)).join('');
  pagination.style.display = 'flex';
  document.getElementById('pageIndicator').textContent = `Стр. ${state.historyPage + 1}`;
  document.getElementById('prevPageBtn').disabled = state.historyPage === 0;
  document.getElementById('nextPageBtn').disabled = !state.historyHasNext;
}

// ==================== DROPDOWNS POPULATION ====================

function populateAccountDropdowns() {
  const regularAccs = state.accounts.filter(a => !a.is_savings);
  const optionsHtml = regularAccs.map(a => `<option value="${a.id}">${a.icon || '💳'} ${a.name} (${formatMoney(a.balance)})</option>`).join('');

  const ids = [
    'incomeAccount', 'expenseAccount', 'transferFromAccount',
    'transferToAccount', 'saveDepositSource', 'saveWithdrawDest',
    'debtAccount'
  ];

  ids.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = optionsHtml;
  });
}

function populateCategoryDropdowns() {
  const expEl = document.getElementById('expenseCategory');
  const incEl = document.getElementById('incomeCategory');

  if (expEl && state.categories.expense) {
    expEl.innerHTML = state.categories.expense.map(c => `
      <option value="${c.id}">${c.icon || '🛍'} ${c.name}</option>
    `).join('');
  }

  if (incEl && state.categories.income) {
    incEl.innerHTML = '<option value="">(Без категории)</option>' + state.categories.income.map(c => `
      <option value="${c.id}">${c.icon || '💰'} ${c.name}</option>
    `).join('');
  }
}

// ==================== NAVIGATION & MODALS ====================

function switchTab(tabId) {
  haptic('light');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const activeTab = document.getElementById(tabId);
  const activeNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);

  if (activeTab) activeTab.classList.add('active');
  if (activeNav) activeNav.classList.add('active');

  // Trigger data reload for specific tabs
  if (tabId === 'tab-stats') loadStats();
  if (tabId === 'tab-debts') loadDebts();
  if (tabId === 'tab-history') loadHistory(0);
}

function openModal(modalId) {
  haptic('medium');
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

function closeModal(modalId) {
  haptic('light');
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

function addAmount(inputId, delta) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    const current = Number(input.value || 0);
    input.value = current + delta;
  }
}

function switchDebtType(type) {
  haptic('light');
  state.currentDebtType = type;
  document.getElementById('btnDebtGiven').classList.toggle('active', type === 'given');
  document.getElementById('btnDebtTaken').classList.toggle('active', type === 'taken');
  renderDebtsList();
}

function changePeriod(period, btn) {
  haptic('light');
  document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadStats(period);
}

function loadHistoryPage(direction) {
  const newPage = state.historyPage + direction;
  if (newPage >= 0) {
    loadHistory(newPage);
  }
}

// ==================== FORM SUBMISSIONS ====================

async function handleFormSubmit(e, asyncCallback) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    if (submitBtn.disabled) return;
    submitBtn.disabled = true;
    submitBtn.dataset.origText = submitBtn.textContent;
    submitBtn.textContent = 'Обработка...';
  }
  haptic('medium');

  try {
    await asyncCallback();
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      if (submitBtn.dataset.origText) {
        submitBtn.textContent = submitBtn.dataset.origText;
      }
    }
  }
}

async function submitIncome(e) {
  await handleFormSubmit(e, async () => {
    const amount = document.getElementById('incomeAmount').value;
    const account_id = document.getElementById('incomeAccount').value;
    const category_id = document.getElementById('incomeCategory').value;
    const description = document.getElementById('incomeDesc').value;

    try {
      await apiFetch('/api/transactions/income', {
        method: 'POST',
        body: JSON.stringify({ amount, account_id, category_id, description }),
      });
      closeModal('modalIncome');
      document.getElementById('formIncome').reset();
      showToast('Доход успешно добавлен!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitExpense(e) {
  await handleFormSubmit(e, async () => {
    const amount = document.getElementById('expenseAmount').value;
    const account_id = document.getElementById('expenseAccount').value;
    const category_id = document.getElementById('expenseCategory').value;
    const description = document.getElementById('expenseDesc').value;

    try {
      await apiFetch('/api/transactions/expense', {
        method: 'POST',
        body: JSON.stringify({ amount, account_id, category_id, description }),
      });
      closeModal('modalExpense');
      document.getElementById('formExpense').reset();
      showToast('Расход записан!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitTransfer(e) {
  await handleFormSubmit(e, async () => {
    const amount = document.getElementById('transferAmount').value;
    const from_account_id = document.getElementById('transferFromAccount').value;
    const to_account_id = document.getElementById('transferToAccount').value;

    try {
      await apiFetch('/api/transactions/transfer', {
        method: 'POST',
        body: JSON.stringify({ amount, from_account_id, to_account_id }),
      });
      closeModal('modalTransfer');
      document.getElementById('formTransfer').reset();
      showToast('Перевод успешно выполнен!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitSaveDeposit(e) {
  await handleFormSubmit(e, async () => {
    const amount = document.getElementById('saveDepositAmount').value;
    const source_account_id = document.getElementById('saveDepositSource').value;
    const description = document.getElementById('saveDepositDesc').value;

    try {
      const res = await apiFetch('/api/savings/deposit', {
        method: 'POST',
        body: JSON.stringify({ amount, source_account_id, description }),
      });
      closeModal('modalSaveDeposit');
      document.getElementById('formSaveDeposit').reset();
      showToast('Отложено в накопления!');
      if (res.reached_goals && res.reached_goals.length) {
        showToast(`🎉 Достигнута цель: ${res.reached_goals.join(', ')}!`, 'success');
      }
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitSaveWithdraw(e) {
  await handleFormSubmit(e, async () => {
    const amount = document.getElementById('saveWithdrawAmount').value;
    const dest_account_id = document.getElementById('saveWithdrawDest').value;
    const description = document.getElementById('saveWithdrawDesc').value;

    try {
      await apiFetch('/api/savings/withdraw', {
        method: 'POST',
        body: JSON.stringify({ amount, dest_account_id, description }),
      });
      closeModal('modalSaveWithdraw');
      document.getElementById('formSaveWithdraw').reset();
      showToast('Деньги выведены из накоплений');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitNewAccount(e) {
  await handleFormSubmit(e, async () => {
    const name = document.getElementById('newAccountName').value;
    const icon = document.querySelector('input[name="accIcon"]:checked')?.value || '💳';
    const initial_balance = document.getElementById('newAccountBalance').value || 0;

    try {
      await apiFetch('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({ name, icon, initial_balance }),
      });
      closeModal('modalNewAccount');
      document.getElementById('formNewAccount').reset();
      showToast('Новый счёт создан!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitNewGoal(e) {
  await handleFormSubmit(e, async () => {
    const name = document.getElementById('newGoalName').value;
    const target_amount = document.getElementById('newGoalTarget').value;
    const target_date = document.getElementById('newGoalDate').value;

    try {
      await apiFetch('/api/savings/goals', {
        method: 'POST',
        body: JSON.stringify({ name, target_amount, target_date }),
      });
      closeModal('modalNewGoal');
      document.getElementById('formNewGoal').reset();
      showToast('Новая цель создана!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

function openSalaryModal() {
  openModal('modalSalary');
}

async function submitSalaryForm(e) {
  await handleFormSubmit(e, async () => {
    const monthly_salary = document.getElementById('salaryMonthlyInput').value;
    const pay_cycle_days = document.getElementById('salaryCycleInput').value;

    try {
      const analysis = await apiFetch('/api/user/salary', {
        method: 'POST',
        body: JSON.stringify({ monthly_salary, pay_cycle_days }),
      });
      closeModal('modalSalary');
      showToast('Настройки дохода сохранены!');
      renderLoadAnalysis(analysis);
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function deleteGoal(goalId) {
  if (!confirm('Удалить эту цель накоплений?')) return;
  haptic('medium');
  try {
    await apiFetch(`/api/savings/goals/${goalId}`, { method: 'DELETE' });
    showToast('Цель удалена');
    await loadSummary();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteTransaction(txId) {
  if (!confirm('Отменить и удалить эту операцию? Баланс счёта будет восстановлен.')) return;
  haptic('medium');
  try {
    await apiFetch(`/api/transactions/${txId}`, { method: 'DELETE' });
    showToast('Операция отменена');
    await loadSummary();
    await loadHistory(state.historyPage);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==================== DEBT MODAL DISPATCHER ====================

function openGiveDebtModal() {
  document.getElementById('debtModalTitle').textContent = '🤝 Дать в долг';
  document.getElementById('debtFormMode').value = 'give';
  document.getElementById('debtPersonGroup').style.display = 'block';
  document.getElementById('debtAccountLabel').textContent = 'Списать со счёта';
  document.getElementById('debtSubmitBtn').textContent = 'Дать в долг';
  document.getElementById('formDebt').reset();
  openModal('modalDebt');
}

function openTakeDebtModal() {
  document.getElementById('debtModalTitle').textContent = '🤝 Взять в долг';
  document.getElementById('debtFormMode').value = 'take';
  document.getElementById('debtPersonGroup').style.display = 'block';
  document.getElementById('debtAccountLabel').textContent = 'Зачислить на счёт';
  document.getElementById('debtSubmitBtn').textContent = 'Взять в долг';
  document.getElementById('formDebt').reset();
  openModal('modalDebt');
}

function openReturnDebtModal(debtId, personName, remAmount) {
  document.getElementById('debtModalTitle').textContent = `Погашение долга (${personName})`;
  document.getElementById('debtFormMode').value = 'return';
  document.getElementById('debtReturnId').value = debtId;
  document.getElementById('debtPersonGroup').style.display = 'none';
  document.getElementById('debtAmount').value = remAmount;
  document.getElementById('debtAccountLabel').textContent = 'Счёт для взаиморасчёта';
  document.getElementById('debtSubmitBtn').textContent = 'Подтвердить возврат';
  openModal('modalDebt');
}

async function submitDebtForm(e) {
  await handleFormSubmit(e, async () => {
    const mode = document.getElementById('debtFormMode').value;
    const amount = document.getElementById('debtAmount').value;
    const account_id = document.getElementById('debtAccount').value;
    const person_name = document.getElementById('debtPersonName').value;
    const debt_id = document.getElementById('debtReturnId').value;

    try {
      if (mode === 'give') {
        await apiFetch('/api/debts/give', {
          method: 'POST',
          body: JSON.stringify({ person_name, amount, account_id }),
        });
        showToast('Долг записан!');
      } else if (mode === 'take') {
        await apiFetch('/api/debts/take', {
          method: 'POST',
          body: JSON.stringify({ person_name, amount, account_id }),
        });
        showToast('Долг записан!');
      } else if (mode === 'return') {
        await apiFetch('/api/debts/return', {
          method: 'POST',
          body: JSON.stringify({ debt_id, amount, account_id }),
        });
        showToast('Долг успешно погашен!');
      }
      closeModal('modalDebt');
      await loadSummary();
      await loadDebts();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', async () => {
  // Sync User Profile
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    document.getElementById('userName').textContent = `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'Пользователь';
    document.getElementById('userAvatar').textContent = (u.first_name || '💰')[0].toUpperCase();
  }

  // Balance Visibility Toggle
  document.getElementById('toggleBalanceVisibility')?.addEventListener('click', () => {
    haptic('light');
    state.balanceVisible = !state.balanceVisible;
    renderDashboard();
    renderAccountsList();
    renderGoals();
  });

  // Refresh Button
  document.getElementById('refreshBtn')?.addEventListener('click', async () => {
    haptic('medium');
    await loadSummary();
    await loadCategories();
    showToast('Данные обновлены');
  });

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        closeModal(backdrop.id);
      }
    });
  });

  // Load initial data
  await loadUserProfiles();
  await loadSummary();
  await loadCategories();
});

// ==================== PROFILES MANAGEMENT ====================

async function loadUserProfiles() {
  try {
    const data = await apiFetch('/api/users');
    const select = document.getElementById('userProfileSelect');
    if (!select) return;

    select.innerHTML = '';
    const currentActive = data.current_user_id;

    data.users.forEach((u) => {
      const option = document.createElement('option');
      option.value = u.id;
      option.textContent = u.name || `Профиль #${u.id}`;
      if (String(u.id) === String(currentActive)) {
        option.selected = true;
      }
      select.appendChild(option);
    });

    if (!localStorage.getItem('activeProfileId') && currentActive) {
      localStorage.setItem('activeProfileId', currentActive);
    }
  } catch (err) {
    console.warn('Could not load user profiles:', err);
  }
}

async function switchUserProfile(profileId) {
  if (!profileId) return;
  haptic('medium');
  localStorage.setItem('activeProfileId', profileId);
  showToast('Переключение профиля...', 'success');
  await loadSummary();
  await loadCategories();
}

async function submitNewProfile(e) {
  e.preventDefault();
  const input = document.getElementById('newProfileName');
  const name = input?.value?.trim();
  if (!name) return;

  try {
    haptic('light');
    const newUser = await apiFetch('/api/users/create', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });

    closeModal('modalNewProfile');
    if (input) input.value = '';
    showToast(`Профиль "${newUser.name}" создан!`, 'success');
    
    // Switch to new profile
    await switchUserProfile(newUser.id);
    await loadUserProfiles();
  } catch (err) {
    showToast(err.message || 'Ошибка создания профиля', 'error');
  }
}
