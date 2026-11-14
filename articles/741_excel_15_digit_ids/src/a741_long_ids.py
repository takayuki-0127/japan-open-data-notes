"""741 16桁以上の番号を Excel で開くと、何件の番号が別の値に変わり、何件が同じ番号になるのか

架空の注文番号（カード番号ではない）。形は2通り。
  16桁：日付8桁＋店3桁＋その日の連番5桁
  18桁：日付8桁＋店4桁＋その日の連番6桁
各5万件。Excel は数を有効数字15桁で持ち、16桁目から先を0にする（ここでは Python でこの動きを再現。Excel では未検証）。
あわせて、pandas などで小数（float64）として読んだ場合（有効数字は約15〜17桁で、丸め方が違う）と、文字として読んだ場合を比べる。
DuckDB（1スレッド）で文字・BIGINT・DOUBLE に読んだ結果と、Python の結果の一致を確かめる。
"""
import json
from decimal import Decimal
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の注文番号（作成者が乱数で作成、seed 741）"
rng = np.random.default_rng(741)
DATA.mkdir(exist_ok=True)
N = 50000


def make(kind):
    days = pd.date_range("2025-04-01", periods=30).strftime("%Y%m%d").to_numpy()
    d = rng.choice(days, N); shop = rng.integers(1, 300 if kind == 16 else 3000, N)
    df = pd.DataFrame({"d": d, "shop": shop}).sort_values(["d", "shop"], kind="stable")
    df["seq"] = df.groupby(["d", "shop"]).cumcount() + 1 + rng.integers(0, 50, len(df))
    if kind == 16:
        no = df.d + df.shop.map("{:03d}".format) + df.seq.map("{:05d}".format)
    else:
        no = df.d + df.shop.map("{:04d}".format) + df.seq.map("{:06d}".format)
    no = no.drop_duplicates()
    assert no.str.len().eq(kind).all()
    return pd.DataFrame({"order_no": no.to_numpy(), "amount": rng.integers(500, 30000, len(no))})


def excel15(s):
    """有効数字15桁で残し、16桁目から先を0にする（Excel の動きの再現）"""
    return s[:15] + "0" * (len(s) - 15) if len(s) > 15 else s


con = duckdb.connect(); con.execute("SET threads=1")
q = "\n".join(l for l in (SQL / "02_read_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
rows, ex = [], {}
for kind in [16, 18]:
    D = make(kind); path = DATA / f"orders_{kind}.csv"; D.to_csv(path, index=False)
    t = D.order_no
    xl = t.map(excel15)
    fl = t.map(lambda s: format(Decimal(float(s)), "f").split(".")[0])
    r = dict(digits=kind, n=len(t), distinct_text=t.nunique(),
             excel_changed=int((xl != t).sum()), excel_distinct=xl.nunique(),
             excel_lost=int(t.nunique() - xl.nunique()),
             excel_rows_in_dup=int(xl.duplicated(keep=False).sum()),
             excel_max_group=int(xl.value_counts().max()),
             float_changed=int((fl != t).sum()), float_distinct=fl.nunique(),
             float_rows_in_dup=int(fl.duplicated(keep=False).sum()),
             excel_amount_groups_merged=int((D.groupby(xl).amount.size() > 1).sum()))
    dd = con.execute(q, [str(path)]).df().iloc[0]
    assert int(dd.distinct_text) == r["distinct_text"] == int(dd.distinct_bigint)
    assert int(dd.distinct_double) == r["float_distinct"] and int(dd.changed_by_double) == r["float_changed"]
    r["duckdb_distinct_double"] = int(dd.distinct_double)
    rows.append(r)
    ex[kind] = [dict(original=a, excel=b, float64=c) for a, b, c in zip(t.head(3), xl.head(3), fl.head(3))]
    if kind == 18:
        D18, xl18 = D, xl
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
out = {"rows_each": N, "by_digits": rows, "examples": ex, "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a741_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# 図1：変わった番号と、同じ番号に重なった行
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(2); w = .25
for j, (c, l, colr) in enumerate([("excel_changed", "Excel（15桁）で値が変わった", ORANGE), ("excel_rows_in_dup", "Excel で他と同じ番号になった行", BLUE), ("float_changed", "小数（float64）で値が変わった", LIGHT)]):
    b = ax.bar(x + (j - 1) * w, S[c], w, color=colr, label=l)
    for bb in b:
        ax.text(bb.get_x() + w / 2, bb.get_height() + 600, f"{int(bb.get_height()):,}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{d}桁の番号（{n:,}件）" for d, n in zip(S.digits, S.n)])
ax.set_ylabel("件数"); ax.set_ylim(0, S.n.max() * 1.25); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("16桁以上の番号は、Excel で開くと末尾が0になり、別の番号と重なる")
save(fig, "a741_changed.png", SRC)

# 図2：例（18桁）
fig, ax = plt.subplots(figsize=(9, 4.2)); ax.axis("off")
ax.text(0, 1, "18桁の番号の例", fontsize=13, weight="bold", va="top")
ax.text(0, .86, "元の番号", fontsize=10, color=GRAY, va="top"); ax.text(.36, .86, "Excel（15桁で再現）", fontsize=10, color=GRAY, va="top"); ax.text(.70, .86, "小数（float64）", fontsize=10, color=GRAY, va="top")
yy = .74
grp = xl18.value_counts().idxmax()
sample = D18.order_no[xl18 == grp].head(4)
for s in sample:
    ax.text(0, yy, s, fontsize=12, family="monospace", va="top"); ax.text(.36, yy, excel15(s), fontsize=12, family="monospace", va="top", color=ORANGE)
    ax.text(.70, yy, format(Decimal(float(s)), "f").split(".")[0], fontsize=12, family="monospace", va="top", color=BLUE); yy -= .13
ax.text(0, .12, f"Excel では、元は別の{int((xl18 == grp).sum())}つの番号が同じ番号になる（16桁目から先が0になる。4つまで表示）", fontsize=10, va="top")
save(fig, "a741_examples.png", SRC)

# 図3：重なった番号のまとまりの大きさ（18桁）
fig, ax = plt.subplots(figsize=(9, 4.6))
vc = xl18.value_counts().value_counts().sort_index()
ax.bar(vc.index.astype(str), vc.values, color=ORANGE)
for i, v in zip(range(len(vc)), vc.values):
    ax.text(i, v * 1.02 + 5, f"{v:,}", ha="center", fontsize=9)
ax.set_xlabel("Excel の番号1つに重なった元の番号の数"); ax.set_ylabel("Excel の番号の数")
ax.set_title(f"18桁：{S.n[1]:,}件が {S.excel_distinct[1]:,} 種類の番号にまとまった")
save(fig, "a741_groups.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
