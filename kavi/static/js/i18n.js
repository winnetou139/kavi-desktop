// Bahasa / Language — English and Bahasa Indonesia.
//
// KAVI is used by one person who works in both languages, so every label the
// Founder reads is written in both. The choice is remembered between sessions.
//
// Rules for writing strings here:
//   - Say what a thing IS, not what its record ID is.
//   - Prefer a full sentence over an abbreviation.
//   - Never translate a governed vocabulary value (APPROVED, NOT CONNECTED,
//     FACT). Those are contract terms; changing them would change meaning.

const STORE_KEY = 'kavi.language';

export const LANGUAGES = [
  { code: 'en', label: 'English', short: 'EN' },
  { code: 'id', label: 'Bahasa Indonesia', short: 'ID' },
];

const STRINGS = {
  // ---------------------------------------------------------- app chrome
  'app.title': { en: 'KAVI Founder Cockpit', id: 'KAVI Founder Cockpit' },
  'app.founder': { en: 'Founder', id: 'Founder' },
  'app.search': { en: 'Search or create…', id: 'Cari atau buat…' },
  'app.language': { en: 'Language', id: 'Bahasa' },
  'app.loading': { en: 'Loading…', id: 'Memuat…' },
  'app.close': { en: 'Close', id: 'Tutup' },
  'app.cancel': { en: 'Cancel', id: 'Batal' },
  'app.save': { en: 'Save', id: 'Simpan' },
  'app.create': { en: 'Create', id: 'Buat' },
  'app.open': { en: 'Open', id: 'Buka' },
  'app.reason': { en: 'Reason', id: 'Alasan' },
  'app.none': { en: 'None', id: 'Tidak ada' },
  'app.readonly': { en: 'Read only', id: 'Hanya baca' },
  'app.notMeasured': { en: 'Not measured', id: 'Belum diukur' },
  'app.notConnected': { en: 'Not connected', id: 'Belum terhubung' },

  // ------------------------------------------------------------- groups
  'group.FOUNDER': { en: 'Founder', id: 'Founder' },
  'group.WORK': { en: 'Work', id: 'Pekerjaan' },
  'group.COMPANY': { en: 'Company', id: 'Perusahaan' },

  // -------------------------------------------------------------- rail
  'nav.command': { en: 'Command', id: 'Pusat Kendali' },
  'nav.command.sub': {
    en: 'Start here · give KAVI an objective',
    id: 'Mulai di sini · beri KAVI satu tujuan',
  },
  'nav.ask': { en: 'Ask KAVI', id: 'Minta KAVI' },
  'nav.ask.sub': {
    en: 'Send work to the connected runtime',
    id: 'Kirim pekerjaan ke runtime yang terhubung',
  },
  'nav.inbox': { en: 'Decisions for You', id: 'Keputusan untuk Anda' },
  'nav.inbox.sub': {
    en: 'Things waiting for your judgement',
    id: 'Hal yang menunggu keputusan Anda',
  },
  'nav.objectives': { en: 'Objectives & Work', id: 'Tujuan & Pekerjaan' },
  'nav.objectives.sub': {
    en: 'What you asked for, and the work under it',
    id: 'Apa yang Anda minta, dan pekerjaan di bawahnya',
  },
  'nav.ventures': { en: 'Ventures', id: 'Usaha' },
  'nav.ventures.sub': {
    en: 'Where each product stands, and what it must prove next',
    id: 'Posisi tiap produk, dan apa yang harus dibuktikan berikutnya',
  },
  'nav.organization': { en: 'Organization', id: 'Organisasi' },
  'nav.organization.sub': {
    en: 'Divisions and who may act',
    id: 'Divisi dan siapa yang boleh bertindak',
  },
  'nav.memory': { en: 'Company Knowledge', id: 'Pengetahuan Perusahaan' },
  'nav.memory.sub': {
    en: 'The vault — read only',
    id: 'Vault kanonik — hanya baca',
  },
  'nav.metrics': { en: 'Metrics & Cost', id: 'Metrik & Biaya' },
  'nav.metrics.sub': {
    en: 'What is measured, and what is not',
    id: 'Yang terukur, dan yang belum',
  },
  'nav.decisions': { en: 'Decision Record', id: 'Catatan Keputusan' },
  'nav.decisions.sub': {
    en: 'Decisions already made, read from the vault',
    id: 'Keputusan yang sudah diambil, dibaca dari vault',
  },
  'nav.authority': { en: 'Authority & Limits', id: 'Wewenang & Batasan' },
  'nav.authority.sub': {
    en: 'What KAVI may and may not do',
    id: 'Apa yang boleh dan tidak boleh dilakukan KAVI',
  },

  // ------------------------------------------------------------- status
  'status.mode': { en: 'Mode', id: 'Mode' },
  'status.thisComputer': { en: 'This computer only', id: 'Hanya komputer ini' },
  'status.server': { en: 'Server', id: 'Server' },
  'status.scheduler': { en: 'Automatic scheduling', id: 'Penjadwalan otomatis' },
  'status.queue': { en: 'Work queue', id: 'Antrian kerja' },
  'status.router': { en: 'AI provider', id: 'Penyedia AI' },
  'status.vault': { en: 'Knowledge vault', id: 'Vault pengetahuan' },
  'status.cost': { en: 'Spend today', id: 'Biaya hari ini' },
  'status.uptime': { en: 'Uptime', id: 'Waktu aktif' },
  'status.nothingRunning': {
    en: 'Nothing is running on your behalf.',
    id: 'Tidak ada yang berjalan atas nama Anda.',
  },

  // -------------------------------------------------------------- inbox
  'inbox.empty': { en: 'Nothing needs your decision.', id: 'Tidak ada yang perlu Anda putuskan.' },
  'inbox.emptyHint': {
    en: 'Items appear here when work needs your judgement.',
    id: 'Item muncul di sini saat ada pekerjaan yang butuh keputusan Anda.',
  },
  'inbox.open': { en: 'Waiting', id: 'Menunggu' },
  'inbox.about': { en: 'This is about', id: 'Ini tentang' },
  'inbox.recommendation': { en: 'What KAVI recommends', id: 'Rekomendasi KAVI' },
  'inbox.evidence': { en: 'Evidence behind it', id: 'Bukti pendukung' },
  'inbox.authority': { en: 'What this allows', id: 'Yang diizinkan' },
  'inbox.yourDecision': { en: 'Your decision', id: 'Keputusan Anda' },
  'inbox.approve': { en: 'Approve', id: 'Setujui' },
  'inbox.reject': { en: 'Reject', id: 'Tolak' },
  'inbox.defer': { en: 'Decide later', id: 'Tunda dulu' },
  'inbox.askEvidence': { en: 'Ask for more evidence', id: 'Minta bukti tambahan' },
  'inbox.decided': { en: 'Your decision', id: 'Keputusan Anda' },
  'inbox.localOnly': {
    en: 'Recorded on this computer only. Nothing is sent, spent, or executed.',
    id: 'Hanya dicatat di komputer ini. Tidak ada yang dikirim, dibelanjakan, atau dijalankan.',
  },
  'inbox.demoLocked': {
    en: 'This is sample data, so it cannot be decided. Raise a real item from an objective to try this.',
    id: 'Ini data contoh, jadi tidak bisa diputuskan. Ajukan item nyata dari sebuah tujuan untuk mencobanya.',
  },
  'inbox.closed': { en: 'Already decided. No further action.', id: 'Sudah diputuskan. Tidak ada tindakan lagi.' },

  // --------------------------------------------------------- objectives
  'obj.new': { en: 'New objective', id: 'Tujuan baru' },
  'obj.title': { en: 'What outcome do you want?', id: 'Hasil apa yang Anda inginkan?' },
  'obj.outcome': { en: 'What must be true when this is done?', id: 'Apa yang harus tercapai saat ini selesai?' },
  'obj.success': { en: 'How will you know it succeeded?', id: 'Bagaimana Anda tahu ini berhasil?' },
  'obj.constraints': { en: 'What must this NOT do?', id: 'Apa yang TIDAK boleh dilakukan?' },
  'obj.budget': { en: 'Budget', id: 'Anggaran' },
  'obj.deadline': { en: 'Deadline', id: 'Tenggat' },
  'obj.priority': { en: 'Priority', id: 'Prioritas' },
  'obj.addTask': { en: 'Add work item', id: 'Tambah pekerjaan' },
  'obj.raise': { en: 'Send to my decisions', id: 'Kirim ke keputusan saya' },
  'obj.noTasks': { en: 'No work items yet', id: 'Belum ada pekerjaan' },
  'obj.progress': { en: 'Progress', id: 'Kemajuan' },

  // ------------------------------------------------------------- vault
  'vault.search': { en: 'Search company knowledge…', id: 'Cari pengetahuan perusahaan…' },
  'vault.allSections': { en: 'All sections', id: 'Semua bagian' },
  'vault.notes': { en: 'notes', id: 'catatan' },
  'vault.matches': { en: 'matches', id: 'hasil' },
  'vault.linksOut': { en: 'Links to', id: 'Menautkan ke' },
  'vault.linkedFrom': { en: 'Linked from', id: 'Ditautkan dari' },
  'vault.neverWrites': {
    en: 'KAVI reads this knowledge. It never changes it.',
    id: 'KAVI membaca pengetahuan ini. Tidak pernah mengubahnya.',
  },

  // --------------------------------------------------------- decisions
  'dec.source': { en: 'Read from your vault', id: 'Dibaca dari vault Anda' },
  'dec.reversible': { en: 'Can this be undone?', id: 'Bisakah dibatalkan?' },
  'dec.approvedBy': { en: 'Approved by', id: 'Disetujui oleh' },
  'dec.why': { en: 'Why', id: 'Alasan' },
  'dec.consequences': { en: 'What follows from it', id: 'Konsekuensinya' },
  'dec.readFrom': { en: 'Read from file', id: 'Dibaca dari berkas' },
  'dec.none': {
    en: 'No decisions could be read. Nothing has been made up in their place.',
    id: 'Tidak ada keputusan yang bisa dibaca. Tidak ada yang dikarang sebagai gantinya.',
  },

  // ---------------------------------------------------------- authority
  'auth.founderAuthority': { en: 'Your authority', id: 'Wewenang Anda' },
  'auth.humanApproval': { en: 'Human approval', id: 'Persetujuan manusia' },
  'auth.ladder': { en: 'What KAVI is allowed to do', id: 'Apa yang boleh dilakukan KAVI' },
  'auth.availableNow': { en: 'Allowed now', id: 'Boleh sekarang' },
  'auth.notAvailable': { en: 'Not allowed yet', id: 'Belum boleh' },
  'auth.nothingRunning': {
    en: 'KAVI cannot act on its own. Nothing is connected that could execute anything.',
    id: 'KAVI tidak bisa bertindak sendiri. Tidak ada yang terhubung untuk menjalankan apa pun.',
  },

  // ----------------------------------------------------------- evidence
  'ev.register': { en: 'Evidence register', id: 'Daftar bukti' },
  'ev.claims': { en: 'claims', id: 'klaim' },
  'ev.contradiction': { en: 'Caveat or contradiction', id: 'Peringatan atau kontradiksi' },
  'ev.notMarketProof': {
    en: 'Not proof that anyone will pay',
    id: 'Bukan bukti bahwa ada yang akan membayar',
  },
  'ev.noMarketValidation': {
    en: 'No customer has been asked anything yet.',
    id: 'Belum ada satu pun calon pelanggan yang ditanya.',
  },
};

let current = 'en';

export function initLanguage() {
  try {
    const saved = localStorage.getItem(STORE_KEY);
    if (saved && LANGUAGES.some((l) => l.code === saved)) current = saved;
    else if ((navigator.language || '').toLowerCase().startsWith('id')) current = 'id';
  } catch (error) {
    current = 'en';
  }
  document.documentElement.lang = current;
  return current;
}

export function language() {
  return current;
}

export function setLanguage(code) {
  if (!LANGUAGES.some((l) => l.code === code)) return current;
  current = code;
  try {
    localStorage.setItem(STORE_KEY, code);
  } catch (error) {
    /* a read-only profile is not a reason to fail */
  }
  document.documentElement.lang = code;
  return current;
}

/**
 * Translate a key. Falls back to English, then to the key itself, so a missing
 * translation shows something meaningful instead of blank space.
 */
export function t(key, fallback = '') {
  const entry = STRINGS[key];
  if (!entry) return fallback || key;
  return entry[current] || entry.en || fallback || key;
}

/** Both languages at once, for a tooltip. */
export function both(key) {
  const entry = STRINGS[key];
  if (!entry) return '';
  return current === 'id' ? entry.en : entry.id;
}
