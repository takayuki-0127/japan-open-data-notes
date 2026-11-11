"""04 図：figures/ に5枚（6枚目は 06_KPIシート.py が作る画面の写し）"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
NOTE = "サンプルマート（架空）の合成データ。売上の季節と物価の動きだけ公開データ（商業動態統計・家計調査）から借りた"
M = json.load(open(RES / "main.json"))
tree = pd.read_csv(RES / "A_kpi_tree_fy2024_fy2025.csv", index_col=0)

# ---------- 図1 KPI ツリー ----------
fig, ax = plt.subplots(figsize=(13, 7.2)); ax.axis("off"); ax.set_xlim(0, 13); ax.set_ylim(0, 7.2)
def box(x, y, name, key, w=2.2, h=0.85, rate=False, color="#eef3fb"):
    v1 = tree.loc[key, "既存店_FY2025"]; ch = tree.loc[key, "既存店_変化率"]
    v0 = tree.loc[key, "既存店_FY2024"]
    if rate:
        val = f"{v1*100:.2f}%"; chs = f"{(v1-v0)*100:+.2f}pt"
    elif key in ("売上", "粗利（廃棄後）", "営業利益"):
        val = f"{v1/1e8:,.1f}億円"; chs = f"{ch*100:+.1f}%"
    elif key == "客数":
        val = f"{v1/1e4:,.0f}万回"; chs = f"{ch*100:+.1f}%"
    elif key in ("会員の延べ人数",):
        val = f"{v1/1e4:,.0f}万人"; chs = f"{ch*100:+.1f}%"
    elif key == "人時":
        val = f"{v1/1e4:,.0f}万時間"; chs = f"{ch*100:+.1f}%"
    elif key in ("客単価", "一品単価", "人時粗利"):
        val = f"{v1:,.0f}円"; chs = f"{ch*100:+.1f}%"
    else:
        val = f"{v1:,.2f}"; chs = f"{ch*100:+.1f}%"
    up_bad = key in ("廃棄率", "人件費率")
    neg = chs.startswith("-")
    col = "#c0392b" if (neg != up_bad) else "#1f6f3f"
    chs = chs.replace("-", "−")
    ax.add_patch(plt.Rectangle((x - w/2, y - h/2), w, h, fc=color, ec="#5b7db1", lw=1.2))
    ax.text(x, y + 0.17, name, ha="center", va="center", fontsize=11, weight="bold")
    ax.text(x, y - 0.18, f"{val}（{chs}）", ha="center", va="center", fontsize=9.5, color=col)
    return (x, y, w, h)
def link(a, b):
    ax.plot([a[0], b[0]], [a[1] - a[3]/2, b[1] + b[3]/2], color="#7f8c8d", lw=1)
top = box(6.5, 6.5, "営業利益（KGI）", "営業利益", w=2.8, color="#fde9d9")
gp = box(3.2, 5.0, "粗利（廃棄後）", "粗利（廃棄後）"); lab = box(6.5, 5.0, "人時粗利", "人時粗利"); oth = box(9.8, 5.0, "人件費率", "人件費率", rate=True)
for b in (gp, lab, oth): link(top, b)
sal = box(1.6, 3.4, "売上", "売上"); gpr = box(4.6, 3.4, "粗利率（廃棄後）", "粗利率（廃棄後）", rate=True)
link(gp, sal); link(gp, gpr)
hrs = box(7.4, 3.4, "人時", "人時"); link(lab, hrs)
cus = box(0.95, 1.8, "客数", "客数", w=1.75); tic = box(2.9, 1.8, "客単価", "客単価", w=1.75); link(sal, cus); link(sal, tic)
was = box(4.9, 1.8, "廃棄率", "廃棄率", rate=True, w=1.75); link(gpr, was)
mem = box(0.75, 0.45, "会員の延べ人数", "会員の延べ人数", w=1.5); link(cus, mem)
itm = box(2.3, 0.45, "買上点数", "買上点数", w=1.3); up = box(3.75, 0.45, "一品単価", "一品単価", w=1.3)
link(tic, itm); link(tic, up)
tt = tree["既存店_変化率"] * 100
ax.text(9.0, 2.6, f"FY2024→FY2025（既存店、13か月以上営業）\n・売上は +{tt['売上']:.1f}% だが、中身は一品単価 +{tt['一品単価']:.1f}%\n・客数は {tt['客数']:+.1f}%、買上点数は {tt['買上点数']:+.1f}%\n・廃棄率が上がって粗利率は {(tree.loc['粗利率（廃棄後）','既存店_FY2025']-tree.loc['粗利率（廃棄後）','既存店_FY2024'])*100:+.2f}pt\n・時給の上昇で人件費率が上がり、\n　営業利益は {tt['営業利益']:+.1f}%".replace("-", "−"), fontsize=10.5, va="top",
        bbox=dict(fc="#fffdf3", ec="#e0c97a"))
ax.set_title("図1　事業の目標（営業利益）から分けた KPI ツリーと、FY2025 の値（前年比）", fontsize=13, loc="left")
fig.text(0.01, 0.01, NOTE, fontsize=8.5, color="#555")
fig.savefig(FIG / "fig1_kpi_tree.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図2 営業利益の変化の分け方＋売上の分け方 ----------
br = pd.read_csv(RES / "A_op_bridge_existing.csv", index_col=0)["円"] / 1e6
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.4, 1]})
steps = ["売上の増減の分", "粗利率（廃棄後）の分", "うち時給の上昇", "うち人時の増減", "その他の経費の分"]
labels = ["売上が増えた分\n（粗利率は前年のまま）", "粗利率（廃棄後）\nの低下", "時給の上昇", "人時の増減", "その他の経費"]
cum = 0
for i, (s, l) in enumerate(zip(steps, labels)):
    v = br[s]; c = "#2e86c1" if v >= 0 else "#c0392b"
    a1.bar(i, v, bottom=cum if v >= 0 else cum + v, color=c, width=0.6)
    a1.text(i, cum + v + (6 if v >= 0 else -6), ("±0" if abs(v) < 0.5 else f"{v:+,.0f}").replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", fontsize=10)
    cum += v
a1.bar(len(steps), cum, color="#7f8c8d", width=0.6); a1.text(len(steps), cum - 6, f"{cum:+,.0f}", ha="center", va="top", fontsize=10, weight="bold")
a1.set_xticks(range(len(steps) + 1)); a1.set_xticklabels(labels + ["営業利益の変化"], fontsize=9)
a1.axhline(0, color="k", lw=0.8); a1.set_ylabel("百万円（既存店、FY2024→FY2025）")
a1.set_title("営業利益の変化は、売上の伸びを時給と廃棄が打ち消した", fontsize=11.5, loc="left")
t = tree["既存店_変化率"] * 100
parts = {"客数": t["客数"], "買上点数": t["買上点数"], "一品単価": t["一品単価"]}
a2.barh(list(parts)[::-1], list(parts.values())[::-1], color=["#c0392b" if v < 0 else "#2e86c1" for v in list(parts.values())[::-1]])
for i, v in enumerate(list(parts.values())[::-1]):
    a2.text(v + (0.1 if v >= 0 else -0.1), i, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right")
a2.axvline(0, color="k", lw=0.8); a2.set_xlabel("前年比（%）"); a2.set_xlim(-2.5, 5.5)
a2.set_title(f"売上 +{t['売上']:.1f}% ＝ 客数 × 買上点数 × 一品単価", fontsize=11.5, loc="left")
fig.suptitle("図2　営業利益の変化を分けると：売上は伸びたが、その中身は「値段」", fontsize=13, x=0.01, ha="left")
fig.text(0.01, -0.01, NOTE, fontsize=8.5, color="#555"); fig.tight_layout()
fig.savefig(FIG / "fig2_op_bridge.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図3 全店と既存店 ----------
y = pd.read_csv(RES / "B_yoy_all_vs_existing_13m.csv"); y24 = pd.read_csv(RES / "B_yoy_all_vs_existing_24m.csv")
x = pd.to_datetime(y.ym)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
a1.plot(x, y["全店_客数"] * 100, color="#e67e22", lw=2, label="全店の客数")
a1.plot(x, y["既存店_客数"] * 100, color="#2e86c1", lw=2, label="既存店の客数（13か月以上）")
a1.plot(x, y24["既存店_客数"] * 100, color="#2e86c1", lw=1, ls="--", label="既存店の客数（24か月以上）")
opp = np.sign(y["全店_客数"]) != np.sign(y["既存店_客数"])
for xi in x[opp]:
    a1.axvspan(xi - pd.Timedelta(days=14), xi + pd.Timedelta(days=14), color="#f5b7b1", alpha=0.6)
a1.axhline(0, color="k", lw=0.8); a1.set_ylabel("前年同月比（%）"); a1.legend(loc="upper left", fontsize=9.5)
for d, txt in (("2024-10-01", "地方1店を閉店・都市に1店を開店"), ("2025-04-01", "郊外に1店を開店"), ("2025-10-01", "地方の1店を閉店")):
    a1.axvline(pd.Timestamp(d), color="#999", lw=0.8, ls=":")
    a1.text(pd.Timestamp(d), a1.get_ylim()[1] * 0.92, txt, fontsize=8.5, rotation=90, va="top", ha="right", color="#555")
a1.set_title(f"全店と既存店で客数の前年比の向きが逆になった月：36か月中 {M['B_all_vs_existing']['13']['opp_receipts']} か月（赤い帯）", fontsize=11.5, loc="left")
a2.step(x, y["全店の数"], where="mid", color="#e67e22", label="全店の数"); a2.step(x, y["既存店の数"], where="mid", color="#2e86c1", label="既存店の数（13か月）")
a2.step(x, y24["既存店の数"], where="mid", color="#2e86c1", ls="--", label="既存店の数（24か月）")
a2.set_ylabel("店の数"); a2.legend(fontsize=8.5, ncol=3, loc="lower left"); a2.set_ylim(17, 24)
fig.suptitle("図3　「客数」を全店で見るか既存店で見るかで、良し悪しが逆になる月がある", fontsize=13, x=0.01, ha="left")
fig.text(0.01, -0.01, NOTE, fontsize=8.5, color="#555"); fig.tight_layout()
fig.savefig(FIG / "fig3_all_vs_existing.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図4 粒度と偶然の幅 ----------
cn = pd.read_csv(RES / "C_noise_by_grain.csv")
ks = ["売上", "客数", "客単価", "買上点数", "一品単価", "人時粗利", "粗利率（廃棄後）", "廃棄率"]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
for a, lvl in zip(axes, ("1店", "全社")):
    d = cn[cn.level == lvl].pivot(index="KPI", columns="grain", values="偶然の幅（±1.96σ）").reindex(ks)
    yy = np.arange(len(ks))
    for j, (gr, c) in enumerate((("日", "#d5dbdb"), ("週", "#85c1e9"), ("月", "#1f618d"))):
        a.barh(yy + (j - 1) * 0.27, d[gr], height=0.26, color=c, label=f"{gr}の前年比")
        for yi, v in zip(yy, d[gr]):
            a.text(v + 0.2, yi + (j - 1) * 0.27, f"±{v:.1f}", va="center", fontsize=7.5)
    a.set_yticks(yy); a.set_yticklabels([k + ("（pt）" if "率" in k else "（%）") for k in ks]); a.invert_yaxis()
    a.set_title(f"{lvl}" + ("（都市の中型店）" if lvl == "1店" else "（通年営業の20店の合計）"), fontsize=11.5, loc="left")
    a.set_xlabel("本当の変化がなくても出る前年比の幅（±1.96σ、乱数の種20通り）")
    a.set_xlim(0, 24 if lvl == "1店" else 6)
axes[0].legend(fontsize=9, loc="center right")
fig.suptitle("図4　同じ KPI でも、1日・1店で見ると偶然の揺れが大きい：1店の月の売上は ±6%、全社の月なら ±1.3%", fontsize=13, x=0.01, ha="left")
fig.text(0.01, -0.01, NOTE + "。営業利益は1店・月で ±205% と大きすぎるので図から外した", fontsize=8.5, color="#555"); fig.tight_layout()
fig.savefig(FIG / "fig4_noise_by_grain.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 図5 定義の違い ----------
reg = pd.read_csv(RES / "D_receipts_vs_members_by_area.csv")
adj = pd.read_csv(RES / "D_calendar_adjust.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1, 1.5]})
w = 0.26; xx = np.arange(3)
for j, (c, col, lab) in enumerate((("レシート", "#e67e22", "レシートの枚数（客数）"), ("会員の人数", "#27ae60", "会員の延べ人数"), ("来店頻度", "#8e44ad", "会員1人の月の来店回数"))):
    a1.bar(xx + (j - 1) * w, reg[c] * 100, width=w, color=col, label=lab)
    for xi, v in zip(xx, reg[c] * 100):
        a1.text(xi + (j - 1) * w, v + (0.15 if v >= 0 else -0.15), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
a1.set_xticks(xx); a1.set_xticklabels(reg["地域"]); a1.axhline(0, color="k", lw=0.8); a1.set_ylabel("前年比（%、既存店、FY2025）")
a1.legend(fontsize=8.5, loc="upper right"); a1.set_title("「客数」の定義で向きが変わる：\n会員は増えたが、地方では来店回数が減った", fontsize=11, loc="left")
xd = pd.to_datetime(adj.ym)
a2.bar(xd, adj["曜日の並びの効果"] * 100, width=20, color="#bdc3c7", label="曜日・祝日の並びの違いだけで動く分")
a2.plot(xd, adj["既存店_客数_そのまま"] * 100, color="#2e86c1", lw=1.8, label="既存店の客数（そのまま）")
a2.plot(xd, adj["既存店_客数_曜日調整後"] * 100, color="#c0392b", lw=1.8, label="既存店の客数（曜日の並びで調整）")
a2.axhline(0, color="k", lw=0.8); a2.legend(fontsize=8.5, loc="lower left"); a2.set_ylabel("前年同月比（%）")
D = M["D_definitions"]
a2.set_title(f"曜日の並びだけで ±1pt 以上動いた月：{D['月の数']}か月中 {D['曜日効果_1pt以上の月']}か月\n調整すると向きが変わる月：{D['曜日調整で符号が変わる月']}か月（最大 {D['曜日効果_最大pt']:.1f}pt）", fontsize=11, loc="left")
fig.suptitle("図5　同じ「客数」でも、数え方と比べ方で答えが変わる", fontsize=13, x=0.01, ha="left")
fig.text(0.01, -0.01, NOTE, fontsize=8.5, color="#555"); fig.tight_layout()
fig.savefig(FIG / "fig5_definitions.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("ok")
