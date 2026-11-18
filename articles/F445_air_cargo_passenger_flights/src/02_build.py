"""data/raw の年報 Excel（統計表2・5）から、月別の長い表を作る（オフライン）。
出力：data/domestic_monthly.csv（総合計・幹線・ローカル線）、data/intl_monthly.csv"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
YEARS = range(2014, 2026)


def path(y, t):
    for ext in ("xlsx", "xls"):
        p = RAW / f"air_{y}_{t}.{ext}"
        if p.exists():
            return p
    raise FileNotFoundError(y, t)


def num(v):
    if isinstance(v, str):
        v = v.replace(",", "").strip()
        if v in ("", "-", "－"):
            return float("nan")
    return float(v)


# 統計表2：列の位置（2014〜2025年で同じことを 02 の中で確かめる）
D_COLS = {2: "flights", 5: "pax", 6: "seats", 7: "pkm", 8: "seat_km", 10: "cargo_kg", 12: "mail_kg",
          14: "cargo_tkm", 16: "mail_tkm"}
I_COLS = {1: "flights", 4: "pax", 5: "pkm_k", 6: "seat_km_k", 8: "cargo_kg", 10: "mail_kg",
          13: "cargo_tkm_k", 15: "mail_tkm_k", 17: "atk_k", 18: "load_factor_w"}


def check_header(x, cols, words):
    for c, w in words.items():
        s = "".join(str(x.iloc[r, c]) for r in (2, 3)).replace("\n", "").replace(" ", "").replace("　", "")
        assert w in s, (c, w, s)


rows_d, rows_i = [], []
for y in YEARS:
    x = pd.read_excel(path(y, "t2"), header=None)
    check_header(x, D_COLS, {5: "旅客数", 8: "座席キロ", 10: "貨物", 12: "郵便", 14: "貨物"})
    blocks = {"total": None, "trunk": None, "local": None}
    for i in range(len(x)):
        s = str(x.iloc[i, 0]).replace(" ", "").replace("　", "")
        if s == "総合計":
            blocks["total"] = i
        elif s == "幹線計":
            blocks["trunk"] = i
        elif s == "ローカル線計":
            blocks["local"] = i
    for seg, i0 in blocks.items():
        assert i0 is not None, (y, seg)
        for m in range(1, 13):
            r = i0 + m
            assert num(x.iloc[r, 0]) == m, (y, seg, m, x.iloc[r, 0])
            d = {"year": y, "month": m, "segment": seg}
            d.update({k: num(x.iloc[r, c]) for c, k in D_COLS.items()})
            rows_d.append(d)
    z = pd.read_excel(path(y, "t5"), header=None)
    check_header(z, I_COLS, {4: "旅客数", 6: "座席キロ", 8: "貨物", 10: "郵便", 17: "利用可能"})
    for m in range(1, 13):
        r = 3 + m
        assert num(z.iloc[r, 0]) == m, (y, m, z.iloc[r, 0])
        d = {"year": y, "month": m}
        d.update({k: num(z.iloc[r, c]) for c, k in I_COLS.items()})
        rows_i.append(d)

dom = pd.DataFrame(rows_d).sort_values(["segment", "year", "month"]).reset_index(drop=True)
intl = pd.DataFrame(rows_i).sort_values(["year", "month"]).reset_index(drop=True)
# 総合計 = 幹線 + ローカル線 の確かめ（貨物重量、座席キロ）
w = dom.pivot_table(index=["year", "month"], columns="segment", values=["cargo_kg", "seat_km"])
for v in ("cargo_kg", "seat_km"):
    diff = (w[(v, "trunk")] + w[(v, "local")] - w[(v, "total")]).abs() / w[(v, "total")]
    assert diff.max() < 0.001, (v, diff.max())
dom.to_csv(ROOT / "data" / "domestic_monthly.csv", index=False, float_format="%.1f")
intl.to_csv(ROOT / "data" / "intl_monthly.csv", index=False, float_format="%.2f")
print("domestic", dom.shape, "intl", intl.shape)
