"""474-1 公的統計の Excel 24枚の「骨組み」から、見出しの置き方を機械的に数える。
骨組み＝セルが数字(n)・文字(t)・空(.)のどれか、左の8列と上の30行の文字、結合セルの範囲（数値は入っていない）。"""
import json, re
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import *

SK = json.load(open(DATA / "public_excel_skeletons.json", encoding="utf-8"))


def measure(e):
    K = e["kinds"]; T = e["text"]; nr = len(K); nc = len(K[0])
    isdata = [k.count("n") >= 3 for k in K]
    drows = [r for r in range(nr) if isdata[r]]
    if not drows: return None
    fn = [np.mean([K[r][c] == "n" for r in drows]) for c in range(nc)]
    first = next(c for c in range(nc) if fn[c] >= 0.5)
    lab = list(range(min(first, 8)))                      # 見出しの列（データの列より左）
    dcols = [c for c in range(first, nc) if fn[c] >= 0.3]
    r0 = drows[0]
    txt = lambda r, c: (T.get(f"{r+1},{c+1}", "") if K[r][c] == "t" else "")
    norm = lambda s: re.sub(r"[\s　]+", "", s)
    # 行の見出し（その行にある文字だけ）
    key = {r: "|".join(norm(txt(r, c)) for c in lab) for r in drows}
    cnt = pd.Series(list(key.values())).value_counts()
    if lab:
        amb = [r for r in drows if key[r].strip("|") == "" or cnt[key[r]] >= 2]
    else:
        amb = []
    # 下方向に埋めると値が入る行／親の行に子の名前が入る行
    seen = {c: False for c in lab}; fill = set(); wrong = set()
    for r in range(r0, nr):
        for c in lab:
            if K[r][c] == "t": seen[c] = True
            elif isdata[r] and seen[c]:
                fill.add(r)
                if any(K[r][cc] == "t" for cc in lab if cc < c) and not any(K[r][cc] == "t" for cc in lab if cc > c):
                    wrong.add(r)
    # 列の見出し
    hrows = [r for r in range(r0) if sum(K[r][c] == "t" for c in range(first, nc)) >= 2]
    top_blank = [c for c in dcols if hrows and K[hrows[0]][c] == "."]
    any_blank = [c for c in dcols if any(K[r][c] == "." for r in hrows[:-1])] if len(hrows) >= 2 else []
    mg = e["merged"]
    hm = sum(1 for a, b, c, d in mg if d > b and a <= r0)          # 見出し部分の横の結合
    vm = sum(1 for a, b, c, d in mg if c > a and b <= max(first, 1))  # 左の列の縦の結合
    blank_between = sum(1 for r in range(r0, drows[-1]) if set(K[r]) == {"."})
    return dict(name=e["name"], sheet=e["sheet"], file=e["file"], data_rows=len(drows), label_cols=len(lab), data_cols=len(dcols),
                ambiguous_rows=len(amb), ambiguous_pct=100 * len(amb) / len(drows),
                fill_rows=len(fill), fill_pct=100 * len(fill) / len(drows),
                wrong_fill_rows=len(wrong), wrong_fill_pct=100 * len(wrong) / len(drows),
                header_levels=len(hrows), top_blank_cols=len(top_blank), top_blank_pct=100 * len(top_blank) / max(len(dcols), 1),
                upper_blank_cols=len(any_blank), upper_blank_pct=100 * len(any_blank) / max(len(dcols), 1),
                merged_all=len(mg), merged_header_horizontal=hm, merged_left_vertical=vm, blank_rows_inside=blank_between)


df = pd.DataFrame([m for m in map(measure, SK) if m])
df.insert(0, "no", range(1, len(df) + 1))
df.round(1).to_csv(RES / "public_sheets.csv", index=False, encoding="utf-8-sig")
tot = dict(sheets=len(df), files=int(df.file.nunique()), data_rows=int(df.data_rows.sum()),
           ambiguous_rows=int(df.ambiguous_rows.sum()), ambiguous_pct=round(100 * df.ambiguous_rows.sum() / df.data_rows.sum(), 1),
           fill_rows=int(df.fill_rows.sum()), fill_pct=round(100 * df.fill_rows.sum() / df.data_rows.sum(), 1),
           wrong_fill_rows=int(df.wrong_fill_rows.sum()), sheets_with_wrong_fill=int((df.wrong_fill_rows > 0).sum()),
           sheets_ambiguous_any=int((df.ambiguous_rows > 0).sum()), sheets_ambiguous_half=int((df.ambiguous_pct >= 50).sum()),
           sheets_fill_any=int((df.fill_rows > 0).sum()),
           sheets_header2=int((df.header_levels >= 2).sum()), sheets_upper_blank=int((df.upper_blank_cols > 0).sum()),
           data_cols=int(df.data_cols.sum()), upper_blank_cols=int(df.upper_blank_cols.sum()),
           upper_blank_pct=round(100 * df.upper_blank_cols.sum() / df.data_cols.sum(), 1),
           median_header_levels=float(df.header_levels.median()), max_header_levels=int(df.header_levels.max()),
           sheets_merged=int((df.merged_all > 0).sum()), merged_total=int(df.merged_all.sum()),
           sheets_blank_rows_inside=int((df.blank_rows_inside > 0).sum()),
           sheets_clean=int(((df.ambiguous_rows == 0) & (df.fill_rows == 0) & (df.upper_blank_cols == 0)).sum()))
json.dump(tot, open(RES / "a474_public.json", "w"), ensure_ascii=False, indent=1)
print(df[["no", "sheet", "data_rows", "label_cols", "data_cols", "ambiguous_pct", "fill_pct", "wrong_fill_rows", "header_levels", "upper_blank_pct", "merged_all", "blank_rows_inside"]].round(0).to_string())
print(tot)

short = [f"{r.no:>2} {r['name'].split('（')[0].replace(' 時系列統計表', '').replace('（教育用標準データセット）', '')[:14]}／{r.sheet[:8]}" for _, r in df.iterrows()]
df["short"] = short
SRC = "出典：e-Stat ほかで公開されている Excel 14ファイル・24枚（厚生労働省、総務省統計局、農林水産省、観光庁、文部科学省、統計センター）の骨組みを集計"
# 図1 行
o = df.sort_values("ambiguous_pct")
fig, ax = plt.subplots(figsize=(9.6, 8.2))
y = np.arange(len(o))
ax.barh(y + 0.2, o.ambiguous_pct, 0.4, color=ORANGE, label="その行の文字だけでは、どの行か決まらない")
ax.barh(y - 0.2, o.fill_pct, 0.4, color=LIGHT, label="見出しの列に、上の行を見ないと埋まらない空きがある")
ax.set_yticks(y); ax.set_yticklabels(o.short, fontsize=8.5)
for i, (a, b) in enumerate(zip(o.ambiguous_pct, o.fill_pct)):
    ax.text(a + 1, i + 0.2, f"{a:.0f}%", va="center", fontsize=7.5, color=INK)
    ax.text(b + 1, i - 0.2, f"{b:.0f}%", va="center", fontsize=7.5, color=GRAY)
ax.set_xlim(0, 118); ax.set_xlabel("数字が入っている行に占める割合（%）")
ax.set_title("公開されている Excel 24枚：行の見出しを上の行に頼っている割合", loc="left")
ax.legend(loc="lower right", fontsize=9, frameon=False)
save(fig, "a474_public_rows.png", SRC)
# 図2 列
o = df.sort_values(["header_levels", "upper_blank_pct"])
fig, axs = plt.subplots(1, 2, figsize=(10.4, 7.6), sharey=True, gridspec_kw={"width_ratios": [1, 1.5]})
y = np.arange(len(o))
axs[0].barh(y, o.header_levels, color=GRAY)
for i, v in enumerate(o.header_levels): axs[0].text(v + 0.08, i, str(int(v)), va="center", fontsize=8)
axs[0].set_yticks(y); axs[0].set_yticklabels(o.short, fontsize=8.5); axs[0].set_xlabel("列の見出しの段数"); axs[0].set_title("見出しが何段あるか", loc="left", fontsize=11)
axs[1].barh(y, o.upper_blank_pct, color=BLUE)
for i, v in enumerate(o.upper_blank_pct): axs[1].text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
axs[1].set_xlim(0, 112); axs[1].set_xlabel("数字の列に占める割合（%）"); axs[1].set_title("上の段の見出しが空になっている列", loc="left", fontsize=11)
fig.suptitle("公開されている Excel 24枚：列の見出しは何段あり、どれだけ空いているか", x=0.01, ha="left", fontsize=13)
fig.tight_layout()
save(fig, "a474_public_columns.png", SRC)
