/**
 * REST API client with Telegram initData & Profile ID authentication headers.
 */

import { tg } from './state.js';

export async function apiFetch(endpoint, options = {}) {
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

    if (!res.ok) {
      let errorMsg = `Ошибка сервера (${res.status})`;
      try {
        const errorJson = await res.json();
        if (errorJson.error) errorMsg = errorJson.error;
      } catch (e) {}
      throw new Error(errorMsg);
    }

    const contentType = res.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await res.json();
    }
    return await res.text();
  } catch (err) {
    console.error(`API Fetch Error [${endpoint}]:`, err);
    throw err;
  }
}

export async function fetchSummary() {
  return await apiFetch('/api/summary');
}

export async function fetchAccounts() {
  return await apiFetch('/api/accounts');
}

export async function fetchCategories() {
  return await apiFetch('/api/categories');
}

export async function fetchDebts() {
  return await apiFetch('/api/debts');
}

export async function fetchStats(period) {
  return await apiFetch(`/api/stats?period=${period}`);
}

export async function fetchHistory(page = 0, pageSize = 15) {
  return await apiFetch(`/api/history?page=${page}&page_size=${pageSize}`);
}

export async function fetchRates() {
  return await apiFetch('/api/rates');
}

export async function syncRates() {
  return await apiFetch('/api/rates/sync', { method: 'POST' });
}

export async function fetchLoadAnalysis() {
  return await apiFetch('/api/savings/load-analysis');
}

export async function fetchUserProfiles() {
  return await apiFetch('/api/users');
}
