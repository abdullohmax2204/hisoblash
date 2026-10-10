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
    const emptyText = state.currentDebtType === 'given' ? 'Мне должны' : 'Я должен';
    container.innerHTML = `<div class="empty-state">Нет активных записей в разделе "${emptyText}"</div>`;
    return;
  }

  container.innerHTML = list.map(d => {
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
