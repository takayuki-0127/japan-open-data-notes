"""04 図：5枚（6枚目はダッシュボードの画面）。"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C = {"D1 前日比": "#7f7f7f", "D1 前日比10%": "#7f7f7f", "D2 28日平均": "#bcbd22", "D2 28日平均±3σ": "#bcbd22", "D3 同じ曜日の中央値": "#1f77b4",
     "D4 STLの残差": "#9467bd", "D4b STL＋外れで尺度": "#8c564b", "D5 D3＋暦": "#d62728", "D6 D5＋2日確認": "#ff7f0e", "D7 暦＋気温の回帰": "#2ca02c"}
# 図1：架空のあおばマートの注文数と警報（2024年4〜6月）
s = pd.read_csv("results/A_sim_seed0_series.csv", parse_dates=["date"])
w = s[(s.date >= "2024-04-01") & (s.date <= "2024-06-30")]
fig, ax = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True)
for a, m, ttl in [(ax[0], "D1 前日比10%", "前日比で10%以上動いたら鳴らす（D1）"), (ax[1], "D5 D3＋暦", "前の同じ曜日4回の中央値と比べ、祝日・販促も考える（D5）")]:
    a.plot(w.date, w.orders, color="#333", lw=1.2)
    for d in w.date[w.anomaly]: a.axvspan(d - pd.Timedelta(hours=12), d + pd.Timedelta(hours=12), color="#ffd166", alpha=0.6, lw=0)
    for d in w.date[w.sp == 3]: a.axvspan(d - pd.Timedelta(hours=12), d + pd.Timedelta(hours=12), color="#1f77b4", alpha=0.12, lw=0)
    hit = w[w[m]]; a.scatter(hit.date, hit.orders, color=C[m], s=40, zorder=3)
    tp = (hit.anomaly).sum(); a.set_title(f"{ttl}：鳴った{len(hit)}日のうち、入れた異常の日{tp}日", fontsize=11, loc="left")
    a.set_ylabel("注文数")
ax[1].text(0.01, -0.22, "黄色＝わざと入れた異常の日、青の帯＝月例セール（予定どおりの山）。数字はすべて架空（シミュレーション）", transform=ax[1].transAxes, fontsize=9, color="#555")
plt.tight_layout(); plt.savefig("figures/fig1_example.png", dpi=150); plt.close()
# 図2：空振りの回数と見つけた割合（閾値を変えた線）
F = pd.read_csv("results/A_frontier.csv")
fig, ax = plt.subplots(figsize=(9.5, 5.6))
for m, g in F.groupby("method"):
    g = g.sort_values("fa"); ax.plot(g.fa.clip(lower=0.3), g.recall * 100, "-o", ms=3, color=C[m], label=m)
ax.set_xscale("log"); ax.set_xticks([0.5, 1, 2, 4, 12, 52, 100]); ax.set_xticklabels(["0.5", "1", "2", "4", "12", "52", "100"])
ax.axvline(4, color="#aaa", ls="--"); ax.text(4.2, 3, "年4回まで", color="#666", fontsize=10)
ax.set_xlabel("空振りの回数（1年あたり、対数目盛）"); ax.set_ylabel("ふつうの日の異常を見つけた割合（%）"); ax.legend(fontsize=9, frameon=False, loc="upper left")
ax.set_title("閾値を動かすと：同じ空振りの回数なら、暦を考えたルール（D5）がいちばん多く見つけた", fontsize=11, loc="left")
plt.tight_layout(); plt.savefig("figures/fig2_frontier.png", dpi=150); plt.close()
# 図3：異常の大きさ別に見つけた割合（下振れ）
B = pd.read_csv("results/A_recall_by_size.csv"); B = B[B.sign == -1]
fig, ax = plt.subplots(figsize=(9.5, 5))
for _, r in B.iterrows():
    m = r.method
    if m in ["D2 28日平均±3σ", "D4 STLの残差"]: continue
    ax.plot([5, 10, 15, 20, 30], [r["0.05"] * 100, r["0.1"] * 100, r["0.15"] * 100, r["0.2"] * 100, r["0.3"] * 100], "-o", color=C[m], label=m)
ax.set_xlabel("異常の大きさ（いつもより何%下がったか）"); ax.set_ylabel("見つけた割合（%）"); ax.legend(fontsize=9, frameon=False)
ax.set_title("下振れの大きさ別：15〜20%（ふだんの揺れの約4倍）から見つかり始める。前日比（D1）が高いのは年69回鳴らすため", fontsize=11, loc="left")
plt.tight_layout(); plt.savefig("figures/fig3_by_size.png", dpi=150); plt.close()
# 図4：既定の閾値で、1年に何回空振りし、何割見つけたか
A = pd.read_csv("results/A_sim_summary.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.8))
y = np.arange(len(A))
ax[0].barh(y, A.fa_per_year, color=[C[m] for m in A.method]); ax[0].errorbar(A.fa_per_year, y, xerr=[A.fa_per_year - A.fa_lo, A.fa_hi - A.fa_per_year], fmt="none", ecolor="#333", lw=1)
ax[0].set_yticks(y); ax[0].set_yticklabels(A.method); ax[0].invert_yaxis(); ax[0].set_xlabel("空振りの回数（1年あたり）")
for i, v in enumerate(A.fa_per_year): ax[0].text(v + 1, i, f"{v:.1f}", va="center", fontsize=9)
ax[1].barh(y, A.recall * 100, color=[C[m] for m in A.method]); ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis(); ax[1].set_xlabel("ふつうの日の異常を見つけた割合（%）")
for i, v in enumerate(A.recall): ax[1].text(v * 100 + 1, i, f"{v*100:.0f}%", va="center", fontsize=9)
fig.suptitle("既定の閾値のまま使うと：よく見つけるルールは、1年に60回以上空振りした（種20通りの平均と95%の幅）", fontsize=11, x=0.01, ha="left")
plt.tight_layout(); plt.savefig("figures/fig4_default_thresholds.png", dpi=150); plt.close()
# 図5：本物の毎日の数字（東京の電力需要）で鳴った日
R = pd.read_csv("results/B_real_power_alerts.csv"); R = R[R.area == "tokyo"]
cols = ["share_特別な日", "share_特別な日の前後", "share_気温が急に変わった日", "share_そのほか"]; cc = ["#9467bd", "#c5b0d5", "#ff9896", "#c7c7c7"]
fig, ax = plt.subplots(figsize=(10.5, 5.2)); y = np.arange(len(R)); left = np.zeros(len(R))
for c, col in zip(cols, cc):
    v = (R[c] * R.alert_days_per_year).values; ax.barh(y, v, left=left, color=col, label=c.replace("share_", "")); left += v
for i, (dy, ev) in enumerate(zip(R.alert_days_per_year, R.events_per_year)): ax.text(dy + 1, i, f"{dy:.0f}日（{ev:.0f}回）", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(R.method); ax.invert_yaxis(); ax.set_xlabel("鳴った日数（1年あたり、2018年4月〜2026年9月）")
ax.legend(fontsize=9, frameon=False, loc="lower right"); ax.set_title("本物の数字（東京の毎日の電力需要）：暦を考えると、残る警報の8割は「気温が急に変わった日」", fontsize=11, loc="left")
plt.tight_layout(); plt.savefig("figures/fig5_real_power.png", dpi=150); plt.close()
print("figs ok")
