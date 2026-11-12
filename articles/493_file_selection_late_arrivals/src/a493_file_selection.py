"""493 ファイル名の日付で取り込み対象を選ぶと、遅れて置かれたファイルを何件落とすのか（実務の型）

架空の日次ファイル（1年分）を、毎朝の取り込みで「どれを読むか」の選び方5通りで処理し、
年末に、落としたファイル・行、二重に入った行、合計金額のずれを数える。
置き方：ファイル名は売上日（sales_YYYYMMDD.csv）。ふつうは翌日2時に置かれる。一部は遅れて置かれ、
一部は数日後に直した版が同じ名前で置き直される。取り込みは毎朝6時。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 493
DAYS = pd.date_range("2025-01-01", "2025-12-31")
RUN_HOUR = 6


def make_files(rng, p_late=0.08, p_replace=0.03):
    """各ファイルの版（置いた時刻・行数・金額）を作る"""
    vers = []
    for d in DAYS:
        n = int(rng.integers(800, 1200))
        amt = float(rng.gamma(4, 2500, n).sum())
        put = d + pd.Timedelta(days=1, hours=2)
        late = rng.random() < p_late
        if late:                                        # 1〜5日遅れて、昼間のどこかで置かれる
            put = d + pd.Timedelta(days=int(rng.integers(1, 6)), hours=int(rng.integers(7, 23)))
        prev_rows = int(round(n * 0.01))                # 1%は前日の売上（締めた後に入った行）
        vers.append({"file": f"sales_{d:%Y%m%d}.csv", "day": d, "ver": 1, "put": put, "rows": n, "amount": amt,
                     "prev_rows": prev_rows, "late": late})
        if rng.random() < p_replace:                    # 1〜3日後に、直した版を同じ名前で置き直す
            n2 = n + int(rng.integers(5, 40)); amt2 = amt * (1 + rng.uniform(0.005, 0.03))
            vers.append({"file": f"sales_{d:%Y%m%d}.csv", "day": d, "ver": 2,
                         "put": put + pd.Timedelta(days=int(rng.integers(1, 4)), hours=int(rng.integers(1, 10))),
                         "rows": n2, "amount": amt2, "prev_rows": int(round(n2 * 0.01)), "late": late})
    return pd.DataFrame(vers)


def run(V: pd.DataFrame, method: str):
    """毎朝の取り込みを年末（＋12日）まで回したとき、表に入った（ファイル, 版）の並び。
    取り込みは毎朝6時。各版は、置かれた後の最初の取り込みで見えるようになる。"""
    loaded = {}
    first_run = (V.put - pd.Timedelta(hours=RUN_HOUR)).dt.ceil("D") + pd.Timedelta(hours=RUN_HOUR)   # 最初に見える取り込み
    end = DAYS[-1] + pd.Timedelta(days=12, hours=RUN_HOUR)
    assert (first_run <= end).all()
    for f, g in V.assign(first_run=first_run).sort_values(["file", "ver"]).groupby("file", sort=False):
        d = g.day.iloc[0]
        if method == "A_name_yesterday":            # ① 売上日の翌朝の取り込みで、名前が「昨日」のものだけ
            r = d + pd.Timedelta(days=1, hours=RUN_HOUR)
            ok = g[g.put <= r]
            if len(ok): loaded[f] = [int(ok.ver.iloc[-1])]
        elif method == "B_mtime_append":            # ② 前回の取り込みより後に置かれたもの（追記）→ 版ごとに1回ずつ入る
            loaded[f] = [int(v) for v in g.ver]
        elif method == "B2_mtime_replace":          # ③ 同上、ただし同じ名前は前の分を消して入れ直す
            loaded[f] = [int(g.ver.iloc[-1])]
        elif method == "C_manifest_name":           # ④ 取り込み済みの名前の一覧にないもの → 最初の版だけ
            loaded[f] = [int(g.ver.iloc[0])]
        elif method == "C2_manifest_name_ver":      # ⑤ 名前と中身（版）の一覧にないもの、同じ名前は入れ直す
            loaded[f] = [int(g.ver.iloc[-1])]
    return loaded


def score(V, loaded):
    final = V.sort_values("ver").drop_duplicates("file", keep="last").set_index("file")
    key = V.set_index(["file", "ver"])
    rows = amt = 0; miss_files = 0; miss_rows = 0; dup_rows = 0; stale_files = 0
    for f, fin in final.iterrows():
        vs = loaded.get(f, [])
        if not vs:
            miss_files += 1; miss_rows += fin.rows; continue
        for v in vs:
            rows += key.loc[(f, v)].rows; amt += key.loc[(f, v)].amount
        if len(vs) > 1: dup_rows += sum(key.loc[(f, v)].rows for v in vs[:-1])
        if vs[-1] != fin.ver or len(vs) > 1 and False: pass
        if fin.ver not in vs: stale_files += 1
    true_rows = int(final.rows.sum()); true_amt = float(final.amount.sum())
    return {"files_total": len(final), "files_missed": miss_files, "rows_missed": int(miss_rows), "files_stale_version": stale_files,
            "rows_duplicated": int(dup_rows), "rows_loaded": int(rows), "rows_true": true_rows,
            "amount_error_pct": (amt / true_amt - 1) * 100}


METHODS = {"A_name_yesterday": "①ファイル名が\n「昨日」のもの", "B_mtime_append": "②前回より後に\n置かれたもの（追記）",
           "B2_mtime_replace": "③②＋同じ名前は\n入れ直す", "C_manifest_name": "④取り込み済みの\n名前の一覧にないもの",
           "C2_manifest_name_ver": "⑤名前と版の一覧に\nないもの＋入れ直す"}


def main():
    rng = np.random.default_rng(SEED)
    V = make_files(rng)
    V.to_csv(DATA / "fictional_file_arrivals.csv", index=False)
    res = {"files": int(V.file.nunique()), "late_files": int(V[V.ver == 1].late.sum()),
           "replaced_files": int((V.ver == 2).sum()), "methods": {}}
    for m in METHODS:
        res["methods"][m] = score(V, run(V, m))
    # 「昨日」方式で、中身の日付も見る（前日の行1%は前日の取り込みに入らない）
    a = res["methods"]["A_name_yesterday"]
    res["prev_day_rows_share"] = float(V[V.ver == 1].prev_rows.sum() / V[V.ver == 1].rows.sum())

    # 遅れの割合を変える（各20回）
    sweep = []
    for p in [0.0, 0.02, 0.05, 0.08, 0.15, 0.25]:
        for rep in range(20):
            r2 = np.random.default_rng(SEED * 1000 + int(p * 100) * 50 + rep)
            V2 = make_files(r2, p_late=p)
            for m in ["A_name_yesterday", "C_manifest_name", "C2_manifest_name_ver"]:
                s = score(V2, run(V2, m))
                sweep.append({"p_late": p, "rep": rep, "method": m, "files_missed": s["files_missed"],
                              "stale": s["files_stale_version"], "amount_error_pct": s["amount_error_pct"]})
    sw = pd.DataFrame(sweep)
    sw.to_csv(RES / "sweep_late_share.csv", index=False)
    swm = sw.groupby(["p_late", "method"]).mean(numeric_only=True).reset_index()
    res["sweep_mean"] = swm.to_dict(orient="records")
    tab = pd.DataFrame(res["methods"]).T
    tab.to_csv(RES / "methods.csv")
    json.dump(res, open(RES / "a493_main.json", "w"), ensure_ascii=False, indent=1, default=float)

    # 図1：方法ごとの、落としたファイル・古い版のまま・二重に入った行
    fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.2), sharey=True)
    y = np.arange(len(METHODS))[::-1]
    for ax, col, ttl, c in [(axs[0], "files_missed", "落としたファイル", ORANGE),
                            (axs[1], "files_stale_version", "直した版を入れていないファイル", GREEN),
                            (axs[2], "rows_duplicated", "二重に入った行", BLUE)]:
        v = tab.loc[list(METHODS), col].astype(float).values
        ax.barh(y, v, color=c)
        for yy, vv in zip(y, v): ax.text(vv + max(v.max(), 1) * 0.02, yy, f"{int(vv):,}", va="center", fontsize=9.5)
        ax.set_title(ttl, fontsize=11); ax.set_xlim(0, max(v.max(), 1) * 1.3)
    axs[0].set_yticks(y, list(METHODS.values()), fontsize=9)
    fig.suptitle(f"365日分のファイル（うち遅れて置かれた{res['late_files']}件、置き直し{res['replaced_files']}件）を、5通りの選び方で取り込むと", fontsize=12, y=1.05)
    save(fig, "a493_methods.png", "架空の日次ファイル（seed 493）で作成。取り込みは毎朝6時、ファイルは翌日2時に置かれるのがふつう")

    # 図2：合計金額のずれ
    fig, ax = plt.subplots(figsize=(8.4, 3.9))
    v = tab.loc[list(METHODS), "amount_error_pct"].astype(float).values
    ax.barh(y, v, color=[ORANGE if x < 0 else BLUE for x in v])
    for yy, vv in zip(y, v): ax.text(vv + (0.15 if vv >= 0 else -0.15), yy, f"{vv:+.2f}%", va="center", ha="left" if vv >= 0 else "right", fontsize=10)
    ax.axvline(0, color=INK, lw=0.8); ax.set_yticks(y, list(METHODS.values()), fontsize=9)
    ax.set_xlim(min(v.min() * 1.5, -1), max(v.max() * 1.5, 1)); ax.set_xlabel("1年の売上合計のずれ（%）")
    ax.set_title("取り込んだ表の、1年の合計金額は正しい値から何%ずれたか")
    save(fig, "a493_amount.png", "架空の日次ファイル（seed 493）で作成")

    # 図3：遅れの割合を変えたとき
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    for m, c, mk in [("A_name_yesterday", ORANGE, "o-"), ("C_manifest_name", GREEN, "s--"), ("C2_manifest_name_ver", BLUE, "^-")]:
        d = swm[swm.method == m]
        ax.plot(d.p_late * 100, d.files_missed + d.stale, mk, color=c, label=METHODS[m].replace("\n", ""))
    ax.set_xlabel("遅れて置かれるファイルの割合（%）"); ax.set_ylabel("落とした＋古い版のままのファイル（件/年）")
    ax.legend(fontsize=9, frameon=False); ax.set_title("遅れが増えると、名前で選ぶ方法の取りこぼしは比例して増える")
    save(fig, "a493_sweep.png", "架空の日次ファイル（seed 493〜、各20回の平均）で作成。置き直しは3%で固定")
    print(json.dumps({k: v for k, v in res.items() if k not in ("sweep_mean",)}, ensure_ascii=False, indent=0, default=float))
    print(swm.round(2).to_string())


if __name__ == "__main__":
    main()
