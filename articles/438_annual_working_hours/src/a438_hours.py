"""A438 1年に働く時間は、いつ2,000時間を切ったのか
長期統計系列 19-15（事業所規模30人以上、1950〜2005年）と、毎月勤労統計調査 実数・指数累積データ（調査産業計の年平均、1970〜2025年）。
年間の時間は「月間の実労働時間 × 12」。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「毎月勤労統計調査」（長期時系列表、総務省統計局「日本の長期統計系列」19-15）をもとに作成"
raw = pd.read_excel(DATA / "raw" / "chouki_19-15.xls", header=None)
i0 = raw.index[raw[0].astype(str).str.contains("昭和25年")][0]
old = pd.DataFrame({"year": range(1950, 2006), "all_ind": pd.to_numeric(raw.iloc[i0:i0 + 56, 2], errors="coerce").values,
                    "excl_service": pd.to_numeric(raw.iloc[i0:i0 + 56, 3], errors="coerce").values})
old.to_csv(DATA / "chouki_19-15_total_hours_30plus.csv", index=False)

m = pd.read_csv(DATA / "maikin_jissu_TL_CY.csv")
m.columns = ["kind", "year", "month", "ind", "size", "type", "pay_total", "pay_regular", "pay_sched", "pay_over", "pay_special", "hours", "hours_sched", "hours_over", "days", "w_prev", "w_in", "w_out", "workers", "part_workers"]
m["size"] = m["size"].astype(str).str.strip(); m["type"] = m["type"].astype(int)
def ser(size, typ, col="hours"): return m[(m["size"] == size) & (m["type"] == typ)].set_index("year")[col].astype(float).sort_index()
h30, h30f, h30p = ser("0", 0), ser("0", 1), ser("0", 2); h5, h5f, h5p = ser("T", 0), ser("T", 1), ser("T", 2)

# 2つの資料が重なる年（1970〜2005年）の一致
ov = old.set_index("year")["all_ind"].dropna(); diff = (ov - h30.reindex(ov.index)).abs()
# 長い線：1950〜69年は「サービス業を除く」、1970年からは調査産業計
long = pd.concat([old.set_index("year")["excl_service"].loc[1950:1969], h30]).rename("monthly"); ann = (long * 12).rename("annual")
tab = pd.DataFrame({"monthly_hours_30plus": long, "annual_hours_30plus": ann, "excl_service_annual": old.set_index("year")["excl_service"] * 12,
                    "full_time_annual_30plus": h30f * 12, "part_time_annual_30plus": h30p * 12, "annual_hours_5plus": h5 * 12, "full_time_annual_5plus": h5f * 12,
                    "sched_annual_30plus": ser("0", 0, "hours_sched") * 12, "overtime_annual_30plus": ser("0", 0, "hours_over") * 12,
                    "part_share_30plus": ser("0", 0, "part_workers") / ser("0", 0, "workers") * 100, "part_share_5plus": ser("T", 0, "part_workers") / ser("T", 0, "workers") * 100,
                    "days_30plus": ser("0", 0, "days")})
tab.index.name = "year"; tab.to_csv(RES / "a438_hours_by_year.csv")

def first_below(s, x):
    s = s.dropna(); b = s[s < x]; return int(b.index[0]) if len(b) else None
def stays_below(s, x):
    s = s.dropna(); ys = s.index.tolist()
    for i, y in enumerate(ys):
        if (s.iloc[i:] < x).all(): return int(y)
    return None
# パートの割合が動いた分と、それぞれの時間が動いた分（30人以上、1993→2025年）
def decomp(hf, hp, share, y0, y1):
    s0, s1 = share[y0] / 100, share[y1] / 100
    within = ((hf[y1] - hf[y0]) * (1 - (s0 + s1) / 2) + (hp[y1] - hp[y0]) * (s0 + s1) / 2) * 12
    mix = (s1 - s0) * ((hp[y0] + hp[y1]) / 2 - (hf[y0] + hf[y1]) / 2) * 12
    return {"total_change": float((h30[y1] - h30[y0]) * 12) if hf is h30f else float((h5[y1] - h5[y0]) * 12), "within": float(within), "mix": float(mix)}
ps30, ps5 = tab.part_share_30plus, tab.part_share_5plus
main = {"longest": {"year": int(ann.idxmax()), "monthly": float(long.max()), "annual": float(ann.max())},
        "annual": {str(y): round(float(ann[y]), 0) for y in (1950, 1955, 1960, 1965, 1970, 1975, 1980, 1988, 1990, 1992, 1993, 2000, 2005, 2010, 2020, 2024, 2025)},
        "first_below_2000_30plus": first_below(ann, 2000), "stays_below_2000_30plus": stays_below(ann, 2000),
        "first_below_2000_excl_service": first_below(tab.excl_service_annual, 2000),
        "first_below_1900_30plus": first_below(ann, 1900), "first_below_1800_30plus": first_below(ann, 1800), "stays_below_1800_30plus": stays_below(ann, 1800),
        "first_below_1700_30plus": first_below(ann, 1700), "min_30plus": [int(ann.idxmin()), round(float(ann.min()), 0)],
        "full_time_30plus": {str(y): round(float(h30f[y] * 12), 0) for y in (1993, 2000, 2010, 2018, 2019, 2020, 2025)},
        "full_time_first_below_2000": first_below(h30f * 12, 2000), "full_time_stays_below_2000": stays_below(h30f * 12, 2000), "full_time_first_below_1900": first_below(h30f * 12, 1900),
        "full_time_max": [int((h30f * 12).idxmax()), round(float((h30f * 12).max()), 0)], "full_time_min": [int((h30f * 12).idxmin()), round(float((h30f * 12).min()), 0)],
        "part_time_30plus": {str(y): round(float(h30p[y] * 12), 0) for y in (1993, 2010, 2025)},
        "part_share_30plus": {str(y): round(float(ps30[y]), 1) for y in (1993, 2000, 2010, 2025)}, "part_share_5plus": {str(y): round(float(ps5[y]), 1) for y in (1993, 2000, 2010, 2025)},
        "decomp_30plus_1993_2025": decomp(h30f, h30p, ps30, 1993, 2025), "decomp_5plus_1993_2025": decomp(h5f, h5p, ps5, 1993, 2025),
        "annual_5plus": {str(y): round(float(h5[y] * 12), 0) for y in (1990, 1993, 2000, 2010, 2025)}, "first_below_1800_5plus": first_below(h5 * 12, 1800), "first_below_2000_5plus": first_below(h5 * 12, 2000),
        "sched_over_30plus": {str(y): [round(float(tab.sched_annual_30plus[y]), 0), round(float(tab.overtime_annual_30plus[y]), 0)] for y in (1970, 1975, 1990, 2009, 2025)},
        "days_30plus": {str(y): float(tab.days_30plus[y]) for y in (1970, 1990, 2025)},
        "change_1988_1993": round(float(ann[1993] - ann[1988]), 0), "change_1960_1975": round(float(ann[1975] - ann[1960]), 0), "change_1975_1988": round(float(ann[1988] - ann[1975]), 0),
        "overlap_check": {"years": [int(ov.index.min()), int(ov.index.max())], "max_abs_diff_monthly": float(diff.max()), "n_diff": int((diff > 0.05).sum())}}
json.dump(main, open(RES / "a438_main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False))

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(ann.loc[1950:1969].index, ann.loc[1950:1969], color=BLUE, lw=2, ls="--", label="30人以上（サービス業を除く、1950〜69年）")
ax.plot(ann.loc[1970:].index, ann.loc[1970:], color=BLUE, lw=2, label="30人以上（調査産業計）")
ax.plot(h5.index, h5 * 12, color=GRAY, lw=1.6, label="5人以上（調査産業計、1990年〜）")
for y in (2000, 1800): ax.axhline(y, color=GRAY, lw=0.8, ls=":")
ax.set_ylabel("年間の総実労働時間（月間×12）"); ax.set_xlim(1950, 2025); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"年間の労働時間：{main['longest']['year']}年の{main['longest']['annual']:,.0f}時間が最長、2,000時間を切ったのは{main['first_below_2000_30plus']}年"); save(fig, "a438_annual_hours.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.4))
ax.plot(h30.loc[1993:].index, h30.loc[1993:] * 12, color=BLUE, lw=2, label="全体"); ax.plot(h30f.index, h30f * 12, color=INK, lw=2, label="一般労働者"); ax.plot(h30p.index, h30p * 12, color=ORANGE, lw=2, label="パートタイム労働者")
ax2 = ax.twinx(); ax2.bar(ps30.dropna().index, ps30.dropna(), color=LIGHT, alpha=0.5, width=0.8); ax2.set_ylim(0, 100); ax2.set_ylabel("パートの割合（%、うすい棒）"); ax2.spines["right"].set_visible(True)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.axhline(2000, color=GRAY, lw=0.8, ls=":"); ax.set_ylim(800, 2200); ax.set_ylabel("年間の総実労働時間"); ax.legend(frameon=False, ncol=3, fontsize=9, loc="lower left")
ax.set_title("一般労働者だけで見ると、2,000時間前後が長く続いた（30人以上、1993〜2025年）"); save(fig, "a438_full_part.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2)); t = tab.loc[1970:]
ax.bar(t.index, t.sched_annual_30plus, color=BLUE, label="所定内"); ax.bar(t.index, t.overtime_annual_30plus, bottom=t.sched_annual_30plus, color=ORANGE, label="所定外（残業など）")
ax.set_ylabel("年間の時間"); ax.set_xlim(1969.3, 2025.7); ax.legend(frameon=False, ncol=2, fontsize=9, loc="upper right")
ax.set_title("減ったのはおもに所定内の時間（30人以上、1970〜2025年）"); save(fig, "a438_sched_overtime.png", SRC)
