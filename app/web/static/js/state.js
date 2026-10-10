/**
 * Global reactive client state and Telegram SDK reference.
 */

export const tg = window.Telegram?.WebApp;

export const state = {
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
  displayCurrency: localStorage.getItem('hisob_display_currency') || 'UZS',
  notifications: JSON.parse(localStorage.getItem('hisob_notifications') || '[]'),
};

export const profilesState = {
  userProfilesList: [],
  confirmCallback: null,
};
