// Local inline SVG icons. No emoji, no external assets.

const P = {
  mission: '<path d="M4 13.5 12 5l8 8.5"/><path d="M6.5 12v7h11v-7"/>',
  intake: '<path d="M5 4.5h9l5 5v10H5z"/><path d="M14 4.5v5h5"/><path d="M8.5 14h7"/><path d="M8.5 17h4.5"/>',
  tasks: '<path d="M6 4.5h12v15H6z"/><path d="M9 8h6"/><path d="M9 11.5h6"/><path d="M9 15h3.5"/>',
  runs: '<path d="M8 5.5v13l10-6.5z"/>',
  evidence: '<path d="M5 7.5h14v11H5z"/><path d="M8 7.5V5h8v2.5"/><path d="M8.5 12h7"/><path d="M8.5 15h4.5"/>',
  devices: '<rect x="4.5" y="5" width="15" height="10" rx="1.5"/><path d="M9 19h6"/><path d="M12 15v4"/>',
  reports: '<path d="M6 4.5h9l3 3v12H6z"/><path d="M9 12h6"/><path d="M9 15.5h6"/><path d="M9 8.5h2.5"/>',
  knowledge: '<path d="M5 5.5 12 8l7-2.5v11L12 19l-7-2.5z"/><path d="M12 8v11"/>',
  runtime: '<circle cx="12" cy="12" r="3"/><path d="M12 4.5v2M12 17.5v2M4.5 12h2M17.5 12h2M6.7 6.7l1.4 1.4M15.9 15.9l1.4 1.4M17.3 6.7l-1.4 1.4M8.1 15.9l-1.4 1.4"/>',
  agents: '<circle cx="9" cy="9" r="2.5"/><circle cx="16" cy="10" r="2"/><path d="M4.5 18c.6-3 2.3-4.5 4.5-4.5s3.9 1.5 4.5 4.5"/><path d="M13.5 18c.4-2.2 1.4-3.4 2.9-3.4 1.4 0 2.4 1.2 2.8 3.4"/>',
  audit: '<path d="M12 4.5 5 7v5c0 3.6 2.6 6.3 7 7.5 4.4-1.2 7-3.9 7-7.5V7z"/><path d="m9 12 2 2 4-4"/>',
  settings: '<circle cx="12" cy="12" r="2.6"/><path d="M12 4.5v2M12 17.5v2M4.5 12h2M17.5 12h2M6.7 6.7l1.4 1.4M15.9 15.9l1.4 1.4M17.3 6.7l-1.4 1.4M8.1 15.9l-1.4 1.4"/>',
  search: '<circle cx="10.5" cy="10.5" r="5.5"/><path d="m14.5 14.5 4 4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M18 6l-1.4 1.4M7.4 16.6 6 18"/>',
  moon: '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  x: '<path d="m7 7 10 10M17 7 7 17"/>',
  alert: '<path d="M12 4.5 3.5 19h17z"/><path d="M12 9v4.5"/><path d="M12 16.5h.01"/>',
  clock: '<circle cx="12" cy="12" r="7.5"/><path d="M12 8v4.5l3 2"/>',
  shield: '<path d="M12 4.5 5 7v5c0 3.6 2.6 6.3 7 7.5 4.4-1.2 7-3.9 7-7.5V7z"/>',
  offline: '<path d="M5 5l14 14"/><path d="M8.5 15.5a5 5 0 0 1 4-2.4"/><path d="M5.5 11.5a9 9 0 0 1 3-1.9"/><path d="M15.5 9.6a9 9 0 0 1 3 .9"/><path d="M12 19h.01"/>',
  refresh: '<path d="M19 12a7 7 0 0 1-12 4.9"/><path d="M5 12a7 7 0 0 1 12-4.9"/><path d="M17 3.5v4h-4"/><path d="M7 20.5v-4h4"/>',
  arrow: '<path d="M5 12h14"/><path d="m14 7 5 5-5 5"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  lock: '<rect x="5" y="10" width="14" height="9" rx="1.5"/><path d="M8 10V7.5a4 4 0 0 1 8 0V10"/>',
  play: '<path d="M8 5.5v13l10-6.5z"/>',
  stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5"/>',
  file: '<path d="M6 4.5h9l3 3v12H6z"/><path d="M14 4.5v4h4"/>',
  link: '<path d="M10 14a3.5 3.5 0 0 0 5 0l3-3a3.5 3.5 0 0 0-5-5l-1 1"/><path d="M14 10a3.5 3.5 0 0 0-5 0l-3 3a3.5 3.5 0 0 0 5 5l1-1"/>',
  info: '<circle cx="12" cy="12" r="7.5"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
  dot: '<circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/>',
  stopwatch: '<circle cx="12" cy="13" r="7"/><path d="M12 9.5V13l2.5 1.5"/><path d="M9 3.5h6"/>',
  layers: '<path d="m12 4 8 4-8 4-8-4z"/><path d="m4 12 8 4 8-4"/><path d="m4 16 8 4 8-4"/>',
  user: '<circle cx="12" cy="8.5" r="3"/><path d="M5.5 19c.8-3.4 3-5 6.5-5s5.7 1.6 6.5 5"/>'
};

export function icon(name, className = "icon") {
  const body = P[name] || P.info;
  return `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}
