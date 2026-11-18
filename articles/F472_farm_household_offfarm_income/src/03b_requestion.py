"""問い直し：全国の農業の割合が上がったのは、各区分（主業・準主業・副業的）の中で上がったからか、区分の構成が変わったからか。
全国の平均（農業・農外・年金の3つの金額）を、区分ごとの平均の重みつきの和として表し、重み（推定の構成比）を
「重みの和＝1、重み≧0」の最小二乗で年ごとに求める。そのうえで、変化を構成と中身に分ける（2つの順番の平均）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy.optimize import nnls

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
L = pd.read_csv(D / "national_long.csv").set_index("year")
S = pd.read_csv(D / "by_type.csv")
TYPES = ["主業", "準主業", "副業的"]
rows, X = [], {}
for y in range(2004, 2019):
    d = S[S.year == y].set_index("type").loc[TYPES]
    A = (d.ag + d.rel).values; O = d.off.values; P = d.pen.values
    M_ = np.vstack([A, O, P]); yv = np.array([L.loc[y, "ag"] + L.loc[y, "rel"], L.loc[y, "off"], L.loc[y, "pen"]])
    big = 1e5  # 重みの和＝1 を強く課す
    Mb = np.vstack([M_ / 1000, big * np.ones(3)]); yb = np.append(yv / 1000, big)
    w, _ = nnls(Mb, yb)
    fit = M_ @ w
    X[y] = (A, O, P)
    rows.append(dict(year=y, w_shugyo=w[0], w_junshugyo=w[1], w_fukugyo=w[2], w_sum=w.sum(),
                     fit_err_farm=fit[0] - yv[0], fit_err_off=fit[1] - yv[1], fit_err_pen=fit[2] - yv[2]))
W = pd.DataFrame(rows).set_index("year")
W.to_csv(R / "requestion_weights.csv", float_format="%.5f")


def share(w, x):
    A, O, P = x
    return 100 * (w @ A) / (w @ (A + O + P))


w0 = W.loc[2004, ["w_shugyo", "w_junshugyo", "w_fukugyo"]].values; w1 = W.loc[2018, ["w_shugyo", "w_junshugyo", "w_fukugyo"]].values
s00, s11 = share(w0, X[2004]), share(w1, X[2018])
s10, s01 = share(w1, X[2004]), share(w0, X[2018])  # 構成だけ2018／中身だけ2018
comp = ((s10 - s00) + (s11 - s01)) / 2
within = ((s01 - s00) + (s11 - s10)) / 2
out = {"s_2004_fit": s00, "s_2018_fit": s11, "change_fit": s11 - s00, "composition": comp, "within": within,
       "w2004": dict(zip(TYPES, map(float, w0))), "w2018": dict(zip(TYPES, map(float, w1))),
       "max_abs_fit_err": float(W[["fit_err_farm", "fit_err_off", "fit_err_pen"]].abs().max().max()),
       "s_only_composition_2018": s10, "s_only_within_2018": s01}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(W.round(3).to_string())
