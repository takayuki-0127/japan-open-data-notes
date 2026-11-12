"""302：作った HTML を Chromium で開き、大きさ・描けたか・描き終わるまでの時間を測る。
開き方：ファイルをそのまま開く（file://）で、ネットあり／ネットなし。V4 は手元のサーバー（http://localhost）でも。
"""
import functools, http.server, json, statistics, threading, zipfile, io
import pandas as pd
from playwright.sync_api import sync_playwright
from common import ROOT, RES

OUT = ROOT / "html"; N = 15
def zsize(p):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(p, p.name)
    return len(b.getvalue())

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):
        pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(OUT)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
PORT = srv.server_address[1]

def open_once(br, url, offline, wait=4000):
    ctx = br.new_context(offline=offline); pg = ctx.new_page()
    try:
        pg.goto(url, wait_until="load", timeout=30000)
    except Exception:
        pass
    try:
        pg.wait_for_function("window.__ok===true", timeout=wait); ok = True
    except Exception:
        ok = False
    t = pg.evaluate("window.__t||null")
    drawn = pg.evaluate("""()=>{const c=document.getElementById('cv');if(c){try{const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
        for(let i=3;i<d.length;i+=4){if(d[i])return true}}catch(e){}return false}const s=document.getElementById('sv');return !!(s&&s.querySelector('path'))}""")
    err = pg.evaluate("document.getElementById('err').textContent")
    k2 = pg.evaluate("document.getElementById('k2').textContent")
    ctx.close()
    return ok and drawn, t, err, k2

rows = []
with sync_playwright() as pw:
    br = pw.chromium.launch()
    for name in ("v1_cdn.html", "v2_inline.html", "v3_svg.html", "v4_fetch.html"):
        p = OUT / name
        modes = [("file・ネットあり", p.as_uri(), False), ("file・ネットなし", p.as_uri(), True)]
        if name == "v4_fetch.html":
            modes.append(("手元のサーバー", f"http://127.0.0.1:{PORT}/{name}", False))
        for mode, url, off in modes:
            r = [open_once(br, url, off) for _ in range(N)]
            ts = [x[1] for x in r if x[0] and x[1] is not None]
            rows.append({"file": name, "mode": mode, "bytes": p.stat().st_size + ((OUT / "data.json").stat().st_size if name == "v4_fetch.html" else 0),
                         "zip_bytes": zsize(p), "runs": N, "drawn": sum(1 for x in r if x[0]),
                         "median_ms": round(statistics.median(ts), 1) if ts else None, "min_ms": round(min(ts), 1) if ts else None,
                         "max_ms": round(max(ts), 1) if ts else None, "message": r[0][2], "kpi_2019ratio": r[0][3]})
    # 区分を切り替えても描けるか（V2・V3）
    inter = {}
    for name in ("v2_inline.html", "v3_svg.html"):
        ctx = br.new_context(offline=True); pg = ctx.new_page(); pg.goto((OUT / name).as_uri())
        pg.wait_for_function("window.__ok===true"); pg.select_option("#sel", "foreign")
        inter[name] = pg.evaluate("document.getElementById('k2').textContent"); ctx.close()
    big = []
    for n in (1_000, 10_000, 100_000, 300_000, 1_000_000):
        for tag in ("inline", "svg"):
            p = OUT / f"big_{tag}_{n}.html"
            r = [open_once(br, p.as_uri(), True, wait=60000) for _ in range(5)]
            ts = [x[1] for x in r if x[0] and x[1] is not None]
            big.append({"rows": n, "kind": tag, "bytes": p.stat().st_size, "zip_bytes": zsize(p), "drawn": sum(1 for x in r if x[0]),
                        "median_ms": round(statistics.median(ts), 1) if ts else None})
    br.close()
pd.DataFrame(rows).to_csv(RES / "variants.csv", index=False)
pd.DataFrame(big).to_csv(RES / "scale.csv", index=False)
json.dump({"switch_kpi_2019ratio_foreign": inter, "runs": N}, open(RES / "a302_extra.json", "w"), ensure_ascii=False, indent=1)
print(pd.DataFrame(rows).to_string()); print(pd.DataFrame(big).to_string()); print(inter)
