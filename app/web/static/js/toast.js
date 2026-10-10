/**
 * Toast notifications and user notification center.
 */

import { state } from './state.js';
import { formatDate, haptic } from './utils.js';

export function saveNotifications() {
  try {
    localStorage.setItem('hisob_notifications', JSON.stringify(state.notifications));
  } catch (e) {}
}

export function updateNotificationBadge() {
  const dot = document.getElementById('notifBadgeDot');
  if (!dot) return;
  const hasUnread = state.notifications.some(n => !n.isRead);
  dot.style.display = hasUnread ? 'block' : 'none';
}

export function addNotification({ title, message, type = 'info', isRead = false }) {
  const notif = {
    id: Date.now() + Math.random().toString(36).substring(2, 7),
    title: title || (type === 'error' ? 'Ошибка' : type === 'success' ? 'Успешно' : 'Информация'),
    message: message || '',
    type: type,
    time: new Date().toISOString(),
    isRead: isRead,
  };
  state.notifications.unshift(notif);
  if (state.notifications.length > 50) state.notifications.pop();
  saveNotifications();
  updateNotificationBadge();
  if (document.getElementById('tab-notifications')?.classList.contains('active')) {
    renderNotifications();
  }
}

export function showToast(message, type = 'success', title = null) {
  // Persist to notification center
  addNotification({
    title: title,
    message: message,
    type: type,
    isRead: false,
  });

  // Render floating toast pill on screen
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  // Create toast pill element
  const pill = document.createElement('div');
  pill.className = `toast-pill ${type}`;

  let iconSvg = '';
  if (type === 'error') {
    iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    haptic('error');
  } else if (type === 'info') {
    iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    haptic('light');
  } else if (type === 'warning') {
    iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
    haptic('medium');
  } else {
    // success default
    iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
    haptic('light');
  }

  pill.innerHTML = `
    <span class="toast-icon-wrap">${iconSvg}</span>
    <span class="toast-text">${message}</span>
  `;

  // Dismiss on click
  pill.addEventListener('click', () => {
    pill.classList.add('hide');
    setTimeout(() => pill.remove(), 200);
  });

  container.appendChild(pill);

  // Auto remove after 3.2s
  setTimeout(() => {
    if (pill.parentNode) {
      pill.classList.add('hide');
      setTimeout(() => pill.remove(), 220);
    }
  }, 3200);
}

export function renderNotifications() {
  const container = document.getElementById('notificationsList');
  if (!container) return;

  state.notifications.forEach(n => (n.isRead = true));
  saveNotifications();
  updateNotificationBadge();

  if (!state.notifications.length) {
    container.innerHTML = `
      <div class="notif-empty-state">
        <div class="notif-empty-icon">
          <svg viewBox="0 0 24 24" width="22" height="22" stroke="currentColor" stroke-width="2" fill="none">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
        </div>
        <div class="notif-empty-title">Нет новых уведомлений</div>
        <div class="notif-empty-sub">Оповещения об операциях и целях появятся здесь</div>
      </div>
    `;
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

export function clearAllNotifications() {
  haptic('medium');
  state.notifications = [];
  saveNotifications();
  updateNotificationBadge();
  renderNotifications();
}
