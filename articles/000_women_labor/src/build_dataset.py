"""e-Stat（社会・人口統計体系 市区町村データ）から分析用データセットを作る。
入力: data/raw/ の Excel（統計でみる市区町村のすがた2026 基礎データ）と SSDS から取得した CSV
出力: data/processed/municipal_women_labor.csv
"""
from pathlib import Path
import pandas as pd
import numpy as np

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = Path(__file__).resolve().parents[1] / "data" / "processed"


def read_kiso(letter: str) -> pd.DataFrame:
    """基礎データ Excel を「市区町村コード × 項目コード」の表にする。
    行7=項目コード、行9=調査年、行10以降=地域（列1=地域コード、列8=地域名）"""
    df = pd.read_excel(RAW / f"2026-{letter}.xls", header=None)
    item_cols = [c for c in range(10, df.shape[1]) if str(df.iat[7, c]).strip() not in ("nan", "")]
    body = df.iloc[10:].copy()
    out = pd.DataFrame({"code": pd.to_numeric(body[1], errors="coerce"),
                        "name": body[8].astype(str).str.replace("　", "").str.strip()})
    for c in item_cols:
        out[str(df.iat[7, c]).strip()] = pd.to_numeric(body[c], errors="coerce")
    out = out.dropna(subset=["code"])
    out["code"] = out["code"].astype(int)
    return out.drop_duplicates("code")


def read_ssds(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    first = df.columns[0]
    df["code"] = df[first].astype(str).str[:5].astype(int)
    ren = {c: c.split("_")[0] for c in df.columns if "_" in c and c != first}
    df = df.rename(columns=ren)
    for c in ren.values():
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    df["pref_name"] = df[first].astype(str).str.split("_").str[1].str.split(" ").str[0]
    return df.drop(columns=[first])


def main():
    base = read_kiso("a")
    for l in "bcefj":
        base = base.merge(read_kiso(l).drop(columns="name"), on="code", how="left")
    w = read_ssds(RAW / "estat_ssds_municipal_women_2020.csv")
    cc = pd.read_csv(RAW / "estat_ssds_municipal_childcare_2017.csv")
    df = w.merge(base, on="code", how="left").merge(cc, on="code", how="left")
    df["pref_code"] = df["code"] // 1000

    # 目的変数：女性の労働力率（労働力状態「不詳」を除く）
    df["y_flfp"] = df["F110102"] / (df["F110102"] + df["F110802"])
    # 説明変数
    df["childcare_per_child"] = (df["J2506"] + df["J2545"] + df["J2546"]) / df["A1405"]   # 2017在所児 / 2020の0〜5歳
    df["nursery_per_1k_child"] = df["J250302"] / df["A1405"] * 1000                      # 2023保育所等数 / 2020の0〜5歳
    df["child_share"] = df["A1405"] / df["A1101"]
    df["nuclear_share"] = df["A810102"] / df["A710101"]
    df["single_share"] = df["A810105"] / df["A710101"]
    df["w_old_share"] = df["A130302"] / df["A141402"]                                    # 15歳以上女性のうち65歳以上
    df["univ_share"] = df["E9106"] / df["E9101"]
    df["w_commute_out"] = df["F270502"] / (df["F110102"])                               # 女性労働力のうち他市区町村へ通勤（概算）
    df["income_per_taxpayer"] = df["C120110"] / df["C120120"]                           # 千円
    df["log_density"] = np.log(df["A1101"] / df["B1103"])                               # 可住地1km²あたり人口
    df["tertiary_share"] = df["F2221"] / df["F1102"]
    df["primary_share"] = df["F2201"] / df["F1102"]
    df["log_pop"] = np.log(df["A1101"])
    df["log_income"] = np.log(df["income_per_taxpayer"])
    df["did_share"] = df["A1801"] / df["A1101"]
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "municipal_women_labor.csv", index=False, encoding="utf-8-sig")
    print(df.shape, df["y_flfp"].describe())


if __name__ == "__main__":
    main()
