"""頑健性：較正用の割合・学習データの量・年をまたいだ場合（分割・正規化コンフォーマルのみ）
結果：results/coverage_robust.csv"""
import numpy as np, pandas as pd, time
from common import load, FEAT, SEED, RES
import importlib
cc = importlib.import_module("01_conformal_cv")

if __name__ == "__main__":
    d = load(); t0 = time.time(); out = []
    # 1) 較正用の割合（外側・較正ともブロック）
    for frac in (0.10, 0.40):
        p = cc.run(d, "block20", "block20", methods=("split", "norm"), frac=frac)
        out.append(cc.summarize(p, d, f"較正用 {int(frac*100)}%（ブロック／ブロック）")); print(out[-1].round(3).to_string(), f"{time.time()-t0:.0f}s")
    # 2) 学習データを半分にする（地点を無作為に半分）
    half = d.sample(frac=0.5, random_state=SEED).reset_index(drop=True)
    for outer, calk in (("random", "random"), ("block20", "block20")):
        p = cc.run(half, outer, calk, methods=("split", "norm"))
        out.append(cc.summarize(p, half, f"データ半分（{outer}／{calk}）")); print(out[-1].round(3).to_string(), f"{time.time()-t0:.0f}s")
    # 3) 年をまたぐ：2016年の価格で学習・較正した区間に、同じ地点の2026年の価格が入るか
    d16 = d[d["price_2016"] > 0].copy().reset_index(drop=True)
    d16["y26"] = d16["y"]; d16["y"] = np.log(d16["price_2016"])
    p = cc.run(d16, "random", "random", methods=("split",))
    p = p.merge(d16[["code", "y26"]], on="code")
    shift = np.median(d16["y26"] - d16["y"])          # 全国の地点の対数変化の中央値（比較のための調整）
    rows = []
    for t in (80, 90, 95):
        lo, hi = p[f"split_lo{t}"], p[f"split_hi{t}"]
        rows += [dict(setting="2016年で作った区間→2016年の価格", method="split", target=t, coverage=((p.y >= lo) & (p.y <= hi)).mean(), width_ratio_median=np.median(np.exp(hi - lo)), n=len(p)),
                 dict(setting="2016年で作った区間→2026年の価格", method="split", target=t, coverage=((p.y26 >= lo) & (p.y26 <= hi)).mean(), width_ratio_median=np.median(np.exp(hi - lo)), n=len(p)),
                 dict(setting="同上＋全国の中央値の変化だけずらす", method="split", target=t, coverage=((p.y26 >= lo + shift) & (p.y26 <= hi + shift)).mean(), width_ratio_median=np.median(np.exp(hi - lo)), n=len(p))]
    out.append(pd.DataFrame(rows)); print(out[-1].round(3).to_string(), "shift", round(float(np.exp(shift)), 3))
    p[["code", "y", "y26", "pred", "split_lo90", "split_hi90"]].to_csv(RES / "year_shift_points.csv", index=False, float_format="%.5f")
    pd.concat(out).to_csv(RES / "coverage_robust.csv", index=False, float_format="%.4f")
