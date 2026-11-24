"""1206 いくつかの配信リストを合わせて送ると、同じ人に2通届く割合はどれだけあるのか？（架空のデータ）

作成者が置いた架空の店の読者20,000人。3つの配信リスト（会員登録の名簿・店頭で書いてもらった名簿・催しの申し込みの名簿）。
1人ひとりが各リストに入る確率：その名簿の基本の確率（0.5・0.3・0.15）に、人ごとの「熱心さ」z（平均0・標準偏差1）を
足し合わせる形（ロジットの尺度で 基本＋s×z、基本 s＝1）。s＝0 なら、リストどうしは関係なく入る。
アドレスを2つ持つ人（基本30%）は、名簿ごとに「いつものアドレス」を70%、もう1つを30%の確率で書く。
名簿に書かれたアドレスは、5%（基本）が表記のゆれ（大文字がまざる・前後に空白が入る）で記録される。どちらも同じ受け箱に届く。
合わせ方：① そのまま足す ② 文字が同じアドレスだけ1通にまとめる ③ 小文字にそろえ空白を除いてからまとめる。
2通以上届いた人の割合（届いた人のうち）と、余分な通数の割合（送った通数のうち、同じ人への2通目以降）を数える。
(1) 基本の置き方で200回
(2) 確かめ：アドレスを2つ持つ人の割合4通り×表記のゆれ3通り×熱心さの効き s 3通り×リストの数3通り＝108通り（各20回）
(3) 確かめ：いつものアドレスを書く確率（50・70・90%）の3通り（各50回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1206
SRC = "架空の店の配信リスト（作成者が置いた名簿への入り方・アドレスの数・表記のゆれからの乱数、seed 1206）"
M = 20000
BASE = {2: [0.5, 0.3], 3: [0.5, 0.3, 0.15], 5: [0.5, 0.3, 0.15, 0.2, 0.1]}
Q2, V, S, MAIN_ADDR = 0.3, 0.05, 1.0, 0.7
R_MAIN, R_GRID, R_ADDR = 200, 20, 50
METHODS = ["① そのまま足す", "② 文字が同じアドレスだけまとめる", "③ 小文字・空白をそろえてまとめる"]
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def logit(p):
    return np.log(p / (1 - p))


def one_run(rng, q2=Q2, v=V, s=S, n_lists=3, main_addr=MAIN_ADDR, keep=False):
    base = np.array(BASE[n_lists])
    z = rng.standard_normal(M)
    p = 1 / (1 + np.exp(-(logit(base)[None, :] + s * z[:, None])))
    join = rng.random((M, n_lists)) < p
    two = rng.random(M) < q2
    pid, lid = np.nonzero(join)
    # 書いたアドレス（0：いつもの、1：もう1つ）
    which = np.where(two[pid] & (rng.random(len(pid)) >= main_addr), 1, 0)
    addr = pid * 2 + which
    # 表記のゆれ（0：なし、1：大文字がまざる、2：前後に空白）
    var = np.where(rng.random(len(pid)) < v, rng.integers(1, 3, len(pid)), 0)
    exact = addr * 3 + var
    n_send = {}
    # 各方法で送る宛先の、だれに届くか
    recips = {
        METHODS[0]: pid,
        METHODS[1]: pid[np.unique(exact, return_index=True)[1]],
        METHODS[2]: pid[np.unique(addr, return_index=True)[1]],
    }
    res = {"people_on_lists": int(len(np.unique(pid))), "records": int(len(pid))}
    for k, (m, rp) in enumerate(recips.items()):
        cnt = np.bincount(rp, minlength=M)
        reached = (cnt > 0).sum()
        res[f"sent_{k + 1}"] = int(len(rp))
        res[f"reached_{k + 1}"] = int(reached)
        res[f"double_share_{k + 1}"] = (cnt >= 2).sum() / reached
        res[f"extra_mail_share_{k + 1}"] = (len(rp) - reached) / len(rp)
    # ③で残った重複のうち、アドレスを2つ持つ人の分（作りどおりなら全部）
    cnt3 = np.bincount(recips[METHODS[2]], minlength=M)
    res["double3_from_two_addr"] = ((cnt3 >= 2) & two).sum() / max((cnt3 >= 2).sum(), 1)
    # ②で残った重複のうち、表記のゆれだけによる分（同じアドレスの別表記だけで2通以上）
    cnt_addr = np.bincount(recips[METHODS[2]], minlength=M)
    res["double2_only_variation"] = (((np.bincount(recips[METHODS[1]], minlength=M)) >= 2) & (cnt_addr == 1)).sum() / max(
        (np.bincount(recips[METHODS[1]], minlength=M) >= 2).sum(), 1)
    # 式：s=0 で①の2通以上の割合（リストどうしが関係ないとき）
    if keep:
        names = ["会員登録", "店頭", "催し", "名簿4", "名簿5"]
        s_addr = np.array([f"m{a // 2 + 1:05d}{'ab'[a % 2]}@example.com" for a in addr])
        s_rec = np.where(var == 1, np.char.upper(s_addr.astype("U")), s_addr)
        s_rec = np.where(var == 2, np.char.add(s_rec.astype("U"), " "), s_rec)
        tab = pd.DataFrame({"list": np.array(names)[lid], "person_id": pid + 1, "address_recorded": s_rec})
        res["table"] = tab
    return res


def formula_double_share(base):
    """リストどうしが関係ないとき（s=0）の、①そのまま足したときの2通以上の割合（届いた人のうち）"""
    base = np.array(base)
    p0 = np.prod(1 - base)
    p1 = sum(base[j] * np.prod(np.delete(1 - base, j)) for j in range(len(base)))
    return (1 - p0 - p1) / (1 - p0)


def summarize(xs):
    df = pd.DataFrame(xs)
    return df


def main():
    rng = np.random.default_rng(SEED)
    ex = one_run(np.random.default_rng(SEED + 1), keep=True)
    tab = ex.pop("table")
    ex = {k: (r(v) if isinstance(v, float) else v) for k, v in ex.items()}
    tab.to_csv(DATA / "registrations_example.csv", index=False)
    # 例の表で、文字列で数えた件数とコードで数えた件数が一致するか
    norm = tab.address_recorded.str.strip().str.lower()
    check_example = {
        "records": int(len(tab)),
        "sent_2_by_string": int(tab.address_recorded.nunique()), "sent_2_by_code": ex["sent_2"],
        "sent_3_by_string": int(norm.nunique()), "sent_3_by_code": ex["sent_3"],
        "people": int(tab.person_id.nunique()), "reached_1": ex["reached_1"],
    }

    df = summarize([one_run(rng) for _ in range(R_MAIN)])
    main_rows = []
    for k, m in enumerate(METHODS, 1):
        main_rows.append({"method": m, "sent": r(df[f"sent_{k}"].mean(), 2), "reached": r(df[f"reached_{k}"].mean(), 2),
                          "double_share": r(df[f"double_share_{k}"].mean()),
                          "double_share_p10": r(df[f"double_share_{k}"].quantile(0.1)),
                          "double_share_p90": r(df[f"double_share_{k}"].quantile(0.9)),
                          "extra_mail_share": r(df[f"extra_mail_share_{k}"].mean())})
    main_t = pd.DataFrame(main_rows)
    main_t.to_csv(RES / "by_method.csv", index=False)

    # s=0 のとき、①が式どおりか
    df0 = summarize([one_run(rng, s=0.0) for _ in range(R_GRID * 5)])
    formula_check = {"s0_double_share_1_sim": r(df0.double_share_1.mean()),
                     "s0_double_share_1_formula": r(formula_double_share(BASE[3])),
                     "s0_double_share_3_sim": r(df0.double_share_3.mean())}

    # 確かめ 108通り
    rows = []
    for q2 in [0.0, 0.15, 0.3, 0.5]:
        for v in [0.0, 0.05, 0.15]:
            for s in [0.0, 1.0, 2.0]:
                for nl in [2, 3, 5]:
                    d = summarize([one_run(rng, q2, v, s, nl) for _ in range(R_GRID)])
                    rows.append({"two_addr_share": q2, "variation": v, "eagerness_effect": s, "n_lists": nl,
                                 "double_share_1": r(d.double_share_1.mean()), "double_share_2": r(d.double_share_2.mean()),
                                 "double_share_3": r(d.double_share_3.mean()),
                                 "extra_mail_share_1": r(d.extra_mail_share_1.mean()),
                                 "extra_mail_share_3": r(d.extra_mail_share_3.mean()),
                                 "remain3_over_1": r(d.double_share_3.mean() / d.double_share_1.mean())})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    rows = []
    for ma in [0.5, 0.7, 0.9]:
        d = summarize([one_run(rng, main_addr=ma) for _ in range(R_ADDR)])
        rows.append({"main_addr_prob": ma, "double_share_1": r(d.double_share_1.mean()),
                     "double_share_2": r(d.double_share_2.mean()), "double_share_3": r(d.double_share_3.mean())})
    addr_t = pd.DataFrame(rows)
    addr_t.to_csv(RES / "main_address.csv", index=False)

    g = grid
    q0 = g[g.two_addr_share == 0]
    qpos = g[g.two_addr_share > 0]
    robust = {
        "n": int(len(g)), "n_without_two_addr": int(len(q0)), "n_with_two_addr": int(len(qpos)),
        "double1_min": r(g.double_share_1.min()), "double1_max": r(g.double_share_1.max()),
        "double3_q0_max": r(q0.double_share_3.max()),
        "double3_qpos_min": r(qpos.double_share_3.min()), "double3_qpos_max": r(qpos.double_share_3.max()),
        "remain3_over_1_qpos_min": r(qpos.remain3_over_1.min()), "remain3_over_1_qpos_max": r(qpos.remain3_over_1.max()),
        "double2_minus_3_max": r((g.double_share_2 - g.double_share_3).max()),
        "by_lists_1": g.groupby("n_lists").double_share_1.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_lists_3_qpos": qpos.groupby("n_lists").double_share_3.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_q2_3": g.groupby("two_addr_share").double_share_3.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "by_s_1": g.groupby("eagerness_effect").double_share_1.agg(["min", "median", "max"]).round(4).reset_index().to_dict("records"),
        "base_cell": g[(g.two_addr_share == 0.3) & (g.variation == 0.05) & (g.eagerness_effect == 1.0) & (g.n_lists == 3)].iloc[0].to_dict(),
        "s0_formula_cells": [{"n_lists": nl, "formula": r(formula_double_share(BASE[nl])),
                              "sim_q0_v0": r(g[(g.two_addr_share == 0) & (g.variation == 0) & (g.eagerness_effect == 0) & (g.n_lists == nl)].double_share_1.iloc[0])}
                             for nl in [2, 3, 5]],
    }
    mt = main_t.set_index("method")
    headline = {
        "double_share_1": mt.loc[METHODS[0], "double_share"], "double_share_2": mt.loc[METHODS[1], "double_share"],
        "double_share_3": mt.loc[METHODS[2], "double_share"],
        "extra_mail_share_1": mt.loc[METHODS[0], "extra_mail_share"], "extra_mail_share_3": mt.loc[METHODS[2], "extra_mail_share"],
        "reached": mt.loc[METHODS[0], "reached"], "sent_1": mt.loc[METHODS[0], "sent"], "sent_3": mt.loc[METHODS[2], "sent"],
        "double3_from_two_addr": r(df.double3_from_two_addr.mean()),
        "double2_only_variation": r(df.double2_only_variation.mean()),
        "robust_double3_qpos_min": robust["double3_qpos_min"], "robust_double3_qpos_max": robust["double3_qpos_max"],
    }
    out = {"settings": {"people": M, "lists_base_prob": BASE, "two_addr_share": Q2, "main_addr_prob": MAIN_ADDR,
                        "variation": V, "eagerness_effect": S, "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline, "formula_check": formula_check, "example_one_run": ex, "check_example_strings": check_example,
           "main_address": addr_t.to_dict("records"), "robust": robust}
    with open(RES / "a1206_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=float)

    # 図1：合わせ方ごとの2通以上届いた人の割合
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(3)
    vals = main_t.double_share * 100
    ax.bar(x, vals, 0.55, color=[GRAY, BLUE, ORANGE])
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.4, f"{v:.2f}%", ha="center", fontsize=10)
    ax.set_xticks(x, [m.replace("を", "を\n", 1) if len(m) > 12 else m for m in METHODS], fontsize=9.5)
    ax.set_ylabel("2通以上届いた人の割合（届いた人のうち、%）")
    ax.set_ylim(0, vals.max() * 1.2)
    ax.set_title("3つのリストを合わせて送ると、2通以上届いた人（基本の置き方、200回の平均）")
    save(fig, "a1206_methods.png", SRC)

    # 図2：アドレスを2つ持つ人の割合と、③で残る2通の割合（リスト3つ・表記のゆれ5%）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    sub = g[(g.n_lists == 3) & (g.variation == 0.05)]
    for s, c in zip([0.0, 1.0, 2.0], [GRAY, BLUE, ORANGE]):
        ss = sub[sub.eagerness_effect == s].sort_values("two_addr_share")
        ax.plot(ss.two_addr_share * 100, ss.double_share_3 * 100, marker="o", color=c,
                label=f"③ 熱心さの効き s={s:g}")
        ax.plot(ss.two_addr_share * 100, ss.double_share_1 * 100, marker="o", color=c, ls=":", alpha=0.7,
                label=f"① 同じ s={s:g}")
    ax.set_xlabel("アドレスを2つ持つ人の割合（%）")
    ax.set_ylabel("2通以上届いた人の割合（届いた人のうち、%）")
    ax.set_ylim(0, sub.double_share_1.max() * 100 * 1.45)
    ax.set_xticks([0, 15, 30, 50])
    ax.set_title("そろえてまとめても、アドレスを2つ持つ人の分は残る（リスト3つ）")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
    save(fig, "a1206_two_address.png", SRC)

    # 図3：リストの数ごとの①と③（アドレス2つ30%・表記のゆれ5%）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    sub = g[(g.two_addr_share == 0.3) & (g.variation == 0.05)]
    w = 0.13
    for i, s in enumerate([0.0, 1.0, 2.0]):
        ss = sub[sub.eagerness_effect == s].sort_values("n_lists")
        xx = np.arange(3) + (i - 1) * 2.2 * w
        ax.bar(xx - w / 2, ss.double_share_1 * 100, w, color=[GRAY, BLUE, ORANGE][i], alpha=0.45)
        ax.bar(xx + w / 2, ss.double_share_3 * 100, w, color=[GRAY, BLUE, ORANGE][i], label=f"熱心さの効き s={s:g}")
    ax.set_xticks(range(3), ["リスト2つ", "リスト3つ", "リスト5つ"])
    ax.set_ylabel("2通以上届いた人の割合（%）")
    ax.set_ylim(0, sub.double_share_1.max() * 100 * 1.15)
    ax.set_title("リストの数ごと：薄い棒は①そのまま、濃い棒は③そろえてまとめた後")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1206_lists.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), formula_check, round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
