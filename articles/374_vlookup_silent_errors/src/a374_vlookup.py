"""374 VLOOKUP は、どんなときに黙って間違った値を返すのか
架空の商品マスタ（2,000商品）と売上表（20,000行）で、VLOOKUP・XLOOKUP の決まりを Python で再現し、
6つの場面で「エラーにならずに違う値が返る行」を数える。pandas の結合（merge）と SQL の結合（DuckDB）とも比べる。
Excel 本体では動かしていない（未検証）。乱数の種は 374。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 374
SRC = "架空の商品マスタと売上表（作成者が乱数で作成、seed 374）。VLOOKUP・XLOOKUP の動きは公開されている決まりを Python で再現したもの"
NA = "#N/A"


def key(v):
    """Excel の比べ方：文字は大文字小文字を区別しない。数と文字は別のもの"""
    return ("s", v.upper()) if isinstance(v, str) else ("n", float(v))


def vlookup(value, table, col, approx=True):
    """table は行のリスト。col は1始まりの列番号。approx=True は第4引数を省略したとき（近似一致）"""
    k = key(value)
    if not approx:                                    # 完全一致：上から探して最初の行
        for row in table:
            if key(row[0]) == k: return row[col - 1]
        return NA
    lo, hi = 0, len(table) - 1                        # 近似一致：昇順に並んでいる前提の二分探索
    while lo <= hi:
        mid = (lo + hi) // 2
        km = key(table[mid][0])
        if km[0] != k[0]:                             # 型が違う行は「大きい」とみなして左へ（数と文字を混ぜた場面は作っていない）
            hi = mid - 1; continue
        if km[1] <= k[1]: lo = mid + 1
        else: hi = mid - 1
    return table[hi][col - 1] if hi >= 0 else NA


def xlookup(value, keys, returns):
    """XLOOKUP の既定（完全一致・最初の行）。返す列は範囲で指すので、列を足してもずれない"""
    k = key(value)
    for a, b in zip(keys, returns):
        if key(a) == k: return b
    return NA


def make(rng):
    n_p, n_s = 2000, 20000
    codes = [f"P{c:05d}" for c in rng.choice(np.arange(1, 60000), n_p, replace=False)]
    master = pd.DataFrame({"商品コード": codes, "商品名": [f"商品{i:04d}" for i in range(n_p)],
                           "単価": (rng.gamma(3, 800, n_p).round(-1) + 100).astype(int)})
    pop = rng.dirichlet(np.ones(n_p) * 0.6)
    sales = pd.DataFrame({"行": np.arange(n_s), "商品コード": rng.choice(codes, n_s, p=pop), "数量": rng.integers(1, 12, n_s)})
    return master, sales


def judge(got, truth):
    """truth が None の行は「マスタにない」＝値が返ったら誤り"""
    ok = sum((g != NA and t is not None and g == t) or (g == NA and t is None) for g, t in zip(got, truth))
    silent = sum(g != NA and (t is None or g != t) for g, t in zip(got, truth))
    vis = sum(g == NA and t is not None for g, t in zip(got, truth))
    return ok, silent, vis


def main():
    rng = np.random.default_rng(SEED)
    master, sales = make(rng)
    master.to_csv(DATA / "product_master.csv", index=False); sales.to_csv(DATA / "sales.csv", index=False)
    price = dict(zip(master["商品コード"], master["単価"]))
    n = len(sales); rows = []; amount = {}
    con = duckdb.connect()

    def run(name, m_df, s_codes, truth, vl_kw, extra=None, m_for_merge=None, xl_cols=("商品コード", "単価")):
        table = m_df.values.tolist()
        g_v = [vlookup(c, table, **vl_kw) for c in s_codes]
        g_x = [xlookup(c, m_df[xl_cols[0]].tolist(), m_df[xl_cols[1]].tolist()) for c in s_codes]
        for meth, g in [("VLOOKUP", g_v), ("XLOOKUP", g_x)]:
            ok, sl, vis = judge(g, truth)
            rows.append({"場面": name, "方法": meth, "正しい": ok, "黙って違う値": sl, "エラー（#N/A）": vis, "行": n})
        # 金額への影響（VLOOKUP、エラーの行は0円として）
        q = sales["数量"].to_numpy()
        tv = np.array([0 if t is None else t for t in truth]); gv = np.array([0 if g == NA else g for g in g_v])
        amount[name] = {"正しい売上": int((tv * q).sum()), "VLOOKUPの売上": int((gv * q).sum()), "差%": round(((gv * q).sum() / (tv * q).sum() - 1) * 100, 3)}
        # pandas の結合
        md = m_for_merge if m_for_merge is not None else m_df
        s = pd.DataFrame({"行": np.arange(n), "商品コード": s_codes})
        note = ""
        try:
            j = s.merge(md[["商品コード", "単価"]], on="商品コード", how="left", validate="m:1")
            g_m = [NA if pd.isna(v) else int(v) for v in j["単価"]]
            ok, sl, vis = judge(g_m, truth)
        except Exception as e:
            ok, sl, vis = 0, 0, n; note = type(e).__name__
        rows.append({"場面": name, "方法": "結合（pandas の merge、validate='m:1'）", "正しい": ok, "黙って違う値": sl, "エラー（#N/A）": vis, "行": n, "備考": note})
        return g_v

    codes = sales["商品コード"].tolist()
    truth = [price[c] for c in codes]

    # ① 第4引数を省略（近似一致）×マスタがコード順でない
    run("① 第4引数を省略し、マスタがコード順でない", master, codes, truth, dict(col=3, approx=True))
    # ② 第4引数を省略×マスタは並んでいるが、売上にマスタにないコードがある（3%）
    m_sorted = master.sort_values("商品コード").reset_index(drop=True)
    newc = [f"P{c:05d}" for c in rng.choice(np.setdiff1d(np.arange(1, 60000), [int(c[1:]) for c in master["商品コード"]]), 300, replace=False)]
    idx = rng.choice(n, int(n * 0.03), replace=False)
    c2 = list(codes); t2 = list(truth)
    for i in idx: c2[i] = rng.choice(newc); t2[i] = None
    run("② 第4引数を省略し、マスタにないコードがある（3%）", m_sorted, c2, t2, dict(col=3, approx=True))
    # ③ 完全一致×マスタに同じコードが2行（5%の商品。上が古い単価、下が新しい単価）
    dup = master.sample(frac=0.05, random_state=SEED).copy()
    dup["単価"] = (dup["単価"] * rng.choice([1.05, 1.1, 1.2], len(dup))).round(-1).astype(int)
    m3 = pd.concat([master, dup], ignore_index=True)
    newp = dict(zip(dup["商品コード"], dup["単価"]))
    t3 = [newp.get(c, price[c]) for c in codes]
    run("③ 完全一致で、マスタに同じコードが2行ある（5%の商品）", m3, codes, t3, dict(col=3, approx=False))
    con.register("sales", sales); con.register("m3", m3)
    fan = con.execute("SELECT COUNT(*) FROM sales s LEFT JOIN m3 m ON m.商品コード = s.商品コード").fetchone()[0]
    # ④ 完全一致×売上側のコードの後ろに空白（3%）
    c4 = list(codes)
    for i in rng.choice(n, int(n * 0.03), replace=False): c4[i] = c4[i] + " "
    run("④ 完全一致で、コードの後ろに空白がある（3%）", master, c4, truth, dict(col=3, approx=False))
    # ⑤ 完全一致×数字だけのコードで、マスタは数、売上は文字
    m5 = master.copy(); m5["商品コード"] = m5["商品コード"].str[1:].astype(int)
    c5 = [c[1:] for c in codes]                                  # "00123" のような文字
    run("⑤ 完全一致で、マスタは数、売上は文字のコード", m5, c5, truth, dict(col=3, approx=False))
    # ⑥ 完全一致×マスタの「単価」の前に列（原価）を足した。式の列番号は3のまま
    m6 = master.copy(); m6.insert(2, "原価", (m6["単価"] * rng.uniform(0.45, 0.75, len(m6))).round(-1).astype(int))
    run("⑥ 完全一致で、マスタに列を足した（列番号は3のまま）", m6, codes, truth, dict(col=3, approx=False))

    R = pd.DataFrame(rows).fillna("")
    for c in ["正しい", "黙って違う値", "エラー（#N/A）"]: R[c + "%"] = (R[c] / R["行"] * 100).round(1)
    R.to_csv(RES / "scenes_by_method.csv", index=False)
    out = {"seed": SEED, "売上の行": n, "商品": len(master), "金額": amount, "③ SQL の LEFT JOIN の行数": int(fan),
           "表": {f"{r['場面']}｜{r['方法']}": {"黙って違う値": int(r["黙って違う値"]), "エラー": int(r["エラー（#N/A）"]), "正しい": int(r["正しい"])} for _, r in R.iterrows()}}
    v = R[R["方法"] == "VLOOKUP"]
    out["VLOOKUP_まとめ"] = {"黙って違う値が出た場面": int((v["黙って違う値"] > 0).sum()), "エラーで気づける場面": int(((v["黙って違う値"] == 0) & (v["エラー（#N/A）"] > 0)).sum())}
    # ①：マスタの並び方を変えて100回（近似一致の結果は並びで決まる）
    r1 = []
    tb = master.values.tolist()
    for k in range(100):
        p = rng.permutation(len(tb)); t = [tb[i] for i in p]
        g = [vlookup(c, t, 3, True) for c in codes[:2000]]
        ok, sl, vis = judge(g, truth[:2000]); r1.append((sl / 2000 * 100, vis / 2000 * 100, ok / 2000 * 100))
    r1 = np.array(r1); out["① 並びを100通りに変えた（2,000行ずつ）"] = {"黙って違う値%_平均": round(r1[:, 0].mean(), 1), "最小": round(r1[:, 0].min(), 1), "最大": round(r1[:, 0].max(), 1),
                                                         "エラー%_平均": round(r1[:, 1].mean(), 1), "正しい%_平均": round(r1[:, 2].mean(), 1)}
    json.dump(out, open(RES / "a374_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：VLOOKUP の6場面
    sc = list(v["場面"])
    fig, ax = plt.subplots(figsize=(8.8, 4.4))
    y = np.arange(len(sc))[::-1]
    ax.barh(y, v["黙って違う値%"], color=ORANGE, label="エラーにならずに違う値")
    ax.barh(y, v["エラー（#N/A）%"], left=v["黙って違う値%"], color=LIGHT, label="エラー（#N/A）")
    ax.barh(y, v["正しい%"], left=v["黙って違う値%"] + v["エラー（#N/A）%"], color="#e9e9e6", label="正しい")
    ax.set_yticks(y); ax.set_yticklabels(sc, fontsize=9)
    for yy, a, b in zip(y, v["黙って違う値%"], v["エラー（#N/A）%"]): ax.text(101, yy, f"黙って {a:.1f}%／エラー {b:.1f}%", va="center", fontsize=8.5)
    ax.set_xlim(0, 140); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xlabel("売上の行の割合（%）"); ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.4, -0.14), fontsize=9)
    ax.set_title("VLOOKUP：6つの場面で返った値")
    save(fig, "a374_vlookup_scenes.png", "出典：" + SRC, y=-0.12)
    # 図2：方法ごとの「黙って違う値」
    meths = ["VLOOKUP", "XLOOKUP", "結合（pandas の merge、validate='m:1'）"]
    fig, ax = plt.subplots(figsize=(8.8, 4.2)); w = 0.27
    for i, (m, c) in enumerate(zip(meths, [ORANGE, BLUE, GREEN])):
        s = R[R["方法"] == m]; ax.bar(np.arange(len(sc)) + (i - 1) * w, s["黙って違う値%"], w, color=c, label=m.split("（")[0] if "結合" not in m else "結合（1対多を止める指定つき）")
        for x, val in zip(np.arange(len(sc)) + (i - 1) * w, s["黙って違う値%"]):
            if val > 0: ax.text(x, val + 1, f"{val:.0f}" if val >= 10 else f"{val:.1f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(sc))); ax.set_xticklabels([s[0] for s in sc]); ax.set_ylabel("エラーにならずに違う値が返った行（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("方法を替えると、黙って違う値が返る場面は減る")
    save(fig, "a374_methods.png", "出典：" + SRC + "。①〜⑥は図1と同じ場面")
    # 図3：金額への影響
    fig, ax = plt.subplots(figsize=(8.8, 3.8))
    d = [amount[s]["差%"] for s in sc]
    ax.barh(y, d, color=[ORANGE if abs(x) > 0 else GRAY for x in d]); ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels(sc, fontsize=9)
    for yy, x in zip(y, d): ax.text(x + (1 if x >= 0 else -1), yy, f"{x:+.1f}%", va="center", ha="left" if x >= 0 else "right", fontsize=9)
    ax.set_xlim(min(d) - 22, max(d) + 22); ax.set_xlabel("売上の合計の差（%、#N/A の行は0円として足した場合）")
    ax.set_title("VLOOKUP で引いた単価で出した売上は、正しい売上からどれだけずれるか")
    save(fig, "a374_amount_impact.png", "出典：" + SRC)
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(R.to_string())


if __name__ == "__main__":
    main()
