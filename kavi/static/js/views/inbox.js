// CEO Inbox — what genuinely requires Founder attention.
import { api } from '../api.js';
import { el, clear, chip, originChip, panel, toast, valueOr } from '../ui.js';

export const meta = {
  id: 'inbox',
  title: 'CEO Inbox',
  subtitle: 'Decisions · approvals · risks · opportunities',
  group: 'FOUNDER',
  key: '2',
  icon: ['M3 13h4l2 3h6l2-3h4', 'M4 5h16l1 8v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-5l1-8z'],
};

export async function render(host, ctx) {
  const { items, counts } = await api.inbox();
  ctx.setHeadStats([
    { v: counts.DECISION || 0, l: 'Decision', tone: 'violet' },
    { v: counts.APPROVAL || 0, l: 'Approval', tone: 'amber' },
    { v: counts.RISK || 0, l: 'Risk', tone: counts.RISK ? 'red' : 'muted' },
    { v: counts.OPEN || 0, l: 'Open', tone: 'mint' },
  ]);

  if (!items.length) {
    host.appendChild(el('div', { class: 'empty' }, [
      el('b', { text: 'Inbox empty' }),
      el('div', { text: 'Nothing currently requires Founder attention.' }),
    ]));
    return;
  }

  const list = el('div', { class: 'inbox-list' });
  const detail = el('div', { class: 'inbox-detail' });

  let selected = items[0].id;
  const draw = () => {
    clear(list);
    for (const item of items) {
      list.appendChild(el('button', {
        class: `inbox-item ${item.id === selected ? 'sel' : ''}`.trim(),
        type: 'button',
        onclick: () => { selected = item.id; draw(); },
      }, [
        el('div', { class: 'row1' }, [
          chip(item.type), chip(item.risk), originChip(item.origin),
        ].filter(Boolean)),
        el('h4', { text: item.title }),
        el('div', { class: 'meta', text: `${item.id}${item.objective_id ? ' · ' + item.objective_id : ''}` }),
      ]));
    }
    drawDetail(detail, items.find((i) => i.id === selected));
  };

  draw();
  host.appendChild(el('div', { class: 'screen-split' }, [list, detail]));
}

function drawDetail(host, item) {
  clear(host);
  if (!item) return;

  host.appendChild(el('div', { class: 'detail-kicker' }, [
    chip(item.type), chip(item.risk), originChip(item.origin),
  ].filter(Boolean)));
  host.appendChild(el('div', { class: 'detail-title', text: item.title }));
  host.appendChild(el('div', {
    class: 'detail-meta',
    text: `${item.id}${item.objective_id ? ' · ' + item.objective_id : ''} · ${item.created_at || ''}`,
  }));

  host.appendChild(section('Recommendation',
    el('div', { class: 'reco-box', text: item.recommendation || '—' })));

  const evidence = item.evidence || [];
  const evList = el('div', { class: 'ev-list' });
  if (!evidence.length) {
    evList.appendChild(el('div', { class: 'ev' }, [
      el('span', { class: 'unknown', text: 'NO EVIDENCE ATTACHED' }),
    ]));
  }
  for (const claim of evidence) {
    const tone = claim.classification === 'FACT' ? 'mint'
      : claim.classification === 'INFERENCE' ? 'blue'
      : claim.classification === 'HYPOTHESIS' ? 'amber' : 'grey';
    const row = el('div', { class: 'ev' }, [
      el('span', {
        class: 'tag',
        style: `background:var(--${tone}-dim);color:var(--${tone})`,
        text: claim.classification,
      }),
      el('div', {}, [
        el('div', { text: claim.claim }),
        el('div', {
          style: 'margin-top:5px;font-family:var(--mono);font-size:9.5px;color:var(--txt-4)',
          text: [claim.source, claim.source_date, `confidence ${claim.confidence}`]
            .filter(Boolean).join(' · '),
        }),
        claim.contradiction
          ? el('span', { class: 'contra', text: `Contradiction: ${claim.contradiction}` })
          : null,
      ]),
    ]);
    evList.appendChild(row);
  }
  host.appendChild(section('Evidence trail', evList));

  if (item.authority_note) {
    host.appendChild(section('Authority condition',
      el('div', { class: 'reco-box', style: 'border-left-color:var(--amber)', text: item.authority_note })));
  }

  const actions = el('div', { class: 'action-row' });
  for (const [label, cls] of [['Approve', 'primary'], ['Reject', 'danger'], ['Defer', ''], ['Ask Chief of Staff', 'ghost']]) {
    actions.appendChild(el('button', {
      class: `btn ${cls}`.trim(),
      type: 'button',
      disabled: 'disabled',
      title: 'Inbox decisioning is not implemented in v0.1. These records are fixture data.',
      text: label,
    }));
  }
  host.appendChild(actions);
  host.appendChild(el('div', {
    style: 'margin-top:10px;font-family:var(--mono);font-size:9.5px;color:var(--txt-4);line-height:1.6',
    text: 'Decisioning is deferred in v0.1. Actions are disabled rather than simulated.',
  }));
}

function section(label, body) {
  return el('div', { class: 'detail-sec' }, [el('div', { class: 'sl', text: label }), body]);
}
