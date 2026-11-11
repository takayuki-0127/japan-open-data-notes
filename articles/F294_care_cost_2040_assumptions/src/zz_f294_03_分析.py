"""F294 分析: 2040年度の介護費用額を、前提を変えて計算する（予測ではなく、前提の置き換え計算）。
費用2040 = 費用2025 × [Σ 受給者2025(a,s) × 人口比(a,s) × 受給率変化(a,s) × 重み(a)] / Σ 受給者2025×重み × (1+g)^15
"""
import json, math, pathlib
import numpy as np, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R = ROOT / "data" / "processed", ROOT / "results"
R.mkdir(exist_ok=True)
users = pd.read_csv(P / "users_rate_65plus.csv")
pop = pd.read_csv(P / "ipss_pop_65plus.csv")
cost = pd.read_csv(P / "cost_total.csv").set_index("fy").cost_million_yen / 1e6  # 兆円
cpu = pd.read_csv(P / "cost_per_user.csv").set_index("year_of_review").cost_per_user_k_yen_april
AGES = ["65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95+"]
YRS = 15
C25 = cost[2025]

u = users.pivot_table(index=["sex", "age"], columns="fy", values="users_k")
r = users.pivot_table(index=["sex", "age"], columns="fy", values="rate_pct")

def popratio(variant, y1=2040, y0=2025, combine=False):
    d = pop[pop.variant == variant].pivot_table(index=["sex", "age"], columns="year", values="pop_k")
    if combine:
        s = d.groupby(level="age").sum()
        return s[y1] / s[y0]
    return d[y1] / d[y0]

def rate_mult(kind):
    if kind == "一定":
        return pd.Series(1.0, index=r.index)
    if kind == "2014→25の傾向":
        g = np.log(r[2025] / r[2014]) / 11
    elif kind == "2019→25の傾向":
        g = np.log(r[2025] / r[2019]) / 6
    elif kind == "傾向の半分":
        g = np.log(r[2025] / r[2014]) / 11 / 2
    elif kind == "2019年の水準に戻る":
        return r[2019] / r[2025]
    return np.exp(g * YRS)

def weight(kind):
    w = pd.Series(1.0, index=r.index)
    if kind == "85歳以上1.2倍":
        w[[i for i in r.index if i[1] in ("85-89", "90-94", "95+")]] = 1.2
    return w

def users_index(variant="中位", rate="一定", w="なし", combine=False):
    if combine:
        uu = u[2025].groupby(level="age").sum()
        rr = rate_mult(rate)
        # 受給率の変化は男女の受給者で重み付けして合成
        rr = (u[2025] * rr).groupby(level="age").sum() / uu
        return float((uu * popratio(variant, combine=True) * rr).sum() / uu.sum())
    ww = weight(w)
    return float((u[2025] * popratio(variant) * rate_mult(rate) * ww).sum() / (u[2025] * ww).sum())

rows = []
for variant in ["中位", "死亡高位", "死亡低位"]:
    for rate in ["一定", "2014→25の傾向", "2019→25の傾向", "傾向の半分"]:
        ui = users_index(variant, rate)
        for g in [0.0, 0.01, 0.02]:
            rows.append({"死亡仮定": variant, "受給率": rate, "1人当たり費用の伸び": g,
                         "受給者指数": ui, "費用2040_兆円": C25 * ui * (1 + g) ** YRS,
                         "2025比": ui * (1 + g) ** YRS})
sc = pd.DataFrame(rows)
sc.to_csv(R / "scenarios.csv", index=False, float_format="%.4f")

# 人口だけ（受給率一定・単価一定・中位）
H1 = users_index()
# 年次の受給者指数（中位・受給率一定）
d = pop[pop.variant == "中位"].pivot_table(index=["sex", "age"], columns="year", values="pop_k")
path = {int(y): float((u[2025] * d[y] / d[2025]).sum() / u[2025].sum()) for y in d.columns if 2025 <= y <= 2070}
pd.Series(path, name="受給者指数_中位_受給率一定").to_csv(R / "users_index_path.csv")

# バックテスト：FY2014→2025 の費用の伸びを分解（対数）
imp = users.pivot_table(index=["sex", "age"], columns="fy", values="implied_pop_k")
def decomp(y0, y1):
    demo = float((u[y0] * imp[y1] / imp[y0]).sum() / u[y0].sum())
    usr = float(u[y1].sum() / u[y0].sum())
    rate_eff = usr / demo
    cr = float(cost[y1] / cost[y0])
    per = cr / usr
    tot = math.log(cr)
    return {"期間": f"{y0}→{y1}", "費用の倍率": cr, "人口構成(受給率一定)": demo,
            "受給率の変化": rate_eff, "受給者1人当たり": per,
            "人口の寄与割合": math.log(demo) / tot, "受給率の寄与割合": math.log(rate_eff) / tot,
            "1人当たりの寄与割合": math.log(per) / tot,
            "年率_費用": cr ** (1 / (y1 - y0)) - 1, "年率_1人当たり": per ** (1 / (y1 - y0)) - 1}
bt = pd.DataFrame([decomp(2014, 2025), decomp(2014, 2019), decomp(2019, 2025)])
bt.to_csv(R / "backtest_decomposition.csv", index=False, float_format="%.4f")

# R5: 年間実受給者数（40〜64歳を含む、全年齢）で1人当たりを測り直す
au = pd.read_csv(P / "annual_users.csv").set_index("fy").annual_users_k
R5 = {"年間実受給者の倍率2014→25": float(au[2025] / au[2014]),
      "1人当たり(年間実受給者ベース)年率": float((cost[2025] / cost[2014] / (au[2025] / au[2014])) ** (1 / 11) - 1),
      "1人当たり費用額(4月審査分)年率2014→25": float((cpu[2025] / cpu[2014]) ** (1 / 11) - 1),
      "1人当たり費用額(4月審査分)年率2019→25": float((cpu[2025] / cpu[2019]) ** (1 / 6) - 1),
      "1人当たり費用額(4月審査分)年率2014→25_2017→18の段差を除く": float((cpu[2025] / cpu[2014] / (cpu[2018] / cpu[2017])) ** (1 / 10) - 1),
      "2017→18の段差": float(cpu[2018] / cpu[2017] - 1)}

# 政府見通し（2018年5月「2040年を見据えた社会保障の将来見通し（議論の素材）」、経済ベースラインケース、介護給付費）
gov = {"計画ベース": {"2018": 10.7, "2025": 15.3, "2040": 25.8},
       "現状投影": {"2018": 10.7, "2025": 14.6, "2040": 24.6}}
govcmp = {}
for k, v in gov.items():
    ratio = v["2040"] / v["2025"]
    need = (ratio / H1) ** (1 / YRS) - 1  # 受給率一定・中位で、この倍率に合わせるのに要る1人当たりの年率
    govcmp[k] = {"2025→2040倍率": ratio, "年率": ratio ** (1 / 15) - 1,
                 "2018→2025年率": (v["2025"] / v["2018"]) ** (1 / 7) - 1,
                 "受給率一定・中位で合わせるのに要る1人当たり年率": need}
# 実績の 2019→2025 年率（費用額累計）
act_19_25 = float((cost[2025] / cost[2019]) ** (1 / 6) - 1)

rob = {
    "R1_受給率を2019年水準に": users_index(rate="2019年の水準に戻る"),
    "R2_男女合算": users_index(combine=True),
    "R3_85歳以上1.2倍": users_index(w="85歳以上1.2倍"),
    "R4_傾向の半分": users_index(rate="傾向の半分"),
}
s0 = sc[sc["1人当たり費用の伸び"] == 0]
H = {
    "H1_人口だけの受給者指数": H1, "H1_成立(>=1.20)": H1 >= 1.20,
    "H2_人口の寄与割合2014→25": bt.iloc[0]["人口の寄与割合"], "H2_成立(>=0.5)": bt.iloc[0]["人口の寄与割合"] >= 0.5,
    "H3_最大/最小": float(sc["費用2040_兆円"].max() / sc["費用2040_兆円"].min()), 
    "H4_死亡高位(受給率一定)": users_index("死亡高位") / H1 - 1, "H4_死亡低位(受給率一定)": users_index("死亡低位") / H1 - 1,
    "H5_政府現状投影倍率": govcmp["現状投影"]["2025→2040倍率"], "H5_人口+年1%の倍率": H1 * 1.01 ** 15,
}
H["H3_成立(>=1.5)"] = H["H3_最大/最小"] >= 1.5
H["H4_成立(±5%以内)"] = max(abs(H["H4_死亡高位(受給率一定)"]), abs(H["H4_死亡低位(受給率一定)"])) <= 0.05
H["H5_成立(政府の方が高い)"] = H["H5_政府現状投影倍率"] > H["H5_人口+年1%の倍率"]
# 年齢別：受給率の変化（2014→2025、2019→2025）
rr = pd.DataFrame({"2014": r[2014], "2019": r[2019], "2025": r[2025],
                   "年率2014→25": np.exp(np.log(r[2025] / r[2014]) / 11) - 1,
                   "年率2019→25": np.exp(np.log(r[2025] / r[2019]) / 6) - 1,
                   "人口比2040/2025_中位": popratio("中位")}).reset_index()
rr.to_csv(R / "rates_by_age.csv", index=False, float_format="%.4f")
out = {"費用2025_兆円": C25, "仮説": H, "頑健性_受給者指数": rob, "R5": R5, "政府見通しとの比較": govcmp,
       "実績2019→25年率_費用額": act_19_25, "バックテスト": bt.to_dict(orient="records"),
       "シナリオ幅_兆円": [float(sc["費用2040_兆円"].min()), float(sc["費用2040_兆円"].max())],
       "受給者65歳以上_2025_千人": float(u[2025].sum())}
(R / "summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
print(sc[sc["死亡仮定"] == "中位"].to_string())
print(rr.to_string())
