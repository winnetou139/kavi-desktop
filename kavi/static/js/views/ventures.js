// Ventures — lifecycle and gate position. KAVI may never advance a gate itself.
import { api } from '../api.js';
import { el, chip, originChip, panel, kv, notice, valueOr, toast } from '../ui.js';

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
      gates.appendChild(el('button', {
        class: `gate ${gate.position}`,
        type: 'button',
        'data-gate': gate.gate,
        title: `${gate.gate} — ${gate.name}`,
        onclick: () => toast(
          `<b>${gate.gate}</b> — ${gate.name}. ` +
          (gate.position === 'current'
            ? `Current gate: <b>${venture.gate_status}</b>. KAVI may not advance it.`
            : gate.position === 'past' ? 'Already passed.' : 'Not reached yet.'),
        ),
      }, [
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
          ['Gate recommendation', chip(venture.recommendation)],
          ['Problem', venture.problem],
          ['Segment', venture.segment],
          ['Commercial evidence', venture.commercial_evidence],
          ['Next required validation', venture.next_validation],
          ['Next Founder decision', venture.next_founder_decision],
        ]),
        bullets('HYPOTHESES', venture.hypotheses, 'mint'),
        bullets('KNOWN EVIDENCE', venture.known_evidence, 'mint'),
        bullets('UNKNOWNS — REQUIRES VALIDATION', venture.unknowns, 'amber'),
        bullets('BLOCKERS', venture.blockers ? [venture.blockers] : [], 'red'),
        el('div', { class: 'detail-label', style: 'margin-top:14px', text: 'NEXT GATE REQUIREMENT' }),
        el('div', { class: 'detail-text', text: venture.next_gate_requirement || '—' }),
      ]),
    ])));
  }

  host.appendChild(stack);
}

/** A labelled bullet list, omitted entirely when there is nothing to show. */
function bullets(label, items, tone) {
  if (!items || !items.length) return null;
  return el('div', { class: 'venture-bullets', 'data-group': label }, [
    el('div', { class: 'detail-label', text: label }),
    el('ul', { class: `bullet-list tone-${tone}` },
      items.map((item) => el('li', { text: item }))),
  ]);
}
