// Decision Log — canonical decision records.
import { api } from '../api.js';
import { el, chip, originChip, panel, notice } from '../ui.js';

export const meta = {
  id: 'decisions',
  title: 'Decision Log',
  subtitle: 'Proposed · approved · rejected · superseded',
  group: 'COMPANY',
  key: '8',
  icon: ['M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z', 'M12 8v4l3 2'],
};

export async function render(host, ctx) {
  const { decisions } = await api.decisions();
  const approved = decisions.filter((d) => d.state === 'APPROVED').length;
  ctx.setHeadStats([
    { v: decisions.length, l: 'Decisions', tone: 'mint' },
    { v: approved, l: 'Approved', tone: 'mint' },
  ]);

  if (!decisions.length) {
    host.appendChild(el('div', { class: 'empty' }, [el('b', { text: 'No decisions recorded' })]));
    return;
  }

  const table = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'ID' }), el('th', { text: 'Decision' }),
      el('th', { text: 'State' }), el('th', { text: 'Approver' }),
      el('th', { text: 'Date' }), el('th', { text: 'Reversible' }),
    ])]),
  ]);
  const tbody = el('tbody');
  for (const decision of decisions) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, [
        el('span', { class: 'mono', style: 'color:var(--violet);font-weight:600', text: decision.id }),
        ' ', originChip(decision.origin),
      ].filter(Boolean)),
      el('td', {}, [
        el('b', { text: decision.title }),
        decision.consequences
          ? el('div', { style: 'margin-top:4px;color:var(--txt-2)', text: decision.consequences })
          : null,
      ].filter(Boolean)),
      el('td', {}, [chip(decision.state)]),
      el('td', { class: 'mono', text: decision.approver_actor_id || '—' }),
      el('td', { class: 'mono', text: decision.date || '—' }),
      el('td', { text: decision.reversible || '—' }),
    ]));
  }
  table.appendChild(tbody);

  host.appendChild(el('div', { class: 'stack' }, [
    notice(
      'Decision records are canonical in the KAVI Vault. This screen is a read view; ' +
      'a decision changes meaning only through supersession, never silent overwrite.',
      'blue',
    ),
    panel('Decision records', [], table),
  ]));
}
