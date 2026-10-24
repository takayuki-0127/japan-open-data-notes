"""人口あたりの病床数は、本当に「西高東低」なのか（医療施設調査 令和7年 第15表）"""
from common import *

REG = {"北海道": "北海道", **{p: "東北" for p in "青森 岩手 宮城 秋田 山形 福島".split()},
       **{p: "関東" for p in "茨城 栃木 群馬 埼玉 千葉 東京 神奈川".split()},
       **{p: "中部" for p in "新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知".split()},
       **{p: "近畿" for p in "三重 滋賀 京都 大阪 兵庫 奈良 和歌山".split()},
       **{p: "中国" for p in "鳥取 島根 岡山 広島 山口".split()}, **{p: "四国" for p in "徳島 香川 愛媛 高知".split()},
       **{p: "九州・沖縄" for p in "福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄".split()}}
ORDER = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
d = load("beds_per100k_2025.csv")
nat = d[d.pref == "全国"].iloc[0]
d = d[d.pref != "全国"].copy()
d["region"] = d.pref.map(REG)
d["west"] = d.region.isin(["中国", "四国", "九州・沖縄"])
a = load("aged65_share_2023.csv")
d = d.merge(a, on="pref")
d["other"] = d.infectious + d.tuberculosis
cols = ["general", "long_term_care", "psychiatric", "other"]
reg = d.groupby("region")[["total"] + cols].mean().loc[ORDER]
reg.round(1).to_csv(RES / "a182_region_mean.csv", encoding="utf-8")
d.sort_values("total", ascending=False).to_csv(RES / "a182_pref.csv", index=False, encoding="utf-8")
L = []
L.append(f"全国 {nat.total}（一般{nat.general}・療養{nat.long_term_care}・精神{nat.psychiatric}）")
s = d.sort_values("total", ascending=False)
L.append("上位10: " + "、".join(f"{r.pref}{r.total:.0f}" for r in s.head(10).itertuples()))
L.append("下位10: " + "、".join(f"{r.pref}{r.total:.0f}" for r in s.tail(10).itertuples()))
L.append(f"最大÷最小 {s.total.max()/s.total.min():.2f}倍（{s.iloc[0].pref}/{s.iloc[-1].pref}）")
L.append("上位15のうち中国・四国・九州沖縄: " + str(int(s.head(15).west.sum())) + "（ほか " + "、".join(s.head(15)[~s.head(15).west].pref) + "）")
for c, n in [("total", "総数"), ("general", "一般"), ("long_term_care", "療養"), ("psychiatric", "精神")]:
    w, e = d[d.west][c].mean(), d[~d.west][c].mean()
    L.append(f"{n}: 西（中国・四国・九州沖縄17県）平均 {w:.0f}、ほか30道府県 {e:.0f}、比 {w/e:.2f}")
    mx, mn = d[c].max(), d[c].min()
    L.append(f"   {n} 最大÷最小 {mx/mn:.2f}（{d.loc[d[c].idxmax(),'pref']}{mx:.0f}／{d.loc[d[c].idxmin(),'pref']}{mn:.0f}）")
L.append("地方別の平均(総数): " + "、".join(f"{r} {reg.loc[r,'total']:.0f}" for r in ORDER))
r = np.corrcoef(d.aged65_share_2023, d.total)[0, 1]
b = np.polyfit(d.aged65_share_2023, d.total, 1)
d["resid"] = d.total - np.polyval(b, d.aged65_share_2023)
L.append(f"65歳以上割合との相関 {r:.2f}、傾き {b[0]:.1f}/pt；残差の西平均 {d[d.west].resid.mean():.0f}・ほか {d[~d.west].resid.mean():.0f}")
L.append("残差の上位: " + "、".join(f"{x.pref}{x.resid:+.0f}" for x in d.sort_values('resid', ascending=False).head(6).itertuples()))
L.append("残差の下位: " + "、".join(f"{x.pref}{x.resid:+.0f}" for x in d.sort_values('resid').head(6).itertuples()))
(RES / "a182_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：都道府県の順位（色＝西側）
s = d.sort_values("total")
fig, ax = plt.subplots(figsize=(9.5, 10))
ax.barh(s.pref, s.total, color=[ORANGE if w else (GREEN if p == "北海道" else BLUE) for w, p in zip(s.west, s.pref)])
ax.axvline(nat.total, color=GRAY, ls="--", lw=1); ax.text(nat.total + 15, 0, f"全国 {nat.total:.0f}", fontsize=9, color=GRAY)
ax.set_xlabel("人口10万人あたりの病院の病床数（2025年10月）"); ax.tick_params(axis="y", labelsize=9)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=ORANGE, label="中国・四国・九州・沖縄"), Patch(color=GREEN, label="北海道"), Patch(color=BLUE, label="ほか")], frameon=False, loc="lower right")
ax.set_title("人口あたりの病床数（都道府県）")
save(fig, "a182_rank.png")

# 図2：地方別の中央値、病床の種類の内訳
fig, ax = plt.subplots(figsize=(9.5, 4.4))
bottom = np.zeros(len(ORDER))
for c, n, col in [("general", "一般病床", BLUE), ("long_term_care", "療養病床", ORANGE), ("psychiatric", "精神病床", PURPLE), ("other", "結核・感染症", GRAY)]:
    v = reg[c].values; ax.bar(ORDER, v, bottom=bottom, color=col, label=n); bottom += v
for i, t in enumerate(reg.total.values):
    ax.text(i, bottom[i] + 20, f"{t:.0f}", ha="center", fontsize=9)
ax.set_ylabel("人口10万人あたり（都道府県の単純平均）"); ax.legend(frameon=False, ncol=4, fontsize=9, loc="upper left"); ax.set_ylim(0, 2200)
ax.set_title("地方別の病床数と種類（各地方の都道府県の単純平均）")
save(fig, "a182_region_types.png")

# 図3：65歳以上の割合と病床数
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.scatter(d.aged65_share_2023, d.total, c=[ORANGE if w else BLUE for w in d.west], s=40)
xs = np.linspace(d.aged65_share_2023.min(), d.aged65_share_2023.max(), 10); ax.plot(xs, np.polyval(b, xs), color=GRAY, lw=1)
for x in d.itertuples():
    if x.pref in ("高知", "鹿児島", "長崎", "徳島", "山口", "北海道", "秋田", "東京", "神奈川", "沖縄", "岐阜", "山形", "新潟"):
        ax.text(x.aged65_share_2023 + 0.15, x.total, x.pref, fontsize=8)
ax.set_xlabel("65歳以上の割合（2023年、%）"); ax.set_ylabel("人口10万人あたりの病床数（2025年）")
ax.set_title(f"高齢化と病床数（相関 {r:.2f}）。橙＝中国・四国・九州・沖縄")
save(fig, "a182_aging.png")
