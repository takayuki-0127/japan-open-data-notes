"""683 品名に「_」や「%」を含む行を LIKE で探すと、何件を取り違えるのか

架空の品名 5,000件。一部の品名に「_」（型番の区切り）や「%」（果汁の割合など）が入っている。
5つの文字列を「含む品名」を LIKE で探す：「_M」「100%」「10%」「_」「%」。
書き方は3通り：
  エスケープなし：LIKE '%_M%'（_ は任意の1文字、% は任意の0文字以上として読まれる）
  ESCAPE 句：LIKE '%\_M%' ESCAPE '\'（DuckDB と SQL Server の両方にある書き方）
  角かっこ：LIKE '%[_]M%'（SQL Server の書き方。DuckDB では [ ] はただの文字として読まれる）
正解は Python の「文字列を含むか」（in）。LIKE の読み方は Python の正規表現でも再現し、DuckDB（1スレッド）の結果と一致を確かめる。
角かっこの SQL Server での結果は Python で再現したもの（SQL Server では未検証）。
"""
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の品名（作成者が乱数で作成、seed 683）"
rng = np.random.default_rng(683)
N = 5000
words = ["ネジ", "ボルト", "ナット", "ワッシャ", "ジュース", "ゼリー", "ノート", "ペン", "ケーブル", "テープ", "マット", "ボトル"]
names = []
for i in range(N):
    w = words[rng.integers(len(words))]; r = rng.random()
    if r < .04:
        name = f"{w}_M{rng.integers(2, 13)}"                               # 型番の区切りの _
    elif r < .07:
        name = f"果汁{rng.choice([10, 30, 50, 100])}%{w}"                   # % を含む
    elif r < .09:
        name = f"{w}_{rng.choice(['S', 'L', 'XL'])}"
    elif r < .45:
        q = rng.choice([10, 50, 100, 200, 500, 1000]) if rng.random() < .5 else rng.integers(10, 1000)
        name = f"{w} {q}{rng.choice(['g', 'ml', '枚', '本', 'cm'])}"
    elif r < .70:
        name = f"{w} {rng.choice(['A', 'B', 'C', 'M', 'K'])}{rng.integers(100, 9999)}"
    else:
        name = f"{w} {rng.choice(['MAX', 'MINI', 'PRO', 'ミニ', '徳用'])}"
    names.append(name)
P = pd.DataFrame({"item_id": np.arange(1, N + 1), "item_name": names})
DATA.mkdir(exist_ok=True)
P.to_csv(DATA / "items.csv", index=False)

TERMS = ["_M", "100%", "10%", "_", "%"]


def like_regex(pat, escape=None, brackets=False):
    """LIKE の読み方を正規表現にする（% と _、ESCAPE、SQL Server の [ ]）"""
    out, i = "", 0
    while i < len(pat):
        c = pat[i]
        if escape and c == escape:
            out += re.escape(pat[i + 1]); i += 2; continue
        if brackets and c == "[":
            j = pat.index("]", i); out += "[" + pat[i + 1:j] + "]"; i = j + 1; continue
        out += ".*" if c == "%" else "." if c == "_" else re.escape(c)
        i += 1
    return re.compile("^" + out + "$", re.S)


def pat_none(t):
    return "%" + t + "%"


def pat_esc(t):
    return "%" + t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def pat_brk(t):
    return "%" + t.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]") + "%"


con = duckdb.connect(); con.execute("SET threads=1"); con.register("items", P)
qs = ["\n".join(l for l in q.splitlines() if not l.strip().startswith("--")).strip()
      for q in (SQL / "02_like_duckdb.sql").read_text(encoding="utf-8").split(";")]
q_none, q_esc, q_brk = [q for q in qs if "?" in q][:3]

rows = []; examples = {}
for t in TERMS:
    truth = P.item_name.map(lambda s: t in s)
    r_none = P.item_name.map(lambda s: bool(like_regex(pat_none(t)).match(s)))
    r_esc = P.item_name.map(lambda s: bool(like_regex(pat_esc(t), escape="\\").match(s)))
    r_brk_ss = P.item_name.map(lambda s: bool(like_regex(pat_brk(t), brackets=True).match(s)))   # SQL Server の読み方
    r_brk_dd = P.item_name.map(lambda s: bool(like_regex(pat_brk(t)).match(s)))                  # DuckDB の読み方（[ ] は文字）
    d_none = con.execute(q_none, [pat_none(t)]).fetchone()[0]
    d_esc = con.execute(q_esc, [pat_esc(t)]).fetchone()[0]
    d_brk = con.execute(q_brk, [pat_brk(t)]).fetchone()[0]
    assert d_none == r_none.sum() and d_esc == r_esc.sum() and d_brk == r_brk_dd.sum(), t
    assert (r_esc == truth).all() and (r_brk_ss == truth).all()
    extra = P.item_name[r_none & ~truth]
    examples[t] = list(extra.drop_duplicates().head(3))
    rows.append(dict(term=t, pattern_none=pat_none(t), pattern_escape=pat_esc(t), pattern_bracket=pat_brk(t),
                     truth=int(truth.sum()), none=int(r_none.sum()), extra_none=int((r_none & ~truth).sum()),
                     escape=int(r_esc.sum()), bracket_sqlserver=int(r_brk_ss.sum()), bracket_duckdb=int(d_brk)))
S = pd.DataFrame(rows)
S.to_csv(RES / "summary.csv", index=False)
out = {"items": N, "n_with_underscore": int(P.item_name.str.contains("_", regex=False).sum()),
       "n_with_percent": int(P.item_name.str.contains("%", regex=False).sum()),
       "by_term": {r["term"]: {k: r[k] for k in ["truth", "none", "extra_none", "escape", "bracket_sqlserver", "bracket_duckdb"]}
                   for r in rows},
       "extra_examples": examples}
json.dump(out, open(RES / "a683_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：正しい件数と、エスケープなしで拾った件数
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(TERMS)); w = .38
b1 = ax.bar(x - w / 2, S.truth, w, color=BLUE, label="本当に含む品名")
b2 = ax.bar(x + w / 2, S.none, w, color=ORANGE, label="エスケープなしの LIKE で拾った品名")
for bs in (b1, b2):
    for b in bs:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.12, f"{int(b.get_height()):,}", ha="center", fontsize=9)
ax.set_yscale("log"); ax.set_ylim(10, 20000)
ax.set_xticks(x); ax.set_xticklabels([f"「{t}」を含む" for t in TERMS])
ax.set_ylabel("件数（対数の目盛り）"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"エスケープしないと、「_」や「%」が任意の文字として読まれる（品名{N:,}件）")
save(fig, "a683_counts.png", SRC)

# 図2：余分に拾った品名の例
fig, ax = plt.subplots(figsize=(9, 4.4)); ax.axis("off")
ax.text(0, 1, "エスケープなしの LIKE が余分に拾った品名の例", fontsize=13, va="top", weight="bold")
yy = .86
for t in ["_M", "100%", "10%"]:
    r = S[S.term == t].iloc[0]
    ax.text(0, yy, f"LIKE '{r.pattern_none}'　→　余分に {r.extra_none:,}件", fontsize=11.5, va="top", color=ORANGE)
    ax.text(.04, yy - .085, "　／　".join(examples[t]), fontsize=11, va="top")
    yy -= .27
ax.text(0, .07, "「_」は任意の1文字、「%」は任意の0文字以上として読まれる。「_M」は「空白＋M」なども拾う", fontsize=9.5, color=GRAY, va="top")
save(fig, "a683_examples.png", SRC)

# 図3：書き方ごとの件数（ESCAPE、角かっこ）
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = [("truth", "本当に含む", BLUE), ("escape", "ESCAPE 句", GREEN),
        ("bracket_sqlserver", "角かっこ（SQL Server の読み方を再現）", LIGHT), ("bracket_duckdb", "角かっこ（DuckDB で実行）", ORANGE)]
w = .2
for i, (c, l, colr) in enumerate(cols):
    bars = ax.bar(x + (i - 1.5) * w, S[c], w, color=colr, label=l)
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 4, f"{int(b.get_height())}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([f"「{t}」" for t in TERMS]); ax.set_ylabel("件数")
ax.set_ylim(0, S.truth.max() * 1.3); ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
ax.set_title("ESCAPE 句は両方で正しい。角かっこは DuckDB では1件も拾わない")
save(fig, "a683_methods.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
