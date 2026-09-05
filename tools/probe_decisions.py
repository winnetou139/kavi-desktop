"""Why does the decision detail not appear on click?"""
import json, os, pathlib, subprocess, sys, time, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tests.smoke_ui_cdp import WS, CHROME, PORT, APP_URL

profile = pathlib.Path(os.environ.get("LOCALAPPDATA", ".")) / "Temp" / "kavi-dec-probe"
proc = subprocess.Popen(
    [CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
     f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
     "--disable-gpu", "--window-size=1600,1000", "about:blank"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ws = None
try:
    target = None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json", timeout=2) as r:
                tabs = json.loads(r.read().decode())
            pages = [x for x in tabs if x.get("type") == "page"]
            if pages:
                target = pages[0]["webSocketDebuggerUrl"]; break
        except Exception:
            time.sleep(0.3)
    ws = WS(target); ws.call("Runtime.enable"); ws.call("Page.enable")
    ws.call("Page.navigate", url=APP_URL); time.sleep(1.2)
    ws.evaluate("localStorage.setItem('kavi.language','en')")
    ws.evaluate("window.__errs=[];window.addEventListener('error',e=>window.__errs.push(e.message+' @'+e.lineno));")
    ws.call("Page.navigate", url=APP_URL); time.sleep(3.0)

    ws.evaluate("document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'8',bubbles:true}))")
    time.sleep(2.0)
    print("TITLE:", ws.evaluate("document.querySelector('.screen-title').innerText"))
    print("rows:", ws.evaluate("document.querySelectorAll('tr[data-decision-id]').length"))
    print("panels before:", ws.evaluate("document.querySelectorAll('.panel').length"))
    ws.evaluate("document.querySelectorAll('tr[data-decision-id]')[0].click()")
    time.sleep(1.5)
    print("ERRORS:", ws.evaluate("JSON.stringify(window.__errs)"))
    print("panels after:", ws.evaluate("document.querySelectorAll('.panel').length"))
    print("selected rows:", ws.evaluate("document.querySelectorAll('tr.sel').length"))
    body = ws.evaluate("(document.querySelector('.screen-body')||document.querySelector('.screen-split')).innerText")
    print("BODY len:", len(body))
    print("has Reversible:", "Reversible" in body)
    print("BODY tail:", body[-500:])
finally:
    if ws: ws.close()
    proc.terminate()
