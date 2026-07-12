/** TickTick-style outline icons for Empire planning nav */
(function () {
  const S = 'stroke="currentColor" fill="none" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"';

  const ICONS = {
    today(day) {
      const d = String(day || new Date().getDate());
      return `<svg viewBox="0 0 24 24" ${S}><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/><text x="12" y="18" text-anchor="middle" fill="currentColor" stroke="none" font-size="8" font-weight="700" font-family="system-ui,sans-serif">${d}</text></svg>`;
    },
    week() {
      return `<svg viewBox="0 0 24 24" ${S}><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/><text x="12" y="18" text-anchor="middle" fill="currentColor" stroke="none" font-size="7.5" font-weight="700" font-family="system-ui,sans-serif">7</text></svg>`;
    },
    matrix() {
      return `<svg viewBox="0 0 24 24" ${S}><rect x="3" y="3" width="8" height="8" rx="1.5"/><rect x="13" y="3" width="8" height="8" rx="1.5"/><rect x="3" y="13" width="8" height="8" rx="1.5"/><rect x="13" y="13" width="8" height="8" rx="1.5"/></svg>`;
    },
    inbox() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 4h16v4l-2 3H10L8 8H4V4z"/><path d="M8 11v7h8v-7"/></svg>`;
    },
    search() {
      return `<svg viewBox="0 0 24 24" ${S}><circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/></svg>`;
    },
    calendar() {
      return `<svg viewBox="0 0 24 24" ${S}><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M8 2v4M16 2v4M3 10h18"/><path d="M8 14h2M14 14h2M8 18h2M14 18h2"/></svg>`;
    },
    lists() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M9 6h12M9 12h12M9 18h12"/><path d="M5 6l1.5 1.5L7 6M5 12l1.5 1.5L7 12M5 18l1.5 1.5L7 18"/></svg>`;
    },
    finance() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 18V6l8-3 8 3v12l-8 3-8-3z"/><path d="M12 9v10M8.5 10.5 12 9l3.5 1.5"/></svg>`;
    },
    insights() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M12 3l1.8 4.5L18 9l-4.2 1.5L12 15l-1.8-4.5L6 9l4.2-1.5L12 3z"/><path d="M5 19c2-1 4-1.5 7-1.5s5 .5 7 1.5"/></svg>`;
    },
    stats() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M5 19V9M12 19V5M19 19v-7"/></svg>`;
    },
    history() {
      return `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/><path d="M8 4 5 7l3 2"/></svg>`;
    },
    projects() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z"/></svg>`;
    },
    health() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M12 21s-6-4.5-8.2-8.5C2.2 9.5 4 6 7.5 6c2 0 3.2 1.2 4.5 2.8C13.3 7.2 14.5 6 16.5 6 20 6 21.8 9.5 20.2 12.5 18 16.5 12 21 12 21z"/></svg>`;
    },
    measurements() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 20 20 4"/><path d="M7 17l2-2M11 13l2-2M15 9l2-2"/></svg>`;
    },
    workouts() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M6 9h2v6H6zM16 9h2v6h-2z"/><path d="M8 12h8"/><path d="M4 10v4M20 10v4"/></svg>`;
    },
    program() {
      return `<svg viewBox="0 0 24 24" ${S}><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>`;
    },
    "health-stats"() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 14c2-4 4-6 8-6s6 2 8 6"/><circle cx="12" cy="8" r="2.5"/></svg>`;
    },
    settings() {
      return `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="12" r="3"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>`;
    },
    bell() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M12 3a5 5 0 0 0-5 5v3l-2 3h14l-2-3V8a5 5 0 0 0-5-5z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>`;
    },
    import() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M12 4v10"/><path d="M8 10l4 4 4-4"/><path d="M5 18h14"/></svg>`;
    },
    refresh() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M20 12a8 8 0 1 1-2.3-5.7"/><path d="M20 4v5h-5"/></svg>`;
    },
    tag() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M5 5h6l8 8-6 6-8-8V5z"/><circle cx="9" cy="9" r="1.5" fill="currentColor" stroke="none"/></svg>`;
    },
    flag() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M6 4v16M6 4h10l-2 4 2 4H6"/></svg>`;
    },
    add() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M12 5v14M5 12h14"/></svg>`;
    },
    back() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M15 6l-6 6 6 6"/></svg>`;
    },
    menu() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 7h16M4 12h16M4 17h16"/></svg>`;
    },
    overflow() {
      return `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="6" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="18" r="1.5" fill="currentColor" stroke="none"/></svg>`;
    },
    pipeline() {
      return `<svg viewBox="0 0 24 24" ${S}><path d="M4 6h6v4H4zM14 6h6v4h-6zM9 14h6v4H9z"/><path d="M10 10v2M14 12H12v2"/></svg>`;
    },
  };

  function svg(name, opts = {}) {
    const fn = ICONS[name];
    if (!fn) return "";
    return typeof fn === "function" ? fn(opts.day) : fn;
  }

  function badge(name, opts = {}) {
    return `<span class="nav-icon nav-icon--${name}" aria-hidden="true">${svg(name, opts)}</span>`;
  }

  function rail(name, opts = {}) {
    return `<span class="rail-icon rail-icon--${name}" aria-hidden="true">${svg(name, opts)}</span>`;
  }

  window.NavIcons = { svg, badge, rail, names: Object.keys(ICONS) };
})();
