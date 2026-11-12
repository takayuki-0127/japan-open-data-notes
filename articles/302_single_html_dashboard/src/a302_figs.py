"""302：図を作る（画面の写し・作り方ごとの大きさと時間・行数を増やしたとき）"""
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from playwright.sync_api import sync_playwright
from common import ROOT, RES, FIG, BLUE, ORANGE, GRAY, INK, GREEN, save

SRC = "出典：観光庁「宿泊旅行統計調査」（246 の写し）をもとに作成者が加工して作成。時間は Chromium で測った中央値"
OUT = ROOT / "html"
with sync_playwright() as pw:                      # 図1：V3（部品なし）の画面を、ネットなしで開いた写し
    br = pw.chromium.launch(); ctx = br.new_context(offline=True, viewport={"width": 960, "height": 560}, device_scale_factor=2)
    pg = ctx.new_page(); pg.goto((OUT / "v3_svg.html").as_uri()); pg.wait_for_function("window.__ok===true")
    pg.screenshot(path=str(FIG / "a302_screen.png")); br.close()

v = pd.read_csv(RES / "variants.csv")
NAME = {"v1_cdn.html": "V1 部品を CDN から", "v2_inline.html": "V2 部品も中に", "v3_svg.html": "V3 部品なし（SVG）", "v4_fetch.html": "V4 データだけ別ファイル"}
fig, ax = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.75})
files = list(NAME); kb = [v[v.file == f].bytes.iloc[0] / 1024 for f in files]
ax[0].barh([NAME[f] for f in files][::-1], kb[::-1], color=[GRAY, BLUE, GREEN, ORANGE][::-1])
for i, k in enumerate(kb[::-1]):
    ax[0].text(k + 3, i, f"{k:.0f} KB", va="center", fontsize=9)
ax[0].set_xlim(0, 270); ax[0].set_title("ファイルの大きさ", fontsize=11)
modes = ["file・ネットあり", "file・ネットなし", "手元のサーバー"]
cell = []
for f in files:
    r = []
    for m in modes:
        q = v[(v.file == f) & (v["mode"] == m)]
        if q.empty: r.append("（試していない）")
        elif q.drawn.iloc[0] == 0: r.append("描けない（0/15）")
        else: r.append(f"描けた　{q.median_ms.iloc[0]:.0f} ミリ秒")
    cell.append(r)
ax[1].axis("off")
tb = ax[1].table(cellText=cell, rowLabels=[NAME[f] for f in files], colLabels=["そのまま開く\n（ネットあり）", "そのまま開く\n（ネットなし）", "手元のサーバー\nから開く"], loc="center", cellLoc="center", bbox=[0.0, 0.05, 1.0, 0.85])
tb.auto_set_font_size(False); tb.set_fontsize(9)
for (r_, c_), c in tb.get_celld().items():
    c.set_edgecolor("#d9d8d2")
    if r_ == 0: c.set_facecolor("#f0efe9")
    elif "描けない" in c.get_text().get_text(): c.set_facecolor("#fbe3da")
ax[1].set_title("開き方ごとに、グラフが描けたか（15回ずつ）", fontsize=11)
save(fig, "a302_variants.png", SRC, y=0.0)

s = pd.read_csv(RES / "scale.csv")
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
for k, c, n in (("inline", BLUE, "V2 部品も中に"), ("svg", GREEN, "V3 部品なし")):
    q = s[s.kind == k]
    ax[0].plot(q.rows, q.bytes / 1e6, color=c, marker="o", label=n); ax[1].plot(q.rows, q.median_ms, color=c, marker="o", label=n)
for a, t, y in ((ax[0], "ファイルの大きさ（MB）", "MB"), (ax[1], "描き終わるまでの時間（ミリ秒）", "ミリ秒")):
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlabel("中に入れた明細の行数"); a.set_title(t, fontsize=11); a.legend(frameon=False, fontsize=9)
ax[0].axhline(10, color=ORANGE, ls="--", lw=1); ax[0].text(1100, 11.5, "10MB", color=ORANGE, fontsize=9)
ax[1].axhline(1000, color=ORANGE, ls="--", lw=1); ax[1].text(1100, 1150, "1秒", color=ORANGE, fontsize=9)
save(fig, "a302_scale.png", "架空の明細（作成者が乱数で作成、seed 302）を HTML の中に入れ、画面で月ごとに集計してから描いた。5回の中央値")
