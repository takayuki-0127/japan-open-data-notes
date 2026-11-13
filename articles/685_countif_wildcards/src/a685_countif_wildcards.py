"""685 Excel の COUNTIF で「*」や「?」を含む品名を数えると、何件を多く数えるのか

架空の品名マスタ（240品目、うち記号「*」「?」を含む品名が36品目）と販売明細3万行を作り、
品名ごとの件数を
  正解        ：品名が完全に一致する行を数える
  COUNTIF そのまま ：COUNTIF(範囲, 品名) と同じ規則（* は任意の文字列、? は任意の1文字、大文字小文字は区別しない）
  COUNTIF ~ で打ち消し：条件の「*」「?」「~」の前に「~」を付ける
で数え、多く数えた品目と件数を比べる。SUMIF でも同じ規則なので、金額も比べる。
Excel の規則は Python で再現した（Excel では未検証）。
"""
import json, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, LIGHT, INK

SRC = "出典：架空の品名と販売明細（作成者が乱数で作成、seed 685）"
rng = np.random.default_rng(685)
DATA.mkdir(exist_ok=True)


def countif_regex(crit, escape=False):
    """COUNTIF の条件文字列を正規表現に直す（~* ~? ~~ は文字そのもの）"""
    if escape:
        crit = re.sub(r"([~*?])", r"~\1", crit)
    out, i = "", 0
    while i < len(crit):
        c = crit[i]
        if c == "~" and i + 1 < len(crit) and crit[i + 1] in "*?~":
            out += re.escape(crit[i + 1]); i += 2; continue
        out += ".*" if c == "*" else "." if c == "?" else re.escape(c)
        i += 1
    return re.compile(out, re.IGNORECASE | re.DOTALL)


# ---- 品名マスタ ----
names = []
# 記号なしのふつうの品名
for k in range(180):
    names.append(f"{rng.choice(['ボルト','ナット','ワッシャ','パイプ','テープ','ケーブル','フック','バンド'])}{k:03d}")
# 記号を含む品名と、その「なかま」（記号の所が別の文字）
fam_rows = []
for k, (stem, tail) in enumerate([("ネジM3", "10"), ("ネジM4", "12"), ("ネジM5", "16"), ("棚板900", "450"), ("角材30", "40"), ("板厚5", "910")]):
    star = f"{stem}*{tail}"                  # 「×」の代わりに「*」で入れた品名
    names += [star, f"{stem}x{tail}", f"{stem}×{tail}", f"{stem}-{tail}", f"{stem}{tail}"]
    fam_rows.append((star, [f"{stem}x{tail}", f"{stem}×{tail}", f"{stem}-{tail}", f"{stem}{tail}"]))
for k, base in enumerate(["袋", "箱", "缶", "瓶", "札", "鍵"]):
    q = f"{base}?"                           # 「サイズ未定」の意味で「?」を付けた品名
    names += [q, f"{base}A", f"{base}B", f"{base}S", f"{base}L"]
for k in range(6):
    names.append(f"お試し*{k}")              # 「*」を飾りに使った品名
names = list(dict.fromkeys(names))
master = pd.DataFrame({"item": names})
master["has_wild"] = master["item"].str.contains(r"[*?]")
master["price"] = rng.integers(20, 400, len(master)) * 10

# ---- 販売明細 ----
w = rng.gamma(0.8, 1.0, len(master)); w /= w.sum()
idx = rng.choice(len(master), 30000, p=w)
lines = pd.DataFrame({"line_id": np.arange(1, 30001), "item": master["item"].values[idx]})
lines["qty"] = rng.integers(1, 6, len(lines))
lines["amount"] = lines["qty"] * master["price"].values[idx]
lines.to_csv(DATA / "sales_lines.csv", index=False)
master[["item", "price"]].to_csv(DATA / "items.csv", index=False)

# ---- 数える ----
vc = lines["item"].value_counts(); amt = lines.groupby("item")["amount"].sum()
uniq = pd.Series(vc.index)
rows = []
for it in master["item"]:
    r_raw, r_esc = countif_regex(it), countif_regex(it, escape=True)
    m_raw = uniq[uniq.map(lambda s: bool(r_raw.fullmatch(s)))]
    m_esc = uniq[uniq.map(lambda s: bool(r_esc.fullmatch(s)))]
    rows.append({"item": it, "has_wild": "*" in it or "?" in it,
                 "true": int(vc.get(it, 0)), "countif": int(vc[m_raw].sum()), "countif_escaped": int(vc[m_esc].sum()),
                 "true_amount": int(amt.get(it, 0)), "sumif": int(amt[m_raw].sum()), "sumif_escaped": int(amt[m_esc].sum()),
                 "matched_names": len(m_raw)})
R = pd.DataFrame(rows)
R["extra"] = R["countif"] - R["true"]; R["ratio"] = R["countif"] / R["true"].replace(0, np.nan)
R.to_csv(RES / "by_item.csv", index=False)
assert (R["countif_escaped"] == R["true"]).all() and (R["sumif_escaped"] == R["true_amount"]).all()
assert (R.loc[~R["has_wild"], "extra"] == 0).all()

W = R[R["has_wild"]]
out = {"items": len(R), "items_with_wildcard": int(R["has_wild"].sum()), "lines": len(lines),
       "items_overcounted": int((R["extra"] > 0).sum()),
       "wild_lines_true": int(W["true"].sum()), "wild_lines_countif": int(W["countif"].sum()),
       "wild_overcount_ratio": round(W["countif"].sum() / W["true"].sum(), 2),
       "wild_amount_true": int(W["true_amount"].sum()), "wild_amount_sumif": int(W["sumif"].sum()),
       "max_ratio": round(float(R["ratio"].max()), 1), "max_ratio_item": R.loc[R["ratio"].idxmax(), "item"],
       "star_items_median_ratio": round(float(W[W["item"].str.contains(r"\*")]["ratio"].median()), 2),
       "q_items_median_ratio": round(float(W[W["item"].str.contains(r"\?")]["ratio"].median()), 2),
       "escaped_all_correct": True,
       "sum_extra_lines": int(R["extra"].sum())}
fam = []
for star, others in fam_rows:
    fam.append({"item": star, "true": int(vc.get(star, 0)), "countif": int(R.set_index("item").loc[star, "countif"]),
                **{o: int(vc.get(o, 0)) for o in others}})
out["example"] = fam[0]
json.dump(out, open(RES / "a685_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：記号を含む品名ごとの正解と COUNTIF
W2 = W.sort_values("ratio", ascending=False)
fig, ax = plt.subplots(figsize=(9, 7))
y = np.arange(len(W2))
ax.barh(y, W2["countif"], color=ORANGE, label="COUNTIF そのまま")
ax.barh(y, W2["true"], color=BLUE, label="正解（完全一致）")
ax.set_yticks(y); ax.set_yticklabels(W2["item"], fontsize=7.5); ax.invert_yaxis()
ax.set_xlabel("行数"); ax.legend(frameon=False, loc="lower right")
ax.set_title(f"記号を含む{len(W2)}品目：COUNTIF は「なかま」の行まで数える")
save(fig, "a685_by_item.png", SRC)

# 図2：何倍に数えたか（* と ?）
fig, ax = plt.subplots(figsize=(8, 4))
grp = [W[W["item"].str.contains(r"\*")]["ratio"].dropna(), W[W["item"].str.contains(r"\?")]["ratio"].dropna()]
ax.boxplot(grp, vert=False, widths=0.5)
for i, g in enumerate(grp, 1):
    ax.scatter(g, np.full(len(g), i) + rng.uniform(-0.12, 0.12, len(g)), s=14, color=ORANGE, zorder=3)
ax.set_yticks([1, 2]); ax.set_yticklabels(["「*」を含む品名", "「?」を含む品名"])
ax.axvline(1, color=INK, ls="--", lw=0.8); ax.set_xlabel("COUNTIF の件数 ÷ 正しい件数（倍）")
ax.set_title("「~」で打ち消せば、どの品目も正しい件数（1倍）に戻った")
save(fig, "a685_ratio.png", SRC)

# 図3：例「ネジM3*10」
e = fam[0]; labels = [e["item"]] + list(e.keys())[3:]
vals = [e["true"]] + [e[k] for k in list(e.keys())[3:]]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(range(len(vals)), vals, color=[BLUE] + [LIGHT] * (len(vals) - 1))
ax.axhline(e["countif"], color=ORANGE, ls="--", lw=1.5)
ax.text(len(vals) - 0.6, e["countif"], f"COUNTIF(範囲,\"{e['item']}\") = {e['countif']}", color=ORANGE, ha="right", va="bottom", fontsize=9)
for i, v in enumerate(vals):
    ax.text(i, v, f"{v}", ha="center", va="bottom", fontsize=9)
ax.set_xticks(range(len(vals))); ax.set_xticklabels(labels, fontsize=9); ax.set_ylabel("行数")
ax.set_title(f"「{e['item']}」の正しい件数は{e['true']}行。COUNTIF は5つの品名をまとめて数えた")
save(fig, "a685_example.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
