"""04 図：5枚"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, RES, FIG

FIG.mkdir(exist_ok=True)
D = "D_気温＋傾向＋季節"
C1, C2, C3, C4, GR = "#2a6f97", "#d1495b", "#edae49", "#66a182", "#888888"

# ---- 図1 成分に分ける
c = pd.read_csv(RES / "components_full.csv", parse_dates=["date"])
fig, ax = plt.subplots(4, 1, figsize=(9, 8.4), sharex=True)
ax[0].plot(c.date, np.exp(c.log_d), lw=0.4, color=GR)
ax[0].set_ylabel("GWh／日")
ax[0].set_title("東京エリアの1日の電力需要（2016年4月〜2026年9月）", loc="left", fontsize=11)
for a_, col, lab, colr in [(ax[1], "temp", "気温の成分", C2), (ax[2], "trend", "ゆっくりした変化（傾向）", C1), (ax[3], "season", "気温以外の季節の形", C4)]:
    a_.plot(c.date, (np.exp(c[col] - c[col].mean()) - 1) * 100, lw=0.6 if col == "temp" else 1.4, color=colr)
    a_.axhline(0, color="k", lw=0.5)
    a_.set_ylabel("%")
    a_.set_title(lab + "（平均からの差、%）", loc="left", fontsize=11)
ax[3].xaxis.set_major_locator(mdates.YearLocator(2))
ax[3].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.text(0.01, 0.005, "曜日・祝日・お盆・年末年始・GW・コロナ期の成分と、数日単位のずれの成分は省略。出典：東京電力パワーグリッド、気象庁をもとに作成",
         fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "f104_1_components.png", dpi=130)
plt.close(fig)

# ---- 図2 気温と需要の曲線：GP と スプライン回帰（F67 型）
g = pd.read_csv(RES / "temp_curve_全期間.csv")
j = json.load(open(RES / "read_full.json"))
d = pd.read_csv(DATA / "gp_daily_tokyo.csv", parse_dates=["date"])
d["fy"] = np.where(d.date.dt.month >= 4, d.date.dt.year, d.date.dt.year - 1)
m = smf.ols("log_d ~ cr(temp_mean, df=8) + C(dow) + holiday + obon + nenmatsu + gw + covid + C(fy)", data=d).fit()
grid = pd.DataFrame({"temp_mean": g.temp, "dow": 2, "holiday": 0, "obon": 0, "nenmatsu": 0, "gw": 0, "covid": 0, "fy": 2024})
sp = m.predict(grid).values
gb = pd.read_csv(RES / "temp_curve_全期間_B.csv")
fig, ax = plt.subplots(figsize=(8, 5))
pc = lambda v: (np.exp(v) - 1) * 100
ax.fill_between(gb.temp, pc(gb.rel_lo), pc(gb.rel_hi), color="#9d6fb0", alpha=0.18)
ax.plot(gb.temp, pc(gb.rel_med), color="#9d6fb0", lw=2, label=f"GP 気温だけ（暑い日 {j['B']['hot'][0]:+.1f}%／℃）")
ax.fill_between(g.temp, pc(g.rel_lo), pc(g.rel_hi), color=C2, alpha=0.2)
ax.plot(g.temp, pc(g.rel_med), color=C2, lw=2, label=f"GP 気温＋傾向＋季節＋短期（{j['hot'][0]:+.1f}%／℃）")
ax.plot(g.temp, pc(sp - sp.min()), color=C1, lw=1.5, ls="--", label="スプライン回帰（F67 と同じ形、+4.5%／℃）")
mt = j["min_temp"]
ax.axvline(mt[0], color=GR, lw=0.8)
ax.text(mt[0] + 0.3, 52, f"いちばん少ない {mt[0]}℃\n（95%区間 {mt[1]}〜{mt[2]}℃）", fontsize=9)
ax.set_xlabel("日平均気温（℃）")
ax.set_ylabel("いちばん少ない気温の日と比べた需要（%）")
ax.set_xlim(-1, 33)
ax.set_ylim(-3, 62)
ax.legend(loc="upper left", fontsize=9)
ax2 = ax.twinx()
ax2.hist(d.temp_mean, bins=np.arange(-1, 33.5, 1), color=GR, alpha=0.18)
ax2.set_ylim(0, 1500)
ax2.set_yticks([])
ax.set_title("気温と需要の関係：季節の成分を入れると、暑さの効き目が小さく読める", loc="left", fontsize=11)
fig.text(0.01, 0.005, "曜日・祝日などをそろえ、いちばん少ない気温の日と比べた差。帯は形の95%区間、灰色の棒は日数。\n出典：東京電力パワーグリッド、気象庁をもとに作成", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(FIG / "f104_2_temp_curve.png", dpi=130)
plt.close(fig)

# ---- 図3 予測の幅の例（2025年7月1日起点）
fc = pd.read_csv(RES / "fc_main.csv", parse_dates=["origin"])
fc["date"] = pd.to_datetime(fc.date.astype(str).str[:10])
o = pd.Timestamp("2025-07-01")
hist = d[(d.date >= o - pd.Timedelta(days=60)) & (d.date < o)]
fig, ax = plt.subplots(3, 1, figsize=(9, 8.4), sharex=True, sharey=True)
for a_, k, lab, col in [(ax[0], "A_時刻だけ", "時刻だけで予測（気温を使わない）", C4),
                        (ax[1], D, "気温を入れて予測：実際の気温が分かっている場合", C2),
                        (ax[2], D + "｜気温シナリオ", "気温を入れて予測：先の気温は過去9年の同じ時期の気温で代用", C3)]:
    s = fc[(fc.origin == o) & (fc.model == k)]
    a_.plot(hist.date, hist.demand_gwh, color="k", lw=0.8)
    a_.fill_between(s.date, np.exp(s.lo), np.exp(s.hi), color=col, alpha=0.3)
    a_.plot(s.date, np.exp(s.m), color=col, lw=1.4)
    a_.plot(s.date, np.exp(s.y), color="k", lw=0.8)
    a_.axvline(o, color=GR, ls=":")
    ape = (np.abs(np.exp(s.m - s.y) - 1)).mean() * 100
    cov = ((s.y >= s.lo) & (s.y <= s.hi)).mean() * 100
    a_.set_title(f"{lab}　誤差 {ape:.1f}%・95%区間に入った日 {cov:.0f}%", loc="left", fontsize=10.5)
    a_.set_ylabel("GWh／日")
ax[2].xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
fig.text(0.01, 0.005, "黒線が実績、色の線が予測（中央値）、帯が95%区間。2023年7月〜2025年6月で学習。出典：東京電力パワーグリッド、気象庁をもとに作成",
         fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "f104_3_fan.png", dpi=130)
plt.close(fig)

# ---- 図4 28回の予測の成績
sc = pd.read_csv(RES / "score_main.csv")
models = [("A_時刻だけ", "時刻だけ", C4), ("OLS_スプライン", "スプライン回帰", C1), ("B_気温だけ", "GP 気温だけ", "#9d6fb0"),
          (D, "GP 気温＋傾向＋季節", C2), (D + "｜平年の気温", "同 平年の気温で", "#e8a0a8"), (D + "｜気温シナリオ", "同 気温シナリオで", C3)]
hz = ["1〜7日先", "8〜30日先", "31〜90日先"]
fig, ax = plt.subplots(1, 3, figsize=(11, 4.6))
w = 0.13
for i, (k, lab, col) in enumerate(models):
    s = sc[sc.model == k].set_index("horizon").reindex(hz)
    x = np.arange(3) + (i - 2.5) * w
    ax[0].bar(x, s.MAPE, w, color=col, label=lab)
    ax[1].bar(x, s.cover95 * 100, w, color=col)
    ax[2].bar(x, s.width, w, color=col)
for a_, t in zip(ax, ["誤差（MAPE、%）", "95%区間に入った割合（%）", "95%区間の幅（予測値の%）"]):
    a_.set_xticks(range(3))
    a_.set_xticklabels(hz, fontsize=9)
    a_.set_title(t, loc="left", fontsize=10.5)
ax[1].axhline(95, color="k", lw=0.8, ls="--")
ax[1].set_ylim(50, 100)
h_, l_ = ax[0].get_legend_handles_labels()
fig.legend(h_, l_, ncol=6, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 0.04), frameon=False)
fig.suptitle("2024年4月〜2026年7月の毎月1日を起点に90日先まで予測（28回、直前2年で学習）", x=0.01, ha="left", fontsize=11)
fig.text(0.01, 0.005, "「平年の気温」「気温シナリオ」以外は、実際の気温を使った場合。出典：東京電力パワーグリッド、気象庁をもとに作成", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.09, 1, 0.95))
fig.savefig(FIG / "f104_4_scores.png", dpi=130)
plt.close(fig)

# ---- 図5 頑健性
rb = pd.read_csv(RES / "score_robust.csv")
allh = rb[rb.horizon.str.startswith("1〜90") | rb.horizon.str.startswith("1〜13")]
base_ = sc[sc.horizon == "1〜90日先"]
rows = []
for lab, src, k in [("本体（2年で学習）", base_, D), ("1年で学習", allh[allh.setting == "train1y"], D), ("3年で学習", allh[allh.setting == "train3y"], D),
                    ("気温を Matern 5/2 に", allh[allh.setting == "matern"], "D_Matern"), ("週ごとに粗く（13週先まで）", allh[allh.setting == "weekly"], D),
                    ("関西（1年で学習）", allh[allh.setting == "kansai"], D),
                    ("　関西：時刻だけ", allh[allh.setting == "kansai"], "A_時刻だけ"), ("　関西：スプライン回帰", allh[allh.setting == "kansai"], "OLS_スプライン"),
                    ("　週ごと：時刻だけ", allh[allh.setting == "weekly"], "A_時刻だけ")]:
    s = src[src.model == k]
    if len(s):
        rows.append((lab, float(s.MAPE.iloc[0]), float(s.cover95.iloc[0]) * 100, float(s.width.iloc[0])))
r = pd.DataFrame(rows, columns=["設定", "MAPE", "cover", "width"])
r.to_csv(RES / "robust_fig.csv", index=False)
fig, ax = plt.subplots(1, 3, figsize=(11, 4.8), sharey=True)
y = np.arange(len(r))[::-1]
for a_, col, t, ref in [(ax[0], "MAPE", "誤差（%）", None), (ax[1], "cover", "95%区間に入った割合（%）", 95), (ax[2], "width", "区間の幅（%）", None)]:
    a_.barh(y, r[col], color=[C2 if not s.startswith("　") else GR for s in r.設定])
    for yy, v in zip(y, r[col]):
        a_.text(v, yy, f" {v:.1f}", va="center", fontsize=8)
    if ref:
        a_.axvline(ref, color="k", ls="--", lw=0.8)
        a_.set_xlim(50, 102)
    a_.set_title(t, loc="left", fontsize=10.5)
ax[0].set_yticks(y)
ax[0].set_yticklabels(r.設定, fontsize=9)
fig.suptitle("設定を変えても：気温を入れた GP（赤）は、時刻だけのモデルより誤差が小さく、幅は狭い", x=0.01, ha="left", fontsize=11)
fig.text(0.01, 0.005, "実際の気温を使った場合。灰色は比べる相手。出典：東京電力パワーグリッド、関西電力送配電、気象庁をもとに作成", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 0.94))
fig.savefig(FIG / "f104_5_robust.png", dpi=130)
plt.close(fig)
print("figures done")
