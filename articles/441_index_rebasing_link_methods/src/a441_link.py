"""441 基準の年が変わった指数をつなぐ方法で、長期の伸びはどれだけ変わるか（消費者物価指数 2010・2015・2020・2025年基準）"""
import csv, json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SER = ["総合", "生鮮食品を除く総合", "食料", "住居", "光熱・水道", "家具・家事用品", "被服及び履物", "保健医療", "交通・通信", "教育", "教養娯楽", "諸雑費"]
BASES = [2010, 2015, 2020, 2025]
SRC = "出典：総務省統計局「消費者物価指数」長期時系列データ（2010・2015・2020・2025年基準、中分類指数）を加工して作成"


def read(b):
    r = list(csv.reader(open(DATA / "raw" / f"cpi_base{b}_mid.csv", encoding="cp932")))
    idx = [r[0].index(s) for s in SER]          # 最初に出てくる列（全国）
    rows = [(x[0], *[float(x[i]) if x[i] not in ("", "-", "…") else np.nan for i in idx]) for x in r if x and x[0].isdigit() and len(x[0]) == 6]
    d = pd.DataFrame(rows, columns=["ym"] + SER)
    d["ym"] = pd.PeriodIndex(pd.to_datetime(d["ym"], format="%Y%m"), freq="M")
    return d.set_index("ym")


F = {b: read(b) for b in BASES}
tidy = pd.concat([F[b].reset_index().melt("ym", var_name="series", value_name="value").assign(base=b) for b in BASES])
tidy["ym"] = tidy["ym"].astype(str)
tidy[tidy["ym"] >= "2009-01"].to_csv(DATA / "cpi_four_bases_2009on.csv", index=False)

# ---- その基準が「現役」だった月だけを取り出す（基準年の1月〜ファイルの最後の月）
NAT = {b: F[b].loc[f"{b}-01":] for b in BASES}
JUN = [(2010, 2015), (2015, 2020), (2020, 2025)]


def factor(old, new, how, s):
    """新基準の値に掛けると旧基準の水準になる係数"""
    o, n = NAT[old][s], NAT[new][s]
    if how == "year":                      # 新基準の基準年（12か月）の平均どうし
        return o.loc[f"{new}-01":f"{new}-12"].mean() / n.loc[f"{new}-01":f"{new}-12"].mean()
    if how.startswith("m"):                # 新基準の基準年の m 月だけ
        k = f"{new}-{int(how[1:]):02d}"
        return o.loc[k] / n.loc[k]
    if how == "last":                      # 旧基準が公表された最後の月
        k = o.index[-1]
        return o.loc[k] / n.loc[k]


def linked(how, s):
    """2010年基準の水準で2010-01〜2026-09をつないだ系列"""
    parts, f = [], 1.0
    for (old, new) in JUN:
        cut = NAT[old].index[-1] if how == "last" else pd.Period(f"{new}-01", "M") - 1
        prev = parts[-1].index[-1] if parts else None
        seg = NAT[old][s].loc[:cut] * f
        if prev is not None: seg = seg.loc[prev + 1:]
        parts.append(seg)
        f *= factor(old, new, how, s)
    seg = NAT[2025][s] * f
    parts.append(seg.loc[parts[-1].index[-1] + 1:])
    return pd.concat(parts)


HOW = ["year"] + [f"m{k}" for k in range(1, 13)] + ["last"]
L = {(h, s): linked(h, s) for h in HOW for s in SER}
assert all(len(L[k]) == 201 for k in L)   # 2010-01〜2026-09

# ---- ① 2010年平均→2025年平均の伸び（%）
def growth(x): return (x.loc["2025-01":"2025-12"].mean() / x.loc["2010-01":"2010-12"].mean() - 1) * 100
G = pd.DataFrame({h: {s: growth(L[(h, s)]) for s in SER} for h in HOW})
off = F[2025]                                   # 公表の2025年基準の長期系列
G["公表（2025年基準の系列）"] = [growth(off[s]) for s in SER]
mcols = [f"m{k}" for k in range(1, 13)]
T1 = pd.DataFrame({"年平均でつなぐ": G["year"], "1月でつなぐ": G["m1"], "12月でつなぐ": G["m12"], "1か月でつなぐ（12通りの最小）": G[mcols].min(axis=1),
                   "1か月でつなぐ（12通りの最大）": G[mcols].max(axis=1), "旧基準の最後の月でつなぐ": G["last"], "公表（2025年基準の系列）": G["公表（2025年基準の系列）"]})
T1["1か月でつなぐ幅（ポイント）"] = T1["1か月でつなぐ（12通りの最大）"] - T1["1か月でつなぐ（12通りの最小）"]
T1["最後の月−年平均（ポイント）"] = T1["旧基準の最後の月でつなぐ"] - T1["年平均でつなぐ"]
T1["年平均−公表（ポイント）"] = T1["年平均でつなぐ"] - T1["公表（2025年基準の系列）"]
T1.round(3).to_csv(RES / "growth_2010_2025_by_method.csv")

# つなぎ目ごとの係数（年平均を1としたときの比、%）
rows = []
for (old, new) in JUN:
    for s in SER:
        fy = factor(old, new, "year", s)
        fm = [factor(old, new, f"m{k}", s) for k in range(1, 13)]
        rows.append(dict(junction=f"{old}→{new}", series=s, factor_year=fy, month_min_pct=(min(fm) / fy - 1) * 100, month_max_pct=(max(fm) / fy - 1) * 100,
                         last_pct=(factor(old, new, "last", s) / fy - 1) * 100, last_month=str(NAT[old].index[-1])))
T2 = pd.DataFrame(rows); T2.round(4).to_csv(RES / "link_factors_by_junction.csv", index=False)

# ---- ② 重なる期間の前年同月比（旧基準のファイルと新基準のファイル）
rows = []; YO = {}
for (old, new) in JUN:
    for s in SER:
        yo = (F[old][s].pct_change(12) * 100).round(1); yn = (F[new][s].pct_change(12) * 100).round(1)
        idx = NAT[old].loc[f"{new}-01":].index
        d = (yn.loc[idx] - yo.loc[idx]).round(1); YO[(new, s)] = d
        by = d.loc[f"{new}-01":f"{new}-12"]; ay = d.loc[f"{new + 1}-01":]
        rows.append(dict(junction=f"{old}→{new}", series=s, months=len(d), differ=int((d.abs() >= 0.1).sum()), differ_02=int((d.abs() >= 0.2).sum()), max_abs=float(d.abs().max()),
                         mean_diff=float(d.mean()), base_year_differ=int((by.abs() >= 0.1).sum()), next_year_months=len(ay), next_year_differ=int((ay.abs() >= 0.1).sum()),
                         next_year_mean=float(ay.mean())))
T3 = pd.DataFrame(rows); T3.round(3).to_csv(RES / "yoy_old_vs_new_base.csv", index=False)

# ---- ③ つなぎ方で前年同月比が変わる月（つないだ系列どうし、基準年の12か月×3回）
rows = []
for s in SER:
    ya = (L[("year", s)].pct_change(12) * 100)
    for h in ["m1", "m12", "last"]:
        yb = (L[(h, s)].pct_change(12) * 100)
        d = (yb.round(1) - ya.round(1)).dropna()
        d = d[(d.index.year.isin([2015, 2020, 2025])) | (h == "last")]
        rows.append(dict(series=s, method=h, months=len(d), differ=int((d.abs() >= 0.1).sum()), max_abs=float((yb - ya).abs().max())))
T4 = pd.DataFrame(rows); T4.round(3).to_csv(RES / "yoy_change_by_link_method.csv", index=False)

# ---- ④ 古い年の数字は、基準が変わるたびに丸めで動く（総合、5つの基準のファイル）
s05 = pd.read_csv(DATA / "cpi_base2005_sogo.csv", dtype={"ym": str}); s05.index = pd.PeriodIndex(pd.to_datetime(s05["ym"], format="%Y%m"), freq="M")
LONG = {2005: s05["sogo"], **{b: F[b]["総合"] for b in BASES}}
rows = []
for b, x in LONG.items():
    rows.append(dict(base=b, level_1970=x.loc["1970-01":"1970-12"].mean(), level_2005=x.loc["2005-01":"2005-12"].mean(),
                     growth_1970_2005=(x.loc["2005-01":"2005-12"].mean() / x.loc["1970-01":"1970-12"].mean() - 1) * 100,
                     growth_1975_2005=(x.loc["2005-01":"2005-12"].mean() / x.loc["1975-01":"1975-12"].mean() - 1) * 100,
                     growth_1970m1_2005m1=(x.loc["2005-01"] / x.loc["1970-01"] - 1) * 100))
T5 = pd.DataFrame(rows); T5.round(3).to_csv(RES / "long_run_growth_by_base_file.csv", index=False)
rows = []; ref = (LONG[2010].pct_change(12) * 100).round(1)
for b in [2005, 2015, 2020, 2025]:
    y = (LONG[b].pct_change(12) * 100).round(1)
    for a, z in [("1971-01", "1979-12"), ("1980-01", "1989-12"), ("1990-01", "1999-12"), ("2000-01", "2009-12")]:
        d = (y.loc[a:z] - ref.loc[a:z]).round(1)
        rows.append(dict(base=b, vs=2010, period=f"{a[:4]}〜{z[:4]}", months=len(d), differ=int((d.abs() >= 0.1).sum()), share=float((d.abs() >= 0.1).mean() * 100), max_abs=float(d.abs().max())))
T6 = pd.DataFrame(rows); T6.round(2).to_csv(RES / "old_years_yoy_rounding.csv", index=False)

# ---- SQL（年平均でつなぐ係数）を DuckDB で実行し、Python と一致することを確かめる
con = duckdb.connect(); con.execute("SET threads=1")
t = tidy.copy(); con.register("cpi", t)
q = """
WITH nat AS (SELECT base, series, ym, value FROM cpi WHERE ym >= CAST(base AS VARCHAR) || '-01'),
f AS (SELECT o.base AS old_base, n.base AS new_base, o.series, AVG(o.value) / AVG(n.value) AS factor
      FROM nat o JOIN nat n ON n.series = o.series AND n.ym = o.ym AND n.base = o.base + 5
      WHERE SUBSTR(o.ym, 1, 4) = CAST(n.base AS VARCHAR) GROUP BY o.base, n.base, o.series)
SELECT * FROM f ORDER BY old_base, series"""
fs = con.execute(q).df()
for _, r in fs.iterrows():
    assert abs(r["factor"] - factor(int(r["old_base"]), int(r["new_base"]), "year", r["series"])) < 1e-12
fs.round(6).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- まとめ
tot = "総合"
main = dict(
    n_series=len(SER), months=201, period="2010-01〜2026-09",
    growth_sogo={k: round(float(T1.loc[tot, k]), 3) for k in T1.columns},
    range_1month_pt={s: round(float(T1.loc[s, "1か月でつなぐ幅（ポイント）"]), 2) for s in SER},
    last_minus_year_pt={s: round(float(T1.loc[s, "最後の月−年平均（ポイント）"]), 2) for s in SER},
    year_minus_official_pt={s: round(float(T1.loc[s, "年平均−公表（ポイント）"]), 3) for s in SER},
    growth_year={s: round(float(T1.loc[s, "年平均でつなぐ"]), 2) for s in SER},
    yoy_overlap_sogo=T3[T3.series == tot].round(3).to_dict("records"),
    yoy_overlap_all=dict(months=int(T3.months.sum()), differ=int(T3.differ.sum()), share=round(float(T3.differ.sum() / T3.months.sum() * 100), 1), max_abs=float(T3.max_abs.max()),
                         worst=T3.sort_values("max_abs", ascending=False).head(5)[["junction", "series", "max_abs", "differ", "months"]].to_dict("records"),
                         base_year_differ=int(T3.base_year_differ.sum()), base_year_months=36 * len(SER), next_year_differ=int(T3.next_year_differ.sum()), next_year_months=int(T3.next_year_months.sum())),
    yoy_by_method=T4.round(3).to_dict("records"),
    long_run=T5.round(3).to_dict("records"), old_years=T6.round(2).to_dict("records"),
    factors_sogo=T2[T2.series == tot].round(4).to_dict("records"),
    factors_extreme=T2.assign(w=T2.month_max_pct - T2.month_min_pct).sort_values("w", ascending=False).head(6).round(3).to_dict("records"),
)
json.dump(main, open(RES / "a441_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図1：つなぎ方ごとの水準の差（総合と、差の大きい系列）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, s in zip(axs, ["総合", "光熱・水道"]):
    a = L[("year", s)]
    for k in range(1, 13):
        ax.plot(a.index.to_timestamp(), (L[(f"m{k}", s)] / a - 1) * 100, color=LIGHT, lw=0.9)
    ax.plot(a.index.to_timestamp(), (L[("m1", s)] / a - 1) * 100, color=BLUE, lw=1.6, label="1月でつなぐ")
    ax.plot(a.index.to_timestamp(), (L[("last", s)] / a - 1) * 100, color=ORANGE, lw=1.6, label="旧基準の最後の月でつなぐ")
    ax.axhline(0, color=INK, lw=0.8); ax.set_title(f"{s}：年平均でつないだ系列との差", fontsize=12); ax.set_ylabel("差（%）")
    for y in (2015, 2020, 2025): ax.axvline(pd.Timestamp(f"{y}-01-01"), color=GRAY, lw=0.6, ls=":")
axs[0].legend(frameon=False, fontsize=9)
fig.text(0.5, 0.0, "うすい青は「基準年のどれか1か月でつなぐ」12通り。2010年の水準をそろえて、先へつないでいったときの差。点線は基準の変わり目", ha="center", fontsize=8.5, color=GRAY)
save(fig, "a441_level_gap.png", SRC, y=-0.05)

# ---- 図2：2010年→2025年の伸びの、つなぎ方による幅
fig, ax = plt.subplots(figsize=(9.5, 5)); y = np.arange(len(SER))[::-1]
for i, s in zip(y, SER):
    ax.plot([T1.loc[s, "1か月でつなぐ（12通りの最小）"] - T1.loc[s, "年平均でつなぐ"], T1.loc[s, "1か月でつなぐ（12通りの最大）"] - T1.loc[s, "年平均でつなぐ"]], [i, i], color=LIGHT, lw=7, solid_capstyle="butt")
    ax.plot(T1.loc[s, "旧基準の最後の月でつなぐ"] - T1.loc[s, "年平均でつなぐ"], i, "o", color=ORANGE, ms=7)
    ax.plot(T1.loc[s, "公表（2025年基準の系列）"] - T1.loc[s, "年平均でつなぐ"], i, "|", color=INK, ms=14, mew=1.6)
ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y); ax.set_yticklabels([f"{s}（{T1.loc[s, '年平均でつなぐ']:+.1f}%）" for s in SER])
ax.set_xlabel("2010年平均→2025年平均の伸びの、年平均でつないだ場合との差（ポイント）")
ax.set_title("つなぎ方で変わる15年の伸び（かっこ内は年平均でつないだ伸び）")
ax.plot([], [], color=LIGHT, lw=7, label="基準年のどれか1か月でつなぐ（12通りの幅）"); ax.plot([], [], "o", color=ORANGE, label="旧基準の最後の月でつなぐ"); ax.plot([], [], "|", color=INK, ms=12, mew=1.6, label="公表の2025年基準の系列")
ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "a441_growth_gap.png", SRC)

# ---- 図3：重なる期間の前年同月比（新基準−旧基準、総合）と、古い年の丸め
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw=dict(width_ratios=[1.25, 1]))
ax = axs[0]
for (new, c) in [(2015, GRAY), (2020, BLUE), (2025, ORANGE)]:
    d = YO[(new, "総合")]; ax.plot(np.arange(1, len(d) + 1), d.values, "-o", color=c, ms=3.5, lw=1.2, label=f"{new - 5}年基準→{new}年基準")
ax.axhline(0, color=INK, lw=0.8); ax.axvline(12.5, color=GRAY, lw=0.6, ls=":"); ax.set_xlabel("新しい基準年の1月から数えた月"); ax.set_ylabel("前年同月比の差（新基準−旧基準、ポイント）")
ax.set_title("総合：同じ月の前年同月比の、基準による違い", fontsize=12); ax.legend(frameon=False, fontsize=9)
ax = axs[1]; per = ["1971〜1979", "1980〜1989", "1990〜1999", "2000〜2009"]; w = 0.2
for j, (b, c) in enumerate([(2005, GRAY), (2015, LIGHT), (2020, BLUE), (2025, ORANGE)]):
    v = [T6[(T6.base == b) & (T6.period == p)]["share"].iloc[0] for p in per]
    ax.bar(np.arange(4) + (j - 1.5) * w, v, w, color=c, label=f"{b}年基準のファイル")
ax.set_xticks(np.arange(4)); ax.set_xticklabels(per, fontsize=9); ax.set_ylabel("前年同月比が0.1ポイント以上違う月（%）")
ax.set_title("古い年の前年同月比（2010年基準と比べて）", fontsize=12); ax.legend(frameon=False, fontsize=8.5)
save(fig, "a441_yoy_differences.png", SRC)
print(json.dumps({k: main[k] for k in ["growth_sogo", "range_1month_pt", "last_minus_year_pt", "year_minus_official_pt", "growth_year", "yoy_overlap_all", "long_run", "factors_sogo"]}, ensure_ascii=False, indent=0)[:6000])
print(T6.to_string()); print(T4.to_string()); print(T3[T3.series=="総合"].to_string())
