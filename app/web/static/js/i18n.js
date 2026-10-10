/**
 * Internationalization (i18n) engine for Hisoblash Web App.
 * Supports: Uzbek (uz), Russian (ru), English (en).
 */

export const TRANSLATIONS = {
  uz: {
    // Header & Brand
    app_title: "Hisoblash",
    fullscreen_tooltip: "To'liq ekran rejimi (F)",
    eye_tooltip: "Balansni yashirish / ko'rsatish",

    // Capital Card
    total_capital: "UMUMIY KAPITAL",
    available: "Mavjud",
    savings: "Jamg'arma",
    debts_net: "Qarzlar (+/-)",

    // Fast Action Buttons
    action_income: "Kirim",
    action_expense: "Chiqim",
    action_transfer: "O'tkazma",

    // Navigation Tabs
    nav_home: "Bosh sahifa",
    nav_accounts: "Hisoblar",
    nav_stats: "Tahlil",
    nav_debts: "Qarzlar",
    nav_history: "Tarix",
    nav_info: "Info",

    // Overview Tab
    recent_transactions: "So'nggi operatsiyalar",
    view_all: "Barchasi",
    no_transactions: "Operatsiyalar yo'q",
    financial_load_title: "Moliyaviy yuklama",

    // Accounts Tab
    my_accounts: "Mening hisoblarim",
    add_btn: "+ Qo'shish",
    savings_goals: "Jamg'arma maqsadlari",
    total_in_savings: "JAMG'ARMADAGI MABLAG'",
    deposit_btn: "To'ldirish",
    withdraw_btn: "Yechib olish",
    no_goals: "Hozircha maqsadlar yo'q",

    // Analytics Tab
    stats_expense_title: "Xarajatlar tahlili",
    stats_income: "Daromadlar",
    stats_expense: "Xarajatlar",
    stats_net: "Natija (Saldo)",
    categories_chart_title: "Kategoriyalar bo'yicha",
    period_today: "Bugun",
    period_week: "Hafta",
    period_month: "Oy",
    period_all: "Barchasi",

    // Debts Tab
    debts_lent_tab: "Menga qarz",
    debts_borrowed_tab: "Men qarzdorman",
    give_debt_btn: "+ Qarz berish",
    take_debt_btn: "+ Qarz olish",
    total_lent_label: "UMUMIY MENGA QARZLAR",
    total_borrowed_label: "UMUMIY MENING QARZLARIM",
    no_debts_msg: "Qarzlar mavjud emas",

    // History Tab
    history_title: "Operatsiyalar tarixi",
    filter_all: "Barchasi",
    filter_income: "Kirim",
    filter_expense: "Chiqim",

    // Common Modals & Forms
    modal_income_title: "Kirim qo'shish",
    modal_expense_title: "Chiqim qo'shish",
    modal_transfer_title: "Hisoblararo o'tkazma",
    modal_new_account_title: "Yangi hisob",
    modal_new_goal_title: "Yangi maqsad",
    amount_label: "Summa (so'm)",
    account_label: "Hisob",
    category_label: "Kategoriya",
    comment_label: "Izoh (ixtiyoriy)",
    btn_confirm: "Tasdiqlash",
    btn_cancel: "Bekor qilish",
    btn_delete: "O'chirish",
    confirm_title: "Tasdiqlash",
    confirm_delete_tx: "Haqiqatan ham ushbu operatsiyani o'chirmoqchimisiz? Hisob balansi avtomatik qaytariladi.",
  },

  ru: {
    // Header & Brand
    app_title: "Hisoblash",
    fullscreen_tooltip: "Полноэкранный режим (F)",
    eye_tooltip: "Скрыть / показать баланс",

    // Capital Card
    total_capital: "ОБЩИЙ КАПИТАЛ",
    available: "Доступно",
    savings: "Накопления",
    debts_net: "В долгах (+/-)",

    // Fast Action Buttons
    action_income: "Доход",
    action_expense: "Расход",
    action_transfer: "Перевод",

    // Navigation Tabs
    nav_home: "Главная",
    nav_accounts: "Счета",
    nav_stats: "Анализ",
    nav_debts: "Долги",
    nav_history: "История",
    nav_info: "Инфо",

    // Overview Tab
    recent_transactions: "Последние операции",
    view_all: "Все",
    no_transactions: "Операций пока нет",
    financial_load_title: "Финансовая нагрузка",

    // Accounts Tab
    my_accounts: "Мои счета",
    add_btn: "+ Добавить",
    savings_goals: "Цели накоплений",
    total_in_savings: "ВСЕГО В НАКОПЛЕНИЯХ",
    deposit_btn: "Пополнить",
    withdraw_btn: "Снять",
    no_goals: "Целей пока нет",

    // Analytics Tab
    stats_expense_title: "Анализ расходов",
    stats_income: "Доходы",
    stats_expense: "Расходы",
    stats_net: "Итог (Сальдо)",
    categories_chart_title: "Расходы по категориям",
    period_today: "Сегодня",
    period_week: "Неделя",
    period_month: "Месяц",
    period_all: "Всё время",

    // Debts Tab
    debts_lent_tab: "Мне должны",
    debts_borrowed_tab: "Я должен",
    give_debt_btn: "+ Дать в долг",
    take_debt_btn: "+ Взять в долг",
    total_lent_label: "ВСЕГО МНЕ ДОЛЖНЫ",
    total_borrowed_label: "ВСЕГО Я ДОЛЖЕН",
    no_debts_msg: "Долгов нет",

    // History Tab
    history_title: "История операций",
    filter_all: "Все",
    filter_income: "Доходы",
    filter_expense: "Расходы",

    // Common Modals & Forms
    modal_income_title: "Добавить доход",
    modal_expense_title: "Добавить расход",
    modal_transfer_title: "Перевод между счетами",
    modal_new_account_title: "Новый счёт",
    modal_new_goal_title: "Новая цель",
    amount_label: "Сумма (сум)",
    account_label: "Счёт",
    category_label: "Категория",
    comment_label: "Комментарий (необязательно)",
    btn_confirm: "Подтвердить",
    btn_cancel: "Отмена",
    btn_delete: "Удалить",
    confirm_title: "Подтверждение",
    confirm_delete_tx: "Вы действительно хотите удалить эту транзакцию? Баланс счёта откатится назад.",
  },

  en: {
    // Header & Brand
    app_title: "Hisoblash",
    fullscreen_tooltip: "Toggle Fullscreen (F)",
    eye_tooltip: "Hide / Show Balance",

    // Capital Card
    total_capital: "TOTAL CAPITAL",
    available: "Available",
    savings: "Savings",
    debts_net: "Net Debts (+/-)",

    // Fast Action Buttons
    action_income: "Income",
    action_expense: "Expense",
    action_transfer: "Transfer",

    // Navigation Tabs
    nav_home: "Home",
    nav_accounts: "Accounts",
    nav_stats: "Analytics",
    nav_debts: "Debts",
    nav_history: "History",
    nav_info: "Info",

    // Overview Tab
    recent_transactions: "Recent Transactions",
    view_all: "View All",
    no_transactions: "No transactions yet",
    financial_load_title: "Financial Load",

    // Accounts Tab
    my_accounts: "My Accounts",
    add_btn: "+ Add",
    savings_goals: "Savings Goals",
    total_in_savings: "TOTAL IN SAVINGS",
    deposit_btn: "Deposit",
    withdraw_btn: "Withdraw",
    no_goals: "No goals yet",

    // Analytics Tab
    stats_expense_title: "Expense Breakdown",
    stats_income: "Income",
    stats_expense: "Expenses",
    stats_net: "Net Balance",
    categories_chart_title: "Expenses by Category",
    period_today: "Today",
    period_week: "Week",
    period_month: "Month",
    period_all: "All Time",

    // Debts Tab
    debts_lent_tab: "Owed to Me",
    debts_borrowed_tab: "I Owe",
    give_debt_btn: "+ Lend Debt",
    take_debt_btn: "+ Borrow",
    total_lent_label: "TOTAL OWED TO ME",
    total_borrowed_label: "TOTAL I OWE",
    no_debts_msg: "No active debts",

    // History Tab
    history_title: "Transaction History",
    filter_all: "All",
    filter_income: "Income",
    filter_expense: "Expenses",

    // Common Modals & Forms
    modal_income_title: "Add Income",
    modal_expense_title: "Add Expense",
    modal_transfer_title: "Transfer Between Accounts",
    modal_new_account_title: "New Account",
    modal_new_goal_title: "New Goal",
    amount_label: "Amount",
    account_label: "Account",
    category_label: "Category",
    comment_label: "Comment (optional)",
    btn_confirm: "Confirm",
    btn_cancel: "Cancel",
    btn_delete: "Delete",
    confirm_title: "Confirmation",
    confirm_delete_tx: "Are you sure you want to delete this transaction? The account balance will be rolled back.",
  },
};

let currentLanguage = localStorage.getItem("app_lang") || "ru";

export function getLanguage() {
  return currentLanguage;
}

export function t(key) {
  const dict = TRANSLATIONS[currentLanguage] || TRANSLATIONS.ru;
  return dict[key] || TRANSLATIONS.ru[key] || key;
}

export function setLanguage(lang, onLangChangeCallback = null) {
  if (!TRANSLATIONS[lang]) return;
  currentLanguage = lang;
  localStorage.setItem("app_lang", lang);

  // Update HTML lang attribute
  document.documentElement.lang = lang;

  // Update active pill button UI in header
  document.querySelectorAll(".lang-pill-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.lang === lang);
  });

  // Update all DOM elements with data-i18n
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      el.textContent = t(key);
    }
  });

  // Update elements with data-i18n-title
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title");
    if (key) {
      el.setAttribute("title", t(key));
    }
  });

  if (typeof onLangChangeCallback === "function") {
    onLangChangeCallback(lang);
  }
}
