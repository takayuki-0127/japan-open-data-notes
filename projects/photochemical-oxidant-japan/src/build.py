"""報告書の PDF（data/raw/）から、分析に使う表を CSV にする。
data/ の CSV があれば分析はそれを使うので、このスクリプトは元の PDF から作り直すときだけ動かす。"""
import re
import pandas as pd
from common import text, year, nums, DATA

SUBST = ["二酸化窒素", "浮遊粒子状物質", "光化学オキシダント", "二酸化硫黄", "一酸化炭素", "微小粒子状物質"]


def ox_mean():
    """表（図４-２-６の下）：光化学オキシダントの昼間の日最高1時間値の年平均値（S52〜R5）"""
    L = text("ch4"); rows = []
    for i, s in enumerate(L):
        if re.match(r"^\s*年度\s+S52|^\s*年度\s+H5|^\s*年度\s+H21", s):
            y0 = year(s.split()[1])
            for k in (1, 2):
                lab = L[i + k].split()[0]
                vals = nums(L[i + k])
                for j, v in enumerate(vals):
                    rows.append({"fiscal_year": y0 + j, "station": "一般局" if lab == "一般局" else "自排局", "ppm": v})
    df = pd.DataFrame(rows).pivot(index="fiscal_year", columns="station", values="ppm").reset_index()
    assert df.fiscal_year.min() == 1977 and df.fiscal_year.max() == 2023 and len(df) == 47, df
    return df


def alerts():
    """表４-２-４：注意報等の発令延日数と被害届出人数（S45〜R5）"""
    L = text("ch4"); i0 = next(i for i, s in enumerate(L) if "表４-２-４" in s)
    era, rows = None, []
    pat = re.compile(r"^\s*(昭和|平成|令和)?\s*(元|\d+)\s+(\d+)\s+(\d+)\s*\(\s*(\d+)\s*\)\s+(\d+)\s+([\d,]+)\s*$")
    for s in L[i0:i0 + 120]:
        m = pat.match(s)
        if not m:
            continue
        era = m.group(1) or era
        n = 1 if m.group(2) == "元" else int(m.group(2))
        y = {"昭和": 1925, "平成": 1988, "令和": 2018}[era] + n
        rows.append({"year": y, "alert_prefs": int(m.group(3)), "alert_days": int(m.group(4)), "warning_days": int(m.group(5)),
                     "damage_prefs": int(m.group(6)), "damage_persons": int(m.group(7).replace(",", ""))})
    df = pd.DataFrame(rows)
    assert df.year.min() == 1970 and df.year.max() == 2023 and len(df) == 54, (df.year.min(), df.year.max(), len(df))
    return df


def attainment():
    """表１-２-１：測定項目別の測定局数と環境基準達成率（H26〜R5）、表１-２-２：年平均値"""
    L = text("ch1")
    i0 = next(i for i, s in enumerate(L) if "表１-２-１" in s)
    i1 = next(i for i, s in enumerate(L) if "表１-２-２" in s)
    years = list(range(2014, 2024))
    st, rt = [], []
    for s in L[i0:i1]:
        if "測定局数" in s:
            st.append(nums(s.split("測定局数")[1])[:10])
        if "達成率" in s and "%" in s:
            rt.append([float(x) for x in re.findall(r"([\d.]+)%", s)][:10])
    assert len(st) == 12 and len(rt) == 12, (len(st), len(rt))
    rows = []
    for k in range(12):
        for j, y in enumerate(years):
            rows.append({"fiscal_year": y, "station": "一般局" if k < 6 else "自排局", "substance": SUBST[k % 6],
                         "stations": st[k][j], "attainment_pct": rt[k][j]})
    att = pd.DataFrame(rows)
    # 表１-２-２ 年平均値
    i2 = next(i for i, s in enumerate(L) if "（１）二酸化窒素（ＮＯ２）" in s)
    mrows, k = [], 0
    for s in L[i1:i2]:
        for name in SUBST:
            if name in s:
                v = nums(s.split(name)[1].replace("μg/m", "").replace("mg/m3", "").replace("mg/m", "").replace("ppm", ""))
                v = [x for x in v if x != 3][-10:]
                if len(v) == 10:
                    for j, y in enumerate(years):
                        mrows.append({"fiscal_year": y, "station": "一般局" if k < 6 else "自排局", "substance": name, "annual_mean": v[j]})
                    k += 1
    mean = pd.DataFrame(mrows)
    assert k == 12, k
    return att, mean


def longterm():
    """第10章：長期継続測定局の年平均値の平均（二酸化窒素14局、一酸化窒素22局、浮遊粒子状物質29局、二酸化硫黄9局）"""
    L = text("ch10")
    sec = {}
    for i, s in enumerate(L):
        for name in ("二酸化窒素", "一酸化窒素", "浮遊粒子状物質", "二酸化硫黄", "一酸化炭素", "非メタン炭化水素"):
            if re.match(rf"^\s*[１２３４５６]\s+{name}", s):
                sec[name] = i
    order = sorted(sec.items(), key=lambda x: x[1])
    rows = []
    for n, (name, a) in enumerate(order):
        b = order[n + 1][1] if n + 1 < len(order) else len(L)
        auto = next((i for i in range(a, b) if "（自排局）" in L[i] and "表１０" in L[i]), b)  # 一般局の表だけ使う
        hdr = None
        for s in L[a:auto]:
            toks = s.split()
            ys = [year(t) for t in toks if year(t)]
            if len(ys) >= 3 and ("測定局" in s or "測   定   局" in s or "測定局" in s.replace(" ", "")):
                hdr = ys
                continue
            if hdr and re.search(r"(１４局平均|平\s*均\s*値)", s):
                part = s.split("局平均")[-1] if "局平均" in s else re.split(r"平\s*均\s*値", s)[-1]
                v = [float("nan") if t in ("－", "-", "―") else float(t.strip("()")) for t in part.split()]
                if len(v) == len(hdr):
                    rows += [{"substance": name, "fiscal_year": y, "mean": x} for y, x in zip(hdr, v)]
                hdr = None
    df = pd.DataFrame(rows).drop_duplicates(["substance", "fiscal_year"])
    return df


def tail_no2():
    """二酸化窒素14局平均のH29〜R5（表の最後のブロックは見出しの形が違うので別に読む）"""
    L = text("ch10")
    i = next(i for i, s in enumerate(L) if "１４局平均" in s and len(nums(s)) == 7)
    return pd.DataFrame({"substance": "二酸化窒素", "fiscal_year": range(2017, 2024), "mean": nums(L[i])})


if __name__ == "__main__":
    ox = ox_mean(); ox.to_csv(DATA / "ox_daily_max_annual_mean.csv", index=False, encoding="utf-8-sig")
    al = alerts(); al.to_csv(DATA / "ox_alerts.csv", index=False, encoding="utf-8-sig")
    att, mean = attainment()
    att.to_csv(DATA / "attainment_2014_2023.csv", index=False, encoding="utf-8-sig")
    mean.to_csv(DATA / "annual_mean_2014_2023.csv", index=False, encoding="utf-8-sig")
    lt = longterm()
    if not ((lt.substance == "二酸化窒素") & (lt.fiscal_year == 2023)).any():
        lt = pd.concat([lt, tail_no2()]).drop_duplicates(["substance", "fiscal_year"])
    lt = lt.sort_values(["substance", "fiscal_year"])
    lt.to_csv(DATA / "longterm_station_mean.csv", index=False, encoding="utf-8-sig")
    print(ox.tail(3), al.tail(3), att.head(3), mean.head(3), sep="\n")
    print(lt.groupby("substance").fiscal_year.agg(["min", "max", "count"]))
