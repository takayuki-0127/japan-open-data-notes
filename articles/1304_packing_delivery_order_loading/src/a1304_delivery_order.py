"""1304 届ける順に取り出せるよう、あとで届ける荷物を奥に積む決まりを入れると、積載率はどれだけ下がるのか？（架空のデータ）

作成者が置いた架空の配送。荷台の床は幅200cm・奥行き420cm。荷物は床に並べるだけで上に重ねない、向きは変えないと置く。
荷物は荷台の幅の向きに「列」として並べ、列の奥行きはその列でいちばん奥行きのある荷物で決まる。列は奥から順に作る。
1日に40か所へ届け、1か所の荷物の数は1＋（平均1の個数）、荷物の幅と奥行きはそれぞれ30〜90cm（5cm刻みの一様）。
車は届ける順に配送先を受け持ち、次の配送先の荷物が載らなくなったら次の車にする。
積み方は3つ：
  ①決まりなし：その車の荷物を奥行きの大きい順に並べてから、入る最初の列へ（どの列からも取り出せると見なす）
  ②奥に積む決まり：あとで届ける配送先の荷物ほど奥に。届ける順の逆に並べ、今の列に入らなければ次の列（同じ列に配送先がまざるのはよい）
  ③配送先ごとに列を分ける：②に加え、配送先が変わるたびに新しい列
積載率は、荷物の床の面積の合計÷（車の台数×荷台の床の面積）。
(1) 基本で300日、台数と積載率を比べる
(2) 確かめ：荷物の大きさ3通り×1か所の荷物の数3通り（各200日）
(3) 確かめ：②と同じ並びのまま、列の切れ目をいちばん良く選ぶ積み方（②の積み方が下手なだけかを見る）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1304
SRC = "架空の配送（作成者が置いた荷台の大きさ・荷物の大きさ・配送先の数からの乱数、seed 1304）"
W, D = 200, 420
STOPS = 40
DAYS = 300
GRID_DAYS = 200
SIZES = {"小さめ（20〜60cm）": (20, 60), "基本（30〜90cm）": (30, 90), "大きめ（50〜120cm）": (50, 120)}
EXTRA = {"1か所1個": 0.0, "基本（平均2個）": 1.0, "平均4個": 3.0}
BASE_SIZE, BASE_EXTRA = "基本（30〜90cm）", "基本（平均2個）"
RULES = {"free": "①決まりなし", "rear": "②奥に積む決まり", "split": "③配送先ごとに列を分ける"}


def r(x, d=4):
    return round(float(x), d)


def depth_free(pk):
    """pk: (stop, w, d) のリスト。奥行きの大きい順に並べ、入る最初の列へ"""
    rows_w, rows_d = [], []
    for _s, w, d in sorted(pk, key=lambda t: (-t[2], -t[1])):
        for i, rw in enumerate(rows_w):
            if rw + w <= W:
                rows_w[i] = rw + w
                break
        else:
            rows_w.append(w)
            rows_d.append(d)
    return sum(rows_d)


def depth_rear(pk, split=False):
    """あとで届ける配送先ほど奥。届ける順の逆に、配送先の中は奥行きの大きい順に並べて、今の列に入らなければ次の列"""
    used, rw, rd, last = 0, None, 0, None
    for s, w, d in sorted(pk, key=lambda t: (-t[0], -t[2], -t[1])):
        if rw is None or rw + w > W or (split and s != last):
            used += rd
            rw, rd = w, d
        else:
            rw += w
            rd = max(rd, d)
        last = s
    return used + rd


def depth_rear_best(pk):
    """確かめ：②と同じ並び（届ける順の逆、配送先の中は奥行きの大きい順）のまま、列の切れ目をいちばん良く選ぶ（奥行きの合計が最小）"""
    seq = sorted(pk, key=lambda t: (-t[0], -t[2], -t[1]))
    n = len(seq)
    f = [0] + [float("inf")] * n
    for i in range(1, n + 1):
        w, d = 0, 0
        for j in range(i - 1, -1, -1):
            w += seq[j][1]
            if w > W:
                break
            d = max(d, seq[j][2])
            if f[j] + d < f[i]:
                f[i] = f[j] + d
    return f[n]


DEPTH = {"free": depth_free, "rear": depth_rear, "split": lambda pk: depth_rear(pk, True), "rear_best": depth_rear_best}


def make_day(rng, lo, hi, extra):
    pk = []
    for s in range(1, STOPS + 1):
        k = 1 + (rng.poisson(extra) if extra > 0 else 0)
        for _ in range(k):
            pk.append((s, int(rng.integers(lo // 5, hi // 5 + 1)) * 5, int(rng.integers(lo // 5, hi // 5 + 1)) * 5))
    return pk


def trucks(pk, rule):
    """届ける順に配送先を受け持ち、載らなくなったら次の車"""
    f = DEPTH[rule]
    by = {}
    for p in pk:
        by.setdefault(p[0], []).append(p)
    n, cur, depths = 0, [], []
    for s in range(1, STOPS + 1):
        trial = cur + by[s]
        if cur and f(trial) > D:
            depths.append(f(cur))
            n += 1
            cur = list(by[s])
        else:
            cur = trial
    depths.append(f(cur))
    n += 1
    return n, depths


def run(rng, lo, hi, extra, days):
    rows = []
    for d in range(days):
        pk = make_day(rng, lo, hi, extra)
        area = sum(w * dd for _s, w, dd in pk)
        o = {"day": d + 1, "packages": len(pk), "area_m2": round(area / 1e4, 4)}
        for k in list(RULES) + ["rear_best"]:
            n, _dp = trucks(pk, k)
            o[f"trucks_{k}"] = n
        # 同じ荷物で比べる：①で決めた車の受け持ちのまま、②③で積むと奥行きはどれだけ要るか
        by = {}
        for p in pk:
            by.setdefault(p[0], []).append(p)
        cur, same = [], []
        for s in range(1, STOPS + 1):
            trial = cur + by[s]
            if cur and depth_free(trial) > D:
                same.append(cur)
                cur = list(by[s])
            else:
                cur = trial
        same.append(cur)
        o["same_load_depth_free"] = sum(depth_free(c) for c in same)
        o["same_load_depth_rear"] = sum(depth_rear(c) for c in same)
        o["same_load_over_D_rear"] = sum(depth_rear(c) > D for c in same)
        o["same_load_trucks"] = len(same)
        rows.append(o)
    return pd.DataFrame(rows)


def summarize(df):
    bed = W * D / 1e4
    out = {"days": len(df), "packages_mean": r(df.packages.mean(), 2), "area_m2_mean": r(df.area_m2.mean(), 3)}
    for k in RULES:
        t = df[f"trucks_{k}"]
        out[k] = {"trucks_mean": r(t.mean(), 3), "fill_pct": r(df.area_m2.sum() / (t.sum() * bed) * 100, 2)}
    t = df.trucks_rear_best
    out["rear_best"] = {"trucks_mean": r(t.mean(), 3), "fill_pct": r(df.area_m2.sum() / (t.sum() * bed) * 100, 2)}
    for k in ("rear", "split", "rear_best"):
        out[k]["extra_trucks_mean"] = r((df[f"trucks_{k}"] - df.trucks_free).mean(), 3)
        out[k]["extra_trucks_pct"] = r((df[f"trucks_{k}"].sum() / df.trucks_free.sum() - 1) * 100, 2)
        out[k]["fill_drop_pt"] = r(out["free"]["fill_pct"] - out[k]["fill_pct"], 2)
        out[k]["days_more_trucks_pct"] = r((df[f"trucks_{k}"] > df.trucks_free).mean() * 100, 2)
    out["same_load"] = {"depth_ratio_rear_vs_free": r(df.same_load_depth_rear.sum() / df.same_load_depth_free.sum(), 4),
                        "loads_over_bed_with_rear_pct": r(df.same_load_over_D_rear.sum() / df.same_load_trucks.sum() * 100, 2)}
    return out


def main():
    t0 = time.time()
    out = {"setting": {"bed_width_cm": W, "bed_depth_cm": D, "stops": STOPS, "days": DAYS, "grid_days": GRID_DAYS,
                       "sizes_cm": {k: list(v) for k, v in SIZES.items()}, "extra_mean": EXTRA, "rules": RULES, "seed": SEED}}
    rng = np.random.default_rng(SEED)
    lo, hi = SIZES[BASE_SIZE]
    df = run(rng, lo, hi, EXTRA[BASE_EXTRA], DAYS)
    df.to_csv(DATA / "days_base.csv", index=False)
    out["base"] = summarize(df)
    mx = int(max((df.trucks_rear - df.trucks_free).max(), (df.trucks_split - df.trucks_free).max()))
    dist = pd.DataFrame({"extra_trucks": np.arange(0, mx + 1)})
    dist["days_rear"] = [int(((df.trucks_rear - df.trucks_free) == k).sum()) for k in dist.extra_trucks]
    dist["days_split"] = [int(((df.trucks_split - df.trucks_free) == k).sum()) for k in dist.extra_trucks]
    dist.to_csv(RES / "base_extra_trucks_dist.csv", index=False)
    out["base_extra_trucks_dist"] = dist.to_dict("records")

    g = []
    for i, (sn, (lo, hi)) in enumerate(SIZES.items()):
        for j, (en, ex) in enumerate(EXTRA.items()):
            g_rng = np.random.default_rng([SEED, i, j])
            sm = summarize(run(g_rng, lo, hi, ex, GRID_DAYS))
            g.append({"size": sn, "per_stop": en, "packages_mean": sm["packages_mean"],
                      "trucks_free": sm["free"]["trucks_mean"], "trucks_rear": sm["rear"]["trucks_mean"],
                      "trucks_split": sm["split"]["trucks_mean"],
                      "fill_free_pct": sm["free"]["fill_pct"], "fill_rear_pct": sm["rear"]["fill_pct"],
                      "fill_split_pct": sm["split"]["fill_pct"],
                      "trucks_rear_best": sm["rear_best"]["trucks_mean"], "fill_rear_best_pct": sm["rear_best"]["fill_pct"],
                      "fill_drop_rear_pt": sm["rear"]["fill_drop_pt"], "fill_drop_rear_best_pt": sm["rear_best"]["fill_drop_pt"], "fill_drop_split_pt": sm["split"]["fill_drop_pt"],
                      "extra_trucks_rear_pct": sm["rear"]["extra_trucks_pct"], "extra_trucks_split_pct": sm["split"]["extra_trucks_pct"],
                      "same_load_depth_ratio_rear": sm["same_load"]["depth_ratio_rear_vs_free"]})
    gr = pd.DataFrame(g)
    gr.to_csv(RES / "grid.csv", index=False)
    out["grid_summary"] = {"n": len(gr),
                           "fill_drop_rear_pt_min": r(gr.fill_drop_rear_pt.min(), 2), "fill_drop_rear_pt_max": r(gr.fill_drop_rear_pt.max(), 2),
                           "extra_trucks_rear_pct_min": r(gr.extra_trucks_rear_pct.min(), 2), "extra_trucks_rear_pct_max": r(gr.extra_trucks_rear_pct.max(), 2),
                           "fill_drop_rear_best_pt_min": r(gr.fill_drop_rear_best_pt.min(), 2), "fill_drop_rear_best_pt_max": r(gr.fill_drop_rear_best_pt.max(), 2),
                           "depth_ratio_min": r(gr.same_load_depth_ratio_rear.min(), 4), "depth_ratio_max": r(gr.same_load_depth_ratio_rear.max(), 4),
                           "fill_drop_split_pt_min": r(gr.fill_drop_split_pt.min(), 2), "fill_drop_split_pt_max": r(gr.fill_drop_split_pt.max(), 2)}

    b = out["base"]
    # 図1：基本の積載率
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    vals = [b[k]["fill_pct"] for k in RULES]
    bars = ax.bar(list(RULES.values()), vals, color=[GRAY, BLUE, ORANGE], width=0.55)
    for bb, v, k in zip(bars, vals, RULES):
        ax.text(bb.get_x() + bb.get_width() / 2, v, f"{v:.2f}%\n（{b[k]['trucks_mean']:.3f}台）", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_ylabel("床の積載率（%）")
    ax.set_title("床の積載率と1日の台数（1日40か所・荷物は1日平均%.2f個、300日）" % b["packages_mean"])
    save(fig, "a1304_base.png", SRC)

    # 図2：増えた台数の分布
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = dist.extra_trucks.values
    ax.bar(x - 0.18, dist.days_rear, 0.36, color=BLUE, label=RULES["rear"])
    ax.bar(x + 0.18, dist.days_split, 0.36, color=ORANGE, label=RULES["split"])
    ax.set_xticks(x, [f"+{k}台" for k in x])
    ax.set_ylim(0, DAYS)
    ax.set_xlabel("①決まりなしと比べて増えた台数")
    ax.set_ylabel("日数（300日のうち）")
    ax.set_title("1日に増えた車の台数（基本、300日）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1304_extra.png", SRC)

    # 図3：確かめ（積載率の下がり幅）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    cols = [ORANGE, BLUE, GREEN]
    xs = np.arange(len(EXTRA))
    for i, (sn, c) in enumerate(zip(SIZES, cols)):
        sub = gr[gr["size"] == sn]
        ax.bar(xs + (i - 1) * 0.25, sub.fill_drop_rear_pt, 0.25, color=c, label=sn)
    ax.set_xticks(xs, list(EXTRA))
    ax.set_ylim(0, max(gr.fill_drop_rear_pt.max() * 1.2, 1))
    ax.set_ylabel("②で下がった積載率（ポイント）")
    ax.set_title("荷物の大きさと1か所の数で、②の下がり幅（各200日）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1304_grid.png", SRC)

    (RES / "a1304_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(gr.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
