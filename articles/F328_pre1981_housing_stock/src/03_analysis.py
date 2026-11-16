"""03 分析：1980年以前の住宅の残り方（全国・都道府県）、耐震工事の割合、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
P = pd.read_csv(ROOT / "data" / "pref_period.csv")
Rt = pd.read_csv(ROOT / "data" / "owned_retrofit.csv")
PRE = ["-1950", "1951", "1971"]
METRO = [11, 12, 13, 14, 21, 23, 24, 26, 27, 28, 29]; CHIHO = [p for p in range(1, 48) if p not in METRO]; TK = [11, 12, 13, 14]
def r(x, n=1): return float(round(float(x), n))

def pre(col="dwellings", periods=PRE, alloc=False):
    q = P[P.period.isin(periods)].groupby(["year", "pref"])[col].sum().unstack("year")
    if alloc:  # 建築の時期「不詳」を、時期のわかる住宅と同じ割合で配る
        tot = P[P.period == "total"].set_index(["year", "pref"])[col].unstack("year")
        unk = P[P.period == "unknown"].set_index(["year", "pref"])[col].unstack("year")
        q = q * tot / (tot - unk)
    return q

M = {}
# ---- 全国の持ち家：2003〜2023年
own = Rt[Rt.pre1981].groupby("year")[["owned", "retrofit_5y"]].sum()
own.loc[2023, "owned"] = pre("owned").loc[0, 2023]
own["5年後に残る割合_%"] = (own["owned"] / own["owned"].shift(1) * 100).round(2)
own["耐震工事をした割合_%"] = (own["retrofit_5y"] / own["owned"] * 100).round(2)
own.index.name = "year"; own.to_csv(RES / "national_owned_pre1981.csv")
s23 = own.loc[2023, "5年後に残る割合_%"]
M["全国_持ち家_1980年以前"] = {str(int(y)): int(v) for y, v in own["owned"].items()}
M["全国_持ち家_5年後に残る割合_%"] = {str(int(y)): (None if pd.isna(v) else float(v)) for y, v in own["5年後に残る割合_%"].items()}
M["H1"] = {"2018_2023_残る割合_%": float(s23), "判定": ("支持" if s23 >= 90 else "外れ") + "（参考：全国の値を先に見ていた）"}
rf = own["耐震工事をした割合_%"].dropna()
M["H4"] = {"耐震工事をした割合_%": {str(int(y)): float(v) for y, v in rf.items()}, "判定": "支持" if (rf < 5).all() else "外れ"}

# ---- 都道府県：人が住む住宅すべて、2018→2023年
D = pre(); tot = P[P.period == "total"].set_index(["year", "pref"])["dwellings"].unstack("year")
names = P[(P.year == 2023)].drop_duplicates("pref").set_index("pref")["name"]
T = pd.DataFrame({"県": names, "1980年以前_2018": D[2018], "1980年以前_2023": D[2023],
                  "5年後に残る割合_%": (D[2023] / D[2018] * 100).round(2),
                  "1980年以前の割合_2023_%": (D[2023] / tot[2023] * 100).round(2),
                  "1980年以前の割合_2018_%": (D[2018] / tot[2018] * 100).round(2)})
T.index.name = "pref"; T.to_csv(RES / "pref_pre1981.csv")
mm = lambda col, g: float(T.loc[g, col].mean())
M["全国_すべて"] = {"1980年以前_2018": int(D.loc[0, 2018]), "1980年以前_2023": int(D.loc[0, 2023]),
                  "5年後に残る割合_%": float(T.loc[0, "5年後に残る割合_%"]), "割合_2018_%": float(T.loc[0, "1980年以前の割合_2018_%"]),
                  "割合_2023_%": float(T.loc[0, "1980年以前の割合_2023_%"])}
M["H2"] = {"三大都市圏_平均_%": r(mm("5年後に残る割合_%", METRO), 2), "地方圏_平均_%": r(mm("5年後に残る割合_%", CHIHO), 2),
           "判定": "支持" if mm("5年後に残る割合_%", METRO) < mm("5年後に残る割合_%", CHIHO) else "外れ"}
M["H3"] = {"三大都市圏_平均_%": r(mm("1980年以前の割合_2023_%", METRO), 2), "地方圏_平均_%": r(mm("1980年以前の割合_2023_%", CHIHO), 2),
           "判定": "支持" if mm("1980年以前の割合_2023_%", CHIHO) - mm("1980年以前の割合_2023_%", METRO) >= 3 else "外れ"}
M["県の範囲"] = {"5年後に残る割合_%": [r(T.loc[1:47, "5年後に残る割合_%"].min(), 1), r(T.loc[1:47, "5年後に残る割合_%"].max(), 1)],
              "1980年以前の割合_2023_%": [r(T.loc[1:47, "1980年以前の割合_2023_%"].min(), 1), r(T.loc[1:47, "1980年以前の割合_2023_%"].max(), 1)]}
M["残る割合_100超の県の数"] = int((T.loc[1:47, "5年後に残る割合_%"] > 100).sum())

# ---- 頑健性
rob = []
Do = pre("owned")
so = Do[2023] / Do[2018] * 100
rob.append(("持ち家だけ", r(so[METRO].mean(), 2), r(so[CHIHO].mean(), 2), r(so[0], 2)))
Da = pre(alloc=True); sa = Da[2023] / Da[2018] * 100
rob.append(("建築の時期「不詳」を配る", r(sa[METRO].mean(), 2), r(sa[CHIHO].mean(), 2), r(sa[0], 2)))
for lab, per in [("1950年以前だけ", ["-1950"]), ("1951〜1970年だけ", ["1951"]), ("1971〜1980年だけ", ["1971"])]:
    Dp = pre(periods=per); sp = Dp[2023] / Dp[2018] * 100
    rob.append((lab, r(sp[METRO].mean(), 2), r(sp[CHIHO].mean(), 2), r(sp[0], 2)))
rob.append(("比べる相手を東京圏（4都県）に", r(T.loc[TK, "5年後に残る割合_%"].mean(), 2), r(mm("5年後に残る割合_%", CHIHO), 2), float(T.loc[0, "5年後に残る割合_%"])))
R = pd.DataFrame(rob, columns=["変えたこと", "大都市圏_平均_%", "地方圏_平均_%", "全国_%"])
R["H2"] = np.where(R["大都市圏_平均_%"] < R["地方圏_平均_%"], "支持", "外れ")
R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {row[0]: {"大都市圏": row[1], "地方圏": row[2], "全国": row[3], "H2": h} for row, h in zip(rob, R["H2"])}

# ---- 問い直し（結果を見てから足した）：古い住宅がよく残る県は、人が住む住宅全体が増えている県か
from scipy import stats
T["住宅全体の増減率_%"] = ((tot[2023] / tot[2018] - 1) * 100).round(2)
T.to_csv(RES / "pref_pre1981.csv")
q = T.loc[1:47]
rho = stats.spearmanr(q["住宅全体の増減率_%"], q["5年後に残る割合_%"])[0]
pr = stats.pearsonr(q["住宅全体の増減率_%"], q["5年後に残る割合_%"])[0]
lr = stats.linregress(q["住宅全体の増減率_%"], q["5年後に残る割合_%"])
M["問い直し"] = {"順位相関": r(rho, 3), "相関_r": r(pr, 3), "傾き_1ポイントあたり": r(lr.slope, 3),
               "住宅全体が減った県の数": int((q["住宅全体の増減率_%"] < 0).sum()),
               "住宅全体が減った県の残る割合_平均_%": r(q.loc[q["住宅全体の増減率_%"] < 0, "5年後に残る割合_%"].mean(), 2),
               "住宅全体が増えた県の残る割合_平均_%": r(q.loc[q["住宅全体の増減率_%"] >= 0, "5年後に残る割合_%"].mean(), 2)}
# 参考の計算：2018→2023年と同じ割合で減り続けると仮定したとき、半分になるまでの年数（予測ではない）
for lab, sv in [("持ち家", s23), ("住宅すべて", float(T.loc[0, "5年後に残る割合_%"]))]:
    M["問い直し"][f"半分になるまでの年数_{lab}（同じ割合が続くと仮定）"] = r(5 * np.log(0.5) / np.log(sv / 100), 0)

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
