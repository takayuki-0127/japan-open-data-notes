"""02 整形：同梱の日別値（gzip の CSV）から、地点・年ごとの夏の始まり・終わり・長さを出す。
出力：
- data/daily_summary.csv  地点・年ごとの値（夏の定義ごとの始まり・終わり・長さ、25℃以上の日数、欠けの数、6〜9月の平均気温など）
- data/a2_counts.csv      年ごとの値のページの「日平均気温25℃以上の日数」（照合用）
- data/thresholds.csv     地点ごとの基準（1961〜1990年の日平均気温の上位25%の境の値）
"""
import gzip, html, io, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
VALID_Q = {"8", "5"}  # 8＝正常値、5＝準正常値。4（資料不足値）・1（欠測）などは欠けにする
Y0, Y1 = 1901, 2025


def read_daily(block):
    txt = gzip.decompress((RAW / f"jma_daily_tmean_{block}.csv.gz").read_bytes()).decode("cp932")
    lines = txt.splitlines()[5:]  # 先頭5行は時刻・空行・見出し3行（6行目が1901/1/1。レビューで [6:] から直した）
    df = pd.read_csv(io.StringIO("\n".join(lines)), header=None, names=["date", "t", "q", "hom"], dtype=str)
    df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d")
    df["t"] = pd.to_numeric(df["t"], errors="coerce")
    df.loc[~df["q"].isin(VALID_Q), "t"] = np.nan
    return df.set_index("date")["t"].astype(float)


def season(rm, thr, doy):
    """移動平均 rm（その年の日ごと）がしきい値以上の最初の日・最後の日。届かなければ NaN、長さ0。"""
    ok = np.where(rm >= thr)[0]
    if len(ok) == 0:
        return np.nan, np.nan, 0.0
    s, e = doy[ok[0]], doy[ok[-1]]
    return float(s), float(e), float(e - s + 1)


def main():
    st = pd.read_csv(RAW / "stations.csv", dtype={"block_no": str, "prec_no": str})
    rows, thr_rows, a2_rows = [], [], []
    for _, r in st.sort_values("order").iterrows():
        t = read_daily(r.block_no)
        t = t[(t.index.year >= Y0 - 1) & (t.index.year <= Y1)]
        base = t[(t.index.year >= 1961) & (t.index.year <= 1990)].dropna()
        p75 = float(np.round(np.quantile(base.values, 0.75), 2))
        thr_rows.append({"station": r.station, "group": r.group, "p75_1961_1990": p75})
        # 移動平均は 1e-9 単位で丸めてから比べる（pandas の rolling は累積和で計算するため、ちょうど25.0℃などの値が
        # 読み始めの位置で 24.999… になったりならなかったりする。レビューで足した）
        rm = {w: t.rolling(w, center=True, min_periods=w - 2).mean().round(9) for w in (7, 15)}
        for y in range(Y0, Y1 + 1):
            m = t.index.year == y
            ty = t[m]
            # うるう年は3月以降を1日引き、毎年同じ日付が同じ番号になるようにする（1＝1月1日、182＝7月1日）
            doy = ty.index.dayofyear.values - ((ty.index.is_leap_year) & (ty.index.month > 2)).astype(int)
            amj = (ty.index.month >= 4) & (ty.index.month <= 11)
            miss = int(ty[amj].isna().sum())
            row = {"station": r.station, "group": r.group, "order": int(r.order), "year": y, "missing_apr_nov": miss,
                   "tmean_jjas": float(np.round(ty[(ty.index.month >= 6) & (ty.index.month <= 9)].mean(), 3)),
                   "days_ge25": int((ty >= 25.0).sum())}
            for w in (7, 15):
                v = rm[w][m].values
                for name, thr in (("abs25", 25.0), ("abs24", 24.0), ("abs26", 26.0), ("p75", p75)):
                    if w == 15 and name not in ("abs25", "p75"):
                        continue
                    s, e, L = season(v, thr, doy)
                    key = f"{name}_w{w}"
                    row[f"{key}_start"], row[f"{key}_end"], row[f"{key}_len"] = s, e, L
                # いちばん暑い時期（移動平均が最も高い日。問い直し用）
                if w == 15 and np.isfinite(v).any():
                    row["peak_doy_w15"] = float(doy[int(np.nanargmax(v))])
                    row["peak_val_w15"] = float(np.round(np.nanmax(v), 3))
            rows.append(row)
        if r.group == "rural":
            s = gzip.decompress((RAW / f"jma_a2_{r.block_no}.html.gz").read_bytes()).decode("utf-8")
            for tr in re.findall(r'<tr class="mtx2?"[^>]*>(.*?)</tr>', s, flags=re.S):
                c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
                if len(c) >= 14 and c[0].isdigit() and Y0 <= int(c[0]) <= Y1:
                    v = c[13]
                    a2_rows.append({"station": r.station, "year": int(c[0]), "a2_days_ge25_raw": v})
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "daily_summary.csv", index=False, float_format="%.3f")
    a2 = pd.DataFrame(a2_rows)
    a2["a2_days_ge25"] = a2["a2_days_ge25_raw"].str.extract(r"^(\d+)\s*\)?$")[0].astype(float)
    a2.to_csv(DATA / "a2_counts.csv", index=False)
    pd.DataFrame(thr_rows).to_csv(DATA / "thresholds.csv", index=False)
    print("rows", len(df), "a2", len(a2))


if __name__ == "__main__":
    main()
