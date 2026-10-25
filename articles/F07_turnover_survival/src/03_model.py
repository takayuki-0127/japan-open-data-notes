"""離散時間ハザードモデル（集計値の二項ロジット）。景気は「就職した年」と「その年」の2つを入れる。
標準誤差は卒業年でクラスター（30クラスター）。"""
import json
import statsmodels.api as sm
import statsmodels.formula.api as smf
from common import *

hz = pd.read_csv(RES / "hazard_by_education.csv")
hz["ljr_entry"] = np.log(hz.jr_entry)
hz["ljr_cur"] = np.log(hz.jr_cur)
hz["later"] = (hz.k >= 2).astype(int)
hz["trend"] = (hz.grad_year - 2010) / 10
hz["edk"] = hz.education + "_" + hz.k.astype(str)

def fit(d, rhs, name):
    d = d.dropna(subset=[c for c in ["ljr_entry", "ljr_cur", "ue_entry", "ue_cur"] if c in rhs])
    y = np.column_stack([d.events, d.at_risk - d.events])
    X = smf.glm(f"events ~ {rhs}", d).data.frame if False else None
    mod = smf.glm(f"np.column_stack([events, at_risk - events]) ~ {rhs}", d, family=sm.families.Binomial())
    r = mod.fit(cov_type="cluster", cov_kwds={"groups": d.grad_year.values})
    out = []
    for v in r.params.index:
        if v.startswith(("ljr", "ue_", "trend", "later:")):
            out.append(dict(model=name, term=v, coef=r.params[v], se=r.bse[v],
                            lo=r.conf_int().loc[v, 0], hi=r.conf_int().loc[v, 1], p=r.pvalues[v], n=len(d)))
    return r, out

res = []
# 基本：学歴×経過年数の固定効果 ＋ 就職年の求人倍率 ＋ その年の求人倍率 ＋ 直線のトレンド
base_rhs = "C(edk) + ljr_entry + ljr_cur + trend"
r0, o = fit(hz, base_rhs, "基本（全学歴）"); res += o
# 就職年の景気が2・3年目に残るか（傷跡）：就職年の求人倍率 × 2年目以降
r1, o = fit(hz, "C(edk) + ljr_entry + ljr_entry:later + ljr_cur + trend", "傷跡（2・3年目との交差項）"); res += o
# 頑健性
for ed in EDU:
    _, o = fit(hz[hz.education == ed], "C(k) + ljr_entry + ljr_cur + trend", f"{ed}だけ"); res += o
_, o = fit(hz, "C(edk) + ue_entry + ue_cur + trend", "失業率に入れ替え"); res += o
_, o = fit(hz[~hz.grad_year.between(2009, 2012)], base_rhs, "2009〜2012年卒を除く"); res += o
_, o = fit(hz[~hz.cal_year.between(2020, 2021)], base_rhs, "2020・2021年の離職を除く"); res += o
_, o = fit(hz, "C(edk) + ljr_entry + ljr_cur", "トレンドなし"); res += o
_, o = fit(hz[hz.education.isin(["高校", "大学"])], base_rhs, "高校と大学だけ"); res += o
R = pd.DataFrame(res)
R.to_csv(RES / "hazard_model_coefs.csv", index=False)

# 分かりやすい形：求人倍率が 0.5倍 → 1.5倍 のとき、大学1年目・2年目のハザードは何ポイント変わるか（基本モデル）
def pred(r, ed, k, je, jc, year=2010):
    d = pd.DataFrame(dict(edk=[f"{ed}_{k}"], ljr_entry=[np.log(je)], ljr_cur=[np.log(jc)], trend=[(year - 2010) / 10],
                          later=[int(k >= 2)], events=[0], at_risk=[1]))
    return float(r.predict(d).iloc[0])
eff = {}
for ed in ["高校", "大学"]:
    for k in (1, 2, 3):
        eff[f"{ed}_{k}年目_その年の求人倍率0.5→1.5"] = round((pred(r0, ed, k, 1.0, 1.5) - pred(r0, ed, k, 1.0, 0.5)) * 100, 2)
        eff[f"{ed}_{k}年目_就職年の求人倍率0.5→1.5"] = round((pred(r0, ed, k, 1.5, 1.0) - pred(r0, ed, k, 0.5, 1.0)) * 100, 2)
        eff[f"{ed}_{k}年目_基準(1.0,1.0)"] = round(pred(r0, ed, k, 1.0, 1.0) * 100, 2)
# 3年以内の離職率に直すと
for ed in ["高校", "大学"]:
    for lab, je, jc in [("就職年0.5・その後1.0", 0.5, 1.0), ("就職年1.5・その後1.0", 1.5, 1.0),
                        ("就職年1.0・その後0.5", 1.0, 0.5), ("就職年1.0・その後1.5", 1.0, 1.5)]:
        S = 1
        for k in (1, 2, 3): S *= 1 - pred(r0, ed, k, je, jc)
        eff[f"{ed}_3年以内_{lab}"] = round((1 - S) * 100, 1)
# 当てはまり：予測と実際の相関（ハザード）
hz2 = hz.dropna(subset=["ljr_entry", "ljr_cur"]).copy()
hz2["pred"] = r0.predict(hz2)
eff["予測と実際のハザードの相関"] = round(float(np.corrcoef(hz2.pred, hz2.hazard)[0, 1]), 3)
eff["就職年とその年の求人倍率の相関（全行）"] = round(float(np.corrcoef(hz2.ljr_entry, hz2.ljr_cur)[0, 1]), 3)
eff["就職年とその年の求人倍率の相関（2・3年目）"] = round(float(np.corrcoef(hz2[hz2.k > 1].ljr_entry, hz2[hz2.k > 1].ljr_cur)[0, 1]), 3)
hz2.to_csv(RES / "hazard_fitted.csv", index=False)
json.dump(eff, open(RES / "effects.json", "w"), ensure_ascii=False, indent=1)
print(R.round(4).to_string())
print(json.dumps(eff, ensure_ascii=False, indent=1))

# 傷跡モデル：2・3年目での就職年の効果（主効果＋交差項）とその幅
b = r1.params; V = r1.cov_params()
c = b["ljr_entry"] + b["ljr_entry:later"]
se = float(np.sqrt(V.loc["ljr_entry", "ljr_entry"] + V.loc["ljr_entry:later", "ljr_entry:later"] + 2 * V.loc["ljr_entry", "ljr_entry:later"]))
eff["傷跡モデル_就職年の効果_1年目"] = [round(b["ljr_entry"], 3), round(b["ljr_entry"] - 1.96 * r1.bse["ljr_entry"], 3), round(b["ljr_entry"] + 1.96 * r1.bse["ljr_entry"], 3)]
eff["傷跡モデル_就職年の効果_2・3年目"] = [round(c, 3), round(c - 1.96 * se, 3), round(c + 1.96 * se, 3)]
json.dump(eff, open(RES / "effects.json", "w"), ensure_ascii=False, indent=1)
print(eff["傷跡モデル_就職年の効果_1年目"], eff["傷跡モデル_就職年の効果_2・3年目"])
