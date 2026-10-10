/**
 * Forms handling and submissions for transactions, transfers, debts, accounts, goals, and salary.
 */

import { state } from './state.js';
import { apiFetch } from './api.js';
import { showToast } from './toast.js';
import { parseAmountInput, clearAmount, formatThousands, haptic } from './utils.js';
import { openModal, closeModal } from './components/modals.js';
import { renderLoadAnalysis } from './views/overview.js';

export async function handleFormSubmit(e, asyncCallback) {
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

export async function submitIncome(e, onCompleted) {
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
    const category_id = rawCat && !isNaN(parseInt(rawCat, 10)) ? parseInt(rawCat, 10) : null;
    const description = document.getElementById('incomeDesc')?.value;

    try {
      await apiFetch('/api/transactions/income', {
        method: 'POST',
        body: JSON.stringify({ amount, account_id, category_id, description }),
      });
      closeModal('modalIncome');
      document.getElementById('formIncome')?.reset();
      clearAmount('incomeAmount');
      showToast('Доход успешно добавлен!');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка добавления дохода', 'error');
    }
  });
}

export async function submitExpense(e, onCompleted) {
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
    let category_id = rawCat && !isNaN(parseInt(rawCat, 10)) ? parseInt(rawCat, 10) : null;
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
      document.getElementById('formExpense')?.reset();
      clearAmount('expenseAmount');
      showToast('Расход записан!');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка записи расхода', 'error');
    }
  });
}

export async function submitTransfer(e, onCompleted) {
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

    if (String(from_account_id) === String(to_account_id)) {
      showToast('Счета списания и зачисления должны отличаться', 'warning');
      return;
    }

    try {
      await apiFetch('/api/transactions/transfer', {
        method: 'POST',
        body: JSON.stringify({ amount, from_account_id, to_account_id }),
      });
      closeModal('modalTransfer');
      document.getElementById('formTransfer')?.reset();
      clearAmount('transferAmount');
      showToast('Перевод успешно выполнен!');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка выполнения перевода', 'error');
    }
  });
}

export async function submitSaveDeposit(e, onCompleted) {
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
      document.getElementById('formSaveDeposit')?.reset();
      clearAmount('saveDepositAmount');
      showToast('Отложено в накопления!');
      if (res.reached_goals && res.reached_goals.length) {
        showToast(`🎉 Достигнута цель: ${res.reached_goals.join(', ')}!`, 'success');
      }
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка пополнения накоплений', 'error');
    }
  });
}

export async function submitSaveWithdraw(e, onCompleted) {
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
      document.getElementById('formSaveWithdraw')?.reset();
      clearAmount('saveWithdrawAmount');
      showToast('Деньги выведены из накоплений');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка вывода средств', 'error');
    }
  });
}

export async function submitNewAccount(e, onCompleted) {
  await handleFormSubmit(e, async () => {
    const name = document.getElementById('newAccountName')?.value;
    const icon = document.querySelector('input[name="accIcon"]:checked')?.value || '💳';
    const initial_balance = parseAmountInput(document.getElementById('newAccountBalance'));

    try {
      await apiFetch('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({ name, icon, initial_balance }),
      });
      closeModal('modalNewAccount');
      document.getElementById('formNewAccount')?.reset();
      showToast('Новый счёт создан!');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка создания счета', 'error');
    }
  });
}

export async function submitNewGoal(e, onCompleted) {
  await handleFormSubmit(e, async () => {
    const name = document.getElementById('newGoalName')?.value;
    const target_amount = parseAmountInput(document.getElementById('newGoalTarget'));
    const target_date = document.getElementById('newGoalDate')?.value;

    try {
      await apiFetch('/api/savings/goals', {
        method: 'POST',
        body: JSON.stringify({ name, target_amount, target_date }),
      });
      closeModal('modalNewGoal');
      document.getElementById('formNewGoal')?.reset();
      showToast('Новая цель создана!');
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка создания цели', 'error');
    }
  });
}

export function openSalaryModal() {
  const currentVal = state.summary?.user?.monthly_salary;
  const inputEl = document.getElementById('salaryMonthlyInput');
  if (inputEl) {
    inputEl.value = currentVal ? formatThousands(currentVal) : '';
  }
  const cycleVal = state.summary?.user?.pay_cycle_days || 30;
  const cycleEl = document.getElementById('salaryCycleInput');
  if (cycleEl) {
    cycleEl.value = cycleVal;
  }
  openModal('modalSalary');
}

export async function submitSalaryForm(e, onCompleted) {
  await handleFormSubmit(e, async () => {
    const monthly_salary = parseAmountInput(document.getElementById('salaryMonthlyInput'));
    const pay_cycle_days = parseInt(document.getElementById('salaryCycleInput')?.value || '30', 10);

    try {
      const analysis = await apiFetch('/api/user/salary', {
        method: 'POST',
        body: JSON.stringify({ monthly_salary, pay_cycle_days }),
      });
      closeModal('modalSalary');
      showToast('Настройки дохода сохранены!');
      if (state.summary) {
        if (!state.summary.user) state.summary.user = {};
        state.summary.user.monthly_salary = monthly_salary;
        state.summary.user.pay_cycle_days = pay_cycle_days;
      }
      renderLoadAnalysis(analysis);
      if (typeof onCompleted === 'function') await onCompleted();
    } catch (err) {
      showToast(err.message || 'Ошибка сохранения зарплаты', 'error');
    }
  });
}

export async function submitDebtForm(e, onCompleted, onDebtsReload) {
  await handleFormSubmit(e, async () => {
    const mode = document.getElementById('debtFormMode')?.value;
    const amount = parseAmountInput(document.getElementById('debtAmount'));
    const account_id = document.getElementById('debtAccount')?.value;
    const person_name = document.getElementById('debtPersonName')?.value;
    const debt_id = document.getElementById('debtReturnId')?.value;

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
      if (typeof onCompleted === 'function') await onCompleted();
      if (typeof onDebtsReload === 'function') await onDebtsReload();
    } catch (err) {
      showToast(err.message || 'Ошибка обработки долга', 'error');
    }
  });
}
