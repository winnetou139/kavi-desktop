// Command — Founder objective intake and cockpit overview.
import { api } from '../api.js';
import { el, panel, chip, originChip, toast, valueOr, notice } from '../ui.js';
import { objectiveForm } from './objectives.js';
import { t as tr } from '../i18n.js';

export const meta = {
  id: 'command',
  title: 'Command',
  subtitle: 'Founder objective intake · single company interface',
  group: 'FOUNDER',
  key: '1',
  icon: ['M3 3h8v8H3z', 'M13 3h8v8h-8z', 'M3 13h8v8H3z', 'M13 13h8v8h-8z'],
};

export async function render(host, ctx) {
  const summary = await api.summary();
  ctx.setSummary(summary);

  const stats = [
    { v: summary.inbox.OPEN || 0, l: 'Inbox open', tone: summary.inbox.OPEN ? 'red' : 'mint' },
    { v: summary.objectives.active, l: 'Objectives active', tone: 'mint' },
    { v: summary.tasks.blocked, l: 'Tasks blocked', tone: summary.tasks.blocked ? 'red' : 'muted' },
  ];
  ctx.setHeadStats(stats);

  const input = el('input', {
    id: 'objectiveQuick',
    placeholder: 'Give KAVI an objective — outcome, constraints, evidence required…',
    autocomplete: 'off',
  });
  input.addEventListener('keydown', (event) => {
    event.stopPropagation();
    if (event.key === 'Enter' && input.value.trim()) {
      objectiveForm(ctx, input.value.trim());
      input.value = '';
    }
  });

  const deck = commandDeck(ctx, summary);

  const intake = panel('Objective intake', [
    el('button', {
      class: 'btn primary', type: 'button', text: 'New objective',
      onclick: () => objectiveForm(ctx, input.value.trim()),
    }),
  ], el('div', { class: 'panel-body' }, [
    el('div', { class: 'objective-input' }, [input]),
    el('div', { class: 'hint', style: 'margin-top:10px;color:var(--txt-4);font-size:10px;line-height:1.6' , text:
      'An objective becomes a structured record — owner, sponsor, permission grant, constraints, evidence requirements. It is not a chat message.' }),
  ]));

  const flow = panel('Founder interaction model', [], el('div', {}, [
    briefBlock('mint', 'F', 'Founder handles exceptions',
      'Objectives, decisions, approvals, risks, capital allocation. <b>Not</b> routine task management.'),
    briefBlock('blue', 'K', 'KAVI handles work',
      'Decomposition, delegation, execution, review, retries, evidence collection.'),
    briefBlock('amber', '!', 'Authority stays explicit',
      'Controlled actions require a distinct approver. Founder-reserved actions remain human-approved.'),
  ]));

  const runtime = summary.runtime;
  const kpis = el('div', { class: 'kpi-row' }, [
    kpi(runtime.label, 'Runtime mode', true),
    kpi(runtime.cost_today, 'Cost today', true),
    kpi(String(summary.evidence.total), 'Evidence claims', false),
    kpi(String(summary.evidence.with_contradiction), 'With contradiction', false),
  ]);

  const ventureRows = summary.ventures.map((venture) => el('div', { class: 'brief-block' }, [
    el('div', { style: 'flex:1' }, [
      el('h4', { text: venture.name }),
      el('p', { html: `${venture.stage} · ${venture.gate}` }),
    ]),
    el('div', { style: 'display:flex;gap:6px;align-items:center' }, [
      chip(venture.gate_status), chip(venture.recommendation), originChip(venture.origin),
    ].filter(Boolean)),
  ]));

  host.appendChild(deck);
  host.appendChild(el('div', { class: 'cols-2' }, [
    el('div', { class: 'stack' }, [
      notice(
        '<b>LOCAL / DEVELOPMENT MODE.</b> No autonomous runtime is connected. ' +
        'KAVI Desktop records structured work; it does not execute it. ' +
        'Records marked <b>FIXTURE</b> are development data, not company evidence.',
      ),
      intake,
      flow,
    ]),
    el('div', { class: 'stack' }, [
      kpis,
      panel('Ventures', [], el('div', {}, ventureRows.length ? ventureRows : [
        el('div', { class: 'empty', text: 'No ventures recorded.' }),
      ])),
    ]),
  ]));
}

function briefBlock(tone, glyph, title, html) {
  return el('div', { class: 'brief-block' }, [
    el('div', {
      class: 'brief-ico',
      style: `background:var(--${tone}-dim);color:var(--${tone});border:1px solid var(--${tone}-bd)`,
      text: glyph,
    }),
    el('div', {}, [el('h4', { text: title }), el('p', { html })]),
  ]);
}

function kpi(value, label, small) {
  const node = el('div', { class: 'kpi' });
  const v = el('div', { class: small ? 'v small' : 'v num' });
  v.appendChild(valueOr(value));
  node.appendChild(v);
  node.appendChild(el('div', { class: 'l', text: label }));
  return node;
}

/**
 * Command Deck — one-press actions.
 *
 * Every button here does something real right now. An action that needs a
 * runtime KAVI does not have is shown as unavailable with the reason, rather
 * than as a button that pretends to work. A dead button in a cockpit is worse
 * than no button.
 */
function commandDeck(ctx, summary) {
  const actions = [
    {
      key: 'new-objective',
      en: 'New objective', id: 'Tujuan baru',
      hint: { en: 'Create a structured objective', id: 'Buat tujuan terstruktur' },
      run: () => objectiveForm(ctx),
    },
    {
      key: 'open-decisions',
      en: 'My decisions', id: 'Keputusan saya',
      badge: summary.inbox.OPEN || 0,
      hint: { en: 'Items waiting for you', id: 'Item yang menunggu Anda' },
      run: () => ctx.navigate('inbox'),
    },
    {
      key: 'open-work',
      en: 'Open work', id: 'Pekerjaan berjalan',
      badge: summary.objectives.active || 0,
      hint: { en: 'Objectives and their tasks', id: 'Tujuan dan pekerjaannya' },
      run: () => ctx.navigate('objectives'),
    },
    {
      key: 'venture-state',
      en: 'Venture state', id: 'Status usaha',
      hint: { en: 'Gate position and evidence', id: 'Posisi gate dan bukti' },
      run: () => ctx.navigate('ventures'),
    },
    {
      key: 'search-knowledge',
      en: 'Search knowledge', id: 'Cari pengetahuan',
      hint: { en: 'Read the canonical vault', id: 'Baca vault kanonik' },
      run: () => ctx.navigate('memory'),
    },
    {
      key: 'decision-record',
      en: 'Decision record', id: 'Catatan keputusan',
      hint: { en: 'What has already been decided', id: 'Apa yang sudah diputuskan' },
      run: () => ctx.navigate('decisions'),
    },
    {
      key: 'check-limits',
      en: 'Check limits', id: 'Cek batasan',
      hint: { en: 'What KAVI may not do', id: 'Yang tidak boleh dilakukan KAVI' },
      run: () => ctx.navigate('authority'),
    },
    {
      key: 'run-work',
      en: 'Run work now', id: 'Jalankan sekarang',
      hint: {
        en: 'Needs an execution runtime — none is connected',
        id: 'Butuh runtime eksekusi — belum ada yang terhubung',
      },
      disabled: true,
    },
  ];

  const grid = el('div', { class: 'deck-grid' });
  for (const action of actions) {
    const label = tr('app.close') === 'Tutup' ? action.id : action.en;
    const hint = tr('app.close') === 'Tutup' ? action.hint.id : action.hint.en;

    const button = el('button', {
      class: `deck-btn${action.disabled ? ' is-disabled' : ''}`,
      type: 'button',
      'data-deck': action.key,
      title: hint,
      disabled: action.disabled ? 'disabled' : null,
      onclick: action.disabled ? null : action.run,
    }, [
      el('div', { class: 'deck-row' }, [
        el('span', { class: 'deck-label', text: label }),
        action.badge
          ? el('span', { class: 'deck-badge', text: String(action.badge) })
          : null,
      ]),
      el('span', { class: 'deck-hint', text: hint }),
    ]);
    grid.appendChild(button);
  }

  return panel('Command Deck', [chip(`${actions.filter((a) => !a.disabled).length} ready`, 'mint')],
    el('div', { class: 'panel-body' }, [
      grid,
      el('div', { class: 'deck-foot', text: tr('status.nothingRunning') }),
    ]));
}
