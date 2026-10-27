"""04 図：figures/ に6枚"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, COL

FIG.mkdir(exist_ok=True)
F = pd.read_csv(RES / "factors_mine_vs_published.csv", parse_dates=["date"]).rename(columns={"Unnamed: 0": "date"})
if "date" not in F.columns:
    F = F.rename(columns={F.columns[0]: "date"})
F["date"] = pd.to_datetime(F["date"])
CMP = pd.read_csv(RES / "compare_with_published.csv")
CAL = pd.read_csv(RES / "calendar_effects.csv")
CF = pd.read_csv(RES / "iip_calendar_factor.csv", parse_dates=[0], index_col=0)
REV = pd.read_csv(RES / "revisions.csv", parse_dates=["月"])
ROB = pd.read_csv(RES / "robustness.csv")


def sub(k):
    return F[F["系列"] == k].set_index("date").sort_index()


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=130)
    plt.close(fig)


# 1. 原数値・季節要素・暦要素（鉱工業生産）
d = sub("鉱工業生産")["2014":]
fig, ax = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True, gridspec_kw={"height_ratios": [2, 1.2, 1.2]})
ax[0].plot(d.index, d["原数値"], color=COL["原数値"], lw=1, label="原指数（季節調整前）")
ax[0].plot(d.index, d["公表_季節調整値"], color=COL["公表値"], lw=1.6, label="季節調整済指数（公表）")
ax[0].set_ylabel("2020年=100")
ax[0].legend(loc="lower left", fontsize=9, frameon=False)
ax[0].set_title("鉱工業生産を分けると：毎年同じ形でくり返す「季節」と、曜日・祝日の並びで決まる「暦」", fontsize=11, loc="left")
ax[1].plot(d.index, d["自作_季節要素"], color=COL["X-13（自作）"], lw=1.2)
ax[1].axhline(100, color="#ccc", lw=0.8)
ax[1].set_ylabel("季節要素")
ax[2].bar(d.index, d["自作_暦要素"] - 100, width=25, color=np.where(d["自作_暦要素"] >= 100, "#1a73e8", "#e37400"))
ax[2].axhline(0, color="#999", lw=0.8)
ax[2].set_ylabel("暦要素（%）")
ax[2].text(0.01, 0.95, "X-13 の自作（2014〜2025年で計算、2026年は予測）", transform=ax[2].transAxes, fontsize=8, va="top", color="#555")
save(fig, "a42_components.png")

# 2. 自作と公表の比較
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.5, 1]})
d = sub("鉱工業生産")["2023":]
ax[0].plot(d.index, d["公表_季節調整値"], color=COL["公表値"], lw=2.2, label="公表")
ax[0].plot(d.index, d["自作_季節調整値"], color=COL["X-13（自作）"], lw=1.3, ls="--", label="自作（公表元の説明どおり）")
ax[0].plot(d.index, d["原数値"] / d["自作_季節指数_暦なし"] * 100, color="#e37400", lw=1, alpha=0.8, label="自作（曜日・祝日の調整なし）")
ax[0].set_title("鉱工業生産の季節調整済指数（2023年〜）", fontsize=11, loc="left")
ax[0].legend(fontsize=8.5, frameon=False, loc="lower left")
ax[0].set_ylabel("2020年=100")
rows = []
for k, per in [("鉱工業生産", "2025年"), ("鉱工業出荷", "2025年"), ("労働力人口", "2016〜2025年（再計算された期間）"),
               ("就業者", "2016〜2025年（再計算された期間）"), ("雇用者", "2016〜2025年（再計算された期間）"),
               ("非労働力人口", "2016〜2025年（再計算された期間）"), ("完全失業者", "2016〜2025年（再計算された期間）")]:
    r = CMP[(CMP["系列"] == k) & (CMP["期間"] == per) & (CMP["設定"] == "公表元の説明どおり")].iloc[0]
    rows.append((k, r["季節指数の差の平均"]))
for k, per in [("鉱工業生産", "2025年"), ("鉱工業出荷", "2025年")]:
    r = CMP[(CMP["系列"] == k) & (CMP["期間"] == per) & (CMP["設定"] == "曜日・祝日の調整なし")].iloc[0]
    rows.append((k + "\n（曜日・祝日なし）", r["季節指数の差の平均"]))
rows = rows[::-1]
y = np.arange(len(rows))
ax[1].barh(y, [v for _, v in rows], color=["#e37400" if "なし" in k else "#1a73e8" for k, _ in rows])
ax[1].set_yticks(y, [k for k, _ in rows], fontsize=9)
for i, (_, v) in enumerate(rows):
    ax[1].text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=8.5)
ax[1].set_xlabel("季節指数の差の平均（指数ポイント、100=平均）")
ax[1].set_title("自作と公表の季節指数の差", fontsize=11, loc="left")
save(fig, "a42_mine_vs_published.png")

# 3. 曜日・祝日の効果
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
c = CF["2014":"2025"].copy()
w = c["稼働日数（平日−平日の祝日）"]
c["稼働日の差"] = w - w.groupby(c.index.month).transform("mean")
sc = ax[0].scatter(c["稼働日の差"] + np.random.default_rng(42).uniform(-0.05, 0.05, len(c)), c["暦要素"] - 100,
                   c=c.index.month, cmap="twilight", s=22)
ax[0].axhline(0, color="#999", lw=0.8)
ax[0].set_xlabel("稼働日数（平日 − 平日の祝日）の、同じ月の平均との差（日）")
ax[0].set_ylabel("暦要素（%）")
ax[0].set_title("鉱工業生産：稼働日が1日多いと、それだけで約2%高く出る", fontsize=11, loc="left")
cb = fig.colorbar(sc, ax=ax[0], fraction=0.04)
cb.set_label("月")
e = CAL.copy()
e["ラベル"] = e["系列"] + "：" + e["変数"].str.replace("（土日との入れ替え）", "（土日1日と入れ替え）")
e = e.iloc[::-1]
yy = np.arange(len(e))
lo = np.where(e["変数"].str.startswith("平日1日"), (np.exp((e["係数"] - 1.96 * e["標準誤差"]) * 3.5) - 1) * 100,
              (np.exp(e["係数"] - 1.96 * e["標準誤差"]) - 1) * 100)
hi = np.where(e["変数"].str.startswith("平日1日"), (np.exp((e["係数"] + 1.96 * e["標準誤差"]) * 3.5) - 1) * 100,
              (np.exp(e["係数"] + 1.96 * e["標準誤差"]) - 1) * 100)
ax[1].errorbar(e["効果（%）"], yy, xerr=[e["効果（%）"] - lo, hi - e["効果（%）"]], fmt="o", color="#1a73e8", capsize=3)
ax[1].axvline(0, color="#999", lw=0.8)
ax[1].set_yticks(yy, e["ラベル"], fontsize=8.5)
ax[1].set_xlabel("効果（%、95%区間）")
ax[1].set_title("曜日・祝日の効果は系列で違う", fontsize=11, loc="left")
save(fig, "a42_calendar.png")

# 4. STL と X-13
d = pd.read_csv(RES / "stl_vs_x13_鉱工業生産.csv", parse_dates=[0], index_col=0)["2023":"2025"]
s = pd.read_csv(RES / "stl_vs_x13.csv")
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.5, 1]})
for col, c, lab in [("公表", COL["公表値"], "公表"), ("X-13", COL["X-13（自作）"], "X-13（曜日・祝日あり）"), ("STL", COL["STL"], "STL")]:
    ax[0].plot(d.index, d[col].pct_change() * 100, color=c, lw=2 if col == "公表" else 1.2, label=lab, marker="o", ms=2.5)
ax[0].axhline(0, color="#999", lw=0.8)
ax[0].set_ylabel("前月比（%）")
ax[0].set_title("鉱工業生産の前月比（2023〜2025年）", fontsize=11, loc="left")
ax[0].legend(fontsize=8.5, frameon=False)
lab = []
vals = []
for k in ["鉱工業生産", "就業者", "完全失業者"]:
    for m in ["X-13（全期間を1回で計算）", "X-13（曜日・祝日の調整なし）", "STL"]:
        r = s[(s["系列"] == k) & (s["方法"] == m)]
        if len(r):
            lab.append(f"{k}\n{m.replace('（全期間を1回で計算）', '').replace('（曜日・祝日の調整なし）', '・暦なし')}")
            vals.append(r["前月比の向きの一致率"].iloc[0])
yy = np.arange(len(vals))[::-1]
ax[1].barh(yy, vals, color=["#e37400" if "STL" in l else ("#f9ab00" if "暦なし" in l else "#1a73e8") for l in lab])
ax[1].set_yticks(yy, lab, fontsize=8)
for i, v in zip(yy, vals):
    ax[1].text(v + 0.5, i, f"{v:.0f}%", va="center", fontsize=8)
ax[1].set_xlim(0, 105)
ax[1].set_xlabel("前月比の向きが公表と同じだった月の割合")
ax[1].set_title("前月比の向きの一致率", fontsize=11, loc="left")
save(fig, "a42_stl_vs_x13.png")

# 5. 改定
fig, ax = plt.subplots(1, 3, figsize=(12, 4))
for i, k in enumerate(["鉱工業生産", "完全失業者", "就業者"]):
    r = REV[REV["系列"] == k]
    lim = max(r[["毎月計算_初回の前月比", "年1回_初回の前月比", "2026年8月までで計算した前月比"]].abs().max()) * 1.1
    ax[i].scatter(r["年1回_初回の前月比"], r["2026年8月までで計算した前月比"], color="#e37400", s=18, label="年に1度だけ計算（公表のやり方に近い）")
    ax[i].scatter(r["毎月計算_初回の前月比"], r["2026年8月までで計算した前月比"], color="#1a73e8", s=18, label="毎月計算し直す")
    ax[i].plot([-lim, lim], [-lim, lim], color="#999", lw=0.8)
    ax[i].axhline(0, color="#ddd", lw=0.6)
    ax[i].axvline(0, color="#ddd", lw=0.6)
    ax[i].set_xlim(-lim, lim)
    ax[i].set_ylim(-lim, lim)
    m1 = r["毎月計算_改定幅"].abs().mean()
    m2 = r["年1回_改定幅"].abs().mean()
    ax[i].set_title(f"{k}\n改定幅の平均：毎月 {m1:.2f} / 年1回 {m2:.2f}ポイント", fontsize=10, loc="left")
    ax[i].set_xlabel("その月の分が出た時点の前月比（%）")
    if i == 0:
        ax[i].set_ylabel("2026年8月までのデータで計算した前月比（%）")
ax[0].legend(fontsize=7.5, frameon=False, loc="upper left")
save(fig, "a42_revisions.png")

# 6. 頑健性
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
for i, k in enumerate(["鉱工業生産", "就業者"]):
    r = ROB[ROB["系列"] == k].iloc[::-1]
    yy = np.arange(len(r))
    base = r["設定"].str.startswith("基本")
    ax[i].barh(yy, r["季節指数の差の平均"], color=np.where(base, "#1a73e8", "#9aa0a6"))
    ax[i].set_yticks(yy, ["基本（公表元の説明どおり）" if s.startswith("基本") else s for s in r["設定"]], fontsize=8)
    for j, v in zip(yy, r["季節指数の差の平均"]):
        ax[i].text(v * 1.02 + 0.003, j, f"{v:.3f}", va="center", fontsize=8)
    ax[i].set_xlabel("公表との季節指数の差の平均（指数ポイント）")
    ax[i].set_title(f"{k}：設定を変えると公表との差は", fontsize=11, loc="left")
save(fig, "a42_robustness.png")
print("ok")
