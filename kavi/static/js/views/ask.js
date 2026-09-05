// Ask KAVI — talk to the connected runtime from the cockpit.
//
// This is the first screen where KAVI actually does something rather than
// recording something. Rules kept deliberately visible to the Founder:
//   - a run only ever starts because he pressed Run;
//   - nothing is scheduled, queued, or triggered in the background;
//   - the real result comes back, including failures and timeouts;
//   - if no runtime is connected, the button says so instead of pretending.

import { api } from '../api.js';
import { el, clear, chip, panel, notice, toast, empty } from '../ui.js';
import { t as tr, language } from '../i18n.js';

export const meta = {
  id: 'ask',
  title: 'Ask KAVI',
  subtitle: 'Send work to the connected runtime',
  group: 'FOUNDER',
  key: '0',
  icon: ['M12 3a9 9 0 1 0 4.5 16.8L21 21l-1.2-4.5A9 9 0 0 0 12 3z', 'M8.5 11h7', 'M8.5 14.5h4.5'],
};

const STATE_TONE = {
  RUNNING: 'amber',
  SUCCEEDED: 'mint',
  FAILED: 'red',
  TIMED_OUT: 'red',
  DECLINED: 'muted',
};

// Starting points, so the Founder is not facing an empty box.
const SUGGESTIONS = [
  {
    en: 'Summarise what changed in my vault this week',
    id: 'Ringkas apa yang berubah di vault saya minggu ini',
  },
  {
    en: 'Read my VECYRA venture state and tell me the single weakest claim',
    id: 'Baca status usaha VECYRA dan sebutkan klaim paling lemah',
  },
  {
    en: 'List every UNKNOWN in my evidence register and what would resolve it',
    id: 'Daftar semua UNKNOWN di daftar bukti dan apa yang bisa menjawabnya',
  },
];

let pollTimer = null;

export async function render(host, ctx) {
  const data = await api.execution();
  const status = data.status || {};
  const connected = status.connected === true;
  const isID = language() === 'id';

  ctx.setHeadStats([
    { v: status.adapter || 'NONE', l: isID ? 'Runtime' : 'Runtime',
      tone: connected ? 'mint' : 'muted' },
    { v: status.state || 'NOT CONNECTED', l: isID ? 'Status' : 'Status',
      tone: connected ? 'mint' : 'amber' },
    { v: (data.runs || []).length, l: isID ? 'Riwayat' : 'Runs', tone: 'muted' },
  ]);

  const stack = el('div', { class: 'stack' });

  // --- honest banner about what this can and cannot do
  stack.appendChild(notice(
    connected
      ? (isID
        ? `<b>${status.adapter} siap.</b> Perintah hanya jalan saat Anda menekan Jalankan. `
          + `Tidak ada jadwal, tidak ada antrian, tidak ada yang berjalan sendiri. `
          + `Setiap run berhenti otomatis setelah ${status.timeout_seconds || 300} detik.`
        : `<b>${status.adapter} is ready.</b> A run only happens when you press Run. `
          + `Nothing is scheduled, queued, or triggered on its own. `
          + `Every run stops by itself after ${status.timeout_seconds || 300} seconds.`)
      : `<b>${isID ? 'Belum terhubung.' : 'Not connected.'}</b> ${status.detail || ''}`,
    connected ? 'mint' : 'amber',
  ));

  // --- the prompt box
  const box = el('textarea', {
    class: 'ask-input',
    id: 'askInput',
    rows: 4,
    placeholder: isID
      ? 'Tulis apa yang Anda ingin KAVI kerjakan…'
      : 'Write what you want KAVI to do…',
    disabled: connected ? null : 'disabled',
  });

  const runButton = el('button', {
    class: 'btn primary ask-run',
    type: 'button',
    id: 'askRun',
    disabled: connected ? null : 'disabled',
    text: connected
      ? (isID ? 'Jalankan' : 'Run')
      : (isID ? 'Tidak tersedia' : 'Unavailable'),
    onclick: () => startRun(box, resultHost, ctx),
  });

  box.addEventListener('keydown', (event) => {
    event.stopPropagation();
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      startRun(box, resultHost, ctx);
    }
  });

  const chips = el('div', { class: 'ask-suggestions' },
    SUGGESTIONS.map((s) => el('button', {
      class: 'suggestion',
      type: 'button',
      text: isID ? s.id : s.en,
      disabled: connected ? null : 'disabled',
      onclick: () => { box.value = isID ? s.id : s.en; box.focus(); },
    })));

  const resultHost = el('div', { class: 'ask-result' });

  stack.appendChild(panel(
    isID ? 'Minta KAVI mengerjakan sesuatu' : 'Ask KAVI to do something',
    [connected ? chip('READY', 'mint') : chip('NOT CONNECTED', 'amber')],
    el('div', { class: 'panel-body' }, [
      box,
      el('div', { class: 'ask-actions' }, [
        runButton,
        el('span', { class: 'ask-hint', text: isID
          ? 'Ctrl+Enter untuk menjalankan' : 'Ctrl+Enter to run' }),
      ]),
      chips,
      resultHost,
    ]),
  ));

  // --- what this runtime is, in plain terms
  stack.appendChild(panel(
    isID ? 'Runtime yang terhubung' : 'Connected runtime',
    [],
    el('div', { class: 'panel-body' }, [
      el('table', { class: 'grid' }, [
        el('tbody', {}, [
          row(isID ? 'Adapter' : 'Adapter', status.adapter || 'NONE'),
          row(isID ? 'Status' : 'State', status.state || 'NOT CONNECTED'),
          status.path ? row(isID ? 'Program' : 'Program', status.path) : null,
          status.workdir ? row(isID ? 'Folder kerja' : 'Working folder', status.workdir) : null,
          status.timeout_seconds
            ? row(isID ? 'Batas waktu' : 'Time limit', `${status.timeout_seconds}s`) : null,
          status.transcripts
            ? row(isID ? 'Catatan run' : 'Transcripts', status.transcripts) : null,
        ].filter(Boolean)),
      ]),
      el('div', { class: 'deck-foot', text: status.detail || '' }),
    ]),
  ));

  // --- history
  const runs = data.runs || [];
  stack.appendChild(panel(
    isID ? 'Riwayat' : 'Recent runs',
    [chip(String(runs.length), 'muted')],
    runs.length
      ? el('table', { class: 'grid' }, [
          el('thead', {}, [el('tr', {}, [
            el('th', { text: 'Run' }),
            el('th', { text: isID ? 'Status' : 'State' }),
            el('th', { text: isID ? 'Permintaan' : 'Prompt' }),
            el('th', { text: isID ? 'Mulai' : 'Started' }),
          ])]),
          el('tbody', {}, runs.map((run) => el('tr', {}, [
            el('td', {}, [el('span', { class: 'mono', text: run.run_id })]),
            el('td', {}, [chip(run.state, STATE_TONE[run.state] || 'muted')]),
            el('td', { class: 'ask-prompt-cell', text: run.prompt || '—' }),
            el('td', { class: 'mono', text: (run.started_at || '').replace('T', ' ') }),
          ]))),
        ])
      : el('div', { class: 'panel-body' }, [
          empty(
            isID ? 'Belum ada yang dijalankan.' : 'Nothing has been run yet.',
            isID ? 'Tulis sesuatu di atas lalu tekan Jalankan.'
                 : 'Write something above and press Run.',
          ),
        ]),
  ));

  host.appendChild(stack);
}

async function startRun(box, resultHost, ctx) {
  const prompt = box.value.trim();
  const isID = language() === 'id';
  if (!prompt) {
    toast(isID ? 'Tulis dulu apa yang ingin dikerjakan.' : 'Write what you want done first.', 'err');
    box.focus();
    return;
  }

  clear(resultHost);
  resultHost.appendChild(el('div', { class: 'run-live' }, [
    el('span', { class: 'run-spinner' }),
    el('span', { text: isID ? 'Menjalankan…' : 'Running…' }),
  ]));

  try {
    const run = await api.runPrompt(prompt);
    pollRun(run.run_id, resultHost, ctx);
  } catch (error) {
    clear(resultHost);
    resultHost.appendChild(notice(error.message, 'warn'));
  }
}

/** Poll until the run finishes. The screen shows exactly what came back. */
function pollRun(runId, resultHost, ctx) {
  if (pollTimer) clearInterval(pollTimer);
  const isID = language() === 'id';
  const started = Date.now();

  pollTimer = setInterval(async () => {
    let run;
    try {
      run = await api.runStatus(runId);
    } catch (error) {
      clearInterval(pollTimer);
      clear(resultHost);
      resultHost.appendChild(notice(error.message, 'warn'));
      return;
    }

    if (run.state === 'RUNNING') {
      const seconds = Math.round((Date.now() - started) / 1000);
      const live = resultHost.querySelector('.run-live span:last-child');
      if (live) live.textContent = `${isID ? 'Menjalankan' : 'Running'}… ${seconds}s`;
      return;
    }

    clearInterval(pollTimer);
    pollTimer = null;
    clear(resultHost);

    resultHost.appendChild(el('div', { class: 'run-done' }, [
      el('div', { class: 'run-head' }, [
        el('span', { class: 'mono', text: run.run_id }),
        chip(run.state, STATE_TONE[run.state] || 'muted'),
        run.exit_code !== null && run.exit_code !== undefined
          ? el('span', { class: 'run-exit mono', text: `exit ${run.exit_code}` })
          : null,
      ]),
      el('div', { class: 'run-detail', text: run.detail || '' }),
      run.output
        ? el('pre', { class: 'run-output', text: run.output })
        : notice(isID ? 'Tidak ada keluaran.' : 'No output was returned.'),
    ]));

    toast(`${run.run_id} → ${run.state}`, run.state === 'SUCCEEDED' ? '' : 'err');
  }, 1500);
}

function row(label, value) {
  return el('tr', {}, [
    el('td', { class: 'er-label' }, [el('div', { class: 'er-name', text: label })]),
    el('td', { class: 'mono', style: 'word-break:break-all', text: String(value) }),
  ]);
}
