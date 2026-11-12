"""397 住宅の建て方と階数（1968〜2023年）：住宅・土地統計調査 時系列統計表 第12-1表"""
import csv, json
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save
SRC = "出典：総務省統計局「令和5年住宅・土地統計調査」時系列統計表 第12-1表をもとに作成者が加工して作成"
rows = list(csv.reader(open(DATA / "raw" / "hlts_ts_t12_1.csv", encoding="utf-8")))
i0 = next(k for k, r in enumerate(rows) if r[1] == "実数"); i1 = next(k for k, r in enumerate(rows) if r[1].startswith("割合"))
cols = ["total", "det", "det_1", "det_2p", "det_3p", "row", "row_1", "row_2p", "apt", "apt_1_2", "apt_3_5", "apt_6p", "apt_11p", "apt_15p", "other"]
num = lambda s: np.nan if s.strip() in ("-", "", "…") else round(float(s))
d = pd.DataFrame([[int(r[2])] + [num(x) for x in r[4:19]] for r in rows[i0 + 1:i1] if r[2].strip().isdigit()], columns=["year"] + cols)
assert len(d) == 12 and d.year.tolist() == list(range(1968, 2024, 5))
# 確かめ：建て方の合計＝総数（100戸単位の丸めの範囲）、共同住宅の階数の合計＝共同住宅
assert ((d.det + d.row + d.apt + d.other - d.total).abs() <= 300).all()
assert ((d.apt_1_2 + d.apt_3_5 + d.apt_6p - d.apt).abs() <= 300).all()
pub = pd.DataFrame([[int(r[2])] + [np.nan if x.strip() in ("-", "") else float(x) for x in r[4:19]] for r in rows[i1 + 1:i1 + 13]], columns=["year"] + cols)
for c in ["det", "row", "apt", "apt_6p"]:
    d["s_" + c] = d[c] / d.total * 100
    assert (d["s_" + c].round(1) - pub[c]).abs().max() <= 0.11, c
for c in ["apt_1_2", "apt_3_5", "apt_11p", "apt_15p", "det_1", "det_2p"]:
    d["s_" + c] = d[c] / d.total * 100
d["in_apt_6p"] = d.apt_6p / d.apt * 100; d["in_apt_11p"] = d.apt_11p / d.apt * 100; d["in_apt_1_2"] = d.apt_1_2 / d.apt * 100
d.to_csv(DATA / "dwellings_by_type_stories.csv", index=False)
g = d.set_index("year")
inc = g.loc[2023] - g.loc[1968]
res = {
    "share_apt": g.s_apt.round(1).to_dict(), "share_det": g.s_det.round(1).to_dict(), "share_row": g.s_row.round(1).to_dict(),
    "share_apt_6p": g.s_apt_6p.round(1).to_dict(), "share_apt_11p": g.s_apt_11p.round(1).to_dict(), "share_apt_15p": g.s_apt_15p.round(2).to_dict(),
    "first_year_apt_30": int(g.index[g.s_apt >= 30][0]), "first_year_apt_40": int(g.index[g.s_apt >= 40][0]),
    "total_1968": int(g.total[1968]), "total_2023": int(g.total[2023]), "ratio_total": float(g.total[2023] / g.total[1968]),
    "apt_1968": int(g.apt[1968]), "apt_2023": int(g.apt[2023]), "ratio_apt": float(g.apt[2023] / g.apt[1968]),
    "det_ratio": float(g.det[2023] / g.det[1968]), "row_ratio": float(g.row[2023] / g.row[1968]),
    "share_of_increase": {k: float(inc[k] / inc.total) for k in ["det", "row", "apt", "other"]},
    "apt_inc_by_stories": {k: float(inc[k] / inc.apt) for k in ["apt_1_2", "apt_3_5", "apt_6p"]},
    "apt_6p_1968": int(g.apt_6p[1968]), "apt_6p_2023": int(g.apt_6p[2023]), "apt_11p_1978": int(g.apt_11p[1978]), "apt_11p_2023": int(g.apt_11p[2023]),
    "apt_15p_1978": int(g.apt_15p[1978]), "apt_15p_2023": int(g.apt_15p[2023]),
    "in_apt_6p": g.in_apt_6p.round(1).to_dict(), "in_apt_11p": g.in_apt_11p.round(1).to_dict(), "in_apt_1_2": g.in_apt_1_2.round(1).to_dict(),
    "det_1story_share": g.s_det_1.round(1).to_dict(), "det_1story_1968": int(g.det_1[1968]), "det_1story_2023": int(g.det_1[2023]),
    "det_1_in_det": (g.det_1 / g.det * 100).round(1).to_dict(),
    "apt_change_5y_pt": g.s_apt.diff().round(1).dropna().to_dict(), "apt_inc_5y": g.apt.diff().dropna().astype(int).to_dict(),
    "inc_2013_2023": {k: int(g[k][2023] - g[k][2013]) for k in ["total", "det", "apt", "apt_1_2", "apt_3_5", "apt_6p", "apt_11p"]},
}
json.dump(res, open(RES / "a397_main.json", "w"), ensure_ascii=False, indent=1)
g.round(2).to_csv(RES / "a397_shares.csv")

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.stackplot(d.year, d.s_det, d.s_row, d.s_apt, d.other / d.total * 100, colors=[BLUE, GRAY, ORANGE, "#dddddd"], labels=["一戸建", "長屋建", "共同住宅", "その他"])
for y in d.year[2::2]:
    ax.text(y, g.s_det[y] / 2, f"{g.s_det[y]:.0f}%", ha="center", color="white", fontsize=9); ax.text(y, 100 - g.s_apt[y] / 2, f"{g.s_apt[y]:.0f}%", ha="center", color="white", fontsize=9)
ax.set_xlim(1968, 2023); ax.set_ylim(0, 100); ax.set_ylabel("住宅に占める割合（%）"); ax.set_title("住宅の建て方の割合（1968〜2023年）"); ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
save(fig, "a397_type_shares.png", SRC, y=-0.08)

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(d.year, d.apt_1_2 / 1e4, 3.6, color=LIGHT, label="1〜2階建"); ax.bar(d.year, d.apt_3_5 / 1e4, 3.6, bottom=d.apt_1_2 / 1e4, color=BLUE, label="3〜5階建")
ax.bar(d.year, d.apt_6p / 1e4, 3.6, bottom=(d.apt_1_2 + d.apt_3_5) / 1e4, color=ORANGE, label="6階建以上")
for y in d.year:
    ax.text(y, g.apt[y] / 1e4 + 30, f"{g.apt[y]/1e4:,.0f}", ha="center", fontsize=8.5)
ax.set_xticks(d.year); ax.set_ylabel("共同住宅の数（万戸）"); ax.set_title("共同住宅の数を、建物の階数で分ける"); ax.legend(frameon=False)
save(fig, "a397_apartments_by_stories.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(d.year, d.s_apt_6p, color=ORANGE, marker="o", label="6階建以上の共同住宅"); ax.plot(d.year, d.s_apt_11p, color=BLUE, marker="o", label="うち11階建以上"); ax.plot(d.year, d.s_apt_15p, color=GREEN, marker="o", label="うち15階建以上")
for y in (1978, 1998, 2023):
    ax.text(y, g.s_apt_6p[y] + 0.6, f"{g.s_apt_6p[y]:.1f}%", ha="center", fontsize=9, color=ORANGE); ax.text(y, g.s_apt_11p[y] + 0.6, f"{g.s_apt_11p[y]:.1f}%", ha="center", fontsize=9, color=BLUE)
ax.text(2023, g.s_apt_15p[2023] - 1.3, f"{g.s_apt_15p[2023]:.1f}%", ha="center", fontsize=9, color=GREEN)
ax.set_ylabel("住宅全体に占める割合（%）"); ax.set_title("高い建物にある住宅の割合（11階・15階以上は1978年から）"); ax.legend(frameon=False)
save(fig, "a397_high_rise_share.png", SRC)
print(json.dumps(res, ensure_ascii=False))
