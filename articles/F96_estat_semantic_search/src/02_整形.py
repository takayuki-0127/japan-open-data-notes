"""F96 02 整形：取得した一覧（2026年1〜10月に公開・更新されたファイル）から、検索の対象にする「表」の一覧を作る。
- 同じ統計の同じ表題（毎月・毎年の更新）は1つにまとめる（いちばん新しい公開のものを残す）
- 検索に使う文：表題＋政府統計名＋提供統計名・分類（パス）。パスの年・年度は残す（調査回の区別に使われるため）
出力：data/tables.csv.gz（id, toukei, path, survey, open, title, n_files, text）
"""
import json, re, unicodedata
import pandas as pd
from common import RAW, DATA

import gzip
raw = json.load(gzip.open(RAW / "estat_files_2026.json.gz", "rt", encoding="utf-8"))
df = pd.DataFrame(raw["rows"])
print("取得した行", len(df), "ログ", raw["log"][-3:])
df = df.drop_duplicates("id")
# 01 の初回の取得では、DB へのリンクがある表の表題を取りこぼした（DB へのリンクにも stat_infid が入るため）。
# そのページだけ取り直した表題（01_取得_browser.js の修正版と同じ読み方）で埋める
fix = json.load(open(RAW / "title_fix.json", encoding="utf-8"))
emp = df.title.str.strip() == ""
df.loc[emp, "title"] = df.loc[emp, "id"].map(fix).fillna("")
print("表題を埋めた", int((df.loc[emp, "title"] != "").sum()), "/", int(emp.sum()))
print("重複を除いたファイル", len(df))

def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s+", " ", s).strip()

for c in ["toukei", "path", "title", "survey"]:
    df[c] = df[c].map(norm)
df = df[df.title != ""].copy()
df["key"] = df.toukei + "||" + df.title
g = df.sort_values(["open", "id"], ascending=False).groupby("key", sort=False)
tab = g.first().reset_index()
tab["n_files"] = g.size().values
# path は先頭の政府統計名と重なる部分があるので、そのまま残す（検索ではどちらも1つの文にまとめる）
tab["text"] = tab.title + "（" + tab.toukei + "／" + tab.path + "）"
tab = tab[["id", "toukei", "path", "survey", "open", "title", "n_files", "text"]].sort_values("id").reset_index(drop=True)
tab.to_csv(DATA / "tables.csv.gz", index=False)
summ = dict(files=int(len(df)), tables=int(len(tab)), toukei=int(tab.toukei.nunique()),
            title_len_median=float(tab.title.str.len().median()),
            text_len_median=float(tab.text.str.len().median()))
json.dump(summ, open(DATA / "tables_summary.json", "w"), ensure_ascii=False, indent=1)
print(summ)
