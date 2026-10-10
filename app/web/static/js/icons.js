/**
 * SVG Icons registry and category icon mapper.
 */

export const SVG_ICONS = {
  // Accounts
  card: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="5" width="20" height="14" rx="2"></rect><line x1="2" y1="10" x2="22" y2="10"></line></svg>`,
  cash: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="6" width="20" height="12" rx="2"></rect><circle cx="12" cy="12" r="3"></circle><path d="M6 12h.01M18 12h.01"></path></svg>`,
  bank: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M3 21h18M3 10h18M5 10v11M9 10v11M15 10v11M19 10v11M12 3l9 7H3l9-7z"></path></svg>`,
  crypto: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="9"></circle><path d="M12 6v12M9 9h6M9 15h6"></path></svg>`,

  // Actions & General
  income: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`,
  expense: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2.5" fill="none"><path d="M12 5v14M5 12l7 7 7-7"/></svg>`,
  transfer: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M17 1 21 5 17 9"></path><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><path d="M7 23 3 19 7 15"></path><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>`,
  target: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>`,
  debt: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>`,
  user: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,

  // Categories
  work: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>`,
  design: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"></circle><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"></circle><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"></circle><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"></circle><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"></path></svg>`,
  dev: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`,
  sales: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>`,
  gift: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><polyline points="20 12 20 22 4 22 4 12"></polyline><rect x="2" y="7" width="20" height="5"></rect><line x1="12" y1="22" x2="12" y2="7"></line><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"></path><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"></path></svg>`,
  food: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>`,
  transport: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>`,
  clothes: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10c0 1.1.9 2 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"></path></svg>`,
  tech: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>`,
  games: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><line x1="6" y1="12" x2="10" y2="12"></line><line x1="8" y1="10" x2="8" y2="14"></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line x1="18" y1="11" x2="18.01" y2="11"></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg>`,
  study: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`,
  home: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`,
  mobile: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>`,
  other: `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>`,
};

export function getCategoryIcon(nameOrKey) {
  if (!nameOrKey) return SVG_ICONS.other;
  const str = nameOrKey.toString().toLowerCase();

  if (str.includes('работ') || str.includes('work') || str.includes('job') || str.includes('зарплат') || str.includes('💼')) return SVG_ICONS.work;
  if (str.includes('дизайн') || str.includes('design') || str.includes('art') || str.includes('🎨')) return SVG_ICONS.design;
  if (str.includes('програм') || str.includes('dev') || str.includes('code') || str.includes('it') || str.includes('💻')) return SVG_ICONS.dev;
  if (str.includes('продаж') || str.includes('sale') || str.includes('бизнес') || str.includes('🛒')) return SVG_ICONS.sales;
  if (str.includes('подар') || str.includes('gift') || str.includes('🎁')) return SVG_ICONS.gift;
  if (str.includes('ед') || str.includes('продукт') || str.includes('food') || str.includes('кафе') || str.includes('ресторан') || str.includes('🍔')) return SVG_ICONS.food;
  if (str.includes('транспорт') || str.includes('такси') || str.includes('car') || str.includes('авто') || str.includes('бензин') || str.includes('🚕')) return SVG_ICONS.transport;
  if (str.includes('одежд') || str.includes('clothes') || str.includes('вещи') || str.includes('обувь') || str.includes('👕')) return SVG_ICONS.clothes;
  if (str.includes('техник') || str.includes('tech') || str.includes('гаджет') || str.includes('ноутбук') || str.includes('телефон')) return SVG_ICONS.tech;
  if (str.includes('игр') || str.includes('game') || str.includes('развлечен') || str.includes('кино') || str.includes('🎮')) return SVG_ICONS.games;
  if (str.includes('учеб') || str.includes('study') || str.includes('курс') || str.includes('книг') || str.includes('образован') || str.includes('📚')) return SVG_ICONS.study;
  if (str.includes('дом') || str.includes('home') || str.includes('аренд') || str.includes('квартир') || str.includes('коммунал') || str.includes('🏠')) return SVG_ICONS.home;
  if (str.includes('связ') || str.includes('интернет') || str.includes('mobile') || str.includes('phone') || str.includes('📱')) return SVG_ICONS.mobile;
  if (str.includes('карт') || str.includes('card') || str.includes('💳')) return SVG_ICONS.card;
  if (str.includes('налич') || str.includes('cash') || str.includes('💵')) return SVG_ICONS.cash;
  if (str.includes('банк') || str.includes('bank') || str.includes('🏦')) return SVG_ICONS.bank;
  if (str.includes('крипт') || str.includes('валют') || str.includes('coin') || str.includes('🪙')) return SVG_ICONS.crypto;

  return SVG_ICONS[nameOrKey] || SVG_ICONS.other;
}

export function getIconHTML(iconStr) {
  return getCategoryIcon(iconStr);
}
