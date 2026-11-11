"""F271 04 測定：Playwright で3つの画面（と共通の元データの表）を開き、答えになる要素の位置を集める。
問いごとに「読む人の手順」を決めて、スクロール・クリック・マウス当て・読む・比べる・計算・探す の数を数え、
画面から読んだ値で答えを出して正解と照らす（results/tasks.csv）。時間への換算は 05 で行う。"""
import os, sys, json, math, asyncio
import numpy as np, pandas as pd
from playwright.async_api import async_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
DASH = os.path.join(ROOT, "dashboard")
p = pd.read_csv(os.path.join(ROOT, "data", "processed", "panel.csv"))
G = ["百貨店", "スーパー", "コンビニ", "ドラッグストア", "ホームセンター", "家電大型専門店"]; T = "6業態合計"
months = sorted(p.ym.unique()); MI = {m: i for i, m in enumerate(months)}
EXCL = {m for m in months if "2020-03" <= m <= "2021-12"}
TRUTH = {(r.g, r.ym): r for r in p.itertuples()}
MAIN = months[MI["2024-09"]:MI["2026-08"] + 1]
COVID = months[MI["2020-03"]:MI["2021-02"] + 1]
VPS = {"pc": (1366, 768), "sp": (390, 844), "pc_s": (1280, 720), "pc_l": (1920, 1080)}
RUNS = [(vp, MAIN) for vp in VPS] + [("pc", COVID), ("sp", COVID)]
QS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "X1", "X2", "X3", "X4"]
sh = lambda m, k: months[MI[m] + k]

COLLECT = r"""()=>{const r=e=>{const b=e.getBoundingClientRect();return [b.left+scrollX,b.top+scrollY,b.width,b.height]};
const grp=e=>{let x=e;while(x&&!x.dataset?.grp)x=x.parentElement;return x?x.dataset.grp:''};const o={k:[],it:[],vw:innerWidth,vh:innerHeight,
H:document.documentElement.scrollHeight,W:document.documentElement.scrollWidth};
document.querySelectorAll('[data-k]').forEach(e=>{const k=e.dataset.k;if(k.startsWith('flag|'))return;o.k.push([k,e.dataset.v,r(e),e.dataset.hover?1:0,grp(e)]);
 if(e.dataset.rank){const g=k.split('|')[1],m=k.split('|')[2];o.k.push(['rank|'+e.dataset.rank+'|'+m,g+'|'+e.dataset.v,r(e),0,grp(e)]);o.k.push(['flag|'+g+'|'+m,e.dataset.flag,r(e),0,grp(e)])}});
document.querySelectorAll('[data-item]').forEach(e=>o.it.push([e.dataset.grp,r(e)]));
const s=document.getElementById('sel');o.sel=s?r(s):null;const a=document.getElementById('raw');o.raw=a?r(a):null;return o}"""

class Page:
    def __init__(self, o):
        self.vw, self.vh, self.H, self.W = o["vw"], o["vh"], o["H"], o["W"]
        self.keys = {}
        for k, v, b, hv, g in o["k"]:
            self.keys.setdefault(k, []).append(dict(v=v, b=b, hover=hv, grp=g))
        self.items = o["it"]; self.sel = o["sel"]; self.raw = o["raw"]

class Cnt:
    def __init__(self): self.c = dict(P=0, B=0, K=0, M=0, C=0, R=0, SCR=0, SRCH=0, HOV=0, SELN=0, FB=0, CALC=0, POSR=0)
    def add(self, **kw):
        for k, v in kw.items(): self.c[k] += v

class Viewer:
    """1枚のページの上で、見えている範囲を動かしながら値を読む。"""
    def __init__(self, page, cnt): self.pg, self.cnt, self.sx, self.sy = page, cnt, 0.0, 0.0
    def visible(self, b):
        return b[1] >= self.sy - 1 and b[1] + b[3] <= self.sy + self.pg.vh + 1 and b[0] >= self.sx - 1 and b[0] + b[2] <= self.sx + self.pg.vw + 1
    def goto(self, b):
        if not self.visible(b):
            ny = max(0.0, min(self.pg.H - self.pg.vh, b[1] - 0.25 * self.pg.vh)) if not (b[1] >= self.sy and b[1] + b[3] <= self.sy + self.pg.vh) else self.sy
            nx = max(0.0, min(self.pg.W - self.pg.vw, b[0] - 0.25 * self.pg.vw)) if not (b[0] >= self.sx and b[0] + b[2] <= self.sx + self.pg.vw) else self.sx
            scr = math.ceil(abs(ny - self.sy) / self.pg.vh - 1e-9) + math.ceil(abs(nx - self.sx) / self.pg.vw - 1e-9)
            self.cnt.add(SCR=max(1, scr)); self.sy, self.sx = ny, nx
    def search(self, grp):
        vis = [(g, b) for g, b in self.pg.items if self.visible(b)]
        ng = len({g for g, _ in vis}); ni = sum(1 for g, _ in vis if g == grp)
        self.cnt.add(SRCH=ng + ni)  # 2段の探索（まとまりを探す→その中を探す）。時間は（数/2）×1つあたり
    def read(self, e):
        self.goto(e["b"]); self.search(e["grp"])
        if e["hover"]: self.cnt.add(P=1, HOV=1, R=1)
        else: self.cnt.add(R=1)
        return e["v"]

def pick(lst):
    return sorted(lst, key=lambda e: (e["hover"], e["b"][1], e["b"][0], e["grp"]))[0]

class Reader:
    """1つの画面・1つの最新月について、値の取り方（直接・計算・元データの表）を決めて数える。"""
    def __init__(self, design, pages, L):
        self.d, self.P, self.L = design, pages, L  # pages: {'main':Page, 'sel:<g>':Page, 'fb':Page}
    def where(self, k):
        if k in self.P["main"].keys: return "main"
        for s, pg in self.P.items():
            if s.startswith("sel:") and k in pg.keys: return s
        if k in self.P["fb"].keys: return "fb"
        return None
    # ---- 値の解き方：(葉のキーの集合, 計算の K, M)
    def need(self, kind, g, m, leaves, calc):
        k = f"{kind}|{g}|{m}"
        w = self.where(k)
        if kind == "lvl" or (w is not None and w != "fb"):
            leaves.add(k); return
        if kind == "yoy":
            self.need("lvl", g, m, leaves, calc); self.need("lvl", g, sh(m, -12), leaves, calc); calc["K"] += 15; calc["M"] += 1; calc["CALC"] += 1; return
        if kind == "yoy12":
            for j in range(-23, 1): self.need("lvl", g, sh(m, j), leaves, calc)
            calc["K"] += 24 * 7 + 15; calc["M"] += 3; calc["CALC"] += 1; return
        if kind == "flag":
            self.need("yoy", g, m, leaves, calc); n = 0
            for j in range(-36, 0):
                mm = sh(m, j)
                if MI[mm] >= 12 and mm not in EXCL: self.need("yoy", g, mm, leaves, calc); n += 1
            calc["K"] += 7 * n; calc["M"] += 5; calc["CALC"] += 1; return
        raise ValueError(k)
    def run(self, leaves, cnt, extra_reads=0, peak=None):
        """葉のキーを、画面の状態ごとにまとめて、上から順に読む。"""
        vals = {}
        groups = {}
        for k in leaves:
            groups.setdefault(self.where(k), []).append(k)
        v = Viewer(self.P["main"], cnt)
        for k in sorted(groups.get("main", []), key=lambda k: (pick(self.P["main"].keys[k])["b"][1], pick(self.P["main"].keys[k])["b"][0], k)):
            vals[k] = v.read(pick(self.P["main"].keys[k]))
        for s in sorted(x for x in groups if x and x.startswith("sel:")):
            pg = self.P[s]; v.goto(self.P["main"].sel); v.search("sec")
            cnt.add(P=2, B=2, SRCH=7, M=1, SELN=1)  # 開く→選ぶ（7つの中から探す）→描き直しを待って見直す
            v2 = Viewer(pg, cnt); v2.sx, v2.sy = v.sx, v.sy
            for k in sorted(groups[s], key=lambda k: (pick(pg.keys[k])["b"][1], pick(pg.keys[k])["b"][0], k)):
                vals[k] = v2.read(pick(pg.keys[k]))
            v = v2
        if groups.get("fb"):
            v.goto(self.P["main"].raw); v.search("sec" if self.d != "d2" else "head"); cnt.add(P=1, B=1, M=1, FB=1)
            v3 = Viewer(self.P["fb"], cnt)
            for k in sorted(groups["fb"], key=lambda k: (pick(self.P["fb"].keys[k])["b"][1], pick(self.P["fb"].keys[k])["b"][0], k)):  # 同じ行は左から（集合の順に依らないように）
                vals[k] = v3.read(pick(self.P["fb"].keys[k]))
        cnt.add(R=extra_reads)
        if None in groups: raise ValueError(("missing", groups[None]))
        return vals
    # ---- 読んだ値から答える
    def lv(self, vals, g, m): return float(vals[f"lvl|{g}|{m}"])
    def yv(self, vals, g, m):
        k = f"yoy|{g}|{m}"
        return float(vals[k]) if k in vals else (self.lv(vals, g, m) / self.lv(vals, g, sh(m, -12)) - 1) * 100
    def ask(self, q):
        L, cnt, calc, leaves = self.L, Cnt(), dict(K=0, M=0, CALC=0), set()
        extra, comp = 0, 0
        main = self.P["main"].keys
        if q == "Q1":
            self.need("yoy", T, L, leaves, calc); vals = self.run(leaves, cnt); ans = round(self.yv(vals, T, L), 1)
        elif q == "Q2":
            if f"rank|1|{L}" in main:
                vals = self.run({f"rank|1|{L}"}, cnt); ans = vals[f"rank|1|{L}"].split("|")[0]
            else:
                for g in G: self.need("yoy", g, L, leaves, calc)
                vals = self.run(leaves, cnt); comp = 5; ans = max(G, key=lambda g: self.yv(vals, g, L))
        elif q == "Q3":
            if f"rank|1|{L}" in main:
                ys = {r: float(main[f"rank|{r}|{L}"][0]["v"].split("|")[1]) for r in range(1, 7)}
                nneg = sum(1 for r in ys if ys[r] < 0); ks = {f"rank|{r}|{L}" for r in range(6, 6 - min(6, nneg + 1), -1)}
                vals = self.run(ks, cnt); ans = sorted(x.split("|")[0] for x in vals.values() if float(x.split("|")[1]) < 0)
            else:
                for g in G: self.need("yoy", g, L, leaves, calc)
                vals = self.run(leaves, cnt); ans = sorted(g for g in G if self.yv(vals, g, L) < 0)
        elif q == "Q4":
            self.need("yoy", "スーパー", L, leaves, calc); self.need("yoy", "スーパー", sh(L, -1), leaves, calc)
            vals = self.run(leaves, cnt); comp = 1; ans = self.yv(vals, "スーパー", L) > self.yv(vals, "スーパー", sh(L, -1))
        elif q == "Q5":
            g = "ドラッグストア"
            if self.where(f"yoy|{g}|{L}") in ("main",) or (self.where(f"yoy|{g}|{L}") or "").startswith("sel"):
                vals = self.run({f"yoy|{g}|{L}"}, cnt); ans = float(vals[f"yoy|{g}|{L}"]) > 0
            else:
                vals = self.run({f"lvl|{g}|{L}", f"lvl|{g}|{sh(L, -12)}"}, cnt); comp = 1; ans = self.lv(vals, g, L) > self.lv(vals, g, sh(L, -12))
        elif q == "Q6":
            if f"flag|{G[0]}|{L}" in main:
                fl = [g for g in G if main[f"flag|{g}|{L}"][0]["v"] == "外"]
                vals = self.run({f"flag|{g}|{L}" for g in fl}, cnt, extra_reads=1); ans = sorted(fl)
            else:
                for g in G: self.need("flag", g, L, leaves, calc)
                vals = self.run(leaves, cnt); res = []
                for g in G:
                    y = self.yv(vals, g, L); win = [sh(L, j) for j in range(-36, 0) if MI[sh(L, j)] >= 12 and sh(L, j) not in EXCL]
                    a = np.array([self.yv(vals, g, mm) for mm in win]); mu, sd = a.mean(), a.std(ddof=1)
                    if y < mu - 1.645 * sd or y > mu + 1.645 * sd: res.append(g)
                comp = 12; ans = sorted(res)
        elif q == "Q7":
            self.need("yoy12", T, L, leaves, calc); vals = self.run(leaves, cnt)
            k = f"yoy12|{T}|{L}"
            if k in vals: ans = float(vals[k]) > 0
            else:
                s1 = sum(self.lv(vals, T, sh(L, j)) for j in range(-11, 1)); s0 = sum(self.lv(vals, T, sh(L, j)) for j in range(-23, -11)); ans = s1 > s0
        elif q == "Q8":
            vals = self.run({"latest"}, cnt); ans = vals["latest"]
        elif q == "X1":
            vals = self.run({f"lvl|百貨店|{L}"}, cnt); ans = int(vals[f"lvl|百貨店|{L}"])
        elif q == "X2":
            m0 = "2019-" + L[5:]; vals = self.run({f"lvl|コンビニ|{L}", f"lvl|コンビニ|{m0}"}, cnt); comp = 1
            ans = self.lv(vals, "コンビニ", L) > self.lv(vals, "コンビニ", m0)
        elif q == "X3":
            vals = self.run({f"lvl|{g}|{L}" for g in G}, cnt); comp = 5; ans = max(G, key=lambda g: self.lv(vals, g, L))
        elif q == "X4":
            g = "ホームセンター"; ms = months[:MI[L] + 1]
            tr = max(ms, key=lambda m: TRUTH[(g, m)].lvl)
            s = "sel:" + g
            if s in self.P and f"lvl|{g}|{tr}" in self.P[s].keys:
                i = ms.index(tr); nb = [ms[j] for j in (i - 1, i, i + 1) if 0 <= j < len(ms)]
                vals = self.run({f"lvl|{g}|{m}" for m in nb}, cnt); comp = len(nb) - 1
                ans = max(nb, key=lambda m: self.lv(vals, g, m))
            else:
                vals = self.run({f"lvl|{g}|{m}" for m in ms}, cnt); comp = len(ms) - 1; ans = max(ms, key=lambda m: self.lv(vals, g, m))
        cnt.add(K=calc["K"], M=calc["M"], C=comp, CALC=calc["CALC"])
        return cnt.c, ans, leaves_or(vals)
def leaves_or(vals): return len(vals)

def truth(q, L):
    t = lambda g, m: TRUTH[(g, m)]
    if q == "Q1": return round(t(T, L).yoy, 1)
    if q == "Q2": return max(G, key=lambda g: t(g, L).yoy)
    if q == "Q3": return sorted(g for g in G if t(g, L).yoy < 0)
    if q == "Q4": return t("スーパー", L).yoy > t("スーパー", sh(L, -1)).yoy
    if q == "Q5": return t("ドラッグストア", L).lvl > t("ドラッグストア", sh(L, -12)).lvl
    if q == "Q6": return sorted(g for g in G if t(g, L).flag == 1)
    if q == "Q7": return t(T, L).yoy12 > 0
    if q == "Q8": return L
    if q == "X1": return int(round(t("百貨店", L).lvl))
    if q == "X2": return t("コンビニ", L).lvl > t("コンビニ", "2019-" + L[5:]).lvl
    if q == "X3": return max(G, key=lambda g: t(g, L).lvl)
    if q == "X4": return max(months[:MI[L] + 1], key=lambda m: t("ホームセンター", m).lvl)

async def collect(pg, url):
    await pg.goto(url); await pg.evaluate("document.fonts.ready.then(()=>1)"); await pg.wait_for_timeout(120)
    # 文字の読み込みと配置が終わってから位置を集める（終わる前だと、スマートフォンの表の幅が1px単位でずれ、スクロールの数が±1変わることがあった）
    o = await pg.evaluate(COLLECT); await pg.wait_for_timeout(30); o2 = await pg.evaluate(COLLECT)
    assert o["W"] == o2["W"] and o["H"] == o2["H"], url
    return Page(o2)

async def main():
    rows = []; checks = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        for vp, mset in RUNS:
            w, h = VPS[vp]; pg = await b.new_page(viewport={"width": w, "height": h})
            for L in mset:
                fb = await collect(pg, f"file://{DASH}/table.html?m={L}")
                for d in ["d1", "d2", "d3", "d4"]:  # d4 は問い直しで足した（D3＋水準）
                    pages = {"main": await collect(pg, f"file://{DASH}/{d}.html?m={L}"), "fb": fb}
                    if d in ("d1", "d4"):
                        for g in G:
                            pages["sel:" + g] = await collect(pg, f"file://{DASH}/d1.html?m={L}&sel={g}")
                    R = Reader(d, pages, L)
                    for q in QS:
                        c, ans, nv = R.ask(q); tr = truth(q, L)
                        ok = (abs(ans - tr) <= 0.051) if isinstance(tr, float) else (ans == tr)
                        # 最初の画面だけで答えられるか：スクロール・クリック・マウス当て・計算・元データの表 なし
                        first = c["SCR"] == 0 and c["HOV"] == 0 and c["SELN"] == 0 and c["CALC"] == 0 and c["FB"] == 0
                        rows.append(dict(vp=vp, period="main" if mset is MAIN else "covid", design=d, ym=L, q=q, ok=ok, first=first, nvals=nv, **c))
            # 実際の操作の確かめ（各画面の大きさで1回）：マウスを当てるとツールチップに値が出るか、プルダウンで線が変わるか
            L = mset[-1]
            await pg.goto(f"file://{DASH}/d1.html?m={L}"); await pg.wait_for_timeout(100)
            el = pg.locator(f'#c2 circle[data-k="lvl|コンビニ|{L}"]'); await el.scroll_into_view_if_needed(); await el.hover(force=True)
            tip = await pg.evaluate("document.getElementById('tip').textContent")
            await pg.select_option("#sel", "ホームセンター"); await pg.wait_for_timeout(50)
            n_hc = await pg.locator('#c1 circle[data-k^="lvl|ホームセンター|"]').count()
            checks.append(dict(vp=vp, L=L, tip=tip, expect=str(int(round(TRUTH[("コンビニ", L)].lvl))), sel_points=n_hc))
            await pg.close()
        await b.close()
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    df = pd.DataFrame(rows); df.to_csv(os.path.join(ROOT, "results", "tasks.csv"), index=False)
    json.dump(checks, open(os.path.join(ROOT, "results", "interaction_checks.json"), "w"), ensure_ascii=False, indent=1)
    print(df.groupby(["vp", "period", "design"]).ok.mean().round(3).to_string())
    print(checks)
asyncio.run(main())
