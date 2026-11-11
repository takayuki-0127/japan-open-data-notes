"""図1〜5（図6はダッシュボードの画面）"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

B = Path(__file__).resolve().parents[1]; R = B / "results"; FIG = B / "figures"; FIG.mkdir(exist_ok=True)
fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
fm.fontManager.addfont(fp); plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 11})
C1, C2, C3, GR = "#c0392b", "#2c6fbb", "#7f8c8d", "#bbbbbb"
o = json.load(open(R / "main.json"))
EXPO0, EXPO1 = pd.Timestamp("2025-04-01"), pd.Timestamp("2025-10-01")


def shade(ax):
    ax.axvspan(EXPO0 - pd.Timedelta(days=15), EXPO1 + pd.Timedelta(days=15), color="#f6d5d1", alpha=.6, lw=0, zorder=0)


# 図1 前年比
A = pd.read_csv(R / "A_yoy.csv", parse_dates=["date"]).set_index("date").loc["2024-01":]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
d = pd.read_csv(B / "data/lodging_pref_monthly_2011_2025.csv", parse_dates=["date"])
os_ = d[d.pref == "27大阪府"].set_index("date")["japanese"] / 1e4
for yr, c, ls in [(2024, C3, "--"), (2025, C1, "-")]:
    s = os_.loc[str(yr)]
    ax[0].plot(s.index.month, s.values, color=c, ls=ls, marker="o", ms=4, label=f"{yr}年")
ax[0].axvspan(3.5, 10.5, color="#f6d5d1", alpha=.6, lw=0)
ax[0].set_xticks(range(1, 13)); ax[0].set_xlabel("月"); ax[0].set_ylabel("万人泊")
ax[0].set_title("大阪府の日本人延べ宿泊者数（万博の期間を色づけ）"); ax[0].legend(frameon=False)
ax[1].bar(A.index - pd.Timedelta(days=7), A.osaka_yoy * 100, width=14, color=C1, label="大阪府")
ax[1].bar(A.index + pd.Timedelta(days=7), A.others_yoy * 100, width=14, color=GR, label="大阪以外の46都道府県")
shade(ax[1]); ax[1].axhline(0, color="k", lw=.6)
ax[1].set_ylabel("前年同月比（%）"); ax[1].set_title("前年同月比：大阪は伸び、ほかは横ばい〜減少")
ax[1].legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig1_yoy.png", dpi=150); plt.close(fig)

# 図2 合成対照
S = pd.read_csv(R / "C_sc_path.csv", parse_dates=[0], index_col=0) / 1e4
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [2.2, 1]})
ax[0].plot(S.index, S.actual, color=C1, lw=2, label="実際の大阪府")
ax[0].plot(S.index, S.synth, color=C2, lw=2, ls="--", label="合成の大阪（ほかの県の組み合わせ）")
shade(ax[0]); ax[0].set_ylabel("万人泊"); ax[0].legend(frameon=False, loc="upper left")
ax[0].set_title("合成対照：2023年1月〜2025年3月で合わせ、4〜10月を比べる")
w = o["C_sc"][0]["top_w"]
ax[1].barh(list(w.keys())[::-1], [v * 100 for v in list(w.values())[::-1]], color=C2)
ax[1].set_xlabel("重み（%）"); ax[1].set_title("合成に使われた県（上位）")
fig.tight_layout(); fig.savefig(FIG / "fig2_synthetic_control.png", dpi=150); plt.close(fig)

# 図3 プラセボ（場所）
G = np.load(R / "D_placebo_gaps.npy"); idx = json.load(open(R / "D_placebo_gaps_index.json"))
ti = pd.to_datetime(idx["index"]); prefs = idx["prefs"]
P = pd.read_csv(R / "D_placebo_space.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
for g, p in zip(G, prefs):
    if p == "27大阪府":
        continue
    ax[0].plot(ti, (np.exp(g) - 1) * 100, color=GR, lw=.8)
ax[0].plot(ti, (np.exp(G[prefs.index("27大阪府")]) - 1) * 100, color=C1, lw=2.2, label="大阪府")
shade(ax[0]); ax[0].axhline(0, color="k", lw=.6); ax[0].set_ylabel("実際 ÷ 合成 − 1（%）")
ax[0].set_title("ほかの41都道県を「大阪」とみなしても同じことをする"); ax[0].legend(frameon=False, loc="upper left")
import matplotlib.dates as mdates
ax[0].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
Ps = P.sort_values("ratio")
cols = [C1 if p == "27大阪府" else GR for p in Ps.pref]
ax[1].barh(range(len(Ps)), Ps.ratio, color=cols)
ax[1].set_yticks([]); ax[1].set_xlabel("期間中の外れ ÷ 合わせた期間の外れ")
ax[1].set_title(f"外れの比：大阪は{len(P)}府県中1位")
fig.tight_layout(); fig.savefig(FIG / "fig3_placebo_space.png", dpi=150); plt.close(fig)

# 図4 方法の比較
rows = [
    ("前年同月比（大阪だけ）", o["A_yoy"]["osaka_expo_yoy"], None, None, C3),
    ("前年比をほかの県で補正", float(pd.read_csv(R / "H_sql_check.csv").query("ym==99999").eff_vs_baseline_py.iloc[0]), None, None, C3),
    ("ITS：2023〜25年で学習", o["B_its"]["pre_2023_25"]["expo_eff"], o["B_its"]["pre_2023_25"]["expo_lo"], o["B_its"]["pre_2023_25"]["expo_hi"], C2),
    ("ITS：2015〜19年も使う", o["B_its"]["pre_2015_19_2023_25"]["expo_eff"], o["B_its"]["pre_2015_19_2023_25"]["expo_lo"], o["B_its"]["pre_2015_19_2023_25"]["expo_hi"], C2),
    ("BSTS（対照なし）", o["F_bsts"]["no_control"]["eff"], o["F_bsts"]["no_control"]["lo"], o["F_bsts"]["no_control"]["hi"], "#8e44ad"),
    ("BSTS（ほかの県を説明変数）", o["F_bsts"]["eff"], o["F_bsts"]["lo"], o["F_bsts"]["hi"], "#8e44ad"),
    ("合成対照（主）", o["C_sc"][0]["expo_eff"], None, None, C1),
]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
for i, (lab, e, lo, hi, c) in enumerate(rows[::-1]):
    ax[0].plot(e * 100, i, "o", color=c, ms=8)
    if lo is not None:
        ax[0].plot([lo * 100, hi * 100], [i, i], color=c, lw=2.5)
ax[0].set_yticks(range(len(rows))); ax[0].set_yticklabels([r[0] for r in rows[::-1]])
ax[0].axvline(0, color="k", lw=.6); ax[0].set_xlabel("万博期間（4〜10月）の増加（%）")
ax[0].set_title("同じデータでも、測り方で答えが変わる")
pl = [("合成対照", o["E_placebo_time"]["sc_eff"], None, None), ("ITS（2023〜24年で学習）", o["E_placebo_time"]["its_eff"], o["E_placebo_time"]["its_lo"], o["E_placebo_time"]["its_hi"]),
      ("BSTS", o["F_bsts"]["placebo_2024"]["eff"], o["F_bsts"]["placebo_2024"]["lo"], o["F_bsts"]["placebo_2024"]["hi"])]
for i, (lab, e, lo, hi) in enumerate(pl[::-1]):
    ax[1].plot(e * 100, i, "o", color=C3, ms=8)
    if lo is not None:
        ax[1].plot([lo * 100, hi * 100], [i, i], color=C3, lw=2.5)
ax[1].set_yticks(range(len(pl))); ax[1].set_yticklabels([p[0] for p in pl[::-1]])
ax[1].axvline(0, color="k", lw=.6); ax[1].set_xlabel("増加（%）")
ax[1].set_title("時期のプラセボ：\n万博のない2024年4〜10月")
fig.tight_layout(); fig.savefig(FIG / "fig4_methods.png", dpi=150); plt.close(fig)

# 図5 月ごとの効果と波及
M = pd.read_csv(R / "M_monthly.csv", parse_dates=[0], index_col=0)
Gs = pd.DataFrame(o["G_spillover"])
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
ax[0].bar(M.index, M.persons / 1e4, width=20, color=[C1 if x <= EXPO1 else C3 for x in M.index])
ax[0].axhline(0, color="k", lw=.6); ax[0].set_ylabel("実際 − 合成（万人泊）")
ax[0].set_title("月ごとの増加（合成対照）：9月が最大、閉幕後はマイナス")
ax[0].set_xticks(M.index); ax[0].set_xticklabels([f"{x.month}月" for x in M.index])
for x, v in zip(M.index, M.eff_pct):
    ax[0].text(x, (M.persons.loc[x] / 1e4) + (3 if v >= 0 else -6), f"{v*100:+.0f}%", ha="center", fontsize=9)
lab = [p[2:] for p in Gs.pref] + ["大阪府"]
val = list(Gs.expo_eff * 100) + [o["C_sc"][0]["expo_eff"] * 100]
ax[1].barh(lab, val, color=[GR] * len(Gs) + [C1]); ax[1].axvline(0, color="k", lw=.6)
ax[1].set_xlabel("期間中の増加（%、合成対照）"); ax[1].set_title("周りの府県：はっきり増えた・減ったとは言えない")
fig.tight_layout(); fig.savefig(FIG / "fig5_monthly_spillover.png", dpi=150); plt.close(fig)
print("ok")
