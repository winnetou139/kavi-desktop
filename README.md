# KAVI Desktop v0.1 — Founder Cockpit Foundation

Local desktop cockpit for KAVI. Zero external dependencies: Python standard library
backend, vanilla JavaScript ES-module frontend, no build step, no package manager.

## Run

```
python run.py
```

Then open the URL it prints (default `http://127.0.0.1:8760`).

Options:

```
python run.py --port 8760 --host 127.0.0.1 --no-browser
python run.py --vault "C:/path/to/KAVI_Vault_v0.1"
```

## Tests

```
python tests/run_all.py
```

## Operating mode

KAVI Desktop v0.1 runs in **LOCAL / DEVELOPMENT MODE**. The Engine Room
(VPS, scheduler, queue, provider router, vault sync) is **NOT CONNECTED**.
Every runtime figure the UI concept showed as live — uptime, queue depth,
cost today, router status — is reported by the runtime status abstraction as
unavailable, not faked.

## Data honesty

Two data origins exist and are labelled everywhere they surface:

| Origin | Meaning |
|---|---|
| `LOCAL` | Records you created in this application, stored under the app data directory |
| `FIXTURE` | Development fixture data derived from the UI concept — **not company evidence** |

Fixture records carry `origin: "FIXTURE"` through the API and render with a
`FIXTURE` chip in the interface. They must never be cited as KAVI company
evidence, venture evidence, or commercial validation.

## Vault

The KAVI Vault remains the canonical source of organizational knowledge.
This application reads it. It does not write to it, and it does not synchronize.

## Architecture

```
Presentation            kavi/static/            vanilla JS, no framework
      ↓
Application/Use Cases   kavi/application/       orchestration, no I/O details
      ↓
Domain Contracts        kavi/domain/            KAVI contracts, pure Python
      ↓
Infrastructure          kavi/infrastructure/    store, vault reader, execution adapters
```

`kavi/api/` is transport only. `kavi/server.py` is HTTP plumbing only.
No domain rule is implemented in the browser.
