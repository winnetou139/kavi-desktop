// Objectives & Tasks — a view over the Work/Task Kernel. Never a source of truth.
import { api } from '../api.js';
import {
  el, clear, chip, originChip, panel, toast, valueOr, openModal, closeModal,
  field, input, textarea, select, kv, notice,
} from '../ui.js';

export const meta = {
  id: 'objectives',
  title: 'Objectives & Tasks',
  subtitle: 'Structured work · governed state transitions',
  group: 'WORK',
  key: '3',
  icon: ['M9 6h12M9 12h12M9 18h12', 'M4.5 4.6v2.8', 'M4.5 10.6v2.8', 'M4.5 16.6v2.8'],
};

let selectedObjective = null;

export async function render(host, ctx) {
  const { objectives } = await api.objectives();
  ctx.setHeadStats([
    { v: objectives.length, l: 'Objectives', tone: 'mint' },
    { v: objectives.filter((o) => o.state === 'ACTIVE').length, l: 'Active', tone: 'mint' },
  ]);
  ctx.setHeadActions([
    el('button', { class: 'btn primary', type: 'button', text: 'New objective', onclick: () => objectiveForm(ctx) }),
  ]);

  if (!objectives.length) {
    host.appendChild(el('div', { class: 'empty' }, [
      el('b', { text: 'No objectives yet' }),
      el('div', { text: 'Press Ctrl+K or use New objective to create one.' }),
    ]));
    return;
  }

  if (!objectives.some((o) => o.id === selectedObjective)) {
    selectedObjective = objectives[0].id;
  }

  const strip = el('div', { class: 'obj-strip' });
  const detailHost = el('div', { class: 'stack' });

  const drawStrip = () => {
    clear(strip);
    for (const objective of objectives) {
      strip.appendChild(el('button', {
        class: `obj-card ${objective.id === selectedObjective ? 'sel' : ''}`.trim(),
        type: 'button',
        onclick: () => { selectedObjective = objective.id; drawStrip(); drawDetail(); },
      }, [
        el('div', { class: 'id', text: objective.id }),
        el('h4', { text: objective.title }),
        el('div', { class: 'prog' }, [
          el('i', { style: `width:${objective.progress === null ? 0 : objective.progress}%` }),
        ]),
        el('div', { class: 'foot' }, [
          el('span', { text: objective.progress === null ? 'NOT MEASURED' : `${objective.progress}%` }),
          el('span', { text: `${objective.task_done}/${objective.task_count} tasks` }),
        ]),
        el('div', { style: 'display:flex;gap:6px;margin-top:8px' }, [
          chip(objective.state), originChip(objective.origin),
        ].filter(Boolean)),
      ]));
    }
  };

  const drawDetail = async () => {
    clear(detailHost);
    const objective = await api.objective(selectedObjective);
    const board = await api.board(selectedObjective);

    const actions = [];
    if (objective.origin !== 'FIXTURE') {
      for (const target of transitionsFor(objective.state)) {
        actions.push(el('button', {
          class: 'btn sm', type: 'button', text: target,
          onclick: async () => {
            try {
              await api.transitionObjective(objective.id, target);
              toast(`Objective ${objective.id} → <b>${target}</b>`);
              ctx.reload();
            } catch (error) { toast(error.message, 'err'); }
          },
        }));
      }
      actions.push(el('button', {
        class: 'btn sm', type: 'button', text: 'Raise to CEO Inbox',
        'data-action': 'raise-inbox',
        onclick: () => raiseForm(ctx, objective),
      }));
      actions.push(el('button', {
        class: 'btn sm primary', type: 'button', text: 'Add task',
        onclick: () => taskForm(ctx, objective.id),
      }));
    }

    detailHost.appendChild(panel(`${objective.id} — governed record`, actions,
      el('div', { class: 'panel-body' }, [
        objective.origin === 'FIXTURE'
          ? notice('This objective is <b>development fixture data</b>. It cannot be modified and is not company evidence.')
          : null,
        kv([
          ['Outcome', objective.outcome],
          ['State', chip(objective.state)],
          ['Owner', objective.owner_actor_id],
          ['Sponsor', objective.sponsor_actor_id],
          ['Permission grant', objective.permission_grant_id],
          ['Constraints', objective.constraints],
          ['Evidence required', objective.evidence_requirements],
          ['Budget', objective.budget],
          ['Actual cost', objective.actual_cost],
          ['Venture', objective.venture_id],
        ]),
      ])));

    const columns = board.columns.filter((c) => c.tasks.length > 0 || !c.terminal);
    const boardNode = el('div', { class: 'board' });
    for (const column of columns) {
      const body = el('div', { class: 'col-body' });
      for (const task of column.tasks) {
        body.appendChild(el('button', {
          class: 'tcard', type: 'button',
          onclick: () => taskDetail(ctx, task),
        }, [
          el('div', { class: 'tid', text: task.id }),
          el('h5', { text: task.title }),
          el('div', { class: 'tags' }, [originChip(task.origin)].filter(Boolean)),
        ]));
      }
      boardNode.appendChild(el('div', { class: `col s-${column.state}` }, [
        el('div', { class: 'col-head' }, [
          el('span', { text: column.state }),
          el('span', { class: 'cnt', text: String(column.tasks.length) }),
        ]),
        body,
      ]));
    }
    detailHost.appendChild(panel('Task board · Work State Model', [], boardNode));
  };

  drawStrip();
  await drawDetail();
  host.appendChild(el('div', { class: 'stack' }, [strip, detailHost]));
}

const OBJECTIVE_TRANSITIONS = {
  DRAFT: ['ACTIVE', 'CANCELLED'],
  ACTIVE: ['PAUSED', 'COMPLETED', 'CANCELLED'],
  PAUSED: ['ACTIVE', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: [],
};

const TASK_TRANSITIONS = {
  BACKLOG: ['READY', 'CANCELLED'],
  READY: ['RUNNING', 'BLOCKED', 'CANCELLED'],
  RUNNING: ['REVIEW', 'BLOCKED', 'FAILED', 'READY', 'CANCELLED', 'KILLED'],
  BLOCKED: ['READY', 'CANCELLED', 'KILLED'],
  REVIEW: ['APPROVAL', 'READY', 'FAILED', 'CANCELLED'],
  APPROVAL: ['DONE', 'READY', 'BLOCKED', 'CANCELLED'],
  DONE: [], FAILED: [], CANCELLED: [], KILLED: [],
};

function transitionsFor(state) {
  return OBJECTIVE_TRANSITIONS[state] || [];
}

export function objectiveForm(ctx, prefill = '') {
  const titleInput = input('title', 'What outcome must be achieved?');
  titleInput.value = prefill;
  const body = el('div', {}, [
    notice('An objective is a governed record. The fields below map to the approved Objective contract.'),
    field('Title', titleInput),
    field('Outcome required', textarea('outcome', 'What must be true when this is complete?')),
    el('div', { class: 'form-grid' }, [
      field('Owner actor ID', input('owner_actor_id', 'ACT-…')),
      field('Sponsor actor ID', input('sponsor_actor_id', 'ACT-…')),
      field('Priority', select('priority', ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'], 'NORMAL')),
      field('Authority level', select('authority_level', ['A0', 'A1', 'A2'], 'A0'),
        'A3 and A4 are not grantable in LOCAL MODE.'),
      field('Permission grant ID', input('permission_grant_id', 'GNT-…')),
      field('Budget', input('budget', 'e.g. 0 external spend')),
      field('Deadline', input('deadline', 'YYYY-MM-DD')),
      field('Venture ID', input('venture_id', 'VEN-…')),
    ]),
    field('Success criteria', textarea('success_criteria', 'How will you know this succeeded?')),
    field('Constraints', textarea('constraints', 'What may this objective NOT do?')),
    field('Evidence requirements', textarea('evidence_requirements', 'What evidence standard applies?')),
    field('Initial state', select('state', ['DRAFT', 'ACTIVE'], 'DRAFT'),
      'DRAFT records the objective. ACTIVE starts it.'),
  ]);

  openModal('New objective', body, [
    el('button', { class: 'btn ghost', type: 'button', text: 'Cancel', onclick: closeModal }),
    el('button', {
      class: 'btn primary', type: 'button', text: 'Create objective',
      onclick: async () => {
        const payload = collect(body);
        try {
          const created = await api.createObjective(payload);
          closeModal();
          selectedObjective = created.id;
          toast(`Objective <b>${created.id}</b> created.`);
          ctx.navigate('objectives');
        } catch (error) { toast(error.message, 'err'); }
      },
    }),
  ]);
}

function taskForm(ctx, objectiveId) {
  const body = el('div', {}, [
    field('Title', input('title', 'What bounded work is required?')),
    field('Expected output', textarea('expected_output', 'What artifact or answer must this produce?')),
    el('div', { class: 'form-grid' }, [
      field('Assignee actor ID', input('assignee_actor_id', 'ACT-…')),
      field('Assigned role', input('assigned_role_id', 'ROLE-…')),
      field('Priority', select('priority', ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'], 'NORMAL')),
      field('Authority level', select('authority_level', ['A0', 'A1', 'A2'], 'A0')),
      field('Permission grant ID', input('permission_grant_id', 'GNT-…')),
      field('Depends on', input('depends_on', 'TASK-…, TASK-…'),
        'Comma separated. A task cannot run until these are DONE.'),
    ]),
    field('Evidence requirement', textarea('evidence_requirement', 'What evidence must this produce?')),
    el('div', { class: 'form-grid' }, [
      field('Review required', select('review_required', ['false', 'true'], 'false')),
      field('Approval required', select('approval_required', ['false', 'true'], 'false')),
    ]),
  ]);
  openModal(`New task under ${objectiveId}`, body, [
    el('button', { class: 'btn ghost', type: 'button', text: 'Cancel', onclick: closeModal }),
    el('button', {
      class: 'btn primary', type: 'button', text: 'Create task',
      onclick: async () => {
        try {
          const created = await api.createTask({ ...collect(body), objective_id: objectiveId });
          closeModal();
          toast(`Task <b>${created.id}</b> created in BACKLOG.`);
          ctx.reload();
        } catch (error) { toast(error.message, 'err'); }
      },
    }),
  ]);
}

function taskDetail(ctx, task) {
  const body = el('div', {}, [
    task.origin === 'FIXTURE'
      ? notice('This task is <b>development fixture data</b> and cannot be modified.')
      : null,
    kv([
      ['State', chip(task.state)],
      ['Objective', task.objective_id],
      ['Parent task', task.parent_task_id],
      ['Assignee', task.assignee_actor_id],
      ['Assigned role', task.assigned_role_id],
      ['Permission grant', task.permission_grant_id],
      ['Expected output', task.expected_output],
      ['Priority', task.priority],
      ['Authority level', task.authority_level],
      ['Depends on', task.depends_on],
      ['Evidence requirement', task.evidence_requirement],
      ['Review required', task.review_required ? 'YES' : 'NO'],
      ['Approval required', task.approval_required ? 'YES' : 'NO'],
      ['Created at', task.created_at],
      ['Updated at', task.updated_at],
      ['Estimated cost', task.estimated_cost],
      ['Actual cost', task.actual_cost],
      ['Idempotency key', task.idempotency_key],
      ['Retry policy', task.retry_policy],
      ['Failure reason', task.failure_reason],
      ['Started at', task.started_at],
      ['Completed at', task.completed_at],
    ]),
  ]);

  const actions = [el('button', { class: 'btn ghost', type: 'button', text: 'Close', onclick: closeModal })];
  actions.push(el('button', {
    class: 'btn', type: 'button', text: 'Dispatch to runtime',
    onclick: async () => {
      const result = await api.dispatchTask(task.id);
      toast(`<b>${result.state}</b> — ${result.detail}`, 'warn');
    },
  }));
  if (task.origin !== 'FIXTURE') {
    for (const target of (TASK_TRANSITIONS[task.state] || [])) {
      actions.push(el('button', {
        class: 'btn sm', type: 'button', text: `→ ${target}`,
        onclick: async () => {
          try {
            await api.transitionTask(task.id, target, '');
            closeModal();
            toast(`Task ${task.id} → <b>${target}</b>`);
            ctx.reload();
          } catch (error) { toast(error.message, 'err'); }
        },
      }));
    }
  }
  openModal(`${task.id} — ${task.title}`, body, actions);
}

function collect(scope) {
  const payload = {};
  for (const node of scope.querySelectorAll('input[name],textarea[name],select[name]')) {
    payload[node.name] = node.value;
  }
  return payload;
}


/**
 * Raise a Founder-level item from this objective into the CEO Inbox.
 *
 * The inbox is an aggregation, so the item stores a reference to the real
 * object rather than a copy of it. Nothing is sent anywhere; this writes local
 * state only.
 */
function raiseForm(ctx, objective) {
  const body = el('div', {}, [
    notice(
      `This raises a Founder-level item referencing <b>${objective.id}</b>. `
      + 'The inbox stores the reference, not a copy. No external action is taken.',
    ),
    el('div', { class: 'form-grid' }, [
      field('Type', select('type', ['DECISION', 'APPROVAL', 'RISK', 'OPPORTUNITY', 'FYI'], 'DECISION')),
      field('Risk', select('risk', ['LOW', 'MEDIUM', 'HIGH'], 'MEDIUM')),
    ]),
    field('Title', input('title', `Review required: ${objective.title}`)),
    field('Recommendation', textarea('recommendation', 'What are you recommending the Founder do?')),
    field('Authority note', textarea('authority_note', 'What authority applies? What is reversible?')),
  ]);

  openModal(`Raise to CEO Inbox — ${objective.id}`, body, [
    el('button', { class: 'btn ghost', type: 'button', text: 'Cancel', onclick: closeModal }),
    el('button', {
      class: 'btn primary', type: 'button', text: 'Raise item',
      onclick: async () => {
        try {
          const created = await api.createInboxItem({
            ...collect(body),
            subject_kind: 'OBJECTIVE',
            subject_id: objective.id,
          });
          closeModal();
          toast(`Inbox item <b>${created.id}</b> raised from ${objective.id}.`);
          ctx.navigate('inbox');
        } catch (error) { toast(error.message, 'err'); }
      },
    }),
  ]);
}
