// Memory / Vault — read-only navigation over canonical organizational knowledge.
import { api } from '../api.js';
import { el, clear, chip, panel, notice, toast } from '../ui.js';

export const meta = {
  id: 'memory',
  title: 'Memory / Vault',
  subtitle: 'Canonical organizational knowledge · read only',
  group: 'COMPANY',
  key: '6',
  icon: ['M4 5.5c0 1.55 3.58 2.8 8 2.8s8-1.25 8-2.8-3.58-2.8-8-2.8-8 1.25-8 2.8z',
         'M4 5.5V12c0 1.5 3.6 2.8 8 2.8s8-1.3 8-2.8V5.5',
         'M4 12v6.5c0 1.5 3.6 2.8 8 2.8s8-1.3 8-2.8V12'],
};

let query = '';
let section = '';
let openPath = '';

export async function render(host, ctx) {
  const data = await api.memory({ q: query, section });
  const status = data.status;

  ctx.setHeadStats([
    { v: status.note_count, l: 'Notes', tone: status.available ? 'mint' : 'muted' },
    { v: status.access, l: 'Access', tone: 'muted' },
    { v: status.sync, l: 'Sync', tone: 'muted' },
  ]);

  if (!status.available) {
    host.appendChild(el('div', { class: 'screen-body' }, [
      notice(`<b>Canonical vault not found.</b> ${status.detail}`, 'red'),
    ]));
    return;
  }

  const list = el('div', { class: 'mem-list' });
  const body = el('div', { class: 'mem-body' });

  const search = el('input', { placeholder: 'Search notes…', value: query, autocomplete: 'off' });
  search.addEventListener('keydown', (event) => event.stopPropagation());
  let timer = null;
  search.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => { query = search.value.trim(); ctx.reload(); }, 220);
  });

  const sectionSelect = el('select', {});
  sectionSelect.appendChild(el('option', { value: '', text: `All sections (${status.note_count})` }));
  for (const row of data.sections) {
    sectionSelect.appendChild(el('option', {
      value: row.section, text: `${row.section} (${row.count})`,
      selected: row.section === section ? 'selected' : null,
    }));
  }
  sectionSelect.addEventListener('change', () => { section = sectionSelect.value; ctx.reload(); });

  list.appendChild(el('div', { class: 'mem-search' }, [
    search,
    el('div', { style: 'margin-top:8px' }, [sectionSelect]),
  ]));

  const notesHost = el('div', { style: 'flex:1;overflow-y:auto' });
  for (const note of data.notes) {
    notesHost.appendChild(el('button', {
      class: `mem-note ${note.path === openPath ? 'sel' : ''}`.trim(),
      type: 'button',
      onclick: async () => {
        openPath = note.path;
        await drawNote(body, note.path);
        for (const other of notesHost.querySelectorAll('.mem-note')) other.classList.remove('sel');
      },
    }, [
      el('div', { class: 't', text: note.title }),
      el('div', { class: 's', text: `${note.section} · ${note.doc_type || 'note'} · ${note.document_state}` }),
    ]));
  }
  if (!data.notes.length) {
    notesHost.appendChild(el('div', { class: 'empty', text: 'No notes match.' }));
  }
  list.appendChild(notesHost);

  body.appendChild(el('div', {}, [
    notice(
      `<b>${status.path}</b><br>${status.detail}<br>` +
      `Access is <b>${status.access}</b>. Vault Sync is <b>${status.sync}</b> in v0.1.<br>` +
      `${data.matched} note(s) matched.`,
      'blue',
    ),
    el('div', { class: 'empty', text: 'Select a note to read it.' }),
  ]));

  if (openPath) await drawNote(body, openPath);

  host.appendChild(el('div', { class: 'mem-split' }, [list, body]));
}

async function drawNote(host, path) {
  clear(host);
  try {
    const note = await api.memoryNote(path);
    host.appendChild(el('div', { class: 'detail-kicker' }, [
      chip(note.document_state), chip(note.access, 'blue'),
      note.doc_type ? chip(note.doc_type, 'grey') : null,
    ].filter(Boolean)));
    host.appendChild(el('div', { class: 'detail-title', text: note.title }));
    host.appendChild(el('div', { class: 'detail-meta', text: note.path }));
    host.appendChild(el('pre', { text: note.content }));
  } catch (error) {
    host.appendChild(notice(error.message, 'red'));
  }
}
