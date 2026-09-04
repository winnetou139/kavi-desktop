// Command — Founder objective intake and cockpit overview.
import { api } from '../api.js';
import { el, panel, chip, originChip, toast, valueOr, notice } from '../ui.js';
import { objectiveForm } from './objectives.js';

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
