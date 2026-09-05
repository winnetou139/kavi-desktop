// Thin transport client. It knows URLs and JSON. Nothing else.

async function request(method, path, body) {
  const options = { method, headers: { Accept: 'application/json' } };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`${response.status} — malformed response`);
  }
  if (!response.ok) throw new Error(payload.error || `${response.status}`);
  return payload;
}

function qs(params) {
  const entries = Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== null && v !== '');
  if (!entries.length) return '';
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
}

export const api = {
  summary: () => request('GET', '/api/summary'),
  runtime: () => request('GET', '/api/runtime'),
  authority: () => request('GET', '/api/authority'),
  storage: () => request('GET', '/api/storage'),

  execution: () => request('GET', '/api/execution'),
  runPrompt: (prompt, timeout) => request('POST', '/api/execution/run', { prompt, timeout }),
  runStatus: (runId) => request('GET', `/api/execution/status${qs({ run_id: runId })}`),

  objectives: () => request('GET', '/api/objectives'),
  objective: (id) => request('GET', `/api/objective${qs({ id })}`),
  createObjective: (payload) => request('POST', '/api/objectives/create', payload),
  transitionObjective: (id, state) => request('POST', '/api/objectives/transition', { id, state }),

  tasks: (objectiveId) => request('GET', `/api/tasks${qs({ objective_id: objectiveId })}`),
  board: (objectiveId) => request('GET', `/api/tasks/board${qs({ objective_id: objectiveId })}`),
  createTask: (payload) => request('POST', '/api/tasks/create', payload),
  transitionTask: (id, state, reason) => request('POST', '/api/tasks/transition', { id, state, reason }),
  dispatchTask: (id) => request('POST', '/api/tasks/dispatch', { id }),

  inbox: () => request('GET', '/api/inbox'),
  createInboxItem: (payload) => request('POST', '/api/inbox/create', payload),
  decideInboxItem: (id, disposition, note) =>
    request('POST', '/api/inbox/decide', { id, disposition, note }),

  ventures: () => request('GET', '/api/ventures'),
  venture: (id) => request('GET', `/api/venture${qs({ id })}`),
  organization: () => request('GET', '/api/organization'),
  memory: (params) => request('GET', `/api/memory${qs(params)}`),
  memoryNote: (path) => request('GET', `/api/memory/note${qs({ path })}`),
  metrics: () => request('GET', '/api/metrics'),
  decisions: () => request('GET', '/api/decisions'),
  evidence: () => request('GET', '/api/evidence'),
};
