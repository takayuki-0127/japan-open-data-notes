"""275 稼働率が高い業種と低い業種：能力と稼働率に分ける・自分の過去と比べる"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, splice

setup_font()
d = pd.read_csv(DATA / "capacity_utilization_2018_2026.csv", dtype={"code": str})
old = pd.read_csv(DATA / "utilization_sa_connected_1978_2022.csv", dtype={"code": str})
name = d.drop_duplicates("code").set_index("code").name
d["y"] = d.ym // 100
yr = d[d.y <= 2025].groupby(["kind", "code", "y"]).value.mean()
rows = []
for c in name.index:
    cap, ut = yr["cap"][c], yr["util_nsa"][c]
    lc = np.log(cap[2025] / cap[2018]) * 100; lu = np.log(ut[2025] / ut[2018]) * 100
    # 長い期間：接続指数（季節調整済）と2020年基準の季節調整済をつなぐ
    a = pd.to_numeric(old[old.code == c].set_index("ym").value, errors="coerce")
    b = d[(d.code == c) & (d.kind == "util_sa")].set_index("ym").value
    s = splice(a, b)
    v25 = float(s["2025"].mean()); start = str(s.index.min())
    pct = float((s[: "2024-12"] < v25).mean() * 100)
    pct_since2000 = float((s["2000-01":"2024-12"] < v25).mean() * 100)
    rows.append({"code": c, "name": name[c], "cap_2018": round(cap[2018], 1), "cap_2025": round(cap[2025], 1), "util_2018": round(ut[2018], 1), "util_2025": round(ut[2025], 1),
                 "dlog_cap": round(lc, 1), "dlog_util": round(lu, 1), "dlog_prod_equiv": round(lc + lu, 1),
                 "util_sa_2025_avg": round(v25, 1), "history_start": start, "pct_months_below_2025": round(pct, 1), "pct_since2000": round(pct_since2000, 1),
                 "hist_max": round(float(s.max()), 1), "hist_max_month": str(s.idxmax())})
t = pd.DataFrame(rows).set_index("code"); t.to_csv(RES / "a275_capacity_utilization_by_industry.csv")
MAIN = [c for c in t.index if c.endswith("000000") and c != "1100000000"]
# 製造工業の稼働率の長い系列
a = pd.to_numeric(old[old.code == "1100000000"].set_index("ym").value, errors="coerce"); b = d[(d.code == "1100000000") & (d.kind == "util_sa")].set_index("ym").value
mfg = splice(a, b); mfg.to_frame("util_sa").to_csv(RES / "a275_mfg_utilization_1978_2026.csv")
# 頑健性：2019年を起点に／季節調整済の稼働率で
yr2 = d.groupby(["kind", "code", "y"]).value.mean()
rob = {}
for c in ["1100000000", "1105000000", "1109000000", "1103000000"]:
    rob[c] = {"from2019_dlog_cap": round(float(np.log(yr2["cap"][c][2025] / yr2["cap"][c][2019]) * 100), 1),
              "from2019_dlog_util": round(float(np.log(yr2["util_nsa"][c][2025] / yr2["util_nsa"][c][2019]) * 100), 1),
              "sa_dlog_util_2018_2025": round(float(np.log(yr2["util_sa"][c][2025] / yr2["util_sa"][c][2018]) * 100), 1)}
# 頑健性：2026年1〜8月の平均で順位
v26 = {c: float(d[(d.code == c) & (d.kind == "util_sa") & (d.y == 2026)].value.mean()) for c in MAIN}
main = {"table": t.reset_index().to_dict("records"),
        "mfg": t.loc["1100000000"].to_dict(),
        "n_main": len(MAIN), "n_util_down": int((t.loc[MAIN].dlog_util < 0).sum()), "n_cap_down": int((t.loc[MAIN].dlog_cap < 0).sum()),
        "n_util_bigger_than_cap": int((t.loc[MAIN].dlog_util.abs() > t.loc[MAIN].dlog_cap.abs()).sum()),
        "n_pct_below_25": int((t.loc[MAIN].pct_months_below_2025 < 25).sum()),
        "mfg_lowest_months": {str(k): round(float(v), 1) for k, v in mfg.nsmallest(5).items()},
        "robust": rob, "util_sa_2026_janaug": {name[c]: round(v, 1) for c, v in v26.items()}}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

short = lambda s: s.replace("工業", "").replace("・紙加工品", "")
# 図1：製造工業の稼働率（1978〜）
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(mfg.index.to_timestamp(), mfg.values, color="#333", lw=1.2)
v = t.loc["1100000000", "util_sa_2025_avg"]
ax.axhline(v, color="#d1495b", ls="--", lw=1); ax.text(mfg.index[5].to_timestamp(), v - 4, f"2025年の平均 {v:.1f}：1978〜2024年の月のうち、これより低いのは{t.loc['1100000000','pct_months_below_2025']:.0f}%", color="#d1495b", fontsize=9)
ax.set_ylabel("稼働率指数（季節調整済、2020年=100）"); ax.set_title("製造工業の稼働率（1978年1月〜2026年8月）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a275_mfg_long.png", dpi=150); plt.close()

# 図2：2018→2025年の変化を能力と稼働率に分ける
tt = t.loc[MAIN].sort_values("dlog_prod_equiv")
fig, ax = plt.subplots(figsize=(8.5, 5.2))
yy = np.arange(len(tt))
ax.barh(yy, tt.dlog_cap, color="#2e86ab", label="生産能力の変化")
ax.barh(yy, tt.dlog_util, left=np.where((tt.dlog_cap * tt.dlog_util) > 0, tt.dlog_cap, 0), color="#f2a541", label="稼働率の変化")
ax.scatter(tt.dlog_prod_equiv, yy, color="#333", zorder=3, s=14, label="合計（能力×稼働率）")
ax.set_yticks(yy); ax.set_yticklabels([short(n) for n in tt.name]); ax.axvline(0, color="#333", lw=0.8)
ax.set_xlabel("2018年→2025年の変化（対数の差×100、ほぼ%）"); ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("ほとんどの業種で、能力より稼働率の下がり方が大きい", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a275_decomp.png", dpi=150); plt.close()

# 図3：2025年の稼働率は、自分の過去の何%の月より高いか
tp = t.loc[MAIN].sort_values("pct_months_below_2025")
fig, ax = plt.subplots(figsize=(8, 5))
ax.barh([short(n) for n in tp.name], tp.pct_months_below_2025, color=["#d1495b" if v < 25 else "#8a8a8a" for v in tp.pct_months_below_2025])
for i, (v, s0) in enumerate(zip(tp.pct_months_below_2025, tp.history_start)):
    ax.text(v + 1, i, f"{v:.0f}%（{s0[:4]}年〜）", va="center", fontsize=8)
ax.set_xlim(0, 110); ax.set_xlabel("2025年の平均より稼働率が低かった月の割合（%、その業種の系列の始まり〜2024年）")
ax.set_title("2025年の稼働率は、多くの業種で自分の過去の下の方", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a275_percentile.png", dpi=150); plt.close()
print(t[["name", "dlog_cap", "dlog_util", "dlog_prod_equiv", "util_sa_2025_avg", "history_start", "pct_months_below_2025", "pct_since2000"]].to_string())
print({k: v for k, v in main.items() if k not in ("table", "mfg")})
