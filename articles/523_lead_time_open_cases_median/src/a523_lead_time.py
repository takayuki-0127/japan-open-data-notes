"""523 未完了の案件を除いてリードタイムの中央値を出すと、本当より何日短く出るのか（実務の型）

架空の案件（2024年1月〜2025年12月に受注）を作る。受注から完了までの日数は、どの時期も同じ分布
（対数正規、中央値60日）にしてある。2025年12月31日で締めて集計すると、まだ終わっていない案件がある。
2025年に受注した案件のリードタイムの中央値を、次のやり方で出して「本当の中央値」（全部が終わった後に分かる値）と比べる。
  - 完了分だけ：締めの日までに終わった案件だけの中央値
  - カプラン・マイヤー：終わっていない案件を「締めの日まではまだ続いていた」として入れる
  - 締めを後ろにずらす：締めの30〜360日後まで待って、終わった案件だけの中央値
  - 2025年に完了した案件：受注の時期を問わず、2025年中に終わった案件の中央値
件数が増えている時期・横ばい・減っている時期の3通りで比べる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 523
SRC = "架空の案件データ（作成者が乱数で作成、seed 523）"
CUT = pd.Timestamp("2025-12-31")
MED, SIG = 60.0, 0.9


def make(growth, seed=SEED, per_day=8.0):
    """growth：2024年1月→2025年12月で1日の受注件数が何倍になるか"""
    rng = np.random.default_rng(seed)
    days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
    rate = per_day * growth ** (np.arange(len(days)) / (len(days) - 1)) / np.sqrt(growth)   # 期間の真ん中で per_day
    n = rng.poisson(rate)
    recv = np.repeat(days.to_numpy(), n)
    lt = np.maximum(1, np.round(rng.lognormal(np.log(MED), SIG, len(recv)))).astype(int)
    df = pd.DataFrame({"received": recv, "lead_days": lt})
    df["done"] = df.received + pd.to_timedelta(df.lead_days, unit="D")
    return df


def km_median(t, event):
    """カプラン・マイヤーの中央値（生存が0.5以下になる最初の日）"""
    t = np.asarray(t); event = np.asarray(event, bool)
    order = np.argsort(t, kind="stable"); t, event = t[order], event[order]
    uniq = np.unique(t[event]); S = 1.0
    for u in uniq:
        at_risk = (t >= u).sum(); d = ((t == u) & event).sum()
        S *= 1 - d / at_risk
        if S <= 0.5:
            return float(u)
    return float("nan")


def measure(df):
    c25 = df[df.received.dt.year == 2025]
    true = float(c25.lead_days.median())
    obs = c25.done <= CUT
    out = {"件数(2025年受注)": len(c25), "締めの日に未完了": int((~obs).sum()), "未完了の割合(%)": round((~obs).mean() * 100, 1),
           "本当の中央値": true,
           "完了分だけ": float(c25[obs].lead_days.median()),
           "カプラン・マイヤー": km_median(np.where(obs, c25.lead_days, (CUT - c25.received).dt.days), obs)}
    fin25 = df[(df.done.dt.year == 2025)]
    out["2025年に完了した案件"] = float(fin25.lead_days.median())
    return out


def main():
    scen = [("増えている（2年で3倍）", 3.0), ("横ばい", 1.0), ("減っている（2年で3分の1）", 1 / 3)]
    rows, keep = [], {}
    for name, g in scen:
        df = make(g); keep[name] = df
        m = measure(df); r = {"時期": name, **m}
        for k in ["完了分だけ", "カプラン・マイヤー", "2025年に完了した案件"]:
            r[k + "のずれ(日)"] = round(m[k] - m["本当の中央値"], 1)
        rows.append(r)
    tb = pd.DataFrame(rows); tb.to_csv(RES / "median_by_method.csv", index=False)

    flat = keep["横ばい"]
    out = flat.copy(); out["done_observed"] = np.where(out.done <= CUT, out.done.dt.strftime("%Y-%m-%d"), "")
    out = out.drop(columns=["done"]); out["lead_days_observed"] = np.where(out.done_observed != "", out.lead_days, "")
    out[["received", "done_observed", "lead_days_observed"]].assign(received=out.received.dt.strftime("%Y-%m-%d")).to_csv(DATA / "fictional_cases_flat_cut20251231.csv", index=False)

    # SQL（DuckDB）：締めの日時点の「完了分だけの中央値」と未完了の件数。Python と一致するか
    con = duckdb.connect(); con.execute("SET threads=1")
    con.register("cases", flat.assign(done_obs=flat.done.where(flat.done <= CUT))[["received", "done_obs"]])
    s = con.execute(open(SQL / "02_lead_time_duckdb.sql", encoding="utf-8").read()).df().iloc[0]
    m = measure(flat)
    sql_ok = bool(abs(s.median_completed_only - m["完了分だけ"]) < 1e-9 and int(s.open_cases) == m["締めの日に未完了"])

    # 受注月ごと（横ばい）：完了分だけの中央値と、本当の中央値
    c25 = flat[flat.received.dt.year == 2025].copy(); c25["m"] = c25.received.dt.month; c25["obs"] = c25.done <= CUT
    bm = []
    for mth, g in c25.groupby("m"):
        bm.append({"受注月": mth, "件数": len(g), "未完了の割合(%)": round((~g.obs).mean() * 100, 1),
                   "完了分だけの中央値": float(g[g.obs].lead_days.median()), "本当の中央値": float(g.lead_days.median())})
    bm = pd.DataFrame(bm); bm.to_csv(RES / "by_received_month_flat.csv", index=False)

    # 締めを後ろにずらす（横ばい・増えている）
    sw = []
    for wait in [0, 30, 60, 90, 120, 180, 270, 360]:
        cut = CUT + pd.Timedelta(days=wait); r = {"待つ日数": wait}
        for name in ["増えている（2年で3倍）", "横ばい", "減っている（2年で3分の1）"]:
            d = keep[name]; c = d[d.received.dt.year == 2025]; ob = c.done <= cut
            r[name] = round(float(c[ob].lead_days.median()) - float(c.lead_days.median()), 1)
            r[name + "：未完了(%)"] = round((~ob).mean() * 100, 2)
        sw.append(r)
    sw = pd.DataFrame(sw); sw.to_csv(RES / "sweep_wait_days.csv", index=False)

    res = {"sql_matches_python": sql_ok, "by_scenario": rows, "lognormal_median": MED, "lognormal_sigma": SIG,
           "dec_received_completed_only_median": float(bm.iloc[-1]["完了分だけの中央値"]), "dec_open_pct": float(bm.iloc[-1]["未完了の割合(%)"])}
    json.dump(res, open(RES / "a523_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：受注月ごと
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(bm["受注月"], bm["本当の中央値"], "o-", color=BLUE, label="本当の中央値（全部終わった後に分かる）")
    ax.plot(bm["受注月"], bm["完了分だけの中央値"], "s-", color=ORANGE, label="完了分だけの中央値（2025/12/31 締め）")
    ax2 = ax.twinx(); ax2.bar(bm["受注月"], bm["未完了の割合(%)"], color=LIGHT, alpha=.5, width=.6, zorder=0); ax2.set_ylabel("締めの日に未完了の割合（%、棒）", color=GRAY)
    ax2.set_ylim(0, 100); ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    for i, r in bm.iterrows():
        if r["受注月"] >= 9:
            ax.text(r["受注月"], r["完了分だけの中央値"] - 6, f'{r["完了分だけの中央値"]:.0f}日', ha="center", fontsize=8.5, color=ORANGE)
    ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)]); ax.set_xlabel("受注月（2025年、件数は横ばい）")
    ax.set_ylabel("リードタイムの中央値（日）"); ax.set_ylim(0, 80)
    ax.set_title("締めに近い月に受けた案件ほど、終わったものだけでは短く出る"); ax.legend(frameon=False, loc="lower left", fontsize=9)
    save(fig, "a523_by_month.png", SRC)
    # 図2：やり方ごと
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    meth = ["本当の中央値", "完了分だけ", "カプラン・マイヤー", "2025年に完了した案件"]; cols = [BLUE, ORANGE, GREEN, GRAY]
    x = np.arange(len(rows)); w = .2
    for j, (k, c) in enumerate(zip(meth, cols)):
        ax.bar(x + (j - 1.5) * w, tb[k], w, color=c, label=k)
        for i, v in enumerate(tb[k]):
            ax.text(i + (j - 1.5) * w, v + .8, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x, [f"{r['時期']}\n未完了 {r['未完了の割合(%)']}%" for r in rows], fontsize=9)
    ax.set_ylabel("2025年受注の案件のリードタイムの中央値（日）"); ax.set_ylim(0, 80)
    ax.set_title("終わった案件だけの中央値は短く、カプラン・マイヤーは本当に近い"); ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(.5, -.15))
    save(fig, "a523_by_method.png", SRC, y=-0.13)
    # 図3：待つ日数
    fig, ax = plt.subplots(figsize=(7.2, 4))
    for name, c, mk in [("増えている（2年で3倍）", ORANGE, "s-"), ("横ばい", BLUE, "o-"), ("減っている（2年で3分の1）", GREEN, "^-")]:
        ax.plot(sw["待つ日数"], sw[name], mk, color=c, label=name)
    ax.axhline(0, color=GRAY, lw=.8)
    ax.set_xlabel("締めの日（2025/12/31）から待つ日数"); ax.set_ylabel("完了分だけの中央値 − 本当の中央値（日）")
    ax.set_title("待てば短く出る分は小さくなるが、長い案件が残るうちは0にならない"); ax.legend(frameon=False, loc="lower right")
    save(fig, "a523_wait.png", SRC)
    print(tb.to_string()); print(bm.to_string()); print(sw.to_string()); print(sql_ok)


if __name__ == "__main__":
    main()
