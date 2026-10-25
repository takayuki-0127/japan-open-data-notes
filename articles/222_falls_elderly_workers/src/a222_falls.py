"""222 労災の主役は「高齢者の転倒」になっていた（事故の型別の構成比）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, save, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

t, a, r = load()
# 2020・2021年は新型コロナの感染（「その他」に入る）を含むため、構成比は「その他」を除いた合計で計算する
t["合計（その他を除く）"] = t["合計"] - t["その他"]
MAIN = ["転倒", "動作の反動・無理な動作", "墜落・転落", "はさまれ・巻き込まれ", "切れ・こすれ", "交通事故（道路）"]
share = t[MAIN].div(t["合計（その他を除く）"], axis=0) * 100
idx = t[MAIN + ["合計（その他を除く）"]].div(t.loc[2009, MAIN + ["合計（その他を除く）"]]) * 100
share.round(1).to_csv(RES / "share_by_type.csv", encoding="utf-8-sig"); idx.round(1).to_csv(RES / "index_by_type_2009eq100.csv", encoding="utf-8-sig")
a["share60plus"] = a.age60plus / a.total * 100
a.round(1).to_csv(RES / "age_share.csv", encoding="utf-8-sig")
# 2025年：度数率×延べ実労働時間で年齢別の転倒の死傷者数を推計（延べ実労働時間は千万時間）
r = r.set_index("age"); ra = r.drop("年齢計")
est = (ra[["転倒", "合計"]].mul(ra["延べ実労働時間_千万時間"], axis=0) * 10).round()
est["転倒の割合"] = (est["転倒"] / est["合計"] * 100).round(1)
est.to_csv(RES / "falls_by_age_2025_estimated.csv", encoding="utf-8-sig")
old = est.loc[["60～64", "65～69", "70～74", "75歳以上"]]
pd.set_option("display.width", 200)
print(share.round(1).to_string()); print(idx.round(0).to_string()); print(a.share60plus.round(1).to_string()); print(est.to_string())
print("転倒推計合計", est["転倒"].sum(), "うち60歳以上", old["転倒"].sum(), round(old["転倒"].sum() / est["転倒"].sum() * 100, 1),
      "60歳以上の死傷に占める転倒", round(old["転倒"].sum() / old["合計"].sum() * 100, 1))

# 図1 事故の型別の死傷者数
fig, ax = plt.subplots(figsize=(9.5, 4.8))
cols = [ORANGE, PURPLE, BLUE, GREEN, LIGHT, GRAY]
for c, col in zip(MAIN, cols):
    s = t[c]; ax.plot(s.index, s.values, "o-", color=col, lw=2.4 if c == "転倒" else 1.6, ms=3.5, label=c)
    ax.text(2025.3, s.iloc[-1] + {"切れ・こすれ": 450, "交通事故（道路）": -450, "動作の反動・無理な動作": 300, "墜落・転落": -300}.get(c, 0), f"{c} {s.iloc[-1]:,}", va="center", fontsize=8.5, color=col)
ax.set_xlim(2008.5, 2030.5); ax.set_xticks([2009, 2013, 2017, 2021, 2025]); ax.set_ylabel("人")
ax.set_title("事故の型別にみた休業4日以上の死傷者数（全産業、2009〜2025年、2011年は欠け）", loc="left", fontsize=11)
save(fig, "a222_types.png")

# 図2 死傷者に占める60歳以上の割合と、転倒の割合
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
ax.plot(share.index, share["転倒"], "o-", color=ORANGE, lw=2, label="転倒")
ax.plot(share.index, share["動作の反動・無理な動作"], "o-", color=PURPLE, lw=1.6, label="動作の反動・無理な動作")
ax.plot(share.index, share["墜落・転落"], "o-", color=BLUE, lw=1.6, label="墜落・転落")
for y in [2009, 2025]: ax.text(y, share.loc[y, "転倒"] + 0.8, f"{share.loc[y, '転倒']:.1f}%", ha="center", fontsize=9, color=ORANGE)
ax.set_title("死傷者に占める割合（%、「その他」を除く）", loc="left", fontsize=11); ax.legend(frameon=False, fontsize=8.5); ax.set_ylim(0, 32)
ax = axes[1]
ax.plot(a.index, a.share60plus, "o-", color=INK, lw=2)
for y in [2009, 2025]: ax.text(y, a.loc[y, "share60plus"] + 0.8, f"{a.loc[y, 'share60plus']:.1f}%", ha="center", fontsize=9)
ax.set_title("死傷者に占める60歳以上の割合（%）", loc="left", fontsize=11); ax.set_ylim(0, 35)
for ax in axes: ax.set_xticks([2009, 2013, 2017, 2021, 2025])
fig.suptitle("転倒と60歳以上の割合が、そろって上がってきた", x=0.01, ha="left", fontsize=11, y=1.02)
fig.tight_layout(); save(fig, "a222_shares.png")

# 図3 年齢別・男女別の転倒の度数率（2025年）
fig, ax = plt.subplots(figsize=(9.5, 4.6))
x = np.arange(len(ra)); w = 0.38
ax.bar(x - w / 2, ra["転倒_男性"], w, color=BLUE, label="男性")
ax.bar(x + w / 2, ra["転倒_女性"], w, color=ORANGE, label="女性")
for xi, v in zip(x, ra["転倒_女性"]):
    if v >= 0.4: ax.text(xi + w / 2, v + 0.04, f"{v:.2f}", ha="center", fontsize=8)
ax.set_xticks(x, [s.replace("歳以下", "以下").replace("歳以上", "以上") for s in ra.index], rotation=45, ha="right")
ax.set_ylabel("度数率（100万労働時間あたり）"); ax.legend(frameon=False)
ax.set_title("年齢別・男女別にみた転倒の死傷度数率（休業4日以上、2025年）", loc="left", fontsize=11)
save(fig, "a222_rate_age.png")
