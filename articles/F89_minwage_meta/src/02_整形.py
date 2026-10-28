"""各記事の推定値を、同じ単位にそろえた表を作る。
主な単位：雇用の弾力性（最低賃金が1%上がると、就業者・従業者が何%変わるか）。
失業率は「最低賃金10%あたり、何%ポイント変わるか」。"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import RAW, DATA

p = pd.read_csv(RAW / "F01_panel.csv")
base = p[(p.year >= 2008) & (p.year <= 2019)]
E1 = base.emp_rate.mean()                      # 就業率の平均（2008〜19年）
E2 = p[p.year != 0].emp_rate.mean()            # 2008〜25年
BITE = p[p.year == 2015].bite.mean()           # 最低賃金 ÷ 平均時給（2015年）
UNIT17 = 1 / BITE                              # F17 の処置1単位 ＝ 最低賃金の何%か
print(f"就業率の平均 2008-19 {E1:.2f}%  2008-25 {E2:.2f}%  bite {BITE:.3f}  F17の1単位=最低賃金の{UNIT17:.3f}%")

rows = []
def add(study, spec, outcome, est, se, unit_note, main=False, sample="", design=""):
    rows.append(dict(study=study, spec=spec, outcome=outcome, est=est, se=se,
                     lo=est - 1.96 * se, hi=est + 1.96 * se, main=main,
                     unit_note=unit_note, sample=sample, design=design))

# ---------- F01：県×年の二方向固定効果（log 最低賃金の係数、就業率 %pt）----------
tw = pd.read_csv(RAW / "F01_twfe.csv")
for _, r in tw.iterrows():
    E = E1 if "2019" in r.spec else E2
    if r.outcome == "emp_rate":
        add("F01", r.spec, "emp", r.beta_logmw / E, r.se / E,
            "係数（%pt／log最低賃金）÷ 就業率の平均", main=(r.spec == "基本（2008–2019）"),
            sample="47都道府県×年", design="二方向固定効果")
    elif r.outcome == "unemp_rate":
        add("F01", r.spec, "unemp", r.beta_logmw * 0.1, r.se * 0.1,
            "係数 × 0.1（最低賃金10%あたり）", main=(r.spec == "基本（2008–2019）"),
            sample="47都道府県×年", design="二方向固定効果")

# F01 のデータで、就業者数（log）を直接 log 最低賃金に回帰した弾力性も足す（記事にはなかった版）。
# 人口の増減を除くため、15歳以上人口（log）を入れる。
base = base.assign(lpop=np.log(base.pop15))
m = smf.ols("log_emp ~ log_mw + lpop + C(code) + C(year)", data=base).fit(
    cov_type="cluster", cov_kwds={"groups": base["code"]})
add("F01", "就業者数（log）を直接・人口を調整（2008–2019）", "emp", m.params["log_mw"], m.bse["log_mw"],
    "log 就業者数の係数（そのまま弾力性）", sample="47都道府県×年", design="二方向固定効果")

# ---------- F15：県境のペア比較（弾力性そのもの）----------
f15 = json.load(open(RAW / "F15_estimates.json"))
lab15 = {"main_total": "全産業", "main_foodretail": "飲食＋小売", "main_food": "宿泊・飲食",
         "main_retail": "卸売・小売"}
for k, lab in lab15.items():
    v = f15["main"][k]
    add("F15", lab, "emp", v["beta"], v["se"], "弾力性（2016→21年、ペアの差）",
        main=(k == "main_total"), sample="県境で接する724組", design="境界のペア比較")
for k in ["中心が20km以内のペアも入れる", "人口で重みづけ"]:
    v = f15["robust"][k]
    add("F15", "飲食＋小売・" + k, "emp", v["beta"], (v["hi"] - v["lo"]) / 3.92,
        "弾力性（区間から標準誤差を逆算）", sample="県境のペア", design="境界のペア比較")

# ---------- F17：因果フォレスト（処置1単位＝平均時給の1%分、就業率の前年差 %pt）----------
f17 = json.load(open(RAW / "F17_main.json"))
def conv17(est, lo, hi):
    se = (hi - lo) / 3.92
    return est / UNIT17 / E1 * 100, se / UNIT17 / E1 * 100
e, s = conv17(f17["ate"], f17["ate_lo"], f17["ate_hi"])
add("F17", "因果フォレストの平均効果（2010–25年）", "emp", e, s,
    "効果 ÷ (1/bite) ÷ 就業率の平均 ×100", main=True, sample="47都道府県×年", design="因果フォレスト（前年差）")
e, s = conv17(f17["linear_dml"], *f17["linear_dml_ci"])
add("F17", "LinearDML", "emp", e, s, "同上", sample="47都道府県×年", design="ダブル機械学習（前年差）")
e, s = conv17(f17["ols_fd"], *f17["ols_fd_ci"])
add("F17", "前年差の単純な回帰", "emp", e, s, "同上", sample="47都道府県×年", design="前年差の回帰")
rb = pd.read_csv(RAW / "F17_robustness.csv")
for lab in ["2010〜19年だけ（コロナ前）", "2016〜25年（2020〜22年を除く）"]:
    r = rb[rb["設定"] == lab].iloc[0]
    e, s = conv17(r["平均効果"], r["下限"], r["上限"])
    add("F17", "平均効果・" + lab, "emp", e, s, "同上", sample="47都道府県×年", design="因果フォレスト（前年差）")
r = rb[rb["設定"] == "結果を完全失業率の前年差にする"].iloc[0]
se = (r["上限"] - r["下限"]) / 3.92
add("F17", "因果フォレストの平均効果（失業率）", "unemp", r["平均効果"] * 10 / UNIT17, se * 10 / UNIT17,
    "効果 × 10 ÷ (1/bite)（最低賃金10%あたり）", main=True, sample="47都道府県×年", design="因果フォレスト（前年差）")

est = pd.DataFrame(rows)
est.to_csv(DATA / "estimates_common_unit.csv", index=False, encoding="utf-8-sig")

# F26 の「見つけられる最小の効果」（80%の検出力）を同じ単位にそろえる
pf = pd.read_csv(RAW / "F26_past_flagships.csv")
mde = []
for _, r in pf.iterrows():
    if r.key.startswith("F01 就業率"):
        # F26 の MDE は「bite 高低×2016年以降」の差の差の単位（%pt）なので、そのままは換算できない。参考として記録だけ。
        mde.append(dict(key=r.key, mde80_native=r.mde80, unit=r.unit, note="差の差の単位（換算しない）"))
    else:
        mde.append(dict(key=r.key, mde80_native=r.mde80, unit=r.unit, note=""))
pd.DataFrame(mde).to_csv(DATA / "f26_mde.csv", index=False, encoding="utf-8-sig")

json.dump(dict(emp_rate_mean_2008_19=E1, emp_rate_mean_2008_25=E2, bite_2015=BITE, f17_unit_pct_of_mw=UNIT17),
          open(DATA / "constants.json", "w"), ensure_ascii=False, indent=1)
print(est[["study", "spec", "outcome", "est", "se", "main"]].round(4).to_string())
