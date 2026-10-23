"""e-Stat から落とした表1の Excel（data/raw/kouri_YYYY_NN.xls(x)）を読み、data/ の整形済み CSV を作る

出力
  data/prices_1.csv〜prices_4.csv : 分析に使う25品目の都市別・月別価格（品目×都市×年の横持ち）
  data/items.csv                  : 25品目の各年の銘柄（基本銘柄）と単位
  data/brand_changes.csv          : 全品目の銘柄・単位の改正月（価格の変化から除く月）
  data/freq_all_1.csv, _2.csv     : 食料・外食の全品目について、月ごとの「前月と比べた変化」の集計
"""
import re, glob
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd
from common import RAW, DATA, MONTHS, parse_file

# 分析に使う25品目：キー → 銘柄符号
SELECT = {
    "米（コシヒカリ）": "1001", "食パン": "1021", "カップ麺": "1051", "牛乳": "1303", "鶏卵": "1341",
    "豚肉": "1211", "鶏肉": "1221", "キャベツ": "1401", "じゃがいも": "1412", "たまねぎ": "1417",
    "バナナ": "1581", "豆腐": "1471", "納豆": "1473", "食用油": "1601", "しょうゆ": "1621",
    "みそ": "1631", "砂糖": "1632", "マヨネーズ": "1643", "ビール": "2021",
    "中華そば（外食）": "2102", "すし（外食）": "2121", "カレーライス（外食）": "2133",
    "牛丼（外食）": "2136", "ハンバーガー（外食）": "2135", "コーヒー（喫茶店）": "2162",
}


def change_months(d):
    """銘柄の説明にある「○年○月から基本銘柄改正／単位変更」と、年をまたいで銘柄・単位の文言が変わった1月を拾う"""
    rows = []
    for code, g in d.groupby("code"):
        g = g.groupby("year").agg(brand=("brand", "first"), unit=("unit", "first")).reset_index()
        for r in g.itertuples():
            for m in re.finditer(r"(平成(\d+)|(\d{4}))年(\d+)月から([^，,]*)", r.brand):
                y = 1988 + int(m.group(2)) if m.group(2) else int(m.group(3))
                if "銘柄" in m.group(5) or "単位" in m.group(5):
                    rows.append([code, f"{y}-{int(m.group(4)):02d}", m.group(0)])
        def norm(s):
            s = re.sub(r"[，,]?(平成\d+|\d{4})年\d+月から.*$", "", s)
            return re.sub(r"[\s()（）｢｣「」･・]", "", s)
        g["b"] = g.brand.map(norm); g["u"] = g.unit.map(lambda s: re.sub(r"[･\s].*$", "", s))
        for a, b in zip(g.itertuples(), g.iloc[1:].itertuples()):
            if b.year == a.year + 1 and (a.b != b.b or a.u != b.u) and not any(x[0] == code and x[1].startswith(str(b.year)) for x in rows):
                rows.append([code, f"{b.year}-01", "年をまたいで銘柄・単位の文言が変わった"])
    return pd.DataFrame(rows, columns=["code", "t", "reason"]).drop_duplicates(["code", "t"])


def to_long(d):
    m = d.melt(id_vars=["code", "city", "year"], value_vars=MONTHS, var_name="m", value_name="p")
    m["ti"] = m.year * 12 + m.m.str[1:].astype(int) - 1
    return m.drop(columns=["m", "year"]).sort_values(["code", "city", "ti"])


def freq_table(d, ch):
    """品目×月：前月も今月も価格がある都市の数、上がった・下がった都市の数、変化率（対数）の絶対値の合計"""
    m = to_long(d)
    m["p0"] = m.groupby(["code", "city"]).p.shift()
    m["t0"] = m.groupby(["code", "city"]).ti.shift()
    m = m[(m.ti - m.t0 == 1) & m.p.notna() & m.p0.notna() & (m.p > 0) & (m.p0 > 0)]
    m["t"] = [f"{t // 12}-{t % 12 + 1:02d}" for t in m.ti]
    m = m.merge(ch[["code", "t"]].assign(x=1), on=["code", "t"], how="left")
    m = m[m.x.isna()]
    r = np.log(m.p / m.p0)
    m = m.assign(up=(r > 0).astype(int), dn=(r < 0).astype(int), absr=np.abs(r).round(6))
    return m.groupby(["code", "t"]).agg(n=("p", "size"), up=("up", "sum"), dn=("dn", "sum"), sum_abs=("absr", "sum")).reset_index()


def main():
    fs = sorted(glob.glob(str(RAW / "kouri_*.xls*")))
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(parse_file, fs))
    d = pd.DataFrame([r for rs in res for r in rs],
                     columns=["year", "code", "item", "brand", "unit", "city", "avg"] + MONTHS + ["subst"])
    d["brand"] = d.brand.str.replace(r"\s", "", regex=True)
    d["unit"] = d.unit.str.replace(r"\s", "", regex=True)
    print("全体", d.shape, "年", d.year.min(), d.year.max(), "品目数", d.code.nunique())
    ch = change_months(d)
    ch.to_csv(DATA / "brand_changes.csv", index=False)
    # 25品目
    key = {v: k for k, v in SELECT.items()}
    s = d[d.code.isin(key)].copy()
    s.insert(0, "key", s.code.map(key))
    s.groupby(["key", "code", "year"]).agg(item=("item", "first"), brand=("brand", "first"), unit=("unit", "first")) \
        .reset_index().to_csv(DATA / "items.csv", index=False)
    s = s.drop(columns=["item", "brand", "unit"])
    for c in ["avg"] + MONTHS:
        s[c] = s[c].round(1)
    keys = list(SELECT)
    for i in range(4):
        part = s[s.key.isin(keys[i::4])].sort_values(["code", "year", "city"])
        part.to_csv(DATA / f"prices_{i + 1}.csv", index=False, float_format="%g")
    # 食料・外食の全品目（銘柄符号 1001〜2199）の変化の集計
    f = d[d.code.astype(int).between(1001, 2199)]
    ft = freq_table(f, ch)
    codes = sorted(ft.code.unique())
    half = codes[len(codes) // 2]
    ft[ft.code < half].to_csv(DATA / "freq_all_1.csv", index=False, float_format="%g")
    ft[ft.code >= half].to_csv(DATA / "freq_all_2.csv", index=False, float_format="%g")
    names = f.groupby("code").item.last().rename("item").reset_index()
    names.to_csv(DATA / "item_names.csv", index=False)
    for p in sorted(DATA.glob("*.csv")):
        print(p.name, p.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
