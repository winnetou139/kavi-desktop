// Authority & Policy — who may do what, and the runtime that could act.
import { api } from '../api.js';
import { el, chip, originChip, panel, kv, notice } from '../ui.js';

export const meta = {
  id: 'authority',
  title: 'Authority & Policy',
  subtitle: 'Actors · grants · separation of duties · runtime',
  group: 'COMPANY',
  key: '9',
  icon: ['M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
         'M19 12a7 7 0 0 0-.14-1.4l2.1-1.63-2-3.46-2.49 1a7 7 0 0 0-2.42-1.4L13.66 2h-3.32l-.39 2.61a7 7 0 0 0-2.42 1.4l-2.49-1-2 3.46 2.1 1.63A7 7 0 0 0 5 12c0 .48.05.94.14 1.4l-2.1 1.63 2 3.46 2.49-1a7 7 0 0 0 2.42 1.4l.39 2.61h3.32l.39-2.61a7 7 0 0 0 2.42-1.4l2.49 1 2-3.46-2.1-1.63c.09-.46.14-.92.14-1.4z'],
};

export async function render(host, ctx) {
  const authority = await api.authority();
  const runtime = await api.runtime();

  const active = authority.permissions.filter((p) => p.state === 'ACTIVE').length;
  ctx.setHeadStats([
    { v: authority.actors.length, l: 'Actors', tone: 'mint' },
    { v: active, l: 'Active grants', tone: 'mint' },
    { v: authority.pending_approvals.length, l: 'Pending approvals', tone: 'amber' },
  ]);

  const rules = el('div', {});
  for (const rule of authority.rules) {
    rules.appendChild(el('div', {
      style: 'display:flex;gap:10px;padding:9px 16px;border-bottom:1px solid var(--line);font-size:11.5px;color:var(--txt-2);line-height:1.55',
    }, [
      el('span', { style: 'width:5px;height:5px;border-radius:50%;background:var(--amber);margin-top:6px;flex:none' }),
      el('span', { text: rule }),
    ]));
  }

  const grants = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Grant' }), el('th', { text: 'Actor' }), el('th', { text: 'Action' }),
      el('th', { text: 'Resource / scope' }), el('th', { text: 'Budget' }),
      el('th', { text: 'Expiry' }), el('th', { text: 'Approver' }), el('th', { text: 'State' }),
    ])]),
  ]);
  const gbody = el('tbody');
  for (const grant of authority.permissions) {
    gbody.appendChild(el('tr', {}, [
      el('td', {}, [el('span', { class: 'mono', text: grant.id }), ' ', originChip(grant.origin)].filter(Boolean)),
      el('td', { class: 'mono', text: grant.actor_id }),
      el('td', {}, [el('b', { text: grant.action })]),
      el('td', {}, [
        el('div', { text: grant.resource }),
        grant.scope ? el('div', { style: 'color:var(--txt-4);margin-top:3px', text: grant.scope }) : null,
        grant.conditions ? el('div', { style: 'color:var(--txt-4);margin-top:3px', text: grant.conditions }) : null,
      ].filter(Boolean)),
      el('td', { text: grant.budget || '—' }),
      el('td', { text: grant.expiry || '—' }),
      el('td', { class: 'mono', text: grant.approver_id || '—' }),
      el('td', {}, [chip(grant.state)]),
    ]));
  }
  grants.appendChild(gbody);

  const approvals = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Approval' }), el('th', { text: 'Subject' }),
      el('th', { text: 'Approver' }), el('th', { text: 'Reason' }), el('th', { text: 'State' }),
    ])]),
  ]);
  const abody = el('tbody');
  for (const approval of authority.pending_approvals) {
    abody.appendChild(el('tr', {}, [
      el('td', { class: 'mono', text: approval.id }),
      el('td', { class: 'mono', text: approval.subject_id }),
      el('td', { class: 'mono', text: approval.approver_actor_id }),
      el('td', { text: approval.reason || '—' }),
      el('td', {}, [chip(approval.state)]),
    ]));
  }
  if (!authority.pending_approvals.length) {
    abody.appendChild(el('tr', {}, [el('td', { colspan: '5', text: 'No approvals pending.' })]));
  }
  approvals.appendChild(abody);

  const providers = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'Capability' }), el('th', { text: 'Category' }), el('th', { text: 'State' }),
    ])]),
  ]);
  const pbody = el('tbody');
  for (const provider of runtime.providers) {
    pbody.appendChild(el('tr', {}, [
      el('td', {}, [el('b', { text: provider.name })]),
      el('td', { text: provider.category }),
      el('td', {}, [chip(provider.state, 'grey')]),
    ]));
  }
  providers.appendChild(pbody);

  host.appendChild(el('div', { class: 'stack' }, [
    notice(
      `<b>HUMAN AUTHORITY — ${authority.human_authority}.</b> ` +
      `Emergency stop: ${authority.emergency_stop.detail}`,
      'amber',
    ),
    el('div', { class: 'cols-2' }, [
      panel('Permission grants', [], grants),
      el('div', { class: 'stack' }, [
        panel('Separation of duties', [], rules),
        panel('Founder identity', [], el('div', { class: 'panel-body' }, [
          kv([
            ['Name', authority.founder.name],
            ['Kind', chip(authority.founder.kind, 'amber')],
            ['Role', authority.founder.role],
            ['May approve', chip(authority.founder.may_approve ? 'YES' : 'NO', 'mint')],
          ]),
        ])),
      ]),
    ]),
    el('div', { class: 'cols-eq' }, [
      panel('Pending approvals', [], approvals),
      panel('Execution capabilities', [], providers),
    ]),
    panel('Execution adapter', [], el('div', { class: 'panel-body' }, [
      kv([
        ['Adapter', runtime.execution.adapter],
        ['Connected', chip(runtime.execution.connected ? 'YES' : 'NO', runtime.execution.connected ? 'mint' : 'grey')],
        ['State', runtime.execution.state],
        ['Detail', runtime.execution.detail],
      ]),
    ])),
  ]));
}
