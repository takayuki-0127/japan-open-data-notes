import pathlib
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if pathlib.Path(f).exists(): fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
ROOT = pathlib.Path(__file__).resolve().parents[1]; R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "jgb_yields_daily.csv", parse_dates=["date"]).set_index("date")
C = ["#2b6cb0", "#dd6b20", "#2f855a", "#805ad5", "#718096"]
REGS = [("2013-04-04", "2016-09-20", "量的・質的緩和"), ("2016-09-21", "2024-03-18", "長短金利操作")]

# 1 金利の推移
fig, ax = plt.subplots(figsize=(10, 5))
for c, (m, lab) in zip(C, [("y2", "2年"), ("y10", "10年"), ("y20", "20年"), ("y30", "30年")]):
    s = d.loc["1992":, m]; ax.plot(s.index, s, lw=1, color=c, label=lab)
for a, b, lab in REGS:
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="#e2e8f0", alpha=.7, lw=0)
    ax.text(pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2, 6.3, lab, ha="center", fontsize=9, color="#4a5568")
ax.axhline(0, color="#a0aec0", lw=.8); ax.set_ylabel("金利（%）"); ax.legend(ncol=4, frameon=False, loc="lower left")
ax.set_title("国債金利の推移（1992年1月〜2026年11月、日次）", loc="left")
fig.text(0.01, 0.01, "出典：財務省「国債金利情報」を加工して作成", fontsize=8, color="#718096")
fig.tight_layout(); fig.savefig(F / "f192_history.png", dpi=150); plt.close()

# 2 負荷量
Ld = pd.read_csv(R / "loadings_main.csv", index_col=0); x = [1, 2, 3, 5, 7, 10, 15, 20]
import json; S = json.load(open(R / "summary.json"))
fig, ax = plt.subplots(figsize=(9, 5))
for c, col, s in zip(C, Ld.columns, S["main"]["share"]):
    ax.plot(x, Ld[col], "o-", color=c, lw=2, label=f"{col}（{s*100:.1f}%）")
ax.axhline(0, color="#a0aec0", lw=.8); ax.set_xticks(x); ax.set_xlabel("年限（年）"); ax.set_ylabel("負荷量")
ax.legend(frameon=False, title="主成分（説明できる割合）"); ax.set_title("日々の金利の動きは3つの形でほぼ表せる（1992〜2026年、8年限）", loc="left")
fig.text(0.01, 0.01, "日次の変化（bp）の共分散行列の主成分。出典：財務省「国債金利情報」を加工して作成", fontsize=8, color="#718096")
fig.tight_layout(); fig.savefig(F / "f192_loadings.png", dpi=150); plt.close()

# 3 期間ごとの1日の動きの大きさ
rg = pd.read_csv(R / "by_regime.csv")
fig, ax = plt.subplots(figsize=(9, 5))
for c, (_, r) in zip(C, rg.iterrows()):
    ax.plot(x, [r[f"sd_y{m}"] for m in x], "o-", color=c, lw=2, label=r["期間"])
ax.axvline(10, color="#a0aec0", ls=":", lw=1); ax.set_xticks(x); ax.set_xlabel("年限（年）"); ax.set_ylabel("1日の変化の標準偏差（bp）")
ax.legend(frameon=False); ax.set_title("年限ごとの1日の動きの大きさ（期間別）", loc="left")
fig.text(0.01, 0.01, "出典：財務省「国債金利情報」を加工して作成", fontsize=8, color="#718096")
fig.tight_layout(); fig.savefig(F / "f192_regime.png", dpi=150); plt.close()

# 4 出来事
ev = pd.read_csv(R / "events.csv")
fig, ax = plt.subplots(figsize=(10, 6))
yy = np.arange(len(ev))[::-1]; w = .26
for j, (c, col, lab) in enumerate(zip(C, ["z_level", "z_slope", "z_curv"], ["水準", "傾き", "曲率"])):
    ax.barh(yy + (1 - j) * w, ev[col], height=w, color=c, label=lab)
ax.set_yticks(yy); ax.set_yticklabels([f"{a}  {b}" for a, b in zip(ev["日付"], ev["出来事"])], fontsize=9)
for v in (-2, 2): ax.axvline(v, color="#a0aec0", ls=":", lw=1)
ax.axvline(0, color="#4a5568", lw=.8); ax.set_xlabel("その日の動き ÷ 前後250営業日の標準偏差")
ax.legend(frameon=False, loc="lower right"); ax.set_title("日銀の政策決定の日、3つの形はどれだけ動いたか（前日→当日）", loc="left")
fig.text(0.01, 0.01, "点線は ±2。出典：財務省「国債金利情報」、日本銀行の公表日をもとに作成", fontsize=8, color="#718096")
fig.tight_layout(); fig.savefig(F / "f192_events.png", dpi=150); plt.close()

# 5 頑健性
rb = pd.read_csv(R / "robustness.csv")
lab = [f"{a}・{b}・{c}" for a, b, c in zip(rb["年限"].str.replace(r"（.*）", "", regex=True), rb["変化の幅"], rb["標準化"])]
fig, ax = plt.subplots(figsize=(10, 7.5)); yy = np.arange(len(rb))[::-1]; left = np.zeros(len(rb))
for c, col, ln in zip(C, ["PC1", "PC2", "PC3"], ["水準", "傾き", "曲率"]):
    ax.barh(yy, rb[col] * 100, left=left, color=c, label=ln, height=.75); left += rb[col].values * 100
ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=8.5); ax.set_xlim(0, 100); ax.set_ylim(-1.9, len(rb) - 0.4); ax.set_xlabel("説明できる割合（%）")
ax.legend(frameon=False, ncol=3, loc="lower left"); ax.set_title("年限・変化の幅・標準化を変えた24通り", loc="left")
fig.text(0.01, 0.01, "超長期まで＝2007年11月〜、代表5年限＝1999年9月〜。出典：財務省「国債金利情報」を加工して作成", fontsize=8, color="#718096")
fig.tight_layout(); fig.savefig(F / "f192_robustness.png", dpi=150); plt.close()
print(sorted(p.name for p in F.iterdir()))
