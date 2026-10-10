/**
 * Personal profile display module for single-user accounting.
 */

import { fetchUserProfiles } from '../api.js';

export let userProfilesList = [];

export async function loadUserProfiles() {
  try {
    const data = await fetchUserProfiles();
    userProfilesList = data.users || [];
    updateProfilePillUI();
  } catch (err) {
    console.warn('Could not load user profile:', err);
  }
}

export function updateProfilePillUI() {
  const nameEl = document.getElementById('currentProfileName');
  if (!nameEl) return;
  const user = userProfilesList[0];
  nameEl.textContent = user?.name || 'Личный кабинет';
}
