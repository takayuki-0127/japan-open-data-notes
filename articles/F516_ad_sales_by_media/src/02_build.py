"""Excel の「年・実数」「年・伸び率」「年度・実数」「年度・伸び率」から長い表（data/annual.csv）を作る。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "tokusabi_advertising_long.xls"
ITEMS = {"売上高合計": "total", "４媒体広告合計": "four_media", "新聞(４媒体広告)": "newspaper", "雑誌(４媒体広告)": "magazine",
         "テレビ(４媒体広告)": "tv", "ラジオ(４媒体広告)": "radio", "屋外広告": "outdoor", "交通広告": "transit",
         "折込み・ダイレクトメール": "insert_dm", "海外広告": "overseas", "ＳＰ・ＰＲ・催事企画": "sp_pr", "インターネット広告": "internet", "その他": "other"}


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def read(sheet):
    d = pd.read_excel(RAW, sheet_name=sheet, header=None)
    cols = {ITEMS[str(d.iloc[1, j])]: j for j in range(d.shape[1]) if str(d.iloc[1, j]) in ITEMS}
    assert len(cols) == len(ITEMS), cols
    out = []
    for i in range(len(d)):
        m = re.fullmatch(r"(\d{4})年度?", str(d.iloc[i, 1]).strip())
        if m:
            for k, j in cols.items():
                out.append((int(m.group(1)), k, num(d.iloc[i, j])))
    return pd.DataFrame(out, columns=["year", "item", "v"])


def main():
    parts = []
    for ptype, a, g in [("年", "年・実数", "年・伸び率"), ("年度", "年度・実数", "年度・伸び率")]:
        z = read(a).rename(columns={"v": "value"}).merge(read(g).rename(columns={"v": "growth"}), on=["year", "item"], how="left")
        z.insert(0, "period_type", ptype)
        parts.append(z)
    pd.concat(parts, ignore_index=True).sort_values(["period_type", "item", "year"]).to_csv(ROOT / "data" / "annual.csv", index=False)


if __name__ == "__main__":
    main()
