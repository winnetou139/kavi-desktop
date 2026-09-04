// CEO Inbox — an aggregation of Founder-level items.
//
// Every item points at a real underlying object: Objective, Task, Decision,
// Venture or Approval. This view resolves and displays that reference, and lets
// the Founder dispose of LOCAL items. Fixture items are decision-locked on
// purpose: deciding demo data would create a false operational impression.
//
// Dispositions update local state only. No external action occurs in v0.1.

import { api } from '../api.js';
import {
  el, chip, originChip, empty, notice, toast, confirmModal, panel,
} from '../ui.js';
import { t as tr } from '../i18n.js';

export const meta = {
  id: 'inbox',
  title: 'CEO Inbox',
  subtitle: 'Founder-level items · aggregated from real objects',
  group: 'FOUNDER',
  key: '2',
  icon: ['M3 7h18v10H3z', 'M3 7l9 6 9-6'],
};

const TYPE_TONE = {
  DECISION: 'gold', APPROVAL: 'amber', RISK: 'red',
  OPPORTUNITY: 'green', FYI: 'muted',
};
const RISK_TONE = { HIGH: 'red', MEDIUM: 'amber', LOW: 'muted' };
const STATE_TONE = {
  OPEN: 'gold', APPROVED: 'green', REJECTED: 'red',
  DEFERRED: 'muted', EVIDENCE_REQUESTED: 'amber', ACKNOWLEDGED: 'muted',
};

const DISPOSITIONS = [
  ['APPROVED', 'inbox.approve'],
  ['REJECTED', 'inbox.reject'],
  ['DEFERRED', 'inbox.defer'],
  ['EVIDENCE_REQUESTED', 'inbox.askEvidence'],
];

let selectedId = null;

export async function render(host, ctx) {
  const data = await api.inbox();
  const items = data.items || [];
  const counts = data.counts || {};

  host.appendChild(el('div', { class: 'stat-row' }, [
    stat(tr('inbox.open').toUpperCase(), counts.OPEN ?? 0),
    stat('DECISION', counts.DECISION ?? 0),
    stat('APPROVAL', counts.APPROVAL ?? 0),
    stat('RISK', counts.RISK ?? 0),
    stat('OPPORTUNITY', counts.OPPORTUNITY ?? 0),
  ]));

  if (!items.length) {
    host.appendChild(empty(tr('inbox.empty'), tr('inbox.emptyHint')));
    return;
  }

  if (!selectedId || !items.some((i) => i.id === selectedId)) selectedId = items[0].id;

  const detailHost = el('div', { class: 'inbox-detail' });
  const listHost = el('div', { class: 'inbox-list' });

  const draw = () => {
    listHost.innerHTML = '';
    items.forEach((item) => {
      listHost.appendChild(el('button', {
        class: `inbox-row${item.id === selectedId ? ' active' : ''}`,
        type: 'button',
        'data-inbox-id': item.id,
        onclick: () => { selectedId = item.id; draw(); drawDetail(); },
      }, [
        el('div', { class: 'inbox-row-top' }, [
          chip(item.type, TYPE_TONE[item.type]),
          chip(item.state, STATE_TONE[item.state]),
          item.origin === 'FIXTURE' ? originChip('FIXTURE') : null,
        ]),
        el('div', { class: 'inbox-row-title', text: item.title }),
        el('div', { class: 'inbox-row-meta' }, [
          item.subject_id ? el('span', { class: 'mono', text: item.subject_id }) : null,
          el('span', { text: (item.created_at || '').slice(0, 10) }),
        ]),
      ]));
    });
  };

  const drawDetail = () => {
    detailHost.innerHTML = '';
    const item = items.find((i) => i.id === selectedId);
    if (item) detailHost.appendChild(detailFor(item, ctx));
  };

  draw();
  drawDetail();
  host.appendChild(el('div', { class: 'inbox-split' }, [listHost, detailHost]));
}

function detailFor(item, ctx) {
  const rows = [];

  rows.push(el('div', { class: 'detail-head' }, [
    el('div', { class: 'mono muted', text: item.id }),
    el('h2', { class: 'detail-title', text: item.title }),
    el('div', { class: 'chip-row' }, [
      chip(item.type, TYPE_TONE[item.type]),
      chip(`RISK ${item.risk}`, RISK_TONE[item.risk]),
      chip(item.state, STATE_TONE[item.state]),
      item.origin === 'FIXTURE' ? originChip('FIXTURE') : null,
    ]),
  ]));

  // The real underlying object this item refers to.
  const subject = item.subject;
  rows.push(el('div', { class: 'detail-block' }, [
    el('div', { class: 'detail-label', text: tr('inbox.about').toUpperCase() }),
    subject
      ? el('div', { class: 'subject-ref' }, [
          chip(subject.kind, 'muted'),
          el('span', { class: 'mono', text: subject.id }),
          subject.found
            ? el('span', { class: 'subject-title', text: subject.title })
            : el('span', { class: 'subject-missing', text: subject.detail || 'not found' }),
          subject.found && subject.state ? chip(subject.state, 'muted') : null,
        ])
      : notice('This item does not reference an underlying object.', 'warn'),
  ]));

  if (item.recommendation) {
    rows.push(block(tr('inbox.recommendation').toUpperCase(), el('p', { class: 'detail-text', text: item.recommendation })));
  }

  const evidence = item.evidence || [];
  if (evidence.length) {
    rows.push(block(`${tr('inbox.evidence').toUpperCase()} (${evidence.length})`, el('div', { class: 'evidence-list' },
      evidence.map((e) => el('div', { class: 'evidence-row' }, [
        el('div', { class: 'evidence-head' }, [
          el('span', { class: 'mono', text: e.id }),
          chip(e.classification,
            e.classification === 'FACT' ? 'green' : e.classification === 'UNKNOWN' ? 'red' : 'amber'),
          e.confidence ? chip(e.confidence, 'muted') : null,
        ]),
        el('div', { class: 'evidence-claim', text: e.claim }),
        e.source ? el('div', { class: 'evidence-source', text: e.source }) : null,
      ])),
    )));
  }

  if (item.authority_note) {
    rows.push(block(tr('inbox.authority').toUpperCase(), notice(item.authority_note)));
  }

  if (item.decided_at) {
    rows.push(block(tr('inbox.decided').toUpperCase(), el('div', {}, [
      el('div', { class: 'detail-text', text: `${item.state} · ${(item.decided_at || '').slice(0, 16).replace('T', ' ')}` }),
      item.disposition_note ? el('p', { class: 'detail-text', text: item.disposition_note }) : null,
    ])));
  }

  rows.push(actionsFor(item, ctx));
  return el('div', { class: 'detail' }, rows);
}

function actionsFor(item, ctx) {
  if (item.origin === 'FIXTURE') {
    return el('div', { class: 'detail-block' }, [
      notice(tr('inbox.demoLocked'), 'warn'),
    ]);
  }
  if (!['OPEN', 'DEFERRED', 'EVIDENCE_REQUESTED'].includes(item.state)) {
    return el('div', { class: 'detail-block' }, [
      notice(`${tr('inbox.closed')} (${item.state})`),
    ]);
  }

  const buttons = DISPOSITIONS
    .filter(([key]) => key !== item.state)
    .map(([key, labelKey]) => {
      const label = tr(labelKey);
      return el('button', {
      class: key === 'APPROVED' ? 'btn primary' : 'btn ghost',
      type: 'button',
      'data-disposition': key,
      text: label,
      onclick: async () => {
        const note = await confirmModal({
          title: `${label} — ${item.id}`,
          body: item.title,
          fieldLabel: 'Reason',
          confirmLabel: label,
        });
        if (note === null) return;
        try {
          await api.decideInboxItem(item.id, key, note);
          toast(`<b>${item.id}</b> → ${key}`);
          ctx.navigate('inbox');
        } catch (error) {
          toast(error.message, 'err');
        }
      },
    });
    });

  return el('div', { class: 'detail-block' }, [
    el('div', { class: 'detail-label', text: tr('inbox.yourDecision').toUpperCase() }),
    el('div', { class: 'btn-row' }, buttons),
    el('div', { class: 'detail-foot', text: tr('inbox.localOnly') }),
  ]);
}

function block(label, node) {
  return el('div', { class: 'detail-block' }, [
    el('div', { class: 'detail-label', text: label }),
    node,
  ]);
}

function stat(label, value) {
  return el('div', { class: 'stat' }, [
    el('div', { class: 'stat-value', text: String(value) }),
    el('div', { class: 'stat-label', text: label }),
  ]);
}
