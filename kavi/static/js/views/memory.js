// Memory / Vault — read-only navigation of canonical organizational knowledge.
//
// The KAVI Vault is canonical. The desktop reads it and never writes to it in
// v0.1. Search runs over full note text, and wikilink relationships are
// resolved both ways so the Founder can follow the knowledge graph.

import { api } from '../api.js';
import { el, clear, chip, panel, notice, empty, toast } from '../ui.js';

export const meta = {
  id: 'memory',
  title: 'Memory / Vault',
  subtitle: 'Canonical organizational knowledge · read only',
  group: 'COMPANY',
  key: '6',
  icon: ['M4 5h10a3 3 0 013 3v11H7a3 3 0 01-3-3z', 'M7 9h7', 'M7 13h7'],
};

let currentSection = '';
let currentQuery = '';
let openPath = '';

export async function render(host, ctx) {
  const data = await api.memory({ section: currentSection, q: currentQuery });
  const status = data.status || {};

  ctx.setHeadStats([
    { v: data.matched, l: data.mode === 'SEARCH' ? 'Matches' : 'Notes', tone: 'mint' },
    { v: (data.sections || []).length, l: 'Sections', tone: 'muted' },
    { v: status.access || 'READ ONLY', l: 'Access', tone: 'amber' },
  ]);

  const body = el('div', {}, [
    notice(
      `<b>${status.path || 'Vault not located'}</b><br>${status.detail || ''}<br>`
      + `Access is <b>${status.access || 'READ ONLY'}</b>. Vault Sync is `
      + `<b>${status.sync || 'NOT CONNECTED'}</b> in v0.1.<br>`
      + 'The desktop reads canonical knowledge. It never writes to the vault.',
      'amber',
    ),
  ]);

  // ---- search + section filter
  const searchInput = el('input', {
    class: 'inp', type: 'search', placeholder: 'Search canonical knowledge…',
    'data-role': 'vault-search', value: currentQuery,
  });
  const runSearch = async () => {
    currentQuery = searchInput.value.trim();
    openPath = '';
    ctx.reload();
  };
  searchInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); runSearch(); }
  });

  const sectionSelect = el('select', { class: 'inp' }, [
    el('option', { value: '', text: 'All sections' }),
    ...(data.sections || []).map((s) => el('option', {
      value: s, text: s, selected: s === currentSection ? 'selected' : null,
    })),
  ]);
  sectionSelect.addEventListener('change', () => {
    currentSection = sectionSelect.value;
    openPath = '';
    ctx.reload();
  });

  body.appendChild(el('div', { class: 'vault-controls' }, [
    searchInput,
    sectionSelect,
    el('button', { class: 'btn sm primary', type: 'button', text: 'Search', onclick: runSearch }),
    currentQuery
      ? el('button', {
          class: 'btn sm ghost', type: 'button', text: 'Clear',
          onclick: () => { currentQuery = ''; searchInput.value = ''; ctx.reload(); },
        })
      : null,
  ]));

  const readerHost = el('div', { class: 'vault-reader' });
  const listHost = el('div', { class: 'vault-list' });

  const notes = data.notes || [];
  if (!notes.length) {
    listHost.appendChild(empty(
      currentQuery ? `Nothing matched “${currentQuery}”.` : 'No notes found.',
      currentQuery ? 'Try a different term.' : 'Check the vault path.',
    ));
  }

  notes.forEach((note) => {
    listHost.appendChild(el('button', {
      class: `vault-row${note.path === openPath ? ' sel' : ''}`,
      type: 'button',
      'data-note-path': note.path,
      onclick: () => openNote(note.path, readerHost, ctx),
    }, [
      el('div', { class: 'vault-row-head' }, [
        el('span', { class: 'vault-row-title', text: note.title }),
        note.document_state ? chip(note.document_state, 'muted') : null,
      ]),
      el('div', { class: 'vault-row-path mono', text: note.path }),
      note.excerpt
        ? el('div', { class: 'vault-row-excerpt', text: note.excerpt })
        : (note.summary ? el('div', { class: 'vault-row-excerpt', text: note.summary }) : null),
      note.hits ? el('div', { class: 'vault-row-hits', text: `${note.hits} match${note.hits === 1 ? '' : 'es'}` }) : null,
    ]));
  });

  body.appendChild(el('div', { class: 'vault-split' }, [listHost, readerHost]));
  host.appendChild(panel('Canonical vault', [chip('READ ONLY', 'amber')], body));

  if (openPath) openNote(openPath, readerHost, ctx);
}

async function openNote(path, readerHost, ctx) {
  openPath = path;
  clear(readerHost);
  try {
    const note = await api.memoryNote(path);
    readerHost.appendChild(el('div', { class: 'note-head' }, [
      el('h3', { class: 'note-title', text: note.title }),
      el('div', { class: 'chip-row' }, [
        chip(note.document_state || 'ACTIVE', 'muted'),
        note.doc_type ? chip(note.doc_type, 'muted') : null,
        chip(note.access || 'READ ONLY', 'amber'),
      ]),
      el('div', { class: 'note-path mono', text: note.path }),
    ]));

    const links = note.links || [];
    const backlinks = note.backlinks || [];
    if (links.length || backlinks.length) {
      readerHost.appendChild(el('div', { class: 'note-links' }, [
        links.length
          ? el('div', { class: 'note-link-group' }, [
              el('div', { class: 'detail-label', text: `LINKS OUT (${links.length})` }),
              el('div', { class: 'link-chips' }, links.map((link) => el('button', {
                class: `link-chip${link.resolved ? '' : ' unresolved'}`,
                type: 'button',
                text: link.name,
                title: link.resolved ? link.path : 'Not a note in this vault',
                onclick: () => { if (link.resolved) openNote(link.path, readerHost, ctx); },
              }))),
            ])
          : null,
        backlinks.length
          ? el('div', { class: 'note-link-group' }, [
              el('div', { class: 'detail-label', text: `LINKED FROM (${backlinks.length})` }),
              el('div', { class: 'link-chips' }, backlinks.map((link) => el('button', {
                class: 'link-chip', type: 'button', text: link.title,
                onclick: () => openNote(link.path, readerHost, ctx),
              }))),
            ])
          : null,
      ]));
    }

    readerHost.appendChild(el('pre', { class: 'note-body', text: note.content }));
  } catch (error) {
    toast(error.message, 'err');
    readerHost.appendChild(notice('Could not open that note.', 'amber'));
  }
}
