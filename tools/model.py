"""Switch the default model, and measure which subscription is worth using.

Three subscriptions are paid for. This tool answers two questions:

    which one is active right now, and how do I change it?
    which one is actually fastest for the work I do?

Speed is measured, never assumed. Quality is NOT measured here: judging answer
quality needs the Founder reading the answers, and a stopwatch cannot do it.

Usage:
    python tools/model.py                    show what is active
    python tools/model.py claude             switch to Claude Max
    python tools/model.py gpt                switch to ChatGPT Pro
    python tools/model.py kimi               switch to Kimi K3
    python tools/model.py bench              time all three on one prompt
    python tools/model.py bench "prompt"     time all three on your own prompt
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import time

CONFIG = pathlib.Path.home() / "AppData" / "Local" / "hermes" / "config.yaml"

# The provider prefix matters: 'gpt-5.6-sol' alone resolves to the openai-api
# provider and fails asking for an API key that does not exist, because the
# real credential lives under openai-codex.
CHOICES: dict[str, dict[str, str]] = {
    "claude": {
        "label": "Claude Max",
        "model": "claude-opus-4-8",
        "provider": "anthropic",
        "call": "claude-opus-4-8",
        "note": "Strongest reasoning. Use for governance decisions.",
    },
    "gpt": {
        "label": "ChatGPT Pro",
        "model": "gpt-5.6-sol",
        "provider": "openai-codex",
        "call": "openai-codex/gpt-5.6-sol",
        "note": "Balanced. Currently the automatic fallback.",
    },
    "kimi": {
        "label": "Kimi K3",
        "model": "kimi-k3",
        "provider": "kimi-coding",
        "call": "kimi-k3",
        "base_url": "https://api.kimi.com/coding",
        "note": "Large context, cheapest for long work. Runs the engine room.",
    },
}


def _read() -> str:
    return CONFIG.read_text(encoding="utf-8")


def current() -> tuple[str, str]:
    """Return (provider, model) as configured. Parsed narrowly on purpose."""
    provider = model = "?"
    inside = False
    for line in _read().splitlines():
        if line.startswith("model:"):
            inside = True
            continue
        if inside:
            if line and not line.startswith((" ", "\t")):
                break
            stripped = line.strip()
            if stripped.startswith("provider:"):
                provider = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("default:"):
                model = stripped.split(":", 1)[1].strip()
    return provider, model


def switch(key: str) -> None:
    choice = CHOICES[key]
    text = _read()
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inside = False
    changed_provider = changed_model = False

    for line in lines:
        if line.startswith("model:"):
            inside = True
            out.append(line)
            continue
        if inside and line.strip() and not line.startswith((" ", "\t")):
            inside = False
        if inside:
            stripped = line.strip()
            indent = line[: len(line) - len(line.lstrip())]
            if stripped.startswith("provider:"):
                out.append(f"{indent}provider: {choice['provider']}\n")
                changed_provider = True
                continue
            if stripped.startswith("default:"):
                out.append(f"{indent}default: {choice['model']}\n")
                changed_model = True
                # A base_url belongs to one provider only. Carrying another
                # provider's URL across a switch would silently misroute every
                # request, so the line is rewritten here and dropped below.
                if choice.get("base_url"):
                    out.append(f"{indent}base_url: {choice['base_url']}\n")
                continue
            if stripped.startswith("base_url:"):
                continue
        out.append(line)

    if not (changed_provider and changed_model):
        print("Tidak bisa menemukan blok model di config.yaml — tidak ada yang diubah.")
        sys.exit(1)

    backup = CONFIG.with_suffix(".yaml.bak")
    backup.write_text(text, encoding="utf-8")
    CONFIG.write_text("".join(out), encoding="utf-8")
    print(f"Model utama sekarang: {choice['label']} ({choice['model']})")
    print(f"  {choice['note']}")
    print(f"  Cadangan config lama: {backup}")


def _time_one(call: str, prompt: str) -> tuple[float, str]:
    start = time.monotonic()
    try:
        done = subprocess.run(
            ["hermes", "-m", call, "-z", prompt],
            capture_output=True, text=True, timeout=300,
        )
        elapsed = time.monotonic() - start
        answer = (done.stdout or done.stderr or "").strip()
        if done.returncode != 0:
            return elapsed, f"GAGAL: {answer.splitlines()[-1][:70] if answer else '?'}"
        return elapsed, answer
    except subprocess.TimeoutExpired:
        return time.monotonic() - start, "TIMEOUT setelah 300 detik"
    except OSError as error:
        return 0.0, f"GAGAL: {error}"


def bench(prompt: str) -> None:
    print(f"Prompt: {prompt}\n")
    print("Mengukur ketiganya. Ini butuh beberapa menit.\n")
    results: list[tuple[str, float, str]] = []
    for key, choice in CHOICES.items():
        print(f"  {choice['label']:14} ... ", end="", flush=True)
        elapsed, answer = _time_one(choice["call"], prompt)
        print(f"{elapsed:6.1f}s")
        results.append((choice["label"], elapsed, answer))

    print("\n" + "=" * 62)
    print("KECEPATAN (yang diukur hanya waktu, bukan mutu jawaban)")
    print("=" * 62)
    for label, elapsed, _ in sorted(results, key=lambda r: r[1]):
        print(f"  {label:14} {elapsed:6.1f}s")

    print("\n" + "=" * 62)
    print("JAWABAN — bandingkan sendiri mutunya")
    print("=" * 62)
    for label, _, answer in results:
        print(f"\n--- {label} ---")
        print(answer[:600] if answer else "(kosong)")

    print("\nCatatan: waktu bisa berbeda tiap kali dijalankan karena beban server")
    print("dan panjang jawaban. Mutu jawaban hanya Anda yang bisa menilai.")


def main() -> None:
    args = sys.argv[1:]
    provider, model = current()

    if not args:
        print(f"Model utama saat ini : {model}  (provider: {provider})\n")
        print("Pilihan:")
        for key, choice in CHOICES.items():
            active = "  <- aktif" if choice["model"] == model else ""
            print(f"  {key:8} {choice['label']:14}{active}")
            print(f"           {choice['note']}")
        print("\n  python tools/model.py claude|gpt|kimi   ganti model utama")
        print("  python tools/model.py bench             ukur kecepatan ketiganya")
        print("\nUntuk sekali pakai tanpa mengganti default:")
        for choice in CHOICES.values():
            print(f"  hermes -m {choice['call']:28} -z \"...\"")
        return

    command = args[0].lower()
    if command == "bench":
        default_prompt = (
            "In two sentences, explain the difference between a project "
            "schedule delay and a disruption claim."
        )
        bench(args[1] if len(args) > 1 else default_prompt)
        return
    if command in CHOICES:
        switch(command)
        return

    print(f"Tidak dikenal: {command}")
    print("Pakai: claude, gpt, kimi, atau bench")
    sys.exit(1)


if __name__ == "__main__":
    main()
