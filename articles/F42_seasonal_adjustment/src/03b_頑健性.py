"""03b 頑健性：設定を変えると、公表値との差はどれだけ変わるか
- ARIMA の次数：自動選択 / (0 1 1)(0 1 1) に固定
- コロナ期の外れ値：自動で探す / 探さない / 2020年4月〜6月を一時的な外れ値（AO）として固定
- 曜日・祝日：両方 / 曜日だけ / 祝日だけ / なし（鉱工業）
- 労働力調査：管理限界 9.8σ〜9.9σ（総務省の説明、基本）/ X-13 の既定 1.5σ〜2.5σ、計算の始まりを2000年・2010年にする
- 系列を変える：鉱工業2系列＋労働力調査6系列＋有効求人倍率（03 の結果）
出力: results/robustness.csv
"""
import numpy as np
import pandas as pd
from common import DATA, RES, run_x13, compare

S = pd.read_csv(DATA / "series.csv", parse_dates=["date"])
G = {k: v.set_index("date").sort_index() for k, v in S.groupby("series")}
PF = pd.read_csv(DATA / "lfs_factors_pub.csv", parse_dates=["date"], index_col="date")
COVID_AO = ("ao2020.apr", "ao2020.may", "ao2020.jun")


def iip_run(y, **kw):
    """2025年の年間補正（2014〜2025年のデータ）で、2025年と2026年1〜8月の季節指数を比べる"""
    r = run_x13(y.nsa, span=("2014-01", "2025-12"), name="iip", **kw)
    pubf = y.nsa / y.sa_pub * 100
    d = (r["sf"] - pubf)["2025-01":"2026-08"].abs()
    c = compare(y.nsa / r["sf"] * 100, y.sa_pub, "2025-01", "2026-08")
    return {"季節指数の差の平均": d.mean(), "季節指数の差の最大": d.max(), "前月比の相関": c["前月比の相関"],
            "前月比の向きの一致率": c["前月比の向きの一致率"], "モデル": r["model"]}


def lfs_run(k, start="1990-01", **kw):
    y = G[k]
    r = run_x13(y.nsa, span=(start, "2025-12"), name="lfs", **kw)
    d = (r["sf"] - PF[k])["2016-01":"2026-08"].abs()
    rate = k == "完全失業率"
    c = compare(y.nsa / r["sf"] * 100, y.sa_pub, "2016-01", "2026-08", rate=rate, ndigits=1 if rate else None)
    return {"季節指数の差の平均": d.mean(), "季節指数の差の最大": d.max(), "前月比の相関": c["前月比の相関"],
            "前月比の向きの一致率": c["前月比の向きの一致率"], "モデル": r["model"]}


def main():
    rows = []
    base_iip = dict(td=True, holiday=True, lpyear=True, arima="auto", outliers=True)
    variants_iip = [
        ("基本（曜日＋祝日、ARIMA 自動、外れ値を自動で探す）", base_iip),
        ("ARIMA を (0 1 1)(0 1 1) に固定", {**base_iip, "arima": "(0 1 1)(0 1 1)"}),
        ("外れ値を探さない", {**base_iip, "outliers": False}),
        ("2020年4〜6月を外れ値（AO）に固定", {**base_iip, "outliers": False, "fixed_outliers": COVID_AO}),
        ("曜日だけ（祝日なし）", {**base_iip, "holiday": False}),
        ("祝日だけ（曜日なし）", {**base_iip, "td": False}),
        ("曜日・祝日の調整なし", {**base_iip, "td": False, "holiday": False, "lpyear": False}),
        ("X-11 の既定（事前調整なし）", dict(mode="x11")),
    ]
    for k in ["鉱工業生産", "鉱工業出荷"]:
        for lab, kw in variants_iip:
            try:
                res = iip_run(G[k], **kw)
            except Exception as e:  # noqa
                res = {"季節指数の差の平均": np.nan, "モデル": f"失敗: {e}"}
            rows.append({"系列": k, "比べた期間": "2025年1月〜2026年8月", "設定": lab, **res})

    base_lfs = dict(arima="auto", outliers=True, sigmalim=(9.8, 9.9))
    variants_lfs = [
        ("基本（1990年〜、ARIMA 自動、外れ値を自動で探す、管理限界 9.8σ〜9.9σ）", "1990-01", base_lfs),
        ("ARIMA を (0 1 1)(0 1 1) に固定", "1990-01", {**base_lfs, "arima": "(0 1 1)(0 1 1)"}),
        ("外れ値を探さない", "1990-01", {**base_lfs, "outliers": False}),
        ("2020年4〜6月を外れ値（AO）に固定", "1990-01", {**base_lfs, "outliers": False, "fixed_outliers": COVID_AO}),
        ("管理限界を X-13 の既定（1.5σ〜2.5σ）にする", "1990-01", {**base_lfs, "sigmalim": None}),
        ("曜日・祝日の調整を入れる", "1990-01", {**base_lfs, "td": True, "holiday": True}),
        ("計算を2000年からにする", "2000-01", base_lfs),
        ("計算を2010年からにする", "2010-01", base_lfs),
    ]
    for k in ["就業者", "完全失業者", "完全失業率"]:
        for lab, st, kw in variants_lfs:
            res = lfs_run(k, start=st, **kw)
            rows.append({"系列": k, "比べた期間": "2016年1月〜2026年8月", "設定": lab, **res})
    df = pd.DataFrame(rows)
    df.round(3).to_csv(RES / "robustness.csv", index=False)
    print(df.round(3).to_string())


if __name__ == "__main__":
    main()
