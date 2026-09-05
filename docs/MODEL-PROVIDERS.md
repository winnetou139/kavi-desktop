# Tiga langganan, nol kredit API

Semua model dijalankan lewat langganan yang sudah dibayar. **Tidak ada satu pun
yang memakai kredit API berbayar terpisah.**

| Langganan | Jalur di Hermes | Status |
|---|---|---|
| Claude Max | `anthropic` — OAuth Claude Code | aktif |
| ChatGPT Pro | `openai-codex` — OAuth device code | aktif |
| Kimi K3 Max | `kimi-coding` — Coding Plan key | aktif, **model utama** |

## Kenapa ini penting

Claude Max dan API key Anthropic adalah **dua produk terpisah dengan tagihan
terpisah**. Langganan tidak mengalir ke API. Hermes memakai jalur OAuth, jadi
langganan yang sudah dibayar itulah yang terpakai — bukan kredit baru.

Kalau suatu saat Hermes minta `ANTHROPIC_API_KEY`, itu tanda jalur OAuth-nya
putus. Sambungkan ulang, jangan beli kredit.

## Fallback berjenjang

```yaml
fallback_model:
  provider: openai-codex
  model: gpt-5.6-sol
```

Utama **Kimi K3** (paling hemat untuk kerja panjang). Kalau kena rate limit
(429), overload (529), atau service error (503), Hermes otomatis pindah ke
ChatGPT Pro. Kerja tidak berhenti.

## Memanggil model tertentu

```bash
hermes -z "..."                                 # Kimi K3 (utama)
hermes -m claude-opus-4-8 -z "..."              # Claude Max
hermes -m openai-codex/gpt-5.6-sol -z "..."     # ChatGPT Pro
```

**Perhatikan awalan `openai-codex/`.** Tanpa itu Hermes memilih provider
`openai-api` yang butuh API key, lalu gagal dengan pesan
`No usable credentials found for provider 'openai-api'`. Pesan itu menyesatkan:
kredensialnya ada, hanya di provider yang berbeda.

Untuk keputusan governance KAVI, panggil Claude Max secara eksplisit —
penalarannya paling kuat untuk urusan yang butuh pertimbangan.

## Perintah pemeriksaan

```bash
hermes auth list              # lihat semua kredensial
hermes auth status anthropic  # cek satu provider
hermes model                  # ganti model utama
```

## Jebakan yang sudah ditemui

**Mengonfigurasi provider baru bisa memutus yang lama.** Saat Kimi
dikonfigurasi, kredensial OAuth Claude Code terputus dan `hermes auth status
anthropic` berubah jadi `logged out` — padahal Claude Code di laptop masih
login normal. Sambungkan ulang dengan:

```bash
hermes auth add anthropic --type oauth --label claude_code
```

Perintah itu **interaktif**: browser terbuka, salin kode dari Claude, tempel
kembali ke terminal. Tidak bisa dijalankan non-interaktif.

**Selalu cek `hermes auth list` setelah menambah provider baru.**

## Engine room (VPS)

OAuth Claude dan ChatGPT terikat ke mesin tempat login. Apakah boleh dipakai
di dua mesin sekaligus — **belum diverifikasi**, jadi jangan diasumsikan boleh.

Kimi memakai API key biasa, sah dipasang di server mana pun. Jadi engine room
sebaiknya memakai Kimi; Claude dan ChatGPT tetap melayani cockpit di laptop.

## Berganti model

```bash
python tools/model.py            # lihat yang aktif sekarang
python tools/model.py claude     # ganti ke Claude Max
python tools/model.py gpt        # ganti ke ChatGPT Pro
python tools/model.py kimi       # ganti ke Kimi K3
python tools/model.py bench      # ukur kecepatan ketiganya
```

Sekali pakai tanpa mengubah default:

```bash
hermes -m claude-opus-4-8 -z "..."
```

### Jebakan base_url

`base_url` milik satu provider saja. Kimi memakai
`https://api.kimi.com/coding`; Claude dan ChatGPT tidak boleh membawanya.

Versi pertama alat ini membuang `base_url` saat pindah ke provider lain tapi
**tidak mengembalikannya** saat kembali ke Kimi. Kimi tetap berjalan karena
Hermes punya default sendiri — jadi kerusakannya tidak terlihat. Konfigurasi
yang tadinya eksplisit diam-diam berubah jadi implisit.

Sekarang `base_url` ditulis ulang bersama baris `default:`, dan siklus penuh
kimi → gpt → claude → kimi sudah diuji mengembalikan konfigurasi utuh.

## Hasil pengukuran kecepatan

Diukur pada 2026-09-05, pertanyaan singkat domain project controls:

| Model | Waktu |
|---|---|
| Claude Max | 20.4s |
| ChatGPT Pro | 21.9s |
| Kimi K3 | 22.3s |

**Selisihnya kecil — di bawah 2 detik.** Untuk pertanyaan pendek, kecepatan
bukan alasan yang cukup untuk memilih salah satu.

Yang **tidak** diukur: mutu jawaban. Stopwatch tidak bisa menilai penalaran.
Pada uji claim keterlambatan, ketiganya sama-sama menyebut *contemporaneous
records* dan *Time Impact Analysis* — jawaban yang benar secara domain.
Bedanya ada di kedalaman, dan itu hanya Founder yang bisa menilai.

Jalankan `python tools/model.py bench "pertanyaan Anda"` dengan pekerjaan
nyata Anda, lalu bandingkan jawabannya sendiri.
