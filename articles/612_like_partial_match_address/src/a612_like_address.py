"""612 住所を「LIKE '%桜ヶ丘%'」のような部分一致で探すと、何件を余分に拾い、何件を取りこぼすのか

架空の市（架空市）の顧客の住所2万件を作る。町名・建物名はすべて架空。探したいのは「桜ヶ丘」の町の顧客。
まぎらわしい町（東桜ヶ丘・桜ヶ丘台・西桜ヶ丘）と、建物名に「桜ヶ丘」を含む住所（本町1-2 桜ヶ丘ハイツ）を混ぜ、
書き方のゆれ（市の名前の省略・「桜ケ丘」・全角の数字・空白・漢数字の丁目）を入れる。
  A1 部分一致 LIKE '%桜ヶ丘%'
  A2 前方一致 LIKE '架空市桜ヶ丘%'
  A3 正規化（NFKC・ケ→ヶ・空白の除去）してから、町名のすぐあとが数字・丁目・終わりであることを正規表現で確かめる
余分に拾った件数・取りこぼした件数を、正解（作ったときの町）と比べる。DuckDB（1スレッド）で実行し、Python の判定と一致を確かめる。
"""
import json
import re
import unicodedata
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の顧客の住所（作成者が乱数で作成、seed 612）。地名・建物名はすべて架空"
rng = np.random.default_rng(612)
N = 20000
towns = ["桜ヶ丘", "東桜ヶ丘", "桜ヶ丘台", "西桜ヶ丘", "本町", "緑町", "旭町", "港南", "若葉台", "大原", "川端", "新町"]
p = np.array([8, 4, 4, 3, 10, 9, 9, 8, 8, 7, 6, 6], float); p /= p.sum()
KAN = "〇一二三四五六七八九"
rows = []
for i in range(N):
    t = towns[rng.choice(len(towns), p=p)]
    ch, bl, no = int(rng.integers(1, 6)), int(rng.integers(1, 30)), int(rng.integers(1, 20))
    style = rng.choice(["hyphen", "kanji", "zen"], p=[0.6, 0.2, 0.2])
    if style == "hyphen":
        rest = f"{ch}-{bl}-{no}"
    elif style == "kanji":
        rest = f"{KAN[ch]}丁目{bl}番{no}号"
    else:
        rest = f"{ch}-{bl}-{no}".translate(str.maketrans("0123456789-", "０１２３４５６７８９－"))
    name = t
    if "桜ヶ丘" in t and rng.random() < 0.15:
        name = t.replace("ヶ", "ケ")
    city = "" if rng.random() < 0.2 else "架空市"
    sp = " " if rng.random() < 0.1 else ""
    addr = f"{city}{name}{sp}{rest}"
    if t != "桜ヶ丘" and rng.random() < 0.03:
        addr += " 桜ヶ丘ハイツ" + str(int(rng.integers(101, 310)))
    rows.append((i + 1, addr, t))
C = pd.DataFrame(rows, columns=["cust_id", "address", "town_true"])


def norm(s):
    s = unicodedata.normalize("NFKC", s).replace("ケ丘", "ヶ丘").replace(" ", "")
    return s


C["address_norm"] = C.address.map(norm)
C[["cust_id", "address"]].to_csv(DATA / "addresses.csv", index=False)
truth = set(C.cust_id[C.town_true == "桜ヶ丘"])
con = duckdb.connect(); con.execute("SET threads=1"); con.register("customers", C)
qs = [q for q in (SQL / "02_address_match_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
got = {k: set(con.execute(q).df().cust_id) for k, q in zip(["A1", "A2", "A3"], qs)}
# Python で同じ判定
py = {"A1": set(C.cust_id[C.address.str.contains("桜ヶ丘", regex=False)]),
      "A2": set(C.cust_id[C.address.str.startswith("架空市桜ヶ丘")]),
      "A3": set(C.cust_id[C.address_norm.str.match(r"^(架空市)?桜ヶ丘([0-9一二三四五六七八九]|$)")])}
assert all(got[k] == py[k] for k in got)
res, why = {}, {}
for k, s in got.items():
    fp = s - truth; fn = truth - s
    res[k] = {"hits": len(s), "correct": len(s & truth), "extra": len(fp), "missed": len(fn),
              "precision_pct": round(100 * len(s & truth) / max(len(s), 1), 1), "recall_pct": round(100 * len(s & truth) / len(truth), 1)}
    sub = C[C.cust_id.isin(fp)]
    why[k] = {"extra_by_true_town": sub.town_true.value_counts().to_dict(),
              "extra_building": int(sub.address.str.contains("ハイツ").sum())}
    m = C[C.cust_id.isin(fn)]
    why[k]["missed_no_city"] = int((~m.address.str.startswith("架空市")).sum())
    why[k]["missed_ke"] = int(m.address.str.contains("桜ケ丘").sum())
    why[k]["missed_space_or_zen"] = int(((m.address.str.contains(" ")) | (m.address.str.contains("[０-９]"))).sum())
pd.DataFrame(res).T.to_csv(RES / "summary.csv")
out = {"addresses": N, "true_sakuragaoka": len(truth), "results": res, "breakdown": why,
       "styles": {"no_city_pct": round(100 * (~C.address.str.startswith("架空市")).mean(), 1),
                  "ke_variant": int(C.address.str.contains("桜ケ丘").sum()), "building_name": int(C.address.str.contains("ハイツ").sum())}}
json.dump(out, open(RES / "a612_main.json", "w"), ensure_ascii=False, indent=1, default=int)

lab = {"A1": "部分一致 LIKE '%桜ヶ丘%'", "A2": "前方一致 LIKE '架空市桜ヶ丘%'", "A3": "正規化＋町名の区切りを確かめる"}
ks = ["A1", "A2", "A3"]
# 図1：拾った件数の内訳
fig, ax = plt.subplots(figsize=(9, 3.6))
for i, k in enumerate(ks[::-1]):
    r = res[k]
    ax.barh(i, r["correct"], color=GREEN); ax.barh(i, r["extra"], left=r["correct"], color=ORANGE)
    ax.text(r["hits"] * 1.01 + 30, i, f"正しい {r['correct']:,}件＋余分 {r['extra']:,}件（取りこぼし {r['missed']:,}件）", va="center", fontsize=9)
ax.axvline(len(truth), color=GRAY, ls=":", lw=1)
ax.set_yticks(range(3)); ax.set_yticklabels([lab[k] for k in ks[::-1]]); ax.set_xlim(0, max(r["hits"] for r in res.values()) * 1.9)
ax.set_xlabel(f"拾った件数（点線は本当の桜ヶ丘の {len(truth):,}件）"); ax.set_title("架空の住所2万件から「桜ヶ丘」を探す")
save(fig, "a612_hits.png", SRC, y=-0.08)
# 図2：余分に拾った住所の、本当の町
ex = pd.DataFrame({k: pd.Series(why[k]["extra_by_true_town"]) for k in ["A1", "A2"]}).fillna(0).astype(int)
fig, ax = plt.subplots(figsize=(8, 3.6))
xx = np.arange(len(ex))
ax.bar(xx - 0.2, ex.A1, 0.4, color=ORANGE, label=lab["A1"]); ax.bar(xx + 0.2, ex.A2, 0.4, color=BLUE, label=lab["A2"])
ax.set_xticks(xx); ax.set_xticklabels([f"{t}\n（建物名）" if t not in ["東桜ヶ丘", "桜ヶ丘台", "西桜ヶ丘"] else t for t in ex.index], fontsize=9)
ax.set_ylabel("余分に拾った件数"); ax.legend(frameon=False, fontsize=9); ax.set_title("余分に拾った住所は、本当はどの町か")
save(fig, "a612_extra_towns.png", SRC, y=-0.1)
# 図3：取りこぼしの理由
fig, ax = plt.subplots(figsize=(8, 3.4))
cats = ["市の名前の省略", "「桜ケ丘」の書き方", "空白・全角の数字"]
for i, k in enumerate(["A1", "A2"]):
    v = [why[k]["missed_no_city"], why[k]["missed_ke"], why[k]["missed_space_or_zen"]]
    ax.bar(np.arange(3) + (i - 0.5) * 0.4, v, 0.4, color=[ORANGE, BLUE][i], label=lab[k])
    for j, vv in enumerate(v):
        ax.text(j + (i - 0.5) * 0.4, vv, str(vv), ha="center", va="bottom", fontsize=9)
ax.set_xticks(range(3)); ax.set_xticklabels(cats); ax.set_ylabel("取りこぼした件数（重なりあり）")
ax.legend(frameon=False, fontsize=9); ax.set_title("取りこぼした桜ヶ丘の住所の書き方")
save(fig, "a612_missed_reasons.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
