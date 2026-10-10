/**
 * Formatting, device detection, fullscreen, and haptic feedback utilities.
 */

import { tg, state } from './state.js';

export function haptic(type = 'light') {
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

export function formatMoney(amount, currency = null) {
  if (amount === undefined || amount === null) return '0 сум';
  if (!state.balanceVisible) return '••••••';

  const targetCur = currency || state.displayCurrency || 'UZS';
  let num = Number(amount);

  if (!currency && state.displayCurrency !== 'UZS' && state.summary?.rates) {
    const rateData = state.summary.rates[state.displayCurrency];
    const rate = Number(rateData?.rate || 1);
    if (rate > 0) {
      num = num / rate;
    }
  }

  let symbol = 'сум';
  let decimals = 0;
  if (targetCur === 'USD') { symbol = '$'; decimals = 2; }
  else if (targetCur === 'EUR') { symbol = '€'; decimals = 2; }
  else if (targetCur === 'RUB') { symbol = '₽'; decimals = 0; }

  const formatted = num.toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).replace(/,/g, ' ');

  if (targetCur === 'USD' || targetCur === 'EUR' || targetCur === 'RUB') {
    return `${symbol} ${formatted}`;
  }
  return `${formatted} сум`;
}

export function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
  const month = months[d.getMonth()];
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day} ${month}, ${hours}:${minutes}`;
}

export function formatThousands(valStr) {
  if (valStr === undefined || valStr === null || valStr === '') return '';
  const clean = valStr.toString().replace(/[^\d.,]/g, '').replace(',', '.');
  const parts = clean.split('.');
  const integerPart = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  if (parts.length > 1) {
    return `${integerPart}.${parts[1].slice(0, 2)}`;
  }
  return integerPart;
}

export function parseAmountInput(inputOrValue) {
  if (typeof inputOrValue === 'number') return isNaN(inputOrValue) ? 0 : inputOrValue;
  let val = typeof inputOrValue === 'string' ? inputOrValue : (inputOrValue?.value || '0');
  val = val.toString().replace(/\s+/g, '').replace(',', '.');
  const num = parseFloat(val);
  return isNaN(num) ? 0 : num;
}

export function updateHeroDisplay(input) {
  if (!input) return;
  const displayId = input.dataset.displayId;
  if (!displayId) return;
  const displayEl = document.getElementById(displayId);
  if (!displayEl) return;

  const rawNum = parseAmountInput(input.value);
  const formatted = rawNum > 0 ? formatThousands(rawNum) : '0';
  displayEl.innerHTML = `${formatted} <span class="hero-amount-currency">сум</span>`;
}

export function formatNumberOnInput(e) {
  const input = e.target;
  const formatted = formatThousands(input.value);
  input.value = formatted;
  updateHeroDisplay(input);
}

export function initAmountInputListeners() {
  document.querySelectorAll('.amount-input').forEach(input => {
    input.removeEventListener('input', formatNumberOnInput);
    input.removeEventListener('keyup', formatNumberOnInput);
    input.addEventListener('input', formatNumberOnInput);
    input.addEventListener('keyup', formatNumberOnInput);
    updateHeroDisplay(input);
  });
}

export function setDisplayCurrency(cur, renderCallback) {
  haptic('light');
  state.displayCurrency = cur;
  localStorage.setItem('hisob_display_currency', cur);
  updateCurrencyPillsUI();
  if (typeof renderCallback === 'function') {
    renderCallback();
  }
}

export function updateCurrencyPillsUI() {
  document.querySelectorAll('.curr-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.curr === (state.displayCurrency || 'UZS'));
  });
}

export function isMobileDevice() {
  if (tg?.platform) {
    const p = tg.platform.toLowerCase();
    if (['android', 'ios', 'mobile'].includes(p)) return true;
    if (['tdesktop', 'macos', 'web', 'weba', 'webk'].includes(p)) return false;
  }
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

export function toggleFullscreenMode() {
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

export function updateFullscreenBtnState() {
  const isFull = (tg && tg.isFullscreen) || !!document.fullscreenElement;
  if (typeof document !== 'undefined' && document.body) {
    document.body.classList.toggle('is-fullscreen', isFull);
  }

  const btn = document.getElementById('toggleFullscreenBtn');
  if (!btn) return;

  if (isMobileDevice()) {
    btn.style.display = 'none';
    return;
  }

  btn.style.display = 'flex';

  if (isFull) {
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path></svg>`;
    btn.title = 'Оконный режим (F)';
  } else {
    btn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>`;
    btn.title = 'Полноэкранный режим (F)';
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('fullscreenchange', updateFullscreenBtnState);
  window.addEventListener('resize', updateFullscreenBtnState);
}

export function isLightBg(hex) {
  if (!hex || typeof hex !== 'string' || !hex.startsWith('#')) return false;
  const rgb = parseInt(hex.slice(1), 16);
  if (isNaN(rgb)) return false;
  const r = (rgb >> 16) & 0xff;
  const g = (rgb >> 8) & 0xff;
  const b = (rgb >> 0) & 0xff;
  const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return luma > 128;
}
