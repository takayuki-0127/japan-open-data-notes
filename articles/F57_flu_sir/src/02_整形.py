"""全国と都道府県の週ごとの定点当たり報告数を、シーズン（第36週〜翌年第35週）ごとに並べる。

- 全国は IDWR の「総数」の行（定点当たり報告数）を使う
- 週の中日（木曜）の日付を付ける（ISO 週）
- 2025年第14週から定点が急性呼吸器感染症（ARI）定点に変わったので、2025/26 以降は水準が前と少し違う
"""
import json
import numpy as np
import pandas as pd
from common import RAW, DATA

PREF = pd.read_csv(RAW / "pref_points_F33.csv")["pref"].tolist()


def main():
    rows = json.load(open(RAW / "f52_teiten_flu.json", encoding="utf-8"))["rows"]
    df = pd.DataFrame(rows, columns=["src", "period", "pref", "rep", "per"])
    m = df["src"].str.extract(r"(\d{4})-(\d{2})-teiten")
    df["year"] = m[0].astype(int)
    df["week"] = m[1].astype(int)
    for c in ["rep", "per"]:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    df = df[df["pref"].isin(PREF + ["総数"])].drop_duplicates(["year", "week", "pref"], keep="last")
    df["date"] = [pd.Timestamp.fromisocalendar(y, w, 4) for y, w in zip(df["year"], df["week"])]
    df["season_start"] = np.where(df["week"] >= 36, df["year"], df["year"] - 1)
    df["season"] = df["season_start"].astype(str) + "/" + (df["season_start"] + 1).astype(str).str[-2:]
    df = df.sort_values(["date", "pref"])
    nat = df[df["pref"] == "総数"][["season", "season_start", "year", "week", "date", "rep", "per"]]
    nat["sentinels"] = (nat["rep"] / nat["per"]).round()
    nat.to_csv(DATA / "flu_national_weekly.csv", index=False)
    pref = df[df["pref"] != "総数"][["season", "season_start", "year", "week", "date", "pref", "rep", "per"]]
    pref.to_csv(DATA / "flu_pref_weekly.csv", index=False)
    print(nat.groupby("season")["per"].agg(["size", "max", "sum"]).round(1).to_string())


if __name__ == "__main__":
    main()
