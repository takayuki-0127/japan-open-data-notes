"""515 フィルタで隠した行も含めて合計すると、表の合計は何%多くなるのか（SUM と SUBTOTAL）（実務の型）

Excel の SUM・SUBTOTAL(9)・SUBTOTAL(109)・AGGREGATE(9, 5/7) が、
「フィルタで隠した行」「手で非表示にした行」「途中の小計の行」「エラーの値」をどう扱うかを
Microsoft のヘルプに書かれた仕様のとおり Python で再現し、架空の売上明細の表（1,000枚）で比べる。
Excel 本体では動かしていない（未検証）。
"""
import json, math
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 515
SRC = "架空の売上明細の表（作成者が乱数で作成、seed 515）。Excel の関数の扱いは仕様を Python で再現（Excel 本体では未検証）"
ERR = "#N/A"


AGG_OPT = {0: (True, False, False), 1: (True, True, False), 2: (True, False, True), 3: (True, True, True),
           4: (False, False, False), 5: (False, True, False), 6: (False, False, True), 7: (False, True, True)}
# AGGREGATE の option → （範囲内の SUBTOTAL・AGGREGATE を無視、非表示の行を無視、エラーを無視）


def excel_sum(cells, func):
    """cells: dict のリスト（v=数値/文字/ERR, filt=フィルタで隠れた, hid=手で非表示, sub=SUBTOTAL か AGGREGATE の式の行）
    func: 'SUM' / 'SUBTOTAL9' / 'SUBTOTAL109' / 'AGG9_k'（AGGREGATE(9, k)）"""
    if func == "SUM":
        nest, hide_f, hide_m, err = False, False, False, False
    elif func == "SUBTOTAL9":
        nest, hide_f, hide_m, err = True, True, False, False      # フィルタで隠れた行だけ除く（手で隠した行は数える）
    elif func == "SUBTOTAL109":
        nest, hide_f, hide_m, err = True, True, True, False       # 両方の非表示を除く
    else:
        nest, hid, err = AGG_OPT[int(func.split("_")[1])]
        hide_f = hide_m = hid                                     # AGGREGATE の「非表示の行」はフィルタも手も同じに扱うと置いた
    tot = 0.0
    for c in cells:
        if nest and c["sub"]:
            continue
        if (hide_f and c["filt"]) or (hide_m and c["hid"]):
            continue
        v = c["v"]
        if v == ERR:
            if err:
                continue
            return ERR                                 # エラーがあれば結果もエラー
        if isinstance(v, (int, float)):
            tot += v                                   # 文字は数えない
    return tot


def make_table(rng, n_reg=8, rows_per=25, keep=None, hide_p=0.0, err_p=0.0, with_sub=False):
    cells = []
    if keep is None:
        keep = rng.integers(1, n_reg + 1)
    kept = set(rng.choice(n_reg, keep, replace=False))
    for r in range(n_reg):
        amt = np.round(rng.lognormal(10, 1.0, rows_per), 0)
        block = []
        for a in amt:
            v = ERR if rng.random() < err_p else float(a)
            block.append({"reg": r, "v": v, "filt": r not in kept, "hid": rng.random() < hide_p, "sub": False})
        cells += block
        if with_sub:                                   # 地域ごとの小計行（SUBTOTAL(9) の式、フィルタ後も見える形にしておく）
            sv = excel_sum(block, "SUBTOTAL9")
            cells.append({"reg": r, "v": sv, "filt": r not in kept, "hid": False, "sub": True})
    return cells, keep


def visible_detail(cells):
    vals = [c["v"] for c in cells if not c["sub"] and not c["filt"] and not c["hid"]]
    if ERR in vals:
        return ERR
    return float(sum(vals))


def unit_tests():
    """関数の扱いの小さな表で、ヘルプの説明どおりになるかを確かめる"""
    t = [{"v": 10.0, "filt": False, "hid": False, "sub": False},
         {"v": 20.0, "filt": True, "hid": False, "sub": False},
         {"v": 30.0, "filt": False, "hid": True, "sub": False},
         {"v": "abc", "filt": False, "hid": False, "sub": False},
         {"v": 60.0, "filt": False, "hid": False, "sub": True}]
    assert excel_sum(t, "SUM") == 120 and excel_sum(t, "SUBTOTAL9") == 40 and excel_sum(t, "SUBTOTAL109") == 10
    assert excel_sum(t, "AGG9_3") == 10 and excel_sum(t, "AGG9_7") == 70 and excel_sum(t, "AGG9_4") == 120
    t2 = t + [{"v": ERR, "filt": False, "hid": True, "sub": False}]
    assert excel_sum(t2, "SUBTOTAL109") == 10 and excel_sum(t2, "SUBTOTAL9") == ERR and excel_sum(t2, "AGG9_3") == 10
    t3 = t + [{"v": ERR, "filt": False, "hid": False, "sub": False}]
    assert excel_sum(t3, "SUBTOTAL109") == ERR and excel_sum(t3, "AGG9_3") == 10
    return True


def main():
    rng = np.random.default_rng(SEED)
    out = {"seed": SEED, "単体の確認": unit_tests()}
    F = ["SUM", "SUBTOTAL9", "SUBTOTAL109", "AGG9_3"]
    # A：フィルタで残す地域の数（1〜8）× 手で隠す行の割合
    rows = []
    for hide in [0.0, 0.05]:
        for keep in range(1, 9):
            for _ in range(200):
                cells, _ = make_table(rng, keep=keep, hide_p=hide)
                vis = visible_detail(cells)
                for f in F:
                    rows.append({"手で隠す割合": hide, "残す地域": keep, "関数": f, "過大": excel_sum(cells, f) / vis - 1})
    a = pd.DataFrame(rows); ag = a.groupby(["手で隠す割合", "残す地域", "関数"])["過大"].median().unstack(); ag.to_csv(RES / "by_keep.csv")
    out["過大_中央値_隠し0"] = ag.loc[0.0].to_dict("index"); out["過大_中央値_隠し5%"] = ag.loc[0.05].to_dict("index")
    # B：1,000枚のランダムな表（残す地域ランダム、手で隠す 0〜10%、小計行あり3割、エラーあり1割）
    recs = []
    for i in range(1000):
        hide = float(rng.choice([0, 0.02, 0.05, 0.10])); ws = rng.random() < 0.3; ep = 0.01 if rng.random() < 0.1 else 0.0
        cells, keep = make_table(rng, hide_p=hide, err_p=ep, with_sub=ws)
        vis = visible_detail(cells)
        r = {"表": i, "残す地域": int(keep), "手で隠す割合": hide, "小計行": ws, "エラーあり": any(c["v"] == ERR for c in cells),
             "見えている明細の合計": vis}
        for f in F + ["AGG9_1", "AGG9_7"]:
            v = excel_sum(cells, f); r[f] = v
        recs.append(r)
    b = pd.DataFrame(recs)
    def judge(row, f):
        v, t = row[f], row["見えている明細の合計"]
        if v == ERR: return "エラー"
        if t == ERR: return "見える行にエラー（比べられない）"
        if abs(v - t) < 1e-6: return "一致"
        return "多い" if v > t else "少ない"
    summ = {f: b.apply(lambda r: judge(r, f), axis=1).value_counts().to_dict() for f in F + ["AGG9_1", "AGG9_7"]}
    out["1000枚の判定"] = summ
    num = b[(b["SUM"] != ERR)].copy()
    num = num[num["見えている明細の合計"] != ERR]
    num["SUM過大"] = num["SUM"].astype(float) / num["見えている明細の合計"].astype(float) - 1
    out["SUMの過大_中央値"] = float(num["SUM過大"].median())
    out["SUMの過大_小計行あり_中央値"] = float(num[num["小計行"]]["SUM過大"].median())
    out["SUMの過大_小計行なし_中央値"] = float(num[~num["小計行"]]["SUM過大"].median())
    b.astype({"SUM": str, "SUBTOTAL9": str, "SUBTOTAL109": str, "AGG9_3": str, "AGG9_1": str, "AGG9_7": str, "見えている明細の合計": str}).to_csv(RES / "tables_1000.csv", index=False)
    # DuckDB：明細を縦長の表にして、同じ合計を SQL の FILTER で出す（小計行・エラーなしの1枚）
    cells, _ = make_table(np.random.default_rng(SEED + 1), keep=3, hide_p=0.05)
    df = pd.DataFrame([{"amount": c["v"], "filtered_out": c["filt"], "manual_hidden": c["hid"]} for c in cells])
    con = duckdb.connect(); con.register("detail", df)
    q = con.execute(open(SQL / "02_sum_duckdb.sql").read()).df().iloc[0]
    assert abs(q["sum_all"] - excel_sum(cells, "SUM")) < 1e-6
    assert abs(q["subtotal_9"] - excel_sum(cells, "SUBTOTAL9")) < 1e-6
    assert abs(q["subtotal_109"] - excel_sum(cells, "SUBTOTAL109")) < 1e-6
    out["DuckDB_一致"] = True
    json.dump(out, open(RES / "a515_main.json", "w"), ensure_ascii=False, indent=1, default=str)

    # 図1：残す地域の数 × 過大（手で隠す 5%）
    g = ag.loc[0.05] * 100
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    ax.plot(g.index, g["SUM"], marker="o", color=ORANGE, label="SUM（隠した行も足す）")
    ax.plot(g.index, g["SUBTOTAL9"], marker="s", color=BLUE, label="SUBTOTAL(9)（手で隠した行は足す）")
    ax.plot([], [], " ", label="SUBTOTAL(109)・AGGREGATE(9,3) は0%")
    for x, v in zip(g.index, g["SUM"]): ax.text(x, v * 1.25, f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", fontsize=8, color=ORANGE)
    for x, v in zip(g.index, g["SUBTOTAL9"]): ax.text(x, v * 0.72, f"{v:.1f}", ha="center", fontsize=8, color=BLUE)
    ax.set_yscale("log"); ax.set_ylim(2, 2000); ax.set_xlabel("フィルタで残した地域の数（8地域のうち）")
    ax.set_ylabel("見えている明細の合計より多い分（%）")
    ax.set_title("残す行が少ないほど、SUM の合計は見えている合計から離れる", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a515_by_keep.png", SRC + "。\n各200枚の中央値、手で隠した行5%。SUBTOTAL(109) と AGGREGATE(9,3) はどれも0%（対数目盛のため線は描いていない）")
    # 図2：SUBTOTAL(9) と 109 の差（手で隠す割合別、全地域を残す）
    rows2 = []
    for hide in [0, 0.02, 0.05, 0.10, 0.20]:
        for _ in range(300):
            cells, _ = make_table(rng, keep=8, hide_p=hide)
            vis = visible_detail(cells)
            rows2.append({"hide": hide, "s9": excel_sum(cells, "SUBTOTAL9") / vis - 1})
    c2 = pd.DataFrame(rows2).groupby("hide")["s9"].median() * 100; c2.to_csv(RES / "subtotal9_manual_hidden.csv")
    out["SUBTOTAL9_手で隠した行の過大"] = c2.to_dict()
    json.dump(out, open(RES / "a515_main.json", "w"), ensure_ascii=False, indent=1, default=str)
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    ax.bar(range(len(c2)), c2.values, color=BLUE)
    for i, v in enumerate(c2.values): ax.text(i, v + 0.4, f"+{v:.1f}%", ha="center", fontsize=9)
    ax.set_xticks(range(len(c2)), [f"{h*100:.0f}%" for h in c2.index]); ax.set_xlabel("手で非表示にした行の割合（フィルタなし）")
    ax.set_ylabel("SUBTOTAL(9) が多い分（%）")
    ax.set_title("SUBTOTAL(9) は、手で非表示にした行を合計に入れる", fontsize=12)
    save(fig, "a515_manual_hidden.png", SRC + "。\n各300枚の中央値。SUBTOTAL(109) と AGGREGATE(9,1)・(9,3) はどれも0%")
    # 図3：1,000枚での判定の内訳
    order = ["一致", "多い", "少ない", "エラー", "見える行にエラー（比べられない）"]
    cols = {"一致": GREEN, "多い": ORANGE, "少ない": LIGHT, "エラー": INK, "見える行にエラー（比べられない）": GRAY}
    lab = {"SUM": "SUM", "SUBTOTAL9": "SUBTOTAL(9)", "SUBTOTAL109": "SUBTOTAL(109)", "AGG9_1": "AGGREGATE(9,1)", "AGG9_3": "AGGREGATE(9,3)", "AGG9_7": "AGGREGATE(9,7)"}
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    fs = ["SUM", "SUBTOTAL9", "SUBTOTAL109", "AGG9_1", "AGG9_3", "AGG9_7"]
    for yi, f in enumerate(fs):
        left = 0
        for k in order:
            w = summ[f].get(k, 0) / 10
            if w > 0:
                ax.barh(yi, w, left=left, color=cols[k], label=k if yi == 0 or k not in summ["SUM"] else None)
                if w >= 4: ax.text(left + w / 2, yi, f"{w:.0f}", ha="center", va="center", fontsize=8.5, color="white" if k in ("エラー", "多い", "一致") else INK)
                left += w
    ax.set_yticks(range(len(fs)), [lab[f] for f in fs]); ax.invert_yaxis(); ax.set_xlim(0, 100)
    h, l = ax.get_legend_handles_labels(); dd = dict(zip(l, h))
    ax.legend([dd[k] for k in order if k in dd], [k for k in order if k in dd], frameon=False, fontsize=8, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_xlabel(""); ax.set_title("1,000枚の表で、見えている明細の合計と一致した割合（%）", fontsize=12)
    save(fig, "a515_1000_tables.png", SRC + "。\n小計行あり3割、エラーの値ありの表1割", y=-0.1)
    print(ag.round(3).to_string()); print(json.dumps({k: v for k, v in out.items() if not k.startswith("過大")}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
