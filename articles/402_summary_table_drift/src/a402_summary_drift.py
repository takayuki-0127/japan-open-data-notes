"""402 速くするために作った集計済みの表は、元の表とどれくらいずれていくのか
架空の売上（あとから遅れて届く行・金額の訂正・行の削除がある）で、日別の集計済みの表を6通りの更新の仕方で1年間保ち、
元の表とのずれと、照合クエリが気づくまでの日数を数える。
更新と照合の SQL は sql_update_and_check.sql（T-SQL。SQL Server では未検証）。同じ集計を DuckDB でも確かめる。"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 402
SRC = "架空のデータ（作成者が乱数で作成、seed 402）"
ND, TAIL = 365, 120            # 売上の日は2025年の365日。取り込みはその後120日も続ける
PER_DAY = 400
P_LATE, P_UPD, P_DEL = 0.06, 0.03, 0.01


def lag(rng, n):
    """遅れの日数：70%は1〜3日、25%は4〜30日、5%は31〜90日"""
    u = rng.random(n)
    return np.where(u < .70, rng.integers(1, 4, n), np.where(u < .95, rng.integers(4, 31, n), rng.integers(31, 91, n)))


def make(seed=SEED, p_late=P_LATE, p_upd=P_UPD, p_del=P_DEL):
    rng = np.random.default_rng(seed)
    n = ND * PER_DAY
    sale = np.repeat(np.arange(ND), PER_DAY)
    amt0 = np.round(rng.lognormal(8.0, 0.7, n), -1).astype(np.int64)
    created = sale + np.where(rng.random(n) < p_late, lag(rng, n), 0)
    is_upd = rng.random(n) < p_upd
    upd = np.where(is_upd, created + lag(rng, n), 10**6)
    amt1 = np.where(is_upd, np.round(amt0 * rng.uniform(0.5, 1.5, n), -1).astype(np.int64), amt0)
    is_del = (rng.random(n) < p_del) & ~is_upd
    dele = np.where(is_del, created + lag(rng, n), 10**6)
    return pd.DataFrame(dict(sale=sale, amt0=amt0, created=created, upd=upd, amt1=amt1, dele=dele))


METHODS = ["A 当日分だけ足す", "B 直近7日を作り直す", "B' 直近35日を作り直す", "C 更新日時で変わった日を作り直す",
           "C' 更新日時＋削除の記録", "D 毎晩ぜんぶ作り直す"]
CHECKS = ["K1 取り込んだ当日分の合計", "K2 直近7日を日ごと", "K3 今月の合計（0.1%まで許す）", "K4 全期間の合計（0.1%まで許す）", "K5 全期間を日ごと"]


def simulate(df):
    T = ND + TAIL
    ev_ins = [[] for _ in range(T + 1)]; ev_upd = [[] for _ in range(T + 1)]; ev_del = [[] for _ in range(T + 1)]
    s, a0, a1 = df.sale.values, df.amt0.values, df.amt1.values
    for i, c in enumerate(df.created.values): ev_ins[c].append(i)
    for i in np.where(df.upd.values < 10**6)[0]:
        if df.upd.values[i] <= T: ev_upd[df.upd.values[i]].append(i)
    for i in np.where(df.dele.values < 10**6)[0]:
        if df.dele.values[i] <= T: ev_del[df.dele.values[i]].append(i)
    true = np.zeros(ND, dtype=np.int64)
    summ = {m: np.zeros(ND, dtype=np.int64) for m in METHODS}
    scanned = {m: 0 for m in METHODS}
    live = 0
    month = pd.date_range("2025-01-01", periods=ND).month.values
    gap_ts = {m: [] for m in METHODS}; bad_ts = {m: [] for m in METHODS}
    first_bad = {m: None for m in METHODS}; first_alarm = {m: {k: None for k in CHECKS} for m in METHODS}
    silent = {m: {k: 0 for k in CHECKS} for m in METHODS}; bad_nights = {m: 0 for m in METHODS}
    rows_per_day = np.zeros(ND, dtype=np.int64)
    for t in range(T):
        ins, up, de = np.array(ev_ins[t], dtype=int), np.array(ev_upd[t], dtype=int), np.array(ev_del[t], dtype=int)
        np.add.at(true, s[ins], a0[ins]); np.add.at(rows_per_day, s[ins], 1)
        np.add.at(true, s[up], a1[up] - a0[up])
        np.subtract.at(true, s[de], a0[de]); np.subtract.at(rows_per_day, s[de], 1)
        hi = min(t, ND - 1)
        for m in METHODS:
            if m.startswith("A"):
                dates = np.array([t]) if t < ND else np.array([], dtype=int)
            elif m.startswith("B 直近7日"):
                dates = np.arange(max(0, t - 6), hi + 1)
            elif m.startswith("B'"):
                dates = np.arange(max(0, t - 34), hi + 1)
            elif m.startswith("C 更新"):
                dates = np.unique(np.concatenate([s[ins], s[up]]))          # 消えた行は元の表に残らないので拾えない
            elif m.startswith("C'"):
                dates = np.unique(np.concatenate([s[ins], s[up], s[de]]))
            else:
                dates = np.arange(0, hi + 1)
            summ[m][dates] = true[dates]
            scanned[m] += int(rows_per_day[dates].sum())
            bad = summ[m][:hi + 1] != true[:hi + 1]
            tot_t, tot_s = true[:hi + 1].sum(), summ[m][:hi + 1].sum()
            gap_ts[m].append((tot_s - tot_t) / tot_t); bad_ts[m].append(bad.mean())
            if bad.any():
                bad_nights[m] += 1
                if first_bad[m] is None: first_bad[m] = t
                al = {}
                al[CHECKS[0]] = (t < ND) and bad[t] if t < ND else False
                al[CHECKS[1]] = bad[max(0, t - 6):hi + 1].any()
                mm = month[hi] if t < ND else 12
                idx = (month[:hi + 1] == mm) if t < ND else np.zeros(hi + 1, dtype=bool)
                al[CHECKS[2]] = bool(idx.any() and abs(summ[m][:hi + 1][idx].sum() - true[:hi + 1][idx].sum()) / true[:hi + 1][idx].sum() > 0.001)
                al[CHECKS[3]] = abs(tot_s - tot_t) / tot_t > 0.001
                al[CHECKS[4]] = True
                for k in CHECKS:
                    if al[k] and first_alarm[m][k] is None: first_alarm[m][k] = t
                    if not al[k]: silent[m][k] += 1
    return dict(true=true, summ=summ, scanned=scanned, gap_ts=gap_ts, bad_ts=bad_ts, first_bad=first_bad,
                first_alarm=first_alarm, silent=silent, bad_nights=bad_nights, T=T)


df = make()
df.sample(5000, random_state=SEED).sort_index().to_csv(DATA / "sales_events_sample5000.csv", index=False)
R = simulate(df)
true = R["true"]
res = []
for m in METHODS:
    s = R["summ"][m]; bad = s != true
    res.append({"更新の仕方": m, "ずれた日の割合": bad.mean(), "ずれた日数": int(bad.sum()),
                "金額のずれ（絶対値の合計÷売上）": np.abs(s - true).sum() / true.sum(),
                "金額のずれ（差し引き）": (s.sum() - true.sum()) / true.sum(),
                "1日のずれの最大": (np.abs(s - true) / true).max(),
                "読んだ行（Dを1とした比）": R["scanned"][m] / R["scanned"][METHODS[-1]],
                "ずれが出た最初の晩（日目）": R["first_bad"][m]})
res = pd.DataFrame(res); res.to_csv(RES / "methods_final.csv", index=False)

det = []
for m in METHODS[:4]:
    for k in CHECKS:
        fa = R["first_alarm"][m][k]
        det.append({"更新の仕方": m, "照合": k, "気づくまでの日数": None if fa is None else fa - R["first_bad"][m],
                    "ずれがあるのに鳴らなかった晩の割合": R["silent"][m][k] / max(1, R["bad_nights"][m])})
det = pd.DataFrame(det); det.to_csv(RES / "detection.csv", index=False)

ts = pd.DataFrame({"日目": np.arange(R["T"])})
for m in METHODS: ts[m + "_金額の差"] = R["gap_ts"][m]; ts[m + "_ずれた日の割合"] = R["bad_ts"][m]
ts.to_csv(RES / "drift_timeseries.csv", index=False)

# 遅れや訂正の多さを変える
sens = []
for name, kw in [("基本（遅れ6%・訂正3%・削除1%）", {}), ("遅れなし", dict(p_late=0)), ("訂正なし", dict(p_upd=0)), ("削除なし", dict(p_del=0)),
                 ("どれも半分", dict(p_late=.03, p_upd=.015, p_del=.005)), ("どれも2倍", dict(p_late=.12, p_upd=.06, p_del=.02))]:
    r = simulate(make(**kw))
    for m in METHODS[:5]:
        s = r["summ"][m]; t_ = r["true"]
        sens.append({"場面": name, "更新の仕方": m, "ずれた日の割合": (s != t_).mean(), "金額のずれ（差し引き）": (s.sum() - t_.sum()) / t_.sum(),
                     "金額のずれ（絶対値の合計÷売上）": np.abs(s - t_).sum() / t_.sum()})
sens = pd.DataFrame(sens); sens.to_csv(RES / "sensitivity.csv", index=False)

# 乱数の種を変えた20回（基本の場面）
rep = []
for sd in range(20):
    r = simulate(make(seed=1000 + sd))
    for m in METHODS[:5]:
        s = r["summ"][m]; t_ = r["true"]
        rep.append({"seed": 1000 + sd, "更新の仕方": m, "ずれた日の割合": (s != t_).mean(), "金額のずれ（差し引き）": (s.sum() - t_.sum()) / t_.sum()})
rep = pd.DataFrame(rep); rep.to_csv(RES / "repeat20.csv", index=False)
rep_sum = rep.groupby("更新の仕方").agg(ずれた日の割合_中央値=("ずれた日の割合", "median"), ずれた日の割合_最小=("ずれた日の割合", "min"),
                                    ずれた日の割合_最大=("ずれた日の割合", "max"), 金額の差_中央値=("金額のずれ（差し引き）", "median")).reset_index()
rep_sum.to_csv(RES / "repeat20_summary.csv", index=False)

# DuckDB で確かめる：最後の時点の元の表から日別に集計し直すと、true と一致する。全期間を日ごとに比べる照合が A のずれた日数を返す
T = R["T"]
final = df[(df.created <= T) & (df.dele > T)].copy()
final["amount"] = np.where(final.upd <= T, final.amt1, final.amt0)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("raw", final[["sale", "amount"]])
agg = con.execute("SELECT sale, SUM(amount) AS amount FROM raw GROUP BY sale ORDER BY sale").df()
assert (agg.amount.values == true).all()
con.register("summ_a", pd.DataFrame({"sale": np.arange(ND), "amount": R["summ"][METHODS[0]]}))
k5 = con.execute("""SELECT COUNT(*) FROM (SELECT sale, SUM(amount) AS amount FROM raw GROUP BY sale) r
                    FULL JOIN summ_a s ON s.sale=r.sale WHERE COALESCE(r.amount,0) <> COALESCE(s.amount,0)""").fetchone()[0]
assert k5 == int(res.loc[0, "ずれた日数"])

main = {"前提": {"売上の日数": ND, "1日の行数": PER_DAY, "遅れて届く行": P_LATE, "金額の訂正": P_UPD, "行の削除": P_DEL,
               "遅れの日数": "70%は1〜3日、25%は4〜30日、5%は31〜90日"},
        "最後の時点": res.round(6).to_dict("records"), "照合": det.to_dict("records")}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=lambda o: None if o is None else int(o))

# ---------------- 図 ----------------
col = [ORANGE, BLUE, LIGHT, GREEN, GRAY, INK]
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2)); y = np.arange(len(res))
ax[0].barh(y, res["ずれた日の割合"] * 100, color=col); ax[0].set_yticks(y); ax[0].set_yticklabels(res["更新の仕方"], fontsize=9); ax[0].invert_yaxis()
for i, v in enumerate(res["ずれた日の割合"] * 100): ax[0].text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
ax[0].set_xlim(0, 118); ax[0].set_xlabel("365日のうち、元の表と合わない日（%）"); ax[0].set_title("ずれた日の割合")
ax[1].barh(y, res["金額のずれ（差し引き）"] * 100, color=col); ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis()
for i, v in enumerate(res["金額のずれ（差し引き）"] * 100): ax[1].text(v - 0.05 if v < 0 else v + 0.05, i, f"{v:+.2f}%", va="center", ha="right" if v < 0 else "left", fontsize=9)
ax[1].axvline(0, color=INK, lw=.8); ax[1].set_xlim(-7.5, 1.5); ax[1].set_xlabel("1年の売上の合計の差（%）"); ax[1].set_title("金額の差（集計済みの表 − 元の表）")
fig.suptitle("更新の仕方ごとの、最後の時点でのずれ", y=1.02)
save(fig, "a402_final_drift.png", SRC, y=-0.03)

fig, ax = plt.subplots(figsize=(8.4, 4.4))
for m, c in zip(METHODS[:4], col):
    ax.plot(ts["日目"], ts[m + "_ずれた日の割合"] * 100, color=c, lw=1.8, label=m)
ax.axvline(ND, color=GRAY, ls=":", lw=1); ax.text(ND + 3, 5, "売上の最後の日", fontsize=8, color=GRAY)
ax.set_xlabel("取り込みを始めてからの日数"); ax.set_ylabel("その時点までの日のうち、合わない日（%）"); ax.set_title("合わない日の割合は、日がたつとどう動くか"); ax.legend(frameon=False, fontsize=9)
save(fig, "a402_drift_over_time.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2)); ax.axis("off")
piv = det.pivot(index="照合", columns="更新の仕方", values="気づくまでの日数").reindex(CHECKS)[METHODS[:4]]
piv2 = det.pivot(index="照合", columns="更新の仕方", values="ずれがあるのに鳴らなかった晩の割合").reindex(CHECKS)[METHODS[:4]]
cell = [[("気づかない" if pd.isna(piv.loc[k, m]) else f"{int(piv.loc[k, m])}日後") + f"\n（鳴らない晩 {piv2.loc[k, m]:.0%}）" for m in METHODS[:4]] for k in CHECKS]
tb = ax.table(cellText=cell, rowLabels=CHECKS, colLabels=[m.replace("を作り直す", "").replace("で変わった日", "") for m in METHODS[:4]], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 2.2)
for (r, c), ce in tb.get_celld().items():
    ce.set_edgecolor("#d0d0d0")
    if r > 0 and c >= 0 and "気づかない" in ce.get_text().get_text(): ce.set_facecolor("#fde3d8")
ax.set_title("照合のクエリは、最初のずれから何日で気づくか", pad=12)
save(fig, "a402_detection_table.png", SRC, y=0.02)
print(res.to_string()); print(det.to_string()); print(sens.to_string()); print(rep_sum.to_string())
