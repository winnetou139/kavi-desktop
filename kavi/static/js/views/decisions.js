// Decision Log — canonical decisions, read from the KAVI Vault.
//
// The vault owns decisions (D-005). This view reads 08_DECISIONS/ and never
// writes. Fields the record does not state are shown as blank rather than
// filled with a plausible guess: a decision record is exactly where invention
// does the most damage.

import { api } from '../api.js';
import { el, clear, chip, originChip, panel, kv, notice, empty } from '../ui.js';

export const meta = {
  id: 'decisions',
  title: 'Decision Log',
  subtitle: 'Canonical decisions · read from the vault',
  group: 'COMPANY',
  key: '8',
  icon: ['M6 4h9l5 5v11H6z', 'M15 4v5h5', 'M9 13h7', 'M9 17h5'],
};

const STATE_TONE = {
  APPROVED: 'mint',
  PROPOSED: 'amber',
  REJECTED: 'red',
  SUPERSEDED: 'muted',
  UNKNOWN: 'amber',
};

let openId = null;

export async function render(host, ctx) {
  const data = await api.decisions();
  const decisions = data.decisions || [];
  const status = data.status || {};

  ctx.setHeadStats([
    { v: decisions.length, l: 'Decisions', tone: 'mint' },
    { v: decisions.filter((d) => d.state === 'APPROVED').length, l: 'Approved', tone: 'mint' },
    { v: status.source || 'UNKNOWN', l: 'Source', tone: 'amber' },
  ]);

  const stack = el('div', { class: 'stack' });

  stack.appendChild(notice(
    `<b>${status.source || 'UNKNOWN'}</b> — ${status.detail || ''}<br>`
    + `<span class="mono">${status.path || ''}</span><br>`
    + `Access is <b>${status.access || 'READ ONLY'}</b>. `
    + 'No decision shown here was authored by the desktop.',
    'amber',
  ));

  if (!decisions.length) {
    stack.appendChild(empty(
      'No canonical decision could be read.',
      'The vault was not reachable. Nothing has been substituted in its place.',
    ));
    host.appendChild(stack);
    return;
  }

  const table = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'ID' }), el('th', { text: 'Title' }),
      el('th', { text: 'State' }), el('th', { text: 'Date' }),
      el('th', { text: 'Approver' }), el('th', { text: 'Reversible' }),
      el('th', { text: 'Source' }),
    ])]),
  ]);

  const tbody = el('tbody');
  const detailHost = el('div', {});

  const drawDetail = () => {
    clear(detailHost);
    const decision = decisions.find((d) => d.id === openId);
    if (!decision) return;
    detailHost.appendChild(panel(
      `${decision.id} — ${decision.title}`,
      [chip(decision.state, STATE_TONE[decision.state] || 'muted'), originChip(decision.origin)],
      el('div', { class: 'panel-body' }, [
        kv([
          ['Decision', decision.decision],
          ['Context', decision.context],
          ['Why', decision.rationale],
          ['Evidence basis', decision.evidence_ids],
          ['Alternatives considered', decision.alternatives],
          ['Consequences', decision.consequences],
          ['Reversible?', decision.reversible],
          ['Review date', decision.review_date],
          ['Supersedes', decision.supersedes || '—'],
          ['Owner', decision.owner_actor_id],
          ['Approver', decision.approver_actor_id],
          ['Read from', decision.source_path],
        ].filter(([, value]) => String(value || '').trim() !== '')),
      ]),
    ));
  };

  decisions.forEach((decision) => {
    const row = el('tr', {
      class: `clickable${decision.id === openId ? ' sel' : ''}`,
      'data-decision-id': decision.id,
      onclick: () => {
        openId = decision.id === openId ? null : decision.id;
        ctx.reload();
      },
    }, [
      el('td', {}, [el('span', { class: 'mono', text: decision.id })]),
      el('td', { text: decision.title }),
      el('td', {}, [chip(decision.state, STATE_TONE[decision.state] || 'muted')]),
      el('td', { class: 'mono', text: decision.date || '—' }),
      el('td', { text: decision.approver_actor_id || '—' }),
      el('td', { class: 'reversible', text: decision.reversible || '—' }),
      el('td', {}, [originChip(decision.origin)]),
    ]);
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  stack.appendChild(panel('Canonical decisions', [chip('READ ONLY', 'amber')], table));
  drawDetail();
  stack.appendChild(detailHost);
  host.appendChild(stack);
}
