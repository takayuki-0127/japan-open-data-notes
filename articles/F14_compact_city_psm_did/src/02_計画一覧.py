"""02 立地適正化計画の一覧を作る：PDF の文字（色・位置）から市町村名と「作成・公表済み／取組中」を読み、市町村コードを付ける。
出力：data/plans.csv（1行＝1市町村、各時点の状態と最初に「公表済み」になった時点）"""
import json, re, collections
import pandas as pd
from common import RAW, DATA

SNAP = {"H2907": "2017-07-31", "H3005": "2018-05-01", "H3012": "2018-12-31", "R0204": "2020-04-01", "R0207": "2020-07-31"}
HEAD = {"H2907": (357, 112), "H3005": (407, 161), "H3012": (440, 186), "R0204": (522, 326), "R0207": (542, 339)}  # PDF に書かれた合計（取組・公表）
P = ['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県','茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県','新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県','静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県','徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県']

ss = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", skiprows=2, dtype=str)
muni = collections.defaultdict(list)
for _, r in ss.iterrows():
    muni[r["市区町村"]].append((r["都道府県"], r["地域コード"]))

def tokens(cs):
    md = collections.Counter(c[4] for c in cs).most_common(1)[0][0]   # 市町村名の文字サイズ（いちばん多いもの）
    cs = sorted([c for c in cs if c[4] <= md], key=lambda c: (-c[3], c[2]))
    out, cur = [], None
    for ch, col, x, y, fs in cs:   # 同じ行・同じ色で隣り合う文字をつなぐ
        if cur and abs(y - cur["y"]) < 1 and x - cur["xe"] < 0.4 * fs and col == cur["col"]:
            cur["s"] += ch; cur["xe"] = x + fs
        else:
            if cur: out.append(cur)
            cur = {"s": ch, "col": col, "x": x, "y": y, "xe": x + fs}
    out.append(cur)
    res = []
    for t in out:   # つながってしまった「県名＋市町村名」「市町村名＋市町村名」を分ける
        s, i = t["s"], 0
        w = (t["xe"] - t["x"]) / max(len(s), 1)
        while i < len(s):
            m = next((p for p in P if s.startswith(p, i)), None)
            if not m:
                m = None
                for j in range(i + 2, min(len(s), i + 9) + 1):
                    if s[i:j] in muni and (j == len(s) or any(s.startswith(p, j) for p in P)
                                           or any(s[j:k] in muni for k in range(j + 2, min(len(s), j + 9) + 1))):
                        m = s[i:j]; break
                if m is None:
                    m = s[i:]
            res.append({"s": m, "col": t["col"], "x": t["x"] + i * w, "y": t["y"]})
            i += len(m)
    return res

A = json.load(open(RAW / "plans_pdf_chars.json"))
rows = []
for k, cs in A.items():
    T = tokens(cs)
    labels = [t for t in T if t["s"] in P]           # 県名の見出し（各県の並びの先頭に置かれている）
    names = [t for t in T if t["s"] not in P]
    cols = sorted(set(round(t["x"]) for t in labels))
    colof = lambda x: min(range(len(cols)), key=lambda i: abs(cols[i] - x))
    lab = sorted([(colof(t["x"]), -t["y"], t["s"]) for t in labels])
    n_ok = 0
    for t in names:   # 市町村名の県＝同じ列で、すぐ上にある県名（なければ前の列の最後の県名）
        c = colof(t["x"])
        cand = [l for l in lab if l[0] == c and -l[1] >= t["y"] - 1]
        if cand:
            pref = max(cand, key=lambda l: l[1])[2]
        else:
            prev = [l for l in lab if l[0] < c]; pref = prev[-1][2] if prev else None
        ok = [m for m in muni.get(t["s"], []) if m[0] == pref] or (muni[t["s"]] if len(muni.get(t["s"], [])) == 1 else [])
        if not ok:
            print("  照合できない：", k, pref, t["s"]); continue
        rows.append({"snap": k, "code": ok[0][1], "pref": ok[0][0], "name": t["s"],
                     "status": "公表済み" if t["col"] != "0,0,0" else "取組中"})
df = pd.DataFrame(rows)
for k, (tot, pub) in HEAD.items():
    d = df[df.snap == k]
    print(f"{k}（{SNAP[k]}）：取組 {len(d)}（PDF {tot}）・公表 {(d.status=='公表済み').sum()}（PDF {pub}）")
    assert len(d) == tot and (d.status == "公表済み").sum() == pub

w = df.pivot_table(index=["code", "pref", "name"], columns="snap", values="status", aggfunc="first").reset_index()
order = list(SNAP)
def first_pub(r):
    for k in order:
        if r.get(k) == "公表済み": return SNAP[k]
    return None
w["first_pub"] = w.apply(first_pub, axis=1)
# 前の時点で公表済みなのに後の時点で外れている市町村がないか
bad = [r.code for _, r in w.iterrows() if isinstance(r.first_pub, str) and any(r.get(k) != "公表済み" for k in order if SNAP[k] > r.first_pub)]
print("公表済みの並びに矛盾がある市町村：", len(bad))
w = w[["code", "pref", "name"] + order + ["first_pub"]].sort_values("code")
w.to_csv(DATA / "plans.csv", index=False, encoding="utf-8-sig")
print(w.first_pub.value_counts(dropna=False).sort_index())
