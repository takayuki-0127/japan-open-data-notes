"""W2：供給熱量ベースの総合食料自給率の変化を「食べるものの構成」と「品目ごとの自給率」に分ける（近似、1965〜2024年度）

近似の作り方：品目 i の 1日当たり供給熱量 w_i（kcal）に、品目別自給率（重量ベース、畜産物は飼料自給率を掛けた値）s_i を掛けて
「国産の熱量」とみなし、Σ w_i s_i ／ 合計熱量 を計算する。s_i は 100% で頭打ちにする。
変化は Δ(Σ a_i s_i) = Σ Δa_i × (s̄_i − S̄)（構成の効果）＋ Σ ā_i × Δs_i（自給率の効果）と分ける
（a_i＝熱量の構成比、バーは2時点の平均、S̄＝全体の自給率の2時点の平均。Σ Δa_i = 0 なので S̄ を引いても合計は変わらない）。
"""
from common import *

kc, s, tot, feed = wide("kcal"), wide("ssr_item") / 100, wide("ssr_total"), wide("feed")
OFF = tot["供給熱量ベースの総合食料自給率"]


def k(*cols):
    return sum(kc[c].fillna(0) for c in cols)


# 品目：（熱量, 自給率の列）
MAP = {"米": (k("穀類_米"), "米"), "小麦": (k("穀類_小麦"), "小麦"),
       "大麦・はだか麦": (k("穀類_大麦", "穀類_はだか麦"), "はだか麦_大・はだか麦計"),
       "雑穀": (k("穀類_とうもろこし", "穀類_こうりゃん", "穀類_その他の雑穀"), "雑穀"),
       "いも類": (k("いも類"), "いも類"), "でん粉": (k("でん粉"), "でん粉"),
       "大豆": (k("豆類_大豆"), "豆類_大豆"), "その他の豆類": (k("豆類_その他の豆類"), "豆類_その他の豆類"),
       "野菜": (k("野菜"), "野菜"), "果実": (k("果実"), "果実"),
       "肉類": (k("肉類"), "肉類（飼料自給率）"), "鶏卵": (k("鶏卵"), "鶏卵（飼料自給率）"),
       "牛乳・乳製品": (k("牛乳及び乳製品"), "牛乳及び乳製品（飼料自給率）"),
       "魚介類": (k("魚介類"), "魚介類"), "海藻類": (k("海藻類"), "海藻類"),
       "砂糖類": (k("砂糖類"), "砂糖類（沖縄県を含む）"),
       "植物油脂": (k("油脂類_植物油脂"), "油脂類_植物油脂"), "動物油脂": (k("油脂類_動物油脂"), "油脂類_動物油脂"),
       "みそ": (k("みそ"), "豆類_大豆_うち食用"), "しょうゆ": (k("しょうゆ"), "豆類_大豆_うち食用"),
       "その他（きのこ等）": (k("その他食料計"), "きのこ類")}
W = pd.DataFrame({n: v for n, (v, _) in MAP.items()}).loc[1965:]
S = pd.DataFrame({n: s[c] for n, (_, c) in MAP.items()}).loc[1965:].clip(upper=1)
TOTAL = kc["合計"].loc[1965:]
A = W.div(TOTAL, axis=0)                  # 熱量の構成比
approx = (A * S).sum(1) * 100
cmp_ = pd.DataFrame({"公表値": OFF.loc[1965:], "近似値": approx.round(2), "差": (approx - OFF.loc[1965:]).round(2)})
cmp_.to_csv(RES / "w2_official_vs_approx.csv", encoding="utf-8-sig")
print("近似と公表値の差：平均", round(cmp_["差"].mean(), 2), "平均絶対", round(cmp_["差"].abs().mean(), 2),
      "最大", cmp_["差"].abs().max(), "（", int(cmp_["差"].abs().idxmax()), "年度）")
print(cmp_.loc[[1965, 1975, 1990, 2000, 2010, 2024]])


def decompose(y0, y1):
    a0, a1, s0, s1 = A.loc[y0], A.loc[y1], S.loc[y0], S.loc[y1]
    sbar = ((a0 * s0).sum() + (a1 * s1).sum()) / 2   # 全体の自給率（2時点の平均）
    comp = (a1 - a0) * ((s0 + s1) / 2 - sbar) * 100  # 構成比は合計が1なので、全体の平均との差で配分しても合計は同じ
    rate = (a0 + a1) / 2 * (s1 - s0) * 100
    d = pd.DataFrame({"熱量の構成比_前": a0 * 100, "熱量の構成比_後": a1 * 100, "自給率_前": s0 * 100, "自給率_後": s1 * 100,
                      "構成の効果": comp, "自給率の効果": rate})
    d["合計"] = d["構成の効果"] + d["自給率の効果"]
    return d


PER = [(1965, 2024), (1965, 1990), (1990, 2024), (2000, 2024)]
summ = []
for y0, y1 in PER:
    d = decompose(y0, y1)
    d.round(3).to_csv(RES / f"w2_decomp_{y0}_{y1}.csv", encoding="utf-8-sig")
    summ.append({"期間": f"{y0}→{y1}", "公表値_前": OFF[y0], "公表値_後": OFF[y1], "近似_前": round(approx[y0], 1),
                 "近似_後": round(approx[y1], 1), "近似の変化": round(approx[y1] - approx[y0], 1),
                 "構成の効果": round(d["構成の効果"].sum(), 1), "自給率の効果": round(d["自給率の効果"].sum(), 1)})
summ = pd.DataFrame(summ)
summ.to_csv(RES / "w2_decomp_summary.csv", index=False, encoding="utf-8-sig")
print(summ.to_string(index=False))
d = decompose(1965, 2024)
print(d.round(1).sort_values("合計").to_string())

# 飼料自給率
fs = feed["飼料自給率_純国内産飼料自給率(B＋C)/A×100【％】"]
print("飼料自給率", fs.loc[[1965, 1990, 2024]].to_dict())

# 図1：公表値と近似値
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(OFF.loc[1960:].index, OFF.loc[1960:], color=INK, lw=2.2, label="公表値（供給熱量ベース）")
ax.plot(approx.index, approx, color=ORANGE, lw=1.6, ls="--", label="この記事の近似（品目別自給率×熱量）")
ax.plot(tot.index, tot["生産額ベースの総合食料自給率"], color=GRAY, lw=1.4, label="（参考）生産額ベース")
ax.set_ylim(0, 100); ax.set_ylabel("%"); ax.set_xlabel("年度"); ax.legend(frameon=False, loc="lower left")
ax.set_title("総合食料自給率：公表値と近似値")
fig.text(0, -0.03, SOURCE + "。2024年度は概算値", fontsize=8, color=GRAY)
fig.savefig(FIG / "w2_official.png"); plt.close(fig)

# 図2：期間ごとの分解
fig, ax = plt.subplots(figsize=(8, 4.5))
x = np.arange(len(summ))
ax.bar(x - 0.2, summ["構成の効果"], 0.4, color=BLUE, label="食べるものの構成の変化")
ax.bar(x + 0.2, summ["自給率の効果"], 0.4, color=ORANGE, label="品目ごとの自給率の変化")
for i, r in summ.iterrows():
    for dx, v in ((-0.2, r["構成の効果"]), (0.2, r["自給率の効果"])):
        ax.text(i + dx, v - 0.4 if v < 0 else v + 0.3, f"{v:+.1f}", ha="center", va="top" if v < 0 else "bottom", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{p}年度" for p in summ["期間"]]); ax.axhline(0, color=INK, lw=1)
ax.set_ylabel("自給率の変化（ポイント）"); ax.legend(frameon=False, loc="lower right"); ax.set_ylim(summ[["構成の効果", "自給率の効果"]].min().min() - 2, 3)
ax.set_title("自給率の低下の内訳（近似）")
fig.text(0, -0.03, SOURCE, fontsize=8, color=GRAY)
fig.savefig(FIG / "w2_decomp.png"); plt.close(fig)

# 図3：1965→2024年度の品目別の寄与
dd = d[d["合計"].abs() >= 0.3].sort_values("合計")
fig, ax = plt.subplots(figsize=(8, 5.5))
yy = np.arange(len(dd))
ax.barh(yy, dd["構成の効果"], color=BLUE, label="構成の効果")
ax.barh(yy, dd["自給率の効果"], left=np.where(np.sign(dd["自給率の効果"]) == np.sign(dd["構成の効果"]), dd["構成の効果"], 0),
        color=ORANGE, label="自給率の効果")
for i, (c_, r_) in enumerate(zip(dd["構成の効果"], dd["自給率の効果"])):
    v = c_ + r_
    left = min(0, c_, r_, v if np.sign(c_) == np.sign(r_) else 0)
    ax.text(left - 0.15, i, f"{v:+.1f}", va="center", ha="right", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels(dd.index); ax.axvline(0, color=INK, lw=1)
ax.set_xlabel("自給率への寄与（ポイント）"); ax.legend(frameon=False, loc="upper left"); ax.set_xlim(dd["構成の効果"].min() - 1.8, 1.5)
ax.set_title("1965→2024年度：品目別の寄与（近似、絶対値0.3ポイント以上）")
fig.text(0, -0.03, SOURCE, fontsize=8, color=GRAY)
fig.savefig(FIG / "w2_items.png"); plt.close(fig)
