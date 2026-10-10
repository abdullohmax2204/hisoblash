/**
 * Debts view and debt modals management.
 */

import { state } from '../state.js';
import { fetchDebts } from '../api.js';
import { formatMoney, formatDate, formatThousands, haptic } from '../utils.js';
import { openModal } from '../components/modals.js';

export async function loadDebts() {
  try {
    const data = await fetchDebts();
    state.debts = data;
    renderDebtsList();
  } catch (err) {
    console.error('Failed to load debts:', err);
  }
}

export function renderDebtsList() {
  const container = document.getElementById('debtsList');
  if (!container) return;

  const list = state.debts[state.currentDebtType] || [];

  if (!list.length) {
    if (state.currentDebtType === 'given') {
      container.innerHTML = `
        <div class="debt-empty-card" onclick="window.openGiveDebtModal()">
          <div class="debt-empty-icon given">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
          </div>
          <div class="debt-empty-info">
            <div class="debt-empty-title">Вам никто не должен</div>
            <div class="debt-empty-sub">+ Нажмите, чтобы записать, если дали в долг</div>
          </div>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="debt-empty-card" onclick="window.openTakeDebtModal()">
          <div class="debt-empty-icon taken">
            <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
          </div>
          <div class="debt-empty-info">
            <div class="debt-empty-title">У вас нет активных долгов</div>
            <div class="debt-empty-sub">Все обязательства закрыты. Нажмите, если взяли взаймы</div>
          </div>
        </div>
      `;
    }
    return;
  }

  const totalRemaining = list.reduce((sum, d) => sum + (Number(d.remaining_amount) || 0), 0);
  const summaryBarHTML = `
    <div class="debt-summary-bar">
      <span class="debt-summary-label">${state.currentDebtType === 'given' ? 'Всего вам должны' : 'Ваш общий долг'}</span>
      <span class="debt-summary-val ${state.currentDebtType === 'given' ? 'text-green' : 'text-red'}">${formatMoney(totalRemaining)}</span>
    </div>
  `;

  const itemsHTML = list.map(d => {
    const personSafe = (d.person_name || 'Контакт').replace(/'/g, "\\'");
    const actionLabel = state.currentDebtType === 'given' ? 'Вернули долг' : 'Погасить';
    return `
      <div class="debt-item">
        <div class="debt-item-info">
          <div class="person">
            <svg viewBox="0 0 24 24" width="15" height="15" stroke="currentColor" stroke-width="2" fill="none" style="vertical-align: text-bottom; margin-right: 4px; color: var(--text-muted);">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            ${d.person_name || 'Контакт'}
          </div>
          <div class="date">Создан: ${formatDate(d.created_at)}</div>
        </div>
        <div class="debt-item-right">
          <div class="rem-amount">${formatMoney(d.remaining_amount)}</div>
          <button class="btn-repay" onclick="window.openReturnDebtModal(${d.id}, '${personSafe}', ${d.remaining_amount})">
            ${actionLabel}
          </button>
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = summaryBarHTML + itemsHTML;
}

export function switchDebtType(type) {
  haptic('light');
  state.currentDebtType = type;
  const btnGiven = document.getElementById('btnDebtGiven');
  const btnTaken = document.getElementById('btnDebtTaken');
  if (btnGiven) btnGiven.classList.toggle('active', type === 'given');
  if (btnTaken) btnTaken.classList.toggle('active', type === 'taken');
  renderDebtsList();
}

export function openGiveDebtModal() {
  const title = document.getElementById('debtModalTitle');
  const mode = document.getElementById('debtFormMode');
  const pGroup = document.getElementById('debtPersonGroup');
  const accLabel = document.getElementById('debtAccountLabel');
  const sBtn = document.getElementById('debtSubmitBtn');
  const form = document.getElementById('formDebt');

  if (title) title.textContent = 'Дать в долг';
  if (mode) mode.value = 'give';
  if (pGroup) pGroup.style.display = 'block';
  if (accLabel) accLabel.textContent = 'Списать со счёта';
  if (sBtn) sBtn.textContent = 'Дать в долг';
  if (form) form.reset();

  openModal('modalDebt');
}

export function openTakeDebtModal() {
  const title = document.getElementById('debtModalTitle');
  const mode = document.getElementById('debtFormMode');
  const pGroup = document.getElementById('debtPersonGroup');
  const accLabel = document.getElementById('debtAccountLabel');
  const sBtn = document.getElementById('debtSubmitBtn');
  const form = document.getElementById('formDebt');

  if (title) title.textContent = 'Взять в долг';
  if (mode) mode.value = 'take';
  if (pGroup) pGroup.style.display = 'block';
  if (accLabel) accLabel.textContent = 'Зачислить на счёт';
  if (sBtn) sBtn.textContent = 'Взять в долг';
  if (form) form.reset();

  openModal('modalDebt');
}

export function openReturnDebtModal(debtId, personName, remAmount) {
  const title = document.getElementById('debtModalTitle');
  const mode = document.getElementById('debtFormMode');
  const returnId = document.getElementById('debtReturnId');
  const pGroup = document.getElementById('debtPersonGroup');
  const amtInput = document.getElementById('debtAmount');
  const accLabel = document.getElementById('debtAccountLabel');
  const sBtn = document.getElementById('debtSubmitBtn');

  if (title) title.textContent = `Погашение долга (${personName})`;
  if (mode) mode.value = 'return';
  if (returnId) returnId.value = debtId;
  if (pGroup) pGroup.style.display = 'none';
  if (amtInput) amtInput.value = formatThousands(remAmount);
  if (accLabel) accLabel.textContent = 'Счёт для взаиморасчёта';
  if (sBtn) sBtn.textContent = 'Подтвердить возврат';

  openModal('modalDebt');
}
