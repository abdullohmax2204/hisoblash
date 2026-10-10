/**
 * Main application orchestrator and entry point.
 * Integrates modular domain views, state management, REST client, and Telegram WebApp environment.
 */

import { state, tg } from './state.js';
import { fetchRates } from './api.js';
import {
  haptic,
  toggleFullscreenMode,
  updateFullscreenBtnState,
  setDisplayCurrency,
  updateCurrencyPillsUI,
  initAmountInputListeners,
} from './utils.js';
import {
  showToast,
  updateNotificationBadge,
  renderNotifications,
  clearAllNotifications,
} from './toast.js';
import {
  openModal,
  closeModal,
  addAmount,
  clearAmount,
  selectCategoryChip,
  selectAccountPill,
  populateAccountDropdowns,
  populateCategoryDropdowns,
  initConfirmModalListeners,
  showConfirmDialog,
} from './components/modals.js';
import {
  renderDashboard,
  renderAccountsList,
  renderLoadAnalysis,
  createTxItemHTML,
  renderRecentTx,
} from './views/overview.js';
import { renderGoals, deleteGoal } from './views/accounts.js';
import { renderStats, changePeriod } from './views/stats.js';
import {
  loadDebts,
  renderDebtsList,
  switchDebtType,
  openGiveDebtModal,
  openTakeDebtModal,
  openReturnDebtModal,
} from './views/debts.js';
import { loadHistory, loadHistoryPage, deleteTransaction } from './views/history.js';
import { loadUserProfiles, updateProfilePillUI } from './views/profiles.js';
import {
  submitIncome,
  submitExpense,
  submitTransfer,
  submitSaveDeposit,
  submitSaveWithdraw,
  submitNewAccount,
  submitNewGoal,
  openSalaryModal,
  submitSalaryForm,
  submitDebtForm,
} from './forms.js';
import { fetchSummary, fetchLoadAnalysis, fetchCategories, fetchStats } from './api.js';

// ==================== DATA LOADERS ====================

export async function loadSummary() {
  try {
    const data = await fetchSummary();
    state.summary = data;
    state.accounts = data.regular_accounts || [];
    if (data.rates || data.exchange_rates) {
      state.exchangeRates = data.rates || data.exchange_rates;
    }
    renderDashboard();
    renderAccountsList();
    renderGoals();
    await loadLoadAnalysis();
  } catch (err) {
    console.error('Error loading summary:', err);
    showToast('Ошибка загрузки данных', 'error');
  }
}

export async function loadLoadAnalysis() {
  try {
    const analysis = await fetchLoadAnalysis();
    renderLoadAnalysis(analysis);
  } catch (err) {
    console.error('Error loading load analysis:', err);
  }
}

export async function loadCategories() {
  try {
    const data = await fetchCategories();
    state.categories = data;
    populateCategoryDropdowns();
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

export async function loadStatsData(period = state.statsPeriod) {
  try {
    state.statsPeriod = period;
    const data = await fetchStats(period);
    renderStats(data);
  } catch (err) {
    showToast('Ошибка загрузки аналитики', 'error');
  }
}

export async function onProfileSwitch() {
  await loadSummary();
  await loadCategories();
}

// ==================== TAB NAVIGATION ====================

export function switchTab(tabId) {
  haptic('light');
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const activeTab = document.getElementById(tabId);
  const activeNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);

  if (activeTab) activeTab.classList.add('active');
  if (activeNav) activeNav.classList.add('active');

  if (tabId === 'tab-stats') loadStatsData();
  if (tabId === 'tab-debts') loadDebts();
  if (tabId === 'tab-history') loadHistory(0);
  if (tabId === 'tab-notifications') renderNotifications();
}

// ==================== GLOBAL WINDOW BINDINGS ====================
// Attached to window to preserve 100% interoperability with HTML onclick / onsubmit attributes.

window.openModal = openModal;
window.closeModal = closeModal;
window.addAmount = addAmount;
window.clearAmount = clearAmount;
window.selectCategoryChip = selectCategoryChip;
window.selectAccountPill = selectAccountPill;
window.toggleFullscreenMode = toggleFullscreenMode;

window.setDisplayCurrency = (cur) => {
  setDisplayCurrency(cur, () => {
    renderDashboard();
    renderAccountsList();
    renderGoals();
  });
};

window.switchTab = switchTab;
window.changePeriod = (period, btn) => changePeriod(period, btn, loadStatsData);
window.clearAllNotifications = clearAllNotifications;

window.openGiveDebtModal = openGiveDebtModal;
window.openTakeDebtModal = openTakeDebtModal;
window.openReturnDebtModal = openReturnDebtModal;
window.switchDebtType = switchDebtType;
window.submitDebtForm = (e) => submitDebtForm(e, loadSummary, loadDebts);

window.loadHistoryPage = loadHistoryPage;
window.deleteTransaction = (txId) => deleteTransaction(txId, loadSummary);

window.deleteGoal = (id) => deleteGoal(id, loadSummary);
window.openSalaryModal = openSalaryModal;
window.submitSalaryForm = (e) => submitSalaryForm(e, loadSummary);

window.submitNewAccount = (e) => submitNewAccount(e, loadSummary);
window.submitNewGoal = (e) => submitNewGoal(e, loadSummary);
window.submitIncome = (e) => submitIncome(e, loadSummary);
window.submitExpense = (e) => submitExpense(e, loadSummary);
window.submitTransfer = (e) => submitTransfer(e, loadSummary);
window.submitSaveDeposit = (e) => submitSaveDeposit(e, loadSummary);
window.submitSaveWithdraw = (e) => submitSaveWithdraw(e, loadSummary);

// ==================== APP INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', async () => {
  if (tg) {
    try {
      tg.ready?.();
      tg.expand?.();
    } catch (e) {
      console.warn('Telegram WebApp init notice:', e);
    }
  }

  // Telegram User Avatar & Name
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    const avatarEl = document.getElementById('userAvatar');
    if (avatarEl) {
      if (u.photo_url) {
        avatarEl.innerHTML = `<img src="${u.photo_url}" class="avatar-photo" alt="Avatar" />`;
      } else {
        const initial = (u.first_name || 'U')[0].toUpperCase();
        avatarEl.textContent = initial;
      }
    }
  }

  // Balance Visibility Toggle
  document.getElementById('toggleBalanceVisibility')?.addEventListener('click', () => {
    haptic('light');
    state.balanceVisible = !state.balanceVisible;
    renderDashboard();
    renderAccountsList();
    renderGoals();
  });

  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        closeModal(backdrop.id);
      }
    });
  });

  // Bottom Navigation click handlers
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      if (tabId) switchTab(tabId);
    });
  });

  // Initialize input formatting masks & modals
  initAmountInputListeners();
  initConfirmModalListeners();

  // Initial badge, currency pills, and fullscreen state update
  updateNotificationBadge();
  updateFullscreenBtnState();
  updateCurrencyPillsUI();

  // Load initial exchange rates
  try {
    const ratesData = await fetchRates();
    if (ratesData) {
      state.exchangeRates = ratesData.rates || ratesData;
    }
  } catch (e) {
    console.warn('Rates fetch fallback:', e);
  }

  // Load initial domain data
  await loadUserProfiles();
  await loadSummary();
  await loadCategories();
});
