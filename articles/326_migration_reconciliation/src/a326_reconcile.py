"""326 移行したデータは、何を照合すれば「同じ」と言えるか
架空の顧客・口座・取引を作り、新システム側に10種類の移行ミスを1つずつ入れて、5段の照合で見つかるかを数える。"""
import json, itertools, hashlib
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 326
rng = np.random.default_rng(SEED)
NC, NA, NT = 5_000, 8_000, 200_000

# ---------- 旧システムのデータ（正） ----------
sei = list("佐藤 鈴木 高橋 田中 伊藤 渡辺 山本 中村 小林 加藤 吉田 山田 佐々木 山口 松本 井上 木村 林 斎藤 清水 髙田 﨑山 濵口".split())
mei = list("太郎 花子 一郎 美咲 健 由美 翔 さくら 大輔 恵 誠 陽子 直樹 真由美 拓也 久美子".split())
town = list("中央 本町 緑町 栄 東 西 南 北 旭町 幸町".split())
def name(i):
    s = sei[rng.integers(len(sei))] + " " + mei[rng.integers(len(mei))]
    if rng.random() < 0.06: s += "（" + "株式会社" + town[rng.integers(len(town))] + "商事 代表取締役" + "）"   # 長い名前
    return s
cust = pd.DataFrame({"customer_id": np.arange(1, NC + 1)})
cust["name"] = [name(i) for i in range(NC)]
cust["address"] = [f"{town[rng.integers(10)]}{rng.integers(1,6)}－{rng.integers(1,30)}－{rng.integers(1,20)}" for _ in range(NC)]
cust["birth_date"] = pd.to_datetime("1940-01-01") + pd.to_timedelta(rng.integers(0, 24000, NC), unit="D")
cust["email"] = [f"user{i}@example.invalid" if rng.random() > 0.3 else None for i in range(1, NC + 1)]
acct = pd.DataFrame({"account_id": np.arange(1, NA + 1)})
acct["customer_id"] = rng.integers(1, NC + 1, NA)
acct["kind"] = rng.choice(["1", "2", "3"], NA, p=[0.7, 0.2, 0.1])          # 1普通 2定期 3当座
acct["opened_on"] = pd.to_datetime("2005-01-01") + pd.to_timedelta(rng.integers(0, 7300, NA), unit="D")
acct["credit_limit"] = np.where(acct.kind == "3", rng.integers(1, 50, NA) * 100000.0, np.nan)   # NULL が多い列
tx = pd.DataFrame({"tx_id": np.arange(1, NT + 1)})
tx["account_id"] = rng.integers(1, NA + 1, NT)
ts = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365 * 24 * 3600, NT), unit="s")
tx["tx_at"] = ts                                                            # 日本時間
sign = rng.choice([1, -1], NT, p=[0.45, 0.55])
tx["amount"] = np.round(sign * np.round(rng.lognormal(9.3, 1.2, NT), 2), 2)  # 円・銭つき（利息など）
tx.loc[rng.random(NT) < 0.7, "amount"] = np.round(tx["amount"]).where(rng.random(NT) < 0.7, tx["amount"])
tx["amount"] = tx["amount"].round(2)
tx["memo"] = rng.choice(["振込", "ATM", "口座振替", "利息", "手数料", None], NT, p=[.3, .3, .2, .05, .1, .05])
OLD = {"customer": cust, "account": acct, "tx": tx}
KEY = {"customer": "customer_id", "account": "account_id", "tx": "tx_id"}

# ---------- 10種類の移行ミス（新システム側に1つずつ入れる） ----------
def copy(): return {k: v.copy() for k, v in OLD.items()}
def m1(d, r):   # 行の欠け：取引が0.1%落ちる
    d["tx"] = d["tx"].drop(d["tx"].sample(frac=0.001, random_state=1).index)
def m2(d, r):   # 行の重複：取引50行が二重に入る
    d["tx"] = pd.concat([d["tx"], d["tx"].sample(50, random_state=2)], ignore_index=True)
def m3(d, r):   # 端数の切り捨て：銭が落ちる
    d["tx"]["amount"] = np.trunc(d["tx"]["amount"])
def m4(d, r):   # 符号の逆転：手数料300行だけ符号が逆
    i = d["tx"].index[d["tx"].memo == "手数料"][:300]; d["tx"].loc[i, "amount"] *= -1
def m5(d, r):   # 文字の切り詰め：名前が12文字で切れる
    d["customer"]["name"] = d["customer"]["name"].str[:12]
def m6(d, r):   # 文字の置き換え：旧字体と全角ハイフンが化ける
    d["customer"]["name"] = d["customer"]["name"].str.replace("髙", "?").str.replace("﨑", "?").str.replace("濵", "?")
    j = d["customer"].sample(200, random_state=6).index
    d["customer"].loc[j, "address"] = d["customer"].loc[j, "address"].str.replace("－", "?")
def m7(d, r):   # 日付のずれ：日本時間を UTC として入れ直し、9時間ずれる
    d["tx"]["tx_at"] = d["tx"]["tx_at"] - pd.Timedelta(hours=9)
def m8(d, r):   # NULL が 0 や空文字に
    d["account"]["credit_limit"] = d["account"]["credit_limit"].fillna(0.0)
    d["customer"]["email"] = d["customer"]["email"].fillna("")
def m9(d, r):   # ひも付けのずれ：30組の口座で、持ち主の顧客番号が入れ替わる
    a = d["account"]; i = a.sample(60, random_state=9).index.values
    v = a.loc[i, "customer_id"].values.copy(); a.loc[i[:30], "customer_id"] = v[30:]; a.loc[i[30:], "customer_id"] = v[:30]
def m10(d, r):  # 相殺する入れ違い：同じ口座の2つの取引の金額が入れ替わる（100組）
    t = d["tx"]; g = t.groupby("account_id").head(2); pairs = g.groupby("account_id").filter(lambda x: len(x) == 2)
    ids = pairs["tx_id"].values.reshape(-1, 2)[:100]
    a = t.set_index("tx_id")["amount"]; x, y = a.loc[ids[:, 0]].values.copy(), a.loc[ids[:, 1]].values.copy()
    t.loc[t.tx_id.isin(ids[:, 0]), "amount"] = y; t.loc[t.tx_id.isin(ids[:, 1]), "amount"] = x
MIS = [("M1 行の欠け（取引の0.1%）", m1), ("M2 行の重複（取引50行）", m2), ("M3 端数の切り捨て（銭）", m3),
       ("M4 符号の逆転（手数料300行）", m4), ("M5 文字の切り詰め（名前12文字）", m5), ("M6 文字の置き換え（旧字体・ハイフン）", m6),
       ("M7 日時のずれ（9時間）", m7), ("M8 NULL が 0・空文字に", m8), ("M9 ひも付けのずれ（口座30組）", m9),
       ("M10 相殺する入れ違い（100組）", m10)]
# 害のない、決めたとおりの変換（空振りを数える）
def h1(d): d["account"]["kind"] = d["account"]["kind"].map({"1": "普通", "2": "定期", "3": "当座"})   # コードを名前に
def h2(d): d["customer"]["address"] = d["customer"]["address"].str.replace("－", "-")                   # 全角ハイフンを半角に
def h3(d): d["tx"] = d["tx"].sample(frac=1, random_state=3).reset_index(drop=True)                      # 行の並びが変わる
HARMLESS = [("H1 コードを名前に（1→普通）", h1), ("H2 全角ハイフンを半角に", h2), ("H3 行の並びが変わる", h3)]

# ---------- 5段の照合（DuckDB の SQL） ----------
con = duckdb.connect()
NUM = {"customer": [], "account": ["credit_limit"], "tx": ["amount"]}
def reg(prefix, d):
    for k, v in d.items(): con.register(f"{prefix}_{k}", v)
def c1(_):   # 件数
    return any(con.sql(f"SELECT (SELECT count(*) FROM o_{t}) <> (SELECT count(*) FROM n_{t})").fetchone()[0] for t in OLD)
def c2(_):   # 合計（数値の列の合計。NULL は合計に入らない）
    out = False
    for t, cols in NUM.items():
        for c in cols:
            a, b = con.sql(f"SELECT (SELECT round(sum({c}),2) FROM o_{t}), (SELECT round(sum({c}),2) FROM n_{t})").fetchone()
            out |= (a != b)
    return out
def c3(_):   # キーの有無と重複（どちらかにしかないキー、2回出るキー）
    out = False
    for t, k in KEY.items():
        miss = con.sql(f"SELECT count(*) FROM (SELECT {k} FROM o_{t} EXCEPT SELECT {k} FROM n_{t})").fetchone()[0]
        extra = con.sql(f"SELECT count(*) FROM (SELECT {k} FROM n_{t} EXCEPT SELECT {k} FROM o_{t})").fetchone()[0]
        dup = con.sql(f"SELECT count(*) FROM (SELECT {k} FROM n_{t} GROUP BY {k} HAVING count(*)>1)").fetchone()[0]
        out |= (miss + extra + dup) > 0
    return out
def colhash(prefix, t, c, how="sum"):
    k = KEY[t]
    if how == "xor":   # キーと値のハッシュを XOR でまとめる（打ち消し合いが起きる形）
        return con.sql(f"SELECT bit_xor(hash({k}, CAST({c} AS VARCHAR))) FROM {prefix}_{t}").fetchone()[0]
    # キーと値を1つの文字列にしてからハッシュし、足し合わせる（NULL は印に置き換える）
    return con.sql(f"""SELECT sum(CAST(hash(CAST({k} AS VARCHAR) || '|' || coalesce(CAST({c} AS VARCHAR), '<NULL>')) AS HUGEINT))
                       FROM {prefix}_{t}""").fetchone()[0]
def c4(_, detail=False, how="sum"):   # 列ごとのハッシュ（キーと値を合わせたハッシュを、列ごとに1つにまとめる）
    bad = [(t, c) for t in OLD for c in OLD[t].columns if c != KEY[t] and colhash("o", t, c, how) != colhash("n", t, c, how)]
    return bad if detail else len(bad) > 0
def sample_detect(n, seeds=200):   # 抜き取り：各表から n 行のキーを引いて、全列を比べる。見つかる割合
    hit = 0
    diffs = {}
    for t, k in KEY.items():      # 違いのあるキーの集合を先に作る（抜き取りは旧側のキーから引く）
        q = " OR ".join([f"o.{c} IS DISTINCT FROM n.{c}" for c in OLD[t].columns if c != k])
        d = con.sql(f"""SELECT o.{k} FROM o_{t} o LEFT JOIN (SELECT * FROM n_{t} QUALIFY row_number() OVER (PARTITION BY {k})=1) n USING ({k})
                        WHERE n.{k} IS NULL OR {q}""").df()[k].values
        diffs[t] = set(d.tolist())
    r = np.random.default_rng(SEED + n)
    for s in range(seeds):
        found = False
        for t, k in KEY.items():
            if not diffs[t]: continue
            pick = r.choice(OLD[t][k].values, size=min(n, len(OLD[t])), replace=False)
            if diffs[t].intersection(pick.tolist()): found = True; break
        hit += found
    return hit / seeds, {t: len(v) for t, v in diffs.items()}
CHECKS = [("C1 件数", c1), ("C2 合計", c2), ("C3 キーの有無・重複", c3), ("C4 列ごとのハッシュ", c4)]
NS = [10, 30, 100, 300, 1000, 3000]

reg("o", OLD)
rows, samp, where = [], [], []
for name_, f in MIS:
    d = copy(); f(d, rng); reg("n", d)
    r = {"ミス": name_}
    for cn, cf in CHECKS: r[cn] = int(bool(cf(None)))
    p, nd = sample_detect(300)
    r["C5 抜き取り300行"] = p
    r["（参考）XOR でまとめたハッシュ"] = int(bool(c4(None, how="xor")))
    r["違う行（顧客）"], r["違う行（口座）"], r["違う行（取引）"] = nd["customer"], nd["account"], nd["tx"]
    rows.append(r)
    where.append({"ミス": name_, "ハッシュが違った列": "、".join(f"{t}.{c}" for t, c in c4(None, True))})
    for n in NS: samp.append({"ミス": name_, "n": n, "見つかる割合": sample_detect(n)[0]})
res = pd.DataFrame(rows); res.to_csv(RES / "detect_matrix.csv", index=False)
pd.DataFrame(samp).to_csv(RES / "sampling_curve.csv", index=False)
pd.DataFrame(where).to_csv(RES / "hash_columns.csv", index=False)

# 害のない変換での空振り
fa = []
for name_, f in HARMLESS:
    d = copy(); f(d); reg("n", d)
    r = {"変換": name_}
    for cn, cf in CHECKS: r[cn] = int(bool(cf(None)))
    r["C5 抜き取り300行"] = sample_detect(300)[0]
    r["（参考）XOR でまとめたハッシュ"] = int(bool(c4(None, how="xor")))
    fa.append(r)
fa = pd.DataFrame(fa); fa.to_csv(RES / "false_alarms.csv", index=False)

print(res.to_string()); print(fa.to_string())
# 全部見つけるのに必要な最小の組み合わせ（C1〜C4 は 0/1、C5 は 300行で95%以上を「見つかる」とする）
D = res[[c for c, _ in CHECKS]].astype(bool).copy(); D["C5 抜き取り300行"] = res["C5 抜き取り300行"] >= 0.95
names = list(D.columns); best = None
for k in range(1, 6):
    for comb in itertools.combinations(names, k):
        if D[list(comb)].any(axis=1).all(): best = best or []; best.append(comb)
    if best: break
no_hash = None
for k in range(1, 5):
    c_ = [comb for comb in itertools.combinations([n for n in names if "ハッシュ" not in n], k) if D[list(comb)].any(axis=1).all()]
    if c_: no_hash = c_; break
missed_wo_hash = res.loc[~D[[n for n in names if "ハッシュ" not in n]].any(axis=1), "ミス"].tolist()
main = {"rows": {"customer": NC, "account": NA, "tx": NT},
        "found_by_check": {c: int(D[c].sum()) for c in names},
        "min_combination": [list(c) for c in (best or [])], "min_without_hash": [list(c) for c in no_hash] if no_hash else None,
        "missed_by_C1C2C3C5": missed_wo_hash,
        "found_by_xor_hash": int(res["（参考）XOR でまとめたハッシュ"].sum()),
        "missed_by_xor_hash": res.loc[res["（参考）XOR でまとめたハッシュ"] == 0, "ミス"].tolist(),
        "found_by_C1C2C3": int(D[["C1 件数", "C2 合計", "C3 キーの有無・重複"]].any(axis=1).sum()),
        "false_alarms": {c: int(fa[c].sum()) if c != "C5 抜き取り300行" else int((fa[c] >= 0.95).sum()) for c in names},
        "sampling_300": dict(zip(res["ミス"], res["C5 抜き取り300行"].round(3)))}
json.dump(main, open(RES / "a326_main.json", "w"), ensure_ascii=False, indent=1)
print(res.to_string()); print(fa.to_string()); print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(where).to_string())

SRC = "架空のデータ（作成者が乱数で作成、seed 326）"
# 図1：ミス×照合
fig, ax = plt.subplots(figsize=(8.6, 5.2))
M = res[[c for c, _ in CHECKS] + ["C5 抜き取り300行"]].values.astype(float)
ax.imshow(M, cmap="Blues", vmin=0, vmax=1.6, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M[i, j]; s = ("見つかる" if v == 1 else "見逃す") if j < 4 else f"{v*100:.0f}%"
        ax.text(j, i, s, ha="center", va="center", fontsize=9.5, color=INK if v < 0.6 else "white", weight="bold" if v >= 0.95 else None)
ax.set_xticks(range(5)); ax.set_xticklabels(["C1 件数", "C2 合計", "C3 キーの\n有無・重複", "C4 列ごとの\nハッシュ", "C5 抜き取り\n300行"], fontsize=9.5)
ax.set_yticks(range(10)); ax.set_yticklabels(res["ミス"], fontsize=9.5); ax.xaxis.tick_top()
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("10種類の移行ミスは、どの照合で見つかったか（抜き取りは200回のうち見つかった割合）", fontsize=11.5, pad=34, loc="left", x=-0.55)
save(fig, "a326_matrix.png", SRC)
# 図2：抜き取りの行数
sc = pd.DataFrame(samp); fig, ax = plt.subplots(figsize=(8.2, 4.6))
cols = plt.cm.tab10(np.linspace(0, 1, 10))
for (nm, g), c in zip(sc.groupby("ミス", sort=False), cols):
    ax.plot(g["n"], g["見つかる割合"] * 100, marker="o", ms=3.5, lw=1.6, color=c, label=nm.split("（")[0])
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n:,}" for n in NS]); ax.set_xlabel("各表から抜き取る行数"); ax.set_ylabel("見つかった割合（%）")
ax.axhline(95, color=GRAY, lw=0.8, ls="--"); ax.legend(fontsize=8.5, ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), columnspacing=1.0, handlelength=1.4)
ax.set_title("抜き取りは、全部の行が違うミスにはすぐ当たり、数十行だけのミスにはほとんど当たらない", fontsize=11.5, loc="left")
save(fig, "a326_sampling.png", SRC, y=-0.16)
# 図3：照合ごとのまとめ（表）
tab = pd.DataFrame({"照合": names,
                    "見つけたミス（10種類中）": [main["found_by_check"][c] for c in names],
                    "害のない変換で鳴った数（3種類中）": [main["false_alarms"][c] for c in names],
                    "分かること": ["表のどれかで行数が違う", "数値の列の合計が違う", "どのキーが足りない・多い・重なる", "どの表のどの列が違う（行は分からない）", "当たれば、どの行のどの列が違う"]})
tab.to_csv(RES / "check_summary.csv", index=False)
fig, ax = plt.subplots(figsize=(9.2, 3.0)); ax.axis("off")
t = ax.table(cellText=tab.values, colLabels=["照合", "見つけたミス\n（10種類中）", "害のない変換で鳴った数\n（3種類中）", "分かること"], loc="center", cellLoc="center", colWidths=[0.2, 0.15, 0.22, 0.43])
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.7)
for (r_, c_), cell in t.get_celld().items():
    cell.set_edgecolor("#d0d0d0")
    if r_ == 0: cell.set_facecolor("#eef3fa"); cell.set_text_props(weight="bold"); cell.set_height(cell.get_height() * 1.6)
ax.set_title("照合ごとの、見つけた数・空振りの数・分かること", fontsize=11.5, loc="left")
save(fig, "a326_summary.png", SRC, y=0.02)
