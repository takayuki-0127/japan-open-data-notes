"""産業廃棄物は、どの業種からどれだけ出ているか（令和5年度実績、令和4年度と比較）"""
from common import *

ind = load("by_industry_r5_r4.csv"); typ = load("by_type_r5_r4.csv"); flow = load("flow_r5.csv")
TOT = ind.loc[ind.level == "合計", "r5_kt"].item(); TOT4 = ind.loc[ind.level == "合計", "r4_kt"].item()
# 大分類（製造業は中分類に分けて並べる）
big = ind[(ind.level == "大分類") & (ind.industry != "製造業")].copy(); mfg = ind[ind.level == "製造業内訳"].copy()
rows = pd.concat([big, mfg]); rows["share_r5"] = rows.r5_kt / TOT * 100; rows["share_r4"] = rows.r4_kt / TOT4 * 100
rows["chg_pct"] = (rows.r5_kt / rows.r4_kt - 1) * 100
rows = rows.sort_values("r5_kt", ascending=False)
rows.round(2).to_csv(RES / "a168_industry_ranked.csv", index=False, encoding="utf-8")
top5 = rows.head(5); cum5 = top5.r5_kt.sum() / TOT * 100
typ2 = typ[typ.type != "合計"].copy(); typ2["share_r5"] = typ2.r5_kt / TOT * 100; typ2 = typ2.sort_values("r5_kt", ascending=False)
typ2.round(2).to_csv(RES / "a168_type_ranked.csv", index=False, encoding="utf-8")
L = [f"総排出量 令和5年度 {TOT/1e3:.1f}百万t（令和4年度 {TOT4/1e3:.1f}百万t、{TOT/TOT4-1:+.1%}）",
     "業種別 上位10（製造業は中分類）:\n" + rows.head(10)[["industry", "r5_kt", "share_r5", "r4_kt", "chg_pct"]].round(1).to_string(index=False),
     f"上位5業種の合計 {cum5:.1f}%；製造業（大分類）{ind.loc[ind.industry=='製造業','r5_kt'].item()/TOT*100:.1f}%",
     "前年度からの変化が大きい業種（1,000千t以上）:\n" + rows[rows.r5_kt >= 1000].sort_values("chg_pct")[["industry", "r5_kt", "r4_kt", "chg_pct"]].round(1).to_string(index=False),
     "種類別 上位5:\n" + typ2.head(5)[["type", "r5_kt", "share_r5", "recycle_rate_r5"]].round(1).to_string(index=False),
     "処理の流れ:\n" + flow.to_string(index=False)]
(RES / "a168_summary.txt").write_text("\n\n".join(L), encoding="utf-8"); print("\n\n".join(L))

# 図1：業種別（上位12＋その他）
fig, ax = plt.subplots(figsize=(9.5, 5.6))
u = rows.head(12).iloc[::-1]
other = TOT - rows.head(12).r5_kt.sum()
names = ["その他の業種"] + list(u.industry); vals = [other] + list(u.r5_kt)
cols = [LIGHT] + [ORANGE if n in set(top5.industry) else BLUE for n in u.industry]
ax.barh(names, [v / 1e3 for v in vals], color=cols)
for i, v in enumerate(vals):
    ax.text(v / 1e3 + 0.8, i, f"{v/1e3:.1f}（{v/TOT*100:.1f}%）", va="center", fontsize=8.5)
ax.set_xlim(0, 118); ax.set_xlabel("排出量（百万t、令和5年度）")
ax.set_title(f"上位5業種（オレンジ）で全体の{cum5:.0f}%。製造業は中分類に分けて表示")
save(fig, "a168_industry.png")

# 図2：種類別
fig, ax = plt.subplots(figsize=(9.5, 4.8))
v = typ2.head(9).iloc[::-1]; oth = TOT - typ2.head(9).r5_kt.sum()
names = ["その他"] + list(v.type); vals = [oth] + list(v.r5_kt)
ax.barh(names, [x / 1e3 for x in vals], color=[LIGHT] + [ORANGE if n in ("汚泥", "動物のふん尿", "がれき類") else BLUE for n in v.type])
for i, x in enumerate(vals):
    ax.text(x / 1e3 + 1, i, f"{x/1e3:.1f}（{x/TOT*100:.1f}%）", va="center", fontsize=8.5)
ax.set_xlim(0, 185); ax.set_xlabel("排出量（百万t、令和5年度）")
ax.set_title("種類では汚泥が42%。動物のふん尿、がれき類と合わせて8割")
save(fig, "a168_type.png")

# 図3：再生利用率（種類別、公表値のあるもの）
r = typ[typ.recycle_rate_r5.notna()].copy(); r = r.sort_values("recycle_rate_r5")
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.barh(r.type, r.recycle_rate_r5, color=[GRAY if t == "合計" else (ORANGE if t == "汚泥" else BLUE) for t in r.type])
for i, (x, k) in enumerate(zip(r.recycle_rate_r5, r.r5_kt)):
    ax.text(x + 1, i, f"{x:.1f}%（排出 {k/1e3:.1f}百万t）", va="center", fontsize=8.5)
ax.set_xlim(0, 125); ax.set_xlabel("再生利用率（%、排出量に対する再生利用量）")
ax.set_title("いちばん多い汚泥の再生利用は7.6%。多くは中間処理で量を減らす（減量化）")
save(fig, "a168_recycle.png")
