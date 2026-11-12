"""A436 いちばん多い死因（病気）は、何から何へ入れ替わったのか
人口動態統計 上巻 5-12（死因年次推移分類別の死亡率、1899〜2024年）と 5-15（年齢5歳階級別、1950年〜）。
病気の5つ（結核・悪性新生物・心疾患・脳血管疾患・肺炎）だけを比べる。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：厚生労働省「人口動態統計」（2025年確定数 上巻 第5.12表・第5.15表）をもとに作成"
C5 = ["tuberculosis", "pneumonia", "stroke", "cancer", "heart"]
JA = {"tuberculosis": "結核", "pneumonia": "肺炎", "stroke": "脳血管疾患", "cancer": "悪性新生物（がん）", "heart": "心疾患"}
COL = {"tuberculosis": ORANGE, "pneumonia": GREEN, "stroke": BLUE, "cancer": INK, "heart": GRAY}

d = pd.read_csv(DATA / "jinkou_r7_jokan_5-12_diseases_total.csv")
r = d[["year"] + [f"{c}_rate" for c in C5] + ["total_rate"]].copy()
r.columns = ["year"] + C5 + ["total"]
r = r[r.year <= 2024].reset_index(drop=True)          # 2025年は率が未公表（人口が未確定）
r.to_csv(RES / "a436_rates_by_year.csv", index=False)

# --- 5つのうちの1位と、入れ替わった年 ---
top = r[C5].idxmax(axis=1)
runs = []
for y, t in zip(r.year, top):
    if runs and runs[-1]["cause"] == t and y - runs[-1]["end"] <= 4: runs[-1]["end"] = int(y)
    else: runs.append({"cause": t, "start": int(y), "end": int(y)})
pd.DataFrame([{**x, "cause_ja": JA[x["cause"]], "years": x["end"] - x["start"] + 1} for x in runs]).to_csv(RES / "a436_top_runs.csv", index=False)

def first_above(a, b, after=1899):
    """a の率が b を上回り、その後ずっと上回ったままになった最初の年"""
    ok = (r[a] > r[b]).values; ys = r.year.values
    for i in range(len(ys)):
        if ys[i] >= after and ok[i:].all(): return int(ys[i])
    return None
cross = {"stroke_over_tuberculosis": first_above("stroke", "tuberculosis"),
         "cancer_over_tuberculosis": first_above("cancer", "tuberculosis"),
         "cancer_over_stroke": first_above("cancer", "stroke"),
         "heart_over_stroke": first_above("heart", "stroke"),
         "pneumonia_over_stroke": first_above("pneumonia", "stroke")}

# --- 結核：山と、10分の1・100分の1になるまで ---
tb = r.set_index("year")["tuberculosis"]
pk_y = int(tb.idxmax()); pk = float(tb.max())
def below(frac):
    s = tb[tb.index > pk_y]; s = s[s <= pk * frac]
    return int(s.index[0]) if len(s) else None
tb_res = {"peak_year": pk_y, "peak_rate": pk, "half_year": below(0.5), "tenth_year": below(0.1), "hundredth_year": below(0.01),
          "rate_1947": float(tb[1947]), "rate_1950": float(tb[1950]), "rate_1955": float(tb[1955]), "rate_1960": float(tb[1960]),
          "rate_2024": float(tb[2024]), "deaths_peak_year": int(d.loc[d.tuberculosis_deaths.idxmax(), "year"]),
          "deaths_peak": int(d.tuberculosis_deaths.max()), "deaths_2025": int(d.loc[d.year == 2025, "tuberculosis_deaths"].iloc[0])}
tb_res["years_peak_to_tenth"] = tb_res["tenth_year"] - pk_y
tb_res["years_1947_to_tenth_of_1947"] = int(tb[(tb.index > 1947) & (tb <= tb[1947] / 10)].index[0]) - 1947

# --- 年齢構成を1950年にそろえた率（5-15）---
a = pd.read_csv(DATA / "jinkou_r7_jokan_5-15_diseases_by_age_total.csv")
ages = ["0-4歳"] + [f"{x}-{x+4}歳" for x in range(5, 90, 5)]
def tab(cause, kind): return a[(a.cause == cause) & (a.kind == kind)].pivot(index="age", columns="year", values="value")
td, tr = tab("total", "deaths"), tab("total", "rate")
years = [y for y in td.columns if y <= 2024]
def pop(y):
    """年齢別の人口 = 死亡総数 ÷ 死亡率 × 10万。90歳以上は1つにまとめる"""
    p = {g: td.loc[g, y] / tr.loc[g, y] * 1e5 for g in ages}
    if y <= 2000: p["90歳以上"] = np.nansum([td.loc[g, y] for g in ["90-94歳", "95-99歳", "100歳以上"]]) / tr.loc["90-94歳", y] * 1e5
    else: p["90歳以上"] = sum(td.loc[g, y] / tr.loc[g, y] * 1e5 for g in ["90-94歳", "95-99歳", "100歳以上"])
    return pd.Series(p)
P = {y: pop(y) for y in years}
std = P[1950] / P[1950].sum()
rows = []
for c in C5:
    cd = tab(c, "deaths")
    for y in years:
        dd = pd.Series({g: cd.loc[g, y] for g in ages}); dd["90歳以上"] = np.nansum([cd.loc[g, y] for g in ["90-94歳", "95-99歳", "100歳以上"]])
        dd = dd.fillna(0); asr = dd / P[y] * 1e5
        rows.append({"cause": c, "cause_ja": JA[c], "year": y, "crude": dd.sum() / P[y].sum() * 1e5, "age_fixed_1950": float((asr * std).sum()),
                     "published_crude": float(tab(c, "rate").loc["総数", y]), "share_65plus_of_deaths": float(dd[["65-69歳", "70-74歳", "75-79歳", "80-84歳", "85-89歳", "90歳以上"]].sum() / dd.sum())})
s = pd.DataFrame(rows); s.to_csv(RES / "a436_age_fixed_rates.csv", index=False)
chk = float((s.crude - s.published_crude).abs().max())
pop65 = {int(y): float(P[y][["65-69歳", "70-74歳", "75-79歳", "80-84歳", "85-89歳", "90歳以上"]].sum() / P[y].sum()) for y in (1950, 1980, 2024)}

def g(c, y, col): return float(s[(s.cause == c) & (s.year == y)][col].iloc[0])
main = {"years": [int(r.year.min()), int(r.year.max())], "top_runs": runs, "crossings": cross, "tuberculosis": tb_res,
        "rates": {str(y): {c: float(r.set_index("year").loc[y, c]) for c in C5} for y in (1899, 1918, 1935, 1950, 1951, 1960, 1980, 1981, 1985, 2000, 2011, 2024)},
        "share_of_all_deaths_2024": {c: float(d.loc[d.year == 2024, f"{c}_deaths"].iloc[0] / d.loc[d.year == 2024, "total_deaths"].iloc[0]) for c in C5},
        "share_of_all_deaths_1950": {c: float(d.loc[d.year == 1950, f"{c}_deaths"].iloc[0] / d.loc[d.year == 1950, "total_deaths"].iloc[0]) for c in C5},
        "age_fixed": {c: {"crude_1950": g(c, 1950, "crude"), "crude_2024": g(c, 2024, "crude"), "fixed_2024": g(c, 2024, "age_fixed_1950"),
                          "fixed_peak_year": int(s[s.cause == c].set_index("year")["age_fixed_1950"].idxmax()),
                          "fixed_peak": float(s[s.cause == c]["age_fixed_1950"].max()), "share65_1950": g(c, 1950, "share_65plus_of_deaths"), "share65_2024": g(c, 2024, "share_65plus_of_deaths")} for c in C5},
        "pop_share_65plus": pop65, "max_abs_diff_crude_vs_published": chk}
json.dump(main, open(RES / "a436_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False)[:3000])

# --- 図1：5つの病気の死亡率 ---
fig, ax = plt.subplots(figsize=(9, 4.8))
for c in C5:
    ax.plot(r.year, r[c], color=COL[c], lw=2 if c in ("tuberculosis", "cancer") else 1.6, label=JA[c])
ax.axvspan(1943.5, 1946.5, color="#eeeeee"); ax.text(1945, ax.get_ylim()[1] * 0.93, "資料なし", ha="center", fontsize=8, color=GRAY)
ax.set_ylabel("人口10万人あたりの死亡数"); ax.set_xlim(1899, 2025); ax.legend(frameon=False, ncol=3, fontsize=9, loc="upper center")
ax.set_title("5つの病気の死亡率（1899〜2024年）")
save(fig, "a436_rates.png", SRC)

# --- 図2：結核の率（対数）と、5つのうちの1位 ---
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9, 5.2), gridspec_kw={"height_ratios": [3.2, 1]}, sharex=True)
ax.plot(tb.index, tb.values, color=ORANGE, lw=2); ax.set_yscale("log"); ax.set_ylabel("結核の死亡率（人口10万対、対数）")
for fr, lab in ((1, "山"), (0.1, "山の10分の1"), (0.01, "山の100分の1")):
    ax.axhline(pk * fr, color=GRAY, lw=0.8, ls=":"); ax.text(1900, pk * fr * 1.08, f"{lab}（{pk*fr:.1f}）", fontsize=8, color=GRAY)
ax.set_title(f"結核の死亡率：{pk_y}年の{pk:.0f}から、{tb_res['tenth_year']}年に10分の1、{tb_res['hundredth_year']}年に100分の1")
for x in runs:
    ax2.barh(0, x["end"] - x["start"] + 1, left=x["start"] - 0.5, color=COL[x["cause"]], height=0.6)
    if x["end"] - x["start"] >= 6: ax2.text((x["start"] + x["end"]) / 2, 0, JA[x["cause"]].split("（")[0], ha="center", va="center", fontsize=8.5, color="white")
ax2.set_yticks([]); ax2.set_xlim(1899, 2025); ax2.set_xlabel("5つの病気のうち、率がいちばん高かったもの"); ax2.spines["left"].set_visible(False)
save(fig, "a436_tuberculosis_top.png", SRC)

# --- 図3：そのままの率と、年齢構成を1950年にそろえた率 ---
fig, axes = plt.subplots(1, 4, figsize=(11, 3.6), sharey=False)
for ax, c in zip(axes, ["cancer", "heart", "stroke", "pneumonia"]):
    x = s[s.cause == c]
    ax.plot(x.year, x.crude, color=INK, lw=1.8, label="そのままの率"); ax.plot(x.year, x.age_fixed_1950, color=ORANGE, lw=1.8, label="年齢構成を1950年にそろえた率")
    ax.set_title(JA[c].split("（")[0], fontsize=11); ax.set_ylim(0, None); ax.set_xticks([1950, 1975, 2000, 2024])
axes[0].set_ylabel("人口10万人あたり"); h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, frameon=False, fontsize=9, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.08))
fig.suptitle("年齢構成を1950年にそろえると、4つの病気の率はどれも1950年より低い", y=1.02, fontsize=12)
save(fig, "a436_age_fixed.png", SRC, y=-0.1)
