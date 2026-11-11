"""254 米の10a当たり収量は、天候でどれだけ揺れるのか

農林水産省「作物統計調査」の水稲の収穫量累年統計（記事111と同じ整形済みデータ data/rice_panel.csv）と
気象庁「日本の季節平均気温」（data/ssn_jpn.csv）で、
  1. 全国の作況指数（2020年以降は作況単収指数）の揺れ（標準偏差・不作の年の数）を時期ごとに比べる
  2. 平年収量に頼らない見方として、10a当たり収量の対数から LOWESS のトレンドを引いた偏差でも同じことをする
  3. 地域（9地域＋北海道）ごとの揺れを 1958〜1999年と2000〜2025年で比べる
  4. 夏（6〜8月）の気温の揺れそのものが小さくなったのか、気温1℃当たりの効き方が小さくなったのかを分ける
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess
from common import DATA, RES, FIG, setup_font

setup_font()
P = pd.read_csv(DATA / "rice_panel.csv")
reg = P[P.level == "region"]
nat = reg[reg.name == "全国"].set_index("year")
sak = nat["sakkyo_any"].dropna()          # 1926〜2025年
T = pd.read_csv(DATA / "ssn_jpn.csv")
T.columns = ["year", "winter", "spring", "summer", "autumn"]
T = T.set_index("year")["summer"].astype(float)

PERIODS = [(1926, 1944), (1946, 1969), (1970, 1999), (2000, 2025)]
LAB = {p: f"{p[0]}〜{p[1]}年" for p in PERIODS}


def stats(x):
    return {"年数": int(len(x)), "標準偏差": round(float(x.std(ddof=1)), 2),
            "平年との差の絶対値の平均": round(float((x - 100).abs().mean()), 2),
            "95未満の年": int((x < 95).sum()), "90以下の年": int((x <= 90).sum()),
            "最低": float(x.min()), "最低の年": int(x.idxmin())}


res = {"作況指数_時期別": {LAB[p]: stats(sak.loc[p[0]:p[1]]) for p in PERIODS}}
res["作況指数_1945年"] = float(sak.loc[1945])
res["作況指数_2010〜2025年"] = stats(sak.loc[2010:2025])

# 2. 平年収量に頼らない偏差（10a当たり収量の対数 − LOWESS トレンド、%）
y = nat["yield_kg"].dropna().loc[1883:2025]
ly = np.log(y.values)
trend = lowess(ly, y.index.values, frac=0.3, return_sorted=False)
dev = pd.Series((np.exp(ly - trend) - 1) * 100, index=y.index)
res["自前のトレンドからの偏差_標準偏差（%）"] = {LAB[p]: round(float(dev.loc[p[0]:p[1]].std()), 2) for p in PERIODS}
res["自前のトレンドからの偏差_標準偏差（%）"]["1883〜1925年"] = round(float(dev.loc[1883:1925].std()), 2)
for frac in (0.2, 0.4):
    tr = lowess(ly, y.index.values, frac=frac, return_sorted=False)
    dv = pd.Series((np.exp(ly - tr) - 1) * 100, index=y.index)
    res[f"頑健性_LOWESS_frac{frac}_標準偏差（%）"] = {LAB[p]: round(float(dv.loc[p[0]:p[1]].std()), 2) for p in PERIODS}

# 3. 地域別（1958〜1999 と 2000〜2025）
REG = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州"]
rows = []
for r in REG:
    s = reg[reg.name == r].set_index("year")["sakkyo_any"].dropna()
    a, b = s.loc[1958:1999], s.loc[2000:2025]
    rows.append({"地域": r, "1958〜1999年_標準偏差": round(a.std(), 2), "2000〜2025年_標準偏差": round(b.std(), 2),
                 "1958〜1999年_95未満の年": int((a < 95).sum()), "2000〜2025年_95未満の年": int((b < 95).sum()),
                 "1958〜1999年_最低": a.min(), "2000〜2025年_最低": b.min()})
R = pd.DataFrame(rows)
R["比（後÷前）"] = (R["2000〜2025年_標準偏差"] / R["1958〜1999年_標準偏差"]).round(2)
R.to_csv(RES / "a254_region_sd.csv", index=False)

# 4. 気温の揺れと効き方
tt = T.loc[1898:2025]
ttr = lowess(tt.values, tt.index.values, frac=0.3, return_sorted=False)
tdev = pd.Series(tt.values - ttr, index=tt.index)
df = pd.DataFrame({"sak": sak, "t": tdev}).dropna()
temp_rows = {}
for p in PERIODS:
    d = df.loc[p[0]:p[1]]
    if p == (1946, 1969):
        d = d.drop(index=[1945], errors="ignore")
    X = sm.add_constant(np.minimum(d["t"], 0))
    m = sm.OLS(d["sak"], X).fit(cov_type="HC1")
    temp_rows[LAB[p]] = {"夏の気温偏差の標準偏差（℃）": round(float(d["t"].std()), 2),
                         "涼しい側の傾き（作況指数/℃）": round(float(m.params.iloc[1]), 1),
                         "傾きの標準誤差": round(float(m.bse.iloc[1]), 1),
                         "決定係数": round(float(m.rsquared), 2),
                         "偏差−0.5℃以下の年": int((d["t"] <= -0.5).sum())}
res["気温_時期別"] = temp_rows
# 頑健性：1993年（記録的な冷夏）を除いた 1970〜1999年の傾き
d = df.loc[1970:1999].drop(index=[1993])
m = sm.OLS(d["sak"], sm.add_constant(np.minimum(d["t"], 0))).fit(cov_type="HC1")
res["頑健性_1993年を除く1970〜1999年の傾き"] = {"傾き": round(float(m.params.iloc[1]), 1), "標準誤差": round(float(m.bse.iloc[1]), 1)}
d = df.loc[2000:2025].drop(index=[2003])
m = sm.OLS(d["sak"], sm.add_constant(np.minimum(d["t"], 0))).fit(cov_type="HC1")
res["頑健性_2003年を除く2000〜2025年の傾き"] = {"傾き": round(float(m.params.iloc[1]), 1), "標準誤差": round(float(m.bse.iloc[1]), 1)}
# 気温の揺れを固定したら、揺れはどれだけ残るか：後の時期の傾きで、前の時期の気温を当てはめたときの作況の標準偏差
d0, d1 = df.loc[1970:1999], df.loc[2000:2025]
b1 = temp_rows[LAB[(2000, 2025)]]["涼しい側の傾き（作況指数/℃）"]
b0 = temp_rows[LAB[(1970, 1999)]]["涼しい側の傾き（作況指数/℃）"]
res["分け方_1970〜1999年の気温に2000〜2025年の傾き"] = round(float((b1 * np.minimum(d0["t"], 0)).std()), 2)
res["分け方_1970〜1999年の気温に1970〜1999年の傾き"] = round(float((b0 * np.minimum(d0["t"], 0)).std()), 2)
res["分け方_2000〜2025年の気温に1970〜1999年の傾き"] = round(float((b0 * np.minimum(d1["t"], 0)).std()), 2)
res["涼しい夏の年_1980年以降"] = {int(k): {"気温偏差": round(float(v), 2), "作況指数": float(df.loc[k, "sak"])}
                                for k, v in df.loc[1980:, "t"].items() if v <= -0.5}

json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"作況指数": sak, "自前の偏差（%）": dev.round(2), "夏の気温偏差（トレンド除去、℃）": tdev.round(3)}).to_csv(RES / "a254_national_series.csv")

# 図1：全国の作況指数の推移
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ax.axhline(100, color="#888", lw=0.8)
ax.axhspan(95, 105, color="#eee", zorder=0)
ax.plot(sak.index, sak.values, color="#2b6cb0", lw=1.4, marker="o", ms=2.5)
for p in PERIODS:
    sd = res["作況指数_時期別"][LAB[p]]["標準偏差"]
    ax.text((p[0] + p[1]) / 2, 124, f"{LAB[p]}\n標準偏差 {sd}", ha="center", va="top", fontsize=8.5)
for yy in [1945, 1953, 1980, 1993, 2003]:
    ax.annotate(f"{yy}年 {int(sak[yy])}", (yy, sak[yy]), xytext=(yy + 1.5, sak[yy] - 4), fontsize=8, color="#c53030")
ax.set_ylim(60, 126)
ax.set_ylabel("作況指数（平年＝100）")
ax.set_title("米の作況指数（全国）：揺れは2000年以降に小さくなった", fontsize=11)
ax.text(0.0, -0.13, "2020年以降は作況単収指数。灰色の帯は95〜105。出典：農林水産省「作物統計調査」", transform=ax.transAxes, fontsize=7.5, color="#555")
fig.tight_layout(); fig.savefig(FIG / "a254_national.png", dpi=150); plt.close(fig)

# 図2：地域別の標準偏差
fig, ax = plt.subplots(figsize=(8.2, 4.2))
x = np.arange(len(R))
ax.bar(x - 0.2, R["1958〜1999年_標準偏差"], 0.4, label="1958〜1999年", color="#a0aec0")
ax.bar(x + 0.2, R["2000〜2025年_標準偏差"], 0.4, label="2000〜2025年", color="#2b6cb0")
for i, r in R.iterrows():
    ax.text(i - 0.2, r["1958〜1999年_標準偏差"] + 0.3, f'{r["1958〜1999年_標準偏差"]:.1f}', ha="center", fontsize=7.5)
    ax.text(i + 0.2, r["2000〜2025年_標準偏差"] + 0.3, f'{r["2000〜2025年_標準偏差"]:.1f}', ha="center", fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(R["地域"], fontsize=9)
ax.set_ylabel("作況指数の標準偏差")
ax.set_title("地域ごとの作況指数の揺れ：8地域で半分前後に。九州は2割減", fontsize=11)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "a254_region.png", dpi=150); plt.close(fig)

# 図3：夏の気温偏差と作況指数
fig, ax = plt.subplots(figsize=(7.4, 4.6))
cols = {LAB[(1926, 1944)]: "#cbd5e0", LAB[(1946, 1969)]: "#a0aec0", LAB[(1970, 1999)]: "#ed8936", LAB[(2000, 2025)]: "#2b6cb0"}
for p in PERIODS:
    d = df.loc[p[0]:p[1]].drop(index=[1945], errors="ignore")
    ax.scatter(d["t"], d["sak"], s=18, color=cols[LAB[p]], label=f'{LAB[p]}：1℃涼しいと {temp_rows[LAB[p]]["涼しい側の傾き（作況指数/℃）"]} 下がる')
for yy in [1993, 2003, 1980]:
    ax.annotate(str(yy), (df.loc[yy, "t"], df.loc[yy, "sak"]), xytext=(4, -2), textcoords="offset points", fontsize=8)
ax.axhline(100, color="#888", lw=0.7); ax.axvline(0, color="#888", lw=0.7)
ax.set_xlabel("夏（6〜8月）の気温偏差（長期のトレンドを除いた値、℃）")
ax.set_ylabel("作況指数")
ax.set_title("涼しい夏ほど作況が落ちる。2000年以降は落ち方が小さい", fontsize=11)
ax.legend(frameon=False, fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "a254_temp.png", dpi=150); plt.close(fig)
print(json.dumps(res, ensure_ascii=False, indent=1))
print(R.to_string())
