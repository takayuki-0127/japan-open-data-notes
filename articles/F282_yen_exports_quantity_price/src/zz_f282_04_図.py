"""04 図：6枚。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R, F = ROOT / "data" / "processed", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "savefig.dpi": 150, "figure.dpi": 150})
C = dict(V="#1f4e79", Q="#d9822b", UV="#5b8c5a", FX="#4a78b5", PCC="#c0504d", MIX="#9e9e9e", GR="#555555")
t = pd.read_csv(P / "trade_index.csv", dtype={"period": str})
res = json.load(open(R / "main.json")); rk = json.load(open(R / "reask.json"))
mp = pd.read_csv(R / "E_monthly_panel.csv", index_col=0)
cat = pd.read_csv(R / "C_categories.csv"); ar = pd.read_csv(R / "B_areas_2020_2025.csv")
SRC = "出典：財務省「貿易統計」、日本銀行「企業物価指数」「為替相場」をもとに作成"

# 図1 年の水準（世界、2020=100）
w = t[(t.kind == "CY") & (t.area == "WORLD")].copy(); w["y"] = w.period.astype(int)
w = pd.concat([w, pd.DataFrame([dict(y=2020, V=100, Q=100, UV=100)])]).drop_duplicates("y").sort_values("y")
w = w[w.y >= 2010]
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(w.y, w.V, "-o", color=C["V"], lw=2.2, label="輸出金額（円）")
ax.plot(w.y, w.UV, "-s", color=C["UV"], lw=2, label="価格指数（1単位あたりの円）")
ax.plot(w.y, w.Q, "-^", color=C["Q"], lw=2, label="数量指数")
for col, c in (("V", C["V"]), ("UV", C["UV"]), ("Q", C["Q"])):
    v = w[w.y == 2025][col].iloc[0]; ax.annotate(f"{v:.0f}", (2025, v), xytext=(6, 0), textcoords="offset points", va="center", color=c, fontsize=10)
ax.axhline(100, color="k", lw=0.8)
ax.set_title("輸出は金額で2020年の1.6倍。数量はほぼ同じで、伸びたのは価格", loc="left", fontsize=12.5)
ax.set_ylabel("指数（2020年=100）"); ax.set_xticks(range(2010, 2026, 2)); ax.legend(frameon=False, loc="upper left")
fig.text(0.01, 0.005, SRC + "（貿易指数、暦年、世界）", fontsize=8, color="#666"); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "fig1_levels.png"); plt.close(fig)

# 図2 分解（対数の差、%ポイント）
eps = [("2012→2015年\n（アベノミクスの円安）", res["abe_2012_2015"]), ("2019→2025年\n（コロナ前から）", res["base2019"]), ("2020→2025年\n（基本）", res["main_2020_2025"])]
parts = [("dQ", "数量", C["Q"]), ("dMix", "品目構成など", C["MIX"]), ("dPcc", "相手の通貨での値段", C["PCC"]), ("dFX", "円に直すときの為替", C["FX"])]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
x = np.arange(len(eps))
for i, (lab, d) in enumerate(eps):
    pos, neg = 0.0, 0.0
    for k, nm, c in parts:
        v = 100 * d[k]
        if v >= 0: ax.bar(i, v, bottom=pos, color=c, width=0.55, label=nm if i == 0 else None); pos += v
        else: ax.bar(i, v, bottom=neg, color=c, width=0.55, label=nm if i == 0 else None); neg += v
    ax.plot([i - 0.32, i + 0.32], [100 * d["dV"]] * 2, color="k", lw=2.5)
    ax.annotate(f"金額 {100*(d['V_ratio']-1):+.0f}%", (i, 100 * d["dV"]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=10)
ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels([e[0] for e in eps])
ax.set_ylabel("伸び（対数の差×100、%ポイント）")
ax.set_title("金額の伸びのほとんどは価格。価格の中では為替の分がいちばん大きい", loc="left", fontsize=12.5)
ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=9.5); ax.set_ylim(-35, 72)
fig.text(0.01, 0.005, SRC + "。黒い横線は金額の伸び（対数の差）", fontsize=8, color="#666"); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "fig2_decomposition.png"); plt.close(fig)

# 図3 月次：輸出物価（円・契約通貨）とドル円
m = mp[mp.index >= "2010-01"].copy(); xx = pd.to_datetime(m.index + "-01")
fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.plot(xx, m.Pyen, color=C["FX"], lw=2, label="輸出物価・円ベース")
ax.plot(xx, m.Pcc, color=C["PCC"], lw=2, label="輸出物価・契約通貨ベース")
ax.set_ylabel("指数（2020年=100）")
ax2 = ax.twinx(); ax2.plot(xx, m.usdjpy, color=C["GR"], lw=1.2, ls="--", label="ドル円（右目盛り）"); ax2.set_ylabel("円／ドル"); ax2.grid(False)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9.5)
ax.set_title("円ベースと契約通貨ベースの開きが「為替の分」。2021年から大きく開いた", loc="left", fontsize=12.5)
fig.text(0.01, 0.005, "出典：日本銀行「企業物価指数（2020年基準）」「外国為替相場（東京17時、月中平均）」をもとに作成", fontsize=8, color="#666"); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "fig3_prices_monthly.png"); plt.close(fig)

# 図4 類別（2020→2025年）
c2 = cat.sort_values("dPyen")
fig, ax = plt.subplots(figsize=(8.4, 4.8))
y = np.arange(len(c2))
ax.barh(y, 100 * c2.dPcc, color=C["PCC"], label="相手の通貨での値段", height=0.55)
ax.barh(y, 100 * c2.dFX, left=100 * c2.dPcc.clip(lower=0), color=C["FX"], label="円に直すときの為替", height=0.55)
for i, r in enumerate(c2.itertuples()):
    ax.annotate(f"円で{100*(r.Pyen_ratio-1):+.0f}%（相手の通貨で{100*(r.Pcc_ratio-1):+.0f}%）", (100 * r.dPyen, i), xytext=(5, 0), textcoords="offset points", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(c2.cat); ax.set_xlim(0, 95)
ax.set_xlabel("2020→2025年の上昇（対数の差×100）")
ax.set_title("7つの類別すべてで為替の分がプラス。相手の通貨でも全類別で値上げ", loc="left", fontsize=12.5)
ax.legend(frameon=False, loc="lower right", fontsize=9.5)
fig.text(0.01, 0.005, "出典：日本銀行「企業物価指数（2020年基準）」輸出物価指数の類別をもとに作成", fontsize=8, color="#666"); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "fig4_categories.png"); plt.close(fig)

# 図5 地域別の数量と価格（2020→2025年）＋ 月次の相関（遅れ別）
NM = {"WORLD": "世界", "USA": "米国", "EU": "EU", "ASIA": "アジア", "CHINA": "中国", "ASEAN": "ASEAN", "ASIA NIES": "アジアNIEs"}
a2 = ar.copy(); a2["nm"] = a2.area.map(NM)
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
ax = axs[0]; y = np.arange(len(a2))
ax.barh(y - 0.18, 100 * (a2.Q_ratio - 1), height=0.34, color=C["Q"], label="数量")
ax.barh(y + 0.18, 100 * (a2.UV_ratio - 1), height=0.34, color=C["UV"], label="価格指数")
ax.set_yticks(y); ax.set_yticklabels(a2.nm); ax.invert_yaxis(); ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("2020→2025年の変化（%）"); ax.set_xlim(-30, 95); ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.set_title("（a）相手先別：価格はどこでも+4〜7割", loc="left", fontsize=11.5)
ax = axs[1]
lags = res["H4"]["lags"]; L = sorted(int(k) for k in lags)
ax.plot(L, [lags[str(k)]["r"] for k in L], "-o", color=C["V"], lw=2, label="世界（2010年1月〜）")
ax.axhline(-0.3, color=C["PCC"], ls="--", lw=1); ax.text(0.2, -0.33, "外れの基準 −0.3", color=C["PCC"], fontsize=9, va="top")
ax.axhline(0, color="k", lw=0.8); ax.set_ylim(-0.5, 0.5)
ax.set_xlabel("実質実効為替レートの変化から何か月後か"); ax.set_ylabel("相関係数")
ax.set_title("（b）円安と数量の伸びの相関（前年同月比）", loc="left", fontsize=11.5)
fig.text(0.01, 0.005, SRC + "。(b)の相関がマイナスなら「円安の後に数量が増える」向き", fontsize=8, color="#666")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(F / "fig5_areas_lags.png"); plt.close(fig)

# 図6 問い直し：局面ごとの相手の通貨での値段の変化
ep = pd.DataFrame(rk["episodes"])
ep = ep[ep.episode.isin(["アベノミクスの円安", "2021年からの円安"])]
cats = ["総平均", "輸送用機器", "電気・電子機器", "はん用・生産用・業務用機器", "化学製品", "金属・同製品"]
fig, ax = plt.subplots(figsize=(8.6, 4.8)); y = np.arange(len(cats))
for j, (e, c, lab) in enumerate([("アベノミクスの円安", "#7f7f7f", "2012→2015年（ドル円 80→121円）"), ("2021年からの円安", C["PCC"], "2020→2025年（ドル円 107→150円）")]):
    v = [100 * (ep[(ep.episode == e) & (ep.cat == k)].Pcc_ratio.iloc[0] - 1) for k in cats]
    ax.barh(y + (j - 0.5) * 0.36, v, height=0.34, color=c, label=lab)
    for i, vv in enumerate(v): ax.annotate(f"{vv:+.0f}%", (vv, y[i] + (j - 0.5) * 0.36), xytext=(4 if vv >= 0 else -4, 0), textcoords="offset points", va="center", ha="left" if vv >= 0 else "right", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(cats); ax.invert_yaxis(); ax.axvline(0, color="k", lw=0.8); ax.set_xlim(-30, 62)
ax.set_xlabel("契約通貨ベースの輸出物価の変化（%）")
ax.set_title("前の円安では相手の通貨で値下げ、今回は値上げ。機械の値下げは前回も小さかった", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9.5, loc="upper right")
fig.text(0.01, 0.005, "出典：日本銀行「企業物価指数（2020年基準）」をもとに作成。暦年平均どうしの比較", fontsize=8, color="#666"); fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(F / "fig6_reask_contract_prices.png"); plt.close(fig)
print("figs:", sorted(p.name for p in F.glob("*.png")))
