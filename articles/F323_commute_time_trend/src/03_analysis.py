"""03 分析：通勤・通学時間の推移、2016→2021年の県別の変化、頑健性、問い直し（オフライン）。"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
N = pd.read_csv(ROOT / "data" / "national.csv")
P = pd.read_csv(ROOT / "data" / "pref.csv")
TK = [11, 12, 13, 14]
METRO = [11, 12, 13, 14, 21, 23, 24, 26, 27, 28, 29]
CHIHO = [p for p in range(1, 48) if p not in METRO]
NAGOYA_OSAKA = [21, 23, 24, 26, 27, 28, 29]
SEED = 20261116
def r(x, n=1): return float(round(float(x), n))

M = {}
# ---- 全国の推移
nt = N.pivot_table(index="year", columns=["sex", "day"], values="commute_min")
nt.columns = [f"{a}_{b}" for a, b in nt.columns]
nt.to_csv(RES / "national_trend.csv")
g = lambda y, s="総数", d="週全体": float(N[(N.year == y) & (N.sex == s) & (N.day == d)].commute_min.iloc[0])
M["全国_有業者"] = {f"{d}_{y}": g(y, d=d) for d in ["週全体", "平日"] for y in [1976, 1986, 2001, 2016, 2021]}
d1 = g(2016) - g(1986)
M["H1"] = {"1986→2016_週全体_分": r(d1, 0), "1986→2016_平日_分": r(g(2016, d="平日") - g(1986, d="平日"), 0),
           "判定": ("支持" if d1 >= 3 else "外れ") + "（参考：数字を見たあとに置いた仮説）"}

# ---- 県別の変化
def wide(group="正規の職員・従業員", day="平日", sex="総数"):
    q = P[(P.group == group) & (P.day == day) & (P.sex == sex)]
    w = q.pivot(index="pref", columns="year", values="commute_min")
    w["変化"] = w[2021] - w[2016]
    return w

def h2(w):
    tk = w.loc[TK, "変化"].mean(); ch = w.loc[CHIHO, "変化"].mean()
    return tk, ch

def h3(w, drop=()):
    q = w.drop(index=[0, *drop])
    pr = stats.pearsonr(q[2016], q["変化"])[0]; sp = stats.spearmanr(q[2016], q["変化"])[0]
    return pr, sp, q

W = wide()
names = P[P.year == 2021].drop_duplicates("pref").set_index("pref")["area"]
out = W.copy(); out.insert(0, "県", names.reindex(out.index).values); out.to_csv(RES / "pref_change_regular_weekday.csv")
tk, ch = h2(W)
M["H2"] = {"東京圏_平均変化_分": r(tk, 2), "地方圏_平均変化_分": r(ch, 2),
           "名古屋大阪圏_平均変化_分": r(W.loc[NAGOYA_OSAKA, "変化"].mean(), 2),
           "東京圏_2016_平均_分": r(W.loc[TK, 2016].mean(), 1), "地方圏_2016_平均_分": r(W.loc[CHIHO, 2016].mean(), 1),
           "東京圏_2021_平均_分": r(W.loc[TK, 2021].mean(), 1), "地方圏_2021_平均_分": r(W.loc[CHIHO, 2021].mean(), 1),
           "全国_2016_分": float(W.loc[0, 2016]), "全国_2021_分": float(W.loc[0, 2021]),
           "判定": "支持" if (tk < 0 and tk <= 2 * ch and ch < 0) or (tk < 0 and ch >= 0) else "外れ"}
M["H2"]["減った県の数"] = int((W.drop(index=0)["変化"] < 0).sum()); M["H2"]["増えた県の数"] = int((W.drop(index=0)["変化"] > 0).sum())
pr, sp, q = h3(W)
rng = np.random.default_rng(SEED)
bs = []
x, yv = q[2016].values, q["変化"].values
for _ in range(2000):
    i = rng.integers(0, len(x), len(x))
    if np.std(x[i]) > 0 and np.std(yv[i]) > 0:
        bs.append(np.corrcoef(x[i], yv[i])[0, 1])
lo, hi = np.percentile(bs, [2.5, 97.5])
slope = stats.linregress(q[2016], q["変化"])
M["H3"] = {"ピアソン_r": r(pr, 3), "スピアマン_rho": r(sp, 3), "r_95%区間": [r(lo, 3), r(hi, 3)],
           "傾き_分あたり": r(slope.slope, 3), "判定": "支持" if pr <= -0.5 else "外れ"}
# レビューで追加：東京圏の4都県を除いた相関、地方圏36道県だけの相関（4点の影響と平均への回帰の確かめ）
pr_x4, sp_x4, _ = h3(W, tuple(TK)); pr_ch = stats.pearsonr(W.loc[CHIHO, 2016], W.loc[CHIHO, "変化"])[0]
M["H3"]["東京圏を除く43道府県_r"] = r(pr_x4, 3); M["H3"]["東京圏を除く43道府県_rho"] = r(sp_x4, 3)
M["H3"]["地方圏36道県だけ_r"] = r(pr_ch, 3)
# H4（参考）：全国の正規の職員・従業員
w4 = wide(day="週全体"); w4h = wide()
M["H4"] = {"正規_週全体_2016": float(w4.loc[0, 2016]), "正規_週全体_2021": float(w4.loc[0, 2021]),
           "正規_平日_2016": float(w4h.loc[0, 2016]), "正規_平日_2021": float(w4h.loc[0, 2021]),
           "有業者_週全体_2016": g(2016), "有業者_週全体_2021": g(2021),
           "判定": ("支持" if (w4.loc[0, 2016] - w4.loc[0, 2021]) >= 3 else "外れ") + "（参考）"}

# ---- 頑健性
rob = []
for lab, kw, drop in [("週全体で", dict(day="週全体"), ()), ("有業者総数で", dict(group="有業者総数"), ()),
                      ("男", dict(sex="男"), ()), ("女", dict(sex="女"), ()), ("東京都を除く", {}, (13,))]:
    w = wide(**kw)
    a, b = h2(w) if 13 not in drop else (w.loc[[11, 12, 14], "変化"].mean(), w.loc[CHIHO, "変化"].mean())
    p_, s_, _ = h3(w, drop)
    rob.append({"変えたこと": lab, "東京圏_平均変化": r(a, 2), "地方圏_平均変化": r(b, 2),
                "H2": "支持" if (a < 0 and ((b < 0 and a <= 2 * b) or b >= 0)) else "外れ",
                "ピアソン_r": r(p_, 3), "スピアマン_rho": r(s_, 3), "H3": "支持" if p_ <= -0.5 else "外れ"})
rob.append({"変えたこと": "スピアマンの順位相関（主の設定）", "東京圏_平均変化": r(tk, 2), "地方圏_平均変化": r(ch, 2),
            "H2": M["H2"]["判定"], "ピアソン_r": r(pr, 3), "スピアマン_rho": r(sp, 3), "H3": "支持" if sp <= -0.5 else "外れ"})
R = pd.DataFrame(rob); R.to_csv(RES / "robustness.csv", index=False)
M["頑健性"] = {d["変えたこと"]: {k: v for k, v in d.items() if k != "変えたこと"} for d in rob}

# ---- 問い直し：構成の変化で見かけが変わったか（全国、2016→2021、週全体）
#  有業者総数の変化を「正規の職員・従業員の割合の変化」と「区分の中の時間の変化」に分ける（2区分：正規・それ以外）
def comp(day):
    tot = P[(P.pref == 0) & (P.sex == "総数") & (P.day == day)].set_index(["year", "group"])
    out = {}
    for y in (2016, 2021):
        n_all = tot.loc[(y, "有業者総数"), "pop_k"]; n_reg = tot.loc[(y, "正規の職員・従業員"), "pop_k"]
        t_all = tot.loc[(y, "有業者総数"), "commute_min"]; t_reg = tot.loc[(y, "正規の職員・従業員"), "commute_min"]
        s = n_reg / n_all; t_oth = (t_all - s * t_reg) / (1 - s)
        out[y] = (s, t_reg, t_oth, t_all)
    (s0, a0, b0, T0), (s1, a1, b1, T1) = out[2016], out[2021]
    share_eff = (s1 - s0) * ((a0 + a1) / 2 - (b0 + b1) / 2)
    within = ((s0 + s1) / 2) * (a1 - a0) + (1 - (s0 + s1) / 2) * (b1 - b0)
    return {"正規の割合_2016_%": r(s0 * 100), "正規の割合_2021_%": r(s1 * 100),
            "正規_分": [float(a0), float(a1)], "正規以外_分（逆算）": [r(b0, 2), r(b1, 2)],
            "有業者総数の変化_分": r(T1 - T0, 2), "構成の寄与_分": r(share_eff, 2), "区分の中の変化の寄与_分": r(within, 2)}
M["問い直し"] = {"週全体": comp("週全体"), "平日": comp("平日")}
# 2021年の東京圏と地方圏の差は縮んだか
M["問い直し"]["東京圏−地方圏_2016_分"] = r(W.loc[TK, 2016].mean() - W.loc[CHIHO, 2016].mean(), 1)
M["問い直し"]["東京圏−地方圏_2021_分"] = r(W.loc[TK, 2021].mean() - W.loc[CHIHO, 2021].mean(), 1)

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps(M, ensure_ascii=False, indent=1))
