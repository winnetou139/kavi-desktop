// DOM helpers and shared UI atoms. No domain logic lives in this file.

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'text') node.textContent = value;
    else if (key === 'html') node.innerHTML = value;
    else if (key.startsWith('on') && typeof value === 'function') {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, value);
  }
  const list = Array.isArray(children) ? children : [children];
  for (const child of list) {
    if (child === null || child === undefined || child === false) continue;
    node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return node;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
  return node;
}

export function svg(paths, size = 15) {
  const ns = 'http://www.w3.org/2000/svg';
  const root = document.createElementNS(ns, 'svg');
  root.setAttribute('viewBox', '0 0 24 24');
  root.setAttribute('fill', 'none');
  root.setAttribute('stroke', 'currentColor');
  root.setAttribute('stroke-width', '1.8');
  root.setAttribute('width', String(size));
  root.setAttribute('height', String(size));
  root.setAttribute('aria-hidden', 'true');
  for (const d of paths) {
    const p = document.createElementNS(ns, 'path');
    p.setAttribute('d', d);
    root.appendChild(p);
  }
  return root;
}

// ---------------------------------------------------------------- chips

const STATE_TONE = {
  // task
  BACKLOG: 'grey', READY: 'grey', RUNNING: 'blue', BLOCKED: 'red',
  REVIEW: 'violet', APPROVAL: 'amber', DONE: 'mint', FAILED: 'red',
  CANCELLED: 'grey', KILLED: 'red',
  // objective
  DRAFT: 'grey', ACTIVE: 'mint', PAUSED: 'amber', COMPLETED: 'mint',
  // decision / approval
  PROPOSED: 'amber', APPROVED: 'mint', REJECTED: 'red', SUPERSEDED: 'grey',
  PENDING: 'amber', EXPIRED: 'grey', REVOKED: 'red',
  // evidence
  FACT: 'mint', INFERENCE: 'blue', HYPOTHESIS: 'amber', UNKNOWN: 'grey',
  // review
  PASS: 'mint', PASS_WITH_CONDITIONS: 'amber', FAIL: 'red',
  // inbox
  DECISION: 'violet', RISK: 'red', OPPORTUNITY: 'mint', FYI: 'grey',
  // misc
  HIGH: 'red', MEDIUM: 'amber', LOW: 'grey',
  'NOT PASSED': 'amber', PASSED: 'mint',
  CONTINUE: 'mint', INVESTIGATE: 'amber', KILL: 'red', SCALE: 'mint',
  STAFFED: 'mint', STANDBY: 'grey',
};

export function toneFor(value) {
  return STATE_TONE[String(value || '').toUpperCase()] || 'grey';
}

export function chip(text, tone) {
  return el('span', { class: `chip ${tone || toneFor(text)}`, text: String(text) });
}

/** Origin chip. FIXTURE data must always be visibly labelled. */
export function originChip(origin) {
  if (origin !== 'FIXTURE') return null;
  return el('span', { class: 'chip amber', text: 'FIXTURE', title: 'Development fixture data — not company evidence' });
}

export function unknown(text = 'UNKNOWN / REQUIRES VALIDATION') {
  return el('span', { class: 'unknown', text });
}

/** Render a value, or an explicit not-available marker. Never render a blank. */
export function valueOr(value, fallback = 'NOT RECORDED') {
  const str = value === null || value === undefined ? '' : String(value).trim();
  if (!str) return unknown(fallback);
  if (str.startsWith('UNKNOWN') || str === 'NOT MEASURED' || str === 'NOT CONNECTED') {
    return unknown(str);
  }
  return document.createTextNode(str);
}

export function panel(title, rightNodes, bodyNode) {
  const head = el('div', { class: 'panel-head' }, [el('span', { text: title })]);
  if (rightNodes && rightNodes.length) {
    head.appendChild(el('div', { class: 'right' }, rightNodes));
  }
  return el('div', { class: 'panel' }, [head, bodyNode]);
}

export function kv(pairs) {
  const dl = el('dl', { class: 'kv' });
  for (const [key, value] of pairs) {
    dl.appendChild(el('dt', { text: key }));
    const dd = el('dd');
    dd.appendChild(value instanceof Node ? value : valueOr(value));
    dl.appendChild(dd);
  }
  return dl;
}

export function empty(title, detail) {
  return el('div', { class: 'empty' }, [
    el('b', { text: title }),
    detail ? el('div', { text: detail }) : null,
  ]);
}

export function notice(text, tone = '') {
  return el('div', { class: `notice ${tone}`.trim(), html: text });
}

// ---------------------------------------------------------------- toasts

export function toast(message, kind = '') {
  const host = document.getElementById('toasts');
  const node = el('div', { class: `toast ${kind}`.trim() }, [
    el('div', { html: message }),
    el('div', { class: 'ts', text: new Date().toLocaleTimeString() }),
  ]);
  host.appendChild(node);
  setTimeout(() => node.remove(), 6000);
}

// ---------------------------------------------------------------- modal

export function openModal(title, bodyNode, footNodes) {
  document.getElementById('modalTitle').textContent = title;
  clear(document.getElementById('modalBody')).appendChild(bodyNode);
  const foot = clear(document.getElementById('modalFoot'));
  for (const node of footNodes || []) foot.appendChild(node);
  document.getElementById('modalVeil').classList.add('on');
  const focusable = document.querySelector('#modalBody input, #modalBody textarea');
  if (focusable) setTimeout(() => focusable.focus(), 40);
}

export function closeModal() {
  document.getElementById('modalVeil').classList.remove('on');
}

export function field(label, control, hint) {
  return el('div', { class: 'field' }, [
    el('label', { text: label }),
    control,
    hint ? el('div', { class: 'hint', text: hint }) : null,
  ]);
}

export function input(name, placeholder) {
  const node = el('input', { name, placeholder: placeholder || '', autocomplete: 'off' });
  node.addEventListener('keydown', (event) => event.stopPropagation());
  return node;
}

export function textarea(name, placeholder) {
  const node = el('textarea', { name, placeholder: placeholder || '' });
  node.addEventListener('keydown', (event) => event.stopPropagation());
  return node;
}

export function select(name, options, selected) {
  const node = el('select', { name });
  for (const option of options) {
    const value = typeof option === 'string' ? option : option.value;
    const label = typeof option === 'string' ? option : option.label;
    node.appendChild(el('option', { value, text: label, selected: value === selected ? 'selected' : null }));
  }
  node.addEventListener('keydown', (event) => event.stopPropagation());
  return node;
}
