"""130：観光客はどの県で「日帰り」が多いのか（日本人・観光目的、2016〜2019年のうち各県の最新年）"""
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from common import *

df = load()
COLS = ["県内宿泊", "県内日帰り", "県外宿泊", "県外日帰り"]


def wide(col, seg):
    v = df[df.segment == seg].pivot_table(index=["year", "code", "pref"], columns=["area", "stay"], values=col, aggfunc="sum")
    v.columns = [a + s for a, s in v.columns]
    v = v.reset_index()
    v["計"] = v[COLS].sum(axis=1, min_count=1)
    v["日帰り"] = v[["県内日帰り", "県外日帰り"]].sum(axis=1, min_count=1)
    return v[v["計"] > 0]


vis = wide("visitors_k", "日本人・観光目的")
spd = wide("spend_m", "日本人・観光目的")
# 各都道府県で 2016〜2019年のうち、集計がある最新の年を使う
pre = vis[vis.year.between(2016, 2019)].sort_values("year").groupby("code").tail(1).copy()
pre["日帰り割合"] = pre["日帰り"] / pre["計"]
pre["県内客の日帰り割合"] = pre["県内日帰り"] / (pre["県内宿泊"] + pre["県内日帰り"])
pre["県外客の日帰り割合"] = pre["県外日帰り"] / (pre["県外宿泊"] + pre["県外日帰り"])
pre["県外客の割合"] = (pre["県外宿泊"] + pre["県外日帰り"]) / pre["計"]
sp = spd.merge(pre[["year", "code"]], on=["year", "code"])
sp["消費額の日帰り割合"] = sp["日帰り"] / sp["計"]
pre = pre.merge(sp[["code", "消費額の日帰り割合"]], on="code")
pre = pre.sort_values("日帰り割合", ascending=False)
out = pre[["code", "pref", "year", "計", "日帰り割合", "県内客の日帰り割合", "県外客の日帰り割合", "県外客の割合", "消費額の日帰り割合"]]
out.round(4).to_csv(RES / "a130_pref_daytrip.csv", index=False)

# 単価（円/人回）の中央値
u = df[(df.segment == "日本人・観光目的") & df.year.between(2016, 2019)].merge(pre[["year", "code"]], on=["year", "code"])
unit = u.groupby(["area", "stay"]).unit_yen.median().round(0)
unit.to_csv(RES / "a130_unit_median.csv")

# 区分別の日帰り割合（2016年＝44都道府県の集計がある最後の年）
seg_rows = []
for seg in SEG.values():
    w = wide("visitors_k", seg)
    for y, d in w.groupby("year"):
        seg_rows.append(dict(segment=seg, year=y, n_pref=len(d), day_share=d["日帰り"].sum() / d["計"].sum()))
segdf = pd.DataFrame(seg_rows)
segdf.round(4).to_csv(RES / "a130_segment_year.csv", index=False)

# 2011〜2019年に毎年集計がある都道府県だけで、日帰り割合の推移
j = vis[vis.year.between(2011, 2019)]
bal = j.groupby("code").year.nunique(); bal = bal[bal == 9].index
trend = j[j.code.isin(bal)].groupby("year").apply(lambda d: d["日帰り"].sum() / d["計"].sum()).rename("day_share")
trend.round(4).to_csv(RES / "a130_trend_balanced.csv")

S = {"n": len(pre), "median": pre["日帰り割合"].median(), "pooled": pre["日帰り"].sum() / pre["計"].sum(),
     "spend_pooled": sp["日帰り"].sum() / sp["計"].sum(), "spend_median": pre["消費額の日帰り割合"].median(),
     "in_med": pre["県内客の日帰り割合"].median(), "out_med": pre["県外客の日帰り割合"].median(), "n_bal": len(bal)}
pd.Series(S).round(4).to_csv(RES / "a130_summary.csv")
print(pd.Series(S).round(4)); print(unit); print(segdf[segdf.year == 2016]); print(trend.round(4))

# 図1：都道府県の日帰り割合
fig, ax = plt.subplots(figsize=(7, 10))
lab = [f"{p}（{y}）" if y != 2019 else p for p, y in zip(pre.pref, pre.year)]
y = np.arange(len(pre))[::-1]
ax.barh(y, pre["日帰り割合"] * 100, color=BLUE, height=0.7)
ax.set_yticks(y, lab, fontsize=8.5)
ax.axvline(S["median"] * 100, color=GRAY, lw=1, ls="--")
ax.text(S["median"] * 100 + 0.5, len(pre) - 0.5, f"中央値 {S['median']*100:.1f}%", color=GRAY, fontsize=9, va="top")
ax.set_xlim(40, 100); ax.set_xlabel("日帰り客の割合（%、観光入込客数〔実人回〕ベース）")
ax.set_title("日本人・観光目的の観光客のうち日帰りの割合（44都道府県）", loc="left")
fig.text(0, -0.02, "年の表記がない県は2019年。かっこは2019年の集計がなく、2016〜2018年の最新年を使った県。\n石川県・大阪府・沖縄県は2016〜2019年に集計がない。" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a130_rank.png"); plt.close(fig)

# 図2：県内客と県外客の日帰り割合
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(pre["県内客の日帰り割合"] * 100, pre["県外客の日帰り割合"] * 100, s=pre["計"] / 4000 + 15, color=BLUE, alpha=0.7, edgecolor="white")
for _, r in pre.iterrows():
    if r["県外客の日帰り割合"] < 0.6 or r["県外客の日帰り割合"] > 0.93 or r["県内客の日帰り割合"] < 0.8:
        ax.annotate(r.pref, (r["県内客の日帰り割合"] * 100, r["県外客の日帰り割合"] * 100), fontsize=8.5, xytext=(-40, -14) if r.pref == "東京都" else (4, 2), textcoords="offset points")
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls=":")
ax.set_xlim(50, 100); ax.set_ylim(0, 100)
ax.set_xlabel("県内から来た客の日帰り割合（%）"); ax.set_ylabel("県外から来た客の日帰り割合（%）")
ax.set_title("県外から来る客は、県によって日帰りの割合が大きく違う", loc="left")
fig.text(0, -0.04, "点の大きさは観光入込客数。点線は県内と県外が同じ割合。" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a130_inout.png"); plt.close(fig)

# 図3：人数で見た日帰り割合と、消費額で見た日帰り割合
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(pre["日帰り割合"] * 100, pre["消費額の日帰り割合"] * 100, color=ORANGE, alpha=0.8, edgecolor="white", s=45)
for _, r in pre.iterrows():
    if r["消費額の日帰り割合"] < 0.4 or r["消費額の日帰り割合"] > 0.85:
        ax.annotate(r.pref, (r["日帰り割合"] * 100, r["消費額の日帰り割合"] * 100), fontsize=8.5, xytext=(4, 2), textcoords="offset points")
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls=":")
ax.set_xlim(45, 100); ax.set_ylim(0, 100)
ax.set_xlabel("人数で見た日帰りの割合（%）"); ax.set_ylabel("観光消費額で見た日帰りの割合（%）")
ax.set_title("人数では9割近くが日帰りでも、お金では半分ほど", loc="left")
fig.text(0, -0.04, "点線より下は、日帰りの割合が人数より消費額で小さい県。" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a130_spend.png"); plt.close(fig)
