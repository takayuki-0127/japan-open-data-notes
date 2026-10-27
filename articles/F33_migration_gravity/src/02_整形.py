"""都道府県×都道府県×年の移動者数（日本人、1989〜2025年）と、距離・隣接・地方・新幹線の変数を作る。"""
import io, csv, json, re
import numpy as np
import pandas as pd
import geopandas as gpd
from common import RAW, DATA

PREF = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県",
        "新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県",
        "奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県",
        "熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
# 県庁所在地（東京都は都庁のある新宿区）
CAPITAL = ["札幌市","青森市","盛岡市","仙台市","秋田市","山形市","福島市","水戸市","宇都宮市","前橋市","さいたま市","千葉市","新宿区","横浜市",
           "新潟市","富山市","金沢市","福井市","甲府市","長野市","岐阜市","静岡市","名古屋市","津市","大津市","京都市","大阪市","神戸市",
           "奈良市","和歌山市","鳥取市","松江市","岡山市","広島市","山口市","徳島市","高松市","松山市","高知市","福岡市","佐賀市","長崎市",
           "熊本市","大分市","宮崎市","鹿児島市","那覇市"]
# 8地方区分
REGION = {}
for r, ps in {"北海道": [1], "東北": range(2, 8), "関東": range(8, 15), "中部": range(15, 24), "近畿": range(24, 31),
              "中国": range(31, 36), "四国": range(36, 40), "九州・沖縄": range(40, 48)}.items():
    for p in ps:
        REGION[p] = r
# フル規格の新幹線網につながった年（その年の3月までの開業はその年から、4月以降の開業は翌年から数える）
# 九州新幹線の新八代〜鹿児島中央（2004年）は2011年の全線開業まで本州とつながっていないので2011年、
# 西九州新幹線（2022年、武雄温泉〜長崎）は網につながっていないので長崎は含めない
SHINKANSEN = {"東京都": 1964, "神奈川県": 1964, "静岡県": 1964, "愛知県": 1964, "岐阜県": 1964, "滋賀県": 1964, "京都府": 1964,
              "大阪府": 1964, "兵庫県": 1972, "岡山県": 1972, "広島県": 1975, "山口県": 1975, "福岡県": 1975,
              "埼玉県": 1982, "栃木県": 1982, "福島県": 1982, "宮城県": 1982, "岩手県": 1982, "群馬県": 1982, "新潟県": 1982,
              "長野県": 1998, "青森県": 2003, "熊本県": 2011, "鹿児島県": 2011, "佐賀県": 2011,
              "富山県": 2015, "石川県": 2015, "北海道": 2016, "福井県": 2024}
# 頑健性：ミニ新幹線（山形 1992年7月→1993年、秋田 1997年3月→1997年）も含める
MINI = {"山形県": 1993, "秋田県": 1997}


def num(c):
    c = c.strip().replace(",", "")
    return 0 if c in ("", "－", "-", "…", "x", "X") else int(float(c))


raw = json.load(open(RAW / "f33_migration_raw.json", encoding="utf-8"))
recs = []
for y in range(1989, 2026):
    rows = list(csv.reader(io.StringIO(raw[str(y)])))
    hdr = rows[4]
    cols = {j: int(c) for j, c in enumerate(hdr) if re.fullmatch(r"\d\d", c.strip())}
    M = np.zeros((47, 47), int); seen = set(); tot = {}
    for r in rows[5:]:
        c = r[0].strip()
        if re.fullmatch(r"\d\d", c) and 1 <= int(c) <= 47 and int(c) not in seen:
            o = int(c); seen.add(o); tot[o] = num(r[3])
            for j, d in cols.items():
                if 1 <= d <= 47:
                    M[o - 1, d - 1] = num(r[j])
    assert len(seen) == 47, y
    # 各行の合計が「総数」と一致するか（都道府県間の移動だけを数えた表なので一致するはず）
    bad = [o for o in tot if M[o - 1].sum() != tot[o]]
    assert not bad, (y, bad)
    for i in range(47):
        for j in range(47):
            if i != j:
                recs.append((y, i + 1, j + 1, M[i, j]))
flow = pd.DataFrame(recs, columns=["year", "o", "d", "flow"])
print("年ごとの移動者数（日本人、都道府県間）")
print(flow.groupby("year")["flow"].sum().to_string())

# 境界から距離と隣接
g = gpd.read_file(RAW / "N03-21_210101.json").set_crs(4326, allow_override=True)
g = g[g["N03_001"].isin(PREF)].copy()
g["city"] = g["N03_003"].where(g["N03_003"].fillna("").str.endswith("市") & g["N03_004"].fillna("").str.endswith("区"), g["N03_004"])
g.loc[g["N03_001"] == "東京都", "city"] = g.loc[g["N03_001"] == "東京都", "N03_004"]
g = g.to_crs(6677)
cap_pts = []
for p, c in zip(PREF, CAPITAL):
    s = g[(g["N03_001"] == p) & (g["city"] == c)]
    assert len(s) > 0, (p, c)
    cap_pts.append(s.dissolve().representative_point().iloc[0])
pref_g = g.dissolve(by="N03_001").reindex(PREF)
pref_pts = pref_g.representative_point()
cap = gpd.GeoSeries(cap_pts, crs=6677).to_crs(4326)
prp = gpd.GeoSeries(list(pref_pts), crs=6677).to_crs(4326)


def gc(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


xy = pd.DataFrame({"pref": PREF, "cap_lon": cap.x.values, "cap_lat": cap.y.values,
                   "pref_lon": prp.x.values, "pref_lat": prp.y.values})
xy.to_csv(DATA / "pref_points.csv", index=False)

# 隣接：簡略化した境界で、50m のバッファで接していれば隣接とみなす（簡略化のすき間を埋めるため）
buf = pref_g.geometry.buffer(50)
pairs = []
for i in range(47):
    for j in range(47):
        if i == j:
            continue
        adj = int(buf.iloc[i].intersects(buf.iloc[j]))
        pairs.append(dict(o=i + 1, d=j + 1,
                          dist=gc(xy.cap_lon[i], xy.cap_lat[i], xy.cap_lon[j], xy.cap_lat[j]),
                          dist_pref=gc(xy.pref_lon[i], xy.pref_lat[i], xy.pref_lon[j], xy.pref_lat[j]),
                          adj=adj, same_region=int(REGION[i + 1] == REGION[j + 1])))
pairs = pd.DataFrame(pairs)
pairs.to_csv(DATA / "pairs.csv", index=False)
print("隣接ペア（向きなし）:", pairs.adj.sum() // 2)

panel = flow.merge(pairs, on=["o", "d"])
po = {i + 1: p for i, p in enumerate(PREF)}
def conn(y, a, b, table):
    return int(table.get(po[a], 9999) <= y and table.get(po[b], 9999) <= y)
full = dict(SHINKANSEN)
withmini = dict(SHINKANSEN); withmini.update(MINI)
panel["shinkansen"] = [conn(y, a, b, full) for y, a, b in zip(panel.year, panel.o, panel.d)]
panel["shinkansen_mini"] = [conn(y, a, b, withmini) for y, a, b in zip(panel.year, panel.o, panel.d)]
panel["o_name"] = panel.o.map(po)
panel["d_name"] = panel.d.map(po)
panel.to_csv(DATA / "panel.csv", index=False)
print(panel.shape, "新幹線でつながるペアの割合（2025年）:", panel[panel.year == 2025].shinkansen.mean().round(3))
