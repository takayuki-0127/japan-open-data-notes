"""03b 問い直し：円安の半期に円建ての割合が下がるのは、契約の変化か、計算の上の効果か。
外貨建ての契約の円換算額はドル円とともに膨らむので、契約が同じでも円の割合は下がる。
その「計算の上の効果」＝ −s(1−s)×Δlog(ドル円)（s は前の半期の円の割合）を求め、実際の変化への回帰の傾きと比べる。
出力：results/requestion.json
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"


def main():
    t = pd.read_csv(R / "jpy_share.csv").set_index("half")
    s = t.WORLD / 100
    dlfx = np.log(t.usdjpy).diff()
    actual = s.diff() * 100
    mech = -(s.shift(1) * (1 - s.shift(1))) * dlfx * 100
    ok = actual.notna() & mech.notna()
    b_act = float(np.polyfit(dlfx[ok], actual[ok], 1)[0])       # 円の割合（ポイント）／ Δlog ドル円
    b_mech = float(np.polyfit(dlfx[ok], mech[ok], 1)[0])
    resid = actual - mech
    out = dict(slope_actual=b_act, slope_mechanical=b_mech, mech_share_of_slope=b_act and b_mech / b_act * 100,
               corr_resid_dfx=float(np.corrcoef(resid[ok], dlfx[ok])[0, 1]),
               mech_total_first_last=float(mech[ok].sum()), actual_total_first_last=float(actual[ok].sum()),
               resid_total=float(resid[ok].sum()))
    json.dump({k: round(v, 4) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
