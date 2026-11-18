"""分解の関数と定数（03_analysis.py と 03b_requestion.py から使う）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
W = pd.read_csv(ROOT / "data" / "wood_national.csv").set_index("year")
DCOLS = ["dom_seizai", "dom_gouhan", "dom_pulp", "dom_sonota", "dom_shiitake", "dom_nenryo"]
MCOLS = ["imp_seizai", "imp_gouhan", "imp_pulp", "imp_sonota", "imp_nenryo"]
LAB = {"seizai": "製材用", "gouhan": "合板用", "pulp": "パルプ・チップ用", "sonota": "その他用", "shiitake": "しいたけ原木", "nenryo": "燃料材"}
STEPS = 20000


def ss(d, m):
    return 100 * d.sum() / (d.sum() + m.sum())


def decomp(d0, m0, d1, m1):
    """すべての成分を同時にまっすぐ動かす経路で ds を積分（中点法）。戻り値：各成分の寄与（ポイント）"""
    dd, dm = d1 - d0, m1 - m0
    cd, cm = np.zeros_like(d0), np.zeros_like(m0)
    for t in (np.arange(STEPS) + 0.5) / STEPS:
        D = (d0 + t * dd).sum(); M = (m0 + t * dm).sum(); T = D + M
        cd += M / T**2 * dd / STEPS; cm += -D / T**2 * dm / STEPS
    return 100 * cd, 100 * cm


def vec(y0, y1=None, cols=None):
    sel = W.loc[y0:y1 if y1 else y0, cols].mean() if y1 else W.loc[y0, cols]
    return sel.to_numpy(float)


def run(a, b, dcols=DCOLS, mcols=MCOLS, avg=0):
    """a→b の分解。avg>0 なら前後 avg 年の平均（端は表の範囲で切る）"""
    def get(y, cols):
        lo, hi = max(y - avg, W.index.min()), min(y + avg, W.index.max())
        return W.loc[lo:hi, cols].mean().to_numpy(float)
    d0, m0, d1, m1 = get(a, dcols), get(a, mcols), get(b, dcols), get(b, mcols)
    cd, cm = decomp(d0, m0, d1, m1)
    s0, s1 = ss(d0, m0), ss(d1, m1)
    out = {"from": a, "to": b, "ss_from": s0, "ss_to": s1, "change": s1 - s0,
           "dom_contrib": float(cd.sum()), "imp_contrib": float(cm.sum()),
           "resid": float(s1 - s0 - cd.sum() - cm.sum())}
    for c, v in zip(dcols, cd): out[c] = float(v)
    for c, v in zip(mcols, cm): out[c] = float(v)
    # 2要因のシャープレイ値（国内生産の合計・輸入の合計）
    D0, D1, M0, M1 = d0.sum(), d1.sum(), m0.sum(), m1.sum()
    f = lambda D, M: 100 * D / (D + M)
    out["shapley_dom"] = 0.5 * ((f(D1, M0) - f(D0, M0)) + (f(D1, M1) - f(D0, M1)))
    out["shapley_imp"] = 0.5 * ((f(D0, M1) - f(D0, M0)) + (f(D1, M1) - f(D1, M0)))
    out.update({"D_from": D0, "D_to": D1, "M_from": M0, "M_to": M1})
    return out


