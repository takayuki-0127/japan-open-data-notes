"""462 2つの期間が重なるかどうかの条件を書き間違えると、何件が漏れ、何件が余分に入るのか（架空の契約とキャンペーン、seed 462）"""
import json
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, BLUE, ORANGE, GRAY, LIGHT, GREEN, save

SRC = "架空の契約期間とキャンペーン期間（作成者が乱数で作成、seed 462）"
D0 = pd.Timestamp("2024-01-01")

# 条件の書き方。c＝契約、k＝キャンペーン。期間は両端を含む（終了日もその期間の中）
COND = {
    "正しい": "c.start_date <= k.end_date AND COALESCE(c.end_date, DATE '9999-12-31') >= k.start_date",
    "①開始日が期間の中": "c.start_date BETWEEN k.start_date AND k.end_date",
    "②開始日か終了日が期間の中": "(c.start_date BETWEEN k.start_date AND k.end_date) OR (COALESCE(c.end_date, DATE '9999-12-31') BETWEEN k.start_date AND k.end_date)",
    "③端を含めない（< と >）": "c.start_date < k.end_date AND COALESCE(c.end_date, DATE '9999-12-31') > k.start_date",
    "④終了日の空を考えない": "c.start_date <= k.end_date AND c.end_date >= k.start_date",
    "⑤AND を OR にする": "c.start_date <= k.end_date OR COALESCE(c.end_date, DATE '9999-12-31') >= k.start_date",
    "⑥開始の時点で有効かだけ見る": "c.start_date <= k.start_date AND COALESCE(c.end_date, DATE '9999-12-31') >= k.start_date",
}
WRONG = [k for k in COND if k != "正しい"]


def make(seed=462, n=20000):
    rng = np.random.default_rng(seed)
    start = rng.integers(0, 730, n)                                # 2024-01-01〜2025-12-30 のどこかで始まる
    kind = rng.choice(["1年", "1か月", "1日", "ばらばら", "続行中"], n, p=[0.45, 0.15, 0.05, 0.27, 0.08])
    length = np.select([kind == "1年", kind == "1か月", kind == "1日", kind == "ばらばら"],
                       [364, 29, 0, rng.integers(1, 500, n)], 0)
    # 月初に始まる契約を多めにする（端が同じ日の組が出やすくなる）
    snap = rng.random(n) < 0.35
    sd = D0 + pd.to_timedelta(start, unit="D")
    sd = pd.DatetimeIndex(np.where(snap, sd.to_period("M").to_timestamp(), sd))
    ed = sd + pd.to_timedelta(length, unit="D")
    c = pd.DataFrame({"contract_id": np.arange(1, n + 1), "start_date": sd.date, "end_date": ed.date, "kind": kind})
    c.loc[c.kind == "続行中", "end_date"] = None
    # キャンペーン：12本。月初〜月末、1日だけ、数日、四半期などを混ぜる
    ks = [("2024-04-01", "2024-04-30"), ("2024-07-01", "2024-07-01"), ("2024-08-10", "2024-08-18"),
          ("2024-10-01", "2024-12-31"), ("2025-01-01", "2025-01-31"), ("2025-03-15", "2025-04-14"),
          ("2025-05-01", "2025-05-01"), ("2025-06-01", "2025-06-30"), ("2025-08-01", "2025-08-31"),
          ("2025-10-01", "2025-10-07"), ("2025-11-01", "2025-12-31"), ("2026-01-01", "2026-03-31")]
    k = pd.DataFrame({"campaign_id": range(1, 13), "start_date": [pd.Timestamp(a).date() for a, _ in ks],
                      "end_date": [pd.Timestamp(b).date() for _, b in ks]})
    return c, k


SHAPE_SQL = """
CASE
  WHEN c.end_date IS NULL AND c.start_date <= k.end_date THEN '終了日が空（続行中）で重なる'
  WHEN c.end_date IS NULL THEN '終了日が空で、あとから始まる'
  WHEN c.end_date < k.start_date THEN '重ならない（前に終わる）'
  WHEN c.start_date > k.end_date THEN '重ならない（あとに始まる）'
  WHEN c.end_date = k.start_date AND c.start_date < k.start_date THEN '端が同じ日（契約の終了＝開始）'
  WHEN c.start_date = k.end_date AND c.end_date > k.end_date THEN '端が同じ日（契約の開始＝終了）'
  WHEN c.start_date < k.start_date AND c.end_date > k.end_date THEN '契約がキャンペーンをすっぽり含む'
  WHEN c.start_date >= k.start_date AND c.end_date <= k.end_date THEN '契約がキャンペーンの中に入る'
  WHEN c.start_date < k.start_date THEN '前からまたぐ'
  ELSE 'あとへまたぐ'
END"""


def main():
    res = {}
    c, k = make()
    DATA.mkdir(exist_ok=True)
    c.to_csv(DATA / "contracts.csv", index=False); k.to_csv(DATA / "campaigns.csv", index=False)
    con = duckdb.connect()
    con.execute("CREATE TABLE c AS SELECT contract_id, CAST(start_date AS DATE) start_date, CAST(end_date AS DATE) end_date, kind FROM read_csv_auto(?, nullstr='')", [str(DATA / "contracts.csv")])
    con.execute("CREATE TABLE k AS SELECT campaign_id, CAST(start_date AS DATE) start_date, CAST(end_date AS DATE) end_date FROM read_csv_auto(?)", [str(DATA / "campaigns.csv")])
    cols = ", ".join(f"COALESCE(({v}), FALSE) AS \"{n}\"" for n, v in COND.items())
    pairs = con.execute(f"SELECT c.contract_id, k.campaign_id, {SHAPE_SQL} AS shape, {cols} FROM c CROSS JOIN k").df()

    # pandas で正解を別に出して、SQL の「正しい」と一致することを確かめる（1日ずつ数える方法ではなく、両端の比べ）
    cc = c.assign(key=1).merge(k.assign(key=1), on="key", suffixes=("_c", "_k"))
    end_c = pd.to_datetime(cc.end_date_c).fillna(pd.Timestamp("2262-01-01"))
    truth = (pd.to_datetime(cc.start_date_c) <= pd.to_datetime(cc.end_date_k)) & (end_c >= pd.to_datetime(cc.start_date_k))
    assert int(truth.sum()) == int(pairs["正しい"].sum())
    # さらに、契約500件については、日を1日ずつ並べて「同じ日が1日でもあるか」で確かめる
    sub = cc[cc.contract_id <= 500]
    def brute(r):
        e = r.end_date_c if r.end_date_c is not None and not pd.isna(r.end_date_c) else pd.Timestamp("2027-12-31").date()
        a = set(pd.date_range(r.start_date_c, e).date); b = set(pd.date_range(r.start_date_k, r.end_date_k).date)
        return len(a & b) > 0
    bt = sub.apply(brute, axis=1).to_numpy()
    ps = pairs[pairs.contract_id <= 500].sort_values(["contract_id", "campaign_id"])["正しい"].to_numpy()
    assert (bt == ps).all()

    n_pairs, n_true = len(pairs), int(pairs["正しい"].sum())
    res["pairs"] = {"組の数": n_pairs, "本当に重なる組": n_true, "契約": len(c), "キャンペーン": len(k),
                    "終了日が空の契約": int(c.end_date.isna().sum())}
    rows = []
    for w in WRONG:
        miss = int((pairs["正しい"] & ~pairs[w]).sum()); extra = int((~pairs["正しい"] & pairs[w]).sum())
        rows.append({"書き方": w, "漏れ": miss, "余分": extra, "漏れ%（重なる組に対して）": miss / n_true * 100,
                     "余分%（重なる組に対して）": extra / n_true * 100, "返した組": int(pairs[w].sum())})
    summ = pd.DataFrame(rows); summ.to_csv(RES / "miss_extra_by_condition.csv", index=False)
    res["by_condition"] = {r["書き方"]: {"漏れ": r["漏れ"], "余分": r["余分"], "漏れ%": round(r["漏れ%（重なる組に対して）"], 1),
                                       "余分%": round(r["余分%（重なる組に対して）"], 1)} for _, r in summ.iterrows()}

    # 形ごと：どの形の組で外れるか
    shp = pairs.groupby("shape").agg(組=("正しい", "size"), 重なる=("正しい", "sum")).reset_index()
    for w in WRONG:
        shp[w] = pairs.assign(bad=pairs[w] != pairs["正しい"]).groupby("shape").bad.mean().reindex(shp["shape"]).to_numpy() * 100
    shp = shp.sort_values("組", ascending=False); shp.to_csv(RES / "wrong_share_by_shape.csv", index=False)
    res["shapes"] = {r["shape"]: int(r["組"]) for _, r in shp.iterrows()}

    # キャンペーンごとの件数（契約の数）への影響：いちばんずれたキャンペーン
    per = pairs.groupby("campaign_id")[["正しい"] + WRONG].sum()
    dev = (per[WRONG].div(per["正しい"], axis=0) - 1) * 100
    dev.insert(0, "正しい件数", per["正しい"]); dev.to_csv(RES / "count_by_campaign.csv")
    res["by_campaign_dev%"] = {w: {"最小": round(float(dev[w].min()), 1), "最大": round(float(dev[w].max()), 1)} for w in WRONG}
    one_day = per.loc[[2, 7]]                                         # 1日だけのキャンペーン
    res["one_day_campaigns"] = {w: [int(one_day.loc[2, w]), int(one_day.loc[7, w])] for w in ["正しい"] + WRONG}

    # ---- テストで見つかるか ----
    # (a) 端の値だけを並べた手作りの12組　(b) 本番の組からくじで N 組
    hand = [  # (契約の開始, 終了 or None, キャンペーンの開始, 終了, 重なるか)
        ("2025-01-01", "2025-01-31", "2025-02-01", "2025-02-28", False),   # 前に終わる（1日あく）
        ("2025-03-01", "2025-03-31", "2025-02-01", "2025-02-28", False),   # あとに始まる
        ("2025-01-10", "2025-02-01", "2025-02-01", "2025-02-28", True),    # 契約の終了＝開始
        ("2025-02-28", "2025-03-20", "2025-02-01", "2025-02-28", True),    # 契約の開始＝終了
        ("2025-01-10", "2025-03-20", "2025-02-01", "2025-02-28", True),    # すっぽり含む
        ("2025-02-05", "2025-02-10", "2025-02-01", "2025-02-28", True),    # 中に入る
        ("2025-01-20", "2025-02-10", "2025-02-01", "2025-02-28", True),    # 前からまたぐ
        ("2025-02-20", "2025-03-10", "2025-02-01", "2025-02-28", True),    # あとへまたぐ
        ("2025-01-10", None, "2025-02-01", "2025-02-28", True),            # 終了日が空で重なる
        ("2025-03-05", None, "2025-02-01", "2025-02-28", False),           # 終了日が空で、あとから始まる
        ("2025-02-01", "2025-02-28", "2025-02-01", "2025-02-28", True),    # ぴったり同じ
        ("2025-02-10", "2025-02-10", "2025-02-10", "2025-02-10", True),    # 1日どうし
    ]
    h = pd.DataFrame(hand, columns=["cs", "ce", "ks", "ke", "truth"])
    con.register("h", h)
    def hand_eval(cond):
        s = cond.replace("c.start_date", "CAST(cs AS DATE)").replace("c.end_date", "CAST(ce AS DATE)") \
                .replace("k.start_date", "CAST(ks AS DATE)").replace("k.end_date", "CAST(ke AS DATE)")
        return con.execute(f"SELECT COALESCE(({s}), FALSE) FROM h").df().iloc[:, 0].to_numpy()
    assert (hand_eval(COND["正しい"]) == h.truth.to_numpy()).all()
    rng = np.random.default_rng(462)
    tests = []
    for w in WRONG:
        hv = hand_eval(COND[w]); nh = int((hv != h.truth.to_numpy()).sum())
        bad = (pairs[w] != pairs["正しい"]).to_numpy(); p = bad.mean()
        row = {"書き方": w, "手作り12組で外れた組": nh, "手作りで見つかる": nh > 0, "本番の組で外れる割合%": p * 100}
        for m in [20, 100, 1000]:
            hit = np.mean([bad[rng.choice(n_pairs, m, replace=False)].any() for _ in range(2000)])
            row[f"くじ{m}組で見つかる割合%"] = hit * 100
        tests.append(row)
    tests = pd.DataFrame(tests); tests.to_csv(RES / "tests_detection.csv", index=False)
    res["tests"] = {r["書き方"]: {"手作りで外れた組": int(r["手作り12組で外れた組"]), "くじ20": round(r["くじ20組で見つかる割合%"], 1),
                                "くじ100": round(r["くじ100組で見つかる割合%"], 1), "くじ1000": round(r["くじ1000組で見つかる割合%"], 1)}
                    for _, r in tests.iterrows()}
    # 件数だけの照合（返した組の数が正しい数と1%以内）で通ってしまう書き方
    res["count_within_1pct"] = {w: bool(abs(int(pairs[w].sum()) / n_true - 1) < 0.01) for w in WRONG}
    json.dump(res, open(RES / "a462_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(9, 4.3))
    y = np.arange(len(summ))[::-1]
    ax.barh(y + 0.2, summ["漏れ%（重なる組に対して）"], 0.38, color=BLUE, label="漏れ（重なるのに返さない）")
    ax.barh(y - 0.2, summ["余分%（重なる組に対して）"], 0.38, color=ORANGE, label="余分（重ならないのに返す）")
    for yy, m, e, mn, en in zip(y, summ["漏れ%（重なる組に対して）"], summ["余分%（重なる組に対して）"], summ["漏れ"], summ["余分"]):
        ax.text(m + 1, yy + 0.2, f"{m:.1f}%（{mn:,}組）", va="center", fontsize=8.5)
        ax.text(e + 1, yy - 0.2, f"{e:.1f}%（{en:,}組）" if en else "0", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(summ["書き方"])
    ax.set_xlabel(f"本当に重なる {n_true:,} 組に対する割合（%）"); ax.set_title("条件の書き方ごとの、漏れと余分")
    ax.set_xlim(0, max(summ["漏れ%（重なる組に対して）"].max(), summ["余分%（重なる組に対して）"].max()) * 1.3)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    save(fig, "a462_miss_extra.png", SRC)

    fig, ax = plt.subplots(figsize=(10, 4.6))
    M = shp[WRONG].to_numpy()
    im = ax.imshow(M, cmap="Oranges", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(WRONG))); ax.set_xticklabels(["①開始日が\n期間の中", "②開始日か終了日が\n期間の中", "③端を含めない\n（< と >）", "④終了日の空を\n考えない", "⑤AND を\nOR にする", "⑥開始の時点で\n有効かだけ見る"], fontsize=8)
    ax.set_yticks(range(len(shp))); ax.set_yticklabels([f"{s}（{n:,}組）" for s, n in zip(shp["shape"], shp["組"])], fontsize=8.5)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=9, color="white" if M[i, j] > 60 else "black")
    ax.spines[:].set_visible(False)
    ax.set_title("2つの期間の並び方ごとに、答えを誤った組の割合（%）")
    save(fig, "a462_by_shape.png", SRC)

    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = np.arange(len(tests)); wd = 0.2
    ax.bar(x - 1.5 * wd, tests["手作りで見つかる"] * 100, wd, color=GREEN, label="端の値を並べた手作りの12組")
    for i, m in enumerate([20, 100, 1000]):
        ax.bar(x + (i - 0.5) * wd, tests[f"くじ{m}組で見つかる割合%"], wd, color=[LIGHT, BLUE, "#1b4f91"][i], label=f"本番の組からくじで{m:,}組")
    SHORT = ["①開始日が\n期間の中", "②開始日か終了日が\n期間の中", "③端を含めない\n（< と >）", "④終了日の空を\n考えない", "⑤AND を\nOR にする", "⑥開始の時点で\n有効かだけ見る"]
    ax.set_xticks(x); ax.set_xticklabels(SHORT, fontsize=8.5)
    ax.set_ylabel("書き間違いが見つかる割合（%）"); ax.set_ylim(0, 135)
    ax.set_title("どのテストで、書き間違いが見つかるか"); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center")
    save(fig, "a462_tests.png", SRC)


if __name__ == "__main__":
    main()
