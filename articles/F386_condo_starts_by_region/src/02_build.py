"""02 整形（オフライン）：建築着工統計の都道府県別の表（1988〜2025年）から、利用関係×構造×建て方ごとの
戸数・床面積を縦長の CSV にする。全国の時系列表（分譲住宅のうちマンション・一戸建）も CSV にする。
出力：data/starts_pref_long.csv（分譲住宅と住宅全体の行だけ）、data/national_tenure.csv"""
import pathlib
import re

import pandas as pd
import xlrd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
STRUCT = ["計", "木造", "鉄骨鉄筋コンクリート造", "鉄筋コンクリート造", "鉄骨造", "コンクリートブロック造", "その他"]
TYPE = ["計", "一戸建", "長屋建", "共同住宅"]
TENURE = ["計", "持家", "貸家", "給与住宅", "分譲住宅"]
Z = lambda x: re.sub(r"[\s　]", "", str(x))


def num(x):
    if isinstance(x, (int, float)):
        return float(x)
    s = Z(x).replace(",", "")
    return 0.0 if s in ("", "-", "－", "‐") else float(s)


def wareki(name):
    s = Z(name).replace("年", "")
    for era, base in (("昭和", 1925), ("平成", 1988), ("令和", 2018)):
        if s.startswith(era):
            k = s[len(era):]
            k = "1" if k == "元" else k.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
            return base + int(k)
    raise ValueError(name)


b = xlrd.open_workbook(RAW / "starts_pref_tenure_struct_type_annual.xls")
recs = []
for sh in b.sheets():
    y = wareki(sh.name)
    assert f"{Z(sh.name).replace('年', '')}年計" in Z(sh.cell_value(2, 0)), sh.name
    # 見出しの確かめ
    for k, st in enumerate(STRUCT):
        h = Z(sh.cell_value(3, 2 + 8 * k))
        assert h[:2] == ("総計"[:2] if st == "計" else st[:2]), (y, k, h)
        for t, ty in enumerate(TYPE):
            assert Z(sh.cell_value(4, 2 + 8 * k + 2 * t)) == ty, (y, k, t)
    for p in range(48):  # 0 は全国
        r0 = 8 + 6 * p
        head = Z(sh.cell_value(r0, 0)) + Z(sh.cell_value(r0 + 4, 0))
        area = "全国" if p == 0 else PREFS[p - 1]
        assert head[0] == area[0], (y, p, head)
        for j, tn in enumerate(TENURE):
            assert Z(sh.cell_value(r0 + j, 1)) == tn, (y, p, j)
            for k, st in enumerate(STRUCT):
                for t, ty in enumerate(TYPE):
                    c = 2 + 8 * k + 2 * t
                    recs.append((y, area, tn, st, ty, num(sh.cell_value(r0 + j, c)), num(sh.cell_value(r0 + j, c + 1))))
d = pd.DataFrame(recs, columns=["year", "area", "tenure", "struct", "type", "units", "floor_m2"])
# 足し算の確かめ：47都道府県の合計＝全国、構造の合計＝計、建て方の合計＝計、利用関係の合計＝計
key = ["year", "tenure", "struct", "type"]
pref_sum = d[d.area != "全国"].groupby(key)[["units", "floor_m2"]].sum()
nat = d[d.area == "全国"].set_index(key)[["units", "floor_m2"]]
assert (pref_sum - nat).abs().max().max() < 1e-6
g = d.set_index(["year", "area", "tenure", "struct", "type"])["units"]
for lev, tot in (("struct", "計"), ("type", "計"), ("tenure", "計")):
    s = g.drop(tot, level=lev).groupby([n for n in g.index.names if n != lev]).sum()
    t = g.xs(tot, level=lev)
    assert (s - t.reindex(s.index)).abs().max() < 1e-6, lev
d = d.astype({"units": "int64", "floor_m2": "int64"})
# 使う行だけを残す：分譲住宅の全構造×全建て方と、すべての住宅の合計（利用関係・構造・建て方の計）
keep = (d.tenure == "分譲住宅") | ((d.tenure == "計") & (d.struct == "計") & (d.type == "計"))
d[keep].to_csv(DATA / "starts_pref_long.csv", index=False)

# 全国の時系列表（1988〜2025年の分譲・マンション・一戸建）
s = xlrd.open_workbook(RAW / "starts_tenure_national_annual.xls").sheet_by_index(0)
assert "うちマンション" in Z(s.cell_value(4, 11)) and "うち一戸建" in Z(s.cell_value(4, 13))
rows, y = [], None
for r in range(7, s.nrows):
    lab = Z(s.cell_value(r, 0))
    if lab == "":
        break
    y = wareki(lab + "年") if not re.fullmatch(r"[\d.]+", lab) and not re.fullmatch(r"[０-９]+", lab) else None
    if y is None:
        v = lab.replace(".0", "").translate(str.maketrans("０１２３４５６７８９", "0123456789"))
        prev = rows[-1]["year"]
        era_base = 1925 if prev < 1989 else (1988 if prev < 2019 else 2018)
        y = era_base + int(v)
        if y != prev + 1:  # 元号が変わった直後の「2」など
            raise ValueError((r, lab, prev))
    rows.append({"year": y, "all_units": num(s.cell_value(r, 1)), "bunjo_units": num(s.cell_value(r, 9)), "bunjo_floor": num(s.cell_value(r, 10)),
                 "mansion_units": num(s.cell_value(r, 11)), "mansion_floor": num(s.cell_value(r, 12)),
                 "detached_units": num(s.cell_value(r, 13)), "detached_floor": num(s.cell_value(r, 14))})
n = pd.DataFrame(rows)
assert list(n.year) == list(range(1948, 2026)), (n.year.min(), n.year.max())
n = n[n.year >= 1985].astype("int64")
n.to_csv(DATA / "national_tenure.csv", index=False)
d = d[keep]
# 定義の確かめ：都道府県の表の「分譲×共同住宅×(SRC+RC+S)」の全国＝時系列表の「うちマンション」
m = d[(d.area == "全国") & (d.tenure == "分譲住宅") & (d.type == "共同住宅") & d.struct.isin(["鉄骨鉄筋コンクリート造", "鉄筋コンクリート造", "鉄骨造"])]
m = m.groupby("year")[["units", "floor_m2"]].sum()
chk = n.set_index("year").loc[m.index]
# 2008年だけ、時系列表のほうが9戸（床面積203㎡）多い（0.005%）。表の作り方の違いとみて、差の小ささだけを確かめる
du = (m.units - chk.mansion_units).abs()
assert (du / chk.mansion_units).max() < 1e-4 and set(du[du > 0].index) <= {2008}, du[du > 0]
assert ((m.floor_m2 - chk.mansion_floor).abs() / chk.mansion_floor).max() < 1e-4
print("ok", d.shape, n.shape)
