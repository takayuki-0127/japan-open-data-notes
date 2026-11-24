"""1193 1つの不具合で問い合わせが一度に来ると、件数の上位の種類は何を表すのか？（架空のデータ）

架空の会社の問い合わせ窓口。問い合わせの種類12（作成者が名前を置いた架空の分類）ごとに、
ふだんの1日の件数（ふだんの困りごと。ばらばらの原因から1件ずつ来る）を作成者が置く。
ときどき、ある種類で不具合が起き、1つの原因から問い合わせが数日に固まって来る（不具合の大きさを置く）。
月ごとに種類を件数の順に並べ、上位が「ふだんの困りごとの多さ」と「1つの不具合のかたまり」のどちらを表しているかを数える。
  ① 件数の順
  ② 件数の順。ただし、1日の件数がその種類の前の90日の1日の中央値の3倍を超えた日は、中央値に置きかえて数える
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1193
SRC = "架空の問い合わせ窓口の種類12（作成者が置いたふだんの件数・不具合の起き方からの乱数、seed 1193）"
CATS = ["ログイン", "支払い", "配送", "使い方", "会員情報", "返品", "通知", "請求書", "画面の表示", "予約", "解約", "その他"]
RATE0 = np.array([8, 7, 6, 5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1.0])   # ふだんの1日の件数
MONTH = 30
YEARS = 100
YEARS_GRID = 40
WARM_M = 3            # 初めの3か月は②の基準を作るためだけに使い、数えない
P_BUG = 0.05          # 1つの種類で、1か月に不具合が起きる確率
BUG_MED = 120         # 1つの不具合で来る件数の中央値
BUG_SD = 0.7          # 不具合の大きさのばらつき（対数の標準偏差）
SPREAD = [0.6, 0.3, 0.1]   # 不具合の問い合わせが起きた日から3日に分かれる割合
CAP_K = 3.0
CAP_WIN = 90


def rates_for(steep):
    """ふだんの件数の散らばり。steep=1 が基本、0.5 でならし、1.5 で上の種類に寄せる（合計はそろえる）"""
    r = RATE0 ** steep
    return r / r.sum() * RATE0.sum()


def simulate(rng, months, rate, p_bug=P_BUG, bug_med=BUG_MED):
    days = months * MONTH
    k = len(rate)
    base = rng.poisson(rate[None, :], size=(days, k)).astype(float)
    bug = np.zeros((days, k))
    events = []
    occur = rng.random((months, k)) < p_bug
    for m, c in zip(*np.nonzero(occur)):
        start = m * MONTH + rng.integers(0, MONTH)
        size = int(round(bug_med * np.exp(rng.normal(0, BUG_SD))))
        parts = rng.multinomial(size, SPREAD)
        for i, n in enumerate(parts):
            if start + i < days:
                bug[start + i, c] += n
        events.append((m, c, size))
    return base, bug, events


def capped(total):
    df = pd.DataFrame(total)
    med = df.rolling(CAP_WIN, min_periods=30).median().shift(1).values
    med = np.where(np.isnan(med), np.nanmedian(total, axis=0)[None, :], med)
    base_line = np.maximum(med, 1.0)
    return np.where(total > CAP_K * base_line, base_line, total)


def rank_corr(x, y):
    rx = np.argsort(np.argsort(-x, kind="stable")); ry = np.argsort(np.argsort(-y, kind="stable"))
    return float(np.corrcoef(rx, ry)[0, 1])


def evaluate(rng, months, rate, p_bug=P_BUG, bug_med=BUG_MED, keep_months=False):
    base, bug, events = simulate(rng, months + WARM_M, rate, p_bug, bug_med)
    total = base + bug
    cap = capped(total)
    k = len(rate)
    mb = base.reshape(-1, MONTH, k).sum(1)[WARM_M:]
    mbug = bug.reshape(-1, MONTH, k).sum(1)[WARM_M:]
    mt = total.reshape(-1, MONTH, k).sum(1)[WARM_M:]
    mc = cap.reshape(-1, MONTH, k).sum(1)[WARM_M:]
    true_top = int(np.argmax(rate)); true_top3 = set(np.argsort(-rate)[:3])
    rec = []
    for m in range(len(mt)):
        row = {"month": m + 1, "any_bug": bool(mbug[m].sum() > 0)}
        for name, v in [("count", mt[m]), ("capped", mc[m])]:
            top = int(np.argmax(v)); top3 = set(np.argsort(-v, kind="stable")[:3])
            row[f"{name}_top"] = top
            row[f"{name}_top_is_usual"] = top == true_top
            row[f"{name}_top_has_bug"] = bool(mbug[m, top] > 0)
            row[f"{name}_top_bug_share"] = float(mbug[m, top] / mt[m, top])
            row[f"{name}_top3_overlap"] = len(top3 & true_top3) / 3
            row[f"{name}_rank_corr"] = rank_corr(v, rate)
        # 不具合のあった種類の順位の上がり方（ふだんの順位 → 件数の順位）
        usual_rank = np.argsort(np.argsort(-rate, kind="stable"))
        cnt_rank = np.argsort(np.argsort(-mt[m], kind="stable"))
        cap_rank = np.argsort(np.argsort(-mc[m], kind="stable"))
        bugcats = np.nonzero(mbug[m] > 0)[0]
        row["bug_rank_up"] = [int(usual_rank[c] - cnt_rank[c]) for c in bugcats]
        row["bug_rank_up_capped"] = [int(usual_rank[c] - cap_rank[c]) for c in bugcats]
        row["bug_tickets"] = float(mbug[m].sum()); row["all_tickets"] = float(mt[m].sum())
        rec.append(row)
    r = pd.DataFrame(rec)
    return r, (mb, mbug, mt, mc, events) if keep_months else None


def summarize(r):
    bugm = r[r["any_bug"]]; nob = r[~r["any_bug"]]
    out = {"months": int(len(r)), "months_with_bug_pct": round(float(r["any_bug"].mean()) * 100, 2),
           "bug_ticket_share_pct": round(float(r["bug_tickets"].sum() / r["all_tickets"].sum()) * 100, 2)}
    for name in ["count", "capped"]:
        out[name] = {
            "top_is_usual_pct": round(float(r[f"{name}_top_is_usual"].mean()) * 100, 2),
            "top_is_usual_bug_months_pct": round(float(bugm[f"{name}_top_is_usual"].mean()) * 100, 2),
            "top_is_usual_nobug_months_pct": round(float(nob[f"{name}_top_is_usual"].mean()) * 100, 2),
            "top_has_bug_pct": round(float(r[f"{name}_top_has_bug"].mean()) * 100, 2),
            "top_has_bug_bug_months_pct": round(float(bugm[f"{name}_top_has_bug"].mean()) * 100, 2),
            "top_bug_share_when_has_bug_pct": round(float(r.loc[r[f"{name}_top_has_bug"], f"{name}_top_bug_share"].mean()) * 100, 2)
            if r[f"{name}_top_has_bug"].any() else None,
            "top_bug_share_all_months_pct": round(float(r[f"{name}_top_bug_share"].mean()) * 100, 2),
            "top_half_from_bug_pct": round(float((r[f"{name}_top_bug_share"] >= 0.5).mean()) * 100, 2),
            "top3_overlap_pct": round(float(r[f"{name}_top3_overlap"].mean()) * 100, 2),
            "top3_overlap_bug_months_pct": round(float(bugm[f"{name}_top3_overlap"].mean()) * 100, 2),
            "rank_corr_mean": round(float(r[f"{name}_rank_corr"].mean()), 3),
            "rank_corr_bug_months": round(float(bugm[f"{name}_rank_corr"].mean()), 3),
        }
    ups = np.concatenate([np.array(x) for x in r["bug_rank_up"] if len(x)] or [np.array([])])
    upc = np.concatenate([np.array(x) for x in r["bug_rank_up_capped"] if len(x)] or [np.array([])])
    out["bug_rank_up_median"] = float(np.median(ups)) if len(ups) else None
    out["bug_rank_up_capped_median"] = float(np.median(upc)) if len(upc) else None
    out["bug_rank_up_ge3_pct"] = round(float(np.mean(ups >= 3)) * 100, 2) if len(ups) else None
    out["bug_rank_up_capped_ge3_pct"] = round(float(np.mean(upc >= 3)) * 100, 2) if len(upc) else None
    return out


def main():
    t0 = time.time()
    rate = rates_for(1.0)
    months = YEARS * 12
    r, extra = evaluate(np.random.default_rng(SEED), months, rate, keep_months=True)
    base = summarize(r)
    mb, mbug, mt, mc, events = extra
    # 何が上位1位になったか（件数の順）
    top_counts = pd.Series([CATS[i] for i in r["count_top"]]).value_counts()
    cap_counts = pd.Series([CATS[i] for i in r["capped_top"]]).value_counts()
    base["count_top_categories_pct"] = {k: round(v / len(r) * 100, 2) for k, v in top_counts.items()}
    base["capped_top_categories_pct"] = {k: round(v / len(r) * 100, 2) for k, v in cap_counts.items()}
    sizes = np.array([e[2] for e in events])
    base["bug_size_median"] = float(np.median(sizes)); base["bug_size_p90"] = float(np.quantile(sizes, 0.9))
    base["n_bugs"] = int(len(events))
    base["usual_monthly"] = {c: round(float(x * MONTH), 1) for c, x in zip(CATS, rate)}
    # 不具合の大きさ別：その種類が1位になった割合
    rows_sz = []
    ev = [(m - WARM_M, c, s) for m, c, s in events if m >= WARM_M]
    for m, c, s in ev:
        rows_sz.append({"month": m + 1, "category": CATS[c], "usual_rank": int(np.argsort(np.argsort(-rate))[c]) + 1, "bug_size": s,
                        "count_rank": int(np.argsort(np.argsort(-mt[m], kind="stable"))[c]) + 1,
                        "capped_rank": int(np.argsort(np.argsort(-mc[m], kind="stable"))[c]) + 1})
    bugs = pd.DataFrame(rows_sz)
    bugs.to_csv(DATA / "bugs.csv", index=False)
    bugs["usual_rank_band"] = pd.cut(bugs["usual_rank"], [0, 3, 6, 12], labels=["ふだん1〜3位", "4〜6位", "7〜12位"])
    by_band = bugs.groupby("usual_rank_band", observed=True).agg(n=("bug_size", "size"), count_top1_pct=("count_rank", lambda x: round(float((x == 1).mean()) * 100, 2)),
                                                 count_top3_pct=("count_rank", lambda x: round(float((x <= 3).mean()) * 100, 2)),
                                                 capped_top3_pct=("capped_rank", lambda x: round(float((x <= 3).mean()) * 100, 2))).reset_index()
    by_band.to_csv(RES / "bug_by_usual_rank.csv", index=False)
    base["bug_by_usual_rank"] = by_band.astype({"usual_rank_band": str}).to_dict(orient="records")

    # data：最初の2年分の月ごとの件数（ふだん・不具合）
    md = []
    for m in range(24):
        for i, c in enumerate(CATS):
            md.append({"month": m + 1, "category": c, "usual": int(mb[m, i]), "bug": int(mbug[m, i]), "total": int(mt[m, i]), "capped": round(float(mc[m, i]), 1)})
    pd.DataFrame(md).to_csv(DATA / "monthly_first24.csv", index=False)

    # 27通り
    rows = []
    g = 0
    for p in [0.02, 0.05, 0.15]:
        for med in [40, 120, 360]:
            for steep in [0.5, 1.0, 1.5]:
                g += 1
                rr, _ = evaluate(np.random.default_rng(SEED + 100 + g), YEARS_GRID * 12, rates_for(steep), p, med)
                sm = summarize(rr)
                rows.append({"p_bug": p, "bug_median": med, "steep": steep, "months_with_bug_pct": sm["months_with_bug_pct"],
                             "bug_ticket_share_pct": sm["bug_ticket_share_pct"],
                             **{f"{n}_{k}": sm[n][k] for n in ["count", "capped"] for k in
                                ["top_is_usual_pct", "top_has_bug_pct", "top_bug_share_all_months_pct", "top_half_from_bug_pct", "top3_overlap_pct", "rank_corr_mean"]}})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    gs = {"n_settings": int(len(grid))}
    for c in ["count_top_is_usual_pct", "capped_top_is_usual_pct", "count_top_has_bug_pct", "capped_top_has_bug_pct",
              "count_top_half_from_bug_pct", "capped_top_half_from_bug_pct", "count_top_bug_share_all_months_pct", "capped_top_bug_share_all_months_pct", "count_top3_overlap_pct", "capped_top3_overlap_pct",
              "count_rank_corr_mean", "capped_rank_corr_mean", "bug_ticket_share_pct", "months_with_bug_pct"]:
        gs[c + "_range"] = [float(grid[c].min()), float(grid[c].max())]
    gs["n_capped_top_usual_ge_count"] = int((grid["capped_top_is_usual_pct"] >= grid["count_top_is_usual_pct"]).sum())
    gs["n_capped_top3_ge_count"] = int((grid["capped_top3_overlap_pct"] >= grid["count_top3_overlap_pct"]).sum())
    gs["n_count_top_bugshare_gt_overall"] = int((grid["count_top_bug_share_all_months_pct"] > grid["bug_ticket_share_pct"]).sum())
    gs["n_capped_top_bugshare_lt_overall"] = int((grid["capped_top_bug_share_all_months_pct"] < grid["bug_ticket_share_pct"]).sum())
    gs["count_top_bugshare_ratio_range"] = [round(float((grid["count_top_bug_share_all_months_pct"] / grid["bug_ticket_share_pct"]).min()), 3),
                                            round(float((grid["count_top_bug_share_all_months_pct"] / grid["bug_ticket_share_pct"]).max()), 3)]

    out = {"settings": {"categories": CATS, "usual_daily": rate.tolist(), "month_days": MONTH, "years": YEARS, "warm_months": WARM_M,
                        "p_bug": P_BUG, "bug_median": BUG_MED, "bug_sd": BUG_SD, "spread": SPREAD, "cap_k": CAP_K, "cap_window": CAP_WIN,
                        "years_grid": YEARS_GRID, "grid_p_bug": [0.02, 0.05, 0.15], "grid_bug_median": [40, 120, 360], "grid_steep": [0.5, 1.0, 1.5], "seed": SEED},
           "base": base, "grid_summary": gs}
    with open(RES / "a1193_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：2年分の月ごとの1位の種類と、その中の不具合の分
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    m24 = np.arange(24)
    top = mt[:24].argmax(1)
    usual_part = mb[np.arange(24), top]; bug_part = mbug[np.arange(24), top]
    ax.bar(m24 + 1, usual_part, color=BLUE, label="ふだんの困りごと")
    ax.bar(m24 + 1, bug_part, bottom=usual_part, color=ORANGE, label="1つの不具合から来た分")
    for x, t, h in zip(m24 + 1, top, usual_part + bug_part):
        ax.text(x, h + 6, CATS[t], rotation=90, ha="center", va="bottom", fontsize=7.5)
    ax.set_ylim(0, (usual_part + bug_part).max() * 1.35)
    ax.set_xlabel("月（初めの2年分）"); ax.set_ylabel("1位の種類の件数")
    ax.set_xticks(range(1, 25, 2))
    ax.set_title("件数で1位の種類と、その中身（文字は1位の種類）", fontsize=12)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1193_monthly_top.png", SRC)

    # 図2：ふだんの順位ごとの、不具合が起きた月の順位
    fig, ax = plt.subplots(figsize=(8, 4.2))
    xs = np.arange(len(by_band)); w = 0.27
    for i, (col, lab, c) in enumerate([("count_top1_pct", "①件数で1位", ORANGE), ("count_top3_pct", "①件数で3位以内", BLUE), ("capped_top3_pct", "②固まった日をならして3位以内", GREEN)]):
        v = by_band[col].values
        ax.bar(xs + (i - 1) * w, v, w, color=c, label=lab)
        for x, vv in zip(xs + (i - 1) * w, v):
            ax.text(x, vv + 1.5, f"{vv:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(xs); ax.set_xticklabels([f"{b}\n（不具合{n}回）" for b, n in zip(by_band["usual_rank_band"], by_band["n"])])
    ax.set_ylim(0, 110); ax.set_ylabel("不具合が起きた月のうち（%）")
    ax.set_title("不具合が起きた種類は、ふだんの順位が低くても上位に入る", fontsize=12)
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a1193_jump.png", SRC)

    # 図3：27通り
    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.scatter(grid["bug_ticket_share_pct"], grid["count_top_bug_share_all_months_pct"], color=ORANGE, s=22, label="①件数で1位の種類")
    ax.scatter(grid["bug_ticket_share_pct"], grid["capped_top_bug_share_all_months_pct"], color=GREEN, s=22, marker="x", label="②固まった日をならして1位の種類")
    mx = max(grid["count_top_bug_share_all_months_pct"].max(), grid["bug_ticket_share_pct"].max()) * 1.05
    ax.plot([0, mx], [0, mx], color=GRAY, lw=0.8)
    ax.set_xlim(0, None); ax.set_ylim(0, None)
    ax.set_xlabel("全部の問い合わせのうち、不具合から来た分（%）")
    ax.set_ylabel("1位の種類のうち不具合の分（%、月の平均）")
    ax.set_title("置き方27通り：灰色の線より上なら、不具合の分は1位に偏って入る", fontsize=11.5)
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a1193_robust.png", SRC)
    print(json.dumps(base, ensure_ascii=False))
    print(json.dumps(gs, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
