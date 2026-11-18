"""02 整形：府県相互間旅客輸送人員表の機関別シートから、県の間（発≠着）の人数（千人）を年度×発×着の表にする。
県庁所在地の観測所の緯度・経度から、県の間の直線距離（km）も作る。
出力：data/od_wide.csv（fy, orig, dest, 機関ごとの列）、data/pref_distance.csv"""
import pathlib, re, io, zipfile
import numpy as np, pandas as pd
import openpyxl, xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PREF = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
        "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良",
        "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分",
        "宮崎", "鹿児島", "沖縄"]
NAMES = set(PREF) | {"道北", "道東", "道央", "道南", "全国"}
SHEETS = {"ＪＲ定期外": "jr_nonpass", "民鉄定期外": "pvt_nonpass", "乗合バス": "bus_route", "貸切バス": "bus_charter",
          "営業用乗用車": "taxi", "旅客船": "ship", "航空": "air", "自家用乗用車": "car_private", "自家用バス": "bus_private",
          "ＪＲ定期": "jr_pass", "民鉄定期": "pvt_pass", "全機関": "all"}
# 県庁所在地の観測所（気象庁 地域気象観測所一覧の「観測所名」と「都府県振興局」）
CAP = {"北海道": ("石狩", "札幌"), "青森": ("青森", "青森"), "岩手": ("岩手", "盛岡"), "宮城": ("宮城", "仙台"), "秋田": ("秋田", "秋田"),
       "山形": ("山形", "山形"), "福島": ("福島", "福島"), "茨城": ("茨城", "水戸"), "栃木": ("栃木", "宇都宮"), "群馬": ("群馬", "前橋"),
       "埼玉": ("埼玉", "さいたま"), "千葉": ("千葉", "千葉"), "東京": ("東京", "東京"), "神奈川": ("神奈川", "横浜"), "新潟": ("新潟", "新潟"),
       "富山": ("富山", "富山"), "石川": ("石川", "金沢"), "福井": ("福井", "福井"), "山梨": ("山梨", "甲府"), "長野": ("長野", "長野"),
       "岐阜": ("岐阜", "岐阜"), "静岡": ("静岡", "静岡"), "愛知": ("愛知", "名古屋"), "三重": ("三重", "津"), "滋賀": ("滋賀", "大津"),
       "京都": ("京都", "京都"), "大阪": ("大阪", "大阪"), "兵庫": ("兵庫", "神戸"), "奈良": ("奈良", "奈良"), "和歌山": ("和歌山", "和歌山"),
       "鳥取": ("鳥取", "鳥取"), "島根": ("島根", "松江"), "岡山": ("岡山", "岡山"), "広島": ("広島", "広島"), "山口": ("山口", "山口"),
       "徳島": ("徳島", "徳島"), "香川": ("香川", "高松"), "愛媛": ("愛媛", "松山"), "高知": ("高知", "高知"), "福岡": ("福岡", "福岡"),
       "佐賀": ("佐賀", "佐賀"), "長崎": ("長崎", "長崎"), "熊本": ("熊本", "熊本"), "大分": ("大分", "大分"), "宮崎": ("宮崎", "宮崎"),
       "鹿児島": ("鹿児島", "鹿児島"), "沖縄": ("沖縄", "那覇")}


def clean(x):
    return str(x).replace("　", "").replace(" ", "").strip() if x is not None else ""


def sheet_rows(f, sh):
    if f.suffix == ".xls":
        s = xlrd.open_workbook(str(f), on_demand=True).sheet_by_name(sh)
        return [s.row_values(i) for i in range(s.nrows)]
    ws = openpyxl.load_workbook(str(f), read_only=True, data_only=True)[sh]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def parse(rows):
    cells, hdr = {}, None
    for r in rows:
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


def distances():
    z = zipfile.ZipFile(RAW / "ame_master.zip")
    name = sorted(n for n in z.namelist() if n.endswith(".csv"))[0]
    d = pd.read_csv(io.BytesIO(z.read(name)), encoding="cp932")
    d["lat"] = d["緯度(度)"] + d["緯度(分)"] / 60
    d["lon"] = d["経度(度)"] + d["経度(分)"] / 60
    pos = {}
    for p, (area, st) in CAP.items():
        s = d[(d["都府県振興局"] == area) & (d["観測所名"] == st)]
        assert len(s) >= 1, p
        pos[p] = (float(s["lat"].iloc[0]), float(s["lon"].iloc[0]))
    rows = []
    for a in PREF:
        for b in PREF:
            if a == b:
                continue
            la1, lo1 = np.radians(pos[a]); la2, lo2 = np.radians(pos[b])
            h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
            rows.append({"orig": a, "dest": b, "km": round(float(2 * 6371.0 * np.arcsin(np.sqrt(h))), 1)})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "data" / "pref_distance.csv", index=False, encoding="utf-8")
    pd.DataFrame([{"pref": p, "station": CAP[p][1], "lat": round(pos[p][0], 4), "lon": round(pos[p][1], 4)} for p in PREF]) \
        .to_csv(ROOT / "data" / "pref_capital_station.csv", index=False, encoding="utf-8")


def main():
    distances()
    recs = []
    files = sorted(RAW.glob("ryokaku_*"))
    for f in files:
        fy = int(re.search(r"ryokaku_(\d{4})_", f.name).group(1))
        names = (xlrd.open_workbook(str(f), on_demand=True).sheet_names() if f.suffix == ".xls"
                 else openpyxl.load_workbook(str(f), read_only=True).sheetnames)
        per = {}
        for sh, key in SHEETS.items():
            if sh not in names:
                continue
            cells = parse(sheet_rows(f, sh))
            n = sum(1 for a in PREF for b in PREF if (a, b) in cells)
            assert n == 47 * 47, (fy, sh, n)
            per[key] = cells
        for a in PREF:
            for b in PREF:
                if a == b:
                    continue
                r = {"fy": fy, "orig": a, "dest": b}
                for key in SHEETS.values():
                    r[key] = per[key][(a, b)] if key in per else np.nan
                recs.append(r)
        print(fy, sorted(per))
    df = pd.DataFrame(recs)
    df.to_csv(ROOT / "data" / "od_wide.csv", index=False, encoding="utf-8", float_format="%.3f")


if __name__ == "__main__":
    main()
