"""605 先頭の0が落ちた商品コードや取引先コードで表をつなぐと、何件がつながらず、何件が別のコードにつながるのか

架空のコードマスタ（3,000件。古い4桁・5桁と今の6桁が混ざり、先頭が0のコードを含む）と明細5万行を作る。
明細の4割は表計算ソフトを通ったファイルから来ており、コードが数として読まれて先頭の0が落ちている。
  K0 正解（明細を文字として読み直した場合）
  K1 文字のまま結合
  K2 両方を整数にして結合
  K3 両方を6桁に0で埋めて結合
つながらない行・別のコードにつながった行・行の増え方・金額の差を数える。DuckDB（1スレッド）と pandas で一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空のコードマスタと明細（作成者が乱数で作成、seed 605）"
rng = np.random.default_rng(605)
codes = set()
spec = [(4, 1000), (5, 1200), (6, 800)]
for L, n in spec:
    while sum(len(c) == L for c in codes) < n:
        codes.add(str(int(rng.integers(0, 10 ** L))).zfill(L))
codes = sorted(codes)
# 古い4桁コードを5桁に付け替えた品目がある想定：'0123' と '00123' のように数として同じコードを60組つくる
four = [c for c in codes if len(c) == 4 and c.startswith("0")]
pairs = rng.choice(four, 60, replace=False)
codes = sorted(set(codes) | {"0" + c for c in pairs})
M = pd.DataFrame({"code": codes})
M["item_name"] = [f"品目{i:04d}" for i in range(len(M))]
M["unit_price"] = rng.choice([120, 300, 580, 980, 1500, 3200], len(M))
N = 50000
w = rng.gamma(0.8, 1.0, len(M)); w /= w.sum()
idx = rng.choice(len(M), N, p=w)
L = pd.DataFrame({"line_id": np.arange(1, N + 1), "code_true": M.code.values[idx], "qty": rng.integers(1, 6, N)})
L["via_sheet"] = rng.random(N) < 0.4
L["code_raw"] = np.where(L.via_sheet, L.code_true.str.lstrip("0").replace("", "0"), L.code_true)
L[["line_id", "code_raw", "qty"]].to_csv(DATA / "lines.csv", index=False)
M.to_csv(DATA / "master.csv", index=False)

price = M.set_index("code").unit_price
true_amt = int((L.qty * price.reindex(L.code_true).values).sum())
zero_lead = M.code.str.startswith("0")
num_dup = M.assign(n=M.code.astype(int)).groupby("n").code.transform("size") > 1


def join(key_m, key_d):
    m = M.assign(k=key_m(M.code))
    d = L.assign(k=key_d(L.code_raw))
    j = d.merge(m, on="k", how="left", suffixes=("", "_m"))
    lines_after = len(j)
    hit = j.dropna(subset=["code"])
    wrong = int((hit.code != hit.code_true).sum())
    right = int((hit.code == hit.code_true).sum())
    unmatched = int(j.code.isna().sum())
    amt = int((hit.qty * hit.unit_price).sum())
    # 正しく1行にだけつながった明細
    ok_lines = int(hit.groupby("line_id").apply(lambda g: (len(g) == 1) and (g.code.iloc[0] == g.code_true.iloc[0]), include_groups=False).sum())
    return {"rows_after_join": lines_after, "unmatched_lines": unmatched, "matched_rows_right": right, "matched_rows_wrong": wrong,
            "lines_ok": ok_lines, "lines_ok_pct": round(100 * ok_lines / N, 2), "amount": amt, "amount_diff_pct": round(100 * (amt / true_amt - 1), 2)}


res = {"K1": join(lambda s: s, lambda s: s),
       "K2": join(lambda s: s.astype(int), lambda s: s.astype(int)),
       "K3": join(lambda s: s.str.zfill(6), lambda s: s.str.zfill(6))}
con = duckdb.connect(); con.execute("SET threads=1")
con.register("lines", L[["line_id", "code_raw", "qty"]]); con.register("master", M)
qs = [q for q in (SQL / "02_code_join_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
for k, q in zip(["K1", "K2", "K3"], qs):
    n, matched = con.execute(q).fetchone()
    assert n == res[k]["rows_after_join"] and n - matched == res[k]["unmatched_lines"], k
pd.DataFrame(res).T.to_csv(RES / "summary.csv")
# 先頭が0のコードの明細のうち、シートを通った行
lead_lines = L.code_true.str.startswith("0")
out = {"master_codes": len(M), "codes_by_length": M.code.str.len().value_counts().sort_index().to_dict(),
       "codes_leading_zero": int(zero_lead.sum()), "codes_leading_zero_pct": round(100 * zero_lead.mean(), 1),
       "codes_same_number_groups": int(num_dup.sum() // 2), "lines": N, "lines_via_sheet_pct": round(100 * L.via_sheet.mean(), 1),
       "lines_leading_zero_via_sheet": int((lead_lines & L.via_sheet).sum()), "true_amount": true_amt, "results": res}
json.dump(out, open(RES / "a605_main.json", "w"), ensure_ascii=False, indent=1, default=int)

lab = {"K1": "文字のまま結合", "K2": "両方を整数にして結合", "K3": "両方を6桁に0で埋めて結合"}
ks = ["K1", "K2", "K3"]
# 図1：明細の行の行き先
fig, ax = plt.subplots(figsize=(9, 3.6))
for i, k in enumerate(ks[::-1]):
    r = res[k]; ok = r["lines_ok"]; un = r["unmatched_lines"]; bad = N - ok - un
    ax.barh(i, ok, color=GREEN); ax.barh(i, bad, left=ok, color=ORANGE); ax.barh(i, un, left=ok + bad, color=GRAY)
    ax.text(N * 1.01, i, f"つながらない {un:,}行／取り違え・二重 {bad:,}行", va="center", fontsize=9)
ax.set_yticks(range(3)); ax.set_yticklabels([lab[k] for k in ks[::-1]]); ax.set_xlim(0, N * 1.6)
ax.set_xlabel("明細5万行の行き先（緑：正しく1行につながった、橙：別のコードにもつながった、灰：つながらない）")
ax.set_title("先頭の0が落ちた明細をマスタにつなぐと")
save(fig, "a605_lines_outcome.png", SRC, y=-0.08)
# 図2：金額
fig, ax = plt.subplots(figsize=(7.5, 3.6))
v = [res[k]["amount_diff_pct"] for k in ks]
ax.bar([lab[k].replace("して", "して\n").replace("埋めて", "埋めて\n") for k in ks], v, color=[GRAY, ORANGE, BLUE])
for i, x in enumerate(v):
    ax.text(i, x, f"{x:+.1f}%", ha="center", va="bottom" if x >= 0 else "top", fontsize=10)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_ylabel("正しい金額との差（%）")
ax.set_title("結合したあとの売上金額のずれ")
ax.set_ylim(min(v) * 1.3 - 1, max(max(v), 0) * 1.5 + 1)
save(fig, "a605_amount_diff.png", SRC, y=-0.1)
# 図3：コードの桁と先頭0の割合
cl = M.assign(L=M.code.str.len(), z=zero_lead).groupby("L").agg(n=("code", "size"), z=("z", "sum"))
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.bar(cl.index.astype(str) + "桁", cl.n, color=LIGHT, label="コードの数")
ax.bar(cl.index.astype(str) + "桁", cl.z, color=BLUE, label="うち先頭が0")
for i, (n, z) in enumerate(zip(cl.n, cl.z)):
    ax.text(i, n, f"{z}/{n}（{100 * z / n:.0f}%）", ha="center", va="bottom", fontsize=9)
ax.set_ylabel("マスタのコードの数"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, cl.n.max() * 1.2)
ax.set_title("マスタのコード：桁数ごとの、先頭が0のコード")
save(fig, "a605_master_codes.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
