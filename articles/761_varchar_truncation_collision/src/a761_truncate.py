"""761 長さの足りない列に名前を入れると、後ろが切れて別の商品が同じ名前になるのは何件か

架空の日用品600品目。名前は「シリーズ名＋種類＋香り・味＋容量」で、同じシリーズは先頭がそろい、違いは後ろにある。
名前の列の長さが足りないときに後ろが切れる場合を3通り再現する（Python で再現。SQL Server では未検証）。
  A 20文字で切る（NVARCHAR(20) に CAST したとき）
  B 20バイトで切る・Shift_JIS（日本語の照合順序の VARCHAR(20)。全角は2バイト）
  C 20バイトで切る・UTF-8（UTF-8 の照合順序の VARCHAR(20)。全角は3バイト）
切れた品目、同じ名前になった組、名前で集計したときに合わさった売上を数える。DuckDB（1スレッド）で A を確かめる。seed 761。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の日用品の商品名と売上（作成者が乱数で作成、seed 761）"
rng = np.random.default_rng(761)
CAT = {  # シリーズ名: (種類, 香り・味, 容量)
    "やわらか仕上げ柔軟剤": (["本体", "詰め替え用", "詰め替え用大容量"], ["フローラルの香り", "せっけんの香り", "無香料"], ["480mL", "720mL", "1,200mL"]),
    "すっきり洗浄台所用洗剤": (["本体", "詰め替え用", "詰め替え用特大"], ["レモンの香り", "オレンジの香り", "微香性"], ["240mL", "500mL", "1,000mL"]),
    "さらさら衣料用洗剤": (["本体", "詰め替え用", "詰め替え用超特大"], ["部屋干し用", "抗菌プラス", "香りなし"], ["750g", "1,160g", "1,800g"]),
    "ふんわりボディソープ": (["ポンプ", "詰め替え用", "お試し"], ["ピーチの香り", "ハーブの香り", "弱酸性無香料"], ["340mL", "480mL", "800mL"]),
    "ぴかぴかお風呂用洗剤": (["スプレー", "詰め替え用", "泡タイプ"], ["シトラスの香り", "ミントの香り", "無香料"], ["380mL", "760mL", "1,100mL"]),
    "さわやか消臭スプレー": (["本体", "つけかえ用", "携帯用"], ["グリーンの香り", "せっけんの香り", "香りが残らない"], ["50mL", "280mL", "370mL"]),
    "ごくごく麦茶": (["ペットボトル", "ティーバッグ", "パック"], ["国産大麦", "カフェインゼロ", "香ばし焙煎"], ["500mL×24本", "2L×6本", "54袋入"]),
    "しゃきっと炭酸水": (["ペットボトル", "缶", "ラベルレス"], ["プレーン", "レモン", "グレープフルーツ"], ["500mL×24本", "1L×15本", "350mL×24本"]),
    "まろやか無調整豆乳": (["紙パック", "小パック"], ["無調整", "調製", "低糖"], ["200mL×18本", "1,000mL×6本", "125mL×24本"]),
    "さくさく全粒粉クラッカー": (["袋", "小分け", "箱"], ["プレーン", "ごま", "チーズ"], ["8枚×3袋", "12枚×4袋", "200g"]),
}
names = []
for s0, (ks, fs, zs) in CAT.items():
    for k in ks:
        for f in fs:
            for z in zs:
                names.append(" ".join([s0, k, f, z]))
names = sorted(names)
P = pd.DataFrame({"product_id": [f"P{i + 1:04d}" for i in range(len(names))], "name": names})
P["sales"] = (rng.lognormal(13, 1.0, len(P)) // 100 * 100).astype(int)
P.to_csv(DATA / "products.csv", index=False)


def cut_bytes(s, n, enc):
    b = s.encode(enc)
    if len(b) <= n:
        return s
    out = ""
    for ch in s:
        if len((out + ch).encode(enc)) > n:
            break
        out += ch
    return out


P["A"] = P.name.str.slice(0, 20)
P["B"] = P.name.map(lambda s: cut_bytes(s, 20, "cp932"))
P["C"] = P.name.map(lambda s: cut_bytes(s, 20, "utf-8"))
P["len_chars"] = P.name.str.len(); P["len_cp932"] = P.name.map(lambda s: len(s.encode("cp932"))); P["len_utf8"] = P.name.map(lambda s: len(s.encode("utf-8")))
con = duckdb.connect(); con.execute("SET threads=1"); con.register("products", P[["product_id", "name", "sales"]])
q = [x for x in (SQL / "02_truncate_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
dA = con.execute(q[0]).df(); dLen = con.execute(q[1]).df()
assert int(dA.n_names.iloc[0]) == P.A.nunique() and int(dLen.too_long.iloc[0]) == int((P.len_chars > 20).sum())
res = {}
for m in "ABC":
    g = P.groupby(m).agg(n=("product_id", "size"), sales=("sales", "sum"))
    coll = g[g.n > 1]
    res[m] = {"truncated": int((P[m] != P.name).sum()), "distinct_names": int(P[m].nunique()),
              "names_shared": int(len(coll)), "products_in_shared": int(coll.n.sum()),
              "products_in_shared_pct": round(coll.n.sum() / len(P) * 100, 1),
              "sales_merged_pct": round(coll.sales.sum() / P.sales.sum() * 100, 1),
              "max_products_one_name": int(g.n.max()), "kept_chars_median": float(P[m].str.len().median())}
_g = P.groupby("A").filter(lambda g: len(g) == 3).sort_values(["A", "name"])
ex = _g[_g.A.isin(_g.A.unique()[:2])]
out = {"products": len(P), "name_len_chars_median": float(P.len_chars.median()), "name_len_chars_max": int(P.len_chars.max()),
       "names_over_20_chars_pct": round((P.len_chars > 20).mean() * 100, 1), "methods": res,
       "example_A": ex[["name", "A"]].values.tolist()}
json.dump(out, open(RES / "a761_main.json", "w"), ensure_ascii=False, indent=1)
P.drop(columns=["sales"]).to_csv(RES / "truncated_names.csv", index=False)

# 図1：3つの切り方で同じ名前になった品目の割合
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = ["A 20文字\n（NVARCHAR(20)）", "B 20バイト・Shift_JIS\n（日本語の VARCHAR(20)）", "C 20バイト・UTF-8\n（UTF-8 の VARCHAR(20)）"]
v = [res[m]["products_in_shared_pct"] for m in "ABC"]; v2 = [res[m]["sales_merged_pct"] for m in "ABC"]
x = np.arange(3)
ax.bar(x - 0.18, v, 0.36, color=ORANGE, label="ほかの品目と同じ名前になった品目（%）")
ax.bar(x + 0.18, v2, 0.36, color=LIGHT, label="名前で集計すると合わさる売上（%）")
for i in range(3):
    ax.text(i - 0.18, v[i] + 1, f"{v[i]:.1f}", ha="center", fontsize=9); ax.text(i + 0.18, v2[i] + 1, f"{v2[i]:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9); ax.set_ylabel("%"); ax.set_ylim(0, 112); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("同じ「20」でも、文字かバイトかで切れ方が大きく違う")
save(fig, "a761_collisions.png", SRC)
# 図2：名前の長さの分布
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.hist(P.len_chars, bins=range(5, 45), color=BLUE, alpha=0.8, label="文字数")
ax.axvline(20, color=ORANGE, lw=1.5, ls="--"); ax.text(19.7, ax.get_ylim()[1] * 0.9, "20文字", color=ORANGE, ha="right")
ax.axvline(10, color=GRAY, lw=1.2, ls=":"); ax.text(10.3, ax.get_ylim()[1] * 0.75, "Shift_JIS の\n20バイト ≒ 10文字", color=GRAY, fontsize=9)
ax.set_xlabel("商品名の長さ（文字）"); ax.set_ylabel("品目数")
ax.set_title(f"商品名の{out['names_over_20_chars_pct']}%が20文字を超える（中央値{out['name_len_chars_median']:.0f}文字）")
save(fig, "a761_lengths.png", SRC)
# 図3：例
fig, ax = plt.subplots(figsize=(9, 3.4)); ax.axis("off")
ax.text(0, 0.95, "元の名前", fontsize=10.5, color=GRAY, transform=ax.transAxes); ax.text(0.62, 0.95, "20文字で切った名前", fontsize=10.5, color=GRAY, transform=ax.transAxes)
for i, (n, b) in enumerate(ex[["name", "A"]].values.tolist()):
    y = 0.8 - i * 0.14
    ax.text(0, y, n, fontsize=10.5, transform=ax.transAxes); ax.text(0.62, y, b, fontsize=10.5, color=ORANGE, transform=ax.transAxes)
ax.set_title("違いは名前の後ろにあるので、切ると同じ名前になる")
save(fig, "a761_examples.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
