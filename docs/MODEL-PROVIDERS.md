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
