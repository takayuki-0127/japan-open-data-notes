"""週×都道府県のパネルと、隣接・移動・距離の重み行列を作る。

- シーズン：第36週〜翌年第35週。"2015/16" のように呼ぶ
- 定点当たり報告数（定当）を主に使う。2025年第14週から定点が急性呼吸器感染症（ARI）定点に
  変わったため、それ以降は数字の水準が前と少し違う（記事の「言えないこと」に書いた）
"""
import json, re
import numpy as np
import pandas as pd
from common import RAW, DATA

PREF = pd.read_csv(RAW / "pref_points_F33.csv")["pref"].tolist()  # 47都道府県（コード順）


def main():
    rows = json.load(open(RAW / "f52_teiten_flu.json", encoding="utf-8"))["rows"]
    df = pd.DataFrame(rows, columns=["src", "period", "pref", "rep", "per"])
    m = df["src"].str.extract(r"(\d{4})-(\d{2})-teiten")
    df["year"] = m[0].astype(int)
    df["week"] = m[1].astype(int)
    df = df[df["pref"].isin(PREF)].copy()
    for c in ["rep", "per"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").replace({"-": "0", "": np.nan}), errors="coerce")
    df = df.drop_duplicates(["year", "week", "pref"], keep="last")
    df["season_start"] = np.where(df["week"] >= 36, df["year"], df["year"] - 1)
    df["season"] = df["season_start"].astype(str) + "/" + (df["season_start"] + 1).astype(str).str[-2:]
    # シーズン内の週の番号（第36週＝0）
    df["sw"] = np.where(df["week"] >= 36, df["week"] - 36, df["week"] + (53 if False else 52) - 36)
    # 53週ある年（2015・2020・2026）の調整：その年の第53週は sw=17、翌年の週は +1
    y53 = {2015, 2020, 2026}
    df.loc[(df["week"] < 36) & ((df["year"] - 1).isin(y53)), "sw"] += 1
    df["pcode"] = df["pref"].map({p: i + 1 for i, p in enumerate(PREF)})
    df = df.sort_values(["season_start", "sw", "pcode"])
    df[["season", "season_start", "year", "week", "sw", "pcode", "pref", "rep", "per", "period"]].to_csv(
        DATA / "flu_weekly_pref.csv", index=False)

    # 重み行列：隣接（境界を共有）、移動（2025年の都道府県間移動者数、往復の合計）、距離（逆数）
    pairs = pd.read_csv(RAW / "pref_pairs_F33.csv")
    n = 47
    A = np.zeros((n, n)); D = np.zeros((n, n))
    for r in pairs.itertuples():
        A[r.o - 1, r.d - 1] = A[r.d - 1, r.o - 1] = r.adj
        D[r.o - 1, r.d - 1] = D[r.d - 1, r.o - 1] = r.dist
    mig = pd.read_csv(RAW / "migration_2025_F10.csv", index_col=0).loc[PREF, PREF].values.astype(float)
    M = mig + mig.T
    np.fill_diagonal(M, 0)
    np.save(DATA / "W_adj.npy", A)
    np.save(DATA / "W_mig.npy", M)
    np.save(DATA / "D_km.npy", D)
    print(df.groupby("season").size().to_string())


if __name__ == "__main__":
    main()
