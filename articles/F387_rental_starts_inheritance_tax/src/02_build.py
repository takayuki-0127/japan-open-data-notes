"""02 整形（オフライン）：建築着工統計の都道府県別の表（1988〜2025年）から、利用関係×構造×建て方の戸数を縦長の CSV にする。
出力：data/starts_pref.csv（利用関係ごとの合計＝構造・建て方の「計」と、貸家の構造×建て方）、data/national_tenure.csv（全国の時系列表、照合用）"""
import pathlib, re
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


def main():
    b = xlrd.open_workbook(RAW / "starts_pref_tenure_struct_type_annual.xls")
    recs = []
    for sh in b.sheets():
        y = wareki(sh.name)
        assert f"{Z(sh.name).replace('年', '')}年計" in Z(sh.cell_value(2, 0)), sh.name
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
                        recs.append((y, area, tn, st, ty, num(sh.cell_value(r0 + j, 2 + 8 * k + 2 * t))))
    d = pd.DataFrame(recs, columns=["year", "area", "tenure", "struct", "type", "units"])
    # 足し算の確かめ：47都道府県の合計＝全国、構造・建て方・利用関係の合計＝計
    key = ["year", "tenure", "struct", "type"]
    ps = d[d.area != "全国"].groupby(key).units.sum()
    nat = d[d.area == "全国"].set_index(key).units
    assert (ps - nat).abs().max() < 1e-6
    g = d.set_index(["year", "area", "tenure", "struct", "type"]).units
    for lev in ("struct", "type", "tenure"):
        s = g.drop("計", level=lev).groupby([n for n in g.index.names if n != lev]).sum()
        t = g.xs("計", level=lev)
        assert (s - t.reindex(s.index)).abs().max() < 1e-6, lev
    d["units"] = d.units.astype("int64")
    keep = ((d.struct == "計") & (d.type == "計")) | (d.tenure == "貸家")
    d[keep].sort_values(["year", "area", "tenure", "struct", "type"], kind="stable").to_csv(DATA / "starts_pref.csv", index=False)

    # 全国の時系列表（照合用）
    s = xlrd.open_workbook(RAW / "starts_tenure_national_annual.xls").sheet_by_index(0)
    assert Z(s.cell_value(3, 3)) == "持家" and Z(s.cell_value(3, 5)) == "貸家" and Z(s.cell_value(3, 9)) == "分譲住宅"
    rows = []
    for r in range(7, s.nrows):
        lab = Z(s.cell_value(r, 0))
        if lab == "":
            break
        if re.match(r"(昭和|平成|令和)", lab):
            y = wareki(lab)
        else:
            y = rows[-1]["year"] + 1
        rows.append({"year": y, "total": num(s.cell_value(r, 1)), "owner": num(s.cell_value(r, 3)), "rental": num(s.cell_value(r, 5)),
                     "company": num(s.cell_value(r, 7)), "forsale": num(s.cell_value(r, 9))})
    n = pd.DataFrame(rows)
    assert list(n.year) == list(range(1948, 2026)), (n.year.min(), n.year.max(), len(n))
    n = n[n.year >= 1988].astype("int64")
    n.to_csv(DATA / "national_tenure.csv", index=False)
    # 照合：都道府県の表の全国＝時系列表
    chk = d[(d.area == "全国") & (d.struct == "計") & (d.type == "計")].pivot(index="year", columns="tenure", values="units")
    nn = n.set_index("year")
    for a, b2 in (("計", "total"), ("持家", "owner"), ("貸家", "rental"), ("分譲住宅", "forsale")):
        diff = (chk[a] - nn[b2]).abs()
        assert (diff / nn[b2]).max() < 1e-3, (a, diff[diff > 0])
    print("ok", d[keep].shape, n.shape)


if __name__ == "__main__":
    main()
