"""整形：日別×出生の場所×時刻の出生数と、月別の出生数・死亡数（年次）を縦長の表にする。"""
import csv
import datetime as dt
import unicodedata
import pandas as pd
import jpholiday
from common import RAW, DATA, YEARS


def nk(s):
    return unicodedata.normalize("NFKC", s).replace(" ", "").replace("　", "")


def num(s):
    s = nk(s)
    return 0 if s in ("-", "", "…") else int(s)


def daily():
    rows = []
    for y in YEARS:
        place = month = None
        with open(RAW / f"hokan_shussei_t07_{y}.csv", encoding="utf-8") as f:
            for r in csv.reader(f):
                if not r:
                    continue
                c0 = nk(r[0])
                if "*" in c0:
                    place, m = c0.split("*")
                    month = None if m == "総数" else int(m.replace("月", ""))
                    continue
                if month is None or not c0.endswith("日"):
                    continue
                d = int(c0[:-1])
                try:
                    date = dt.date(y, month, d)
                except ValueError:
                    continue
                vals = [num(v) for v in r[1:26]]
                rows.append([date, y, month, d, place, vals[0]] + vals[1:25])
    cols = ["date", "year", "month", "day", "place", "births"] + [f"h{h:02d}" for h in range(24)]
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df.date.dt.weekday
    df["holiday"] = df.date.map(lambda x: jpholiday.is_holiday(x.date())).astype(int)
    md = df.date.dt.strftime("%m-%d")
    df["newyear"] = md.isin(["12-29", "12-30", "12-31", "01-01", "01-02", "01-03"]).astype(int)
    return df


def monthly(fname, label):
    out = []
    with open(RAW / fname, encoding="utf-8") as f:
        block = False
        for r in csv.reader(f):
            if not r:
                continue
            c = [nk(x) for x in r]
            head = c[0]
            if label == "births":
                if head.startswith("出生数"):
                    block = True
                    continue
                if head.startswith("出生率"):
                    break
                if block and head.isdigit():
                    y = int(head)
                    vals = c[2:14]
                    if "…" in vals:
                        continue
                    out += [[y, m + 1, int(v)] for m, v in enumerate(vals)]
            else:
                if head.startswith("死亡率"):
                    break
                if head.startswith("死亡数") or (head == "" and c[1].isdigit()):
                    y = int(c[1])
                    vals = c[3:15]
                    if "…" in vals:
                        continue
                    out += [[y, m + 1, int(v)] for m, v in enumerate(vals)]
    return pd.DataFrame(out, columns=["year", "month", label])


if __name__ == "__main__":
    d = daily()
    d.to_csv(DATA / "births_daily_place_hour.csv", index=False)
    b = monthly("joukan_shussei_t4_2_2025.csv", "births")
    m = monthly("joukan_shibou_t5_4_2025.csv", "deaths")
    b.merge(m, on=["year", "month"], how="outer").sort_values(["year", "month"]).to_csv(
        DATA / "births_deaths_monthly.csv", index=False)
    # 検算：日別の合計が年の総数と一致するか
    tot = d[d.place == "総数"].groupby("year").births.sum()
    print(tot.to_dict())
    print(b.groupby("year").births.sum().tail(8).to_dict())
    print(d.place.value_counts().to_dict(), len(d))
    print(m.year.unique())
