/**
 * Hisoblash Telegram Mini App - Client Logic
 */

// Initialize Telegram WebApp SDK & Theme Detection
const tg = window.Telegram?.WebApp;
if (tg) {
  try {
    tg.ready();
    tg.expand();
    if (typeof tg.disableVerticalSwipes === 'function') {
      tg.disableVerticalSwipes();
    }
    tg.onEvent?.('fullscreen_changed', updateFullscreenBtnState);
    tg.onEvent?.('fullscreen_failed', updateFullscreenBtnState);
  } catch (e) {
    console.debug('Telegram WebApp features init error:', e);
  }

  const isLight = tg.colorScheme === 'light' || isLightBg(tg.themeParams?.bg_color);
  if (isLight) {
    document.body.classList.add('light-theme');
  }
}

document.addEventListener('fullscreenchange', updateFullscreenBtnState);
window.addEventListener('resize', updateFullscreenBtnState);

function isMobileDevice() {
  if (tg?.platform) {
    const p = tg.platform.toLowerCase();
    if (['android', 'ios', 'mobile'].includes(p)) return true;
    if (['tdesktop', 'macos', 'web', 'weba', 'webk'].includes(p)) return false;
  }
  return window.innerWidth <= 768 || /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

function toggleFullscreenMode() {
  haptic('light');
  if (tg) {
    if (tg.isFullscreen) {
      if (typeof tg.exitFullscreen === 'function') {
        tg.exitFullscreen();
      }
    } else {
      if (typeof tg.requestFullscreen === 'function') {
        tg.requestFullscreen();
      } else if (typeof tg.expand === 'function') {
        tg.expand();
      }
    }
  } else {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  }
  setTimeout(updateFullscreenBtnState, 150);
}

function updateFullscreenBtnState() {
  const btn = document.getElementById('toggleFullscreenBtn');
  if (!btn) return;

  // On Mobile (phones), hide the windowed/fullscreen button completely
  if (isMobileDevice()) {
    btn.style.display = 'none';
    return;
  }

  // On Desktop / Laptop / PC, display the toggle button
  btn.style.display = 'flex';
  const isFull = (tg && tg.isFullscreen) || !!document.fullscreenElement;
  
  if (isFull) {
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path></svg>`;
    btn.title = 'Обычный оконный режим';
  } else {
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>`;
    btn.title = 'Полноэкранный режим';
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

// ==================== NOTIFICATIONS LAYER ====================

state.notifications = JSON.parse(localStorage.getItem('hisob_notifications') || '[]');

function saveNotifications() {
  try {
    localStorage.setItem('hisob_notifications', JSON.stringify(state.notifications));
  } catch (e) {}
}

function updateNotificationBadge() {
  const dot = document.getElementById('notifBadgeDot');
  if (!dot) return;
  const hasUnread = state.notifications.some(n => !n.isRead);
  dot.classList.toggle('active', hasUnread);
}

function addNotification({ title, message, type = 'info', isRead = false }) {
  const notif = {
    id: Date.now() + Math.random(),
    title: title || (type === 'error' ? 'Ошибка' : type === 'success' ? 'Успешно' : 'Информация'),
    message: message || '',
    type: type,
    time: new Date().toISOString(),
    isRead: isRead
  };
  state.notifications.unshift(notif);
  if (state.notifications.length > 50) state.notifications.pop();
  saveNotifications();
  updateNotificationBadge();
  if (document.getElementById('tab-notifications')?.classList.contains('active')) {
    renderNotifications();
  }
}

function showToast(message, type = 'success', title = null) {
  // Silent notification - lights up the red dot on the bell icon in bottom menu!
  addNotification({
    title: title,
    message: message,
    type: type,
    isRead: false
  });
}

function renderNotifications() {
  const container = document.getElementById('notificationsList');
  if (!container) return;

  // Mark all as read
  state.notifications.forEach(n => n.isRead = true);
  saveNotifications();
  updateNotificationBadge();

  if (!state.notifications.length) {
    container.innerHTML = '<div class="empty-state">Нет новых уведомлений</div>';
    return;
  }

  container.innerHTML = state.notifications.map(n => {
    let iconSvg = '';
    if (n.type === 'error') {
      iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    } else if (n.type === 'success') {
      iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else if (n.type === 'warning') {
      iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
    } else {
      iconSvg = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    return `
      <div class="notif-item">
        <div class="notif-icon-box ${n.type}">
          ${iconSvg}
        </div>
        <div class="notif-content">
          <div class="notif-title">${n.title}</div>
          <div class="notif-msg">${n.message}</div>
          <div class="notif-time">${formatDate(n.time)}</div>
        </div>
      </div>
    `;
  }).join('');
}

function clearAllNotifications() {
  haptic('medium');
  state.notifications = [];
  saveNotifications();
  updateNotificationBadge();
  renderNotifications();
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

const SVG_ICONS = {
  // Accounts
  card: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></svg>`,
  cash: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="6" width="20" height="12" rx="2"></rect><circle cx="12" cy="12" r="3"></circle><path d="M6 12h.01M18 12h.01"></path></svg>`,
  bank: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M3 21h18M3 10h18M5 10v11M9 10v11M15 10v11M19 10v11M12 3l9 7H3l9-7z"></path></svg>`,
  crypto: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="9"></circle><path d="M12 6v12M9 9h6M9 15h6"></path></svg>`,
  
  // Actions & General
  income: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`,
  expense: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M12 5v14M5 12l7 7 7-7"/></svg>`,
  transfer: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M17 1 21 5 17 9"></path><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><path d="M7 23 3 19 7 15"></path><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>`,
  target: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
  debt: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
  user: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,

  // Categories
  work: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
  design: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"></circle><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"></circle><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"></circle><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"></circle><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"></path></svg>`,
  dev: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
  sales: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>`,
  gift: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><polyline points="20 12 20 22 4 22 4 12"></polyline><rect x="2" y="7" width="20" height="5"></rect><line x1="12" y1="22" x2="12" y2="7"></line><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"></path><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"></path></svg>`,
  food: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>`,
  transport: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>`,
  clothes: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"></path></svg>`,
  tech: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>`,
  games: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><line x1="6" y1="12" x2="10" y2="12"></line><line x1="8" y1="10" x2="8" y2="14"></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line x1="18" y1="11" x2="18.01" y2="11"></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg>`,
  study: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`,
  home: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`,
  mobile: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>`,
  other: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>`,
};

function getCategoryIcon(nameOrKey) {
  if (!nameOrKey) return SVG_ICONS.other;
  const str = nameOrKey.toString().toLowerCase();

  if (str.includes('работ') || str.includes('work') || str.includes('job') || str.includes('зарплат') || str.includes('💼')) return SVG_ICONS.work;
  if (str.includes('дизайн') || str.includes('design') || str.includes('art') || str.includes('🎨')) return SVG_ICONS.design;
  if (str.includes('програм') || str.includes('dev') || str.includes('code') || str.includes('it') || str.includes('💻')) return SVG_ICONS.dev;
  if (str.includes('продаж') || str.includes('sale') || str.includes('бизнес') || str.includes('🛒')) return SVG_ICONS.sales;
  if (str.includes('подар') || str.includes('gift') || str.includes('🎁')) return SVG_ICONS.gift;
  if (str.includes('ед') || str.includes('продукт') || str.includes('food') || str.includes('кафе') || str.includes('ресторан') || str.includes('🍔')) return SVG_ICONS.food;
  if (str.includes('транспорт') || str.includes('такси') || str.includes('car') || str.includes('авто') || str.includes('бензин') || str.includes('🚕')) return SVG_ICONS.transport;
  if (str.includes('одежд') || str.includes('clothes') || str.includes('вещи') || str.includes('обувь') || str.includes('👕')) return SVG_ICONS.clothes;
  if (str.includes('техник') || str.includes('tech') || str.includes('гаджет') || str.includes('ноутбук') || str.includes('телефон')) return SVG_ICONS.tech;
  if (str.includes('игр') || str.includes('game') || str.includes('развлечен') || str.includes('кино') || str.includes('🎮')) return SVG_ICONS.games;
  if (str.includes('учеб') || str.includes('study') || str.includes('курс') || str.includes('книг') || str.includes('образован') || str.includes('📚')) return SVG_ICONS.study;
  if (str.includes('дом') || str.includes('home') || str.includes('аренд') || str.includes('квартир') || str.includes('коммунал') || str.includes('🏠')) return SVG_ICONS.home;
  if (str.includes('связ') || str.includes('интернет') || str.includes('mobile') || str.includes('phone') || str.includes('📱')) return SVG_ICONS.mobile;
  if (str.includes('карт') || str.includes('card') || str.includes('💳')) return SVG_ICONS.card;
  if (str.includes('налич') || str.includes('cash') || str.includes('💵')) return SVG_ICONS.cash;
  if (str.includes('банк') || str.includes('bank') || str.includes('🏦')) return SVG_ICONS.bank;
  if (str.includes('крипт') || str.includes('валют') || str.includes('coin') || str.includes('🪙')) return SVG_ICONS.crypto;

  return SVG_ICONS[nameOrKey] || SVG_ICONS.other;
}

function getIconHTML(iconStr) {
  return getCategoryIcon(iconStr);
}

function createTxItemHTML(tx, allowDelete = false) {
  let sign = '';
  let colorClass = 'expense';
  let iconKey = tx.category_name || tx.category_icon || 'expense';

  if (tx.type === 'income') {
    sign = '+';
    colorClass = 'income';
  } else if (tx.type === 'expense') {
    sign = '-';
    colorClass = 'expense';
  } else if (tx.type === 'transfer') {
    sign = '';
    colorClass = 'transfer';
    iconKey = 'transfer';
  } else if (tx.type === 'saving') {
    sign = '';
    colorClass = 'saving';
    iconKey = 'target';
  } else if (tx.type === 'saving_withdraw') {
    sign = '+';
    colorClass = 'income';
    iconKey = 'target';
  } else if (tx.type === 'debt_given' || tx.type === 'debt_taken' || tx.type === 'debt_return') {
    sign = '';
    colorClass = 'debt';
    iconKey = 'debt';
  }

  const title = tx.category_name || tx.description || 'Операция';
  const iconHTML = getCategoryIcon(iconKey);
  const meta = `${tx.account_name || 'Счет'} • ${formatDate(tx.created_at)}`;

  const deleteBtn = allowDelete
    ? `<button class="tx-del-btn" onclick="deleteTransaction(${tx.id})">Удалить</button>`
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

function renderAccountsList() {
  const scrollContainer = document.getElementById('accountsList');
  const allGrid = document.getElementById('allAccountsList');
  if (!state.accounts) return;

  const html = state.accounts.map(acc => `
    <div class="account-card-item">
      <div class="acc-icon-badge">${getIconHTML(acc.icon || 'card')}</div>
      <div class="acc-info">
        <div class="acc-name">${acc.name}</div>
        <div class="acc-balance">${formatMoney(acc.balance)}</div>
      </div>
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
        <div class="goal-name">
          ${g.name}
          ${g.is_funded ? '<span class="status-badge green" style="font-size: 10px; padding: 2px 6px; margin-left: 6px;">Достигнуто</span>' : ''}
        </div>
        <div>
          <span class="goal-target">${g.pct}% (${formatMoney(g.target_amount)})</span>
          <button class="goal-delete-btn" onclick="deleteGoal(${g.id})" title="Удалить">✕</button>
        </div>
      </div>
      ${g.target_date ? `<div style="font-size:11px; color:var(--text-muted); margin-top:2px; margin-bottom:6px;">Дедлайн: ${formatDate(g.target_date)}</div>` : ''}
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
      breakdownContainer.innerHTML = '';
      return;
    }

    breakdownContainer.innerHTML = a.goals.map(g => {
      const dateInfo = g.target_date ? `дедлайн: ${formatDate(g.target_date)} (${g.months_left} мес)` : 'без даты (расчет на 12 мес)';
      return `
        <div class="load-goal-item">
          <div>
            <div class="load-goal-name">${g.name}</div>
            <div class="load-goal-details" style="text-align: left; font-size: 11px; color: var(--text-muted);">${dateInfo}</div>
          </div>
          <div class="load-goal-details">
            <div class="load-goal-req">${formatMoney(g.required_monthly)}/мес</div>
            <div style="font-size: 11px; color: var(--text-muted);">(${formatMoney(g.required_15day)}/15дн)</div>
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
        <div class="person">
          <svg viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none" style="vertical-align: text-bottom; margin-right: 4px; color: var(--text-muted);">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          ${d.person_name}
        </div>
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

// ==================== NUMBER FORMATTING & INPUT MASKS ====================

function formatThousands(valStr) {
  if (valStr === undefined || valStr === null || valStr === '') return '';
  const clean = valStr.toString().replace(/[^\d.,]/g, '').replace(',', '.');
  const parts = clean.split('.');
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  if (parts.length > 1) {
    return `${integerPart}.${parts[1].slice(0, 2)}`;
  }
  return integerPart;
}

function parseAmountInput(inputOrValue) {
  if (typeof inputOrValue === 'number') return isNaN(inputOrValue) ? 0 : inputOrValue;
  let val = typeof inputOrValue === 'string' ? inputOrValue : (inputOrValue?.value || '0');
  val = val.toString().replace(/\s+/g, '').replace(',', '.');
  const num = parseFloat(val);
  return isNaN(num) ? 0 : num;
}

function updateHeroDisplay(input) {
  if (!input) return;
  const displayId = input.dataset.displayId;
  if (!displayId) return;
  const displayEl = document.getElementById(displayId);
  if (!displayEl) return;

  const rawNum = parseAmountInput(input.value);
  const formatted = rawNum > 0 ? formatThousands(rawNum) : '0';
  displayEl.innerHTML = `${formatted} <span class="hero-amount-currency">сум</span>`;
}

function formatNumberOnInput(e) {
  const input = e.target;
  const formatted = formatThousands(input.value);
  input.value = formatted;
  updateHeroDisplay(input);
}

function initAmountInputListeners() {
  document.querySelectorAll('.amount-input').forEach(input => {
    input.removeEventListener('input', formatNumberOnInput);
    input.removeEventListener('keyup', formatNumberOnInput);
    input.addEventListener('input', formatNumberOnInput);
    input.addEventListener('keyup', formatNumberOnInput);
    updateHeroDisplay(input);
  });
}

function addAmount(inputId, delta) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    const current = parseAmountInput(input.value);
    const total = current + delta;
    input.value = formatThousands(total);
    updateHeroDisplay(input);
  }
}

function clearAmount(inputId) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    input.value = '';
    updateHeroDisplay(input);
  }
}

// ==================== VISUAL CHIPS & PILLS POPULATION ====================

const DEFAULT_FALLBACK_INCOME = [
  { id: '1', name: 'Работа', iconKey: 'work' },
  { id: '2', name: 'Дизайн', iconKey: 'design' },
  { id: '3', name: 'Программирование', iconKey: 'dev' },
  { id: '4', name: 'Продажи', iconKey: 'sales' },
  { id: '5', name: 'Подарок', iconKey: 'gift' },
  { id: '6', name: 'Другое', iconKey: 'other' },
];

const DEFAULT_FALLBACK_EXPENSE = [
  { id: '1', name: 'Еда', iconKey: 'food' },
  { id: '2', name: 'Транспорт', iconKey: 'transport' },
  { id: '3', name: 'Одежда', iconKey: 'clothes' },
  { id: '4', name: 'Техника', iconKey: 'tech' },
  { id: '5', name: 'Игры', iconKey: 'games' },
  { id: '6', name: 'Учёба', iconKey: 'study' },
  { id: '7', name: 'Дом', iconKey: 'home' },
  { id: '8', name: 'Связь', iconKey: 'mobile' },
  { id: '9', name: 'Подарки', iconKey: 'gift' },
  { id: '10', name: 'Другое', iconKey: 'other' },
];

function selectCategoryChip(containerId, hiddenInputId, catId) {
  haptic('light');
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  hiddenInput.value = catId;
  container.querySelectorAll('.cat-chip').forEach(chip => {
    chip.classList.toggle('selected', String(chip.dataset.id) === String(catId));
  });
}

function selectAccountPill(containerId, hiddenInputId, accId) {
  haptic('light');
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  hiddenInput.value = accId;
  container.querySelectorAll('.acc-pill').forEach(pill => {
    pill.classList.toggle('selected', String(pill.dataset.id) === String(accId));
  });
}

function renderCategoryChips(containerId, hiddenInputId, categories, defaultSelectedId) {
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  const currentVal = hiddenInput.value || defaultSelectedId || (categories[0] ? categories[0].id : '');
  hiddenInput.value = currentVal;

  container.innerHTML = categories.map(c => {
    const isSelected = String(c.id) === String(currentVal);
    const iconSvg = getCategoryIcon(c.icon || c.name || c.iconKey);
    return `
      <div class="cat-chip ${isSelected ? 'selected' : ''}" data-id="${c.id}" onclick="selectCategoryChip('${containerId}', '${hiddenInputId}', '${c.id}')">
        <span class="cat-chip-icon">${iconSvg}</span>
        <span>${c.name}</span>
      </div>
    `;
  }).join('');
}

function renderAccountPills(containerId, hiddenInputId, accounts, defaultSelectedId) {
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  const regularAccs = (accounts || []).filter(a => !a.is_savings);
  const activeList = regularAccs.length ? regularAccs : [
    { id: 1, name: 'Карта', icon: 'card', balance: 0 },
    { id: 2, name: 'Наличные', icon: 'cash', balance: 0 }
  ];

  const currentVal = hiddenInput.value || defaultSelectedId || activeList[0].id;
  hiddenInput.value = currentVal;

  container.innerHTML = activeList.map(a => {
    const isSelected = String(a.id) === String(currentVal);
    const iconSvg = getCategoryIcon(a.icon || a.name || 'card');
    return `
      <div class="acc-pill ${isSelected ? 'selected' : ''}" data-id="${a.id}" onclick="selectAccountPill('${containerId}', '${hiddenInputId}', '${a.id}')">
        <span class="acc-pill-icon">${iconSvg}</span>
        <div>
          <div class="acc-pill-name">${a.name}</div>
          <div class="acc-pill-balance">${formatMoney(a.balance)}</div>
        </div>
      </div>
    `;
  }).join('');
}

function populateAccountDropdowns() {
  const accs = state.accounts || [];
  renderAccountPills('incomeAccountPills', 'incomeAccount', accs);
  renderAccountPills('expenseAccountPills', 'expenseAccount', accs);
  renderAccountPills('transferFromAccountPills', 'transferFromAccount', accs);
  renderAccountPills('transferToAccountPills', 'transferToAccount', accs);
  renderAccountPills('saveDepositSourcePills', 'saveDepositSource', accs);
  renderAccountPills('saveWithdrawDestPills', 'saveWithdrawDest', accs);

  // Standard select fallback for debt
  const regularAccs = accs.filter(a => !a.is_savings);
  const optionsHtml = regularAccs.length
    ? regularAccs.map(a => `<option value="${a.id}">${a.name} (${formatMoney(a.balance)})</option>`).join('')
    : '<option value="1">Карта (0 сум)</option><option value="2">Наличные (0 сум)</option>';
  const debtAcc = document.getElementById('debtAccount');
  if (debtAcc) debtAcc.innerHTML = optionsHtml;
}

function populateCategoryDropdowns() {
  const expCats = (state.categories?.expense && state.categories.expense.length)
    ? state.categories.expense
    : DEFAULT_FALLBACK_EXPENSE;

  const incCats = (state.categories?.income && state.categories.income.length)
    ? state.categories.income
    : DEFAULT_FALLBACK_INCOME;

  renderCategoryChips('expenseCategoryChips', 'expenseCategory', expCats);
  renderCategoryChips('incomeCategoryChips', 'incomeCategory', incCats);
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

  if (tabId === 'tab-stats') loadStats();
  if (tabId === 'tab-debts') loadDebts();
  if (tabId === 'tab-history') loadHistory(0);
  if (tabId === 'tab-notifications') renderNotifications();
}

function openModal(modalId) {
  haptic('medium');
  populateAccountDropdowns();
  populateCategoryDropdowns();
  initAmountInputListeners();
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
    const current = parseAmountInput(input.value);
    const total = current + delta;
    input.value = formatThousands(total);
    updateHeroDisplay(input);
  }
}

function clearAmount(inputId) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    input.value = '';
    updateHeroDisplay(input);
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
    const amount = parseAmountInput(document.getElementById('incomeAmount'));
    if (!amount || amount <= 0) {
      showToast('Введите сумму дохода', 'error');
      return;
    }
    let account_id = document.getElementById('incomeAccount')?.value;
    if (!account_id && state.accounts && state.accounts.length) {
      const reg = state.accounts.find(a => !a.is_savings) || state.accounts[0];
      if (reg) account_id = reg.id;
    }
    if (!account_id) {
      showToast('Выберите счёт', 'error');
      return;
    }

    const rawCat = document.getElementById('incomeCategory')?.value;
    const category_id = rawCat && !isNaN(parseInt(rawCat)) ? parseInt(rawCat) : null;
    const description = document.getElementById('incomeDesc')?.value;

    try {
      await apiFetch('/api/transactions/income', {
        method: 'POST',
        body: JSON.stringify({ amount, account_id, category_id, description }),
      });
      closeModal('modalIncome');
      document.getElementById('formIncome').reset();
      clearAmount('incomeAmount');
      showToast('Доход успешно добавлен!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitExpense(e) {
  await handleFormSubmit(e, async () => {
    const amount = parseAmountInput(document.getElementById('expenseAmount'));
    if (!amount || amount <= 0) {
      showToast('Введите сумму расхода', 'error');
      return;
    }
    let account_id = document.getElementById('expenseAccount')?.value;
    if (!account_id && state.accounts && state.accounts.length) {
      const reg = state.accounts.find(a => !a.is_savings) || state.accounts[0];
      if (reg) account_id = reg.id;
    }
    if (!account_id) {
      showToast('Выберите счёт', 'error');
      return;
    }

    let rawCat = document.getElementById('expenseCategory')?.value;
    let category_id = rawCat && !isNaN(parseInt(rawCat)) ? parseInt(rawCat) : null;
    if (!category_id && state.categories?.expense && state.categories.expense.length) {
      category_id = state.categories.expense[0].id;
    }

    const description = document.getElementById('expenseDesc')?.value;

    try {
      await apiFetch('/api/transactions/expense', {
        method: 'POST',
        body: JSON.stringify({ amount, account_id, category_id, description }),
      });
      closeModal('modalExpense');
      document.getElementById('formExpense').reset();
      clearAmount('expenseAmount');
      showToast('Расход записан!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitTransfer(e) {
  await handleFormSubmit(e, async () => {
    const amount = parseAmountInput(document.getElementById('transferAmount'));
    if (!amount || amount <= 0) {
      showToast('Введите сумму перевода', 'error');
      return;
    }
    let from_account_id = document.getElementById('transferFromAccount')?.value;
    let to_account_id = document.getElementById('transferToAccount')?.value;
    const regularAccs = (state.accounts || []).filter(a => !a.is_savings);
    if (!from_account_id && regularAccs.length > 0) from_account_id = regularAccs[0].id;
    if (!to_account_id && regularAccs.length > 1) to_account_id = regularAccs[1].id;
    else if (!to_account_id && regularAccs.length > 0) to_account_id = regularAccs[0].id;

    if (!from_account_id || !to_account_id) {
      showToast('Выберите счёта для перевода', 'error');
      return;
    }

    try {
      await apiFetch('/api/transactions/transfer', {
        method: 'POST',
        body: JSON.stringify({ amount, from_account_id, to_account_id }),
      });
      closeModal('modalTransfer');
      document.getElementById('formTransfer').reset();
      clearAmount('transferAmount');
      showToast('Перевод успешно выполнен!');
      await loadSummary();
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}

async function submitSaveDeposit(e) {
  await handleFormSubmit(e, async () => {
    const amount = parseAmountInput(document.getElementById('saveDepositAmount'));
    if (!amount || amount <= 0) {
      showToast('Введите сумму для накоплений', 'error');
      return;
    }
    let source_account_id = document.getElementById('saveDepositSource')?.value;
    if (!source_account_id && state.accounts && state.accounts.length) {
      const reg = state.accounts.find(a => !a.is_savings) || state.accounts[0];
      if (reg) source_account_id = reg.id;
    }

    const description = document.getElementById('saveDepositDesc')?.value;

    try {
      const res = await apiFetch('/api/savings/deposit', {
        method: 'POST',
        body: JSON.stringify({ amount, source_account_id, description }),
      });
      closeModal('modalSaveDeposit');
      document.getElementById('formSaveDeposit').reset();
      clearAmount('saveDepositAmount');
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
    const amount = parseAmountInput(document.getElementById('saveWithdrawAmount'));
    if (!amount || amount <= 0) {
      showToast('Введите сумму снятия', 'error');
      return;
    }
    let dest_account_id = document.getElementById('saveWithdrawDest')?.value;
    if (!dest_account_id && state.accounts && state.accounts.length) {
      const reg = state.accounts.find(a => !a.is_savings) || state.accounts[0];
      if (reg) dest_account_id = reg.id;
    }

    const description = document.getElementById('saveWithdrawDesc')?.value;

    try {
      await apiFetch('/api/savings/withdraw', {
        method: 'POST',
        body: JSON.stringify({ amount, dest_account_id, description }),
      });
      closeModal('modalSaveWithdraw');
      document.getElementById('formSaveWithdraw').reset();
      clearAmount('saveWithdrawAmount');
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
    const initial_balance = parseAmountInput(document.getElementById('newAccountBalance'));

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
    const target_amount = parseAmountInput(document.getElementById('newGoalTarget'));
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
  const currentVal = state.summary?.user?.monthly_salary;
  if (currentVal) {
    document.getElementById('salaryMonthlyInput').value = formatThousands(currentVal);
  }
  openModal('modalSalary');
}

async function submitSalaryForm(e) {
  await handleFormSubmit(e, async () => {
    const monthly_salary = parseAmountInput(document.getElementById('salaryMonthlyInput'));
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

function deleteGoal(goalId) {
  showConfirmDialog({
    title: 'Удалить цель?',
    message: 'Цель накопления будет удалена. Накопленные средства останутся на счете.',
    btnText: 'Удалить',
    isDanger: true,
    onConfirm: async () => {
      try {
        await apiFetch(`/api/savings/goals/${goalId}`, { method: 'DELETE' });
        showToast('Цель удалена', 'info');
        await loadSummary();
      } catch (err) {
        showToast(err.message || 'Ошибка удаления цели', 'error');
      }
    }
  });
}

function deleteTransaction(txId) {
  showConfirmDialog({
    title: 'Удалить операцию?',
    message: 'Операция будет удалена, а баланс счёта скорректирован.',
    btnText: 'Удалить',
    isDanger: true,
    onConfirm: async () => {
      try {
        await apiFetch(`/api/transactions/${txId}`, { method: 'DELETE' });
        showToast('Операция отменена', 'info');
        await loadSummary();
        await loadHistory(state.historyPage);
      } catch (err) {
        showToast(err.message || 'Ошибка удаления операции', 'error');
      }
    }
  });
}

// ==================== DEBT MODAL DISPATCHER ====================

function openGiveDebtModal() {
  document.getElementById('debtModalTitle').textContent = 'Дать в долг';
  document.getElementById('debtFormMode').value = 'give';
  document.getElementById('debtPersonGroup').style.display = 'block';
  document.getElementById('debtAccountLabel').textContent = 'Списать со счёта';
  document.getElementById('debtSubmitBtn').textContent = 'Дать в долг';
  document.getElementById('formDebt').reset();
  openModal('modalDebt');
}

function openTakeDebtModal() {
  document.getElementById('debtModalTitle').textContent = 'Взять в долг';
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
  document.getElementById('debtAmount').value = formatThousands(remAmount);
  document.getElementById('debtAccountLabel').textContent = 'Счёт для взаиморасчёта';
  document.getElementById('debtSubmitBtn').textContent = 'Подтвердить возврат';
  openModal('modalDebt');
}

async function submitDebtForm(e) {
  await handleFormSubmit(e, async () => {
    const mode = document.getElementById('debtFormMode').value;
    const amount = parseAmountInput(document.getElementById('debtAmount'));
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

  // Initialize input formatting masks & modals
  initAmountInputListeners();
  initConfirmModalListeners();

  // Initial badge and fullscreen state update
  updateNotificationBadge();
  updateFullscreenBtnState();

  // Load initial data
  await loadUserProfiles();
  await loadSummary();
  await loadCategories();
});

// ==================== PROFILES MANAGEMENT (MAX 3) ====================

let userProfilesList = [];
let confirmCallback = null;

function showConfirmDialog({ title = 'Подтверждение', message = 'Вы уверены?', btnText = 'Подтвердить', isDanger = true, onConfirm }) {
  haptic('warning');
  const titleEl = document.getElementById('confirmTitle');
  const msgEl = document.getElementById('confirmMessage');
  const acceptBtn = document.getElementById('confirmAcceptBtn');
  
  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;
  if (acceptBtn) {
    acceptBtn.textContent = btnText;
    acceptBtn.className = `confirm-btn ${isDanger ? 'confirm-btn-danger' : 'confirm-btn-accent'}`;
  }
  confirmCallback = onConfirm;
  openModal('modalConfirm');
}

function initConfirmModalListeners() {
  document.getElementById('confirmAcceptBtn')?.addEventListener('click', async () => {
    haptic('medium');
    closeModal('modalConfirm');
    if (typeof confirmCallback === 'function') {
      const cb = confirmCallback;
      confirmCallback = null;
      await cb();
    }
  });
}

async function loadUserProfiles() {
  try {
    const data = await apiFetch('/api/users');
    userProfilesList = data.users || [];
    const currentActive = data.current_user_id;

    if (!localStorage.getItem('activeProfileId') && currentActive) {
      localStorage.setItem('activeProfileId', currentActive);
    }
    
    updateProfilePillUI();
  } catch (err) {
    console.warn('Could not load user profiles:', err);
  }
}

function updateProfilePillUI() {
  const nameEl = document.getElementById('currentProfileName');
  if (!nameEl) return;

  const activeId = localStorage.getItem('activeProfileId');
  const activeProf = userProfilesList.find(u => String(u.id) === String(activeId)) || userProfilesList[0];

  if (activeProf) {
    nameEl.textContent = activeProf.name || 'Основной';
  } else {
    nameEl.textContent = 'Основной';
  }
}

function openProfilePicker() {
  haptic('medium');
  const listContainer = document.getElementById('profilePickerList');
  const addBox = document.getElementById('profilePickerAddBox');
  if (!listContainer) return;

  const activeId = localStorage.getItem('activeProfileId') || (userProfilesList[0]?.id);

  listContainer.innerHTML = userProfilesList.map((u, idx) => {
    const isActive = String(u.id) === String(activeId);
    const displayName = u.name || (idx === 0 ? 'Основной' : `Профиль ${idx + 1}`);

    const editBtn = `
      <button class="profile-action-icon" onclick="openRenameModal(event, ${u.id}, '${displayName.replace(/'/g, "\\'")}')" title="Переименовать">
        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
      </button>
    `;

    const deleteBtn = idx > 0 ? `
      <button class="profile-action-icon profile-action-delete" onclick="handleDeleteProfileClick(event, ${u.id}, '${displayName.replace(/'/g, "\\'")}')" title="Удалить профиль">
        <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none">
          <polyline points="3 6 5 6 21 6"></polyline>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          <line x1="10" y1="11" x2="10" y2="17"></line>
          <line x1="14" y1="11" x2="14" y2="17"></line>
        </svg>
      </button>
    ` : '';

    return `
      <div class="profile-item-row ${isActive ? 'active' : ''}" onclick="selectProfileAndClose(${u.id})">
        <div class="profile-item-left">
          <div class="profile-item-badge">${idx + 1}</div>
          <div class="profile-item-name">${displayName}</div>
        </div>
        <div class="profile-item-actions">
          ${editBtn}
          ${deleteBtn}
        </div>
      </div>
    `;
  }).join('');

  if (addBox) {
    if (userProfilesList.length < 3) {
      addBox.innerHTML = `
        <button class="btn-submit btn-accent btn-add-profile" onclick="openNewProfileModal()" title="Добавить профиль">
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2.5" fill="none">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      `;
    } else {
      addBox.innerHTML = '';
    }
  }

  openModal('modalProfilePicker');
}

function openRenameModal(e, userId, currentName) {
  e.stopPropagation();
  haptic('light');
  document.getElementById('renameProfileUserId').value = userId;
  const input = document.getElementById('renameProfileNameInput');
  if (input) {
    input.value = currentName;
  }
  openModal('modalRenameProfile');
}

async function submitRenameProfile(e) {
  e.preventDefault();
  const userId = document.getElementById('renameProfileUserId')?.value;
  const input = document.getElementById('renameProfileNameInput');
  const newName = input?.value?.trim();
  if (!userId || !newName) return;

  try {
    haptic('medium');
    await apiFetch('/api/users/rename', {
      method: 'POST',
      body: JSON.stringify({ user_id: Number(userId), name: newName })
    });
    closeModal('modalRenameProfile');
    showToast(`Имя изменено на "${newName}"`, 'success');
    await loadUserProfiles();
    openProfilePicker();
  } catch (err) {
    showToast(err.message || 'Ошибка обновления названия', 'error');
  }
}

function handleDeleteProfileClick(e, userId, name) {
  e.stopPropagation();
  showConfirmDialog({
    title: `Удаление профиля «${name}»`,
    message: 'Все связанные данные и счета будут удалены без возможности восстановления.',
    btnText: 'Удалить',
    isDanger: true,
    onConfirm: async () => {
      try {
        await apiFetch('/api/users/delete', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId })
        });
        showToast(`Профиль «${name}» удален`, 'info');
        
        // If active was deleted, fallback to first profile
        const activeId = localStorage.getItem('activeProfileId');
        if (String(activeId) === String(userId)) {
          localStorage.removeItem('activeProfileId');
        }

        await loadUserProfiles();
        if (userProfilesList.length) {
          await switchUserProfile(userProfilesList[0].id);
        }
        openProfilePicker();
      } catch (err) {
        showToast(err.message || 'Ошибка удаления профиля', 'error');
      }
    }
  });
}

async function selectProfileAndClose(profileId) {
  closeModal('modalProfilePicker');
  await switchUserProfile(profileId);
}

function openNewProfileModal() {
  closeModal('modalProfilePicker');
  openModal('modalNewProfile');
}

async function switchUserProfile(profileId) {
  if (!profileId) return;
  haptic('medium');
  localStorage.setItem('activeProfileId', profileId);
  updateProfilePillUI();
  showToast('Переключение профиля...', 'info');
  await loadSummary();
  await loadCategories();
}

async function submitNewProfile(e) {
  e.preventDefault();
  const input = document.getElementById('newProfileName');
  const name = input?.value?.trim();
  if (!name) return;

  if (userProfilesList.length >= 3) {
    showToast('Достигнут максимум профилей (3/3)', 'error');
    return;
  }

  try {
    haptic('light');
    const newUser = await apiFetch('/api/users/create', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });

    closeModal('modalNewProfile');
    if (input) input.value = '';
    showToast(`Профиль "${newUser.name}" создан!`, 'success');
    
    // Reload user profiles and switch
    await loadUserProfiles();
    await switchUserProfile(newUser.id);
  } catch (err) {
    showToast(err.message || 'Ошибка создания профиля', 'error');
  }
}
