/**
 * Transaction history view with pagination and deletion.
 */

import { state } from '../state.js';
import { fetchHistory, apiFetch } from '../api.js';
import { showToast } from '../toast.js';
import { showConfirmDialog } from '../components/modals.js';
import { createTxItemHTML } from './overview.js';

export async function loadHistory(page = 0) {
  try {
    const data = await fetchHistory(page, 15);
    state.historyPage = page;
    const txs = data.transactions || [];
    state.historyHasNext = txs.length === 15;
    renderFullHistory(txs);
  } catch (err) {
    console.error('Failed to load history:', err);
    showToast('Ошибка загрузки истории', 'error');
  }
}

export function renderFullHistory(transactions) {
  const container = document.getElementById('fullHistoryList');
  const pagination = document.getElementById('historyPagination');
  if (!container) return;

  if (!transactions.length && state.historyPage === 0) {
    container.innerHTML = `
      <div class="tx-empty-state">
        <div class="tx-empty-icon">
          <svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none">
            <polyline points="12 8 12 12 14 14"></polyline>
            <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
          </svg>
        </div>
        <div class="tx-empty-title">История операций пуста</div>
        <div class="tx-empty-sub">Все совершённые доходы, расходы и переводы будут сохраняться здесь</div>
      </div>
    `;
    if (pagination) pagination.style.display = 'none';
    return;
  }

  container.innerHTML = transactions.map(tx => createTxItemHTML(tx, true)).join('');

  if (pagination) {
    pagination.style.display = 'flex';
    const pageIndicator = document.getElementById('pageIndicator');
    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    if (pageIndicator) pageIndicator.textContent = `Стр. ${state.historyPage + 1}`;
    if (prevBtn) prevBtn.disabled = state.historyPage === 0;
    if (nextBtn) nextBtn.disabled = !state.historyHasNext;
  }
}

export function loadHistoryPage(direction) {
  const newPage = state.historyPage + direction;
  if (newPage >= 0) {
    loadHistory(newPage);
  }
}

export function deleteTransaction(txId, onDeletedCallback) {
  showConfirmDialog({
    title: 'Удалить операцию?',
    message: 'Операция будет удалена, а баланс счёта скорректирован.',
    btnText: 'Удалить',
    isDanger: true,
    onConfirm: async () => {
      try {
        await apiFetch(`/api/transactions/${txId}`, { method: 'DELETE' });
        showToast('Операция отменена', 'info');
        if (typeof onDeletedCallback === 'function') {
          await onDeletedCallback();
        }
        await loadHistory(state.historyPage);
      } catch (err) {
        showToast(err.message || 'Ошибка удаления операции', 'error');
      }
    }
  });
}
