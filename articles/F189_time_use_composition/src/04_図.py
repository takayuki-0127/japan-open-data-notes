# F189 図
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results"); FG = os.path.join(ROOT, "figures"); os.makedirs(FG, exist_ok=True)
S = json.load(open(os.path.join(R, "summary.json")))
BLUE, ORANGE, GRAY = "#2b6cb0", "#dd6b20", "#888888"
short = {"移動(通勤・通学を除く)": "移動(通勤通学以外)", "テレビ・ラジオ・新聞・雑誌": "テレビ・新聞等", "学習・自己啓発・訓練(学業以外)": "学習・自己啓発",
         "ボランティア活動・社会参加活動": "ボランティア等"}

# 1. 分の差と log 比
A = pd.read_csv(os.path.join(R, "A_change_2001_2021.csv")); a = A[A.grouping == "G20"].copy()
a["lab"] = a.part.map(lambda s: short.get(s, s)); a = a.sort_values("diff_min")
fig, ax = plt.subplots(1, 2, figsize=(11, 6.2), sharey=True)
ax[0].barh(a.lab, a.diff_min, color=[BLUE if v > 0 else ORANGE for v in a.diff_min]); ax[0].axvline(0, color="k", lw=.6)
ax[0].set_title("分の差（2021年−2001年）"); ax[0].set_xlabel("分／日")
ax[1].barh(a.lab, 100 * (np.exp(a.log_ratio) - 1), color=[BLUE if v > 0 else ORANGE for v in a.log_ratio]); ax[1].axvline(0, color="k", lw=.6)
ax[1].set_title("比で見た変化（2021年÷2001年−1）"); ax[1].set_xlabel("%")
fig.suptitle("同じ20年の変化でも、分で見ると「休養」、比で見ると「交際」がいちばん大きい（10歳以上・週全体）", fontsize=11.5)
fig.text(0.01, 0.005, "出典：総務省「社会生活基本調査」時系列統計表 第7表を加工して作成", fontsize=8, color=GRAY)
fig.tight_layout(rect=[0, 0.02, 1, 0.95]); fig.savefig(os.path.join(FG, "f189_minutes_vs_ratio.png"), dpi=150); plt.close()

# 2. 5年ごとの動き
B = pd.read_csv(os.path.join(R, "B_step_distance.csv")); b = B[B.sex == "総数"]
fig, ax = plt.subplots(figsize=(9, 4.8))
per = ["1996-2001", "2001-2006", "2006-2011", "2011-2016", "2016-2021"]
for gk, c, lab in [("G20", ORANGE, "20区分"), ("G8", BLUE, "8区分"), ("G4", GRAY, "4区分（1次・2次・3次活動）")]:
    v = b[b.grouping == gk].set_index("period").dist.reindex(per)
    ax.plot(per, v, marker="o", color=c, label=lab)
ax.axhline(S["G_round_95"], color="k", ls=":", lw=1); ax.text(0, S["G_round_95"] + .02, "丸め（±0.5分）だけで出る大きさ（95%点、8区分）", fontsize=8.5)
ax.set_ylabel("組成の動き（Aitchison 距離）"); ax.legend(fontsize=9)
ax.set_title("5年ごとの「1日の配分」の動き：2016→2021年が細かい区分ほど大きい", fontsize=11.5)
fig.text(0.01, 0.005, "出典：総務省「社会生活基本調査」を加工して作成。10歳以上・週全体", fontsize=8, color=GRAY)
fig.tight_layout(rect=[0, 0.03, 1, 1]); fig.savefig(os.path.join(FG, "f189_steps.png"), dpi=150); plt.close()

# 3. 男女×年齢の clr 変化（8区分）
C = pd.read_csv(os.path.join(R, "C_sex_age_2001_2021.csv"))
parts = ["睡眠", "身の回り・食事", "仕事・通勤", "学業・学習", "家事関連", "テレビ等", "休養・くつろぎ", "趣味・交際など"]
fig, axs = plt.subplots(1, 2, figsize=(11, 5.4), sharey=True)
for k, sex in enumerate(["男", "女"]):
    c = C[C.sex == sex]; M = c[["clr_" + p for p in parts]].values
    im = axs[k].imshow(M, cmap="RdBu", vmin=-1.3, vmax=1.3, aspect="auto")
    axs[k].set_xticks(range(len(parts))); axs[k].set_xticklabels(parts, rotation=45, ha="right", fontsize=9)
    axs[k].set_yticks(range(len(c))); axs[k].set_yticklabels(c.age, fontsize=9); axs[k].set_title(sex + "性")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            axs[k].text(j, i, f"{100*(np.exp(M[i,j])-1):+.0f}", ha="center", va="center", fontsize=7)
fig.colorbar(im, ax=axs, shrink=.8, label="ほかに対する比の変化（clr の差）")
fig.suptitle("2001→2021年：テレビ等が減り休養が増えたのは若い世代ほど大きい（数字は比の変化％）", fontsize=11.5)
fig.text(0.01, -0.06, "出典：総務省「社会生活基本調査」時系列統計表 第7表を加工して作成", fontsize=8, color=GRAY)
fig.savefig(os.path.join(FG, "f189_age_heatmap.png"), dpi=150, bbox_inches="tight"); plt.close()

# 4. 男女の差
E = pd.read_csv(os.path.join(R, "E_gender_gap.csv"))
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
for (g, ag), c, lab in [(("総数", "計"), BLUE, "10歳以上"), (("有業者", "計"), ORANGE, "有業者"), (("総数", "30～39歳"), "#38a169", "30〜39歳")]:
    e = E[(E.group == g) & (E.age == ag)]; ax[0].plot(e.year, e.dist_G8, marker="o", color=c, label=lab)
e4 = E[(E.group == "総数") & (E.age == "計")]; ax[0].plot(e4.year, e4.dist_G4, marker="s", color=GRAY, ls="--", label="10歳以上（4区分）")
ax[0].set_ylabel("男女の組成の差（Aitchison 距離）"); ax[0].set_title("男女の1日の配分の差（8区分）"); ax[0].legend(fontsize=8.5); ax[0].set_ylim(0)
ax[1].plot(e4.year, e4.male_house, marker="o", color=BLUE, label="男性 家事関連"); ax[1].plot(e4.year, e4.female_house, marker="o", color=ORANGE, label="女性 家事関連")
ax[1].plot(e4.year, e4.male_work, marker="s", ls="--", color=BLUE, label="男性 仕事・通勤"); ax[1].plot(e4.year, e4.female_work, marker="s", ls="--", color=ORANGE, label="女性 仕事・通勤")
ax[1].set_ylabel("分／日"); ax[1].set_title("家事関連と仕事・通勤（10歳以上）"); ax[1].legend(fontsize=8.5, loc="center right")
fig.suptitle("男女の差は25年で約3分の1縮んだ。ただし「2次活動」でまとめると差はほとんど見えない", fontsize=11.5)
fig.text(0.01, 0.005, "出典：総務省「社会生活基本調査」時系列統計表 第7表を加工して作成", fontsize=8, color=GRAY)
fig.tight_layout(rect=[0, 0.03, 1, 0.94]); fig.savefig(os.path.join(FG, "f189_gender_gap.png"), dpi=150); plt.close()

# 5. 高齢化の分け方
D = pd.read_csv(os.path.join(R, "D_aging_decomposition.csv"))
fig, ax = plt.subplots(figsize=(9.5, 4.8)); x = np.arange(len(D))
ax.bar(x - .2, D.min_age, .4, color=GRAY, label="年齢構成の変化（高齢化など）による分")
ax.bar(x + .2, D.min_total - D.min_age, .4, color=BLUE, label="同じ年齢の中での変化")
ax.scatter(x, D.min_total, color="k", zorder=3, label="合計（2021−2001）")
ax.axhline(0, color="k", lw=.6); ax.set_xticks(x); ax.set_xticklabels(D.part, rotation=30, ha="right", fontsize=9)
ax.set_ylabel("分／日"); ax.legend(fontsize=8.5)
ax.set_title("高齢化はテレビ等を約17分押し上げ、仕事・通勤を約23分押し下げた（2001→2021年）", fontsize=11.5)
fig.text(0.01, 0.005, "出典：総務省「社会生活基本調査」を加工して作成。年齢の重みは人口推計（2021年は2020年10月1日の値で代用）", fontsize=8, color=GRAY)
fig.tight_layout(rect=[0, 0.03, 1, 1]); fig.savefig(os.path.join(FG, "f189_aging_split.png"), dpi=150); plt.close()
print(sorted(os.listdir(FG)))
