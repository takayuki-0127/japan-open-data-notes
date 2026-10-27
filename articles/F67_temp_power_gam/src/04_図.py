"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG

t = pd.read_csv(DATA / "daily_tokyo.csv", parse_dates=["date"])
mm = pd.read_csv(RES / "marginal_main.csv")
gc = pd.read_csv(RES / "gam_curve.csv")
mp = pd.read_csv(RES / "marginal_by_period.csv")
sm = pd.read_csv(RES / "summary.csv")
bh = pd.read_csv(RES / "by_hour.csv")
mt = pd.read_csv(RES / "marginal_tokyo24.csv")
mk = pd.read_csv(RES / "marginal_kansai.csv")
tr = sm.loc[0, "trough"]

# 1 散布図と当てはめ
fig, ax = plt.subplots(figsize=(8, 5))
wk = t[(t.offday == 0) & (t.obon == 0) & (t.nenmatsu == 0) & (t.gw == 0)]
for (a, b), c, lab in [((2016, 2019), "#9aa0a6", "2016〜19年度"), ((2023, 2026), "#1a73e8", "2023〜26年度")]:
    x = wk[(wk.fy >= a) & (wk.fy <= b)]
    ax.scatter(x.temp_mean, x.demand_gwh, s=5, alpha=.35, color=c, label=f"平日（{lab}）")
ax.plot(mm.temp, mm.level_gwh, color="#d93025", lw=2.2, label="当てはめ（平日・最新年度）")
ax.axvline(tr, color="#5f6368", ls=":", lw=1)
ax.text(tr + .3, ax.get_ylim()[0] + 30, f"いちばん少ない {tr:.1f}℃", color="#5f6368")
ax.set_xlabel("日平均気温（℃、東京）"); ax.set_ylabel("1日の需要（GWh）")
ax.set_title("東京エリアの1日の電力需要と気温：U字だが左右で傾きが違う")
ax.legend(loc="upper center", fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f67_scatter.png"); plt.close()

# 2 1℃あたりの変化率
fig, ax = plt.subplots(figsize=(8, 5))
ax.fill_between(mm.temp, mm.lo, mm.hi, color="#d93025", alpha=.2)
ax.plot(mm.temp, mm.pct_per_deg, color="#d93025", lw=2, label="スプライン回帰（95%区間）")
ax.plot(gc.temp, gc.gam_pct_per_deg, color="#1a73e8", ls="--", lw=1.6, label="GAM（平滑化を自動で選ぶ）")
ax.axhline(0, color="k", lw=.8); ax.axvline(tr, color="#5f6368", ls=":", lw=1)
for tt in [5, 28]:
    v = mm.set_index("temp").loc[float(tt), "pct_per_deg"]
    ax.annotate(f"{tt}℃：{v:+.1f}%", (tt, v), xytext=(tt - 8 if tt > 20 else tt + 1, v - 0.6 if v > 0 else v - 1.2),
                arrowprops=dict(arrowstyle="->", color="#333"), fontsize=10)
ax.set_xlabel("日平均気温（℃）"); ax.set_ylabel("気温が1℃上がったときの需要の変化（%）")
ax.set_title("気温が1℃上がると需要は何%変わるか（東京、2016〜2026年度）")
ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f67_slope.png"); plt.close()

# 3 期間別
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
cols = {"2016〜2019年度": "#9aa0a6", "2020〜2022年度": "#f9ab00", "2023〜2026年度": "#1a73e8"}
for p, g in mp.groupby("period"):
    axes[0].plot(g.temp, g.level_gwh, color=cols[p], lw=2, label=p)
    axes[1].plot(g.temp, g.pct_per_deg, color=cols[p], lw=2, label=p)
axes[0].set_title("平日の需要の水準（各期間の最後の年度）"); axes[0].set_xlabel("日平均気温（℃）"); axes[0].set_ylabel("GWh")
axes[1].axhline(0, color="k", lw=.8)
axes[1].set_title("1℃あたりの変化率（%）"); axes[1].set_xlabel("日平均気温（℃）")
axes[0].legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f67_period.png"); plt.close()

# 4 時刻別
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(bh.hour, bh.pct_at30, "o-", color="#d93025", label="30℃の日：1℃上がると")
ax.fill_between(bh.hour, bh.lo30, bh.hi30, color="#d93025", alpha=.15)
ax.plot(bh.hour, -bh.pct_at5, "o-", color="#1a73e8", label="5℃の日：1℃下がると")
ax.fill_between(bh.hour, -bh.hi5, -bh.lo5, color="#1a73e8", alpha=.15)
ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("時刻"); ax.set_ylabel("需要の増え方（%）")
ax.set_title("時刻ごとの気温の効き方（東京）：暑さは昼に強く、寒さは昼夜の差が小さい")
ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f67_hour.png"); plt.close()

# 5 東京と関西
fig, ax = plt.subplots(figsize=(8, 4.6))
for g, c, lab in [(mt, "#d93025", "東京"), (mk, "#188038", "関西")]:
    ax.plot(g.temp, g.pct_per_deg, color=c, lw=2, label=lab)
    ax.fill_between(g.temp, g.lo, g.hi, color=c, alpha=.12)
ax.axhline(0, color="k", lw=.8)
ax.set_xlabel("日平均気温（℃、東京・大阪）"); ax.set_ylabel("1℃あたりの変化率（%）")
ax.set_title("東京と関西（2024年4月〜2026年9月）")
ax.legend(fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f67_area.png"); plt.close()

# 6 頑健性
r = sm.copy()
r["label"] = r.model.str.replace("頑健性：", "").str.replace("期間：", "期間 ").str.replace("地域：", "")
fig, ax = plt.subplots(figsize=(8, 6))
y = np.arange(len(r))[::-1]
ax.scatter(r.ame_hot, y, color="#d93025", label="暑い日（26℃以上）：1℃上がると", zorder=3)
ax.scatter(-r.ame_cold, y, color="#1a73e8", label="寒い日（8℃以下）：1℃下がると", zorder=3)
ax.set_yticks(y); ax.set_yticklabels(r.label, fontsize=8.5)
ax.set_xlabel("需要の増え方（%、その日の気温での平均）"); ax.set_xlim(0, 6)
ax.set_title("東京では設定を変えても、暑さは寒さの1.5〜1.7倍効く")
ax.legend(fontsize=8.5, loc="upper center", bbox_to_anchor=(0.4, -0.09), ncol=2); fig.tight_layout(); fig.savefig(FIG / "f67_robust.png"); plt.close()
print("ok")
