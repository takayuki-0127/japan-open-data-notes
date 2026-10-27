import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, AGES
cell = pd.read_csv(DATA/"cells.csv"); by = pd.read_csv(RES/"by_age.csv", index_col=0)
rob = pd.read_csv(RES/"robustness.csv"); S = json.load(open(RES/"summary.json"))
C1, C2, C3 = "#c0392b", "#2c6fbb", "#7f8c8d"

# 1 年齢別の「主に仕事」の割合と平均賃金（全国の加重平均）
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
x = np.arange(len(AGES))
ax[0].plot(x, by["女_主に仕事"]*100, "o-", color=C1, label="女性"); ax[0].plot(x, by["男_主に仕事"]*100, "o-", color=C2, label="男性")
ax[0].set_title("「主に仕事」をしている人の割合（%）"); ax[0].set_ylim(0, 100)
ax[1].plot(x, by["女_観察"], "o-", color=C1, label="女性"); ax[1].plot(x, by["男_観察"], "o-", color=C2, label="男性")
ax[1].set_title("働いている人の所定内給与（千円／月）")
for a in ax:
    a.set_xticks(x); a.set_xticklabels(AGES, rotation=45); a.legend(frameon=False); a.grid(alpha=.3)
fig.suptitle("女性は30代から「働いている人」が6割前後に減る（2020年、47都道府県の加重平均）")
fig.tight_layout(); fig.savefig(FIG/"f54_age_profile.png", dpi=150); plt.close()

# 2 1段目：保育所の定員と、子育て年齢の女性の「主に仕事」の割合
f = cell[(cell["sex"]=="女") & cell["age"].isin(["25-29","30-34","35-39","40-44"])]
g = f.groupby("pref")[["p_main","known","cap_per_child","tfr"]].apply(lambda d: pd.Series({"p": np.average(d["p_main"], weights=d["known"]), "cap": d["cap_per_child"].iloc[0], "tfr": d["tfr"].iloc[0]}))
fig, ax = plt.subplots(figsize=(6.4, 4.6))
sc = ax.scatter(g["cap"]*100, g["p"]*100, c=g["tfr"], cmap="viridis", s=40)
b = np.polyfit(g["cap"]*100, g["p"]*100, 1); xx = np.linspace(g["cap"].min()*100, g["cap"].max()*100, 10)
ax.plot(xx, b[1]+b[0]*xx, color=C3, lw=1)
fig.colorbar(sc, label="合計特殊出生率")
ax.set_xlabel("保育所等の定員（15歳未満人口100人あたり）"); ax.set_ylabel("25〜44歳女性の「主に仕事」の割合（%）")
ax.set_title(f"保育の受け皿が大きい県ほど、子育て年齢の女性が働いている\n（相関 {np.corrcoef(g['cap'], g['p'])[0,1]:.2f}）")
ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FIG/"f54_first_stage.png", dpi=150); plt.close()

# 3 女性の観察された賃金と、補正後（全員が働いた場合）の賃金
fig, ax = plt.subplots(figsize=(7, 4.3))
ax.plot(x, by["女_観察"], "o-", color=C1, label="女性：働いている人の平均（観察）")
ax.plot(x, by["女_補正"], "s--", color=C1, alpha=.6, label="女性：選択を補正した平均（本体）")
ax.plot(x, by["男_観察"], "o-", color=C2, label="男性：働いている人の平均（観察）")
ax.set_xticks(x); ax.set_xticklabels(AGES); ax.set_ylabel("所定内給与（千円／月）")
ax.set_title("本体の補正では、女性の平均賃金はほとんど動かない（+2.9%）")
ax.legend(frameon=False); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FIG/"f54_corrected_wage.png", dpi=150); plt.close()

# 4 設定ごとの θ（選択の強さ）と補正後÷観察
r = rob.copy()
fig, ax = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
y = np.arange(len(r))[::-1]
col = [C1 if s=="女" else C2 for s in r["sex"]]
for yi,(_,rr),cc in zip(y, r.iterrows(), col):
    ax[0].errorbar(rr["theta"], yi, xerr=[[rr["theta"]-rr["theta_lo"]],[rr["theta_hi"]-rr["theta"]]], fmt="none", ecolor=cc, capsize=3)
    ax[1].errorbar(rr["ratio_corr_obs"], yi, xerr=[[rr["ratio_corr_obs"]-rr["lo"]],[rr["hi"]-rr["ratio_corr_obs"]]], fmt="none", ecolor=cc, capsize=3)
ax[0].scatter(r["theta"], y, c=col, zorder=3); ax[0].axvline(0, color=C3, lw=1)
ax[0].set_title("逆ミルズ比の係数 θ（95%区間）\n＋なら「働いている人ほど賃金が高い」選択")
ax[1].scatter(r["ratio_corr_obs"], y, c=col, zorder=3); ax[1].axvline(1, color=C3, lw=1)
ax[1].set_title("補正後の平均賃金 ÷ 観察された平均賃金（95%区間）")
ax[0].set_yticks(y); ax[0].set_yticklabels([f"{s}（F={f:.0f}）" if pd.notna(f) else s for s,f in zip(r["spec"], r["firstF"])], fontsize=8)
ax[0].set_xlim(-1.5, 2); ax[1].set_xlim(0.3, 2.1)
for a in ax: a.grid(alpha=.3)
fig.suptitle("除外制約の選び方で、補正の向きも大きさも変わる（区間はどれも広い）")
fig.tight_layout(); fig.savefig(FIG/"f54_robustness.png", dpi=150); plt.close()

# 5 男女の賃金差：観察と、女性の選択を補正した場合
fig, ax = plt.subplots(figsize=(7, 4.2))
w = 0.38
ax.bar(x-w/2, by["差_観察"]*100, w, color=C3, label="観察（働いている人どうし）")
ax.bar(x+w/2, by["差_女性補正"]*100, w, color=C1, alpha=.7, label="女性の選択を補正（本体）")
ax.set_xticks(x); ax.set_xticklabels(AGES); ax.set_ylabel("男性に対する女性の賃金の低さ（%）")
ax.set_title(f"男女の賃金差は年齢とともに広がる。補正しても形は同じ\n（20〜64歳全体：観察 {S['gap_overall']['obs']*100:.1f}% → 補正 {S['gap_overall']['women_corrected_vs_men_obs']*100:.1f}%）")
ax.legend(frameon=False); ax.grid(alpha=.3, axis="y"); fig.tight_layout(); fig.savefig(FIG/"f54_gender_gap.png", dpi=150); plt.close()
print("ok")
