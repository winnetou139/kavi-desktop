// Metrics & Cost — reports what is measured, and says so when nothing is.
import { api } from '../api.js';
import { el, chip, panel, kv, notice, valueOr, toast } from '../ui.js';
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

  // Execution telemetry and the economic ledger (brief sections 10 and 15).
  let ledgerData = null;
  try { ledgerData = await api.ledger(); } catch (e) { ledgerData = null; }
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

  // ---- Execution telemetry + economic ledger --------------------------
  const L = (ledgerData && ledgerData.ledger) || null;
  const runRows = (ledgerData && ledgerData.runs) || [];
  const ledgerBody = el('div', { class: 'panel-body' });
  if (L) {
    ledgerBody.appendChild(kv([
      ['Runs recorded', String(L.runs ?? 0)],
      ['Succeeded / failed', `${L.succeeded ?? 0} / ${L.failed ?? 0}`],
      ['Success rate', L.success_rate == null
        ? 'NOT MEASURED' : `${Math.round(L.success_rate * 100)}%`],
      ['Active time total', L.active_seconds_total == null
        ? 'NOT MEASURED' : `${L.active_seconds_total}s`],
      ['Active time median', L.active_seconds_median == null
        ? 'NOT MEASURED' : `${L.active_seconds_median}s`],
      ['Tokens', L.tokens_total == null
        ? 'NOT REPORTED by the transport' : String(L.tokens_total)],
      ['Cost basis', L.cost_basis || 'UNKNOWN'],
      ['Cost', L.cost_idr == null ? 'NOT METERED' : String(L.cost_idr)],
      ['Quality scored by KAVI', String(L.quality_scored ?? 0)],
    ]));
    if (runRows.length) {
      const table = el('table', { class: 'tbl' });
      const head = el('tr');
      for (const label of ['Run', 'Adapter', 'Model', 'State', 'Active', 'Trigger']) {
        head.appendChild(el('th', { text: label }));
      }
      table.appendChild(head);
      for (const run of runRows.slice(0, 12)) {
        const row = el('tr');
        row.appendChild(el('td', { text: run.run_id || '—' }));
        row.appendChild(el('td', { text: run.adapter || '—' }));
        row.appendChild(el('td', { text: run.model || 'UNKNOWN' }));
        row.appendChild(el('td', { text: run.state || 'UNKNOWN' }));
        row.appendChild(el('td', { text: run.active_seconds == null
          ? 'NOT MEASURED' : `${run.active_seconds}s` }));
        row.appendChild(el('td', { text: run.trigger || 'UNKNOWN' }));
        table.appendChild(row);
      }
      ledgerBody.appendChild(table);
    } else {
      ledgerBody.appendChild(el('div', { class: 'empty' }, [
        el('b', { text: 'No runs recorded yet' }),
      ]));
    }
    ledgerBody.appendChild(notice(
      L.detail || 'Cost per run is not metered.', 'amber'));
  } else {
    ledgerBody.appendChild(notice('Telemetry is unavailable.', 'amber'));
  }

  host.appendChild(el('div', { class: 'stack' }, [
    panel('Execution telemetry & economic ledger', [], ledgerBody),
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
    evidencePanel(evidenceData),
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

/**
 * Every claim, clickable. Pressing a row reveals the caveat that came with it.
 * A claim without its limitation is how a register quietly becomes misleading,
 * so the caveat is never more than one click away.
 */
function evidencePanel(evidenceData) {
  const claims = evidenceData.evidence || [];
  if (!claims.length) return el('div', {});

  const detail = el('div', { class: 'claim-detail' });
  const showClaim = (claim) => {
    detail.innerHTML = '';
    detail.appendChild(el('div', { class: 'run-head' }, [
      el('span', { class: 'mono', text: claim.id }),
      chip(claim.classification,
        claim.classification === 'FACT' ? 'mint'
          : claim.classification === 'UNKNOWN' ? 'red' : 'amber'),
      claim.confidence ? chip(claim.confidence, 'muted') : null,
      claim.kind ? chip(claim.kind, 'muted') : null,
    ]));
    detail.appendChild(el('div', { class: 'run-detail', text: claim.claim }));
    detail.appendChild(el('table', { class: 'grid' }, [
      el('tbody', {}, [
        claim.source ? kvRow('Source', claim.source) : null,
        claim.source_date ? kvRow('Source date', claim.source_date) : null,
        claim.locator ? kvRow('Locator', claim.locator) : null,
        claim.access_date ? kvRow('Checked on', claim.access_date) : null,
        claim.freshness ? kvRow('Freshness', claim.freshness) : null,
        claim.contradiction
          ? kvRow('Caveat or contradiction', claim.contradiction, 'caveat')
          : kvRow('Caveat or contradiction', 'None recorded.'),
      ].filter(Boolean)),
    ]));
  };

  const table = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'ID' }), el('th', { text: 'Claim' }),
      el('th', { text: 'Class' }), el('th', { text: 'Confidence' }),
      el('th', { text: 'Caveat' }),
    ])]),
    el('tbody', {}, claims.map((claim) => el('tr', {
      class: 'clickable',
      'data-claim': claim.id,
      title: 'Open this claim',
      onclick: () => showClaim(claim),
    }, [
      el('td', {}, [el('span', { class: 'mono', text: claim.id })]),
      el('td', { class: 'claim-text', text: claim.claim }),
      el('td', {}, [chip(claim.classification,
        claim.classification === 'FACT' ? 'mint'
          : claim.classification === 'UNKNOWN' ? 'red' : 'amber')]),
      el('td', {}, [claim.confidence ? chip(claim.confidence, 'muted') : el('span', { text: '—' })]),
      el('td', {}, [claim.contradiction
        ? chip('YES', 'amber')
        : el('span', { class: 'muted', text: '—' })]),
    ]))),
  ]);

  if (claims.length) showClaim(claims[0]);

  return panel(
    `Evidence — every claim (${claims.length})`,
    [chip('CLICK A ROW', 'muted')],
    el('div', {}, [
      el('div', { class: 'claim-scroll' }, [table]),
      detail,
    ]),
  );
}

function kvRow(label, value, cls = '') {
  return el('tr', {}, [
    el('td', { class: 'er-label' }, [el('div', { class: 'er-name', text: label })]),
    el('td', { class: cls, text: String(value) }),
  ]);
}
