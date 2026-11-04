"""02 整形：data/raw/ の元ファイルを、分析に使う data/*.csv に整える。"""
import csv
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
DATA.mkdir(exist_ok=True)


def num(s):
    s = str(s).replace(",", "").replace(" ", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def monthly_nsa():
    """利用関係別 戸数（原数値、月次、1965年1月〜）"""
    rows = list(csv.reader(open(RAW / "estat_starts_tenure_monthly_000040521928.csv", encoding="utf-8")))
    start = next(i for i, r in enumerate(rows) if r and "S４０年" in r[0] and "１月" in r[0])
    out, t = [], pd.Period("1965-01", "M")
    for r in rows[start:]:
        if not r or not r[0].strip() or r[0].startswith("※") or num(r[1]) != num(r[1]):
            break
        out.append({"month": str(t), "total": num(r[1]), "owner": num(r[5]), "rental": num(r[9]),
                    "company": num(r[11]), "sale": num(r[13]), "sale_condo": num(r[15]), "sale_house": num(r[18])})
        t += 1
    return pd.DataFrame(out)


def monthly_sa():
    """利用関係別 戸数の季節調整値（月次、1969年1月〜。それ以前は四半期のため使わない）"""
    rows = list(csv.reader(open(RAW / "estat_starts_sa_000040521931.csv", encoding="utf-8")))
    start = next(i for i, r in enumerate(rows) if r and r[0].replace("　", " ").startswith("44年") and "1月" in r[0])
    out, t = [], pd.Period("1969-01", "M")
    for r in rows[start:]:
        if not r or not r[0].strip() or r[0].startswith("※") or num(r[1]) != num(r[1]):
            break
        out.append({"month": str(t), "total_sa": num(r[1]), "owner_sa": num(r[3]), "rental_sa": num(r[5]),
                    "company_sa": num(r[7]), "sale_sa": num(r[9])})
        t += 1
    return pd.DataFrame(out)


def rates():
    r = pd.read_csv(RAW / "boj_rates_monthly_raw.csv", dtype={"month": str})
    r["month"] = r.month.str[:4] + "-" + r.month.str[4:6]
    return r.rename(columns={"MADR1M": "basic_rate", "DLLI2CI@07": "loan_lt_city_stock",
                             "DLLI2CI@08": "loan_lt_regional_stock", "DLLR2CIDBNL3": "loan_lt_new",
                             "DLLR2CIDBST3": "loan_lt_stock"})


if __name__ == "__main__":
    m = monthly_nsa().merge(monthly_sa(), on="month", how="left").merge(rates(), on="month", how="left")
    m.to_csv(DATA / "monthly.csv", index=False)
    y = pd.read_csv(RAW / "f091_tenure_year.csv").pivot(index="year", columns="tenure", values="units")
    y = y.rename(columns={"総計": "total", "持家": "owner", "貸家": "rental", "給与住宅": "company", "分譲住宅": "sale"})
    y = y[["total", "owner", "rental", "company", "sale"]]
    r = rates(); r["year"] = r.month.str[:4].astype(int)
    ry = r.groupby("year")[["basic_rate", "loan_lt_city_stock", "loan_lt_new"]].mean()
    pop = pd.read_csv(RAW / "f140_pop_national_year.csv").set_index("year")
    ann = y.join(ry, how="left").join(pop, how="left")
    ann.to_csv(DATA / "annual.csv")
    pf = pd.read_csv(RAW / "f091_pref_year.csv").query("pref != '全国'")
    pp = pd.read_csv(RAW / "ssdse_b_pref_pop.csv")
    pp["pref"] = pp.pref.str.replace(r"(都|府|県)$", "", regex=True)  # 「青森県」→「青森」（建築着工の表記に合わせる）
    panel = pf.merge(pp, on=["year", "pref"], how="inner")
    panel.to_csv(DATA / "pref_panel.csv", index=False)
    print(m.month.iloc[[0, -1]].tolist(), m.total_sa.notna().sum(), len(ann), panel.shape, panel.year.min(), panel.year.max())
