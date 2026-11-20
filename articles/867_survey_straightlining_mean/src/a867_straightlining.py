"""867 同じ選択肢ばかり選ぶ回答を、何%混ぜると平均が動くのか？（架空のデータ）

架空の店の客アンケート（10問、1〜5の5段階）。ちゃんと答える客の答えは、問いごとの中心＋人ごとの甘さ辛さ＋ぶれで作る。
そこに「10問すべて同じ数字を選ぶ回答」（ここでは同じ選択肢ばかり選ぶ回答と呼ぶ）を何%か混ぜ、
問いごとの平均・満足の割合・問いどうしのまとまり（相関）がどれだけ動くか、取り除く決まりで何が起きるかを数える。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 867
SRC = "架空の店の客アンケート（作成者が乱数で作成、seed 867）"
ITEMS = ["料理の味", "料理の量", "品ぞろえ", "接客", "提供の速さ", "店内の清潔さ", "席の広さ", "待ち時間", "予約のしやすさ", "支払いのしやすさ"]
CENTER = np.array([4.0, 3.7, 3.4, 3.9, 3.2, 3.8, 3.0, 2.8, 3.3, 3.6])  # 問いごとの中心（作成者が置いた）
N_RESP = 400
P_LIST = [0, 0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30]


def genuine(rng, n, center=CENTER, person_sd=0.5, noise_sd=0.8):
    lat = center[None, :] + rng.normal(0, person_sd, (n, 1)) + rng.normal(0, noise_sd, (n, len(center)))
    return np.clip(np.rint(lat), 1, 5).astype(int)


def straight(rng, n, k, kind):
    if kind == "mix":  # 1・3・5 を 2:5:3 で
        v = rng.choice([1, 3, 5], size=n, p=[0.2, 0.5, 0.3])
    else:
        v = np.full(n, int(kind))
    return np.repeat(v[:, None], k, axis=1)


def alpha_and_r(x):
    c = np.corrcoef(x.T)
    k = x.shape[1]
    r = (c.sum() - k) / (k * (k - 1))
    a = k / (k - 1) * (1 - x.var(0, ddof=1).sum() / x.sum(1).var(ddof=1))
    return float(r), float(a)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 本当の平均（ちゃんと答える客だけ、40万人で数える）
    pop = genuine(np.random.default_rng(SEED * 10), 400000)
    true_mean = pop.mean(0)
    true_sat = (pop >= 4).mean(0)
    sd_item = pop.std(0)
    se400 = sd_item / np.sqrt(N_RESP)
    r0, a0 = alpha_and_r(pop[:50000])
    true_all_same = float((pop == pop[:, :1]).all(1).mean())
    true_all5 = float((pop == 5).all(1).mean())

    # 1) 混ぜる割合ごとの、問いごとの平均のずれ（400人を2,000回）
    rows = []
    for kind in ["5", "3", "1", "mix"]:
        for p in P_LIST:
            sh, sat, gap, rr, aa, swap = [], [], [], [], [], []
            for r in range(300 if kind != "5" else 2000):
                g = np.random.default_rng([SEED, int(p * 1000), ord(kind[0]), r])
                ns = g.binomial(N_RESP, p)
                x = np.vstack([genuine(g, N_RESP - ns), straight(g, ns, 10, kind)])
                m = x.mean(0)
                sh.append(m - true_mean)
                sat.append((x >= 4).mean(0) - true_sat)
                gap.append(m.max() - m.min())
                if r < 300:
                    r_, a_ = alpha_and_r(x); rr.append(r_); aa.append(a_)
                swap.append(int(np.argmax(m) != np.argmax(true_mean)) + int(np.argmin(m) != np.argmin(true_mean)) > 0)
            sh = np.array(sh); sat = np.array(sat)
            rows.append({"kind": kind, "p": p,
                         "mean_shift_all_items": round(float(sh.mean()), 4),
                         "mean_shift_max_item": round(float(np.abs(sh.mean(0)).max()), 4),
                         "share_items_shift_gt_1_96se": round(float((np.abs(sh) > 1.96 * se400).mean()), 4),
                         "sat_share_shift_pt": round(float(sat.mean() * 100), 2),
                         "gap_best_worst": round(float(np.mean(gap)), 4),
                         "avg_inter_item_r": round(float(np.mean(rr)), 4),
                         "cronbach_alpha": round(float(np.mean(aa)), 4),
                         "top_or_bottom_item_changed": round(float(np.mean(swap)), 4)})
    sim = pd.DataFrame(rows)
    sim.to_csv(RES / "shift_by_share.csv", index=False)
    # 理屈の値：ずれ = 割合 ×（選んだ数字 − 本当の平均）
    theory = {str(p): round(float(p * (5 - true_mean).mean()), 4) for p in P_LIST}

    # 2) 「10問すべて同じ」を除く決まり：ちゃんと答えた客も除かれる
    rem = []
    for person_sd in [0.3, 0.5, 0.8]:
        for k in [5, 10, 20]:
            cen = np.resize(CENTER, k)
            gp = genuine(np.random.default_rng([SEED, k, int(person_sd * 10)]), 200000, cen, person_sd)
            tm = gp.mean()
            flag = (gp == gp[:, :1]).all(1)
            # 5%の全問5を混ぜて、除いたあとの全体の平均
            ns = 10526  # 200000人に対し約5%
            x = np.vstack([gp, np.full((ns, k), 5)])
            fl = (x == x[:, :1]).all(1)
            # ゆるい回答：全問5のうち1問だけ4にする人（決まりをすり抜ける）
            lz = np.full((ns, k), 5); lz[np.arange(ns), np.random.default_rng([SEED, k, 99]).integers(0, k, ns)] = 4
            xl = np.vstack([gp, lz]); fll = (xl == xl[:, :1]).all(1)
            rem.append({"person_sd": person_sd, "n_items": k,
                        "genuine_flagged_pct": round(float(flag.mean() * 100), 3),
                        "genuine_all5_pct": round(float((gp == 5).all(1).mean() * 100), 3),
                        "bias_if_remove_without_straight": round(float(gp[~flag].mean() - tm), 4),
                        "bias_mixed5pct_keep": round(float(x.mean() - tm), 4),
                        "bias_mixed5pct_remove": round(float(x[~fl].mean() - tm), 4),
                        "bias_mixed5pct_lazy_remove": round(float(xl[~fll].mean() - tm), 4)})
    rem = pd.DataFrame(rem)
    rem.to_csv(RES / "removal_rule.csv", index=False)

    # 1回分のデータ（400人、全問5を5%）
    g = np.random.default_rng(SEED + 1)
    ns = int(N_RESP * 0.05)
    x = np.vstack([genuine(g, N_RESP - ns), straight(g, ns, 10, "5")])
    df = pd.DataFrame(x, columns=[f"q{i+1}" for i in range(10)])
    df.insert(0, "straight", [0] * (N_RESP - ns) + [1] * ns)
    df.insert(0, "resp_id", np.arange(1, N_RESP + 1))
    df.to_csv(DATA / "responses_5pct_all5.csv", index=False)

    s5 = sim[sim.kind == "5"].set_index("p")
    def first_p(col, thr, kind="5"):
        s = sim[sim.kind == kind].set_index("p")[col]
        hit = [p for p in P_LIST if abs(s[p]) >= thr]
        return hit[0] if hit else None
    out = {"items": ITEMS, "true_mean": [round(float(v), 3) for v in true_mean],
           "true_sat_share": [round(float(v), 3) for v in true_sat],
           "true_overall_mean": round(float(true_mean.mean()), 3),
           "se_item_n400": [round(float(v), 4) for v in se400], "se_item_n400_mean": round(float(se400.mean()), 4),
           "genuine_inter_item_r": round(r0, 3), "genuine_alpha": round(a0, 3),
           "genuine_all_same_pct": round(true_all_same * 100, 3), "genuine_all5_pct": round(true_all5 * 100, 3),
           "theory_shift_all5": theory,
           "first_p_overall_shift_ge_0_1_all5": first_p("mean_shift_all_items", 0.1),
           "first_p_overall_shift_ge_0_05_all5": first_p("mean_shift_all_items", 0.05),
           "first_p_overall_shift_ge_0_1_all1": first_p("mean_shift_all_items", 0.1, "1"),
           "shift_by_share": sim.to_dict("records"), "removal_rule": rem.to_dict("records"),
           "one_draw_item_means": [round(float(v), 3) for v in x.mean(0)],
           "one_draw_item_means_without_straight": [round(float(v), 3) for v in x[:N_RESP - ns].mean(0)]}
    out["se_item_n400_mean_x1_96"] = round(float(se400.mean() * 1.96), 4)
    json.dump(out, open(RES / "a867_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：混ぜる割合と、全問の平均のずれ
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    lab = {"5": "全問「5」を選ぶ", "3": "全問「3」を選ぶ", "1": "全問「1」を選ぶ", "mix": "1・3・5を2:5:3で混ぜる"}
    col = {"5": ORANGE, "3": GRAY, "1": BLUE, "mix": GREEN}
    for kind in ["5", "3", "1", "mix"]:
        s = sim[sim.kind == kind]
        ax.plot(s.p * 100, s.mean_shift_all_items, marker="o", ms=4, color=col[kind], label=lab[kind])
    se = float(se400.mean()) * 1.96
    ax.axhspan(-se, se, color=LIGHT, alpha=.35, lw=0)
    ax.text(30, se + 0.01, f"1問の平均が400人で持つ振れ（±{se:.2f}）", ha="right", fontsize=8.5, color=BLUE)
    ax.axhline(0, color=INK, lw=.6)
    ax.set_xlabel("同じ選択肢ばかり選ぶ回答を混ぜた割合（%）"); ax.set_ylabel("10問の平均のずれ（点）")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    v5 = float(s5.loc[0.05, "mean_shift_all_items"])
    ax.set_title(f"全問「5」の回答を5%混ぜると、10問の平均は{v5:+.2f}点ずれる")
    save(fig, "a867_shift.png", SRC)

    # 図2：問いごとの平均（本当 vs 全問5を10%）
    s10 = sim[(sim.kind == "5") & (sim.p == 0.10)].iloc[0]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    order = np.argsort(true_mean)
    y = np.arange(10)
    mixed = true_mean * 0.9 + 5 * 0.1
    ax.scatter(true_mean[order], y, color=BLUE, zorder=3, label="ちゃんと答えた客だけ（本当の平均）")
    ax.scatter(mixed[order], y, color=ORANGE, zorder=3, label="全問「5」を10%混ぜたとき")
    for i, j in enumerate(order):
        ax.plot([true_mean[j], mixed[j]], [i, i], color=GRAY, lw=1)
    ax.set_yticks(y); ax.set_yticklabels([ITEMS[j] for j in order]); ax.set_xlabel("平均（1〜5）")
    ax.set_xlim(2.6, 4.4)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"低い問いほど大きく上がり、いちばん高い問いと低い問いの差は縮む（{true_mean.max()-true_mean.min():.2f}→{s10.gap_best_worst:.2f}）", fontsize=11)
    save(fig, "a867_items.png", SRC)

    # 図3：「全問同じ」を除く決まり（人ごとの甘さ辛さ0.5）
    r10 = rem[rem.person_sd == 0.5]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(r10)); w = 0.26
    ax.bar(xs - w, r10.bias_mixed5pct_keep, w, color=ORANGE, label="そのまま")
    ax.bar(xs, r10.bias_mixed5pct_remove, w, color=BLUE, label="「全問同じ」を除く")
    ax.bar(xs + w, r10.bias_mixed5pct_lazy_remove, w, color=GRAY, label="「全問同じ」を除く（混ぜた回答が1問だけ4にする場合）")
    ax.axhline(0, color=INK, lw=.6)
    ax.set_xticks(xs); ax.set_xticklabels([f"{k}問のアンケート" for k in r10.n_items])
    ax.set_ylabel("全問の平均のずれ（点）"); ax.set_ylim(-0.01, 0.125)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("全問「5」を5%混ぜたとき：「全問同じ」を除くとずれは消えるが、1問だけ変える回答はすり抜ける", fontsize=10.5)
    save(fig, "a867_removal.png", SRC)
    print(json.dumps({k: out[k] for k in ["true_mean", "true_overall_mean", "se_item_n400_mean", "theory_shift_all5",
                                          "first_p_overall_shift_ge_0_1_all5", "first_p_overall_shift_ge_0_05_all5",
                                          "genuine_all_same_pct", "genuine_all5_pct", "genuine_inter_item_r", "genuine_alpha"]},
                     ensure_ascii=False))
    print(sim.to_string()); print(rem.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
