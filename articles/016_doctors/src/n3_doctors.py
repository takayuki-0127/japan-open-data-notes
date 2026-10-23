"""N3：人口あたり医師数が多いのは、どんな市区町村か（医師数 2022年、従業地ベース）"""
from common import *
SRC2 = "出典：e-Stat「統計でみる市区町村のすがた2026」（医師数は厚生労働省「医師・歯科医師・薬剤師統計」）を加工して作成"

d = load_extra()
d["doc"] = d.I6100 / d.A2301 * 1000
d["band"] = pd.cut(d.A2301, [0, 5000, 10000, 30000, 100000, 300000, 1e9], labels=["5千人未満", "5千〜1万", "1万〜3万", "3万〜10万", "10万〜30万", "30万人以上"])
g = d.groupby("band", observed=True).agg(n=("doc", "size"), median=("doc", "median"), doctors=("I6100", "sum"), pop=("A2301", "sum"))
g["rate"] = g.doctors / g["pop"] * 1000; g.round(3).to_csv(RES / "n3_band.csv", encoding="utf-8-sig"); print(g.round(2))
top10 = d.nlargest(int(len(d) * .1), "I6100")
s = {"n": len(d), "national_rate": d.I6100.sum() / d.A2301.sum() * 1000, "median_rate": d.doc.median(), "n_zero": int((d.I6100 == 0).sum()),
     "n_zero_with_clinic": int(((d.I6100 == 0) & (d.I5102 > 0)).sum()), "top10pct_doctor_share": top10.I6100.sum() / d.I6100.sum(),
     "top10pct_pop_share": top10.A2301.sum() / d.A2301.sum(), "corr_doc_old": np.corrcoef(d.doc, d.old)[0, 1]}
pd.Series(s).round(3).to_csv(RES / "n3_summary.csv", header=["value"]); print(pd.Series(s).round(3))
d.nlargest(20, "doc")[["pref_name", "name", "A2301", "I6100", "doc"]].round(2).to_csv(RES / "n3_top.csv", index=False, encoding="utf-8-sig")
d[d.I6100 == 0][["pref_name", "name", "A2301", "I5102"]].to_csv(RES / "n3_zero.csv", index=False, encoding="utf-8-sig")

# 図1：上位15
med = {"永平寺町", "矢巾町", "東温市", "壬生町", "毛呂山町", "中央市", "三木町", "下野市", "由布市", "内灘町", "西原町"}
t = d.nlargest(15, "doc").iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5)); y = np.arange(len(t))
ax.barh(y, t.doc, color=[BLUE if n in med else LIGHT for n in t["name"]], height=0.65)
for yi, (_, x) in zip(y, t.iterrows()):
    ax.text(x.doc + 0.3, yi, f"{x.doc:.1f}（{x.I6100:,.0f}人）", va="center", fontsize=8)
ax.axvline(s["national_rate"], color=ORANGE, lw=1, ls="--"); ax.text(s["national_rate"] + 0.3, -0.9, f"全国 {s['national_rate']:.1f}", fontsize=8, color="#52514e")
ax.set_yticks(y, [f"{x['name']}（{x.pref_name}）" for _, x in t.iterrows()]); ax.set_xlim(0, 33); ax.set_ylim(-1.4, len(t) - 0.4)
ax.set_xlabel("住民1,000人あたり医師数（医師は働いている場所で数える）")
ax.set_title("上位は「医学部・医科大学の病院がある町」と東京の都心", loc="left")
fig.text(0.01, -0.03, SRC2 + "（濃い青：医学部・医科大学の附属病院がある市町。2022年時点）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "n3_top.png"); plt.close(fig)

# 図2：人口規模別
fig, ax = plt.subplots(figsize=(8, 3.6)); y = np.arange(len(g))[::-1]
ax.barh(y, g.rate, color=BLUE, height=0.6)
for yi, v, n in zip(y, g.rate, g.n):
    ax.text(v + 0.05, yi, f"{v:.2f}（{n}市区町村）", va="center", fontsize=9)
ax.set_yticks(y, g.index.astype(str)); ax.set_xlim(0, 4); ax.set_xlabel("住民1,000人あたり医師数（グループ全体の合計で計算）")
ax.set_title("人口が少ない町ほど、医師は少ない", loc="left")
fig.text(0.01, -0.06, SRC2, fontsize=8, color="#8a8984"); fig.savefig(FIG / "n3_band.png"); plt.close(fig)
