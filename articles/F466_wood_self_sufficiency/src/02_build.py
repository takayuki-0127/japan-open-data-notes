"""木材需給表 長期累年の Excel を読み、列の名前を見出しの文字（結合セルを広げた複数行）から付けて CSV にする。
列の順ではなく見出しで読むことを、合計の一致と公表の自給率との一致で確かめる。"""
import pathlib, re
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)


def read(name):
    ws = openpyxl.load_workbook(RAW / name, data_only=True).worksheets[0]
    grid = [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)] for r in range(1, ws.max_row + 1)]
    for mr in ws.merged_cells.ranges:  # 結合セルは左上の値で埋める
        v = ws.cell(mr.min_row, mr.min_col).value
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                grid[r - 1][c - 1] = v
    top = next(i for i, row in enumerate(grid) if row[0] == "年次")
    unit = next(i for i, row in enumerate(grid) if i > top and any(isinstance(x, str) and "千" in x for x in row[1:]))
    names = []
    for c in range(1, ws.max_column):
        parts = []
        for r in range(top, unit):
            v = grid[r][c]
            if v is None: continue
            v = re.sub(r"\s+", "", str(v))
            if not parts or parts[-1] != v: parts.append(v)
        names.append("/".join(parts))
    recs = []
    for row in grid[unit + 1:]:
        m = re.search(r"\((\d{4})\)", str(row[0] or ""))
        if not m: continue
        rec = {"year": int(m.group(1))}
        for n, v in zip(names, row[1:]):
            rec[n] = float(v) if isinstance(v, (int, float)) else None
        recs.append(rec)
    return pd.DataFrame(recs), names


tot, n_tot = read("mokuzai_jukyu_ruinen_total.xlsx")
sup, n_sup = read("mokuzai_jukyu_ruinen_supply.xlsx")
dem, n_dem = read("mokuzai_jukyu_ruinen_demand.xlsx")
pd.DataFrame({"table": ["total"] * len(n_tot) + ["supply"] * len(n_sup) + ["demand"] * len(n_dem),
              "column_from_headers": n_tot + n_sup + n_dem}).to_csv(RES / "build_header_map.csv", index=False)

USES = {"製材用": "seizai", "合板用": "gouhan", "パルプ・チップ用": "pulp", "その他用": "sonota"}


def pick(df, names, *keys):
    """見出しの文字に keys がすべて（この順で）入る列を1つだけ選ぶ"""
    hit = [n for n in names if all(k in n.split("/") for k in keys) and len(n.split("/")) == len(keys)]
    if len(hit) != 1: raise SystemExit(f"見出しが一意でない: {keys} -> {hit}")
    return df[hit[0]]


rows = pd.DataFrame({"year": tot.year})
rows["total"] = pick(tot, n_tot, "総需要(供給)量")
for side, lab in [("dom", "国内生産"), ("imp", "輸入")]:
    for u, k in USES.items():
        rows[f"{side}_{k}"] = pick(tot, n_tot, "供給先別", lab, "用材", u)
    rows[f"{side}_youzai"] = pick(tot, n_tot, "供給先別", lab, "用材", "小計")
    rows[f"{side}_nenryo"] = pick(tot, n_tot, "供給先別", lab, "燃料材(薪炭材)")
    rows[f"{side}_total"] = pick(tot, n_tot, "供給先別", lab, "計")
rows["dom_shiitake"] = pick(tot, n_tot, "供給先別", "国内生産", "しいたけ原木")
rows["ss_youzai_pub"] = pick(tot, n_tot, "自給率", "用材")
rows["ss_total_pub"] = pick(tot, n_tot, "自給率", "総数")
# 輸入の丸太・製品の別（供給量累年統計）
rows["imp_maruta"] = pick(sup, n_sup, "輸入", "丸太").values
for lab, k in [("製材品等", "seizaihin"), ("合板等", "gouhanhin"), ("木材パルプ", "pulphin"), ("木材チップ等", "chiphin"), ("その他", "sonotahin")]:
    rows[f"imp_prod_{k}"] = pick(sup, n_sup, "輸入", "木材製品", lab).values
rows["imp_prod_total"] = pick(sup, n_sup, "輸入", "木材製品", "小計").values
rows["imp_nenryo_sup"] = pick(sup, n_sup, "輸入", "燃料材(薪炭材)").values
rows["export_total"] = pick(dem, n_dem, "輸出", "計").values
assert (sup.year.values == tot.year.values).all() and (dem.year.values == tot.year.values).all()
rows = rows.fillna(0.0)  # 「…」（数字なし）は0として扱う（初期の年の燃料材の輸入など）
rows.to_csv(OUT / "wood_national.csv", index=False)

# 点検：合計の一致、公表の自給率との一致
chk = []
y = rows
for side in ["dom", "imp"]:
    s = sum(y[f"{side}_{k}"] for k in USES.values())
    chk.append((f"{side}: 用材の4用途の和＝用材小計（最大の差、千m3）", float((s - y[f"{side}_youzai"]).abs().max())))
d = y.dom_youzai + y.dom_shiitake + y.dom_nenryo
chk.append(("国内生産：用材＋しいたけ原木＋燃料材＝計（最大の差）", float((d - y.dom_total).abs().max())))
m = y.imp_youzai + y.imp_nenryo
chk.append(("輸入：用材＋燃料材＝計（最大の差）", float((m - y.imp_total).abs().max())))
chk.append(("国内生産計＋輸入計＝総需要量（最大の差）", float((y.dom_total + y.imp_total - y.total).abs().max())))
chk.append(("輸入：丸太＋製品＋燃料材＝輸入計（供給量累年統計、最大の差）", float((y.imp_maruta + y.imp_prod_total + y.imp_nenryo_sup - y.imp_total).abs().max())))
chk.append(("輸入の燃料材：2つの表の値の最大の差", float((y.imp_nenryo_sup - y.imp_nenryo).abs().max())))
ss = 100 * y.dom_total / y.total
chk.append(("自給率（総数）：計算値と表の値の最大の差（ポイント）", float((ss.round(1) - y.ss_total_pub).abs().max())))
ssy = 100 * y.dom_youzai / (y.dom_youzai + y.imp_youzai)
chk.append(("自給率（用材）：計算値と表の値の最大の差（ポイント）", float((ssy.round(1) - y.ss_youzai_pub).abs().max())))
chk.append(("年の数", float(len(y))))
pd.DataFrame(chk, columns=["check", "value"]).to_csv(RES / "build_checks.csv", index=False)
print(pd.DataFrame(chk))
