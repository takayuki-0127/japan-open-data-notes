"""03 経路の集計：全体・作り手ごとの地図・e-Stat 経由の割合・記事の順番による変化・頑健性・手作業の確認"""
import re, json
import numpy as np, pandas as pd
from common import DATA, RES

RES.mkdir(exist_ok=True)
D = pd.read_csv(DATA / "article_owner.csv")
L = pd.read_csv(DATA / "source_lines.csv.gz")
ROUTES = ["API", "表ファイル", "一括ファイル", "Webページの表", "画面操作", "PDF", "手で転記", "ページURLのみ", "記録なし"]
GROUP = {"API": "API", "表ファイル": "ファイル（表・一括）", "一括ファイル": "ファイル（表・一括）",
         "Webページの表": "画面・ページから", "画面操作": "画面・ページから", "PDF": "PDF・手で転記", "手で転記": "PDF・手で転記",
         "ページURLのみ": "経路の記録なし", "記録なし": "経路の記録なし"}
G4 = ["API", "ファイル（表・一括）", "画面・ページから", "PDF・手で転記", "経路の記録なし"]
out = {}

N = D[D["new"]].copy()
N["g"] = N["route"].map(GROUP); N["g_hard"] = N["route_hard"].map(GROUP)
out["n_articles"] = int(L["article"].nunique())
out["n_articles_F"] = int(L.loc[L.article.str.startswith("F"), "article"].nunique())
out["n_pairs"] = int(len(D)); out["n_pairs_new"] = int(len(N))
out["n_articles_with_new"] = int(N["article"].nunique())
out["route_share"] = (N["route"].value_counts(normalize=True).reindex(ROUTES).fillna(0).round(4)).to_dict()
out["route_count"] = N["route"].value_counts().reindex(ROUTES).fillna(0).astype(int).to_dict()
out["group_share"] = N["g"].value_counts(normalize=True).reindex(G4).fillna(0).round(4).to_dict()
out["group_share_hard"] = N["g_hard"].value_counts(normalize=True).reindex(G4).fillna(0).round(4).to_dict()
anyc = [c for c in N.columns if c.startswith("any_")]
out["any_share"] = {c[4:]: round(float(N[c].mean()), 4) for c in anyc}

# 作り手ごとの地図（新規の組、5組以上）
own = N.groupby("owner").agg(n=("article", "size"), via_estat=("via_estat", "mean"))
for g in G4:
    own[g] = N.assign(x=N["g"] == g).groupby("owner")["x"].mean()
own = own[own["n"] >= 5].sort_values("n", ascending=False)
own.round(3).to_csv(RES / "owner_map.csv")
ownr = pd.crosstab(N["owner"], N["route"]).reindex(columns=ROUTES, fill_value=0)
ownr.to_csv(RES / "owner_route_counts.csv")

# API を使った組
api = N[N["any_API"]][["article", "owner", "route"]]
api.to_csv(RES / "api_pairs.csv", index=False)
out["api_pairs"] = int(len(api)); out["api_articles"] = int(api["article"].nunique())
out["api_owners"] = api["owner"].value_counts().to_dict()
# API を使わなかった理由の記録（アプリケーションIDの登録など）
why = L[L["text"].astype(str).str.contains(r"appId|アプリケーションID|API ?キー|APIキー|アプリの登録|ユーザー登録", regex=True)]
why[["article", "file", "text"]].to_csv(RES / "api_not_used_notes.csv", index=False)
out["api_key_note_articles"] = int(why["article"].nunique())

# e-Stat 経由の割合（作り手ごと）
out["via_estat_share"] = round(float(N["via_estat"].mean()), 4)
out["via_estat_by_owner"] = own["via_estat"].round(3).to_dict()

# 記事の順番による変化（F と、番号つきの通常記事を別々に、番号の3区分）
def seg(df):
    df = df[df["num"] >= 0].copy()
    df["part"] = pd.qcut(df["num"].rank(method="first"), 3, labels=["前", "中", "後"])
    t = pd.crosstab(df["part"], df["g"], normalize="index").reindex(columns=G4, fill_value=0)
    t["n"] = df.groupby("part", observed=False).size()
    return t
seg_F = seg(N[N["F"]]); seg_O = seg(N[~N["F"]])
seg_F.round(3).to_csv(RES / "trend_F.csv"); seg_O.round(3).to_csv(RES / "trend_numbered.csv")

# 頑健性（分類の仕方）
def summ(df, col="g"):
    s = df[col].value_counts(normalize=True).reindex(G4).fillna(0)
    return {"ファイル": s["ファイル（表・一括）"], "API": s["API"], "手間（画面・PDF・転記）": s["画面・ページから"] + s["PDF・手で転記"],
            "記録なし": s["経路の記録なし"], "n": len(df)}
DA = D.copy(); DA["g"] = DA["route"].map(GROUP); DA["g_hard"] = DA["route_hard"].map(GROUP)
art = N.sort_values("route", key=lambda s: s.map({r: i for i, r in enumerate(ROUTES)})).groupby("article").first()
art_hard = N.copy(); art_hard["k"] = art_hard["route_hard"].map({r: i for i, r in enumerate(["API","表ファイル","一括ファイル","Webページの表","画面操作","PDF","手で転記","ページURLのみ","記録なし"])})
rob = {
    "基本（新規の組・機械向きの経路）": summ(N),
    "手間のかかる経路で数える": summ(N, "g_hard"),
    "再利用の組も含める": summ(DA),
    "記事単位（記事ごとにいちばん機械向き）": summ(art.assign(g=art["route"].map(GROUP))),
    "看板記事（F）だけ": summ(N[N["F"]]),
    "通常記事（番号つき）だけ": summ(N[~N["F"]]),
    "e-Stat 経由の組だけ": summ(N[N["via_estat"]]),
    "e-Stat 経由でない組だけ": summ(N[~N["via_estat"]]),
}
R = pd.DataFrame(rob).T
R.round(4).to_csv(RES / "robustness.csv")

# 手作業の確認（作成後に見た40組。調整に使った80組とは別）
V = pd.read_csv(DATA / "validation_labels.csv").merge(D, on=["article", "owner"], how="left")
def ok(r):
    if r.exp_new == "F": return not r.new
    if r.exp_new == "T" and not r.new: return False
    return r.exp_route == "*" or r.route in r.exp_route.split("|")
V["ok"] = V.apply(ok, axis=1)
V["err"] = np.where(V["ok"], "", np.where((V["exp_new"] == "F") & V["new"], "再利用を新規と判定", "経路の違い"))
V.to_csv(RES / "validation_result.csv", index=False)
out["validation_agree"] = round(float(V["ok"].mean()), 3); out["validation_n"] = int(len(V))
out["validation_errors"] = V["err"][V["err"] != ""].value_counts().to_dict()

# 同梱データの形（data フォルダの拡張子、記事数）
T = pd.read_csv(DATA / "tree_data_files.csv")
T["ext"] = T["path"].str.extract(r"\.([A-Za-z0-9]+)(?:\.gz)?$")[0].str.lower()
T["raw"] = T["path"].str.startswith("data/raw")
ext = T.groupby("ext")["article"].nunique().sort_values(ascending=False)
ext.to_csv(RES / "bundled_ext_articles.csv")
out["bundled_ext_articles"] = ext.head(8).to_dict()

json.dump(out, open(RES / "results.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["n_articles","n_articles_F","n_pairs","n_pairs_new","n_articles_with_new","route_count","group_share","group_share_hard","any_share","api_pairs","api_articles","api_owners","api_key_note_articles","via_estat_share","validation_agree","validation_errors"]}, ensure_ascii=False, indent=0, default=float))
print(own.round(2).to_string())
print(R.round(3).to_string())
print(seg_F.round(2).to_string()); print(seg_O.round(2).to_string())
