"""252 外れ値を消すか残すか、どう決めてきたか（④ 振り返り R008）

使い方: python a252.py <japan-open-data-notes のクローン>
  README を1行ずつ読み、外れ値・特別な点の扱いを書いた行を拾って、
  ①扱い方（除いた結果も並べた・1つずつ外した・端を丸めた・頑健な指標・最初から除いた）
  ②何を外したか（コロナの時期・東京・1つの年や月・業種や部門・災害・小さい市町村）
  を言葉で数える。外したときに結論が動いたかは、拾った行から30行を選んで目で確かめた
  （data/manual_outcome_sample.csv）。
"""
import re, sys, os, json
import pandas as pd
import matplotlib.pyplot as plt
from common import readmes, GROUPS, group_of

repo = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
docs = readmes(repo)

PICK = (r"外れ値|異常値|極端な|飛び抜け|除くと|除いても|除いた場合|除いた版|除いて計算|外すと|外しても|抜くと|抜いても|"
        r"ずつ(外|除|抜)|外れ値の丸め|端を丸め|ウィンソ|上下\s*[0-9.]+\s*%|影響度|Cook")
ACT = {
    "除いた結果も並べた": r"除くと|除いても|除いた場合|除いた版|除いて計算|外すと|外しても|抜くと|抜いても",
    "1つずつ外して確かめた": r"ずつ(外|除|抜)|影響度|Cook|DFBETA",
    "端を丸めた": r"外れ値の丸め|端を丸め|ウィンソ|上下\s*[0-9.]+\s*%",
    "頑健な指標・変換を使った": r"中央値|対数|順位|頑健な|ロバスト|Huber|分位点",
}
WHAT = {
    "コロナの時期": r"コロナ|2020年度?(だけ|を除)|2020〜2?0?2[12]",
    "東京・大都市": r"東京|23区|大都市|政令市",
    "1つの年・月・回": r"(\d{4}年|\d+か月|\d+月)(だけ|を除|を外|を抜)|1年ずつ|1か月",
    "業種・部門・品目": r"業種|部門|産業|品目|業態",
    "災害・特別な出来事": r"地震|震災|台風|豪雨|リーマン|災害|消費税",
    "小さい市町村・少ない件数": r"人口\s*[0-9,千万]+\s*人?未満|小さい(町|市|村)|件数が少|少ない",
}

rows = []
for folder, t in docs:
    for ln in t.split("\n"):
        s = ln.strip()
        if not s or s.startswith("#") or "http" in s:
            continue
        if not re.search(PICK, s):
            continue
        r = {"article": folder, "group": group_of(folder), "text": s[:300]}
        for k, p in ACT.items():
            r[k] = bool(re.search(p, s))
        for k, p in WHAT.items():
            r[k] = bool(re.search(p, s))
        rows.append(r)
L = pd.DataFrame(rows)
L.to_csv(os.path.join(OUT, "data", "outlier_lines.csv"), index=False)

n_art = len(docs)
art = L.groupby("article").agg({**{k: "any" for k in ACT}, **{k: "any" for k in WHAT}})
act = pd.DataFrame({"扱い方": list(ACT), "記事": [int(art[k].sum()) for k in ACT]})
what = pd.DataFrame({"外したもの": list(WHAT), "記事": [int(art[k].sum()) for k in WHAT]})
act.to_csv(os.path.join(OUT, "results", "by_action.csv"), index=False)
what.to_csv(os.path.join(OUT, "results", "by_target.csv"), index=False)


g = pd.DataFrame({"group": GROUPS})
cnt = pd.Series([group_of(f) for f, _ in docs]).value_counts()
hit = L.drop_duplicates("article").group.value_counts()
g["記事"] = g.group.map(cnt).fillna(0).astype(int)
g["書いた記事"] = g.group.map(hit).fillna(0).astype(int)
g["割合"] = (g["書いた記事"] / g["記事"]).round(3)
g.to_csv(os.path.join(OUT, "results", "by_group.csv"), index=False)

summary = {"readmes": n_art, "lines": int(len(L)), "articles": int(L.article.nunique()),
           "exclusion_lines": int((L["除いた結果も並べた"] | L["1つずつ外して確かめた"]).sum())}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False)); print(act.to_string(index=False)); print(what.to_string(index=False)); print(g.to_string(index=False))

# ---- 図1：扱い方と外したもの ----
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, df, col, ttl in [(axes[0], act, "扱い方", "扱い方"), (axes[1], what, "外したもの", "外したもの")]:
    d = df.sort_values("記事")
    ax.barh(d[col], d["記事"], color="#4C78A8")
    for y, v in enumerate(d["記事"]):
        ax.text(v + 1, y, f"{v}本", va="center", fontsize=9)
    ax.set_xlim(0, d["記事"].max() * 1.3); ax.set_title(ttl, fontsize=11); ax.set_xlabel("書いた記事の数")
fig.suptitle(f"外れ値・特別な点の扱いを書いた記事 {L.article.nunique()}本（{n_art}本中）", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a252_actions.png"), dpi=150); plt.close()

# ---- 図2：手で確かめた結果（「除くと・外すと」の行から乱数 seed 11 で30行） ----
M = pd.read_csv(os.path.join(OUT, "data", "manual_outcome_sample.csv"))
mc = M.label.value_counts()
summary["manual_sample"] = {k: int(v) for k, v in mc.items()}
json.dump(summary, open(os.path.join(OUT, "results", "summary.json"), "w"), ensure_ascii=False, indent=1)

# ---- 図2：F178 の3,403組で、いちばん効く1県を除くと p<0.05 の判定が入れ替わる割合 ----
f178 = pd.DataFrame({"p の区間": ["1e-6未満", "1e-6〜1e-4", "1e-4〜0.001", "0.001〜0.01", "0.01〜0.05", "0.05〜0.2", "0.2〜1"],
                     "組": [364, 362, 269, 390, 357, 514, 1147],
                     "都道府県の指標": [0.8, 1.4, 2.6, 16.7, 38.9, 33.5, 9.0],
                     "乱数（正規分布）": [0.0, 0.0, 0.0, 1.7, 37.0, 32.7, 0.9]})
f178.to_csv(os.path.join(OUT, "data", "f178_flip_by_p.csv"), index=False)
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = range(len(f178)); w = 0.38
ax.bar([i - w / 2 for i in x], f178["都道府県の指標"], w, color="#E45756", label="都道府県の指標（F178）")
ax.bar([i + w / 2 for i in x], f178["乱数（正規分布）"], w, color="#BAB0AC", label="乱数のデータ（正規分布）")
for i, v in zip(x, f178["都道府県の指標"]):
    ax.text(i - w / 2, v + 1, f"{v:.0f}%" if v >= 1 else f"{v}%", ha="center", fontsize=8.5)
ax.set_xticks(list(x)); ax.set_xticklabels(f178["p の区間"], fontsize=8.5)
ax.set_ylabel("判定が入れ替わる割合（%）"); ax.set_xlabel("元の回帰の p")
ax.set_title("いちばん効く1県を除くと、p<0.05 の判定が入れ替わる割合（3,403組）", fontsize=11.5)
ax.legend(fontsize=9, frameon=False)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a252_f178_flip.png"), dpi=150); plt.close()

# ---- 図3：外したら結論が動いた例・動かなかった例（README の記述から作成者が選んだ） ----
cases = [
    ("013", "昼に人が集まる街と所得", "東京23区を除く", "動いた：条件をそろえても残った関係が消えた"),
    ("127", "物価が高い県", "家賃を除く", "動いた：2023年から1位が入れ替わった"),
    ("F185", "宅配便とネット支出", "FY2020を除く", "動いた：弾力性が0.02に（コロナの1年が効いていた）"),
    ("F264", "事故率と保険", "2020年を除く", "動いた：相関0.77→0.45"),
    ("F133", "輸出の重力モデル", "米国と中国を除く", "動いた：距離の効果が −1.18 に強まった"),
    ("F35", "景気の状態の推定", "コロナ期を除く", "動かなかった：一致は90.9%のまま"),
    ("F141", "特許出願の地方割合", "2020〜21年を除く", "動かなかった：傾きはほぼ同じ"),
]
pd.DataFrame(cases, columns=["記事", "題材", "外したもの", "結果"]).to_csv(os.path.join(OUT, "data", "cases.csv"), index=False)
fig, ax = plt.subplots(figsize=(10, 5.6)); ax.axis("off")
tb = ax.table(cellText=[list(c) for c in cases], colLabels=["記事", "題材", "外したもの", "結果"],
              colWidths=[0.07, 0.25, 0.2, 0.48], loc="center", cellLoc="left")
tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 2.6)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#CCCCCC")
    if r == 0:
        cell.set_facecolor("#4C78A8"); cell.set_text_props(color="white", weight="bold")
    elif c == 3:
        cell.set_text_props(color="#B03A2E" if cell.get_text().get_text().startswith("動いた") else "#2E5E8C")
ax.set_title("特別な点を外して確かめた例（各記事の README から）", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(OUT, "figures", "a252_cases.png"), dpi=150); plt.close()
