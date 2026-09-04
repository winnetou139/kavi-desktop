// KAVI Desktop shell: rail, router, palette, statusbar, keyboard.
import { api } from './api.js';
import { el, clear, svg, toast, chip } from './ui.js';

import * as command from './views/command.js';
import * as inbox from './views/inbox.js';
import * as objectives from './views/objectives.js';
import * as ventures from './views/ventures.js';
import * as organization from './views/organization.js';
import * as memory from './views/memory.js';
import * as metrics from './views/metrics.js';
import * as decisions from './views/decisions.js';
import * as authority from './views/authority.js';

const VIEWS = [command, inbox, objectives, ventures, organization, memory, metrics, decisions, authority];
const BY_ID = Object.fromEntries(VIEWS.map((v) => [v.meta.id, v]));
const BY_KEY = Object.fromEntries(VIEWS.map((v) => [v.meta.key, v.meta.id]));

const state = { current: 'command', summary: null };

const mainHost = document.getElementById('main');
const railHost = document.getElementById('rail');

const ctx = {
  navigate,
  reload: () => navigate(state.current, { silent: true }),
  setSummary: (summary) => { state.summary = summary; drawRail(); drawStatusbar(summary.runtime); },
  setHeadStats: (stats) => { pendingStats = stats; },
  setHeadActions: (nodes) => { pendingActions = nodes; },
};

let pendingStats = [];
let pendingActions = [];

// ------------------------------------------------------------------- rail

function drawRail() {
  clear(railHost);
  const groups = ['FOUNDER', 'WORK', 'COMPANY'];
  for (const group of groups) {
    railHost.appendChild(el('div', { class: 'rail-sec', text: group }));
    for (const view of VIEWS.filter((v) => v.meta.group === group)) {
      const item = el('button', {
        class: `nav-item ${view.meta.id === state.current ? 'active' : ''}`.trim(),
        type: 'button',
        onclick: () => navigate(view.meta.id),
      }, [svg(view.meta.icon), el('span', { text: view.meta.title })]);

      const badge = badgeFor(view.meta.id);
      item.appendChild(badge || el('span', { class: 'nav-key', text: view.meta.key }));
      railHost.appendChild(item);
    }
  }

  const founder = state.summary ? state.summary.founder : { name: 'Founder', role: 'CEO · Approver' };
  railHost.appendChild(el('div', { class: 'rail-foot' }, [
    el('div', { class: 'founder' }, [
      el('div', { class: 'avatar', text: (founder.name || 'F').slice(0, 1).toUpperCase() }),
      el('div', {}, [
        el('div', { class: 'founder-name', text: founder.name || 'Founder' }),
        el('div', { class: 'founder-role', text: founder.role || 'CEO · Approver' }),
      ]),
    ]),
    el('div', { class: 'auth-chip' }, [
      el('span', { text: 'HUMAN AUTHORITY' }),
      el('b', { text: 'EXPLICIT' }),
    ]),
  ]));
}

function badgeFor(id) {
  if (!state.summary) return null;
  if (id === 'inbox') {
    const open = state.summary.inbox.OPEN || 0;
    return open ? el('span', { class: 'nav-badge', text: String(open) }) : null;
  }
  if (id === 'ventures') {
    const venture = state.summary.ventures[0];
    if (!venture) return null;
    const gate = String(venture.gate).split(' ')[0];
    return el('span', { class: 'nav-badge amber', text: gate });
  }
  if (id === 'objectives') {
    const blocked = state.summary.tasks.blocked;
    return blocked ? el('span', { class: 'nav-badge', text: String(blocked) }) : null;
  }
  return null;
}

// ------------------------------------------------------------- statusbar

function drawStatusbar(runtime) {
  const bar = clear(document.getElementById('statusbar'));
  const off = (label, value) => el('span', {}, [
    el('span', { text: label + ' ' }),
    el('b', { class: 'off', text: value }),
  ]);
  bar.appendChild(el('span', { class: 'wr', text: '◐ ' + runtime.label }));
  bar.appendChild(el('span', { class: 'sep' }));
  bar.appendChild(off('SCHEDULER', runtime.scheduler));
  bar.appendChild(el('span', { class: 'sep' }));
  bar.appendChild(off('QUEUE', runtime.queue_depth));
  bar.appendChild(el('span', { class: 'sep' }));
  bar.appendChild(off('ROUTER', runtime.router));
  bar.appendChild(el('span', { class: 'sep' }));
  bar.appendChild(off('VAULT SYNC', runtime.vault_sync));

  const right = el('div', { class: 'right' }, [
    off('UPTIME', runtime.uptime),
    el('span', { class: 'sep' }),
    off('COST TODAY', runtime.cost_today),
    el('span', { class: 'sep' }),
    el('span', { text: 'KAVI Desktop v0.1.0 · LOCAL' }),
  ]);
  bar.appendChild(right);

  const pill = document.getElementById('modePill');
  clear(pill);
  pill.appendChild(el('span', { class: 'dot' }));
  pill.appendChild(el('span', { text: runtime.label }));
}

// ------------------------------------------------------------------ router

async function navigate(id, options = {}) {
  const view = BY_ID[id];
  if (!view) return;
  state.current = id;
  pendingStats = [];
  pendingActions = [];
  drawRail();

  clear(mainHost);
  const screen = el('div', { class: 'screen' });
  const head = el('div', { class: 'screen-head' }, [
    el('div', {}, [
      el('div', { class: 'screen-title', text: view.meta.title }),
      el('div', { class: 'screen-sub', text: view.meta.subtitle }),
    ]),
  ]);
  screen.appendChild(head);
  mainHost.appendChild(screen);

  const isSplit = ['inbox', 'memory'].includes(id);
  const body = el('div', { class: isSplit ? 'screen-split' : 'screen-body' });
  screen.appendChild(body);

  try {
    await view.render(body, ctx);
  } catch (error) {
    clear(body);
    body.appendChild(el('div', { class: 'empty' }, [
      el('b', { text: 'Could not load this screen' }),
      el('div', { text: error.message }),
    ]));
  }

  if (pendingStats.length || pendingActions.length) {
    const stats = el('div', { class: 'head-stats' });
    for (const stat of pendingStats) {
      stats.appendChild(el('div', { class: 'hstat' }, [
        el('div', { class: `v ${stat.tone || ''}`.trim(), text: String(stat.v) }),
        el('div', { class: 'l', text: stat.l }),
      ]));
    }
    for (const action of pendingActions) stats.appendChild(action);
    head.appendChild(stats);
  }
}

// ----------------------------------------------------------------- palette

const veil = document.getElementById('paletteVeil');
const paletteInput = document.getElementById('paletteInput');
const paletteBody = document.getElementById('paletteBody');

function drawPalette(filter = '') {
  clear(paletteBody);
  const needle = filter.trim().toLowerCase();
  const matches = VIEWS.filter((v) => !needle || v.meta.title.toLowerCase().includes(needle));

  if (needle && !matches.length) {
    paletteBody.appendChild(el('div', { class: 'palette-sec', text: 'Create' }));
    paletteBody.appendChild(el('button', {
      class: 'pal-item hl', type: 'button',
      onclick: () => { closePalette(); objectives.objectiveForm(ctx, filter.trim()); },
    }, [el('span', { text: `Draft objective: "${filter.trim()}"` }), el('span', { class: 'k', text: 'OBJ' })]));
    return;
  }

  paletteBody.appendChild(el('div', { class: 'palette-sec', text: 'Create' }));
  paletteBody.appendChild(el('button', {
    class: 'pal-item', type: 'button',
    onclick: () => { closePalette(); objectives.objectiveForm(ctx, paletteInput.value.trim()); },
  }, [el('span', { text: 'New objective' }), el('span', { class: 'k', text: 'OBJ' })]));

  paletteBody.appendChild(el('div', { class: 'palette-sec', text: 'Jump to' }));
  for (const view of matches) {
    paletteBody.appendChild(el('button', {
      class: 'pal-item', type: 'button',
      onclick: () => { closePalette(); navigate(view.meta.id); },
    }, [el('span', { text: view.meta.title }), el('span', { class: 'k', text: view.meta.key })]));
  }
}

function openPalette() {
  veil.classList.add('on');
  paletteInput.value = '';
  drawPalette();
  setTimeout(() => paletteInput.focus(), 30);
}

function closePalette() { veil.classList.remove('on'); }

paletteInput.addEventListener('input', () => drawPalette(paletteInput.value));
paletteInput.addEventListener('keydown', (event) => {
  event.stopPropagation();
  if (event.key === 'Escape') closePalette();
  if (event.key === 'Enter') {
    const first = paletteBody.querySelector('.pal-item');
    if (first) first.click();
  }
});
veil.addEventListener('click', (event) => { if (event.target === veil) closePalette(); });
document.getElementById('cmdkBtn').addEventListener('click', openPalette);

document.getElementById('modalVeil').addEventListener('click', (event) => {
  if (event.target.id === 'modalVeil') event.target.classList.remove('on');
});

// ---------------------------------------------------------------- keyboard

document.addEventListener('keydown', (event) => {
  const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    openPalette();
    return;
  }
  if (event.key === 'Escape') {
    closePalette();
    document.getElementById('modalVeil').classList.remove('on');
    return;
  }
  if (typing) return;
  if (veil.classList.contains('on')) return;
  if (document.getElementById('modalVeil').classList.contains('on')) return;
  if (BY_KEY[event.key]) {
    event.preventDefault();
    navigate(BY_KEY[event.key]);
  }
});

// ------------------------------------------------------------------- clock

function tick() {
  document.getElementById('clock').textContent = new Date().toLocaleTimeString();
}
tick();
setInterval(tick, 1000);

// -------------------------------------------------------------------- boot

(async function boot() {
  try {
    const summary = await api.summary();
    ctx.setSummary(summary);
  } catch (error) {
    toast(`Could not reach the KAVI service: ${error.message}`, 'err');
  }
  drawRail();
  await navigate('command');
})();
