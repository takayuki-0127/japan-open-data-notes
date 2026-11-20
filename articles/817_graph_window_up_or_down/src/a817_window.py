"""817 期間の切り出し方で、「上昇」も「下落」も描けるのか？（架空のデータ）

架空の店の月ごとの来店数（10年＝120か月）。本当の伸びは0（作成者が置いた正解）。
季節の山谷（12月が山、6月が谷）と、前の月の揺れが残る揺れ（AR(1)）を足す。
10年の中から、長さ12〜36か月の期間を、始まりの月をずらしてすべて切り出し、
「上昇」「下落」「横ばい」のどれに見えるかを3つの読み方で数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from numpy.lib.stride_tricks import sliding_window_view as swv
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 817
SRC = "架空の店の月ごとの来店数（作成者が乱数で作成、seed 817）"
T = 120
LEVEL = 3000
N_STORE = 200
LENGTHS = range(12, 37)
BASE = {"season": 0.15, "phi": 0.8, "sd": 0.08, "trend": 0.0, "cut": 0.10}


def make_store(rng, season=0.15, phi=0.8, sd=0.08, trend=0.0):
    """log の来店数 = log(3000) + 伸び×年 + 季節 + AR(1) の揺れ（揺れの全体の標準偏差は sd）"""
    t = np.arange(T)
    cal = t % 12 + 1  # 1〜12月（1か月目を1月とする）
    seas = season * np.cos(2 * np.pi * (cal - 12) / 12)
    e = np.empty(T)
    e[0] = rng.normal(0, sd)
    for i in range(1, T):
        e[i] = phi * e[i - 1] + rng.normal(0, sd * np.sqrt(1 - phi ** 2))
    return LEVEL * np.exp(np.log(1 + trend) * t / 12 + seas + e)


def classify(x, cut):
    return np.where(x >= cut, "上昇", np.where(x <= -cut, "下落", "横ばい"))


def windows(y, L, cut):
    """長さ L のすべての期間で、3つの読み方の変化率を返す"""
    w = swv(y, L)                                  # (始まりの数, L)
    endpoint = w[:, -1] / w[:, 0] - 1              # 始めの月と終わりの月
    x = np.arange(L); xc = x - x.mean()
    b = (np.log(w) * xc).sum(1) / (xc ** 2).sum()  # 期間に引いた直線（対数）の傾き
    line = np.exp(b * (L - 1)) - 1                 # 直線で見た期間の始めから終わりまでの変化
    avg12 = w[:, -12:].mean(1) / w[:, :12].mean(1) - 1 if L >= 24 else np.full(len(w), np.nan)
    return endpoint, line, avg12


def shares(stores, cut, lengths=LENGTHS):
    rec = []
    for L in lengths:
        for y in stores:
            ep, ln, av = windows(y, L, cut)
            for name, v in [("始めの月と終わりの月", ep), ("期間に引いた直線", ln), ("最初と最後の12か月の平均", av)]:
                v = v[~np.isnan(v)]
                if len(v) == 0:
                    continue
                c = classify(v, cut)
                rec.append({"length": L, "method": name, "n": len(v), "up": int((c == "上昇").sum()),
                            "down": int((c == "下落").sum())})
    d = pd.DataFrame(rec)
    return d


def agg(d, by):
    g = d.groupby(by, sort=False)[["n", "up", "down"]].sum()
    g["up_share"] = (g.up / g.n).round(3); g["down_share"] = (g.down / g.n).round(3)
    g["flat_share"] = (1 - g.up_share - g.down_share).round(3)
    return g.reset_index()


def main():
    rng = np.random.default_rng(SEED)
    stores = [make_store(rng) for _ in range(N_STORE)]
    one = stores[0]
    pd.DataFrame({"month": np.arange(1, T + 1), "calendar_month": np.arange(T) % 12 + 1,
                  "visitors": one.round(0).astype(int)}).to_csv(DATA / "store_visitors.csv", index=False)

    # 1) 200店×すべての期間
    d = shares(stores, BASE["cut"])
    by_method = agg(d, ["method"])
    by_len = agg(d, ["method", "length"])
    by_method.to_csv(RES / "share_by_method.csv", index=False)
    by_len.to_csv(RES / "share_by_length.csv", index=False)

    # 2) 1店（data）の中で選べる「いちばんの上昇」と「いちばんの下落」（24か月の期間）
    ep, ln, av = windows(one, 24, BASE["cut"])
    i_up, i_dn = int(np.argmax(ep)), int(np.argmin(ep))
    store_any = []
    for y in stores:
        e = np.concatenate([windows(y, L, 0.1)[0] for L in LENGTHS])
        store_any.append({"has_up": bool((e >= 0.1).any()), "has_down": bool((e <= -0.1).any())})
    store_any = pd.DataFrame(store_any)
    one_res = {"len24_max_rise": round(float(ep[i_up]), 3), "len24_max_rise_start_month": i_up + 1,
               "len24_max_fall": round(float(ep[i_dn]), 3), "len24_max_fall_start_month": i_dn + 1,
               "len24_up_share_endpoint": round(float((ep >= 0.1).mean()), 3),
               "len24_down_share_endpoint": round(float((ep <= -0.1).mean()), 3),
               "len24_avg12_max": round(float(av.max()), 3), "len24_avg12_min": round(float(av.min()), 3),
               "ten_year_avg_first_vs_last12": round(float(one[-12:].mean() / one[:12].mean() - 1), 3)}
    both = {"stores_with_both_up_and_down_endpoint": round(float((store_any.has_up & store_any.has_down).mean()), 3)}

    # 3) 確かめ：揺れの残りやすさ・季節の大きさ・本当の伸び・線の幅を変える
    sens = []
    settings = [("基本（残りやすさ0.8・季節15%・伸び0・線±10%）", {}, 0.10),
                ("残りやすさ 0.5", {"phi": 0.5}, 0.10), ("残りやすさ 0.95", {"phi": 0.95}, 0.10),
                ("季節なし", {"season": 0.0}, 0.10), ("季節30%", {"season": 0.30}, 0.10),
                ("本当の伸び 年+3%", {"trend": 0.03}, 0.10), ("本当の伸び 年−3%", {"trend": -0.03}, 0.10),
                ("線±5%", {}, 0.05), ("線±20%", {}, 0.20)]
    for k, (label, kw, cut) in enumerate(settings):
        r = np.random.default_rng(SEED * 100 + k)
        st = [make_store(r, **kw) for _ in range(N_STORE)]
        a = agg(shares(st, cut), ["method"])
        a.insert(0, "setting", label)
        sens.append(a)
    sens = pd.concat(sens, ignore_index=True)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"assumptions": {"months": T, "level": LEVEL, "stores": N_STORE, "lengths": [12, 36], **BASE},
           "by_method": by_method.to_dict("records"), "by_length": by_len.to_dict("records"),
           "one_store": one_res, "all_stores": both, "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a817_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ店の10年から、上昇の2年と下落の2年を切り出す
    fig = plt.figure(figsize=(10, 6.2))
    ax0 = fig.add_subplot(2, 1, 1)
    m = np.arange(1, T + 1)
    ax0.plot(m, one, color=GRAY, lw=1.2)
    ax0.axvspan(i_up + 1, i_up + 24, color=BLUE, alpha=.15); ax0.axvspan(i_dn + 1, i_dn + 24, color=ORANGE, alpha=.15)
    ax0.set_ylim(0, one.max() * 1.1); ax0.set_xlabel("月（10年）"); ax0.set_ylabel("来店数")
    ax0.set_title("10年全体（本当の伸びは0と置いた。青と橙が下の2つの期間）")
    for k, (i, col, word) in enumerate([(i_up, BLUE, "上昇"), (i_dn, ORANGE, "下落")]):
        ax = fig.add_subplot(2, 2, 3 + k)
        mm = m[i:i + 24]; yy = one[i:i + 24]
        ax.plot(mm, yy, color=col, lw=2)
        ax.set_ylim(0, one.max() * 1.1)
        ch = yy[-1] / yy[0] - 1
        ax.set_title(f"{i + 1}〜{i + 24}か月目：始め→終わり {ch * 100:+.0f}%（「{word}」）", fontsize=11)
        ax.set_xlabel("月")
    fig.suptitle("同じ店の同じ10年から、「上昇」の2年も「下落」の2年も切り出せる", y=1.0)
    fig.tight_layout()
    save(fig, "a817_two_cuts.png", SRC)

    # 図2：読み方ごとの上昇・横ばい・下落の割合
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    labs = list(by_method.method)
    yy = np.arange(len(labs))[::-1]
    up, fl, dn = by_method.up_share * 100, by_method.flat_share * 100, by_method.down_share * 100
    ax.barh(yy, up, color=BLUE, label="上昇（+10%以上）")
    ax.barh(yy, fl, left=up, color="#e4e3df", label="横ばい")
    ax.barh(yy, dn, left=up + fl, color=ORANGE, label="下落（−10%以下）")
    for yi, a, b, c in zip(yy, up, fl, dn):
        ax.text(a / 2, yi, f"{a:.0f}%", ha="center", va="center", fontsize=9, color="white")
        ax.text(a + b / 2, yi, f"{b:.0f}%", ha="center", va="center", fontsize=9)
        ax.text(a + b + c / 2, yi, f"{c:.0f}%", ha="center", va="center", fontsize=9, color="white")
    ax.set_yticks(yy); ax.set_yticklabels(labs); ax.set_xlim(0, 100)
    ax.set_xlabel("切り出した期間のうちの割合（%、200店・長さ12〜36か月のすべての期間）")
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    ax.set_title("本当の伸びは0でも、始めと終わりの月で比べると6割が上昇か下落に見える", pad=28)
    save(fig, "a817_share.png", SRC)

    # 図3：確かめ（上昇か下落に見えた割合）
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    labs = [s for s, _, _ in settings]
    yy = np.arange(len(labs))[::-1]
    for off, meth, col in [(0.2, "始めの月と終わりの月", ORANGE), (-0.2, "最初と最後の12か月の平均", BLUE)]:
        v = [float(sens[(sens.setting == s) & (sens.method == meth)].eval("up_share + down_share").iloc[0]) * 100 for s in labs]
        ax.barh(yy + off, v, 0.38, color=col, label=meth)
        for yi, vv in zip(yy + off, v):
            ax.text(vv + 1, yi, f"{vv:.0f}%", va="center", fontsize=8)
    ax.set_yticks(yy); ax.set_yticklabels(labs, fontsize=9); ax.set_xlim(0, 105)
    ax.set_xlabel("上昇か下落に見えた期間の割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("置き方を変えても、始めと終わりの月で比べると3〜8割が上昇か下落に見えた")
    save(fig, "a817_sens.png", SRC)
    print(json.dumps({k: out[k] for k in ["by_method", "by_length", "one_store", "all_stores"]}, ensure_ascii=False, indent=1))
    print(sens.to_string())


if __name__ == "__main__":
    main()
