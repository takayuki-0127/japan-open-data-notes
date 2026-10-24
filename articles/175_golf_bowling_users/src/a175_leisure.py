"""ゴルフ場やボウリング場の利用者は、長い目でどう減ったか（2000〜2024年）"""
from common import *
from statsmodels.tsa.holtwinters import Holt

d = load("tokusabi_golf_bowling.csv")
N = {"golf": "ゴルフ場", "golf_range": "ゴルフ練習場", "bowling": "ボウリング場"}; C = {"golf": GREEN, "golf_range": BLUE, "bowling": ORANGE}
idx = {}
L = []
for k in N:
    x = d[d.facility == k].set_index("year")
    # 調査対象の追加で水準が段差になるので、調整済みの前年比をつないで指数にする（2000年=100）
    for c in ["users", "sales"]:
        g = (1 + x[f"{c}_yoy_adj"].fillna(0) / 100).cumprod() * 100
        x[f"{c}_index"] = g
    idx[k] = x
    u = x.users_index
    L.append(f"{N[k]}: 利用者指数 2000=100 → 2019 {u[2019]:.1f} → 2020 {u[2020]:.1f} → 2024 {u[2024]:.1f}（2019比 {u[2024]/u[2019]-1:+.1%}）／売上指数 2019 {x.sales_index[2019]:.1f} 2024 {x.sales_index[2024]:.1f}")
    pre = u.loc[2000:2019]
    L.append(f"  {N[k]} 2000→2019 年平均 {(u[2019]/u[2000])**(1/19)-1:+.2%}")
    m = Holt(pre.values, damped_trend=True, initialization_method="estimated").fit()
    fc = m.forecast(5); x.loc[2020:2024, "holt_fc"] = fc
    L.append(f"  {N[k]} Holt(減衰トレンド, 2000-2019で推定) 2024予測 {fc[-1]:.1f} 実際 {u[2024]:.1f}（実際/予測 {u[2024]/fc[-1]:.2f}）")
    L.append(f"  {N[k]} 1人当たり売上 2000 {x.sales_million_yen[2000]*1e6/x.users[2000]:,.0f}円 2024 {x.sales_million_yen[2024]*1e6/x.users[2024]:,.0f}円（水準の値どうし）")
pd.concat({N[k]: v for k, v in idx.items()}).to_csv(RES / "a175_index.csv")
(RES / "a175_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

fig, ax = plt.subplots(figsize=(9.5, 4.4))
for k in N:
    x = idx[k]; ax.plot(x.index, x.users_index, lw=2.3, color=C[k], label=N[k])
    ax.annotate(f"{x.users_index[2024]:.0f}", (2024, x.users_index[2024]), xytext=(5, -3), textcoords="offset points", fontsize=9, color=C[k])
ax.axhline(100, color=GRAY, lw=0.6, ls=":"); ax.set_ylim(0, 125); ax.set_ylabel("利用者数の指数（2000年＝100）")
ax.legend(frameon=False, loc="lower left"); ax.set_title("利用者数の長期推移（調整済みの前年比をつないだ指数）")
save(fig, "a175_users_index.png")

fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharey=False)
for ax, k in zip(axes, N):
    x = idx[k]
    ax.plot(x.index, x.users_index, color=C[k], lw=2.2, label="実際")
    ax.plot(x.loc[2019:2024].index, [x.users_index[2019]] + list(x.holt_fc.loc[2020:2024]), color=GRAY, ls="--", lw=1.6, label="2019年までの傾向の延長")
    ax.set_title(N[k], fontsize=12); ax.set_xticks([2000, 2010, 2020])
    lo = min(x.users_index.min(), x.holt_fc.min()) * 0.85; ax.set_ylim(lo, max(x.users_index.max(), 100) * 1.08)
axes[0].set_ylabel("指数（2000年＝100）"); axes[0].legend(frameon=False, fontsize=8, loc="lower left")
fig.suptitle("コロナ後の利用者数と、2019年までの傾向の延長（減衰トレンドの指数平滑法）", fontsize=12, y=1.02)
save(fig, "a175_vs_trend.png")

fig, ax = plt.subplots(figsize=(9.5, 4.2))
for k in N:
    x = idx[k]; ax.plot(x.index, x.sales_index / x.users_index * 100, lw=2.2, color=C[k], label=N[k])
ax.axhline(100, color=GRAY, lw=0.6, ls=":"); ax.set_ylabel("売上指数÷利用者指数（2000年＝100）")
ax.legend(frameon=False); ax.set_title("利用者1人当たりの売上の動き（指数どうしの比）")
save(fig, "a175_per_user.png")
