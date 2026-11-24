"""1251 読み放題のページ数は、文字の大きさや図の多さでどれだけ変わるのか？（架空のデータ）

作成者が置いた架空の電子書籍8冊（字数と図の数を作成者が決めたもの）と、架空の読者。
読者ごとに端末の文字の大きさ（1画面の字数）と、本のどこまで読んだか（読んだ割合）を乱数で決める。
ページの数え方を2つ置く。
  画面のページ：めくった画面の数。1画面の字数は文字の大きさで変わり、図1枚は文字の大きさによらず1画面。
  標準のページ：文字の大きさによらず「500字で1ページ」、図1枚は w ページ（w を 0.25・1・2 で比べる）。
本当の読まれた分量は、作成者が「図1枚＝500字分」と置いて、読んだ字数＋読んだ図×500字で数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1251
SRC = "架空の電子書籍8冊と読者（作成者が置いた字数・図の数・文字の大きさの割合からの乱数、seed 1251）"
CPP = np.array([900, 700, 500, 350, 250])          # 文字の大きさ1（小）〜5（大）の1画面の字数
MIX0 = np.array([0.10, 0.20, 0.35, 0.20, 0.15])    # 文字の大きさの、全体での割合
STD_CHARS = 500                                     # 標準のページ：500字で1ページ
WS = [0.25, 1.0, 2.0]                               # 標準のページで、図1枚を何ページと数えるか
BOOKS = pd.DataFrame({"book": list("ABCDEFGH"),
                      "chars": [90000, 80000, 70000, 60000, 50000, 45000, 40000, 35000],
                      "figures": [0, 5, 10, 20, 40, 60, 90, 120]})
N_READERS = 300
BASE = dict(conc=20.0, figw_true=500.0, m_lo=0.35, m_hi=0.75, k=4.0)
RULES = ["screen"] + [f"std_w{w}" for w in WS]
RULE_JA = {"screen": "画面のページ", "std_w0.25": "標準のページ（図1枚＝0.25ページ）",
           "std_w1.0": "標準のページ（図1枚＝1ページ）", "std_w2.0": "標準のページ（図1枚＝2ページ）"}


def one_set(rng, conc=20.0, figw_true=500.0, m_lo=0.35, m_hi=0.75, k=4.0, keep=False):
    ch, fg = BOOKS.chars.values.astype(float), BOOKS.figures.values.astype(float)
    nb = len(BOOKS)
    m = rng.uniform(m_lo, m_hi, nb)                 # 本ごとの、読んだ割合の平均（作成者が置く）
    mix = rng.dirichlet(conc * MIX0, nb)            # 本ごとの、読者の文字の大きさの割合
    out = {r: np.zeros(nb) for r in RULES}
    true = np.zeros(nb)
    big_share = np.zeros(nb)
    rows = []
    for b in range(nb):
        font = rng.choice(5, N_READERS, p=mix[b])
        p = rng.beta(m[b] * k, (1 - m[b]) * k, N_READERS)
        true[b] = np.mean(p * (ch[b] + fg[b] * figw_true))
        out["screen"][b] = np.mean(p * (ch[b] / CPP[font] + fg[b]))
        for w in WS:
            out[f"std_w{w}"][b] = np.mean(p * (ch[b] / STD_CHARS + fg[b] * w))
        big_share[b] = np.mean(font >= 3)
        if keep:
            rows.append(pd.DataFrame({"book": BOOKS.book[b], "font_size": font + 1, "read_share": p.round(4)}))
    return true, out, m, big_share, (pd.concat(rows) if keep else None)


def flips(a, b):
    i, j = np.triu_indices(len(a), 1)
    return int(np.sum(np.sign(a[i] - a[j]) != np.sign(b[i] - b[j])))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    BOOKS.to_csv(DATA / "books.csv", index=False)

    # 1) 最後まで読んだときのページ数（式どおり）
    ch, fg = BOOKS.chars.values, BOOKS.figures.values
    full = BOOKS.copy()
    for i, c in enumerate(CPP):
        full[f"screen_font{i+1}"] = np.round(ch / c + fg, 2)
    for w in WS:
        full[f"std_w{w}"] = np.round(ch / STD_CHARS + fg * w, 2)
    full["amount_10k"] = (ch + fg * 500) / 10000
    full["font_ratio_5_to_1"] = np.round(full.screen_font5 / full.screen_font1, 4)
    full.to_csv(RES / "full_read_pages.csv", index=False)

    # 1回分の読者（data に置く）
    _, _, _, _, rd = one_set(np.random.default_rng([SEED, 0]), keep=True)
    rd.to_csv(DATA / "readers_one_set.csv", index=False)

    # 2) 基本の置き方で200回
    reps = []
    per_amount = {r: [] for r in RULES}
    corr_big = []
    for r in range(200):
        true, out, m, big, _ = one_set(np.random.default_rng([SEED, 1, r]), **BASE)
        row = {"rep": r}
        for rule in RULES:
            row[f"flips_{rule}"] = flips(out[rule], true)
            row[f"top1_{rule}"] = int(np.argmax(out[rule]) == np.argmax(true))
            per_amount[rule].append(out[rule] / true * 10000)
        # 画面のページ÷分量 と 大きい文字（4・5）の読者の割合の関係
        corr_big.append(np.corrcoef(big[ch > 0], (out["screen"] / true)[ch > 0])[0, 1])
        reps.append(row)
    reps = pd.DataFrame(reps)
    reps.to_csv(RES / "reps_base.csv", index=False)
    pa = pd.DataFrame({"book": BOOKS.book})
    for rule in RULES:
        arr = np.array(per_amount[rule])
        pa[f"{rule}_mean"] = arr.mean(0).round(2)
        pa[f"{rule}_p10"] = np.percentile(arr, 10, axis=0).round(2)
        pa[f"{rule}_p90"] = np.percentile(arr, 90, axis=0).round(2)
    pa.to_csv(RES / "pages_per_10k_amount.csv", index=False)
    a_text = np.array(per_amount["screen"])[:, 0]   # 図のない本A
    head = {
        "pairs": 28,
        "flips_mean": {rule: round(float(reps[f"flips_{rule}"].mean()), 2) for rule in RULES},
        "flips_range": {rule: [int(reps[f"flips_{rule}"].min()), int(reps[f"flips_{rule}"].max())] for rule in RULES},
        "top1_match_share": {rule: round(float(reps[f"top1_{rule}"].mean()), 4) for rule in RULES},
        "share_reps_any_flip": {rule: round(float((reps[f"flips_{rule}"] > 0).mean()), 4) for rule in RULES},
        "screen_per_10k_bookA_p10_p90": [round(float(np.percentile(a_text, 10)), 2), round(float(np.percentile(a_text, 90)), 2)],
        "screen_per_10k_bookA_min_max": [round(float(a_text.min()), 2), round(float(a_text.max()), 2)],
        "corr_big_font_share_vs_screen_per_amount_mean": round(float(np.mean(corr_big)), 4),
        "std_w1_equals_true_scaled": True,
    }

    # 3) 確かめ：文字の大きさの割合の本ごとの違い×本当の図の重さ×読んだ割合の違い（27通り、各50回）
    grid = []
    for conc in [5.0, 20.0, 100.0]:
        for fw in [250.0, 500.0, 1000.0]:
            for (lo, hi) in [(0.5, 0.6), (0.35, 0.75), (0.2, 0.9)]:
                f = {rule: [] for rule in RULES}
                for r in range(50):
                    sd = [SEED, 2, int(conc), int(fw), int(lo * 100), r]
                    true, out, _, _, _ = one_set(np.random.default_rng(sd), conc=conc, figw_true=fw, m_lo=lo, m_hi=hi)
                    for rule in RULES:
                        f[rule].append(flips(out[rule], true))
                grid.append({"conc": conc, "figw_true": fw, "m_lo": lo, "m_hi": hi,
                             **{f"flips_{rule}": round(float(np.mean(f[rule])), 2) for rule in RULES}})
    gr = pd.DataFrame(grid)
    gr.to_csv(RES / "grid.csv", index=False)
    best = gr[[f"flips_{r}" for r in RULES]].idxmin(axis=1).str.replace("flips_", "")
    robust = {"settings": int(len(gr)),
              "flips_range": {rule: [float(gr[f"flips_{rule}"].min()), float(gr[f"flips_{rule}"].max())] for rule in RULES},
              "screen_flips_by_conc": {str(int(c)): [float(gr[gr.conc == c].flips_screen.min()), float(gr[gr.conc == c].flips_screen.max())]
                                       for c in [5, 20, 100]},
              "screen_flips_by_m": {f"{lo}-{hi}": [float(gr[gr.m_lo == lo].flips_screen.min()), float(gr[gr.m_lo == lo].flips_screen.max())]
                                    for lo, hi in [(0.5, 0.6), (0.35, 0.75), (0.2, 0.9)]},
              "fewest_flips_rule_by_figw": {str(int(fw)): sorted(set(best[gr.figw_true == fw])) for fw in [250, 500, 1000]},
              "std_w1_zero_when_figw500": bool((gr[gr.figw_true == 500]["flips_std_w1.0"] == 0).all())}

    out = {"headline": head, "full_read": {"font_ratio_5_to_1_range": [float(full.font_ratio_5_to_1.min()), float(full.font_ratio_5_to_1.max())],
                                           "bookA_screen_font1_font5": [float(full.screen_font1[0]), float(full.screen_font5[0])],
                                           "bookH_screen_font1_font5": [float(full.screen_font1[7]), float(full.screen_font5[7])],
                                           "bookA_std": [float(full[f"std_w{w}"][0]) for w in WS],
                                           "bookH_std": [float(full[f"std_w{w}"][7]) for w in WS]},
           "robust": robust,
           "setup": {"cpp": CPP.tolist(), "mix": MIX0.tolist(), "std_chars": STD_CHARS, "ws": WS, "readers_per_book": N_READERS,
                     **BASE, "reps": 200, "grid_reps": 50}}
    json.dump(out, open(RES / "a1251_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：最後まで読んだときのページ数
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(len(BOOKS))
    series = [("screen_font1", LIGHT, "画面のページ（文字の大きさ1・小）"), ("screen_font3", BLUE, "画面のページ（文字の大きさ3）"),
              ("screen_font5", INK, "画面のページ（文字の大きさ5・大）"), ("std_w1.0", ORANGE, "標準のページ（図1枚＝1ページ）")]
    for i, (col, c, lab) in enumerate(series):
        ax.bar(x + (i - 1.5) * 0.2, full[col], 0.2, color=c, label=lab)
    ax.set_xticks(x); ax.set_xticklabels([f"{b}\n{c//10000}万{'' if c % 10000 == 0 else str(c % 10000 // 1000) + '千'}字\n図{f}枚"
                                          for b, c, f in zip(BOOKS.book, BOOKS.chars, BOOKS.figures)], fontsize=8)
    ax.set_ylim(0, 400); ax.set_ylabel("最後まで読んだときのページ数")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("同じ1冊を読み切っても、文字の大きさでページ数が変わる（式どおり）")
    save(fig, "a1251_full_read_pages.png", SRC)

    # 図2：読まれた分量1万字分あたりのページ数（200回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    cols = {"screen": INK, "std_w0.25": LIGHT, "std_w1.0": ORANGE, "std_w2.0": BLUE}
    for i, rule in enumerate(RULES):
        mu = pa[f"{rule}_mean"].values
        lo = mu - pa[f"{rule}_p10"].values; hi = pa[f"{rule}_p90"].values - mu
        ax.bar(x + (i - 1.5) * 0.2, mu, 0.2, color=cols[rule], label=RULE_JA[rule],
               yerr=[lo, hi] if rule == "screen" else None, error_kw=dict(lw=0.8, ecolor=GRAY))
    ax.set_xticks(x); ax.set_xticklabels([f"{b}（図{f}枚）" for b, f in zip(BOOKS.book, BOOKS.figures)], fontsize=8)
    ax.set_ylim(0, 45); ax.set_ylabel("読まれた分量1万字分あたりのページ数")
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    ax.set_title("同じ分量を読まれても、ページ数は本で変わる（200回の平均、線は画面のページの10〜90%）", fontsize=11)
    save(fig, "a1251_pages_per_amount.png", SRC)

    # 図3：確かめ。27通りの入れかわった組の数
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    gs = gr.sort_values(["figw_true", "conc", "m_lo"], ascending=[True, True, False]).reset_index(drop=True)
    gx = np.arange(len(gs))
    for rule in RULES:
        ax.plot(gx, gs[f"flips_{rule}"], marker="o", ms=4, lw=0, color=cols[rule], label=RULE_JA[rule])
    for k in [9, 18]:
        ax.axvline(k - 0.5, color=GRAY, lw=0.8, ls=":")
    for k, fw in enumerate(["図1枚＝250字分", "図1枚＝500字分", "図1枚＝1,000字分"]):
        ax.text(k * 9 + 4, 27.3, f"本当の重さ：{fw}", ha="center", fontsize=8)
    ax.set_xticks(gx); ax.set_xticklabels([f"{int(c)}" for c in gs.conc], fontsize=6.5)
    ax.set_xlabel("27通り（下の数字は文字の大きさの割合の本どうしの近さ。同じ数字の中は、読んだ割合の本ごとの差が小・中・大の順）", fontsize=8)
    ax.set_ylim(0, 28); ax.set_ylabel("本当の分量と順が入れかわった組\n（28組中、各50回の平均）", fontsize=9, linespacing=1.5)
    ax.legend(frameon=False, fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    ax.set_title("どの数え方の入れかわりが少ないかは、図1枚の重さの置き方で変わる", fontsize=11)
    save(fig, "a1251_grid.png", SRC, y=-0.2)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
