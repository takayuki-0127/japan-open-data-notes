"""図を6枚つくる（figures/）。"""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG, AGES
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
FIG.mkdir(exist_ok=True)
C1, C2, C3 = "#3B6EA8", "#D9822B", "#7A7A7A"
res = json.load(open(RES / "main.json", encoding="utf-8"))

# 1 全国：区間ごとの TFR の変化を「結婚」と「夫婦」に分ける
A = pd.read_csv(RES / "A_decomposition.csv").iloc[:6]
fig, ax = plt.subplots(figsize=(8.5, 4.8))
x = np.arange(len(A)); lab = [f"{a}→{b}" for a, b in zip(A.y0, A.y1)]
ax.bar(x - 0.2, A.marriage, 0.38, color=C1, label="結婚の要因（有配偶の割合の変化）")
ax.bar(x + 0.2, A.marital, 0.38, color=C2, label="夫婦の要因（有配偶の女性の出生率の変化）")
ax.plot(x, A.d, "k_", ms=28, mew=2.5, label="合計特殊出生率の変化（2つの合計）")
ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x, lab)
ax.set_ylabel("合計特殊出生率の変化"); ax.set_title("合計特殊出生率の変化を2つに分ける（全国、国勢調査の年ごと）")
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2); fig.tight_layout(); fig.savefig(FIG / "f203_01_decomposition.png", dpi=150); plt.close()

# 2 年齢別：有配偶の割合と、有配偶の女性の出生率
P = pd.read_csv(RES / "A_age_profiles.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
for y, c in zip([1970, 1990, 2020], ["#BBBBBB", C3, C1]):
    s = P[P.year == y]
    axs[0].plot(AGES, s.married * 100, "o-", color=c, label=f"{y}年")
    axs[1].plot(AGES[1:], s.marital_rate.values[1:] * 1000, "o-", color=c, label=f"{y}年")
m25 = res["A_2025_marriage_only"]["married_2025"]
axs[0].plot(AGES, [m25[a] * 100 for a in AGES], "o--", color=C2, label="2025年")
axs[0].set_title("有配偶の女性の割合（％）"); axs[1].set_title("有配偶の女性1,000人あたりの出生（年）")
for a in axs: a.set_xlabel("年齢"); a.tick_params(axis="x", rotation=45); a.legend(frameon=False, fontsize=9)
axs[1].set_ylim(0, None); axs[1].text(0, -0.38, "15〜19歳は有配偶の人が少なく値が極端になるので省いた", transform=axs[1].transAxes, fontsize=8)
fig.suptitle("結婚している人の割合は下がり、結婚している人の出生率は上がった"); fig.tight_layout(); fig.subplots_adjust(bottom=0.24); fig.savefig(FIG / "f203_02_age_profiles.png", dpi=150); plt.close()

# 3 生まれ年：30歳までの出生と49歳までの出生
Bc = pd.read_csv(RES / "B_cohort.csv")
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4))
axs[0].plot(Bc.cohort, Bc.cum49, color=C1, lw=2.2, label="49歳までに産んだ子どもの数")
axs[0].plot(Bc.cohort, Bc.cum30, color=C2, lw=2.2, label="30歳までに産んだ数")
axs[0].fill_between(Bc.cohort, Bc.cum30, Bc.cum49, color=C1, alpha=0.12, label="31〜49歳に産んだ数")
axs[0].set_xlabel("女性の生まれ年"); axs[0].set_ylabel("女性1人あたり"); axs[0].legend(frameon=False, fontsize=9); axs[0].set_title("生まれ年ごとの子どもの数")
axs[1].scatter(Bc.cum30, Bc.cum49, c=Bc.cohort, cmap="viridis", s=22)
b = res["B_main"]; xs = np.linspace(Bc.cum30.min(), Bc.cum30.max(), 10)
a0 = Bc.cum49.mean() - b["slope"] * Bc.cum30.mean()
axs[1].plot(xs, a0 + b["slope"] * xs, color="k", lw=1)
axs[1].plot(xs, Bc.cum49.iloc[0] + (xs - Bc.cum30.iloc[0]), color=C3, ls=":", lw=1.2, label="取り戻しがない場合（傾き1）")
axs[1].set_xlabel("30歳までに産んだ数"); axs[1].set_ylabel("49歳までに産んだ数")
axs[1].set_title(f"30歳までに減った分のうち、後で取り戻せたのは約{b['recovered_share']*100:.0f}%"); axs[1].legend(frameon=False, fontsize=9)
for t, (xx, yy) in zip([1932, 1974], [(Bc.cum30.iloc[0], Bc.cum49.iloc[0]), (Bc.cum30.iloc[-1], Bc.cum49.iloc[-1])]):
    axs[1].annotate(f"{t}年生まれ", (xx, yy), textcoords="offset points", xytext=(-70 if t == 1932 else 6, 8 if t == 1932 else -14), fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f203_03_cohort.png", dpi=150); plt.close()

# 4 都道府県：結婚の要因と夫婦の要因（名前は出さない）
pr = pd.read_csv(RES / "C_pref.csv")
fig, ax = plt.subplots(figsize=(6.4, 5.2))
ax.scatter(np.exp(pr.logM), np.exp(pr.logC), color=C1, s=30)
ax.axhline(1, color=C3, lw=0.8); ax.axvline(1, color=C3, lw=0.8)
ax.set_xlabel("結婚の要因（全国＝1。有配偶の割合だけで決まる出生率の比）"); ax.set_ylabel("夫婦の要因（全国＝1。残りの比）")
s = res["C_pref"]; ax.set_title(f"47都道府県：地域差の{s['marriage']*100:.0f}%が結婚、{s['couple']*100:.0f}%が夫婦", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f203_04_pref.png", dpi=150); plt.close()

# 5 地域差のうち結婚の要因の割合：都道府県・市区町村、設定ごと
R = pd.read_csv(RES / "C_robustness.csv")
order = [("基本", "pref", "都道府県"), ("基本", "muni", "市区町村（ベイズ推定値）"), ("素の出生率", "muni", "市区町村（素の出生率）"),
         ("基本（女性15〜49歳が5千人以上）", "muni", "市区町村（女性5千人以上）"), ("基本（女性の数で重み）", "muni", "市区町村（女性の数で重み）"),
         ("結婚経験で定義", "pref", "都道府県（結婚経験で定義）"), ("20〜39歳だけ", "muni", "市区町村（20〜39歳だけ）")]
vals = [(lab, float(R[(R.setting == s) & (R.kind == k)].marriage.iloc[0])) for s, k, lab in order]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
y = np.arange(len(vals))[::-1]
ax.barh(y, [v * 100 for _, v in vals], color=C1); ax.barh(y, [100 - v * 100 for _, v in vals], left=[v * 100 for _, v in vals], color=C2)
for yy, (_, v) in zip(y, vals): ax.text(v * 100 - 2, yy, f"{v*100:.0f}%", ha="right", va="center", color="white", fontsize=10)
ax.set_yticks(y, [l for l, _ in vals]); ax.set_xlim(0, 100); ax.set_xlabel("地域差（出生率の対数のばらつき）に占める割合（％）　青＝結婚の要因、橙＝夫婦の要因")
ax.set_title("地域差のどれだけが「結婚」の違いか：数え方で 46〜85%", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f203_05_regional_share.png", dpi=150); plt.close()

# 6 小さい分母：市区町村の夫婦の要因と、女性の数（ファンネル図）
mb = pd.read_csv(RES / "C_muni.csv")
import importlib.util
raw = mb.copy()
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
# 素の出生率で計算し直す
cols_r = ["r15", "r20", "r25", "r30", "r35", "r40", "r45"]
sh = sum(mb["mar_" + a] / mb["tot_" + a] * res["C_national"]["marital_rate"][a] for a in AGES) * 5
logC_raw = np.log(mb.tfr_raw / sh)
for ax, v, t in [(axs[0], logC_raw, "素の出生率で計算"), (axs[1], mb.logC, "ベイズ推定値で計算")]:
    ax.scatter(mb.women, np.exp(v), s=6, alpha=0.45, color=C1 if "ベイズ" in t else C2)
    ax.set_xscale("log"); ax.axhline(1, color=C3, lw=0.8); ax.set_title(t); ax.set_xlabel("15〜49歳の女性の数（人、対数目盛）")
axs[0].set_ylabel("夫婦の要因（全国＝1）"); axs[0].set_ylim(0.4, 2.0)
fig.suptitle("人口の小さい町ほど、偶然のばらつきで夫婦の要因が大きく振れる"); fig.tight_layout(); fig.savefig(FIG / "f203_06_funnel.png", dpi=150); plt.close()
print("ok")
