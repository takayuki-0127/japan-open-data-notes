"""525 メールの開封率は、画像の自動読み込みによる「見かけの開封」を除くと何ポイント下がるのか（実務の型）

架空のメール配信（1回5万通、件名A・Bを半分ずつ）の記録を作る。受信者の一部は、届いた直後に
画像を自動で読み込む端末を使っている。その場合、本人が読んだかどうかに関係なく「開封」が記録され、
本人が後で読んでも2回目は記録されない（最初の読み込みで済んでいる）と置く。
開封の数え方を変えて開封率を出し、本当の開封率（本人が読んだ割合、架空のデータなので分かる）と比べる。
  1. 全部の開封
  2. 配信から5分以内の開封を除く
  3. クリックした人だけ
  4. 5分以内を除いた開封＋クリックした人
  5. 自動読み込みの端末と分かる人を分母からも除く
さらに小さめのA/Bテスト（各2,000通）を2,000回くり返し、勝ち負けが本当とどれだけ入れ替わるかを数える。
特定のメール配信サービスや端末の仕様は扱っていない。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 525
SRC = "架空のメール配信記録（作成者が乱数で作成、seed 525）"
QUICK = 5.0            # 「配信直後」とみなす分
CLICK_GIVEN_OPEN = 0.12
DEFS = ["全部の開封", "5分以内の開封を除く", "クリックした人だけ", "5分以内を除く＋クリックした人", "自動読み込みの端末を分母から除く"]


def make(n, p_true, auto_share, rng, variant="A"):
    auto = rng.random(n) < auto_share
    human = rng.random(n) < p_true                                   # 本人が読んだか
    t_human = rng.exponential(360, n)                                # 本人が読むまでの分（平均6時間）
    t_auto = rng.lognormal(np.log(1.0), 0.8, n)                      # 自動読み込みは届いて数分以内
    click = human & (rng.random(n) < CLICK_GIVEN_OPEN)
    first = np.where(auto, t_auto, np.where(human, t_human, np.nan)) # 最初に開封が記録された分
    return pd.DataFrame({"variant": variant, "auto_device": auto, "read_by_person": human,
                         "first_open_min": np.round(first, 2), "clicked": click})


def rates(d):
    opened = d.first_open_min.notna()
    late = opened & (d.first_open_min > QUICK)
    na = ~d.auto_device
    return {"本当の開封率": d.read_by_person.mean() * 100,
            "全部の開封": opened.mean() * 100,
            "5分以内の開封を除く": late.mean() * 100,
            "クリックした人だけ": d.clicked.mean() * 100,
            "5分以内を除く＋クリックした人": (late | d.clicked).mean() * 100,
            "自動読み込みの端末を分母から除く": opened[na].mean() * 100}


def main():
    rng = np.random.default_rng(SEED)
    df = pd.concat([make(25000, 0.20, 0.40, rng, "A"), make(25000, 0.22, 0.40, rng, "B")], ignore_index=True)
    df.insert(0, "id", np.arange(1, len(df) + 1))
    df.to_csv(DATA / "fictional_send_log.csv", index=False)
    r_all, rA, rB = rates(df), rates(df[df.variant == "A"]), rates(df[df.variant == "B"])
    tb = pd.DataFrame([{"数え方": k, "全体(%)": round(r_all[k], 2), "件名A(%)": round(rA[k], 2), "件名B(%)": round(rB[k], 2),
                        "本当との差(pt)": round(r_all[k] - r_all["本当の開封率"], 2), "B−A(pt)": round(rB[k] - rA[k], 2)}
                       for k in ["本当の開封率"] + DEFS])
    tb.to_csv(RES / "open_rate_by_definition.csv", index=False)

    # SQL（DuckDB）で同じ数え方をして、Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("sends", df)
    s = con.execute(open(SQL / "02_open_rates_duckdb.sql", encoding="utf-8").read()).df().iloc[0]
    sql_ok = bool(np.allclose([s.all_opens, s.excl_quick, s.clickers, s.excl_quick_or_click, s.non_auto_only],
                              [r_all[k] for k in DEFS]))

    # 自動読み込みの割合を変える（本当の開封率21%）
    sw = []
    for a in [0, .1, .2, .3, .4, .5, .6, .7, .8]:
        d = make(50000, 0.21, a, np.random.default_rng(SEED + 1))
        r = rates(d); sw.append({"自動読み込みの割合(%)": int(a * 100), **{k: round(v, 2) for k, v in r.items()}})
    sw = pd.DataFrame(sw); sw.to_csv(RES / "sweep_auto_share.csv", index=False)

    # 小さめのA/Bテストをくり返す：勝ち負けは本当（本人が読んだ割合）と入れ替わるか
    rr = np.random.default_rng(SEED + 2); N, n = 2000, 2000; flips = {k: 0 for k in DEFS}; diffs = []
    for _ in range(N):
        base = rr.uniform(.15, .25); delta = rr.uniform(-.03, .03)
        a = make(n, base, .40, rr, "A"); b = make(n, base + delta, .40, rr, "B")
        ra, rb = rates(a), rates(b)
        true_win = np.sign(rb["本当の開封率"] - ra["本当の開封率"])
        row = {"本当のB−A(pt)": rb["本当の開封率"] - ra["本当の開封率"]}
        for k in DEFS:
            dk = rb[k] - ra[k]; row[k] = dk
            if true_win != 0 and np.sign(dk) != true_win:
                flips[k] += 1
        diffs.append(row)
    diffs = pd.DataFrame(diffs)
    ft = pd.DataFrame([{"数え方": k, "勝ち負けが本当と入れ替わった割合(%)": round(flips[k] / N * 100, 1),
                        "本当の差との相関": round(float(np.corrcoef(diffs["本当のB−A(pt)"], diffs[k])[0, 1]), 3)} for k in DEFS])
    ft.to_csv(RES / "ab_flip_rate.csv", index=False)
    big = diffs["本当のB−A(pt)"].abs() >= 2
    ft2 = {k: round(float((np.sign(diffs.loc[big, k]) != np.sign(diffs.loc[big, "本当のB−A(pt)"])).mean() * 100), 1) for k in DEFS}

    res = {"sql_matches_python": sql_ok, "n": len(df), "auto_share": 0.40, "quick_min": QUICK,
           "by_definition": tb.to_dict("records"), "ab_flip": ft.to_dict("records"), "ab_flip_when_true_diff_ge_2pt": ft2,
           "ab_tests": N, "ab_n_per_arm": n, "true_open_within_5min_pct": round(float((df.read_by_person & ~df.auto_device).sum() and
               ((df.read_by_person & ~df.auto_device) & (df.first_open_min <= QUICK)).sum() / (df.read_by_person & ~df.auto_device).sum() * 100), 2)}
    json.dump(res, open(RES / "a525_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：数え方ごとの開封率
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    labs = ["本当の開封率"] + DEFS; vals = [r_all[k] for k in labs]; cols = [BLUE, ORANGE, GRAY, GRAY, GRAY, GREEN]
    y = np.arange(len(labs))[::-1]
    ax.barh(y, vals, color=cols)
    for yy, v, k in zip(y, vals, labs):
        ax.text(v + .8, yy, f"{v:.1f}%" + ("" if k == "本当の開封率" else ("（±0.0pt）" if abs(v - r_all['本当の開封率']) < 0.05 else f"（{v - r_all['本当の開封率']:+.1f}pt）")), va="center", fontsize=9)
    ax.set_yticks(y, labs, fontsize=9.5); ax.set_xlim(0, max(vals) * 1.3); ax.set_xlabel("開封率（%、5万通、自動読み込みの端末40%）")
    ax.set_title("全部の開封で数えると、本当の倍以上に出る")
    save(fig, "a525_by_definition.png", SRC)
    # 図2：自動読み込みの割合
    fig, ax = plt.subplots(figsize=(7.2, 4))
    x = sw["自動読み込みの割合(%)"]
    for k, c, m in [("本当の開封率", BLUE, "o-"), ("全部の開封", ORANGE, "s-"), ("5分以内の開封を除く", GRAY, "^-"), ("自動読み込みの端末を分母から除く", GREEN, "d--")]:
        ax.plot(x, sw[k], m, color=c, label=k)
    ax.set_xlabel("自動読み込みの端末の割合（%）"); ax.set_ylabel("開封率（%）")
    ax.set_title("自動読み込みが多いほど、全部の開封は上に、5分以内を除くと下にずれる", fontsize=11.5); ax.legend(frameon=False, fontsize=9)
    save(fig, "a525_auto_share.png", SRC)
    # 図3：A/B の入れ替わり
    fig, ax = plt.subplots(figsize=(7.6, 4))
    y = np.arange(len(DEFS))[::-1]
    ax.barh(y, ft["勝ち負けが本当と入れ替わった割合(%)"], color=[ORANGE, GRAY, GRAY, GRAY, GREEN])
    for yy, v in zip(y, ft["勝ち負けが本当と入れ替わった割合(%)"]):
        ax.text(v + .4, yy, f"{v:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y, DEFS, fontsize=9.5); ax.set_xlabel(f"A/B の勝ち負けが本当と入れ替わった割合（%、各{n:,}通×{N:,}回）")
    ax.set_title("見かけの開封が混ざると、A/Bの勝ち負けが本当と入れ替わりやすい"); ax.set_xlim(0, ft["勝ち負けが本当と入れ替わった割合(%)"].max() * 1.25)
    save(fig, "a525_ab_flip.png", SRC)
    print(tb.to_string()); print(sw.to_string()); print(ft.to_string()); print(ft2, sql_ok, res["true_open_within_5min_pct"])


if __name__ == "__main__":
    main()
