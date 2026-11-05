import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
B = Path(__file__).resolve().parents[1]; RE = B/"results"; FG = B/"figures"; FG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 1 指標ごとの順位
rk = pd.read_csv(RE/"A_ranks_tokyo.csv", index_col=0)
mt = pd.read_csv(RE/"A_metrics_tokyo.csv", index_col=0)
lab = {"時間ごとのMAPE": "1時間ごとの\nMAPE", "時間ごとのRMSE": "1時間ごとの\nRMSE", "日量のMAPE": "1日の量の\nMAPE",
       "ピークのMAPE": "ピークの\nMAPE", "ピーク下振れ3超の日数": "ピークが3%超\n下に外れた日数", "悪い日95点": "悪い日\n（95%点）"}
fig, ax = plt.subplots(figsize=(10, 5.6))
im = ax.imshow(rk.values, cmap="RdYlGn_r", vmin=1, vmax=9, aspect="auto")
for i in range(rk.shape[0]):
    for j in range(rk.shape[1]):
        v = mt.values[i, j]
        s = f"{int(rk.values[i,j])}位\n{v:.0f}" if v > 50 else f"{int(rk.values[i,j])}位\n{v:.2f}"
        ax.text(j, i, s, ha="center", va="center", fontsize=8)
ax.set_xticks(range(rk.shape[1])); ax.set_xticklabels([lab[c] for c in rk.columns], fontsize=9)
ax.set_yticks(range(rk.shape[0])); ax.set_yticklabels(rk.index, fontsize=9)
ax.set_title("同じ9つの予測でも、何で測るかで「いちばん」が入れ替わる（東京・2025年10月〜2026年9月）", fontsize=11)
fig.tight_layout(); fig.savefig(FG/"f205_1_metric_rank.png"); plt.close()

# 2 いつまでに出すか
ld = pd.read_csv(RE/"A2_leadtime.csv")
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = ["#999"]*5 + ["#2b6cb0"]
ax.barh(range(len(ld)), ld.MAPE, color=cols)
for i, v in enumerate(ld.MAPE): ax.text(v+0.1, i, f"{v:.1f}%", va="center", fontsize=9)
ax.set_yticks(range(len(ld))); ax.set_yticklabels(ld.手法, fontsize=9); ax.invert_yaxis()
ax.set_xlabel("1時間ごとの MAPE（%）")
ax.set_title("同じ「何日前の値を使うか」でも、締め切りしだいで外れ方が変わる", fontsize=11)
fig.tight_layout(); fig.savefig(FG/"f205_2_leadtime.png"); plt.close()

# 3 外れの値段：比ごとに、出す予測を変えたときの値段
bc = pd.read_csv(RE/"B_cost_by_option.csv")
order = ["点予測（そのまま）", "点予測＋3%", "点予測＋5%", "点予測＋8%"] + [f"分位点{t}（コンフォーマル）" for t in [0.5, 0.8, 0.9, 0.95, 0.975, 0.99]]
short = ["点", "＋3%", "＋5%", "＋8%", "q0.5", "q0.8", "q0.9", "q0.95", "q0.975", "q0.99"]
fig, ax = plt.subplots(figsize=(10, 5))
for r, c in zip([1, 4, 9, 19, 49], ["#555", "#2b6cb0", "#38a169", "#d69e2e", "#c53030"]):
    s = bc[bc.比 == r].set_index("出す予測").loc[order, "指数"]
    ax.plot(range(4), s.values[:4], "-o", color=c, label=f"足りない1MW＝余る1MWの{r}倍")
    ax.plot(range(4, len(order)), s.values[4:], "-o", color=c)
ax.axhline(100, color="k", lw=0.6, ls=":")
ax.set_xticks(range(len(order))); ax.set_xticklabels(short)
ax.axvline(3.5, color="#999", lw=0.8)
ax.text(1.5, ax.get_ylim()[1]*0.97, "点予測に上乗せ", ha="center", fontsize=9, color="#555")
ax.text(6.5, ax.get_ylim()[1]*0.97, "分位点の予測（左ほど低い）", ha="center", fontsize=9, color="#555")
ax.set_ylabel("値段の指数（点予測そのまま＝100）")
ax.set_title("足りないときの値段が高いほど、点予測より上の値を出すほうが安くなる（翌日ピーク・東京2020〜2026年度）", fontsize=10.5)
ax.legend(fontsize=8.5); fig.tight_layout(); fig.savefig(FG/"f205_3_cost_curves.png"); plt.close()

# 4 前の年度で上乗せ幅を決めて次の年度に使う
R = pd.read_csv(RE/"B_rolling_margin.csv")
g = R.groupby("比")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
x = np.arange(len(g))
for k, (c, nm) in enumerate([("上乗せの指数", "点予測＋上乗せ（前の年度で決める）"), ("コンフォーマルの指数", "分位点（コンフォーマル）"), ("LightGBM分位点の指数", "分位点（LightGBM）")]):
    med = g[c].median(); lo = g[c].min(); hi = g[c].max()
    axs[0].errorbar(x+(k-1)*0.22, med, yerr=[med-lo, hi-med], fmt="o", capsize=3, label=nm)
axs[0].axhline(100, color="k", lw=0.6, ls=":")
axs[0].set_xticks(x); axs[0].set_xticklabels([f"{r}倍" for r in g.groups.keys()])
axs[0].set_xlabel("足りない1MWの値段（余る1MWの何倍か）"); axs[0].set_ylabel("値段の指数（点予測＝100、年度の中央値と幅）")
axs[0].legend(fontsize=8); axs[0].set_title("次の年度に使ったときの値段", fontsize=10.5)
med = g.上乗せ幅.median()*100
axs[1].bar(x, med, color="#2b6cb0")
for i, v in enumerate(med): axs[1].text(i, v+0.1, f"{v:.1f}%", ha="center", fontsize=9)
th = [r/(1+r) for r in g.groups.keys()]
axs[1].set_xticks(x); axs[1].set_xticklabels([f"{r}倍\n(τ={t:.2f})" for r, t in zip(g.groups.keys(), th)], fontsize=8.5)
axs[1].set_ylabel("点予測に上乗せする幅（%）"); axs[1].set_title("いちばん安くなる上乗せ幅", fontsize=10.5)
fig.tight_layout(); fig.savefig(FG/"f205_4_cost_rolling.png"); plt.close()

# 5 作り直すタイミング：空振りと気づくまでの日数
C = pd.read_csv(RE/"C_drift_detection.csv")
c = C[(C.データ == "東京2025") & (C.ずれ == 0.02)]
fig, ax = plt.subplots(figsize=(9, 5))
for (rule, sub), col, mk in zip(c.groupby("ルール"), ["#c53030", "#2b6cb0", "#38a169"], ["s", "o", "^"]):
    nm = {"MAPE14日": "直近14日の MAPE が○%超", "ずれ7日": "直近7日のずれの平均が±○%超", "CUSUM": "ずれの累積（CUSUM）が○超"}[rule]
    ax.plot(sub.空振り_年, sub.気づくまでの日数_中央値, "-"+mk, color=col, label=nm)
    for _, r in sub.iterrows(): ax.annotate(f"{r.しきい値:g}", (r.空振り_年, r.気づくまでの日数_中央値), textcoords="offset points", xytext=(4, 4), fontsize=8, color=col)
ax.set_xlabel("ずれのない1年で鳴った回数（空振り）"); ax.set_ylabel("需要が2%増えてから気づくまでの日数（中央値）")
ax.set_title("同じ空振りの回数なら、「ずれの向き」を見るルールのほうが早く気づく（東京・固定モデル）", fontsize=10.5)
ax.legend(fontsize=9); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FG/"f205_5_drift_tradeoff.png"); plt.close()

# 6 例：2026年2月から需要が3%増えたとき
ex = pd.read_csv(RE/"C_example_drift3_20260201.csv", parse_dates=["date"])
m = json.load(open(RE/"main.json"))
fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
axs[0].plot(ex.date, ex.bias7, color="#2b6cb0"); axs[0].axhline(1.5, ls=":", color="k"); axs[0].axhline(-1.5, ls=":", color="k")
axs[0].set_ylabel("ずれの7日平均（%）\n＋は予測が上"); axs[0].axvline(pd.Timestamp("2026-02-01"), color="#c53030")
for d in m["C_example_alarms"]["ずれ7日"]: axs[0].axvline(pd.Timestamp(d), color="#2b6cb0", alpha=.25)
axs[0].set_title("2026年2月1日から需要を3%増やしてみると、ずれの線は数日でしきい値を超え、直さない限り鳴り続ける", fontsize=10.5)
axs[1].plot(ex.date, ex.ape14, color="#c53030"); axs[1].axhline(3.0, ls=":", color="k")
axs[1].set_ylabel("MAPE の14日平均（%）"); axs[1].axvline(pd.Timestamp("2026-02-01"), color="#c53030")
r = m["C_recal"]
axs[1].text(pd.Timestamp("2026-04-10"), ex.ape14.max()*0.95, f"2月以降の MAPE：何もしない {r['何もしない']:.2f}% → 直近14日の比で割り戻す {r['比で割り戻す']:.2f}%（ずれなし {r['ずれなしのMAPE']:.2f}%）", fontsize=8.5)
fig.tight_layout(); fig.savefig(FG/"f205_6_drift_example.png"); plt.close()
print("ok")
