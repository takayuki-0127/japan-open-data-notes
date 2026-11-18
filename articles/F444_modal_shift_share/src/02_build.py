"""data/raw の Excel から、年度の表と月の表を作る（オフライン）。
単位：トンキロは百万トンキロ、トンは千トン。
出力：data/annual_fy.csv、data/monthly.csv"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def num(v):
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if v in ("", "-", "－", "…"):
            return float("nan")
    return float(v)


def norm(s):
    return re.sub(r"[\s　\n]", "", str(s))


# ---------- 自動車（総括表（１）トン、（２）トンキロ）----------
def truck_file(kind, y):
    x = pd.read_excel(RAW / f"truck_{kind}_{y}04.xlsx", header=None)
    assert "合計" in norm(x.iloc[3, 2]) and "営業用" in norm(x.iloc[3, 4]), (kind, y)
    rows = []
    for i in range(8, len(x)):
        code = x.iloc[i, 1]
        if pd.isna(code) or not str(code).strip().isdigit():
            continue
        c = str(code).strip()
        rows.append({"code": c, "total": num(x.iloc[i, 2]), "comm": num(x.iloc[i, 4])})
    return pd.DataFrame(rows)


tr_ann, tr_mon = {}, {}
for kind in ("ton", "tonkm"):
    for y in range(2021, 2027):
        d = truck_file(kind, y)
        for _, r in d.iterrows():
            c = r.code
            if c.endswith("000000"):  # 年度
                if y == 2026:
                    tr_ann[(int(c[:4]), kind)] = (r.total, r.comm)
            else:  # 月：yyyy00mmmm
                ym = (int(c[:4]), int(c[-2:]))
                tr_mon[(ym, kind)] = (r.total, r.comm)  # 後の年の版で上書き

# ---------- 鉄道 ----------
rail_ann, rail_mon = {}, {}
for fy in range(2020, 2025):
    x = pd.read_excel(RAW / f"rail_{fy}_tkm.xls", header=None)
    assert "全国計" in norm(x.iloc[3, 1]) and "コンテナ" in norm(x.iloc[3, 3]), fy
    for i in range(5, len(x)):
        lab = norm(x.iloc[i, 0])
        m = re.match(r"^(\d{4})年度$", lab)
        if m:
            rail_ann[int(m.group(1))] = {"rail_tkm": num(x.iloc[i, 1]) / 1000, "rail_cont_tkm": num(x.iloc[i, 3]) / 1000}
            continue
        v = x.iloc[i, 0]
        if isinstance(v, pd.Timestamp) or hasattr(v, "year"):
            ym = (v.year, v.month)
        else:
            m = re.match(r"^(\d{4})年(\d{1,2})月$", lab)
            if not m:
                continue
            ym = (int(m.group(1)), int(m.group(2)))
        rail_mon[ym] = {"rail_tkm": num(x.iloc[i, 1]) / 1000, "rail_cont_tkm": num(x.iloc[i, 3]) / 1000}
xm = pd.read_excel(RAW / "rail_m202603.xlsx", sheet_name=None, header=None)
rail_ton_ann = {}
for sheet, key in (("貨物トンキロ（機械判読用）", "tkm"), ("貨物数量（機械判読用）", "ton")):
    x = xm[sheet]
    assert "全国計" in norm(x.iloc[3, 1]) and "コンテナ" in norm(x.iloc[3, 3])
    for i in range(5, len(x)):
        lab = norm(x.iloc[i, 0])
        m = re.match(r"^(\d{4})年度$", lab)
        if m:
            fy = int(m.group(1))
            if key == "ton":
                rail_ton_ann[fy] = {"rail_ton": num(x.iloc[i, 1]) / 1000, "rail_cont_ton": num(x.iloc[i, 3]) / 1000}
            elif fy not in rail_ann:
                rail_ann[fy] = {"rail_tkm": num(x.iloc[i, 1]) / 1000, "rail_cont_tkm": num(x.iloc[i, 3]) / 1000}
            continue
        m = re.match(r"^(\d{4})年(\d{1,2})月$", lab)
        if m:
            ym = (int(m.group(1)), int(m.group(2)))
            d = rail_mon.setdefault(ym, {}) if key == "tkm" else None
            if key == "tkm":
                d.update({"rail_tkm": num(x.iloc[i, 1]) / 1000, "rail_cont_tkm": num(x.iloc[i, 3]) / 1000})
            else:
                rail_mon.setdefault(ym, {}).update({"rail_ton": num(x.iloc[i, 1]) / 1000, "rail_cont_ton": num(x.iloc[i, 3]) / 1000})
# 2025年度は月の合計（2025年4月〜2026年3月）
mons25 = [(2025, m) for m in range(4, 13)] + [(2026, m) for m in range(1, 4)]
rail_ann[2025] = {k: sum(rail_mon[ym][k] for ym in mons25) for k in ("rail_tkm", "rail_cont_tkm")}
rail_ton_ann[2025] = {k: sum(rail_mon[ym][k] for ym in mons25) for k in ("rail_ton", "rail_cont_ton")}

# ---------- 内航 ----------
ship_ann, ship_mon, unit_ann = {}, {}, {}
for fy in range(2015, 2026):
    x = pd.read_excel(RAW / f"ship_{fy}_t1.xls", header=None)
    assert "営業用計" in norm(x.iloc[3, 5]), fy
    last = None
    for i in range(6, len(x)):
        lab = norm(x.iloc[i, 0])
        m = re.match(r"^(\d{2})(?:\((\d{4})\))?$", lab)
        if m and not pd.isna(x.iloc[i, 1]):
            yy = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else 1988 + yy  # かっこの西暦がない行は平成（2025年度版では2005・2006年度だけ）
            last = i
            if fy == 2025:
                ship_ann[year] = {"ship_ton": num(x.iloc[i, 1]), "ship_tkm": num(x.iloc[i, 3])}
    # 月：年度の行のあとの空行の次から12行（4月〜翌年3月）
    j = last + 1
    while pd.isna(x.iloc[j, 5]):
        j += 1
    assert norm(x.iloc[j, 0]).endswith(".4") and norm(x.iloc[j + 9, 0]).endswith(".1"), (fy, x.iloc[j, 0])
    for k in range(12):
        mth = 4 + k if k < 9 else k - 8
        yr = fy if k < 9 else fy + 1
        ship_mon[(yr, mth)] = {"ship_comm_ton": num(x.iloc[j + k, 5]), "ship_comm_tkm": num(x.iloc[j + k, 6])}
    z = pd.read_excel(RAW / f"ship_{fy}_t5.xls", header=None)
    assert "ＲＯＲＯ船" in norm(z.iloc[3, 19]) and "コンテナ専用船" in norm(z.iloc[3, 13]) and norm(z.iloc[6, 1]) == "合計", fy
    unit_ann[fy] = {"bigsteel_ton": num(z.iloc[6, 5]) / 1000, "bigsteel_tkm": num(z.iloc[6, 6]) / 1e6,
                    "contship_ton": num(z.iloc[6, 13]) / 1000, "contship_tkm": num(z.iloc[6, 14]) / 1e6,
                    "roro_ton": num(z.iloc[6, 19]) / 1000, "roro_tkm": num(z.iloc[6, 20]) / 1e6}
# 推移表の和暦の年度の読み：2025年度版は「07(2025)」の形で西暦が入る。確かめ
assert abs(ship_ann[2015]["ship_tkm"] - 180381) < 1 and abs(ship_ann[2025]["ship_tkm"] - 147574) < 1

# ---------- 年度の表 ----------
rows = []
for fy in range(2015, 2026):
    d = {"fy": fy}
    d["truck_ton"], d["truck_comm_ton"] = tr_ann[(fy, "ton")]
    d["truck_tkm"], d["truck_comm_tkm"] = tr_ann[(fy, "tonkm")]
    d.update(rail_ann[fy]); d.update(rail_ton_ann.get(fy, {"rail_ton": float("nan"), "rail_cont_ton": float("nan")}))
    d.update(ship_ann[fy]); d.update(unit_ann[fy])
    rows.append(d)
ann = pd.DataFrame(rows)
# 月の合計と年度の値の照合（自動車 2020〜2025年度、内航の営業用は年度の表の営業用と別ファイルなので照合しない）
for fy in range(2020, 2026):
    ms = [(fy, m) for m in range(4, 13)] + [(fy + 1, m) for m in range(1, 4)]
    s = sum(tr_mon[(ym, "tonkm")][0] for ym in ms)
    assert abs(s / ann.loc[ann.fy == fy, "truck_tkm"].item() - 1) < 0.002, (fy, s)
ann.to_csv(ROOT / "data" / "annual_fy.csv", index=False, float_format="%.3f")

# ---------- 月の表（2020年4月〜2026年3月）----------
rows = []
for y in range(2020, 2027):
    for m in range(1, 13):
        if (y, m) < (2020, 4) or (y, m) > (2026, 3):
            continue
        d = {"year": y, "month": m, "fy": y if m >= 4 else y - 1}
        d["truck_tkm"], d["truck_comm_tkm"] = tr_mon[((y, m), "tonkm")]
        d["truck_ton"], d["truck_comm_ton"] = tr_mon[((y, m), "ton")]
        d["rail_tkm"] = rail_mon[(y, m)]["rail_tkm"]; d["rail_cont_tkm"] = rail_mon[(y, m)]["rail_cont_tkm"]
        d.update(ship_mon[(y, m)])
        rows.append(d)
mon = pd.DataFrame(rows)
# 前年同月比を出すため、2019年4月〜2020年3月の内航・鉄道は使わない（自動車の月がないため、月の表は2020年4月から）
mon.to_csv(ROOT / "data" / "monthly.csv", index=False, float_format="%.3f")
print(ann.round(1).to_string()); print(mon.shape)
