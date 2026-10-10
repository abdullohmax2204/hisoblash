/**
 * Modals, visual chips, account pills, and confirmation dialogs.
 */

import { state, profilesState } from '../state.js';
import { haptic, formatMoney, formatThousands, parseAmountInput, updateHeroDisplay, initAmountInputListeners } from '../utils.js';
import { getCategoryIcon } from '../icons.js';

export const DEFAULT_FALLBACK_INCOME = [
  { id: '1', name: 'Работа', iconKey: 'work' },
  { id: '2', name: 'Дизайн', iconKey: 'design' },
  { id: '3', name: 'Программирование', iconKey: 'dev' },
  { id: '4', name: 'Продажи', iconKey: 'sales' },
  { id: '5', name: 'Подарок', iconKey: 'gift' },
  { id: '6', name: 'Другое', iconKey: 'other' },
];

export const DEFAULT_FALLBACK_EXPENSE = [
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

export function selectCategoryChip(containerId, hiddenInputId, catId) {
  haptic('light');
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  hiddenInput.value = catId;
  container.querySelectorAll('.cat-chip').forEach(chip => {
    chip.classList.toggle('selected', String(chip.dataset.id) === String(catId));
  });
}

export function selectAccountPill(containerId, hiddenInputId, accId) {
  haptic('light');
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  hiddenInput.value = accId;
  container.querySelectorAll('.acc-pill').forEach(pill => {
    pill.classList.toggle('selected', String(pill.dataset.id) === String(accId));
  });
}

export function renderCategoryChips(containerId, hiddenInputId, categories, defaultSelectedId) {
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container || !hiddenInput) return;

  const currentVal = hiddenInput.value || defaultSelectedId || (categories[0] ? categories[0].id : '');
  hiddenInput.value = currentVal;

  container.innerHTML = categories.map(c => {
    const isSelected = String(c.id) === String(currentVal);
    const iconSvg = getCategoryIcon(c.icon || c.name || c.iconKey);
    return `
      <div class="cat-chip ${isSelected ? 'selected' : ''}" data-id="${c.id}" onclick="window.selectCategoryChip('${containerId}', '${hiddenInputId}', '${c.id}')">
        <span class="cat-chip-icon">${iconSvg}</span>
        <span>${c.name}</span>
      </div>
    `;
  }).join('');
}

export function renderAccountPills(containerId, hiddenInputId, accounts, defaultSelectedId) {
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
      <div class="acc-pill ${isSelected ? 'selected' : ''}" data-id="${a.id}" onclick="window.selectAccountPill('${containerId}', '${hiddenInputId}', '${a.id}')">
        <span class="acc-pill-icon">${iconSvg}</span>
        <div>
          <div class="acc-pill-name">${a.name}</div>
          <div class="acc-pill-balance">${formatMoney(a.balance)}</div>
        </div>
      </div>
    `;
  }).join('');
}

export function populateAccountDropdowns() {
  const accs = state.accounts || [];
  renderAccountPills('incomeAccountPills', 'incomeAccount', accs);
  renderAccountPills('expenseAccountPills', 'expenseAccount', accs);
  renderAccountPills('transferFromAccountPills', 'transferFromAccount', accs);
  renderAccountPills('transferToAccountPills', 'transferToAccount', accs);
  renderAccountPills('saveDepositSourcePills', 'saveDepositSource', accs);
  renderAccountPills('saveWithdrawDestPills', 'saveWithdrawDest', accs);

  // Select fallback for debt
  const regularAccs = accs.filter(a => !a.is_savings);
  const optionsHtml = regularAccs.length
    ? regularAccs.map(a => `<option value="${a.id}">${a.name} (${formatMoney(a.balance)})</option>`).join('')
    : '<option value="1">Карта (0 сум)</option><option value="2">Наличные (0 сум)</option>';
  const debtAcc = document.getElementById('debtAccount');
  if (debtAcc) debtAcc.innerHTML = optionsHtml;
}

export function populateCategoryDropdowns() {
  const expCats = (state.categories?.expense && state.categories.expense.length)
    ? state.categories.expense
    : DEFAULT_FALLBACK_EXPENSE;

  const incCats = (state.categories?.income && state.categories.income.length)
    ? state.categories.income
    : DEFAULT_FALLBACK_INCOME;

  renderCategoryChips('expenseCategoryChips', 'expenseCategory', expCats);
  renderCategoryChips('incomeCategoryChips', 'incomeCategory', incCats);
}

export function openModal(modalId) {
  haptic('medium');
  populateAccountDropdowns();
  populateCategoryDropdowns();
  initAmountInputListeners();
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('open');
}

export function closeModal(modalId) {
  haptic('light');
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('open');
}

export function addAmount(inputId, delta) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    const current = parseAmountInput(input.value);
    const total = current + delta;
    input.value = formatThousands(total);
    updateHeroDisplay(input);
  }
}

export function clearAmount(inputId) {
  haptic('light');
  const input = document.getElementById(inputId);
  if (input) {
    input.value = '';
    updateHeroDisplay(input);
  }
}

export function showConfirmDialog({ title = 'Подтверждение', message = 'Вы уверены?', btnText = 'Подтвердить', isDanger = true, onConfirm }) {
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
  profilesState.confirmCallback = onConfirm;
  openModal('modalConfirm');
}

export function initConfirmModalListeners() {
  document.getElementById('confirmAcceptBtn')?.addEventListener('click', async () => {
    haptic('medium');
    closeModal('modalConfirm');
    if (typeof profilesState.confirmCallback === 'function') {
      const cb = profilesState.confirmCallback;
      profilesState.confirmCallback = null;
      await cb();
    }
  });
}
