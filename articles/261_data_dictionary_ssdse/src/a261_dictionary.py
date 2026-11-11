"""261 データ辞書（列の説明書）は、どう作ると使われるのか

SSDSE-B 2026年版（109項目）の CSV だけでは答えられない「この列は何か」の問いを、
統計センターの項目一覧（SSDSE_ITEM_2025.xlsx：単位）と解説 PDF（kaisetsu-B-2026.pdf：出典・地域の範囲・注意）から
1つの辞書にまとめ、問いの種類ごとに何項目が辞書で初めて分かるかを数える。値から確かめられることは値で確かめる。
"""
import json, re
import numpy as np
import pandas as pd
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, read_raw, save, plt

codes, names, body = read_raw(DATA / "SSDSE-B-2026.csv")
body.columns = ["year"] + codes[1:]
ITEMS, NAMES = codes[3:], names[3:]
x = pd.read_excel(DATA / "SSDSE_ITEM_2025.xlsx", header=None)
x = x[x[3].astype(str).str.contains("〇")]
item_name = {r[0]: r[1] for r in x.itertuples(index=False)}

FIELD = {"A": "人口・世帯", "B": "自然環境", "C": "経済基盤", "E": "教育", "F": "労働", "G": "文化・スポーツ",
         "H": "居住", "I": "健康・医療", "J": "福祉・社会保障", "L": "家計"}
# 解説 PDF（kaisetsu-B-2026.pdf）の別表 4〜6 ページから、項目コードの頭で出典を書き写したもの
SOURCE_BY_PREFIX = [
    ("A11", "総務省統計局「国勢調査報告」（国勢調査の年）・「人口推計」（それ以外の年）"),
    ("A13", "総務省統計局「国勢調査報告」（国勢調査の年）・「人口推計」（それ以外の年）"),
    ("A41", "厚生労働省「人口動態統計」"), ("A42", "厚生労働省「人口動態統計」"), ("A9", "厚生労働省「人口動態統計」"),
    ("A51", "総務省統計局「住民基本台帳人口移動報告年報」"),
    ("B", "気象庁「過去の気象データ」"), ("C33", "国土交通省「建築着工統計調査」"), ("C38", "厚生労働省「衛生行政報告例」"),
    ("C54", "国土交通省「都道府県地価調査」"), ("E", "文部科学省「学校基本調査報告書」"),
    ("F31", "厚生労働省「一般職業紹介状況」「労働市場年報」"), ("G51", "外務省「旅券統計」"),
    ("G71", "観光庁「宿泊旅行統計調査報告」"), ("H1", "国土交通省「住宅着工統計」"), ("H2", "国土交通省「住宅着工統計」"),
    ("H56", "環境省「一般廃棄物処理事業実態調査」"), ("I5", "厚生労働省「医療施設調査・病院報告」"),
    ("J250502", "こども家庭庁「都道府県別の認定こども園の数の推移」"), ("J25", "厚生労働省「社会福祉施設等調査」"),
    ("L", "総務省統計局「家計調査」")]


def source_of(c):
    for p, s in SOURCE_BY_PREFIX:  # 長い頭から順に並べてある（J250502 を J25 より先に）
        if c.startswith(p):
            return s
    return ""


rows = []
for c, n in zip(ITEMS, NAMES):
    full = item_name[c]
    unit = re.search(r"【(.*)】", full).group(1)
    v = pd.to_numeric(body[c])
    is_int = bool((v % 1 == 0).all())
    round1000 = body.assign(m=(v % 1000 == 0)).groupby("year")["m"].mean()
    rounded_years = [y for y, r in round1000.items() if r == 1.0]
    notes = []
    area = "都道府県全体"
    if c.startswith("B"):
        area = "県庁所在市の気象台（埼玉は熊谷、東京は千代田区、滋賀は彦根）"
    if c.startswith("L"):
        area = "県庁所在市（東京は区部）・二人以上の世帯"
        notes.append("1か月あたりの支出の年平均")
    if c.startswith(("A11", "A13")):
        notes.append("2015・2020年度は国勢調査、ほかの年は人口推計（千人単位で丸め）")
    if c.startswith("F31"):
        notes.append("（一般）は新規学卒者を除き、パートタイムを含む")
    if c in ("A4103", "H5614", "H5610"):
        notes.append("率・割合。県どうしを足し合わせられない")
    if c.startswith("B4") and c in ("B4106", "B4109"):
        notes.append("2021・2022年の一部は資料不足値（解説 3ページ）")
    rows.append({"項目コード": c, "項目名（CSV）": n, "項目名（項目一覧）": re.sub(r"[\s　]*【.*】", "", full),
                 "分野": FIELD[c[0]], "単位": unit, "出典": source_of(c), "地域の範囲": area,
                 "値の型": "整数" if is_int else "小数", "最小（2026年版）": v.min(), "最大（2026年版）": v.max(),
                 "負の値": bool((v < 0).any()), "千の倍数にそろう年度": ",".join(rounded_years), "注意": "／".join(notes)})
D = pd.DataFrame(rows)
assert (D["出典"] != "").all()
D.to_csv(RES / "data_dictionary_ssdse_b_2026.csv", index=False, encoding="utf-8-sig")

# --- CSV だけでは答えられない問いを数える ---
Q = {
    "Q1 単位は何か": D["項目コード"].tolist(),  # CSV には単位の行がない
    "Q2 1か月分か1年分か": D.loc[D["注意"].str.contains("1か月"), "項目コード"].tolist(),
    "Q3 県全体か県庁所在市か": D.loc[D["地域の範囲"] != "都道府県全体", "項目コード"].tolist(),
    "Q4 年によって出典が変わるか": D.loc[D["注意"].str.contains("国勢調査"), "項目コード"].tolist(),
    "Q5 率・割合で足し合わせられないか": D.loc[D["注意"].str.contains("率・割合"), "項目コード"].tolist(),
    "Q6 項目名が一覧と違う": D.loc[D["項目名（CSV）"].str.replace(" ", "") != D["項目名（項目一覧）"].str.replace(" ", "").str.replace("１", "1"), "項目コード"].tolist(),
}
# Q4 は値でも確かめる：国勢調査の年だけ千の倍数にそろわない項目
by_value = D.loc[D["千の倍数にそろう年度"].str.len() > 0, "項目コード"].tolist()
census_free = all(("2015" not in r and "2020" not in r) for r in D.loc[D["項目コード"].isin(by_value), "千の倍数にそろう年度"])
cnt = {k: len(v) for k, v in Q.items()}
flags = pd.Series(0, index=D["項目コード"])
for k, v in Q.items():
    if k.startswith("Q1"):
        continue
    flags[v] += 1
units = D["単位"].value_counts()
summary = {"n_items": len(D), "question_counts": cnt, "items_with_any_Q2_Q6": int((flags > 0).sum()),
           "flags_total_Q2_Q6": int(flags.sum()), "Q4_by_value_items": by_value, "Q4_by_value_matches": sorted(by_value) == sorted(Q["Q4 年によって出典が変わるか"]),
           "Q4_rounded_years_exclude_census": census_free, "units": units.to_dict(), "n_units": int(units.size),
           "Q6_items": Q["Q6 項目名が一覧と違う"], "n_sources": int(D["出典"].nunique())}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)

# --- 図1：辞書の抜き出し ---
show = D[D["項目コード"].isin(["A1101", "A4103", "B4101", "C5401", "F3101", "G7102", "H5610", "L3221"])]
cols = ["項目コード", "項目名（CSV）", "単位", "出典", "地域の範囲", "注意"]
fig, ax = plt.subplots(figsize=(13.5, 4.0)); ax.axis("off")
tb = show[cols].copy()
tb["出典"] = tb["出典"].str.replace("（国勢調査の年）・「人口推計」（それ以外の年）", "・人口推計", regex=False)
tb["地域の範囲"] = tb["地域の範囲"].str.replace("（埼玉は熊谷、東京は千代田区、滋賀は彦根）", "", regex=False)
tb["注意"] = tb["注意"].str.replace("2015・2020年度は国勢調査、ほかの年は人口推計（千人単位で丸め）", "国勢調査の年以外は千人単位", regex=False)
tb["注意"] = tb["注意"].str.replace("。県どうしを足し合わせられない", "（足せない）", regex=False).str.replace("、パートタイムを含む", "", regex=False)
tb["出典"] = tb["出典"].str.replace("「一般職業紹介状況」「労働市場年報」", "「一般職業紹介状況」", regex=False)
tb["項目名（CSV）"] = tb["項目名（CSV）"].str.replace("（平均価格）", "", regex=False).str.replace("（二人以上の世帯）", "", regex=False)
tb["単位"] = tb["単位"].str.replace("月間支出金額　円", "円（月）", regex=False)
tb["地域の範囲"] = tb["地域の範囲"].str.replace("・二人以上の世帯", "", regex=False)
t = ax.table(cellText=tb.values, colLabels=cols, loc="upper left", cellLoc="left", colLoc="left",
             colWidths=[0.07, 0.16, 0.07, 0.26, 0.19, 0.22])
t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.75)
for (r, c_), cell in t.get_celld().items():
    cell.set_edgecolor("#dddddd")
    if r == 0:
        cell.set_facecolor(LIGHT); cell.set_text_props(weight="bold")
ax.set_title("SSDSE-B のデータ辞書（109項目のうち8項目を抜き出し）", loc="left", fontsize=12)
save(fig, "a261_dictionary.png", source="出典：統計センター「SSDSE-B-2026」・項目一覧・解説をもとに作成者が作成")

# --- 図2：CSV だけでは答えられない問い ---
fig, ax = plt.subplots(figsize=(10.5, 3.9))
ks = list(cnt)[::-1]
ax.barh(ks, [cnt[k] for k in ks], color=[BLUE if not k.startswith("Q1") else GRAY for k in ks])
for i, k in enumerate(ks):
    ax.text(cnt[k] + 1, i, f"{cnt[k]}項目", va="center", fontsize=10)
ax.set_xlim(0, 125); ax.set_xlabel("辞書で初めて答えが分かる項目の数（全109項目）")
ax.set_title("CSV だけでは答えられない問いが、辞書でいくつ分かるか", loc="left", fontsize=12)
save(fig, "a261_questions.png", source="出典：統計センター「SSDSE-B-2026」・項目一覧・解説をもとに作成者が作成")

# --- 図3：値から確かめる（総人口が千の倍数にそろう年度）---
v = pd.to_numeric(body["A1101"])
share = body.assign(m=(v % 1000 == 0)).groupby("year")["m"].mean() * 100
fig, ax = plt.subplots(figsize=(10.5, 3.6))
ax.bar(share.index, share.values, color=[ORANGE if y in ("2015", "2020") else BLUE for y in share.index])
for xx, yy in zip(share.index, share.values):
    ax.text(xx, yy + 2, f"{yy:.0f}%", ha="center", fontsize=9)
ax.set_ylim(0, 115); ax.set_ylabel("47都道府県のうち千の倍数の割合（%）")
ax.set_title("総人口が千の倍数にそろわないのは、国勢調査の年の2015・2020年度だけ（ほかの年は千人単位の人口推計）", loc="left", fontsize=11.5)
save(fig, "a261_rounding.png")
print(json.dumps(summary, ensure_ascii=False, indent=0)[:1500])
