/**
 * Accounts and savings goals view.
 */

import { state } from '../state.js';
import { formatMoney, formatDate, haptic } from '../utils.js';
import { showToast } from '../toast.js';
import { showConfirmDialog } from '../components/modals.js';
import { apiFetch } from '../api.js';

export function renderGoals() {
  if (!state.summary) return;
  const goals = state.summary.goals || [];
  const goalsContainer = document.getElementById('savingsGoalsList');
  const tabBalEl = document.getElementById('savingsTabBalance');
  if (tabBalEl) tabBalEl.textContent = formatMoney(state.summary.savings_balance);

  if (!goalsContainer) return;

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
          <button class="goal-delete-btn" onclick="window.deleteGoal(${g.id})" title="Удалить">✕</button>
        </div>
      </div>
      ${g.target_date ? `<div style="font-size:11px; color:var(--text-muted); margin-top:2px; margin-bottom:6px;">Дедлайн: ${formatDate(g.target_date)}</div>` : ''}
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${Math.min(g.pct, 100)}%;"></div>
      </div>
    </div>
  `).join('');
}

export function deleteGoal(goalId, reloadSummaryCallback) {
  showConfirmDialog({
    title: 'Удалить цель?',
    message: 'Цель накопления будет удалена. Накопленные средства останутся на счете.',
    btnText: 'Удалить',
    isDanger: true,
    onConfirm: async () => {
      try {
        await apiFetch(`/api/savings/goals/${goalId}`, { method: 'DELETE' });
        showToast('Цель удалена', 'info');
        if (typeof reloadSummaryCallback === 'function') {
          await reloadSummaryCallback();
        }
      } catch (err) {
        showToast(err.message || 'Ошибка удаления цели', 'error');
      }
    }
  });
}
