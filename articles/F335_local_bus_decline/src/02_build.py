"""02 整形：府県相互間旅客輸送人員表（乗合バス）から、府県の中の移動（対角）と府県から出る合計を取り出す。人口（国勢調査）も"""
import pathlib, re
import numpy as np, pandas as pd
import openpyxl, xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PREF = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
        "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
        "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
        "宮崎", "鹿児島", "沖縄"]
NAMES = set(PREF) | {"道北", "道東", "道央", "道南", "全国"}


def rows_of(f):
    if f.suffix == ".xls":
        s = xlrd.open_workbook(str(f)).sheet_by_name("乗合バス")
        return [s.row_values(i) for i in range(s.nrows)]
    ws = openpyxl.load_workbook(str(f), read_only=True, data_only=True)["乗合バス"]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def clean(x):
    return str(x).replace("　", "").replace(" ", "").strip() if x is not None else ""


def parse(f):
    cells, hdr = {}, None
    for r in rows_of(f):
        c = [clean(x) for x in r]
        if sum(x in NAMES for x in c) >= 5:
            hdr = {j: x for j, x in enumerate(c) if x in NAMES}
            continue
        orig = next((x for x in c[:2] if x in NAMES), None)
        if orig is None or hdr is None:
            continue
        for j, dest in hdr.items():
            if j < len(r):
                try:
                    cells[(orig, dest)] = float(r[j])
                except (TypeError, ValueError):
                    pass
    return cells


def population():
    ws = openpyxl.load_workbook(str(RAW / "census_ts_households_t1_1960_2020_000001086170.xlsx"), read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr = rows[5]
    starts = [(j, int(str(x)[:4])) for j, x in enumerate(hdr) if x and re.fullmatch(r"\d{4}年", str(x))]
    out = []
    for r in rows[9:]:
        m = re.match(r"^(\d{5})_(.+)$", str(r[0]) if r[0] else "")
        if not m or not m.group(1).endswith("000") or m.group(1) == "00000":
            continue
        for j, y in starts:
            if y >= 2000:
                out.append((y, int(m.group(1)[:2]), float(r[j + 1]), float(r[j + 3])))
    ws = openpyxl.load_workbook(str(RAW / "census_2025_t12-2_members_000040506466.xlsx"), read_only=True).worksheets[0]
    for r in ws.iter_rows(min_row=11, values_only=True):
        if r[0] != "a" or r[2] != "0_総数" or r[3] != "0_総数" or r[4] != "00_総数":
            continue
        m = re.match(r"^(\d{5})_(.+)$", str(r[1]))
        if m and m.group(1).endswith("000") and m.group(1) != "00000":
            out.append((2025, int(m.group(1)[:2]), np.nan, float(r[5])))
    p = pd.DataFrame(out, columns=["year", "code", "total_p", "gen_p"])
    # 年ごとに直線でつなぐ（2000〜2025年）
    res = []
    for code, g in p.groupby("code"):
        g = g.set_index("year").sort_index()
        yrs = np.arange(2000, 2026)
        gp = np.interp(yrs, g.index, g.gen_p)
        tp_known = g.total_p.dropna()
        # 総人口：2025年は一般世帯人員の伸びでのばす
        tp25 = tp_known.loc[2020] * g.gen_p.loc[2025] / g.gen_p.loc[2020]
        tp = np.interp(yrs, list(tp_known.index) + [2025], list(tp_known.values) + [tp25])
        for y, a, b in zip(yrs, gp, tp):
            res.append((int(y), PREF[code - 1], a, b))
    return pd.DataFrame(res, columns=["year", "pref", "gen_p", "total_p"])


def main():
    out = []
    for f in sorted(RAW.glob("ryokaku_*")):
        y = int(f.name.split("_")[1])
        c = parse(f)
        for p in PREF:
            out.append((y, p, c.get((p, p), np.nan), c.get((p, "全国"), np.nan)))
        out.append((y, "全国", c.get(("全国", "全国"), np.nan), np.nan))
    d = pd.DataFrame(out, columns=["year", "pref", "within", "from_total"])
    pop = population()
    d = d.merge(pop, on=["year", "pref"], how="left")
    d.to_csv(ROOT / "data" / "panel.csv", index=False)
    chk = d[d.pref != "全国"].groupby("year").within.agg(["count", "sum"])
    print(chk.T.to_string())
    print(d.within.isna().sum(), d.from_total.isna().sum())


if __name__ == "__main__":
    main()
