# KAVI Engine Room — VPS

Server ini adalah **engine room**, bukan cockpit. Sesuai D-003:
cockpit tetap berjalan lokal di laptop Founder; VPS hanya untuk kerja yang
harus jalan terus-menerus.

## Akses

| Item | Nilai |
|---|---|
| Host | `srv1957149.hstgr.cloud` |
| IP | `72.62.127.35` |
| OS | Ubuntu 24.04.4 LTS |
| User | `kavi` (sudo, tanpa password) |
| Kunci privat | `C:\Users\abdul.kausar\.ssh\kavi_vps` |
| Login root | **dimatikan** |
| Login password | **dimatikan** |

Masuk:

```bash
ssh -i ~/.ssh/kavi_vps kavi@72.62.127.35
```

Kunci privat tidak pernah meninggalkan laptop ini. Jangan pernah menempelkannya
ke chat, tiket, atau repositori.

## Hardening yang sudah diterapkan (2026-09-05)

| # | Tindakan | Status |
|---|---|---|
| 1 | Semua paket diperbarui | 0 update tertunda |
| 2 | User non-root `kavi` + sudo | aktif |
| 3 | `PermitRootLogin no` | terverifikasi ditolak |
| 4 | `PasswordAuthentication no` | terverifikasi ditolak |
| 5 | `AllowUsers kavi` | hanya satu user yang boleh |
| 6 | `MaxAuthTries 3` | aktif |
| 7 | UFW: deny masuk, hanya 22/tcp (rate-limited) | aktif |
| 8 | fail2ban: 3 percobaan → blokir 2 jam | aktif |
| 9 | unattended-upgrades keamanan | aktif |

Port yang terbuka ke internet: **hanya 22**.

### Jebakan yang ditemukan saat hardening

Ubuntu cloud image memasang `50-cloud-init.conf` yang berisi
`PasswordAuthentication yes`. SSH memakai nilai **pertama** yang dibaca, bukan
yang terakhir — sehingga file `99-kavi-hardening.conf` kalah dan login password
**masih hidup** meski konfigurasi terlihat benar.

Perbaikan: berkas hardening dinamai ulang menjadi `00-kavi-hardening.conf`
agar terbaca lebih dulu, dan nilai milik cloud-init dinetralkan.

Pelajaran: selalu verifikasi dengan `sudo sshd -T`, jangan percaya isi berkas.

## Yang sengaja TIDAK dipasang

**KAVI Desktop tidak berjalan di server ini.**

Aplikasi itu belum punya autentikasi sama sekali — keamanannya hanya berasal
dari ikatan ke `127.0.0.1`. Menaruhnya di IP publik berarti membuka seluruh
vault kanonik kepada siapa pun yang tahu alamatnya.

Prasyarat sebelum KAVI Desktop boleh naik ke VPS:

1. autentikasi login,
2. HTTPS,
3. binding bukan `0.0.0.0` tanpa proteksi,
4. keputusan Founder yang eksplisit.

## Langkah berikutnya yang mungkin

- Pasang Hermes sebagai engine room (kerja jangka panjang, terjadwal).
- Biarkan cockpit lokal terhubung ke sana lewat terowongan SSH, bukan port publik.

## Verifikasi ulang kapan saja

```bash
ssh -i ~/.ssh/kavi_vps kavi@72.62.127.35 "sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|allowusers'; sudo ufw status; sudo fail2ban-client status sshd"
```
