// Ventures — lifecycle and gate position. KAVI may never advance a gate itself.
import { api } from '../api.js';
import { el, chip, originChip, panel, kv, notice, valueOr } from '../ui.js';

export const meta = {
  id: 'ventures',
  title: 'Ventures',
  subtitle: 'Venture lifecycle · phase gates · evidence',
  group: 'WORK',
  key: '4',
  icon: ['M4 20V9', 'M9.3 20V4', 'M15.9 20v-9', 'M21 20V7'],
};

export async function render(host, ctx) {
  const { ventures } = await api.ventures();
  ctx.setHeadStats([{ v: ventures.length, l: 'Ventures', tone: 'mint' }]);

  if (!ventures.length) {
    host.appendChild(el('div', { class: 'empty' }, [el('b', { text: 'No ventures recorded' })]));
    return;
  }

  const stack = el('div', { class: 'stack' });
  stack.appendChild(notice(
    'KAVI may not approve a gate. Gate advancement requires explicit Founder approval.',
    'amber',
  ));

  for (const venture of ventures) {
    const gates = el('div', { class: 'gates' });
    for (const gate of venture.gates || []) {
      gates.appendChild(el('div', { class: `gate ${gate.position}` }, [
        gate.position === 'current'
          ? el('div', { class: 'marker', text: venture.gate_status })
          : null,
        el('div', { class: 'node' }, [
          el('div', { class: 'gid', text: gate.gate }),
          el('div', { class: 'gname', text: gate.name }),
        ]),
      ]));
    }

    stack.appendChild(panel(venture.name, [
      chip(venture.stage), chip(venture.gate_status), chip(venture.recommendation),
      originChip(venture.origin),
    ].filter(Boolean), el('div', {}, [
      gates,
      el('div', { class: 'panel-body', style: 'border-top:1px solid var(--line)' }, [
        kv([
          ['Current stage', chip(venture.stage)],
          ['Current gate', venture.gate],
          ['Gate status', chip(venture.gate_status)],
          ['Recommendation', chip(venture.recommendation)],
          ['Problem', venture.problem],
          ['Segment', venture.segment],
          ['Commercial evidence', venture.commercial_evidence],
          ['Blockers', venture.blockers],
          ['Next gate requirement', venture.next_gate_requirement],
          ['Next Founder decision', venture.next_founder_decision],
        ]),
      ]),
    ])));
  }

  host.appendChild(stack);
}
