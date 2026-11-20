"""869 2つのことを1つの質問で聞くと、何を読み違えるのか？（架空のデータ）

架空の飲食チェーン100店。店ごとに「料理に満足している客の割合」と「接客に満足している客の割合」を作成者が置く。
「料理と接客に満足していますか」と1つの質問で聞くと、客は次のどれかの決め方で答えると置く：
  両方：両方に満足なら「はい」／どちらか：どちらかに満足なら「はい」／先：先に書かれたほう（料理）だけで決める／後：後に書かれたほう（接客）だけで決める
決め方の混ざり方は作成者が置き（基本 40:15:30:15）、置き方を変えて確かめる。
"""
import json, math, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 869
SRC = "架空のチェーンの客アンケート（作成者が乱数で作成、seed 869）"
N_STORE, N_RESP, K = 100, 200, 10
BASE_MIX = (0.40, 0.15, 0.30, 0.15)  # 両方・どちらか・先・後
RULES = ["両方", "どちらか", "先", "後"]


def probit(p):
    p = np.asarray(p, float)
    lo, hi = np.full(p.shape, -8.0), np.full(p.shape, 8.0)
    cdf = np.vectorize(lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2))))
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = np.where(cdf(mid) < p, mid, lo), np.where(cdf(mid) < p, hi, mid)
    return (lo + hi) / 2


def customers(rng, f, g, n, rho):
    """店ごとの料理・接客の満足（0/1）を、相関 rho の2つの正規の値から作る"""
    a = rng.normal(size=(len(f), n))
    b = rho * a + math.sqrt(1 - rho ** 2) * rng.normal(size=(len(f), n))
    return (a < probit(f)[:, None]).astype(int), (b < probit(g)[:, None]).astype(int)


def answer(rng, food, serv, mix, food_first=True):
    rule = rng.choice(4, size=food.shape, p=mix)
    first, last = (food, serv) if food_first else (serv, food)
    ans = np.select([rule == 0, rule == 1, rule == 2, rule == 3],
                    [food & serv, food | serv, first, last])
    return ans


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    # 1) 1店の例：料理80%・接客50%（20万人で数える）
    ex = {}
    for rho in [0.3]:
        fd, sv = customers(rng, np.array([0.8]), np.array([0.5]), 200000, rho)
        ex["food"] = round(float(fd.mean() * 100), 2); ex["service"] = round(float(sv.mean() * 100), 2)
        for i, r in enumerate(RULES):
            mix = np.eye(4)[i]
            ex[f"rule_{r}_food_first"] = round(float(answer(rng, fd, sv, mix).mean() * 100), 2)
        ex["mix_food_first"] = round(float(answer(rng, fd, sv, BASE_MIX).mean() * 100), 2)
        ex["mix_service_first"] = round(float(answer(rng, fd, sv, BASE_MIX, False).mean() * 100), 2)
        # 接客を50%→70%に上げたとき
        fd2, sv2 = customers(rng, np.array([0.8]), np.array([0.7]), 200000, rho)
        ex["after_service"] = round(float(sv2.mean() * 100), 2)
        ex["after_mix_food_first"] = round(float(answer(rng, fd2, sv2, BASE_MIX).mean() * 100), 2)
        for i, r in enumerate(RULES):
            ex[f"after_rule_{r}_food_first"] = round(float(answer(rng, fd2, sv2, np.eye(4)[i]).mean() * 100), 2)
        # 料理80%・接客50% と 料理50%・接客80% は、1つの質問で同じに見えるか
        fd3, sv3 = customers(rng, np.array([0.5]), np.array([0.8]), 200000, rho)
        ex["swap_store_mix_food_first"] = round(float(answer(rng, fd3, sv3, BASE_MIX).mean() * 100), 2)
        ex["diff_swap_store_pt"] = round(ex["mix_food_first"] - ex["swap_store_mix_food_first"], 1)
        ex["diff_order_pt"] = round(ex["mix_food_first"] - ex["mix_service_first"], 1)
        ex["gain_service_only_pt"] = round(ex["after_service"] - ex["service"], 1)
        ex["gain_mix_pt"] = round(ex["after_mix_food_first"] - ex["mix_food_first"], 1)
        for r in RULES:
            ex[f"gain_rule_{r}_pt"] = round(ex[f"after_rule_{r}_food_first"] - ex[f"rule_{r}_food_first"], 1)

    # 2) チェーン100店：1つの質問で低い10店を選ぶと、本当に接客（料理）の低い10店に当たるか
    def chain(mix, rho, reps, seed_off):
        out = {"hit_service_double": [], "hit_food_double": [], "hit_service_sep": [], "hit_food_sep": [],
               "corr_double_food": [], "corr_double_service": [], "same_score_diff_weak": []}
        for r in range(reps):
            g = np.random.default_rng([SEED, seed_off, r])
            f = g.uniform(0.55, 0.90, N_STORE); s = g.uniform(0.40, 0.85, N_STORE)
            fd, sv = customers(g, f, s, N_RESP, rho)
            dbl = answer(g, fd, sv, mix).mean(1)
            low_d = set(np.argsort(dbl)[:K])
            true_s, true_f = set(np.argsort(s)[:K]), set(np.argsort(f)[:K])
            out["hit_service_double"].append(len(low_d & true_s) / K)
            out["hit_food_double"].append(len(low_d & true_f) / K)
            out["hit_service_sep"].append(len(set(np.argsort(sv.mean(1))[:K]) & true_s) / K)
            out["hit_food_sep"].append(len(set(np.argsort(fd.mean(1))[:K]) & true_f) / K)
            out["corr_double_food"].append(np.corrcoef(dbl, f)[0, 1])
            out["corr_double_service"].append(np.corrcoef(dbl, s)[0, 1])
            # 1つの質問の割合が2ポイント以内の店の組のうち、低いほうの項目（本当）が違う組の割合
            # 料理のほうが弱い店＝料理の満足がチェーンの真ん中（0.725）から下がっている分が、接客（真ん中0.625）より大きい店
            weak = (f - 0.725) < (s - 0.625)
            i, j = np.triu_indices(N_STORE, 1)
            close = np.abs(dbl[i] - dbl[j]) <= 0.02
            out["same_score_diff_weak"].append(float((weak[i][close] != weak[j][close]).mean()))
        return {k: round(float(np.mean(v)), 4) for k, v in out.items()}

    base = chain(BASE_MIX, 0.3, 300, 1)
    sens = []
    mixes = {"基本（40:15:30:15）": BASE_MIX, "全員が両方": (1, 0, 0, 0), "全員がどちらか": (0, 1, 0, 0),
             "全員が先（料理）": (0, 0, 1, 0), "全員が後（接客）": (0, 0, 0, 1), "4つを同じ割合": (.25, .25, .25, .25)}
    for mi, (name, mix) in enumerate(mixes.items()):
        for rho in [0.0, 0.3, 0.6]:
            res = chain(mix, rho, 100, 100 + mi * 10 + int(rho * 10))
            sens.append({"mix": name, "rho": rho, **res})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    # 1回分のデータ（100店）
    g = np.random.default_rng(SEED + 1)
    f = g.uniform(0.55, 0.90, N_STORE); s = g.uniform(0.40, 0.85, N_STORE)
    fd, sv = customers(g, f, s, N_RESP, 0.3)
    dbl = answer(g, fd, sv, BASE_MIX).mean(1)
    df = pd.DataFrame({"store": np.arange(1, N_STORE + 1), "true_food": f.round(4), "true_service": s.round(4),
                       "obs_food": fd.mean(1).round(4), "obs_service": sv.mean(1).round(4), "obs_double": dbl.round(4)})
    df.to_csv(DATA / "stores.csv", index=False)
    one = {"low10_double_in_true_low10_service": int(len(set(np.argsort(dbl)[:K]) & set(np.argsort(s)[:K]))),
           "low10_double_in_true_low10_food": int(len(set(np.argsort(dbl)[:K]) & set(np.argsort(f)[:K])))}

    out = {"base_mix": dict(zip(RULES, BASE_MIX)), "example_store": ex, "chain_base": base, "one_draw": one,
           "random_hit": K / N_STORE, "sensitivity": sens.to_dict("records"),
           "range_hit_service_double": [float(sens.hit_service_double.min()), float(sens.hit_service_double.max())],
           "range_hit_service_double_excl_pure_last": [float(sens[sens["mix"] != "全員が後（接客）"].hit_service_double.min()),
                                                        float(sens[sens["mix"] != "全員が後（接客）"].hit_service_double.max())],
           "range_hit_service_sep": [float(sens.hit_service_sep.min()), float(sens.hit_service_sep.max())]}
    json.dump(out, open(RES / "a869_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1店の例
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labs = ["料理だけ聞く", "接客だけ聞く", "1つの質問：両方", "1つの質問：どちらか", "1つの質問：先（料理）",
            "1つの質問：後（接客）", "1つの質問：混ざり（基本）", "1つの質問：混ざり（接客と料理の順）"]
    vals = [ex["food"], ex["service"], ex["rule_両方_food_first"], ex["rule_どちらか_food_first"],
            ex["rule_先_food_first"], ex["rule_後_food_first"], ex["mix_food_first"], ex["mix_service_first"]]
    cols = [BLUE, BLUE, LIGHT, LIGHT, LIGHT, LIGHT, ORANGE, ORANGE]
    ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set_xlim(0, 100); ax.set_xlabel("「はい（満足）」の割合（%）")
    rv = [ex[f"rule_{r}_food_first"] for r in RULES]
    ax.set_title(f"料理80%・接客50%の店を1つの質問で聞くと、答えは決め方で{min(rv):.0f}〜{max(rv):.0f}%に散る", fontsize=11.5)
    save(fig, "a869_example.png", SRC)

    # 図2：1つの質問の割合と、本当の料理・接客（1回分の100店）
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.6), sharey=True)
    low = np.argsort(dbl)[:K]
    for ax, col, name in [(axs[0], f, "本当の料理の満足（%）"), (axs[1], s, "本当の接客の満足（%）")]:
        ax.scatter(col * 100, dbl * 100, s=14, color=GRAY, lw=0)
        ax.scatter(col[low] * 100, dbl[low] * 100, s=22, color=ORANGE, lw=0, label="1つの質問で低い10店")
        ax.set_xlabel(name)
    axs[0].set_ylabel("1つの質問の「はい」（%）")
    axs[1].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.suptitle(f"1つの質問で低い10店のうち、本当に接客の低い10店は{one['low10_double_in_true_low10_service']}店、"
                 f"料理の低い10店は{one['low10_double_in_true_low10_food']}店（1回分）", fontsize=11.5)
    save(fig, "a869_chain.png", SRC)

    # 図3：決め方の混ざり方で、接客の低い10店を当てる割合
    s3 = sens[sens.rho == 0.3]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(len(s3))
    ax.barh(y + 0.2, s3.hit_service_double * 100, 0.4, color=ORANGE, label="1つの質問で選ぶ")
    ax.barh(y - 0.2, s3.hit_service_sep * 100, 0.4, color=BLUE, label="接客だけを聞いて選ぶ")
    ax.axvline(10, color=GRAY, ls="--", lw=.8); ax.text(10.5, -0.75, "でたらめに選ぶと10%", fontsize=8.5, color=GRAY, va="center")
    ax.set_yticks(y); ax.set_yticklabels(s3["mix"]); ax.set_ylim(len(s3) - 0.4, -1.1)
    ax.set_xlim(0, 100); ax.set_xlabel("選んだ10店のうち、本当に接客の低い10店だった割合（%、100回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=2)
    ax.set_title(f"接客の悪い店を探すとき、1つの質問の当たりは決め方しだいで{s3.hit_service_double.min()*100:.0f}〜{s3.hit_service_double.max()*100:.0f}%")
    save(fig, "a869_rules.png", SRC)
    print(json.dumps({"ex": ex, "base": base, "one": one}, ensure_ascii=False, indent=0))
    print(sens.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
