"""02 整形（オフライン）：家計調査 第4-6表・第4-3表（2015〜2025年）からレジャー・娯楽サービスの品目を取り出し、
消費者物価指数（品目別、年平均）とあわせて縦長の CSV にする。
出力：data/leisure_items.csv（年・区分（年齢／収入五分位）・品目・支出金額・購入頻度）、data/cpi_leisure.csv"""
import glob, pathlib, re, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import kakei_parse as K

RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
CODES = {"9.4": "教養娯楽サービス", "9.4.1": "宿泊料", "861": "国内パック旅行費", "862": "外国パック旅行費", "882": "映画・演劇等入場料",
         "883": "スポーツ観覧料", "878": "スポーツクラブ使用料", "881": "他のスポーツ施設使用料", "884": "文化施設入場料",
         "886": "遊園地入場・乗物代", "885": "他の入場・ゲーム代"}
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_4-*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    tab = "age" if "4-6" in f else "income"
    for r in (K.read_46 if tab == "age" else K.read_43)(f, y, set(CODES)):
        r["table"] = tab
        recs.append(r)
d = pd.DataFrame(recs)
d["item"] = d.code.map(CODES).fillna(d.code)
# 確かめ：どの年・区分にも全品目がそろう。平均の値は 4-6 と 4-3 で一致する
cnt = d.groupby(["table", "year", "group"]).code.nunique()
print(cnt.groupby(level=0).agg(["min", "max"]))
assert cnt.loc["age"].eq(len(CODES) + 2).all() and cnt.loc["income"].ge(len(CODES) + 1).all(), cnt
a = d[d.group == "平均"].pivot_table(index=["year", "code"], columns="table", values="amount")
assert (a["age"] - a["income"]).abs().max() < 1e-9, a[(a["age"] - a["income"]).abs() > 0]
d = d[["table", "year", "group", "code", "item", "amount", "freq"]].sort_values(["table", "year", "group", "code"])
d.to_csv(DATA / "leisure_items.csv", index=False)

# 消費者物価指数（年平均）
t = pd.read_csv(RAW / "cpi_item_annual.csv", encoding="cp932", header=None, dtype=str)
head = [str(x).strip() for x in t.iloc[0]]
code_row = [str(x).strip() for x in t.iloc[2]]
want = {"総合": "0001", "教養娯楽サービス": "0138", "宿泊料": "9300", "外国パック旅行費": "9305", "映画観覧料": "9341", "演劇観覧料": "9342",
        "プロ野球観覧料": "9350", "フィットネスクラブ使用料": "9362", "文化施設入場料": "9374", "テーマパーク入場料": "9372", "入場・観覧・ゲーム代": "0143"}
t[0] = t[0].str.strip()
b = t[t[0].str.fullmatch(r"\d{4}", na=False)]
out = pd.DataFrame({"year": b[0].astype(int).values})
for nm, cd in want.items():
    j = [k for k in range(len(head)) if head[k] == nm and code_row[k] == cd]
    assert len(j) == 1, (nm, j)
    out[nm] = pd.to_numeric(b[j[0]], errors="coerce").values
out = out[(out.year >= 2015) & (out.year <= 2025)]
assert out.notna().all().all()
out.to_csv(DATA / "cpi_leisure.csv", index=False)
print(d.groupby("table").size(), out.tail(3).T, sep="\n")
