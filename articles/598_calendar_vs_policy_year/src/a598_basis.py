"""598 年の途中で売る1年契約で、事故を暦年で数えるか契約年度で数えるかで、事故率の推移はどれだけ違って見えるか（seed 598）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(598)
SRC = "架空のデータ（作成者が乱数で作成、seed 598）"
Y0, NC = 2017, 120                      # 契約の始まりは 2017年1月〜2026年12月の120か月（表は2019年から）
NM = NC + 12 + 24                       # 事故・報告の月は 2028年12月まで追う
BASE, HIGH = 0.05, 0.06                 # 本当の事故率（1契約・1年あたり）5% → 6%（+20%）
SEASON = np.array([0.6, 0.8, 2.2, 3.0, 1.0, 0.7, 0.7, 0.6, 0.8, 0.9, 0.8, 0.9])   # 3〜4月に多く売れる
SEASON = SEASON / SEASON.mean()
Q = 0.6                                 # 報告の遅れ：P(遅れ k か月) = (1 − Q) Q^k、平均1.5か月
CHG_CAL, CHG_POL = 6 * 12 + 6, 6 * 12 + 3   # A：2023年7月の事故から 6%／B：2023年4月に始まる契約から 6%
YEARS = list(range(2019, 2026))
BASES = {"accident": "事故年（起きた年）", "policy": "契約年度（契約が始まった年）", "report": "報告年（報告された年）"}


def ym(m):
    return f"{Y0 + m // 12}-{m % 12 + 1:02d}"


def policies():
    m = np.arange(NC)
    return np.round(8000 * SEASON[m % 12] * 1.03 ** (m / 12)).astype(int)


def simulate(pol, scen):
    """契約の始まりの月 c・事故の月 a・報告の月 r ごとの事故件数（a は c〜c+11）"""
    out = np.zeros((NC, NM, NM), dtype=np.int32)
    for c in range(NC):
        for a in range(c, c + 12):
            rate = (HIGH if a >= CHG_CAL else BASE) if scen == "A" else (HIGH if c >= CHG_POL else BASE)
            n = rng.poisson(pol[c] / 12 * rate)
            if n:
                lag = rng.geometric(1 - Q, n) - 1
                lag = lag[a + lag < NM]
                np.add.at(out[c, a], a + lag, 1)
    return out


def expected(pol, scen):
    """偶然の揺れを除いた期待値の件数（報告の遅れも確率どおりに割り振る）"""
    out = np.zeros((NC, NM, NM))
    k = np.arange(NM); pk = (1 - Q) * Q ** k
    for c in range(NC):
        for a in range(c, c + 12):
            rate = (HIGH if a >= CHG_CAL else BASE) if scen == "A" else (HIGH if c >= CHG_POL else BASE)
            out[c, a, a:] = pol[c] / 12 * rate * pk[:NM - a]
    return out


def exposure_by_month(pol):
    e = np.zeros(NM)
    for c in range(NC):
        e[c:c + 12] += pol[c] / 12
    return e


def annual(cube, pol):
    e = exposure_by_month(pol); res = {}
    for y in YEARS:
        ms = range((y - Y0) * 12, (y - Y0) * 12 + 12)
        res[y] = {"accident": cube[:, list(ms), :].sum() / e[list(ms)].sum(),
                  "policy": cube[list(ms)].sum() / pol[list(ms)].sum(),
                  "report": cube[:, :, list(ms)].sum() / e[list(ms)].sum()}
    return pd.DataFrame(res).T


def known_at(cube, pol, t):
    """月末 t の時点で分かっていること（報告が t までのもの）で計算した、直近12か月の3つの事故率"""
    e = exposure_by_month(pol); w = range(t - 11, t + 1)
    rep = cube[:, :, :t + 1]
    acc = rep[:, list(w), :].sum() / e[list(w)].sum()
    rpt = cube[:, :, list(w)].sum() / e[list(w)].sum()
    cs = [c for c in range(t - 23, t - 11) if c >= 0]                # 期間が終わった直近12か月分の契約
    pyr = rep[cs].sum() / pol[cs].sum() if cs else np.nan
    return acc, pyr, rpt


pol = policies()
true_ann = {"A": {y: (BASE if y < 2023 else (BASE * 0.5 + HIGH * 0.5 if y == 2023 else HIGH)) for y in YEARS}}

# 1回の例（A・B）で年の表をつくる
rows, roll = [], []
cubes = {}
for scen in ["A", "B"]:
    cube = simulate(pol, scen); cubes[scen] = cube
    an = annual(cube, pol)
    for y, r in an.iterrows():
        rows.append({"scenario": scen, "year": y, **{k: r[k] for k in BASES}})
    for t in range(36, NC):
        acc, pyr, rpt = known_at(cube, pol, t)
        roll.append({"scenario": scen, "month": ym(t), "t": t, "accident": acc, "policy": pyr, "report": rpt})
ann = pd.DataFrame(rows); ann.round(6).to_csv(RES / "annual_rates.csv", index=False)
exp_rows = []
for scen in ["A", "B"]:
    an = annual(expected(pol, scen), pol)
    for y, r in an.iterrows():
        exp_rows.append({"scenario": scen, "year": y, **{k: r[k] for k in BASES}})
annx = pd.DataFrame(exp_rows); annx.round(6).to_csv(RES / "annual_rates_expected.csv", index=False)
roll = pd.DataFrame(roll); roll.round(6).to_csv(RES / "known_at_month_end.csv", index=False)


def detect(rl, chg):
    """変化前（2021年1月〜2022年12月の月末）の平均の1.1倍を、変化の後に初めて超えた月末までの月数"""
    out = {}
    for k in BASES:
        pre = rl[(rl.t >= 48) & (rl.t < 72)][k].mean()
        post = rl[(rl.t >= chg) & (rl[k] >= 1.1 * pre)]
        out[k] = int(post.t.iloc[0] - chg) if len(post) else np.nan
    return out


# 遅れの分布：各200回
det = []
for scen, chg in [("A", CHG_CAL), ("B", CHG_POL)]:
    for r in range(200):
        cube = simulate(pol, scen)
        rl = pd.DataFrame([dict(zip(["accident", "policy", "report"], known_at(cube, pol, t)), t=t) for t in range(36, NC)])
        det.append({"scenario": scen, "rep": r, **detect(rl, chg)})
det = pd.DataFrame(det); det.to_csv(RES / "detection_delay.csv", index=False)
dsum = det.groupby("scenario")[list(BASES)].median().reset_index(); dsum.to_csv(RES / "detection_summary.csv", index=False)

# データ（シナリオ A の1回）を書き出し、SQL で年の表を作り直して突き合わせ
cube = cubes["A"]; c_, a_, r_ = np.nonzero(cube)
claims = pd.DataFrame({"start_month": [ym(x) for x in c_], "accident_month": [ym(x) for x in a_],
                       "report_month": [ym(x) for x in r_], "claims": cube[c_, a_, r_]})
claims.to_csv(DATA / "claims.csv", index=False)
pols = pd.DataFrame({"start_month": [ym(x) for x in range(NC)], "policies": pol}); pols.to_csv(DATA / "policies.csv", index=False)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("claims", claims); con.register("policies", pols)
sq = con.execute(open(SQL / "02_basis_duckdb.sql").read()).df().set_index("year")
a_py = ann[ann.scenario == "A"].set_index("year")
mx = max(float((sq[k] - a_py[k]).abs().max()) for k in BASES)
pd.DataFrame([{"max_abs_diff": mx, "match": mx < 1e-12}]).to_csv(RES / "sql_check.csv", index=False)

# 図1 年の表（A と B）
fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
for ax, scen, ttl in zip(axs, ["A", "B"], ["A：2023年7月から、すべての契約で事故が起きやすくなった", "B：2023年4月以降に始まった契約だけ、事故が起きやすい"]):
    s = annx[annx.scenario == scen]
    for k, col, mk in zip(BASES, [BLUE, ORANGE, GREEN], ["o", "s", "^"]):
        ax.plot(s.year, s[k] * 100, marker=mk, color=col, label=BASES[k])
        for xv, yv in zip(s.year, s[k] * 100):
            if xv in (2022, 2023, 2024): ax.text(xv + 0.08, yv, f"{yv:.2f}", fontsize=7.5, color=col, va="center")
    ax.axhline(5, color=GRAY, lw=0.8, ls=":"); ax.axhline(6, color=GRAY, lw=0.8, ls=":")
    ax.set_title(ttl, fontsize=10); ax.set_xticks(YEARS); ax.grid(alpha=0.3); ax.set_xlabel("年")
axs[0].set_ylabel("事故率（1契約・1年あたり、%）"); axs[0].legend(fontsize=9, loc="upper left")
fig.suptitle("同じデータでも、どの年に数えるかで「いつ上がったか」が違って見える（本当の事故率は5% → 6%）", fontsize=12, y=1.02)
save(fig, "a598_annual.png", "出典：" + SRC + "。偶然の揺れを除いた期待値。報告が出そろった時点の値")

# 図2 その時点で分かる直近12か月の値（A）
fig, ax = plt.subplots(figsize=(10, 4.6))
s = roll[roll.scenario == "A"]
for k, col in zip(BASES, [BLUE, ORANGE, GREEN]):
    ax.plot(s.t, s[k] * 100, color=col, label=BASES[k], lw=1.5)
ax.axvline(CHG_CAL, color=INK, lw=0.8, ls="--"); ax.text(CHG_CAL + 0.8, 4.45, "2023年7月：\n本当の事故率が6%に", fontsize=8.5)
tick = list(range(36, NC, 12)); ax.set_xticks(tick); ax.set_xticklabels([ym(t) for t in tick])
ax.set_ylabel("直近12か月の事故率（%）"); ax.set_xlabel("月末（その時点までに報告された事故で計算）"); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="upper left")
ax.set_title("その月末に分かる値：契約年度は遅れて動き、事故年は直近の未報告の分だけ低い")
save(fig, "a598_known_at.png", "出典：" + SRC + "。シナリオ A の1回。契約年度は、期間が終わった直近12か月分の契約で計算")

# 図3 気づくまでの月数（中央値、各200回）
fig, ax = plt.subplots(figsize=(9.5, 4.4)); xx = np.arange(2)
for j, (k, col) in enumerate(zip(BASES, [BLUE, ORANGE, GREEN])):
    v = [dsum.set_index("scenario").loc[sc, k] for sc in ["A", "B"]]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=col, label=BASES[k])
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 0.3, f"{vv:.0f}", ha="center", fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels(["A：時期で変わった（2023年7月から）", "B：契約で変わった（2023年4月の契約から）"])
ax.set_ylabel("変化から気づくまでの月数（中央値）"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9)
ax.set_title("直近12か月の値が、変化前の1.1倍を初めて超えるまでの月数（各200回）")
save(fig, "a598_delay.png", "出典：" + SRC + "。変化前 = 2021年1月〜2022年12月の月末の平均")

json.dump({"annual": ann.round(6).to_dict("records"), "annual_expected": annx.round(6).to_dict("records"), "detection_median": dsum.to_dict("records"),
           "detection_mean": det.groupby("scenario")[list(BASES)].mean().round(2).reset_index().to_dict("records"),
           "sql": pd.read_csv(RES / "sql_check.csv").to_dict("records"), "policies_per_year": {str(y): int(pol[(y - Y0) * 12:(y - Y0) * 12 + 12].sum()) for y in YEARS}},
          open(RES / "a598_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); print(ann.round(4).to_string()); print(annx.round(4).to_string()); print(dsum); print(det.groupby("scenario")[list(BASES)].describe().T.round(1).to_string()); print(mx)
