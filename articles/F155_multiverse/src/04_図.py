"""F155 の図（results/ から作る）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES

R = json.load(open(RES / "results.json"))
SA = pd.read_csv(RES / "A_specifications.csv")
SB = pd.read_csv(RES / "B_specifications.csv")
SB2 = pd.read_csv(RES / "B2_specifications_lfpr.csv")
C_POS, C_NEG, C_NS = "#c0392b", "#2c6fbb", "#9a9a9a"

A_DIMS = ["処置の定義", "期間の始まり", "期間の終わり", "追加の条件", "対象", "重み"]
B_DIMS = ["比べ方", "地域の条件", "県の違い", "対象", "重み", "外れ値", "処置の定義"]
SHORT = {"2025年まで（2020〜22年を除く）": "2025年まで（20〜22年除く）", "＋前の値（変化の比較だけ）": "＋前の値（変化のみ）",
         "除く（県ダミー）": "除く", "政令市・23区を除く": "政令市・23区除く", "15歳以上人口": "人口"}


ORDER = {"処置の定義": ["中央値で2分", "上下3分の1", "連続（bite）", "連続（在所児）"], "期間の始まり": ["2008", "2012"],
         "期間の終わり": ["2019年まで", "2022年まで", "2025年まで", "2025年まで（2020〜22年を除く）"],
         "追加の条件": ["なし", "地方×年", "県別の傾き"], "対象": ["47県", "被災3県を除く", "全体", "人口1万人以上", "政令市・23区を除く"],
         "重み": ["なし", "15歳以上人口", "人口"], "比べ方": ["水準", "変化"],
         "地域の条件": ["なし", "人口・密度", "＋年齢・世帯", "＋産業・通勤・所得", "＋財政・学歴・雇用", "＋前の値（変化の比較だけ）"],
         "県の違い": ["除く（県ダミー）", "除かない"], "外れ値": ["そのまま", "上下1%を除く"]}


def spec_curve(ax_top, ax_bot, s, dims, unit, title, base_mask=None, color_by=None):
    s = s.sort_values("est").reset_index(drop=True)
    x = np.arange(len(s))
    col = np.where(s.lo > 0, C_POS, np.where(s.hi < 0, C_NEG, C_NS))
    ax_top.vlines(x, s.lo, s.hi, color=col, alpha=0.35, lw=0.8)
    ax_top.scatter(x, s.est, c=col, s=6, zorder=3)
    ax_top.axhline(0, color="k", lw=0.8)
    med = s.est.median()
    ax_top.axhline(med, color="#444", lw=0.8, ls="--")
    ax_top.text(len(s) * 0.01, med, f" 中央値 {med:+.3f}", va="bottom", fontsize=8, color="#444")
    if base_mask is not None:
        bm = base_mask(s)
        for i in np.where(bm)[0]:
            ax_top.scatter([i], [s.est[i]], marker="D", s=40, facecolor="none", edgecolor="k", zorder=4)
    ax_top.set_ylabel(unit, fontsize=9)
    ax_top.set_title(title, fontsize=11, loc="left")
    ax_top.set_xlim(-2, len(s) + 1)
    ax_top.set_xticks([])
    # 下の段：それぞれの指定でどの選択肢を使ったか
    yt, yl = [], []
    yy = 0
    for d in dims:
        levels = [lv for lv in ORDER.get(d, []) if lv in set(s[d].astype(str))] or sorted(set(s[d].astype(str)))
        for lv in levels:
            m = s[d].astype(str) == lv
            ax_bot.scatter(x[m], np.full(m.sum(), yy), s=2.5, color=np.array(col)[m], marker="|")
            yt.append(yy); yl.append(f"{d}：{SHORT.get(lv, lv)}")
            yy -= 1
        yy -= 0.6
    ax_bot.set_yticks(yt); ax_bot.set_yticklabels(yl, fontsize=6.5)
    ax_bot.set_xlim(-2, len(s) + 1)
    ax_bot.set_xlabel("指定（推定値の小さい順）", fontsize=9)
    for sp in ("top", "right"):
        ax_top.spines[sp].set_visible(False); ax_bot.spines[sp].set_visible(False)


def base_A(s):
    return ((s["処置の定義"] == "中央値で2分") & (s["期間の始まり"] == 2008) & (s["期間の終わり"] == "2019年まで")
            & (s["追加の条件"] == "なし") & (s["対象"] == "47県") & (s["重み"] == "なし")).values


def base_B(s):
    return ((s["県の違い"] == "除く（県ダミー）") & (s["対象"] == "全体") & (s["重み"] == "なし") & (s["外れ値"] == "そのまま")
            & (s["処置の定義"] == "連続（在所児）")
            & (((s["比べ方"] == "水準") & (s["地域の条件"] == "＋財政・学歴・雇用"))
               | ((s["比べ方"] == "変化") & (s["地域の条件"] == "＋前の値（変化の比較だけ）")))).values


# ---- 図1 問いA
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 8.2), gridspec_kw=dict(height_ratios=[1.3, 1.6]), sharex=False)
s = SA[SA.outcome == "emp_rate"]
spec_curve(a1, a2, s, A_DIMS, "就業率の差（%ポイント、bite 1標準偏差あたり）",
           f"問いA：最低賃金と就業率　{len(s)}通りの指定（◇はF01の基本の指定）", base_A)
fig.text(0.01, 0.005, "赤：95%区間が0より上　青：0より下　灰：0をまたぐ。データ：F01（労働力調査 都道府県別モデル推計値ほか）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.015, 1, 1)); fig.savefig(FIG / "fig1_A_spec_curve.png", dpi=150); plt.close(fig)

# ---- 図2 問いB
fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 8.6), gridspec_kw=dict(height_ratios=[1.3, 1.9]))
spec_curve(a1, a2, SB, B_DIMS, "出生率の差（在所児 +10人あたり）",
           f"問いB：保育所と出生率　{len(SB)}通りの指定（◇はF100の基本の指定）", base_B)
fig.text(0.01, 0.005, "赤：95%区間が0より上　青：0より下　灰：0をまたぐ。データ：F100（社会・人口統計体系、人口動態保健所・市区町村別統計）", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.015, 1, 1)); fig.savefig(FIG / "fig2_B_spec_curve.png", dpi=150); plt.close(fig)

# ---- 図3 ばらつきはどの選択肢から来るか（シャープレイ値）
fig, axes = plt.subplots(1, 3, figsize=(12, 4.4))
sets = [("問いA：就業率", R["A"]["emp_rate"]["shapley"]), ("問いB：出生率（全体）", R["B"]["tfr"]["shapley"]),
        ("問いB：出生率（水準の比較だけ）", R["B"]["tfr"]["shapley_水準"])]
for ax, (t, sh) in zip(axes, sets):
    items = [(k, v) for k, v in sh.items() if not k.startswith("全部")]
    items.sort(key=lambda kv: kv[1])
    ax.barh([k for k, _ in items], [100 * v for _, v in items], color="#5b7fa6")
    for i, (k, v) in enumerate(items):
        ax.text(100 * v + 0.5, i, f"{100 * v:.0f}%", va="center", fontsize=8)
    tot = sh["全部の組み合わせ（交互作用なし）"]
    ax.set_title(f"{t}\n（足し合わせ {100 * tot:.0f}%、残りは組み合わせの効果）", fontsize=9.5)
    ax.set_xlabel("推定値のばらつきのうち説明できる割合（%）", fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_xlim(0, max(100 * v for _, v in items) * 1.25 + 2)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig3_variance_share.png", dpi=150); plt.close(fig)

# ---- 図4 「効果0」の世界で同じことをしたら（推定値の中央値の分布）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, (t, f, j, unit) in zip(axes, [("問いA：就業率（bite を県の間で並べ替え）", "A_null_median_emp_rate.npy", R["A"]["emp_rate"]["joint"], "%ポイント"),
                                     ("問いB：出生率（効果0を課したブートストラップ）", "B_null_median_tfr.npy", R["B"]["tfr"]["joint"], "在所児+10人あたり")]):
    nm = np.load(RES / f)
    ax.hist(nm, bins=40, color="#bbbbbb", edgecolor="white")
    ax.axvline(j["observed_median"], color=C_POS if j["observed_median"] > 0 else C_NEG, lw=2)
    ax.text(j["observed_median"], ax.get_ylim()[1] * 0.92, f" 実際の中央値 {j['observed_median']:+.4f}\n p={j['p_median_two_sided']:.3f}",
            fontsize=8.5, ha="left" if j["observed_median"] < np.median(nm) else "right")
    ax.set_title(t, fontsize=10)
    ax.set_xlabel(f"全指定の推定値の中央値（{unit}）", fontsize=8.5)
    ax.set_ylabel("回数", fontsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig4_joint_null.png", dpi=150); plt.close(fig)

# ---- 図5 重み付けと、選択肢を1つ固定したときの幅
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
ax = axes[0]
rows = []
for q, key, lab in [("A", ("A", "emp_rate"), "A 就業率"), ("B", ("B", "tfr"), "B 出生率")]:
    W = R[key[0]][key[1]]["weighting"]
    for k, v in W.items():
        rows.append((f"{lab}｜{k}", v["median"], v["p05"], v["p95"], q))
for i, (lab, m, lo, hi, q) in enumerate(rows[::-1]):
    sc = 1.0 if q == "A" else 10.0  # B は値が小さいので ×10 で同じ軸に
    ax.plot([lo * sc, hi * sc], [i, i], color="#888", lw=2)
    ax.scatter([m * sc], [i], color="k", zorder=3)
    ax.text(hi * sc, i, f"  {m:+.3f}", va="center", fontsize=7.5)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows[::-1]], fontsize=7.5)
ax.axvline(0, color="k", lw=0.8)
ax.set_title("重み付けを変えたときの中央値と5〜95%の幅\n（A は%ポイント、B は×10 して表示。数字は元の単位の中央値）", fontsize=9)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax = axes[1]
items = []
for lab, lf in [("A", R["A"]["emp_rate"]["leave_fixed"]), ("B水準", R["B"]["tfr"]["leave_fixed_水準"]), ("B変化", R["B"]["tfr"]["leave_fixed_変化"])]:
    for d, v in lf["by_dim"].items():
        items.append((f"{lab}｜{d}を「{SHORT.get(v['fixed_to'], v['fixed_to'])}」に固定", 100 * v["shrink"]))
y = np.arange(len(items))[::-1]
ax.barh(y, [v for _, v in items], color=["#5b7fa6" if v >= 0 else "#c9a227" for _, v in items])
ax.set_yticks(y); ax.set_yticklabels([k for k, _ in items], fontsize=7)
ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("推定値の幅（5〜95%）が縮んだ割合（%）", fontsize=8.5)
ax.set_title("選択肢を1つだけ基本に固定すると、答えの幅はどれだけ縮むか", fontsize=9)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig5_weighting_fixing.png", dpi=150); plt.close(fig)

# ---- 図6 別の結果で同じことをすると
fig, axes = plt.subplots(1, 2, figsize=(11, 4.0))
for ax, (s, t, unit) in zip(axes, [(SA[SA.outcome == "unemp_rate"], "問いA：完全失業率（288通り）", "%ポイント（bite 1SDあたり）"),
                                   (SB2, f"問いB：女性の労働力率（{len(SB2)}通り）", "%ポイント（在所児+10人あたり）")]):
    s = s.sort_values("est").reset_index(drop=True)
    x = np.arange(len(s))
    col = np.where(s.lo > 0, C_POS, np.where(s.hi < 0, C_NEG, C_NS))
    ax.vlines(x, s.lo, s.hi, color=col, alpha=0.35, lw=0.8)
    ax.scatter(x, s.est, c=col, s=5)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title(t, fontsize=10, loc="left"); ax.set_ylabel(unit, fontsize=8.5); ax.set_xticks([])
    ax.set_xlabel("指定（推定値の小さい順）", fontsize=8.5)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
fig.tight_layout(); fig.savefig(FIG / "fig6_other_outcomes.png", dpi=150); plt.close(fig)
print("figures done")
