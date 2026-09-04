// Organization — organizational abstraction, not a permanent agent roster.
import { api } from '../api.js';
import { el, chip, originChip, panel, notice } from '../ui.js';

export const meta = {
  id: 'organization',
  title: 'Organization',
  subtitle: 'Roles · divisions · actor identities',
  group: 'WORK',
  key: '5',
  icon: ['M12 2.6a2.4 2.4 0 1 0 0 4.8 2.4 2.4 0 0 0 0-4.8z',
         'M5 15.6a2.4 2.4 0 1 0 0 4.8 2.4 2.4 0 0 0 0-4.8z',
         'M19 15.6a2.4 2.4 0 1 0 0 4.8 2.4 2.4 0 0 0 0-4.8z',
         'M12 7.5V12m0 0-5.5 4M12 12l5.5 4'],
};

export async function render(host, ctx) {
  const org = await api.organization();
  const staffed = org.divisions.filter((d) => d.state === 'STAFFED').length;
  ctx.setHeadStats([
    { v: org.divisions.length, l: 'Divisions', tone: 'mint' },
    { v: staffed, l: 'Staffed', tone: staffed ? 'mint' : 'muted' },
  ]);

  const office = el('div', { class: 'org-canvas' }, [
    el('div', { class: 'org-node human' }, [
      el('div', { class: 'role', text: 'Human authority · explicit' }),
      el('div', { class: 'nm', text: 'Founder' }),
    ]),
    el('div', { class: 'org-link' }),
    el('div', { class: 'org-node cos' }, [
      el('div', { class: 'role', text: 'Orchestration' }),
      el('div', { class: 'nm', text: 'KAVI Office · Chief of Staff' }),
    ]),
    el('div', { class: 'org-link' }),
  ]);

  const divisions = el('div', { class: 'org-divs' });
  for (const division of org.divisions) {
    const members = el('div', {}, division.members.map((member) =>
      el('span', { class: 'wk', text: `${member.name} · ${member.kind}` })));
    divisions.appendChild(el('div', { class: `div-card ${division.state === 'STANDBY' ? 'standby' : ''}`.trim() }, [
      el('div', { class: 'code', text: division.code }),
      el('div', { class: 'mand', text: division.mandate }),
      el('div', { style: 'margin-top:8px' }, [chip(division.state)]),
      members,
    ]));
  }
  office.appendChild(divisions);

  const actorRows = el('table', { class: 'grid' }, [
    el('thead', {}, [el('tr', {}, [
      el('th', { text: 'ID' }), el('th', { text: 'Name' }), el('th', { text: 'Kind' }),
      el('th', { text: 'Role' }), el('th', { text: 'May approve' }), el('th', { text: 'Note' }),
    ])]),
  ]);
  const tbody = el('tbody');
  const authority = await api.authority();
  for (const actor of authority.actors) {
    tbody.appendChild(el('tr', {}, [
      el('td', {}, [el('span', { class: 'mono', text: actor.id }), ' ', originChip(actor.origin)].filter(Boolean)),
      el('td', {}, [el('b', { text: actor.name })]),
      el('td', {}, [chip(actor.kind, actorTone(actor.kind))]),
      el('td', { text: actor.role || '—' }),
      el('td', {}, [chip(actor.may_approve ? 'YES' : 'NO', actor.may_approve ? 'mint' : 'grey')]),
      el('td', { text: actor.notes || '' }),
    ]));
  }
  actorRows.appendChild(tbody);

  host.appendChild(el('div', { class: 'stack' }, [
    notice(org.note),
    panel('Organizational structure', [], el('div', { class: 'panel-body' }, [office])),
    panel('Actor identities', [], actorRows),
  ]));
}

function actorTone(kind) {
  if (kind === 'HUMAN') return 'amber';
  if (kind === 'AGENT_INSTANCE') return 'blue';
  if (kind === 'SERVICE_ACCOUNT') return 'violet';
  if (kind === 'PROVIDER' || kind === 'TOOL') return 'grey';
  return 'grey';
}
