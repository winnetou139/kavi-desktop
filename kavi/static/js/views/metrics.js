// Metrics & Cost — reports what is measured, and says so when nothing is.
import { api } from '../api.js';
import { el, chip, panel, kv, notice, valueOr } from '../ui.js';
import { t as tr } from '../i18n.js';

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
  const runtime = await api.runtime();
  const storage = await api.storage();
  const evidenceData = await api.evidence();
  const evidence = metrics.evidence;
  const evStatus = evidenceData.status || {};
  const evSummary = evidenceData.summary || {};

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
  // D-006: these classes may never be cited as external market validation.
  tbody.appendChild(el('tr', {}, [
    el('td', {}, [el('b', { text: 'Not external market validation' })]),
    el('td', { class: 'num', text: String(evSummary.non_market_claims ?? '—') }),
  ]));
  classRows.appendChild(tbody);

  const confidenceRows = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Confidence' }), el('th', { text: 'Claims' }),
    ])]),
    el('tbody', {}, Object.entries(evSummary.by_confidence || {}).map(([name, count]) =>
      el('tr', {}, [
        el('td', {}, [chip(name, name === 'HIGH' ? 'mint' : name === 'LOW' ? 'red' : 'amber')]),
        el('td', { class: 'num', text: String(count) }),
      ]))),
  ]);

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

  // The Engine Room readout. Every line reports what is actually true.
  // Each technical key gets a plain-language label. The value itself is a
  // governed term and is never translated.
  const ENGINE_LABELS = {
    MODE: 'status.mode',
    VPS: 'status.server',
    RUNTIME: 'status.mode',
    SCHEDULER: 'status.scheduler',
    QUEUE: 'status.queue',
    'PROVIDER ROUTER': 'status.router',
    VAULT: 'status.vault',
    COST: 'status.cost',
  };
  const engineRoom = el('table', { class: 'grid engine-room' }, [
    el('tbody', {}, (runtime.engine_room_panel || []).map(([label, value]) => el('tr', {}, [
      el('td', { class: 'er-label' }, [
        el('div', { class: 'er-name', text: tr(ENGINE_LABELS[label] || '', label) }),
        el('div', { class: 'er-key mono', text: label }),
      ]),
      el('td', { class: 'er-value' }, [chip(value, toneForRuntime(value))]),
    ]))),
  ]);

  const providerRows = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Provider' }), el('th', { text: 'Category' }), el('th', { text: 'State' }),
    ])]),
    el('tbody', {}, (runtime.providers || []).map((prov) => el('tr', {}, [
      el('td', {}, [el('b', { text: prov.name })]),
      el('td', { class: 'muted', text: prov.category }),
      el('td', {}, [chip(prov.state, 'muted')]),
    ]))),
  ]);

  host.appendChild(el('div', { class: 'stack' }, [
    panel('Engine Room', [chip(runtime.label, 'amber')], el('div', { class: 'panel-body' }, [
      engineRoom,
      el('div', { class: 'engine-room-note' },
        (runtime.warnings || []).map((w) => el('div', { text: w }))),
    ])),
    panel('Providers', [], providerRows),
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
    panel('Evidence register', [
      chip(evStatus.source || 'UNKNOWN', 'mint'), chip('READ ONLY', 'amber'),
    ], el('div', { class: 'panel-body' }, [
      notice(
        `<b>${evStatus.claim_count ?? 0} canonical claims</b> read from `
        + `<span class="mono">${evStatus.path || '—'}</span>.<br>`
        + `${evStatus.detail || ''}`
        + (evStatus.scope_limit ? `<br><b>Scope limit:</b> ${evStatus.scope_limit}` : ''),
        'amber',
      ),
      el('div', { class: 'cols-eq' }, [classRows, confidenceRows]),
    ])),
    panel('Record origin', [], recordRows),
    panel('Where state is stored', [], el('div', { class: 'panel-body' }, [
      kv([
        ['Local operational store', storage.operational_store.path],
        ['Format', storage.operational_store.format],
        ['Canonical for', storage.operational_store.canonical_for],
        ['Canonical vault', storage.canonical_vault.path || 'NOT LOCATED'],
        ['Vault canonical for', storage.canonical_vault.canonical_for],
        ['Vault access', storage.canonical_vault.access || 'READ ONLY'],
      ]),
      notice(storage.separation_rule),
    ])),
  ]));
}

function toneForRuntime(value) {
  const v = String(value).toUpperCase();
  if (v.includes('NOT CONNECTED') || v.includes('NOT ACTIVE')) return 'amber';
  if (v.includes('UNAVAILABLE') || v.includes('NOT MEASURED')) return 'amber';
  return 'muted';
}
