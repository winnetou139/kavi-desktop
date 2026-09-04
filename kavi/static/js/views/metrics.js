// Metrics & Cost — reports what is measured, and says so when nothing is.
import { api } from '../api.js';
import { el, chip, panel, kv, notice, valueOr } from '../ui.js';

export const meta = {
  id: 'metrics',
  title: 'Metrics & Cost',
  subtitle: 'Company economics · runtime economics',
  group: 'COMPANY',
  key: '7',
  icon: ['M3 17l5.5-6 4 3L21 5', 'M15 5h6v6'],
};

export async function render(host, ctx) {
  const metrics = await api.metrics();
  const evidence = metrics.evidence;

  ctx.setHeadStats([
    { v: metrics.work.objectives_total, l: 'Objectives', tone: 'mint' },
    { v: metrics.work.tasks_open, l: 'Tasks open', tone: 'mint' },
    { v: metrics.work.tasks_blocked, l: 'Blocked', tone: metrics.work.tasks_blocked ? 'red' : 'muted' },
    { v: evidence.total, l: 'Evidence', tone: 'mint' },
  ]);

  const classRows = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Classification' }), el('th', { text: 'Count' }),
    ])]),
  ]);
  const tbody = el('tbody');
  for (const [name, count] of Object.entries(evidence.by_classification)) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, [chip(name)]),
      el('td', { class: 'num', text: String(count) }),
    ]));
  }
  tbody.appendChild(el('tr', {}, [
    el('td', {}, [el('b', { text: 'With contradiction preserved' })]),
    el('td', { class: 'num', text: String(evidence.with_contradiction) }),
  ]));
  classRows.appendChild(tbody);

  const recordRows = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Collection' }), el('th', { text: 'Fixture' }),
      el('th', { text: 'Local' }), el('th', { text: 'Total' }),
    ])]),
  ]);
  const rbody = el('tbody');
  for (const [name, counts] of Object.entries(metrics.records)) {
    rbody.appendChild(el('tr', {}, [
      el('td', {}, [el('b', { text: name })]),
      el('td', { class: 'num', text: String(counts.fixture) }),
      el('td', { class: 'num', text: String(counts.local) }),
      el('td', { class: 'num', text: String(counts.total) }),
    ]));
  }
  recordRows.appendChild(rbody);

  host.appendChild(el('div', { class: 'stack' }, [
    notice(
      '<b>No commercial figure exists.</b> Revenue, cost-to-serve and provider cost are ' +
      'unmeasured in LOCAL MODE. Fixture records must never be counted as company evidence.',
      'amber',
    ),
    el('div', { class: 'cols-eq' }, [
      panel('Runtime economics', [], el('div', { class: 'panel-body' }, [
        kv([
          ['Mode', metrics.runtime.mode],
          ['Cost today', metrics.runtime.cost_today],
          ['Uptime', metrics.runtime.uptime],
          ['Queue depth', metrics.runtime.queue_depth],
        ]),
        el('div', {
          style: 'margin-top:12px;font-family:var(--mono);font-size:10px;color:var(--txt-4);line-height:1.6',
          text: metrics.runtime.detail,
        }),
      ])),
      panel('Company economics', [], el('div', { class: 'panel-body' }, [
        kv([
          ['Revenue', metrics.commercial.revenue],
          ['Venture spend', metrics.commercial.venture_spend],
          ['Provider cost', metrics.commercial.provider_cost],
        ]),
        el('div', {
          style: 'margin-top:12px;font-family:var(--mono);font-size:10px;color:var(--txt-4);line-height:1.6',
          text: metrics.commercial.detail,
        }),
      ])),
    ]),
    el('div', { class: 'cols-eq' }, [
      panel('Evidence classification', [], classRows),
      panel('Record origin', [], recordRows),
    ]),
  ]));
}
