"""A364 成績の悪かった店だけに手を打つと、何もしなくてもどれだけ「良くなって」見えるのか
架空の100店の月次売上（施策の効果は0）で、成績の悪い店を選んだあとの戻り（平均への回帰）を測る。乱数の種は364。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N_STORE, N_PICK, REPS = 364, 100, 20, 2000
SRC = "架空のデータ（作成者が乱数で作成、seed 364）"


def make(rng, reps, months=30, noise=0.08, rho=0.0, persist_sd=0.0):
    """月次の達成率（その店のふだんの売上を100としたときの売上）。施策の効果は入れていない。
    noise：月ごとの偶然のばらつき。rho・persist_sd：何か月か続く不調（AR1）"""
    eps = rng.normal(0, noise, (reps, N_STORE, months))
    if persist_sd > 0:
        a = np.zeros((reps, N_STORE, months)); a[:, :, 0] = rng.normal(0, persist_sd, (reps, N_STORE))
        innov = persist_sd * np.sqrt(1 - rho ** 2)
        for t in range(1, months): a[:, :, t] = rho * a[:, :, t - 1] + rng.normal(0, innov, (reps, N_STORE))
        eps = eps + a
    return 100 * np.exp(eps)


def experiment(x, k=1, after=3, t0=18):
    """t0 の直前 k か月の平均で下位20店を選び、その後 after か月の平均と比べる"""
    before = x[:, :, t0 - k:t0].mean(axis=2); later = x[:, :, t0:t0 + after].mean(axis=2)
    order = np.argsort(before, axis=1)
    pick = order[:, :N_PICK]; rest = order[:, N_PICK:]
    r = np.arange(x.shape[0])[:, None]
    b_p, l_p = before[r, pick], later[r, pick]; b_r, l_r = before[r, rest], later[r, rest]
    change = (l_p.mean(axis=1) / b_p.mean(axis=1) - 1) * 100                   # 選んだ店の前後の変化
    # 前後を比べる検定（対応のある t 検定、片側：良くなった）
    d = l_p - b_p; t = d.mean(axis=1) / (d.std(axis=1, ddof=1) / np.sqrt(N_PICK))
    sig_before_after = (stats.t.sf(t, N_PICK - 1) < 0.025).mean() * 100
    # 選ばなかった80店と、変化の差を比べる（差の差）
    did = (l_p - b_p).mean(axis=1) - (l_r - b_r).mean(axis=1)
    se = np.sqrt((l_p - b_p).var(axis=1, ddof=1) / N_PICK + (l_r - b_r).var(axis=1, ddof=1) / (N_STORE - N_PICK))
    sig_did = (stats.norm.sf(did / se) < 0.025).mean() * 100
    return dict(before=float(b_p.mean()), after=float(l_p.mean()), change_pct=float(change.mean()),
                change_p10=float(np.percentile(change, 10)), change_p90=float(np.percentile(change, 90)),
                sig_before_after=float(sig_before_after), did_points=float(did.mean()), sig_did=float(sig_did))


def randomized(x, rng, k=1, after=3, t0=18):
    """下位40店を選び、そのうち20店をくじで「手を打つ店」に、残り20店を「比べる店」にする"""
    before = x[:, :, t0 - k:t0].mean(axis=2); later = x[:, :, t0:t0 + after].mean(axis=2)
    order = np.argsort(before, axis=1)[:, :2 * N_PICK]
    perm = np.argsort(rng.random(order.shape), axis=1); order = np.take_along_axis(order, perm, axis=1)
    r = np.arange(x.shape[0])[:, None]
    tr, co = order[:, :N_PICK], order[:, N_PICK:]
    dt = later[r, tr] - before[r, tr]; dc = later[r, co] - before[r, co]
    diff = dt.mean(axis=1) - dc.mean(axis=1)
    se = np.sqrt(dt.var(axis=1, ddof=1) / N_PICK + dc.var(axis=1, ddof=1) / N_PICK)
    p = 2 * stats.t.sf(np.abs(diff / se), 2 * N_PICK - 2)
    return dict(diff_points=float(diff.mean()), sig_two_sided=float((p < 0.05).mean() * 100),
                treated_change_pct=float(((later[r, tr].mean(axis=1) / before[r, tr].mean(axis=1)) - 1).mean() * 100),
                control_change_pct=float(((later[r, co].mean(axis=1) / before[r, co].mean(axis=1)) - 1).mean() * 100))


def main():
    rng = np.random.default_rng(SEED)
    out = {"n_store": N_STORE, "n_pick": N_PICK, "reps": REPS}
    # 基本：月の偶然のばらつき8%、続く不調なし
    x = make(rng, REPS)
    pd.DataFrame(np.round(x[0], 1), columns=[f"month{m + 1}" for m in range(x.shape[2])]).assign(store=np.arange(1, N_STORE + 1)) \
        .set_index("store").to_csv(DATA / "example_100_stores.csv")
    base = experiment(x); out["base"] = {k: round(v, 2) for k, v in base.items()}
    rnd = randomized(x, rng); out["randomized"] = {k: round(v, 2) for k, v in rnd.items()}

    # 選ぶ月数を増やす
    rows = []
    for k in [1, 2, 3, 6, 12]:
        e = experiment(x, k=k); rows.append(dict(months_used=k, **{a: round(b, 2) for a, b in e.items()}))
    sel = pd.DataFrame(rows); sel.to_csv(RES / "by_selection_months.csv", index=False)

    # 選ぶ店の数（下位何店か）
    rows = []
    for n_pick in [5, 10, 20, 50]:
        before = x[:, :, 17]; later = x[:, :, 18:21].mean(axis=2); order = np.argsort(before, axis=1)[:, :n_pick]
        r = np.arange(REPS)[:, None]
        ch = (later[r, order].mean(axis=1) / before[r, order].mean(axis=1) - 1) * 100
        rows.append(dict(n_pick=n_pick, before=round(float(before[r, order].mean()), 2), change_pct=round(float(ch.mean()), 2)))
    npk = pd.DataFrame(rows); npk.to_csv(RES / "by_number_picked.csv", index=False)

    # 不調が続く場合（偶然のばらつき8%は同じ。続く不調の大きさ8%、続きやすさを変える）
    rows = []
    for rho in [0.0, 0.5, 0.8, 0.95]:
        xx = make(rng, REPS, rho=rho, persist_sd=0.08)
        for k in [1, 3]:
            e = experiment(xx, k=k); rows.append(dict(rho=rho, months_used=k, **{a: round(b, 2) for a, b in e.items()}))
    per = pd.DataFrame(rows); per.to_csv(RES / "by_persistence.csv", index=False)

    # 本当に効果がある場合（選んだ店に +3%）：前後比べはどれだけ大きく見せるか
    xe = x.copy(); before = xe[:, :, 17]; order = np.argsort(before, axis=1)[:, :N_PICK]; r = np.arange(REPS)[:, None]
    later = xe[:, :, 18:21].mean(axis=2).copy(); later[r, order] *= 1.03
    ch = (later[r, order].mean(axis=1) / before[r, order].mean(axis=1) - 1) * 100
    out["true_effect_3pct_looks_like"] = round(float(ch.mean()), 2)

    out["by_selection_months"] = sel.to_dict("records"); out["by_number_picked"] = npk.to_dict("records"); out["by_persistence"] = per.to_dict("records")
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：1回分の例（選んだ20店の前と後） ---
    fig, ax = plt.subplots(figsize=(8.4, 4.4))
    x0 = x[0]; pick = np.argsort(x0[:, 17])[:N_PICK]; months = np.arange(12, 24)
    for s in range(N_STORE):
        if s not in pick: ax.plot(months - 17, x0[s, months], color=LIGHT, lw=0.5, alpha=0.5)
    for s in pick: ax.plot(months - 17, x0[s, months], color=ORANGE, lw=0.9, alpha=0.7)
    ax.plot(months - 17, x0[pick][:, months].mean(axis=0), color=INK, lw=2.4, label="選んだ20店の平均")
    ax.axvline(0.5, color=GRAY, lw=1, ls="--"); ax.text(0.6, x0[:, months].max() * 0.995, "ここで「手を打った」ことにする\n（実際は何もしていない）", fontsize=9, va="top", color=GRAY)
    ax.set_xlabel("選んだ月を0とした月"); ax.set_ylabel("売上（その店のふだんを100とする）"); ax.legend(frameon=False, loc="lower left")
    ax.set_title("成績が悪かった月の下位20店は、翌月には何もしなくても戻る")
    save(fig, "a364_example.png", SRC + "。橙＝選んだ月の下位20店、水色＝ほかの80店")

    # --- 図2：選ぶ月数と見かけの改善 ---
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = np.arange(len(sel))
    ax.bar(xs, sel.change_pct, 0.6, color=ORANGE)
    for xx_, v in zip(xs, sel.change_pct): ax.text(xx_, v + 0.15, f"+{v:.1f}%", ha="center", fontsize=10)
    ax.set_xticks(xs); ax.set_xticklabels([f"直前{k}か月の平均\nで選ぶ" for k in sel.months_used], fontsize=9.5)
    ax.set_ylabel("選んだ20店の、その後3か月の見かけの改善（%）"); ax.set_title("長い期間の成績で選ぶほど、見かけの改善は小さくなる")
    save(fig, "a364_selection_months.png", SRC + "。施策の効果は0。2,000回の平均")

    # --- 図3：誤って「効果あり」と出る割合 ---
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labs = ["選んだ20店の\n前と後を比べる", "選ばなかった80店と\n変化を比べる", "下位40店をくじで\n20店ずつに分けて比べる"]
    v = [base["sig_before_after"], base["sig_did"], rnd["sig_two_sided"]]
    ax.bar(np.arange(3), v, 0.55, color=[ORANGE, ORANGE, BLUE])
    for i, vv in enumerate(v): ax.text(i, vv + 1.5, f"{vv:.0f}%", ha="center", fontsize=11)
    ax.axhline(5, color=GRAY, lw=1, ls="--"); ax.text(1.5, 7.5, "本来の誤りの割合（5%）", ha="center", fontsize=9, color=GRAY)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(labs); ax.set_ylim(0, 110); ax.set_ylabel("効果0なのに「効果あり」と出た割合（%）")
    ax.set_title("効果が0でも、比べ方によってはほぼ毎回「効果あり」と出る")
    save(fig, "a364_false_positive.png", SRC + "。施策の効果は0。2,000回")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
